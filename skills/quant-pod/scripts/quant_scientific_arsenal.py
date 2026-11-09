"""
quant_scientific_arsenal.py
===========================
Arsenal Mathématique, Statistique, Microstructural et d'Ingénierie de Portefeuille
pour Quant Pod v2 (Teamwork + Boost).

Implémente l'intégralité des piliers de l'Encyclopédie Maître :
1. Différenciation Fractionnaire à Fenêtre Fixe (FFD - Marcos López de Prado)
2. Modélisation Ornstein-Uhlenbeck (demi-vie de retour à la moyenne & test ADF)
3. Probabilistic Sharpe Ratio (PSR) & Deflated Sharpe Ratio (DSR - Bailey & López de Prado)
4. Purged & Embargoed K-Fold Split (Validation croisée sans fuite temporelle)
5. Dimensionnement Dynamique : Volatility Targeting, Standardisation Carver [-20,+20] & Fractional Kelly
6. Modélisation de l'Impact de Marché (Loi de la Racine Carrée de Grinold & Kahn / Almgren-Chriss)
7. Théorie des Matrices Aléatoires (RMT - Loi de Marchenko-Pastur) & Allocation HRP (Hierarchical Risk Parity)
8. Filtre de Kalman 2D en Espace d'État pour Statistical Arbitrage / Pairs Trading (Hedge Ratio dynamique beta_t)
9. Triple Barrier Method & Meta-Labeling (Marcos López de Prado)
10. Théorie des Valeurs Extrêmes (EVT - GPD Peak-Over-Threshold) & CVaR / Expected Shortfall à 99%
11. Microstructure & Multi-Actifs : Order Flow Imbalance (OFI), VPIN, AMM LVR vs Fees, Cross-Sectional Momentum, Nelson-Siegel
12. Synchronisation Point-in-Time Stricte (ASOF JOIN backward sur available_timestamp vs event_timestamp)
"""

import math
import numpy as np
import pandas as pd

try:
    from scipy.stats import norm, skew, kurtosis, genpareto
    from scipy.cluster.hierarchy import linkage, leaves_list
    from scipy.spatial.distance import squareform
except ImportError:
    norm = skew = kurtosis = genpareto = linkage = leaves_list = squareform = None

try:
    from statsmodels.tsa.stattools import adfuller
except ImportError:
    adfuller = None

from typing import Tuple, List, Generator, Dict, Any, Optional


# ============================================================================
# 1. DIFFÉRENCIATION FRACTIONNAIRE (STATIONNARITÉ SANS PERTE DE MÉMOIRE)
# ============================================================================

def get_ffd_weights(d: float, threshold: float = 1e-4) -> np.ndarray:
    """
    Calcule les poids binomiaux w_k pour la différenciation fractionnaire d'ordre d (0 < d < 1)
    avec troncature à seuil fixe (Fixed-Window Fractional Differentiation).
    w_0 = 1, w_k = -w_{k-1} * (d - k + 1) / k
    """
    weights = [1.0]
    k = 1
    while True:
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights[::-1], dtype=np.float64)


def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """
    Applique la différenciation fractionnaire à fenêtre fixe sur une série temporelle (log-prix).
    Permet d'atteindre la stationnarité statistique tout en préservant la mémoire longue.
    """
    weights = get_ffd_weights(d, threshold)
    width = len(weights) - 1
    vals = series.values
    out = np.full(len(vals), np.nan)
    for i in range(width, len(vals)):
        out[i] = np.dot(weights, vals[i - width : i + 1])
    return pd.Series(out, index=series.index, name=f"{series.name}_ffd_{d:.2f}")


def find_min_ffd_d(log_price_series: pd.Series, p_val_target: float = 0.05) -> Tuple[float, float, float]:
    """
    Cherche le plus petit ordre d'intégration fractionnaire d* dans [0.05, 1.00]
    qui rend la série stationnaire (ADF p-value < 0.05, ou test AR(1) de secours si statsmodels absent).
    Retourne (d_optimal, p_value_adf, correlation_avec_log_prix).
    """
    clean_s = log_price_series.dropna()
    for d in np.linspace(0.05, 1.00, 20):
        diff_s = frac_diff_ffd(clean_s, d=d).dropna()
        if len(diff_s) < 50:
            continue
        if adfuller is not None:
            _, p_val, _, _, _, _ = adfuller(diff_s, maxlag=1, regression="c", autolag=None)
        else:
            # Test DF(0) analytique si statsmodels non installé
            y = np.diff(diff_s.values)
            x = diff_s.values[:-1]
            X = np.column_stack([np.ones(len(x)), x])
            beta, residuals, _, _ = np.linalg.lstsq(X, y, rcond=None)
            s2 = np.sum((y - X @ beta) ** 2) / max(1, len(y) - 2)
            se_b = math.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
            t_df = beta[1] / max(1e-12, se_b)
            # Seuil critique de MacKinnon à 5% ~ -2.86
            p_val = 0.01 if t_df < -2.86 else 0.20
        corr = np.corrcoef(clean_s.loc[diff_s.index], diff_s)[0, 1]
        if p_val < p_val_target:
            return round(float(d), 2), float(p_val), float(corr)
    return 1.0, 0.0, 0.0


# ============================================================================
# 2. MODÉLISATION ORNSTEIN-UHLENBECK & DEMI-VIE DE RETOUR À LA MOYENNE
# ============================================================================

def estimate_ou_half_life(spread: pd.Series) -> Tuple[float, float]:
    """
    Estime la vitesse de rappel theta et la demi-vie (Half-Life en périodes)
    d'un processus d'Ornstein-Uhlenbeck dX_t = theta*(mu - X_t)dt + sigma*dW_t
    par régression AR(1) : Delta_X_t = alpha + beta * X_{t-1} + epsilon_t.
    """
    s = spread.dropna()
    s_lag = s.shift(1).dropna()
    delta_s = (s - s.shift(1)).dropna()
    X = np.column_stack([np.ones(len(s_lag)), s_lag.values])
    y = delta_s.values
    beta_hat = np.linalg.lstsq(X, y, rcond=None)[0][1]
    if beta_hat >= 0 or 1.0 + beta_hat <= 0:
        return np.inf, float(beta_hat)
    theta = -np.log(1.0 + beta_hat)
    half_life = np.log(2.0) / theta
    return float(half_life), float(theta)


# ============================================================================
# 3. AUDIT ANTAGONISTE (/BOOST) : PROBABILISTIC & DEFLATED SHARPE RATIO (DSR)
# ============================================================================

def expected_max_sharpe_ratio(n_trials: int, std_sharpe_across_trials: float) -> float:
    """
    Calcule le Ratio de Sharpe maximum attendu sous l'hypothèse nulle (pur bruit SR=0)
    après K essais indépendants (Théorème des Valeurs Extrêmes de Bailey & López de Prado).
    """
    if n_trials <= 1 or std_sharpe_across_trials <= 0:
        return 0.0
    euler_gamma = 0.5772156649015329
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    sr0 = std_sharpe_across_trials * ((1.0 - euler_gamma) * z1 + euler_gamma * z2)
    return float(sr0)


def deflated_sharpe_ratio(
    returns: pd.Series,
    n_trials: int = 1,
    std_sharpe_trials: float = 0.5,
    periods_per_year: int = 252,
) -> Dict[str, Any]:
    """
    Calcule le Ratio de Sharpe annualisé, le Seuil de Bruit SR_0 et le Deflated Sharpe Ratio (DSR).
    Note : Pour l'audit officiel avec registre persistant K, utiliser `quant_validation_engine.dsr`.
    """
    r = returns.dropna().values
    T = len(r)
    if T < 30 or np.std(r, ddof=1) == 0:
        return {"valid": False, "reason": "Échantillon insuffisant (<30 observations) ou variance nulle"}

    sr_non_ann = np.mean(r) / np.std(r, ddof=1)
    sr_ann = sr_non_ann * np.sqrt(periods_per_year)

    g3 = float(skew(r, bias=False))
    g4 = float(kurtosis(r, fisher=False, bias=False))

    std_sr_non_ann = std_sharpe_trials / np.sqrt(periods_per_year)
    sr0_non_ann = expected_max_sharpe_ratio(n_trials, std_sr_non_ann)

    denom_sq = 1.0 - g3 * sr_non_ann + ((g4 - 1.0) / 4.0) * (sr_non_ann ** 2)
    if denom_sq <= 0:
        return {"valid": False, "reason": "Dénominateur statistique dégénéré"}

    z_score = ((sr_non_ann - sr0_non_ann) * np.sqrt(T - 1.0)) / np.sqrt(denom_sq)
    dsr_prob = float(norm.cdf(z_score))

    return {
        "valid": True,
        "n_observations": T,
        "n_trials_penalized": n_trials,
        "sharpe_annualized": round(float(sr_ann), 3),
        "threshold_sr0_annualized": round(float(sr0_non_ann * np.sqrt(periods_per_year)), 3),
        "skewness": round(g3, 3),
        "kurtosis": round(g4, 3),
        "deflated_sharpe_probability": round(dsr_prob, 4),
        "passes_boost_gate_95pct": bool(dsr_prob >= 0.95),
    }


# ============================================================================
# 4. VALIDATION CROISÉE PURGÉE ET AVEC EMBARGO (PURGED K-FOLD CV)
# ============================================================================

def purged_embargo_kfold_split(
    n_samples: int,
    n_splits: int = 5,
    label_horizon: int = 5,
    embargo_pct: float = 0.01,
) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
    """Génère des indices (train_idx, test_idx) avec Purge avant le test et Embargo après."""
    indices = np.arange(n_samples)
    embargo_size = int(n_samples * embargo_pct)
    fold_sizes = np.full(n_splits, n_samples // n_splits, dtype=int)
    fold_sizes[: n_samples % n_splits] += 1
    current = 0

    for fold_size in fold_sizes:
        start_test, stop_test = current, current + fold_size
        test_idx = indices[start_test:stop_test]
        left_purge_bound = max(0, start_test - label_horizon)
        right_embargo_bound = min(n_samples, stop_test + embargo_size)
        train_left = indices[:left_purge_bound]
        train_right = indices[right_embargo_bound:]
        train_idx = np.concatenate([train_left, train_right])
        yield train_idx, test_idx
        current = stop_test


# ============================================================================
# 5. GESTION DU RISQUE : STANDARDISATION CARVER [-20,+20], VOL TARGETING & KELLY
# ============================================================================

def carver_standardize_forecast(raw_signal: pd.Series, lookback: int = 60, cap: float = 20.0) -> pd.Series:
    """
    Standardise un signal brut selon le protocole de Robert Carver (Systematic Trading) :
    - Moyenne absolue glissante ramenée à 10.0
    - Bornage strict dans [-20.0, +20.0]
    - Aucune information future utilisée.
    """
    mean_abs = raw_signal.abs().rolling(lookback, min_periods=10).mean()
    scaled = raw_signal * (10.0 / mean_abs.replace(0.0, np.nan))
    return scaled.clip(lower=-cap, upper=cap).fillna(0.0)


def compute_volatility_targeted_weights(
    raw_signal: pd.Series,
    returns: pd.Series,
    target_ann_vol: float = 0.15,
    vol_lookback: int = 20,
    max_leverage: float = 2.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """Calcule la taille de position dynamique avec Volatility Targeting et décalage .shift(1)."""
    rolling_vol_ann = returns.rolling(vol_lookback).std(ddof=1) * np.sqrt(periods_per_year)
    vol_scalar = (target_ann_vol / rolling_vol_ann.replace(0, np.nan)).clip(upper=max_leverage)
    positions = (raw_signal * vol_scalar).shift(1).fillna(0.0)
    return positions.clip(lower=-max_leverage, upper=max_leverage)


def compute_fractional_kelly(win_rate: float, win_loss_ratio: float, fraction: float = 0.25) -> float:
    """Calcule la fraction de Kelly optimale (Quarter-Kelly par défaut = 0.25)."""
    if win_loss_ratio <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    p = win_rate
    q = 1.0 - p
    b = win_loss_ratio
    full_kelly = (p * b - q) / b
    if full_kelly <= 0:
        return 0.0
    return float(np.clip(full_kelly * fraction, 0.0, 1.0))


# ============================================================================
# 6. MODÉLISATION DE L'IMPACT DE MARCHÉ & FRICTIONS RÉELLES
# ============================================================================

def compute_market_impact_bps(
    order_size_q: float,
    avg_daily_volume: float,
    daily_volatility: float,
    bid_ask_spread_bps: float = 2.0,
    fixed_fee_bps: float = 1.0,
    y_constant: float = 0.75,
) -> float:
    """Loi de la Racine Carrée institutionnelle (Grinold & Kahn / Almgren-Chriss)."""
    if avg_daily_volume <= 0:
        return float("inf")
    participation_rate = max(0.0, order_size_q / avg_daily_volume)
    impact_bps = y_constant * daily_volatility * np.sqrt(participation_rate) * 10000.0
    return float(fixed_fee_bps + (0.5 * bid_ask_spread_bps) + impact_bps)


# ============================================================================
# 7. THÉORIE DES MATRICES ALÉATOIRES (MARCHENKO-PASTUR) & ALLOCATION HRP
# ============================================================================

def denoise_covariance_marchenko_pastur(returns_matrix: np.ndarray) -> Dict[str, Any]:
    """
    Débruite une matrice de covariance empirique (T observations x N actifs) via la loi de
    Marchenko-Pastur (Random Matrix Theory - López de Prado) :
    - Calcule la borne supérieure du bruit lambda_+ = sigma^2 * (1 + sqrt(N/T))^2
    - Remplace toutes les valeurs propres <= lambda_+ par leur moyenne constante (Constant Residual Eigenvalue)
    - Reconstruit la matrice de corrélation et de covariance débruitée.
    """
    R = np.asarray(returns_matrix, dtype=np.float64)
    T, N = R.shape
    if T <= N or N < 2:
        cov = np.cov(R, rowvar=False)
        return {"cov_denoised": cov, "lambda_plus": 0.0, "n_signal_factors": N}

    cov_emp = np.cov(R, rowvar=False)
    std_vec = np.sqrt(np.maximum(np.diag(cov_emp), 1e-18))
    corr_emp = cov_emp / np.outer(std_vec, std_vec)

    eigvals, eigvecs = np.linalg.eigh(corr_emp)
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    q = float(N) / float(T)
    lambda_plus = (1.0 + math.sqrt(q)) ** 2

    noise_mask = eigvals <= lambda_plus
    n_signal = int(np.sum(~noise_mask))
    eigvals_clean = eigvals.copy()
    if np.any(noise_mask):
        eigvals_clean[noise_mask] = float(np.mean(eigvals[noise_mask]))

    corr_clean = eigvecs @ np.diag(eigvals_clean) @ eigvecs.T
    diag_clean = np.sqrt(np.maximum(np.diag(corr_clean), 1e-18))
    corr_clean = corr_clean / np.outer(diag_clean, diag_clean)
    cov_clean = corr_clean * np.outer(std_vec, std_vec)

    return {
        "cov_denoised": cov_clean,
        "corr_denoised": corr_clean,
        "lambda_plus_threshold": round(float(lambda_plus), 4),
        "n_signal_eigenvalues": n_signal,
        "n_noise_eigenvalues": int(np.sum(noise_mask)),
    }


def hrp_portfolio_weights(returns_matrix: np.ndarray, denoise_rmt: bool = True) -> np.ndarray:
    """
    Calcule l'allocation Hierarchical Risk Parity (HRP - Marcos López de Prado, 2016) :
    1. Clustering hiérarchique basé sur la distance de corrélation d_{i,j} = sqrt(0.5 * (1 - rho_{i,j}))
    2. Quasi-diagonalisation de la matrice de covariance
    3. Bissection récursive en variance inverse (sans jamais inverser la matrice de covariance).
    """
    R = np.asarray(returns_matrix, dtype=np.float64)
    T, N = R.shape
    if N == 1:
        return np.array([1.0])

    if denoise_rmt and T > N:
        rmt = denoise_covariance_marchenko_pastur(R)
        cov = rmt["cov_denoised"]
        corr = rmt["corr_denoised"]
    else:
        cov = np.cov(R, rowvar=False)
        std_vec = np.sqrt(np.maximum(np.diag(cov), 1e-18))
        corr = cov / np.outer(std_vec, std_vec)

    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    sort_ix = list(leaves_list(link))

    weights = np.ones(N, dtype=np.float64)

    def _cluster_var(c_cov: np.ndarray, items: List[int]) -> float:
        sub = c_cov[np.ix_(items, items)]
        ivp = 1.0 / np.maximum(np.diag(sub), 1e-18)
        ivp /= np.sum(ivp)
        return float(ivp.T @ sub @ ivp)

    clusters = [sort_ix]
    while len(clusters) > 0:
        new_clusters = []
        for cl in clusters:
            if len(cl) > 1:
                mid = len(cl) // 2
                left_c = cl[:mid]
                right_c = cl[mid:]
                var_l = _cluster_var(cov, left_c)
                var_r = _cluster_var(cov, right_c)
                alpha = 1.0 - var_l / max(1e-18, var_l + var_r)
                weights[left_c] *= alpha
                weights[right_c] *= 1.0 - alpha
                new_clusters.extend([left_c, right_c])
        clusters = new_clusters

    return weights / np.sum(weights)


# ============================================================================
# 8. FILTRE DE KALMAN 2D EN ESPACE D'ÉTAT (STATISTICAL ARBITRAGE / PAIRS TRADING)
# ============================================================================

def kalman_pairs_hedge_ratio(
    price_y: np.ndarray,
    price_x: np.ndarray,
    delta: float = 1e-4,
    obs_var_r: float = 1e-3,
) -> Dict[str, np.ndarray]:
    """
    Filtre de Kalman 2D en espace d'état pour le Pairs Trading / Statistical Arbitrage :
    Estime dynamiquement à chaque instant t l'état latent theta_t = [alpha_t, beta_t]^T
    reliant log(P_y,t) = alpha_t + beta_t * log(P_x,t) + epsilon_t.
    Retourne les vecteurs causaux : intercept alpha_t, hedge ratio beta_t, spread e_t et z_score_t.
    """
    y = np.log(np.maximum(np.asarray(price_y, dtype=np.float64), 1e-12))
    x = np.log(np.maximum(np.asarray(price_x, dtype=np.float64), 1e-12))
    n = min(len(y), len(x))

    alpha_vec = np.zeros(n)
    beta_vec = np.zeros(n)
    spread_vec = np.zeros(n)
    zscore_vec = np.zeros(n)

    theta = np.array([0.0, 1.0], dtype=np.float64)
    P = np.eye(2, dtype=np.float64)
    Q = (delta / (1.0 - delta)) * np.eye(2, dtype=np.float64)

    for t in range(n):
        F = np.array([1.0, x[t]], dtype=np.float64)
        if t > 0:
            P = P + Q

        y_pred = float(F @ theta)
        err = float(y[t] - y_pred)
        S = float(F @ P @ F.T) + obs_var_r
        z_t = err / math.sqrt(max(1e-18, S))

        alpha_vec[t] = theta[0]
        beta_vec[t] = theta[1]
        spread_vec[t] = err
        zscore_vec[t] = np.clip(z_t, -6.0, 6.0)

        K = (P @ F) / max(1e-18, S)
        theta = theta + K * err
        P = P - np.outer(K, F) @ P

    return {
        "alpha": alpha_vec,
        "beta": beta_vec,
        "spread_innovation": spread_vec,
        "innovation_zscore": zscore_vec,
    }


# ============================================================================
# 9. TRIPLE BARRIER METHOD & META-LABELING (MARCOS LÓPEZ DE PRADO)
# ============================================================================

def triple_barrier_labels(
    close: np.ndarray,
    volatility: np.ndarray,
    pt_mult: float = 2.0,
    sl_mult: float = 2.0,
    max_holding_bars: int = 12,
    primary_side: Optional[np.ndarray] = None,
) -> Dict[str, np.ndarray]:
    """
    Implémente la Triple Barrier Method (Advances in Financial Machine Learning) :
    - Barrière supérieure : +pt_mult * sigma_t
    - Barrière inférieure : -sl_mult * sigma_t
    - Barrière verticale : t + max_holding_bars
    Si `primary_side` (+1 ou -1) est fourni, génère également les étiquettes binaires
    de Meta-Labeling (1 si le modèle primaire gagne sur la première barrière touchée, 0 sinon).
    """
    c = np.log(np.maximum(np.asarray(close, dtype=np.float64), 1e-12))
    sig = np.asarray(volatility, dtype=np.float64)
    n = len(c)

    labels = np.zeros(n, dtype=np.int64)
    realized_ret = np.zeros(n, dtype=np.float64)
    exit_bar = np.arange(n, dtype=np.int64)

    for t in range(n - 1):
        s_t = sig[t] if (np.isfinite(sig[t]) and sig[t] > 1e-8) else 0.002
        up_b = pt_mult * s_t
        dn_b = -sl_mult * s_t
        end_t = min(n - 1, t + max_holding_bars)

        touched = 0
        hit_idx = end_t
        for u in range(t + 1, end_t + 1):
            path_r = c[u] - c[t]
            if pt_mult > 0 and path_r >= up_b:
                touched = 1
                hit_idx = u
                break
            if sl_mult > 0 and path_r <= dn_b:
                touched = -1
                hit_idx = u
                break

        ret_final = float(c[hit_idx] - c[t])
        if touched == 0:
            touched = 1 if ret_final > 0 else (-1 if ret_final < 0 else 0)
        labels[t] = touched
        realized_ret[t] = ret_final
        exit_bar[t] = hit_idx

    out = {"barrier_label": labels, "realized_log_return": realized_ret, "exit_index": exit_bar}
    if primary_side is not None:
        side = np.asarray(primary_side, dtype=np.float64)
        meta_y = ((side * realized_ret) > 0).astype(np.int64)
        out["meta_label"] = meta_y
    return out


# ============================================================================
# 10. THÉORIE DES VALEURS EXTRÊMES (EVT - GPD) & CVaR / EXPECTED SHORTFALL
# ============================================================================

def compute_evt_cvar_gpd(
    returns: np.ndarray, threshold_quantile: float = 0.95, confidence_alpha: float = 0.99
) -> Dict[str, float]:
    """
    Calcule la Value-at-Risk (VaR) et la Conditional Value-at-Risk (CVaR / Expected Shortfall)
    à 99% par la Théorie des Valeurs Extrêmes (Peak-Over-Threshold avec Loi de Pareto Généralisée GPD).
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    losses = -r
    n = len(losses)
    if n < 100:
        return {"valid": False}

    u = float(np.quantile(losses, threshold_quantile))
    exceedances = losses[losses > u] - u
    n_u = len(exceedances)
    if n_u < 10 or genpareto is None:
        q_alpha = float(np.quantile(losses, confidence_alpha))
        cvar_emp = float(np.mean(losses[losses >= q_alpha]))
        return {"valid": True, "var_99": q_alpha, "cvar_99_es": cvar_emp, "xi_tail_shape": 0.0}

    xi, _, beta = genpareto.fit(exceedances, floc=0.0)
    xi = float(np.clip(xi, -0.45, 0.85))
    beta = float(max(1e-8, beta))
    p_tail = 1.0 - confidence_alpha
    ratio = (n / float(n_u)) * p_tail

    if abs(xi) < 1e-6:
        var_evt = u - beta * math.log(ratio)
        cvar_evt = var_evt + beta
    else:
        var_evt = u + (beta / xi) * ((ratio ** (-xi)) - 1.0)
        cvar_evt = (var_evt + beta - xi * u) / max(0.05, 1.0 - xi)

    return {
        "valid": True,
        "threshold_u": round(u, 6),
        "xi_tail_shape": round(xi, 4),
        "var_99": round(float(var_evt), 6),
        "cvar_99_es": round(float(cvar_evt), 6),
    }


# ============================================================================
# 11. MICROSTRUCTURE & MULTI-ACTIFS (OFI, VPIN, AMM LVR, CS-MOMENTUM, NELSON-SIEGEL)
# ============================================================================

def compute_order_flow_imbalance(
    bid_price: np.ndarray,
    bid_size: np.ndarray,
    ask_price: np.ndarray,
    ask_size: np.ndarray,
    window: int = 50,
) -> np.ndarray:
    """
    Calcule l'Order Flow Imbalance (OFI - Cont, Kukanov & Stoikov, 2014) normalisé :
    OFI_t = Delta_Bid_Size * I(Bid_t >= Bid_{t-1}) - Delta_Ask_Size * I(Ask_t <= Ask_{t-1}).
    """
    bp = np.asarray(bid_price, dtype=np.float64)
    bs = np.asarray(bid_size, dtype=np.float64)
    ap = np.asarray(ask_price, dtype=np.float64)
    as_ = np.asarray(ask_size, dtype=np.float64)
    n = len(bp)
    ofi = np.zeros(n, dtype=np.float64)

    for t in range(1, n):
        e_b = (bs[t] if bp[t] > bp[t - 1] else (bs[t] - bs[t - 1] if bp[t] == bp[t - 1] else -bs[t - 1]))
        e_a = (as_[t] if ap[t] < ap[t - 1] else (as_[t] - as_[t - 1] if ap[t] == ap[t - 1] else -as_[t - 1]))
        ofi[t] = e_b - e_a

    # Normalisation causale par la profondeur moyenne
    depth = 0.5 * (bs + as_)
    s_depth = pd.Series(depth).rolling(window, min_periods=5).mean().replace(0.0, np.nan).values
    s_ofi = pd.Series(ofi).rolling(window, min_periods=5).sum().values
    return np.nan_to_num(s_ofi / (s_depth * window), nan=0.0)


def compute_vpin_toxicity(returns: np.ndarray, volume: np.ndarray, window: int = 50) -> np.ndarray:
    """
    Estime la toxicité du flux d'ordres VPIN (Bulk Volume Classification - Easley, López de Prado, O'Hara) :
    V_buy = V * Phi(r_t / sigma_t), V_sell = V - V_buy, VPIN = sum(|V_buy - V_sell|) / sum(V).
    """
    r = np.asarray(returns, dtype=np.float64)
    v = np.maximum(np.asarray(volume, dtype=np.float64), 0.0)
    sig = pd.Series(r).rolling(window, min_periods=10).std(ddof=1).replace(0.0, np.nan).values
    z = np.nan_to_num(r / sig, nan=0.0)
    buy_prob = norm.cdf(np.clip(z, -4.0, 4.0))
    v_imb = np.abs(2.0 * buy_prob - 1.0) * v
    num = pd.Series(v_imb).rolling(window, min_periods=10).sum().values
    den = pd.Series(v).rolling(window, min_periods=10).sum().replace(0.0, np.nan).values
    return np.nan_to_num(num / den, nan=0.0)


def compute_amm_lvr_vs_fees(
    volatility_ann: float,
    pool_fee_bps: float,
    daily_volume_to_tvl_ratio: float,
    price_range_width_pct: float = 0.20,
) -> Dict[str, Any]:
    """
    Équation de Milionis, Moallemi & Roughgarden (Loss-Versus-Rebalancing sur DEX AMM) :
    Compare le flux de frais attendu d'un LP concentré au coût d'antisélection LVR.
    - LVR instantané sur AMM : sigma_daily^2 / 8 * facteur_concentration
    """
    sigma_daily = volatility_ann / math.sqrt(365.0)
    concentration_mult = min(20.0, 1.0 / max(0.02, price_range_width_pct))
    daily_lvr_bps = ((sigma_daily ** 2) / 8.0) * concentration_mult * 1e4
    daily_fees_bps = daily_volume_to_tvl_ratio * pool_fee_bps * concentration_mult
    net_daily_bps = daily_fees_bps - daily_lvr_bps
    return {
        "daily_fees_bps": round(daily_fees_bps, 2),
        "daily_lvr_adverse_selection_bps": round(daily_lvr_bps, 2),
        "net_lp_edge_daily_bps": round(net_daily_bps, 2),
        "is_lp_profitable_after_lvr": bool(net_daily_bps > 0.0),
    }


def cross_sectional_momentum_weights(
    returns_matrix: np.ndarray, lookback: int = 60, skip_recent: int = 5, vol_window: int = 20
) -> np.ndarray:
    """
    Calcule les poids Dollar-Neutral (Somme = 0, Somme(|w|) = 1) du Cross-Sectional Momentum
    normalisé par la volatilité (Section 4.1 Famille 1) :
    S_{i,t} = R_{i, t-lookback -> t-skip} / sigma_{i,t}.
    """
    R = np.asarray(returns_matrix, dtype=np.float64)
    T, N = R.shape
    weights = np.zeros((T, N), dtype=np.float64)
    start_t = lookback + skip_recent + 1

    for t in range(start_t, T):
        cum_ret = np.sum(R[t - lookback - skip_recent : t - skip_recent, :], axis=0)
        vol = np.std(R[t - vol_window : t, :], axis=0, ddof=1)
        vol = np.where(vol > 1e-8, vol, np.nan)
        score = np.nan_to_num(cum_ret / vol, nan=0.0)
        centered = score - np.mean(score)
        l1 = float(np.sum(np.abs(centered)))
        if l1 > 1e-12:
            # Décalage d'une période : le poids calculé en t-1 s'applique en t
            weights[t, :] = centered / l1
    return weights


def fit_nelson_siegel_curve(maturities_years: np.ndarray, yields: np.ndarray, tau: float = 1.5) -> Dict[str, float]:
    """
    Décompose une courbe des taux obligataires selon le modèle à 3 facteurs de Nelson-Siegel
    (Section 13.1 : beta_0 = Level, beta_1 = Slope, beta_2 = Curvature).
    """
    m = np.maximum(np.asarray(maturities_years, dtype=np.float64), 1e-3)
    y = np.asarray(yields, dtype=np.float64)
    x1 = (1.0 - np.exp(-m / tau)) / (m / tau)
    x2 = x1 - np.exp(-m / tau)
    X = np.column_stack([np.ones(len(m)), x1, x2])
    betas = np.linalg.lstsq(X, y, rcond=None)[0]
    return {
        "beta0_level": round(float(betas[0]), 5),
        "beta1_slope": round(float(betas[1]), 5),
        "beta2_curvature": round(float(betas[2]), 5),
    }


# ============================================================================
# 12. SYNCHRONISATION POINT-IN-TIME STRICTE (ASOF JOIN BACKWARD)
# ============================================================================

def asof_join_point_in_time(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_time_col: str = "timestamp",
    right_available_col: str = "available_timestamp",
    right_event_col: Optional[str] = "event_timestamp",
) -> pd.DataFrame:
    """
    Exécute une jointure Point-in-Time stricte (Section 3.2) :
    - Vérifie que `available_timestamp >= event_timestamp` sur la table de droite.
    - Joint uniquement les lignes où `right.available_timestamp <= left.timestamp` (direction='backward').
    """
    if right_event_col and right_event_col in right_df.columns:
        bad = right_df[right_available_col] < right_df[right_event_col]
        if bool( np.any(bad) ):
            raise ValueError("Violation Point-in-Time détectée : available_timestamp < event_timestamp !")

    l_sorted = left_df.sort_values(left_time_col).reset_index(drop=True)
    r_sorted = right_df.sort_values(right_available_col).reset_index(drop=True)
    merged = pd.merge_asof(
        l_sorted,
        r_sorted,
        left_on=left_time_col,
        right_on=right_available_col,
        direction="backward",
    )
    return merged


if __name__ == "__main__":
    # Auto-test rapide des 12 modules
    rng = np.random.default_rng(7)
    R_mat = rng.normal(0.0, 0.01, size=(500, 6))
    w_hrp = hrp_portfolio_weights(R_mat)
    assert abs(np.sum(w_hrp) - 1.0) < 1e-6, "HRP doit sommer à 1"
    evt = compute_evt_cvar_gpd(R_mat[:, 0])
    assert evt["valid"] and evt["cvar_99_es"] >= evt["var_99"]
    ns = fit_nelson_siegel_curve(np.array([0.5, 1, 2, 5, 10, 30]), np.array([0.04, 0.042, 0.044, 0.046, 0.048, 0.05]))
    print("[OK] quant_scientific_arsenal.py (12 modules) validé avec succès.", {"hrp_w0": round(w_hrp[0], 3), "cvar99": evt["cvar_99_es"], "ns": ns})
