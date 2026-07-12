"""
bos_choch.py — Break of Structure & Change of Character Detection
====================================================================
Design Doc reference: §3.1, §2.5.

BOS (Break of Structure):
    BOS_UP:   close melampaui last_swing_high, dan minimal 1 HH exists sebelumnya
              (konteks uptrend continuation)
    BOS_DOWN: close di bawah last_swing_low, dan minimal 1 LL exists sebelumnya
              (konteks downtrend continuation)

CHoCH (Change of Character):
    CHoCH_UP:   HH pertama muncul setelah rangkaian LL (downtrend → bullish shift)
    CHoCH_DOWN: LL pertama muncul setelah rangkaian HH (uptrend → bearish shift)

Kedua sinyal ini adalah timing gate untuk Sub-Strategy 4A (BOS untuk continuation)
dan 4B (CHoCH untuk reversal).
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np

from .swing_detector import Swing, SwingType, last_swing_before
from .structure_labels import LabeledSwing, StructureLabel


class EventType(str, Enum):
    BOS_UP = "BOS_UP"
    BOS_DOWN = "BOS_DOWN"
    CHOCH_UP = "CHOCH_UP"      # Bullish shift
    CHOCH_DOWN = "CHOCH_DOWN"  # Bearish shift


@dataclass
class StructureEvent:
    """Satu event struktural (BOS/CHoCH)."""
    idx: int                  # Index candle di mana event trigger
    event_type: EventType
    reference_price: float    # Level yang di-break (swing high/low)
    close_price: float        # Close candle trigger
    swing_ref_idx: int        # Index swing yang di-reference

    def __repr__(self):
        return (f"{self.event_type.value}@{self.idx} "
                f"close={self.close_price:.4f} ref={self.reference_price:.4f}")


def detect_structure_events(
    closes: np.ndarray,
    swings: List[Swing],
    labeled_swings: List[LabeledSwing],
    recent_hh_lookback: int = 10,
    choch_min_prior_swings: int = 2,
) -> List[StructureEvent]:
    """
    Deteksi semua event BOS dan CHoCH sepanjang array closes.

    Args:
        closes: array of close prices
        swings: raw swings (from detect_swings)
        labeled_swings: labeled swings (from label_swings)
        recent_hh_lookback: berapa swing terakhir untuk cek "already trending"
        choch_min_prior_swings: minimum swing prior dengan opposite bias
                                sebelum CHoCH dianggap valid

    Returns:
        List of StructureEvent, sorted by idx.

    Design Doc §3.1: is_BOS_UP, is_BOS_DOWN, is_CHoCH_UP, is_CHoCH_DOWN.
    """
    n = len(closes)
    closes = np.asarray(closes, dtype=np.float64)
    events: List[StructureEvent] = []

    # Track state: last event index untuk anti-duplicate near same swing
    last_bos_up_ref: Optional[int] = None
    last_bos_down_ref: Optional[int] = None

    # We iterate candle by candle (not swing by swing) because BOS is triggered
    # by close beyond swing, which may happen many candles after swing formed.
    for i in range(1, n):
        c = float(closes[i])

        # Find last swing high and swing low BEFORE index i.
        # (Swing itself formed at idx s.idx, but confirmed s.idx + N candles later.
        #  For BOS, we use the fact that once swing is in `swings` list, kita boleh
        #  reference-nya di candle > s.idx + N.)
        last_high = last_swing_before(swings, i, SwingType.HIGH)
        last_low = last_swing_before(swings, i, SwingType.LOW)

        # BOS_UP: close > last_swing_high AND uptrend context
        if last_high is not None and c > last_high.price:
            # Anti-duplicate: kalau reference swing sama seperti sebelumnya, skip
            if last_bos_up_ref != last_high.idx:
                # Context check: minimal 1 HH exists di swings sebelum last_high
                priors = [ls for ls in labeled_swings
                          if ls.idx < last_high.idx][-recent_hh_lookback:]
                has_hh_prior = any(ls.label == StructureLabel.HH for ls in priors)

                # Also check: NOT already in fresh downtrend
                # (heuristic: last 2 swings both LL means active downtrend)
                is_active_downtrend = (
                    len(priors) >= 2
                    and priors[-1].label == StructureLabel.LL
                    and priors[-2].label == StructureLabel.LL
                )

                if has_hh_prior and not is_active_downtrend:
                    events.append(StructureEvent(
                        idx=i, event_type=EventType.BOS_UP,
                        reference_price=last_high.price,
                        close_price=c,
                        swing_ref_idx=last_high.idx,
                    ))
                    last_bos_up_ref = last_high.idx

        # BOS_DOWN: close < last_swing_low AND downtrend context
        if last_low is not None and c < last_low.price:
            if last_bos_down_ref != last_low.idx:
                priors = [ls for ls in labeled_swings
                          if ls.idx < last_low.idx][-recent_hh_lookback:]
                has_ll_prior = any(ls.label == StructureLabel.LL for ls in priors)
                is_active_uptrend = (
                    len(priors) >= 2
                    and priors[-1].label == StructureLabel.HH
                    and priors[-2].label == StructureLabel.HH
                )

                if has_ll_prior and not is_active_uptrend:
                    events.append(StructureEvent(
                        idx=i, event_type=EventType.BOS_DOWN,
                        reference_price=last_low.price,
                        close_price=c,
                        swing_ref_idx=last_low.idx,
                    ))
                    last_bos_down_ref = last_low.idx

    # CHoCH detection — iterate over labeled_swings, not candles.
    # CHoCH_UP: HH forms after >= choch_min_prior_swings of LL/LH bias
    # CHoCH_DOWN: LL forms after >= choch_min_prior_swings of HH/HL bias
    for j, ls in enumerate(labeled_swings):
        priors = labeled_swings[max(0, j - 4):j]  # look at 4 prior swings
        if len(priors) < choch_min_prior_swings:
            continue

        prior_labels = [p.label for p in priors]
        bearish_count = sum(1 for lbl in prior_labels
                            if lbl in [StructureLabel.LL, StructureLabel.LH])
        bullish_count = sum(1 for lbl in prior_labels
                            if lbl in [StructureLabel.HH, StructureLabel.HL])

        # CHoCH_UP: HH after bearish structure dominant
        if (ls.label == StructureLabel.HH
                and bearish_count >= choch_min_prior_swings
                and bearish_count > bullish_count):
            events.append(StructureEvent(
                idx=ls.idx, event_type=EventType.CHOCH_UP,
                reference_price=ls.price,
                close_price=float(closes[ls.idx]),
                swing_ref_idx=ls.idx,
            ))

        # CHoCH_DOWN: LL after bullish structure dominant
        if (ls.label == StructureLabel.LL
                and bullish_count >= choch_min_prior_swings
                and bullish_count > bearish_count):
            events.append(StructureEvent(
                idx=ls.idx, event_type=EventType.CHOCH_DOWN,
                reference_price=ls.price,
                close_price=float(closes[ls.idx]),
                swing_ref_idx=ls.idx,
            ))

    # Sort by idx
    events.sort(key=lambda e: (e.idx, e.event_type.value))
    return events


def get_most_recent_event(
    events: List[StructureEvent],
    idx_before: int,
    event_types: Optional[List[EventType]] = None,
) -> Optional[StructureEvent]:
    """
    Return most recent event with idx < idx_before, optionally filtered by type.
    """
    result = None
    for e in events:
        if e.idx >= idx_before:
            break
        if event_types is not None and e.event_type not in event_types:
            continue
        result = e
    return result


__all__ = [
    "EventType", "StructureEvent",
    "detect_structure_events", "get_most_recent_event",
]
