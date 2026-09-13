#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "research" / "bnb_long_reset_v1_h00_primary.py"

spec = importlib.util.spec_from_file_location("bnb_reset_h00_base", BASE_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load frozen H00 runner: {BASE_RUNNER}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# H01 is a habitat-only shift. All Stage-2 methodology, features, bins,
# gates, ranking, Development years, horizons, and causal rules remain frozen.
TARGET_LOCAL_HOUR = 1
PFX = "BNB_LONG_RESET_V1_H01_PRIMARY"
base.PFX = PFX
base.OUT_EVENTS = ROOT / f"{PFX}_DevelopmentEvents.csv"
base.OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
base.OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
base.OUT_RESULT = ROOT / f"{PFX}_Result.md"
base.OUT_STATUS = ROOT / f"{PFX}_Status.txt"
base.OUT_SELECTED = ROOT / f"{PFX}_Selected.json"


def build_events_h01(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idx = x.index
    for i, ts in enumerate(idx):
        local = ts + pd.Timedelta(hours=7)
        if (
            local.year not in base.DEV_YEARS
            or local.hour != TARGET_LOCAL_HOUR
            or local.minute not in base.ANCHOR_MINUTES
        ):
            continue
        row = base.feature_row(x, i, ts)
        if row is not None and all(np.isfinite(row[f"r{h}"]) for h in base.HORIZONS):
            rows.append(row)

    E = pd.DataFrame(rows).sort_values("entry_ts_utc").reset_index(drop=True)
    if len(E) < 3000:
        raise RuntimeError(f"unexpectedly low H01 development event count: {len(E)}")
    E["consensus_return"] = E[[f"r{h}" for h in base.HORIZONS]].mean(axis=1)
    E["consensus_win"] = E.consensus_return > 0
    return E


base.build_events = build_events_h01


def main() -> None:
    base.main()

    # Keep generated human-readable artifact explicit about the habitat shift.
    if base.OUT_RESULT.exists():
        text = base.OUT_RESULT.read_text()
        text = text.replace("H00", "H01")
        text = text.replace("00:00-01:00 WIB", "01:00-02:00 WIB")
        text = text.replace("00:00–01:00 WIB", "01:00–02:00 WIB")
        base.OUT_RESULT.write_text(text)


if __name__ == "__main__":
    main()
