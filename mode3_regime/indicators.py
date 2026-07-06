"""
indicators.py — Technical indicators untuk regime detection
=============================================================
EMA, ATR, VWAP, rolling stats, volume distribution.
Numpy-based (no external TA library).
"""

from __future__ import annotations
import numpy as np


def ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    n = len(series)
    result = np.zeros(n)
    if n == 0:
        return result
    alpha = 2.0 / (period + 1)
    result[0] = series[0]
    for i in range(1, n):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def sma(series: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    n = len(series)
    result = np.zeros(n)
    if n < period:
        return result
    csum = np.cumsum(series)
    result[period - 1] = csum[period - 1] / period
    result[period:] = (csum[period:] - csum[:-period]) / period
    # Fill warmup with first valid value
    result[:period - 1] = result[period - 1]
    return result


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(closes)
    if n < 2:
        return np.zeros(n)

    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    result = np.zeros(n)
    if n < period:
        return result
    result[period - 1] = tr[:period].mean()
    for i in range(period, n):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def rolling_vwap(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Rolling VWAP + upper/lower sigma bands.

    Returns (vwap, upper_1sigma, lower_1sigma).
    """
    n = len(closes)
    typical = (highs + lows + closes) / 3

    vwap = np.zeros(n)
    upper = np.zeros(n)
    lower = np.zeros(n)

    for i in range(n):
        start = max(0, i - window + 1)
        tp_slice = typical[start:i + 1]
        vol_slice = volumes[start:i + 1]
        vol_sum = vol_slice.sum()
        if vol_sum <= 0:
            vwap[i] = closes[i]
            upper[i] = closes[i]
            lower[i] = closes[i]
            continue
        vwap[i] = float(np.sum(tp_slice * vol_slice) / vol_sum)
        var = float(np.sum(((tp_slice - vwap[i]) ** 2) * vol_slice) / vol_sum)
        sigma = np.sqrt(var)
        upper[i] = vwap[i] + sigma
        lower[i] = vwap[i] - sigma

    return vwap, upper, lower


def rolling_high_low(
    highs: np.ndarray, lows: np.ndarray, window: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Rolling high and low over window."""
    n = len(highs)
    result_high = np.zeros(n)
    result_low = np.zeros(n)
    for i in range(n):
        start = max(0, i - window + 1)
        result_high[i] = float(np.max(highs[start:i + 1]))
        result_low[i] = float(np.min(lows[start:i + 1]))
    return result_high, result_low


def consecutive_count(condition: np.ndarray) -> np.ndarray:
    """
    Untuk boolean array, return count of consecutive True ending at each index.
    Example: [T, T, F, T, T, T] -> [1, 2, 0, 1, 2, 3]
    """
    n = len(condition)
    result = np.zeros(n, dtype=int)
    count = 0
    for i in range(n):
        if condition[i]:
            count += 1
        else:
            count = 0
        result[i] = count
    return result


def slope_pct(series: np.ndarray, lookback: int) -> np.ndarray:
    """
    % change dari `lookback` bar yang lalu ke sekarang.
    Return (current - past) / past.
    """
    n = len(series)
    result = np.zeros(n)
    for i in range(n):
        past_idx = i - lookback
        if past_idx < 0 or series[past_idx] <= 0:
            continue
        result[i] = (series[i] - series[past_idx]) / series[past_idx]
    return result


def rolling_volume_distribution(
    closes: np.ndarray, volumes: np.ndarray, window: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Rolling sum of volume di up-candle vs down-candle over window.

    Returns (up_volume_sum, down_volume_sum) per bar.
    """
    n = len(closes)
    is_up = np.zeros(n)
    is_down = np.zeros(n)
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            is_up[i] = 1
        elif closes[i] < closes[i - 1]:
            is_down[i] = 1

    up_vol = is_up * volumes
    down_vol = is_down * volumes

    up_sum = np.zeros(n)
    down_sum = np.zeros(n)
    for i in range(n):
        start = max(0, i - window + 1)
        up_sum[i] = up_vol[start:i + 1].sum()
        down_sum[i] = down_vol[start:i + 1].sum()

    return up_sum, down_sum


__all__ = [
    "ema", "sma", "atr",
    "rolling_vwap", "rolling_high_low",
    "consecutive_count", "slope_pct",
    "rolling_volume_distribution",
]
