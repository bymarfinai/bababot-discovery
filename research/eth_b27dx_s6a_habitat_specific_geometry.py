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

PFX='ETH_B27DX_S6A_HABITAT_SPECIFIC_GEOMETRY'
SCORES_PATH=ROOT/'ETH_B27DX_S3C_JOINT_GEOMETRY_Scores.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_PARITY=ROOT/f'{PFX}_Parity.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
ENTRIES=(0.85,0.80,0.75,0.70); TARGETS=(0.10,0.15,0.20,0.25,0.30,0.35,0.40); STOPS=(0.20,0.15); CLOCKS=(300,540,600,960); PARTS=('external','development','reference_validation')
BTC_WR=.719298; BTC_PF=2.223193; BTC_EXP=1.26

def fl(v):return f'F{int(round(v*100)):02d}'
def tl(v):return f'E{int(round(v*100)):02d}'
def cl(v):return s4.clock_label(int(v))
def load_scores():
    q=pd.read_csv(SCORES_PATH)
    for c in ('entry_f','target_ext','stop_f','wr','pf','expectancy','net','n','exec_min'):q[c]=pd.to_numeric(q[c],errors='coerce')
    return q

def comps(cells):
    ei={v:i for i,v in enumerate(ENTRIES)};ti={v:i for i,v in enumerate(TARGETS)};si={v:i for i,v in enumerate(STOPS)}
    coord={(ei[e],ti[t],si[st]):(e,t,st) for e,t,st in cells}; unseen=set(coord);out=[]
    while unseen:
        seed=min(unseen);unseen.remove(seed);stack=[seed];comp=[]
        while stack:
            c=stack.pop();comp.append(coord[c])
            for ax in range(3):
                for d in (-1,1):
                    z=list(c);z[ax]+=d;z=tuple(z)
                    if z in unseen:unseen.remove(z);stack.append(z)
        out.append(comp)
    return out

def qualifies(comp):return len(comp)>=4 and len({e for e,_,_ in comp})>=2 and len({t for _,t,_ in comp})>=2 and len({st for _,_,st in comp})==2
def medoid(comp):
    ei={v:i for i,v in enumerate(ENTRIES)};ti={v:i for i,v in enumerate(TARGETS)};si={v:i for i,v in enumerate(STOPS)}
    med=np.array([np.median([ei[e] for e,_,_ in comp]),np.median([ti[t] for _,t,_ in comp]),np.median([si[st] for _,_,st in comp])])
    def key(x):
        e,t,st=x;idx=np.array([ei[e],ti[t],si[st]],dtype=float);return (float(np.abs(idx-med).sum()),-e,t,-st)
    return min(comp,key=key)
def select(scores):
    rows=[]
    for ex in CLOCKS:
        d=scores[(scores.exec_min==ex)&(scores.partition=='development')].copy()
        elig=d[(d.n>=30)&(d.wr>=.65)&(d.pf>=1.40)&(d.expectancy>=.80)&(d.net>0)].copy()
        cells=[(float(r.entry_f),float(r.target_ext),float(r.stop_f)) for r in elig.itertuples(index=False)]
        cc=sorted(comps(cells),key=lambda z:(-len(z),sorted(z))) if cells else []
        qc=[z for z in cc if qualifies(z)]
        if not qc:
            rows.append({'exec_min':ex,'execution_utc':cl(ex),'dev_eligible_cells':len(cells),'component_cells':0,'entry_f':np.nan,'target_ext':np.nan,'stop_f':np.nan,'selected':False,'external_pass':False,'reference_validation_pass':False,'validated':False})
            continue
        comp=qc[0];e,t,st=medoid(comp)
        row={'exec_min':ex,'execution_utc':cl(ex),'dev_eligible_cells':len(cells),'component_cells':len(comp),'component_entries':','.join(fl(v) for v in sorted({x[0] for x in comp},reverse=True)),'component_targets':','.join(tl(v) for v in sorted({x[1] for x in comp})),'component_stops':','.join(fl(v) for v in sorted({x[2] for x in comp},reverse=True)),'entry_f':e,'target_ext':t,'stop_f':st,'geometry':f'{fl(e)}/{tl(t)}/{fl(st)}','selected':True}
        allpass=True
        for p in ('external','reference_validation'):
            z=scores[(scores.exec_min==ex)&(scores.partition==p)&(scores.entry_f==e)&(scores.target_ext==t)&(scores.stop_f==st)]
            if z.empty:ok=False; vals={}
            else:
                r=z.iloc[0];ok=bool(r.n>=15 and r.wr>=.60 and r.pf>=1.25 and r.expectancy>0 and r.net>0);vals={'n':r.n,'wr':r.wr,'pf':r.pf,'expectancy':r.expectancy,'net':r.net}
            row[f'{p}_pass']=ok
            for k,v in vals.items():row[f'{p}_{k}']=v
            allpass &= ok
        row['validated']=allpass;rows.append(row)
    return pd.DataFrame(rows)
def build_candidates(x,sel):
    rows=[]
    for r in sel[sel.validated].itertuples(index=False):
        ex=int(r.exec_min);e=float(r.entry_f);t=float(r.target_ext);st=float(r.stop_f)
        for p in PARTS:
            sess=s4.b.sessions_for(x,p,ex,s4.REF_MIN,s4.HORIZON_MIN,'LONG',e)
            for q in sess:
                target=s4.b.target_level(q['L'],q['H'],'LONG',t);stop=s4.b.stop_level(q['L'],q['H'],st)
                d0=s4.score_trade_detail(x,q['exe'],q['fill_ts'],q['ee'],q['entry'],target,stop,0.);d5=s4.score_trade_detail(x,q['exe'],q['fill_ts'],q['ee'],q['entry'],target,stop,5.)
                if d0 is None or d5 is None:continue
                rows.append({'partition':p,'exec_min':ex,'execution_utc':cl(ex),'geometry':r.geometry,'entry_f':e,'target_ext':t,'stop_f':st,'execution_start':pd.Timestamp(q['es']),'entry_bar_start':pd.Timestamp(q['fill_ts']),'exit_ts':d0['exit_ts'],'exit_reason':d0['exit_reason'],'pnl_0':d0['pnl'],'pnl_5':d5['pnl']})
    c=pd.DataFrame(rows)
    for col in ('execution_start','entry_bar_start','exit_ts'):
        if col in c:c[col]=pd.to_datetime(c[col],utc=True)
    return c
def parity(x,c,sel):
    rows=[]
    for r in sel[sel.validated].itertuples(index=False):
        for p in PARTS:
            q=c[(c.exec_min==r.exec_min)&(c.partition==p)];calc=s4.metrics(q,'pnl_0');exp=s4.b.score_config(x=x,part_name=p,side='LONG',exec_min=int(r.exec_min),ref_min=s4.REF_MIN,horizon_min=s4.HORIZON_MIN,entry_f=float(r.entry_f),target_ext=float(r.target_ext),stop_f=float(r.stop_f),stress_bps=0.)
            for f in ('n','wins','wr','pf','expectancy','net'):
                a=float(calc[f]);b=float(exp[f]);ok=(math.isnan(a) and math.isnan(b)) or (math.isinf(a) and math.isinf(b)) or abs(a-b)<=1e-9;rows.append({'clock':r.execution_utc,'partition':p,'field':f,'calc':a,'expected':b,'pass':ok})
    return pd.DataFrame(rows)
def portfolio(c):
    if c.empty:return pd.DataFrame(),pd.DataFrame()
    decs=[];rows=[];mw=sum(s4.weeks_for(p) for p in PARTS)
    for p in PARTS:
        d=s4.lock_partition(c[c.partition==p].copy());decs.append(d);a=d[d.accepted].sort_values('entry_bar_start')
        for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
            m=s4.metrics(a,col);rows.append({'partition':p,'stress_bps':stress,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s4.weeks_for(p),**m})
    d=pd.concat(decs,ignore_index=True);a=d[d.accepted].sort_values('entry_bar_start')
    for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
        m=s4.metrics(a,col);rows.append({'partition':'POOLED_MAJOR','stress_bps':stress,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/mw,**m})
    return d,pd.DataFrame(rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    scores=load_scores();sel=select(scores);sel.to_csv(OUT_SEL,index=False);x,cov=s4.b.m.m.load5();c=build_candidates(x,sel);c.to_csv(OUT_CAND,index=False);par=parity(x,c,sel);par.to_csv(OUT_PARITY,index=False);parity_ok=bool(par['pass'].all()) if len(par) else bool(sel.validated.sum()==0);dec,sumdf=portfolio(c);dec.to_csv(OUT_DEC,index=False);sumdf.to_csv(OUT_SUM,index=False)
    nv=int(sel.validated.sum())
    if nv==0:status='ETH_S6A_NO_VALIDATED_HABITAT_GEOMETRY';btc=False;stress=False;positive=False;p0=None;p5=None
    else:
        p0=sumdf[(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==0)].iloc[0];p5=sumdf[(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==5)].iloc[0];maj=sumdf[(sumdf.partition.isin(PARTS))&(sumdf.stress_bps==0)];positive=bool(((maj.net>0)&(maj.pf>1)).all() and p0.net>0 and p0.pf>1);stress=bool(p5.net>=0 and p5.pf>=1);btc=bool(parity_ok and positive and stress and p0.wr>=BTC_WR and p0.pf>=BTC_PF and p0.expectancy>=BTC_EXP)
        status='ETH_S6A_HABITAT_GEOMETRY_BTC_QUALITY_SUPPORTED' if btc else ('ETH_S6A_HABITAT_GEOMETRY_POSITIVE_BELOW_BTC' if parity_ok and positive and stress else 'ETH_S6A_NO_VALIDATED_HABITAT_GEOMETRY')
    lines=['# ETH B27DX — S6A Habitat-Specific Geometry Calibration — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','', 'Selection uses Development only from the frozen 56-cell S3C family; validation cannot alter the selected geometry.','', '## Habitat selections','', '| Clock | Dev eligible | Component | Geometry | External pass | RefVal pass | Validated |','|---:|---:|---:|---|---|---|---|']
    for r in sel.itertuples(index=False):lines.append(f'| {r.execution_utc} | {int(r.dev_eligible_cells)} | {int(r.component_cells)} | {getattr(r,"geometry","-") if bool(r.selected) else "-"} | {"YES" if bool(r.external_pass) else "NO"} | {"YES" if bool(r.reference_validation_pass) else "NO"} | {"YES" if bool(r.validated) else "NO"} |')
    lines += ['','## Portfolio','']
    if nv==0:lines.append('No habitat geometry passed frozen validation.')
    else:
        lines += ['| Partition | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in (*PARTS,'POOLED_MAJOR'):
            for st in (0,5):
                r=sumdf[(sumdf.partition==p)&(sumdf.stress_bps==st)].iloc[0];lines.append(f'| {p} | {st} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
        lines += ['',f'- Candidate parity: **{"PASS" if parity_ok else "FAIL"}**.',f'- BTC-quality gate: **{"PASS" if btc else "FAIL"}**.',f'- 5 bps stress: **{"PASS" if stress else "FAIL"}**.']
    lines += ['','## Decision','',f'**Status: {status}**','', '- No new geometry values, runner, leverage, or live-code changes were introduced.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
