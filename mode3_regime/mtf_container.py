"""
mtf_container.py — Multi-Timeframe Container Detector
=======================================================
Definisi sideways dari trader:
- Container = range (high/low) dari N candle CLOSED di TF besar
- Trading TF = 1h
- Container TFs = 4h, 1D (aggregated dari 4h), 1W (aggregated dari 4h)
- 1h candle inside container N = sideways confirmed at TF N
- 1h candle beyond container = breakout/breakdown

Aggregation on-the-fly dari 4h data (no separate fetch).
Container hanya dari candle CLOSED (previous complete), tidak include current.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional


def _aggregate_ohlcv(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    timestamps_ms: np.ndarray,
    factor: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Aggregate OHLCV dari lower TF ke higher TF.
    factor = berapa candle lower TF = 1 candle higher TF.
    - 4h to 1D: factor = 6
    - 4h to 1W: factor = 42
    - 1h to 4h: factor = 4

    Returns aggregated (opens, highs, lows, closes, volumes, start_timestamps_ms)
    """
    n = len(closes)
    n_agg = n // factor

    if n_agg == 0:
        return (np.array([]), np.array([]), np.array([]), np.array([]),
                np.array([]), np.array([]))

    agg_opens = np.zeros(n_agg)
    agg_highs = np.zeros(n_agg)
    agg_lows = np.zeros(n_agg)
    agg_closes = np.zeros(n_agg)
    agg_volumes = np.zeros(n_agg)
    agg_ts = np.zeros(n_agg, dtype=np.int64)

    for i in range(n_agg):
        start = i * factor
        end = start + factor
        agg_opens[i] = opens[start]
        agg_highs[i] = float(np.max(highs[start:end]))
        agg_lows[i] = float(np.min(lows[start:end]))
        agg_closes[i] = closes[end - 1]
        agg_volumes[i] = float(np.sum(volumes[start:end]))
        agg_ts[i] = timestamps_ms[start]

    return agg_opens, agg_highs, agg_lows, agg_closes, agg_volumes, agg_ts


@dataclass
class ContainerStats:
    """Statistik distribusi container inside/breakout untuk validasi."""
    total_1h_candles: int = 0

    inside_4h_count: int = 0
    inside_1d_count: int = 0
    inside_1w_count: int = 0

    inside_4h_pct: float = 0.0
    inside_1d_pct: float = 0.0
    inside_1w_pct: float = 0.0

    break_up_4h: int = 0
    break_up_1d: int = 0
    break_up_1w: int = 0

    break_down_4h: int = 0
    break_down_1d: int = 0
    break_down_1w: int = 0

    break_4h_pct: float = 0.0
    break_1d_pct: float = 0.0
    break_1w_pct: float = 0.0

    break_1d_also_break_4h_pct: float = 0.0
    break_1w_also_break_1d_pct: float = 0.0

    confidence_3_of_3: int = 0
    confidence_2_of_3: int = 0
    confidence_1_of_3: int = 0
    confidence_0_of_3: int = 0

    conf_3_of_3_pct: float = 0.0
    conf_2_of_3_pct: float = 0.0
    conf_1_of_3_pct: float = 0.0
    conf_0_of_3_pct: float = 0.0


@dataclass
class MTFClassification:
    """Per-1h-candle classification hasil."""
    idx: int
    timestamp_ms: int
    close: float

    range_4h_high: Optional[float] = None
    range_4h_low: Optional[float] = None
    range_1d_high: Optional[float] = None
    range_1d_low: Optional[float] = None
    range_1w_high: Optional[float] = None
    range_1w_low: Optional[float] = None

    inside_4h: bool = False
    inside_1d: bool = False
    inside_1w: bool = False
    break_up_4h: bool = False
    break_up_1d: bool = False
    break_up_1w: bool = False
    break_down_4h: bool = False
    break_down_1d: bool = False
    break_down_1w: bool = False

    inside_confidence: int = 0

    pos_in_4h: Optional[float] = None
    pos_in_1d: Optional[float] = None
    pos_in_1w: Optional[float] = None


def classify_mtf(
    opens_1h: np.ndarray,
    highs_1h: np.ndarray,
    lows_1h: np.ndarray,
    closes_1h: np.ndarray,
    volumes_1h: np.ndarray,
    timestamps_ms_1h: np.ndarray,
    opens_4h: np.ndarray,
    highs_4h: np.ndarray,
    lows_4h: np.ndarray,
    closes_4h: np.ndarray,
    volumes_4h: np.ndarray,
    timestamps_ms_4h: np.ndarray,
    n_candles_per_layer: int = 1,
) -> tuple[list[MTFClassification], ContainerStats]:
    """
    Classify setiap 1h candle terhadap MTF containers.
    """
    op_1d, hi_1d, lo_1d, cl_1d, vo_1d, ts_1d = _aggregate_ohlcv(
        opens_4h, highs_4h, lows_4h, closes_4h, volumes_4h, timestamps_ms_4h, factor=6,
    )
    op_1w, hi_1w, lo_1w, cl_1w, vo_1w, ts_1w = _aggregate_ohlcv(
        opens_4h, highs_4h, lows_4h, closes_4h, volumes_4h, timestamps_ms_4h, factor=42,
    )

    n_1h = len(closes_1h)

    hour_ms = 3600 * 1000
    close_time_4h = timestamps_ms_4h + 4 * hour_ms
    close_time_1d = ts_1d + 24 * hour_ms
    close_time_1w = ts_1w + 7 * 24 * hour_ms

    classifications: list[MTFClassification] = []

    idx_last_4h_closed = np.searchsorted(close_time_4h, timestamps_ms_1h, side='right') - 1
    idx_last_1d_closed = np.searchsorted(close_time_1d, timestamps_ms_1h, side='right') - 1
    idx_last_1w_closed = np.searchsorted(close_time_1w, timestamps_ms_1h, side='right') - 1

    stats = ContainerStats()
    stats.total_1h_candles = 0

    for i in range(n_1h):
        close_1h_i = float(closes_1h[i])
        idx_4h = int(idx_last_4h_closed[i])
        idx_1d = int(idx_last_1d_closed[i])
        idx_1w = int(idx_last_1w_closed[i])

        cls = MTFClassification(
            idx=i,
            timestamp_ms=int(timestamps_ms_1h[i]),
            close=close_1h_i,
        )

        if idx_4h < n_candles_per_layer - 1:
            classifications.append(cls)
            continue
        if idx_1d < n_candles_per_layer - 1:
            classifications.append(cls)
            continue
        if idx_1w < n_candles_per_layer - 1:
            classifications.append(cls)
            continue

        r4h_hi = float(np.max(highs_4h[idx_4h - n_candles_per_layer + 1: idx_4h + 1]))
        r4h_lo = float(np.min(lows_4h[idx_4h - n_candles_per_layer + 1: idx_4h + 1]))
        r1d_hi = float(np.max(hi_1d[idx_1d - n_candles_per_layer + 1: idx_1d + 1]))
        r1d_lo = float(np.min(lo_1d[idx_1d - n_candles_per_layer + 1: idx_1d + 1]))
        r1w_hi = float(np.max(hi_1w[idx_1w - n_candles_per_layer + 1: idx_1w + 1]))
        r1w_lo = float(np.min(lo_1w[idx_1w - n_candles_per_layer + 1: idx_1w + 1]))

        cls.range_4h_high = r4h_hi
        cls.range_4h_low = r4h_lo
        cls.range_1d_high = r1d_hi
        cls.range_1d_low = r1d_lo
        cls.range_1w_high = r1w_hi
        cls.range_1w_low = r1w_lo

        cls.pos_in_4h = (close_1h_i - r4h_lo) / (r4h_hi - r4h_lo) if r4h_hi > r4h_lo else 0.5
        cls.pos_in_1d = (close_1h_i - r1d_lo) / (r1d_hi - r1d_lo) if r1d_hi > r1d_lo else 0.5
        cls.pos_in_1w = (close_1h_i - r1w_lo) / (r1w_hi - r1w_lo) if r1w_hi > r1w_lo else 0.5

        cls.inside_4h = r4h_lo <= close_1h_i <= r4h_hi
        cls.inside_1d = r1d_lo <= close_1h_i <= r1d_hi
        cls.inside_1w = r1w_lo <= close_1h_i <= r1w_hi
        cls.break_up_4h = close_1h_i > r4h_hi
        cls.break_up_1d = close_1h_i > r1d_hi
        cls.break_up_1w = close_1h_i > r1w_hi
        cls.break_down_4h = close_1h_i < r4h_lo
        cls.break_down_1d = close_1h_i < r1d_lo
        cls.break_down_1w = close_1h_i < r1w_lo

        cls.inside_confidence = (int(cls.inside_4h) + int(cls.inside_1d) + int(cls.inside_1w))

        classifications.append(cls)

        stats.total_1h_candles += 1
        stats.inside_4h_count += int(cls.inside_4h)
        stats.inside_1d_count += int(cls.inside_1d)
        stats.inside_1w_count += int(cls.inside_1w)
        stats.break_up_4h += int(cls.break_up_4h)
        stats.break_up_1d += int(cls.break_up_1d)
        stats.break_up_1w += int(cls.break_up_1w)
        stats.break_down_4h += int(cls.break_down_4h)
        stats.break_down_1d += int(cls.break_down_1d)
        stats.break_down_1w += int(cls.break_down_1w)

        if cls.inside_confidence == 3:
            stats.confidence_3_of_3 += 1
        elif cls.inside_confidence == 2:
            stats.confidence_2_of_3 += 1
        elif cls.inside_confidence == 1:
            stats.confidence_1_of_3 += 1
        else:
            stats.confidence_0_of_3 += 1

    tc = max(stats.total_1h_candles, 1)
    stats.inside_4h_pct = round(stats.inside_4h_count / tc, 4)
    stats.inside_1d_pct = round(stats.inside_1d_count / tc, 4)
    stats.inside_1w_pct = round(stats.inside_1w_count / tc, 4)

    break_4h_total = stats.break_up_4h + stats.break_down_4h
    break_1d_total = stats.break_up_1d + stats.break_down_1d
    break_1w_total = stats.break_up_1w + stats.break_down_1w
    stats.break_4h_pct = round(break_4h_total / tc, 4)
    stats.break_1d_pct = round(break_1d_total / tc, 4)
    stats.break_1w_pct = round(break_1w_total / tc, 4)

    n_break_1d_and_4h = 0
    n_break_1w_and_1d = 0
    for c in classifications:
        break_1d_any = c.break_up_1d or c.break_down_1d
        break_4h_any = c.break_up_4h or c.break_down_4h
        break_1w_any = c.break_up_1w or c.break_down_1w
        if break_1d_any and break_4h_any:
            n_break_1d_and_4h += 1
        if break_1w_any and break_1d_any:
            n_break_1w_and_1d += 1

    stats.break_1d_also_break_4h_pct = round(n_break_1d_and_4h / max(break_1d_total, 1), 4)
    stats.break_1w_also_break_1d_pct = round(n_break_1w_and_1d / max(break_1w_total, 1), 4)

    stats.conf_3_of_3_pct = round(stats.confidence_3_of_3 / tc, 4)
    stats.conf_2_of_3_pct = round(stats.confidence_2_of_3 / tc, 4)
    stats.conf_1_of_3_pct = round(stats.confidence_1_of_3 / tc, 4)
    stats.conf_0_of_3_pct = round(stats.confidence_0_of_3 / tc, 4)

    return classifications, stats


__all__ = ["ContainerStats", "MTFClassification", "classify_mtf"]
