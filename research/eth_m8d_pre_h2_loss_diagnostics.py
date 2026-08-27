#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
spec=importlib.util.spec_from_file_location('m8c',HERE/'eth_m8c_exit_mechanism.py'); c=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(c)
b=c.b; LOCKED=c.LOCKED; STOPS=c.STOPS
PFX='ETH_M8D_PRE_H2_LOSS_DIAGNOSTICS'; DETAIL=ROOT/f'{PFX}_Detail.csv'; SUMMARY=ROOT/f'{PFX}_Summary.csv'; RESULT=ROOT/f'{PFX}_Result.md'; STATUS=ROOT/f'{PFX}_Status.txt'

def scan(x,r,mode,dist,sf):
 entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end); h2=pd.Timestamp(r.h2_ts) if pd.notna(r.h2_ts) else pd.NaT
 H,L,R,entry=map(float,(r.H,r.L,r.R,r.entry_px)); boundary=L+float(sf)*R; gap=H-entry
 q=x.iloc[int(x.index.searchsorted(entry_ts)):int(x.index.searchsorted(end))]; assert len(q)>0 and q.index[0]==entry_ts
 minlow=entry; maxhigh=entry; exit_ts=pd.NaT; exit_px=np.nan; reason=''; reached_975=False; reached_99=False
 for ts,bar in q.iterrows():
  hi,lo,cl=float(bar.high),float(bar.low),float(bar.close); minlow=min(minlow,lo); maxhigh=max(maxhigh,hi)
  reached_975 |= hi >= L+.975*R; reached_99 |= hi >= L+.99*R
  is_h2=pd.notna(h2) and ts==h2; after=pd.notna(h2) and ts>h2
  if mode=='HARD_TOUCH' and not after and lo<=boundary:
   exit_ts=ts; exit_px=boundary; reason='PRE_H2_HARD_STOP'; break
  if mode=='CLOSE_NEXT_OPEN' and not after and not is_h2 and cl<boundary:
   nxt=ts+b.BAR5
   if nxt<=end:
    op=c.next_open(x,nxt)
    if op is not None and op[0]==nxt: exit_ts=op[0]; exit_px=op[1]; reason='PRE_H2_CLOSE_INVALIDATION'; break
  if is_h2: exit_ts=ts; exit_px=H; reason='H2'; break
 if not reason:
  op=c.next_open(x,end); assert op is not None; exit_ts,exit_px=op; reason='NO_H2_TIME_EXIT'
 mae=max(0.,(entry-minlow)/R); mfe=max(0.,(maxhigh-entry)/R); recovery=max(0.,min(1.,(maxhigh-entry)/gap)) if gap>0 else np.nan
 net=c.leg_pnl(exit_px,entry,b.NOTIONAL,b.FEE) if reason!='H2' else c.leg_pnl(H,entry,b.NOTIONAL,b.FEE)
 return {'mode':mode,'stop_distance':dist,'stop_fraction':sf,'diag_outcome':reason,'diag_h2':reason=='H2','mae_r':mae,'mfe_r':mfe,'recovery_to_h':recovery,'reached_f975':reached_975,'reached_f99':reached_99,'duration_min':float((pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1)),'diag_exit_px':exit_px,'diag_net_pnl_usd':net}

def qs(g,col):
 s=pd.to_numeric(g[col],errors='coerce').dropna(); return {f'{col}_median':float(s.median()) if len(s) else np.nan,f'{col}_p75':float(s.quantile(.75)) if len(s) else np.nan,f'{col}_p90':float(s.quantile(.90)) if len(s) else np.nan}

def main():
 x,cov=b.m.load5(); assert cov>=.995; E=b.build_entries(x); rows=[]
 for r0 in E.to_dict('records'):
  for mode,(dist,sf) in STOPS[r0['clock']].items(): rows.append({**r0,**scan(x,pd.Series(r0),mode,dist,sf)})
 T=pd.DataFrame(rows); T.to_csv(DETAIL,index=False); out=[]
 for clock in LOCKED:
  for mode in STOPS[clock]:
   for part in (*b.PARTS,'POOLED_MAJOR'):
    z=T[(T.clock==clock)&(T['mode']==mode)]; z=z[z.partition.isin(b.MAJOR)] if part=='POOLED_MAJOR' else z[z.partition==part]
    for grp,mask in [('ALL',pd.Series(True,index=z.index)),('H2',z.diag_h2),('FAIL',~z.diag_h2)]:
     g=z[mask]; losses=-pd.to_numeric(g.loc[g.diag_net_pnl_usd<0,'diag_net_pnl_usd'],errors='coerce').dropna().sort_values(ascending=False); total=float(losses.sum())
     n10=max(1,int(np.ceil(len(losses)*.10))) if len(losses) else 0; n20=max(1,int(np.ceil(len(losses)*.20))) if len(losses) else 0
     d={'clock':clock,'mode':mode,'partition':part,'group':grp,'n':len(g),'rate_of_all':len(g)/len(z) if len(z) else np.nan,'mean_net':float(g.diag_net_pnl_usd.mean()) if len(g) else np.nan,'gross_loss':total,'worst10_loss_share':float(losses.head(n10).sum()/total) if total>0 else np.nan,'worst20_loss_share':float(losses.head(n20).sum()/total) if total>0 else np.nan,'f975_rate':float(g.reached_f975.mean()) if len(g) else np.nan,'f99_rate':float(g.reached_f99.mean()) if len(g) else np.nan}; d.update(qs(g,'mae_r')); d.update(qs(g,'mfe_r')); d.update(qs(g,'recovery_to_h')); d.update(qs(g,'duration_min')); out.append(d)
 S=pd.DataFrame(out); S.to_csv(SUMMARY,index=False)
 lines=['# ETH M8D — Pre-H2 Loss Diagnostics','','Coverage: **%.4f%%**'%(cov*100),'','No rule optimization; descriptive diagnosis only.','','| Habitat | Protection | H2 rate | Failure MAE med/P90 | Failure recovery med | Failure F97.5 / F99 reach | Worst 20% share of failure losses |','|---|---|---:|---|---:|---|---:|']
 for clock in LOCKED:
  for mode in STOPS[clock]:
   allr=S[(S.clock==clock)&(S['mode']==mode)&(S.partition=='POOLED_MAJOR')&(S.group=='ALL')].iloc[0]; f=S[(S.clock==clock)&(S['mode']==mode)&(S.partition=='POOLED_MAJOR')&(S.group=='FAIL')].iloc[0]
   lines.append(f"| {clock} | {mode} | {1-f.rate_of_all:.1%} | {f.mae_r_median:.3f} / {f.mae_r_p90:.3f}R | {f.recovery_to_h_median:.1%} | {f.f975_rate:.1%} / {f.f99_rate:.1%} | {f.worst20_loss_share:.1%} |")
 lines += ['','Interpretation guardrail: landmarks are diagnostic only. Any candidate filter/invalidation requires a new preregistered milestone.','','**Status: ETH_M8D_PRE_H2_LOSS_DIAGNOSTICS_COMPLETED**']; RESULT.write_text('\n'.join(lines)+'\n'); STATUS.write_text('ETH_M8D_PRE_H2_LOSS_DIAGNOSTICS_COMPLETED\n'); print(RESULT.read_text())
if __name__=='__main__': main()
