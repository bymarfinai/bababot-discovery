"""
test_sesi2.py — Unit tests untuk Sesi 2 modules (structure/ + liquidity/).

Coverage: 19 tests across 7 modules.
- Swing detector: 4 tests
- Structure labels: 3 tests
- BOS/CHoCH: 2 tests
- Impulse leg: 2 tests
- Session levels: 1 test
- Equal levels: 3 tests
- Liquidity map: 4 tests

Run:
    python -m mode4_amt.tests.test_sesi2
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np

from mode4_amt.structure.swing_detector import (
    detect_swings, last_swing_before, Swing, SwingType,
)
from mode4_amt.structure.structure_labels import (
    label_swings, StructureLabel, count_recent_labels, get_trend_bias,
)
from mode4_amt.structure.bos_choch import (
    detect_structure_events, EventType, get_most_recent_event,
)
from mode4_amt.structure.impulse_leg import (
    detect_impulse_legs, ImpulseDirection,
)
from mode4_amt.liquidity.session_levels import (
    detect_session_levels, SessionType, SESSION_RANGES,
)
from mode4_amt.liquidity.equal_levels import (
    detect_equal_highs, detect_equal_lows,
)
from mode4_amt.liquidity.liquidity_map import (
    build_liquidity_map, LevelCategory, LevelSide, DEFAULT_WEIGHTS,
)


def make_zigzag_ohlc(pattern):
    """Build OHLCV from a list of (n_candles, direction) pairs."""
    highs, lows, closes = [], [], []
    price = 100.0
    for n, direction in pattern:
        for i in range(n):
            step = 1.0 if direction == 'up' else -1.0
            price += step
            highs.append(price + 0.5)
            lows.append(price - 0.5)
            closes.append(price)
    return np.array(highs), np.array(lows), np.array(closes)


# ============================================================
# SWING DETECTOR
# ============================================================
def test_swing_detect_zigzag():
    highs, lows, closes = make_zigzag_ohlc([(10, 'up'), (10, 'down'), (10, 'up')])
    swings = detect_swings(highs, lows, lookback_n=3)
    assert len(swings) >= 2
    types = [s.swing_type for s in swings]
    assert SwingType.HIGH in types
    assert SwingType.LOW in types


def test_swing_short_data_empty():
    highs = np.array([100, 101, 102, 103, 102])
    lows = np.array([99, 100, 101, 102, 101])
    swings = detect_swings(highs, lows, lookback_n=3)
    assert swings == []


def test_swing_lookback_n():
    highs, lows, closes = make_zigzag_ohlc(
        [(15, 'up'), (15, 'down'), (15, 'up'), (15, 'down')])
    s3 = detect_swings(highs, lows, lookback_n=3)
    s7 = detect_swings(highs, lows, lookback_n=7)
    assert len(s3) >= len(s7)


def test_last_swing_before():
    highs, lows, _ = make_zigzag_ohlc(
        [(10, 'up'), (10, 'down'), (10, 'up'), (10, 'down')])
    swings = detect_swings(highs, lows, lookback_n=3)
    assert len(swings) >= 3
    last_high = last_swing_before(swings, idx=25, swing_type=SwingType.HIGH)
    assert last_high is not None
    assert last_high.idx < 25
    assert last_high.swing_type == SwingType.HIGH


# ============================================================
# STRUCTURE LABELS
# ============================================================
def test_labels_uptrend_pattern():
    highs, lows, closes = make_zigzag_ohlc([
        (10, 'up'), (5, 'down'),
        (12, 'up'), (5, 'down'),
        (14, 'up'), (5, 'down'),
    ])
    swings = detect_swings(highs, lows, lookback_n=3)
    labeled = label_swings(swings)
    labels = [ls.label for ls in labeled]
    assert StructureLabel.HH in labels
    assert labels[0] == StructureLabel.UNDEFINED


def test_labels_downtrend_pattern():
    highs, lows, closes = make_zigzag_ohlc([
        (10, 'down'), (5, 'up'),
        (12, 'down'), (5, 'up'),
        (14, 'down'), (5, 'up'),
    ])
    swings = detect_swings(highs, lows, lookback_n=3)
    labeled = label_swings(swings)
    labels = [ls.label for ls in labeled]
    assert StructureLabel.LL in labels
    bias = get_trend_bias(labeled, lookback=6)
    assert bias == "DOWNTREND"


def test_trend_bias_uptrend():
    highs, lows, closes = make_zigzag_ohlc([
        (10, 'up'), (5, 'down'),
        (12, 'up'), (5, 'down'),
        (14, 'up'), (5, 'down'),
        (16, 'up'), (5, 'down'),
    ])
    swings = detect_swings(highs, lows, lookback_n=3)
    labeled = label_swings(swings)
    bias = get_trend_bias(labeled, lookback=6)
    assert bias == "UPTREND"


# ============================================================
# BOS / CHoCH
# ============================================================
def test_bos_up_detected():
    highs, lows, closes = make_zigzag_ohlc([
        (8, 'up'), (5, 'down'),
        (10, 'up'), (5, 'down'),
        (12, 'up'), (5, 'down'),
        (10, 'up'),
    ])
    swings = detect_swings(highs, lows, lookback_n=3)
    labeled = label_swings(swings)
    events = detect_structure_events(closes, swings, labeled)
    bos_up = [e for e in events if e.event_type == EventType.BOS_UP]
    assert len(bos_up) >= 1


def test_no_bos_in_flat_data():
    highs = np.array([100.0] * 30)
    lows = np.array([100.0] * 30)
    closes = np.array([100.0] * 30)
    swings = detect_swings(highs, lows, lookback_n=3)
    labeled = label_swings(swings)
    events = detect_structure_events(closes, swings, labeled)
    assert len(events) == 0


# ============================================================
# IMPULSE LEG
# ============================================================
def test_impulse_leg_bullish():
    down_h = [105 - i for i in range(5)]
    down_l = [104 - i for i in range(5)]
    down_c = [104.5 - i for i in range(5)]
    up_h = [100 + i * 1.0 + 0.5 for i in range(25)]
    up_l = [100 + i * 1.0 - 0.5 for i in range(25)]
    up_c = [100 + i * 1.0 for i in range(25)]
    tail_h = [123.5 - i * 0.3 for i in range(8)]
    tail_l = [122.5 - i * 0.3 for i in range(8)]
    tail_c = [123.0 - i * 0.3 for i in range(8)]
    highs = np.array(down_h + up_h + tail_h)
    lows = np.array(down_l + up_l + tail_l)
    closes = np.array(down_c + up_c + tail_c)
    swings = detect_swings(highs, lows, lookback_n=3)
    assert len(swings) >= 2
    legs = detect_impulse_legs(highs, lows, closes, swings,
                              min_candles=5, min_directional_pct=0.75,
                              min_atr_ratio=1.0, max_retracement_pct=0.5,
                              atr_period=14)
    bullish = [l for l in legs if l.direction == ImpulseDirection.BULLISH]
    assert len(bullish) >= 1


def test_impulse_retracement_fib():
    from mode4_amt.structure.impulse_leg import ImpulseLeg
    leg = ImpulseLeg(
        direction=ImpulseDirection.BULLISH,
        start_idx=0, end_idx=20,
        start_price=100.0, end_price=130.0,
        num_candles=20, directional_candles_pct=0.9,
        total_move=30.0, atr_at_start=5.0, move_atr_ratio=6.0,
        max_retracement_pct=0.2,
    )
    assert abs(leg.retracement_level(0.382) - 118.54) < 0.01
    assert abs(leg.retracement_level(0.618) - 111.46) < 0.01
    assert abs(leg.extension_level(1.618) - 148.54) < 0.01


# ============================================================
# SESSION LEVELS
# ============================================================
def test_session_asia_london_ny():
    n = 72
    start_ms = 1767225600 * 1000  # 2026-01-01 00:00 UTC
    hour_ms = 3600 * 1000
    timestamps = np.array([start_ms + i * hour_ms for i in range(n)])
    rng = np.random.default_rng(42)
    closes = 100 + rng.uniform(-5, 5, n)
    highs = closes + rng.uniform(0.1, 1.0, n)
    lows = closes - rng.uniform(0.1, 1.0, n)
    sessions = detect_session_levels(highs, lows, timestamps)
    assert len(sessions) >= 6
    types_present = set(s.session for s in sessions)
    assert SessionType.ASIA in types_present
    assert SessionType.LONDON in types_present
    assert SessionType.NY in types_present


# ============================================================
# EQUAL LEVELS
# ============================================================
def test_equal_highs_detection():
    swings = [
        Swing(idx=10, swing_type=SwingType.HIGH, price=100.0),
        Swing(idx=20, swing_type=SwingType.LOW, price=95.0),
        Swing(idx=30, swing_type=SwingType.HIGH, price=100.05),
        Swing(idx=40, swing_type=SwingType.LOW, price=94.0),
        Swing(idx=50, swing_type=SwingType.HIGH, price=105.0),
    ]
    eqh = detect_equal_highs(swings, tolerance_pct=0.001, min_distance=5)
    assert len(eqh) >= 1
    assert eqh[0].num_equals == 2
    assert 100.0 < eqh[0].price_avg < 100.1


def test_no_equal_highs():
    swings = [
        Swing(idx=10, swing_type=SwingType.HIGH, price=100.0),
        Swing(idx=20, swing_type=SwingType.LOW, price=95.0),
        Swing(idx=30, swing_type=SwingType.HIGH, price=110.0),
        Swing(idx=40, swing_type=SwingType.LOW, price=90.0),
        Swing(idx=50, swing_type=SwingType.HIGH, price=120.0),
    ]
    eqh = detect_equal_highs(swings, tolerance_pct=0.001)
    assert len(eqh) == 0


def test_equal_lows():
    swings = [
        Swing(idx=10, swing_type=SwingType.LOW, price=90.0),
        Swing(idx=20, swing_type=SwingType.HIGH, price=100.0),
        Swing(idx=30, swing_type=SwingType.LOW, price=90.08),
        Swing(idx=40, swing_type=SwingType.HIGH, price=105.0),
    ]
    eql = detect_equal_lows(swings, tolerance_pct=0.001, min_distance=5)
    assert len(eql) == 1
    assert eql[0].num_equals == 2


# ============================================================
# LIQUIDITY MAP
# ============================================================
def test_liquidity_map_bsl_ssl_split():
    current_price = 100.0
    swings_1h = [
        Swing(idx=10, swing_type=SwingType.HIGH, price=105.0),
        Swing(idx=20, swing_type=SwingType.LOW, price=95.0),
        Swing(idx=30, swing_type=SwingType.HIGH, price=108.0),
        Swing(idx=40, swing_type=SwingType.LOW, price=93.0),
    ]
    lmap = build_liquidity_map(
        current_price=current_price, current_atr=2.0,
        swings_1h=swings_1h,
        vah=110.0, val=90.0,
        prev_day_high=115.0, prev_day_low=85.0,
        round_number_step=10.0,
    )
    for l in lmap.bsl_levels():
        assert l.price > current_price
    for l in lmap.ssl_levels():
        assert l.price < current_price


def test_liquidity_map_weight_sorting():
    lmap = build_liquidity_map(
        current_price=100.0, current_atr=2.0,
        vah=110.0, val=90.0,
        prev_day_high=112.0, prev_day_low=88.0,
        round_number_step=10.0,
    )
    weights = [l.weight_score for l in lmap.levels]
    assert weights == sorted(weights, reverse=True)


def test_liquidity_map_nearest():
    lmap = build_liquidity_map(
        current_price=100.0, current_atr=2.0,
        vah=105.0, val=95.0,
        prev_day_high=110.0, prev_day_low=90.0,
    )
    assert lmap.nearest_bsl().price == 105.0
    assert lmap.nearest_ssl().price == 95.0


def test_liquidity_map_dedup():
    lmap = build_liquidity_map(
        current_price=100.0, current_atr=2.0,
        vah=110.0, prev_day_high=110.01,
    )
    close_to_110 = [l for l in lmap.bsl_levels() if abs(l.price - 110.0) < 0.1]
    assert len(close_to_110) == 1
    assert close_to_110[0].category == LevelCategory.VAH_VAL


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    tests = [
        test_swing_detect_zigzag, test_swing_short_data_empty,
        test_swing_lookback_n, test_last_swing_before,
        test_labels_uptrend_pattern, test_labels_downtrend_pattern,
        test_trend_bias_uptrend,
        test_bos_up_detected, test_no_bos_in_flat_data,
        test_impulse_leg_bullish, test_impulse_retracement_fib,
        test_session_asia_london_ny,
        test_equal_highs_detection, test_no_equal_highs, test_equal_lows,
        test_liquidity_map_bsl_ssl_split, test_liquidity_map_weight_sorting,
        test_liquidity_map_nearest, test_liquidity_map_dedup,
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
