"""
src.bot.paper_adapter
=====================
High-fidelity local paper trading execution adapter simulating Deriv exchange
microstructure, spread costs, leverage, margin, and gap slippage physics.

Capable of running continuously for >= 1 hour without memory leakage.
Compliant with PROJECT.md §5.E, survey_software_arch.md §6.1, and tests/e2e/contract_harness.py §5 (F13).
"""

from __future__ import annotations

import collections
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.backtest.costs import (
    DERIV_SPECS,
    SymbolSpec,
    check_position_stops_with_gap_slippage,
    clamp_lot_size,
    execute_market_order_with_gap_slippage,
)
from src.backtest.portfolio import (
    AccountState,
    FillReport,
    OrderRequest,
    OrderSide,
    Position,
)
from src.data.schema import TickRecord


@dataclass
class ExecutionResult:
    """Standardized result returned by any ExecutionAdapter upon order submission."""
    ticket: int
    success: bool
    status: str  # "FILLED", "REJECTED", "QUEUED", "CLOSED"
    fill_price: float
    lots: float
    message: str = ""
    error_code: Optional[int] = None
    order_id: Optional[int] = None
    fill_time_ns: Optional[int] = None

    def __post_init__(self) -> None:
        if self.order_id is None:
            self.order_id = self.ticket
        elif self.ticket == 0 and self.order_id is not None:
            self.ticket = self.order_id


class ExecutionAdapter(ABC):
    """
    Abstract Port/Adapter interface for trading bot order execution and position sync.
    Enables plug-and-play switching between Paper Trading and MetaTrader 5 Demo.
    """

    @abstractmethod
    def send_order(self, order: OrderRequest) -> ExecutionResult:
        """Submits an order request to the execution venue."""
        raise NotImplementedError

    @abstractmethod
    def close_position(self, ticket: int) -> bool:
        """Closes a specific position by its unique ticket number."""
        raise NotImplementedError

    @abstractmethod
    def close_all_positions(self) -> int:
        """Closes all active open positions immediately. Returns count of closed positions."""
        raise NotImplementedError

    @abstractmethod
    def emergency_stop(self) -> None:
        """Executes emergency liquidation of all positions and halts order routing."""
        raise NotImplementedError

    @abstractmethod
    def get_account_state(self) -> AccountState:
        """Returns the current real-time snapshot of account balance, equity, and positions."""
        raise NotImplementedError

    def set_position_close_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers an optional callback hook invoked when a position is closed."""
        pass


class PaperTradingAdapter(ExecutionAdapter):
    """
    Genuine Paper Trading Engine implementing:
    - Real-time or simulated tick consumption
    - Next-tick or immediate market fill with exact Deriv spread costs
    - Continuous gap slippage execution on Stop-Loss and Take-Profit crossings
    - Dynamic margin tracking with 50% margin level Stop-Out liquidation
    - Bounded history memory ring-buffer for >= 1 hour continuous execution
    """

    def __init__(
        self,
        initial_balance: float = 1000.0,
        default_spec: Optional[SymbolSpec] = None,
        max_history_records: int = 2000,
    ) -> None:
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin = 0.0
        self.free_margin = initial_balance
        self.margin_level_pct = float("inf")

        self.default_spec = default_spec or DERIV_SPECS["Step Index"]
        self.positions: Dict[int, Position] = {}
        self.closed_trades: collections.deque[Dict[str, Any]] = collections.deque(
            maxlen=max_history_records
        )
        self.latest_ticks: Dict[str, TickRecord] = {}
        self.ticket_counter: int = 1000
        self.stop_outs_count: int = 0
        self.is_stopped: bool = False
        self._position_close_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_position_close_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback hook invoked whenever a position is closed (SL, TP, Stop-out, Manual)."""
        self._position_close_callback = callback

    def get_spec(self, symbol: str) -> SymbolSpec:
        """Retrieves authoritative specification for instrument or default."""
        return DERIV_SPECS.get(symbol, self.default_spec)

    def on_tick(self, tick: TickRecord) -> None:
        """
        Processes an incoming market tick:
        1. Caches latest tick for symbol
        2. Evaluates SL/TP triggers across open positions with gap slippage physics
        3. Recalculates floating PnL, equity, margin, and triggers 50% stop-out if breached
        """
        self.latest_ticks[tick.symbol] = tick
        spec = self.get_spec(tick.symbol)

        # 1. Evaluate position stop loss and take profit with Deriv gap slippage physics
        for ticket in list(self.positions.keys()):
            pos = self.positions.get(ticket)
            if not pos or pos.symbol != tick.symbol:
                continue

            stop_hit = check_position_stops_with_gap_slippage(pos, tick, spec)
            if stop_hit:
                fill_price, reason = stop_hit
                self._close_position_internal(
                    ticket=ticket,
                    exit_price=fill_price,
                    timestamp_ns=tick.timestamp_ns,
                    reason=reason,
                )

        # 2. Update account equity, margin, and margin level
        self._update_account_state(tick)

    def _update_account_state(self, current_tick: Optional[TickRecord] = None) -> None:
        """Recalculates floating equity, total margin, and checks 50% stop-out."""
        total_floating = 0.0
        total_margin = 0.0

        for pos in self.positions.values():
            tick = self.latest_ticks.get(pos.symbol, current_tick)
            if tick is None:
                continue
            spec = self.get_spec(pos.symbol)
            floating = pos.floating_pnl(tick.bid, tick.ask, spec.contract_size)
            total_floating += floating

            pos_price = tick.ask if pos.side == OrderSide.BUY else tick.bid
            pos_margin = (pos.lots * spec.contract_size * pos_price) / max(spec.leverage, 1.0)
            total_margin += pos_margin

        self.margin = total_margin
        self.equity = self.balance + total_floating
        self.free_margin = self.equity - self.margin

        if self.margin > 0:
            self.margin_level_pct = (self.equity / self.margin) * 100.0
        else:
            self.margin_level_pct = float("inf")

        # 3. Check for 50% Stop-Out liquidation
        if (
            self.margin > 0
            and (self.margin_level_pct <= 50.0 or self.equity <= 0)
            and current_tick is not None
        ):
            self._handle_stop_out(current_tick)

    def _handle_stop_out(self, current_tick: TickRecord) -> None:
        """Liquidates position with largest floating loss until margin level > 50%."""
        while self.positions and (self.margin_level_pct <= 50.0 or self.equity <= 0):
            self.stop_outs_count += 1
            spec = self.get_spec(current_tick.symbol)
            # Find worst position
            worst_pos = min(
                self.positions.values(),
                key=lambda p: p.floating_pnl(
                    self.latest_ticks.get(p.symbol, current_tick).bid,
                    self.latest_ticks.get(p.symbol, current_tick).ask,
                    self.get_spec(p.symbol).contract_size,
                ),
            )
            tick = self.latest_ticks.get(worst_pos.symbol, current_tick)
            exit_price = tick.bid if worst_pos.side == OrderSide.BUY else tick.ask
            self._close_position_internal(
                ticket=worst_pos.ticket,
                exit_price=exit_price,
                timestamp_ns=tick.timestamp_ns,
                reason="STOP_OUT_LIQUIDATION",
            )
            self._update_account_state(current_tick)

    def send_order(self, order: OrderRequest) -> ExecutionResult:
        """
        Executes a market order immediately at the current market tick using Deriv specs.
        Supports both position opening and explicit position closing (close_ticket / action='CLOSE').
        """
        if self.is_stopped:
            return ExecutionResult(
                ticket=0,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=order.lots,
                message="Adapter is in EMERGENCY_STOPPED state. Orders refused.",
            )

        spec = self.get_spec(order.symbol)
        clamped_lots = clamp_lot_size(order.lots, spec)

        # Get latest known tick for this symbol
        tick = self.latest_ticks.get(order.symbol)
        if tick is None:
            # Fallback nominal price if no tick streamed yet
            base_p = 1000.0
            tick = TickRecord(
                timestamp_ns=time.time_ns(),
                symbol=order.symbol,
                bid=base_p - spec.point * (spec.spread_points / 2.0),
                ask=base_p + spec.point * (spec.spread_points / 2.0),
                last=base_p,
                volume=1.0,
                flags=6,
            )
            self.latest_ticks[order.symbol] = tick

        # 1. Explicit close order handling
        close_ticket = getattr(order, "close_ticket", None)
        if close_ticket is not None:
            if close_ticket in self.positions:
                pos = self.positions[close_ticket]
                exit_price = tick.bid if pos.side == OrderSide.BUY else tick.ask
                fill_ts = tick.timestamp_ns
                lots = pos.lots
                closed = self.close_position(close_ticket)
                if closed:
                    return ExecutionResult(
                        ticket=close_ticket,
                        order_id=close_ticket,
                        success=True,
                        status="CLOSED",
                        fill_price=exit_price,
                        lots=lots,
                        fill_time_ns=fill_ts,
                        message="Closed paper position by ticket",
                    )
            return ExecutionResult(
                ticket=close_ticket,
                order_id=close_ticket,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=order.lots,
                message=f"Target position ticket {close_ticket} not found to close",
            )
        elif getattr(order, "action", "OPEN") == "CLOSE":
            opposing_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
            target_pos = next(
                (p for p in self.positions.values() if p.symbol == order.symbol and p.side == opposing_side),
                None,
            )
            if target_pos:
                ticket_to_close = target_pos.ticket
                exit_price = tick.bid if target_pos.side == OrderSide.BUY else tick.ask
                fill_ts = tick.timestamp_ns
                lots = target_pos.lots
                closed = self.close_position(ticket_to_close)
                if closed:
                    return ExecutionResult(
                        ticket=ticket_to_close,
                        order_id=ticket_to_close,
                        success=True,
                        status="CLOSED",
                        fill_price=exit_price,
                        lots=lots,
                        fill_time_ns=fill_ts,
                        message="Closed paper position by opposing action",
                    )
            return ExecutionResult(
                ticket=0,
                order_id=0,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=order.lots,
                message=f"Target position for {order.symbol} not found to close",
            )

        # 2. Standard open order flow
        self.ticket_counter += 1
        ticket = self.ticket_counter
        order.ticket = ticket

        # Fill at Ask for BUY, Bid for SELL
        fill_report = execute_market_order_with_gap_slippage(order, tick, spec)

        pos = Position(
            ticket=ticket,
            symbol=order.symbol,
            side=order.side,
            lots=fill_report.lots,
            entry_price=fill_report.fill_price,
            entry_timestamp_ns=fill_report.timestamp_ns,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            comment=order.comment,
            magic=order.magic,
        )
        self.positions[ticket] = pos
        self._update_account_state(tick)

        return ExecutionResult(
            ticket=ticket,
            order_id=ticket,
            success=True,
            status="FILLED",
            fill_price=fill_report.fill_price,
            lots=fill_report.lots,
            message="Filled paper market order",
        )

    def _close_position_internal(
        self,
        ticket: int,
        exit_price: float,
        timestamp_ns: int,
        reason: str = "NORMAL",
    ) -> Optional[Dict[str, Any]]:
        pos = self.positions.pop(ticket, None)
        if not pos:
            return None

        spec = self.get_spec(pos.symbol)
        if pos.side == OrderSide.BUY:
            gross_pnl = pos.lots * spec.contract_size * (exit_price - pos.entry_price)
        else:
            gross_pnl = pos.lots * spec.contract_size * (pos.entry_price - exit_price)

        net_pnl = gross_pnl + pos.cumulative_swap
        self.balance += net_pnl

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
        self.closed_trades.append(trade_record)

        if self._position_close_callback is not None:
            try:
                self._position_close_callback({
                    "ticket": ticket,
                    "symbol": pos.symbol,
                    "side": pos.side.value if hasattr(pos.side, "value") else str(pos.side),
                    "lots": pos.lots,
                    "exit_price": exit_price,
                    "reason": reason,
                    "timestamp_ns": timestamp_ns,
                    "pnl": net_pnl,
                })
            except Exception as e:
                print(f"[PaperTradingAdapter ERROR] position_close_callback error: {e}")

        return trade_record

    def close_position(self, ticket: int) -> bool:
        """Closes position at current market price."""
        pos = self.positions.get(ticket)
        if not pos:
            return False

        tick = self.latest_ticks.get(pos.symbol)
        if tick is not None:
            exit_price = tick.bid if pos.side == OrderSide.BUY else tick.ask
            ts = tick.timestamp_ns
        else:
            exit_price = pos.entry_price
            ts = time.time_ns()

        record = self._close_position_internal(ticket, exit_price, ts, reason="MANUAL_CLOSE")
        self._update_account_state()
        return record is not None

    def close_all_positions(self) -> int:
        """Immediately closes all open positions at current market quotes."""
        tickets = list(self.positions.keys())
        closed_count = 0
        for ticket in tickets:
            if self.close_position(ticket):
                closed_count += 1
        return closed_count

    def emergency_stop(self) -> None:
        """Executes emergency stop: marks adapter as stopped and liquidates all positions."""
        self.is_stopped = True
        self.close_all_positions()

    def get_account_state(self) -> AccountState:
        """Returns fresh AccountState snapshot."""
        self._update_account_state()
        return AccountState(
            balance=round(self.balance, 4),
            equity=round(self.equity, 4),
            margin=round(self.margin, 4),
            free_margin=round(self.free_margin, 4),
            margin_level_pct=round(self.margin_level_pct, 2),
            positions=dict(self.positions),
            closed_trades=list(self.closed_trades),
        )
