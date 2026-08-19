#!/usr/bin/env python3
"""C9A: frozen Binance spot-vs-futures lead/lag event on BTC Fridays."""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

import btc_friday_15m_candle_taker_c4 as c4

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_C9A_Spot_Futures_LeadLag_Result.md';OUT_JSON=ROOT/'BTC_Friday_C9A_Spot_Futures_LeadLag_Result.json';OUT_ROWS=ROOT/'BTC_Friday_C9A_Spot_Futures_LeadLag_Rows.csv'
START=c4.START;END=c4.END;BASE='https://data.binance.vision/data/spot'


def fetch_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c9a/1.0'})
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

def load_spot():
    src_start=(START-pd.Timedelta(days=8)).normalize();jobs=[];cur=pd.Timestamp(src_start.year,src_start.month,1,tz='UTC');em=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<em:
        ym=cur.strftime('%Y-%m');jobs.append(f'{BASE}/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip');cur+=pd.offsets.MonthBegin(1)
    d=em
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d');jobs.append(f'{BASE}/daily/klines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip');d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    s=pd.DataFrame(rows,columns=['ts','s_open','s_high','s_low','s_close','s_quote_volume','s_taker_buy_quote'])
    if s.empty:raise RuntimeError('no spot rows')
    s['ts']=pd.to_datetime(pd.to_numeric(s.ts),unit='ms',utc=True);s=s.dropna().drop_duplicates('ts').sort_values('ts');s=s[(s.ts>=src_start)&(s.ts<END)]
    if len(s)<90000:raise RuntimeError(f'insufficient spot rows {len(s)}')
    return s

def stat(z):
    if z.empty:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    a=z.pnl.astype(float).tolist();w=sum(v>0 for v in a);gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);pf=gp/gl if gl>0 else (999. if gp>0 else None)
    return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf}

def main():
    f=c4.load15().copy();s=load_spot();f=f.rename(columns={'open':'f_open','high':'f_high','low':'f_low','close':'f_close','quote_volume':'f_quote_volume','taker_buy_quote':'f_taker_buy_quote'})
    z=f.merge(s,on='ts',how='inner',validate='one_to_one').sort_values('ts').reset_index(drop=True)
    if len(z)<90000:raise RuntimeError(f'insufficient aligned rows {len(z)}')
    z['spot_ret15']=z.s_close/z.s_open-1.;z['fut_ret15']=z.f_close/z.f_open-1.;z['lead_spread']=z.spot_ret15-z.fut_ret15
    z['spot_taker_imbalance']=np.where(z.s_quote_volume>0,2*z.s_taker_buy_quote/z.s_quote_volume-1,np.nan);z['fut_taker_imbalance']=np.where(z.f_quote_volume>0,2*z.f_taker_buy_quote/z.f_quote_volume-1,np.nan);z['flow_divergence']=z.spot_taker_imbalance-z.fut_taker_imbalance
    q=z.set_index('ts');ls=q.lead_spread.astype(float);mu=ls.rolling('7D',closed='left',min_periods=192).mean();sd=ls.rolling('7D',closed='left',min_periods=192).std(ddof=0);q['lead_z7d']=(ls-mu)/sd;z=q.reset_index()
    wib=z.ts+pd.Timedelta(hours=7);all_dates=sorted(set(str(d) for d in wib[(wib.dt.weekday==4)&(z.ts>=START)&(z.ts<END)].dt.date));cut=int(math.floor(.70*len(all_dates)));dd=set(all_dates[:cut]);rows=[];viol=0
    O=z.f_open.to_numpy(float);H=z.f_high.to_numpy(float);L=z.f_low.to_numpy(float);C=z.f_close.to_numpy(float);idx=np.flatnonzero(wib.dt.weekday.to_numpy()==4);idx=idx[(idx+c4.HOLD<len(z)-1)]
    for i in idx:
        if z.ts.iloc[i]<START or z.ts.iloc[i]>=END:continue
        vals=[z.lead_z7d.iloc[i],z.spot_ret15.iloc[i],z.spot_taker_imbalance.iloc[i],z.flow_divergence.iloc[i]]
        if not all(math.isfinite(float(v)) for v in vals):continue
        l=bool(vals[0]>=2 and vals[1]>0 and vals[2]>0 and vals[3]>0);sh=bool(vals[0]<=-2 and vals[1]<0 and vals[2]<0 and vals[3]<0)
        if l and sh:viol+=1;continue
        if not(l or sh):continue
        side=1 if l else -1;ep=O[i+1];hs=H[i+1:i+1+c4.HOLD];los=L[i+1:i+1+c4.HOLD];fc=C[i+c4.HOLD];pnl,win,reason=c4.resolve(ep,hs,los,fc,side);day=str(wib.iloc[i].date())
        rows.append({'signal_ts':str(z.ts.iloc[i]),'entry_ts':str(z.ts.iloc[i+1]),'friday_wib':day,'period':'discovery' if day in dd else 'validation','direction':'LONG' if side>0 else 'SHORT','spot_ret15':float(vals[1]),'fut_ret15':float(z.fut_ret15.iloc[i]),'lead_spread':float(z.lead_spread.iloc[i]),'lead_z7d':float(vals[0]),'spot_taker_imbalance':float(vals[2]),'fut_taker_imbalance':float(z.fut_taker_imbalance.iloc[i]),'flow_divergence':float(vals[3]),'pnl':pnl,'win':win,'reason':reason})
    df=pd.DataFrame(rows)
    if df.empty:
        out={'protocol':'C9A','aligned_rows':len(z),'friday_dates':len(all_dates),'events':0,'integrity_violations':viol,'verdict':'REJECT_C9A_SPOT_LEAD_IDENTIFIER','reason':'No frozen spot-lead events qualified.'};OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday C9A — Result\n\n**REJECT_C9A_SPOT_LEAD_IDENTIFIER**\n\nNo frozen events qualified.\n');print(json.dumps(out,indent=2));return
    df.to_csv(OUT_ROWS,index=False);d=df[df.period=='discovery'];v=df[df.period=='validation'];sd0=stat(d);sv=stat(v);sf=stat(df);direction={k:stat(df[df.direction==k]) for k in ['LONG','SHORT']};blocks={}
    for i,ch in enumerate(np.array_split(np.array(sorted(df.friday_wib.unique()),dtype=object),4)):blocks[f'B{i+1}']=stat(df[df.friday_wib.isin(set(ch))])
    good=sum(q['n']>=5 and q['wr'] is not None and q['wr']>.50 and q['pnl']>0 for q in blocks.values());ok=bool(sd0['n']>=12 and sd0['wr'] is not None and sd0['wr']>=.80 and sv['n']>=10 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=25 and sf['wr'] is not None and sf['wr']>=.80 and sv['pnl']>0 and sv['pf'] is not None and sv['pf']>1 and good>=3 and viol==0)
    out={'protocol':'C9A','aligned_rows':len(z),'friday_dates':len(all_dates),'events':len(df),'discovery':sd0,'validation':sv,'full':sf,'direction_descriptive':direction,'blocks':blocks,'promotion_quality_blocks':good,'integrity_violations':viol,'verdict':'BTC_FRIDAY_C9A_SPOT_LEAD_80_CANDIDATE' if ok else 'REJECT_C9A_SPOT_LEAD_IDENTIFIER'};OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    P=lambda x:'-' if x is None else f'{100*x:.2f}%';md=['# BTC Friday C9A — Spot-vs-Futures Lead/Lag Result','',f"**Verdict: {out['verdict']}**",'',f"Aligned 15m rows **{len(z)}**; Friday dates **{len(all_dates)}**; qualifying events **{len(df)}**; integrity **{viol}**.",'','Frozen event: |spot-minus-futures return z|>=2 vs prior7d, spot return/taker/flow divergence aligned with catch-up direction; next-futures-15m-open execution.','', '## Primary','','| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for n,qv in [('Discovery',sd0),('Validation',sv),('Full',sf)]:md.append(f"| {n} | {qv['n']} | {qv['wins']} | {P(qv['wr'])} | ${qv['pnl']:.2f} | {'-' if qv['exp'] is None else '$'+format(qv['exp'],'.3f')} | {'-' if qv['pf'] is None else format(qv['pf'],'.3f')} |")
    md+=['','## Direction descriptive only','','| Direction | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,qv in direction.items():md.append(f"| {k} | {qv['n']} | {qv['wins']} | {P(qv['wr'])} | ${qv['pnl']:.2f} |")
    md+=['','## Blocks','','| Block | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,qv in blocks.items():md.append(f"| {k} | {qv['n']} | {qv['wins']} | {P(qv['wr'])} | ${qv['pnl']:.2f} |")
    md+=['',f"Promotion-quality blocks **{good}/4**.",'','No z/lookback/direction/flow/TP-SL rescue is authorized after result.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
