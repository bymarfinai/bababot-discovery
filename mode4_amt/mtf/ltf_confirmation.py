"""
ltf_confirmation.py — Lower Timeframe (15m) Entry Confirmation
================================================================
Setelah signal 1h + HTF bias searah, tunggu konfirmasi di 15m sebelum entry.

Konfirmasi types:
    1. Mini-BOS: 15m close melampaui 15m swing di arah signal
    2. Mini-FVG retest: 15m FVG di zona 1h FVG, price tap-and-reverse
    3. Simple bounce: 15m candle close above/below reference level

Return: entry_idx_15m, entry_price, structural_sl (dari 15m swing)

Kalau tidak ada konfirmasi dalam `wait_window_15m` candles → skip signal.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..structure.swing_detector import detect_swings, SwingType
from ..structure.structure_labels import label_swings
from ..structure.bos_choch import detect_structure_events, EventType


@dataclass
class LTFConfirmation:
    is_confirmed: bool
    entry_idx_15m: int = -1
    entry_price: float = 0.0
    sl_price_ltf: float = 0.0        # structural SL based on 15m swing
    confirmation_type: str = ""       # "MINI_BOS" / "MINI_FVG_RETEST" / "BOUNCE"
    reason: str = ""


def wait_ltf_confirmation(
    ltf_times: np.ndarray,           # 15m timestamps (ms)
    ltf_highs: np.ndarray,
    ltf_lows: np.ndarray,
    ltf_closes: np.ndarray,
    signal_ts_ms: int,               # 1h signal candle timestamp
    signal_direction: str,           # "LONG" or "SHORT"
    reference_level: float,          # 1h FVG mid or signal entry price
    fvg_zone_low: float,             # 1h FVG lower bound (for retest check)
    fvg_zone_high: float,            # 1h FVG upper bound
    wait_window_candles: int = 8,    # 8 × 15m = 2 hours
    ltf_swing_n: int = 2,
) -> LTFConfirmation:
    """
    Scan 15m candles after signal_ts_ms untuk cari konfirmasi entry.

    Returns LTFConfirmation with is_confirmed=True kalau ada konfirmasi
    dalam window, dengan entry_idx_15m dan structural SL dari 15m.
    """
    # Find starting 15m candle: first candle at or after signal_ts_ms
    start_idx = int(np.searchsorted(ltf_times, signal_ts_ms, side='left'))
    end_idx = min(start_idx + wait_window_candles, len(ltf_times))
    if start_idx >= len(ltf_times) or end_idx - start_idx < 3:
        return LTFConfirmation(is_confirmed=False, reason="Insufficient LTF data")

    # Scan window
    for t in range(start_idx + 2, end_idx):
        # === CHECK 1: Simple bounce/close beyond reference ===
        # LONG: 15m close above reference AND price tapped fvg zone from above
        # SHORT: 15m close below reference AND price tapped fvg zone from below
        c = float(ltf_closes[t])
        h = float(ltf_highs[t])
        l = float(ltf_lows[t])

        # Did any prior LTF candle in window enter the FVG zone?
        window_lows = ltf_lows[start_idx:t+1]
        window_highs = ltf_highs[start_idx:t+1]
        tapped_zone = np.any((window_lows <= fvg_zone_high) & (window_highs >= fvg_zone_low))

        if not tapped_zone:
            continue

        if signal_direction == "LONG":
            # After tapping zone, want bullish confirmation candle
            if c > reference_level and c > float(ltf_closes[t-1]):
                # SL below the low of this candle or the touched zone low
                sl = min(float(np.min(window_lows)), l) - (h - l) * 0.1
                return LTFConfirmation(
                    is_confirmed=True, entry_idx_15m=t,
                    entry_price=c, sl_price_ltf=sl,
                    confirmation_type="BOUNCE",
                    reason=f"LTF bounce close@{c:.4f} > ref@{reference_level:.4f}")
        else:  # SHORT
            if c < reference_level and c < float(ltf_closes[t-1]):
                sl = max(float(np.max(window_highs)), h) + (h - l) * 0.1
                return LTFConfirmation(
                    is_confirmed=True, entry_idx_15m=t,
                    entry_price=c, sl_price_ltf=sl,
                    confirmation_type="BOUNCE",
                    reason=f"LTF drop close@{c:.4f} < ref@{reference_level:.4f}")

        # === CHECK 2: Mini-BOS on 15m ===
        if t - start_idx >= 4:
            sub_highs = ltf_highs[max(0, start_idx-5):t+1]
            sub_lows = ltf_lows[max(0, start_idx-5):t+1]
            sub_closes = ltf_closes[max(0, start_idx-5):t+1]
            swings = detect_swings(sub_highs, sub_lows, lookback_n=ltf_swing_n)
            if len(swings) >= 2:
                labeled = label_swings(swings)
                events = detect_structure_events(sub_closes, swings, labeled)
                for e in events:
                    ev_type = e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type)
                    if signal_direction == "LONG" and ev_type in ("BOS_UP", "CHOCH_UP"):
                        sl = float(np.min(sub_lows[max(0, e.idx-3):e.idx+1])) - (h-l)*0.2
                        return LTFConfirmation(
                            is_confirmed=True, entry_idx_15m=t,
                            entry_price=c, sl_price_ltf=sl,
                            confirmation_type="MINI_BOS",
                            reason=f"15m {ev_type}")
                    if signal_direction == "SHORT" and ev_type in ("BOS_DOWN", "CHOCH_DOWN"):
                        sl = float(np.max(sub_highs[max(0, e.idx-3):e.idx+1])) + (h-l)*0.2
                        return LTFConfirmation(
                            is_confirmed=True, entry_idx_15m=t,
                            entry_price=c, sl_price_ltf=sl,
                            confirmation_type="MINI_BOS",
                            reason=f"15m {ev_type}")

    return LTFConfirmation(is_confirmed=False, reason=f"No confirmation in {wait_window_candles} candles")


__all__ = ["LTFConfirmation", "wait_ltf_confirmation"]
