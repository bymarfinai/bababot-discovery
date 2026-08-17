"""BTC Friday15 A6.49 — causal two-layer regime direction-switch test.

Research question
-----------------
When the A6.48 online detector is already DEFENSIVE before entry AND the current
Friday itself shows the pre-entry A6.46 stress-unwind mechanism, does the
historical mean-reversion BUY remain appropriate, or has continuation SHORT
become the better response?

Every Friday occurrence remains traded. Only direction/management for the
DEFENSIVE + stress_unwind subset is changed. No threshold sweep is performed.

Detector is maintained as an A6.33 SHADOW health process: even when a policy
would trade SHORT, the engine can causally compute the hypothetical A6.33
Friday outcome after the occurrence and update the next Friday's health state.
Thus current-Friday decisions never use current/future outcomes.

Predeclared SHORT geometries are inherited, not tuned here:
- SYMMETRIC: TP2.0 / SL0.7 / max6h (mirror of Friday parent)
- POSTSTOP: TP1.5 / SL0.5 / max remaining6h (existing A6.22 short geometry)
- STILLOPEN: TP1.3 / SL0.7 / max6h (existing A6.22 still-open flip geometry)
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
import btc_temporal_friday15_a645_positioning_attribution as a645
from btc_temporal_a34_5m_events import ldt, rnd, TF

FAST_W=8;SLOW_W=13;COND_W=13;MIN_COND=2;HYST=2
DD_START='2025-05-09';DD_END='2026-01-30';FEE=.15;NOTIONAL=500.;HOLD=360


def group(d):
    if d<DD_START:return 'PRE_DD'
    if d<=DD_END:return 'DD'
    return 'POST'

def avg(x):return statistics.mean(x) if x else None

def short_trade(rows,i,tp,sl,hold=HOLD):
    e=rows[i][1];tp_px=e*(1-tp/100);sl_px=e*(1+sl/100);end=min(len(rows),i+hold//5)
    exit_px=None;reason='TIMEOUT'
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF:return None
        hit_tp=x[3]<=tp_px;hit_sl=x[2]>=sl_px
        if hit_tp and hit_sl:exit_px=sl_px;reason='AMB_SL';break
        if hit_sl:exit_px=sl_px;reason='SL';break
        if hit_tp:exit_px=tp_px;reason='TP';break
    if exit_px is None:exit_px=rows[end-1][4]
    gross=100*(e-exit_px)/e;net=gross-FEE
    return {'net_usd':NOTIONAL*net/100,'reason':reason,'gross_pct':gross}

def maxdd(p):return a636.a60.max_dd(p)
def ls(p):return a636.a60.loss_streak(p)
def econ_p(p):
    if not p:return {'n':0,'wr':None,'pnl':0.,'avg':None,'pf':None,'mdd':None,'ls':None}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),'avg':rnd(avg(p),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(maxdd(p),3),'ls':ls(p)}
def econ(q,key):return econ_p([r[key] for r in q])

def raw120(rows,r):
    j=r['i']+24
    return None if j>=len(rows) else 100*(rows[j][1]-r['entry'])/r['entry']

def build():
    rows,rec=a636.build();cache={};u=[]
    for r in rec:
        d=str(ldt(r['ts']).date());r['date']=d;r['grp']=group(d)
        if d not in cache:cache[d]=a645.load_day(d)
        p=a645.features(cache[d],r['ts']);m=a642.features(rows,r)
        seller=m['taker_imb_60']<0 and m['netret_60']<0
        stress=seller and m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['stress_unwind']=stress and p['oi_value_chg_60']<=0
        r['ret120']=raw120(rows,r);u.append(r)
    assert len(u)==138
    # Rebuild frozen A6.48 shadow-health state from PRIOR A6.33 outcomes only.
    state=False;en=0;ex=0
    for i,r in enumerate(u):
        fast=u[max(0,i-FAST_W):i];slow=u[max(0,i-SLOW_W):i];cw=u[max(0,i-COND_W):i]
        cond=[x for x in cw if x['stress_unwind']]
        f=avg([x['chosen'] for x in fast]) if len(fast)==FAST_W else None
        s=avg([x['chosen'] for x in slow]) if len(slow)==SLOW_W else None
        cp=avg([x['chosen'] for x in cond]) if len(cond)>=MIN_COND else None
        cr=avg([x['ret120'] for x in cond if x['ret120'] is not None]) if len(cond)>=MIN_COND else None
        confirms=sum(v is not None and v<0 for v in (s,cp,cr))
        enter=f is not None and f<0 and confirms>=1
        exit_=f is not None and s is not None and f>0 and s>0
        en=en+1 if enter else 0;ex=ex+1 if exit_ else 0
        if not state and en>=HYST:state=True;ex=0
        elif state and ex>=HYST:state=False;en=0
        r['defensive']=state;r['switch']=state and r['stress_unwind']
    return rows,u

def main():
    rows,u=build()
    geoms={'SYMMETRIC':(2.0,.7),'POSTSTOP':(1.5,.5),'STILLOPEN':(1.3,.7)}
    for r in u:
        r['BASE']=r['chosen']
        for name,(tp,sl) in geoms.items():
            if r['switch']:
                t=short_trade(rows,r['i'],tp,sl,HOLD);r[name]=t['net_usd'];r[name+'_reason']=t['reason']
            else:r[name]=r['chosen'];r[name+'_reason']='BASE'
    out={'status':'FRIDAY15_A649_REGIME_DIRECTION_SWITCH','base':econ(u,'BASE'),'switch_n':sum(r['switch'] for r in u),
         'switch_dates':[r['date'] for r in u if r['switch']],'policies':{}}
    for name in geoms:
        pol={'full':econ(u,name),'discovery':econ(u[:82],name),'validation':econ(u[82:],name),
             'by_period':{},'switch_only':econ([r for r in u if r['switch']],name),
             'baseline_same_cases':econ([r for r in u if r['switch']],'BASE')}
        for g in ('PRE_DD','DD','POST'):
            q=[r for r in u if r['grp']==g];s=[r for r in q if r['switch']]
            pol['by_period'][g]={'engine':econ(q,name),'switch_n':len(s),'switch_policy':econ(s,name),'switch_base':econ(s,'BASE')}
        pol['delta_full']=rnd(pol['full']['pnl']-out['base']['pnl'],3)
        pol['changed_positive_to_negative']=sum(r['switch'] and r['BASE']>0 and r[name]<=0 for r in u)
        pol['changed_negative_to_positive']=sum(r['switch'] and r['BASE']<=0 and r[name]>0 for r in u)
        out['policies'][name]=pol
    out['notes']='All 138 Fridays remain traded. A6.48 detector uses prior shadow A6.33 outcomes only; current stress-unwind uses pre-entry data only. Geometries inherited; no new parameter sweep.'
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
