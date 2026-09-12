#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT=Path(__file__).resolve().parent.parent
PRIOR=ROOT/'ETH_R4B_STAGE_E_2026_YTD_CELLS.csv'
OUT_THRESH=ROOT/'ETH_R4B_STAGE_H_ENERGY_THRESHOLDS_2022.csv'
OUT_BUCKETS=ROOT/'ETH_R4B_STAGE_H_HISTORICAL_BUCKETS.csv'
OUT_SUPPORT=ROOT/'ETH_R4B_STAGE_H_HISTORICAL_SUPPORT.csv'
OUT_RESULT=ROOT/'ETH_R4B_STAGE_H_HISTORICAL_Result.md'
OUT_STATUS=ROOT/'ETH_R4B_STAGE_H_HISTORICAL_Status.txt'
EXPECTED={(120,240),(180,240),(240,240),(180,360),(240,360)}
HOUR=4
RULE='DRIVE_DOWN__STR_B80_100'
FEATURES=['rv_60','atr_pct_60']
PERIODS=[
 ('DEV_2022',pd.Timestamp('2022-01-01',tz='UTC'),pd.Timestamp('2023-01-01',tz='UTC')),
 ('TEST_2023',pd.Timestamp('2023-01-01',tz='UTC'),pd.Timestamp('2024-01-01',tz='UTC')),
 ('CONFIRM_2024',pd.Timestamp('2024-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')),
 ('FINAL_OOS_2025',pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2026-01-01',tz='UTC')),
 ('SHADOW_2026',pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2027-01-01',tz='UTC')),
]

def finite(x): return bool(np.isfinite(x))
def metric(st,k):
 x=float(st[k]); return x if finite(x) else np.nan

def stats(T): return r1.stats_from_df(T[['entry_ts','exit_ts','clock','gross','net']].copy())

def build_features(x):
 c=x['close'].astype(float); h=x['high'].astype(float); l=x['low'].astype(float); prev=c.shift(1)
 lr=np.log(c).diff(); tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)/prev
 F=pd.DataFrame(index=x.index)
 F['rv_60']=lr.shift(1).rolling(12,min_periods=12).std(ddof=0)*np.sqrt(12)
 F['atr_pct_60']=tr.shift(1).rolling(12,min_periods=12).mean()
 return F

def all_events(cache,lb,hold,last_ts,F):
 rows=[]
 for clock in e12.CLOCKS:
  S,ent,pre,ex,valid,xp,delta,masks=cache[(clock,lb,hold)]
  ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
  m=valid & (ent>=pd.Timestamp('2022-01-01',tz='UTC')) & (ex<=last_ts) & masks[RULE]
  gross=e12.NOTIONAL*np.asarray(delta,float)[m]; net=gross-e12.FEE
  for entry_ts,exit_ts,g,n in zip(ent[m],ex[m],gross,net):
   row={'entry_ts':entry_ts,'exit_ts':exit_ts,'clock':int(clock),'gross':float(g),'net':float(n)}
   for f in FEATURES:
    v=F.at[entry_ts,f] if entry_ts in F.index else np.nan
    row[f]=float(v) if finite(v) else np.nan
   rows.append(row)
 return pd.DataFrame(rows,columns=['entry_ts','exit_ts','clock','gross','net']+FEATURES)

def label_bucket(v,q33,q67):
 if not finite(v): return 'NA'
 if v<=q33: return 'LOW'
 if v>=q67: return 'HIGH'
 return 'MID'

def safe_pf(st):
 x=float(st['pf'])
 return x

def summarize(T,period,lb,hold,dimension,bucket):
 st=stats(T)
 return {'period':period,'lookback_min':lb,'hold_min':hold,'dimension':dimension,'bucket':bucket,
         'n':int(st['trades']),'wr':metric(st,'win_rate'),'net':float(st['net_pnl']),
         'exp':metric(st,'expectancy'),'pf':safe_pf(st),'dd':metric(st,'max_dd')}

def fmt_pct(x): return 'NA' if not finite(x) else f'{100*x:.2f}%'
def fmt_money(x): return 'NA' if not finite(x) else f'${x:+.2f}'
def fmt_num(x,d=3):
 if pd.isna(x): return 'NA'
 if np.isposinf(x): return 'inf'
 if np.isneginf(x): return '-inf'
 return f'{float(x):.{d}f}'

def main():
 prior=pd.read_csv(PRIOR)
 if len(prior)!=5: raise AssertionError('frozen plateau must contain 5 cells')
 if set(prior.hour_wib.astype(int))!={HOUR}: raise AssertionError('frozen hour changed')
 if set(prior.character_rule.astype(str))!={RULE}: raise AssertionError('frozen rule changed')
 actual=set(zip(prior.lookback_min.astype(int),prior.hold_min.astype(int)))
 if actual!=EXPECTED: raise AssertionError(f'frozen cells changed: {sorted(actual)}')
 cutoffs=pd.to_datetime(prior.dataset_last_ts_utc,utc=True).unique()
 if len(cutoffs)!=1: raise AssertionError('non-unique Stage-E cutoff')
 last_ts=pd.Timestamp(cutoffs[0])

 e12.base.synthetic_tests(); x5,coverage=e12.base.load5('ETHUSDT')
 if coverage<.995: raise RuntimeError(f'coverage too low: {coverage}')
 idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
 if idx.min()>pd.Timestamp('2022-01-01',tz='UTC') or idx.max()<last_ts: raise RuntimeError('historical coverage insufficient')
 x=x5[(idx>=pd.Timestamp('2021-12-01',tz='UTC'))&(idx<=last_ts)].copy(); F=build_features(x)
 e12.CLOCKS=r1.clocks_for_hour(HOUR)
 e12.LOOKBACKS=sorted(prior.lookback_min.astype(int).unique().tolist()); e12.HOLDS=sorted(prior.hold_min.astype(int).unique().tolist())
 cache=e12.prep(x)
 event_map={}
 for lb,hold in EXPECTED: event_map[(lb,hold)]=all_events(cache,lb,hold,last_ts,F)

 # Thresholds are distribution-only, derived from unique 2022 entry timestamps across the frozen plateau.
 dev_entries=[]
 for T in event_map.values(): dev_entries.extend(T.loc[(T.entry_ts>=PERIODS[0][1])&(T.entry_ts<PERIODS[0][2]),'entry_ts'].tolist())
 unique_dev=pd.DatetimeIndex(sorted(set(dev_entries)))
 U=F.reindex(unique_dev)[FEATURES].dropna()
 if len(U)<30: raise RuntimeError(f'too few unique 2022 entries for threshold freeze: {len(U)}')
 thresh=[]; Q={}
 for f in FEATURES:
  q33=float(U[f].quantile(1/3)); q67=float(U[f].quantile(2/3)); Q[f]=(q33,q67)
  thresh.append({'feature':f,'dev_unique_entry_n':int(U[f].notna().sum()),'q33':q33,'q67':q67,'selection_basis':'2022 unique-entry distribution only; no outcome optimization'})
 pd.DataFrame(thresh).to_csv(OUT_THRESH,index=False)

 rows=[]
 for label,start,end in PERIODS:
  end_eff=min(end,last_ts+pd.Timedelta(microseconds=1))
  for lb,hold in sorted(EXPECTED,key=lambda z:(z[1],z[0])):
   T=event_map[(lb,hold)].copy(); T=T[(T.entry_ts>=start)&(T.entry_ts<end_eff)].copy()
   for f in FEATURES:
    q33,q67=Q[f]; T[f+'_bucket']=[label_bucket(v,q33,q67) for v in T[f]]
    for b in ['LOW','MID','HIGH']:
     rows.append(summarize(T[T[f+'_bucket']==b],label,lb,hold,f,b))
   rvlo,rvhi=Q['rv_60']; atlo,athi=Q['atr_pct_60']
   T['energy_bucket']=np.where((T.rv_60<=rvlo)&(T.atr_pct_60<=atlo),'LOW_ENERGY',np.where((T.rv_60>=rvhi)&(T.atr_pct_60>=athi),'HIGH_ENERGY','MIXED'))
   for b in ['LOW_ENERGY','MIXED','HIGH_ENERGY']:
    rows.append(summarize(T[T.energy_bucket==b],label,lb,hold,'composite_energy',b))
 B=pd.DataFrame(rows); B.to_csv(OUT_BUCKETS,index=False)

 support=[]
 for label,_,_ in PERIODS:
  for f in FEATURES:
   W=B[(B.period==label)&(B.dimension==f)]
   supports=0; usable=0; deltas=[]
   for lb,hold in sorted(EXPECTED,key=lambda z:(z[1],z[0])):
    C=W[(W.lookback_min==lb)&(W.hold_min==hold)].set_index('bucket')
    lo=C.loc['LOW']; hi=C.loc['HIGH']
    ok=(int(lo.n)>=5 and int(hi.n)>=5 and finite(float(lo.exp)) and finite(float(hi.exp)))
    if ok:
     usable+=1; d=float(hi.exp-lo.exp); deltas.append(d); supports+=int(d>0)
   support.append({'period':label,'feature':f,'usable_cells':usable,'support_cells_high_exp_gt_low':supports,
                   'support_rate':supports/usable if usable else np.nan,'median_delta_exp_high_minus_low':float(np.median(deltas)) if deltas else np.nan})
 S=pd.DataFrame(support); S.to_csv(OUT_SUPPORT,index=False)

 # Pre-registered interpretation: historical persistence requires both features to show >50% directional support
 # and positive median high-minus-low expectancy in each of 2023, 2024, and 2025. 2022 is calibration; 2026 is shadow.
 val=S[S.period.isin(['TEST_2023','CONFIRM_2024','FINAL_OOS_2025'])].copy()
 checks=[]
 for period in ['TEST_2023','CONFIRM_2024','FINAL_OOS_2025']:
  W=val[val.period==period]
  ok=bool(len(W)==2 and (W.usable_cells>=3).all() and (W.support_rate>.5).all() and (W.median_delta_exp_high_minus_low>0).all())
  checks.append((period,ok))
 pass_n=sum(int(ok) for _,ok in checks)
 if pass_n==3: status='HISTORICAL_ENERGY_RELATIONSHIP_PERSISTENT'
 elif pass_n>=2: status='HISTORICAL_ENERGY_RELATIONSHIP_PARTIAL'
 else: status='HISTORICAL_ENERGY_RELATIONSHIP_WEAK'

 lines=['# ETH R4b — Stage H Historical Energy-Regime Validation','',
 '**VALIDATION ONLY. FEATURES FIXED FROM STAGE G; THRESHOLDS FROZEN FROM 2022 DISTRIBUTION ONLY. NO PNL-OPTIMIZED CUTS. NO LIVE GATE PROMOTION.**','',
 f'Dataset through frozen Stage-E cutoff: **{last_ts.isoformat()}**. Coverage **{coverage:.4%}**.',
 f'2022 unique entry timestamps used to freeze tertiles: **{len(U)}**.',
 f'RV1H q33/q67: **{Q["rv_60"][0]:.6f} / {Q["rv_60"][1]:.6f}**.',
 f'ATR1H q33/q67: **{Q["atr_pct_60"][0]:.6f} / {Q["atr_pct_60"][1]:.6f}**.',
 f'Stage H status: **{status}**.','',
 '## High-vs-low tertile directional support','',
 '| Period | Feature | Usable cells | High Exp > Low | Support | Median ΔExp |','|---|---|---:|---:|---:|---:|']
 for r in S.itertuples(index=False):
  lines.append(f'| {r.period} | {r.feature} | {int(r.usable_cells)} | {int(r.support_cells_high_exp_gt_low)} | {fmt_pct(float(r.support_rate))} | {fmt_money(float(r.median_delta_exp_high_minus_low))} |')
 lines += ['', '## Validation gates', '']
 for p,ok in checks: lines.append(f'- {p}: **{"PASS" if ok else "FAIL"}**')
 lines += ['', '## Canonical LB240/H360 composite-energy view','',
 '| Period | Bucket | N | WR | Exp | PF |','|---|---|---:|---:|---:|---:|']
 C=B[(B.lookback_min==240)&(B.hold_min==360)&(B.dimension=='composite_energy')]
 for period,_,_ in PERIODS:
  for b in ['LOW_ENERGY','MIXED','HIGH_ENERGY']:
   r=C[(C.period==period)&(C.bucket==b)].iloc[0]
   lines.append(f'| {period} | {b} | {int(r.n)} | {fmt_pct(float(r.wr))} | {fmt_money(float(r.exp))} | {fmt_num(float(r.pf))} |')
 lines += ['', '## Guardrails','',
 '- RV1H and ATR1H were nominated by Stage G; Stage H does not search additional features.',
 '- q33/q67 thresholds come only from the 2022 feature distribution, never from outcomes.',
 '- 2023, 2024, and 2025 are sequential historical validation periods for the energy hypothesis; 2026 is shadow context only.',
 '- Composite-energy buckets are secondary diagnostics; the formal Stage-H verdict uses individual RV1H and ATR1H high-vs-low expectancy direction.',
 '- No strategy parameter, entry, hold, TP/SL, hour, character rule, or risk rule is changed here.',
 '- Even a PASS does not authorize a live regime gate; that requires a separate preregistered gate-validation stage.']
 OUT_RESULT.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
