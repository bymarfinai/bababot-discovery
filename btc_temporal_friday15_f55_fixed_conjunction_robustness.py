"""Friday T-Method F5.5 — robustness of the fixed F5.4 conjunction.

FROZEN candidate from F5.4 (no retuning here):
- all Friday 15:00 WIB BUY entries retained
- parent TP2.0 / SL0.7 / hold6h
- after causal +0.50% MFE hinge, PROTECT +0.20% only when:
    range_ratio >= 2.683993
    AND pre_eff240 >= 0.165628
- otherwise remain RUNNER.

F5.5 only measures metrics, chronology concentration, leave-one-block-out uplift,
and incremental execution-cost stress. It does not select a new threshold.
"""
import json
import btc_temporal_friday15_f52_runner_protect as F
import btc_temporal_friday15_f53_separability_attribution as A
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

RANGE=2.683993
EFF240=0.165628


def fire(r):
    s=r.get('state')
    return bool(s is not None and r.get('protect') is not None and
                s.get('range_ratio') is not None and s.get('pre_eff240') is not None and
                s['range_ratio']>=RANGE and s['pre_eff240']>=EFF240)


def materialize(recs,extra_cost=0.0):
    out=[]; actions=0; true_gain=false_damage=0.0; improved=worsened=0
    for r in recs:
        final=r['base']
        if fire(r):
            actions+=1; final=r['protect']-extra_cost
            d=r['protect']-r['base']
            if d>0:true_gain+=d;improved+=1
            elif d<0:false_damage+=-d;worsened+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':final})
    z=F.summarize(out); b=F.summarize(out,'base')
    z.update({'base_pnl':b['pnl'],'delta':rnd(z['pnl']-b['pnl'],3),'actions':actions,
              'improved_actions':improved,'worsened_actions':worsened,
              'true_gain_usd':rnd(true_gain,3),'false_damage_usd':rnd(false_damage,3),
              'gain_damage_ratio':rnd(true_gain/false_damage,3) if false_damage else None,
              'extra_cost_per_action':extra_cost})
    return z


def block_rows(recs):
    out=[]
    for b in range(8):
        q=[r for r in recs if min(7,max(0,int((r['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        z=materialize(q) if q else {'delta':0,'actions':0,'pnl':0,'base_pnl':0}
        out.append({'block':b+1,'n':len(q),'delta':z['delta'],'actions':z['actions'],
                    'pnl':z['pnl'],'base_pnl':z['base_pnl']})
    return out


def year_rows(recs):
    yrs=sorted(set(ldt(r['ts']).year for r in recs)); out=[]
    for y in yrs:
        q=[r for r in recs if ldt(r['ts']).year==y]; z=materialize(q)
        out.append({'year':y,'n':len(q),'delta':z['delta'],'actions':z['actions'],
                    'wr':z['wr'],'pnl':z['pnl'],'base_pnl':z['base_pnl'],'pf':z['pf']})
    return out


def action_rows(recs):
    out=[]
    for r in recs:
        if not fire(r):continue
        s=r['state']; d=r['protect']-r['base']
        out.append({'date':ldt(r['ts']).strftime('%Y-%m-%d'),'base':rnd(r['base'],3),'protect':rnd(r['protect'],3),
                    'delta':rnd(d,3),'range_ratio':rnd(s['range_ratio'],3),'pre_eff240':rnd(s['pre_eff240'],3),
                    'better':'PROTECT' if d>0 else 'RUNNER'})
    return out


def main():
    rows=load(); fi=A.make_indices(rows,4,15); recs=A.enrich(rows,F.build(rows,fi)); disc,val=A.split_records(recs)
    full=materialize(recs); blocks=block_rows(recs)
    total_delta=full['delta']; loo=[]
    for b in blocks:
        loo.append({'drop_block':b['block'],'remaining_delta':rnd(total_delta-b['delta'],3)})
    stress=[]
    for c in (0.05,0.10,0.15,0.25,0.50,0.75,1.00):
        stress.append(materialize(recs,c))
    out={'status':'FRIDAY_TMETHOD_F55_FIXED_CONJUNCTION_ROBUSTNESS',
         'frozen_rule':{'range_ratio_min':RANGE,'pre_eff240_min':EFF240,'hinge':0.50,'lock':0.20},
         'baseline':{'discovery':materialize(disc,999999)['base_pnl'],'validation':materialize(val,999999)['base_pnl'],'full':materialize(recs,999999)['base_pnl']},
         'candidate':{'discovery':materialize(disc),'validation':materialize(val),'full':full},
         'blocks':blocks,'leave_one_block_out':loo,'years':year_rows(recs),
         'cost_stress':stress,'actions':action_rows(recs),
         'notes':'Fixed F5.4 candidate only; no threshold selection. Still not fresh OOS because F5.4 architecture followed F5.3.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
