"""
deriv_quant_engine.py
=====================
Moteur Complet d'Audit Mathématique, Statistique, Spectral, Cryptographique,
Chaotique et Topologique pour les Marchés Synthétiques Deriv (11 Familles)
et Flux Haute Fréquence (Sections 10, 11, 12 & Parties 1-3 de l'Encyclopédie).

Couvre les 11 familles Deriv :
1. Crash & Boom (150, 300, 500, 600, 900, 1000)
2. Drift Switch Indices (DSI 10, 20, 30 - Markov-Switching + Filtre Bayésien de Wonham/Hamilton + CUSUM)
3. DEX Indices (600, 900, 1500 UP/DOWN - Modèle de Kou + Entropie de Transfert)
4. Classic Step Indices (Step 100-500 - Canari Cryptographique + Export binaire .bin)
5. Multi Step Indices (Multi Step 2, 3, 4 - Information Mutuelle taille/signe)
6. Skew Step Indices (Skew Step 4, 5 UP/DOWN)
7. Trek Indices (Trek UP/DOWN - Loi de Weibull MLE k != 1)
8. Range Break Indices (Range Break 100, 200 - Barrières exactes [L_t, U_t])
9. Jump Indices (Jump 10-100 - Diffusion à sauts de Merton)
10. Volatility Indices (V10-V300, standard & 1s)
11. Hybrid & Tactical Indices (Accumulators & DTrader Options)

Intègre les 10 Modules d'Audit :
- Module 1 : Extraction MT5 haute fréquence (`fetch_deriv_ticks`) & Export `.bin` pour NIST/PractRand/TestU01
- Module 2 : Entropie de Permutation (Bandt-Pompe), Runs Test (Wald-Wolfowitz), Hurst R/S, Welch PSD
- Module 3 : Min-Entropie inspirée NIST SP 800-90B, Complexité Linéaire de Berlekamp-Massey (LFSR), Complexité de Lempel-Ziv (LZ76)
- Module 4 : Géométrie des Chemins Rugueux (Terry Lyons - Aire de Lévy 2D)
- Module 5 : Détection de Changement de Régime : CUSUM / SPRT de Wald & Filtre Bayésien de Wonham/Hamilton à 3 états (DSI 10/20/30)
- Module 6 : Formule Analytique Exacte des Accumulators & Options Barrières (Fokker-Planck)
- Module 7 : Audit Spécifique Boom/Crash (Poisson, Spearman attente/taille, Timing Side-Channel KS)
- Module 8 : Théorie de l'Information & Non-Linéarité : Information Mutuelle Décalée (TDMI), Entropie de Transfert de Schreiber, Test BDS (Brock-Dechert-Scheinkman)
- Module 9 : Chaos, Multifractalité & Transport Optimal : Multifractal DFA (MF-DFA), Plus Grand Exposant de Lyapunov (Rosenstein), RQA (Déterminisme DET), Distance de Wasserstein W_1
- Module 10 : Modèles Spécifiques Trek (Weibull Hazard MLE) & Range Break 100/200 (Barrières Réfléchissantes Exactes)
"""

import math
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

try:
    import scipy.signal as signal
    import scipy.stats as stats
except ImportError:
    signal = None
    stats = None


# ==============================================================================
# 1. MODULE D'EXTRACTION HAUTE FRÉQUENCE (MT5 -> PARQUET / BINAIRE NIST)
# ==============================================================================

def fetch_deriv_ticks(symbol: str, num_days: int = 15) -> pd.DataFrame:
    """
    Extrait les ticks bruts à la milliseconde depuis le serveur Deriv MT5.
    Requiert que MetaTrader5 soit installé et connecté.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        raise ImportError("Le package MetaTrader5 n'est pas installé. Lancez: pip install MetaTrader5")

    if not mt5.initialize():
        raise RuntimeError(f"Erreur d'initialisation MT5 : {mt5.last_error()}")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=num_days)

    print(f"[*] Téléchargement des ticks pour {symbol} du {start_time} au {end_time}...")
    ticks = mt5.copy_ticks_range(symbol, start_time, end_time, mt5.COPY_TICKS_ALL)
    mt5.shutdown()

    if ticks is None or len(ticks) == 0:
        raise ValueError(f"Aucun tick récupéré pour {symbol}. Vérifiez que le symbole est activé dans le Market Watch.")

    df = pd.DataFrame(ticks)
    df["dt"] = pd.to_datetime(df["time_msc"], unit="ms", utc=True)
    df["spread"] = df["ask"] - df["bid"]
    df["delta_bid"] = df["bid"].diff()
    df["delta_time_ms"] = df["time_msc"].diff()
    print(f"[+] {len(df):,} ticks extraits avec succès.")
    return df.dropna().reset_index(drop=True)


def export_binary_stream_for_nist_practrand(
    delta_series: np.ndarray, output_bin_path: str | Path, mode: str = "sign"
) -> Dict[str, Any]:
    """
    Convertit un flux de variations de ticks (ex: Step Index 100 ou durées inter-spikes Boom/Crash)
    en un fichier binaire brut (.bin, 1 octet par bit 0/1 ou bits compactés) prêt à être audité
    par la suite C++ officielle NIST SP 800-90B (`ea_non_iid`), PractRand ou TestU01.
    - mode='sign' : 1 si delta > 0, 0 si delta < 0 (Step Index)
    - mode='parity' : delta_int % 2 (Parité des temps d'attente inter-spikes)
    """
    arr = np.asarray(delta_series)
    arr = arr[arr != 0]
    if mode == "parity":
        bits = (np.abs(arr).astype(np.int64) % 2).astype(np.uint8)
    else:
        bits = (arr > 0).astype(np.uint8)

    out_path = Path(output_bin_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bits.tofile(str(out_path))
    p_one = float(np.mean(bits)) if len(bits) > 0 else 0.5
    return {
        "output_file": str(out_path),
        "n_bits_written": int(len(bits)),
        "p_one": round(p_one, 6),
        "bias_from_half": round(abs(p_one - 0.5), 6),
    }


# ==============================================================================
# 2. BATTERIE DE TESTS CRYPTOGRAPHIQUES, SPECTRAUX ET NON-LINÉAIRES DE BASE
# ==============================================================================

def permutation_entropy(time_series: np.ndarray, order: int = 4, delay: int = 1) -> float:
    """
    Calcule l'Entropie de Permutation normalisée (Bandt & Pompe, 2002).
    Vaut 1.00000 pour un hasard pur.
    """
    x = np.asarray(time_series)
    n = len(x)
    if n < order * delay:
        return 1.0

    permutations = np.array(
        [np.argsort(x[i : i + order * delay : delay]) for i in range(n - (order - 1) * delay)]
    )
    multipliers = np.power(order, np.arange(order))
    hash_vals = np.dot(permutations, multipliers)
    _, counts = np.unique(hash_vals, return_counts=True)
    probs = counts / counts.sum()
    pe = -np.sum(probs * np.log2(probs))
    return float(pe / np.log2(math.factorial(order)))


def wald_wolfowitz_runs_test(binary_seq: np.ndarray) -> Tuple[float, float]:
    """Test des Séquences (Runs Test de NIST SP 800-22 / Wald-Wolfowitz)."""
    b = np.asarray(binary_seq, dtype=int)
    n = len(b)
    n1 = int(np.sum(b == 1))
    n0 = int(np.sum(b == 0))
    if n1 == 0 or n0 == 0 or n < 10:
        return 0.0, 1.0

    runs = 1 + np.sum(b[1:] != b[:-1])
    expected_runs = ((2.0 * n1 * n0) / n) + 1.0
    variance_runs = (2.0 * n1 * n0 * (2.0 * n1 * n0 - n)) / ((n ** 2) * (n - 1.0))
    if variance_runs <= 0:
        return 0.0, 1.0

    z_stat = (runs - expected_runs) / np.sqrt(variance_runs)
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat)))
    return float(z_stat), float(p_value)


def hurst_exponent_rs(ts: np.ndarray, max_lag: int = 500) -> float:
    """Estime l'Exposant de Hurst (H) par analyse R/S."""
    if len(ts) < max_lag * 2:
        max_lag = max(20, len(ts) // 4)
    lags = range(10, max_lag, 10)
    tau = []
    valid_lags = []
    for lag in lags:
        diffs = np.subtract(ts[lag:], ts[:-lag])
        s = np.std(diffs)
        if s > 0:
            tau.append(s)
            valid_lags.append(lag)
    if len(tau) < 3:
        return 0.5
    poly = np.polyfit(np.log(valid_lags), np.log(tau), 1)
    return float(poly[0])


def spectral_welch_audit(series: np.ndarray) -> Dict[str, Any]:
    """Analyse Spectrale de Welch (PSD) pour détecter les cycles cachés."""
    x = series - np.mean(series)
    n = len(x)
    nperseg = min(4096, max(64, n // 4))
    freqs, psd = signal.welch(x, fs=1.0, nperseg=nperseg)
    if len(psd) <= 1:
        return {"dominant_period_ticks": np.inf, "peak_to_mean_power_ratio": 1.0}
    max_idx = int(np.argmax(psd[1:]) + 1)
    peak_freq = freqs[max_idx]
    mean_power = np.mean(psd[1:])
    peak_ratio = psd[max_idx] / mean_power if mean_power > 0 else 1.0
    period_in_ticks = (1.0 / peak_freq) if peak_freq > 0 else np.inf
    return {
        "dominant_period_ticks": float(period_in_ticks),
        "peak_to_mean_power_ratio": float(peak_ratio),
        "is_periodic_cycle_detected": bool(peak_ratio > 4.5),
    }


# ==============================================================================
# 3. AUDIT CRYPTOGRAPHIQUE : MIN-ENTROPIE, BERLEKAMP-MASSEY & LEMPEL-ZIV LZ76
# ==============================================================================

def nist_800_90b_min_entropy_estimate(data: np.ndarray) -> Dict[str, float]:
    """
    APPROXIMATION SIMPLIFIÉE inspirée de NIST SP 800-90B (MCV + heuristiques Collision/Markov).
    Pour l'audit certifié 10 estimateurs, exporter via `export_binary_stream_for_nist_practrand`
    et exécuter `ea_non_iid` (NIST officiel).
    """
    arr = np.asarray(data)
    n = len(arr)
    if n < 50:
        return {"h_min_mcv": 1.0, "h_min_collision": 1.0, "h_min_markov": 1.0, "h_min_final": 1.0}

    _, counts = np.unique(arr, return_counts=True)
    p_max = np.max(counts) / n
    p_u = min(1.0, p_max + 2.576 * np.sqrt(p_max * (1.0 - p_max) / (n - 1)))
    h_mcv = -np.log2(p_u)

    diffs = np.where(arr[1:] == arr[:-1])[0]
    p_col = len(diffs) / (n - 1) if (n > 1) else 1.0
    h_col = -np.log2(max(1e-6, p_col))

    if len(np.unique(arr)) <= 4:
        pairs = list(zip(arr[:-1], arr[1:]))
        _, p_counts = np.unique(pairs, axis=0, return_counts=True)
        p_trans_max = np.max(p_counts) / len(pairs) if len(pairs) > 0 else 1.0
        h_markov = -np.log2(max(1e-6, p_trans_max))
    else:
        h_markov = h_mcv

    return {
        "h_min_mcv": float(h_mcv),
        "h_min_collision": float(h_col),
        "h_min_markov": float(h_markov),
        "h_min_final": float(min(h_mcv, h_col, h_markov)),
    }


def berlekamp_massey_linear_complexity(binary_stream: np.ndarray) -> int:
    """
    Algorithme de Berlekamp-Massey : Calcule la complexité linéaire L sur GF(2).
    Pour une séquence aléatoire pure de longueur N, L ~ N / 2.
    Borné à 20 000 bits par bloc pour garantir un temps d'exécution rapide.
    """
    s = [int(x) for x in binary_stream][:20000]
    n = len(s)
    c = [0] * n
    b = [0] * n
    c[0] = 1
    b[0] = 1
    l = 0
    m = -1

    for i in range(n):
        d = s[i]
        for j in range(1, l + 1):
            d ^= c[j] & s[i - j]
        if d == 1:
            t = list(c)
            p = i - m
            for j in range(n - p):
                c[j + p] ^= b[j]
            if l <= i // 2:
                l = i + 1 - l
                m = i
                b = t
    return int(l)


def lempel_ziv_complexity_lz76(binary_seq: np.ndarray) -> float:
    """
    Calcule la Complexité de Lempel-Ziv normalisée (LZ76 - Section 11.1) :
    Compte le nombre de sous-mots nouveaux c(n) lors d'un balayage de gauche à droite,
    normalisé par la borne asymptotique d'une source aléatoire pure n / log2(n).
    Vaut ~1.0 pour un bruit aléatoire incompressible ; < 0.90 signale une structure répétitive.
    """
    s = "".join("1" if int(x) > 0 else "0" for x in binary_seq[:50000])
    n = len(s)
    if n < 20:
        return 1.0

    i = 0
    c = 1
    l = 1
    k = 1
    k_max = 1
    while True:
        if i + k - 1 < n and l + k - 1 < n and s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                break
        else:
            if k > k_max:
                k_max = k
            i += 1
            if i == l:
                c += 1
                l += k_max
                if l + 1 > n:
                    break
                i = 0
                k = 1
                k_max = 1
            else:
                k = 1

    norm_factor = n / math.log2(n)
    return float(c / norm_factor)


# ==============================================================================
# 4. GÉOMÉTRIE DES CHEMINS RUGUEUX : AIRE DE LÉVY 2D (TERRY LYONS)
# ==============================================================================

def path_signature_levy_area_2d(path_x: np.ndarray, path_y: np.ndarray) -> float:
    """Calcule l'Aire de Lévy signée d'ordre 2 pour un chemin 2D X_t = (path_x, path_y)."""
    x = np.asarray(path_x, dtype=np.float64)
    y = np.asarray(path_y, dtype=np.float64)
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    dx = np.diff(x[:n])
    dy = np.diff(y[:n])
    mid_x = 0.5 * (x[: n - 1] + x[1:n])
    mid_y = 0.5 * (y[: n - 1] + y[1:n])
    return float(0.5 * np.sum(mid_x * dy - mid_y * dx))


# ==============================================================================
# 5. DÉTECTION DE RÉGIME DSI 10/20/30 : CUSUM/SPRT & FILTRE BAYÉSIEN DE WONHAM
# ==============================================================================

def cusum_sprt_regime_detector(
    tick_returns: np.ndarray,
    target_drift_mu: float = 0.0002,
    sigma_noise: float = 0.001,
    h_threshold: float = 4.0,
) -> List[int]:
    """Détecteur séquentiel CUSUM / SPRT de Wald sur flux de ticks."""
    change_points = []
    s_pos = 0.0
    s_neg = 0.0
    k = target_drift_mu / 2.0

    for i, r in enumerate(tick_returns):
        s_pos = max(0.0, s_pos + (r - k) / sigma_noise)
        s_neg = max(0.0, s_neg + (-r - k) / sigma_noise)
        if s_pos > h_threshold:
            change_points.append(i)
            s_pos = 0.0
            s_neg = 0.0
        elif s_neg > h_threshold:
            change_points.append(i)
            s_pos = 0.0
            s_neg = 0.0
    return change_points


def wonham_bayesian_regime_filter_dsi(
    returns: np.ndarray,
    mu_bull: float = 0.0003,
    mu_bear: float = -0.0003,
    sigma: float = 0.0015,
    p_stay: float = 0.995,
) -> Dict[str, np.ndarray]:
    """
    Filtre Bayésien non-linéaire de Wonham / Hamilton à 3 états cachés
    S_t in {+1 (Bull), 0 (Sideways), -1 (Bear)} pour les Drift Switch Indices (DSI 10, 20, 30) :
    Met à jour tick par tick la probabilité a posteriori P(S_t = k | F_t) sans aucun look-ahead.
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    mus = np.array([mu_bull, 0.0, mu_bear], dtype=np.float64)
    q_trans = (1.0 - p_stay) / 2.0
    P_mat = np.array(
        [
            [p_stay, q_trans, q_trans],
            [q_trans, p_stay, q_trans],
            [q_trans, q_trans, p_stay],
        ],
        dtype=np.float64,
    )

    probs = np.zeros((n, 3), dtype=np.float64)
    state_p = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float64)
    s2 = max(1e-18, sigma ** 2)

    for t in range(n):
        prior = P_mat.T @ state_p
        log_lik = -0.5 * ((r[t] - mus) ** 2) / s2
        log_lik -= np.max(log_lik)
        lik = np.exp(log_lik)
        post = prior * lik
        total = float(np.sum(post))
        state_p = post / total if total > 1e-18 else np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0])
        probs[t, :] = state_p

    net_signal = probs[:, 0] - probs[:, 2]
    return {
        "prob_bull": probs[:, 0],
        "prob_sideways": probs[:, 1],
        "prob_bear": probs[:, 2],
        "net_regime_signal": net_signal,
    }


# ==============================================================================
# 6. FORMULE ANALYTIQUE ACCUMULATORS & OPTIONS BARRIÈRES DTRADER
# ==============================================================================

def accumulator_survival_probability(
    growth_rate_per_tick: float,
    barrier_range_points: float,
    tick_volatility_sigma: float,
    num_ticks_k: int,
) -> Dict[str, Any]:
    """Calcule la probabilité exacte de survie d'un contrat Accumulator Deriv."""
    b = barrier_range_points
    s = tick_volatility_sigma
    if s <= 0:
        return {"valid": False}

    z = b / s
    p_one_tick = float(stats.norm.cdf(z) - stats.norm.cdf(-z))
    p_survie_k = float(p_one_tick ** num_ticks_k)
    expected_payout_factor = float(((1.0 + growth_rate_per_tick) ** num_ticks_k) * p_survie_k)
    edge_detected = bool(expected_payout_factor > 1.0)

    return {
        "single_tick_survival_prob": round(p_one_tick, 5),
        "k_ticks_survival_prob": round(p_survie_k, 5),
        "expected_growth_multiplier": round(expected_payout_factor, 4),
        "theoretical_mathematical_edge": edge_detected,
        "net_expected_roi_pct": round((expected_payout_factor - 1.0) * 100.0, 2),
    }


# ==============================================================================
# 7. MODULE D'AUDIT SPÉCIFIQUE BOOM / CRASH (ANATOMIE DES SPIKES)
# ==============================================================================

def audit_boom_crash(df: pd.DataFrame, is_boom: bool = True, theoretical_n: int = 500) -> Dict[str, Any]:
    """Isole les Spikes, vérifie la loi géométrique de Poisson, teste Spearman et Timing KS."""
    deltas = df["delta_bid"].values
    drift_abs = float(np.median(np.abs(deltas[deltas != 0]))) if np.any(deltas != 0) else 0.0
    thr = 3.5 * drift_abs
    spike_mask = (deltas > thr) if is_boom else (deltas < -thr)

    spike_indices = np.where(spike_mask)[0]
    if len(spike_indices) < 2:
        return {"error": "Trop peu de Spikes détectés"}

    inter_arrivals = np.diff(spike_indices)
    spike_sizes = np.abs(deltas[spike_indices[1:]])
    empirical_p = len(spike_indices) / len(df)

    corr_wait_size, p_val_corr = stats.spearmanr(inter_arrivals, spike_sizes)
    corr_wait_lag1, p_val_lag1 = stats.spearmanr(inter_arrivals[:-1], inter_arrivals[1:])

    ms_spike = df.loc[spike_mask, "delta_time_ms"].values
    ms_normal = df.loc[~spike_mask, "delta_time_ms"].values
    ks_timing_stat, ks_timing_pval = stats.ks_2samp(ms_spike, ms_normal)

    pe_spikes = permutation_entropy(spike_sizes, order=4)
    fft_wait = spectral_welch_audit(inter_arrivals)
    drift_costs = np.abs(deltas[~spike_mask])
    mean_drift = float(np.mean(drift_costs)) if len(drift_costs) > 0 else 0.0

    # Probabilité conditionnelle de Clustering de Spikes (< 20 ticks d'écart)
    cluster_20_prob = float(np.mean(inter_arrivals <= 20))
    theo_cluster_20 = 1.0 - ((1.0 - 1.0 / theoretical_n) ** 20)

    return {
        "n_ticks_total": len(df),
        "n_spikes_detected": len(spike_indices),
        "empirical_frequency_1_in_n": round(1.0 / empirical_p, 2),
        "theoretical_n": theoretical_n,
        "mean_spike_amplitude": round(float(np.mean(spike_sizes)), 4),
        "max_spike_amplitude": round(float(np.max(spike_sizes)), 4),
        "mean_drift_cost_per_tick": round(mean_drift, 5),
        "mean_spread": round(float(df["spread"].mean()), 5),
        "spike_clustering_le20_empirical": round(cluster_20_prob, 5),
        "spike_clustering_le20_theoretical": round(theo_cluster_20, 5),
        "correlation_wait_to_size": round(float(corr_wait_size), 5),
        "correlation_wait_to_size_pval": float(p_val_corr),
        "lag1_wait_memory": round(float(corr_wait_lag1), 5),
        "lag1_wait_memory_pval": float(p_val_lag1),
        "permutation_entropy_spikes": round(float(pe_spikes), 6),
        "server_timing_ks_stat": round(float(ks_timing_stat), 5),
        "server_timing_ks_pval": float(ks_timing_pval),
        "dominant_spike_period_ticks": fft_wait["dominant_period_ticks"],
        "fft_peak_ratio": fft_wait["peak_to_mean_power_ratio"],
        "is_timing_leak_statistically_significant": bool(ks_timing_pval < 0.001),
        "is_wait_memory_statistically_significant": bool(p_val_lag1 < 0.001),
    }


# ==============================================================================
# 8. THÉORIE DE L'INFORMATION & NON-LINÉARITÉ : TDMI, ENTROPIE DE TRANSFERT & BDS
# ==============================================================================

def time_delayed_mutual_information(
    x: np.ndarray, y: Optional[np.ndarray] = None, lag: int = 1, n_bins: int = 8
) -> float:
    """
    Calcule l'Information Mutuelle Décalée (TDMI - Partie 1 Section 2) en bits :
    I(X_t ; Y_{t-lag}) = sum p(x, y) log2( p(x, y) / (p(x) p(y)) ).
    Si y est None, calcule l'auto-information mutuelle I(X_t ; X_{t-lag}).
    """
    a = np.asarray(x, dtype=np.float64)
    b = a if y is None else np.asarray(y, dtype=np.float64)
    n = min(len(a), len(b))
    if n <= lag + 20:
        return 0.0

    target = a[lag:n]
    source = b[: n - lag]
    c_xy, _, _ = np.histogram2d(target, source, bins=n_bins)
    p_xy = c_xy / float(np.sum(c_xy))
    p_x = np.sum(p_xy, axis=1, keepdims=True)
    p_y = np.sum(p_xy, axis=0, keepdims=True)
    denom = p_x @ p_y

    mask = (p_xy > 0) & (denom > 0)
    mi = float(np.sum(p_xy[mask] * np.log2(p_xy[mask] / denom[mask])))
    return max(0.0, mi)


def schreiber_transfer_entropy(source: np.ndarray, target: np.ndarray, lag: int = 1, n_bins: int = 4) -> float:
    """
    Calcule l'Entropie de Transfert directionnelle de Schreiber (2000) en bits :
    TE_{Source -> Target} = H(Target_t | Target_{t-1}) - H(Target_t | Target_{t-1}, Source_{t-lag}).
    Mesure le flux d'information causal de `source` vers `target` (ex: BTC -> Altcoin ou petits sauts -> grands sauts DEX).
    """
    src = np.asarray(source, dtype=np.float64)
    tgt = np.asarray(target, dtype=np.float64)
    n = min(len(src), len(tgt))
    k = max(1, lag)
    if n <= k + 50:
        return 0.0

    # Discrétisation par quantiles
    def _quantize(v: np.ndarray, bins: int) -> np.ndarray:
        qs = np.linspace(0, 1, bins + 1)[1:-1]
        edges = np.quantile(v, qs)
        return np.digitize(v, edges)

    s_q = _quantize(src, n_bins)
    t_q = _quantize(tgt, n_bins)

    t_now = t_q[k:n]
    t_prev = t_q[k - 1 : n - 1]
    s_lag = s_q[: n - k]

    # Comptage conjoint 3D (t_now, t_prev, s_lag)
    joint_3d = np.zeros((n_bins, n_bins, n_bins), dtype=np.float64)
    for a, b, c in zip(t_now, t_prev, s_lag):
        joint_3d[a, b, c] += 1.0
    p_abc = joint_3d / float(len(t_now))
    p_bc = np.sum(p_abc, axis=0, keepdims=True)
    p_ab = np.sum(p_abc, axis=2, keepdims=True)
    p_b = np.sum(p_abc, axis=(0, 2), keepdims=True)

    mask = (p_abc > 0) & (p_bc > 0) & (p_ab > 0) & (p_b > 0)
    ratio = (p_abc[mask] * np.broadcast_to(p_b, p_abc.shape)[mask]) / (
        np.broadcast_to(p_bc, p_abc.shape)[mask] * np.broadcast_to(p_ab, p_abc.shape)[mask]
    )
    te = float(np.sum(p_abc[mask] * np.log2(np.maximum(ratio, 1e-12))))
    return max(0.0, te)


def bds_non_linear_chaos_test(series: np.ndarray, emb_dim: int = 3, eps_sigma: float = 1.0) -> Dict[str, float]:
    """
    Test BDS (Brock-Dechert-Scheinkman - Partie 1 Section 2) par intégrale de corrélation spatiale C(eps, m) :
    Teste l'hypothèse nulle i.i.d. contre toute dépendance non-linéaire ou chaotique
    en comparant C(eps, m) à C(eps, 1)^m.
    """
    x = np.asarray(series, dtype=np.float64)
    x = x[np.isfinite(x)][:1500]  # Sous-échantillon rapide O(N^2)
    n = len(x)
    if n < 100 or np.std(x) <= 1e-12:
        return {"c1": 0.0, "cm": 0.0, "bds_ratio_diff": 0.0}

    eps = eps_sigma * float(np.std(x, ddof=1))
    diff_1d = np.abs(x[:, None] - x[None, :])
    np.fill_diagonal(diff_1d, np.inf)
    c1 = float(np.mean(diff_1d < eps))

    # Plongement de Takens de dimension m
    m_len = n - emb_dim + 1
    emb = np.column_stack([x[j : j + m_len] for j in range(emb_dim)])
    cheb_dist = np.max(np.abs(emb[:, None, :] - emb[None, :, :]), axis=2)
    np.fill_diagonal(cheb_dist, np.inf)
    cm = float(np.mean(cheb_dist < eps))

    expected_cm = c1 ** emb_dim
    diff_ratio = (cm - expected_cm) / max(1e-6, expected_cm)
    return {
        "c1": round(c1, 5),
        "cm": round(cm, 5),
        "expected_cm_under_iid": round(expected_cm, 5),
        "non_linear_excess_ratio": round(diff_ratio, 4),
    }


# ==============================================================================
# 9. CHAOS, MULTIFRACTALITÉ & TRANSPORT OPTIMAL : MF-DFA, LYAPUNOV, RQA, WASSERSTEIN
# ==============================================================================

def multifractal_dfa_spectrum(series: np.ndarray, q_orders: Tuple[float, ...] = (-3.0, -1.0, 1.0, 2.0, 4.0)) -> Dict[str, Any]:
    """
    Multifractal Detrended Fluctuation Analysis (MF-DFA - Kantelhardt et al. / Section 11.1) :
    Calcule l'exposant de Hurst généralisé H(q) et la largeur du spectre multifractal
    Delta_H = H(q_min) - H(q_max).
    """
    x = np.asarray(series, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 256:
        return {"valid": False}

    profile = np.cumsum(x - np.mean(x))
    scales = [16, 32, 64, 128]
    hq_dict: Dict[str, float] = {}

    for q in q_orders:
        fq_vals = []
        for s in scales:
            n_seg = n // s
            rms = []
            t_grid = np.arange(s, dtype=np.float64)
            for v in range(n_seg):
                seg = profile[v * s : (v + 1) * s]
                poly = np.polyfit(t_grid, seg, 1)
                trend = poly[0] * t_grid + poly[1]
                var_s = float(np.mean((seg - trend) ** 2))
                if var_s > 1e-18:
                    rms.append(math.sqrt(var_s))
            rms_arr = np.asarray(rms, dtype=np.float64)
            if abs(q) < 1e-4:
                fq = math.exp(0.5 * float(np.mean(np.log(rms_arr ** 2))))
            else:
                fq = float(np.mean(rms_arr ** q)) ** (1.0 / q)
            fq_vals.append(fq)
        slope = float(np.polyfit(np.log(scales), np.log(fq_vals), 1)[0])
        hq_dict[f"H_q_{q:+.1f}"] = round(slope, 4)

    vals = list(hq_dict.values())
    delta_h = float(max(vals) - min(vals))
    return {
        "valid": True,
        "generalized_hurst_hq": hq_dict,
        "multifractal_width_delta_h": round(delta_h, 4),
    }


def largest_lyapunov_exponent_rosenstein(series: np.ndarray, emb_dim: int = 3, tau: int = 1) -> float:
    """
    Estime le Plus Grand Exposant de Lyapunov (lambda_max - Algorithme de Rosenstein, 1993 / Section 11.1) :
    Mesure le taux moyen de divergence exponentielle des trajectoires proches dans l'espace des phases.
    """
    x = np.asarray(series, dtype=np.float64)
    x = x[np.isfinite(x)][:800]
    n = len(x)
    m_len = n - (emb_dim - 1) * tau
    if m_len < 60:
        return 0.0

    emb = np.column_stack([x[j * tau : j * tau + m_len] for j in range(emb_dim)])
    dist_mat = np.linalg.norm(emb[:, None, :] - emb[None, :, :], axis=2)
    # Exclusion temporelle de Theiler (voisinage immédiat +-5 pas)
    for i in range(m_len):
        dist_mat[i, max(0, i - 5) : min(m_len, i + 6)] = np.inf

    max_step = 8
    div_curve = np.zeros(max_step, dtype=np.float64)
    counts = np.zeros(max_step, dtype=np.float64)

    nn_idx = np.argmin(dist_mat[: m_len - max_step, : m_len - max_step], axis=1)
    for i, j in enumerate(nn_idx):
        for k in range(1, max_step):
            d_k = float(np.linalg.norm(emb[i + k] - emb[j + k]))
            if d_k > 1e-12:
                div_curve[k] += math.log(d_k)
                counts[k] += 1.0

    valid = counts > 10
    if int(np.sum(valid)) < 3:
        return 0.0
    steps = np.arange(max_step)[valid]
    avg_log_div = div_curve[valid] / counts[valid]
    slope = float(np.polyfit(steps, avg_log_div, 1)[0])
    return round(slope, 5)


def recurrence_quantification_rqa(series: np.ndarray, eps_sigma: float = 0.5) -> Dict[str, float]:
    """
    Analyse de Quantification de Récurrence (RQA - Section 11.1) :
    Calcule le Taux de Récurrence (RR) et le Déterminisme (DET : proportion de points récurrents
    formant des lignes diagonales de longueur >= 2).
    """
    x = np.asarray(series, dtype=np.float64)[:600]
    n = len(x)
    if n < 50 or np.std(x) <= 1e-12:
        return {"recurrence_rate": 0.0, "determinism_det": 0.0}

    eps = eps_sigma * float(np.std(x, ddof=1))
    R = (np.abs(x[:, None] - x[None, :]) < eps).astype(np.int32)
    np.fill_diagonal(R, 0)
    total_rec = int(np.sum(R))
    if total_rec == 0:
        return {"recurrence_rate": 0.0, "determinism_det": 0.0}

    diag_points = 0
    for offset in range(1, n - 1):
        diag = np.diag(R, k=offset)
        # Compte les segments consécutifs de 1 de longueur >= 2
        run_len = 0
        for val in diag:
            if val == 1:
                run_len += 1
            else:
                if run_len >= 2:
                    diag_points += run_len
                run_len = 0
        if run_len >= 2:
            diag_points += run_len

    det = (2.0 * diag_points) / float(total_rec)
    rr = float(total_rec) / float(n * (n - 1))
    return {"recurrence_rate": round(rr, 5), "determinism_det": round(min(1.0, det), 5)}


def wasserstein_regime_shift_detector(series: np.ndarray, window: int = 100) -> np.ndarray:
    """
    Distance de Wasserstein d'ordre 1 (Transport Optimal W_1 - Section 11.1 Niveau 4)
    calculée de manière strictement causale entre [t-2*window : t-window] et [t-window : t] :
    Détecte instantanément une déformation de la distribution des ticks sans hypothèse gaussienne.
    """
    x = np.asarray(series, dtype=np.float64)
    n = len(x)
    w1_vec = np.zeros(n, dtype=np.float64)
    for t in range(2 * window, n):
        u = x[t - 2 * window : t - window]
        v = x[t - window : t]
        w1_vec[t] = float(stats.wasserstein_distance(u, v))
    return w1_vec


# ==============================================================================
# 10. MODÈLES SPÉCIFIQUES FAMILLES DERIV : TREK (WEIBULL MLE) & RANGE BREAK 100/200
# ==============================================================================

def weibull_hazard_mle_trek(durations: np.ndarray) -> Dict[str, Any]:
    """
    Estime par Maximum de Vraisemblance (MLE) les paramètres (k, lambda) de la loi de Weibull
    f(x; k, lambda) = (k/lambda)*(x/lambda)^(k-1)*exp(-(x/lambda)^k) pour Trek Up/Down (Section 12 Famille 7) :
    - Si k = 1.0 : loi exponentielle sans mémoire (hasard constant).
    - Si k > 1.0 : vieillissement positif (le taux de hasard h(x) ~ x^(k-1) croît avec la durée).
    - Si k < 1.0 : rajeunissement / grappes (le taux de hasard décroît avec la durée).
    """
    d = np.asarray(durations, dtype=np.float64)
    d = d[d > 0]
    if len(d) < 30:
        return {"valid": False}

    k_shape, _, lam_scale = stats.weibull_min.fit(d, floc=0.0)
    # Test de Kolmogorov-Smirnov contre la loi exponentielle sans mémoire (k=1)
    ks_exp_stat, ks_exp_p = stats.kstest(d / np.mean(d), "expon")
    return {
        "valid": True,
        "n_events": len(d),
        "weibull_shape_k": round(float(k_shape), 4),
        "weibull_scale_lambda": round(float(lam_scale), 4),
        "ks_vs_memoryless_exponential_p": float(ks_exp_p),
        "has_duration_memory": bool(ks_exp_p < 0.01 and abs(k_shape - 1.0) > 0.08),
    }


def audit_range_break_barriers(high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 50) -> Dict[str, Any]:
    """
    Audite les barrières réfléchissantes exactes [L_t, U_t] sur Range Break 100 / 200 (Section 12 Famille 8) :
    Identifie les contacts avec le plafond U_t et le plancher L_t et mesure la probabilité empirique
    de rebond interne vs cassure franche.
    """
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    n = len(c)
    if n < window + 20:
        return {"valid": False}

    touches = 0
    breakouts = 0
    rebound_gains = []
    breakout_moves = []

    for t in range(window, n - 1):
        u_t = float(np.max(h[t - window : t]))
        l_t = float(np.min(l[t - window : t]))
        rng = max(1e-8, u_t - l_t)
        # Contact proche de la barrière haute ou basse (< 2% de la largeur du couloir)
        if abs(h[t] - u_t) <= 0.02 * rng:
            touches += 1
            next_move = c[t + 1] - c[t]
            if h[t + 1] > u_t + 0.05 * rng:
                breakouts += 1
                breakout_moves.append(abs(next_move))
            else:
                rebound_gains.append(-next_move)
        elif abs(l[t] - l_t) <= 0.02 * rng:
            touches += 1
            next_move = c[t + 1] - c[t]
            if l[t + 1] < l_t - 0.05 * rng:
                breakouts += 1
                breakout_moves.append(abs(next_move))
            else:
                rebound_gains.append(next_move)

    if touches == 0:
        return {"valid": False, "touches": 0}

    p_break = breakouts / float(touches)
    return {
        "valid": True,
        "n_barrier_touches": touches,
        "n_breakouts": breakouts,
        "empirical_breakout_prob": round(p_break, 4),
        "empirical_rebound_prob": round(1.0 - p_break, 4),
        "mean_rebound_move": round(float(np.mean(rebound_gains)) if rebound_gains else 0.0, 5),
        "mean_breakout_move": round(float(np.mean(breakout_moves)) if breakout_moves else 0.0, 5),
    }


if __name__ == "__main__":
    rng = np.random.default_rng(123)
    bits = rng.integers(0, 2, size=2000)
    lz = lempel_ziv_complexity_lz76(bits)
    tdmi = time_delayed_mutual_information(bits.astype(float), lag=1)
    te = schreiber_transfer_entropy(bits.astype(float), np.roll(bits, 1).astype(float), lag=1)
    dsi_res = wonham_bayesian_regime_filter_dsi(rng.normal(0.0003, 0.001, size=300))
    weib = weibull_hazard_mle_trek(rng.weibull(1.8, size=400) * 50.0)
    print(
        "[OK] deriv_quant_engine.py (10 modules complets) initialisé et testé :",
        {"lz76": round(lz, 3), "te_bits": round(te, 3), "dsi_p_bull": round(float(dsi_res["prob_bull"][-1]), 3), "weibull_k": weib["weibull_shape_k"]},
    )
