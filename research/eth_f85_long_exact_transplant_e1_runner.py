#!/usr/bin/env python3
"""Execution wrapper for ETH E1.

This fixes only implementation edge cases around empty buckets under Pandas 3:
- empty metrics buckets have no PnL column;
- an empty `accepted` assignment otherwise becomes float dtype and `d[d.accepted]`
  can be interpreted as column selection rather than a boolean row mask.

Strategy logic, signals, exits, filters, sizing, and preregistered gates remain
unchanged from the E1 script.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import eth_f85_long_exact_transplant_e1 as e1

_original_metrics = e1.metrics
_original_lock = e1.lock


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


def safe_lock(g, label):
    q = _original_lock(g, label)
    if 'accepted' in q.columns:
        q['accepted'] = q['accepted'].astype(bool)
    return q


e1.metrics = safe_metrics
e1.lock = safe_lock

if __name__ == '__main__':
    e1.main()
