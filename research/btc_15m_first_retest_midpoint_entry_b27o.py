#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_previous_session_direct_sweep_b26c as b26c
import btc_prev_session_level_retest_atlas_b27l as b27l

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_15M_FIRST_RETEST_MIDPOINT_ENTRY_B27O_Result.md'
OUT_SUM = ROOT / 'BTC_15M_FIRST_RETEST_MIDPOINT_ENTRY_B27O_Summary.csv'
OUT_TRADES = ROOT / 'BTC_15M_FIRST_RETEST_MIDPOINT_ENTRY_B27O_Trades.csv'

PARTS = b22b.PARTS
TRANSITIONS = b26c.TRANSITIONS
BAR5 = pd.Timedelta(minutes=5)
TF_MIN = 15
TOL = 0.002
NOTIONAL = 500.0
FEE_USD = 0.40


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def first_signal(bars: pd.DataFrame, prev_hi: float, prev_lo: float):
    for ts, r in bars.iterrows():
        close = float(r.close); high = float(r.high); low = float(r.low)
        if close > prev_hi or close < prev_lo:
            return {'status':'BREAK_BEFORE_RETEST'}
        hit_hi = b27l.intersects(high, low, prev_hi, TOL)
        hit_lo = b27l.intersects(high, low, prev_lo, TOL)
        if hit_hi and hit_lo:
            return {'status':'AMBIGUOUS_BOTH_ZONES'}
        if hit_hi:
            return {'status':'SIGNAL','side':'LONG','signal_bar_start':ts,'signal_ts':r.bar_end,'signal_level':'HIGH'}
        if hit_lo:
            return {'status':'SIGNAL','side':'SHORT','signal_bar_start':ts,'signal_ts':r.bar_end,'signal_level':'LOW'}
    return {'status':'NO_RETEST'}


def find_midpoint_fill(q5: pd.DataFrame, signal_ts: pd.Timestamp, session_end: pd.Timestamp, midpoint: float):
    a = int(q5.index.searchsorted(signal_ts, side='left'))
    b = int(q5.index.searchsorted(session_end, side='left'))
    for k in range(a, b):
        r = q5.iloc[k]
        if float(r.low) <= midpoint <= float(r.high):
            return k, q5.index[k]
    return None


def resolve_after_fill(q5: pd.DataFrame, fill_k: int, fill_ts: pd.Timestamp, side: str,
                       entry_px: float, stop_px: float, target_px: float,
                       session_end: pd.Timestamp):
    # Fill bar is order-ambiguous. Conservative treatment:
    # - if the stop is touched anywhere in the fill bar, count SL;
    # - a target-only touch in the fill bar is not awarded because target may have occurred before the limit fill.
    r0 = q5.iloc[fill_k]
    if side == 'LONG':
        fillbar_sl = float(r0.low) <= stop_px
    else:
        fillbar_sl = float(r0.high) >= stop_px
    if fillbar_sl:
        exit_px = stop_px
        ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return fill_ts, float(exit_px), float(ret), 'SL_FILL_5M_CONSERVATIVE'

    b = int(q5.index.searchsorted(session_end, side='left'))
    for k in range(fill_k + 1, b):
        r = q5.iloc[k]
        if side == 'LONG':
            tp = float(r.high) >= target_px
            sl = float(r.low) <= stop_px
        else:
            tp = float(r.low) <= target_px
            sl = float(r.high) >= stop_px
        if tp and sl:
            exit_px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            exit_px = target_px; reason = 'TP_RANGE_EDGE'
        elif sl:
            exit_px = stop_px; reason = 'SL_RANGE_EDGE'
        else:
            continue
        ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return q5.index[k], float(exit_px), float(ret), reason

    # Time exit at first 5m open at/after active-session end from full source is handled by caller.
    return None


def simulate_day(x5: pd.DataFrame, partition: str, part_start: pd.Timestamp, part_end: pd.Timestamp,
                 transition: str, cfg: dict, day: pd.Timestamp):
    ps = b26c.ts_for_day(day, cfg['prev_start']); pe = b26c.ts_for_day(day, cfg['prev_end'])
    ns = b26c.ts_for_day(day, cfg['next_start']); ne = b26c.ts_for_day(day, cfg['next_end'])
    if ps < part_start or ne > part_end:
        return None
    prev = fast_slice(x5, ps, pe); q5 = fast_slice(x5, ns, ne)
    if len(prev) != int((pe-ps)/BAR5) or len(q5) != int((ne-ns)/BAR5):
        return None

    prev_hi = float(prev.high.max()); prev_lo = float(prev.low.min())
    if not prev_hi > prev_lo:
        return None
    midpoint = (prev_hi + prev_lo) / 2.0
    bars = b27l.session_bars(q5, ns, ne, TF_MIN)
    sig = first_signal(bars, prev_hi, prev_lo)

    base = {
        'partition': partition, 'transition': transition, 'date_utc': str(day.date()),
        'previous_session_high': prev_hi, 'previous_session_low': prev_lo,
        'midpoint': midpoint, 'setup_status': sig['status'],
        'active_session_start': ns, 'active_session_end': ne,
    }
    if sig['status'] != 'SIGNAL':
        return {**base, 'side':None, 'signal_level':None, 'signal_ts':pd.NaT,
                'filled':False, 'entry_ts':pd.NaT, 'entry_px':np.nan,
                'stop_px':np.nan, 'target_px':np.nan, 'exit_ts':pd.NaT,
                'exit_px':np.nan, 'exit_reason':sig['status'], 'gross_return':np.nan,
                'net_pnl_usd':np.nan, 'hold_minutes':np.nan}

    side = sig['side']
    stop_px = prev_lo if side == 'LONG' else prev_hi
    target_px = prev_hi if side == 'LONG' else prev_lo
    fill = find_midpoint_fill(q5, sig['signal_ts'], ne, midpoint)
    if fill is None:
        return {**base, **sig, 'filled':False, 'entry_ts':pd.NaT, 'entry_px':np.nan,
                'stop_px':stop_px, 'target_px':target_px, 'exit_ts':pd.NaT,
                'exit_px':np.nan, 'exit_reason':'NO_FILL_MIDPOINT', 'gross_return':np.nan,
                'net_pnl_usd':np.nan, 'hold_minutes':np.nan}

    fill_k, fill_ts = fill
    solved = resolve_after_fill(q5, fill_k, fill_ts, side, midpoint, stop_px, target_px, ne)
    if solved is None:
        pos = int(x5.index.searchsorted(ne, side='left'))
        if pos >= len(x5):
            return {**base, **sig, 'filled':True, 'entry_ts':fill_ts, 'entry_px':midpoint,
                    'stop_px':stop_px, 'target_px':target_px, 'exit_ts':pd.NaT,
                    'exit_px':np.nan, 'exit_reason':'CENSORED', 'gross_return':np.nan,
                    'net_pnl_usd':np.nan, 'hold_minutes':np.nan}
        exit_ts = x5.index[pos]; exit_px = float(x5.iloc[pos].open)
        ret = (exit_px / midpoint - 1.0) * (1.0 if side == 'LONG' else -1.0)
        reason = 'TIME_EXIT_SESSION_END'
    else:
        exit_ts, exit_px, ret, reason = solved

    net = float(ret * NOTIONAL - FEE_USD)
    return {**base, **sig, 'filled':True, 'entry_ts':fill_ts, 'entry_px':midpoint,
            'stop_px':stop_px, 'target_px':target_px, 'exit_ts':exit_ts,
            'exit_px':float(exit_px), 'exit_reason':reason, 'gross_return':float(ret),
            'net_pnl_usd':net,
            'hold_minutes':float((exit_ts-fill_ts)/pd.Timedelta(minutes=1))}


def pf(vals):
    s = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(s[s>0].sum()); neg = float(-s[s<0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos/neg if neg > 0 else np.nan


def summarize(g: pd.DataFrame):
    setups = g[g.setup_status == 'SIGNAL'] if len(g) else g
    f = setups[setups.filled.astype(bool)] if len(setups) else setups
    if len(f) == 0:
        return {'days':int(len(g)), 'setups':int(len(setups)), 'fills':0, 'fill_rate':np.nan,
                'wins':0,'losses':0,'wr':np.nan,'tp_rate':np.nan,'net_pf':np.nan,
                'net_exp':np.nan,'total_net':np.nan,'time_exit_rate':np.nan}
    net = pd.to_numeric(f.net_pnl_usd, errors='coerce')
    resolved = f[net.notna()].copy(); net = pd.to_numeric(resolved.net_pnl_usd, errors='coerce')
    wins = int((net > 0).sum()); losses = int((net <= 0).sum())
    return {'days':int(len(g)), 'setups':int(len(setups)), 'fills':int(len(resolved)),
            'fill_rate':float(len(resolved)/len(setups)) if len(setups) else np.nan,
            'wins':wins,'losses':losses,'wr':float(wins/len(resolved)) if len(resolved) else np.nan,
            'tp_rate':float((resolved.exit_reason=='TP_RANGE_EDGE').mean()) if len(resolved) else np.nan,
            'net_pf':pf(net),'net_exp':float(net.mean()) if len(net) else np.nan,
            'total_net':float(net.sum()) if len(net) else np.nan,
            'time_exit_rate':float((resolved.exit_reason=='TIME_EXIT_SESSION_END').mean()) if len(resolved) else np.nan}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5(); rows=[]
    for part,(start,end) in PARTS.items():
        for day in pd.date_range(start.normalize(), (end-pd.Timedelta(seconds=1)).normalize(), freq='D', tz='UTC'):
            if day.weekday() >= 5: continue
            for transition,cfg in TRANSITIONS.items():
                r = simulate_day(x5, part, start, end, transition, cfg, day)
                if r is not None: rows.append(r)
    trades = pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)

    sums=[]
    for transition in TRANSITIONS:
        for part in PARTS:
            base=trades[(trades.transition==transition)&(trades.partition==part)]
            for group,gg in [('ALL',base),('LONG',base[base.side=='LONG']),('SHORT',base[base.side=='SHORT'])]:
                sums.append({'transition':transition,'partition':part,'group':group,**summarize(gg)})
    s=pd.DataFrame(sums)
    major=('external','development','reference_validation'); verdicts={}
    for transition in TRANSITIONS:
        q=s[(s.transition==transition)&(s.group=='ALL')&s.partition.isin(major)]
        verdicts[transition]=bool(len(q)==3 and (q.fills>=100).all() and (q.net_exp>0).all() and (q.net_pf>=1.20).all())
    s['repeatable_pass']=[verdicts[r.transition] for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUM,index=False)

    md=['# B27O — BTC 15m First Retest -> Midpoint Entry Result','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        'Rule: first unambiguous 15m High-zone retest -> BULL setup -> BUY midpoint on later retrace; first Low-zone retest -> BEAR setup -> SELL midpoint. Zone ±0.20%. Midpoint is frozen previous-session (High+Low)/2. LONG SL=Low TP=High; SHORT SL=High TP=Low. 1:1 before fees.','',
        '| Transition | Partition | Group | Setups | Fills | Fill rate | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Time exit |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in s.itertuples(index=False):
        md.append(f'| {r.transition} | {r.partition} | {r.group} | {r.setups} | {r.fills} | {pct(r.fill_rate)} | {r.wins} | {r.losses} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.time_exit_rate)} |')
    md += ['', '## Pre-registered verdict','']
    for transition in TRANSITIONS:
        md.append(f'- {transition}: **{"PASS" if verdicts[transition] else "FAIL"}**')
    md += ['', f'**B27O overall: {"PASS" if any(verdicts.values()) else "FAIL"}.**','',
           'Gate requires >=100 filled trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation for the same transition.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__ == '__main__':
    main()
