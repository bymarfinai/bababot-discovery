#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "research" / "bnb_long_reset_v1_h00_primary.py"

spec = importlib.util.spec_from_file_location("bnb_reset_h00_base", BASE_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load frozen base runner: {BASE_RUNNER}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

base.PFX = "BNB_LONG_RESET_V1_H03_PRIMARY"
base.OUT_EVENTS = ROOT / f"{base.PFX}_DevelopmentEvents.csv"
base.OUT_GRID = ROOT / f"{base.PFX}_DevelopmentGrid.csv"
base.OUT_LEADER = ROOT / f"{base.PFX}_DevelopmentLeaderboard.csv"
base.OUT_RESULT = ROOT / f"{base.PFX}_Result.md"
base.OUT_STATUS = ROOT / f"{base.PFX}_Status.txt"
base.OUT_SELECTED = ROOT / f"{base.PFX}_Selected.json"

TARGET_LOCAL_HOUR = 3


def build_events_h03() -> None:
    old_build = base.build_events
    try:
        def _build(x):
            rows = []
            idx = x.index
            for i, ts in enumerate(idx):
                local = ts + base.pd.Timedelta(hours=7)
                if (
                    local.year not in base.DEV_YEARS
                    or local.hour != TARGET_LOCAL_HOUR
                    or local.minute not in base.ANCHOR_MINUTES
                ):
                    continue
                row = base.feature_row(x, i, ts)
                if row is not None and all(base.np.isfinite(row[f"r{h}"]) for h in base.HORIZONS):
                    rows.append(row)
            E = base.pd.DataFrame(rows).sort_values("entry_ts_utc").reset_index(drop=True)
            if len(E) < 3000:
                raise RuntimeError(f"unexpectedly low H03 development event count: {len(E)}")
            E["consensus_return"] = E[[f"r{h}" for h in base.HORIZONS]].mean(axis=1)
            E["consensus_win"] = E.consensus_return > 0
            return E

        base.build_events = _build
        base.main()
    finally:
        base.build_events = old_build


if __name__ == "__main__":
    build_events_h03()
