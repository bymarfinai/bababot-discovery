"""
regime.py — Layer 1: 4-Regime Detector
========================================
Detect 4 fundamental market regimes:
- BULL_MARKUP: trending up
- BEAR_MARKDOWN: trending down
- ACCUMULATION: range di bawah, prior bear, siap bull
- DISTRIBUTION: range di atas, prior bull, siap bear

Approach: layered detection
1. Check range vs trend (dari VAH/VAL width + ATR contraction)
2. Kalau range → discriminate accumulation vs distribution by prior context
3. Kalau trend → discriminate bull vs bear by direction

--- Fix #3 (2026-07-13) ---
Relaxed trend detection to reduce UNKNOWN regime frequency:
- trend_ema_distance: 0.003 → 0.0015 (0.15% jarak EMA cukup buat qualify trend)
- trend_min_slope_pct: 0.005 → 0.003
- is_trending: (ema_diff >= threshold) AND slope > 0 → (ema_diff >= threshold) OR (steep slope)
  → Early trend (EMA baru cross, jarak masih tipis, tapi slope momentum kuat) sekarang ke-catch
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema, atr, rolling_high_low, slope_pct


class Regime(Enum):
    UNKNOWN = "unknown"
    BULL_MARKUP = "bull_markup"
    BEAR_MARKDOWN = "bear_markdown"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


@dataclass
class RegimeConfig:
    # VA window
    lookback: int = 50

    # Range detection
    range_max_width_pct: float = 0.04         # VAH-VAL width < 4% = potentially range
    range_min_candles: int = 8                # butuh 8+ candle di kondisi range
    atr_contraction_ratio: float = 0.7        # ATR < 70% median = contracted (range)
    atr_median_lookback: int = 100            # median ATR over 100 bars

    # Trend detection (Fix #3: relaxed 2026-07-13)
    ema_fast_period: int = 20
    ema_slow_period: int = 50
    trend_ema_distance: float = 0.0015        # was 0.003 — 0.15% EMA distance cukup
    trend_slope_lookback: int = 20            # cek slope EMA over 20 bars
    trend_min_slope_pct: float = 0.003        # was 0.005 — slope threshold lebih sensitif

    # Accumulation vs Distribution discrimination
    range_position_low_threshold: float = 0.35   # < 35% dari swing = low position (accumulation)
    range_position_high_threshold: float = 0.65  # > 65% = high position (distribution)


@dataclass
class RegimeState:
    regime: Regime
    confidence: float
    prior_regime: Regime = Regime.UNKNOWN

    # Levels
    vah: float = 0.0
    val: float = 0.0
    poc: float = 0.0

    # Range metadata
    range_width_pct: float = 0.0
    range_position: float = 0.5  # 0.0 = at VAL, 1.0 = at VAH
    is_range: bool = False

    # Trend metadata
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    ema_diff_pct: float = 0.0
    ema_fast_slope: float = 0.0

    reason: str = ""


def classify_regime_series(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: RegimeConfig,
    warmup: int = 100,
) -> list[RegimeState]:
    """
    Classify regime untuk setiap candle di series.
    """
    n = len(closes)

    # Pre-compute indicators (vectorized)
    vah_arr, val_arr = rolling_high_low(highs, lows, cfg.lookback)
    poc_arr = (vah_arr + val_arr) / 2

    ema_fast_arr = ema(closes, cfg.ema_fast_period)
    ema_slow_arr = ema(closes, cfg.ema_slow_period)
    ema_fast_slope_arr = slope_pct(ema_fast_arr, cfg.trend_slope_lookback)

    atr_arr = atr(highs, lows, closes, 14)

    # Rolling median ATR (untuk contraction detection)
    atr_median_arr = np.zeros(n)
    for i in range(n):
        start = max(0, i - cfg.atr_median_lookback + 1)
        if i - start >= 20:
            atr_median_arr[i] = float(np.median(atr_arr[start:i + 1]))

    states: list[RegimeState] = []
    prior_regime = Regime.UNKNOWN

    # For accumulation/distribution discrimination
    for i in range(n):
        if i < warmup:
            states.append(RegimeState(regime=Regime.UNKNOWN, confidence=0.0))
            continue

        vah = float(vah_arr[i])
        val = float(val_arr[i])
        poc = float(poc_arr[i])
        cur_close = float(closes[i])
        cur_atr = float(atr_arr[i])
        median_atr = float(atr_median_arr[i])

        # Range width
        range_width_pct = (vah - val) / val if val > 0 else 0.0

        # Position dalam range (0 = at VAL, 1 = at VAH)
        span = vah - val
        range_position = (cur_close - val) / span if span > 1e-9 else 0.5

        # ATR contraction check
        atr_contracted = median_atr > 0 and cur_atr < median_atr * cfg.atr_contraction_ratio

        # Range detection
        range_narrow = 0 < range_width_pct < cfg.range_max_width_pct
        is_range = range_narrow and atr_contracted

        # Trend detection (Fix #3: OR condition — catch early trend)
        ema_f = float(ema_fast_arr[i])
        ema_s = float(ema_slow_arr[i])
        ema_diff_pct = abs(ema_f - ema_s) / ema_s if ema_s > 0 else 0.0
        ema_fast_slope = float(ema_fast_slope_arr[i])

        # NEW: trend qualifies if EITHER EMA jarak lebar OR slope momentum kuat
        is_trending = (
            ema_diff_pct >= cfg.trend_ema_distance
            or abs(ema_fast_slope) >= cfg.trend_min_slope_pct
        )
        trend_up = is_trending and ema_f > ema_s and ema_fast_slope >= 0
        trend_down = is_trending and ema_f < ema_s and ema_fast_slope <= 0

        # Determine regime
        regime = Regime.UNKNOWN
        confidence = 0.0
        reason = ""

        if is_range:
            # Range mode — discriminate accumulation vs distribution
            if range_position < cfg.range_position_low_threshold:
                regime = Regime.ACCUMULATION
                confidence = 0.75
                reason = f"range_pos_low_{range_position:.2f}"
            elif range_position > cfg.range_position_high_threshold:
                regime = Regime.DISTRIBUTION
                confidence = 0.75
                reason = f"range_pos_high_{range_position:.2f}"
            else:
                # Mid-range — use prior regime as tiebreaker
                if prior_regime == Regime.BULL_MARKUP:
                    regime = Regime.DISTRIBUTION
                    confidence = 0.6
                    reason = "mid_range_post_bull"
                elif prior_regime == Regime.BEAR_MARKDOWN:
                    regime = Regime.ACCUMULATION
                    confidence = 0.6
                    reason = "mid_range_post_bear"
                else:
                    regime = Regime.ACCUMULATION
                    confidence = 0.4
                    reason = "mid_range_ambiguous"

        elif trend_up:
            regime = Regime.BULL_MARKUP
            # Confidence scale: wide EMA distance = high confidence
            confidence = min(0.85, 0.5 + ema_diff_pct * 20 + abs(ema_fast_slope) * 10)
            reason = f"trend_up_ema_diff_{ema_diff_pct:.4f}_slope_{ema_fast_slope:.4f}"

        elif trend_down:
            regime = Regime.BEAR_MARKDOWN
            confidence = min(0.85, 0.5 + ema_diff_pct * 20 + abs(ema_fast_slope) * 10)
            reason = f"trend_down_ema_diff_{ema_diff_pct:.4f}_slope_{ema_fast_slope:.4f}"

        else:
            # Ambiguous: neither clear range nor clear trend
            regime = Regime.UNKNOWN
            confidence = 0.3
            reason = "ambiguous"

        state = RegimeState(
            regime=regime,
            confidence=confidence,
            prior_regime=prior_regime,
            vah=vah,
            val=val,
            poc=poc,
            range_width_pct=range_width_pct,
            range_position=range_position,
            is_range=is_range,
            ema_fast=ema_f,
            ema_slow=ema_s,
            ema_diff_pct=ema_diff_pct,
            ema_fast_slope=ema_fast_slope,
            reason=reason,
        )
        states.append(state)

        # Update prior_regime (only for confident detections)
        if confidence >= 0.6 and regime in (Regime.BULL_MARKUP, Regime.BEAR_MARKDOWN):
            prior_regime = regime

    return states


__all__ = ["Regime", "RegimeConfig", "RegimeState", "classify_regime_series"]
