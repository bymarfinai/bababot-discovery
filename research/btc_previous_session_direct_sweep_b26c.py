#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PREVIOUS_SESSION_DIRECT_SWEEP_B26C_Result.md'
OUT_SUMMARY = ROOT / 'BTC_PREVIOUS_SESSION_DIRECT_SWEEP_B26C_Summary.csv'
OUT_TRADES = ROOT / 'BTC_PREVIOUS_SESSION_DIRECT_SWEEP_B26C_Trades.csv'

PARTS = b22b.PARTS
NOTIONAL = 500.0
FEE_USD = 0.40
BAR = pd.Timedelta(minutes=5)

TRANSITIONS = {
    'ASIA_TO_LONDON': {
        'prev_start': (0, 0), 'prev_end': (8, 0),
        'next_start': (8, 0), 'next_end': (13, 30),
    },
    'LONDON_TO_NEWYORK': {
        'prev_start': (8, 0), 'prev_end': (13, 30),
        'next_start': (13, 30), 'next_end': (20, 0),
    },
}


def ts_for_day(day: pd.Timestamp, hhmm: tuple[int, int]) -> pd.Timestamp:
    hh, mm = hhmm
    return pd.Timestamp(day.date(), tz='UTC') + pd.Timedelta(hours=hh, minutes=mm)


def find_candidate(q: pd.DataFrame, prev_hi: float, prev_lo: float):
    opens = q.open.to_numpy(float)
    highs = q.high.to_numpy(float)
    lows = q.low.to_numpy(float)
    closes = q.close.to_numpy(float)
    idx = q.index
    cands = []
    for s in range(0, len(q) - 1):
        if highs[s] > prev_hi and closes[s] < prev_hi:
            entry_i = s + 1
            entry_px = float(opens[entry_i])
            stop_px = float(highs[s])
            risk_px = stop_px - entry_px
            if risk_px > 0:
                cands.append({
                    'side':'SHORT','signal_ts':idx[s],'entry_ts':idx[entry_i],
                    'entry_px':entry_px,'sweep_level':prev_hi,'sweep_extreme':float(highs[s]),
                    'stop_px':stop_px,'target_px':entry_px - 2.0*risk_px,
                    'risk_pct':risk_px/entry_px,
                })
        if lows[s] < prev_lo and closes[s] > prev_lo:
            entry_i = s + 1
            entry_px = float(opens[entry_i])
            stop_px = float(lows[s])
            risk_px = entry_px - stop_px
            if risk_px > 0:
                cands.append({
                    'side':'LONG','signal_ts':idx[s],'entry_ts':idx[entry_i],
                    'entry_px':entry_px,'sweep_level':prev_lo,'sweep_extreme':float(lows[s]),
                    'stop_px':stop_px,'target_px':entry_px + 2.0*risk_px,
                    'risk_pct':risk_px/entry_px,
                })
    if not cands:
        return None
    cands.sort(key=lambda z: (z['entry_ts'], 0 if z['side']=='LONG' else 1))
    return cands[0]


def resolve(x5: pd.DataFrame, cand: dict, session_end: pd.Timestamp):
    entry_ts = cand['entry_ts']; entry_px = float(cand['entry_px'])
    stop_px = float(cand['stop_px']); target_px = float(cand['target_px']); side = cand['side']
    q = x5[(x5.index >= entry_ts) & (x5.index < session_end)]
    for ts, row in q.iterrows():
        if side == 'LONG':
            tp_hit = float(row.high) >= target_px
            sl_hit = float(row.low) <= stop_px
        else:
            tp_hit = float(row.low) <= target_px
            sl_hit = float(row.high) >= stop_px
        if tp_hit and sl_hit:
            exit_px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp_hit:
            exit_px = target_px; reason = 'TP_2R'
        elif sl_hit:
            exit_px = stop_px; reason = 'SL'
        else:
            continue
        gross_ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return reason, ts, float(exit_px), float(gross_ret)

    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]; exit_px = float(x5.iloc[pos].open)
    gross_ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
    return 'TIME_EXIT_SESSION_END', ts, exit_px, float(gross_ret)


def simulate_day(x5: pd.DataFrame, transition: str, cfg: dict, day: pd.Timestamp,
                 partition: str, part_start: pd.Timestamp, part_end: pd.Timestamp):
    prev_start = ts_for_day(day, cfg['prev_start']); prev_end = ts_for_day(day, cfg['prev_end'])
    next_start = ts_for_day(day, cfg['next_start']); next_end = ts_for_day(day, cfg['next_end'])
    if prev_start < part_start or next_end > part_end:
        return None
    prev = x5[(x5.index >= prev_start) & (x5.index < prev_end)]
    q = x5[(x5.index >= next_start) & (x5.index < next_end)]
    if len(prev) != int((prev_end-prev_start)/BAR) or len(q) != int((next_end-next_start)/BAR):
        return None
    prev_hi = float(prev.high.max()); prev_lo = float(prev.low.min())
    cand = find_candidate(q, prev_hi, prev_lo)
    if cand is None:
        return None
    solved = resolve(x5, cand, next_end)
    if solved is None:
        return None
    reason, exit_ts, exit_px, gross_ret = solved
    gross_pnl = gross_ret * NOTIONAL; net_pnl = gross_pnl - FEE_USD
    return {
        'partition':partition,'transition':transition,'date_utc':str(day.date()),
        'previous_session_high':prev_hi,'previous_session_low':prev_lo,
        **cand,'exit_reason':reason,'exit_ts':exit_ts,'exit_px':exit_px,
        'gross_return':gross_ret,'gross_pnl_usd':gross_pnl,'net_pnl_usd':net_pnl,
        'hold_minutes':float((exit_ts-cand['entry_ts'])/pd.Timedelta(minutes=1)),
    }


def pf(vals: pd.Series):
    v = pd.to_numeric(vals, errors='coerce').dropna()
    pos = float(v[v>0].sum()); neg = float(-v[v<0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos/neg if neg > 0 else np.nan


def summarize(g: pd.DataFrame):
    if len(g)==0:
        return {'n':0,'wins':0,'losses':0,'wr':np.nan,'tp_rate':np.nan,'net_pf':np.nan,
                'net_expectancy_usd':np.nan,'total_net_usd':np.nan,'median_risk_pct':np.nan,
                'median_hold_min':np.nan,'time_exit_rate':np.nan,'samebar_rate':np.nan}
    net = g.net_pnl_usd.astype(float)
    return {
        'n':int(len(g)),'wins':int((net>0).sum()),'losses':int((net<=0).sum()),
        'wr':float((net>0).mean()),'tp_rate':float((g.exit_reason=='TP_2R').mean()),
        'net_pf':float(pf(net)),'net_expectancy_usd':float(net.mean()),'total_net_usd':float(net.sum()),
        'median_risk_pct':float(g.risk_pct.median()),'median_hold_min':float(g.hold_minutes.median()),
        'time_exit_rate':float((g.exit_reason=='TIME_EXIT_SESSION_END').mean()),
        'samebar_rate':float((g.exit_reason=='SL_SAME_5M_CONSERVATIVE').mean()),
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    rows=[]
    for part,(start,end) in PARTS.items():
        first_day=start.normalize(); last_day=(end-pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first_day,last_day,freq='D',tz='UTC'):
            if day.weekday()>=5: continue
            for transition,cfg in TRANSITIONS.items():
                r=simulate_day(x5,transition,cfg,day,part,start,end)
                if r is not None: rows.append(r)
    trades=pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)
    sums=[]
    for transition in TRANSITIONS:
        for part in PARTS:
            g=trades[(trades.transition==transition)&(trades.partition==part)] if len(trades) else pd.DataFrame()
            sums.append({'transition':transition,'partition':part,**summarize(g)})
    s=pd.DataFrame(sums)
    major=('external','development','reference_validation'); verdicts={}
    for transition in TRANSITIONS:
        z=s[(s.transition==transition)&s.partition.isin(major)]
        verdicts[transition]=bool(len(z)==3 and (z.n>=100).all() and (z.net_expectancy_usd>0).all() and (z.net_pf>=1.20).all())
    s['repeatable_pass']=[verdicts[r.transition] for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUMMARY,index=False)

    md=['# BTC Previous-Session Direct Sweep B26C — Result','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Frozen sequence: completed previous-session HIGH/LOW -> same-candle sweep and reclaim -> immediate next-5m-open entry -> stop at sweep candle extreme -> TP 2R; otherwise time exit at active-session end. No ChoCH/BOS, FVG, EMA, order block, or retest filter. Weekdays only.','',
        'Session windows are fixed UTC: Asia 00:00-08:00, London 08:00-13:30, New York 13:30-20:00.','',
        '| Transition | Partition | N | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Median risk | Median hold min | Time exit | Same-5m ambiguity |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in s.itertuples(index=False):
        md.append(f'| {r.transition} | {r.partition} | {r.n} | {r.wins} | {r.losses} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_expectancy_usd)} | ${num(r.total_net_usd)} | {pct(r.median_risk_pct)} | {num(r.median_hold_min,1)} | {pct(r.time_exit_rate)} | {pct(r.samebar_rate)} |')
    md+=['','## Frozen repeatability verdict','']
    for transition in TRANSITIONS: md.append(f'- {transition}: **{"PASS" if verdicts[transition] else "FAIL"}**')
    md+=['',f'**B26C overall: {"PASS" if any(verdicts.values()) else "FAIL"}.**','',
         'Gate requires the same transition to have >=100 trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.','',
         'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
