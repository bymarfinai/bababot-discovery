"""BTC Friday15 A6.22 — post-stop sequential SHORT rescue geometry.

A6.21 attribution showed the normal non-managed validation subset is profitable, while the
post-stop rescue route has 60% validation WR on the SHORT leg but negative occurrence PnL
because failed rescue creates a double loss. Study only the post-stop leg geometry.

Frozen:
- all 138 Friday15 BUY entries
- parent BUY TP2.0 / SL0.7 / max6h
- A6.20 failed-thesis detector at 60m+120m
- wrong-way flip while BUY still open stays SHORT TP1.3/SL0.7
- A6.15 distribution layer stays frozen

Only if parent BUY already exited before120 and failure remains confirmed, test a compact
sequential SHORT TP/SL geometry set. Select by first82 discovery engine PnL only.
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

H=120;HOLD=360;NOTIONAL=500.;FEE_USD=.75
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
# Compact mechanism-driven set: tighter rescue risk and/or larger reward than frozen 1.3/.7.
GEOMS=((1.3,.4),(1.3,.5),(1.3,.6),(1.3,.7),
       (1.5,.5),(1.5,.6),(1.5,.7),
       (1.7,.5),(1.7,.6),(1.7,.7),
       (2.0,.7))

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
         'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
         'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

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
  rec.append(r)
 assert len(rec)==138
 def engine_pnl(r,tp,sl):
  if r['wrongway']:
   if r['prior_stop']:
    j=r['i']+H//5;end=r['i']+HOLD//5
    return r['base']+a611.short_leg(rows,j,end,tp,sl)
   return a620.wrongway_action(rows,r,1.3)  # frozen while-open flip geometry
  if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
  return r['base']
 variants=[]
 for tp,sl in GEOMS:
  for r in rec:r['new']=engine_pnl(r,tp,sl)
  def sub(q):
   z=[r for r in q if r['prior_stop']]
   return {'engine':econ([r['new'] for r in q]),'poststop':econ([r['new'] for r in z]),
           'poststop_n':len(z),'poststop_positive':sum(r['new']>0 for r in z),
           'poststop_negative':sum(r['new']<=0 for r in z),
           'poststop_delta_vs_parent':rnd(sum(r['new']-r['base'] for r in z),3),
           'double_loss_count':sum(r['new']<r['base'] for r in z)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'tp':tp,'sl':sl,'score_disc':ds['engine']['pnl'],'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['poststop']['pnl'],-z['discovery']['double_loss_count']))
 tp=chosen['tp'];sl=chosen['sl']
 for r in rec:r['chosen']=engine_pnl(r,tp,sl)
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'pnl':rnd(sum(r['chosen'] for r in q),3),'parent':rnd(sum(r['base'] for r in q),3),
                 'delta':rnd(sum(r['chosen']-r['base'] for r in q),3),'poststop':sum(r['prior_stop'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y]
  years[str(y)]={'stats':econ([r['chosen'] for r in q]),'parent':econ([r['base'] for r in q]),
                 'delta':rnd(sum(r['chosen']-r['base'] for r in q),3),'poststop':sum(r['prior_stop'] for r in q)}
 out={'status':'FRIDAY15_A622_POSTSTOP_RESCUE_GEOMETRY','selection':'first82 discovery engine PnL only',
      'frozen_reference':{'poststop_tp':1.3,'poststop_sl':.7},'variants':variants,'chosen':chosen,
      'chosen_full':econ([r['chosen'] for r in rec]),'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),
      'chosen_validation':econ([r['chosen'] for r in rec[82:]]),'blocks':blocks,
      'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
