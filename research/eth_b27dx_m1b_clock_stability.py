#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_b27dx_pair_calibration_v2.py'
spec = importlib.util.spec_from_file_location('eth_v2_base', BASE_PATH)
b = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(b)

PFX = 'ETH_B27DX_M1B_CLOCK_STABILITY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PROBES = ROOT / f'{PFX}_ProbeScores.csv'
OUT_CLOCKS = ROOT / f'{PFX}_ClockSummary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_MIN = 330
HORIZON_MIN = 390
TARGET_EXT = 0.20
ENTRY_PROBES = (0.90, 0.85, 0.80)
STOP_F = 0.35
GRID_MINUTES = tuple(range(14 * 60, 18 * 60 + 1, 30))
VAL_PARTS = ('external', 'reference_validation')
ALL_PARTS = ('development', 'external', 'reference_validation', 'august')
ANCHOR_MIN = 16 * 60


def probe_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def clock_label(exec_min: int) -> str:
    return f'{exec_min // 60:02d}:{exec_min % 60:02d}'


def score_probe(x: pd.DataFrame, part: str, exec_min: int, f: float) -> dict:
    r = b.score_config(
        x=x,
        part_name=part,
        side='LONG',
        exec_min=exec_min,
        ref_min=REF_MIN,
        horizon_min=HORIZON_MIN,
        entry_f=f,
        target_ext=TARGET_EXT,
        stop_f=STOP_F,
        stress_bps=0.0,
    )
    r['exec_min'] = int(exec_min)
    r['clock_utc'] = clock_label(exec_min)
    r['probe'] = probe_label(f)
    if part == 'development':
        r['positive'] = bool(
            r['n'] >= 30 and r['pf'] >= 1.10 and
            r['expectancy'] > 0 and r['net'] > 0
        )
    elif part in VAL_PARTS:
        r['positive'] = bool(
            r['n'] >= 15 and r['pf'] > 1.00 and
            r['expectancy'] > 0 and r['net'] > 0
        )
    else:
        r['positive'] = False
    return r


def run_scores(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in GRID_MINUTES:
        for part in ALL_PARTS:
            for f in ENTRY_PROBES:
                rows.append(score_probe(x, part, exec_min, f))
    return pd.DataFrame(rows)


def finite_pf_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors='coerce').replace([np.inf], 999999.0)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in GRID_MINUTES:
        row = {
            'exec_min': int(exec_min),
            'clock_utc': clock_label(exec_min),
        }

        dev = scores[(scores.exec_min == exec_min) & (scores.partition == 'development')]
        row['development_positive_probes'] = int(dev.positive.sum())
        row['development_pass'] = bool(row['development_positive_probes'] >= 2)
        row['development_median_pf'] = float(finite_pf_series(dev.pf).median())
        row['development_median_expectancy'] = float(pd.to_numeric(dev.expectancy, errors='coerce').median())
        row['development_total_n'] = int(pd.to_numeric(dev.n, errors='coerce').sum())

        for part in VAL_PARTS:
            q = scores[(scores.exec_min == exec_min) & (scores.partition == part)]
            pos = int(q.positive.sum())
            enough_n = int((pd.to_numeric(q.n, errors='coerce') >= 15).sum())
            row[f'{part}_positive_probes'] = pos
            row[f'{part}_n_probes'] = enough_n
            row[f'{part}_pass'] = bool(pos >= 2 and enough_n >= 2)

        row['supported'] = bool(
            row['development_pass'] and
            row['external_pass'] and
            row['reference_validation_pass']
        )
        rows.append(row)
    return pd.DataFrame(rows)


def anchor_run(summary: pd.DataFrame) -> list[int]:
    supported = set(int(v) for v in summary.loc[summary.supported, 'exec_min'])
    if ANCHOR_MIN not in supported:
        return []

    run = [ANCHOR_MIN]
    cur = ANCHOR_MIN - 30
    while cur in supported:
        run.insert(0, cur)
        cur -= 30
    cur = ANCHOR_MIN + 30
    while cur in supported:
        run.append(cur)
        cur += 30
    return run


def fmt(x, nd=2):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.{nd}f}'


def main():
    x, coverage = b.m.m.load5()
    scores = run_scores(x)
    scores.to_csv(OUT_PROBES, index=False)

    summary = summarize(scores)
    summary.to_csv(OUT_CLOCKS, index=False)

    run = anchor_run(summary)
    anchor_row = summary[summary.exec_min == ANCHOR_MIN].iloc[0]
    anchor_supported = bool(anchor_row.supported)

    if not anchor_supported:
        status = 'ETH_M1B_ANCHOR_NOT_SUPPORTED'
    elif len(run) >= 3:
        status = 'ETH_M1B_LOCAL_HABITAT_SUPPORTED'
    else:
        status = 'ETH_M1B_ANCHOR_SUPPORTED_BUT_ISOLATED'

    lines = [
        '# ETH B27DX V2 — M1B Clock / Habitat Stability — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        'M1B changes execution clock only: 14:00–18:00 UTC in frozen 30-minute steps. All M1 diagnostic economics remain unchanged.',
        '',
        '| UTC clock | Dev + probes | Dev median PF | Dev median expectancy | External + probes | Validation + probes | Supported |',
        '|---:|---:|---:|---:|---:|---:|---|',
    ]

    for _, r in summary.iterrows():
        lines.append(
            f"| {r.clock_utc} | {int(r.development_positive_probes)}/3 | "
            f"{fmt(r.development_median_pf)} | {fmt(r.development_median_expectancy)} | "
            f"{int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 | "
            f"{'YES' if bool(r.supported) else 'NO'} |"
        )

    lines += ['', '## Anchor-local contiguous run', '']
    if run:
        labels = [clock_label(v) for v in run]
        width = run[-1] - run[0]
        lines += [
            f"Supported run containing 16:00 UTC: **{' → '.join(labels)}**.",
            f'Contiguous first-to-last width: **{width} minutes**.',
            f'Number of consecutive supported 30-minute clock points: **{len(run)}**.',
        ]
    else:
        lines.append('No supported contiguous run contains 16:00 UTC because the anchor itself did not remain supported.')

    lines += [
        '',
        f'**Status: {status}**',
        '',
    ]

    if status == 'ETH_M1B_LOCAL_HABITAT_SUPPORTED':
        lines.append('Interpretation: the M1 16:00 anchor is embedded in a locally stable ETH temporal habitat. The next milestone may calibrate reference duration while keeping this temporal neighborhood fixed.')
    elif status == 'ETH_M1B_ANCHOR_SUPPORTED_BUT_ISOLATED':
        lines.append('Interpretation: 16:00 remains economically supported but does not satisfy the preregistered contiguous-width gate. Do not treat it as a stable temporal habitat yet.')
    else:
        lines.append('Interpretation: the coarse M1 16:00 winner did not survive the exact M1B local rescore gate. Do not proceed to downstream parameter calibration from this anchor.')

    lines += [
        '',
        'August remains diagnostic only and did not affect support.',
        'Research only. No exchange writes and no live BBC changes.',
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
