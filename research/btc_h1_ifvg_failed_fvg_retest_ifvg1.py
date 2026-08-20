#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_amd_fvg_amd1 as amd1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_H1_IFVG_FailedFVG_Retest_IFVG1_Result.md'
OUT_JSON=ROOT/'BTC_H1_IFVG_FailedFVG_Retest_IFVG1_Result.json'
OUT_EVENTS=ROOT/'BTC_H1_IFVG_FailedFVG_Retest_IFVG1_Events.csv'
OUT_AUG=ROOT/'BTC_H1_IFVG_FailedFVG_Retest_IFVG1_August.csv'
EXT0=pd.Timestamp('2020-01-01T00:00:00Z'); EXT1=pd.Timestamp('2022-01-01T00:00:00Z')
REF0=pd.Timestamp('2022-01-01T00:00:00Z'); CUT=pd.Timestamp('2025-03-18T00:00:00Z'); REF1=pd.Timestamp('2026-07-30T00:00:00Z')
AUG0=pd.Timestamp('2026-08-01T00:00:00Z'); AUG1=pd.Timestamp('2026-08-20T00:00:00Z')
FEE=.0015; NOTIONAL=500.; FAILWIN=6; RETESTWIN=6; HOLD=6

def pct(v):
    if v is None:return '-'
    try:
        if math.isnan(float(v)):return '-'
    except Exception:pass
    return f'{100*float(v):.2f}%'
def money(v): return f'${float(v):+.2f}'

def continuity(x,start,n):
    if start<0 or start+n>len(x): return False
    t0=pd.Timestamp(x.ts.iloc[start])
    return all(pd.Timestamp(x.ts.iloc[start+j])==t0+pd.Timedelta(hours=j) for j in range(n))

def find_failure(x,r):
    start=int(r.fvg_entry_idx)
    if not continuity(x,start,FAILWIN): return None
    if str(r.side)=='SHORT': # original bearish FVG -> inversion LONG
        far=float(r.fvg_high); near=float(r.fvg_low)
        for j in range(FAILWIN):
            idx=start+j
            if float(x.close.iloc[idx])>far:
                return dict(failure_idx=idx,inversion_side='LONG',entry=far,sl=near,tp=float(r.manip_high))
    else: # original bullish FVG -> inversion SHORT
        far=float(r.fvg_low); near=float(r.fvg_high)
        for j in range(FAILWIN):
            idx=start+j
            if float(x.close.iloc[idx])<far:
                return dict(failure_idx=idx,inversion_side='SHORT',entry=far,sl=near,tp=float(r.manip_low))
    return None

def find_retest(x,f):
    start=int(f['failure_idx'])+1
    if not continuity(x,start,RETESTWIN): return None
    entry=float(f['entry']); side=f['inversion_side']
    for j in range(RETESTWIN):
        idx=start+j
        hit=float(x.low.iloc[idx])<=entry if side=='LONG' else float(x.high.iloc[idx])>=entry
        if hit:return idx
    return None

def signed(side,entry,final):
    r=final/entry-1
    return r if side=='LONG' else -r

def execute(x,side,idx,entry,sl,tp,risk,td):
    if not continuity(x,idx,HOLD):return None
    f=x.iloc[idx:idx+HOLD]
    def sh(b):return float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
    def th(b):return float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
    # fill candle: SL adverse-first, TP not credited
    if sh(f.iloc[0]): out='SL';raw=-risk
    else:
        out=None;raw=None
        for j in range(1,HOLD):
            b=f.iloc[j]
            if sh(b):out='SL';raw=-risk;break
            if th(b):out='TP';raw=td;break
        if out is None:
            out='TIME';raw=signed(side,entry,float(f.close.iloc[-1]))
    net=float(raw)-FEE
    return out,net,net*NOTIONAL

def enrich(x,base):
    rows=[]
    for _,r in base[base.fvg].copy().iterrows():
        d=r.to_dict()
        d.update(failure=False,failure_idx=np.nan,failure_ts=pd.NaT,inversion_side=None,retest=False,retest_idx=np.nan,retest_ts=pd.NaT,
                 inversion_entry=np.nan,inversion_sl=np.nan,inversion_tp=np.nan,risk=np.nan,target_dist=np.nan,net_rr=np.nan,rr_eligible=False,outcome=None,net_ret=np.nan,pnl=np.nan)
        f=find_failure(x,r)
        if f is None:rows.append(d);continue
        d['failure']=True;d['failure_idx']=int(f['failure_idx']);d['failure_ts']=pd.Timestamp(x.ts.iloc[int(f['failure_idx'])]);d['inversion_side']=f['inversion_side']
        ri=find_retest(x,f)
        if ri is None:rows.append(d);continue
        d['retest']=True;d['retest_idx']=int(ri);d['retest_ts']=pd.Timestamp(x.ts.iloc[int(ri)])
        entry=float(f['entry']);sl=float(f['sl']);tp=float(f['tp']);side=f['inversion_side']
        d['inversion_entry']=entry;d['inversion_sl']=sl;d['inversion_tp']=tp
        if side=='LONG':
            if not (sl<entry<tp):rows.append(d);continue
            risk=(entry-sl)/entry;td=(tp-entry)/entry
        else:
            if not (tp<entry<sl):rows.append(d);continue
            risk=(sl-entry)/entry;td=(entry-tp)/entry
        d['risk']=risk;d['target_dist']=td;d['net_rr']=(td-FEE)/(risk+FEE)
        eligible=bool(td>=risk+2*FEE);d['rr_eligible']=eligible
        if eligible:
            q=execute(x,side,int(ri),entry,sl,tp,risk,td)
            if q is not None:d['outcome'],d['net_ret'],d['pnl']=q
        rows.append(d)
    return pd.DataFrame(rows)

def trade_stats(z):
    q=z[z.rr_eligible & z.outcome.notna()].copy()
    if q.empty:return dict(n=0,tp=0,sl=0,time=0,wr=None,pnl=0.,exp=None,medrisk=None,medrr=None)
    dec=q[q.outcome.isin(['TP','SL'])]
    return dict(n=int(len(q)),tp=int((q.outcome=='TP').sum()),sl=int((q.outcome=='SL').sum()),time=int((q.outcome=='TIME').sum()),
                wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(q.pnl.sum()),exp=float(q.pnl.mean()),medrisk=float(q.risk.median()),medrr=float(q.net_rr.median()))
def cohort(z):
    n=len(z);fn=int(z.failure.sum()) if n else 0;rn=int(z.retest.sum()) if n else 0
    return dict(fvg_n=int(n),failure_n=fn,failure_rate=(fn/n if n else None),retest_n=rn,retest_rate_of_failure=(rn/fn if fn else None),eligible_n=int(z.rr_eligible.sum()) if n else 0,trade=trade_stats(z))
def blocks(z):
    q=z[z.rr_eligible & z.outcome.notna()].sort_values('event_ts').reset_index(drop=True)
    if q.empty:return []
    b=np.linspace(0,len(q),5,dtype=int);out=[]
    for j in range(4):
        p=q.iloc[b[j]:b[j+1]];dec=p[p.outcome.isin(['TP','SL'])]
        out.append(dict(block=f'B{j+1}',n=int(len(p)),tp=int((p.outcome=='TP').sum()),sl=int((p.outcome=='SL').sum()),time=int((p.outcome=='TIME').sum()),wr=float((dec.outcome=='TP').mean()) if len(dec) else None,pnl=float(p.pnl.sum())))
    return out

def main():
    x=amd1.dataio.load_1h();base=amd1.build_events(x);ev=enrich(x,base)
    parts={'development':ev[(ev.event_ts>=REF0)&(ev.event_ts<CUT)],'reference_validation':ev[(ev.event_ts>=CUT)&(ev.event_ts<REF1)],'external':ev[(ev.event_ts>=EXT0)&(ev.event_ts<EXT1)],'august':ev[(ev.event_ts>=AUG0)&(ev.event_ts<AUG1)]}
    ev.to_csv(OUT_EVENTS,index=False);parts['august'].to_csv(OUT_AUG,index=False)
    agg={k:cohort(v) for k,v in parts.items()}
    matrix=[]
    for part,z in parts.items():
        for side in ['LONG','SHORT']:
            for sess in ['ASIA_OPEN','LONDON_OPEN','NEW_YORK_OPEN']:
                q=z[(z.inversion_side==side)&(z.session==sess)]
                matrix.append(dict(partition=part,side=side,session=sess,**cohort(q)))
    eb=blocks(parts['external']);vt=agg['reference_validation']['trade'];et=agg['external']['trade']
    supp=bool(vt['n']>=25 and (vt['wr'] or 0)>=.60 and vt['pnl']>0 and et['n']>=40 and (et['wr'] or 0)>=.60 and et['pnl']>0 and sum(b['n']>=8 and b['pnl']>0 for b in eb)>=3)
    c80=bool(vt['n']>=20 and (vt['wr'] or 0)>=.80 and vt['pnl']>0 and et['n']>=30 and (et['wr'] or 0)>=.80 and et['pnl']>0 and sum(b['n']>=5 and (b['wr'] or 0)>=.70 for b in eb)>=3)
    res=dict(protocol='BTC_H1_IFVG_FAILED_FVG_RETEST_IFVG1',coverage=dict(first=str(x.ts.min()),last=str(x.ts.max()),rows=len(x)),exact_fvg_total=len(ev),aggregate=agg,matrix=matrix,external_blocks=eb,IFVG1_SUPPORTED=supp,IFVG1_80_CANDIDATE=c80)
    OUT_JSON.write_text(json.dumps(res,indent=2,default=str)+'\n')
    md=['# BTC H1 Failed / Inversion FVG Retest IFVG1 — Result','',
        'Frozen 1H sequence: exact AMD/FVG -> completed close through far FVG edge within 6H -> wait max6H for first retest of that far edge -> enter in direction of FVG failure. SL = original FVG near edge; TP = manipulation extreme. Only modeled net RR>=1:1 after 0.15% fee is eligible. Fill-candle TP not credited; fill-candle SL adverse-first.','',
        f'Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**, exact FVG events **{len(ev)}**.','',
        '## Aggregate','',
        '| Partition | FVG | Failure close | Failure rate | Retest | Retest/failure | RR-eligible | TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ['development','reference_validation','external','august']:
        s=agg[p];t=s['trade'];ex='-' if t['exp'] is None else money(t['exp']);mr='-' if t['medrr'] is None else f"{t['medrr']:.2f}"
        md.append(f"| {p} | {s['fvg_n']} | {s['failure_n']} | {pct(s['failure_rate'])} | {s['retest_n']} | {pct(s['retest_rate_of_failure'])} | {s['eligible_n']} | {t['tp']}/{t['sl']}/{t['time']} | {pct(t['wr'])} | {money(t['pnl'])} | {ex} | {pct(t['medrisk'])} | {mr} |")
    for part,title in [('reference_validation','Reference validation by inversion side/session'),('external','External 2020-2021 by inversion side/session')]:
        md += ['',f'## {title}','', '| Inversion side | Session | FVG cohort | Failure | Retest | RR-eligible | TP/SL/TIME | WR | PnL |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in matrix:
            if r['partition']!=part:continue
            t=r['trade'];md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {r['failure_n']} | {r['retest_n']} | {r['eligible_n']} | {t['tp']}/{t['sl']}/{t['time']} | {pct(t['wr'])} | {money(t['pnl'])} |")
    md += ['','## External chronological blocks','', '| Block | N | TP | SL | TIME | WR | PnL |','|---|---:|---:|---:|---:|---:|---:|']
    for b in eb:md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")
    md += ['','## Verdicts','',f"**IFVG1_SUPPORTED: {'PASS' if supp else 'FAIL'}**",f"**IFVG1_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**",'',
           'No post-result immediate-failure entry, wick-through rule, close buffer, retest-depth change, stop buffer, target change, clock/side carve-out, or window retuning.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
