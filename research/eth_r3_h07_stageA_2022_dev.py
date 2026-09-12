#!/usr/bin/env python3
from pathlib import Path
import eth_r3_h06_stageA_2022_dev as base

ROOT = Path(__file__).resolve().parent.parent
base.PFX = "ETH_R3_H07_STAGEA"
base.OUT_GRID = ROOT / "ETH_R3_H07_STAGEA_2022_DevGrid.csv"
base.OUT_LOCK = ROOT / "ETH_R3_H07_STAGEA_FrozenDevCandidate.csv"
base.OUT_RESULT = ROOT / "ETH_R3_H07_STAGEA_Result.md"
base.OUT_STATUS = ROOT / "ETH_R3_H07_STAGEA_Status.txt"
base.HOUR_WIB = 7

if __name__ == "__main__":
    base.main()
