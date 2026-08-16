"""Saturday18 A7.16 — strict-causal lockable runner-failure atlas.

Goal: find giveback failure while the BUY still has enough gross profit to exit net-positive
under the 0.15% round-trip fee assumption.

We inspect fixed checkpoints 240m, 300m, 360m. Signal decision is next 5m open; EMA ends
at the last completed 5m bar. Parent must still be open.

Rules are deliberately compact and fixed, not a threshold sweep.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080
CPS=(240,300,360)
RULES=(
 ('LOCK05_EMA',lambda s:s['mfe']>=0.5 and 0.20<=s['progress']<=0.40 and s['d20']<0 and s['s20_3']<0),
 ('LOCK05_FLOW',lambda s:s['mfe']>=0.5 and 0.20<=s['progress']<=0.40 and s['taker']<0),
 ('LOCK05_DD_EMA',lambda s:s['mfe']>=0.5 and 0.20<=s['progress']<=0.45 and (s['mfe']-s['progress'])>=0.25 and s['d20']<0),
 ('LOCK08_EMA',lambda s:s['mfe']>=0.8 and 0.20<=s['progress']<=0.50 and s['d20']<0 and s['s20_3']<0),
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
        rec.append({'i':i,'ts':x[0],'base':base,'tax':tax,'states':{cp:a713b.causal_state(rows,i,cp,e7,e20) for cp in CPS}})
    return rec,miss

def score(q,cp,fn):
    eligible=[r for r in q if r['states'].get(cp)]
    sig=[r for r in eligible if fn(r['states'][cp])]
    losses=[r for r in eligible if r['tax']!='WIN'];cd=[r for r in eligible if r['tax'] in ('C_GIVEBACK_0.5_TO_0.8','D_DEEP_GIVEBACK_GE_0.8')]
    hit=sum(r['tax']!='WIN' for r in sig); hitcd=sum(r['tax'] in ('C_GIVEBACK_0.5_TO_0.8','D_DEEP_GIVEBACK_GE_0.8') for r in sig); fp=sum(r['tax']=='WIN' for r in sig)
    progresses=[r['states'][cp]['progress'] for r in sig]
    return {'eligible':len(eligible),'signals':len(sig),'eventual_losses':len(losses),'cd_losses':len(cd),
      'loss_hits':hit,'loss_precision_pct':rnd(100*hit/len(sig),2) if sig else None,
      'cd_hits':hitcd,'cd_precision_pct':rnd(100*hitcd/len(sig),2) if sig else None,
      'winner_false_positive':fp,'winner_fp_rate_pct':rnd(100*fp/max(1,sum(r['tax']=='WIN' for r in eligible)),2),
      'signal_progress_avg':rnd(sum(progresses)/len(progresses),4) if progresses else None,
      'signal_progress_min':rnd(min(progresses),4) if progresses else None}

def main():
    rec,miss=build();d=rec[:83];v=rec[83:];out=[]
    for cp in CPS:
      for name,fn in RULES:
        out.append({'checkpoint_min':cp,'rule':name,'discovery':score(d,cp,fn),'validation':score(v,cp,fn),'full':score(rec,cp,fn)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A716_LOCKABLE_RUNNER_FAILURE','parent_n':len(rec),'funding_missing':miss,'rules':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
