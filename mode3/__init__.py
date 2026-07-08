"""BabaBot Mode3 — clean rebuild per BabaBot_Switcher_Spec_v0_21."""
from .config import Mode3Config
from .switcher import Switcher, Position, Trade, MarkerState
from .indicators import compute_ema_series, compute_va_at_bar

__all__ = [
    "Mode3Config",
    "Switcher",
    "Position",
    "Trade",
    "MarkerState",
    "compute_ema_series",
    "compute_va_at_bar",
]
