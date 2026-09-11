#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

import sol_robustness_first_v2 as v2

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "v2-hour-results"


def read_coverage() -> float:
    vals = []
    for p in sorted(INPUT_DIR.glob("SOL_ROBUSTNESS_FIRST_V2_H??_Meta.txt")):
        for line in p.read_text().splitlines():
            if line.startswith("coverage="):
                vals.append(float(line.split("=", 1)[1]))
    if len(vals) != 24:
        raise AssertionError(f"expected 24 coverage metadata files, got {len(vals)}")
    if max(vals) - min(vals) > 1e-12:
        raise AssertionError("coverage mismatch across hourly workers")
    return vals[0]


def main() -> None:
    parts = []
    for hour in range(24):
        p = INPUT_DIR / f"SOL_ROBUSTNESS_FIRST_V2_H{hour:02d}_Grid.csv"
        if not p.exists():
            raise FileNotFoundError(p)
        q = pd.read_csv(p)
        expected = len(v2.LOOKBACKS) * len(v2.HOLDS) * len(v2.RULES)
        if len(q) != expected:
            raise AssertionError(f"H{hour:02d} rows {len(q)} != {expected}")
        parts.append(q)

    grid = pd.concat(parts, ignore_index=True)
    expected_total = 24 * len(v2.LOOKBACKS) * len(v2.HOLDS) * len(v2.RULES)
    if len(grid) != expected_total:
        raise AssertionError(f"total rows {len(grid)} != {expected_total}")

    # Preserve booleans after CSV round-trip.
    bool_cols = [
        "anchor_gate", "pooled_gate", "era_gate", "effective_n_gate", "pre_neighborhood_gate"
    ]
    bool_cols += [c for c in grid.columns if c.endswith("_pass") or c.endswith("_evaluable") or c.endswith("_supportive")]
    for c in bool_cols:
        if c in grid:
            if grid[c].dtype != bool:
                grid[c] = grid[c].astype(str).str.lower().map({"true": True, "false": False}).fillna(False)

    grid = v2.add_neighborhood_gate(grid)
    passers = v2.rank_passers(grid[grid.candidate_gate].copy())
    top = grid.sort_values(
        ["candidate_gate", "pre_neighborhood_gate", "win_rate", "expectancy", "pf", "max_dd"],
        ascending=[False, False, False, False, False, True],
    ).head(50)

    coverage = read_coverage()
    grid.to_csv(v2.OUT_GRID, index=False)
    passers.to_csv(v2.OUT_PASSERS, index=False)
    top.to_csv(v2.OUT_TOP, index=False)
    result = v2.render_result(grid, passers, coverage)
    v2.OUT_RESULT.write_text(result)
    status = "SOL_ROBUSTNESS_FIRST_V2_CHARACTER_FOUND" if len(passers) else "SOL_ROBUSTNESS_FIRST_V2_NO_CHARACTER"
    v2.OUT_STATUS.write_text(status + "\n")
    print(result)


if __name__ == "__main__":
    main()
