"""BTC Friday15 A6.48 — time-decay + hysteresis regime detector.

Fixes the A6.47 flaw where sparse conditional-event memory could remain stale
for months after the underlying stress state stopped occurring.

All decisions use PRIOR Fridays only. No current outcome leakage.
No strategy action is changed.

Fixed detector architecture:
- FAST health = prior 8 Friday A6.33 average PnL
- SLOW health = prior 13 Friday A6.33 average PnL
- CONDITIONAL health = stress-unwind outcomes occurring inside prior 13 Fridays
  (minimum 2 events; otherwise unavailable, so stale events cannot persist)
- raw conditional price response = same rolling-13-week stress events, 120m return

State machine, fixed before seeing results:
- enter DEFENSIVE after two consecutive Fridays with FAST<0 and at least one
  additional confirming negative component among SLOW / conditional PnL /
  conditional 120m response.
- exit DEFENSIVE after two consecutive Fridays with FAST>0 and SLOW>0.

The two-consecutive hysteresis is to avoid one-week toggling, not optimized.
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
import btc_temporal_friday15_a645_positioning_attribution as a645
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'
FAST_W=8; SLOW_W=13; COND_W=13; MIN_COND=2; HYST=2


def group(d):
    if d<DD_START:return 'PRE_DD'
    if d<=DD_END:return 'DD'
    return 'POST'


def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0.0,'avg':None,'pf':None,'mdd':None}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),
            'avg':rnd(statistics.mean(p),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a636.a60.max_dd(p),3)}


def avg(xs): return statistics.mean(xs) if xs else None

def raw120(rows,r):
    j=r['i']+24
    return None if j>=len(rows) else 100*(rows[j][1]-r['entry'])/r['entry']


def stats(rec,key):
    yes=[r for r in rec if r[key]];no=[r for r in rec if not r[key]]
    by={}
    for g in ('PRE_DD','DD','POST'):
        q=[r for r in rec if r['grp']==g];s=[r for r in q if r[key]]
        by[g]={'n':len(q),'flag_n':len(s),'flag_rate':rnd(100*len(s)/len(q),2),
               'flag_econ':econ(s),'other_econ':econ([r for r in q if not r[key]])}
    return {'flagged':econ(yes),'other':econ(no),'by_period':by}


def main():
    rows,rec=a636.build();cache={};u=[]
    for r in rec:
        d=str(ldt(r['ts']).date());r['date']=d;r['grp']=group(d)
        if d not in cache:cache[d]=a645.load_day(d)
        p=a645.features(cache[d],r['ts'])
        if p is None:continue
        m=a642.features(rows,r)
        seller=m['taker_imb_60']<0 and m['netret_60']<0
        stress=seller and m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['stress_unwind']=stress and p['oi_value_chg_60']<=0
        r['ret120']=raw120(rows,r);u.append(r)
    assert len(u)==138

    enter_streak=0;exit_streak=0;state=False;trans=[]
    for i,r in enumerate(u):
        fast=u[max(0,i-FAST_W):i];slow=u[max(0,i-SLOW_W):i];cw=u[max(0,i-COND_W):i]
        cond=[x for x in cw if x['stress_unwind']]
        r['fast8']=rnd(avg([x['chosen'] for x in fast]),4) if len(fast)==FAST_W else None
        r['slow13']=rnd(avg([x['chosen'] for x in slow]),4) if len(slow)==SLOW_W else None
        r['cond13_n']=len(cond)
        r['cond13_pnl']=rnd(avg([x['chosen'] for x in cond]),4) if len(cond)>=MIN_COND else None
        cr=[x['ret120'] for x in cond if x['ret120'] is not None]
        r['cond13_ret']=rnd(avg(cr),4) if len(cr)>=MIN_COND else None
        confirms=sum(v is not None and v<0 for v in (r['slow13'],r['cond13_pnl'],r['cond13_ret']))
        enter_raw=r['fast8'] is not None and r['fast8']<0 and confirms>=1
        exit_raw=r['fast8'] is not None and r['slow13'] is not None and r['fast8']>0 and r['slow13']>0
        enter_streak=enter_streak+1 if enter_raw else 0
        exit_streak=exit_streak+1 if exit_raw else 0
        old=state
        if not state and enter_streak>=HYST:
            state=True;exit_streak=0
        elif state and exit_streak>=HYST:
            state=False;enter_streak=0
        r['enter_raw']=enter_raw;r['exit_raw']=exit_raw;r['defensive']=state
        if state!=old:
            trans.append({'date':r['date'],'to':'DEFENSIVE' if state else 'NORMAL','fast8':r['fast8'],'slow13':r['slow13'],
                          'cond13_n':r['cond13_n'],'cond13_pnl':r['cond13_pnl'],'cond13_ret':r['cond13_ret']})

    # Simple fixed-window diagnostics, not candidates for promotion.
    for r in u:
        r['fast_bad']=r['fast8'] is not None and r['fast8']<0
        r['slow_bad']=r['slow13'] is not None and r['slow13']<0
        r['cond_recent_bad']=r['cond13_pnl'] is not None and r['cond13_pnl']<0

    dd=[r for r in u if r['grp']=='DD'];post=[r for r in u if r['grp']=='POST']
    first=next((r['date'] for r in dd if r['defensive']),None)
    first_post_normal=next((r['date'] for r in post if not r['defensive']),None)
    audit=[{'date':r['date'],'pnl':rnd(r['chosen'],3),'stress':r['stress_unwind'],'fast8':r['fast8'],'slow13':r['slow13'],
            'cond_n':r['cond13_n'],'cond_pnl':r['cond13_pnl'],'cond_ret':r['cond13_ret'],'defensive':r['defensive']}
           for r in u if '2025-04-01'<=r['date']<='2026-05-31']
    out={'status':'FRIDAY15_A648_TIME_DECAY_HYSTERESIS_DETECTOR','engine':econ(u),
         'architecture':{'fast_weeks':FAST_W,'slow_weeks':SLOW_W,'conditional_calendar_weeks':COND_W,'min_conditional_events':MIN_COND,
                         'hysteresis_weeks':HYST,'entry':'FAST<0 and >=1 negative confirmation for 2 consecutive Fridays',
                         'exit':'FAST>0 and SLOW>0 for 2 consecutive Fridays'},
         'state':stats(u,'defensive'),'diagnostics':{'fast_bad':stats(u,'fast_bad'),'slow_bad':stats(u,'slow_bad'),'conditional_recent_bad':stats(u,'cond_recent_bad')},
         'first_defensive_inside_dd':first,'first_normal_post_dd':first_post_normal,'transitions':trans,'audit':audit,
         'notes':'All state decisions are known before entry; known DD dates are labels only. No trading action changed.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
