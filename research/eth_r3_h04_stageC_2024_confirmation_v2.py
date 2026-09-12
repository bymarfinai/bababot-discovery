#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12
import eth_r3_h04_stageC_2024_confirmation as base


def candidate_events_2024(cache, lb: int, hold: int, rule: str):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        entry = pd.to_datetime(ent, utc=True)
        exit_ = pd.to_datetime(ex, utc=True)
        m = valid & (entry >= base.START) & (exit_ < base.END) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(entry[m], exit_[m], gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
            })
    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


# Technical correction only. The frozen rule/coordinate and all confirmation
# gates remain those preregistered before 2024 was opened.
r1.candidate_events = candidate_events_2024


if __name__ == "__main__":
    base.main()
