#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import eth_f85_long_exact_transplant_e1 as ethdata

ROOT=Path(__file__).resolve().parent.parent
ENTRIES=ROOT/'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Entries.csv'
WINDOWS=ROOT/'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX='ETH_LONG_F75_EARLY_RECLAIM_B27AA_ADAPT'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_TRADES=ROOT/f'{PFX}_Trades.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
BAR5=pd.Timedelta(minutes=5); PARTS=('external','development','reference_validation','august'); MAJOR=('external','development','reference_validation')
VARIANTS=('EARLY_RECLAIM','SAME_BAR_REJECTION'); ENTRY_F=.75; STOP_F=.15; TARGET_EXT=.10; NOTIONAL=500.; FEE=.40

def fs(x,a,b):
    i=int(x.index.searchsorted(a,side='left')); j=int(x.index.searchsorted(b,side='left')); return x.iloc[i:j]

def load_source():
    e=pd.read_csv(ENTRIES); e=e[(e.entry_name=='F75')&(e.filled.astype(str).str.lower()=='true')].copy()
    for c in ('signal_ts','entry_ts','h2_bar_start'): e[c]=pd.to_datetime(e[c],utc=True,errors='coerce')
    w=pd.read_csv(WINDOWS)
    for c in ('signal_ts','session_end','h2_bar_start'): w[c]=pd.to_datetime(w[c],utc=True,errors='coerce')
    z=e.merge(w[['partition','date_utc','signal_ts','session_end','h2_bar_start']],on=['partition','date_utc','signal_ts'],how='left',suffixes=('_entry','_window'),validate='many_to_one')
    a=pd.to_datetime(z.h2_bar_start_entry,utc=True,errors='coerce'); b=pd.to_datetime(z.h2_bar_start_window,utc=True,errors='coerce')
    if not bool(((a.isna()&b.isna())|(a==b)).all()): raise AssertionError('H2 identity mismatch')
    z['h2_bar_start']=b
    if z.session_end.isna().any() or z.duplicated(['partition','date_utc','signal_ts']).any(): raise AssertionError('source identity failure')
    return z.sort_values(['partition','entry_ts']).reset_index(drop=True)

def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); p=float(x[x>0].sum()); n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def run_one(x5,r,variant):
    H=float(r.H); L=float(r.L); R=H-L; f75=L+ENTRY_F*R; boundary=L+STOP_F*R; target=H+TARGET_EXT*R
    touch=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end); frozen_h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    q=fs(x5,touch,end)
    if q.empty or q.index[0]!=touch or not(float(q.iloc[0].low)<=f75<=float(q.iloc[0].high)): raise AssertionError('touch identity')
    conf_bar=pd.NaT; conf_kind=''; status='NO_CONFIRMATION'; maxk=1 if variant=='SAME_BAR_REJECTION' else len(q)
    for k in range(maxk):
        ts=q.index[k]; b=q.iloc[k]; hi=float(b.high); cl=float(b.close)
        if hi>=H: status='H2_BEFORE_CONFIRMATION'; break
        if cl<L: status='LOW_BREAK_BEFORE_CONFIRMATION'; break
        if cl>f75: conf_bar=ts; conf_kind='SAME_BAR' if k==0 else 'LATER_RECLAIM'; status='CONFIRMED'; break
    base={'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,'variant':variant,'H':H,'L':L,'range':R,'F75':f75,'F15':boundary,'E10':target,'touch_bar_start':touch,'frozen_h2_bar_start':frozen_h2,'confirmation_status':status,'confirmation_kind':conf_kind}
    if status!='CONFIRMED': return {**base,'entry_executed':False,'entry_ts':pd.NaT,'entry_px':np.nan,'entry_fraction':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':status,'net_pnl_usd':np.nan,'hold_minutes':np.nan,'h2_before_exit':False}
    if pd.notna(frozen_h2) and not(conf_bar<frozen_h2): raise AssertionError('confirmation not pre-H2')
    entry_ts=conf_bar+BAR5
    if entry_ts>=end: return {**base,'entry_executed':False,'entry_ts':entry_ts,'entry_px':np.nan,'entry_fraction':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_NEXT_BAR','net_pnl_usd':np.nan,'hold_minutes':np.nan,'h2_before_exit':False}
    pos=int(x5.index.searchsorted(entry_ts,side='left'))
    if pos>=len(x5) or x5.index[pos]!=entry_ts: raise AssertionError('missing entry bar')
    entry=float(x5.iloc[pos].open); ef=(entry-L)/R
    if entry>=H: return {**base,'entry_executed':False,'entry_ts':entry_ts,'entry_px':entry,'entry_fraction':ef,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'MISSED_H2_AT_OPEN','net_pnl_usd':np.nan,'hold_minutes':np.nan,'h2_before_exit':False}
    if not(boundary<entry<H): return {**base,'entry_executed':False,'entry_ts':entry_ts,'entry_px':entry,'entry_fraction':ef,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'INVALID_ENTRY_GEOMETRY','net_pnl_usd':np.nan,'hold_minutes':np.nan,'h2_before_exit':False}
    if pd.notna(frozen_h2) and frozen_h2<entry_ts: raise AssertionError('entry after H2')
    eq=fs(x5,entry_ts,end); reason=None; exit_ts=pd.NaT; exit_px=np.nan; h2_seen=False
    for ts,b in eq.iterrows():
        hi=float(b.high); cl=float(b.close)
        if hi>=H: h2_seen=True
        if hi>=target: exit_ts=ts; exit_px=target; reason='TP_E10'; break
        if cl<boundary: exit_ts=ts+BAR5; exit_px=cl; reason='CLOSE_INVALIDATION_F15'; break
    if reason is None:
        p=int(x5.index.searchsorted(end,side='left'))
        if p>=len(x5) or x5.index[p]!=end: raise AssertionError('missing time exit')
        exit_ts=end; exit_px=float(x5.iloc[p].open); reason='TIME_EXIT_SESSION_END'
    net=(exit_px/entry-1.)*NOTIONAL-FEE
    return {**base,'confirmation_bar_start':conf_bar,'confirmation_ts':conf_bar+BAR5,'entry_executed':True,'entry_ts':entry_ts,'entry_px':entry,'entry_fraction':ef,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'net_pnl_usd':net,'hold_minutes':float((exit_ts-entry_ts)/pd.Timedelta(minutes=1)),'h2_before_exit':h2_seen}

def metrics(g,opps):
    ex=g[g.entry_executed.astype(bool)].copy(); n=len(ex)
    if not n:return {'opportunities':opps,'executed':0,'execution_rate':0.,'same_bar':0,'later':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.,'tp_rate':np.nan,'median_entry_fraction':np.nan,'median_hold':np.nan}
    p=ex.net_pnl_usd.astype(float)
    return {'opportunities':opps,'executed':n,'execution_rate':n/opps if opps else np.nan,'same_bar':int((ex.confirmation_kind=='SAME_BAR').sum()),'later':int((ex.confirmation_kind=='LATER_RECLAIM').sum()),'wr':float((p>0).mean()),'pf':float(pf(p)),'expectancy':float(p.mean()),'net':float(p.sum()),'tp_rate':float((ex.exit_reason=='TP_E10').mean()),'median_entry_fraction':float(ex.entry_fraction.median()),'median_hold':float(ex.hold_minutes.median())}
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.2f}'

def main():
    x5,cov=ethdata.load5(); src=load_source(); rows=[]
    for r in src.itertuples(index=False):
        for v in VARIANTS: rows.append(run_one(x5,r,v))
    d=pd.DataFrame(rows); d.to_csv(OUT_TRADES,index=False)
    sums=[]
    for part in PARTS:
        opp=int((src.partition==part).sum())
        for v in VARIANTS: sums.append({'partition':part,'variant':v,**metrics(d[(d.partition==part)&(d.variant==v)],opp)})
    sm=pd.DataFrame(sums); sm.to_csv(OUT_SUM,index=False)
    er=sm[(sm.variant=='EARLY_RECLAIM')&sm.partition.isin(MAJOR)]
    passed=bool(len(er)==3 and (er.executed>=30).all() and (er.wr>=.70).all() and (er.pf>=1.20).all() and (er.expectancy>0).all())
    status='ETH_LONG_B27AA_ADAPT_EARLY_RECLAIM_SCREEN_PASS' if passed else 'ETH_LONG_B27AA_ADAPT_EARLY_RECLAIM_NOT_SUPPORTED'; OUT_STATUS.write_text(status+'\n')
    md=['# ETH LONG B27AA-Adapt — Early F75 Rejection / Reclaim — Result','',f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**; frozen F75 opportunities: **{len(src)}**.','', 'Frozen economics: E10 target + D60/F15 completed-close invalidation.','', '| Partition | Variant | Opps | Executed | Exec rate | Same-bar | Later | WR | PF | Exp | Net | TP rate | Median entry f | Median hold |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False): md.append(f'| {r.partition} | {r.variant} | {r.opportunities} | {r.executed} | {pct(r.execution_rate)} | {r.same_bar} | {r.later} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.net)} | {pct(r.tp_rate)} | {num(r.median_entry_fraction)} | {num(r.median_hold)} |')
    md += ['',f'**Status: {status}**','', 'SAME_BAR_REJECTION is diagnostic only. Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
