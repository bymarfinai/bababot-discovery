"""BTC Friday15 A6.26 — causal online regime adaptation for still-open failure policy.

No entry filter, no threshold retuning, no validation-trained rule.
Frozen:
- all 138 Friday15 BUY entries
- parent TP2.0 / SL0.7 / max6h
- failed-thesis detector 60m + persistent120m
- if BUY already exited before120: A6.22 post-stop SHORT TP1.5 / SL0.5, immediate
- A6.15 distribution protection unchanged

Only the 12 historical confirmed-failure cases where BUY is still open at120 can choose among:
HOLD parent BUY, CUT at actual120 open, FLIP to SHORT TP1.3 / SL0.7.

ONLINE_EXPANDING rule:
- process Fridays chronologically
- first still-open event defaults to FLIP (the pre-existing balanced A6.22 policy)
- before every later still-open event, choose the policy with highest cumulative counterfactual PnL
  over ALL earlier completed still-open events; all policies have identical past sample count
- deterministic tie-break: FLIP, then HOLD, then CUT (preserve incumbent balanced behavior on ties)
- after the current Friday's original 6h horizon has completed, update cumulative scores for all
  three counterfactual policies; those scores are available before the next Friday

This is causal online adaptation: no future Friday is used to select the current action.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a623_stillopen_failure_policy as a623
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

H=120;HOLD=360;POSTSTOP_TP=1.5;POSTSTOP_SL=.5
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')
POLICIES=('HOLD','CUT','FLIP'); TIE=('FLIP','HOLD','CUT')

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
        r['stillopen']=r['wrongway'] and not r['prior_stop']
        r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
        r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
        r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
        if r['stillopen']:
            r['cf']={pol:a623.stillopen_action(rows,r,pol) for pol in POLICIES}
        rec.append(r)
    assert len(rec)==138

    def fixed_nonstill(r):
        if r['prior_stop']:
            j=r['i']+H//5
            return r['base']+a611.short_leg(rows,j,r['i']+HOLD//5,POSTSTOP_TP,POSTSTOP_SL)
        if r['dist_active']:return a613.protect_pnl(rows,r,r['sig'],a620.LOCK)
        return r['base']

    # static references
    for r in rec:
        r['a622']=r['cf']['FLIP'] if r['stillopen'] else fixed_nonstill(r)
        r['a623cut']=r['cf']['CUT'] if r['stillopen'] else fixed_nonstill(r)

    scores={p:0.0 for p in POLICIES};seen=0;events=[]
    for idx,r in enumerate(rec):
        if not r['stillopen']:
            r['online']=fixed_nonstill(r);continue
        before={p:scores[p] for p in POLICIES}
        if seen==0:
            choice='FLIP'
        else:
            # highest cumulative PnL; deterministic incumbent-first tie break
            best=max(scores.values())
            choice=next(p for p in TIE if abs(scores[p]-best)<1e-12)
        r['online']=r['cf'][choice];r['online_choice']=choice
        event={'date':ldt(r['ts']).date().isoformat(),'index':idx,'split':'D' if idx<82 else 'V','choice':choice,
               'scores_before':{p:rnd(before[p],3) for p in POLICIES},
               'counterfactual':{p:rnd(r['cf'][p],3) for p in POLICIES},
               'chosen_pnl':rnd(r['online'],3),'base_parent':rnd(r['base'],3)}
        # scores become available only after this completed Friday horizon
        for p in POLICIES:scores[p]+=r['cf'][p]
        seen+=1;event['scores_after']={p:rnd(scores[p],3) for p in POLICIES};events.append(event)

    def sub(q):
        return {'online':econ([r['online'] for r in q]),'a622_balanced':econ([r['a622'] for r in q]),
                'a623_cut':econ([r['a623cut'] for r in q]),
                'delta_vs_a622':rnd(sum(r['online']-r['a622'] for r in q),3),
                'delta_vs_parent':rnd(sum(r['online']-r['base'] for r in q),3),
                'stillopen_events':sum(r['stillopen'] for r in q),
                'choices':{p:sum(r.get('online_choice')==p for r in q) for p in POLICIES}}
    discovery=sub(rec[:82]);validation=sub(rec[82:]);full=sub(rec)
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
        blocks.append({'block':b+1,'parent':rnd(sum(r['base'] for r in q),3),'a622':rnd(sum(r['a622'] for r in q),3),
                       'online':rnd(sum(r['online'] for r in q),3),'delta_vs_parent':rnd(sum(r['online']-r['base'] for r in q),3),
                       'delta_vs_a622':rnd(sum(r['online']-r['a622'] for r in q),3),'stillopen':sum(r['stillopen'] for r in q)})
    years={}
    for y in sorted(set(ldt(r['ts']).year for r in rec)):
        q=[r for r in rec if ldt(r['ts']).year==y]
        years[str(y)]={'online':econ([r['online'] for r in q]),'a622':econ([r['a622'] for r in q]),'parent':econ([r['base'] for r in q]),
                       'delta_vs_a622':rnd(sum(r['online']-r['a622'] for r in q),3),'choices':{p:sum(r.get('online_choice')==p for r in q) for p in POLICIES}}
    out={'status':'FRIDAY15_A626_ONLINE_REGIME_POLICY','rule':'expanding past still-open counterfactual PnL; first event FLIP; tie FLIP>HOLD>CUT',
         'discovery':discovery,'validation':validation,'full':full,'blocks':blocks,
         'positive_parent_delta_blocks':sum(b['delta_vs_parent']>0 for b in blocks),
         'positive_a622_delta_blocks':sum(b['delta_vs_a622']>0 for b in blocks),'years':years,'events':events,
         'final_scores':{p:rnd(scores[p],3) for p in POLICIES}}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
