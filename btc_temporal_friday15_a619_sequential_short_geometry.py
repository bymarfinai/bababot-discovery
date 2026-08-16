"""BTC Friday15 A6.19 — parity-correct sequential SHORT geometry after confirmed 120m BUY failure.

A6.17b showed 15/27 confirmed failures had already realized the original BUY SL before 120m.
With a new SHORT TP1.0/SL0.7, a prior -$4.25 BUY loss plus a +$4.25 net short TP only nets ~$0,
so the historical 1.0% target cannot convert those cases into positive Friday outcomes.

Keep detector frozen. Keep SHORT SL fixed 0.7%. Test only compact TP set 1.0/1.1/1.2/1.3%.
If BUY already exited, retain realized parent PnL exactly and add sequential short leg.
If BUY still open, close at actual 120m open and add short leg.
Selection by first-82 discovery PnL only; last-56 validation unopened for selection.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TPS=(1.0,1.1,1.2,1.3);SL=.7;H=120;HOLD=360;NOTIONAL=500.;FEE_USD=.75

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def confirmed(rows,r,e7,e20):
 c60=a69.checkpoint(rows,r,e7,e20,60);c120=a69.checkpoint(rows,r,e7,e20,120)
 return bool(c60 and c120 and a612.initial(c60) and a612.confirmed(c120))

def action(rows,r,tp):
 if not r['confirmed']:return r['base']
 j=r['i']+H//5;end=r['i']+HOLD//5
 short=a611.short_leg(rows,j,end,tp,SL)
 if a617b.exited_before_120(r):return r['base']+short
 px=rows[j][1];long=(px-r['entry'])/r['entry']*NOTIONAL-FEE_USD
 return long+short

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r);r['confirmed']=confirmed(rows,r,e7,e20);r['stopped_before']=r['confirmed'] and a617b.exited_before_120(r);rec.append(r)
 assert len(rec)==138
 variants=[]
 for tp in TPS:
  for r in rec:r['new']=action(rows,r,tp)
  def sub(q):
   sig=[r for r in q if r['confirmed']]
   return {'stats':econ([r['new'] for r in q]),'parent':econ([r['base'] for r in q]),'delta':rnd(sum(r['new']-r['base'] for r in q),3),
    'confirmed':len(sig),'stopped_before':sum(r['stopped_before'] for r in sig),'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in sig),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in sig),'zero_or_loss_after_rescue':sum(r['base']<=0 and r['new']<=0 for r in sig)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'tp':tp,'sl':SL,'score_disc':ds['stats']['pnl'],'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['stats']['wr']))
 tp=chosen['tp']
 for r in rec:r['chosen']=action(rows,r,tp)
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'parent':rnd(sum(r['base'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),'delta':rnd(sum(r['chosen']-r['base'] for r in q),3),'confirmed':sum(r['confirmed'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y];years[str(y)]={'parent':econ([r['base'] for r in q]),'new':econ([r['chosen'] for r in q]),'delta':rnd(sum(r['chosen']-r['base'] for r in q),3),'confirmed':sum(r['confirmed'] for r in q)}
 out={'status':'FRIDAY15_A619_SEQUENTIAL_SHORT_GEOMETRY','variants':variants,'chosen':chosen,
  'parent':econ([r['base'] for r in rec]),'new':econ([r['chosen'] for r in rec]),'blocks':blocks,'positive_delta_blocks':sum(b['delta']>0 for b in blocks),'years':years}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
