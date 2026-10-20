"""
src.bot.risk_manager
====================
Pre-trade order validation, exposure limits, margin requirements verification,
and lot size clamping for autonomous Deriv synthetic trading bots.

Compliant with PROJECT.md §5.D, §6.3, and survey_software_arch.md §6.3.
"""

from __future__ import annotations

import copy
from typing import Optional, Tuple

from src.backtest.costs import SymbolSpec, clamp_lot_size
from src.backtest.portfolio import AccountState, OrderRequest, OrderSide
from src.data.schema import TickRecord


class RiskManager:
    """
    Enforces pre-trade risk controls and validation rules:
    - Minimum and maximum lot sizes, volume step clamping (PROJECT.md §5.D)
    - Maximum open position count limits
    - Symbol-level and account-level aggregate lot exposure caps
    - Margin requirement verification with free margin safety buffer
    """

    def __init__(
        self,
        max_open_positions: int = 5,
        max_symbol_lots: float = 10.0,
        max_total_lots: float = 25.0,
        min_free_margin_buffer: float = 5.0,
        enforce_margin_check: bool = True,
    ) -> None:
        self.max_open_positions = max_open_positions
        self.max_symbol_lots = max_symbol_lots
        self.max_total_lots = max_total_lots
        self.min_free_margin_buffer = min_free_margin_buffer
        self.enforce_margin_check = enforce_margin_check

    def validate_order(
        self,
        order: OrderRequest,
        account_state: AccountState,
        tick: Optional[TickRecord],
        spec: SymbolSpec,
    ) -> Tuple[bool, Optional[str], OrderRequest]:
        """
        Validates an order request against risk policies.
        Returns:
            (approved: bool, rejection_reason: Optional[str], adjusted_order: OrderRequest)
        """
        # 1. Closing orders are always approved to facilitate risk reduction/liquidation
        if getattr(order, "action", "OPEN") == "CLOSE" or getattr(order, "close_ticket", None) is not None:
            return True, None, order

        # 2. Maximum open position count check
        current_positions_count = len(account_state.positions)
        if current_positions_count >= self.max_open_positions:
            return (
                False,
                f"MAX_POSITIONS_REACHED: {current_positions_count} >= {self.max_open_positions}",
                order,
            )

        # 3. Lot size clamping according to instrument specification
        clamped_lots = clamp_lot_size(order.lots, spec)
        if clamped_lots <= 0:
            return (
                False,
                f"INVALID_LOT_SIZE: Requested {order.lots} clamped to {clamped_lots}",
                order,
            )

        adjusted_order = copy.copy(order)
        adjusted_order.lots = clamped_lots

        # 4. Symbol-level and aggregate account exposure checks
        current_symbol_lots = sum(
            p.lots for p in account_state.positions.values() if p.symbol == order.symbol
        )
        if (current_symbol_lots + clamped_lots) > self.max_symbol_lots:
            return (
                False,
                f"MAX_SYMBOL_EXPOSURE_EXCEEDED: ({current_symbol_lots:.2f} + {clamped_lots:.2f}) > {self.max_symbol_lots:.2f}",
                adjusted_order,
            )

        current_total_lots = sum(p.lots for p in account_state.positions.values())
        if (current_total_lots + clamped_lots) > self.max_total_lots:
            return (
                False,
                f"MAX_TOTAL_EXPOSURE_EXCEEDED: ({current_total_lots:.2f} + {clamped_lots:.2f}) > {self.max_total_lots:.2f}",
                adjusted_order,
            )

        # 5. Margin requirement & free margin buffer check
        if self.enforce_margin_check and tick is not None:
            price = tick.ask if order.side == OrderSide.BUY else tick.bid
            required_margin = (clamped_lots * spec.contract_size * price) / max(spec.leverage, 1.0)
            
            # If account has balance but no free_margin yet computed, fallback to balance
            available_free_margin = (
                account_state.free_margin
                if account_state.free_margin != 0.0 or len(account_state.positions) > 0
                else account_state.equity
            )

            if (available_free_margin - required_margin) < self.min_free_margin_buffer:
                return (
                    False,
                    f"INSUFFICIENT_FREE_MARGIN: Required {required_margin:.2f}, Free {available_free_margin:.2f}, Buffer {self.min_free_margin_buffer:.2f}",
                    adjusted_order,
                )

        return True, None, adjusted_order
