"""
transition.py — Layer 2: Continuation vs Reversal Classifier
==============================================================
Untuk sideways periods, classify apakah ini pause (continuation) atau
regime change (reversal). 5-signal scoring.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .indicators import slope_pct, rolling_volume_distribution
from .regime import Regime, RegimeState


class Transition(Enum):
    CONTINUATION = "continuation"
    REVERSAL = "reversal"
    AMBIGUOUS = "ambiguous"


@dataclass
class TransitionConfig:
    volume_trend_threshold: float = 0.15
    test_count_lookback: int = 30
    test_count_tolerance: float = 0.003
    range_width_cont_max: float = 0.02
    range_width_rev_min: float = 0.03
    duration_cont_max: int = 15
    duration_rev_min: int = 20
    mtf_momentum_weakening: float = 0.02
    min_score: int = 3


@dataclass
class TransitionState:
    transition: Transition
    confidence: float
    continuation_score: int = 0
    reversal_score: int = 0
    reason: str = ""


def classify_transitions(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: TransitionConfig,
) -> list[TransitionState]:
    """Classify transition per bar for range periods."""
    n = len(closes)
    up_vol, down_vol = rolling_volume_distribution(closes, volumes, 20)
    results: list[TransitionState] = []

    range_start = -1
    for i in range(n):
        rs = regime_states[i]

        # Only classify when in range regime
        if rs.regime not in (Regime.ACCUMULATION, Regime.DISTRIBUTION):
            range_start = -1
            results.append(TransitionState(Transition.AMBIGUOUS, 0.0, reason="not_range"))
            continue

        if range_start < 0:
            range_start = i

        duration = i - range_start + 1

        # ─── 5 Signals ───

        # 1. Volume trend (up 15% during sideways → reversal signal)
        if duration >= 4:
            half = duration // 2
            v1 = float(np.mean(volumes[i - duration + 1: i - half + 1]))
            v2 = float(np.mean(volumes[i - half + 1: i + 1]))
            vol_change = (v2 - v1) / v1 if v1 > 0 else 0.0
        else:
            vol_change = 0.0

        sig_vol_rev = vol_change > cfg.volume_trend_threshold
        sig_vol_cont = vol_change < -cfg.volume_trend_threshold

        # 2. Range width
        width = rs.range_width_pct
        sig_width_cont = width < cfg.range_width_cont_max
        sig_width_rev = width > cfg.range_width_rev_min

        # 3. Duration
        sig_dur_cont = duration <= cfg.duration_cont_max
        sig_dur_rev = duration >= cfg.duration_rev_min

        # 4. Test count (how many times price touch VAH/VAL)
        vah = rs.vah
        val = rs.val
        test_count = 0
        for j in range(max(range_start, i - cfg.test_count_lookback), i + 1):
            if highs[j] >= vah * (1 - cfg.test_count_tolerance):
                test_count += 1
            if lows[j] <= val * (1 + cfg.test_count_tolerance):
                test_count += 1
        sig_test_cont = test_count <= 3
        sig_test_rev = test_count >= 6

        # 5. MTF momentum (proxy: EMA slope)
        ema_slope = rs.ema_fast_slope
        if rs.prior_regime == Regime.BULL_MARKUP:
            sig_mtf_cont = ema_slope > -cfg.mtf_momentum_weakening
            sig_mtf_rev = ema_slope < -cfg.mtf_momentum_weakening
        elif rs.prior_regime == Regime.BEAR_MARKDOWN:
            sig_mtf_cont = ema_slope < cfg.mtf_momentum_weakening
            sig_mtf_rev = ema_slope > cfg.mtf_momentum_weakening
        else:
            sig_mtf_cont = False
            sig_mtf_rev = False

        cont_score = sum([sig_vol_cont, sig_width_cont, sig_dur_cont, sig_test_cont, sig_mtf_cont])
        rev_score = sum([sig_vol_rev, sig_width_rev, sig_dur_rev, sig_test_rev, sig_mtf_rev])

        if cont_score >= cfg.min_score and cont_score > rev_score:
            transition = Transition.CONTINUATION
            confidence = cont_score / 5.0
            reason = f"cont_{cont_score}"
        elif rev_score >= cfg.min_score and rev_score > cont_score:
            transition = Transition.REVERSAL
            confidence = rev_score / 5.0
            reason = f"rev_{rev_score}"
        else:
            transition = Transition.AMBIGUOUS
            confidence = max(cont_score, rev_score) / 5.0
            reason = f"amb_c{cont_score}_r{rev_score}"

        results.append(TransitionState(
            transition=transition,
            confidence=confidence,
            continuation_score=cont_score,
            reversal_score=rev_score,
            reason=reason,
        ))

    return results


__all__ = ["Transition", "TransitionConfig", "TransitionState", "classify_transitions"]
