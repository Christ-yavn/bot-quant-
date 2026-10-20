"""
src.data.validator
==================
Strict data quality rules, schema assertion gates, family classification,
and Parquet file verification for Deriv synthetic indices tick datasets.

Compliant with PROJECT.md §3.2, test_spec_data.md, and contractual quality gates.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import polars as pl

from src.data.schema import TICK_SCHEMA

EXPECTED_TICK_COLUMNS: List[str] = [
    "timestamp_ns",
    "symbol",
    "bid",
    "ask",
    "last",
    "volume",
    "flags",
]


# ============================================================================
# Domain Exceptions
# ============================================================================

class DataQualityError(Exception):
    """Base exception for data quality and integrity violations."""
    pass


class SchemaValidationError(DataQualityError):
    """Raised when columns or data types do not conform to TICK_SCHEMA."""
    pass


class MonotonicityError(DataQualityError):
    """Raised when timestamps flow backwards or fail strict monotonicity."""
    pass


class PriceSanityError(DataQualityError):
    """Raised when price values are negative, non-finite, or spread is crossed."""
    pass


class CrossedMarketError(PriceSanityError):
    """Raised when bid > ask (inverted/crossed spread)."""
    pass


class InsufficientTicksError(DataQualityError):
    """Raised when dataset contains fewer than 1,000,000 ticks."""
    pass


class InsufficientFamilyDiversityError(DataQualityError):
    """Raised when saved datasets span fewer than 6 distinct index families."""
    pass


class CorruptedParquetError(DataQualityError):
    """Raised when a parquet file is truncated or has invalid magic headers."""
    pass


class EmptyDatasetError(DataQualityError):
    """Raised when a dataset file is zero bytes or has zero records."""
    pass


# ============================================================================
# Synthetic Family Taxonomy
# ============================================================================

@unique
class SyntheticFamily(Enum):
    CRASH_BOOM = "Crash Boom Indices"
    VOLATILITY_STANDARD = "Volatility Indices"
    VOLATILITY_1S = "Volatility (1s) Indices"
    STEP = "Step Indices"
    JUMP = "Jump Indices"
    DEX = "DEX Indices"
    DRIFT_SWITCHING = "Drift Switching Indices"
    RANGE_BREAK = "Range Break Indices"


def classify_family(symbol: str) -> SyntheticFamily:
    """
    Classifies a Deriv synthetic symbol into its canonical family.
    Supports both MT5 full display names and Deriv WebSocket short symbols.
    """
    upper = symbol.strip().upper()

    if "RANGE BREAK" in upper or upper.startswith("RBD") or "RANGEBREAK" in upper:
        return SyntheticFamily.RANGE_BREAK
    elif "DRIFT SWITCH" in upper or "DRIFTSWITCH" in upper or upper.startswith("DSI"):
        return SyntheticFamily.DRIFT_SWITCHING
    elif "BOOM" in upper or "CRASH" in upper:
        return SyntheticFamily.CRASH_BOOM
    elif "STEP" in upper or upper.startswith("STPRNG"):
        return SyntheticFamily.STEP
    elif "JUMP" in upper or re.match(r"^JD\d+", upper):
        return SyntheticFamily.JUMP
    elif re.search(r"\bDEX\b", upper) or upper.startswith("DEX"):
        return SyntheticFamily.DEX
    elif "(1S)" in upper or "1S" in upper or re.match(r"^1HZ\d+V", upper):
        return SyntheticFamily.VOLATILITY_1S
    elif "VOLATILITY" in upper or re.match(r"^R_\d+", upper):
        return SyntheticFamily.VOLATILITY_STANDARD
    else:
        raise ValueError(f"Unrecognized synthetic instrument family for symbol: {symbol}")


# ============================================================================
# Quality Gate Functions
# ============================================================================

def validate_schema(df: pl.DataFrame) -> None:
    """
    Validates exact column names, ordering, strict data types, and null/NaN absence.
    Raises SchemaValidationError or DataQualityError upon violation.
    """
    actual_cols = df.columns
    if actual_cols != EXPECTED_TICK_COLUMNS:
        missing = set(EXPECTED_TICK_COLUMNS) - set(actual_cols)
        unexpected = set(actual_cols) - set(EXPECTED_TICK_COLUMNS)
        raise SchemaValidationError(
            f"Schema column mismatch. Expected: {EXPECTED_TICK_COLUMNS}. "
            f"Actual: {actual_cols}. Missing: {missing}. Unexpected: {unexpected}"
        )

    for col, expected_type in TICK_SCHEMA.items():
        actual_type = df.schema[col]
        # Allow pl.String as alias for pl.Utf8, and pl.Int64/pl.UInt64 for flags if unsigned uint32 not exact
        if actual_type != expected_type:
            if col == "symbol" and actual_type in (pl.Utf8, pl.String):
                continue
            if col == "flags" and actual_type in (pl.UInt32, pl.Int64, pl.UInt64):
                continue
            raise SchemaValidationError(
                f"Column '{col}' has invalid data type {actual_type}. Expected {expected_type}."
            )

    # Null check across all columns
    null_counts = {col: df[col].null_count() for col in df.columns if df[col].null_count() > 0}
    if null_counts:
        raise DataQualityError(f"Dataset contains null values: {null_counts}")

    # NaN and Inf check on float columns
    for float_col in ["bid", "ask", "last", "volume"]:
        nan_count = df.select(pl.col(float_col).is_nan().sum()).item()
        if nan_count > 0:
            raise DataQualityError(f"Column '{float_col}' contains {nan_count} NaN values.")
        non_finite_count = df.select((~pl.col(float_col).is_finite()).sum()).item()
        if non_finite_count > 0:
            raise DataQualityError(f"Column '{float_col}' contains {non_finite_count} non-finite/infinite values.")


def validate_chronological_monotonicity(df: pl.DataFrame, strict: bool = True) -> None:
    """
    Ensures timestamp_ns values are strictly increasing (dt > 0) or non-decreasing (dt >= 0)
    without backward jumps, and verifies plausible UTC nanosecond epoch scale.
    """
    if df.height <= 1:
        return

    diffs = df.select(pl.col("timestamp_ns").diff().slice(1).alias("dt"))["dt"]
    min_dt = diffs.min()

    if min_dt is None:
        return

    if strict and min_dt <= 0:
        neg_count = (diffs <= 0).sum()
        diffs_list = diffs.to_list()
        first_neg_idx = diffs_list.index(next(x for x in diffs_list if x is not None and x <= 0))
        raise MonotonicityError(
            f"Monotonicity violation: {neg_count} non-positive delta(s) found. "
            f"Min dt = {min_dt} ns at row index {first_neg_idx + 1}."
        )
    elif not strict and min_dt < 0:
        diffs_list = diffs.to_list()
        first_neg_idx = diffs_list.index(next(x for x in diffs_list if x is not None and x < 0))
        raise MonotonicityError(
            f"Backward time jump violation: Min dt = {min_dt} ns at row index {first_neg_idx + 1}."
        )

    # Time scale sanity check: nanoseconds should be ~ 1.5e18 to 2.5e18 (2017-2049)
    min_ts = df["timestamp_ns"].min()
    if min_ts is not None and min_ts < 1_500_000_000_000_000_000:
        raise DataQualityError(
            f"Plausibility failure: minimum timestamp {min_ts} is not in nanosecond scale."
        )


def resolve_duplicate_timestamps(df: pl.DataFrame) -> pl.DataFrame:
    """
    Resolves identical timestamps:
    1. Removes exact duplicate rows (pure redundant network ticks).
    2. Adds deterministic +1ns tie-breaking offsets to distinct ticks within the same millisecond.
    """
    if df.height == 0:
        return df

    # Step 1: Deduplicate identical records
    deduped = df.unique(subset=EXPECTED_TICK_COLUMNS, keep="first")
    if deduped.height <= 1:
        return deduped

    # Step 2: Tie-break duplicate timestamps
    if deduped["timestamp_ns"].n_unique() == deduped.height:
        return deduped.sort("timestamp_ns")

    # Apply sub-millisecond sequence offset
    resolved = (
        deduped.sort(["timestamp_ns"])
        .with_columns(
            seq=pl.int_range(0, pl.len()).over("timestamp_ns")
        )
        .with_columns(
            (pl.col("timestamp_ns") + pl.col("seq")).alias("timestamp_ns")
        )
        .drop("seq")
    )
    return resolved.sort("timestamp_ns")


def validate_price_sanity(df: pl.DataFrame, max_spread_ratio: float = 0.5) -> None:
    """
    Validates bid > 0, ask > 0, ask >= bid (no crossed quotes), and spread sanity.
    """
    if df.height == 0:
        return

    # 1. Strictly positive
    min_bid = df["bid"].min()
    min_ask = df["ask"].min()
    if min_bid is not None and min_bid <= 0.0:
        raise PriceSanityError(f"Price sanity violation: minimum bid {min_bid} <= 0.")
    if min_ask is not None and min_ask <= 0.0:
        raise PriceSanityError(f"Price sanity violation: minimum ask {min_ask} <= 0.")

    # 2. Spread non-negativity
    crossed = df.filter(pl.col("ask") < pl.col("bid"))
    if crossed.height > 0:
        row = crossed.row(0, named=True)
        raise CrossedMarketError(
            f"Crossed market error: {crossed.height} ticks with ask < bid. "
            f"Sample: bid={row['bid']}, ask={row['ask']} at ts={row['timestamp_ns']}."
        )

    # 3. Spread ratio check (ask - bid) / bid <= max_spread_ratio
    anomalous = df.filter(((pl.col("ask") - pl.col("bid")) / pl.col("bid")) > max_spread_ratio)
    if anomalous.height > 0:
        row = anomalous.row(0, named=True)
        raise PriceSanityError(
            f"Anomalous spread detected: {anomalous.height} ticks exceed spread ratio {max_spread_ratio}. "
            f"Sample: bid={row['bid']}, ask={row['ask']}."
        )


def detect_tick_gaps(df: pl.DataFrame, max_allowed_gap_sec: float = 60.0) -> List[Dict[str, Any]]:
    """
    Detects missing tick gaps exceeding the specified threshold in seconds.
    """
    if df.height <= 1:
        return []

    threshold_ns = int(max_allowed_gap_sec * 1_000_000_000)
    gaps_df = (
        df.select([
            pl.col("timestamp_ns").alias("start_ts"),
            pl.col("timestamp_ns").shift(-1).alias("end_ts"),
        ])
        .filter(pl.col("end_ts").is_not_null())
        .with_columns(
            (pl.col("end_ts") - pl.col("start_ts")).alias("dt_ns")
        )
        .filter(pl.col("dt_ns") > threshold_ns)
    )

    gaps: List[Dict[str, Any]] = []
    for row in gaps_df.iter_rows(named=True):
        gaps.append({
            "start_ts": int(row["start_ts"]),
            "end_ts": int(row["end_ts"]),
            "gap_duration_sec": float(row["dt_ns"] / 1_000_000_000.0),
        })
    return gaps


def verify_parquet_file(file_path: Union[str, Path]) -> pl.DataFrame:
    """
    Verifies file existence, magic headers, non-zero size, and reads Parquet.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Parquet file does not exist: {p}")

    size = p.stat().st_size
    if size == 0:
        raise EmptyDatasetError(f"Parquet file is empty (0 bytes): {p}")
    if size < 12:
        raise CorruptedParquetError(f"Parquet file too small to contain valid metadata ({size} bytes): {p}")

    with open(p, "rb") as f:
        header = f.read(4)
        if header != b"PAR1":
            raise CorruptedParquetError(f"Invalid Parquet header magic bytes: {header!r}. Expected b'PAR1'.")
        f.seek(-4, os.SEEK_END)
        footer = f.read(4)
        if footer != b"PAR1":
            raise CorruptedParquetError(f"Invalid Parquet footer magic bytes: {footer!r}. File likely truncated.")

    try:
        df = pl.read_parquet(p)
    except Exception as e:
        raise CorruptedParquetError(f"Failed to deserialize Parquet file: {e}") from e

    return df


def validate_family_diversity(symbols: List[str], min_families: int = 6) -> Set[SyntheticFamily]:
    """
    Validates that a list of symbols represents at least min_families distinct families.
    """
    families: Set[SyntheticFamily] = set()
    for s in symbols:
        try:
            fam = classify_family(s)
            families.add(fam)
        except ValueError:
            pass

    if len(families) < min_families:
        raise InsufficientFamilyDiversityError(
            f"Family diversity gate failed: Found {len(families)} distinct families, "
            f"minimum required is {min_families}. Families identified: {[f.value for f in families]}."
        )
    return families


# ============================================================================
# Full Quality Audit Report
# ============================================================================

@dataclass(frozen=True)
class DatasetValidationReport:
    symbol: str
    family: SyntheticFamily
    tick_count: int
    start_time_utc: datetime
    end_time_utc: datetime
    duration_days: float
    spread_mean: float
    spread_min: float
    spread_max: float
    gaps_detected: int
    is_valid: bool
    diagnostic_messages: List[str]


def run_full_quality_audit(parquet_path: Union[str, Path], min_ticks: int = 1_000_000) -> DatasetValidationReport:
    """
    Executes all 6 validation gates in sequence and returns a structured audit report.
    """
    p = Path(parquet_path)
    diagnostics: List[str] = []

    # Gate 1: Parquet headers and read
    df = verify_parquet_file(p)
    if df.height == 0:
        raise EmptyDatasetError("Parquet dataset contains 0 records")
    diagnostics.append(f"Gate 1 passed: Parquet file structure valid ({df.height} rows)")

    # Gate 2: Schema conformance
    validate_schema(df)
    diagnostics.append("Gate 2 passed: TICK_SCHEMA strictly satisfied, zero nulls/NaNs")

    # Gate 3: Monotonicity
    validate_chronological_monotonicity(df, strict=True)
    diagnostics.append("Gate 3 passed: Monotonic timestamps strictly increasing in UTC nanoseconds")

    # Gate 4: Duplicate resolution check
    if df["timestamp_ns"].n_unique() != df.height:
        diagnostics.append("Gate 4 warning: Identical timestamps detected, applying tie-breaking")
        df = resolve_duplicate_timestamps(df)
    else:
        diagnostics.append("Gate 4 passed: Zero duplicate timestamps")

    # Gate 5: Price sanity
    validate_price_sanity(df)
    diagnostics.append("Gate 5 passed: Prices strictly positive, spread non-negative")

    # Gate 6: Count
    if df.height < min_ticks:
        raise InsufficientTicksError(
            f"Tick count {df.height} is below required threshold of {min_ticks:,} ticks."
        )
    diagnostics.append(f"Gate 6 passed: Row count {df.height:,} >= {min_ticks:,}")

    # Metadata extraction
    if df.height == 0:
        raise EmptyDatasetError("Parquet dataset contains 0 records")
    symbol = str(df["symbol"][0])
    family = classify_family(symbol)

    t_min_ns = int(df["timestamp_ns"].min())  # type: ignore
    t_max_ns = int(df["timestamp_ns"].max())  # type: ignore
    start_dt = datetime.fromtimestamp(t_min_ns / 1_000_000_000.0, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(t_max_ns / 1_000_000_000.0, tz=timezone.utc)
    duration_days = (t_max_ns - t_min_ns) / (1_000_000_000.0 * 86400.0)

    spread_series = df["ask"] - df["bid"]
    spread_mean = float(spread_series.mean())  # type: ignore
    spread_min = float(spread_series.min())    # type: ignore
    spread_max = float(spread_series.max())    # type: ignore

    gaps = detect_tick_gaps(df, max_allowed_gap_sec=60.0)

    return DatasetValidationReport(
        symbol=symbol,
        family=family,
        tick_count=df.height,
        start_time_utc=start_dt,
        end_time_utc=end_dt,
        duration_days=duration_days,
        spread_mean=spread_mean,
        spread_min=spread_min,
        spread_max=spread_max,
        gaps_detected=len(gaps),
        is_valid=True,
        diagnostic_messages=diagnostics,
    )
