#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_LOCAL_RISK_ENTRY_B27U_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_LOCAL_RISK_ENTRY_B27U_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_LOCAL_RISK_ENTRY_B27U_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_LOCAL_RISK_ENTRY_B27U_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external','development','reference_validation','august')
KS = (1,2)
ENTRIES = {'F75':0.75,'F80':0.80,'F85':0.85}
STOPS = {'D10':0.10,'D15':0.15}


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def load_signals():
    s=pd.read_csv(SIGNALS)
    s=s[(s.transition=='LONDON_TO_NEWYORK')&(s.side=='LONG')&(s.k.isin(KS))&(s.opp_visits_at_signal==0)].copy()
    for c in ('signal_ts','signal_bar_start','active_session_end'):
        s[c]=pd.to_datetime(s[c],utc=True)
    return s.sort_values(['partition','signal_ts','k']).reset_index(drop=True)


def find_fill(q,entry_px,H,L):
    for k,(ts,r) in enumerate(q.iterrows()):
        c=float(r.close)
        if c>H or c<L:
            return None,'RANGE_BROKE_BEFORE_FILL'
        if float(r.low)<=entry_px<=float(r.high):
            return k,'FILLED'
    return None,'NO_FILL'


def resolve(q,fill_k,entry_px,stop_px,target_px):
    r0=q.iloc[fill_k]
    if float(r0.low)<=stop_px:
        return q.index[fill_k],stop_px,'SL_FILL_5M_CONSERVATIVE'
    for k in range(fill_k+1,len(q)):
        r=q.iloc[k]
        tp=float(r.high)>=target_px
        sl=float(r.low)<=stop_px
        if tp and sl:
            return q.index[k],stop_px,'SL_SAME_5M_CONSERVATIVE'
        if sl:
            return q.index[k],stop_px,'SL_LOCAL_RANGE'
        if tp:
            return q.index[k],target_px,'TP_PREV_HIGH'
    return None


def simulate_one(x5,s,entry_name,stop_name):
    H=float(s.previous_session_high); L=float(s.previous_session_low); rng=H-L
    sig=pd.Timestamp(s.signal_ts); end=pd.Timestamp(s.active_session_end)
    ef=ENTRIES[entry_name]; sd=STOPS[stop_name]; sf=ef-sd
    entry_px=L+ef*rng; stop_px=L+sf*rng; target_px=H
    assert H>L and 0<sf<ef<1
    rr=(target_px-entry_px)/(entry_px-stop_px)
    q=fast_slice(x5,sig,end)
    base={'partition':s.partition,'date_utc':s.date_utc,'k':int(s.k),'signal_ts':sig,
          'structural_outcome':s.structural_outcome,'entry_name':entry_name,'stop_name':stop_name,
          'entry_fraction':ef,'stop_fraction':sf,'entry_px_planned':entry_px,'stop_px':stop_px,
          'target_px':target_px,'nominal_rr':rr}
    if q.empty:
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_ELIGIBLE_5M','net_pnl_usd':np.nan}
    fk,status=find_fill(q,entry_px,H,L)
    if fk is None:
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':status,'net_pnl_usd':np.nan}
    entry_ts=q.index[fk]
    solved=resolve(q,fk,entry_px,stop_px,target_px)
    if solved is None:
        pos=int(x5.index.searchsorted(end,'left'))
        if pos>=len(x5):
            return {**base,'filled':True,'entry_ts':entry_ts,'entry_px':entry_px,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'CENSORED','net_pnl_usd':np.nan}
        exit_ts=x5.index[pos]; exit_px=float(x5.iloc[pos].open); reason='TIME_EXIT_SESSION_END'
    else:
        exit_ts,exit_px,reason=solved
    ret=exit_px/entry_px-1.0
    return {**base,'filled':True,'entry_ts':entry_ts,'entry_px':entry_px,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'net_pnl_usd':ret*NOTIONAL-FEE}


def pf(vals):
    x=pd.Series(vals,dtype=float).dropna(); pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0:return float('inf')
    return pos/neg if neg>0 else np.nan


def summarize(g):
    f=g[g.filled.astype(bool)].copy(); x=pd.to_numeric(f.net_pnl_usd,errors='coerce').dropna()
    return {'setups':len(g),'fills':len(x),'fill_rate':len(x)/len(g) if len(g) else np.nan,
            'wins':int((x>0).sum()),'losses':int((x<=0).sum()),'wr':float((x>0).mean()) if len(x) else np.nan,
            'tp_rate':float((f.loc[x.index].exit_reason=='TP_PREV_HIGH').mean()) if len(x) else np.nan,
            'pf':pf(x),'net_exp':float(x.mean()) if len(x) else np.nan,'total_net':float(x.sum()) if len(x) else np.nan,
            'median_rr':float(g.nominal_rr.median()) if len(g) else np.nan}


def pct(x): return '-' if pd.isna(x) else f'{100*x:.1f}%'
def num(x):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.2f}'


def main():
    x5,coverage=b21.load5(); s=load_signals(); rows=[]
    for _,r in s.iterrows():
        for en in ENTRIES:
            for sn in STOPS:
                rows.append(simulate_one(x5,r,en,sn))
    t=pd.DataFrame(rows)
    # real-data mapping assertions
    assert set(t.k.unique())=={1,2}
    for r in t.itertuples(index=False):
        assert abs(r.entry_fraction-(0.75 if r.entry_name=='F75' else 0.80 if r.entry_name=='F80' else 0.85))<1e-12
        assert r.stop_fraction<r.entry_fraction
        if r.filled:
            assert pd.Timestamp(r.entry_ts)>=pd.Timestamp(r.signal_ts)
            assert r.stop_px<r.entry_px<r.target_px
    t.to_csv(OUT_TRADES,index=False)

    sums=[]
    for part in PARTS:
        for k in KS:
            for en in ENTRIES:
                for sn in STOPS:
                    g=t[(t.partition==part)&(t.k==k)&(t.entry_name==en)&(t.stop_name==sn)]
                    sums.append({'partition':part,'k':k,'entry_name':en,'stop_name':sn,**summarize(g)})
    sm=pd.DataFrame(sums)
    # screen only K1 exact pair across three historical major partitions
    major=('external','development','reference_validation')
    passes={}
    for en in ENTRIES:
        for sn in STOPS:
            z=sm[(sm.k==1)&(sm.entry_name==en)&(sm.stop_name==sn)&(sm.partition.isin(major))]
            passes[(en,sn)]=bool(len(z)==3 and (z.fills>=30).all() and (z.net_exp>0).all() and (z.pf>=1.20).all())
    sm['screen_pass']=[passes[(r.entry_name,r.stop_name)] if r.k==1 else False for r in sm.itertuples(index=False)]
    sm.to_csv(OUT_SUM,index=False)
    pd.DataFrame(t.exit_reason.value_counts(dropna=False)).to_csv(OUT_STATUS)

    md=['# B27U — London -> New York Shallow Entry + Local Range Stop — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** B27Q signal identity frozen; only entry/stop geometry changed.','',
        '## Primary K1 OPP0','',
        '| Partition | Entry | Stop | Fills | Fill rate | WR | TP rate | PF | Net exp | Total net | RR |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm[sm.k==1].itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_name} | {r.stop_name} | {r.fills} | {pct(r.fill_rate)} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {num(r.median_rr)} |')
    md+=['','## Screen','']
    good=[f'{en}/{sn}' for (en,sn),v in passes.items() if v]
    md.append('**PASS:** '+', '.join(good) if good else '**No K1 pair passed the frozen three-partition screen.**')
    md+=['','## Secondary K2 diagnostic','',
         '| Partition | Entry | Stop | Fills | WR | PF | Net exp | Total net |',
         '|---|---|---|---:|---:|---:|---:|---:|']
    for r in sm[sm.k==2].itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_name} | {r.stop_name} | {r.fills} | {pct(r.wr)} | {num(r.pf)} | ${num(r.net_exp)} | ${num(r.total_net)} |')
    md+=['','Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
