"""
src.strategies
==============
Quantitative trading strategies, hypothesis registry, and multiple testing corrections.
"""

from src.strategies.alternative_quant import (
    StepMeanReversionStrategy,
    VolatilityBreakoutStrategy,
)
from src.strategies.base import SignalType, StrategyInterface
from src.strategies.registry import (
    TrialRecord,
    TrialRegistry,
    benjamini_hochberg,
    compute_adjusted_p_values_bh,
    compute_adjusted_p_values_holm,
    holm_bonferroni,
)
from src.strategies.user_post_spike import UserPostSpikeStrategy

__all__ = [
    # Multiple testing registry
    "benjamini_hochberg",
    "holm_bonferroni",
    "compute_adjusted_p_values_bh",
    "compute_adjusted_p_values_holm",
    "TrialRegistry",
    "TrialRecord",
    # Base strategy contracts
    "SignalType",
    "StrategyInterface",
    # Strategies
    "UserPostSpikeStrategy",
    "StepMeanReversionStrategy",
    "VolatilityBreakoutStrategy",
]
