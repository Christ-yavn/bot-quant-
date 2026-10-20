"""
src.bot.bot_engine
==================
Autonomous trading bot engine coordinating live/simulated tick processing,
state machine lifecycle transitions, strategy order generation, pre-trade risk validation,
and automated circuit breaker emergency stop liquidation.

Compliant with PROJECT.md §5.E, survey_software_arch.md §6.1, and tests/e2e/contract_harness.py §5 (F13, F14, F15).
"""

from __future__ import annotations

import collections
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.backtest.costs import DERIV_SPECS, SymbolSpec
from src.backtest.portfolio import AccountState, OrderRequest, OrderSide
from src.bot.circuit_breakers import CircuitBreakerManager
from src.bot.logger import BotLogger
from src.bot.mt5_adapter import (
    MT5DemoAdapter,
    RealMoneyTradingForbiddenError,
    SafetyLocks,
    SafetyViolationError,
)
from src.bot.paper_adapter import ExecutionAdapter, PaperTradingAdapter
from src.bot.risk_manager import RiskManager
from src.data.schema import TickRecord


class BotMode(str, Enum):
    PAPER = "PAPER"
    DEMO = "DEMO"
    REAL = "REAL"


class BotState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HALTED = "HALTED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


class BotEngine:
    """
    Central Autonomous Trading Bot Engine:
    - Finite State Machine: IDLE, RUNNING, PAUSED, HALTED, EMERGENCY_STOPPED
    - Event loop: tick consumption -> circuit breaker evaluation -> strategy dispatch -> risk check -> execution
    - Dual mode operation: Paper Trading & MT5 Demo execution
    - Triple anti-real-money safety locks
    """

    def __init__(
        self,
        mode: Union[BotMode, str] = BotMode.PAPER,
        strategy: Optional[Any] = None,
        adapter: Optional[ExecutionAdapter] = None,
        risk_manager: Optional[RiskManager] = None,
        circuit_breakers: Optional[CircuitBreakerManager] = None,
        logger: Optional[BotLogger] = None,
        log_path: Optional[Union[str, Path]] = None,
        allow_real_money_config: bool = False,
    ) -> None:
        self.mode = BotMode(mode) if isinstance(mode, str) else mode
        self.allow_real_money_config = allow_real_money_config
        self.state = BotState.IDLE
        self.strategy = strategy

        # In-memory bounded event audit log (matching contract_harness.TradingBot interface)
        self.order_log: collections.deque = collections.deque(maxlen=2000)

        # 1. Enforce Triple Anti-Real-Money Safety Locks
        self._verify_safety_locks()

        # 2. Initialize Logger
        self.log_path = Path(log_path) if log_path else None
        if logger is not None:
            self.logger = logger
        elif self.log_path:
            self.logger = BotLogger(unified_log_path=self.log_path)
        else:
            self.logger = BotLogger()

        # 3. Initialize Execution Adapter
        if adapter is not None:
            self.adapter = adapter
        else:
            if self.mode == BotMode.PAPER:
                self.adapter = PaperTradingAdapter()
            elif self.mode == BotMode.DEMO:
                self.adapter = MT5DemoAdapter(allow_real_money=self.allow_real_money_config)
            else:
                raise SafetyViolationError("REAL money execution adapter not permitted.")

        # Register position close callback if supported
        if hasattr(self.adapter, "set_position_close_callback"):
            self.adapter.set_position_close_callback(self._on_adapter_position_closed)

        # 4. Initialize Risk Controls & Circuit Breakers
        self.risk_manager = risk_manager or RiskManager()
        self.circuit_breakers = circuit_breakers or CircuitBreakerManager()
        self.circuit_breaker_manager = self.circuit_breakers  # alias

        self.logger.log_event(
            "BOT_INITIALIZED",
            {"mode": self.mode.value, "state": self.state.value},
            bot_state=self.state.value,
        )

    def _on_adapter_position_closed(self, fill_info: Dict[str, Any]) -> None:
        """Callback invoked when execution adapter closes a position (e.g. TP, SL, Stop-Out)."""
        self.logger.log_order(
            order_id=fill_info.get("ticket"),
            symbol=fill_info.get("symbol"),
            side="CLOSE",
            lots=fill_info.get("lots"),
            order_type="MARKET",
            fill_price=fill_info.get("exit_price"),
            status="CLOSED",
            fill_time_ns=fill_info.get("timestamp_ns"),
            comment=fill_info.get("reason"),
            bot_state=self.state.value,
        )
        self.log_event("POSITION_CLOSED", fill_info)

    def _verify_safety_locks(self) -> None:
        """
        Enforces triple anti-real-money verification.
        Raises SafetyViolationError if real money execution is attempted.
        """
        if self.mode == BotMode.REAL:
            if not self.allow_real_money_config:
                raise SafetyViolationError("REAL MONEY BLOCKED: config 'allow_real_money' is False.")
            if os.environ.get("DERIV_ALLOW_REAL_MONEY") != "CONFIRMED_I_UNDERSTAND_THE_RISKS":
                raise SafetyViolationError(
                    "REAL MONEY BLOCKED: Required environment confirmation token missing."
                )

    def start(self) -> None:
        """Starts or resumes the bot from IDLE or PAUSED to RUNNING."""
        if self.state == BotState.EMERGENCY_STOPPED:
            raise RuntimeError("Cannot start bot from EMERGENCY_STOPPED state. Re-instantiation required.")
        
        acc = self.adapter.get_account_state()
        self.circuit_breakers.initialize(initial_equity=acc.equity)
        self.state = BotState.RUNNING
        self.log_event("STATE_CHANGED", {"from": "IDLE", "to": "RUNNING", "equity": acc.equity})

    def pause(self) -> None:
        """Pauses bot execution; ignores new trade signals without liquidating positions."""
        if self.state == BotState.RUNNING:
            self.state = BotState.PAUSED
            self.log_event("STATE_CHANGED", {"to": "PAUSED"})

    def resume(self) -> None:
        """Resumes trading from PAUSED to RUNNING."""
        if self.state == BotState.PAUSED:
            self.state = BotState.RUNNING
            self.log_event("STATE_CHANGED", {"to": "RUNNING"})

    def stop(self) -> None:
        """Stops the bot gracefully and returns to IDLE."""
        self.state = BotState.IDLE
        self.log_event("STATE_CHANGED", {"to": "IDLE"})

    def emergency_stop(self, reason: str = "MANUAL_ESTOP") -> None:
        """
        Immediately halts trading, transitions state to EMERGENCY_STOPPED,
        and executes total market liquidation of all open positions.
        """
        self.state = BotState.EMERGENCY_STOPPED
        liquidated_count = self.adapter.close_all_positions()
        self.adapter.emergency_stop()

        event_data = {"reason": reason, "liquidated_positions": liquidated_count}
        self.order_log.append({
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": "EMERGENCY_STOP",
            "bot_state": self.state.value,
            "data": event_data,
        })
        self.logger.log_emergency_stop(
            reason=reason,
            liquidated_positions=liquidated_count,
            bot_state=self.state.value,
        )

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Logs an event both to internal memory buffer and structured JSONL logger."""
        event = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "bot_state": self.state.value,
            "data": data,
        }
        self.order_log.append(event)
        self.logger.log_event(event_type, data, bot_state=self.state.value)

    def on_tick(self, tick: TickRecord) -> Dict[str, Any]:
        """
        Core tick-driven event loop:
        1. Forwards tick to adapter if paper trading
        2. Evaluates bot running state (skips breaker evaluation and strategy if halted/paused/stopped)
        3. Retrieves latest account state snapshot
        4. Evaluates all 5 circuit breakers -> triggers E-STOP if any breaker trips
        5. If RUNNING, triggers strategy -> validates orders with risk manager -> handles close orders or sends approved orders
        """
        # 1. Update adapter pricing
        if hasattr(self.adapter, "on_tick"):
            self.adapter.on_tick(tick)

        # 2. Check running state (Defect 2 fix: must evaluate BEFORE circuit breakers to prevent duplicate e-stop loops)
        if self.state != BotState.RUNNING:
            return {
                "status": "IGNORED",
                "reason": f"Bot is in {self.state.value} state",
                "bot_state": self.state.value,
            }

        # 3. Query portfolio state
        portfolio_state = self.adapter.get_account_state()

        # 4. Evaluate 5 Circuit Breakers
        tripped = self.circuit_breakers.check(tick, portfolio_state)
        if tripped:
            trip_reason = "; ".join(tripped)
            # Log circuit breaker trip to structured logger before emergency stop
            self.logger.log_circuit_breaker(
                tripped_breakers=tripped,
                reason=trip_reason,
                current_metrics={"symbol": tick.symbol, "equity": portfolio_state.equity},
                bot_state=self.state.value,
            )
            self.emergency_stop(reason=trip_reason)
            return {
                "status": "CIRCUIT_BREAKER_TRIPPED",
                "tripped": tripped,
                "bot_state": self.state.value,
            }

        # 5. Evaluate strategy if attached
        orders_submitted: List[Dict[str, Any]] = []
        if self.strategy is not None:
            raw_orders = self.strategy.on_tick(tick, portfolio_state)
            for order in raw_orders:
                spec = DERIV_SPECS.get(order.symbol, DERIV_SPECS["Step Index"])
                approved, rejection_reason, clamped_order = self.risk_manager.validate_order(
                    order=order,
                    account_state=portfolio_state,
                    tick=tick,
                    spec=spec,
                )

                if not approved:
                    self.logger.log_order(
                        order=order,
                        status="REJECTED",
                        details={"reason": rejection_reason},
                        bot_state=self.state.value,
                    )
                    self.log_event("ORDER_REJECTED", {"order": order, "reason": rejection_reason})
                    continue

                # Defect 1 fix: Check for explicit position close orders
                close_ticket = getattr(clamped_order, "close_ticket", None)
                if close_ticket is not None:
                    close_res = self.adapter.close_position(close_ticket)
                    if close_res:
                        self.logger.log_order(
                            order_id=close_ticket,
                            symbol=clamped_order.symbol,
                            side="CLOSE",
                            lots=clamped_order.lots,
                            order_type="MARKET",
                            status="CLOSED",
                            comment=clamped_order.comment or "POSITION_CLOSED",
                            bot_state=self.state.value,
                        )
                        self.log_event("ORDER_CLOSED", {
                            "ticket": close_ticket,
                            "symbol": clamped_order.symbol,
                            "comment": clamped_order.comment,
                        })
                        orders_submitted.append({"ticket": close_ticket, "status": "CLOSED"})
                        # Refresh portfolio_state after filled order
                        portfolio_state = self.adapter.get_account_state()
                    continue
                elif getattr(clamped_order, "action", "OPEN") == "CLOSE":
                    opposing_side = OrderSide.SELL if clamped_order.side == OrderSide.BUY else OrderSide.BUY
                    target_pos = next(
                        (p for p in portfolio_state.positions.values() if p.symbol == clamped_order.symbol and p.side == opposing_side),
                        None,
                    )
                    if target_pos:
                        close_res = self.adapter.close_position(target_pos.ticket)
                        if close_res:
                            self.logger.log_order(
                                order_id=target_pos.ticket,
                                symbol=clamped_order.symbol,
                                side="CLOSE",
                                lots=target_pos.lots,
                                order_type="MARKET",
                                status="CLOSED",
                                comment=clamped_order.comment or "POSITION_CLOSED",
                                bot_state=self.state.value,
                            )
                            self.log_event("ORDER_CLOSED", {
                                "ticket": target_pos.ticket,
                                "symbol": clamped_order.symbol,
                                "comment": clamped_order.comment,
                            })
                            orders_submitted.append({"ticket": target_pos.ticket, "status": "CLOSED"})
                            # Refresh portfolio_state after filled order
                            portfolio_state = self.adapter.get_account_state()
                    continue
                else:
                    # Standard open order flow
                    self.log_event("ORDER_SUBMITTED", {
                        "symbol": clamped_order.symbol,
                        "lots": clamped_order.lots,
                        "side": clamped_order.side.value if hasattr(clamped_order.side, "value") else str(clamped_order.side),
                    })
                    self.logger.log_order(
                        order=clamped_order,
                        status="SUBMITTED",
                        bot_state=self.state.value,
                    )

                    exec_res = self.adapter.send_order(clamped_order)
                    if exec_res.success:
                        self.log_event("ORDER_FILLED", {
                            "ticket": exec_res.ticket,
                            "price": exec_res.fill_price,
                            "lots": exec_res.lots,
                        })
                        self.logger.log_order(
                            order=clamped_order,
                            status="FILLED",
                            details={"ticket": exec_res.ticket, "fill_price": exec_res.fill_price},
                            bot_state=self.state.value,
                        )
                        orders_submitted.append({"ticket": exec_res.ticket, "status": "FILLED"})
                    else:
                        self.log_event("ORDER_FAILED", {"message": exec_res.message})
                        self.logger.log_order(
                            order=clamped_order,
                            status="FAILED",
                            details={"message": exec_res.message},
                            bot_state=self.state.value,
                        )

        # Refresh state after executions
        refreshed_acc = self.adapter.get_account_state()
        return {
            "status": "PROCESSED",
            "bot_state": self.state.value,
            "equity": refreshed_acc.equity,
            "positions_count": len(refreshed_acc.positions),
            "orders_count": len(orders_submitted),
        }


# Authoritative contract alias
TradingBot = BotEngine
