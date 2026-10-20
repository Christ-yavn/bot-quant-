"""
src.backtest.metrics
====================
Statistical and financial performance metrics evaluation for backtested trading strategies.

Calculates:
- Net expectancy & stationary bootstrap 95% confidence intervals
- Win rate, loss rate, payoff ratio
- Profit factor, gross profit, gross loss
- Maximum drawdown (USD and percentage)
- Sharpe ratio & Sortino ratio
- Liquidation stop-out counts and trade distribution
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


def bootstrap_net_expectancy(
    pnls: Sequence[float],
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Computes stationary bootstrap confidence interval for net trade expectancy.
    
    Returns:
        (mean_pnl, ci_lower, ci_upper)
    """
    if len(pnls) == 0:
        return 0.0, 0.0, 0.0

    arr = np.asarray(pnls, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(arr)
    boot_means = np.empty(n_bootstrap, dtype=np.float64)

    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    alpha = 1.0 - ci
    ci_lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return float(np.mean(arr)), ci_lower, ci_upper


def calculate_drawdowns(
    equity_curve: Sequence[Tuple[int, float]],
    initial_balance: float = 1000.0,
) -> Tuple[float, float]:
    """
    Computes maximum peak-to-trough drawdown in USD and percentage from an equity trajectory.
    
    Returns:
        (max_drawdown_usd, max_drawdown_pct)
    """
    if not equity_curve:
        return 0.0, 0.0

    equities = np.array([eq for _, eq in equity_curve], dtype=np.float64)
    if len(equities) == 0:
        return 0.0, 0.0

    running_max = np.maximum.accumulate(equities)
    # Ensure running_max is at least initial balance if start is lower
    running_max = np.maximum(running_max, initial_balance)

    drawdowns_usd = running_max - equities
    max_dd_usd = float(np.max(drawdowns_usd)) if len(drawdowns_usd) > 0 else 0.0

    # Avoid zero-division in percentage calculation
    safe_peaks = np.where(running_max > 0, running_max, 1.0)
    drawdowns_pct = (drawdowns_usd / safe_peaks) * 100.0
    max_dd_pct = float(np.max(drawdowns_pct)) if len(drawdowns_pct) > 0 else 0.0

    return max(0.0, max_dd_usd), max(0.0, max_dd_pct)


def calculate_sharpe_ratio(
    pnls: Sequence[float],
    risk_free_rate: float = 0.0,
) -> float:
    """
    Calculates per-trade Sharpe Ratio:
        Sharpe = (mean(pnls) - rf) / std(pnls)
    """
    if len(pnls) < 2:
        return 0.0
    arr = np.asarray(pnls, dtype=np.float64)
    std_pnl = float(np.std(arr, ddof=1))
    if std_pnl <= 1e-12:
        return 0.0
    return float((np.mean(arr) - risk_free_rate) / std_pnl)


def calculate_sortino_ratio(
    pnls: Sequence[float],
    target_return: float = 0.0,
) -> float:
    """
    Calculates Sortino Ratio based on downside semi-deviation:
        Sortino = (mean(pnls) - target) / downside_deviation
    """
    if len(pnls) < 2:
        return 0.0
    arr = np.asarray(pnls, dtype=np.float64)
    downside_diff = np.minimum(0.0, arr - target_return)
    downside_variance = float(np.mean(downside_diff ** 2))
    downside_dev = math.sqrt(downside_variance)
    if downside_dev <= 1e-12:
        return 0.0
    return float((np.mean(arr) - target_return) / downside_dev)


def calculate_backtest_metrics(
    closed_trades: Sequence[Dict[str, Any]],
    equity_curve: Sequence[Tuple[int, float]],
    initial_balance: float = 1000.0,
    stop_outs_count: int = 0,
) -> Dict[str, Any]:
    """
    Comprehensive performance metrics evaluation of a completed backtest run.
    """
    total_trades = len(closed_trades)
    if total_trades == 0:
        max_dd_usd, max_dd_pct = calculate_drawdowns(equity_curve, initial_balance)
        final_equity = equity_curve[-1][1] if equity_curve else initial_balance
        return {
            "total_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "breakeven_trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "net_expectancy": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "total_net_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "payoff_ratio": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_usd": max_dd_usd,
            "max_drawdown_pct": max_dd_pct,
            "initial_balance": initial_balance,
            "final_balance": initial_balance,
            "final_equity": final_equity,
            "return_pct": 0.0,
            "stop_outs_count": stop_outs_count,
        }

    pnls = [float(t["net_pnl"]) for t in closed_trades]
    pnl_arr = np.array(pnls, dtype=np.float64)

    wins = pnl_arr[pnl_arr > 0]
    losses = pnl_arr[pnl_arr < 0]
    breakevens = pnl_arr[pnl_arr == 0]

    n_wins = len(wins)
    n_losses = len(losses)
    n_be = len(breakevens)

    win_rate = n_wins / total_trades
    loss_rate = n_losses / total_trades

    mean_pnl, ci_lower, ci_upper = bootstrap_net_expectancy(pnls)

    gross_profit = float(np.sum(wins)) if n_wins > 0 else 0.0
    gross_loss = float(abs(np.sum(losses))) if n_losses > 0 else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    avg_win = float(np.mean(wins)) if n_wins > 0 else 0.0
    avg_loss = float(abs(np.mean(losses))) if n_losses > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if avg_win > 0 else 0.0)

    sharpe = calculate_sharpe_ratio(pnls)
    sortino = calculate_sortino_ratio(pnls)

    max_dd_usd, max_dd_pct = calculate_drawdowns(equity_curve, initial_balance)
    final_equity = equity_curve[-1][1] if equity_curve else (initial_balance + float(np.sum(pnl_arr)))
    total_net_pnl = float(np.sum(pnl_arr))
    final_balance = initial_balance + total_net_pnl
    return_pct = ((final_equity - initial_balance) / initial_balance) * 100.0 if initial_balance > 0 else 0.0

    return {
        "total_trades": total_trades,
        "win_trades": n_wins,
        "loss_trades": n_losses,
        "breakeven_trades": n_be,
        "win_rate": win_rate,
        "loss_rate": loss_rate,
        "net_expectancy": mean_pnl,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "total_net_pnl": total_net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": payoff_ratio,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "final_equity": final_equity,
        "return_pct": return_pct,
        "stop_outs_count": stop_outs_count,
    }
