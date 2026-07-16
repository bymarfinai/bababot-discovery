"""Mode3 BBC (Bull Bear Continuation) — v2.1 with POC breakout.
Reuses indicators from mode3 module.
"""
from .config import Mode3BBCConfig
from .switcher import Switcher, Trade, Position, MarkerState
from mode3 import compute_ema_series, compute_va_at_bar

__all__ = [
    'Mode3BBCConfig', 'Switcher', 'Trade', 'Position', 'MarkerState',
    'compute_ema_series', 'compute_va_at_bar',
]
