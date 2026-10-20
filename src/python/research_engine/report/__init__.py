"""
src.report
==========
Quantitative Evaluation Pipeline, Ruin Theory & Research Report Generation.

Modules:
- ruin_theory: Cramér-Lundberg analytical bounds, Pollaczek-Khinchine formula, Monte Carlo ruin simulations
- hypothesis_tests: Out-of-sample sealed test evaluation, bootstrap 95% CIs, placebo comparisons, FDR/FWER
- generate_report: Comprehensive French quantitative research report compilation
"""

from src.report.generate_report import (
    build_full_research_report,
    generate_french_report,
    get_dgp_name_for_symbol,
)
from src.report.hypothesis_tests import (
    bootstrap_confidence_interval,
    bootstrap_net_expectancy,
    compare_against_placebo,
    evaluate_out_of_sample,
    get_default_strategy_for_symbol,
)
from src.report.ruin_theory import (
    cramer_lundberg_bound,
    cramer_lundberg_ruin_prob,
    evaluate_capital_ladder,
    monte_carlo_ruin_prob,
    monte_carlo_ruin_probability,
    pollaczek_khinchine_ruin_prob,
    time_to_ruin_distribution,
)

__all__ = [
    # Ruin Theory
    "cramer_lundberg_bound",
    "cramer_lundberg_ruin_prob",
    "pollaczek_khinchine_ruin_prob",
    "monte_carlo_ruin_probability",
    "monte_carlo_ruin_prob",
    "evaluate_capital_ladder",
    "time_to_ruin_distribution",
    # Hypothesis Tests
    "bootstrap_confidence_interval",
    "bootstrap_net_expectancy",
    "compare_against_placebo",
    "evaluate_out_of_sample",
    "get_default_strategy_for_symbol",
    # Report Generation
    "generate_french_report",
    "build_full_research_report",
    "get_dgp_name_for_symbol",
]
