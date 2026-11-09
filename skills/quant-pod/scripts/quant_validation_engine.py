"""
quant_validation_engine.py
==========================
Moteur de validation antagoniste (le "Boost") du Quant Pod.

Principe : aucune métrique n'est acceptée si elle n'est pas
  (1) calculée par ce code sur des données réelles,
  (2) pénalisée pour le nombre TOTAL d'essais enregistrés dans le registre (ledger),
  (3) comparée à ce que la même procédure de recherche produit sur un MODÈLE NUL
      (marché sans edge, mêmes coûts, même grille de paramètres).

Dépendances : numpy, scipy (aucune autre).

Contenu :
  - ResearchLedger            : registre append-only des essais (K réel pour le DSR) + verrou du holdout
  - sharpe / psr / dsr        : Probabilistic & Deflated Sharpe Ratio (Bailey & López de Prado 2012/2014)
  - pbo_cscv                  : Probability of Backtest Overfitting par CSCV (Bailey, Borwein, LdP, Zhu 2015)
  - purged_kfold / cpcv_splits: validation croisée purgée + embargo, et combinatoire (LdP 2018)
  - plateau_score             : stabilité de la surface paramétrique (pic vs plateau)
  - cost_stress               : stress des frictions (x2, x3)
  - null_calibration          : p-value "best-of-grid" sous modèle nul simulé (type Reality Check de White)
  - holm / benjamini_hochberg : corrections de tests multiples
  - stationary_bootstrap_ci   : IC de la moyenne robustes à l'autocorrélation (Politis & Romano 1994)
  - evaluate_gates            : verdict final unique, seuils centralisés dans GATES
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from itertools import combinations
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import kurtosis, norm, skew

EULER_GAMMA = 0.5772156649015329

# ----------------------------------------------------------------------------
# Seuils centralisés (UNE seule source de vérité pour tous les agents)
# ----------------------------------------------------------------------------
GATES: Dict[str, float] = {
    "min_trades": 200,              # en dessous : pas de conclusion statistique possible
    "dsr_min": 0.95,                # Deflated Sharpe Ratio (probabilité)
    "pbo_max": 0.20,                # Probability of Backtest Overfitting
    "null_pvalue_max": 0.05,        # p-value best-of-grid vs modèle nul
    "plateau_min": 0.50,            # fraction de voisins du meilleur point restant "bons"
    "cost_stress_mult": 2.0,        # multiplicateur de frais pour le stress
    "cost_stress_min_mean": 0.0,    # l'espérance nette doit rester > 0 sous frais x2
    "oos_decay_max": 0.50,          # perte max de Sharpe OOS vs IS (50 %)
}


# ============================================================================
# 1. REGISTRE DES ESSAIS (ledger) + VERROU DU HOLDOUT
# ============================================================================
class ResearchLedger:
    """
    Registre append-only (JSONL). Chaque backtest lancé = 1 ligne, même s'il est mauvais.
    C'est la seule façon honnête de connaître K (nombre d'essais) pour le DSR.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            open(path, "a", encoding="utf-8").close()

    def _rows(self) -> List[dict]:
        rows = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def log_trial(self, hypothesis_id: str, params: dict, sr_per_period: float,
                  n_obs: int, extra: Optional[dict] = None) -> None:
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "type": "trial",
            "hypothesis_id": hypothesis_id,
            "params": params,
            "sr_per_period": float(sr_per_period) if np.isfinite(sr_per_period) else None,
            "n_obs": int(n_obs),
            "extra": extra or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def trials(self, hypothesis_id: Optional[str] = None) -> List[dict]:
        rows = [r for r in self._rows() if r.get("type") == "trial"]
        if hypothesis_id is not None:
            rows = [r for r in rows if r["hypothesis_id"] == hypothesis_id]
        return rows

    def n_trials(self) -> int:
        """K global : TOUS les essais de la session/projet comptent (pas seulement l'hypothèse courante)."""
        return len(self.trials())

    def trial_sharpes(self) -> np.ndarray:
        s = [r["sr_per_period"] for r in self.trials() if r["sr_per_period"] is not None]
        return np.asarray(s, dtype=float)

    # --- Verrou du holdout : on enregistre l'empreinte du fichier, on ne l'ouvre qu'une fois
    def register_holdout(self, file_path: str) -> str:
        digest = _sha256(file_path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "type": "holdout_registered",
                                "file": os.path.abspath(file_path), "sha256": digest}) + "\n")
        return digest

    def open_holdout(self, file_path: str) -> None:
        """Lève une erreur si le holdout a déjà été ouvert ou si le fichier a été modifié."""
        rows = self._rows()
        reg = [r for r in rows if r.get("type") == "holdout_registered"
               and r["file"] == os.path.abspath(file_path)]
        if not reg:
            raise RuntimeError("Holdout non enregistré : appeler register_holdout() AVANT toute recherche.")
        if any(r.get("type") == "holdout_opened" and r["file"] == os.path.abspath(file_path) for r in rows):
            raise RuntimeError("Holdout DÉJÀ ouvert une fois. Toute nouvelle évaluation est contaminée.")
        if _sha256(file_path) != reg[-1]["sha256"]:
            raise RuntimeError("Le fichier holdout a été modifié depuis son enregistrement.")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "type": "holdout_opened",
                                "file": os.path.abspath(file_path)}) + "\n")


def _sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# 2. SHARPE, PSR, DSR
# ============================================================================
def sharpe(r: Sequence[float]) -> float:
    """Sharpe NON annualisé, par période (par trade ou par barre)."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return float("nan")
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else float("nan")


def psr(r: Sequence[float], sr_benchmark: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio : P(SR_vrai > sr_benchmark) en tenant compte de T, skew, kurtosis."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    T = len(r)
    if T < 10:
        return float("nan")
    sr = sharpe(r)
    if not np.isfinite(sr):
        return float("nan")
    g3 = float(skew(r, bias=False))
    g4 = float(kurtosis(r, fisher=False, bias=False))
    denom = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return float("nan")
    return float(norm.cdf((sr - sr_benchmark) * math.sqrt(T - 1.0) / math.sqrt(denom)))


def expected_max_sharpe(n_trials: int, var_trial_sharpes: float) -> float:
    """E[max SR] de K essais sans edge (SR_vrai = 0), dispersion = variance observée des SR des essais."""
    if n_trials <= 1 or var_trial_sharpes <= 0:
        return 0.0
    sd = math.sqrt(var_trial_sharpes)
    return sd * ((1 - EULER_GAMMA) * norm.ppf(1 - 1.0 / n_trials)
                 + EULER_GAMMA * norm.ppf(1 - 1.0 / (n_trials * math.e)))


def dsr(r: Sequence[float], trial_sharpes: Sequence[float]) -> Dict[str, float]:
    """
    Deflated Sharpe Ratio. trial_sharpes = SR (même fréquence que r) de TOUS les essais du registre.
    Sous H0 (SR_vrai = 0), l'écart-type théorique d'un estimateur de Sharpe sur T observations
    est borné par ~1.5 / sqrt(T - 1) (évite qu'un vrai signal fort + son inverse n'explosent la variance nulle).
    """
    r_arr = np.asarray(r, dtype=float)
    r_arr = r_arr[np.isfinite(r_arr)]
    T = max(2, len(r_arr))
    ts = np.asarray([x for x in trial_sharpes if x is not None and np.isfinite(x)], dtype=float)
    K = max(1, len(ts))
    null_var_cap = (1.5 / math.sqrt(T - 1.0)) ** 2
    sample_var = float(ts.var(ddof=1)) if len(ts) > 1 else (1.0 / (T - 1.0))
    var = min(sample_var, null_var_cap) if sample_var > 0 else (1.0 / (T - 1.0))
    sr0 = expected_max_sharpe(K, var)
    return {"sr": sharpe(r_arr), "sr0_noise_threshold": sr0, "n_trials": K,
            "dsr": psr(r_arr, sr0)}


# ============================================================================
# 3. PBO par CSCV (Combinatorially Symmetric Cross-Validation)
# ============================================================================
def pbo_cscv(perf_matrix: np.ndarray, n_blocks: int = 16,
             metric: Callable[[np.ndarray], np.ndarray] = None) -> Dict[str, float]:
    """
    perf_matrix : T x N, rendements par période de N configurations (0 quand pas en position),
                  alignés sur le même axe temporel.
    Retourne PBO = P(la meilleure config IS finit sous la médiane OOS).
    """
    M = np.asarray(perf_matrix, dtype=float)
    T, N = M.shape
    if N < 2:
        raise ValueError("PBO exige au moins 2 configurations.")
    n_blocks = n_blocks - (n_blocks % 2)
    if T < n_blocks * 5:
        raise ValueError("Trop peu d'observations pour CSCV.")
    if metric is None:
        def metric(X):
            sd = X.std(axis=0, ddof=1)
            sd[sd == 0] = np.nan
            return X.mean(axis=0) / sd
    blocks = np.array_split(np.arange(T), n_blocks)
    logits, degrad = [], []
    for is_combo in combinations(range(n_blocks), n_blocks // 2):
        is_idx = np.concatenate([blocks[b] for b in is_combo])
        oos_idx = np.concatenate([blocks[b] for b in range(n_blocks) if b not in is_combo])
        is_perf = np.nan_to_num(metric(M[is_idx]), nan=-np.inf)
        oos_perf = np.nan_to_num(metric(M[oos_idx]), nan=-np.inf)
        best = int(np.argmax(is_perf))
        rank = (oos_perf < oos_perf[best]).sum() + 0.5 * ((oos_perf == oos_perf[best]).sum() - 1) + 1
        w = rank / (N + 1.0)
        logits.append(math.log(w / (1 - w)))
        degrad.append((is_perf[best], oos_perf[best]))
    logits = np.asarray(logits)
    d = np.asarray(degrad)
    finite = np.isfinite(d).all(axis=1)
    slope = float(np.polyfit(d[finite, 0], d[finite, 1], 1)[0]) if finite.sum() > 2 else float("nan")
    return {"pbo": float(np.mean(logits <= 0)), "n_combinations": int(len(logits)),
            "is_to_oos_slope": slope}


# ============================================================================
# 4. VALIDATION CROISÉE PURGÉE / CPCV
# ============================================================================
def purged_kfold(n: int, k: int = 5, horizon: int = 1, embargo_pct: float = 0.01):
    """Yield (train_idx, test_idx). Purge des 'horizon' obs avant le test, embargo après."""
    idx = np.arange(n)
    emb = int(n * embargo_pct)
    for test in np.array_split(idx, k):
        a, b = test[0], test[-1] + 1
        train = np.concatenate([idx[:max(0, a - horizon)], idx[min(n, b + emb):]])
        yield train, test


def cpcv_splits(n: int, n_groups: int = 6, k_test: int = 2, horizon: int = 1, embargo_pct: float = 0.01):
    """Combinatorial Purged CV : C(n_groups, k_test) découpages, purge + embargo à chaque frontière."""
    idx = np.arange(n)
    groups = np.array_split(idx, n_groups)
    emb = int(n * embargo_pct)
    for test_groups in combinations(range(n_groups), k_test):
        test = np.concatenate([groups[g] for g in test_groups])
        mask = np.ones(n, dtype=bool)
        for g in test_groups:
            a, b = groups[g][0], groups[g][-1] + 1
            mask[max(0, a - horizon):min(n, b + emb)] = False
        yield idx[mask], test


# ============================================================================
# 5. STABILITÉ PARAMÉTRIQUE (plateau vs pic)
# ============================================================================
def plateau_score(grid_results: Dict[Tuple, float]) -> Dict[str, object]:
    """
    grid_results : {(p1_index, p2_index, ...): metric} sur une grille régulière (indices entiers).
    Score = fraction des voisins (distance de Chebyshev 1) du meilleur point dont la métrique
    est > 0 ET >= 50 % du meilleur. Un pic isolé donne ~0, un plateau ~1.
    """
    if not grid_results:
        return {"best": None, "plateau_score": 0.0}
    best_key = max(grid_results, key=lambda k: grid_results[k])
    best_val = grid_results[best_key]
    neigh = []
    for key, val in grid_results.items():
        if key == best_key:
            continue
        if max(abs(a - b) for a, b in zip(key, best_key)) == 1:
            neigh.append(val)
    if not neigh or best_val <= 0:
        return {"best": best_key, "best_value": best_val, "plateau_score": 0.0, "n_neighbors": len(neigh)}
    good = [v for v in neigh if v > 0 and v >= 0.5 * best_val]
    return {"best": best_key, "best_value": best_val,
            "plateau_score": len(good) / len(neigh), "n_neighbors": len(neigh)}


# ============================================================================
# 6. STRESS DES FRICTIONS
# ============================================================================
def cost_stress(gross: Sequence[float], cost: Sequence[float],
                mults: Iterable[float] = (1.0, 1.5, 2.0, 3.0)) -> Dict[float, Dict[str, float]]:
    g = np.asarray(gross, dtype=float)
    c = np.asarray(cost, dtype=float)
    out = {}
    for m in mults:
        net = g - m * c
        out[float(m)] = {"mean": float(net.mean()), "sharpe": sharpe(net),
                         "t": float(net.mean() / (net.std(ddof=1) / math.sqrt(len(net)))) if len(net) > 2 else float("nan")}
    return out


# ============================================================================
# 7. CALIBRATION SOUS MODÈLE NUL (le test le plus important)
# ============================================================================
def null_calibration(search_fn: Callable[[np.ndarray], float],
                     null_generator: Callable[[np.random.Generator], np.ndarray],
                     observed_stat: float, n_sims: int = 200, seed: int = 0) -> Dict[str, float]:
    """
    search_fn(data) -> statistique du MEILLEUR résultat que TA procédure de recherche trouve
                       (ex. meilleur t-stat de toute la grille, après coûts).
    null_generator(rng) -> données simulées SANS edge (GBM, marche aléatoire, Poisson compensé...)
                           avec les mêmes caractéristiques (longueur, volatilité, spread).
    p-value = P(best-of-grid sous le nul >= observé). Intègre automatiquement le data-snooping de la grille.
    """
    rng = np.random.default_rng(seed)
    sims = np.array([search_fn(null_generator(rng)) for _ in range(n_sims)], dtype=float)
    sims = sims[np.isfinite(sims)]
    p = (1.0 + np.sum(sims >= observed_stat)) / (1.0 + len(sims))
    return {"observed": float(observed_stat), "null_mean": float(sims.mean()),
            "null_p95": float(np.quantile(sims, 0.95)), "null_max": float(sims.max()),
            "p_value": float(p), "n_sims": int(len(sims))}


# ============================================================================
# 8. TESTS MULTIPLES & BOOTSTRAP
# ============================================================================
def holm(pvals: Sequence[float], alpha: float = 0.05) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    m = len(p)
    reject = np.zeros(m, dtype=bool)
    for rank, i in enumerate(order):
        if p[i] <= alpha / (m - rank):
            reject[i] = True
        else:
            break
    return reject


def benjamini_hochberg(pvals: Sequence[float], q: float = 0.05) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    thresh = q * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    reject = np.zeros(m, dtype=bool)
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        reject[order[:kmax + 1]] = True
    return reject


def stationary_bootstrap_ci(x: Sequence[float], mean_block: float = 10.0, n_boot: int = 2000,
                            alpha: float = 0.05, seed: int = 0) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=int)
        idx[0] = rng.integers(n)
        jumps = rng.random(n) < p
        starts = rng.integers(n, size=n)
        for t in range(1, n):
            idx[t] = starts[t] if jumps[t] else (idx[t - 1] + 1) % n
        means[b] = x[idx].mean()
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


# ============================================================================
# 9. VERDICT UNIQUE
# ============================================================================
def evaluate_gates(n_trades: int, dsr_value: float, pbo_value: Optional[float],
                   null_pvalue: Optional[float], plateau: Optional[float],
                   stressed_mean: Optional[float], oos_decay: Optional[float] = None,
                   gates: Dict[str, float] = GATES) -> Dict[str, object]:
    """Toutes les portes doivent passer. Une porte non évaluée (None) = ÉCHEC (pas de preuve = pas de validation)."""
    checks = {
        "G0_echantillon": n_trades >= gates["min_trades"],
        "G1_dsr": dsr_value is not None and np.isfinite(dsr_value) and dsr_value >= gates["dsr_min"],
        "G2_pbo": pbo_value is not None and pbo_value <= gates["pbo_max"],
        "G3_modele_nul": null_pvalue is not None and null_pvalue <= gates["null_pvalue_max"],
        "G4_plateau": plateau is not None and plateau >= gates["plateau_min"],
        "G5_frais_x2": stressed_mean is not None and stressed_mean > gates["cost_stress_min_mean"],
    }
    if oos_decay is not None:
        checks["G6_decroissance_oos"] = oos_decay <= gates["oos_decay_max"]
    verdict = "VALIDÉE (candidate paper-trading)" if all(checks.values()) else "REJETÉE"
    return {"checks": checks, "verdict": verdict, "failed": [k for k, v in checks.items() if not v]}


if __name__ == "__main__":
    # Auto-test : une stratégie sans edge doit être rejetée, un edge planté doit être détecté par le PSR.
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 1, 2000)
    edge = rng.normal(0.12, 1, 2000)
    print("PSR bruit  :", round(psr(noise), 3))
    print("PSR edge   :", round(psr(edge), 3))
    trial_srs = rng.normal(0, 0.05, 500)
    print("DSR edge (K=500):", dsr(edge, trial_srs))
    M = rng.normal(0, 1, (1600, 30))
    print("PBO bruit pur (attendu ~0.5):", pbo_cscv(M, n_blocks=10)["pbo"])
