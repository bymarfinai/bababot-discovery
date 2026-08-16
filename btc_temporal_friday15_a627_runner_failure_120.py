"""BTC Friday15 A6.27 — 120m failed-runner state after proven rebound.

New mechanism, no entry filtering and no threshold sweep.
State at actual 120m open, strict causal completed history:
- NOT in the existing wrong-way state
- original BUY is still open at120
- completed first120m MFE >= +0.5% (rebound was proven)
- actual120m-open progress < 0% (the proven rebound has fully failed back below entry)

This uses natural boundaries already established by the loss taxonomy: +0.5 hinge and zero-entry reclaim.
If A6.15 distribution protection already triggered before120, that earlier action retains precedence.
Otherwise compare only three policies on this fixed state, selected by first82 discovery engine PnL:
HOLD existing A6.22 path, CUT at actual120 open, FLIP at120 into SHORT TP1.5/SL0.5.

Frozen elsewhere:
- all 138 Friday15 BUY entries
- parent TP2/SL0.7/max6h
- wrong-way post-stop SHORT TP1.5/SL0.5
- wrong-way still-open FLIP TP1.3/SL0.7
- A6.15 distribution protection
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

H=120;HOLD=360;NOTIONAL=500.;FEE_USD=.75
POSTSTOP_TP=1.5;POSTSTOP_SL=.5
RUNNER_SHORT_TP=1.5;RUNNER_SHORT_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
POLICIES=('HOLD','CUT','FLIP')

def econ(p):
    n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
            'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
        r['wrongway']=a620.confirmed(rows,r,e7,e20);r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
        r['c120']=a69.checkpoint(rows,r,e7,e20,120)
        r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
        r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
        r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
        j=i+H//5
        # Earlier distribution action has temporal precedence if decision is strictly before 120m decision.
        r['dist_before120']=r['dist_active'] and r['sig'] is not None and r['sig']['decision']<j
        r['open120']=not a617b.exited_before_120(r)
        r['runner_fail']=bool((not r['wrongway']) and (not r['dist_before120']) and r['open120'] and r['c120']
                              and r['c120']['mfe']>=.5 and r['c120']['progress']<0)
        rec.append(r)
    assert len(rec)==138

    def baseline(r):
        if r['wrongway']:
            if r['prior_stop']:
                j=r['i']+H//5
                return r['base']+a611.short_leg(rows,j,r['i']+HOLD//5,POSTSTOP_TP,POSTSTOP_SL)
            return a620.wrongway_action(rows,r,1.3)
        if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
        return r['base']

    def runner_action(r,policy):
        if not r['runner_fail']:return baseline(r)
        if policy=='HOLD':return baseline(r)
        j=r['i']+H//5;px=rows[j][1]
        long=(px-r['entry'])/r['entry']*NOTIONAL-FEE_USD
        if policy=='CUT':return long
        return long+a611.short_leg(rows,j,r['i']+HOLD//5,RUNNER_SHORT_TP,RUNNER_SHORT_SL)

    variants=[]
    for pol in POLICIES:
        for r in rec:r['new']=runner_action(r,pol)
        def sub(q):
            z=[r for r in q if r['runner_fail']]
            return {'engine':econ([r['new'] for r in q]),'runner_fail':econ([r['new'] for r in z]),
                    'baseline_runner':econ([baseline(r) for r in z]),'n':len(z),
                    'delta':rnd(sum(r['new']-baseline(r) for r in z),3),
                    'loss_to_win':sum(baseline(r)<=0 and r['new']>0 for r in z),
                    'win_to_loss':sum(baseline(r)>0 and r['new']<=0 for r in z)}
        ds=sub(rec[:82]);vs=sub(rec[82:]);fs=sub(rec)
        variants.append({'policy':pol,'score_disc':ds['engine']['pnl'],'discovery':ds,'validation':vs,'full':fs})
    chosen=max(variants,key=lambda z:(z['score_disc'],z['discovery']['loss_to_win'],-z['discovery']['win_to_loss']))
    pol=chosen['policy']
    for r in rec:r['chosen']=runner_action(r,pol);r['ref']=baseline(r)
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
        blocks.append({'block':b+1,'reference':rnd(sum(r['ref'] for r in q),3),'new':rnd(sum(r['chosen'] for r in q),3),
                       'delta':rnd(sum(r['chosen']-r['ref'] for r in q),3),'signals':sum(r['runner_fail'] for r in q)})
    years={}
    for y in sorted(set(ldt(r['ts']).year for r in rec)):
        q=[r for r in rec if ldt(r['ts']).year==y]
        years[str(y)]={'reference':econ([r['ref'] for r in q]),'new':econ([r['chosen'] for r in q]),
                       'delta':rnd(sum(r['chosen']-r['ref'] for r in q),3),'signals':sum(r['runner_fail'] for r in q)}
    cases=[]
    for ix,r in enumerate(rec):
        if r['runner_fail']:
            cases.append({'date':ldt(r['ts']).date().isoformat(),'split':'D' if ix<82 else 'V','label':r['label'],
                          'baseline':rnd(r['ref'],3),'chosen':rnd(r['chosen'],3),'mfe120':rnd(r['c120']['mfe'],4),
                          'progress120':rnd(r['c120']['progress'],4),'reason':r['trade']['reason']})
    out={'status':'FRIDAY15_A627_RUNNER_FAILURE_120','state':'nonwrongway, BUY open120, MFE120>=.5, progress120<0; earlier distribution precedence',
         'selection':'first82 discovery engine PnL only','variants':variants,'chosen':chosen,
         'reference_full':econ([r['ref'] for r in rec]),'chosen_full':econ([r['chosen'] for r in rec]),
         'reference_validation':econ([r['ref'] for r in rec[82:]]),'chosen_validation':econ([r['chosen'] for r in rec[82:]]),
         'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years,'cases':cases}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
