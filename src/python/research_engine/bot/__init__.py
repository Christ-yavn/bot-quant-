"""
src.bot
=======
Autonomous Trading Bot, Execution Adapters (Paper & MT5 Demo),
Triple Anti-Real-Money Safety Locks, 5 Risk Circuit Breakers,
and Structured JSONL Audit Logger.

Compliant with PROJECT.md §5.E, §6.3, and tests/e2e/contract_harness.py §5 (F13, F14, F15).
"""

from src.bot.bot_engine import (
    BotEngine,
    BotMode,
    BotState,
    TradingBot,
)
from src.bot.circuit_breakers import (
    CircuitBreaker,
    CircuitBreakerManager,
    ConsecutiveLossBreaker,
    MaxDailyLossBreaker,
    MaxDrawdownBreaker,
    MaxPositionsBreaker,
    SpreadSpikeBreaker,
)
from src.bot.logger import BotLogger
from src.bot.mt5_adapter import (
    ALLOWED_DEMO_SERVERS,
    DEFAULT_DEMO_LOGIN,
    DEFAULT_DEMO_SERVER,
    MT5DemoAdapter,
    RealMoneyTradingForbiddenError,
    SafetyLocks,
    SafetyViolationError,
)
from src.bot.paper_adapter import (
    ExecutionAdapter,
    ExecutionResult,
    PaperTradingAdapter,
)
from src.bot.risk_manager import RiskManager

__all__ = [
    "BotEngine",
    "BotMode",
    "BotState",
    "TradingBot",
    "ExecutionAdapter",
    "ExecutionResult",
    "PaperTradingAdapter",
    "MT5DemoAdapter",
    "ALLOWED_DEMO_SERVERS",
    "DEFAULT_DEMO_LOGIN",
    "DEFAULT_DEMO_SERVER",
    "CircuitBreaker",
    "CircuitBreakerManager",
    "MaxDailyLossBreaker",
    "MaxDrawdownBreaker",
    "MaxPositionsBreaker",
    "ConsecutiveLossBreaker",
    "SpreadSpikeBreaker",
    "SafetyLocks",
    "SafetyViolationError",
    "RealMoneyTradingForbiddenError",
    "RiskManager",
    "BotLogger",
]
