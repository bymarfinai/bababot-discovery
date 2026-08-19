#!/usr/bin/env python3
"""C7A: frozen BTC Friday premium-dislocation + OI-unwind event test."""
from __future__ import annotations
import csv, io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

import btc_friday_15m_derivatives_c5 as c5

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_C7A_Premium_Dislocation_Result.md'
OUT_JSON=ROOT/'BTC_Friday_C7A_Premium_Dislocation_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_C7A_Premium_Dislocation_Rows.csv'
BASE='https://data.binance.vision/data/futures/um'
START=c5.START; END=c5.END
LOOKBACK=pd.Timedelta(days=7)


def fetch_premium_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c7a/1.0'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:return []
        with zf.open(names[0]) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<5:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4])])
                except Exception:continue
    return out


def load_premium():
    src_start=(START-LOOKBACK-pd.Timedelta(days=2)).normalize()
    jobs=[];cur=pd.Timestamp(src_start.year,src_start.month,1,tz='UTC');em=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<em:
        ym=cur.strftime('%Y-%m')
        jobs.append(f'{BASE}/monthly/premiumIndexKlines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip')
        cur+=pd.offsets.MonthBegin(1)
    d=em
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d')
        jobs.append(f'{BASE}/daily/premiumIndexKlines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip')
        d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_premium_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    p=pd.DataFrame(rows,columns=['ts','p_open','p_high','p_low','p_close'])
    if p.empty:raise RuntimeError('no premiumIndexKlines rows; verify Binance Data Vision premiumIndexKlines path')
    p['ts']=pd.to_datetime(pd.to_numeric(p.ts),unit='ms',utc=True)
    p=p.dropna().drop_duplicates('ts').sort_values('ts')
    p=p[(p.ts>=src_start)&(p.ts<END)].set_index('ts',drop=False)
    if len(p)<80000:raise RuntimeError(f'insufficient premium rows {len(p)}')
    s=p.p_close.astype(float)
    p['prior7_mean']=s.rolling('7D',closed='left',min_periods=192).mean()
    p['prior7_std']=s.rolling('7D',closed='left',min_periods=192).std(ddof=0)
    p['premium_z']=(s-p.prior7_mean)/p.prior7_std
    return p


def stats(z):
    if z.empty:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    a=z.pnl.astype(float).tolist();wins=sum(v>0 for v in a);gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0)
    pf=gp/gl if gl>0 else (999.0 if gp>0 else None)
    return {'n':len(a),'wins':wins,'wr':wins/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf}


def blocks(df):
    dates=sorted(df.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):
        q=df[df.friday_wib.isin(set(ch))]
        out[f'B{i+1}']=stats(q)
    return out


def main():
    x=c5.load15();m=c5.load_metrics();p=load_premium();x=c5.geom_features(x)
    O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);wib=x.ts+pd.Timedelta(hours=7)
    all_fridays=sorted(set(str(d) for d in wib[(wib.dt.weekday==4)&(x.ts>=START)&(x.ts<END)].dt.date))
    cut=int(math.floor(.70*len(all_fridays)));disc_dates=set(all_fridays[:cut]);val_dates=set(all_fridays[cut:])
    rows=[];viol=0;premium_missing=0;metric_missing=0
    idx=np.flatnonzero((wib.dt.weekday.to_numpy()==4)&(C!=O));idx=idx[(idx>=4)&(idx+c5.HOLD<len(x)-1)]
    for i in idx:
        signal_t=x.ts.iloc[i]
        if signal_t<START or signal_t>=END:continue
        entry_t=x.ts.iloc[i]+pd.Timedelta(minutes=15)
        if signal_t not in p.index:premium_missing+=1;continue
        pr=p.loc[signal_t]
        z=float(pr.premium_z)
        if not math.isfinite(z):continue
        mf=c5.metric_at(m,entry_t)
        if mf is None:metric_missing+=1;continue
        oi=float(mf['oi_chg15']); rg=max(H[i]-L[i],1e-12);cp=(C[i]-L[i])/rg
        long_rule=(z<=-2.0 and oi<0 and C[i]>O[i] and cp>=.50)
        short_rule=(z>=2.0 and oi<0 and C[i]<O[i] and cp<=.50)
        if long_rule and short_rule:viol+=1;continue
        if not (long_rule or short_rule):continue
        side=1 if long_rule else -1
        ep=O[i+1];hs=H[i+1:i+1+c5.HOLD];ls=L[i+1:i+1+c5.HOLD];fc=C[i+c5.HOLD]
        pnl,win,reason=c5.resolve(ep,hs,ls,fc,side)
        dt=str(wib.iloc[i].date())
        rows.append({'signal_ts':str(signal_t),'entry_ts':str(x.ts.iloc[i+1]),'friday_wib':dt,'period':'discovery' if dt in disc_dates else 'validation',
                     'direction':'LONG' if side>0 else 'SHORT','premium_close':float(pr.p_close),'premium_z':z,'oi_chg15':oi,
                     'signal_ret':C[i]/O[i]-1.0,'close_pos':cp,'entry_open':ep,'pnl':pnl,'win':win,'reason':reason})
    df=pd.DataFrame(rows)
    if df.empty:
        out={'protocol':'C7A','verdict':'REJECT_C7A_PREMIUM_IDENTIFIER','reason':'No frozen premium-dislocation events qualified.','friday_dates':len(all_fridays),'premium_rows':len(p),'metrics_rows':len(m),'integrity_violations':viol}
        OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text('# BTC Friday C7A — Result\n\n**REJECT_C7A_PREMIUM_IDENTIFIER**\n\nNo frozen events qualified.\n');print(json.dumps(out,indent=2));return
    df.to_csv(OUT_ROWS,index=False)
    d=df[df.period=='discovery'];v=df[df.period=='validation'];sd=stats(d);sv=stats(v);sf=stats(df);bl=blocks(df)
    direction={k:stats(df[df.direction==k]) for k in ['LONG','SHORT']}
    good_blocks=sum(q['n']>=5 and q['wr'] is not None and q['wr']>.50 and q['pnl']>0 for q in bl.values())
    ok=bool(sd['n']>=12 and sd['wr'] is not None and sd['wr']>=.80 and sv['n']>=10 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=25 and sf['wr'] is not None and sf['wr']>=.80 and sv['pnl']>0 and sv['pf'] is not None and sv['pf']>1 and good_blocks>=3 and viol==0)
    out={'protocol':'C7A','friday_dates':len(all_fridays),'premium_rows':len(p),'metrics_rows':len(m),'events':len(df),'discovery':sd,'validation':sv,'full':sf,'direction_descriptive':direction,'blocks':bl,'promotion_quality_blocks':good_blocks,'premium_missing_signal_rows':premium_missing,'metric_missing_signal_rows':metric_missing,'integrity_violations':viol,'verdict':'BTC_FRIDAY_C7A_PREMIUM_80_CANDIDATE' if ok else 'REJECT_C7A_PREMIUM_IDENTIFIER'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    pct=lambda q:'-' if q is None else f'{100*q:.2f}%'
    md=['# BTC Friday C7A — Premium Dislocation + OI Unwind Result','',f"**Verdict: {out['verdict']}**",'',f"Friday dates: **{len(all_fridays)}**; premium rows: **{len(p)}**; metrics rows: **{len(m)}**; qualifying events: **{len(df)}**",f"Integrity violations: **{viol}**",'',
        'Frozen event: |premium z|>=2, OI15m<0, directionally confirming signal candle, next-15m-open execution, TP=SL1.3%, hold6h, fee0.15%.','',
        '## Primary','','| Cohort | N | Wins | WR | PnL | Exp/trade | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for name,q in [('Discovery',sd),('Validation',sv),('Full',sf)]:md.append(f"| {name} | {q['n']} | {q['wins']} | {pct(q['wr'])} | ${q['pnl']:.2f} | {'-' if q['exp'] is None else '$'+format(q['exp'],'.3f')} | {'-' if q['pf'] is None else format(q['pf'],'.3f')} |")
    md+=['','## Direction descriptive only','','| Direction | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
    for k,q in direction.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {pct(q['wr'])} | ${q['pnl']:.2f} | {'-' if q['pf'] is None else format(q['pf'],'.3f')} |")
    md+=['','## Chronological blocks','','| Block | N | Wins | WR | PnL |','|---|---:|---:|---:|---:|']
    for k,q in bl.items():md.append(f"| {k} | {q['n']} | {q['wins']} | {pct(q['wr'])} | ${q['pnl']:.2f} |")
    md+=['',f"Promotion-quality blocks: **{good_blocks}/4**.",'','No sigma/lookback/OI/direction/TP-SL rescue is authorized after result. Observed historical WR is not a future guarantee.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
