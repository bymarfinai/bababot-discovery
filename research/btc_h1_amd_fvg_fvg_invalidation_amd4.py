#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_amd_fvg_amd1 as amd1
import btc_h1_amd_fvg_mitigation_amd2_runner as amd2

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_H1_AMD_FVG_FVGInvalidation_AMD4_Result.md'
OUT_JSON=ROOT/'BTC_H1_AMD_FVG_FVGInvalidation_AMD4_Result.json'
OUT_EVENTS=ROOT/'BTC_H1_AMD_FVG_FVGInvalidation_AMD4_Events.csv'
OUT_AUG=ROOT/'BTC_H1_AMD_FVG_FVGInvalidation_AMD4_August.csv'
EXT0=pd.Timestamp('2020-01-01T00:00:00Z'); EXT1=pd.Timestamp('2022-01-01T00:00:00Z')
REF0=pd.Timestamp('2022-01-01T00:00:00Z'); CUT=pd.Timestamp('2025-03-18T00:00:00Z'); REF1=pd.Timestamp('2026-07-30T00:00:00Z')
AUG0=pd.Timestamp('2026-08-01T00:00:00Z'); AUG1=pd.Timestamp('2026-08-20T00:00:00Z')
FEE=.0015; NOTIONAL=500.0

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
        d.update(fill=idx is not None,fill_idx=np.nan if idx is None else int(idx),fill_ts=pd.NaT if idx is None else pd.Timestamp(x.ts.iloc[idx]),entry=np.nan if entry is None else float(entry),
                 fvg_stop_valid=False,fvg_stop=np.nan,fvg_risk=np.nan,target=np.nan,target_dist=np.nan,net_rr=np.nan,rr_ok=False,
                 outcome=None,net_ret=np.nan,pnl=np.nan,control_manip_risk=np.nan,control_rr_ok=False)
        if idx is None or entry is None:
            rows.append(d);continue
        side=str(r.side)
        if side=='SHORT':
            sl=float(r.fvg_high)  # far/upper FVG edge = manipulation low
            tp=float(r.acc_low)
            if not (sl>entry and tp<entry):
                rows.append(d);continue
            risk=(sl-entry)/entry; td=(entry-tp)/entry
            old_sl=float(r.manip_high); old_risk=(old_sl-entry)/entry if old_sl>entry else np.nan
        else:
            sl=float(r.fvg_low)   # far/lower FVG edge = manipulation high
            tp=float(r.acc_high)
            if not (sl<entry and tp>entry):
                rows.append(d);continue
            risk=(entry-sl)/entry; td=(tp-entry)/entry
            old_sl=float(r.manip_low); old_risk=(entry-old_sl)/entry if old_sl<entry else np.nan
        d['fvg_stop_valid']=bool(risk>0); d['fvg_stop']=sl; d['fvg_risk']=risk; d['target']=tp; d['target_dist']=td
        d['net_rr']=((td-FEE)/(risk+FEE)) if risk>0 else np.nan
        d['rr_ok']=bool(td >= risk + 2*FEE)
        d['control_manip_risk']=old_risk
        d['control_rr_ok']=bool(pd.notna(old_risk) and td >= float(old_risk)+2*FEE)
        if d['rr_ok']:
            q=amd2.run_target(x,side,int(idx),float(entry),float(sl),float(tp),float(risk),float(td))
            if q is not None:
                out,net,pnl=q
                d['outcome']=out;d['net_ret']=net;d['pnl']=pnl
        rows.append(d)
    return pd.DataFrame(rows)

def stats(z):
    q=z[z.rr_ok & z.outcome.notna()].copy()
    if q.empty:return dict(n=0,tp=0,sl=0,time=0,wr=None,pnl=0.,exp=None,medrisk=None,medrr=None,positive=None)
    dec=q[q.outcome.isin(['TP','SL'])]
    return dict(n=int(len(q)),tp=int((q.outcome=='TP').sum()),sl=int((q.outcome=='SL').sum()),time=int((q.outcome=='TIME').sum()),
                wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(q.pnl.sum()),exp=float(q.pnl.mean()),
                medrisk=float(q.fvg_risk.median()),medrr=float(q.net_rr.median()),positive=float((q.net_ret>0).mean()))

def cohort(z):
    n=len(z);fills=int(z['fill'].sum()) if n else 0;valid=int(z.fvg_stop_valid.sum()) if n else 0;rr=int(z.rr_ok.sum()) if n else 0;ctrl=int(z.control_rr_ok.sum()) if n else 0
    return dict(fvg_n=int(n),filled_n=fills,fill_rate=fills/n if n else None,valid_n=valid,rr_n=rr,rr_rate=rr/n if n else None,control_manip_rr_n=ctrl,trade=stats(z))

def blocks(z):
    q=z[z.rr_ok & z.outcome.notna()].sort_values('event_ts').reset_index(drop=True)
    if q.empty:return []
    b=np.linspace(0,len(q),5,dtype=int);out=[]
    for j in range(4):
        p=q.iloc[b[j]:b[j+1]].copy();dec=p[p.outcome.isin(['TP','SL'])]
        out.append(dict(block=f'B{j+1}',n=int(len(p)),tp=int((p.outcome=='TP').sum()),sl=int((p.outcome=='SL').sum()),time=int((p.outcome=='TIME').sum()),
                        wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(p.pnl.sum())))
    return out

def main():
    x=amd1.dataio.load_1h();base=amd1.build_events(x);ev=enrich(x,base)
    if ev.empty:raise RuntimeError('no AMD+FVG events')
    parts={'development':ev[(ev.event_ts>=REF0)&(ev.event_ts<CUT)].copy(),
           'reference_validation':ev[(ev.event_ts>=CUT)&(ev.event_ts<REF1)].copy(),
           'external':ev[(ev.event_ts>=EXT0)&(ev.event_ts<EXT1)].copy(),
           'august':ev[(ev.event_ts>=AUG0)&(ev.event_ts<AUG1)].copy()}
    ev.to_csv(OUT_EVENTS,index=False);parts['august'].to_csv(OUT_AUG,index=False)
    agg={k:cohort(v) for k,v in parts.items()}
    matrix=[]
    for part,z in parts.items():
        for side in ['LONG','SHORT']:
            for sess in ['ASIA_OPEN','LONDON_OPEN','NEW_YORK_OPEN']:
                q=z[(z.side==side)&(z.session==sess)].copy();matrix.append(dict(partition=part,side=side,session=sess,**cohort(q)))
    eb=blocks(parts['external']);v=agg['reference_validation']['trade'];e=agg['external']['trade']
    pass_blocks=sum(b['n']>=8 and b['pnl']>0 for b in eb)
    supported=bool(v['n']>=25 and v['wr'] is not None and v['wr']>=.60 and v['pnl']>0 and e['n']>=40 and e['wr'] is not None and e['wr']>=.60 and e['pnl']>0 and pass_blocks>=3)
    pass80=sum(b['n']>=5 and b['wr'] is not None and b['wr']>=.70 for b in eb)
    cand80=bool(v['n']>=20 and v['wr'] is not None and v['wr']>=.80 and v['pnl']>0 and e['n']>=30 and e['wr'] is not None and e['wr']>=.80 and e['pnl']>0 and pass80>=3)
    res=dict(protocol='BTC_H1_AMD_FVG_FVG_INVALIDATION_AMD4',coverage=dict(first=str(x.ts.min()),last=str(x.ts.max()),rows=int(len(x))),exact_fvg_total=int(len(ev)),aggregate=agg,matrix=matrix,external_blocks=eb,AMD4_FVG_STOP_SUPPORTED=supported,AMD4_80_CANDIDATE=cand80)
    OUT_JSON.write_text(json.dumps(res,indent=2,default=str)+'\n')
    md=['# BTC H1 AMD + FVG Invalidation Stop AMD4 — Result','',
        'Frozen AMD2 entry geometry retained: exact 1H AMD+FVG -> first near-edge mitigation within 6H. New risk definition only: SL at far FVG edge. TP = opposite accumulation boundary. Only net-RR>=1:1 trades after 0.15% fee are eligible. Fill-candle TP not credited; fill-candle SL adverse-first.','',
        f'Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**, exact FVG events **{len(ev)}**.','',
        '## Aggregate','',
        '| Partition | FVG | Filled | Fill rate | FVG-stop valid | RR-eligible | Manip-stop eligible control | TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ['development','reference_validation','external','august']:
        s=agg[p];t=s['trade'];ex='-' if t['exp'] is None else money(t['exp']);mr='-' if t['medrr'] is None else f"{t['medrr']:.2f}"
        md.append(f"| {p} | {s['fvg_n']} | {s['filled_n']} | {pct(s['fill_rate'])} | {s['valid_n']} | {s['rr_n']} | {s['control_manip_rr_n']} | {t['tp']}/{t['sl']}/{t['time']} | {pct(t['wr'])} | {money(t['pnl'])} | {ex} | {pct(t['medrisk'])} | {mr} |")
    for part,title in [('reference_validation','Reference validation by side/session'),('external','External 2020-2021 by side/session')]:
        md += ['',f'## {title}','','| Side | Session | FVG | Fill rate | RR-eligible | Manip-stop eligible | TP/SL/TIME | WR | PnL |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in matrix:
            if r['partition']!=part:continue
            t=r['trade'];md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {pct(r['fill_rate'])} | {r['rr_n']} | {r['control_manip_rr_n']} | {t['tp']}/{t['sl']}/{t['time']} | {pct(t['wr'])} | {money(t['pnl'])} |")
    md += ['','## External chronological blocks','','| Block | N | TP | SL | TIME | WR | PnL |','|---|---:|---:|---:|---:|---:|---:|']
    for b in eb:md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")
    md += ['','## Verdicts','',f"**AMD4_FVG_STOP_SUPPORTED: {'PASS' if supported else 'FAIL'}**",f"**AMD4_80_CANDIDATE: {'PASS' if cand80 else 'FAIL'}**",'',
           'No post-result stop buffer, FVG-depth entry, target, side/session, accumulation, later-FVG, or timing retuning.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
