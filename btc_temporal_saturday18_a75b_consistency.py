"""A7.5b — verify A7.3/A7.4/A7.5 parent funding parity trade by trade."""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a75_early_failure as a75
from btc_temporal_a34_5m_events import load,ldt,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding,eval_cfg

TP=2.6;SL=1.2;HOLD=1080

def main():
 rows=load(); im={x[0]:i for i,x in enumerate(rows)}; tsmap={x[0]:x for x in rows}; idx=[]
 for x in rows:
  if EVAL_START<=x[0]<EVAL_END:
   d=ldt(x[0])
   if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
 funding,_,_=load_funding()
 cfg=eval_cfg(rows,idx,funding,TP,SL,0.0)
 a74vals=[];a75vals=[];raw=[];diff=[]
 for i in idx:
  t=trade(rows,i,TP,SL,HOLD); raw.append(t['net_usd'])
  z74=a74.funding_adjust(rows,t,funding,tsmap)[0]
  z75=a75.parent_trade(rows,i,funding,tsmap)['pnl']
  a74vals.append(z74);a75vals.append(z75)
  if abs(z74-z75)>1e-9:diff.append({'ts':t['ts'],'a74':z74,'a75':z75,'d':z75-z74})
 print('RESULT_JSON',json.dumps({'eval_cfg':cfg,'raw_sum':sum(raw),'a74_sum':sum(a74vals),'a75_sum':sum(a75vals),'diff_count':len(diff),'diff':diff[:10]},separators=(',',':')),flush=True)
if __name__=='__main__':main()
