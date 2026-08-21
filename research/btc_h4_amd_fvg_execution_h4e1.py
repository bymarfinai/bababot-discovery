#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h4_amd_fvg_pathmap_h4p1 as h4p1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_H4_AMD_FVG_Execution_H4E1_Result.md'
OUT_JSON=ROOT/'BTC_H4_AMD_FVG_Execution_H4E1_Result.json'
OUT_EVENTS=ROOT/'BTC_H4_AMD_FVG_Execution_H4E1_Events.csv'
OUT_AUG=ROOT/'BTC_H4_AMD_FVG_Execution_H4E1_August.csv'
FEE=.0015; NOTIONAL=500.; HOLD=6

def pct(v):
    if v is None:return '-'
    try:
        if math.isnan(float(v)):return '-'
    except Exception:pass
    return f'{100*float(v):.2f}%'
def money(v): return f'${float(v):+.2f}'
def signed(side,e,f):
    r=f/e-1
    return r if side=='LONG' else -r

def enrich(x,ev):
    h4=h4p1.make_h4_builder(x); rows=[]
    for _,r in ev[ev.fvg].copy().iterrows():
        d=r.to_dict(); ts=pd.Timestamp(r.event_ts)+pd.Timedelta(hours=12)
        bars=[h4(ts+pd.Timedelta(hours=4*j)) for j in range(HOLD)]
        d.update(entry_ts=ts,entry=np.nan,sl=float(r.far),tp=float(r.opp_boundary),valid=False,risk=np.nan,reward=np.nan,net_rr=np.nan,rr_ok=False,outcome=None,pnl=np.nan)
        if any(b is None for b in bars): rows.append(d); continue
        entry=float(bars[0]['open']); sl=float(r.far); tp=float(r.opp_boundary); side=r.original_side
        d['entry']=entry
        if side=='LONG':
            valid=sl<entry<tp; risk=(entry-sl)/entry if valid else np.nan; reward=(tp-entry)/entry if valid else np.nan
        else:
            valid=tp<entry<sl; risk=(sl-entry)/entry if valid else np.nan; reward=(entry-tp)/entry if valid else np.nan
        d['valid']=bool(valid)
        if not valid: rows.append(d); continue
        d['risk']=risk; d['reward']=reward; d['net_rr']=(reward-FEE)/(risk+FEE); d['rr_ok']=bool(reward>=risk+2*FEE)
        out=None; raw=None
        for b in bars:
            sh=(b['low']<=sl) if side=='LONG' else (b['high']>=sl)
            th=(b['high']>=tp) if side=='LONG' else (b['low']<=tp)
            if sh: out='SL'; raw=-risk; break
            if th: out='TP'; raw=reward; break
        if out is None: out='TIME'; raw=signed(side,entry,float(bars[-1]['close']))
        d['outcome']=out; d['pnl']=(float(raw)-FEE)*NOTIONAL
        rows.append(d)
    return pd.DataFrame(rows)

def stats(z,primary=True):
    q=z[z.valid].copy()
    if primary:q=q[q.rr_ok]
    q=q[q.outcome.notna()]
    if q.empty:return dict(n=0,tp=0,sl=0,time=0,wr=None,pnl=0.,exp=None,medrisk=None,medrr=None)
    dec=q[q.outcome.isin(['TP','SL'])]
    return dict(n=len(q),tp=int((q.outcome=='TP').sum()),sl=int((q.outcome=='SL').sum()),time=int((q.outcome=='TIME').sum()),wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(q.pnl.sum()),exp=float(q.pnl.mean()),medrisk=float(q.risk.median()),medrr=float(q.net_rr.median()))

def blocks(z):
    q=z[z.valid & z.rr_ok & z.outcome.notna()].sort_values('event_ts').reset_index(drop=True)
    if q.empty:return []
    cuts=np.linspace(0,len(q),5,dtype=int); out=[]
    for i in range(4):
        p=q.iloc[cuts[i]:cuts[i+1]]; dec=p[p.outcome.isin(['TP','SL'])]
        out.append(dict(block=f'B{i+1}',n=len(p),decisive=len(dec),tp=int((p.outcome=='TP').sum()),sl=int((p.outcome=='SL').sum()),time=int((p.outcome=='TIME').sum()),wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(p.pnl.sum())))
    return out

def main():
    x=h4p1.load_source(); raw=h4p1.build_events(x); ev=enrich(x,raw)
    parts={
      'development':ev[(ev.event_ts>=h4p1.DEV0)&(ev.event_ts<h4p1.CUT)],
      'reference_validation':ev[(ev.event_ts>=h4p1.CUT)&(ev.event_ts<h4p1.REF1)],
      'external':ev[(ev.event_ts>=h4p1.EXT0)&(ev.event_ts<h4p1.EXT1)],
      'august':ev[(ev.event_ts>=h4p1.AUG0)&(ev.event_ts<h4p1.AUG1)]}
    agg={}
    for k,z in parts.items():
        agg[k]=dict(fvg_n=len(z),descriptive_opp_reach=float(z.opp_reached.mean()) if len(z) else None,valid=stats(z,False),primary=stats(z,True))
    matrix=[]
    for part,z in parts.items():
        for side in ['LONG','SHORT']:
            for sess in ['ASIA_OPEN','LONDON_OPEN','NEW_YORK_OPEN']:
                q=z[(z.original_side==side)&(z.session==sess)]
                matrix.append(dict(partition=part,side=side,session=sess,fvg_n=len(q),primary=stats(q,True)))
    eb=blocks(parts['external']); v=agg['reference_validation']['primary']; e=agg['external']['primary']
    pos=sum(b['pnl']>0 for b in eb)
    support=v['n']>=15 and (v['wr'] or 0)>.50 and v['pnl']>0 and e['n']>=20 and (e['wr'] or 0)>.50 and e['pnl']>0 and pos>=3
    b80=sum(b['decisive']>=4 and (b['wr'] or 0)>=.70 for b in eb)
    c80=v['n']>=15 and (v['wr'] or 0)>=.80 and e['n']>=20 and (e['wr'] or 0)>=.80 and b80>=3
    ev.to_csv(OUT_EVENTS,index=False); parts['august'].to_csv(OUT_AUG,index=False)
    res=dict(protocol='BTC_H4_AMD_FVG_EXECUTION_H4E1',coverage=dict(first=str(x.ts.min()),last=str(x.ts.max()),source_1h_rows=len(x)),aggregate=agg,matrix=matrix,external_blocks=eb,H4E1_EXECUTION_SUPPORTED=bool(support),H4E1_80_CANDIDATE=bool(c80))
    OUT_JSON.write_text(json.dumps(res,indent=2,default=str)+'\n')
    md=['# BTC H4 AMD + FVG Execution H4E1 — Result','', 'Frozen execution: exact session-anchored H4 AMD/FVG -> enter next H4 open -> SL FAR FVG edge -> TP opposite accumulation boundary -> max24H. Same-H4 ambiguity adverse-first. Primary cohort requires modeled net RR>=1:1 after 0.15% round-trip fee.','',f"Coverage **{x.ts.min()} -> {x.ts.max()}**, official 1H rows **{len(x):,}**.",'','## Aggregate','', '| Partition | Exact FVG | Descriptive opp reach | Valid N/WR/PnL | RR>=1 N | TP/SL/TIME | WR | PnL | Exp | Med risk | Med net RR |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ['development','reference_validation','external','august']:
        a=agg[p]; d=a['valid']; s=a['primary']; exp='-' if s['exp'] is None else money(s['exp']); rr='-' if s['medrr'] is None else f"{s['medrr']:.2f}"
        md.append(f"| {p} | {a['fvg_n']} | {pct(a['descriptive_opp_reach'])} | {d['n']}/{pct(d['wr'])}/{money(d['pnl'])} | {s['n']} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {money(s['pnl'])} | {exp} | {pct(s['medrisk'])} | {rr} |")
    for part,title in [('reference_validation','Reference validation'),('external','External 2020-2021')]:
        md += ['',f'## {title} primary by fixed side/session','', '| Side | Session | FVG | RR>=1 N | TP/SL/TIME | WR | PnL |','|---|---|---:|---:|---:|---:|---:|']
        for r in matrix:
            if r['partition']!=part:continue
            s=r['primary']; md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {s['n']} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {money(s['pnl'])} |")
    md += ['','## External chronological primary blocks','', '| Block | N | TP | SL | TIME | WR | PnL |','|---|---:|---:|---:|---:|---:|---:|']
    for b in eb: md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")
    md += ['','## Verdicts','',f"**H4E1_EXECUTION_SUPPORTED: {'PASS' if support else 'FAIL'}**",f"**H4E1_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**",'','No post-result entry-depth, stop-buffer, target, hold, side/session, gap-size, weekday, volatility, or accumulation/FVG retuning.']
    OUT_MD.write_text('\n'.join(md)+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()

# no-op retrigger marker; frozen H4E1 logic unchanged
