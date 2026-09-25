#!/usr/bin/env python3
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
subprocess.run([sys.executable, str(HERE/'eth_f85_f15_transfer_m8_economic_combination_v3.py')], check=True)
