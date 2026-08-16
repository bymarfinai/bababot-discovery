"""BTC Friday15 A6.18 — route confirmed 120m failed-thesis cases by short-stretch state.

Parity-correct baseline from A6.17b:
- every Friday15 BUY enters with TP2/SL0.7/max6h
- frozen failure detector at 60m + confirmation at 120m
- if original BUY already stopped before 120m, any SHORT is a new sequential re-entry
- if BUY still open, SHORT action closes BUY at actual 120m open then opens SHORT TP1/SL0.7

A6.17 atlas suggests SHORT failure is associated with already-deep downside stretch at 120m
(price materially below EMA20 / entry), consistent with chasing exhaustion.
Candidate eligibility thresholds are compact and selected on first 82 Friday occurrences only.
Validation last 56 is untouched for selection. Research only.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

NOTIONAL=500.;FEE_USD=.75;H=120;HOLD=360

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def cut120(rows,r):
 if a617b.exited_before_120(r):return r['base']
 j=r['i']+H//5;px=rows[j][1];return (px-r['entry'])/r['entry']*NOTIONAL-FEE_USD

def no_short(rows,r,fallback):
 if a617b.exited_before_120(r):return r['base']
 return r['base'] if fallback=='HOLD' else cut120(rows,r)

def rules():
 out=[]
 for z in (-.05,-.10,-.15,-.20):out.append((f'D20_GT_{z}',lambda c,z=z:c['d20']>z))
 for z in (-.02,-.05,-.08):out.append((f'D7_GT_{z}',lambda c,z=z:c['d7']>z))
 for z in (-.30,-.40,-.50,-.60):out.append((f'PROG_GT_{z}',lambda c,z=z:c['progress']>z))
 out += [
  ('D20_GT_10_AND_PROG_GT_50',lambda c:c['d20']>-.10 and c['progress']>-.50),
  ('D20_GT_15_AND_PROG_GT_60',lambda c:c['d20']>-.15 and c['progress']>-.60),
  ('NEAR_EMA_BOTH',lambda c:c['d7']>-.05 and c['d20']>-.15),
  ('EMA20_NOT_FALLING',lambda c:c['s20_15']>=0),
 ]
 return out

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  c60=a69.checkpoint(rows,r,e7,e20,60);c120=a69.checkpoint(rows,r,e7,e20,120);r['c120']=c120
  r['confirmed']=bool(c60 and c120 and a612.initial(c60) and a612.confirmed(c120));r['stopped_before']=r['confirmed'] and a617b.exited_before_120(r)
  r['all_short']=a617b.repaired(rows,r,True);rec.append(r)
 assert len(rec)==138
 base=[r['base'] for r in rec];allshort=[r['all_short'] for r in rec]
 variants=[]
 for name,fn in rules():
  for fallback in ('HOLD','CUT'):
   for r in rec:
    if not r['confirmed']:r['new']=r['base'];r['take_short']=False
    else:
     r['take_short']=bool(fn(r['c120']));r['new']=r['all_short'] if r['take_short'] else no_short(rows,r,fallback)
   def sub(q):
    sig=[r for r in q if r['confirmed']];sh=[r for r in q if r['confirmed'] and r['take_short']]
    return {'stats':econ([r['new'] for r in q]),'parent':econ([r['base'] for r in q]),'all_short':econ([r['all_short'] for r in q]),
      'delta_parent':rnd(sum(r['new']-r['base'] for r in q),3),'delta_all_short':rnd(sum(r['new']-r['all_short'] for r in q),3),
      'confirmed':len(sig),'short_actions':len(sh),'short_after_prior_stop':sum(r['stopped_before'] for r in sh),'short_while_open':sum(not r['stopped_before'] for r in sh),
      'base_loss_to_positive':sum(r['base']<=0 and r['new']>0 for r in sig),'base_win_to_loss':sum(r['base']>0 and r['new']<=0 for r in sig)}
   ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
   score=ds['stats']['pnl'] if ds['short_actions']>=3 else -1e9
   variants.append({'rule':name,'fallback':fallback,'score_disc':rnd(score,3),'discovery':ds,'validation':vs,'full':fs})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['delta_parent'],z['discovery']['stats']['pf'] or 0))
 name=chosen['rule'];fallback=chosen['fallback'];fn=dict(rules())[name]
 for r in rec:
  if not r['confirmed']:r['chosen']=r['base'];r['chosen_short']=False
  else:
   r['chosen_short']=bool(fn(r['c120']));r['chosen']=r['all_short'] if r['chosen_short'] else no_short(rows,r,fallback)
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'parent':rnd(sum(r['base'] for r in q),3),'all_short':rnd(sum(r['all_short'] for r in q),3),'router':rnd(sum(r['chosen'] for r in q),3),'delta_parent':rnd(sum(r['chosen']-r['base'] for r in q),3),'actions':sum(r['chosen_short'] for r in q)})
 out={'status':'FRIDAY15_A618_WRONGWAY_STRETCH_ROUTER','parent':econ(base),'all_short_repaired':econ(allshort),'variants':sorted(variants,key=lambda z:z['score_disc'],reverse=True),'chosen':chosen,
  'router_full':econ([r['chosen'] for r in rec]),'router_disc':econ([r['chosen'] for r in rec[:82]]),'router_val':econ([r['chosen'] for r in rec[82:]]),
  'blocks':blocks,'positive_router_vs_parent_blocks':sum(b['delta_parent']>0 for b in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
