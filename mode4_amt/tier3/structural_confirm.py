"""
structural_confirm.py — Structural Confirmation (Tier 3)
============================================================
Design Doc reference: §7.2.3.

Setelah Tier 1 (sweep/breakout) confirmed, Tier 3 memerlukan structural
confirmation di lower timeframe / near-term structure:

    Sub-4A (Breakout Continuation):
        Butuh BOS_UP di small swing_n (lookback lebih pendek) DALAM window
        setelah breakout — konfirmasi bahwa momentum tidak lemah.

    Sub-4B (SFP Reversal, sweep-based):
        Butuh CHoCH_UP DALAM window setelah sweep — konfirmasi arah reversal.

Ini seperti "confirmation candle" di trader manual, tapi structural.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from ..structure.swing_detector import detect_swings, SwingType
from ..structure.structure_labels import label_swings
from ..structure.bos_choch import detect_structure_events, EventType, StructureEvent


@dataclass
class StructuralConfirmation:
    """Structural confirmation event after Tier 1 trigger."""
    is_confirmed: bool
    confirm_event: Optional[StructureEvent] = None
    confirm_idx: int = -1
    lookback_swing_n: int = 2
    strength_score: float = 0.0    # 0..1 quality


def check_structural_confirmation(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    trigger_idx: int,
    direction: str,            # "UP" or "DOWN"
    window: int = 8,           # candles setelah trigger untuk cari confirmation
    lookback_swing_n: int = 2, # smaller N untuk near-term swings
    require_event_type: Optional[str] = None,  # "BOS", "CHOCH", None=either
) -> StructuralConfirmation:
    """
    Cek apakah ada BOS/CHoCH searah `direction` dalam [trigger_idx+1, trigger_idx+window].

    Args:
        trigger_idx: idx candle Tier 1 event (sweep or breakout)
        direction: "UP" untuk bullish confirmation, "DOWN" untuk bearish
        window: candles ke depan yang di-scan
        lookback_swing_n: N untuk detect_swings (kecil = responsive)
        require_event_type: filter — "BOS" only, "CHOCH" only, None = both

    Returns:
        StructuralConfirmation with is_confirmed flag.
    """
    n = len(closes)
    end_idx = min(trigger_idx + window + 1, n)
    if end_idx - trigger_idx < lookback_swing_n * 2 + 2:
        return StructuralConfirmation(is_confirmed=False,
                                      lookback_swing_n=lookback_swing_n)

    # Detect swings + events di sub-array
    highs_sub = highs[:end_idx]
    lows_sub = lows[:end_idx]
    closes_sub = closes[:end_idx]

    swings = detect_swings(highs_sub, lows_sub, lookback_n=lookback_swing_n)
    if len(swings) < 2:
        return StructuralConfirmation(is_confirmed=False,
                                      lookback_swing_n=lookback_swing_n)

    labeled = label_swings(swings)
    events = detect_structure_events(closes_sub, swings, labeled,
                                     choch_min_prior_swings=1)

    # Find event dalam window matching direction
    target_types = []
    if direction == "UP":
        if require_event_type == "BOS":
            target_types = [EventType.BOS_UP]
        elif require_event_type == "CHOCH":
            target_types = [EventType.CHOCH_UP]
        else:
            target_types = [EventType.BOS_UP, EventType.CHOCH_UP]
    else:  # DOWN
        if require_event_type == "BOS":
            target_types = [EventType.BOS_DOWN]
        elif require_event_type == "CHOCH":
            target_types = [EventType.CHOCH_DOWN]
        else:
            target_types = [EventType.BOS_DOWN, EventType.CHOCH_DOWN]

    for e in events:
        if e.idx <= trigger_idx:
            continue
        if e.idx > trigger_idx + window:
            break
        if e.event_type in target_types:
            # Strength: how far the confirming candle closed beyond reference
            atr_approx = float(np.mean(np.abs(np.diff(closes_sub[-14:]))))
            if atr_approx <= 0:
                atr_approx = 1e-9
            close_diff = abs(e.close_price - e.reference_price)
            strength = min(1.0, close_diff / (atr_approx * 0.5))

            return StructuralConfirmation(
                is_confirmed=True,
                confirm_event=e,
                confirm_idx=e.idx,
                lookback_swing_n=lookback_swing_n,
                strength_score=float(strength),
            )

    return StructuralConfirmation(is_confirmed=False,
                                  lookback_swing_n=lookback_swing_n)


__all__ = ["StructuralConfirmation", "check_structural_confirmation"]
