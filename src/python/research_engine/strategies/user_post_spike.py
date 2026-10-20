"""
src.strategies.user_post_spike
==============================
Implementation and empirical refutation of the User Post-Spike Drift Strategy.

Compliant with:
- PROJECT.md §3 (F12)
- Survey Math §3.1 (Optimal Stopping & Hazard Decay)
- tests/e2e/test_acceptance_tiers.py (Scenario S3)

Concept:
On Boom indices (continuous downward drift punctuated by stochastic upward spikes),
detects an upward spike (|ΔP| >= threshold) and opens SHORT (SELL) positions into the drift.
On Crash indices (continuous upward drift punctuated by stochastic downward spikes),
detects a downward spike (|ΔP| >= threshold) and opens LONG (BUY) positions into the drift.
Implements progressive staged exits (partial lot scale-outs across multiple targets or holding intervals).
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Sequence

from src.backtest.portfolio import AccountState, OrderRequest, OrderSide, OrderType
from src.data.schema import TickRecord
from src.strategies.base import StrategyInterface
from src.strategies.registry import TrialRegistry


# Train-calibrated microstructure defaults across all 10 classic Boom & Crash indices
# Derived strictly from the 60% Train partitions (6,000,000 ticks total; zero Test leakage).
BOOM_CRASH_CALIBRATED_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Boom 1000 Index": {
        "abs_drift": 0.01622,
        "mean_jump": 17.015,
        "spike_threshold": 17.015,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.6488,   # 40 ticks of drift
        "sl_points": 51.045,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Crash 1000 Index": {
        "abs_drift": 0.00625,
        "mean_jump": 5.887,
        "spike_threshold": 5.887,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.2500,   # 40 ticks of drift
        "sl_points": 17.661,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Boom 900 Index": {
        "abs_drift": 0.00969,
        "mean_jump": 8.865,
        "spike_threshold": 8.865,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.3876,   # 40 ticks of drift
        "sl_points": 26.595,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Crash 900 Index": {
        "abs_drift": 0.01861,
        "mean_jump": 17.314,
        "spike_threshold": 17.314,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.7444,   # 40 ticks of drift
        "sl_points": 51.942,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Boom 600 Index": {
        "abs_drift": 0.00873,
        "mean_jump": 5.155,
        "spike_threshold": 5.155,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.3492,   # 40 ticks of drift
        "sl_points": 15.465,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Crash 600 Index": {
        "abs_drift": 0.03848,
        "mean_jump": 22.904,
        "spike_threshold": 22.904,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 1.5392,   # 40 ticks of drift
        "sl_points": 68.712,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Boom 500 Index": {
        "abs_drift": 0.01160,
        "mean_jump": 5.825,
        "spike_threshold": 5.825,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.4640,   # 40 ticks of drift
        "sl_points": 17.475,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Crash 500 Index": {
        "abs_drift": 0.00613,
        "mean_jump": 2.991,
        "spike_threshold": 2.991,
        "total_lots": 0.60,
        "staged_exits": 3,
        "tp_step_points": 0.2452,   # 40 ticks of drift
        "sl_points": 8.973,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Boom 300 Index": {
        "abs_drift": 0.00441,
        "mean_jump": 1.324,
        "spike_threshold": 1.324,
        "total_lots": 1.50,         # 3 stages * 0.50 min lot
        "staged_exits": 3,
        "tp_step_points": 0.1764,   # 40 ticks of drift
        "sl_points": 3.972,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
    "Crash 300 Index": {
        "abs_drift": 0.02249,
        "mean_jump": 6.863,
        "spike_threshold": 6.863,
        "total_lots": 1.50,         # 3 stages * 0.50 min lot
        "staged_exits": 3,
        "tp_step_points": 0.8996,   # 40 ticks of drift
        "sl_points": 20.589,
        "max_holding_ticks": 110,
        "cooldown_ticks": 10,
    },
}


class UserPostSpikeStrategy(StrategyInterface):
    """
    User Post-Spike Drift Harvesting Strategy with Staged Exits, Anti-Cluster Delay,
    and Multi-Spike Cluster Exhaustion Filter (F12).
    """

    def __init__(
        self,
        name: str = "UserPostSpikeDrift",
        symbol: str = "Boom 1000 Index",
        spike_threshold: float = 25.0,
        total_lots: float = 0.60,
        staged_exits: int = 3,
        tp_step_points: float = 1.5,
        sl_points: float = 5.0,
        max_holding_ticks: int = 100,
        cooldown_ticks: int = 10,
        delay_ticks: int = 0,
        min_cluster: int = 1,
        cluster_window: int = 60,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged_params = {
            "symbol": symbol,
            "spike_threshold": spike_threshold,
            "total_lots": total_lots,
            "staged_exits": staged_exits,
            "tp_step_points": tp_step_points,
            "sl_points": sl_points,
            "max_holding_ticks": max_holding_ticks,
            "cooldown_ticks": cooldown_ticks,
            "delay_ticks": delay_ticks,
            "min_cluster": min_cluster,
            "cluster_window": cluster_window,
        }
        if params:
            merged_params.update(params)

        super().__init__(name=name, params=merged_params)
        self.symbol = str(merged_params["symbol"])
        self.spike_threshold = float(merged_params["spike_threshold"])
        self.total_lots = float(merged_params["total_lots"])
        self.staged_exits = max(1, int(merged_params["staged_exits"]))
        self.tp_step_points = float(merged_params["tp_step_points"])
        self.sl_points = float(merged_params["sl_points"])
        self.max_holding_ticks = int(merged_params["max_holding_ticks"])
        self.cooldown_ticks = int(merged_params["cooldown_ticks"])
        self.delay_ticks = max(0, int(merged_params["delay_ticks"]))
        self.min_cluster = max(1, int(merged_params["min_cluster"]))
        self.cluster_window = max(1, int(merged_params["cluster_window"]))

        self.last_price: Optional[float] = None
        self.ticks_since_entry: int = 0
        self.ticks_since_spike: int = 999999
        self.active_entry_tick: Optional[int] = None
        self._current_tick_count: int = 0
        self._pending_direction: Optional[OrderSide] = None
        self._pending_delay_remaining: int = 0
        self._recent_spike_ticks: deque[int] = deque(maxlen=32)

    @classmethod
    def for_symbol(
        cls,
        symbol: str,
        delay_ticks: int = 0,
        min_cluster: int = 1,
        cluster_window: int = 60,
        name: str = "UserPostSpikeDrift",
    ) -> "UserPostSpikeStrategy":
        """
        Instantiates a UserPostSpikeStrategy with Train-calibrated parameters
        for any of the 10 classic Boom & Crash indices.
        """
        cfg = BOOM_CRASH_CALIBRATED_DEFAULTS.get(symbol)
        if cfg is None:
            return cls(
                name=name,
                symbol=symbol,
                delay_ticks=delay_ticks,
                min_cluster=min_cluster,
                cluster_window=cluster_window,
            )
        return cls(
            name=name,
            symbol=symbol,
            spike_threshold=cfg["spike_threshold"],
            total_lots=cfg["total_lots"],
            staged_exits=cfg["staged_exits"],
            tp_step_points=cfg["tp_step_points"],
            sl_points=cfg["sl_points"],
            max_holding_ticks=cfg["max_holding_ticks"],
            cooldown_ticks=cfg["cooldown_ticks"],
            delay_ticks=delay_ticks,
            min_cluster=min_cluster,
            cluster_window=cluster_window,
        )

    def reset(self) -> None:
        """Resets internal state."""
        self.last_price = None
        self.ticks_since_entry = 0
        self.ticks_since_spike = 999999
        self.active_entry_tick = None
        self._current_tick_count = 0
        self._pending_direction = None
        self._pending_delay_remaining = 0
        self._recent_spike_ticks.clear()

    def _determine_direction(self, delta: float) -> Optional[OrderSide]:
        """
        Determines trade direction based on symbol and spike delta.
        - Boom: Upward spike (+delta >= threshold) -> enter SELL (drift is down).
        - Crash: Downward spike (-delta >= threshold) -> enter BUY (drift is up).
        """
        sym_lower = self.symbol.lower()
        if "boom" in sym_lower:
            if delta >= self.spike_threshold:
                return OrderSide.SELL
        elif "crash" in sym_lower:
            if delta <= -self.spike_threshold:
                return OrderSide.BUY
        else:
            # Generic: if positive jump, sell into mean reversion; if negative jump, buy
            if delta >= self.spike_threshold:
                return OrderSide.SELL
            elif delta <= -self.spike_threshold:
                return OrderSide.BUY
        return None

    def _build_staged_orders(self, tick: TickRecord, direction: OrderSide) -> List[OrderRequest]:
        """Builds progressive scale-out orders across `staged_exits` TP levels."""
        orders: List[OrderRequest] = []
        lot_per_stage = max(0.01, self.total_lots / self.staged_exits)
        for stage in range(1, self.staged_exits + 1):
            stage_tp_dist = stage * self.tp_step_points
            if direction == OrderSide.BUY:
                tp = tick.ask + stage_tp_dist
                sl = tick.ask - self.sl_points if self.sl_points > 0 else None
            else:
                tp = tick.bid - stage_tp_dist
                sl = tick.bid + self.sl_points if self.sl_points > 0 else None

            orders.append(
                OrderRequest(
                    symbol=self.symbol,
                    side=direction,
                    lots=lot_per_stage,
                    order_type=OrderType.MARKET,
                    stop_loss=sl,
                    take_profit=tp,
                    comment=f"POST_SPIKE_STAGE_{stage}",
                )
            )
        return orders

    def on_tick(self, tick: TickRecord, portfolio_state: AccountState) -> List[OrderRequest]:
        """
        Processes tick and generates orders:
        - Spike detection, cluster check, and immediate or delayed multi-stage entry
        - Staged holding interval monitoring
        """
        if tick.symbol != self.symbol:
            return []

        self._current_tick_count += 1
        orders: List[OrderRequest] = []

        if self.last_price is None:
            self.last_price = tick.last
            return []

        delta = tick.last - self.last_price
        self.last_price = tick.last
        self.ticks_since_spike += 1

        # Check existing positions for this symbol
        open_positions = [p for p in portfolio_state.positions.values() if p.symbol == self.symbol]

        # 1. Check time-based holding exit for aged positions
        if open_positions:
            self._pending_direction = None
            self._pending_delay_remaining = 0
            self.ticks_since_entry += 1
            if self.ticks_since_entry >= self.max_holding_ticks:
                # Close aged positions
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
                            comment=f"STAGED_TIME_EXIT_STAGE_{self.ticks_since_entry}",
                        )
                    )
                self.ticks_since_entry = 0
                return orders

        # 2. Check for new spike signal if no positions are currently active and cooldown respected
        direction = self._determine_direction(delta)
        if direction is not None:
            self.ticks_since_spike = 0
            self._recent_spike_ticks.append(self._current_tick_count)

            if len(open_positions) == 0 and self._current_tick_count > self.cooldown_ticks:
                cluster_cnt = sum(
                    1 for t_idx in self._recent_spike_ticks
                    if (self._current_tick_count - t_idx) <= self.cluster_window
                )
                if cluster_cnt >= self.min_cluster:
                    if self.delay_ticks <= 0:
                        self.ticks_since_entry = 0
                        orders.extend(self._build_staged_orders(tick, direction))
                    else:
                        self._pending_direction = direction
                        self._pending_delay_remaining = self.delay_ticks
        elif self._pending_direction is not None and len(open_positions) == 0:
            self._pending_delay_remaining -= 1
            if self._pending_delay_remaining <= 0:
                self.ticks_since_entry = 0
                orders.extend(self._build_staged_orders(tick, self._pending_direction))
                self._pending_direction = None

        return orders

    def register_outcome(
        self,
        registry: TrialRegistry,
        pnls: Sequence[float],
        sharpe: float = 0.0,
        notes: str = "",
    ) -> int:
        """
        Helper to evaluate p-value and register this trial into the TrialRegistry.
        """
        import numpy as np

        if len(pnls) == 0:
            p_val = 1.0
            t_stat = 0.0
        else:
            arr = np.array(pnls, dtype=np.float64)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 1.0
            se = std_val / np.sqrt(len(arr)) if len(arr) > 0 else 1.0
            t_stat = mean_val / se if se > 1e-12 else 0.0
            # Two-sided p-value against H0: mean == 0
            from scipy import stats  # type: ignore

            try:
                p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
            except Exception:
                p_val = 0.5

        return self.register_with_trial_registry(
            registry=registry,
            symbol=self.symbol,
            p_value=p_val,
            t_stat=t_stat,
            sharpe=sharpe,
            notes=notes or f"PostSpikeDrift on {self.symbol} (thresh={self.spike_threshold})",
        )
