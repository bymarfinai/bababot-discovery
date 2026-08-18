#!/usr/bin/env python3
"""Sunday T-Method ST8 family completion — Sunday-scaled FastMR sweep matching Tuesday A5.8 milestone.
Research only; live BBC untouched.
Fixed parent Sunday16 SELL TP2.5 SL1.4 hold18h; fixed hinge +1.0%; fixed lock +0.4%.
Compact family: EMA20 overextension x giveback x latency (2h/4h/6h). Discovery-only selection;
validation report-only. Then test the same EMA7 runner-recovery concept with selected giveback as min progress.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sunday_tmethod_st0_st3_reset as st03

sun17=st03.sun17
OUT=Path(os.getenv('SUNT8F_OUT','sunt8f_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83; HINGE=0.010; LOCK=0.004
D20S=[0.004,0.006,0.008,0.010]
GIVEBACKS=[0.006,0.005,0.004]
LATENCIES=[120,240,360]


def hinfo(k,tr): return st03.first_hinge(k,tr,HINGE)

def d20(k,h):
    b=k.loc[h['bar_t']]
    return float(b.ema20)/float(b.close)-1.0

def arm(k,tr,h,th,gb,lat):
    if h is None: return None
    dist=d20(k,h)
    if dist<th: return None
    start=h['decision_t']; end=min(tr['exit_t'],start+pd.Timedelta(minutes=lat)); ep=tr['entry']
    for b in k[(k.index>=start)&(k.index<end)].itertuples(index=False):
        prog=1.0-float(b.close)/ep
        if prog<=gb:
            dt=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=dt: return None
            return {'decision_t':dt,'d20':dist,'progress':prog}
    return None

def lock_outcome(k,f,tr,a,recover=False,minprog=0.006):
    if a is None: return float(tr['pnl']),False,False
    ep=tr['entry']; lp=ep*(1-LOCK); d=a['decision_t']
    if d not in k.index: return float(tr['pnl']),False,False
    op=float(k.loc[d,'open'])
    if op>=lp:
        return st03.funding_pnl(k,f,tr['entry_t'],d+pd.Timedelta(minutes=5),ep,op),True,False
    for b in k[(k.index>=d)&(k.index<tr['exit_t'])].itertuples(index=False):
        if float(b.high)>=lp:
            et=b.ts+pd.Timedelta(minutes=5)
            return st03.funding_pnl(k,f,tr['entry_t'],et,ep,lp),True,False
        if recover:
            prog=1.0-float(b.close)/ep
            if float(b.high)>=float(b.ema7) and float(b.close)<float(b.ema7) and prog>=minprog:
                ct=b.ts+pd.Timedelta(minutes=5)
                if tr['exit_t']>ct: return float(tr['pnl']),True,True
    return float(tr['pnl']),True,False

def blocks(a):
    ix=np.array_split(np.arange(len(a)),8); return [st03.metrics(np.asarray(a)[z]) for z in ix]

def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k)
    trades=[sun17.simulate_parent(k,f,t) for t in es]; hs=[hinfo(k,tr) for tr in trades]
    parent=np.array([tr['pnl'] for tr in trades],float); pm=st03.metrics(parent); pD=st03.metrics(parent[:DISC_N]); pV=st03.metrics(parent[DISC_N:])
    if abs(pm['pnl']-63.599379132074105)>0.25: raise RuntimeError(f'parent parity {pm}')
    grid=[]
    for th in D20S:
      for gb in GIVEBACKS:
       for lat in LATENCIES:
        vals=[]; detail=[]
        for i,(tr,h) in enumerate(zip(trades,hs)):
            a=arm(k,tr,h,th,gb,lat); p,act,_=lock_outcome(k,f,tr,a,False,gb); vals.append(p)
            if act: detail.append({'i':i,'date':str(tr['entry_t'].date()),'delta':p-tr['pnl'],'parent_pnl':tr['pnl'],'managed_pnl':p})
        vals=np.array(vals,float); da=sum(x['i']<DISC_N for x in detail)
        grid.append({'d20':th,'giveback':gb,'latency':lat,'actions':len(detail),'D_actions':da,'V_actions':len(detail)-da,
                     'full':st03.metrics(vals),'D':st03.metrics(vals[:DISC_N]),'V':st03.metrics(vals[DISC_N:])})
    eligible=[x for x in grid if x['D_actions']>=4 and x['D']['pnl']>pD['pnl']]
    champ=max(eligible,key=lambda x:x['D']['pnl']) if eligible else max(grid,key=lambda x:x['D']['pnl'])
    th,gb,lat=champ['d20'],champ['giveback'],champ['latency']
    fast=[]; rec=[]; acts=recs=0
    for tr,h in zip(trades,hs):
        a=arm(k,tr,h,th,gb,lat)
        p,ac,_=lock_outcome(k,f,tr,a,False,gb); fast.append(p); acts+=int(ac)
        q,ac2,rr=lock_outcome(k,f,tr,a,True,gb); rec.append(q); recs+=int(rr)
    fast=np.array(fast); rec=np.array(rec); fm=st03.metrics(fast); rm=st03.metrics(rec)
    fD=st03.metrics(fast[:DISC_N]); fV=st03.metrics(fast[DISC_N:]); rD=st03.metrics(rec[:DISC_N]); rV=st03.metrics(rec[DISC_N:])
    fb=blocks(fast); rb=blocks(rec)
    top=sorted(grid,key=lambda x:x['D']['pnl'],reverse=True)[:10]
    out={'status':'COMPLETE_SUNDAY_TMETHOD_ST8_FAMILY','parent':{'full':pm,'D':pD,'V':pV},'grid_n':len(grid),'topD':top,
         'selected':champ,'fastmr':{'full':fm,'D':fD,'V':fV,'actions':acts,'positive_blocks':sum(x['pnl']>0 for x in fb)},
         'runner_recovery':{'full':rm,'D':rD,'V':rV,'actions':recs,'positive_blocks':sum(x['pnl']>0 for x in rb)},
         'guardrail':'Compact family mirrors Tuesday A5.8 but with Sunday time scale (2h/4h/6h) and +1.0 hinge. Selection is discovery-only with >=4 discovery actions; V report-only. Prior Sunday research means not untouched OOS.'}
    (OUT/'sunt8f_summary.json').write_text(json.dumps(out,indent=2,default=str))
    def pc(m): return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday T-Method — ST8 FastMR Family Completion','', '**Status: COMPLETE — compact Sunday FastMR family; live BBC untouched.**','',
        f"Parent: WR **{pc(pm)}**, PnL **${pm['pnl']:+.2f}**, D ${pD['pnl']:+.2f}, V ${pV['pnl']:+.2f}.",'',
        '## Selected discovery rule',
        f"- +1.00% hinge; EMA20 overextension **{100*th:.2f}%**; giveback <= **+{100*gb:.2f}%** within **{lat//60}h**; arm +0.40% lock.",
        f"- actions {acts}; FastMR WR **{pc(fm)}**, PnL **${fm['pnl']:+.2f}**, PF **{fm['pf']:.2f}**, blocks {sum(x['pnl']>0 for x in fb)}/8.",
        f"- D: {pc(fD)}, ${fD['pnl']:+.2f}; V: {pc(fV)}, ${fV['pnl']:+.2f}.",'',
        '## Top discovery neighborhood','', '| d20 | giveback | latency | actions D/V | Full PnL | D PnL | V PnL |','|---:|---:|---:|---:|---:|---:|---:|']
    for x in top:
        md.append(f"| {100*x['d20']:.2f}% | {100*x['giveback']:.2f}% | {x['latency']//60}h | {x['D_actions']}/{x['V_actions']} | ${x['full']['pnl']:+.2f} | ${x['D']['pnl']:+.2f} | ${x['V']['pnl']:+.2f} |")
    md += ['', '## EMA7 runner recovery on selected FastMR',
           f"- recovery actions {recs}; PnL ${fm['pnl']:+.2f} -> **${rm['pnl']:+.2f}**; WR **{pc(rm)}**.",
           f"- D ${rD['pnl']:+.2f}; V ${rV['pnl']:+.2f}; blocks {sum(x['pnl']>0 for x in rb)}/8.",'',
           '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_TMETHOD_ST8_FAMILY_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__': main()
