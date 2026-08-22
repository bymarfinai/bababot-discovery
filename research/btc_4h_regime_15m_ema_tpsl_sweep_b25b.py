#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_crossover_cycle_entry_b23e as b23e

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_REGIME_15M_EMA_TPSL_SWEEP_B25B_Result.md'
OUT_SUMMARY = ROOT / 'BTC_4H_REGIME_15M_EMA_TPSL_SWEEP_B25B_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_REGIME_15M_EMA_TPSL_SWEEP_B25B_Trades.csv'

PARTS = b22b.PARTS
BAR15 = pd.Timedelta(minutes=15)
BAR4H = pd.Timedelta(hours=4)
NOTIONAL = 500.0
FEE_USD = 0.40
GRID = [
    ('TP0.50_SL0.50', 0.0050, 0.0050),
    ('TP0.75_SL0.75', 0.0075, 0.0075),
    ('TP1.00_SL0.50', 0.0100, 0.0050),
    ('TP1.00_SL0.75', 0.0100, 0.0075),
    ('TP1.50_SL1.00', 0.0150, 0.0100),
    ('TP2.00_SL1.00', 0.0200, 0.0100),
    ('TP2.00_SL1.50', 0.0200, 0.0150),
]


def pct(v):
    if v is None or pd.isna(v): return '-'
    return f'{100*float(v):.2f}%'


def num(v, d=2):
    if v is None or pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def build_inputs(x5):
    z15 = b23e.add_cycles(b22b.enrich(b22b.resample_ohlc(x5, '15min')))
    h4 = b22b.resample_ohlc(x5, '4h')
    h4_av = b21._bull_available(h4, BAR4H)
    return z15, h4_av


def regime_on_at(h4_av, when):
    pos = int(h4_av.index.searchsorted(when, side='right')) - 1
    return False if pos < 0 else bool(h4_av.iloc[pos].bull)


def entry_events(z15, h4_av, part, start, end):
    idx = z15.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi-lo < 10: return []

    opens = z15.open.to_numpy(float)
    closes = z15.close.to_numpy(float)
    ema20 = z15.ema20.to_numpy(float)
    ema50 = z15.ema50.to_numpy(float)
    bull = z15.bull_cross.fillna(False).to_numpy(bool)
    bear = z15.bear_cross.fillna(False).to_numpy(bool)

    rows=[]; cursor=max(lo,1); final_i=hi-1
    while cursor < final_i:
        cross_i=None
        for i in range(cursor, final_i):
            if bull[i]: cross_i=i; break
        if cross_i is None: break

        bear_i=None
        for j in range(cross_i+1, hi):
            if bear[j]: bear_i=j; break
        cycle_end=bear_i if bear_i is not None else hi

        cross_complete=idx[cross_i]+BAR15
        if regime_on_at(h4_av, cross_complete):
            signal_i=None
            for j in range(cross_i+1, cycle_end):
                if ema20[j] > ema50[j] and closes[j] > opens[j]:
                    signal_i=j; break
            if signal_i is not None:
                signal_complete=idx[signal_i]+BAR15
                entry_i=signal_i+1
                if regime_on_at(h4_av, signal_complete) and entry_i < cycle_end and entry_i < hi:
                    rows.append({
                        'partition':part,
                        'bull_cross_ts':idx[cross_i],
                        'signal_ts':idx[signal_i],
                        'entry_ts':idx[entry_i],
                        'entry_px':float(opens[entry_i]),
                        'partition_end':end,
                    })
        cursor=(bear_i+1) if bear_i is not None else hi
    return rows


def resolve(x5, event, tp, sl):
    entry_ts=event['entry_ts']; entry_px=float(event['entry_px']); end=event['partition_end']
    tp_px=entry_px*(1+tp); sl_px=entry_px*(1-sl)
    q=x5[(x5.index>=entry_ts)&(x5.index<end)]
    for ts,row in q.iterrows():
        th=float(row.high)>=tp_px; sh=float(row.low)<=sl_px
        if th and sh:
            return 'SL_SAME_5M_BAR_CONSERVATIVE', ts, -sl
        if th: return 'TP', ts, tp
        if sh: return 'SL', ts, -sl
    return 'PARTITION_CENSORED', pd.NaT, np.nan


def summarize(g):
    r=g[g.resolved].copy()
    if len(r)==0:
        return dict(resolved=0,wins=0,losses=0,wr=np.nan,gross_pf=np.nan,gross_expectancy_pct=np.nan,net_expectancy_usd=np.nan,total_net_usd=np.nan,median_hold_min=np.nan,samebar=np.nan)
    wins=int((r.exit_reason=='TP').sum()); losses=int(len(r)-wins)
    gp=float(r.loc[r.gross_return>0,'gross_pnl_usd'].sum())
    gl=float(-r.loc[r.gross_return<0,'gross_pnl_usd'].sum())
    pf=float('inf') if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan)
    return dict(
        resolved=int(len(r)), wins=wins, losses=losses, wr=float(wins/len(r)), gross_pf=pf,
        gross_expectancy_pct=float(r.gross_return.mean()), net_expectancy_usd=float(r.net_pnl_usd.mean()),
        total_net_usd=float(r.net_pnl_usd.sum()), median_hold_min=float(r.hold_minutes.median()),
        samebar=float((r.exit_reason=='SL_SAME_5M_BAR_CONSERVATIVE').mean()),
    )


def main():
    x5,coverage=b21.load5(); z15,h4_av=build_inputs(x5)
    events=[]
    for part,(start,end) in PARTS.items(): events += entry_events(z15,h4_av,part,start,end)

    trades=[]
    for ev in events:
        for cfg,tp,sl in GRID:
            reason,exit_ts,ret=resolve(x5,ev,tp,sl)
            resolved=pd.notna(ret)
            hold=np.nan if not resolved else float((exit_ts-ev['entry_ts'])/pd.Timedelta(minutes=1))
            gross=np.nan if not resolved else ret*NOTIONAL
            trades.append({**{k:v for k,v in ev.items() if k!='partition_end'},'config':cfg,'tp':tp,'sl':sl,
                           'resolved':resolved,'exit_reason':reason,'exit_ts':exit_ts,'gross_return':ret,
                           'gross_pnl_usd':gross,'net_pnl_usd':np.nan if not resolved else gross-FEE_USD,'hold_minutes':hold})
    t=pd.DataFrame(trades); t.to_csv(OUT_TRADES,index=False)

    sums=[]
    for cfg,tp,sl in GRID:
        for part in PARTS:
            g=t[(t.config==cfg)&(t.partition==part)]
            m=summarize(g)
            sums.append({'config':cfg,'tp':tp,'sl':sl,'rr':tp/sl,'partition':part,'entered':len(g),**m})
    s=pd.DataFrame(sums)

    majors=['external','development','reference_validation']
    verdict=[]
    for cfg,_,_ in GRID:
        q=s[(s.config==cfg)&(s.partition.isin(majors))]
        repeatable=bool(len(q)==3 and (q.resolved>=50).all() and (q.net_expectancy_usd>0).all())
        verdict.append({'config':cfg,'repeatable_positive_net':repeatable,
                        'min_major_net_expectancy':float(q.net_expectancy_usd.min()) if len(q) else np.nan,
                        'min_major_wr':float(q.wr.min()) if len(q) else np.nan,
                        'mean_major_net_expectancy':float(q.net_expectancy_usd.mean()) if len(q) else np.nan})
    v=pd.DataFrame(verdict)
    s=s.merge(v,on='config',how='left'); s.to_csv(OUT_SUMMARY,index=False)

    md=['# BTC 4H Regime + 15m EMA TP/SL Sweep B25B — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Entry is frozen B25A. Only TP/SL changes. 5m determines first barrier touch; same-5m TP+SL is conservatively SL.','',
        '| Config | Partition | N | W | L | WR | PF | Gross exp | Net exp/trade | Total net | Med hold min | Repeatable across 3 major partitions |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in s.itertuples(index=False):
        md.append(f'| {r.config} | {r.partition} | {r.resolved} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.gross_pf)} | {pct(r.gross_expectancy_pct)} | ${num(r.net_expectancy_usd)} | ${num(r.total_net_usd)} | {num(r.median_hold_min,1)} | {"PASS" if r.repeatable_positive_net else "FAIL"} |')

    md += ['', '## Cross-partition verdict','']
    for r in v.itertuples(index=False):
        md.append(f'- {r.config}: **{"PASS" if r.repeatable_positive_net else "FAIL"}**; worst major net expectancy ${num(r.min_major_net_expectancy)}; worst major WR {pct(r.min_major_wr)}.')
    passes=v[v.repeatable_positive_net]
    if len(passes):
        best=passes.sort_values('mean_major_net_expectancy',ascending=False).iloc[0]
        md += ['',f'Best repeatable positive-net configuration by mean major-partition expectancy: **{best.config}**. This is a sweep clue, not promotion.']
    else:
        md += ['', 'No frozen TP/SL configuration is positive after illustrative fees in all three major partitions. **Sweep verdict: FAIL.**']
    md += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
