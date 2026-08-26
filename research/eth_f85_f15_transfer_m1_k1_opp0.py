#!/usr/bin/env python3
from __future__ import annotations
import io, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX='ETH_F85_F15_TRANSFER_M1_K1_OPP0'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
BASE='https://data.binance.vision/data/futures/um'
START=pd.Timestamp('2020-01-01',tz='UTC')
END=pd.Timestamp('2026-08-26',tz='UTC')
BAR5=pd.Timedelta(minutes=5); REF_DUR=pd.Timedelta(hours=5,minutes=30); EXEC_DUR=pd.Timedelta(hours=6,minutes=30)
PARTS={
 'external':(pd.Timestamp('2020-01-01',tz='UTC'),pd.Timestamp('2022-01-01',tz='UTC')),
 'development':(pd.Timestamp('2022-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')),
 'reference_validation':(pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2026-07-30',tz='UTC')),
 'august':(pd.Timestamp('2026-08-01',tz='UTC'),END),
}
MAJOR=('external','development','reference_validation')
CLOCKS={'ALT_0330':210,'RAW_0530':330,'LONDON':480,'RAW_2330':1410,'SHORT_2000':1200}
SIDE={k:('SHORT' if k=='SHORT_2000' else 'LONG') for k in CLOCKS}

def urls(symbol):
 out=[]; m=pd.Timestamp(START.year,START.month,1,tz='UTC'); em=pd.Timestamp(END.year,END.month,1,tz='UTC')
 while m<em:
  ym=m.strftime('%Y-%m'); out.append(f'{BASE}/monthly/klines/{symbol}/5m/{symbol}-5m-{ym}.zip'); m+=pd.offsets.MonthBegin(1)
 d=em
 while d<END.normalize():
  ds=d.strftime('%Y-%m-%d'); out.append(f'{BASE}/daily/klines/{symbol}/5m/{symbol}-5m-{ds}.zip'); d+=pd.Timedelta(days=1)
 return out

def fetch_one(u):
 r=requests.get(u,timeout=90,headers={'User-Agent':'bababot-eth-m1/1.0'})
 if r.status_code==404:return None
 r.raise_for_status()
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  names=[n for n in z.namelist() if n.lower().endswith('.csv')]
  if not names:return None
  with z.open(names[0]) as f:
   return pd.read_csv(f,header=None,usecols=[0,1,2,3,4],names=['ts','open','high','low','close'])

def load5(symbol):
 frames=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  futs=[ex.submit(fetch_one,u) for u in urls(symbol)]
  for f in as_completed(futs):
   z=f.result()
   if z is not None and len(z):frames.append(z)
 if not frames:raise RuntimeError(f'no {symbol} data')
 x=pd.concat(frames,ignore_index=True); t=pd.to_numeric(x.ts,errors='coerce'); t=np.where(t>100_000_000_000_000,t/1000.0,t)
 x['ts']=pd.to_datetime(t,unit='ms',utc=True,errors='coerce')
 for c in ['open','high','low','close']:x[c]=pd.to_numeric(x[c],errors='coerce')
 x=x.dropna().drop_duplicates('ts').sort_values('ts'); x=x[(x.ts>=START)&(x.ts<END)].set_index('ts')
 expected=int((x.index[-1]-x.index[0])/BAR5)+1; cov=len(x)/expected
 if cov<.995:raise RuntimeError(f'{symbol} coverage too low {cov:.6f}')
 return x,cov

def part_for(es):
 for n,(a,z) in PARTS.items():
  if a<=es<z:return n
 return None

def sl(x,a,z):
 i=int(x.index.searchsorted(a)); j=int(x.index.searchsorted(z)); return x.iloc[i:j]

def classify(exe,H,L,side):
 hi_touch=False; lo_touch=False; hi_vis=0; lo_vis=0; state='SEEK_K1'; k1_start=pd.NaT; k1_signal=pd.NaT; leave_start=pd.NaT; leave_ts=pd.NaT
 for ts,r in exe.iterrows():
  hi=float(r.high); lo=float(r.low); cl=float(r.close)
  if state=='SEEK_K1':
   if cl>H or cl<L:return {'qualified':False,'reason':'BREAK_BEFORE_K1'}
   hit_hi=hi>=H and cl<=H; hit_lo=lo<=L and cl>=L
   if hit_hi and hit_lo:return {'qualified':False,'reason':'AMBIGUOUS_BOTH_LEVELS'}
   if side=='LONG':
    if hit_lo and not lo_touch:lo_vis+=1
    if hit_hi and not hi_touch:
     hi_vis+=1
     if hi_vis==1 and lo_vis==0:
      k1_start=ts;k1_signal=ts+BAR5;state='K1_EPISODE'
    hi_touch=bool(hit_hi);lo_touch=bool(hit_lo)
    if lo_vis>0 and state=='SEEK_K1':return {'qualified':False,'reason':'OPPOSITE_VISIT_BEFORE_K1'}
   else:
    if hit_hi and not hi_touch:hi_vis+=1
    if hit_lo and not lo_touch:
     lo_vis+=1
     if lo_vis==1 and hi_vis==0:
      k1_start=ts;k1_signal=ts+BAR5;state='K1_EPISODE'
    hi_touch=bool(hit_hi);lo_touch=bool(hit_lo)
    if hi_vis>0 and state=='SEEK_K1':return {'qualified':False,'reason':'OPPOSITE_VISIT_BEFORE_K1'}
   continue
  if state=='K1_EPISODE':
   if cl>H or cl<L:return {'qualified':True,'k1_start':k1_start,'k1_signal':k1_signal,'leave':False,'terminal':'BREAK_DURING_K1'}
   same=(hi>=H and cl<=H) if side=='LONG' else (lo<=L and cl>=L)
   if same:continue
   leave_start=ts;leave_ts=ts+BAR5;state='AFTER_LEAVE';continue
  if state=='AFTER_LEAVE':
   h2=(hi>=H) if side=='LONG' else (lo<=L)
   opp=(cl<L) if side=='LONG' else (cl>H)
   if h2 and opp:term='AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
   elif h2:term='H2_ARRIVAL'
   elif opp:term='OPPOSITE_BREAK_BEFORE_H2'
   else:continue
   mins=float((ts+BAR5-leave_ts)/pd.Timedelta(minutes=1)) if term=='H2_ARRIVAL' else np.nan
   return {'qualified':True,'k1_start':k1_start,'k1_signal':k1_signal,'leave':True,'leave_start':leave_start,'leave_ts':leave_ts,'terminal':term,'terminal_start':ts,'minutes_leave_to_h2':mins}
 if state=='SEEK_K1':return {'qualified':False,'reason':'NO_K1'}
 if state=='K1_EPISODE':return {'qualified':True,'k1_start':k1_start,'k1_signal':k1_signal,'leave':False,'terminal':'NO_CAUSAL_LEAVE_BY_END'}
 return {'qualified':True,'k1_start':k1_start,'k1_signal':k1_signal,'leave':True,'leave_start':leave_start,'leave_ts':leave_ts,'terminal':'NO_H2_BY_END','terminal_start':pd.NaT,'minutes_leave_to_h2':np.nan}

def synth():
 idx=pd.date_range('2026-01-05 13:30',periods=7,freq='5min',tz='UTC'); H=100.;L=90.
 q=pd.DataFrame([
  [99,100.2,98,99.5],[99.5,100.1,98.5,99.2],[99.2,99.6,97,98],[98,99,96,98.5],[98.5,100.1,98,99.8],[99.8,100.5,99,100.2],[100.2,101,100,100.8]],index=idx,columns=['open','high','low','close'])
 a=classify(q,H,L,'LONG'); assert a['qualified'] and a['leave'] and a['terminal']=='H2_ARRIVAL' and a['leave_start']==idx[2]
 q2=q.copy(); q2.iloc[0]=[95,99,89.5,91]; assert not classify(q2,H,L,'LONG')['qualified']
 q3=q.copy(); q3.iloc[4]=[98.5,100.1,89,89.5]; assert classify(q3,H,L,'LONG')['terminal']=='AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
 q4=q.iloc[:4].copy(); assert classify(q4,H,L,'LONG')['terminal']=='NO_H2_BY_END'
 # short mirror
 s=q.copy(); s[['open','high','low','close']]=190-s[['open','low','high','close']].to_numpy()[:,[0,1,2,3]]
 # dedicated simple short path
 s=pd.DataFrame([[91,92,89.8,90.5],[90.5,91.5,89.9,90.8],[90.8,93,90.2,92],[92,94,90.5,92.5],[92.5,93,89.7,90.1]],index=idx[:5],columns=['open','high','low','close'])
 b=classify(s,100,90,'SHORT'); assert b['qualified'] and b['leave'] and b['terminal']=='H2_ARRIVAL'

def run_symbol(symbol,x):
 rows=[]; anchors=pd.date_range(START.normalize(),END.normalize(),freq='D',tz='UTC')
 for a in anchors:
  for clock,cm in CLOCKS.items():
   rs=a+pd.Timedelta(minutes=cm); re=rs+REF_DUR; es=re; ee=es+EXEC_DUR; p=part_for(es)
   if p is None or es.weekday()>=5 or ee>END:continue
   ref=sl(x,rs,re); exe=sl(x,es,ee)
   if len(ref)!=66 or len(exe)!=78:continue
   H=float(ref.high.max());L=float(ref.low.min())
   if not H>L:continue
   z=classify(exe,H,L,SIDE[clock]); z.update(symbol=symbol,clock=clock,side=SIDE[clock],partition=p,reference_start=rs,execution_start=es,H=H,L=L,R=H-L)
   rows.append(z)
 return pd.DataFrame(rows)

def summary(detail):
 rows=[]
 groups=[]
 for sym in ('BTCUSDT','ETHUSDT'):
  for clock in CLOCKS:
   for p in (*PARTS.keys(),'POOLED_MAJOR'):
    q=detail[(detail.symbol==sym)&(detail.clock==clock)]
    q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
    complete=len(q); k=q[q.qualified.fillna(False).astype(bool)]; lv=k[k.leave.fillna(False).astype(bool)] if len(k) else k
    h=int((lv.terminal=='H2_ARRIVAL').sum()) if len(lv) else 0; o=int((lv.terminal=='OPPOSITE_BREAK_BEFORE_H2').sum()) if len(lv) else 0; amb=int((lv.terminal=='AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()) if len(lv) else 0; no=int((lv.terminal=='NO_H2_BY_END').sum()) if len(lv) else 0
    rows.append(dict(symbol=sym,clock=clock,side=SIDE[clock],partition=p,sessions=complete,k1_opp0=len(k),k1_rate=len(k)/complete if complete else np.nan,causal_leave=len(lv),leave_rate=len(lv)/len(k) if len(k) else np.nan,h2=h,opposite=o,ambiguous=amb,no_h2=no,h2_rate=h/len(lv) if len(lv) else np.nan,resolved_h2_wr=h/(h+o) if h+o else np.nan,median_min_to_h2=pd.to_numeric(lv.loc[lv.terminal=='H2_ARRIVAL','minutes_leave_to_h2'],errors='coerce').median() if h else np.nan))
 return pd.DataFrame(rows)

def main():
 synth(); data={}; cov={}
 for sym in ('BTCUSDT','ETHUSDT'):data[sym],cov[sym]=load5(sym)
 detail=pd.concat([run_symbol(s,data[s]) for s in data],ignore_index=True); detail.to_csv(OUT_DETAIL,index=False)
 s=summary(detail)
 # transfer gate on pooled major
 gate=[]
 for clock in CLOCKS:
  e=s[(s.symbol=='ETHUSDT')&(s.clock==clock)&(s.partition=='POOLED_MAJOR')].iloc[0]; b=s[(s.symbol=='BTCUSDT')&(s.clock==clock)&(s.partition=='POOLED_MAJOR')].iloc[0]
  ok=(e.k1_opp0>=30 and e.causal_leave>=25 and e.h2_rate>=.60 and e.resolved_h2_wr>=.65 and e.h2_rate>=b.h2_rate-.10)
  gate.append((clock,bool(ok)))
 gmap=dict(gate); overall=sum(gmap[c] for c in ('ALT_0330','RAW_0530','LONDON','RAW_2330'))>=3 and gmap['SHORT_2000']
 status='ETH_M1_K1_OPP0_STRUCTURAL_REPLICATION_SUPPORTED' if overall else 'ETH_M1_K1_OPP0_STRUCTURAL_REPLICATION_NOT_SUPPORTED'
 s['m1_replication']=''
 for clock,ok in gate:s.loc[(s.symbol=='ETHUSDT')&(s.clock==clock)&(s.partition=='POOLED_MAJOR'),'m1_replication']='PASS' if ok else 'FAIL'
 s.to_csv(OUT_SUM,index=False); OUT_STATUS.write_text(status+'\n')
 lines=['# ETH F85/F15 Transfer — M1 K1 OPP0 Structural Replication — Result','',f'Raw 5m coverage: BTC **{cov["BTCUSDT"]:.4%}**, ETH **{cov["ETHUSDT"]:.4%}**.','', 'M1 only: no F85/F15, no entry, no stop, no target, no PnL.','', '## Pooled-major structural comparison','', '| Clock | Side | ETH K1 | ETH Leave | ETH H2 Rate | ETH Resolved H2 WR | BTC H2 Rate | ETH Gate |','|---|---|---:|---:|---:|---:|---:|---|']
 for clock in CLOCKS:
  e=s[(s.symbol=='ETHUSDT')&(s.clock==clock)&(s.partition=='POOLED_MAJOR')].iloc[0]; b=s[(s.symbol=='BTCUSDT')&(s.clock==clock)&(s.partition=='POOLED_MAJOR')].iloc[0]
  lines.append(f'| {clock} | {e.side} | {int(e.k1_opp0)} | {int(e.causal_leave)} | {100*e.h2_rate:.1f}% | {100*e.resolved_h2_wr:.1f}% | {100*b.h2_rate:.1f}% | {"PASS" if gmap[clock] else "FAIL"} |')
 lines += ['',f'**Status: {status}**','', 'Per preregistration, execution stops here. M2 is not run automatically.']
 OUT_MD.write_text('\n'.join(lines)+'\n'); print(OUT_MD.read_text())
if __name__=='__main__':main()
