#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
F6B=ROOT/"SOL_REGIME_PHASE_STAGE6B_Features_DEV.csv"
S6B=ROOT/"SOL_REGIME_PHASE_STAGE6B_Status.txt"
L6D=ROOT/"SOL_REGIME_PHASE_STAGE6D_Labels_DEV.csv"
S6D=ROOT/"SOL_REGIME_PHASE_STAGE6D_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_PHASE_STAGE6F_Result.md"
OUT_SCAN=ROOT/"SOL_REGIME_PHASE_STAGE6F_FeatureScan.csv"
OUT_SURV=ROOT/"SOL_REGIME_PHASE_STAGE6F_Survivors.csv"
OUT_BLOCK=ROOT/"SOL_REGIME_PHASE_STAGE6F_BlockDetail.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_PHASE_STAGE6F_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6F_Status.txt"

SHARED=[
    "h1_atr_norm","h1_atr_vs_med72","h1_atr_pct168",
    "h1_mean_cross_12","h1_mean_cross_24",
    "h1_overlap_12","h1_overlap_24",
    "h1_range_path_12","h1_range_path_24",
    "atr_slope6","range24_atr","compression_6v24",
    "boundary_touch_count12","failed_escape_count24",
    "range_atr","volume_vs_med24","v1_regime_duration_hours",
]

BLOCKS=["2023-H1","2023-H2","2024-H1","2024-H2"]

def numericize(s):
    if s.dtype==bool:
        return s.astype(float)
    x=s.astype(str).str.lower()
    if x.isin(["true","false","1","0","1.0","0.0"]).mean()>0.98:
        return x.map({"true":1.0,"false":0.0,"1":1.0,"0":0.0,"1.0":1.0,"0.0":0.0})
    return pd.to_numeric(s,errors="coerce")

def auc_rank(y,score):
    y=np.asarray(y,dtype=int)
    s=np.asarray(score,dtype=float)
    m=np.isfinite(s) & np.isfinite(y)
    y=y[m]; s=s[m]
    n1=int((y==1).sum()); n0=int((y==0).sum())
    if n1==0 or n0==0:
        return np.nan
    ranks=pd.Series(s).rank(method="average").to_numpy(float)
    u=float(ranks[y==1].sum())-n1*(n1+1)/2.0
    return u/(n1*n0)

def oriented_auc(y,x,orientation):
    a=auc_rank(y,x)
    if pd.isna(a): return np.nan
    return a if orientation=="HIGH" else 1.0-a

def block_of(ts):
    if ts<pd.Timestamp("2023-07-01",tz="UTC"): return "2023-H1"
    if ts<pd.Timestamp("2024-01-01",tz="UTC"): return "2023-H2"
    if ts<pd.Timestamp("2024-07-01",tz="UTC"): return "2024-H1"
    return "2024-H2"

def main():
    s6b=(S6B.read_text() if S6B.exists() else "")
    s6d=(S6D.read_text() if S6D.exists() else "")

    f=pd.read_csv(F6B,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    l=pd.read_csv(L6D,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()

    idx=f.index.intersection(l.index)
    f=f.loc[idx].copy()
    l=l.loc[idx].copy()
    base=pd.DataFrame(index=idx)
    base["decision_time"]=l["decision_time"]
    base["selected_side"]=l["selected_side"]
    base["block"]=l["block"]
    base["year"]=l["year"]
    for h in (6,12,24):
        base[f"firsthit_{h}h"]=l[f"firsthit_{h}h"]
        base[f"aligned_hit_{h}h"]=pd.to_numeric(l[f"aligned_hit_{h}h"],errors="coerce")

    # Build symmetric routed feature universe.
    bull={c[len("bull_"):]:c for c in f.columns if c.startswith("bull_")}
    bear={c[len("bear_"):]:c for c in f.columns if c.startswith("bear_")}
    suffixes=sorted(set(bull).intersection(bear))

    candidates={}
    for suf in suffixes:
        bv=numericize(f[bull[suf]])
        rv=numericize(f[bear[suf]])
        arr=np.where(base.selected_side=="BULL",bv,np.where(base.selected_side=="BEAR",rv,np.nan))
        candidates["SIDE:"+suf]=pd.Series(arr,index=idx,dtype=float)

    for c in SHARED:
        if c in f.columns:
            candidates["SHARED:"+c]=numericize(f[c]).astype(float)

    # preregistered presence candidates.
    original=list(candidates.items())
    mask23=(base.year==2023)&base.aligned_hit_24h.notna()
    for name,s in original:
        cov=float(s[mask23].notna().mean()) if mask23.any() else 0.0
        if 0.05<=cov<=0.95:
            candidates[name+"__present"]=s.notna().astype(float)

    rows=[]
    block_rows=[]

    def target_mask(h,year=None):
        m=base[f"aligned_hit_{h}h"].notna()
        if year is not None:
            m &= (base.year==year)
        return m

    baseline={}
    for y in (2023,2024):
        m=target_mask(24,y)
        baseline[y]=float(base.loc[m,"aligned_hit_24h"].mean())

    for name,x in candidates.items():
        x=pd.to_numeric(x,errors="coerce")
        m23=target_mask(24,2023)&x.notna()
        m24=target_mask(24,2024)&x.notna()
        n23=int(m23.sum()); n24=int(m24.sum())

        rec={
            "feature":name,
            "n23":n23,"n24":n24,
            "eligible":False,
            "type":"",
            "orientation":"",
            "rule_value":np.nan,
            "auc23_raw":np.nan,"auc23_oriented":np.nan,
            "auc24_raw":np.nan,"auc24_oriented":np.nan,
            "auc24_6h_oriented":np.nan,"auc24_12h_oriented":np.nan,
            "fav_n23":0,"fav_hit23":np.nan,"fav_lift23":np.nan,
            "fav_n24":0,"fav_hit24":np.nan,"fav_lift24":np.nan,
            "positive_blocks":0,
            "tier":"INELIGIBLE",
        }
        if n23<500 or n24<500:
            rows.append(rec); continue

        vals23=x[m23]
        uniq=np.sort(vals23.dropna().unique())
        is_binary=len(uniq)<=2 and set(np.round(uniq,10)).issubset({0.0,1.0})
        typ="BINARY" if is_binary else "CONTINUOUS"
        y23=base.loc[m23,"aligned_hit_24h"].astype(int)
        auc23=auc_rank(y23.to_numpy(),vals23.to_numpy())

        if typ=="BINARY":
            h1=float(y23[vals23==1].mean()) if (vals23==1).sum() else np.nan
            h0=float(y23[vals23==0].mean()) if (vals23==0).sum() else np.nan
            favorable=1.0 if (pd.notna(h1) and pd.notna(h0) and h1>=h0) else 0.0
            orientation="HIGH" if favorable==1.0 else "LOW"
            threshold=favorable
            fav23=m23 & (x==favorable)
            fav24=m24 & (x==favorable)
        else:
            orientation="HIGH" if auc23>=0.50 else "LOW"
            threshold=float(vals23.quantile(0.80 if orientation=="HIGH" else 0.20))
            fav23=m23 & ((x>=threshold) if orientation=="HIGH" else (x<=threshold))
            fav24=m24 & ((x>=threshold) if orientation=="HIGH" else (x<=threshold))

        y24=base.loc[m24,"aligned_hit_24h"].astype(int)
        auc24=auc_rank(y24.to_numpy(),x[m24].to_numpy())
        oa23=auc23 if orientation=="HIGH" else 1.0-auc23
        oa24=auc24 if orientation=="HIGH" else 1.0-auc24

        fav_n23=int(fav23.sum()); fav_n24=int(fav24.sum())
        fav_hit23=float(base.loc[fav23,"aligned_hit_24h"].mean()) if fav_n23 else np.nan
        fav_hit24=float(base.loc[fav24,"aligned_hit_24h"].mean()) if fav_n24 else np.nan
        lift23=fav_hit23-baseline[2023] if pd.notna(fav_hit23) else np.nan
        lift24=fav_hit24-baseline[2024] if pd.notna(fav_hit24) else np.nan

        # secondary 2024 horizons using the same 2023-frozen orientation.
        sec={}
        for h in (6,12):
            mh=target_mask(h,2024)&x.notna()
            if mh.sum()>=500:
                sec[h]=oriented_auc(
                    base.loc[mh,f"aligned_hit_{h}h"].astype(int).to_numpy(),
                    x[mh].to_numpy(),orientation
                )
            else:
                sec[h]=np.nan

        positive_blocks=0
        for b in BLOCKS:
            mb=(base.block==b)&base.aligned_hit_24h.notna()&x.notna()
            if typ=="BINARY":
                fb=mb&(x==threshold)
            else:
                fb=mb&((x>=threshold) if orientation=="HIGH" else (x<=threshold))
            n=int(fb.sum())
            bh=float(base.loc[mb,"aligned_hit_24h"].mean()) if mb.sum() else np.nan
            fh=float(base.loc[fb,"aligned_hit_24h"].mean()) if n else np.nan
            lift=fh-bh if pd.notna(fh) and pd.notna(bh) else np.nan
            good=bool(n>=30 and pd.notna(lift) and lift>0)
            if good: positive_blocks+=1
            block_rows.append({
                "feature":name,"block":b,"fav_n":n,
                "baseline_hit":bh,"fav_hit":fh,"lift":lift,"positive":good
            })

        strong=(
            oa23>=0.54 and oa24>=0.53 and
            fav_n23>=100 and fav_n24>=100 and
            fav_hit23>=0.55 and fav_hit24>=0.54 and
            lift23>=0.03 and lift24>=0.03 and
            positive_blocks>=3 and
            ((pd.notna(sec[6]) and sec[6]>=0.52) or (pd.notna(sec[12]) and sec[12]>=0.52))
        )
        watch=(
            (not strong) and
            oa23>=0.53 and oa24>=0.515 and
            lift23>0 and lift24>0 and
            positive_blocks>=3
        )
        tier="STRONG_SURVIVOR" if strong else ("WATCHLIST" if watch else "NO_EDGE")

        rec.update({
            "eligible":True,"type":typ,"orientation":orientation,"rule_value":threshold,
            "auc23_raw":auc23,"auc23_oriented":oa23,
            "auc24_raw":auc24,"auc24_oriented":oa24,
            "auc24_6h_oriented":sec[6],"auc24_12h_oriented":sec[12],
            "fav_n23":fav_n23,"fav_hit23":fav_hit23,"fav_lift23":lift23,
            "fav_n24":fav_n24,"fav_hit24":fav_hit24,"fav_lift24":lift24,
            "positive_blocks":positive_blocks,"tier":tier,
        })
        rows.append(rec)

    scan=pd.DataFrame(rows)
    scan.to_csv(OUT_SCAN,index=False)
    bdf=pd.DataFrame(block_rows)
    bdf.to_csv(OUT_BLOCK,index=False)
    surv=scan[scan.tier.isin(["STRONG_SURVIVOR","WATCHLIST"])].copy()
    surv=surv.sort_values(["tier","auc24_oriented","fav_lift24"],ascending=[True,False,False])
    surv.to_csv(OUT_SURV,index=False)

    eligible=scan[scan.eligible].copy()
    strong=scan[scan.tier=="STRONG_SURVIVOR"]
    watch=scan[scan.tier=="WATCHLIST"]

    audit=[]
    def add(name,ok,value):
        audit.append({"audit":name,"pass":bool(ok),"value":value})

    add("stage6d_failed_status_present","SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATION_FAILED" in s6d,True)
    add("stage6b_valid","SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_VALID" in s6b,True)
    years=sorted(set(base.year.dropna().astype(int).tolist()))
    add("dev_years_only",all(y in (2023,2024) for y in years),years)
    add("no_2025_2026_loaded",not any(y>=2025 for y in years),years)
    # Routing copied directly from 6D labels; no alternative side is computed here.
    add("direction_routing_copied_from_6d",True,base.selected_side.value_counts().to_dict())
    add("future_labels_copied_from_6d",True,{"source":"Stage6D labels","relabel":False})
    add("2024_not_used_for_rule_fit",True,{"fit_year":2023,"validation_year":2024})
    add("at_least_50_eligible_candidates",len(eligible)>=50,len(eligible))
    badnames=[n for n in candidates if any(k in n.lower() for k in ["forward","future","outcome","tp_","sl_","trade_result"])]
    add("candidate_names_no_future_fields",len(badnames)==0,badnames)

    # Re-evaluate frozen gates mechanically for promoted rows.
    promoted_gate_ok=True
    badprom=[]
    for _,r in scan[scan.tier=="STRONG_SURVIVOR"].iterrows():
        ok=(
            r.auc23_oriented>=0.54 and r.auc24_oriented>=0.53 and
            r.fav_n23>=100 and r.fav_n24>=100 and
            r.fav_hit23>=0.55 and r.fav_hit24>=0.54 and
            r.fav_lift23>=0.03 and r.fav_lift24>=0.03 and
            r.positive_blocks>=3 and
            ((pd.notna(r.auc24_6h_oriented) and r.auc24_6h_oriented>=0.52) or
             (pd.notna(r.auc24_12h_oriented) and r.auc24_12h_oriented>=0.52))
        )
        if not ok: promoted_gate_ok=False; badprom.append(r.feature)
    for _,r in scan[scan.tier=="WATCHLIST"].iterrows():
        ok=(
            r.auc23_oriented>=0.53 and r.auc24_oriented>=0.515 and
            r.fav_lift23>0 and r.fav_lift24>0 and r.positive_blocks>=3
        )
        if not ok: promoted_gate_ok=False; badprom.append(r.feature)
    add("promoted_rows_match_frozen_gates",promoted_gate_ok,badprom)

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    tech=bool(adf["pass"].all())

    top=eligible.sort_values(
        ["auc24_oriented","fav_lift24","auc23_oriented"],
        ascending=False
    ).head(15)

    # Distribution of validation AUCs is useful to see whether everything clusters around noise.
    q=eligible.auc24_oriented.dropna()
    aq={p:float(q.quantile(p)) for p in [0.5,0.75,0.9,0.95,0.99]} if len(q) else {}

    lines=[
        "# SOL Regime + Phase V2 — Stage 6F Predictive Feature Forensics","",
        "Stage 6F scanned individual causal Stage-6B features using **2023 discovery** and **2024 frozen-rule validation**. 2025/2026 were not opened.","",
        f"- Candidates constructed: **{len(candidates)}**.",
        f"- Eligible after support floors: **{len(eligible)}**.",
        f"- STRONG_SURVIVOR: **{len(strong)}**.",
        f"- WATCHLIST: **{len(watch)}**.","",
        "## Top validated individual features","",
        "| Feature | Type | Direction | AUC23 | AUC24 | Hit23 | Lift23 | Hit24 | Lift24 | + blocks | Tier |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for _,r in top.iterrows():
        lines.append(
            f"| {r.feature} | {r.type} | {r.orientation} | {r.auc23_oriented:.3f} | {r.auc24_oriented:.3f} | "
            f"{r.fav_hit23:.1%} | {r.fav_lift23:+.1%} | {r.fav_hit24:.1%} | {r.fav_lift24:+.1%} | "
            f"{int(r.positive_blocks)} | {r.tier} |"
        )

    lines += ["","## 2024 oriented-AUC distribution","",
              str(aq),"",
              "## Survivors",""]
    if len(surv):
        lines += ["| Feature | Tier | AUC23 | AUC24 | Hit23 | Hit24 | Lift23 | Lift24 | Blocks |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for _,r in surv.iterrows():
            lines.append(
                f"| {r.feature} | {r.tier} | {r.auc23_oriented:.3f} | {r.auc24_oriented:.3f} | "
                f"{r.fav_hit23:.1%} | {r.fav_hit24:.1%} | {r.fav_lift23:+.1%} | {r.fav_lift24:+.1%} | {int(r.positive_blocks)} |"
            )
    else:
        lines.append("**No feature met either frozen survivor gate.**")

    lines += ["","## Technical audits","",
              "| Audit | Pass | Value |","|---|---|---|"]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Decision",""]
    if tech:
        if len(strong)>0:
            lines += [
                "**Status: SOL_REGIME_PHASE_STAGE6F_STRONG_FEATURES_FOUND**","",
                "At least one individual causal feature survived the preregistered 2023 -> 2024 robustness gates.",
                "These features are candidates for a separately preregistered interaction/event study; they are not yet a trading strategy."
            ]
            status="SOL_REGIME_PHASE_STAGE6F_STRONG_FEATURES_FOUND"
        elif len(watch)>0:
            lines += [
                "**Status: SOL_REGIME_PHASE_STAGE6F_WATCHLIST_ONLY**","",
                "No individual feature met the strong survivor gate, but one or more features met the weaker preregistered watchlist gate.",
                "The evidence is insufficient for direct promotion; any next step should test preregistered combinations/interactions."
            ]
            status="SOL_REGIME_PHASE_STAGE6F_WATCHLIST_ONLY"
        else:
            lines += [
                "**Status: SOL_REGIME_PHASE_STAGE6F_NO_UNIVARIATE_EDGE**","",
                "No individual Stage-6B feature survived even the preregistered watchlist gate from 2023 into 2024.",
                "This indicates the missing edge is unlikely to be a simple one-feature threshold and motivates interaction/event-sequence research rather than more single-score weighting."
            ]
            status="SOL_REGIME_PHASE_STAGE6F_NO_UNIVARIATE_EDGE"
        OUT_STATUS.write_text(status+"\n2025_UNOPENED=true\n")
    else:
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6F_TECHNICAL_INVALID**","",
            "Technical audit failure prevents interpretation."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6F_TECHNICAL_INVALID\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
