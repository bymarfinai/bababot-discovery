"""test_sesi4.py — Unit tests for tier3/ modules.

Coverage: 14 tests across 4 modules.
- FVG detector: 5 tests
- Retracement zone: 4 tests
- Structural confirmation: 1 test
- Setup score: 4 tests

Run:
    python -m mode4_amt.tests.test_sesi4
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import numpy as np

from mode4_amt.tier3.fvg_detector import (
    detect_fvgs, update_fvg_states, get_active_fvgs,
    FVGDirection, FVGState, FVG,
)
from mode4_amt.tier3.retracement_zone import (
    compute_retracement_zone, fvg_in_zone, best_fvg_for_leg,
)
from mode4_amt.tier3.structural_confirm import (
    check_structural_confirmation, StructuralConfirmation,
)
from mode4_amt.tier3.setup_score import (
    SetupCandidate, compute_setup_score, DEFAULT_WEIGHTS,
)
from mode4_amt.structure.impulse_leg import ImpulseLeg, ImpulseDirection


# ============================================================
# FVG DETECTOR
# ============================================================
def test_fvg_bullish_positive():
    highs = np.array([100.0]*20 + [100.0, 103.0, 105.0])
    lows = np.array([99.0]*20 + [99.5, 101.0, 102.0])
    opens = np.array([99.5]*20 + [99.7, 101.2, 102.5])
    closes = np.array([99.7]*20 + [99.9, 102.8, 103.0])
    fvgs = detect_fvgs(highs, lows, opens, closes,
                       min_gap_atr_ratio=0.1, min_middle_body_ratio=0.3)
    bulls = [f for f in fvgs if f.direction == FVGDirection.BULLISH]
    assert len(bulls) >= 1
    target = [f for f in bulls if abs(f.gap_low - 100.0) < 0.01
              and abs(f.gap_high - 102.0) < 0.01]
    assert len(target) >= 1


def test_fvg_bearish_positive():
    highs = np.array([100.0]*20 + [100.0, 99.0, 97.0])
    lows = np.array([99.0]*20 + [99.5, 96.5, 96.0])
    opens = np.array([99.7]*20 + [99.7, 98.5, 97.5])
    closes = np.array([99.5]*20 + [99.6, 96.8, 96.5])
    fvgs = detect_fvgs(highs, lows, opens, closes,
                       min_gap_atr_ratio=0.1, min_middle_body_ratio=0.3)
    bears = [f for f in fvgs if f.direction == FVGDirection.BEARISH]
    assert len(bears) >= 1


def test_fvg_no_gap():
    n = 25
    highs = np.array([102.0]*n)
    lows = np.array([98.0]*n)
    opens = np.array([99.0]*n)
    closes = np.array([101.0]*n)
    fvgs = detect_fvgs(highs, lows, opens, closes,
                       min_gap_atr_ratio=0.1, min_middle_body_ratio=0.3)
    assert fvgs == []


def test_fvg_state_untouched():
    highs = np.array([100.0]*20 + [100.0, 103.0, 105.0] + [110.0]*7)
    lows = np.array([99.0]*20 + [99.5, 101.0, 102.0] + [108.0]*7)
    opens = np.array([99.5]*20 + [99.7, 101.2, 102.5] + [109.0]*7)
    closes = np.array([99.7]*20 + [99.9, 102.8, 104.0] + [109.5]*7)
    fvgs = detect_fvgs(highs, lows, opens, closes,
                       min_gap_atr_ratio=0.1, min_middle_body_ratio=0.3)
    update_fvg_states(fvgs, highs, lows)
    target = [f for f in fvgs if f.direction == FVGDirection.BULLISH
              and abs(f.gap_low - 100.0) < 0.01 and abs(f.gap_high - 102.0) < 0.01]
    assert len(target) >= 1
    assert target[0].state == FVGState.UNTOUCHED


def test_fvg_state_filled():
    highs = np.array([100.0]*20 + [100.0, 103.0, 105.0]
                     + [104.0, 103.0, 101.0, 100.0, 98.0, 97.0, 96.0])
    lows = np.array([99.0]*20 + [99.5, 101.0, 102.0]
                    + [103.0, 101.5, 99.5, 98.0, 96.5, 95.0, 94.5])
    opens = np.array([99.5]*20 + [99.7, 101.2, 102.5]
                     + [104.0, 103.0, 100.5, 99.0, 97.0, 96.5, 95.5])
    closes = np.array([99.7]*20 + [99.9, 102.8, 104.0]
                      + [103.5, 101.5, 100.0, 98.5, 96.8, 95.0, 94.5])
    fvgs = detect_fvgs(highs, lows, opens, closes,
                       min_gap_atr_ratio=0.1, min_middle_body_ratio=0.3)
    update_fvg_states(fvgs, highs, lows)
    bulls = [f for f in fvgs if f.direction == FVGDirection.BULLISH]
    assert len(bulls) >= 1
    assert bulls[-1].state == FVGState.FILLED


# ============================================================
# RETRACEMENT ZONE
# ============================================================
def test_zone_38_bullish():
    leg = ImpulseLeg(
        direction=ImpulseDirection.BULLISH,
        start_idx=0, end_idx=20, start_price=100.0, end_price=130.0,
        num_candles=20, directional_candles_pct=0.9,
        total_move=30.0, atr_at_start=5.0, move_atr_ratio=6.0,
        max_retracement_pct=0.2,
    )
    z = compute_retracement_zone(leg, "38.2%")
    assert abs(z.zone_low - 115.0) < 0.01
    assert abs(z.zone_high - 118.54) < 0.02


def test_zone_ote_bullish():
    leg = ImpulseLeg(
        direction=ImpulseDirection.BULLISH,
        start_idx=0, end_idx=20, start_price=100.0, end_price=130.0,
        num_candles=20, directional_candles_pct=0.9,
        total_move=30.0, atr_at_start=5.0, move_atr_ratio=6.0,
        max_retracement_pct=0.2,
    )
    z = compute_retracement_zone(leg, "OTE")
    assert abs(z.zone_low - 106.3) < 0.02
    assert abs(z.zone_high - 111.46) < 0.02


def test_fvg_in_zone_positive():
    leg = ImpulseLeg(
        direction=ImpulseDirection.BULLISH,
        start_idx=0, end_idx=20, start_price=100.0, end_price=130.0,
        num_candles=20, directional_candles_pct=0.9,
        total_move=30.0, atr_at_start=5.0, move_atr_ratio=6.0,
        max_retracement_pct=0.2,
    )
    zone = compute_retracement_zone(leg, "OTE")
    fvg = FVG(
        idx=15, direction=FVGDirection.BULLISH,
        gap_low=108.0, gap_high=112.0,
        gap_size=4.0, gap_size_atr_ratio=0.8, middle_body_ratio=0.7,
        quality_score=0.7,
    )
    assert fvg_in_zone(fvg, zone, min_overlap_pct=0.3)


def test_fvg_not_in_zone():
    leg = ImpulseLeg(
        direction=ImpulseDirection.BULLISH,
        start_idx=0, end_idx=20, start_price=100.0, end_price=130.0,
        num_candles=20, directional_candles_pct=0.9,
        total_move=30.0, atr_at_start=5.0, move_atr_ratio=6.0,
        max_retracement_pct=0.2,
    )
    zone = compute_retracement_zone(leg, "OTE")
    fvg = FVG(
        idx=15, direction=FVGDirection.BULLISH,
        gap_low=125.0, gap_high=128.0,
        gap_size=3.0, gap_size_atr_ratio=0.6, middle_body_ratio=0.7,
        quality_score=0.7,
    )
    assert not fvg_in_zone(fvg, zone)


# ============================================================
# STRUCTURAL CONFIRMATION
# ============================================================
def test_structural_confirm_no_data():
    highs = np.array([100.0]*25)
    lows = np.array([99.0]*25)
    closes = np.array([99.5]*25)
    result = check_structural_confirmation(highs, lows, closes, trigger_idx=23,
                                           direction="UP", window=8)
    assert not result.is_confirmed


# ============================================================
# SETUP SCORE
# ============================================================
def test_setup_score_sub4a_valid():
    c = SetupCandidate(
        symbol="BTC", sub_strategy="4A", direction="LONG",
        trigger_idx=100, entry_price=100.0, sl_price=98.0,
        tier1_score=0.75, tier1_type="BREAKOUT",
        tier3_fvg_quality=0.70,
        liquidity_target_weight=0.85,
        structural_alignment=0.60,
        mtf_context=0.50,
    )
    result = compute_setup_score(c)
    assert abs(result.setup_score - 0.71) < 0.01
    assert result.passes_hard_gate
    assert result.is_valid


def test_setup_score_sub4a_wrong_tier1():
    c = SetupCandidate(
        symbol="BTC", sub_strategy="4A", direction="LONG",
        trigger_idx=100, entry_price=100.0, sl_price=98.0,
        tier1_score=0.80, tier1_type="SWEEP",
        tier3_fvg_quality=0.80,
        liquidity_target_weight=0.90,
        structural_alignment=0.70,
        mtf_context=0.60,
    )
    result = compute_setup_score(c)
    assert not result.passes_hard_gate
    assert not result.is_valid


def test_setup_score_low_composite():
    c = SetupCandidate(
        symbol="BTC", sub_strategy="4A", direction="LONG",
        trigger_idx=100, entry_price=100.0, sl_price=98.0,
        tier1_score=0.50, tier1_type="BREAKOUT",
        tier3_fvg_quality=0.30,
        liquidity_target_weight=0.40,
        structural_alignment=0.30,
        mtf_context=0.20,
    )
    result = compute_setup_score(c)
    assert result.setup_score < 0.65
    assert not result.is_valid


def test_setup_score_sub4b_needs_sweep():
    c = SetupCandidate(
        symbol="BTC", sub_strategy="4B", direction="LONG",
        trigger_idx=100, entry_price=100.0, sl_price=98.0,
        tier1_score=0.80, tier1_type="BREAKOUT",
        tier3_fvg_quality=0.80,
        liquidity_target_weight=0.90,
        structural_alignment=0.70,
        mtf_context=0.60,
    )
    result = compute_setup_score(c)
    assert not result.passes_hard_gate


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    tests = [
        test_fvg_bullish_positive, test_fvg_bearish_positive,
        test_fvg_no_gap, test_fvg_state_untouched, test_fvg_state_filled,
        test_zone_38_bullish, test_zone_ote_bullish,
        test_fvg_in_zone_positive, test_fvg_not_in_zone,
        test_structural_confirm_no_data,
        test_setup_score_sub4a_valid, test_setup_score_sub4a_wrong_tier1,
        test_setup_score_low_composite, test_setup_score_sub4b_needs_sweep,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed.append(t.__name__)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
