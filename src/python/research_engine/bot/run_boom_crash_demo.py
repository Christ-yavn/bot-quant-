"""
src.bot.run_boom_crash_demo
===========================
High-Frequency Python Execution Controller for Deriv Boom & Crash Indices
on the local MT5 Demo Account (32449166, Deriv-Demo, $10,000.00 balance)
or in Local Paper Mode.

Safety Guarantee:
- Hard-locked against Real Money accounts (blocks ACCOUNT_TRADE_MODE_REAL).
- Defaults to `--mode paper` (dry-run simulation on live MT5 ticks) unless
  `--mode demo --confirm-demo-orders` is explicitly passed by the operator.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.backtest.costs import DERIV_SPECS
from src.bot.bot_engine import BotMode, TradingBot
from src.strategies.user_post_spike import UserPostSpikeStrategy

logger = logging.getLogger("run_boom_crash_demo")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deriv Boom & Crash HFT Bot Controller (Paper & MT5 Demo 32449166)"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="Boom 1000 Index",
        choices=[s for s in DERIV_SPECS.keys() if "Boom" in s or "Crash" in s],
        help="Target Boom or Crash synthetic index (default: Boom 1000 Index).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["paper", "demo"],
        default="paper",
        help="Execution mode: 'paper' (simulated fills) or 'demo' (MT5 Demo 32449166).",
    )
    parser.add_argument(
        "--confirm-demo-orders",
        action="store_true",
        help="Explicit operator confirmation required before sending orders to MT5 Demo.",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=600,
        help="Number of live ticks to process before clean shutdown (default: 600).",
    )
    parser.add_argument(
        "--delay-ticks",
        type=int,
        default=3,
        help="Anti-cluster delay in ticks after spike detection (default: 3).",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.mode == "demo" and not args.confirm_demo_orders:
        logger.warning(
            "Demo mode requested without --confirm-demo-orders. "
            "Switching to PAPER dry-run mode to prevent unauthorized demo orders."
        )
        bot_mode = BotMode.PAPER
    else:
        bot_mode = BotMode.DEMO if args.mode == "demo" else BotMode.PAPER

    strategy = UserPostSpikeStrategy.for_symbol(
        args.symbol,
        delay_ticks=args.delay_ticks,
    )
    log_path = Path("logs") / f"bot_{args.symbol.lower().replace(' ', '_')}.jsonl"

    bot = TradingBot(
        mode=bot_mode,
        symbol=args.symbol,
        strategy=strategy,
        initial_balance=10000.0,
        log_path=log_path,
        allow_real_money_config=False,
    )

    logger.info(
        f"Initialized Deriv Boom/Crash HFT Bot | Symbol={args.symbol} | Mode={bot_mode.value} | "
        f"Params={strategy.get_params()}"
    )
    bot.start(max_ticks=args.max_ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
