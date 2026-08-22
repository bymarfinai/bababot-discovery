#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_FROZEN_SWING_ZONE_TOUCH_B27G_Result.md'
OUT_SUM = ROOT / 'BTC_4H_FROZEN_SWING_ZONE_TOUCH_B27G_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_FROZEN_SWING_ZONE_TOUCH_B27G_Trades.csv'
PARTS = b22b.PARTS
TOLS = {'TOL_0.10': 0.001, 'TOL_0.20': 0.002}
NOTIONAL = 500.0
FEE = 0.40
RR = 2.0


def pf(v):
    s = pd.Series(v, dtype=float)
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def build4h(x5):
    return b22b.resample_ohlc(x5, '4h')


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


def bucket(n):
    return '4+' if int(n) >= 4 else str(int(n))


def simulate_partition(z, x5, part, start, end, tol_name, tol):
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
    hi_visits = lo_visits = 0
    hi_touching = lo_touching = False
    blocked_until = None
    rows = []

    for i in range(lo_i, hi_i - 1):
        # Causal pivot k=i-2 becomes known before bar i opens, after k+1 completed.
        k = i - 2
        if k >= lo_i + 1 and k + 1 < hi_i:
            pivot_hi = highs[k] > highs[k - 1] and highs[k] > highs[k + 1]
            pivot_lo = lows[k] < lows[k - 1] and lows[k] < lows[k + 1]
            if pd.isna(active_hi) and pivot_hi:
                active_hi = float(highs[k])
                active_hi_ts = idx[k]
                hi_visits = 0
                hi_touching = False
            if pd.isna(active_lo) and pivot_lo:
                active_lo = float(lows[k])
                active_lo_ts = idx[k]
                lo_visits = 0
                lo_touching = False

        long_break = (not pd.isna(active_hi)) and closes[i] > active_hi
        short_break = (not pd.isna(active_lo)) and closes[i] < active_lo
        can_enter = blocked_until is None or idx[i] > blocked_until

        if (long_break or short_break) and can_enter:
            # If both sides somehow close-through on one 4H candle, choose the side with larger
            # normalized close extension beyond its frozen level; exact tie -> LONG.
            if long_break and short_break:
                le = (closes[i] - active_hi) / active_hi
                se = (active_lo - closes[i]) / active_lo
                side = 'LONG' if le >= se else 'SHORT'
            else:
                side = 'LONG' if long_break else 'SHORT'

            level = active_hi if side == 'LONG' else active_lo
            level_ts = active_hi_ts if side == 'LONG' else active_lo_ts
            prior_touches = hi_visits if side == 'LONG' else lo_visits
            entry_i = i + 1
            entry_ts = idx[entry_i]
            if entry_ts >= end:
                break
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
                    'tolerance': tol_name,
                    'tol_value': tol,
                    'side': side,
                    'signal_ts': idx[i],
                    'entry_ts': entry_ts,
                    'swing_level_ts': level_ts,
                    'swing_level': float(level),
                    'prior_touches': int(prior_touches),
                    'touch_bucket': bucket(prior_touches),
                    'entry_px': entry_px,
                    'stop_px': stop_px,
                    'target_px': float(target_px),
                    'risk_pct': float(risk / entry_px),
                }
                if solved is None:
                    rows.append({**base,
                                 'resolved': False, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                                 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                                 'exit_reason': 'CENSORED', 'hold_minutes': np.nan})
                    blocked_until = end
                else:
                    exit_ts, exit_px, ret, reason = solved
                    rows.append({**base,
                                 'resolved': True, 'exit_ts': exit_ts, 'exit_px': exit_px,
                                 'gross_return': ret,
                                 'net_pnl_usd': float(ret * NOTIONAL - FEE),
                                 'exit_reason': reason,
                                 'hold_minutes': float((exit_ts - entry_ts) / pd.Timedelta(minutes=1))})
                    blocked_until = exit_ts

        # Breakout candle is explicitly excluded from touch counting.
        if long_break:
            active_hi = np.nan
            active_hi_ts = pd.NaT
            hi_visits = 0
            hi_touching = False
        elif not pd.isna(active_hi):
            # Near-miss or rejection within tolerance below/through the high level; close must remain
            # on the pre-breakout side of the original frozen level.
            touching = highs[i] >= active_hi * (1.0 - tol) and closes[i] <= active_hi
            if touching and not hi_touching:
                hi_visits += 1
            hi_touching = bool(touching)

        if short_break:
            active_lo = np.nan
            active_lo_ts = pd.NaT
            lo_visits = 0
            lo_touching = False
        elif not pd.isna(active_lo):
            touching = lows[i] <= active_lo * (1.0 + tol) and closes[i] >= active_lo
            if touching and not lo_touching:
                lo_visits += 1
            lo_touching = bool(touching)

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
    z = build4h(x5)
    rows = []
    for tol_name, tol in TOLS.items():
        for part, (start, end) in PARTS.items():
            rows.extend(simulate_partition(z, x5, part, start, end, tol_name, tol))
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    bs = ['ALL', '0', '1', '2', '3', '4+']
    sums = []
    for tol_name in TOLS:
        for part in PARTS:
            base = trades[(trades.tolerance == tol_name) & (trades.partition == part)] if len(trades) else pd.DataFrame()
            for b in bs:
                g = base if b == 'ALL' else base[base.touch_bucket == b]
                sums.append({
                    'tolerance': tol_name,
                    'partition': part,
                    'touch_bucket': b,
                    'long_n': int((g.side == 'LONG').sum()) if len(g) else 0,
                    'short_n': int((g.side == 'SHORT').sum()) if len(g) else 0,
                    **summarize(g),
                })
    s = pd.DataFrame(sums)
    major = ('external', 'development', 'reference_validation')
    verdict = {}
    for tol_name in TOLS:
        for b in ['0', '1', '2', '3', '4+']:
            q = s[(s.tolerance == tol_name) & (s.touch_bucket == b) & s.partition.isin(major)]
            verdict[(tol_name, b)] = bool(
                len(q) == 3
                and (q.resolved >= 30).all()
                and (q.net_exp > 0).all()
                and (q.net_pf >= 1.20).all()
            )
    s['repeatable_pass'] = [verdict.get((r.tolerance, r.touch_bucket), False) for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUM, index=False)

    md = [
        '# B27G — BTC 4H Frozen Swing-Level Zone Retest Breakout',
        '',
        f'Source coverage: **{coverage:.4%}**. Same frozen swing-level breakout and 2R trade rule as B27F; only the pre-breakout retest definition is expanded to 0.10% and 0.20% zones.',
        '',
        'Retest HIGH: high reaches at least level*(1-tolerance) while close remains <= original level. Retest LOW: low reaches at most level*(1+tolerance) while close remains >= original level. Consecutive qualifying candles = one visit. Breakout remains strict close-through of the original level.',
        '',
        '| Tolerance | Partition | Prior retests | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    bo = {'ALL': 0, '0': 1, '1': 2, '2': 3, '3': 4, '4+': 5}
    po = {k: i for i, k in enumerate(PARTS)}
    to = {k: i for i, k in enumerate(TOLS)}
    s['bo'] = s.touch_bucket.map(bo)
    s['po'] = s.partition.map(po)
    s['to'] = s.tolerance.map(to)
    for r in s.sort_values(['to', 'po', 'bo']).itertuples(index=False):
        md.append(
            f'| {r.tolerance} | {r.partition} | {r.touch_bucket} | {r.resolved} | {r.long_n} | {r.short_n} | '
            f'{r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | '
            f'{pct(r.med_risk)} | {num(r.med_hold, 1)} |'
        )

    md += ['', '## Pre-registered repeatability verdict', '']
    for tol_name in TOLS:
        for b in ['0', '1', '2', '3', '4+']:
            md.append(f'- {tol_name}, {b} prior retests: **{"PASS" if verdict[(tol_name, b)] else "FAIL / INSUFFICIENT"}**')
    md += [
        '',
        'Gate: same tolerance + retest bucket must have >=30 resolved trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.',
        '',
        f'**B27G overall: {"PASS" if any(verdict.values()) else "FAIL / INSUFFICIENT"}.**',
        '',
        'Research only; live BBC unchanged.',
    ]
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
