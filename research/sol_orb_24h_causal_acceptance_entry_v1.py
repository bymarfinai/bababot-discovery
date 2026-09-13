#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import eth_london_ny_liquidity_pressure_m1 as base
import sol_orb_24h_causal_retest_sweep_v1 as sweep

ROOT=Path(__file__).resolve().parent.parent
PFX='SOL_ORB_24H_CAUSAL_ACCEPTANCE_ENTRY_V1'
BAR=pd.Timedelta(minutes=5); HORIZONS=(15,30,60,120); COST=.15; NOTIONAL=500.

def pf(pnls):
 a=pd.Series(pnls,dtype=float).dropna(); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
 return math.inf if neg<=0 and pos>0 else (np.nan if neg<=0 else pos/neg)

def mls(pnls):
 best=cur=0
 for x in pd.Series(pnls,dtype=float).dropna():
  if x<0: cur+=1; best=max(best,cur)
  else: cur=0
 return best

def mdd(pnls):
 a=pd.Series(pnls,dtype=float).fillna(0); eq=a.cumsum(); peak=eq.cummax().clip(lower=0); return float((peak-eq).max()) if len(a) else np.nan

def detect(x5,start):
 orb=[sweep.row_at(x5,start+i*BAR) for i in range(3)]
 if any(r is None for r in orb): return None
 oh=max(float(r.high) for r in orb); ol=min(float(r.low) for r in orb); om=(oh+ol)/2
 brt=None
 for i in range(3,12):
  ts=start+i*BAR; r=sweep.row_at(x5,ts)
  if r is not None and float(r.close)>oh: brt=ts; break
 if brt is None: return {'session_start':start,'hour_utc':start.hour,'hour_wib':(start.hour+7)%24,'year':start.year,'has_signal':False}
 post=[]
 for j in range(1,7):
  ts=brt+j*BAR; r=sweep.row_at(x5,ts)
  if r is not None: post.append((ts,r))
 rt=None
 for ts,r in post:
  if float(r.low)<=oh and float(r.close)>=om: rt=ts; break
 if rt is None: return {'session_start':start,'hour_utc':start.hour,'hour_wib':(start.hour+7)%24,'year':start.year,'has_signal':False}
 at=None; ar=None
 for ts,r in post:
  if ts>rt and float(r.close)>oh: at=ts; ar=r; break
 if at is None: return {'session_start':start,'hour_utc':start.hour,'hour_wib':(start.hour+7)%24,'year':start.year,'has_signal':False}
 et=at+BAR; er=sweep.row_at(x5,et)
 if er is None: return {'session_start':start,'hour_utc':start.hour,'hour_wib':(start.hour+7)%24,'year':start.year,'has_signal':False}
 ep=float(er.open); d={'session_start':start,'hour_utc':start.hour,'hour_wib':(start.hour+7)%24,'year':start.year,'has_signal':True,'breakout_time':brt,'retest_time':rt,'acceptance_time':at,'entry_time':et,'entry_price':ep}
 for m in HORIZONS:
  xp=sweep.close_after(x5,et,m)
  if np.isfinite(xp):
   gross=(xp/ep-1)*100; net=gross-COST; d[f'net_{m}m_pct']=net; d[f'pnl_{m}m']=net/100*NOTIONAL
  else: d[f'net_{m}m_pct']=np.nan; d[f'pnl_{m}m']=np.nan
 return d

def collect(x5):
 q=x5[(x5.index>=base.PARTS['development'][0])&(x5.index<base.PARTS['development'][1])]
 days=pd.Index(q.index.normalize().unique()).sort_values(); rows=[]
 for day in days:
  if day.weekday()>=5: continue
  for h in range(24):
   d=detect(x5,day+pd.Timedelta(hours=h))
   if d is not None: rows.append(d)
 return pd.DataFrame(rows)

def econ(ev):
 rows=[]; z=ev[ev.has_signal].copy()
 for hour,g in z.groupby('hour_utc'):
  for m in HORIZONS:
   gg=g.dropna(subset=[f'pnl_{m}m']).sort_values('entry_time'); p=gg[f'pnl_{m}m'].astype(float)
   rows.append({'hour_utc':hour,'hour_wib':(hour+7)%24,'exit_minutes':m,'n':len(gg),'net_wr':(gg[f'net_{m}m_pct']>0).mean(),'net_pnl_usd':p.sum(),'expectancy_usd':p.mean(),'profit_factor':pf(p),'max_dd_usd':mdd(p),'max_loss_streak':mls(p)})
 return pd.DataFrame(rows)

def yearly(ev):
 rows=[]; z=ev[ev.has_signal].copy()
 for (hour,year),g in z.groupby(['hour_utc','year']):
  for m in HORIZONS:
   gg=g.dropna(subset=[f'pnl_{m}m']); p=gg[f'pnl_{m}m'].astype(float)
   rows.append({'hour_utc':hour,'hour_wib':(hour+7)%24,'year':year,'exit_minutes':m,'n':len(gg),'net_wr':(gg[f'net_{m}m_pct']>0).mean(),'net_pnl_usd':p.sum(),'expectancy_usd':p.mean(),'profit_factor':pf(p)})
 return pd.DataFrame(rows)

def main():
 x5,cov=base.load5('SOLUSDT'); assert cov>=.995
 ev=collect(x5); ec=econ(ev); yr=yearly(ev)
 ev.to_csv(ROOT/f'{PFX}_Events.csv',index=False); ec.to_csv(ROOT/f'{PFX}_EconomicsByHour.csv',index=False); yr.to_csv(ROOT/f'{PFX}_YearStability.csv',index=False)
 sig=int(ev.has_signal.sum()); lines=['# SOL ORB 24H Causal Acceptance Entry v1 — Development','',f'- Coverage: {cov*100:.6f}%','- Rule: ORB -> breakout -> retest -> later acceptance -> next 5m open.','- $500/trade; 0.15% round-trip cost; fixed exits only; OOS closed.','',f'- Total causal acceptance signals: **{sig}**','', '## Economics by hour','', '| UTC | WIB | Exit | N | Net WR | Net PnL | Exp | PF | Max DD | Max LS |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for _,r in ec.sort_values(['hour_utc','exit_minutes']).iterrows(): lines.append(f"| {int(r.hour_utc):02d}:00 | {int(r.hour_wib):02d}:00 | {int(r.exit_minutes)}m | {int(r.n)} | {r.net_wr*100:.1f}% | ${r.net_pnl_usd:.2f} | ${r.expectancy_usd:.3f} | {r.profit_factor:.3f} | ${r.max_dd_usd:.2f} | {int(r.max_loss_streak)} |")
 stable=[]
 for _,r in ec.iterrows():
  y=yr[(yr.hour_utc==r.hour_utc)&(yr.exit_minutes==r.exit_minutes)]
  if len(y)==3 and bool(((y.net_pnl_usd>0)&(y.profit_factor>1)).all()): stable.append(r)
 lines+=['','## Three-year stability','']
 if stable:
  lines.append('| UTC | WIB | Exit | N | Exp | PF |'); lines.append('|---:|---:|---:|---:|---:|---:|')
  for r in stable: lines.append(f"| {int(r.hour_utc):02d}:00 | {int(r.hour_wib):02d}:00 | {int(r.exit_minutes)}m | {int(r.n)} | ${r.expectancy_usd:.3f} | {r.profit_factor:.3f} |")
 else: lines.append('No hour/exit combination is positive with PF>1 in all three Development years.')
 lines+=['','## Boundary','','Development map only. Any surviving hour/exit requires separately preregistered confirmation before Reference/OOS.']
 (ROOT/f'{PFX}_Result.md').write_text('\n'.join(lines)+'\n'); (ROOT/f'{PFX}_Status.txt').write_text('COMPLETE_DEVELOPMENT_24H_ACCEPTANCE_MAP\n'); print('\n'.join(lines))
if __name__=='__main__': main()
