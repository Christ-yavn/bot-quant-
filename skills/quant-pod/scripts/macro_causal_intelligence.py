"""
macro_causal_intelligence.py
============================
Moteur d'Intelligence Macro-Économique, d'Écologie de Marché, de Découverte Causale
Inter-Actifs (Double-ML / Granger-HAC) et d'Étude d'Événements Point-in-Time pour `quant-pod` v4.0.

Pourquoi ce moteur est indispensable à un vrai Quant Researcher :
Un chercheur quantitatif institutionnel (Two Sigma, Citadel, Bridgewater, AQR, Man AHL) ne
regarde jamais une série OHLCV en vase clos. Avant de poser une équation de signal, il
modélise CE QUI FAIT TOURNER LE MARCHÉ :
  1. `pit_macro_release_aligner` : Alignement Point-in-Time strict des publications économiques
     et fondamentales (`reference_period` != `release_timestamp` != `revision_vintage`), calculant
     les surprises macroéconomiques standardisées sans aucune fuite du futur.
  2. `classify_macro_liquidity_regime` : Classification causale en 4 quadrants macro-financiers
     (Croissance x Inflation : Goldilocks, Reflation, Stagflation, Déflation/Deleveraging) modulée
     par l'impulsion de liquidité nette et la structure par terme de volatilité.
  3. `cross_asset_causal_network` : Découverte causale inter-marchés inspirée de Pearl (2009) et
     du Double/Debiased Machine Learning (Chernozhukov et al., 2018). Teste si un facteur exogène
     (taux, DXY, VIX, flux ETF, stablecoins, funding, open interest, courbe des matières premières)
     prédit réellement les rendements futurs APRÈS orthogonalisation de l'auto-corrélation propre
     et des variables confondantes, avec erreurs standards Newey-West HAC et contrôle FDR
     Benjamini-Hochberg.
  4. `macro_event_study_analyzer` : Étude d'impact autour des catalyseurs économiques planifiés
     (FOMC, CPI, NFP, expirations d'options, fixings institutionnels Londres 16h00, rolls Futures,
     unlocks), décomposant Pre-Event Drift, Choc d'Annonce, Expansion/Crush de volatilité et
     Post-Event Drift (PEAD) face aux coûts réels.
  5. `diagnose_market_ecology` : Synthèse structurelle identifiant la contrepartie contrainte et
     le moteur économique primaire d'un marché (Spillover Inter-Actifs, Prime de Portage/Basis,
     Saisonnalité de Session/Fixing, Dérive Post-Catalyseur Macro, Cascade de Liquidations, ou
     Martingale Pure Sans Contrepartie).

Dépendances : numpy, scipy, pandas uniquement (zéro dépendance externe fragile).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats


# ============================================================================
# 1. ALIGNEMENT POINT-IN-TIME DES ANNONCES ÉCONOMIQUES & SURPRISES MACRO
# ============================================================================

def pit_macro_release_aligner(
    bar_timestamps: Sequence[Any],
    releases: Sequence[Dict[str, Any]],
    surprise_lookback: int = 12,
    decay_half_life_bars: Optional[float] = None,
) -> pd.DataFrame:
    """
    Aligne des publications macroéconomiques ou fondamentales sur une grille de barres de marché
    sans AUCUNE fuite temporelle (Point-in-Time Vintage Discipline) :

    Chaque élément de `releases` contient :
      - `release_ts`   : horodatage exact de publication publique (seule date admissible !)
      - `actual`       : valeur publiée à `release_ts`
      - `consensus`    : attente médiane avant l'annonce (optionnel ; sinon variation vs publication précédente)
      - `reference_ts` : période économique mesurée (ex: fin du mois précédent — ignorée si < release_ts
                         pour interdire le biais classique d'utiliser le CPI de janvier dès le 31 janvier
                         alors qu'il sort le 13 février !)

    Lève `ValueError` si `release_ts < reference_ts` (incohérence chronologique).
    Retourne un DataFrame aligné sur `bar_timestamps` avec :
      - `latest_actual`, `raw_surprise`, `surprise_z`, `bars_since_release`, `impulse_decayed`, `is_release_bar`.
    """
    bar_ts = pd.to_datetime(pd.Index(bar_timestamps), utc=True)
    n_bars = len(bar_ts)
    if n_bars == 0:
        raise ValueError("bar_timestamps ne peut pas être vide.")
    if not bar_ts.is_monotonic_increasing:
        raise ValueError("bar_timestamps doit être strictement croissant ou monotone croissant.")

    out = pd.DataFrame(
        {
            "bar_ts": bar_ts,
            "latest_actual": np.nan,
            "raw_surprise": 0.0,
            "surprise_z": 0.0,
            "bars_since_release": np.full(n_bars, np.inf, dtype=np.float64),
            "impulse_decayed": 0.0,
            "is_release_bar": np.zeros(n_bars, dtype=bool),
        }
    )
    if not releases:
        return out

    cleaned: List[Tuple[pd.Timestamp, float, Optional[float]]] = []
    for idx, row in enumerate(releases):
        if "release_ts" not in row or "actual" not in row:
            raise ValueError(f"Release #{idx} doit contenir 'release_ts' et 'actual'.")
        r_ts = pd.Timestamp(row["release_ts"])
        if r_ts.tzinfo is None:
            r_ts = r_ts.tz_localize("UTC")
        else:
            r_ts = r_ts.tz_convert("UTC")

        if "reference_ts" in row and row["reference_ts"] is not None:
            ref_ts = pd.Timestamp(row["reference_ts"])
            ref_ts = ref_ts.tz_localize("UTC") if ref_ts.tzinfo is None else ref_ts.tz_convert("UTC")
            if r_ts < ref_ts:
                raise ValueError(
                    f"Fuite temporelle détectée sur release #{idx}: release_ts ({r_ts}) < reference_ts ({ref_ts})."
                )
        act = float(row["actual"])
        cons = float(row["consensus"]) if row.get("consensus") is not None else None
        cleaned.append((r_ts, act, cons))

    cleaned.sort(key=lambda x: x[0])

    # Calcul causal des surprises standardisées uniquement sur les annonces passées [0 .. k-1]
    rel_times: List[pd.Timestamp] = []
    rel_actuals: List[float] = []
    rel_surprises: List[float] = []
    rel_zscores: List[float] = []

    for k, (r_ts, act, cons) in enumerate(cleaned):
        if cons is not None:
            surp = act - cons
        elif k > 0:
            surp = act - rel_actuals[-1]
        else:
            surp = 0.0

        hist = rel_surprises[max(0, k - int(surprise_lookback)) : k]
        if len(hist) >= 3:
            sd = float(np.std(hist, ddof=1))
            z_val = float(np.clip(surp / sd, -5.0, 5.0)) if sd > 1e-12 else 0.0
        elif len(hist) >= 1 and abs(hist[-1]) > 1e-12:
            scale = float(np.mean(np.abs(hist)))
            z_val = float(np.clip(surp / max(1e-12, scale), -5.0, 5.0))
        else:
            z_val = float(np.clip(np.sign(surp), -1.0, 1.0)) if abs(surp) > 1e-12 else 0.0

        rel_times.append(r_ts)
        rel_actuals.append(act)
        rel_surprises.append(surp)
        rel_zscores.append(z_val)

    rel_idx = pd.DatetimeIndex(rel_times)
    # Pour chaque barre t, dernière annonce telle que release_ts <= bar_ts[t]
    pos = np.searchsorted(rel_idx.asi8, bar_ts.asi8, side="right") - 1
    valid = pos >= 0

    latest_actual = np.full(n_bars, np.nan, dtype=np.float64)
    raw_surprise = np.zeros(n_bars, dtype=np.float64)
    surprise_z = np.zeros(n_bars, dtype=np.float64)
    bars_since = np.full(n_bars, np.inf, dtype=np.float64)
    is_rel_bar = np.zeros(n_bars, dtype=bool)

    act_arr = np.asarray(rel_actuals, dtype=np.float64)
    surp_arr = np.asarray(rel_surprises, dtype=np.float64)
    z_arr = np.asarray(rel_zscores, dtype=np.float64)

    latest_actual[valid] = act_arr[pos[valid]]
    raw_surprise[valid] = surp_arr[pos[valid]]
    surprise_z[valid] = z_arr[pos[valid]]

    # Première barre sur ou après chaque annonce
    first_bar_for_rel = np.searchsorted(bar_ts.asi8, rel_idx.asi8, side="left")
    for k, fb in enumerate(first_bar_for_rel):
        if 0 <= fb < n_bars:
            # Seulement si aucune annonce plus récente n'écrase déjà cette même barre
            if pos[fb] == k:
                is_rel_bar[fb] = True

    last_rel_bar = -1
    for i in range(n_bars):
        if not valid[i]:
            continue
        k = int(pos[i])
        fb = int(first_bar_for_rel[k])
        if fb <= i:
            last_rel_bar = fb
            bars_since[i] = float(i - last_rel_bar)

    hl = float(decay_half_life_bars) if (decay_half_life_bars is not None and decay_half_life_bars > 0) else 12.0
    decay_lambda = math.log(2.0) / hl
    impulse = np.where(np.isfinite(bars_since), surprise_z * np.exp(-decay_lambda * bars_since), 0.0)

    out["latest_actual"] = latest_actual
    out["raw_surprise"] = raw_surprise
    out["surprise_z"] = surprise_z
    out["bars_since_release"] = bars_since
    out["impulse_decayed"] = impulse
    out["is_release_bar"] = is_rel_bar
    return out


# ============================================================================
# 2. CLASSIFICATION CAUSALE DES 4 QUADRANTS MACRO-FINANCIERS & LIQUIDITÉ
# ============================================================================

QUADRANT_NAMES = (
    "GOLDILOCKS_EXPANSION",       # Croissance +, Inflation -
    "REFLATION_OVERHEAT",         # Croissance +, Inflation +
    "STAGFLATION_STRESS",         # Croissance -, Inflation +
    "DEFLATION_DELEVERAGING",     # Croissance -, Inflation -
)


def _causal_ewma_zscore(series: np.ndarray, span: int = 48) -> np.ndarray:
    """Z-score EWMA strictement causal (utilise [0..t] sans fuite du futur)."""
    x = np.asarray(series, dtype=np.float64)
    n = len(x)
    out = np.zeros(n, dtype=np.float64)
    if n < 3:
        return out
    alpha = 2.0 / (max(2, int(span)) + 1.0)
    mean = float(x[0]) if np.isfinite(x[0]) else 0.0
    var = 1e-6
    for t in range(1, n):
        val = float(x[t]) if np.isfinite(x[t]) else mean
        diff = val - mean
        # Standardisation par la variance connue en t-1 (strictement prévisible)
        sd_prev = math.sqrt(max(1e-12, var))
        if t >= 5:
            out[t] = float(np.clip(diff / sd_prev, -5.0, 5.0))
        mean = (1.0 - alpha) * mean + alpha * val
        var = (1.0 - alpha) * (var + alpha * diff * diff)
    return out


def classify_macro_liquidity_regime(
    growth_proxy: np.ndarray,
    inflation_proxy: np.ndarray,
    liquidity_proxy: Optional[np.ndarray] = None,
    vol_term_slope: Optional[np.ndarray] = None,
    ewma_span: int = 48,
    temperature: float = 1.0,
) -> Dict[str, Any]:
    """
    Modèle Macro-Financier à 4 Quadrants + Filtre de Liquidité & Structure par Terme de Volatilité
    (inspiré de Bridgewater Risk Parity / AQR Macro Regime Conditioning) :

      - `growth_proxy`    : impulsion croissance (ex: panier cycliques/défensifs, cuivre/or, PMI PIT, actions)
      - `inflation_proxy` : impulsion inflation/taux (ex: breakevens, énergie, rendements courts PIT)
      - `liquidity_proxy` : impulsion de liquidité nette (ex: bilan BC, offre stablecoins, spreads crédit inversés)
      - `vol_term_slope`  : pente de structure par terme de volatilité (VIX_3M - VIX_1M ; < 0 = backwardation/panique)

    Retourne :
      - `quadrant_probs` : matrice `(T, 4)` des probabilités causales sur `QUADRANT_NAMES`
      - `dominant_quadrant` : liste de longueur `T` du quadrant dominant à chaque pas `t`
      - `risk_appetite_score` : indice continu dans `[-1, +1]` combinant macro, liquidité et stress de vol
      - `current_state` : synthèse structurée au dernier pas `T - 1`.
    """
    g = np.asarray(growth_proxy, dtype=np.float64).reshape(-1)
    inf = np.asarray(inflation_proxy, dtype=np.float64).reshape(-1)
    n = min(len(g), len(inf))
    if n < 10:
        raise ValueError("Au moins 10 observations sont requises pour classify_macro_liquidity_regime.")
    g, inf = g[:n], inf[:n]

    gz = _causal_ewma_zscore(g, span=ewma_span)
    iz = _causal_ewma_zscore(inf, span=ewma_span)
    lz = _causal_ewma_zscore(liquidity_proxy[:n], span=ewma_span) if liquidity_proxy is not None else np.zeros(n)
    vz = _causal_ewma_zscore(vol_term_slope[:n], span=ewma_span) if vol_term_slope is not None else np.zeros(n)

    temp = max(0.15, float(temperature))
    # Scores log-linéaires des 4 quadrants : (+G,-I), (+G,+I), (-G,+I), (-G,-I)
    logits = np.column_stack(
        [
            (+gz - iz + 0.35 * lz) / temp,
            (+gz + iz + 0.15 * lz) / temp,
            (-gz + iz - 0.35 * lz) / temp,
            (-gz - iz - 0.25 * lz) / temp,
        ]
    )
    logits = logits - np.max(logits, axis=1, keepdims=True)
    exp_l = np.exp(logits)
    probs = exp_l / np.maximum(1e-12, np.sum(exp_l, axis=1, keepdims=True))

    dom_idx = np.argmax(probs, axis=1)
    dom_labels = [QUADRANT_NAMES[int(k)] for k in dom_idx]

    # Indice synthétique d'appétit pour le risque [-1, +1] :
    # Goldilocks (+) / Liquidité (+) / Contango vol (+), pénalisé par Stagflation & Backwardation vol
    raw_risk = 0.45 * gz - 0.25 * iz + 0.35 * lz + 0.25 * vz
    risk_appetite = np.tanh(0.65 * raw_risk)

    curr_k = int(dom_idx[-1])
    regime_counts = {name: round(float(np.mean(dom_idx == idx)), 4) for idx, name in enumerate(QUADRANT_NAMES)}
    return {
        "valid": True,
        "n_obs": n,
        "quadrant_names": list(QUADRANT_NAMES),
        "quadrant_probs": probs,
        "dominant_quadrant": dom_labels,
        "growth_z": gz,
        "inflation_z": iz,
        "liquidity_z": lz,
        "vol_term_z": vz,
        "risk_appetite_score": risk_appetite,
        "regime_occupancy": regime_counts,
        "current_state": {
            "quadrant": QUADRANT_NAMES[curr_k],
            "confidence": round(float(probs[-1, curr_k]), 4),
            "risk_appetite": round(float(risk_appetite[-1]), 4),
            "liquidity_impulse_z": round(float(lz[-1]), 4),
            "vol_term_structure_z": round(float(vz[-1]), 4),
        },
    }


# ============================================================================
# 3. DÉCOUVERTE CAUSALE INTER-ACTIFS (DOUBLE-ML PARTIALING-OUT + GRANGER HAC)
# ============================================================================

@dataclass
class CausalDriverLink:
    driver_name: str
    best_lag_bars: int
    partial_beta: float
    partial_corr: float
    t_stat_hac: float
    p_value_raw: float
    q_value_bh: float
    significant_fdr_5pct: bool
    direction: str


def _newey_west_tstat_slope(x_res: np.ndarray, y_res: np.ndarray, nw_lags: int = 5) -> Tuple[float, float, float]:
    """Régression univariée sur résidus orthogonalisés (Frisch-Waugh-Lovell / Double-ML linéaire) avec SE HAC."""
    T = len(y_res)
    sxx = float(np.sum(x_res * x_res))
    syy = float(np.sum(y_res * y_res))
    if T < 25 or sxx <= 1e-18 or syy <= 1e-18:
        return 0.0, 0.0, 1.0
    beta = float(np.sum(x_res * y_res) / sxx)
    p_corr = float(np.clip(np.sum(x_res * y_res) / math.sqrt(sxx * syy), -1.0, 1.0))
    u = y_res - beta * x_res
    if float(np.std(u, ddof=1)) <= 1e-10 * float(np.std(y_res, ddof=1)):
        return beta, p_corr, 0.0

    scores = x_res * u
    S = float(np.sum(scores * scores))
    max_l = min(int(nw_lags), max(1, T // 5))
    for lag in range(1, max_l + 1):
        w = 1.0 - lag / float(max_l + 1.0)
        gamma_l = float(np.sum(scores[lag:] * scores[:-lag]))
        S += 2.0 * w * gamma_l
    var_b = (float(T) / float(max(1, T - 2))) * max(1e-24, S) / (sxx * sxx)
    t_hac = beta / math.sqrt(var_b)
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_hac))))
    return beta, p_corr, t_hac if np.isfinite(t_hac) else 0.0


def cross_asset_causal_network(
    target_returns: np.ndarray,
    candidate_drivers: Dict[str, np.ndarray],
    max_lag: int = 6,
    ar_order: int = 3,
    fdr_alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Découverte Causale Prédictive Inter-Marchés (Pearl Causal Pruning + Double-ML Partialing-Out) :
    Pour chaque variable exogène `X_j` et délai `lag in {1 .. max_lag}` :
      1. Construit la matrice de contrôle `W_t` incluant l'histoire autorégressive propre de la cible
         `[y_{t-1} .. y_{t-p}]` ET les autres drivers retardés `X_{-j, t-lag}` (élimination des
         facteurs confondants communs !).
      2. Orthogonalise à la fois `y_t` et `X_{j, t-lag}` par rapport à `W_t` (régression Ridge-stabilisée
         type Frisch-Waugh-Lovell / Double-ML de Chernozhukov et al., 2018).
      3. Évalue l'effet causal direct retardé via t-stat Newey-West HAC et applique la correction
         multiple Benjamini-Hochberg (FDR) sur l'ensemble des `(drivers x lags)` testés.

    Retourne les vrais moteurs avancés (`verified_causal_leaders`) et un signal composite causal
    prêt à être utilisé (uniquement si ajusté sur Train puis appliqué hors-échantillon !).
    """
    y = np.asarray(target_returns, dtype=np.float64).reshape(-1)
    n = len(y)
    if n < 80:
        return {"valid": False, "reason": "Au moins 80 observations requises pour cross_asset_causal_network."}
    if not candidate_drivers:
        return {"valid": True, "n_obs": n, "links": [], "verified_causal_leaders": []}

    clean_drivers: Dict[str, np.ndarray] = {}
    for name, arr in candidate_drivers.items():
        v = np.asarray(arr, dtype=np.float64).reshape(-1)
        if len(v) < n:
            raise ValueError(f"Driver '{name}' a une longueur {len(v)} < len(target_returns)={n}.")
        v = np.nan_to_num(v[:n], nan=0.0, posinf=0.0, neginf=0.0)
        sd = float(np.std(v, ddof=1))
        clean_drivers[name] = (v - float(np.mean(v))) / sd if sd > 1e-12 else np.zeros(n, dtype=np.float64)

    max_l = max(1, min(int(max_lag), n // 6))
    p_ar = max(1, min(int(ar_order), 8))
    start = max(max_l, p_ar) + 1
    T_eff = n - start
    if T_eff < 40:
        return {"valid": False, "reason": "Échantillon utile trop court après retardement."}

    y_target = y[start:]
    ar_cols = [y[start - k : n - k] for k in range(1, p_ar + 1)]

    names = list(clean_drivers.keys())
    all_tests: List[Tuple[str, int, float, float, float, float]] = []

    for j_idx, d_name in enumerate(names):
        d_vec = clean_drivers[d_name]
        for lag in range(1, max_l + 1):
            x_cand = d_vec[start - lag : n - lag]
            if float(np.std(x_cand, ddof=1)) <= 1e-12:
                all_tests.append((d_name, lag, 0.0, 0.0, 0.0, 1.0))
                continue

            # Contrôles confondants : AR propre + autres drivers au même lag (si K raisonnable)
            other_cols = [
                clean_drivers[other][start - lag : n - lag]
                for k_idx, other in enumerate(names)
                if k_idx != j_idx
            ]
            # Limiter la dimension des contrôles à T_eff // 4 pour préserver les degrés de liberté
            max_other = max(0, (T_eff // 4) - p_ar - 1)
            W_list = [np.ones(T_eff, dtype=np.float64)] + ar_cols + other_cols[:max_other]
            W = np.column_stack(W_list)

            # Partialing-out Ridge léger (évite l'instabilité sous colinéarité entre drivers)
            wtw = W.T @ W
            reg = 1e-6 * np.eye(wtw.shape[0], dtype=np.float64)
            reg[0, 0] = 0.0
            proj = np.linalg.solve(wtw + reg, W.T)
            y_res = y_target - W @ (proj @ y_target)
            x_res = x_cand - W @ (proj @ x_cand)

            beta, p_corr, t_hac = _newey_west_tstat_slope(x_res, y_res, nw_lags=max(3, lag))
            p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_hac))))
            all_tests.append((d_name, lag, beta, p_corr, t_hac, p_val))

    # Correction FDR Benjamini-Hochberg sur l'ensemble des m = K * max_lag tests
    m_tests = len(all_tests)
    p_vals = np.asarray([row[5] for row in all_tests], dtype=np.float64)
    order = np.argsort(p_vals)
    q_vals = np.ones(m_tests, dtype=np.float64)
    running_min = 1.0
    for rank in range(m_tests - 1, -1, -1):
        orig_i = int(order[rank])
        q_raw = p_vals[orig_i] * float(m_tests) / float(rank + 1)
        running_min = min(running_min, q_raw)
        q_vals[orig_i] = min(1.0, running_min)

    # Meilleur lag causal par driver
    best_by_driver: Dict[str, CausalDriverLink] = {}
    for idx_t, (d_name, lag, beta, p_corr, t_hac, p_val) in enumerate(all_tests):
        q_v = float(q_vals[idx_t])
        cand_link = CausalDriverLink(
            driver_name=d_name,
            best_lag_bars=lag,
            partial_beta=round(beta, 6),
            partial_corr=round(p_corr, 4),
            t_stat_hac=round(t_hac, 4),
            p_value_raw=round(p_val, 6),
            q_value_bh=round(q_v, 6),
            significant_fdr_5pct=bool(q_v <= fdr_alpha and abs(t_hac) >= 1.96),
            direction="POSITIVE_SPILLOVER" if beta >= 0 else "INVERSE_SPILLOVER",
        )
        prev = best_by_driver.get(d_name)
        if prev is None or abs(t_hac) > abs(prev.t_stat_hac):
            best_by_driver[d_name] = cand_link

    links_sorted = sorted(best_by_driver.values(), key=lambda x: abs(x.t_stat_hac), reverse=True)
    verified = [asdict(lk) for lk in links_sorted if lk.significant_fdr_5pct]
    return {
        "valid": True,
        "n_obs": n,
        "n_tests_m": m_tests,
        "links": [asdict(lk) for lk in links_sorted],
        "verified_causal_leaders": verified,
    }


def build_causal_spillover_forecast(
    candidate_drivers: Dict[str, np.ndarray],
    causal_network_report: Dict[str, Any],
    n_bars: int,
    ewma_norm_span: int = 48,
) -> np.ndarray:
    """
    Construit une prévision composite strictement causale `F_t` à partir des seuls leaders causaux
    validés sur l'échantillon d'entraînement (`verified_causal_leaders`), pondérés par le signe et
    la force bornée de leur t-stat HAC d'entraînement.

    IMPORTANT : `causal_network_report` DOIT être estimé uniquement sur `[:split_idx]` (Train) pour
    que l'application sur `[split_idx:]` (Validation/Holdout) soit 100 % hors-échantillon !
    """
    out = np.zeros(int(n_bars), dtype=np.float64)
    leaders = causal_network_report.get("verified_causal_leaders", [])
    if not leaders:
        return out

    w_sum = 0.0
    for lk in leaders:
        name = lk["driver_name"]
        lag = int(lk["best_lag_bars"])
        if name not in candidate_drivers or lag < 1 or lag >= n_bars:
            continue
        raw_x = np.asarray(candidate_drivers[name], dtype=np.float64).reshape(-1)[:n_bars]
        z_x = _causal_ewma_zscore(np.nan_to_num(raw_x, nan=0.0), span=ewma_norm_span)
        # En t, `F_t` prédit `r_{t+1}` : un leader à `best_lag_bars = 1` (où `x_{t-1}` prédit `r_t`)
        # utilise donc `z_x[t]` (connu à la clôture de `t`) pour prédire `r_{t+1}` ; pour `lag >= 2`,
        # il utilise `z_x[t - (lag - 1)]` !
        shift = max(0, lag - 1)
        shifted = np.zeros(n_bars, dtype=np.float64)
        if shift == 0:
            shifted[:] = z_x
        else:
            shifted[shift:] = z_x[:-shift]
        weight = math.copysign(min(3.0, abs(float(lk["t_stat_hac"])) / 2.0), float(lk["partial_beta"]))
        out += weight * shifted
        w_sum += abs(weight)

    if w_sum > 1e-12:
        out = np.clip(out / w_sum, -5.0, 5.0)
    return out


# ============================================================================
# 4. ÉTUDE D'ÉVÉNEMENTS MACRO / CATALYSEURS PLANIFIÉS (`macro_event_study_analyzer`)
# ============================================================================

def macro_event_study_analyzer(
    returns: np.ndarray,
    event_indices: Sequence[int],
    event_surprises: Optional[Sequence[float]] = None,
    pre_window: int = 6,
    post_window: int = 12,
    roundtrip_cost_bps: float = 2.0,
) -> Dict[str, Any]:
    """
    Analyse rigoureuse de la dynamique de prix et de volatilité autour d'événements économiques
    ou structurels planifiés (FOMC, CPI, NFP, Fixing WM 16h00, Expiration Options, Roll Futures) :
      - `pre_event_drift_bps`  : dérive moyenne d'anticipation/hedging sur `[e - pre_window .. e - 1]`
      - `announcement_jump_bps`: choc moyen sur la barre d'annonce `e`
      - `post_event_pead_bps`  : dérive post-annonce sur `[e + 1 .. e + post_window]` (conditionnée au
                                 signe de la surprise si `event_surprises` est fourni !)
      - `vol_expansion_ratio`  : ratio `std(r_event) / std(r_hors_event)` (mesure le risque de gap/slippage)
      - `net_pead_tradable`    : vrai si le PEAD conditionnel net des coûts a `t_stat >= 2.0` et `EV_net > 0`.
    """
    r = np.asarray(returns, dtype=np.float64).reshape(-1)
    n = len(r)
    ev_idx = [int(i) for i in event_indices if pre_window <= int(i) < n - post_window]
    m = len(ev_idx)
    if m < 5:
        return {"valid": False, "n_events": m, "reason": "Au moins 5 événements complets requis."}

    surprises = None
    if event_surprises is not None:
        raw_s = np.asarray(event_surprises, dtype=np.float64).reshape(-1)
        if len(raw_s) == len(event_indices):
            surprises = [
                float(raw_s[k])
                for k, i in enumerate(event_indices)
                if pre_window <= int(i) < n - post_window
            ]

    pre_rets = np.zeros(m, dtype=np.float64)
    imp_rets = np.zeros(m, dtype=np.float64)
    post_signed = np.zeros(m, dtype=np.float64)

    ev_mask = np.zeros(n, dtype=bool)
    for k, e in enumerate(ev_idx):
        ev_mask[e] = True
        pre_rets[k] = float(np.sum(r[e - pre_window : e]))
        imp_rets[k] = float(r[e])
        post_cum = float(np.sum(r[e + 1 : e + 1 + post_window]))
        if surprises is not None and abs(surprises[k]) > 1e-12:
            direction = 1.0 if surprises[k] > 0 else -1.0
        elif abs(r[e]) > 1e-12:
            direction = 1.0 if r[e] > 0 else -1.0
        else:
            direction = 0.0
        post_signed[k] = direction * post_cum

    non_ev_sd = float(np.std(r[~ev_mask], ddof=1)) if np.sum(~ev_mask) > 5 else float(np.std(r, ddof=1))
    ev_sd = float(np.std(imp_rets, ddof=1))
    vol_ratio = ev_sd / max(1e-12, non_ev_sd)

    cost_dec = roundtrip_cost_bps * 1e-4
    net_post = post_signed - cost_dec
    sd_net = float(np.std(net_post, ddof=1))
    t_pead = float(np.mean(net_post) / (sd_net / math.sqrt(m))) if sd_net > 1e-18 else 0.0

    sd_pre = float(np.std(pre_rets, ddof=1))
    t_pre = float(np.mean(pre_rets) / (sd_pre / math.sqrt(m))) if sd_pre > 1e-18 else 0.0

    return {
        "valid": True,
        "n_events": m,
        "pre_event_drift_bps": round(float(np.mean(pre_rets) * 1e4), 3),
        "pre_event_t_stat": round(t_pre, 4),
        "announcement_abs_move_bps": round(float(np.mean(np.abs(imp_rets)) * 1e4), 3),
        "vol_expansion_ratio": round(vol_ratio, 4),
        "post_event_pead_gross_bps": round(float(np.mean(post_signed) * 1e4), 3),
        "post_event_pead_net_bps": round(float(np.mean(net_post) * 1e4), 3),
        "post_event_pead_t_stat": round(t_pead, 4),
        "net_pead_tradable": bool(float(np.mean(net_post)) > 0.0 and t_pead >= 2.0),
    }


# ============================================================================
# 5. DIAGNOSTIC D'ÉCOLOGIE DE MARCHÉ & CARTOGRAPHIE DES CONTREPARTIES FORCÉES
# ============================================================================

def diagnose_market_ecology(
    close: np.ndarray,
    roundtrip_cost_bps: float = 2.0,
    bar_timestamps: Optional[Sequence[Any]] = None,
    volume: Optional[np.ndarray] = None,
    carry_or_funding_rate: Optional[np.ndarray] = None,
    exogenous_drivers: Optional[Dict[str, np.ndarray]] = None,
    is_synthetic_csprng: bool = False,
) -> Dict[str, Any]:
    """
    Répond scientifiquement à la question fondamentale du Quant Researcher :
    « QU'EST-CE QUI FAIT TOURNER CE MARCHÉ, QUI EST LA CONTREPARTIE CONTRAINTE, ET QUELLE FAMILLE
    DE MÉCANISME ÉCONOMIQUE PEUT Y ENGENDRER UN ALPHA DURABLE ? »

    Inspecte simultanément :
      1. L'existence d'une contrepartie économique réelle vs générateur CSPRNG synthétique.
      2. Les liens causaux inter-marchés (`cross_asset_causal_network`).
      3. La prime structurelle de portage / funding / basis (`carry_or_funding_rate`).
      4. La saisonnalité institutionnelle d'ouverture/fixing (`bar_timestamps` heure UTC).
      5. L'asymétrie pression de volume / illiquidité (`volume`).
    """
    c = np.asarray(close, dtype=np.float64).reshape(-1)
    n = len(c)
    if n < 120:
        return {"valid": False, "reason": "Au moins 120 barres requises pour diagnose_market_ecology."}

    r = np.zeros(n, dtype=np.float64)
    r[1:] = np.diff(np.log(np.maximum(c, 1e-12)))

    if is_synthetic_csprng:
        return {
            "valid": True,
            "market_nature": "SYNTHETIC_ALGORITHMIC_CSPRNG",
            "forced_counterparty": "NONE (Contrepartie = Serveur Broker CSPRNG ; zéro flux de couverture humain)",
            "primary_economic_engine": "STATE_DEPENDENT_SDE_OR_DOOB_MARTINGALE",
            "verified_causal_leaders": [],
            "carry_regime": {"present": False},
            "session_seasonality": {"significant": False},
            "researcher_prescription": (
                "Interdiction d'invoquer macroéconomie, SMC ou psychologie retail. Tester uniquement : "
                "(1) persistance d'état programmée (Wonham DSI / Weibull Trek) nette du spread live, "
                "(2) mispricing analytique d'options barrières, ou (3) défaut CSPRNG NIST SP 800-22/90B."
            ),
        }

    # 1. Réseau causal inter-actifs
    causal_net = (
        cross_asset_causal_network(r, exogenous_drivers, max_lag=6)
        if exogenous_drivers
        else {"valid": True, "verified_causal_leaders": [], "links": []}
    )
    verified_leaders = causal_net.get("verified_causal_leaders", [])

    # 2. Analyse de la prime de portage / funding / basis
    carry_info: Dict[str, Any] = {"present": False}
    if carry_or_funding_rate is not None:
        cf = np.nan_to_num(np.asarray(carry_or_funding_rate, dtype=np.float64).reshape(-1)[:n], nan=0.0)
        cf_sd = float(np.std(cf, ddof=1))
        if cf_sd > 1e-12 or abs(float(np.mean(cf))) > 1e-8:
            # Test de prédictibilité de l'excès de funding sur le retournement (crowded positioning)
            cf_z = _causal_ewma_zscore(cf, span=48)
            crowd_corr = float(np.corrcoef(cf_z[:-1], r[1:])[0, 1]) if np.std(cf_z[:-1]) > 1e-12 else 0.0
            t_crowd = crowd_corr * math.sqrt(max(1, n - 3) / max(1e-12, 1.0 - crowd_corr ** 2))
            carry_info = {
                "present": True,
                "mean_rate_bps": round(float(np.mean(cf) * 1e4), 4),
                "crowding_reversal_corr": round(crowd_corr, 4),
                "crowding_t_stat": round(t_crowd, 4),
                "actionable": bool(abs(t_crowd) >= 2.0 or abs(float(np.mean(cf) * 1e4)) > roundtrip_cost_bps * 0.25),
            }

    # 3. Saisonnalité horaire des sessions / fixings institutionnels (Tokyo 00h, Londres 08h/16h, NY 13h30-20h UTC)
    season_info: Dict[str, Any] = {"significant": False}
    if bar_timestamps is not None and len(bar_timestamps) >= n:
        ts_idx = pd.to_datetime(pd.Index(bar_timestamps[:n]), utc=True)
        hours = ts_idx.hour.to_numpy()
        uniq_h = np.unique(hours)
        if len(uniq_h) >= 4:
            groups_vol = [np.abs(r[1:][hours[1:] == h]) for h in uniq_h if np.sum(hours[1:] == h) >= 5]
            if len(groups_h := [g for g in groups_vol if len(g) >= 5]) >= 3:
                kw_stat, kw_p = stats.kruskal(*groups_h)
                hour_vol_bps = {
                    int(h): round(float(np.mean(np.abs(r[1:][hours[1:] == h])) * 1e4), 2)
                    for h in uniq_h
                    if np.sum(hours[1:] == h) >= 5
                }
                peak_hour = max(hour_vol_bps, key=hour_vol_bps.get)
                season_info = {
                    "significant": bool(kw_p < 0.01),
                    "kruskal_vol_p_value": round(float(kw_p), 6),
                    "peak_activity_utc_hour": int(peak_hour),
                    "peak_abs_move_bps": hour_vol_bps[peak_hour],
                }

    # 4. Pression de volume & asymétrie d'absorption
    vol_flow_info: Dict[str, Any] = {"present": False}
    if volume is not None:
        v = np.maximum(0.0, np.nan_to_num(np.asarray(volume, dtype=np.float64).reshape(-1)[:n], nan=0.0))
        if float(np.std(v, ddof=1)) > 1e-12:
            vz = _causal_ewma_zscore(np.log1p(v), span=48)
            high_vol_bars = vz[:-1] > 1.5
            cont_corr = (
                float(np.corrcoef(r[1:-1][high_vol_bars[1:]], r[2:][high_vol_bars[1:]])[0, 1])
                if np.sum(high_vol_bars[1:]) >= 20 and np.std(r[1:-1][high_vol_bars[1:]]) > 1e-12
                else 0.0
            )
            vol_flow_info = {
                "present": True,
                "high_volume_continuation_corr": round(cont_corr if np.isfinite(cont_corr) else 0.0, 4),
            }

    # Synthèse hiérarchique du moteur économique primaire et de la contrepartie contrainte
    drivers_detected: List[str] = []
    counterparties: List[str] = []
    if verified_leaders:
        top_lk = verified_leaders[0]
        drivers_detected.append(
            f"CROSS_ASSET_CAUSAL_SPILLOVER ({top_lk['driver_name']} lag={top_lk['best_lag_bars']}, t_HAC={top_lk['t_stat_hac']})"
        )
        counterparties.append("Réallocation inter-marchés à vitesse finie & couverture retardée des desks multi-actifs")
    if carry_info.get("actionable"):
        drivers_detected.append("CARRY_FUNDING_AND_CROWDED_LEVERAGE_TRANSFER")
        counterparties.append("Spéculateurs directionnels en levier payant le funding / hedgers commerciaux sur la courbe")
    if season_info.get("significant"):
        drivers_detected.append(f"INSTITUTIONAL_SESSION_FIXING_FLOW (pic UTC {season_info['peak_activity_utc_hour']}h)")
        counterparties.append("Flux passifs contraints aux horaires de fixing/clôture cash (ETF, trésoreries corporate)")
    if vol_flow_info.get("present") and abs(vol_flow_info.get("high_volume_continuation_corr", 0.0)) >= 0.08:
        drivers_detected.append("INFORMED_VOLUME_EXECUTION_SPLITTING")
        counterparties.append("Exécution fractionnée TWAP/VWAP d'institutionnels ou liquidations forcées")

    primary = drivers_detected[0] if drivers_detected else "ENDOGENOUS_PRICE_VOLATILITY_DYNAMICS_ONLY"
    forced_cp = " ; ".join(counterparties) if counterparties else "À identifier par données exogènes (flux, funding, taux, calendrier macro)"

    return {
        "valid": True,
        "market_nature": "REAL_ECONOMIC_ORDERFLOW_MARKET",
        "primary_economic_engine": primary,
        "all_detected_engines": drivers_detected,
        "forced_counterparty": forced_cp,
        "verified_causal_leaders": verified_leaders,
        "carry_regime": carry_info,
        "session_seasonality": season_info,
        "volume_flow_profile": vol_flow_info,
        "researcher_prescription": (
            f"Construire des hypothèses ancrées sur [{primary}] : combiner les leaders causaux validés "
            "hors-échantillon, le conditionnement de régime macro/volatilité et l'exécution adaptée aux coûts réels."
        ),
    }


# ============================================================================
# AUTO-TESTS DÉTERMINISTES INTÉGRÉS
# ============================================================================

if __name__ == "__main__":
    rng = np.random.default_rng(2026)

    # 1. Test Point-in-Time Macro Aligner (zéro fuite avant release_ts + rejet si release_ts < reference_ts)
    bars = pd.date_range("2026-01-01", periods=120, freq="h", tz="UTC")
    rels = [
        {"reference_ts": "2026-01-01T00:00:00Z", "release_ts": "2026-01-02T13:30:00Z", "actual": 3.4, "consensus": 3.1},
        {"reference_ts": "2026-01-02T00:00:00Z", "release_ts": "2026-01-03T13:30:00Z", "actual": 2.8, "consensus": 3.0},
        {"reference_ts": "2026-01-03T00:00:00Z", "release_ts": "2026-01-04T13:30:00Z", "actual": 3.9, "consensus": 3.2},
    ]
    pit_df = pit_macro_release_aligner(bars, rels)
    # Avant le 2026-01-02 13:30 UTC (barre 38), aucune donnée du 1er release ne doit fuiter !
    assert np.all(np.isnan(pit_df.loc[pit_df["bar_ts"] < pd.Timestamp("2026-01-02T13:30:00Z"), "latest_actual"]))
    assert pit_df.loc[pit_df["bar_ts"] >= pd.Timestamp("2026-01-02T14:00:00Z"), "latest_actual"].iloc[0] == 3.4
    leak_caught = False
    try:
        pit_macro_release_aligner(
            bars, [{"reference_ts": "2026-01-05T00:00:00Z", "release_ts": "2026-01-03T00:00:00Z", "actual": 1.0}]
        )
    except ValueError:
        leak_caught = True
    assert leak_caught, "Une annonce antérieure à sa période de référence doit être bloquée !"

    # 2. Test Classification Causale des 4 Quadrants Macro & Liquidité
    n_m = 400
    g_series = np.concatenate([np.linspace(0, 2.0, 200), np.linspace(2.0, -2.0, 200)]) + rng.normal(0, 0.2, n_m)
    i_series = np.concatenate([np.linspace(1.0, -1.0, 200), np.linspace(-1.0, 2.5, 200)]) + rng.normal(0, 0.2, n_m)
    liq_series = np.concatenate([np.linspace(0, 1.5, 200), np.linspace(1.5, -1.5, 200)])
    macro_reg = classify_macro_liquidity_regime(g_series, i_series, liq_series, ewma_span=32)
    assert macro_reg["valid"] and macro_reg["quadrant_probs"].shape == (n_m, 4)
    assert np.allclose(np.sum(macro_reg["quadrant_probs"], axis=1), 1.0)
    # En fin de série (croissance chute, inflation monte, liquidité chute) -> STAGFLATION_STRESS
    assert macro_reg["current_state"]["quadrant"] == "STAGFLATION_STRESS", macro_reg["current_state"]

    # 3. Test Découverte Causale Inter-Actifs (vrai leader causal vs facteur confondant pur bruit)
    n_c = 1200
    common_factor = rng.normal(0.0, 0.004, size=n_c)
    true_rates_leader = rng.normal(0.0, 0.003, size=n_c)
    spurious_peer = 0.8 * common_factor + rng.normal(0.0, 0.002, size=n_c)
    target_r = np.zeros(n_c)
    for t in range(2, n_c):
        # target_r dépend de son propre AR(1), du facteur contemporain, et de true_rates_leader en t-2
        target_r[t] = 0.20 * target_r[t - 1] + 0.50 * common_factor[t] - 0.35 * true_rates_leader[t - 2] + rng.normal(0.0, 0.0025)

    net = cross_asset_causal_network(
        target_r,
        {"US2Y_Yield_Shock": true_rates_leader, "Spurious_Peer": spurious_peer, "Pure_Noise": rng.normal(0, 1, n_c)},
        max_lag=4,
    )
    leader_names = [lk["driver_name"] for lk in net["verified_causal_leaders"]]
    assert "US2Y_Yield_Shock" in leader_names, f"Vrai leader manqué: {net}"
    assert "Pure_Noise" not in leader_names, f"Faux positif sur bruit pur: {net}"
    us2y_lk = [lk for lk in net["verified_causal_leaders"] if lk["driver_name"] == "US2Y_Yield_Shock"][0]
    assert us2y_lk["best_lag_bars"] == 2 and us2y_lk["direction"] == "INVERSE_SPILLOVER"

    # 4. Test Event Study Catalyseurs Macro (PEAD significatif)
    ev_bars = list(range(40, 1100, 50))
    ev_surp = rng.choice([-1.5, 1.5], size=len(ev_bars))
    r_ev = rng.normal(0.0, 0.0015, size=1200)
    for idx_e, b_i in enumerate(ev_bars):
        r_ev[b_i] += 0.006 * np.sign(ev_surp[idx_e])
        r_ev[b_i + 1 : b_i + 6] += 0.0012 * np.sign(ev_surp[idx_e])
    es_rep = macro_event_study_analyzer(r_ev, ev_bars, event_surprises=ev_surp, pre_window=4, post_window=6, roundtrip_cost_bps=2.0)
    assert es_rep["valid"] and es_rep["net_pead_tradable"] and es_rep["vol_expansion_ratio"] > 1.5

    # 5. Test Diagnostic d'Écologie de Marché
    px = 100.0 * np.exp(np.cumsum(target_r))
    eco = diagnose_market_ecology(
        px,
        roundtrip_cost_bps=2.0,
        exogenous_drivers={"US2Y_Yield_Shock": true_rates_leader, "Spurious_Peer": spurious_peer},
    )
    assert eco["valid"] and "CROSS_ASSET_CAUSAL_SPILLOVER" in eco["primary_economic_engine"]
    print(
        "macro_causal_intelligence : 5/5 auto-tests OK",
        {
            "quadrant": macro_reg["current_state"]["quadrant"],
            "causal_leader": us2y_lk["driver_name"],
            "lag": us2y_lk["best_lag_bars"],
            "t_hac": us2y_lk["t_stat_hac"],
            "pead_t": es_rep["post_event_pead_t_stat"],
        },
    )
