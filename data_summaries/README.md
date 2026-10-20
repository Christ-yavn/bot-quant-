# DATA SUMMARIES & EMPIRICAL RUNS

Clean, lightweight CSV datasets summarizing the empirical live runs on MetaTrader 5 account `32449166`:

## `v6/`
* `v6_closed_positions.csv`: 258 round-trip positions executed by v6.00.
* `v6_deals.csv`: 516 individual deal records.
* `v6_orders.csv`: 516 order execution records.
* `v6_equity_curve.csv`: Balance trajectory over time.
* `v6_performance_by_symbol.csv`: Symbol-by-symbol performance matrix.
* `v6_performance_by_close_reason.csv`: PnL by exit trigger.

## `v7/`
* `v7_closed_positions.csv`: 1,242 round-trip positions executed by v7.00.
* `v7_deals.csv`: 2,484 individual deal records.
* `v7_orders.csv`: 2,484 order execution records.
* `equity_curve_v7.csv`: 1,242-trade equity and balance curve.
* `pnl_by_symbol.csv`: Full breakdown for all 7 active symbols.
* `pnl_by_close_reason.csv`: Breakdown by close reason (`GREEN_CASH_IN`, `SERVER_STOP_LOSS`, etc.).
* `reverse_strategy_simulation.csv`: Position-by-position simulation of the user's inverted thesis (+$340.73 net profit).
