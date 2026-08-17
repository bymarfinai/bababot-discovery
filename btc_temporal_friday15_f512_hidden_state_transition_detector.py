"""Friday T-Method F5.12 — Hidden-State Transition Detector.

Milestone objective
-------------------
Test whether the F5.11 hidden-state mechanism can emit a causal first-fire
REVERSAL_WARNING before a materially better future reversal window.

IMPORTANT:
- no BUY->SHORT trading rule is selected here
- no TP/SL is optimized
- all thresholds are natural/mechanistic (zero crossings), not fitted numeric sweeps
- discovery selects at most one warning architecture; validation is report-only

F5.11 mechanism carried forward:
1) top-trader position long-bias is no longer elevated vs global-account long-bias
2) top/global account L/S ratios are deteriorating
3) EMA7-vs-EMA20 spread is contracting
4) OI is context only, never a standalone gate
"""
import json, statistics
from collections import defaultdict

import btc_temporal_friday15_f511_hidden_state_reversal_forensics as F
from btc_temporal_a34_5m_events import rnd, ldt

HORIZONS=(15,30,60,120)


def med(v):
    v=[x for x in v if x is not None]
    return statistics.median(v) if v else None


def mean(v):
    v=[x for x in v if x is not None]
    return statistics.mean(v) if v else None


def sigs(e):
    f=e['feat']
    rel=(f.get('top_vs_global') is not None and f['top_vs_global']<=0)
    acct=(f.get('top_account_chg_15') is not None and f.get('global_account_chg_15') is not None and
          f['top_account_chg_15']<0 and f['global_account_chg_15']<0)
    ema=(f.get('ema_spread_chg15') is not None and f['ema_spread_chg15']<0)
    return rel,acct,ema


def rules():
    return {
      'RELATIVE_ONLY':lambda e:sigs(e)[0],
      'ACCOUNT_DECAY':lambda e:sigs(e)[1],
      'DECAY_EMA':lambda e:sigs(e)[1] and sigs(e)[2],
      'HIDDEN_CORE':lambda e:sigs(e)[0] and sigs(e)[1],
      'HIDDEN_CORE_EMA':lambda e:sigs(e)[0] and sigs(e)[1] and sigs(e)[2],
      'TWO_OF_THREE':lambda e:sum(sigs(e))>=2,
    }


def group_events(events):
    d=defaultdict(list)
    for e in events:d[e['entry_ts']].append(e)
    for k in d:d[k].sort(key=lambda z:z['ts'])
    return d


def future_good(q,idx,h):
    t=q[idx]['ts']
    return any(x['good'] and 0<=x['ts']-t<=h*60000 for x in q[idx:])


def forward_path(rows,e,h):
    j=e['j']; steps=h//5
    if j+steps>=len(rows):return None
    if rows[j+steps][0] != rows[j][0]+steps*5*60000:return None
    entry=rows[j][1]
    q=rows[j:j+steps]
    if not q:return None
    close=rows[j+steps-1][4]
    ret=100*(close/entry-1)
    downside=100*(min(x[3] for x in q)/entry-1)
    upside=100*(max(x[2] for x in q)/entry-1)
    return {'ret':ret,'downside':downside,'upside':upside}


def first_fire(q,fn):
    for n,e in enumerate(q):
        if fn(e):return n,e
    return None,None


def metrics(rows,groups,entry_keys,fn):
    warns=[]
    for k in entry_keys:
        q=groups.get(k,[])
        idx,e=first_fire(q,fn)
        if e is None:continue
        rec={'entry_ts':k,'date':e['date'],'minute':e['minute'],'parent':e['parent'],
             'parent_reason':e['parent_reason'],'good_now':e['good'],
             'top_vs_global':e['feat'].get('top_vs_global'),
             'top_account_chg15':e['feat'].get('top_account_chg_15'),
             'global_account_chg15':e['feat'].get('global_account_chg_15'),
             'ema_spread_chg15':e['feat'].get('ema_spread_chg15'),
             'oi_chg15':e['feat'].get('oi_chg_15')}
        for h in HORIZONS:
            rec[f'good_{h}']=future_good(q,idx,h)
            p=forward_path(rows,e,h)
            if p:
                for z,v in p.items():rec[f'{z}_{h}']=v
        warns.append(rec)
    n=len(warns)
    out={'entries':len(entry_keys),'warnings':n,'warning_rate':rnd(n/len(entry_keys),3) if entry_keys else None}
    if not warns:return out,[]
    out.update({
      'median_minute':rnd(med([w['minute'] for w in warns]),2),
      'parent_loss_rate':rnd(sum(w['parent']<=0 for w in warns)/n,3),
      'parent_sl_rate':rnd(sum(w['parent_reason'].startswith('SL') for w in warns)/n,3),
      'parent_tp_rate':rnd(sum(w['parent_reason']=='TP' for w in warns)/n,3),
      'oi15_median':rnd(med([w['oi_chg15'] for w in warns]),5),
    })
    for h in HORIZONS:
        avail=[w for w in warns if f'good_{h}' in w]
        out[f'future_good_{h}_rate']=rnd(sum(w[f'good_{h}'] for w in avail)/len(avail),3) if avail else None
        out[f'median_ret_{h}']=rnd(med([w.get(f'ret_{h}') for w in warns]),4)
        out[f'median_downside_{h}']=rnd(med([w.get(f'downside_{h}') for w in warns]),4)
        out[f'median_upside_{h}']=rnd(med([w.get(f'upside_{h}') for w in warns]),4)
    return out,warns


def baseline(groups,keys):
    # Baseline at the first eligible event (+15m) for every occurrence.
    out={'entries':len(keys)}
    for h in HORIZONS:
        vals=[]; paths=[]
        for k in keys:
            q=groups.get(k,[])
            if not q:continue
            vals.append(future_good(q,0,h))
            p=forward_path(ROWS,q[0],h)
            if p:paths.append(p)
        out[f'future_good_{h}_rate']=rnd(sum(vals)/len(vals),3) if vals else None
        out[f'median_ret_{h}']=rnd(med([p['ret'] for p in paths]),4)
        out[f'median_downside_{h}']=rnd(med([p['downside'] for p in paths]),4)
    return out


def add_lifts(m,b):
    z=dict(m)
    for h in HORIZONS:
        x=m.get(f'future_good_{h}_rate'); y=b.get(f'future_good_{h}_rate')
        z[f'good_{h}_lift']=rnd(x/y,3) if x is not None and y not in (None,0) else None
    return z


def discovery_score(m):
    # Predeclared: prioritize 60m reversal-window lift, then fewer parent-TP false warnings.
    if m.get('warnings',0)<8:return -1e9
    lift=m.get('good_60_lift') or 0
    tp=m.get('parent_tp_rate') or 0
    return lift-0.5*tp


def main():
    global ROWS
    ROWS,e7,e20,cache,events,occ=F.build_events()
    groups=group_events(events)
    keys=sorted(groups)
    cut=keys[int(len(keys)*.60)]
    disc=[k for k in keys if k<cut]; val=[k for k in keys if k>=cut]
    bd=baseline(groups,disc); bv=baseline(groups,val); bf=baseline(groups,keys)
    result={}; warn_rows={}
    for name,fn in rules().items():
        md,wd=metrics(ROWS,groups,disc,fn); mv,wv=metrics(ROWS,groups,val,fn); mf,wf=metrics(ROWS,groups,keys,fn)
        md=add_lifts(md,bd); mv=add_lifts(mv,bv); mf=add_lifts(mf,bf)
        result[name]={'discovery':md,'validation':mv,'full':mf}
        warn_rows[name]=wf
    ranked=sorted(result,key=lambda n:discovery_score(result[n]['discovery']),reverse=True)
    selected=ranked[0] if ranked and discovery_score(result[ranked[0]]['discovery'])>-1e8 else None
    pass_flag=False; reason='NO_DISCOVERY_CANDIDATE'
    if selected:
        d=result[selected]['discovery'];v=result[selected]['validation']
        # Milestone PASS requires warning enrichment in BOTH periods and non-trivial counts.
        pass_flag=(d['warnings']>=8 and v['warnings']>=5 and
                   (d.get('good_60_lift') or 0)>1.15 and (v.get('good_60_lift') or 0)>1.10 and
                   (d.get('parent_tp_rate') or 1)<0.45 and (v.get('parent_tp_rate') or 1)<0.45)
        reason='CROSS_PERIOD_WARNING_ENRICHMENT' if pass_flag else 'SELECTED_DISCOVERY_BUT_VALIDATION_GATE_FAILED'
    out={'status':'FRIDAY_TMETHOD_F512_HIDDEN_STATE_TRANSITION_DETECTOR',
         'design':{'trading':False,'thresholds':'natural zero-crossings only','first_fire':True,
                   'architectures':list(rules()),'split_cut_date':ldt(cut).strftime('%Y-%m-%d'),
                   'selection':'discovery score = 60m GOOD_REVERSE lift - 0.5*parent TP warning rate',
                   'pass_gate':'disc>=8 warnings,val>=5; GOOD_REVERSE60 lift >1.15/>1.10; parent TP warning rate <45% both'},
         'baseline':{'discovery':bd,'validation':bv,'full':bf},
         'results':result,'discovery_rank':ranked,'selected_discovery':selected,
         'milestone_pass':pass_flag,'verdict':reason,
         'notes':'No SHORT is opened in F5.12. OI is reported as context only and never used as a gate. Validation is report-only.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
