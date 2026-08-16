"""BTC Friday15 A6.20 — parity-correct combined high-coverage engine.

Combine two disjoint management layers without changing any original Friday entry:
A) parity-correct wrong-way sequential SHORT at 120m, detector frozen from A6.12.
   - if original BUY already exited, preserve realized parent PnL and add new SHORT
   - if still open, close at actual 120m open and add SHORT
   - canonical TP1.3/SL0.7 selected by first82 discovery PnL in A6.19
   - TP1.1/SL0.7 retained as explicit WR-first alternate, NOT re-selected on validation
B) frozen A6.15 distribution giveback on NON-wrongway trades only:
   +0.5% hinge while BUY still open -> within60m completed close <=+0.3%
   -> taker<=-0.04 and close above EMA20 -> +0.20% protection, TP2 stays alive.

All 138 original Friday15 BUY occurrences remain. Research only; live untouched.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a615_distribution_giveback as a615
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

H=120;HOLD=360;NOTIONAL=500.;FEE_USD=.75
RULE=next(r for r in a613.RULES if r[0]=='GB30_60');LOCK=.20;TAKER=-.04
TPS=(1.1,1.3)

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def confirmed(rows,r,e7,e20):
 c60=a69.checkpoint(rows,r,e7,e20,60);c120=a69.checkpoint(rows,r,e7,e20,120)
 return bool(c60 and c120 and a612.initial(c60) and a612.confirmed(c120))

def wrongway_action(rows,r,tp):
 if not r['wrongway']:return r['base']
 j=r['i']+H//5;end=r['i']+HOLD//5;short=a611.short_leg(rows,j,end,tp,.7)
 if a617b.exited_before_120(r):return r['base']+short
 px=rows[j][1];long=(px-r['entry'])/r['entry']*NOTIONAL-FEE_USD
 return long+short

def distribution_active(sig):
 if sig is None:return False
 st=sig['state'];return st['taker']<=TAKER and st['d20']>0

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=confirmed(rows,r,e7,e20)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and distribution_active(r['sig'])
  rec.append(r)
 assert len(rec)==138
 variants=[]
 for tp in TPS:
  for r in rec:
   r['ww']=wrongway_action(rows,r,tp)
   if r['wrongway']:r['new']=r['ww']
   elif r['dist_active']:r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK)
   else:r['new']=r['base']
  def sub(q):
   ww=[r for r in q if r['wrongway']];gb=[r for r in q if r['dist_active']]
   return {'stats':econ([r['new'] for r in q]),'parent':econ([r['base'] for r in q]),'delta':rnd(sum(r['new']-r['base'] for r in q),3),
    'wrongway_actions':len(ww),'wrongway_prior_stop':sum(a617b.exited_before_120(r) for r in ww),
    'distribution_actions':len(gb),'total_management_actions':len(ww)+len(gb),
    'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in ww+gb),
    'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in ww+gb),
    'win_clipped_positive':sum(r['base']>0 and 0<r['new']<r['base'] for r in ww+gb)}
  ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
  variants.append({'short_tp':tp,'short_sl':.7,'role':'WR_FIRST_ALTERNATE' if tp==1.1 else 'DISCOVERY_PNL_CANONICAL','discovery':ds,'validation':vs,'full':fs})
 # canonical predetermined from A6.19 discovery-only selection = TP1.3
 canonical=next(v for v in variants if v['short_tp']==1.3)
 for r in rec:
  r['ww']=wrongway_action(rows,r,1.3)
  r['canonical']=r['ww'] if r['wrongway'] else (a613.protect_pnl(rows,r,r['sig'],LOCK) if r['dist_active'] else r['base'])
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'n':len(q),'parent':rnd(sum(r['base'] for r in q),3),'new':rnd(sum(r['canonical'] for r in q),3),'delta':rnd(sum(r['canonical']-r['base'] for r in q),3),'ww':sum(r['wrongway'] for r in q),'gb':sum(r['dist_active'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y];years[str(y)]={'parent':econ([r['base'] for r in q]),'new':econ([r['canonical'] for r in q]),'delta':rnd(sum(r['canonical']-r['base'] for r in q),3),'ww':sum(r['wrongway'] for r in q),'gb':sum(r['dist_active'] for r in q)}
 # intervention cost stress: extra fee/slippage applied once to each additional management event (ww second leg/flip or gb protection exit).
 stress=[];acts=[r for r in rec if r['wrongway'] or r['dist_active']]
 for pct in (0,.02,.05,.10,.15):
  extra=NOTIONAL*pct/100
  p=[r['canonical']-(extra if (r['wrongway'] or r['dist_active']) else 0) for r in rec]
  stress.append({'extra_pct_per_management_action':pct,'extra_usd':rnd(extra,3),'stats':econ(p)})
 out={'status':'FRIDAY15_A620_PARITY_CORRECT_COMBINED','parent':econ([r['base'] for r in rec]),'variants':variants,'canonical':canonical,
  'blocks':blocks,'positive_delta_blocks':sum(b['delta']>0 for b in blocks),'years':years,'stress':stress,
  'rules':{'entry':'all 138 Friday 15:00 WIB BUY','parent':'TP2.0 SL0.7 max6h','wrongway':'60m failure + 120m persistent; parity-correct sequential SHORT; canonical TP1.3 SL0.7','distribution':'+0.5 then <=+0.3 within60m, taker<=-0.04,d20>0, +0.20 lock'}}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
