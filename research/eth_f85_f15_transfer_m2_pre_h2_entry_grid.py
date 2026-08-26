#!/usr/bin/env python3
from __future__ import annotations
import io, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX='ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_WIN=ROOT/f'{PFX}_Windows.csv'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
BASE='https://data.binance.vision/data/futures/um'
START=pd.Timestamp('2020-01-01',tz='UTC'); END=pd.Timestamp('2026-08-26',tz='UTC'); BAR5=pd.Timedelta(minutes=5); REF=pd.Timedelta(hours=5,minutes=30); EXE=pd.Timedelta(hours=6,minutes=30)
PARTS={'external':(pd.Timestamp('2020-01-01',tz='UTC'),pd.Timestamp('2022-01-01',tz='UTC')),'development':(pd.Timestamp('2022-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')),'reference_validation':(pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2026-07-30',tz='UTC')),'august':(pd.Timestamp('2026-08-01',tz='UTC'),END)}
MAJOR=('external','development','reference_validation')
CLOCKS={'ALT_0330':210,'RAW_0530':330,'LONDON':480,'RAW_2330':1410,'SHORT_2000':1200}
SIDE={k:('SHORT' if k=='SHORT_2000' else 'LONG') for k in CLOCKS}
LONG_LEVELS={'F95':.95,'F90':.90,'F85':.85,'F80':.80,'F75':.75}; SHORT_LEVELS={'F05':.05,'F10':.10,'F15':.15,'F20':.20,'F25':.25}

def urls():
 out=[]; m=pd.Timestamp(START.year,START.month,1,tz='UTC'); em=pd.Timestamp(END.year,END.month,1,tz='UTC')
 while m<em:
  ym=m.strftime('%Y-%m'); out.append(f'{BASE}/monthly/klines/ETHUSDT/5m/ETHUSDT-5m-{ym}.zip'); m+=pd.offsets.MonthBegin(1)
 d=em
 while d<END.normalize():
  ds=d.strftime('%Y-%m-%d'); out.append(f'{BASE}/daily/klines/ETHUSDT/5m/ETHUSDT-5m-{ds}.zip'); d+=pd.Timedelta(days=1)
 return out

def fetch(u):
 r=requests.get(u,timeout=90,headers={'User-Agent':'bababot-eth-m2/1.0'})
 if r.status_code==404:return None
 r.raise_for_status()
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  n=[x for x in z.namelist() if x.lower().endswith('.csv')]
  if not n:return None
  with z.open(n[0]) as f:return pd.read_csv(f,header=None,usecols=[0,1,2,3,4],names=['ts','open','high','low','close'])

def load5():
 fs=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  fut=[ex.submit(fetch,u) for u in urls()]
  for f in as_completed(fut):
   z=f.result()
   if z is not None and len(z):fs.append(z)
 x=pd.concat(fs,ignore_index=True); t=pd.to_numeric(x.ts,errors='coerce'); t=np.where(t>100_000_000_000_000,t/1000.0,t); x['ts']=pd.to_datetime(t,unit='ms',utc=True,errors='coerce')
 for c in ['open','high','low','close']:x[c]=pd.to_numeric(x[c],errors='coerce')
 x=x.dropna().drop_duplicates('ts').sort_values('ts'); x=x[(x.ts>=START)&(x.ts<END)].set_index('ts'); expected=int((x.index[-1]-x.index[0])/BAR5)+1; cov=len(x)/expected
 if cov<.995:raise RuntimeError(f'coverage {cov:.6f}')
 return x,cov

def sl(x,a,z):i=int(x.index.searchsorted(a));j=int(x.index.searchsorted(z));return x.iloc[i:j]
def part(ts):
 for n,(a,z) in PARTS.items():
  if a<=ts<z:return n
 return None

def find_window(exe,H,L,side):
 hi_touch=lo_touch=False; hi_vis=lo_vis=0; state='SEEK'; k1=pd.NaT; leave_bar=pd.NaT; eligible_start=pd.NaT
 for ts,r in exe.iterrows():
  hi,lo,cl=float(r.high),float(r.low),float(r.close)
  if state=='SEEK':
   if cl>H or cl<L:return None
   hh=hi>=H and cl<=H; ll=lo<=L and cl>=L
   if hh and ll:return None
   if side=='LONG':
    if ll and not lo_touch:lo_vis+=1
    if hh and not hi_touch:
     hi_vis+=1
     if hi_vis==1 and lo_vis==0:k1=ts;state='EP'
    hi_touch,lo_touch=hh,ll
    if lo_vis>0 and state=='SEEK':return None
   else:
    if hh and not hi_touch:hi_vis+=1
    if ll and not lo_touch:
     lo_vis+=1
     if lo_vis==1 and hi_vis==0:k1=ts;state='EP'
    hi_touch,lo_touch=hh,ll
    if hi_vis>0 and state=='SEEK':return None
   continue
  if state=='EP':
   if cl>H or cl<L:return {'k1':k1,'clean':False,'leave_bar':pd.NaT,'eligible_start':pd.NaT,'terminal':'BREAK_DURING_K1','terminal_bar':ts}
   same=(hi>=H and cl<=H) if side=='LONG' else (lo<=L and cl>=L)
   if same:continue
   leave_bar=ts; eligible_start=ts+2*BAR5; state='POST'; continue
  if state=='POST':
   h2=(hi>=H) if side=='LONG' else (lo<=L); opp=(cl<L) if side=='LONG' else (cl>H)
   if h2 and opp:term='AMBIGUOUS'
   elif h2:term='H2'
   elif opp:term='OPPOSITE'
   else:continue
   return {'k1':k1,'clean':True,'leave_bar':leave_bar,'eligible_start':eligible_start,'terminal':term,'terminal_bar':ts}
 if state=='EP':return {'k1':k1,'clean':False,'leave_bar':pd.NaT,'eligible_start':pd.NaT,'terminal':'NO_LEAVE','terminal_bar':pd.NaT}
 if state=='POST':return {'k1':k1,'clean':True,'leave_bar':leave_bar,'eligible_start':eligible_start,'terminal':'NO_H2','terminal_bar':pd.NaT}
 return None

def candidate(exe,H,L,w,side,name,f):
 level=L+f*(H-L); terminal=w['terminal_bar']; elig=w['eligible_start']; q=exe[exe.index>=elig]
 if pd.notna(terminal):q=q[q.index<terminal]
 fill_ts=pd.NaT; minfrac=np.nan; maxfrac=np.nan
 for ts,r in q.iterrows():
  if float(r.low)<=level<=float(r.high):fill_ts=ts;break
 if pd.isna(fill_ts):return {'level':name,'fraction':f,'price':level,'filled':False,'fill_ts':pd.NaT,'outcome':w['terminal'],'minutes_to_h2':np.nan,'mae_ru':np.nan,'tail_frac':np.nan}
 post=exe[exe.index>=fill_ts]
 if pd.notna(terminal):post=post[post.index<=terminal]
 if side=='LONG':
  minfrac=(float(post.low.min())-L)/(H-L); mae=max(0.0,f-minfrac)
  tail=minfrac
 else:
  maxfrac=(float(post.high.max())-L)/(H-L); mae=max(0.0,maxfrac-f)
  tail=maxfrac
 mins=float((terminal-fill_ts)/pd.Timedelta(minutes=1)) if w['terminal']=='H2' and pd.notna(terminal) else np.nan
 return {'level':name,'fraction':f,'price':level,'filled':True,'fill_ts':fill_ts,'outcome':w['terminal'],'minutes_to_h2':mins,'mae_ru':mae,'tail_frac':tail}

def main():
 x,cov=load5(); wins=[]; cands=[]
 for d in pd.date_range(START.normalize(),END.normalize(),freq='D',tz='UTC'):
  for clock,cm in CLOCKS.items():
   rs=d+pd.Timedelta(minutes=cm); re=rs+REF; es=re; ee=es+EXE; p=part(es)
   if p is None or es.weekday()>=5 or ee>END:continue
   ref=sl(x,rs,re); exe=sl(x,es,ee)
   if len(ref)!=66 or len(exe)!=78:continue
   H=float(ref.high.max());L=float(ref.low.min());
   if not H>L:continue
   w=find_window(exe,H,L,SIDE[clock])
   if w is None:continue
   row={'clock':clock,'side':SIDE[clock],'partition':p,'reference_start':rs,'execution_start':es,'H':H,'L':L,**w}; wins.append(row)
   if not w['clean']:continue
   grid=LONG_LEVELS if SIDE[clock]=='LONG' else SHORT_LEVELS
   for name,f in grid.items():cands.append({'clock':clock,'side':SIDE[clock],'partition':p,'reference_start':rs,'execution_start':es,'H':H,'L':L,**candidate(exe,H,L,w,SIDE[clock],name,f)})
 W=pd.DataFrame(wins); C=pd.DataFrame(cands); W.to_csv(OUT_WIN,index=False); C.to_csv(OUT_CAND,index=False)
 rows=[]
 for clock in CLOCKS:
  grid=LONG_LEVELS if SIDE[clock]=='LONG' else SHORT_LEVELS
  for lvl in grid:
   for p in (*PARTS.keys(),'POOLED_MAJOR'):
    w=W[W.clock==clock]; c=C[(C.clock==clock)&(C.level==lvl)]
    if p=='POOLED_MAJOR':w=w[w.partition.isin(MAJOR)];c=c[c.partition.isin(MAJOR)]
    else:w=w[w.partition==p];c=c[c.partition==p]
    clean=w[w.clean.astype(bool)] if len(w) else w; f=c[c.filled.astype(bool)] if len(c) else c; h=int((f.outcome=='H2').sum()) if len(f) else 0;o=int((f.outcome=='OPPOSITE').sum()) if len(f) else 0;n=int((f.outcome=='NO_H2').sum()) if len(f) else 0
    rows.append({'clock':clock,'side':SIDE[clock],'level':lvl,'partition':p,'k1':len(w),'clean':len(clean),'clean_h2_rate':float((clean.terminal=='H2').mean()) if len(clean) else np.nan,'fills':len(f),'fill_rate':len(f)/len(clean) if len(clean) else np.nan,'h2':h,'opposite':o,'no_h2':n,'h2_hit_rate':h/len(f) if len(f) else np.nan,'resolved_h2_wr':h/(h+o) if h+o else np.nan,'median_min_to_h2':pd.to_numeric(f.loc[f.outcome=='H2','minutes_to_h2'],errors='coerce').median() if h else np.nan,'median_mae_ru':pd.to_numeric(f.mae_ru,errors='coerce').median() if len(f) else np.nan,'tail_fraction':pd.to_numeric(f.tail_frac,errors='coerce').quantile(.10 if SIDE[clock]=='LONG' else .90) if len(f) else np.nan})
 S=pd.DataFrame(rows); passes=[]
 for clock in CLOCKS:
  grid=LONG_LEVELS if SIDE[clock]=='LONG' else SHORT_LEVELS
  for lvl in grid:
   ok=True
   for p in MAJOR:
    r=S[(S.clock==clock)&(S.level==lvl)&(S.partition==p)].iloc[0];ok=ok and int(r.fills)>=30 and float(r.h2_hit_rate)>=.70
   if ok:passes.append((clock,lvl))
 S['screen']='';
 for clock,lvl in passes:S.loc[(S.clock==clock)&(S.level==lvl)&(S.partition=='POOLED_MAJOR'),'screen']='SCREEN_PASS'
 S.to_csv(OUT_SUM,index=False)
 status='ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED';OUT_STATUS.write_text(status+'\n')
 lines=['# ETH F85/F15 Transfer — M2 Pre-H2 Entry Grid — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','', 'Structural only: no confirmation, stop, target, PnL, PF, or expectancy.','', '| Habitat | Side | Passing levels | Pooled fills / H2 rate by passing level |','|---|---|---|---|']
 for clock in CLOCKS:
  pp=[lvl for c,lvl in passes if c==clock]
  desc=[]
  for lvl in pp:
   r=S[(S.clock==clock)&(S.level==lvl)&(S.partition=='POOLED_MAJOR')].iloc[0];desc.append(f'{lvl}: {int(r.fills)} / {100*r.h2_hit_rate:.1f}%')
  lines.append(f'| {clock} | {SIDE[clock]} | {", ".join(pp) if pp else "NONE"} | {"; ".join(desc) if desc else "-"} |')
 lines += ['',f'**Status: {status}**','', 'Stop after M2. No M3/economic testing was run automatically.']
 OUT_MD.write_text('\n'.join(lines)+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
