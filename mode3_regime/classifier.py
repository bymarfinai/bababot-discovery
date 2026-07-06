"""
classifier.py — Phase C: Continuation vs Reversal Classifier
=============================================================

Setelah trend (bull/bear), market masuk sideways. Bot harus tebak:
apakah ini pause (continuation) atau smart money reversal?

5-signal scoring quantitative:
1. Volume trend selama sideways (naik = reversal, turun = continuation)
2. Test count VAH/VAL (multiple = reversal, rare = continuation)
3. Range width (wide = reversal, tight = continuation)
4. Duration (panjang = reversal, pendek = continuation)
5. MTF confluence (higher TF trending = continuation, weakening = reversal)

Output: SidewaysBias enum + score, feed ke state machine untuk bias entry.

Author: BabaBot team
Version: 0.1.0 (Phase C)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .regime import Regime, RegimeConfig, ValueArea, RegimeState


# ═════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════

class SidewaysBias(Enum):
    """3 possible bias untuk sideways market."""
    CONTINUATION = "continuation"    # Bull → sideways → bull lanjut
    REVERSAL = "reversal"            # Bull → sideways → bear (distribution)
    AMBIGUOUS = "ambiguous"          # Nggak clear, trade both sides small


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

@dataclass
class ClassifierConfig:
    """Tunable parameters untuk continuation vs reversal classifier."""

    # Signal 1: Volume trend
    volume_trend_threshold_pct: float = 0.15    # ±15% volume change = signal
    volume_trend_lookback_ratio: float = 0.5    # Compare first half vs second half of sideways

    # Signal 2: Test count
    test_touch_tolerance: float = 0.003         # 0.3% tolerance untuk qualify as test
    test_count_continuation_max: int = 2        # ≤2 test = continuation
    test_count_reversal_min: int = 4            # ≥4 test = reversal

    # Signal 3: Range width
    range_width_continuation_max_pct: float = 0.02  # ≤2% = tight (continuation)
    range_width_reversal_min_pct: float = 0.03      # ≥3% = wide (reversal)

    # Signal 4: Duration
    duration_continuation_max_candles: int = 15  # ≤15 candle = short (continuation)
    duration_reversal_min_candles: int = 20      # ≥20 candle = long (reversal)

    # Signal 5: MTF confluence (higher TF trend momentum)
    mtf_momentum_lookback: int = 30              # Candle di higher TF untuk cek momentum
    mtf_momentum_weakening_pct: float = 0.02     # Trend melemah kalau slope drop 2%

    # Scoring thresholds
    score_continuation_min: int = 3              # ≥3 signal continuation → CONTINUATION
    score_reversal_min: int = 3                  # ≥3 signal reversal → REVERSAL


# ═════════════════════════════════════════════════════════════
# SCORE OBJECT
# ═════════════════════════════════════════════════════════════

@dataclass
class SidewaysAnalysis:
    """Hasil analisis sideways period."""
    bias: SidewaysBias
    confidence: float                        # 0.0 - 1.0
    continuation_score: int                  # 0-5
    reversal_score: int                      # 0-5

    # Signal breakdown (untuk debug/log)
    signal_volume: str = ""                  # "cont" / "rev" / "neutral"
    signal_test_count: str = ""
    signal_range_width: str = ""
    signal_duration: str = ""
    signal_mtf: str = ""

    # Raw metrics
    volume_change_pct: float = 0.0
    test_count_total: int = 0
    range_width_pct: float = 0.0
    duration_candles: int = 0

    reason: str = ""


# ═════════════════════════════════════════════════════════════
# SIGNAL EVALUATORS
# ═════════════════════════════════════════════════════════════

def signal_volume_trend(
    volumes: np.ndarray,
    start_idx: int,
    end_idx: int,
    cfg: ClassifierConfig,
) -> tuple[str, float]:
    """
    Signal 1: Volume trend selama sideways.

    Returns: ("cont"/"rev"/"neutral", volume_change_pct)
    - Volume TURUN → continuation (buyer/seller lelah)
    - Volume NAIK → reversal (smart money aktif distribution/accumulation)
    """
    n = end_idx - start_idx
    if n < 4:
        return ("neutral", 0.0)

    split = start_idx + int(n * cfg.volume_trend_lookback_ratio)
    first_half = volumes[start_idx:split]
    second_half = volumes[split:end_idx]

    if len(first_half) == 0 or len(second_half) == 0:
        return ("neutral", 0.0)

    vol_first = float(np.mean(first_half))
    vol_second = float(np.mean(second_half))

    if vol_first <= 0:
        return ("neutral", 0.0)

    change_pct = (vol_second - vol_first) / vol_first

    if change_pct >= cfg.volume_trend_threshold_pct:
        return ("rev", change_pct)
    elif change_pct <= -cfg.volume_trend_threshold_pct:
        return ("cont", change_pct)
    else:
        return ("neutral", change_pct)


def signal_test_count(
    highs: np.ndarray,
    lows: np.ndarray,
    va: ValueArea,
    start_idx: int,
    end_idx: int,
    cfg: ClassifierConfig,
) -> tuple[str, int]:
    """
    Signal 2: Berapa kali harga test VAH/VAL.

    Returns: ("cont"/"rev"/"neutral", total_test_count)
    - Test count RARE (≤2) → continuation
    - Test count MANY (≥4) → reversal
    """
    vah_tol_upper = va.vah * (1 + cfg.test_touch_tolerance)
    vah_tol_lower = va.vah * (1 - cfg.test_touch_tolerance)
    val_tol_upper = va.val * (1 + cfg.test_touch_tolerance)
    val_tol_lower = va.val * (1 - cfg.test_touch_tolerance)

    vah_touches = 0
    val_touches = 0
    prev_touched_vah = False
    prev_touched_val = False

    for i in range(start_idx, end_idx):
        # VAH touch: high in tolerance range
        vah_touched = vah_tol_lower <= highs[i] <= vah_tol_upper
        val_touched = val_tol_lower <= lows[i] <= val_tol_upper

        # Count only new touches (not consecutive candles all touching)
        if vah_touched and not prev_touched_vah:
            vah_touches += 1
        if val_touched and not prev_touched_val:
            val_touches += 1

        prev_touched_vah = vah_touched
        prev_touched_val = val_touched

    total = vah_touches + val_touches

    if total <= cfg.test_count_continuation_max:
        return ("cont", total)
    elif total >= cfg.test_count_reversal_min:
        return ("rev", total)
    else:
        return ("neutral", total)


def signal_range_width(
    va: ValueArea,
    cfg: ClassifierConfig,
) -> tuple[str, float]:
    """
    Signal 3: Range width VAH-VAL.

    Returns: ("cont"/"rev"/"neutral", width_pct)
    - Tight range (≤2%) → continuation (compression)
    - Wide range (≥3%) → reversal (fight over levels)
    """
    if va.val <= 0:
        return ("neutral", 0.0)

    width_pct = (va.vah - va.val) / va.val

    if width_pct <= cfg.range_width_continuation_max_pct:
        return ("cont", width_pct)
    elif width_pct >= cfg.range_width_reversal_min_pct:
        return ("rev", width_pct)
    else:
        return ("neutral", width_pct)


def signal_duration(
    start_idx: int,
    end_idx: int,
    cfg: ClassifierConfig,
) -> tuple[str, int]:
    """
    Signal 4: Berapa candle sideways sudah berlangsung.

    Returns: ("cont"/"rev"/"neutral", duration)
    - Duration pendek (≤15 candle) → continuation
    - Duration panjang (≥20 candle) → reversal
    """
    duration = end_idx - start_idx

    if duration <= cfg.duration_continuation_max_candles:
        return ("cont", duration)
    elif duration >= cfg.duration_reversal_min_candles:
        return ("rev", duration)
    else:
        return ("neutral", duration)


def signal_mtf_momentum(
    higher_tf_closes: Optional[np.ndarray],
    prior_regime: Regime,
    cfg: ClassifierConfig,
) -> tuple[str, float]:
    """
    Signal 5: Higher timeframe momentum.

    Returns: ("cont"/"rev"/"neutral", momentum_change_pct)
    - Higher TF trend masih strong → continuation
    - Higher TF trend melemah → reversal
    """
    if higher_tf_closes is None or len(higher_tf_closes) < cfg.mtf_momentum_lookback:
        return ("neutral", 0.0)

    lookback = cfg.mtf_momentum_lookback
    tail = higher_tf_closes[-lookback:]
    first_half = tail[:lookback // 2]
    second_half = tail[lookback // 2:]

    slope_first = float(np.polyfit(range(len(first_half)), first_half, 1)[0])
    slope_second = float(np.polyfit(range(len(second_half)), second_half, 1)[0])

    if abs(slope_first) < 1e-9:
        return ("neutral", 0.0)

    slope_change_pct = (slope_second - slope_first) / abs(slope_first)

    # Kalau prior bull, cek apakah momentum bull melemah
    if prior_regime == Regime.BULL_MARKUP:
        # Slope masih positif dan nggak drop banyak → continuation
        if slope_second > 0 and slope_change_pct > -cfg.mtf_momentum_weakening_pct:
            return ("cont", slope_change_pct)
        # Slope drop banyak atau negatif → reversal
        if slope_change_pct < -cfg.mtf_momentum_weakening_pct or slope_second <= 0:
            return ("rev", slope_change_pct)
    elif prior_regime == Regime.BEAR_MARKDOWN:
        # Mirror untuk bear
        if slope_second < 0 and slope_change_pct < cfg.mtf_momentum_weakening_pct:
            return ("cont", slope_change_pct)
        if slope_change_pct > cfg.mtf_momentum_weakening_pct or slope_second >= 0:
            return ("rev", slope_change_pct)

    return ("neutral", slope_change_pct)


# ═════════════════════════════════════════════════════════════
# COMBINED CLASSIFIER
# ═════════════════════════════════════════════════════════════

def analyze_sideways(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    va: ValueArea,
    start_idx: int,
    end_idx: int,
    prior_regime: Regime,
    cfg: ClassifierConfig,
    higher_tf_closes: Optional[np.ndarray] = None,
) -> SidewaysAnalysis:
    """
    Full analysis: run 5 signals, score, output bias.

    Args:
        highs, lows, closes, volumes: candle data
        va: anchored value area untuk sideways ini
        start_idx, end_idx: range dari sideways period
        prior_regime: regime sebelum sideways (BULL/BEAR/UNKNOWN)
        higher_tf_closes: optional higher timeframe untuk MTF signal
        cfg: config

    Returns:
        SidewaysAnalysis dengan bias + confidence
    """
    # Run 5 signals
    sig_vol, vol_change = signal_volume_trend(volumes, start_idx, end_idx, cfg)
    sig_test, test_count = signal_test_count(highs, lows, va, start_idx, end_idx, cfg)
    sig_width, width = signal_range_width(va, cfg)
    sig_dur, duration = signal_duration(start_idx, end_idx, cfg)
    sig_mtf, mtf_change = signal_mtf_momentum(higher_tf_closes, prior_regime, cfg)

    # Count votes
    cont_score = sum(1 for s in [sig_vol, sig_test, sig_width, sig_dur, sig_mtf] if s == "cont")
    rev_score = sum(1 for s in [sig_vol, sig_test, sig_width, sig_dur, sig_mtf] if s == "rev")

    # Determine bias
    if cont_score >= cfg.score_continuation_min and cont_score > rev_score:
        bias = SidewaysBias.CONTINUATION
        confidence = cont_score / 5.0
        reason = f"cont_score={cont_score}, rev_score={rev_score}"
    elif rev_score >= cfg.score_reversal_min and rev_score > cont_score:
        bias = SidewaysBias.REVERSAL
        confidence = rev_score / 5.0
        reason = f"rev_score={rev_score}, cont_score={cont_score}"
    else:
        bias = SidewaysBias.AMBIGUOUS
        confidence = max(cont_score, rev_score) / 5.0
        reason = f"tied or below threshold (cont={cont_score}, rev={rev_score})"

    return SidewaysAnalysis(
        bias=bias,
        confidence=confidence,
        continuation_score=cont_score,
        reversal_score=rev_score,
        signal_volume=sig_vol,
        signal_test_count=sig_test,
        signal_range_width=sig_width,
        signal_duration=sig_dur,
        signal_mtf=sig_mtf,
        volume_change_pct=vol_change,
        test_count_total=test_count,
        range_width_pct=width,
        duration_candles=end_idx - start_idx,
        reason=reason,
    )


# ═════════════════════════════════════════════════════════════
# HELPER: Detect prior regime dari regime series
# ═════════════════════════════════════════════════════════════

def get_prior_regime(
    regime_states: list[RegimeState],
    sideways_start_idx: int,
    lookback: int = 30,
) -> Regime:
    """
    Cari regime dominant SEBELUM sideways start.

    Returns: BULL_MARKUP, BEAR_MARKDOWN, or UNKNOWN
    """
    start = max(0, sideways_start_idx - lookback)
    end = sideways_start_idx

    if end <= start:
        return Regime.UNKNOWN

    counts = {Regime.BULL_MARKUP: 0, Regime.BEAR_MARKDOWN: 0}
    for i in range(start, end):
        r = regime_states[i].regime
        if r in counts:
            counts[r] += 1

    if counts[Regime.BULL_MARKUP] > counts[Regime.BEAR_MARKDOWN]:
        return Regime.BULL_MARKUP
    elif counts[Regime.BEAR_MARKDOWN] > counts[Regime.BULL_MARKUP]:
        return Regime.BEAR_MARKDOWN
    else:
        return Regime.UNKNOWN


# ═════════════════════════════════════════════════════════════
# ENTRY BIAS RESOLVER (integrasi dengan state machine)
# ═════════════════════════════════════════════════════════════

def resolve_entry_bias(
    analysis: SidewaysAnalysis,
    prior_regime: Regime,
    proposed_side: str,  # "long" or "short"
) -> tuple[bool, float]:
    """
    Decide apakah proposed entry side aligned dengan bias, dan return size multiplier.

    Rules:
    - Continuation + prior bull:  LONG = full size, SHORT = skip
    - Continuation + prior bear:  SHORT = full size, LONG = skip
    - Reversal + prior bull:      SHORT = full size (distribution → bear), LONG = 0.5x
    - Reversal + prior bear:      LONG = full size (accumulation → bull), SHORT = 0.5x
    - Ambiguous:                  both sides = 0.5x size

    Returns:
        (allowed: bool, size_multiplier: float)
    """
    if analysis.bias == SidewaysBias.CONTINUATION:
        if prior_regime == Regime.BULL_MARKUP:
            if proposed_side == "long":
                return (True, 1.0)
            else:
                return (False, 0.0)
        elif prior_regime == Regime.BEAR_MARKDOWN:
            if proposed_side == "short":
                return (True, 1.0)
            else:
                return (False, 0.0)

    elif analysis.bias == SidewaysBias.REVERSAL:
        if prior_regime == Regime.BULL_MARKUP:
            if proposed_side == "short":
                return (True, 1.0)  # Reversal from bull → bear
            else:
                return (True, 0.5)  # Small counter
        elif prior_regime == Regime.BEAR_MARKDOWN:
            if proposed_side == "long":
                return (True, 1.0)  # Reversal from bear → bull
            else:
                return (True, 0.5)

    # AMBIGUOUS or unknown → both sides small
    return (True, 0.5)


# ═════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════

__all__ = [
    "SidewaysBias",
    "ClassifierConfig",
    "SidewaysAnalysis",
    "signal_volume_trend",
    "signal_test_count",
    "signal_range_width",
    "signal_duration",
    "signal_mtf_momentum",
    "analyze_sideways",
    "get_prior_regime",
    "resolve_entry_bias",
]
