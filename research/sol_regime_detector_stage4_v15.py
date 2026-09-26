"""SOL Regime Detector Stage 4 V1.5 — adaptive BULL research candidate.

Frozen after DEV-only Stage 4 refinement on 2023-2024.
Do not retune on 2025 or 2026.

Research only. Input must be completed 1H candles.

BULL:
- >=2 of rv8 / rv24 / ATR14% are >= their causal rolling-720H 85th percentile
- distHigh8 is <= its causal rolling-720H 25th percentile

BEAR and SIDEWAYS remain the frozen Stage 3 V1 rules.
Bull/Bear conflict => TRANSITION.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sol_regime_detector_stage3_v1 import TH as V1_TH
from sol_regime_detector_stage3_v1 import features_1h


@dataclass(frozen=True)
class AdaptiveBullThresholds:
    lookback_hours: int = 720
    vol_percentile: float = 0.85
    vol_votes: int = 2
    dist_high8_percentile_max: float = 0.25


CFG = AdaptiveBullThresholds()


def _percentile_rank(history, value):
    """Causal empirical percentile using historical observations only."""
    if not history:
        raise ValueError("empty percentile history")
    return sum(x <= value for x in history) / len(history)


def features_with_percentiles(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    i: int,
):
    """Return current 1H features plus rolling-720H causal percentiles.

    A full 720 completed-hour feature history is required. Each historical
    feature itself needs 24 candles, so i must be >= 744.
    """
    if i < 24 + CFG.lookback_hours:
        raise ValueError("Need at least 744 completed 1H candles for Stage 4 V1.5")

    current = features_1h(high, low, close, i)
    keys = ("rv8", "rv24", "atr14_pct", "dist_high8")
    hist = {k: [] for k in keys}

    for j in range(i - CFG.lookback_hours, i):
        f = features_1h(high, low, close, j)
        for k in keys:
            hist[k].append(f[k])

    pct = {k: _percentile_rank(hist[k], current[k]) for k in keys}
    return current, pct


def classify_from_features(f, p):
    vol_votes = sum(
        (
            p["rv8"] >= CFG.vol_percentile,
            p["rv24"] >= CFG.vol_percentile,
            p["atr14_pct"] >= CFG.vol_percentile,
        )
    )

    bull = (
        vol_votes >= CFG.vol_votes
        and p["dist_high8"] <= CFG.dist_high8_percentile_max
    )

    # Frozen Stage 3 V1 BEAR head.
    bear = (
        f["accel4v12"] >= V1_TH.accel4v12_high
        and f["close_loc"] >= V1_TH.close_loc_high
    )

    if bull and not bear:
        return "BULL"
    if bear and not bull:
        return "BEAR"

    # Frozen Stage 3 V1 non-directional head.
    if f["rv8"] < V1_TH.rv8_low and f["atr14_pct"] < V1_TH.atr14_low:
        return "SIDEWAYS"

    return "TRANSITION"


def classify_1h(high, low, close, i):
    f, p = features_with_percentiles(high, low, close, i)
    return classify_from_features(f, p)
