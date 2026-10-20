"""
src.strategies.alternative_quant
================================
Alternative quantitative strategies on Deriv synthetic indices:
1. StepMeanReversionStrategy (Discrete Lattice Mean-Reversion on Step Indices)
2. VolatilityBreakoutStrategy (Rolling Volatility Channel Breakout on Continuous Indices)

Compliant with:
- PROJECT.md §3 (F12)
- Survey Math §3.2 (Markov Variance Ratio & Runs Test)
- Survey Math §3.3 & §3.5
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np

from src.backtest.portfolio import AccountState, OrderRequest, OrderSide, OrderType
from src.data.schema import TickRecord
from src.strategies.base import StrategyInterface


class StepMeanReversionStrategy(StrategyInterface):
    """
    Step Lattice Mean-Reversion Strategy (Survey Math §3.2, F12).
    
    Tracks consecutive increments on discrete step trellises (e.g. Step Index).
    When a directional run of length >= streak_length is detected without interruption,
    submits an opposing counter-order expecting an alternating step.
    """

    def __init__(
        self,
        name: str = "StepMeanReversion",
        symbol: str = "Step Index",
        streak_length: int = 3,
        lots: float = 0.10,
        step_size: float = 0.10,
        take_profit_steps: int = 1,
        stop_loss_steps: int = 2,
        max_holding_ticks: int = 10,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged_params = {
            "symbol": symbol,
            "streak_length": streak_length,
            "lots": lots,
            "step_size": step_size,
            "take_profit_steps": take_profit_steps,
            "stop_loss_steps": stop_loss_steps,
            "max_holding_ticks": max_holding_ticks,
        }
        if params:
            merged_params.update(params)

        super().__init__(name=name, params=merged_params)
        self.symbol = str(merged_params["symbol"])
        self.streak_length = int(merged_params["streak_length"])
        self.lots = float(merged_params["lots"])
        self.step_size = float(merged_params["step_size"])
        self.take_profit_steps = int(merged_params["take_profit_steps"])
        self.stop_loss_steps = int(merged_params["stop_loss_steps"])
        self.max_holding_ticks = int(merged_params["max_holding_ticks"])

        self.last_price: Optional[float] = None
        self.current_run_direction: int = 0  # +1 for up, -1 for down
        self.current_streak: int = 0
        self.ticks_in_position: int = 0

    def reset(self) -> None:
        self.last_price = None
        self.current_run_direction = 0
        self.current_streak = 0
        self.ticks_in_position = 0

    def on_tick(self, tick: TickRecord, portfolio_state: AccountState) -> List[OrderRequest]:
        if tick.symbol != self.symbol:
            return []

        orders: List[OrderRequest] = []

        if self.last_price is None:
            self.last_price = tick.last
            return []

        diff = tick.last - self.last_price
        self.last_price = tick.last

        # Check existing positions
        open_positions = [p for p in portfolio_state.positions.values() if p.symbol == self.symbol]

        if open_positions:
            self.ticks_in_position += 1
            if self.ticks_in_position >= self.max_holding_ticks:
                for pos in open_positions:
                    close_side = OrderSide.SELL if pos.side == OrderSide.BUY else OrderSide.BUY
                    orders.append(
                        OrderRequest(
                            symbol=self.symbol,
                            side=close_side,
                            lots=pos.lots,
                            order_type=OrderType.MARKET,
                            action="CLOSE",
                            close_ticket=pos.ticket,
                            comment="STEP_TIME_EXIT",
                        )
                    )
                self.ticks_in_position = 0
                return orders

        # Update run length
        direction = 0
        if diff >= self.step_size / 2.0:
            direction = 1
        elif diff <= -self.step_size / 2.0:
            direction = -1

        if direction != 0:
            if direction == self.current_run_direction:
                self.current_streak += 1
            else:
                self.current_run_direction = direction
                self.current_streak = 1
        else:
            self.current_streak = 0

        # Trigger mean-reversion counter trade
        if len(open_positions) == 0 and self.current_streak >= self.streak_length:
            self.ticks_in_position = 0
            if self.current_run_direction > 0:
                # 3 consecutive up steps -> SELL counter
                entry_side = OrderSide.SELL
                tp = round(tick.bid - self.take_profit_steps * self.step_size, 4)
                sl = round(tick.bid + self.stop_loss_steps * self.step_size, 4)
            else:
                # 3 consecutive down steps -> BUY counter
                entry_side = OrderSide.BUY
                tp = round(tick.ask + self.take_profit_steps * self.step_size, 4)
                sl = round(tick.ask - self.stop_loss_steps * self.step_size, 4)

            orders.append(
                OrderRequest(
                    symbol=self.symbol,
                    side=entry_side,
                    lots=self.lots,
                    order_type=OrderType.MARKET,
                    stop_loss=sl,
                    take_profit=tp,
                    comment=f"STEP_REVERSION_STREAK_{self.current_streak}",
                )
            )
            # Reset streak after firing order
            self.current_streak = 0

        return orders


class VolatilityBreakoutStrategy(StrategyInterface):
    """
    Volatility Channel Breakout Strategy (Survey Math §3.3, §3.5, F12).
    
    Computes a rolling statistical price envelope (moving average +/- k * standard deviations).
    Enters in the direction of the explosive breakout.
    """

    def __init__(
        self,
        name: str = "VolatilityBreakout",
        symbol: str = "Volatility 75 Index",
        window: int = 20,
        k_std: float = 2.0,
        lots: float = 0.001,
        tp_points: float = 10.0,
        sl_points: float = 5.0,
        cooldown_ticks: int = 15,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged_params = {
            "symbol": symbol,
            "window": window,
            "k_std": k_std,
            "lots": lots,
            "tp_points": tp_points,
            "sl_points": sl_points,
            "cooldown_ticks": cooldown_ticks,
        }
        if params:
            merged_params.update(params)

        super().__init__(name=name, params=merged_params)
        self.symbol = str(merged_params["symbol"])
        self.window = max(5, int(merged_params["window"]))
        self.k_std = float(merged_params["k_std"])
        self.lots = float(merged_params["lots"])
        self.tp_points = float(merged_params["tp_points"])
        self.sl_points = float(merged_params["sl_points"])
        self.cooldown_ticks = int(merged_params["cooldown_ticks"])

        self.price_history: deque[float] = deque(maxlen=self.window)
        self.cooldown_counter: int = 0

    def reset(self) -> None:
        self.price_history.clear()
        self.cooldown_counter = 0

    def on_tick(self, tick: TickRecord, portfolio_state: AccountState) -> List[OrderRequest]:
        if tick.symbol != self.symbol:
            return []

        orders: List[OrderRequest] = []
        self.price_history.append(tick.last)
        self.cooldown_counter += 1

        if len(self.price_history) < self.window:
            return []

        open_positions = [p for p in portfolio_state.positions.values() if p.symbol == self.symbol]
        if len(open_positions) > 0 or self.cooldown_counter < self.cooldown_ticks:
            return []

        prices = np.array(self.price_history, dtype=np.float64)
        mean_p = float(np.mean(prices))
        std_p = float(np.std(prices))

        upper_band = mean_p + self.k_std * std_p
        lower_band = mean_p - self.k_std * std_p

        if tick.last > upper_band:
            # Bullish breakout
            self.cooldown_counter = 0
            orders.append(
                OrderRequest(
                    symbol=self.symbol,
                    side=OrderSide.BUY,
                    lots=self.lots,
                    order_type=OrderType.MARKET,
                    stop_loss=tick.ask - self.sl_points if self.sl_points > 0 else None,
                    take_profit=tick.ask + self.tp_points if self.tp_points > 0 else None,
                    comment="VOL_BREAKOUT_BULL",
                )
            )
        elif tick.last < lower_band:
            # Bearish breakdown
            self.cooldown_counter = 0
            orders.append(
                OrderRequest(
                    symbol=self.symbol,
                    side=OrderSide.SELL,
                    lots=self.lots,
                    order_type=OrderType.MARKET,
                    stop_loss=tick.bid + self.sl_points if self.sl_points > 0 else None,
                    take_profit=tick.bid - self.tp_points if self.tp_points > 0 else None,
                    comment="VOL_BREAKDOWN_BEAR",
                )
            )

        return orders
