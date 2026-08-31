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

PFX = 'ETH_B27DX_M1_HABITAT_DISCOVERY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DEV = ROOT / f'{PFX}_Development.csv'
OUT_SEL = ROOT / f'{PFX}_Selected.csv'
OUT_VAL = ROOT / f'{PFX}_Validation.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_MIN = 330
HORIZON_MIN = 390
TARGET_EXT = 0.20
HOURS = tuple(range(24))
PROBES = {
    'LONG': (0.90, 0.85, 0.80),
    'SHORT': (0.10, 0.15, 0.20),
}
STOPS = {'LONG': 0.35, 'SHORT': 0.65}
VAL_PARTS = ('external', 'reference_validation')


def finite_pf(x: float) -> float:
    return 999999.0 if math.isinf(float(x)) else float(x)


def probe_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def score_probe(x: pd.DataFrame, part: str, side: str, hour: int, f: float) -> dict:
    r = b.score_config(
        x=x,
        part_name=part,
        side=side,
        exec_min=hour * 60,
        ref_min=REF_MIN,
        horizon_min=HORIZON_MIN,
        entry_f=f,
        target_ext=TARGET_EXT,
        stop_f=STOPS[side],
        stress_bps=0.0,
    )
    r['hour_utc'] = hour
    r['probe'] = probe_label(f)
    return r


def development_scan(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for side in ('LONG', 'SHORT'):
        for hour in HOURS:
            for f in PROBES[side]:
                r = score_probe(x, 'development', side, hour, f)
                r['positive_probe'] = bool(
                    r['n'] >= 30 and r['pf'] >= 1.10 and
                    r['expectancy'] > 0 and r['net'] > 0
                )
                rows.append(r)
    return pd.DataFrame(rows)


def select_habitats(dev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (side, hour), g in dev.groupby(['side', 'hour_utc'], sort=True):
        pfs = pd.to_numeric(g.pf, errors='coerce').replace([np.inf], 999999.0)
        exps = pd.to_numeric(g.expectancy, errors='coerce')
        rows.append({
            'side': side,
            'hour_utc': int(hour),
            'positive_probes': int(g.positive_probe.sum()),
            'median_pf': float(pfs.median()) if len(pfs) else np.nan,
            'median_expectancy': float(exps.median()) if len(exps) else np.nan,
            'total_n': int(pd.to_numeric(g.n).sum()),
            'development_pass': bool(int(g.positive_probe.sum()) >= 2),
        })
    s = pd.DataFrame(rows)
    s = s[s.development_pass].copy()
    if s.empty:
        return s
    s = s.sort_values(
        ['side', 'positive_probes', 'median_pf', 'median_expectancy', 'total_n'],
        ascending=[True, False, False, False, False],
    )
    return s.groupby('side', group_keys=False).head(4).reset_index(drop=True)


def validate(x: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    vals = []
    summaries = []
    for _, h in selected.iterrows():
        side = str(h.side)
        hour = int(h.hour_utc)
        for part in (*VAL_PARTS, 'august'):
            for f in PROBES[side]:
                r = score_probe(x, part, side, hour, f)
                r['validation_positive'] = bool(
                    r['n'] >= 15 and r['pf'] > 1.00 and
                    r['expectancy'] > 0 and r['net'] > 0
                ) if part in VAL_PARTS else False
                vals.append(r)

        ok = True
        detail = {}
        for part in VAL_PARTS:
            q = [z for z in vals if z['side'] == side and z['hour_utc'] == hour and z['partition'] == part]
            pos = sum(bool(z['validation_positive']) for z in q)
            enough_n = sum(int(z['n']) >= 15 for z in q)
            detail[f'{part}_positive_probes'] = int(pos)
            detail[f'{part}_n_probes'] = int(enough_n)
            ok = ok and pos >= 2 and enough_n >= 2
        summaries.append({
            'side': side,
            'hour_utc': hour,
            **detail,
            'm1_supported': bool(ok),
        })
    return pd.DataFrame(vals), pd.DataFrame(summaries)


def fmt(x, nd=2):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.{nd}f}'


def main():
    x, coverage = b.m.m.load5()
    dev = development_scan(x)
    dev.to_csv(OUT_DEV, index=False)

    selected = select_habitats(dev)
    selected.to_csv(OUT_SEL, index=False)

    if selected.empty:
        val = pd.DataFrame()
        summary = pd.DataFrame()
        status = 'ETH_M1_NO_DEVELOPMENT_HABITAT'
    else:
        val, summary = validate(x, selected)
        val.to_csv(OUT_VAL, index=False)
        selected = selected.merge(summary, on=['side', 'hour_utc'], how='left')
        selected.to_csv(OUT_SEL, index=False)
        status = 'ETH_M1_HABITAT_SUPPORTED' if bool(selected.m1_supported.any()) else 'ETH_M1_NO_VALIDATED_HABITAT'

    lines = [
        '# ETH B27DX V2 — M1 Habitat Discovery — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        'M1 varies UTC execution habitat only. H/H2 is not an optimization target.',
        '',
        '| Side | UTC habitat | Dev positive probes | Median PF | Median expectancy | External + probes | Validation + probes | M1 |',
        '|---|---:|---:|---:|---:|---:|---:|---|',
    ]
    if selected.empty:
        lines.append('| - | - | - | - | - | - | - | NO DEVELOPMENT HABITAT |')
    else:
        for _, r in selected.iterrows():
            lines.append(
                f"| {r.side} | {int(r.hour_utc):02d}:00 | {int(r.positive_probes)}/3 | "
                f"{fmt(r.median_pf)} | {fmt(r.median_expectancy)} | "
                f"{int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 | "
                f"{'SUPPORTED' if bool(r.m1_supported) else 'FAIL'} |"
            )
    lines += [
        '',
        f'**Status: {status}**',
        '',
        'M1 only selects time habitats. Reference duration, final entry geometry, target and invalidation remain for later milestones.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
