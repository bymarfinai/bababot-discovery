#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s1_real_expansion_universe as s39

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S2_BACKWARD_PRETOUCH_ANATOMY"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")

LABELS=["GE1R","GE1_5R","CLEAN1R","CLEAN1_5R"]

NUM_FEATURES=[
    "demand_width_pct",
    "bos_break_pct",
    "bos_body_zw",
    "bos_range_zw",
    "bos_close_location",
    "zone_age_hours",
    "origin_to_activation_hours",
    "broken_swing_to_activation_hours",
    "expansion_room_zw",
    "pullback_bars",
    "pullback_duration_hours",
    "retracement_expansion_to_preclose_zw",
    "pullback_total_range_zw",
    "lower_high_count",
    "lower_high_rate",
    "lower_low_count",
    "lower_low_rate",
    "pullback_close_slope_zw_per_bar",
    "pullback_path_efficiency",
    "pullback_overlap_rate",
    "compression_last3_vs_earlier",
    "last1_progress_zw",
    "last3_progress_zw",
    "last3_green_rate",
    "last3_range_vs_pullback_median",
    "preclose_to_demand_high_zw",
    "preclose_to_demand_low_zw",
    "last_bar_close_location",
    "last_bar_body_zw",
    "last_bar_range_zw",
    "h1_nearest_high_room_zw",
    "h1_nearest_low_distance_zw",
    "h1_close_to_demand_high_zw",
    "h1_close_to_demand_low_zw",
]
BIN_FEATURES=[
    "has_lower_high",
    "has_lower_low",
    "h1_hh",
    "h1_hl",
    "h1_hh_hl",
    "h1_bearish_ll_lh",
]

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def safe_div(a,b):
    return float(a/b) if np.isfinite(a) and np.isfinite(b) and b!=0 else np.nan

def close_location(bar):
    rng=float(bar.high-bar.low)
    return float((bar.close-bar.low)/rng) if rng>0 else np.nan

def pullback_features(m15,r):
    idx=m15.index
    t=pd.Timestamp(r.first_touch_ts)
    pre_ts=t-pd.Timedelta(minutes=15)
    if pre_ts not in idx:
        return None

    p_i=int(idx.get_loc(pd.Timestamp(r.expansion_pivot_ts)))
    e_i=int(idx.get_loc(pre_ts))
    if e_i<=p_i:
        return None

    # Frozen B38 family used expansion pivot +1 through bar before touch.
    seg=m15.iloc[p_i+1:e_i+1].copy()
    if len(seg)<1:
        return None

    width=float(r.demand_width)
    pre=seg.iloc[-1]

    highs=seg.high.to_numpy(float)
    lows=seg.low.to_numpy(float)
    closes=seg.close.to_numpy(float)

    dh=np.diff(highs)
    dl=np.diff(lows)
    lh_count=int((dh<0).sum()) if len(dh) else 0
    ll_count=int((dl<0).sum()) if len(dl) else 0
    denom=max(1,len(seg)-1)

    if len(closes)>=2:
        x=np.arange(len(closes),dtype=float)
        slope=float(np.polyfit(x,closes,1)[0])/width
        path_denom=float(np.abs(np.diff(closes)).sum())
        path_eff=float((closes[-1]-closes[0])/path_denom) if path_denom>0 else np.nan
    else:
        slope=np.nan
        path_eff=np.nan

    overlaps=[]
    for i in range(1,len(seg)):
        lo=max(float(seg.low.iloc[i-1]),float(seg.low.iloc[i]))
        hi=min(float(seg.high.iloc[i-1]),float(seg.high.iloc[i]))
        overlaps.append(hi>=lo)
    overlap_rate=float(np.mean(overlaps)) if overlaps else np.nan

    ranges=(seg.high-seg.low).astype(float)
    if len(seg)>=6:
        early=ranges.iloc[:-3]
        last3=ranges.iloc[-3:]
        compression=safe_div(float(last3.median()),float(early.median()))
    else:
        compression=np.nan

    last1=(float(closes[-1])-float(closes[-2]))/width if len(closes)>=2 else np.nan
    last3=(float(closes[-1])-float(closes[-4]))/width if len(closes)>=4 else np.nan
    if len(seg)>=3:
        q=seg.iloc[-3:]
        last3_green=float((q.close>q.open).mean())
        med_all=float(ranges.median())
        last3_range_vs_med=safe_div(float((q.high-q.low).median()),med_all)
    else:
        last3_green=np.nan
        last3_range_vs_med=np.nan

    return {
        "pre_touch_ts":pre_ts,
        "pre_touch_close":float(pre.close),
        "pullback_bars":float(len(seg)),
        "pullback_duration_hours":float((pre_ts-pd.Timestamp(r.expansion_pivot_ts))/pd.Timedelta(hours=1)),
        "retracement_expansion_to_preclose_zw":(float(r.expansion_high)-float(pre.close))/width,
        "pullback_total_range_zw":(float(seg.high.max())-float(seg.low.min()))/width,
        "lower_high_count":float(lh_count),
        "lower_high_rate":float(lh_count/denom),
        "lower_low_count":float(ll_count),
        "lower_low_rate":float(ll_count/denom),
        "pullback_close_slope_zw_per_bar":slope,
        "pullback_path_efficiency":path_eff,
        "pullback_overlap_rate":overlap_rate,
        "compression_last3_vs_earlier":compression,
        "last1_progress_zw":last1,
        "last3_progress_zw":last3,
        "last3_green_rate":last3_green,
        "last3_range_vs_pullback_median":last3_range_vs_med,
        "preclose_to_demand_high_zw":(float(pre.close)-float(r.demand_high))/width,
        "preclose_to_demand_low_zw":(float(pre.close)-float(r.demand_low))/width,
        "last_bar_close_location":close_location(pre),
        "last_bar_body_zw":(float(pre.close)-float(pre.open))/width,
        "last_bar_range_zw":(float(pre.high)-float(pre.low))/width,
    }

def h1_context(h1,h1_hi,h1_lo,pre_ts,preclose,width,r):
    # latest completed H1 bar no later than pre-touch cutoff
    hidx=h1.index[h1.index<=pre_ts]
    if not len(hidx):
        return None
    hb=h1.loc[hidx[-1]]

    hi=h1_hi[h1_hi.confirm_ts<=pre_ts].sort_values("confirm_ts")
    lo=h1_lo[h1_lo.confirm_ts<=pre_ts].sort_values("confirm_ts")

    nearest_hi=float(hi.loc[hi.level>preclose,"level"].min()) if len(hi[hi.level>preclose]) else np.nan
    nearest_lo=float(lo.loc[lo.level<preclose,"level"].max()) if len(lo[lo.level<preclose]) else np.nan

    hh=False; hl=False; bearish=False
    if len(hi)>=2:
        hh=float(hi.iloc[-1].level)>float(hi.iloc[-2].level)
        lh=float(hi.iloc[-1].level)<float(hi.iloc[-2].level)
    else:
        lh=False
    if len(lo)>=2:
        hl=float(lo.iloc[-1].level)>float(lo.iloc[-2].level)
        ll=float(lo.iloc[-1].level)<float(lo.iloc[-2].level)
    else:
        ll=False

    if len(hi) and len(lo):
        ih=hi.iloc[-1]; il=lo.iloc[-1]
        if pd.Timestamp(ih.confirm_ts)>pd.Timestamp(il.confirm_ts):
            last_type="HIGH"
        elif pd.Timestamp(il.confirm_ts)>pd.Timestamp(ih.confirm_ts):
            last_type="LOW"
        else:
            last_type="BOTH"
    elif len(hi):
        last_type="HIGH"
    elif len(lo):
        last_type="LOW"
    else:
        last_type="NONE"

    return {
        "h1_nearest_high_room_zw":(nearest_hi-preclose)/width if np.isfinite(nearest_hi) else np.nan,
        "h1_nearest_low_distance_zw":(preclose-nearest_lo)/width if np.isfinite(nearest_lo) else np.nan,
        "h1_close_to_demand_high_zw":(float(hb.close)-float(r.demand_high))/width,
        "h1_close_to_demand_low_zw":(float(hb.close)-float(r.demand_low))/width,
        "h1_hh":bool(hh),
        "h1_hl":bool(hl),
        "h1_hh_hl":bool(hh and hl),
        "h1_bearish_ll_lh":bool(ll and lh),
        "most_recent_h1_pivot_type":last_type,
    }

def label_outcomes(raw5,r,end):
    anchor=float(r.touch_close)
    floor=float(r.demand_low)
    risk=anchor-floor
    if not (risk>0):
        return None

    p24=s39.measure_path(raw5,r.first_touch_ts,anchor,floor,end,hours=24)
    mfe=float(p24["mfe_r"]) if np.isfinite(p24["mfe_r"]) else 0.0
    ge1=bool(mfe>=1.0)
    ge15=bool(mfe>=1.5)

    p1=s39.threshold_probe(raw5,r.first_touch_ts,anchor,floor,end,1.0,hours=24)
    p15=s39.threshold_probe(raw5,r.first_touch_ts,anchor,floor,end,1.5,hours=24)
    return {
        "anchor_price":anchor,
        "event_risk":risk,
        "mfe_24h_r":mfe,
        "GE1R":ge1,
        "GE1_5R":ge15,
        "CLEAN1R":bool(p1["clean"]),
        "CLEAN1_5R":bool(p15["clean"]),
    }

def robust_effect(q,feature,label,dev_iqr):
    pos=pd.to_numeric(q.loc[q[label],feature],errors="coerce").dropna()
    neg=pd.to_numeric(q.loc[~q[label],feature],errors="coerce").dropna()
    if not len(pos) or not len(neg) or not np.isfinite(dev_iqr) or dev_iqr<=0:
        return np.nan,np.nan,np.nan
    mp=float(pos.median()); mn=float(neg.median())
    return mp,mn,float((mp-mn)/dev_iqr)

def binary_effect(q,feature,label):
    pos=q.loc[q[label],feature].astype(float)
    neg=q.loc[~q[label],feature].astype(float)
    if not len(pos) or not len(neg):
        return np.nan,np.nan,np.nan
    mp=float(pos.mean()); mn=float(neg.mean())
    return mp,mn,mp-mn

def band_name(x,c1,c2,c3):
    if not np.isfinite(x): return "NA"
    if x<=c1:return "Q1"
    if x<=c2:return "Q2"
    if x<=c3:return "Q3"
    return "Q4"

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    s1.START=START; s1.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end].copy()
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end].copy()
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    fam["period"]=[period(x) for x in fam.first_touch_ts]
    fam["year"]=pd.to_datetime(fam.first_touch_ts,utc=True).dt.year

    if int((fam.period=="DEV").sum())!=788 or int((fam.period=="REF").sum())!=463:
        raise RuntimeError("B39-S1 parent parity drift")

    h1_hi,h1_lo=s1.pivots_df(h1)

    rows=[]
    for r in fam.itertuples(index=False):
        out=label_outcomes(raw5,r,end)
        if out is None:
            continue

        pf=pullback_features(m15,r)
        if pf is None:
            continue

        width=float(r.demand_width)
        preclose=float(pf["pre_touch_close"])
        hc=h1_context(h1,h1_hi,h1_lo,pf["pre_touch_ts"],preclose,width,r)
        if hc is None:
            continue

        # Activation/BOS bar is completed at activation_ts and always predates first touch.
        if pd.Timestamp(r.activation_ts) not in h1.index:
            raise RuntimeError(f"activation bar missing {r.zone_id}")
        bb=h1.loc[pd.Timestamp(r.activation_ts)]

        rec={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "activation_ts":r.activation_ts,"first_touch_ts":r.first_touch_ts,
            "expansion_pivot_ts":r.expansion_pivot_ts,
            "demand_width_pct":float(r.demand_width)/float(r.demand_high),
            "bos_break_pct":(float(r.bos_close)-float(r.broken_level))/float(r.broken_level),
            "bos_body_zw":(float(bb.close)-float(bb.open))/width,
            "bos_range_zw":(float(bb.high)-float(bb.low))/width,
            "bos_close_location":close_location(bb),
            "zone_age_hours":float((pd.Timestamp(r.first_touch_ts)-pd.Timestamp(r.activation_ts))/pd.Timedelta(hours=1)),
            "origin_to_activation_hours":float((pd.Timestamp(r.activation_ts)-pd.Timestamp(r.origin_ts))/pd.Timedelta(hours=1)),
            "broken_swing_to_activation_hours":float((pd.Timestamp(r.activation_ts)-pd.Timestamp(r.broken_swing_ts))/pd.Timedelta(hours=1)),
            "expansion_room_zw":(float(r.expansion_high)-preclose)/width,
            "has_lower_high":bool(r.has_lower_high),
            "has_lower_low":bool(r.has_lower_low),
            **pf,**hc,**out,
        }
        rec["pullback_state"]=(
            "LH_LL" if rec["has_lower_high"] and rec["has_lower_low"]
            else "LH_ONLY" if rec["has_lower_high"]
            else "LL_ONLY" if rec["has_lower_low"]
            else "NONE"
        )
        rec["h1_state"]=(
            "HH_HL" if rec["h1_hh_hl"]
            else "LL_LH" if rec["h1_bearish_ll_lh"]
            else "MIXED"
        )
        rows.append(rec)

    L=pd.DataFrame(rows)

    # Exact normalizable parity from B39-S1.
    if len(L)!=1248 or int((L.period=="DEV").sum())!=785 or int((L.period=="REF").sum())!=463:
        raise RuntimeError(f"normalizable parity drift total={len(L)} DEV={sum(L.period=='DEV')} REF={sum(L.period=='REF')}")

    expected={
        ("DEV","GE1R"):375,("REF","GE1R"):241,
        ("DEV","GE1_5R"):284,("REF","GE1_5R"):193,
        ("DEV","CLEAN1R"):237,("REF","CLEAN1R"):170,
        ("DEV","CLEAN1_5R"):170,("REF","CLEAN1_5R"):135,
    }
    for (per,lab),n in expected.items():
        got=int(L.loc[L.period==per,lab].sum())
        if got!=n:
            raise RuntimeError(f"label parity drift {per} {lab}: got={got} expected={n}")

    # Comparison: DEV scale frozen and reused for REF effect normalization.
    comp=[]
    for lab in LABELS:
        dev=L[L.period=="DEV"]
        for feature in NUM_FEATURES:
            x=pd.to_numeric(dev[feature],errors="coerce").dropna()
            dev_iqr=float(x.quantile(.75)-x.quantile(.25)) if len(x) else np.nan
            vals={}
            for per in ["DEV","REF"]:
                q=L[L.period==per]
                mp,mn,e=robust_effect(q,feature,lab,dev_iqr)
                vals[per]=(mp,mn,e,int(pd.to_numeric(q[feature],errors="coerce").notna().sum()))
            de=vals["DEV"][2]; re=vals["REF"][2]
            consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            score=min(abs(de),abs(re)) if consistent else 0.0
            comp.append({
                "label":lab,"feature":feature,"feature_type":"NUMERIC","dev_iqr":dev_iqr,
                "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":consistent,"robust_score":score,
            })

        for feature in BIN_FEATURES:
            vals={}
            for per in ["DEV","REF"]:
                q=L[L.period==per]
                mp,mn,e=binary_effect(q,feature,lab)
                vals[per]=(mp,mn,e,len(q))
            de=vals["DEV"][2]; re=vals["REF"][2]
            consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            score=min(abs(de),abs(re)) if consistent else 0.0
            comp.append({
                "label":lab,"feature":feature,"feature_type":"BINARY","dev_iqr":np.nan,
                "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":consistent,"robust_score":score,
            })
    FC=pd.DataFrame(comp)
    RANK=FC.sort_values(["label","direction_consistent","robust_score"],ascending=[True,False,False]).copy()

    # DEV quartile cuts, unchanged REF audit.
    cuts=[]; bands=[]
    dev=L[L.period=="DEV"]
    for lab in LABELS:
        for feature in NUM_FEATURES:
            x=pd.to_numeric(dev[feature],errors="coerce").dropna()
            if len(x)<40:
                continue
            c1=float(x.quantile(.25)); c2=float(x.quantile(.50)); c3=float(x.quantile(.75))
            cuts.append({"label":lab,"feature":feature,"q25":c1,"q50":c2,"q75":c3,"dev_n":len(x)})
            for per in ["DEV","REF"]:
                q=L[L.period==per].copy()
                q["_x"]=pd.to_numeric(q[feature],errors="coerce")
                q=q[np.isfinite(q._x)].copy()
                q["band"]=[band_name(float(v),c1,c2,c3) for v in q._x]
                for band in ["Q1","Q2","Q3","Q4"]:
                    z=q[q.band==band]
                    if not len(z): continue
                    succ=int(z[lab].sum())
                    bands.append({
                        "label":lab,"feature":feature,"period":per,"band":band,
                        "n":len(z),"success":succ,"success_rate":succ/len(z),
                    })
    CUT=pd.DataFrame(cuts)
    BA=pd.DataFrame(bands)

    # Structural state audit.
    states=[]
    for lab in LABELS:
        for per in ["DEV","REF"]:
            q=L[L.period==per]
            for col in ["pullback_state","h1_state","most_recent_h1_pivot_type"]:
                for state,z in q.groupby(col,dropna=False):
                    states.append({
                        "label":lab,"period":per,"state_family":col,"state":str(state),
                        "n":len(z),"success":int(z[lab].sum()),"success_rate":float(z[lab].mean()),
                    })
    ST=pd.DataFrame(states)

    # Year audit for top robust primary features only, frozen without selecting by year.
    top_primary=RANK[(RANK.label=="GE1R")&(RANK.direction_consistent)&(RANK.feature_type=="NUMERIC")].head(10).feature.tolist()
    year_rows=[]
    for feature in top_primary:
        cutrow=CUT[(CUT.label=="GE1R")&(CUT.feature==feature)]
        if cutrow.empty: continue
        cr=cutrow.iloc[0]
        for y in [2022,2023,2024,2025,2026]:
            q=L[L.year==y].copy()
            q["_x"]=pd.to_numeric(q[feature],errors="coerce")
            q=q[np.isfinite(q._x)].copy()
            q["band"]=[band_name(float(v),cr.q25,cr.q50,cr.q75) for v in q._x]
            for band in ["Q1","Q2","Q3","Q4"]:
                z=q[q.band==band]
                if len(z):
                    year_rows.append({
                        "feature":feature,"year":y,"band":band,"n":len(z),
                        "ge1r":int(z.GE1R.sum()),"ge1r_rate":float(z.GE1R.mean())
                    })
    YA=pd.DataFrame(year_rows)

    # Label baseline.
    base=[]
    for per in ["DEV","REF"]:
        q=L[L.period==per]
        for lab in LABELS:
            base.append({
                "period":per,"label":lab,"n":len(q),"success":int(q[lab].sum()),
                "base_rate":float(q[lab].mean())
            })
    BS=pd.DataFrame(base)

    L.to_csv(ROOT/f"{PFX}_FeatureLedger.csv.gz",index=False,compression="gzip")
    BS.to_csv(ROOT/f"{PFX}_LabelBaseline.csv",index=False)
    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    RANK.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    BA.to_csv(ROOT/f"{PFX}_BandAudit.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StateAudit.csv",index=False)
    YA.to_csv(ROOT/f"{PFX}_TopFeatureByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B39_S1_REAL_EXPANSION_UNIVERSE\nRAW_END={end.isoformat()}\n"
        "DEV_NORMALIZABLE=785\nREF_NORMALIZABLE=463\n"
        "STRICT_FEATURE_CUTOFF=FIRST_TOUCH_MINUS_15M\nTOUCH_BAR_FEATURES=FORBIDDEN\n"
        "PRIMARY_LABEL=GE1R\nSECONDARY_LABELS=GE1_5R,CLEAN1R,CLEAN1_5R\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S2 — Backward Pre-Touch Structural Anatomy","",
        "**No detector is selected in S2. Touch-bar information is forbidden as a feature.**","",
        "## Frozen label baselines","",
        "| Period | Label | N | Success | Base rate |",
        "|---|---|---:|---:|---:|"
    ]
    for r in BS.itertuples(index=False):
        lines.append(f"| {r.period} | {r.label} | {r.n} | {r.success} | {fmt_pct(r.base_rate)} |")

    lines += ["","## Strongest directionally consistent pre-touch features — GE1R","",
        "| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in RANK[(RANK.label=="GE1R")&RANK.direction_consistent].head(15).itertuples(index=False):
        lines.append(
            f"| {r.feature} | {r.feature_type} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
            f"{fmt_num(r.dev_pos)}/{fmt_num(r.dev_neg)} | {fmt_num(r.ref_pos)}/{fmt_num(r.ref_neg)} |"
        )

    lines += ["","## Strongest directionally consistent pre-touch features — CLEAN1R","",
        "| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in RANK[(RANK.label=="CLEAN1R")&RANK.direction_consistent].head(12).itertuples(index=False):
        lines.append(
            f"| {r.feature} | {r.feature_type} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
            f"{fmt_num(r.dev_pos)}/{fmt_num(r.dev_neg)} | {fmt_num(r.ref_pos)}/{fmt_num(r.ref_neg)} |"
        )

    lines += ["","## Structural-state base rates — GE1R","",
        "| Period | Family | State | N | GE1R | Rate |",
        "|---|---|---|---:|---:|---:|"
    ]
    for r in ST[ST.label=="GE1R"].itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.state_family} | {r.state} | {r.n} | {r.success} | {fmt_pct(r.success_rate)} |"
        )

    lines += ["","## Interpretation boundary",
        "S2 identifies robust pre-touch anatomy only.",
        "No scalar cut, quartile band, or state is promoted to a detector here.",
        "B39-S3 may preregister a small candidate detector set only from feature families whose separation is directionally consistent in DEV and REF and whose event retention remains useful."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S2_BACKWARD_PRETOUCH_ANATOMY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
