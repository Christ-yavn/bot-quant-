# DERIV SYNTHETIC MARKET MICROSTRUCTURE SPECIFICATION

> [!WARNING]
> **RECTIFICATIF SCIENTIFIQUE POST-AUDIT (25/10/2026) — LIRE [`docs/ETAT_DE_LA_VERITE.md`](ETAT_DE_LA_VERITE.md) EN PREMIER :**
> Ce document historique est intégralement préservé à titre d'archive. Les mesures directes sur 648 trades live v8 ([`forensic_v8_live.py`](../research/audit_2026-10-25/forensic_v8_live.py)) et [`real_live_spreads_mt5.json`](../src/python/colab_ai/real_live_spreads_mt5.json) ont établi les **vrais spreads d'exécution live (`SymbolInfoTick`)** et les vraies vitesses de dérive sur 6,8M ticks :
> - `Boom 1000` : Spread live $= \mathbf{1,7215\text{ pts}}$ ($d = 0,01551\text{ pt/t} \implies 111,0\text{ ticks}$ de breakeven, contre $0,159\text{ pt}$ dans `CopyTicks`).
> - `Crash 1000` : Spread live $= \mathbf{0,5422\text{ pt}}$ ($d = 0,00636\text{ pt/t} \implies 85,3\text{ ticks}$ de breakeven).
> - `Boom 900` : Spread live $= \mathbf{0,9620\text{ pt}}$ ($d = 0,00972\text{ pt/t} \implies 99,0\text{ ticks}$ de breakeven).
> - `Crash 900` : Spread live $= \mathbf{1,3560\text{ pts}}$ ($d = 0,01900\text{ pt/t} \implies 71,4\text{ ticks}$ de breakeven, contre $0,193\text{ pt}$ dans `CopyTicks`).
> - `Boom 600` : Spread live $= \mathbf{0,7730\text{ pt}}$ ($d = 0,00894\text{ pt/t} \implies 86,5\text{ ticks}$ de breakeven).
> - `Crash 600` : Spread live $= \mathbf{3,2810\text{ pts}}$ ($d = 0,03773\text{ pt/t} \implies 87,0\text{ ticks}$ de breakeven, contre $0,297\text{ pt}$ dans `CopyTicks`).
> - `Boom 500` : Spread live $= \mathbf{0,5270\text{ pt}}$ ($d = 0,01128\text{ pt/t} \implies 46,7\text{ ticks}$ de breakeven).
> - `Crash 500` : Spread live $= \mathbf{0,3270\text{ pt}}$ ($d = 0,00623\text{ pt/t} \implies 52,5\text{ ticks}$ de breakeven).

## 1. Tick Stream Dynamics
* **Tick Frequency:** Exactly 1 tick per second on standard series; 1 tick per second on (1s) series.
* **Granularity:** Fixed price increment per tick during calm drift periods:
  * `Crash 600`: $+0.03848$ pts/tick
  * `Crash 900`: $+0.01633$ pts/tick
  * `Crash 1000`: $+0.01168$ pts/tick
  * `Boom 500`: $-0.01160$ pts/tick
  * `Boom 600`: $-0.01358$ pts/tick
  * `Boom 900`: $-0.01025$ pts/tick
  * `Boom 1000`: $-0.00785$ pts/tick

---

## 2. Spread Reality vs Chart Illusion
Retail traders commonly assume that Deriv synthetic indices feature near-zero spreads (2 to 3 points).  
Our empirical telemetry on account `32449166` across 1,242 trades proved that the **real execution spread** in ticks ($S / d$) is substantial:

| Symbol | Real Spread (Points) | Drift per Tick ($d$) | Breakeven Ticks ($B = S/d$) | Spread Filter Status |
| :--- | :---: | :---: | :---: | :---: |
| **Crash 600** | 1.83 pts | 0.03848 | **47.6 ticks** | Passed (Golden 7) |
| **Crash 500** | 1.34 pts | 0.02700 | **49.6 ticks** | Passed (Golden 7) |
| **Boom 500** | 0.58 pts | 0.01160 | **50.0 ticks** | Passed (Golden 7) |
| **Boom 600** | 0.95 pts | 0.01358 | **70.0 ticks** | Passed (Golden 7) |
| **Crash 900** | 1.55 pts | 0.01633 | **94.9 ticks** | Passed (Golden 7) |
| **Crash 1000** | 1.25 pts | 0.01168 | **107.0 ticks** | Passed (Golden 7) |
| **Boom 900** | 1.10 pts | 0.01025 | **107.3 ticks** | Passed (Golden 7) |
| **Boom 1000** | 0.93 pts | 0.00785 | **118.5 ticks** | Rejected (>115t ceiling) |
| **Crash 300** | 2.95 pts | 0.01250 | **236.0 ticks** | Rejected (>115t ceiling) |
| **Boom 300** | 3.10 pts | 0.01180 | **262.7 ticks** | Rejected (>115t ceiling) |

---

## 3. Order Execution & Virtual Take-Profit Mechanics
Under MetaTrader 5 broker constraints, placing hard stop-loss (`req.sl`) or take-profit (`req.tp`) closer than `SYMBOL_TRADE_STOPS_LEVEL` generates catastrophic order rejections:
`trade failed with error [Invalid stops] (error 4756)`.

In Version `v6.00`, this bug generated **162,956 order rejections** overnight.

### The Virtual Take-Profit Solution:
* The Expert Advisor submits orders with `req.tp = 0.0` (completely bypassing broker checks).
* The internal tick engine tracks the floating PnL at every incoming tick ($1000 \text{ ms}$).
* When the net floating gain crosses the threshold ($+\$0.15$ to $+\$0.25$), a memory-managed async close is fired:
  ```cpp
  if(net_floating_usd >= InpTargetProfitUSD) {
      trade.PositionClose(ticket);
  }
  ```
* In Version `v7.00`, this reduced order rejections from **162,956 down to exactly 0**.
