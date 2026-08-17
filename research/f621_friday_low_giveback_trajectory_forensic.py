#!/usr/bin/env python3
"""F6.21 — Friday low-giveback trajectory persistence forensic.

FORENSIC ONLY. No exit rule tuning or promotion. Live BBC untouched.
Frozen stack remains FIB5 -> EARLY10 -> F6.5 plus F6.18 D3.

Purpose
-------
F6.20 showed that fixed +35m/+65m snapshots identify a real failure-to-
accelerate phenotype but also cut healthy eventual winners. This study asks
what distinguishes PERSISTENT failure from TEMPORARY structural pullback.

Primary loss cohort is frozen from F6.14/F6.19:
- parent loss
- no original three-layer FIB5/EARLY10/F6.5 action
- MFE >= +0.5R and < +1R
Expected N=12.

Primary controls are eventual parent winners that would have been false
positives for at least one F6.20 candidate after chronological competition
with the frozen four-layer stack. Secondary controls are all eligible eventual
winners that reached +0.5R and had no original three-layer action.

All trajectory features use completed 5m bars only and fixed windows ending
35m and 65m after the FIRST causal +0.5R hit. No management PnL is optimized.
"""
from __future__ import annotations
import json, os, math
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f620_friday_failure_to_accelerate_management as f620

OUT=Path(os.getenv('F621_OUT','f621_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL


def auc(y,x):
    y=np.asarray(y,dtype=int); x=np.asarray(x,dtype=float)
    ok=np.isfinite(x); y=y[ok]; x=x[ok]
    p=x[y==1]; n=x[y==0]
    if len(p)==0 or len(n)==0:return np.nan
    s=0.0
    for a in p:
        s += float(np.sum(a>n)) + 0.5*float(np.sum(a==n))
    return s/(len(p)*len(n))


def longest_true(a):
    best=cur=0
    for v in a:
        if bool(v): cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)


def cross_up(a):
    a=np.asarray(a,dtype=bool)
    if len(a)<2:return 0
    return int(np.sum((~a[:-1]) & a[1:]))


def transition_count(a):
    a=np.asarray(a,dtype=bool)
    if len(a)<2:return 0
    return int(np.sum(a[1:]!=a[:-1]))


def slope(v):
    v=np.asarray(v,dtype=float)
    ok=np.isfinite(v)
    if ok.sum()<2:return np.nan
    x=np.arange(len(v),dtype=float)[ok]; y=v[ok]
    return float(np.polyfit(x,y,1)[0])


def trajectory(k,tr,ht,mins):
    dt=ht+pd.Timedelta(minutes=mins)
    if dt not in k.index or tr.exit_t<=dt:return None
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    if len(w)!=mins//5:return None
    close=w.close.astype(float).to_numpy(); low=w.low.astype(float).to_numpy()
    ema7=w.ema7.astype(float).to_numpy(); ema20=w.ema20.astype(float).to_numpy()
    tak=w.taker_imb.astype(float).to_numpy()
    progress=(close/tr.entry-1.0)/R
    above7=close>=ema7; above20=close>=ema20; abovehalf=progress>=0.5
    below7=~above7; below20=~above20

    # milestone-loss/rebuild sequence: after first observed completed close below
    # +0.5R, did a later completed close rebuild >=+0.5R?
    lost_idx=np.where(~abovehalf)[0]
    if len(lost_idx):
        first_lost=int(lost_idx[0]); rebuild_after_loss=bool(np.any(abovehalf[first_lost+1:]))
        rebuild_count=cross_up(abovehalf[first_lost:])
    else:
        first_lost=-1; rebuild_after_loss=False; rebuild_count=0

    # EMA7 recovery after first loss of acceptance.
    b7idx=np.where(below7)[0]
    if len(b7idx):
        first_b7=int(b7idx[0]); ema7_reclaim_after_loss=bool(np.any(above7[first_b7+1:]))
        ema7_reclaims_after_loss=cross_up(above7[first_b7:])
    else:
        first_b7=-1; ema7_reclaim_after_loss=False; ema7_reclaims_after_loss=0

    # EMA20 recovery after first loss.
    b20idx=np.where(below20)[0]
    if len(b20idx):
        first_b20=int(b20idx[0]); ema20_reclaim_after_loss=bool(np.any(above20[first_b20+1:]))
        ema20_reclaims_after_loss=cross_up(above20[first_b20:])
    else:
        first_b20=-1; ema20_reclaim_after_loss=False; ema20_reclaims_after_loss=0

    # Flow recovery: after first negative taker bar, any later positive bar and
    # whether the last two completed bars average positive.
    negidx=np.where(tak<0)[0]
    if len(negidx):
        first_neg=int(negidx[0]); flow_positive_after_negative=bool(np.any(tak[first_neg+1:]>0))
    else:
        first_neg=-1; flow_positive_after_negative=False

    # Higher-low persistence is threshold-free: count pairwise rising lows and
    # require the final 3 completed lows strictly rise for local repair.
    hl_trans=int(np.sum(low[1:]>low[:-1])) if len(low)>1 else 0
    final3_higher_low=bool(len(low)>=3 and low[-2]>low[-3] and low[-1]>low[-2])

    # Bars since last acceptance above EMA7 / +0.5R. If never above, full len.
    def since_last(mask):
        ix=np.where(mask)[0]
        return int(len(mask)-1-ix[-1]) if len(ix) else int(len(mask))

    return {
        'decision_t':str(dt), 'n_bars':int(len(w)),
        'end_progress_r':float(progress[-1]),
        'progress_slope_r_per_bar':slope(progress),
        'progress_last3_slope':slope(progress[-3:]) if len(progress)>=3 else np.nan,
        'progress_min_r':float(np.min(progress)),
        'progress_max_r':float(np.max(progress)),
        'progress_range_r':float(np.max(progress)-np.min(progress)),
        'frac_below_ema7':float(np.mean(below7)),
        'frac_below_ema20':float(np.mean(below20)),
        'longest_below_ema7':longest_true(below7),
        'longest_below_ema20':longest_true(below20),
        'ema7_reclaims':cross_up(above7),
        'ema20_reclaims':cross_up(above20),
        'ema7_transitions':transition_count(above7),
        'ema20_transitions':transition_count(above20),
        'ema7_reclaim_after_loss':float(ema7_reclaim_after_loss),
        'ema20_reclaim_after_loss':float(ema20_reclaim_after_loss),
        'ema7_reclaims_after_loss':float(ema7_reclaims_after_loss),
        'ema20_reclaims_after_loss':float(ema20_reclaims_after_loss),
        'bars_since_above_ema7':float(since_last(above7)),
        'bars_since_above_ema20':float(since_last(above20)),
        'frac_below_halfR':float(np.mean(~abovehalf)),
        'longest_below_halfR':longest_true(~abovehalf),
        'halfR_rebuild_after_loss':float(rebuild_after_loss),
        'halfR_rebuild_count':float(rebuild_count),
        'bars_since_halfR':float(since_last(abovehalf)),
        'taker_median':float(np.median(tak)),
        'taker_mean':float(np.mean(tak)),
        'taker_last':float(tak[-1]),
        'taker_last2_mean':float(np.mean(tak[-2:])),
        'taker_slope':slope(tak),
        'frac_taker_positive':float(np.mean(tak>0)),
        'flow_positive_after_negative':float(flow_positive_after_negative),
        'higher_low_fraction':float(hl_trans/max(len(low)-1,1)),
        'final3_higher_low':float(final3_higher_low),
    }


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        original_ev=list(f616.existing_events(k,t,tr)); original_ev.sort(key=lambda x:x[0])
        original_untouched=(len(original_ev)==0)
        ht=f616.first_hit(k,tr,0.5*R)
        st=f620.accel_state(k,tr)
        # Was this eventual winner actually acted by any F6.20 candidate after
        # chronological competition with frozen four-layer stack?
        false_positive_rules=[]
        if st is not None:
            for rule in f620.RULES:
                pnl,layer,_=f620.apply(k,t,tr,st,rule)
                if layer==rule and tr.pnl>0:false_positive_rules.append(rule)
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'mfe_r':float(tr.mfe/R),
             'original_untouched':bool(original_untouched),
             'false_positive_any':bool(false_positive_rules),
             'false_positive_rules':'|'.join(false_positive_rules)}
        if ht is not None:
            row['halfR_hit_t']=str(ht)
            for mins in (35,65):
                z=trajectory(k,tr,ht,mins)
                if z:
                    for kk,v in z.items():row[f't{mins}_{kk}']=v
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f621_rows.csv',index=False)

    loss=df[(df.parent_pnl<=0)&(df.original_untouched)&(df.mfe_r>=0.5)&(df.mfe_r<1.0)].copy()
    if len(loss)!=12: raise AssertionError(f'low cohort parity expected 12 got {len(loss)}')
    fp=df[(df.parent_win)&(df.false_positive_any)].copy()
    broad=df[(df.parent_win)&(df.original_untouched)&(df.mfe_r>=0.5)].copy()

    feature_names=[
      'end_progress_r','progress_slope_r_per_bar','progress_last3_slope','progress_min_r','progress_max_r','progress_range_r',
      'frac_below_ema7','frac_below_ema20','longest_below_ema7','longest_below_ema20','ema7_reclaims','ema20_reclaims',
      'ema7_transitions','ema20_transitions','ema7_reclaim_after_loss','ema20_reclaim_after_loss','ema7_reclaims_after_loss','ema20_reclaims_after_loss',
      'bars_since_above_ema7','bars_since_above_ema20','frac_below_halfR','longest_below_halfR','halfR_rebuild_after_loss','halfR_rebuild_count','bars_since_halfR',
      'taker_median','taker_mean','taker_last','taker_last2_mean','taker_slope','frac_taker_positive','flow_positive_after_negative',
      'higher_low_fraction','final3_higher_low']

    rec=[]
    for mins in (35,65):
      for control_name,ctrl in [('false_positive',fp),('broad_winner',broad)]:
        for f in feature_names:
          c=f't{mins}_{f}'
          if c not in df.columns:continue
          a=loss[['period',c]].dropna(); b=ctrl[['period',c]].dropna()
          z=pd.concat([a.assign(y=1),b.assign(y=0)],ignore_index=True)
          zd=z[z.period=='discovery']; zv=z[z.period=='validation']
          A=auc(z.y,z[c]); AD=auc(zd.y,zd[c]); AV=auc(zv.y,zv[c])
          rec.append({'horizon':mins,'control':control_name,'feature':f,
                      'n_loss':int(len(a)),'n_ctrl':int(len(b)),
                      'auc_loss_high':A,'auc_D':AD,'auc_V':AV,
                      'strength':max(A,1-A) if np.isfinite(A) else np.nan,
                      'direction':'higher_loss' if np.isfinite(A) and A>=0.5 else 'lower_loss',
                      'median_loss':float(a[c].median()) if len(a) else np.nan,
                      'median_ctrl':float(b[c].median()) if len(b) else np.nan})
    atlas=pd.DataFrame(rec).sort_values(['control','strength'],ascending=[True,False])
    atlas.to_csv(OUT/'f621_trajectory_atlas.csv',index=False)

    # Stable shortlist: primary false-positive controls, full separation >=.65,
    # D and V both defined and pointing the same direction at >=.60.
    p=atlas[atlas.control=='false_positive'].copy()
    def stable(r):
      vals=[r.auc_loss_high,r.auc_D,r.auc_V]
      if any(pd.isna(v) for v in vals):return False
      dirs=[v>=0.5 for v in vals]
      strengths=[max(v,1-v) for v in vals]
      return bool(len(set(dirs))==1 and strengths[0]>=.65 and strengths[1]>=.60 and strengths[2]>=.60)
    p['stable']=p.apply(stable,axis=1)
    stable_rows=p[p.stable].sort_values('strength',ascending=False)

    # Human-readable summary of false-positive cohort composition.
    out={
      'cohorts':{
        'low_givebacks':int(len(loss)),
        'false_positive_winners_union':int(len(fp)),
        'false_positive_D':int((fp.period=='discovery').sum()),
        'false_positive_V':int((fp.period=='validation').sum()),
        'broad_winner_controls':int(len(broad)),
      },
      'false_positive_rule_membership':{},
      'stable_primary_separators':stable_rows.head(15).to_dict('records'),
      'top_primary_separators':p.sort_values('strength',ascending=False).head(20).to_dict('records'),
    }
    for rule in f620.RULES:
      out['false_positive_rule_membership'][rule]=int(fp.false_positive_rules.str.contains(rule,regex=False).sum())
    (OUT/'f621_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.21 — Low-Giveback Trajectory Persistence Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**',
        '**Live BBC untouched; frozen FIB5/EARLY10/F6.5/D3 unchanged.**','',
        '## Cohorts',
        f"- low givebacks: **{len(loss)}**",
        f"- F6.20 false-positive eventual winners (union): **{len(fp)}** (D {(fp.period=='discovery').sum()} / V {(fp.period=='validation').sum()})",
        f"- broad eligible winner controls: **{len(broad)}**",'',
        '## Stable primary separators (loss vs F6.20 false-positive winner)']
    if len(stable_rows)==0:
      md.append('- none satisfy same-direction full/D/V stability screen')
    else:
      for _,r in stable_rows.head(15).iterrows():
        md.append(f"- {int(r.horizon)}m {r.feature}: AUC {r.auc_loss_high:.3f}, D {r.auc_D:.3f}, V {r.auc_V:.3f}; {r.direction}; median loss {r.median_loss:.4f} vs ctrl {r.median_ctrl:.4f}")
    md += ['', '## Interpretation guardrail',
           'This stage describes persistence/recovery trajectories only. It does not choose a cut threshold or management action. Any F6.22 rule must be predeclared from a small interpretable subset of stable trajectory features and then replayed chronologically against the frozen stack.',
           'Do not retune the 35/65m horizons on this sample.']
    (OUT/'F6.21_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
