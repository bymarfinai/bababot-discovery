#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
M4_PATH = HERE / 'eth_f85_f15_transfer_m4_retrace_confirmation.py'
spec = importlib.util.spec_from_file_location('eth_m4', M4_PATH)
m4 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m4)


def main():
    m4.main()
    # The already-registered PR workflow uploads the M2 prefix glob.
    # Branch-only aliases expose M4 outputs without changing the workflow on main.
    aliases = {
        m4.OUT_MD: ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M4_Result.md',
        m4.OUT_SUM: ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M4_Summary.csv',
        m4.OUT_DETAIL: ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M4_Detail.csv',
        m4.OUT_STATUS: ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M4_Status.txt',
    }
    for src, dst in aliases.items():
        shutil.copyfile(src, dst)


if __name__ == '__main__':
    main()
