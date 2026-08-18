#!/usr/bin/env python3
"""F6.35 — Friday remaining +20m false-cut winner forensic.

Research only; live BBC untouched. No management rule is tuned or promoted.
Frozen Friday stack remains FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.32/F6.34 remain same-sample diagnostics and are NOT frozen.

Question:
F6.34 solved the flow-divergence branch (2 winners held, 4 losers cut at +35),
but one parent winner remains in the no-divergence branch and is still cut at
+20m. What causal information already known at +20m distinguishes that ONE
remaining false-cut winner from the five correctly defensive no-divergence cuts?

Guardrails:
- +20m information only; no later path leakage;
- no numeric threshold/timing/economic sweep;
- primary cohort is 1 winner vs 5 losers, so primary separation is hypothesis
  generation only and is NEVER sufficient by itself;
- every candidate is cross-checked against a larger branch-matched control:
  active F6.26 WATCH cases that are alive at +20 and do NOT have the F6.31
  lower-low + improving-taker divergence, comparing future winners vs true-dead;
- broader 13-winner vs 9-true-dead control is also reported;
- D/V direction is reported for branch-matched control when both classes exist.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629
import f630_friday_f629_false_positive_forensic as f630
import f631_friday_flow_reversal_recovery_guard as f631

OUT=Path(os.getenv('F635_OUT','f635_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N


def auc_winner_high(w,l,col):
    a=w[col].to_numpy(float); b=l[col].to_numpy(float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def sep(w,l,col):
    a=auc_winner_high(w,l,col)
    return {
      'auc_winner_high':a,
      'strength':float(max(a,1-a)) if np.isfinite(a) else np.nan,
      'direction':'higher=winner' if np.isfinite(a) and a>=.5 else 'lower=winner',
      'winner_median':float(w[col].median()) if len(w) and w[col].notna().any() else np.nan,
      'loss_median':float(l[col].median()) if len(l) and l[col].notna().any() else np.nan,
      'n_winner':int(w[col].notna().sum()),'n_loss':int(l[col].notna().sum())}


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

        z=None; gs=None; st=None; f629_action=False; guarded20=False
        if watch_active:
            z=f630.causal20_features(k,t,tr)
            gs=f631.guard_state(k,t,tr)
            st=f629.candidate_state(k,t,tr)
            if st is not None and st[f629.RULE]:
                f629_action=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
            if f629_action:
                guarded20=bool(gs is not None and gs[f631.RULE])

        row={
          'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
          'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),
          'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
          'base_pnl':float(base_pnl),'base_layer':base_layer,
          'watch_active':watch_active,'alive20_features':bool(z is not None),
          'f629_action':f629_action,'guarded20':guarded20,
          'no_divergence20':bool(gs is not None and not gs[f631.RULE])}
        if z is not None: row.update(z)
        if gs is not None:
            row.update({
              'guard_new_lower_low':float(gs['new_lower_low']),
              'guard_taker_improves':float(gs['taker_improves']),
              'guard_taker_change':float(gs['taker_change'])})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f635_rows.csv',index=False)

    watches=df[df.watch_active].copy()
    acts=df[df.f629_action].copy()
    primary=acts[~acts.guarded20].copy()
    pw=primary[primary.parent_pnl>0].copy(); pl=primary[primary.parent_pnl<=0].copy()
    if len(watches)!=26 or len(acts)!=12 or (len(pw),len(pl))!=(1,5):
        raise RuntimeError(f'parity watches/acts/primary W-L {len(watches)}/{len(acts)}/{len(pw)}-{len(pl)}')

    # Branch-matched larger control: only +20-alive WATCH cases with NO F6.31 divergence.
    branch=df[(df.watch_active)&(df.alive20_features)&(df.no_divergence20)].copy()
    bw=branch[branch.parent_pnl>0].copy()
    bd=branch[(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')].copy()

    # Broader F6.27/F6.30 external control, regardless of divergence branch.
    broad=df[(df.watch_active)&(df.alive20_features)].copy()
    ew=broad[broad.parent_pnl>0].copy()
    ed=broad[(broad.parent_pnl<=0)&(broad.parent_mfe_r<.5)&(broad.base_layer=='PARENT')].copy()

    exclude={'i','period','date','parent_pnl','parent_win','parent_mfe_r','parent_mae_r','base_pnl','base_layer',
             'watch_active','alive20_features','f629_action','guarded20','no_divergence20'}
    cols=[c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

    stats=[]
    for col in cols:
        if not pw[col].notna().sum() or not pl[col].notna().sum(): continue
        p=sep(pw,pl,col)
        bm=sep(bw,bd,col) if len(bw) and len(bd) and bw[col].notna().sum() and bd[col].notna().sum() else None
        br=sep(ew,ed,col) if len(ew) and len(ed) and ew[col].notna().sum() and ed[col].notna().sum() else None
        dv={}
        for name,sub in [('D',branch[branch.i<SPLIT]),('V',branch[branch.i>=SPLIT])]:
            sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
            dv[name]=sep(sw,sd,col) if len(sw) and len(sd) and sw[col].notna().sum() and sd[col].notna().sum() else None
        agree_bm=bool(bm is not None and bm['direction']==p['direction'])
        agree_br=bool(br is not None and br['direction']==p['direction'])
        agree_dv=True
        dv_available=0
        for s in dv.values():
            if s is not None:
                dv_available+=1
                agree_dv=agree_dv and (s['direction']==p['direction'])
        stats.append({
          'feature':col,'primary':p,'branch_control':bm,'broad_control':br,'branch_DV':dv,
          'direction_agrees_branch':agree_bm,'direction_agrees_broad':agree_br,
          'direction_agrees_available_DV':bool(agree_dv),'dv_slices_available':dv_available})

    # Rank by external reproducibility first, not by the one primary winner.
    def key(r):
        bm=r['branch_control']; br=r['broad_control']
        return (r['direction_agrees_branch'] and r['direction_agrees_broad'] and r['direction_agrees_available_DV'],
                r['dv_slices_available'],
                bm['strength'] if bm else -1,
                br['strength'] if br else -1,
                r['primary']['strength'])
    stats.sort(key=key,reverse=True)

    # Natural booleans: strongest protection against single-case overfitting.
    bools=[]
    for col in cols:
        vals=set(df[col].dropna().unique().tolist())
        if not vals.issubset({0,1,0.0,1.0}): continue
        if not pw[col].notna().sum() or not pl[col].notna().sum(): continue
        pval=float(pw[col].iloc[0]); lrate=float(pl[col].mean())
        bwr=float(bw[col].mean()) if len(bw) and bw[col].notna().any() else np.nan
        bdr=float(bd[col].mean()) if len(bd) and bd[col].notna().any() else np.nan
        ewr=float(ew[col].mean()) if len(ew) and ew[col].notna().any() else np.nan
        edr=float(ed[col].mean()) if len(ed) and ed[col].notna().any() else np.nan
        primary_gap=pval-lrate
        branch_gap=bwr-bdr if np.isfinite(bwr) and np.isfinite(bdr) else np.nan
        broad_gap=ewr-edr if np.isfinite(ewr) and np.isfinite(edr) else np.nan
        bools.append({
          'feature':col,'primary_winner_value':pval,'primary_loss_rate':lrate,'primary_gap':primary_gap,
          'branch_winner_rate':bwr,'branch_dead_rate':bdr,'branch_gap':branch_gap,
          'broad_winner_rate':ewr,'broad_dead_rate':edr,'broad_gap':broad_gap,
          'same_direction_branch':bool(np.isfinite(branch_gap) and primary_gap*branch_gap>0),
          'same_direction_broad':bool(np.isfinite(broad_gap) and primary_gap*broad_gap>0)})
    bools.sort(key=lambda r:(r['same_direction_branch'] and r['same_direction_broad'],
                             abs(r['branch_gap']) if np.isfinite(r['branch_gap']) else -1,
                             abs(r['broad_gap']) if np.isfinite(r['broad_gap']) else -1,
                             abs(r['primary_gap'])),reverse=True)

    top=[]
    for r in stats:
        if r['direction_agrees_branch'] and r['direction_agrees_broad'] and r['direction_agrees_available_DV']:
            top.append(r)
        if len(top)>=15: break

    out={
      'status':'FORENSIC_ONLY_NO_RULE',
      'primary':{
        'winner_n':int(len(pw)),'loser_n':int(len(pl)),
        'winner_date':str(pw.iloc[0].date),'winner_parent_pnl':float(pw.iloc[0].parent_pnl),
        'loser_dates':[str(x) for x in pl.date.tolist()]},
      'branch_matched_control':{
        'winner_n':int(len(bw)),'true_dead_n':int(len(bd)),
        'D_winner_n':int(((branch.i<SPLIT)&(branch.parent_pnl>0)).sum()),
        'D_dead_n':int(((branch.i<SPLIT)&(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')).sum()),
        'V_winner_n':int(((branch.i>=SPLIT)&(branch.parent_pnl>0)).sum()),
        'V_dead_n':int(((branch.i>=SPLIT)&(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')).sum())},
      'broad_control':{'winner_n':int(len(ew)),'true_dead_n':int(len(ed))},
      'top_reproducible_continuous':top,
      'top_natural_boolean':bools[:20],
      'guardrail':'One primary winner cannot validate a rule. Use only +20m causal information; no threshold/timing/economic rule may be promoted from F6.35.'}
    (OUT/'f635_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.35 — Remaining +20m False-Cut Winner Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**',
        '**Live BBC untouched; F6.34 remains same-sample diagnostic and is NOT frozen.**','',
        '## Cohorts',
        f"- primary no-divergence +20 cuts: **1 future winner vs 5 losers**; winner `{pw.iloc[0].date}`",
        f"- branch-matched +20-alive WATCH control: **{len(bw)} winners vs {len(bd)} true-dead**",
        f"- branch D/V: **{out['branch_matched_control']['D_winner_n']}/{out['branch_matched_control']['D_dead_n']}** W/dead and **{out['branch_matched_control']['V_winner_n']}/{out['branch_matched_control']['V_dead_n']}** W/dead",
        f"- broad control: **{len(ew)} winners vs {len(ed)} true-dead**",'',
        '## Strongest +20m features with direction agreement in primary + branch + broad + available D/V']
    for r in top[:12]:
        p=r['primary']; bm=r['branch_control']; br=r['broad_control']
        dv=[]
        for name in ['D','V']:
            s=r['branch_DV'][name]
            if s is not None: dv.append(f"{name} {s['strength']:.3f}")
        md.append(f"- `{r['feature']}`: primary **{p['strength']:.3f} {p['direction']}** (winner/loss med {p['winner_median']:.4f}/{p['loss_median']:.4f}); branch **{bm['strength']:.3f}**; broad **{br['strength']:.3f}**; " + ', '.join(dv))
    md += ['', '## Natural boolean clues']
    for r in bools[:12]:
        md.append(f"- `{r['feature']}`: primary winner/loss-rate **{100*r['primary_winner_value']:.1f}%/{100*r['primary_loss_rate']:.1f}%**; branch W/dead **{100*r['branch_winner_rate']:.1f}%/{100*r['branch_dead_rate']:.1f}%**; broad W/dead **{100*r['broad_winner_rate']:.1f}%/{100*r['broad_dead_rate']:.1f}%**; agree branch/broad **{r['same_direction_branch']}/{r['same_direction_broad']}**")
    md += ['', '## Guardrail','There is only one remaining primary winner. A perfect-looking separator is not evidence by itself. The only useful output is a causal hypothesis whose direction also persists in the larger branch-matched and broad controls. No rule is promoted from this run.']
    (OUT/'F6.35_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
