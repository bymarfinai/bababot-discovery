#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import eth_london_ny_liquidity_pressure_m1 as base
import sol_orb_24h_causal_retest_sweep_v1 as sweep

ROOT=Path(__file__).resolve().parent.parent
PFX='SOL_ORB_CAUSAL_RETEST_CHARACTER_V1'
BAR=pd.Timedelta(minutes=5); COST=.15; NOTIONAL=500.; H=(15,30,60,120)
FEATURES=['orb_range_pct','breakout_extension_r','breakout_body_r','bars_orb_to_break','bars_break_to_retest','retest_low_depth_r','retest_close_r','retest_body_r','retest_upper_wick_r','retest_lower_wick_r','retest_close_location']

def collect(x5):
 q=x5[(x5.index>=base.PARTS['development'][0])&(x5.index<base.PARTS['development'][1])]
 rows=[]
 for day in pd.Index(q.index.normalize().unique()).sort_values():
  if day.weekday()>=5: continue
  for hour in range(24):
   st=day+pd.Timedelta(hours=hour); orb=[sweep.row_at(x5,st+i*BAR) for i in range(3)]
   if any(r is None for r in orb): continue
   oh=max(float(r.high) for r in orb); ol=min(float(r.low) for r in orb); rng=oh-ol
   if rng<=0: continue
   br=None; bri=None
   for i in range(3,12):
    r=sweep.row_at(x5,st+i*BAR)
    if r is not None and float(r.close)>oh: br=r; bri=i; break
   if br is None: continue
   rt=None; rti=None
   for j in range(1,7):
    r=sweep.row_at(x5,st+(bri+j)*BAR)
    if r is not None and float(r.low)<=oh and float(r.close)>=(oh+ol)/2: rt=r; rti=bri+j; break
   if rt is None: continue
   dec=st+(rti+1)*BAR; ent=sweep.row_at(x5,dec)
   if ent is None: continue
   hi=float(rt.high); lo=float(rt.low); op=float(rt.open); cl=float(rt.close); span=max(hi-lo,1e-12)
   d={'session_start':st,'hour_utc':hour,'hour_wib':(hour+7)%24,'year':st.year,'entry_time':dec,'entry_price':float(ent.open),
      'orb_range_pct':rng/float(orb[0].open)*100,'breakout_extension_r':(float(br.close)-oh)/rng,'breakout_body_r':abs(float(br.close)-float(br.open))/rng,
      'bars_orb_to_break':bri-2,'bars_break_to_retest':rti-bri,'retest_low_depth_r':(oh-lo)/rng,'retest_close_r':(cl-oh)/rng,
      'retest_body_r':abs(cl-op)/rng,'retest_upper_wick_r':(hi-max(op,cl))/rng,'retest_lower_wick_r':(min(op,cl)-lo)/rng,
      'retest_close_location':(cl-lo)/span,'retest_bullish':cl>op}
   # acceptance diagnostic after retest, never used to select entry
   d['later_acceptance']=False
   for k in range(rti+1,bri+7):
    r=sweep.row_at(x5,st+k*BAR)
    if r is not None and float(r.close)>oh: d['later_acceptance']=True; break
   for m in H:
    xp=sweep.close_after(x5,dec,m)
    net=(xp/d['entry_price']-1)*100-COST if np.isfinite(xp) else np.nan
    d[f'net_{m}m_pct']=net; d[f'pnl_{m}m']=net/100*NOTIONAL if np.isfinite(net) else np.nan
   rows.append(d)
 return pd.DataFrame(rows)

def quartiles(ev):
 out=[]
 for f in FEATURES:
  z=ev.dropna(subset=[f]).copy()
  try: z['bucket']=pd.qcut(z[f],4,labels=['Q1','Q2','Q3','Q4'],duplicates='drop')
  except ValueError: continue
  for (yr,b),g in z.groupby(['year','bucket'],observed=True):
   for m in (30,60,120):
    a=g[f'pnl_{m}m'].dropna(); out.append({'feature':f,'year':yr,'bucket':str(b),'exit_minutes':m,'n':len(a),'net_wr':(a>0).mean(),'exp_usd':a.mean(),'net_pnl_usd':a.sum()})
  for b,g in z.groupby('bucket',observed=True):
   for m in (30,60,120):
    a=g[f'pnl_{m}m'].dropna(); out.append({'feature':f,'year':'ALL','bucket':str(b),'exit_minutes':m,'n':len(a),'net_wr':(a>0).mean(),'exp_usd':a.mean(),'net_pnl_usd':a.sum()})
 return pd.DataFrame(out)

def outcome_summary(ev):
 out=[]
 for f in FEATURES:
  for m in (30,60,120):
   z=ev.dropna(subset=[f,f'pnl_{m}m']); p=z[z[f'pnl_{m}m']>0][f]; n=z[z[f'pnl_{m}m']<=0][f]
   out.append({'feature':f,'exit_minutes':m,'median_all':z[f].median(),'median_positive':p.median(),'median_nonpositive':n.median(),'delta':p.median()-n.median()})
 return pd.DataFrame(out)

def main():
 x5,cov=base.load5('SOLUSDT'); assert cov>=.995
 ev=collect(x5); q=quartiles(ev); o=outcome_summary(ev)
 ev.to_csv(ROOT/f'{PFX}_Events.csv',index=False); q.to_csv(ROOT/f'{PFX}_Quartiles.csv',index=False); o.to_csv(ROOT/f'{PFX}_OutcomeSummary.csv',index=False)
 lines=['# SOL ORB Causal Retest Character v1 — Development','',f'- Coverage: {cov*100:.6f}%','- Decision: retest candle close; executable entry = next 5m open.','- No future acceptance selection; Reference/OOS closed.','',f'- Causal retest-close entries: **{len(ev)}**',f'- Later acceptance diagnostic: **{ev.later_acceptance.mean()*100:.2f}%**','', '## Pooled feature quartiles']
 for f in FEATURES:
  lines+=['',f'### {f}','', '| Exit | Bucket | N | Net WR | Exp | Net PnL |','|---:|---|---:|---:|---:|---:|']
  z=q[(q.feature==f)&(q.year=='ALL')]
  for _,r in z.iterrows(): lines.append(f"| {int(r.exit_minutes)}m | {r.bucket} | {int(r.n)} | {r.net_wr*100:.1f}% | ${r.exp_usd:.3f} | ${r.net_pnl_usd:.2f} |")
 lines+=['','## Boundary','','Characterization only. No threshold is promoted by this run. Candidate zones must survive a separately preregistered confirmation test.']
 (ROOT/f'{PFX}_Result.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); (ROOT/f'{PFX}_Status.txt').write_text('COMPLETE_DEVELOPMENT_CHARACTERIZATION_ONLY\n')
 print('\n'.join(lines))
if __name__=='__main__': main()
