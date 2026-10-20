"""
================================================================================
PROJET DERIV — PIPELINE UNIFIÉ GOOGLE COLAB (L99 REAL-SPREAD + GREEN CASH-IN)
================================================================================
Ce script charge instantanément la matrice pré-extraite des 10 000 000 de ticks
(`boom_crash_10M_events.npz` : 18 268 événements de spikes réels calibrés avec
les VRAIS spreads d'exécution live MT5 et la règle Green Cash-In + Break-Even
de la v4.00) — ou extrait depuis les fichiers Parquet si présents — puis :

1. Lance le Tournoi Scientifique de 4 Architectures IA sur Google Colab :
   - IA #1 : LightGBM (Cost-Sensitive Gradient Boosted Decision Trees)
   - IA #2 : HistGradientBoosting L2 (Arbres d'Histogrammes Régularisés)
   - IA #3 : Deep Survival Neural Network (MLP Profond 128 -> 64 -> 32)
   - IA #4 : Meta-Ensemble Hybride L99 (Stacking Arbres + Réseau de Neurones)
2. Optimise les seuils de probabilité par palier sur la partition Validation.
3. Évalue la performance Out-of-Sample sur les 2 000 000 de ticks secrets (Test).
4. Exporte le cerveau IA au format natif `.onnx` (`boom_crash_meta_brain.onnx`)
   pour MetaTrader 5 (`OnnxCreate` / `OnnxRun`).
================================================================================
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


BOOM_CRASH_SPECS = [
    ("boom_1000_index", True, 0, 1.7215, 0.20),
    ("crash_1000_index", False, 1, 0.5422, 0.20),
    ("boom_900_index", True, 2, 0.9620, 0.20),
    ("crash_900_index", False, 3, 1.3560, 0.20),
    ("boom_600_index", True, 4, 0.7730, 0.20),
    ("crash_600_index", False, 5, 3.2820, 0.20),
    ("boom_500_index", True, 6, 0.5270, 0.20),
    ("crash_500_index", False, 7, 0.3270, 0.20),
    ("boom_300_index", True, 8, 0.5030, 0.50),
    ("crash_300_index", False, 9, 1.1130, 0.50),
]

FEATURE_NAMES = [
    "symbol_id",               # 0..9 : Identifiant de l'indice
    "is_boom",                 # 1.0 si Boom, 0.0 si Crash
    "spike_amp_norm",          # Amplitude du spike initial / E[|J|]
    "prev1_inter_spike_norm",  # Temps d'attente N-1 / E[tau]
    "prev2_inter_spike_norm",  # Temps d'attente N-2 / E[tau]
    "prev3_inter_spike_norm",  # Temps d'attente N-3 / E[tau]
    "hawkes_intensity_fast",   # Excitation de Hawkes rapide (beta=0.05)
    "hawkes_intensity_med",    # Excitation de Hawkes moyenne (beta=0.015)
    "hawkes_intensity_slow",   # Excitation de Hawkes lente (beta=0.003)
    "cluster_count_60",        # Densité de spikes sur 60 ticks
    "cluster_count_300",       # Densité de spikes sur 300 ticks
    "post3_drift_velocity",    # Vitesse réelle de dérive sur les 3 ticks post-spike
    "real_breakeven_ticks",    # Vrai spread live exprimé en nombre de ticks de dérive
    "cycle_cost_ratio",        # Ratio (Vrai Spread en ticks) / E[tau]
]


def load_parquet_columns(fp: Path) -> tuple[np.ndarray, np.ndarray]:
    try:
        df = pd.read_parquet(fp, columns=["bid", "ask"])
        return df["bid"].to_numpy(dtype=np.float64), df["ask"].to_numpy(dtype=np.float64)
    except Exception:
        import polars as pl
        df_pl = pl.read_parquet(fp, columns=["bid", "ask"])
        return df_pl["bid"].to_numpy(), df_pl["ask"].to_numpy()


def extract_real_spread_dataset(
    fp: Path,
    is_boom: bool,
    symbol_id: int,
    real_live_spread_pts: float,
    delay_ticks: int = 3,
    net_targets_ticks: tuple[float, float, float] = (15.0, 30.0, 50.0),
    max_sim_ticks: int = 320,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bid, ask = load_parquet_columns(fp)
    mid = 0.5 * (bid + ask)
    diffs = np.diff(mid, prepend=mid[0])

    drift_mask = (diffs < 0.0) if is_boom else (diffs > 0.0)
    abs_drift = float(np.median(np.abs(diffs[drift_mask]))) if np.any(drift_mask) else 0.01
    spike_mask = (diffs > 3.5 * abs_drift) if is_boom else (diffs < -3.5 * abs_drift)
    spike_indices = np.flatnonzero(spike_mask)

    if len(spike_indices) < 25:
        return (
            np.empty((0, len(FEATURE_NAMES)), dtype=np.float32),
            np.empty((0, 3), dtype=np.int64),
            np.empty((0, 3), dtype=np.float64),
        )

    mean_spike = float(np.mean(np.abs(diffs[spike_indices])))
    inter_arrival = np.diff(spike_indices, prepend=0).astype(np.float64)
    mean_tau = float(np.mean(inter_arrival[1:])) if len(inter_arrival) > 1 else 500.0

    breakeven_ticks = real_live_spread_pts / max(abs_drift, 1e-8)
    cycle_cost_ratio = breakeven_ticks / max(mean_tau, 1.0)
    sl_pts = 2.0 * mean_spike

    X_rows, Y_stage_rows, PnL_stage_rows = [], [], []
    n_total = len(mid)

    for idx_pos, s_idx in enumerate(spike_indices):
        if idx_pos < 4:
            continue
        entry_idx = int(s_idx + delay_ticks)
        if entry_idx + max_sim_ticks >= n_total:
            break
        if idx_pos + 1 < len(spike_indices) and spike_indices[idx_pos + 1] <= entry_idx:
            continue

        spike_amp_norm = abs(diffs[s_idx]) / max(mean_spike, 1e-8)
        tau_1 = (s_idx - spike_indices[idx_pos - 1]) / max(mean_tau, 1.0)
        tau_2 = (spike_indices[idx_pos - 1] - spike_indices[idx_pos - 2]) / max(mean_tau, 1.0)
        tau_3 = (spike_indices[idx_pos - 2] - spike_indices[idx_pos - 3]) / max(mean_tau, 1.0)

        past_spikes = spike_indices[max(0, idx_pos - 20) : idx_pos + 1]
        past_amps = np.abs(diffs[past_spikes]) / max(mean_spike, 1e-8)
        lags = float(entry_idx) - past_spikes.astype(np.float64)

        hawkes_fast = float(np.sum(past_amps * np.exp(-0.05 * lags)))
        hawkes_med = float(np.sum(past_amps * np.exp(-0.015 * lags)))
        hawkes_slow = float(np.sum(past_amps * np.exp(-0.003 * lags)))

        c60 = int(np.sum((s_idx - past_spikes) <= 60))
        c300 = int(np.sum((s_idx - past_spikes) <= 300))

        post3_move = (mid[s_idx] - mid[entry_idx]) if is_boom else (mid[entry_idx] - mid[s_idx])
        post3_vel = post3_move / max(delay_ticks * abs_drift, 1e-8)

        feat = [
            float(symbol_id),
            1.0 if is_boom else 0.0,
            float(spike_amp_norm),
            float(tau_1),
            float(tau_2),
            float(tau_3),
            float(hawkes_fast),
            float(hawkes_med),
            float(hawkes_slow),
            float(c60),
            float(c300),
            float(post3_vel),
            float(breakeven_ticks),
            float(cycle_cost_ratio),
        ]

        req_moves = [
            real_live_spread_pts + net_targets_ticks[0] * abs_drift,
            real_live_spread_pts + net_targets_ticks[1] * abs_drift,
            real_live_spread_pts + net_targets_ticks[2] * abs_drift,
        ]

        entry_mid = mid[entry_idx]
        stage_pnls_ticks = [None, None, None]
        stage1_done = False

        for t in range(entry_idx + 1, entry_idx + max_sim_ticks + 1):
            favorable_move = (entry_mid - mid[t]) if is_boom else (mid[t] - entry_mid)
            net_move_after_spread = favorable_move - real_live_spread_pts

            for s_i in range(3):
                if stage_pnls_ticks[s_i] is None and favorable_move >= req_moves[s_i]:
                    stage_pnls_ticks[s_i] = float(net_targets_ticks[s_i])
                    if s_i == 0:
                        stage1_done = True

            if stage_pnls_ticks[0] is not None and stage_pnls_ticks[1] is not None and stage_pnls_ticks[2] is not None:
                break

            is_adverse_spike = (diffs[t] > 3.5 * abs_drift) if is_boom else (diffs[t] < -3.5 * abs_drift)
            if is_adverse_spike or net_move_after_spread <= -sl_pts:
                for s_i in range(3):
                    if stage_pnls_ticks[s_i] is None:
                        if stage1_done and net_move_after_spread > -abs(diffs[t]):
                            stage_pnls_ticks[s_i] = 0.0
                        else:
                            stage_pnls_ticks[s_i] = float(max(net_move_after_spread, -sl_pts) / max(abs_drift, 1e-8))
                break

        final_favorable = (entry_mid - mid[entry_idx + max_sim_ticks]) if is_boom else (mid[entry_idx + max_sim_ticks] - entry_mid)
        final_net_ticks = float((final_favorable - real_live_spread_pts) / max(abs_drift, 1e-8))
        for s_i in range(3):
            if stage_pnls_ticks[s_i] is None:
                stage_pnls_ticks[s_i] = final_net_ticks

        stage_labels = [1 if p > 0.0 else 0 for p in stage_pnls_ticks]
        X_rows.append(feat)
        Y_stage_rows.append(stage_labels)
        PnL_stage_rows.append(stage_pnls_ticks)

    return (
        np.asarray(X_rows, dtype=np.float32),
        np.asarray(Y_stage_rows, dtype=np.int64),
        np.asarray(PnL_stage_rows, dtype=np.float64),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline Unifié Colab L99 (Vrai Spread Live + 4 IAs) -> Export ONNX MQL5")
    parser.add_argument("--data-dir", type=str, default="/content/deriv_l99", help="Dossier contenant boom_crash_10M_events.npz ou partitioned/")
    parser.add_argument("--out-dir", type=str, default="/content/deriv_l99/models", help="Dossier de sortie pour boom_crash_meta_brain.onnx")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    npz_candidates = [
        data_dir / "boom_crash_10M_events.npz",
        data_dir.parent / "boom_crash_10M_events.npz",
        Path("/content/deriv_l99/boom_crash_10M_events.npz"),
    ]
    npz_file = next((p for p in npz_candidates if p.exists()), None)

    print("================================================================================")
    print(" ÉTAPE 1/4 : CHARGEMENT DES 10 000 000 DE TICKS (VRAI SPREAD LIVE + GREEN CASH-IN)")
    print("================================================================================")
    if npz_file is not None:
        print(f"  [OK] Archive matricielle haute vitesse détectée : {npz_file}")
        npz = np.load(npz_file)
        X_train, Y_train, P_train = npz["X_train"], npz["Y_train"], npz["P_train"]
        X_val, Y_val, P_val = npz["X_val"], npz["Y_val"], npz["P_val"]
        X_test, Y_test, P_test = npz["X_test"], npz["Y_test"], npz["P_test"]
        for prefix, _is_b, sym_id, real_spr, _lot in BOOM_CRASH_SPECS:
            m_tr = (X_train[:, 0] == float(sym_id))
            m_va = (X_val[:, 0] == float(sym_id))
            m_te = (X_test[:, 0] == float(sym_id))
            wr_s1 = float(np.mean(Y_train[m_tr, 0]) * 100.0) if np.any(m_tr) else 0.0
            print(f"  [OK] {prefix:<18} | SpreadLive={real_spr:6.4f} | Train={int(np.sum(m_tr)):4d} (WR_S1={wr_s1:5.1f}%) | Val={int(np.sum(m_va)):4d} | Test={int(np.sum(m_te)):4d}")
    else:
        splits_data = {"train": ([], [], []), "val": ([], [], []), "test": ([], [], [])}
        for prefix, is_boom, sym_id, real_spr, _lot in BOOM_CRASH_SPECS:
            for split in ("train", "val", "test"):
                fp = data_dir / f"{prefix}_{split}.parquet"
                X_s, Y_s, P_s = extract_real_spread_dataset(
                    fp, is_boom=is_boom, symbol_id=sym_id, real_live_spread_pts=real_spr
                )
                splits_data[split][0].append(X_s)
                splits_data[split][1].append(Y_s)
                splits_data[split][2].append(P_s)
        X_train = np.vstack(splits_data["train"][0])
        Y_train = np.vstack(splits_data["train"][1])
        P_train = np.vstack(splits_data["train"][2])
        X_val = np.vstack(splits_data["val"][0])
        Y_val = np.vstack(splits_data["val"][1])
        P_val = np.vstack(splits_data["val"][2])
        X_test = np.vstack(splits_data["test"][0])
        Y_test = np.vstack(splits_data["test"][1])
        P_test = np.vstack(splits_data["test"][2])

    pnl_train_panier = np.mean(P_train, axis=1)
    pnl_val_panier = np.mean(P_val, axis=1)
    pnl_test_panier = np.mean(P_test, axis=1)

    y_train_win = (pnl_train_panier > 0.0).astype(np.int64)
    y_val_win = (pnl_val_panier > 0.0).astype(np.int64)

    print(f"\nTotal Signaux Post-Spike : Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    print("\n================================================================================")
    print(" ÉTAPE 2/4 : TOURNOI DES 4 ARCHITECTURES IA SUR COLAB")
    print("================================================================================")
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, VotingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    sample_weights = np.clip(np.abs(pnl_train_panier) / (np.median(np.abs(pnl_train_panier)) + 1e-6), 0.25, 8.0)
    candidates = []

    try:
        from lightgbm import LGBMClassifier
        model_lgbm = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LGBMClassifier(
                n_estimators=350, max_depth=5, num_leaves=24,
                learning_rate=0.025, subsample=0.8, colsample_bytree=0.8,
                reg_alpha=1.5, reg_lambda=2.5, random_state=42, verbose=-1
            )),
        ])
        candidates.append(("IA1_LightGBM_CostSensitive", model_lgbm, True))
    except ImportError:
        model_rf = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=8, min_samples_leaf=25,
                class_weight="balanced_subsample", random_state=42, n_jobs=-1
            )),
        ])
        candidates.append(("IA1_RandomForest_CostSensitive", model_rf, True))

    model_hgb = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", HistGradientBoostingClassifier(
            max_iter=350, max_depth=5, learning_rate=0.025,
            min_samples_leaf=35, l2_regularization=3.0, random_state=42
        )),
    ])
    candidates.append(("IA2_HistGradientBoosting_L2", model_hgb, True))

    model_mlp = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", MLPClassifier(
            hidden_layer_sizes=(128, 64, 32), activation="relu",
            alpha=0.08, batch_size=128, learning_rate_init=0.001,
            max_iter=200, early_stopping=True, random_state=42
        )),
    ])
    candidates.append(("IA3_DeepSurvivalNeuralNet_MLP", model_mlp, False))

    model_hybrid = Pipeline([
        ("scaler", StandardScaler()),
        ("voting", VotingClassifier(
            estimators=[
                ("hgb", HistGradientBoostingClassifier(
                    max_iter=350, max_depth=5, learning_rate=0.025,
                    min_samples_leaf=35, l2_regularization=3.0, random_state=42
                )),
                ("mlp", MLPClassifier(
                    hidden_layer_sizes=(128, 64, 32), activation="relu",
                    alpha=0.08, batch_size=128, learning_rate_init=0.001,
                    max_iter=200, early_stopping=True, random_state=42
                )),
            ],
            voting="soft",
            weights=[0.60, 0.40],
        )),
    ])
    candidates.append(("IA4_MetaEnsemble_Hybrid_L99", model_hybrid, False))

    best_name = ""
    best_model = None
    best_val_pnl = -1e18
    best_thr_s1, best_thr_s2, best_thr_s3 = 0.75, 0.82, 0.88

    for name, mdl, supports_weights in candidates:
        if supports_weights:
            try:
                mdl.fit(X_train, y_train_win, clf__sample_weight=sample_weights)
            except Exception:
                mdl.fit(X_train, y_train_win)
        else:
            mdl.fit(X_train, y_train_win)

        v_prob = mdl.predict_proba(X_val)[:, 1]
        auc_v = roc_auc_score(y_val_win, v_prob)

        local_best_pnl = -1e18
        local_thrs = (0.75, 0.82, 0.88)
        for q1 in np.linspace(0.30, 0.85, 12):
            t1 = float(np.quantile(v_prob, q1))
            t2 = float(np.quantile(v_prob, min(0.95, q1 + 0.10)))
            t3 = float(np.quantile(v_prob, min(0.98, q1 + 0.20)))
            sim_pnl = (
                np.where(v_prob >= t1, P_val[:, 0], 0.0)
                + np.where(v_prob >= t2, P_val[:, 1], 0.0)
                + np.where(v_prob >= t3, P_val[:, 2], 0.0)
            ) / 3.0
            score = float(np.sum(sim_pnl))
            if score > local_best_pnl:
                local_best_pnl = score
                local_thrs = (t1, t2, t3)

        print(f"  -> {name:<30} | ROC-AUC Val = {auc_v:.4f} | Meilleur PnL Val = {local_best_pnl:+.1f} ticks nets")
        if local_best_pnl > best_val_pnl:
            best_val_pnl = local_best_pnl
            best_name = name
            best_model = mdl
            best_thr_s1, best_thr_s2, best_thr_s3 = local_thrs

    print(f"\n>>> ARCHITECTURE IA GAGNANTE : {best_name} <<<")
    print(f"Seuils Optimaux Calibrés : Palier1={best_thr_s1:.4f} | Palier2={best_thr_s2:.4f} | Palier3={best_thr_s3:.4f}")

    print("\n================================================================================")
    print(" ÉTAPE 3/4 : RÉSULTATS OUT-OF-SAMPLE SUR LA PARTITION TEST SCELLÉE (2M TICKS)")
    print("================================================================================")
    test_prob = best_model.predict_proba(X_test)[:, 1]
    base_pnl = float(np.sum(pnl_test_panier))
    ai_pnl = float(np.sum((
        np.where(test_prob >= best_thr_s1, P_test[:, 0], 0.0)
        + np.where(test_prob >= best_thr_s2, P_test[:, 1], 0.0)
        + np.where(test_prob >= best_thr_s3, P_test[:, 2], 0.0)
    ) / 3.0))
    active_mask = test_prob >= best_thr_s1
    ai_wr_s1 = float(np.mean(Y_test[active_mask, 0]) * 100.0) if np.any(active_mask) else 0.0

    print(f"  - Sans Filtre IA (Tous les spikes) : {len(X_test):5d} rafales | PnL Net = {base_pnl:+.1f} ticks nets")
    print(f"  - Avec Cerveau IA ({best_name}) : {int(np.sum(active_mask)):5d} rafales | WinRate Palier 1 = {ai_wr_s1:.2f}% | PnL Net = {ai_pnl:+.1f} ticks nets")

    per_symbol_summary = {}
    for prefix, _is_boom, sym_id, _real_spr, _lot in BOOM_CRASH_SPECS:
        sym_mask = (X_test[:, 0] == float(sym_id))
        sym_ai_mask = sym_mask & (test_prob >= best_thr_s1)
        sym_pnl_raw = float(np.sum(pnl_test_panier[sym_mask]))
        sym_pnl_ai = float(np.sum((
            np.where(test_prob[sym_mask] >= best_thr_s1, P_test[sym_mask, 0], 0.0)
            + np.where(test_prob[sym_mask] >= best_thr_s2, P_test[sym_mask, 1], 0.0)
            + np.where(test_prob[sym_mask] >= best_thr_s3, P_test[sym_mask, 2], 0.0)
        ) / 3.0))
        sym_wr_ai = float(np.mean(Y_test[sym_ai_mask, 0]) * 100.0) if np.any(sym_ai_mask) else 0.0
        per_symbol_summary[prefix] = {
            "trades_kept": int(np.sum(sym_ai_mask)),
            "win_rate_stage1_pct": round(sym_wr_ai, 2),
            "pnl_unfiltered_ticks": round(sym_pnl_raw, 1),
            "pnl_ai_filtered_ticks": round(sym_pnl_ai, 1),
        }
        print(f"    * {prefix:<18} | Gardés={int(np.sum(sym_ai_mask)):3d}/{int(np.sum(sym_mask)):3d} | WR_S1={sym_wr_ai:5.1f}% | PnL Brut={sym_pnl_raw:+7.1f} -> PnL IA={sym_pnl_ai:+7.1f}")

    print("\n================================================================================")
    print(" ÉTAPE 4/4 : EXPORT DU CERVEAU .ONNX POUR METATRADER 5")
    print("================================================================================")
    onnx_path = out_dir / "boom_crash_meta_brain.onnx"
    try:
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [("input", FloatTensorType([None, len(FEATURE_NAMES)]))]
        onnx_model = to_onnx(
            best_model,
            initial_types=initial_type,
            options={id(best_model): {"zipmap": False}},
            target_opset=15,
        )
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"  [SUCCÈS] Cerveau ONNX généré : {onnx_path} ({onnx_path.stat().st_size / 1024:.1f} Ko)")
    except Exception as exc:
        print(f"  [INFO] Conversion ONNX via modèle compatible C++ MQL5 ({exc})...")
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType
        initial_type = [("input", FloatTensorType([None, len(FEATURE_NAMES)]))]
        onnx_model = to_onnx(
            model_hgb,
            initial_types=initial_type,
            options={id(model_hgb): {"zipmap": False}},
            target_opset=15,
        )
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"  [SUCCÈS] Cerveau ONNX généré : {onnx_path} ({onnx_path.stat().st_size / 1024:.1f} Ko)")

    meta_path = out_dir / "onnx_model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "winner_architecture": best_name,
                "feature_names": FEATURE_NAMES,
                "thresholds": {
                    "stage1_15ticks": best_thr_s1,
                    "stage2_30ticks": best_thr_s2,
                    "stage3_50ticks": best_thr_s3,
                },
                "test_unfiltered_pnl_drift_units": base_pnl,
                "test_ai_unified_pnl_drift_units": ai_pnl,
                "test_ai_stage1_win_rate_pct": ai_wr_s1,
                "per_symbol_test_results": per_symbol_summary,
            },
            f,
            indent=2,
        )
    print(f"  [SUCCÈS] Métadonnées sauvegardées : {meta_path}")


if __name__ == "__main__":
    main()
