"""Audit microstructure Boom/Crash sur ticks reels Deriv (bid/ask).
Tests: spread reel, drift, spikes, martingale, absence de memoire (hazard), valeur du point.
"""
import MetaTrader5 as mt5, numpy as np, pandas as pd, pickle, os
from datetime import datetime, timezone, timedelta

OUT = os.path.join(os.path.dirname(__file__), "bc_ticks.pkl")
SYMS = ["Crash 600 Index", "Crash 900 Index", "Crash 1000 Index", "Boom 600 Index", "Boom 900 Index",
        "Crash 500 Index", "Boom 500 Index", "Boom 1000 Index"]
mt5.initialize()
end = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
start = end - timedelta(days=10)
store = {}
for s in SYMS:
    mt5.symbol_select(s, True)
    info = mt5.symbol_info(s)
    t = mt5.copy_ticks_range(s, start, end, mt5.COPY_TICKS_ALL)
    if t is None or len(t) == 0:
        print(s, "NO TICKS", mt5.last_error()); continue
    df = pd.DataFrame(t)[["time_msc", "bid", "ask"]]
    df = df[(df.bid > 0) & (df.ask > 0)].drop_duplicates("time_msc", keep="last").reset_index(drop=True)
    usd_per_pt_lot = info.trade_tick_value / info.trade_tick_size
    store[s] = dict(df=df, vol_min=info.volume_min, usd_pt_lot=usd_per_pt_lot, point=info.point)
    mid = ((df.bid + df.ask) / 2).values
    d = np.diff(mid)
    boom = "Boom" in s
    spread = (df.ask - df.bid).values
    # seuil spike = 10x la mediane des |d| dans le sens drift
    drift_moves = d[d < 0] if boom else d[d > 0]
    med = np.median(np.abs(drift_moves))
    thr = 10 * med
    spk = (d > thr) if boom else (d < -thr)
    idx = np.where(spk)[0]
    gaps = np.diff(idx)
    n = len(d)
    # hazard: P(spike au tick k | pas de spike depuis k-1 ticks) par tranches
    bins = [0, 10, 50, 100, 200, 400, 600, 1000, 2000, 10**9]
    haz = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        at_risk = np.sum(np.clip(gaps, None, hi) - np.clip(gaps, None, lo)) if len(gaps) else 0
        events = np.sum((gaps > lo) & (gaps <= hi))
        haz.append((f"{lo}-{hi}", events, at_risk, events / at_risk if at_risk else np.nan))
    # ACF des inter-arrivees (Hawkes => autocorr positive)
    acf1 = np.corrcoef(gaps[:-1], gaps[1:])[0, 1] if len(gaps) > 3 else np.nan
    cv = gaps.std() / gaps.mean() if len(gaps) else np.nan  # geometrique => CV ~ 1
    mean_d = d.mean()
    se_d = d.std() / np.sqrt(n)
    print(f"\n===== {s} =====  ticks={n:,}  jours={(df.time_msc.iloc[-1]-df.time_msc.iloc[0])/86400000:.1f}  ticks/s={n/((df.time_msc.iloc[-1]-df.time_msc.iloc[0])/1000):.2f}")
    print(f" spread pts: median={np.median(spread):.4f}  mean={spread.mean():.4f}  p95={np.percentile(spread,95):.4f}  | vol_min={info.volume_min}  $/pt/lot={usd_per_pt_lot}")
    print(f" drift/tick (median |d| sens drift)={med:.5f}  mean drift move={np.abs(drift_moves).mean():.5f}")
    print(f" spikes={len(idx)}  tau moyen={n/max(len(idx),1):.1f} ticks  amp moy={np.abs(d[idx]).mean():.3f}  amp med={np.median(np.abs(d[idx])):.3f}")
    print(f" spread en ticks de drift (breakeven)={np.median(spread)/med:.1f}  | spread / spike moyen = {np.median(spread)/np.abs(d[idx]).mean()*100:.1f}%")
    print(f" MARTINGALE: E[dMid]/tick={mean_d:+.6f}  (se {se_d:.6f}, t={mean_d/se_d:+.2f})  -> sur 60 ticks: {60*mean_d:+.4f} pts vs spread {np.median(spread):.4f}")
    print(f" MEMOIRE: CV inter-spikes={cv:.3f} (geometrique=1.0) | autocorr(gap_t,gap_t+1)={acf1:+.3f} (Hawkes>0)")
    print(" HAZARD par anciennete (Poisson => constant ~ 1/tau):")
    for h in haz:
        print(f"   age {h[0]:>11}: events={h[1]:5d}  hazard={h[3]*1000 if h[3]==h[3] else float('nan'):.3f} /1000 ticks")
pickle.dump(store, open(OUT, "wb"))
print("\nsaved", OUT)
