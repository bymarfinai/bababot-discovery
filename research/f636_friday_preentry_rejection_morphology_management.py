#!/usr/bin/env python3
"""F6.36 — Friday pre-entry rejection morphology management.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.34 remain same-sample diagnostics and are NOT frozen.

ONE predeclared structural extension motivated by F6.35; no fitted threshold/timing sweep:
  PREENTRY_REJECTION_MORPH_35
  1) Start from the exact F6.34 architecture.
  2) F6.31 flow-divergence cases still defer to +35m and use the exact F6.34
     +35 higher-close continuation confirmation.
  3) Among F6.29 candidates WITHOUT flow divergence, define the immediate
     pre-entry 5m candle as rejection-like iff:
       - an upper wick is present; AND
       - total wick length > candle body length.
     This is pure candle geometry (wick-dominant), not a fitted magnitude cutoff.
  4) Rejection-like no-divergence cases join the SAME +35 recovery watcher.
     Non-rejection no-divergence cases retain the actual +20m-open cut.
  5) At +35 actual decision open, completed +30->35 close > +25->30 close
     releases to frozen management; otherwise cut at actual +35 open.
  6) Any parent/frozen exit at or before +35 has priority.

Because the morphology was discovered from F6.35 on the same historical sample,
this is a SAME-SAMPLE ECONOMIC DIAGNOSTIC ONLY even if economics improve.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629
import f630_friday_f629_false_positive_forensic as f630
import f631_friday_flow_reversal_recovery_guard as f631
import f634_friday_higher_close35_continuation_management as f634

OUT=Path(os.getenv('F636_OUT','f636_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='PREENTRY_REJECTION_MORPH_35'


def resolve35(k,t,tr,base_pnl,base_dt):
    """Return (pnl, action, state) using the exact F6.34 +35 architecture."""
    dt35=t+pd.Timedelta(minutes=35)
    if pd.Timestamp(tr.exit_t)<=dt35 or (base_dt is not None and pd.Timestamp(base_dt)<=dt35):
        return float(base_pnl),'FROZEN_BEFORE35',None
    c35=f634.continuation35_state(k,t,tr)
    if c35 is None: raise RuntimeError(f'missing causal +35 state {tr.date}')
    if c35[f634.RULE]:
        return float(base_pnl),'CONFIRM35_HOLD',c35
    return float(f616.cut_pnl(float(tr.entry),float(c35['decision_open']))),'CUT35',c35


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
        z=f630.causal20_features(k,t,tr) if watch_active else None

        f629_action=False; f629_pnl=float(base_pnl); guarded20=False
        if st is not None and st[f629.RULE]:
            if base_dt is None or st['decision_t']<pd.Timestamp(base_dt):
                f629_action=True
                f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
                guarded20=bool(gs is not None and gs[f631.RULE])

        # Natural morphology: upper wick exists AND combined wick dominates body.
        pre_body=np.nan; pre_upper=np.nan; pre_wicks=np.nan
        upper_present=False; wick_dominant=False; morphology=False
        if z is not None:
            pre_body=float(z['pre_last_body_ratio'])
            pre_upper=float(z['pre_last_upper_wick_ratio'])
            pre_wicks=float(1.0-pre_body)
            upper_present=bool(pre_upper>0.0)
            wick_dominant=bool(pre_wicks>pre_body)
            morphology=bool(upper_present and wick_dominant)

        # Reconstruct exact F6.34 result first.
        f634_pnl=float(base_pnl); f634_action='BASE'; c35_634=None
        if f629_action and not guarded20:
            f634_pnl=f629_pnl; f634_action='CUT20'
        elif f629_action and guarded20:
            f634_pnl,f634_action,c35_634=resolve35(k,t,tr,base_pnl,base_dt)

        # F6.36: F6.34 plus morphology as a second natural admission gate to same +35 watcher.
        managed=float(base_pnl); action='BASE'; route35=None; c35=None
        if f629_action:
            if guarded20:
                route35='FLOW_DIVERGENCE'
                managed,action,c35=resolve35(k,t,tr,base_pnl,base_dt)
            elif morphology:
                route35='PREENTRY_REJECTION'
                managed,action,c35=resolve35(k,t,tr,base_pnl,base_dt)
            else:
                route35='NONE'
                managed=f629_pnl; action='CUT20'

        row={
          'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
          'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),
          'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
          'base_pnl':float(base_pnl),'base_layer':base_layer,
          'watch_active':watch_active,'f629_action':f629_action,'f629_pnl':f629_pnl,
          'guarded20':guarded20,'pre_body_ratio':pre_body,'pre_upper_wick_ratio':pre_upper,
          'pre_total_wick_ratio':pre_wicks,'upper_wick_present':upper_present,
          'wick_dominant':wick_dominant,'morphology20':morphology,
          'f634_pnl':f634_pnl,'f634_action':f634_action,
          'managed_pnl':managed,'action':action,'route35':route35,
          'incremental_vs_base':managed-float(base_pnl),
          'incremental_vs_f629':managed-f629_pnl,
          'incremental_vs_f634':managed-f634_pnl,
        }
        if gs is not None:
            row.update({'new_lower_low20':bool(gs['new_lower_low']),
                        'taker_improves20':bool(gs['taker_improves']),
                        'taker_change20':float(gs['taker_change'])})
        if c35 is not None:
            row.update({'higher_close35':bool(c35['higher_close']),
                        'current_green35':bool(c35['current_green']),
                        'higher_high35':bool(c35['current_higher_high']),
                        'higher_low35':bool(c35['current_higher_low']),
                        'decision_open35':float(c35['decision_open'])})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f636_rows.csv',index=False)

    base_m=f634.metrics(df.base_pnl)
    f629_m=f634.metrics(df.f629_pnl)
    f634_m=f634.metrics(df.f634_pnl)
    managed_m=f634.metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'five-layer parity fail {base_m}')
    if abs(f629_m['pnl']-147.5396282208)>0.10 or f629_m['wins']!=70:
        raise RuntimeError(f'F6.29 parity fail {f629_m}')
    if abs(f634_m['pnl']-155.1811622510)>0.10 or f634_m['wins']!=72:
        raise RuntimeError(f'F6.34 parity fail {f634_m}')

    watches=df[df.watch_active].copy(); acts=df[df.f629_action].copy()
    if len(watches)!=26 or len(acts)!=12:
        raise RuntimeError(f'watch/action parity {len(watches)}/{len(acts)}')
    nodiv=acts[~acts.guarded20].copy()
    if (int((nodiv.parent_pnl>0).sum()),int((nodiv.parent_pnl<=0).sum()))!=(1,5):
        raise RuntimeError('no-divergence 1W/5L parity failed')
    morph=nodiv[nodiv.morphology20].copy()
    nonmorph=nodiv[~nodiv.morphology20].copy()
    morph_holds=morph[morph.action=='CONFIRM35_HOLD'].copy()
    morph_cuts=morph[morph.action=='CUT35'].copy()
    morph_frozen=morph[morph.action=='FROZEN_BEFORE35'].copy()

    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    inc=float(managed_m['pnl']-base_m['pnl'])
    inc634=float(managed_m['pnl']-f634_m['pnl'])
    incD=float(d.incremental_vs_base.sum()); incV=float(v.incremental_vs_base.sum())
    delta634D=float(d.incremental_vs_f634.sum()); delta634V=float(v.incremental_vs_f634.sum())
    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    parent_winners=acts[acts.parent_pnl>0]
    winners_preserved=int((parent_winners.managed_pnl>0).sum())
    losses=acts[acts.parent_pnl<=0]
    loser_savings=float(losses.incremental_vs_base.sum())
    winner_damage=float(parent_winners.incremental_vs_base.sum())
    morph_loser_cost_vs_f634=float(morph[morph.parent_pnl<=0].incremental_vs_f634.sum())
    morph_winner_gain_vs_f634=float(morph[morph.parent_pnl>0].incremental_vs_f634.sum())
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<.5)&(df.base_layer=='PARENT')]
    defensive=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r<.5)&(acts.base_layer=='PARENT')&acts.action.isin(['CUT20','CUT35'])]

    # Strict diagnostic screen: improve on F6.34, no D/V regression vs F6.34,
    # rescue all acted parent winners, preserve baseline WR, and keep DD no worse than F6.34.
    screen=bool(inc634>0 and delta634D>=-1e-9 and delta634V>=-1e-9 and
                baseline_pos_nonpos==0 and winners_preserved==len(parent_winners) and
                managed_m['wr']>=base_m['wr']-1e-12 and managed_m['dd']<=f634_m['dd']+1e-9)

    out={
      'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY',
      'rule_definition':{
        'parent':'exact F6.34 architecture',
        'morphology':'no-divergence F6.29 candidate; immediate pre-entry 5m upper wick > 0 AND total wick > body',
        'morph_route':'join exact F6.34 +35 watcher',
        'non_morph_route':'retain actual +20m-open cut',
        'confirm35':'+30->35 close > +25->30 close -> frozen HOLD; else actual +35m-open cut',
        'priority':'parent/frozen exit at or before +35 wins',
        'tuning':'none; geometry inequality only; no alternate timing or magnitude sweep'},
      'frozen_five_layer':base_m,'f629_diagnostic':f629_m,'f634_management':f634_m,'f636_management':managed_m,
      'active_watches':int(len(watches)),'f629_actions':int(len(acts)),
      'no_divergence_branch':int(len(nodiv)),'morphology_signals':int(len(morph)),'non_morph_cut20':int(len(nonmorph)),
      'morphology_winner_loser':[int((morph.parent_pnl>0).sum()),int((morph.parent_pnl<=0).sum())],
      'morphology_hold_winner_loser':[int((morph_holds.parent_pnl>0).sum()),int((morph_holds.parent_pnl<=0).sum())],
      'morphology_cut35_winner_loser':[int((morph_cuts.parent_pnl>0).sum()),int((morph_cuts.parent_pnl<=0).sum())],
      'morphology_frozen_before35':int(len(morph_frozen)),
      'parent_winners_acted':int(len(parent_winners)),'parent_winners_preserved_positive':winners_preserved,
      'failure_to_develop_defensively_cut':int(len(defensive)),'f625_target_n':int(len(target)),
      'incremental_vs_frozen':inc,'incremental_vs_f634':inc634,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,
      'delta_vs_f634_D':delta634D,'delta_vs_f634_V':delta634V,
      'morphology_winner_gain_vs_f634':morph_winner_gain_vs_f634,
      'morphology_loser_cost_vs_f634':morph_loser_cost_vs_f634,
      'saved_on_parent_losers_vs_frozen':loser_savings,'damage_on_parent_winners_vs_frozen':winner_damage,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,
      'wr_gain_pp_vs_frozen':float((managed_m['wr']-base_m['wr'])*100),
      'dd_delta_vs_f634':float(managed_m['dd']-f634_m['dd']),
      'screen_pass':screen,
      'no_divergence_detail':nodiv[['date','period','parent_pnl','base_pnl','f634_pnl','managed_pnl','pre_body_ratio','pre_upper_wick_ratio','pre_total_wick_ratio','morphology20','action','incremental_vs_f634']].to_dict('records'),
      'guardrail':'Morphology came from F6.35 on the same sample. D/V are robustness slices only. No promotion even if PASS; no threshold/timing retuning if FAIL.'}
    (OUT/'f636_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.36 — Pre-entry Rejection Morphology Management','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact architecture',
        'Start from F6.34. For the no-flow-divergence +20 branch only, the immediate pre-entry 5m candle is rejection-like when an upper wick is present and total wick length exceeds body length. Rejection-like cases join the existing +35 higher-close watcher; all other no-divergence cases keep the +20 cut. No new timing or confirmation rule is introduced.','',
        '## Routing',
        f'- no-divergence +20 branch **{len(nodiv)}** = {(nodiv.parent_pnl>0).sum()} winner / {(nodiv.parent_pnl<=0).sum()} losers',
        f'- morphology signals **{len(morph)}** = {(morph.parent_pnl>0).sum()} winner / {(morph.parent_pnl<=0).sum()} losers',
        f'- morphology +35 HOLD W/L **{(morph_holds.parent_pnl>0).sum()} / {(morph_holds.parent_pnl<=0).sum()}**; CUT35 W/L **{(morph_cuts.parent_pnl>0).sum()} / {(morph_cuts.parent_pnl<=0).sum()}**','',
        '## Economics',
        f"- frozen **{base_m['pnl']:+.3f}** → F6.34 **{f634_m['pnl']:+.3f}** → F6.36 **{managed_m['pnl']:+.3f}**",
        f"- incremental vs frozen **{inc:+.3f}**; vs F6.34 **{inc634:+.3f}**",
        f"- D/V incremental vs frozen **{incD:+.3f} / {incV:+.3f}**; delta vs F6.34 **{delta634D:+.3f} / {delta634V:+.3f}**",
        f"- WR **{base_m['wr']*100:.2f}% → {managed_m['wr']*100:.2f}%**; PF **{base_m['pf']:.3f} → {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} → {managed_m['dd']:.3f}**",
        f'- acted parent winners preserved positive **{winners_preserved}/{len(parent_winners)}**; baseline positive→nonpositive **{baseline_pos_nonpos}**',
        f'- morphology winner gain vs F6.34 **{morph_winner_gain_vs_f634:+.3f}**; morphology loser cost vs F6.34 **{morph_loser_cost_vs_f634:+.3f}**','',
        '## No-divergence detail']
    for _,r in nodiv.iterrows():
        md.append(f"- `{r.date}` {r.period}: parent {r.parent_pnl:+.3f}; body {r.pre_body_ratio:.3f}; upper-wick {r.pre_upper_wick_ratio:.3f}; total-wick {r.pre_total_wick_ratio:.3f}; morph **{bool(r.morphology20)}** → {r.action}; ΔF6.34 {r.incremental_vs_f634:+.3f}")
    md += ['', '## Guardrail','This is a same-sample economic diagnostic built from F6.35 morphology. Even a PASS cannot promote the rule. If it fails, do not tune wick/body thresholds or +35 timing on these same cases.']
    (OUT/'F6.36_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
