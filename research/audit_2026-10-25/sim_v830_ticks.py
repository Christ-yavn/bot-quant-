"""Simulation tick-par-tick de la logique v8.30 (BUY Boom / SELL Crash) sur ticks reels bid/ask,
+ strategie inverse (v7) + entrees aleatoires. Lot = 0.20 (min Deriv), $/pt/lot = 1.
Regles v8.30 reproduites : entree apres 18 ticks calmes (sens drift), cooldown 15/18 ticks,
sortie spike : 3 ticks de grace apres le spike (ou retracement 8% du pic), time-stop 60 ticks,
coupe-circuit -0.35$, seuil spike = max(3.5*drift, 0.25*spike moyen)."""
import pickle, numpy as np, os
store = pickle.load(open(os.path.join(os.path.dirname(__file__), "bc_ticks.pkl"), "rb"))
rng = np.random.default_rng(1)
LOT = 0.20

def run(bid, ask, boom, thr, mode, calm_req=18, M=60, maxloss=0.35, grace=3):
    mid = (bid + ask) / 2
    n = len(mid); d = np.diff(mid, prepend=mid[0])
    pnl = []; holds = []; spike_wins = 0
    i = 1; calm = 0; cooldown = 0
    while i < n - M - 5:
        di = d[i]
        is_spike = (di >= thr) if boom else (di <= -thr)
        if is_spike: calm = 0
        elif (di <= 0 if boom else di >= 0): calm += 1
        enter = False
        if mode == "random":
            enter = rng.random() < 1/40 and i >= cooldown
        else:
            enter = calm >= calm_req and i >= cooldown
        if not enter: i += 1; continue
        long_ = boom if mode in ("v830", "random") else (not boom)
        if mode == "random": long_ = rng.random() < 0.5
        entry = ask[i] if long_ else bid[i]
        j = i + 1; peak = -1e9; spk_at = -1; out = None
        while j < n - 1:
            cur = (bid[j] - entry) if long_ else (entry - ask[j])
            usd = cur * LOT
            peak = max(peak, usd)
            dj = d[j]
            sp = (dj >= thr) if boom else (dj <= -thr)
            if sp and spk_at < 0: spk_at = j
            if spk_at >= 0 and usd >= 0.10 and (j - spk_at >= grace or usd <= peak * 0.92):
                out = usd; spike_wins += usd > 0; break
            if spk_at < 0 and (j - i) >= M: out = usd; break
            if spk_at < 0 and usd <= -maxloss: out = usd; break
            if spk_at >= 0 and (j - spk_at) > 200: out = usd; break
            j += 1
        if out is None: break
        pnl.append(out); holds.append(j - i)
        cooldown = j + (18 if spk_at >= 0 else 15); calm = 0
        i = j + 1
    return np.array(pnl), np.array(holds), spike_wins

print(f"{'Indice':18s} {'Mode':7s} {'Trades':>7s} {'WR%':>6s} {'Gain moy':>9s} {'Perte moy':>10s} {'EV/trade $':>11s} {'t-stat':>7s} {'Total $':>9s} {'-spread*lot':>12s}")
for s, v in store.items():
    df = v["df"]; bid = df.bid.values; ask = df.ask.values; boom = "Boom" in s
    mid = (bid + ask) / 2; d = np.diff(mid)
    dm = d[d < 0] if boom else d[d > 0]; drift = np.abs(dm).mean()
    big = d[d > 10*np.median(np.abs(dm))] if boom else d[d < -10*np.median(np.abs(dm))]
    thr = max(3.5*drift, 0.25*np.abs(big).mean())
    spread = np.median(ask - bid)
    for mode in ["v830", "v7inv", "random"]:
        p, h, sw = run(bid, ask, boom, thr, mode)
        if len(p) < 5: continue
        t = p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))
        w = p[p > 0]; l = p[p <= 0]
        print(f"{s:18s} {mode:7s} {len(p):7d} {np.mean(p>0)*100:6.1f} {w.mean() if len(w) else 0:9.3f} {l.mean() if len(l) else 0:10.3f} {p.mean():+11.4f} {t:+7.2f} {p.sum():+9.2f} {-spread*LOT:+12.4f}")
