"""A7.8 statistical classifier only; no trade management changes.
Rank simple fast-giveback conditions using discovery only, then report untouched validation.
Parent: Saturday18 BUY TP2.6 / SL1.2 / 18h with historical funding labels.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a76_hinge_statistics as a76
import btc_temporal_saturday18_a77_giveback_statistics as a77
from btc_temporal_a34_5m_events import load,ldt,rnd,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding
TP=2.6;SL=1.2;HOLD=1080;SPEEDS=(5,10,15,20,30,45,60);LEVELS=(0.4,0.3);CONDS=('ANY','D20_POS','S20_POS','D20_S20_POS')
def build():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,_=load_funding();idx=[]
 for x in rows:
  if EVAL_START<=x[0]<EVAL_END:
   d=ldt(x[0])
   if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
 rec=[]
 for i in idx:
  t=trade(rows,i,TP,SL,HOLD)
  if t is None:continue
  base=a74.funding_adjust(rows,t,funding,tsmap)[0];h=a76.first_hinge(rows,i,0.5,e7,e20);gb={}
  if h:
   for lvl in LEVELS:gb[lvl]=a77.first_giveback(rows,i,h,lvl,e7,e20)
  rec.append({'loss':base<=0,'h':h,'gb':gb})
 return rec
def passes(g,speed,cond):
 if not g or g['since']>speed:return False
 if cond=='ANY':return True
 if cond=='D20_POS':return g['d20']>0
 if cond=='S20_POS':return g['s20']>0
 if cond=='D20_S20_POS':return g['d20']>0 and g['s20']>0
 return False
def stats(q,lvl,speed,cond):
 z=[r for r in q if r['h'] and passes(r['gb'].get(lvl),speed,cond)];los=sum(r['loss'] for r in z);win=len(z)-los
 all_los=sum(bool(r['loss'] and r['h']) for r in q)
 return {'n':len(z),'losers':los,'winners':win,'loser_precision':rnd(100*los/len(z),2) if z else None,'hinge_loser_recall':rnd(100*los/all_los,2) if all_los else None}
def main():
 rec=build();d=rec[:83];v=rec[83:];c=[]
 for lvl in LEVELS:
  for sp in SPEEDS:
   for cond in CONDS:
    ds=stats(d,lvl,sp,cond)
    if ds['n']>=5:c.append({'level':lvl,'speed':sp,'cond':cond,'discovery':ds})
 c.sort(key=lambda x:(x['discovery']['loser_precision'] or 0,x['discovery']['losers'],x['discovery']['n']),reverse=True)
 out=[]
 for x in c[:20]:
  y=dict(x);y['validation']=stats(v,y['level'],y['speed'],y['cond']);y['full']=stats(rec,y['level'],y['speed'],y['cond']);out.append(y)
 print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A78_FAST_GIVEBACK_CLASSIFIER','parent':{'n':len(rec),'losses':sum(r['loss'] for r in rec)},'top20_discovery_ranked':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
