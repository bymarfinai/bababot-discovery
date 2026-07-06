"""mode3_regime v0.6 — 3-layer regime + adaptive entry rules"""

from .indicators import (
    ema, sma, atr, rolling_vwap, rolling_high_low,
    consecutive_count, slope_pct, rolling_volume_distribution,
)
from .regime import Regime, RegimeConfig, RegimeState, classify_regime_series
from .transition import Transition, TransitionConfig, TransitionState, classify_transitions
from .microevent import (
    MicroEvent, Bias, MicroEventConfig, BiasConfig,
    detect_micro_events, compute_bias_series,
)
from .entry_rules import EntrySide, EntryMode, EntryConfig, EntrySignal, generate_entry_signals
from .backtest import BacktestConfig, TradeRecord, BacktestStats, BacktestResult, run_backtest, ExitReason

__version__ = "0.6.0"

__all__ = [
    "ema", "sma", "atr", "rolling_vwap", "rolling_high_low",
    "consecutive_count", "slope_pct", "rolling_volume_distribution",
    "Regime", "RegimeConfig", "RegimeState", "classify_regime_series",
    "Transition", "TransitionConfig", "TransitionState", "classify_transitions",
    "MicroEvent", "Bias", "MicroEventConfig", "BiasConfig",
    "detect_micro_events", "compute_bias_series",
    "EntrySide", "EntryMode", "EntryConfig", "EntrySignal", "generate_entry_signals",
    "BacktestConfig", "TradeRecord", "BacktestStats", "BacktestResult", "run_backtest", "ExitReason",
]
