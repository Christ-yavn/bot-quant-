"""
prng_forensics.py
=================
Cryptanalyse appliquée des marchés générés par RNG (indices synthétiques Deriv, simulateurs)
et tests d'aléa de niveau laboratoire, pour quant-pod v3.

Principe de rigueur : un défaut de générateur n'est un EDGE que si
    (a) il est statistiquement significatif APRÈS correction de multiplicité,
    (b) il survit à des données jamais vues (holdout),
    (c) sa taille dépasse la probabilité de break-even imposée par le payout ou le spread.
Le module fournit les trois briques.

Contenu :
  A. Conversion série -> bits / uniformes : sign_bits, parity_bits, pit_uniforms
  B. NIST SP 800-22 (réimplémentation de 8 tests avec p-values exactes du standard) :
     frequency, block_frequency, runs, longest_run_ones, cumulative_sums, approximate_entropy,
     serial, dft_spectral  + nist_sp800_22_battery (proportion de succès)
  C. NIST SP 800-90B (4 estimateurs non-IID sur 10 : MCV, Markov, t-Tuple, LRS) : sp800_90b_min_entropy
     -> CERTIFICATION : exporter les bits et lancer l'outil officiel `ea_non_iid` (usnistgov/SP800-90B_EntropyAssessment)
  D. Batterie PIT (loi théorique connue) : KS, Anderson-Darling, Cramér-von Mises, Ljung-Box sur z et z²,
     test de Berkowitz (2001)
  E. Données de substitution (surrogates) : shuffle / phase-randomisée / IAAFT -> p-value de N'IMPORTE
     quelle statistique non linéaire (BDS, Lyapunov, RQA, TE, MF-DFA n'ont AUCUN sens sans cela)
  F. Exploitabilité : exploitability_verdict (IC de p vs p* de break-even)
  G. Faisabilité d'attaque PRNG : mt19937_untemper / mt19937_recover_and_predict (démonstration réelle
     sur le Mersenne Twister de Python) + prng_attack_feasibility (quand c'est impossible : CSPRNG,
     sorties transformées/arrondies)

Dépendances : numpy, scipy.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats
from scipy.special import erfc, gammaincc


# ============================================================================
# A. CONVERSIONS
# ============================================================================
def sign_bits(deltas: Sequence[float]) -> np.ndarray:
    """1 si hausse, 0 si baisse ; les variations nulles sont retirées (sinon biais)."""
    d = np.asarray(deltas, dtype=float)
    d = d[np.isfinite(d) & (d != 0)]
    return (d > 0).astype(np.uint8)


def parity_bits(int_series: Sequence[int]) -> np.ndarray:
    return (np.abs(np.asarray(int_series, dtype=np.int64)) % 2).astype(np.uint8)


def pit_uniforms(x: Sequence[float], cdf: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Probability Integral Transform : u = F(x). Si F est la VRAIE loi, u ~ U(0,1) i.i.d."""
    u = cdf(np.asarray(x, dtype=float))
    return np.clip(u, 1e-12, 1 - 1e-12)


def _bits(b) -> np.ndarray:
    b = np.asarray(b).astype(np.int64)
    if not np.isin(b, [0, 1]).all():
        raise ValueError("séquence binaire attendue (0/1)")
    return b


# ============================================================================
# B. NIST SP 800-22
# ============================================================================
def nist_frequency(b) -> float:
    b = _bits(b)
    n = len(b)
    s = abs(np.sum(2 * b - 1)) / math.sqrt(n)
    return float(erfc(s / math.sqrt(2)))


def nist_block_frequency(b, M: int = 128) -> float:
    b = _bits(b)
    N = len(b) // M
    if N < 1:
        return float("nan")
    pi = b[: N * M].reshape(N, M).mean(axis=1)
    chi2 = 4.0 * M * np.sum((pi - 0.5) ** 2)
    return float(gammaincc(N / 2.0, chi2 / 2.0))


def nist_runs(b) -> float:
    b = _bits(b)
    n = len(b)
    pi = b.mean()
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return 0.0
    v = 1 + np.sum(b[1:] != b[:-1])
    return float(erfc(abs(v - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi))))


def nist_longest_run_ones(b) -> float:
    b = _bits(b)
    n = len(b)
    if n < 128:
        return float("nan")
    if n < 6272:
        M, edges, pi = 8, [1, 2, 3], [0.2148, 0.3672, 0.2305, 0.1875]
    elif n < 750000:
        M, edges, pi = 128, [4, 5, 6, 7, 8], [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    else:
        M, edges, pi = 10000, [10, 11, 12, 13, 14, 15], [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]
    N = n // M
    blocks = b[: N * M].reshape(N, M)
    longest = np.zeros(N, dtype=int)
    for i in range(N):
        runs = np.diff(np.flatnonzero(np.diff(np.concatenate([[0], blocks[i], [0]])))) [::2]
        longest[i] = runs.max() if len(runs) else 0
    K = len(pi) - 1
    # classes : <= e0, e1, ..., e_{K-1}, > e_{K-1}
    v = np.zeros(K + 1)
    for L in longest:
        if L <= edges[0]:
            v[0] += 1
        elif L > edges[-1]:
            v[K] += 1
        else:
            v[edges.index(L)] += 1
    pi = np.asarray(pi)
    chi2 = np.sum((v - N * pi) ** 2 / (N * pi))
    return float(gammaincc(K / 2.0, chi2 / 2.0))


def nist_cumulative_sums(b, mode: str = "forward") -> float:
    b = _bits(b)
    n = len(b)
    x = 2 * b - 1
    if mode != "forward":
        x = x[::-1]
    z = float(np.max(np.abs(np.cumsum(x))))
    if z == 0:
        return 1.0
    sq = math.sqrt(n)
    k1 = np.arange(int(math.floor((-n / z + 1) / 4)), int(math.floor((n / z - 1) / 4)) + 1)
    k2 = np.arange(int(math.floor((-n / z - 3) / 4)), int(math.floor((n / z - 1) / 4)) + 1)
    s1 = np.sum(stats.norm.cdf((4 * k1 + 1) * z / sq) - stats.norm.cdf((4 * k1 - 1) * z / sq))
    s2 = np.sum(stats.norm.cdf((4 * k2 + 3) * z / sq) - stats.norm.cdf((4 * k2 + 1) * z / sq))
    return float(min(1.0, max(0.0, 1.0 - s1 + s2)))


def _pattern_counts(b: np.ndarray, m: int) -> np.ndarray:
    """Comptes des 2^m motifs de m bits, chevauchants, avec bouclage (wrap-around)."""
    n = len(b)
    ext = np.concatenate([b, b[: m - 1]]) if m > 1 else b
    val = np.zeros(n, dtype=np.int64)
    for j in range(m):
        val = (val << 1) | ext[j: j + n]
    return np.bincount(val, minlength=2 ** m)


def nist_approximate_entropy(b, m: int = 10) -> float:
    b = _bits(b)
    n = len(b)

    def phi(mm):
        if mm == 0:
            return 0.0
        c = _pattern_counts(b, mm) / n
        c = c[c > 0]
        return float(np.sum(c * np.log(c)))

    apen = phi(m) - phi(m + 1)
    chi2 = 2.0 * n * (math.log(2) - apen)
    return float(gammaincc(2 ** (m - 1), chi2 / 2.0))


def nist_serial(b, m: int = 16) -> Dict[str, float]:
    b = _bits(b)
    n = len(b)

    def psi2(mm):
        if mm <= 0:
            return 0.0
        c = _pattern_counts(b, mm)
        return float((2 ** mm / n) * np.sum(c.astype(float) ** 2) - n)

    p0, p1, p2 = psi2(m), psi2(m - 1), psi2(m - 2)
    d1 = p0 - p1
    d2 = p0 - 2 * p1 + p2
    return {"p1": float(gammaincc(2 ** (m - 2), d1 / 2.0)), "p2": float(gammaincc(2 ** (m - 3), d2 / 2.0))}


def nist_dft_spectral(b) -> float:
    b = _bits(b)
    n = len(b)
    x = 2 * b - 1
    mod = np.abs(np.fft.fft(x))[: n // 2]
    T = math.sqrt(math.log(1 / 0.05) * n)
    N0 = 0.95 * n / 2
    N1 = np.sum(mod < T)
    d = (N1 - N0) / math.sqrt(n * 0.95 * 0.05 / 4)
    return float(erfc(abs(d) / math.sqrt(2)))


def nist_sp800_22_battery(b, n_sequences: int = 10, alpha: float = 0.01) -> Dict[str, object]:
    """
    Découpe le flux en n_sequences séquences, applique les 8 tests, rapporte la proportion de succès
    et l'uniformité des p-values (procédure NIST §4.2). Proportion min acceptable :
    (1-alpha) - 3 sqrt(alpha(1-alpha)/n_seq).
    """
    b = _bits(b)
    L = len(b) // n_sequences
    if L < 1000:
        raise ValueError("Flux trop court : >= 1000 bits par séquence requis (idéalement 10^6).")
    m_apen = max(2, min(10, int(math.log2(L)) - 6))
    m_ser = max(3, min(16, int(math.log2(L)) - 3))
    tests = {
        "frequency": nist_frequency, "block_frequency": nist_block_frequency, "runs": nist_runs,
        "longest_run": nist_longest_run_ones, "cusum_fwd": nist_cumulative_sums,
        "approx_entropy": lambda s: nist_approximate_entropy(s, m_apen),
        "serial_p1": lambda s: nist_serial(s, m_ser)["p1"], "dft_spectral": nist_dft_spectral,
    }
    res = {}
    min_prop = (1 - alpha) - 3 * math.sqrt(alpha * (1 - alpha) / n_sequences)
    for name, fn in tests.items():
        ps = np.array([fn(b[i * L:(i + 1) * L]) for i in range(n_sequences)], dtype=float)
        ps = ps[np.isfinite(ps)]
        prop = float(np.mean(ps >= alpha)) if len(ps) else float("nan")
        unif = float(stats.kstest(ps, "uniform").pvalue) if len(ps) >= 5 else float("nan")
        res[name] = {"proportion": prop, "uniformity_p": unif, "pass": bool(prop >= min_prop)}
    res["_summary"] = {"n_sequences": n_sequences, "bits_per_sequence": L, "min_proportion": min_prop,
                       "all_pass": all(v["pass"] for k, v in res.items() if not k.startswith("_"))}
    return res


# ============================================================================
# C. NIST SP 800-90B (4 estimateurs non-IID)
# ============================================================================
def _upper(p: float, L: int) -> float:
    return min(1.0, p + 2.576 * math.sqrt(max(p * (1 - p), 0) / max(1, L - 1)))


def mcv_estimate(x) -> float:
    x = np.asarray(x)
    L = len(x)
    _, c = np.unique(x, return_counts=True)
    return -math.log2(_upper(c.max() / L, L))


def markov_estimate_binary(b) -> float:
    b = _bits(b)
    L = len(b)
    p1 = b.mean()
    p0 = 1 - p1
    a, c = b[:-1], b[1:]
    n0, n1 = np.sum(a == 0), np.sum(a == 1)
    P01 = np.sum((a == 0) & (c == 1)) / n0 if n0 else 0.0
    P11 = np.sum((a == 1) & (c == 1)) / n1 if n1 else 0.0
    P00, P10 = 1 - P01, 1 - P11
    seqs = [p0 * P00 ** 127, p0 * P01 ** 64 * P10 ** 63, p0 * P01 * P11 ** 126,
            p1 * P10 * P00 ** 126, p1 * P10 ** 64 * P01 ** 63, p1 * P11 ** 127]
    pmax = max(seqs)
    return float(min(-math.log2(pmax) / 128.0, 1.0)) if pmax > 0 else 1.0


def _tuple_vals(b: np.ndarray, W: int) -> np.ndarray:
    n = len(b) - W + 1
    v = np.zeros(n, dtype=np.uint64)
    for j in range(W):
        v = (v << np.uint64(1)) | b[j: j + n].astype(np.uint64)
    return v


def t_tuple_and_lrs_estimates(b, max_len: int = 48) -> Dict[str, float]:
    b = _bits(b)
    L = len(b)
    pmax_tuple, t = 0.0, 0
    counts_by_W = {}
    for W in range(1, max_len + 1):
        _, c = np.unique(_tuple_vals(b, W), return_counts=True)
        counts_by_W[W] = c
        if c.max() >= 35:
            t = W
            pmax_tuple = max(pmax_tuple, (c.max() / (L - W + 1)) ** (1.0 / W))
        else:
            break
    h_tuple = -math.log2(_upper(pmax_tuple, L)) if t else 1.0
    # LRS : u = t+1 ... v = plus longue sous-chaîne répétée
    u = t + 1
    pmax_lrs = 0.0
    W = u
    while W <= max_len:
        c = counts_by_W.get(W)
        if c is None:
            _, c = np.unique(_tuple_vals(b, W), return_counts=True)
        if c.max() < 2:
            break
        n_w = L - W + 1
        P_W = np.sum(c * (c - 1) / 2.0) / (n_w * (n_w - 1) / 2.0)
        pmax_lrs = max(pmax_lrs, P_W ** (1.0 / W))
        W += 1
    h_lrs = -math.log2(_upper(pmax_lrs, L)) if pmax_lrs > 0 else 1.0
    return {"t_tuple": float(h_tuple), "lrs": float(h_lrs), "t": t, "v_lrs": W - 1}


def sp800_90b_min_entropy(b, max_bits: int = 1_000_000) -> Dict[str, float]:
    """Min-entropie par bit (1.0 = parfait). Réimplémentation PARTIELLE ; valeur finale = min des 4."""
    b = _bits(b)[:max_bits]
    tt = t_tuple_and_lrs_estimates(b)
    est = {"mcv": mcv_estimate(b), "markov": markov_estimate_binary(b), "t_tuple": tt["t_tuple"], "lrs": tt["lrs"]}
    est["h_min"] = float(min(est.values()))
    est["n_bits"] = int(len(b))
    est["note"] = "4/10 estimateurs non-IID ; certifier avec ea_non_iid (NIST officiel)"
    return est


# ============================================================================
# D. BATTERIE PIT
# ============================================================================
def _ad_inf_cdf(z: float) -> float:
    """Marsaglia & Marsaglia (2004) : CDF asymptotique de A^2."""
    if z <= 0:
        return 0.0
    if z < 2:
        return math.exp(-1.2337141 / z) / math.sqrt(z) * (2.00012 + (0.247105 - (0.0649821 - (0.0347962 - (0.011672 - 0.00168691 * z) * z) * z) * z) * z)
    return math.exp(-math.exp(1.0776 - (2.30695 - (0.43424 - (0.082433 - (0.008056 - 0.0003146 * z) * z) * z) * z) * z))


def anderson_darling_uniform(u) -> Dict[str, float]:
    u = np.sort(np.clip(np.asarray(u, dtype=float), 1e-12, 1 - 1e-12))
    n = len(u)
    i = np.arange(1, n + 1)
    A2 = -n - np.mean((2 * i - 1) * (np.log(u) + np.log(1 - u[::-1])))
    return {"A2": float(A2), "p_value": float(max(0.0, 1.0 - _ad_inf_cdf(A2)))}


def ljung_box(x, lags: int = 20) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    den = np.dot(x, x)
    rho = np.array([np.dot(x[:-k], x[k:]) / den for k in range(1, lags + 1)])
    Q = n * (n + 2) * np.sum(rho ** 2 / (n - np.arange(1, lags + 1)))
    return {"Q": float(Q), "p_value": float(stats.chi2.sf(Q, lags))}


def berkowitz_test(u) -> Dict[str, float]:
    """z = Phi^-1(u) ; H0 : z ~ N(0,1) i.i.d. contre AR(1) gaussien de moyenne/variance libres. LR ~ chi2(3)."""
    z = stats.norm.ppf(np.clip(np.asarray(u, dtype=float), 1e-12, 1 - 1e-12))
    y, x = z[1:], z[:-1]
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = max(1e-18, float(np.mean(resid ** 2)))
    n = len(y)
    ll1 = -0.5 * n * (math.log(2 * math.pi * s2) + 1)
    ll0 = -0.5 * n * math.log(2 * math.pi) - 0.5 * float(np.sum(y ** 2))
    LR = -2 * (ll0 - ll1)
    return {"LR": float(LR), "p_value": float(stats.chi2.sf(LR, 3)), "mu": float(beta[0]), "rho": float(beta[1]),
            "sigma": math.sqrt(s2)}


def pit_battery(u, lags: int = 20) -> Dict[str, object]:
    u = np.clip(np.asarray(u, dtype=float), 1e-12, 1 - 1e-12)
    z = stats.norm.ppf(u)
    out = {
        "ks_p": float(stats.kstest(u, "uniform").pvalue),
        "anderson_darling": anderson_darling_uniform(u),
        "cramer_von_mises_p": float(stats.cramervonmises(u, "uniform").pvalue),
        "ljung_box_z": ljung_box(z, lags),
        "ljung_box_z2": ljung_box(z ** 2, lags),
        "berkowitz": berkowitz_test(u),
    }
    ps = [out["ks_p"], out["anderson_darling"]["p_value"], out["cramer_von_mises_p"],
          out["ljung_box_z"]["p_value"], out["ljung_box_z2"]["p_value"], out["berkowitz"]["p_value"]]
    out["min_p_bonferroni"] = float(min(1.0, min(ps) * len(ps)))
    out["model_rejected_at_1pct"] = bool(out["min_p_bonferroni"] < 0.01)
    return out


# ============================================================================
# E. SURROGATES
# ============================================================================
def make_surrogate(x: np.ndarray, method: str, rng: np.random.Generator, n_iter: int = 50) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if method == "shuffle":
        return rng.permutation(x)
    n = len(x)
    if method == "phase":
        F = np.fft.rfft(x - x.mean())
        ph = rng.uniform(0, 2 * np.pi, len(F))
        ph[0] = 0.0
        if n % 2 == 0:
            ph[-1] = 0.0
        return np.fft.irfft(np.abs(F) * np.exp(1j * ph), n) + x.mean()
    if method == "iaaft":
        amp = np.abs(np.fft.rfft(x))
        sorted_x = np.sort(x)
        y = rng.permutation(x)
        for _ in range(n_iter):
            Y = np.fft.rfft(y)
            y = np.fft.irfft(amp * np.exp(1j * np.angle(Y)), n)
            y = sorted_x[np.argsort(np.argsort(y))]
        return y
    raise ValueError("method in {'shuffle','phase','iaaft'}")


def surrogate_test(stat_fn: Callable[[np.ndarray], float], x, n_surr: int = 199, method: str = "shuffle",
                   alternative: str = "greater", seed: int = 0) -> Dict[str, float]:
    """
    p-value de Monte-Carlo de stat_fn(x) contre la distribution sous H0 :
      shuffle -> i.i.d. ; phase -> processus linéaire gaussien ; iaaft -> linéaire + marginale conservée.
    Toute métrique de chaos (Lyapunov, RQA, BDS, TE, MF-DFA) DOIT passer par ce test.
    """
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    obs = float(stat_fn(x))
    null = np.array([stat_fn(make_surrogate(x, method, rng)) for _ in range(n_surr)], dtype=float)
    null = null[np.isfinite(null)]
    if alternative == "greater":
        p = (1 + np.sum(null >= obs)) / (1 + len(null))
    elif alternative == "less":
        p = (1 + np.sum(null <= obs)) / (1 + len(null))
    else:
        c = np.median(null)
        p = (1 + np.sum(np.abs(null - c) >= abs(obs - c))) / (1 + len(null))
    sd = float(null.std(ddof=1)) if len(null) > 1 else float("nan")
    return {"observed": obs, "null_mean": float(null.mean()), "null_sd": sd,
            "z": float((obs - null.mean()) / sd) if sd and sd > 0 else float("nan"),
            "p_value": float(p), "method": method, "n_surr": int(len(null))}


# ============================================================================
# F. EXPLOITABILITÉ
# ============================================================================
def exploitability_verdict(n_success: int, n_trials: int, p_break_even: float, alpha: float = 0.01,
                           n_tests: int = 1) -> Dict[str, object]:
    """
    Exploitable seulement si la borne BASSE de l'IC (Wilson, corrigée Bonferroni pour n_tests)
    dépasse la probabilité de break-even p* (payout ou spread). Sinon : biais non exploitable.
    """
    a = alpha / max(1, n_tests)
    z = stats.norm.isf(a / 2)
    p = n_success / n_trials
    den = 1 + z ** 2 / n_trials
    centre = (p + z ** 2 / (2 * n_trials)) / den
    half = z * math.sqrt(p * (1 - p) / n_trials + z ** 2 / (4 * n_trials ** 2)) / den
    lo, hi = centre - half, centre + half
    return {"p_hat": p, "ci_low": lo, "ci_high": hi, "p_break_even": p_break_even,
            "exploitable": bool(lo > p_break_even),
            "verdict": "EXPLOITABLE (à confirmer sur holdout)" if lo > p_break_even else "NON EXPLOITABLE"}


# ============================================================================
# G. ATTAQUE PRNG : DÉMONSTRATION MT19937 + FAISABILITÉ
# ============================================================================
def _unshift_right_xor(y: int, shift: int) -> int:
    res = y
    for _ in range(32 // shift + 1):
        res = y ^ (res >> shift)
    return res & 0xFFFFFFFF


def _unshift_left_xor_mask(y: int, shift: int, mask: int) -> int:
    res = y
    for _ in range(32 // shift + 1):
        res = y ^ ((res << shift) & mask)
    return res & 0xFFFFFFFF


def mt19937_untemper(y: int) -> int:
    y = _unshift_right_xor(y, 18)
    y = _unshift_left_xor_mask(y, 15, 0xEFC60000)
    y = _unshift_left_xor_mask(y, 7, 0x9D2C5680)
    y = _unshift_right_xor(y, 11)
    return y


def mt19937_recover_and_predict(outputs32: Sequence[int], n_predict: int = 10) -> List[int]:
    """
    À partir de 624 sorties 32 bits CONSÉCUTIVES et NON TRANSFORMÉES d'un MT19937, reconstruit
    l'état interne et prédit les sorties suivantes. (Python `random` est un MT19937.)
    """
    import random as _random
    if len(outputs32) < 624:
        raise ValueError("624 sorties 32 bits consécutives requises.")
    state = [mt19937_untemper(int(o)) for o in outputs32[-624:]]
    g = _random.Random()
    g.setstate((3, tuple(state + [624]), None))
    return [g.getrandbits(32) for _ in range(n_predict)]


def prng_attack_feasibility(generator: str = "unknown", full_outputs_observed: bool = False,
                            bits_lost_per_output: int = 32, csprng_claimed: bool = True) -> Dict[str, str]:
    """
    Évaluation honnête : une attaque d'état n'est possible QUE si l'on observe des sorties brutes
    d'un générateur linéaire (MT19937, LCG, xorshift). Prix arrondis, transformés (Box-Muller,
    inversion de CDF, multiplication par sigma) et mélangés à d'autres flux = information détruite.
    """
    if csprng_claimed or generator.lower() in {"chacha20", "aes-ctr", "hmac-drbg", "hash-drbg", "ctr-drbg"}:
        return {"feasible": "NON",
                "why": "CSPRNG : prédire la sortie suivante équivaut à casser la primitive (>= 2^128 opérations). "
                       "Seuls restent : défauts d'implémentation (seed faible, réutilisation), et la STRUCTURE "
                       "contractuelle/régime (A2/A3), pas le générateur."}
    if generator.lower().startswith("mt19937"):
        if full_outputs_observed and bits_lost_per_output == 0:
            return {"feasible": "OUI", "why": "624 sorties 32 bits brutes -> état complet (voir mt19937_recover_and_predict)."}
        return {"feasible": "TRÈS IMPROBABLE",
                "why": f"{bits_lost_per_output} bits perdus/sortie : système GF(2) sous-déterminé ; il faudrait "
                       "connaître exactement la transformation sortie->prix et observer chaque tirage."}
    if generator.lower().startswith("lcg"):
        return {"feasible": "POSSIBLE si sorties tronquées connues",
                "why": "LCG tronqué : réduction de réseau (LLL) si la troncature et le module sont connus."}
    return {"feasible": "INCONNU", "why": "Générateur non identifié : commencer par SP800-22/90B/PIT sur flux brut."}


if __name__ == "__main__":
    import random

    rng = np.random.default_rng(11)
    good = rng.integers(0, 2, 200_000).astype(np.uint8)
    # Générateur biaisé : P(1)=0.51 et dépendance de Markov
    bad = np.zeros(200_000, dtype=np.uint8)
    for t in range(1, len(bad)):
        bad[t] = 1 if rng.random() < (0.56 if bad[t - 1] else 0.46) else 0
    bat_good = nist_sp800_22_battery(good, n_sequences=10)
    bat_bad = nist_sp800_22_battery(bad, n_sequences=10)
    assert bat_good["_summary"]["all_pass"], bat_good
    assert not bat_bad["_summary"]["all_pass"]
    h_good = sp800_90b_min_entropy(good[:100_000])
    h_bad = sp800_90b_min_entropy(bad[:100_000])
    assert h_good["h_min"] > 0.9 and h_bad["h_min"] < h_good["h_min"], (h_good, h_bad)
    # PIT : bonne loi vs mauvaise loi (on suppose N(0,1) alors que c'est Student t3)
    x_norm = rng.normal(size=5000)
    x_t3 = rng.standard_t(3, size=5000)
    assert not pit_battery(pit_uniforms(x_norm, stats.norm.cdf))["model_rejected_at_1pct"]
    assert pit_battery(pit_uniforms(x_t3, stats.norm.cdf))["model_rejected_at_1pct"]
    # Surrogates : un AR(1) a une ACF lag-1 significative vs shuffle ; un bruit blanc non
    ar = np.zeros(3000)
    for t in range(1, 3000):
        ar[t] = 0.3 * ar[t - 1] + rng.normal()
    acf1 = lambda v: float(np.corrcoef(v[:-1], v[1:])[0, 1])
    assert surrogate_test(acf1, ar, 99, "shuffle")["p_value"] < 0.05
    assert surrogate_test(acf1, rng.normal(size=3000), 99, "shuffle")["p_value"] > 0.01
    # MT19937 : reconstruction réelle de l'état du `random` de Python
    g = random.Random(2026)
    outs = [g.getrandbits(32) for _ in range(624)]
    pred = mt19937_recover_and_predict(outs, 5)
    real = [g.getrandbits(32) for _ in range(5)]
    assert pred == real, (pred, real)
    # Exploitabilité : 50.4 % sur 100k contrats payés 0.95 -> non exploitable (p* = 0.513)
    ev = exploitability_verdict(50_400, 100_000, 1 / 1.95)
    assert not ev["exploitable"]
    print(f"SP800-22 bon={bat_good['_summary']['all_pass']} biaisé={bat_bad['_summary']['all_pass']} | "
          f"H_min bon={h_good['h_min']:.3f} biaisé={h_bad['h_min']:.3f}")
    print(f"MT19937 : 5/5 sorties futures prédites exactement | {ev['verdict']} (IC bas {ev['ci_low']:.4f} < p* {ev['p_break_even']:.4f})")
    print("prng_forensics : 7/7 auto-tests OK")
