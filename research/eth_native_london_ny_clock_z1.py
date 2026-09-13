#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_NATIVE_LONDON_NY_CLOCK_Z1'
OUT_WINDOWS = ROOT / f'{PFX}_Windows.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_LEADER = ROOT / f'{PFX}_DevelopmentLeaderboard.csv'
OUT_PARITY = ROOT / f'{PFX}_LondonParity.csv'
OUT_RESULT = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

REF_DUR = pd.Timedelta(hours=5, minutes=30)
EXE_DUR = pd.Timedelta(hours=6, minutes=30)
CLOCKS = list(range(0, 24 * 60, 30))
MAJOR = ('external', 'development', 'reference_validation')

PARITY = {
    'external': {'sessions': 523, 'signals': 120, 'target': 103, 'opposite': 3, 'no_break': 14},
    'development': {'sessions': 782, 'signals': 173, 'target': 137, 'opposite': 21, 'no_break': 15},
    'reference_validation': {'sessions': 411, 'signals': 85, 'target': 69, 'opposite': 12, 'no_break': 4},
    'POOLED_MAJOR': {'signals': 378, 'target': 309, 'opposite': 36, 'no_break': 33},
}


def hhmm(minute: int) -> str:
    minute %= 1440
    return f'{minute // 60:02d}:{minute % 60:02d}'


def wib(minute_utc: int) -> str:
    return hhmm(minute_utc + 7 * 60)


def clock_label(start_min: int) -> str:
    if start_min == 8 * 60:
        return 'LONDON'
    return wib(start_min)


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


def scan_clock(x5: pd.DataFrame, start_min: int):
    rows = []
    anchors = pd.date_range(base.START.normalize(), base.END.normalize(), freq='D', tz='UTC')
    for day in anchors:
        rs = day + pd.Timedelta(minutes=start_min)
        re = rs + REF_DUR
        ee = re + EXE_DUR
        if ee > base.END:
            continue
        if re.weekday() >= 5:  # weekday is execution start, exactly as frozen BTC clock rotation
            continue
        part = partition_for_window(rs, ee)
        if part is None:
            continue
        ref = base.fast_slice(x5, rs, re)
        exe = base.fast_slice(x5, re, ee)
        if len(ref) != 66 or len(exe) != 78:
            continue
        _, sig = base.analyze_session('ETHUSDT', part, rs.normalize(), ref, exe)
        row = {
            'clock_start_min_utc': start_min,
            'clock_label': clock_label(start_min),
            'reference_start_wib': wib(start_min),
            'execution_start_wib': wib(start_min + 330),
            'partition': part,
            'reference_start': rs,
            'reference_end_execution_start': re,
            'execution_end': ee,
            'H': float(ref.high.max()),
            'L': float(ref.low.min()),
            'signal': sig is not None,
            'signal_ts': pd.NaT,
            'terminal': 'NO_SIGNAL',
            'terminal_ts': pd.NaT,
            'minutes_to_target_break': np.nan,
        }
        if sig is not None:
            row.update({
                'signal_ts': sig['signal_ts'],
                'terminal': sig['terminal'],
                'terminal_ts': sig['terminal_ts'],
                'minutes_to_target_break': sig['minutes_to_target_break'],
            })
        rows.append(row)
    return rows


def summarize(W: pd.DataFrame):
    rows = []
    for start_min in CLOCKS:
        cw = W[W.clock_start_min_utc == start_min]
        for part in (*base.PARTS.keys(), 'POOLED_MAJOR'):
            if part == 'POOLED_MAJOR':
                g = cw[cw.partition.isin(MAJOR)]
            else:
                g = cw[cw.partition == part]
            s = g[g.signal.astype(bool)]
            n = len(s)
            t = int((s.terminal == 'TARGET_BREAK').sum()) if n else 0
            o = int((s.terminal == 'OPPOSITE_BREAK').sum()) if n else 0
            nb = int((s.terminal == 'NO_BREAK').sum()) if n else 0
            other = n - t - o - nb
            rows.append({
                'clock_start_min_utc': start_min,
                'clock_label': clock_label(start_min),
                'reference_start_utc': hhmm(start_min),
                'reference_start_wib': wib(start_min),
                'execution_start_utc': hhmm(start_min + 330),
                'execution_start_wib': wib(start_min + 330),
                'partition': part,
                'complete_sessions': len(g),
                'k1_opp0_signals': n,
                'k1_rate': n / len(g) if len(g) else np.nan,
                'target_break': t,
                'opposite_break': o,
                'no_break': nb,
                'other_terminal': other,
                'target_break_rate': t / n if n else np.nan,
                'resolved_same_side_rate': t / (t + o) if (t + o) else np.nan,
                'wilson_lb95_target': wilson_lb(t, n),
                'median_minutes_to_target': pd.to_numeric(
                    s.loc[s.terminal == 'TARGET_BREAK', 'minutes_to_target_break'], errors='coerce'
                ).median() if t else np.nan,
            })
    return pd.DataFrame(rows)


def parity_audit(S: pd.DataFrame):
    rows = []
    for part, exp in PARITY.items():
        r = S[(S.clock_start_min_utc == 480) & (S.partition == part)].iloc[0]
        got = {
            'sessions': int(r.complete_sessions),
            'signals': int(r.k1_opp0_signals),
            'target': int(r.target_break),
            'opposite': int(r.opposite_break),
            'no_break': int(r.no_break),
        }
        ok = True
        for key, val in exp.items():
            ok = ok and got[key] == val
        rows.append({
            'partition': part,
            **{f'expected_{k}': v for k, v in exp.items()},
            **{f'actual_{k}': got[k] for k in exp.keys()},
            'parity_pass': ok,
        })
    P = pd.DataFrame(rows)
    if not bool(P.parity_pass.all()):
        P.to_csv(OUT_PARITY, index=False)
        raise AssertionError('London 08:00 UTC parity gate failed; abort before clock selection')
    return P


def build_leaderboard(S: pd.DataFrame):
    dev = S[S.partition == 'development'].copy()
    dev = dev.sort_values('clock_start_min_utc').reset_index(drop=True)
    lookup = {int(r.clock_start_min_utc): r for r in dev.itertuples(index=False)}
    eligible = []
    stable = []
    for r in dev.itertuples(index=False):
        e = (
            int(r.k1_opp0_signals) >= 80 and
            float(r.target_break_rate) >= .75 and
            float(r.resolved_same_side_rate) >= .80
        )
        prev = lookup[(int(r.clock_start_min_utc) - 30) % 1440]
        nxt = lookup[(int(r.clock_start_min_utc) + 30) % 1440]
        def neighbor_ok(x):
            return (
                int(x.k1_opp0_signals) >= 60 and
                float(x.target_break_rate) >= .70 and
                float(x.resolved_same_side_rate) >= .78
            )
        eligible.append(e)
        stable.append(bool(neighbor_ok(prev) and neighbor_ok(nxt)))
    dev['dev_eligible'] = eligible
    dev['local_stable'] = stable
    dev['candidate_eligible'] = dev.dev_eligible & dev.local_stable
    dev['rank_score'] = dev.wilson_lb95_target
    dev['dev_rank'] = np.nan
    cand = dev[dev.candidate_eligible].sort_values(
        ['wilson_lb95_target', 'target_break_rate', 'resolved_same_side_rate', 'k1_opp0_signals', 'clock_start_min_utc'],
        ascending=[False, False, False, False, True]
    )
    for rank, idx in enumerate(cand.index, start=1):
        dev.loc[idx, 'dev_rank'] = rank
    selected = None if len(cand) == 0 else cand.iloc[0]
    return dev.sort_values(['dev_rank', 'wilson_lb95_target'], na_position='last', ascending=[True, False]), selected


def replication_readout(S: pd.DataFrame, selected):
    if selected is None:
        return [], False
    start = int(selected.clock_start_min_utc)
    rows = []
    all_ok = True
    for part in ('external', 'reference_validation'):
        r = S[(S.clock_start_min_utc == start) & (S.partition == part)].iloc[0]
        ok = (
            int(r.k1_opp0_signals) >= 50 and
            float(r.target_break_rate) >= .70 and
            float(r.resolved_same_side_rate) >= .80 and
            int(r.target_break) > int(r.opposite_break)
        )
        all_ok = all_ok and ok
        rows.append((part, r, ok))
    return rows, all_ok


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def main():
    base.synthetic_tests()
    x5, coverage = base.load5('ETHUSDT')
    if coverage < .995:
        raise RuntimeError(f'ETH raw 5m coverage too low: {coverage:.6f}')

    rows = []
    for start_min in CLOCKS:
        rows.extend(scan_clock(x5, start_min))
    W = pd.DataFrame(rows)
    if len(W) == 0:
        raise RuntimeError('clock scan produced no complete windows')
    if sorted(W.clock_start_min_utc.unique().tolist()) != CLOCKS:
        raise AssertionError('not all 48 frozen clock placements were scanned')
    W.to_csv(OUT_WINDOWS, index=False)

    S = summarize(W)
    P = parity_audit(S)
    P.to_csv(OUT_PARITY, index=False)
    S.to_csv(OUT_SUMMARY, index=False)

    L, selected = build_leaderboard(S)
    L.to_csv(OUT_LEADER, index=False)
    reps, replicated = replication_readout(S, selected)

    if selected is None:
        status = 'ETH_NATIVE_CLOCK_Z1_NO_DEV_CANDIDATE'
    elif replicated:
        status = 'ETH_NATIVE_LONDON_NY_CLOCK_Z1_SUPPORTED'
    else:
        status = 'ETH_NATIVE_LONDON_NY_CLOCK_Z1_CANDIDATE_NOT_REPLICATED'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH Native London->New York Clock Discovery — Z1 Result', '',
        f'Raw ETHUSDT 5m coverage: **{coverage:.4%}**.',
        'Scanned exactly **48** 30-minute clock rotations with frozen 5h30 reference + 6h30 execution geometry.',
        'LONG structural pressure only. No entry, TP, SL, fee, PnL, PF, or expectancy.', '',
        '## London parity control', '',
        'The known 15:00 WIB LONDON reference -> 20:30 WIB execution cell reproduced the prior ETH London->NY M1 counts exactly. **PARITY PASS.**', '',
    ]

    london = S[(S.clock_start_min_utc == 480) & (S.partition == 'development')].iloc[0]
    lines += [
        f'LONDON development: N **{int(london.k1_opp0_signals)}**, target-break **{pct(london.target_break_rate)}**, resolved **{pct(london.resolved_same_side_rate)}**, Wilson LB **{pct(london.wilson_lb95_target)}**.', '',
        '## Development leaderboard — top structural clocks', '',
        '| Rank | Ref start WIB | Execution start WIB | N | Target rate | Resolved | Wilson LB | Eligible | Local stable |',
        '|---:|---:|---:|---:|---:|---:|---:|---|---|',
    ]
    top = L.sort_values(['wilson_lb95_target'], ascending=False).head(12)
    for r in top.itertuples(index=False):
        rank = '-' if pd.isna(r.dev_rank) else str(int(r.dev_rank))
        label = 'LONDON' if int(r.clock_start_min_utc) == 480 else str(r.reference_start_wib)
        lines.append(
            f'| {rank} | {label} | {r.execution_start_wib} | {int(r.k1_opp0_signals)} | '
            f'{pct(r.target_break_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95_target)} | '
            f'{"YES" if bool(r.dev_eligible) else "NO"} | {"YES" if bool(r.local_stable) else "NO"} |'
        )

    lines += ['', '## Selected ETH-native clock', '']
    if selected is None:
        lines += ['No development clock passed the frozen eligibility + local-stability gate.', '']
    else:
        start = int(selected.clock_start_min_utc)
        label = 'LONDON' if start == 480 else wib(start)
        lines += [
            f'**Reference start: {label} WIB** (UTC {hhmm(start)}); execution starts **{wib(start + 330)} WIB**.',
            f'Development: N **{int(selected.k1_opp0_signals)}**, target-break **{pct(selected.target_break_rate)}**, resolved **{pct(selected.resolved_same_side_rate)}**, Wilson LB **{pct(selected.wilson_lb95_target)}**.', '',
            'Historical replication:', '',
            '| Partition | N | Target rate | Resolved | Gate |',
            '|---|---:|---:|---:|---|',
        ]
        for part, r, ok in reps:
            lines.append(
                f'| {part} | {int(r.k1_opp0_signals)} | {pct(r.target_break_rate)} | '
                f'{pct(r.resolved_same_side_rate)} | {"PASS" if ok else "FAIL"} |'
            )
        lines.append('')

    lines += [
        f'**Status: {status}**', '',
        'Stop after Z1. No entry/breakout-entry/TP/SL milestone was run automatically.'
    ]
    OUT_RESULT.write_text('\n'.join(lines) + '\n')
    print(OUT_RESULT.read_text())


if __name__ == '__main__':
    main()
