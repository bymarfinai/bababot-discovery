"""Friday T-Method F5.16 — Persistent-State Economic Management Test.

F5.15 showed that first-warning persistence, especially sustained EMA contraction,
separates eventual Friday BUY deterioration better than acting on the first F5.12
warning. F5.16 tests whether that information is economically actionable.

Frozen design
-------------
- every Friday15 BUY retained
- parent TP2.0 / SL0.7 / hold360m unchanged
- F5.12 HIDDEN_CORE_EMA warning unchanged
- NO SHORT and NO entry filtering
- two predeclared persistence states only:
    P15: warning remains continuously true through +15m after first warning
    P20: warning remains continuously true through +20m after first warning
- management starts only at the causal decision open at +15m / +20m
- if warning recovered earlier, or parent is no longer alive, HOLD parent
- no numeric threshold sweep

Management actions match the simple permanent F5.14 families:
- HALF_RISK_STOP: SL -0.70 -> -0.35
- BE_IF_GREEN: if execution open > entry, stop to entry
- LOCK_HALF_GAIN: if green, lock half current open gain
- PARTIAL50: close half, leave half on parent
- PARTIAL50_HALF_RISK: close half + -0.35 stop on remainder

Selection is discovery-only by PnL uplift. Validation is report-only.
PASS requires selected discovery candidate to retain positive validation uplift,
>=5 validation actions, positive full uplift, and full max drawdown not worse.
"""
import json

import btc_temporal_friday15_f511_hidden_state_reversal_forensics as F
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
import btc_temporal_friday15_f514_transition_state_management as M
from btc_temporal_friday15_a60_money_geometry import trade
from btc_temporal_a34_5m_events import ldt, rnd

BUY_TP=2.0; BUY_SL=0.7; BUY_HOLD=360
PERSISTENCE_MIN=(15,20)
POLICIES=('HALF_RISK_STOP','BE_IF_GREEN','LOCK_HALF_GAIN','PARTIAL50','PARTIAL50_HALF_RISK')
MIN_ACTIONS=5


def persistent_execution(q,mins):
    """Return causal execution event iff warning stays continuously true through mins."""
    wi,we=M.first_warning(q)
    if we is None:return None
    target=we['ts']+mins*60000
    seen=[]
    for e in q[wi:]:
        if e['ts']>target:break
        seen.append(e)
        if not M.warning(e):return None
    if not seen or seen[-1]['ts']!=target:return None
    # Exact 5m observations including t0 and target.
    need=mins//5+1
    if len(seen)!=need:return None
    return seen[-1]


def evaluate(rows,all_entries,groups,keys,mins,kind):
    keyset=set(keys);base=[];managed=[];acts=[];states=0
    for i in all_entries:
        ts=rows[i][0]
        if ts not in keyset:continue
        p=trade(rows,i,BUY_TP,BUY_SL,BUY_HOLD)
        if p is None:continue
        b=p['net_usd'];m=b
        q=groups.get(ts,[])
        ex=persistent_execution(q,mins) if q else None
        if ex is not None:
            states+=1
            a=M.apply_policy(rows,i,p,ex,q,kind)
            if a is not None:
                m,reason,released=a
                if abs(m-b)>1e-12:
                    acts.append({'date':ldt(ts).strftime('%Y-%m-%d'),'entry_ts':ts,
                                 'first_warning_minute':M.first_warning(q)[1]['minute'],
                                 'execution_minute':ex['minute'],'parent':b,'managed':m,
                                 'delta':m-b,'parent_reason':p['reason'],'manage_reason':reason,
                                 'execution_progress':100*(rows[ex['j']][1]/rows[i][1]-1)})
        base.append(b);managed.append(m)
    bs=M.summarize(base);ms=M.summarize(managed)
    imp=[a for a in acts if a['delta']>0];dmg=[a for a in acts if a['delta']<0]
    return {'entries':len(base),'persistent_states':states,'actions':len(acts),
            'parent':bs,'managed':ms,'delta':rnd(ms['pnl']-bs['pnl'],3),
            'dd_delta':rnd(ms['mdd']-bs['mdd'],3),
            'improved_actions':len(imp),'damaged_actions':len(dmg),
            'action_gain':rnd(sum(a['delta'] for a in imp),3),
            'action_damage':rnd(sum(a['delta'] for a in dmg),3),
            'parent_tp_actions':sum(a['parent_reason']=='TP' for a in acts),
            'parent_sl_actions':sum(a['parent_reason'] in ('SL','AMB_SL') for a in acts),
            'best_examples':sorted(acts,key=lambda a:a['delta'],reverse=True)[:6],
            'worst_examples':sorted(acts,key=lambda a:a['delta'])[:6]}


def main():
    rows,e7,e20,cache,events,occ=F.build_events()
    groups=M.group_events(events)
    all_entries=F57.indices(rows)
    all_keys=[rows[i][0] for i in all_entries]
    split=int(len(all_keys)*.60);disc=all_keys[:split];val=all_keys[split:]
    results={};candidates=[]
    for mins in PERSISTENCE_MIN:
        for kind in POLICIES:
            name=f'P{mins}_{kind}'
            d=evaluate(rows,all_entries,groups,disc,mins,kind)
            v=evaluate(rows,all_entries,groups,val,mins,kind)
            f=evaluate(rows,all_entries,groups,all_keys,mins,kind)
            results[name]={'persistence_min':mins,'policy':kind,
                           'discovery':d,'validation':v,'full':f}
            if d['actions']>=MIN_ACTIONS and d['delta']>0:
                candidates.append(name)
    ranked=sorted(candidates,key=lambda n:results[n]['discovery']['delta'],reverse=True)
    selected=ranked[0] if ranked else None
    passed=False;verdict='NO_DISCOVERY_PERSISTENT_MANAGEMENT_CANDIDATE'
    if selected:
        r=results[selected];v=r['validation'];f=r['full']
        passed=(v['actions']>=MIN_ACTIONS and v['delta']>0 and
                f['delta']>0 and f['managed']['mdd']<=f['parent']['mdd'])
        verdict='CROSS_PERIOD_PERSISTENT_MANAGEMENT' if passed else 'DISCOVERY_CANDIDATE_VALIDATION_OR_DD_FAILED'
    baseline=M.summarize([trade(rows,i,BUY_TP,BUY_SL,BUY_HOLD)['net_usd'] for i in all_entries])
    out={'status':'FRIDAY_TMETHOD_F516_PERSISTENT_STATE_ECONOMIC_MANAGEMENT',
         'design':{'all_fridays':len(all_keys),'discovery_n':len(disc),'validation_n':len(val),
                   'warning':'F5.12 HIDDEN_CORE_EMA frozen','entry_filter':False,'short':False,
                   'persistence_min':PERSISTENCE_MIN,
                   'persistence_definition':'continuous warning from first warning through exact +15m/+20m causal decision open',
                   'policies':POLICIES,'selection':'discovery PnL uplift only; validation report-only',
                   'pass_gate':'selected validation uplift >0, >=5 validation actions, full uplift >0, full MDD not worse'},
         'baseline_parent':baseline,'results':results,'discovery_rank':ranked,
         'selected_discovery':selected,'milestone_pass':passed,'verdict':verdict,
         'notes':'No warning/persistence threshold tuning beyond predeclared P15/P20. All Fridays retained; nonpersistent/missing-metrics occurrences HOLD parent.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
