#!/usr/bin/env python3
"""SR82: external pre-2023-12 validation of SR81-generated PRIOR_PROVEN SUPPORT hypothesis."""
from __future__ import annotations
import csv, io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

import btc_friday_sr80_level_reliability as sr
import btc_friday_sr81_prior_proof_level as sr81

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_SR82_Support_External_Result.md'
OUT_JSON=ROOT/'BTC_Friday_SR82_Support_External_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_SR82_Support_External_Rows.csv'
BASE='https://data.binance.vision/data/futures/um'
LOAD_START=pd.Timestamp('2021-12-20T00:00:00Z')
LOAD_END=pd.Timestamp('2023-12-02T00:00:00Z')
FIRST_LOCAL='2022-01-07';LAST_LOCAL='2023-11-24'


def fetch_month(ym):
    url=f'{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{ym}.zip'
    r=requests.get(url,timeout=90,headers={'User-Agent':'bababot-sr82/1.0'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<8:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),float(row[7])])
                except Exception:continue
    return out


def load5():
    months=[];cur=pd.Timestamp(LOAD_START.year,LOAD_START.month,1,tz='UTC');last=pd.Timestamp(LOAD_END.year,LOAD_END.month,1,tz='UTC')-pd.offsets.MonthBegin(1)
    while cur<=last:
        months.append(cur.strftime('%Y-%m'));cur+=pd.offsets.MonthBegin(1)
    rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs=[ex.submit(fetch_month,m) for m in months]
        for f in as_completed(fs):rows.extend(f.result())
    k=pd.DataFrame(rows,columns=['ts','open','high','low','close','volume','quote_volume'])
    if k.empty:raise RuntimeError('no external Data Vision rows')
    k['ts']=pd.to_datetime(pd.to_numeric(k.ts),unit='ms',utc=True)
    k=k.dropna().drop_duplicates('ts').sort_values('ts');k=k[(k.ts>=LOAD_START)&(k.ts<LOAD_END)].copy()
    if len(k)<190000:raise RuntimeError(f'insufficient external 5m rows {len(k)}')
    k=k.set_index('ts',drop=False)
    return k


def friday_dates():
    ds=pd.date_range(FIRST_LOCAL,LAST_LOCAL,freq='W-FRI')
    return [pd.Timestamp(d.date()).tz_localize('Asia/Jakarta').tz_convert('UTC') for d in ds]


def touch_atr(h,t):
    cutoff=t-pd.Timedelta(hours=1);j=int(h.index.searchsorted(cutoff,side='right'))-1
    return np.nan if j<0 else float(h.iloc[j].atr14)


def resolve_fast(k,touch,level,side,atr):
    j=int(k.index.searchsorted(touch,side='left'))
    if j>=len(k) or k.index[j]!=touch:return {'outcome':'INTEGRITY_ERROR'}
    up=level+sr.REACTION_ATR*atr;dn=level-sr.REACTION_ATR*atr;b0=k.iloc[j]
    if float(b0.high)>=up or float(b0.low)<=dn:return {'outcome':'AMBIGUOUS_TOUCH_BAR'}
    end=touch+pd.Timedelta(hours=6);i=j+1
    while i<len(k) and k.index[i]<end:
        b=k.iloc[i];hu=float(b.high)>=up;ld=float(b.low)<=dn
        if hu and ld:return {'outcome':'AMBIGUOUS_LATER_BAR','resolution_time':str(k.index[i])}
        if side=='SUPPORT':
            if hu:return {'outcome':'HOLD','resolution_time':str(k.index[i])}
            if ld:return {'outcome':'BREAK','resolution_time':str(k.index[i])}
        else:
            if ld:return {'outcome':'HOLD','resolution_time':str(k.index[i])}
            if hu:return {'outcome':'BREAK','resolution_time':str(k.index[i])}
        i+=1
    return {'outcome':'UNRESOLVED'}


def prior_proof(k,h,fs,level):
    hist=k[(k.index>=fs-pd.Timedelta(days=7))&(k.index<fs)]
    if hist.empty:return {'resolved':0,'hold':0,'break':0,'ambiguous':0,'unresolved':0}
    idx=hist.index;i=1;outs=[]
    while i<len(hist):
        b=hist.iloc[i];t=idx[i]
        if not (float(b.low)<=level<=float(b.high)):
            i+=1;continue
        atr=touch_atr(h,t)
        if not np.isfinite(atr) or atr<=0:
            i+=1;continue
        prev=hist.iloc[i-1]
        if not (float(prev.close)>level+0.10*atr):
            i+=1;continue
        r=resolve_fast(k,t,level,'SUPPORT',atr);outs.append(r['outcome'])
        resume=t+pd.Timedelta(hours=6);i=int(idx.searchsorted(resume,side='left'))
    return {'resolved':sum(o in {'HOLD','BREAK'} for o in outs),'hold':sum(o=='HOLD' for o in outs),'break':sum(o=='BREAK' for o in outs),'ambiguous':sum(str(o).startswith('AMBIGUOUS') for o in outs),'unresolved':sum(o=='UNRESOLVED' for o in outs)}


def build(k,h):
    rows=[];viol=0
    for fs in friday_dates():
        if fs not in k.index:continue
        hc=sr.completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14):continue
        atr=float(hc.iloc[-1].atr14);fopen=float(k.loc[fs].open);friday=k[(k.index>=fs)&(k.index<fs+pd.Timedelta(days=1))]
        levels=sr.cluster_levels(sr.raw_levels(k,h,fs),atr)
        for ci,c in enumerate(levels):
            level=float(c['level'])
            if not level<fopen:continue
            mask=(friday.low.to_numpy(float)<=level)&(friday.high.to_numpy(float)>=level);hits=np.flatnonzero(mask)
            if len(hits)==0:continue
            proof=prior_proof(k,h,fs,level)
            if not (proof['resolved']>=2 and proof['hold']==proof['resolved'] and proof['break']==0):continue
            touch=friday.index[int(hits[0])];out=resolve_fast(k,touch,level,'SUPPORT',atr)
            if any(pd.Timestamp(o)>=fs for o in c['origins']):viol+=1
            rows.append({'friday_wib':str((fs+pd.Timedelta(hours=7)).date()),'freeze_utc':str(fs),'touch_utc':str(touch),'cluster_id':f"{(fs+pd.Timedelta(hours=7)).date()}-{ci}",'level':level,'sources':'|'.join(c['sources']),'families':'|'.join(c['families']),'confluence_count':int(c['confluence_count']),'prior_resolved':proof['resolved'],'prior_hold':proof['hold'],'prior_break':proof['break'],'prior_ambiguous':proof['ambiguous'],'prior_unresolved':proof['unresolved'],'outcome':out['outcome']})
    return pd.DataFrame(rows),viol


def wilson(w,n):
    if n<=0:return [None,None]
    p=w/n;z=1.959963984540054;den=1+z*z/n;c=(p+z*z/(2*n))/den;hh=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0,c-hh),min(1,c+hh)]

def stats(z):
    if len(z)==0:return {'n':0,'hold':0,'break':0,'rate':None,'wilson95':[None,None]}
    w=int((z.outcome=='HOLD').sum());n=len(z);return {'n':n,'hold':w,'break':n-w,'rate':w/n,'wilson95':wilson(w,n)}
def blocks(z):
    dates=sorted(z.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=stats(z[z.friday_wib.isin(set(ch))])
    return out


def main():
    k=load5();h=sr.build_h1(k);events,viol=build(k,h)
    if events.empty:
        out={'protocol':'SR82','external_window':[FIRST_LOCAL,LAST_LOCAL],'verdict':'REJECT_SR82_SUPPORT_EXTERNAL','reason':'No PRIOR_PROVEN_SUPPORT external touches','integrity_violations':viol}
        OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday SR82 — External Support Result\n\n**REJECT_SR82_SUPPORT_EXTERNAL**\n\nNo external PRIOR_PROVEN_SUPPORT touches.\n');print(json.dumps(out,indent=2));return
    events.to_csv(OUT_ROWS,index=False);resolved=events[events.outcome.isin(['HOLD','BREAK'])].copy();s=stats(resolved);bl=blocks(resolved);positive=sum(q['n']>=5 and q['rate'] is not None and q['rate']>.50 for q in bl.values())
    ok=bool(s['n']>=20 and s['rate'] is not None and s['rate']>=.80 and viol==0 and positive>=3)
    counts=events.outcome.value_counts().to_dict();out={'protocol':'SR82','hypothesis_origin':'SR81 descriptive SUPPORT 11/13; this decision uses only untouched earlier BTC data','external_window':[FIRST_LOCAL,LAST_LOCAL],'support_prior_proven_touches':len(events),'resolved':s,'outcome_counts':{str(a):int(b) for a,b in counts.items()},'blocks':bl,'positive_blocks':positive,'integrity_violations':viol,'verdict':'BTC_FRIDAY_SR82_SUPPORT_EXTERNAL_80_CANDIDATE' if ok else 'REJECT_SR82_SUPPORT_EXTERNAL','guardrail':'No same-sample rescue. If PASS, next step is executable rejection-candle trade validation.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');pct=lambda x:'-' if x is None else f'{100*x:.2f}%';ci=lambda q:'-' if q[0] is None else f'{100*q[0]:.1f}%–{100*q[1]:.1f}%'
    md=['# BTC Friday SR82 — PRIOR_PROVEN Support External Validation','',f"**Verdict: {out['verdict']}**",'',f"External BTC window: **{FIRST_LOCAL} through {LAST_LOCAL} Friday-WIB** (entirely before SR80/SR81 sample).",f"PRIOR_PROVEN_SUPPORT touches: **{len(events)}**; resolved: **{s['n']}**",f"Outcome counts: `{out['outcome_counts']}`",f"Integrity violations: **{viol}**",'', '## External resolved reliability','', '| N | HOLD | BREAK | HOLD rate | Wilson 95% |','|---:|---:|---:|---:|---:|',f"| {s['n']} | {s['hold']} | {s['break']} | {pct(s['rate'])} | {ci(s['wilson95'])} |",'', '## Chronological blocks','', '| Block | N | HOLD | Rate |','|---|---:|---:|---:|']
    for b,q in bl.items():md.append(f"| {b} | {q['n']} | {q['hold']} | {pct(q['rate'])} |")
    md += ['',f"Blocks with N>=5 and HOLD>50%: **{positive}/4**",'', 'This is external validation of level context, not yet a tradable candle entry or a future guarantee.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))

if __name__=='__main__':main()
