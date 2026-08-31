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
DEV_START = pd.Timestamp('2022-01-01 00:00:00', tz='UTC')
DEV_END = pd.Timestamp('2025-01-01 00:00:00', tz='UTC')
ANCHORS = (14, 15, 16, 17)
PFX = 'BNB_HOURLY_SWEEP_B27FI'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

PRIOR = [
    (0, 137, 105),
    (1, 162, 132),
    (2, 162, 126),
    (3, 142, 96),
    (4, 142, 108),
    (5, 141, 94),
    (6, 148, 104),
    (7, 149, 114),
    (8, 143, 113),
    (9, 161, 118),
    (10, 175, 136),
    (11, 159, 120),
    (12, 161, 117),
    (13, 183, 139),
]


def fs(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds_for_local_day(day, anchor_hour):
    ref_start_local = datetime.combine(day, time(anchor_hour, 0), tzinfo=WIB)
    ref_end_local = ref_start_local + timedelta(hours=4)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=4)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (ref_start_local, ref_end_local, exe_start_local, exe_end_local))


def build_sessions(x5, anchor_hour):
    rows = []
    local_first = DEV_START.tz_convert(WIB).date() - timedelta(days=1)
    local_last = DEV_END.tz_convert(WIB).date() + timedelta(days=1)
    for d in pd.date_range(local_first, local_last, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds_for_local_day(day, anchor_hour)
        if ref_start < DEV_START or exe_end > DEV_END:
            continue
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 48:
            raise AssertionError(
                f'incomplete B27FI session anchor={anchor_hour:02d} day={day}: '
                f'ref={len(ref)}/48 exe={len(exe)}/48'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range anchor={anchor_hour:02d} day={day}: H={H} L={L}')
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'anchor_hour_wib': anchor_hour,
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
    d = pd.DataFrame(rows)
    if d.empty:
        raise AssertionError(f'no B27FI sessions for anchor {anchor_hour:02d}')
    return d


def metrics(q):
    sessions = int(len(q))
    k = q[q.qualified.fillna(False).astype(bool)] if sessions else q
    lv = k[k.leave.fillna(False).astype(bool)] if len(k) else k
    h2 = int((lv.terminal == 'H2_ARRIVAL').sum()) if len(lv) else 0
    opp = int((lv.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum()) if len(lv) else 0
    amb = int((lv.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()) if len(lv) else 0
    no = int((lv.terminal == 'NO_H2_BY_END').sum()) if len(lv) else 0
    resolved = h2 + opp
    med = pd.to_numeric(
        lv.loc[lv.terminal == 'H2_ARRIVAL', 'minutes_leave_to_h2'], errors='coerce'
    ).median() if h2 else np.nan
    return {
        'sessions': sessions,
        'k1_qualified': int(len(k)),
        'k1_rate': float(len(k) / sessions) if sessions else np.nan,
        'causal_leave': int(len(lv)),
        'leave_rate': float(len(lv) / len(k)) if len(k) else np.nan,
        'h2': h2,
        'opposite_break_before_h2': opp,
        'ambiguous_h2_vs_opposite': amb,
        'no_h2_by_end': no,
        'h2_rate': float(h2 / len(lv)) if len(lv) else np.nan,
        'resolved_h2_share': float(h2 / resolved) if resolved else np.nan,
        'median_minutes_leave_to_h2': float(med) if not pd.isna(med) else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def label_for(m):
    if m['causal_leave'] >= 100 and m['h2_rate'] >= .70:
        return 'STRONG_STRUCTURAL'
    if m['causal_leave'] >= 60 and m['h2_rate'] >= .65:
        return 'PROMISING_STRUCTURAL'
    return 'WEAK_STRUCTURAL'


def main():
    if not (ROOT / f'{PFX}_Preregistration.md').exists():
        raise AssertionError('B27FI preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    details = []
    pooled_by_anchor = {}
    summary_rows = []
    weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

    for anchor in ANCHORS:
        d = build_sessions(x5, anchor)
        details.append(d)
        pooled = metrics(d)
        pooled_by_anchor[anchor] = pooled
        summary_rows.append({
            'anchor_hour_wib': anchor,
            'scope': 'POOLED',
            'label': label_for(pooled),
            **pooled,
        })
        for wd in weekdays:
            m = metrics(d[d.weekday == wd])
            summary_rows.append({
                'anchor_hour_wib': anchor,
                'scope': wd,
                'label': '',
                **m,
            })

    detail = pd.concat(details, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    all_clock_rows = [(h, lv, h2, h2 / lv) for h, lv, h2 in PRIOR]
    for h in ANCHORS:
        m = pooled_by_anchor[h]
        all_clock_rows.append((h, m['causal_leave'], m['h2'], m['h2_rate']))
    leader_h, leader_lv, leader_h2, leader_rate = max(all_clock_rows, key=lambda x: x[3])

    lines = [
        '# BNB Hourly Structural Sweep — B27FI', '',
        '**Anchors tested together under one preregistration:** 14:00, 15:00, 16:00, 17:00 WIB.', '',
        '- Each anchor uses a 4h reference window followed by a 4h execution window',
        '- Development only: 2022-01-01 through 2025-01-01 UTC',
        f'- Raw loader coverage: {coverage:.4%}',
        '- Frozen causal structure: K1 -> causal leave -> H2',
        '- Same B27EM/B27FA–B27FH state machine for all four clocks',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout economics', '',
        '## Batch pooled results', '',
        '| Anchor | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 | Label |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|',
    ]

    for h in ANCHORS:
        m = pooled_by_anchor[h]
        med = '-' if pd.isna(m['median_minutes_leave_to_h2']) else f"{m['median_minutes_leave_to_h2']:.1f}m"
        lines.append(
            f"| {h:02d}:00 WIB | {m['sessions']} | {m['k1_qualified']} | {m['causal_leave']} | "
            f"{m['h2']} | {pct(m['h2_rate'])} | {m['opposite_break_before_h2']} | "
            f"{m['no_h2_by_end']} | {pct(m['resolved_h2_share'])} | {med} | {label_for(m)} |"
        )

    lines += ['', '## Frozen comparison: 00:00–17:00 WIB', '',
        '| Anchor | Leaves | H2 | H2/leave |',
        '|---|---:|---:|---:|',
    ]
    for h, lv, h2, rate in all_clock_rows:
        marker = ' **LEADER**' if h == leader_h else ''
        lines.append(f'| {h:02d}:00 WIB{marker} | {lv} | {h2} | {pct(rate)} |')

    lines += [
        '',
        f'Current structural leader after B27FI: **{leader_h:02d}:00 WIB — {leader_rate * 100:.1f}% H2/leave ({leader_h2}/{leader_lv})**.',
        '',
        '## Per-anchor weekday breakdown',
    ]

    for h in ANCHORS:
        lines += ['', f'### {h:02d}:00 WIB', '',
            '| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        ]
        ss = summary[(summary.anchor_hour_wib == h) & (summary.scope != 'POOLED')]
        for _, r in ss.iterrows():
            med = '-' if pd.isna(r.median_minutes_leave_to_h2) else f'{r.median_minutes_leave_to_h2:.1f}m'
            lines.append(
                f"| {r.scope} | {int(r.sessions)} | {int(r.k1_qualified)} | {int(r.causal_leave)} | "
                f"{int(r.h2)} | {pct(r.h2_rate)} | {int(r.opposite_break_before_h2)} | "
                f"{int(r.no_h2_by_end)} | {pct(r.resolved_h2_share)} | {med} |"
            )

    lines += [
        '', '## Interpretation', '',
        'B27FI is a temporal habitat sweep only. H2/leave is a structural outcome rate, not trading win rate. No economic edge is claimed from these results alone.', '',
        '**Status: B27FI_BNB_HOUR14_17_SWEEP_COMPLETE**', '',
        'STOP: do not test 18:00 WIB or later and do not define an entry inside B27FI.',
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text('B27FI_BNB_HOUR14_17_SWEEP_COMPLETE\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
