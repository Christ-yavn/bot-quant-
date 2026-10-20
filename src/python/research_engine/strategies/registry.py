"""
src.strategies.registry
=======================
Central Hypothesis Registry & Multiple Testing Correction Engine (F7).

Features:
- Global trial counter M preventing data snooping and p-hacking
- Benjamini-Hochberg (1995) step-up procedure for False Discovery Rate (FDR) control
- Holm-Bonferroni (1979) step-down procedure for Family-Wise Error Rate (FWER) control
- Adjusted p-values (q-values) computation
- Polars DataFrame catalog export and evaluation reports
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import polars as pl

logger = logging.getLogger("src.strategies.registry")


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> List[bool]:
    """
    Benjamini-Hochberg procedure for controlling the False Discovery Rate (FDR).
    Conforms to PROJECT.md § 5, contract_harness.py, and Survey Math § 4.3.

    Parameters
    ----------
    p_values : Sequence[float]
        Unadjusted p-values from M statistical hypothesis tests.
    alpha : float, default 0.05
        Target FDR significance threshold Q*.

    Returns
    -------
    List[bool]
        Boolean list indicating hypothesis rejection (True = statistically significant edge).
    """
    m = len(p_values)
    if m == 0:
        return []

    p_arr = np.asarray(p_values, dtype=np.float64)
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]

    thresholds = (np.arange(1, m + 1) / m) * alpha
    significant = sorted_p <= thresholds

    rejected_sorted = np.zeros(m, dtype=bool)
    if np.any(significant):
        max_k = np.max(np.where(significant)[0])
        rejected_sorted[: max_k + 1] = True

    rejected = np.zeros(m, dtype=bool)
    rejected[sorted_indices] = rejected_sorted
    return rejected.tolist()


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> List[bool]:
    """
    Holm-Bonferroni step-down procedure for Family-Wise Error Rate (FWER).
    Strict conservative control against any false positive across M tests.

    Parameters
    ----------
    p_values : Sequence[float]
        Unadjusted p-values from M hypothesis tests.
    alpha : float, default 0.05
        Target FWER significance threshold.

    Returns
    -------
    List[bool]
        Boolean list indicating hypothesis rejection (True = statistically significant edge).
    """
    m = len(p_values)
    if m == 0:
        return []

    p_arr = np.asarray(p_values, dtype=np.float64)
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]

    rejected_sorted = np.zeros(m, dtype=bool)
    for i in range(m):
        threshold = alpha / (m - i)
        if sorted_p[i] <= threshold:
            rejected_sorted[i] = True
        else:
            break

    rejected = np.zeros(m, dtype=bool)
    rejected[sorted_indices] = rejected_sorted
    return rejected.tolist()


def compute_adjusted_p_values_bh(p_values: Sequence[float]) -> List[float]:
    """
    Computes Benjamini-Hochberg adjusted p-values (q-values).

    Parameters
    ----------
    p_values : Sequence[float]
        Raw p-values.

    Returns
    -------
    List[float]
        Adjusted p-values clamped to [0.0, 1.0].
    """
    m = len(p_values)
    if m == 0:
        return []

    p_arr = np.asarray(p_values, dtype=np.float64)
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]

    adj_p = np.zeros(m, dtype=np.float64)
    adj_p[-1] = sorted_p[-1]

    for i in range(m - 2, -1, -1):
        rank = i + 1
        adj_val = (m / rank) * sorted_p[i]
        adj_p[i] = min(adj_p[i + 1], adj_val)

    adj_p = np.clip(adj_p, 0.0, 1.0)
    result = np.zeros(m, dtype=np.float64)
    result[sorted_indices] = adj_p
    return result.tolist()


def compute_adjusted_p_values_holm(p_values: Sequence[float]) -> List[float]:
    """
    Computes Holm-Bonferroni adjusted p-values.

    Parameters
    ----------
    p_values : Sequence[float]
        Raw p-values.

    Returns
    -------
    List[float]
        Adjusted p-values clamped to [0.0, 1.0].
    """
    m = len(p_values)
    if m == 0:
        return []

    p_arr = np.asarray(p_values, dtype=np.float64)
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]

    adj_p = np.zeros(m, dtype=np.float64)
    running_max = 0.0

    for i in range(m):
        multiplier = m - i
        val = multiplier * sorted_p[i]
        running_max = max(running_max, val)
        adj_p[i] = running_max

    adj_p = np.clip(adj_p, 0.0, 1.0)
    result = np.zeros(m, dtype=np.float64)
    result[sorted_indices] = adj_p
    return result.tolist()


@dataclass
class TrialRecord:
    trial_id: int
    strategy_id: str
    symbol: str
    params: str
    p_value: float
    t_stat: float
    sharpe: float
    notes: str
    registered_at_utc: str


class TrialRegistry:
    """
    Central hypothesis registry tracking trial count M across all strategy candidates,
    asset combinations, and hyperparameter grids (PROJECT.md § 5, F7).
    """

    def __init__(self, name: str = "CentralTrialRegistry") -> None:
        self.name = name
        self._trials: List[TrialRecord] = []
        self._counter: int = 0

    @property
    def trial_count(self) -> int:
        """Returns the total number of registered trials M."""
        return self._counter

    def register_trial(
        self,
        strategy_id: str,
        symbol: str,
        params: Union[Dict[str, Any], str],
        p_value: float,
        t_stat: float = 0.0,
        sharpe: float = 0.0,
        notes: str = "",
    ) -> int:
        """
        Registers a new hypothesis trial and increments the central counter M.

        Parameters
        ----------
        strategy_id : str
            Strategy identifier (e.g. "PostSpikeDrift", "HawkesPrecursor").
        symbol : str
            Deriv index symbol (e.g. "Boom 1000 Index").
        params : dict or str
            Hyperparameter dictionary.
        p_value : float
            Empirical p-value of the test against H0.
        t_stat : float, default 0.0
            Observed test t-statistic.
        sharpe : float, default 0.0
            Annualized Sharpe Ratio or performance metric.
        notes : str, optional
            Additional observations.

        Returns
        -------
        int
            Assigned trial_id (1-indexed).
        """
        self._counter += 1
        param_str = json.dumps(params) if isinstance(params, dict) else str(params)

        record = TrialRecord(
            trial_id=self._counter,
            strategy_id=strategy_id,
            symbol=symbol,
            params=param_str,
            p_value=float(p_value),
            t_stat=float(t_stat),
            sharpe=float(sharpe),
            notes=notes,
            registered_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._trials.append(record)
        return self._counter

    def get_trials(self) -> pl.DataFrame:
        """
        Returns the registered trials catalog as a Polars DataFrame.

        Returns
        -------
        pl.DataFrame
            Registered trials.
        """
        if not self._trials:
            return pl.DataFrame({
                "trial_id": pl.Series([], dtype=pl.Int64),
                "strategy_id": pl.Series([], dtype=pl.Utf8),
                "symbol": pl.Series([], dtype=pl.Utf8),
                "params": pl.Series([], dtype=pl.Utf8),
                "p_value": pl.Series([], dtype=pl.Float64),
                "t_stat": pl.Series([], dtype=pl.Float64),
                "sharpe": pl.Series([], dtype=pl.Float64),
                "notes": pl.Series([], dtype=pl.Utf8),
                "registered_at_utc": pl.Series([], dtype=pl.Utf8),
            })

        return pl.DataFrame([asdict(t) for t in self._trials])

    def evaluate_hypotheses(self, alpha: float = 0.05) -> pl.DataFrame:
        """
        Evaluates Benjamini-Hochberg (FDR) and Holm-Bonferroni (FWER) corrections
        across all registered trials M.

        Parameters
        ----------
        alpha : float, default 0.05
            Family significance level.

        Returns
        -------
        pl.DataFrame
            DataFrame with trial details plus significance flags and adjusted p-values.
        """
        df = self.get_trials()
        if len(df) == 0:
            return df.with_columns([
                pl.Series("fdr_significant", [], dtype=pl.Boolean),
                pl.Series("fwer_significant", [], dtype=pl.Boolean),
                pl.Series("bh_adjusted_p", [], dtype=pl.Float64),
                pl.Series("holm_adjusted_p", [], dtype=pl.Float64),
            ])

        p_vals = df["p_value"].to_list()
        fdr_flags = benjamini_hochberg(p_vals, alpha=alpha)
        fwer_flags = holm_bonferroni(p_vals, alpha=alpha)
        bh_adj = compute_adjusted_p_values_bh(p_vals)
        holm_adj = compute_adjusted_p_values_holm(p_vals)

        return df.with_columns([
            pl.Series("fdr_significant", fdr_flags, dtype=pl.Boolean),
            pl.Series("fwer_significant", fwer_flags, dtype=pl.Boolean),
            pl.Series("bh_adjusted_p", bh_adj, dtype=pl.Float64),
            pl.Series("holm_adjusted_p", holm_adj, dtype=pl.Float64),
        ])

    def summary(self, alpha: float = 0.05) -> Dict[str, Any]:
        """
        Computes high-level summary statistics of the registry.

        Parameters
        ----------
        alpha : float, default 0.05
            Significance level.

        Returns
        -------
        dict
            Summary metrics.
        """
        evaluated = self.evaluate_hypotheses(alpha=alpha)
        total = len(evaluated)
        fdr_count = int(evaluated["fdr_significant"].sum()) if total > 0 else 0
        fwer_count = int(evaluated["fwer_significant"].sum()) if total > 0 else 0
        min_p = float(evaluated["p_value"].min()) if total > 0 else 1.0
        max_p = float(evaluated["p_value"].max()) if total > 0 else 1.0

        return {
            "registry_name": self.name,
            "total_trials_M": total,
            "alpha": alpha,
            "fdr_discoveries": fdr_count,
            "fwer_discoveries": fwer_count,
            "min_p_value": min_p,
            "max_p_value": max_p,
        }

    def reset(self) -> None:
        """Resets the registry, clearing all registered trials."""
        self._trials.clear()
        self._counter = 0
