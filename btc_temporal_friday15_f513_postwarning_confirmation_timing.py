"""Friday T-Method F5.13 — Post-Warning Confirmation Timing.

Freeze F5.12 HIDDEN_CORE_EMA exactly. No warning threshold retuning.
Goal: determine whether a causal event AFTER the warning turns the warning into an
executable BUY->SHORT reversal, or whether the warning is only useful as context.

Frozen components
-----------------
Parent: Friday15 BUY TP2.0 / SL0.7 / hold360m.
Warning (F5.12 HIDDEN_CORE_EMA):
  top_vs_global <= 0
  top_account_chg_15 < 0
  global_account_chg_15 < 0
  ema_spread_chg15 < 0
SHORT diagnostic geometry: TP0.7 / SL0.7 / hold180m, own round-trip fee.

Confirmation families are compact and use natural zero/sign crossings only:
- fixed delay: 0/5/10/15/20m after warning
- first red completed 5m bar
- first bearish structure bar: red + low below prior low
- first seller-flow confirmation: ret5 < 0 and taker_imb5 < 0
- first EMA deterioration: completed price below EMA7 while EMA spread still contracting
- first dual confirmation: seller-flow + EMA deterioration

For each confirmation compare:
1) HOLD_PARENT
2) EXIT_ONLY at execution open
3) REVERSE = EXIT_ONLY + fixed SHORT leg

A reversal is economically valid only if REVERSE improves parent and EXIT_ONLY,
while standalone SHORT legs are positive. Discovery selection only; validation is
report-only.
"""
import json, statistics
from collections import defaultdict

import btc_temporal_friday15_f511_hidden_state_reversal_forensics as F
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
from btc_temporal_a34_5m_events import rnd, ldt
from btc_temporal_friday15_a60_money_geometry import max_dd, loss_streak

MIN_ACTIONS=5
DELAYS=(0,5,10,15,20)


def med(v):
    v=[x for x in v if x is not None]
    return statistics.median(v) if v else None


def summarize(ps):
    if not ps:return {'n':0}
    pos=sum(x for x in ps if x>0); neg=-sum(x for x in ps if x<0)
    return {'n':len(ps),'wr':rnd(100*sum(x>0 for x in ps)/len(ps),2),
            'pnl':rnd(sum(ps),3),'exp':rnd(statistics.mean(ps),4),
            'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(max_dd(ps),3),'ls':loss_streak(ps)}


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
    for idx,e in enumerate(q):
        if warning(e):return idx,e
    return None,None


def bar_state(rows,e):
    j=e['j']
    if j<2:return {}
    last=rows[j-1]; prev=rows[j-2]
    red=last[4] < last[1]
    lower_low=last[3] < prev[3]
    px=last[4]
    f=e['feat']
    ema_below7=(f.get('ema7_dist') is not None and f['ema7_dist']<0)
    ema_contract=(f.get('ema_spread_chg15') is not None and f['ema_spread_chg15']<0)
    seller=(f.get('ret_5') is not None and f.get('taker_imb_5') is not None and
            f['ret_5']<0 and f['taker_imb_5']<0)
    return {'red':red,'lower_low':lower_low,'seller':seller,
            'ema_deterioration':ema_below7 and ema_contract,'px':px}


def executor(rows,q,widx,kind):
    w=q[widx]
    if kind.startswith('DELAY_'):
        delay=int(kind.split('_')[1])
        target=w['ts']+delay*60000
        for e in q[widx:]:
            if e['ts']==target:return e
            if e['ts']>target:return None
        return None
    # Confirmation must occur strictly after the warning, except there is a separate DELAY_0 baseline.
    for e in q[widx+1:]:
        s=bar_state(rows,e)
        if kind=='FIRST_RED' and s.get('red'):return e
        if kind=='BEAR_STRUCTURE' and s.get('red') and s.get('lower_low'):return e
        if kind=='SELLER_FLOW' and s.get('seller'):return e
        if kind=='EMA_DETERIORATION' and s.get('ema_deterioration'):return e
        if kind=='SELLER_PLUS_EMA' and s.get('seller') and s.get('ema_deterioration'):return e
    return None


def kinds():
    return [f'DELAY_{d}' for d in DELAYS]+['FIRST_RED','BEAR_STRUCTURE','SELLER_FLOW','EMA_DETERIORATION','SELLER_PLUS_EMA']


def action(rows,e):
    buy=F57.buy_close_pnl(rows[e['i']][1],rows[e['j']][1])
    short=F57.short_trade(rows,e['j'])
    if short is None:return None
    return {'buy_close':buy,'short':short['net_usd'],'reverse':buy+short['net_usd'],
            'short_reason':short['reason'],'minute':e['minute'],'date':e['date']}


def evaluate(rows,groups,keys,kind):
    parent=[]; exit_port=[]; reverse_port=[]; acts=[]
    for k in keys:
        q=groups.get(k,[])
        if not q:continue
        p=q[0]['parent']; parent.append(p)
        wi,we=first_warning(q)
        if we is None:
            exit_port.append(p);reverse_port.append(p);continue
        ex=executor(rows,q,wi,kind)
        if ex is None:
            exit_port.append(p);reverse_port.append(p);continue
        a=action(rows,ex)
        if a is None:
            exit_port.append(p);reverse_port.append(p);continue
        acts.append({'entry_ts':k,'parent':p,'parent_reason':q[0]['parent_reason'],
                     'warning_minute':we['minute'],**a})
        exit_port.append(a['buy_close']);reverse_port.append(a['reverse'])
    b=summarize(parent);x=summarize(exit_port);r=summarize(reverse_port)
    short_sum=sum(a['short'] for a in acts); short_wr=(100*sum(a['short']>0 for a in acts)/len(acts)) if acts else None
    out={'actions':len(acts),'warning_entries':sum(first_warning(groups.get(k,[]))[1] is not None for k in keys),
         'median_warning_minute':rnd(med([a['warning_minute'] for a in acts]),2),
         'median_exec_minute':rnd(med([a['minute'] for a in acts]),2),
         'parent':b,'exit_only':x,'reverse':r,
         'exit_delta':rnd(x.get('pnl',0)-b.get('pnl',0),3),
         'reverse_delta':rnd(r.get('pnl',0)-b.get('pnl',0),3),
         'reverse_vs_exit':rnd(r.get('pnl',0)-x.get('pnl',0),3),
         'short_leg_pnl':rnd(short_sum,3),'short_leg_wr':rnd(short_wr,2),
         'parent_tp_actions':sum(a['parent_reason']=='TP' for a in acts),
         'parent_sl_actions':sum(a['parent_reason'].startswith('SL') for a in acts)}
    return out,acts


def acceptable(m):
    return (m['actions']>=MIN_ACTIONS and m['reverse_delta']>0 and
            m['reverse_vs_exit']>0 and m['short_leg_pnl']>0)


def score(m):
    if not acceptable(m):return -1e9
    # Pure economic discovery ranking; tie-break implicitly by fewer actions through no extra bonus.
    return m['reverse_delta']


def main():
    rows,e7,e20,cache,events,occ=F.build_events()
    groups=group_events(events);keys=sorted(groups);cut=keys[int(len(keys)*.60)]
    disc=[k for k in keys if k<cut];val=[k for k in keys if k>=cut]
    result={}
    for kind in kinds():
        d,_=evaluate(rows,groups,disc,kind);v,_=evaluate(rows,groups,val,kind);f,acts=evaluate(rows,groups,keys,kind)
        result[kind]={'discovery':d,'validation':v,'full':f}
    ranked=sorted(kinds(),key=lambda z:score(result[z]['discovery']),reverse=True)
    selected=ranked[0] if ranked and score(result[ranked[0]]['discovery'])>-1e8 else None
    pass_flag=False; verdict='NO_DISCOVERY_EXECUTION_CANDIDATE'
    if selected:
        d=result[selected]['discovery'];v=result[selected]['validation']
        # Validation must preserve all three economic signs; no validation selection.
        pass_flag=(acceptable(d) and v['actions']>=MIN_ACTIONS and v['reverse_delta']>0 and
                   v['reverse_vs_exit']>0 and v['short_leg_pnl']>0)
        verdict='CROSS_PERIOD_EXECUTION_CONFIRMATION' if pass_flag else 'DISCOVERY_CANDIDATE_VALIDATION_FAILED'
    out={'status':'FRIDAY_TMETHOD_F513_POSTWARNING_CONFIRMATION_TIMING',
         'design':{'warning':'F5.12 HIDDEN_CORE_EMA frozen','short_geometry':'TP0.7 SL0.7 hold180m frozen',
                   'confirmations':kinds(),'split_cut_date':ldt(cut).strftime('%Y-%m-%d'),
                   'selection':'discovery reverse_delta only among rules where REVERSE>parent, REVERSE>EXIT_ONLY, standalone SHORT>0, actions>=5',
                   'validation':'report-only; same three economic signs required for milestone PASS'},
         'results':result,'discovery_rank':ranked,'selected_discovery':selected,
         'milestone_pass':pass_flag,'verdict':verdict,
         'notes':'No warning thresholds or SHORT geometry retuned. Confirmation features use only completed bars available before execution open.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
