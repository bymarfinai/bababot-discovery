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
PFX = 'BNB_HOUR01_TEMPORAL_ZONE_B27FN'
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
ANCHORS_MIN = (23*60, 23*60+30, 0, 30, 60, 90, 120, 150, 180)
KNOWN = {
    23*60: (1095, 145, 109),
    0: (1095, 137, 105),
    60: (1095, 162, 132),
    120: (1095, 162, 126),
    180: (1095, 142, 96),
}
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def label(anchor_min: int) -> str:
    return f'{(anchor_min // 60) % 24:02d}:{anchor_min % 60:02d}'


def fs(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds(day, anchor_min):
    hh = (anchor_min // 60) % 24
    mm = anchor_min % 60
    ref_local = datetime.combine(day, time(hh, mm), tzinfo=WIB)
    ref_end_local = ref_local + timedelta(hours=4)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=4)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_local, ref_end_local, exe_start_local, exe_end_local
    ))


def build_sessions(x5, anchor_min):
    rows = []
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds(day, anchor_min)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 48:
            raise AssertionError(
                f'incomplete session {label(anchor_min)} {day}: ref={len(ref)}/48 exe={len(exe)}/48'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range {label(anchor_min)} {day}')
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'anchor_min_wib': anchor_min,
            'anchor_wib': label(anchor_min),
            'local_date': str(day),
            'weekday': day.strftime('%A'),
            'reference_start_utc': ref_start,
            'reference_end_utc': ref_end,
            'execution_start_utc': exe_start,
            'execution_end_utc': exe_end,
            'H': H, 'L': L, 'R': R, **out,
        })
    d = pd.DataFrame(rows)
    if len(d) != 1095:
        raise AssertionError(f'{label(anchor_min)} sessions={len(d)} expected=1095')
    return d


def metrics(d):
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
        'k1_rate': len(k) / len(d),
        'causal_leave': int(len(lv)),
        'h2': h2,
        'opposite_break_before_h2': opp,
        'ambiguous_h2_vs_opposite': amb,
        'no_h2_by_end': no,
        'h2_rate': h2 / len(lv) if len(lv) else np.nan,
        'resolved_h2_share': h2 / resolved if resolved else np.nan,
        'median_minutes_leave_to_h2': float(med) if not pd.isna(med) else np.nan,
    }


def pct(x, dec=1):
    return '-' if pd.isna(x) else f'{100*float(x):.{dec}f}%'


def longest_high_strength(summary):
    qualifies = {
        int(r.anchor_min_wib): (
            int(r.causal_leave) >= 100 and float(r.h2_rate) >= 0.75
        ) for _, r in summary.iterrows()
    }
    ordered = list(ANCHORS_MIN)
    best = []
    cur = []
    for a in ordered:
        if qualifies[a]:
            cur.append(a)
            if len(cur) > len(best):
                best = cur.copy()
        else:
            cur = []
    return best


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FN preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw coverage below gate: {coverage:.6%}')

    details = []
    summary_rows = []
    for a in ANCHORS_MIN:
        d = build_sessions(x5, a)
        details.append(d)
        m = metrics(d)
        summary_rows.append({'anchor_min_wib': a, 'anchor_wib': label(a), **m})

    detail = pd.concat(details, ignore_index=True)
    summary = pd.DataFrame(summary_rows)

    # Exact reproduction gates for known whole-hour normalized anchors.
    for a, (exp_s, exp_lv, exp_h2) in KNOWN.items():
        r = summary.loc[summary.anchor_min_wib == a].iloc[0]
        got = (int(r.sessions), int(r.causal_leave), int(r.h2))
        exp = (exp_s, exp_lv, exp_h2)
        if got != exp:
            raise AssertionError(f'reproduction mismatch {label(a)} got={got} expected={exp}')

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    # Center-neighborhood diagnostics.
    center_anchors = [30, 60, 90]
    center = summary[summary.anchor_min_wib.isin(center_anchors)].copy()
    pooled_leaves = int(center.causal_leave.sum())
    pooled_h2 = int(center.h2.sum())
    pooled_rate = pooled_h2 / pooled_leaves
    mean_rate = float(center.h2_rate.mean())
    spread = float(center.h2_rate.max() - center.h2_rate.min())
    r0030 = float(summary.loc[summary.anchor_min_wib == 30, 'h2_rate'].iloc[0])
    r0100 = float(summary.loc[summary.anchor_min_wib == 60, 'h2_rate'].iloc[0])
    r0130 = float(summary.loc[summary.anchor_min_wib == 90, 'h2_rate'].iloc[0])
    n0030 = int(summary.loc[summary.anchor_min_wib == 30, 'causal_leave'].iloc[0])
    n0130 = int(summary.loc[summary.anchor_min_wib == 90, 'causal_leave'].iloc[0])

    robust = (
        n0030 >= 100 and n0130 >= 100 and
        r0030 >= .75 and r0130 >= .75 and
        mean_rate >= .78 and
        (r0100 - r0030) <= .075 and (r0100 - r0130) <= .075
    )
    boundary_sensitive = (
        r0030 < .70 or r0130 < .70 or
        (r0100 - r0030) > .10 or (r0100 - r0130) > .10
    )
    if robust:
        classification = 'ROBUST_TEMPORAL_ZONE'
    elif boundary_sensitive:
        classification = 'BOUNDARY_SENSITIVE'
    else:
        classification = 'MIXED_TEMPORAL_ZONE'

    best = longest_high_strength(summary)
    best_text = 'NONE' if not best else f'{label(best[0])}–{label(best[-1])} WIB ({len(best)} grid points)'

    chronological = summary.copy()
    chronological['chron_order'] = chronological.anchor_min_wib.map({
        1380: 0, 1410: 1, 0: 2, 30: 3, 60: 4, 90: 5, 120: 6, 150: 7, 180: 8
    })
    chronological = chronological.sort_values('chron_order')
    ranked = summary.sort_values(['h2_rate', 'causal_leave'], ascending=[False, False])

    lines = [
        '# BNB 01:00 WIB Temporal-Zone Refinement — B27FN', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Common normalized local-date universe: {COMMON_START} through {COMMON_END}',
        '- Complete sessions per anchor: 1095',
        '- Whole-hour B27FL reproduction gates: PASS',
        '- Grid: 23:00 through 03:00 WIB in 30-minute steps',
        '- Reference/execution geometry unchanged at 4h + 4h',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used', '',
        '## 1. Local sensitivity curve', '',
        '| Anchor | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in chronological.iterrows():
        lines.append(
            f"| {r.anchor_wib} | {int(r.k1_qualified)} | {int(r.causal_leave)} | {int(r.h2)} | "
            f"{pct(r.h2_rate,2)} | {int(r.opposite_break_before_h2)} | {int(r.no_h2_by_end)} | "
            f"{pct(r.resolved_h2_share,1)} | {r.median_minutes_leave_to_h2:.1f}m |"
        )

    lines += ['', '## 2. Ranking inside the preregistered neighborhood', '',
              '| Rank | Anchor | Leaves | H2 | H2/leave |',
              '|---:|---|---:|---:|---:|']
    for i, (_, r) in enumerate(ranked.iterrows(), 1):
        lines.append(f"| {i} | {r.anchor_wib} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate,2)} |")

    lines += ['', '## 3. Frozen center-neighborhood diagnostic', '',
              '| Anchor | Leaves | H2 | H2/leave |', '|---|---:|---:|---:|']
    for a in center_anchors:
        r = summary.loc[summary.anchor_min_wib == a].iloc[0]
        lines.append(f"| {r.anchor_wib} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate,2)} |")
    lines += [
        '',
        f'- Pooled 00:30/01:00/01:30: {pooled_h2}/{pooled_leaves} = {pct(pooled_rate,2)}',
        f'- Unweighted mean of three anchor rates: {pct(mean_rate,2)}',
        f'- Max-minus-min center spread: {100*spread:.2f}pp',
        f'- Frozen robustness classification: **{classification}**',
        '', '## 4. High-strength contiguous region', '',
        '- Definition: every grid point has >=100 causal leaves and H2/leave >=75%.',
        f'- Longest contiguous region: **{best_text}**',
        '', '## Interpretation boundary', '',
        'B27FN tests temporal robustness only. H2/leave is a structural outcome rate, not trading win rate. A robust zone does not establish an executable or profitable edge.',
        '', f'**Status: B27FN_BNB_TEMPORAL_ZONE_REFINEMENT_COMPLETE_{classification}**', '',
        'STOP: do not define an entry, alter reference-window length, select weekdays, or reveal holdout data inside B27FN.'
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text(f'B27FN_BNB_TEMPORAL_ZONE_REFINEMENT_COMPLETE_{classification}\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
