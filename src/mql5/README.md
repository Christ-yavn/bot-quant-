# MQL5 EXPERT ADVISORS & PRODUCTION INFERENCE ENGINES

This directory contains the production Expert Advisors (EAs) and scripts for MetaTrader 5 on Deriv synthetic indices:

---

## 🚀 Production Robots (Compiled & Certified):

### 1. Track 1 : `DerivBoomCrashHFT_v8.mq5` (`.ex5` — 116,606 bytes)
- **Architecture :** High-Frequency Convex Spike Hunter (Positive Skewness Engine).
- **Core Strategy :** Implements Charlie Munger's INVERT methodology on the forensic v7 dataset:
  - Crash Index : **SELL** (Harvesting descending spikes $\sim \text{Exp}(1/\bar{A})$).
  - Boom Index : **BUY** (Harvesting ascending spikes).
- **Stops & Execution Mechanics :**
  - Instant server-side Take-Profit: $p_{\text{entry}} \pm (k_{\text{TP}} \cdot \bar{A})$.
  - Guaranteed broker stop distance ($M_{\min} \ge \text{stops\_level} + 5\text{ points}$).
  - Strict analytical time stop $M^* = 60\text{ ticks}$.
  - Real-time tick watchdog: closes position instantly upon spike detection.
  - Zero order rejections (`10016 : Invalid stops` completely eliminated via live tick sampling).
- **Quality Gates :** Calibrated priors, dynamic Hawkes rate, Kelly fractional position sizing, daily equity reset at 00:00 UTC.

### 2. Track 2 : `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`.ex5` — 49,438 bytes)
- **Architecture :** Volatility Squeeze & Impulse Breakout with C2 Machine Learning ONNX Filter.
- **Certified Asset :** `Volatility 25 (1s) Index` (H1 Timeframe, certified via Sentinel C1).
- **Features :**
  - Real broker spread reader per bar (`SymbolInfoInteger`).
  - Rolling volatility window ($N=20$), 100-bar bandwidth squeeze quantile filter ($q=0.25$).
  - Real-time ONNX inference (`c2_vol_filter.onnx`) utilizing Lévy area signatures (Rough Paths theory), impulse z-score, skewness, and kurtosis.
  - 4-Hour non-overlapping holding horizon ($M=4$).
  - Dynamic volatility-parity position sizing.

### 3. Utility Script : `OpenAuditedCharts.mq5` (`.ex5` — 10,724 bytes)
- Automatically opens and formats M1 charts for all 5 audited v8.10/v8.22 symbols:
  `Crash 600 Index`, `Crash 900 Index`, `Boom 900 Index`, `Boom 600 Index`, `Crash 1000 Index`.

---

## 🏛️ Historical Versions (Archived for Forensic Audit):
4. `DerivBoomCrashHFT_v7.mq5` (`.ex5`): The v7.00 zero-leakage drift harvesting robot (1,242 trades logged).
5. `DerivBoomCrashHFT_v6.mq5` (`.ex5`): The v6.00 prototype featuring Hawkes filters and ONNX brain embedding.
6. `Deriv_VolSqueeze_Breakout_EA.mq5` (`.ex5`): Initial unconstrained prototype of the Volatility Squeeze EA.

---

## 🛠️ Compilation & Installation Protocol:
1. Copy `DerivBoomCrashHFT_v8.mq5` and `Deriv_VolSqueeze_Breakout_EA_v3.mq5` to `MQL5\Experts\`.
2. Copy `c2_vol_filter.onnx` and `boom_crash_meta_brain.onnx` to `MQL5\Files\`.
3. Open MetaEditor 64 and press `F7` (or execute via CLI `metaeditor64.exe /compile:...`).
4. Result: **0 errors, 0 warnings**.
