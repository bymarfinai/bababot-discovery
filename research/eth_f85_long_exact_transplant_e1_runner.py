#!/usr/bin/env python3
"""Execution wrapper for ETH E1.

This fixes only an implementation edge case: an empty partition×zone bucket has
no DataFrame columns. Strategy logic, signals, exits, filters, sizing, and gates
remain unchanged from the preregistered E1 script.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import eth_f85_long_exact_transplant_e1 as e1

_original_metrics = e1.metrics


def safe_metrics(d):
    if d is None or len(d) == 0 or 'net_pnl_usd' not in d.columns:
        return {
            'n': 0,
            'wins': 0,
            'wr': np.nan,
            'pf': np.nan,
            'expectancy': np.nan,
            'total_net': 0.0,
            'max_loss_streak': 0,
        }
    return _original_metrics(d)


e1.metrics = safe_metrics

if __name__ == '__main__':
    e1.main()
