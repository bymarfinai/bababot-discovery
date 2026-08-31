#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
from functools import cmp_to_key
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em

TARGET = 'BNBUSDT'
WIB = ZoneInfo('Asia/Jakarta')
UTC = ZoneInfo('UTC')
PFX = 'BNB_EXECUTION_DURATION_GRID_B27FQ'
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
REF_STARTS_MIN = (60, 90, 120)  # 01:00, 01:30, 02:00 WIB
REF_END_MIN = 300  # 05:00 WIB
EXEC_DURATIONS_H = (3, 4, 5)
REPRO_4H = {
    60: (1095, 162, 132),
    90: (1095, 167, 137),
    120: (1095, 167, 135),
}

OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_DURATION = ROOT / f'{PFX}_Duration_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def hm(minutes: int) -> str:
    return f'{(minutes // 60) % 24:02d}:{minutes % 60:02d}'


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds(day, ref_start_min: int, exec_duration_h: int):
    ref_start_local = datetime.combine(
        day, time(ref_start_min // 60, ref_start_min % 60), tzinfo=WIB
    )
    ref_end_local = datetime.combine(day, time(5, 0), tzinfo=WIB)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=exec_duration_h)
    if not ref_start_local < ref_end_local < exe_end_local:
        raise AssertionError(
            f'invalid geometry day={day} ref_start={hm(ref_start_min)} exec={exec_duration_h}h'
        )
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_start_local, ref_end_local, exe_start_local, exe_end_local
    ))


def build_sessions(x5: pd.DataFrame, ref_start_min: int, exec_duration_h: int) -> pd.DataFrame:
    rows = []
    expected_ref = (REF_END_MIN - ref_start_min) // 5
    expected_exe = exec_duration_h * 12
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds(day, ref_start_min, exec_duration_h)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != expected_ref or len(exe) != expected_exe:
            raise AssertionError(
                f'incomplete geometry ref={hm(ref_start_min)}–05:00 exec={exec_duration_h}h day={day}: '
                f'ref={len(ref)}/{expected_ref} exe={len(exe)}/{expected_exe}'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(
                f'nonpositive range ref={hm(ref_start_min)}–05:00 day={day}'
            )
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'ref_start_min_wib': ref_start_min,
            'ref_start_wib': hm(ref_start_min),
            'reference_end_wib': '05:00',
            'execution_duration_h': exec_duration_h,
            'execution_start_wib': '05:00',
            'execution_end_wib': hm(REF_END_MIN + exec_duration_h * 60),
            'local_date': str(day),
            'weekday': day.strftime('%A'),
            'reference_start_utc': ref_start,
            'reference_end_utc': ref_end,
            'execution_start_utc': exe_start,
            'execution_end_utc': exe_end,
            'H': H,
            'L': L,
            'R': R,
            **out,
        })
    result = pd.DataFrame(rows)
    if len(result) != 1095:
        raise AssertionError(
            f'sessions ref={hm(ref_start_min)} exec={exec_duration_h}h={len(result)} expected=1095'
        )
    return result


def metrics(d: pd.DataFrame) -> dict:
    k = d[d.qualified.fillna(False).astype(bool)]
    lv = k[k.leave.fillna(False).astype(bool)]
    h2 = int((lv.terminal == 'H2_ARRIVAL').sum())
    opp = int((lv.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum())
    amb = int((lv.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum())
    no = int((lv.terminal == 'NO_H2_BY_END').sum())
    resolved = h2 + opp
    med = pd.to_numeric(
        lv.loc[lv.terminal == 'H2_ARRIVAL', 'minutes_leave_to_h2'], errors='coerce'
    ).median() if h2 else np.nan
    return {
        'sessions': int(len(d)),
        'k1_qualified': int(len(k)),
        'causal_leave': int(len(lv)),
        'h2': h2,
        'opposite_break_before_h2': opp,
        'ambiguous_h2_vs_opposite': amb,
        'no_h2_by_end': no,
        'h2_rate': float(h2 / len(lv)) if len(lv) else np.nan,
        'resolved_h2_share': float(h2 / resolved) if resolved else np.nan,
        'median_minutes_leave_to_h2': float(med) if not pd.isna(med) else np.nan,
    }


def pct(x, dec=2):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.{dec}f}%'


def duration_cmp(a: dict, b: dict) -> int:
    mean_gap = a['mean_h2_rate'] - b['mean_h2_rate']
    if abs(mean_gap) > .0025:
        return -1 if mean_gap > 0 else 1
    min_gap = a['min_h2_rate'] - b['min_h2_rate']
    if abs(min_gap) > 1e-12:
        return -1 if min_gap > 0 else 1
    spread_gap = a['spread'] - b['spread']
    if abs(spread_gap) > 1e-12:
        return -1 if spread_gap < 0 else 1
    leave_gap = a['total_leaves'] - b['total_leaves']
    if leave_gap:
        return -1 if leave_gap > 0 else 1
    return -1 if a['duration_h'] < b['duration_h'] else (1 if a['duration_h'] > b['duration_h'] else 0)


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FQ preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    details = []
    summary_rows = []
    for exec_duration_h in EXEC_DURATIONS_H:
        for ref_start_min in REF_STARTS_MIN:
            d = build_sessions(x5, ref_start_min, exec_duration_h)
            details.append(d)
            m = metrics(d)
            summary_rows.append({
                'ref_start_min_wib': ref_start_min,
                'ref_start_wib': hm(ref_start_min),
                'reference_end_wib': '05:00',
                'execution_duration_h': exec_duration_h,
                'execution_end_wib': hm(REF_END_MIN + exec_duration_h * 60),
                **m,
            })

    detail = pd.concat(details, ignore_index=True)
    summary = pd.DataFrame(summary_rows)

    # Mandatory B27FP reproduction gates for 4h execution.
    for ref_start_min, expected in REPRO_4H.items():
        r = summary[
            (summary.ref_start_min_wib == ref_start_min) &
            (summary.execution_duration_h == 4)
        ].iloc[0]
        got = (int(r.sessions), int(r.causal_leave), int(r.h2))
        if got != expected:
            raise AssertionError(
                f'B27FP 4h reproduction mismatch ref={hm(ref_start_min)}–05:00 '
                f'got={got} expected={expected}'
            )

    duration_rows = []
    for duration_h in EXEC_DURATIONS_H:
        g = summary[summary.execution_duration_h == duration_h].copy()
        if len(g) != 3:
            raise AssertionError(f'execution duration={duration_h}h expected 3 cells got={len(g)}')
        mean_rate = float(g.h2_rate.mean())
        min_rate = float(g.h2_rate.min())
        max_rate = float(g.h2_rate.max())
        spread = max_rate - min_rate
        total_leaves = int(g.causal_leave.sum())
        total_h2 = int(g.h2.sum())
        pooled_rate = total_h2 / total_leaves if total_leaves else np.nan
        stable = bool(
            (g.causal_leave >= 100).all() and
            mean_rate >= .75 and
            min_rate >= .725 and
            spread <= .075
        )
        duration_rows.append({
            'duration_h': duration_h,
            'execution_window': f'05:00–{hm(REF_END_MIN + duration_h*60)}',
            'mean_h2_rate': mean_rate,
            'min_h2_rate': min_rate,
            'max_h2_rate': max_rate,
            'spread': spread,
            'total_leaves': total_leaves,
            'total_h2': total_h2,
            'pooled_h2_rate_descriptive': pooled_rate,
            'stable': stable,
            'stability_label': 'STABLE_EXECUTION_DURATION' if stable else 'UNSTABLE_EXECUTION_DURATION',
        })

    duration_summary = pd.DataFrame(duration_rows)
    ranked = sorted(duration_rows, key=cmp_to_key(duration_cmp))
    top = ranked[0]
    runner = ranked[1]
    mean_gap = top['mean_h2_rate'] - runner['mean_h2_rate']
    stable_count = sum(bool(r['stable']) for r in duration_rows)

    if top['stable'] and mean_gap >= .02:
        classification = 'CLEAR_EXECUTION_DURATION_PREFERENCE'
    elif stable_count >= 2 and mean_gap < .02:
        classification = 'EXECUTION_DURATION_PLATEAU'
    else:
        classification = 'MIXED_EXECUTION_GEOMETRY'

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    duration_summary.to_csv(OUT_DURATION, index=False)

    lines = [
        '# BNB Execution-Duration Geometry Grid — B27FQ', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Common normalized local-date universe: {COMMON_START} through {COMMON_END}',
        '- Complete sessions per geometry cell: 1095',
        '- Reference end fixed at 05:00 WIB',
        '- Frozen reference starts: 01:00 / 01:30 / 02:00 WIB',
        '- Execution starts at 05:00 WIB',
        '- Tested execution durations: 3h / 4h / 5h',
        '- B27FP 4h execution reproduction gates: PASS',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used', '',
        '## 1. Full 3 × 3 execution-geometry grid', '',
        '| Reference | Execution | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for duration_h in EXEC_DURATIONS_H:
        for ref_start_min in REF_STARTS_MIN:
            r = summary[
                (summary.ref_start_min_wib == ref_start_min) &
                (summary.execution_duration_h == duration_h)
            ].iloc[0]
            lines.append(
                f"| {r.ref_start_wib}–05:00 | 05:00–{r.execution_end_wib} | "
                f"{int(r.k1_qualified)} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate)} | "
                f"{int(r.opposite_break_before_h2)} | {int(r.no_h2_by_end)} | "
                f"{pct(r.resolved_h2_share,1)} | {r.median_minutes_leave_to_h2:.1f}m |"
            )

    lines += ['', '## 2. Execution-duration structural summary', '',
              '| Rank | Execution | Mean H2/leave | Min | Max | Spread | Total leaves* | Total H2* | Pooled rate* | Stability |',
              '|---:|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for rank, r in enumerate(ranked, 1):
        lines.append(
            f"| {rank} | {r['execution_window']} | {pct(r['mean_h2_rate'])} | {pct(r['min_h2_rate'])} | "
            f"{pct(r['max_h2_rate'])} | {100*r['spread']:.2f}pp | {r['total_leaves']} | {r['total_h2']} | "
            f"{pct(r['pooled_h2_rate_descriptive'])} | {r['stability_label']} |"
        )

    lines += [
        '',
        '\* Pooled counts/rates are descriptive only because the three reference ranges overlap heavily and are not independent samples.',
        '', '## 3. Frozen execution-duration classification', '',
        f"- Top-ranked execution duration: **{top['duration_h']}h ({top['execution_window']})**",
        f"- Runner-up: **{runner['duration_h']}h ({runner['execution_window']})**",
        f"- Top-vs-runner mean gap: **{100*mean_gap:.2f}pp**",
        f"- Number of stable execution durations: **{stable_count}/3**",
        f"- Overall classification: **{classification}**",
        '', '## Interpretation boundary', '',
        'B27FQ compares full execution geometries. Changing execution duration changes both the time available to form a causal leave and the time available for H2/opposite/no-H2 resolution.',
        '',
        'H2/leave is a structural outcome rate, not trading win rate. No economic edge is established here.',
        '', f'**Status: B27FQ_BNB_EXECUTION_DURATION_GRID_COMPLETE_{classification}**', '',
        'STOP: temporal exploration ends here. Do not add clock/range variants, define TP/SL, select weekdays, or reveal holdout data inside B27FQ.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text(
        f'B27FQ_BNB_EXECUTION_DURATION_GRID_COMPLETE_{classification}\n',
        encoding='utf-8'
    )
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
