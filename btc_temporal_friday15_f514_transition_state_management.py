"""Friday T-Method F5.14 — Transition-State BUY Management.

Freeze F5.12 HIDDEN_CORE_EMA warning exactly and ask a different question after
F5.13 rejected direct BUY->SHORT reversal:

    Can the warning improve management of the existing Friday BUY without
    assuming an opposite-direction edge?

Hard constraints
----------------
- every Friday15 BUY entry is retained
- frozen parent TP2.0 / SL0.7 / hold360m
- F5.12 warning thresholds are unchanged
- NO SHORT
- NO entry filtering
- NO fitted numeric sweep
- 138-Friday portfolio retained; dates without usable futures metrics simply HOLD

Management families are deliberately mechanistic:
1) HALF_RISK_STOP: move SL from -0.70% to -0.35% (half original risk distance)
2) BE_IF_GREEN: if warning-open is above entry, move SL to entry; otherwise HOLD
3) LOCK_HALF_GAIN: if warning-open is above entry, lock half the current open gain
4) PARTIAL50: close half at warning, leave half on frozen parent
5) PARTIAL50_HALF_RISK: close half, manage remainder with -0.35% stop
6) TEMP_HALF_RISK: -0.35% stop only until the frozen hidden warning fully clears
7) TEMP_BE_IF_GREEN: break-even stop while warning persists if warning-open is green
8) TEMP_LOCK_HALF_GAIN: half-gain lock while warning persists if warning-open is green

Temporary governors release at the first later causal decision-open where the
exact F5.12 conjunction is false. They never reverse direction.

Discovery selects by PnL uplift only among positive-uplift policies. Validation
is report-only. Milestone PASS requires selected discovery policy to preserve
positive uplift in validation and not worsen full-sample max drawdown.
"""
import json, statistics
from collections import defaultdict

import btc_temporal_friday15_f511_hidden_state_reversal_forensics as F
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
from btc_temporal_a34_5m_events import rnd, ldt, TF
from btc_temporal_friday15_a60_money_geometry import trade, NOTIONAL, FEE_PCT, max_dd, loss_streak

BUY_TP=2.0; BUY_SL=0.7; BUY_HOLD=360
HALF_RISK=0.35
MIN_ACTIONS=5


def warning(e):
    f=e['feat']
    return (f.get('top_vs_global') is not None and f['top_vs_global']<=0 and
            f.get('top_account_chg_15') is not None and f['top_account_chg_15']<0 and
            f.get('global_account_chg_15') is not None and f['global_account_chg_15']<0 and
            f.get('ema_spread_chg15') is not None and f['ema_spread_chg15']<0)


def group_events(events):
    d=defaultdict(list)
    for e in events:d[e['entry_ts']].append(e)
    for k in d:d[k].sort(key=lambda z:z['ts'])
    return d


def first_warning(q):
    for n,e in enumerate(q):
        if warning(e):return n,e
    return None,None


def summarize(ps):
    if not ps:return {'n':0}
    pos=sum(x for x in ps if x>0);neg=-sum(x for x in ps if x<0)
    return {'n':len(ps),'wr':rnd(100*sum(x>0 for x in ps)/len(ps),2),
            'pnl':rnd(sum(ps),3),'exp':rnd(statistics.mean(ps),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(ps),3),
            'ls':loss_streak(ps)}


def pnl_at(entry,exit_px):
    gross=100*(exit_px/entry-1)
    return NOTIONAL*(gross-FEE_PCT)/100


def managed_leg(rows,i,j,stop_gross_pct,events_by_ts=None,temporary=False):
    """Manage a full-notional BUY from warning open j onward.

    stop_gross_pct is relative to original Friday entry (e.g. -0.35, 0, +0.2).
    If temporary=True, release back to original -0.70% at first later decision
    open where the exact F5.12 warning conjunction is false.
    """
    entry=rows[i][1];tp_px=entry*(1+BUY_TP/100);parent_sl=entry*(1-BUY_SL/100)
    stop_px=entry*(1+stop_gross_pct/100)
    end=min(len(rows),i+BUY_HOLD//5)
    active_stop=stop_px;released=False
    for k in range(j,end):
        if rows[k][0] != rows[i][0]+(k-i)*TF:return None
        if temporary and k>j and not released and events_by_ts is not None:
            ev=events_by_ts.get(rows[k][0])
            if ev is not None and not warning(ev):
                active_stop=parent_sl;released=True
        op=rows[k][1]
        if op<=active_stop:
            return {'net':pnl_at(entry,op),'reason':'OPEN_STOP','exit':op,'released':released}
        x=rows[k];hit_tp=x[2]>=tp_px;hit_sl=x[3]<=active_stop
        if hit_tp and hit_sl:
            return {'net':pnl_at(entry,active_stop),'reason':'SL_AMBIG','exit':active_stop,'released':released}
        if hit_sl:
            return {'net':pnl_at(entry,active_stop),'reason':'MANAGED_SL','exit':active_stop,'released':released}
        if hit_tp:
            return {'net':pnl_at(entry,tp_px),'reason':'TP','exit':tp_px,'released':released}
    if end<=j:return None
    ex=rows[end-1][4]
    return {'net':pnl_at(entry,ex),'reason':'TIMEOUT','exit':ex,'released':released}


def policies():
    return ['HALF_RISK_STOP','BE_IF_GREEN','LOCK_HALF_GAIN','PARTIAL50',
            'PARTIAL50_HALF_RISK','TEMP_HALF_RISK','TEMP_BE_IF_GREEN','TEMP_LOCK_HALF_GAIN']


def apply_policy(rows,i,parent,warning_event,q,kind):
    j=warning_event['j'];entry=rows[i][1];op=rows[j][1]
    progress=100*(op/entry-1)
    evmap={e['ts']:e for e in q}

    if kind=='HALF_RISK_STOP':
        z=managed_leg(rows,i,j,-HALF_RISK)
        return (z['net'],z['reason'],False) if z else None
    if kind=='BE_IF_GREEN':
        if progress<=0:return (parent['net_usd'],'NO_ACTION',False)
        z=managed_leg(rows,i,j,0.0)
        return (z['net'],z['reason'],False) if z else None
    if kind=='LOCK_HALF_GAIN':
        if progress<=0:return (parent['net_usd'],'NO_ACTION',False)
        z=managed_leg(rows,i,j,progress*0.5)
        return (z['net'],z['reason'],False) if z else None
    if kind=='PARTIAL50':
        now=pnl_at(entry,op)
        return (0.5*now+0.5*parent['net_usd'],'PARTIAL50',False)
    if kind=='PARTIAL50_HALF_RISK':
        now=pnl_at(entry,op);z=managed_leg(rows,i,j,-HALF_RISK)
        if z is None:return None
        return (0.5*now+0.5*z['net'],'PARTIAL50_HALF_RISK',False)
    if kind=='TEMP_HALF_RISK':
        z=managed_leg(rows,i,j,-HALF_RISK,evmap,True)
        return (z['net'],z['reason'],z['released']) if z else None
    if kind=='TEMP_BE_IF_GREEN':
        if progress<=0:return (parent['net_usd'],'NO_ACTION',False)
        z=managed_leg(rows,i,j,0.0,evmap,True)
        return (z['net'],z['reason'],z['released']) if z else None
    if kind=='TEMP_LOCK_HALF_GAIN':
        if progress<=0:return (parent['net_usd'],'NO_ACTION',False)
        z=managed_leg(rows,i,j,progress*0.5,evmap,True)
        return (z['net'],z['reason'],z['released']) if z else None
    raise ValueError(kind)


def evaluate(rows,all_entries,groups,keys,kind):
    ps=[];ms=[];acts=[]
    keyset=set(keys)
    for i in all_entries:
        ts=rows[i][0]
        if ts not in keyset:continue
        p=trade(rows,i,BUY_TP,BUY_SL,BUY_HOLD)
        if p is None:continue
        base=p['net_usd'];managed=base
        q=groups.get(ts,[]);wi,we=first_warning(q)
        if we is not None:
            a=apply_policy(rows,i,p,we,q,kind)
            if a is not None:
                managed,reason,released=a
                changed=abs(managed-base)>1e-12
                if changed:
                    acts.append({'date':ldt(ts).strftime('%Y-%m-%d'),'entry_ts':ts,
                                 'warning_minute':we['minute'],'parent':base,'managed':managed,
                                 'delta':managed-base,'parent_reason':p['reason'],
                                 'manage_reason':reason,'released':released,
                                 'warning_progress':100*(rows[we['j']][1]/rows[i][1]-1)})
        ps.append(base);ms.append(managed)
    b=summarize(ps);m=summarize(ms)
    improved=[a for a in acts if a['delta']>0];damaged=[a for a in acts if a['delta']<0]
    return {'entries':len(ps),'warnings':sum(first_warning(groups.get(k,[]))[1] is not None for k in keys),
            'actions':len(acts),'parent':b,'managed':m,'delta':rnd(m['pnl']-b['pnl'],3),
            'dd_delta':rnd(m['mdd']-b['mdd'],3),
            'improved_actions':len(improved),'damaged_actions':len(damaged),
            'action_gain':rnd(sum(a['delta'] for a in improved),3),
            'action_damage':rnd(sum(a['delta'] for a in damaged),3),
            'parent_tp_actions':sum(a['parent_reason']=='TP' for a in acts),
            'parent_sl_actions':sum(a['parent_reason'] in ('SL','AMB_SL') for a in acts),
            'released_actions':sum(a['released'] for a in acts),
            'examples_best':sorted(acts,key=lambda a:a['delta'],reverse=True)[:8],
            'examples_worst':sorted(acts,key=lambda a:a['delta'])[:8]}


def main():
    rows,e7,e20,cache,events,occ=F.build_events()
    groups=group_events(events)
    all_entries=F57.indices(rows)
    all_keys=[rows[i][0] for i in all_entries]
    split=int(len(all_keys)*.60);disc_keys=all_keys[:split];val_keys=all_keys[split:]
    result={}
    for kind in policies():
        d=evaluate(rows,all_entries,groups,disc_keys,kind)
        v=evaluate(rows,all_entries,groups,val_keys,kind)
        full=evaluate(rows,all_entries,groups,all_keys,kind)
        result[kind]={'discovery':d,'validation':v,'full':full}
    eligible=[k for k in policies() if result[k]['discovery']['actions']>=MIN_ACTIONS and result[k]['discovery']['delta']>0]
    ranked=sorted(eligible,key=lambda k:result[k]['discovery']['delta'],reverse=True)
    selected=ranked[0] if ranked else None
    passed=False;verdict='NO_DISCOVERY_MANAGEMENT_CANDIDATE'
    if selected:
        d=result[selected]['discovery'];v=result[selected]['validation'];f=result[selected]['full']
        passed=(v['actions']>=MIN_ACTIONS and v['delta']>0 and f['managed']['mdd']<=f['parent']['mdd'])
        verdict='CROSS_PERIOD_BUY_MANAGEMENT' if passed else 'DISCOVERY_CANDIDATE_VALIDATION_OR_DD_FAILED'
    baseline=evaluate(rows,all_entries,groups,all_keys,'PARTIAL50')['parent']
    out={'status':'FRIDAY_TMETHOD_F514_TRANSITION_STATE_MANAGEMENT',
         'design':{'warning':'F5.12 HIDDEN_CORE_EMA frozen','entry_filter':False,'short':False,
                   'all_fridays':len(all_keys),'discovery_n':len(disc_keys),'validation_n':len(val_keys),
                   'metrics_warning_coverage':len(groups),'missing_metrics_action':'HOLD_PARENT',
                   'policies':policies(),'half_risk_stop_pct':-HALF_RISK,
                   'temporary_release':'first later causal decision-open where exact F5.12 warning is false',
                   'selection':'discovery PnL uplift only; validation report-only',
                   'pass_gate':'selected validation uplift >0, >=5 validation actions, full MDD not worse'},
         'baseline_parent':baseline,'results':result,'discovery_rank':ranked,
         'selected_discovery':selected,'milestone_pass':passed,'verdict':verdict,
         'notes':'All 138 Friday entries retained. No warning threshold sweep. No SHORT. Temporary governors use only causal recovery information.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
