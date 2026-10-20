"""
src.bot.logger
==============
Structured JSONL audit logger for trading bot orders, executions,
circuit breaker trips, state changes, and emergency stop events.

Compliant with PROJECT.md §5.E, §6.3, and tests/e2e/contract_harness.py §5 (F15).
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _json_serializable(obj: Any) -> Any:
    """Recursively converts objects (dataclasses, enums, NamedTuples, Paths) to JSON-serializable types."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _json_serializable(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, Path):
        return str(obj)
    elif hasattr(obj, "_asdict"):  # NamedTuple
        return {k: _json_serializable(v) for k, v in obj._asdict().items()}
    elif isinstance(obj, dict):
        return {str(k): _json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_json_serializable(item) for item in obj]
    elif isinstance(obj, float):
        if not (obj == obj):  # NaN check
            return None
        if obj == float("inf") or obj == float("-inf"):
            return str(obj)
        return obj
    return obj


class BotLogger:
    """
    Structured JSONL logger writing audit records to bot_events.jsonl and bot_orders.jsonl.
    Flushes after every write to ensure real-time auditability in production.
    Thread-safe across multiple concurrent caller threads via an internal Lock.
    """

    def __init__(
        self,
        log_dir: Optional[Union[str, Path]] = None,
        events_filename: str = "bot_events.jsonl",
        orders_filename: str = "bot_orders.jsonl",
        unified_log_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.unified_log_path = Path(unified_log_path) if unified_log_path else None
        self._lock = threading.Lock()
        
        if log_dir is not None:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path("logs")

        self.events_path = self.unified_log_path if self.unified_log_path else self.log_dir / events_filename
        self.orders_path = self.unified_log_path if self.unified_log_path else self.log_dir / orders_filename

        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensures parent log directories exist."""
        if self.unified_log_path:
            self.unified_log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, target_path: Path, record: Dict[str, Any]) -> None:
        """Serializes record and appends to target JSONL file with immediate flush (thread-safe)."""
        with self._lock:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                serialized = json.dumps(_json_serializable(record), ensure_ascii=False)
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(serialized + "\n")
                    f.flush()
            except Exception as e:
                # Fallback to standard error to prevent logging crash from breaking trading
                print(f"[BotLogger ERROR] Failed to write log to {target_path}: {e}")

    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        bot_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Logs a general bot event (state transitions, circuit breaker trips, ticks, heartbeats).
        """
        record = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timestamp_ns": time.time_ns(),
            "event_type": event_type,
            "bot_state": bot_state,
            "data": data,
        }
        self._write_jsonl(self.events_path, record)
        return record

    def log_order(
        self,
        order: Any = None,
        status: str = "SUBMITTED",
        details: Optional[Dict[str, Any]] = None,
        bot_state: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Logs an order lifecycle event (SUBMITTED, FILLED, REJECTED, CANCELLED, CLOSED).
        Supports both order object and keyword attributes (e.g. order_id, symbol, side, lots).
        """
        if order is not None:
            order_dict = _json_serializable(order)
            if kwargs:
                if isinstance(order_dict, dict):
                    order_dict.update(_json_serializable(kwargs))
                else:
                    order_dict = {"order": order_dict, **_json_serializable(kwargs)}
        else:
            order_dict = _json_serializable(kwargs)

        record = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timestamp_ns": time.time_ns(),
            "event_type": f"ORDER_{status.upper()}",
            "status": status,
            "bot_state": bot_state,
            "order": order_dict,
            "details": details or {},
        }
        self._write_jsonl(self.orders_path, record)
        return record

    def log_circuit_breaker(
        self,
        breaker_name: str = "",
        reason: str = "",
        account_state: Optional[Any] = None,
        bot_state: Optional[str] = None,
        tripped_breakers: Optional[List[str]] = None,
        current_metrics: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Logs a circuit breaker trip event.
        """
        name = breaker_name or ("; ".join(tripped_breakers) if tripped_breakers else "CIRCUIT_BREAKER")
        trip_reason = reason or name
        metrics = current_metrics if current_metrics is not None else (_json_serializable(account_state) if account_state else None)
        data = {
            "breaker_name": name,
            "reason": trip_reason,
            "account": metrics,
            "tripped_breakers": tripped_breakers or [name],
            **kwargs,
        }
        return self.log_event("CIRCUIT_BREAKER_TRIPPED", data, bot_state=bot_state)

    def log_emergency_stop(
        self,
        reason: str,
        liquidated_positions: int = 0,
        bot_state: Optional[str] = "EMERGENCY_STOPPED",
    ) -> Dict[str, Any]:
        """
        Logs an emergency stop event and liquidation report.
        """
        data = {
            "reason": reason,
            "liquidated_positions": liquidated_positions,
        }
        return self.log_event("EMERGENCY_STOP", data, bot_state=bot_state)
