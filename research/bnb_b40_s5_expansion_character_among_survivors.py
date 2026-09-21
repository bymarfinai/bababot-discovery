#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S5_EXPANSION_CHARACTER_AMONG_SURVIVORS"
S1=ROOT/"results/bnb_b40_s1/BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_CandidateLedger.csv.gz"
S3=ROOT/"results/bnb_b40_s3/BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY_DecisionLedger.csv.gz"

LABELS={
    "GE1R":("hit_1_0r",1.0),
    "GE1_5R":("hit_1_5r",1.5),
    "GE2R":("hit_2_0r",2.0),
}

FORMATION_NUM=[
    "base_candles","base_width_pct","base_mean_added_overlap","base_mean_body_frac",
    "departure_bars","departure_net_progress_zone_r","departure_efficiency",
    "bos_overshoot_zone_r","bos_body_frac","max_bull_fvg_zone_r",
    "source_age_at_activation_h","protected_depth_to_broken_level_zone_r",
]
FORMATION_BIN=["has_bull_fvg","predeparture_swept_prior_low"]

RETEST_NUM=[
    "zone_age_at_retest_h","approach_slope_per_zone_r","approach_efficiency",
    "approach_overlap_mean","approach_net_progress_zone_r",
    "last1_bear_progress_zone_r","last2_bear_progress_zone_r","last3_bear_progress_zone_r",
]
RETEST_BIN=["touch_local_liquidity_sweep"]

TOUCH_NUM=[
    "touch_penetration_zone_r","touch_floor_sweep_depth_zone_r",
    "touch_close_vs_zone_high_zone_r","touch_close_vs_floor_zone_r",
    "touch_recovery_from_low_event_r","touch_lower_wick_event_r",
    "touch_upper_wick_event_r","touch_body_event_r","touch_range_event_r",
    "touch_close_location_in_candle",
]
TOUCH_BIN=["TOUCH_CLOSE_ABOVE_ZONE","TOUCH_BULLISH","TOUCH_SWEEP_FLOOR_RECLAIM"]

P5_NUM=[
    "p5_close_r","p5_high_r","p5_low_r","p5_body_r","p5_range_r",
    "p5_recovery_from_low_r","p5_close_location","p5_close_vs_zone_high_zone_r",
]
P5_BIN=[
    "CLOSE5_ABOVE_ANCHOR","CLOSE5_ABOVE_ZONE","CLOSE5_BREAK_TOUCH_HIGH",
    "CLOSE5_BULLISH","LOW5_HOLDS_TOUCH_LOW","RETEST5_ZONE_RECLAIM",
]

P15_NUM=[
    "p15_close_r","p15_high_r","p15_low_r","p15_body_r","p15_range_r",
    "p15_close_location","p15_green_rate","p15_close_slope_r_per_bar",
    "p15_path_efficiency","p15_min_close_r","p15_max_close_r",
    "p15_close_above_anchor_rate","p15_close_above_zone_rate",
]
P15_BIN=[
    "CLOSE15_ABOVE_ANCHOR","CLOSE15_ABOVE_ZONE","CLOSE15_BREAK_TOUCH_HIGH",
    "ALL3_CLOSES_ABOVE_ANCHOR","ALL3_CLOSES_ABOVE_ZONE",
    "RECLAIM_ZONE_THEN_HOLD","BREAK_TOUCH_HIGH_WITHIN15",
]

PROOF_NUM=["time_to_0_5r_min"]
PROOF_BIN=["PROOF_WITHIN_15M","PROOF_WITHIN_30M","PROOF_WITHIN_60M"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def boolify(s):
    if s.dtype==bool: return s
    return s.astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})

def band_name(x,c1,c2,c3):
    if not np.isfinite(x): return "NA"
    if x<=c1:return "Q1"
    if x<=c2:return "Q2"
    if x<=c3:return "Q3"
    return "Q4"

def effect_numeric(q,feature,label,dev_iqr):
    pos=pd.to_numeric(q.loc[q[label],feature],errors="coerce").dropna()
    neg=pd.to_numeric(q.loc[~q[label],feature],errors="coerce").dropna()
    if not len(pos) or not len(neg):
        return np.nan,np.nan,np.nan
    mp=float(pos.median()); mn=float(neg.median())
    eff=(mp-mn)/dev_iqr if np.isfinite(dev_iqr) and dev_iqr>0 else np.nan
    return mp,mn,eff

def effect_binary(q,feature,label):
    z=q[q[feature].notna()].copy()
    if not len(z): return np.nan,np.nan,np.nan,0
    x=z[feature].astype(bool)
    t=z[x]; f=z[~x]
    rt=float(t[label].mean()) if len(t) else np.nan
    rf=float(f[label].mean()) if len(f) else np.nan
    return rt,rf,(rt-rf if np.isfinite(rt) and np.isfinite(rf) else np.nan),len(z)

def load():
    A=pd.read_csv(S1,compression="gzip")
    B=pd.read_csv(S3,compression="gzip")
    for c in ["first_retest_ts","consumption_ts","survival_resolution_ts","activation_ts"]:
        if c in A.columns: A[c]=pd.to_datetime(A[c],utc=True,errors="coerce")
    for c in ["first_retest_ts","decision_ts"]:
        if c in B.columns: B[c]=pd.to_datetime(B[c],utc=True,errors="coerce")

    A["normalizable"]=boolify(A.normalizable)
    for c,_ in LABELS.values():
        A[c]=boolify(A[c])
    for c in FORMATION_BIN+RETEST_BIN:
        if c in A.columns: A[c]=boolify(A[c])

    surv=A[A.normalizable & A.survival_status.eq("SURVIVE")].copy()
    surv["base_width_pct"]=pd.to_numeric(surv.base_width,errors="coerce")/pd.to_numeric(surv.bos_close,errors="coerce")
    surv["protected_depth_to_broken_level_zone_r"]=(
        (pd.to_numeric(surv.broken_level,errors="coerce")-pd.to_numeric(surv.protected_low,errors="coerce"))/
        pd.to_numeric(surv.base_width,errors="coerce")
    )
    surv["PROOF_WITHIN_15M"]=pd.to_numeric(surv.time_to_0_5r_min,errors="coerce")<=15
    surv["PROOF_WITHIN_30M"]=pd.to_numeric(surv.time_to_0_5r_min,errors="coerce")<=30
    surv["PROOF_WITHIN_60M"]=pd.to_numeric(surv.time_to_0_5r_min,errors="coerce")<=60

    exp={
        "DEV":(500,361,266,205),
        "REF":(309,231,168,134),
    }
    for per,(n,a,b,c) in exp.items():
        q=surv[surv.period==per]
        got=(len(q),int(q.hit_1_0r.sum()),int(q.hit_1_5r.sum()),int(q.hit_2_0r.sum()))
        if got!=(n,a,b,c):
            raise RuntimeError(f"S1 survivor parity drift {per}: {got} != {(n,a,b,c)}")

    for c in TOUCH_BIN+P5_BIN+P15_BIN:
        if c in B.columns: B[c]=boolify(B[c])
    return surv,B

def reaction_frame(surv,B,decision):
    rb=B[B.decision==decision].copy()
    keep=[c for c in rb.columns if c not in {"period","year","first_retest_ts","survival_status","survived","event_risk","base_width","base_low","base_high","protected_low","touch_open","touch_high","touch_low","touch_close"}]
    rb=rb[["zone_id"]+keep].copy()
    return surv.merge(rb,on="zone_id",how="left",validate="one_to_one")

def decision_gate(raw5,q,n_bars,threshold_r):
    status=[]
    idx=raw5.index
    for r in q.itertuples(index=False):
        i0=int(idx.searchsorted(pd.Timestamp(r.first_retest_ts),side="right"))
        if i0+n_bars>len(raw5):
            status.append("DECISION_CENSORED"); continue
        bars=raw5.iloc[i0:i0+n_bars]
        dec_ts=bars.index[-1]
        # Once later structural consumption has occurred, no later feature may classify expansion.
        if pd.notna(r.consumption_ts) and pd.Timestamp(r.consumption_ts)<=dec_ts:
            status.append("TOO_FAST_CONSUMED"); continue
        target=float(r.touch_close)+threshold_r*float(r.event_risk)
        if bool((bars.high>=target).any()):
            status.append("TOO_FAST_TARGET"); continue
        status.append("ELIGIBLE")
    return np.asarray(status,dtype=object)

def analyze_family(df,family,decision,num_features,bin_features,labels,gate_map=None):
    comp=[]; cuts=[]; bands=[]; states=[]
    for lab in labels:
        q0=df.copy()
        if gate_map is not None:
            q0=q0[gate_map[lab]=="ELIGIBLE"].copy()
        for f in num_features:
            if f not in q0.columns: continue
            ddev=q0[q0.period=="DEV"]
            xd=pd.to_numeric(ddev[f],errors="coerce").dropna()
            iqr=float(xd.quantile(.75)-xd.quantile(.25)) if len(xd) else np.nan
            q25=float(xd.quantile(.25)) if len(xd) else np.nan
            q50=float(xd.quantile(.50)) if len(xd) else np.nan
            q75=float(xd.quantile(.75)) if len(xd) else np.nan
            cuts.append({"family":family,"decision":decision,"label":lab,"feature":f,"q25":q25,"q50":q50,"q75":q75,"dev_n":len(xd)})
            vals={}
            for per in ["DEV","REF"]:
                q=q0[q0.period==per]
                mp,mn,e=effect_numeric(q,f,lab,iqr)
                vals[per]=(mp,mn,e,int(pd.to_numeric(q[f],errors="coerce").notna().sum()))
            de=vals["DEV"][2]; re=vals["REF"][2]
            con=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            comp.append({
                "family":family,"decision":decision,"label":lab,"feature":f,"feature_type":"NUMERIC",
                "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":con,"robust_score":min(abs(de),abs(re)) if con else 0.0,
            })
            if all(np.isfinite([q25,q50,q75])) and q25<q50<q75:
                for per in ["DEV","REF"]:
                    q=q0[q0.period==per].copy()
                    q["_x"]=pd.to_numeric(q[f],errors="coerce")
                    q=q[np.isfinite(q._x)].copy()
                    q["band"]=[band_name(float(v),q25,q50,q75) for v in q._x]
                    for band in ["Q1","Q2","Q3","Q4"]:
                        z=q[q.band==band]
                        if len(z):
                            bands.append({
                                "family":family,"decision":decision,"label":lab,"feature":f,
                                "period":per,"band":band,"n":len(z),"success":int(z[lab].sum()),
                                "success_rate":float(z[lab].mean()),
                            })
        for f in bin_features:
            if f not in q0.columns: continue
            vals={}
            for per in ["DEV","REF"]:
                q=q0[q0.period==per]
                rt,rf,e,n=effect_binary(q,f,lab)
                vals[per]=(rt,rf,e,n)
                states.append({
                    "family":family,"decision":decision,"label":lab,"feature":f,"period":per,
                    "true_rate":rt,"false_rate":rf,"rate_diff":e,"n":n,
                })
            de=vals["DEV"][2]; re=vals["REF"][2]
            con=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            comp.append({
                "family":family,"decision":decision,"label":lab,"feature":f,"feature_type":"BINARY",
                "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":con,"robust_score":min(abs(de),abs(re)) if con else 0.0,
            })
    return comp,cuts,bands,states

def main():
    surv,B=load()
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)

    # Unified labels.
    for name,(col,_) in LABELS.items():
        surv[name]=surv[col].astype(bool)

    touch=reaction_frame(surv,B,"TOUCH_CLOSE")
    p5=reaction_frame(surv,B,"PLUS5_CLOSE")
    p15=reaction_frame(surv,B,"PLUS15_CLOSE")
    for df in [touch,p5,p15]:
        for name,(col,_) in LABELS.items():
            if name not in df.columns:
                df[name]=df[col].astype(bool)

    gates5={}; gates15={}
    for name,(_,thr) in LABELS.items():
        gates5[name]=decision_gate(raw5,p5,1,thr)
        gates15[name]=decision_gate(raw5,p15,3,thr)

    all_comp=[]; all_cuts=[]; all_bands=[]; all_states=[]
    specs=[
        (surv,"FORMATION","BOS_CLOSE",FORMATION_NUM,FORMATION_BIN,None),
        (surv,"RETEST_APPROACH","TOUCH_CLOSE",RETEST_NUM,RETEST_BIN,None),
        (touch,"TOUCH_REACTION","TOUCH_CLOSE",TOUCH_NUM,TOUCH_BIN,None),
        (p5,"PLUS5_REACTION","PLUS5_CLOSE",P5_NUM,P5_BIN,gates5),
        (p15,"PLUS15_REACTION","PLUS15_CLOSE",P15_NUM,P15_BIN,gates15),
        (surv,"SURVIVAL_PROOF_SPEED","SURVIVAL_PROOF",PROOF_NUM,PROOF_BIN,None),
    ]
    for df,fam,dec,nums,bins,gates in specs:
        c,u,b,s=analyze_family(df,fam,dec,nums,bins,list(LABELS),gates)
        all_comp.extend(c); all_cuts.extend(u); all_bands.extend(b); all_states.extend(s)

    FC=pd.DataFrame(all_comp)
    CUT=pd.DataFrame(all_cuts)
    BA=pd.DataFrame(all_bands)
    ST=pd.DataFrame(all_states)
    R=FC.sort_values(["label","family","direction_consistent","robust_score"],ascending=[True,True,False,False]).copy()

    # Gate census.
    GC=[]
    for dec,df,gates in [("PLUS5_CLOSE",p5,gates5),("PLUS15_CLOSE",p15,gates15)]:
        for lab in LABELS:
            for per in ["DEV","REF"]:
                mask=df.period.eq(per)
                g=np.asarray(gates[lab])[mask.to_numpy()]
                q=df[mask]
                eligible=g=="ELIGIBLE"
                GC.append({
                    "decision":dec,"label":lab,"period":per,"n":len(q),
                    "eligible":int(eligible.sum()),
                    "eligible_success":int(q.loc[eligible,lab].sum()),
                    "eligible_rate":float(q.loc[eligible,lab].mean()) if eligible.any() else np.nan,
                    "too_fast_target":int((g=="TOO_FAST_TARGET").sum()),
                    "too_fast_consumed":int((g=="TOO_FAST_CONSUMED").sum()),
                    "censored":int((g=="DECISION_CENSORED").sum()),
                })
    GC=pd.DataFrame(GC)

    # Year audit for top 3 consistent GE1R descriptors per family.
    Y=[]
    top=R[(R.label=="GE1R")&R.direction_consistent].groupby("family",group_keys=False).head(3)
    frame_map={
        "FORMATION":surv,"RETEST_APPROACH":surv,"TOUCH_REACTION":touch,
        "PLUS5_REACTION":p5,"PLUS15_REACTION":p15,"SURVIVAL_PROOF_SPEED":surv,
    }
    gate_family={"PLUS5_REACTION":gates5["GE1R"],"PLUS15_REACTION":gates15["GE1R"]}
    for rr in top.itertuples(index=False):
        df=frame_map[rr.family].copy()
        if rr.family in gate_family:
            df=df[np.asarray(gate_family[rr.family])=="ELIGIBLE"].copy()
        if rr.feature_type=="NUMERIC":
            cr=CUT[(CUT.family==rr.family)&(CUT.label=="GE1R")&(CUT.feature==rr.feature)]
            if cr.empty: continue
            cr=cr.iloc[0]
            if not (cr.q25<cr.q50<cr.q75): continue
            for y in [2022,2023,2024,2025,2026]:
                q=df[df.year==y].copy()
                q["_x"]=pd.to_numeric(q[rr.feature],errors="coerce")
                q=q[np.isfinite(q._x)]
                q["state"]=[band_name(float(v),cr.q25,cr.q50,cr.q75) for v in q._x]
                for st,z in q.groupby("state"):
                    Y.append({"family":rr.family,"feature":rr.feature,"feature_type":"NUMERIC","year":y,
                              "state":st,"n":len(z),"success":int(z.GE1R.sum()),"rate":float(z.GE1R.mean())})
        else:
            for y in [2022,2023,2024,2025,2026]:
                q=df[df.year==y]
                if rr.feature not in q: continue
                q=q[q[rr.feature].notna()]
                for st in [False,True]:
                    z=q[q[rr.feature].astype(bool)==st]
                    if len(z):
                        Y.append({"family":rr.family,"feature":rr.feature,"feature_type":"BINARY","year":y,
                                  "state":str(st),"n":len(z),"success":int(z.GE1R.sum()),"rate":float(z.GE1R.mean())})
    Y=pd.DataFrame(Y)

    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    BA.to_csv(ROOT/f"{PFX}_Quartiles.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StateAudit.csv",index=False)
    GC.to_csv(ROOT/f"{PFX}_DecisionCensus.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_TopFeatureByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        "PARENT=B40_S1_TRUE_SURVIVORS\n"
        "DEV_SURVIVORS=500\nREF_SURVIVORS=309\n"
        "PRIMARY_LABEL=GE1R\nSECONDARY_LABELS=GE1_5R,GE2R\n"
        "PLUS5_PLUS15_TARGET_RESOLUTION_EXCLUDED=TRUE\n"
        "LATER_CONSUMPTION_BEFORE_DECISION_EXCLUDED=TRUE\n"
        "NO_COMBINATIONS=TRUE\nNO_PROMOTION=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S5 — Expansion Character Among Surviving Demand","",
        "Universe = true B40 SURVIVE zones only. Primary question: LOCAL_ONLY (<1R) vs GE1R expansion.","",
        "## Frozen survivor universe","",
        "| Period | Survivors | >=1R | >=1.5R | >=2R |",
        "|---|---:|---:|---:|---:|"
    ]
    for per in ["DEV","REF"]:
        q=surv[surv.period==per]
        lines.append(
            f"| {per} | {len(q)} | {int(q.GE1R.sum())} ({fmt_pct(q.GE1R.mean())}) | "
            f"{int(q.GE1_5R.sum())} ({fmt_pct(q.GE1_5R.mean())}) | "
            f"{int(q.GE2R.sum())} ({fmt_pct(q.GE2R.mean())}) |"
        )

    lines += ["","## Causal reaction decision census — GE1R","",
              "| Decision | Period | N | Eligible | GE1R residual | Too-fast GE1R | Consumed before decision |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for r in GC[GC.label=="GE1R"].itertuples(index=False):
        lines.append(
            f"| {r.decision} | {r.period} | {r.n} | {r.eligible} | "
            f"{r.eligible_success}/{r.eligible} ({fmt_pct(r.eligible_rate)}) | "
            f"{r.too_fast_target} | {r.too_fast_consumed} |"
        )

    for fam in ["FORMATION","RETEST_APPROACH","TOUCH_REACTION","PLUS5_REACTION","PLUS15_REACTION","SURVIVAL_PROOF_SPEED"]:
        lines += ["",f"## {fam} — strongest consistent GE1R separators","",
                  "| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |",
                  "|---|---|---:|---:|---:|---:|"]
        q=R[(R.family==fam)&(R.label=="GE1R")&R.direction_consistent].head(10)
        for r in q.itertuples(index=False):
            lines.append(
                f"| {r.feature} | {r.feature_type} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
                f"{fmt_num(r.dev_pos)}/{fmt_num(r.dev_neg)} | {fmt_num(r.ref_pos)}/{fmt_num(r.ref_neg)} |"
            )

    lines += ["","## Interpretation boundary",
        "S5 discovers individual expansion descriptors only.",
        "A true survival label is used to isolate expansion anatomy; this is not yet a live trading gate.",
        "No feature combination, Expansion Detector, entry, SL, or TP is promoted in S5."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S5_EXPANSION_CHARACTER_AMONG_SURVIVORS_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
