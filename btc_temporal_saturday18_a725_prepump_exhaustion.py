"""Saturday18 A7.25 — strict-causal pre-pump / local-exhaustion classifier.

A7.24 falsified the falling-knife pre-entry hypothesis: A1 wrong-way losses were, on median,
entered AFTER positive pre-1h/pre-4h movement, above/rising EMA20, and closer to the prior-hour high.

This file freezes that directional insight and tests only a small set of interpretable exhaustion
confluences. Classification only; no trade is skipped here.
"""
import json
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import rnd

A1='A1_WRONG_WAY_BEFORE_0.3'; WIN='WIN'

RULES=(
 ('PUMP_TREND',lambda x:x['pre1']>0 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0),
 ('PUMP_NEAR_PH',lambda x:x['pre1']>0 and x['pre4']>0 and x['to_ph']<=.10),
 ('EMA_NEAR_PH',lambda x:x['pre1']>0 and x['d20']>0 and x['s20_60']>0 and x['to_ph']<=.10),
 ('PUMP_TREND_NEAR_PH',lambda x:x['pre1']>0 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0 and x['to_ph']<=.10),
 ('HIGH_DAY_PUMP_NEAR_PH',lambda x:x['day_pos']>=.55 and x['pre1']>0 and x['pre4']>0 and x['to_ph']<=.12),
 ('PUMP_005_TREND',lambda x:x['pre1']>=.05 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0),
)

def score(q,fn):
    z=[r for r in q if r.get('prex')]
    sig=[r for r in z if fn(r['prex'])]
    a1=sum(r['tax']==A1 for r in z); wins=sum(r['tax']==WIN for r in z)
    ah=sum(r['tax']==A1 for r in sig); wf=sum(r['tax']==WIN for r in sig)
    other=sum(r['tax'] not in (A1,WIN) for r in sig)
    return {
      'signals':len(sig),'a1_hits':ah,
      'precision_a1_pct':rnd(100*ah/len(sig),2) if sig else None,
      'recall_a1_pct':rnd(100*ah/a1,2) if a1 else None,
      'winner_false_positive':wf,
      'winner_fp_rate_pct':rnd(100*wf/wins,2) if wins else None,
      'other_loss_signals':other,
      'loss_precision_any_pct':rnd(100*(ah+other)/len(sig),2) if sig else None,
      'signal_dates':[r['ts'] for r in sig],
    }

def main():
    rows,rec,miss=a713b.build(); e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20)
    for r in rec:r['prex']=a724.pre_features(rows,r['i'],e7,e20)
    d=rec[:83];v=rec[83:]
    out=[]
    for name,fn in RULES:
        out.append({'rule':name,'discovery':score(d,fn),'validation':score(v,fn),'full':score(rec,fn)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A725_PREPUMP_EXHAUSTION','parent_n':len(rec),'funding_missing':miss,'rules':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
