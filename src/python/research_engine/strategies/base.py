"""
src.strategies.base
===================
Base strategy interface and signal types for quantitative research on Deriv synthetics.

Compliant with PROJECT.md §2.A, §5.C, and survey_math_models.md §3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from src.backtest.portfolio import AccountState, OrderRequest
from src.data.schema import TickRecord
from src.strategies.registry import TrialRegistry


class SignalType(Enum):
    BUY = 1
    SELL = -1
    CLOSE_ALL = 0
    SCALE_OUT = 2
    HOLD = 3


class StrategyInterface(ABC):
    """
    Abstract Base Class for all quantitative trading strategies.
    Receives market ticks and portfolio state; outputs a list of OrderRequests.
    """

    def __init__(self, name: str = "BaseStrategy", params: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.params: Dict[str, Any] = params or {}

    @abstractmethod
    def on_tick(self, tick: TickRecord, portfolio_state: AccountState) -> List[OrderRequest]:
        """
        Processes a single tick in discrete time and returns a list of orders to submit.
        Zero-lookahead: orders will be executed on the subsequent tick (t+1).
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Resets any internal strategy state between runs."""
        pass

    def get_params(self) -> Dict[str, Any]:
        """Returns the dictionary of strategy parameters."""
        return dict(self.params)

    def register_with_trial_registry(
        self,
        registry: TrialRegistry,
        symbol: str,
        p_value: float,
        t_stat: float = 0.0,
        sharpe: float = 0.0,
        notes: str = "",
    ) -> int:
        """
        Registers this strategy's trial execution in the Central Hypothesis Registry
        to ensure rigorous Multiple Testing Correction (F7, FDR/FWER).
        """
        return registry.register_trial(
            strategy_id=self.name,
            symbol=symbol,
            params=self.params,
            p_value=p_value,
            t_stat=t_stat,
            sharpe=sharpe,
            notes=notes,
        )
