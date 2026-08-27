#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_native_london_ny_retest_breakout_z2 as z2

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_RESULT = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external', 'development', 'reference_validation')
COHORTS = {'F95': 0.95, 'F90': 0.90}
MODES = ('BREAKOUT_CLOSE_BENCHMARK', 'NEXT_OPEN', 'H_RETEST_LIMIT', 'H_REBREAK_NEXT_OPEN')
EXECUTABLE = ('NEXT_OPEN', 'H_RETEST_LIMIT', 'H_REBREAK_NEXT_OPEN')
CHECKS = {'C05': 0.05, 'C10': 0.10, 'C20': 0.20}
TIE_PRIORITY = {'H_RETEST_LIMIT': 0, 'NEXT_OPEN': 1, 'H_REBREAK_NEXT_OPEN': 2}


def fast_slice(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp):
    return base.fast_slice(x, a, z)


def bar_at(x: pd.DataFrame, ts: pd.Timestamp):
    if ts not in x.index:
        return None
    return x.loc[ts]


def build_cases(x5: pd.DataFrame):
    W, A = z2.scan(x5)
    rows = []
    for label, f in COHORTS.items():
        q = A[
            (A.partition.isin(MAJOR)) &
            (np.isclose(A.fraction.astype(float), f)) &
            (A.retested.astype(bool)) &
            (A.outcome == 'TARGET_BREAK')
        ].copy()
        for r in q.itertuples(index=False):
            bstart = pd.Timestamp(r.terminal_start)
            bts = pd.Timestamp(r.terminal_ts)
            rt = pd.Timestamp(r.retest_ts)
            ee = pd.Timestamp(r.execution_end)
            H = float(r.H); L = float(r.L); R = H - L
            if not R > 0:
                raise AssertionError('invalid R')
            b = bar_at(x5, bstart)
            if b is None:
                raise AssertionError('missing B00 bar')
            bclose = float(b.close)
            if not bclose > H:
                raise AssertionError('B00 close must be strictly above H')
            if not bts > rt:
                raise AssertionError('B00 must complete strictly after retest')
            rows.append({
                'cohort': label,
                'fraction': f,
                'session_id': str(r.session_id),
                'partition': str(r.partition),
                'reference_start': pd.Timestamp(r.reference_start),
                'execution_start': pd.Timestamp(r.execution_start),
                'execution_end': ee,
                'H': H, 'L': L, 'R': R,
                'retest_ts': rt,
                'breakout_start': bstart,
                'breakout_ts': bts,
                'breakout_close': bclose,
                'breakout_close_frac': (bclose - L) / R,
            })
    C = pd.DataFrame(rows)
    f95 = set(C.loc[C.cohort == 'F95', 'session_id'])
    f90 = set(C.loc[C.cohort == 'F90', 'session_id'])
    if not f90.issubset(f95):
        raise AssertionError('F90 B00 sessions must be subset of F95 B00 sessions')
    return C


def mode_entry(x5: pd.DataFrame, c, mode: str):
    H = float(c.H); L = float(c.L)
    bstart = pd.Timestamp(c.breakout_start)
    bts = pd.Timestamp(c.breakout_ts)
    ee = pd.Timestamp(c.execution_end)

    out = {
        'available': False,
        'cancel_reason': '',
        'entry_start': pd.NaT,
        'entry_ts': pd.NaT,
        'entry_price': np.nan,
        'eval_start': pd.NaT,
        'pre_eval_failure': False,
        'fill_bar_low': np.nan,
        'back_in_range_ts': pd.NaT,
        'rebreak_ts': pd.NaT,
    }

    if mode == 'BREAKOUT_CLOSE_BENCHMARK':
        out.update({
            'available': True,
            'entry_start': bstart,
            'entry_ts': bts,
            'entry_price': float(c.breakout_close),
            'eval_start': bts,
        })
        return out

    post = fast_slice(x5, bts, ee)
    if mode == 'NEXT_OPEN':
        if len(post) == 0 or post.index[0] != bts:
            out['cancel_reason'] = 'NO_NEXT_BAR_BEFORE_END'
            return out
        r = post.iloc[0]
        out.update({
            'available': True,
            'entry_start': post.index[0],
            'entry_ts': post.index[0],
            'entry_price': float(r.open),
            'eval_start': post.index[0],
        })
        if out['entry_start'] != bstart + BAR5:
            raise AssertionError('NEXT_OPEN is not immediate next raw 5m bar')
        return out

    if mode == 'H_RETEST_LIMIT':
        for ts, r in post.iterrows():
            lo = float(r.low); cl = float(r.close)
            # Fill credit precedes completed-close failure on the same bar.
            if lo <= H:
                out.update({
                    'available': True,
                    'entry_start': ts,
                    'entry_ts': ts + BAR5,
                    'entry_price': H,
                    'eval_start': ts + BAR5,
                    'pre_eval_failure': bool(cl < L),
                    'fill_bar_low': lo,
                })
                if ts == bstart:
                    raise AssertionError('H retest filled on breakout bar')
                return out
            if cl < L:
                out['cancel_reason'] = 'CLOSE_BELOW_L_BEFORE_H_RETEST'
                return out
        out['cancel_reason'] = 'NO_H_RETEST_BY_END'
        return out

    if mode == 'H_REBREAK_NEXT_OPEN':
        back = False
        back_ts = pd.NaT
        for ts, r in post.iterrows():
            cl = float(r.close)
            if cl < L:
                out['cancel_reason'] = 'CLOSE_BELOW_L_BEFORE_REBREAK_ENTRY'
                return out
            if not back:
                if cl <= H:
                    back = True
                    back_ts = ts + BAR5
                continue
            if cl > H:
                rb_ts = ts + BAR5
                next_start = rb_ts
                if next_start >= ee:
                    out['cancel_reason'] = 'NO_NEXT_BAR_AFTER_REBREAK'
                    return out
                nr = bar_at(x5, next_start)
                if nr is None:
                    out['cancel_reason'] = 'MISSING_NEXT_BAR_AFTER_REBREAK'
                    return out
                out.update({
                    'available': True,
                    'entry_start': next_start,
                    'entry_ts': next_start,
                    'entry_price': float(nr.open),
                    'eval_start': next_start,
                    'back_in_range_ts': back_ts,
                    'rebreak_ts': rb_ts,
                })
                if not (back_ts < rb_ts <= next_start):
                    raise AssertionError('invalid H rebreak chronology')
                return out
        out['cancel_reason'] = 'NO_REBREAK_ENTRY_BY_END'
        return out

    raise ValueError(mode)


def evaluate_path(x5: pd.DataFrame, c, ent: dict):
    H = float(c.H); L = float(c.L); R = float(c.R); ee = pd.Timestamp(c.execution_end)
    out = {
        'entry_frac': np.nan,
        'C05_reached': False, 'C10_reached': False, 'C20_reached': False,
        'C05_ts': pd.NaT, 'C10_ts': pd.NaT, 'C20_ts': pd.NaT,
        'C05_already_passed': False, 'C10_already_passed': False, 'C20_already_passed': False,
        'close_below_L_before_C20': False,
        'close_below_L_ts': pd.NaT,
        'mfe_frac': np.nan, 'mae_frac': np.nan, 'adverse_R': np.nan,
    }
    if not ent['available']:
        return out

    ep = float(ent['entry_price'])
    ef = (ep - L) / R
    out['entry_frac'] = ef
    cp = {k: H + v * R for k, v in CHECKS.items()}
    eligible = {k: ep < p for k, p in cp.items()}
    for k in CHECKS:
        out[f'{k}_already_passed'] = not eligible[k]

    if ent.get('pre_eval_failure', False):
        out['close_below_L_before_C20'] = True
        out['close_below_L_ts'] = pd.Timestamp(ent['entry_ts'])
        if not pd.isna(ent.get('fill_bar_low', np.nan)):
            lowf = (float(ent['fill_bar_low']) - L) / R
            out['mae_frac'] = lowf
            out['adverse_R'] = max(0.0, ef - lowf)
        return out

    a = pd.Timestamp(ent['eval_start'])
    path = fast_slice(x5, a, ee)
    if len(path) == 0:
        return out

    max_hi = -np.inf
    min_lo = np.inf
    fail = False
    fail_ts = pd.NaT
    for ts, r in path.iterrows():
        hi = float(r.high); lo = float(r.low); cl = float(r.close)
        max_hi = max(max_hi, hi)
        min_lo = min(min_lo, lo)
        for k in ('C05', 'C10', 'C20'):
            if eligible[k] and not out[f'{k}_reached'] and hi >= cp[k]:
                out[f'{k}_reached'] = True
                out[f'{k}_ts'] = ts + BAR5
        if cl < L:
            fail = True
            fail_ts = ts + BAR5
            break

    if max_hi > -np.inf:
        out['mfe_frac'] = (max_hi - L) / R
        out['mae_frac'] = (min_lo - L) / R
        out['adverse_R'] = max(0.0, ef - out['mae_frac'])
    if fail and not out['C20_reached']:
        out['close_below_L_before_C20'] = True
        out['close_below_L_ts'] = fail_ts

    if out['C20_reached'] and not (out['C10_reached'] or out['C10_already_passed']):
        raise AssertionError('C20 without C10 state')
    if out['C10_reached'] and not (out['C05_reached'] or out['C05_already_passed']):
        raise AssertionError('C10 without C05 state')
    return out


def build_audit(x5: pd.DataFrame, C: pd.DataFrame):
    rows = []
    for c in C.itertuples(index=False):
        for mode in MODES:
            ent = mode_entry(x5, c, mode)
            ev = evaluate_path(x5, c, ent)
            row = {
                'cohort': c.cohort, 'fraction': c.fraction,
                'session_id': c.session_id, 'partition': c.partition,
                'reference_start': c.reference_start,
                'execution_start': c.execution_start, 'execution_end': c.execution_end,
                'H': c.H, 'L': c.L, 'R': c.R,
                'retest_ts': c.retest_ts,
                'breakout_start': c.breakout_start, 'breakout_ts': c.breakout_ts,
                'breakout_close': c.breakout_close, 'breakout_close_frac': c.breakout_close_frac,
                'mode': mode,
                **ent,
                **ev,
            }
            if ent['available'] and pd.Timestamp(ent['entry_start']) >= pd.Timestamp(c.execution_end):
                raise AssertionError('entry at/after execution end')
            rows.append(row)
    return pd.DataFrame(rows)


def summarize(C: pd.DataFrame, A: pd.DataFrame):
    rows = []
    parts = (*MAJOR, 'POOLED_MAJOR')
    for cohort in COHORTS:
        for mode in MODES:
            for part in parts:
                if part == 'POOLED_MAJOR':
                    c = C[(C.cohort == cohort) & C.partition.isin(MAJOR)]
                    a = A[(A.cohort == cohort) & (A.mode == mode) & A.partition.isin(MAJOR)]
                else:
                    c = C[(C.cohort == cohort) & (C.partition == part)]
                    a = A[(A.cohort == cohort) & (A.mode == mode) & (A.partition == part)]
                q = a[a.available.astype(bool)]
                denom = len(c); n = len(q)
                row = {
                    'cohort': cohort, 'mode': mode, 'partition': part,
                    'b00_cases': denom, 'available_entries': n,
                    'participation': n / denom if denom else np.nan,
                    'median_entry_frac': pd.to_numeric(q.entry_frac, errors='coerce').median() if n else np.nan,
                    'median_adverse_R': pd.to_numeric(q.adverse_R, errors='coerce').median() if n else np.nan,
                    'p90_adverse_R': pd.to_numeric(q.adverse_R, errors='coerce').quantile(.90) if n else np.nan,
                    'median_mfe_frac': pd.to_numeric(q.mfe_frac, errors='coerce').median() if n else np.nan,
                    'close_below_L_before_C20': int(q.close_below_L_before_C20.astype(bool).sum()) if n else 0,
                }
                for k in ('C05', 'C10', 'C20'):
                    hits = int(q[f'{k}_reached'].astype(bool).sum()) if n else 0
                    passed = int(q[f'{k}_already_passed'].astype(bool).sum()) if n else 0
                    row[f'{k}_reach'] = hits
                    row[f'{k}_reach_rate'] = hits / n if n else np.nan
                    row[f'{k}_already_passed'] = passed
                    if hits:
                        mins = []
                        for r in q[q[f'{k}_reached'].astype(bool)].itertuples(index=False):
                            ets = pd.Timestamp(r.entry_ts)
                            cts = pd.Timestamp(getattr(r, f'{k}_ts'))
                            mins.append(float((cts - ets) / pd.Timedelta(minutes=1)))
                        row[f'median_minutes_to_{k}'] = float(np.median(mins))
                    else:
                        row[f'median_minutes_to_{k}'] = np.nan
                row['unresolved_no_post_entry_C20'] = n - row['C20_reach'] - row['close_below_L_before_C20']
                rows.append(row)
    return pd.DataFrame(rows)


def select_development(S: pd.DataFrame):
    cand = []
    for mode in EXECUTABLE:
        qq = S[(S.partition == 'development') & (S.mode == mode) & S.cohort.isin(COHORTS)]
        if len(qq) != 2:
            continue
        ok = True
        for r in qq.itertuples(index=False):
            ok = ok and (
                int(r.available_entries) >= 35 and
                float(r.participation) >= .40 and
                float(r.C10_reach_rate) >= .60 and
                float(r.C20_reach_rate) >= .45 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
        if ok:
            cand.append({
                'mode': mode,
                'min_c20': float(qq.C20_reach_rate.min()),
                'min_c10': float(qq.C10_reach_rate.min()),
                'entry_frac': float(qq.median_entry_frac.max()),
                'min_part': float(qq.participation.min()),
                'tie': TIE_PRIORITY[mode],
            })
    if not cand:
        return None, pd.DataFrame()
    L = pd.DataFrame(cand).sort_values(
        ['min_c20', 'min_c10', 'entry_frac', 'min_part', 'tie'],
        ascending=[False, False, True, False, True]
    ).reset_index(drop=True)
    return str(L.iloc[0].mode), L


def replication(S: pd.DataFrame, mode: str | None):
    rows = []
    if mode is None:
        return rows, False
    all_ok = True
    for part in ('external', 'reference_validation'):
        for cohort in COHORTS:
            r = S[(S.partition == part) & (S.mode == mode) & (S.cohort == cohort)].iloc[0]
            ok = (
                int(r.available_entries) >= 20 and
                float(r.participation) >= .30 and
                float(r.C10_reach_rate) >= .55 and
                float(r.C20_reach_rate) >= .40 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
            all_ok = all_ok and ok
            rows.append((part, cohort, r, ok))
    return rows, all_ok


def pct(v):
    return '-' if pd.isna(v) else f'{100.0 * float(v):.1f}%'


def synthetic_tests():
    idx = pd.date_range('2026-01-05 17:00', periods=8, freq='5min', tz='UTC')
    x = pd.DataFrame([
        [100.5,101.0,100.2,100.8],
        [100.8,101.2,99.8,100.3],
        [100.3,100.6,99.7,99.9],
        [99.9,100.5,99.8,100.4],
        [100.4,101.4,100.2,101.0],
        [101.0,102.5,100.9,102.0],
        [102.0,102.2,101.2,101.5],
        [101.5,101.7,100.8,101.0],
    ], index=idx, columns=['open','high','low','close'])
    class C: pass
    c = C(); c.H=100.; c.L=90.; c.R=10.; c.breakout_start=idx[0]; c.breakout_ts=idx[1]; c.execution_end=idx[-1]+BAR5; c.breakout_close=100.8
    e = mode_entry(x, c, 'NEXT_OPEN')
    assert e['available'] and e['entry_start'] == idx[1]
    e2 = mode_entry(x, c, 'H_RETEST_LIMIT')
    assert e2['available'] and e2['entry_start'] == idx[1] and e2['eval_start'] == idx[2]
    e3 = mode_entry(x, c, 'H_REBREAK_NEXT_OPEN')
    assert e3['available'] and e3['entry_start'] == idx[4]


def main():
    synthetic_tests()
    z2.read_provenance()
    x5, coverage = base.load5('ETHUSDT')
    if coverage < .995:
        raise RuntimeError(f'ETH raw 5m coverage too low: {coverage:.6f}')

    C = build_cases(x5)
    A = build_audit(x5, C)
    S = summarize(C, A)

    A.to_csv(OUT_AUDIT, index=False)
    S.to_csv(OUT_SUMMARY, index=False)

    selected, leaderboard = select_development(S)
    reps, supported = replication(S, selected)
    if selected is None:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_NO_DEV_CANDIDATE'
    elif supported:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_SUPPORTED'
    else:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_CANDIDATE_NOT_REPLICATED'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH Native London->New York Entry Discovery — Z4 Result', '',
        f'Raw ETHUSDT 5m coverage: **{coverage:.4%}**.',
        'Frozen lineage: 18:30-00:00 WIB reference -> 00:00-06:30 WIB execution; F95/F90 shallow retest; B00 completed 5m close >H.',
        'C05/C10/C20 are structural diagnostics only, not TP.', '',
        '## Pooled major entry-mode comparison', '',
        '| Cohort | Mode | B00 | Entries | Participation | Median entry frac | C10 post-entry | C20 post-entry | Close<L before C20 | Median adverse R |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    pooled = S[S.partition == 'POOLED_MAJOR']
    for cohort in COHORTS:
        for mode in MODES:
            r = pooled[(pooled.cohort == cohort) & (pooled.mode == mode)].iloc[0]
            lines.append(
                f'| {cohort} | {mode} | {int(r.b00_cases)} | {int(r.available_entries)} | {pct(r.participation)} | '
                f'{float(r.median_entry_frac):.3f} | {pct(r.C10_reach_rate)} | {pct(r.C20_reach_rate)} | '
                f'{int(r.close_below_L_before_C20)} | {float(r.median_adverse_R):.3f} |'
            )

    lines += ['', '## Development selection', '']
    if selected is None:
        lines += ['No executable entry mode passed the frozen development gate for both F95 and F90.', '']
    else:
        lines += [f'Selected development mode: **{selected}**.', '']
        for cohort in COHORTS:
            r = S[(S.partition == 'development') & (S.mode == selected) & (S.cohort == cohort)].iloc[0]
            lines.append(
                f'- {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({pct(r.participation)}), '
                f'C10={pct(r.C10_reach_rate)}, C20={pct(r.C20_reach_rate)}, median entry frac={float(r.median_entry_frac):.3f}.'
            )
        lines += ['', 'Historical replication:', '']
        for part, cohort, r, ok in reps:
            lines.append(
                f'- {part} {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({pct(r.participation)}), '
                f'C10={pct(r.C10_reach_rate)}, C20={pct(r.C20_reach_rate)} -> {"PASS" if ok else "FAIL"}.'
            )

    lines += ['', f'**Status: {status}**', '', 'Stop after Z4. No TP/SL/PnL milestone was run automatically.']
    OUT_RESULT.write_text('\n'.join(lines) + '\n')
    print(OUT_RESULT.read_text())


if __name__ == '__main__':
    main()
