#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PHASE 2 QUANTITATIVE SCANNER: HURST EXPONENT & ORNSTEIN-UHLENBECK ESTIMATOR
===============================================================================
Calibrates mean-reverting vs trending properties on financial & synthetic series:
1. Rescaled Range (R/S) Hurst Exponent:
   - H < 0.45 : Mean-reverting (Anti-persistent, Ornstein-Uhlenbeck candidate)
   - 0.45 <= H <= 0.55 : Geometric Brownian Motion (Random Walk / Martingale)
   - H > 0.55 : Trending / Persistent (Momentum / Trend Following candidate)
2. Ornstein-Uhlenbeck Parameter Calibration:
   - dX_t = theta * (mu - X_t) dt + sigma * dW_t
   - Half-life of mean reversion: t_half = ln(2) / theta
===============================================================================
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

def compute_hurst_exponent(ts: np.ndarray, max_lags: int = 100) -> float:
    """Computes the Hurst Exponent using Rescaled Range (R/S) analysis."""
    lags = range(2, max_lags)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def fit_ornstein_uhlenbeck(ts: np.ndarray, dt: float = 1.0):
    x = ts[:-1]
    y = ts[1:]

    # OLS regression: y = a*x + b
    p = np.polyfit(x, y, 1)
    a, b = p[0], p[1]

    if a >= 1.0 or a <= 0.0:
        return {"mean_reverting": False, "theta": 0.0, "mu": np.mean(ts), "half_life": np.inf}

    theta = -np.log(a) / dt
    mu = b / (1.0 - a)
    half_life = np.log(2.0) / theta

    residuals = y - (a * x + b)
    sigma = np.std(residuals) * np.sqrt(-2.0 * np.log(a) / (dt * (1.0 - a**2)))

    return {
        "mean_reverting": True,
        "theta": theta,
        "mu": mu,
        "sigma": sigma,
        "half_life": half_life
    }

def main():
    print("="*75)
    print("PHASE 2 QUANT SCANNER: HURST EXPONENT & OU MEAN-REVERSION CALIBRATION")
    print("="*75)
    data_dir = Path(__file__).resolve().parent.parent / "harvested_data"
    if not data_dir.exists():
        print(f"[!] No harvested data directory found at {data_dir}.")
        print("[!] Please run extract_historical_step_volatilities.py first.")
        return

    csv_files = list(data_dir.glob("*_M1_*.csv"))
    if not csv_files:
        print("[!] No M1 CSV files found. Waiting for data extraction.")
        return

    results = []
    for f in csv_files:
        symbol = f.name.split("_M1_")[0]
        df = pd.read_csv(f)
        if "close" not in df.columns:
            continue
        closes = df["close"].values
        h = compute_hurst_exponent(closes, max_lags=60)
        ou = fit_ornstein_uhlenbeck(closes, dt=1.0)

        regime = "MEAN_REVERTING" if h < 0.45 else ("TRENDING" if h > 0.55 else "RANDOM_WALK")
        results.append({
            "symbol": symbol,
            "hurst_H": round(h, 4),
            "regime": regime,
            "ou_half_life_min": round(ou["half_life"], 2) if ou["mean_reverting"] else "N/A",
            "ou_theta": round(ou["theta"], 5) if ou["mean_reverting"] else "N/A"
        })

    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))

if __name__ == "__main__":
    main()
