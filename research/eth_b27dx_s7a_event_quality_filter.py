#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S4_PATH=HERE/'eth_b27dx_s4_portfolio_lock.py'
spec=importlib.util.spec_from_file_location('eth_s4',S4_PATH); s4=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s4)

PFX='ETH_B27DX_S7A_EVENT_QUALITY_FILTER'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_SUM=ROOT/f'{PFX}_FilterSummary.csv'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=(300,540,600,960); PARTS=('external','development','reference_validation')
REF_MIN=300; HORIZON_MIN=360; ENTRY_F=.75; TARGET_EXT=.25; STOP_F=.20
HALF_REF=150.; HALF_EXEC=180.
FILTERS=('BASE','RANGE_COMPLETED_FIRST_HALF','RANGE_COMPLETED_SECOND_HALF','K1_FIRST_HALF','K1_SECOND_HALF','FILL_FIRST_HALF','FILL_SECOND_HALF','K1_FIRST_HALF__RANGE_COMPLETED_SECOND_HALF','FILL_FIRST_HALF__RANGE_COMPLETED_SECOND_HALF')
BTC_WR=.719298; BTC_PF=2.223193; BTC_EXP=1.26

def cl(v):return s4.clock_label(int(v))
def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,side='left'));b=int(x.index.searchsorted(end,side='left'));return x.iloc[a:b]
def first_extreme_ts(ref,col,val):
    arr=ref[col].to_numpy(float);idx=np.flatnonzero(np.isclose(arr,float(val),rtol=0.,atol=max(1e-10,abs(float(val))*1e-12)))
    if len(idx)==0:raise AssertionError('extreme occurrence missing')
    return pd.Timestamp(ref.index[int(idx[0])])
def feature_candidates(x):
    rows=[];audit=[]
    for p in PARTS:
        a,z=s4.b.m.m.PARTS[p]
        for ex in CLOCKS:
            for day in pd.date_range(a.normalize(),min(z,s4.b.m.m.END).normalize(),freq='D',tz='UTC'):
                es=day+pd.Timedelta(minutes=ex)
                if not (a<=es<z) or es.weekday()>=5:continue
                rs=es-pd.Timedelta(minutes=REF_MIN);ee=es+pd.Timedelta(minutes=HORIZON_MIN)
                if rs<s4.b.m.m.START or ee>=s4.b.m.m.END:continue
                ref=fast_slice(x,rs,es);exe=fast_slice(x,es,ee)
                if len(ref)!=REF_MIN//5 or len(exe)!=HORIZON_MIN//5:continue
                H=float(ref.high.max());L=float(ref.low.min())
                if not H>L:continue
                w=s4.b.m.corrected_find_window(exe,H,L,'LONG')
                if w is None or not bool(w.get('clean',False)):continue
                ep=s4.b.entry_level(L,H,ENTRY_F);fill=s4.b.find_fill(exe,w,ep)
                if fill is None:continue
                hts=first_extreme_ts(ref,'high',H);lts=first_extreme_ts(ref,'low',L);completion=max(hts,lts)
                completion_elapsed=float((completion-rs)/pd.Timedelta(minutes=1));k1_elapsed=float((pd.Timestamp(w['k1'])-es)/pd.Timedelta(minutes=1));fill_elapsed=float((pd.Timestamp(fill)-es)/pd.Timedelta(minutes=1))
                if not (0<=completion_elapsed<REF_MIN and 0<=k1_elapsed<HORIZON_MIN and 0<=fill_elapsed<HORIZON_MIN):raise AssertionError('feature timing out of bounds')
                target=s4.b.target_level(L,H,'LONG',TARGET_EXT);stop=s4.b.stop_level(L,H,STOP_F)
                d0=s4.score_trade_detail(x,exe,pd.Timestamp(fill),ee,ep,target,stop,0.);d5=s4.score_trade_detail(x,exe,pd.Timestamp(fill),ee,ep,target,stop,5.)
                if d0 is None or d5 is None:continue
                rows.append({'partition':p,'exec_min':ex,'execution_utc':cl(ex),'reference_start':rs,'execution_start':es,'entry_bar_start':pd.Timestamp(fill),'exit_ts':d0['exit_ts'],'entry_px':ep,'pnl_0':d0['pnl'],'pnl_5':d5['pnl'],'exit_reason':d0['exit_reason'],'H':H,'L':L,'range_completion_ts':completion,'range_completion_elapsed_min':completion_elapsed,'k1_ts':pd.Timestamp(w['k1']),'k1_elapsed_min':k1_elapsed,'fill_elapsed_min':fill_elapsed})
                audit.append({'partition':p,'clock':cl(ex),'execution_start':es,'completion_pre_execution':completion<es,'k1_pre_or_at_fill':pd.Timestamp(w['k1'])<=pd.Timestamp(fill),'feature_known_by_entry':completion<es and pd.Timestamp(w['k1'])<=pd.Timestamp(fill)})
    c=pd.DataFrame(rows)
    for col in ('reference_start','execution_start','entry_bar_start','exit_ts','range_completion_ts','k1_ts'):
        if col in c:c[col]=pd.to_datetime(c[col],utc=True)
    return c,pd.DataFrame(audit)
def mask(g,name):
    m=pd.Series(True,index=g.index)
    if name=='BASE':return m
    if 'RANGE_COMPLETED_FIRST_HALF' in name:m &= g.range_completion_elapsed_min<HALF_REF
    if 'RANGE_COMPLETED_SECOND_HALF' in name:m &= g.range_completion_elapsed_min>=HALF_REF
    if 'K1_FIRST_HALF' in name:m &= g.k1_elapsed_min<=HALF_EXEC
    if 'K1_SECOND_HALF' in name:m &= g.k1_elapsed_min>HALF_EXEC
    if 'FILL_FIRST_HALF' in name:m &= g.fill_elapsed_min<=HALF_EXEC
    if 'FILL_SECOND_HALF' in name:m &= g.fill_elapsed_min>HALF_EXEC
    return m
def complexity(name):return 0 if name=='BASE' else name.count('__')+1
def score_filters(c):
    rows=[]
    for ex in CLOCKS:
        for filt in FILTERS:
            for p in PARTS:
                raw=c[(c.exec_min==ex)&(c.partition==p)].copy();f=raw[mask(raw,filt)].copy();m=s4.metrics(f,'pnl_0')
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'filter':filt,'partition':p,'raw_n':len(raw),'filtered_n':len(f),'retention':len(f)/len(raw) if len(raw) else np.nan,**m})
    return pd.DataFrame(rows)
def choose(summary):
    rows=[]
    for ex in CLOCKS:
        d=summary[(summary.exec_min==ex)&(summary.partition=='development')].copy();d['promotable']=(d['filter']!='BASE')&(d.n>=20)&(d.retention>=.50)&(d.wr>=.75)&(d.pf>=1.50)&(d.expectancy>=.80)&(d.net>0)
        q=d[d.promotable].copy()
        if q.empty:
            rows.append({'exec_min':ex,'execution_utc':cl(ex),'selected_filter':'','dev_promoted':False,'replicated':False});continue
        q['complexity']=q['filter'].map(complexity);q['order']=q['filter'].map({v:i for i,v in enumerate(FILTERS)});q=q.sort_values(['complexity','retention','order'],ascending=[True,False,True]);r=q.iloc[0]
        row={'exec_min':ex,'execution_utc':cl(ex),'selected_filter':r['filter'],'dev_promoted':True,'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,'dev_expectancy':r.expectancy,'dev_net':r.net}
        oks=[]
        for p in ('external','reference_validation'):
            z=summary[(summary.exec_min==ex)&(summary.partition==p)&(summary['filter']==r['filter'])].iloc[0];ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
            for k in ('n','retention','wr','pf','expectancy','net'):row[f'{p}_{k}']=z[k]
            row[f'{p}_pass']=ok
        row['replicated']=all(oks);rows.append(row)
    return pd.DataFrame(rows)
def lock_filtered(c,sel,stress_col):
    pieces=[]
    for r in sel[sel.replicated].itertuples(index=False):
        q=c[c.exec_min==r.exec_min].copy();q=q[mask(q,r.selected_filter)].copy();q['selected_filter']=r.selected_filter;pieces.append(q)
    if not pieces:return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pieces,ignore_index=True);decs=[];rows=[];mw=sum(s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');m=s4.metrics(a,stress_col);rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');m=s4.metrics(a,stress_col);rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m});return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s4.b.m.m.load5();c,audit=feature_candidates(x);c.to_csv(OUT_CAND,index=False);audit.to_csv(OUT_AUDIT,index=False);causal=bool(audit.feature_known_by_entry.all()) if len(audit) else False;summary=score_filters(c);summary.to_csv(OUT_SUM,index=False);sel=choose(summary);sel.to_csv(OUT_SEL,index=False)
    d0,p0=lock_filtered(c,sel,'pnl_0');d5,p5=lock_filtered(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    if len(p0):
        po=p0.copy();po['stress_bps']=0;ps=p5.copy();ps['stress_bps']=5;ports=pd.concat([po,ps],ignore_index=True)
    else:ports=pd.DataFrame()
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False;majorpos=False
    if not causal:status='ETH_S7A_CAUSAL_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7A_NO_DEV_FILTER'
    elif nrep==0:status='ETH_S7A_DEV_FILTERS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)];majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1);btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress);status='ETH_S7A_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7A_FILTERS_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7A Native Event-Quality Filter Discovery — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Causal feature audit: **{"PASS" if causal else "FAIL"}**.','', '## Development filter screen','', '| Clock | Filter | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        d=summary[(summary.exec_min==ex)&(summary.partition=='development')].copy();d['prom']=(d['filter']!='BASE')&(d.n>=20)&(d.retention>=.50)&(d.wr>=.75)&(d.pf>=1.50)&(d.expectancy>=.80)&(d.net>0)
        for r in d.sort_values('filter').itertuples(index=False):lines.append(f'| {r.execution_utc} | {r.filter} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if r.prom else "NO"} |')
    lines += ['','## Frozen Development selections / replication','', '| Clock | Selected filter | Dev | External | RefVal | Replicated |','|---:|---|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | - | NO | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | {r.selected_filter} | YES | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-selected filter replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No cutoff sweep, new geometry, runner, leverage, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
