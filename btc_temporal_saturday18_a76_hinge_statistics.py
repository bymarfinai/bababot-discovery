"""A7.6 pure statistical forensic study; no trading intervention is executed.
For the frozen Saturday18 BUY parent, compare eventual winners vs losers at the first
completed 5m bar that reaches +0.3%, +0.5%, or +0.8% favorable excursion.
"""
import json,statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load,ldt,rnd,TF,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding
TP=2.6;SL=1.2;HOLD=1080;HINGES=(0.3,0.5,0.8)
def med(x):return rnd(statistics.median(x),4) if x else None
def pct(a,b):return 100*(a-b)/b if b else 0.0
def first_hinge(rows,i,h,e7,e20):
 e=rows[i][1];target=e*(1+h/100);stop=e*(1-SL/100);end=min(len(rows),i+HOLD//5);hi=e;lo=e
 for j in range(i,end):
  x=rows[j]
  if x[0]!=rows[i][0]+(j-i)*TF:return None
  if x[3]<=stop:return None
  hi=max(hi,x[2]);lo=min(lo,x[3])
  if x[2]>=target:
   p3=max(0,j-3); ratios=[]
   for k in range(i,j+1):
    q=rows[k];ratios.append((q[9]/q[6] if q[6] else 0.5)-0.5)
   return {'j':j,'time':(j-i+1)*5,'close_prog':100*(x[4]-e)/e,'mae':100*(e-lo)/e,
    'd7':pct(x[4],e7[j]),'d20':pct(x[4],e20[j]),'s7':pct(e7[j],e7[p3]),'s20':pct(e20[j],e20[p3]),
    'taker':sum(ratios)/len(ratios),'above7':x[4]>e7[j],'above20':x[4]>e20[j]}
 return None
def group(q):
 if not q:return {'n':0}
 return {'n':len(q),'time_med':med([x['time'] for x in q]),'close_prog_med':med([x['close_prog'] for x in q]),
  'mae_med':med([x['mae'] for x in q]),'d7_med':med([x['d7'] for x in q]),'d20_med':med([x['d20'] for x in q]),
  's7_med':med([x['s7'] for x in q]),'s20_med':med([x['s20'] for x in q]),'taker_med':med([x['taker'] for x in q]),
  'above7_pct':rnd(100*sum(x['above7'] for x in q)/len(q),2),'above20_pct':rnd(100*sum(x['above20'] for x in q)/len(q),2)}
def atlas(rec,h):
 q=[r for r in rec if r['h'].get(h)];return {'reached':len(q),'winner':group([r['h'][h] for r in q if r['base']>0]),'loser':group([r['h'][h] for r in q if r['base']<=0])}
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
  base=a74.funding_adjust(rows,t,funding,tsmap)[0]
  rec.append({'base':base,'h':{h:first_hinge(rows,i,h,e7,e20) for h in HINGES}})
 out={'status':'SATURDAY18_A76_HINGE_STATISTICS','parent':{'n':len(rec),'wr':rnd(100*sum(r['base']>0 for r in rec)/len(rec),2),'pnl':rnd(sum(r['base'] for r in rec),3)},'missing_funding':miss,
  'full':{str(h):atlas(rec,h) for h in HINGES},'discovery':{str(h):atlas(rec[:83],h) for h in HINGES},'validation':{str(h):atlas(rec[83:],h) for h in HINGES}}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
