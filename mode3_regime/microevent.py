"""
microevent.py — Layer 3: 6 Micro Event Detector
==================================================
Per-candle events at VAH/VAL levels:
- TRUE_BOUNCE, TRUE_BREAKDOWN, TRUE_BREAKOUT
- FAKE_BREAKDOWN, FAKE_BREAKOUT
- UNDECIDED (hover)

Plus bias filter with responsive exit + reversal signal detection.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .indicators import ema, consecutive_count, slope_pct, rolling_volume_distribution
from .regime import Regime, RegimeState


class MicroEvent(Enum):
    NONE = "none"
    TRUE_BOUNCE = "true_bounce"
    TRUE_BREAKDOWN = "true_breakdown"
    TRUE_BREAKOUT = "true_breakout"
    FAKE_BREAKDOWN = "fake_breakdown"
    FAKE_BREAKOUT = "fake_breakout"
    UNDECIDED = "undecided"


class Bias(Enum):
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class MicroEventConfig:
    touch_tolerance: float = 0.003
    volume_multiplier: float = 1.3
    reclaim_buffer: float = 0.001

    # Break confirmation (for true break)
    break_confirmation_candles: int = 3
    break_volume_multiplier: float = 1.5
    break_distance_pct: float = 0.003

    # Fake break
    fake_max_candles: int = 2
    fake_recovery_pct: float = 0.002


@dataclass
class BiasConfig:
    # 5-signal bias filter
    ema_fast_len: int = 20
    ema_slow_len: int = 50
    ema_distance_threshold: float = 0.003
    close_ema_streak: int = 5
    val_slope_lookback: int = 20
    val_slope_threshold: float = 0.005
    volume_dist_ratio: float = 1.15
    min_score: int = 3

    # Responsive exit
    strong_reversal_volume: float = 1.5
    ll_lookback: int = 10


def detect_micro_events(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: MicroEventConfig,
) -> list[MicroEvent]:
    """Detect micro event per bar."""
    n = len(closes)
    events: list[MicroEvent] = [MicroEvent.NONE] * n

    vol_avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - 19)
        vol_avg[i] = float(np.mean(volumes[start:i + 1])) if i > start else 1.0

    for i in range(1, n):
        rs = regime_states[i]
        if rs.vah == 0 or rs.val == 0:
            continue

        vah = rs.vah
        val = rs.val
        c = closes[i]
        h = highs[i]
        l = lows[i]
        v = volumes[i]

        vol_ok_range = v > vol_avg[i] * cfg.volume_multiplier
        vol_ok_break = v > vol_avg[i] * cfg.break_volume_multiplier

        # Check consecutive close beyond level
        consec_above = 0
        consec_below = 0
        vol_high_above = 0
        vol_high_below = 0
        for k in range(cfg.break_confirmation_candles):
            idx = i - k
            if idx < 0:
                break
            if closes[idx] > vah:
                consec_above += 1
                if volumes[idx] > vol_avg[idx] * cfg.break_volume_multiplier:
                    vol_high_above += 1
            else:
                break
        for k in range(cfg.break_confirmation_candles):
            idx = i - k
            if idx < 0:
                break
            if closes[idx] < val:
                consec_below += 1
                if volumes[idx] > vol_avg[idx] * cfg.break_volume_multiplier:
                    vol_high_below += 1
            else:
                break

        # True break check
        distance_above = (c - vah) / vah if c > vah else 0
        distance_below = (val - c) / val if c < val else 0

        is_true_breakout = (
            consec_above >= cfg.break_confirmation_candles
            and vol_high_above >= (cfg.break_confirmation_candles // 2 + 1)
            and distance_above >= cfg.break_distance_pct
        )
        is_true_breakdown = (
            consec_below >= cfg.break_confirmation_candles
            and vol_high_below >= (cfg.break_confirmation_candles // 2 + 1)
            and distance_below >= cfg.break_distance_pct
        )

        # Fake break check: wick beyond, close back inside
        wick_above = h > vah * (1 + cfg.touch_tolerance)
        wick_below = l < val * (1 - cfg.touch_tolerance)
        closed_below_vah = c < vah
        closed_above_val = c > val

        is_fake_breakout = wick_above and closed_below_vah and vol_ok_range
        is_fake_breakdown = wick_below and closed_above_val and vol_ok_range

        # True bounce check: touch level, then close reclaim + upward candle
        touch_val = lows[i] <= val * (1 + cfg.touch_tolerance) and lows[i] >= val * (1 - cfg.touch_tolerance)
        touch_vah = highs[i] >= vah * (1 - cfg.touch_tolerance) and highs[i] <= vah * (1 + cfg.touch_tolerance)

        bullish_candle = c > closes[i - 1] and c > (highs[i] + lows[i]) / 2
        bearish_candle = c < closes[i - 1] and c < (highs[i] + lows[i]) / 2

        is_true_bounce_val = touch_val and bullish_candle and c > val and vol_ok_range
        is_true_bounce_vah = touch_vah and bearish_candle and c < vah and vol_ok_range

        # Assign event (priority: true break > fake break > true bounce)
        if is_true_breakout:
            events[i] = MicroEvent.TRUE_BREAKOUT
        elif is_true_breakdown:
            events[i] = MicroEvent.TRUE_BREAKDOWN
        elif is_fake_breakout:
            events[i] = MicroEvent.FAKE_BREAKOUT
        elif is_fake_breakdown:
            events[i] = MicroEvent.FAKE_BREAKDOWN
        elif is_true_bounce_val or is_true_bounce_vah:
            events[i] = MicroEvent.TRUE_BOUNCE
        elif touch_val or touch_vah:
            events[i] = MicroEvent.UNDECIDED

    return events


def compute_bias_series(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: BiasConfig,
) -> list[Bias]:
    """
    Compute bias per bar with 5-signal scoring + responsive exit.
    """
    n = len(closes)
    biases: list[Bias] = [Bias.NEUTRAL] * n

    ema_fast = ema(closes, cfg.ema_fast_len)
    ema_slow = ema(closes, cfg.ema_slow_len)

    close_below_ema = closes < ema_fast
    close_above_ema = closes > ema_fast
    streak_below = consecutive_count(close_below_ema)
    streak_above = consecutive_count(close_above_ema)

    val_slope = slope_pct(np.array([rs.val for rs in regime_states]), cfg.val_slope_lookback)
    vah_slope = slope_pct(np.array([rs.vah for rs in regime_states]), cfg.val_slope_lookback)

    up_vol, down_vol = rolling_volume_distribution(closes, volumes, 20)

    vol_avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - 19)
        vol_avg[i] = float(np.mean(volumes[start:i + 1])) if i > start else 1.0

    prev_bias = Bias.NEUTRAL

    for i in range(n):
        if i < 50:
            biases[i] = Bias.NEUTRAL
            continue

        # Signal 1: EMA cross + distance
        ema_diff_pct = abs(ema_fast[i] - ema_slow[i]) / ema_slow[i] if ema_slow[i] > 0 else 0
        sig1_bear = ema_fast[i] < ema_slow[i] and ema_diff_pct >= cfg.ema_distance_threshold
        sig1_bull = ema_fast[i] > ema_slow[i] and ema_diff_pct >= cfg.ema_distance_threshold

        # Signal 2: Close vs EMA streak
        sig2_bear = streak_below[i] >= cfg.close_ema_streak
        sig2_bull = streak_above[i] >= cfg.close_ema_streak

        # Signal 3: LL+LH or HH+HL
        if i >= cfg.ll_lookback:
            low_past = lows[i - cfg.ll_lookback]
            high_past = highs[i - cfg.ll_lookback]
            recent_low = float(np.min(lows[max(0, i - 4):i + 1]))
            recent_high = float(np.max(highs[max(0, i - 4):i + 1]))
            sig3_bear = recent_low < low_past and recent_high < high_past
            sig3_bull = recent_low > low_past and recent_high > high_past
        else:
            sig3_bear = False
            sig3_bull = False

        # Signal 4: VAL/VAH slope
        sig4_bear = val_slope[i] <= -cfg.val_slope_threshold
        sig4_bull = vah_slope[i] >= cfg.val_slope_threshold

        # Signal 5: Volume distribution
        sig5_bear = down_vol[i] > up_vol[i] * cfg.volume_dist_ratio
        sig5_bull = up_vol[i] > down_vol[i] * cfg.volume_dist_ratio

        bear_score = sum([sig1_bear, sig2_bear, sig3_bear, sig4_bear, sig5_bear])
        bull_score = sum([sig1_bull, sig2_bull, sig3_bull, sig4_bull, sig5_bull])

        current_bias = Bias.NEUTRAL
        if bear_score >= cfg.min_score and bear_score > bull_score:
            current_bias = Bias.BEARISH
        elif bull_score >= cfg.min_score and bull_score > bear_score:
            current_bias = Bias.BULLISH

        # Responsive exit: strong reversal candle overrides
        if i > 0:
            strong_bull_candle = (
                closes[i] > ema_fast[i]
                and closes[i - 1] < ema_fast[i - 1]  # was below, now above (reclaim)
                and closes[i] > closes[i - 1] * 1.008  # 0.8% up
                and volumes[i] > vol_avg[i] * cfg.strong_reversal_volume
            )
            strong_bear_candle = (
                closes[i] < ema_fast[i]
                and closes[i - 1] > ema_fast[i - 1]
                and closes[i] < closes[i - 1] * 0.992
                and volumes[i] > vol_avg[i] * cfg.strong_reversal_volume
            )

            # Override: strong reversal candle in prior bias direction resets to neutral
            if prev_bias == Bias.BEARISH and strong_bull_candle:
                current_bias = Bias.NEUTRAL
            elif prev_bias == Bias.BULLISH and strong_bear_candle:
                current_bias = Bias.NEUTRAL

        biases[i] = current_bias
        prev_bias = current_bias

    return biases


__all__ = [
    "MicroEvent", "Bias",
    "MicroEventConfig", "BiasConfig",
    "detect_micro_events", "compute_bias_series",
]
