#!/usr/bin/env python3
"""Execution wrapper for the frozen three-session reversal study.

Only fixes the research-report block-splitting plumbing bug from the first run.
No strategy/data/anchor/RR rule is changed.
"""
import pandas as pd
import btc_three_session_daily_hilo_reversal as core


def fixed_blocks(z: pd.DataFrame):
    if z.empty:
        return []
    z = z.sort_values("entry_ts").reset_index(drop=True)
    n = len(z)
    bounds = [0, n // 4, n // 2, (3 * n) // 4, n]
    out = []
    for i in range(4):
        part = z.iloc[bounds[i]:bounds[i + 1]].copy()
        out.append({"block": f"B{i + 1}", **core.stats(part)})
    return out


core.blocks = fixed_blocks

if __name__ == "__main__":
    core.main()
