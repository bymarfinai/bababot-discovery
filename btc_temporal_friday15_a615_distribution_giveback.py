"""BTC Friday15 A6.15 — selective distribution giveback rescue.

Frozen event from A6.13/A6.14: actionable +0.5% while BUY still open, then completed 5m close
falls to <= +0.30% within 60m. Broad protection failed because it clipped healthy runners.
A6.14 atlas showed eventual losers have materially more negative taker flow while still trading
above a rising EMA20. Test that mechanism with a compact discovery-only threshold set.
All 138 Fridays still enter. A6.12 wrong-way layer remains baseline. Lock fixed at +0.20%.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a613_giveback_rescue as a613
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
import btc_temporal_saturday18_a74_loss_forensics as a74

RULE=next(r for r in a613.RULES if r[0]=='GB30_60');LOCK=.20
TAKERS=(-.02,-.03,-.04)
CONTEXTS=('FLOW','FLOW_D20','FLOW_D20_SLOPE')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def active(sig,thr,ctx):
 if sig is None:return False
 st=sig['state']
 if st['taker']>thr:return False
 if ctx in ('FLOW_D20','FLOW_D20_SLOPE') and st['d20']<=0:return False
 if ctx=='FLOW_D20_SLOPE' and st['s20']<=0:return False
 return True

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
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
 assert len(rec)==138
 variants=[]
 for thr in TAKERS:
  for ctx in CONTEXTS:
   for r in rec:
    r['active']=not r['wrongway'] and active(r['sig'],thr,ctx)
    r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK) if r['active'] else r['a612']
   def subset(q):
    a=[r for r in q if r['active']]
    return {'stats':econ([r['new'] for r in q]),'baseline':econ([r['a612'] for r in q]),'delta':rnd(sum(r['new']-r['a612'] for r in q),3),
     'actions':len(a),'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in a),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in a),
     'win_clipped':sum(r['base']>0 and 0<r['new']<r['base'] for r in a),'loss_still_loss':sum(r['base']<=0 and r['new']<=0 for r in a)}
   disc=subset(rec[:82]);val=subset(rec[82:]);full=subset(rec)
   score=disc['delta'] if disc['actions']>=3 else -1e9
   variants.append({'taker_thr':thr,'context':ctx,'score_disc':rnd(score,3),'discovery':disc,'validation':val,'full':full})
 chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['loss_to_win'],-z['discovery']['win_to_loss']))
 thr=chosen['taker_thr'];ctx=chosen['context']
 for r in rec:
  r['active']=not r['wrongway'] and active(r['sig'],thr,ctx)
  r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK) if r['active'] else r['a612']
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'actions':sum(r['active'] for r in q)})
 years={}
 for y in sorted(set(ldt(r['ts']).year for r in rec)):
  q=[r for r in rec if ldt(r['ts']).year==y]
  years[str(y)]={'actions':sum(r['active'] for r in q),'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'a612':econ([r['a612'] for r in q]),'new':econ([r['new'] for r in q])}
 acts=[r for r in rec if r['active']]
 out={'status':'FRIDAY15_A615_DISTRIBUTION_GIVEBACK','variants':variants,'chosen':chosen,
  'parent':econ([r['base'] for r in rec]),'a612':econ([r['a612'] for r in rec]),'combined':econ([r['new'] for r in rec]),
  'delta_vs_a612':rnd(sum(r['new']-r['a612'] for r in rec),3),
  'transitions':{'actions':len(acts),'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in acts),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in acts),'win_clipped':sum(r['base']>0 and 0<r['new']<r['base'] for r in acts)},
  'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
