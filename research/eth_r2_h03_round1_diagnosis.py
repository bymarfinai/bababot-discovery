#!/usr/bin/env python3
from pathlib import Path

import eth_r2_h05_round1_diagnosis as lab

ROOT = Path(__file__).resolve().parent.parent

# Methodology is intentionally inherited unchanged from the preregistered H05
# diagnostic engine; only the target hour and file namespace are changed.
lab.GRID_PATH = ROOT / "ETH_R1_H03_ROBUST_TrainGrid.csv"
lab.OUT_FAMILY = ROOT / "ETH_R2_H03_R1_FamilyDiagnosis.csv"
lab.OUT_CELL = ROOT / "ETH_R2_H03_R1_CellDiagnosis.csv"
lab.OUT_RESULT = ROOT / "ETH_R2_H03_R1_Result.md"
lab.OUT_STATUS = ROOT / "ETH_R2_H03_R1_Status.txt"
lab.HOUR_WIB = 3


def relabel(path: Path):
    if path.exists():
        path.write_text(path.read_text().replace("H05", "H03"))


def main():
    lab.main()
    relabel(lab.OUT_RESULT)
    relabel(lab.OUT_STATUS)


if __name__ == "__main__":
    main()
