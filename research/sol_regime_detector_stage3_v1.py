"""SOL Regime Detector Stage 3 V1 — hierarchical causal baseline.

Frozen from DEV 2023-2024.
Do not retune on 2025 or 2026.

Output states:
- BULL
- BEAR
- SIDEWAYS
- TRANSITION

This module is research-only. It expects completed 1H candles.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class DetectorThresholds:
    rv24_high: float = 1.1633509828632893
    atr14_high: float = 1.8851167596025002
    dist_high8_low: float = -2.9087400396089276
    accel4v12_high: float = 1.101215540095295
    close_loc_high: float = 0.6260779194779318
    rv8_low: float = 0.47186330933162923
    atr14_low: float = 0.9798115352248504

TH = DetectorThresholds()

def _mean(xs):
    return sum(xs) / len(xs)

def _sd(xs):
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

def _ret(close, i, h):
    return 100.0 * (close[i] / close[i-h] - 1.0)

def _tr(high, low, close, i):
    if i == 0:
        return high[i] - low[i]
    return max(
        high[i] - low[i],
        abs(high[i] - close[i-1]),
        abs(low[i] - close[i-1]),
    )

def features_1h(high: Sequence[float], low: Sequence[float], close: Sequence[float], i: int):
    if i < 24:
        raise ValueError("Need at least 24 completed historical 1H candles")

    tr14 = [_tr(high, low, close, j) for j in range(i-13, i+1)]
    atr14_pct = 100.0 * _mean(tr14) / close[i]

    lr8 = [math.log(close[j] / close[j-1]) for j in range(i-7, i+1)]
    lr24 = [math.log(close[j] / close[j-1]) for j in range(i-23, i+1)]
    rv8 = 100.0 * _sd(lr8)
    rv24 = 100.0 * _sd(lr24)

    hi8 = max(high[i-7:i+1])
    lo8 = min(low[i-7:i+1])
    dist_high8 = 100.0 * (close[i] / hi8 - 1.0)
    dist_low8 = 100.0 * (close[i] / lo8 - 1.0)

    ret4 = _ret(close, i, 4)
    accel4v12 = ret4 - _ret(close, i, 12) / 3.0
    close_loc = 2.0 * (close[i] - low[i]) / (high[i] - low[i] + 1e-12) - 1.0

    return {
        "rv8": rv8,
        "rv24": rv24,
        "atr14_pct": atr14_pct,
        "dist_high8": dist_high8,
        "dist_low8": dist_low8,
        "ret4": ret4,
        "accel4v12": accel4v12,
        "close_loc": close_loc,
    }

def classify_from_features(f):
    # Stage 3 V1-BALANCED, frozen before VAL/OOS.
    bull = (
        f["rv24"] > TH.rv24_high
        and f["atr14_pct"] > TH.atr14_high
        and f["dist_high8"] <= TH.dist_high8_low
    )

    bear = (
        f["accel4v12"] >= TH.accel4v12_high
        and f["close_loc"] >= TH.close_loc_high
    )

    # Conflicting directional evidence is explicitly rejected.
    if bull and not bear:
        return "BULL"
    if bear and not bull:
        return "BEAR"

    # Conservative non-directional head.
    if f["rv8"] < TH.rv8_low and f["atr14_pct"] < TH.atr14_low:
        return "SIDEWAYS"

    return "TRANSITION"

def classify_1h(high, low, close, i):
    return classify_from_features(features_1h(high, low, close, i))
