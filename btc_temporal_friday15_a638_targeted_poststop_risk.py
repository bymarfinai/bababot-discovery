"""BTC Friday15 A6.38 — targeted risk reduction for damage-control post-stop rescue.

Motivated by A6.36: biggest individual DD hits are -6.5/-7.5 double-loss occurrences.
Do NOT resize normal Friday occurrences or still-open flips. Only when A6.33 damage-control
has already stopped the BUY early AND the frozen wrong-way state triggers a sequential SHORT,
reduce that SHORT size during a causal prior strategy stress state.

Key economics for damage-control first leg: long ~= -3.25. Full short TP ~= +6.75 / SL ~= -3.25.
At 50% short size, a successful rescue remains slightly positive (~+0.125) while a failed
rescue improves from ~-6.5 to ~-4.875. Thus 50% is a structural risk-budget choice, not a
local TP/SL retune.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a637_drawdown_aware_risk as a637
from btc_temporal_a34_5m_events import rnd

R=4.25
SPECS=(
 ('BASE','NONE',0,1.0),
 ('DD2R_DAMAGE_SHORT050','DD',2*R,.50),
 ('DD3R_DAMAGE_SHORT050','DD',3*R,.50),
 ('LOSS2_DAMAGE_SHORT050','LOSS2',2,.50),
 ('DD2R_DAMAGE_SHORT075','DD',2*R,.75),
)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
  'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def active(s,kind,thr):
 if kind=='DD':return s['dd']>=thr-1e-12
 if kind=='LOSS2':return s['loss_run']>=int(thr)
 return False

def eligible_target(r):
 return bool(r['action'] and r['wrongway'])

def run(rec,states,spec):
 name,kind,thr,f=spec;p=[];acts=[]
 for r,s in zip(rec,states):
  z=r['chosen'];act=False
  if name!='BASE' and active(s,kind,thr) and eligible_target(r):
   sh=a611.short_leg(r['rows'],r['i']+24,r['i']+72,1.5,.5)
   long=z-sh;z=long+sh*f;act=True
  p.append(z);acts.append({'active':act,'base':r['chosen'],'new':z,'shadow_dd':s['dd'],'loss_run':s['loss_run']})
 return p,acts

def sub(p,a,lo,hi):
 q=p[lo:hi];aa=a[lo:hi]
 return {'stats':econ(q),'actions':sum(x['active'] for x in aa),'delta':rnd(sum(q)-sum(x['base'] for x in aa),3),
  'improved_actions':sum(x['active'] and x['new']>x['base'] for x in aa),
  'worsened_actions':sum(x['active'] and x['new']<x['base'] for x in aa),
  'base_win_to_loss':sum(x['active'] and x['base']>0 and x['new']<=0 for x in aa)}

def main():
 _,rec=a636.build();states=a637.shadow_states(rec);base=[r['chosen'] for r in rec];variants=[]
 for spec in SPECS:
  p,a=run(rec,states,spec)
  variants.append({'policy':spec[0],'kind':spec[1],'threshold':spec[2],'short_factor':spec[3],
   'discovery':sub(p,a,0,82),'validation':sub(p,a,82,len(rec)),'full':sub(p,a,0,len(rec))})
 # Predeclared mechanism candidate from forensics: DD>=2R, damage-stop sequential short at half size.
 chosen=next(v for v in variants if v['policy']=='DD2R_DAMAGE_SHORT050')
 out={'status':'FRIDAY15_A638_TARGETED_POSTSTOP_RISK','baseline':{'full':econ(base),'discovery':econ(base[:82]),'validation':econ(base[82:])},
  'chosen':chosen,'variants':variants,
  'mechanism':'only damage-control+wrongway sequential short resized; all initial Friday entries and all normal/still-open cases unchanged'}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
