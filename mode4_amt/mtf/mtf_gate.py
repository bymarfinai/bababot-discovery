"""
mtf_gate.py — MTF Gate: combine HTF bias + 1h signal + LTF confirmation
=========================================================================
Final gate untuk emit trade signal setelah semua context confluence:

    1. 1h Sub-4A/4B signal detected
    2. HTF (4h) bias searah dengan signal direction
    3. LTF (15m) konfirmasi entry
    4. If all 3 pass → emit MTFDecision dengan LTF entry price + LTF SL

Otherwise: skip trade.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from .htf_bias import compute_htf_bias, BiasResult, HTFBias
from .ltf_confirmation import wait_ltf_confirmation, LTFConfirmation


@dataclass
class MTFDecision:
    """Final MTF-filtered trade decision."""
    is_valid: bool
    direction: str = ""              # "LONG" or "SHORT"
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp1_price: float = 0.0           # inherit from 1h signal
    tp2_price: float = 0.0
    tp3_price: float = 0.0
    initial_risk: float = 0.0
    rr_at_tp1: float = 0.0
    entry_idx_15m: int = -1
    entry_ts_15m: int = 0

    # Context flags
    htf_bias: str = ""
    htf_strength: float = 0.0
    ltf_confirm_type: str = ""

    reject_reason: str = ""


@dataclass
class MTFGate:
    """Configuration for MTF gate."""
    require_htf_alignment: bool = True
    require_ltf_confirmation: bool = True
    ltf_wait_candles: int = 8         # 2 hours of 15m
    htf_min_strength: float = 0.5     # 2/3 confluence


def apply_mtf_gate(
    gate: MTFGate,
    signal_direction: str,
    signal_ts_ms: int,
    signal_entry: float,
    signal_sl: float,
    signal_tp1: float,
    signal_tp2: float,
    signal_tp3: float,
    fvg_gap_low: float,
    fvg_gap_high: float,
    htf_data: dict,                  # {'times', 'highs', 'lows', 'closes', 'volumes'}
    ltf_data: dict,                  # {'times', 'highs', 'lows', 'closes'}
) -> MTFDecision:
    """
    Apply full MTF gate pipeline.

    Returns MTFDecision with is_valid=True dan updated entry/SL (from LTF),
    inherited TPs (from 1h signal).
    """
    # === 1. HTF Bias check ===
    bias = compute_htf_bias(
        htf_data['times'], htf_data['highs'], htf_data['lows'],
        htf_data['closes'], htf_data['volumes'],
        at_ts_ms=signal_ts_ms)

    if gate.require_htf_alignment:
        if signal_direction == "LONG" and bias.bias != HTFBias.BULL:
            return MTFDecision(is_valid=False,
                              htf_bias=bias.bias.value,
                              htf_strength=bias.strength,
                              reject_reason=f"HTF not bullish (got {bias.bias.value})")
        if signal_direction == "SHORT" and bias.bias != HTFBias.BEAR:
            return MTFDecision(is_valid=False,
                              htf_bias=bias.bias.value,
                              htf_strength=bias.strength,
                              reject_reason=f"HTF not bearish (got {bias.bias.value})")
        if bias.strength < gate.htf_min_strength:
            return MTFDecision(is_valid=False,
                              htf_bias=bias.bias.value,
                              htf_strength=bias.strength,
                              reject_reason=f"HTF strength too low ({bias.strength:.2f})")

    # === 2. LTF Confirmation ===
    if gate.require_ltf_confirmation:
        conf = wait_ltf_confirmation(
            ltf_data['times'], ltf_data['highs'], ltf_data['lows'], ltf_data['closes'],
            signal_ts_ms=signal_ts_ms,
            signal_direction=signal_direction,
            reference_level=signal_entry,
            fvg_zone_low=fvg_gap_low, fvg_zone_high=fvg_gap_high,
            wait_window_candles=gate.ltf_wait_candles)

        if not conf.is_confirmed:
            return MTFDecision(is_valid=False,
                              htf_bias=bias.bias.value,
                              htf_strength=bias.strength,
                              reject_reason=f"LTF: {conf.reason}")

        # Use LTF entry + SL
        entry_final = conf.entry_price
        sl_final = conf.sl_price_ltf
        # Inherit TP from 1h signal (kalau LTF entry beda dari 1h entry, RR bisa berubah)
        entry_idx = conf.entry_idx_15m
        entry_ts = int(ltf_data['times'][conf.entry_idx_15m])
        confirm_type = conf.confirmation_type
    else:
        entry_final = signal_entry
        sl_final = signal_sl
        entry_idx = -1
        entry_ts = signal_ts_ms
        confirm_type = "SKIPPED"

    # === Validate direction consistency ===
    is_long = signal_direction == "LONG"
    if is_long and (entry_final <= sl_final or entry_final >= signal_tp1):
        return MTFDecision(is_valid=False, reject_reason="Invalid LONG geometry")
    if not is_long and (entry_final >= sl_final or entry_final <= signal_tp1):
        return MTFDecision(is_valid=False, reject_reason="Invalid SHORT geometry")

    risk = abs(entry_final - sl_final)
    if risk <= 0:
        return MTFDecision(is_valid=False, reject_reason="Zero risk")
    rr1 = abs(signal_tp1 - entry_final) / risk

    return MTFDecision(
        is_valid=True,
        direction=signal_direction,
        entry_price=entry_final, sl_price=sl_final,
        tp1_price=signal_tp1, tp2_price=signal_tp2, tp3_price=signal_tp3,
        initial_risk=risk, rr_at_tp1=rr1,
        entry_idx_15m=entry_idx, entry_ts_15m=entry_ts,
        htf_bias=bias.bias.value, htf_strength=bias.strength,
        ltf_confirm_type=confirm_type,
    )


__all__ = ["MTFGate", "MTFDecision", "apply_mtf_gate"]
