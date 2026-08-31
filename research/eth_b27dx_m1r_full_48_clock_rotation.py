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

PFX = 'ETH_B27DX_M1R_FULL_48_CLOCK_ROTATION'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PROBES = ROOT / f'{PFX}_ProbeScores.csv'
OUT_CLOCKS = ROOT / f'{PFX}_ClockSummary.csv'
OUT_SUPPORTED = ROOT / f'{PFX}_SupportedClocks.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_MIN = 330
HORIZON_MIN = 390
TARGET_EXT = 0.20
ENTRY_PROBES = (0.90, 0.85, 0.80)
STOP_F = 0.35
CLOCKS = tuple(range(0, 24 * 60, 30))
VAL_PARTS = ('external', 'reference_validation')
ALL_PARTS = ('development', 'external', 'reference_validation', 'august')
ANCHOR_MIN = 16 * 60


def probe_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def clock_label(v: int) -> str:
    return f'{(v // 60) % 24:02d}:{v % 60:02d}'


def reference_start_min(exec_min: int) -> int:
    return (exec_min - REF_MIN) % (24 * 60)


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
    r['execution_utc'] = clock_label(exec_min)
    rs = reference_start_min(exec_min)
    r['reference_start_min'] = int(rs)
    r['reference_start_utc'] = clock_label(rs)
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
    for exec_min in CLOCKS:
        for part in ALL_PARTS:
            for f in ENTRY_PROBES:
                rows.append(score_probe(x, part, exec_min, f))
    return pd.DataFrame(rows)


def finite_pf_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors='coerce').replace([np.inf], 999999.0)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in CLOCKS:
        row = {
            'exec_min': int(exec_min),
            'execution_utc': clock_label(exec_min),
            'reference_start_min': int(reference_start_min(exec_min)),
            'reference_start_utc': clock_label(reference_start_min(exec_min)),
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


def contiguous_runs(summary: pd.DataFrame) -> list[list[int]]:
    supported = sorted(int(v) for v in summary.loc[summary.supported, 'exec_min'])
    if not supported:
        return []
    runs = []
    cur = [supported[0]]
    for v in supported[1:]:
        if v - cur[-1] == 30:
            cur.append(v)
        else:
            runs.append(cur)
            cur = [v]
    runs.append(cur)
    # Merge midnight-wrapping support if both 23:30 and 00:00 are supported.
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == 1410:
        merged = runs[-1] + [v + 1440 for v in runs[0]]
        runs = [merged] + runs[1:-1]
    return runs


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
    supported = summary[summary.supported].copy()
    supported.to_csv(OUT_SUPPORTED, index=False)
    runs = contiguous_runs(summary)

    anchor = summary[summary.exec_min == ANCHOR_MIN].iloc[0]
    anchor_supported = bool(anchor.supported)
    half_hour_supported = supported[(supported.exec_min % 60) == 30]

    if supported.empty:
        status = 'ETH_M1R_NO_SUPPORTED_CLOCK'
    elif len(supported) == 1:
        status = 'ETH_M1R_SINGLE_ISOLATED_CLOCK_SUPPORTED'
    elif any(len(r) >= 2 for r in runs):
        status = 'ETH_M1R_MULTI_CLOCK_WITH_CONTIGUOUS_REGION'
    else:
        status = 'ETH_M1R_MULTIPLE_ISOLATED_CLOCKS_SUPPORTED'

    lines = [
        '# ETH B27DX V2 — M1R Full BTC-Parity 48-Clock Rotation — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        'M1R scans all 48 UTC execution-clock placements in 30-minute steps. Reference duration remains 330m and execution horizon 390m. B27DX causal grammar and M1 economics are frozen.',
        '',
        '## All 48 clock placements',
        '',
        '| Ref start | Exec start | Dev + | Dev median PF | Dev median exp | External + | Validation + | Supported |',
        '|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r.reference_start_utc} | {r.execution_utc} | {int(r.development_positive_probes)}/3 | "
            f"{fmt(r.development_median_pf)} | {fmt(r.development_median_expectancy)} | "
            f"{int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 | "
            f"{'YES' if bool(r.supported) else 'NO'} |"
        )

    lines += ['', '## Supported ETH clocks', '']
    if supported.empty:
        lines.append('None.')
    else:
        lines += [
            '| Ref start | Exec start | Dev + | Dev PF | External + | Validation + |',
            '|---:|---:|---:|---:|---:|---:|',
        ]
        for _, r in supported.iterrows():
            lines.append(
                f"| {r.reference_start_utc} | {r.execution_utc} | {int(r.development_positive_probes)}/3 | "
                f"{fmt(r.development_median_pf)} | {int(r.external_positive_probes)}/3 | "
                f"{int(r.reference_validation_positive_probes)}/3 |"
            )

    lines += ['', '## Contiguous supported 30-minute runs', '']
    if not runs:
        lines.append('None.')
    else:
        for i, run in enumerate(runs, 1):
            labels = [clock_label(v % 1440) for v in run]
            width = 30 * (len(run) - 1)
            lines.append(f'- Run {i}: **{" → ".join(labels)}** ({len(run)} clock points; first-to-last width {width} minutes).')

    lines += [
        '',
        '## Resolution audit',
        '',
        f'- Original 16:00 UTC M1 anchor supported: **{"YES" if anchor_supported else "NO"}**.',
        f'- Supported half-hour-only placements (`xx:30`) discovered by the parity scan: **{len(half_hour_supported)}**.',
    ]
    if len(half_hour_supported):
        lines.append('- Half-hour supported clocks: **' + ', '.join(half_hour_supported.execution_utc.astype(str)) + '**.')

    lines += [
        '',
        f'**Status: {status}**',
        '',
        'August remains diagnostic only and did not affect support.',
        'H/H2 remains telemetry only and is not an optimization target.',
        'Research only. No exchange writes and no live BBC changes.',
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
