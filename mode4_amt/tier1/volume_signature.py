"""
volume_signature.py — Volume Anomaly Detection (Tier 1 supporting)
====================================================================
Design Doc reference: §3.7, §7.2.2 (volume component).

Volume signature membedakan:
    SWEEP:     Volume spike TAJAM di 1 candle, tapi ga sustained.
               Volume total tinggi (SL grab), tapi setelah candle sweep,
               volume kembali normal.

    BREAKOUT:  Volume elevated dan SUSTAINED selama beberapa candle.
               Institutional accumulation → distribution pattern.

    NORMAL:    Volume within normal range (0.7× - 1.3× avg).

Metrics:
    - spike_ratio = this_vol / rolling_avg(N)
    - sustain_ratio = avg_vol_last_M / rolling_avg(N)
    - relative_dominance = this_vol / max(volumes[i-K:i])  (relative to recent peaks)

Used internally by sweep_detector dan breakout_classifier untuk komponen
volume dalam scoring.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class VolumeProfile:
    """Volume signature at a specific candle."""
    idx: int
    volume: float
    rolling_avg_short: float     # 5-period avg
    rolling_avg_long: float      # 20-period avg
    spike_ratio: float           # volume / rolling_avg_long
    sustain_ratio: float         # avg last 3 / rolling_avg_long
    relative_dominance: float    # volume / max(last 10)

    is_spike: bool = False       # spike_ratio >= K_spike (default 1.8)
    is_sustained: bool = False   # sustain_ratio >= K_sustain (default 1.3)
    is_dominant: bool = False    # relative_dominance >= K_dom (default 0.85)

    def __repr__(self):
        flags = []
        if self.is_spike: flags.append("SPIKE")
        if self.is_sustained: flags.append("SUSTAIN")
        if self.is_dominant: flags.append("DOM")
        return (f"VolumeProfile(@{self.idx} spike={self.spike_ratio:.2f} "
                f"sustain={self.sustain_ratio:.2f} [{','.join(flags) or 'NORMAL'}])")


def compute_volume_signature(
    volumes: np.ndarray,
    idx: int,
    avg_period_short: int = 5,
    avg_period_long: int = 20,
    sustain_window: int = 3,
    dominance_window: int = 10,
    k_spike: float = 1.8,
    k_sustain: float = 1.3,
    k_dominance: float = 0.85,
) -> Optional[VolumeProfile]:
    """
    Compute volume signature at candle `idx`.

    Args:
        volumes: OHLCV volume array
        idx: target candle idx
        avg_period_short/long: rolling avg windows
        sustain_window: number of recent candles (including idx) for sustain calc
        dominance_window: window untuk relative dominance

    Returns None if insufficient history.
    """
    n = len(volumes)
    if idx < avg_period_long or idx >= n:
        return None

    volumes = np.asarray(volumes, dtype=np.float64)
    v = float(volumes[idx])

    # Rolling avgs BEFORE current candle to avoid self-contamination
    short_start = max(0, idx - avg_period_short)
    long_start = max(0, idx - avg_period_long)
    avg_short = float(np.mean(volumes[short_start:idx])) if idx > short_start else v
    avg_long = float(np.mean(volumes[long_start:idx])) if idx > long_start else v

    spike = v / max(avg_long, 1e-9)

    sustain_start = max(0, idx - sustain_window + 1)
    sustain_avg = float(np.mean(volumes[sustain_start: idx + 1]))
    sustain_ratio = sustain_avg / max(avg_long, 1e-9)

    dom_start = max(0, idx - dominance_window)
    recent_max = float(np.max(volumes[dom_start: idx])) if idx > dom_start else v
    relative_dom = v / max(recent_max, 1e-9)

    return VolumeProfile(
        idx=idx,
        volume=v,
        rolling_avg_short=avg_short,
        rolling_avg_long=avg_long,
        spike_ratio=float(spike),
        sustain_ratio=float(sustain_ratio),
        relative_dominance=float(relative_dom),
        is_spike=(spike >= k_spike),
        is_sustained=(sustain_ratio >= k_sustain),
        is_dominant=(relative_dom >= k_dominance),
    )


def is_volume_spike(volumes: np.ndarray, idx: int,
                    avg_period: int = 20, k: float = 1.8) -> bool:
    """Quick check: is candle `idx` a volume spike relative to `avg_period` avg?"""
    if idx < avg_period or idx >= len(volumes):
        return False
    start = max(0, idx - avg_period)
    avg = float(np.mean(volumes[start:idx])) if idx > start else 1.0
    if avg <= 0:
        return False
    return (volumes[idx] / avg) >= k


__all__ = ["VolumeProfile", "compute_volume_signature", "is_volume_spike"]
