"""
src.data
========
Data ingestion, validation, and storage pipeline for Deriv synthetic indices.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional, Union

import polars as pl

from src.data.harvester_mt5 import MT5Harvester
from src.data.harvester_ws import DerivWebSocketHarvester
from src.data.partitioner import (
    DEFAULT_PARTITION_DIR,
    DEFAULT_RATIOS,
    partition_all_raw_datasets,
    partition_dataset,
    split_chronological,
)
from src.data.quarantine import (
    OOS_AUTHORIZATION_TOKEN,
    QuarantineViolationError,
    compute_sha256,
    create_global_quarantine_manifest,
    create_quarantine_manifest,
    load_test_partition,
    log_quarantine_event,
    verify_quarantine_manifest,
)
from src.data.schema import (
    TICK_SCHEMA,
    TickRecord,
    TickRecordDict,
    clean_and_validate_ticks,
    load_ticks_parquet,
    mt5_ticks_to_polars,
    save_ticks_parquet,
    to_tick_record,
    ws_history_to_polars,
)
from src.data.validator import (
    CorruptedParquetError,
    CrossedMarketError,
    DataQualityError,
    DatasetValidationReport,
    EmptyDatasetError,
    InsufficientFamilyDiversityError,
    InsufficientTicksError,
    MonotonicityError,
    PriceSanityError,
    SchemaValidationError,
    SyntheticFamily,
    classify_family,
    detect_tick_gaps,
    resolve_duplicate_timestamps,
    run_full_quality_audit,
    validate_chronological_monotonicity,
    validate_family_diversity,
    validate_price_sanity,
    validate_schema,
    verify_parquet_file,
)

logger = logging.getLogger("src.data")


def _symbol_to_slug(symbol: str) -> str:
    s = re.sub(r"[^\w\s-]", "", symbol.lower())
    return re.sub(r"[\s-]+", "_", s.strip())


def harvest_ticks(
    symbol: str,
    count: int = 1_000_000,
    source: str = "mt5",
    output_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> Path:
    """
    Download count ticks and save to compressed Parquet format.
    Compliant with PROJECT.md § 5.A interface contract.

    Parameters
    ----------
    symbol : str
        Deriv index name (e.g. "Boom 1000 Index", "Volatility 75 Index").
    count : int, default 1_000_000
        Target number of ticks to harvest.
    source : str, default "mt5"
        Data source ("mt5", "ws", or "auto").
    output_dir : Path or str, optional
        Destination directory. Defaults to Path("data/raw").
    force : bool, default False
        If True, re-download even if a valid Parquet dataset already exists.

    Returns
    -------
    Path
        Path to the persisted Parquet dataset.
    """
    out_dir = Path(output_dir) if output_dir is not None else Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _symbol_to_slug(symbol)
    target_path = out_dir / f"{slug}.parquet"

    # Fast cache check: if valid parquet with >= count ticks exists
    if target_path.exists() and not force:
        try:
            summary = pl.scan_parquet(target_path).select(pl.len()).collect()
            existing_count = summary.item()
            if existing_count >= count:
                logger.info(
                    f"[{symbol}] Found cached Parquet with {existing_count:,} ticks (>= {count:,}). "
                    f"Returning existing file: {target_path}"
                )
                return target_path
        except Exception:
            pass

    # Source selection & harvesting
    normalized_source = source.lower().strip()
    if normalized_source not in ("mt5", "ws", "auto"):
        raise ValueError(f"Unknown data source: '{source}'. Expected 'mt5', 'ws', or 'auto'.")

    # 1. MT5 attempt
    if normalized_source in ("auto", "mt5"):
        try:
            harvester = MT5Harvester()
            if harvester.connect():
                try:
                    return harvester.harvest_and_save(
                        symbol=symbol,
                        output_path=target_path,
                        count=count,
                    )
                finally:
                    harvester.disconnect()
            elif normalized_source == "mt5":
                raise ConnectionError(f"Could not connect to MT5 terminal to harvest '{symbol}'")
        except Exception as e:
            if normalized_source == "mt5":
                raise
            logger.warning(f"MT5 harvest attempt failed ({e}), falling back to WebSocket...")

    # 2. WebSocket attempt
    if normalized_source in ("auto", "ws"):
        ws = DerivWebSocketHarvester()

        async def _run_ws() -> Path:
            await ws.connect()
            try:
                return await ws.harvest_and_save(
                    symbol=symbol,
                    output_path=target_path,
                    total_count=count,
                )
            finally:
                await ws.disconnect()

        return asyncio.run(_run_ws())

    raise RuntimeError(f"Failed to harvest ticks for '{symbol}' from source '{source}'")


__all__ = [
    "TICK_SCHEMA",
    "TickRecord",
    "TickRecordDict",
    "to_tick_record",
    "mt5_ticks_to_polars",
    "ws_history_to_polars",
    "clean_and_validate_ticks",
    "save_ticks_parquet",
    "load_ticks_parquet",
    "harvest_ticks",
    "DataQualityError",
    "SchemaValidationError",
    "MonotonicityError",
    "PriceSanityError",
    "CrossedMarketError",
    "InsufficientTicksError",
    "InsufficientFamilyDiversityError",
    "CorruptedParquetError",
    "EmptyDatasetError",
    "SyntheticFamily",
    "classify_family",
    "validate_schema",
    "validate_chronological_monotonicity",
    "resolve_duplicate_timestamps",
    "validate_price_sanity",
    "detect_tick_gaps",
    "verify_parquet_file",
    "validate_family_diversity",
    "DatasetValidationReport",
    "run_full_quality_audit",
    # Partitioner & Quarantine
    "DEFAULT_RATIOS",
    "DEFAULT_PARTITION_DIR",
    "split_chronological",
    "partition_dataset",
    "partition_all_raw_datasets",
    "OOS_AUTHORIZATION_TOKEN",
    "QuarantineViolationError",
    "compute_sha256",
    "create_quarantine_manifest",
    "create_global_quarantine_manifest",
    "verify_quarantine_manifest",
    "load_test_partition",
    "log_quarantine_event",
]

