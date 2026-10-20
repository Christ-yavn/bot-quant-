"""
src.bot.circuit_breakers
========================
Automated risk controls, 5 independent circuit breakers, and coordinating
manager for autonomous Deriv synthetic trading bots.

Compliant with PROJECT.md §6.3, survey_software_arch.md §6.3,
and tests/e2e/contract_harness.py §5 (F14).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.backtest.portfolio import AccountState
from src.data.schema import TickRecord


class CircuitBreaker(ABC):
    """
    Abstract Base Class for an independent risk circuit breaker.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.is_tripped: bool = False
        self.trip_reason: Optional[str] = None
        self.tripped_at_utc: Optional[str] = None

    @abstractmethod
    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Evaluates risk conditions on incoming tick / account state.
        Returns a trip reason string if the breaker trips, otherwise None.
        """
        raise NotImplementedError

    def trip(self, reason: str) -> str:
        """Marks breaker as tripped with reason and timestamp."""
        self.is_tripped = True
        self.trip_reason = reason
        self.tripped_at_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return reason

    def reset(self) -> None:
        """Resets breaker state to nominal."""
        self.is_tripped = False
        self.trip_reason = None
        self.tripped_at_utc = None


class MaxDailyLossBreaker(CircuitBreaker):
    """
    Breaker 1: Trips if cumulative daily realized + floating loss exceeds
    max_daily_loss_usd or daily_loss_pct (PROJECT.md §6.3).
    """

    def __init__(
        self,
        max_daily_loss_usd: float = 100.0,
        daily_loss_pct: float = 5.0,
    ) -> None:
        super().__init__("MaxDailyLossBreaker")
        self.max_daily_loss_usd = max_daily_loss_usd
        self.daily_loss_pct = daily_loss_pct

    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        day_start_equity = context.get("day_start_equity", account_state.balance)
        if day_start_equity <= 0:
            return None

        current_equity = account_state.equity
        loss_usd = day_start_equity - current_equity
        if loss_usd <= 0:
            return None

        loss_pct = (loss_usd / day_start_equity) * 100.0

        if loss_usd >= self.max_daily_loss_usd:
            return self.trip(
                f"DAILY_LOSS_USD: Cumulative daily loss ${loss_usd:.2f} >= limit ${self.max_daily_loss_usd:.2f}"
            )

        if loss_pct >= self.daily_loss_pct:
            return self.trip(
                f"DAILY_LOSS: Daily loss {loss_pct:.2f}% >= limit {self.daily_loss_pct:.2f}%"
            )

        return None


class MaxDrawdownBreaker(CircuitBreaker):
    """
    Breaker 2: Trips if peak-to-trough equity drawdown exceeds max_drawdown_pct.
    """

    def __init__(self, max_drawdown_pct: float = 15.0) -> None:
        super().__init__("MaxDrawdownBreaker")
        self.max_drawdown_pct = max_drawdown_pct

    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        peak_equity = context.get("peak_equity", account_state.equity)
        if peak_equity <= 0:
            return None

        current_equity = account_state.equity
        if current_equity > peak_equity:
            context["peak_equity"] = current_equity
            return None

        dd_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
        if dd_pct >= self.max_drawdown_pct:
            return self.trip(
                f"MAX_DRAWDOWN: Current DD {dd_pct:.2f}% >= limit {self.max_drawdown_pct:.2f}% (Peak: ${peak_equity:.2f}, Current: ${current_equity:.2f})"
            )

        return None


class MaxPositionsBreaker(CircuitBreaker):
    """
    Breaker 3: Trips if open positions strictly exceed max_open_positions.
    """

    def __init__(self, max_open_positions: int = 5) -> None:
        super().__init__("MaxPositionsBreaker")
        self.max_open_positions = max_open_positions

    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        count = len(account_state.positions)
        if count > self.max_open_positions:
            return self.trip(
                f"MAX_POSITIONS: Open positions count {count} > limit {self.max_open_positions}"
            )
        return None


class ConsecutiveLossBreaker(CircuitBreaker):
    """
    Breaker 4: Trips if consecutive losing trades exceed max_consecutive_losses.
    """

    def __init__(self, max_consecutive_losses: int = 4) -> None:
        super().__init__("ConsecutiveLossBreaker")
        self.max_consecutive_losses = max_consecutive_losses

    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        closed = account_state.closed_trades
        if not closed:
            return None

        consecutive_losses = 0
        for trade in reversed(closed):
            # Check pnl
            pnl = trade.get("net_pnl", trade.get("pnl", 0.0))
            if pnl < 0:
                consecutive_losses += 1
            else:
                break

        context["consecutive_losses"] = consecutive_losses

        if consecutive_losses >= self.max_consecutive_losses:
            return self.trip(
                f"CONSECUTIVE_LOSSES: {consecutive_losses} consecutive losses >= limit {self.max_consecutive_losses}"
            )

        return None


class SpreadSpikeBreaker(CircuitBreaker):
    """
    Breaker 5: Trips if current tick spread exceeds max_spread_multiplier * typical_spread.
    """

    def __init__(
        self,
        max_spread_multiplier: float = 3.0,
        default_typical_spread: float = 1.0,
    ) -> None:
        super().__init__("SpreadSpikeBreaker")
        self.max_spread_multiplier = max_spread_multiplier
        self.default_typical_spread = default_typical_spread

    def evaluate(
        self,
        tick: Optional[TickRecord],
        account_state: AccountState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        if tick is None:
            return None

        spread = tick.ask - tick.bid
        typical_spread = context.get("typical_spread", self.default_typical_spread)
        if typical_spread <= 0:
            typical_spread = self.default_typical_spread

        limit = self.max_spread_multiplier * typical_spread
        if spread > limit:
            return self.trip(
                f"EXTREME_SPREAD: {spread:.4f} > {self.max_spread_multiplier:.1f}x typical ({typical_spread:.4f}, limit {limit:.4f})"
            )

        return None


class CircuitBreakerManager:
    """
    Coordinates the 5 independent risk circuit breakers and triggers immediate
    automated emergency stop and position liquidation upon any trip.
    """

    def __init__(
        self,
        max_daily_loss_usd: float = 100.0,
        daily_loss_pct: float = 5.0,
        max_drawdown_pct: float = 15.0,
        max_open_positions: int = 5,
        max_consecutive_losses: int = 4,
        max_spread_multiplier: float = 3.0,
        stale_quote_seconds: float = 5.0,
    ) -> None:
        self.max_daily_loss_breaker = MaxDailyLossBreaker(
            max_daily_loss_usd=max_daily_loss_usd,
            daily_loss_pct=daily_loss_pct,
        )
        self.max_drawdown_breaker = MaxDrawdownBreaker(max_drawdown_pct=max_drawdown_pct)
        self.max_positions_breaker = MaxPositionsBreaker(max_open_positions=max_open_positions)
        self.consecutive_loss_breaker = ConsecutiveLossBreaker(max_consecutive_losses=max_consecutive_losses)
        self.spread_spike_breaker = SpreadSpikeBreaker(max_spread_multiplier=max_spread_multiplier)

        self.breakers: List[CircuitBreaker] = [
            self.max_daily_loss_breaker,
            self.max_drawdown_breaker,
            self.max_positions_breaker,
            self.consecutive_loss_breaker,
            self.spread_spike_breaker,
        ]

        self.stale_quote_seconds = stale_quote_seconds
        self.peak_equity: float = 0.0
        self.day_start_equity: float = 0.0
        self.typical_spread: float = 1.0
        self.last_tick_time: float = 0.0
        self.tripped_breakers: List[str] = []

        # Compatibility aliases with contract_harness
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_pct = daily_loss_pct
        self.spread_multiplier_limit = max_spread_multiplier
        self.median_spread = self.typical_spread

    def initialize(self, initial_equity: float, median_spread: float = 1.0) -> None:
        """Initializes baseline reference values for equity and spread tracking."""
        self.peak_equity = initial_equity
        self.day_start_equity = initial_equity
        self.typical_spread = median_spread
        self.median_spread = median_spread
        self.last_tick_time = time.time()
        self.tripped_breakers.clear()
        for b in self.breakers:
            b.reset()

    @property
    def is_tripped(self) -> bool:
        """Returns True if any breaker has tripped."""
        return len(self.tripped_breakers) > 0 or any(b.is_tripped for b in self.breakers)

    def check(self, tick: Optional[TickRecord], account_state: AccountState) -> List[str]:
        """
        Evaluates all 5 circuit breakers against the current market tick and account state.
        Returns a list of newly tripped breaker message strings.
        """
        # Update peak equity
        if account_state.equity > self.peak_equity:
            self.peak_equity = account_state.equity

        # Track tick timing
        if tick is not None:
            now_sec = tick.timestamp_ns / 1e9 if tick.timestamp_ns > 1e12 else time.time()
            if self.last_tick_time > 0 and (now_sec - self.last_tick_time) > self.stale_quote_seconds:
                dt = now_sec - self.last_tick_time
                stale_msg = f"STALE_QUOTE: No ticks for {dt:.2f}s"
                if stale_msg not in self.tripped_breakers:
                    self.tripped_breakers.append(stale_msg)
            self.last_tick_time = now_sec

        context: Dict[str, Any] = {
            "peak_equity": self.peak_equity,
            "day_start_equity": self.day_start_equity,
            "typical_spread": self.typical_spread,
        }

        newly_tripped: List[str] = []
        for breaker in self.breakers:
            res = breaker.evaluate(tick, account_state, context)
            if res:
                newly_tripped.append(res)
                if res not in self.tripped_breakers:
                    self.tripped_breakers.append(res)

        return newly_tripped

    def check_tick(self, current_time: float, bid: float, ask: float) -> Optional[str]:
        """
        Compatibility method with contract_harness CircuitBreakerManager.
        Checks for stale quotes and extreme spread spikes.
        """
        dt = current_time - self.last_tick_time if self.last_tick_time > 0 else 0.0
        self.last_tick_time = current_time

        if self.last_tick_time > 0 and dt > self.stale_quote_seconds:
            msg = f"STALE_QUOTE: No ticks for {dt:.2f}s"
            self.tripped_breakers.append(msg)
            return msg

        spread = ask - bid
        ref_spread = self.typical_spread if self.typical_spread > 0 else self.median_spread
        if ref_spread > 0 and spread > self.spread_multiplier_limit * ref_spread:
            msg = f"EXTREME_SPREAD: {spread:.4f} > {self.spread_multiplier_limit}x median"
            self.tripped_breakers.append(msg)
            return msg

        return None

    def check_equity(self, current_equity: float) -> Optional[str]:
        """
        Compatibility method with contract_harness CircuitBreakerManager.
        Checks for maximum drawdown and daily loss.
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # Max drawdown
        dd_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0
        if dd_pct >= self.max_drawdown_pct:
            msg = f"MAX_DRAWDOWN: Current DD {dd_pct:.2f}% >= limit {self.max_drawdown_pct}%"
            self.tripped_breakers.append(msg)
            return msg

        # Daily loss
        daily_loss_pct = (
            ((self.day_start_equity - current_equity) / self.day_start_equity) * 100.0
            if self.day_start_equity > 0
            else 0
        )
        if daily_loss_pct >= self.daily_loss_pct:
            msg = f"DAILY_LOSS: Daily loss {daily_loss_pct:.2f}% >= limit {self.daily_loss_pct}%"
            self.tripped_breakers.append(msg)
            return msg

        return None

    def reset_all(self) -> None:
        """Resets all breakers and cleared tripped list."""
        self.tripped_breakers.clear()
        for b in self.breakers:
            b.reset()
