#!/usr/bin/env python3
"""SR82 external historical holdout for frozen SR81 prior-proven SUPPORT rule."""
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
OUT_MD=ROOT/'BTC_Friday_SR82_External_Holdout_Support_Result.md'
OUT_JSON=ROOT/'BTC_Friday_SR82_External_Holdout_Support_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_SR82_External_Holdout_Support_Rows.csv'
BASE='https://data.binance.vision/data/futures/um'
LOAD_START=pd.Timestamp('2019-12-01T00:00:00Z')
LOAD_END=pd.Timestamp('2023-12-02T00:00:00Z')
EVAL_START=pd.Timestamp('2020-01-03')
EVAL_END=pd.Timestamp('2023-11-24')


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

def load():
    cur=pd.Timestamp(LOAD_START.year,LOAD_START.month,1,tz='UTC');last=pd.Timestamp(LOAD_END.year,LOAD_END.month,1,tz='UTC');months=[]
    while cur<=last:months.append(cur.strftime('%Y-%m'));cur+=pd.offsets.MonthBegin(1)
    rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs=[ex.submit(fetch_month,m) for m in months]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','volume','quote_volume'])
    if x.empty:raise RuntimeError('no holdout data')
    x.ts=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True);x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=LOAD_START)&(x.ts<LOAD_END)].copy();x=x.set_index('ts',drop=False)
    if len(x)<400000:raise RuntimeError(f'insufficient holdout 5m rows {len(x)}')
    return x

def friday_dates():
    ds=pd.date_range(EVAL_START,EVAL_END,freq='W-FRI')
    return [pd.Timestamp(d.date()).tz_localize('Asia/Jakarta').tz_convert('UTC') for d in ds]

def wilson(w,n):
    if n<=0:return [None,None]
    p=w/n;z=1.959963984540054;den=1+z*z/n;c=(p+z*z/(2*n))/den;hh=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0.,c-hh),min(1.,c+hh)]

def stats(z):
    if len(z)==0:return {'n':0,'hold':0,'break':0,'rate':None,'wilson95':[None,None]}
    w=int((z.outcome=='HOLD').sum());n=len(z);return {'n':n,'hold':w,'break':n-w,'rate':w/n,'wilson95':wilson(w,n)}

def main():
    k=load();h=sr.build_h1(k);rows=[];viol=0
    for fs in friday_dates():
        if fs not in k.index:continue
        hc=sr.completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14):continue
        atr=float(hc.iloc[-1].atr14);fopen=float(k.loc[fs].open);fe=fs+pd.Timedelta(days=1)
        levels=sr.cluster_levels(sr.raw_levels(k,h,fs),atr);friday=k[(k.index>=fs)&(k.index<fe)]
        for ci,c in enumerate(levels):
            level=float(c['level'])
            if not level<fopen:continue
            mask=(friday.low.to_numpy(float)<=level)&(friday.high.to_numpy(float)>=level);hits=np.flatnonzero(mask)
            if len(hits)==0:continue
            proof=sr81.prior_proof(k,h,fs,level,'SUPPORT')
            proven=proof['resolved']>=2 and proof['hold']==proof['resolved'] and proof['break']==0
            if not proven:continue
            touch=friday.index[int(hits[0])];out=sr81.resolve_fast(k,touch,level,'SUPPORT',atr)
            if any(pd.Timestamp(o)>=fs for o in c['origins']):viol+=1
            rows.append({'friday_wib':str((fs+pd.Timedelta(hours=7)).date()),'year':int((fs+pd.Timedelta(hours=7)).year),
                         'touch_utc':str(touch),'level':level,'sources':'|'.join(c['sources']),'families':'|'.join(c['families']),
                         'confluence_count':int(c['confluence_count']),'prior_resolved':proof['resolved'],'prior_hold':proof['hold'],
                         'prior_break':proof['break'],'outcome':out['outcome']})
    df=pd.DataFrame(rows)
    if not df.empty:df.to_csv(OUT_ROWS,index=False)
    resolved=df[df.outcome.isin(['HOLD','BREAK'])].copy() if not df.empty else pd.DataFrame(columns=['outcome','year','families'])
    sf=stats(resolved);years={}
    for y in range(2020,2024):years[str(y)]=stats(resolved[resolved.year==y])
    qualifying_years=sum(q['n']>=5 and q['rate'] is not None and q['rate']>.50 for q in years.values())
    bad_years=sum(q['n']>=5 and q['rate'] is not None and q['rate']<.40 for q in years.values())
    counts=df.outcome.value_counts().to_dict() if not df.empty else {}
    fam={f:stats(resolved[resolved.families.astype(str).str.contains(f,regex=False)]) for f in ['PDAY','W7','SWING']} if len(resolved) else {}
    ok=bool(sf['n']>=30 and sf['rate'] is not None and sf['rate']>=.80 and viol==0 and qualifying_years>=3 and bad_years==0)
    out={'protocol':'SR82','period':'2020-01-03..2023-11-24 Friday WIB','rule':'SUPPORT only; SR81 prior proof >=2 resolved same-side HOLD, zero BREAK',
         'touch_events':len(df),'outcome_counts':{str(k):int(v) for k,v in counts.items()},'resolved':sf,'calendar_years':years,
         'qualifying_years_gt50_with_n5':qualifying_years,'bad_years_lt40_with_n5':bad_years,'source_family_descriptive':fam,
         'integrity_violations':viol,'verdict':'SR82_EXTERNAL_HOLDOUT_SUPPORT_CONFIRMED' if ok else 'REJECT_SR82_SUPPORT_80_HOLDOUT',
         'guardrail':'Frozen post-SR81 support hypothesis tested on pre-2023-12 external historical holdout; no rescue/tuning.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    pct=lambda x:'-' if x is None else f'{100*x:.2f}%';ci=lambda q:'-' if q[0] is None else f'{100*q[0]:.1f}%–{100*q[1]:.1f}%'
    md=['# BTC Friday SR82 — External Historical Holdout SUPPORT Result','',f"**Verdict: {out['verdict']}**",'',
        'Frozen rule: SUPPORT only; at least 2 resolved same-side prior-7d reactions, all prior resolved reactions HOLD, zero BREAK.','',
        f"Holdout first-touch events: **{len(df)}**; outcome counts: `{out['outcome_counts']}`",f"Integrity violations: **{viol}**",'',
        '## Holdout reliability','','| N | HOLD | BREAK | HOLD rate | Wilson 95% |','|---:|---:|---:|---:|---:|',
        f"| {sf['n']} | {sf['hold']} | {sf['break']} | {pct(sf['rate'])} | {ci(sf['wilson95'])} |",'',
        '## Calendar years','','| Year | N | HOLD | BREAK | HOLD rate |','|---|---:|---:|---:|---:|']
    for y,q in years.items():md.append(f"| {y} | {q['n']} | {q['hold']} | {q['break']} | {pct(q['rate'])} |")
    md += ['','This is an external historical holdout, not true-forward evidence and not a guarantee of future support behavior.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
