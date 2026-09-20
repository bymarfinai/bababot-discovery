#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1
import bnb_b37_s1b_visual_equivalent as s1b

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S2_VISUAL_ANATOMY"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")
YEARS=[2022,2023,2024]
EPS=1e-12

CONT_FEATURES=[
    "demand_width_pct",
    "h4_bos_clearance_zw",
    "expansion_above_bos_zw",
    "expansion_from_demand_zw",
    "activation_to_touch_h",
    "expansion_to_touch_h",
    "pullback_bars",
    "pullback_depth",
    "penetration_zone_fraction",
    "touch_close_zone_fraction",
    "touch_close_location",
    "touch_body_ratio",
    "touch_lower_wick_ratio",
    "approach_lower_close_share_3",
    "approach_slope_3_zw",
    "approach_compression_3v3",
]
BIN_FEATURES=[
    "strict_exact",
    "touch_bullish",
    "distal_sweep_reclaim",
    "proximal_reclaim",
    "both_lh_ll",
]

def cliff_delta(a,b):
    a=np.asarray([x for x in a if np.isfinite(x)],dtype=float)
    b=np.asarray([x for x in b if np.isfinite(x)],dtype=float)
    if len(a)==0 or len(b)==0:return np.nan
    # positive => WIN values tend to be larger than LOSS values
    gt=(a[:,None]>b[None,:]).sum()
    lt=(a[:,None]<b[None,:]).sum()
    return float((gt-lt)/(len(a)*len(b)))

def structural_outcome(b1,r):
    q=b1[(b1.index>r.first_touch_ts)&(b1.index<=END)]
    up=float(r.expansion_high); dn=float(r.demand_low)
    for t,c in q.iterrows():
        close=float(c.close); hi=float(c.high); lo=float(c.low)
        if hi>up and lo<dn and dn<=close<=up:
            return "AMBIGUOUS_SAME_BAR",t
        if close>up:
            return "WIN_CONTINUATION",t
        if close<dn:
            return "LOSS_INVALIDATION",t
    return "UNRESOLVED",pd.NaT

def safe_div(a,b):
    return np.nan if not np.isfinite(a) or not np.isfinite(b) or abs(b)<=EPS else float(a/b)

def anatomy_row(b1,r):
    width=float(r.demand_high-r.demand_low)
    mid=(float(r.demand_high)+float(r.demand_low))/2.0
    tr=float(r.touch_high-r.touch_low)
    denom_expand=float(r.expansion_high-r.demand_high)

    pre=b1[(b1.index>=r.expansion_pivot_ts)&(b1.index<r.first_touch_ts)].copy()
    pull=b1[(b1.index>r.expansion_pivot_ts)&(b1.index<r.first_touch_ts)].copy()
    before=b1[b1.index<r.first_touch_ts].tail(7).copy()

    lower_share=np.nan
    slope=np.nan
    compression=np.nan
    if len(before)>=2:
        closes=before.close.to_numpy(float)
        d=np.diff(closes)
        steps=d[-3:] if len(d)>=3 else d
        lower_share=float((steps<0).mean()) if len(steps) else np.nan
    if len(before)>=4:
        slope=safe_div(float(before.close.iloc[-1]-before.close.iloc[-4]),width)
    if len(before)>=6:
        rg=(before.high-before.low).to_numpy(float)
        last3=np.median(rg[-3:])
        prev3=np.median(rg[-6:-3])
        compression=safe_div(last3,prev3)

    body=abs(float(r.touch_close-r.touch_open))
    lower_wick=min(float(r.touch_open),float(r.touch_close))-float(r.touch_low)

    return {
        "demand_width_pct":safe_div(width,mid),
        "h4_bos_clearance_zw":safe_div(float(r.h4_bos_close-r.broken_h4_level),width),
        "expansion_above_bos_zw":safe_div(float(r.expansion_high-r.h4_bos_close),width),
        "expansion_from_demand_zw":safe_div(float(r.expansion_high-r.demand_high),width),
        "activation_to_touch_h":float((r.first_touch_ts-r.activation_ts)/pd.Timedelta(hours=1)),
        "expansion_to_touch_h":float((r.first_touch_ts-r.expansion_pivot_ts)/pd.Timedelta(hours=1)),
        "pullback_bars":float(len(pull)),
        "pullback_depth":safe_div(float(r.expansion_high-r.touch_low),denom_expand),
        "penetration_zone_fraction":safe_div(float(r.demand_high-r.touch_low),width),
        "touch_close_zone_fraction":safe_div(float(r.touch_close-r.demand_low),width),
        "touch_close_location":safe_div(float(r.touch_close-r.touch_low),tr),
        "touch_body_ratio":safe_div(body,tr),
        "touch_lower_wick_ratio":safe_div(lower_wick,tr),
        "approach_lower_close_share_3":lower_share,
        "approach_slope_3_zw":slope,
        "approach_compression_3v3":compression,
        "strict_exact":bool(r.strict_exact),
        "touch_bullish":bool(float(r.touch_close)>float(r.touch_open)),
        "distal_sweep_reclaim":bool(float(r.touch_low)<float(r.demand_low) and float(r.touch_close)>=float(r.demand_low)),
        "proximal_reclaim":bool(float(r.touch_close)>float(r.demand_high)),
        "both_lh_ll":bool(r.has_lower_high and r.has_lower_low),
    }

def build_ledger(b1,visual):
    rows=[]
    for r in visual.itertuples(index=False):
        outcome,resolution_ts=structural_outcome(b1,r)
        a=anatomy_row(b1,r)
        rows.append({
            "zone_id":r.zone_id,
            "activation_ts":r.activation_ts,
            "origin_ts":r.origin_ts,
            "first_touch_ts":r.first_touch_ts,
            "retest_year":int(pd.Timestamp(r.first_touch_ts).year),
            "demand_low":float(r.demand_low),
            "demand_high":float(r.demand_high),
            "expansion_high":float(r.expansion_high),
            "expansion_pivot_ts":r.expansion_pivot_ts,
            "touch_open":float(r.touch_open),
            "touch_high":float(r.touch_high),
            "touch_low":float(r.touch_low),
            "touch_close":float(r.touch_close),
            "outcome":outcome,
            "resolution_ts":resolution_ts,
            **a,
        })
    return pd.DataFrame(rows)

def cont_summary(L):
    resolved=L[L.outcome.isin(["WIN_CONTINUATION","LOSS_INVALIDATION"])].copy()
    rows=[]; yearly=[]
    for f in CONT_FEATURES:
        w=pd.to_numeric(resolved.loc[resolved.outcome=="WIN_CONTINUATION",f],errors="coerce").dropna()
        l=pd.to_numeric(resolved.loc[resolved.outcome=="LOSS_INVALIDATION",f],errors="coerce").dropna()
        wm=float(w.median()) if len(w) else np.nan
        lm=float(l.median()) if len(l) else np.nan
        diff=wm-lm if np.isfinite(wm) and np.isfinite(lm) else np.nan
        delta=cliff_delta(w.to_numpy(),l.to_numpy())
        pooled_sign=0 if not np.isfinite(diff) or abs(diff)<=EPS else (1 if diff>0 else -1)
        qual=0; same=True
        for y in YEARS:
            q=resolved[resolved.retest_year==y]
            wy=pd.to_numeric(q.loc[q.outcome=="WIN_CONTINUATION",f],errors="coerce").dropna()
            ly=pd.to_numeric(q.loc[q.outcome=="LOSS_INVALIDATION",f],errors="coerce").dropna()
            yd=np.nan
            if len(wy)>=10 and len(ly)>=10:
                qual+=1
                yd=float(wy.median()-ly.median())
                ysign=0 if abs(yd)<=EPS else (1 if yd>0 else -1)
                if pooled_sign==0 or ysign!=pooled_sign:same=False
            yearly.append({"feature":f,"type":"continuous","year":y,
                           "win_n":len(wy),"loss_n":len(ly),
                           "win_median":float(wy.median()) if len(wy) else np.nan,
                           "loss_median":float(ly.median()) if len(ly) else np.nan,
                           "difference":yd})
        stable=bool(pooled_sign!=0 and qual>0 and same)
        rows.append({"feature":f,"win_n":len(w),"loss_n":len(l),"win_median":wm,"loss_median":lm,
                     "median_difference":diff,"cliffs_delta":delta,"qualified_years":qual,
                     "stable_directional":stable})
    return pd.DataFrame(rows),pd.DataFrame(yearly)

def bin_summary(L):
    resolved=L[L.outcome.isin(["WIN_CONTINUATION","LOSS_INVALIDATION"])].copy()
    rows=[]; yearly=[]
    for f in BIN_FEATURES:
        w=resolved[resolved.outcome=="WIN_CONTINUATION"][f].astype(bool)
        l=resolved[resolved.outcome=="LOSS_INVALIDATION"][f].astype(bool)
        wp=float(w.mean()) if len(w) else np.nan
        lp=float(l.mean()) if len(l) else np.nan
        diff=wp-lp if np.isfinite(wp) and np.isfinite(lp) else np.nan
        pooled_sign=0 if not np.isfinite(diff) or abs(diff)<=EPS else (1 if diff>0 else -1)
        qual=0; same=True
        for y in YEARS:
            q=resolved[resolved.retest_year==y]
            wy=q[q.outcome=="WIN_CONTINUATION"][f].astype(bool)
            ly=q[q.outcome=="LOSS_INVALIDATION"][f].astype(bool)
            yd=np.nan
            if len(wy)>=10 and len(ly)>=10:
                qual+=1
                yd=float(wy.mean()-ly.mean())
                ysign=0 if abs(yd)<=EPS else (1 if yd>0 else -1)
                if pooled_sign==0 or ysign!=pooled_sign:same=False
            yearly.append({"feature":f,"type":"binary","year":y,
                           "win_n":len(wy),"loss_n":len(ly),
                           "win_prevalence":float(wy.mean()) if len(wy) else np.nan,
                           "loss_prevalence":float(ly.mean()) if len(ly) else np.nan,
                           "difference":yd})
        stable=bool(pooled_sign!=0 and qual>0 and same)
        rows.append({"feature":f,"win_n":len(w),"loss_n":len(l),"win_prevalence":wp,"loss_prevalence":lp,
                     "prevalence_difference":diff,"qualified_years":qual,"stable_directional":stable})
    return pd.DataFrame(rows),pd.DataFrame(yearly)

def pct(x):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:.1f}%"

def num(x,d=3):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{d}f}"

def strongest(C,B):
    cand=[]
    for r in C.itertuples(index=False):
        if r.stable_directional and np.isfinite(r.cliffs_delta):
            cand.append({"feature":r.feature,"kind":"continuous","effect":abs(float(r.cliffs_delta)),
                         "direction":"higher in WIN" if r.median_difference>0 else "lower in WIN",
                         "detail":f"Cliff δ={r.cliffs_delta:.3f}; medians {r.win_median:.3f} vs {r.loss_median:.3f}; stable years={r.qualified_years}"})
    for r in B.itertuples(index=False):
        if r.stable_directional and np.isfinite(r.prevalence_difference):
            cand.append({"feature":r.feature,"kind":"binary","effect":abs(float(r.prevalence_difference)),
                         "direction":"more common in WIN" if r.prevalence_difference>0 else "less common in WIN",
                         "detail":f"Δ prevalence={100*r.prevalence_difference:.1f}pp; WIN {100*r.win_prevalence:.1f}% vs LOSS {100*r.loss_prevalence:.1f}%; stable years={r.qualified_years}"})
    cand=sorted(cand,key=lambda x:(x["effect"],x["feature"]),reverse=True)
    # Prefer features stable in all three years if available.
    full=[x for x in cand if "stable years=3" in x["detail"]]
    chosen=full[:4]
    if len(chosen)<4:
        seen={x["feature"] for x in chosen}
        chosen += [x for x in cand if x["feature"] not in seen][:4-len(chosen)]
    return chosen[:4]

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    b1=s1.exact_bars(raw,"1h",12)
    b4=s1.exact_bars(raw,"4h",48)
    zones=s1.h4_demand_zones(b4)
    fam,_=s1b.classify(b1,zones)
    visual=fam[fam.visual_equivalent].copy()
    if len(visual)!=201:
        raise RuntimeError(f"frozen visual family drift: expected 201, got {len(visual)}")

    L=build_ledger(b1,visual)
    C,CY=cont_summary(L)
    B,BY=bin_summary(L)
    Y=pd.concat([CY,BY],ignore_index=True,sort=False)
    top=strongest(C,B)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_Continuous.csv",index=False)
    B.to_csv(ROOT/f"{PFX}_Binary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_Yearly.csv",index=False)
    pd.DataFrame(top).to_csv(ROOT/f"{PFX}_StrongestStable.csv",index=False)

    census=L.outcome.value_counts().to_dict()
    year_rows=[]
    for y in YEARS:
        q=L[L.retest_year==y]
        year_rows.append({"year":y,**{k:int((q.outcome==k).sum()) for k in ["WIN_CONTINUATION","LOSS_INVALIDATION","AMBIGUOUS_SAME_BAR","UNRESOLVED"]}})
    pd.DataFrame(year_rows).to_csv(ROOT/f"{PFX}_OutcomeByYear.csv",index=False)

    lines=[
        "# BNB B37-S2 — Visual-Family Winner/Loser Structural Anatomy","",
        "**STEP 2 — ANATOMY DISCOVERY ONLY**","",
        "Frozen population: **201 B37-S1B visual-equivalent retests**. 2025-2026 remained unopened.","",
        "## Structural outcome race",
        "- WIN_CONTINUATION: H1 close above frozen pre-retest expansion high before H1 close below H4 demand low.",
        "- LOSS_INVALIDATION: H1 close below H4 demand low first.",
        "- AMBIGUOUS/UNRESOLVED are excluded from winner-vs-loser anatomy.","",
        "## Outcome census",
        f"- WIN_CONTINUATION: **{census.get('WIN_CONTINUATION',0)}**",
        f"- LOSS_INVALIDATION: **{census.get('LOSS_INVALIDATION',0)}**",
        f"- AMBIGUOUS_SAME_BAR: **{census.get('AMBIGUOUS_SAME_BAR',0)}**",
        f"- UNRESOLVED: **{census.get('UNRESOLVED',0)}**","",
        "### By retest year","",
        "| Year | WIN | LOSS | Ambiguous | Unresolved |",
        "|---:|---:|---:|---:|---:|"
    ]
    for r in year_rows:
        lines.append(f"| {r['year']} | {r['WIN_CONTINUATION']} | {r['LOSS_INVALIDATION']} | {r['AMBIGUOUS_SAME_BAR']} | {r['UNRESOLVED']} |")

    lines += ["","## Continuous anatomy comparison","",
              "| Feature | WIN median | LOSS median | Δ median | Cliff δ | Stable years | Stable direction |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for r in C.sort_values("cliffs_delta",key=lambda s:s.abs(),ascending=False).itertuples(index=False):
        lines.append(f"| {r.feature} | {num(r.win_median)} | {num(r.loss_median)} | {num(r.median_difference)} | {num(r.cliffs_delta)} | {r.qualified_years} | {'YES' if r.stable_directional else '—'} |")

    lines += ["","## Categorical anatomy comparison","",
              "| Flag | WIN | LOSS | Δ | Stable years | Stable direction |",
              "|---|---:|---:|---:|---:|---|"]
    for r in B.sort_values("prevalence_difference",key=lambda s:s.abs(),ascending=False).itertuples(index=False):
        lines.append(f"| {r.feature} | {pct(r.win_prevalence)} | {pct(r.loss_prevalence)} | {100*r.prevalence_difference:+.1f}pp | {r.qualified_years} | {'YES' if r.stable_directional else '—'} |")

    lines += ["","## Strongest stable structural separators",""]
    if top:
        for i,x in enumerate(top,1):
            lines.append(f"{i}. **{x['feature']}** — {x['direction']}; {x['detail']}.")
    else:
        lines.append("No preregistered anatomy feature showed stable directional separation.")

    lines += ["","## Step-2 decision",
              "**ANATOMY COMPLETE — NO DETECTOR RULE HAS BEEN SELECTED YET.**",
              "These are descriptive structural differences only. Step 3 must convert at most a small subset into named causal detector hypotheses and preregister their rules before any validation.",
              "No threshold optimization, timing filter, indicator, derivative data, TP/SL, PnL, or 2025-2026 reference evaluation was performed."]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B37_S2_ANATOMY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
