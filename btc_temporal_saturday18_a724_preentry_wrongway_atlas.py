"""Saturday18 A7.24 — strict-causal PRE-ENTRY atlas for A1 wrong-way losses.

Frozen reference:
- Saturday 18:00 WIB BUY
- TP 2.6%, SL 1.2%, max hold 18h
- A7.19 is the provisional post-entry management champion, but this file DOES NOT alter it.

Question:
Can the A1_WRONG_WAY_BEFORE_0.3 family be recognized at/just before the 18:00 open,
using only completed pre-entry 5m bars plus the actual 18:00 open price?

This is classification only. No skip/entry filter is promoted here.
EMA values end at i-1; no current-candle close is used.
"""
import json, statistics
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import context, rnd

A1='A1_WRONG_WAY_BEFORE_0.3'
WIN='WIN'


def med(xs):
    return rnd(statistics.median(xs),4) if xs else None

def mean(xs):
    return statistics.mean(xs) if xs else 0.0

def pct(a,b):
    return 100.0*(a-b)/b if b else 0.0

def pre_features(rows,i,e7,e20):
    if i < 288 or i < 12:
        return None
    c=context(rows,i)
    if c is None:
        return None
    # Strict causal indicator anchor: last COMPLETED 5m candle.
    last=i-1
    p3=max(0,last-3); p12=max(0,last-12)
    e=rows[i][1]  # actual 18:00 open, known when deciding whether to enter
    pre30=rows[i-6:i]; pre60=rows[i-12:i]; pre120=rows[i-24:i]; prev4h=rows[i-48:i-12]
    if len(pre30)<6 or len(pre60)<12 or len(pre120)<24 or not prev4h:
        return None
    def taker(q):
        vals=[(x[9]/x[6] if x[6] else .5) for x in q]
        return mean(vals)-.5
    def upfrac(q):
        return sum(x[4]>x[1] for x in q)/len(q)
    r1=mean([x[2]-x[3] for x in pre60])
    rprev=mean([x[2]-x[3] for x in prev4h])
    q1=mean([x[6] for x in pre60])
    qprev=mean([x[6] for x in prev4h])
    ph=max(x[2] for x in pre60); pl=min(x[3] for x in pre60)
    return {
      'pre1':c['pre1'],'pre4':c['pre4'],'pre24':c['pre24'],
      'day_pos':c['day_pos'],
      'vs_dopen':100*(e-c['daily_open'])/e,
      'to_hod':100*(c['hod']-e)/e,'to_lod':100*(e-c['lod'])/e,
      'to_ph':100*(ph-e)/e,'to_pl':100*(e-pl)/e,
      'd7':pct(e,e7[last]),'d20':pct(e,e20[last]),
      's7_15':pct(e7[last],e7[p3]),'s20_15':pct(e20[last],e20[p3]),
      's7_60':pct(e7[last],e7[p12]),'s20_60':pct(e20[last],e20[p12]),
      'taker30':taker(pre30),'taker60':taker(pre60),'taker120':taker(pre120),
      'upfrac60':upfrac(pre60),
      'range_ratio_1h_vs_prev':r1/rprev if rprev else 1.0,
      'vol_ratio_1h_vs_prev':q1/qprev if qprev else 1.0,
      'below7':e<e7[last],'below20':e<e20[last],
    }

FEATURES=(
 'pre1','pre4','pre24','day_pos','vs_dopen','to_hod','to_lod','to_ph','to_pl',
 'd7','d20','s7_15','s20_15','s7_60','s20_60','taker30','taker60','taker120',
 'upfrac60','range_ratio_1h_vs_prev','vol_ratio_1h_vs_prev'
)

# Compact, interpretable hypotheses. Thresholds are deliberately coarse and predeclared;
# this is not a large parameter sweep.
RULES=(
 ('FALLING_KNIFE_CORE',lambda x:x['pre1']<=-.20 and x['below20'] and x['s20_60']<0),
 ('FALLING_KNIFE_FLOW',lambda x:x['pre1']<=-.20 and x['below20'] and x['taker60']<0),
 ('BEAR_STACK',lambda x:x['pre1']<0 and x['pre4']<0 and x['below20'] and x['s20_60']<0),
 ('LOW_DAY_BEAR',lambda x:x['day_pos']<=.35 and x['pre1']<0 and x['below20']),
 ('EMA_FLOW_BEAR',lambda x:x['below20'] and x['s20_60']<0 and x['taker60']<0),
 ('EXPANDING_SELL',lambda x:x['pre1']<=-.20 and x['taker60']<0 and x['range_ratio_1h_vs_prev']>=1.15),
 ('DEEP_BEAR_CONFLUENCE',lambda x:x['pre1']<=-.20 and x['pre4']<0 and x['below20'] and x['s20_60']<0 and x['taker60']<0),
)


def atlas(q):
    out={}
    for lab in (A1,WIN):
        z=[r['prex'] for r in q if r['tax']==lab and r.get('prex')]
        d={'n':len(z)}
        for f in FEATURES:
            d[f+'_med']=med([x[f] for x in z])
        d['below7_pct']=rnd(100*sum(x['below7'] for x in z)/len(z),2) if z else None
        d['below20_pct']=rnd(100*sum(x['below20'] for x in z)/len(z),2) if z else None
        out[lab]=d
    return out


def score(q,fn):
    z=[r for r in q if r.get('prex')]
    sig=[r for r in z if fn(r['prex'])]
    a1=sum(r['tax']==A1 for r in z); wins=sum(r['tax']==WIN for r in z)
    ah=sum(r['tax']==A1 for r in sig); wf=sum(r['tax']==WIN for r in sig)
    other=sum(r['tax'] not in (A1,WIN) for r in sig)
    return {
      'eligible':len(z),'signals':len(sig),'target_a1':a1,'a1_hits':ah,
      'precision_a1_pct':rnd(100*ah/len(sig),2) if sig else None,
      'recall_a1_pct':rnd(100*ah/a1,2) if a1 else None,
      'winner_false_positive':wf,
      'winner_fp_rate_pct':rnd(100*wf/wins,2) if wins else None,
      'other_loss_signals':other,
      'loss_precision_any_pct':rnd(100*(ah+other)/len(sig),2) if sig else None,
    }


def main():
    rows,rec,miss=a713b.build()
    e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20)
    for r in rec:
        r['prex']=pre_features(rows,r['i'],e7,e20)
    d=rec[:83]; v=rec[83:]
    rules=[]
    for name,fn in RULES:
        rules.append({'rule':name,'discovery':score(d,fn),'validation':score(v,fn),'full':score(rec,fn)})
    out={
      'status':'SATURDAY18_A724_PREENTRY_WRONGWAY_ATLAS',
      'parent_n':len(rec),'funding_missing':miss,
      'base_counts':{
        'a1_full':sum(r['tax']==A1 for r in rec),'a1_discovery':sum(r['tax']==A1 for r in d),'a1_validation':sum(r['tax']==A1 for r in v),
        'winner_full':sum(r['tax']==WIN for r in rec),'winner_discovery':sum(r['tax']==WIN for r in d),'winner_validation':sum(r['tax']==WIN for r in v),
      },
      'atlas':{'discovery':atlas(d),'validation':atlas(v),'full':atlas(rec)},
      'rules':rules,
    }
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':
    main()
