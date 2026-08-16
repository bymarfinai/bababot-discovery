"""BTC Friday15 A6.29 — two-stage early damage control.

A6.28 showed direct early CUT damages delayed winners. Repair the idea mechanistically:
1) warning state first,
2) allow 15-30m recovery window,
3) CUT only if completed data still show no +0.3 proof and negative progress.

All 138 Friday entries remain. Frozen comparison baseline is A6.22 balanced.
Candidate definitions are compact and derived from A6.28/A6.11, selected on first82 discovery only.
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

HOLD=360;NOTIONAL=500.;FEE_USD=.75;POST_TP=1.5;POST_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
# (name, warning minute, warning type, confirm minute, confirmation type)
CANDS=(
 ('W60_FULL_C75_NP',60,'FULL',75,'NP'),
 ('W60_FULL_C90_NP',60,'FULL',90,'NP'),
 ('W60_FULL_C90_FLOW',60,'FULL',90,'FLOW'),
 ('W90_D20_C105_NP',90,'D20',105,'NP'),
 ('W90_D20_C120_NP',90,'D20',120,'NP'),
 ('W90_FULL_C105_NP',90,'FULL',105,'NP'),
 ('W90_FULL_C120_NP',90,'FULL',120,'NP'),
)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
         'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
         'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def warn(c,kind):
 if c is None or not(c['mfe']<.3 and c['progress']<0):return False
 if kind=='D20':return c['d20']<0
 if kind=='FULL':return c['taker']<0 and c['d20']<0 and c['s20_15']<0
 return False

def confirm(c,kind):
 if c is None or not(c['mfe']<.3 and c['progress']<0):return False
 if kind=='FLOW':return c['taker']<0
 return True

def cuttable(r,h):
 j=r['i']+h//5
 if r['trade']['reason'] in ('TP','SL','AMB_SL'):
  if r['i']+r['trade']['bars']-1<j:return False
 return True

def cut_pnl(rows,r,h):
 px=rows[r['i']+h//5][1]
 return (px-r['entry'])/r['entry']*NOTIONAL-FEE_USD

def baseline(rows,r):
 if r['wrongway']:
  if r['prior_stop']:
   return r['base']+a611.short_leg(rows,r['i']+24,r['i']+72,POST_TP,POST_SL)
  return a620.wrongway_action(rows,r,1.3)
 if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
 return r['base']

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 times=sorted(set([c[1] for c in CANDS]+[c[3] for c in CANDS]))
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
  r['checks']={h:a69.checkpoint(rows,r,e7,e20,h) for h in times}
  r['baseline']=baseline(rows,r);rec.append(r)
 assert len(rec)==138
 variants=[]
 for name,wh,wk,ch,ck in CANDS:
  for r in rec:
   r['action']=warn(r['checks'][wh],wk) and confirm(r['checks'][ch],ck) and cuttable(r,ch)
   r['new']=cut_pnl(rows,r,ch) if r['action'] else r['baseline']
  def sub(q):
   a=[r for r in q if r['action']];los=[r for r in a if r['base']<=0];win=[r for r in a if r['base']>0]
   return {'engine':econ([r['new'] for r in q]),'baseline':econ([r['baseline'] for r in q]),
    'delta':rnd(sum(r['new']-r['baseline'] for r in q),3),'actions':len(a),
    'orig_losses':len(los),'orig_winners':len(win),'loss_precision':rnd(100*len(los)/len(a),2) if a else None,
    'loss_delta':rnd(sum(r['new']-r['baseline'] for r in los),3),
    'winner_delta':rnd(sum(r['new']-r['baseline'] for r in win),3),
    'baseline_win_to_loss':sum(r['baseline']>0 and r['new']<=0 for r in a),
    'loss_to_less_negative':sum(r['base']<=0 and r['new']>r['baseline'] for r in a)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  score=ds['delta'] if ds['actions']>=5 else -1e9
  variants.append({'name':name,'warn':wh,'confirm':ch,'score_disc':rnd(score,3),'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['loss_precision'] or 0,-z['discovery']['baseline_win_to_loss']))
 spec=next(c for c in CANDS if c[0]==chosen['name']);_,wh,wk,ch,ck=spec
 for r in rec:
  r['action']=warn(r['checks'][wh],wk) and confirm(r['checks'][ch],ck) and cuttable(r,ch)
  r['chosen']=cut_pnl(rows,r,ch) if r['action'] else r['baseline']
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'baseline':rnd(sum(r['baseline'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
   'delta':rnd(sum(r['chosen']-r['baseline'] for r in q),3),'actions':sum(r['action'] for r in q)})
 out={'status':'FRIDAY15_A629_TWO_STAGE_DAMAGE_CONTROL','baseline':econ([r['baseline'] for r in rec]),
  'selection':'first82 discovery engine PnL only; min5 actions','variants':sorted(variants,key=lambda z:z['score_disc'],reverse=True),
  'chosen':chosen,'chosen_full':econ([r['chosen'] for r in rec]),'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),
  'chosen_validation':econ([r['chosen'] for r in rec[82:]]),'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
