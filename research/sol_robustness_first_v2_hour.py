#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as engine
import sol_robustness_first_v2 as v2

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hour", type=int, required=True)
    args = ap.parse_args()
    hour = int(args.hour)
    if not 0 <= hour <= 23:
        raise SystemExit("hour must be 0..23")

    # Same preregistered hard end: August 2026 is never loaded.
    engine.base.END = v2.RESEARCH_END
    x5, coverage = engine.base.load5("SOLUSDT")
    if x5.index.max() >= v2.RESEARCH_END:
        raise AssertionError("research loader crossed frozen end")

    print(f"parallel worker H{hour:02d} {v2.hour_wib(hour)} WIB", flush=True)
    cache = v2.build_hour_cache(x5, hour)
    rows = []
    for lookback in v2.LOOKBACKS:
        for hold in v2.HOLDS:
            for rule in v2.RULES:
                rows.append(v2.eval_candidate(cache, hour, lookback, hold, rule))

    grid = pd.DataFrame(rows)
    expected = len(v2.LOOKBACKS) * len(v2.HOLDS) * len(v2.RULES)
    if len(grid) != expected:
        raise AssertionError(f"hour candidate count mismatch {len(grid)} != {expected}")

    out = ROOT / f"SOL_ROBUSTNESS_FIRST_V2_H{hour:02d}_Grid.csv"
    meta = ROOT / f"SOL_ROBUSTNESS_FIRST_V2_H{hour:02d}_Meta.txt"
    grid.to_csv(out, index=False)
    meta.write_text(f"hour={hour}\ncoverage={coverage:.12f}\nrows={len(grid)}\n")
    print(f"saved {out.name} rows={len(grid)} coverage={coverage:.6f}")


if __name__ == "__main__":
    main()
