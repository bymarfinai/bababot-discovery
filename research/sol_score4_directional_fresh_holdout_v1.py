#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import sol_structural_liquidity_detector_v3 as v3
import sol_score4_directional_anatomy_v2 as frozen

OBSERVATION_END = pd.Timestamp("2026-09-21 00:00:00", tz="UTC")


def main():
    # Data-horizon plumbing only. The frozen evaluator/rule is unchanged.
    base = v3.wf1.v3.v1.base
    base.END = OBSERVATION_END
    frozen.main()


if __name__ == "__main__":
    main()
