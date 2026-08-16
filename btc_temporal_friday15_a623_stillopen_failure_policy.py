"""BTC Friday15 A6.23 — policy for confirmed failure while original BUY is still open at120m.

Frozen from prior accepted research steps:
- all Friday15 BUY entries, parent TP2/SL0.7/max6h
- failed-thesis detector 60m + 120m
- post-stop sequential SHORT rescue geometry from A6.22: TP1.5/SL0.5
- non-wrongway distribution protection from A6.15

Only study the 120m confirmed-failure subset where the original BUY has NOT exited yet.
Compact policy comparison: HOLD original BUY, CUT at actual 120m open, or current FLIP
(close BUY + SHORT TP1.3/SL0.7). Select by first82 discovery engine PnL only.
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
POSTSTOP_TP=1.5;POSTSTOP_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
POLICIES=('HOLD','CUT','FLIP')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
         'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
         'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def stillopen_action(rows,r,policy):
 if policy=='HOLD':return r['base']
 j=r['i']+H//5;px=rows[j][1]
 long=(px-r['entry'])/r['entry']*NOTIONAL-FEE_USD
 if policy=='CUT':return long
 short=a611.short_leg(rows,j,r['i']+HOLD//5,1.3,.7)
 return long+short

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
  r['stillopen']=r['wrongway'] and not r['prior_stop']
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  rec.append(r)
 assert len(rec)==138
 def engine(r,policy):
  if r['prior_stop']:
   j=r['i']+H//5
   return r['base']+a611.short_leg(rows,j,r['i']+HOLD//5,POSTSTOP_TP,POSTSTOP_SL)
  if r['stillopen']:return stillopen_action(rows,r,policy)
  if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
  return r['base']
 variants=[]
 for policy in POLICIES:
  for r in rec:r['new']=engine(r,policy)
  def sub(q):
   z=[r for r in q if r['stillopen']]
   return {'engine':econ([r['new'] for r in q]),'stillopen':econ([r['new'] for r in z]),
           'stillopen_parent':econ([r['base'] for r in z]),'n':len(z),
           'delta_stillopen':rnd(sum(r['new']-r['base'] for r in z),3),
           'base_win_to_loss':sum(r['base']>0 and r['new']<=0 for r in z),
           'base_loss_to_win':sum(r['base']<=0 and r['new']>0 for r in z)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'policy':policy,'score_disc':ds['engine']['pnl'],'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['stillopen']['pnl'],-z['discovery']['base_win_to_loss']))
 pol=chosen['policy']
 for r in rec:r['chosen']=engine(r,pol)
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'parent':rnd(sum(r['base'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
                 'delta':rnd(sum(r['chosen']-r['base'] for r in q),3),'stillopen':sum(r['stillopen'] for r in q)})
 out={'status':'FRIDAY15_A623_STILLOPEN_FAILURE_POLICY','selection':'first82 discovery engine PnL only',
      'frozen':{'poststop_short':'TP1.5 SL0.5','distribution':'A6.15','stillopen_flip_reference':'TP1.3 SL0.7'},
      'variants':variants,'chosen':chosen,'chosen_full':econ([r['chosen'] for r in rec]),
      'chosen_discovery':econ([r['chosen'] for r in rec[:82]]),'chosen_validation':econ([r['chosen'] for r in rec[82:]]),
      'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
