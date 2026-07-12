"""
breakout_classifier.py — True Breakout Detection (Tier 1)
==============================================================
Design Doc reference: §3.5, §7.2.2.

Breakout = candle close beyond level L, dengan follow-through di M candle
berikutnya (all closes tetap di sisi baru) dan volume elevated.

Formal conditions (Breakout UP through BSL level L):
    1. closes[i] > L                                (close beyond)
    2. close_through = (closes[i] - L) / ATR >= K3  (min significance, K3=0.20)
    3. All closes[i+1..i+M] > L                     (follow-through, M=3)
    4. Volume in [i, i+M] avg >= K4 × vol_avg_prev  (K4=1.3)

Scoring (Design Doc §7.2.2):
    breakout_score = 0.35 × close_through_norm
                   + 0.25 × follow_through_ratio
                   + 0.20 × vol_sustain_norm
                   + 0.20 × body_strength_norm

Anti-conflict: breakout dan sweep pada level & candle sama = classified as SWEEP
(karena sweep more restrictive: close balik). Breakout classifier di sini hanya
dipanggil setelah candle close beyond level, dan sweep detector sudah negative.

Karena breakout membutuhkan candle mendatang (follow-through), sinyal ini
INHERENT DELAYED — hanya bisa dikonfirmasi di t + M.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np

from ..liquidity.liquidity_map import LiquidityLevel, LevelSide, LiquidityMap


class BreakoutDirection(str, Enum):
    UP = "UP"     # Close through BSL upward — bullish
    DOWN = "DOWN" # Close through SSL downward — bearish


@dataclass
class BreakoutEvent:
    """One classified true breakout."""
    idx: int                          # Candle idx where breakout initially triggered
    confirmation_idx: int             # Candle idx where follow-through completes
    direction: BreakoutDirection
    level_price: float
    level_category: str = ""
    level_weight: float = 0.0

    close_price: float = 0.0
    close_through: float = 0.0        # abs(close - level)
    close_through_atr_ratio: float = 0.0

    follow_through_candles: int = 0    # M
    follow_through_valid: int = 0      # count with close beyond L
    follow_through_ratio: float = 0.0  # valid / M

    volume_sustain_ratio: float = 0.0  # (avg vol in [i, i+M]) / (avg vol in [i-N, i-1])
    body_strength_ratio: float = 0.0   # body / range for trigger candle

    breakout_score: float = 0.0

    def __repr__(self):
        return (f"BreakoutEvent({self.direction.value}@{self.idx}"
                f"→conf@{self.confirmation_idx} L={self.level_price:.4f} "
                f"score={self.breakout_score:.2f})")


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


def classify_level_interaction(
    idx: int,
    highs: np.ndarray, lows: np.ndarray, opens: np.ndarray,
    closes: np.ndarray, volumes: np.ndarray,
    level: LiquidityLevel,
    atr: float,
    follow_through_candles: int = 3,
    min_close_through_atr: float = 0.20,
    min_follow_through_ratio: float = 0.80,
    min_vol_sustain: float = 1.30,
    min_score: float = 0.60,
    vol_lookback_prev: int = 10,
) -> Optional[BreakoutEvent]:
    """
    Check if candle at `idx` starts a true breakout through `level`, confirmed
    over next `follow_through_candles`.

    Returns None if:
    - Not a breakout direction (close not beyond level)
    - Insufficient close-through
    - Follow-through fails
    - Volume not sustained
    - Score below threshold

    Requires future data (idx + follow_through_candles). Caller must ensure
    that many candles exist ahead.
    """
    n = len(closes)
    if idx + follow_through_candles >= n:
        return None
    if atr <= 0:
        return None

    c = float(closes[idx])
    o = float(opens[idx])
    h = float(highs[idx])
    l = float(lows[idx])
    L = level.price

    # Direction check based on level side
    if level.side == LevelSide.BSL:
        # Breakout UP through BSL
        if c <= L:
            return None
        close_through = c - L
        direction = BreakoutDirection.UP
        # Follow-through: closes should stay above L
        ft_closes = closes[idx + 1: idx + 1 + follow_through_candles]
        ft_valid = int(np.sum(ft_closes > L))
    else:  # SSL
        # Breakout DOWN through SSL
        if c >= L:
            return None
        close_through = L - c
        direction = BreakoutDirection.DOWN
        ft_closes = closes[idx + 1: idx + 1 + follow_through_candles]
        ft_valid = int(np.sum(ft_closes < L))

    close_through_atr = close_through / atr
    if close_through_atr < min_close_through_atr:
        return None

    ft_ratio = ft_valid / follow_through_candles
    if ft_ratio < min_follow_through_ratio:
        return None

    # Volume sustain: avg of [idx..idx+M] / avg of prev N
    vol_range_start = max(0, idx - vol_lookback_prev)
    prev_vol_avg = float(np.mean(volumes[vol_range_start:idx])) if idx > vol_range_start else 1.0
    curr_vol_avg = float(np.mean(volumes[idx: idx + 1 + follow_through_candles]))
    vol_sustain = curr_vol_avg / max(prev_vol_avg, 1e-9)
    if vol_sustain < min_vol_sustain:
        return None

    # Body strength: how much of the candle was body (not wick)
    candle_range = h - l
    body = abs(c - o)
    body_strength = body / max(candle_range, 1e-9)

    # Composite score
    ct_norm = min(1.0, close_through_atr / 0.8)  # 0.2 ATR → 0.25, 0.8 ATR → 1.0
    ft_norm = ft_ratio
    vol_norm = min(1.0, max(0.0, (vol_sustain - 1.0) / 1.5))  # 2.5× → 1.0
    body_norm = min(1.0, body_strength)  # already 0..1

    score = (0.35 * ct_norm + 0.25 * ft_norm
             + 0.20 * vol_norm + 0.20 * body_norm)

    if score < min_score:
        return None

    return BreakoutEvent(
        idx=idx,
        confirmation_idx=idx + follow_through_candles,
        direction=direction,
        level_price=L,
        level_category=level.category.value,
        level_weight=level.weight_score,
        close_price=c,
        close_through=float(close_through),
        close_through_atr_ratio=float(close_through_atr),
        follow_through_candles=follow_through_candles,
        follow_through_valid=ft_valid,
        follow_through_ratio=float(ft_ratio),
        volume_sustain_ratio=float(vol_sustain),
        body_strength_ratio=float(body_strength),
        breakout_score=float(score),
    )


def detect_breakouts(
    highs: np.ndarray, lows: np.ndarray, opens: np.ndarray,
    closes: np.ndarray, volumes: np.ndarray,
    liquidity_map: LiquidityMap,
    follow_through_candles: int = 3,
    min_close_through_atr: float = 0.20,
    min_follow_through_ratio: float = 0.80,
    min_vol_sustain: float = 1.30,
    min_score: float = 0.60,
    atr_period: int = 14,
    scan_last_n: Optional[int] = None,
) -> List[BreakoutEvent]:
    """
    Scan candles for confirmed breakouts. Breakout kandidat di candle i,
    dikonfirmasi di i + follow_through_candles.
    """
    n = len(closes)
    if n < atr_period + follow_through_candles + 1:
        return []

    atr_arr = _compute_atr(highs, lows, closes, atr_period)

    # Cannot classify last M candles (no follow-through data yet)
    start = max(1, n - scan_last_n) if scan_last_n else 1
    end = n - follow_through_candles

    events: List[BreakoutEvent] = []

    for i in range(start, end):
        atr_i = float(atr_arr[i])
        for level in liquidity_map.levels:
            ev = classify_level_interaction(
                i, highs, lows, opens, closes, volumes, level,
                atr=atr_i,
                follow_through_candles=follow_through_candles,
                min_close_through_atr=min_close_through_atr,
                min_follow_through_ratio=min_follow_through_ratio,
                min_vol_sustain=min_vol_sustain,
                min_score=min_score,
            )
            if ev is not None:
                events.append(ev)

    events.sort(key=lambda e: (e.idx, -e.breakout_score))
    return events


__all__ = [
    "BreakoutDirection", "BreakoutEvent",
    "classify_level_interaction", "detect_breakouts",
]
