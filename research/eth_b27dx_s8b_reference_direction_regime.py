#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
S7A_PATH=HERE/'eth_b27dx_s7a_event_quality_filter.py'
spec=importlib.util.spec_from_file_location('eth_s7a',S7A_PATH)
s7a=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(s7a)

PFX='ETH_B27DX_S8B_REFERENCE_DIRECTION_REGIME'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_CAND=ROOT/f'{PFX}_Candidates.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_SEL=ROOT/f'{PFX}_Selections.csv'
OUT_DEC=ROOT/f'{PFX}_Decisions.csv'
OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS
PARTS=s7a.PARTS

def cl(v): return s7a.cl(int(v))

def attach_direction(c,x):
    q=c.copy()
    rows=[]
    for r in q.itertuples(index=False):
        rs=pd.Timestamp(r.reference_start)
        es=pd.Timestamp(r.execution_start)
        ref=s7a.fast_slice(x,rs,es)
        if len(ref)!=s7a.REF_MIN//5:
            raise AssertionError('reference bar count mismatch')
        op=float(ref.iloc[0].open)
        close=float(ref.iloc[-1].close)
        drift=close/op-1.0
        if close>op: state='UP_REF'
        elif close<op: state='DOWN_REF'
        else: state='FLAT_REF'
        rows.append({'partition':r.partition,'exec_min':int(r.exec_min),'execution_start':es,
                     'entry_bar_start':pd.Timestamp(r.entry_bar_start),'reference_open':op,
                     'reference_close':close,'reference_drift':drift,'direction_regime':state,
                     'direction_known_by_execution':True})
    feat=pd.DataFrame(rows)
    keys=['partition','exec_min','execution_start','entry_bar_start']
    if feat.duplicated(keys).any(): raise AssertionError('duplicate direction keys')
    q=q.merge(feat,on=keys,how='left',validate='one_to_one')
    if q.direction_regime.isna().any(): raise AssertionError('missing direction regime')
    return q,feat

def score(c):
    rows=[]
    for ex in CLOCKS:
        for p in PARTS:
            base=c[(c.exec_min==ex)&(c.partition==p)&(c.direction_regime!='FLAT_REF')].copy()
            n0=len(base)
            for state in ('DIRECTION_BASE','UP_REF','DOWN_REF'):
                z=base if state=='DIRECTION_BASE' else base[base.direction_regime==state].copy()
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'state':state,'partition':p,
                             'base_n':n0,'n':len(z),'retention':len(z)/n0 if n0 else np.nan,
                             **s7a.s4.metrics(z,'pnl_0')})
    return pd.DataFrame(rows)

def choose(s):
    rows=[]
    for ex in CLOCKS:
        d=s[(s.exec_min==ex)&(s.partition=='development')&s.state.isin(['UP_REF','DOWN_REF'])].copy()
        d['prom']=(d.n>=20)&(d.retention>=.40)&(d.wr>=.75)&(d.pf>=1.50)&(d.expectancy>=.80)&(d.net>0)
        q=d[d.prom].copy()
        if q.empty:
            rows.append({'exec_min':ex,'execution_utc':cl(ex),'selected_state':'','dev_promoted':False,'replicated':False})
            continue
        q['tie']=q.state.map({'UP_REF':0,'DOWN_REF':1})
        q=q.sort_values(['retention','tie'],ascending=[False,True])
        r=q.iloc[0]
        row={'exec_min':ex,'execution_utc':cl(ex),'selected_state':r.state,'dev_promoted':True,
             'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,
             'dev_expectancy':r.expectancy,'dev_net':r.net}
        oks=[]
        for p in ('external','reference_validation'):
            z=s[(s.exec_min==ex)&(s.partition==p)&(s.state==r.state)].iloc[0]
            ok=bool(z.n>=10 and z.retention>=.30 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0)
            oks.append(ok)
            for k in ('n','retention','wr','pf','expectancy','net'):
                row[f'{p}_{k}']=z[k]
            row[f'{p}_pass']=ok
        row['replicated']=all(oks)
        rows.append(row)
    return pd.DataFrame(rows)

def lock_selected(c,sel,pnl_col):
    pieces=[]
    for r in sel[sel.replicated].itertuples(index=False):
        z=c[(c.exec_min==r.exec_min)&(c.direction_regime==r.selected_state)].copy()
        z['selected_state']=r.selected_state
        pieces.append(z)
    if not pieces: return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pieces,ignore_index=True)
    decs=[]; rows=[]
    mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy())
        decs.append(d)
        a=d[d.accepted].sort_values('entry_bar_start')
        rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),
                     'trades_per_week':len(a)/s7a.s4.weeks_for(p),**s7a.s4.metrics(a,pnl_col)})
    d=pd.concat(decs,ignore_index=True)
    a=d[d.accepted].sort_values('entry_bar_start')
    rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),
                 'trades_per_week':len(a)/mw,**s7a.s4.metrics(a,pnl_col)})
    return d,pd.DataFrame(rows)

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    return 'inf' if math.isinf(float(v)) else f'{float(v):.2f}'

def main():
    x,cov=s7a.s4.b.m.m.load5()
    base,audit=s7a.feature_candidates(x)
    c,feat=attach_direction(base,x)
    c.to_csv(OUT_CAND,index=False)
    causal=bool(audit.feature_known_by_entry.all() and feat.direction_known_by_execution.all()) if len(c) else False
    s=score(c); s.to_csv(OUT_SUM,index=False)
    sel=choose(s); sel.to_csv(OUT_SEL,index=False)
    d0,p0=lock_selected(c,sel,'pnl_0')
    d5,p5=lock_selected(c,sel,'pnl_5')
    d0.to_csv(OUT_DEC,index=False)
    ports=pd.concat([p0.assign(stress_bps=0),p5.assign(stress_bps=5)],ignore_index=True) if len(p0) else pd.DataFrame()
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum()); nrep=int(sel.replicated.sum()); btc=False; stress=False
    if not causal: status='ETH_S8B_CAUSAL_AUDIT_FAILED'
    elif ndev==0: status='ETH_S8B_NO_DEV_DIRECTION_REGIME'
    elif nrep==0: status='ETH_S8B_DEV_REGIMES_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0]
        zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0]
        maj=p0[p0.partition.isin(PARTS)]
        stress=bool(zs.net>=0 and zs.pf>=1)
        btc=bool(z.wr>=s7a.BTC_WR and z.pf>=s7a.BTC_PF and z.expectancy>=s7a.BTC_EXP and ((maj.net>0)&(maj.pf>1)).all() and stress)
        status='ETH_S8B_DIRECTION_REGIME_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S8B_DIRECTION_REGIMES_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S8B Reference-Direction Regime — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           f'- Causal audit: **{"PASS" if causal else "FAIL"}**.','- Direction state is the sign of completed R300 reference drift; no magnitude threshold or lookback.','',
           '## Development regime screen','',
           '| Clock | State | N | Retain | WR | PF | Exp | Net | Promote |',
           '|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        for state in ('DIRECTION_BASE','UP_REF','DOWN_REF'):
            r=s[(s.exec_min==ex)&(s.partition=='development')&(s.state==state)].iloc[0]
            prom=bool(state!='DIRECTION_BASE' and r.n>=20 and r.retention>=.40 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
            lines.append(f'| {r.execution_utc} | {state} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.net)} | {"YES" if prom else "NO"} |')
    lines+=['','## Frozen Development selection / replication','']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted: lines.append(f'- {r.execution_utc}: no Development direction regime promoted.')
        else: lines.append(f'- {r.execution_utc}: **{r.selected_state}**; External {"PASS" if r.external_pass else "FAIL"}; RefVal {"PASS" if r.reference_validation_pass else "FAIL"}; replicated **{"YES" if r.replicated else "NO"}**.')
    lines+=['','## Portfolio','']
    if nrep:
        for p in (*PARTS,'POOLED_MAJOR'):
            r=p0[p0.partition==p].iloc[0]
            lines.append(f'- {p}: N **{int(r.accepted)}**, {r.trades_per_week:.3f}/wk, WR **{pct(r.wr)}**, PF **{num(r.pf)}**, exp **{num(r.expectancy)}**, net **{num(r.net)}**.')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0]
        lines += [f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    else: lines.append('No direction regime replicated into a promoted portfolio.')
    lines+=['','## Decision','',f'**Status: {status}**','', '- No magnitude threshold, alternate timeframe, event filter, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())
if __name__=='__main__': main()
