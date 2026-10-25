"""Audit Volatility 25 (1s) / 75 (1s) : reproduction EXACTE du signal EA v3 sur l'historique H1 maximal,
avec spread reel par barre, baselines aleatoires, tests de clustering de volatilite, et test du modele ONNX
avec le vecteur de features EXACT envoye par l'EA."""
import MetaTrader5 as mt5, numpy as np, pandas as pd, os
rng = np.random.default_rng(7)
mt5.initialize()
ONNX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "models", "c2_vol_filter.onnx"))
try:
    import onnxruntime as ort
    sess = ort.InferenceSession(ONNX)
except Exception as e:
    sess = None; print("onnxruntime indisponible:", e)

def levy(p):
    n = len(p); dt = 1/(n-1); t = np.arange(n-1)*dt
    return np.sum(t*np.diff(p) - p[:-1]*dt)

for sym in ["Volatility 25 (1s) Index", "Volatility 75 (1s) Index"]:
    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 1, 99999)
    df = pd.DataFrame(r)
    c = df.close.values.astype(float); o = df.open.values.astype(float)
    sp = df.spread.values * info.point  # spread en prix
    n = len(c)
    ret = np.zeros(n); ret[1:] = (c[1:]-c[:-1])/c[:-1]*1e4
    print(f"\n==================== {sym} ====================")
    print(f"Barres H1: {n:,}  de {pd.to_datetime(df.time.iloc[0],unit='s')} a {pd.to_datetime(df.time.iloc[-1],unit='s')}")
    print(f"Spread median: {np.median(sp):.4f} prix = {np.median(sp/c*1e4):.2f} bps | sigma H1 = {ret[1:].std():.2f} bps")
    # --- clustering de volatilite (GARCH) : si ~0 => volatilite constante => squeeze = bruit d'echantillonnage
    a = np.abs(ret[1:]); a2 = ret[1:]**2
    acf = lambda x,k: np.corrcoef(x[:-k], x[k:])[0,1]
    print("ACF rendements   lag1..5:", " ".join(f"{acf(ret[1:],k):+.3f}" for k in range(1,6)), f"(bande 95% = +/-{1.96/np.sqrt(n):.3f})")
    print("ACF |rendements| lag1..5:", " ".join(f"{acf(a,k):+.3f}" for k in range(1,6)))
    print("ACF rendements^2 lag1..5:", " ".join(f"{acf(a2,k):+.3f}" for k in range(1,6)))
    # Kurtosis H1 (GBM => 3)
    z = (ret[1:]-ret[1:].mean())/ret[1:].std(); print(f"Kurtosis H1 = {np.mean(z**4):.3f} (gaussien = 3.000)")
    # std20 realise vs persistance: corr(std20 passe, |ret| futur)
    s20 = pd.Series(ret).rolling(20).std().values
    fut_abs = np.r_[np.abs(ret[1:]), np.nan]
    m = ~np.isnan(s20) & ~np.isnan(fut_abs)
    print(f"Pouvoir predictif de la vol: corr(std20_t, |r_t+1|) = {np.corrcoef(s20[m], fut_abs[m])[0,1]:+.4f}")
    # --- Reproduction exacte du signal de l'EA
    N, M, Q, Z = 20, 100, 0.25, 1.5
    sig = []  # (i_entry_bar, direction, features)
    for i in range(N+M+2, n):  # i = barre qui s'ouvre ; barres completes jusqu'a i-1
        rb = ret[i-1:i-1-(N+M):-1] if i-1-(N+M) >= 0 else None  # r_bps[0..N+M-1], r_bps[0] = barre i-1
        if rb is None or len(rb) < N+M: continue
        rs = np.array([np.std(rb[m_:m_+N], ddof=1) for m_ in range(M)])
        thr = np.sort(rs)[int(np.floor(Q*(M-1)))]
        s0 = rs[0]
        if s0 > thr or s0 <= 1e-6: continue
        zz = abs(rb[0])/s0
        if zz < Z: continue
        d = 1.0 if rb[0] > 0 else -1.0
        # features EA (ordre EA)
        closes = c[i-1::-1][:N+M+2]
        pw = closes[:N][::-1]; pn = (pw-pw.mean())/(pw.std() if pw.std()>1e-8 else 1)
        rsub = rb[:N][::-1]; mu = rsub.mean()
        sk = np.mean(((rsub-mu)/s0)**3); ku = np.mean(((rsub-mu)/s0)**4)
        f = [s0/(thr+1e-8), zz, d, levy(pn), 0.0005, sk, ku]
        sig.append((i, d, f))
    print(f"Signaux bruts (avant non-chevauchement): {len(sig)}  = 1 signal / {n/max(len(sig),1):.0f} barres")
    feats = np.array([s[2] for s in sig], dtype=np.float32)
    probs = None
    if sess is not None and len(feats):
        inp = sess.get_inputs()[0].name
        probs = np.array([sess.run(None, {inp: feats[k:k+1]})[1][0][1] for k in range(len(feats))])
        print(f"ONNX (features EA exactes): P(win) moyenne={probs.mean():.3f}  min={probs.min():.3f}  max={probs.max():.3f}  %>=0.50: {np.mean(probs>=0.5)*100:.1f}%")
    for H in [1, 2, 3, 4, 6]:
        for use_onnx in ([False, True] if probs is not None else [False]):
            pnl, gross, busy_until = [], [], -1
            for k, (i, d, f) in enumerate(sig):
                if i < busy_until or i+H >= n: continue
                if use_onnx and probs[k] < 0.5: continue
                entry = o[i]; exitp = o[i+H]
                g = d*(exitp-entry)/entry*1e4
                cost = sp[i]/entry*1e4  # spread paye une fois (aller-retour bid/ask)
                gross.append(g); pnl.append(g-cost); busy_until = i+H
            pnl = np.array(pnl); gross = np.array(gross); k_ = len(pnl)
            if k_ < 3: print(f" H={H} onnx={use_onnx}: trop peu de trades"); continue
            t = pnl.mean()/(pnl.std(ddof=1)/np.sqrt(k_))
            tg = gross.mean()/(gross.std(ddof=1)/np.sqrt(k_))
            pf = pnl[pnl>0].sum()/max(-pnl[pnl<0].sum(),1e-9)
            # baseline : memes nb trades, entrees & directions aleatoires
            base = []
            for _ in range(2000):
                ii = rng.integers(200, n-H-1, k_); dd = rng.choice([-1,1], k_)
                base.append(np.mean(dd*(o[ii+H]-o[ii])/o[ii]*1e4 - sp[ii]/o[ii]*1e4))
            base = np.array(base); pval = np.mean(base >= pnl.mean())
            print(f" H={H}h ONNX={'ON ' if use_onnx else 'OFF'} | trades={k_:4d} | WR={np.mean(pnl>0)*100:5.1f}% | PF={pf:4.2f} | net moy={pnl.mean():+6.2f} bps (t={t:+.2f}) | brut moy={gross.mean():+6.2f} bps (t={tg:+.2f}) | p-val vs hasard={pval:.3f}")
