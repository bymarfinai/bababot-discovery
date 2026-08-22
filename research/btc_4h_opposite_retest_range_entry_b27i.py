#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_OPPOSITE_RETEST_RANGE_ENTRY_B27I_Result.md'
OUT_SUM = ROOT / 'BTC_4H_OPPOSITE_RETEST_RANGE_ENTRY_B27I_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_OPPOSITE_RETEST_RANGE_ENTRY_B27I_Trades.csv'
PARTS = b22b.PARTS
NOTIONAL = 500.0
FEE = 0.40
RR = 2.0
TOL = 0.002


def pf(v):
    s = pd.Series(v, dtype=float)
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def build4h(x5):
    return b22b.resample_ohlc(x5, '4h')


def resolve_trade(x5_idx, x5_hi, x5_lo, entry_ts, entry_px, stop_px, target_px, side, part_end):
    a = int(x5_idx.searchsorted(entry_ts, side='left'))
    b = int(x5_idx.searchsorted(part_end, side='left'))
    for k in range(a, b):
        if side == 'LONG':
            tp = x5_hi[k] >= target_px
            sl = x5_lo[k] <= stop_px
        else:
            tp = x5_lo[k] <= target_px
            sl = x5_hi[k] >= stop_px
        if tp and sl:
            px = stop_px
            reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            px = target_px
            reason = 'TP_2R'
        elif sl:
            px = stop_px
            reason = 'SL'
        else:
            continue
        ret = (px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return x5_idx[k], float(px), float(ret), reason
    return None


def first_stop_ts(x5_idx, x5_hi, x5_lo, entry_ts, stop_px, side, part_end):
    a = int(x5_idx.searchsorted(entry_ts, side='left'))
    b = int(x5_idx.searchsorted(part_end, side='left'))
    for k in range(a, b):
        hit = (x5_lo[k] <= stop_px) if side == 'LONG' else (x5_hi[k] >= stop_px)
        if hit:
            return x5_idx[k]
    return pd.NaT


def first_target_break_close_ts(z, entry_i, side, high_level, low_level, part_end):
    idx = z.index
    closes = z.close.to_numpy(float)
    hi_i = int(idx.searchsorted(part_end, side='left'))
    for j in range(entry_i, hi_i):
        broke = closes[j] > high_level if side == 'LONG' else closes[j] < low_level
        if broke:
            # 4H candle close is causally known at the next 4H boundary.
            ts = idx[j] + pd.Timedelta(hours=4)
            if ts <= part_end:
                return ts
    return pd.NaT


def pressure_bucket(n):
    return '3+' if int(n) >= 3 else str(int(n))


def simulate_partition(z, x5, part, start, end):
    idx = z.index
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    closes = z.close.to_numpy(float)
    xidx = x5.index
    xhi = x5.high.to_numpy(float)
    xlo = x5.low.to_numpy(float)

    lo_i = int(idx.searchsorted(start, side='left'))
    hi_i = int(idx.searchsorted(end, side='left'))
    if hi_i - lo_i < 8:
        return []

    candidate_hi = candidate_lo = np.nan
    candidate_hi_ts = candidate_lo_ts = pd.NaT
    active = False
    range_hi = range_lo = np.nan
    range_hi_ts = range_lo_ts = pd.NaT
    hi_visits = lo_visits = 0
    hi_touching = lo_touching = False
    consumed = False
    reset_i = lo_i - 1
    blocked_until = None
    rows = []

    def clear_range(current_i):
        nonlocal candidate_hi, candidate_lo, candidate_hi_ts, candidate_lo_ts
        nonlocal active, range_hi, range_lo, range_hi_ts, range_lo_ts
        nonlocal hi_visits, lo_visits, hi_touching, lo_touching, consumed, reset_i
        candidate_hi = candidate_lo = np.nan
        candidate_hi_ts = candidate_lo_ts = pd.NaT
        active = False
        range_hi = range_lo = np.nan
        range_hi_ts = range_lo_ts = pd.NaT
        hi_visits = lo_visits = 0
        hi_touching = lo_touching = False
        consumed = False
        reset_i = current_i

    for i in range(lo_i, hi_i - 1):
        # A pivot centered at k=i-2 is known before bar i opens because k+1=i-1 has completed.
        k = i - 2
        if k > reset_i and k >= lo_i + 1 and k + 1 < hi_i:
            pivot_hi = highs[k] > highs[k - 1] and highs[k] > highs[k + 1]
            pivot_lo = lows[k] < lows[k - 1] and lows[k] < lows[k + 1]
            if not active:
                if pd.isna(candidate_hi) and pivot_hi:
                    candidate_hi = float(highs[k])
                    candidate_hi_ts = idx[k]
                if pd.isna(candidate_lo) and pivot_lo:
                    candidate_lo = float(lows[k])
                    candidate_lo_ts = idx[k]
                if not pd.isna(candidate_hi) and not pd.isna(candidate_lo) and candidate_hi > candidate_lo:
                    range_hi = float(candidate_hi)
                    range_lo = float(candidate_lo)
                    range_hi_ts = candidate_hi_ts
                    range_lo_ts = candidate_lo_ts
                    active = True
                    hi_visits = lo_visits = 0
                    hi_touching = lo_touching = False
                    consumed = False

        if not active:
            continue

        # Strict close-through invalidates the frozen range. No entry is taken on the breakout candle.
        break_hi = closes[i] > range_hi
        break_lo = closes[i] < range_lo
        if break_hi or break_lo:
            clear_range(i)
            continue

        high_touch = highs[i] >= range_hi * (1.0 - TOL) and closes[i] <= range_hi
        low_touch = lows[i] <= range_lo * (1.0 + TOL) and closes[i] >= range_lo

        # One candle spanning both zones has unknown intrabar order; do not count a visit or signal.
        if high_touch and low_touch:
            hi_touching = True
            lo_touching = True
            continue

        new_hi = bool(high_touch and not hi_touching)
        new_lo = bool(low_touch and not lo_touching)
        if new_hi:
            hi_visits += 1
        if new_lo:
            lo_visits += 1

        # Update visit-state after detecting starts.
        hi_touching = bool(high_touch)
        lo_touching = bool(low_touch)

        can_enter_time = blocked_until is None or idx[i] > blocked_until
        long_signal = (not consumed) and can_enter_time and new_lo and lo_visits >= 2 and hi_visits >= 2
        short_signal = (not consumed) and can_enter_time and new_hi and hi_visits >= 2 and lo_visits >= 2

        if long_signal and short_signal:
            continue
        if not (long_signal or short_signal):
            continue

        side = 'LONG' if long_signal else 'SHORT'
        entry_i = i + 1
        entry_ts = idx[entry_i]
        if entry_ts >= end:
            break
        entry_px = float(opens[entry_i])
        if side == 'LONG':
            stop_px = float(lows[i])
            risk = entry_px - stop_px
            pressure_visits = int(hi_visits)
            opposite_visits = int(lo_visits)
            target_px = entry_px + RR * risk if risk > 0 else np.nan
        else:
            stop_px = float(highs[i])
            risk = stop_px - entry_px
            pressure_visits = int(lo_visits)
            opposite_visits = int(hi_visits)
            target_px = entry_px - RR * risk if risk > 0 else np.nan

        consumed = True
        if risk <= 0:
            continue

        solved = resolve_trade(xidx, xhi, xlo, entry_ts, entry_px, stop_px, target_px, side, end)
        stop_ts = first_stop_ts(xidx, xhi, xlo, entry_ts, stop_px, side, end)
        target_break_ts = first_target_break_close_ts(z, entry_i, side, range_hi, range_lo, end)
        breakout_before_stop = (not pd.isna(target_break_ts)) and (pd.isna(stop_ts) or target_break_ts < stop_ts)

        base = {
            'partition': part,
            'side': side,
            'signal_ts': idx[i],
            'entry_ts': entry_ts,
            'range_high_ts': range_hi_ts,
            'range_low_ts': range_lo_ts,
            'range_high': float(range_hi),
            'range_low': float(range_lo),
            'pressure_visits': pressure_visits,
            'pressure_bucket': pressure_bucket(pressure_visits),
            'opposite_visits': opposite_visits,
            'entry_px': entry_px,
            'stop_px': stop_px,
            'target_px': float(target_px),
            'risk_pct': float(risk / entry_px),
            'target_break_ts': target_break_ts,
            'stop_first_ts': stop_ts,
            'target_break_before_stop': bool(breakout_before_stop),
        }

        if solved is None:
            rows.append({**base, 'resolved': False, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                         'gross_return': np.nan, 'net_pnl_usd': np.nan, 'exit_reason': 'CENSORED',
                         'hold_minutes': np.nan})
            blocked_until = end
        else:
            exit_ts, exit_px, ret, reason = solved
            rows.append({**base, 'resolved': True, 'exit_ts': exit_ts, 'exit_px': exit_px,
                         'gross_return': ret, 'net_pnl_usd': float(ret * NOTIONAL - FEE),
                         'exit_reason': reason,
                         'hold_minutes': float((exit_ts - entry_ts) / pd.Timedelta(minutes=1))})
            blocked_until = exit_ts

    return rows


def summarize(g):
    if len(g) == 0:
        return {'entered': 0, 'resolved': 0, 'wins': 0, 'losses': 0, 'wr': np.nan,
                'net_pf': np.nan, 'net_exp': np.nan, 'total_net': np.nan,
                'med_risk': np.nan, 'med_hold': np.nan, 'breakout_rate': np.nan}
    r = g[g.resolved.astype(bool)].copy()
    br = float(g.target_break_before_stop.astype(bool).mean()) if len(g) else np.nan
    if len(r) == 0:
        return {'entered': int(len(g)), 'resolved': 0, 'wins': 0, 'losses': 0, 'wr': np.nan,
                'net_pf': np.nan, 'net_exp': np.nan, 'total_net': np.nan,
                'med_risk': float(g.risk_pct.median()), 'med_hold': np.nan, 'breakout_rate': br}
    net = r.net_pnl_usd.astype(float)
    wins = int((r.exit_reason == 'TP_2R').sum())
    losses = int(len(r) - wins)
    return {'entered': int(len(g)), 'resolved': int(len(r)), 'wins': wins, 'losses': losses,
            'wr': wins / len(r), 'net_pf': pf(net), 'net_exp': float(net.mean()),
            'total_net': float(net.sum()), 'med_risk': float(r.risk_pct.median()),
            'med_hold': float(r.hold_minutes.median()), 'breakout_rate': br}


def pct(v):
    return '-' if pd.isna(v) else f'{100 * float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    z = build4h(x5)
    rows = []
    for part, (start, end) in PARTS.items():
        rows.extend(simulate_partition(z, x5, part, start, end))
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for part in PARTS:
        base = trades[trades.partition == part] if len(trades) else pd.DataFrame()
        groups = [('ALL', base)]
        if len(base):
            groups += [('PRESSURE_2', base[base.pressure_bucket == '2']),
                       ('PRESSURE_3PLUS', base[base.pressure_bucket == '3+']),
                       ('LONG', base[base.side == 'LONG']),
                       ('SHORT', base[base.side == 'SHORT'])]
        else:
            groups += [('PRESSURE_2', base), ('PRESSURE_3PLUS', base), ('LONG', base), ('SHORT', base)]
        for name, g in groups:
            sums.append({'partition': part, 'group': name, **summarize(g)})
    s = pd.DataFrame(sums)
    major = ('external', 'development', 'reference_validation')
    q = s[(s.group == 'ALL') & s.partition.isin(major)]
    passed = bool(len(q) == 3 and (q.resolved >= 30).all() and (q.net_exp > 0).all() and (q.net_pf >= 1.20).all())
    s['primary_pass'] = passed
    s.to_csv(OUT_SUM, index=False)

    md = [
        '# B27I — BTC 4H Opposite-Side Retest Entry Before Range Breakout', '',
        f'Source coverage: **{coverage:.4%}**. Frozen causal 4H swing range; retest tolerance ±0.20%; target-side visits >=2; entry from second-or-later opposite-side retest; next 4H open; retest-candle extreme SL; TP 2R.', '',
        'Structural diagnostic = intended frozen boundary achieves a strict 4H close-through breakout before the 5m stop is first hit.', '',
        '| Partition | Group | Resolved | W | L | WR | Net PF | Net exp/trade | Total net | Target breakout before SL | Median stop | Median hold min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    po = {k: i for i, k in enumerate(PARTS)}
    go = {'ALL': 0, 'PRESSURE_2': 1, 'PRESSURE_3PLUS': 2, 'LONG': 3, 'SHORT': 4}
    s['po'] = s.partition.map(po)
    s['go'] = s.group.map(go)
    for r in s.sort_values(['po', 'go']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.group} | {r.resolved} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.breakout_rate)} | {pct(r.med_risk)} | {num(r.med_hold,1)} |')
    md += ['', '## Pre-registered verdict', '', f'**B27I: {"PASS" if passed else "FAIL / INSUFFICIENT"}.**', '',
           'PASS requires >=30 resolved trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.', '',
           'Pressure-count and side rows are diagnostics only and are not promoted post hoc.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
