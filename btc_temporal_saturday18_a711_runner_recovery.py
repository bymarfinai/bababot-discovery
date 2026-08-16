"""Saturday18 A7.11 — C1 fast-giveback lock + causal runner recovery.

Parent: BUY Saturday18 TP2.6 / SL1.2 / 18h.
C1: after +0.5 hinge, completed 5m gives back to <=+0.4 within 5m.
Base protection: +0.30% protective stop.
Recovery: while stop has not fired, if price reaches a recovery threshold first, cancel
protection and restore original TP2.6 / SL1.2 runner. If both stop and recovery threshold
are touched in the same 5m candle, stop wins (adverse precedence).

Recovery thresholds are ranked on discovery only. Historical funding is charged until
actual simulated exit. This is research only; no live code changes.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a76_hinge_statistics as a76
import btc_temporal_saturday18_a77_giveback_statistics as a77
from btc_temporal_a34_5m_events import load,ldt,rnd,TF,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade,FEE_PCT,NOTIONAL,max_dd,loss_streak
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding
TP=2.6;SL=1.2;HOLD=1080;LOCK=0.30
RECOVERIES=(0.45,0.50,0.55,0.60,0.70)

def block_id(ts):return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))
def funding_pnl(funding,tsmap,entry_ts,exit_ts,qty,e):
 z=0.0
 for ft,rate in funding:
  if ft<=entry_ts:continue
  if ft>exit_ts:break
  px=(tsmap.get(ft) or [None,e])[1];z+=-qty*px*rate
 return z
def trigger(rows,i,e7,e20):
 h=a76.first_hinge(rows,i,0.5,e7,e20)
 if not h:return None
 g=a77.first_giveback(rows,i,h,0.4,e7,e20)
 if not g or g['since']>5:return None
 return h['j']+int(g['since']//5)
def parent(rows,i,funding,tsmap,e7,e20):
 t=trade(rows,i,TP,SL,HOLD)
 if not t:return None
 return {'ts':t['ts'],'i':i,'entry':t['entry'],'base':a74.funding_adjust(rows,t,funding,tsmap)[0],'tr':trigger(rows,i,e7,e20)}
def managed(rows,r,recov,funding,tsmap):
 if r['tr'] is None:return r['base'],False,'NO_TRIGGER',False
 e=r['entry'];j=r['tr']+1;end=min(len(rows),r['i']+HOLD//5);lock=e*(1+LOCK/100);recover=e*(1+recov/100);tp=e*(1+TP/100);sl=e*(1-SL/100)
 if j>=end:return r['base'],False,'TOO_LATE',False
 # At next open, if stop level already violated, exit actual open.
 if rows[j][1]<=lock:
  ex=rows[j][1];exi=j;reason='MARKET_BELOW_LOCK';recovered=False
 else:
  ex=None;exi=None;reason=None;recovered=False;k=j
  # Protection arbitration: stop vs recovery touch. Stop wins same-bar ambiguity.
  for k in range(j,end):
   x=rows[k]
   if x[0]!=rows[j][0]+(k-j)*TF:return r['base'],False,'DATA_GAP',False
   hit_lock=x[3]<=lock;hit_rec=x[2]>=recover
   if hit_lock:
    ex=lock;exi=k;reason='LOCK';break
   if hit_rec:
    recovered=True;reason='RECOVER';break
  if recovered:
   # Protection canceled. Continue original parent geometry causally from recovery bar.
   # If original SL/TP occur in same recovery bar, adverse SL first.
   for m in range(k,end):
    x=rows[m]
    ht=x[2]>=tp;hs=x[3]<=sl
    if ht and hs:ex=sl;exi=m;reason='RECOVER_AMB_SL';break
    if hs:ex=sl;exi=m;reason='RECOVER_SL';break
    if ht:ex=tp;exi=m;reason='RECOVER_TP';break
   if ex is None:
    exi=end-1;ex=rows[exi][4];reason='RECOVER_TIMEOUT'
  elif ex is None:
   exi=end-1;ex=rows[exi][4];reason='TIMEOUT'
 gross=100*(ex-e)/e;raw=NOTIONAL*(gross-FEE_PCT)/100;fp=funding_pnl(funding,tsmap,rows[r['i']][0],rows[exi][0],NOTIONAL/e,e)
 return raw+fp,True,reason,recovered
def summarize(vals,key):
 p=[x[key] for x in vals];n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0);blocks=[rnd(sum(x[key] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p),'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}
def evalq(rows,recs,recov,funding,tsmap):
 vals=[];actions=rescued=damaged=clipped=recovers=rec_win=rec_loss=0;reasons={}
 for r in recs:
  z,act,rs,recovered=managed(rows,r,recov,funding,tsmap)
  if act:
   actions+=1;reasons[rs]=reasons.get(rs,0)+1
   if r['base']<=0 and z>0:rescued+=1
   if r['base']>0 and z<=0:damaged+=1
   if r['base']>0 and z>0 and z<r['base']:clipped+=1
   if recovered:
    recovers+=1
    if r['base']>0:rec_win+=1
    else:rec_loss+=1
  vals.append({'ts':r['ts'],'base':r['base'],'final':z})
 b=summarize(vals,'base');z=summarize(vals,'final');z.update({'delta':rnd(z['pnl']-b['pnl'],3),'actions':actions,'rescued':rescued,'damaged':damaged,'clipped_winners':clipped,'recoveries':recovers,'recovered_original_winners':rec_win,'recovered_original_losers':rec_loss,'reasons':reasons});return z
def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,miss=load_funding();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);idx=[]
 for x in rows:
  if EVAL_START<=x[0]<EVAL_END:
   d=ldt(x[0])
   if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
 recs=[parent(rows,i,funding,tsmap,e7,e20) for i in idx];recs=[r for r in recs if r];d=recs[:83];v=recs[83:]
 out=[]
 for rr in RECOVERIES:
  ds=evalq(rows,d,rr,funding,tsmap);out.append({'recovery':rr,'discovery':ds})
 out.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['pf'] or 0,-x['discovery']['mdd']),reverse=True)
 for x in out:
  x['validation']=evalq(rows,v,x['recovery'],funding,tsmap);x['full']=evalq(rows,recs,x['recovery'],funding,tsmap)
 print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A711_RUNNER_RECOVERY','parent':summarize([{'ts':r['ts'],'base':r['base']} for r in recs],'base'),'lock':LOCK,'recovery_thresholds':RECOVERIES,'ranked_discovery_only':out,'funding_missing':miss},separators=(',',':')),flush=True)
if __name__=='__main__':main()
