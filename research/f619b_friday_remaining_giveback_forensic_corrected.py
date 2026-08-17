#!/usr/bin/env python3
"""F6.19b corrected cohort accounting. Forensic only; no rule tuning."""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f618_friday_bearish_displacement_protection as f618
import f619_friday_remaining_giveback_forensic as h
OUT=Path(os.getenv('F619B_OUT','f619b_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL

def main():
 k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]; rows=[]; parents=[]
 for i,d0 in enumerate(days):
  t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t); parents.append(tr)
  ev=f616.existing_events(k,t,tr); ev.sort(key=lambda x:x[0]); untouched=len(ev)==0
  ps=f616.protection_state(k,tr); ds=f618.displacement_state(k,tr,ps); d3p,d3layer,_=f618.apply(k,t,tr,ps,ds,'D3_STRONG_BODY_BREAK_PRIOR_LOW')
  h05=f616.first_hit(k,tr,.5*R); h1=f616.first_hit(k,tr,1*R)
  row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'mfe_r':float(tr.mfe/R),'untouched':untouched,'d3_acted':d3layer=='D3_STRONG_BODY_BREAK_PRIOR_LOW','d3_pnl':float(d3p)}
  row['orig25']=bool(tr.pnl<=0 and untouched and .5<=tr.mfe/R<2); row['low']=bool(row['orig25'] and tr.mfe/R<1); row['high']=bool(row['orig25'] and tr.mfe/R>=1)
  if h05 is not None:
   sc=h.rolling(k,tr,h05)
   if sc:
    for kk,v in sc.items():row[f'scan05_{kk}']=v
   for mins in (20,35,65):
    s=h.snap(k,tr,h05,h05+pd.Timedelta(minutes=mins))
    if s:
     for kk,v in s.items():row[f'h05_{mins}_{kk}']=v
  if h1 is not None:
   sc=h.rolling(k,tr,h1)
   if sc:
    for kk,v in sc.items():row[f'scan1_{kk}']=v
  rows.append(row)
 f517.assert_parent(parents); df=pd.DataFrame(rows); df.to_csv(OUT/'f619b_rows.csv',index=False)
 g=df[df.orig25].copy()
 if not (len(g)==25 and int(g.low.sum())==12 and int(g.high.sum())==13):
  raise AssertionError(f"F6.14 parity n={len(g)} low={g.low.sum()} high={g.high.sum()}")
 d3_saved_exact=int(g.d3_acted.sum()); low=g[g.low].copy(); highrem=g[(g.high)&(~g.d3_acted)].copy(); remaining=int(len(g)-d3_saved_exact)
 ctl05=df[(df.parent_win)&(df.untouched)&(df.mfe_r>=.5)].copy(); ctl1=df[(df.parent_win)&(df.untouched)&(df.mfe_r>=1)&(~df.d3_acted)].copy()
 feats=['progress_r','drawdown_best_r','retained_fraction','last_vs_prev_r','taker4_med','taker_last','body_ratio','upper_wick_ratio','below_ema7','below_ema20','ema7_above_ema20','strong_break']; at=[]
 for mins in (20,35,65):
  for f in feats:
   c=f'h05_{mins}_{f}'
   if c not in df:continue
   a=low[['period',c]].dropna(); b=ctl05[['period',c]].dropna(); z=pd.concat([a.assign(y=1),b.assign(y=0)])
   zd=z[z.period=='discovery']; zv=z[z.period=='validation']
   at.append({'horizon':mins,'feature':f,'n_loss':len(a),'n_ctrl':len(b),'auc':h.auc(z.y,z[c]),'auc_D':h.auc(zd.y,zd[c]),'auc_V':h.auc(zv.y,zv[c]),'med_loss':float(a[c].median()) if len(a) else np.nan,'med_ctrl':float(b[c].median()) if len(b) else np.nan})
 atlas=pd.DataFrame(at); atlas['strength']=np.maximum(atlas.auc,1-atlas.auc); atlas=atlas.sort_values('strength',ascending=False); atlas.to_csv(OUT/'f619b_low_atlas.csv',index=False)
 reasons={'no_p1_alert':0,'p1_not_strong':0,'strong_no_break':0,'other':0}; details=[]
 for _,r in highrem.iterrows():
  i=int(r.i); t=pd.Timestamp(days[i].date(),tz='UTC')+pd.Timedelta(hours=8); tr=parents[i]; ps=f616.protection_state(k,tr); ds=f618.displacement_state(k,tr,ps)
  if ps is None or not ps['P1_FLOW_EMA15']:reason='no_p1_alert'
  elif ds is None or not ds['strong_body']:reason='p1_not_strong'
  elif not ds['break_prior_low']:reason='strong_no_break'
  else:reason='other'
  reasons[reason]+=1; details.append({'date':r.date,'period':r.period,'reason':reason,'later':bool(pd.notna(r.get('scan1_minutes',np.nan))),'later_minutes':None if pd.isna(r.get('scan1_minutes',np.nan)) else float(r.get('scan1_minutes')),'later_cut_pnl':None if pd.isna(r.get('scan1_cut_pnl',np.nan)) else float(r.get('scan1_cut_pnl'))})
 out={'parity':{'original':25,'low':12,'high':13,'d3_saved_exact_from_original25':d3_saved_exact,'remaining_exact':remaining,'high_remaining':int(len(highrem))},'low_scan':h.scanstats(low,'scan05'),'low_ctrl_scan':h.scanstats(ctl05,'scan05'),'high_scan':h.scanstats(highrem,'scan1'),'high_ctrl_scan':h.scanstats(ctl1,'scan1'),'high_miss_reasons':reasons,'high_details':details,'low_top':atlas.head(12).to_dict('records')}
 (OUT/'f619b_summary.json').write_text(json.dumps(out,indent=2,default=str))
 md=['# Friday F6.19b — Remaining Giveback Forensic (Corrected Overlap)','','**FORENSIC ONLY. Live BBC untouched. No threshold/rule tuning.**','',f"Exact F6.14 cohort: 25 = 12 low + 13 high. D3 overlap with this exact cohort: **{d3_saved_exact}**, so exact remaining = **{remaining}** (12 low + {len(highrem)} high).",'',f"Low later D3-like: {out['low_scan']['ever']}/{out['low_scan']['n']} vs controls {out['low_ctrl_scan']['ever']}/{out['low_ctrl_scan']['n']}.",f"High misses later D3-like: {out['high_scan']['ever']}/{out['high_scan']['n']} vs controls {out['high_ctrl_scan']['ever']}/{out['high_ctrl_scan']['n']}.",'','High miss reasons: '+json.dumps(reasons),'','Top low-cohort separators:']
 for r in out['low_top']:md.append(f"- {r['horizon']}m {r['feature']}: AUC {r['auc']:.3f}, D {r['auc_D']:.3f}, V {r['auc_V']:.3f}, loss {r['med_loss']:.4f}, ctrl {r['med_ctrl']:.4f}")
 md+=['','Guardrail: rolling later-state scans are diagnostic only, not trading rules.']
 (OUT/'F6.19B_CHECKPOINT.md').write_text('\n'.join(md)+'\n'); print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
