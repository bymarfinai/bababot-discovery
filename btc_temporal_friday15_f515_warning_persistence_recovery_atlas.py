"""Friday T-Method F5.15 — Warning Persistence & Recovery Atlas.

F5.12 found a causal first REVERSAL_WARNING, while F5.13/F5.14 showed that acting
on the first warning (SHORT or defensive BUY management) is too early and clips
runners. F5.15 asks whether the trajectory AFTER first warning separates:

    transient fragility -> recovery / runner
    persistent deterioration -> parent loss / SL / future reversal window

This milestone is FORENSICS ONLY:
- no trading action
- no entry filter
- F5.12 HIDDEN_CORE_EMA warning is frozen exactly
- no fitted threshold sweep
- 60/40 chronological discovery/validation reporting

Trajectory features are causal at their stated horizons after the first warning.
"""
import json, statistics
from collections import defaultdict

import btc_temporal_friday15_f511_hidden_state_reversal_forensics as F
from btc_temporal_a34_5m_events import rnd, ldt

HORIZONS=(15,30,60,120)


def med(xs):
    xs=[x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def mean(xs):
    xs=[x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def sigs(e):
    f=e['feat']
    rel=(f.get('top_vs_global') is not None and f['top_vs_global']<=0)
    acct=(f.get('top_account_chg_15') is not None and f.get('global_account_chg_15') is not None and
          f['top_account_chg_15']<0 and f['global_account_chg_15']<0)
    ema=(f.get('ema_spread_chg15') is not None and f['ema_spread_chg15']<0)
    return rel,acct,ema


def warning(e):
    a,b,c=sigs(e)
    return a and b and c


def group_events(events):
    d=defaultdict(list)
    for e in events:d[e['entry_ts']].append(e)
    for k in d:d[k].sort(key=lambda z:z['ts'])
    return d


def first_warning(q):
    for i,e in enumerate(q):
        if warning(e):return i,e
    return None,None


def future_good(q,start_idx,h):
    t=q[start_idx]['ts']
    return any(e['good'] and 0<=e['ts']-t<=h*60000 for e in q[start_idx:])


def auc(vals,labels):
    q=[(v,int(y)) for v,y in zip(vals,labels) if v is not None]
    pos=[v for v,y in q if y];neg=[v for v,y in q if not y]
    if not pos or not neg:return None
    s=0.0
    for a in pos:
        for b in neg:
            if a>b:s+=1
            elif a==b:s+=.5
    return s/(len(pos)*len(neg))


def consecutive_run(q,wi):
    n=0
    for e in q[wi:]:
        if warning(e):n+=1
        else:break
    return n


def first_recovery_idx(q,wi):
    for j in range(wi+1,len(q)):
        if not warning(q[j]):return j
    return None


def longest_true_run(flags):
    best=cur=0
    for x in flags:
        if x:cur+=1;best=max(best,cur)
        else:cur=0
    return best


def transitions(flags):
    # false->true transitions after the first element.
    return sum((not flags[i-1]) and flags[i] for i in range(1,len(flags)))


def window_events(q,wi,h):
    t=q[wi]['ts'];end=t+h*60000
    return [e for e in q[wi:] if e['ts']<=end]


def trajectory(q,wi):
    we=q[wi]
    rel0,acct0,ema0=sigs(we)
    run=consecutive_run(q,wi)
    ri=first_recovery_idx(q,wi)
    rec=q[ri] if ri is not None else None
    rec_rel=rec_acct=rec_ema=None
    if rec is not None:
        rr,aa,ee=sigs(rec)
        rec_rel=not rr;rec_acct=not aa;rec_ema=not ee
    out={
      'first_warning_minute':we['minute'],
      'initial_run_bars':run,
      'initial_run_min':run*5,
      'time_to_recovery_min':(q[ri]['ts']-we['ts'])/60000 if ri is not None else None,
      'no_recovery_in_observed_path':ri is None,
      'recovery_rel_first':rec_rel,
      'recovery_acct_first':rec_acct,
      'recovery_ema_first':rec_ema,
    }
    for h in HORIZONS:
        z=window_events(q,wi,h)
        flags=[warning(e) for e in z]
        rel=[sigs(e)[0] for e in z];acct=[sigs(e)[1] for e in z];ema=[sigs(e)[2] for e in z]
        n=len(z)
        out[f'eligible_bars_{h}']=n
        out[f'warning_share_{h}']=sum(flags)/n if n else None
        out[f'longest_warning_run_{h}']=longest_true_run(flags) if n else None
        out[f'rewarning_count_{h}']=transitions(flags) if n else None
        out[f'rel_share_{h}']=sum(rel)/n if n else None
        out[f'acct_share_{h}']=sum(acct)/n if n else None
        out[f'ema_share_{h}']=sum(ema)/n if n else None
        out[f'full_warning_at_horizon_{h}']=bool(flags[-1]) if flags else None
        out[f'no_recovery_{h}']=all(flags) if n else None
        out[f'future_good_{h}']=future_good(q,wi,h)
    # Natural, predeclared state summaries. These are descriptive bins, not tuned rules.
    out['persist_10m']=run>=2
    out['persist_15m']=run>=3
    out['persist_20m']=run>=4
    out['recover_within_10m']=(out['time_to_recovery_min'] is not None and out['time_to_recovery_min']<=10)
    out['recover_within_20m']=(out['time_to_recovery_min'] is not None and out['time_to_recovery_min']<=20)
    out['rewarn_after_recovery_60']=bool(ri is not None and any(warning(e) for e in q[ri+1:] if e['ts']<=we['ts']+60*60000))
    return out


def build_records(events,occ):
    groups=group_events(events)
    om={o['entry_ts']:o for o in occ}
    rec=[]
    for k,q in groups.items():
        wi,we=first_warning(q)
        if we is None:continue
        o=om.get(k)
        if o is None:continue
        t=trajectory(q,wi)
        t.update({
          'entry_ts':k,'date':we['date'],
          'parent':o['parent'],'parent_reason':o['parent_reason'],
          'parent_sl':o['parent_reason'] in ('SL','AMB_SL'),
          'parent_tp':o['parent_reason']=='TP',
          'parent_loss':o['parent']<=0,
          'strong_oracle':o['strong'],
        })
        rec.append(t)
    rec.sort(key=lambda x:x['entry_ts'])
    return rec


def cohort(rows,label):
    n=len(rows)
    if not n:return {'n':0}
    return {
      'n':n,
      'parent_sl_rate':rnd(sum(r['parent_sl'] for r in rows)/n,3),
      'parent_tp_rate':rnd(sum(r['parent_tp'] for r in rows)/n,3),
      'parent_loss_rate':rnd(sum(r['parent_loss'] for r in rows)/n,3),
      'strong_oracle_rate':rnd(sum(r['strong_oracle'] for r in rows)/n,3),
      'future_good_60_rate':rnd(sum(r['future_good_60'] for r in rows)/n,3),
      'median_initial_run_min':rnd(med([r['initial_run_min'] for r in rows]),2),
      'median_recovery_min':rnd(med([r['time_to_recovery_min'] for r in rows]),2),
      'median_warning_share_60':rnd(med([r['warning_share_60'] for r in rows]),3),
      'median_rel_share_60':rnd(med([r['rel_share_60'] for r in rows]),3),
      'median_acct_share_60':rnd(med([r['acct_share_60'] for r in rows]),3),
      'median_ema_share_60':rnd(med([r['ema_share_60'] for r in rows]),3),
    }


def compare_continuous(rows,features,label):
    out=[]
    labs=[r[label] for r in rows]
    for f in features:
        vals=[r.get(f) for r in rows]
        a=auc(vals,labs)
        if a is None:continue
        pos=[r.get(f) for r in rows if r[label] and r.get(f) is not None]
        neg=[r.get(f) for r in rows if not r[label] and r.get(f) is not None]
        out.append({'feature':f,'auc':rnd(a,4),'positive_median':rnd(med(pos),4),'negative_median':rnd(med(neg),4)})
    return out


def boolean_state_table(rows,states):
    base=cohort(rows,'BASE')
    out={}
    for s in states:
        yes=[r for r in rows if r.get(s) is True]
        no=[r for r in rows if r.get(s) is False]
        y=cohort(yes,s);n=cohort(no,'NOT_'+s)
        if y.get('n',0):
            bsl=base.get('parent_sl_rate') or 0
            bl=base.get('parent_loss_rate') or 0
            y['sl_lift_vs_warned_base']=rnd(y['parent_sl_rate']/bsl,3) if bsl else None
            y['loss_lift_vs_warned_base']=rnd(y['parent_loss_rate']/bl,3) if bl else None
        out[s]={'yes':y,'no':n}
    return out


def recovery_component_table(rows):
    out={}
    for k in ('recovery_rel_first','recovery_acct_first','recovery_ema_first'):
        yes=[r for r in rows if r.get(k) is True]
        out[k]=cohort(yes,k)
    return out


def stable_auc(disc,val,features,label):
    d={x['feature']:x for x in compare_continuous(disc,features,label)}
    v={x['feature']:x for x in compare_continuous(val,features,label)}
    out=[]
    for f in features:
        if f not in d or f not in v:continue
        da=d[f]['auc'];va=v[f]['auc'];dd=da-.5;vd=va-.5
        same=(dd==0 or vd==0 or dd*vd>0)
        out.append({'feature':f,'disc_auc':da,'val_auc':va,'same_direction':same,
                    'disc_strength':rnd(abs(dd),4),'val_strength':rnd(abs(vd),4),
                    'min_strength':rnd(min(abs(dd),abs(vd)),4),
                    'disc_positive_median':d[f]['positive_median'],'disc_negative_median':d[f]['negative_median'],
                    'val_positive_median':v[f]['positive_median'],'val_negative_median':v[f]['negative_median']})
    return sorted(out,key=lambda x:(x['same_direction'],x['min_strength']),reverse=True)


def main():
    rows,e7,e20,cache,events,occ=F.build_events()
    rec=build_records(events,occ)
    keys=sorted(set(e['entry_ts'] for e in events));cut=keys[int(len(keys)*.60)]
    disc=[r for r in rec if r['entry_ts']<cut];val=[r for r in rec if r['entry_ts']>=cut]

    continuous=['initial_run_min','time_to_recovery_min',
                'warning_share_15','warning_share_30','warning_share_60','warning_share_120',
                'longest_warning_run_30','longest_warning_run_60','longest_warning_run_120',
                'rewarning_count_30','rewarning_count_60','rewarning_count_120',
                'rel_share_30','rel_share_60','rel_share_120',
                'acct_share_30','acct_share_60','acct_share_120',
                'ema_share_30','ema_share_60','ema_share_120']
    states=['persist_10m','persist_15m','persist_20m','recover_within_10m','recover_within_20m',
            'no_recovery_15','no_recovery_30','no_recovery_60','rewarn_after_recovery_60']

    stable_sl=stable_auc(disc,val,continuous,'parent_sl')
    stable_loss=stable_auc(disc,val,continuous,'parent_loss')
    stable_good=stable_auc(disc,val,continuous,'future_good_60')

    # Forensic PASS: at least one trajectory feature has same-direction rank separation
    # of >=0.08 AUC distance from random in BOTH chronology periods for parent SL or loss.
    strong_stable=[x for x in stable_sl if x['same_direction'] and x['min_strength']>=0.08]
    strong_stable_loss=[x for x in stable_loss if x['same_direction'] and x['min_strength']>=0.08]
    passed=bool(strong_stable or strong_stable_loss)

    out={
      'status':'FRIDAY_TMETHOD_F515_WARNING_PERSISTENCE_RECOVERY_ATLAS',
      'design':{
        'forensics_only':True,'trading_action':False,
        'warning':'F5.12 HIDDEN_CORE_EMA frozen',
        'metrics_occurrences':len(keys),'warned_occurrences':len(rec),
        'discovery_warned':len(disc),'validation_warned':len(val),
        'split_cut_date':ldt(cut).strftime('%Y-%m-%d'),
        'horizons_min':HORIZONS,
        'natural_states':states,
        'pass_gate':'same-direction AUC separation >=0.08 from 0.5 in both discovery and validation for parent SL or parent loss'
      },
      'warned_baseline':{'discovery':cohort(disc,'DISC'),'validation':cohort(val,'VAL'),'full':cohort(rec,'FULL')},
      'stable_auc_parent_sl':stable_sl,
      'stable_auc_parent_loss':stable_loss,
      'stable_auc_future_good60':stable_good,
      'strong_stable_sl':strong_stable,
      'strong_stable_loss':strong_stable_loss,
      'state_tables':{
        'discovery':boolean_state_table(disc,states),
        'validation':boolean_state_table(val,states),
        'full':boolean_state_table(rec,states)
      },
      'recovery_components':{
        'discovery':recovery_component_table(disc),
        'validation':recovery_component_table(val),
        'full':recovery_component_table(rec)
      },
      'milestone_pass':passed,
      'verdict':'PERSISTENCE_TRAJECTORY_SEPARABLE' if passed else 'NO_STABLE_PERSISTENCE_SEPARATION',
      'notes':'No management rule selected. Any next action milestone must freeze a simple persistence state from discovery only and validate economically; do not tune on validation.'
    }
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
