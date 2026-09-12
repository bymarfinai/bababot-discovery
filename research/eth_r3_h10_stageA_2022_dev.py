#!/usr/bin/env python3
from pathlib import Path
import eth_r3_h06_stageA_2022_dev as base

ROOT = Path(__file__).resolve().parent.parent
base.PFX = "ETH_R3_H10_STAGEA"
base.OUT_GRID = ROOT / "ETH_R3_H10_STAGEA_2022_DevGrid.csv"
base.OUT_LOCK = ROOT / "ETH_R3_H10_STAGEA_FrozenDevCandidate.csv"
base.OUT_RESULT = ROOT / "ETH_R3_H10_STAGEA_Result.md"
base.OUT_STATUS = ROOT / "ETH_R3_H10_STAGEA_Status.txt"
base.HOUR_WIB = 10

if __name__ == "__main__":
    base.main()
    if base.OUT_RESULT.exists():
        base.OUT_RESULT.write_text(base.OUT_RESULT.read_text().replace("ETH R3 H06", "ETH R3 H10"))
    if base.OUT_STATUS.exists():
        base.OUT_STATUS.write_text(base.OUT_STATUS.read_text().replace("ETH_R3_H06", "ETH_R3_H10"))
