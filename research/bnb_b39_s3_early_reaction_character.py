#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s1_real_expansion_universe as s39
import bnb_b39_s2_backward_pretouch_anatomy as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S3_EARLY_REACTION_CHARACTER"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
DECISIONS=["TOUCH_CLOSE","PLUS5_CLOSE","PLUS15_CLOSE"]
LABELS=["GE1R","GE1_5R","CLEAN1R","CLEAN1_5R"]

INHERITED_NUM=[
    "zone_age_hours","bos_body_zw",
    "pullback_close_slope_zw_per_bar","compression_last3_vs_earlier"
]
TOUCH_NUM=[
    "touch_penetration_zw","touch_floor_sweep_depth_zw",
    "touch_close_vs_demand_high_zw","touch_close_vs_demand_low_zw",
    "touch_recovery_from_low_zw","touch_lower_wick_zw","touch_upper_wick_zw",
    "touch_body_zw","touch_range_zw","touch_close_location"
]
PLUS5_NUM=[
    "p5_close_r","p5_high_r","p5_low_r","p5_body_r","p5_range_r",
    "p5_recovery_from_low_r","p5_close_location","p5_close_vs_demand_high_zw"
]
PLUS15_NUM=[
    "p15_close_r","p15_high_r","p15_low_r","p15_body_r","p15_range_r",
    "p15_close_location","p15_green_rate","p15_close_slope_r_per_bar",
    "p15_path_efficiency","p15_min_close_r","p15_max_close_r",
    "p15_close_above_anchor_rate","p15_close_above_demand_high_rate"
]

TOUCH_BIN=["TOUCH_RECLAIM_HIGH","TOUCH_FLOOR_SWEEP_RECLAIM","TOUCH_BULLISH"]
PLUS5_BIN=[
    "CLOSE5_ABOVE_ANCHOR","CLOSE5_ABOVE_DEMAND_HIGH","CLOSE5_BREAK_TOUCH_HIGH",
    "CLOSE5_BULLISH","LOW5_HOLDS_TOUCH_LOW"
]
PLUS15_BIN=[
    "CLOSE15_ABOVE_ANCHOR","CLOSE15_ABOVE_DEMAND_HIGH","CLOSE15_BREAK_TOUCH_HIGH",
    "ALL3_CLOSES_ABOVE_ANCHOR","ALL3_CLOSES_ABOVE_DEMAND_HIGH",
    "RECLAIM_HIGH_THEN_HOLD","BREAK_TOUCH_HIGH_WITHIN15"
]

NUM_BY_DECISION={
    "TOUCH_CLOSE":INHERITED_NUM+TOUCH_NUM,
    "PLUS5_CLOSE":INHERITED_NUM+TOUCH_NUM+PLUS5_NUM,
    "PLUS15_CLOSE":INHERITED_NUM+TOUCH_NUM+PLUS5_NUM+PLUS15_NUM,
}
BIN_BY_DECISION={
    "TOUCH_CLOSE":TOUCH_BIN,
    "PLUS5_CLOSE":TOUCH_BIN+PLUS5_BIN,
    "PLUS15_CLOSE":TOUCH_BIN+PLUS5_BIN+PLUS15_BIN,
}

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def safe_div(a,b):
    return float(a/b) if np.isfinite(a) and np.isfinite(b) and b!=0 else np.nan

def close_location(o,h,l,c):
    rng=float(h-l)
    return float((c-l)/rng) if rng>0 else np.nan

def decision_scan(raw5,anchor_ts,anchor,floor,n_bars):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(anchor_ts),side="right"))
    if i0+n_bars>len(raw5):
        return "DECISION_CENSORED",pd.NaT,[]
    bars=raw5.iloc[i0:i0+n_bars].copy()
    target=anchor+(anchor-floor)
    for j,b in enumerate(bars.itertuples()):
        ht=float(b.high)>=target
        hf=float(b.low)<=floor
        ts=idx[i0+j]
        if ht and hf:
            return "AMBIGUOUS_RESOLUTION",ts,bars.iloc[:j+1]
        if ht:
            return "TOO_FAST_WIN",ts,bars.iloc[:j+1]
        if hf:
            return "TOO_FAST_FAIL",ts,bars.iloc[:j+1]
    return "ELIGIBLE",idx[i0+n_bars-1],bars

def touch_features(r):
    width=float(r.demand_width)
    o=float(r.touch_open); h=float(r.touch_high); l=float(r.touch_low); c=float(r.touch_close)
    dh=float(r.demand_high); dl=float(r.demand_low)
    return {
        "touch_penetration_zw":(dh-l)/width,
        "touch_floor_sweep_depth_zw":max(0.0,(dl-l)/width),
        "touch_close_vs_demand_high_zw":(c-dh)/width,
        "touch_close_vs_demand_low_zw":(c-dl)/width,
        "touch_recovery_from_low_zw":(c-l)/width,
        "touch_lower_wick_zw":(min(o,c)-l)/width,
        "touch_upper_wick_zw":(h-max(o,c))/width,
        "touch_body_zw":(c-o)/width,
        "touch_range_zw":(h-l)/width,
        "touch_close_location":close_location(o,h,l,c),
        "TOUCH_RECLAIM_HIGH":bool(c>=dh),
        "TOUCH_FLOOR_SWEEP_RECLAIM":bool(l<dl and c>=dl),
        "TOUCH_BULLISH":bool(c>o),
    }

def plus5_features(bars,r,anchor,risk):
    b=bars.iloc[0]
    width=float(r.demand_width)
    return {
        "p5_close_r":(float(b.close)-anchor)/risk,
        "p5_high_r":(float(b.high)-anchor)/risk,
        "p5_low_r":(float(b.low)-anchor)/risk,
        "p5_body_r":(float(b.close)-float(b.open))/risk,
        "p5_range_r":(float(b.high)-float(b.low))/risk,
        "p5_recovery_from_low_r":(float(b.close)-float(b.low))/risk,
        "p5_close_location":close_location(float(b.open),float(b.high),float(b.low),float(b.close)),
        "p5_close_vs_demand_high_zw":(float(b.close)-float(r.demand_high))/width,
        "CLOSE5_ABOVE_ANCHOR":bool(float(b.close)>=anchor),
        "CLOSE5_ABOVE_DEMAND_HIGH":bool(float(b.close)>=float(r.demand_high)),
        "CLOSE5_BREAK_TOUCH_HIGH":bool(float(b.close)>=float(r.touch_high)),
        "CLOSE5_BULLISH":bool(float(b.close)>float(b.open)),
        "LOW5_HOLDS_TOUCH_LOW":bool(float(b.low)>=float(r.touch_low)),
    }

def plus15_features(bars,r,anchor,risk):
    q=bars.iloc[:3]
    o=float(q.open.iloc[0]); h=float(q.high.max()); l=float(q.low.min()); c=float(q.close.iloc[-1])
    closes=q.close.to_numpy(float)
    x=np.arange(3,dtype=float)
    slope=float(np.polyfit(x,closes,1)[0])/risk
    denom=float(np.abs(np.diff(closes)).sum())
    eff=float((closes[-1]-closes[0])/denom) if denom>0 else np.nan
    dh=float(r.demand_high); th=float(r.touch_high)
    above_a=(q.close>=anchor).to_numpy(bool)
    above_h=(q.close>=dh).to_numpy(bool)
    reclaim_hold=False
    # Must reclaim by bar 1 or 2 and all subsequent completed closes hold the level.
    for j in [0,1]:
        if bool(above_h[j]) and bool(np.all(above_h[j:])):
            reclaim_hold=True
            break
    return {
        "p15_close_r":(c-anchor)/risk,
        "p15_high_r":(h-anchor)/risk,
        "p15_low_r":(l-anchor)/risk,
        "p15_body_r":(c-o)/risk,
        "p15_range_r":(h-l)/risk,
        "p15_close_location":close_location(o,h,l,c),
        "p15_green_rate":float((q.close>q.open).mean()),
        "p15_close_slope_r_per_bar":slope,
        "p15_path_efficiency":eff,
        "p15_min_close_r":float((q.close.min()-anchor)/risk),
        "p15_max_close_r":float((q.close.max()-anchor)/risk),
        "p15_close_above_anchor_rate":float(above_a.mean()),
        "p15_close_above_demand_high_rate":float(above_h.mean()),
        "CLOSE15_ABOVE_ANCHOR":bool(c>=anchor),
        "CLOSE15_ABOVE_DEMAND_HIGH":bool(c>=dh),
        "CLOSE15_BREAK_TOUCH_HIGH":bool(c>=th),
        "ALL3_CLOSES_ABOVE_ANCHOR":bool(np.all(above_a)),
        "ALL3_CLOSES_ABOVE_DEMAND_HIGH":bool(np.all(above_h)),
        "RECLAIM_HIGH_THEN_HOLD":bool(reclaim_hold),
        "BREAK_TOUCH_HIGH_WITHIN15":bool(np.any(q.close.to_numpy(float)>=th)),
    }

def inherited_features(m15,h1,r):
    pf=s2.pullback_features(m15,r)
    if pf is None:
        return None
    width=float(r.demand_width)
    bb=h1.loc[pd.Timestamp(r.activation_ts)]
    return {
        "zone_age_hours":float((pd.Timestamp(r.first_touch_ts)-pd.Timestamp(r.activation_ts))/pd.Timedelta(hours=1)),
        "bos_body_zw":(float(bb.close)-float(bb.open))/width,
        "pullback_close_slope_zw_per_bar":pf["pullback_close_slope_zw_per_bar"],
        "compression_last3_vs_earlier":pf["compression_last3_vs_earlier"],
    }

def label_outcomes(raw5,r,end):
    z=s2.label_outcomes(raw5,r,end)
    if z is None:
        return None
    return {k:z[k] for k in ["GE1R","GE1_5R","CLEAN1R","CLEAN1_5R","mfe_24h_r","anchor_price","event_risk"]}

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
    if diag["coverage"]<.995: raise RuntimeError(diag)
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
        raise RuntimeError("parent parity drift")

    rows=[]
    for r in fam.itertuples(index=False):
        out=label_outcomes(raw5,r,end)
        if out is None:
            continue
        inh=inherited_features(m15,h1,r)
        if inh is None:
            continue
        tf=touch_features(r)
        anchor=float(out["anchor_price"]); risk=float(out["event_risk"])

        # TOUCH_CLOSE — all frozen normalizable events are eligible.
        base={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "first_touch_ts":r.first_touch_ts,"decision":"TOUCH_CLOSE",
            "decision_status":"ELIGIBLE","decision_ts":r.first_touch_ts,
            **out,**inh,**tf
        }
        rows.append(base)

        # PLUS5_CLOSE
        st5,dt5,b5=decision_scan(raw5,r.first_touch_ts,anchor,float(r.demand_low),1)
        rec5={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "first_touch_ts":r.first_touch_ts,"decision":"PLUS5_CLOSE",
            "decision_status":st5,"decision_ts":dt5,
            **out,**inh,**tf
        }
        if len(b5)>=1:
            rec5.update(plus5_features(b5,r,anchor,risk))
        rows.append(rec5)

        # PLUS15_CLOSE
        st15,dt15,b15=decision_scan(raw5,r.first_touch_ts,anchor,float(r.demand_low),3)
        rec15={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "first_touch_ts":r.first_touch_ts,"decision":"PLUS15_CLOSE",
            "decision_status":st15,"decision_ts":dt15,
            **out,**inh,**tf
        }
        if len(b15)>=1:
            rec15.update(plus5_features(b15.iloc[:1],r,anchor,risk))
        if st15=="ELIGIBLE" and len(b15)>=3:
            rec15.update(plus15_features(b15,r,anchor,risk))
        elif len(b15)>=3:
            # Diagnostic values exist at the decision bar but are not used in scoring
            # once the event has already resolved.
            rec15.update(plus15_features(b15,r,anchor,risk))
        rows.append(rec15)

    L=pd.DataFrame(rows)

    # Exact frozen label parity at TOUCH_CLOSE.
    T=L[L.decision=="TOUCH_CLOSE"]
    if len(T)!=1248 or int((T.period=="DEV").sum())!=785 or int((T.period=="REF").sum())!=463:
        raise RuntimeError(f"touch parity drift total={len(T)} DEV={sum(T.period=='DEV')} REF={sum(T.period=='REF')}")
    expected={
        ("DEV","GE1R"):375,("REF","GE1R"):241,
        ("DEV","GE1_5R"):284,("REF","GE1_5R"):193,
        ("DEV","CLEAN1R"):237,("REF","CLEAN1R"):170,
        ("DEV","CLEAN1_5R"):170,("REF","CLEAN1_5R"):135,
    }
    for (per,lab),n in expected.items():
        got=int(T.loc[T.period==per,lab].sum())
        if got!=n: raise RuntimeError(f"label parity {per} {lab} got={got} expected={n}")

    # Decision census and residual base rates.
    census=[]
    for dec in DECISIONS:
        for per in ["DEV","REF"]:
            q=L[(L.decision==dec)&(L.period==per)]
            e=q[q.decision_status=="ELIGIBLE"]
            row={
                "decision":dec,"period":per,"n":len(q),"eligible":len(e),
                "too_fast_win":int((q.decision_status=="TOO_FAST_WIN").sum()),
                "too_fast_fail":int((q.decision_status=="TOO_FAST_FAIL").sum()),
                "ambiguous_resolution":int((q.decision_status=="AMBIGUOUS_RESOLUTION").sum()),
                "decision_censored":int((q.decision_status=="DECISION_CENSORED").sum()),
            }
            for lab in LABELS:
                row[f"{lab}_success"]=int(e[lab].sum())
                row[f"{lab}_rate"]=float(e[lab].mean()) if len(e) else np.nan
            census.append(row)
    C=pd.DataFrame(census)

    # Feature comparison by causal decision cohort.
    comp=[]
    for dec in DECISIONS:
        ddev=L[(L.decision==dec)&(L.period=="DEV")&(L.decision_status=="ELIGIBLE")]
        for lab in LABELS:
            for feature in NUM_BY_DECISION[dec]:
                x=pd.to_numeric(ddev[feature],errors="coerce").dropna() if feature in ddev else pd.Series(dtype=float)
                dev_iqr=float(x.quantile(.75)-x.quantile(.25)) if len(x) else np.nan
                vals={}
                for per in ["DEV","REF"]:
                    q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")]
                    if feature not in q:
                        vals[per]=(np.nan,np.nan,np.nan,0); continue
                    mp,mn,e=robust_effect(q,feature,lab,dev_iqr)
                    vals[per]=(mp,mn,e,int(pd.to_numeric(q[feature],errors="coerce").notna().sum()))
                de=vals["DEV"][2]; re=vals["REF"][2]
                cons=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
                comp.append({
                    "decision":dec,"label":lab,"feature":feature,"feature_type":"NUMERIC",
                    "dev_iqr":dev_iqr,
                    "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                    "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                    "direction_consistent":cons,
                    "robust_score":min(abs(de),abs(re)) if cons else 0.0,
                })
            for feature in BIN_BY_DECISION[dec]:
                vals={}
                for per in ["DEV","REF"]:
                    q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")]
                    if feature not in q:
                        vals[per]=(np.nan,np.nan,np.nan,0); continue
                    z=q[q[feature].notna()]
                    mp,mn,e=binary_effect(z,feature,lab)
                    vals[per]=(mp,mn,e,len(z))
                de=vals["DEV"][2]; re=vals["REF"][2]
                cons=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
                comp.append({
                    "decision":dec,"label":lab,"feature":feature,"feature_type":"BINARY",
                    "dev_iqr":np.nan,
                    "dev_pos":vals["DEV"][0],"dev_neg":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                    "ref_pos":vals["REF"][0],"ref_neg":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                    "direction_consistent":cons,
                    "robust_score":min(abs(de),abs(re)) if cons else 0.0,
                })
    FC=pd.DataFrame(comp)
    RANK=FC.sort_values(["decision","label","direction_consistent","robust_score"],
                        ascending=[True,True,False,False]).copy()

    # DEV-only quartiles applied unchanged to REF.
    cuts=[]; bands=[]
    for dec in DECISIONS:
        ddev=L[(L.decision==dec)&(L.period=="DEV")&(L.decision_status=="ELIGIBLE")]
        for feature in NUM_BY_DECISION[dec]:
            if feature not in ddev: continue
            x=pd.to_numeric(ddev[feature],errors="coerce").dropna()
            if len(x)<40: continue
            c1=float(x.quantile(.25)); c2=float(x.quantile(.50)); c3=float(x.quantile(.75))
            cuts.append({"decision":dec,"feature":feature,"q25":c1,"q50":c2,"q75":c3,"dev_n":len(x)})
            for lab in LABELS:
                for per in ["DEV","REF"]:
                    q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")].copy()
                    q["_x"]=pd.to_numeric(q[feature],errors="coerce")
                    q=q[np.isfinite(q._x)].copy()
                    q["band"]=[band_name(float(v),c1,c2,c3) for v in q._x]
                    for band in ["Q1","Q2","Q3","Q4"]:
                        z=q[q.band==band]
                        if len(z):
                            bands.append({
                                "decision":dec,"label":lab,"feature":feature,"period":per,"band":band,
                                "n":len(z),"success":int(z[lab].sum()),"success_rate":float(z[lab].mean())
                            })
    CUT=pd.DataFrame(cuts)
    BA=pd.DataFrame(bands)

    # Binary structural-state audit.
    states=[]
    for dec in DECISIONS:
        for feature in BIN_BY_DECISION[dec]:
            for lab in LABELS:
                for per in ["DEV","REF"]:
                    q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")]
                    if feature not in q: continue
                    q=q[q[feature].notna()]
                    for state in [False,True]:
                        z=q[q[feature].astype(bool)==state]
                        if len(z):
                            states.append({
                                "decision":dec,"label":lab,"feature":feature,"period":per,
                                "state":state,"n":len(z),"success":int(z[lab].sum()),
                                "success_rate":float(z[lab].mean())
                            })
    ST=pd.DataFrame(states)

    # Year audit for top primary numeric + binary feature per decision, selected only by DEV/REF consistency.
    yr=[]
    for dec in DECISIONS:
        top=RANK[(RANK.decision==dec)&(RANK.label=="GE1R")&RANK.direction_consistent].head(6)
        for rr in top.itertuples(index=False):
            if rr.feature_type=="NUMERIC":
                cr=CUT[(CUT.decision==dec)&(CUT.feature==rr.feature)]
                if cr.empty: continue
                cr=cr.iloc[0]
                for y in [2022,2023,2024,2025,2026]:
                    q=L[(L.decision==dec)&(L.year==y)&(L.decision_status=="ELIGIBLE")].copy()
                    if rr.feature not in q: continue
                    q["_x"]=pd.to_numeric(q[rr.feature],errors="coerce")
                    q=q[np.isfinite(q._x)].copy()
                    q["state"]=[band_name(float(v),cr.q25,cr.q50,cr.q75) for v in q._x]
                    for state,z in q.groupby("state"):
                        yr.append({
                            "decision":dec,"feature":rr.feature,"feature_type":"NUMERIC",
                            "year":y,"state":state,"n":len(z),"ge1r":int(z.GE1R.sum()),
                            "ge1r_rate":float(z.GE1R.mean())
                        })
            else:
                for y in [2022,2023,2024,2025,2026]:
                    q=L[(L.decision==dec)&(L.year==y)&(L.decision_status=="ELIGIBLE")]
                    if rr.feature not in q: continue
                    q=q[q[rr.feature].notna()]
                    for state in [False,True]:
                        z=q[q[rr.feature].astype(bool)==state]
                        if len(z):
                            yr.append({
                                "decision":dec,"feature":rr.feature,"feature_type":"BINARY",
                                "year":y,"state":str(state),"n":len(z),"ge1r":int(z.GE1R.sum()),
                                "ge1r_rate":float(z.GE1R.mean())
                            })
    YA=pd.DataFrame(yr)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_DecisionCensus.csv",index=False)
    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    RANK.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    BA.to_csv(ROOT/f"{PFX}_BandAudit.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StateAudit.csv",index=False)
    YA.to_csv(ROOT/f"{PFX}_TopFeatureByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B39_S1_REAL_EXPANSION_UNIVERSE\nRAW_END={end.isoformat()}\n"
        "DEV_NORMALIZABLE=785\nREF_NORMALIZABLE=463\n"
        "DECISIONS=TOUCH_CLOSE,PLUS5_CLOSE,PLUS15_CLOSE\n"
        "TOO_FAST_GATE=PLUS5_AND_PLUS15_EXCLUDE_GE1R_OR_INVALIDATION_AT_OR_BEFORE_DECISION\n"
        "PRIMARY_LABEL=GE1R\nSECONDARY=GE1_5R,CLEAN1R,CLEAN1_5R\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S3 — Early Reaction Character Discovery","",
        "**Discovery only. No detector/entry/SL/TP is promoted.**","",
        "## Decision-point census","",
        "| Decision | Period | N | Eligible | Too-fast WIN | Too-fast FAIL | Ambig | GE1R residual | GE1.5R residual | CLEAN1R residual |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.decision} | {r.period} | {r.n} | {r.eligible} | {r.too_fast_win} | {r.too_fast_fail} | "
            f"{r.ambiguous_resolution} | {r.GE1R_success}/{r.eligible} ({fmt_pct(r.GE1R_rate)}) | "
            f"{r.GE1_5R_success}/{r.eligible} ({fmt_pct(r.GE1_5R_rate)}) | "
            f"{r.CLEAN1R_success}/{r.eligible} ({fmt_pct(r.CLEAN1R_rate)}) |"
        )

    for dec in DECISIONS:
        lines += ["",f"## {dec} — strongest consistent GE1R features","",
            "| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |",
            "|---|---|---:|---:|---:|---:|"
        ]
        q=RANK[(RANK.decision==dec)&(RANK.label=="GE1R")&RANK.direction_consistent].head(12)
        for r in q.itertuples(index=False):
            lines.append(
                f"| {r.feature} | {r.feature_type} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
                f"{fmt_num(r.dev_pos)}/{fmt_num(r.dev_neg)} | {fmt_num(r.ref_pos)}/{fmt_num(r.ref_neg)} |"
            )

    lines += ["","## Interpretation boundary",
        "S3 measures whether reaction information available at touch, +5m, or +15m materially enriches real expansion.",
        "Too-fast outcomes are never credited to a later decision point.",
        "No threshold or feature combination is promoted here. Candidate detector construction requires a separate preregistered stage."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S3_EARLY_REACTION_CHARACTER_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
