"""
src.backtest.costs
==================
Deriv synthetic indices cost models, margin calculations, lot size clamping,
overnight swaps, and gap slippage execution physics.

Compliant with PROJECT.md §2.A, §5.D, and survey_software_arch.md §5.2-§5.4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.backtest.portfolio import FillReport, OrderRequest, OrderSide, Position
from src.data.schema import TickRecord


@dataclass(frozen=True)
class SymbolSpec:
    """
    Authoritative trading specification for a Deriv synthetic index instrument.
    """
    symbol: str
    category: str
    digits: int
    point: float
    spread_points: float
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    swap_long: float
    swap_short: float
    leverage: float = 100.0
    stop_out_level: float = 0.50  # 50% equity / margin threshold


# Authoritative Deriv Synthetic Specifications extracted from MT5 terminal specs
DERIV_SPECS: Dict[str, SymbolSpec] = {
    "Step Index": SymbolSpec(
        symbol="Step Index",
        category="Step Indices",
        digits=1,
        point=0.1,
        spread_points=1.0,
        contract_size=10.0,
        volume_min=0.10,
        volume_max=100.0,
        volume_step=0.01,
        swap_long=-1.0,
        swap_short=-1.0,
        leverage=100.0,
        stop_out_level=0.50,
    ),
    "Boom 1000 Index": SymbolSpec(
        symbol="Boom 1000 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=1190.0,  # ~1.19 points
        contract_size=1.0,
        volume_min=0.20,
        volume_max=50.0,
        volume_step=0.01,
        swap_long=-1.0,
        swap_short=-1.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Crash 1000 Index": SymbolSpec(
        symbol="Crash 1000 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=1190.0,
        contract_size=1.0,
        volume_min=0.20,
        volume_max=50.0,
        volume_step=0.01,
        swap_long=-1.0,
        swap_short=-1.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Volatility 75 Index": SymbolSpec(
        symbol="Volatility 75 Index",
        category="Continuous Indices",
        digits=4,
        point=0.0001,
        spread_points=5000.0,
        contract_size=1.0,
        volume_min=0.001,
        volume_max=100.0,
        volume_step=0.001,
        swap_long=-5.0,
        swap_short=-5.0,
        leverage=100.0,
        stop_out_level=0.50,
    ),
    "Jump 10 Index": SymbolSpec(
        symbol="Jump 10 Index",
        category="Jump Indices",
        digits=4,
        point=0.0001,
        spread_points=3000.0,
        contract_size=1.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        swap_long=-2.0,
        swap_short=-2.0,
        leverage=100.0,
        stop_out_level=0.50,
    ),
    "Range Break 100 Index": SymbolSpec(
        symbol="Range Break 100 Index",
        category="Range Break Indices",
        digits=2,
        point=0.01,
        spread_points=20.0,
        contract_size=1.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        swap_long=-1.5,
        swap_short=-1.5,
        leverage=100.0,
        stop_out_level=0.50,
    ),
    "DEX 900 DOWN Index": SymbolSpec(
        symbol="DEX 900 DOWN Index",
        category="DEX Indices",
        digits=4,
        point=0.0001,
        spread_points=1000.0,
        contract_size=1.0,
        volume_min=0.01,
        volume_max=50.0,
        volume_step=0.01,
        swap_long=-1.0,
        swap_short=-1.0,
        leverage=100.0,
        stop_out_level=0.50,
    ),
    "Boom 900 Index": SymbolSpec(
        symbol="Boom 900 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=95.0,  # ~0.095 points empirical
        contract_size=1.0,
        volume_min=0.20,
        volume_max=135.0,
        volume_step=0.01,
        swap_long=-32.0,
        swap_short=-32.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Crash 900 Index": SymbolSpec(
        symbol="Crash 900 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=184.0,  # ~0.184 points empirical
        contract_size=1.0,
        volume_min=0.20,
        volume_max=80.0,
        volume_step=0.01,
        swap_long=-16.0,
        swap_short=-16.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Boom 600 Index": SymbolSpec(
        symbol="Boom 600 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=69.0,  # ~0.069 points empirical
        contract_size=1.0,
        volume_min=0.20,
        volume_max=175.0,
        volume_step=0.01,
        swap_long=-36.0,
        swap_short=-36.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Crash 600 Index": SymbolSpec(
        symbol="Crash 600 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=304.0,  # ~0.304 points empirical
        contract_size=1.0,
        volume_min=0.20,
        volume_max=55.0,
        volume_step=0.01,
        swap_long=-36.0,
        swap_short=-36.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Boom 500 Index": SymbolSpec(
        symbol="Boom 500 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=80.0,
        contract_size=1.0,
        volume_min=0.20,
        volume_max=190.0,
        volume_step=0.01,
        swap_long=-23.0,
        swap_short=-23.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Crash 500 Index": SymbolSpec(
        symbol="Crash 500 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=42.0,
        contract_size=1.0,
        volume_min=0.20,
        volume_max=290.0,
        volume_step=0.01,
        swap_long=-46.0,
        swap_short=-46.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Boom 300 Index": SymbolSpec(
        symbol="Boom 300 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=25.0,  # ~0.025 points empirical
        contract_size=1.0,
        volume_min=0.50,
        volume_max=150.0,
        volume_step=0.01,
        swap_long=-36.0,
        swap_short=-36.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
    "Crash 300 Index": SymbolSpec(
        symbol="Crash 300 Index",
        category="Crash/Boom",
        digits=3,
        point=0.001,
        spread_points=125.0,  # ~0.125 points empirical
        contract_size=1.0,
        volume_min=0.50,
        volume_max=230.0,
        volume_step=0.01,
        swap_long=-72.0,
        swap_short=-72.0,
        leverage=1000.0,
        stop_out_level=0.50,
    ),
}


def clamp_lot_size(lots: float, spec: SymbolSpec) -> float:
    """
    Clamps lot size to [volume_min, volume_max] and rounds down to nearest volume_step.
    
    Formula:
        Lots_adj = RoundDown(max(VolumeMin, min(VolumeMax, Lots)), VolumeStep)
    """
    if lots < spec.volume_min:
        return spec.volume_min
    if lots > spec.volume_max:
        lots = spec.volume_max
    steps = math.floor(lots / spec.volume_step + 1e-9)
    return round(steps * spec.volume_step, 4)


def calculate_margin(lots: float, price: float, spec: SymbolSpec) -> float:
    """
    Calculates required margin for a given lot size and price.
    
    Formula:
        Margin = (Lots * ContractSize * Price) / Leverage
    """
    return (lots * spec.contract_size * price) / spec.leverage


def calculate_swap(lots: float, side: OrderSide, spec: SymbolSpec, n_days: float = 1.0) -> float:
    """
    Calculates overnight financing swap fees according to official MT5 / Deriv formulas:
        Swap = Lots * ContractSize * SwapRate * Point * n_days
    """
    rate = spec.swap_long if side == OrderSide.BUY else spec.swap_short
    return lots * spec.contract_size * rate * spec.point * n_days


def execute_market_order_with_gap_slippage(
    order: OrderRequest,
    next_tick: TickRecord,
    spec: SymbolSpec,
) -> FillReport:
    """
    Executes a market order at next tick (t+1) with realistic bid/ask spread:
    - BUY executes at next_tick.ask
    - SELL executes at next_tick.bid
    - Volume is strictly clamped to broker min/step constraints.
    - Spread cost is recorded.
    """
    clamped_lots = clamp_lot_size(order.lots, spec)
    if order.side == OrderSide.BUY:
        fill_price = next_tick.ask
    else:
        fill_price = next_tick.bid

    spread_cost = clamped_lots * spec.contract_size * (next_tick.ask - next_tick.bid)
    return FillReport(
        ticket=order.ticket,
        symbol=order.symbol,
        side=order.side,
        lots=clamped_lots,
        fill_price=fill_price,
        timestamp_ns=next_tick.timestamp_ns,
        spread_cost=spread_cost,
    )


def execute_order(
    order: OrderRequest,
    current_tick: Optional[TickRecord],
    next_tick: TickRecord,
    symbol_spec: SymbolSpec,
) -> FillReport:
    """
    Interface Contract D adapter (PROJECT.md §5.D).
    Executes order at next tick with realistic spread and gap slippage.
    """
    return execute_market_order_with_gap_slippage(order, next_tick, symbol_spec)


def check_position_stops_with_gap_slippage(
    pos: Position,
    next_tick: TickRecord,
    spec: SymbolSpec,
) -> Optional[Tuple[float, str]]:
    """
    Enforces Deriv Gap Slippage Physics (PROJECT.md §5.3, F10):
    If Stop-Loss is crossed by a price jump/spike:
    - For Long (BUY) with SL: if next_tick.bid <= pos.stop_loss,
      fill_price = min(pos.stop_loss, next_tick.bid) (Executed at actual market price post-spike, NOT SL!).
    - For Long (BUY) with TP: if next_tick.bid >= pos.take_profit,
      fill_price = max(pos.take_profit, next_tick.bid).
    - For Short (SELL) with SL: if next_tick.ask >= pos.stop_loss,
      fill_price = max(pos.stop_loss, next_tick.ask) (Executed at actual market price post-spike, NOT SL!).
    - For Short (SELL) with TP: if next_tick.ask <= pos.take_profit,
      fill_price = min(pos.take_profit, next_tick.ask).
    
    Returns:
        Tuple of (fill_price, reason) where reason in ("STOP_LOSS", "TAKE_PROFIT"), or None if no stop hit.
    """
    tol = 1e-7
    if pos.side == OrderSide.BUY:
        # Long position liquidates at Bid
        if pos.stop_loss is not None and next_tick.bid <= pos.stop_loss + tol:
            fill_price = min(pos.stop_loss, next_tick.bid)
            return fill_price, "STOP_LOSS"
        if pos.take_profit is not None and next_tick.bid >= pos.take_profit - tol:
            fill_price = max(pos.take_profit, next_tick.bid)
            return fill_price, "TAKE_PROFIT"
    else:
        # Short position liquidates at Ask
        if pos.stop_loss is not None and next_tick.ask >= pos.stop_loss - tol:
            fill_price = max(pos.stop_loss, next_tick.ask)
            return fill_price, "STOP_LOSS"
        if pos.take_profit is not None and next_tick.ask <= pos.take_profit + tol:
            fill_price = min(pos.take_profit, next_tick.ask)
            return fill_price, "TAKE_PROFIT"
    return None
