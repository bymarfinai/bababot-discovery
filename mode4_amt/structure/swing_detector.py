"""
swing_detector.py — Swing High/Low Detection
==============================================
Design Doc reference: §3.1 (Terminologi Struktur).

Formal N-bar swing:
    is_swing_high(i, N) = highs[i] > max(highs[i-N:i])
                         AND highs[i] > max(highs[i+1:i+N+1])
    is_swing_low(i, N)  = lows[i]  < min(lows[i-N:i])
                         AND lows[i]  < min(lows[i+1:i+N+1])

Note: swing hanya bisa dikonfirmasi SETELAH N candle forward closed.
Karena itu swing terbaru selalu N candle di belakang candle current.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np


class SwingType(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass
class Swing:
    """Identifikasi satu swing point."""
    idx: int              # Index dari candle swing
    swing_type: SwingType
    price: float          # highs[idx] untuk HIGH, lows[idx] untuk LOW
    timestamp_ms: int = 0 # Optional, jika tersedia
    lookback_n: int = 3   # N yang dipakai deteksi

    def __repr__(self):
        return f"Swing({self.swing_type.value}@{self.idx}={self.price:.4f})"


def detect_swings(
    highs: np.ndarray,
    lows: np.ndarray,
    lookback_n: int = 3,
    timestamps_ms: Optional[np.ndarray] = None,
) -> List[Swing]:
    """
    Deteksi semua swing high dan swing low dalam array.

    Args:
        highs, lows: numpy arrays
        lookback_n: N untuk N-bar swing (default 3, sesuai config 1h)
        timestamps_ms: optional, untuk populate Swing.timestamp_ms

    Returns:
        List of Swing objects, sorted by idx ascending.
        Swings di ujung array (< N atau > n-N-1) tidak dideteksi karena
        forward window belum lengkap.

    Design Doc §3.1: is_swing_high/is_swing_low formal definition.
    """
    n = len(highs)
    if n != len(lows):
        raise ValueError(f"highs/lows length mismatch: {n} vs {len(lows)}")
    if n < 2 * lookback_n + 1:
        return []

    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)

    swings: List[Swing] = []
    N = lookback_n

    # Iterate over candidates: index N to n-N-1 (inclusive)
    for i in range(N, n - N):
        # Swing HIGH check
        left_max_high = float(np.max(highs[i - N:i]))
        right_max_high = float(np.max(highs[i + 1:i + N + 1]))
        if highs[i] > left_max_high and highs[i] > right_max_high:
            swings.append(Swing(
                idx=i, swing_type=SwingType.HIGH, price=float(highs[i]),
                timestamp_ms=int(timestamps_ms[i]) if timestamps_ms is not None else 0,
                lookback_n=N,
            ))
            continue  # A single candle rarely both HIGH and LOW; skip low check

        # Swing LOW check
        left_min_low = float(np.min(lows[i - N:i]))
        right_min_low = float(np.min(lows[i + 1:i + N + 1]))
        if lows[i] < left_min_low and lows[i] < right_min_low:
            swings.append(Swing(
                idx=i, swing_type=SwingType.LOW, price=float(lows[i]),
                timestamp_ms=int(timestamps_ms[i]) if timestamps_ms is not None else 0,
                lookback_n=N,
            ))

    return swings


def last_swing_before(
    swings: List[Swing],
    idx: int,
    swing_type: Optional[SwingType] = None,
) -> Optional[Swing]:
    """
    Return the most recent swing BEFORE idx (strict <), optionally filtered
    by type. Returns None if no such swing exists.

    Useful for BOS/CHoCH detection where kita perlu "last swing high before
    current candle".
    """
    result = None
    for s in swings:
        if s.idx >= idx:
            break
        if swing_type is not None and s.swing_type != swing_type:
            continue
        result = s
    return result


def swings_between(
    swings: List[Swing],
    idx_start: int,
    idx_end: int,
) -> List[Swing]:
    """Return swings with idx in [idx_start, idx_end)."""
    return [s for s in swings if idx_start <= s.idx < idx_end]


__all__ = [
    "Swing", "SwingType", "detect_swings",
    "last_swing_before", "swings_between",
]
