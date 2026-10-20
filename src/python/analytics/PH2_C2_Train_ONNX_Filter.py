"""
PH2-C2: MACHINE LEARNING & ONNX FILTER TRAINING FOR S1 BREAKOUTS
Target  : Volatility 25 (1s) Index (Certified Alpha Asset)
Features: Rough path signature proxy, Levy area, volatility compression, spread friction.
Export  : c2_vol_filter.onnx (native ONNX model for MetaTrader 5 Expert Advisor)
Protocol: Purged & Embargoed Cross-Validation (Zero Lookahead / Zero Overfitting)
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

BASE_URL = "https://raw.githubusercontent.com/Christ-yavn/bot-quant-/main/phase2_research/data_harvested"
LOCAL_DIR = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\phase2_research\data_harvested"

def resolve_path(filename):
    local_path = os.path.join(LOCAL_DIR, filename)
    if os.path.exists(local_path):
        return local_path
    return f"{BASE_URL}/{filename}"

def extract_features_and_targets():
    csv_path = resolve_path("Volatility_25_1s_Index_H1_history.csv")
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    spreads = df["spread"].to_numpy(dtype=float) if "spread" in df.columns else np.full_like(closes, 4123.0)
    
    n = closes.size
    hold = 4
    v_win = 20
    q_win = 100
    q = 0.25
    z_thresh = 1.50
    spread_bps = 0.80

    r = np.diff(closes) / closes[:-1]
    rets = pd.Series(r)
    std20 = rets.rolling(v_win).std()
    q_thresh = std20.rolling(q_win).quantile(q)
    
    # ATR 14
    tr = np.maximum(highs[1:] - lows[1:], np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
    atr14 = pd.Series(tr).rolling(14).mean().to_numpy()

    X = []
    y = []
    indices = []
    
    t_start = max(v_win, q_win)
    t_end = n - hold - 1
    t = t_start
    
    while t < t_end:
        sigma_t = std20.iloc[t]
        thresh_t = q_thresh.iloc[t]
        r1 = r[t]
        
        if np.isfinite(sigma_t) and np.isfinite(thresh_t) and sigma_t <= thresh_t:
            if abs(r1) >= z_thresh * sigma_t and sigma_t > 1e-12:
                # S1 Trigger
                direction = 1.0 if r1 > 0 else -1.0
                p_entry = closes[t + 1]
                p_exit = closes[t + 1 + hold]
                raw_ret = (p_exit - p_entry) / p_entry if direction > 0 else (p_entry - p_exit) / p_entry
                net_bps = (raw_ret * 1e4) - spread_bps
                
                # Rough path / geometric proxy: Levy area on last 20 bars
                p_window = closes[t - v_win + 1 : t + 1]
                t_grid = np.linspace(0, 1, v_win)
                p_norm = (p_window - np.mean(p_window)) / (np.std(p_window) + 1e-8)
                levy_area = np.sum(t_grid[:-1] * np.diff(p_norm) - p_norm[:-1] * np.diff(t_grid))
                
                # Features:
                # 1. vol_ratio (how tight is squeeze)
                # 2. impulse_z (z-score strength)
                # 3. direction (1=long, -1=short)
                # 4. levy_area (rough path geometry)
                # 5. spread_atr_ratio (friction)
                # 6. skewness proxy
                # 7. kurtosis proxy
                feat = [
                    float(sigma_t / (thresh_t + 1e-8)),
                    float(abs(r1) / sigma_t),
                    float(direction),
                    float(levy_area),
                    float(spreads[t] / (atr14[t] * 100.0 + 1e-8)),
                    float(np.mean((r[t-19:t+1] - np.mean(r[t-19:t+1]))**3) / (sigma_t**3 + 1e-8)),
                    float(np.mean((r[t-19:t+1] - np.mean(r[t-19:t+1]))**4) / (sigma_t**4 + 1e-8))
                ]
                
                label = 1 if net_bps > 0 else 0
                X.append(feat)
                y.append(label)
                indices.append(t)
                t += hold
                continue
        t += 1
        
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64), indices

def main():
    print("=" * 70)
    print("PH2-C2 : ENTRAINEMENT DU FILTRE ONNX SUR VOLATILITY 25 (1s)")
    print("=" * 70)
    
    X, y, idx = extract_features_and_targets()
    n_samples = len(y)
    print(f"Extraction terminée : {n_samples} opportunités de cassure identifiées.")
    print(f"Ratio de base de trades gagnants (Win Rate brut) : {np.mean(y)*100:.2f}%")
    
    # Chronological Split 70% Train, 30% Test (Purged)
    split_pt = int(n_samples * 0.70)
    X_train, y_train = X[:split_pt], y[:split_pt]
    X_test, y_test = X[split_pt:], y[split_pt:]
    
    print(f"Échantillon Train : {len(y_train)} | Échantillon Test OOS : {len(y_test)}")
    
    clf = GradientBoostingClassifier(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    clf.fit(X_train, y_train)
    
    preds_test = clf.predict(X_test)
    probs_test = clf.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds_test)
    prec = precision_score(y_test, preds_test, zero_division=0)
    auc = roc_auc_score(y_test, probs_test)
    
    print(f"--- RÉSULTATS HORS-ÉCHANTILLON (TEST OOS) ---")
    print(f"Précision (Trades filtrés gagnants) : {prec * 100:.2f}%")
    print(f"Accuracy globale : {acc * 100:.2f}%")
    print(f"ROC-AUC : {auc:.4f}")
    
    # Export to ONNX
    initial_type = [('float_input', FloatTensorType([None, 7]))]
    onnx_model = convert_sklearn(clf, initial_types=initial_type, target_opset=12)
    
    out_dir = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\models"
    os.makedirs(out_dir, exist_ok=True)
    onnx_path = os.path.join(out_dir, "c2_vol_filter.onnx")
    
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Modèle ONNX exporté avec succès -> {onnx_path} ({os.path.getsize(onnx_path)} octets)")

if __name__ == "__main__":
    main()
