"""
null_models.py
==============
Modèles nuls calibrés (marchés SANS edge) pour la porte G3 de quant-pod v3.

La calibration sous modèle nul est le test le plus important du desk : on rejoue TOUTE la
procédure de recherche (même grille, mêmes coûts) sur des marchés simulés qui ont la même
"physique" que le vrai (volatilité, sauts, pas, régimes) mais AUCUN avantage exploitable.
Si la meilleure stratégie trouvée sur le vrai marché ne bat pas le 95e centile des meilleures
trouvées sur ces marchés nuls, l'edge n'est pas démontré.

Contenu :
  1. Simulateurs des familles Deriv (paramétrés et martingales par construction) :
     volatility (GBM), boom_crash (Poisson composé compensé), jump (Merton), step,
     multi_step, skew_step, dsi (dérive à changement de régime markovien), range_break,
     dex (sauts asymétriques exponentiels), trek (tendances à durées de Weibull)
  2. calibrate_family(family, prices) : estimation des paramètres par les moments sur données réelles
  3. Nuls génériques pour marchés réels : iid_bootstrap, block_bootstrap (stationnaire),
     sign_flip (détruit la direction, conserve le clustering de volatilité)
  4. make_null_generator(...) : fabrique le callable rng -> prix attendu par
     quant_validation_engine.null_calibration

ATTENTION (honnêteté) : ces simulateurs reproduisent les faits stylisés publiés/observés,
pas l'algorithme propriétaire de Deriv. DSI et Trek SONT des processus à structure
(dérive persistante) : ce sont des nuls "sans edge exploitable après délai de détection"
seulement si l'on retire la dérive (option `driftless=True`).

Dépendances : numpy.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Optional

import numpy as np

SECONDS_PER_YEAR = 365.0 * 86400.0


# ============================================================================
# 1. SIMULATEURS DES FAMILLES
# ============================================================================
def sim_volatility(n: int, rng: np.random.Generator, sigma_annual: float = 0.75, tick_seconds: float = 1.0,
                   s0: float = 1000.0) -> np.ndarray:
    dt = tick_seconds / SECONDS_PER_YEAR
    r = -0.5 * sigma_annual ** 2 * dt + sigma_annual * math.sqrt(dt) * rng.standard_normal(n)
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


def sim_boom_crash(n: int, rng: np.random.Generator, mean_interval: float = 500.0, spike_mean: float = 10.0,
                   spike_cv: float = 0.5, noise_sd: float = 0.05, is_boom: bool = True, s0: float = 5000.0) -> np.ndarray:
    """Pas additifs : spike (prob 1/N) de taille lognormale ; dérive compensatrice => E[incrément] = 0."""
    p = 1.0 / mean_interval
    s2 = math.log(1 + spike_cv ** 2)
    sizes = rng.lognormal(math.log(spike_mean) - 0.5 * s2, math.sqrt(s2), n)
    spikes = (rng.random(n) < p) * sizes
    drift = -p * spike_mean / (1 - p)
    inc = np.where(spikes > 0, spikes, drift + noise_sd * rng.standard_normal(n))
    inc = inc if is_boom else -inc
    return s0 + np.concatenate([[0.0], np.cumsum(inc)])


def sim_jump(n: int, rng: np.random.Generator, sigma_tick: float = 1e-4, jump_prob: float = 1 / 1800,
             jump_sd: float = 0.01, s0: float = 1000.0) -> np.ndarray:
    """Merton symétrique sur log-prix, compensé (E[exp(r)] = 1)."""
    jumps = (rng.random(n) < jump_prob) * rng.normal(0, jump_sd, n)
    comp = -0.5 * sigma_tick ** 2 - jump_prob * (math.exp(0.5 * jump_sd ** 2) - 1)
    r = comp + sigma_tick * rng.standard_normal(n) + jumps
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


def sim_step(n: int, rng: np.random.Generator, step: float = 0.1, p_up: float = 0.5, s0: float = 8000.0) -> np.ndarray:
    inc = np.where(rng.random(n) < p_up, step, -step)
    return s0 + np.concatenate([[0.0], np.cumsum(inc)])


def sim_multi_step(n: int, rng: np.random.Generator, sizes=(0.1, 0.2, 0.3), probs=(0.5, 0.3, 0.2),
                   s0: float = 8000.0) -> np.ndarray:
    mag = rng.choice(np.asarray(sizes), size=n, p=np.asarray(probs) / np.sum(probs))
    sgn = np.where(rng.random(n) < 0.5, 1.0, -1.0)
    return s0 + np.concatenate([[0.0], np.cumsum(mag * sgn)])


def sim_skew_step(n: int, rng: np.random.Generator, p_up: float = 0.2, size_up: float = 0.4,
                  s0: float = 8000.0) -> np.ndarray:
    """Pas asymétriques martingales : p*up = (1-p)*down => down = p*up/(1-p)."""
    size_down = p_up * size_up / (1 - p_up)
    inc = np.where(rng.random(n) < p_up, size_up, -size_down)
    return s0 + np.concatenate([[0.0], np.cumsum(inc)])


def sim_dsi(n: int, rng: np.random.Generator, drift_tick: float = 2e-5, sigma_tick: float = 1e-4,
            mean_duration: float = 1200.0, driftless: bool = False, s0: float = 10000.0) -> np.ndarray:
    """3 régimes {+mu, 0, -mu}, durées géométriques de moyenne mean_duration ticks."""
    states = np.empty(n, dtype=np.int8)
    s = rng.integers(-1, 2)
    p_switch = 1.0 / mean_duration
    sw = rng.random(n) < p_switch
    nxt = rng.integers(-1, 2, n)
    for t in range(n):
        if sw[t]:
            s = nxt[t]
        states[t] = s
    mu = 0.0 if driftless else drift_tick
    r = mu * states + sigma_tick * rng.standard_normal(n) - 0.5 * sigma_tick ** 2
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


def sim_range_break(n: int, rng: np.random.Generator, step: float = 0.1, width: float = 20.0,
                    break_prob: float = 0.01, s0: float = 1000.0) -> np.ndarray:
    """Marche bornée dans [c - w/2, c + w/2] ; au contact, cassure (prob q) qui décale le canal de w."""
    x = np.empty(n + 1)
    x[0] = s0
    c = s0
    u = rng.random(n)
    sgn = np.where(rng.random(n) < 0.5, step, -step)
    for t in range(n):
        y = x[t] + sgn[t]
        if abs(y - c) >= width / 2:
            if u[t] < break_prob:
                c += math.copysign(width, y - c)
            else:
                y = x[t] - sgn[t]
        x[t + 1] = y
    return x


def sim_dex(n: int, rng: np.random.Generator, jump_prob: float = 1 / 600, jump_mean: float = 0.004,
            sigma_tick: float = 5e-5, up: bool = True, s0: float = 1000.0) -> np.ndarray:
    """Sauts exponentiels dans un sens, dérive compensatrice dans l'autre (log-prix martingale)."""
    J = (rng.random(n) < jump_prob) * rng.exponential(jump_mean, n)
    J = J if up else -J
    comp = -jump_prob * (1 / (1 - jump_mean) - 1 if up else 1 / (1 + jump_mean) - 1) - 0.5 * sigma_tick ** 2
    r = comp + sigma_tick * rng.standard_normal(n) + J
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


def sim_trek(n: int, rng: np.random.Generator, drift_tick: float = 1e-5, sigma_tick: float = 1e-4,
             weibull_k: float = 1.0, weibull_scale: float = 900.0, driftless: bool = False,
             s0: float = 1000.0) -> np.ndarray:
    """Phases de tendance alternées dont la durée suit Weibull(k, scale)."""
    states = np.empty(n)
    t, sgn = 0, 1.0
    while t < n:
        d = max(1, int(weibull_scale * rng.weibull(weibull_k)))
        states[t:t + d] = sgn
        t += d
        sgn = -sgn
    mu = 0.0 if driftless else drift_tick
    r = mu * states + sigma_tick * rng.standard_normal(n) - 0.5 * sigma_tick ** 2
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


SIMULATORS: Dict[str, Callable[..., np.ndarray]] = {
    "volatility": sim_volatility, "boom_crash": sim_boom_crash, "jump": sim_jump, "step": sim_step,
    "multi_step": sim_multi_step, "skew_step": sim_skew_step, "dsi": sim_dsi, "range_break": sim_range_break,
    "dex": sim_dex, "trek": sim_trek,
}


# ============================================================================
# 2. CALIBRATION PAR LES MOMENTS
# ============================================================================
def calibrate_family(family: str, prices, tick_seconds: float = 1.0, spike_k: float = 6.0) -> Dict[str, float]:
    p = np.asarray(prices, dtype=float)
    p = p[np.isfinite(p)]
    d = np.diff(p)
    lr = np.diff(np.log(p))
    if family == "volatility":
        return {"sigma_annual": float(lr.std(ddof=1) * math.sqrt(SECONDS_PER_YEAR / tick_seconds)),
                "tick_seconds": tick_seconds, "s0": float(p[0])}
    if family in ("boom_crash", "dex"):
        med = np.median(np.abs(d[d != 0])) if np.any(d != 0) else 1.0
        is_up = np.abs(d.max()) > np.abs(d.min())
        spike = (d > spike_k * med) if is_up else (d < -spike_k * med)
        q = spike.mean()
        if family == "boom_crash":
            sz = np.abs(d[spike])
            return {"mean_interval": float(1 / max(q, 1e-9)), "spike_mean": float(sz.mean()) if len(sz) else 0.0,
                    "spike_cv": float(sz.std() / sz.mean()) if len(sz) > 1 else 0.5,
                    "noise_sd": float(d[~spike].std()), "is_boom": bool(is_up), "s0": float(p[0])}
        J = np.abs(lr[spike])
        return {"jump_prob": float(q), "jump_mean": float(J.mean()) if len(J) else 0.0,
                "sigma_tick": float(lr[~spike].std()), "up": bool(is_up), "s0": float(p[0])}
    if family == "jump":
        sd = lr.std()
        big = np.abs(lr - np.median(lr)) > 5 * 1.4826 * np.median(np.abs(lr - np.median(lr)))
        return {"sigma_tick": float(lr[~big].std()), "jump_prob": float(big.mean()),
                "jump_sd": float(lr[big].std()) if big.sum() > 2 else float(5 * sd), "s0": float(p[0])}
    if family == "step":
        nz = d[d != 0]
        return {"step": float(np.median(np.abs(nz))), "p_up": float((nz > 0).mean()), "s0": float(p[0])}
    if family == "multi_step":
        a = np.round(np.abs(d[d != 0]), 6)
        vals, cnt = np.unique(a, return_counts=True)
        return {"sizes": tuple(vals.tolist()), "probs": tuple((cnt / cnt.sum()).tolist()), "s0": float(p[0])}
    if family == "skew_step":
        nz = d[d != 0]
        return {"p_up": float((nz > 0).mean()), "size_up": float(nz[nz > 0].mean()), "s0": float(p[0])}
    if family in ("dsi", "trek"):
        return {"sigma_tick": float(lr.std()), "s0": float(p[0]), "driftless": True}
    if family == "range_break":
        nz = d[d != 0]
        return {"step": float(np.median(np.abs(nz))), "s0": float(p[0])}
    raise ValueError(f"famille inconnue : {family}")


# ============================================================================
# 3. NULS GÉNÉRIQUES (marchés réels)
# ============================================================================
def iid_bootstrap_null(returns, rng: np.random.Generator) -> np.ndarray:
    r = np.asarray(returns, dtype=float)
    return rng.choice(r, size=len(r), replace=True)


def block_bootstrap_null(returns, rng: np.random.Generator, mean_block: float = 20.0) -> np.ndarray:
    r = np.asarray(returns, dtype=float) - np.mean(returns)   # dérive retirée : pas d'edge "buy & hold"
    n = len(r)
    p = 1.0 / mean_block
    idx = np.empty(n, dtype=np.int64)
    idx[0] = rng.integers(n)
    jumps = rng.random(n) < p
    starts = rng.integers(0, n, n)
    for t in range(1, n):
        idx[t] = starts[t] if jumps[t] else (idx[t - 1] + 1) % n
    return r[idx]


def sign_flip_null(returns, rng: np.random.Generator) -> np.ndarray:
    """Signes aléatoires : toute prédictibilité directionnelle disparaît, |r_t| (clustering) est conservé."""
    r = np.asarray(returns, dtype=float)
    return np.abs(r - np.mean(r)) * np.where(rng.random(len(r)) < 0.5, 1.0, -1.0)


def returns_to_prices(r, s0: float = 100.0, log: bool = True) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(r)])) if log else s0 + np.concatenate([[0.0], np.cumsum(r)])


# ============================================================================
# 4. FABRIQUE DE GÉNÉRATEURS NULS
# ============================================================================
def make_null_generator(family: str, n: int, params: Optional[Dict] = None,
                        real_returns=None, mean_block: float = 20.0) -> Callable[[np.random.Generator], np.ndarray]:
    """
    Retourne gen(rng) -> prix simulés (longueur n+1), à passer à null_calibration(search_fn, gen, ...).
    family : une famille Deriv de SIMULATORS, ou 'block_bootstrap' / 'sign_flip' / 'iid' (real_returns requis).
    """
    params = dict(params or {})
    if family in SIMULATORS:
        if family in ("dsi", "trek"):
            params["driftless"] = True
        sim = SIMULATORS[family]
        return lambda rng: sim(n, rng, **params)
    if real_returns is None:
        raise ValueError("real_returns requis pour les nuls génériques")
    rr = np.asarray(real_returns, dtype=float)
    if family == "block_bootstrap":
        return lambda rng: returns_to_prices(block_bootstrap_null(rr, rng, mean_block))
    if family == "sign_flip":
        return lambda rng: returns_to_prices(sign_flip_null(rr, rng))
    if family == "iid":
        return lambda rng: returns_to_prices(iid_bootstrap_null(rr - rr.mean(), rng))
    raise ValueError(f"famille inconnue : {family}")


def martingale_drift_check(prices, additive: bool = False) -> Dict[str, float]:
    """t-stat de la moyenne des incréments (devrait être ~0 pour un nul correct)."""
    p = np.asarray(prices, dtype=float)
    inc = np.diff(p) if additive else np.diff(np.log(p))
    t = inc.mean() / (inc.std(ddof=1) / math.sqrt(len(inc)))
    return {"mean_increment": float(inc.mean()), "t_stat": float(t)}


if __name__ == "__main__":
    rng = np.random.default_rng(3)
    N = 200_000
    ok = 0
    for fam in SIMULATORS:
        kw = {"driftless": True} if fam in ("dsi", "trek") else {}
        px = SIMULATORS[fam](N, rng, **kw)
        additive = fam in ("boom_crash", "step", "multi_step", "skew_step", "range_break")
        chk = martingale_drift_check(px, additive=additive)
        assert len(px) == N + 1 and np.isfinite(px).all(), fam
        # tolérance large : t de la moyenne < 4.5 (sous H0 ~ N(0,1))
        assert abs(chk["t_stat"]) < 4.5, (fam, chk)
        ok += 1
    # Calibration boom/crash : on retrouve ~ l'intervalle moyen
    bc = sim_boom_crash(300_000, rng, mean_interval=500, spike_mean=10, noise_sd=0.05)
    cal = calibrate_family("boom_crash", bc)
    assert 400 < cal["mean_interval"] < 620, cal
    vol = sim_volatility(100_000, rng, sigma_annual=0.75)
    cv = calibrate_family("volatility", vol)
    assert abs(cv["sigma_annual"] - 0.75) < 0.02, cv
    gen = make_null_generator("sign_flip", 0, real_returns=rng.normal(0.001, 0.01, 1000))
    assert len(gen(rng)) == 1001
    print(f"null_models : {ok}/10 familles martingales OK | Boom N estimé={cal['mean_interval']:.0f} (vrai 500) | "
          f"sigma V75 estimée={cv['sigma_annual']:.3f}")
    print("null_models : auto-tests OK")
