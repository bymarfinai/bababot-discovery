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
ANCHOR_HOUR = 3

PFX = 'BNB_HOURLY_STRUCTURE_B27FD'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds_for_local_day(day):
    ref_start_local = datetime.combine(day, time(ANCHOR_HOUR, 0), tzinfo=WIB)
    ref_end_local = ref_start_local + timedelta(hours=4)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=4)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (ref_start_local, ref_end_local, exe_start_local, exe_end_local))


def build_sessions(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    local_first = DEV_START.tz_convert(WIB).date() - timedelta(days=1)
    local_last = DEV_END.tz_convert(WIB).date() + timedelta(days=1)

    for d in pd.date_range(local_first, local_last, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds_for_local_day(day)
        if ref_start < DEV_START or exe_end > DEV_END:
            continue

        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 48:
            raise AssertionError(f'incomplete B27FD session {day}: ref={len(ref)}/48 exe={len(exe)}/48')

        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range {day}: H={H} L={L}')

        out = b27em.classify_long(exe, H, L)
        rows.append({
            'local_date': str(day), 'weekday': day.strftime('%A'),
            'reference_start_utc': ref_start, 'reference_end_utc': ref_end,
            'execution_start_utc': exe_start, 'execution_end_utc': exe_end,
            'H': H, 'L': L, 'R': R, **out,
        })

    d = pd.DataFrame(rows)
    if d.empty:
        raise AssertionError('no B27FD sessions')
    return d


def metrics(q: pd.DataFrame) -> dict:
    sessions = int(len(q))
    k = q[q.qualified.fillna(False).astype(bool)] if sessions else q
    lv = k[k.leave.fillna(False).astype(bool)] if len(k) else k
    h2 = int((lv.terminal == 'H2_ARRIVAL').sum()) if len(lv) else 0
    opp = int((lv.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum()) if len(lv) else 0
    amb = int((lv.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()) if len(lv) else 0
    no = int((lv.terminal == 'NO_H2_BY_END').sum()) if len(lv) else 0
    resolved = h2 + opp
    med = pd.to_numeric(lv.loc[lv.terminal == 'H2_ARRIVAL', 'minutes_leave_to_h2'], errors='coerce').median() if h2 else np.nan
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


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FD preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    d = build_sessions(x5)
    d.to_csv(OUT_DETAIL, index=False)

    rows = [{'scope': 'POOLED', **metrics(d)}]
    weekdays = ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
    for wd in weekdays:
        rows.append({'scope': wd, **metrics(d[d.weekday == wd])})
    s = pd.DataFrame(rows)
    s.to_csv(OUT_SUMMARY, index=False)

    pooled = metrics(d)
    if pooled['causal_leave'] >= 100 and pooled['h2_rate'] >= .70:
        label = 'STRONG_STRUCTURAL'
    elif pooled['causal_leave'] >= 60 and pooled['h2_rate'] >= .65:
        label = 'PROMISING_STRUCTURAL'
    else:
        label = 'WEAK_STRUCTURAL'

    prior = [
        ('00:00 WIB', 137, 105, 105/137),
        ('01:00 WIB', 162, 132, 132/162),
        ('02:00 WIB', 162, 126, 126/162),
    ]
    current_rate = pooled['h2_rate']
    leader_slot, _, _, leader_rate = max(prior, key=lambda x: x[3])
    delta_pp = 100.0 * (current_rate - leader_rate) if not pd.isna(current_rate) else np.nan

    lines = [
        '# BNB Hour-by-Hour Structural Discovery — B27FD','',
        '**Anchor tested:** 03:00 WIB only.','',
        '- Reference: 03:00–07:00 WIB',
        '- Execution: 07:00–11:00 WIB',
        '- Development only: 2022-01-01 through 2025-01-01 UTC',
        f'- Raw loader coverage: {coverage:.4%}',
        '- Structure only: K1 -> causal leave -> H2 using frozen B27EM/B27FA/B27FB/B27FC causal ordering',
        '- No entry, TP, SL, PnL, fee, or holdout economics','',
        '## Pooled result','',
        f"- Complete sessions: **{pooled['sessions']}**",
        f"- K1 qualified: **{pooled['k1_qualified']} ({pct(pooled['k1_rate'])})**",
        f"- Causal leaves: **{pooled['causal_leave']}**",
        f"- H2 arrivals: **{pooled['h2']}**",
        f"- Opposite breaks before H2: **{pooled['opposite_break_before_h2']}**",
        f"- Ambiguous H2/opposite: **{pooled['ambiguous_h2_vs_opposite']}**",
        f"- No H2 by end: **{pooled['no_h2_by_end']}**",
        f"- H2 / causal-leave rate: **{pct(pooled['h2_rate'])}**",
        f"- Resolved H2 share: **{pct(pooled['resolved_h2_share'])}**",
        f"- Median leave -> H2: **{pooled['median_minutes_leave_to_h2']:.1f} min**" if not pd.isna(pooled['median_minutes_leave_to_h2']) else '- Median leave -> H2: -',
        f"- Frozen structural label: **{label}**",'',
        '## Frozen comparison vs completed clocks','',
        '- 00:00 WIB: **137 leaves / 105 H2 = 76.6%**',
        '- 01:00 WIB: **162 leaves / 132 H2 = 81.5%**',
        '- 02:00 WIB: **162 leaves / 126 H2 = 77.8%**',
        f"- 03:00 WIB: **{pooled['causal_leave']} leaves / {pooled['h2']} H2 = {pct(pooled['h2_rate'])}**",
        f'- B27FD minus prior leader ({leader_slot}) H2-rate delta: **{delta_pp:+.1f} percentage points**','',
        '## Weekday breakdown','',
        '| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in s[s.scope != 'POOLED'].iterrows():
        med = '-' if pd.isna(r.median_minutes_leave_to_h2) else f'{r.median_minutes_leave_to_h2:.1f}m'
        lines.append(f"| {r.scope} | {int(r.sessions)} | {int(r.k1_qualified)} | {int(r.causal_leave)} | {int(r.h2)} | {pct(r.h2_rate)} | {int(r.opposite_break_before_h2)} | {int(r.no_h2_by_end)} | {pct(r.resolved_h2_share)} | {med} |")

    lines += ['', '## Interpretation','',
        'This milestone ranks only whether the 03:00 WIB clock geometry produces a repeatable LONG revisit structure under the same state machine as prior hourly milestones. The H2 rate is not trading WR and cannot be compared to TP/SL WR.','',
        '**Status: B27FD_BNB_HOUR03_STRUCTURE_COMPLETE**','',
        'STOP: do not test 04:00 WIB or define an entry in B27FD.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text('B27FD_BNB_HOUR03_STRUCTURE_COMPLETE\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
