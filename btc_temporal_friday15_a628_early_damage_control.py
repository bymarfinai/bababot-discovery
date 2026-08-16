"""BTC Friday15 A6.28 — early damage control on full 138 Friday entries.

Question: can we reduce the economic damage of eventual losers by cutting early when the
BUY thesis is already visibly failing, without filtering any Friday entry?

Frozen baseline = A6.22 balanced:
- every Friday 15:00 WIB BUY enters
- parent BUY TP2.0 / SL0.7 / max6h
- failed-thesis detector 60m+120m
- if already stopped before120: sequential SHORT TP1.5/SL0.5
- if still open at120: current FLIP SHORT TP1.3/SL0.7
- A6.15 distribution protection unchanged

A6.28 adds ONE earlier CUT layer before later A6.22 management. Signal uses only completed
5m bars available at actual 15/30/60/90m open. If original BUY already exited, no early cut.
Compact candidates use the previously observed wrong-way ingredients only: no +0.3 MFE,
negative progress, negative taker flow, below EMA20, falling EMA20. Select on first82
discovery engine PnL only; validation remains unseen for selection.
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

HOLD=360; NOTIONAL=500.; FEE_USD=.75; POST_TP=1.5; POST_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
CHECKS=(15,30,60,90)
KINDS=('NP','NP_FLOW','NP_D20','FULL_FAIL')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
         'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
         'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),
         'ls':a60.loss_streak(p)}

def signal(c,kind):
 if c is None:return False
 # "NP" = no proof of rebound yet: no +0.3 MFE and negative current progress.
 if not(c['mfe']<.3 and c['progress']<0):return False
 if kind in ('NP_FLOW','FULL_FAIL') and not(c['taker']<0):return False
 if kind in ('NP_D20','FULL_FAIL') and not(c['d20']<0):return False
 if kind=='FULL_FAIL' and not(c['s20_15']<0):return False
 return True

def cuttable(r,h):
 j=r['i']+h//5
 if r['trade']['reason'] in ('TP','SL','AMB_SL'):
  exit_idx=r['i']+r['trade']['bars']-1
  if exit_idx<j:return False
 return True

def cut_pnl(rows,r,h):
 j=r['i']+h//5;px=rows[j][1]
 return (px-r['entry'])/r['entry']*NOTIONAL-FEE_USD

def baseline(rows,r):
 if r['wrongway']:
  if r['prior_stop']:
   j=r['i']+120//5;end=r['i']+HOLD//5
   return r['base']+a611.short_leg(rows,j,end,POST_TP,POST_SL)
  return a620.wrongway_action(rows,r,1.3)
 if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
 return r['base']

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a620.confirmed(rows,r,e7,e20)
  r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  r['checks']={h:a69.checkpoint(rows,r,e7,e20,h) for h in CHECKS}
  r['baseline']=baseline(rows,r);rec.append(r)
 assert len(rec)==138

 variants=[]
 for h in CHECKS:
  for kind in KINDS:
   for r in rec:
    r['early']=cuttable(r,h) and signal(r['checks'][h],kind)
    r['new']=cut_pnl(rows,r,h) if r['early'] else r['baseline']
   def sub(q):
    a=[r for r in q if r['early']]
    origloss=[r for r in a if r['base']<=0];origwin=[r for r in a if r['base']>0]
    saved=sum((r['baseline']-r['new'])<0 for r in origloss)
    return {'engine':econ([r['new'] for r in q]),'baseline':econ([r['baseline'] for r in q]),
      'delta':rnd(sum(r['new']-r['baseline'] for r in q),3),'actions':len(a),
      'orig_loss_actions':len(origloss),'orig_win_actions':len(origwin),
      'loss_precision':rnd(100*len(origloss)/len(a),2) if a else None,
      'loss_damage_before':rnd(sum(r['baseline'] for r in origloss),3),
      'loss_damage_after':rnd(sum(r['new'] for r in origloss),3),
      'loss_damage_improvement':rnd(sum(r['new']-r['baseline'] for r in origloss),3),
      'winner_pnl_before':rnd(sum(r['baseline'] for r in origwin),3),
      'winner_pnl_after':rnd(sum(r['new'] for r in origwin),3),
      'winner_damage':rnd(sum(r['new']-r['baseline'] for r in origwin),3),
      'baseline_win_to_loss':sum(r['baseline']>0 and r['new']<=0 for r in a),
      'loss_to_less_negative':sum(r['base']<=0 and r['new']>r['baseline'] for r in a)}
   ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
   score=ds['delta'] if ds['actions']>=6 else -1e9
   variants.append({'h':h,'kind':kind,'score_disc':rnd(score,3),'discovery':ds,'validation':vs,'full':fs})

 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['loss_precision'] or 0,-z['discovery']['baseline_win_to_loss']))
 h=chosen['h'];kind=chosen['kind']
 for r in rec:
  r['early']=cuttable(r,h) and signal(r['checks'][h],kind)
  r['chosen']=cut_pnl(rows,r,h) if r['early'] else r['baseline']
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),
    'new':rnd(sum(r['chosen'] for r in q),3),'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),
    'actions':sum(r['early'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y]
  years[str(y)]={'baseline':econ([r['baseline'] for r in q]),'new':econ([r['chosen'] for r in q]),
    'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['early'] for r in q)}
 acts=[r for r in rec if r['early']]
 out={'status':'FRIDAY15_A628_EARLY_DAMAGE_CONTROL','selection':'first82 discovery engine PnL only; min6 discovery actions',
  'baseline_a622':econ([r['baseline'] for r in rec]),'variants':sorted(variants,key=lambda z:z['score_disc'],reverse=True),
  'chosen':chosen,'chosen_full':econ([r['chosen'] for r in rec]),
  'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),'chosen_validation':econ([r['chosen'] for r in rec[82:]]),
  'transition':{'actions':len(acts),'orig_losses':sum(r['base']<=0 for r in acts),'orig_winners':sum(r['base']>0 for r in acts),
   'baseline_win_to_loss':sum(r['baseline']>0 and r['chosen']<=0 for r in acts),
   'loss_to_less_negative':sum(r['base']<=0 and r['chosen']>r['baseline'] for r in acts)},
  'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
