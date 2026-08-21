#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import btc_mtf_bull_cascade_b21 as b21


def _on_times_resolution_safe(state: pd.Series) -> pd.DatetimeIndex:
    s = state.fillna(False).astype(bool)
    return s.index[s & ~s.shift(1, fill_value=False)]


def _first_on_resolution_safe(on_idx: pd.DatetimeIndex, seed: pd.Timestamp):
    j = int(on_idx.searchsorted(seed, side='left'))
    if j >= len(on_idx):
        return pd.NaT
    t = on_idx[j]
    return t if t <= seed + b21.HORIZON else pd.NaT


def main():
    b21._on_times = _on_times_resolution_safe
    b21._first_on = _first_on_resolution_safe
    b21.main()

    root = Path(__file__).resolve().parent.parent
    result_json = root / 'BTC_MTF_BULL_CASCADE_B21_Result.json'
    result_md = root / 'BTC_MTF_BULL_CASCADE_B21_Result.md'

    payload = json.loads(result_json.read_text())
    payload['implementation_revision'] = 'B21_V1_R2_RESOLUTION_SAFE'
    payload['supersedes_first_run'] = 'run_id=32478430958'
    result_json.write_text(json.dumps(payload, indent=2) + '\n')

    md = result_md.read_text()
    marker = '# BTC MTF Bull Cascade B21 — Result\n'
    note = (
        '# BTC MTF Bull Cascade B21 — Result\n\n'
        '**Implementation revision:** `B21_V1_R2_RESOLUTION_SAFE`  \n'
        '**Supersedes:** first run `32478430958`, invalidated only for timestamp-unit lookup implementation.\n'
    )
    if md.startswith(marker):
        md = note + md[len(marker):]
    result_md.write_text(md)


if __name__ == '__main__':
    main()
