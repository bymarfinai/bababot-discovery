"""
sweep_detector.py — Liquidity Sweep Detection (Tier 1)
=========================================================
Design Doc reference: §3.4, §7.2.2.

Sweep definition: candle wick pierces liquidity level L, but close reverses
back to origin side. Signals institutional taking of SLs without commitment.

Formal conditions (Sweep at BSL, wick going up):
    1. highs[i] > L                          (wick tembus)
    2. closes[i] < L                         (close balik ke bawah)
    3. wick_penetration = highs[i] - L
       wick_penetration >= K1 × ATR(i)       (min significance, K1=0.15)
    4. upper_wick = highs[i] - max(open, close)
       body        = abs(close - open)
       upper_wick / max(body, eps) >= K2     (wick dominant, K2=1.5)

Scoring (Design Doc §7.2.2):
    sweep_score = 0.35 × pen_ratio_norm
                + 0.25 × close_back_ratio
                + 0.20 × wick_body_norm
                + 0.20 × vol_spike_norm

    where each component is normalized to [0, 1].

Sweep valid jika sweep_score >= 0.60 (config threshold).
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np

from ..liquidity.liquidity_map import LiquidityLevel, LevelSide, LiquidityMap


class SweepDirection(str, Enum):
    UP = "UP"      # Wick sweep BSL (bullish liquidity taken), close reverses down → BEARISH implication
    DOWN = "DOWN"  # Wick sweep SSL (bearish liquidity taken), close reverses up → BULLISH implication


@dataclass
class SweepEvent:
    """One detected liquidity sweep."""
    idx: int
    direction: SweepDirection
    level_price: float              # Level yang di-sweep
    level_category: str = ""        # e.g. "EQUAL_HL", "SWING_1H"
    level_weight: float = 0.0       # weight_score dari LiquidityLevel

    # Candle metrics
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    # Sweep metrics
    wick_penetration: float = 0.0
    wick_penetration_atr_ratio: float = 0.0
    close_back_distance: float = 0.0        # abs distance from level to close
    close_back_ratio: float = 0.0            # close_back / candle_range (0..1)
    wick_body_ratio: float = 0.0
    volume_spike_ratio: float = 0.0          # this_vol / avg_vol_last_N

    # Composite score
    sweep_score: float = 0.0                 # 0..1 quality score

    def __repr__(self):
        return (f"SweepEvent({self.direction.value}@{self.idx} L={self.level_price:.4f} "
                f"score={self.sweep_score:.2f})")


def _compute_atr(highs, lows, closes, period=14):
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1]))
    atr = np.zeros(n)
    for i in range(n):
        start = max(0, i - period + 1)
        atr[i] = float(np.mean(tr[start:i+1]))
    return atr


def _rolling_vol_avg(volumes, period=20):
    n = len(volumes)
    avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - period + 1)
        avg[i] = float(np.mean(volumes[start:i+1]))
    return avg


def detect_sweep_at_candle(
    idx: int,
    highs: np.ndarray, lows: np.ndarray, opens: np.ndarray,
    closes: np.ndarray, volumes: np.ndarray,
    level: LiquidityLevel,
    atr: float,
    vol_avg: float,
    min_wick_pen_atr: float = 0.15,
    min_wick_body_ratio: float = 1.5,
    min_score: float = 0.60,
) -> Optional[SweepEvent]:
    """
    Check if candle at `idx` sweeps `level`. Returns SweepEvent if valid, else None.

    Design Doc §3.4 (4 formal conditions) + §7.2.2 (score formula).
    """
    h, l, o, c = float(highs[idx]), float(lows[idx]), float(opens[idx]), float(closes[idx])
    v = float(volumes[idx])
    L = level.price
    candle_range = h - l
    if candle_range <= 0 or atr <= 0:
        return None

    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # BSL sweep: wick pierces up, close reverses down
    if level.side == LevelSide.BSL:
        if not (h > L and c < L):
            return None
        wick_pen = h - L
        # Condition: wick penetration significance
        pen_atr_ratio = wick_pen / atr
        if pen_atr_ratio < min_wick_pen_atr:
            return None
        # Condition: upper wick dominant
        wick_body = upper_wick / max(body, 1e-9)
        if wick_body < min_wick_body_ratio:
            return None
        direction = SweepDirection.UP
        close_back = L - c   # positive: how far close is below level
    # SSL sweep: wick pierces down, close reverses up
    else:  # SSL
        if not (l < L and c > L):
            return None
        wick_pen = L - l
        pen_atr_ratio = wick_pen / atr
        if pen_atr_ratio < min_wick_pen_atr:
            return None
        wick_body = lower_wick / max(body, 1e-9)
        if wick_body < min_wick_body_ratio:
            return None
        direction = SweepDirection.DOWN
        close_back = c - L

    close_back_ratio = close_back / candle_range if candle_range > 0 else 0
    vol_spike = v / max(vol_avg, 1e-9)

    # Normalize components to [0, 1]
    pen_norm = min(1.0, pen_atr_ratio / 0.6)          # 0.15 ATR → 0.25, 0.6 ATR → 1.0
    close_back_norm = min(1.0, max(0.0, close_back_ratio))
    wick_body_norm = min(1.0, (wick_body - 1.0) / 3.0)  # 1.5 → 0.17, 4.0 → 1.0
    vol_norm = min(1.0, max(0.0, (vol_spike - 1.0) / 1.5))  # 2.5× vol → 1.0

    score = (0.35 * pen_norm + 0.25 * close_back_norm
             + 0.20 * wick_body_norm + 0.20 * vol_norm)

    if score < min_score:
        return None

    return SweepEvent(
        idx=idx,
        direction=direction,
        level_price=L,
        level_category=level.category.value,
        level_weight=level.weight_score,
        high=h, low=l, open=o, close=c, volume=v,
        wick_penetration=float(wick_pen),
        wick_penetration_atr_ratio=float(pen_atr_ratio),
        close_back_distance=float(close_back),
        close_back_ratio=float(close_back_ratio),
        wick_body_ratio=float(wick_body),
        volume_spike_ratio=float(vol_spike),
        sweep_score=float(score),
    )


def detect_sweeps(
    highs: np.ndarray, lows: np.ndarray, opens: np.ndarray,
    closes: np.ndarray, volumes: np.ndarray,
    liquidity_map: LiquidityMap,
    min_wick_pen_atr: float = 0.15,
    min_wick_body_ratio: float = 1.5,
    min_score: float = 0.60,
    atr_period: int = 14,
    vol_avg_period: int = 20,
    scan_last_n: Optional[int] = None,
) -> List[SweepEvent]:
    """
    Scan candles for sweeps of any level in LiquidityMap.

    Args:
        scan_last_n: if set, only scan last N candles (untuk live use).
                     None = scan all candles.
    """
    n = len(closes)
    if n < atr_period + 1:
        return []

    atr_arr = _compute_atr(highs, lows, closes, atr_period)
    vol_avg = _rolling_vol_avg(volumes, vol_avg_period)

    start = max(1, n - scan_last_n) if scan_last_n else 1
    events: List[SweepEvent] = []

    for i in range(start, n):
        atr_i = float(atr_arr[i])
        vol_avg_i = float(vol_avg[i])
        # Check each level: was it swept at candle i?
        for level in liquidity_map.levels:
            ev = detect_sweep_at_candle(
                i, highs, lows, opens, closes, volumes, level,
                atr=atr_i, vol_avg=vol_avg_i,
                min_wick_pen_atr=min_wick_pen_atr,
                min_wick_body_ratio=min_wick_body_ratio,
                min_score=min_score,
            )
            if ev is not None:
                events.append(ev)

    events.sort(key=lambda e: (e.idx, -e.sweep_score))
    return events


__all__ = [
    "SweepDirection", "SweepEvent",
    "detect_sweep_at_candle", "detect_sweeps",
]
