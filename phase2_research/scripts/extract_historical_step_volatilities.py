#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PHASE 2 DATA HARVESTER: STEP INDEX & VOLATILITY INDICES (V10 - V100 1s)
===============================================================================
Connects to MetaTrader 5 on the active terminal and downloads complete
tick-by-tick and M1 bar historical data for:
- Step Index
- Volatility 10 Index, Volatility 10 (1s) Index
- Volatility 25 Index, Volatility 25 (1s) Index
- Volatility 50 Index, Volatility 50 (1s) Index
- Volatility 75 Index, Volatility 75 (1s) Index
- Volatility 100 Index, Volatility 100 (1s) Index
===============================================================================
"""

import sys
import datetime
from pathlib import Path
import pandas as pd
import MetaTrader5 as mt5

TARGET_SYMBOLS = [
    "Step Index",
    "Volatility 10 Index",
    "Volatility 10 (1s) Index",
    "Volatility 25 Index",
    "Volatility 25 (1s) Index",
    "Volatility 50 Index",
    "Volatility 50 (1s) Index",
    "Volatility 75 Index",
    "Volatility 75 (1s) Index",
    "Volatility 100 Index",
    "Volatility 100 (1s) Index",
]

def initialize_mt5():
    if not mt5.initialize():
        print(f"[!] MetaTrader5 initialization failed, error: {mt5.last_error()}")
        sys.exit(1)
    account_info = mt5.account_info()
    if account_info is None:
        print("[!] No active trading account connected to MT5.")
        sys.exit(1)
    print(f"[+] Connected to MT5 Account: {account_info.login} ({account_info.server})")
    print(f"[+] Balance: ${account_info.balance:.2f} {account_info.currency} | Equity: ${account_info.equity:.2f}")

def harvest_symbol_data(symbol: str, output_dir: Path, days_back: int = 30):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if symbol is available in MarketWatch
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"[-] Symbol '{symbol}' could not be selected in MarketWatch.")
        return

    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"[-] Could not retrieve symbol_info for {symbol}.")
        return

    print(f"\n[*] Harvesting: {symbol} (Digits: {info.digits}, Point: {info.point}, Spread: {info.spread})")

    # Time window
    utc_to = datetime.datetime.now(datetime.timezone.utc)
    utc_from = utc_to - datetime.timedelta(days=days_back)

    # 1. M1 Bars Extraction
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)
    if rates is not None and len(rates) > 0:
        df_rates = pd.DataFrame(rates)
        df_rates["time"] = pd.to_datetime(df_rates["time"], unit="s")
        m1_file = output_dir / f"{symbol.replace(' ', '_').replace('(', '').replace(')', '')}_M1_{days_back}d.csv"
        df_rates.to_csv(m1_file, index=False)
        print(f"    [+] Saved {len(df_rates):,} M1 bars -> {m1_file.name}")
    else:
        print(f"    [-] No M1 bars returned for {symbol}.")

    # 2. Recent Tick Stream (Up to 1,000,000 ticks)
    ticks = mt5.copy_ticks_range(symbol, utc_to - datetime.timedelta(days=7), utc_to, mt5.COPY_TICKS_ALL)
    if ticks is not None and len(ticks) > 0:
        df_ticks = pd.DataFrame(ticks)
        df_ticks["time"] = pd.to_datetime(df_ticks["time"], unit="s")
        tick_file = output_dir / f"{symbol.replace(' ', '_').replace('(', '').replace(')', '')}_ticks_recent.csv"
        df_ticks.to_csv(tick_file, index=False)
        print(f"    [+] Saved {len(df_ticks):,} raw ticks -> {tick_file.name}")
    else:
        print(f"    [-] No tick data returned for {symbol}.")

def main():
    initialize_mt5()
    output_path = Path(__file__).resolve().parent.parent / "harvested_data"
    print(f"[+] Output directory set to: {output_path}")

    for sym in TARGET_SYMBOLS:
        harvest_symbol_data(sym, output_path, days_back=30)

    mt5.shutdown()
    print("\n[+] Harvesting sequence complete for Phase 2 targets.")

if __name__ == "__main__":
    main()
