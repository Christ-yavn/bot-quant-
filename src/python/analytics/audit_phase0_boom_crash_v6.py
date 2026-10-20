#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
AUDIT SCIENTIFIQUE PHASE 0 (a -> i) & SIMULATION MONTE-CARLO EXACTE (v6.00)
Généré par Gemini 4 Argon & Configuré pour s'exécuter sur :
C:/Users/CHRIST/Desktop/IA/ANTIGRAVITY/REGARDER/01_DONNEES_COLAB_10M_ET_MODELE/boom_crash_10M_events.npz
"""

import os
import numpy as np
import scipy.stats as stats
from scipy.optimize import minimize

SEED = 20261019
rng = np.random.default_rng(SEED)

INDICES_SPEC = [
    # (nom, tau_ticks, B_ticks, min_lot, tick_val_020_usd, is_golden)
    ("Crash 600",   571.5,  25.0, 0.20, 0.0077, True),
    ("Crash 900",   907.3,  41.5, 0.20, None,   True),
    ("Boom 900",    911.4,  48.2, 0.20, None,   True),
    ("Crash 1000",  961.0,  54.1, 0.20, None,   True),
    ("Boom 500",    486.9,  30.5, 0.20, None,   True),
    ("Boom 600",    586.5,  43.2, 0.20, None,   True),
    ("Crash 500",   480.0,  41.4, 0.20, None,   True),
    ("Boom 1000",  1066.6, 118.7, 0.20, None,   False),
    ("Crash 300",   297.3,  58.6, 0.50, None,   False),
    ("Crash 50",     50.0,  28.0, 0.20, None,   False),
]

def simulate_v6_exact(tau, B, G=8.0, be_recovery=1.0, sl_mult=3.0, n_sims=300_000, seed=SEED):
    local_rng = np.random.default_rng(seed)
    p = 1.0 / tau
    mu_S = tau
    sl_level = -sl_mult * mu_S

    pnl = np.full(n_sims, -B, dtype=np.float64)
    active = np.ones(n_sims, dtype=bool)
    had_spike = np.zeros(n_sims, dtype=bool)
    duration = np.zeros(n_sims, dtype=np.int64)
    exit_type = np.zeros(n_sims, dtype=np.int8)

    while np.any(active):
        idx = np.where(active)[0]
        m = len(idx)
        target = np.where(had_spike[idx], be_recovery, G)
        ticks_needed = np.maximum(np.ceil(target - pnl[idx]).astype(np.int64), 1)
        k = local_rng.geometric(p, size=m)

        win_mask = k > ticks_needed
        if np.any(win_mask):
            w_idx = idx[win_mask]
            pnl[w_idx] += ticks_needed[win_mask]
            duration[w_idx] += ticks_needed[win_mask]
            exit_type[w_idx] = np.where(had_spike[w_idx], 2, 1)
            active[w_idx] = False

        sp_mask = ~win_mask
        if np.any(sp_mask):
            s_idx = idx[sp_mask]
            k_sp = k[sp_mask]
            amp = local_rng.exponential(scale=mu_S, size=len(s_idx))
            pnl[s_idx] += k_sp - amp
            duration[s_idx] += k_sp
            had_spike[s_idx] = True

            sl_hit = pnl[s_idx] <= sl_level
            if np.any(sl_hit):
                sl_idx = s_idx[sl_hit]
                exit_type[sl_idx] = 3
                active[sl_idx] = False

    return pnl, duration, exit_type

if __name__ == "__main__":
    print("=" * 112)
    print("AUDIT QUANTITATIF PHASE 0 & FALSIFICATION MONTE-CARLO (SEED = 20261019)")
    print("=" * 112)

    possible_npz = [
        "01_DONNEES_COLAB_10M_ET_MODELE/boom_crash_10M_events.npz",
        "boom_crash_10M_events.npz",
        r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\REGARDER\01_DONNEES_COLAB_10M_ET_MODELE\boom_crash_10M_events.npz"
    ]
    npz_path = None
    for p in possible_npz:
        if os.path.exists(p):
            npz_path = p
            break

    if npz_path:
        print(f"[SUCCES] Fichier 10M events détecté : {npz_path}")
        d = np.load(npz_path, allow_pickle=True)
        print("Clés de l'archive :", list(d.keys()))
        for k in d.keys():
            arr = d[k]
            print(f"  {k:15s} shape={arr.shape} dtype={arr.dtype}")
    else:
        print("[INFO] Fichier 10M non trouvé localement, exécution sur simulation sous H0.")

    print("\n--- MONTE-CARLO EXACT v6.00 PAR INDICE SOUS H0 (300 000 TRADES/INDICE) ---")
    header = (f"{'Indice':12s} | {'WR Tot':>7s} | {'WR Dir':>7s} | {'WR Rec':>6s} | {'SL %':>5s} | "
              f"{'GainMoy':>8s} | {'PerteMoy':>9s} | {'E[PnL] ± IC95%':>16s} | {'PF':>5s} | "
              f"{'CVaR95':>8s} | {'MaxDD_1k [IC95%]':>21s} | {'Kelly':>7s}")
    print(header)
    print("-" * len(header))
    for name, tau, B, lot, tval, is_g in INDICES_SPEC:
        be_rec = (0.01 / tval) if tval else 1.0
        pnl, dur, etype = simulate_v6_exact(tau, B, G=8.0, be_recovery=be_rec, sl_mult=3.0, n_sims=300_000, seed=SEED)
        wr_tot = np.mean(pnl > 0) * 100
        wr_dir = np.mean(etype == 1) * 100
        wr_rec = np.mean(etype == 2) * 100
        sl_pct = np.mean(etype == 3) * 100
        g_moy = np.mean(pnl[pnl > 0])
        p_moy = np.mean(pnl[pnl <= 0])
        e_pnl = np.mean(pnl)
        ci_pnl = 1.96 * np.std(pnl, ddof=1) / np.sqrt(len(pnl))
        pf = np.sum(pnl[pnl > 0]) / abs(np.sum(pnl[pnl <= 0]))
        q05 = np.percentile(pnl, 5)
        cvar95 = np.mean(pnl[pnl <= q05])
        pw = np.mean(pnl > 0)
        kelly = pw - (1.0 - pw) / (g_moy / abs(p_moy))

        idx_b = rng.integers(0, len(pnl), size=(1000, 1000))
        paths = np.cumsum(pnl[idx_b], axis=1)
        peaks = np.maximum.accumulate(np.concatenate([np.zeros((1000, 1)), paths], axis=1), axis=1)[:, 1:]
        max_dds = np.max(peaks - paths, axis=1)
        dd_m, dd_l, dd_h = np.median(max_dds), np.percentile(max_dds, 2.5), np.percentile(max_dds, 97.5)

        print(f"{name:12s} | {wr_tot:6.2f}% | {wr_dir:6.2f}% | {wr_rec:5.2f}% | {sl_pct:4.2f}% | "
              f"{g_moy:+7.2f}t | {p_moy:8.1f}t | {e_pnl:+7.2f}±{ci_pnl:4.2f}t | "
              f"{pf:5.3f} | {cvar95:7.1f}t | {dd_m:6.0f} [{dd_l:5.0f},{dd_h:6.0f}] | {kelly:+7.2f}")
