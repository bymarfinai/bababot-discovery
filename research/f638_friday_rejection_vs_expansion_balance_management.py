#!/usr/bin/env python3
"""F6.38 — Friday rejection-vs-expansion balance management.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.34/F6.36/F6.37 remain same-sample diagnostics/forensics and are NOT frozen.

ONE predeclared natural inequality motivated by F6.37; no fitted threshold/timing sweep:
  REJECTION_VS_EXPANSION_BALANCE_35
  1) Start from exact F6.34 architecture.
  2) F6.31 flow-divergence cases still join exact +35 higher-close watcher.
  3) Among F6.29 candidates WITHOUT flow divergence, compute at entry time:
       upper = immediate pre-entry 5m upper-wick ratio
       body_expansion = immediate pre-entry body ratio - median body ratio of prior 3 completed 5m bars
     Admit to the SAME +35 watcher iff upper > body_expansion.
  4) Otherwise retain actual +20m-open cut.
  5) +35 confirmation and frozen/parent priority are exactly F6.34.

No magnitude cutoff, alternate lookback, timing, EMA, or economic sweep is used.
Because F6.37 selected this architecture on the same historical sample, this is
SAME-SAMPLE ECONOMIC DIAGNOSTIC ONLY even if it passes.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629
import f631_friday_flow_reversal_recovery_guard as f631
import f634_friday_higher_close35_continuation_management as f634
import f636_friday_preentry_rejection_morphology_management as f636
import f637_friday_relative_upper_rejection_forensic as f637

OUT=Path(os.getenv('F638_OUT','f638_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='REJECTION_VS_EXPANSION_BALANCE_35'


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]

    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        bst=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)

        watch=f626.failed_launch_state(k,t,tr)
        watch_active=False
        if watch is not None and watch[f626.RULE]:
            watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))
        st=f629.candidate_state(k,t,tr) if watch_active else None
        gs=f631.guard_state(k,t,tr) if watch_active else None

        f629_action=False; f629_pnl=float(base_pnl); guarded20=False
        if st is not None and st[f629.RULE] and (base_dt is None or st['decision_t']<pd.Timestamp(base_dt)):
            f629_action=True
            f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
            guarded20=bool(gs is not None and gs[f631.RULE])

        lf=f637.local_features(k,t)
        upper=float(lf['rel_last_upper']) if lf is not None else float('nan')
        body_exp=float(lf['rel_body_delta_prev3median']) if lf is not None else float('nan')
        balance=bool(upper>body_exp) if lf is not None else False

        # Exact F6.34 reconstruction.
        f634_pnl=float(base_pnl); f634_action='BASE'
        if f629_action and not guarded20:
            f634_pnl=f629_pnl; f634_action='CUT20'
        elif f629_action and guarded20:
            f634_pnl,f634_action,_=f636.resolve35(k,t,tr,base_pnl,base_dt)

        # F6.38 = F6.34 + one second admission gate for no-divergence candidates.
        managed=float(base_pnl); action='BASE'; route35='NONE'; c35=None
        if f629_action:
            if guarded20:
                route35='FLOW_DIVERGENCE'
                managed,action,c35=f636.resolve35(k,t,tr,base_pnl,base_dt)
            elif balance:
                route35='REJECTION_GT_BODY_EXPANSION'
                managed,action,c35=f636.resolve35(k,t,tr,base_pnl,base_dt)
            else:
                managed=f629_pnl; action='CUT20'

        row={
          'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
          'parent_pnl':float(tr.pnl),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
          'base_pnl':float(base_pnl),'base_layer':base_layer,'watch_active':watch_active,
          'f629_action':f629_action,'guarded20':guarded20,'f629_pnl':f629_pnl,
          'rel_last_upper':upper,'rel_body_delta_prev3median':body_exp,
          'balance_margin':upper-body_exp if lf is not None else float('nan'),RULE:balance,
          'f634_pnl':f634_pnl,'f634_action':f634_action,
          'managed_pnl':managed,'action':action,'route35':route35,
          'incremental_vs_base':managed-float(base_pnl),'incremental_vs_f634':managed-f634_pnl,
        }
        if c35 is not None:
            row.update({'higher_close35':bool(c35['higher_close']),'decision_open35':float(c35['decision_open'])})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f638_rows.csv',index=False)
    base_m=f634.metrics(df.base_pnl); f634_m=f634.metrics(df.f634_pnl); managed_m=f634.metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'five-layer parity fail {base_m}')
    if abs(f634_m['pnl']-155.1811622510)>0.10 or f634_m['wins']!=72:
        raise RuntimeError(f'F6.34 parity fail {f634_m}')

    watches=df[df.watch_active].copy(); acts=df[df.f629_action].copy(); nodiv=acts[~acts.guarded20].copy()
    if len(watches)!=26 or len(acts)!=12 or (int((nodiv.parent_pnl>0).sum()),int((nodiv.parent_pnl<=0).sum()))!=(1,5):
        raise RuntimeError(f'parity watches/acts/nodiv {len(watches)}/{len(acts)}/{(nodiv.parent_pnl>0).sum()}-{(nodiv.parent_pnl<=0).sum()}')
    signals=nodiv[nodiv[RULE]].copy(); nonsig=nodiv[~nodiv[RULE]].copy()
    sig_hold=signals[signals.action=='CONFIRM35_HOLD']; sig_cut=signals[signals.action=='CUT35']; sig_frozen=signals[signals.action=='FROZEN_BEFORE35']

    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    inc=float(managed_m['pnl']-base_m['pnl']); delta634=float(managed_m['pnl']-f634_m['pnl'])
    incD=float(d.incremental_vs_base.sum()); incV=float(v.incremental_vs_base.sum())
    deltaD=float(d.incremental_vs_f634.sum()); deltaV=float(v.incremental_vs_f634.sum())
    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    pw=acts[acts.parent_pnl>0]; winners_preserved=int((pw.managed_pnl>0).sum())
    winner_gain=float(signals[signals.parent_pnl>0].incremental_vs_f634.sum())
    loser_cost=float(signals[signals.parent_pnl<=0].incremental_vs_f634.sum())

    screen=bool(delta634>0 and deltaD>=-1e-9 and deltaV>=-1e-9 and baseline_pos_nonpos==0 and
                winners_preserved==len(pw) and managed_m['wr']>=base_m['wr']-1e-12 and
                managed_m['dd']<=f634_m['dd']+1e-9)

    out={
      'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY','screen_pass':screen,
      'rule_definition':{
        'parent':'exact F6.34 architecture','no_divergence_gate':'pre-entry upper-wick ratio > body-ratio expansion vs median prior 3 bars',
        'gate_timing':'entry-time causal geometry only','gate_pass':'join exact F6.34 +35 watcher','gate_fail':'actual +20m-open cut',
        'confirm35':'+30->35 close > +25->30 close -> frozen HOLD; else actual +35m-open cut','tuning':'none; one natural inequality'},
      'frozen_five_layer':base_m,'f634_management':f634_m,'f638_management':managed_m,
      'active_watches':int(len(watches)),'f629_actions':int(len(acts)),'no_divergence_branch':int(len(nodiv)),
      'balance_signals':int(len(signals)),'non_balance_cut20':int(len(nonsig)),
      'balance_signal_winner_loser':[int((signals.parent_pnl>0).sum()),int((signals.parent_pnl<=0).sum())],
      'balance_hold_winner_loser':[int((sig_hold.parent_pnl>0).sum()),int((sig_hold.parent_pnl<=0).sum())],
      'balance_cut35_winner_loser':[int((sig_cut.parent_pnl>0).sum()),int((sig_cut.parent_pnl<=0).sum())],
      'balance_frozen_before35':int(len(sig_frozen)),
      'parent_winners_acted':int(len(pw)),'parent_winners_preserved_positive':winners_preserved,
      'incremental_vs_frozen':inc,'incremental_vs_f634':delta634,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,'delta_vs_f634_D':deltaD,'delta_vs_f634_V':deltaV,
      'balance_winner_gain_vs_f634':winner_gain,'balance_loser_cost_vs_f634':loser_cost,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,'wr_gain_pp_vs_frozen':float((managed_m['wr']-base_m['wr'])*100),
      'dd_delta_vs_f634':float(managed_m['dd']-f634_m['dd']),
      'no_divergence_detail':nodiv[['date','period','parent_pnl','base_pnl','f634_pnl','managed_pnl','rel_last_upper','rel_body_delta_prev3median','balance_margin',RULE,'action','incremental_vs_f634']].to_dict('records'),
      'guardrail':'F6.37 selected this relationship on the same sample. D/V are robustness slices only. No auto-promotion; no threshold/lookback/timing retuning if FAIL.'}
    (OUT/'f638_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.38 — Rejection-vs-Expansion Balance Management','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact architecture',
        'Start from F6.34. In the no-flow-divergence +20 branch, admit to the existing +35 watcher iff the immediate pre-entry upper-wick ratio is greater than body-ratio expansion versus the median of the prior 3 completed 5m bars. Otherwise keep the actual +20m cut. +35 confirmation is unchanged.','',
        '## Routing',
        f"- no-divergence branch **{len(nodiv)}** = {(nodiv.parent_pnl>0).sum()} winner / {(nodiv.parent_pnl<=0).sum()} losers",
        f"- balance signals **{len(signals)}** = {(signals.parent_pnl>0).sum()} winner / {(signals.parent_pnl<=0).sum()} losers; non-signals cut20 **{len(nonsig)}**",
        f"- balance +35 HOLD W/L **{(sig_hold.parent_pnl>0).sum()} / {(sig_hold.parent_pnl<=0).sum()}**; CUT35 W/L **{(sig_cut.parent_pnl>0).sum()} / {(sig_cut.parent_pnl<=0).sum()}**; frozen before35 **{len(sig_frozen)}**",'',
        '## Economics',
        f"- frozen **{base_m['pnl']:+.3f}** → F6.34 **{f634_m['pnl']:+.3f}** → F6.38 **{managed_m['pnl']:+.3f}**",
        f"- incremental vs frozen **{inc:+.3f}**; vs F6.34 **{delta634:+.3f}**",
        f"- D/V incremental vs frozen **{incD:+.3f} / {incV:+.3f}**; delta vs F6.34 **{deltaD:+.3f} / {deltaV:+.3f}**",
        f"- WR **{base_m['wr']*100:.2f}% → {managed_m['wr']*100:.2f}%**; PF **{base_m['pf']:.3f} → {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} → {managed_m['dd']:.3f}**",
        f"- acted parent winners preserved positive **{winners_preserved}/{len(pw)}**; baseline positive→nonpositive **{baseline_pos_nonpos}**",
        f"- balance winner gain vs F6.34 **{winner_gain:+.3f}**; balance loser cost vs F6.34 **{loser_cost:+.3f}**",'',
        '## No-divergence detail']
    for _,r in nodiv.iterrows():
        md.append(f"- `{r.date}` {r.period}: parent {r.parent_pnl:+.3f}; upper {r.rel_last_upper:.4f}; body-exp {r.rel_body_delta_prev3median:+.4f}; margin {r.balance_margin:+.4f}; gate **{bool(r[RULE])}** → {r.action}; ΔF6.34 {r.incremental_vs_f634:+.3f}")
    md += ['', '## Guardrail','Same-sample diagnostic selected from F6.37. Even a PASS cannot validate or freeze this rule. No numeric threshold, alternate lookback, or timing tuning is allowed from these same cases.']
    (OUT/'F6.38_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
