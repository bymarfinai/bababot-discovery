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
PFX = 'BNB_REFERENCE_DURATION_GRID_B27FO'
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
STARTS_MIN = (60, 90, 120)  # 01:00, 01:30, 02:00 WIB
DURATIONS_H = (3, 4, 5)
EXECUTION_H = 4
REPRO_4H = {
    60: (1095, 162, 132),
    90: (1095, 170, 133),
    120: (1095, 162, 126),
}
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_DURATION = ROOT / f'{PFX}_Duration_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def start_label(start_min: int) -> str:
    return f'{(start_min // 60) % 24:02d}:{start_min % 60:02d}'


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds(day, start_min: int, duration_h: int):
    hh = (start_min // 60) % 24
    mm = start_min % 60
    ref_start_local = datetime.combine(day, time(hh, mm), tzinfo=WIB)
    ref_end_local = ref_start_local + timedelta(hours=duration_h)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=EXECUTION_H)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_start_local, ref_end_local, exe_start_local, exe_end_local
    ))


def build_sessions(x5: pd.DataFrame, start_min: int, duration_h: int) -> pd.DataFrame:
    rows = []
    expected_ref = duration_h * 12
    expected_exe = EXECUTION_H * 12
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds(day, start_min, duration_h)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != expected_ref or len(exe) != expected_exe:
            raise AssertionError(
                f'incomplete geometry start={start_label(start_min)} dur={duration_h}h day={day}: '
                f'ref={len(ref)}/{expected_ref} exe={len(exe)}/{expected_exe}'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(
                f'nonpositive range start={start_label(start_min)} dur={duration_h}h day={day}'
            )
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'start_min_wib': start_min,
            'start_wib': start_label(start_min),
            'reference_duration_h': duration_h,
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
            f'sessions start={start_label(start_min)} dur={duration_h}h = {len(result)} expected=1095'
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
        'k1_rate': float(len(k) / len(d)) if len(d) else np.nan,
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
    # Mean is primary. Means within 0.25pp are treated as tied and use frozen tie-breakers.
    mean_gap = a['mean_h2_rate'] - b['mean_h2_rate']
    if abs(mean_gap) > 0.0025:
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
        raise AssertionError('B27FO preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    details = []
    summary_rows = []
    for duration_h in DURATIONS_H:
        for start_min in STARTS_MIN:
            d = build_sessions(x5, start_min, duration_h)
            details.append(d)
            m = metrics(d)
            summary_rows.append({
                'start_min_wib': start_min,
                'start_wib': start_label(start_min),
                'reference_duration_h': duration_h,
                **m,
            })

    detail = pd.concat(details, ignore_index=True)
    summary = pd.DataFrame(summary_rows)

    # Mandatory exact reproduction of the inherited 4h cells.
    for start_min, expected in REPRO_4H.items():
        r = summary[
            (summary.start_min_wib == start_min) &
            (summary.reference_duration_h == 4)
        ].iloc[0]
        got = (int(r.sessions), int(r.causal_leave), int(r.h2))
        if got != expected:
            raise AssertionError(
                f'B27FN 4h reproduction mismatch start={start_label(start_min)} got={got} expected={expected}'
            )

    duration_rows = []
    for duration_h in DURATIONS_H:
        g = summary[summary.reference_duration_h == duration_h].copy()
        if len(g) != 3:
            raise AssertionError(f'duration={duration_h}h expected 3 cells got {len(g)}')
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
            'mean_h2_rate': mean_rate,
            'min_h2_rate': min_rate,
            'max_h2_rate': max_rate,
            'spread': spread,
            'total_leaves': total_leaves,
            'total_h2': total_h2,
            'pooled_h2_rate_descriptive': pooled_rate,
            'stability_label': 'STABLE_DURATION' if stable else 'UNSTABLE_DURATION',
            'stable': stable,
        })

    duration_summary = pd.DataFrame(duration_rows)
    ranked = sorted(duration_rows, key=cmp_to_key(duration_cmp))
    top = ranked[0]
    runner = ranked[1]
    mean_gap = top['mean_h2_rate'] - runner['mean_h2_rate']
    stable_count = sum(bool(r['stable']) for r in duration_rows)

    if top['stable'] and mean_gap >= .02:
        classification = 'CLEAR_DURATION_PREFERENCE'
    elif stable_count >= 2 and mean_gap < .02:
        classification = 'DURATION_PLATEAU'
    else:
        classification = 'MIXED_DURATION_GEOMETRY'

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    duration_summary.to_csv(OUT_DURATION, index=False)

    lines = [
        '# BNB Reference-Duration Geometry Grid — B27FO', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Common normalized local-date universe: {COMMON_START} through {COMMON_END}',
        '- Complete sessions per geometry cell: 1095',
        '- Start zone frozen to 01:00 / 01:30 / 02:00 WIB',
        '- Tested reference durations: 3h / 4h / 5h',
        '- Execution duration fixed at 4h immediately after each reference window',
        '- B27FN 4h reproduction gates: PASS',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used', '',
        '## 1. Full 3 × 3 geometry grid', '',
        '| Start | Ref duration | Reference window | Execution window | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |',
        '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for duration_h in DURATIONS_H:
        for start_min in STARTS_MIN:
            r = summary[
                (summary.start_min_wib == start_min) &
                (summary.reference_duration_h == duration_h)
            ].iloc[0]
            start_dt = datetime(2000, 1, 1, start_min // 60, start_min % 60)
            ref_end_dt = start_dt + timedelta(hours=duration_h)
            exe_end_dt = ref_end_dt + timedelta(hours=EXECUTION_H)
            ref_window = f'{start_dt:%H:%M}–{ref_end_dt:%H:%M}'
            exe_window = f'{ref_end_dt:%H:%M}–{exe_end_dt:%H:%M}'
            lines.append(
                f"| {r.start_wib} | {duration_h}h | {ref_window} | {exe_window} | "
                f"{int(r.k1_qualified)} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate)} | "
                f"{int(r.opposite_break_before_h2)} | {int(r.no_h2_by_end)} | "
                f"{pct(r.resolved_h2_share,1)} | {r.median_minutes_leave_to_h2:.1f}m |"
            )

    lines += ['', '## 2. Duration-level structural summary', '',
              '| Rank | Ref duration | Mean H2/leave | Min | Max | Spread | Total leaves* | Total H2* | Pooled rate* | Stability |',
              '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for rank, r in enumerate(ranked, 1):
        lines.append(
            f"| {rank} | {r['duration_h']}h | {pct(r['mean_h2_rate'])} | {pct(r['min_h2_rate'])} | "
            f"{pct(r['max_h2_rate'])} | {100*r['spread']:.2f}pp | {r['total_leaves']} | {r['total_h2']} | "
            f"{pct(r['pooled_h2_rate_descriptive'])} | {r['stability_label']} |"
        )

    lines += [
        '',
        '\* Pooled counts/rates are descriptive only because start-time cells overlap heavily; they are not independent samples.',
        '', '## 3. Frozen duration classification', '',
        f"- Top-ranked duration: **{top['duration_h']}h**",
        f"- Runner-up duration: **{runner['duration_h']}h**",
        f"- Top-vs-runner mean gap: **{100*mean_gap:.2f}pp**",
        f"- Number of stable durations: **{stable_count}/3**",
        f"- Overall classification: **{classification}**",
        '', '## Interpretation boundary', '',
        'B27FO tests reference-duration geometry inside the frozen 01:00–02:00 WIB start zone. Because execution begins immediately after reference completion, changing reference duration also shifts the execution window; the result is a full geometry comparison, not a pure isolated-duration causal effect.',
        '',
        'H2/leave is a structural outcome rate, not a trading win rate. No economic edge is established here.',
        '', f'**Status: B27FO_BNB_REFERENCE_DURATION_GRID_COMPLETE_{classification}**', '',
        'STOP: do not define an entry, TP/SL, weekday filter, or reveal holdout data inside B27FO.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text(
        f'B27FO_BNB_REFERENCE_DURATION_GRID_COMPLETE_{classification}\n',
        encoding='utf-8'
    )
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
