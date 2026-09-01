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

PFX = 'ETH_B27DX_S5A_ZONE_NATIVE_TARGET_GEOMETRY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_SCORES = ROOT / f'{PFX}_Scores.csv'
OUT_ROBUST = ROOT / f'{PFX}_RobustTargets.csv'
OUT_ZONES = ROOT / f'{PFX}_ZoneSummary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_MIN = 300
HORIZON_MIN = 360
STOP_F = 0.35
ZONES = {
    300: 0.80,   # 05:00
    540: 0.80,   # 09:00
    600: 0.75,   # 10:00
    960: 0.90,   # 16:00
}
TARGETS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
PARTS = ('development', 'external', 'reference_validation')
BTC_WR = 0.719298
BTC_PF = 2.223193
BTC_EXP = 1.26


def clock_label(v: int) -> str:
    return f'{(v // 60) % 24:02d}:{v % 60:02d}'


def f_label(v: float) -> str:
    return f'F{int(round(v * 100)):02d}'


def e_label(v: float) -> str:
    return f'E{int(round(v * 100)):02d}'


def finite(v):
    if pd.isna(v):
        return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)


def positive(part: str, r: dict) -> bool:
    if part == 'development':
        return bool(r['n'] >= 30 and r['pf'] >= 1.10 and r['expectancy'] > 0 and r['net'] > 0)
    return bool(r['n'] >= 15 and r['pf'] > 1.00 and r['expectancy'] > 0 and r['net'] > 0)


def dev_weeks() -> float:
    a, z = b.m.m.PARTS['development']
    return float((z - a) / pd.Timedelta(days=7))


def run_scores(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exec_min, entry_f in ZONES.items():
        for target_ext in TARGETS:
            for part in PARTS:
                r = b.score_config(
                    x=x,
                    part_name=part,
                    side='LONG',
                    exec_min=exec_min,
                    ref_min=REF_MIN,
                    horizon_min=HORIZON_MIN,
                    entry_f=entry_f,
                    target_ext=target_ext,
                    stop_f=STOP_F,
                    stress_bps=0.0,
                )
                r['execution_utc'] = clock_label(exec_min)
                r['entry'] = f_label(entry_f)
                r['target'] = e_label(target_ext)
                r['positive'] = positive(part, r)
                rows.append(r)
    return pd.DataFrame(rows)


def contiguous_runs(vals: list[float]) -> list[list[float]]:
    vals = sorted(vals)
    if not vals:
        return []
    out = []
    cur = [vals[0]]
    for v in vals[1:]:
        if abs((v - cur[-1]) - 0.05) < 1e-9:
            cur.append(v)
        else:
            out.append(cur)
            cur = [v]
    out.append(cur)
    return out


def upper_median(run: list[float]) -> float:
    s = sorted(run)
    return float(s[len(s) // 2])


def select_family(runs: list[list[float]]) -> list[float] | None:
    eligible = [r for r in runs if len(r) >= 2]
    if not eligible:
        return None
    max_len = max(len(r) for r in eligible)
    tied = [r for r in eligible if len(r) == max_len]
    tied.sort(key=lambda r: upper_median(r))  # conservative smaller median target
    return tied[0]


def summarize(scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    robust_rows = []
    zone_rows = []
    weeks = dev_weeks()

    for exec_min, entry_f in ZONES.items():
        robust_targets = []
        for te in TARGETS:
            q = scores[(scores.exec_min == exec_min) & (scores.target_ext == te)]
            ok = len(q) == 3 and all(bool(q.loc[q.partition == p, 'positive'].iloc[0]) for p in PARTS)
            if ok:
                robust_targets.append(te)
                robust_rows.append({
                    'exec_min': exec_min,
                    'execution_utc': clock_label(exec_min),
                    'entry_f': entry_f,
                    'entry': f_label(entry_f),
                    'target_ext': te,
                    'target': e_label(te),
                })

        runs = contiguous_runs(robust_targets)
        family = select_family(runs)
        representative = upper_median(family) if family else np.nan

        row = {
            'exec_min': exec_min,
            'execution_utc': clock_label(exec_min),
            'entry_f': entry_f,
            'entry': f_label(entry_f),
            'robust_targets': ','.join(e_label(v) for v in robust_targets),
            'robust_target_count': len(robust_targets),
            'target_runs': ' | '.join('→'.join(e_label(v) for v in r) for r in runs) if runs else '',
            'has_target_family': family is not None,
            'selected_family': '→'.join(e_label(v) for v in family) if family else '',
            'representative_target_ext': representative,
            'representative_target': e_label(representative) if not pd.isna(representative) else '',
        }

        if family:
            q = scores[(scores.exec_min == exec_min) & (scores.target_ext == representative)]
            for p in PARTS:
                r = q[q.partition == p].iloc[0]
                row[f'{p}_n'] = int(r.n)
                row[f'{p}_wr'] = float(r.wr)
                row[f'{p}_pf'] = finite(r.pf)
                row[f'{p}_expectancy'] = float(r.expectancy)
                row[f'{p}_net'] = float(r.net)
            row['development_opportunities_per_week'] = row['development_n'] / weeks
            row['median_major_wr'] = float(np.median([row[f'{p}_wr'] for p in PARTS]))
            row['median_major_pf'] = float(np.median([row[f'{p}_pf'] for p in PARTS]))
            row['median_major_expectancy'] = float(np.median([row[f'{p}_expectancy'] for p in PARTS]))
            row['btc_wr_gap_pp'] = 100.0 * (row['median_major_wr'] - BTC_WR)
            row['btc_pf_gap'] = row['median_major_pf'] - BTC_PF
            row['btc_exp_gap'] = row['median_major_expectancy'] - BTC_EXP
        else:
            row['development_opportunities_per_week'] = np.nan
            row['median_major_wr'] = np.nan
            row['median_major_pf'] = np.nan
            row['median_major_expectancy'] = np.nan
            row['btc_wr_gap_pp'] = np.nan
            row['btc_pf_gap'] = np.nan
            row['btc_exp_gap'] = np.nan
        zone_rows.append(row)

    return pd.DataFrame(zone_rows), pd.DataFrame(robust_rows)


def fmt(v, nd=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100 * float(v):.1f}%'


def main():
    x, coverage = b.m.m.load5()
    scores = run_scores(x)
    scores.to_csv(OUT_SCORES, index=False)
    zones, robust = summarize(scores)
    zones.to_csv(OUT_ZONES, index=False)
    robust.to_csv(OUT_ROBUST, index=False)

    n_families = int(zones.has_target_family.sum())
    if n_families == len(ZONES):
        status = 'ETH_S5A_ALL_ZONES_TARGET_FAMILIES_SUPPORTED'
    elif n_families > 0:
        status = 'ETH_S5A_PARTIAL_ZONE_TARGET_FAMILIES_SUPPORTED'
    else:
        status = 'ETH_S5A_NO_ZONE_TARGET_FAMILY'

    lines = [
        '# ETH B27DX — S5A Zone-Native Entry Freeze + Target Geometry — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        'Frozen lifecycle: **R300/X360**. Each clock uses its S2-predeclared zone-native entry. F35 completed-close invalidation remains fixed. Only target extension varies.',
        '',
        '## Zone-native target families',
        '',
        '| Clock | Entry | Robust targets | Selected family | Representative | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Dev opp/wk |',
        '|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in zones.itertuples(index=False):
        if bool(r.has_target_family):
            lines.append(
                f'| {r.execution_utc} | {r.entry} | {r.robust_targets or "-"} | {r.selected_family} | {r.representative_target} | '
                f'{pct(r.development_wr)} | {fmt(r.development_pf)} | {pct(r.external_wr)} | {fmt(r.external_pf)} | '
                f'{pct(r.reference_validation_wr)} | {fmt(r.reference_validation_pf)} | {fmt(r.development_opportunities_per_week,3)} |'
            )
        else:
            lines.append(f'| {r.execution_utc} | {r.entry} | {r.robust_targets or "-"} | - | - | - | - | - | - | - | - | - |')

    lines += ['', '## Full robust target map', '']
    if robust.empty:
        lines.append('None.')
    else:
        lines += ['| Clock | Entry | Target |', '|---:|---:|---:|']
        for r in robust.sort_values(['exec_min', 'target_ext']).itertuples(index=False):
            lines.append(f'| {r.execution_utc} | {r.entry} | {r.target} |')

    lines += [
        '',
        '## BTC benchmark diagnostic',
        '',
        '- BTC B27DX LONG final: WR 71.9%, PF 2.22, expectancy +$1.26/trade.',
        '- S5A freezes target representatives by family topology, not by maximum performance.',
        '',
        '## Decision',
        '',
        f'**Status: {status}**',
        '',
        '- No per-clock entry reselection, stop, runner, leverage, lifecycle, clock, or live-code changes were made.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
