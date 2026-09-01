#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S7C_PATH=HERE/'eth_b27dx_s7c_single_bar_k1_rejection.py'
spec=importlib.util.spec_from_file_location('eth_s7c',S7C_PATH); s7c=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s7c)
s7a=s7c.s7a

PFX='ETH_B27DX_S7D_EVENT_QUALITY_CONJUNCTION'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS; PARTS=s7a.PARTS; BTC_WR=s7a.BTC_WR; BTC_PF=s7a.BTC_PF; BTC_EXP=s7a.BTC_EXP
FILTERS=('A__B','A__C','A__B__C'); ORDER={v:i for i,v in enumerate(FILTERS)}

def cl(v):return s7a.cl(int(v))
def mask(g,name):
    a=g.single_bar_k1_rejection.astype(bool)
    b=g.fill_elapsed_min<=s7a.HALF_EXEC
    c=g.range_completion_elapsed_min>=s7a.HALF_REF
    if name=='A__B':return a&b
    if name=='A__C':return a&c
    if name=='A__B__C':return a&b&c
    raise ValueError(name)
def complexity(name):return name.count('__')+1

def score(c):
    rows=[]
    for ex in CLOCKS:
        for p in PARTS:
            raw=c[(c.exec_min==ex)&(c.partition==p)].copy()
            bm=s7a.s4.metrics(raw,'pnl_0');rows.append({'exec_min':ex,'execution_utc':cl(ex),'filter':'BASE','partition':p,'raw_n':len(raw),'n':len(raw),'retention':1.0,**bm})
            for f in FILTERS:
                q=raw[mask(raw,f)].copy();m=s7a.s4.metrics(q,'pnl_0')
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'filter':f,'partition':p,'raw_n':len(raw),'n':len(q),'retention':len(q)/len(raw) if len(raw) else np.nan,**m})
    return pd.DataFrame(rows)
def choose(s):
    rows=[]
    for ex in CLOCKS:
        d=s[(s.exec_min==ex)&(s.partition=='development')&(s['filter'].isin(FILTERS))].copy()
        d['promotable']=(d.n>=20)&(d.retention>=.40)&(d.wr>=.75)&(d.pf>=1.50)&(d.expectancy>=.80)&(d.net>0)
        q=d[d.promotable].copy()
        if q.empty:
            rows.append({'exec_min':ex,'execution_utc':cl(ex),'selected_filter':'','dev_promoted':False,'replicated':False});continue
        q['complexity']=q['filter'].map(complexity);q['order']=q['filter'].map(ORDER);q=q.sort_values(['complexity','retention','order'],ascending=[True,False,True]);r=q.iloc[0]
        row={'exec_min':ex,'execution_utc':cl(ex),'selected_filter':r['filter'],'dev_promoted':True,'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,'dev_expectancy':r.expectancy,'dev_net':r.net}
        oks=[]
        for p in ('external','reference_validation'):
            z=s[(s.exec_min==ex)&(s.partition==p)&(s['filter']==r['filter'])].iloc[0]
            ok=bool(z.n>=10 and z.retention>=.30 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
            for k in ('n','retention','wr','pf','expectancy','net'):row[f'{p}_{k}']=z[k]
            row[f'{p}_pass']=ok
        row['replicated']=all(oks);rows.append(row)
    return pd.DataFrame(rows)
def lock_selected(c,sel,pnl_col):
    pieces=[]
    for r in sel[sel.replicated].itertuples(index=False):
        q=c[c.exec_min==r.exec_min].copy();q=q[mask(q,r.selected_filter)].copy();q['selected_filter']=r.selected_filter;pieces.append(q)
    if not pieces:return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pieces,ignore_index=True);decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,pnl_col)
        rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,pnl_col)
    rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m});return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s7a.s4.b.m.m.load5();base,audit=s7a.feature_candidates(x);c,af=s7c.attach_episode(base,x);c.to_csv(OUT_CAND,index=False)
    causal=bool(audit.feature_known_by_entry.all() and af.episode_known_by_entry.all()) if len(c) else False
    s=score(c);s.to_csv(OUT_SUM,index=False);sel=choose(s);sel.to_csv(OUT_SEL,index=False)
    d0,p0=lock_selected(c,sel,'pnl_0');d5,p5=lock_selected(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    if len(p0):
        a=p0.copy();a['stress_bps']=0;b=p5.copy();b['stress_bps']=5;ports=pd.concat([a,b],ignore_index=True)
    else:ports=pd.DataFrame()
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False
    if not causal:status='ETH_S7D_CAUSAL_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7D_NO_DEV_CONJUNCTION'
    elif nrep==0:status='ETH_S7D_DEV_CONJUNCTIONS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)];majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1)
        btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress);status='ETH_S7D_CONJUNCTION_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7D_CONJUNCTIONS_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7D Event-Quality Conjunction — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Causal audit: **{"PASS" if causal else "FAIL"}**.','- A = single-bar K1 rejection; B = fill first-half; C = range completed second-half. No new cutoff was introduced.','',
           '## Development conjunction screen','', '| Clock | Filter | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        for f in FILTERS:
            r=s[(s.exec_min==ex)&(s.partition=='development')&(s['filter']==f)].iloc[0];prom=bool(r.n>=20 and r.retention>=.40 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
            lines.append(f'| {r.execution_utc} | {f} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if prom else "NO"} |')
    lines += ['','## Frozen Development selection / replication','', '| Clock | Selected | External | RefVal | Replicated |','|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | - | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | {r.selected_filter} | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-selected conjunction replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No new cutoff, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
