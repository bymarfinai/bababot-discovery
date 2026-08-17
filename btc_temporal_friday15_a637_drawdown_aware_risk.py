"""BTC Friday15 A6.37 — drawdown-aware risk study on A6.33.

All 138 Friday entries remain. No signal/TP/SL retuning. Risk state uses only completed prior
Friday outcomes on a normalized full-size shadow equity curve, so decisions are causal and
independent of actual size scaling. Test compact natural policies tied to R=$4.25 normal loss:
- reduce whole occurrence size during >=2R or >=3R shadow DD
- reduce only wrong-way sequential SHORT second leg during those states
- simple two-consecutive-loss analogues
Selection: first82 discovery only; require >=95% of baseline discovery PnL, then minimize MDD.
Validation is report-only. Research only; live untouched.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a636_maxdd_forensics as a636
from btc_temporal_a34_5m_events import rnd

R=4.25
POLICIES=(
 ('BASE','NONE',0,1.0),
 ('DD2R_OCC075','DD',2*R,.75),
 ('DD3R_OCC075','DD',3*R,.75),
 ('DD2R_OCC050','DD',2*R,.50),
 ('DD2R_SHORT050','DD_SHORT',2*R,.50),
 ('DD3R_SHORT050','DD_SHORT',3*R,.50),
 ('DD2R_SHORT075','DD_SHORT',2*R,.75),
 ('LOSS2_OCC075','LOSS2',2,.75),
 ('LOSS2_SHORT050','LOSS2_SHORT',2,.50),
)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
  'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def second_leg(r):
 if not r['wrongway']:return None
 rows=r['rows'];i=r['i']
 # Damage-control action exits long early then uses A6.22 post-stop SHORT geometry.
 if r['action']:
  return a611.short_leg(rows,i+24,i+72,1.5,.5)
 if r['prior_stop']:
  return a611.short_leg(rows,i+24,i+72,1.5,.5)
 # Still-open frozen flip uses old A6.20 TP1.3/SL0.7 geometry.
 return a611.short_leg(rows,i+24,i+72,1.3,.7)

def shadow_states(rec):
 eq=0.;peak=0.;loss_run=0;out=[]
 for r in rec:
  out.append({'dd':peak-eq,'loss_run':loss_run})
  eq+=r['chosen'];peak=max(peak,eq)
  loss_run=loss_run+1 if r['chosen']<=0 else 0
 return out

def active(state,kind,threshold):
 if kind.startswith('DD'):return state['dd']>=threshold-1e-12
 if kind.startswith('LOSS2'):return state['loss_run']>=int(threshold)
 return False

def run_policy(rec,states,spec):
 name,kind,thr,factor=spec;pnls=[];acts=[]
 for idx,(r,s) in enumerate(zip(rec,states)):
  p=r['chosen'];act=False;detail=None
  if name!='BASE' and active(s,kind,thr):
   if kind in ('DD','LOSS2'):
    p=p*factor;act=True;detail='WHOLE_OCCURRENCE'
   elif kind in ('DD_SHORT','LOSS2_SHORT') and r['wrongway']:
    sh=second_leg(r)
    if sh is not None:
     long_component=p-sh;p=long_component+sh*factor;act=True;detail='SECOND_LEG_ONLY'
  pnls.append(p);acts.append({'i':idx,'active':act,'detail':detail,'shadow_dd':s['dd'],'loss_run':s['loss_run'],
   'base':r['chosen'],'new':p,'wrongway':r['wrongway']})
 return pnls,acts

def sub(p,acts,lo,hi):
 q=p[lo:hi];aa=acts[lo:hi]
 return {'stats':econ(q),'actions':sum(x['active'] for x in aa),'delta':rnd(sum(q)-sum(x['base'] for x in aa),3),
  'wrongway_actions':sum(x['active'] and x['wrongway'] for x in aa)}

def main():
 _,rec=a636.build();states=shadow_states(rec);base=[r['chosen'] for r in rec];base_disc=econ(base[:82]);variants=[]
 for spec in POLICIES:
  p,a=run_policy(rec,states,spec)
  variants.append({'policy':spec[0],'kind':spec[1],'threshold':spec[2],'factor':spec[3],
   'discovery':sub(p,a,0,82),'validation':sub(p,a,82,len(rec)),'full':sub(p,a,0,len(rec))})
 eligible=[v for v in variants if v['policy']!='BASE' and v['discovery']['stats']['pnl']>=.95*base_disc['pnl']]
 if eligible:
  chosen=min(eligible,key=lambda v:(v['discovery']['stats']['mdd'],-v['discovery']['stats']['pnl']))
 else:
  chosen=max([v for v in variants if v['policy']!='BASE'],key=lambda v:(v['discovery']['stats']['pnl']/(1+v['discovery']['stats']['mdd']/25)))
 out={'status':'FRIDAY15_A637_DRAWDOWN_AWARE_RISK','baseline':{'full':econ(base),'discovery':base_disc,'validation':econ(base[82:])},
  'selection':'first82 only: discovery PnL >=95% baseline, then minimum discovery MDD','variants':variants,'chosen':chosen,
  'rules':'all entries remain; state from prior completed full-size normalized A6.33 shadow equity only','R_usd':R}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
