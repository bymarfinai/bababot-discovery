#!/usr/bin/env python3
"""Fast exact-equivalent runner for frozen SR81.

Scientific definition is unchanged. The only optimization replaces repeated
full-DataFrame completed-H1 filtering used by touch_atr() with an index
search for the exact same latest completed 1H row.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import btc_friday_sr81_prior_proof_level as sr81


def fast_touch_atr(h: pd.DataFrame, t: pd.Timestamp):
    # Original: completed_h1_before(h,t) => h[h.index <= t-1h], then last row.
    cutoff = t - pd.Timedelta(hours=1)
    pos = h.index.searchsorted(cutoff, side="right") - 1
    if pos < 0:
        return np.nan
    return float(h.iloc[int(pos)].atr14)


sr81.touch_atr = fast_touch_atr

if __name__ == "__main__":
    sr81.main()
