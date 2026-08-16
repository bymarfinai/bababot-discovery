"""A7.7 pure statistical giveback study; no intervention is executed.
For Saturday18 frozen parent trades that reached +0.5% or +0.8%, measure the first
completed 5m close that gives back to lower profit levels before parent TP/SL.
"""
import json,statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a76_hinge_statistics as a76
from btc_temporal_a34_5m_events import load,ldt,rnd,TF,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding
TP=2.6;SL=1.2;HOLD=1080
LEVELS={0.5:(0.4,0.3,0.2,0.1),0.8:(0.6,0.5,0.4,0.3)}
def med(x):return rnd(statistics.median(x),4) if x else None
def pct(a,b):return 100*(a-b)/b if b else 0.0
def first_giveback(rows,i,hr,level,e7,e20):
 e=rows[i][1];tp=e*(1+TP/100);sl=e*(1-SL/100);end=min(len(rows),i+HOLD//5)
 for j in range(hr['j']+1,end):
  x=rows[j]
  if x[0]!=rows[i][0]+(j-i)*TF:return None
  if x[2]>=tp or x[3]<=sl:return None
  prog=100*(x[4]-e)/e
  if prog<=level:
   p1=max(0,j-1);p3=max(0,j-3)
   return {'since':(j-hr['j'])*5,'progress':prog,'d7':pct(x[4],e7[j]),'d20':pct(x[4],e20[j]),
    's7':pct(e7[j],e7[p3]),'s20':pct(e20[j],e20[p3]),'below7':x[4]<e7[j],'below20':x[4]<e20[j],
    'two_below7':x[4]<e7[j] and rows[p1][4]<e7[p1], 'two_below20':x[4]<e20[j] and rows[p1][4]<e20[p1]}
 return None
def group(q):
 if not q:return {'n':0}
 return {'n':len(q),'since_med':med([x['since'] for x in q]),'progress_med':med([x['progress'] for x in q]),
  'd7_med':med([x['d7'] for x in q]),'d20_med':med([x['d20'] for x in q]),'s7_med':med([x['s7'] for x in q]),'s20_med':med([x['s20'] for x in q]),
  'below7_pct':rnd(100*sum(x['below7'] for x in q)/len(q),2),'below20_pct':rnd(100*sum(x['below20'] for x in q)/len(q),2),
  'two_below7_pct':rnd(100*sum(x['two_below7'] for x in q)/len(q),2),'two_below20_pct':rnd(100*sum(x['two_below20'] for x in q)/len(q),2)}
def atlas(rec,h,lvl):
 q=[r for r in rec if r['gb'][h].get(lvl)]
 return {'triggered':len(q),'winner':group([r['gb'][h][lvl] for r in q if r['base']>0]),'loser':group([r['gb'][h][lvl] for r in q if r['base']<=0])}
def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,miss=load_funding();idx=[]
 for x in rows:
  if EVAL_START<=x[0]<EVAL_END:
   d=ldt(x[0])
   if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
 rec=[]
 for i in idx:
  t=trade(rows,i,TP,SL,HOLD)
  if t is None:continue
  base=a74.funding_adjust(rows,t,funding,tsmap)[0]; hs={h:a76.first_hinge(rows,i,h,e7,e20) for h in LEVELS}; gb={}
  for h,lvls in LEVELS.items():
   gb[h]={}
   if hs[h]:
    for lvl in lvls:gb[h][lvl]=first_giveback(rows,i,hs[h],lvl,e7,e20)
  rec.append({'base':base,'gb':gb})
 def pack(q):return {str(h):{str(lvl):atlas(q,h,lvl) for lvl in lvls} for h,lvls in LEVELS.items()}
 out={'status':'SATURDAY18_A77_GIVEBACK_STATISTICS','parent':{'n':len(rec),'wr':rnd(100*sum(r['base']>0 for r in rec)/len(rec),2),'pnl':rnd(sum(r['base'] for r in rec),3)},'missing_funding':miss,'full':pack(rec),'discovery':pack(rec[:83]),'validation':pack(rec[83:])}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
