#!/usr/bin/env python3
"""F6.40 — Friday balance-only architecture simplification.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.

Question:
Can the exact F6.38/F6.39 balance gate REPLACE the F6.31 flow-divergence
admission guard, instead of being stacked on top of it?

ONE predeclared replacement architecture; no sweep:
  1) Start from F6.29 +20m cut candidates.
  2) IGNORE F6.31 for routing (it is measured only for overlap diagnostics).
  3) Compute the exact frozen F6.38 balance gate at entry time:
       upper_wick_ratio > body_expansion_vs_median_prior_3_completed_5m_bars
  4) Gate PASS -> join the exact F6.34 +35m higher-close watcher.
  5) Gate FAIL -> retain actual +20m-open cut.
  6) Parent/frozen exit at or before +35m keeps priority.

Comparators are exact F6.34 and F6.38 reconstructions. No threshold, lookback,
timing, EMA, or alternate architecture is tested.
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

OUT=Path(os.getenv('F640_OUT','f640_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='BALANCE_ONLY_REPLACEMENT_35'


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
        f629_action=False; f629_pnl=float(base_pnl)
        if st is not None and st[f629.RULE] and (base_dt is None or st['decision_t']<pd.Timestamp(base_dt)):
            f629_action=True
            f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
        flow_guard=bool(f629_action and gs is not None and gs[f631.RULE])

        lf=f637.local_features(k,t)
        upper=float(lf['rel_last_upper']) if lf is not None else float('nan')
        body_exp=float(lf['rel_body_delta_prev3median']) if lf is not None else float('nan')
        balance=bool(upper>body_exp) if lf is not None else False

        # Exact F6.34 reconstruction: flow guard only.
        f634_pnl=float(base_pnl); f634_action='BASE'
        if f629_action and not flow_guard:
            f634_pnl=f629_pnl; f634_action='CUT20'
        elif f629_action and flow_guard:
            f634_pnl,f634_action,_=f636.resolve35(k,t,tr,base_pnl,base_dt)

        # Exact F6.38 reconstruction: flow guard OR balance gate.
        f638_pnl=float(base_pnl); f638_action='BASE'; f638_route='NONE'
        if f629_action:
            if flow_guard or balance:
                f638_route='FLOW' if flow_guard else 'BALANCE'
                f638_pnl,f638_action,_=f636.resolve35(k,t,tr,base_pnl,base_dt)
            else:
                f638_pnl=f629_pnl; f638_action='CUT20'

        # F6.40 replacement: balance gate alone decides admission to +35.
        managed=float(base_pnl); action='BASE'; route='NONE'; c35=None
        if f629_action:
            if balance:
                route='BALANCE'
                managed,action,c35=f636.resolve35(k,t,tr,base_pnl,base_dt)
            else:
                managed=f629_pnl; action='CUT20'

        rows.append({
          'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
          'parent_pnl':float(tr.pnl),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
          'base_pnl':float(base_pnl),'base_layer':base_layer,
          'watch_active':watch_active,'f629_action':f629_action,'f629_pnl':f629_pnl,
          'flow_guard':flow_guard,'balance_gate':balance,
          'balance_margin':upper-body_exp if lf is not None else float('nan'),
          'rel_last_upper':upper,'rel_body_delta_prev3median':body_exp,
          'f634_pnl':f634_pnl,'f634_action':f634_action,
          'f638_pnl':f638_pnl,'f638_action':f638_action,'f638_route':f638_route,
          'managed_pnl':managed,'action':action,'route':route,
          'incremental_vs_base':managed-float(base_pnl),
          'incremental_vs_f634':managed-f634_pnl,
          'incremental_vs_f638':managed-f638_pnl,
          'higher_close35':None if c35 is None else bool(c35['higher_close']),
        })

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f640_rows.csv',index=False)
    base_m=f634.metrics(df.base_pnl); f634_m=f634.metrics(df.f634_pnl)
    f638_m=f634.metrics(df.f638_pnl); managed_m=f634.metrics(df.managed_pnl)

    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'five-layer parity fail {base_m}')
    if abs(f634_m['pnl']-155.1811622510)>0.10 or f634_m['wins']!=72:
        raise RuntimeError(f'F6.34 parity fail {f634_m}')
    if abs(f638_m['pnl']-157.2014181017)>0.10 or f638_m['wins']!=73:
        raise RuntimeError(f'F6.38 parity fail {f638_m}')

    acts=df[df.f629_action].copy()
    if len(acts)!=12 or (int((acts.parent_pnl>0).sum()),int((acts.parent_pnl<=0).sum()))!=(3,9):
        raise RuntimeError(f'F6.29 action cohort parity {len(acts)} / {(acts.parent_pnl>0).sum()}-{(acts.parent_pnl<=0).sum()}')

    # 2x2 overlap of the old flow guard and exact balance gate on the same 12 actions.
    overlap=[]
    for fg,bg in [(False,False),(False,True),(True,False),(True,True)]:
        s=acts[(acts.flow_guard==fg)&(acts.balance_gate==bg)]
        overlap.append({'flow_guard':fg,'balance_gate':bg,'n':int(len(s)),
                        'winner_n':int((s.parent_pnl>0).sum()),'loser_n':int((s.parent_pnl<=0).sum()),
                        'dates':[str(x) for x in s.date.tolist()]})

    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    delta638=float(managed_m['pnl']-f638_m['pnl'])
    delta634=float(managed_m['pnl']-f634_m['pnl'])
    inc=float(managed_m['pnl']-base_m['pnl'])
    delta638D=float(d.incremental_vs_f638.sum()); delta638V=float(v.incremental_vs_f638.sum())
    incD=float(d.incremental_vs_base.sum()); incV=float(v.incremental_vs_base.sum())
    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    pw=acts[acts.parent_pnl>0]; winners_preserved=int((pw.managed_pnl>0).sum())
    changed=acts[abs(acts.incremental_vs_f638)>1e-12].copy()
    balance_pass=acts[acts.balance_gate].copy(); balance_fail=acts[~acts.balance_gate].copy()

    # Strict simplification screen: replacement must not sacrifice economics or robustness slices.
    screen=bool(delta638>=-1e-9 and delta638D>=-1e-9 and delta638V>=-1e-9 and
                baseline_pos_nonpos==0 and winners_preserved==len(pw) and
                managed_m['wr']>=f638_m['wr']-1e-12 and managed_m['dd']<=f638_m['dd']+1e-9)

    out={
      'status':'SAME_SAMPLE_SIMPLIFICATION_DIAGNOSTIC_ONLY','screen_pass':screen,
      'rule_definition':{
        'candidate':'exact F6.29 +20m cut candidate',
        'removed_from_routing':'F6.31 lower-low + improving-taker flow guard',
        'sole_admission_gate':'exact F6.38 balance: upper-wick ratio > body expansion vs median prior 3 completed 5m bars',
        'gate_pass':'exact F6.34 +35 higher-close watcher','gate_fail':'actual +20m-open cut',
        'tuning':'none; no threshold/lookback/timing/alternate architecture sweep'},
      'frozen_five_layer':base_m,'f634_management':f634_m,'f638_or_architecture':f638_m,'f640_balance_only':managed_m,
      'f629_actions':int(len(acts)),'parent_winners_acted':int(len(pw)),'parent_winners_preserved_positive':winners_preserved,
      'balance_pass_n':int(len(balance_pass)),'balance_pass_winner_loser':[int((balance_pass.parent_pnl>0).sum()),int((balance_pass.parent_pnl<=0).sum())],
      'balance_fail_n':int(len(balance_fail)),'balance_fail_winner_loser':[int((balance_fail.parent_pnl>0).sum()),int((balance_fail.parent_pnl<=0).sum())],
      'flow_balance_overlap':overlap,'changed_vs_f638_n':int(len(changed)),
      'incremental_vs_frozen':inc,'incremental_vs_f634':delta634,'incremental_vs_f638':delta638,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,
      'delta_vs_f638_D':delta638D,'delta_vs_f638_V':delta638V,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,
      'changed_vs_f638_detail':changed[['date','period','parent_pnl','flow_guard','balance_gate','balance_margin','f638_pnl','managed_pnl','f638_action','action','incremental_vs_f638']].to_dict('records'),
      'action_detail':acts[['date','period','parent_pnl','flow_guard','balance_gate','balance_margin','f638_pnl','managed_pnl','f638_action','action','incremental_vs_f638']].to_dict('records'),
      'guardrail':'F6.40 is a same-history simplification diagnostic. F6.39 is robustness, not untouched OOS. Even a PASS cannot freeze the architecture.'}
    (OUT/'f640_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.40 — Balance-Only Architecture Simplification','',
        f"**Simplification screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-history diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact replacement architecture',
        'Ignore F6.31 for routing. Every exact F6.29 +20 candidate is admitted to the existing +35 watcher iff the exact F6.38 balance gate passes; otherwise it is cut at +20. No other rule changes.','',
        '## Economics',
        f"- frozen **{base_m['pnl']:+.3f}** → F6.34 **{f634_m['pnl']:+.3f}** → F6.38 OR-stack **{f638_m['pnl']:+.3f}** → F6.40 balance-only **{managed_m['pnl']:+.3f}**",
        f"- Δ vs F6.38 **{delta638:+.3f}**; D/V **{delta638D:+.3f} / {delta638V:+.3f}**",
        f"- WR **{managed_m['wr']*100:.2f}%**; PF **{managed_m['pf']:.3f}**; DD **{managed_m['dd']:.3f}**",
        f"- acted winners preserved **{winners_preserved}/{len(pw)}**; baseline positive→nonpositive **{baseline_pos_nonpos}**",'',
        '## Balance gate on the 12 F6.29 actions',
        f"- PASS **{len(balance_pass)}** = {(balance_pass.parent_pnl>0).sum()}W / {(balance_pass.parent_pnl<=0).sum()}L",
        f"- FAIL **{len(balance_fail)}** = {(balance_fail.parent_pnl>0).sum()}W / {(balance_fail.parent_pnl<=0).sum()}L",'',
        '## F6.31 × balance overlap']
    for r in overlap:
        md.append(f"- flow {r['flow_guard']} / balance {r['balance_gate']}: **{r['n']}** = {r['winner_n']}W/{r['loser_n']}L; {', '.join(r['dates']) if r['dates'] else 'none'}")
    md += ['', '## Changed vs F6.38']
    if len(changed)==0: md.append('- **No trades changed.** F6.31 is fully redundant on this action cohort.')
    else:
        for _,r in changed.iterrows():
            md.append(f"- `{r.date}` {r.period}: parent {r.parent_pnl:+.3f}; flow {bool(r.flow_guard)}; balance {bool(r.balance_gate)} margin {r.balance_margin:+.4f}; F6.38 {r.f638_action} {r.f638_pnl:+.3f} → F6.40 {r.action} {r.managed_pnl:+.3f}; Δ {r.incremental_vs_f638:+.3f}")
    md += ['', '## Guardrail','Same-history simplification diagnostic only. No freeze/promotion without genuinely new evidence.']
    (OUT/'F6.40_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
