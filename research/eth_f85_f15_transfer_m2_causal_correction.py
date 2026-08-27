#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / 'research' / 'eth_post_breakout_retest_m1.py'
subprocess.run([sys.executable, str(RUNNER)], check=True)

aliases = {
    'ETH_POST_BREAKOUT_RETEST_M1_Result.md': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Result.md',
    'ETH_POST_BREAKOUT_RETEST_M1_Detail.csv': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Detail.csv',
    'ETH_POST_BREAKOUT_RETEST_M1_Summary.csv': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Summary.csv',
    'ETH_POST_BREAKOUT_RETEST_M1_Targets.csv': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Targets.csv',
    'ETH_POST_BREAKOUT_RETEST_M1_Status.txt': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Status.txt',
    'ETH_POST_BREAKOUT_RETEST_M1_Preregistration.md': 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_POST_BREAKOUT_M1_Preregistration.md',
}
for src, dst in aliases.items():
    p = ROOT / src
    if p.exists():
        shutil.copy2(p, ROOT / dst)
