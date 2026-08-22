#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT=Path(__file__).resolve().parent.parent
TRADES=ROOT/'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Trades.csv'
OUT=ROOT/'BTC_4H_SWING_ZONE_TEKTOK_FORENSICS_B27D_Result.md'
OUTCSV=ROOT/'BTC_4H_SWING_ZONE_TEKTOK_FORENSICS_B27D_Trades.csv'
ZONES=(0.10,0.20,0.30)


def pf(v):
    s=pd.Series(v,dtype=float).dropna(); p=float(s[s>0].sum()); n=float(-s[s<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def summ(g):
    if len(g)==0:return (0,0,0,np.nan,np.nan,np.nan,np.nan)
    v=pd.to_numeric(g.net_pnl_usd,errors='coerce').dropna(); n=len(v); w=int((v>0).sum())
    return n,w,n-w,w/n,pf(v),float(v.mean()),float(v.sum())

def pct(x):return '-' if pd.isna(x) else f'{100*x:.2f}%'
def num(x,d=2):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.{d}f}'


def main():
    x5,cov=b21.load5(); z=b22b.resample_ohlc(x5,'4h').copy(); idx=z.index
    H=z.high.to_numpy(float); L=z.low.to_numpy(float); C=z.close.to_numpy(float)
    sh=np.zeros(len(z),bool); sl=np.zeros(len(z),bool)
    for k in range(1,len(z)-1):
        sh[k]=H[k]>H[k-1] and H[k]>H[k+1]
        sl[k]=L[k]<L[k-1] and L[k]<L[k+1]

    t=pd.read_csv(TRADES)
    for c in ['signal_ts','entry_ts','exit_ts']:t[c]=pd.to_datetime(t[c],utc=True,errors='coerce')
    t=t[(t.timeframe=='4h')&(t.rr=='R2')&(t.resolved.astype(str).str.lower().isin(['true','1']))].copy()

    rows=[]
    for q in t.itertuples(index=False):
        s=int(idx.searchsorted(q.signal_ts,'left'))
        if s<4 or s>=len(z):continue
        # Latest causal swing high/low known before signal starts.
        kh=kl=None
        for k in range(1,s-1):
            if k+2>=len(idx) or idx[k+2]>q.signal_ts:break
            if sh[k]:kh=k
            if sl[k]:kl=k
        if kh is None or kl is None:continue
        top=float(H[kh]); bot=float(L[kl]); width=top-bot
        if width<=0:continue
        true_break=(q.side=='LONG' and C[s]>top) or (q.side=='SHORT' and C[s]<bot)
        if not true_break:continue
        known=max(idx[kh+2],idx[kl+2]); a=int(idx.searchsorted(known,'left'))
        base={'partition':q.partition,'side':q.side,'signal_ts':q.signal_ts,'net_pnl_usd':float(q.net_pnl_usd),
              'swing_high':top,'swing_low':bot,'range_pct':width/((top+bot)/2)}
        for frac in ZONES:
            seq=[]; upper_bars=lower_bars=both=0
            upper_cut=top-frac*width; lower_cut=bot+frac*width
            for j in range(a,s):
                up=H[j]>=upper_cut and C[j]<=top
                dn=L[j]<=lower_cut and C[j]>=bot
                if up and dn: both+=1; continue
                if up: upper_bars+=1; side='H'
                elif dn: lower_bars+=1; side='L'
                else: continue
                if not seq or seq[-1]!=side:seq.append(side)
            visits=len(seq); switches=max(0,visits-1)
            rows.append({**base,'zone_frac':frac,'upper_zone_bars':upper_bars,'lower_zone_bars':lower_bars,
                         'both_zone_bars':both,'zone_visits':visits,'side_switches':switches,'visit_sequence':'-'.join(seq)})
    d=pd.DataFrame(rows); d.to_csv(OUTCSV,index=False)
    d['switch_bucket']=pd.cut(d.side_switches,[-1,0,1,2,3,10**9],labels=['0','1','2','3','4+'])

    md=['# B27D — 4H Swing-Zone “Tektok” Before Breakout','',f'Source coverage: **{cov:.4%}**. Frozen B27A 4H R2 outcomes; no trade rule changed.','',
        'For each true breakout of the latest causally-known swing range, define top/bottom zones as 10%, 20%, or 30% of range width. Consecutive candles in the same zone count as one visit. `side_switches` is the number of H→L or L→H transitions before the breakout candle.','']

    md += ['## Typical tektok count by zone width','', '| Partition | Zone | N | Median visits | Median side switches | P75 switches | Share with >=1 switch | Share with >=2 switches |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for part in ['external','development','reference_validation','august']:
        for f in ZONES:
            g=d[(d.partition==part)&(d.zone_frac==f)]
            n=len(g)
            md.append(f'| {part} | {int(f*100)}% | {n} | {num(g.zone_visits.median() if n else np.nan,1)} | {num(g.side_switches.median() if n else np.nan,1)} | {num(g.side_switches.quantile(.75) if n else np.nan,1)} | {pct(float((g.side_switches>=1).mean()) if n else np.nan)} | {pct(float((g.side_switches>=2).mean()) if n else np.nan)} |')

    md += ['','## 20% zone: trade result by tektok side-switch count','', '| Partition | Switches | N | W | L | WR | Net PF | Net exp/trade | Total net |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    x=d[d.zone_frac==0.20]
    for part in ['external','development','reference_validation','august']:
        for b in ['0','1','2','3','4+']:
            g=x[(x.partition==part)&(x.switch_bucket.astype(str)==b)]
            n,w,l,wr,p,e,tot=summ(g)
            md.append(f'| {part} | {b} | {n} | {w} | {l} | {pct(wr)} | {num(p)} | ${num(e)} | ${num(tot)} |')

    md += ['','## Validation 20% zone sequences','', '| Sequence | N | W | L | WR | Net PF | Total net |','|---|---:|---:|---:|---:|---:|---:|']
    v=x[x.partition=='reference_validation']
    for seq,g in v.groupby('visit_sequence',dropna=False):
        n,w,l,wr,p,e,tot=summ(g)
        md.append(f'| {seq if seq else "none"} | {n} | {w} | {l} | {pct(wr)} | {num(p)} | ${num(tot)} |')

    md += ['','Forensic only. Any subgroup is hindsight-discovered and is not a validated entry filter until a new preregistered test.','','Research only; live BBC unchanged.']
    OUT.write_text('\n'.join(md)+'\n')

if __name__=='__main__':main()
