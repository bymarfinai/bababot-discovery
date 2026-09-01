#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S7C_PATH=HERE/'eth_b27dx_s7c_k1_episode_persistence.py'
spec=importlib.util.spec_from_file_location('eth_s7c',S7C_PATH); s7c=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s7c)
s7a=s7c.s7a

PFX='ETH_B27DX_S7D_SINGLE_K1_LATE_RANGE_INTERACTION'
OUT_MD=ROOT/f'{PFX}_Result.md';OUT_CAND=ROOT/f'{PFX}_Candidates.csv';OUT_SUM=ROOT/f'{PFX}_Summary.csv';OUT_SEL=ROOT/f'{PFX}_Selections.csv';OUT_DEC=ROOT/f'{PFX}_Decisions.csv';OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv';OUT_AUDIT=ROOT/f'{PFX}_Audit.csv';OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7c.CLOCKS;PARTS=s7c.PARTS;HALF_REF=150.
BTC_WR=s7c.BTC_WR;BTC_PF=s7c.BTC_PF;BTC_EXP=s7c.BTC_EXP
VARIANTS=('BASE','SINGLE_BAR_K1_EPISODE','RANGE_COMPLETED_SECOND_HALF','SINGLE_K1__LATE_RANGE')

def cl(v):return s7c.cl(int(v))
def mask(g,v):
    if v=='BASE':return pd.Series(True,index=g.index)
    single=g.k1_episode_bars.eq(1);late=g.range_completion_elapsed_min.ge(HALF_REF)
    if v=='SINGLE_BAR_K1_EPISODE':return single
    if v=='RANGE_COMPLETED_SECOND_HALF':return late
    if v=='SINGLE_K1__LATE_RANGE':return single&late
    raise KeyError(v)

def build(x):
    a,aa=s7a.feature_candidates(x);c,ca=s7c.build_candidates(x)
    keys=['partition','exec_min','execution_start','entry_bar_start']
    acols=keys+['range_completion_ts','range_completion_elapsed_min','pnl_0','pnl_5']
    ccols=keys+['exit_ts','entry_px','pnl_0','pnl_5','k1_ts','leave_bar','k1_episode_bars','single_bar_episode']
    m=c[ccols].merge(a[acols],on=keys,how='inner',validate='one_to_one',suffixes=('_c','_a'))
    rows=[]
    universe_ok=(len(m)==len(a)==len(c))
    pnl0_ok=bool(np.allclose(m.pnl_0_c,m.pnl_0_a,rtol=0,atol=1e-9)) if len(m) else False
    pnl5_ok=bool(np.allclose(m.pnl_5_c,m.pnl_5_a,rtol=0,atol=1e-9)) if len(m) else False
    causal_ok=bool((pd.to_datetime(m.range_completion_ts,utc=True)<pd.to_datetime(m.execution_start,utc=True)).all() and ((pd.to_datetime(m.leave_bar,utc=True)+pd.Timedelta(minutes=5))<=pd.to_datetime(m.entry_bar_start,utc=True)).all()) if len(m) else False
    rows=[{'check':'candidate_universe_one_to_one','pass':universe_ok,'value':len(m)},{'check':'pnl_0_parity','pass':pnl0_ok,'value':float((m.pnl_0_c-m.pnl_0_a).abs().max()) if len(m) else np.nan},{'check':'pnl_5_parity','pass':pnl5_ok,'value':float((m.pnl_5_c-m.pnl_5_a).abs().max()) if len(m) else np.nan},{'check':'causal_features_known_by_entry','pass':causal_ok,'value':len(m)}]
    m=m.rename(columns={'pnl_0_c':'pnl_0','pnl_5_c':'pnl_5'}).drop(columns=['pnl_0_a','pnl_5_a'])
    return m,pd.DataFrame(rows)
def score(c):
    rows=[]
    for ex in CLOCKS:
        for v in VARIANTS:
            for p in PARTS:
                raw=c[(c.exec_min==ex)&(c.partition==p)].copy();q=raw[mask(raw,v)].copy();met=s7a.s4.metrics(q,'pnl_0')
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'variant':v,'partition':p,'raw_n':len(raw),'n':len(q),'retention':len(q)/len(raw) if len(raw) else np.nan,**met})
    return pd.DataFrame(rows)
def choose(s):
    rows=[]
    for ex in CLOCKS:
        r=s[(s.exec_min==ex)&(s.partition=='development')&(s.variant=='SINGLE_K1__LATE_RANGE')].iloc[0]
        prom=bool(r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
        row={'exec_min':ex,'execution_utc':cl(ex),'dev_promoted':prom,'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,'dev_expectancy':r.expectancy,'dev_net':r.net,'replicated':False}
        if prom:
            oks=[]
            for p in ('external','reference_validation'):
                z=s[(s.exec_min==ex)&(s.partition==p)&(s.variant=='SINGLE_K1__LATE_RANGE')].iloc[0];ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
                for k in ('n','retention','wr','pf','expectancy','net'):row[f'{p}_{k}']=z[k]
                row[f'{p}_pass']=ok
            row['replicated']=all(oks)
        rows.append(row)
    return pd.DataFrame(rows)
def portfolio(c,sel,col):
    pieces=[]
    for r in sel[sel.replicated].itertuples(index=False):pieces.append(c[(c.exec_min==r.exec_min)&mask(c,'SINGLE_K1__LATE_RANGE')].copy())
    if not pieces:return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pieces,ignore_index=True);decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');met=s7a.s4.metrics(a,col);rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**met})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');met=s7a.s4.metrics(a,col);rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**met});return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s7a.s4.b.m.m.load5();c,audit=build(x);c.to_csv(OUT_CAND,index=False);audit.to_csv(OUT_AUDIT,index=False);audit_ok=bool(audit['pass'].all())
    s=score(c);s.to_csv(OUT_SUM,index=False);sel=choose(s);sel.to_csv(OUT_SEL,index=False);d0,p0=portfolio(c,sel,'pnl_0');d5,p5=portfolio(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    ports=pd.DataFrame()
    if len(p0):
        a=p0.copy();a['stress_bps']=0;b=p5.copy();b['stress_bps']=5;ports=pd.concat([a,b],ignore_index=True)
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False
    if not audit_ok:status='ETH_S7D_PARITY_OR_CAUSAL_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7D_NO_DEV_INTERACTION'
    elif nrep==0:status='ETH_S7D_DEV_INTERACTIONS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)];majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1);btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress);status='ETH_S7D_INTERACTION_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7D_INTERACTION_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7D Single-K1 × Late-Range Interaction — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Candidate/parity/causal audit: **{"PASS" if audit_ok else "FAIL"}**.','- Only `SINGLE_K1__LATE_RANGE` is promotion-eligible.','','## Development comparison','', '| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        d=s[(s.exec_min==ex)&(s.partition=='development')]
        for r in d.itertuples(index=False):
            prom=(r.variant=='SINGLE_K1__LATE_RANGE' and r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
            lines.append(f'| {r.execution_utc} | {r.variant} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if prom else "NO"} |')
    lines += ['','## Frozen selection / replication','', '| Clock | Dev | External | RefVal | Replicated |','|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | NO | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | YES | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-promoted interaction replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- Exploratory interaction on inspected history; no alternate threshold, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
