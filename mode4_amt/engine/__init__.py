"""engine/ — Mode 4 AMT signal engine (Balance State + Sub-4A/4B + Orchestrator)."""

from .balance_state import (
    BalanceState,
    BalanceStateResult,
    compute_balance_state,
)
from .sub_4a_engine import (
    Sub4ACandidate,
    detect_sub4a_setup,
)
from .sub_4b_engine import (
    Sub4BCandidate,
    detect_sub4b_setup,
)
from .entry_orchestrator import (
    TradeSignal,
    Mode4Orchestrator,
)

__all__ = [
    "BalanceState", "BalanceStateResult", "compute_balance_state",
    "Sub4ACandidate", "detect_sub4a_setup",
    "Sub4BCandidate", "detect_sub4b_setup",
    "TradeSignal", "Mode4Orchestrator",
]
