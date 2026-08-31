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

PFX = 'ETH_B27DX_M1R_FAST_PARITY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PROBES = ROOT / f'{PFX}_ProbeScores.csv'
OUT_CLOCKS = ROOT / f'{PFX}_ClockSummary.csv'
OUT_SUPPORTED = ROOT / f'{PFX}_SupportedClocks.csv'
OUT_PARITY = ROOT / f'{PFX}_Parity.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_MIN = 330
HORIZON_MIN = 390
TARGET_EXT = 0.20
ENTRY_PROBES = (0.90, 0.85, 0.80)
STOP_F = 0.35
CLOCKS = tuple(range(0, 24 * 60, 30))
PARTS = ('external', 'development', 'reference_validation', 'august')
VAL_PARTS = ('external', 'reference_validation')
BAR5 = pd.Timedelta(minutes=5)
ANCHOR_MIN = 16 * 60


def clock_label(v: int) -> str:
    return f'{(v // 60) % 24:02d}:{v % 60:02d}'


def probe_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def ref_start_min(exec_min: int) -> int:
    return (exec_min - REF_MIN) % 1440


def metrics_from_rows(q: pd.DataFrame) -> dict:
    if q.empty:
        return {'n': 0, 'wins': 0, 'wr': np.nan, 'pf': np.nan, 'expectancy': np.nan, 'net': 0.0, 'max_ls': 0}
    return b.metrics(pd.to_numeric(q.pnl, errors='coerce').dropna().tolist())


def build_trade_rows(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    start = b.m.m.START.normalize()
    end = b.m.m.END.normalize()
    for day in pd.date_range(start, end, freq='D', tz='UTC'):
        for exec_min in CLOCKS:
            es = day + pd.Timedelta(minutes=exec_min)
            part = b.m.m.part(es)
            if part not in PARTS or es.weekday() >= 5:
                continue
            rs = es - pd.Timedelta(minutes=REF_MIN)
            ee = es + pd.Timedelta(minutes=HORIZON_MIN)
            if rs < b.m.m.START or ee >= b.m.m.END:
                continue
            ref = b.fast_slice(x, rs, es)
            exe = b.fast_slice(x, es, ee)
            if len(ref) != REF_MIN // 5 or len(exe) != HORIZON_MIN // 5:
                continue
            H = float(ref.high.max()); L = float(ref.low.min())
            if not H > L:
                continue
            w = b.m.corrected_find_window(exe, H, L, 'LONG')
            if w is None or not bool(w.get('clean', False)):
                continue
            for f in ENTRY_PROBES:
                ep = b.entry_level(L, H, f)
                fill = b.find_fill(exe, w, ep)
                if fill is None:
                    continue
                target = b.target_level(L, H, 'LONG', TARGET_EXT)
                stop = b.stop_level(L, H, STOP_F)
                out = b.score_trade(x, exe, fill, ee, 'LONG', ep, target, stop, 0.0)
                if out is None:
                    continue
                pnl, reason = out
                rows.append({
                    'partition': part,
                    'exec_min': int(exec_min),
                    'execution_utc': clock_label(exec_min),
                    'reference_start_min': int(ref_start_min(exec_min)),
                    'reference_start_utc': clock_label(ref_start_min(exec_min)),
                    'entry_f': float(f),
                    'probe': probe_label(f),
                    'pnl': float(pnl),
                    'reason': reason,
                })
    return pd.DataFrame(rows)


def aggregate(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in CLOCKS:
        for part in PARTS:
            for f in ENTRY_PROBES:
                q = trades[(trades.exec_min == exec_min) & (trades.partition == part) & np.isclose(trades.entry_f, f)]
                d = metrics_from_rows(q)
                positive = False
                if part == 'development':
                    positive = bool(d['n'] >= 30 and d['pf'] >= 1.10 and d['expectancy'] > 0 and d['net'] > 0)
                elif part in VAL_PARTS:
                    positive = bool(d['n'] >= 15 and d['pf'] > 1.00 and d['expectancy'] > 0 and d['net'] > 0)
                rows.append({
                    **d,
                    'partition': part,
                    'side': 'LONG',
                    'exec_min': int(exec_min),
                    'execution_utc': clock_label(exec_min),
                    'reference_start_min': int(ref_start_min(exec_min)),
                    'reference_start_utc': clock_label(ref_start_min(exec_min)),
                    'ref_min': REF_MIN,
                    'horizon_min': HORIZON_MIN,
                    'entry_f': float(f),
                    'target_ext': TARGET_EXT,
                    'stop_f': STOP_F,
                    'probe': probe_label(f),
                    'positive': positive,
                })
    return pd.DataFrame(rows)


def close(a, z, tol=1e-9):
    if pd.isna(z): return pd.isna(a)
    if math.isinf(float(z)): return math.isinf(float(a)) and ((float(a) > 0) == (float(z) > 0))
    return abs(float(a) - float(z)) <= tol * max(1.0, abs(float(z)))


def parity_check(x: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fields = ('n', 'wins', 'wr', 'pf', 'expectancy', 'net', 'max_ls')
    for part in PARTS:
        for f in ENTRY_PROBES:
            expected = b.score_config(
                x=x, part_name=part, side='LONG', exec_min=ANCHOR_MIN,
                ref_min=REF_MIN, horizon_min=HORIZON_MIN, entry_f=f,
                target_ext=TARGET_EXT, stop_f=STOP_F, stress_bps=0.0,
            )
            actual = scores[(scores.exec_min == ANCHOR_MIN) & (scores.partition == part) & np.isclose(scores.entry_f, f)].iloc[0]
            for field in fields:
                a = actual[field]; z = expected[field]
                ok = int(a) == int(z) if field in ('n', 'wins', 'max_ls') else close(a, z)
                rows.append({'partition': part, 'probe': probe_label(f), 'field': field, 'fast': a, 'original': z, 'pass': bool(ok)})
    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('M1R fast/original scorer parity failed:\n' + out[~out['pass']].to_string(index=False))
    return out


def finite_pf(s):
    return pd.to_numeric(s, errors='coerce').replace([np.inf], 999999.0)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min in CLOCKS:
        row = {'exec_min': exec_min, 'execution_utc': clock_label(exec_min), 'reference_start_min': ref_start_min(exec_min), 'reference_start_utc': clock_label(ref_start_min(exec_min))}
        dev = scores[(scores.exec_min == exec_min) & (scores.partition == 'development')]
        row['development_positive_probes'] = int(dev.positive.sum())
        row['development_pass'] = bool(row['development_positive_probes'] >= 2)
        row['development_median_pf'] = float(finite_pf(dev.pf).median())
        row['development_median_expectancy'] = float(pd.to_numeric(dev.expectancy).median())
        row['development_total_n'] = int(pd.to_numeric(dev.n).sum())
        for part in VAL_PARTS:
            q = scores[(scores.exec_min == exec_min) & (scores.partition == part)]
            pos = int(q.positive.sum())
            enough = int((pd.to_numeric(q.n) >= 15).sum())
            row[f'{part}_positive_probes'] = pos
            row[f'{part}_n_probes'] = enough
            row[f'{part}_pass'] = bool(pos >= 2 and enough >= 2)
        row['supported'] = bool(row['development_pass'] and row['external_pass'] and row['reference_validation_pass'])
        rows.append(row)
    return pd.DataFrame(rows)


def contiguous_runs(summary: pd.DataFrame) -> list[list[int]]:
    s = sorted(int(v) for v in summary.loc[summary.supported, 'exec_min'])
    if not s: return []
    runs = [[s[0]]]
    for v in s[1:]:
        if v - runs[-1][-1] == 30: runs[-1].append(v)
        else: runs.append([v])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == 1410:
        runs = [runs[-1] + [x + 1440 for x in runs[0]]] + runs[1:-1]
    return runs


def fmt(x, nd=2):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.{nd}f}'


def main():
    x, coverage = b.m.m.load5()
    trades = build_trade_rows(x)
    scores = aggregate(trades)
    parity = parity_check(x, scores)
    parity.to_csv(OUT_PARITY, index=False)
    scores.to_csv(OUT_PROBES, index=False)
    summary = summarize(scores)
    summary.to_csv(OUT_CLOCKS, index=False)
    supported = summary[summary.supported].copy()
    supported.to_csv(OUT_SUPPORTED, index=False)
    runs = contiguous_runs(summary)
    half = supported[supported.exec_min % 60 == 30]
    anchor = bool(summary.loc[summary.exec_min == ANCHOR_MIN, 'supported'].iloc[0])

    if supported.empty: status = 'ETH_M1R_NO_SUPPORTED_CLOCK'
    elif len(supported) == 1: status = 'ETH_M1R_SINGLE_ISOLATED_CLOCK_SUPPORTED'
    elif any(len(r) >= 2 for r in runs): status = 'ETH_M1R_MULTI_CLOCK_WITH_CONTIGUOUS_REGION'
    else: status = 'ETH_M1R_MULTIPLE_ISOLATED_CLOCKS_SUPPORTED'

    lines = [
        '# ETH B27DX V2 — M1R Full BTC-Parity 48-Clock Rotation — Fast Parity Result','',
        f'ETH raw 5m coverage: **{coverage:.4%}**.','',
        '**Fast/original scorer parity at 16:00 across all partitions and F90/F85/F80: PASS.**','',
        'The acceleration only reuses one causal window per clock/day across the three frozen entry probes. Rules and support gates are unchanged from the M1R preregistration.','',
        '## All 48 clock placements','',
        '| Ref start | Exec start | Dev + | Dev median PF | Dev median exp | External + | Validation + | Supported |',
        '|---:|---:|---:|---:|---:|---:|---:|---|'
    ]
    for _, r in summary.iterrows():
        lines.append(f"| {r.reference_start_utc} | {r.execution_utc} | {int(r.development_positive_probes)}/3 | {fmt(r.development_median_pf)} | {fmt(r.development_median_expectancy)} | {int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 | {'YES' if bool(r.supported) else 'NO'} |")
    lines += ['', '## Supported ETH clocks','']
    if supported.empty: lines.append('None.')
    else:
        lines += ['| Ref start | Exec start | Dev + | Dev PF | External + | Validation + |','|---:|---:|---:|---:|---:|---:|']
        for _, r in supported.iterrows():
            lines.append(f"| {r.reference_start_utc} | {r.execution_utc} | {int(r.development_positive_probes)}/3 | {fmt(r.development_median_pf)} | {int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 |")
    lines += ['', '## Contiguous supported 30-minute runs','']
    if not runs: lines.append('None.')
    else:
        for i, run in enumerate(runs,1):
            labels = [clock_label(v % 1440) for v in run]
            lines.append(f'- Run {i}: **{" → ".join(labels)}** ({len(run)} points; first-to-last width {30*(len(run)-1)} minutes).')
    lines += ['', '## Resolution audit','',
              f'- Original 16:00 anchor supported: **{"YES" if anchor else "NO"}**.',
              f'- Supported half-hour (`xx:30`) placements: **{len(half)}**.']
    if len(half): lines.append('- Half-hour supported clocks: **' + ', '.join(half.execution_utc.astype(str)) + '**.')
    lines += ['', f'**Status: {status}**','',
              'August remains diagnostic only and did not affect support.',
              'H/H2 remains telemetry only and is not an optimization target.',
              'Research only. No exchange writes and no live BBC changes.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__ == '__main__': main()
