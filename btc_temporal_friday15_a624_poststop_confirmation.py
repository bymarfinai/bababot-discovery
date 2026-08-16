"""BTC Friday15 A6.24 — post-stop SHORT confirmation / exhaustion guard.

Goal: improve A6.22 post-stop rescue without training on validation.
All 138 original Friday15 BUY entries remain.

Frozen engine pieces:
- parent BUY TP2.0 / SL0.7 / max6h
- failed-thesis detector at 60m + persistent failure at 120m
- post-stop SHORT geometry TP1.5 / SL0.5 from A6.22
- still-open failure remains A6.22 FLIP SHORT TP1.3 / SL0.7
- A6.15 distribution protection unchanged

Mechanism-driven post-stop policies only:
1) NO_REENTRY control
2) IMMEDIATE_120 = A6.22 reference
3) D20_GUARD = take 120m SHORT only if strict-causal d20 > -0.10%, a threshold inherited from prior A6.18 exhaustion hypothesis
4) WAIT15_CONT = wait to 135m, SHORT only if actual 135m open is below actual 120m open
5) WAIT30_CONT = wait to 150m, same continuation condition
6) WAIT15_CONT_D20 = both frozen d20 guard and 15m continuation

Selection summary uses first82 discovery engine PnL only. Validation is reporting only.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

H=120; HOLD=360; POST_TP=1.5; POST_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
D20_GUARD=-.10
POLICIES=('NO_REENTRY','IMMEDIATE_120','D20_GUARD','WAIT15_CONT','WAIT30_CONT','WAIT15_CONT_D20')

def econ(p):
    n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
            'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
            'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def exact_index(rows,i,mins):
    j=i+mins//5
    if j>=len(rows) or rows[j][0]!=rows[i][0]+(mins//5)*TF:return None
    return j

def poststop_decision(rows,r,policy):
    """Return (occurrence pnl, took_short, short_leg_pnl, decision_min)."""
    if not r['prior_stop']:
        return r['base'],False,None,None
    j0=exact_index(rows,r['i'],120); end=exact_index(rows,r['i'],HOLD)
    if j0 is None or end is None:return r['base'],False,None,None
    c120=r['c120']
    if policy=='NO_REENTRY':return r['base'],False,None,None
    if policy=='IMMEDIATE_120':j=j0
    elif policy=='D20_GUARD':
        if c120 is None or c120['d20']<=D20_GUARD:return r['base'],False,None,None
        j=j0
    elif policy in ('WAIT15_CONT','WAIT15_CONT_D20'):
        if policy.endswith('_D20') and (c120 is None or c120['d20']<=D20_GUARD):return r['base'],False,None,None
        j=exact_index(rows,r['i'],135)
        if j is None or rows[j][1]>=rows[j0][1]:return r['base'],False,None,None
    elif policy=='WAIT30_CONT':
        j=exact_index(rows,r['i'],150)
        if j is None or rows[j][1]>=rows[j0][1]:return r['base'],False,None,None
    else:raise ValueError(policy)
    if j>=end:return r['base'],False,None,None
    s=a611.short_leg(rows,j,end,POST_TP,POST_SL)
    return r['base']+s,True,s,(j-r['i'])*5

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
        r['wrongway']=a620.confirmed(rows,r,e7,e20)
        r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
        r['c120']=a69.checkpoint(rows,r,e7,e20,120) if r['wrongway'] else None
        r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
        r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
        r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
        rec.append(r)
    assert len(rec)==138

    def final_for(r,policy):
        if r['wrongway']:
            if r['prior_stop']:
                return poststop_decision(rows,r,policy)
            return a620.wrongway_action(rows,r,1.3),True,None,120  # still-open frozen FLIP
        if r['dist_active']:
            return a613.protect_pnl(rows,r,r['sig'],a620.LOCK),True,None,None
        return r['base'],False,None,None

    variants=[]
    for policy in POLICIES:
        vals=[]
        for r in rec:
            v,took,short,dm=final_for(r,policy)
            vals.append((r,v,took,short,dm))
        def sub(q):
            p=[v for r,v,took,short,dm in q];z=[x for x in q if x[0]['prior_stop']]
            taken=[x for x in z if x[2]]
            shortlegs=[x[3] for x in taken if x[3] is not None]
            return {'engine':econ(p),'poststop_n':len(z),'poststop_taken':len(taken),
                    'poststop_positive':sum(v>0 for r,v,took,short,dm in z),
                    'poststop_negative':sum(v<=0 for r,v,took,short,dm in z),
                    'poststop_pnl':rnd(sum(v for r,v,took,short,dm in z),3),
                    'poststop_delta_vs_parent':rnd(sum(v-r['base'] for r,v,took,short,dm in z),3),
                    'double_loss':sum(took and v<r['base'] for r,v,took,short,dm in z),
                    'short_leg':econ(shortlegs) if shortlegs else None,
                    'd20_taken_med':rnd(__import__('statistics').median([r['c120']['d20'] for r,v,took,short,dm in taken if r['c120']]),4) if any(r['c120'] for r,v,took,short,dm in taken) else None,
                    'decision_mins':{str(m):sum(dm==m for r,v,took,short,dm in taken) for m in (120,135,150)}}
        ds=sub(vals[:82]);vs=sub(vals[82:]);fs=sub(vals)
        variants.append({'policy':policy,'score_disc':ds['engine']['pnl'],'discovery':ds,'validation':vs,'full':fs})

    chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['poststop_pnl'],-z['discovery']['double_loss']))
    policy=chosen['policy']; chosen_vals=[]
    for r in rec:
        v,took,short,dm=final_for(r,policy);chosen_vals.append((r,v,took,short,dm))
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=chosen_vals[lo:hi]
        blocks.append({'block':b+1,'parent':rnd(sum(r['base'] for r,v,took,short,dm in q),3),
                       'new':rnd(sum(v for r,v,took,short,dm in q),3),
                       'delta':rnd(sum(v-r['base'] for r,v,took,short,dm in q),3),
                       'poststop':sum(r['prior_stop'] for r,v,took,short,dm in q),
                       'poststop_taken':sum(r['prior_stop'] and took for r,v,took,short,dm in q)})
    years={}
    for y in sorted(set(ldt(r['ts']).year for r in rec)):
        q=[x for x in chosen_vals if ldt(x[0]['ts']).year==y]
        years[str(y)]={'stats':econ([v for r,v,took,short,dm in q]),
                       'parent':econ([r['base'] for r,v,took,short,dm in q]),
                       'delta':rnd(sum(v-r['base'] for r,v,took,short,dm in q),3),
                       'poststop':sum(r['prior_stop'] for r,v,took,short,dm in q),
                       'poststop_taken':sum(r['prior_stop'] and took for r,v,took,short,dm in q)}
    postcases=[]
    for r in rec:
        if not r['prior_stop']:continue
        row={'date':ldt(r['ts']).date().isoformat(),'split':'D' if rec.index(r)<82 else 'V',
             'base':rnd(r['base'],3),'d20_120':rnd(r['c120']['d20'],4) if r['c120'] else None,
             'progress_120':rnd(r['c120']['progress'],4) if r['c120'] else None}
        for pol in POLICIES:
            v,took,short,dm=poststop_decision(rows,r,pol)
            row[pol]={'pnl':rnd(v,3),'taken':took,'short':rnd(short,3) if short is not None else None,'decision_min':dm}
        postcases.append(row)
    out={'status':'FRIDAY15_A624_POSTSTOP_CONFIRMATION','frozen_poststop_geometry':{'tp':POST_TP,'sl':POST_SL},
         'inherited_d20_guard':D20_GUARD,'selection':'first82 discovery engine PnL only; low-N caution',
         'variants':variants,'chosen':chosen,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),
         'blocks':blocks,'years':years,'poststop_cases':postcases}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
