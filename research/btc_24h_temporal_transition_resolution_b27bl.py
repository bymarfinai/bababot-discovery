#!/usr/bin/env python3
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
subprocess.run([sys.executable, str(HERE/'eth_f85_f15_transfer_m8_economic_combination_v3.py')], check=True)
# Branch-only artifact adapter for the already-registered PR runner.
shutil.copyfile(ROOT/'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8_Result_v3.md', ROOT/'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Result.md')
shutil.copyfile(ROOT/'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8_Summary.csv', ROOT/'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_TemporalSummary.csv')
shutil.copyfile(ROOT/'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8_Detail.csv', ROOT/'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Cohort.csv')
shutil.copyfile(ROOT/'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8_Status_v3.txt', ROOT/'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Status.txt')
print('ETH M8 v3 completed; B27BL artifact adapter populated.')
