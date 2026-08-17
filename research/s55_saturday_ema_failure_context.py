#!/usr/bin/env python3
"""Saturday T-Method S5.5 — Saturday-native EMA Failure Context.

Research only; live BBC untouched. No management action is applied.

S5.4 found that Saturday future-deep runners are slightly STRONGER at the +0.50
hinge and that shallow runners tend to lose EMA structure sooner after the hinge.
Therefore S5.5 does not test Tuesday-style overextension. It tests a tiny,
predeclared causal family:

  weak hinge impulse = completed hinge close progress < +0.50%
  early EMA loss      = event occurs within 60m after the +0.50 hinge

Contexts (NO threshold sweep):
A. WEAK + first completed close below EMA20 <=60m
B. WEAK + two consecutive completed closes below EMA7 <=60m
C. WEAK + two consecutive completed closes below EMA20 <=60m

The +0.50 level is the already-frozen favorable hinge geometry. 60m is a natural
clock window, not selected from S5.4 medians. Outcome labels are forensic only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52
import s54_saturday_ema_failure_forensics as s54

OUT=Path(os.getenv('S55_OUT','s55_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83
EARLY_MIN=60.0
HINGE_LEVEL=0.005

CONTEXTS={
    'WEAK_FIRST_BELOW20_60': lambda d: d.hinge_progress_close.lt(HINGE_LEVEL) & d.first_close_below_ema20_min.le(EARLY_MIN),
    'WEAK_TWO_BELOW7_60': lambda d: d.hinge_progress_close.lt(HINGE_LEVEL) & d.two_close_below_ema7_min.le(EARLY_MIN),
    'WEAK_TWO_BELOW20_60': lambda d: d.hinge_progress_close.lt(HINGE_LEVEL) & d.two_close_below_ema20_min.le(EARLY_MIN),
}


def build_df():
    k=s50.load_klines(); k['ema7']=k['close'].ewm(span=7,adjust=False).mean(); k['ema20']=k['close'].ewm(span=20,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]; all_a719=0.0
    for i,(t,tr) in enumerate(zip(entries,trades)):
        s240=a50.state240(k,t,tr); a719=a50.a719_pnl(k,f,t,tr,s240); all_a719+=a719
        base_exit=b52.a719_exit_time(t,tr,s240)
        h05,h08=a52.first_hinges(k,t,tr)
        if h05 is None: continue
        r={'idx':i,'date':tr.date,'parent_pnl':float(tr.pnl),'a719_pnl':float(a719),'deep':bool(h08 is not None),'shallow':bool(h08 is None),
           'time_to05_min':(h05-t).total_seconds()/60}
        r.update(s54.hinge_features(k,t,tr,h05)); r.update(s54.posthinge_events(k,tr,h05,base_exit)); rows.append(r)
    df=pd.DataFrame(rows).sort_values('idx').reset_index(drop=True)
    all_parent=sum(float(x.pnl) for x in trades)
    if len(df)!=89 or int(df.deep.sum())!=61 or int(df.shallow.sum())!=28: raise RuntimeError('S5.4 hinge parity failed')
    if abs(all_parent-87.199692)>.02 or abs(all_a719-103.3830997612)>.02: raise RuntimeError('frozen benchmark parity failed')
    return df, all_parent, all_a719


def stats(df,name,mask):
    g=df[mask].copy(); d=g[g.idx<SPLIT]; v=g[g.idx>=SPLIT]
    def one(x):
        n=len(x); sh=int(x.shallow.sum()); de=int(x.deep.sum())
        return {'n':n,'shallow':sh,'deep':de,'shallow_rate':sh/n if n else np.nan,'a719_pnl':float(x.a719_pnl.sum()) if n else 0.0}
    F=one(g); D=one(d); V=one(v)
    # Context gate: enough support, >50% shallow in both chronology halves, and
    # cohort A7.19 economics nonpositive in both halves. No action is applied.
    gate=bool(D['n']>=5 and V['n']>=5 and D['shallow_rate']>.50 and V['shallow_rate']>.50 and D['a719_pnl']<=0 and V['a719_pnl']<=0)
    return {'context':name,**F,'disc_n':D['n'],'disc_shallow_rate':D['shallow_rate'],'disc_a719_pnl':D['a719_pnl'],
            'val_n':V['n'],'val_shallow_rate':V['shallow_rate'],'val_a719_pnl':V['a719_pnl'],'context_gate':gate}


def main():
    df,all_parent,all_a719=build_df()
    df['weak_hinge']=df.hinge_progress_close < HINGE_LEVEL
    df['early_first_below20']=df.first_close_below_ema20_min <= EARLY_MIN
    df['early_two_below7']=df.two_close_below_ema7_min <= EARLY_MIN
    df['early_two_below20']=df.two_close_below_ema20_min <= EARLY_MIN
    df.to_csv(OUT/'s55_hinge_rows.csv',index=False)

    baseline=[]
    for period,mask in [('full',np.ones(len(df),dtype=bool)),('disc',df.idx<SPLIT),('val',df.idx>=SPLIT)]:
        g=df[mask]; baseline.append({'period':period,'n':len(g),'shallow_rate':float(g.shallow.mean()),'a719_pnl':float(g.a719_pnl.sum())})
    b=pd.DataFrame(baseline); b.to_csv(OUT/'s55_baseline.csv',index=False)

    results=[stats(df,name,fn(df)) for name,fn in CONTEXTS.items()]
    r=pd.DataFrame(results).sort_values(['context_gate','shallow_rate'],ascending=[False,False]).reset_index(drop=True)
    r.to_csv(OUT/'s55_contexts.csv',index=False)

    # Simple controls to understand whether both ingredients matter; no promotion.
    controls=[]
    control_masks={
      'WEAK_HINGE_ONLY':df.weak_hinge,
      'STRONG_HINGE_ONLY':~df.weak_hinge,
      'EARLY_FIRST_BELOW20_ONLY':df.early_first_below20,
      'EARLY_TWO_BELOW7_ONLY':df.early_two_below7,
      'EARLY_TWO_BELOW20_ONLY':df.early_two_below20,
    }
    for name,m in control_masks.items(): controls.append(stats(df,name,m))
    c=pd.DataFrame(controls); c.to_csv(OUT/'s55_controls.csv',index=False)

    summary={'parent_pnl':all_parent,'a719_pnl':all_a719,'hinge_n':len(df),'deep_n':int(df.deep.sum()),'shallow_n':int(df.shallow.sum()),
             'baseline':baseline,'contexts':results,'controls':controls}
    (OUT/'s55_summary.json').write_text(json.dumps(summary,indent=2,default=float))

    def pct(x): return 'NA' if not np.isfinite(x) else f'{100*x:.2f}%'
    lines=['# BTC Temporal Saturday T-Method S5.5 — EMA Failure Context','',
           '**Status:** COMPLETE — CONTEXT STUDY ONLY; NO EMA ACTION','**Research only:** live BBC untouched','',
           '## Frozen parity',f'- +0.50 hinge: **{len(df)}** = {int(df.deep.sum())} deep / {int(df.shallow.sum())} shallow',
           f'- Parent PnL **${all_parent:+.3f}**; A7.19 **${all_a719:+.3f}**','',
           '## Predeclared geometry','- Weak hinge: completed hinge close progress < +0.50%.',
           '- Early EMA loss: causal completed-bar event within 60m after hinge.',
           '- No threshold sweep and no management action.','',
           '## Context results','| Context | N | Shallow rate | D N/rate/PnL | V N/rate/PnL | Gate |','|---|---:|---:|---:|---:|---:|']
    for _,x in r.iterrows():
        lines.append(f"| {x.context} | {int(x.n)} | {pct(x.shallow_rate)} | {int(x.disc_n)}/{pct(x.disc_shallow_rate)}/${x.disc_a719_pnl:+.2f} | {int(x.val_n)}/{pct(x.val_shallow_rate)}/${x.val_a719_pnl:+.2f} | {'PASS' if x.context_gate else 'FAIL'} |")
    lines += ['', '## Controls','| State | N | Shallow rate | D rate | V rate |','|---|---:|---:|---:|---:|']
    for _,x in c.iterrows(): lines.append(f"| {x.context} | {int(x.n)} | {pct(x.shallow_rate)} | {pct(x.disc_shallow_rate)} | {pct(x.val_shallow_rate)} |")
    lines += ['', '## Promotion guardrail','A context only earns S5.6 follow-up if it has >=5 observations in each chronology half, >50% shallow rate in both halves, and nonpositive A7.19 cohort PnL in both halves.',
              'No context is an exit rule yet.']
    (OUT/'S5.5_CHECKPOINT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=float))

if __name__=='__main__': main()
