# ANALYTICS & FORENSIC SUITE

Diagnostic scripts and data extractors connecting directly to the MetaTrader 5 terminal:

1. `audit_phase0_boom_crash_v6.py`:  
   Statistical scanner validating Hawkes process parameters, testing data leakage, and computing mutual information between input features and target labels.
2. `export_v6_data.py`:  
   High-throughput extraction script that captured all trades, orders, deals, and logs during the v6.00 live run.
3. `export_v7_data.py`:  
   Forensic extraction script that harvested 2,484 deals, 1,242 positions, and terminal logs from the v7.00 session.
4. `simulate_reverse_strategy.py`:  
   Trade-by-trade empirical backtesting script proving the profitability of the Inverted Convex Spike-Hunting strategy ($+\$340.73$ USD).
