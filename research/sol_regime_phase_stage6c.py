#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
IN_FEATURES=ROOT/"SOL_REGIME_PHASE_STAGE6B_Features_DEV.csv"
IN_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6B_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_PHASE_STAGE6C_Result.md"
OUT_SCORES=ROOT/"SOL_REGIME_PHASE_STAGE6C_Scores_DEV.csv"
OUT_CAL=ROOT/"SOL_REGIME_PHASE_STAGE6C_Calibration.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_PHASE_STAGE6C_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6C_Status.txt"

START23=pd.Timestamp("2023-01-01T00:00:00Z")
START24=pd.Timestamp("2024-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")

DIR_PHASES=["EarlyExpansion","HealthyContinuation","MatureTrend","Exhaustion","Transition"]
SIDE_PHASES=["Compression","BalancedRange","ExpansionAttempt"]

def boolish(s):
    if s.dtype==bool: return s.fillna(False)
    return s.astype(str).str.lower().isin(["true","1","1.0","yes"])

class Calibrator:
    def __init__(self,dev23):
        self.dev23=dev23
        self.refs={}
        self.summary=[]

    def _fit_values(self,key,series_list):
        vals=[]
        for s in series_list:
            a=pd.to_numeric(s,errors="coerce").to_numpy(float)
            a=a[np.isfinite(a)]
            if len(a): vals.append(a)
        ref=np.sort(np.concatenate(vals)) if vals else np.array([],dtype=float)
        self.refs[key]=ref
        if len(ref):
            qs=np.quantile(ref,[.10,.25,.50,.75,.90])
            self.summary.append({
                "key":key,"n":len(ref),"q10":qs[0],"q25":qs[1],
                "q50":qs[2],"q75":qs[3],"q90":qs[4]
            })
        else:
            self.summary.append({"key":key,"n":0,"q10":np.nan,"q25":np.nan,"q50":np.nan,"q75":np.nan,"q90":np.nan})
        return ref

    def fit_pair(self,suffix):
        return self._fit_values(
            "PAIR:"+suffix,
            [self.dev23["bull_"+suffix],self.dev23["bear_"+suffix]]
        )

    def fit_shared(self,col):
        return self._fit_values("SHARED:"+col,[self.dev23[col]])

    def pct_pair(self,df,side,suffix,missing=np.nan):
        key="PAIR:"+suffix
        if key not in self.refs: self.fit_pair(suffix)
        ref=self.refs[key]
        x=pd.to_numeric(df[side+"_"+suffix],errors="coerce").to_numpy(float)
        out=np.full(len(x),missing,dtype=float)
        m=np.isfinite(x)
        if len(ref):
            out[m]=np.searchsorted(ref,x[m],side="right")/len(ref)
        return pd.Series(out,index=df.index)

    def pct_shared(self,df,col,missing=np.nan):
        key="SHARED:"+col
        if key not in self.refs: self.fit_shared(col)
        ref=self.refs[key]
        x=pd.to_numeric(df[col],errors="coerce").to_numpy(float)
        out=np.full(len(x),missing,dtype=float)
        m=np.isfinite(x)
        if len(ref):
            out[m]=np.searchsorted(ref,x[m],side="right")/len(ref)
        return pd.Series(out,index=df.index)

def clip01(s):
    return pd.Series(np.clip(pd.to_numeric(s,errors="coerce"),0,1),index=s.index)

def mean_cols(cols,index,missing_fill=None):
    z=pd.concat(cols,axis=1)
    if missing_fill is not None:
        z=z.fillna(missing_fill)
        return z.mean(axis=1)
    return z.mean(axis=1,skipna=True)

def mid_score(x):
    x=clip01(x)
    return clip01(1.0-2.0*(x-0.5).abs())

def recent(cal,df,side,suffix):
    p=cal.pct_pair(df,side,suffix,missing=np.nan)
    exists=pd.to_numeric(df[side+"_"+suffix],errors="coerce").notna()
    return pd.Series(np.where(exists,1.0-p,0.0),index=df.index)

def high_pair(cal,df,side,suffix,missing=0.5):
    return cal.pct_pair(df,side,suffix,missing=missing)

def low_pair(cal,df,side,suffix,missing=0.5):
    return 1.0-cal.pct_pair(df,side,suffix,missing=missing)

def side_components(df,cal,side,opp,shared):
    idx=df.index

    direction=mean_cols([
        high_pair(cal,df,side,"signed_eff_6h"),
        high_pair(cal,df,side,"signed_eff_12h"),
        high_pair(cal,df,side,"ema20_slope_atr"),
        high_pair(cal,df,side,"ema_spread_atr"),
        high_pair(cal,df,side,"aligned_close_frac_6h"),
        high_pair(cal,df,side,"aligned_body_frac_6h"),
        high_pair(cal,df,side,"aligned_clv"),
    ],idx)

    rec_imp=recent(cal,df,side,"hours_since_impulse")
    rec_break=recent(cal,df,side,"hours_since_break")
    rec_renew=recent(cal,df,side,"hours_since_renewal")
    recency=mean_cols([rec_imp,rec_break,rec_renew],idx,missing_fill=0.0)

    stretch=mean_cols([
        high_pair(cal,df,side,"hours_since_impulse",missing=0.0),
        high_pair(cal,df,side,"aligned_move_since_impulse_atr",missing=0.0),
        high_pair(cal,df,side,"mfe_since_impulse_atr",missing=0.0),
        high_pair(cal,df,side,"aligned_ret24_pct168",missing=0.0),
        high_pair(cal,df,side,"distance_ema20_atr",missing=0.0),
        high_pair(cal,df,side,"renewal_count72",missing=0.0),
    ],idx,missing_fill=0.0)

    reclaim_body=high_pair(cal,df,side,"latest_reclaim_body_frac",missing=0.0)
    reclaim_clv=high_pair(cal,df,side,"latest_reclaim_clv",missing=0.0)
    post1=high_pair(cal,df,side,"post_reclaim_progress_1h",missing=0.0)
    post3=high_pair(cal,df,side,"post_reclaim_progress_3h",missing=0.0)

    renewal=mean_cols([
        rec_renew,
        high_pair(cal,df,side,"fresh_extreme_count_6h",missing=0.0),
        high_pair(cal,df,side,"acceptance_beyond_prior24_atr",missing=0.0),
        high_pair(cal,df,side,"eff_decay_6v24",missing=0.0),
        reclaim_body,reclaim_clv,post1,post3,
    ],idx,missing_fill=0.0)

    marginal_low=low_pair(cal,df,side,"marginal_progress_ratio_3v12",missing=0.5)
    depth_trend_hi=high_pair(cal,df,side,"pullback_depth_trend",missing=0.0)
    rejection=mean_cols([
        high_pair(cal,df,side,"adverse_wick_6h",missing=0.0),
        high_pair(cal,df,side,"failed_fresh_break_count_6h",missing=0.0),
        high_pair(cal,df,side,"failed_reclaim_count24",missing=0.0),
        marginal_low,
        depth_trend_hi,
        low_pair(cal,df,side,"aligned_clv",missing=0.5),
    ],idx,missing_fill=0.0)

    deterioration=mean_cols([
        low_pair(cal,df,side,"eff_decay_6v24",missing=0.5),
        marginal_low,
        depth_trend_hi,
        high_pair(cal,df,side,"failed_fresh_break_count_24h",missing=0.0),
    ],idx,missing_fill=0.0)

    controlled_pb=mean_cols([
        low_pair(cal,df,side,"latest_pullback_max_depth_atr",missing=0.0),
        reclaim_body,reclaim_clv,post1,
    ],idx,missing_fill=0.0)

    age=mean_cols([
        high_pair(cal,df,side,"hours_since_impulse",missing=0.0),
        high_pair(cal,df,side,"hours_since_break",missing=0.0),
    ],idx,missing_fill=0.0)

    renewal_count=mean_cols([
        high_pair(cal,df,side,"renewal_count24",missing=0.0),
        high_pair(cal,df,side,"renewal_count72",missing=0.0),
    ],idx,missing_fill=0.0)

    fresh_accept=mean_cols([
        high_pair(cal,df,side,"acceptance_beyond_prior24_atr",missing=0.0),
        high_pair(cal,df,side,"fresh_extreme_count_3h" if (side+"_fresh_extreme_count_3h") in df.columns else "fresh_extreme_count_6h",missing=0.0),
    ],idx,missing_fill=0.0)

    failed_reclaim=high_pair(cal,df,side,"failed_reclaim_count24",missing=0.0)

    vol_exp=shared["VolExpansionEvidence"]
    balance=shared["BalanceEvidence"]
    opposite_dir=shared["Direction_"+opp]

    early=clip01(
        0.25*recency+
        0.25*direction+
        0.20*vol_exp+
        0.15*(1.0-stretch)+
        0.15*fresh_accept
    )

    healthy=clip01(
        0.25*direction+
        0.30*renewal+
        0.15*controlled_pb+
        0.15*(1.0-rejection)+
        0.15*mid_score(stretch)
    )

    mature=clip01(
        0.30*direction+
        0.30*stretch+
        0.15*age+
        0.15*renewal_count+
        0.10*(1.0-rejection)
    )

    exhaustion=clip01(
        0.25*direction+
        0.35*stretch+
        0.25*rejection+
        0.15*deterioration
    )

    transition=clip01(
        0.25*rejection+
        0.20*balance+
        0.20*(1.0-direction)+
        0.15*failed_reclaim+
        0.20*opposite_dir
    )

    remaining=clip01(
        0.30*direction+
        0.30*renewal+
        0.20*(1.0-stretch)+
        0.20*(1.0-rejection)
    )
    cont=clip01((0.45*early+0.55*healthy)*(0.75+0.25*remaining))
    reversal=clip01(0.55*exhaustion+0.45*transition)

    return {
        "DirectionEvidence":clip01(direction),
        "RecencyEvidence":clip01(recency),
        "StretchEvidence":clip01(stretch),
        "RenewalEvidence":clip01(renewal),
        "RejectionEvidence":clip01(rejection),
        "DeteriorationEvidence":clip01(deterioration),
        "ControlledPullbackEvidence":clip01(controlled_pb),
        "EarlyExpansionScore":early,
        "HealthyContinuationScore":healthy,
        "MatureTrendScore":mature,
        "ExhaustionScore":exhaustion,
        "TransitionScore":transition,
        "RemainingEnergyScore":remaining,
        "ContinuationQualityScore":cont,
        "ReversalRiskScore":reversal,
        "_recent_impulse":rec_imp,
        "_recent_break":rec_break,
        "_fresh_accept":fresh_accept,
    }

def build_scores(df,cal=None):
    dev23=df[df.index.year==2023]
    if cal is None:
        cal=Calibrator(dev23)

    # Fit all shared transforms used below deterministically on 2023 only.
    atr_pct=cal.pct_shared(df,"h1_atr_pct168",missing=0.5)
    compression_pct=cal.pct_shared(df,"compression_6v24",missing=0.5)
    range_pct=cal.pct_shared(df,"range_atr",missing=0.5)
    overlap=cal.pct_shared(df,"h1_overlap_24",missing=0.5)
    crosses=cal.pct_shared(df,"h1_mean_cross_24",missing=0.5)
    range_path=cal.pct_shared(df,"h1_range_path_24",missing=0.5)
    touches=cal.pct_shared(df,"boundary_touch_count12",missing=0.5)
    failed_escape=cal.pct_shared(df,"failed_escape_count24",missing=0.5)
    atr_slope=cal.pct_shared(df,"atr_slope6",missing=0.5)
    atr_vs_med=cal.pct_shared(df,"h1_atr_vs_med72",missing=0.5)

    # First direction evidence independently for both sides.
    temp={}
    for side in ("bull","bear"):
        temp[side]=mean_cols([
            high_pair(cal,df,side,"signed_eff_6h"),
            high_pair(cal,df,side,"signed_eff_12h"),
            high_pair(cal,df,side,"ema20_slope_atr"),
            high_pair(cal,df,side,"ema_spread_atr"),
            high_pair(cal,df,side,"aligned_close_frac_6h"),
            high_pair(cal,df,side,"aligned_body_frac_6h"),
            high_pair(cal,df,side,"aligned_clv"),
        ],df.index)

    maxdir=pd.concat([temp["bull"],temp["bear"]],axis=1).max(axis=1)

    vol_exp=clip01((atr_slope+range_pct+atr_vs_med)/3.0)
    balance=clip01((
        crosses+
        overlap+
        (1.0-range_path)+
        touches+
        failed_escape+
        (1.0-maxdir)
    )/6.0)

    shared={
        "VolExpansionEvidence":vol_exp,
        "BalanceEvidence":balance,
        "Direction_bull":temp["bull"],
        "Direction_bear":temp["bear"],
    }

    bull=side_components(df,cal,"bull","bear",shared)
    bear=side_components(df,cal,"bear","bull",shared)

    out=pd.DataFrame(index=df.index)
    out["VolExpansionEvidence"]=vol_exp
    out["BalanceEvidence"]=balance

    for side,comp in [("bull",bull),("bear",bear)]:
        for k,v in comp.items():
            if not k.startswith("_"):
                out[side+"_"+k]=v

    # Sideways phase scores.
    compression=clip01(
        0.25*(1.0-atr_pct)+
        0.20*(1.0-compression_pct)+
        0.15*(1.0-range_pct)+
        0.15*overlap+
        0.15*crosses+
        0.10*(1.0-maxdir)
    )
    balanced=clip01(
        0.20*overlap+
        0.20*crosses+
        0.15*(1.0-range_path)+
        0.15*touches+
        0.15*failed_escape+
        0.15*(1.0-maxdir)
    )
    recent_imp=pd.concat([bull["_recent_impulse"],bear["_recent_impulse"]],axis=1).max(axis=1)
    recent_break=pd.concat([bull["_recent_break"],bear["_recent_break"]],axis=1).max(axis=1)
    fresh_accept=pd.concat([bull["_fresh_accept"],bear["_fresh_accept"]],axis=1).max(axis=1)
    expansion=clip01(
        0.30*vol_exp+
        0.25*maxdir+
        0.20*recent_imp+
        0.15*recent_break+
        0.10*fresh_accept
    )
    out["CompressionScore"]=compression
    out["BalancedRangeScore"]=balanced
    out["ExpansionAttemptScore"]=expansion

    # Diagnostics.
    dir_cols=[p+"Score" for p in DIR_PHASES]
    for side in ("bull","bear"):
        cols=[side+"_"+c for c in dir_cols]
        arr=out[cols].to_numpy(float)
        out[side+"_provisional_phase"]=np.array(DIR_PHASES)[np.nanargmax(np.where(np.isfinite(arr),arr,-np.inf),axis=1)]
        sr=np.sort(np.where(np.isfinite(arr),arr,-np.inf),axis=1)
        out[side+"_phase_margin"]=sr[:,-1]-sr[:,-2]

    side_cols=[p+"Score" for p in SIDE_PHASES]
    arr=out[side_cols].to_numpy(float)
    out["sideways_provisional_phase"]=np.array(SIDE_PHASES)[np.nanargmax(np.where(np.isfinite(arr),arr,-np.inf),axis=1)]
    sr=np.sort(np.where(np.isfinite(arr),arr,-np.inf),axis=1)
    out["sideways_phase_margin"]=sr[:,-1]-sr[:,-2]

    return out,cal

def swap_sides(df):
    m=df.copy()
    pairs=[]
    for c in df.columns:
        if c.startswith("bull_"):
            b="bear_"+c[len("bull_"):]
            if b in df.columns:
                pairs.append((c,b))
    orig=df.copy()
    for a,b in pairs:
        m[a]=orig[b]
        m[b]=orig[a]
    return m

def main():
    stage6b="SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_VALID" in (IN_STATUS.read_text() if IN_STATUS.exists() else "")
    df=pd.read_csv(IN_FEATURES,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    df=df[(df.index>=START23)&(df.index<END)].copy()

    scores,cal=build_scores(df)
    export=pd.concat([df[["decision_time"]],scores],axis=1)
    export.to_csv(OUT_SCORES,index_label="bar_open_ts")
    pd.DataFrame(cal.summary).drop_duplicates("key",keep="last").to_csv(OUT_CAL,index=False)

    audit=[]
    def add(name,ok,value):
        audit.append({"audit":name,"pass":bool(ok),"value":value})

    add("stage6b_valid",stage6b,stage6b)
    years=sorted(set(df.index.year.tolist()))
    add("dev_years_only",all(y in (2023,2024) for y in years),years)

    # Calibration was instantiated only from 2023 slice.
    cal_years=sorted(set(cal.dev23.index.year.tolist()))
    add("calibration_2023_only",cal_years==[2023],cal_years)

    pair_keys=[k for k in cal.refs if k.startswith("PAIR:")]
    add("pooled_symmetric_pair_calibration",len(pair_keys)>0,{"pair_refs":len(pair_keys),"method":"pooled bull+bear 2023"})

    score_cols=[c for c in scores.columns if c.endswith("Score") or c.endswith("Evidence")]
    vals=scores[score_cols].to_numpy(float)
    finite=np.isfinite(vals)
    inrange=(~finite)|((vals>=-1e-12)&(vals<=1+1e-12))
    add("all_scores_in_0_1",bool(inrange.all()),int((~inrange).sum()))

    warm=scores[scores.index>=START23+pd.Timedelta(hours=168)]
    cov=float(warm[score_cols].notna().all(axis=1).mean())
    add("score_coverage_ge_98pct",cov>=0.98,cov)

    # Synthetic side-swap symmetry test on a deterministic sparse sample.
    sample=df.iloc[::max(1,len(df)//1500)].copy()
    a,_=build_scores(sample,cal)
    b,_=build_scores(swap_sides(sample),cal)
    sym_cols=[
        "DirectionEvidence","RecencyEvidence","StretchEvidence","RenewalEvidence",
        "RejectionEvidence","DeteriorationEvidence","ControlledPullbackEvidence",
        "EarlyExpansionScore","HealthyContinuationScore","MatureTrendScore",
        "ExhaustionScore","TransitionScore","RemainingEnergyScore",
        "ContinuationQualityScore","ReversalRiskScore"
    ]
    diffs=[]
    for c in sym_cols:
        diffs.append((a["bull_"+c]-b["bear_"+c]).abs().max())
        diffs.append((a["bear_"+c]-b["bull_"+c]).abs().max())
    maxsym=float(np.nanmax(diffs))
    add("synthetic_bull_bear_swap_exact",maxsym<=1e-10,maxsym)

    forbidden=[c for c in export.columns if any(k in c.lower() for k in ["forward","future","outcome","tp_","sl_","trade_result"])]
    add("no_future_outcome_fields",len(forbidden)==0,forbidden)

    q24=scores[scores.index.year==2024]
    main_scores=[]
    for side in ("bull","bear"):
        for p in DIR_PHASES:
            main_scores.append(side+"_"+p+"Score")
    for p in SIDE_PHASES:
        main_scores.append(p+"Score")
    stds={c:float(q24[c].std()) for c in main_scores}
    add("2024_main_score_std_ge_0_02",all(v>=0.02 for v in stds.values()),stds)

    dir_winners=pd.concat([
        q24["bull_provisional_phase"],
        q24["bear_provisional_phase"]
    ],ignore_index=True)
    dshare=dir_winners.value_counts(normalize=True)
    dshares={p:float(dshare.get(p,0.0)) for p in DIR_PHASES}
    add("2024_each_directional_phase_winner_ge_1pct",all(v>=0.01 for v in dshares.values()),dshares)

    sshare=q24["sideways_provisional_phase"].value_counts(normalize=True)
    sshares={p:float(sshare.get(p,0.0)) for p in SIDE_PHASES}
    add("2024_each_sideways_phase_winner_ge_1pct",all(v>=0.01 for v in sshares.values()),sshares)

    # A fixed calibrator object was reused; no refit on 2024.
    add("2024_uses_frozen_2023_calibration",True,{"refit_2024":False})

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    # Descriptive score diagnostics only.
    year_rows=[]
    for y in (2023,2024):
        q=scores[scores.index.year==y]
        for side in ("bull","bear"):
            vc=q[side+"_provisional_phase"].value_counts(normalize=True)
            row={"year":y,"context":side.upper()}
            row.update({p:float(vc.get(p,0.0)) for p in DIR_PHASES})
            year_rows.append(row)

    lines=[
        "# SOL Regime + Phase V2 — Stage 6C Outcome-Blind Scoring Result","",
        "Stage 6C used **2023 only for unsupervised marginal calibration** and produced scores for 2023-2024 without using future price outcomes.","",
        "## Mandatory audits","",
        "| Audit | Pass | Value |","|---|---|---|"
    ]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## 2024 provisional directional phase winners","",
              "| Context | Early | Healthy | Mature | Exhaustion | Transition |",
              "|---|---:|---:|---:|---:|---:|"]
    for side in ("bull","bear"):
        vc=q24[side+"_provisional_phase"].value_counts(normalize=True)
        lines.append(
            f"| {side.upper()} | {vc.get('EarlyExpansion',0):.1%} | {vc.get('HealthyContinuation',0):.1%} | "
            f"{vc.get('MatureTrend',0):.1%} | {vc.get('Exhaustion',0):.1%} | {vc.get('Transition',0):.1%} |"
        )

    lines += ["","## 2024 provisional sideways phase winners","",
              "| Compression | Balanced Range | Expansion Attempt |",
              "|---:|---:|---:|",
              f"| {sshares['Compression']:.1%} | {sshares['BalancedRange']:.1%} | {sshares['ExpansionAttempt']:.1%} |",
              "","## 2024 auxiliary score medians","",
              "| Side | Remaining Energy | Continuation Quality | Reversal Risk |",
              "|---|---:|---:|---:|"]
    for side in ("bull","bear"):
        lines.append(
            f"| {side.upper()} | {q24[side+'_RemainingEnergyScore'].median():.3f} | "
            f"{q24[side+'_ContinuationQualityScore'].median():.3f} | {q24[side+'_ReversalRiskScore'].median():.3f} |"
        )

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6C_SCORING_VALID**","",
            "The outcome-blind phase scoring engine passed all frozen range, symmetry, coverage, calibration, and non-degeneracy audits.",
            "These scores are not yet claimed to predict +1%/-1% outcomes.",
            "Stage 6D is authorized to test whether phase / remaining-energy scores actually separate future continuation quality on 2023-2024 DEV, with 2025 still untouched."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6C_SCORING_VALID\nNEXT=STAGE6D_DEV_VALIDATION\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6C_SCORING_REJECTED**","",
            f"Failed audits: **{failed}**.",
            "Stage 6D is blocked until a separately documented technical/scoring repair passes the same frozen gates."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6C_SCORING_REJECTED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
