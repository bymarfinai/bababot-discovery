"""BTC Friday15 A6.17b — live-parity repair for A6.12 wrong-way handling.

A6.17 exposed that some 120m confirmed-failure cases had already hit the original BUY SL0.7%
before the 120m decision. The old A6.12 action incorrectly replaced that already-realized long
loss with a synthetic long PnL at 120m.

Repair policy:
- failure detector remains frozen (60m initial + 120m persistent state)
- if original BUY is still open at the 120m open: close actual BUY at 120m open, then SHORT
- if original BUY already exited before 120m: keep its realized parent PnL exactly; optional
  REENTRY policy opens a new SHORT at 120m, while NO_REENTRY leaves the realized exit alone
- SHORT geometry remains frozen TP1.0% / SL0.7%, expiry at original 6h horizon
- every Friday15 original BUY still occurs; sequential second leg is explicitly counted
Research only; live untouched.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

H=120; HOLD=360; FEE_USD=.75; NOTIONAL=500.

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def confirmed(rows,r,e7,e20):
 c60=a69.checkpoint(rows,r,e7,e20,60);c120=a69.checkpoint(rows,r,e7,e20,120)
 return bool(c60 and c120 and a612.initial(c60) and a612.confirmed(c120))

def exited_before_120(r):
 if r['trade']['reason'] not in ('SL','AMB_SL','TP'):return False
 exit_idx=r['i']+r['trade']['bars']-1; decision=r['i']+H//5
 return exit_idx < decision

def repaired(rows,r,reentry=True):
 if not r['confirmed']:return r['base']
 j=r['i']+H//5; end=r['i']+HOLD//5
 if exited_before_120(r):
  if not reentry:return r['base']
  return r['base'] + a611.short_leg(rows,j,end,1.0,.7)
 # position is still alive at 120m open; close actual BUY then open short
 e=r['entry'];px=rows[j][1];long_pnl=(px-e)/e*NOTIONAL-FEE_USD
 return long_pnl + a611.short_leg(rows,j,end,1.0,.7)

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r);r['confirmed']=confirmed(rows,r,e7,e20);r['stopped_before']=r['confirmed'] and exited_before_120(r)
  rr=dict(r);rr['confirmed']=r['confirmed'];r['old_a612']=a611.action(rows,rr,H,'FLIP',(1.0,.7)) if r['confirmed'] else r['base']
  r['reentry']=repaired(rows,r,True);r['no_reentry']=repaired(rows,r,False);rec.append(r)
 assert len(rec)==138
 def subset(q,key):return econ([r[key] for r in q])
 out={'status':'FRIDAY15_A617B_WRONGWAY_PARITY_REPAIR',
  'counts':{'n':138,'confirmed':sum(r['confirmed'] for r in rec),'already_exited_before_120':sum(r['stopped_before'] for r in rec),'still_open_at_120':sum(r['confirmed'] and not r['stopped_before'] for r in rec),
            'stopped_labels':{lab:sum(r['stopped_before'] and r['label']==lab for r in rec) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')}},
  'full':{'parent':subset(rec,'base'),'old_a612_invalid':subset(rec,'old_a612'),'reentry_repaired':subset(rec,'reentry'),'no_reentry_repaired':subset(rec,'no_reentry')},
  'discovery':{'parent':subset(rec[:82],'base'),'old_a612_invalid':subset(rec[:82],'old_a612'),'reentry_repaired':subset(rec[:82],'reentry'),'no_reentry_repaired':subset(rec[:82],'no_reentry')},
  'validation':{'parent':subset(rec[82:],'base'),'old_a612_invalid':subset(rec[82:],'old_a612'),'reentry_repaired':subset(rec[82:],'reentry'),'no_reentry_repaired':subset(rec[82:],'no_reentry')},
  'delta_vs_parent':{
   'reentry_full':rnd(sum(r['reentry']-r['base'] for r in rec),3),'reentry_disc':rnd(sum(r['reentry']-r['base'] for r in rec[:82]),3),'reentry_val':rnd(sum(r['reentry']-r['base'] for r in rec[82:]),3),
   'no_reentry_full':rnd(sum(r['no_reentry']-r['base'] for r in rec),3),'no_reentry_disc':rnd(sum(r['no_reentry']-r['base'] for r in rec[:82]),3),'no_reentry_val':rnd(sum(r['no_reentry']-r['base'] for r in rec[82:]),3)},
  'cases':[{'ts':r['ts'],'label':r['label'],'base':rnd(r['base'],3),'stopped_before':r['stopped_before'],'old':rnd(r['old_a612'],3),'reentry':rnd(r['reentry'],3),'no_reentry':rnd(r['no_reentry'],3)} for r in rec if r['confirmed']]}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
