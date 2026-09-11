#!/usr/bin/env python3
"""Preregistered H06 adapter for the frozen SOL economic-first engine."""

from pathlib import Path

import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ECONOMIC_FIRST_H06_LONG_13_14WIB_CHARACTER"

engine.CLOCKS = (360, 375, 390, 405)
engine.PFX = PFX
engine.OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
engine.OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
engine.OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
engine.OUT_RESULT = ROOT / f"{PFX}_Result.md"
engine.OUT_STATUS = ROOT / f"{PFX}_Status.txt"


def relabel_outputs() -> None:
    result = engine.OUT_RESULT.read_text()
    for old, new in (
        ("SOL Economic-First H00 — 07:00–08:00 WIB", "SOL Economic-First H06 — 13:00–14:00 WIB"),
        ("00:00–01:00 UTC / 07:00–08:00 WIB", "06:00–07:00 UTC / 13:00–14:00 WIB"),
        ("07:00–08:00 WIB", "13:00–14:00 WIB"),
        ("SOL_ECONOMIC_FIRST_H00_", "SOL_ECONOMIC_FIRST_H06_"),
    ):
        result = result.replace(old, new)
    engine.OUT_RESULT.write_text(result)
    engine.OUT_STATUS.write_text(
        engine.OUT_STATUS.read_text().replace("SOL_ECONOMIC_FIRST_H00_", "SOL_ECONOMIC_FIRST_H06_")
    )


def main() -> None:
    engine.main()
    relabel_outputs()
    print(engine.OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
