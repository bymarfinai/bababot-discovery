"""BTC Friday15 A6.32 — EMA failure structure for conditional damage control.

Question: can EMA structure identify Friday BUY failure earlier or more precisely than the
current A6.30 60m FULL warning? All 138 Friday entries remain. Parent and A6.22 management
are frozen. Action is ONLY the already-researched conditional first-leg stop cap -0.50%; no
new TP/SL geometry and no direct CUT.

Strict causal: at checkpoint h, EMA/rejection features use completed 5m candles through h-5m
and the actual h-minute open. Candidate selection is first82 discovery engine PnL only;
last56 validation is report-only.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a630_conditional_tight_stop as a630
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

HOLD=360; CAP=.50
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
CHECKS=(30,45,60)
KINDS=('REF_FULL','STACK_DOWN','STACK_WIDEN','REJECT7_STACK','REJECT20_DOWN','NP_STACK_DOWN','NP_STACK_WIDEN','NP_REJECT7')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
  'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
  'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def ema_state(rows,r,e7,e20,h):
 i=r['i'];j=i+h//5
 if j>=len(rows) or j<=i:return None
 last=j-1;prev=max(i,last-3)
 if rows[j][0]!=rows[i][0]+(h//5)*TF:return None
 op=rows[j][1];c=rows[last][4];o=rows[last][1];hi=rows[last][2]
 e7l=e7[last];e20l=e20[last];e7p=e7[prev];e20p=e20[prev]
 spread=(e7l-e20l)/e20l if e20l else 0
 spread_prev=(e7p-e20p)/e20p if e20p else 0
 return {
  'below7':op<e7l,'below20':op<e20l,'stack':op<e7l<e20l,
  's7down':e7l<e7p,'s20down':e20l<e20p,
  'widen':spread<spread_prev,
  'reject7':hi>=e7l and c<e7l and c<o,
  'reject20':hi>=e20l and c<e20l and c<o,
  'spread_pct':100*spread,
 }

def signal(r,h,kind):
 c=r['checks'][h];s=r['ema'][h]
 if c is None or s is None:return False
 np=(c['mfe']<.3 and c['progress']<0)
 if kind=='REF_FULL':
  return h==60 and np and c['taker']<0 and c['d20']<0 and c['s20_15']<0
 if kind=='STACK_DOWN':return s['stack'] and s['s7down'] and s['s20down']
 if kind=='STACK_WIDEN':return s['stack'] and s['s7down'] and s['s20down'] and s['widen']
 if kind=='REJECT7_STACK':return s['stack'] and s['reject7'] and s['s20down']
 if kind=='REJECT20_DOWN':return s['below20'] and s['reject20'] and s['s20down']
 if kind=='NP_STACK_DOWN':return np and s['stack'] and s['s7down'] and s['s20down']
 if kind=='NP_STACK_WIDEN':return np and s['stack'] and s['s7down'] and s['s20down'] and s['widen']
 if kind=='NP_REJECT7':return np and s['below20'] and s['reject7'] and s['s20down']
 return False

def managed(rows,r,h,kind):
 if not signal(r,h,kind):return r['baseline'],False
 ep=a630.early_stop(rows,r,h,CAP)
 if ep is None:return r['baseline'],False
 if ep>0:return ep,True
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
  r['baseline']=a630.baseline(rows,r)
  r['checks']={h:a69.checkpoint(rows,r,e7,e20,h) for h in CHECKS}
  r['ema']={h:ema_state(rows,r,e7,e20,h) for h in CHECKS}
  rec.append(r)
 assert len(rec)==138
 variants=[]
 specs=[(60,'REF_FULL')]+[(h,k) for h in CHECKS for k in KINDS if k!='REF_FULL']
 for h,kind in specs:
  for r in rec:r['new'],r['action']=managed(rows,r,h,kind)
  def sub(q):
   a=[r for r in q if r['action']];los=[r for r in a if r['base']<=0];win=[r for r in a if r['base']>0]
   return {'engine':econ([r['new'] for r in q]),'baseline':econ([r['baseline'] for r in q]),
    'delta':rnd(sum(r['new']-r['baseline'] for r in q),3),'actions':len(a),
    'orig_losses':len(los),'orig_winners':len(win),
    'loss_precision':rnd(100*len(los)/len(a),2) if a else None,
    'loss_delta':rnd(sum(r['new']-r['baseline'] for r in los),3),
    'winner_delta':rnd(sum(r['new']-r['baseline'] for r in win),3),
    'baseline_win_to_loss':sum(r['baseline']>0 and r['new']<=0 for r in a),
    'loss_to_less_negative':sum(r['base']<=0 and r['new']>r['baseline'] for r in a)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'h':h,'kind':kind,'score_disc':ds['delta'],'discovery':ds,'validation':vs,'full':fs})
 eligible=[v for v in variants if v['discovery']['actions']>=2]
 chosen=max(eligible,key=lambda z:(z['score_disc'],z['discovery']['loss_precision'] or 0,-z['discovery']['baseline_win_to_loss']))
 for r in rec:r['chosen'],r['action']=managed(rows,r,chosen['h'],chosen['kind'])
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
   'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['action'] for r in q)})
 out={'status':'FRIDAY15_A632_EMA_FAILURE_STRUCTURE','baseline':econ([r['baseline'] for r in rec]),
  'reference':'A6.30 60m FULL warning + conditional SL cap0.50','selection':'first82 discovery PnL only; EMA structural rules; min2 discovery actions',
  'variants':sorted(variants,key=lambda z:z['score_disc'],reverse=True),'chosen':chosen,
  'chosen_full':econ([r['chosen'] for r in rec]),'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),
  'chosen_validation':econ([r['chosen'] for r in rec[82:]]),'blocks':blocks,
  'positive_delta_blocks':sum(b['delta']>0 for b in blocks),'negative_delta_blocks':sum(b['delta']<0 for b in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
