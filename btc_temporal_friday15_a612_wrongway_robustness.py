"""BTC Friday15 A6.12 — robustness of full-coverage wrong-way intervention.

Fixed candidate from A6.10/A6.11:
- every Friday15 BUY still enters
- at 60m initial failure: MFE<.3, progress<0, taker<0, d20<0, EMA20 15m slope<0
- do not act yet
- at 120m confirm if cumulative MFE still<.3 and progress still<0
- then close BUY at actual 120m open and flip SHORT TP1.0 / SL0.7 for remaining original 6h horizon
- otherwise keep original BUY parent TP2 / SL.7 / 6h
Research only. No further threshold tuning here.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TP=2.;SL=.7;HOLD=360;FLIP=(1.0,.7)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def initial(c):return c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0 and c['s20_15']<0

def confirmed(c):return c['mfe']<.3 and c['progress']<0

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,TP,SL,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p};r['label']=a69.label(r)
  c60=a69.checkpoint(rows,r,e7,e20,60);c120=a69.checkpoint(rows,r,e7,e20,120)
  if c60 is None or c120 is None:continue
  r['signal']=initial(c60) and confirmed(c120)
  r['confirmed']=r['signal']
  r['new']=a611.action(rows,r,120,'FLIP',FLIP) if r['signal'] else t['net_usd']
  r['base']=t['net_usd'];rec.append(r)
 base=[r['base'] for r in rec];new=[r['new'] for r in rec]
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'n':len(q),'base':rnd(sum(r['base'] for r in q),3),'new':rnd(sum(r['new'] for r in q),3),'delta':rnd(sum(r['new']-r['base'] for r in q),3),'signals':sum(r['signal'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y];years[str(y)]={'n':len(q),'signals':sum(r['signal'] for r in q),'base':econ([r['base'] for r in q]),'new':econ([r['new'] for r in q]),'delta':rnd(sum(r['new']-r['base'] for r in q),3)}
 sig=[r for r in rec if r['signal']]
 trans={'actions':len(sig),'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in sig),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in sig),'loss_to_loss':sum(r['base']<=0 and r['new']<=0 for r in sig),'win_to_win':sum(r['base']>0 and r['new']>0 for r in sig)}
 loo=[]
 for z in sig:
  p=[(r['base'] if r is z else r['new']) for r in rec];loo.append(sum(p))
 stress=[]
 for pct in (0,.02,.05,.10,.15):
  extra=500*pct/100
  p=[r['new']-(extra if r['signal'] else 0) for r in rec];stress.append({'extra_pct_on_action':pct,'extra_usd_action':rnd(extra,3),'stats':econ(p)})
 out={'status':'FRIDAY15_A612_WRONGWAY_ROBUSTNESS','rule':'all 138 enter; initial60 failure + persistent no+.3/negative at120; flip SHORT TP1.0 SL0.7 remaining horizon',
  'base':econ(base),'new':econ(new),'delta':rnd(sum(new)-sum(base),3),'transitions':trans,
  'signal_labels':{lab:sum(r['label']==lab for r in sig) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')},
  'blocks':blocks,'positive_delta_blocks':sum(b['delta']>0 for b in blocks),'years':years,
  'loo_min_pnl':rnd(min(loo),3),'loo_max_pnl':rnd(max(loo),3),'stress':stress}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
