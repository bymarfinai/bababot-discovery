#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S7A_PATH=HERE/'eth_b27dx_s7a_event_quality_filter.py'
spec=importlib.util.spec_from_file_location('eth_s7a',S7A_PATH); s7a=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(s7a)
PFX='ETH_B27DX_S7E_BEARISH_LEAVE_BAR'; OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_SEL=ROOT/f'{PFX}_Selections.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_PORT=ROOT/f'{PFX}_PortfolioSummary.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCKS=s7a.CLOCKS; PARTS=s7a.PARTS

def cl(v):return s7a.cl(int(v))
def attach(c,x):
 q=c.copy(); vals=[]
 for r in q.itertuples(index=False):
  es=pd.Timestamp(r.execution_start); ee=es+pd.Timedelta(minutes=s7a.HORIZON_MIN); exe=s7a.fast_slice(x,es,ee); w=s7a.s4.b.m.corrected_find_window(exe,float(r.H),float(r.L),'LONG')
  if w is None or not bool(w.get('clean',False)): raise AssertionError('lost window')
  leave=pd.Timestamp(w['leave_bar']); entry=pd.Timestamp(r.entry_bar_start); bar=x.loc[leave]; vals.append({'partition':r.partition,'exec_min':int(r.exec_min),'execution_start':es,'entry_bar_start':entry,'leave_bar_start':leave,'leave_open':float(bar.open),'leave_close':float(bar.close),'bearish_leave_bar':float(bar.close)<float(bar.open),'known':leave+pd.Timedelta(minutes=5)<=entry})
 f=pd.DataFrame(vals); keys=['partition','exec_min','execution_start','entry_bar_start']; q=q.merge(f,on=keys,how='left',validate='one_to_one'); return q,f
def mask(g):return g.bearish_leave_bar.astype(bool)
def metrics_table(c):
 rows=[]
 for ex in CLOCKS:
  for p in PARTS:
   raw=c[(c.exec_min==ex)&(c.partition==p)].copy()
   for name,z in [('BASE',raw),('BEARISH_LEAVE_BAR',raw[mask(raw)].copy())]: rows.append({'exec_min':ex,'execution_utc':cl(ex),'filter':name,'partition':p,'raw_n':len(raw),'n':len(z),'retention':len(z)/len(raw) if len(raw) else np.nan,**s7a.s4.metrics(z,'pnl_0')})
 return pd.DataFrame(rows)
def select(s):
 rows=[]
 for ex in CLOCKS:
  d=s[(s.exec_min==ex)&(s.partition=='development')&(s['filter']=='BEARISH_LEAVE_BAR')].iloc[0]; prom=bool(d.n>=20 and d.retention>=.50 and d.wr>=.75 and d.pf>=1.50 and d.expectancy>=.80 and d.net>0); row={'exec_min':ex,'execution_utc':cl(ex),'dev_promoted':prom,'replicated':False,'dev_n':d.n,'dev_retention':d.retention,'dev_wr':d.wr,'dev_pf':d.pf,'dev_expectancy':d.expectancy,'dev_net':d.net}
  if prom:
   oks=[]
   for p in ('external','reference_validation'):
    z=s[(s.exec_min==ex)&(s.partition==p)&(s['filter']=='BEARISH_LEAVE_BAR')].iloc[0]; ok=bool(z.n>=10 and z.retention>=.40 and z.wr>=.70 and z.pf>=1.20 and z.expectancy>0 and z.net>0); oks.append(ok); row[f'{p}_pass']=ok
   row['replicated']=all(oks)
  rows.append(row)
 return pd.DataFrame(rows)
def lock(c,sel,col):
 clocks=set(int(v) for v in sel.loc[sel.replicated,'exec_min'])
 if not clocks:return pd.DataFrame(),pd.DataFrame()
 allc=c[c.exec_min.isin(clocks)&mask(c)].copy(); decs=[];rows=[];mw=sum(s7a.s4.weeks_for(p) for p in PARTS)
 for p in PARTS:
  d=s7a.s4.lock_partition(allc[allc.partition==p].copy());decs.append(d);a=d[d.accepted];rows.append({'partition':p,'accepted':len(a),'trades_per_week':len(a)/s7a.s4.weeks_for(p),**s7a.s4.metrics(a,col)})
 d=pd.concat(decs,ignore_index=True);a=d[d.accepted];rows.append({'partition':'POOLED_MAJOR','accepted':len(a),'trades_per_week':len(a)/mw,**s7a.s4.metrics(a,col)});return d,pd.DataFrame(rows)
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
 if pd.isna(v):return '-'
 return 'inf' if math.isinf(float(v)) else f'{float(v):.2f}'
def main():
 x,cov=s7a.s4.b.m.m.load5();base,a0=s7a.feature_candidates(x);c,a=attach(base,x);causal=bool(a.known.all() and a0.feature_known_by_entry.all());s=metrics_table(c);s.to_csv(OUT_SUM,index=False);sel=select(s);sel.to_csv(OUT_SEL,index=False);d0,p0=lock(c,sel,'pnl_0');d5,p5=lock(c,sel,'pnl_5');d0.to_csv(OUT_DEC,index=False)
 ports=pd.concat([p0.assign(stress_bps=0),p5.assign(stress_bps=5)],ignore_index=True) if len(p0) else pd.DataFrame();ports.to_csv(OUT_PORT,index=False);ndev=int(sel.dev_promoted.sum());nrep=int(sel.replicated.sum())
 if not causal:status='ETH_S7E_CAUSAL_AUDIT_FAILED'
 elif ndev==0:status='ETH_S7E_NO_DEV_BEARISH_LEAVE_FILTER'
 elif nrep==0:status='ETH_S7E_DEV_FILTERS_NOT_REPLICATED'
 else:
  z=p0[p0.partition=='POOLED_MAJOR'].iloc[0];zs=p5[p5.partition=='POOLED_MAJOR'].iloc[0];maj=p0[p0.partition.isin(PARTS)];btc=bool(z.wr>=s7a.BTC_WR and z.pf>=s7a.BTC_PF and z.expectancy>=s7a.BTC_EXP and ((maj.net>0)&(maj.pf>1)).all() and zs.net>=0 and zs.pf>=1);status='ETH_S7E_BEARISH_LEAVE_PORTFOLIO_BTC_QUALITY_SUPPORTED' if btc else 'ETH_S7E_BEARISH_LEAVE_FILTERS_REPLICATED_BELOW_BTC'
 lines=['# ETH B27DX — S7E Bearish Leave-Bar Quality — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Causal audit: **{"PASS" if causal else "FAIL"}**.','','| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |','|---:|---|---:|---:|---:|---:|---:|---:|---|']
 for ex in CLOCKS:
  for name in ('BASE','BEARISH_LEAVE_BAR'):
   r=s[(s.exec_min==ex)&(s.partition=='development')&(s['filter']==name)].iloc[0];prom=bool(name!='BASE' and r.n>=20 and r.retention>=.50 and r.wr>=.75 and r.pf>=1.50 and r.expectancy>=.80 and r.net>0);lines.append(f'| {r.execution_utc} | {name} | {int(r.n)} | {pct(r.retention)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.net)} | {"YES" if prom else "NO"} |')
 lines+=['','## Replication','']
 for r in sel.itertuples(index=False): lines.append(f'- {r.execution_utc}: Dev {"PASS" if r.dev_promoted else "FAIL"}; replicated **{"YES" if r.replicated else "NO"}**.')
 lines+=['','## Decision','',f'**Status: {status}**','', '- No numeric threshold, geometry, runner, leverage, fee, or live-code change was made.'];OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
