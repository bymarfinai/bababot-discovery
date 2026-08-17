"""BTC Friday15 A6.46 — causal top-trader crowding + unwind attribution.

Diagnostics only; no strategy changes / no threshold optimization.
Natural states available before Friday15 entry:
- top_vs_global = top-trader position L/S ratio > global account L/S ratio
- top_vs_topacct = top-trader position L/S ratio > top-trader account L/S ratio
- crowded_both = both divergences true
- seller_unwind = seller-led 60m price/flow + OI-value non-increasing
- stress_unwind = A6.43 stress-core + OI-value non-increasing
- crowded_stress_unwind = crowded_both + stress_unwind
Also test crowding relative to trailing 26-Friday median (causal history only).
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
import btc_temporal_friday15_a645_positioning_attribution as a645
from btc_temporal_a34_5m_events import ldt, rnd

W=26;DD_START='2025-05-09';DD_END='2026-01-30'

def group(d):
    if d<DD_START:return 'PRE_DD'
    if d<=DD_END:return 'DD'
    return 'POST'

def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0,'avg':None,'pf':None,'mdd':None}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),
            'avg':rnd(statistics.mean(p),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a636.a60.max_dd(p),3)}

def pack(q,key):
    yes=[r for r in q if r[key]];no=[r for r in q if not r[key]]
    return {'state':econ(yes),'other':econ(no),'rate':rnd(100*len(yes)/len(q),2) if q else None}

def main():
    rows,rec=a636.build();cache={};usable=[]
    for r in rec:
        d=str(ldt(r['ts']).date());r['date']=d;r['grp']=group(d)
        if d not in cache:cache[d]=a645.load_day(d)
        r['pos']=a645.features(cache[d],r['ts'])
        if r['pos'] is None:continue
        m=a642.features(rows,r);r['micro']=m
        r['top_global_div']=100*(r['pos']['top_position']/r['pos']['global_account']-1)
        r['top_topacct_div']=100*(r['pos']['top_position']/r['pos']['top_account']-1)
        r['top_vs_global']=r['top_global_div']>0
        r['top_vs_topacct']=r['top_topacct_div']>0
        r['crowded_both']=r['top_vs_global'] and r['top_vs_topacct']
        r['seller_led']=m['taker_imb_60']<0 and m['netret_60']<0
        r['stress_core']=r['seller_led'] and m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['oi_down']=r['pos']['oi_value_chg_60']<=0
        r['seller_unwind']=r['seller_led'] and r['oi_down']
        r['stress_unwind']=r['stress_core'] and r['oi_down']
        r['crowded_stress_unwind']=r['crowded_both'] and r['stress_unwind']
        usable.append(r)
    assert len(usable)==138
    # causal trailing median of top/global divergence
    for i,r in enumerate(usable):
        if i<W:r['crowd_above_trailing_med']=False
        else:r['crowd_above_trailing_med']=r['top_global_div']>statistics.median([usable[j]['top_global_div'] for j in range(i-W,i)])
        r['trailing_crowd_stress_unwind']=i>=W and r['crowd_above_trailing_med'] and r['stress_unwind']
    groups={g:[r for r in usable if r['grp']==g] for g in ('PRE_DD','DD','POST')}
    states=['top_vs_global','top_vs_topacct','crowded_both','seller_unwind','stress_unwind','crowded_stress_unwind','crowd_above_trailing_med','trailing_crowd_stress_unwind']
    period={g:{s:pack(q,s) for s in states} for g,q in groups.items()}
    chronology={}
    for s in states:
        chronology[s]={'discovery':pack(usable[:82],s),'validation':pack(usable[82:],s),'full':pack(usable,s)}
    div_stats={}
    for n in ('top_global_div','top_topacct_div'):
        div_stats[n]={g:{'mean':rnd(statistics.mean([r[n] for r in q]),3),'median':rnd(statistics.median([r[n] for r in q]),3)} for g,q in groups.items()}
    # 8-block state frequency/outcome to see when inversion emerges.
    blocks=[]
    for b in range(8):
        lo=round(len(usable)*b/8);hi=round(len(usable)*(b+1)/8);q=usable[lo:hi]
        st=[r for r in q if r['crowded_stress_unwind']]
        blocks.append({'block':b+1,'n':len(q),'state_n':len(st),'state':econ(st),'other':econ([r for r in q if not r['crowded_stress_unwind']])})
    out={'status':'FRIDAY15_A646_CROWDING_UNWIND_ATTRIBUTION','divergence':div_stats,'period':period,'chronology':chronology,
         'blocks_crowded_stress_unwind':blocks,
         'rules':{'top_vs_global':'top_position_ratio > global_account_ratio','top_vs_topacct':'top_position_ratio > top_account_ratio',
                  'oi_down':'60m OI-value change <= 0','stress_unwind':'A6.43 stress_core AND oi_down',
                  'crowded_stress_unwind':'both top-trader divergence states AND stress_unwind',
                  'trailing':'top/global divergence > prior 26-Friday median AND stress_unwind'},
         'notes':'Diagnostics only. All conditions known before entry; thresholds are sign/relative comparisons, not fitted.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
