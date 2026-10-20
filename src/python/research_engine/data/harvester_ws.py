"""
src.data.harvester_ws
=====================
Asynchronous WebSocket tick harvester for Deriv Synthetic Indices.
Handles reverse pagination via ticks_history (5,000 ticks/call, 3 req/sec limit),
active ping/pong keepalive, Cloudflare HTTP 520 error recovery, and live streaming.

Compliant with PROJECT.md §3.2, F1, and Deriv API specifications.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Sequence, Union

import polars as pl
import websockets

from src.data.schema import TickRecord, clean_and_validate_ticks, save_ticks_parquet, ws_history_to_polars

logger = logging.getLogger("harvester_ws")

DEFAULT_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
FALLBACK_WS_URLS = [
    "wss://red.derivws.com/websockets/v3?app_id=1089",
    "wss://ws.binaryws.com/websockets/v3?app_id=1089",
]
MAX_BATCH_SIZE = 5000
RATE_LIMIT_DELAY_SEC = 0.35  # ~2.85 req/sec (Deriv max is 3.0 req/sec)


class DerivWebSocketHarvester:
    """
    Robust asynchronous WebSocket harvester for Deriv historical ticks & streaming.
    """

    def __init__(
        self,
        ws_url: str = DEFAULT_WS_URL,
        rate_limit_delay: float = RATE_LIMIT_DELAY_SEC,
        request_timeout: float = 15.0,
    ) -> None:
        self.ws_url = ws_url
        self.rate_limit_delay = rate_limit_delay
        self.request_timeout = request_timeout
        self._ws: Optional[Any] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._req_id = 0
        self._headers = {
            "Origin": "https://deriv.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def __aenter__(self) -> "DerivWebSocketHarvester":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def connect(self, max_retries: int = 5) -> None:
        """
        Connects to Deriv WebSocket endpoint with exponential backoff against Cloudflare 520 / timeouts.
        """
        urls_to_try = [self.ws_url] + [u for u in FALLBACK_WS_URLS if u != self.ws_url]
        delay = 1.0

        for attempt in range(1, max_retries + 1):
            for target_url in urls_to_try:
                try:
                    logger.info(f"Connecting to Deriv WebSocket at {target_url} (Attempt {attempt}/{max_retries})...")
                    self._ws = await asyncio.wait_for(
                        websockets.connect(
                            target_url,
                            compression=None,
                            additional_headers=self._headers,
                            ping_interval=30,
                            ping_timeout=10,
                        ),
                        timeout=self.request_timeout,
                    )
                    logger.info(f"WebSocket connected successfully to {target_url}.")
                    self._start_keepalive()
                    return
                except Exception as e:
                    logger.warning(f"Connection to {target_url} failed: {type(e).__name__} ({e})")

            logger.info(f"Backing off for {delay:.1f}s before next connection attempt...")
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, 30.0)

        raise ConnectionError(f"Failed to connect to Deriv WebSocket after {max_retries} attempts.")

    async def disconnect(self) -> None:
        """Stops keepalive ping and closes WebSocket."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("WebSocket connection closed.")

    @property
    def is_connected(self) -> bool:
        """
        Checks if the underlying WebSocket connection is alive across websockets library versions.
        Compatible with websockets 16.0+ (State enum/int), older .open boolean, and .closed attribute.
        """
        if self._ws is None:
            return False
        state = getattr(self._ws, "state", None)
        if state is not None:
            return getattr(state, "name", "") == "OPEN" or state == 1
        if hasattr(self._ws, "open"):
            return bool(self._ws.open)
        return not getattr(self._ws, "closed", False)

    def _start_keepalive(self) -> None:
        """Spawns background task sending ping frames every 30s."""
        async def keepalive():
            while True:
                try:
                    await asyncio.sleep(30)
                    if self.is_connected:
                        await self._send({"ping": 1})
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Keepalive error: {e}")
                    break

        self._ping_task = asyncio.create_task(keepalive())

    async def _send(self, payload: Dict[str, Any]) -> None:
        if not self.is_connected:
            await self.connect()
        self._req_id += 1
        payload["req_id"] = self._req_id
        await self._ws.send(json.dumps(payload))

    async def _recv(self) -> Dict[str, Any]:
        if not self._ws:
            raise RuntimeError("WebSocket is not connected.")
        msg = await asyncio.wait_for(self._ws.recv(), timeout=self.request_timeout)
        return json.loads(msg)

    async def harvest_ticks_history(
        self,
        symbol: str,
        total_count: int = 1_000_000,
        spread_pts: float = 0.0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> pl.DataFrame:
        """
        Paginates historical ticks backwards using ticks_history until total_count is reached.
        Enforces rate limiting delay (350ms) to respect Deriv API 3 req/sec threshold.
        """
        all_times: List[int] = []
        all_prices: List[float] = []

        current_end: Union[str, int] = "latest"
        batch_count = 0

        logger.info(f"Starting WebSocket historical harvest for {symbol} (Target: {total_count} ticks)...")

        while len(all_times) < total_count:
            req_count = min(MAX_BATCH_SIZE, total_count - len(all_times))
            payload = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": req_count,
                "end": current_end,
                "style": "ticks",
            }

            try:
                await self._send(payload)
                resp = await self._recv()
            except Exception as e:
                logger.warning(f"Error during ticks_history request: {e}. Reconnecting...")
                await self.connect()
                continue

            if "error" in resp:
                err_msg = resp["error"].get("message", "Unknown error")
                err_code = resp["error"].get("code", "")
                if err_code == "RateLimit":
                    logger.warning("Rate limit hit! Backing off for 3.0s...")
                    await asyncio.sleep(3.0)
                    continue
                else:
                    raise RuntimeError(f"Deriv API error for symbol {symbol}: {err_code} - {err_msg}")

            history = resp.get("history")
            if not history or "times" not in history or not history["times"]:
                logger.info(f"No further historical ticks available for {symbol}.")
                break

            times: List[int] = history["times"]
            prices: List[float] = history["prices"]
            n = len(times)

            # Prepend older batches
            all_times = times + all_times
            all_prices = prices + all_prices
            batch_count += 1

            logger.info(
                f"Batch {batch_count} [{symbol}]: retrieved {n} ticks. "
                f"Total collected: {len(all_times)}/{total_count} (Oldest epoch: {times[0]})"
            )

            if progress_callback:
                progress_callback(len(all_times), total_count)

            # Oldest tick becomes the boundary for next query (minus 1 second to avoid duplicate)
            current_end = times[0] - 1

            # Strict rate limiting pause
            await asyncio.sleep(self.rate_limit_delay)

        # Truncate to exact requested count if slightly over
        if len(all_times) > total_count:
            all_times = all_times[-total_count:]
            all_prices = all_prices[-total_count:]

        # Convert to standardized Polars DataFrame
        df = ws_history_to_polars(all_times, all_prices, symbol, spread_pts)
        cleaned_df, rep = clean_and_validate_ticks(df)
        logger.info(
            f"WebSocket harvest completed for {symbol}: {len(cleaned_df)} valid ticks assembled "
            f"({rep['purged_duplicates']} purged duplicates, {rep['gap_warnings']} gap warnings)."
        )
        return cleaned_df

    async def subscribe_ticks(self, symbol: str) -> AsyncIterator[TickRecord]:
        """
        Subscribes to live real-time tick stream and yields TickRecord instances.
        """
        payload = {"ticks": symbol, "subscribe": 1}
        await self._send(payload)
        logger.info(f"Subscribed to live real-time tick feed for '{symbol}'")

        while True:
            try:
                resp = await self._recv()
                if "tick" in resp:
                    t = resp["tick"]
                    epoch = int(t["epoch"])
                    ts_ns = epoch * 1_000_000_000
                    bid = float(t.get("bid", t["quote"]))
                    ask = float(t.get("ask", t["quote"]))
                    quote = float(t["quote"])

                    yield TickRecord(
                        timestamp_ns=ts_ns,
                        symbol=str(t["symbol"]),
                        bid=bid,
                        ask=ask,
                        last=quote,
                        volume=1.0,
                        flags=6,
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in tick streaming loop: {e}. Attempting reconnect...")
                await self.connect()
                await self._send(payload)

    async def harvest_and_save(
        self,
        symbol: str,
        output_path: Union[str, Path],
        total_count: int = 1_000_000,
        spread_pts: float = 0.0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Harvests ticks via WebSocket and persists atomically to compressed Apache Parquet.
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path = out_path.parent / f".tmp_{out_path.name}"

        try:
            df = await self.harvest_ticks_history(
                symbol=symbol,
                total_count=total_count,
                spread_pts=spread_pts,
                progress_callback=progress_callback,
            )
            save_ticks_parquet(df, staging_path)
            staging_path.replace(out_path)
            logger.info(f"Persisted {len(df)} ticks to {out_path}")
            return out_path
        finally:
            if staging_path.exists():
                try:
                    staging_path.unlink()
                except Exception:
                    pass
