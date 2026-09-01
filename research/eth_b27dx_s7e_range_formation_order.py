#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
S7A_PATH=HERE/'eth_b27dx_s7a_event_quality_filter.py'
spec=importlib.util.spec_from_file_location('eth_s7a',S7A_PATH);s7a=importlib.util.module_from_spec(spec)
assert spec.loader is not None;spec.loader.exec_module(s7a)

PFX='ETH_B27DX_S7E_RANGE_FORMATION_ORDER'
OUT_MD=ROOT/f'{PFX}_Result.md';OUT_CAND=ROOT/f'{PFX}_Candidates.csv';OUT_SUM=ROOT/f'{PFX}_Summary.csv';OUT_SEL=ROOT/f'{PFX}_Selections.csv';OUT_DEC=ROOT/f'{PFX}_Decisions.csv';OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv';OUT_AUDIT=ROOT/f'{PFX}_Audit.csv';OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS;PARTS=s7a.PARTS;BTC_WR=s7a.BTC_WR;BTC_PF=s7a.BTC_PF;BTC_EXP=s7a.BTC_EXP
VARIANTS=('BASE','LOW_BEFORE_HIGH','HIGH_BEFORE_LOW','SAME_BAR_EXTREMES')

def cl(v):return s7a.cl(int(v))
def enrich(x):
    c,base_audit=s7a.feature_candidates(x);rows=[];aud=[]
    for r in c.itertuples(index=False):
        ref=s7a.fast_slice(x,pd.Timestamp(r.reference_start),pd.Timestamp(r.execution_start))
        H=float(ref.high.max());L=float(ref.low.min())
        hts=s7a.first_extreme_ts(ref,'high',H);lts=s7a.first_extreme_ts(ref,'low',L)
        h_ok=abs(H-float(r.H))<=1e-9*max(1.,abs(H));l_ok=abs(L-float(r.L))<=1e-9*max(1.,abs(L));causal=(hts<pd.Timestamp(r.execution_start) and lts<pd.Timestamp(r.execution_start))
        if lts<hts:order='LOW_BEFORE_HIGH'
        elif hts<lts:order='HIGH_BEFORE_LOW'
        else:order='SAME_BAR_EXTREMES'
        d=r._asdict();d.update({'high_formation_ts':hts,'low_formation_ts':lts,'range_order':order});rows.append(d)
        aud.append({'partition':r.partition,'clock':r.execution_utc,'execution_start':r.execution_start,'H_parity':h_ok,'L_parity':l_ok,'extremes_pre_execution':causal,'pass':h_ok and l_ok and causal})
    q=pd.DataFrame(rows)
    for col in ('reference_start','execution_start','entry_bar_start','exit_ts','range_completion_ts','k1_ts','high_formation_ts','low_formation_ts'):
        if col in q:q[col]=pd.to_datetime(q[col],utc=True)
    return q,pd.DataFrame(aud)
def mask(g,v):
    if v=='BASE':return pd.Series(True,index=g.index)
    return g.range_order.eq(v)
def score(c):
    rows=[]
    for ex in CLOCKS:
        for v in VARIANTS:
            for p in PARTS:
                raw=c[(c.exec_min==ex)&(c.partition==p)].copy();q=raw[mask(raw,v)].copy();m=s7a.s4.metrics(q,'pnl_0');rows.append({'exec_min':ex,'execution_utc':cl(ex),'variant':v,'partition':p,'raw_n':len(raw),'n':len(q),'retention':len(q)/len(raw) if len(raw) else np.nan,**m})
    return pd.DataFrame(rows)
def choose(s):
    rows=[]
    for ex in CLOCKS:
        r=s[(s.exec_min==ex)&(s.partition=='development')&(s.variant=='LOW_BEFORE_HIGH')].iloc[0]
        prom=bool(r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
        row={'exec_min':ex,'execution_utc':cl(ex),'dev_promoted':prom,'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,'dev_expectancy':r.expectancy,'dev_net':r.net,'replicated':False}
        if prom:
            oks=[]
            for p in ('external','reference_validation'):
                z=s[(s.exec_min==ex)&(s.partition==p)&(s.variant=='LOW_BEFORE_HIGH')].iloc[0];ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
                for k in ('n','retention','wr','pf','expectancy','net'):row[f'{p}_{k}']=z[k]
                row[f'{p}_pass']=ok
            row['replicated']=all(oks)
        rows.append(row)
    return pd.DataFrame(rows)
def portfolio(c,sel,col):
    pcs=[]
    for r in sel[sel.replicated].itertuples(index=False):pcs.append(c[(c.exec_min==r.exec_min)&(c.range_order=='LOW_BEFORE_HIGH')].copy())
    if not pcs:return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pcs,ignore_index=True);decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,col);rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,col);rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m});return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s7a.s4.b.m.m.load5();c,audit=enrich(x);c.to_csv(OUT_CAND,index=False);audit.to_csv(OUT_AUDIT,index=False);audit_ok=bool(audit['pass'].all()) if len(audit) else False
    s=score(c);s.to_csv(OUT_SUM,index=False);sel=choose(s);sel.to_csv(OUT_SEL,index=False);d0,p0=portfolio(c,sel,'pnl_0');d5,p5=portfolio(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    ports=pd.DataFrame()
    if len(p0):
        a=p0.copy();a['stress_bps']=0;b=p5.copy();b['stress_bps']=5;ports=pd.concat([a,b],ignore_index=True)
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False
    if not audit_ok:status='ETH_S7E_CAUSAL_OR_PARITY_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7E_NO_DEV_RANGE_ORDER_FILTER'
    elif nrep==0:status='ETH_S7E_DEV_FILTERS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)];majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1);btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress);status='ETH_S7E_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7E_FILTERS_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7E Reference Range Formation Order — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- H/L + causal audit: **{"PASS" if audit_ok else "FAIL"}**.','- Promotion hypothesis: **LOW_BEFORE_HIGH** only.','','## Development anatomy','', '| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        d=s[(s.exec_min==ex)&(s.partition=='development')]
        for r in d.itertuples(index=False):
            prom=(r.variant=='LOW_BEFORE_HIGH' and r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0);lines.append(f'| {r.execution_utc} | {r.variant} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if prom else "NO"} |')
    lines += ['','## Frozen selection / replication','', '| Clock | Dev | External | RefVal | Replicated |','|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | NO | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | YES | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-promoted LOW_BEFORE_HIGH filter replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No cutoff sweep, alternate direction hypothesis, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
