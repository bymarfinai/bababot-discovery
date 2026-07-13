"""
htf_bias.py — Higher Timeframe (4h) Bias Classifier
=====================================================
Determines regime context untuk filter signal 1h.

Inputs:
    - 4h OHLCV
    - Timestamp yang mau di-query (1h signal ts)

Logic (3 confluence checks):
    1. EMA20 slope on 4h (last 20 candles): positive = bull tilt
    2. Position vs 4h VP: above VAH = bullish imbalance, below VAL = bearish
    3. Recent structure: last major 4h swing (HH or LL dominance)

Output: BULL / BEAR / NEUTRAL
Signals only fired jika bias.direction sesuai signal direction.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np

from ..zones.volume_profile import compute_volume_profile
from ..structure.swing_detector import detect_swings, SwingType
from ..structure.structure_labels import label_swings, get_trend_bias


class HTFBias(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"


@dataclass
class BiasResult:
    bias: HTFBias
    strength: float                # 0-1, higher = stronger conviction
    ema_slope: float               # % change
    va_position: str               # "ABOVE_VAH" / "IN_VA" / "BELOW_VAL"
    structure_bias: str            # "UPTREND" / "DOWNTREND" / "MIXED"
    reason: str = ""


def _ema(arr, period):
    """Simple EMA."""
    alpha = 2 / (period + 1)
    ema = np.zeros_like(arr, dtype=np.float64)
    ema[0] = arr[0]
    for i in range(1, len(arr)):
        ema[i] = alpha * arr[i] + (1 - alpha) * ema[i-1]
    return ema


def compute_htf_bias(
    htf_times: np.ndarray,
    htf_highs: np.ndarray,
    htf_lows: np.ndarray,
    htf_closes: np.ndarray,
    htf_volumes: np.ndarray,
    at_ts_ms: int,
    ema_period: int = 20,
    vp_window: int = 100,
    swing_n: int = 3,
) -> BiasResult:
    """
    Compute 4h bias at time `at_ts_ms` using data up to (but not including)
    the 4h candle containing that timestamp.

    Uses only historical HTF candles (no lookahead).
    """
    # Find HTF candle index at or before at_ts_ms (use only past candles)
    idx = int(np.searchsorted(htf_times, at_ts_ms, side='right') - 1)
    if idx < ema_period:
        return BiasResult(bias=HTFBias.NEUTRAL, strength=0.0,
                         ema_slope=0.0, va_position="UNKNOWN",
                         structure_bias="UNDEFINED",
                         reason="Insufficient HTF history")

    closes = htf_closes[:idx+1]
    highs = htf_highs[:idx+1]
    lows = htf_lows[:idx+1]
    volumes = htf_volumes[:idx+1]
    current = float(closes[-1])

    # 1. EMA slope
    ema_arr = _ema(closes, ema_period)
    ema_slope = (ema_arr[-1] - ema_arr[-ema_period]) / ema_arr[-ema_period] if ema_arr[-ema_period] > 0 else 0
    ema_bull = ema_slope > 0.005    # >0.5% slope
    ema_bear = ema_slope < -0.005

    # 2. Volume Profile position
    va_pos = "UNKNOWN"
    va_bull = va_bear = False
    if len(closes) >= vp_window:
        vp = compute_volume_profile(
            highs[-vp_window:], lows[-vp_window:],
            closes[-vp_window:], volumes[-vp_window:],
            num_bins=50, value_area_pct=0.70)
        if vp.is_valid:
            if current > vp.vah:
                va_pos = "ABOVE_VAH"; va_bull = True
            elif current < vp.val:
                va_pos = "BELOW_VAL"; va_bear = True
            else:
                va_pos = "IN_VA"

    # 3. Structure bias
    swings = detect_swings(highs, lows, lookback_n=swing_n)
    if len(swings) >= 4:
        labeled = label_swings(swings)
        struct_bias = get_trend_bias(labeled, lookback=6)
    else:
        struct_bias = "UNDEFINED"

    struct_bull = struct_bias == "UPTREND"
    struct_bear = struct_bias == "DOWNTREND"

    # === Confluence rule ===
    # Bull: at least 2 of 3 checks agree
    bull_score = int(ema_bull) + int(va_bull) + int(struct_bull)
    bear_score = int(ema_bear) + int(va_bear) + int(struct_bear)

    if bull_score >= 2 and bear_score == 0:
        bias = HTFBias.BULL
        strength = bull_score / 3.0
        reason = f"ema={ema_slope:.3f}({'✓' if ema_bull else '·'}) va={va_pos}({'✓' if va_bull else '·'}) struct={struct_bias}({'✓' if struct_bull else '·'})"
    elif bear_score >= 2 and bull_score == 0:
        bias = HTFBias.BEAR
        strength = bear_score / 3.0
        reason = f"ema={ema_slope:.3f}({'✓' if ema_bear else '·'}) va={va_pos}({'✓' if va_bear else '·'}) struct={struct_bias}({'✓' if struct_bear else '·'})"
    else:
        bias = HTFBias.NEUTRAL
        strength = 0.0
        reason = f"conflicted: bull_score={bull_score} bear_score={bear_score}"

    return BiasResult(
        bias=bias, strength=strength,
        ema_slope=float(ema_slope),
        va_position=va_pos,
        structure_bias=struct_bias,
        reason=reason,
    )


__all__ = ["HTFBias", "BiasResult", "compute_htf_bias"]
