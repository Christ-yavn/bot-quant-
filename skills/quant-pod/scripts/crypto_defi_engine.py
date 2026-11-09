"""
crypto_defi_engine.py
=====================
Microstructure crypto CEX/DEX : là où existent des edges MESURABLES et explicables (quant-pod v3).

Contenu (formules exactes, références) :
  AMM / DEX
   - impermanent_loss_cpmm            : IL = 2 sqrt(k)/(1+k) - 1 (k = P1/P0)
   - univ3_position_amounts / value   : réserves d'une position concentrée [Pa, Pb] de liquidité L
   - lvr_rate                         : LVR instantané = sigma^2 L sqrt(P) / 4 (Milionis, Moallemi,
                                        Roughgarden, Zhang 2022) ; pour un CPMM plein : LVR/V = sigma^2/8
   - arb_with_fees_ptrade             : P_trade = 1/(1 + gamma sqrt(2 lambda)/sigma), ARB ~ LVR * P_trade
                                        (Milionis-Moallemi-Roughgarden 2023, régime blocs rapides ; à vérifier
                                        sur arXiv:2305.14604 avant usage chiffré)
   - lp_breakeven_volume              : volume/TVL quotidien nécessaire pour que les frais couvrent la LVR
   - cpmm_optimal_arbitrage           : taille et profit optimaux d'un arbitrage CEX->DEX (Uniswap v2, frais gamma)
  CEX / perpétuels
   - funding_carry_backtest           : cash-and-carry delta-neutre (long spot / short perp) avec frais,
                                        variation de base, distance de liquidation
  Market making
   - avellaneda_stoikov_quotes        : prix de réservation et spread optimal (Avellaneda & Stoikov 2008)
   - glft_quotes                      : quotes asymptotiques Guéant-Lehalle-Fernandez-Tapia (2013)
  Liquidité / impact
   - kyle_lambda, amihud_illiquidity

Dépendances : numpy.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

import numpy as np


# ============================================================================
# AMM / DEX
# ============================================================================
def impermanent_loss_cpmm(price_ratio: float) -> float:
    k = float(price_ratio)
    return 2.0 * math.sqrt(k) / (1.0 + k) - 1.0


def univ3_position_amounts(L: float, P: float, Pa: float, Pb: float) -> Dict[str, float]:
    sp, sa, sb = math.sqrt(P), math.sqrt(Pa), math.sqrt(Pb)
    if P <= Pa:
        x, y = L * (1 / sa - 1 / sb), 0.0
    elif P >= Pb:
        x, y = 0.0, L * (sb - sa)
    else:
        x, y = L * (1 / sp - 1 / sb), L * (sp - sa)
    return {"x": x, "y": y, "value_in_y": x * P + y}


def lvr_rate(L: float, P: float, sigma_annual: float, Pa: float = 0.0, Pb: float = float("inf")) -> Dict[str, float]:
    """
    LVR instantané (par an, en unités de y) d'une position active : sigma^2 * P^2 * |x'(P)| / 2,
    x(P) = L(1/sqrt(P) - 1/sqrt(Pb)) => |x'(P)| = L / (2 P^1.5) => LVR = sigma^2 L sqrt(P) / 4. Hors range : 0.
    """
    if not (Pa < P < Pb):
        return {"lvr_per_year": 0.0, "lvr_frac_of_value_per_year": 0.0}
    lvr = sigma_annual ** 2 * L * math.sqrt(P) / 4.0
    V = univ3_position_amounts(L, P, Pa if Pa > 0 else 1e-300, Pb)["value_in_y"] if math.isfinite(Pb) or Pa > 0 \
        else 2.0 * L * math.sqrt(P)
    return {"lvr_per_year": lvr, "lvr_frac_of_value_per_year": lvr / V if V > 0 else float("inf")}


def arb_with_fees_ptrade(sigma_annual: float, fee: float, block_time_seconds: float) -> Dict[str, float]:
    lam = 1.0 / (block_time_seconds / (365.0 * 86400.0))   # blocs par an
    eta = fee * math.sqrt(2.0 * lam) / sigma_annual
    p = 1.0 / (1.0 + eta)
    return {"p_trade": p, "eta": eta, "arb_share_of_lvr": p,
            "note": "[LITTÉRATURE: Milionis-Moallemi-Roughgarden 2023, asymptotique gamma->0, lambda->inf]"}


def lp_breakeven_volume(sigma_annual: float, fee: float, concentration: float = 1.0) -> Dict[str, float]:
    """
    Volume quotidien / TVL tel que fee * volume = LVR. CPMM plein : LVR/V = sigma^2/8 par an.
    concentration > 1 : position concentrée (LVR/V multipliée ~ par le facteur de concentration).
    """
    lvr_frac_daily = (sigma_annual ** 2 / 8.0) * concentration / 365.0
    return {"lvr_frac_daily": lvr_frac_daily, "breakeven_daily_volume_over_tvl": lvr_frac_daily / fee}


def cpmm_optimal_arbitrage(x: float, y: float, p_ext: float, fee: float) -> Dict[str, float]:
    """Pool Uniswap v2 (x actif risqué, y numéraire, p = y/x). Arbitrage optimal vs prix externe p_ext."""
    k = x * y
    g = 1.0 - fee
    p = y / x
    if p_ext > p / g:      # le pool est trop bon marché : acheter x avec y
        dy = (math.sqrt(p_ext * k * g) - y) / g
        dx_out = x - k / (y + g * dy)
        return {"direction": "BUY_X_ON_DEX", "input_y": dy, "output_x": dx_out, "profit_y": p_ext * dx_out - dy}
    if p_ext < p * g:      # le pool est trop cher : vendre x contre y
        dx = (math.sqrt(k * g / p_ext) - x) / g
        dy_out = y - k / (x + g * dx)
        return {"direction": "SELL_X_ON_DEX", "input_x": dx, "output_y": dy_out, "profit_y": dy_out - p_ext * dx}
    return {"direction": "NONE (dans la bande de frais)", "profit_y": 0.0}


# ============================================================================
# PERPÉTUELS : CASH-AND-CARRY
# ============================================================================
def funding_carry_backtest(spot: Sequence[float], perp: Sequence[float], funding_rate: Sequence[float],
                           entry_threshold: float = 0.0001, exit_threshold: float = 0.0, fee_per_leg: float = 0.0005,
                           leverage: float = 3.0, maint_margin: float = 0.005) -> Dict[str, object]:
    """
    Par intervalle de funding i : funding_rate[i] payé par les longs aux shorts (si > 0).
    Décision au début de i avec le funding CONNU de l'intervalle précédent (i-1) -> pas de look-ahead.
    Position : +1 spot, -1 perp (notionnel 1). PnL_i = funding_i + (spot_i+1-spot_i) - (perp_i+1-perp_i), normalisé.
    Coût : 2 jambes x fee à l'entrée et à la sortie. Distance de liquidation du short perp ~ 1/leverage - maint.
    """
    s, f, fr = (np.asarray(a, dtype=float) for a in (spot, perp, funding_rate))
    n = len(s)
    pos = 0
    pnl = np.zeros(n)
    entry_ref = None
    n_trades = 0
    liq_flags = 0
    liq_dist = 1.0 / leverage - maint_margin
    for i in range(1, n - 1):
        prev = fr[i - 1]
        if pos == 0 and prev > entry_threshold:
            pos, entry_ref = 1, f[i]
            pnl[i] -= 2 * fee_per_leg
            n_trades += 1
        elif pos == 1 and prev <= exit_threshold:
            pos = 0
            pnl[i] -= 2 * fee_per_leg
        if pos == 1:
            pnl[i] += fr[i] + (s[i + 1] - s[i]) / s[i] - (f[i + 1] - f[i]) / f[i]
            if (f[i + 1] - entry_ref) / entry_ref > liq_dist:
                liq_flags += 1
    active = pnl[pnl != 0]
    return {"total_return": float(pnl.sum()), "n_entries": n_trades,
            "mean_per_interval_active": float(active.mean()) if len(active) else 0.0,
            "liquidation_risk_events": liq_flags, "pnl": pnl}


# ============================================================================
# MARKET MAKING
# ============================================================================
def avellaneda_stoikov_quotes(mid: float, inventory: float, gamma: float, sigma: float, k: float,
                              time_left: float) -> Dict[str, float]:
    """r = s - q gamma sigma^2 (T-t) ; spread = gamma sigma^2 (T-t) + (2/gamma) ln(1 + gamma/k)."""
    r = mid - inventory * gamma * sigma ** 2 * time_left
    spread = gamma * sigma ** 2 * time_left + (2.0 / gamma) * math.log(1.0 + gamma / k)
    return {"reservation": r, "spread": spread, "bid": r - spread / 2, "ask": r + spread / 2}


def glft_quotes(mid: float, inventory: float, gamma: float, sigma: float, A: float, k: float) -> Dict[str, float]:
    """Approximation asymptotique (horizon infini) de Guéant, Lehalle & Fernandez-Tapia (2013)."""
    c1 = (1.0 / gamma) * math.log(1.0 + gamma / k)
    c2 = math.sqrt((sigma ** 2 * gamma) / (2.0 * k * A) * (1.0 + gamma / k) ** (1.0 + k / gamma))
    db = c1 + (2 * inventory + 1) / 2.0 * c2
    da = c1 - (2 * inventory - 1) / 2.0 * c2
    return {"bid": mid - db, "ask": mid + da, "delta_bid": db, "delta_ask": da}


# ============================================================================
# LIQUIDITÉ / IMPACT
# ============================================================================
def kyle_lambda(price_changes: Sequence[float], signed_volume: Sequence[float]) -> Dict[str, float]:
    dp = np.asarray(price_changes, dtype=float)
    q = np.asarray(signed_volume, dtype=float)
    q = q - q.mean()
    lam = float(np.dot(q, dp - dp.mean()) / np.dot(q, q))
    resid = dp - dp.mean() - lam * q
    se = float(math.sqrt(np.sum(resid ** 2) / (len(dp) - 2) / np.dot(q, q)))
    return {"lambda": lam, "t_stat": lam / se if se > 0 else float("nan")}


def amihud_illiquidity(returns: Sequence[float], dollar_volume: Sequence[float]) -> float:
    r = np.abs(np.asarray(returns, dtype=float))
    v = np.asarray(dollar_volume, dtype=float)
    ok = v > 0
    return float(np.mean(r[ok] / v[ok]))


if __name__ == "__main__":
    # 1. LVR/V = sigma^2/8 pour un CPMM plein
    sig = 0.8
    lv = lvr_rate(L=1000.0, P=2500.0, sigma_annual=sig)
    assert abs(lv["lvr_frac_of_value_per_year"] - sig ** 2 / 8) < 1e-9, lv
    # 2. Position concentrée : LVR/V plus élevée (levier de liquidité)
    lv3 = lvr_rate(L=1000.0, P=2500.0, sigma_annual=sig, Pa=2000.0, Pb=3100.0)
    assert lv3["lvr_frac_of_value_per_year"] > lv["lvr_frac_of_value_per_year"]
    # 3. IL : prix x4 -> -20 %
    assert abs(impermanent_loss_cpmm(4.0) + 0.2) < 1e-12
    # 4. Arbitrage CPMM : profit > 0 hors bande, 0 dans la bande
    a1 = cpmm_optimal_arbitrage(100.0, 250000.0, 2600.0, 0.003)
    a2 = cpmm_optimal_arbitrage(100.0, 250000.0, 2502.0, 0.003)
    assert a1["profit_y"] > 0 and a2["profit_y"] == 0.0, (a1, a2)
    # 5. Avellaneda-Stoikov : inventaire long -> prix de réservation sous le mid
    q = avellaneda_stoikov_quotes(100.0, 5, 0.1, 2.0, 1.5, 1.0)
    assert q["reservation"] < 100.0 and q["ask"] > q["bid"]
    # 6. Carry : funding constant positif, base stable -> rendement positif net de frais
    n = 500
    spot = 30000 * np.ones(n); perp = 30010 * np.ones(n); fr = np.full(n, 0.0002)
    cb = funding_carry_backtest(spot, perp, fr)
    assert cb["total_return"] > 0 and cb["n_entries"] == 1, cb
    p = arb_with_fees_ptrade(0.8, 0.003, 12.0)
    be = lp_breakeven_volume(0.8, 0.003)
    print(f"LVR/V CPMM={lv['lvr_frac_of_value_per_year']:.4f} (=sigma^2/8) | concentrée={lv3['lvr_frac_of_value_per_year']:.3f}")
    print(f"P_trade(ETH-like, 30bps, 12s)={p['p_trade']:.3f} | volume/TVL de break-even={be['breakeven_daily_volume_over_tvl']:.3f}/jour")
    print(f"arbitrage optimal: {a1['direction']} profit={a1['profit_y']:.2f} | carry total={cb['total_return']:.4f}")
    print("crypto_defi_engine : 6/6 auto-tests OK")
