"""BTC Friday15 A6.33 — EMA early warning + frozen 60m fallback.

Predeclared architecture after A6.32 mechanism study:
- all 138 Friday15 BUY entries remain
- A6.22 baseline management frozen
- first chance at 45m: bearish EMA stack widening = price<EMA7<EMA20, EMA7 down,
  EMA20 down, EMA7-EMA20 spread widening bearish. If true, arm -0.50% first-leg stop.
- if no 45m EMA warning, retain frozen A6.30 60m FULL warning as fallback and arm same -0.50%.
- if early stop fires and frozen 120m wrong-way failure is confirmed, retain post-stop SHORT
  TP1.5/SL0.5. No new target/stop tuning.

Strict causal, completed 5m only. This tests whether EMA can move the proven damage-control
response earlier without replacing the existing fallback.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a630_conditional_tight_stop as a630
import btc_temporal_friday15_a632_ema_failure_structure as a632
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

HOLD=360;CAP=.50;RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
  'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
  'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def ema45(r):
 s=r['ema45']
 return bool(s and s['stack'] and s['s7down'] and s['s20down'] and s['widen'])

def full60(r):
 c=r['c60']
 return bool(c and c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0 and c['s20_15']<0)

def apply_from(rows,r,h,source):
 ep=a630.early_stop(rows,r,h,CAP)
 if ep is None:return r['baseline'],False,source
 if ep>0:return ep,True,source
 if r['wrongway']:ep+=a611.short_leg(rows,r['i']+24,r['i']+72,1.5,.5)
 return ep,True,source

def managed(rows,r,mode):
 if mode=='REF60':
  if full60(r):return apply_from(rows,r,60,'FULL60')
  return r['baseline'],False,None
 if mode=='EMA45_ONLY':
  if ema45(r):return apply_from(rows,r,45,'EMA45')
  return r['baseline'],False,None
 if mode=='EMA45_OR_FULL60':
  if ema45(r):return apply_from(rows,r,45,'EMA45')
  if full60(r):return apply_from(rows,r,60,'FULL60')
  return r['baseline'],False,None
 raise ValueError(mode)

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a620.confirmed(rows,r,e7,e20);r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  r['baseline']=a630.baseline(rows,r)
  r['c60']=a69.checkpoint(rows,r,e7,e20,60)
  r['ema45']=a632.ema_state(rows,r,e7,e20,45)
  rec.append(r)
 assert len(rec)==138
 modes=('REF60','EMA45_ONLY','EMA45_OR_FULL60');variants=[]
 for mode in modes:
  for r in rec:r['new'],r['action'],r['source']=managed(rows,r,mode)
  def sub(q):
   a=[r for r in q if r['action']];los=[r for r in a if r['base']<=0];win=[r for r in a if r['base']>0]
   return {'engine':econ([r['new'] for r in q]),'baseline':econ([r['baseline'] for r in q]),
    'delta':rnd(sum(r['new']-r['baseline'] for r in q),3),'actions':len(a),
    'ema45_actions':sum(r['source']=='EMA45' for r in a),'fallback60_actions':sum(r['source']=='FULL60' for r in a),
    'orig_losses':len(los),'orig_winners':len(win),'loss_precision':rnd(100*len(los)/len(a),2) if a else None,
    'loss_delta':rnd(sum(r['new']-r['baseline'] for r in los),3),'winner_delta':rnd(sum(r['new']-r['baseline'] for r in win),3),
    'baseline_win_to_loss':sum(r['baseline']>0 and r['new']<=0 for r in a),
    'loss_to_less_negative':sum(r['base']<=0 and r['new']>r['baseline'] for r in a)}
  variants.append({'mode':mode,'discovery':sub(rec[:82]),'validation':sub(rec[82:]),'full':sub(rec)})
 # Architecture candidate fixed ex ante; not selected on validation.
 chosen=next(v for v in variants if v['mode']=='EMA45_OR_FULL60')
 for r in rec:r['chosen'],r['action'],r['source']=managed(rows,r,'EMA45_OR_FULL60')
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
   'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['action'] for r in q),
   'ema45':sum(r['source']=='EMA45' for r in q),'fallback60':sum(r['source']=='FULL60' for r in q)})
 out={'status':'FRIDAY15_A633_EMA_EARLY_WARNING_UNION','baseline':econ([r['baseline'] for r in rec]),
  'architecture':'EMA45 stack+widen first; if absent frozen FULL60 fallback; cap0.50; A6.22 downstream frozen',
  'variants':variants,'chosen':chosen,'chosen_full':econ([r['chosen'] for r in rec]),
  'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),'chosen_validation':econ([r['chosen'] for r in rec[82:]]),
  'blocks':blocks,'positive_delta_blocks':sum(b['delta']>0 for b in blocks),'negative_delta_blocks':sum(b['delta']<0 for b in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
