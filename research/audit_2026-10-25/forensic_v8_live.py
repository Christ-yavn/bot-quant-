"""Forensique d'execution des trades reels v8 (magic 20261020) : decomposition de la perte.
Pour chaque position : prix d'entree/sortie reels vs ticks bid/ask au meme instant, duree, nb de ticks tenus,
mouvement 'theorique' du mid, cout du spread, et slippage/latence."""
import MetaTrader5 as mt5, pandas as pd, numpy as np, pickle, os
from datetime import datetime, timezone
store = pickle.load(open(os.path.join(os.path.dirname(__file__), "bc_ticks.pkl"), "rb"))
mt5.initialize()
d = mt5.history_deals_get(datetime(2026,10,20,tzinfo=timezone.utc), datetime(2026,10,22,tzinfo=timezone.utc))
df = pd.DataFrame(list(d), columns=d[0]._asdict().keys())
df = df[df.magic == 20261020]
ent = df[df.entry == 0].set_index("position_id"); ex = df[df.entry == 1].set_index("position_id")
pos = ent[["time_msc","symbol","type","volume","price"]].join(ex[["time_msc","price","profit","comment"]], rsuffix="_x", how="inner")
rows = []
for pid, r in pos.iterrows():
    s = r.symbol
    if s not in store: continue
    t = store[s]["df"]; tm = t.time_msc.values
    i0 = np.searchsorted(tm, r.time_msc, side="right") - 1
    i1 = np.searchsorted(tm, r.time_msc_x, side="right") - 1
    if i0 < 0 or i1 < 0: continue
    long_ = r.type == 0
    mid0 = (t.bid.iloc[i0]+t.ask.iloc[i0])/2; mid1 = (t.bid.iloc[i1]+t.ask.iloc[i1])/2
    sgn = 1 if long_ else -1
    theo_entry = t.ask.iloc[i0] if long_ else t.bid.iloc[i0]
    theo_exit = t.bid.iloc[i1] if long_ else t.ask.iloc[i1]
    rows.append(dict(sym=s, long=long_, vol=r.volume, hold_s=(r.time_msc_x-r.time_msc)/1000, hold_ticks=i1-i0,
                     pnl=r.profit, mid_move=sgn*(mid1-mid0)*r.volume,
                     spread_cost=-((t.ask.iloc[i0]-t.bid.iloc[i0])/2+(t.ask.iloc[i1]-t.bid.iloc[i1])/2)*r.volume,
                     slip_entry=-sgn*(r.price-theo_entry)*r.volume, slip_exit=sgn*(r.price_x-theo_exit)*r.volume,
                     comment=r.comment))
R = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(f"Positions reconstituees: {len(R)}  | volumes: {R.vol.value_counts().to_dict()}")
print(f"Duree tenue: mediane {R.hold_s.median():.0f}s, p90 {R.hold_s.quantile(.9):.0f}s | ticks tenus: mediane {R.hold_ticks.median():.0f}, p90 {R.hold_ticks.quantile(.9):.0f}, max {R.hold_ticks.max()}")
print("\nDECOMPOSITION DE LA PERTE ($):")
for c in ["pnl","mid_move","spread_cost","slip_entry","slip_exit"]:
    print(f"  {c:12s}: total {R[c].sum():+9.2f} | moyenne/trade {R[c].mean():+.4f}")
print(f"  residuel (pnl - somme des composantes): {(R.pnl - R.mid_move - R.spread_cost - R.slip_entry - R.slip_exit).sum():+.2f}")
print("\nPar symbole:")
print(R.groupby("sym")[["pnl","mid_move","spread_cost","slip_entry","slip_exit","hold_ticks"]].agg(["sum","mean"]).round(3).to_string())
se = R.mid_move.std(ddof=1)*np.sqrt(len(R))
print(f"\nTest martingale du mouvement mid sur positions reelles: somme={R.mid_move.sum():+.2f}$, ecart-type de la somme={se:.2f}$ -> z={R.mid_move.sum()/se:+.2f}")
