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
ANCHORS = tuple(range(24))
PFX = 'BNB_CLOCK_NORMALIZATION_AUDIT_B27FL'
OUT_DIAG = ROOT / f'{PFX}_Diagnosis.csv'
OUT_DETAIL = ROOT / f'{PFX}_Normalized_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Normalized_Summary.csv'
OUT_COMPARE = ROOT / f'{PFX}_Comparison.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

# Frozen original B27FK counts. Exact original rates are recomputed from counts,
# rather than from the one-decimal display values.
ORIGINAL = {
    0: (137, 105), 1: (162, 132), 2: (162, 126), 3: (142, 96),
    4: (142, 108), 5: (141, 94), 6: (148, 104), 7: (149, 114),
    8: (143, 113), 9: (161, 118), 10: (175, 136), 11: (159, 120),
    12: (161, 117), 13: (183, 139), 14: (162, 126), 15: (178, 132),
    16: (157, 107), 17: (142, 94), 18: (127, 89), 19: (133, 91),
    20: (129, 89), 21: (145, 107), 22: (147, 114), 23: (145, 109),
}
ORIGINAL_TOP6 = {1, 8, 2, 14, 10, 22}


def fs(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds_for_local_day(day, anchor_hour):
    ref_start_local = datetime.combine(day, time(anchor_hour, 0), tzinfo=WIB)
    ref_end_local = ref_start_local + timedelta(hours=4)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=4)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_start_local, ref_end_local, exe_start_local, exe_end_local
    ))


def eligible_local_dates(anchor_hour):
    dates = []
    local_first = DEV_START.tz_convert(WIB).date() - timedelta(days=1)
    local_last = DEV_END.tz_convert(WIB).date() + timedelta(days=1)
    for d in pd.date_range(local_first, local_last, freq='D'):
        day = d.date()
        ref_start, _, _, exe_end = bounds_for_local_day(day, anchor_hour)
        if ref_start >= DEV_START and exe_end <= DEV_END:
            dates.append(day)
    return dates


def build_sessions(x5, anchor_hour, allowed_dates=None):
    eligible = eligible_local_dates(anchor_hour)
    if allowed_dates is not None:
        allowed = set(allowed_dates)
        eligible = [d for d in eligible if d in allowed]
    rows = []
    for day in eligible:
        ref_start, ref_end, exe_start, exe_end = bounds_for_local_day(day, anchor_hour)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 48:
            raise AssertionError(
                f'incomplete B27FL session anchor={anchor_hour:02d} day={day}: '
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
            'H': H, 'L': L, 'R': R, **out,
        })
    d = pd.DataFrame(rows)
    if d.empty:
        raise AssertionError(f'no B27FL sessions for anchor {anchor_hour:02d}')
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
        'h2': h2,
        'opposite_break_before_h2': opp,
        'ambiguous_h2_vs_opposite': amb,
        'no_h2_by_end': no,
        'h2_rate': float(h2 / len(lv)) if len(lv) else np.nan,
        'resolved_h2_share': float(h2 / resolved) if resolved else np.nan,
        'median_minutes_leave_to_h2': float(med) if not pd.isna(med) else np.nan,
    }


def pct(x, decimals=1):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.{decimals}f}%'


def pp(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):+.3f}pp'


def rank_map(rows):
    ordered = sorted(rows, key=lambda r: (-r['rate'], r['anchor']))
    return {r['anchor']: i + 1 for i, r in enumerate(ordered)}, ordered


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FL preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    # Geometry-only date universe diagnosis first.
    eligible = {h: eligible_local_dates(h) for h in ANCHORS}
    common = set(eligible[0])
    for h in ANCHORS[1:]:
        common &= set(eligible[h])
    common_dates = sorted(common)
    if not common_dates:
        raise AssertionError('empty all-clock intersection')

    expected_start = datetime(2022, 1, 2).date()
    expected_end = datetime(2024, 12, 31).date()
    expectation_match = (
        common_dates[0] == expected_start and
        common_dates[-1] == expected_end and
        len(common_dates) == 1095
    )

    diag_rows = []
    for h in ANCHORS:
        e = eligible[h]
        extras = sorted(set(e) - common)
        missing = sorted(common - set(e))
        diag_rows.append({
            'anchor_hour_wib': h,
            'original_eligible_sessions': len(e),
            'first_eligible_local_date': str(min(e)),
            'last_eligible_local_date': str(max(e)),
            'normalized_common_sessions': len(common_dates),
            'extra_vs_common_count': len(extras),
            'extra_vs_common_dates': ';'.join(map(str, extras)),
            'missing_common_count': len(missing),
            'missing_common_dates': ';'.join(map(str, missing)),
        })
    diag = pd.DataFrame(diag_rows)
    OUT_DIAG.write_text(diag.to_csv(index=False), encoding='utf-8')

    # Reproduce the original sweep exactly before normalized comparison.
    original_reproduced = {}
    full_by_anchor = {}
    for h in ANCHORS:
        d = build_sessions(x5, h)
        full_by_anchor[h] = d
        m = metrics(d)
        original_reproduced[h] = m
        exp_lv, exp_h2 = ORIGINAL[h]
        if m['causal_leave'] != exp_lv or m['h2'] != exp_h2:
            raise AssertionError(
                f'original B27FK reproduction mismatch anchor={h:02d}: '
                f"got leaves/H2={m['causal_leave']}/{m['h2']} expected={exp_lv}/{exp_h2}"
            )
        if m['sessions'] != len(eligible[h]):
            raise AssertionError(f'eligibility/session mismatch anchor={h:02d}')

    normalized_details = []
    normalized_metrics = {}
    summary_rows = []
    for h in ANCHORS:
        d = full_by_anchor[h]
        n = d[d.local_date.isin({str(x) for x in common_dates})].copy()
        if len(n) != len(common_dates):
            raise AssertionError(
                f'normalized session count mismatch anchor={h:02d}: {len(n)} vs {len(common_dates)}'
            )
        normalized_details.append(n)
        m = metrics(n)
        normalized_metrics[h] = m
        summary_rows.append({'anchor_hour_wib': h, **m})

    detail = pd.concat(normalized_details, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    original_rank_input = []
    normalized_rank_input = []
    for h in ANCHORS:
        olv, oh2 = ORIGINAL[h]
        original_rank_input.append({'anchor': h, 'rate': oh2 / olv})
        nm = normalized_metrics[h]
        normalized_rank_input.append({'anchor': h, 'rate': nm['h2_rate']})
    orig_rank, orig_order = rank_map(original_rank_input)
    norm_rank, norm_order = rank_map(normalized_rank_input)

    compare_rows = []
    for h in ANCHORS:
        om = original_reproduced[h]
        nm = normalized_metrics[h]
        delta = nm['h2_rate'] - om['h2_rate']
        compare_rows.append({
            'anchor_hour_wib': h,
            'original_sessions': om['sessions'],
            'normalized_sessions': nm['sessions'],
            'sessions_removed': om['sessions'] - nm['sessions'],
            'original_leaves': om['causal_leave'],
            'original_h2': om['h2'],
            'original_h2_rate': om['h2_rate'],
            'normalized_leaves': nm['causal_leave'],
            'normalized_h2': nm['h2'],
            'normalized_h2_rate': nm['h2_rate'],
            'rate_delta': delta,
            'rate_delta_pp': 100.0 * delta,
            'original_rank': orig_rank[h],
            'normalized_rank': norm_rank[h],
            'rank_delta': orig_rank[h] - norm_rank[h],
        })
    comp = pd.DataFrame(compare_rows)
    comp.to_csv(OUT_COMPARE, index=False)

    orig_leader = orig_order[0]['anchor']
    norm_leader = norm_order[0]['anchor']
    norm_top6 = {r['anchor'] for r in norm_order[:6]}
    max_abs_delta = float(comp.rate_delta.abs().max())
    max_delta_h = int(comp.loc[comp.rate_delta.abs().idxmax(), 'anchor_hour_wib'])

    leader_changed = norm_leader != 1
    top6_changed = norm_top6 != ORIGINAL_TOP6
    material_rate_shift = max_abs_delta >= 0.01
    stable = not (leader_changed or top6_changed or material_rate_shift)

    flags = []
    if leader_changed:
        flags.append('LEADER_CHANGED')
    if top6_changed:
        flags.append('TOP6_CHANGED')
    if material_rate_shift:
        flags.append('MATERIAL_RATE_SHIFT')
    if stable:
        flags.append('COMPARABILITY_STABLE')

    lines = [
        '# BNB 24H Clock Comparability / Normalization Audit — B27FL', '',
        f'- Raw loader coverage: {coverage:.4%}',
        '- Original B27FA–B27FK state machine reproduced exactly before normalization: YES',
        f'- Derived common local-date universe: {common_dates[0]} through {common_dates[-1]} inclusive',
        f'- Common sessions per anchor: {len(common_dates)}',
        f'- Preregistered boundary expectation match: {"YES" if expectation_match else "NO"}',
        '- No entry, TP, SL, PnL, weekday filter, or holdout data used', '',
        '## 1. Session-universe diagnosis', '',
        '| Anchor | Original sessions | First local date | Last local date | Extra vs common | Extra dates |',
        '|---|---:|---|---|---:|---|',
    ]
    for _, r in diag.iterrows():
        extra_dates = r.extra_vs_common_dates if r.extra_vs_common_dates else '-'
        lines.append(
            f"| {int(r.anchor_hour_wib):02d}:00 | {int(r.original_eligible_sessions)} | "
            f"{r.first_eligible_local_date} | {r.last_eligible_local_date} | "
            f"{int(r.extra_vs_common_count)} | {extra_dates} |"
        )

    lines += ['', '## 2. Original vs normalized structural outcomes', '',
              '| Anchor | Sessions old→norm | Leaves old→norm | H2 old→norm | Rate old→norm | Δ rate | Rank old→norm |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for _, r in comp.iterrows():
        lines.append(
            f"| {int(r.anchor_hour_wib):02d}:00 | {int(r.original_sessions)}→{int(r.normalized_sessions)} | "
            f"{int(r.original_leaves)}→{int(r.normalized_leaves)} | {int(r.original_h2)}→{int(r.normalized_h2)} | "
            f"{pct(r.original_h2_rate, 2)}→{pct(r.normalized_h2_rate, 2)} | "
            f"{r.rate_delta_pp:+.3f}pp | {int(r.original_rank)}→{int(r.normalized_rank)} |"
        )

    lines += ['', '## 3. Normalized 24-hour ranking', '',
              '| Rank | Anchor | Sessions | Leaves | H2 | H2/leave |',
              '|---:|---|---:|---:|---:|---:|']
    for rank, r in enumerate(norm_order, start=1):
        h = r['anchor']
        m = normalized_metrics[h]
        marker = ' **LEADER**' if rank == 1 else ''
        lines.append(
            f"| {rank} | {h:02d}:00 WIB{marker} | {m['sessions']} | {m['causal_leave']} | "
            f"{m['h2']} | {pct(m['h2_rate'], 2)} |"
        )

    lines += ['', '## 4. Frozen materiality flags', '',
              f'- Original leader: {orig_leader:02d}:00 WIB',
              f'- Normalized leader: {norm_leader:02d}:00 WIB',
              f'- Leader changed: {"YES" if leader_changed else "NO"}',
              f'- Original top-six set: {sorted(ORIGINAL_TOP6)}',
              f'- Normalized top-six set: {sorted(norm_top6)}',
              f'- Top-six composition changed: {"YES" if top6_changed else "NO"}',
              f'- Maximum absolute H2/leave rate shift: {100.0 * max_abs_delta:.3f}pp at {max_delta_h:02d}:00 WIB',
              f'- Any >=1.0pp material rate shift: {"YES" if material_rate_shift else "NO"}',
              f'- Audit classification: **{", ".join(flags)}**', '',
              '## Interpretation boundary', '',
              'B27FL audits cross-clock comparability only. A stable normalized ranking supports treating the temporal ranking as not being an artifact of unequal boundary-session counts. It does not establish an executable or profitable trading edge.', '',
              '**Status: B27FL_BNB_CLOCK_NORMALIZATION_AUDIT_COMPLETE**', '',
              'STOP: do not define an entry, select weekdays, or reveal holdout data inside B27FL.']

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text('B27FL_BNB_CLOCK_NORMALIZATION_AUDIT_COMPLETE\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
