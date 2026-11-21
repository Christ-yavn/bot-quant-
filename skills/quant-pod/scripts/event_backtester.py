"""
event_backtester.py
===================
Backtest événementiel réaliste + détecteurs de biais automatiques (quant-pod v3).

Leçons reprises des moteurs de référence :
  - hftbacktest (nkaz001)    : latence d'ordre explicite, pas de fill "magique" au prix du signal
  - freqtrade                : lookahead-analysis (troncature) et recursive-analysis (warm-up)
  - nautilus_trader / LEAN   : modèle événementiel, fills au prix exécutable (bid/ask), gaps

Contenu :
  backtest_events            : décision à la clôture t, exécution à l'OUVERTURE t+latence au prix
                               ask/bid ; stop-loss / take-profit intrabar avec GAP-THROUGH (le stop
                               s'exécute au prix d'ouverture s'il est sauté) ; si SL et TP sont
                               touchés dans la même barre -> hypothèse pessimiste (SL d'abord) ;
                               time-stop ; commissions ; coût de portage (swap/funding) par barre.
  lookahead_truncation_test  : recalcule le signal sur data[:t+1] et compare à data complète
                               -> toute différence = fuite du futur (LOOKAHEAD).
  warmup_stability_test      : sensibilité du signal à la longueur d'historique de démarrage.
  markouts                   : mouvement moyen signé après les entrées (sélection adverse).
  summarize_trades           : n, espérance, t-stat, win-rate, profit factor, max drawdown.

Dépendances : numpy.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Union

import numpy as np

ArrayLike = Union[Sequence[float], np.ndarray]


def backtest_events(open_: ArrayLike, high: ArrayLike, low: ArrayLike, close: ArrayLike, signal: ArrayLike,
                    spread: Union[float, ArrayLike] = 0.0, commission_frac: float = 0.0, latency_bars: int = 1,
                    stop_loss_frac: Optional[float] = None, take_profit_frac: Optional[float] = None,
                    max_hold_bars: Optional[int] = None, carry_frac_per_bar: float = 0.0,
                    exit_on_flat: bool = True) -> Dict[str, object]:
    """
    signal[t] in {-1, 0, +1} calculé avec l'information <= clôture t.
    spread : écart ask-bid en unités de prix (scalaire ou série) ; achat à mid+spread/2, vente à mid-spread/2.
    Rendements de trade exprimés en fraction du prix d'entrée, nets de spread, commission (aller-retour) et portage.
    """
    o, h, l, c = (np.asarray(x, dtype=float) for x in (open_, high, low, close))
    s = np.nan_to_num(np.asarray(signal, dtype=float))
    n = len(c)
    spr = np.full(n, float(spread)) if np.isscalar(spread) else np.asarray(spread, dtype=float)
    lat = max(1, int(latency_bars))
    trades: List[dict] = []
    pos, entry_px, entry_i, sl_px, tp_px = 0, 0.0, -1, None, None
    t = 0
    while t < n - lat:
        e = t + lat                                   # barre d'exécution
        want = int(np.sign(s[t]))
        stopped_on_bar = False

        # Étape 1 : Événements à l'OUVERTURE o[e] (SL_GAP, TP_GAP, TIME, SIGNAL)
        if pos != 0:
            old_pos = pos
            exit_px, reason = None, None
            if sl_px is not None or tp_px is not None:
                if pos > 0:
                    if sl_px is not None and o[e] <= sl_px:
                        exit_px, reason = o[e], "SL_GAP"
                    elif tp_px is not None and o[e] >= tp_px:
                        exit_px, reason = o[e], "TP_GAP"
                else:
                    if sl_px is not None and o[e] >= sl_px:
                        exit_px, reason = o[e], "SL_GAP"
                    elif tp_px is not None and o[e] <= tp_px:
                        exit_px, reason = o[e], "TP_GAP"
            if exit_px is None and max_hold_bars is not None and (e - entry_i) >= max_hold_bars:
                exit_px, reason = o[e], "TIME"
            if exit_px is None and (want == -pos or (exit_on_flat and want == 0)):
                exit_px, reason = o[e], "SIGNAL"
            if exit_px is not None:
                fill = exit_px - pos * spr[e] / 2.0
                bars = max(1, e - entry_i)
                gross = pos * (fill - entry_px) / entry_px
                net = gross - 2 * commission_frac - carry_frac_per_bar * bars
                trades.append({"entry_i": entry_i, "exit_i": e, "side": pos, "entry_px": entry_px,
                               "exit_px": fill, "bars": bars, "gross": gross, "net": net, "reason": reason})
                if reason in ("SL_GAP", "TP_GAP") or (reason == "TIME" and want == old_pos):
                    stopped_on_bar = True
                pos, sl_px, tp_px = 0, None, None

        # Entrée à l'OUVERTURE o[e] (uniquement si pas stoppé sur ce même open)
        if pos == 0 and not stopped_on_bar and want != 0 and e < n - 1:
            entry_px = o[e] + want * spr[e] / 2.0
            pos, entry_i = want, e
            sl_px = entry_px * (1 - want * stop_loss_frac) if stop_loss_frac else None
            tp_px = entry_px * (1 + want * take_profit_frac) if take_profit_frac else None

        # Étape 2 : Excursion INTRABAR (o[e] -> h[e], l[e] -> c[e]) incluant la barre d'entrée
        # Priorité pessimiste : SL testé avant TP. Aucune ré-entrée rétroactive à o[e] possible.
        if pos != 0 and (sl_px is not None or tp_px is not None):
            exit_px, reason = None, None
            if pos > 0:
                if sl_px is not None and l[e] <= sl_px:
                    exit_px, reason = min(o[e], sl_px), "SL"
                elif tp_px is not None and h[e] >= tp_px:
                    exit_px, reason = max(o[e], tp_px), "TP"
            else:
                if sl_px is not None and h[e] >= sl_px:
                    exit_px, reason = max(o[e], sl_px), "SL"
                elif tp_px is not None and l[e] <= tp_px:
                    exit_px, reason = min(o[e], tp_px), "TP"
            if exit_px is not None:
                fill = exit_px - pos * spr[e] / 2.0
                bars = max(1, e - entry_i)
                gross = pos * (fill - entry_px) / entry_px
                net = gross - 2 * commission_frac - carry_frac_per_bar * bars
                trades.append({"entry_i": entry_i, "exit_i": e, "side": pos, "entry_px": entry_px,
                               "exit_px": fill, "bars": bars, "gross": gross, "net": net, "reason": reason})
                pos, sl_px, tp_px = 0, None, None

        t += 1
    if pos != 0:
        fill = c[-1] - pos * spr[-1] / 2.0
        bars = max(1, n - 1 - entry_i)
        gross = pos * (fill - entry_px) / entry_px
        trades.append({"entry_i": entry_i, "exit_i": n - 1, "side": pos, "entry_px": entry_px, "exit_px": fill,
                       "bars": bars, "gross": gross, "net": gross - 2 * commission_frac - carry_frac_per_bar * bars,
                       "reason": "END"})

    # Marquage au marché (Mark-to-Market) causal barre par barre (somme télescopique exacte = sum(tr["net"]))
    bar_returns = np.zeros(n, dtype=float)
    for tr in trades:
        ei, xi = int(tr["entry_i"]), int(tr["exit_i"])
        side = float(tr["side"])
        epx, xpx = float(tr["entry_px"]), float(tr["exit_px"])
        if xi <= ei:
            bar_returns[ei] += float(tr["net"])
        else:
            bar_returns[ei] += side * (c[ei] - epx) / epx - commission_frac
            if xi > ei + 1:
                bar_returns[ei + 1 : xi] += side * (c[ei + 1 : xi] - c[ei : xi - 1]) / epx - carry_frac_per_bar
            bar_returns[xi] += side * (xpx - c[xi - 1]) / epx - commission_frac - carry_frac_per_bar

    return {
        "trades": trades,
        "summary": summarize_trades([tr["net"] for tr in trades], [tr["gross"] for tr in trades]),
        "bar_returns": bar_returns,
    }


def summarize_trades(net: Sequence[float], gross: Optional[Sequence[float]] = None) -> Dict[str, float]:
    r = np.asarray(net, dtype=float)
    m = len(r)
    if m < 2:
        return {"n_trades": m}
    sd = r.std(ddof=1)
    eq = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(eq) - eq)) if m else 0.0
    wins, losses = r[r > 0], r[r < 0]
    out = {"n_trades": m, "mean_net": float(r.mean()), "t_net": float(r.mean() / (sd / math.sqrt(m))) if sd > 0 else 0.0,
           "sharpe_per_trade": float(r.mean() / sd) if sd > 0 else 0.0, "win_rate": float((r > 0).mean()),
           "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else float("inf"),
           "avg_win": float(wins.mean()) if len(wins) else 0.0, "avg_loss": float(losses.mean()) if len(losses) else 0.0,
           "max_drawdown_sum": dd}
    if gross is not None:
        g = np.asarray(gross, dtype=float)
        out["mean_gross"] = float(g.mean())
        out["t_gross"] = float(g.mean() / (g.std(ddof=1) / math.sqrt(m))) if g.std(ddof=1) > 0 else 0.0
    return out


# ============================================================================
# DÉTECTEURS DE BIAIS
# ============================================================================
def lookahead_truncation_test(signal_fn: Callable[[Dict[str, np.ndarray]], np.ndarray], data: Dict[str, ArrayLike],
                              n_checkpoints: int = 25, min_history: int = 200, tail_check: int = 5,
                              atol: float = 1e-9, seed: int = 0) -> Dict[str, object]:
    """
    Pour des instants t tirés au hasard : signal_fn(data[:t+1]) doit redonner EXACTEMENT les
    dernières valeurs de signal_fn(data complète)[:t+1]. Sinon le signal utilise le futur.
    """
    d = {k: np.asarray(v) for k, v in data.items()}
    n = len(next(iter(d.values())))
    if tail_check < 1 or n_checkpoints < 1:
        raise ValueError("tail_check et n_checkpoints doivent être >= 1.")
    if n <= min_history + 1:
        raise ValueError(f"Série trop courte (n={n}) pour min_history={min_history} dans lookahead_truncation_test.")
    if min_history < tail_check:
        raise ValueError(f"min_history={min_history} doit être >= tail_check={tail_check}.")
    full = np.asarray(signal_fn(d), dtype=float)
    rng = np.random.default_rng(seed)
    cps = np.sort(rng.choice(np.arange(min_history, n - 1), size=min(n_checkpoints, n - 1 - min_history), replace=False))
    bad = []
    for t in cps:
        part = np.asarray(signal_fn({k: v[: t + 1] for k, v in d.items()}), dtype=float)
        a = part[-tail_check:]
        b = full[t + 1 - tail_check: t + 1]
        both_nan = np.isnan(a) & np.isnan(b)
        diff = ~both_nan & ~np.isclose(a, b, atol=atol, equal_nan=False)
        if diff.any():
            bad.append(int(t))
    return {"lookahead_detected": bool(bad), "n_checkpoints": int(len(cps)), "mismatch_at": bad[:10],
            "verdict": "FUITE DU FUTUR DÉTECTÉE" if bad else "OK (aucune fuite détectée aux points testés)"}


def warmup_stability_test(signal_fn: Callable[[Dict[str, np.ndarray]], np.ndarray], data: Dict[str, ArrayLike],
                          eval_index: Optional[int] = None, startups: Sequence[int] = (100, 300, 1000)) -> Dict[str, object]:
    """Valeur du signal à eval_index selon la longueur d'historique disponible (vs historique complet)."""
    d = {k: np.asarray(v) for k, v in data.items()}
    n = len(next(iter(d.values())))
    ei = n - 1 if eval_index is None else int(eval_index)
    ref = float(np.asarray(signal_fn({k: v[: ei + 1] for k, v in d.items()}), dtype=float)[-1])
    res = {}
    for su in startups:
        if su >= ei:
            continue
        val = float(np.asarray(signal_fn({k: v[ei - su: ei + 1] for k, v in d.items()}), dtype=float)[-1])
        res[int(su)] = {"value": val, "rel_diff": abs(val - ref) / max(1e-12, abs(ref)) if np.isfinite(val) else float("inf")}
    stable = [su for su, v in res.items() if v["rel_diff"] < 1e-3]
    return {"reference": ref, "by_startup": res, "min_stable_startup": min(stable) if stable else None}


def markouts(mid: ArrayLike, entry_idx: Sequence[int], sides: Sequence[int],
             horizons: Sequence[int] = (1, 5, 20, 60)) -> Dict[int, float]:
    """Moyenne de side*(mid[t+h]-mid[t])/mid[t] : négatif juste après l'entrée = sélection adverse."""
    m = np.asarray(mid, dtype=float)
    idx = np.asarray(entry_idx, dtype=int)
    sd = np.asarray(sides, dtype=float)
    out = {}
    for hz in horizons:
        ok = idx + hz < len(m)
        if ok.any():
            out[int(hz)] = float(np.mean(sd[ok] * (m[idx[ok] + hz] - m[idx[ok]]) / m[idx[ok]]))
    return out


if __name__ == "__main__":
    rng = np.random.default_rng(5)
    n = 5000
    r = rng.normal(0, 0.01, n)
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[100.0], c[:-1]])
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
    data = {"open": o, "high": h, "low": l, "close": c}

    def causal(dd):
        x = dd["close"]
        ma = np.convolve(x, np.ones(20) / 20, mode="full")[: len(x)]
        ma[:19] = np.nan
        return np.sign(x - ma)

    def leaky(dd):
        x = dd["close"]
        fut = np.roll(x, -1)
        fut[-1] = x[-1]
        return np.sign(fut - x)

    lk = lookahead_truncation_test(leaky, data)
    ok = lookahead_truncation_test(causal, data)
    assert lk["lookahead_detected"] and not ok["lookahead_detected"], (lk, ok)

    # Signal aléatoire + coûts -> espérance nette négative ~ -coûts
    sig = rng.choice([-1, 0, 1], n)
    bt = backtest_events(o, h, l, c, sig, spread=0.05, commission_frac=0.0002)
    assert bt["summary"]["mean_net"] < 0

    # Gap-through : stop à -1 %, la barre suivante ouvre à -5 % -> sortie à -5 %, pas à -1 %
    o2 = np.array([100, 100, 100, 95, 95, 95.0]); c2 = np.array([100, 100, 100, 95, 95, 95.0])
    h2 = o2 + 0.1; l2 = o2 - 0.1
    s2 = np.array([1, 0, 0, 0, 0, 0])
    bt2 = backtest_events(o2, h2, l2, c2, s2, stop_loss_frac=0.01, exit_on_flat=False)
    tr = bt2["trades"][0]
    assert tr["reason"] == "SL_GAP" and tr["gross"] < -0.04, tr

    # Warm-up : une EMA dépend de l'historique, une SMA20 non (au-delà de 20 barres)
    def ema(dd):
        x = dd["close"]
        out = np.empty_like(x)
        out[0] = x[0]
        for i in range(1, len(x)):
            out[i] = 0.05 * x[i] + 0.95 * out[i - 1]
        return out
    ws = warmup_stability_test(ema, data, startups=(30, 100, 400))

    # 5. Chronologie intrabar : (1A) SL touché dès la barre d'entrée, (1B) sortie SIGNAL à l'open avant SL intrabar,
    #    (1C) pas de ré-entrée rétroactive à o[e] après un SL intrabar sur la barre e.
    o3 = np.array([100.0, 100.0, 100.0, 100.0])
    h3 = np.array([100.5, 100.5, 100.5, 100.5])
    l3 = np.array([99.5, 95.0, 99.5, 99.5])      # krach intrabar sur la barre d'entrée e=1
    c3 = np.array([100.0, 96.0, 100.0, 100.0])
    s3 = np.array([1, 0, 0, 0])                  # s3[0]=1 -> entrée e=1 et SL intrabar immédiat sur e=1
    bt3 = backtest_events(o3, h3, l3, c3, s3, stop_loss_frac=0.02, exit_on_flat=False)
    assert len(bt3["trades"]) == 1 and bt3["trades"][0]["entry_i"] == 1 and bt3["trades"][0]["exit_i"] == 1 and bt3["trades"][0]["reason"] == "SL", bt3["trades"]

    # (1C) SL intrabar sur e=2 alors que s[1]=1 : interdiction de ré-entrer rétroactivement à o[2]
    l_1c = np.array([99.5, 99.5, 95.0, 99.5])
    s_1c = np.array([1, 1, 0, 0])
    bt_1c = backtest_events(o3, h3, l_1c, c3, s_1c, stop_loss_frac=0.02, exit_on_flat=False)
    assert len(bt_1c["trades"]) == 1 and bt_1c["trades"][0]["entry_i"] == 1 and bt_1c["trades"][0]["exit_i"] == 2 and bt_1c["trades"][0]["reason"] == "SL", bt_1c["trades"]

    # (1B) Sortie SIGNAL à l'ouverture o[2] avant le creux intrabar l[2]
    l4 = np.array([99.5, 99.5, 90.0, 99.5])
    s4 = np.array([1, 0, 0, 0])                  # s4[0]=1 -> entrée e=1; s4[1]=0 -> sortie SIGNAL à o4[2]=100.0
    bt4 = backtest_events(o3, h3, l4, c3, s4, stop_loss_frac=0.02, exit_on_flat=True)
    assert bt4["trades"][0]["reason"] == "SIGNAL" and abs(bt4["trades"][0]["exit_px"] - 100.0) < 1e-12, bt4["trades"]
    assert len(bt["bar_returns"]) == n and abs(bt["bar_returns"].sum() - sum(t["net"] for t in bt["trades"])) < 1e-9

    print(f"lookahead: fuite={lk['verdict']} | causal={ok['verdict']}")
    print(f"aléatoire+coûts: mean_net={bt['summary']['mean_net']:.5f} | gap-through: {tr['reason']} {tr['gross']:.3f} | "
          f"EMA warm-up stable dès {ws['min_stable_startup']} barres")
    print("event_backtester : 6/6 auto-tests OK")
