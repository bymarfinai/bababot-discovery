"""
strategy_sideways.py — Sideways Tektok Strategy v0.3
======================================================
v0.3 changes (Round 2: Confidence Scoring):
- Add 5-signal confidence scoring for each qualifying signal
- Signal 1: swing structure (higher low before VAL touch / lower high before VAH touch)
- Signal 2: wick rejection pattern (long wick in opposite direction)
- Signal 3: volume divergence (decreasing volume at successive tests)
- Signal 4: EMA20 alignment (price above/below EMA20 supports direction)
- Signal 5: multi-touch penalty (level tested 4+ times in 20 candles → reduce confidence)

Confidence is used for POSITION SIZING (not filtering):
- Score >= 4 → full size (1.0)
- Score 2-3 → half size (0.5)
- Score 0-1 → quarter size (0.25)
- Score < 0 → skip (0.0) — rare, only when multiple red flags
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .regime import Regime, RegimeState
from .microevent import MicroEvent
from .indicators import ema


class SideEnum(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"


class SidewaysMode(Enum):
    BOUNCE_VAL = "bounce_val"
    REJECT_VAH = "reject_vah"
    FAKE_BREAKDOWN = "fake_breakdown"
    FAKE_BREAKOUT = "fake_breakout"


def _default_allowed_regimes():
    return (Regime.ACCUMULATION, Regime.DISTRIBUTION, Regime.UNKNOWN)


@dataclass
class SidewaysConfig:
    # Range detection
    range_max_width_pct: float = 0.03
    touch_tolerance: float = 0.003
    volume_multiplier: float = 1.3
    cooldown_bars: int = 10

    allowed_regimes: tuple = field(default_factory=_default_allowed_regimes)

    # v0.2 flags
    skip_regime_filter: bool = False
    skip_range_width_filter: bool = False

    # v0.3: Confidence scoring params
    enable_confidence_scoring: bool = True   # Round 2 toggle
    structure_lookback: int = 10              # bars to check swing structure
    wick_ratio_threshold: float = 1.5         # wick length / body length ratio
    volume_divergence_lookback: int = 20      # bars to check volume trend at level
    ema_period: int = 20
    multi_touch_lookback: int = 20            # bars to count level touches
    multi_touch_penalty_threshold: int = 4    # 4+ touches → penalty

    # Confidence-to-size mapping
    full_size_min_score: int = 4              # score >= 4 → full size
    half_size_min_score: int = 2              # score 2-3 → half size
    # score 0-1 → quarter size
    # score < 0 → skip


@dataclass
class SidewaysSignal:
    idx: int
    side: SideEnum
    mode: SidewaysMode
    price: float
    val: float
    vah: float
    poc: float
    regime: str
    confidence: float = 1.0        # v0.3: 0.0, 0.25, 0.5, or 1.0
    score: int = 0                 # v0.3: raw score -5 to +5
    signals_detail: dict = field(default_factory=dict)  # per-signal breakdown for analysis
    reason: str = ""


def _score_long_bounce(
    i: int, val: float,
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    ema_arr: np.ndarray, vol_avg: np.ndarray,
    cfg: SidewaysConfig,
) -> tuple[int, dict]:
    """Score LONG bounce VAL signal. Returns (score, details_dict)."""
    score = 0
    details = {}

    # Signal 1: Higher low structure (recent low > previous low)
    lb = cfg.structure_lookback
    if i >= lb * 2:
        recent_low = float(np.min(lows[i - lb:i + 1]))
        previous_low = float(np.min(lows[i - lb * 2:i - lb]))
        if recent_low > previous_low:
            score += 1
            details["structure_higher_low"] = True
        else:
            details["structure_higher_low"] = False

    # Signal 2: Wick rejection (long lower wick vs body)
    body_size = abs(closes[i] - closes[i - 1])
    lower_wick = min(closes[i], closes[i - 1]) - lows[i]
    if body_size > 0 and lower_wick / body_size > cfg.wick_ratio_threshold:
        score += 1
        details["wick_rejection"] = True
    else:
        details["wick_rejection"] = False

    # Signal 3: Volume divergence (this touch has lower volume than previous touches at VAL)
    prev_val_touches_vol = []
    lookback = cfg.volume_divergence_lookback
    for k in range(max(0, i - lookback), i):
        if lows[k] <= val * (1 + cfg.touch_tolerance) and lows[k] >= val * (1 - cfg.touch_tolerance):
            prev_val_touches_vol.append(volumes[k])
    if prev_val_touches_vol:
        avg_prev_vol = float(np.mean(prev_val_touches_vol))
        if volumes[i] < avg_prev_vol * 0.9:
            score += 1
            details["volume_divergence"] = True
        else:
            details["volume_divergence"] = False
    else:
        details["volume_divergence"] = "no_prior_touches"

    # Signal 4: EMA20 alignment (price above EMA20 = bullish context)
    if i < len(ema_arr) and closes[i] > ema_arr[i]:
        score += 1
        details["ema_aligned"] = True
    else:
        details["ema_aligned"] = False

    # Signal 5: Multi-touch penalty
    touch_count = 0
    for k in range(max(0, i - cfg.multi_touch_lookback), i):
        if lows[k] <= val * (1 + cfg.touch_tolerance) and lows[k] >= val * (1 - cfg.touch_tolerance):
            touch_count += 1
    if touch_count >= cfg.multi_touch_penalty_threshold:
        score -= 1
        details["multi_touch_penalty"] = touch_count
    else:
        details["multi_touch_penalty"] = 0

    return score, details


def _score_short_reject(
    i: int, vah: float,
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    ema_arr: np.ndarray, vol_avg: np.ndarray,
    cfg: SidewaysConfig,
) -> tuple[int, dict]:
    """Score SHORT reject VAH signal."""
    score = 0
    details = {}

    # Signal 1: Lower high structure
    lb = cfg.structure_lookback
    if i >= lb * 2:
        recent_high = float(np.max(highs[i - lb:i + 1]))
        previous_high = float(np.max(highs[i - lb * 2:i - lb]))
        if recent_high < previous_high:
            score += 1
            details["structure_lower_high"] = True
        else:
            details["structure_lower_high"] = False

    # Signal 2: Wick rejection (long upper wick)
    body_size = abs(closes[i] - closes[i - 1])
    upper_wick = highs[i] - max(closes[i], closes[i - 1])
    if body_size > 0 and upper_wick / body_size > cfg.wick_ratio_threshold:
        score += 1
        details["wick_rejection"] = True
    else:
        details["wick_rejection"] = False

    # Signal 3: Volume divergence at VAH
    prev_vah_touches_vol = []
    lookback = cfg.volume_divergence_lookback
    for k in range(max(0, i - lookback), i):
        if highs[k] >= vah * (1 - cfg.touch_tolerance) and highs[k] <= vah * (1 + cfg.touch_tolerance):
            prev_vah_touches_vol.append(volumes[k])
    if prev_vah_touches_vol:
        avg_prev_vol = float(np.mean(prev_vah_touches_vol))
        if volumes[i] < avg_prev_vol * 0.9:
            score += 1
            details["volume_divergence"] = True
        else:
            details["volume_divergence"] = False
    else:
        details["volume_divergence"] = "no_prior_touches"

    # Signal 4: EMA20 alignment (price below EMA20 = bearish context)
    if i < len(ema_arr) and closes[i] < ema_arr[i]:
        score += 1
        details["ema_aligned"] = True
    else:
        details["ema_aligned"] = False

    # Signal 5: Multi-touch penalty
    touch_count = 0
    for k in range(max(0, i - cfg.multi_touch_lookback), i):
        if highs[k] >= vah * (1 - cfg.touch_tolerance) and highs[k] <= vah * (1 + cfg.touch_tolerance):
            touch_count += 1
    if touch_count >= cfg.multi_touch_penalty_threshold:
        score -= 1
        details["multi_touch_penalty"] = touch_count
    else:
        details["multi_touch_penalty"] = 0

    return score, details


def _score_to_confidence(score: int, cfg: SidewaysConfig) -> float:
    """Convert raw score to position sizing confidence (0.0 to 1.0)."""
    if score < 0:
        return 0.0   # skip trade
    elif score >= cfg.full_size_min_score:
        return 1.0   # full size
    elif score >= cfg.half_size_min_score:
        return 0.5   # half size
    else:
        return 0.25  # quarter size


def generate_sideways_signals(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: SidewaysConfig,
) -> list[SidewaysSignal]:
    """
    Generate signals sideways tektok with confidence scoring.
    All qualifying signals are emitted; confidence adjusts position size (not filter).
    """
    n = len(closes)
    signals: list[SidewaysSignal] = []

    # Precompute
    vol_avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - 19)
        vol_avg[i] = float(np.mean(volumes[start:i + 1])) if i > start else 1.0

    ema_arr = ema(closes, cfg.ema_period)

    last_long_bar = -9999
    last_short_bar = -9999

    for i in range(50, n):
        rs = regime_states[i]

        # Filter 1: regime
        if not cfg.skip_regime_filter:
            if rs.regime not in cfg.allowed_regimes:
                continue

        # Filter 2: range width
        if not cfg.skip_range_width_filter:
            if rs.range_width_pct <= 0 or rs.range_width_pct >= cfg.range_max_width_pct:
                continue

        vah = rs.vah
        val = rs.val
        poc = rs.poc

        if vah <= 0 or val <= 0 or vah <= val:
            continue

        h, l, c = highs[i], lows[i], closes[i]
        v = volumes[i]
        vol_ok = v > vol_avg[i] * cfg.volume_multiplier

        cooldown_long_ok = (i - last_long_bar) >= cfg.cooldown_bars
        cooldown_short_ok = (i - last_short_bar) >= cfg.cooldown_bars

        touch_val = (l <= val * (1 + cfg.touch_tolerance)) and (l >= val * (1 - cfg.touch_tolerance))
        touch_vah = (h >= vah * (1 - cfg.touch_tolerance)) and (h <= vah * (1 + cfg.touch_tolerance))

        wick_below_val = l < val * (1 - cfg.touch_tolerance) and c > val
        wick_above_vah = h > vah * (1 + cfg.touch_tolerance) and c < vah

        bullish_candle = c > closes[i - 1]
        bearish_candle = c < closes[i - 1]

        # ─── LONG BOUNCE VAL ───
        if touch_val and bullish_candle and vol_ok and c > val and cooldown_long_ok:
            if cfg.enable_confidence_scoring:
                score, details = _score_long_bounce(i, val, highs, lows, closes, volumes, ema_arr, vol_avg, cfg)
                confidence = _score_to_confidence(score, cfg)
            else:
                score, details, confidence = 0, {}, 1.0

            if confidence > 0.0:
                signals.append(SidewaysSignal(
                    idx=i, side=SideEnum.LONG, mode=SidewaysMode.BOUNCE_VAL,
                    price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                    regime=rs.regime.value,
                    confidence=confidence, score=score, signals_detail=details,
                    reason="touch_val_bullish_vol_ok",
                ))
                last_long_bar = i
            continue

        # ─── LONG FAKE BREAKDOWN ───
        if wick_below_val and vol_ok and cooldown_long_ok:
            if cfg.enable_confidence_scoring:
                score, details = _score_long_bounce(i, val, highs, lows, closes, volumes, ema_arr, vol_avg, cfg)
                confidence = _score_to_confidence(score, cfg)
            else:
                score, details, confidence = 0, {}, 1.0

            if confidence > 0.0:
                signals.append(SidewaysSignal(
                    idx=i, side=SideEnum.LONG, mode=SidewaysMode.FAKE_BREAKDOWN,
                    price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                    regime=rs.regime.value,
                    confidence=confidence, score=score, signals_detail=details,
                    reason="wick_below_val_reclaim",
                ))
                last_long_bar = i
            continue

        # ─── SHORT REJECT VAH ───
        if touch_vah and bearish_candle and vol_ok and c < vah and cooldown_short_ok:
            if cfg.enable_confidence_scoring:
                score, details = _score_short_reject(i, vah, highs, lows, closes, volumes, ema_arr, vol_avg, cfg)
                confidence = _score_to_confidence(score, cfg)
            else:
                score, details, confidence = 0, {}, 1.0

            if confidence > 0.0:
                signals.append(SidewaysSignal(
                    idx=i, side=SideEnum.SHORT, mode=SidewaysMode.REJECT_VAH,
                    price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                    regime=rs.regime.value,
                    confidence=confidence, score=score, signals_detail=details,
                    reason="touch_vah_bearish_vol_ok",
                ))
                last_short_bar = i
            continue

        # ─── SHORT FAKE BREAKOUT ───
        if wick_above_vah and vol_ok and cooldown_short_ok:
            if cfg.enable_confidence_scoring:
                score, details = _score_short_reject(i, vah, highs, lows, closes, volumes, ema_arr, vol_avg, cfg)
                confidence = _score_to_confidence(score, cfg)
            else:
                score, details, confidence = 0, {}, 1.0

            if confidence > 0.0:
                signals.append(SidewaysSignal(
                    idx=i, side=SideEnum.SHORT, mode=SidewaysMode.FAKE_BREAKOUT,
                    price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                    regime=rs.regime.value,
                    confidence=confidence, score=score, signals_detail=details,
                    reason="wick_above_vah_rejection",
                ))
                last_short_bar = i
            continue

    return signals


__all__ = ["SideEnum", "SidewaysMode", "SidewaysConfig", "SidewaysSignal", "generate_sideways_signals"]
