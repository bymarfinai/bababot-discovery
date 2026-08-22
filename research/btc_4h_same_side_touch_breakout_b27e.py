#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_SAME_SIDE_TOUCH_BREAKOUT_B27E_Result.md'
OUT_SUM = ROOT / 'BTC_4H_SAME_SIDE_TOUCH_BREAKOUT_B27E_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_SAME_SIDE_TOUCH_BREAKOUT_B27E_Trades.csv'

PARTS = b22b.PARTS
NOTIONAL = 500.0
FEE = 0.40
RR = 2.0
DUR = pd.Timedelta(hours=4)


def pf(v):
    s = pd.Series(v, dtype=float)
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def build4h(x5: pd.DataFrame) -> pd.DataFrame:
    return b22b.resample_ohlc(x5, '4h')


def confirmed_seed(z: pd.DataFrame, start_i: int):
    """Return latest pivots known before bar start_i opens.

    A pivot at k is confirmed after k+1 completes, so before start_i opens we may
    use pivots k <= start_i-2.
    """
    hi_val = lo_val = np.nan
    hi_ts = lo_ts = pd.NaT
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    idx = z.index
    last_k = start_i - 2
    for k in range(1, max(1, last_k + 1)):
        if k + 1 >= start_i:
            break
        if highs[k] > highs[k - 1] and highs[k] > highs[k + 1]:
            hi_val = float(highs[k]); hi_ts = idx[k]
        if lows[k] < lows[k - 1] and lows[k] < lows[k + 1]:
            lo_val = float(lows[k]); lo_ts = idx[k]
    return hi_val, hi_ts, lo_val, lo_ts


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
            px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            px = target_px; reason = 'TP_2R'
        elif sl:
            px = stop_px; reason = 'SL'
        else:
            continue
        ret = (px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return x5_idx[k], float(px), float(ret), reason
    return None


def bucket(n: int) -> str:
    return '4+' if n >= 4 else str(int(n))


def simulate_partition(z: pd.DataFrame, x5: pd.DataFrame, part: str, start: pd.Timestamp, end: pd.Timestamp):
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
    if hi_i - lo_i < 4:
        return []

    active_hi, active_hi_ts, active_lo, active_lo_ts = confirmed_seed(z, lo_i)
    hi_visits = 0; lo_visits = 0
    hi_touching = False; lo_touching = False
    blocked_until = None
    rows = []

    for i in range(lo_i, hi_i - 1):
        # At the start of bar i, pivot i-2 is causally confirmed by completed bar i-1.
        k = i - 2
        if k >= 1 and k + 1 < len(z):
            if highs[k] > highs[k - 1] and highs[k] > highs[k + 1]:
                new_hi = float(highs[k])
                if pd.isna(active_hi) or new_hi != active_hi or idx[k] != active_hi_ts:
                    active_hi = new_hi; active_hi_ts = idx[k]
                    hi_visits = 0; hi_touching = False
            if lows[k] < lows[k - 1] and lows[k] < lows[k + 1]:
                new_lo = float(lows[k])
                if pd.isna(active_lo) or new_lo != active_lo or idx[k] != active_lo_ts:
                    active_lo = new_lo; active_lo_ts = idx[k]
                    lo_visits = 0; lo_touching = False

        # If a position is still open, we still update structural touch state but do not enter.
        can_enter = blocked_until is None or idx[i] > blocked_until

        long_break = (not pd.isna(active_hi)) and closes[i] > active_hi
        short_break = (not pd.isna(active_lo)) and closes[i] < active_lo

        if can_enter and (long_break or short_break):
            side = 'LONG' if long_break else 'SHORT'
            prior_touches = hi_visits if side == 'LONG' else lo_visits
            level = active_hi if side == 'LONG' else active_lo
            level_ts = active_hi_ts if side == 'LONG' else active_lo_ts
            entry_i = i + 1
            entry_ts = idx[entry_i]
            if entry_ts >= end:
                break
            entry_px = float(opens[entry_i])
            if side == 'LONG':
                stop_px = float(lows[i])
                risk = entry_px - stop_px
                if risk <= 0:
                    # breakout consumed the level anyway; reset high side below
                    active_hi = np.nan; active_hi_ts = pd.NaT; hi_visits = 0; hi_touching = False
                    continue
                target_px = entry_px + RR * risk
            else:
                stop_px = float(highs[i])
                risk = stop_px - entry_px
                if risk <= 0:
                    active_lo = np.nan; active_lo_ts = pd.NaT; lo_visits = 0; lo_touching = False
                    continue
                target_px = entry_px - RR * risk

            solved = resolve(xidx, xhi, xlo, entry_ts, entry_px, stop_px, target_px, side, end)
            if solved is None:
                rows.append({
                    'partition': part, 'side': side, 'signal_ts': idx[i], 'entry_ts': entry_ts,
                    'swing_level_ts': level_ts, 'swing_level': float(level),
                    'prior_touches': int(prior_touches), 'touch_bucket': bucket(prior_touches),
                    'entry_px': entry_px, 'stop_px': stop_px, 'target_px': target_px,
                    'risk_pct': float(risk / entry_px), 'resolved': False,
                    'exit_ts': pd.NaT, 'exit_px': np.nan, 'gross_return': np.nan,
                    'net_pnl_usd': np.nan, 'exit_reason': 'CENSORED', 'hold_minutes': np.nan,
                })
                blocked_until = end
                break

            exit_ts, exit_px, ret, reason = solved
            rows.append({
                'partition': part, 'side': side, 'signal_ts': idx[i], 'entry_ts': entry_ts,
                'swing_level_ts': level_ts, 'swing_level': float(level),
                'prior_touches': int(prior_touches), 'touch_bucket': bucket(prior_touches),
                'entry_px': entry_px, 'stop_px': stop_px, 'target_px': target_px,
                'risk_pct': float(risk / entry_px), 'resolved': True,
                'exit_ts': exit_ts, 'exit_px': exit_px, 'gross_return': ret,
                'net_pnl_usd': float(ret * NOTIONAL - FEE), 'exit_reason': reason,
                'hold_minutes': float((exit_ts - entry_ts) / pd.Timedelta(minutes=1)),
            })
            blocked_until = exit_ts

        # Update rejection-touch visits for boundaries that have NOT closed through this bar.
        if not pd.isna(active_hi):
            if closes[i] > active_hi:
                # Level has broken; it is no longer an active unbroken resistance.
                active_hi = np.nan; active_hi_ts = pd.NaT
                hi_visits = 0; hi_touching = False
            else:
                touching = highs[i] >= active_hi
                if touching and not hi_touching:
                    hi_visits += 1
                hi_touching = bool(touching)

        if not pd.isna(active_lo):
            if closes[i] < active_lo:
                active_lo = np.nan; active_lo_ts = pd.NaT
                lo_visits = 0; lo_touching = False
            else:
                touching = lows[i] <= active_lo
                if touching and not lo_touching:
                    lo_visits += 1
                lo_touching = bool(touching)

    return rows


def summarize(g: pd.DataFrame):
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
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    z = build4h(x5)

    rows = []
    for part, (start, end) in PARTS.items():
        rows.extend(simulate_partition(z, x5, part, start, end))
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    buckets = ['ALL', '0', '1', '2', '3', '4+']
    sums = []
    for part in PARTS:
        base = trades[trades.partition == part] if len(trades) else pd.DataFrame()
        for b in buckets:
            g = base if b == 'ALL' else base[base.touch_bucket == b]
            side_long = int((g.side == 'LONG').sum()) if len(g) else 0
            side_short = int((g.side == 'SHORT').sum()) if len(g) else 0
            sums.append({'partition': part, 'touch_bucket': b, 'long_n': side_long,
                         'short_n': side_short, **summarize(g)})
    s = pd.DataFrame(sums)

    major = ('external', 'development', 'reference_validation')
    verdict = {}
    for b in ['0', '1', '2', '3', '4+']:
        q = s[(s.touch_bucket == b) & s.partition.isin(major)]
        verdict[b] = bool(len(q) == 3 and (q.resolved >= 30).all() and
                          (q.net_exp > 0).all() and (q.net_pf >= 1.20).all())
    s['repeatable_pass'] = [verdict.get(r.touch_bucket, False) for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUM, index=False)

    md = [
        '# B27E — BTC 4H Same-Side Swing Touches Before Breakout', '',
        f'Source coverage: **{coverage:.4%}**. 4H causal swing breakout -> next 4H open -> breakout-candle opposite extreme SL -> 2R TP.', '',
        'Touch = distinct rejection visit to the SAME swing boundary before the final close-through breakout. Consecutive touching candles count as one visit. New same-side swing level resets that side count.', '',
        '| Partition | Prior touches | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    order_b = {'ALL': 0, '0': 1, '1': 2, '2': 3, '3': 4, '4+': 5}
    s['ord'] = s.touch_bucket.map(order_b)
    part_order = {k: i for i, k in enumerate(PARTS.keys())}
    s['pord'] = s.partition.map(part_order)
    for r in s.sort_values(['pord', 'ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.touch_bucket} | {r.resolved} | {r.long_n} | {r.short_n} | '
            f'{r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | '
            f'${num(r.total_net)} | {pct(r.med_risk)} | {num(r.med_hold,1)} |'
        )

    md += ['', '## Pre-registered repeatability verdict by prior-touch bucket', '']
    for b in ['0', '1', '2', '3', '4+']:
        md.append(f'- {b} prior touches: **{"PASS" if verdict[b] else "FAIL / INSUFFICIENT"}**')
    md += ['', 'A bucket requires >=30 resolved trades AND positive net expectancy AND net PF >=1.20 in external, development, and reference_validation.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
