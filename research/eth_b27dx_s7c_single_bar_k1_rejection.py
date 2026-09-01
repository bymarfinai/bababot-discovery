#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S7A_PATH=HERE/'eth_b27dx_s7a_event_quality_filter.py'
spec=importlib.util.spec_from_file_location('eth_s7a',S7A_PATH); s7a=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s7a)

PFX='ETH_B27DX_S7C_SINGLE_BAR_K1_REJECTION'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS; PARTS=s7a.PARTS; HORIZON_MIN=s7a.HORIZON_MIN
BTC_WR=s7a.BTC_WR; BTC_PF=s7a.BTC_PF; BTC_EXP=s7a.BTC_EXP

def cl(v): return s7a.cl(int(v))
def attach_episode(c,x):
    q=c.copy(); rows=[]
    for r in q.itertuples(index=False):
        es=pd.Timestamp(r.execution_start); ee=es+pd.Timedelta(minutes=HORIZON_MIN); exe=s7a.fast_slice(x,es,ee)
        w=s7a.s4.b.m.corrected_find_window(exe,float(r.H),float(r.L),'LONG')
        if w is None or not bool(w.get('clean',False)): raise AssertionError('candidate lost causal window')
        k1=pd.Timestamp(w['k1']); leave=pd.Timestamp(w['leave_bar']); eligible=pd.Timestamp(w['eligible_start']); entry=pd.Timestamp(r.entry_bar_start)
        delta=float((leave-k1)/pd.Timedelta(minutes=5))
        if delta < 1 or abs(delta-round(delta))>1e-9: raise AssertionError(f'invalid episode bars {delta}')
        bars=int(round(delta))
        rows.append({'partition':r.partition,'exec_min':int(r.exec_min),'execution_start':es,'entry_bar_start':entry,
                     'k1_ts_check':k1,'leave_bar_start':leave,'eligible_start_check':eligible,
                     'k1_touch_episode_bars':bars,'single_bar_k1_rejection':bars==1,
                     'episode_known_by_entry':bool(k1 < leave < eligible <= entry)})
    f=pd.DataFrame(rows); keys=['partition','exec_min','execution_start','entry_bar_start']
    if f.duplicated(keys).any(): raise AssertionError('duplicate episode feature keys')
    q=q.merge(f,on=keys,how='left',validate='one_to_one')
    if q.k1_touch_episode_bars.isna().any(): raise AssertionError('missing episode feature')
    return q,f

def filt_mask(g): return g.single_bar_k1_rejection.astype(bool)
def score(c):
    rows=[]
    for ex in CLOCKS:
        for p in PARTS:
            raw=c[(c.exec_min==ex)&(c.partition==p)].copy()
            for name,f in [('BASE',raw),('SINGLE_BAR_K1_REJECTION',raw[filt_mask(raw)].copy())]:
                m=s7a.s4.metrics(f,'pnl_0')
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'filter':name,'partition':p,'raw_n':len(raw),'n':len(f),
                             'retention':len(f)/len(raw) if len(raw) else np.nan,**m})
    return pd.DataFrame(rows)
def choose(summary):
    rows=[]
    for ex in CLOCKS:
        d=summary[(summary.exec_min==ex)&(summary.partition=='development')&(summary['filter']=='SINGLE_BAR_K1_REJECTION')].iloc[0]
        prom=bool(d.n>=20 and d.retention>=.50 and d.wr>=.75 and d.pf>=1.50 and d.expectancy>=.80 and d.net>0)
        row={'exec_min':ex,'execution_utc':cl(ex),'selected_filter':'SINGLE_BAR_K1_REJECTION' if prom else '',
             'dev_promoted':prom,'dev_n':d.n,'dev_retention':d.retention,'dev_wr':d.wr,'dev_pf':d.pf,'dev_expectancy':d.expectancy,'dev_net':d.net,'replicated':False}
        if prom:
            oks=[]
            for p in ('external','reference_validation'):
                z=summary[(summary.exec_min==ex)&(summary.partition==p)&(summary['filter']=='SINGLE_BAR_K1_REJECTION')].iloc[0]
                ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
                for k in ('n','retention','wr','pf','expectancy','net'): row[f'{p}_{k}']=z[k]
                row[f'{p}_pass']=ok
            row['replicated']=all(oks)
        rows.append(row)
    return pd.DataFrame(rows)
def lock_filtered(c,sel,pnl_col):
    clocks=set(int(x) for x in sel.loc[sel.replicated,'exec_min'].tolist())
    if not clocks:return pd.DataFrame(),pd.DataFrame()
    allc=c[c.exec_min.isin(clocks)&filt_mask(c)].copy();decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,pnl_col)
        rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,pnl_col)
    rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m})
    return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s7a.s4.b.m.m.load5();base,a0=s7a.feature_candidates(x);c,af=attach_episode(base,x);c.to_csv(OUT_CAND,index=False)
    audit=pd.concat([a0.reset_index(drop=True),af[['episode_known_by_entry']].reset_index(drop=True)],axis=1);audit.to_csv(OUT_AUDIT,index=False)
    causal=bool(audit.feature_known_by_entry.all() and audit.episode_known_by_entry.all()) if len(audit) else False
    summary=score(c);summary.to_csv(OUT_SUM,index=False);sel=choose(summary);sel.to_csv(OUT_SEL,index=False)
    d0,p0=lock_filtered(c,sel,'pnl_0');d5,p5=lock_filtered(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    if len(p0):
        a=p0.copy();a['stress_bps']=0;b=p5.copy();b['stress_bps']=5;ports=pd.concat([a,b],ignore_index=True)
    else:ports=pd.DataFrame()
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False
    if not causal:status='ETH_S7C_CAUSAL_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7C_NO_DEV_SINGLE_BAR_FILTER'
    elif nrep==0:status='ETH_S7C_DEV_FILTERS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)]
        majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1)
        btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress)
        status='ETH_S7C_SINGLE_BAR_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7C_SINGLE_BAR_FILTERS_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7C Single-Bar K1 Rejection — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Causal audit: **{"PASS" if causal else "FAIL"}**.','- Frozen filter: **SINGLE_BAR_K1_REJECTION = the first K1 H-touch bar is followed immediately by the causal leave bar.**','',
           '## Development comparison','', '| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        for name in ('BASE','SINGLE_BAR_K1_REJECTION'):
            r=summary[(summary.exec_min==ex)&(summary.partition=='development')&(summary['filter']==name)].iloc[0]
            prom=bool(name!='BASE' and r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
            lines.append(f'| {r.execution_utc} | {name} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if prom else "NO"} |')
    lines += ['','## Frozen Development selections / replication','', '| Clock | Dev | External | RefVal | Replicated |','|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | NO | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | YES | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-promoted single-bar K1 filter replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No duration threshold sweep, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
