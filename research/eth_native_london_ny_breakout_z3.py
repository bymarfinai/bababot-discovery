#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

import eth_native_london_ny_retest_breakout_z2 as z2

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_NATIVE_LONDON_NY_BREAKOUT_Z3'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_RESULT = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
RETESTS = (0.95, 0.90)
MAJOR = ('external', 'development', 'reference_validation')
EXTENSIONS = (0.0, 0.025, 0.050, 0.075, 0.100, 0.125, 0.150, 0.175, 0.200)


def retest_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def threshold_label(e: float) -> str:
    if e == 0.0:
        return 'B00'
    return f'B{int(round(e * 1000)):03d}'


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = k / n
    zz = z * z
    den = 1.0 + zz / n
    center = p + zz / (2.0 * n)
    rad = z * math.sqrt((p * (1.0 - p) + zz / (4.0 * n)) / n)
    return (center - rad) / den


def fast_slice(x: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(b, side='left'))
    return x.iloc[i:j]


def audit_path_after_retest(
    x5: pd.DataFrame,
    retest_ts: pd.Timestamp,
    execution_end: pd.Timestamp,
    H: float,
    L: float,
):
    if not H > L:
        raise AssertionError('invalid range')
    R = H - L
    q = fast_slice(x5, retest_ts, execution_end)

    reached = {e: pd.NaT for e in EXTENSIONS}
    first_high_arrival_ts = pd.NaT
    opposite_ts = pd.NaT

    for ts, r in q.iterrows():
        cl = float(r.close)
        hi = float(r.high)
        completed = ts + BAR5

        # Terminal-first. A close below L ends the path for all still-unreached thresholds.
        if cl < L:
            opposite_ts = completed
            break

        if pd.isna(first_high_arrival_ts) and hi >= H:
            first_high_arrival_ts = completed

        for e in EXTENSIONS:
            if not pd.isna(reached[e]):
                continue
            if e == 0.0:
                hit = cl > H
            else:
                hit = cl >= H + e * R
            if hit:
                reached[e] = completed

    rows = []
    for e in EXTENSIONS:
        rt = reached[e]
        if not pd.isna(rt):
            outcome = 'THRESHOLD_REACHED'
            if not rt > retest_ts:
                raise AssertionError('threshold may not be credited on/before retest close')
        elif not pd.isna(opposite_ts):
            outcome = 'OPPOSITE_BREAK_BEFORE_THRESHOLD'
        else:
            outcome = 'NO_THRESHOLD_BY_END'
        rows.append({
            'extension': e,
            'threshold': threshold_label(e),
            'threshold_price': H if e == 0.0 else H + e * R,
            'threshold_reached': not pd.isna(rt),
            'threshold_ts': rt,
            'opposite_ts': opposite_ts,
            'outcome': outcome,
            'minutes_retest_to_threshold': (
                float((rt - retest_ts) / pd.Timedelta(minutes=1)) if not pd.isna(rt) else np.nan
            ),
            'high_arrival': not pd.isna(first_high_arrival_ts),
            'high_arrival_ts': first_high_arrival_ts,
            'minutes_retest_to_high_arrival': (
                float((first_high_arrival_ts - retest_ts) / pd.Timedelta(minutes=1))
                if not pd.isna(first_high_arrival_ts) else np.nan
            ),
        })
    return rows


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 00:05', periods=4, freq='5min', tz='UTC')
    x = pd.DataFrame([
        [99.8, 100.2, 99.0, 100.10],  # B00 only
        [100.1, 100.7, 99.8, 100.60], # B025 + B050
        [100.6, 100.8, 99.5, 100.70], # still below B075=100.75
        [100.7, 101.0, 89.0, 89.50],  # opposite terminal; cannot credit high-arrival/threshold here
    ], index=idx, columns=['open','high','low','close'])
    rows = audit_path_after_retest(x, idx[0], idx[-1] + BAR5, H, L)
    d = {r['threshold']: r for r in rows}
    assert d['B00']['threshold_reached'] and d['B00']['threshold_ts'] == idx[0] + BAR5
    assert d['B025']['threshold_reached'] and d['B050']['threshold_reached']
    assert not d['B075']['threshold_reached']
    assert d['B075']['outcome'] == 'OPPOSITE_BREAK_BEFORE_THRESHOLD'
    assert d['B00']['threshold_price'] == H
    assert abs(d['B050']['threshold_price'] - 100.5) < 1e-12


def build_audit(x5: pd.DataFrame, A: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in RETESTS:
        q = A[(A.fraction == f) & A.retested.astype(bool)].copy()
        for r in q.itertuples(index=False):
            rt = pd.Timestamp(r.retest_ts)
            ee = pd.Timestamp(r.execution_end)
            H = float(r.H); L = float(r.L); R = float(r.range)
            if not H > L or abs(R - (H - L)) > max(1e-9, 1e-9 * abs(R)):
                raise AssertionError('range mismatch')
            path_rows = audit_path_after_retest(x5, rt, ee, H, L)
            for p in path_rows:
                rows.append({
                    'session_id': r.session_id,
                    'partition': r.partition,
                    'reference_start': r.reference_start,
                    'execution_start': r.execution_start,
                    'execution_end': r.execution_end,
                    'H': H,
                    'L': L,
                    'range': R,
                    'retest_fraction': f,
                    'retest': retest_label(f),
                    'retest_start': r.retest_start,
                    'retest_ts': rt,
                    **p,
                })
    return pd.DataFrame(rows)


def summarize(B: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in RETESTS:
        for e in EXTENSIONS:
            for part in (*z2.base.PARTS.keys(), 'POOLED_MAJOR'):
                if part == 'POOLED_MAJOR':
                    q = B[(B.retest_fraction == f) & (B.extension == e) & B.partition.isin(MAJOR)]
                else:
                    q = B[(B.retest_fraction == f) & (B.extension == e) & (B.partition == part)]
                n = len(q)
                hit = int(q.threshold_reached.astype(bool).sum()) if n else 0
                opp = int((q.outcome == 'OPPOSITE_BREAK_BEFORE_THRESHOLD').sum()) if n else 0
                no = int((q.outcome == 'NO_THRESHOLD_BY_END').sum()) if n else 0
                if n and hit + opp + no != n:
                    raise AssertionError('threshold outcomes do not reconcile')
                harr = int(q.high_arrival.astype(bool).sum()) if n else 0
                rows.append({
                    'retest_fraction': f,
                    'retest': retest_label(f),
                    'extension': e,
                    'threshold': threshold_label(e),
                    'partition': part,
                    'retest_cohort_n': n,
                    'threshold_reached': hit,
                    'opposite_before_threshold': opp,
                    'no_threshold_by_end': no,
                    'threshold_reach_rate': hit / n if n else np.nan,
                    'resolved_upside_rate': hit / (hit + opp) if (hit + opp) else np.nan,
                    'wilson_lb95_reach': wilson_lb(hit, n),
                    'median_minutes_retest_to_threshold': pd.to_numeric(
                        q.loc[q.threshold_reached.astype(bool), 'minutes_retest_to_threshold'], errors='coerce'
                    ).median() if hit else np.nan,
                    'high_arrival_count': harr,
                    'high_arrival_rate': harr / n if n else np.nan,
                    'median_minutes_retest_to_high_arrival': pd.to_numeric(
                        q.loc[q.high_arrival.astype(bool), 'minutes_retest_to_high_arrival'], errors='coerce'
                    ).median() if harr else np.nan,
                })
    return pd.DataFrame(rows)


def development_candidates(S: pd.DataFrame):
    candidates = []
    detail = []
    for e in EXTENSIONS:
        ok_all = True
        for f in RETESTS:
            r = S[(S.partition == 'development') & (S.retest_fraction == f) & (S.extension == e)].iloc[0]
            ok = (
                int(r.retest_cohort_n) >= 50 and
                float(r.threshold_reach_rate) >= .55 and
                float(r.resolved_upside_rate) >= .85 and
                int(r.threshold_reached) > int(r.opposite_before_threshold)
            )
            detail.append((f, e, r, ok))
            ok_all = ok_all and ok
        if ok_all:
            candidates.append(e)
    selected = max(candidates) if candidates else None
    return selected, detail


def replication_gate(S: pd.DataFrame, selected: float | None):
    if selected is None:
        return [], False
    rows = []
    all_ok = True
    for part in ('external', 'reference_validation'):
        for f in RETESTS:
            r = S[(S.partition == part) & (S.retest_fraction == f) & (S.extension == selected)].iloc[0]
            ok = (
                int(r.retest_cohort_n) >= 30 and
                float(r.threshold_reach_rate) >= .50 and
                float(r.resolved_upside_rate) >= .85 and
                int(r.threshold_reached) > int(r.opposite_before_threshold)
            )
            rows.append((part, f, r, ok))
            all_ok = all_ok and ok
    return rows, all_ok


def assert_monotonic(S: pd.DataFrame):
    for part in (*z2.base.PARTS.keys(), 'POOLED_MAJOR'):
        for f in RETESTS:
            q = S[(S.partition == part) & (S.retest_fraction == f)].sort_values('extension')
            counts = q.threshold_reached.astype(int).tolist()
            if any(b > a for a, b in zip(counts, counts[1:])):
                raise AssertionError(f'non-monotonic threshold reaches: {part} {retest_label(f)}')


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def main():
    synthetic_tests()
    z2.read_provenance()
    z2.base.synthetic_tests()
    x5, coverage = z2.base.load5('ETHUSDT')
    if coverage < .995:
        raise RuntimeError(f'ETH coverage too low: {coverage:.6f}')

    # Deterministically rerun Z2 chronology to obtain the frozen F95/F90 retest cohorts.
    W, A = z2.scan(x5)
    Z2S = z2.summarize(W, A)
    dev95 = Z2S[(Z2S.partition == 'development') & (Z2S.fraction == .95)].iloc[0]
    dev90 = Z2S[(Z2S.partition == 'development') & (Z2S.fraction == .90)].iloc[0]
    if int(dev95.retest_count) != 70 or int(dev90.retest_count) != 67:
        raise AssertionError('Z2 development retest cohort parity failed')

    s95 = set(A[(A.fraction == .95) & A.retested.astype(bool)].session_id)
    s90 = set(A[(A.fraction == .90) & A.retested.astype(bool)].session_id)
    if not s90.issubset(s95):
        raise AssertionError('F90 retest sessions must be a subset of F95 retest sessions')

    B = build_audit(x5, A)
    if len(B) == 0:
        raise RuntimeError('Z3 audit is empty')
    B.to_csv(OUT_AUDIT, index=False)

    S = summarize(B)
    assert_monotonic(S)
    S.to_csv(OUT_SUMMARY, index=False)

    selected, _ = development_candidates(S)
    reps, supported = replication_gate(S, selected)

    if selected is None:
        status = 'ETH_NATIVE_LONDON_NY_BREAKOUT_Z3_NO_DEV_THRESHOLD'
    elif supported:
        status = 'ETH_NATIVE_LONDON_NY_BREAKOUT_Z3_SUPPORTED'
    else:
        status = 'ETH_NATIVE_LONDON_NY_BREAKOUT_Z3_CANDIDATE_NOT_REPLICATED'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH Native London->New York Breakout Confirmation Discovery — Z3 Result', '',
        'Frozen clock: reference **18:30-00:00 WIB**, execution **00:00-06:30 WIB**.',
        'Frozen shallow retest zone: **F95 and F90 are both audited; neither is promoted alone**.',
        f'Raw ETHUSDT 5m coverage: **{coverage:.4%}**.',
        'Breakout thresholds are completed 5m closes from B00 (>H) through B200 (H+0.20R).',
        'Structural only: no entry, TP, SL, fees, leverage, PnL, PF, or expectancy.', '',
        '## Development threshold sweep', '',
        '| Threshold | F95 N | F95 reach | F95 resolved | F90 N | F90 reach | F90 resolved | Dev gate both |',
        '|---|---:|---:|---:|---:|---:|---:|---|',
    ]
    for e in EXTENSIONS:
        a = S[(S.partition == 'development') & (S.retest_fraction == .95) & (S.extension == e)].iloc[0]
        b = S[(S.partition == 'development') & (S.retest_fraction == .90) & (S.extension == e)].iloc[0]
        ok = (
            int(a.retest_cohort_n) >= 50 and float(a.threshold_reach_rate) >= .55 and float(a.resolved_upside_rate) >= .85 and int(a.threshold_reached) > int(a.opposite_before_threshold) and
            int(b.retest_cohort_n) >= 50 and float(b.threshold_reach_rate) >= .55 and float(b.resolved_upside_rate) >= .85 and int(b.threshold_reached) > int(b.opposite_before_threshold)
        )
        lines.append(
            f'| {threshold_label(e)} | {int(a.retest_cohort_n)} | {pct(a.threshold_reach_rate)} | {pct(a.resolved_upside_rate)} | '
            f'{int(b.retest_cohort_n)} | {pct(b.threshold_reach_rate)} | {pct(b.resolved_upside_rate)} | {"PASS" if ok else "FAIL"} |'
        )

    lines += ['', '## Selected completed-close breakout threshold', '']
    if selected is None:
        lines += ['No threshold passed the frozen development gate simultaneously for F95 and F90.', '']
    else:
        lines += [
            f'**Selected from development only: {threshold_label(selected)}**.',
            ('This means a completed 5m close strictly above H.' if selected == 0.0 else
             f'This means a completed 5m close at or above **H + {selected:.3f}R**.'), '',
            'Historical replication:', '',
            '| Partition | Retest | N | Reach | Resolved upside | Gate |',
            '|---|---|---:|---:|---:|---|',
        ]
        for part, f, r, ok in reps:
            lines.append(
                f'| {part} | {retest_label(f)} | {int(r.retest_cohort_n)} | {pct(r.threshold_reach_rate)} | '
                f'{pct(r.resolved_upside_rate)} | {"PASS" if ok else "FAIL"} |'
            )
        pooled95 = S[(S.partition == 'POOLED_MAJOR') & (S.retest_fraction == .95) & (S.extension == selected)].iloc[0]
        pooled90 = S[(S.partition == 'POOLED_MAJOR') & (S.retest_fraction == .90) & (S.extension == selected)].iloc[0]
        lines += ['',
            f'Pooled F95: N **{int(pooled95.retest_cohort_n)}**, reach **{pct(pooled95.threshold_reach_rate)}**, resolved **{pct(pooled95.resolved_upside_rate)}**, median retest->threshold **{int(pooled95.median_minutes_retest_to_threshold) if not pd.isna(pooled95.median_minutes_retest_to_threshold) else "-"}m**.',
            f'Pooled F90: N **{int(pooled90.retest_cohort_n)}**, reach **{pct(pooled90.threshold_reach_rate)}**, resolved **{pct(pooled90.resolved_upside_rate)}**, median retest->threshold **{int(pooled90.median_minutes_retest_to_threshold) if not pd.isna(pooled90.median_minutes_retest_to_threshold) else "-"}m**.',
            ''
        ]

    # Descriptive High-arrival context at B00 row (same cohort, independent of threshold selection).
    for f in RETESTS:
        r = S[(S.partition == 'POOLED_MAJOR') & (S.retest_fraction == f) & (S.extension == 0.0)].iloc[0]
        lines.append(
            f'{retest_label(f)} pooled first later High-arrival rate: **{pct(r.high_arrival_rate)}**; median **{int(r.median_minutes_retest_to_high_arrival) if not pd.isna(r.median_minutes_retest_to_high_arrival) else "-"}m**.'
        )

    lines += ['', f'**Status: {status}**', '', 'Stop after Z3. No entry or TP/SL milestone was run automatically.']
    OUT_RESULT.write_text('\n'.join(lines) + '\n')
    print(OUT_RESULT.read_text())


if __name__ == '__main__':
    main()
