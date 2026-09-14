#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import sol_adaptive_structure_detector_v1 as detector


def fast_context_features(x5: pd.DataFrame, start: pd.Timestamp, orb_rows: list) -> dict | None:
    idx = x5.index
    i1 = int(idx.searchsorted(start, side="left"))
    i24 = int(idx.searchsorted(start - pd.Timedelta(hours=24), side="left"))
    i7 = int(idx.searchsorted(start - pd.Timedelta(days=7), side="left"))
    q24 = x5.iloc[i24:i1]
    q7 = x5.iloc[i7:i1]
    if len(q24) < 250 or len(q7) < 1500:
        return None

    c24 = q24.close.astype(float)
    c7 = q7.close.astype(float)
    lr24 = np.log(c24).diff().dropna()
    lr7 = np.log(c7).diff().dropna()
    if len(lr24) < 200 or len(lr7) < 1000:
        return None

    rv24 = float(lr24.std(ddof=1) * np.sqrt(288.0) * 100.0)
    rv7 = float(lr7.std(ddof=1) * np.sqrt(288.0) * 100.0)
    trend24 = float((c24.iloc[-1] / c24.iloc[0] - 1.0) * 100.0)
    bar_range_pct = ((q24.high.astype(float) - q24.low.astype(float)) / q24.close.astype(float) * 100.0)
    avg_bar_range = float(bar_range_pct.mean())
    vol_med = float(q24.volume.astype(float).median())
    orb_vol = float(sum(float(r.volume) for r in orb_rows))
    orb_vol_ratio = orb_vol / (3.0 * vol_med) if vol_med > 0 else np.nan

    h = int(start.hour)
    ang = 2.0 * np.pi * h / 24.0
    return {
        "hour_sin": float(np.sin(ang)),
        "hour_cos": float(np.cos(ang)),
        "pre24_rv_pct": rv24,
        "pre7d_rv_pct": rv7,
        "pre24_trend_pct": trend24,
        "pre24_avg_bar_range_pct": avg_bar_range,
        "orb_volume_ratio": orb_vol_ratio,
    }


def main():
    detector.context_features = fast_context_features
    detector.main()


if __name__ == "__main__":
    main()
