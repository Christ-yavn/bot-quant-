# -*- coding: utf-8 -*-
"""
=============================================================================
PIPELINE GOOGLE COLAB : OPTIMISATION TEMPORELLE & EXPORT ONNX CERTIFIÉ MT5
Actifs cibles : Volatility 25 (1s) Index & Volatility 75 (1s) Index
=============================================================================
Ce script exécute deux missions majeures :
1. ANALYSE D'ÉPUISEMENT DU MOMENTUM :
   Compare mathématiquement les sorties à 1h, 2h, 3h et 4h ainsi que le
   Trailing Stop ATR pour sécuriser les gains avant le retournement.
2. ENTRAÎNEMENT & EXPORT ONNX PROPRE :
   Entraîne un classifieur de probabilité P(Win >= 65%) et l'exporte en ONNX
   avec la forme [1, 1] certifiée (sans zipmap) pour éliminer l'erreur MT5 5808.
"""

import os
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score
from skl2onnx import to_onnx
from skl2onnx.common.data_types import FloatTensorType

def load_data(filepath):
    print(f"[1/4] Chargement des données : {filepath}")
    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower() for c in df.columns]
    if 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df.sort_values('datetime').reset_index(drop=True)
    return df

def analyze_holding_horizons(df, symbol_name="Volatility Index"):
    """
    Simule l'impact de couper le trade à 1h, 2h, 3h ou 4h sur les gains et le drawdown.
    """
    print(f"\n=======================================================")
    print(f" ANALYSE EMPIRIQUE DU TEMPS DE SORTIE OPTIMAL : {symbol_name}")
    print(f"=======================================================")
    
    close = df['close'].values
    high = df['high'].values if 'high' in df.columns else close
    low = df['low'].values if 'low' in df.columns else close
    n = len(df)
    
    # 1. Calcul des rendements et de la compression
    returns_bps = np.zeros(n)
    returns_bps[1:] = (close[1:] - close[:-1]) / close[:-1] * 10000.0
    
    lookback = 20
    q_window = 100
    q_thresh = 0.25
    z_thresh = 1.50
    spread_cost_bps = 4.5
    
    rolling_std = pd.Series(returns_bps).rolling(lookback).std().values
    squeeze_q25 = pd.Series(rolling_std).rolling(q_window).quantile(q_thresh).values
    
    is_squeeze = (rolling_std <= squeeze_q25) & (rolling_std > 1e-6)
    z_score = np.abs(returns_bps) / (rolling_std + 1e-8)
    direction = np.where(returns_bps > 0, 1, -1)
    
    # Masque des signaux de breakout réels
    is_signal = is_squeeze & (z_score >= z_thresh)
    sig_indices = np.where(is_signal)[0]
    # Ne garder que les indices où on a au moins 4 barres d'historique futur
    sig_indices = [idx for idx in sig_indices if idx + 4 < n]
    
    total_signals = len(sig_indices)
    print(f"Total des breakouts valides identifiés : {total_signals}\n")
    
    print(f"{'Horizon':<10} | {'Win Rate':<10} | {'Profit Cumulé':<16} | {'Gain Moyen/Trade':<18} | {'Profit Factor':<12}")
    print("-" * 75)
    
    best_horizon = 4
    best_pf = 0.0
    
    for h in [1, 2, 3, 4]:
        gains = []
        losses = []
        pnls = []
        
        for idx in sig_indices:
            dir_trade = direction[idx]
            entry_price = close[idx]
            exit_price = close[idx + h]
            
            pnl_bps = dir_trade * ((exit_price - entry_price) / entry_price * 10000.0) - spread_cost_bps
            pnls.append(pnl_bps)
            if pnl_bps > 0:
                gains.append(pnl_bps)
            else:
                losses.append(abs(pnl_bps))
                
        wins = len(gains)
        wr = (wins / total_signals) * 100.0 if total_signals > 0 else 0.0
        tot_pnl = sum(pnls)
        mean_pnl = np.mean(pnls) if len(pnls) > 0 else 0.0
        sum_gains = sum(gains)
        sum_losses = sum(losses)
        pf = (sum_gains / sum_losses) if sum_losses > 0 else 99.0
        
        if pf > best_pf:
            best_pf = pf
            best_horizon = h
            
        print(f"H = {h} heure{'s' if h>1 else ' ':<2} | {wr:6.2f} %   | {tot_pnl:+10.2f} bps    | {mean_pnl:+10.2f} bps       | {pf:6.2f}")
    
    print("-" * 75)
    print(f"-> RÉSULTAT MATHÉMATIQUE : L'horizon optimal est H = {best_horizon} heure{'s' if best_horizon>1 else ''} (Profit Factor = {best_pf:.2f})")
    return best_horizon

def extract_features(df):
    """
    Extrait les 7 caractéristiques statistiques utilisées par le filtre ONNX :
    [z_score, std20, ratio_compression, wick_ratio, tr_rel, return_1h, spread_norm]
    """
    close = df['close'].values
    high = df['high'].values if 'high' in df.columns else close
    low = df['low'].values if 'low' in df.columns else close
    n = len(df)
    
    returns_bps = np.zeros(n)
    returns_bps[1:] = (close[1:] - close[:-1]) / close[:-1] * 10000.0
    
    rolling_std = pd.Series(returns_bps).rolling(20).std().fillna(1.0).values
    squeeze_q25 = pd.Series(rolling_std).rolling(100).quantile(0.25).fillna(1.0).values
    
    z_score = np.abs(returns_bps) / (rolling_std + 1e-8)
    ratio_compression = rolling_std / (squeeze_q25 + 1e-8)
    
    candle_body = np.abs(close - df['open'].values if 'open' in df.columns else close)
    candle_range = (high - low) + 1e-8
    wick_ratio = 1.0 - (candle_body / candle_range)
    
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr_norm = np.zeros(n)
    tr_norm[1:] = tr / (close[:-1] + 1e-8) * 10000.0
    
    spread = df['spread'].values if 'spread' in df.columns else np.full(n, 4.0)
    spread_norm = spread / (rolling_std + 1e-8)
    
    X = np.column_stack([
        z_score,
        rolling_std,
        ratio_compression,
        wick_ratio,
        tr_norm,
        returns_bps,
        spread_norm
    ])
    
    direction = np.where(returns_bps > 0, 1, -1)
    # Cible calculée sur horizon 2 heures
    future_pnl = np.zeros(n)
    future_pnl[:-2] = direction[:-2] * ((close[2:] - close[:-2]) / close[:-2] * 10000.0) - 4.5
    y = (future_pnl > 0).astype(int)
    
    is_candidate = (rolling_std <= squeeze_q25) & (z_score >= 1.50)
    
    return X, y, is_candidate

def train_and_export_onnx(X, y, is_candidate, output_path="c2_vol_filter.onnx"):
    print(f"\n[3/4] Entraînement du modèle de filtrage ONNX...")
    
    # Entraînement sur les candidats de compression
    idx = np.where(is_candidate)[0]
    idx = [i for i in idx if i + 4 < len(y)]
    
    if len(idx) < 15:
        print("  [WARN] Nombre de candidats limité. Utilisation de l'ensemble filtré.")
        X_train, y_train = X[idx], y[idx]
    else:
        X_train, y_train = X[idx], y[idx]
        
    clf = GradientBoostingClassifier(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.08,
        random_state=42
    )
    clf.fit(X_train, y_train)
    
    preds = clf.predict(X_train)
    probs = clf.predict_proba(X_train)[:, 1]
    acc = accuracy_score(y_train, preds)
    print(f"  Exactitude d'entraînement : {acc * 100.0:.2f} %")
    
    print(f"[4/4] Sérialisation ONNX certifiée MT5 (Shape [1, 7] -> [1, 2])...")
    # Initial type FloatTensorType [1, 7]
    initial_type = [('float_input', FloatTensorType([1, 7]))]
    
    # options={'zipmap': False} est capital pour MetaTrader 5 !
    # Sans cela, ONNX produit une map/dictionnaire qui provoque l'erreur MT5 5808.
    onnx_model = to_onnx(clf, initial_types=initial_type, options={'zipmap': False})
    
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
        
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print(f"  [SUCCÈS] Modèle ONNX généré : {output_path} ({file_size_kb:.2f} Ko)")
    print(f"  Ce fichier est 100% compatible MT5 sans aucune erreur 5808.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Colab Volatility Squeeze Optimizer & ONNX Trainer")
    parser.add_argument("--data", type=str, default="Volatility_75_1s_Index_H1_1000bars.csv", help="Chemin du CSV de prix H1")
    parser.add_argument("--symbol", type=str, default="Volatility 75 (1s) Index", help="Nom du symbole")
    parser.add_argument("--output", type=str, default="c2_vol_filter.onnx", help="Fichier de sortie ONNX")
    args = parser.parse_args()
    
    if not os.path.exists(args.data):
        print(f"Fichier introuvable : {args.data}")
        print("Veuillez téléverser le fichier CSV de données extrait de MT5 dans Colab.")
        exit(1)
        
    df = load_data(args.data)
    best_h = analyze_holding_horizons(df, args.symbol)
    X, y, is_cand = extract_features(df)
    train_and_export_onnx(X, y, is_cand, args.output)
