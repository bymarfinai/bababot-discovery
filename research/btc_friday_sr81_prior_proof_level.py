#!/usr/bin/env python3
"""SR81: deterministic prior-proof support/resistance level reliability.

Uses exact SR80 level universe and Friday outcome definition. A level qualifies
only after >=2 clean same-side prior-7d HOLD reactions and zero resolved BREAKs.
Research only; no trading/live code.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_friday_sr80_level_reliability as sr
import btc_friday_sr80_level_reliability_fast as fast

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_SR81_Prior_Proof_Level_Result.md'
OUT_JSON=ROOT/'BTC_Friday_SR81_Prior_Proof_Level_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_SR81_Prior_Proof_Level_Rows.csv'

LOOKBACK=pd.Timedelta(days=7)
EPISODE=pd.Timedelta(hours=6)
APPROACH_ATR=.10


def wilson(w:int,n:int):
    if n<=0:return [None,None]
    p=w/n;z=1.959963984540054;den=1+z*z/n
    c=(p+z*z/(2*n))/den;h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0.,c-h),min(1.,c+h)]

def stats(z:pd.DataFrame):
    if len(z)==0:return {'n':0,'hold':0,'break':0,'rate':None,'wilson95':[None,None]}
    w=int((z.outcome=='HOLD').sum());n=len(z)
    return {'n':n,'hold':w,'break':n-w,'rate':w/n,'wilson95':wilson(w,n)}

def touch_atr(h:pd.DataFrame,t:pd.Timestamp):
    hc=sr.completed_h1_before(h,t)
    if hc.empty:return np.nan
    return float(hc.iloc[-1].atr14)

def prior_proof(k:pd.DataFrame,h:pd.DataFrame,fs:pd.Timestamp,level:float,side:str):
    hist=k[(k.index>=fs-LOOKBACK)&(k.index<fs)]
    if hist.empty:return {'resolved':0,'hold':0,'break':0,'ambiguous':0,'unresolved':0,'events':[]}
    idx=list(hist.index);i=1;events=[]
    while i<len(idx):
        t=idx[i];prev_t=idx[i-1];b=hist.loc[t];prev=hist.loc[prev_t]
        atr=touch_atr(h,t)
        if not np.isfinite(atr) or atr<=0:
            i+=1;continue
        touched=float(b.low)<=level<=float(b.high)
        if side=='SUPPORT':eligible=touched and float(prev.close)>level+APPROACH_ATR*atr
        else:eligible=touched and float(prev.close)<level-APPROACH_ATR*atr
        if not eligible:
            i+=1;continue
        r=sr.resolve(k,t,level,side,atr)
        events.append({'touch':str(t),'atr':atr,'outcome':r['outcome']})
        # Resume after the fixed 6h evaluation episode, as preregistered.
        resume=t+EPISODE
        while i<len(idx) and idx[i]<resume:i+=1
    outcomes=[e['outcome'] for e in events]
    return {
      'resolved':sum(o in {'HOLD','BREAK'} for o in outcomes),
      'hold':sum(o=='HOLD' for o in outcomes),'break':sum(o=='BREAK' for o in outcomes),
      'ambiguous':sum(str(o).startswith('AMBIGUOUS') for o in outcomes),
      'unresolved':sum(o=='UNRESOLVED' for o in outcomes),'events':events}

def build(k:pd.DataFrame,h:pd.DataFrame):
    rows=[];all_touch_dates=[];viol=0
    for fs in sr.friday_dates():
        if fs not in k.index:continue
        hc=sr.completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14):continue
        atr=float(hc.iloc[-1].atr14);fopen=float(k.loc[fs].open);fe=fs+pd.Timedelta(days=1)
        levels=sr.cluster_levels(sr.raw_levels(k,h,fs),atr);friday=k[(k.index>=fs)&(k.index<fe)]
        touched_any=False
        for ci,c in enumerate(levels):
            level=float(c['level'])
            if level==fopen:continue
            side='SUPPORT' if level<fopen else 'RESISTANCE'
            touched=friday[(friday.low.astype(float)<=level)&(friday.high.astype(float)>=level)]
            if touched.empty:continue
            touched_any=True
            proof=prior_proof(k,h,fs,level,side)
            proven=proof['resolved']>=2 and proof['hold']==proof['resolved'] and proof['break']==0
            if not proven:continue
            touch=touched.index[0]
            out=sr.resolve(k,touch,level,side,atr)
            if any(pd.Timestamp(o)>=fs for o in c['origins']):viol+=1
            rows.append({
              'friday_wib':str((fs+pd.Timedelta(hours=7)).date()),'freeze_utc':str(fs),'touch_utc':str(touch),
              'cluster_id':f"{(fs+pd.Timedelta(hours=7)).date()}-{ci}",'level':level,'side':side,
              'sources':'|'.join(c['sources']),'families':'|'.join(c['families']),'confluence_count':int(c['confluence_count']),
              'prior_resolved':proof['resolved'],'prior_hold':proof['hold'],'prior_break':proof['break'],
              'prior_ambiguous':proof['ambiguous'],'prior_unresolved':proof['unresolved'],
              'outcome':out['outcome']})
        if touched_any:all_touch_dates.append(str((fs+pd.Timedelta(hours=7)).date()))
    return pd.DataFrame(rows),sorted(set(all_touch_dates)),viol

def blocks(z:pd.DataFrame):
    dates=sorted(z.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):
        q=z[z.friday_wib.isin(set(ch))];out[f'B{i+1}']=stats(q)
    return out

def main():
    k=fast.fast_load();h=sr.build_h1(k)
    events,base_dates,viol=build(k,h)
    if events.empty:
        out={'protocol':'SR81','verdict':'REJECT_SR81_PRIOR_PROOF_LEVEL','reason':'No PRIOR_PROVEN Friday levels touched.','integrity_violations':viol}
        OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday SR81 — Result\n\n**REJECT_SR81_PRIOR_PROOF_LEVEL**\n\nNo PRIOR_PROVEN Friday levels touched.\n');print(json.dumps(out,indent=2));return
    events.to_csv(OUT_ROWS,index=False)
    cut=int(math.floor(.70*len(base_dates)));dd=set(base_dates[:cut]);vd=set(base_dates[cut:])
    resolved=events[events.outcome.isin(['HOLD','BREAK'])].copy();resolved['period']=np.where(resolved.friday_wib.isin(dd),'discovery','validation')
    d=resolved[resolved.period=='discovery'];v=resolved[resolved.period=='validation'];full=resolved
    sd,sv,sf=stats(d),stats(v),stats(full);bl=blocks(full)
    pos=sum(q['n']>=5 and q['rate'] is not None and q['rate']>.50 for q in bl.values())
    ok=bool(sd['n']>=20 and sd['rate'] is not None and sd['rate']>=.80 and sv['n']>=10 and sv['rate'] is not None and sv['rate']>=.80 and sf['n']>=30 and sf['rate'] is not None and sf['rate']>=.80 and sv['rate']>.60 and pos>=3 and viol==0)
    sides={s:stats(full[full.side==s]) for s in ['SUPPORT','RESISTANCE']}
    fam={}
    for f in ['PDAY','W7','SWING']:
        fam[f]=stats(full[full.families.astype(str).str.contains(f,regex=False)])
    counts=events.outcome.value_counts().to_dict()
    out={'protocol':'SR81','rule':'prior resolved same-side events >=2; all resolved prior events HOLD; zero BREAK',
         'base_friday_dates_with_any_level_touch':len(base_dates),'prior_proven_touch_events':len(events),
         'outcome_counts':{str(k):int(vv) for k,vv in counts.items()},'resolved_events':len(full),
         'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos,
         'support_resistance_descriptive':sides,'source_family_descriptive':fam,'integrity_violations':viol,
         'verdict':'BTC_FRIDAY_SR81_PRIOR_PROOF_80_CANDIDATE' if ok else 'REJECT_SR81_PRIOR_PROOF_LEVEL',
         'guardrail':'Combined rule only. No support-only/resistance-only or threshold rescue.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    pct=lambda x:'-' if x is None else f'{100*x:.2f}%'
    ci=lambda q:'-' if q[0] is None else f'{100*q[0]:.1f}%–{100*q[1]:.1f}%'
    md=['# BTC Friday SR81 — Prior-Proof Support/Resistance Result','',f"**Verdict: {out['verdict']}**",'',
        'Exact rule: at least 2 resolved same-side prior-7d reactions, every resolved reaction was HOLD, zero BREAK.','',
        f"PRIOR_PROVEN first-touch events: **{len(events)}**; resolved Friday outcomes: **{len(full)}**",f"Outcome counts: `{out['outcome_counts']}`",f"Integrity violations: **{viol}**",'',
        '## Primary combined reliability','','| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |','|---|---:|---:|---:|---:|---:|']
    for name,q in [('Discovery',sd),('Validation',sv),('Full',sf)]:md.append(f"| {name} | {q['n']} | {q['hold']} | {q['break']} | {pct(q['rate'])} | {ci(q['wilson95'])} |")
    md += ['','## Support / resistance descriptive only','','| Side | N | HOLD | Rate |','|---|---:|---:|---:|']
    for s,q in sides.items():md.append(f"| {s} | {q['n']} | {q['hold']} | {pct(q['rate'])} |")
    md += ['','## Chronological blocks','','| Block | N | HOLD | Rate |','|---|---:|---:|---:|']
    for b,q in bl.items():md.append(f"| {b} | {q['n']} | {q['hold']} | {pct(q['rate'])} |")
    md += ['','No side/family may rescue a failed combined verdict. This is level reliability, not PnL and not a future guarantee.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
