#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Result.md'
OUT_CASES = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Cases.csv'
OUT_SUM = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Summary.csv'
OUT_LEADER = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_DevelopmentLeaderboard.csv'
OUT_PARITY = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_LondonParity.csv'
OUT_STATUS = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Status.txt'
EXISTING_AA = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Trades.csv'

PARTS = b22b.PARTS
PART_ORDER = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
BAR5 = pd.Timedelta(minutes=5)
REF_DUR = pd.Timedelta(hours=5, minutes=30)
EXEC_DUR = pd.Timedelta(hours=6, minutes=30)
REF_BARS = 66
EXEC_BARS = 78
CLOCKS_MIN = tuple(range(0, 24 * 60, 30))
BASELINE_MIN = 8 * 60
ENTRY_F = 0.85
STOP_F = 0.35
TARGET_EXT = 0.20
NOTIONAL = 500.0
FEE = 0.40


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def part_for_window(ref_start: pd.Timestamp, exec_start: pd.Timestamp, exec_end: pd.Timestamp):
    for name, (a, z) in PARTS.items():
        if ref_start >= a and exec_start >= a and exec_end <= z:
            return name
    return None


def qualifies_high_touch(r, H: float) -> bool:
    return float(r.high) >= H and float(r.close) <= H


def clock_label(minute: int) -> tuple[str, str, str]:
    base = pd.Timestamp('2026-01-01', tz='UTC') + pd.Timedelta(minutes=minute)
    ref_end = base + REF_DUR
    exec_end = ref_end + EXEC_DUR

    def f(t: pd.Timestamp) -> str:
        dayoff = int((t.normalize() - base.normalize()) / pd.Timedelta(days=1))
        core = t.strftime('%H:%M')
        return core if dayoff == 0 else f'{core}+{dayoff}d'

    return f(base), f(ref_end), f(exec_end)


def blank_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, status):
    return {
        'partition': part,
        'anchor_date_utc': str(anchor.date()),
        'clock_min': clock_min,
        'reference_start': ref_start,
        'reference_end': ref_end,
        'execution_start': exec_start,
        'execution_end': exec_end,
        'H': np.nan,
        'L': np.nan,
        'range': np.nan,
        'F85': np.nan,
        'F35': np.nan,
        'E20': np.nan,
        'k1_signal_bar_start': pd.NaT,
        'k1_signal_ts': pd.NaT,
        'leave_bar_start': pd.NaT,
        'leave_ts': pd.NaT,
        'h2_bar_start': pd.NaT,
        'opposite_break_bar_start': pd.NaT,
        'touch_bar_start': pd.NaT,
        'same_bar_confirmed': False,
        'entry_executed': False,
        'entry_bar_start': pd.NaT,
        'entry_px': np.nan,
        'entry_fraction': np.nan,
        'nominal_rr': np.nan,
        'exit_bar_start': pd.NaT,
        'exit_ts': pd.NaT,
        'exit_px': np.nan,
        'exit_reason': status,
        'gross_return': np.nan,
        'net_pnl_usd': np.nan,
        'tp_hit': False,
        'time_exit': False,
        'case_status': status,
    }


def build_case(x5: pd.DataFrame, anchor: pd.Timestamp, clock_min: int):
    ref_start = anchor + pd.Timedelta(minutes=clock_min)
    ref_end = ref_start + REF_DUR
    exec_start = ref_end
    exec_end = exec_start + EXEC_DUR
    part = part_for_window(ref_start, exec_start, exec_end)
    if part is None:
        return None
    if exec_start.weekday() >= 5:
        return None

    base = blank_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, 'INIT')
    ref = fast_slice(x5, ref_start, ref_end)
    exe = fast_slice(x5, exec_start, exec_end)
    if len(ref) != REF_BARS or len(exe) != EXEC_BARS:
        return {**base, 'case_status': 'DATA_GAP', 'exit_reason': 'DATA_GAP'}

    H = float(ref.high.max())
    L = float(ref.low.min())
    if not (math.isfinite(H) and math.isfinite(L) and H > L):
        return {**base, 'case_status': 'INVALID_RANGE', 'exit_reason': 'INVALID_RANGE'}
    R = H - L
    f85 = L + ENTRY_F * R
    f35 = L + STOP_F * R
    e20 = H + TARGET_EXT * R
    base.update({'H': H, 'L': L, 'range': R, 'F85': f85, 'F35': f35, 'E20': e20})

    hi_touching = False
    lo_touching = False
    hi_visits = 0
    lo_visits = 0
    sig_k = None
    for k, (ts, r) in enumerate(exe.iterrows()):
        close = float(r.close)
        break_hi = close > H
        break_lo = close < L
        if break_hi and break_lo:
            raise AssertionError('impossible strict breakout beyond both edges')
        if break_hi or break_lo:
            return {**base, 'case_status': 'BREAK_BEFORE_K1', 'exit_reason': 'BREAK_BEFORE_K1'}

        hit_hi = float(r.high) >= H and close <= H
        hit_lo = float(r.low) <= L and close >= L
        if hit_hi and hit_lo:
            return {**base, 'case_status': 'AMBIGUOUS_BOTH_LEVELS', 'exit_reason': 'AMBIGUOUS_BOTH_LEVELS'}

        if hit_hi and not hi_touching:
            hi_visits += 1
            if hi_visits == 1 and lo_visits == 0:
                sig_k = k
                base['k1_signal_bar_start'] = ts
                base['k1_signal_ts'] = ts + BAR5
                break
        if hit_lo and not lo_touching:
            lo_visits += 1

        hi_touching = bool(hit_hi)
        lo_touching = bool(hit_lo)

    if sig_k is None:
        return {**base, 'case_status': 'NO_K1_OPP0', 'exit_reason': 'NO_K1_OPP0'}

    leave_k = None
    for k in range(sig_k + 1, len(exe)):
        r = exe.iloc[k]
        ts = exe.index[k]
        close = float(r.close)
        if close > H:
            return {**base, 'case_status': 'NO_WINDOW_HIGH_BREAK_DURING_K1', 'exit_reason': 'NO_WINDOW_HIGH_BREAK_DURING_K1'}
        if close < L:
            return {**base, 'case_status': 'NO_WINDOW_LOW_BREAK_DURING_K1', 'exit_reason': 'NO_WINDOW_LOW_BREAK_DURING_K1'}
        if qualifies_high_touch(r, H):
            continue
        leave_k = k
        base['leave_bar_start'] = ts
        base['leave_ts'] = ts + BAR5
        break

    if leave_k is None:
        return {**base, 'case_status': 'NO_CAUSAL_LEAVE', 'exit_reason': 'NO_CAUSAL_LEAVE'}

    terminal_k = len(exe)
    terminal_status = 'NO_H2_BY_EXEC_END'
    for k in range(leave_k + 1, len(exe)):
        r = exe.iloc[k]
        ts = exe.index[k]
        hit_h = float(r.high) >= H
        break_l = float(r.close) < L
        if hit_h and break_l:
            terminal_k = k
            terminal_status = 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
            break
        if hit_h:
            terminal_k = k
            terminal_status = 'H2_ARRIVAL'
            base['h2_bar_start'] = ts
            break
        if break_l:
            terminal_k = k
            terminal_status = 'OPPOSITE_BREAK_BEFORE_H2'
            base['opposite_break_bar_start'] = ts
            break

    if terminal_status == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK':
        return {**base, 'case_status': terminal_status, 'exit_reason': terminal_status}

    touch_k = None
    for k in range(leave_k + 1, terminal_k):
        r = exe.iloc[k]
        if float(r.low) <= f85 <= float(r.high):
            touch_k = k
            base['touch_bar_start'] = exe.index[k]
            break

    if touch_k is None:
        return {**base, 'case_status': 'NO_F85_TOUCH_PRE_H2', 'exit_reason': 'NO_F85_TOUCH_PRE_H2'}

    touch = exe.iloc[touch_k]
    if not (float(touch.close) > f85):
        return {**base, 'case_status': 'F85_TOUCH_NO_SAME_BAR_REJECTION', 'exit_reason': 'F85_TOUCH_NO_SAME_BAR_REJECTION'}
    base['same_bar_confirmed'] = True

    entry_start = exe.index[touch_k] + BAR5
    if entry_start >= exec_end:
        return {**base, 'case_status': 'CONFIRMED_NO_NEXT_BAR', 'exit_reason': 'CONFIRMED_NO_NEXT_BAR'}
    pos = int(x5.index.searchsorted(entry_start, side='left'))
    if pos >= len(x5) or x5.index[pos] != entry_start:
        return {**base, 'case_status': 'ENTRY_BAR_MISSING', 'exit_reason': 'ENTRY_BAR_MISSING'}
    entry_px = float(x5.iloc[pos].open)
    base['entry_bar_start'] = entry_start
    base['entry_px'] = entry_px
    base['entry_fraction'] = (entry_px - L) / R

    if entry_px >= H:
        return {**base, 'case_status': 'MISSED_H2_AT_OPEN', 'exit_reason': 'MISSED_H2_AT_OPEN'}
    if not (f35 < entry_px < H):
        return {**base, 'case_status': 'INVALID_ENTRY_GEOMETRY', 'exit_reason': 'INVALID_ENTRY_GEOMETRY'}
    if terminal_k < len(exe):
        terminal_start = exe.index[terminal_k]
        if entry_start > terminal_start:
            raise AssertionError('entry starts after structural terminal')

    base['entry_executed'] = True
    base['nominal_rr'] = (e20 - entry_px) / (entry_px - f35)

    q = fast_slice(x5, entry_start, exec_end)
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    exit_reason = None
    for ts, r in q.iterrows():
        high = float(r.high)
        close = float(r.close)
        if high >= e20:
            exit_bar_start = ts
            exit_ts = ts
            exit_px = e20
            exit_reason = 'TP_E20'
            break
        if close < f35:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = close
            exit_reason = 'CLOSE_INVALIDATION_F35'
            break

    if exit_reason is None:
        epos = int(x5.index.searchsorted(exec_end, side='left'))
        if epos >= len(x5):
            return {**base, 'case_status': 'CENSORED', 'exit_reason': 'CENSORED'}
        exit_bar_start = x5.index[epos]
        exit_ts = x5.index[epos]
        exit_px = float(x5.iloc[epos].open)
        exit_reason = 'TIME_EXIT_EXEC_END'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    return {
        **base,
        'exit_bar_start': exit_bar_start,
        'exit_ts': exit_ts,
        'exit_px': float(exit_px),
        'exit_reason': exit_reason,
        'gross_return': gross,
        'net_pnl_usd': net,
        'tp_hit': exit_reason == 'TP_E20',
        'time_exit': exit_reason == 'TIME_EXIT_EXEC_END',
        'case_status': 'TRADE_EXECUTED',
    }


def summarize(g: pd.DataFrame) -> dict:
    k1 = g[g.k1_signal_ts.notna()]
    clean = g[g.leave_ts.notna()]
    touch = g[g.touch_bar_start.notna()]
    tr = g[g.entry_executed.astype(bool) & g.net_pnl_usd.notna()].copy()
    vals = pd.to_numeric(tr.net_pnl_usd, errors='coerce')
    return {
        'days': int(len(g)),
        'k1_opp0': int(len(k1)),
        'clean_windows': int(len(clean)),
        'f85_touches': int(len(touch)),
        'trades': int(len(tr)),
        'wins': int((vals > 0).sum()) if len(tr) else 0,
        'wr': float((vals > 0).mean()) if len(tr) else np.nan,
        'pf': pf(vals) if len(tr) else np.nan,
        'expectancy': float(vals.mean()) if len(tr) else np.nan,
        'total_net': float(vals.sum()) if len(tr) else 0.0,
        'tp_rate': float(tr.tp_hit.mean()) if len(tr) else np.nan,
        'time_exit_rate': float(tr.time_exit.mean()) if len(tr) else np.nan,
    }


def dev_eligible(r: pd.Series) -> bool:
    return bool(
        int(r.trades) >= 25
        and pd.notna(r.wr) and float(r.wr) >= 0.70
        and pd.notna(r.pf) and float(r.pf) >= 1.30
        and pd.notna(r.expectancy) and float(r.expectancy) > 0
    )


def historical_replication_supported(summary: pd.DataFrame, clock_min: int) -> bool:
    need = {'external': (15, 0.65, 1.20), 'reference_validation': (10, 0.65, 1.20)}
    for part, (nmin, wrmin, pfmin) in need.items():
        q = summary[(summary.clock_min == clock_min) & (summary.partition == part)]
        if len(q) != 1:
            return False
        r = q.iloc[0]
        if not (
            int(r.trades) >= nmin
            and pd.notna(r.wr) and float(r.wr) >= wrmin
            and pd.notna(r.pf) and float(r.pf) >= pfmin
            and pd.notna(r.expectancy) and float(r.expectancy) > 0
        ):
            return False
    return True


def london_parity(cases: pd.DataFrame) -> pd.DataFrame:
    q = cases[(cases.clock_min == BASELINE_MIN) & cases.partition.isin(PART_ORDER)].copy()
    tr = q[q.entry_executed.astype(bool) & q.net_pnl_usd.notna()].copy()
    expected_counts = {'external': 27, 'development': 30, 'reference_validation': 11, 'august': 1}
    rows = []
    for part in PART_ORDER:
        z = tr[tr.partition == part]
        rows.append({'check': f'count_{part}', 'actual': len(z), 'expected': expected_counts[part], 'pass': len(z) == expected_counts[part]})

    major = tr[tr.partition.isin(MAJOR)].copy()
    vals = pd.to_numeric(major.net_pnl_usd, errors='coerce')
    n = len(major)
    wins = int((vals > 0).sum())
    wr = float((vals > 0).mean()) if n else np.nan
    p = pf(vals)
    exp = float(vals.mean()) if n else np.nan
    total = float(vals.sum()) if n else np.nan
    rows += [
        {'check': 'pooled_major_n', 'actual': n, 'expected': 68, 'pass': n == 68},
        {'check': 'pooled_major_wins', 'actual': wins, 'expected': 47, 'pass': wins == 47},
        {'check': 'pooled_major_wr', 'actual': wr, 'expected': 47/68, 'pass': abs(wr - 47/68) < 1e-12 if n else False},
        {'check': 'pooled_major_pf', 'actual': p, 'expected': 1.70, 'pass': pd.notna(p) and abs(float(p) - 1.70) <= 0.03},
        {'check': 'pooled_major_expectancy', 'actual': exp, 'expected': 0.91, 'pass': pd.notna(exp) and abs(float(exp) - 0.91) <= 0.03},
        {'check': 'pooled_major_total', 'actual': total, 'expected': 61.80, 'pass': pd.notna(total) and abs(float(total) - 61.80) <= 0.15},
    ]

    if EXISTING_AA.exists():
        aa = pd.read_csv(EXISTING_AA)
        aa = aa[(aa.variant == 'SAME_BAR_REJECTION') & (aa.entry_executed.astype(str).str.lower() == 'true')].copy()
        aa['entry_bar_start'] = pd.to_datetime(aa.entry_bar_start, utc=True)
        tr['entry_bar_start'] = pd.to_datetime(tr.entry_bar_start, utc=True)
        akeys = set(zip(aa.partition.astype(str), aa.entry_bar_start.astype(str)))
        gkeys = set(zip(tr.partition.astype(str), tr.entry_bar_start.astype(str)))
        rows.append({'check': 'exact_entry_timestamp_identity', 'actual': len(gkeys & akeys), 'expected': len(akeys), 'pass': gkeys == akeys})

    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DE London parity gate failed:\n' + out.to_string(index=False))
    return out


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def num(v, d=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    rows = []
    for anchor in anchors:
        for clock_min in CLOCKS_MIN:
            r = build_case(x5, anchor, clock_min)
            if r is not None:
                rows.append(r)
    cases = pd.DataFrame(rows)
    if cases.empty:
        raise RuntimeError('no B27DE cases generated')

    parity = london_parity(cases)

    sums = []
    for clock_min in CLOCKS_MIN:
        rs, es, ee = clock_label(clock_min)
        for part in PART_ORDER:
            g = cases[(cases.clock_min == clock_min) & (cases.partition == part)]
            sums.append({'clock_min': clock_min, 'reference_start_utc': rs, 'execution_start_utc': es, 'execution_end_utc': ee, 'partition': part, **summarize(g)})
    summary = pd.DataFrame(sums)

    dev = summary[summary.partition == 'development'].copy()
    dev['dev_eligible'] = dev.apply(dev_eligible, axis=1)
    dev['is_london_baseline'] = dev.clock_min == BASELINE_MIN
    leader = dev.sort_values(['dev_eligible', 'pf', 'wr', 'expectancy', 'trades', 'clock_min'], ascending=[False, False, False, False, False, True]).reset_index(drop=True)

    eligible_new = leader[leader.dev_eligible & ~leader.is_london_baseline].copy()
    selected = None if eligible_new.empty else eligible_new.iloc[0]
    if selected is None:
        status = 'B27DE_NO_NEW_CLOCK_CANDIDATE'
        replication = False
    else:
        sel_min = int(selected.clock_min)
        replication = historical_replication_supported(summary, sel_min)
        status = 'B27DE_NEW_CLOCK_HISTORICAL_REPLICATION_SUPPORTED' if replication else 'B27DE_NEW_CLOCK_DEV_CANDIDATE_NOT_REPLICATED'

    cases.to_csv(OUT_CASES, index=False)
    summary.to_csv(OUT_SUM, index=False)
    leader.to_csv(OUT_LEADER, index=False)
    parity.to_csv(OUT_PARITY, index=False)
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# B27DE — Generic F85 LONG Clock-Rotation Scan — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**London parity: PASS.** The generic detector reproduced the persisted 08:00 UTC London -> New York SAME_BAR_REJECTION cohort before rotated clocks were interpreted.', '',
        '## Development clock leaderboard', '',
        '| Ref start | Exec start | Exec end | N | WR | PF | Exp | Net | K1 | F85 touches | Eligible |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for r in leader.head(16).itertuples(index=False):
        lines.append(f'| {r.reference_start_utc} | {r.execution_start_utc} | {r.execution_end_utc} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {r.k1_opp0} | {r.f85_touches} | {"YES" if r.dev_eligible else "NO"} |')

    lines += ['', '## London baseline', '', '| Partition | N | WR | PF | Exp | Net | TP rate |', '|---|---:|---:|---:|---:|---:|---:|']
    b = summary[summary.clock_min == BASELINE_MIN]
    for part in PART_ORDER:
        r = b[b.partition == part].iloc[0]
        lines.append(f'| {part} | {int(r.trades)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {pct(r.tp_rate)} |')

    lines += ['', '## New clock selection', '']
    if selected is None:
        lines.append('No non-London clock passed the frozen development eligibility gate.')
    else:
        sel_min = int(selected.clock_min)
        rs, es, ee = clock_label(sel_min)
        lines.append(f'Primary development-selected new clock: **reference {rs} -> execution {es}-{ee} UTC**.')
        lines.append(f'Development: N={int(selected.trades)}, WR={pct(selected.wr)}, PF={num(selected.pf)}, expectancy=${num(selected.expectancy)}, net=${num(selected.total_net)}.')
        lines.append(f'Historical external + reference-validation replication label: **{"SUPPORTED" if replication else "NOT SUPPORTED"}**.')
        lines += ['', '| Partition | N | WR | PF | Exp | Net |', '|---|---:|---:|---:|---:|---:|']
        for part in PART_ORDER:
            r = summary[(summary.clock_min == sel_min) & (summary.partition == part)].iloc[0]
            lines.append(f'| {part} | {int(r.trades)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} |')

    lines += ['', f'**Status: {status}**', '', 'Guardrail: this is a historical discovery scan across 48 preregistered clock placements. External/reference-validation are reused historical partitions, not pristine fresh OOS. No live BBC change is authorized.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
