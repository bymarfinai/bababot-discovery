"""BTC Friday15 A6.31 — robustness of A6.30 conditional tight stop.

Freeze A6.30 mechanism: 60m FULL failure warning, then tighten first-leg BUY stop while keeping
A6.22 rescue machinery. Reference cap=0.50%. Test local cap plateau only; do not re-select a
new champion from full/validation. Also leave-one-action-out and execution-cost stress.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a630_conditional_tight_stop as a630
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

CAPS=(.45,.50,.55,.60,.65);REF=.50;RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,360);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a620.confirmed(rows,r,e7,e20);r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  r['checks']={60:a69.checkpoint(rows,r,e7,e20,60)};r['baseline']=a630.baseline(rows,r);rec.append(r)
 assert len(rec)==138
 plateau=[]
 for cap in CAPS:
  for r in rec:r['p'],r['act']=a630.managed(rows,r,60,'FULL',cap)
  plateau.append({'cap':cap,'full':a630.econ([r['p'] for r in rec]),'discovery':a630.econ([r['p'] for r in rec[:82]]),
   'validation':a630.econ([r['p'] for r in rec[82:]]),'delta_full':rnd(sum(r['p']-r['baseline'] for r in rec),3),
   'delta_disc':rnd(sum(r['p']-r['baseline'] for r in rec[:82]),3),'delta_val':rnd(sum(r['p']-r['baseline'] for r in rec[82:]),3),
   'actions_full':sum(r['act'] for r in rec),'actions_disc':sum(r['act'] for r in rec[:82]),'actions_val':sum(r['act'] for r in rec[82:])})
 # Materialize fixed reference cap .50 only.
 for r in rec:r['ref'],r['act']=a630.managed(rows,r,60,'FULL',REF)
 acts=[r for r in rec if r['act']]
 loo=[]
 for z in acts:
  p=[(r['baseline'] if r is z else r['ref']) for r in rec]
  loo.append(sum(p))
 stress=[]
 for pct in (0,.02,.05,.10,.15):
  extra=500*pct/100
  p=[r['ref']-(extra if r['act'] else 0) for r in rec]
  stress.append({'extra_pct_per_action':pct,'stats':a630.econ(p)})
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),'new':rnd(sum(r['ref'] for r in q),3),
   'delta':rnd(sum(r['ref']-r['baseline'] for r in q),3),'actions':sum(r['act'] for r in q)})
 out={'status':'FRIDAY15_A631_TIGHT_STOP_ROBUSTNESS','reference':{'warning':'60m FULL failure','cap':REF},
  'baseline':a630.econ([r['baseline'] for r in rec]),'reference_full':a630.econ([r['ref'] for r in rec]),
  'plateau':plateau,'loo_min_pnl':rnd(min(loo),3) if loo else None,'loo_max_pnl':rnd(max(loo),3) if loo else None,
  'stress':stress,'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),
  'actions':len(acts),'orig_loss_actions':sum(r['base']<=0 for r in acts),'orig_win_actions':sum(r['base']>0 for r in acts),
  'baseline_win_to_loss':sum(r['baseline']>0 and r['ref']<=0 for r in acts),
  'loss_to_less_negative':sum(r['base']<=0 and r['ref']>r['baseline'] for r in acts)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
