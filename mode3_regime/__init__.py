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
from .classifier import (
    SidewaysBias,
    ClassifierConfig,
    SidewaysAnalysis,
    signal_volume_trend,
    signal_test_count,
    signal_range_width,
    signal_duration,
    signal_mtf_momentum,
    analyze_sideways,
    get_prior_regime,
    resolve_entry_bias,
)
from .backtest import (
    EntryMode,
    ExitReason,
    BacktestConfig,
    Position,
    TradeRecord,
    BacktestStats,
    BacktestResult,
    CircuitBreakerState,
    open_position,
    manage_position,
    close_position,
    check_circuit_breakers,
    infer_entry_mode,
    run_regime_backtest,
)

__version__ = "0.4.0"

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
    # classifier
    "SidewaysBias", "ClassifierConfig", "SidewaysAnalysis",
    "signal_volume_trend", "signal_test_count", "signal_range_width",
    "signal_duration", "signal_mtf_momentum",
    "analyze_sideways", "get_prior_regime", "resolve_entry_bias",
    # backtest
    "EntryMode", "ExitReason", "BacktestConfig",
    "Position", "TradeRecord", "BacktestStats", "BacktestResult",
    "CircuitBreakerState",
    "open_position", "manage_position", "close_position",
    "check_circuit_breakers", "infer_entry_mode", "run_regime_backtest",
]
