#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from collections import deque
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

PFX = 'ETH_B27DX_M1C_TIME_REFERENCE_TOPOLOGY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PROBES = ROOT / f'{PFX}_ProbeScores.csv'
OUT_CELLS = ROOT / f'{PFX}_CellSummary.csv'
OUT_COMPONENT = ROOT / f'{PFX}_AnchorComponent.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

HORIZON_MIN = 390
TARGET_EXT = 0.20
ENTRY_PROBES = (0.90, 0.85, 0.80)
STOP_F = 0.35
EXEC_GRID = tuple(range(14 * 60, 18 * 60 + 1, 30))
REF_GRID = tuple(range(240, 420 + 1, 30))
VAL_PARTS = ('external', 'reference_validation')
ALL_PARTS = ('development', 'external', 'reference_validation', 'august')
ANCHOR = (16 * 60, 330)


def probe_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def clock_label(minutes: int) -> str:
    m = int(minutes) % (24 * 60)
    return f'{m // 60:02d}:{m % 60:02d}'


def score_probe(x: pd.DataFrame, part: str, exec_min: int, ref_min: int, f: float) -> dict:
    r = b.score_config(
        x=x,
        part_name=part,
        side='LONG',
        exec_min=exec_min,
        ref_min=ref_min,
        horizon_min=HORIZON_MIN,
        entry_f=f,
        target_ext=TARGET_EXT,
        stop_f=STOP_F,
        stress_bps=0.0,
    )
    r['exec_min'] = int(exec_min)
    r['clock_utc'] = clock_label(exec_min)
    r['ref_min'] = int(ref_min)
    r['reference_start_min'] = int((exec_min - ref_min) % (24 * 60))
    r['reference_start_utc'] = clock_label(exec_min - ref_min)
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
    for exec_min in EXEC_GRID:
        for ref_min in REF_GRID:
            for part in ALL_PARTS:
                for f in ENTRY_PROBES:
                    rows.append(score_probe(x, part, exec_min, ref_min, f))
    return pd.DataFrame(rows)


def finite_pf_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors='coerce').replace([np.inf], 999999.0)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in EXEC_GRID:
        for ref_min in REF_GRID:
            row = {
                'exec_min': int(exec_min),
                'clock_utc': clock_label(exec_min),
                'ref_min': int(ref_min),
                'reference_start_min': int((exec_min - ref_min) % (24 * 60)),
                'reference_start_utc': clock_label(exec_min - ref_min),
            }
            dev = scores[(scores.exec_min == exec_min) & (scores.ref_min == ref_min) & (scores.partition == 'development')]
            row['development_positive_probes'] = int(dev.positive.sum())
            row['development_pass'] = bool(row['development_positive_probes'] >= 2)
            row['development_median_pf'] = float(finite_pf_series(dev.pf).median())
            row['development_median_expectancy'] = float(pd.to_numeric(dev.expectancy, errors='coerce').median())
            row['development_total_n'] = int(pd.to_numeric(dev.n, errors='coerce').sum())

            for part in VAL_PARTS:
                q = scores[(scores.exec_min == exec_min) & (scores.ref_min == ref_min) & (scores.partition == part)]
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


def anchor_component(summary: pd.DataFrame) -> pd.DataFrame:
    supported = {
        (int(r.exec_min), int(r.ref_min))
        for _, r in summary.loc[summary.supported].iterrows()
    }
    if ANCHOR not in supported:
        return summary.iloc[0:0].copy()

    q = deque([ANCHOR])
    seen = {ANCHOR}
    while q:
        e, r = q.popleft()
        for nxt in ((e - 30, r), (e + 30, r), (e, r - 30), (e, r + 30)):
            if nxt in supported and nxt not in seen:
                seen.add(nxt)
                q.append(nxt)

    comp = summary[
        summary.apply(lambda z: (int(z.exec_min), int(z.ref_min)) in seen, axis=1)
    ].copy()
    return comp.sort_values(['exec_min', 'ref_min']).reset_index(drop=True)


def fmt(x, nd=2):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.{nd}f}'


def support_matrix(summary: pd.DataFrame) -> list[str]:
    lines = []
    headers = [clock_label(e) for e in EXEC_GRID]
    lines.append('| Ref min | ' + ' | '.join(headers) + ' |')
    lines.append('|---:|' + '|'.join([':---:' for _ in headers]) + '|')
    for ref_min in REF_GRID:
        vals = []
        for exec_min in EXEC_GRID:
            r = summary[(summary.exec_min == exec_min) & (summary.ref_min == ref_min)].iloc[0]
            vals.append('✅' if bool(r.supported) else '·')
        lines.append(f"| {ref_min} | " + ' | '.join(vals) + ' |')
    return lines


def main():
    x, coverage = b.m.m.load5()
    scores = run_scores(x)
    scores.to_csv(OUT_PROBES, index=False)

    summary = summarize(scores)
    summary.to_csv(OUT_CELLS, index=False)

    component = anchor_component(summary)
    component.to_csv(OUT_COMPONENT, index=False)

    anchor_row = summary[(summary.exec_min == ANCHOR[0]) & (summary.ref_min == ANCHOR[1])].iloc[0]
    anchor_supported = bool(anchor_row.supported)
    n_cells = int(len(component))
    n_exec = int(component.exec_min.nunique()) if n_cells else 0
    n_ref = int(component.ref_min.nunique()) if n_cells else 0
    topology_supported = bool(anchor_supported and n_cells >= 3 and n_exec >= 2 and n_ref >= 2)

    if not anchor_supported:
        status = 'ETH_M1C_ANCHOR_NOT_SUPPORTED'
    elif topology_supported:
        status = 'ETH_M1C_TOPOLOGY_SUPPORTED'
    else:
        status = 'ETH_M1C_ANCHOR_SUPPORTED_NO_TOPOLOGY'

    lines = [
        '# ETH B27DX V2 — M1C Time × Reference Duration Topology — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        'M1C varies only execution clock and reference duration. B27DX causal grammar and M1 diagnostic economics remain frozen.',
        '',
        '## Supported-cell topology',
        '',
        'A checkmark means the cell independently passed Development, External, and Reference Validation using the frozen 2-of-3 probe gates.',
        '',
    ]
    lines += support_matrix(summary)
    lines += [
        '',
        '## Anchor component',
        '',
        f'Anchor `16:00 × R330` supported: **{"YES" if anchor_supported else "NO"}**.',
        f'Connected supported cells containing anchor: **{n_cells}**.',
        f'Distinct execution clocks in component: **{n_exec}**.',
        f'Distinct reference durations in component: **{n_ref}**.',
        '',
    ]

    if n_cells:
        lines += [
            '| Execution | Reference | Reference start | Dev + | Dev median PF | External + | Validation + |',
            '|---:|---:|---:|---:|---:|---:|---:|',
        ]
        for _, r in component.iterrows():
            lines.append(
                f"| {r.clock_utc} | {int(r.ref_min)} | {r.reference_start_utc} | "
                f"{int(r.development_positive_probes)}/3 | {fmt(r.development_median_pf)} | "
                f"{int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 |"
            )

        starts = component.reference_start_min.astype(int).tolist()
        # Circular concentration diagnostic using resultant length, with a simple representative circular mean.
        angles = np.asarray(starts, dtype=float) / (24 * 60) * 2 * np.pi
        z = np.exp(1j * angles).mean()
        concentration = float(abs(z))
        mean_angle = float(np.angle(z) % (2 * np.pi))
        mean_min = int(round(mean_angle / (2 * np.pi) * 24 * 60)) % (24 * 60)
        lines += [
            '',
            '### Reference-start diagnostic',
            '',
            f'Circular mean reference-start clock: **{clock_label(mean_min)} UTC**.',
            f'Circular concentration (0 diffuse → 1 identical): **{concentration:.3f}**.',
            'This diagnostic does not affect the preregistered support decision.',
        ]

    lines += [
        '',
        f'**Status: {status}**',
        '',
    ]

    if status == 'ETH_M1C_TOPOLOGY_SUPPORTED':
        lines.append('Interpretation: ETH shows a connected, multi-clock, multi-duration B27DX structural region. The next milestone may freeze this structural habitat and calibrate trade geometry inside it.')
    elif status == 'ETH_M1C_ANCHOR_SUPPORTED_NO_TOPOLOGY':
        lines.append('Interpretation: the original 16:00 × R330 anchor survives, but neighboring clock-duration combinations do not form a preregistered coherent 2D region. Do not sharpen entry/TP/SL around the isolated cell.')
    else:
        lines.append('Interpretation: the original M1/M1B anchor did not survive when embedded in the fixed 2D topology grid. Do not proceed from the prior anchor.')

    lines += [
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
