#!/usr/bin/env python3
"""Branch-only execution adapter for preregistered ETH M3.

The registered PR workflow on main invokes this path.  On this experiment branch
only, delegate that invocation to the frozen M3 winner-MAE audit.  No M2 research
logic or main-branch file is modified by this adapter.
"""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
M3_PATH = HERE / 'eth_f85_f15_transfer_m3_winner_mae.py'

spec = importlib.util.spec_from_file_location('eth_m3_runner', M3_PATH)
m3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m3)


def main():
    m3.main()

    # The already-registered M2 PR workflow uploads only the M2 prefix.
    # Create branch-artifact aliases so M3 outputs are retrievable without
    # changing the workflow definition on main.  Canonical M3 files remain intact.
    aliases = {
        ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_Result.md':
            ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M3_Result.md',
        ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_Detail.csv':
            ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M3_Detail.csv',
        ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_Summary.csv':
            ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M3_Summary.csv',
        ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_SurvivalCurve.csv':
            ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M3_SurvivalCurve.csv',
        ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_Status.txt':
            ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M3_Status.txt',
    }
    for src, dst in aliases.items():
        if not src.exists():
            raise RuntimeError(f'M3 output missing: {src.name}')
        shutil.copyfile(src, dst)

    print((ROOT / 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE_Result.md').read_text())


if __name__ == '__main__':
    main()
