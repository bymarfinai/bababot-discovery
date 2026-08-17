"""BTC Friday15 A6.47 — causal online response-function regime detector.

Purpose
-------
Detect whether the Friday15 response function has shifted from historical
mean-reversion toward continuation using ONLY outcomes from PRIOR Fridays.
No current-Friday outcome is used in the current-Friday regime decision.
No live changes and no trading rule promotion in this study.

Fixed, interpretable memories (not optimized on the known drawdown):
- overall strategy health: prior 13 Fridays (~1 quarter)
- conditional response health: last 5 prior stress-unwind Fridays
- raw price response health: same last 5 stress-unwind Fridays, 120m return

stress_unwind is the already-defined A6.46 pre-entry mechanism:
60m seller-led local expansion + OI-value non-increasing.

Three causal health votes before each entry:
1) prior13 A6.33 average PnL < 0
2) last5 stress-unwind A6.33 average PnL < 0 (minimum 3 observations)
3) last5 stress-unwind raw 120m return < 0 (minimum 3 observations)

We report 1/2/3-vote regimes. The point is detection quality, not selecting a
threshold to maximize the same 138-Friday backtest.
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
import btc_temporal_friday15_a645_positioning_attribution as a645
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'
OVERALL_W=13; COND_W=5; MIN_COND=3


def grp(d):
    if d < DD_START: return 'PRE_DD'
    if d <= DD_END: return 'DD'
    return 'POST'


def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0.0,'avg':None,'pf':None,'mdd':None}
    pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),
            'avg':rnd(statistics.mean(p),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a636.a60.max_dd(p),3)}


def raw120(rows,r):
    j=r['i']+24
    if j>=len(rows): return None
    return 100*(rows[j][1]-r['entry'])/r['entry']


def detector_stats(rec,key):
    yes=[r for r in rec if r[key]]; no=[r for r in rec if not r[key]]
    by={}
    for g in ('PRE_DD','DD','POST'):
        q=[r for r in rec if r['grp']==g]; st=[r for r in q if r[key]]
        by[g]={'n':len(q),'flag_n':len(st),'flag_rate':rnd(100*len(st)/len(q),2) if q else None,
               'flag_econ':econ(st),'other_econ':econ([r for r in q if not r[key]])}
    dd=[r for r in rec if r['grp']=='DD']
    first=next((r['date'] for r in dd if r[key]),None)
    # transition dates for auditability
    trans=[]; prev=None
    for r in rec:
        cur=bool(r[key])
        if prev is None or cur!=prev:
            trans.append({'date':r['date'],'flag':cur,'votes':r['votes'],
                          'overall13_avg':r['overall13_avg'],'cond5_pnl_avg':r['cond5_pnl_avg'],
                          'cond5_ret120_avg':r['cond5_ret120_avg'],'cond_hist_n':r['cond_hist_n']})
        prev=cur
    return {'full_flagged':econ(yes),'full_other':econ(no),'by_period':by,
            'first_flag_inside_dd':first,'transitions':trans}


def main():
    rows,rec=a636.build(); cache={}; usable=[]
    for r in rec:
        d=str(ldt(r['ts']).date()); r['date']=d; r['grp']=grp(d)
        if d not in cache: cache[d]=a645.load_day(d)
        pos=a645.features(cache[d],r['ts'])
        if pos is None: continue
        m=a642.features(rows,r)
        seller=m['taker_imb_60']<0 and m['netret_60']<0
        stress=seller and m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['stress_unwind']=stress and pos['oi_value_chg_60']<=0
        r['ret120']=raw120(rows,r)
        usable.append(r)
    assert len(usable)==138

    cond_hist=[]
    for i,r in enumerate(usable):
        prior_all=usable[max(0,i-OVERALL_W):i]
        r['overall13_avg']=rnd(statistics.mean([x['chosen'] for x in prior_all]),4) if len(prior_all)==OVERALL_W else None
        last=cond_hist[-COND_W:]
        r['cond_hist_n']=len(cond_hist)
        r['cond5_pnl_avg']=rnd(statistics.mean([x['chosen'] for x in last]),4) if len(last)>=MIN_COND else None
        rr=[x['ret120'] for x in last if x['ret120'] is not None]
        r['cond5_ret120_avg']=rnd(statistics.mean(rr),4) if len(rr)>=MIN_COND else None
        votes=[]
        if r['overall13_avg'] is not None: votes.append(r['overall13_avg']<0)
        if r['cond5_pnl_avg'] is not None: votes.append(r['cond5_pnl_avg']<0)
        if r['cond5_ret120_avg'] is not None: votes.append(r['cond5_ret120_avg']<0)
        r['votes']=sum(votes)
        r['available_votes']=len(votes)
        r['bad_vote1']=r['available_votes']>=2 and r['votes']>=1
        r['bad_vote2']=r['available_votes']>=2 and r['votes']>=2
        r['bad_vote3']=r['available_votes']==3 and r['votes']==3
        r['bad_overall13']=r['overall13_avg'] is not None and r['overall13_avg']<0
        r['bad_cond_pnl']=r['cond5_pnl_avg'] is not None and r['cond5_pnl_avg']<0
        r['bad_cond_ret']=r['cond5_ret120_avg'] is not None and r['cond5_ret120_avg']<0
        if r['stress_unwind']: cond_hist.append(r)

    keys=['bad_overall13','bad_cond_pnl','bad_cond_ret','bad_vote1','bad_vote2','bad_vote3']
    stats={k:detector_stats(usable,k) for k in keys}

    # Week-by-week audit around the known structural break, but dates are NOT used by detector.
    audit=[]
    for r in usable:
        if '2025-03-01'<=r['date']<='2026-04-30':
            audit.append({'date':r['date'],'pnl':rnd(r['chosen'],3),'stress_unwind':r['stress_unwind'],
                          'ret120':rnd(r['ret120'],3),'overall13_avg':r['overall13_avg'],
                          'cond5_pnl_avg':r['cond5_pnl_avg'],'cond5_ret120_avg':r['cond5_ret120_avg'],
                          'votes':r['votes'],'vote2':r['bad_vote2']})

    out={'status':'FRIDAY15_A647_ONLINE_RESPONSE_REGIME_DETECTOR',
         'engine':econ(usable),'fixed_memory':{'overall_weeks':OVERALL_W,'conditional_events':COND_W,'min_conditional_events':MIN_COND},
         'detectors':stats,'audit_break_window':audit,
         'notes':'All flags are known before each Friday entry. Known DD dates are evaluation labels only; they are never inputs to a detector. No strategy action is changed.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__': main()
