"""
mode3_regime.py — Phase A: Regime Detector + Anchored VAH/VAL + 5-line Value Area
================================================================================

Core engine untuk deteksi market regime dan compute value area levels.
Design filosofis: nested classifier 3-layer.

LAYER 1: Regime classifier (4 output: Bull/Bear/Accumulation/Distribution)
LAYER 2: Continuation vs Reversal classifier (Phase C)
LAYER 3: State machine 3-way confirmation (Phase B)

Phase A ini fokus ke:
- Anchored VAH/VAL detection (bukan rolling)
- Value area 5 line (VAH, VAL, POC, VWAP, VWAP±1σ)
- 4-regime basic classifier

Author: BabaBot team
Version: 0.1.0 (Phase A)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ═════════════════════════════════════════════════════════════
# ENUMS & CONFIG
# ═════════════════════════════════════════════════════════════

class Regime(Enum):
    """4 fundamental market regimes."""
    UNKNOWN = "unknown"
    BULL_MARKUP = "bull_markup"        # Trending up, expanding VA
    BEAR_MARKDOWN = "bear_markdown"    # Trending down, expanding VA
    ACCUMULATION = "accumulation"      # Range di bawah/mid, low volatility
    DISTRIBUTION = "distribution"      # Range di puncak, higher volume


@dataclass
class RegimeConfig:
    """Tunable parameters untuk regime detection."""

    # Value Area computation
    va_percentage: float = 0.70          # 70% volume = Value Area (standard MP)
    vp_bin_count: int = 20               # Volume Profile bin resolution

    # Range detection thresholds
    range_min_candles: int = 8           # Minimum candles untuk qualify as range
    range_max_width_pct: float = 0.04    # Max range width 4% untuk qualify as range
    range_touch_tolerance: float = 0.002 # 0.2% tolerance untuk "touch" VAH/VAL
    range_confirmation_candles: int = 3  # Consecutive candles inside range untuk confirm

    # Trend detection
    trend_min_candles: int = 15          # Min candles untuk qualify as trend
    trend_min_move_pct: float = 0.05     # 5% move dari start untuk qualify as trend

    # Rolling windows per timeframe (candles)
    window_daily: int = 30               # 30 days lookback for daily VA
    window_4h: int = 42                  # 7 days × 6 candles/day
    window_1h: int = 72                  # 3 days × 24 candles/day
    window_15m: int = 96                 # 1 day × 96 candles/day

    # VWAP + sigma
    vwap_sigma_multiplier: float = 1.0   # ±1σ bands (tune-able 0.5-1.5)

    # Volatility filter (DEAD MARKET mode)
    dead_market_atr_ratio: float = 0.20  # Skip trade if ATR < 20% median


@dataclass
class ValueArea:
    """5-line value area: VAH, VAL, POC, VWAP, VWAP±1σ."""
    vah: float
    val: float
    poc: float
    vwap: float
    vwap_upper: float  # VWAP + 1σ
    vwap_lower: float  # VWAP - 1σ
    volume_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    anchor_start_idx: int = 0
    anchor_end_idx: int = 0
    is_anchored: bool = False  # True kalau ini range-anchored, False kalau rolling


@dataclass
class RegimeState:
    """Current regime state di suatu candle."""
    regime: Regime
    confidence: float  # 0.0 - 1.0
    prior_regime: Regime = Regime.UNKNOWN
    current_va: Optional[ValueArea] = None
    prior_va: Optional[ValueArea] = None  # Untuk detect old-VAH-as-new-support (retest)
    range_start_idx: int = -1
    range_end_idx: int = -1  # -1 kalau range masih ongoing
    trend_start_idx: int = -1


# ═════════════════════════════════════════════════════════════
# VALUE AREA COMPUTATION
# ═════════════════════════════════════════════════════════════

def compute_value_area(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: RegimeConfig,
    anchor_start: int = 0,
    anchor_end: Optional[int] = None,
    is_anchored: bool = False,
) -> ValueArea:
    """
    Compute value area (VAH, VAL, POC, VWAP, ±1σ) dari OHLCV slice.

    Args:
        highs, lows, closes, volumes: numpy arrays
        cfg: config
        anchor_start, anchor_end: index range untuk compute
        is_anchored: True kalau ini range-anchored (levels persist)

    Returns:
        ValueArea object
    """
    end = anchor_end if anchor_end is not None else len(closes)
    if end <= anchor_start:
        raise ValueError("anchor_end must be > anchor_start")

    h = highs[anchor_start:end]
    l = lows[anchor_start:end]
    c = closes[anchor_start:end]
    v = volumes[anchor_start:end]

    n = len(c)
    if n < 2:
        # Insufficient data — return degenerate
        px = float(c[-1] if len(c) > 0 else 0)
        return ValueArea(
            vah=px, val=px, poc=px, vwap=px,
            vwap_upper=px, vwap_lower=px,
            anchor_start_idx=anchor_start,
            anchor_end_idx=end,
            is_anchored=is_anchored,
        )

    # ─── Volume Profile: histogram of volume per price bin ───
    price_min = float(np.min(l))
    price_max = float(np.max(h))
    if price_max <= price_min:
        # Zero-range edge case
        return ValueArea(
            vah=price_max, val=price_min, poc=price_min, vwap=price_min,
            vwap_upper=price_min, vwap_lower=price_min,
            anchor_start_idx=anchor_start, anchor_end_idx=end,
            is_anchored=is_anchored,
        )

    bin_size = (price_max - price_min) / cfg.vp_bin_count
    profile = np.zeros(cfg.vp_bin_count, dtype=float)

    for i in range(n):
        # Distribute candle volume across bins it spans (Time Price Opportunity approximation)
        # Simpler: use midpoint
        mid = (h[i] + l[i]) / 2
        bin_idx = min(cfg.vp_bin_count - 1, int((mid - price_min) / bin_size))
        profile[bin_idx] += v[i]

    total_vol = profile.sum()
    if total_vol <= 0:
        # No volume — degenerate
        return ValueArea(
            vah=price_max, val=price_min, poc=(price_max + price_min) / 2,
            vwap=(price_max + price_min) / 2,
            vwap_upper=price_max, vwap_lower=price_min,
            volume_profile=profile,
            anchor_start_idx=anchor_start, anchor_end_idx=end,
            is_anchored=is_anchored,
        )

    # ─── POC: bin dengan volume terbesar ───
    poc_bin = int(np.argmax(profile))
    poc = price_min + (poc_bin + 0.5) * bin_size

    # ─── VAH & VAL: expand dari POC sampai capture 70% volume ───
    target_vol = total_vol * cfg.va_percentage
    accum = profile[poc_bin]
    lo_bin = poc_bin
    hi_bin = poc_bin

    while accum < target_vol and (lo_bin > 0 or hi_bin < cfg.vp_bin_count - 1):
        vol_below = profile[lo_bin - 1] if lo_bin > 0 else 0.0
        vol_above = profile[hi_bin + 1] if hi_bin < cfg.vp_bin_count - 1 else 0.0

        # Expand ke arah volume lebih tinggi (standard MP algorithm)
        if vol_above >= vol_below and hi_bin < cfg.vp_bin_count - 1:
            hi_bin += 1
            accum += vol_above
        elif lo_bin > 0:
            lo_bin -= 1
            accum += vol_below
        else:
            break

    vah = price_min + (hi_bin + 1) * bin_size  # Upper edge of highest bin
    val = price_min + lo_bin * bin_size         # Lower edge of lowest bin

    # ─── VWAP: volume-weighted average price ───
    typical = (h + l + c) / 3
    vwap = float(np.sum(typical * v) / np.sum(v))

    # ─── Standard deviation dari VWAP (weighted) ───
    variance = float(np.sum(((typical - vwap) ** 2) * v) / np.sum(v))
    sigma = np.sqrt(variance) * cfg.vwap_sigma_multiplier
    vwap_upper = vwap + sigma
    vwap_lower = vwap - sigma

    return ValueArea(
        vah=vah,
        val=val,
        poc=poc,
        vwap=vwap,
        vwap_upper=vwap_upper,
        vwap_lower=vwap_lower,
        volume_profile=profile,
        anchor_start_idx=anchor_start,
        anchor_end_idx=end,
        is_anchored=is_anchored,
    )


# ═════════════════════════════════════════════════════════════
# RANGE DETECTION (untuk anchored VAH/VAL)
# ═════════════════════════════════════════════════════════════

def is_price_in_range(
    price: float,
    va: ValueArea,
    tolerance: float,
) -> bool:
    """Check kalau price di dalam range VAH-VAL (dengan tolerance)."""
    upper_bound = va.vah * (1 + tolerance)
    lower_bound = va.val * (1 - tolerance)
    return lower_bound <= price <= upper_bound


def detect_range(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: RegimeConfig,
    start_idx: int,
    max_lookforward: int = 100,
) -> Optional[tuple[int, int, ValueArea]]:
    """
    Detect apakah dari start_idx market masuk range mode.

    Strategy:
    1. Compute tentative VA dari window kecil (range_min_candles)
    2. Cek apakah range width < range_max_width_pct
    3. Cek apakah range_confirmation_candles berikut close di dalam VA
    4. Kalau confirmed, extend range sampai break

    Returns:
        (range_start, range_end, anchored_va) kalau range confirmed
        None kalau nggak ada range
    """
    n = len(closes)
    if start_idx + cfg.range_min_candles >= n:
        return None

    # Step 1: Tentative VA dari window awal
    tentative_end = min(start_idx + cfg.range_min_candles, n)
    tentative_va = compute_value_area(
        highs, lows, closes, volumes, cfg,
        anchor_start=start_idx,
        anchor_end=tentative_end,
    )

    # Step 2: Cek range width
    if tentative_va.val <= 0:
        return None
    range_width_pct = (tentative_va.vah - tentative_va.val) / tentative_va.val
    if range_width_pct > cfg.range_max_width_pct:
        return None  # Terlalu wide untuk qualify as range

    # Step 3: Cek confirmation candles setelah tentative window
    confirmation_end = min(tentative_end + cfg.range_confirmation_candles, n)
    in_range_count = 0
    for i in range(tentative_end, confirmation_end):
        if is_price_in_range(closes[i], tentative_va, cfg.range_touch_tolerance):
            in_range_count += 1

    if in_range_count < cfg.range_confirmation_candles - 1:  # Allow 1 candle luar
        return None

    # Step 4: Extend range — anchor VA sampai break happens
    range_end = tentative_end
    for i in range(tentative_end, min(start_idx + max_lookforward, n)):
        # Range break kalau close beyond VAH atau VAL dengan margin
        break_upper = closes[i] > tentative_va.vah * (1 + cfg.range_touch_tolerance)
        break_lower = closes[i] < tentative_va.val * (1 - cfg.range_touch_tolerance)
        if break_upper or break_lower:
            range_end = i
            break
        range_end = i + 1

    # Recompute anchored VA dari full range period untuk final accuracy
    final_va = compute_value_area(
        highs, lows, closes, volumes, cfg,
        anchor_start=start_idx,
        anchor_end=range_end,
        is_anchored=True,
    )

    return (start_idx, range_end, final_va)


# ═════════════════════════════════════════════════════════════
# TREND DETECTION
# ═════════════════════════════════════════════════════════════

def detect_trend(
    closes: np.ndarray,
    start_idx: int,
    cfg: RegimeConfig,
) -> tuple[Optional[Regime], int]:
    """
    Detect apakah dari start_idx market lagi trending (Bull markup / Bear markdown).

    Simple approach: cek move price dari start_idx ke sampai +trend_min_candles.
    Kalau move ≥ trend_min_move_pct dan monotonic-ish → trend.

    Returns:
        (regime, trend_end_idx) — regime bisa Bull, Bear, atau None (no trend)
    """
    n = len(closes)
    if start_idx + cfg.trend_min_candles >= n:
        return (None, start_idx)

    start_price = closes[start_idx]
    if start_price <= 0:
        return (None, start_idx)

    end_idx = min(start_idx + cfg.trend_min_candles, n - 1)
    end_price = closes[end_idx]
    move_pct = (end_price - start_price) / start_price

    if abs(move_pct) < cfg.trend_min_move_pct:
        return (None, start_idx)

    regime = Regime.BULL_MARKUP if move_pct > 0 else Regime.BEAR_MARKDOWN

    # Extend trend end sampai reverse happens
    trend_end = end_idx
    for i in range(end_idx, n):
        if regime == Regime.BULL_MARKUP:
            # Bull ends kalau retrace >50% dari trend move
            retrace = (end_price - closes[i]) / (end_price - start_price + 1e-9)
            if retrace > 0.5:
                trend_end = i
                break
        else:
            retrace = (closes[i] - end_price) / (start_price - end_price + 1e-9)
            if retrace > 0.5:
                trend_end = i
                break
        trend_end = i

    return (regime, trend_end)


# ═════════════════════════════════════════════════════════════
# REGIME CLASSIFIER (Layer 1)
# ═════════════════════════════════════════════════════════════

def classify_regime_at(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: RegimeConfig,
    idx: int,
    prior_regime: Regime = Regime.UNKNOWN,
) -> RegimeState:
    """
    Classify regime pada candle index `idx`, berdasarkan konteks sekitar.

    Strategy:
    1. Cek dulu apakah ada range yang aktif dan mengandung idx
    2. Kalau nggak, cek trend (bull/bear markup/markdown)
    3. Discriminate accumulation vs distribution by relative price level
    """
    lookback = cfg.window_1h
    ctx_start = max(0, idx - lookback)

    # Scan multiple candidate start points untuk detect range yang mengandung idx
    range_result = None
    scan_step = max(1, cfg.range_min_candles // 3)
    for candidate_start in range(ctx_start, idx - cfg.range_min_candles, scan_step):
        result = detect_range(
            highs, lows, closes, volumes, cfg,
            start_idx=candidate_start,
            max_lookforward=lookback,
        )
        if result is None:
            continue
        rng_start, rng_end, _ = result
        # Cek apakah idx dalam range ini (range masih ongoing atau baru break)
        if rng_start <= idx <= rng_end + cfg.range_confirmation_candles:
            range_result = result
            break

    if range_result is not None:
        rng_start, rng_end, rng_va = range_result
        # Discriminate accumulation vs distribution
        price_now = closes[idx]
        recent_high = float(np.max(highs[ctx_start:idx + 1]))
        recent_low = float(np.min(lows[ctx_start:idx + 1]))
        span = recent_high - recent_low
        if span > 1e-9:
            range_level_pct = (price_now - recent_low) / span
        else:
            range_level_pct = 0.5

        if range_level_pct < 0.4:
            regime = Regime.ACCUMULATION
        elif range_level_pct > 0.6:
            regime = Regime.DISTRIBUTION
        else:
            if prior_regime == Regime.BULL_MARKUP:
                regime = Regime.DISTRIBUTION
            elif prior_regime == Regime.BEAR_MARKDOWN:
                regime = Regime.ACCUMULATION
            else:
                regime = Regime.ACCUMULATION

        return RegimeState(
            regime=regime,
            confidence=0.75,
            prior_regime=prior_regime,
            current_va=rng_va,
            range_start_idx=rng_start,
            range_end_idx=-1 if idx <= rng_end else rng_end,
        )

    # No range → check trend
    trend_regime, trend_end = detect_trend(closes, ctx_start, cfg)
    if trend_regime is not None:
        trend_va = compute_value_area(
            highs, lows, closes, volumes, cfg,
            anchor_start=ctx_start,
            anchor_end=idx + 1,
            is_anchored=False,
        )
        return RegimeState(
            regime=trend_regime,
            confidence=0.65,
            prior_regime=prior_regime,
            current_va=trend_va,
            trend_start_idx=ctx_start,
        )

    # Unknown regime — but still provide rolling VA for state machine to use
    fallback_va = compute_value_area(
        highs, lows, closes, volumes, cfg,
        anchor_start=ctx_start,
        anchor_end=idx + 1,
        is_anchored=False,
    )
    return RegimeState(
        regime=Regime.UNKNOWN,
        confidence=0.3,
        prior_regime=prior_regime,
        current_va=fallback_va,
    )


def classify_regime_series(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: RegimeConfig,
    warmup: int = 100,
) -> list[RegimeState]:
    """
    Classify regime untuk semua candle dalam series.

    Returns list of RegimeState, satu per candle (warmup diisi UNKNOWN).
    """
    n = len(closes)
    states: list[RegimeState] = []
    prior_regime = Regime.UNKNOWN

    for i in range(n):
        if i < warmup:
            states.append(RegimeState(regime=Regime.UNKNOWN, confidence=0.0))
            continue

        state = classify_regime_at(
            highs, lows, closes, volumes, cfg,
            idx=i,
            prior_regime=prior_regime,
        )

        # Update prior regime only when confidence is decent
        if state.confidence >= 0.5 and state.regime != Regime.UNKNOWN:
            prior_regime = state.regime

        states.append(state)

    return states


# ═════════════════════════════════════════════════════════════
# HELPER: ATR untuk dead market detection
# ═════════════════════════════════════════════════════════════

def compute_atr(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Compute Average True Range dengan Wilder smoothing."""
    n = len(closes)
    if n < 2:
        return np.zeros(n)

    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)

    atr = np.zeros(n)
    if n < period:
        return atr

    atr[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return atr


def is_dead_market(
    atr_now: float,
    atr_median: float,
    cfg: RegimeConfig,
) -> bool:
    """Check kalau market lagi dead (volatility rendah anomalous)."""
    if atr_median <= 0:
        return False
    ratio = atr_now / atr_median
    return ratio < cfg.dead_market_atr_ratio


# ═════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════

__all__ = [
    "Regime",
    "RegimeConfig",
    "ValueArea",
    "RegimeState",
    "compute_value_area",
    "detect_range",
    "detect_trend",
    "classify_regime_at",
    "classify_regime_series",
    "compute_atr",
    "is_dead_market",
    "is_price_in_range",
]
