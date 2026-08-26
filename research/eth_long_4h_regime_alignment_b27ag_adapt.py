#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT=Path(__file__).resolve().parent.parent
QSIG=ROOT/'ETH_LONG_SESSION_LIQUIDITY_PRESSURE_B27Q_ADAPT_Signals.csv'
YPATH=ROOT/'ETH_LONG_F75_POST_H2_EXTENSION_B27Y_ADAPT_Paths.csv'
ACTR=ROOT/'ETH_LONG_F75_E10_PROFIT_LOCK_B27AC_ADAPT_Trades.csv'
PFX='ETH_LONG_4H_REGIME_ALIGNMENT_B27AG_ADAPT'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_STATE=ROOT/f'{PFX}_4HStates.csv'; OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
PARTS=('external','development','reference_validation','august'); MAJOR=('external','development','reference_validation'); REGIMES=('BULL','BEAR','SIDEWAYS')


def ema(c,p):
    c=np.asarray(c,dtype=float); e=np.zeros(len(c),dtype=float)
    if not len(c):return e
    e[0]=c[0]; k=2.0/(p+1)
    for i in range(1,len(c)):e[i]=c[i]*k+e[i-1]*(1-k)
    return e

def atr(H,L,C,p=14):
    H=np.asarray(H,float);L=np.asarray(L,float);C=np.asarray(C,float);a=np.zeros(len(H),dtype=float)
    for i in range(1,len(H)):
        t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]));a[i]=a[i-1]+(t-a[i-1])/min(i,p)
    return a

class SwingRegime:
    def __init__(self,slb=5,sa=.5):
        self.slb=slb;self.sa=sa;self.hh=0;self.hl=0;self.lh=0;self.ll=0;self.lsh=None;self.lsl=None;self.psh=None;self.psl=None
    def process(self,i,H,L,C,ef,es,at):
        if i<self.slb:return 'SIDEWAYS'
        mid=i-self.slb//2
        if mid<0:return 'SIDEWAYS'
        wh=H[max(0,i-self.slb):i+1];wl=L[max(0,i-self.slb):i+1];am=self.sa*at[i] if at[i]>0 else 0
        if H[mid]==max(wh) and(self.lsh is None or abs(H[mid]-self.lsh)>=am):
            self.psh=self.lsh;self.lsh=float(H[mid])
            if self.psh:
                if self.lsh>self.psh:self.hh+=1
                else:self.lh+=1;self.hh=max(0,self.hh-1)
        if L[mid]==min(wl) and(self.lsl is None or abs(L[mid]-self.lsl)>=am):
            self.psl=self.lsl;self.lsl=float(L[mid])
            if self.psl:
                if self.lsl>self.psl:self.hl+=1;self.ll=max(0,self.ll-1)
                else:self.ll+=1;self.hl=max(0,self.hl-1)
        if self.hh>=2 and self.hl>=2 and ef[i]>es[i] and C[i]>es[i]:return 'BULL'
        if self.lh>=2 and self.ll>=2 and ef[i]<es[i] and C[i]<es[i]:return 'BEAR'
        return 'SIDEWAYS'

def build_4h(x5):
    z=x5[['open','high','low','close']].copy();z['bucket']=z.index.floor('4h')
    g=z.groupby('bucket',sort=True)
    cnt=g.size(); o=g.open.first(); h=g.high.max(); l=g.low.min(); c=g.close.last()
    d=pd.DataFrame({'open':o,'high':h,'low':l,'close':c,'bars':cnt})
    d=d[d.bars==48].copy()
    H=d.high.to_numpy(float);L=d.low.to_numpy(float);C=d.close.to_numpy(float);ef=ema(C,7);es=ema(C,20);at=atr(H,L,C,14)
    det=SwingRegime(5,.5); states=[]
    for i in range(len(d)):states.append(det.process(i,H,L,C,ef,es,at))
    d['ema7']=ef;d['ema20']=es;d['atr14']=at;d['regime']=states;d['available_ts']=d.index+pd.Timedelta(hours=4)
    return d

def attach_regime(df,state,signal_col='signal_ts'):
    q=df.copy();q[signal_col]=pd.to_datetime(q[signal_col],utc=True)
    av=pd.DatetimeIndex(state.available_ts); pos=av.searchsorted(pd.DatetimeIndex(q[signal_col]),side='right')-1
    if (pos<0).any():raise AssertionError('signal precedes first 4H state')
    q['regime_at_signal']=state.regime.to_numpy()[pos]
    q['regime_bar_start']=state.index.to_numpy()[pos]
    q['regime_available_ts']=state.available_ts.to_numpy()[pos]
    if not (pd.to_datetime(q.regime_available_ts,utc=True)<=q[signal_col]).all():raise AssertionError('future regime leakage')
    return q

def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna();p=float(x[x>0].sum());n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def econ(g,col):
    x=pd.to_numeric(g[col],errors='coerce').dropna();n=len(x)
    return {'n':n,'wr':float((x>0).mean()) if n else np.nan,'pf':float(pf(x)) if n else np.nan,'exp':float(x.mean()) if n else np.nan,'net':float(x.sum()) if n else 0.0}
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.2f}'

def main():
    x5,cov=ethdata.load5(); state=build_4h(x5);state.to_csv(OUT_STATE)
    q=pd.read_csv(QSIG);q=q[(q.transition=='LONDON_TO_NEWYORK')&(q.side=='LONG')&(q.k==1)&(q.opp_visits_at_signal==0)].copy();q=attach_regime(q,state)
    y=pd.read_csv(YPATH);y=attach_regime(y,state)
    y['has_h2']=y.has_h2.astype(str).str.lower()=='true';y['E10_high_reach']=y.E10_high_reach.astype(str).str.lower()=='true'
    a=pd.read_csv(ACTR);a=a[a.cohort=='EARLY_RECLAIM'].copy();a=attach_regime(a,state)

    # identity/regime details persisted together for audit
    detail=[]
    for source,df in [('K1',q),('F75_PATH',y),('EARLY_RECLAIM',a)]:
        t=df[['partition','date_utc','signal_ts','regime_at_signal','regime_bar_start','regime_available_ts']].copy();t['source']=source;detail.append(t)
    pd.concat(detail,ignore_index=True).to_csv(OUT_DETAIL,index=False)

    rows=[]
    groups=[*PARTS,'POOLED_MAJOR']
    for part in groups:
        qg=q[q.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else q[q.partition==part]
        yg=y[y.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else y[y.partition==part]
        ag=a[a.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else a[a.partition==part]
        for reg in REGIMES:
            qr=qg[qg.regime_at_signal==reg];yr=yg[yg.regime_at_signal==reg];ar=ag[ag.regime_at_signal==reg]
            h=yr[yr.has_h2]
            fx=econ(ar,'fixed_net_pnl_usd');hy=econ(ar,'hybrid_net_pnl_usd')
            rows.append({'partition':part,'regime':reg,'k1_n':len(qr),'target_break_rate':float((qr.structural_outcome=='TARGET_BREAK').mean()) if len(qr) else np.nan,
                         'f75_fills':len(yr),'h2_n':int(yr.has_h2.sum()),'h2_rate':float(yr.has_h2.mean()) if len(yr) else np.nan,
                         'e10_reach_n':int(h.E10_high_reach.sum()) if len(h) else 0,'e10_reach_given_h2':float(h.E10_high_reach.mean()) if len(h) else np.nan,
                         'fixed_n':fx['n'],'fixed_wr':fx['wr'],'fixed_pf':fx['pf'],'fixed_exp':fx['exp'],'fixed_net':fx['net'],
                         'hybrid_wr':hy['wr'],'hybrid_pf':hy['pf'],'hybrid_exp':hy['exp'],'hybrid_net':hy['net']})
    sm=pd.DataFrame(rows);sm.to_csv(OUT_SUM,index=False)
    p=sm[sm.partition=='POOLED_MAJOR'].set_index('regime')
    enough=('BULL' in p.index and 'BEAR' in p.index and p.loc['BULL','f75_fills']>0 and p.loc['BEAR','f75_fills']>0)
    supported=bool(enough and p.loc['BULL','h2_rate']>p.loc['BEAR','h2_rate'] and p.loc['BULL','e10_reach_given_h2']>p.loc['BEAR','e10_reach_given_h2'] and p.loc['BULL','fixed_exp']>p.loc['BEAR','fixed_exp'])
    status='ETH_LONG_B27AG_ADAPT_REGIME_ALIGNMENT_DIRECTIONALLY_SUPPORTED' if supported else 'ETH_LONG_B27AG_ADAPT_REGIME_ALIGNMENT_NOT_DIRECTIONALLY_SUPPORTED'
    OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27AG-Adapt — 4H HH/HL Regime Alignment Audit — Result','',f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**; complete 4H bars: **{len(state):,}**.','',
        'The repository SwingRegime defaults are reproduced causally. Regime is attached at K1 signal time using only the latest completed 4H bar. No trade is filtered.','',
        '| Partition | Regime | K1 N | Target break | F75 fills | H2 | H2 rate | E10/H2 | ER N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Hybrid PF | Hybrid exp | Hybrid net |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.regime} | {r.k1_n} | {pct(r.target_break_rate)} | {r.f75_fills} | {r.h2_n} | {pct(r.h2_rate)} | {pct(r.e10_reach_given_h2)} | {r.fixed_n} | {pct(r.fixed_wr)} | {num(r.fixed_pf)} | ${num(r.fixed_exp)} | ${num(r.fixed_net)} | {num(r.hybrid_pf)} | ${num(r.hybrid_exp)} | ${num(r.hybrid_net)} |')
    md += ['','## Frozen directional-support readout','']
    if enough:
        md += [f'- BULL vs BEAR F75 H2 rate: {pct(p.loc["BULL","h2_rate"])} vs {pct(p.loc["BEAR","h2_rate"])}.',
               f'- BULL vs BEAR E10 reach given H2: {pct(p.loc["BULL","e10_reach_given_h2"])} vs {pct(p.loc["BEAR","e10_reach_given_h2"])}.',
               f'- BULL vs BEAR EARLY_RECLAIM fixed expectancy: ${num(p.loc["BULL","fixed_exp"])} vs ${num(p.loc["BEAR","fixed_exp"])}.']
    md += ['',f'**Status: {status}**','', 'Attribution only; this does not authorize a regime filter. Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
