# MQL5 EXPERT ADVISORS & PRODUCTION INFERENCE ENGINES

This directory contains the Expert Advisors (EAs) and scripts for MetaTrader 5 on Deriv synthetic indices. All historical versions (`v6`, `v7`, `v8`, `VolSqueeze v1`) are preserved intact for forensic reproducibility.

> [!IMPORTANT]
> **Audit Hardening (25/10/2026) — See [`docs/ETAT_DE_LA_VERITE.md`](../../docs/ETAT_DE_LA_VERITE.md) :**  
> Both active EAs (`DerivBoomCrashHFT_v830_Ultimate.mq5` and `Deriv_VolSqueeze_Breakout_EA_v3.mq5`) have been repaired and recompiled (`0 errors, 0 warnings`) to fix all defects B1–B9 and align the ONNX input tensors with their respective Python training pipelines.

---

## 🛡️ Active Hardened Robots (Compiled 0 Errors, 0 Warnings):

### 1. Track 1 : `DerivBoomCrashHFT_v830_Ultimate.mq5` (`.ex5` — 97,810 bytes)
- **Architecture :** High-Frequency Convex Spike Harvester (SELL Crash / BUY Boom) with Enforced EV Gate.
- **Audit Fixes Implemented (B1 to B9) :**
  - **B1 (Static & Dynamic EV Gate Enforced) :** `OpenConvexSpikeProbe()` strictly enforces `if(InpEnableStaticEvGate && !tr.ev_gate_pass) return false;` and `InpEnforcePositivePayoffLock = true`. Because live executable spreads (`SymbolInfoTick`) are 7x to 11x larger than historical `CopyTicks` spreads, the EV gate locks all 10 Boom/Crash symbols when $\text{EV} < \text{InpMinEvUsd}$, preventing certain spread loss under Doob's Optional Stopping Theorem.
  - **B2 (Active AI Filter) :** Removed `MathMax(phys_spike_p0, ...)` clamp and set `InpThetaEffBaseMult = 1.00` so the ONNX filter can genuinely block unfavorable probes.
  - **B3 & B4 (14-Feature ONNX Alignment & Horizon Scaling) :** Aligned the 14 input features with `src/models/onnx_model_metadata.json` (`InpUseZeroCheatFeatures = false`) and scaled 15-tick survival probabilities to the $M^*$ tick horizon via $1 - P_{\text{surv},15}^{M^*/15}$.
  - **B5 (Server Epoch Seconds Time-Stop) :** Replaced `GetTickCount64()` vs `POSITION_TIME_MSC` mismatch with server epoch millisecond/second elapsed time calculation.
  - **B6 (UTC Daily Rollover) :** Tracks daily drawdown from `g_day_start_equity` reset at 00:00 UTC.
  - **B7, B8, B9 (Mathematical Honesty) :** Removed Gambler's Fallacy `calm_maturity_boost`, removed the artificial `0.20 * mean_sp` gain floor, included real spread in time-stop loss estimation, and disabled `InpEnableHawkesClusterEntry` by default.

### 2. Track 2 : `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`.ex5` — 50,054 bytes)
- **Architecture :** Volatility Squeeze & Impulse Breakout (H1) with Aligned 7-Feature C2 ONNX Filter.
- **Audit Fixes Implemented :**
  - **Exact 7-Feature Alignment with `train_volatility_colab.py` and `c2_vol_filter.onnx` :**
    `[vol_ratio, impulse_z, direction, levy_area, spread_to_atr, skew20, kurt20]`.
  - **Real Live Spread Measurement :** Reads live executable spread from `SymbolInfoTick` (`ask - bid`) and computes exact `spread_to_atr = spread_pts / (atr_pts + 1e-8)`.
  - **Generalized Horizon Volatility-Parity Sizing :** Scales 1-hour SD by $\sqrt{\text{InpMaxHoldBars}}$ (`2.0` for 4h, $\sqrt{3}$ for 3h).

### 3. Utility Script : `OpenAuditedCharts.mq5` (`.ex5` — 8,332 bytes)
- Opens and formats M1 charts for the 5 Boom/Crash symbols.

---

## 🏛️ Historical Versions (Preserved Additively for Forensic Audit):
4. `DerivBoomCrashHFT_v8.mq5` (`.ex5`): Initial v8.00 Convex Spike Hunter (logged 648 live trades, -311.20 USD, proving Doob's theorem under live spreads).
5. `DerivBoomCrashHFT_v7.mq5` (`.ex5`): The v7.00 drift harvesting robot (1,242 live trades logged, 85.91% WR, -406.14 USD).
6. `DerivBoomCrashHFT_v6.mq5` (`.ex5`): The v6.00 prototype (258 live trades logged, -68.40 USD).
7. `Deriv_VolSqueeze_Breakout_EA.mq5` (`.ex5`): Initial v1 prototype of the Volatility Squeeze EA.
