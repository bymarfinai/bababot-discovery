"""
sub_4b_engine.py — Sub-Strategy 4B: SFP Reversal (Sweep + CHoCH)
=====================================================================
Design Doc reference: §5.2, §7.4.

Sub-4B conditions:
    B1. Balance state == SWEEP_REVERSAL
        (sweep at BSL/SSL + CHoCH searah reversal ≤ N candles)
    B2. Sweep quality (sweep_score) sufficient
    B3. CHoCH structural alignment: direction opposite of sweep
    B4. FVG formed AFTER sweep, DIRECTION searah reversal
    B5. FVG state != FILLED
    B6. Setup Score >= threshold

Entry: FVG mid (if available in reasonable location)
       OR CHoCH reference candle close price + 0.1×ATR (pullback entry)
SL:    beyond sweep wick extreme + 0.1×ATR buffer
       (for LONG after SSL sweep: SL = sweep_candle.low - 0.1×ATR)
       (for SHORT after BSL sweep: SL = sweep_candle.high + 0.1×ATR)
TP1:   POC (mean reversion target — 40% close)
TP2:   opposite VA boundary (VAH for long, VAL for short — 30% close)
TP3:   next major opposing liquidity level (30% close)

Sub-4B punya SL yang natural karena sweep wick memberi definisi
"institutional decision level" — kalau harga tembus sweep low lagi,
setup invalidated.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

from ..tier1.sweep_detector import SweepEvent, SweepDirection
from ..structure.bos_choch import StructureEvent, EventType
from ..tier3.fvg_detector import FVG, FVGDirection, FVGState, get_active_fvgs
from ..tier3.setup_score import SetupCandidate, compute_setup_score
from ..liquidity.liquidity_map import LiquidityMap, LevelSide
from .balance_state import BalanceStateResult, BalanceState, ImbalanceDirection


@dataclass
class Sub4BCandidate:
    """Sub-4B trade setup candidate."""
    symbol: str
    trigger_idx: int
    direction: str

    # Underlying components
    sweep_event: Optional[SweepEvent] = None
    choch_event: Optional[StructureEvent] = None
    fvg: Optional[FVG] = None

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

    initial_risk: float = 0.0
    rr_at_tp1: float = 0.0
    rr_at_tp2: float = 0.0
    rr_at_tp3: float = 0.0

    is_valid: bool = False
    reject_reason: str = ""


def detect_sub4b_setup(
    symbol: str,
    current_idx: int,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    atr: float,
    balance_state: BalanceStateResult,
    recent_sweeps: List[SweepEvent],
    structure_events: List[StructureEvent],
    fvgs: List[FVG],
    liquidity_map: LiquidityMap,
    poc: Optional[float],
    vah: Optional[float],
    val: Optional[float],
    structural_confirm_score: float = 0.0,
    mtf_context_score: float = 0.5,
    min_setup_score: float = 0.60,
    min_rr_tp1: float = 1.0,
    fvg_max_age: int = 15,
    sl_buffer_atr: float = 0.1,
) -> Optional[Sub4BCandidate]:
    """
    Attempt to build a Sub-4B candidate at current_idx.

    Sub-4B requires SWEEP_REVERSAL state. Entry after sweep + CHoCH,
    idealnya on FVG pullback.

    Returns Sub4BCandidate if valid, else None.
    """
    # === Gate B1: state must be SWEEP_REVERSAL ===
    if balance_state.state != BalanceState.SWEEP_REVERSAL:
        return None
    if balance_state.imbalance_direction == ImbalanceDirection.NONE:
        return None

    # Find the trigger sweep
    sweep = None
    for sw in recent_sweeps:
        if sw.idx == balance_state.active_sweep_idx:
            sweep = sw
            break
    if sweep is None:
        return None

    direction = "LONG" if balance_state.imbalance_direction == ImbalanceDirection.UP else "SHORT"

    # === Find CHoCH after sweep ===
    target_choch = (EventType.CHOCH_UP if direction == "LONG"
                   else EventType.CHOCH_DOWN)
    choch = None
    for ev in structure_events:
        if ev.idx > sweep.idx and ev.idx <= current_idx and ev.event_type == target_choch:
            choch = ev
            break
    if choch is None:
        return None

    # === Find FVG formed after sweep ===
    target_fvg_dir = (FVGDirection.BULLISH if direction == "LONG"
                     else FVGDirection.BEARISH)
    active_fvgs = get_active_fvgs(fvgs, at_idx=current_idx,
                                  direction=target_fvg_dir, max_age=fvg_max_age)
    # Restrict to FVGs formed AFTER sweep and BEFORE current
    active_fvgs = [f for f in active_fvgs
                   if sweep.idx <= f.idx <= current_idx]
    if not active_fvgs:
        return None
    # Pick highest-quality FVG
    fvg = max(active_fvgs, key=lambda f: f.quality_score)

    # === Entry, SL, TP ===
    entry = fvg.mid_price
    if direction == "LONG":
        # SL below sweep low (institutional invalidation point)
        sl = sweep.low - sl_buffer_atr * atr
        # TP hierarchy: POC → VAH → next major BSL
        tp1 = poc if poc is not None else fvg.gap_high + (fvg.gap_high - sl) * 1.0
        tp2 = vah if vah is not None else tp1 + atr
        nearest_bsl = liquidity_map.nearest_bsl()
        tp3 = nearest_bsl.price if nearest_bsl is not None else tp2 + atr
        tp1_weight = 0.85  # POC
    else:  # SHORT
        sl = sweep.high + sl_buffer_atr * atr
        tp1 = poc if poc is not None else fvg.gap_low - (sl - fvg.gap_low) * 1.0
        tp2 = val if val is not None else tp1 - atr
        nearest_ssl = liquidity_map.nearest_ssl()
        tp3 = nearest_ssl.price if nearest_ssl is not None else tp2 - atr
        tp1_weight = 0.85

    risk = abs(entry - sl)
    if risk <= 0:
        return None
    rr1 = abs(tp1 - entry) / risk
    rr2 = abs(tp2 - entry) / risk
    rr3 = abs(tp3 - entry) / risk

    # === Gate: min RR at TP1 ===
    if rr1 < min_rr_tp1:
        return None

    # Sanity: TPs must be on right side of entry
    if direction == "LONG":
        if tp1 <= entry or tp2 <= entry:
            return None
    else:
        if tp1 >= entry or tp2 >= entry:
            return None

    # Scores
    tier1_score = sweep.sweep_score
    tier3_fvg = fvg.quality_score
    struct_align = structural_confirm_score if structural_confirm_score > 0 else 0.5
    mtf = mtf_context_score

    candidate = Sub4BCandidate(
        symbol=symbol, trigger_idx=current_idx, direction=direction,
        sweep_event=sweep, choch_event=choch, fvg=fvg,
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
        symbol=symbol, sub_strategy="4B", direction=direction,
        trigger_idx=current_idx,
        entry_price=entry, sl_price=sl,
        tp_prices=[tp1, tp2, tp3],
        tier1_score=tier1_score, tier1_type="SWEEP",
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


__all__ = ["Sub4BCandidate", "detect_sub4b_setup"]
