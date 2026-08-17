"""BTC Friday15 A6.42 — pre-entry microstructure attribution.

Diagnostics only. No strategy changes / no threshold selection.
Compare PRE_DD vs DD vs POST using only completed 5m bars before 15:00 WIB.
Features: taker imbalance, volume participation, range/compression, directional efficiency,
close location, and absorption-like flow/price disagreement over 30/60/120m.
"""
import json, math, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'
WINDOWS=(30,60,120)

def mean(x): return statistics.mean(x) if x else None

def med(x): return statistics.median(x) if x else None

def sd(x): return statistics.stdev(x) if len(x)>1 else 0.0

def smd(a,b):
    a=[x for x in a if x is not None]; b=[x for x in b if x is not None]
    if len(a)<2 or len(b)<2:return None
    den=math.sqrt((statistics.variance(a)+statistics.variance(b))/2)
    return rnd((statistics.mean(a)-statistics.mean(b))/den,3) if den else 0.0

def corr(x,y):
    q=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(q)<3:return None
    xa=[a for a,b in q]; ya=[b for a,b in q]; mx=mean(xa); my=mean(ya)
    num=sum((a-mx)*(b-my) for a,b in q)
    den=math.sqrt(sum((a-mx)**2 for a in xa)*sum((b-my)**2 for b in ya))
    return rnd(num/den,3) if den else 0.0

def group(date):
    if date<DD_START:return 'PRE_DD'
    if date<=DD_END:return 'DD'
    return 'POST'

def feat_window(rows,i,mins):
    n=mins//5; q=rows[i-n:i]
    p0=q[0][1]; pc=q[-1][4]
    net=100*(pc/p0-1)
    bar_abs=sum(abs(100*(x[4]/x[1]-1)) for x in q)
    efficiency=abs(net)/bar_abs if bar_abs>0 else 0.0
    total_q=sum(x[6] for x in q); total_taker=sum(x[9] for x in q)
    taker_ratio=total_taker/total_q if total_q>0 else .5
    taker_imb=2*taker_ratio-1
    hi=max(x[2] for x in q); lo=min(x[3] for x in q); rng=100*(hi/lo-1) if lo>0 else 0
    close_loc=(pc-lo)/(hi-lo) if hi>lo else .5
    bodies=[abs(x[4]-x[1])/(x[2]-x[3]) if x[2]>x[3] else 0 for x in q]
    signed_bodies=[(1 if x[4]>x[1] else -1 if x[4]<x[1] else 0)*(abs(x[4]-x[1])/(x[2]-x[3]) if x[2]>x[3] else 0) for x in q]
    # compare recent participation/range to prior 24h 5m medians, all completed pre-entry.
    h24=rows[max(0,i-288):i]
    vol_med=statistics.median([x[6] for x in h24]) if h24 else 1
    range_med=statistics.median([x[2]-x[3] for x in h24]) if h24 else 1
    vol_ratio=statistics.mean([x[6] for x in q])/vol_med if vol_med else 0
    range_ratio=statistics.mean([x[2]-x[3] for x in q])/range_med if range_med else 0
    # Price/flow disagreement: positive means taker buying but price fails upward, negative converse.
    absorption=taker_imb * (-1 if net<0 else 1 if net>0 else 0) * -1
    # simpler explicit flags represented continuously
    buy_fail=max(0,taker_imb) * max(0,-net)
    sell_fail=max(0,-taker_imb) * max(0,net)
    return {
      f'taker_imb_{mins}':taker_imb,
      f'netret_{mins}':net,
      f'efficiency_{mins}':efficiency,
      f'range_{mins}':rng,
      f'close_loc_{mins}':close_loc,
      f'body_ratio_{mins}':statistics.mean(bodies),
      f'signed_body_{mins}':statistics.mean(signed_bodies),
      f'vol_ratio24_{mins}':vol_ratio,
      f'range_ratio24_{mins}':range_ratio,
      f'buy_fail_{mins}':buy_fail,
      f'sell_fail_{mins}':sell_fail,
    }

def features(rows,r):
    out={}
    for w in WINDOWS: out.update(feat_window(rows,r['i'],w))
    return out

def stat(vals):
    vals=[x for x in vals if x is not None]
    return {'n':len(vals),'mean':rnd(mean(vals),4),'median':rnd(med(vals),4),'sd':rnd(sd(vals),4)}

def main():
    rows,rec=a636.build()
    for r in rec:
        r['date']=str(ldt(r['ts']).date()); r['grp']=group(r['date']); r['feat']=features(rows,r)
    groups={g:[r for r in rec if r['grp']==g] for g in ('PRE_DD','DD','POST')}
    names=list(rec[0]['feat'].keys()); result={}
    for n in names:
        pre=[r['feat'][n] for r in groups['PRE_DD']]; dd=[r['feat'][n] for r in groups['DD']]; post=[r['feat'][n] for r in groups['POST']]
        result[n]={'pre':stat(pre),'dd':stat(dd),'post':stat(post),
                   'smd_dd_vs_pre':smd(dd,pre),'smd_dd_vs_post':smd(dd,post),
                   'corr_vs_pnl':corr([r['feat'][n] for r in rec],[r['chosen'] for r in rec])}
    ranked=sorted([{'feature':n,**result[n]} for n in names],key=lambda z:abs(z['smd_dd_vs_pre'] or 0),reverse=True)
    # pre-entry taker/price sign table, descriptive only
    combos={}
    for g,q in groups.items():
        z={}
        for w in WINDOWS:
            for key,fn in {
              'SELLFLOW_DOWN':lambda r: r['feat'][f'taker_imb_{w}']<0 and r['feat'][f'netret_{w}']<0,
              'BUYFLOW_UP':lambda r: r['feat'][f'taker_imb_{w}']>0 and r['feat'][f'netret_{w}']>0,
              'BUYFLOW_FAIL':lambda r: r['feat'][f'taker_imb_{w}']>0 and r['feat'][f'netret_{w}']<=0,
              'SELLFLOW_FAIL':lambda r: r['feat'][f'taker_imb_{w}']<0 and r['feat'][f'netret_{w}']>=0,
            }.items():
                a=[r for r in q if fn(r)]
                z[f'{key}_{w}']={'n':len(a),'rate':rnd(100*len(a)/len(q),2) if q else None,
                                 'avg_pnl':rnd(mean([r['chosen'] for r in a]),4) if a else None}
        combos[g]=z
    out={'status':'FRIDAY15_A642_PREENTRY_MICROSTRUCTURE_ATTRIBUTION','features':result,
         'ranked_dd_vs_pre':ranked,'flow_price_combos':combos,
         'notes':'Diagnostics only; no thresholds or trading rules selected.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
