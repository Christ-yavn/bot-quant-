"""
src.backtest.engine
===================
High-throughput event-driven tick backtester for Deriv synthetic indices.

Features:
- Pure discrete event loop with zero lookahead (orders at t fill at t+1)
- Exact Deriv cost structures: dynamic bid/ask spread, overnight swaps, margin calculation
- 50% stop-out forced liquidation cascade (prioritizing worst floating loss)
- 100% gap slippage on spikes and jump discontinuities
- Real-time portfolio state and equity curve tracking
- Full integration with StrategyInterface and Polars Parquet datasets
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import polars as pl

from src.backtest.costs import (
    DERIV_SPECS,
    SymbolSpec,
    calculate_margin,
    calculate_swap,
    check_position_stops_with_gap_slippage,
    clamp_lot_size,
    execute_market_order_with_gap_slippage,
)
from src.backtest.metrics import calculate_backtest_metrics
from src.backtest.portfolio import (
    AccountState,
    OrderRequest,
    OrderSide,
    OrderType,
    Position,
)
from src.data.schema import TickRecord


class BacktestEngine:
    """
    High-fidelity event-driven tick backtester (PROJECT.md §5, F8-F11).
    Zero-lookahead: decisions at tick t fill at tick t+1.
    Full margin calculation and 50% stop-out liquidation.
    """

    def __init__(
        self,
        initial_balance: float = 1000.0,
        spec: Optional[SymbolSpec] = None,
        specs: Optional[Dict[str, SymbolSpec]] = None,
        record_equity_interval: int = 1,
    ) -> None:
        self.initial_balance = float(initial_balance)
        self.spec = spec or DERIV_SPECS["Step Index"]
        self.specs: Dict[str, SymbolSpec] = dict(specs or DERIV_SPECS)
        if self.spec.symbol not in self.specs:
            self.specs[self.spec.symbol] = self.spec

        self.account = AccountState(
            balance=self.initial_balance,
            equity=self.initial_balance,
            free_margin=self.initial_balance,
        )
        self.ticket_counter = 1
        self.pending_orders: List[OrderRequest] = []
        self.equity_curve: List[Tuple[int, float]] = []
        self.stop_outs_count = 0
        self.record_equity_interval = max(1, record_equity_interval)
        self._tick_step = 0
        self._last_day: Optional[int] = None
        self.latest_quotes: Dict[str, Tuple[float, float]] = {}

    def get_spec(self, symbol: str) -> SymbolSpec:
        """Retrieves symbol specification or defaults to primary spec."""
        return self.specs.get(symbol, self.spec)

    def submit_order(self, order: OrderRequest) -> int:
        """
        Places an order in queue for next tick execution (zero lookahead).
        Returns the assigned order ticket.
        """
        if not order.ticket or order.ticket in self.account.positions or any(o.ticket == order.ticket for o in self.pending_orders):
            order.ticket = self.ticket_counter
            self.ticket_counter += 1
        elif order.ticket >= self.ticket_counter:
            self.ticket_counter = order.ticket + 1

        self.pending_orders.append(order)
        return order.ticket

    def cancel_order(self, ticket: int) -> bool:
        """Cancels a pending order if still in queue."""
        initial_len = len(self.pending_orders)
        self.pending_orders = [o for o in self.pending_orders if o.ticket != ticket]
        return len(self.pending_orders) < initial_len

    def close_position(
        self,
        ticket: int,
        exit_price: float,
        timestamp_ns: int,
        reason: str = "NORMAL",
    ) -> Optional[Dict[str, Any]]:
        """Public alias for closing an active position."""
        return self._close_position(ticket, exit_price, timestamp_ns, reason=reason)

    def _close_position(
        self,
        ticket: int,
        exit_price: float,
        timestamp_ns: int,
        reason: str = "NORMAL",
    ) -> Optional[Dict[str, Any]]:
        """
        Closes an active position at the specified exit price.
        Computes gross PnL, deducts accumulated swaps, updates cash balance,
        and logs the trade record.
        """
        pos = self.account.positions.pop(ticket, None)
        if not pos:
            return None

        spec = self.get_spec(pos.symbol)
        if pos.side == OrderSide.BUY:
            gross_pnl = pos.lots * spec.contract_size * (exit_price - pos.entry_price)
        else:
            gross_pnl = pos.lots * spec.contract_size * (pos.entry_price - exit_price)

        net_pnl = gross_pnl + pos.cumulative_swap
        self.account.balance += net_pnl

        trade_record = {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "side": pos.side.value if hasattr(pos.side, "value") else str(pos.side),
            "lots": pos.lots,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "entry_ts": pos.entry_timestamp_ns,
            "exit_ts": timestamp_ns,
            "gross_pnl": gross_pnl,
            "swap": pos.cumulative_swap,
            "net_pnl": net_pnl,
            "reason": reason,
        }
        self.account.closed_trades.append(trade_record)
        return trade_record

    def _handle_stop_out(self, current_tick: TickRecord) -> None:
        """
        Deriv 50% Stop-Out Liquidation Protocol (PROJECT.md §5.2, F9).
        When Margin Level % <= 50% or Equity <= 0:
        Liquidates open positions in order of worst floating loss until Margin Level > 50%.
        """
        self.latest_quotes[current_tick.symbol] = (current_tick.bid, current_tick.ask)
        while self.account.positions and (self.account.margin_level_pct <= 50.0 or self.account.equity <= 0):
            self.stop_outs_count += 1
            # Find position with the worst (lowest) floating PnL (including accumulated swap)
            def _pos_floating_with_swap(p: Position) -> float:
                q = self.latest_quotes.get(p.symbol, (current_tick.bid, current_tick.ask))
                return p.floating_pnl(q[0], q[1], self.get_spec(p.symbol).contract_size) + p.cumulative_swap

            worst_pos = min(self.account.positions.values(), key=_pos_floating_with_swap)
            quote_worst = self.latest_quotes.get(worst_pos.symbol, (current_tick.bid, current_tick.ask))
            exit_price = quote_worst[0] if worst_pos.side == OrderSide.BUY else quote_worst[1]
            self._close_position(worst_pos.ticket, exit_price, current_tick.timestamp_ns, reason="STOP_OUT")

            # Re-evaluate portfolio state
            total_floating = sum(
                p.floating_pnl(
                    self.latest_quotes.get(p.symbol, (current_tick.bid, current_tick.ask))[0],
                    self.latest_quotes.get(p.symbol, (current_tick.bid, current_tick.ask))[1],
                    self.get_spec(p.symbol).contract_size,
                )
                + p.cumulative_swap
                for p in self.account.positions.values()
            )
            total_margin = sum(
                (
                    p.lots
                    * self.get_spec(p.symbol).contract_size
                    * (
                        self.latest_quotes.get(p.symbol, (current_tick.bid, current_tick.ask))[1]
                        if p.side == OrderSide.BUY
                        else self.latest_quotes.get(p.symbol, (current_tick.bid, current_tick.ask))[0]
                    )
                )
                / self.get_spec(p.symbol).leverage
                for p in self.account.positions.values()
            )
            self.account.margin = total_margin
            self.account.equity = self.account.balance + total_floating
            self.account.free_margin = self.account.equity - self.account.margin
            if self.account.margin > 0:
                self.account.margin_level_pct = (self.account.equity / self.account.margin) * 100.0
            else:
                self.account.margin_level_pct = float("inf")

    def update_account_state(self, current_tick: TickRecord) -> None:
        """
        Recalculates floating equity, required margin, free margin, and margin level.
        Enforces 50% stop-out threshold.
        """
        self.latest_quotes[current_tick.symbol] = (current_tick.bid, current_tick.ask)

        total_floating = 0.0
        total_margin = 0.0

        for pos in self.account.positions.values():
            spec = self.get_spec(pos.symbol)
            quote = self.latest_quotes.get(pos.symbol, (current_tick.bid, current_tick.ask))
            floating = pos.floating_pnl(quote[0], quote[1], spec.contract_size)
            total_floating += floating + pos.cumulative_swap
            # Margin = Lots * ContractSize * Price / Leverage
            pos_price = quote[1] if pos.side == OrderSide.BUY else quote[0]
            pos_margin = (pos.lots * spec.contract_size * pos_price) / spec.leverage
            total_margin += pos_margin

        self.account.margin = total_margin
        self.account.equity = self.account.balance + total_floating
        self.account.free_margin = self.account.equity - self.account.margin

        if self.account.margin > 0:
            self.account.margin_level_pct = (self.account.equity / self.account.margin) * 100.0
        else:
            self.account.margin_level_pct = float("inf")

        if self._tick_step % self.record_equity_interval == 0:
            self.equity_curve.append((current_tick.timestamp_ns, self.account.equity))

        # Check for 50% Stop-Out liquidation trigger
        if self.account.margin > 0 and (self.account.margin_level_pct <= 50.0 or self.account.equity <= 0):
            self._handle_stop_out(current_tick)

    def on_tick(self, next_tick: TickRecord) -> None:
        """
        Processes market tick:
        1. Applies overnight swaps if UTC day rolled over (before stops & fills).
        2. Fills pending orders or executes position closes (zero lookahead).
        3. Tests position stops (SL/TP) with 100% gap slippage on matching symbol.
        4. Updates account state and enforces stop-out liquidation.
        """
        self._tick_step += 1

        # 1. Overnight swap deduction on UTC day change (23:59:59 UTC rollover)
        day = next_tick.timestamp_ns // 86_400_000_000_000
        if self._last_day is not None and day > self._last_day:
            days_passed = day - self._last_day
            for pos in self.account.positions.values():
                spec = self.get_spec(pos.symbol)
                swap_cost = calculate_swap(pos.lots, pos.side, spec, n_days=float(days_passed))
                pos.cumulative_swap += swap_cost
        self._last_day = day

        # 2. Process pending orders from previous tick (zero lookahead)
        orders_to_fill = list(self.pending_orders)
        self.pending_orders.clear()

        for order in orders_to_fill:
            if order.close_ticket is not None:
                if order.close_ticket in self.account.positions:
                    pos = self.account.positions[order.close_ticket]
                    exit_price = next_tick.bid if pos.side == OrderSide.BUY else next_tick.ask
                    self._close_position(pos.ticket, exit_price, next_tick.timestamp_ns, reason=order.comment or "ORDER_CLOSE")
                continue
            elif order.action == "CLOSE":
                opposing_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
                target_pos = next(
                    (p for p in self.account.positions.values() if p.symbol == order.symbol and p.side == opposing_side),
                    None,
                )
                if target_pos:
                    exit_price = next_tick.bid if target_pos.side == OrderSide.BUY else next_tick.ask
                    self._close_position(target_pos.ticket, exit_price, next_tick.timestamp_ns, reason=order.comment or "ORDER_CLOSE")
                continue
            else:
                spec = self.get_spec(order.symbol)
                fill = execute_market_order_with_gap_slippage(order, next_tick, spec)
                pos = Position(
                    ticket=fill.ticket,
                    symbol=order.symbol,
                    side=order.side,
                    lots=fill.lots,
                    entry_price=fill.fill_price,
                    entry_timestamp_ns=fill.timestamp_ns,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic,
                )
                self.account.positions[pos.ticket] = pos

        # 3. Check stop-loss / take-profit triggers with gap slippage
        for pos in list(self.account.positions.values()):
            if pos.symbol != next_tick.symbol:
                continue
            spec = self.get_spec(pos.symbol)
            stop_hit = check_position_stops_with_gap_slippage(pos, next_tick, spec)
            if stop_hit:
                fill_price, reason = stop_hit
                self._close_position(pos.ticket, fill_price, next_tick.timestamp_ns, reason=reason)

        # 4. Update account state (floating equity, margin level, stop-outs)
        self.update_account_state(next_tick)

    def run(
        self,
        ticks: Union[pl.DataFrame, Sequence[TickRecord]],
        strategy: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        High-throughput event-driven simulation loop over ticks.
        
        Parameters
        ----------
        ticks : pl.DataFrame or Sequence[TickRecord]
            Stream of tick records.
        strategy : Optional[StrategyInterface]
            Strategy instance. Receives `(tick, account)` and returns `List[OrderRequest]`.
        
        Returns
        -------
        Dict[str, Any]
            Performance metrics summary dictionary.
        """
        if isinstance(ticks, pl.DataFrame):
            n_ticks = len(ticks)
            if n_ticks == 0:
                return calculate_backtest_metrics(
                    self.account.closed_trades,
                    self.equity_curve,
                    self.initial_balance,
                    self.stop_outs_count,
                )

            ts_arr = ticks["timestamp_ns"].to_numpy()
            sym_arr = (
                ticks["symbol"].to_list() if "symbol" in ticks.columns else [self.spec.symbol] * n_ticks
            )
            bid_arr = ticks["bid"].to_numpy()
            ask_arr = ticks["ask"].to_numpy()
            last_arr = ticks["last"].to_numpy()
            vol_arr = (
                ticks["volume"].to_numpy() if "volume" in ticks.columns else np.ones(n_ticks, dtype=np.float64)
            )
            flag_arr = (
                ticks["flags"].to_numpy() if "flags" in ticks.columns else np.full(n_ticks, 6, dtype=np.uint32)
            )

            for i in range(n_ticks):
                tick = TickRecord(
                    int(ts_arr[i]),
                    str(sym_arr[i]),
                    float(bid_arr[i]),
                    float(ask_arr[i]),
                    float(last_arr[i]),
                    float(vol_arr[i]),
                    int(flag_arr[i]),
                )
                self.on_tick(tick)

                if strategy is not None:
                    new_orders = strategy.on_tick(tick, self.account)
                    if new_orders:
                        for order in new_orders:
                            self.submit_order(order)
        else:
            for tick in ticks:
                self.on_tick(tick)
                if strategy is not None:
                    new_orders = strategy.on_tick(tick, self.account)
                    if new_orders:
                        for order in new_orders:
                            self.submit_order(order)

        metrics = calculate_backtest_metrics(
            closed_trades=self.account.closed_trades,
            equity_curve=self.equity_curve,
            initial_balance=self.initial_balance,
            stop_outs_count=self.stop_outs_count,
        )
        metrics["open_positions"] = len(self.account.positions)
        metrics["account_state"] = self.account
        return metrics
