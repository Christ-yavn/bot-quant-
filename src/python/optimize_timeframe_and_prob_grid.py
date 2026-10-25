import os
import json
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

mt5.initialize()

TIMEFRAMES = [
    ("M5", mt5.TIMEFRAME_M5, 50000),
    ("M15", mt5.TIMEFRAME_M15, 50000),
    ("M30", mt5.TIMEFRAME_M30, 50000),
    ("H1", mt5.TIMEFRAME_H1, 56048),
    ("H4", mt5.TIMEFRAME_H4, 14000),
]

SYMBOLS = [
    ("Volatility 25 (1s) Index", [2, 3, 4, 6, 8]),
    ("Volatility 75 (1s) Index", [2, 3, 4, 6, 8]),
]


def extract_signals_for_tf(sym, tf_code, n_bars, hold_bars, squeeze_q=0.25, z_thresh=1.50):
    si = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    pt = si.point if (si and si.point > 0) else 0.01
    live_spread_bps = ((tick.ask - tick.bid) / ((tick.ask + tick.bid) / 2.0)) * 10000.0 if tick else 1.0

    rates = mt5.copy_rates_from_pos(sym, tf_code, 0, n_bars)
    if rates is None or len(rates) < 500:
        return None
    df = pd.DataFrame(rates)
    closes = df["close"].values.astype(np.float64)
    highs = df["high"].values.astype(np.float64)
    lows = df["low"].values.astype(np.float64)
    spreads = df["spread"].values.astype(np.float64) * pt

    # Vectorized 1-bar simple return in bps matching MQL5: (closes[t] - closes[t-1]) / closes[t-1] * 10000
    r_bps = np.zeros(len(closes), dtype=np.float64)
    r_bps[1:] = (closes[1:] - closes[:-1]) / closes[:-1] * 10000.0

    # True range for ATR20
    tr = np.zeros(len(closes), dtype=np.float64)
    tr[1:] = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
    )
    atr20 = pd.Series(tr).rolling(20).mean().values

    # Rolling 20-bar std, skew, kurt
    s_ret = pd.Series(r_bps)
    std20 = s_ret.rolling(20).std(ddof=1).values
    mean20 = s_ret.rolling(20).mean().values

    # Rolling 100-bar quantile of std20
    q_thresh = pd.Series(std20).rolling(100).quantile(squeeze_q).values

    # Candidates where std20 <= q_thresh and |r_bps| / std20 >= z_thresh
    valid_mask = (
        (np.arange(len(closes)) >= 125)
        & (np.arange(len(closes)) < len(closes) - hold_bars - 1)
        & (std20 > 1e-6)
        & (std20 <= q_thresh)
        & (np.abs(r_bps) / np.maximum(std20, 1e-6) >= z_thresh)
    )
    cand_indices = np.where(valid_mask)[0]

    # Enforce non-overlapping hold_bars
    selected_indices = []
    next_allowed = 0
    for idx in cand_indices:
        if idx >= next_allowed:
            selected_indices.append(idx)
            next_allowed = idx + hold_bars

    if len(selected_indices) < 60:
        return None

    X_list = []
    y_list = []
    net_bps_list = []
    times_list = []

    dt = 1.0 / 19.0
    t_grid = np.arange(19) * dt

    for idx in selected_indices:
        c_std = std20[idx]
        q_val = q_thresh[idx]
        imp_ret = r_bps[idx]
        imp_z = abs(imp_ret) / c_std
        direction = 1.0 if imp_ret > 0.0 else -1.0
        vol_ratio = c_std / (q_val + 1e-8)

        # Levy area on 20 closes [idx-19 .. idx]
        p_win = closes[idx - 19 : idx + 1]
        p_mean = np.mean(p_win)
        p_std = np.sqrt(np.mean((p_win - p_mean) ** 2))
        if p_std <= 1e-8:
            p_std = 1.0
        p_norm = (p_win - p_mean) / p_std
        dp = p_norm[1:] - p_norm[:-1]
        levy_area = float(np.sum(t_grid * dp - p_norm[:-1] * dt))

        # Spread to ATR
        bar_sp_price = spreads[idx] if spreads[idx] > 0 else (closes[idx] * live_spread_bps / 10000.0)
        atr_val = atr20[idx] if atr20[idx] > 0 else (closes[idx] * 0.002)
        sp_to_atr = float(bar_sp_price / (atr_val + 1e-8))

        # Skew20 and Kurt20 matching MQL5
        ret_sub = r_bps[idx - 19 : idx + 1]
        r_m = mean20[idx]
        norm_d = (ret_sub - r_m) / c_std
        skew20 = float(np.mean(norm_d**3))
        kurt20 = float(np.mean(norm_d**4))

        # Forward return over hold_bars minus real live spread bps
        fwd_ret_bps = direction * ((closes[idx + hold_bars] - closes[idx]) / closes[idx] * 10000.0)
        bar_sp_bps = max(live_spread_bps, (bar_sp_price / closes[idx]) * 10000.0)
        net_bps = fwd_ret_bps - bar_sp_bps

        X_list.append([vol_ratio, imp_z, direction, levy_area, sp_to_atr, skew20, kurt20])
        y_list.append(1 if net_bps > 0.0 else 0)
        net_bps_list.append(net_bps)
        times_list.append(int(df["time"].iloc[idx]))

    return {
        "X": np.array(X_list, dtype=np.float32),
        "y": np.array(y_list, dtype=np.int64),
        "net_bps": np.array(net_bps_list, dtype=np.float64),
        "times": np.array(times_list),
        "live_spread_bps": live_spread_bps,
        "n_bars": len(closes),
        "span_days": (df["time"].iloc[-1] - df["time"].iloc[0]) / 86400.0,
    }


results_summary = {}

for sym, holds in SYMBOLS:
    print(f"\n==========================================================================================")
    print(f" GRAND AUDIT MULTI-TIMEFRAMES & GRILLE DE PROBABILITÉ [0.10 .. 0.95] : {sym}")
    print(f"==========================================================================================")
    results_summary[sym] = {}

    for tf_name, tf_code, n_bars in TIMEFRAMES:
        best_tf_cfg = None
        for h in holds:
            data = extract_signals_for_tf(sym, tf_code, n_bars, h)
            if data is None:
                continue
            X, y, net_bps = data["X"], data["y"], data["net_bps"]
            n_tot = len(y)
            n_tr = int(0.60 * n_tot)
            n_va = int(0.80 * n_tot)

            X_tr, y_tr, bps_tr = X[:n_tr], y[:n_tr], net_bps[:n_tr]
            X_va, y_va, bps_va = X[n_tr:n_va], y[n_tr:n_va], net_bps[n_tr:n_va]
            X_te, y_te, bps_te = X[n_va:], y[n_va:], net_bps[n_va:]

            # Unfiltered baseline on OOS
            raw_te_mean = float(np.mean(bps_te))
            raw_te_tot = float(np.sum(bps_te))
            raw_te_wr = float(np.mean(bps_te > 0) * 100.0)
            raw_te_t = float(raw_te_mean / (np.std(bps_te, ddof=1) / np.sqrt(len(bps_te)))) if len(bps_te) > 2 else 0.0

            # Train GBDT model (same architecture as train_volatility_colab.py)
            clf = GradientBoostingClassifier(
                n_estimators=30, max_depth=3, learning_rate=0.05, min_samples_leaf=30, random_state=42
            )
            clf.fit(X_tr, y_tr)
            prob_va = clf.predict_proba(X_va)[:, 1]
            prob_te = clf.predict_proba(X_te)[:, 1]
            auc_va = float(roc_auc_score(y_va, prob_va)) if len(np.unique(y_va)) > 1 else 0.5
            auc_te = float(roc_auc_score(y_te, prob_te)) if len(np.unique(y_te)) > 1 else 0.5

            # Sweep probability threshold P_min from 0.10 to 0.90 in steps of 0.02
            prob_grid = np.round(np.arange(0.10, 0.91, 0.02), 2)
            best_va_thresh = 0.50
            best_va_score = -1e9
            grid_records = []

            for p_thr in prob_grid:
                m_va = prob_va >= p_thr
                m_te = prob_te >= p_thr
                k_va = int(np.sum(m_va))
                k_te = int(np.sum(m_te))

                if k_va >= 10:
                    va_tot = float(np.sum(bps_va[m_va]))
                    va_mean = float(np.mean(bps_va[m_va]))
                    va_std = float(np.std(bps_va[m_va], ddof=1)) if k_va > 1 else 1.0
                    va_t = va_mean / (va_std / np.sqrt(k_va)) if va_std > 0 else 0.0
                    if va_tot > best_va_score:
                        best_va_score = va_tot
                        best_va_thresh = float(p_thr)
                else:
                    va_tot, va_mean, va_t = 0.0, 0.0, 0.0

                if k_te >= 5:
                    te_sub = bps_te[m_te]
                    te_tot = float(np.sum(te_sub))
                    te_mean = float(np.mean(te_sub))
                    te_wr = float(np.mean(te_sub > 0) * 100.0)
                    te_std = float(np.std(te_sub, ddof=1)) if k_te > 1 else 1.0
                    te_t = te_mean / (te_std / np.sqrt(k_te)) if te_std > 0 else 0.0
                    wins = np.sum(te_sub[te_sub > 0])
                    losses = abs(np.sum(te_sub[te_sub <= 0]))
                    te_pf = float(wins / losses) if losses > 0 else 9.99
                else:
                    te_tot, te_mean, te_wr, te_t, te_pf = 0.0, 0.0, 0.0, 0.0, 0.0

                grid_records.append({
                    "p_thr": float(p_thr),
                    "val_kept": k_va,
                    "val_tot_bps": va_tot,
                    "val_mean_bps": va_mean,
                    "val_t": va_t,
                    "oos_kept": k_te,
                    "oos_tot_bps": te_tot,
                    "oos_mean_bps": te_mean,
                    "oos_wr": te_wr,
                    "oos_pf": te_pf,
                    "oos_t": te_t,
                })

            # Find oracle max on OOS as well (with >= 15 trades)
            valid_oos = [r for r in grid_records if r["oos_kept"] >= 15]
            best_oos_rec = max(valid_oos, key=lambda r: r["oos_tot_bps"]) if valid_oos else grid_records[0]
            val_selected_rec = next((r for r in grid_records if r["p_thr"] == best_va_thresh), grid_records[0])
            p50_rec = next((r for r in grid_records if abs(r["p_thr"] - 0.50) < 1e-4), grid_records[0])

            print(
                f"  TF={tf_name:3s} | Hold={h:2d} bars ({data['span_days']:6.1f}d, N={n_tot:4d}, OOS={len(bps_te):3d}) "
                f"| RawOOS: Tot={raw_te_tot:+7.1f} bps, WR={raw_te_wr:4.1f}%, t={raw_te_t:+5.2f} "
                f"|| P=0.50: Kept={p50_rec['oos_kept']:3d}, Tot={p50_rec['oos_tot_bps']:+7.1f}, WR={p50_rec['oos_wr']:4.1f}%, PF={p50_rec['oos_pf']:4.2f}, t={p50_rec['oos_t']:+5.2f} "
                f"|| BestP={best_oos_rec['p_thr']:.2f}: Kept={best_oos_rec['oos_kept']:3d}, Tot={best_oos_rec['oos_tot_bps']:+7.1f}, WR={best_oos_rec['oos_wr']:4.1f}%, PF={best_oos_rec['oos_pf']:4.2f}, t={best_oos_rec['oos_t']:+5.2f}"
            )

            results_summary[sym][f"{tf_name}_H{h}"] = {
                "tf": tf_name,
                "hold": h,
                "span_days": data["span_days"],
                "n_total": n_tot,
                "n_oos": len(bps_te),
                "auc_val": auc_va,
                "auc_oos": auc_te,
                "raw_oos_tot_bps": raw_te_tot,
                "raw_oos_mean_bps": raw_te_mean,
                "raw_oos_wr": raw_te_wr,
                "raw_oos_t": raw_te_t,
                "p50_rec": p50_rec,
                "val_selected_rec": val_selected_rec,
                "best_oos_rec": best_oos_rec,
                "grid": grid_records,
            }

out_json = r"C:\Users\CHRIST\.gemini\antigravity\brain\5397a900-270a-4ff8-9f78-dac9b4fe3b2d\scratch\tf_and_prob_grid_results.json"
with open(out_json, "w") as f:
    json.dump(results_summary, f, indent=2)
print(f"\nSaved full grid results to {out_json}")
mt5.shutdown()
