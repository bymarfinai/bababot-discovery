"""Saturday18 A7.13b — strict-causal repair of wrong-way separability.

Important repair versus legacy helper state():
- Decision after completed checkpoint occurs at next 5m OPEN j.
- Price progress may use that actual decision open.
- EMA7/EMA20 state MUST use only the last completed bar j-1.
- EMA slopes end at j-1, never at j.

No trade management changes here. Classification only.
"""
import json, statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6; SL=1.2; HOLD=1080
CHECKPOINTS=(15,30,60)

def pct(a,b): return 100.0*(a-b)/b if b else 0.0

def causal_state(rows,i,cp,e7,e20):
    nb=cp//5
    j=i+nb
    if j>=len(rows) or j-1<i: return None
    # All observed bars i..j-1 must be contiguous and the parent must still be open.
    e=rows[i][1]; tp=e*(1+TP/100.0); sl=e*(1-SL/100.0)
    for k in range(i,j):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:return None
        x=rows[k]
        if x[2]>=tp or x[3]<=sl:return None
    if rows[j][0]!=rows[i][0]+(j-i)*TF:return None
    obs=rows[i:j]
    dec=rows[j][1]  # actual next 5m open, known at decision time
    hi=max(x[2] for x in obs); lo=min(x[3] for x in obs)
    tbr=[(x[9]/x[6] if x[6] else 0.5) for x in obs]
    last=j-1; p3=max(i,last-3)
    return {
      'decision_i':j,
      'progress':100*(dec-e)/e,
      'mfe':100*(hi-e)/e,'mae':100*(e-lo)/e,
      'taker':statistics.mean(tbr)-0.5,
      'd7':pct(dec,e7[last]),'d20':pct(dec,e20[last]),
      's7_3':pct(e7[last],e7[p3]),'s20_3':pct(e20[last],e20[p3]),
      'above7':dec>e7[last],'above20':dec>e20[last],
    }

RULES=(
 ('R15_PROGRESS_FLOW',15,lambda s:s['progress']<=-0.05 and s['taker']<=-0.03),
 ('R15_PROGRESS_EMA20',15,lambda s:s['progress']<=-0.05 and s['d20']<0),
 ('R15_FLOW_EMA20',15,lambda s:s['taker']<=-0.05 and s['d20']<0),
 ('R30_PROGRESS_FLOW',30,lambda s:s['progress']<=-0.05 and s['taker']<=-0.02),
 ('R30_PROGRESS_EMA20',30,lambda s:s['progress']<=-0.05 and s['d20']<0),
 ('R60_PROGRESS_FLOW',60,lambda s:s['progress']<=-0.10 and s['taker']<0),
 ('R60_PROGRESS_EMA20',60,lambda s:s['progress']<=-0.10 and s['d20']<0),
 ('R60_PROGRESS_EMA20_SLOPE',60,lambda s:s['progress']<=-0.10 and s['d20']<0 and s['s20_3']<0),
)

def build():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; tsmap={x[0]:x for x in rows}
    e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20); funding,_,miss=load_funding(); rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
        i=im[x[0]]; t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,_,_=a74.funding_adjust(rows,t,funding,tsmap); p=a712.path_stats(rows,i)
        tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN'
        rec.append({'i':i,'ts':x[0],'base':base,'tax':tax,'states':{cp:causal_state(rows,i,cp,e7,e20) for cp in CHECKPOINTS}})
    return rows,rec,miss

def score(q,cp,fn):
    eligible=[r for r in q if r['states'].get(cp)]
    sig=[r for r in eligible if fn(r['states'][cp])]
    target=sum(r['tax']=='A1_WRONG_WAY_BEFORE_0.3' for r in eligible)
    hit=sum(r['tax']=='A1_WRONG_WAY_BEFORE_0.3' for r in sig)
    winfp=sum(r['tax']=='WIN' for r in sig)
    otherloss=sum(r['tax']!='WIN' and r['tax']!='A1_WRONG_WAY_BEFORE_0.3' for r in sig)
    return {'eligible':len(eligible),'signals':len(sig),'target_a1':target,'a1_hits':hit,
      'precision_a1_pct':rnd(100*hit/len(sig),2) if sig else None,
      'recall_a1_pct':rnd(100*hit/target,2) if target else None,
      'winner_false_positive':winfp,
      'winner_fp_rate_pct':rnd(100*winfp/max(1,sum(r['tax']=='WIN' for r in eligible)),2),
      'other_loss_signals':otherloss,
      'loss_precision_any_pct':rnd(100*(hit+otherloss)/len(sig),2) if sig else None}

def main():
    rows,rec,miss=build(); d=rec[:83]; v=rec[83:]; out=[]
    for name,cp,fn in RULES:
        out.append({'rule':name,'checkpoint_min':cp,'discovery':score(d,cp,fn),'validation':score(v,cp,fn),'full':score(rec,cp,fn)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A713B_STRICT_CAUSAL','parent_n':len(rec),'funding_missing':miss,'rules':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
