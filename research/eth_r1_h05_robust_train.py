#!/usr/bin/env python3
"""ETH R1 H05 robust train discovery; exact-parity wrapper around preregistered H00 engine."""
from pathlib import Path
import eth_r1_h00_robust_train as study
ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R1_H05_ROBUST"
study.HOUR_WIB = 5
study.PFX = PFX
study.OUT_GRID = ROOT / f"{PFX}_TrainGrid.csv"
study.OUT_REGIONS = ROOT / f"{PFX}_TrainRegions.csv"
study.OUT_LOCK = ROOT / f"{PFX}_FrozenCandidate.csv"
study.OUT_RESULT = ROOT / f"{PFX}_TrainResult.md"
study.OUT_STATUS = ROOT / f"{PFX}_TrainStatus.txt"
def main():
    study.main()
    if study.OUT_RESULT.exists(): study.OUT_RESULT.write_text(study.OUT_RESULT.read_text().replace("ETH R1 H00", "ETH R1 H05"))
    if study.OUT_STATUS.exists(): study.OUT_STATUS.write_text(study.OUT_STATUS.read_text().replace("ETH_R1_H00", "ETH_R1_H05"))
if __name__ == "__main__": main()
