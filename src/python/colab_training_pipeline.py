# -*- coding: utf-8 -*-
"""
PIPELINE D'ENTRAÎNEMENT GOOGLE COLAB POUR LES BOTS DERIV
"""
import os
import numpy as np
import pandas as pd

CONFIG = {
    'vol_lookback': 20,
    'quantile_window': 100,
    'squeeze_quantile': 0.25,
    'breakout_z_threshold': 1.50,
    'holding_horizon_bars': 4,
}

def load_market_data(csv_path):
    df = pd.read_csv(csv_path)
    if 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df.sort_values('datetime').reset_index(drop=True)
    return df

def compute_features(df, lookback=20, q_window=100, q_thresh=0.25):
    df = df.copy()
    close = df['close'].values
    n = len(df)
    returns_bps = np.zeros(n)
    returns_bps[1:] = (close[1:] - close[:-1]) / close[:-1] * 10000.0
    df['returns_bps'] = returns_bps
    rolling_std = pd.Series(returns_bps).rolling(window=lookback).std().values
    df['std20'] = rolling_std
    squeeze_threshold = pd.Series(rolling_std).rolling(window=q_window).quantile(q_thresh).values
    df['squeeze_q25'] = squeeze_threshold
    df['is_squeeze'] = (df['std20'] <= df['squeeze_q25']) & (df['std20'] > 1e-6)
    df['z_score'] = np.abs(df['returns_bps']) / (df['std20'] + 1e-8)
    df['direction'] = np.where(df['returns_bps'] > 0, 1, -1)
    future_return_bps = np.zeros(n)
    future_return_bps[:-4] = (close[4:] - close[:-4]) / close[:-4] * 10000.0
    df['future_return_4h_bps'] = future_return_bps
    df['trade_pnl_bps'] = df['direction'] * df['future_return_4h_bps'] - 4.5
    df['target_win'] = (df['trade_pnl_bps'] > 0.0).astype(int)
    df['is_candidate'] = df['is_squeeze'] & (df['z_score'] >= CONFIG['breakout_z_threshold'])
    return df

def generate_report(df, symbol_name):
    cand = df[df['is_candidate']].copy()
    tot = len(cand)
    if tot == 0:
        print(f'[{symbol_name}] Aucun candidat.')
        return
    wins = cand['target_win'].sum()
    wr = (wins / tot) * 100.0
    mean_pnl = cand['trade_pnl_bps'].mean()
    tot_pnl = cand['trade_pnl_bps'].sum()
    pos = cand[cand['trade_pnl_bps'] > 0]['trade_pnl_bps'].sum()
    neg = np.abs(cand[cand['trade_pnl_bps'] < 0]['trade_pnl_bps'].sum())
    pf = (pos / neg) if neg > 0 else 999.0
    print('='*60)
    print(f'ANALYSE HISTORIQUE 1000 BARS H1 : {symbol_name}')
    print('='*60)
    print(f'  Signaux detectes : {tot}')
    print(f'  Gagnants         : {wins} ({wr:.2f}%)')
    print(f'  Gain moyen/trade : {mean_pnl:+.2f} bps')
    print(f'  PnL cumule       : {tot_pnl:+.2f} bps')
    print(f'  Profit Factor    : {pf:.2f}')
    print('='*60)

if __name__ == '__main__':
    data_dir = r'C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\data\live_trading_extraction'
    for s in ['Volatility_25_1s_Index', 'Volatility_75_1s_Index']:
        p = os.path.join(data_dir, f'{s}_H1_1000bars.csv')
        if os.path.exists(p):
            d = load_market_data(p)
            f_df = compute_features(d)
            generate_report(f_df, s)