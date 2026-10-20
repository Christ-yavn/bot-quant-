"""
src.bot.benchmark_mt5_latency
=============================
Empirical HFT Latency & Execution Architecture Benchmark (Requirement R5).
Measures real IPC, tick-polling, order-check, and network ping latencies
against the local Deriv MT5 terminal (Account 32449166, Deriv-Demo) WITHOUT
submitting any live or demo trade orders.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


def run_mt5_hft_benchmark(n_tick_samples: int = 1000, n_order_checks: int = 200) -> Dict[str, Any]:
    """
    Executes an empirical benchmark on the local MT5 terminal and saves results
    to `data/mt5_latency_benchmark.json`.
    """
    if mt5 is None or not mt5.initialize():
        return {"connected": False, "error": "MT5 initialize failed"}

    term_info = mt5.terminal_info()
    acc_info = mt5.account_info()

    ping_us = int(getattr(term_info, "ping_last", 0))  # MT5 reports ping_last in microseconds
    ping_ms = ping_us / 1000.0

    symbol = "Boom 1000 Index"
    mt5.symbol_select(symbol, True)

    # 1. Benchmark mt5.symbol_info_tick(symbol) IPC latency
    tick_latencies_us = []
    for _ in range(n_tick_samples):
        t0 = time.perf_counter_ns()
        _ = mt5.symbol_info_tick(symbol)
        t1 = time.perf_counter_ns()
        tick_latencies_us.append((t1 - t0) / 1000.0)

    # 2. Benchmark mt5.copy_ticks_from(symbol, ..., 100) IPC batch latency
    batch_latencies_us = []
    now_sec = int(time.time()) - 60
    for _ in range(100):
        t0 = time.perf_counter_ns()
        _ = mt5.copy_ticks_from(symbol, now_sec, 100, mt5.COPY_TICKS_ALL)
        t1 = time.perf_counter_ns()
        batch_latencies_us.append((t1 - t0) / 1000.0)

    # 3. Benchmark mt5.order_check(request) IPC + margin engine latency (ZERO orders sent!)
    tick = mt5.symbol_info_tick(symbol)
    order_check_latencies_us = []
    if tick is not None:
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.20,
            "type": mt5.ORDER_TYPE_SELL,
            "price": float(tick.bid),
            "deviation": 20,
            "magic": 20261018,
            "comment": "BENCHMARK_CHECK_ONLY",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        for _ in range(n_order_checks):
            t0 = time.perf_counter_ns()
            _ = mt5.order_check(req)
            t1 = time.perf_counter_ns()
            order_check_latencies_us.append((t1 - t0) / 1000.0)

    # 4. Benchmark Python pure strategy decision overhead per tick
    strat_latencies_us = []
    last_p = 10000.0
    for i in range(n_tick_samples):
        p = 10000.0 + (i % 5) * 0.016
        t0 = time.perf_counter_ns()
        delta = p - last_p
        _ = delta >= 15.0
        last_p = p
        t1 = time.perf_counter_ns()
        strat_latencies_us.append((t1 - t0) / 1000.0)

    mt5.shutdown()

    def stats_dict(arr_us):
        if not arr_us:
            return {"mean_us": 0.0, "p50_us": 0.0, "p95_us": 0.0, "p99_us": 0.0, "max_us": 0.0}
        a = np.array(arr_us, dtype=np.float64)
        return {
            "mean_us": float(np.mean(a)),
            "p50_us": float(np.median(a)),
            "p95_us": float(np.percentile(a, 95)),
            "p99_us": float(np.percentile(a, 99)),
            "max_us": float(np.max(a)),
            "mean_ms": float(np.mean(a) / 1000.0),
            "p99_ms": float(np.percentile(a, 99) / 1000.0),
        }

    res = {
        "connected": True,
        "account_login": int(getattr(acc_info, "login", 0)),
        "account_server": str(getattr(acc_info, "server", "")),
        "account_balance": float(getattr(acc_info, "balance", 0.0)),
        "account_currency": str(getattr(acc_info, "currency", "USD")),
        "terminal_ping_us": ping_us,
        "terminal_ping_ms": ping_ms,
        "ipc_symbol_info_tick": stats_dict(tick_latencies_us),
        "ipc_copy_ticks_100": stats_dict(batch_latencies_us),
        "ipc_order_check": stats_dict(order_check_latencies_us),
        "python_strategy_step": stats_dict(strat_latencies_us),
    }

    out_path = Path("data/mt5_latency_benchmark.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    return res


if __name__ == "__main__":
    results = run_mt5_hft_benchmark()
    print(json.dumps(results, indent=2))
