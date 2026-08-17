"""BTC Friday15 A6.41 — causal rolling volatility regime diagnostic.

No strategy change and no validation-tuned thresholds.
Use RV24 from A6.40, but classify each Friday relative only to PRIOR Fridays:
- LOW_MEDIAN26: current RV24 below trailing 26-Friday median
- LOW_Q25_26: current RV24 below trailing 26-Friday 25th percentile
- HIGH_MEDIAN26: complement of LOW_MEDIAN26
Warmup first 26 Fridays excluded from regime comparisons.
Goal: test whether low-vol pre-entry state consistently associates with weaker A6.33 outcomes.
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a640_preentry_regime_attribution as a640
from btc_temporal_a34_5m_events import ldt, rnd

W=26

def quantile(vals,q):
    s=sorted(vals)
    if not s:return None
    p=(len(s)-1)*q; lo=int(p); hi=min(lo+1,len(s)-1); f=p-lo
    return s[lo]*(1-f)+s[hi]*f

def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0,'avg':None,'pf':None,'mdd':None}
    pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),
            'avg':rnd(statistics.mean(p),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a640.a636.a60.max_dd(p),3) if hasattr(a640.a636,'a60') else None}

def main():
    rows,rec=a636.build()
    for r in rec:
        r['date']=str(ldt(r['ts']).date()); r['rv24']=a640.feature_row(rows,r)['rv24']
    usable=[]
    for i,r in enumerate(rec):
        if i<W: continue
        hist=[rec[j]['rv24'] for j in range(i-W,i)]
        med=statistics.median(hist); q25=quantile(hist,.25)
        r['med26']=med; r['q25_26']=q25
        r['low_med']=r['rv24']<med
        r['low_q25']=r['rv24']<q25
        usable.append(r)
    # Chronological discovery/validation remains original split at first82.
    disc=[r for r in usable if rec.index(r)<82]
    val=[r for r in usable if rec.index(r)>=82]
    def pack(q,key):
        lo=[r for r in q if r[key]]; hi=[r for r in q if not r[key]]
        return {'low':econ(lo),'other':econ(hi),
                'low_rate':rnd(100*len(lo)/len(q),2) if q else None,
                'delta_avg_low_minus_other':rnd((statistics.mean([r['chosen'] for r in lo]) if lo else 0)-(statistics.mean([r['chosen'] for r in hi]) if hi else 0),4) if lo and hi else None}
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8); hi=round(len(rec)*(b+1)/8)
        q=[r for i,r in enumerate(rec) if lo<=i<hi and i>=W]
        if not q: continue
        low=[r for r in q if r['low_med']]; oth=[r for r in q if not r['low_med']]
        blocks.append({'block':b+1,'n':len(q),'low_n':len(low),'low_pnl':rnd(sum(r['chosen'] for r in low),3),
                       'other_pnl':rnd(sum(r['chosen'] for r in oth),3),
                       'low_avg':rnd(statistics.mean([r['chosen'] for r in low]),4) if low else None,
                       'other_avg':rnd(statistics.mean([r['chosen'] for r in oth]),4) if oth else None})
    # How often each regime overlaps the known DD interval, descriptive only.
    dd=[r for r in usable if '2025-05-09'<=r['date']<='2026-01-30']
    pre=[r for r in usable if r['date']<'2025-05-09']
    post=[r for r in usable if r['date']>'2026-01-30']
    overlap={g:{'n':len(q),'low_med_rate':rnd(100*sum(r['low_med'] for r in q)/len(q),2) if q else None,
                'low_q25_rate':rnd(100*sum(r['low_q25'] for r in q)/len(q),2) if q else None}
             for g,q in [('PRE',pre),('DD',dd),('POST',post)]}
    out={'status':'FRIDAY15_A641_CAUSAL_VOL_REGIME','warmup':W,
         'median26':{'full':pack(usable,'low_med'),'discovery_after_warmup':pack(disc,'low_med'),'validation':pack(val,'low_med')},
         'q25_26':{'full':pack(usable,'low_q25'),'discovery_after_warmup':pack(disc,'low_q25'),'validation':pack(val,'low_q25')},
         'overlap':overlap,'blocks_median26':blocks,
         'notes':'Diagnostic only. Regime thresholds are trailing-history statistics, not fit to DD or validation.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
