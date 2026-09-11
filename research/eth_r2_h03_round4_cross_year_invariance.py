#!/usr/bin/env python3
from pathlib import Path

import eth_r2_h05_round4_cross_year_invariance as lab

ROOT = Path(__file__).resolve().parent.parent
lab.PFX = "ETH_R2_H03_R4"
lab.OUT_GRID = ROOT / f"{lab.PFX}_CrossYearGrid.csv"
lab.OUT_REGIONS = ROOT / f"{lab.PFX}_Regions.csv"
lab.OUT_LOCK = ROOT / f"{lab.PFX}_FrozenRegion.csv"
lab.OUT_RESULT = ROOT / f"{lab.PFX}_Result.md"
lab.OUT_STATUS = ROOT / f"{lab.PFX}_Status.txt"

# Preserve the already-preregistered H05 Round-4 methodology exactly while
# redirecting its hour calculation to H03.
_original_clocks_for_hour = lab.r1.clocks_for_hour
lab.r1.clocks_for_hour = lambda _ignored_hour: _original_clocks_for_hour(3)


def relabel(path: Path):
    if path.exists():
        path.write_text(path.read_text().replace("H05", "H03"))


def main():
    lab.main()
    relabel(lab.OUT_RESULT)
    relabel(lab.OUT_STATUS)


if __name__ == "__main__":
    main()
