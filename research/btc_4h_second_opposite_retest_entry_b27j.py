#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_4h_opposite_retest_range_entry_b27i as b27i

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_SECOND_OPPOSITE_RETEST_ENTRY_B27J_Result.md'
OUT_SUM = ROOT / 'BTC_4H_SECOND_OPPOSITE_RETEST_ENTRY_B27J_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_SECOND_OPPOSITE_RETEST_ENTRY_B27J_Trades.csv'
PARTS = b22b.PARTS
TOL = 0.002
NOTIONAL = 500.0
FEE = 0.40
RR = 2.0


def first_target_wick_ts(xidx, xhi, xlo, entry_ts, side, level, part_end):
    a = int(xidx.searchsorted(entry_ts, side='left'))
    b = int(xidx.searchsorted(part_end, side='left'))
    for k in range(a, b):
        hit = xhi[k] >= level if side == 'LONG' else xlo[k] <= level
        if hit:
            return xidx[k]
    return pd.NaT


def visit_bucket(n):
    return '2+' if int(n) >= 2 else str(int(n))


def simulate_partition(z, x5, part, start, end):
    idx = z.index
    opens = z.open.to_numpy(float); highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float); closes = z.close.to_numpy(float)
    xidx = x5.index; xhi = x5.high.to_numpy(float); xlo = x5.low.to_numpy(float)

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
        k = i - 2
        if k > reset_i and k >= lo_i + 1 and k + 1 < hi_i:
            pivot_hi = highs[k] > highs[k-1] and highs[k] > highs[k+1]
            pivot_lo = lows[k] < lows[k-1] and lows[k] < lows[k+1]
            if not active:
                if pd.isna(candidate_hi) and pivot_hi:
                    candidate_hi = float(highs[k]); candidate_hi_ts = idx[k]
                if pd.isna(candidate_lo) and pivot_lo:
                    candidate_lo = float(lows[k]); candidate_lo_ts = idx[k]
                if not pd.isna(candidate_hi) and not pd.isna(candidate_lo) and candidate_hi > candidate_lo:
                    active = True
                    range_hi = float(candidate_hi); range_lo = float(candidate_lo)
                    range_hi_ts = candidate_hi_ts; range_lo_ts = candidate_lo_ts
                    hi_visits = lo_visits = 0
                    hi_touching = lo_touching = False
                    consumed = False

        if not active:
            continue

        break_hi = closes[i] > range_hi
        break_lo = closes[i] < range_lo
        if break_hi or break_lo:
            clear_range(i)
            continue

        high_touch = highs[i] >= range_hi*(1-TOL) and closes[i] <= range_hi
        low_touch = lows[i] <= range_lo*(1+TOL) and closes[i] >= range_lo
        if high_touch and low_touch:
            hi_touching = True; lo_touching = True
            continue

        new_hi = bool(high_touch and not hi_touching)
        new_lo = bool(low_touch and not lo_touching)
        if new_hi: hi_visits += 1
        if new_lo: lo_visits += 1
        hi_touching = bool(high_touch); lo_touching = bool(low_touch)

        can_enter_time = blocked_until is None or idx[i] > blocked_until
        long_signal = (not consumed) and can_enter_time and new_lo and lo_visits >= 2 and hi_visits >= 1
        short_signal = (not consumed) and can_enter_time and new_hi and hi_visits >= 2 and lo_visits >= 1
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
            stop_px = float(lows[i]); risk = entry_px - stop_px
            target_side_visits = int(hi_visits); opposite_visits = int(lo_visits)
            target_boundary = float(range_hi)
            target_px = entry_px + RR*risk if risk > 0 else np.nan
        else:
            stop_px = float(highs[i]); risk = stop_px - entry_px
            target_side_visits = int(lo_visits); opposite_visits = int(hi_visits)
            target_boundary = float(range_lo)
            target_px = entry_px - RR*risk if risk > 0 else np.nan

        consumed = True
        if risk <= 0:
            continue

        solved = b27i.resolve_trade(xidx, xhi, xlo, entry_ts, entry_px, stop_px, target_px, side, end)
        stop_ts = b27i.first_stop_ts(xidx, xhi, xlo, entry_ts, stop_px, side, end)
        wick_ts = first_target_wick_ts(xidx, xhi, xlo, entry_ts, side, target_boundary, end)
        break_ts = b27i.first_target_break_close_ts(z, entry_i, side, range_hi, range_lo, end)
        wick_before_stop = (not pd.isna(wick_ts)) and (pd.isna(stop_ts) or wick_ts < stop_ts)
        breakout_before_stop = (not pd.isna(break_ts)) and (pd.isna(stop_ts) or break_ts < stop_ts)

        base = {
            'partition': part, 'side': side, 'signal_ts': idx[i], 'entry_ts': entry_ts,
            'range_high_ts': range_hi_ts, 'range_low_ts': range_lo_ts,
            'range_high': float(range_hi), 'range_low': float(range_lo),
            'target_side_visits_at_entry': target_side_visits,
            'target_visit_bucket': visit_bucket(target_side_visits),
            'opposite_visits_at_entry': opposite_visits,
            'entry_px': entry_px, 'stop_px': stop_px, 'target_px': float(target_px),
            'risk_pct': float(risk/entry_px), 'target_boundary': target_boundary,
            'target_wick_ts': wick_ts, 'target_break_ts': break_ts, 'stop_first_ts': stop_ts,
            'target_wick_before_stop': bool(wick_before_stop),
            'target_break_before_stop': bool(breakout_before_stop),
        }

        if solved is None:
            rows.append({**base, 'resolved': False, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                         'gross_return': np.nan, 'net_pnl_usd': np.nan,
                         'exit_reason': 'CENSORED', 'hold_minutes': np.nan})
            blocked_until = end
        else:
            exit_ts, exit_px, ret, reason = solved
            rows.append({**base, 'resolved': True, 'exit_ts': exit_ts, 'exit_px': exit_px,
                         'gross_return': ret, 'net_pnl_usd': float(ret*NOTIONAL-FEE),
                         'exit_reason': reason,
                         'hold_minutes': float((exit_ts-entry_ts)/pd.Timedelta(minutes=1))})
            blocked_until = exit_ts

    return rows


def summarize(g):
    if len(g) == 0:
        return {'entered':0,'resolved':0,'wins':0,'losses':0,'wr':np.nan,'net_pf':np.nan,
                'net_exp':np.nan,'total_net':np.nan,'med_risk':np.nan,'med_hold':np.nan,
                'wick_rate':np.nan,'breakout_rate':np.nan}
    r = g[g.resolved.astype(bool)].copy()
    wrate = float(g.target_wick_before_stop.astype(bool).mean())
    brate = float(g.target_break_before_stop.astype(bool).mean())
    if len(r) == 0:
        return {'entered':len(g),'resolved':0,'wins':0,'losses':0,'wr':np.nan,'net_pf':np.nan,
                'net_exp':np.nan,'total_net':np.nan,'med_risk':float(g.risk_pct.median()),'med_hold':np.nan,
                'wick_rate':wrate,'breakout_rate':brate}
    net = r.net_pnl_usd.astype(float)
    wins = int((r.exit_reason == 'TP_2R').sum()); losses = int(len(r)-wins)
    return {'entered':int(len(g)),'resolved':int(len(r)),'wins':wins,'losses':losses,
            'wr':wins/len(r),'net_pf':b27i.pf(net),'net_exp':float(net.mean()),'total_net':float(net.sum()),
            'med_risk':float(r.risk_pct.median()),'med_hold':float(r.hold_minutes.median()),
            'wick_rate':wrate,'breakout_rate':brate}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5(); z = b27i.build4h(x5)
    rows=[]
    for part,(start,end) in PARTS.items():
        rows.extend(simulate_partition(z,x5,part,start,end))
    trades=pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)

    sums=[]
    for part in PARTS:
        base=trades[trades.partition==part] if len(trades) else pd.DataFrame()
        groups=[('ALL',base)]
        if len(base):
            groups += [('TARGET_VISITS_1',base[base.target_visit_bucket=='1']),
                       ('TARGET_VISITS_2PLUS',base[base.target_visit_bucket=='2+']),
                       ('LONG',base[base.side=='LONG']),('SHORT',base[base.side=='SHORT'])]
        else:
            groups += [('TARGET_VISITS_1',base),('TARGET_VISITS_2PLUS',base),('LONG',base),('SHORT',base)]
        for name,g in groups:
            sums.append({'partition':part,'group':name,**summarize(g)})
    s=pd.DataFrame(sums)
    major=('external','development','reference_validation')
    q=s[(s.group=='ALL') & s.partition.isin(major)]
    passed=bool(len(q)==3 and (q.resolved>=30).all() and (q.net_exp>0).all() and (q.net_pf>=1.20).all())
    s['primary_pass']=passed; s.to_csv(OUT_SUM,index=False)

    md=['# B27J — BTC 4H Second Opposite-Side Retest Entry','',
        f'Source coverage: **{coverage:.4%}**. Frozen causal 4H range, ±0.20% zones. LONG at second-or-later Low retest after >=1 known High visit; SHORT symmetric. Entry next 4H open; retest candle extreme SL; TP 2R.','',
        '| Partition | Group | Resolved | W | L | WR | Net PF | Net exp/trade | Total net | Target wick before SL | Target close-break before SL | Median stop | Median hold min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    po={k:i for i,k in enumerate(PARTS)}; go={'ALL':0,'TARGET_VISITS_1':1,'TARGET_VISITS_2PLUS':2,'LONG':3,'SHORT':4}
    s['po']=s.partition.map(po); s['go']=s.group.map(go)
    for r in s.sort_values(['po','go']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.group} | {r.resolved} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.wick_rate)} | {pct(r.breakout_rate)} | {pct(r.med_risk)} | {num(r.med_hold,1)} |')
    md += ['', '## Pre-registered verdict', '', f'**B27J: {"PASS" if passed else "FAIL / INSUFFICIENT"}.**', '',
           'PASS requires >=30 resolved trades, positive fee-sensitive expectancy, and PF >=1.20 in external, development, and reference_validation.', '',
           'Subgroups are diagnostic only; no post-hoc promotion.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
