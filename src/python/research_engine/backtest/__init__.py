"""
src.backtest
============
Realistic event-driven backtesting engine, Deriv cost structures,
gap slippage execution, portfolio management, and performance metrics.
"""

from src.backtest.costs import (
    DERIV_SPECS,
    SymbolSpec,
    calculate_margin,
    calculate_swap,
    check_position_stops_with_gap_slippage,
    clamp_lot_size,
    execute_market_order_with_gap_slippage,
    execute_order,
)
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import (
    bootstrap_net_expectancy,
    calculate_backtest_metrics,
    calculate_drawdowns,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
)
from src.backtest.portfolio import (
    AccountState,
    FillReport,
    OrderRequest,
    OrderSide,
    OrderType,
    PortfolioState,
    Position,
)

__all__ = [
    # Engine
    "BacktestEngine",
    # Costs & Specifications
    "SymbolSpec",
    "DERIV_SPECS",
    "clamp_lot_size",
    "calculate_margin",
    "calculate_swap",
    "execute_market_order_with_gap_slippage",
    "execute_order",
    "check_position_stops_with_gap_slippage",
    # Portfolio & Orders
    "OrderSide",
    "OrderType",
    "OrderRequest",
    "FillReport",
    "Position",
    "AccountState",
    "PortfolioState",
    # Metrics
    "calculate_backtest_metrics",
    "bootstrap_net_expectancy",
    "calculate_drawdowns",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
]
