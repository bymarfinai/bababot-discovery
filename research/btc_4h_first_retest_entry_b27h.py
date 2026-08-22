#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_FIRST_RETEST_ENTRY_B27H_Result.md'
OUT_SUM = ROOT / 'BTC_4H_FIRST_RETEST_ENTRY_B27H_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_FIRST_RETEST_ENTRY_B27H_Trades.csv'
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


def resolve(x5_idx, x5_hi, x5_lo, entry_ts, entry_px, stop_px, target_px, side, part_end):
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
    if hi_i - lo_i < 5:
        return []

    active_hi = active_lo = np.nan
    active_hi_ts = active_lo_ts = pd.NaT
    hi_traded = lo_traded = False
    blocked_until = None
    rows = []

    for i in range(lo_i, hi_i - 1):
        # Pivot k=i-2 is known before bar i opens because k+1=i-1 is complete.
        k = i - 2
        if k >= lo_i + 1 and k + 1 < hi_i:
            pivot_hi = highs[k] > highs[k - 1] and highs[k] > highs[k + 1]
            pivot_lo = lows[k] < lows[k - 1] and lows[k] < lows[k + 1]
            if pd.isna(active_hi) and pivot_hi:
                active_hi = float(highs[k])
                active_hi_ts = idx[k]
                hi_traded = False
            if pd.isna(active_lo) and pivot_lo:
                active_lo = float(lows[k])
                active_lo_ts = idx[k]
                lo_traded = False

        long_break = (not pd.isna(active_hi)) and closes[i] > active_hi
        short_break = (not pd.isna(active_lo)) and closes[i] < active_lo

        # First pre-breakout retest candidates. Breakout candle itself is excluded.
        hi_retest = (
            (not pd.isna(active_hi)) and (not hi_traded) and (not long_break)
            and highs[i] >= active_hi * (1.0 - TOL)
            and closes[i] <= active_hi
            and idx[i] > active_hi_ts + pd.Timedelta(hours=4)
        )
        lo_retest = (
            (not pd.isna(active_lo)) and (not lo_traded) and (not short_break)
            and lows[i] <= active_lo * (1.0 + TOL)
            and closes[i] >= active_lo
            and idx[i] > active_lo_ts + pd.Timedelta(hours=4)
        )

        # If both boundaries qualify on one completed 4H bar, skip as ambiguous,
        # but retire both first-retest opportunities so there is no hindsight retry.
        if hi_retest and lo_retest:
            hi_traded = True
            lo_traded = True
        elif hi_retest or lo_retest:
            side = 'LONG' if hi_retest else 'SHORT'
            level = active_hi if side == 'LONG' else active_lo
            level_ts = active_hi_ts if side == 'LONG' else active_lo_ts
            if side == 'LONG':
                hi_traded = True
            else:
                lo_traded = True

            entry_i = i + 1
            entry_ts = idx[entry_i]
            can_enter = (blocked_until is None or entry_ts > blocked_until) and entry_ts < end
            if can_enter:
                entry_px = float(opens[entry_i])
                if side == 'LONG':
                    stop_px = float(lows[i])
                    risk = entry_px - stop_px
                    target_px = entry_px + RR * risk if risk > 0 else np.nan
                else:
                    stop_px = float(highs[i])
                    risk = stop_px - entry_px
                    target_px = entry_px - RR * risk if risk > 0 else np.nan

                if risk > 0:
                    solved = resolve(xidx, xhi, xlo, entry_ts, entry_px, stop_px, target_px, side, end)
                    base = {
                        'partition': part,
                        'side': side,
                        'swing_level_ts': level_ts,
                        'swing_level': float(level),
                        'retest_ts': idx[i],
                        'entry_ts': entry_ts,
                        'entry_px': entry_px,
                        'stop_px': stop_px,
                        'target_px': float(target_px),
                        'risk_pct': float(risk / entry_px),
                    }
                    if solved is None:
                        rows.append({**base, 'resolved': False, 'exit_ts': pd.NaT,
                                     'exit_px': np.nan, 'gross_return': np.nan,
                                     'net_pnl_usd': np.nan, 'exit_reason': 'CENSORED',
                                     'hold_minutes': np.nan})
                        blocked_until = end
                    else:
                        exit_ts, exit_px, ret, reason = solved
                        rows.append({**base, 'resolved': True, 'exit_ts': exit_ts,
                                     'exit_px': exit_px, 'gross_return': ret,
                                     'net_pnl_usd': float(ret * NOTIONAL - FEE),
                                     'exit_reason': reason,
                                     'hold_minutes': float((exit_ts - entry_ts) / pd.Timedelta(minutes=1))})
                        blocked_until = exit_ts

        # Frozen level retires only on strict close-through breakout.
        if long_break:
            active_hi = np.nan
            active_hi_ts = pd.NaT
            hi_traded = False
        if short_break:
            active_lo = np.nan
            active_lo_ts = pd.NaT
            lo_traded = False

    return rows


def summarize(g):
    if len(g) == 0:
        return {'entered': 0, 'resolved': 0, 'wins': 0, 'losses': 0, 'wr': np.nan,
                'net_pf': np.nan, 'net_exp': np.nan, 'total_net': np.nan,
                'med_risk': np.nan, 'med_hold': np.nan}
    r = g[g.resolved.astype(bool)].copy()
    if len(r) == 0:
        return {'entered': int(len(g)), 'resolved': 0, 'wins': 0, 'losses': 0, 'wr': np.nan,
                'net_pf': np.nan, 'net_exp': np.nan, 'total_net': np.nan,
                'med_risk': float(g.risk_pct.median()), 'med_hold': np.nan}
    net = r.net_pnl_usd.astype(float)
    wins = int((r.exit_reason == 'TP_2R').sum())
    losses = int(len(r) - wins)
    return {'entered': int(len(g)), 'resolved': int(len(r)), 'wins': wins, 'losses': losses,
            'wr': wins / len(r), 'net_pf': pf(net), 'net_exp': float(net.mean()),
            'total_net': float(net.sum()), 'med_risk': float(r.risk_pct.median()),
            'med_hold': float(r.hold_minutes.median())}


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
    z = b22b.resample_ohlc(x5, '4h')
    rows = []
    for part, (start, end) in PARTS.items():
        rows.extend(simulate_partition(z, x5, part, start, end))
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for part in PARTS:
        g = trades[trades.partition == part] if len(trades) else pd.DataFrame()
        s = summarize(g)
        sums.append({'partition': part,
                     'long_n': int((g.side == 'LONG').sum()) if len(g) else 0,
                     'short_n': int((g.side == 'SHORT').sum()) if len(g) else 0,
                     **s})
    sm = pd.DataFrame(sums)
    major = sm[sm.partition.isin(['external', 'development', 'reference_validation'])]
    passed = bool(len(major) == 3 and (major.resolved >= 30).all()
                  and (major.net_exp > 0).all() and (major.net_pf >= 1.20).all())
    sm['repeatable_pass'] = passed
    sm.to_csv(OUT_SUM, index=False)

    md = [
        '# B27H — BTC 4H First Retest Entry', '',
        f'Source coverage: **{coverage:.4%}**. Frozen 4H swing level, ±0.20% first pre-breakout retest, breakout-direction entry next 4H open, retest-candle opposite extreme SL, TP 2R.', '',
        '| Partition | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order = {k: i for i, k in enumerate(PARTS)}
    sm['ord'] = sm.partition.map(order)
    for r in sm.sort_values('ord').itertuples(index=False):
        md.append(f'| {r.partition} | {r.resolved} | {r.long_n} | {r.short_n} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.med_risk)} | {num(r.med_hold,1)} |')
    md += ['', '## Repeatability verdict', '',
           f'**B27H: {"PASS" if passed else "FAIL"}.**', '',
           'PASS requires >=30 resolved trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
