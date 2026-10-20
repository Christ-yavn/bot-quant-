# -*- coding: utf-8 -*-
"""
Stationary Block Bootstrap Validation Engine for V8 "Spike Hunter Convexe"
Direction de la Recherche Quantitative — L99 / BEASTMODE Standard
Implements Politis & Romano (1994) Stationary Bootstrap with 10,000 resamples.
"""

import json
import os
import numpy as np
import pandas as pd

def run_stationary_bootstrap():
    v7_closed_path = r'C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\data_summaries\v7\v7_closed_positions.csv'
    v7_rev_path    = r'C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\data_summaries\v7\reverse_strategy_simulation.csv'
    out_dir        = r'C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\data_summaries\v8'
    os.makedirs(out_dir, exist_ok=True)

    df_rev = pd.read_csv(v7_rev_path)
    df_closed = pd.read_csv(v7_closed_path)

    pnl_series = df_rev['reverse_net_pnl'].values
    n = len(pnl_series)
    print(f"Loaded {n} trades from reverse strategy simulation.")

    # 1. Baseline Performance Metrics
    total_pnl = np.sum(pnl_series)
    wins = pnl_series[pnl_series > 0]
    losses = pnl_series[pnl_series <= 0]
    win_rate = len(wins) / n
    avg_win = np.mean(wins) if len(wins) > 0 else 0.0
    avg_loss = np.abs(np.mean(losses)) if len(losses) > 0 else 0.0
    payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    gross_profit = np.sum(wins)
    gross_loss = np.abs(np.sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    # Max Drawdown calculation
    cum_pnl = np.cumsum(pnl_series)
    peak = np.maximum.accumulate(cum_pnl)
    drawdowns = peak - cum_pnl
    max_dd = np.max(drawdowns)

    # Trade Sharpe
    std_pnl = np.std(pnl_series, ddof=1)
    trade_sharpe = (np.mean(pnl_series) / std_pnl) if std_pnl > 0 else 0.0
    # Annualized Sharpe (assuming ~1,242 trades over 24h = ~453,330 trades/year)
    ann_sharpe = trade_sharpe * np.sqrt(453330)

    print("\n=== BASELINE METRICS (V8 REVERSE ON 1,242 TRADES) ===")
    print(f"Total Cumulative P&L : +${total_pnl:.2f} USD")
    print(f"Win Rate             : {win_rate*100:.2f}% ({len(wins)}/{n})")
    print(f"Average Win          : +${avg_win:.2f} USD")
    print(f"Average Loss         : -${avg_loss:.2f} USD")
    print(f"Payoff Ratio (R)     : {payoff_ratio:.2f}")
    print(f"Profit Factor        : {profit_factor:.2f}")
    print(f"Trade Sharpe         : {trade_sharpe:.4f}")
    print(f"Max Drawdown ($)     : ${max_dd:.2f} USD")

    # 2. Stationary Block Bootstrap (Politis & Romano 1994)
    # Mean block length b = 15 trades (captures clustering of Hawkes events)
    np.random.seed(20261020)
    num_bootstrap = 10000
    mean_block_len = 15.0
    p_geom = 1.0 / mean_block_len

    boot_pnl = np.zeros(num_bootstrap)
    boot_wr = np.zeros(num_bootstrap)
    boot_pf = np.zeros(num_bootstrap)
    boot_sharpe = np.zeros(num_bootstrap)
    boot_max_dd = np.zeros(num_bootstrap)

    print(f"\nExecuting {num_bootstrap} Stationary Bootstrap resamples (mean block length = {mean_block_len})...")
    for b in range(num_bootstrap):
        # Generate stationary bootstrap sample indices
        indices = np.zeros(n, dtype=int)
        idx = np.random.randint(0, n)
        for i in range(n):
            if np.random.rand() < p_geom:
                idx = np.random.randint(0, n)
            else:
                idx = (idx + 1) % n
            indices[i] = idx

        resampled_pnl = pnl_series[indices]
        boot_pnl[b] = np.sum(resampled_pnl)
        w = resampled_pnl[resampled_pnl > 0]
        l = resampled_pnl[resampled_pnl <= 0]
        boot_wr[b] = len(w) / n
        gp = np.sum(w)
        gl = np.abs(np.sum(l))
        boot_pf[b] = gp / gl if gl > 0 else 0.0

        s = np.std(resampled_pnl, ddof=1)
        boot_sharpe[b] = (np.mean(resampled_pnl) / s) if s > 0 else 0.0

        cum = np.cumsum(resampled_pnl)
        pk = np.maximum.accumulate(cum)
        boot_max_dd[b] = np.max(pk - cum)

    # Quantiles
    quantiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    quant_labels = ['Q1%', 'Q5%', 'Q10%', 'Q25%', 'Median', 'Q75%', 'Q90%', 'Q95%', 'Q99%']

    boot_summary = pd.DataFrame({
        'Quantile': quant_labels,
        'Cumulative_PnL_USD': np.quantile(boot_pnl, quantiles),
        'Win_Rate_Pct': np.quantile(boot_wr, quantiles) * 100.0,
        'Profit_Factor': np.quantile(boot_pf, quantiles),
        'Trade_Sharpe': np.quantile(boot_sharpe, quantiles),
        'Max_Drawdown_USD': np.quantile(boot_max_dd, quantiles)
    })

    boot_summary_path = os.path.join(out_dir, 'v8_bootstrap_results.csv')
    boot_summary.to_csv(boot_summary_path, index=False)
    print(f"Bootstrap results written to {boot_summary_path}")
    print(boot_summary.to_string())

    # Probability of positive outcome
    p_pos = np.mean(boot_pnl > 0)
    print(f"\nEmpirical Probability of Positive P&L P(PnL > 0): {p_pos*100:.2f}%")
    print(f"95% Confidence Interval for P&L: [${np.quantile(boot_pnl, 0.025):.2f}, ${np.quantile(boot_pnl, 0.975):.2f}] USD")

    # 3. Breakdown by Symbol
    symbols = df_rev['symbol'].unique()
    sym_rows = []
    for s in symbols:
        sub = df_rev[df_rev['symbol'] == s]
        s_pnl = sub['reverse_net_pnl'].sum()
        s_trades = len(sub)
        s_wins = len(sub[sub['reverse_net_pnl'] > 0])
        s_wr = s_wins / s_trades if s_trades > 0 else 0
        s_avg_w = sub[sub['reverse_net_pnl'] > 0]['reverse_net_pnl'].mean() if s_wins > 0 else 0
        s_avg_l = np.abs(sub[sub['reverse_net_pnl'] <= 0]['reverse_net_pnl'].mean()) if (s_trades - s_wins) > 0 else 0
        s_pf = (s_wins * s_avg_w) / ((s_trades - s_wins) * s_avg_l) if ((s_trades - s_wins) * s_avg_l) > 0 else 0

        sym_rows.append({
            'symbol': s,
            'trades': s_trades,
            'wins': s_wins,
            'losses': s_trades - s_wins,
            'win_rate_pct': round(s_wr * 100.0, 2),
            'avg_win_usd': round(s_avg_w, 2),
            'avg_loss_usd': round(s_avg_l, 2),
            'payoff_ratio': round(s_avg_w / s_avg_l, 2) if s_avg_l > 0 else 0,
            'profit_factor': round(s_pf, 2),
            'net_pnl_usd': round(s_pnl, 2)
        })

    df_sym = pd.DataFrame(sym_rows).sort_values(by='net_pnl_usd', ascending=False)
    sym_path = os.path.join(out_dir, 'v8_symbol_breakdown.csv')
    df_sym.to_csv(sym_path, index=False)
    print(f"\nSymbol Breakdown written to {sym_path}")
    print(df_sym.to_string())

    # 4. Parameter Sensitivity Grid (M* in [30, 45, 60, 75, 90], k_TP in [0.6, 0.7, 0.8, 0.9, 1.0])
    m_values = [30, 45, 60, 75, 90]
    k_tp_values = [0.6, 0.7, 0.8, 0.9, 1.0]
    sens_rows = []

    # Using the analytical model calibrated on V7 data:
    # Loss scale scales roughly linearly with M* (d * M + S)
    # Win scale scales with k_TP
    base_l7 = avg_loss  # at M = 60
    base_w7 = avg_win   # at k_TP = 0.8

    for m in m_values:
        scaled_loss = base_l7 * (m / 60.0)
        # Hazard probability over horizon M ticks: 1 - (1 - p0_60)^(M/60)
        p_m = 1.0 - (1.0 - win_rate)**(m / 60.0)
        for k in k_tp_values:
            scaled_win = base_w7 * (k / 0.8)
            exp_payoff = p_m * scaled_win - (1.0 - p_m) * scaled_loss
            tot_exp_pnl = exp_payoff * n
            pf = (p_m * scaled_win) / ((1.0 - p_m) * scaled_loss) if (1.0 - p_m) * scaled_loss > 0 else 0
            sens_rows.append({
                'Time_Stop_M_ticks': m,
                'Take_Profit_k_TP': k,
                'Hazard_Win_Rate_Pct': round(p_m * 100.0, 2),
                'Avg_Win_USD': round(scaled_win, 2),
                'Avg_Loss_USD': round(scaled_loss, 2),
                'Exp_Payoff_USD': round(exp_payoff, 3),
                'Expected_Total_PnL_USD': round(tot_exp_pnl, 2),
                'Profit_Factor': round(pf, 2)
            })

    df_sens = pd.DataFrame(sens_rows)
    sens_path = os.path.join(out_dir, 'v8_parameter_sensitivity.csv')
    df_sens.to_csv(sens_path, index=False)
    print(f"\nParameter sensitivity written to {sens_path}")

    # 5. Export JSON summary
    summary_dict = {
        'model_version': 'v8.00 Spike Hunter Convexe',
        'sample_size_trades': int(n),
        'baseline': {
            'net_pnl_usd': float(round(total_pnl, 2)),
            'win_rate_pct': float(round(win_rate * 100.0, 2)),
            'avg_win_usd': float(round(avg_win, 2)),
            'avg_loss_usd': float(round(avg_loss, 2)),
            'payoff_ratio': float(round(payoff_ratio, 2)),
            'profit_factor': float(round(profit_factor, 2)),
            'trade_sharpe': float(round(trade_sharpe, 4)),
            'max_drawdown_usd': float(round(max_dd, 2))
        },
        'bootstrap_10000': {
            'mean_block_length': float(mean_block_len),
            'probability_positive_pnl': float(round(p_pos * 100.0, 2)),
            'ci_95_pnl_usd': [float(round(np.quantile(boot_pnl, 0.025), 2)), float(round(np.quantile(boot_pnl, 0.975), 2))],
            'median_pnl_usd': float(round(np.median(boot_pnl), 2)),
            'median_profit_factor': float(round(np.median(boot_pf), 2)),
            'median_max_dd_usd': float(round(np.median(boot_max_dd), 2))
        }
    }

    json_path = os.path.join(out_dir, 'v8_validation_summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_dict, f, indent=2)
    print(f"Validation summary written to {json_path}")

if __name__ == '__main__':
    run_stationary_bootstrap()
