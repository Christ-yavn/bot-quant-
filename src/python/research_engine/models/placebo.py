"""
src.models.placebo
==================
Parametric Moment-Matched Placebo Generator (F6).

Features:
- Parametric calibration on empirical training ticks:
  * Drift mean (mu) and diffusion variance (sigma)
  * Jump arrival Poisson intensity (lambda_jump)
  * Jump magnitude distribution moments (jump_mean, jump_std)
- Memoryless PRNG synthetic trajectory generation (pure null hypothesis, zero predictive alpha)
- Strict compliance with TICK_SCHEMA and positive price invariants
- Moment matching and diagnostic autocorrelation verification
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import polars as pl

from src.data.schema import TICK_SCHEMA

logger = logging.getLogger("src.models.placebo")


class PlaceboGenerator:
    """
    Parametric Placebo Generator (PROJECT.md § 5.B, F6).

    Calibrates on empirical training ticks:
    - Poisson jump frequency lambda
    - Jump magnitude distribution (mean, std)
    - Continuous drift mu and diffusion sigma

    Generates synthetic null ticks with matching empirical moments but
    rigorously zero predictive alpha (pure memoryless renewal/martingale process).
    """

    def __init__(self) -> None:
        self.mu: float = 0.0
        self.sigma: float = 0.001
        self.lambda_jump: float = 0.001
        self.jump_mean: float = 0.0
        self.jump_std: float = 1.0
        self.initial_price: float = 1000.0
        self.mean_spread: float = 0.1
        self.symbol: str = "Synthetic"
        self._is_fitted: bool = False

    def fit(self, train_ticks: pl.DataFrame, spike_threshold: Optional[float] = None) -> "PlaceboGenerator":
        """
        Calibrates jump-diffusion moments from empirical tick data.

        Parameters
        ----------
        train_ticks : pl.DataFrame
            Historical training ticks conforming to TICK_SCHEMA.
        spike_threshold : float, optional
            Absolute price increment threshold |Delta P| to classify a tick as a spike/jump.
            If None, adaptively calibrated from empirical drift median for Boom/Crash indices.

        Returns
        -------
        PlaceboGenerator
            Fitted instance.
        """
        if len(train_ticks) == 0:
            logger.warning("Empty training DataFrame provided to PlaceboGenerator.fit(). Keeping defaults.")
            return self

        prices = train_ticks["last"].to_numpy()
        self.symbol = (
            str(train_ticks["symbol"][0])
            if "symbol" in train_ticks.columns and len(train_ticks["symbol"]) > 0
            else "Synthetic"
        )
        self.initial_price = float(prices[0])
        if "ask" in train_ticks.columns and "bid" in train_ticks.columns:
            sp = float((train_ticks["ask"] - train_ticks["bid"]).mean())
            self.mean_spread = sp if sp > 0 else 0.1

        diffs = np.diff(prices)
        if len(diffs) == 0:
            self._is_fitted = True
            return self

        if spike_threshold is not None:
            eff_thresh = float(spike_threshold)
        else:
            med_abs = float(np.median(np.abs(diffs)))
            sym_low = self.symbol.lower()
            if ("boom" in sym_low or "crash" in sym_low) and med_abs > 1e-6:
                eff_thresh = max(0.05, 5.0 * med_abs)
            else:
                eff_thresh = 5.0

        is_spike = np.abs(diffs) >= eff_thresh
        spike_diffs = diffs[is_spike]
        drift_diffs = diffs[~is_spike]

        # Poisson jump intensity per tick
        self.lambda_jump = float(np.mean(is_spike)) if len(diffs) > 0 else 0.001

        # Jump distribution moments
        if len(spike_diffs) > 0:
            self.jump_mean = float(np.mean(spike_diffs))
            raw_std = float(np.std(spike_diffs))
            self.jump_std = raw_std if raw_std > 0 else 1.0
        else:
            self.jump_mean = 0.0
            self.jump_std = 1.0

        # Continuous drift and diffusion moments
        if len(drift_diffs) > 0:
            self.mu = float(np.mean(drift_diffs))
            raw_sigma = float(np.std(drift_diffs))
            self.sigma = raw_sigma if raw_sigma > 0 else 0.001
        else:
            self.mu = 0.0
            self.sigma = 0.001

        self._is_fitted = True
        logger.info(
            f"Fitted PlaceboGenerator for '{self.symbol}': mu={self.mu:.6f}, "
            f"sigma={self.sigma:.6f}, lambda_jump={self.lambda_jump:.6f}, "
            f"jump_mean={self.jump_mean:.4f}, jump_std={self.jump_std:.4f}, spread={self.mean_spread:.4f}"
        )
        return self

    def generate(
        self,
        n_ticks: int,
        seed: int = 42,
        base_ts_ns: int = 1_700_000_000_000_000_000,
        step_ns: int = 1_000_000_000,
        spread: Optional[float] = None,
    ) -> pl.DataFrame:
        """
        Generates synthetic null ticks under the pure null hypothesis H0.

        Parameters
        ----------
        n_ticks : int
            Number of ticks to simulate.
        seed : int, default 42
            PRNG seed for strict reproducibility.
        base_ts_ns : int, default 1_700_000_000_000_000_000
            Starting timestamp in nanoseconds.
        step_ns : int, default 1_000_000_000
            Nanosecond interval between ticks.
        spread : float, optional
            Bid/Ask spread width. Defaults to calibrated empirical mean_spread.

        Returns
        -------
        pl.DataFrame
            Simulated ticks conforming to TICK_SCHEMA.
        """
        if n_ticks <= 0:
            return pl.DataFrame(schema=TICK_SCHEMA)

        eff_spread = float(spread) if spread is not None else self.mean_spread

        rng = np.random.default_rng(seed)
        prices = np.zeros(n_ticks, dtype=np.float64)
        prices[0] = self.initial_price

        if n_ticks > 1:
            n_steps = n_ticks - 1
            # Simulate compound Poisson jump process + drift
            jumps = rng.random(n_steps) < self.lambda_jump
            sym_low = self.symbol.lower()
            if ("boom" in sym_low or "crash" in sym_low) and abs(self.jump_mean) > 1e-6:
                # One-sided exponential jump matching empirical mean magnitude and polarity
                sign = 1.0 if self.jump_mean > 0 else -1.0
                jump_sizes = sign * rng.exponential(scale=abs(self.jump_mean), size=n_steps)
            else:
                jump_sizes = rng.normal(self.jump_mean, max(self.jump_std, 1e-6), n_steps)
            drift_sizes = rng.normal(self.mu, max(self.sigma, 1e-6), n_steps)

            increments = np.where(jumps, jump_sizes, drift_sizes)
            prices[1:] = self.initial_price + np.cumsum(increments)

        # Enforce strictly positive prices (cannot be zero or negative)
        prices = np.maximum(prices, 0.01)

        timestamps = base_ts_ns + np.arange(n_ticks, dtype=np.int64) * step_ns
        half_spread = eff_spread / 2.0
        bids = np.maximum(prices - half_spread, 0.001)
        asks = prices + half_spread

        df = pl.DataFrame({
            "timestamp_ns": timestamps,
            "symbol": [self.symbol] * n_ticks,
            "bid": bids,
            "ask": asks,
            "last": prices,
            "volume": [1.0] * n_ticks,
            "flags": pl.Series([6] * n_ticks, dtype=pl.UInt32),
        })

        return df

    def summary(self) -> Dict[str, Any]:
        """Returns a dictionary of calibrated parameters."""
        return {
            "symbol": self.symbol,
            "initial_price": self.initial_price,
            "mu": self.mu,
            "sigma": self.sigma,
            "lambda_jump": self.lambda_jump,
            "jump_mean": self.jump_mean,
            "jump_std": self.jump_std,
            "is_fitted": self._is_fitted,
        }

    @staticmethod
    def compute_autocorrelation(ticks_df: pl.DataFrame, lag: int = 1) -> float:
        """
        Computes the empirical autocorrelation of price increments at specified lag.
        Used to verify zero serial correlation under the null hypothesis.

        Parameters
        ----------
        ticks_df : pl.DataFrame
            Tick DataFrame containing the 'last' price column.
        lag : int, default 1
            Lag order.

        Returns
        -------
        float
            Empirical autocorrelation coefficient in [-1.0, 1.0].
        """
        if len(ticks_df) <= lag + 2:
            return 0.0
        prices = ticks_df["last"].to_numpy()
        diffs = np.diff(prices)
        if len(diffs) <= lag:
            return 0.0
        x1 = diffs[:-lag]
        x2 = diffs[lag:]
        std1 = np.std(x1)
        std2 = np.std(x2)
        if std1 == 0 or std2 == 0:
            return 0.0
        corr = float(np.corrcoef(x1, x2)[0, 1])
        return 0.0 if np.isnan(corr) else corr
