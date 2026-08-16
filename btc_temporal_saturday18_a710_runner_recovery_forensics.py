"""Saturday18 A7.10 — runner-recovery forensics after the A7.9 C1 fast-giveback trigger.

Frozen parent stays BUY TP2.6 / SL1.2 / 18h. We do NOT change trades here.
C1 trigger is fixed: after first reaching +0.5%, completed 5m close gives back to <=+0.4%
within 5 minutes. A7.9 showed lock +0.30% rescues many losers but clips winners.

This atlas starts at the NEXT 5m open after C1 and measures which happens first:
- recovery back to +0.5 / +0.6 / +0.8%
- deterioration to +0.3 / +0.2 / 0.0%
It also reports decision-open state and short grace-window closes. This tells us whether a
causal runner-recovery rule has room to act before protection would be consumed.
"""
import json,statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a76_hinge_statistics as a76
import btc_temporal_saturday18_a77_giveback_statistics as a77
from btc_temporal_a34_5m_events import load,ldt,rnd,TF,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding
TP=2.6;SL=1.2;HOLD=1080
UP=(0.5,0.6,0.8);DOWN=(0.3,0.2,0.0);GRACE=(5,10,15,30,60)
def med(x):return rnd(statistics.median(x),4) if x else None
def pct(a,b):return 100*(a-b)/b if b else 0.0
def trigger(rows,i,e7,e20):
 h=a76.first_hinge(rows,i,0.5,e7,e20)
 if not h:return None
 g=a77.first_giveback(rows,i,h,0.4,e7,e20)
 if not g or g['since']>5:return None
 j=h['j']+int(g['since']//5)
 return {'j':j,'h':h,'g':g}
def future(rows,i,tr,e7,e20):
 e=rows[i][1];start=tr['j']+1;end=min(len(rows),i+HOLD//5)
 if start>=end:return None
 op=rows[start][1]; z={'decision_progress':100*(op-e)/e,'decision_d7':pct(op,e7[start]),'decision_d20':pct(op,e20[start]),'open_below_03':op<=e*1.003}
 # first future touch times from decision open; same-bar adverse DOWN gets precedence when comparing later.
 for u in UP:
  tm=None
  for k in range(start,end):
   if rows[k][2]>=e*(1+u/100):tm=(k-start+1)*5;break
  z[f'up_{u}']=tm
 for d in DOWN:
  tm=None
  px=e*(1+d/100)
  for k in range(start,end):
   if rows[k][3]<=px:tm=(k-start+1)*5;break
  z[f'down_{d}']=tm
 for g in GRACE:
  k=start+g//5-1
  if k<end:
   x=rows[k];z[f'close_{g}']=100*(x[4]-e)/e;z[f'd7_{g}']=pct(x[4],e7[k]);z[f'd20_{g}']=pct(x[4],e20[k])
 return z
def group(q):
 if not q:return {'n':0}
 out={'n':len(q),'decision_progress_med':med([x['decision_progress'] for x in q]),'decision_d7_med':med([x['decision_d7'] for x in q]),'decision_d20_med':med([x['decision_d20'] for x in q]),'open_below_03_pct':rnd(100*sum(x['open_below_03'] for x in q)/len(q),2)}
 for u in UP:
  a=[x[f'up_{u}'] for x in q if x[f'up_{u}'] is not None];out[f'up_{u}_reach']=len(a);out[f'up_{u}_time_med']=med(a)
 for d in DOWN:
  a=[x[f'down_{d}'] for x in q if x[f'down_{d}'] is not None];out[f'down_{d}_reach']=len(a);out[f'down_{d}_time_med']=med(a)
 for u in UP:
  for d in DOWN:
   key=f'up{u}_before_down{d}';n=0
   for x in q:
    a=x[f'up_{u}'];b=x[f'down_{d}']
    if a is not None and (b is None or a<b):n+=1
   out[key]=n
 for g in GRACE:
  a=[x[f'close_{g}'] for x in q if f'close_{g}' in x];out[f'close_{g}_med']=med(a)
 return out
def pack(q):
 return {'winner':group([r['f'] for r in q if r['win']]),'loser':group([r['f'] for r in q if not r['win']])}
def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,_=load_funding();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);idx=[]
 for x in rows:
  if EVAL_START<=x[0]<EVAL_END:
   d=ldt(x[0])
   if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
 rec=[]
 for i in idx:
  t=trade(rows,i,TP,SL,HOLD)
  if not t:continue
  tr=trigger(rows,i,e7,e20)
  if not tr:continue
  base=a74.funding_adjust(rows,t,funding,tsmap)[0];f=future(rows,i,tr,e7,e20)
  if f:rec.append({'win':base>0,'f':f})
 print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A710_RUNNER_RECOVERY_FORENSICS','triggers':len(rec),'full':pack(rec),'discovery':pack(rec[:20]),'validation':pack(rec[20:])},separators=(',',':')),flush=True)
if __name__=='__main__':main()
