#!/usr/bin/env python3
"""Performance-only wrapper for preregistered G0.

This replaces repeated full-frame boolean masks with DatetimeIndex `.loc` slices.
It does NOT change the G0 sample universe, labels, features, thresholds, gates, or
outputs. Research only; live BBC untouched.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import g0_global_pooled_regime_dataset as g0


def window(k: pd.DataFrame, start: pd.Timestamp, end_exclusive: pd.Timestamp) -> pd.DataFrame:
    return k.loc[start:end_exclusive - g0.STEP]


def feature_row_fast(k: pd.DataFrame, t: pd.Timestamp):
    pre_t = t - g0.STEP
    required_oldest = t - pd.Timedelta(hours=24) - g0.STEP
    if required_oldest not in k.index or pre_t not in k.index:
        return None, "missing_preentry_anchor"

    x24 = window(k, t - pd.Timedelta(hours=24), t)
    if not g0.is_contiguous(x24, t - pd.Timedelta(hours=24), 24 * 12):
        return None, "noncontiguous_preentry_24h"

    pre = k.loc[pre_t]
    last_close = float(pre.close)
    rets = {}
    for h in [1, 3, 6, 12, 24]:
        anchor_t = t - pd.Timedelta(hours=h) - g0.STEP
        if anchor_t not in k.index:
            rets[f"ret{h}h"] = np.nan
        else:
            anchor = float(k.loc[anchor_t, "close"])
            rets[f"ret{h}h"] = last_close / anchor - 1.0 if np.isfinite(anchor) and anchor > 0 else np.nan

    e20_prev_t = t - pd.Timedelta(hours=1) - g0.STEP
    e20_prev = float(k.loc[e20_prev_t, "ema20"]) if e20_prev_t in k.index else np.nan
    ema20_slope1h = float(pre.ema20) / e20_prev - 1.0 if np.isfinite(e20_prev) and e20_prev > 0 else np.nan

    lo24 = float(x24.low.min())
    hi24 = float(x24.high.max())
    loc24 = (last_close - lo24) / (hi24 - lo24) if hi24 > lo24 else 0.5

    x6 = window(k, t - pd.Timedelta(hours=6), t)
    x4 = window(k, t - pd.Timedelta(hours=4), t)
    x1 = window(k, t - pd.Timedelta(hours=1), t)
    r6 = g0.range_pct(x6)
    r24 = g0.range_pct(x24)

    rv1 = float(k.loc[x1.index, "logret5"].std(ddof=1))
    rv6 = float(k.loc[x6.index, "logret5"].std(ddof=1))

    return {
        **rets,
        "ema_spread": float(pre.ema7) / float(pre.ema20) - 1.0,
        "dist_ema20": last_close / float(pre.ema20) - 1.0,
        "ema20_slope1h": ema20_slope1h,
        "loc24": float(loc24),
        "range6": float(r6),
        "range24": float(r24),
        "range6_to_24": float(r6 / r24) if np.isfinite(r6) and np.isfinite(r24) and r24 > 0 else np.nan,
        "taker1h": float(g0.taker_imbalance(x1)),
        "taker4h": float(g0.taker_imbalance(x4)),
        "rv1h": rv1,
        "rv6h": rv6,
        "atr20_pct": float(pre.atr20) / last_close if last_close > 0 else np.nan,
    }, None


def label_row_fast(k: pd.DataFrame, t: pd.Timestamp):
    if t not in k.index:
        return None, "missing_decision_bar", None
    bars = window(k, t, t + pd.Timedelta(hours=g0.LABEL_HOURS))
    if not g0.is_contiguous(bars, t, g0.HORIZON_BARS):
        return None, "noncontiguous_or_incomplete_label_horizon", None

    ep = float(k.loc[t, "open"])
    down = ep * (1.0 - g0.BARRIER)
    up = ep * (1.0 + g0.BARRIER)
    for i, b in enumerate(bars.itertuples(index=False)):
        sell_hit = float(b.low) <= down
        buy_hit = float(b.high) >= up
        if sell_hit and buy_hit:
            return "NEUTRAL", "same_bar_dual_touch", i * 5 + 5
        if sell_hit:
            return "SELL_COMPATIBLE", "down_first", i * 5 + 5
        if buy_hit:
            return "BUY_COMPATIBLE", "up_first", i * 5 + 5
    return "NEUTRAL", "no_50bp_hit_6h", None


def main():
    g0.feature_row = feature_row_fast
    g0.label_row = label_row_fast
    g0.main()


if __name__ == "__main__":
    main()
