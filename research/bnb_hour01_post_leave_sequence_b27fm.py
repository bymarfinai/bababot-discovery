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
BAR5 = pd.Timedelta(minutes=5)
ANCHOR = 1
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
PFX = 'BNB_HOUR01_POST_LEAVE_SEQUENCE_B27FM'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_THRESH = ROOT / f'{PFX}_Threshold_Summary.csv'
OUT_TIMING = ROOT / f'{PFX}_Timing_Summary.csv'
OUT_FIRST = ROOT / f'{PFX}_First_Close_Bins.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
THRESHOLDS = [('P10', 0.10), ('P20', 0.20), ('P35', 0.35), ('P50', 0.50)]
EXPECTED_SESSIONS = 1095
EXPECTED_LEAVES = 162
EXPECTED_H2 = 132


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds_for_local_day(day):
    ref_start_local = datetime.combine(day, time(ANCHOR, 0), tzinfo=WIB)
    ref_end_local = ref_start_local + timedelta(hours=4)
    exe_start_local = ref_end_local
    exe_end_local = exe_start_local + timedelta(hours=4)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_start_local, ref_end_local, exe_start_local, exe_end_local
    ))


def build_sessions(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds_for_local_day(day)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 48:
            raise AssertionError(
                f'incomplete B27FM session day={day}: ref={len(ref)}/48 exe={len(exe)}/48'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range day={day}: H={H} L={L}')
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'event_id': str(day),
            'local_date': str(day),
            'weekday': day.strftime('%A'),
            'reference_start_utc': ref_start,
            'reference_end_utc': ref_end,
            'execution_start_utc': exe_start,
            'execution_end_utc': exe_end,
            'H': H, 'L': L, 'R': R, **out,
        })
    return pd.DataFrame(rows)


def timing_bucket(minutes):
    if pd.isna(minutes):
        return 'NON_H2'
    bars = int(round(float(minutes) / 5.0))
    if bars <= 1:
        return '1_BAR_5M'
    if bars == 2:
        return '2_BARS_10M'
    if bars == 3:
        return '3_BARS_15M'
    if bars <= 6:
        return '4_6_BARS_20_30M'
    if bars <= 12:
        return '7_12_BARS_35_60M'
    return '13PLUS_BARS_65M_PLUS'


def first_depth_bin(x):
    if pd.isna(x):
        return 'MISSING_FIRST_POST_LEAVE_BAR'
    x = float(x)
    if x <= 0.10:
        return 'LE_0.10R'
    if x <= 0.20:
        return 'GT_0.10_TO_0.20R'
    if x <= 0.35:
        return 'GT_0.20_TO_0.35R'
    if x <= 0.50:
        return 'GT_0.35_TO_0.50R'
    return 'GT_0.50R'


def qstats(s: pd.Series):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if s.empty:
        return (np.nan, np.nan, np.nan, np.nan)
    return tuple(float(s.quantile(q)) for q in (0.25, 0.50, 0.75, 0.90))


def pct(x, d=1):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.{d}f}%'


def num(x, d=3):
    return '-' if pd.isna(x) else f'{float(x):.{d}f}'


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FM preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    sessions = build_sessions(x5)
    if len(sessions) != EXPECTED_SESSIONS:
        raise AssertionError(f'session reproduction mismatch: {len(sessions)} != {EXPECTED_SESSIONS}')

    q = sessions[sessions.qualified.fillna(False).astype(bool)]
    leaves = q[q.leave.fillna(False).astype(bool)].copy()
    h2_count = int((leaves.terminal == 'H2_ARRIVAL').sum())
    if len(leaves) != EXPECTED_LEAVES or h2_count != EXPECTED_H2:
        raise AssertionError(
            f'B27FL reproduction gate failed: leaves/H2={len(leaves)}/{h2_count}, '
            f'expected={EXPECTED_LEAVES}/{EXPECTED_H2}'
        )

    rows = []
    threshold_sets = {name: set() for name, _ in THRESHOLDS}

    for _, r in leaves.iterrows():
        exe_start = pd.Timestamp(r.execution_start_utc)
        exe_end = pd.Timestamp(r.execution_end_utc)
        exe = fs(x5, exe_start, exe_end)
        leave_ts = pd.Timestamp(r.leave_ts)
        post = fs(x5, leave_ts, exe_end)

        terminal_start = pd.NaT if pd.isna(r.terminal_start) else pd.Timestamp(r.terminal_start)
        if pd.isna(terminal_start):
            preterminal = post
        else:
            preterminal = post[post.index < terminal_start]

        first_exists = len(post) > 0
        first_start = pd.Timestamp(post.index[0]) if first_exists else pd.NaT
        first_close = float(post.iloc[0].close) if first_exists else np.nan
        first_close_depth = (float(r.H) - first_close) / float(r.R) if first_exists else np.nan
        first_is_h2_terminal = bool(
            first_exists and r.terminal == 'H2_ARRIVAL' and not pd.isna(terminal_start)
            and first_start == terminal_start
        )

        if r.terminal == 'H2_ARRIVAL':
            prior = preterminal
            if len(prior):
                pre_h2_low_depth = max(0.0, (float(r.H) - float(prior.low.min())) / float(r.R))
                pre_h2_close_depth = max(0.0, (float(r.H) - float(prior.close.min())) / float(r.R))
            else:
                pre_h2_low_depth = 0.0
                pre_h2_close_depth = 0.0
            h2_complete = terminal_start + BAR5
        else:
            pre_h2_low_depth = np.nan
            pre_h2_close_depth = np.nan
            h2_complete = pd.NaT

        out = {
            'event_id': r.event_id,
            'local_date': r.local_date,
            'weekday': r.weekday,
            'H': r.H, 'L': r.L, 'R': r.R,
            'k1_signal': r.k1_signal,
            'leave_start': r.leave_start,
            'leave_ts': r.leave_ts,
            'terminal': r.terminal,
            'terminal_start': r.terminal_start,
            'minutes_leave_to_h2': r.minutes_leave_to_h2,
            'h2_timing_bucket': timing_bucket(r.minutes_leave_to_h2),
            'first_post_leave_exists': first_exists,
            'first_post_leave_start': first_start,
            'first_post_leave_close': first_close,
            'first_close_depth_R': first_close_depth,
            'first_close_depth_bin': first_depth_bin(first_close_depth),
            'first_post_leave_is_h2_terminal': first_is_h2_terminal,
            'pre_h2_low_depth_R': pre_h2_low_depth,
            'pre_h2_close_depth_R': pre_h2_close_depth,
        }

        for name, frac in THRESHOLDS:
            level = float(r.H) - frac * float(r.R)
            hit = preterminal[preterminal.close <= level]
            reached = len(hit) > 0
            first_thr_start = pd.Timestamp(hit.index[0]) if reached else pd.NaT
            first_thr_complete = first_thr_start + BAR5 if reached else pd.NaT
            if reached:
                threshold_sets[name].add(r.event_id)
            if reached and r.terminal == 'H2_ARRIVAL':
                thr_to_h2 = float((h2_complete - first_thr_complete) / pd.Timedelta(minutes=1))
            else:
                thr_to_h2 = np.nan
            out[f'{name}_level'] = level
            out[f'{name}_reached_before_terminal'] = reached
            out[f'{name}_first_start'] = first_thr_start
            out[f'{name}_first_complete'] = first_thr_complete
            out[f'{name}_to_h2_minutes'] = thr_to_h2

        rows.append(out)

    detail = pd.DataFrame(rows)
    if len(detail) != EXPECTED_LEAVES:
        raise AssertionError('event-detail row count mismatch')

    # Nested completed-close threshold consistency.
    nested_ok = (
        threshold_sets['P50'] <= threshold_sets['P35'] <=
        threshold_sets['P20'] <= threshold_sets['P10']
    )
    if not nested_ok:
        raise AssertionError('pullback threshold nested consistency failed')

    detail.to_csv(OUT_DETAIL, index=False)

    # Terminal distribution.
    terminal_order = [
        'H2_ARRIVAL', 'OPPOSITE_BREAK_BEFORE_H2',
        'AMBIGUOUS_H2_VS_OPPOSITE_BREAK', 'NO_H2_BY_END'
    ]
    terminal_counts = {t: int((detail.terminal == t).sum()) for t in terminal_order}

    # H2 timing distribution.
    h2 = detail[detail.terminal == 'H2_ARRIVAL'].copy()
    timing_order = [
        '1_BAR_5M', '2_BARS_10M', '3_BARS_15M',
        '4_6_BARS_20_30M', '7_12_BARS_35_60M', '13PLUS_BARS_65M_PLUS'
    ]
    timing_rows = []
    for b in timing_order:
        n = int((h2.h2_timing_bucket == b).sum())
        timing_rows.append({'bucket': b, 'count': n, 'share_of_h2': n / len(h2)})
    timing_df = pd.DataFrame(timing_rows)
    timing_df.to_csv(OUT_TIMING, index=False)
    h2_q25, h2_med, h2_q75, h2_q90 = qstats(h2.minutes_leave_to_h2)

    low_q25, low_med, low_q75, low_q90 = qstats(h2.pre_h2_low_depth_R)
    close_q25, close_med, close_q75, close_q90 = qstats(h2.pre_h2_close_depth_R)

    # Threshold summary.
    threshold_rows = []
    for name, frac in THRESHOLDS:
        flag = detail[f'{name}_reached_before_terminal'].fillna(False).astype(bool)
        s = detail[flag].copy()
        n = int(len(s))
        hh = int((s.terminal == 'H2_ARRIVAL').sum())
        opp = int((s.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum())
        amb = int((s.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum())
        no = int((s.terminal == 'NO_H2_BY_END').sum())
        t25, t50, t75, t90 = qstats(s.loc[s.terminal == 'H2_ARRIVAL', f'{name}_to_h2_minutes'])
        threshold_rows.append({
            'threshold': name,
            'depth_R': frac,
            'reached_count': n,
            'share_all_leaves': n / EXPECTED_LEAVES,
            'h2': hh,
            'opposite_break': opp,
            'ambiguous': amb,
            'no_h2_by_end': no,
            'h2_recovery_rate': hh / n if n else np.nan,
            'threshold_to_h2_p25_min': t25,
            'threshold_to_h2_median_min': t50,
            'threshold_to_h2_p75_min': t75,
            'threshold_to_h2_p90_min': t90,
        })
    threshold_df = pd.DataFrame(threshold_rows)
    threshold_df.to_csv(OUT_THRESH, index=False)

    # First post-leave close bins.
    first_order = [
        'LE_0.10R', 'GT_0.10_TO_0.20R', 'GT_0.20_TO_0.35R',
        'GT_0.35_TO_0.50R', 'GT_0.50R', 'MISSING_FIRST_POST_LEAVE_BAR'
    ]
    first_rows = []
    for b in first_order:
        s = detail[detail.first_close_depth_bin == b]
        if s.empty and b == 'MISSING_FIRST_POST_LEAVE_BAR':
            continue
        n = int(len(s))
        hh = int((s.terminal == 'H2_ARRIVAL').sum())
        first_rows.append({
            'first_close_depth_bin': b,
            'count': n,
            'share_all_leaves': n / EXPECTED_LEAVES,
            'h2': hh,
            'h2_outcome_rate': hh / n if n else np.nan,
            'opposite_break': int((s.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum()),
            'ambiguous': int((s.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()),
            'no_h2_by_end': int((s.terminal == 'NO_H2_BY_END').sum()),
            'first_bar_is_h2_terminal': int(s.first_post_leave_is_h2_terminal.fillna(False).sum()),
        })
    first_df = pd.DataFrame(first_rows)
    first_df.to_csv(OUT_FIRST, index=False)

    immediate_h2 = int(detail.first_post_leave_is_h2_terminal.fillna(False).sum())

    lines = [
        '# BNB 01:00 WIB Post-Leave Sequence Diagnosis — B27FM', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Frozen normalized universe: {COMMON_START} through {COMMON_END} inclusive',
        f'- Complete sessions: {len(sessions)}',
        f'- B27FL 01:00 reproduction gate: PASS ({len(leaves)} causal leaves, {h2_count} H2)',
        '- Anchor remains frozen at 01:00 WIB; no clock re-selection',
        '- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used', '',
        '## 1. Frozen terminal path after causal leave', '',
        '| Terminal | Count | Share of 162 leaves |',
        '|---|---:|---:|',
    ]
    for t in terminal_order:
        n = terminal_counts[t]
        lines.append(f'| {t} | {n} | {pct(n / EXPECTED_LEAVES)} |')

    lines += ['', '## 2. H2 arrival timing', '',
              f'- Immediate H2 on first post-leave candle: **{immediate_h2}/{EXPECTED_LEAVES} ({pct(immediate_h2 / EXPECTED_LEAVES)})** of all leaves',
              f'- H2 timing quartiles among {len(h2)} H2 arrivals: p25={num(h2_q25,1)}m, median={num(h2_med,1)}m, p75={num(h2_q75,1)}m, p90={num(h2_q90,1)}m', '',
              '| Timing bucket | Count | Share of H2 arrivals |',
              '|---|---:|---:|']
    for _, rr in timing_df.iterrows():
        lines.append(f"| {rr.bucket} | {int(rr['count'])} | {pct(rr.share_of_h2)} |")

    lines += ['', '## 3. Pre-H2 pullback depth (terminal H2 candle excluded)', '',
              '| Measure | p25 | Median | p75 | p90 |',
              '|---|---:|---:|---:|---:|',
              f'| Low depth / R | {num(low_q25)} | {num(low_med)} | {num(low_q75)} | {num(low_q90)} |',
              f'| Close depth / R | {num(close_q25)} | {num(close_med)} | {num(close_q75)} | {num(close_q90)} |']

    lines += ['', '## 4. Frozen completed-close pullback grid', '',
              f'- Nested threshold consistency P50 ⊆ P35 ⊆ P20 ⊆ P10: **{"PASS" if nested_ok else "FAIL"}**',
              '- Threshold must occur on a completed non-terminal candle; the terminal candle itself cannot create the prior pullback.', '',
              '| Threshold | Reached before terminal | Share leaves | H2 | Opp | Amb | No H2 | H2 recovery | Median threshold→H2 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _, rr in threshold_df.iterrows():
        lines.append(
            f"| {rr.threshold} ({rr.depth_R:.2f}R) | {int(rr.reached_count)} | {pct(rr.share_all_leaves)} | "
            f"{int(rr.h2)} | {int(rr.opposite_break)} | {int(rr.ambiguous)} | {int(rr.no_h2_by_end)} | "
            f"{pct(rr.h2_recovery_rate)} | {num(rr.threshold_to_h2_median_min,1)}m |"
        )

    lines += ['', '## 5. First post-leave completed close segmentation', '',
              '| First close depth | N | Share leaves | H2 | H2 outcome | Opp | Amb | No H2 | First bar itself H2 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _, rr in first_df.iterrows():
        lines.append(
            f"| {rr.first_close_depth_bin} | {int(rr['count'])} | {pct(rr.share_all_leaves)} | "
            f"{int(rr.h2)} | {pct(rr.h2_outcome_rate)} | {int(rr.opposite_break)} | {int(rr.ambiguous)} | "
            f"{int(rr.no_h2_by_end)} | {int(rr.first_bar_is_h2_terminal)} |"
        )

    lines += ['', '## Interpretation boundary', '',
              'B27FM maps the causal structural path after the 01:00 WIB leave. Any high H2 recovery percentage is a structural outcome rate, not a trading win rate. The pullback grid is descriptive discovery only and no threshold is selected as an entry in this milestone.', '',
              '**Status: B27FM_BNB_HOUR01_POST_LEAVE_SEQUENCE_COMPLETE**', '',
              'STOP: any actual entry hypothesis, stop/target, or economic test requires a new preregistered milestone.']

    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT_STATUS.write_text('B27FM_BNB_HOUR01_POST_LEAVE_SEQUENCE_COMPLETE\n', encoding='utf-8')

    print(f'coverage={coverage:.4%}')
    print(f'sessions={len(sessions)} leaves={len(leaves)} h2={h2_count} h2_rate={h2_count/len(leaves):.4%}')
    print(f'immediate_h2={immediate_h2}')
    print(threshold_df.to_string(index=False))
    print(first_df.to_string(index=False))
    print('B27FM complete; structural diagnosis only.')


if __name__ == '__main__':
    main()
