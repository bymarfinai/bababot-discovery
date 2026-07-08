"""
Indicators — EMA20 and Value Area (VAH/VAL/POC).
Per spec §2.5 (EMA position) and §3.0 (VA formula, v0.19 percentile-based).
"""
import numpy as np


def compute_ema_series(closes: np.ndarray, period: int) -> np.ndarray:
    """
    Standard EMA. Seeded with first close.
    Spec §2 — EMA20 real-time value per candle close.
    """
    alpha = 2.0 / (period + 1.0)
    ema = np.zeros(len(closes))
    ema[0] = closes[0]
    for i in range(1, len(closes)):
        ema[i] = closes[i] * alpha + ema[i - 1] * (1.0 - alpha)
    return ema


def compute_va_at_bar(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    bar_idx: int,
    window: int,
    p_high: float,
    p_low: float,
):
    """
    VA computation at bar_idx using past `window` bars (EXCLUDE current bar).
    Spec §3.0 v0.19:
      typical[j] = (h+l+c)/3
      POC = Sigma(typical * volume) / Sigma volume  (volume-weighted)
      VAH = percentile P85 of highs
      VAL = percentile P15 of lows

    Returns (vah, val, poc) or (None, None, None) if insufficient data.
    """
    start = bar_idx - window
    end = bar_idx  # exclusive -> excludes current bar
    if start < 0:
        return None, None, None

    win_h = highs[start:end]
    win_l = lows[start:end]
    win_c = closes[start:end]
    win_v = volumes[start:end]

    typical = (win_h + win_l + win_c) / 3.0
    total_vol = float(np.sum(win_v))
    if total_vol > 0:
        poc = float(np.sum(typical * win_v) / total_vol)
    else:
        poc = float(np.mean(typical))

    vah = float(np.percentile(win_h, p_high))
    val = float(np.percentile(win_l, p_low))
    return vah, val, poc
