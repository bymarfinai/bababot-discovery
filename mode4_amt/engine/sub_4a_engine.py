"""
sub_4a_engine.py — Sub-Strategy 4A: Breakout Continuation
=============================================================
Design Doc reference: §5.1, §7.4.

Sub-4A conditions (ALL must satisfy):
    A1. Balance state == IMBALANCE_CONFIRMED (breakout confirmed)
    A2. Impulse leg valid searah breakout (from Tier 0 structure)
    A3. Bullish FVG in retracement zone [38.2%, OTE] of impulse leg (long)
        Bearish FVG in retracement zone (short)
    A4. FVG state != FILLED
    A5. Structural confirmation OR strong Tier 1 BREAKOUT score
    A6. Setup Score >= threshold
    A7. Nearest opposing liquidity level (BSL for long) at min 1.5R from entry

Entry: FVG mid price
SL: below FVG.gap_low - 0.15×ATR (long) / above FVG.gap_high + 0.15×ATR (short)
TP1: nearest opposing liquidity level (50% close)
TP2: 1.618× extension of impulse leg (30% close)
TP3: 2.618× extension of impulse leg (20% close)

Risk-Reward calculation:
    R = abs(entry - SL)
    Min RR at TP1 must be >= 1.5R (else skip setup)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

from ..structure.impulse_leg import ImpulseLeg, ImpulseDirection
from ..tier1.breakout_classifier import BreakoutEvent
from ..tier3.fvg_detector import FVG, FVGDirection, FVGState, get_active_fvgs
from ..tier3.retracement_zone import compute_retracement_zone, fvg_in_zone
from ..tier3.setup_score import SetupCandidate, compute_setup_score
from ..liquidity.liquidity_map import LiquidityMap, LevelSide
from .balance_state import BalanceStateResult, BalanceState, ImbalanceDirection


@dataclass
class Sub4ACandidate:
    """A Sub-4A trade setup candidate."""
    symbol: str
    trigger_idx: int
    direction: str            # "LONG" or "SHORT"

    # Underlying components
    impulse_leg: Optional[ImpulseLeg] = None
    breakout: Optional[BreakoutEvent] = None
    fvg: Optional[FVG] = None
    retracement_zone_type: str = "OTE"

    # Entry/exit
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp1_price: float = 0.0
    tp2_price: float = 0.0
    tp3_price: float = 0.0

    # Scores
    tier1_score: float = 0.0
    tier3_fvg_quality: float = 0.0
    liquidity_target_weight: float = 0.0
    structural_alignment: float = 0.0
    mtf_context: float = 0.0
    setup_score: float = 0.0

    # RR
    initial_risk: float = 0.0
    rr_at_tp1: float = 0.0
    rr_at_tp2: float = 0.0
    rr_at_tp3: float = 0.0

    is_valid: bool = False
    reject_reason: str = ""


def detect_sub4a_setup(
    symbol: str,
    current_idx: int,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    atr: float,
    balance_state: BalanceStateResult,
    impulse_legs: List[ImpulseLeg],
    breakouts: List[BreakoutEvent],
    fvgs: List[FVG],
    liquidity_map: LiquidityMap,
    structural_confirm_score: float = 0.0,
    mtf_context_score: float = 0.5,
    min_setup_score: float = 0.60,
    min_rr_tp1: float = 1.2,
    prefer_zone: str = "OTE",
    fvg_max_age: int = 30,
    sl_buffer_atr: float = 0.15,
) -> Optional[Sub4ACandidate]:
    """
    Attempt to build a Sub-4A candidate at current_idx.

    Returns Sub4ACandidate if valid setup exists, else None.
    """
    # === Gate A1: state must be IMBALANCE_CONFIRMED ===
    if balance_state.state != BalanceState.IMBALANCE_CONFIRMED:
        return None
    if balance_state.imbalance_direction == ImbalanceDirection.NONE:
        return None
    if balance_state.active_breakout_idx < 0:
        return None

    direction = "LONG" if balance_state.imbalance_direction == ImbalanceDirection.UP else "SHORT"

    # === Gate A2: find valid impulse leg searah ===
    target_leg_dir = (ImpulseDirection.BULLISH if direction == "LONG"
                     else ImpulseDirection.BEARISH)
    valid_legs = [l for l in impulse_legs
                  if l.direction == target_leg_dir
                  and l.end_idx <= current_idx
                  and (current_idx - l.end_idx) <= fvg_max_age]
    if not valid_legs:
        return None
    leg = valid_legs[-1]  # most recent

    # === Gate A3-A4: FVG in retracement zone, not FILLED ===
    target_fvg_dir = (FVGDirection.BULLISH if direction == "LONG"
                     else FVGDirection.BEARISH)
    active_fvgs = get_active_fvgs(fvgs, at_idx=current_idx,
                                  direction=target_fvg_dir,
                                  max_age=fvg_max_age)
    # Restrict to FVGs formed during impulse leg
    active_fvgs = [f for f in active_fvgs
                   if leg.start_idx <= f.idx <= leg.end_idx]

    # Match against retracement zones (prefer OTE, fallback 38.2%)
    zone = compute_retracement_zone(leg, prefer_zone)
    matching = [f for f in active_fvgs if fvg_in_zone(f, zone, min_overlap_pct=0.20)]
    if not matching:
        # Try alternative zone
        alt_zone_type = "38.2%" if prefer_zone == "OTE" else "OTE"
        alt_zone = compute_retracement_zone(leg, alt_zone_type)
        matching = [f for f in active_fvgs if fvg_in_zone(f, alt_zone, min_overlap_pct=0.20)]
        if not matching:
            return None
        used_zone_type = alt_zone_type
    else:
        used_zone_type = prefer_zone
    # Pick highest-quality FVG
    fvg = max(matching, key=lambda f: f.quality_score)

    # === Compute entry, SL, TP ===
    entry = fvg.mid_price
    if direction == "LONG":
        sl = fvg.gap_low - sl_buffer_atr * atr
        # TP1: nearest BSL (opposing liquidity)
        nearest_bsl = liquidity_map.nearest_bsl()
        if nearest_bsl is None or nearest_bsl.price <= entry:
            tp1 = leg.end_price  # fallback
            tp1_weight = 0.6
        else:
            tp1 = nearest_bsl.price
            tp1_weight = nearest_bsl.weight_score
        tp2 = leg.extension_level(1.618)
        tp3 = leg.extension_level(2.618)
    else:  # SHORT
        sl = fvg.gap_high + sl_buffer_atr * atr
        nearest_ssl = liquidity_map.nearest_ssl()
        if nearest_ssl is None or nearest_ssl.price >= entry:
            tp1 = leg.end_price
            tp1_weight = 0.6
        else:
            tp1 = nearest_ssl.price
            tp1_weight = nearest_ssl.weight_score
        tp2 = leg.extension_level(1.618)
        tp3 = leg.extension_level(2.618)

    risk = abs(entry - sl)
    if risk <= 0:
        return None
    rr1 = abs(tp1 - entry) / risk
    rr2 = abs(tp2 - entry) / risk
    rr3 = abs(tp3 - entry) / risk

    # === Gate A7: min RR at TP1 ===
    if rr1 < min_rr_tp1:
        return None

    # === Compute scores ===
    # Tier 1: use breakout score
    breakout_events_for_state = [b for b in breakouts
                                 if b.idx == balance_state.active_breakout_idx]
    tier1_score = breakout_events_for_state[0].breakout_score if breakout_events_for_state else 0.5
    tier3_fvg = fvg.quality_score
    struct_align = structural_confirm_score
    mtf = mtf_context_score

    # === Build candidate and score ===
    candidate = Sub4ACandidate(
        symbol=symbol, trigger_idx=current_idx, direction=direction,
        impulse_leg=leg,
        breakout=breakout_events_for_state[0] if breakout_events_for_state else None,
        fvg=fvg, retracement_zone_type=used_zone_type,
        entry_price=entry, sl_price=sl,
        tp1_price=tp1, tp2_price=tp2, tp3_price=tp3,
        tier1_score=tier1_score,
        tier3_fvg_quality=tier3_fvg,
        liquidity_target_weight=tp1_weight,
        structural_alignment=struct_align,
        mtf_context=mtf,
        initial_risk=risk,
        rr_at_tp1=rr1, rr_at_tp2=rr2, rr_at_tp3=rr3,
    )
    sc = SetupCandidate(
        symbol=symbol, sub_strategy="4A", direction=direction,
        trigger_idx=current_idx,
        entry_price=entry, sl_price=sl,
        tp_prices=[tp1, tp2, tp3],
        tier1_score=tier1_score, tier1_type="BREAKOUT",
        tier3_fvg_quality=tier3_fvg,
        liquidity_target_weight=tp1_weight,
        structural_alignment=struct_align,
        mtf_context=mtf,
    )
    score_result = compute_setup_score(sc, min_score_threshold=min_setup_score)
    candidate.setup_score = score_result.setup_score
    candidate.is_valid = score_result.is_valid
    if not score_result.is_valid:
        candidate.reject_reason = (
            "; ".join(score_result.hard_gate_reasons)
            if score_result.hard_gate_reasons
            else f"setup_score {score_result.setup_score:.2f} < {min_setup_score}"
        )
    return candidate


__all__ = ["Sub4ACandidate", "detect_sub4a_setup"]
