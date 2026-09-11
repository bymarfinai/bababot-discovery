#!/usr/bin/env python3
"""Preregistered H01 adapter for the frozen SOL economic-first engine."""

from pathlib import Path

import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ECONOMIC_FIRST_H01_LONG_08_09WIB_CHARACTER"

# H01 is an independent one-hour habitat. Only the clock and output namespace
# differ from H00; candidate grammar, normalization, economics, and gates stay frozen.
engine.CLOCKS = (60, 75, 90, 105)
engine.PFX = PFX
engine.OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
engine.OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
engine.OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
engine.OUT_RESULT = ROOT / f"{PFX}_Result.md"
engine.OUT_STATUS = ROOT / f"{PFX}_Status.txt"


def relabel_h01_outputs() -> None:
    result = engine.OUT_RESULT.read_text()
    replacements = (
        ("SOL Economic-First H00 — 07:00–08:00 WIB", "SOL Economic-First H01 — 08:00–09:00 WIB"),
        ("00:00–01:00 UTC / 07:00–08:00 WIB", "01:00–02:00 UTC / 08:00–09:00 WIB"),
        ("07:00–08:00 WIB", "08:00–09:00 WIB"),
        ("SOL_ECONOMIC_FIRST_H00_", "SOL_ECONOMIC_FIRST_H01_"),
    )
    for old, new in replacements:
        result = result.replace(old, new)
    engine.OUT_RESULT.write_text(result)

    status = engine.OUT_STATUS.read_text().replace(
        "SOL_ECONOMIC_FIRST_H00_", "SOL_ECONOMIC_FIRST_H01_"
    )
    engine.OUT_STATUS.write_text(status)


def main() -> None:
    engine.main()
    relabel_h01_outputs()
    print(engine.OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
