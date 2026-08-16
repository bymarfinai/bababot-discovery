"""BTC Friday15 A6.25 — economic break-even protection for post-stop SHORT rescue.

No entry filtering and no TP/SL retuning.
Frozen A6.22 balanced engine:
- every Friday15 BUY, TP2.0 / SL0.7 / max6h
- failure detector 60m + persistent 120m
- if BUY already exited before120: sequential SHORT immediately at120, TP1.5 / SL0.5
- if BUY still open at120: frozen A6.22 FLIP SHORT TP1.3 / SL0.7
- A6.15 distribution protection unchanged

New mechanism only on the post-stop SHORT:
The realized parent BUY SL is about -$4.25 net. A +1.0% gross SHORT move on $500 produces
about +$4.25 net after the same $0.75 roundtrip fee. Therefore +1.0% is the economic recovery
hinge where the second leg has repaid the first-leg loss.

Strict-causal protection:
- wait for a completed 5m candle to establish SHORT MFE >= +1.0%
- if TP1.5 or SL0.5 already occurred, they win under normal adverse-first semantics
- at the NEXT 5m open, arm a protective stop at the +1.0% SHORT price
- if the next open already retraced through the protection level, exit at that actual open
- otherwise retain TP1.5 while protection is active
- if protection and TP touch in same later 5m bar, protection is assumed first (conservative)

This threshold is economics-derived, not fitted to discovery or validation.
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

H=120;HOLD=360;NOTIONAL=500.;FEE_USD=.75
POST_TP=1.5;POST_SL=.5;RECOVERY_HINGE=1.0
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def econ(p):
    n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
            'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def exact_idx(rows,i,mins):
    j=i+mins//5
    if j>=len(rows) or rows[j][0]!=rows[i][0]+(mins//5)*TF:return None
    return j

def short_leg_econ_lock(rows,j,end,managed):
    e=rows[j][1];tp_px=e*(1-POST_TP/100);sl_px=e*(1+POST_SL/100);lock_px=e*(1-RECOVERY_HINGE/100)
    armed=False;hinge_k=None
    for k in range(j,end):
        x=rows[k]
        if not armed:
            ht=x[3]<=tp_px;hs=x[2]>=sl_px
            if ht and hs:return {'pnl':-POST_SL/100*NOTIONAL-FEE_USD,'reason':'SL','hinge':hinge_k,'protected':False}
            if hs:return {'pnl':-POST_SL/100*NOTIONAL-FEE_USD,'reason':'SL','hinge':hinge_k,'protected':False}
            if ht:return {'pnl':POST_TP/100*NOTIONAL-FEE_USD,'reason':'TP','hinge':hinge_k,'protected':False}
            if managed and x[3]<=lock_px:  # completed candle low establishes >=1.0% favorable MFE
                hinge_k=k
                decision=k+1
                if decision>=end:break
                op=rows[decision][1]
                if op>=lock_px:
                    pnl=(e-op)/e*NOTIONAL-FEE_USD
                    return {'pnl':pnl,'reason':'LOCK_LOST_AT_OPEN','hinge':hinge_k,'protected':True}
                armed=True
                # continue from the next candle, not retrospectively inside hinge candle
                continue
        else:
            # protection at +1.0 is adverse-side to current short; assume it before TP if both touch.
            if x[2]>=lock_px:
                return {'pnl':RECOVERY_HINGE/100*NOTIONAL-FEE_USD,'reason':'ECON_LOCK','hinge':hinge_k,'protected':True}
            if x[3]<=tp_px:
                return {'pnl':POST_TP/100*NOTIONAL-FEE_USD,'reason':'TP_AFTER_LOCK','hinge':hinge_k,'protected':True}
    px=rows[end][1];p=(e-px)/e*NOTIONAL-FEE_USD
    return {'pnl':p,'reason':'TIMEOUT','hinge':hinge_k,'protected':armed or hinge_k is not None}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
        r['wrongway']=a620.confirmed(rows,r,e7,e20)
        r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
        r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
        r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
        r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
        rec.append(r)
    assert len(rec)==138

    def final(r,managed):
        if r['wrongway']:
            if r['prior_stop']:
                j=exact_idx(rows,r['i'],H);end=exact_idx(rows,r['i'],HOLD)
                z=short_leg_econ_lock(rows,j,end,managed)
                return r['base']+z['pnl'],z
            return a620.wrongway_action(rows,r,1.3),None
        if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK),None
        return r['base'],None

    for r in rec:
        r['ref'],r['ref_leg']=final(r,False)
        r['new'],r['new_leg']=final(r,True)
    # hard parity sanity: unmanaged implementation should equal A6.22 engine result +128.989 within rounding
    assert abs(sum(r['ref'] for r in rec)-128.989)<0.02,(sum(r['ref'] for r in rec),128.989)

    def sub(q):
        z=[r for r in q if r['prior_stop']]
        hinges=[r for r in z if r['new_leg'] and r['new_leg']['hinge'] is not None]
        return {'reference':econ([r['ref'] for r in q]),'managed':econ([r['new'] for r in q]),
                'delta':rnd(sum(r['new']-r['ref'] for r in q),3),'poststop_n':len(z),
                'recovery_hinges':len(hinges),'protected_exits':sum(r['new_leg'] and r['new_leg']['protected'] for r in z),
                'loss_to_win':sum(r['ref']<=0 and r['new']>0 for r in z),
                'loss_to_zero_or_better':sum(r['ref']<0 and r['new']>=-1e-9 for r in z),
                'win_to_loss':sum(r['ref']>0 and r['new']<=0 for r in z),
                'winner_clipped':sum(r['ref']>0 and 0<r['new']<r['ref'] for r in z),
                'reasons':{reason:sum(r['new_leg'] and r['new_leg']['reason']==reason for r in z) for reason in ('SL','TP','TP_AFTER_LOCK','ECON_LOCK','LOCK_LOST_AT_OPEN','TIMEOUT')}}
    disc=sub(rec[:82]);val=sub(rec[82:]);full=sub(rec)
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
        blocks.append({'block':b+1,'reference':rnd(sum(r['ref'] for r in q),3),'new':rnd(sum(r['new'] for r in q),3),
                       'delta':rnd(sum(r['new']-r['ref'] for r in q),3),'hinges':sum(r['prior_stop'] and r['new_leg'] and r['new_leg']['hinge'] is not None for r in q)})
    years={}
    for y in sorted(set(ldt(r['ts']).year for r in rec)):
        q=[r for r in rec if ldt(r['ts']).year==y]
        years[str(y)]={'reference':econ([r['ref'] for r in q]),'new':econ([r['new'] for r in q]),
                       'delta':rnd(sum(r['new']-r['ref'] for r in q),3),'hinges':sum(r['prior_stop'] and r['new_leg'] and r['new_leg']['hinge'] is not None for r in q)}
    cases=[]
    for ix,r in enumerate(rec):
        if not r['prior_stop']:continue
        cases.append({'date':ldt(r['ts']).date().isoformat(),'split':'D' if ix<82 else 'V','base_buy':rnd(r['base'],3),
                      'ref_occ':rnd(r['ref'],3),'new_occ':rnd(r['new'],3),'ref_short':rnd(r['ref_leg']['pnl'],3),
                      'new_short':rnd(r['new_leg']['pnl'],3),'new_reason':r['new_leg']['reason'],
                      'hinge_min':None if r['new_leg']['hinge'] is None else (r['new_leg']['hinge']-r['i'])*5})
    out={'status':'FRIDAY15_A625_POSTSTOP_ECONOMIC_LOCK','mechanism':{'recovery_hinge_pct':RECOVERY_HINGE,'lock_pct':RECOVERY_HINGE,'poststop_tp':POST_TP,'poststop_sl':POST_SL},
         'discovery':disc,'validation':val,'full':full,'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks),'years':years,'cases':cases}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
