# MQL5 EXPERT ADVISORS & INFERENCE ENGINES

This directory contains the production Expert Advisors for MetaTrader 5:

## Available Versions:
1. `DerivBoomCrashHFT_v6.mq5` (`.ex5`):  
   The v6.00 engine featuring ONNX brain embedding, Hawkes point process filters, and multi-symbol tracking.
2. `DerivBoomCrashHFT_v7.mq5` (`.ex5`):  
   The state-of-the-art v7.00 engine with **100% Zero-Leakage dynamic Hawkes features**, intra-symbol $Z$-score normalization, Virtual Take-Profit (`req.tp = 0.0`), and spread threshold ceiling ($B \le 115	ext{ ticks}$).

## Compilation & Installation:
1. Copy `*.mq5` into your MetaTrader 5 directory: `MQL5\Experts\`.
2. Copy `boom_crash_meta_brain.onnx` into `MQL5\Files\`.
3. Open MetaEditor 5 and press `F7` to compile.
4. Attach to any chart (`Crash 1000` or `Crash 600` on M1 timeframe). Ensure **Algo Trading** is enabled.
