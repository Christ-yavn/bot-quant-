"""
quant_discovery_engine.py
=========================
Moteur de Recherche Autonome, Diagnostic du Processus Générateur (DGP),
Cryptanalyse de Générateurs Gaussiens, Primitives d'Alpha Orthogonales
et Boucle Évolutive de Mutation Ciblée pour `quant-pod` v2.

Ce module force l'agent à se comporter comme un vrai chercheur quantitatif :
1. `diagnose_market_dgp` : Décompose mathématiquement n'importe quelle série (Futures,
   Crypto, Forex, Actions, Indices Synthétiques Deriv) avant tout backtest :
   - Profil de Ratio de Variance Lo-MacKinlay hétéroscédastique VR(q)
   - Séparation Diffusion Continue vs Sauts via Variation Bi-Puissance (Barndorff-Nielsen & Shephard)
   - Spread Implicite de Roll & Illiquidité d'Amihud
   - Cryptanalyse des queues Box-Muller en coordonnées polaires (détection des vides de Neave)
   - Plafond de prédictibilité de Doob-Meyer face aux frictions réelles
2. `AlphaPrimitives` : Bibliothèque d'opérateurs causaux Point-in-Time (zéro look-ahead)
   allant au-delà des indicateurs retail classiques :
   - Volatilité Yang-Zhang, Ratio de Sauts Bi-Puissance, Filtre de Kalman 1D en espace d'état,
     Intensité auto-excitée de Hawkes (cascades de liquidations/chocs), Porte de régime
     d'autocorrélation locale, Pression de flux signé (Order Flow proxy).
3. `diagnose_failure_and_mutate` : Diagnostique automatiquement POURQUOI une stratégie
   échoue selon 6 modes de défaillance physiques et génère la mutation mathématique ciblée.
4. `run_autonomous_discovery_loop` : Exécute une boucle de recherche bornée par `K_max`,
   enregistre chaque essai dans `ResearchLedger`, mute les candidats prometteurs et
   soumet les survivants aux portes `/boost` (`quant_validation_engine.py`).
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
from scipy import stats

from quant_validation_engine import (
    GATES,
    ResearchLedger,
    dsr,
    pbo_cscv,
    cost_stress,
    plateau_score,
    sharpe,
)


# ============================================================================
# 1. DIAGNOSTIC MATHÉMATIQUE & CRYPTOGRAPHIQUE DU PROCESSUS GÉNÉRATEUR (DGP)
# ============================================================================

def lo_mackinlay_variance_ratio(returns: np.ndarray, q: int = 2) -> Tuple[float, float, float]:
    """
    Test du Ratio de Variance de Lo & MacKinlay (1988) robuste à l'hétéroscédasticité.
    Sous une martingale à accroissements non corrélés (même avec volatilité GARCH), VR(q) = 1.0.
    - VR(q) > 1.0 significatif => persistance / momentum à l'échelle q.
    - VR(q) < 1.0 significatif => retour à la moyenne (mean-reversion) à l'échelle q.
    Retourne (vr, z_stat_hetero, p_value).
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 4 * q + 10 or q < 2:
        return 1.0, 0.0, 1.0

    mu = float(np.mean(r))
    r_centered = r - mu
    var_1 = float(np.sum(r_centered ** 2) / (n - 1))
    if var_1 <= 1e-18:
        return 1.0, 0.0, 1.0

    # Sommes glissantes d'horizon q
    cs = np.concatenate([[0.0], np.cumsum(r_centered)])
    r_q = cs[q:] - cs[:-q]
    m = q * (n - q + 1) * (1.0 - q / n)
    var_q = float(np.sum(r_q ** 2) / m)
    vr = var_q / var_1

    # Variance asymptotique robuste à l'hétéroscédasticité (Lo-MacKinlay theta(q))
    denom = float(np.sum(r_centered ** 2)) ** 2
    theta = 0.0
    for j in range(1, q):
        num = float(np.sum((r_centered[j:] ** 2) * (r_centered[:-j] ** 2)))
        delta_j = (n * num) / denom
        weight = 2.0 * (q - j) / q
        theta += (weight ** 2) * delta_j

    if theta <= 1e-18:
        return float(vr), 0.0, 1.0

    z_stat = (vr - 1.0) * math.sqrt(n) / math.sqrt(theta)
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(z_stat))))
    return float(vr), float(z_stat), p_val


def barndorff_nielsen_jump_decomposition(returns: np.ndarray, window: int = 24) -> Dict[str, np.ndarray]:
    """
    Sépare la Variance Réalisée (RV) en composante diffusive continue (Variation Bi-Puissance BV)
    et composante de Sauts (Jump Variation JV) selon Barndorff-Nielsen & Shephard (2004) :
    - RV_t = sum_{i=1}^W r_{t-i}^2
    - BV_t = (pi / 2) * sum_{i=1}^{W-1} |r_{t-i}| * |r_{t-i-1}|
    - JV_t = max(0, RV_t - BV_t)
    Strictement causal (utilise uniquement les observations <= t).
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    rv = np.full(n, np.nan)
    bv = np.full(n, np.nan)
    jv_ratio = np.full(n, np.nan)

    r2 = r ** 2
    abs_r = np.abs(r)
    biprod = (math.pi / 2.0) * (abs_r[1:] * abs_r[:-1])
    biprod = np.concatenate([[0.0], biprod])

    cs_r2 = np.concatenate([[0.0], np.cumsum(np.nan_to_num(r2, nan=0.0))])
    cs_bi = np.concatenate([[0.0], np.cumsum(np.nan_to_num(biprod, nan=0.0))])

    for t in range(window, n):
        rv_t = cs_r2[t + 1] - cs_r2[t + 1 - window]
        bv_t = (cs_bi[t + 1] - cs_bi[t + 2 - window]) * (window / max(1, window - 1))
        rv[t] = rv_t
        bv[t] = bv_t
        if rv_t > 1e-18:
            jv_ratio[t] = max(0.0, (rv_t - bv_t) / rv_t)
        else:
            jv_ratio[t] = 0.0

    return {"rv": rv, "bv": bv, "jump_ratio": jv_ratio}


def audit_gaussian_generator_tails(returns: np.ndarray, vol_window: int = 50) -> Dict[str, Any]:
    """
    Cryptanalyse statistique des innovations normalisées z_t = r_t / sigma_t :
    Teste si un générateur synthétique utilise une transformation de Box-Muller
    imparfaite (effet Neave : absence de valeurs dans les queues radiales ou
    non-uniformité de l'angle polaire Theta = atan2(z_{2k+1}, z_{2k})).
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 200:
        return {"valid": False, "reason": "Échantillon trop court (<200)"}

    # Normalisation causale par écart-type glissant
    z = np.zeros(n)
    for t in range(vol_window, n):
        s = float(np.std(r[t - vol_window:t], ddof=1))
        z[t] = r[t] / s if s > 1e-12 else 0.0
    z = z[vol_window:]
    m = (len(z) // 2) * 2
    z1 = z[0:m:2]
    z2 = z[1:m:2]

    # Coordonnées polaires de Box-Muller : R^2 = z1^2 + z2^2, Theta = atan2(z2, z1)
    # Sous N(0,1) iid : U1 = exp(-R^2 / 2) ~ U(0, 1) et U2 = (Theta + pi) / (2*pi) ~ U(0, 1)
    r_sq = z1 ** 2 + z2 ** 2
    u1_radial = np.exp(-0.5 * r_sq)
    u2_angular = (np.arctan2(z2, z1) + math.pi) / (2.0 * math.pi)

    ks_rad_stat, ks_rad_p = stats.kstest(u1_radial, "uniform")
    ks_ang_stat, ks_ang_p = stats.kstest(u2_angular, "uniform")

    # Ratio d'excès dans la queue extrême |z| > 3.5 (attendu Gaussien : 0.000465)
    expected_tail_35 = float(2.0 * (1.0 - stats.norm.cdf(3.5)))
    empirical_tail_35 = float(np.mean(np.abs(z) > 3.5))
    tail_ratio_35 = empirical_tail_35 / max(1e-9, expected_tail_35)

    return {
        "valid": True,
        "n_pairs": len(z1),
        "box_muller_radial_ks_p": float(ks_rad_p),
        "box_muller_angular_ks_p": float(ks_ang_p),
        "extreme_tail_3_5_sigma_ratio_vs_normal": round(tail_ratio_35, 3),
        "neave_tail_truncation_suspected": bool(tail_ratio_35 < 0.25 and len(z) > 5000),
    }


def diagnose_market_dgp(
    close: np.ndarray,
    high: Optional[np.ndarray] = None,
    low: Optional[np.ndarray] = None,
    roundtrip_cost_bps: float = 2.0,
) -> Dict[str, Any]:
    """
    Exécute le diagnostic complet du Processus Générateur de Données (Phase 1 de `quant-pod`) :
    1. Profil de Ratio de Variance VR(q) pour q in {2, 4, 8, 16}.
    2. Détection de bascule de régime d'autocorrélation (`REGIME_SWITCHING_CHAMELEON` vs persistance globale).
    3. Autocorrélation des rendements signés ACF(r, 1..5) vs valeurs absolues ACF(|r|, 1..5).
    4. Part de la variance due aux sauts (Barndorff-Nielsen Jump Ratio).
    5. Spread implicite de Roll.
    6. Plafond de prédictibilité conditionnelle face aux coûts réels.
    """
    c = np.asarray(close, dtype=np.float64)
    r = np.diff(np.log(np.maximum(c, 1e-12)))
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 200:
        return {"valid": False, "reason": "Moins de 200 rendements valides."}

    # 1. Ratios de variance multi-échelles
    vr_profile = {}
    min_vr_p = 1.0
    dominant_regime = "MARTINGALE_DRIFT_ZERO"
    for q in (2, 4, 8, 16):
        vr, z_stat, p_val = lo_mackinlay_variance_ratio(r, q=q)
        vr_profile[f"VR_{q}"] = {"vr": round(vr, 4), "z": round(z_stat, 3), "p": round(p_val, 4)}
        if p_val < min_vr_p:
            min_vr_p = p_val
            if p_val < 0.05:
                dominant_regime = "MOMENTUM_PERSISTENT" if vr > 1.0 else "MEAN_REVERTING"

    # 2. ACF signée vs ACF de volatilité |r| + détection de régime alternant (Chameleon : locale + parité spectrale)
    acf_signed_1 = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if np.std(r) > 0 else 0.0
    acf_signed_2 = float(np.corrcoef(r[:-2], r[2:])[0, 1]) if (n > 4 and np.std(r) > 0) else 0.0
    abs_r = np.abs(r)
    acf_abs_1 = float(np.corrcoef(abs_r[:-1], abs_r[1:])[0, 1]) if np.std(abs_r) > 0 else 0.0

    local_rho = AlphaPrimitives.rolling_autocorr_regime(r, window=48)[48:] if n > 96 else np.zeros(1)
    local_rho_std = float(np.std(local_rho, ddof=1)) if len(local_rho) > 2 else 0.0
    frac_pos_regime = float(np.mean(local_rho > 0.12)) if len(local_rho) > 0 else 0.0
    frac_neg_regime = float(np.mean(local_rho < -0.12)) if len(local_rho) > 0 else 0.0
    vr2_val = float(vr_profile["VR_2"]["vr"])
    vr4_val = float(vr_profile["VR_4"]["vr"])
    vr4_p = float(vr_profile["VR_4"]["p"])
    # Parité spectrale (bascule rapide de régime) : dans un processus AR(1) monochrome (rho > 0),
    # ACF(1) > ACF(2) et VR(2)-1 > 0 significatif. Dans un processus Chameleon alternant (rho_t in {+rho, -rho}),
    # le lag impair s'annule (ACF(2) > |ACF(1)|) tandis que les lags pairs s'additionnent (VR(4) > 1 significatif) :
    spectral_parity_chameleon = bool(
        vr4_p < 0.05
        and (vr4_val - 1.0) > 0.06
        and (vr4_val - 1.0) > 2.0 * max(0.0, vr2_val - 1.0)
        and acf_signed_2 > max(0.05, abs(acf_signed_1))
    )
    regime_switching_detected = bool(
        (frac_pos_regime >= 0.15 and frac_neg_regime >= 0.15 and local_rho_std > 0.18)
        or spectral_parity_chameleon
    )
    if regime_switching_detected:
        dominant_regime = "REGIME_SWITCHING_CHAMELEON"

    # 3. Décomposition Diffusion vs Sauts
    bn = barndorff_nielsen_jump_decomposition(r, window=24)
    mean_jump_share = float(np.nanmean(bn["jump_ratio"]))

    # 4. Spread implicite de Roll (en bps)
    cov_lag1 = float(np.cov(r[:-1], r[1:])[0, 1])
    roll_spread_bps = float(2.0 * math.sqrt(max(0.0, -cov_lag1)) * 1e4)

    # 5. Ratio Signal / Friction (volatilité moyenne d'une barre vs coût aller-retour)
    bar_sigma_bps = float(np.std(r, ddof=1) * 1e4)
    friction_to_sigma_ratio = roundtrip_cost_bps / max(1e-9, bar_sigma_bps)

    # 6. Audit des queues gaussiennes
    tail_audit = audit_gaussian_generator_tails(r)

    # Verdict structurel (seuil de Bonferroni sur 4 horizons VR : 0.05 / 4 = 0.0125)
    if min_vr_p > 0.0125 and abs(acf_signed_1) < 2.5 / math.sqrt(n) and acf_abs_1 < 0.05 and not regime_switching_detected:
        verdict = "MARTINGALE_PURE_SANS_MEMOIRE (Attention : Plafond de Doob actif, EV <= -Spread)"
    elif friction_to_sigma_ratio > 0.50:
        verdict = "DOMINE_PAR_LES_FRICTIONS (Coût > 50% de la vol par barre : augmenter l'horizon H ou passer Maker)"
    else:
        verdict = f"EXPLOITABLE_CONDITIONNEL ({dominant_regime}, ACF(|r|,1)={acf_abs_1:.3f}, JumpShare={mean_jump_share:.2f})"

    return {
        "valid": True,
        "n_bars": n,
        "dominant_regime": dominant_regime,
        "regime_switching_detected": regime_switching_detected,
        "local_autocorr_std": round(local_rho_std, 4),
        "frac_momentum_bars": round(frac_pos_regime, 4),
        "frac_mean_rev_bars": round(frac_neg_regime, 4),
        "bar_volatility_bps": round(bar_sigma_bps, 2),
        "roundtrip_cost_bps": roundtrip_cost_bps,
        "friction_to_sigma_ratio": round(friction_to_sigma_ratio, 4),
        "acf_signed_lag1": round(acf_signed_1, 5),
        "acf_abs_vol_clustering_lag1": round(acf_abs_1, 5),
        "mean_jump_variance_share": round(mean_jump_share, 4),
        "roll_implicit_spread_bps": round(roll_spread_bps, 2),
        "variance_ratio_profile": vr_profile,
        "tail_cryptanalysis": tail_audit,
        "structural_verdict": verdict,
    }


# ============================================================================
# 2. PRIMITIVES D'ALPHA ORTHOGONALES (STRICTEMENT CAUSALES POINT-IN-TIME, VECTORISÉES O(N))
# ============================================================================

class AlphaPrimitives:
    """
    Bibliothèque d'opérateurs mathématiques strictement causaux (aucune fuite du futur).
    Chaque fonction retourne un vecteur aligné sur l'indice temporel t utilisant uniquement [0..t].
    """

    @staticmethod
    def causal_zscore(x: np.ndarray, window: int = 48) -> np.ndarray:
        """Z-score glissant causal sur fenêtre `window` (vectorisé O(N) sur données finies)."""
        arr = np.asarray(x, dtype=np.float64)
        n = len(arr)
        out = np.zeros(n, dtype=np.float64)
        if n <= window or window < 2:
            return out
        if np.all(np.isfinite(arr)):
            wins = np.lib.stride_tricks.sliding_window_view(arr, window)[1:]  # t = window .. n-1
            means = np.mean(wins, axis=1)
            stds = np.std(wins, axis=1, ddof=1)
            valid = stds > 1e-12
            out_slice = np.zeros(len(stds), dtype=np.float64)
            out_slice[valid] = (arr[window:][valid] - means[valid]) / stds[valid]
            out[window:] = out_slice
            return np.clip(out, -5.0, 5.0)
        for t in range(window, n):
            seg = arr[t - window + 1 : t + 1]
            valid = seg[np.isfinite(seg)]
            if len(valid) >= 5:
                s = float(np.std(valid, ddof=1))
                if s > 1e-12:
                    out[t] = (arr[t] - float(np.mean(valid))) / s
        return np.clip(out, -5.0, 5.0)

    @staticmethod
    def yang_zhang_volatility(
        open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 20
    ) -> np.ndarray:
        """Estimateur de volatilité OHLC de Yang-Zhang (2000) strictement causal (vectorisé O(N))."""
        o = np.log(np.maximum(open_, 1e-12))
        h = np.log(np.maximum(high, 1e-12))
        l = np.log(np.maximum(low, 1e-12))
        c = np.log(np.maximum(close, 1e-12))
        n = len(c)

        ro = np.zeros(n)
        ro[1:] = o[1:] - c[:-1]
        rc = c - o
        rs = (h - c) * (h - o) + (l - c) * (l - o)

        k = 0.34 / (1.34 + (window + 1.0) / max(1.0, window - 1.0))
        out = np.full(n, np.nan)
        if n <= window or window < 2:
            return out
        ro_w = np.lib.stride_tricks.sliding_window_view(ro, window)[1:]
        rc_w = np.lib.stride_tricks.sliding_window_view(rc, window)[1:]
        rs_w = np.lib.stride_tricks.sliding_window_view(rs, window)[1:]
        s_o = np.var(ro_w, axis=1, ddof=1)
        s_c = np.var(rc_w, axis=1, ddof=1)
        s_rs = np.mean(rs_w, axis=1)
        yz_var = np.maximum(0.0, s_o + k * s_c + (1.0 - k) * s_rs)
        out[window:] = np.sqrt(yz_var)
        return out

    @staticmethod
    def kalman_state_space_zscore(
        close: np.ndarray, process_noise_q: float = 1e-5, obs_noise_r: Optional[float] = 1e-3
    ) -> np.ndarray:
        """
        Filtre de Kalman 1D en espace d'état sur log-prix :
        Estime l'état latent x_{t|t-1} (juste valeur dynamique sans retard de fenêtre fixe)
        et retourne l'innovation normalisée (écart entre le prix observé et la prédiction de Kalman).
        Si `obs_noise_r` est None, estime causalement la variance d'observation par EWMA des
        rendements passés [0..t-1] (invariance d'échelle sans look-ahead).
        """
        y = np.log(np.maximum(close, 1e-12))
        n = len(y)
        innov_z = np.zeros(n, dtype=np.float64)
        if n < 2:
            return innov_z
        x_hat = float(y[0])
        p_cov = 1.0
        adaptive = obs_noise_r is None
        ewma_var = max(1e-10, float((y[1] - y[0]) ** 2)) if adaptive else 0.0

        for t in range(1, n):
            r_cur = max(1e-10, ewma_var) if adaptive else float(obs_noise_r)
            q_cur = 2.0 * r_cur if adaptive else float(process_noise_q)

            # Prédiction a priori (en t-1 pour t)
            x_pred = x_hat
            p_pred = p_cov + q_cur

            # Innovation à l'arrivée de y[t]
            err = float(y[t] - x_pred)
            s_var = p_pred + r_cur
            innov_z[t] = err / math.sqrt(max(1e-18, s_var))

            # Mise à jour de l'état a posteriori
            k_gain = p_pred / max(1e-18, s_var)
            x_hat = x_pred + k_gain * err
            p_cov = (1.0 - k_gain) * p_pred
            if adaptive:
                dy = float(y[t] - y[t - 1])
                ewma_var = 0.94 * ewma_var + 0.06 * (dy * dy)

        return np.clip(innov_z, -5.0, 5.0)

    @staticmethod
    def hawkes_shock_intensity(
        returns: np.ndarray, threshold_sigma: float = 2.0, decay_beta: float = 0.25, vol_window: int = 48
    ) -> np.ndarray:
        """
        Intensité d'un processus auto-excité de Hawkes sur les chocs extrêmes (cascades de
        liquidations ou grappes de sauts) :
        lambda_t = exp(-beta) * lambda_{t-1} + sign(r_t) * I(|r_t| > threshold_sigma * sigma_t).
        Capture l'épuisement directionnel après une cascade de chocs du même signe.
        """
        r = np.asarray(returns, dtype=np.float64)
        n = len(r)
        intensity = np.zeros(n, dtype=np.float64)
        decay = math.exp(-decay_beta)
        if n <= vol_window:
            return intensity
        wins = np.lib.stride_tricks.sliding_window_view(r, vol_window)[:-1]  # r[t-vol_window : t] pour t=vol_window..n-1
        sigs = np.std(wins, axis=1, ddof=1)
        for idx, t in enumerate(range(vol_window, n)):
            sig = float(sigs[idx])
            shock = 0.0
            if sig > 1e-12 and abs(r[t]) > threshold_sigma * sig:
                shock = float(np.sign(r[t]) * (abs(r[t]) / sig))
            intensity[t] = decay * intensity[t - 1] + shock
        return intensity

    @staticmethod
    def rolling_autocorr_regime(returns: np.ndarray, window: int = 48) -> np.ndarray:
        """
        Estime le régime local d'autocorrélation sérielle sur [t-window+1 .. t] (vectorisé O(N)) :
        > 0 : régime local de persistance (momentum)
        < 0 : régime local d'anti-persistance (mean-reversion)
        """
        r = np.asarray(returns, dtype=np.float64)
        n = len(r)
        rho = np.zeros(n, dtype=np.float64)
        if n <= window or window < 4:
            return rho
        if np.all(np.isfinite(r)):
            wins = np.lib.stride_tricks.sliding_window_view(r, window)[1:]  # t = window .. n-1
            x = wins[:, :-1]
            y = wins[:, 1:]
            xm = x - np.mean(x, axis=1, keepdims=True)
            ym = y - np.mean(y, axis=1, keepdims=True)
            num = np.sum(xm * ym, axis=1)
            den = np.sqrt(np.sum(xm ** 2, axis=1) * np.sum(ym ** 2, axis=1))
            valid = den > 1e-12
            out_slice = np.zeros(len(den), dtype=np.float64)
            out_slice[valid] = num[valid] / den[valid]
            rho[window:] = np.nan_to_num(out_slice, nan=0.0)
            return rho
        for t in range(window, n):
            seg = r[t - window + 1 : t + 1]
            s = float(np.std(seg))
            if s > 1e-12:
                c = float(np.corrcoef(seg[:-1], seg[1:])[0, 1])
                if np.isfinite(c):
                    rho[t] = c
        return rho


# ============================================================================
# 2.bis PLANIFICATEUR DE STRATÉGIE ALGORITHMIQUE SELON LE MARCHÉ (`AlgorithmicStrategyPlanner`)
# ============================================================================

@dataclass
class StrategyPlan:
    dominant_regime: str
    primary_playbook: str
    doob_martingale_veto: bool
    optimal_horizon_bars: int
    entry_threshold_z: float
    sl_sigma_mult: float
    tp_sigma_mult: float
    family_priors: Dict[str, float]
    rationale: str


class AlgorithmicStrategyPlanner:
    """
    Poste Senior : Chief Market Regime & Algorithmic Strategy Planner.
    Analyse le diagnostic mathématique DGP (`diagnose_market_dgp`) et prescrit
    algorithmiquement l'architecture de la stratégie AVANT le moindre backtest :
      - Veto immédiat de Doob sur les martingales pures sans mémoire.
      - Horizon optimal H* calibré pour amortir le ratio Coût / Volatilité.
      - Sélection du Playbook (Momentum, Mean-Reversion, Chameleon Regime-Switch, Hawkes Jump-Reversion).
      - Multiplicateurs de barrières SL*/TP* et priors bayésiens par famille d'alpha.
    """

    @staticmethod
    def plan(dgp_report: Dict[str, Any]) -> StrategyPlan:
        verdict = str(dgp_report.get("structural_verdict", ""))
        dom = str(dgp_report.get("dominant_regime", "MARTINGALE_DRIFT_ZERO"))
        fric_ratio = float(dgp_report.get("friction_to_sigma_ratio", 0.20))
        jump_share = float(dgp_report.get("mean_jump_variance_share", 0.0))
        vol_clust = float(dgp_report.get("acf_abs_vol_clustering_lag1", 0.0))

        doob_veto = "MARTINGALE_PURE_SANS_MEMOIRE" in verdict
        # Horizon H* : garantit que le coût aller-retour représente <= 25% de la volatilité sur H*
        raw_h = int(math.ceil((fric_ratio / 0.25) ** 2)) if fric_ratio > 0.25 else 4
        opt_h = int(np.clip(max(4, raw_h), 4, 48))

        if doob_veto:
            return StrategyPlan(
                dominant_regime=dom,
                primary_playbook="NO_GO_DOOB_MARTINGALE_PROTECTION",
                doob_martingale_veto=True,
                optimal_horizon_bars=opt_h,
                entry_threshold_z=2.0,
                sl_sigma_mult=2.0,
                tp_sigma_mult=2.0,
                family_priors={
                    "H1_VolSqueeze_Breakout": 0.05,
                    "H2_Kalman_MeanReversion": 0.05,
                    "H3_Hawkes_Cascade_Reversion": 0.05,
                    "H4_Autocorr_Regime_Adaptive": 0.05,
                    "H5_Chameleon_Kalman_Regime": 0.05,
                },
                rationale="Plafond de Doob actif (martingale sans mémoire) : toute règle basée sur le seul prix a E[PnL] = -Coûts.",
            )

        if dom == "REGIME_SWITCHING_CHAMELEON":
            playbook = "CHAMELEON_REGIME_ADAPTIVE_SWITCHING"
            priors = {
                "H4_Autocorr_Regime_Adaptive": 0.35,
                "H5_Chameleon_Kalman_Regime": 0.35,
                "H1_VolSqueeze_Breakout": 0.12,
                "H2_Kalman_MeanReversion": 0.10,
                "H3_Hawkes_Cascade_Reversion": 0.08,
            }
            sl_m, tp_m, thr_z = 2.0, 2.5, 1.25
            rationale = "Alternance de régimes Momentum/Mean-Reversion détectée : activer le conditionnement de signe par l'ACF locale."
        elif dom == "MOMENTUM_PERSISTENT":
            playbook = "TREND_FOLLOWING_AND_VOL_SQUEEZE_BREAKOUT"
            priors = {
                "H1_VolSqueeze_Breakout": 0.35 if vol_clust > 0.05 else 0.25,
                "H4_Autocorr_Regime_Adaptive": 0.30,
                "H5_Chameleon_Kalman_Regime": 0.20,
                "H2_Kalman_MeanReversion": 0.07,
                "H3_Hawkes_Cascade_Reversion": 0.08,
            }
            sl_m, tp_m, thr_z = 1.8, 3.0, 1.25
            rationale = "Persistance directionnelle VR(q) > 1 : privilégier les cassures de compression Yang-Zhang et le suivi de régime."
        elif dom == "MEAN_REVERTING":
            playbook = "STATE_SPACE_KALMAN_AND_HAWKES_REVERSION"
            priors = {
                "H2_Kalman_MeanReversion": 0.38,
                "H3_Hawkes_Cascade_Reversion": 0.32 if jump_share > 0.15 else 0.22,
                "H5_Chameleon_Kalman_Regime": 0.20,
                "H4_Autocorr_Regime_Adaptive": 0.12,
                "H1_VolSqueeze_Breakout": 0.08,
            }
            sl_m, tp_m, thr_z = 2.5, 1.8, 1.50
            rationale = "Anti-persistance VR(q) < 1 : exploiter l'innovation du filtre de Kalman 1D et l'épuisement des cascades de Hawkes."
        else:
            playbook = "SELECTIVE_VOL_CLUSTERING_AND_JUMP_EXHAUSTION"
            priors = {
                "H3_Hawkes_Cascade_Reversion": 0.30,
                "H1_VolSqueeze_Breakout": 0.25,
                "H4_Autocorr_Regime_Adaptive": 0.20,
                "H5_Chameleon_Kalman_Regime": 0.15,
                "H2_Kalman_MeanReversion": 0.10,
            }
            sl_m, tp_m, thr_z = 2.2, 2.2, 1.50
            rationale = "Dérive inconditionnelle faible mais clustering de volatilité/sauts présent : filtrer les queues extrêmes."

        return StrategyPlan(
            dominant_regime=dom,
            primary_playbook=playbook,
            doob_martingale_veto=False,
            optimal_horizon_bars=opt_h,
            entry_threshold_z=thr_z,
            sl_sigma_mult=sl_m,
            tp_sigma_mult=tp_m,
            family_priors=priors,
            rationale=rationale,
        )


def plan_strategy_from_market_regime(dgp_report: Dict[str, Any]) -> Dict[str, Any]:
    """Enveloppe fonctionnelle retournant le plan stratégique algorithmique sous forme de dictionnaire."""
    return asdict(AlgorithmicStrategyPlanner.plan(dgp_report))


# ============================================================================
# 3. DIAGNOSTIC DES 6 MODES D'ÉCHEC & OPÉRATEURS DE MUTATION CIBLÉE
# ============================================================================

@dataclass
class CandidateEvaluation:
    name: str
    formula_desc: str
    params: Dict[str, Any]
    horizon_bars: int
    n_trades: int
    gross_bps_per_trade: float
    net_bps_per_trade: float
    t_stat_gross: float
    t_stat_net: float
    sharpe_net_ann: float
    subperiod_positive_ratio: float
    failure_mode: str
    recommended_mutation: str
    trade_returns_net: np.ndarray
    bull_bear_approved: bool = True
    bull_bear_conviction: float = 0.5
    bull_bear_objections: Tuple[str, ...] = ()


def evaluate_signal_non_overlapping(
    signal: np.ndarray,
    log_returns: np.ndarray,
    horizon: int = 4,
    entry_threshold: float = 1.0,
    roundtrip_cost_bps: float = 2.0,
    bars_per_year: float = 24.0 * 365.0,
) -> Dict[str, Any]:
    """
    Backtest vectorisé causal sans chevauchement (non-overlapping) :
    - Une décision prise à la clôture de la barre t (sur signal[t] connu en t)
      capture le rendement log_returns[t+1 : t+1+horizon].
    - Coût aller-retour réel soustrait sur chaque trade.
    """
    sig = np.asarray(signal, dtype=np.float64)
    r = np.asarray(log_returns, dtype=np.float64)
    n = min(len(sig), len(r))
    cost_dec = roundtrip_cost_bps * 1e-4

    gross_trades: List[float] = []
    net_trades: List[float] = []
    bar_pnl_net = np.zeros(n, dtype=np.float64)

    t = 0
    while t < n - horizon - 1:
        s_val = sig[t]
        if np.isfinite(s_val) and abs(s_val) >= entry_threshold:
            direction = 1.0 if s_val > 0 else -1.0
            fwd_ret = float(np.sum(r[t + 1 : t + 1 + horizon]))
            g_pnl = direction * fwd_ret
            n_pnl = g_pnl - cost_dec
            gross_trades.append(g_pnl)
            net_trades.append(n_pnl)
            # Marquage au marché (Mark-to-Market) causal barre par barre sur la fenêtre de détention
            bar_pnl_net[t + 1 : t + 1 + horizon] = direction * r[t + 1 : t + 1 + horizon] - (cost_dec / float(horizon))
            t += horizon
        else:
            t += 1

    gross_arr = np.asarray(gross_trades, dtype=np.float64)
    net_arr = np.asarray(net_trades, dtype=np.float64)
    m = len(net_arr)
    if m < 20:
        return {
            "n_trades": m,
            "gross_bps": 0.0,
            "net_bps": 0.0,
            "t_gross": 0.0,
            "t_net": 0.0,
            "sharpe_ann": 0.0,
            "subperiod_pos_ratio": 0.0,
            "net_trades": net_arr,
            "bar_pnl_net": bar_pnl_net,
        }

    g_std = float(np.std(gross_arr, ddof=1))
    n_std = float(np.std(net_arr, ddof=1))
    t_gross = float(np.mean(gross_arr) / (g_std / math.sqrt(m))) if g_std > 1e-18 else 0.0
    t_net = float(np.mean(net_arr) / (n_std / math.sqrt(m))) if n_std > 1e-18 else 0.0

    # Consistance sur 4 sous-périodes chronologiques
    chunks = np.array_split(net_arr, 4)
    pos_chunks = sum(1 for ch in chunks if len(ch) > 0 and float(np.mean(ch)) > 0.0)
    sub_ratio = pos_chunks / 4.0

    trades_per_year = max(1.0, (m / max(1.0, float(n))) * bars_per_year)
    sr_ann = float((np.mean(net_arr) / n_std) * math.sqrt(trades_per_year)) if n_std > 1e-18 else 0.0

    return {
        "n_trades": m,
        "gross_bps": float(np.mean(gross_arr) * 1e4),
        "net_bps": float(np.mean(net_arr) * 1e4),
        "t_gross": t_gross,
        "t_net": t_net,
        "sharpe_ann": sr_ann,
        "subperiod_pos_ratio": sub_ratio,
        "net_trades": net_arr,
        "bar_pnl_net": bar_pnl_net,
    }


def diagnose_failure_mode(metrics: Dict[str, Any], cost_bps: float) -> Tuple[str, str]:
    """
    Classifie scientifiquement la cause d'échec ou de réussite d'un candidat
    parmi les 6 modes physiques et prescrit l'opérateur de mutation exact.
    """
    n_trades = metrics["n_trades"]
    g_bps = metrics["gross_bps"]
    n_bps = metrics["net_bps"]
    t_gross = metrics["t_gross"]
    t_net = metrics["t_net"]
    sub_ratio = metrics["subperiod_pos_ratio"]

    if n_trades < 50:
        return (
            "INSUFFICIENT_SAMPLE (<50 trades)",
            "O6_RELAX_THRESHOLD: Abaisser légèrement le seuil d'entrée pour obtenir >= 100 trades.",
        )
    if t_gross <= -2.0 and abs(g_bps) > cost_bps * 1.3:
        return (
            "GROSS_NEGATIVE_INVERTIBLE (Signal prédictif mais inversé)",
            "O2_INVERT_SIGNAL: Le signal prédit significativement le sens opposé (faux breakout / piège de liquidité). Inverser le signe (-signal).",
        )
    if abs(t_gross) < 1.3:
        return (
            "GROSS_EDGE_ZERO (Aucune information mutuelle prédictive)",
            "O5_ORTHOGONAL_REPLACE: L'indicateur brut est un bruit pur sur ce marché. Changer de famille physique (ex: Kalman ou Hawkes).",
        )
    if t_gross >= 1.8 and n_bps <= 0.0:
        return (
            "KILLED_BY_FRICTION (Alpha brut réel mais détruit par le spread/frais)",
            "O6_HORIZON_AND_EXTREME_FILTER: Allonger l'horizon H (la dérive croît avec H alors que le spread est payé une seule fois) ou filtrer le décile extrême.",
        )
    if t_net >= 1.8 and sub_ratio < 0.75:
        return (
            "REGIME_INSTABILITY (Rentable sur certains régimes mais instable dans le temps)",
            "O1_REGIME_CONDITIONING: Conditionner le signal à l'état d'autocorrélation locale ou au ratio de volatilité Yang-Zhang.",
        )
    if t_net >= 2.0 and sub_ratio >= 0.75:
        return (
            "PASS_CANDIDATE_FOR_BOOST (Candidat solide prêt pour l'audit /boost)",
            "SUBMIT_TO_BOOST_VALIDATOR: Vérifier DSR(K), PBO, Modèle Nul, Stress Coûts 2x et Plateau.",
        )
    return (
        "WEAK_NET_EDGE (Signal positif mais t_net < 2.0)",
        "O1_COMBINE_REGIME_GATE: Combiner avec un filtre de régime orthogonal pour augmenter le rapport signal/bruit.",
    )


# ============================================================================
# 4. BOUCLE DE DÉCOUVERTE AUTONOME & MUTATION CIBLÉE (`run_autonomous_discovery_loop`)
# ============================================================================

def run_autonomous_discovery_loop(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    roundtrip_cost_bps: float = 2.0,
    ledger_path: Optional[str | Path] = None,
    bars_per_year: float = 24.0 * 365.0,
) -> Dict[str, Any]:
    """
    Exécute une campagne de recherche autonome complète en boucle fermée :
    - Phase 1 : Diagnostic DGP complet (`diagnose_market_dgp`) + Planification Stratégique Algorithmique
      (`AlgorithmicStrategyPlanner`) prescrivant le playbook, l'horizon H* et les priors de familles.
    - Phase 2 (Génération 1) : Évaluation des familles d'hypothèses orthogonales (incluant la famille
      Chameleon H5 sur les marchés à bascule de régime), filtrage AST (`ast_originality_penalty`),
      débat contradictoire (`bull_bear_hypothesis_debate`) et ordonnancement UCB (`UCBFamilyBandit`).
    - Phase 3 (Génération 2 — Mutation Ciblée Sans Fuite) : Diagnostic du mode de défaillance
      (`diagnose_failure_mode`) calculé sur la tranche causale Train (70% initiaux) afin d'éviter le
      biais de sélection in-sample, et vérification hors-échantillon sur la tranche Validation (30%).
    - Phase 4 : Journalisation SHA-256 dans `ResearchLedger` et calcul du vrai DSR(K_total) et PBO.
    """
    c = np.asarray(close, dtype=np.float64)
    o = np.asarray(open_, dtype=np.float64)
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    n = len(c)
    if n < 100:
        raise ValueError(f"Série trop courte (n={n} < 100 barres) pour run_autonomous_discovery_loop.")

    # Rendements logarithmiques alignés : r[t] = log(c[t] / c[t-1])
    log_r = np.zeros(n, dtype=np.float64)
    log_r[1:] = np.diff(np.log(np.maximum(c, 1e-12)))

    # 1. Découpage causal strict Train (70%) / Validation (30%) AVANT tout diagnostic DGP
    if n >= 300:
        split_idx = min(max(250, int(0.70 * n)), n - 50)
    elif n >= 251:
        split_idx = min(max(201, int(0.70 * n)), n - 50)
    else:
        split_idx = max(1, int(0.70 * n))
    dgp_report = diagnose_market_dgp(
        c[:split_idx], h[:split_idx], l[:split_idx], roundtrip_cost_bps=roundtrip_cost_bps
    )
    strategy_plan = AlgorithmicStrategyPlanner.plan(dgp_report)
    opt_h = int(strategy_plan.optimal_horizon_bars)

    # 2. Calcul des primitives causales
    yz_short = AlphaPrimitives.yang_zhang_volatility(o, h, l, c, window=16)
    yz_long = AlphaPrimitives.yang_zhang_volatility(o, h, l, c, window=96)
    vol_ratio = np.where(yz_long > 1e-12, yz_short / yz_long, 1.0)
    ret_z = AlphaPrimitives.causal_zscore(log_r, window=24)

    # H1: Vol Squeeze Breakout (compression vol_ratio < 0.85 + choc directionnel ret_z)
    sig_h1 = np.where(vol_ratio < 0.85, ret_z, 0.0)

    # H2: Kalman Mean-Reversion (variance d'observation causale adaptative par EWMA)
    kalman_z = AlphaPrimitives.kalman_state_space_zscore(c, obs_noise_r=None)
    sig_h2 = -kalman_z

    # H3: Hawkes Cascade Exhaustion (parier sur le rebond après une grappe de chocs extrêmes)
    hawkes_int = AlphaPrimitives.hawkes_shock_intensity(log_r, threshold_sigma=2.0, decay_beta=0.30, vol_window=48)
    sig_h3 = -AlphaPrimitives.causal_zscore(hawkes_int, window=72)

    # H4: Regime-Switching Adaptive Signal (suit ret_z si autocorr locale > 0, l'inverse si < 0)
    local_rho = AlphaPrimitives.rolling_autocorr_regime(log_r, window=48)
    sig_h4 = np.where(local_rho >= 0.02, ret_z, np.where(local_rho <= -0.02, -ret_z, 0.0))

    # H5: Chameleon Kalman-Momentum Hybrid (Momentum en régime persistant, Kalman en régime anti-persistant)
    sig_h5 = np.where(local_rho >= 0.08, ret_z, np.where(local_rho <= -0.08, -kalman_z, 0.0))

    gen1_specs = [
        ("H1_VolSqueeze_Breakout", "I(YZ_16/YZ_96 < 0.85) * Z(r_t, 24)", "vol_ratio * ret_z", sig_h1, opt_h, 1.25),
        ("H2_Kalman_MeanReversion", "-KalmanInnovationZ(close, adaptive_ewma_r)", "-kalman_z", sig_h2, opt_h, 1.50),
        ("H3_Hawkes_Cascade_Reversion", "-Z(HawkesIntensity(r_t, 2.0sigma), 72)", "-hawkes_int", sig_h3, max(6, opt_h), 1.50),
        ("H4_Autocorr_Regime_Adaptive", "sign(RollingACF_48) * Z(r_t, 24)", "sign(local_rho) * ret_z", sig_h4, opt_h, 1.25),
        ("H5_Chameleon_Kalman_Regime", "Chameleon(RollingACF_48, ret_z, -kalman_z)", "local_rho * (ret_z - kalman_z)", sig_h5, opt_h, 1.20),
    ]

    bandit = UCBFamilyBandit([sp[0] for sp in gen1_specs], family_priors=strategy_plan.family_priors)
    ast_archive: List[str] = []
    evaluations: List[CandidateEvaluation] = []
    val_t_stats: List[float] = []
    train_t_stats: List[float] = []
    train_selection_scores: List[float] = []
    debate_reports: List[Dict[str, Any]] = []
    bar_pnl_matrix: List[np.ndarray] = []

    # Évaluation Génération 1 + Diagnostic de Mutation & Débat Bull/Bear sur Tranche Causale Train (70%)
    mutated_by_family: Dict[str, List[Tuple[str, str, str, np.ndarray, int, float, str]]] = {}

    for name, desc, ast_expr, sig_vec, horizon, thr in gen1_specs:
        nov = ast_originality_penalty(ast_expr, ast_archive)
        ast_archive.append(ast_expr)

        # Diagnostic causal sur les 70% d'entraînement uniquement (évite l'overfitting de mutation F4)
        train_res = evaluate_signal_non_overlapping(
            sig_vec[:split_idx], log_r[:split_idx], horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        debate = bull_bear_hypothesis_debate(
            dgp_report=dgp_report,
            expected_gross_bps=max(0.0, float(train_res["gross_bps"])),
            roundtrip_cost_bps=roundtrip_cost_bps,
            ast_novelty_report=nov,
            targets_martingale_price_history=strategy_plan.doob_martingale_veto,
        )
        val_res = evaluate_signal_non_overlapping(
            sig_vec[split_idx:], log_r[split_idx:], horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        f_mode_train, _ = diagnose_failure_mode(train_res, roundtrip_cost_bps)

        # Évaluation complète hors-holdout pour le registre officiel
        res = evaluate_signal_non_overlapping(
            sig_vec, log_r, horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        f_mode, f_mut = diagnose_failure_mode(res, roundtrip_cost_bps)
        bandit_t = float(train_res["t_net"]) if debate["approved_for_backtest"] else min(0.0, float(train_res["t_net"]))
        bandit.update(name, t_stat_net=bandit_t, ast_penalty=float(nov["regularization_penalty"]))

        evaluations.append(
            CandidateEvaluation(
                name=name,
                formula_desc=desc,
                params={"horizon": horizon, "threshold": thr, "ast_nodes": nov["n_ast_nodes"]},
                horizon_bars=horizon,
                n_trades=res["n_trades"],
                gross_bps_per_trade=round(res["gross_bps"], 3),
                net_bps_per_trade=round(res["net_bps"], 3),
                t_stat_gross=round(res["t_gross"], 3),
                t_stat_net=round(res["t_net"], 3),
                sharpe_net_ann=round(res["sharpe_ann"], 3),
                subperiod_positive_ratio=res["subperiod_pos_ratio"],
                failure_mode=f_mode,
                recommended_mutation=f_mut,
                trade_returns_net=res["net_trades"],
                bull_bear_approved=bool(debate["approved_for_backtest"]),
                bull_bear_conviction=float(debate["conviction_score"]),
                bull_bear_objections=tuple(debate["bear_objections"]),
            )
        )
        train_t_stats.append(float(train_res["t_net"]))
        if train_res["n_trades"] >= 20 and debate["approved_for_backtest"]:
            sel_score = 1e6 + float(train_res["t_net"])
        elif train_res["n_trades"] >= 20:
            sel_score = float(train_res["t_net"])
        else:
            sel_score = -1e9 + float(train_res["n_trades"])
        train_selection_scores.append(sel_score)
        debate_reports.append(debate)
        val_t_stats.append(float(val_res["t_net"]))
        bar_pnl_matrix.append(res["bar_pnl_net"])

        # Génération automatique des variantes mutées (Génération 2) prescrites par la tranche Train (70%) :
        fam_muts: List[Tuple[str, str, str, np.ndarray, int, float, str]] = []
        if "INSUFFICIENT_SAMPLE" in f_mode_train:
            thr_rel = max(0.85, round(thr * 0.70, 2))
            fam_muts.append((f"{name}_MUT_RELAX_THR", f"{desc} [thr={thr_rel}]", f"({ast_expr}) + 0.25 * ret_z", sig_vec, horizon, thr_rel, name))
        elif "GROSS_NEGATIVE_INVERTIBLE" in f_mode_train:
            fam_muts.append((f"{name}_MUT_INVERT", f"-({desc})", f"-({ast_expr})", -sig_vec, horizon, thr, name))
        elif "KILLED_BY_FRICTION" in f_mode_train:
            fam_muts.append((f"{name}_MUT_LONG_HORIZON", f"{desc} [H*3, thr+0.35]", f"({ast_expr}) / (1.0 + vol_ratio)", sig_vec, horizon * 3, thr + 0.35, name))
        elif "REGIME_INSTABILITY" in f_mode_train or "WEAK_NET_EDGE" in f_mode_train:
            gated_sig = np.where(np.abs(local_rho) > 0.04, sig_vec, 0.0)
            fam_muts.append((f"{name}_MUT_REGIME_GATED", f"I(|ACF_48|>0.04)*({desc})", f"local_rho * ({ast_expr})", gated_sig, horizon * 2, thr, name))
        elif "PASS_CANDIDATE_FOR_BOOST" in f_mode_train:
            fam_muts.append((f"{name}_MUT_HORIZON_2X", f"{desc} [H*2]", f"({ast_expr}) / (1.0 + vol_ratio)", sig_vec, horizon * 2, round(thr + 0.15, 2), name))
        else:
            combo_sig = np.where(vol_ratio < 1.15, sig_vec, 0.0)
            fam_muts.append((f"{name}_MUT_VOL_GATED", f"I(YZ_ratio<1.15)*({desc})", f"vol_ratio * ({ast_expr})", combo_sig, horizon * 2, thr, name))
        # Raffinement sélectif additionnel (Génération 3) disponible si l'ordonnanceur UCB sélectionne cette famille :
        refined_sig = np.where(np.abs(local_rho) > 0.06, sig_vec, 0.0)
        fam_muts.append((f"{name}_UCB_REFINED", f"I(|ACF_48|>0.06)*({desc})", f"tanh({ast_expr}) * local_rho", refined_sig, max(4, horizon), max(1.0, thr - 0.10), name))
        mutated_by_family[name] = fam_muts

    # Évaluation Génération 2 & 3 ordonnancée dynamiquement par UCBFamilyBandit.select_next_family() (RD-Agent(Q))
    n_ucb_pulls = 6
    for _ in range(n_ucb_pulls):
        chosen_fam = bandit.select_next_family()
        queue = mutated_by_family.get(chosen_fam, [])
        if not queue:
            # Si la file de la famille favorite est épuisée, choisir la meilleure famille disponible selon l'indice UCB
            avail = [f for f, q in mutated_by_family.items() if len(q) > 0]
            if not avail:
                break
            total_pulls = max(2, sum(bandit.counts.values()))
            chosen_fam = max(
                avail,
                key=lambda f: (bandit.rewards_sum[f] / max(1, bandit.counts[f]))
                + bandit.c * math.sqrt(math.log(total_pulls) / max(1, bandit.counts[f]))
                + 0.20 * bandit.priors.get(f, 0.0) / max(1, bandit.counts[f]),
            )
            queue = mutated_by_family[chosen_fam]
        name, desc, ast_expr, sig_vec, horizon, thr, parent_fam = queue.pop(0)
        nov = ast_originality_penalty(ast_expr, ast_archive)
        ast_archive.append(ast_expr)
        train_res = evaluate_signal_non_overlapping(
            sig_vec[:split_idx], log_r[:split_idx], horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        debate = bull_bear_hypothesis_debate(
            dgp_report=dgp_report,
            expected_gross_bps=max(0.0, float(train_res["gross_bps"])),
            roundtrip_cost_bps=roundtrip_cost_bps,
            ast_novelty_report=nov,
            targets_martingale_price_history=strategy_plan.doob_martingale_veto,
        )
        val_res = evaluate_signal_non_overlapping(
            sig_vec[split_idx:], log_r[split_idx:], horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        res = evaluate_signal_non_overlapping(
            sig_vec, log_r, horizon=horizon, entry_threshold=thr,
            roundtrip_cost_bps=roundtrip_cost_bps, bars_per_year=bars_per_year
        )
        f_mode, f_mut = diagnose_failure_mode(res, roundtrip_cost_bps)
        bandit_t = float(train_res["t_net"]) if debate["approved_for_backtest"] else min(0.0, float(train_res["t_net"]))
        bandit.update(parent_fam, t_stat_net=bandit_t, ast_penalty=float(nov["regularization_penalty"]))
        evaluations.append(
            CandidateEvaluation(
                name=name,
                formula_desc=desc,
                params={"horizon": horizon, "threshold": thr, "ast_nodes": nov["n_ast_nodes"]},
                horizon_bars=horizon,
                n_trades=res["n_trades"],
                gross_bps_per_trade=round(res["gross_bps"], 3),
                net_bps_per_trade=round(res["net_bps"], 3),
                t_stat_gross=round(res["t_gross"], 3),
                t_stat_net=round(res["t_net"], 3),
                sharpe_net_ann=round(res["sharpe_ann"], 3),
                subperiod_positive_ratio=res["subperiod_pos_ratio"],
                failure_mode=f_mode,
                recommended_mutation=f_mut,
                trade_returns_net=res["net_trades"],
                bull_bear_approved=bool(debate["approved_for_backtest"]),
                bull_bear_conviction=float(debate["conviction_score"]),
                bull_bear_objections=tuple(debate["bear_objections"]),
            )
        )
        train_t_stats.append(float(train_res["t_net"]))
        if train_res["n_trades"] >= 20 and debate["approved_for_backtest"]:
            sel_score = 1e6 + float(train_res["t_net"])
        elif train_res["n_trades"] >= 20:
            sel_score = float(train_res["t_net"])
        else:
            sel_score = -1e9 + float(train_res["n_trades"])
        train_selection_scores.append(sel_score)
        debate_reports.append(debate)
        val_t_stats.append(float(val_res["t_net"]))
        bar_pnl_matrix.append(res["bar_pnl_net"])

    # Sélection du meilleur candidat STRICTEMENT sur la tranche causale Train (zéro fuite Validation)
    k_trials_run = len(evaluations)
    best_idx = int(np.argmax(train_selection_scores))
    best_eval = evaluations[best_idx]
    best_train_t = round(float(train_t_stats[best_idx]), 3)
    best_val_t = round(float(val_t_stats[best_idx]), 3)
    debate_best = debate_reports[best_idx]

    # Calcul des Sharpe sur échelle STRICTEMENT commensurable :
    # (1) Grille temporelle homogène 1-barre (`trial_srs_per_bar`)
    # (2) Échelle trade-horizon homogène ramenée exactement à `best_eval.horizon_bars`
    best_h = max(1.0, float(best_eval.horizon_bars))
    trial_srs_per_bar = [
        sharpe(bp) if np.std(bp) > 1e-18 else 0.0
        for bp in bar_pnl_matrix
    ]
    trial_srs_per_trade_1bar = [
        (sharpe(ev.trade_returns_net) / math.sqrt(max(1.0, float(ev.horizon_bars))))
        if (len(ev.trade_returns_net) >= 2 and np.isfinite(sharpe(ev.trade_returns_net)))
        else 0.0
        for ev in evaluations
    ]

    if ledger_path is not None:
        ledger = ResearchLedger(str(ledger_path))
        for ev, bp, sr_bar, sr_1b in zip(evaluations, bar_pnl_matrix, trial_srs_per_bar, trial_srs_per_trade_1bar):
            sr_bar_clean = sr_bar if np.isfinite(sr_bar) else 0.0
            sr_1b_clean = sr_1b if np.isfinite(sr_1b) else 0.0
            ledger.log_trial(
                hypothesis_id=ev.name,
                params=ev.params,
                sr_per_period=sr_bar_clean,
                n_obs=len(bp),
                extra={
                    "formula": ev.formula_desc,
                    "failure_mode": ev.failure_mode,
                    "horizon_bars": ev.horizon_bars,
                    "n_trades": ev.n_trades,
                    "sr_scale": "bar_grid",
                    "sr_per_bar": sr_bar_clean,
                    "sr_per_trade_1bar": sr_1b_clean,
                    "bull_bear_approved": ev.bull_bear_approved,
                    "bull_bear_conviction": ev.bull_bear_conviction,
                },
            )
        all_bar_srs = np.asarray(
            [
                float(r["extra"]["sr_per_bar"])
                if isinstance(r.get("extra"), dict) and "sr_per_bar" in r["extra"]
                else (
                    float(r["sr_per_period"])
                    if not (isinstance(r.get("extra"), dict) and r["extra"].get("sr_scale") == "trade_horizon")
                    else float(r["extra"].get("sr_per_trade_1bar", 0.0))
                )
                for r in ledger.trials()
                if r.get("sr_per_period") is not None
            ],
            dtype=np.float64,
        )
        all_trade_srs_at_best_h = np.asarray(
            [
                (float(r["extra"]["sr_per_trade_1bar"]) * math.sqrt(best_h))
                if isinstance(r.get("extra"), dict) and "sr_per_trade_1bar" in r["extra"]
                else (float(r["sr_per_period"]) * math.sqrt(best_h))
                for r in ledger.trials()
                if r.get("sr_per_period") is not None
            ],
            dtype=np.float64,
        )
        total_k = ledger.n_trials()
    else:
        all_bar_srs = np.asarray(trial_srs_per_bar, dtype=np.float64)
        all_trade_srs_at_best_h = np.asarray(
            [s * math.sqrt(best_h) for s in trial_srs_per_trade_1bar], dtype=np.float64
        )
        total_k = k_trials_run

    # Audit /boost sur le meilleur candidat trouvé en tenant compte de TOUS les essais (échelles commensurables)
    mat = np.column_stack(bar_pnl_matrix)
    pbo_res = pbo_cscv(mat, n_blocks=8)
    best_trades = best_eval.trade_returns_net
    dsr_res = dsr(best_trades, all_trade_srs_at_best_h)
    dsr_bar_res = dsr(bar_pnl_matrix[best_idx], all_bar_srs)

    summary_rows = []
    for ev in evaluations:
        d = asdict(ev)
        d.pop("trade_returns_net", None)
        d["bull_bear_objections"] = list(ev.bull_bear_objections)
        summary_rows.append(d)

    return {
        "dgp_diagnosis": dgp_report,
        "dgp_scope": "train_causal_slice",
        "split_idx": split_idx,
        "strategy_plan": asdict(strategy_plan),
        "bandit_summary": bandit.summary(),
        "bull_bear_debate_summary": {
            "n_approved": sum(1 for r in debate_reports if r["approved_for_backtest"]),
            "n_vetoed": sum(1 for r in debate_reports if not r["approved_for_backtest"]),
        },
        "total_trials_logged_k": total_k,
        "candidates_evaluated": summary_rows,
        "best_candidate": {
            "name": best_eval.name,
            "formula": best_eval.formula_desc,
            "horizon_bars": best_eval.horizon_bars,
            "n_trades": best_eval.n_trades,
            "gross_bps": best_eval.gross_bps_per_trade,
            "net_bps": best_eval.net_bps_per_trade,
            "t_stat_net": best_eval.t_stat_net,
            "train_t_stat_net": best_train_t,
            "val_t_stat_net": best_val_t,
            "sharpe_net_ann": best_eval.sharpe_net_ann,
            "failure_mode": best_eval.failure_mode,
            "dsr_at_total_k": round(float(dsr_res["dsr"]), 4) if np.isfinite(dsr_res["dsr"]) else 0.0,
            "dsr_bar_grid": round(float(dsr_bar_res["dsr"]), 4) if np.isfinite(dsr_bar_res["dsr"]) else 0.0,
            "pbo_cscv": round(float(pbo_res["pbo"]), 4),
            "bull_bear_approved": debate_best["approved_for_backtest"],
            "bull_bear_conviction": debate_best["conviction_score"],
            "passes_boost": bool(
                not strategy_plan.doob_martingale_veto
                and debate_best["approved_for_backtest"]
                and best_eval.n_trades >= GATES["min_trades"]
                and best_val_t > 0.0
                and np.isfinite(dsr_res["dsr"])
                and dsr_res["dsr"] >= GATES["dsr_min"]
                and np.isfinite(dsr_bar_res["dsr"])
                and dsr_bar_res["dsr"] >= GATES["dsr_min"]
                and pbo_res["pbo"] <= GATES["pbo_max"]
                and best_eval.subperiod_positive_ratio >= 0.75
            ),
        },
    }


# ============================================================================
# 5. RÉGRESSION SYMBOLIQUE ÉVOLUTIONNAIRE AVEC PÉNALISATION AICc (SECTION 13.4)
# ============================================================================

def symbolic_alpha_search_aicc(
    features_dict: Dict[str, np.ndarray],
    log_returns: np.ndarray,
    horizon: int = 4,
    roundtrip_cost_bps: float = 2.0,
    ledger_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Moteur de Régression Symbolique / WorldQuant Formulaic Alpha (Section 13.4 de l'Encyclopédie) :
    - Combine des variables d'état causales X_i via des opérateurs non-linéaires parcimonieux
      (tanh, produit d'interaction, différence de rang/z-score, porte de signe)
    - Pénalise chaque formule par sa complexité syntaxique k (nombre de noeuds/opérateurs)
      via un score inspiré d'AICc : Score_AICc = t_stat_net - 0.35 * k_nodes
    - Compte CHAQUE formule générée dans le compteur d'essais K du `ResearchLedger`.
    """
    names = list(features_dict.keys())
    if len(names) < 2:
        raise ValueError("Fournir au moins 2 primitives causales dans features_dict.")

    candidates: List[Tuple[str, np.ndarray, int]] = []
    # 1. Primitives unitaires et leurs inverses (complexité k=1)
    for nm in names:
        v = np.asarray(features_dict[nm], dtype=np.float64)
        candidates.append((nm, v, 1))
        candidates.append((f"-{nm}", -v, 1))
        candidates.append((f"tanh({nm})", np.tanh(v), 2))

    # 2. Interactions non-linéaires d'ordre 2 (complexité k=3)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            v1 = np.asarray(features_dict[n1], dtype=np.float64)
            v2 = np.asarray(features_dict[n2], dtype=np.float64)
            candidates.append((f"({n1} * tanh({n2}))", v1 * np.tanh(v2), 3))
            candidates.append((f"(sign({n1}) * {n2})", np.sign(v1) * v2, 3))
            candidates.append((f"({n1} - {n2})", 0.5 * (v1 - v2), 2))

    results = []
    trial_srs = []
    ledger = ResearchLedger(str(ledger_path)) if ledger_path is not None else None

    for expr, vec, k_nodes in candidates:
        res = evaluate_signal_non_overlapping(
            vec, log_returns, horizon=horizon, entry_threshold=1.0, roundtrip_cost_bps=roundtrip_cost_bps
        )
        sr_trade = sharpe(res["net_trades"]) if len(res["net_trades"]) >= 2 else 0.0
        sr_trade_clean = sr_trade if np.isfinite(sr_trade) else 0.0
        sr_bar = sharpe(res["bar_pnl_net"]) if np.std(res["bar_pnl_net"]) > 1e-18 else 0.0
        sr_bar_clean = sr_bar if np.isfinite(sr_bar) else 0.0
        trial_srs.append(sr_trade_clean)
        aicc_score = float(res["t_net"]) - 0.35 * float(k_nodes)

        if ledger is not None:
            sr_1bar = sr_trade_clean / math.sqrt(max(1.0, float(horizon)))
            ledger.log_trial(
                hypothesis_id=f"SYM_{expr}",
                params={"horizon": horizon, "k_nodes": k_nodes},
                sr_per_period=sr_trade_clean,
                n_obs=res["n_trades"],
                extra={
                    "aicc_score": round(aicc_score, 3),
                    "horizon_bars": horizon,
                    "sr_scale": "trade_horizon",
                    "sr_per_bar": sr_bar_clean,
                    "sr_per_trade_1bar": sr_1bar,
                },
            )

        results.append(
            {
                "formula": expr,
                "k_complexity_nodes": k_nodes,
                "n_trades": res["n_trades"],
                "net_bps": round(res["net_bps"], 3),
                "t_net": round(res["t_net"], 3),
                "aicc_penalized_score": round(aicc_score, 3),
                "subperiod_pos_ratio": res["subperiod_pos_ratio"],
                "net_trades": res["net_trades"],
            }
        )

    best = max(results, key=lambda d: d["aicc_penalized_score"])
    if ledger is not None:
        h_target = max(1.0, float(horizon))
        all_srs = np.asarray(
            [
                (float(r["extra"]["sr_per_trade_1bar"]) * math.sqrt(h_target))
                if isinstance(r.get("extra"), dict) and "sr_per_trade_1bar" in r["extra"]
                else (
                    float(r["sr_per_period"]) * math.sqrt(h_target / max(1.0, float(r["extra"]["horizon_bars"])))
                    if isinstance(r.get("extra"), dict) and "horizon_bars" in r["extra"]
                    else float(r["sr_per_period"]) * math.sqrt(h_target)
                )
                for r in ledger.trials()
                if r.get("sr_per_period") is not None
            ],
            dtype=np.float64,
        )
    else:
        all_srs = np.asarray(trial_srs, dtype=np.float64)
    dsr_best = dsr(best["net_trades"], all_srs)
    best_clean = {k: v for k, v in best.items() if k != "net_trades"}
    best_clean["dsr_at_total_k"] = round(float(dsr_best["dsr"]), 4) if np.isfinite(dsr_best["dsr"]) else 0.0
    best_clean["total_k_penalized"] = len(all_srs)

    return {
        "n_symbolic_formulas_tested": len(results),
        "best_symbolic_formula": best_clean,
        "top_5_formulas": [
            {k: v for k, v in r.items() if k != "net_trades"}
            for r in sorted(results, key=lambda d: d["aicc_penalized_score"], reverse=True)[:5]
        ],
    }


# ============================================================================
# 6. SOTA 2025-2026 : ALPHAAGENT AST REGULARIZATION, RD-AGENT(Q) UCB BANDIT
#    & TRADINGAGENTS BULL/BEAR PRE-COMMITMENT DEBATE GATE
# ============================================================================

def _canonicalize_ast_node(node: ast.AST, normalize_vars: bool = False) -> Tuple[str, List[str]]:
    """
    Parcourt récursivement un arbre syntaxique abstrait (AST) Python d'une formule d'alpha
    (AlphaAgent, Tang et al. KDD 2025, arXiv:2502.16789) :
    - Canonicalise les opérations commutatives (Add, Mult, BitAnd, BitOr) en triant les sous-arbres
      pour détecter les clones algébriques tels que `(a + b) * c` vs `c * (b + a)`.
    - Extrait tous les sous-arbres (shingles structurels) pour mesurer l'originalité face au Factor Zoo.
    """
    shingles: List[str] = []

    if isinstance(node, ast.Expression):
        return _canonicalize_ast_node(node.body, normalize_vars=normalize_vars)

    if isinstance(node, ast.Constant):
        # Les constantes numériques sont abstraites en `CONST` pour détecter le simple tweaking de seuil
        rep = "CONST"
        shingles.append(rep)
        return rep, shingles

    if isinstance(node, ast.Name):
        rep = "VAR" if normalize_vars else f"VAR({node.id})"
        shingles.append(rep)
        return rep, shingles

    if isinstance(node, ast.UnaryOp):
        op_name = type(node.op).__name__
        sub_rep, sub_sh = _canonicalize_ast_node(node.operand, normalize_vars=normalize_vars)
        rep = f"{op_name}({sub_rep})"
        shingles.extend(sub_sh)
        shingles.append(rep)
        return rep, shingles

    if isinstance(node, ast.BinOp):
        op_name = type(node.op).__name__
        left_rep, left_sh = _canonicalize_ast_node(node.left, normalize_vars=normalize_vars)
        right_rep, right_sh = _canonicalize_ast_node(node.right, normalize_vars=normalize_vars)
        shingles.extend(left_sh)
        shingles.extend(right_sh)
        if isinstance(node.op, (ast.Add, ast.Mult)):
            ordered = sorted([left_rep, right_rep])
            rep = f"{op_name}({ordered[0]},{ordered[1]})"
        else:
            rep = f"{op_name}({left_rep},{right_rep})"
        shingles.append(rep)
        return rep, shingles

    if isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else type(node.func).__name__
        arg_reps = []
        for a in node.args:
            ar, ash = _canonicalize_ast_node(a, normalize_vars=normalize_vars)
            arg_reps.append(ar)
            shingles.extend(ash)
        rep = f"CALL_{func_name}({','.join(arg_reps)})"
        shingles.append(rep)
        return rep, shingles

    if isinstance(node, ast.Compare):
        left_rep, left_sh = _canonicalize_ast_node(node.left, normalize_vars=normalize_vars)
        shingles.extend(left_sh)
        comp_parts = [left_rep]
        for op, comp in zip(node.ops, node.comparators):
            cr, csh = _canonicalize_ast_node(comp, normalize_vars=normalize_vars)
            shingles.extend(csh)
            comp_parts.append(f"{type(op).__name__}:{cr}")
        rep = f"CMP({'|'.join(comp_parts)})"
        shingles.append(rep)
        return rep, shingles

    # Fallback générique
    child_reps = []
    for ch in ast.iter_child_nodes(node):
        cr, csh = _canonicalize_ast_node(ch, normalize_vars=normalize_vars)
        child_reps.append(cr)
        shingles.extend(csh)
    rep = f"{type(node).__name__}({','.join(child_reps)})"
    shingles.append(rep)
    return rep, shingles


def ast_canonical_shingles(expr: str, normalize_vars: bool = False) -> Tuple[str, Set[str], int]:
    """
    Parse une expression mathématique d'alpha en AST Python et retourne :
    (forme_canonique, ensemble_des_sous_arbres, nombre_de_noeuds).
    """
    tree = ast.parse(expr, mode="eval")
    canon, shingle_list = _canonicalize_ast_node(tree, normalize_vars=normalize_vars)
    n_nodes = len(shingle_list)
    return canon, set(shingle_list), n_nodes


def ast_similarity_score(expr_a: str, expr_b: str) -> Dict[str, Any]:
    """
    Mesure la similarité structurelle AST entre deux formules d'alpha (AlphaAgent KDD'25) :
    - `exact_named_jaccard` : similarité avec noms des variables (détecte clones algébriques et tweaking de constantes).
    - `skeleton_jaccard` : similarité du squelette d'opérateurs pur (`normalize_vars=True`).
    - `combined_similarity` = 0.7 * exact_named_jaccard + 0.3 * skeleton_jaccard.
    """
    c_a, sh_a, n_a = ast_canonical_shingles(expr_a, normalize_vars=False)
    c_b, sh_b, n_b = ast_canonical_shingles(expr_b, normalize_vars=False)
    _, sk_a, _ = ast_canonical_shingles(expr_a, normalize_vars=True)
    _, sk_b, _ = ast_canonical_shingles(expr_b, normalize_vars=True)

    inter_named = len(sh_a & sh_b)
    union_named = max(1, len(sh_a | sh_b))
    j_named = inter_named / union_named

    inter_sk = len(sk_a & sk_b)
    union_sk = max(1, len(sk_a | sk_b))
    j_sk = inter_sk / union_sk

    comb = 0.70 * j_named + 0.30 * j_sk
    return {
        "canonical_a": c_a,
        "canonical_b": c_b,
        "nodes_a": n_a,
        "nodes_b": n_b,
        "exact_named_jaccard": round(float(j_named), 4),
        "skeleton_jaccard": round(float(j_sk), 4),
        "combined_similarity": round(float(comb), 4),
        "is_algebraic_clone": bool(c_a == c_b or j_named >= 0.85),
    }


def ast_originality_penalty(
    expr: str,
    archive_exprs: List[str],
    max_nodes: int = 12,
    similarity_threshold: float = 0.80,
) -> Dict[str, Any]:
    """
    Porte de régularisation d'originalité et de parcimonie (AlphaAgent KDD'25) :
    Rejette un candidat AVANT de gaspiller le budget de backtest ou pénalise son score
    si (1) sa profondeur/taille AST dépasse `max_nodes` (overfitting syntaxique), ou
    (2) sa similarité AST maximale avec l'archive des facteurs connus dépasse `similarity_threshold`.
    """
    canon, _, n_nodes = ast_canonical_shingles(expr, normalize_vars=False)
    max_sim = 0.0
    closest_expr = None
    for arch in archive_exprs:
        sim = ast_similarity_score(expr, arch)["combined_similarity"]
        if sim > max_sim:
            max_sim = sim
            closest_expr = arch

    complexity_excess = max(0, n_nodes - max_nodes)
    crowding_penalty = max(0.0, (max_sim - 0.50) * 2.0)
    total_penalty = 0.25 * float(complexity_excess) + crowding_penalty
    accepted = bool(n_nodes <= max_nodes and max_sim < similarity_threshold)

    return {
        "canonical_ast": canon,
        "n_ast_nodes": n_nodes,
        "max_similarity_to_archive": round(float(max_sim), 4),
        "closest_archive_formula": closest_expr,
        "regularization_penalty": round(float(total_penalty), 4),
        "accepted_as_novel": accepted,
    }


class UCBFamilyBandit:
    """
    Ordonnanceur par Bandit Manchot UCB1 (inspiré de Microsoft RD-Agent(Q), arXiv:2505.15155)
    pour allouer dynamiquement le budget de recherche K_max entre les familles d'hypothèses
    orthogonales sans s'acharner sur une famille réfutée (martingale pure ou friction excessive) :
        UCB_i(t) = mu_hat_i + exploration_c * sqrt(ln(N_total) / n_i)
    """

    def __init__(
        self,
        family_names: List[str],
        exploration_c: float = 1.20,
        family_priors: Optional[Dict[str, float]] = None,
    ) -> None:
        if not family_names:
            raise ValueError("Au moins une famille d'alpha requise.")
        self.families = list(family_names)
        self.c = float(exploration_c)
        self.priors: Dict[str, float] = {
            f: float(family_priors.get(f, 1.0 / len(self.families))) if family_priors else (1.0 / len(self.families))
            for f in self.families
        }
        self.counts: Dict[str, int] = {f: 0 for f in self.families}
        self.rewards_sum: Dict[str, float] = {f: 0.0 for f in self.families}
        self.history: List[Dict[str, Any]] = []

    def select_next_family(self) -> str:
        # Phase d'amorçage : tester au moins 1 fois chaque famille orthogonale (par ordre décroissant de prior)
        unvisited = [f for f in self.families if self.counts[f] == 0]
        if unvisited:
            return max(unvisited, key=lambda f: self.priors.get(f, 0.0))
        total_n = sum(self.counts.values())
        best_f = self.families[0]
        best_ucb = -1e18
        for f in self.families:
            mu = self.rewards_sum[f] / self.counts[f]
            bonus = self.c * math.sqrt(math.log(max(2, total_n)) / self.counts[f])
            prior_boost = 0.20 * self.priors.get(f, 0.0) / max(1, self.counts[f])
            ucb = mu + bonus + prior_boost
            if ucb > best_ucb:
                best_ucb = ucb
                best_f = f
        return best_f

    def update(self, family: str, t_stat_net: float, ast_penalty: float = 0.0) -> float:
        """
        Transforme le t_stat_net pénalisé par l'AST en récompense bornée dans [0, 1] :
        - t_net <= 0 -> récompense proche de 0
        - t_net >= 3.0 (seuil Harvey-Liu-Zhu) -> récompense proche de 1
        """
        raw = float(t_stat_net) - float(ast_penalty)
        reward = float(np.clip(raw / 3.5, 0.0, 1.0))
        self.counts[family] += 1
        self.rewards_sum[family] += reward
        self.history.append({"family": family, "t_stat_net": round(float(t_stat_net), 4), "reward": round(reward, 4)})
        return reward

    def summary(self) -> Dict[str, Any]:
        total_n = max(1, sum(self.counts.values()))
        stats_by_family = {}
        for f in self.families:
            cnt = self.counts[f]
            mean_r = (self.rewards_sum[f] / cnt) if cnt > 0 else 0.0
            stats_by_family[f] = {
                "trials_allocated": cnt,
                "allocation_share": round(cnt / total_n, 4),
                "mean_reward": round(mean_r, 4),
            }
        return {"total_pulls": sum(self.counts.values()), "families": stats_by_family}


def bull_bear_hypothesis_debate(
    dgp_report: Dict[str, Any],
    expected_gross_bps: float,
    roundtrip_cost_bps: float,
    ast_novelty_report: Optional[Dict[str, Any]] = None,
    targets_martingale_price_history: bool = False,
) -> Dict[str, Any]:
    """
    Débat Structuré Pré-Backtest Bull vs Bear (inspiré de TauricResearch/TradingAgents, arXiv:2412.20138) :
    Évalue quantitativement la thèse du chercheur (Bull) face au procureur structurel (Bear)
    AVANT de consommer le budget d'essais K_max :
    - Veto immédiat si l'hypothèse tente de prédire la direction d'une martingale pure à loi connue
      à partir du seul historique des prix (Théorème d'Arrêt Optionnel de Doob : EV = -Coûts).
    - Veto si l'alpha brut espéré est inférieur à 1.25x les coûts aller-retour réels.
    - Veto si la formule est un clone AST d'une idée déjà archivée/réfutée.
    """
    bear_objections: List[str] = []
    bull_points: List[str] = []
    score = 0.50

    verdict_str = str(dgp_report.get("structural_verdict", ""))
    friction_ratio = float(dgp_report.get("friction_to_sigma_ratio", 1.0))

    if "MARTINGALE_PURE_SANS_MEMOIRE" in verdict_str and targets_martingale_price_history:
        bear_objections.append(
            "VETO_DOOB_MARTINGALE: Série diagnostiquée Martingale sans mémoire; toute règle sur prix seuls donne E[PnL] = -Coûts."
        )
        score -= 0.60
    elif "EXPLOITABLE_CONDITIONNEL" in verdict_str:
        bull_points.append(f"DGP présente une structure mesurée : {verdict_str}")
        score += 0.20

    if expected_gross_bps <= 1.25 * roundtrip_cost_bps:
        bear_objections.append(
            f"VETO_FRICTION: Edge brut attendu ({expected_gross_bps:.2f} bps) <= 1.25x coûts réels ({roundtrip_cost_bps:.2f} bps)."
        )
        score -= 0.40
    else:
        bull_points.append(
            f"Marge nette théorique positive : {expected_gross_bps - roundtrip_cost_bps:.2f} bps au-dessus du break-even."
        )
        score += 0.15

    if friction_ratio > 0.50:
        bear_objections.append(
            f"ALERTE_HORIZON: Coût/Volatilité par barre = {friction_ratio:.2f} > 0.50; horizon trop court."
        )
        score -= 0.20

    if ast_novelty_report is not None:
        if not ast_novelty_report.get("accepted_as_novel", True):
            bear_objections.append(
                f"VETO_AST_CROWDING: Formule non originale ou trop complexe (sim={ast_novelty_report['max_similarity_to_archive']}, nodes={ast_novelty_report['n_ast_nodes']})."
            )
            score -= 0.50
        else:
            bull_points.append(
                f"Formule AST originale et parcimonieuse ({ast_novelty_report['n_ast_nodes']} noeuds, sim={ast_novelty_report['max_similarity_to_archive']})."
            )
            score += 0.15

    approved = bool(score >= 0.45 and not any(obj.startswith("VETO_") for obj in bear_objections))
    return {
        "approved_for_backtest": approved,
        "conviction_score": round(float(np.clip(score, 0.0, 1.0)), 4),
        "bull_arguments": bull_points,
        "bear_objections": bear_objections,
    }


if __name__ == "__main__":
    # Auto-test sur deux marchés synthétiques :
    # 1) Une martingale pure (doit être diagnostiquée comme telle et rejetée par /boost)
    # 2) Un marché avec vraies cascades de liquidations (Hawkes mean-reversion) -> doit être découvert et validé
    rng = np.random.default_rng(42)
    n_bars = 5000

    # Cas 1 : Martingale pure
    r_noise = rng.normal(0.0, 0.002, size=n_bars)
    c_noise = 100.0 * np.exp(np.cumsum(r_noise))
    h_noise = c_noise * (1.0 + np.abs(rng.normal(0, 0.001, size=n_bars)))
    l_noise = c_noise * (1.0 - np.abs(rng.normal(0, 0.001, size=n_bars)))
    o_noise = np.roll(c_noise, 1)
    o_noise[0] = c_noise[0]

    rep_noise = run_autonomous_discovery_loop(o_noise, h_noise, l_noise, c_noise, roundtrip_cost_bps=2.0)
    print("=== AUTO-TEST 1 : MARTINGALE PURE ===")
    print("Verdict DGP :", rep_noise["dgp_diagnosis"]["structural_verdict"])
    print("Meilleur candidat :", rep_noise["best_candidate"])
    assert not rep_noise["best_candidate"]["passes_boost"], "Une martingale pure ne doit pas passer /boost !"
    print("[OK] Martingale pure correctement rejetée par /boost.\n")

    # Cas 2 : Marché à régimes d'autocorrélation persistants (alternance Momentum / Mean-Reversion)
    r_reg = np.zeros(n_bars)
    for t in range(1, n_bars):
        regime_rho = 0.35 if (t // 250) % 2 == 0 else -0.35
        r_reg[t] = regime_rho * r_reg[t - 1] + rng.normal(0.0, 0.003)
    c_reg = 100.0 * np.exp(np.cumsum(r_reg))
    h_reg = c_reg * (1.0 + np.abs(rng.normal(0, 0.001, size=n_bars)))
    l_reg = c_reg * (1.0 - np.abs(rng.normal(0, 0.001, size=n_bars)))
    o_reg = np.roll(c_reg, 1)
    o_reg[0] = c_reg[0]

    rep_reg = run_autonomous_discovery_loop(o_reg, h_reg, l_reg, c_reg, roundtrip_cost_bps=1.5)
    print("=== AUTO-TEST 2 : MARCHÉ À RÉGIME EXPLOITABLE (CHAMELEON) ===")
    print("Verdict DGP :", rep_reg["dgp_diagnosis"]["structural_verdict"])
    print("Plan Stratégique :", rep_reg["strategy_plan"]["primary_playbook"], "| H* =", rep_reg["strategy_plan"]["optimal_horizon_bars"])
    print("Meilleur candidat découvert :", rep_reg["best_candidate"])
    assert rep_reg["dgp_diagnosis"]["dominant_regime"] == "REGIME_SWITCHING_CHAMELEON", rep_reg["dgp_diagnosis"]
    assert rep_reg["strategy_plan"]["primary_playbook"] == "CHAMELEON_REGIME_ADAPTIVE_SWITCHING", rep_reg["strategy_plan"]
    assert rep_reg["best_candidate"]["passes_boost"], "Le vrai alpha de régime aurait dû être découvert !"
    print("[OK] Vrai alpha structurel Chameleon planifié, découvert et validé par /boost.\n")

    # Cas 3 : AlphaAgent AST Regularization (détection de clones algébriques commutatifs & tweaking de constantes)
    sim_clone = ast_similarity_score("(ret_z + vol_ratio) * tanh(kalman_z * 1.5)", "tanh(2.0 * kalman_z) * (vol_ratio + ret_z)")
    assert sim_clone["is_algebraic_clone"], f"Clone algébrique non détecté: {sim_clone}"
    nov_reject = ast_originality_penalty("tanh(2.0 * kalman_z) * (vol_ratio + ret_z)", ["(ret_z + vol_ratio) * tanh(kalman_z * 1.5)"])
    assert not nov_reject["accepted_as_novel"], "Le clone AST aurait dû être rejeté !"
    nov_accept = ast_originality_penalty("-hawkes_int * sign(local_rho)", ["(ret_z + vol_ratio) * tanh(kalman_z * 1.5)"])
    assert nov_accept["accepted_as_novel"], "La formule orthogonale aurait dû être acceptée !"
    print("[OK] AlphaAgent AST Regularization : clones commutatifs rejetés, formules orthogonales acceptées.")

    # Cas 4 : RD-Agent(Q) UCBFamilyBandit (concentration dynamique du budget K sur la famille rentable)
    bandit = UCBFamilyBandit(["Martingale_Breakout", "Kalman_StateSpace", "Regime_Persistence"])
    for step in range(30):
        fam = bandit.select_next_family()
        simulated_t = 3.4 if fam == "Regime_Persistence" else (-0.4 if fam == "Martingale_Breakout" else 0.8)
        bandit.update(fam, t_stat_net=simulated_t)
    b_sum = bandit.summary()
    assert b_sum["families"]["Regime_Persistence"]["trials_allocated"] > b_sum["families"]["Martingale_Breakout"]["trials_allocated"] * 3
    print("[OK] RD-Agent(Q) UCBFamilyBandit :", b_sum["families"])

    # Cas 5 : TradingAgents Bull/Bear Debate Gate (veto sur martingale pure, approbation sur DGP structuré)
    veto_res = bull_bear_hypothesis_debate(
        rep_noise["dgp_diagnosis"], expected_gross_bps=5.0, roundtrip_cost_bps=2.0, targets_martingale_price_history=True
    )
    assert not veto_res["approved_for_backtest"], "Veto Doob attendu sur martingale !"
    pass_res = bull_bear_hypothesis_debate(
        rep_reg["dgp_diagnosis"], expected_gross_bps=12.0, roundtrip_cost_bps=1.5, ast_novelty_report=nov_accept
    )
    assert pass_res["approved_for_backtest"], f"Approbation attendue sur régime structuré: {pass_res}"
    print("[OK] TradingAgents Bull/Bear Debate Gate validé.")
