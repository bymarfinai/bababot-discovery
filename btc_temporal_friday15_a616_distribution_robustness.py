"""BTC Friday15 A6.16 — robustness of A6.15 distribution giveback candidate.

Mechanism fixed: actionable +0.5% hinge; within 60m completed close <= +0.30%;
strong negative taker flow; close remains above EMA20; arm +0.20% profit lock.
A6.12 wrong-way layer remains baseline. All 138 Fridays enter.
This pass checks local taker threshold plateau, LOO, year/block stability, and extra action cost.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a613_giveback_rescue as a613
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
import btc_temporal_saturday18_a74_loss_forensics as a74

RULE=next(r for r in a613.RULES if r[0]=='GB30_60');LOCK=.20
THRESHOLDS=(-.035,-.040,-.045,-.050)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def active(sig,thr):
 return sig is not None and sig['state']['taker']<=thr and sig['state']['d20']>0

def build(rows,e7,e20):
 im={x[0]:i for i,x in enumerate(rows)};rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,360);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a613.wrongway_signal(rows,r,e7,e20);r['a612']=a613.wrongway_pnl(rows,r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  rec.append(r)
 return rec

def materialize(rows,rec,thr):
 for r in rec:
  r['active']=not r['wrongway'] and active(r['sig'],thr)
  r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK) if r['active'] else r['a612']

def sub(q):
 a=[r for r in q if r['active']]
 return {'stats':econ([r['new'] for r in q]),'baseline':econ([r['a612'] for r in q]),'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'actions':len(a),
  'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in a),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in a),'win_clipped':sum(r['base']>0 and 0<r['new']<r['base'] for r in a)}

def main():
 rows=load();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=build(rows,e7,e20);assert len(rec)==138
 plateau=[]
 for thr in THRESHOLDS:
  materialize(rows,rec,thr)
  plateau.append({'taker_thr':thr,'discovery':sub(rec[:82]),'validation':sub(rec[82:]),'full':sub(rec)})
 # canonical A6.15 threshold
 materialize(rows,rec,-.040)
 base=[r['a612'] for r in rec];new=[r['new'] for r in rec];acts=[r for r in rec if r['active']]
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'actions':sum(r['active'] for r in q),'new_pnl':rnd(sum(r['new'] for r in q),3)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y]
  years[str(y)]={'actions':sum(r['active'] for r in q),'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'a612':econ([r['a612'] for r in q]),'new':econ([r['new'] for r in q])}
 loo=[]
 for z in acts:
  p=[r['a612'] if r is z else r['new'] for r in rec];loo.append(sum(p))
 stress=[]
 for pct in (0,.02,.05,.10,.15):
  extra=500*pct/100
  p=[r['new']-(extra if r['active'] else 0) for r in rec]
  stress.append({'extra_pct_action':pct,'extra_usd_action':rnd(extra,3),'stats':econ(p)})
 out={'status':'FRIDAY15_A616_DISTRIBUTION_ROBUSTNESS','plateau':plateau,'canonical_thr':-.04,
  'a612':econ(base),'new':econ(new),'delta':rnd(sum(new)-sum(base),3),'actions':len(acts),
  'transitions':{'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in acts),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in acts),'win_clipped':sum(r['base']>0 and 0<r['new']<r['base'] for r in acts)},
  'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years,
  'loo_min_pnl':rnd(min(loo),3) if loo else None,'loo_max_pnl':rnd(max(loo),3) if loo else None,'stress':stress}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
