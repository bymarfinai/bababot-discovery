#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd
import eth_r3_h04_stageA_2022_dev as base


def period_utc(T: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    entry = pd.to_datetime(T.entry_ts, utc=True)
    exit_ = pd.to_datetime(T.exit_ts, utc=True)
    mask = (entry >= start) & (exit_ < end)
    return base.stats(T.loc[mask])


# Operational compatibility fix only: normalize candidate event timestamps before
# half-year comparisons. Scientific gates, grammar, grid, ranking and partitions
# remain exactly as preregistered.
base.period = period_utc


if __name__ == "__main__":
    base.main()
