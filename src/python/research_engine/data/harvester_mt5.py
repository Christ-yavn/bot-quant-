"""
src.data.harvester_mt5
======================
High-throughput MetaTrader 5 tick harvester for Deriv synthetic indices.
Connects via local IPC to Deriv MT5 terminal, paginates historical ticks in
chunks of 100,000, manages RAM footprint, and normalizes to UTC nanoseconds.

Compliant with PROJECT.md §3.2, F1, and SPEC-DERIV-SYNTH-2026-10-18.
"""

from __future__ import annotations

import datetime
import gc
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import MetaTrader5 as mt5
import numpy as np
import polars as pl

from src.data.schema import clean_and_validate_ticks, mt5_ticks_to_polars, save_ticks_parquet

logger = logging.getLogger("harvester_mt5")

DEFAULT_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
DEFAULT_LOGIN = 32449166
DEFAULT_SERVER = "Deriv-Demo"
DEFAULT_CHUNK_SIZE = 100_000


class MT5Harvester:
    """
    High-performance MT5 Harvester with chunked pagination and robust error recovery.
    """

    def __init__(
        self,
        terminal_path: Optional[str] = DEFAULT_TERMINAL_PATH,
        login: int = DEFAULT_LOGIN,
        server: str = DEFAULT_SERVER,
        timeout_ms: int = 60_000,
    ) -> None:
        self.terminal_path = terminal_path
        self.login = login
        self.server = server
        self.timeout_ms = timeout_ms
        self._connected = False

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Initializes connection to the Deriv MT5 terminal.
        Retries with exponential backoff if the terminal is booting up.
        """
        for attempt in range(1, max_retries + 1):
            logger.info(f"Connecting to MT5 terminal (Attempt {attempt}/{max_retries})...")

            # Try explicit path and login first
            ok = False
            if self.terminal_path and os.path.exists(self.terminal_path):
                ok = mt5.initialize(
                    path=self.terminal_path,
                    login=self.login,
                    server=self.server,
                    timeout=self.timeout_ms,
                )

            # Fallback to default initialize (attaches to already running MT5 instance)
            if not ok:
                ok = mt5.initialize(timeout=self.timeout_ms)

            if ok:
                acc = mt5.account_info()
                term = mt5.terminal_info()
                login_id = acc.login if acc else "Unknown"
                srv = acc.server if acc else "Unknown"
                connected = term.connected if term else False
                logger.info(f"MT5 Connected successfully: Account {login_id} on {srv} (Server Connected: {connected})")
                self._connected = True
                return True
            else:
                err = mt5.last_error()
                logger.warning(f"MT5 initialize failed on attempt {attempt}: {err}")
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)

        self._connected = False
        return False

    def disconnect(self) -> None:
        """Shuts down MT5 IPC connection."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 IPC connection closed.")

    def ensure_symbol(self, symbol: str) -> bool:
        """
        Verifies symbol exists and selects it in MarketWatch.
        """
        if not self._connected:
            if not self.connect():
                raise RuntimeError("MT5Harvester is not connected. Call connect() first.")

        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"Symbol '{symbol}' not found in MT5 symbols catalog.")
            return False

        if not info.visible:
            selected = mt5.symbol_select(symbol, True)
            if not selected:
                logger.error(f"Failed to select symbol '{symbol}' into MarketWatch: {mt5.last_error()}")
                return False
            logger.info(f"Selected symbol '{symbol}' in MarketWatch.")
        return True

    def get_symbol_specs(self, symbol: str) -> Dict[str, Any]:
        """Returns key execution and contract specifications for a symbol."""
        if not self.ensure_symbol(symbol):
            raise ValueError(f"Cannot get specs for invalid symbol '{symbol}'")
        s = mt5.symbol_info(symbol)
        if s is None:
            raise ValueError(f"Could not retrieve symbol info for {symbol}")
        return {
            "symbol": s.name,
            "digits": s.digits,
            "point": s.point,
            "spread": s.spread,
            "contract_size": s.trade_contract_size,
            "volume_min": s.volume_min,
            "volume_max": s.volume_max,
            "volume_step": s.volume_step,
            "swap_long": s.swap_long,
            "swap_short": s.swap_short,
            "swap_mode": s.swap_mode,
        }

    def iter_ticks_chunks(
        self,
        symbol: str,
        total_count: int = 1_000_000,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        to_datetime: Optional[datetime.datetime] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Iterator[pl.DataFrame]:
        """
        Generator yielding cleaned Polars DataFrames in chunks of chunk_size ticks.
        Paginates backwards in time to avoid terminal RAM saturation (err -3).
        """
        if not self.ensure_symbol(symbol):
            raise ValueError(f"Symbol '{symbol}' cannot be selected.")

        if to_datetime is None:
            tick_now = mt5.symbol_info_tick(symbol)
            if tick_now is not None and tick_now.time > 0:
                to_datetime = datetime.datetime.fromtimestamp(tick_now.time, tz=datetime.timezone.utc)
            else:
                to_datetime = datetime.datetime.now(datetime.timezone.utc)
        elif to_datetime.tzinfo is None:
            to_datetime = to_datetime.replace(tzinfo=datetime.timezone.utc)

        # Estimate time step per chunk based on typical tick density (~1-2 ticks/sec)
        # 100k ticks is typically ~1.2 to 2.5 days. Start with 1.5 days.
        step_delta = datetime.timedelta(days=max(0.5, (chunk_size / 86_400.0) * 1.25))

        current_to = to_datetime
        ticks_harvested = 0
        chunk_idx = 0
        consecutive_empty = 0

        while ticks_harvested < total_count and consecutive_empty < 5:
            current_from = current_to - step_delta

            logger.debug(f"Fetching chunk {chunk_idx + 1}: {current_from} -> {current_to}")
            t0 = time.time()
            raw_ticks = mt5.copy_ticks_range(symbol, current_from, current_to, mt5.COPY_TICKS_ALL)
            elapsed = time.time() - t0

            if raw_ticks is None:
                err = mt5.last_error()
                logger.warning(f"copy_ticks_range returned None on {symbol}: {err}. Reconnecting...")
                self.connect()
                raw_ticks = mt5.copy_ticks_range(symbol, current_from, current_to, mt5.COPY_TICKS_ALL)
                if raw_ticks is None:
                    logger.error(f"Persistent failure fetching ticks for {symbol}: {mt5.last_error()}")
                    consecutive_empty += 1
                    step_delta = step_delta * 1.5
                    continue

            n_raw = len(raw_ticks)
            if n_raw == 0:
                logger.warning(f"No ticks returned for window {current_from} -> {current_to}. Expanding search...")
                consecutive_empty += 1
                step_delta = step_delta * 2
                continue

            consecutive_empty = 0

            # Convert to Polars
            df_chunk = mt5_ticks_to_polars(raw_ticks, symbol)
            cleaned_chunk, rep = clean_and_validate_ticks(df_chunk)

            # Free raw numpy memory immediately
            del raw_ticks
            del df_chunk

            n_cleaned = len(cleaned_chunk)
            if n_cleaned == 0:
                logger.warning("Chunk contained 0 valid ticks after cleaning. Expanding window...")
                step_delta = step_delta * 2
                continue

            # Update dynamic step_delta based on actual tick rate in this chunk
            oldest_ts_ns = int(cleaned_chunk["timestamp_ns"].min())
            newest_ts_ns = int(cleaned_chunk["timestamp_ns"].max())
            time_span_sec = max(1.0, (newest_ts_ns - oldest_ts_ns) / 1_000_000_000.0)
            measured_rate = n_cleaned / time_span_sec  # ticks/sec
            if measured_rate > 0.05:
                # Estimate needed window for next chunk_size
                target_secs = (chunk_size / measured_rate) * 1.15
                step_delta = datetime.timedelta(seconds=max(3600.0, target_secs))

            logger.info(
                f"Chunk {chunk_idx + 1} [{symbol}]: fetched {n_raw} ticks ({n_cleaned} valid) "
                f"in {elapsed:.3f}s. Total progress: {ticks_harvested + n_cleaned}/{total_count}"
            )

            # Set next backward boundary to the oldest tick timestamp minus 1 millisecond
            oldest_dt = datetime.datetime.fromtimestamp(oldest_ts_ns / 1_000_000_000.0, tz=datetime.timezone.utc)
            current_to = oldest_dt - datetime.timedelta(milliseconds=1)

            ticks_harvested += n_cleaned
            chunk_idx += 1

            if progress_callback:
                progress_callback(ticks_harvested, total_count)

            yield cleaned_chunk

            # Clean memory periodically
            if chunk_idx % 5 == 0:
                gc.collect()

    def harvest_ticks(
        self,
        symbol: str,
        count: int = 1_000_000,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        to_datetime: Optional[datetime.datetime] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> pl.DataFrame:
        """
        Harvests count ticks for a symbol by accumulating chunks into a single
        strictly validated, deduplicated Polars DataFrame.
        """
        chunks: List[pl.DataFrame] = []
        for chunk in self.iter_ticks_chunks(
            symbol=symbol,
            total_count=count,
            chunk_size=chunk_size,
            to_datetime=to_datetime,
            progress_callback=progress_callback,
        ):
            chunks.append(chunk)
            # Early break if accumulated count is sufficient
            accumulated = sum(len(c) for c in chunks)
            if accumulated >= count:
                break

        if not chunks:
            raise RuntimeError(f"No ticks could be harvested for symbol {symbol}")

        # Concatenate and final global dedup/sort
        full_df = pl.concat(chunks)
        final_df, rep = clean_and_validate_ticks(full_df)

        # Slice to requested count if slightly over, preserving latest ticks
        if len(final_df) > count:
            final_df = final_df.slice(len(final_df) - count, count)

        logger.info(
            f"Harvesting completed for {symbol}: {len(final_df)} ticks assembled "
            f"(Purged: {rep['purged_duplicates']} dupes, {rep['purged_incoherent_spread']} bad spreads, "
            f"{rep['gap_warnings']} gap warnings)."
        )
        return final_df

    def harvest_and_save(
        self,
        symbol: str,
        output_path: Union[str, Path],
        count: int = 1_000_000,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Harvests ticks and saves directly to compressed Apache Parquet.
        Uses atomic staging file to prevent partial corrupt commits.
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path = out_path.parent / f".tmp_{out_path.name}"

        try:
            df = self.harvest_ticks(
                symbol=symbol,
                count=count,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
            )
            save_ticks_parquet(df, staging_path)
            # Atomic commit
            staging_path.replace(out_path)
            size_mb = out_path.stat().st_size / (1024 * 1024)
            logger.info(f"Persisted {len(df)} ticks to {out_path} ({size_mb:.2f} MB)")
            return out_path
        finally:
            if staging_path.exists():
                try:
                    staging_path.unlink()
                except Exception:
                    pass
