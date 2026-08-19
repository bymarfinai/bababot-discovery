#!/usr/bin/env python3
"""C2: all Friday-WIB BTCUSDT 5m discrete single-candle archetype study.

Implementation accelerated with NumPy only; frozen C2 research definition is unchanged.
"""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_All5m_Candle_C2_Result.md';OUT_JSON=ROOT/'BTC_Friday_All5m_Candle_C2_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_All5m_Candle_C2_Rows.csv';OUT_DISC=ROOT/'BTC_Friday_All5m_Candle_C2_Discovery_Archetypes.csv'
START=pd.Timestamp('2023-12-02T00:00:00Z');END=pd.Timestamp('2026-08-19T00:00:00Z')
BASE='https://data.binance.vision/data/futures/um';TP=SL=.013;HOLD=72;COST=.0015;NOTIONAL=500.

def fetch_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c2/1.1'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<5:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                out.append([ts,row[1],row[2],row[3],row[4]])
    return out

def load5():
    jobs=[];cur=pd.Timestamp(START.year,START.month,1,tz='UTC');em=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<em:
        ym=cur.strftime('%Y-%m');jobs.append(f'{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{ym}.zip');cur+=pd.offsets.MonthBegin(1)
    d=em
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d');jobs.append(f'{BASE}/daily/klines/BTCUSDT/5m/BTCUSDT-5m-{ds}.zip');d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close'])
    for c in ['open','high','low','close']:x[c]=pd.to_numeric(x[c],errors='coerce')
    x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    x=x.dropna().drop_duplicates('ts').sort_values('ts');x=x[(x.ts>=START-pd.Timedelta(minutes=20))&(x.ts<END)].reset_index(drop=True)
    if len(x)<250000:raise RuntimeError(f'insufficient 5m rows {len(x)}')
    return x

def _resolve(ep,hs,ls,final_close,side):
    if side>0:
        tp_hits=np.flatnonzero(hs>=ep*(1+TP));sl_hits=np.flatnonzero(ls<=ep*(1-SL))
    else:
        tp_hits=np.flatnonzero(ls<=ep*(1-TP));sl_hits=np.flatnonzero(hs>=ep*(1+SL))
    ti=int(tp_hits[0]) if tp_hits.size else 10**9;si=int(sl_hits[0]) if sl_hits.size else 10**9
    if si<=ti:raw=-SL;reason='SL'
    elif ti<10**9:raw=TP;reason='TP'
    else:raw=side*(final_close/ep-1);reason='TIME'
    net=raw-COST;return net*NOTIONAL,int(net>0),reason

def build(x):
    O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);TS=x.ts
    rg=np.maximum(H-L,1e-12);body=np.abs(C-O)/rg;upper=(H-np.maximum(O,C))/rg;lower=(np.minimum(O,C)-L)/rg;cp=(C-L)/rg;ro=(H-L)/O
    prev3med=pd.Series(ro).shift(1).rolling(3,min_periods=3).median().to_numpy()
    wib=TS+pd.Timedelta(hours=7);is_friday=(wib.dt.weekday.to_numpy()==4);non_doji=(C!=O)
    idx=np.flatnonzero(is_friday & non_doji & np.isfinite(prev3med))
    idx=idx[(idx>=3)&(idx+HOLD<len(x)-1)]
    rows=[]
    for i in idx:
        green=C[i]>O[i];direction='GREEN' if green else 'RED';b=body[i];u=upper[i];d=lower[i]
        bb='SMALL' if b<=1/3 else ('LARGE' if b>=2/3 else 'MEDIUM')
        dom='UPPER' if u>d and u>b else ('LOWER' if d>u and d>b else 'BODY_BALANCED')
        ch='HIGH' if cp[i]>0.5 else 'LOW';rs='EXPANDED' if ro[i]>prev3med[i] else 'NORMAL'
        if C[i-1]==O[i-1]:pr='PRIOR_DOJI'
        else:pr='SAME' if ((C[i-1]>O[i-1])==green) else 'OPPOSITE'
        key='|'.join([direction,bb,dom,ch,rs,pr]);ep=O[i+1];hs=H[i+1:i+1+HOLD];ls=L[i+1:i+1+HOLD];fc=C[i+HOLD]
        side=1 if green else -1;cont=_resolve(ep,hs,ls,fc,side);rev=_resolve(ep,hs,ls,fc,-side)
        rows.append({'signal_ts':str(TS.iloc[i]),'friday_wib':str(wib.iloc[i].date()),'entry_ts':str(TS.iloc[i+1]),
                     'archetype':key,'direction':direction,'body_bucket':bb,'dominance':dom,'close_half':ch,'range_state':rs,'prior_color_relation':pr,
                     'cont_pnl':cont[0],'cont_win':cont[1],'cont_reason':cont[2],'rev_pnl':rev[0],'rev_win':rev[1],'rev_reason':rev[2]})
    return pd.DataFrame(rows)
def pf(a):
    gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<=0);return gp/gl if gl>0 else (999. if gp>0 else None)
def stats(z,col):
    a=z[col].astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    w=sum(v>0 for v in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}
def blocks(df,mode,key):
    dates=sorted(df.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=stats(df[df.friday_wib.isin(set(ch))&(df.archetype==key)],f'{mode}_pnl')
    return out

def main():
    x=load5();df=build(x);dates=sorted(df.friday_wib.unique());cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);vd=set(dates[cut:]);df['period']=np.where(df.friday_wib.isin(dd),'discovery','validation');disc=df[df.period=='discovery'];val=df[df.period=='validation']
    baseline={m:{'discovery':stats(disc,f'{m}_pnl'),'validation':stats(val,f'{m}_pnl'),'full':stats(df,f'{m}_pnl')} for m in ('cont','rev')};reports=[];eligible=[]
    for mode in ('cont','rev'):
        for key,z in disc.groupby('archetype'):
            s=stats(z,f'{mode}_pnl');q={'mode':mode,'archetype':key,**s};reports.append(q)
            if s['n']>=100 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['pf'] is not None and s['pf']>1:eligible.append(q)
    pd.DataFrame(reports).to_csv(OUT_DISC,index=False);eligible.sort(key=lambda q:(-q['wr'],-q['n'],-q['pf'],q['mode'],q['archetype']))
    out={'protocol':'C2','implementation':'numpy_fast_equivalent','friday_dates':len(dates),'discovery_dates':len(dd),'validation_dates':len(vd),'signal_rows':len(df),'archetypes_discovery':len(set(disc.archetype)),'discovery_eligible_80':len(eligible),'baseline':baseline,'top_discovery_support100':{}}
    for mode in ('cont','rev'):
        top=[q for q in reports if q['mode']==mode and q['n']>=100];top.sort(key=lambda q:(-q['wr'],-q['n'],q['archetype']));out['top_discovery_support100'][mode]=top[:10]
    if not eligible:out.update({'selected':None,'verdict':'REJECT_C2_80_CANDLE_IDENTIFIER','reason':'No frozen 5m single-candle archetype achieved discovery N>=100 and WR>=80%.'})
    else:
        q=eligible[0];m=q['mode'];k=q['archetype'];sd=stats(disc[disc.archetype==k],f'{m}_pnl');sv=stats(val[val.archetype==k],f'{m}_pnl');sf=stats(df[df.archetype==k],f'{m}_pnl');bl=blocks(df,m,k);pos=sum(z['n']>0 and z['pnl']>0 for z in bl.values())
        ok=sd['n']>=100 and sd['wr']>=.80 and sv['n']>=40 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=180 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and sv['wr']>baseline[m]['validation']['wr'] and pos>=3
        out['selected']={'mode':m,'archetype':k,'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos};out['verdict']='BTC_FRIDAY_5M_80_CANDIDATE' if ok else 'REJECT_C2_80_CANDLE_IDENTIFIER'
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda v,d=2:'-' if v is None else f'{v:.{d}f}';md=['# BTC Friday All-5m Candle C2 — Result','',f"Friday dates: **{len(dates)}**; signal candles: **{len(df)}**",f"Discovery / validation dates: **{len(dd)} / {len(vd)}**",f"Discovery archetypes passing 80% support screen: **{len(eligible)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} — best discovery archetypes N>=100','', '| Archetype | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for q in out['top_discovery_support100'][mode]:md.append(f"| `{q['archetype']}` | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | ${F(q['pnl'])} | {F(q['pf'],3)} |")
        md.append('')
    if out.get('selected') is None:md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Discovery-selected archetype','',f"Mode **{s['mode'].upper()}**",f"`{s['archetype']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,z in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {z['n']} | {z['wins']} | {F(100*z['wr'])}% | ${F(z['pnl'])} | ${F(z['exp'],3)} | {F(z['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future probability. C2 closes the preregistered single-candle 5m hypothesis if rejected.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
