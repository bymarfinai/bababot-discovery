#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
IN_FEATURES=ROOT/"SOL_REGIME_DETECTOR_STAGE2_Features.csv"
IN_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE2_Status.txt"
OUT_MD=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Result.md"
OUT_SCORES=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Scores_DEV.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Status.txt"

START=pd.Timestamp("2023-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")

def clip01(x):
    return np.clip(x,0.0,1.0)

def dir01(x,scale):
    return 0.5+0.5*np.tanh(x/scale)

def struct_maps(s):
    bull=s.map({"BULL_SEQ":1.0,"BEAR_SEQ":0.0,"MIXED":0.25,"INSUFFICIENT":0.25}).fillna(0.25)
    bear=s.map({"BULL_SEQ":0.0,"BEAR_SEQ":1.0,"MIXED":0.25,"INSUFFICIENT":0.25}).fillna(0.25)
    side=s.map({"BULL_SEQ":0.15,"BEAR_SEQ":0.15,"MIXED":1.0,"INSUFFICIENT":0.50}).fillna(0.50)
    return bull,bear,side

def calc_scores(df):
    z=df.copy()
    eps=1e-12
    atrn=z["h1_atr_norm"].astype(float).clip(lower=eps)

    b_struct,r_struct,s_struct=struct_maps(z["h1_structure_state"])
    b4_struct,r4_struct,s4_struct=struct_maps(z["h4_structure_state"])
    # 4H directional mixed evidence is slightly less permissive than 1H mapping.
    b4_struct=z["h4_structure_state"].map({"BULL_SEQ":1.0,"BEAR_SEQ":0.0,"MIXED":0.35,"INSUFFICIENT":0.25}).fillna(0.25)
    r4_struct=z["h4_structure_state"].map({"BULL_SEQ":0.0,"BEAR_SEQ":1.0,"MIXED":0.35,"INSUFFICIENT":0.25}).fillna(0.25)

    spread_atr=z["h1_ema_spread"].astype(float)/atrn
    ret12_atr=z["h1_ret_12"].astype(float)/atrn
    ret24_atr=z["h1_ret_24"].astype(float)/atrn
    dist20_atr=z["h1_close_ema20_dist"].astype(float)/atrn

    bull_drift=(
        dir01(z["h1_ema20_slope3_atr"].astype(float),0.60)+
        dir01(spread_atr,1.00)+
        dir01(ret12_atr,2.50)+
        dir01(ret24_atr,4.00)
    )/4.0
    bear_drift=(
        dir01(-z["h1_ema20_slope3_atr"].astype(float),0.60)+
        dir01(-spread_atr,1.00)+
        dir01(-ret12_atr,2.50)+
        dir01(-ret24_atr,4.00)
    )/4.0

    signed_eff=z["h1_eff_24"].astype(float)*(
        z["h1_upfrac_24"].astype(float)-z["h1_dnfrac_24"].astype(float)
    )
    bull_eff=dir01(signed_eff,0.25)
    bear_eff=dir01(-signed_eff,0.25)

    persistence=(
        1.0-clip01(z["h1_mean_cross_24"].astype(float)/8.0)+
        1.0-clip01(z["h1_overlap_24"].astype(float))
    )/2.0
    bull_accept=0.70*dir01(dist20_atr,0.80)+0.30*persistence
    bear_accept=0.70*dir01(-dist20_atr,0.80)+0.30*persistence

    bull4=(
        b4_struct+
        dir01(z["h4_ret_6"].astype(float),0.06)+
        dir01(z["h4_ema_spread"].astype(float),0.02)+
        dir01(z["h4_close_ema20_dist"].astype(float),0.03)
    )/4.0
    bear4=(
        r4_struct+
        dir01(-z["h4_ret_6"].astype(float),0.06)+
        dir01(-z["h4_ema_spread"].astype(float),0.02)+
        dir01(-z["h4_close_ema20_dist"].astype(float),0.03)
    )/4.0

    bull=(
        0.25*b_struct+
        0.25*bull_drift+
        0.18*bull_eff+
        0.14*bull_accept+
        0.18*bull4
    )
    bear=(
        0.25*r_struct+
        0.25*bear_drift+
        0.18*bear_eff+
        0.14*bear_accept+
        0.18*bear4
    )

    side_ineff=1.0-clip01(z["h1_eff_24"].astype(float))
    side_cross=clip01(z["h1_mean_cross_24"].astype(float)/6.0)
    side_overlap=clip01(z["h1_overlap_24"].astype(float))
    side_contain=1.0-clip01(z["h1_range_path_24"].astype(float)/0.80)
    side_muted=1.0-np.abs(np.tanh(ret24_atr/4.0))
    side4=(
        s4_struct+
        (1.0-np.abs(np.tanh(z["h4_ret_6"].astype(float)/0.06)))+
        (1.0-np.abs(np.tanh(z["h4_ema_spread"].astype(float)/0.02)))
    )/3.0

    side=(
        0.18*s_struct+
        0.20*side_ineff+
        0.18*side_cross+
        0.14*side_overlap+
        0.12*side_contain+
        0.10*side_muted+
        0.08*side4
    )

    out=pd.DataFrame(index=z.index)
    out["BullScore"]=clip01(bull)
    out["BearScore"]=clip01(bear)
    out["SidewaysScore"]=clip01(side)

    arr=out[["BullScore","BearScore","SidewaysScore"]].to_numpy(float)
    names=np.array(["BULL","BEAR","SIDEWAYS"])
    valid=np.isfinite(arr).all(axis=1)
    top_idx=np.argmax(np.where(np.isfinite(arr),arr,-np.inf),axis=1)
    sorted_arr=np.sort(np.where(np.isfinite(arr),arr,-np.inf),axis=1)
    top=sorted_arr[:,-1]
    second=sorted_arr[:,-2]
    margin=top-second
    out["provisional_regime"]=np.where(valid,names[top_idx],"UNAVAILABLE")
    out["top_score"]=np.where(valid,top,np.nan)
    out["score_margin"]=np.where(valid,margin,np.nan)
    out["confidence_raw"]=np.where(valid,clip01(0.5*top+0.5*margin),np.nan)

    # Keep components for forensic transparency.
    out["bull_structure"]=b_struct
    out["bear_structure"]=r_struct
    out["side_structure"]=s_struct
    out["bull_drift"]=bull_drift
    out["bear_drift"]=bear_drift
    out["bull_efficiency"]=bull_eff
    out["bear_efficiency"]=bear_eff
    out["bull_acceptance"]=bull_accept
    out["bear_acceptance"]=bear_accept
    out["bull_4h_context"]=bull4
    out["bear_4h_context"]=bear4
    out["side_low_efficiency"]=side_ineff
    out["side_crossing"]=side_cross
    out["side_overlap"]=side_overlap
    out["side_containment"]=side_contain
    out["side_muted_drift"]=side_muted
    out["side_4h_balance"]=side4
    return out

def mirror_df(df):
    m=df.copy()
    # Exact directional sign mirror.
    for c in [
        "h1_ema_spread","h1_ema20_slope3_atr","h1_ret_12","h1_ret_24",
        "h1_close_ema20_dist","h4_ret_6","h4_ema_spread","h4_close_ema20_dist"
    ]:
        m[c]=-m[c].astype(float)
    up=m["h1_upfrac_24"].copy()
    m["h1_upfrac_24"]=m["h1_dnfrac_24"]
    m["h1_dnfrac_24"]=up
    smap={"BULL_SEQ":"BEAR_SEQ","BEAR_SEQ":"BULL_SEQ","MIXED":"MIXED","INSUFFICIENT":"INSUFFICIENT"}
    m["h1_structure_state"]=m["h1_structure_state"].map(smap).fillna(m["h1_structure_state"])
    m["h4_structure_state"]=m["h4_structure_state"].map(smap).fillna(m["h4_structure_state"])
    return m

def run_lengths(regimes):
    if len(regimes)==0:
        return {}
    vals=[]
    cur=regimes.iloc[0]; n=1
    for x in regimes.iloc[1:]:
        if x==cur:
            n+=1
        else:
            vals.append((cur,n))
            cur=x; n=1
    vals.append((cur,n))
    out={}
    for r in ["BULL","BEAR","SIDEWAYS"]:
        a=[n for k,n in vals if k==r]
        out[r]={
            "runs":len(a),
            "median":float(np.median(a)) if a else np.nan,
            "p90":float(np.quantile(a,.9)) if a else np.nan,
        }
    return out

def main():
    status=IN_STATUS.read_text() if IN_STATUS.exists() else ""
    stage2_valid="SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_VALID" in status

    df=pd.read_csv(IN_FEATURES,parse_dates=["bar_open_ts"])
    df=df.set_index("bar_open_ts").sort_index()
    dev=df[(df.index>=START)&(df.index<END)].copy()
    scores=calc_scores(dev)

    export=pd.concat([
        dev[["decision_time","partition","h1_structure_state","h4_structure_state"]],
        scores
    ],axis=1)
    export.to_csv(OUT_SCORES,index_label="bar_open_ts")

    audit=[]
    def add(name,ok,value,detail=""):
        audit.append({"audit":name,"pass":bool(ok),"value":value,"detail":detail})

    add("stage2_valid",stage2_valid,stage2_valid)

    years=set(export.index.year.tolist())
    add("no_2025_2026_rows",all(y in (2023,2024) for y in years),sorted(years))

    score_cols=["BullScore","BearScore","SidewaysScore"]
    vals=export[score_cols].to_numpy(float)
    finite=np.isfinite(vals)
    inrange=(~finite)|((vals>=-1e-12)&(vals<=1+1e-12))
    add("all_scores_in_0_1",bool(inrange.all()),int((~inrange).sum()))

    coverage=float(export[score_cols].notna().all(axis=1).mean())
    add("score_coverage_ge_99_5",coverage>=0.995,coverage)

    sample=dev.iloc[::max(1,len(dev)//2000)].copy()
    a=calc_scores(sample)
    b=calc_scores(mirror_df(sample))
    db=(a["BullScore"]-b["BearScore"]).abs().max()
    dr=(a["BearScore"]-b["BullScore"]).abs().max()
    ds=(a["SidewaysScore"]-b["SidewaysScore"]).abs().max()
    add("directional_mirror_swaps_bull_bear",bool(max(db,dr)<=1e-10),float(max(db,dr)))
    add("sideways_mirror_invariant",bool(ds<=1e-10),float(ds))

    forbidden=[c for c in export.columns if any(k in c.lower() for k in [
        "forward","future","tp_","sl_","mfe","mae","outcome","trade_result"
    ])]
    add("no_future_outcome_fields",len(forbidden)==0,forbidden)

    vc=export.loc[export.provisional_regime!="UNAVAILABLE","provisional_regime"].value_counts(normalize=True)
    shares={k:float(vc.get(k,0.0)) for k in ["BULL","BEAR","SIDEWAYS"]}
    add("nondegenerate_class_shares",all(v>=0.05 for v in shares.values()),shares)

    stds={c:float(export[c].std()) for c in score_cols}
    add("score_std_gt_0_03",all(v>0.03 for v in stds.values()),stds)

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    yearly=[]
    for y in (2023,2024):
        q=export[export.index.year==y]
        v=q[q.provisional_regime!="UNAVAILABLE"].provisional_regime.value_counts(normalize=True)
        yearly.append({
            "year":y,
            "BULL":float(v.get("BULL",0)),
            "BEAR":float(v.get("BEAR",0)),
            "SIDEWAYS":float(v.get("SIDEWAYS",0)),
            "BullScore_med":float(q.BullScore.median()),
            "BearScore_med":float(q.BearScore.median()),
            "SidewaysScore_med":float(q.SidewaysScore.median()),
            "margin_med":float(q.score_margin.median()),
            "confidence_med":float(q.confidence_raw.median()),
        })

    valid=export[export.provisional_regime!="UNAVAILABLE"]
    runs=run_lengths(valid.provisional_regime)

    lines=[
        "# SOL Regime Detector — Stage 3 Raw Scoring Result","",
        "Stage 3 used **2023–2024 only**. 2025/2026 were not scored or inspected.","",
        "## Mandatory audits","",
        "| Audit | Pass | Value |","|---|---|---|"
    ]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Raw provisional regime distribution (no hysteresis)","",
              "| Period | Bull | Bear | Sideways |","|---|---:|---:|---:|"]
    lines.append(f"| 2023–24 combined | {shares['BULL']:.1%} | {shares['BEAR']:.1%} | {shares['SIDEWAYS']:.1%} |")
    for y in yearly:
        lines.append(f"| {y['year']} | {y['BULL']:.1%} | {y['BEAR']:.1%} | {y['SIDEWAYS']:.1%} |")

    lines += ["","## Score medians and separation","",
              "| Year | Bull median | Bear median | Sideways median | Margin median | Confidence median |",
              "|---|---:|---:|---:|---:|---:|"]
    for y in yearly:
        lines.append(
            f"| {y['year']} | {y['BullScore_med']:.3f} | {y['BearScore_med']:.3f} | "
            f"{y['SidewaysScore_med']:.3f} | {y['margin_med']:.3f} | {y['confidence_med']:.3f} |"
        )

    lines += ["","## Raw run-length diagnostic before hysteresis","",
              "| Regime | Runs | Median consecutive hours | P90 hours |",
              "|---|---:|---:|---:|"]
    for r in ["BULL","BEAR","SIDEWAYS"]:
        x=runs[r]
        lines.append(f"| {r} | {x['runs']} | {x['median']:.1f} | {x['p90']:.1f} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_VALID**","",
            "The unsupervised BullScore / BearScore / SidewaysScore system passed all frozen technical and symmetry audits.",
            "These raw argmax classes are **not the final detector**. Stage 4 must add hysteresis, minimum persistence, transition flags, and confidence handling before any forward-behavior validation.",
            "No 2025/2026 data or trading result was used."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_VALID\nNEXT=STAGE4_HYSTERESIS_TRANSITION\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_REJECTED**","",
            f"Failed audits: **{failed}**.",
            "Stage 4 is blocked until a new preregistered Stage-3 formulation passes the frozen audit requirements."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_REJECTED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
