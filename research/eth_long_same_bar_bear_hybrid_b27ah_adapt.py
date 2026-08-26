#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
ACTR=ROOT/'ETH_LONG_F75_E10_PROFIT_LOCK_B27AC_ADAPT_Trades.csv'
REG=ROOT/'ETH_LONG_4H_REGIME_ALIGNMENT_B27AG_ADAPT_Detail.csv'
PFX='ETH_LONG_SAME_BAR_BEAR_HYBRID_B27AH_ADAPT'
OUT_MD=ROOT/f'{PFX}_Result.md';OUT_DETAIL=ROOT/f'{PFX}_Detail.csv';OUT_SUM=ROOT/f'{PFX}_Summary.csv';OUT_STATUS=ROOT/f'{PFX}_Status.txt'
MAJOR=('external','development','reference_validation');REGIMES=('ALL','BEAR','BULL','SIDEWAYS')

def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna();p=float(x[x>0].sum());n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def m(g,col):
    x=pd.to_numeric(g[col],errors='coerce').dropna();n=len(x)
    return {'n':n,'wr':float((x>0).mean()) if n else np.nan,'pf':float(pf(x)) if n else np.nan,'exp':float(x.mean()) if n else np.nan,'net':float(x.sum()) if n else 0.0}
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.2f}'

def main():
    a=pd.read_csv(ACTR);a=a[a.cohort=='SAME_BAR_REJECTION'].copy();a['signal_ts']=pd.to_datetime(a.signal_ts,utc=True)
    r=pd.read_csv(REG);r=r[r.source=='K1'].copy();r['signal_ts']=pd.to_datetime(r.signal_ts,utc=True)
    r=r[['partition','signal_ts','regime_at_signal','regime_available_ts']].drop_duplicates(['partition','signal_ts'])
    d=a.merge(r,on=['partition','signal_ts'],how='left',validate='many_to_one')
    if d.regime_at_signal.isna().any():raise AssertionError('missing regime join')
    if not (pd.to_datetime(d.regime_available_ts,utc=True)<=d.signal_ts).all():raise AssertionError('future regime join')
    d.to_csv(OUT_DETAIL,index=False)

    rows=[]
    pooled=d[d.partition.isin(MAJOR)].copy()
    for reg in REGIMES:
        g=pooled if reg=='ALL' else pooled[pooled.regime_at_signal==reg]
        fx=m(g,'fixed_net_pnl_usd');hy=m(g,'hybrid_net_pnl_usd')
        rows.append({'scope':'POOLED_MAJOR','regime':reg,'n':fx['n'],'fixed_wr':fx['wr'],'fixed_pf':fx['pf'],'fixed_exp':fx['exp'],'fixed_net':fx['net'],'hybrid_wr':hy['wr'],'hybrid_pf':hy['pf'],'hybrid_exp':hy['exp'],'hybrid_net':hy['net']})
    for part in MAJOR:
        g=d[(d.partition==part)&(d.regime_at_signal=='BEAR')]
        fx=m(g,'fixed_net_pnl_usd');hy=m(g,'hybrid_net_pnl_usd')
        rows.append({'scope':part,'regime':'BEAR','n':fx['n'],'fixed_wr':fx['wr'],'fixed_pf':fx['pf'],'fixed_exp':fx['exp'],'fixed_net':fx['net'],'hybrid_wr':hy['wr'],'hybrid_pf':hy['pf'],'hybrid_exp':hy['exp'],'hybrid_net':hy['net']})
    sm=pd.DataFrame(rows);sm.to_csv(OUT_SUM,index=False)
    p=sm[sm.scope=='POOLED_MAJOR'].set_index('regime');allr=p.loc['ALL'];bear=p.loc['BEAR']
    observed=bool(bear['n']>0 and bear.fixed_exp>allr.fixed_exp and bear.fixed_pf>allr.fixed_pf and bear.hybrid_exp>allr.hybrid_exp and bear.hybrid_pf>allr.hybrid_pf)
    status='ETH_LONG_B27AH_ADAPT_BEAR_CONCENTRATION_OBSERVED' if observed else 'ETH_LONG_B27AH_ADAPT_BEAR_CONCENTRATION_NOT_OBSERVED';OUT_STATUS.write_text(status+'\n')
    md=['# ETH LONG B27AH-Adapt — SAME_BAR_REJECTION + 4H BEAR Attribution — Result','',
        'Exact B27AA SAME_BAR entries, B27AC fixed/hybrid economics, and B27AG causal signal-time regime labels are reused without re-detection.','',
        '| Scope | Regime | N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid net |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for z in sm.itertuples(index=False):md.append(f'| {z.scope} | {z.regime} | {z.n} | {pct(z.fixed_wr)} | {num(z.fixed_pf)} | ${num(z.fixed_exp)} | ${num(z.fixed_net)} | {pct(z.hybrid_wr)} | {num(z.hybrid_pf)} | ${num(z.hybrid_exp)} | ${num(z.hybrid_net)} |')
    md += ['',f'**Status: {status}**','', 'BEAR was selected after B27AG and this is therefore historical attribution only, not independent validation or a live filter.']
    OUT_MD.write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
