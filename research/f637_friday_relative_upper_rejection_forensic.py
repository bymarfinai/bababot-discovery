#!/usr/bin/env python3
"""F6.37 — Friday relative upper-rejection forensic.

Research only; live BBC untouched. NO management rule is tuned/promoted.
Frozen Friday stack remains FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.34/F6.36 remain same-sample diagnostics and are NOT frozen.

Question:
F6.36 rescued the one remaining no-divergence future winner, but its wick-dominant
morphology also admitted two validation losers. Is the winner's upper rejection
RELATIVELY unusual versus the immediately preceding local 5m context?

Predeclared feature family (entry-time causal only):
- last pre-entry upper-wick ratio versus previous 1 / previous 2 max / previous 3 max;
- upper-vs-lower wick dominance;
- body contraction versus previous bar / previous-3 median;
- upper-wick share expansion versus previous-3 median;
- ONE conceptual composite: last upper wick is a 4-bar local maximum AND body is
  smaller than the median body of the prior 3 bars.
No fitted magnitude threshold, timing sweep, or economic test is performed.
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

OUT=Path(os.getenv('F637_OUT','f637_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N


def geom(bar):
    o=float(bar.open); h=float(bar.high); l=float(bar.low); c=float(bar.close)
    rg=max(h-l,1e-12)
    body=abs(c-o)/rg
    uw=(h-max(o,c))/rg
    lw=(min(o,c)-l)/rg
    wick=uw+lw
    share=uw/wick if wick>0 else np.nan
    return {'body':body,'upper':uw,'lower':lw,'wick':wick,'upper_share':share,'red':float(c<o)}


def local_features(k,t):
    x=k[(k.index>=t-pd.Timedelta(minutes=20))&(k.index<t)]
    if len(x)!=4:return None
    g=[geom(x.iloc[j]) for j in range(4)]
    p3,p2,p1,last=g[0],g[1],g[2],g[3]
    prev3_upper=np.array([p3['upper'],p2['upper'],p1['upper']],dtype=float)
    prev3_body=np.array([p3['body'],p2['body'],p1['body']],dtype=float)
    prev3_share=np.array([p3['upper_share'],p2['upper_share'],p1['upper_share']],dtype=float)
    prev2_upper=np.array([p2['upper'],p1['upper']],dtype=float)
    med_share=float(np.nanmedian(prev3_share)) if np.isfinite(prev3_share).any() else np.nan
    upper_localmax4=bool(last['upper']>float(np.max(prev3_upper)))
    body_contract3=bool(last['body']<float(np.median(prev3_body)))
    return {
      'rel_last_upper':last['upper'],
      'rel_last_lower':last['lower'],
      'rel_last_body':last['body'],
      'rel_last_upper_share':last['upper_share'],
      'rel_upper_minus_lower':last['upper']-last['lower'],
      'rel_upper_delta_prev1':last['upper']-p1['upper'],
      'rel_upper_delta_prev2max':last['upper']-float(np.max(prev2_upper)),
      'rel_upper_delta_prev3max':last['upper']-float(np.max(prev3_upper)),
      'rel_upper_delta_prev3median':last['upper']-float(np.median(prev3_upper)),
      'rel_body_delta_prev1':last['body']-p1['body'],
      'rel_body_delta_prev3median':last['body']-float(np.median(prev3_body)),
      'rel_upper_share_delta_prev3median':last['upper_share']-med_share if np.isfinite(last['upper_share']) and np.isfinite(med_share) else np.nan,
      'rel_last_upper_gt_lower':float(last['upper']>last['lower']),
      'rel_upper_gt_prev1':float(last['upper']>p1['upper']),
      'rel_upper_gt_prev2max':float(last['upper']>float(np.max(prev2_upper))),
      'rel_upper_localmax4':float(upper_localmax4),
      'rel_body_lt_prev1':float(last['body']<p1['body']),
      'rel_body_contract3median':float(body_contract3),
      'rel_upper_share_gt_prev3median':float(np.isfinite(last['upper_share']) and np.isfinite(med_share) and last['upper_share']>med_share),
      'rel_rejection_expansion_composite':float(upper_localmax4 and body_contract3),
      'rel_last_red':last['red'],
      # F6.36 geometry parity fields
      'rel_upper_present':float(last['upper']>0),
      'rel_wick_dominant':float(last['wick']>last['body']),
      'rel_f636_morphology':float(last['upper']>0 and last['wick']>last['body']),
    }


def auc_winner_high(w,l,col):
    a=w[col].to_numpy(float); b=l[col].to_numpy(float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def sep(w,l,col):
    a=auc_winner_high(w,l,col)
    return {'auc_winner_high':a,'strength':float(max(a,1-a)) if np.isfinite(a) else np.nan,
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
        st=f629.candidate_state(k,t,tr) if watch_active else None
        gs=f631.guard_state(k,t,tr) if watch_active else None
        z=f630.causal20_features(k,t,tr) if watch_active else None
        action=False
        if st is not None and st[f629.RULE]:
            action=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
        guarded=bool(action and gs is not None and gs[f631.RULE])
        lf=local_features(k,t)
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'watch_active':watch_active,
             'alive20_features':bool(z is not None),'f629_action':action,'guarded20':guarded,
             'no_divergence20':bool(gs is not None and not gs[f631.RULE])}
        if lf:row.update(lf)
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f637_rows.csv',index=False)

    watches=df[df.watch_active].copy()
    acts=df[df.f629_action].copy()
    nodiv=acts[~acts.guarded20].copy()
    primary=nodiv[nodiv.rel_f636_morphology==1].copy()
    pw=primary[primary.parent_pnl>0].copy(); pl=primary[primary.parent_pnl<=0].copy()
    if len(watches)!=26 or len(acts)!=12 or (len(nodiv),len(pw),len(pl))!=(6,1,2):
        raise RuntimeError(f'parity watches/acts/nodiv/primary {len(watches)}/{len(acts)}/{len(nodiv)}/{len(pw)}-{len(pl)}')

    # Branch-matched control from F6.35: +20-alive WATCH, no F6.31 divergence.
    branch=df[(df.watch_active)&(df.alive20_features)&(df.no_divergence20)].copy()
    bw=branch[branch.parent_pnl>0].copy()
    bd=branch[(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')].copy()
    broad=df[(df.watch_active)&(df.alive20_features)].copy()
    ew=broad[broad.parent_pnl>0].copy()
    ed=broad[(broad.parent_pnl<=0)&(broad.parent_mfe_r<.5)&(broad.base_layer=='PARENT')].copy()
    if (len(bw),len(bd),len(ew),len(ed))!=(8,6,13,9):
        raise RuntimeError(f'control parity {len(bw)}/{len(bd)}/{len(ew)}/{len(ed)}')

    cols=[c for c in df.columns if c.startswith('rel_')]
    continuous=[]; booleans=[]
    for col in cols:
        vals=set(df[col].dropna().unique().tolist())
        if vals.issubset({0,1,0.0,1.0}):
            if not pw[col].notna().sum() or not pl[col].notna().sum():continue
            pval=float(pw[col].iloc[0]); lrate=float(pl[col].mean())
            bwr=float(bw[col].mean()); bdr=float(bd[col].mean())
            ewr=float(ew[col].mean()); edr=float(ed[col].mean())
            pg=pval-lrate; bg=bwr-bdr; eg=ewr-edr
            dv={}
            dv_agree=True; avail=0
            for name,sub in [('D',branch[branch.i<SPLIT]),('V',branch[branch.i>=SPLIT])]:
                sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
                if len(sw) and len(sd):
                    gap=float(sw[col].mean()-sd[col].mean()); dv[name]={'winner_rate':float(sw[col].mean()),'dead_rate':float(sd[col].mean()),'gap':gap}; avail+=1
                    if pg!=0:dv_agree=dv_agree and (pg*gap>=0)
            booleans.append({'feature':col,'primary_winner_value':pval,'primary_loss_rate':lrate,'primary_gap':pg,
                             'branch_winner_rate':bwr,'branch_dead_rate':bdr,'branch_gap':bg,
                             'broad_winner_rate':ewr,'broad_dead_rate':edr,'broad_gap':eg,
                             'same_direction_branch':bool(pg*bg>=0 if pg!=0 else False),
                             'same_direction_broad':bool(pg*eg>=0 if pg!=0 else False),
                             'branch_DV':dv,'direction_agrees_available_DV':bool(dv_agree),'dv_slices_available':avail})
        else:
            if not pw[col].notna().sum() or not pl[col].notna().sum():continue
            p=sep(pw,pl,col); bm=sep(bw,bd,col); br=sep(ew,ed,col)
            dv={}; agree=True; avail=0
            for name,sub in [('D',branch[branch.i<SPLIT]),('V',branch[branch.i>=SPLIT])]:
                sw=sub[sub.parent_pnl>0]; sd=sub[(sub.parent_pnl<=0)&(sub.parent_mfe_r<.5)&(sub.base_layer=='PARENT')]
                if len(sw) and len(sd):
                    s=sep(sw,sd,col); dv[name]=s; avail+=1; agree=agree and (s['direction']==p['direction'])
            continuous.append({'feature':col,'primary':p,'branch_control':bm,'broad_control':br,'branch_DV':dv,
                               'direction_agrees_branch':bm['direction']==p['direction'],
                               'direction_agrees_broad':br['direction']==p['direction'],
                               'direction_agrees_available_DV':bool(agree),'dv_slices_available':avail})

    continuous.sort(key=lambda r:(r['direction_agrees_branch'] and r['direction_agrees_broad'] and r['direction_agrees_available_DV'],
                                  r['dv_slices_available'],r['branch_control']['strength'],r['broad_control']['strength'],r['primary']['strength']),reverse=True)
    booleans.sort(key=lambda r:(r['same_direction_branch'] and r['same_direction_broad'] and r['direction_agrees_available_DV'],
                               r['dv_slices_available'],abs(r['branch_gap']),abs(r['broad_gap']),abs(r['primary_gap'])),reverse=True)

    out={'status':'FORENSIC_ONLY_NO_RULE',
         'primary':{'winner_n':len(pw),'loser_n':len(pl),'winner_date':str(pw.iloc[0].date),'loser_dates':[str(x) for x in pl.date.tolist()]},
         'branch_control':{'winner_n':len(bw),'true_dead_n':len(bd),'D_winner_n':int(((branch.i<SPLIT)&(branch.parent_pnl>0)).sum()),'D_dead_n':int(((branch.i<SPLIT)&(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')).sum()),'V_winner_n':int(((branch.i>=SPLIT)&(branch.parent_pnl>0)).sum()),'V_dead_n':int(((branch.i>=SPLIT)&(branch.parent_pnl<=0)&(branch.parent_mfe_r<.5)&(branch.base_layer=='PARENT')).sum())},
         'broad_control':{'winner_n':len(ew),'true_dead_n':len(ed)},
         'top_relative_continuous':continuous[:20],'top_relative_boolean':booleans[:20],
         'primary_detail':primary[['date','period','parent_pnl','rel_last_upper','rel_last_lower','rel_last_body','rel_upper_delta_prev1','rel_upper_delta_prev3max','rel_body_delta_prev3median','rel_upper_localmax4','rel_body_contract3median','rel_rejection_expansion_composite']].to_dict('records'),
         'guardrail':'Relative-morphology forensic only. No threshold/timing/economic rule may be promoted from F6.37; primary is 1W/2L and same-sample.'}
    (OUT/'f637_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.37 — Relative Upper-Rejection Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**','**Live BBC untouched.**','',
        '## Cohorts',f'- primary F6.36 morphology signals: **{len(pw)} winner vs {len(pl)} losers**',f'- branch-matched no-divergence control: **{len(bw)} winners vs {len(bd)} true-dead**',f'- broad control: **{len(ew)} winners vs {len(ed)} true-dead**','',
        '## Strongest relative continuous features with direction agreement']
    for r in continuous[:10]:
        p=r['primary']; bm=r['branch_control']; br=r['broad_control']; dv=', '.join(f"{n} {s['strength']:.3f}" for n,s in r['branch_DV'].items())
        md.append(f"- `{r['feature']}`: primary **{p['strength']:.3f} {p['direction']}** ({p['winner_median']:.4f}/{p['loss_median']:.4f}); branch **{bm['strength']:.3f}**; broad **{br['strength']:.3f}**; {dv}")
    md += ['', '## Natural relative-state clues']
    for r in booleans[:12]:
        md.append(f"- `{r['feature']}`: primary W/L-rate **{100*r['primary_winner_value']:.1f}%/{100*r['primary_loss_rate']:.1f}%**; branch W/dead **{100*r['branch_winner_rate']:.1f}%/{100*r['branch_dead_rate']:.1f}%**; broad W/dead **{100*r['broad_winner_rate']:.1f}%/{100*r['broad_dead_rate']:.1f}%**; agree branch/broad/DV **{r['same_direction_branch']}/{r['same_direction_broad']}/{r['direction_agrees_available_DV']}**")
    md += ['', '## Primary 1W/2L detail']
    for _,r in primary.iterrows():
        md.append(f"- `{r.date}` {r.period}: parent {r.parent_pnl:+.3f}; upper {r.rel_last_upper:.4f}; lower {r.rel_last_lower:.4f}; body {r.rel_last_body:.4f}; upper-vs-prev3max {r.rel_upper_delta_prev3max:+.4f}; body-vs-prev3med {r.rel_body_delta_prev3median:+.4f}; localmax4 {bool(r.rel_upper_localmax4)}; contract3 {bool(r.rel_body_contract3median)}; composite {bool(r.rel_rejection_expansion_composite)}")
    md += ['', '## Guardrail','Primary is only 1 winner vs 2 losers and was selected from the same sample. A clean separator matters only if its direction also persists in branch-matched, broad, and available D/V controls. No numeric threshold, timing, or economic action is promoted from this run.']
    (OUT/'F6.37_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
