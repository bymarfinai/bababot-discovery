#!/usr/bin/env python3
"""C10A: frozen BTC Friday large-average-ticket directional impulse."""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

import btc_friday_15m_candle_taker_c4 as c4

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_C10A_Large_Ticket_Impulse_Result.md';OUT_JSON=ROOT/'BTC_Friday_C10A_Large_Ticket_Impulse_Result.json';OUT_ROWS=ROOT/'BTC_Friday_C10A_Large_Ticket_Impulse_Rows.csv'
START=c4.START;END=c4.END;BASE='https://data.binance.vision/data/futures/um'

def fetch_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c10a/1.0'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:return []
        with zf.open(names[0]) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<11:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[7]),float(row[10]),float(row[8])])
                except Exception:continue
    return out

def load():
    src=(START-pd.Timedelta(days=8)).normalize();jobs=[];cur=pd.Timestamp(src.year,src.month,1,tz='UTC');em=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<em:
        ym=cur.strftime('%Y-%m');jobs.append(f'{BASE}/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip');cur+=pd.offsets.MonthBegin(1)
    d=em
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d');jobs.append(f'{BASE}/daily/klines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip');d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','quote_volume','taker_buy_quote','trades']);x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True);x=x.dropna().drop_duplicates('ts').sort_values('ts');x=x[(x.ts>=src)&(x.ts<END)].set_index('ts',drop=False)
    if len(x)<90000:raise RuntimeError(f'insufficient rows {len(x)}')
    x['avg_ticket']=np.where(x.trades>0,x.quote_volume/x.trades,np.nan);a=x.avg_ticket.astype(float);x['ticket_z7d']=(a-a.rolling('7D',closed='left',min_periods=192).mean())/a.rolling('7D',closed='left',min_periods=192).std(ddof=0);x['taker_imbalance']=np.where(x.quote_volume>0,2*x.taker_buy_quote/x.quote_volume-1,np.nan);rg=np.maximum(x.high-x.low,1e-12);x['close_pos']=(x.close-x.low)/rg
    return x.reset_index(drop=True)
def stat(z):
    if z.empty:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    a=z.pnl.astype(float).tolist();w=sum(v>0 for v in a);gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);pf=gp/gl if gl>0 else (999. if gp>0 else None);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf}
def main():
    x=load();O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);wib=x.ts+pd.Timedelta(hours=7);dates=sorted(set(str(d) for d in wib[(wib.dt.weekday==4)&(x.ts>=START)&(x.ts<END)].dt.date));cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);rows=[];viol=0
    idx=np.flatnonzero(wib.dt.weekday.to_numpy()==4);idx=idx[(idx+c4.HOLD<len(x)-1)]
    for i in idx:
        if x.ts.iloc[i]<START or x.ts.iloc[i]>=END:continue
        z=float(x.ticket_z7d.iloc[i]);imb=float(x.taker_imbalance.iloc[i]);cp=float(x.close_pos.iloc[i])
        if not all(math.isfinite(v) for v in [z,imb,cp]):continue
        l=bool(z>=2 and C[i]>O[i] and imb>0 and cp>=.5);sh=bool(z>=2 and C[i]<O[i] and imb<0 and cp<=.5)
        if l and sh:viol+=1;continue
        if not(l or sh):continue
        side=1 if l else -1;ep=O[i+1];hs=H[i+1:i+1+c4.HOLD];ls=L[i+1:i+1+c4.HOLD];fc=C[i+c4.HOLD];pnl,win,reason=c4.resolve(ep,hs,ls,fc,side);day=str(wib.iloc[i].date());rows.append({'signal_ts':str(x.ts.iloc[i]),'entry_ts':str(x.ts.iloc[i+1]),'friday_wib':day,'period':'discovery' if day in dd else 'validation','direction':'LONG' if side>0 else 'SHORT','avg_ticket':float(x.avg_ticket.iloc[i]),'ticket_z7d':z,'taker_imbalance':imb,'close_pos':cp,'pnl':pnl,'win':win,'reason':reason})
    df=pd.DataFrame(rows)
    if df.empty:
        out={'protocol':'C10A','friday_dates':len(dates),'events':0,'integrity_violations':viol,'verdict':'REJECT_C10A_LARGE_TICKET_IDENTIFIER'};OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday C10A — Result\n\n**REJECT_C10A_LARGE_TICKET_IDENTIFIER**\n\nNo frozen events.\n');print(json.dumps(out,indent=2));return
    df.to_csv(OUT_ROWS,index=False);d=df[df.period=='discovery'];v=df[df.period=='validation'];sd=stat(d);sv=stat(v);sf=stat(df);direction={k:stat(df[df.direction==k]) for k in ['LONG','SHORT']};blocks={}
    for i,ch in enumerate(np.array_split(np.array(sorted(df.friday_wib.unique()),dtype=object),4)):blocks[f'B{i+1}']=stat(df[df.friday_wib.isin(set(ch))])
    good=sum(q['n']>=5 and q['wr'] is not None and q['wr']>.50 and q['pnl']>0 for q in blocks.values());ok=bool(sd['n']>=12 and sd['wr'] is not None and sd['wr']>=.80 and sv['n']>=10 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=25 and sf['wr'] is not None and sf['wr']>=.80 and sv['pnl']>0 and sv['pf'] is not None and sv['pf']>1 and good>=3 and viol==0);out={'protocol':'C10A','rows':len(x),'friday_dates':len(dates),'events':len(df),'discovery':sd,'validation':sv,'full':sf,'direction_descriptive':direction,'blocks':blocks,'promotion_quality_blocks':good,'integrity_violations':viol,'verdict':'BTC_FRIDAY_C10A_LARGE_TICKET_80_CANDIDATE' if ok else 'REJECT_C10A_LARGE_TICKET_IDENTIFIER'};OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    P=lambda q:'-' if q is None else f'{100*q:.2f}%';md=['# BTC Friday C10A — Large-Ticket Impulse Result','',f"**Verdict: {out['verdict']}**",'',f"15m rows **{len(x)}**; Fridays **{len(dates)}**; events **{len(df)}**; integrity **{viol}**.",'','Frozen event: average quote/trade z>=2 vs prior7d + candle/taker direction agreement; continuation next-15m-open.','','| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for n,q in [('Discovery',sd),('Validation',sv),('Full',sf)]:md.append(f"| {n} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} | {'-' if q['exp'] is None else '$'+format(q['exp'],'.3f')} | {'-' if q['pf'] is None else format(q['pf'],'.3f')} |")
    md+=['','## Direction descriptive only','','| Direction | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,q in direction.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} |")
    md+=['','## Blocks','','| Block | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,q in blocks.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} |")
    md+=['',f"Promotion-quality blocks **{good}/4**.",'','No ticket threshold/lookback/direction/reversal/TP-SL rescue is authorized.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
