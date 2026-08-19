#!/usr/bin/env python3
"""C1: all Friday-WIB BTCUSDT 15m discrete candle archetype study."""
from __future__ import annotations

import csv, io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_All15m_Candle_C1_Result.md'
OUT_JSON=ROOT/'BTC_Friday_All15m_Candle_C1_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_All15m_Candle_C1_Rows.csv'
OUT_DISC=ROOT/'BTC_Friday_All15m_Candle_C1_Discovery_Archetypes.csv'
START=pd.Timestamp('2023-12-02T00:00:00Z')
END=pd.Timestamp('2026-08-19T00:00:00Z')
BASE='https://data.binance.vision/data/futures/um'
TP=SL=.013
HOLD_BARS=24
COST=.0015
NOTIONAL=500.0


def _fetch_zip(url):
    r=requests.get(url,timeout=45,headers={'User-Agent':'bababot-c1/1.0'})
    if r.status_code==404:return []
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        out=[]
        with zf.open(name) as fh:
            rd=csv.reader(io.TextIOWrapper(fh,encoding='utf-8'))
            for row in rd:
                if len(row)<5:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                out.append([ts,row[1],row[2],row[3],row[4]])
        return out


def load_15m():
    jobs=[]
    cur=pd.Timestamp(START.year,START.month,1,tz='UTC')
    end_month=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<end_month:
        ym=cur.strftime('%Y-%m')
        jobs.append(f'{BASE}/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip')
        cur+=pd.offsets.MonthBegin(1)
    d=end_month
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d')
        jobs.append(f'{BASE}/daily/klines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip')
        d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(_fetch_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    df=pd.DataFrame(rows,columns=['ts','open','high','low','close'])
    for c in ['open','high','low','close']:df[c]=pd.to_numeric(df[c],errors='coerce')
    df['ts']=pd.to_datetime(pd.to_numeric(df.ts),unit='ms',utc=True)
    df=df.dropna().drop_duplicates('ts').sort_values('ts')
    df=df[(df.ts>=START-pd.Timedelta(hours=2))&(df.ts<END)].reset_index(drop=True)
    if len(df)<50_000:raise RuntimeError(f'insufficient 15m rows: {len(df)}')
    return df


def geom(o,h,l,c):
    rg=max(h-l,1e-12)
    body=abs(c-o)/rg;upper=(h-max(o,c))/rg;lower=(min(o,c)-l)/rg;close_pos=(c-l)/rg;range_open=(h-l)/o
    return body,upper,lower,close_pos,range_open


def archetype(df,i):
    r=df.iloc[i];p=df.iloc[i-1]
    o,h,l,c=map(float,[r.open,r.high,r.low,r.close])
    if c==o:return None
    body,upper,lower,cp,ro=geom(o,h,l,c)
    direction='GREEN' if c>o else 'RED'
    if body<=1/3:body_bucket='SMALL'
    elif body>=2/3:body_bucket='LARGE'
    else:body_bucket='MEDIUM'
    if upper>lower and upper>body:dominance='UPPER'
    elif lower>upper and lower>body:dominance='LOWER'
    else:dominance='BODY_BALANCED'
    close_half='HIGH' if cp>0.5 else 'LOW'
    pro=[]
    for j in range(i-3,i):
        q=df.iloc[j];_,_,_,_,qr=geom(float(q.open),float(q.high),float(q.low),float(q.close));pro.append(qr)
    range_state='EXPANDED' if ro>float(np.median(pro)) else 'NORMAL'
    po,pc=float(p.open),float(p.close)
    if pc==po:prior_rel='PRIOR_DOJI'
    else:prior_rel='SAME' if ((pc>po)==(c>o)) else 'OPPOSITE'
    key='|'.join([direction,body_bucket,dominance,close_half,range_state,prior_rel])
    return {'archetype':key,'direction':direction,'body_bucket':body_bucket,'dominance':dominance,
            'close_half':close_half,'range_state':range_state,'prior_color_relation':prior_rel,
            'body_ratio':body,'upper_ratio':upper,'lower_ratio':lower,'close_pos':cp,'range_open':ro}


def trade(df,i,side):
    if i+HOLD_BARS>=len(df):return None
    ep=float(df.iloc[i+1].open);tp=ep*(1+TP) if side>0 else ep*(1-TP);sl=ep*(1-SL) if side>0 else ep*(1+SL)
    raw=None;reason=None
    for j in range(i+1,i+1+HOLD_BARS):
        q=df.iloc[j];hi=float(q.high);lo=float(q.low)
        hit_tp=hi>=tp if side>0 else lo<=tp
        hit_sl=lo<=sl if side>0 else hi>=sl
        if hit_sl:raw=-SL;reason='SL';break
        if hit_tp:raw=TP;reason='TP';break
    if raw is None:
        px=float(df.iloc[i+HOLD_BARS].close);raw=side*(px/ep-1);reason='TIME'
    net=raw-COST
    return {'pnl':net*NOTIONAL,'win':int(net>0),'reason':reason,'entry':ep,'net_ret':net}


def build_rows(df):
    rows=[]
    for i in range(3,len(df)-HOLD_BARS-1):
        r=df.iloc[i];wib=r.ts+pd.Timedelta(hours=7)
        if wib.weekday()!=4:continue
        a=archetype(df,i)
        if a is None:continue
        signal_side=1 if a['direction']=='GREEN' else -1
        cont=trade(df,i,signal_side);rev=trade(df,i,-signal_side)
        if not cont or not rev:continue
        rows.append({'signal_ts':str(r.ts),'friday_wib':str(wib.date()),'entry_ts':str(df.iloc[i+1].ts),**a,
                     'cont_pnl':cont['pnl'],'cont_win':cont['win'],'cont_reason':cont['reason'],
                     'rev_pnl':rev['pnl'],'rev_win':rev['win'],'rev_reason':rev['reason']})
    return pd.DataFrame(rows)


def pf(vals):
    gp=sum(x for x in vals if x>0);gl=-sum(x for x in vals if x<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else None)


def stats(df,pnlcol):
    a=df[pnlcol].astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    w=sum(x>0 for x in a)
    return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}


def blocks(df,mode,key):
    dates=sorted(df.friday_wib.unique());chunks=np.array_split(np.array(dates,dtype=object),4);out={}
    for i,ch in enumerate(chunks):
        z=df[df.friday_wib.isin(set(ch)) & (df.archetype==key)]
        out[f'B{i+1}']=stats(z,f'{mode}_pnl')
    return out


def main():
    px=load_15m();df=build_rows(px)
    dates=sorted(df.friday_wib.unique());cut=int(math.floor(.70*len(dates)));disc_dates=set(dates[:cut]);val_dates=set(dates[cut:])
    df['period']=np.where(df.friday_wib.isin(disc_dates),'discovery','validation')
    disc=df[df.period=='discovery'];val=df[df.period=='validation']
    baseline={m:{'discovery':stats(disc,f'{m}_pnl'),'validation':stats(val,f'{m}_pnl'),'full':stats(df,f'{m}_pnl')} for m in ('cont','rev')}
    reports=[];eligible=[]
    for mode in ('cont','rev'):
        for key,z in disc.groupby('archetype'):
            s=stats(z,f'{mode}_pnl');q={'mode':mode,'archetype':key,**s};reports.append(q)
            if s['n']>=40 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['pf'] is not None and s['pf']>1:eligible.append(q)
    reports.sort(key=lambda q:(q['mode'],-q['wr'] if q['wr'] is not None else 1,-q['n'],q['archetype']))
    pd.DataFrame(reports).to_csv(OUT_DISC,index=False)
    eligible.sort(key=lambda q:(-q['wr'],-q['n'],-q['pf'],q['mode'],q['archetype']))
    out={'protocol':'C1','friday_dates':len(dates),'discovery_dates':len(disc_dates),'validation_dates':len(val_dates),
         'signal_rows':len(df),'archetypes_discovery':len(set(disc.archetype)),'discovery_eligible_80':len(eligible),'baseline':baseline,
         'top_discovery_support40':{}}
    for mode in ('cont','rev'):
        top=[q for q in reports if q['mode']==mode and q['n']>=40]
        top.sort(key=lambda q:(-q['wr'],-q['n'],q['archetype']))
        out['top_discovery_support40'][mode]=top[:10]
    if not eligible:
        out.update({'selected':None,'verdict':'REJECT_C1_80_CANDLE_IDENTIFIER','reason':'No frozen 15m archetype achieved discovery N>=40 and WR>=80%.'})
    else:
        q=eligible[0];mode=q['mode'];key=q['archetype']
        sd=stats(disc[disc.archetype==key],f'{mode}_pnl');sv=stats(val[val.archetype==key],f'{mode}_pnl');sf=stats(df[df.archetype==key],f'{mode}_pnl')
        bl=blocks(df,mode,key);pos=sum(x['n']>0 and x['pnl']>0 for x in bl.values())
        qualify=bool(sd['n']>=40 and sd['wr']>=.80 and sv['n']>=20 and sv['wr'] is not None and sv['wr']>=.80 and
                     sf['n']>=70 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and
                     baseline[mode]['validation']['wr'] is not None and sv['wr']>baseline[mode]['validation']['wr'] and pos>=3)
        out['selected']={'mode':mode,'archetype':key,'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos}
        out['verdict']='BTC_FRIDAY_15M_80_CANDIDATE' if qualify else 'REJECT_C1_80_CANDLE_IDENTIFIER'
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2):return '-' if x is None else f'{x:.{d}f}'
    md=['# BTC Friday All-15m Candle C1 — Result','',f"Friday dates: **{len(dates)}**; signal candles: **{len(df)}**",f"Discovery / validation dates: **{len(disc_dates)} / {len(val_dates)}**",f"Distinct discovery archetypes: **{out['archetypes_discovery']}**",f"Discovery archetypes passing 80% support screen: **{len(eligible)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} — best discovery archetypes with N>=40','', '| Archetype | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for q in out['top_discovery_support40'][mode]:md.append(f"| `{q['archetype']}` | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | ${F(q['pnl'],2)} | {F(q['pf'],3)} |")
        md.append('')
    if out.get('selected') is None:
        md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Discovery-selected archetype','',f"Mode **{s['mode'].upper()}**",f"`{s['archetype']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,x in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],2)} | ${F(x['exp'],3)} | {F(x['pf'],3)} |")
        md += ['','### Chronological blocks','','| Block | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for b,x in s['blocks'].items():md.append(f"| {b} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],2)} | {F(x['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future win probability. No runner-up validation or archetype retuning is authorized.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))

if __name__=='__main__':main()
