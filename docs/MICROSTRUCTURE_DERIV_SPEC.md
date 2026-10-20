# DERIV SYNTHETIC MARKET MICROSTRUCTURE SPECIFICATION

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
