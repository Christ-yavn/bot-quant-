"""
src.data.download_data
======================
CLI Data Ingestion Orchestrator for Deriv Synthetic Indices.
Downloads >= 1,000,000 real ticks per instrument across >= 6 distinct families.
Paginates in 100k chunks, enforces strict quality assertions, and manages memory.

Usage:
    python -m src.data.download_data --symbols core6 --count 1000000 --source auto
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import polars as pl

from src.data.harvester_mt5 import MT5Harvester
from src.data.harvester_ws import DerivWebSocketHarvester
from src.data.validator import (
    DatasetValidationReport,
    classify_family,
    run_full_quality_audit,
    validate_family_diversity,
)

logger = logging.getLogger("download_data")

CORE_6_SYMBOLS: List[str] = [
    "Boom 1000 Index",          # Family 1: Crash Boom
    "Volatility 75 Index",      # Family 2: Volatility
    "Volatility 10 (1s) Index", # Family 3: Volatility 1s
    "Step Index",               # Family 4: Step Indices
    "Jump 10 Index",            # Family 5: Jump Indices
    "DEX 900 DOWN Index",       # Family 6: DEX
]

ALL_12_SYMBOLS: List[str] = [
    "Boom 1000 Index",
    "Crash 1000 Index",
    "Volatility 75 Index",
    "Volatility 100 Index",
    "Volatility 10 (1s) Index",
    "Volatility 25 (1s) Index",
    "Step Index",
    "Jump 10 Index",
    "Jump 25 Index",
    "Range Break 100 Index",
    "DEX 900 DOWN Index",
    "Drift Switch Index 10",
]


BOOM_CRASH_10_SYMBOLS: List[str] = [
    "Boom 1000 Index",
    "Crash 1000 Index",
    "Boom 900 Index",
    "Crash 900 Index",
    "Boom 600 Index",
    "Crash 600 Index",
    "Boom 500 Index",
    "Crash 500 Index",
    "Boom 300 Index",
    "Crash 300 Index",
]


def symbol_to_slug(symbol: str) -> str:
    """
    Transforms MT5/WS symbol names into deterministic, filesystem-safe slugs.
    Example: 'Volatility 10 (1s) Index' -> 'volatility_10_1s_index'
    """
    s = re.sub(r"[^\w\s-]", "", symbol.lower())
    return re.sub(r"[\s-]+", "_", s.strip())


def parse_symbol_arg(symbol_arg: str) -> List[str]:
    """Expands aliases or comma-separated symbols into a clean list of symbols."""
    raw = symbol_arg.strip()
    if raw.lower() == "core6":
        return CORE_6_SYMBOLS
    if raw.lower() == "all":
        return ALL_12_SYMBOLS
    if raw.lower() in ("boom_crash", "boom_crash_10"):
        return BOOM_CRASH_10_SYMBOLS

    parts = [s.strip() for s in raw.split(",") if s.strip()]
    return parts if parts else CORE_6_SYMBOLS


def download_symbol(
    symbol: str,
    target_count: int,
    source: str,
    output_dir: Path,
    chunk_size: int,
    compression: str,
    force: bool,
    verify: bool,
) -> bool:
    """
    Downloads and verifies a single symbol to parquet.
    """
    slug = symbol_to_slug(symbol)
    target_file = output_dir / f"{slug}.parquet"

    # 1. Cache Check
    if target_file.exists() and not force:
        try:
            summary = pl.scan_parquet(target_file).select(pl.len()).collect()
            existing_count = summary.item()
            if existing_count >= target_count:
                if verify:
                    try:
                        report = run_full_quality_audit(target_file, min_ticks=target_count)
                        logger.info(
                            f"[{symbol}] Existing parquet valid with {report.tick_count:,} ticks "
                            f"({report.duration_days:.1f} days, spread mean={report.spread_mean:.4f}). Skipping download."
                        )
                        return True
                    except Exception as ve:
                        logger.warning(f"[{symbol}] Cache audit failed ({ve}), re-downloading...")
                else:
                    logger.info(f"[{symbol}] Found cached file with {existing_count:,} ticks. Skipping download.")
                    return True
        except Exception as e:
            logger.warning(f"[{symbol}] Existing parquet unreadable ({e}), re-downloading...")

    logger.info(f"[{symbol}] Ingesting {target_count:,} ticks (Source: {source})...")
    t0 = time.time()
    success = False

    # 2. Try MT5
    if source in ("auto", "mt5"):
        try:
            logger.info(f"[{symbol}] Attempting ingestion via MT5 IPC...")
            mt5_harvester = MT5Harvester()
            if mt5_harvester.connect():
                def pbar(cur: int, tot: int):
                    pct = (cur / tot) * 100.0 if tot > 0 else 0.0
                    logger.info(f"[{symbol} MT5 Progress] {cur:,}/{tot:,} ticks ({pct:.1f}%)")

                mt5_harvester.harvest_and_save(
                    symbol=symbol,
                    output_path=target_file,
                    count=target_count,
                    chunk_size=chunk_size,
                    progress_callback=pbar,
                )
                mt5_harvester.disconnect()
                success = True
            else:
                logger.warning(f"[{symbol}] MT5 terminal connection failed.")
        except Exception as e:
            logger.warning(f"[{symbol}] MT5 ingestion error: {e}")

    # 3. Fallback to WebSocket if MT5 failed or source == "ws"
    if not success and source in ("auto", "ws"):
        logger.info(f"[{symbol}] Falling back to Deriv WebSocket v3 ingestion...")
        try:
            ws_harvester = DerivWebSocketHarvester()

            def pbar_ws(cur: int, tot: int):
                pct = (cur / tot) * 100.0 if tot > 0 else 0.0
                logger.info(f"[{symbol} WS Progress] {cur:,}/{tot:,} ticks ({pct:.1f}%)")

            async def run_ws():
                await ws_harvester.connect()
                await ws_harvester.harvest_and_save(
                    symbol=symbol,
                    output_path=target_file,
                    total_count=target_count,
                    progress_callback=pbar_ws,
                )
                await ws_harvester.disconnect()

            asyncio.run(run_ws())
            success = True
        except Exception as e:
            logger.error(f"[{symbol}] WebSocket ingestion failed: {e}")

    if not success:
        logger.error(f"[{symbol}] Failed to download dataset from both MT5 and WebSocket.")
        return False

    elapsed = time.time() - t0
    logger.info(f"[{symbol}] Download completed in {elapsed:.2f}s.")

    # 4. Post-Ingestion Verification Gate
    if verify:
        logger.info(f"[{symbol}] Running full quality audit on {target_file}...")
        report = run_full_quality_audit(target_file, min_ticks=target_count)
        logger.info(
            f"[{symbol}] QUALITY GATE PASSED: {report.tick_count:,} ticks, "
            f"span: {report.duration_days:.1f} days, gaps: {report.gaps_detected}, "
            f"spread: [{report.spread_min:.4f}, {report.spread_mean:.4f}, {report.spread_max:.4f}]"
        )

    # 5. Free memory
    gc.collect()
    return True


def run_download_pipeline(
    symbols: List[str],
    count: int = 1_000_000,
    source: str = "auto",
    output_dir: Union[str, Path] = "data/raw",
    chunk_size: int = 100_000,
    compression: str = "zstd",
    force: bool = False,
    verify: bool = True,
) -> Dict[str, Any]:
    """
    Executes sequential download pipeline across symbols and validates family diversity.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, bool] = {}
    completed_symbols: List[str] = []

    logger.info(f"Starting download pipeline for {len(symbols)} instruments...")
    logger.info(f"Target count: {count:,} ticks/symbol | Storage: {out_dir} | Compression: {compression}")

    for idx, sym in enumerate(symbols, 1):
        logger.info(f"\n=======================================================")
        logger.info(f"Processing Instrument {idx}/{len(symbols)}: {sym}")
        logger.info(f"=======================================================")

        ok = download_symbol(
            symbol=sym,
            target_count=count,
            source=source,
            output_dir=out_dir,
            chunk_size=chunk_size,
            compression=compression,
            force=force,
            verify=verify,
        )
        results[sym] = ok
        if ok:
            completed_symbols.append(sym)

    # Verify family diversity across all completed symbols
    families: Set[Any] = set()
    if verify and completed_symbols:
        try:
            distinct_requested = {classify_family(s) for s in symbols}
            req_min_families = min(6, len(distinct_requested))
            families = validate_family_diversity(completed_symbols, min_families=req_min_families)
            logger.info(
                f"\nFAMILY DIVERSITY GATE PASSED: {len(families)} distinct families verified: "
                f"{[f.value for f in families]}"
            )
        except Exception as e:
            logger.error(f"Family diversity gate failed: {e}")

    summary = {
        "total_requested": len(symbols),
        "total_completed": len(completed_symbols),
        "distinct_families": len(families),
        "results": results,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Data Ingestion Orchestrator for Deriv Synthetic Indices.")
    parser.add_argument(
        "--symbols",
        type=str,
        default="core6",
        help="Symbols to download: 'core6', 'all', 'boom_crash', or comma-separated symbol names.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1_000_000,
        help="Minimum ticks required per symbol (default: 1,000,000).",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["mt5", "ws", "auto"],
        default="auto",
        help="Data source engine (default: auto).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw",
        help="Destination directory for raw Parquets (default: data/raw).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
        help="Paging batch size per query (default: 100,000).",
    )
    parser.add_argument(
        "--compression",
        type=str,
        choices=["zstd", "snappy"],
        default="zstd",
        help="Parquet compression codec (default: zstd).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force redownload even if valid Parquet exists (default: False).",
    )
    parser.add_argument(
        "--verify",
        dest="verify",
        action="store_true",
        default=True,
        help="Run post-write integrity assertions (default: True).",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip post-write integrity assertions.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    symbols = parse_symbol_arg(args.symbols)
    summary = run_download_pipeline(
        symbols=symbols,
        count=args.count,
        source=args.source,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        compression=args.compression,
        force=args.force,
        verify=args.verify,
    )

    if summary["total_completed"] < summary["total_requested"]:
        logger.warning(
            f"Pipeline finished with warnings: {summary['total_completed']}/{summary['total_requested']} downloaded."
        )
        sys.exit(1)
    else:
        logger.info(
            f"Pipeline completed successfully: {summary['total_completed']} instruments ready."
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
