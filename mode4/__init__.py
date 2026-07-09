"""BabaBot Mode4 — Trend-Following Bot (Hedge for Mode3)."""
from .config import Mode4Config
from .switcher import Switcher, Position, Trade
from mode3.indicators import compute_ema_series

__all__ = [
    "Mode4Config",
    "Switcher",
    "Position",
    "Trade",
    "compute_ema_series",
]
