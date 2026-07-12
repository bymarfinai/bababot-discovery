"""
impulse_leg.py — Impulse Leg Identification
=============================================
Design Doc reference: §3.6.

Impulse leg = directional move dari swing low ke swing high (bullish) atau
swing high ke swing low (bearish) yang memenuhi 4 kondisi:

    Kondisi Impulse-1: minimal 5 candle antara swing endpoints
    Kondisi Impulse-2: minimal 80% candle di leg searah trend
    Kondisi Impulse-3: total move >= 1.5 × ATR(14) pada swing start
    Kondisi Impulse-4: tidak ada single retracement > 38.2% dari total range

Impulse legs jadi basis untuk:
- Zona 2.6 / 38.2% retracement calc (Sub-4A entry zone)
- Measured move TP projection (1.618× dan 2.618× extension)
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np

from .swing_detector import Swing, SwingType


class ImpulseDirection(str, Enum):
    BULLISH = "BULLISH"   # low → high
    BEARISH = "BEARISH"   # high → low


@dataclass
class ImpulseLeg:
    """Impulse leg identification result."""
    direction: ImpulseDirection
    start_idx: int
    end_idx: int
    start_price: float    # low (bullish) atau high (bearish)
    end_price: float      # high (bullish) atau low (bearish)

    # Diagnostics
    num_candles: int
    directional_candles_pct: float  # % candles searah
    total_move: float               # abs(end - start)
    atr_at_start: float             # ATR reference
    move_atr_ratio: float           # total_move / atr
    max_retracement_pct: float      # deepest counter-move dalam leg

    def range(self) -> float:
        return abs(self.end_price - self.start_price)

    def retracement_level(self, fib: float) -> float:
        """
        Compute Fibonacci retracement level.

        Args:
            fib: 0.382, 0.5, 0.618, 0.79 dst

        Returns:
            Price level. Bullish leg: level di antara start (low) dan end (high),
            retracement dari end ke bawah. Bearish: sebaliknya.
        """
        rng = self.range()
        if self.direction == ImpulseDirection.BULLISH:
            return self.end_price - rng * fib
        else:
            return self.end_price + rng * fib

    def extension_level(self, ext: float) -> float:
        """
        Compute measured-move extension level (untuk TP projection).

        Args:
            ext: 1.618, 2.618 dst

        Returns:
            Bullish: start + rng * ext (target di atas start)
            Bearish: start - rng * ext
        """
        rng = self.range()
        if self.direction == ImpulseDirection.BULLISH:
            return self.start_price + rng * ext
        else:
            return self.start_price - rng * ext

    def __repr__(self):
        return (f"ImpulseLeg({self.direction.value} "
                f"[{self.start_idx}→{self.end_idx}] "
                f"{self.start_price:.4f}→{self.end_price:.4f} "
                f"atr={self.move_atr_ratio:.2f}x)")


def _compute_atr(highs, lows, closes, period=14):
    """Rolling ATR array."""
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1]),
        )
    atr = np.zeros(n)
    for i in range(n):
        start = max(0, i - period + 1)
        atr[i] = float(np.mean(tr[start:i+1]))
    return atr


def detect_impulse_legs(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    swings: List[Swing],
    min_candles: int = 5,
    min_directional_pct: float = 0.80,
    min_atr_ratio: float = 1.5,
    max_retracement_pct: float = 0.382,
    atr_period: int = 14,
) -> List[ImpulseLeg]:
    """
    Deteksi impulse legs dari pasangan swing berurutan.

    Design Doc §3.6: 4 kondisi validity.

    Iteration: untuk setiap pasangan (swing_a, swing_b) berurutan di list swings
    (bukan swing pair sembarang), cek apakah leg valid.

    Args:
        highs, lows, closes: OHLCV arrays
        swings: list of Swing sorted by idx
        min_candles: min 5 candles (Kondisi Impulse-1)
        min_directional_pct: min 80% directional candles (Kondisi Impulse-2)
        min_atr_ratio: min 1.5× ATR (Kondisi Impulse-3)
        max_retracement_pct: max 38.2% retracement dalam leg (Kondisi Impulse-4)
        atr_period: ATR period

    Returns:
        List of ImpulseLeg, sorted by end_idx.
    """
    n = len(closes)
    if n < min_candles + atr_period:
        return []

    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    closes = np.asarray(closes, dtype=np.float64)
    opens_approx = np.concatenate([[closes[0]], closes[:-1]])  # prev close as open

    atr_arr = _compute_atr(highs, lows, closes, period=atr_period)
    legs: List[ImpulseLeg] = []

    # Pair adjacent opposite swings
    for k in range(len(swings) - 1):
        s_a = swings[k]
        s_b = swings[k + 1]

        # Legs go from HIGH→LOW (bearish) or LOW→HIGH (bullish)
        if s_a.swing_type == s_b.swing_type:
            continue  # Same type, skip

        if s_a.swing_type == SwingType.LOW and s_b.swing_type == SwingType.HIGH:
            direction = ImpulseDirection.BULLISH
            start_price = s_a.price
            end_price = s_b.price
        elif s_a.swing_type == SwingType.HIGH and s_b.swing_type == SwingType.LOW:
            direction = ImpulseDirection.BEARISH
            start_price = s_a.price
            end_price = s_b.price
        else:
            continue

        start_idx = s_a.idx
        end_idx = s_b.idx
        num_candles = end_idx - start_idx

        # Kondisi Impulse-1
        if num_candles < min_candles:
            continue

        # Kondisi Impulse-2: directional candles pct
        leg_closes = closes[start_idx:end_idx + 1]
        leg_opens = opens_approx[start_idx:end_idx + 1]
        if direction == ImpulseDirection.BULLISH:
            directional = np.sum(leg_closes > leg_opens)
        else:
            directional = np.sum(leg_closes < leg_opens)
        directional_pct = directional / len(leg_closes)
        if directional_pct < min_directional_pct:
            continue

        # Kondisi Impulse-3: min ATR ratio
        atr_start = atr_arr[start_idx] if atr_arr[start_idx] > 0 else 1e-9
        total_move = abs(end_price - start_price)
        move_atr_ratio = total_move / atr_start
        if move_atr_ratio < min_atr_ratio:
            continue

        # Kondisi Impulse-4: max retracement pct in leg
        # Deep retracement = biggest counter-move within the leg
        if direction == ImpulseDirection.BULLISH:
            # For bullish leg, track deepest pullback: min low after each new high
            running_max = start_price
            deepest_pullback = 0.0
            for j in range(start_idx, end_idx + 1):
                if highs[j] > running_max:
                    running_max = highs[j]
                pullback = running_max - lows[j]
                if pullback > deepest_pullback:
                    deepest_pullback = pullback
            max_retrace = deepest_pullback / total_move if total_move > 0 else 0
        else:
            # Bearish: track deepest bounce
            running_min = start_price
            deepest_bounce = 0.0
            for j in range(start_idx, end_idx + 1):
                if lows[j] < running_min:
                    running_min = lows[j]
                bounce = highs[j] - running_min
                if bounce > deepest_bounce:
                    deepest_bounce = bounce
            max_retrace = deepest_bounce / total_move if total_move > 0 else 0

        if max_retrace > max_retracement_pct:
            continue

        legs.append(ImpulseLeg(
            direction=direction,
            start_idx=start_idx, end_idx=end_idx,
            start_price=start_price, end_price=end_price,
            num_candles=num_candles,
            directional_candles_pct=float(directional_pct),
            total_move=total_move,
            atr_at_start=float(atr_start),
            move_atr_ratio=float(move_atr_ratio),
            max_retracement_pct=float(max_retrace),
        ))

    return legs


__all__ = ["ImpulseDirection", "ImpulseLeg", "detect_impulse_legs"]
