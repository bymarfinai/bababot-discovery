#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_amd_fvg_amd1 as amd1
import btc_h1_amd_fvg_mitigation_amd2_runner as amd2

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_H1_AMD_FVG_DistributionExpansion_AMD3_Result.md'
OUT_JSON=ROOT/'BTC_H1_AMD_FVG_DistributionExpansion_AMD3_Result.json'
OUT_EVENTS=ROOT/'BTC_H1_AMD_FVG_DistributionExpansion_AMD3_Events.csv'
OUT_AUG=ROOT/'BTC_H1_AMD_FVG_DistributionExpansion_AMD3_August.csv'
EXT0=pd.Timestamp('2020-01-01T00:00:00Z'); EXT1=pd.Timestamp('2022-01-01T00:00:00Z')
REF0=pd.Timestamp('2022-01-01T00:00:00Z'); CUT=pd.Timestamp('2025-03-18T00:00:00Z'); REF1=pd.Timestamp('2026-07-30T00:00:00Z')
AUG0=pd.Timestamp('2026-08-01T00:00:00Z'); AUG1=pd.Timestamp('2026-08-20T00:00:00Z')
FEE=.0015; NOTIONAL=500.

def pct(v):
    if v is None:return '-'
    try:
        if math.isnan(float(v)):return '-'
    except Exception:pass
    return f'{100*float(v):.2f}%'
def money(v):return f'${float(v):+.2f}'

def enrich(x,base):
    rows=[]
    for _,r in base[base.fvg].copy().iterrows():
        d=r.to_dict(); idx,entry=amd2.fill_info(x,r)
        d.update(fill=idx is not None,fill_idx=np.nan if idx is None else idx,fill_ts=pd.NaT if idx is None else x.ts.iloc[idx],entry=np.nan if entry is None else entry,
                 valid=False,risk=np.nan,range_size=float(r.acc_high-r.acc_low),exp_tp=np.nan,exp_d=np.nan,exp_rr=np.nan,rr_ok=False,exp_out=None,exp_pnl=np.nan,
                 boundary_out=None,boundary_pnl=np.nan,net1r_out=None,net1r_pnl=np.nan)
        if idx is None:rows.append(d);continue
        side=str(r.side); rng=float(r.acc_high-r.acc_low)
        if rng<=0:rows.append(d);continue
        if side=='LONG':
            sl=float(r.manip_low)
            if entry<=sl:rows.append(d);continue
            risk=(entry-sl)/entry
            tp=float(r.acc_high+rng); td=(tp-entry)/entry if tp>entry else -1
            btp=float(r.acc_high); bd=(btp-entry)/entry if btp>entry else -1
            t1=entry*(1+risk+2*FEE)
        else:
            sl=float(r.manip_high)
            if entry>=sl:rows.append(d);continue
            risk=(sl-entry)/entry
            tp=float(r.acc_low-rng); td=(entry-tp)/entry if tp<entry else -1
            btp=float(r.acc_low); bd=(entry-btp)/entry if btp<entry else -1
            t1=entry*(1-risk-2*FEE)
        d['valid']=True; d['risk']=risk; d['exp_tp']=tp; d['exp_d']=td
        d['exp_rr']=((td-FEE)/(risk+FEE) if td>0 else np.nan); d['rr_ok']=bool(td>=risk+2*FEE)
        q=amd2.run_target(x,side,int(idx),entry,sl,t1,risk,risk+2*FEE)
        if q:d['net1r_out'],_,d['net1r_pnl']=q
        if bd>0:
            q=amd2.run_target(x,side,int(idx),entry,sl,btp,risk,bd)
            if q:d['boundary_out'],_,d['boundary_pnl']=q
        if d['rr_ok']:
            q=amd2.run_target(x,side,int(idx),entry,sl,tp,risk,td)
            if q:d['exp_out'],_,d['exp_pnl']=q
        rows.append(d)
    return pd.DataFrame(rows)

def stats(z,kind):
    if kind=='exp':q=z[z.rr_ok & z.exp_out.notna()].copy();oc='exp_out';pc='exp_pnl';rr='exp_rr'
    elif kind=='boundary':q=z[z.valid & z.boundary_out.notna()].copy();oc='boundary_out';pc='boundary_pnl';rr=None
    else:q=z[z.valid & z.net1r_out.notna()].copy();oc='net1r_out';pc='net1r_pnl';rr=None
    if q.empty:return dict(n=0,tp=0,sl=0,time=0,wr=None,pnl=0.,exp=None,medrisk=None,medrr=None)
    dec=q[q[oc].isin(['TP','SL'])]
    return dict(n=int(len(q)),tp=int((q[oc]=='TP').sum()),sl=int((q[oc]=='SL').sum()),time=int((q[oc]=='TIME').sum()),wr=float((dec[oc]=='TP').mean()) if len(dec) else None,
                pnl=float(q[pc].sum()),exp=float(q[pc].mean()),medrisk=float(q.risk.median()),medrr=(float(q[rr].median()) if rr else None))

def cohort(z):
    n=len(z);fills=int(z['fill'].sum()) if n else 0;rr=int(z.rr_ok.sum()) if n else 0
    return dict(fvg_n=n,filled_n=fills,fill_rate=fills/n if n else None,rr_n=rr,rr_rate=rr/n if n else None,expansion=stats(z,'exp'),boundary=stats(z,'boundary'),net1r=stats(z,'1r'))

def blocks(z):
    q=z[z.rr_ok & z.exp_out.notna()].sort_values('event_ts').reset_index(drop=True)
    if q.empty:return []
    b=np.linspace(0,len(q),5,dtype=int);out=[]
    for j in range(4):
        p=q.iloc[b[j]:b[j+1]];dec=p[p.exp_out.isin(['TP','SL'])]
        out.append(dict(block=f'B{j+1}',n=int(len(p)),tp=int((p.exp_out=='TP').sum()),sl=int((p.exp_out=='SL').sum()),time=int((p.exp_out=='TIME').sum()),wr=float((dec.exp_out=='TP').mean()) if len(dec) else None,pnl=float(p.exp_pnl.sum())))
    return out

def main():
    x=amd1.dataio.load_1h(); base=amd1.build_events(x); ev=enrich(x,base)
    if ev.empty:raise RuntimeError('no exact AMD+FVG events')
    parts={'development':ev[(ev.event_ts>=REF0)&(ev.event_ts<CUT)],'reference_validation':ev[(ev.event_ts>=CUT)&(ev.event_ts<REF1)],'external':ev[(ev.event_ts>=EXT0)&(ev.event_ts<EXT1)],'august':ev[(ev.event_ts>=AUG0)&(ev.event_ts<AUG1)]}
    ev.to_csv(OUT_EVENTS,index=False);parts['august'].to_csv(OUT_AUG,index=False)
    agg={k:cohort(v) for k,v in parts.items()}
    matrix=[]
    for part,z in parts.items():
        for side in ['LONG','SHORT']:
            for sess in ['ASIA_OPEN','LONDON_OPEN','NEW_YORK_OPEN']:
                q=z[(z.side==side)&(z.session==sess)];matrix.append(dict(partition=part,side=side,session=sess,**cohort(q)))
    eb=blocks(parts['external']); vd=agg['reference_validation']['expansion']; ed=agg['external']['expansion']
    support=vd['n']>=25 and (vd['wr'] or 0)>=.60 and vd['pnl']>0 and ed['n']>=40 and (ed['wr'] or 0)>=.60 and ed['pnl']>0 and sum(b['n']>=8 and b['pnl']>0 for b in eb)>=3
    c80=vd['n']>=20 and (vd['wr'] or 0)>=.80 and vd['pnl']>0 and ed['n']>=30 and (ed['wr'] or 0)>=.80 and ed['pnl']>0 and sum(b['n']>=5 and (b['wr'] or 0)>=.70 for b in eb)>=3
    res=dict(protocol='BTC_H1_AMD_FVG_DISTRIBUTION_EXPANSION_AMD3',coverage=dict(first=str(x.ts.min()),last=str(x.ts.max()),rows=len(x)),reference_cut=str(CUT),exact_fvg_total=len(ev),aggregate=agg,matrix=matrix,external_blocks=eb,AMD3_EXPANSION_SUPPORTED=bool(support),AMD3_80_CANDIDATE=bool(c80))
    OUT_JSON.write_text(json.dumps(res,indent=2,default=str)+'\n')
    md=['# BTC H1 AMD + FVG Distribution Expansion AMD3 — Result','', 'Frozen 1H AMD2 entry geometry retained. New primary Distribution TP = one full accumulation-range extension beyond the opposite accumulation boundary. Only trades with modeled net RR>=1:1 after 0.15% fee are eligible.','',f'Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**, exact FVG events **{len(ev)}**.','', '## Aggregate','', '| Partition | FVG | Filled | Fill rate | RR-eligible | Expansion TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR | Opp-boundary N/WR | Net1R N/WR/PnL |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ['development','reference_validation','external','august']:
        s=agg[p];e=s['expansion'];b=s['boundary'];n=s['net1r'];medrr='-' if e['medrr'] is None else f"{e['medrr']:.2f}";ex='-' if e['exp'] is None else money(e['exp'])
        md.append(f"| {p} | {s['fvg_n']} | {s['filled_n']} | {pct(s['fill_rate'])} | {s['rr_n']} | {e['tp']}/{e['sl']}/{e['time']} | {pct(e['wr'])} | {money(e['pnl'])} | {ex} | {pct(e['medrisk'])} | {medrr} | {b['n']}/{pct(b['wr'])} | {n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |")
    for part,title in [('reference_validation','Reference validation by side/session'),('external','External 2020-2021 by side/session')]:
        md += ['',f'## {title}','', '| Side | Session | FVG | Fill | RR-eligible | Expansion WR/PnL | Opp-boundary WR | Net1R WR/PnL |','|---|---|---:|---:|---:|---:|---:|---:|']
        for r in matrix:
            if r['partition']!=part:continue
            e=r['expansion'];b=r['boundary'];n=r['net1r'];md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {pct(r['fill_rate'])} | {r['rr_n']} | {pct(e['wr'])}/{money(e['pnl'])} | {pct(b['wr'])} | {pct(n['wr'])}/{money(n['pnl'])} |")
    md += ['','## External chronological blocks — measured Distribution expansion','', '| Block | N | TP | SL | TIME | WR | PnL |','|---|---:|---:|---:|---:|---:|---:|']
    for b in eb:md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")
    md += ['','## Verdicts','',f"**AMD3_EXPANSION_SUPPORTED: {'PASS' if support else 'FAIL'}**",f"**AMD3_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**",'','No post-result expansion-multiple tuning, entry-depth tuning, side/session carve-out, or AMD/FVG geometry changes.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
