"""Saturday18 A7.21 — strict-causal weak-pop failure classifier.

Sequence starts only after first +0.30% favorable touch while parent is open.
A failure signal is a completed 5m close <= +0.25% before any +0.50% continuation.
We report two predeclared speed windows: <=5m and <=10m after the hinge bar.
No management changes in this file.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080

def event(rows,i):
    e=rows[i][1];end=min(len(rows),i+HOLD//5);h=None
    # first +0.30 hinge before SL
    for k in range(i,end):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:return None
        x=rows[k]
        if x[3]<=e*(1-SL/100):return None
        if x[2]>=e*1.003:h=k;break
    if h is None:return None
    # only completed bars after hinge bar. If +0.50 and <=+0.25 occur same bar, continuation wins
    # to avoid falsely calling failure when bar proves both extremes.
    for k in range(h+1,min(end,h+1+2)): # 5m and 10m bars
        x=rows[k]
        if x[0]!=rows[h][0]+(k-h)*TF:return None
        if x[2]>=e*1.005:return {'hinge_i':h,'signal5':False,'signal10':False,'continued05':True}
        if x[4]<=e*1.0025:
            elapsed=(k-h)*5
            return {'hinge_i':h,'signal5':elapsed<=5,'signal10':elapsed<=10,'continued05':False,'signal_i':k}
    return {'hinge_i':h,'signal5':False,'signal10':False,'continued05':False}

def score(q,key):
    sig=[r for r in q if r['ev'] and r['ev'].get(key)]
    loss=sum(r['base']<=0 for r in sig);b=sum(r['tax']=='B_WEAK_POP_0.3_TO_0.5' for r in sig);win=sum(r['base']>0 for r in sig)
    return {'signals':len(sig),'eventual_loss_hits':loss,'loss_precision_pct':rnd(100*loss/len(sig),2) if sig else None,
      'B_hits':b,'B_precision_pct':rnd(100*b/len(sig),2) if sig else None,'winner_false_positive':win}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,miss=load_funding();recs=[];sats=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if d.weekday()==5 and d.hour==18 and d.minute==0:
            sats.append(x[0]);i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
            if t is None:continue
            base,_,_=a74.funding_adjust(rows,t,funding,tsmap);p=a712.path_stats(rows,i);tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN'
            recs.append({'ts':x[0],'base':base,'tax':tax,'ev':event(rows,i)})
    split=sats[83];parts={'full':recs,'discovery':[r for r in recs if r['ts']<split],'validation':[r for r in recs if r['ts']>=split]}
    out={'status':'SATURDAY18_A721_WEAKPOP_FAILURE_CLASSIFIER','funding_missing':miss,'rules':{}}
    for key in ('signal5','signal10'):
        out['rules'][key]={name:score(q,key) for name,q in parts.items()}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
