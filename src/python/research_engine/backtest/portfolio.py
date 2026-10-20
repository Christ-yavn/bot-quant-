"""
src.backtest.portfolio
======================
Portfolio models, order types, positions, and account state management
for realistic tick-by-tick simulation of Deriv synthetic indices.

Compliant with PROJECT.md §2.A, §5.C, and tests/e2e/contract_harness.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


@dataclass
class OrderRequest:
    """
    Specification of an order to be submitted into the backtest execution queue.
    Zero-lookahead guarantees execution at next tick (t+1).
    """
    symbol: str
    side: OrderSide
    lots: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    ticket: int = 0
    comment: str = ""
    magic: int = 0
    action: str = "OPEN"
    close_ticket: Optional[int] = None



@dataclass
class FillReport:
    """
    Execution report generated when an order is filled at the market.
    """
    ticket: int
    symbol: str
    side: OrderSide
    lots: float
    fill_price: float
    timestamp_ns: int
    spread_cost: float
    slippage_points: float = 0.0
    status: str = "FILLED"


@dataclass
class Position:
    """
    An active open position in the backtester portfolio.
    Tracks entry, stops, accumulated swaps, and floating PnL.
    """
    ticket: int
    symbol: str
    side: OrderSide
    lots: float
    entry_price: float
    entry_timestamp_ns: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    cumulative_swap: float = 0.0
    comment: str = ""
    magic: int = 0

    def floating_pnl(self, current_bid: float, current_ask: float, contract_size: float) -> float:
        """
        Evaluates floating PnL at immediate market liquidation price:
        - Long (BUY) position liquidates at current Bid.
        - Short (SELL) position liquidates at current Ask.
        """
        if self.side == OrderSide.BUY:
            return self.lots * contract_size * (current_bid - self.entry_price)
        else:
            return self.lots * contract_size * (self.entry_price - current_ask)

    def margin_required(self, price: float, contract_size: float, leverage: float) -> float:
        """
        Calculates required margin for this position given current price.
        """
        return (self.lots * contract_size * price) / leverage


@dataclass
class AccountState:
    """
    Real-time snapshot of the trading account.
    Tracks balance, equity, margin, free margin, margin level %,
    open positions, and historical closed trades.
    """
    balance: float
    equity: float
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level_pct: float = float("inf")
    positions: Dict[int, Position] = field(default_factory=dict)
    closed_trades: List[Dict[str, Any]] = field(default_factory=list)


# Alias for compatibility with PROJECT.md Interface Contract C
PortfolioState = AccountState
