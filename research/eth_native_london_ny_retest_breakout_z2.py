#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_NATIVE_LONDON_NY_RETEST_BREAKOUT_Z2'
OUT_WINDOWS = ROOT / f'{PFX}_Windows.csv'
OUT_AUDIT = ROOT / f'{PFX}_LevelAudit.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_LEADER = ROOT / f'{PFX}_DevelopmentLeaderboard.csv'
OUT_RESULT = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
PROVENANCE = ROOT / 'ETH_NATIVE_LONDON_NY_CLOCK_Z1_CANONICAL.txt'

BAR5 = pd.Timedelta(minutes=5)
REF_START_MIN_UTC = 11 * 60 + 30
REF_DUR = pd.Timedelta(hours=5, minutes=30)
EXE_DUR = pd.Timedelta(hours=6, minutes=30)
GRID = [x / 100.0 for x in range(95, 0, -5)]
MAJOR = ('external', 'development', 'reference_validation')
EXPECTED_PROVENANCE = {
    'status': 'ETH_NATIVE_LONDON_NY_CLOCK_Z1_SUPPORTED',
    'reference_start_utc': '11:30',
    'reference_start_wib': '18:30',
    'execution_start_utc': '17:00',
    'execution_start_wib': '00:00',
    'reference_bars_5m': '66',
    'execution_bars_5m': '78',
}


def hhmm(minute: int) -> str:
    minute %= 1440
    return f'{minute // 60:02d}:{minute % 60:02d}'


def frac_label(f: float) -> str:
    return f'F{int(round(f * 100)):02d}'


def read_provenance() -> dict[str, str]:
    if not PROVENANCE.exists():
        raise RuntimeError(f'missing canonical Z1 provenance file: {PROVENANCE.name}')
    out: dict[str, str] = {}
    for raw in PROVENANCE.read_text().splitlines():
        raw = raw.strip()
        if not raw or '=' not in raw:
            continue
        k, v = raw.split('=', 1)
        out[k.strip()] = v.strip()
    for k, v in EXPECTED_PROVENANCE.items():
        if out.get(k) != v:
            raise AssertionError(f'Z1 provenance mismatch for {k}: got={out.get(k)!r}, expected={v!r}')
    return out


def partition_for_window(a: pd.Timestamp, z: pd.Timestamp):
    for name, (pa, pz) in base.PARTS.items():
        if pa <= a and z <= pz:
            return name
    return None


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = k / n
    zz = z * z
    den = 1.0 + zz / n
    center = p + zz / (2.0 * n)
    rad = z * math.sqrt((p * (1.0 - p) + zz / (4.0 * n)) / n)
    return (center - rad) / den


def analyze_execution(exe: pd.DataFrame, H: float, L: float, execution_start: pd.Timestamp):
    if not H > L:
        raise AssertionError('invalid reference range')

    hi_touching = False
    lo_touching = False
    hi_visits = 0
    lo_visits = 0

    k1_start = pd.NaT
    k1_ts = pd.NaT
    leave_start = pd.NaT
    leave_ts = pd.NaT
    eligible_start = pd.NaT

    terminal = 'NO_SIGNAL'
    terminal_start = pd.NaT
    terminal_ts = pd.NaT

    retest_ts = {f: pd.NaT for f in GRID}
    retest_start = {f: pd.NaT for f in GRID}
    level_price = {f: L + f * (H - L) for f in GRID}

    k1_found = False
    causal_leave = False

    for ts, r in exe.iterrows():
        hi = float(r.high)
        lo = float(r.low)
        cl = float(r.close)

        # Before K1: reproduce strict-break-first B27Q semantics exactly.
        if not k1_found:
            if cl > H:
                terminal = 'BULL_BREAK_BEFORE_SIGNAL'
                terminal_start = ts
                terminal_ts = ts + BAR5
                break
            if cl < L:
                terminal = 'BEAR_BREAK_BEFORE_SIGNAL'
                terminal_start = ts
                terminal_ts = ts + BAR5
                break

            hit_hi = hi >= H and cl <= H
            hit_lo = lo <= L and cl >= L
            if hit_hi and hit_lo:
                terminal = 'AMBIGUOUS_BOTH_LEVELS_BEFORE_SIGNAL'
                terminal_start = ts
                terminal_ts = ts + BAR5
                break

            if hit_hi and not hi_touching:
                hi_visits += 1
                if hi_visits == 1 and lo_visits == 0:
                    k1_found = True
                    k1_start = ts
                    k1_ts = ts + BAR5
                    terminal = 'K1_ACTIVE'

            if hit_lo and not lo_touching:
                lo_visits += 1

            hi_touching = bool(hit_hi)
            lo_touching = bool(hit_lo)
            continue

        # After K1 but before causal leave: terminal close still wins first.
        if not causal_leave:
            if cl > H:
                terminal = 'TARGET_BREAK_BEFORE_LEAVE'
                terminal_start = ts
                terminal_ts = ts + BAR5
                break
            if cl < L:
                terminal = 'OPPOSITE_BREAK_BEFORE_LEAVE'
                terminal_start = ts
                terminal_ts = ts + BAR5
                break

            hit_hi = hi >= H and cl <= H
            if hit_hi:
                # Still same contiguous K1 High-touch episode.
                continue

            # First completed non-High-touch, non-terminal bar is causal leave.
            causal_leave = True
            leave_start = ts
            leave_ts = ts + BAR5
            eligible_start = leave_ts  # next raw 5m bar opens exactly here
            terminal = 'NO_BREAK'
            continue

        # First eligible bar must be exactly the bar starting at leave close.
        if ts < eligible_start:
            raise AssertionError('observed a post-leave bar before eligible_start')

        # Terminal is evaluated BEFORE retest credit: same-bar retest+breakout is forbidden.
        if cl > H:
            terminal = 'TARGET_BREAK'
            terminal_start = ts
            terminal_ts = ts + BAR5
            break
        if cl < L:
            terminal = 'OPPOSITE_BREAK'
            terminal_start = ts
            terminal_ts = ts + BAR5
            break

        # Non-terminal completed bar may establish any previously unseen nested retest levels.
        completed_ts = ts + BAR5
        for f in GRID:
            if pd.isna(retest_ts[f]) and lo <= level_price[f]:
                retest_start[f] = ts
                retest_ts[f] = completed_ts

    if k1_found and not causal_leave and terminal == 'K1_ACTIVE':
        terminal = 'NO_LEAVE_BY_SESSION_END'
    elif k1_found and causal_leave and terminal == 'NO_BREAK':
        terminal = 'NO_BREAK'

    session = {
        'k1_found': bool(k1_found),
        'k1_start': k1_start,
        'k1_ts': k1_ts,
        'causal_leave': bool(causal_leave),
        'leave_start': leave_start,
        'leave_ts': leave_ts,
        'eligible_start': eligible_start,
        'terminal': terminal,
        'terminal_start': terminal_start,
        'terminal_ts': terminal_ts,
        'hi_visits_before_signal': 0 if k1_found else hi_visits,
        'low_visits_known': lo_visits,
    }

    levels = []
    if k1_found:
        for f in GRID:
            rt = retest_ts[f]
            retested = not pd.isna(rt)
            if retested:
                if terminal == 'TARGET_BREAK':
                    outcome = 'TARGET_BREAK'
                elif terminal == 'OPPOSITE_BREAK':
                    outcome = 'OPPOSITE_BREAK'
                elif terminal == 'NO_BREAK':
                    outcome = 'NO_BREAK'
                else:
                    # A credited post-leave retest cannot precede a pre-leave terminal.
                    raise AssertionError(f'invalid terminal after credited retest: {terminal}')
            else:
                outcome = 'NO_RETEST'

            if retested and not pd.isna(terminal_ts) and terminal in ('TARGET_BREAK', 'OPPOSITE_BREAK'):
                if not terminal_ts > rt:
                    raise AssertionError('terminal timestamp must be strictly later than credited retest timestamp')

            levels.append({
                'fraction': f,
                'level': frac_label(f),
                'level_price': level_price[f],
                'retested': retested,
                'retest_start': retest_start[f],
                'retest_ts': rt,
                'outcome': outcome,
                'minutes_retest_to_target': (
                    float((terminal_ts - rt) / pd.Timedelta(minutes=1))
                    if retested and terminal == 'TARGET_BREAK' else np.nan
                ),
                'minutes_execution_to_retest': (
                    float((rt - execution_start) / pd.Timedelta(minutes=1))
                    if retested else np.nan
                ),
            })

    return session, levels


def scan(x5: pd.DataFrame):
    windows = []
    audit = []
    anchors = pd.date_range(base.START.normalize(), base.END.normalize(), freq='D', tz='UTC')

    for day in anchors:
        rs = day + pd.Timedelta(minutes=REF_START_MIN_UTC)
        re = rs + REF_DUR
        ee = re + EXE_DUR
        if ee > base.END:
            continue
        if re.weekday() >= 5:  # Z1 freezes weekday at execution start.
            continue
        part = partition_for_window(rs, ee)
        if part is None:
            continue

        ref = base.fast_slice(x5, rs, re)
        exe = base.fast_slice(x5, re, ee)
        if len(ref) != 66 or len(exe) != 78:
            continue

        H = float(ref.high.max())
        L = float(ref.low.min())
        sess, levels = analyze_execution(exe, H, L, re)
        session_id = f'{rs.isoformat()}__{part}'

        windows.append({
            'session_id': session_id,
            'partition': part,
            'reference_start': rs,
            'execution_start': re,
            'execution_end': ee,
            'H': H,
            'L': L,
            'range': H - L,
            **sess,
        })

        for lev in levels:
            audit.append({
                'session_id': session_id,
                'partition': part,
                'reference_start': rs,
                'execution_start': re,
                'execution_end': ee,
                'H': H,
                'L': L,
                'range': H - L,
                'k1_start': sess['k1_start'],
                'k1_ts': sess['k1_ts'],
                'causal_leave': sess['causal_leave'],
                'leave_start': sess['leave_start'],
                'leave_ts': sess['leave_ts'],
                'eligible_start': sess['eligible_start'],
                'terminal': sess['terminal'],
                'terminal_start': sess['terminal_start'],
                'terminal_ts': sess['terminal_ts'],
                **lev,
            })

    return pd.DataFrame(windows), pd.DataFrame(audit)


def summarize(W: pd.DataFrame, A: pd.DataFrame):
    rows = []
    for f in GRID:
        label = frac_label(f)
        for part in (*base.PARTS.keys(), 'POOLED_MAJOR'):
            if part == 'POOLED_MAJOR':
                w = W[W.partition.isin(MAJOR)]
                a = A[(A.partition.isin(MAJOR)) & (A.fraction == f)]
            else:
                w = W[W.partition == part]
                a = A[(A.partition == part) & (A.fraction == f)]

            k1 = int(w.k1_found.astype(bool).sum()) if len(w) else 0
            leaves = int((w.k1_found.astype(bool) & w.causal_leave.astype(bool)).sum()) if len(w) else 0
            r = a[a.retested.astype(bool)] if len(a) else a
            n = len(r)
            t = int((r.outcome == 'TARGET_BREAK').sum()) if n else 0
            o = int((r.outcome == 'OPPOSITE_BREAK').sum()) if n else 0
            nb = int((r.outcome == 'NO_BREAK').sum()) if n else 0
            if n and (t + o + nb != n):
                raise AssertionError('retested-level outcomes do not reconcile')

            rows.append({
                'fraction': f,
                'level': label,
                'partition': part,
                'complete_sessions': len(w),
                'k1_opp0_setups': k1,
                'causal_leave_setups': leaves,
                'retest_count': n,
                'retest_rate_among_leaves': n / leaves if leaves else np.nan,
                'target_break': t,
                'opposite_break': o,
                'no_break': nb,
                'target_break_rate': t / n if n else np.nan,
                'resolved_same_side_rate': t / (t + o) if (t + o) else np.nan,
                'wilson_lb95_target': wilson_lb(t, n),
                'median_minutes_retest_to_target': pd.to_numeric(
                    r.loc[r.outcome == 'TARGET_BREAK', 'minutes_retest_to_target'], errors='coerce'
                ).median() if t else np.nan,
                'median_minutes_execution_to_retest': pd.to_numeric(
                    r['minutes_execution_to_retest'], errors='coerce'
                ).median() if n else np.nan,
            })
    return pd.DataFrame(rows)


def build_leaderboard(S: pd.DataFrame):
    dev = S[S.partition == 'development'].copy().sort_values('fraction', ascending=False).reset_index(drop=True)
    lookup = {float(r.fraction): r for r in dev.itertuples(index=False)}
    eligible = []
    stable = []

    for r in dev.itertuples(index=False):
        e = (
            int(r.retest_count) >= 50 and
            float(r.target_break_rate) >= .70 and
            float(r.resolved_same_side_rate) >= .85
        )

        idx = GRID.index(float(r.fraction))
        neighbors = []
        if idx > 0:
            neighbors.append(GRID[idx - 1])
        if idx < len(GRID) - 1:
            neighbors.append(GRID[idx + 1])

        def neighbor_ok(x):
            return (
                int(x.retest_count) >= 40 and
                float(x.target_break_rate) >= .65 and
                float(x.resolved_same_side_rate) >= .80
            )

        s = all(neighbor_ok(lookup[n]) for n in neighbors)
        eligible.append(bool(e))
        stable.append(bool(s))

    dev['dev_eligible'] = eligible
    dev['local_stable'] = stable
    dev['candidate_eligible'] = dev.dev_eligible & dev.local_stable
    dev['dev_rank'] = np.nan

    cand = dev[dev.candidate_eligible].sort_values(
        ['wilson_lb95_target', 'target_break_rate', 'resolved_same_side_rate', 'retest_count', 'fraction'],
        ascending=[False, False, False, False, False],
    )
    for rank, idx in enumerate(cand.index, start=1):
        dev.loc[idx, 'dev_rank'] = rank

    selected = None if len(cand) == 0 else cand.iloc[0]
    return dev.sort_values(['dev_rank', 'fraction'], na_position='last', ascending=[True, False]), selected


def replication(S: pd.DataFrame, selected):
    if selected is None:
        return [], False
    f = float(selected.fraction)
    rows = []
    all_ok = True
    for part in ('external', 'reference_validation'):
        r = S[(S.partition == part) & (S.fraction == f)].iloc[0]
        ok = (
            int(r.retest_count) >= 30 and
            float(r.target_break_rate) >= .65 and
            float(r.resolved_same_side_rate) >= .80 and
            int(r.target_break) > int(r.opposite_break)
        )
        rows.append((part, r, bool(ok)))
        all_ok = all_ok and bool(ok)
    return rows, all_ok


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 17:00', periods=8, freq='5min', tz='UTC')

    def df(rows):
        return pd.DataFrame(rows, index=idx[:len(rows)], columns=['open', 'high', 'low', 'close'])

    # Consecutive K1 touch episode -> leave -> next-bar F85 retest -> later strict breakout.
    x = df([
        [99.0, 100.2, 98.8, 99.5],  # K1
        [99.5, 100.1, 98.9, 99.2],  # same touch episode
        [99.2, 99.6, 97.0, 98.0],   # causal leave; F85 crossed here but forbidden
        [98.8, 99.2, 98.4, 98.9],   # first eligible; F85 retest completes here
        [98.9, 99.8, 98.7, 99.5],
        [99.5, 101.0, 99.0, 100.4], # strict target breakout
    ])
    s, levels = analyze_execution(x, H, L, idx[0])
    d = {z['level']: z for z in levels}
    assert s['k1_found'] and s['causal_leave']
    assert s['leave_start'] == idx[2]
    assert s['eligible_start'] == idx[3]
    assert d['F85']['retested'] and d['F85']['retest_start'] == idx[3]
    assert s['terminal'] == 'TARGET_BREAK'
    assert s['terminal_ts'] > d['F85']['retest_ts']

    # Same-bar retest + strict breakout is terminal-first and cannot create F85 retest.
    x2 = df([
        [99.0, 100.2, 98.8, 99.5],
        [99.5, 100.1, 98.9, 99.2],
        [99.2, 99.6, 99.0, 99.1],
        [99.1, 101.0, 98.4, 100.3],
    ])
    s2, l2 = analyze_execution(x2, H, L, idx[0])
    d2 = {z['level']: z for z in l2}
    assert s2['terminal'] == 'TARGET_BREAK'
    assert not d2['F85']['retested']

    # Leave-bar F85 cross does not count if later eligible bars never retest F85.
    x3 = df([
        [99.0, 100.2, 98.8, 99.5],
        [99.5, 100.1, 98.9, 99.2],
        [99.2, 99.6, 97.0, 98.0],
        [99.0, 99.5, 98.7, 99.2],
        [99.2, 101.0, 99.0, 100.2],
    ])
    s3, l3 = analyze_execution(x3, H, L, idx[0])
    d3 = {z['level']: z for z in l3}
    assert s3['leave_start'] == idx[2]
    assert not d3['F85']['retested']

    # Retest then opposite strict break.
    x4 = df([
        [99.0, 100.2, 98.8, 99.5],
        [99.5, 100.1, 98.9, 99.2],
        [99.2, 99.6, 99.0, 99.1],
        [99.1, 99.4, 98.4, 98.8],
        [98.8, 99.0, 89.0, 89.7],
    ])
    s4, l4 = analyze_execution(x4, H, L, idx[0])
    d4 = {z['level']: z for z in l4}
    assert d4['F85']['retested'] and s4['terminal'] == 'OPPOSITE_BREAK'
    assert d4['F85']['outcome'] == 'OPPOSITE_BREAK'

    # Retest with no terminal by execution end.
    x5 = df([
        [99.0, 100.2, 98.8, 99.5],
        [99.5, 100.1, 98.9, 99.2],
        [99.2, 99.6, 99.0, 99.1],
        [99.1, 99.4, 98.4, 98.8],
        [98.8, 99.1, 98.3, 98.9],
    ])
    s5, l5 = analyze_execution(x5, H, L, idx[0])
    d5 = {z['level']: z for z in l5}
    assert d5['F85']['retested'] and s5['terminal'] == 'NO_BREAK'
    assert d5['F85']['outcome'] == 'NO_BREAK'

    # Low visit first blocks later High from being OPP0 K1.
    x6 = df([
        [92.0, 93.0, 89.8, 90.5],
        [90.5, 91.0, 90.1, 90.8],
        [99.0, 100.2, 98.8, 99.5],
        [99.5, 99.8, 99.0, 99.3],
    ])
    s6, l6 = analyze_execution(x6, H, L, idx[0])
    assert not s6['k1_found'] and len(l6) == 0

    assert len(GRID) == 19 and GRID[0] == .95 and GRID[-1] == .05


def pct(v):
    return '-' if pd.isna(v) else f'{100.0 * float(v):.1f}%'


def main():
    prov = read_provenance()
    synthetic_tests()

    x5, coverage = base.load5('ETHUSDT')
    if coverage < .995:
        raise RuntimeError(f'ETH raw 5m coverage too low: {coverage:.6f}')

    W, A = scan(x5)
    if len(W) == 0 or len(A) == 0:
        raise RuntimeError('Z2 scan produced no auditable setups')

    # Chronology audits over all credited retests.
    ar = A[A.retested.astype(bool)].copy()
    if len(ar):
        if not (pd.to_datetime(ar.retest_start, utc=True) >= pd.to_datetime(ar.eligible_start, utc=True)).all():
            raise AssertionError('credited retest begins before causal eligibility')
        terminal_rows = ar[ar.outcome.isin(['TARGET_BREAK', 'OPPOSITE_BREAK'])]
        if len(terminal_rows):
            if not (pd.to_datetime(terminal_rows.terminal_ts, utc=True) > pd.to_datetime(terminal_rows.retest_ts, utc=True)).all():
                raise AssertionError('terminal is not strictly later than retest')

    W.to_csv(OUT_WINDOWS, index=False)
    A.to_csv(OUT_AUDIT, index=False)

    S = summarize(W, A)
    S.to_csv(OUT_SUMMARY, index=False)
    L, selected = build_leaderboard(S)
    L.to_csv(OUT_LEADER, index=False)
    reps, replicated = replication(S, selected)

    if selected is None:
        status = 'ETH_NATIVE_LONDON_NY_RETEST_BREAKOUT_Z2_NO_DEV_CANDIDATE'
    elif replicated:
        status = 'ETH_NATIVE_LONDON_NY_RETEST_BREAKOUT_Z2_SUPPORTED'
    else:
        status = 'ETH_NATIVE_LONDON_NY_RETEST_BREAKOUT_Z2_CANDIDATE_NOT_REPLICATED'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH Native London->New York Retest-to-Breakout Discovery — Z2 Result', '',
        f'Canonical upstream Z1: **{prov["status"]}**; workflow run `{prov.get("workflow_run_id", "-")}`.',
        f'Frozen clock: reference **18:30-00:00 WIB**, execution **00:00-06:30 WIB**.',
        f'Raw ETHUSDT 5m coverage: **{coverage:.4%}**.',
        'Grid: **F95 to F05 in exact 5% steps (19 levels)**.',
        'Target is strict later 5m `close > H`; same-bar retest+breakout is forbidden by terminal-first chronology.',
        'Structural only: no entry execution, confirmation, TP/SL, fee, leverage, PnL, PF, or expectancy.', '',
        '## Development retest leaderboard', '',
        '| Rank | Level | Retests | Retest rate | Later breakout | Resolved | Wilson LB | Median retest->break | Eligible | Local stable |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---|---|',
    ]

    disp = L.sort_values(['dev_rank', 'fraction'], na_position='last', ascending=[True, False])
    for r in disp.itertuples(index=False):
        rank = '-' if pd.isna(r.dev_rank) else str(int(r.dev_rank))
        med = '-' if pd.isna(r.median_minutes_retest_to_target) else f'{float(r.median_minutes_retest_to_target):.0f}m'
        lines.append(
            f'| {rank} | {r.level} | {int(r.retest_count)} | {pct(r.retest_rate_among_leaves)} | '
            f'{pct(r.target_break_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95_target)} | '
            f'{med} | {"YES" if bool(r.dev_eligible) else "NO"} | {"YES" if bool(r.local_stable) else "NO"} |'
        )

    lines += ['', '## Selected ETH-native retest point', '']
    if selected is None:
        lines += ['No exact retest level passed the preregistered development eligibility + local-stability screen.', '']
    else:
        lines += [
            f'**Selected: {selected.level}** = {float(selected.fraction):.2f} of the frozen reference range from L to H.',
            f'Development: **{int(selected.retest_count)}** retests; later strict breakout **{pct(selected.target_break_rate)}**; '
            f'resolved **{pct(selected.resolved_same_side_rate)}**; Wilson LB **{pct(selected.wilson_lb95_target)}**.', '',
            'Historical replication:', '',
            '| Partition | Retests | Later breakout | Resolved | Gate |',
            '|---|---:|---:|---:|---|',
        ]
        for part, r, ok in reps:
            lines.append(
                f'| {part} | {int(r.retest_count)} | {pct(r.target_break_rate)} | '
                f'{pct(r.resolved_same_side_rate)} | {"PASS" if ok else "FAIL"} |'
            )
        pooled = S[(S.partition == 'POOLED_MAJOR') & (S.fraction == float(selected.fraction))].iloc[0]
        lines += [
            '',
            f'Pooled major: **{int(pooled.retest_count)}** retests; later strict breakout **{pct(pooled.target_break_rate)}**; '
            f'resolved **{pct(pooled.resolved_same_side_rate)}**; median retest->break **{float(pooled.median_minutes_retest_to_target):.0f}m**.'
        ]

    lines += ['', f'**Status: {status}**', '', 'Stop after Z2. No entry or TP/SL milestone was run automatically.']
    OUT_RESULT.write_text('\n'.join(lines) + '\n')
    print(OUT_RESULT.read_text())


if __name__ == '__main__':
    main()
