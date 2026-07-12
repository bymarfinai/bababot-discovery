"""
test_sesi3.py — Unit tests untuk Sesi 3 modules (tier1/).

Coverage: 12 tests across 3 modules.
- Sweep detector: 4 tests (BSL+, SSL+, close-beyond negative, small-wick negative)
- Breakout classifier: 3 tests (positive, no follow-through negative, insufficient future)
- Volume signature: 4 tests (spike, no-spike, quick-check, sustained)
- Integration: 1 test (detect_sweeps with LiquidityMap)

Run:
    python -m mode4_amt.tests.test_sesi3
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import numpy as np

from mode4_amt.liquidity.liquidity_map import LiquidityLevel, LevelCategory, LevelSide, LevelState, LiquidityMap
from mode4_amt.tier1.sweep_detector import detect_sweep_at_candle, detect_sweeps, SweepDirection
from mode4_amt.tier1.breakout_classifier import classify_level_interaction, detect_breakouts, BreakoutDirection
from mode4_amt.tier1.volume_signature import compute_volume_signature, is_volume_spike


def make_level(price, side=LevelSide.BSL, weight=0.9):
    return LiquidityLevel(
        price=price, category=LevelCategory.SWING_4H, side=side,
        weight_score=weight, source_idx=0, reference="test", timeframe="test",
        distance_from_current=0.0, distance_atr=0.0,
    )


# ============================================================
# SWEEP DETECTOR
# ============================================================
def test_sweep_bsl_positive():
    highs = np.array([100.0]*20 + [106.5])
    lows = np.array([99.0]*20 + [102.5])
    opens = np.array([99.5]*20 + [104.0])
    closes = np.array([100.0]*20 + [103.0])
    volumes = np.array([100.0]*20 + [300.0])
    level = make_level(105.0, LevelSide.BSL)
    ev = detect_sweep_at_candle(20, highs, lows, opens, closes, volumes,
                                level, atr=1.0, vol_avg=100.0,
                                min_wick_pen_atr=0.1, min_wick_body_ratio=1.0,
                                min_score=0.4)
    assert ev is not None
    assert ev.direction == SweepDirection.UP


def test_sweep_ssl_positive():
    highs = np.array([100.0]*20 + [102.5])
    lows = np.array([99.0]*20 + [93.5])
    opens = np.array([99.5]*20 + [96.0])
    closes = np.array([100.0]*20 + [97.0])
    volumes = np.array([100.0]*20 + [250.0])
    level = make_level(95.0, LevelSide.SSL)
    ev = detect_sweep_at_candle(20, highs, lows, opens, closes, volumes,
                                level, atr=1.0, vol_avg=100.0,
                                min_wick_pen_atr=0.1, min_wick_body_ratio=1.0,
                                min_score=0.4)
    assert ev is not None
    assert ev.direction == SweepDirection.DOWN


def test_sweep_negative_close_beyond():
    """Close ALSO beyond level — this is breakout candidate not sweep."""
    highs = np.array([100.0]*20 + [106.5])
    lows = np.array([99.0]*20 + [104.5])
    opens = np.array([99.5]*20 + [104.7])
    closes = np.array([100.0]*20 + [106.0])
    volumes = np.array([100.0]*20 + [200.0])
    level = make_level(105.0, LevelSide.BSL)
    ev = detect_sweep_at_candle(20, highs, lows, opens, closes, volumes,
                                level, atr=1.0, vol_avg=100.0)
    assert ev is None


def test_sweep_negative_small_wick():
    highs = np.array([100.0]*20 + [105.05])
    lows = np.array([99.0]*20 + [102.5])
    opens = np.array([99.5]*20 + [104.0])
    closes = np.array([100.0]*20 + [103.0])
    volumes = np.array([100.0]*20 + [200.0])
    level = make_level(105.0, LevelSide.BSL)
    ev = detect_sweep_at_candle(20, highs, lows, opens, closes, volumes,
                                level, atr=1.0, vol_avg=100.0,
                                min_wick_pen_atr=0.15)
    assert ev is None


# ============================================================
# BREAKOUT CLASSIFIER
# ============================================================
def test_breakout_up_positive():
    highs = np.array([100.5]*15 + [101.0, 101.5, 102.0, 102.5] + [102.5]*11)
    lows = np.array([99.0]*15 + [99.8, 100.5, 100.8, 101.0] + [101.0]*11)
    opens = np.array([99.5]*15 + [99.8, 100.5, 100.7, 101.0] + [102.0]*11)
    closes = np.array([99.5]*15 + [100.5, 100.7, 101.0, 101.3] + [102.0]*11)
    volumes = np.array([100.0]*15 + [200.0, 220.0, 230.0, 210.0] + [100.0]*11)
    level = make_level(100.0, LevelSide.BSL)
    ev = classify_level_interaction(
        15, highs, lows, opens, closes, volumes, level, atr=1.0,
        follow_through_candles=3, min_close_through_atr=0.2,
        min_follow_through_ratio=0.8, min_vol_sustain=1.2, min_score=0.4,
    )
    assert ev is not None
    assert ev.direction == BreakoutDirection.UP


def test_breakout_negative_no_follow():
    highs = np.array([100.5]*15 + [101.0, 100.2, 99.8, 99.5] + [99.5]*11)
    lows = np.array([99.0]*15 + [99.8, 99.2, 99.0, 98.5] + [98.5]*11)
    opens = np.array([99.5]*15 + [99.8, 100.5, 100.0, 99.5] + [99.0]*11)
    closes = np.array([99.5]*15 + [100.5, 99.5, 99.2, 98.8] + [99.0]*11)
    volumes = np.array([100.0]*15 + [200.0, 100.0, 100.0, 100.0] + [100.0]*11)
    level = make_level(100.0, LevelSide.BSL)
    ev = classify_level_interaction(
        15, highs, lows, opens, closes, volumes, level, atr=1.0,
        follow_through_candles=3, min_score=0.4,
    )
    assert ev is None


def test_breakout_needs_future_data():
    n = 20
    highs = np.zeros(n) + 100.5
    lows = np.zeros(n) + 99.5
    opens = np.zeros(n) + 100.0
    closes = np.zeros(n) + 100.5
    volumes = np.zeros(n) + 100.0
    level = make_level(100.0, LevelSide.BSL)
    ev = classify_level_interaction(
        18, highs, lows, opens, closes, volumes, level, atr=1.0,
        follow_through_candles=3,
    )
    assert ev is None


# ============================================================
# VOLUME SIGNATURE
# ============================================================
def test_volume_spike_positive():
    volumes = np.array([100.0]*20 + [300.0])
    vp = compute_volume_signature(volumes, idx=20, avg_period_long=20)
    assert vp is not None
    assert vp.is_spike
    assert vp.spike_ratio >= 2.5


def test_volume_no_spike():
    volumes = np.array([100.0]*20 + [110.0])
    vp = compute_volume_signature(volumes, idx=20, avg_period_long=20)
    assert vp is not None
    assert not vp.is_spike


def test_is_volume_spike_quick():
    volumes = np.array([100.0]*20 + [250.0])
    assert is_volume_spike(volumes, 20, avg_period=20, k=1.8)
    volumes2 = np.array([100.0]*20 + [150.0])
    assert not is_volume_spike(volumes2, 20, avg_period=20, k=1.8)


def test_volume_sustained():
    volumes = np.array([100.0]*18 + [200.0, 200.0, 200.0])
    vp = compute_volume_signature(volumes, idx=20, avg_period_long=20,
                                  sustain_window=3, k_sustain=1.5)
    assert vp is not None
    assert vp.is_sustained


# ============================================================
# INTEGRATION
# ============================================================
def test_detect_sweeps_with_map():
    n = 30
    highs = np.array([100.0]*25 + [106.5, 100.0, 100.0, 100.0, 100.0])
    lows = np.array([99.0]*25 + [102.5, 99.0, 99.0, 99.0, 99.0])
    opens = np.array([99.5]*25 + [104.0, 99.5, 99.5, 99.5, 99.5])
    closes = np.array([100.0]*25 + [103.0, 100.0, 100.0, 100.0, 100.0])
    volumes = np.array([100.0]*25 + [300.0, 100.0, 100.0, 100.0, 100.0])
    lmap = LiquidityMap(
        levels=[make_level(105.0, LevelSide.BSL)],
        current_price=100.0, current_atr=1.0,
    )
    sweeps = detect_sweeps(highs, lows, opens, closes, volumes, lmap,
                           min_wick_pen_atr=0.1, min_wick_body_ratio=1.0,
                           min_score=0.4)
    assert len(sweeps) >= 1
    assert sweeps[0].idx == 25


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    tests = [
        test_sweep_bsl_positive, test_sweep_ssl_positive,
        test_sweep_negative_close_beyond, test_sweep_negative_small_wick,
        test_breakout_up_positive, test_breakout_negative_no_follow,
        test_breakout_needs_future_data,
        test_volume_spike_positive, test_volume_no_spike,
        test_is_volume_spike_quick, test_volume_sustained,
        test_detect_sweeps_with_map,
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
