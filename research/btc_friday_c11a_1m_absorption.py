#!/usr/bin/env python3
"""C11A: frozen final-5m 1m-flow absorption event within BTC Friday 15m signals."""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

import btc_friday_15m_candle_taker_c4 as c4

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_C11A_1m_Absorption_Result.md';OUT_JSON=ROOT/'BTC_Friday_C11A_1m_Absorption_Result.json';OUT_ROWS=ROOT/'BTC_Friday_C11A_1m_Absorption_Rows.csv'
BASE='https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m';START_LOCAL=pd.Timestamp('2023-12-08');END_LOCAL=pd.Timestamp('2026-08-14')

def friday_freezes():
    return [pd.Timestamp(d.date()).tz_localize('Asia/Jakarta').tz_convert('UTC') for d in pd.date_range(START_LOCAL,END_LOCAL,freq='W-FRI')]
def needed_days():
    ds=set()
    for fs in friday_freezes():
        for off in (-1,0,1):ds.add((fs.normalize()+pd.Timedelta(days=off)).strftime('%Y-%m-%d'))
    return sorted(ds)
def fetch_day(ds):
    url=f'{BASE}/BTCUSDT-1m-{ds}.zip';r=requests.get(url,timeout=45,headers={'User-Agent':'bababot-c11a/1.0'})
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
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[7]),float(row[10])])
                except Exception:continue
    return out
def load1m():
    days=needed_days();rows=[]
    with ThreadPoolExecutor(max_workers=24) as ex:
        fs={ex.submit(fetch_day,d):d for d in days}
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','quote_volume','taker_buy_quote'])
    if x.empty:raise RuntimeError('no 1m rows')
    x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True);x=x.dropna().drop_duplicates('ts').sort_values('ts').set_index('ts',drop=False)
    return x,len(days)
def resample(x):
    c5=x.close.resample('5min',label='left',closed='left').count();h5=x.resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),quote_volume=('quote_volume','sum'),taker_buy_quote=('taker_buy_quote','sum'));h5=h5[c5==5].dropna();h5['flow']=np.where(h5.quote_volume>0,2*h5.taker_buy_quote/h5.quote_volume-1,np.nan)
    c15=x.close.resample('15min',label='left',closed='left').count();h15=x.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'));h15=h15[c15==15].dropna();return h5,h15
def stat(z):
    if z.empty:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    a=z.pnl.astype(float).tolist();w=sum(v>0 for v in a);gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);pf=gp/gl if gl>0 else (999. if gp>0 else None);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf}
def main():
    x,day_count=load1m();h5,h15=resample(x);freezes=friday_freezes();dates=[str((fs+pd.Timedelta(hours=7)).date()) for fs in freezes];cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);rows=[];viol=0;incomplete=0
    for fs in freezes:
        day=str((fs+pd.Timedelta(hours=7)).date())
        for k in range(96):
            t=fs+pd.Timedelta(minutes=15*k)
            if t not in h15.index or t+pd.Timedelta(minutes=10) not in h5.index:incomplete+=1;continue
            sig=h15.loc[t];last=h5.loc[t+pd.Timedelta(minutes=10)];base=h5[(h5.index>=t-pd.Timedelta(hours=24))&(h5.index<t)]
            if len(base)<144:incomplete+=1;continue
            medq=float(base.quote_volume.median());medf=float(base.flow.abs().median());qv=float(last.quote_volume);flow=float(last.flow);ret5=float(last.close/last.open-1.);rg=max(float(sig.high-sig.low),1e-12);cp=float((sig.close-sig.low)/rg)
            if not all(math.isfinite(v) for v in [medq,medf,qv,flow,ret5,cp]) or medq<=0 or medf<=0:continue
            vr=qv/medq;fr=abs(flow)/medf;l=bool(flow<0 and ret5>=0 and vr>1 and fr>=1 and cp>=.5);sh=bool(flow>0 and ret5<=0 and vr>1 and fr>=1 and cp<=.5)
            if l and sh:viol+=1;continue
            if not(l or sh):continue
            future=[t+pd.Timedelta(minutes=15*j) for j in range(1,25)]
            if any(u not in h15.index for u in future):incomplete+=1;continue
            side=1 if l else -1;ep=float(h15.loc[future[0]].open);hs=np.array([float(h15.loc[u].high) for u in future]);ls=np.array([float(h15.loc[u].low) for u in future]);fc=float(h15.loc[future[-1]].close);pnl,win,reason=c4.resolve(ep,hs,ls,fc,side)
            rows.append({'signal_ts':str(t),'entry_ts':str(future[0]),'friday_wib':day,'period':'discovery' if day in dd else 'validation','direction':'LONG' if side>0 else 'SHORT','ret5':ret5,'flow5':flow,'qv5':qv,'vol_rel':vr,'flow_strength_rel':fr,'close_pos':cp,'pnl':pnl,'win':win,'reason':reason})
    df=pd.DataFrame(rows)
    if df.empty:
        out={'protocol':'C11A','download_days':day_count,'rows_1m':len(x),'fridays':len(dates),'events':0,'integrity_violations':viol,'incomplete_windows':incomplete,'verdict':'REJECT_C11A_1M_ABSORPTION_IDENTIFIER'};OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday C11A — Result\n\n**REJECT_C11A_1M_ABSORPTION_IDENTIFIER**\n\nNo frozen events.\n');print(json.dumps(out,indent=2));return
    df.to_csv(OUT_ROWS,index=False);d=df[df.period=='discovery'];v=df[df.period=='validation'];sd=stat(d);sv=stat(v);sf=stat(df);direction={k:stat(df[df.direction==k]) for k in ['LONG','SHORT']};blocks={}
    for i,ch in enumerate(np.array_split(np.array(sorted(df.friday_wib.unique()),dtype=object),4)):blocks[f'B{i+1}']=stat(df[df.friday_wib.isin(set(ch))])
    good=sum(q['n']>=5 and q['wr'] is not None and q['wr']>.50 and q['pnl']>0 for q in blocks.values());ok=bool(sd['n']>=12 and sd['wr'] is not None and sd['wr']>=.80 and sv['n']>=10 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=25 and sf['wr'] is not None and sf['wr']>=.80 and sv['pnl']>0 and sv['pf'] is not None and sv['pf']>1 and good>=3 and viol==0);out={'protocol':'C11A','download_days':day_count,'rows_1m':len(x),'fridays':len(dates),'events':len(df),'discovery':sd,'validation':sv,'full':sf,'direction_descriptive':direction,'blocks':blocks,'promotion_quality_blocks':good,'integrity_violations':viol,'incomplete_windows':incomplete,'verdict':'BTC_FRIDAY_C11A_1M_ABSORPTION_80_CANDIDATE' if ok else 'REJECT_C11A_1M_ABSORPTION_IDENTIFIER'};OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    P=lambda q:'-' if q is None else f'{100*q:.2f}%';md=['# BTC Friday C11A — 1-Minute Absorption Result','',f"**Verdict: {out['verdict']}**",'',f"Downloaded UTC days **{day_count}**; 1m rows **{len(x)}**; Fridays **{len(dates)}**; events **{len(df)}**; integrity **{viol}**; incomplete windows **{incomplete}**.",'','Frozen event: final-5m taker aggression fails to move price in its own direction while volume and flow strength exceed prior24h medians; trade reversal next15m open.','','| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for n,q in [('Discovery',sd),('Validation',sv),('Full',sf)]:md.append(f"| {n} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} | {'-' if q['exp'] is None else '$'+format(q['exp'],'.3f')} | {'-' if q['pf'] is None else format(q['pf'],'.3f')} |")
    md+=['','## Direction descriptive only','','| Direction | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,q in direction.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} |")
    md+=['','## Blocks','','| Block | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,q in blocks.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {P(q['wr'])} | ${q['pnl']:.2f} |")
    md+=['',f"Promotion-quality blocks **{good}/4**.",'','No final-window/flow/volume/baseline/close-position/direction/TP-SL rescue is authorized.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
