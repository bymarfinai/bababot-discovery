#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_amd_fvg_amd1 as amd1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_H1_AMD_FVG_Mitigation_AMD2_Result.md'
OUT_JSON=ROOT/'BTC_H1_AMD_FVG_Mitigation_AMD2_Result.json'
OUT_EVENTS=ROOT/'BTC_H1_AMD_FVG_Mitigation_AMD2_Events.csv'
OUT_AUG=ROOT/'BTC_H1_AMD_FVG_Mitigation_AMD2_August.csv'
EXT0=pd.Timestamp('2020-01-01T00:00:00Z'); EXT1=pd.Timestamp('2022-01-01T00:00:00Z')
REF0=pd.Timestamp('2022-01-01T00:00:00Z'); CUT=pd.Timestamp('2025-03-18T00:00:00Z'); REF1=pd.Timestamp('2026-07-30T00:00:00Z')
AUG0=pd.Timestamp('2026-08-01T00:00:00Z'); AUG1=pd.Timestamp('2026-08-20T00:00:00Z')
FEE=.0015; NOTIONAL=500.; WINDOW=6; HOLD=6

def pct(v):
    if v is None:return '-'
    try:
        if math.isnan(float(v)):return '-'
    except:pass
    return f'{100*float(v):.2f}%'
def money(v):return f'${float(v):+.2f}'

def fill_info(x,r):
    start=int(r.fvg_entry_idx)
    entry=float(r.fvg_low if r.side=='SHORT' else r.fvg_high)
    for idx in range(start,start+WINDOW):
        if idx>=len(x):break
        if pd.Timestamp(x.ts.iloc[idx]) != pd.Timestamp(x.ts.iloc[start])+pd.Timedelta(hours=idx-start):return None,None
        hit=float(x.high.iloc[idx])>=entry if r.side=='SHORT' else float(x.low.iloc[idx])<=entry
        if hit:return idx,entry
    return None,None

def signed(side,entry,final):
    r=final/entry-1
    return r if side=='LONG' else -r

def run_target(x,side,idx,entry,sl,tp,risk,td):
    f=x.iloc[idx:idx+HOLD]
    if len(f)!=HOLD:return None
    for j in range(HOLD):
        if pd.Timestamp(f.ts.iloc[j]) != pd.Timestamp(x.ts.iloc[idx])+pd.Timedelta(hours=j):return None
    def sh(b):return float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
    def th(b):return float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
    if sh(f.iloc[0]):out='SL'; raw=-risk
    else:
        out=None; raw=None
        for j in range(1,HOLD):
            b=f.iloc[j]
            if sh(b):out='SL'; raw=-risk; break
            if th(b):out='TP'; raw=td; break
        if out is None:out='TIME'; raw=signed(side,entry,float(f.close.iloc[-1]))
    net=float(raw)-FEE
    return out,net,net*NOTIONAL

def enrich(x,base):
    rows=[]
    for _,r in base[base.fvg].copy().iterrows():
        d=r.to_dict(); idx,entry=fill_info(x,r)
        d.update(fill=idx is not None,fill_idx=np.nan if idx is None else idx,fill_ts=pd.NaT if idx is None else x.ts.iloc[idx],entry=np.nan if entry is None else entry,
                 valid=False,risk=np.nan,dist_tp=np.nan,dist_d=np.nan,dist_rr=np.nan,rr_ok=False,dist_out=None,dist_pnl=np.nan,net1r_out=None,net1r_pnl=np.nan)
        if idx is None:rows.append(d);continue
        if r.side=='LONG':
            sl=float(r.manip_low)
            if entry<=sl:rows.append(d);continue
            risk=(entry-sl)/entry; tp=float(r.acc_high); td=(tp-entry)/entry if tp>entry else -1; t1=entry*(1+risk+2*FEE)
        else:
            sl=float(r.manip_high)
            if entry>=sl:rows.append(d);continue
            risk=(sl-entry)/entry; tp=float(r.acc_low); td=(entry-tp)/entry if tp<entry else -1; t1=entry*(1-risk-2*FEE)
        d['valid']=True;d['risk']=risk;d['dist_tp']=tp;d['dist_d']=td;d['dist_rr']=((td-FEE)/(risk+FEE) if td>0 else np.nan);d['rr_ok']=bool(td>=risk+2*FEE)
        q=run_target(x,r.side,int(idx),entry,sl,t1,risk,risk+2*FEE)
        if q:d['net1r_out'],_,d['net1r_pnl']=q
        if d['rr_ok']:
            q=run_target(x,r.side,int(idx),entry,sl,tp,risk,td)
            if q:d['dist_out'],_,d['dist_pnl']=q
        rows.append(d)
    return pd.DataFrame(rows)

def stats(z,kind):
    if kind=='dist':q=z[z.rr_ok & z.dist_out.notna()].copy();oc='dist_out';pc='dist_pnl'
    else:q=z[z.valid & z.net1r_out.notna()].copy();oc='net1r_out';pc='net1r_pnl'
    if q.empty:return dict(n=0,tp=0,sl=0,time=0,wr=None,pnl=0.,exp=None,medrisk=None,medrr=None)
    dec=q[q[oc].isin(['TP','SL'])]
    return dict(n=len(q),tp=int((q[oc]=='TP').sum()),sl=int((q[oc]=='SL').sum()),time=int((q[oc]=='TIME').sum()),wr=float((dec[oc]=='TP').mean()) if len(dec) else None,pnl=float(q[pc].sum()),exp=float(q[pc].mean()),medrisk=float(q.risk.median()),medrr=(float(q.dist_rr.median()) if kind=='dist' else 1.0))
def cohort(z):
    f=len(z);filled=int(z['fill'].sum()) if f else 0; rr=int(z.rr_ok.sum()) if f else 0
    return dict(fvg_n=f,filled_n=filled,fill_rate=filled/f if f else None,rr_n=rr,dist=stats(z,'dist'),net1r=stats(z,'1r'))
def blocks(z,kind):
    if kind=='dist':q=z[z.rr_ok & z.dist_out.notna()].sort_values('event_ts').reset_index(drop=True);oc='dist_out';pc='dist_pnl'
    else:q=z[z.valid & z.net1r_out.notna()].sort_values('event_ts').reset_index(drop=True);oc='net1r_out';pc='net1r_pnl'
    if q.empty:return []
    b=np.linspace(0,len(q),5,dtype=int);out=[]
    for j in range(4):
        p=q.iloc[b[j]:b[j+1]];dec=p[p[oc].isin(['TP','SL'])]
        out.append(dict(block=f'B{j+1}',n=len(p),tp=int((p[oc]=='TP').sum()),sl=int((p[oc]=='SL').sum()),time=int((p[oc]=='TIME').sum()),wr=float((dec[oc]=='TP').mean()) if len(dec) else None,pnl=float(p[pc].sum())))
    return out

def main():
    x=amd1.dataio.load_1h(); base=amd1.build_events(x); ev=enrich(x,base)
    parts={'development':ev[(ev.event_ts>=REF0)&(ev.event_ts<CUT)],'reference_validation':ev[(ev.event_ts>=CUT)&(ev.event_ts<REF1)],'external':ev[(ev.event_ts>=EXT0)&(ev.event_ts<EXT1)],'august':ev[(ev.event_ts>=AUG0)&(ev.event_ts<AUG1)]}
    ev.to_csv(OUT_EVENTS,index=False);parts['august'].to_csv(OUT_AUG,index=False)
    agg={k:cohort(v) for k,v in parts.items()}
    matrix=[]
    for part,z in parts.items():
        for side in ['LONG','SHORT']:
            for sess in ['ASIA_OPEN','LONDON_OPEN','NEW_YORK_OPEN']:
                q=z[(z.side==side)&(z.session==sess)];matrix.append(dict(partition=part,side=side,session=sess,**cohort(q)))
    db=blocks(parts['external'],'dist'); rb=blocks(parts['external'],'1r')
    vd,ed=agg['reference_validation']['dist'],agg['external']['dist'];v1,e1=agg['reference_validation']['net1r'],agg['external']['net1r']
    dist_pass=vd['n']>=25 and (vd['wr'] or 0)>=.60 and vd['pnl']>0 and ed['n']>=40 and (ed['wr'] or 0)>=.60 and ed['pnl']>0 and sum(b['n']>=8 and b['pnl']>0 for b in db)>=3
    c80=vd['n']>=20 and (vd['wr'] or 0)>=.80 and vd['pnl']>0 and ed['n']>=30 and (ed['wr'] or 0)>=.80 and ed['pnl']>0 and sum(b['n']>=5 and (b['wr'] or 0)>=.70 for b in db)>=3
    rpass=v1['n']>=25 and (v1['wr'] or 0)>=.60 and v1['pnl']>0 and e1['n']>=40 and (e1['wr'] or 0)>=.60 and e1['pnl']>0 and sum(b['n']>=8 and b['pnl']>0 for b in rb)>=3
    res=dict(protocol='BTC_H1_AMD_FVG_MITIGATION_AMD2',coverage=dict(first=str(x.ts.min()),last=str(x.ts.max()),rows=len(x)),reference_cut=str(CUT),exact_fvg_total=len(ev),aggregate=agg,matrix=matrix,external_distribution_blocks=db,external_net1r_blocks=rb,AMD2_DISTRIBUTION_SUPPORTED=bool(dist_pass),AMD2_80_CANDIDATE=bool(c80),AMD2_NET1R_SUPPORTED=bool(rpass))
    OUT_JSON.write_text(json.dumps(res,indent=2,default=str)+'\n')
    md=['# BTC H1 AMD + FVG Mitigation AMD2 — Result','', '1H-only: accumulation -> manipulation -> exact opposite FVG -> wait max6H for first FVG-boundary mitigation -> limit entry. Primary TP = opposite accumulation boundary only if net RR>=1:1 after 0.15% fee. Fill-candle TP is not credited; fill-candle SL is adverse-first.','',f'Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**, exact FVG events **{len(ev)}**.','', '## Aggregate','', '| Partition | FVG | Filled | Fill rate | RR-eligible | Dist TP/SL/TIME | Dist WR | Dist PnL | Dist Exp | Med risk | Med net RR | Net1R N/WR/PnL |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ['development','reference_validation','external','august']:
        s=agg[p];d=s['dist'];n=s['net1r']; medrr='-' if d['medrr'] is None else f"{d['medrr']:.2f}"; de='-' if d['exp'] is None else money(d['exp'])
        md.append(f"| {p} | {s['fvg_n']} | {s['filled_n']} | {pct(s['fill_rate'])} | {s['rr_n']} | {d['tp']}/{d['sl']}/{d['time']} | {pct(d['wr'])} | {money(d['pnl'])} | {de} | {pct(d['medrisk'])} | {medrr} | {n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |")
    for part,title in [('reference_validation','Reference validation by side/session'),('external','External 2020-2021 by side/session')]:
        md += ['',f'## {title}','', '| Side | Session | FVG | Fill rate | RR-eligible | Dist WR/PnL | Net1R N/WR/PnL |','|---|---|---:|---:|---:|---:|---:|']
        for r in matrix:
            if r['partition']!=part:continue
            d=r['dist'];n=r['net1r'];md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {pct(r['fill_rate'])} | {r['rr_n']} | {pct(d['wr'])}/{money(d['pnl'])} | {n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |")
    for bs,title in [(db,'External Distribution blocks'),(rb,'External net1R blocks')]:
        md += ['',f'## {title}','', '| Block | N | TP | SL | TIME | WR | PnL |','|---|---:|---:|---:|---:|---:|---:|']
        for b in bs:md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")
    md += ['','## Verdicts','',f"**AMD2_DISTRIBUTION_SUPPORTED: {'PASS' if dist_pass else 'FAIL'}**",f"**AMD2_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**",f"**AMD2_NET1R_SUPPORTED: {'PASS' if rpass else 'FAIL'}**",'','No post-result midpoint/partial-FVG entry, later-FVG search, clock/side carve-out, accumulation-length change, or mitigation-window retuning.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
