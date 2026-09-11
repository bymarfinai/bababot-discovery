#!/usr/bin/env python3
"""ETH R1 H01 robust train discovery.

Exact-parity wrapper around the preregistered H00 engine. This intentionally changes
only the WIB hour and output namespace; all train partitioning, coarse timing grid,
90-rule grammar, gates, temporal checks, plateau construction, and frozen-candidate
selection remain identical to H00.

2024 validation remains unopened inside this runner. OOS 2025+ remains closed.
"""
from __future__ import annotations

from pathlib import Path
import eth_r1_h00_robust_train as study

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R1_H01_ROBUST"

# The only scientific variable changed from H00.
study.HOUR_WIB = 1

# Separate persistence namespace; all protocol constants/functions are inherited unchanged.
study.PFX = PFX
study.OUT_GRID = ROOT / f"{PFX}_TrainGrid.csv"
study.OUT_REGIONS = ROOT / f"{PFX}_TrainRegions.csv"
study.OUT_LOCK = ROOT / f"{PFX}_FrozenCandidate.csv"
study.OUT_RESULT = ROOT / f"{PFX}_TrainResult.md"
study.OUT_STATUS = ROOT / f"{PFX}_TrainStatus.txt"


def main():
    study.main()

    # H00 engine text labels are presentation-only; correct them after identical computation.
    if study.OUT_RESULT.exists():
        text = study.OUT_RESULT.read_text()
        text = text.replace("ETH R1 H00", "ETH R1 H01")
        study.OUT_RESULT.write_text(text)
    if study.OUT_STATUS.exists():
        text = study.OUT_STATUS.read_text().replace("ETH_R1_H00", "ETH_R1_H01")
        study.OUT_STATUS.write_text(text)


if __name__ == "__main__":
    main()
