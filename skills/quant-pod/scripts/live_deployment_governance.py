r"""
live_deployment_governance.py
=============================
Moteur Quant Dev de Mise en Production, de Capacité d'Exécution (Almgren-Chriss),
de Routage Idempotent avec Coupe-Circuit Pré-Trade et de Surveillance Continue
de Dérive d'Alpha / Slippage (KS + Page-Hinkley / SPRT Kill-Switch) pour `quant-pod` v4.0.

Boucle le cycle de vie complet du Desk Quantitatif :
  Inspection & Macro -> Synthèse & Backtest -> Validation Aveugle -> Allocation -> DÉPLOIEMENT LIVE.

Composants :
  1. `build_deployment_manifest` & `verify_promotion_readiness` :
     Compile une stratégie validée en un manifeste de déploiement immuable signé par SHA-256
     et bloque mathématiquement toute mise en Paper/Live si une porte `/boost`, l'intégrité
     du `HashChainLedger`, ou la validation du Holdout manque.
  2. `estimate_strategy_capacity_usd` & `plan_child_order_schedule` :
     Calcule l'AUM maximal (capacité $C_{\max}$) avant que l'impact racine carrée d'Almgren-Chriss
     ne consomme plus de 50 % de l'alpha net, et découpe les ordres parents (Single-Shot, Maker
     Post-Only ou TWAP fractionné).
  3. `DeterministicExecutionRouter` :
     Génère des `client_order_id` déterministes HMAC-SHA256 (idempotence stricte anti-double-ordre
     sur retry réseau) et applique un pare-feu de risque pré-trade non contournable (levier max,
     taille max par ordre, perte journalière max, drawdown max, filtre d'explosion de spread live
     et fenêtre de blackout macro).
  4. `LiveGovernanceMonitor` :
     Surveille en continu l'écart entre le Paper/Live et le Backtest :
       - Test de Kolmogorov-Smirnov (KS) à 2 échantillons sur la dérive du slippage exécuté.
       - Détecteur séquentiel de Page-Hinkley / CUSUM unilatéral sur la dégradation de l'espérance
         nette par trade (`alpha_decay`).
       - Machine à états de Kill-Switch autonome (`NORMAL` -> `THROTTLE_50PCT` -> `HALT_AND_FLATTEN`)
         journalisée dans `HashChainLedger`.

Dépendances : bibliothèque standard, numpy, scipy uniquement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from quant_validation_engine import GATES
from research_integrity import HashChainLedger, canonical_json, sha256_bytes


# ============================================================================
# 1. MANIFESTE DE DÉPLOIEMENT SIGNÉ & PORTE DE PROMOTION PAPER / LIVE
# ============================================================================

@dataclass
class DeploymentManifest:
    strategy_id: str
    version: str
    target_instruments: List[str]
    timeframe: str
    warmup_bars_required: int
    execution_style: str
    expected_net_bps_per_trade: float
    expected_sharpe_ann: float
    backtest_slippage_bps_mean: float
    backtest_slippage_bps_p95: float
    max_position_frac_equity: float
    max_gross_leverage: float
    max_daily_loss_frac: float
    max_drawdown_kill_frac: float
    max_spread_mult_circuit_breaker: float
    validation_proof: Dict[str, Any]
    created_ts: str
    manifest_sha256: str


def verify_promotion_readiness(
    validation_metrics: Dict[str, Any],
    ledger_verify_report: Dict[str, Any],
    holdout_passed: bool,
    paper_trades_completed: int = 0,
    target_stage: str = "PAPER",
) -> Dict[str, Any]:
    """
    Porte institutionnelle de promotion vers `PAPER` ou `LIVE` :
      - Vérifie l'intégrité cryptographique de la chaîne d'essais (`ledger_verify_report["valid"] == True`).
      - Vérifie l'ensemble des seuils `GATES` (`min_trades >= 200`, `dsr >= 0.95`, `pbo <= 0.20`,
        `null_pvalue <= 0.05`, `plateau >= 0.50`, `cost_stress_2x_mean > 0`).
      - Vérifie le passage du Holdout scellé (`holdout_passed == True`).
      - Pour `target_stage == "LIVE"`, exige en outre `>= 100` trades de Paper-Trading conformes !
    """
    stage = str(target_stage).upper()
    if stage not in ("PAPER", "LIVE"):
        raise ValueError(f"target_stage inconnu: {target_stage}. Attendu 'PAPER' ou 'LIVE'.")

    blockers: List[str] = []
    if not bool(ledger_verify_report.get("valid", False)):
        blockers.append("LEDGER_TAMPERED_OR_INVALID: La chaîne SHA-256 des essais n'est pas valide.")

    n_tr = int(validation_metrics.get("n_trades", 0))
    if n_tr < int(GATES["min_trades"]):
        blockers.append(f"INSUFFICIENT_TRADES: {n_tr} < {int(GATES['min_trades'])}.")

    dsr_val = float(validation_metrics.get("dsr", 0.0))
    if not np.isfinite(dsr_val) or dsr_val < float(GATES["dsr_min"]):
        blockers.append(f"DSR_BELOW_GATE: {dsr_val:.4f} < {GATES['dsr_min']}.")

    pbo_val = float(validation_metrics.get("pbo", 1.0))
    if not np.isfinite(pbo_val) or pbo_val > float(GATES["pbo_max"]):
        blockers.append(f"PBO_ABOVE_GATE: {pbo_val:.4f} > {GATES['pbo_max']}.")

    null_p = float(validation_metrics.get("null_pvalue", 1.0))
    if not np.isfinite(null_p) or null_p > float(GATES["null_pvalue_max"]):
        blockers.append(f"NULL_MODEL_FAILED: p_null={null_p:.4f} > {GATES['null_pvalue_max']}.")

    plat = float(validation_metrics.get("plateau", 0.0))
    if not np.isfinite(plat) or plat < float(GATES["plateau_min"]):
        blockers.append(f"PLATEAU_FRAGILE: {plat:.4f} < {GATES['plateau_min']}.")

    c2x = float(validation_metrics.get("cost_stress_2x_mean", -1.0))
    if not np.isfinite(c2x) or c2x <= float(GATES["cost_stress_min_mean"]):
        blockers.append(f"COST_STRESS_2X_NEGATIVE: mean_2x={c2x:.6f} <= 0.")

    if not holdout_passed:
        blockers.append("HOLDOUT_FAILED_OR_UNVERIFIED: Le Holdout scellé n'a pas validé la stratégie.")

    if stage == "LIVE" and int(paper_trades_completed) < 100:
        blockers.append(
            f"PAPER_TRACK_RECORD_TOO_SHORT: {paper_trades_completed} trades < 100 requis avant passage LIVE."
        )

    return {
        "approved": len(blockers) == 0,
        "target_stage": stage,
        "n_blockers": len(blockers),
        "blockers": blockers,
    }


def build_deployment_manifest(
    strategy_id: str,
    version: str,
    target_instruments: Sequence[str],
    timeframe: str,
    warmup_bars_required: int,
    validation_metrics: Dict[str, Any],
    ledger_verify_report: Dict[str, Any],
    holdout_passed: bool,
    execution_style: str = "MAKER_OR_LIQUID_TAKER",
    backtest_slippage_bps: Sequence[float] = (1.0, 1.5, 2.0),
    max_position_frac_equity: float = 0.10,
    max_gross_leverage: float = 1.50,
    max_daily_loss_frac: float = 0.02,
    max_drawdown_kill_frac: float = 0.08,
    max_spread_mult_circuit_breaker: float = 2.5,
    ledger: Optional[HashChainLedger] = None,
) -> Dict[str, Any]:
    """
    Construit et scelle par SHA-256 le contrat immuable de déploiement Paper-Trading d'une stratégie.
    Refuse de générer un manifeste actif (`status = PROMOTION_BLOCKED`) si `verify_promotion_readiness` échoue.
    """
    readiness = verify_promotion_readiness(
        validation_metrics=validation_metrics,
        ledger_verify_report=ledger_verify_report,
        holdout_passed=holdout_passed,
        target_stage="PAPER",
    )
    if not readiness["approved"]:
        return {
            "status": "PROMOTION_BLOCKED",
            "readiness": readiness,
            "manifest": None,
        }

    slip_arr = np.asarray(list(backtest_slippage_bps), dtype=np.float64)
    slip_mean = float(np.mean(slip_arr)) if len(slip_arr) > 0 else 1.0
    slip_p95 = float(np.percentile(slip_arr, 95)) if len(slip_arr) > 0 else 2.0
    ts_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    body = {
        "strategy_id": str(strategy_id),
        "version": str(version),
        "target_instruments": [str(s) for s in target_instruments],
        "timeframe": str(timeframe),
        "warmup_bars_required": max(1, int(warmup_bars_required)),
        "execution_style": str(execution_style),
        "expected_net_bps_per_trade": round(float(validation_metrics.get("net_bps_per_trade", 5.0)), 4),
        "expected_sharpe_ann": round(float(validation_metrics.get("sharpe_ann", 1.5)), 4),
        "backtest_slippage_bps_mean": round(slip_mean, 4),
        "backtest_slippage_bps_p95": round(slip_p95, 4),
        "max_position_frac_equity": float(np.clip(max_position_frac_equity, 0.005, 1.0)),
        "max_gross_leverage": float(np.clip(max_gross_leverage, 0.1, 5.0)),
        "max_daily_loss_frac": float(np.clip(max_daily_loss_frac, 0.002, 0.20)),
        "max_drawdown_kill_frac": float(np.clip(max_drawdown_kill_frac, 0.01, 0.35)),
        "max_spread_mult_circuit_breaker": float(max(1.2, max_spread_mult_circuit_breaker)),
        "validation_proof": {
            "n_trades": int(validation_metrics["n_trades"]),
            "dsr": round(float(validation_metrics["dsr"]), 4),
            "pbo": round(float(validation_metrics["pbo"]), 4),
            "null_pvalue": round(float(validation_metrics["null_pvalue"]), 4),
            "ledger_head": str(ledger_verify_report.get("head", "")),
        },
        "created_ts": ts_now,
    }
    digest = sha256_bytes(canonical_json(body))
    manifest = DeploymentManifest(**body, manifest_sha256=digest)

    if ledger is not None:
        ledger.append(
            {
                "type": "deployment_manifest_sealed",
                "strategy_id": strategy_id,
                "version": version,
                "manifest_sha256": digest,
            }
        )

    return {
        "status": "APPROVED_FOR_PAPER_DEPLOYMENT",
        "readiness": readiness,
        "manifest": asdict(manifest),
    }


# ============================================================================
# 2. CAPACITÉ MAXIMALE D'AUM & PLANIFICATION D'EXÉCUTION (ALMGREN-CHRISS)
# ============================================================================

def estimate_strategy_capacity_usd(
    expected_alpha_bps_per_trade: float,
    adv_usd: float,
    daily_volatility_frac: float,
    avg_holding_days: float = 0.25,
    impact_coeff_eta: float = 0.50,
    max_alpha_erosion_frac: float = 0.50,
    position_frac_of_aum: float = 0.10,
) -> Dict[str, float]:
    """
    Loi de la Racine Carrée d'Impact de Marché (Grinold & Kahn / Almgren-Chriss) :
      Impact aller-retour (en fraction) ≈ 2 * eta * sigma_daily * sqrt(Order_USD / ADV_USD).
    Calcule la taille maximale par ordre `max_order_usd` et la capacité maximale en capital
    `max_aum_capacity_usd = max_order_usd / position_frac_of_aum` au-delà de laquelle l'impact
    de marché détruit plus de `max_alpha_erosion_frac` (50 % par défaut) de l'alpha net par trade.
    """
    alpha_frac = max(0.0, float(expected_alpha_bps_per_trade) * 1e-4)
    adv = max(1.0, float(adv_usd))
    sig = max(1e-6, float(daily_volatility_frac))
    eta = max(0.05, float(impact_coeff_eta))
    erosion_budget = alpha_frac * float(np.clip(max_alpha_erosion_frac, 0.10, 0.90))

    # 2 * eta * sig * sqrt(Q / ADV) <= erosion_budget  =>  Q <= ADV * (erosion_budget / (2 * eta * sig))^2
    participation_max = (erosion_budget / (2.0 * eta * sig)) ** 2
    participation_capped = min(0.05, participation_max)  # plafond prudentiel 5 % de l'ADV par ordre
    max_order_usd = adv * participation_capped
    pos_frac = float(np.clip(position_frac_of_aum, 0.01, 1.0))
    turnover_per_day = 1.0 / max(0.05, float(avg_holding_days))
    max_aum_usd = max_order_usd / pos_frac

    return {
        "max_order_usd": round(max_order_usd, 2),
        "max_aum_capacity_usd": round(max_aum_usd, 2),
        "daily_turnover_x": round(turnover_per_day * pos_frac, 4),
        "max_adv_participation_pct": round(participation_capped * 100.0, 4),
        "impact_bps_at_max_order": round(2.0 * eta * sig * math.sqrt(participation_capped) * 1e4, 3),
    }


def plan_child_order_schedule(
    order_notional_usd: float,
    adv_usd: float,
    urgency_alpha_decay_bps_per_bar: float = 1.0,
    baseline_spread_bps: float = 2.0,
) -> Dict[str, Any]:
    """
    Résolveur TRIZ d'Exécution (Compromis Urgence vs Impact de Marché) :
      - Participation < 0.1 % de l'ADV et urgence forte -> `SINGLE_IOC_OR_LIMIT` (1 tranche)
      - Participation modérée ou urgence faible -> `PASSIVE_MAKER_POST_ONLY`
      - Participation >= 0.25 % de l'ADV -> découpage `TWAP_ADAPTIVE` en `N` tranches enfants.
    """
    q = max(0.0, float(order_notional_usd))
    adv = max(1.0, float(adv_usd))
    part = q / adv
    if part < 0.001:
        if urgency_alpha_decay_bps_per_bar > baseline_spread_bps * 0.75:
            return {"mode": "SINGLE_LIQUID_TAKER", "n_slices": 1, "slice_usd": round(q, 2), "adv_pct": round(part * 100, 4)}
        return {"mode": "PASSIVE_MAKER_POST_ONLY", "n_slices": 1, "slice_usd": round(q, 2), "adv_pct": round(part * 100, 4)}

    n_slices = int(np.clip(math.ceil(math.sqrt(part / 0.0005)), 2, 24))
    return {
        "mode": "TWAP_ADAPTIVE_SLICED",
        "n_slices": n_slices,
        "slice_usd": round(q / n_slices, 2),
        "adv_pct": round(part * 100, 4),
    }


# ============================================================================
# 3. ROUTEUR D'ORDRES IDEMPOTENT & PARE-FEU PRÉ-TRADE (`DeterministicExecutionRouter`)
# ============================================================================

class DeterministicExecutionRouter:
    """
    Pare-feu d'exécution Quant Dev garantissant :
      1. Idempotence cryptographique : un même `(strategy_id, symbol, bar_ts, side, qty_bucket)`
         produit toujours exactement le même `client_order_id` et ne peut JAMAIS être envoyé 2 fois.
      2. Contrôles pré-trade codés en dur (non contournables par le générateur de signaux) :
         spread live anormal, blackout d'annonce macro, perte journalière max, drawdown max,
         exposition maximale par position et levier global.
    """

    def __init__(self, manifest: Dict[str, Any], secret_key: str = "quant_pod_v4_router"):
        self.manifest = dict(manifest)
        self._key = secret_key.encode("utf-8")
        self._submitted_ids: Dict[str, Dict[str, Any]] = {}

    def make_client_order_id(self, symbol: str, bar_ts: str, side: int, target_notional_usd: float) -> str:
        payload = f"{self.manifest['strategy_id']}|{symbol}|{bar_ts}|{int(side)}|{round(float(target_notional_usd), 2)}"
        digest = hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
        return f"qp4_{digest}"

    def validate_and_route_order(
        self,
        symbol: str,
        bar_ts: str,
        side: int,
        target_notional_usd: float,
        current_equity_usd: float,
        current_gross_exposure_usd: float,
        daily_pnl_frac: float,
        current_drawdown_frac: float,
        live_spread_bps: float,
        baseline_spread_bps: float,
        in_macro_blackout: bool = False,
    ) -> Dict[str, Any]:
        if int(side) not in (-1, 1) or target_notional_usd <= 0.0:
            return {"accepted": False, "reason": "INVALID_SIDE_OR_ZERO_NOTIONAL"}
        if symbol not in self.manifest.get("target_instruments", []):
            return {"accepted": False, "reason": f"SYMBOL_NOT_AUTHORIZED ({symbol})"}
        if current_equity_usd <= 0.0:
            return {"accepted": False, "reason": "NON_POSITIVE_EQUITY"}

        cid = self.make_client_order_id(symbol, bar_ts, side, target_notional_usd)
        if cid in self._submitted_ids:
            return {
                "accepted": False,
                "idempotent_duplicate": True,
                "client_order_id": cid,
                "reason": "DUPLICATE_ORDER_BLOCKED_BY_IDEMPOTENCY",
            }

        if current_drawdown_frac >= float(self.manifest["max_drawdown_kill_frac"]):
            return {"accepted": False, "client_order_id": cid, "reason": "KILL_SWITCH_MAX_DRAWDOWN_BREACHED"}
        if daily_pnl_frac <= -float(self.manifest["max_daily_loss_frac"]):
            return {"accepted": False, "client_order_id": cid, "reason": "DAILY_LOSS_CIRCUIT_BREAKER"}
        if in_macro_blackout:
            return {"accepted": False, "client_order_id": cid, "reason": "MACRO_EVENT_BLACKOUT_ACTIVE"}

        max_sp = float(self.manifest["max_spread_mult_circuit_breaker"]) * max(0.1, float(baseline_spread_bps))
        if live_spread_bps > max_sp:
            return {
                "accepted": False,
                "client_order_id": cid,
                "reason": f"SPREAD_SPIKE_CIRCUIT_BREAKER ({live_spread_bps:.2f} > {max_sp:.2f} bps)",
            }

        max_pos_usd = float(self.manifest["max_position_frac_equity"]) * current_equity_usd
        clipped_usd = min(float(target_notional_usd), max_pos_usd)
        max_gross_usd = float(self.manifest["max_gross_leverage"]) * current_equity_usd
        avail_gross = max(0.0, max_gross_usd - max(0.0, float(current_gross_exposure_usd)))
        final_usd = min(clipped_usd, avail_gross)
        if final_usd <= 0.0:
            return {"accepted": False, "client_order_id": cid, "reason": "MAX_GROSS_LEVERAGE_REACHED"}

        order_record = {
            "accepted": True,
            "idempotent_duplicate": False,
            "client_order_id": cid,
            "symbol": symbol,
            "bar_ts": bar_ts,
            "side": int(side),
            "requested_usd": round(float(target_notional_usd), 2),
            "approved_usd": round(final_usd, 2),
            "was_size_clipped": bool(final_usd < target_notional_usd - 1e-6),
        }
        self._submitted_ids[cid] = order_record
        return order_record


# ============================================================================
# 4. MONITEUR DE DÉRIVE D'EXÉCUTION (KS) & KILL-SWITCH STATISTIQUE (CUSUM)
# ============================================================================

class LiveGovernanceMonitor:
    """
    Surveillance statistique continue en Paper/Live (`Junior Desk Risk & Kill-Switch Monitor`) :
      1. Compare les slippages réalisés en live à la distribution de référence du backtest via le
         test de Kolmogorov-Smirnov unilatéral (`alternative='less'` sur `-slippage`, c.-à-d. live pire).
      2. Applique un détecteur CUSUM unilatéral de Page sur les rendements nets par trade pour
         détecter précocement l'effondrement structurel de l'alpha (`H0: mu = mu_bt` vs `H1: mu <= 0`).
      3. Émet un état de gouvernance : `NORMAL`, `THROTTLE_50PCT`, ou `HALT_AND_FLATTEN`.
    """

    def __init__(
        self,
        expected_net_bps_per_trade: float,
        trade_std_bps: float,
        reference_slippage_bps: Sequence[float],
        max_drawdown_bps: float = 800.0,
        cusum_threshold_h: float = 4.0,
        ledger: Optional[HashChainLedger] = None,
    ):
        self.mu_bps = max(0.1, float(expected_net_bps_per_trade))
        self.sd_bps = max(1.0, float(trade_std_bps))
        self.ref_slip = np.asarray(list(reference_slippage_bps), dtype=np.float64)
        self.max_dd_bps = max(20.0, float(max_drawdown_bps))
        self.cusum_h = max(2.0, float(cusum_threshold_h))
        self.ledger = ledger

        self.live_pnls_bps: List[float] = []
        self.live_slippages_bps: List[float] = []
        self.cusum_neg: float = 0.0
        self.peak_cum_bps: float = 0.0
        self.cum_bps: float = 0.0
        self.state: str = "NORMAL"

    def record_trade(self, net_pnl_bps: float, realized_slippage_bps: float) -> Dict[str, Any]:
        pnl = float(net_pnl_bps)
        slip = float(realized_slippage_bps)
        self.live_pnls_bps.append(pnl)
        self.live_slippages_bps.append(slip)

        self.cum_bps += pnl
        self.peak_cum_bps = max(self.peak_cum_bps, self.cum_bps)
        dd_bps = self.peak_cum_bps - self.cum_bps

        # Statistique CUSUM négative standardisée : détecte le passage de mu = +mu_bps vers mu <= 0
        # Sous H0 (pnl ~ N(mu_bps, sd^2)), z_deficit = (mu_bps - pnl) / sd - 0.5 * (mu_bps / sd) a une dérive < 0 !
        snr = min(1.5, self.mu_bps / self.sd_bps)
        z_obs = (pnl - self.mu_bps) / self.sd_bps
        self.cusum_neg = max(0.0, self.cusum_neg - z_obs - 0.5 * max(0.25, snr))

        slip_ks_p = 1.0
        slip_degraded = False
        if len(self.live_slippages_bps) >= 15 and len(self.ref_slip) >= 10:
            live_arr = np.asarray(self.live_slippages_bps, dtype=np.float64)
            if float(np.mean(live_arr)) > float(np.mean(self.ref_slip)) * 1.25:
                ks_res = stats.ks_2samp(self.ref_slip, live_arr, alternative="greater")
                slip_ks_p = float(ks_res.pvalue)
                slip_degraded = bool(slip_ks_p < 0.01)

        reasons: List[str] = []
        if dd_bps >= self.max_dd_bps:
            self.state = "HALT_AND_FLATTEN"
            reasons.append(f"MAX_DRAWDOWN_BREACHED ({dd_bps:.1f} >= {self.max_dd_bps:.1f} bps)")
        elif self.cusum_neg >= self.cusum_h:
            self.state = "HALT_AND_FLATTEN"
            reasons.append(f"CUSUM_ALPHA_DECAY_TRIGGERED (S_neg={self.cusum_neg:.2f} >= {self.cusum_h:.2f})")
        elif slip_degraded or self.cusum_neg >= 0.60 * self.cusum_h or dd_bps >= 0.65 * self.max_dd_bps:
            if self.state != "HALT_AND_FLATTEN":
                self.state = "THROTTLE_50PCT"
            if slip_degraded:
                reasons.append(f"SLIPPAGE_DRIFT_KS_ALERT (p={slip_ks_p:.5f})")
            if self.cusum_neg >= 0.60 * self.cusum_h:
                reasons.append(f"EARLY_ALPHA_DECAY_WARNING (S_neg={self.cusum_neg:.2f})")

        size_mult = 0.0 if self.state == "HALT_AND_FLATTEN" else (0.5 if self.state == "THROTTLE_50PCT" else 1.0)
        status = {
            "n_live_trades": len(self.live_pnls_bps),
            "state": self.state,
            "recommended_size_multiplier": size_mult,
            "cum_pnl_bps": round(self.cum_bps, 3),
            "drawdown_bps": round(dd_bps, 3),
            "cusum_decay_stat": round(self.cusum_neg, 4),
            "slippage_ks_pvalue": round(slip_ks_p, 6),
            "alerts": reasons,
        }
        if self.ledger is not None and reasons:
            self.ledger.append({"type": "live_governance_alert", **status})
        return status


# ============================================================================
# AUTO-TESTS DÉTERMINISTES INTÉGRÉS
# ============================================================================

if __name__ == "__main__":
    import tempfile

    rng = np.random.default_rng(404)
    tmp_dir = tempfile.mkdtemp()
    hcl = HashChainLedger(os.path.join(tmp_dir, "deploy_chain.jsonl"))
    hcl.append({"type": "init_campaign", "project": "test_v4"})

    # 1. Blocage d'une stratégie non validée + approbation d'une stratégie validée
    bad_dep = build_deployment_manifest(
        "STRAT_BAD",
        "1.0.0",
        ["BTCUSDT"],
        "H1",
        96,
        {"n_trades": 80, "dsr": 0.60, "pbo": 0.45, "null_pvalue": 0.20, "plateau": 0.3, "cost_stress_2x_mean": -0.01},
        hcl.verify(),
        holdout_passed=False,
    )
    assert bad_dep["status"] == "PROMOTION_BLOCKED" and bad_dep["readiness"]["n_blockers"] >= 4

    good_metrics = {
        "n_trades": 340,
        "dsr": 0.992,
        "pbo": 0.08,
        "null_pvalue": 0.004,
        "plateau": 0.75,
        "cost_stress_2x_mean": 0.0012,
        "net_bps_per_trade": 14.5,
        "sharpe_ann": 2.35,
    }
    good_dep = build_deployment_manifest(
        "STRAT_CHAMELEON_V4",
        "4.0.0",
        ["BTCUSDT", "ETHUSDT"],
        "H1",
        96,
        good_metrics,
        hcl.verify(),
        holdout_passed=True,
        backtest_slippage_bps=rng.normal(1.5, 0.4, size=80),
        ledger=hcl,
    )
    assert good_dep["status"] == "APPROVED_FOR_PAPER_DEPLOYMENT"
    assert hcl.verify()["valid"] is True

    # 2. Capacité Almgren-Chriss & Découpage TWAP
    cap = estimate_strategy_capacity_usd(expected_alpha_bps_per_trade=15.0, adv_usd=50_000_000, daily_volatility_frac=0.03)
    assert cap["max_order_usd"] > 0 and cap["impact_bps_at_max_order"] <= 7.501
    sched = plan_child_order_schedule(order_notional_usd=500_000, adv_usd=50_000_000)
    assert sched["mode"] == "TWAP_ADAPTIVE_SLICED" and sched["n_slices"] >= 2

    # 3. Routeur idempotent & coupe-circuit pré-trade
    router = DeterministicExecutionRouter(good_dep["manifest"])
    o1 = router.validate_and_route_order("BTCUSDT", "2026-11-25T12:00:00Z", 1, 5_000, 100_000, 0, 0.0, 0.01, 2.0, 1.5)
    assert o1["accepted"] and not o1["idempotent_duplicate"]
    o_dup = router.validate_and_route_order("BTCUSDT", "2026-11-25T12:00:00Z", 1, 5_000, 100_000, 0, 0.0, 0.01, 2.0, 1.5)
    assert not o_dup["accepted"] and o_dup["idempotent_duplicate"]
    o_sp = router.validate_and_route_order("BTCUSDT", "2026-11-25T13:00:00Z", 1, 5_000, 100_000, 0, 0.0, 0.01, 9.0, 1.5)
    assert not o_sp["accepted"] and "SPREAD_SPIKE" in o_sp["reason"]

    # 4. Moniteur Live KS Slippage + Kill-Switch CUSUM
    ref_sl = rng.normal(1.2, 0.25, size=60)
    mon = LiveGovernanceMonitor(expected_net_bps_per_trade=12.0, trade_std_bps=25.0, reference_slippage_bps=ref_sl, cusum_threshold_h=4.0, ledger=hcl)
    for _ in range(10):
        st_ok = mon.record_trade(net_pnl_bps=float(rng.normal(13.0, 15.0)), realized_slippage_bps=float(rng.normal(1.2, 0.2)))
    assert st_ok["state"] == "NORMAL"
    # Simuler un effondrement d'alpha (série de pertes systématiques) -> déclenchement automatique HALT_AND_FLATTEN
    for _ in range(20):
        st_bad = mon.record_trade(net_pnl_bps=-18.0, realized_slippage_bps=3.8)
    assert st_bad["state"] == "HALT_AND_FLATTEN" and st_bad["recommended_size_multiplier"] == 0.0
    assert hcl.verify()["valid"] is True

    print(
        "live_deployment_governance : 4/4 auto-tests OK",
        {
            "manifest_sha256": good_dep["manifest"]["manifest_sha256"][:12],
            "max_order_usd": cap["max_order_usd"],
            "twap_slices": sched["n_slices"],
            "kill_switch_state": st_bad["state"],
        },
    )
