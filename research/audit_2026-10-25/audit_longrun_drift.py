"""Test de derive de long terme (martingale sur jours/semaines) + couts de swap, et test du modele ONNX
volatilite avec le vecteur EXACT envoye par l'EA vs celui de l'entrainement."""
import MetaTrader5 as mt5, numpy as np, pandas as pd
mt5.initialize()
syms = [f"{k} {n} Index" for k in ["Boom", "Crash"] for n in [300, 500, 600, 900, 1000]] + \
       ["Volatility 25 (1s) Index", "Volatility 75 (1s) Index", "Volatility 10 (1s) Index", "Volatility 100 (1s) Index"]
print(f"{'Symbole':26s} {'jours':>6s} {'deriv/jour %':>13s} {'t-stat':>7s} {'spread % prix':>13s} {'swap L':>8s} {'swap S':>8s} {'mode':>5s}")
for s in syms:
    if not mt5.symbol_select(s, True): continue
    i = mt5.symbol_info(s); t = mt5.symbol_info_tick(s)
    r = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_D1, 1, 5000)
    if r is None or len(r) < 50: continue
    c = r["close"].astype(float); lr = np.diff(np.log(c))
    m = lr.mean(); tt = m / (lr.std(ddof=1) / np.sqrt(len(lr)))
    print(f"{s:26s} {len(lr):6d} {m*100:+13.4f} {tt:+7.2f} {(t.ask-t.bid)/t.bid*100:13.4f} {i.swap_long:8.2f} {i.swap_short:8.2f} {i.swap_mode:5d}")
