#!/usr/bin/env python3
"""F6.7 — Friday15 causal early-sink detector + cut counterfactual.

Research only; live BBC untouched.

Motivation from F6.6:
- 58 trades have a red first 5m candle.
- 10 are strict hindsight immediate sinks: after first 5m red, price never trades
  back to entry and all 10 eventually SL.
- But 48 red-first-5m trades do eventually trade back to entry, so red alone is
  too broad.

Causal detector tested at frozen natural decision times +10/+15/+20/+30m:
EARLY_SINK_t iff
1) first completed 5m candle closes below entry;
2) trade is still alive at decision open t;
3) from the second 5m candle through the final completed candle before t,
   no high has reached the entry price.

This uses only completed path information available at the decision open.
Counterfactual action: exit at the actual decision-time open.
No threshold fitting, no price-level tuning, no extra feature/filter.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517

OUT=Path(os.getenv('F67_OUT','f67_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N
DECISIONS=[5,10,15,20,30]


def metrics(p):
    p=np.asarray(p,dtype=float)
    w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':w,'losses':int(len(p)-w),'wr':float(w/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'exp':float(p.mean()) if len(p) else np.nan,
            'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':int(ls)}


def strict_sink_label(k,t,tr):
    bars=k[(k.index>=t)&(k.index<tr.exit_t)]
    if bars.empty: return False
    first=bars.iloc[0]; rest=bars.iloc[1:]
    return bool(float(first.close)<tr.entry and (rest.empty or float(rest.high.max()) < tr.entry-1e-12))


def causal_state(k,t,tr,mins):
    dt=t+pd.Timedelta(minutes=mins)
    # At decision open dt, bars with opens < dt are completed.
    completed=k[(k.index>=t)&(k.index<dt)]
    if completed.empty: raise RuntimeError(f'no completed bars {tr.date} +{mins}')
    first=completed.iloc[0]
    first5_red=bool(float(first.close)<tr.entry)
    alive=bool(tr.exit_t>dt)
    if mins==5:
        no_reclaim_since_first=True
    else:
        after_first=completed.iloc[1:]
        no_reclaim_since_first=bool(after_first.empty or float(after_first.high.max()) < tr.entry-1e-12)
    state=bool(first5_red and alive and no_reclaim_since_first)
    return state, first5_red, alive, no_reclaim_since_first


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; base=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        sink=strict_sink_label(k,t,tr)
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'entry':tr.entry,'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
             'strict_sink':sink}
        for mins in DECISIONS:
            state,red,alive,nr=causal_state(k,t,tr,mins)
            row[f'state_{mins}']=state; row[f'alive_{mins}']=alive; row[f'no_reclaim_{mins}']=nr
            managed=float(tr.pnl); exit_px=np.nan; delta=0.0
            if state:
                dt=t+pd.Timedelta(minutes=mins)
                exit_px=float(k.loc[dt,'open'])
                managed=f517.NOTIONAL*(exit_px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
                delta=managed-float(tr.pnl)
            row[f'managed_{mins}']=managed; row[f'delta_{mins}']=delta; row[f'exit_px_{mins}']=exit_px
        base.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(base)
    if int(df.strict_sink.sum())!=10: raise RuntimeError(f'F6.6 strict-sink parity failed {int(df.strict_sink.sum())}')
    if int((df.parent_reason=='SL').sum())!=51: raise RuntimeError('parent SL parity failed')
    df.to_csv(OUT/'f67_rows.csv',index=False)

    parent=metrics(df.parent_pnl)
    sink_total=int(df.strict_sink.sum())
    results=[]
    for mins in DECISIONS:
        action=df[df[f'state_{mins}']]
        managed=metrics(df[f'managed_{mins}'])
        d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
        d_action=d[d[f'state_{mins}']]; v_action=v[v[f'state_{mins}']]
        # Strict sink recall only among sinks still alive at decision; also absolute coverage.
        sinks=df[df.strict_sink]
        sinks_alive=sinks[sinks[f'alive_{mins}']]
        sink_actions=int(action.strict_sink.sum())
        non_sink_actions=int((~action.strict_sink).sum())
        parent_winners_cut=int(action.parent_win.sum())
        improved=int((action[f'delta_{mins}']>1e-12).sum())
        damaged=int((action[f'delta_{mins}']<-1e-12).sum())
        r={
            'mins':mins,
            'actions':int(len(action)),
            'strict_sink_actions':sink_actions,
            'strict_sink_total':sink_total,
            'strict_sink_alive':int(len(sinks_alive)),
            'strict_sink_recall_total':sink_actions/sink_total if sink_total else np.nan,
            'strict_sink_recall_alive':sink_actions/len(sinks_alive) if len(sinks_alive) else np.nan,
            'non_sink_actions':non_sink_actions,
            'parent_winners_cut':parent_winners_cut,
            'action_parent_wr':float(action.parent_win.mean()) if len(action) else np.nan,
            'action_parent_pnl':float(action.parent_pnl.sum()),
            'action_managed_pnl':float(action[f'managed_{mins}'].sum()),
            'action_delta':float(action[f'delta_{mins}'].sum()),
            'improved_actions':improved,
            'damaged_actions':damaged,
            'parent':parent,
            'managed':managed,
            'full_delta':float(managed['pnl']-parent['pnl']),
            'discovery_delta':float(d[f'delta_{mins}'].sum()),
            'validation_delta':float(v[f'delta_{mins}'].sum()),
            'discovery_actions':int(len(d_action)),
            'validation_actions':int(len(v_action)),
            'discovery_winners_cut':int(d_action.parent_win.sum()),
            'validation_winners_cut':int(v_action.parent_win.sum()),
            'dd_improvement':float(parent['dd']-managed['dd']),
        }
        # A useful robust-management screen, not a post-hoc optimizer: economic gain in both halves,
        # drawdown non-worse, and action cohort historical WR <= 20%.
        r['robust_screen']=bool(r['full_delta']>0 and r['discovery_delta']>=0 and r['validation_delta']>=0 and r['dd_improvement']>=-1e-12 and (r['action_parent_wr']<=.20 if len(action) else False))
        results.append(r)

    # Prefer earliest decision that passes the fixed robust screen. This is chronology-preserving,
    # not a PnL-maximizing threshold search.
    eligible=[x for x in results if x['robust_screen']]
    earliest=min(eligible,key=lambda x:x['mins']) if eligible else None
    out={'parent':parent,'decisions':results,'earliest_robust':earliest}
    (OUT/'f67_summary.json').write_text(json.dumps(out,indent=2,default=float))

    pct=lambda x:'n/a' if x is None or not np.isfinite(x) else f'{100*x:.2f}%'
    md=['# Friday15 F6.7 — Causal Early-Sink Detector + Cut Counterfactual','',
        '**Status:** COMPLETE — RESEARCH ONLY','**Live BBC untouched.**','',
        '## Causal state',
        '`first 5m red + still alive + no completed 5m after the first has traded back to entry`.',
        'At each decision, exit at the actual decision-time open. No threshold fitting.','',
        '## Parent',f"- 138 trades, {parent['wins']}W/{parent['losses']}L, WR {100*parent['wr']:.2f}%, PnL {parent['pnl']:+.3f}, DD {parent['dd']:.3f}",'',
        '## Decision-time results']
    for x in results:
        md += [f"### +{x['mins']}m",
               f"- actions {x['actions']} = strict sinks {x['strict_sink_actions']}/10 + non-sinks {x['non_sink_actions']}",
               f"- action cohort parent WR {pct(x['action_parent_wr'])}; parent winners cut {x['parent_winners_cut']}",
               f"- action PnL {x['action_parent_pnl']:+.3f} -> {x['action_managed_pnl']:+.3f}; delta {x['action_delta']:+.3f}",
               f"- full strategy delta {x['full_delta']:+.3f}; Discovery {x['discovery_delta']:+.3f}; Validation {x['validation_delta']:+.3f}",
               f"- DD improvement {x['dd_improvement']:+.3f}; robust screen {x['robust_screen']}",'']
    if earliest:
        md += ['## Earliest robust decision',
               f"**+{earliest['mins']}m** is the earliest decision passing the fixed economic/chronology screen.",
               'This is a candidate for a frozen follow-up robustness test; it is not yet promoted to live.','']
    else:
        md += ['## Earliest robust decision','None of the tested natural decision times passed the fixed robust screen.','']
    md += ['## Guardrail',
           'The 10 strict sinks are hindsight labels used only to measure detector recall. The detector itself uses only completed candles and current position-alive state at each decision open.']
    (OUT/'F6.7_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
