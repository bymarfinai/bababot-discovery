#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
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
PFX = 'BNB_REFERENCE_END_0500_GRID_B27FP'
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
STARTS_MIN = (0, 30, 60, 90, 120, 150)
REF_END_MIN = 300  # 05:00 WIB
EXEC_END_MIN = 540  # 09:00 WIB
REPRO = {
    60: (1095, 162, 132),   # 01:00–05:00 inherited B27FO 4h cell
    120: (1095, 167, 135),  # 02:00–05:00 inherited B27FO 3h cell
}

OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def hm(minutes: int) -> str:
    return f'{(minutes // 60) % 24:02d}:{minutes % 60:02d}'


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds(day, start_min: int):
    start_local = datetime.combine(day, time(start_min // 60, start_min % 60), tzinfo=WIB)
    ref_end_local = datetime.combine(day, time(5, 0), tzinfo=WIB)
    exe_end_local = datetime.combine(day, time(9, 0), tzinfo=WIB)
    if not start_local < ref_end_local < exe_end_local:
        raise AssertionError(f'invalid fixed-boundary geometry day={day} start={hm(start_min)}')
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (start_local, ref_end_local, ref_end_local, exe_end_local))


def build_sessions(x5: pd.DataFrame, start_min: int) -> pd.DataFrame:
    rows = []
    expected_ref = (REF_END_MIN - start_min) // 5
    expected_exe = (EXEC_END_MIN - REF_END_MIN) // 5
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds(day, start_min)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != expected_ref or len(exe) != expected_exe:
            raise AssertionError(
                f'incomplete fixed-end session start={hm(start_min)} day={day}: '
                f'ref={len(ref)}/{expected_ref} exe={len(exe)}/{expected_exe}'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range start={hm(start_min)} day={day}')
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'start_min_wib': start_min,
            'start_wib': hm(start_min),
            'reference_end_wib': '05:00',
            'reference_duration_min': REF_END_MIN - start_min,
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
        raise AssertionError(f'sessions start={hm(start_min)}={len(result)} expected=1095')
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


def longest_contiguous_high(summary: pd.DataFrame):
    best = []
    cur = []
    for start_min in STARTS_MIN:
        r = summary.loc[summary.start_min_wib == start_min].iloc[0]
        high = int(r.causal_leave) >= 100 and float(r.h2_rate) >= .75
        if high:
            cur.append(start_min)
            if len(cur) > len(best):
                best = cur.copy()
        else:
            cur = []
    return best


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FP preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    details = []
    rows = []
    for start_min in STARTS_MIN:
        d = build_sessions(x5, start_min)
        details.append(d)
        m = metrics(d)
        rows.append({
            'start_min_wib': start_min,
            'start_wib': hm(start_min),
            'reference_end_wib': '05:00',
            'reference_duration_min': REF_END_MIN - start_min,
            **m,
        })

    detail = pd.concat(details, ignore_index=True)
    summary = pd.DataFrame(rows)

    # Mandatory inherited reproduction gates.
    for start_min, expected in REPRO.items():
        r = summary.loc[summary.start_min_wib == start_min].iloc[0]
        got = (int(r.sessions), int(r.causal_leave), int(r.h2))
        if got != expected:
            raise AssertionError(
                f'B27FO reproduction mismatch {hm(start_min)}–05:00 got={got} expected={expected}'
            )

    summary['high_strength'] = (
        (summary.causal_leave >= 100) & (summary.h2_rate >= .75)
    )
    best = longest_contiguous_high(summary)
    best_len = len(best)
    if best_len >= 4:
        classification = 'BROAD_0500_REFERENCE_END_ZONE'
    elif best_len < 3:
        classification = 'SHARP_START_PREFERENCE'
    else:
        classification = 'MIXED_0500_REFERENCE_END_ZONE'

    spread = float(summary.h2_rate.max() - summary.h2_rate.min())
    ranked = summary.sort_values(['h2_rate', 'causal_leave'], ascending=[False, False]).copy()

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    best_text = 'NONE' if not best else f'{hm(best[0])}–{hm(best[-1])} starts ({best_len} grid points)'

    lines = [
        '# BNB Fixed 05:00 WIB Reference-End Grid — B27FP', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Common normalized local-date universe: {COMMON_START} through {COMMON_END}',
        '- Complete sessions per cell: 1095',
        '- Reference end fixed at 05:00 WIB',
        '- Execution fixed at 05:00–09:00 WIB',
        '- Six preregistered reference starts: 00:00 through 02:30 in 30-minute steps',
        '- B27FO inherited reproduction gates: PASS',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used', '',
        '## 1. Fixed-end grid', '',
        '| Ref start | Ref duration | Reference window | Execution | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 | High strength |',
        '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for start_min in STARTS_MIN:
        r = summary.loc[summary.start_min_wib == start_min].iloc[0]
        dur = int(r.reference_duration_min)
        dur_label = f'{dur//60}h' if dur % 60 == 0 else f'{dur/60:.1f}h'
        lines.append(
            f"| {r.start_wib} | {dur_label} | {r.start_wib}–05:00 | 05:00–09:00 | "
            f"{int(r.k1_qualified)} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate)} | "
            f"{int(r.opposite_break_before_h2)} | {int(r.no_h2_by_end)} | {pct(r.resolved_h2_share,1)} | "
            f"{r.median_minutes_leave_to_h2:.1f}m | {'YES' if bool(r.high_strength) else 'NO'} |"
        )

    lines += ['', '## 2. Ranking', '', '| Rank | Reference | Leaves | H2 | H2/leave |', '|---:|---|---:|---:|---:|']
    for i, (_, r) in enumerate(ranked.iterrows(), 1):
        lines.append(
            f"| {i} | {r.start_wib}–05:00 | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate)} |"
        )

    lines += [
        '', '## 3. Frozen fixed-boundary diagnosis', '',
        '- HIGH_STRENGTH requires >=100 causal leaves and H2/leave >=75%.',
        f'- Longest contiguous HIGH_STRENGTH reference-start region: **{best_text}**',
        f'- Overall max-minus-min H2/leave spread: **{100*spread:.2f}pp**',
        f'- Frozen classification: **{classification}**',
        '', '## Interpretation boundary', '',
        'B27FP isolates a common 05:00 WIB reference-end and 05:00–09:00 WIB execution window while varying only how far backward the reference range begins.',
        '',
        'The six cells overlap heavily and are not independent samples. H2/leave is a structural outcome rate, not trading win rate, and no economic edge is established here.',
        '', f'**Status: B27FP_BNB_REFERENCE_END_0500_GRID_COMPLETE_{classification}**', '',
        'STOP: do not add start times, define an entry, TP/SL, weekday filter, or reveal holdout data inside B27FP.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text(
        f'B27FP_BNB_REFERENCE_END_0500_GRID_COMPLETE_{classification}\n',
        encoding='utf-8'
    )
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
