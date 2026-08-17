#!/usr/bin/env python3
"""Saturday T-Method S5.7A — Adaptive Runner Confidence x A7.19 Conflict Atlas.

Research only; live BBC untouched. No management action is changed.

Purpose
-------
Inspect the exact 8 frozen A7.19 SHALLOW_FAILURE actions and ask whether causal
runner-confidence evidence already printed before +240m conflicts with A7.19's
late monetization decision.

Frozen confidence evidence (no threshold sweep):
- PROVEN: causal +0.50 MFE hinge exists before +240m.
- STRONG_HINGE: completed hinge candle itself closes >=+0.50% progress.
- RECONFIRMED_RUNNER: after +0.50, completed close gives back <=+0.40, then within
  60m rebuilds >=+0.50 before a <=+0.20 breakdown; the rebuild must occur before
  the +240m A7.19 decision.
- HIGH_CONFIDENCE = STRONG_HINGE OR RECONFIRMED_RUNNER.

Counterfactual is not a new strategy: frozen static-parent continuation PnL is
compared with the already-frozen A7.19 +240m exit PnL for those same 8 actions.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52

OUT=Path(os.getenv('S57A_OUT','s57a_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83


def first_close(k,tr,start,end,op,level,deadline=None):
    if start is None or end is None or end<=start:return None
    bars=k[(k.index>=start)&(k.index<end)]
    for b in bars.itertuples(index=False):
        d=b.ts+pd.Timedelta(minutes=5)
        if deadline is not None and d>deadline:break
        p=float(b.close)/tr.entry-1
        if (op=='>=' and p>=level) or (op=='<=' and p<=level):return d
    return None


def confidence_before240(k,t,tr):
    d240=t+pd.Timedelta(minutes=240)
    h05,h08=a52.first_hinges(k,t,tr)
    out={'h05':h05,'h08':h08,'proven':False,'strong_hinge':False,'gb40_before240':False,
         'reconfirmed':False,'gb40_t':None,'rebuild50_t':None,'break20_t':None,
         'hinge_close_progress':np.nan,'confidence_state':'UNPROVEN'}
    if h05 is None or h05>d240:return out
    out['proven']=True
    hb=h05-pd.Timedelta(minutes=5)
    out['hinge_close_progress']=float(k.loc[hb,'close'])/tr.entry-1
    out['strong_hinge']=bool(out['hinge_close_progress']>=.005)

    # The confidence path is only allowed to consume information completed by +240m.
    end=min(pd.Timestamp(tr.exit_t),d240)
    gb=first_close(k,tr,h05,end,'<=',.004)
    if gb is not None and gb<=d240:
        out['gb40_before240']=True; out['gb40_t']=gb
        deadline=min(end,gb+pd.Timedelta(minutes=60))
        rb=first_close(k,tr,gb,end,'>=',.005,deadline)
        br=first_close(k,tr,gb,end,'<=',.002,deadline)
        out['rebuild50_t']=rb; out['break20_t']=br
        if rb is not None and rb<=d240 and (br is None or rb<br):out['reconfirmed']=True

    if out['reconfirmed']:out['confidence_state']='RECONFIRMED'
    elif out['strong_hinge']:out['confidence_state']='STRONG_PROVEN'
    else:out['confidence_state']='UNRESOLVED_PROVEN'
    return out


def met(g):
    if len(g)==0:return {'n':0,'a719_pnl':0.0,'parent_pnl':0.0,'continue_minus_a719':0.0,
                         'a719_help_n':0,'a719_hurt_n':0,'later_deep_rate':np.nan}
    delta=g.parent_pnl-g.a719_pnl
    return {'n':len(g),'a719_pnl':float(g.a719_pnl.sum()),'parent_pnl':float(g.parent_pnl.sum()),
            'continue_minus_a719':float(delta.sum()),'a719_help_n':int((delta<0).sum()),
            'a719_hurt_n':int((delta>0).sum()),'later_deep_rate':float(g.eventual_deep.mean())}


def splitrow(df,mask,label):
    g=df[mask];d=g[g.idx<SPLIT];v=g[g.idx>=SPLIT]
    r={'label':label,**met(g)}
    for p,x in [('disc',d),('val',v)]:
        for k,z in met(x).items():r[f'{p}_{k}']=z
    return r


def main():
    k=s50.load_klines(); f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]; all_a719=0.0
    for i,(t,tr) in enumerate(zip(entries,trades)):
        s240=a50.state240(k,t,tr); a719=float(a50.a719_pnl(k,f,t,tr,s240)); all_a719+=a719
        if s240['state240']!='SHALLOW_FAILURE':continue
        c=confidence_before240(k,t,tr)
        # eventual_deep is forensic only: parent path reaches +0.80 at any later point before frozen parent exit.
        _,h08=a52.first_hinges(k,t,tr)
        row={'idx':i,'date':str(tr.date),'parent_pnl':float(tr.pnl),'a719_pnl':a719,
             'continue_minus_a719':float(tr.pnl-a719),'a719_helped':bool(tr.pnl<a719),
             'a719_hurt':bool(tr.pnl>a719),'eventual_deep':bool(h08 is not None),
             'progress240':float(s240['progress240_open']),'mfe240':float(s240['mfe240']),
             'taker240':float(s240['taker240'])}
        row.update({
            'proven':c['proven'],'strong_hinge':c['strong_hinge'],'reconfirmed':c['reconfirmed'],
            'high_confidence':bool(c['strong_hinge'] or c['reconfirmed']),
            'confidence_state':c['confidence_state'],'hinge_close_progress':c['hinge_close_progress'],
            'gb40_before240':c['gb40_before240'],
            'gb40_t':None if c['gb40_t'] is None else str(c['gb40_t']),
            'rebuild50_t':None if c['rebuild50_t'] is None else str(c['rebuild50_t']),
            'break20_t':None if c['break20_t'] is None else str(c['break20_t'])})
        rows.append(row)
    df=pd.DataFrame(rows).sort_values('idx').reset_index(drop=True)

    # Frozen parity.
    parent_all=sum(float(x.pnl) for x in trades)
    if len(trades)!=139 or abs(parent_all-87.199692)>.02:raise RuntimeError('parent parity fail')
    if abs(all_a719-103.3830997612)>.02:raise RuntimeError('A7.19 parity fail')
    if len(df)!=8:raise RuntimeError(f'A7.19 action count parity fail: {len(df)}')
    if not bool(df.proven.all()):raise RuntimeError('A7.19 action without +0.50 proof')

    df.to_csv(OUT/'s57a_a719_action_conflicts.csv',index=False)
    tables=[]
    tables.append(splitrow(df,np.ones(len(df),dtype=bool),'ALL_A719_ACTIONS'))
    tables.append(splitrow(df,df.high_confidence,'HIGH_CONFIDENCE'))
    tables.append(splitrow(df,~df.high_confidence,'LOWER_CONFIDENCE'))
    for st in ['RECONFIRMED','STRONG_PROVEN','UNRESOLVED_PROVEN']:
        tables.append(splitrow(df,df.confidence_state.eq(st),st))
    pd.DataFrame(tables).to_csv(OUT/'s57a_conflict_tables.csv',index=False)

    hi=df[df.high_confidence]; hid=hi[hi.idx<SPLIT]; hiv=hi[hi.idx>=SPLIT]
    # Predeclared eligibility for a later adaptive ACTION test.
    action_test_eligible=bool(len(hid)>=1 and len(hiv)>=1 and
                              float(hid.parent_pnl.sum()-hid.a719_pnl.sum())>0 and
                              float(hiv.parent_pnl.sum()-hiv.a719_pnl.sum())>0)

    summary={'parent_all_pnl':parent_all,'a719_all_pnl':all_a719,'a719_action_n':len(df),
             'tables':tables,'adaptive_override_action_test_eligible':action_test_eligible,
             'action_rows':df.to_dict(orient='records')}
    (OUT/'s57a_summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.1f}%'
    def money(x):return f'${x:+.3f}'
    lines=['# BTC Temporal Saturday T-Method S5.7A — Runner Confidence × A7.19 Conflict Atlas','',
           '**Status:** COMPLETE — FORENSIC ONLY; NO A7.19 ACTION CHANGED',
           '**Research only:** live BBC untouched','',
           '## Frozen parity',f'- Static parent: 139 / {money(parent_all)}',f'- A7.19: 139 / {money(all_a719)}',f'- Exact A7.19 SHALLOW_FAILURE actions: **{len(df)}**','',
           '## Frozen runner-confidence states','- STRONG_HINGE: completed +0.50 hinge candle closes >=+0.50%.',
           '- RECONFIRMED: after <=+0.40 giveback, completed close rebuilds >=+0.50 before <=+0.20 within 60m, all before +240m.',
           '- HIGH_CONFIDENCE = STRONG_HINGE OR RECONFIRMED.','',
           '## Conflict table','| State | N | A7.19 PnL | Parent continuation | Continue - A7.19 | A7.19 helped/hurt | Later deep | Discovery delta | Validation delta |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in tables:
        lines.append(f"| {r['label']} | {r['n']} | {money(r['a719_pnl'])} | {money(r['parent_pnl'])} | {money(r['continue_minus_a719'])} | {r['a719_help_n']} / {r['a719_hurt_n']} | {pct(r['later_deep_rate'])} | {money(r['disc_continue_minus_a719'])} | {money(r['val_continue_minus_a719'])} |")
    lines += ['', '## Predeclared next-step gate',
              '- A later adaptive override ACTION test requires >=1 HIGH_CONFIDENCE A7.19 conflict in each chronology half and parent continuation must beat A7.19 in both halves.',
              f"- **Adaptive override action-test eligible: {'YES' if action_test_eligible else 'NO'}**",'',
              '## Guardrails','- Eventual deep is outcome-only forensic labeling.','- No A7.19 exit is changed in S5.7A.','- No thresholds are optimized or swept.']
    (OUT/'S5.7A_CHECKPOINT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__':main()
