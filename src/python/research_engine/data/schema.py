"""
src.data.schema
===============
Unified financial tick schemas, serialization contracts, and data cleaning
invariants for Deriv synthetic indices high-frequency quantitative research.

Compliant with PROJECT.md §3.1, §5.A, and tests/e2e/contract_harness.py.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple, TypedDict, Union

import numpy as np
import polars as pl


class TickRecord(NamedTuple):
    """
    Authoritative immutable tick record for event-driven simulation and bots.
    """
    timestamp_ns: int   # UTC epoch in nanoseconds
    symbol: str         # Canonical symbol identifier, e.g. "Boom 1000 Index"
    bid: float          # Best bid price
    ask: float          # Best ask price
    last: float         # Last traded price or quote midpoint (bid + ask) / 2
    volume: float       # Tick volume
    flags: int          # Bitmask flags (MT5 tick flags or provider flags)


class TickRecordDict(TypedDict):
    """Dictionary representation of a tick record for JSON/logging."""
    timestamp_ns: int
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    flags: int


# Canonical Polars Schema for Apache Parquet storage
TICK_SCHEMA: Dict[str, pl.DataType] = {
    "timestamp_ns": pl.Int64,
    "symbol": pl.Utf8,
    "bid": pl.Float64,
    "ask": pl.Float64,
    "last": pl.Float64,
    "volume": pl.Float64,
    "flags": pl.UInt32,
}


def to_tick_record(row: Any) -> TickRecord:
    """
    Converts a Polars row tuple, dict, or namedtuple into a typed TickRecord.
    """
    if isinstance(row, TickRecord):
        return row
    if isinstance(row, dict):
        return TickRecord(
            timestamp_ns=int(row["timestamp_ns"]),
            symbol=str(row["symbol"]),
            bid=float(row["bid"]),
            ask=float(row["ask"]),
            last=float(row.get("last", (float(row["bid"]) + float(row["ask"])) / 2.0)),
            volume=float(row.get("volume", 1.0)),
            flags=int(row.get("flags", 0)),
        )
    # Assume positional tuple (timestamp_ns, symbol, bid, ask, last, volume, flags)
    return TickRecord(
        timestamp_ns=int(row[0]),
        symbol=str(row[1]),
        bid=float(row[2]),
        ask=float(row[3]),
        last=float(row[4]),
        volume=float(row[5]),
        flags=int(row[6]),
    )


def mt5_ticks_to_polars(ticks: np.ndarray, symbol: str) -> pl.DataFrame:
    """
    Converts a NumPy structured array from MT5 copy_ticks_range / copy_ticks_from
    into a standardized Polars DataFrame conforming to TICK_SCHEMA.

    Handles:
    - time_msc (milliseconds epoch) -> timestamp_ns (nanoseconds epoch: * 1_000_000)
    - Midpoint fallback if last <= 0.0 (common in FX/CFD quote ticks)
    - Volume selection from volume_real or volume
    - Column casting to strict schema types
    """
    if ticks is None or len(ticks) == 0:
        return pl.DataFrame(schema=TICK_SCHEMA)

    n = len(ticks)
    # time_msc is int64 milliseconds since epoch
    if "time_msc" in ticks.dtype.names:
        time_msc = ticks["time_msc"].astype(np.int64)
        ts_ns = time_msc * 1_000_000
    else:
        # Fallback to seconds if time_msc absent
        ts_ns = ticks["time"].astype(np.int64) * 1_000_000_000

    bid = ticks["bid"].astype(np.float64)
    ask = ticks["ask"].astype(np.float64)

    # In MT5 quote updates, 'last' is 0.0 unless an actual execution occurred
    if "last" in ticks.dtype.names:
        last = ticks["last"].astype(np.float64)
        zero_mask = last <= 0.0
        if np.any(zero_mask):
            last = np.where(zero_mask, (bid + ask) / 2.0, last)
    else:
        last = (bid + ask) / 2.0

    # Volume: use volume_real if available and positive, else volume, default 1.0
    if "volume_real" in ticks.dtype.names and np.any(ticks["volume_real"] > 0):
        vol = ticks["volume_real"].astype(np.float64)
        vol = np.where(vol <= 0, 1.0, vol)
    elif "volume" in ticks.dtype.names and np.any(ticks["volume"] > 0):
        vol = ticks["volume"].astype(np.float64)
        vol = np.where(vol <= 0, 1.0, vol)
    else:
        vol = np.ones(n, dtype=np.float64)

    # Flags
    if "flags" in ticks.dtype.names:
        flags = ticks["flags"].astype(np.uint32)
    else:
        flags = np.zeros(n, dtype=np.uint32)

    df = pl.DataFrame({
        "timestamp_ns": ts_ns,
        "symbol": [symbol] * n,
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": vol,
        "flags": flags,
    }, schema=TICK_SCHEMA)

    return df


def ws_history_to_polars(
    times: Sequence[int],
    prices: Sequence[float],
    symbol: str,
    spread_pts: float = 0.0,
) -> pl.DataFrame:
    """
    Converts Deriv WebSocket ticks_history response (times in integer seconds,
    single prices array) into a standardized Polars DataFrame conforming to TICK_SCHEMA.

    If spread_pts > 0, reconstructs bid and ask as:
      bid = price - spread_pts / 2.0
      ask = price + spread_pts / 2.0
    Else: bid = ask = last = price.
    """
    n = len(times)
    if n == 0 or len(prices) != n:
        return pl.DataFrame(schema=TICK_SCHEMA)

    ts_arr = np.array(times, dtype=np.int64) * 1_000_000_000
    prices_arr = np.array(prices, dtype=np.float64)

    if spread_pts > 0:
        half_spread = spread_pts / 2.0
        bid_arr = np.round(prices_arr - half_spread, 5)
        ask_arr = np.round(prices_arr + half_spread, 5)
    else:
        bid_arr = prices_arr.copy()
        ask_arr = prices_arr.copy()

    return pl.DataFrame({
        "timestamp_ns": ts_arr,
        "symbol": [symbol] * n,
        "bid": bid_arr,
        "ask": ask_arr,
        "last": prices_arr,
        "volume": np.ones(n, dtype=np.float64),
        "flags": np.full(n, 6, dtype=np.uint32),
    }, schema=TICK_SCHEMA)


def clean_and_validate_ticks(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """
    Strict validation and cleaning engine for ingested ticks (PROJECT.md §3.2, F3).

    Rules:
    1. Positive Price & Coherent Spread: bid > 0, ask >= bid.
    2. Strict Monotonicity & Deduplication: sorted by timestamp_ns, duplicates purged.
    3. Gap Detection: flags timestamps where dt > 5 * median(dt).
    """
    report: Dict[str, Any] = {
        "initial_count": len(df),
        "purged_duplicates": 0,
        "purged_incoherent_spread": 0,
        "gap_warnings": 0,
        "valid": True,
        "final_count": 0,
    }

    if len(df) == 0:
        report["valid"] = False
        return df, report

    # 1. Filter incoherent spread or negative prices
    valid_mask = (pl.col("bid") > 0.0) & (pl.col("ask") >= pl.col("bid"))
    valid_prices = df.filter(valid_mask)
    report["purged_incoherent_spread"] = len(df) - len(valid_prices)

    if len(valid_prices) == 0:
        report["valid"] = False
        return pl.DataFrame(schema=TICK_SCHEMA), report

    # 2. Sort and deduplicate strictly by timestamp_ns
    deduped = valid_prices.sort("timestamp_ns").unique(subset=["timestamp_ns"], keep="last").sort("timestamp_ns")
    report["purged_duplicates"] = len(valid_prices) - len(deduped)

    # 3. Gap Warning Analysis
    if len(deduped) > 2:
        diffs = deduped["timestamp_ns"].diff().drop_nulls()
        median_dt = float(diffs.median()) if len(diffs) > 0 else 0.0
        if median_dt > 0:
            large_gaps = diffs.filter(diffs > 5 * median_dt)
            report["gap_warnings"] = len(large_gaps)

    report["final_count"] = len(deduped)
    return deduped, report


def save_ticks_parquet(df: pl.DataFrame, path: Union[str, Path], compression: str = "zstd") -> Path:
    """
    Persists a ticks Polars DataFrame to Apache Parquet with specified compression.
    Creates parent directories if necessary.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_path, compression=compression)
    return out_path


def load_ticks_parquet(path: Union[str, Path]) -> pl.DataFrame:
    """
    Loads a ticks Parquet file into Polars using multithreaded native Rust engine.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Parquet file not found: {p}")
    return pl.read_parquet(p)
