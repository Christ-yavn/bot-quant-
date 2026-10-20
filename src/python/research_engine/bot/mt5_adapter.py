"""
src.bot.mt5_adapter
===================
MetaTrader 5 Demo execution adapter connecting to Deriv-Demo server (account 32449166),
strictly enforcing Triple Anti-Real-Money Safety Locks.

Compliant with PROJECT.md §5.E, survey_software_arch.md §6.1-§6.2,
and tests/e2e/contract_harness.py §5 (F13, F14).
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.backtest.costs import DERIV_SPECS, SymbolSpec, clamp_lot_size
from src.backtest.portfolio import (
    AccountState,
    OrderRequest,
    OrderSide,
    OrderType,
    Position,
)
from src.bot.paper_adapter import ExecutionAdapter, ExecutionResult

# Attempt to import MetaTrader5; provide fallback if running in headless/mock environment
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class SafetyViolationError(RuntimeError):
    """Raised whenever a safety constraint or anti-real-money lock is violated."""
    pass


class RealMoneyTradingForbiddenError(SafetyViolationError):
    """Raised when any check detects an attempt to execute on real money or non-demo server."""
    pass


ALLOWED_DEMO_SERVERS = ["deriv-demo", "deriv-demo-01"]
DEFAULT_DEMO_LOGIN = 32449166
DEFAULT_DEMO_SERVER = "Deriv-Demo"


class SafetyLocks:
    """
    Triple Anti-Real-Money Protection Locks:
    1. Static configuration check: allow_real_money must be False by default.
    2. Environment token verification: DERIV_ALLOW_REAL_MONEY == 'CONFIRMED_I_UNDERSTAND_THE_RISKS'.
    3. Hardware server & account trade mode whitelist: server must be in ALLOWED_DEMO_SERVERS
       and account.trade_mode must strictly be DEMO (0).
    """

    @staticmethod
    def verify(
        server: str,
        login: int,
        allow_real_money: bool = False,
        trade_mode: Optional[int] = None,
    ) -> None:
        """
        Validates the triple safety locks.
        Raises RealMoneyTradingForbiddenError if any check fails.
        """
        # Lock 1: Config flag check
        if allow_real_money is False:
            pass  # Normal safe demo mode
        else:
            # If user explicitly configured allow_real_money = True, require env confirmation token
            env_token = os.environ.get("DERIV_ALLOW_REAL_MONEY")
            if env_token != "CONFIRMED_I_UNDERSTAND_THE_RISKS":
                raise RealMoneyTradingForbiddenError(
                    "REAL MONEY BLOCKED: Required environment confirmation token missing "
                    "(DERIV_ALLOW_REAL_MONEY != 'CONFIRMED_I_UNDERSTAND_THE_RISKS')."
                )

        # Lock 2: Server whitelist check
        normalized_server = (server or "").strip().lower()
        if not any(normalized_server == allowed for allowed in ALLOWED_DEMO_SERVERS):
            raise RealMoneyTradingForbiddenError(
                f"REAL MONEY BLOCKED: Server '{server}' is not in allowed demo whitelist {ALLOWED_DEMO_SERVERS}. "
                "Trading on live/real Deriv servers is strictly forbidden."
            )

        # Lock 3: Account Trade Mode check (0 = Demo in MT5, 1 = Contest, 2 = Real)
        if trade_mode is not None:
            # mt5.ACCOUNT_TRADE_MODE_DEMO is 0
            if trade_mode != 0:
                raise RealMoneyTradingForbiddenError(
                    f"REAL MONEY BLOCKED: Account trade_mode is {trade_mode} (expected 0 for DEMO). "
                    "Live money accounts are physically prohibited."
                )


class MT5DemoAdapter(ExecutionAdapter):
    """
    Execution Adapter communicating with MetaTrader 5 terminal connected
    to Deriv demo account on server 'Deriv-Demo'.
    """

    def __init__(
        self,
        login: int = DEFAULT_DEMO_LOGIN,
        server: str = DEFAULT_DEMO_SERVER,
        password: Optional[str] = None,
        path: Optional[str] = None,
        allow_real_money: bool = False,
        mock_mode: bool = False,
    ) -> None:
        self.login = login
        self.server = server
        self.password = password
        self.path = path
        self.allow_real_money = allow_real_money
        self.mock_mode = mock_mode or not MT5_AVAILABLE
        self.is_connected: bool = False
        self.is_stopped: bool = False

        # Internal state for mock_mode (or when testing offline)
        self._mock_balance = 10000.0
        self._mock_positions: Dict[int, Position] = {}
        self._mock_ticket = 50000

        # Enforce safety locks immediately upon instantiation
        SafetyLocks.verify(
            server=self.server,
            login=self.login,
            allow_real_money=self.allow_real_money,
            trade_mode=0 if self.mock_mode else None,
        )

        self._position_close_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_position_close_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback hook invoked when an MT5 position is closed."""
        self._position_close_callback = callback

    def connect(self) -> bool:
        """Initializes connection to MT5 terminal and verifies safety locks on live session."""
        if self.mock_mode:
            self.is_connected = True
            return True

        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 python package is not available on this system.")

        init_kwargs = {}
        if self.path:
            init_kwargs["path"] = self.path
        if not mt5.initialize(**init_kwargs):
            raise ConnectionError(f"mt5.initialize() failed: {mt5.last_error()}")

        if self.login and self.server:
            login_kwargs = {"login": self.login, "server": self.server}
            if self.password:
                login_kwargs["password"] = self.password
            if not mt5.login(**login_kwargs):
                mt5.shutdown()
                raise ConnectionError(f"mt5.login() failed: {mt5.last_error()}")

        # Inspect account info directly from terminal
        acc_info = mt5.account_info()
        if acc_info is None:
            mt5.shutdown()
            raise ConnectionError(f"mt5.account_info() returned None: {mt5.last_error()}")

        # Verify Lock 2 & Lock 3 with live hardware account info
        SafetyLocks.verify(
            server=acc_info.server,
            login=acc_info.login,
            allow_real_money=self.allow_real_money,
            trade_mode=acc_info.trade_mode,
        )

        self.is_connected = True
        return True

    def disconnect(self) -> None:
        """Disconnects and shuts down MT5 terminal connection."""
        if not self.mock_mode and MT5_AVAILABLE:
            mt5.shutdown()
        self.is_connected = False

    def send_order(self, order: OrderRequest) -> ExecutionResult:
        """
        Sends an order to MT5 using mt5.order_send (or mock execution).
        Supports explicit position closing via close_ticket or action='CLOSE'.
        """
        if self.is_stopped:
            return ExecutionResult(
                ticket=0,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=order.lots,
                message="Adapter is EMERGENCY_STOPPED. Order refused.",
            )

        # 1. Explicit close order handling
        close_ticket = getattr(order, "close_ticket", None)
        if close_ticket is not None:
            closed = self.close_position(close_ticket)
            return ExecutionResult(
                ticket=close_ticket,
                order_id=close_ticket,
                success=closed,
                status="CLOSED" if closed else "REJECTED",
                fill_price=order.price or 0.0,
                lots=order.lots,
                message="MT5 Demo position closed by ticket" if closed else "MT5 Demo close position failed",
            )
        elif getattr(order, "action", "OPEN") == "CLOSE":
            state = self.get_account_state()
            opposing_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
            target_pos = next(
                (p for p in state.positions.values() if p.symbol == order.symbol and p.side == opposing_side),
                None,
            )
            if target_pos:
                closed = self.close_position(target_pos.ticket)
                return ExecutionResult(
                    ticket=target_pos.ticket,
                    order_id=target_pos.ticket,
                    success=closed,
                    status="CLOSED" if closed else "REJECTED",
                    fill_price=order.price or 0.0,
                    lots=target_pos.lots,
                    message="MT5 Demo position closed by opposing action" if closed else "MT5 Demo close failed",
                )
            else:
                return ExecutionResult(
                    ticket=0,
                    order_id=0,
                    success=False,
                    status="REJECTED",
                    fill_price=0.0,
                    lots=order.lots,
                    message="Target MT5 position to close not found",
                )

        spec = DERIV_SPECS.get(order.symbol, DERIV_SPECS["Step Index"])
        clamped_lots = clamp_lot_size(order.lots, spec)

        if self.mock_mode:
            self._mock_ticket += 1
            ticket = self._mock_ticket
            price = order.price or (1000.1 if order.side == OrderSide.BUY else 1000.0)
            pos = Position(
                ticket=ticket,
                symbol=order.symbol,
                side=order.side,
                lots=clamped_lots,
                entry_price=price,
                entry_timestamp_ns=0,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                comment=order.comment,
                magic=order.magic,
            )
            self._mock_positions[ticket] = pos
            return ExecutionResult(
                ticket=ticket,
                order_id=ticket,
                success=True,
                status="FILLED",
                fill_price=price,
                lots=clamped_lots,
                message="Mock MT5 Demo order filled",
            )

        if not self.is_connected:
            self.connect()

        tick = mt5.symbol_info_tick(order.symbol)
        if tick is None:
            return ExecutionResult(
                ticket=0,
                order_id=0,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=clamped_lots,
                message=f"Symbol {order.symbol} tick unavailable",
                error_code=mt5.last_error()[0] if MT5_AVAILABLE else -1,
            )

        mt5_order_type = (
            mt5.ORDER_TYPE_BUY if order.side == OrderSide.BUY else mt5.ORDER_TYPE_SELL
        )
        price = tick.ask if order.side == OrderSide.BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": clamped_lots,
            "type": mt5_order_type,
            "price": price,
            "deviation": 20,
            "magic": order.magic or 123456,
            "comment": order.comment or "DerivBot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        if order.stop_loss:
            request["sl"] = order.stop_loss
        if order.take_profit:
            request["tp"] = order.take_profit

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = result.retcode if result else -1
            comment = result.comment if result else str(mt5.last_error())
            return ExecutionResult(
                ticket=0,
                order_id=0,
                success=False,
                status="REJECTED",
                fill_price=0.0,
                lots=clamped_lots,
                message=f"MT5 order_send rejected: {comment} (retcode: {retcode})",
                error_code=retcode,
            )

        return ExecutionResult(
            ticket=result.order,
            order_id=result.order,
            success=True,
            status="FILLED",
            fill_price=result.price,
            lots=result.volume,
            message="MT5 order_send success",
        )

    def close_position(self, ticket: int) -> bool:
        """Closes a specific MT5 position by ticket."""
        if self.mock_mode:
            pos = self._mock_positions.pop(ticket, None)
            if pos and self._position_close_callback is not None:
                try:
                    self._position_close_callback({
                        "ticket": ticket,
                        "symbol": pos.symbol,
                        "side": pos.side.value if hasattr(pos.side, "value") else str(pos.side),
                        "lots": pos.lots,
                        "exit_price": pos.entry_price,
                        "reason": "MANUAL_CLOSE",
                        "timestamp_ns": 0,
                        "pnl": 0.0,
                    })
                except Exception as e:
                    print(f"[MT5DemoAdapter ERROR] close callback failed: {e}")
            return pos is not None

        if not self.is_connected:
            self.connect()

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False

        pos = positions[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return False

        close_type = (
            mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        )
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Close Position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(request)
        success = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
        if success and self._position_close_callback is not None:
            try:
                self._position_close_callback({
                    "ticket": ticket,
                    "symbol": pos.symbol,
                    "side": pos.side.value if hasattr(pos.side, "value") else str(pos.side),
                    "lots": pos.volume,
                    "exit_price": price,
                    "reason": "MT5_POSITION_CLOSED",
                    "timestamp_ns": 0,
                    "pnl": 0.0,
                })
            except Exception as e:
                print(f"[MT5DemoAdapter ERROR] close callback failed: {e}")
        return success

    def close_all_positions(self) -> int:
        """Liquidates all open positions immediately."""
        if self.mock_mode:
            count = len(self._mock_positions)
            self._mock_positions.clear()
            return count

        if not self.is_connected:
            self.connect()

        positions = mt5.positions_get()
        if not positions:
            return 0

        closed_count = 0
        for pos in positions:
            if self.close_position(pos.ticket):
                closed_count += 1
        return closed_count

    def emergency_stop(self) -> None:
        """Emergency stop: closes all positions and sets stop flag."""
        self.is_stopped = True
        self.close_all_positions()

    def get_account_state(self) -> AccountState:
        """Returns account state from MT5."""
        if self.mock_mode:
            return AccountState(
                balance=self._mock_balance,
                equity=self._mock_balance,
                margin=0.0,
                free_margin=self._mock_balance,
                margin_level_pct=float("inf"),
                positions=dict(self._mock_positions),
                closed_trades=[],
            )

        if not self.is_connected:
            self.connect()

        acc_info = mt5.account_info()
        if acc_info is None:
            raise ConnectionError("mt5.account_info() returned None")

        positions_raw = mt5.positions_get() or ()
        positions_dict: Dict[int, Position] = {}
        for p in positions_raw:
            side = OrderSide.BUY if p.type == mt5.ORDER_TYPE_BUY else OrderSide.SELL
            positions_dict[p.ticket] = Position(
                ticket=p.ticket,
                symbol=p.symbol,
                side=side,
                lots=p.volume,
                entry_price=p.price_open,
                entry_timestamp_ns=p.time_msc * 1_000_000,
                stop_loss=p.sl if p.sl > 0 else None,
                take_profit=p.tp if p.tp > 0 else None,
                comment=p.comment,
                magic=p.magic,
            )

        margin_level = acc_info.margin_level if acc_info.margin > 0 else float("inf")
        return AccountState(
            balance=acc_info.balance,
            equity=acc_info.equity,
            margin=acc_info.margin,
            free_margin=acc_info.margin_free,
            margin_level_pct=margin_level,
            positions=positions_dict,
            closed_trades=[],
        )
