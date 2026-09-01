#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
S7E_PATH=HERE/'eth_b27dx_s7e_range_formation_order.py'
spec=importlib.util.spec_from_file_location('eth_s7e',S7E_PATH);s7e=importlib.util.module_from_spec(spec)
assert spec.loader is not None;spec.loader.exec_module(s7e)
s7a=s7e.s7a

PFX='ETH_B27DX_S7F_0900_HIGH_BEFORE_LOW_REPLICATION'
OUT_MD=ROOT/f'{PFX}_Result.md';OUT_SUM=ROOT/f'{PFX}_Summary.csv';OUT_CAND=ROOT/f'{PFX}_Candidates.csv';OUT_AUDIT=ROOT/f'{PFX}_Audit.csv';OUT_STATUS=ROOT/f'{PFX}_Status.txt'
S7E_SUM=ROOT/'ETH_B27DX_S7E_RANGE_FORMATION_ORDER_Summary.csv'
CLOCK=540;PARTS=('external','development','reference_validation')
BTC_WR=s7e.BTC_WR;BTC_PF=s7e.BTC_PF;BTC_EXP=s7e.BTC_EXP

def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def close(a,b,tol=1e-9):
    if pd.isna(a) or pd.isna(b):return pd.isna(a) and pd.isna(b)
    if math.isinf(float(a)) or math.isinf(float(b)):return math.isinf(float(a)) and math.isinf(float(b)) and (float(a)>0)==(float(b)>0)
    return abs(float(a)-float(b))<=tol*max(1.,abs(float(b)))

def main():
    x,cov=s7a.s4.b.m.m.load5();c,audit0=s7e.enrich(x);c=c[c.exec_min==CLOCK].copy();f=c[c.range_order=='HIGH_BEFORE_LOW'].copy();c.to_csv(OUT_CAND,index=False)
    rows=[]
    for p in PARTS:
        base=c[c.partition==p].copy();q=f[f.partition==p].copy();m0=s7a.s4.metrics(q,'pnl_0');m5=s7a.s4.metrics(q,'pnl_5');ret=len(q)/len(base) if len(base) else np.nan
        rows.append({'partition':p,'stress_bps':0,'base_n':len(base),'n':len(q),'retention':ret,**m0})
        rows.append({'partition':p,'stress_bps':5,'base_n':len(base),'n':len(q),'retention':ret,**m5})
    # Diagnostic pooled, no selection use.
    for st,col in ((0,'pnl_0'),(5,'pnl_5')):
        m=s7a.s4.metrics(f,col);rows.append({'partition':'POOLED_MAJOR','stress_bps':st,'base_n':len(c),'n':len(f),'retention':len(f)/len(c),**m})
    s=pd.DataFrame(rows);s.to_csv(OUT_SUM,index=False)

    persisted=pd.read_csv(S7E_SUM)
    pr=persisted[(persisted.exec_min==CLOCK)&(persisted.partition=='development')&(persisted.variant=='HIGH_BEFORE_LOW')].iloc[0]
    rr=s[(s.partition=='development')&(s.stress_bps==0)].iloc[0]
    checks={'n':(rr.n,pr.n),'wr':(rr.wr,pr.wr),'pf':(rr.pf,pr.pf),'expectancy':(rr.expectancy,pr.expectancy),'net':(rr.net,pr.net)}
    ar=[]
    for k,(a,b) in checks.items():ar.append({'check':f'S7E_DEV_PARITY_{k}','actual':a,'expected':b,'pass':(int(a)==int(b) if k=='n' else close(a,b))})
    causal=bool(audit0[audit0.clock=='09:00']['pass'].all())
    ar.append({'check':'S7E_CAUSAL_AUDIT_0900','actual':causal,'expected':True,'pass':causal})
    audit=pd.DataFrame(ar);audit.to_csv(OUT_AUDIT,index=False);parity=bool(audit['pass'].all())

    rep=[]
    for p in ('external','reference_validation'):
        r=s[(s.partition==p)&(s.stress_bps==0)].iloc[0]
        rep.append(bool(r.n>=10 and r.retention>=.20 and r.wr>=.70 and r.pf>=1.20 and r.expectancy>0 and r.net>0))
    replicated=all(rep)
    z=s[(s.partition=='POOLED_MAJOR')&(s.stress_bps==0)].iloc[0];zs=s[(s.partition=='POOLED_MAJOR')&(s.stress_bps==5)].iloc[0]
    btc=bool(replicated and z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and zs.pf>=1 and zs.net>=0)
    if not parity:status='ETH_S7F_DEVELOPMENT_PARITY_FAILED'
    elif not replicated:status='ETH_S7F_0900_HIGH_BEFORE_LOW_NOT_REPLICATED'
    elif btc:status='ETH_S7F_0900_HIGH_BEFORE_LOW_REPLICATED_BTC_CLASS'
    else:status='ETH_S7F_0900_HIGH_BEFORE_LOW_REPLICATED_BELOW_BTC'

    lines=['# ETH B27DX — S7F 09:00 HIGH_BEFORE_LOW Historical Replication — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- S7E Development + causal parity: **{"PASS" if parity else "FAIL"}**.','- Frozen rule: **09:00 UTC · R300/X360 · F75/E25/F20 · HIGH_BEFORE_LOW**.','','## Frozen rule results','', '| Partition | Stress | Base N | Filter N | Retain | WR | PF | Exp | Net | Max LS | Replication pass |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for p in (*PARTS,'POOLED_MAJOR'):
        for st in (0,5):
            r=s[(s.partition==p)&(s.stress_bps==st)].iloc[0]
            rp='-'
            if st==0 and p in ('external','reference_validation'):rp='YES' if (r.n>=10 and r.retention>=.20 and r.wr>=.70 and r.pf>=1.20 and r.expectancy>0 and r.net>0) else 'NO'
            lines.append(f'| {p} | {st} bps | {int(r.base_n)} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} | {rp} |')
    lines += ['','## BTC diagnostic',f'- Historical replication: **{"PASS" if replicated else "FAIL"}**.',f'- Pooled BTC-class diagnostic: **{"PASS" if btc else "FAIL"}**.',f'- BTC benchmark: WR 71.9%, PF 2.22, expectancy +$1.26/trade.','','## Decision','',f'**Status: {status}**','', '- S7F is historical replication of a Development-generated hypothesis; no rule change was permitted after opening External/Reference Validation.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
