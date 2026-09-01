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

PFX='ETH_B27DX_S7C_K1_EPISODE_PERSISTENCE'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS; PARTS=s7a.PARTS; REF_MIN=s7a.REF_MIN; HORIZON_MIN=s7a.HORIZON_MIN
ENTRY_F=s7a.ENTRY_F; TARGET_EXT=s7a.TARGET_EXT; STOP_F=s7a.STOP_F
BTC_WR=s7a.BTC_WR; BTC_PF=s7a.BTC_PF; BTC_EXP=s7a.BTC_EXP
BAR5=pd.Timedelta(minutes=5)
VARIANTS=('BASE','SINGLE_BAR_K1_EPISODE','MULTI_BAR_K1_EPISODE')

def cl(v):return s7a.cl(int(v))
def fast_slice(x,start,end):return s7a.fast_slice(x,start,end)

def build_candidates(x):
    rows=[];audit=[]
    for p in PARTS:
        a,z=s7a.s4.b.m.m.PARTS[p]
        for ex in CLOCKS:
            for day in pd.date_range(a.normalize(),min(z,s7a.s4.b.m.m.END).normalize(),freq='D',tz='UTC'):
                es=day+pd.Timedelta(minutes=ex)
                if not (a<=es<z) or es.weekday()>=5:continue
                rs=es-pd.Timedelta(minutes=REF_MIN);ee=es+pd.Timedelta(minutes=HORIZON_MIN)
                if rs<s7a.s4.b.m.m.START or ee>=s7a.s4.b.m.m.END:continue
                ref=fast_slice(x,rs,es);exe=fast_slice(x,es,ee)
                if len(ref)!=REF_MIN//5 or len(exe)!=HORIZON_MIN//5:continue
                H=float(ref.high.max());L=float(ref.low.min())
                if not H>L:continue
                w=s7a.s4.b.m.corrected_find_window(exe,H,L,'LONG')
                if w is None or not bool(w.get('clean',False)):continue
                k1=pd.Timestamp(w['k1']);leave=pd.Timestamp(w['leave_bar'])
                ep=s7a.s4.b.entry_level(L,H,ENTRY_F);fill=s7a.s4.b.find_fill(exe,w,ep)
                if fill is None:continue
                fill=pd.Timestamp(fill)
                delta=(leave-k1)/BAR5
                epi=int(round(float(delta)))
                integer_ok=abs(float(delta)-epi)<=1e-9
                known=(k1<leave and leave+BAR5<=fill)
                if not integer_ok or epi<1:raise AssertionError(f'invalid K1 episode bars {p} {cl(ex)} {es} {delta}')
                target=s7a.s4.b.target_level(L,H,'LONG',TARGET_EXT);stop=s7a.s4.b.stop_level(L,H,STOP_F)
                d0=s7a.s4.score_trade_detail(x,exe,fill,ee,ep,target,stop,0.);d5=s7a.s4.score_trade_detail(x,exe,fill,ee,ep,target,stop,5.)
                if d0 is None or d5 is None:continue
                rows.append({'partition':p,'exec_min':ex,'execution_utc':cl(ex),'execution_start':es,'entry_bar_start':fill,'exit_ts':d0['exit_ts'],'entry_px':ep,'pnl_0':d0['pnl'],'pnl_5':d5['pnl'],'exit_reason':d0['exit_reason'],'k1_ts':k1,'leave_bar':leave,'k1_episode_bars':epi,'single_bar_episode':epi==1})
                audit.append({'partition':p,'clock':cl(ex),'execution_start':es,'k1_before_leave':k1<leave,'leave_completed_by_entry':leave+BAR5<=fill,'integer_episode_bars':integer_ok,'episode_ge_1':epi>=1,'feature_known_by_entry':known and integer_ok and epi>=1})
    c=pd.DataFrame(rows)
    for col in ('execution_start','entry_bar_start','exit_ts','k1_ts','leave_bar'):
        if col in c:c[col]=pd.to_datetime(c[col],utc=True)
    return c,pd.DataFrame(audit)

def mask(g,name):
    if name=='BASE':return pd.Series(True,index=g.index)
    if name=='SINGLE_BAR_K1_EPISODE':return g.k1_episode_bars.eq(1)
    if name=='MULTI_BAR_K1_EPISODE':return g.k1_episode_bars.ge(2)
    raise KeyError(name)

def score(c):
    rows=[]
    for ex in CLOCKS:
        for v in VARIANTS:
            for p in PARTS:
                raw=c[(c.exec_min==ex)&(c.partition==p)].copy();q=raw[mask(raw,v)].copy();m=s7a.s4.metrics(q,'pnl_0')
                rows.append({'exec_min':ex,'execution_utc':cl(ex),'variant':v,'partition':p,'raw_n':len(raw),'n':len(q),'retention':len(q)/len(raw) if len(raw) else np.nan,**m})
    return pd.DataFrame(rows)

def choose(summary):
    rows=[]
    for ex in CLOCKS:
        d=summary[(summary.exec_min==ex)&(summary.partition=='development')]
        r=d[d.variant=='SINGLE_BAR_K1_EPISODE'].iloc[0]
        prom=bool(r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
        row={'exec_min':ex,'execution_utc':cl(ex),'dev_promoted':prom,'dev_n':r.n,'dev_retention':r.retention,'dev_wr':r.wr,'dev_pf':r.pf,'dev_expectancy':r.expectancy,'dev_net':r.net,'replicated':False}
        if prom:
            oks=[]
            for p in ('external','reference_validation'):
                z=summary[(summary.exec_min==ex)&(summary.partition==p)&(summary.variant=='SINGLE_BAR_K1_EPISODE')].iloc[0]
                ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0);oks.append(ok)
                for k in ('n','retention','wr','pf','expectancy','net'):row[f'{p}_{k}']=z[k]
                row[f'{p}_pass']=ok
            row['replicated']=all(oks)
        rows.append(row)
    return pd.DataFrame(rows)

def portfolio(c,sel,col):
    pieces=[]
    for r in sel[sel.replicated].itertuples(index=False):
        q=c[(c.exec_min==r.exec_min)&c.single_bar_episode].copy();pieces.append(q)
    if not pieces:return pd.DataFrame(),pd.DataFrame()
    allc=pd.concat(pieces,ignore_index=True);decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,col);rows.append({'partition':p,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start');m=s7a.s4.metrics(a,col);rows.append({'partition':'POOLED_MAJOR','candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m});return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s7a.s4.b.m.m.load5();c,audit=build_candidates(x);c.to_csv(OUT_CAND,index=False);audit.to_csv(OUT_AUDIT,index=False)
    causal=bool(audit.feature_known_by_entry.all()) if len(audit) else False
    summary=score(c);summary.to_csv(OUT_SUM,index=False);sel=choose(summary);sel.to_csv(OUT_SEL,index=False)
    d0,p0=portfolio(c,sel,'pnl_0');d5,p5=portfolio(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
    ports=pd.DataFrame()
    if len(p0):
        a=p0.copy();a['stress_bps']=0;b=p5.copy();b['stress_bps']=5;ports=pd.concat([a,b],ignore_index=True)
    ports.to_csv(OUT_PORT,index=False)
    ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum());btc=False;stress=False
    if not causal:status='ETH_S7C_CAUSAL_AUDIT_FAILED'
    elif ndev==0:status='ETH_S7C_NO_DEV_SINGLE_EPISODE_FILTER'
    elif nrep==0:status='ETH_S7C_DEV_FILTERS_NOT_REPLICATED'
    else:
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)]
        majorpos=bool(((maj.net>0)&(maj.pf>1)).all());stress=bool(zs.net>=0 and zs.pf>=1);btc=bool(z.wr>=BTC_WR and z.pf>=BTC_PF and z.expectancy>=BTC_EXP and majorpos and stress);status='ETH_S7C_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7C_FILTERS_REPLICATED_BELOW_BTC'
    lines=['# ETH B27DX — S7C K1 Episode Persistence — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Causal audit: **{"PASS" if causal else "FAIL"}**.','- Promotion hypothesis: **SINGLE_BAR_K1_EPISODE** only. Multi-bar is diagnostic complement.','','## Development anatomy','', '| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for ex in CLOCKS:
        d=summary[(summary.exec_min==ex)&(summary.partition=='development')]
        for r in d.itertuples(index=False):
            prom=(r.variant=='SINGLE_BAR_K1_EPISODE' and r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0)
            lines.append(f'| {r.execution_utc} | {r.variant} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {"YES" if prom else "NO"} |')
    lines += ['','## Frozen Development selections / replication','', '| Clock | Dev | External | RefVal | Replicated |','|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):
        if not r.dev_promoted:lines.append(f'| {r.execution_utc} | NO | - | - | NO |')
        else:lines.append(f'| {r.execution_utc} | YES | {"PASS" if r.external_pass else "FAIL"} | {"PASS" if r.reference_validation_pass else "FAIL"} | {"YES" if r.replicated else "NO"} |')
    lines += ['','## Promoted portfolio','']
    if nrep==0:lines.append('No Development-promoted single-bar K1 episode filter replicated in both historical validation partitions.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st,df in ((0,p0),(5,p5)):
                r=df[df.partition==p].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];lines += ['',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- Pooled frequency: **{z.trades_per_week:.3f}/week**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No alternate episode-length threshold, geometry, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
