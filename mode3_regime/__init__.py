"""mode3_regime — Anchored VAH/VAL regime engine dengan 3-way confirmation state machine."""

from .regime import (
    Regime,
    RegimeConfig,
    ValueArea,
    RegimeState,
    compute_value_area,
    detect_range,
    detect_trend,
    classify_regime_at,
    classify_regime_series,
    compute_atr,
    is_dead_market,
)
from .state_machine import (
    SMState,
    BreakType,
    BotContext,
    StateMachineConfig,
    MachineState,
    classify_break,
    determine_context,
    detect_level_touch,
    transition_state,
    run_state_machine,
)

__version__ = "0.2.0"

__all__ = [
    # regime
    "Regime", "RegimeConfig", "ValueArea", "RegimeState",
    "compute_value_area", "detect_range", "detect_trend",
    "classify_regime_at", "classify_regime_series",
    "compute_atr", "is_dead_market",
    # state_machine
    "SMState", "BreakType", "BotContext",
    "StateMachineConfig", "MachineState",
    "classify_break", "determine_context",
    "detect_level_touch", "transition_state", "run_state_machine",
]
