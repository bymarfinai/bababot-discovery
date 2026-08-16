"""BTC Friday15 A6.30 — conditional first-leg loss cap.

Instead of fixed-time CUT, tighten the BUY protective stop only after a causal failure warning.
All 138 Friday entries remain. If the tighter first-leg stop fires before120m and the frozen
failure state is still confirmed at120m, A6.22 sequential SHORT rescue TP1.5/SL0.5 is still
allowed. Goal: reduce sunk BUY loss while retaining recovery machinery.

Compact candidates only: warning at60 FULL_FAIL or 90 NP_D20; tightened stop 0.5/0.6 vs
original 0.7. Selection first82 discovery PnL only.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

HOLD=360;NOTIONAL=500.;FEE_USD=.75
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
CANDS=((60,'FULL',.5),(60,'FULL',.6),(90,'D20',.5),(90,'D20',.6))

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
  'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
  'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def warning(c,kind):
 if c is None or not(c['mfe']<.3 and c['progress']<0):return False
 if kind=='FULL':return c['taker']<0 and c['d20']<0 and c['s20_15']<0
 if kind=='D20':return c['d20']<0
 return False

def baseline(rows,r):
 if r['wrongway']:
  if r['prior_stop']:
   return r['base']+a611.short_leg(rows,r['i']+24,r['i']+72,1.5,.5)
  return a620.wrongway_action(rows,r,1.3)
 if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
 return r['base']

def early_stop(rows,r,h,cap):
 """Arm tightened long stop at actual h-minute open through just before 120m open.
 Returns realized long pnl if it fires, else None. If already through stop at arm time,
 exit at actual arm open. Original TP2 remains live; TP+stop same 5m -> stop first.
 """
 i=r['i'];j=i+h//5;end=i+24;e=r['entry'];sp=e*(1-cap/100);tp=e*1.02
 # If parent already exited strictly before arm time, cannot tighten.
 if r['trade']['reason'] in ('TP','SL','AMB_SL') and i+r['trade']['bars']-1<j:return None
 op=rows[j][1]
 if op<=sp:return (op-e)/e*NOTIONAL-FEE_USD
 for k in range(j,end):
  x=rows[k];hs=x[3]<=sp;ht=x[2]>=tp
  if hs:return -cap/100*NOTIONAL-FEE_USD
  if ht:return 2.0/100*NOTIONAL-FEE_USD
 return None

def managed(rows,r,h,kind,cap):
 if not warning(r['checks'][h],kind):return r['baseline'],False
 ep=early_stop(rows,r,h,cap)
 if ep is None:return r['baseline'],False
 # If early exit was positive TP, no rescue is needed.
 if ep>0:return ep,True
 # Frozen failure confirmation may still trigger a new post-stop SHORT at120.
 if r['wrongway']:
  ep+=a611.short_leg(rows,r['i']+24,r['i']+72,1.5,.5)
 return ep,True

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
  r['checks']={60:a69.checkpoint(rows,r,e7,e20,60),90:a69.checkpoint(rows,r,e7,e20,90)}
  r['baseline']=baseline(rows,r);rec.append(r)
 assert len(rec)==138
 variants=[]
 for h,kind,cap in CANDS:
  for r in rec:r['new'],r['action']=managed(rows,r,h,kind,cap)
  def sub(q):
   a=[r for r in q if r['action']];los=[r for r in a if r['base']<=0];win=[r for r in a if r['base']>0]
   return {'engine':econ([r['new'] for r in q]),'baseline':econ([r['baseline'] for r in q]),
    'delta':rnd(sum(r['new']-r['baseline'] for r in q),3),'actions':len(a),
    'orig_losses':len(los),'orig_winners':len(win),'loss_precision':rnd(100*len(los)/len(a),2) if a else None,
    'loss_delta':rnd(sum(r['new']-r['baseline'] for r in los),3),'winner_delta':rnd(sum(r['new']-r['baseline'] for r in win),3),
    'loss_to_less_negative':sum(r['base']<=0 and r['new']>r['baseline'] for r in a),
    'baseline_win_to_loss':sum(r['baseline']>0 and r['new']<=0 for r in a)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'warn':h,'kind':kind,'cap':cap,'score_disc':ds['delta'],'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['loss_precision'] or 0,-z['discovery']['baseline_win_to_loss']))
 h=chosen['warn'];kind=chosen['kind'];cap=chosen['cap']
 for r in rec:r['chosen'],r['action']=managed(rows,r,h,kind,cap)
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
   'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['action'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y]
  years[str(y)]={'baseline':econ([r['baseline'] for r in q]),'new':econ([r['chosen'] for r in q]),
   'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['action'] for r in q)}
 out={'status':'FRIDAY15_A630_CONDITIONAL_TIGHT_STOP','baseline':econ([r['baseline'] for r in rec]),
  'selection':'first82 discovery engine PnL only','variants':variants,'chosen':chosen,
  'chosen_full':econ([r['chosen'] for r in rec]),'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),
  'chosen_validation':econ([r['chosen'] for r in rec[82:]]),'blocks':blocks,
  'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
