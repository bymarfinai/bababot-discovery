#!/usr/bin/env python3
from pathlib import Path
import eth_r3_h06_stageB_2023_test as base

ROOT = Path(__file__).resolve().parent.parent
base.LOCK_PATH = ROOT / "ETH_R3_H08_STAGEA_FrozenDevCandidate.csv"
base.OUT_NEIGHBOR = ROOT / "ETH_R3_H08_STAGEB_2023_LocalNeighborhood.csv"
base.OUT_LOCK = ROOT / "ETH_R3_H08_STAGEB_FrozenStableCandidate.csv"
base.OUT_RESULT = ROOT / "ETH_R3_H08_STAGEB_Result.md"
base.OUT_STATUS = ROOT / "ETH_R3_H08_STAGEB_Status.txt"
base.HOUR_WIB = 8

if __name__ == "__main__":
    base.main()
    if base.OUT_RESULT.exists():
        base.OUT_RESULT.write_text(base.OUT_RESULT.read_text().replace("ETH R3 H06", "ETH R3 H08"))
    if base.OUT_STATUS.exists():
        base.OUT_STATUS.write_text(base.OUT_STATUS.read_text().replace("ETH_R3_H06", "ETH_R3_H08"))
