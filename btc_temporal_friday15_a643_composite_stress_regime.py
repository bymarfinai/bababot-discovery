"""BTC Friday15 A6.43 — composite pre-entry stress regime diagnostic.

Derived mechanistically from A6.40/A6.42, but thresholds are natural, not optimized:
- recent 60m volume > prior-24h 5m median volume (ratio > 1)
- recent 60m range > prior-24h median 5m range (ratio > 1)
- seller-led flow: 60m taker imbalance < 0
- negative 60m price return < 0
- optional low-vol macro state: RV24 below trailing 26-Friday median

No strategy changes. Diagnostics only. All features strictly pre-entry.
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a640_preentry_regime_attribution as a640
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
from btc_temporal_a34_5m_events import ldt, rnd

W=26

def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0,'avg':None,'pf':None,'mdd':None}
    pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),
            'avg':rnd(statistics.mean(p),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a636.a60.max_dd(p),3)}

def pack(q,key):
    yes=[r for r in q if r.get(key)]; no=[r for r in q if not r.get(key)]
    return {'state':econ(yes),'other':econ(no),'state_rate':rnd(100*len(yes)/len(q),2) if q else None,
            'delta_avg_state_minus_other':rnd(statistics.mean([r['chosen'] for r in yes])-statistics.mean([r['chosen'] for r in no]),4) if yes and no else None}

def main():
    rows,rec=a636.build()
    for r in rec:
        r['date']=str(ldt(r['ts']).date())
        r['macro']=a640.feature_row(rows,r)
        r['micro']=a642.features(rows,r)
    for i,r in enumerate(rec):
        if i>=W:
            hist=[rec[j]['macro']['rv24'] for j in range(i-W,i)]
            r['lowvol']=r['macro']['rv24']<statistics.median(hist)
        else:r['lowvol']=False
        m=r['micro']
        r['expansion']=m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['seller_led']=m['taker_imb_60']<0 and m['netret_60']<0
        r['stress_core']=r['expansion'] and r['seller_led']
        r['stress_lowvol']=i>=W and r['stress_core'] and r['lowvol']
        r['expansion_only']=r['expansion']
        r['seller_only']=r['seller_led']
    usable=[r for i,r in enumerate(rec) if i>=W]
    disc=[r for i,r in enumerate(rec) if W<=i<82]
    val=[r for i,r in enumerate(rec) if i>=82]
    states=['expansion_only','seller_only','stress_core','stress_lowvol']
    outstates={}
    for s in states:
        outstates[s]={'full_after_warmup':pack(usable,s),'discovery_after_warmup':pack(disc,s),'validation':pack(val,s)}
    # Known-period overlap, descriptive only.
    periods={
      'PRE':[r for i,r in enumerate(rec) if i>=W and r['date']<'2025-05-09'],
      'DD':[r for i,r in enumerate(rec) if '2025-05-09'<=r['date']<='2026-01-30'],
      'POST':[r for i,r in enumerate(rec) if r['date']>'2026-01-30']}
    overlap={}
    for g,q in periods.items():
        overlap[g]={'n':len(q)}
        for s in states: overlap[g][s+'_rate']=rnd(100*sum(r[s] for r in q)/len(q),2) if q else None
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8); hi=round(len(rec)*(b+1)/8)
        q=[r for i,r in enumerate(rec) if lo<=i<hi and i>=W]
        if not q:continue
        a=[r for r in q if r['stress_core']]; o=[r for r in q if not r['stress_core']]
        blocks.append({'block':b+1,'n':len(q),'stress_n':len(a),
                       'stress_pnl':rnd(sum(r['chosen'] for r in a),3),'other_pnl':rnd(sum(r['chosen'] for r in o),3),
                       'stress_avg':rnd(statistics.mean([r['chosen'] for r in a]),4) if a else None,
                       'other_avg':rnd(statistics.mean([r['chosen'] for r in o]),4) if o else None})
    out={'status':'FRIDAY15_A643_COMPOSITE_STRESS_REGIME','states':outstates,'overlap':overlap,'blocks_stress_core':blocks,
         'rules':{'expansion':'vol_ratio24_60>1 AND range_ratio24_60>1',
                  'seller_led':'taker_imb_60<0 AND netret_60<0',
                  'stress_core':'expansion AND seller_led',
                  'stress_lowvol':'stress_core AND RV24<trailing26-Friday median'},
         'notes':'Diagnostics only; thresholds are natural comparisons, not tuned on DD/validation.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
