"""
quant_inference_engine.py
=========================
Inférence statistique de niveau institutionnel pour quant-pod v3 :
tests de data-snooping, multiplicité, nombre effectif d'essais, puissance.

Ce que les desks sérieux utilisent et que le moteur v2 n'avait pas :
  - optimal_block_length        : Politis & White (2004) + correction Patton, Politis & White (2009)
  - stationary_bootstrap_indices: Politis & Romano (1994), VECTORISÉ (rapide)
  - white_reality_check         : White (2000) — "le meilleur de la grille bat-il le benchmark ?"
  - hansen_spa                  : Hansen (2005) SPA studentisé (p lower / consistent / upper)
  - romano_wolf_stepm           : Romano & Wolf (2005) — QUELLES stratégies battent le benchmark (FWER)
  - model_confidence_set        : Hansen, Lunde & Nason (2011) — ensemble des meilleures (sans benchmark)
  - benjamini_yekutieli         : FDR sous dépendance arbitraire (BY 2001), utilisé par Harvey-Liu
  - haircut_sharpe              : Harvey & Liu (2015) "Backtesting" — décote du Sharpe pour m essais
  - effective_number_of_trials  : N_eff (ratio de participation spectral, formule rho_bar, clusters)
  - deflated_sharpe_effective   : DSR (Bailey & López de Prado 2014) avec N_eff au lieu de K brut
  - min_track_record_length     : MinTRL (Bailey & López de Prado 2012)
  - sharpe_ci                   : IC du Sharpe non-gaussien (Mertens 2002 / Lo 2002)
  - required_obs_for_sharpe     : taille d'échantillon pour détecter un Sharpe donné (puissance)
  - sample_size_bias_detection  : n pour détecter P(up)=0.5+eps (cryptanalyse d'un générateur)
  - break_even_probability      : probabilité de gain minimale exigée par le payout / le spread

Dépendances : numpy, scipy.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import kurtosis, norm, skew

EULER_GAMMA = 0.5772156649015329


# ============================================================================
# 1. BOOTSTRAP DÉPENDANT
# ============================================================================
def optimal_block_length(x: Sequence[float]) -> Dict[str, float]:
    """
    Longueur de bloc optimale (Politis-White 2004, constantes corrigées Patton-Politis-White 2009).
    Retourne {'stationary': b_SB, 'circular': b_CB}. b ~ 1 pour un bruit blanc, grand si forte dépendance.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 20:
        return {"stationary": 1.0, "circular": 1.0}
    e = x - x.mean()
    b_max = math.ceil(min(3.0 * math.sqrt(n), n / 3.0))
    kn = max(5, int(math.log10(n)))
    m_max = int(math.ceil(math.sqrt(n))) + kn
    m_max = min(m_max, n - 1)
    cv = 2.0 * math.sqrt(math.log10(n) / n)
    acv = np.array([np.dot(e[: n - k], e[k:]) / n for k in range(m_max + 1)])
    if acv[0] <= 0:
        return {"stationary": 1.0, "circular": 1.0}
    abs_acorr = np.abs(acv[1:] / acv[0])
    mhat, count = None, 0
    for i, a in enumerate(abs_acorr):
        count = count + 1 if a < cv else 0
        if count == kn:
            mhat = i + 1 - kn
            break
    if mhat is None:
        sig = np.where(abs_acorr > cv)[0]
        mhat = int(sig.max() + 1) if len(sig) else 1
    M = int(min(max(2 * mhat, 1), m_max))
    k = np.arange(1, M + 1)
    s = k / M
    lam = np.where(s <= 0.5, 1.0, np.where(s <= 1.0, 2.0 * (1.0 - s), 0.0))
    g = 2.0 * np.sum(lam * k * acv[1: M + 1])
    lr = acv[0] + 2.0 * np.sum(lam * acv[1: M + 1])
    if lr <= 0 or g == 0:
        return {"stationary": 1.0, "circular": 1.0}
    d_sb = 2.0 * lr ** 2
    d_cb = (4.0 / 3.0) * lr ** 2
    b_sb = ((2.0 * g ** 2) / d_sb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    b_cb = ((2.0 * g ** 2) / d_cb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    return {"stationary": float(min(max(b_sb, 1.0), b_max)), "circular": float(min(max(b_cb, 1.0), b_max))}


def stationary_bootstrap_indices(n: int, mean_block: float, n_boot: int,
                                 rng: np.random.Generator) -> np.ndarray:
    """Matrice (n_boot, n) d'indices du bootstrap stationnaire, entièrement vectorisée."""
    p = 1.0 / max(1.0, float(mean_block))
    starts = rng.integers(0, n, size=(n_boot, n))
    jumps = rng.random((n_boot, n)) < p
    jumps[:, 0] = True
    pos = np.arange(n)
    last = np.maximum.accumulate(np.where(jumps, pos, 0), axis=1)
    start_vals = np.take_along_axis(starts, last, axis=1)
    return (start_vals + (pos - last)) % n


def _boot_means(d: np.ndarray, n_boot: int, block: float, seed: int) -> np.ndarray:
    """Moyennes bootstrap (n_boot, M) des colonnes de d (T, M)."""
    rng = np.random.default_rng(seed)
    T = d.shape[0]
    out = np.empty((n_boot, d.shape[1]))
    chunk = max(1, int(2e7 // max(1, T * d.shape[1])))
    for a in range(0, n_boot, chunk):
        b = min(n_boot, a + chunk)
        idx = stationary_bootstrap_indices(T, block, b - a, rng)
        out[a:b] = d[idx].mean(axis=1)
    return out


# ============================================================================
# 2. DATA-SNOOPING : REALITY CHECK, SPA, STEPM, MCS
# ============================================================================
def _prep(perf: np.ndarray, benchmark: Optional[np.ndarray]) -> np.ndarray:
    P = np.asarray(perf, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    if benchmark is None:
        return P
    b = np.asarray(benchmark, dtype=float).reshape(-1, 1)
    return P - b


def white_reality_check(perf: np.ndarray, benchmark: Optional[np.ndarray] = None,
                        n_boot: int = 1000, block: Optional[float] = None, seed: int = 0) -> Dict[str, float]:
    """
    perf (T, M) : rendements par période des M stratégies testées (TOUTE la grille).
    H0 : aucune ne bat le benchmark (0 par défaut). p petite => le meilleur n'est pas que du snooping.
    """
    d = _prep(perf, benchmark)
    T, M = d.shape
    dbar = d.mean(axis=0)
    if block is None:
        block = float(np.median([optimal_block_length(d[:, j])["stationary"] for j in range(min(M, 20))]))
    bm = _boot_means(d, n_boot, block, seed)
    V = math.sqrt(T) * dbar.max()
    Vb = math.sqrt(T) * (bm - dbar).max(axis=1)
    return {"stat": float(V), "p_value": float((1 + np.sum(Vb >= V)) / (1 + n_boot)),
            "best_index": int(np.argmax(dbar)), "block": float(block), "n_strategies": int(M)}


def hansen_spa(perf: np.ndarray, benchmark: Optional[np.ndarray] = None, n_boot: int = 1000,
               block: Optional[float] = None, seed: int = 0) -> Dict[str, float]:
    """Test SPA de Hansen (2005), studentisé, recentrage lower / consistent / upper."""
    d = _prep(perf, benchmark)
    T, M = d.shape
    dbar = d.mean(axis=0)
    if block is None:
        block = float(np.median([optimal_block_length(d[:, j])["stationary"] for j in range(min(M, 20))]))
    bm = _boot_means(d, n_boot, block, seed)
    omega = np.sqrt(T) * bm.std(axis=0, ddof=1)
    omega[omega <= 0] = np.inf
    t_obs = math.sqrt(T) * dbar / omega
    stat = max(0.0, float(t_obs.max()))
    thr = -math.sqrt(2.0 * math.log(max(math.log(T), 1.0 + 1e-9)))
    # Recentrage de Hansen : Z* = sqrt(T) (dbar* - g(dbar)) / omega
    # g_l(x) = max(x, 0) ; g_c(x) = x * 1{t >= -sqrt(2 loglog T)} ; g_u(x) = x  =>  p_l <= p_c <= p_u
    g = {"lower": np.maximum(dbar, 0.0), "consistent": dbar * (t_obs >= thr), "upper": dbar}
    out = {"stat": stat, "block": float(block), "n_strategies": int(M)}
    for name, gk in g.items():
        z = math.sqrt(T) * (bm - gk) / omega
        tb = np.maximum(0.0, z.max(axis=1))
        out[f"p_{name}"] = float((1 + np.sum(tb >= stat)) / (1 + n_boot))
    out["p_value"] = out["p_consistent"]
    return out


def romano_wolf_stepm(perf: np.ndarray, benchmark: Optional[np.ndarray] = None, alpha: float = 0.05,
                      n_boot: int = 1000, block: Optional[float] = None, seed: int = 0) -> Dict[str, object]:
    """StepM studentisé : renvoie l'ENSEMBLE des stratégies significativement > benchmark (contrôle FWER)."""
    d = _prep(perf, benchmark)
    T, M = d.shape
    dbar = d.mean(axis=0)
    if block is None:
        block = float(np.median([optimal_block_length(d[:, j])["stationary"] for j in range(min(M, 20))]))
    bm = _boot_means(d, n_boot, block, seed)
    omega = np.sqrt(T) * bm.std(axis=0, ddof=1)
    omega[omega <= 0] = np.inf
    t_obs = math.sqrt(T) * dbar / omega
    zb = math.sqrt(T) * (bm - dbar) / omega
    active = np.ones(M, dtype=bool)
    rejected: List[int] = []
    while active.any():
        crit = float(np.quantile(zb[:, active].max(axis=1), 1 - alpha))
        new = np.where(active & (t_obs > crit))[0]
        if len(new) == 0:
            break
        rejected.extend(int(i) for i in new)
        active[new] = False
    return {"superior": sorted(rejected), "n_superior": len(rejected), "t_stats": t_obs.tolist(),
            "block": float(block)}


def model_confidence_set(losses: np.ndarray, alpha: float = 0.10, n_boot: int = 1000,
                         block: Optional[float] = None, seed: int = 0) -> Dict[str, object]:
    """
    MCS (Hansen-Lunde-Nason 2011), statistique T_max. losses (T, M) : PERTES (ex. -rendements).
    Retourne les modèles inclus et leur p-value MCS.
    """
    L = np.asarray(losses, dtype=float)
    T, M = L.shape
    if block is None:
        block = float(np.median([optimal_block_length(L[:, j])["stationary"] for j in range(min(M, 20))]))
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(T, block, n_boot, rng)
    Lb = np.stack([L[i].mean(axis=0) for i in idx])          # (n_boot, M)
    Lbar = L.mean(axis=0)
    alive = list(range(M))
    pvals = np.zeros(M)
    running = 0.0
    order_out: List[int] = []
    while len(alive) > 1:
        a = np.array(alive)
        dbar = Lbar[a] - Lbar[a].mean()
        db = Lb[:, a] - Lb[:, a].mean(axis=1, keepdims=True)
        se = np.sqrt(np.mean((db - dbar) ** 2, axis=0))
        se[se <= 0] = np.inf
        t = dbar / se
        tmax = t.max()
        tb = ((db - dbar) / se).max(axis=1)
        p = float(np.mean(tb >= tmax))
        worst = int(a[np.argmax(t)])
        running = max(running, p)
        pvals[worst] = running
        order_out.append(worst)
        if p >= alpha:
            break
        alive.remove(worst)
    for m in alive:
        pvals[m] = 1.0 if len(alive) == 1 else max(running, pvals[m])
    included = [m for m in range(M) if m in alive]
    return {"included": included, "pvalues": pvals.tolist(), "eliminated_in_order": order_out[:-1] if len(alive) > 1 else order_out,
            "block": float(block)}


# ============================================================================
# 3. MULTIPLICITÉ & DÉCOTE DE SHARPE
# ============================================================================
def benjamini_yekutieli(pvals: Sequence[float], q: float = 0.05) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    cm = np.sum(1.0 / np.arange(1, m + 1))
    order = np.argsort(p)
    thresh = q * np.arange(1, m + 1) / (m * cm)
    passed = p[order] <= thresh
    rej = np.zeros(m, dtype=bool)
    if passed.any():
        rej[order[: np.max(np.where(passed)[0]) + 1]] = True
    return rej


def haircut_sharpe(sr_per_period: float, n_obs: int, n_tests: int, periods_per_year: float = 252.0) -> Dict[str, float]:
    """
    Harvey & Liu (2015) : t = SR*sqrt(T) ; p ajustée pour m tests ; SR_ajusté = t_ajusté/sqrt(T).
    Bonferroni, Šidák et BHY "pire rang" (conservateur, dépendance arbitraire).
    """
    T = max(2, int(n_obs))
    m = max(1, int(n_tests))
    t = sr_per_period * math.sqrt(T)
    p = float(2.0 * norm.sf(abs(t)))
    cm = float(np.sum(1.0 / np.arange(1, m + 1)))
    adj = {"bonferroni": min(1.0, p * m), "sidak": 1.0 - (1.0 - p) ** m, "bhy_worst_rank": min(1.0, p * m * cm)}
    out = {"t_stat": t, "p_single": p, "sr_annual": sr_per_period * math.sqrt(periods_per_year)}
    for k, pa in adj.items():
        ta = float(norm.isf(pa / 2.0)) if pa < 1.0 else 0.0
        sra = max(0.0, ta) / math.sqrt(T) * (1 if sr_per_period >= 0 else -1)
        out[f"p_{k}"] = pa
        out[f"sr_annual_{k}"] = sra * math.sqrt(periods_per_year)
        out[f"haircut_{k}"] = 1.0 - (sra / sr_per_period) if sr_per_period != 0 else 1.0
    return out


# ============================================================================
# 4. NOMBRE EFFECTIF D'ESSAIS & DSR
# ============================================================================
def effective_number_of_trials(trial_returns: np.ndarray, max_clusters: int = 20) -> Dict[str, float]:
    """
    trial_returns (T, K) : séries de rendements des K essais (même axe temporel).
    - participation_ratio : (sum lambda)^2 / sum lambda^2 des valeurs propres de la corrélation
    - rho_bar_formula     : rho_bar + (1 - rho_bar) * K  (Bailey & LdP)  -> borne simple
    - n_clusters          : nombre de clusters (Ward sur distance sqrt(0.5(1-rho))), choisi par silhouette
    """
    X = np.asarray(trial_returns, dtype=float)
    K = X.shape[1]
    if K < 2:
        return {"K": K, "participation_ratio": 1.0, "rho_bar_formula": 1.0, "n_clusters": 1}
    sd = X.std(axis=0)
    keep = sd > 0
    X = X[:, keep]
    K2 = X.shape[1]
    C = np.corrcoef(X, rowvar=False)
    C = np.nan_to_num(C, nan=0.0)
    lam = np.clip(np.linalg.eigvalsh(C), 0, None)
    pr = float(lam.sum() ** 2 / max(1e-12, np.sum(lam ** 2)))
    rho_bar = float((C.sum() - K2) / (K2 * (K2 - 1)))
    rho_formula = float(rho_bar + (1 - rho_bar) * K2) if rho_bar > 0 else float(K2)
    D = np.sqrt(np.clip(0.5 * (1 - C), 0, None))
    np.fill_diagonal(D, 0)
    best_k, best_s = 1, -1.0
    if K2 >= 3:
        Z = linkage(squareform(D, checks=False), method="ward")
        for k in range(2, min(max_clusters, K2 - 1) + 1):
            lab = fcluster(Z, k, criterion="maxclust")
            s = _silhouette(D, lab)
            if s > best_s:
                best_k, best_s = k, s
    return {"K": int(K), "participation_ratio": pr, "rho_bar": rho_bar,
            "rho_bar_formula": min(float(K2), rho_formula), "n_clusters": int(best_k),
            "silhouette": float(best_s)}


def _silhouette(D: np.ndarray, lab: np.ndarray) -> float:
    s = []
    for i in range(len(lab)):
        same = lab == lab[i]
        same[i] = False
        if not same.any():
            s.append(0.0)
            continue
        a = D[i, same].mean()
        b = min(D[i, lab == c].mean() for c in np.unique(lab) if c != lab[i])
        s.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(s))


def _psr(sr: float, T: int, g3: float, g4: float, sr0: float) -> float:
    den = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2
    if den <= 0 or T < 3:
        return float("nan")
    return float(norm.cdf((sr - sr0) * math.sqrt(T - 1.0) / math.sqrt(den)))


def deflated_sharpe_effective(best_returns: Sequence[float], trial_sharpes: Sequence[float],
                              n_effective: Optional[float] = None) -> Dict[str, float]:
    """DSR avec N = n_effective (sinon K brut). Variance des SR = variance observée des essais."""
    r = np.asarray(best_returns, dtype=float)
    r = r[np.isfinite(r)]
    T = len(r)
    srs = np.asarray([s for s in trial_sharpes if s is not None and np.isfinite(s)], dtype=float)
    N = float(n_effective) if n_effective else float(max(1, len(srs)))
    var = float(srs.var(ddof=1)) if len(srs) > 1 else 1.0 / max(1, T - 1)
    sd = math.sqrt(max(var, 1e-18))
    if N > 1:
        sr0 = sd * ((1 - EULER_GAMMA) * norm.ppf(1 - 1.0 / N) + EULER_GAMMA * norm.ppf(1 - 1.0 / (N * math.e)))
    else:
        sr0 = 0.0
    sr = float(r.mean() / r.std(ddof=1)) if T > 2 and r.std(ddof=1) > 0 else float("nan")
    return {"sr": sr, "sr0": float(sr0), "N_used": N, "T": T,
            "dsr": _psr(sr, T, float(skew(r, bias=False)), float(kurtosis(r, fisher=False, bias=False)), sr0)}


# ============================================================================
# 5. PUISSANCE, MinTRL, IC
# ============================================================================
def sharpe_ci(returns: Sequence[float], alpha: float = 0.05) -> Dict[str, float]:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    T = len(r)
    sr = float(r.mean() / r.std(ddof=1))
    g3 = float(skew(r, bias=False))
    g4 = float(kurtosis(r, fisher=False, bias=False))
    se = math.sqrt(max(1e-18, (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (T - 1)))
    z = norm.isf(alpha / 2)
    return {"sr": sr, "se": se, "lo": sr - z * se, "hi": sr + z * se}


def min_track_record_length(sr: float, g3: float = 0.0, g4: float = 3.0, sr_star: float = 0.0,
                            alpha: float = 0.05) -> float:
    """Nombre minimal d'observations pour que P(SR_vrai > sr_star) >= 1-alpha (Bailey & LdP 2012)."""
    if sr <= sr_star:
        return float("inf")
    return float(1 + (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) * (norm.isf(alpha) / (sr - sr_star)) ** 2)


def required_obs_for_sharpe(sr: float, alpha: float = 0.05, power: float = 0.8,
                            g3: float = 0.0, g4: float = 3.0) -> float:
    if sr <= 0:
        return float("inf")
    return float(1 + (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) * ((norm.isf(alpha) + norm.ppf(power)) / sr) ** 2)


def sample_size_bias_detection(eps: float, alpha: float = 0.01, power: float = 0.9, p0: float = 0.5) -> int:
    """n pour détecter P(succès) = p0 + eps (test bilatéral). Ex. eps=0.001 -> ~ 4 millions de tirages."""
    p1 = p0 + eps
    za = norm.isf(alpha / 2)
    zb = norm.ppf(power)
    n = ((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))) / eps) ** 2
    return int(math.ceil(n))


def break_even_probability(payout_ratio: Optional[float] = None, mean_abs_move: Optional[float] = None,
                           roundtrip_cost: Optional[float] = None) -> float:
    """
    - Contrat binaire (gain = payout_ratio * mise, perte = mise) : p* = 1 / (1 + payout_ratio)
    - Trade directionnel symétrique : p* = 0.5 + cost / (2 * E|move|)
    """
    if payout_ratio is not None:
        return 1.0 / (1.0 + payout_ratio)
    if mean_abs_move and roundtrip_cost is not None:
        return 0.5 + roundtrip_cost / (2.0 * mean_abs_move)
    raise ValueError("Fournir payout_ratio, ou (mean_abs_move, roundtrip_cost).")


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    T, M = 1500, 40
    noise = rng.normal(0, 1, (T, M)) * 0.01
    # 1. Bloc optimal : bruit blanc ~ petit, AR(1) phi=0.8 ~ grand
    ar = np.zeros(4000)
    for t in range(1, 4000):
        ar[t] = 0.8 * ar[t - 1] + rng.normal()
    b_wn = optimal_block_length(rng.normal(size=4000))["stationary"]
    b_ar = optimal_block_length(ar)["stationary"]
    assert b_ar > 3 * b_wn, (b_wn, b_ar)
    # 2. Indices bootstrap valides
    idx = stationary_bootstrap_indices(100, 5, 3, rng)
    assert idx.shape == (3, 100) and idx.min() >= 0 and idx.max() < 100
    # 3. Bruit pur : RC/SPA ne doivent PAS rejeter (en général)
    rc0 = white_reality_check(noise, n_boot=500, seed=1)
    spa0 = hansen_spa(noise, n_boot=500, seed=1)
    # 4. Edge planté dans la colonne 5
    planted = noise.copy()
    planted[:, 5] += 0.0012
    rc1 = white_reality_check(planted, n_boot=500, seed=1)
    spa1 = hansen_spa(planted, n_boot=500, seed=1)
    sm = romano_wolf_stepm(planted, n_boot=500, seed=1)
    assert rc1["p_value"] < 0.05 and spa1["p_value"] < 0.05 and 5 in sm["superior"], (rc1, spa1, sm["superior"])
    # 5. MCS : la stratégie 5 (pertes les plus faibles) doit être incluse
    mcs = model_confidence_set(-planted[:, :10], alpha=0.10, n_boot=400, seed=2)
    assert 5 in mcs["included"], mcs
    # 6. N_eff : 30 essais quasi-identiques -> N_eff petit
    base = rng.normal(size=(T, 1))
    clones = base + 0.05 * rng.normal(size=(T, 30))
    ne = effective_number_of_trials(clones)
    assert ne["participation_ratio"] < 2.0, ne
    # 7. Haircut, puissance, MinTRL
    hc = haircut_sharpe(0.06, 1000, 200)
    assert 0 < hc["haircut_bonferroni"] <= 1
    n_eps = sample_size_bias_detection(0.001)
    assert 2_000_000 < n_eps < 10_000_000, n_eps
    assert abs(break_even_probability(payout_ratio=0.95) - 1 / 1.95) < 1e-12
    print(f"bloc WN={b_wn:.2f} AR(0.8)={b_ar:.2f} | RC bruit p={rc0['p_value']:.3f} SPA bruit p={spa0['p_value']:.3f}")
    print(f"edge planté: RC p={rc1['p_value']:.4f} SPA p={spa1['p_value']:.4f} StepM={sm['superior']} MCS={mcs['included']}")
    print(f"N_eff(30 clones)={ne['participation_ratio']:.2f} clusters={ne['n_clusters']} | haircut Bonf={hc['haircut_bonferroni']:.2%}")
    print(f"n pour détecter eps=0.1% : {n_eps:,} tirages | MinTRL(SR=0.05/période)={min_track_record_length(0.05):.0f} obs")
    print("quant_inference_engine : 7/7 auto-tests OK")
