"""Saturday18 A7.15 — strict-causal runner-failure separability at 6h.

Goal: identify C/D giveback losses only AFTER the BUY thesis has demonstrated favorable
excursion. No management changes in this file.

Decision point: after 360 completed minutes, at next 5m open. All EMA values end at the
last completed 5m bar. Parent must still be open at 360m.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080;CP=360
RULES=(
 ('H05_WEAK_EMA',lambda s:s['mfe']>=0.5 and s['progress']<=0.10 and s['d20']<0 and s['s20_3']<0),
 ('H05_DRAWDOWN_EMA',lambda s:s['mfe']>=0.5 and (s['mfe']-s['progress'])>=0.45 and s['d20']<0),
 ('H08_WEAK_EMA',lambda s:s['mfe']>=0.8 and s['progress']<=0.40 and s['d20']<0),
 ('H08_DRAWDOWN_EMA',lambda s:s['mfe']>=0.8 and (s['mfe']-s['progress'])>=0.50 and s['d20']<0),
 ('H05_WEAK_FLOW',lambda s:s['mfe']>=0.5 and s['progress']<=0.10 and s['taker']<0),
)

def build():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows}
    e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,miss=load_funding();rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
        i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,_,_=a74.funding_adjust(rows,t,funding,tsmap);p=a712.path_stats(rows,i)
        tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN'
        rec.append({'i':i,'ts':x[0],'base':base,'tax':tax,'state':a713b.causal_state(rows,i,CP,e7,e20)})
    return rec,miss

def score(q,fn):
    eligible=[r for r in q if r['state']]
    sig=[r for r in eligible if fn(r['state'])]
    losses=[r for r in eligible if r['tax']!='WIN']
    cd=[r for r in eligible if r['tax'] in ('C_GIVEBACK_0.5_TO_0.8','D_DEEP_GIVEBACK_GE_0.8')]
    hit_loss=sum(r['tax']!='WIN' for r in sig);hit_cd=sum(r['tax'] in ('C_GIVEBACK_0.5_TO_0.8','D_DEEP_GIVEBACK_GE_0.8') for r in sig)
    winfp=sum(r['tax']=='WIN' for r in sig)
    return {'eligible':len(eligible),'signals':len(sig),'eventual_losses':len(losses),'cd_losses':len(cd),
      'loss_hits':hit_loss,'loss_precision_pct':rnd(100*hit_loss/len(sig),2) if sig else None,
      'loss_recall_pct':rnd(100*hit_loss/len(losses),2) if losses else None,
      'cd_hits':hit_cd,'cd_precision_pct':rnd(100*hit_cd/len(sig),2) if sig else None,
      'cd_recall_pct':rnd(100*hit_cd/len(cd),2) if cd else None,
      'winner_false_positive':winfp,'winner_fp_rate_pct':rnd(100*winfp/max(1,sum(r['tax']=='WIN' for r in eligible)),2)}

def main():
    rec,miss=build();d=rec[:83];v=rec[83:];out=[]
    for name,fn in RULES:
        out.append({'rule':name,'discovery':score(d,fn),'validation':score(v,fn),'full':score(rec,fn)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A715_RUNNER_FAILURE_SEPARABILITY','parent_n':len(rec),'checkpoint_min':CP,'funding_missing':miss,'rules':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
