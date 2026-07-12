"""
fvg_detector.py — Fair Value Gap Detection (Tier 3)
=======================================================
Design Doc reference: §3.3.

FVG (Fair Value Gap) = zona "untraded price" antara 3 candle berurutan.
Definisi formal (3-candle pattern di indeks i-2, i-1, i):

    BULLISH FVG (upward gap):
        highs[i-2] < lows[i]
        Zona gap: [highs[i-2], lows[i]]
        Middle candle biasanya bullish body (menandakan momentum push)

    BEARISH FVG (downward gap):
        lows[i-2] > highs[i]
        Zona gap: [highs[i], lows[i-2]]
        Middle candle biasanya bearish body

Quality metrics per FVG:
    - gap_size (absolute)
    - gap_size_atr (normalized)
    - middle_body_ratio (strong middle = more institutional)
    - freshness (age dalam candles)

State (updated as market progresses):
    UNTOUCHED  — belum ada retest
    PARTIAL    — sudah di-touch tapi belum di-fill
    FILLED     — sudah di-fill completely (invalid untuk entry)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import numpy as np


class FVGDirection(str, Enum):
    BULLISH = "BULLISH"    # Upward gap (support zone for pullbacks)
    BEARISH = "BEARISH"    # Downward gap (resistance zone for pullbacks)


class FVGState(str, Enum):
    UNTOUCHED = "UNTOUCHED"
    PARTIAL = "PARTIAL"     # Retested but not filled
    FILLED = "FILLED"       # Completely filled → invalid


@dataclass
class FVG:
    """One Fair Value Gap."""
    idx: int                 # Idx of the 3rd (closing) candle of pattern
    direction: FVGDirection

    # Gap boundaries
    gap_low: float           # Bottom of gap zone
    gap_high: float          # Top of gap zone

    # Quality metrics
    gap_size: float = 0.0            # gap_high - gap_low
    gap_size_atr_ratio: float = 0.0  # normalized
    middle_body_ratio: float = 0.0   # candle_body / candle_range at middle

    # State tracking (updated by update_fvg_states)
    state: FVGState = FVGState.UNTOUCHED
    touched_at_idx: int = -1
    filled_at_idx: int = -1

    # Composite quality score 0..1
    quality_score: float = 0.0

    @property
    def mid_price(self) -> float:
        return (self.gap_low + self.gap_high) / 2

    def contains(self, price: float) -> bool:
        return self.gap_low <= price <= self.gap_high

    def __repr__(self):
        return (f"FVG({self.direction.value}@{self.idx} "
                f"[{self.gap_low:.4f}-{self.gap_high:.4f}] "
                f"state={self.state.value} q={self.quality_score:.2f})")


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
        atr[i] = float(np.mean(tr[max(0, i-period+1):i+1]))
    return atr


def detect_fvgs(
    highs: np.ndarray,
    lows: np.ndarray,
    opens: np.ndarray,
    closes: np.ndarray,
    min_gap_atr_ratio: float = 0.15,
    min_middle_body_ratio: float = 0.40,
    atr_period: int = 14,
) -> List[FVG]:
    """
    Deteksi semua FVG di array. State awal semua UNTOUCHED.
    Call update_fvg_states() untuk update state berdasarkan price action selanjutnya.

    Args:
        min_gap_atr_ratio: gap minimum sebagai fraction ATR (default 0.15)
        min_middle_body_ratio: middle candle body ratio min (default 0.40)

    Returns:
        List of FVG objects sorted by idx.
    """
    n = len(closes)
    if n < 3:
        return []
    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    opens = np.asarray(opens, dtype=np.float64)
    closes = np.asarray(closes, dtype=np.float64)

    atr_arr = _compute_atr(highs, lows, closes, atr_period)

    fvgs: List[FVG] = []
    for i in range(2, n):
        # 3-candle pattern: i-2, i-1, i
        atr = atr_arr[i]
        if atr <= 0:
            continue

        h_prev2, l_prev2 = highs[i-2], lows[i-2]
        h_mid, l_mid = highs[i-1], lows[i-1]
        o_mid, c_mid = opens[i-1], closes[i-1]
        h_curr, l_curr = highs[i], lows[i]

        middle_range = h_mid - l_mid
        middle_body = abs(c_mid - o_mid)
        if middle_range <= 0:
            continue
        body_ratio = middle_body / middle_range

        # Bullish FVG: highs[i-2] < lows[i]
        if h_prev2 < l_curr:
            gap_low = float(h_prev2)
            gap_high = float(l_curr)
            gap_size = gap_high - gap_low
            gap_atr = gap_size / atr
            if gap_atr < min_gap_atr_ratio:
                continue
            if body_ratio < min_middle_body_ratio:
                continue
            # Also require middle candle bullish for cleaner signal
            if c_mid <= o_mid:
                continue
            # Quality: weighted combination of gap size + middle strength
            q = 0.6 * min(1.0, gap_atr / 0.6) + 0.4 * body_ratio
            fvgs.append(FVG(
                idx=i, direction=FVGDirection.BULLISH,
                gap_low=gap_low, gap_high=gap_high,
                gap_size=float(gap_size),
                gap_size_atr_ratio=float(gap_atr),
                middle_body_ratio=float(body_ratio),
                quality_score=float(q),
            ))

        # Bearish FVG: lows[i-2] > highs[i]
        elif l_prev2 > h_curr:
            gap_low = float(h_curr)
            gap_high = float(l_prev2)
            gap_size = gap_high - gap_low
            gap_atr = gap_size / atr
            if gap_atr < min_gap_atr_ratio:
                continue
            if body_ratio < min_middle_body_ratio:
                continue
            if c_mid >= o_mid:
                continue
            q = 0.6 * min(1.0, gap_atr / 0.6) + 0.4 * body_ratio
            fvgs.append(FVG(
                idx=i, direction=FVGDirection.BEARISH,
                gap_low=gap_low, gap_high=gap_high,
                gap_size=float(gap_size),
                gap_size_atr_ratio=float(gap_atr),
                middle_body_ratio=float(body_ratio),
                quality_score=float(q),
            ))

    return fvgs


def update_fvg_states(
    fvgs: List[FVG],
    highs: np.ndarray,
    lows: np.ndarray,
    up_to_idx: Optional[int] = None,
) -> None:
    """
    Update state of each FVG based on price action after formation.

    Rules:
        UNTOUCHED → PARTIAL: harga masuk ke gap range (low <= gap_high AND high >= gap_low)
                             tapi belum menyeberang penuh
        PARTIAL   → FILLED: bullish FVG di-fill jika low <= gap_low; bearish jika high >= gap_high

    Mutates fvgs in place.

    Args:
        up_to_idx: only scan up to this candle idx (for lookahead safety in backtest).
                   Default: scan seluruh array.
    """
    n = len(highs)
    end = up_to_idx if up_to_idx is not None else n
    end = min(end, n)

    for fvg in fvgs:
        if fvg.state == FVGState.FILLED:
            continue
        # Scan from candle AFTER formation
        for j in range(fvg.idx + 1, end):
            h, l = highs[j], lows[j]
            in_zone = (l <= fvg.gap_high) and (h >= fvg.gap_low)
            if not in_zone:
                continue
            if fvg.state == FVGState.UNTOUCHED:
                fvg.state = FVGState.PARTIAL
                fvg.touched_at_idx = j
            # Check fill: full penetration through gap
            if fvg.direction == FVGDirection.BULLISH and l <= fvg.gap_low:
                fvg.state = FVGState.FILLED
                fvg.filled_at_idx = j
                break
            if fvg.direction == FVGDirection.BEARISH and h >= fvg.gap_high:
                fvg.state = FVGState.FILLED
                fvg.filled_at_idx = j
                break


def get_active_fvgs(
    fvgs: List[FVG],
    at_idx: int,
    direction: Optional[FVGDirection] = None,
    max_age: Optional[int] = None,
) -> List[FVG]:
    """
    Return FVGs still valid (not FILLED) at candle `at_idx`, optionally filtered
    by direction and max age.
    """
    result = []
    for fvg in fvgs:
        if fvg.idx > at_idx:
            continue  # not yet formed
        if fvg.state == FVGState.FILLED and fvg.filled_at_idx <= at_idx:
            continue
        if direction is not None and fvg.direction != direction:
            continue
        if max_age is not None and (at_idx - fvg.idx) > max_age:
            continue
        result.append(fvg)
    return result


__all__ = [
    "FVG", "FVGDirection", "FVGState",
    "detect_fvgs", "update_fvg_states", "get_active_fvgs",
]
