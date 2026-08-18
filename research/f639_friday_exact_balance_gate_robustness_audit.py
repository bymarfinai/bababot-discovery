#!/usr/bin/env python3
"""F6.39 — Friday exact F6.38 balance-gate robustness audit.

Research only; live BBC untouched. NO economic management rule is changed,
tuned, or promoted. Frozen Friday stack remains unchanged.

The F6.38 gate is frozen EXACTLY as selected previously:
    upper_wick_ratio > body_ratio_expansion_vs_median_prior_3_completed_5m_bars

This run asks only whether that exact boolean inequality is winner-enriched in
larger controls and temporally robust. No alternate threshold, lookback, timing,
EMA, or economic action is evaluated.

Predeclared robustness screen:
1) branch-matched winner gate rate > true-dead gate rate;
2) broad winner gate rate > true-dead gate rate;
3) branch D and V gaps are each non-negative whenever both classes exist;
4) every leave-one-calendar-year-out branch pool with both classes retains a
   strictly positive winner-minus-dead gate-rate gap.

D/V and calendar slices are robustness checks, NOT untouched OOS, because this
historical sample has already been examined in prior Friday forensics.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629
import f630_friday_f629_false_positive_forensic as f630
import f631_friday_flow_reversal_recovery_guard as f631
import f637_friday_relative_upper_rejection_forensic as f637

OUT=Path(os.getenv('F639_OUT','f639_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='EXACT_F638_BALANCE_GATE'


def rate_stats(w,d):
    wv=w[RULE].astype(float); dv=d[RULE].astype(float)
    wr=float(wv.mean()) if len(wv) else np.nan
    dr=float(dv.mean()) if len(dv) else np.nan
    return {
      'winner_n':int(len(wv)),'dead_n':int(len(dv)),
      'winner_gate_n':int(wv.sum()) if len(wv) else 0,
      'dead_gate_n':int(dv.sum()) if len(dv) else 0,
      'winner_gate_rate':wr,'dead_gate_rate':dr,
      'gap_winner_minus_dead':float(wr-dr) if np.isfinite(wr) and np.isfinite(dr) else np.nan,
    }


def auc_winner_high(w,d,col):
    a=w[col].to_numpy(float); b=d[col].to_numpy(float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def hypergeom_enrichment_p(w,d):
    """One-sided label-exchangeability p-value for >= observed winner gate hits."""
    nw=len(w); nd=len(d); n=nw+nd
    if nw==0 or nd==0:return np.nan
    kw=int(w[RULE].sum()); kd=int(d[RULE].sum()); K=kw+kd
    lo=max(0,nw-(n-K)); hi=min(nw,K)
    den=math.comb(n,nw)
    if den==0:return np.nan
    return float(sum(math.comb(K,x)*math.comb(n-K,nw-x) for x in range(max(kw,lo),hi+1))/den)


def classify_controls(df):
    branch=df[(df.watch_active)&(df.alive20_features)&(df.no_divergence20)].copy()
    bw=branch[branch.parent_pnl>0].copy()
    bd=branch[(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')].copy()
    broad=df[(df.watch_active)&(df.alive20_features)].copy()
    ew=broad[broad.parent_pnl>0].copy()
    ed=broad[(broad.parent_pnl<=0)&(broad.parent_mfe_r<.5)&(broad.base_layer=='PARENT')].copy()
    return branch,bw,bd,broad,ew,ed


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
        action=False
        if st is not None and st[f629.RULE]:
            action=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
        guarded=bool(action and gs is not None and gs[f631.RULE])

        lf=f637.local_features(k,t)
        upper=float(lf['rel_last_upper']) if lf is not None else np.nan
        body_exp=float(lf['rel_body_delta_prev3median']) if lf is not None else np.nan
        margin=float(upper-body_exp) if np.isfinite(upper) and np.isfinite(body_exp) else np.nan
        gate=bool(upper>body_exp) if np.isfinite(upper) and np.isfinite(body_exp) else False

        row={
          'i':i,'period':'discovery' if i<SPLIT else 'validation','date':str(tr.date),
          'year':int(pd.Timestamp(tr.date).year),
          'parent_pnl':float(tr.pnl),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
          'base_pnl':float(base_pnl),'base_layer':base_layer,
          'watch_active':watch_active,'alive20_features':bool(z is not None),
          'f629_action':action,'guarded20':guarded,
          'no_divergence20':bool(gs is not None and not gs[f631.RULE]),
          'upper_wick_ratio':upper,'body_expansion_prev3median':body_exp,
          'balance_margin':margin,RULE:gate,
        }
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f639_rows.csv',index=False)

    watches=df[df.watch_active].copy(); acts=df[df.f629_action].copy(); nodiv_acts=acts[~acts.guarded20].copy()
    if len(watches)!=26 or len(acts)!=12 or (int((nodiv_acts.parent_pnl>0).sum()),int((nodiv_acts.parent_pnl<=0).sum()))!=(1,5):
        raise RuntimeError(f'F6.38 parity watches/acts/nodiv {len(watches)}/{len(acts)}/{(nodiv_acts.parent_pnl>0).sum()}-{(nodiv_acts.parent_pnl<=0).sum()}')
    # Exact F6.38 economic-branch gate parity: one winner passes, zero losers pass.
    if (int(nodiv_acts[nodiv_acts.parent_pnl>0][RULE].sum()),int(nodiv_acts[nodiv_acts.parent_pnl<=0][RULE].sum()))!=(1,0):
        raise RuntimeError('exact F6.38 gate parity failed')

    branch,bw,bd,broad,ew,ed=classify_controls(df)
    if (len(bw),len(bd),len(ew),len(ed))!=(8,6,13,9):
        raise RuntimeError(f'control parity {len(bw)}/{len(bd)}/{len(ew)}/{len(ed)}')

    branch_stats=rate_stats(bw,bd); branch_stats['margin_auc_winner_high']=auc_winner_high(bw,bd,'balance_margin'); branch_stats['gate_enrichment_p_one_sided']=hypergeom_enrichment_p(bw,bd)
    broad_stats=rate_stats(ew,ed); broad_stats['margin_auc_winner_high']=auc_winner_high(ew,ed,'balance_margin'); broad_stats['gate_enrichment_p_one_sided']=hypergeom_enrichment_p(ew,ed)

    dv={}; dv_nonnegative=True; dv_available=0
    for name,mask in [('D',branch.i<SPLIT),('V',branch.i>=SPLIT)]:
        sub=branch[mask].copy()
        sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
        if len(sw) and len(sd):
            s=rate_stats(sw,sd); s['margin_auc_winner_high']=auc_winner_high(sw,sd,'balance_margin'); s['gate_enrichment_p_one_sided']=hypergeom_enrichment_p(sw,sd)
            dv[name]=s; dv_available+=1
            dv_nonnegative=dv_nonnegative and s['gap_winner_minus_dead']>=-1e-12
        else:
            dv[name]={'winner_n':len(sw),'dead_n':len(sd),'insufficient_both_classes':True}

    # Fixed calendar-year temporal atlas and leave-one-calendar-year-out sensitivity.
    years=sorted(int(y) for y in branch.year.unique())
    yearly={}
    for y in years:
        sub=branch[branch.year==y]
        sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
        if len(sw) and len(sd):
            s=rate_stats(sw,sd); s['margin_auc_winner_high']=auc_winner_high(sw,sd,'balance_margin')
            yearly[str(y)]=s
        else:
            yearly[str(y)]={'winner_n':int(len(sw)),'dead_n':int(len(sd)),'insufficient_both_classes':True,
                            'winner_gate_n':int(sw[RULE].sum()) if len(sw) else 0,'dead_gate_n':int(sd[RULE].sum()) if len(sd) else 0}

    loyo={}; loyo_positive=True; loyo_available=0
    for y in years:
        sub=branch[branch.year!=y]
        sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
        if len(sw) and len(sd):
            s=rate_stats(sw,sd); s['margin_auc_winner_high']=auc_winner_high(sw,sd,'balance_margin')
            loyo[str(y)]=s; loyo_available+=1
            loyo_positive=loyo_positive and s['gap_winner_minus_dead']>0
        else:
            loyo[str(y)]={'winner_n':int(len(sw)),'dead_n':int(len(sd)),'insufficient_both_classes':True}

    screen=bool(branch_stats['gap_winner_minus_dead']>0 and broad_stats['gap_winner_minus_dead']>0 and
                dv_available>=2 and dv_nonnegative and loyo_available>0 and loyo_positive)

    out={
      'status':'ROBUSTNESS_FORENSIC_ONLY_NO_PROMOTION',
      'robustness_screen_pass':screen,
      'exact_gate':'upper_wick_ratio > body_ratio_expansion_vs_median_prior_3_completed_5m_bars',
      'f638_economic_branch_parity':{
        'winner_n':int((nodiv_acts.parent_pnl>0).sum()),'loser_n':int((nodiv_acts.parent_pnl<=0).sum()),
        'winner_gate_n':int(nodiv_acts[nodiv_acts.parent_pnl>0][RULE].sum()),'loser_gate_n':int(nodiv_acts[nodiv_acts.parent_pnl<=0][RULE].sum())},
      'branch_matched':branch_stats,
      'broad_control':broad_stats,
      'branch_DV':dv,
      'calendar_year_atlas':yearly,
      'leave_one_calendar_year_out':loyo,
      'screen_requirements':{
        'branch_gap_strict_positive':branch_stats['gap_winner_minus_dead']>0,
        'broad_gap_strict_positive':broad_stats['gap_winner_minus_dead']>0,
        'D_and_V_nonnegative':bool(dv_available>=2 and dv_nonnegative),
        'all_available_leave_one_year_out_strict_positive':bool(loyo_available>0 and loyo_positive)},
      'branch_gate_rows':branch[['date','year','period','parent_pnl','parent_mfe_r','base_layer','upper_wick_ratio','body_expansion_prev3median','balance_margin',RULE]].to_dict('records'),
      'guardrail':'Exact F6.38 gate only. No tuning or economic retest. All chronology slices are robustness checks, not untouched OOS.'
    }
    (OUT/'f639_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.39 — Exact F6.38 Balance-Gate Robustness Audit','',
        f"**Robustness screen: {'PASS' if screen else 'FAIL'}**",
        '**FORENSIC ONLY — no promotion; live BBC untouched.**','',
        '## Frozen exact gate',
        '`upper_wick_ratio > body_expansion_vs_median_prior_3_completed_5m_bars`','',
        'No threshold, alternate lookback, timing, EMA, or economic action was tested.','',
        '## Branch-matched control (8 future winners vs 6 true-dead)',
        f"- gate winner/dead: **{branch_stats['winner_gate_n']}/{branch_stats['winner_n']} ({branch_stats['winner_gate_rate']*100:.1f}%) vs {branch_stats['dead_gate_n']}/{branch_stats['dead_n']} ({branch_stats['dead_gate_rate']*100:.1f}%)**",
        f"- winner-minus-dead gap **{branch_stats['gap_winner_minus_dead']*100:+.1f}pp**; balance-margin AUC **{branch_stats['margin_auc_winner_high']:.3f}**; one-sided enrichment p **{branch_stats['gate_enrichment_p_one_sided']:.4f}**",'',
        '## Broad control (13 future winners vs 9 true-dead)',
        f"- gate winner/dead: **{broad_stats['winner_gate_n']}/{broad_stats['winner_n']} ({broad_stats['winner_gate_rate']*100:.1f}%) vs {broad_stats['dead_gate_n']}/{broad_stats['dead_n']} ({broad_stats['dead_gate_rate']*100:.1f}%)**",
        f"- winner-minus-dead gap **{broad_stats['gap_winner_minus_dead']*100:+.1f}pp**; balance-margin AUC **{broad_stats['margin_auc_winner_high']:.3f}**; one-sided enrichment p **{broad_stats['gate_enrichment_p_one_sided']:.4f}**",'',
        '## D/V branch robustness']
    for name,s in dv.items():
        if s.get('insufficient_both_classes'):
            md.append(f"- {name}: insufficient both classes ({s['winner_n']}W/{s['dead_n']}D)")
        else:
            md.append(f"- {name}: gate **{s['winner_gate_n']}/{s['winner_n']} W vs {s['dead_gate_n']}/{s['dead_n']} dead**; gap **{s['gap_winner_minus_dead']*100:+.1f}pp**; margin AUC **{s['margin_auc_winner_high']:.3f}**")
    md += ['', '## Leave-one-calendar-year-out branch sensitivity']
    for y,s in loyo.items():
        if s.get('insufficient_both_classes'):
            md.append(f"- omit {y}: insufficient both classes")
        else:
            md.append(f"- omit {y}: {s['winner_gate_n']}/{s['winner_n']} W vs {s['dead_gate_n']}/{s['dead_n']} dead; gap **{s['gap_winner_minus_dead']*100:+.1f}pp**; AUC **{s['margin_auc_winner_high']:.3f}**")
    md += ['', '## Guardrail','This is robustness evidence on already-inspected history, not untouched OOS. Even a PASS does not freeze or promote F6.38.']
    (OUT/'F6.39_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
