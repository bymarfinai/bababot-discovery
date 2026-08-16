"""Saturday18 A7.13 — classification-only separability of the A7.12 immediate wrong-way loss family.
No trade management changes and no optimization sweep.

Target family: funding-adjusted parent losses with MFE<0.3% and -0.3% touched before +0.3%.
We evaluate a compact set of hand-specified causal signatures at completed 15/30/60m checkpoints.
All metrics are reported separately for discovery first83 and validation last56.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080
RULES=(
 ('R15_PROGRESS_FLOW',15,lambda s:s['progress']<=-0.05 and s['taker']<=-0.03),
 ('R15_PROGRESS_EMA20',15,lambda s:s['progress']<=-0.05 and s['d20']<0),
 ('R15_FLOW_EMA20',15,lambda s:s['taker']<=-0.05 and s['d20']<0),
 ('R30_PROGRESS_FLOW',30,lambda s:s['progress']<=-0.05 and s['taker']<=-0.02),
 ('R30_PROGRESS_EMA20',30,lambda s:s['progress']<=-0.05 and s['d20']<0),
 ('R60_PROGRESS_FLOW',60,lambda s:s['progress']<=-0.10 and s['taker']<0),
 ('R60_PROGRESS_EMA20',60,lambda s:s['progress']<=-0.10 and s['d20']<0),
 ('R60_PROGRESS_EMA20_SLOPE',60,lambda s:s['progress']<=-0.10 and s['d20']<0 and s['s20_3']<0),
)

def build():
 rows=load(); im={x[0]:i for i,x in enumerate(rows)}; tsmap={x[0]:x for x in rows}
 e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,miss=load_funding();rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
  i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
  if t is None:continue
  base,_,_=a74.funding_adjust(rows,t,funding,tsmap);p=a712.path_stats(rows,i)
  tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN'
  rec.append({'base':base,'tax':tax,'states':{cp:a74.state(rows,i,cp,e7,e20) for cp in (15,30,60)}})
 return rec,miss

def score(q,name,cp,fn):
 eligible=[r for r in q if r['states'].get(cp)]
 sig=[r for r in eligible if fn(r['states'][cp])]
 target=sum(r['tax']=='A1_WRONG_WAY_BEFORE_0.3' for r in eligible)
 hit=sum(r['tax']=='A1_WRONG_WAY_BEFORE_0.3' for r in sig)
 winfp=sum(r['tax']=='WIN' for r in sig)
 otherloss=sum(r['tax']!='WIN' and r['tax']!='A1_WRONG_WAY_BEFORE_0.3' for r in sig)
 return {'eligible':len(eligible),'signals':len(sig),'target_a1':target,'a1_hits':hit,
   'precision_a1_pct':rnd(100*hit/len(sig),2) if sig else None,
   'recall_a1_pct':rnd(100*hit/target,2) if target else None,
   'winner_false_positive':winfp,
   'winner_fp_rate_pct':rnd(100*winfp/max(1,sum(r['tax']=='WIN' for r in eligible)),2),
   'other_loss_signals':otherloss,
   'loss_precision_any_pct':rnd(100*(hit+otherloss)/len(sig),2) if sig else None}

def main():
 rec,miss=build();d=rec[:83];v=rec[83:];out=[]
 for name,cp,fn in RULES:
  out.append({'rule':name,'checkpoint_min':cp,'discovery':score(d,name,cp,fn),'validation':score(v,name,cp,fn),'full':score(rec,name,cp,fn)})
 print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A713_WRONGWAY_SEPARABILITY','parent_n':len(rec),'funding_missing':miss,'rules':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
