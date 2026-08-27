#!/usr/bin/env python3
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(HERE / 'eth_f85_f15_transfer_m7_target_atlas.py')], check=True)

src_prefix = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M7'
dst_prefix = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M7'
for suffix in ['Result.md','Detail.csv','Summary.csv','Selection.csv','Status.txt']:
    src = ROOT / f'{src_prefix}_{suffix}'
    if src.exists():
        # Already matches registered artifact glob; copy is intentionally unnecessary.
        pass
print((ROOT / f'{src_prefix}_Result.md').read_text())
