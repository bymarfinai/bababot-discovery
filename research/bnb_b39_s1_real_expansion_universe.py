#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S1_REAL_EXPANSION_UNIVERSE"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
HORIZONS=[4,12,24]
THRESHOLDS=[0.50,0.75,1.00,1.50,2.00]
CLEAN_THRESHOLDS=[0.75,1.00,1.50]
ADVERSE_CLEAN_R=-0.50

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def first_idx(arr, cond):
    z=np.flatnonzero(cond(arr))
    return int(z[0]) if len(z) else None

def path_bounds(raw5, anchor_ts, floor, end, hours=None):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(anchor_ts),side="right"))
    hard_end=end if hours is None else min(end,pd.Timestamp(anchor_ts)+pd.Timedelta(hours=hours))
    i_h=int(idx.searchsorted(hard_end,side="right"))

    if i0>=len(idx) or i_h<=i0:
        return i0,i0,None,False

    lows=raw5.low.to_numpy(float,copy=False)[i0:i_h]
    z=np.flatnonzero(lows<=floor)
    inv=(i0+int(z[0])) if len(z) else None

    # Exclude invalidation bar because target/floor ordering inside the 5m bar is unknown.
    i1=min(i_h,inv) if inv is not None else i_h

    horizon_complete=True
    if hours is not None:
        desired=pd.Timestamp(anchor_ts)+pd.Timedelta(hours=hours)
        # If invalidation happens first, path is terminal and fully observed.
        if inv is None and end<desired:
            horizon_complete=False
    return i0,i1,inv,horizon_complete

def measure_path(raw5,anchor_ts,anchor,floor,end,hours=None):
    risk=anchor-floor
    i0,i1,inv,complete=path_bounds(raw5,anchor_ts,floor,end,hours)
    idx=raw5.index
    if risk<=0 or i1<=i0:
        return {
            "mfe_r":np.nan,"mae_r":np.nan,"peak_ts":pd.NaT,"peak_hours":np.nan,
            "giveback_r":np.nan,"bars":0,"invalidation_ts":idx[inv] if inv is not None else pd.NaT,
            "horizon_complete":complete,
        }
    q=raw5.iloc[i0:i1]
    hi=q.high.to_numpy(float,copy=False); lo=q.low.to_numpy(float,copy=False)
    j=int(np.argmax(hi))
    peak=float(hi[j]); trough=float(np.min(lo)); peak_abs=i0+j
    peak_ts=idx[peak_abs]
    after=raw5.iloc[peak_abs:i1]
    post_min=float(after.low.min()) if len(after) else peak
    return {
        "mfe_r":float((peak-anchor)/risk),
        "mae_r":float((trough-anchor)/risk),
        "peak_ts":peak_ts,
        "peak_hours":float((peak_ts-pd.Timestamp(anchor_ts))/pd.Timedelta(hours=1)),
        "giveback_r":float((peak-post_min)/risk),
        "bars":int(len(q)),
        "invalidation_ts":idx[inv] if inv is not None else pd.NaT,
        "horizon_complete":complete,
    }

def threshold_probe(raw5,anchor_ts,anchor,floor,end,thr,hours=24):
    risk=anchor-floor
    target=anchor+thr*risk
    adverse=anchor+ADVERSE_CLEAN_R*risk
    i0,i1,inv,complete=path_bounds(raw5,anchor_ts,floor,end,hours)
    idx=raw5.index
    if risk<=0 or i1<=i0:
        return {
            "reached":False,"touch_ts":pd.NaT,"touch_hours":np.nan,
            "mae_before_touch_r":np.nan,"clean":False,"clean_ambiguous":False,
            "horizon_complete":complete,
        }

    q=raw5.iloc[i0:i1]
    highs=q.high.to_numpy(float,copy=False); lows=q.low.to_numpy(float,copy=False)
    zt=np.flatnonzero(highs>=target)
    za=np.flatnonzero(lows<=adverse)
    ti=i0+int(zt[0]) if len(zt) else None
    ai=i0+int(za[0]) if len(za) else None

    reached=ti is not None
    touch_ts=idx[ti] if ti is not None else pd.NaT
    touch_hours=float((touch_ts-pd.Timestamp(anchor_ts))/pd.Timedelta(hours=1)) if reached else np.nan

    if reached:
        # Include target bar in MAE-to-touch; clean ordering is handled separately.
        pre=raw5.iloc[i0:ti+1]
        mae=float((float(pre.low.min())-anchor)/risk) if len(pre) else np.nan
    else:
        mae=np.nan

    amb=bool(reached and ai is not None and ai==ti)
    clean=bool(reached and (ai is None or ti<ai))
    return {
        "reached":reached,"touch_ts":touch_ts,"touch_hours":touch_hours,
        "mae_before_touch_r":mae,"clean":clean,"clean_ambiguous":amb,
        "horizon_complete":complete,
    }

def first_touch_before(raw5,anchor_ts,level,floor,end,hours=None):
    if not np.isfinite(level): return None,None,None,False
    i0,i1,inv,complete=path_bounds(raw5,anchor_ts,floor,end,hours)
    if i1<=i0:return None,None,None,complete
    a=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(a>=level)
    ti=i0+int(z[0]) if len(z) else None
    return ti,inv,i1,complete

def liquidity_probe(raw5,anchor_ts,anchor,floor,level,end):
    if not np.isfinite(level) or level<=anchor or anchor<=floor:
        return {
            "available":False,"distance_r":np.nan,"hit_before_invalid":False,
            "hit_24h":False,"touch_ts":pd.NaT,"touch_hours":np.nan,
            "horizon24_complete":False,
        }
    risk=anchor-floor
    ti,inv,_,_=first_touch_before(raw5,anchor_ts,level,floor,end,hours=None)
    hit=ti is not None
    touch_ts=raw5.index[ti] if hit else pd.NaT
    hrs=float((touch_ts-pd.Timestamp(anchor_ts))/pd.Timedelta(hours=1)) if hit else np.nan

    ti24,inv24,_,complete24=first_touch_before(raw5,anchor_ts,level,floor,end,hours=24)
    hit24=ti24 is not None

    return {
        "available":True,
        "distance_r":float((level-anchor)/risk),
        "hit_before_invalid":bool(hit),
        "hit_24h":bool(hit24),
        "touch_ts":touch_ts,
        "touch_hours":hrs,
        "horizon24_complete":bool(complete24),
    }

def class24(mfe,complete):
    if not complete or not np.isfinite(mfe): return "RIGHT_CENSORED"
    if mfe<0.50:return "FAILURE"
    if mfe<1.00:return "LOCAL_ONLY"
    if mfe<1.50:return "EXPANDER_1R"
    if mfe<2.00:return "STRONG_EXPANDER"
    return "EXTREME_EXPANDER"

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    end=raw.index.max()

    # Frozen H1-demand / 15m-touch parent family.
    s1.START=START
    s1.END=end
    h1=s1.exact_exec(raw,"1h",12)
    h1=h1[h1.index<=end].copy()
    m15=s1.exact_exec(raw,"15min",3)
    m15=m15[m15.index<=end].copy()
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    fam["period"]=[period(x) for x in fam.first_touch_ts]
    fam["year"]=pd.to_datetime(fam.first_touch_ts,utc=True).dt.year

    dev=int((fam.period=="DEV").sum()); ref=int((fam.period=="REF").sum())
    if dev!=788 or ref!=463:
        raise RuntimeError(f"parent parity drift DEV={dev} REF={ref}")

    # Confirmed H1 pivot highs; only confirm_ts <= anchor may be used.
    h1_hi,_=s1.pivots_df(h1)

    rows=[]; liqrows=[]; thrrows=[]
    for r in fam.itertuples(index=False):
        anchor=float(r.touch_close)
        floor=float(r.demand_low)
        risk=anchor-floor
        if not (risk>0):
            continue

        # causal nearest H1 high known at anchor
        qh=h1_hi[(h1_hi.confirm_ts<=r.first_touch_ts)&(h1_hi.level>anchor)]
        h1_nearest=float(qh.level.min()) if len(qh) else np.nan
        expansion=float(r.expansion_high) if np.isfinite(r.expansion_high) and float(r.expansion_high)>anchor else np.nan
        majors=[x for x in [expansion,h1_nearest] if np.isfinite(x) and x>anchor]
        major=min(majors) if majors else np.nan

        rec={
            "zone_id":r.zone_id,"period":r.period,"year":r.year,
            "activation_ts":r.activation_ts,"first_touch_ts":r.first_touch_ts,
            "anchor_ts":r.first_touch_ts,"anchor_price":anchor,
            "demand_low":floor,"demand_high":float(r.demand_high),"risk_unit":risk,
            "risk_pct":risk/anchor,
            "expansion_high":expansion,"h1_nearest":h1_nearest,"major_nearest":major,
            "pullback_bars":int(r.pullback_bars),
            "has_lower_high":bool(r.has_lower_high),"has_lower_low":bool(r.has_lower_low),
        }

        for h in HORIZONS:
            p=measure_path(raw5,r.first_touch_ts,anchor,floor,end,hours=h)
            rec[f"mfe_{h}h_r"]=p["mfe_r"]
            rec[f"mae_{h}h_r"]=p["mae_r"]
            rec[f"peak_{h}h_ts"]=p["peak_ts"]
            rec[f"peak_{h}h_hours"]=p["peak_hours"]
            rec[f"giveback_{h}h_r"]=p["giveback_r"]
            rec[f"horizon_{h}h_complete"]=p["horizon_complete"]

        full=measure_path(raw5,r.first_touch_ts,anchor,floor,end,hours=None)
        rec["mfe_pre_invalid_r"]=full["mfe_r"]
        rec["mae_pre_invalid_r"]=full["mae_r"]
        rec["peak_pre_invalid_ts"]=full["peak_ts"]
        rec["peak_pre_invalid_hours"]=full["peak_hours"]
        rec["giveback_pre_invalid_r"]=full["giveback_r"]
        rec["invalidation_ts"]=full["invalidation_ts"]
        rec["invalidated"]=pd.notna(full["invalidation_ts"])

        for th in THRESHOLDS:
            p=threshold_probe(raw5,r.first_touch_ts,anchor,floor,end,th,hours=24)
            key=f"{th:.2f}".replace(".","_")
            rec[f"reach_{key}r_24h"]=p["reached"]
            rec[f"time_{key}r_h"]=p["touch_hours"]
            rec[f"mae_before_{key}r"]=p["mae_before_touch_r"]
            if th in CLEAN_THRESHOLDS:
                rec[f"clean_{key}r"]=p["clean"]
                rec[f"clean_{key}r_ambiguous"]=p["clean_ambiguous"]
            thrrows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,"threshold_r":th,
                "reached":p["reached"],"touch_hours":p["touch_hours"],
                "mae_before_touch_r":p["mae_before_touch_r"],
                "clean":p["clean"] if th in CLEAN_THRESHOLDS else np.nan,
                "clean_ambiguous":p["clean_ambiguous"] if th in CLEAN_THRESHOLDS else np.nan,
                "horizon_complete":p["horizon_complete"],
            })

        rec["class_24h"]=class24(rec["mfe_24h_r"],bool(rec["horizon_24h_complete"]))
        rows.append(rec)

        for name,level in [
            ("EXPANSION_HIGH",expansion),
            ("H1_NEAREST",h1_nearest),
            ("MAJOR_NEAREST",major),
        ]:
            p=liquidity_probe(raw5,r.first_touch_ts,anchor,floor,level,end)
            liqrows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "objective":name,"level":level,**p
            })

    L=pd.DataFrame(rows)
    T=pd.DataFrame(thrrows)
    Q=pd.DataFrame(liqrows)

    # Ensure almost all parent events are normalizable. Any exclusions remain explicit.
    excluded=len(fam)-len(L)

    census=[]
    for per in ["DEV","REF"]:
        q=L[L.period==per]
        census.append({
            "period":per,"parent":int((fam.period==per).sum()),"normalizable":len(q),
            "right_censored":int((q.class_24h=="RIGHT_CENSORED").sum()),
            "failure":int((q.class_24h=="FAILURE").sum()),
            "local_only":int((q.class_24h=="LOCAL_ONLY").sum()),
            "expander_1r":int((q.class_24h=="EXPANDER_1R").sum()),
            "strong_expander":int((q.class_24h=="STRONG_EXPANDER").sum()),
            "extreme_expander":int((q.class_24h=="EXTREME_EXPANDER").sum()),
            "economic_expander_ge1r":int(q.class_24h.isin(["EXPANDER_1R","STRONG_EXPANDER","EXTREME_EXPANDER"]).sum()),
        })
    C=pd.DataFrame(census)

    years=[]
    for y in sorted(L.year.unique()):
        q=L[L.year==y]
        valid=q[q.class_24h!="RIGHT_CENSORED"]
        years.append({
            "year":int(y),"n":len(q),"valid_24h":len(valid),
            "failure":int((valid.class_24h=="FAILURE").sum()),
            "local_only":int((valid.class_24h=="LOCAL_ONLY").sum()),
            "ge1r":int(valid.class_24h.isin(["EXPANDER_1R","STRONG_EXPANDER","EXTREME_EXPANDER"]).sum()),
            "ge1r_rate":float(valid.class_24h.isin(["EXPANDER_1R","STRONG_EXPANDER","EXTREME_EXPANDER"]).mean()) if len(valid) else np.nan,
            "ge1_5r":int(valid.class_24h.isin(["STRONG_EXPANDER","EXTREME_EXPANDER"]).sum()),
            "ge1_5r_rate":float(valid.class_24h.isin(["STRONG_EXPANDER","EXTREME_EXPANDER"]).mean()) if len(valid) else np.nan,
        })
    Y=pd.DataFrame(years)

    cls=[]
    for per in ["DEV","REF"]:
        for lab in ["FAILURE","LOCAL_ONLY","EXPANDER_1R","STRONG_EXPANDER","EXTREME_EXPANDER"]:
            q=L[(L.period==per)&(L.class_24h==lab)]
            if not len(q): continue
            cls.append({
                "period":per,"class_24h":lab,"n":len(q),
                "median_mfe_24h_r":float(q.mfe_24h_r.median()),
                "median_mae_24h_r":float(q.mae_24h_r.median()),
                "median_peak_24h_hours":float(q.peak_24h_hours.median()),
                "median_giveback_24h_r":float(q.giveback_24h_r.median()),
                "median_risk_pct":float(q.risk_pct.median()),
            })
    CS=pd.DataFrame(cls)

    thsum=[]
    for per in ["DEV","REF"]:
        for th in THRESHOLDS:
            q=T[(T.period==per)&(T.threshold_r==th)&(T.horizon_complete)]
            hit=q[q.reached]
            thsum.append({
                "period":per,"threshold_r":th,"eligible":len(q),
                "reached":int(q.reached.sum()),
                "reach_rate":float(q.reached.mean()) if len(q) else np.nan,
                "median_touch_hours":float(hit.touch_hours.median()) if len(hit) else np.nan,
                "median_mae_before_touch_r":float(hit.mae_before_touch_r.median()) if len(hit) else np.nan,
                "clean":int(hit.clean.fillna(False).sum()) if th in CLEAN_THRESHOLDS else np.nan,
                "clean_rate_of_eligible":float(q.clean.fillna(False).mean()) if th in CLEAN_THRESHOLDS and len(q) else np.nan,
                "clean_ambiguous":int(q.clean_ambiguous.fillna(False).sum()) if th in CLEAN_THRESHOLDS else np.nan,
            })
    TH=pd.DataFrame(thsum)

    liqsum=[]
    for per in ["DEV","REF"]:
        for obj in ["EXPANSION_HIGH","H1_NEAREST","MAJOR_NEAREST"]:
            q=Q[(Q.period==per)&(Q.objective==obj)&(Q.available)]
            q24=q[q.horizon24_complete]
            hit=q[q.hit_before_invalid]
            liqsum.append({
                "period":per,"objective":obj,"available":len(q),
                "median_distance_r":float(q.distance_r.median()) if len(q) else np.nan,
                "hit_before_invalid":int(q.hit_before_invalid.sum()) if len(q) else 0,
                "hit_before_invalid_rate":float(q.hit_before_invalid.mean()) if len(q) else np.nan,
                "eligible_24h":len(q24),
                "hit_24h":int(q24.hit_24h.sum()) if len(q24) else 0,
                "hit_24h_rate":float(q24.hit_24h.mean()) if len(q24) else np.nan,
                "median_touch_hours":float(hit.touch_hours.median()) if len(hit) else np.nan,
            })
    LS=pd.DataFrame(liqsum)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    T.to_csv(ROOT/f"{PFX}_ThresholdLedger.csv.gz",index=False,compression="gzip")
    Q.to_csv(ROOT/f"{PFX}_LiquidityLedger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_Census.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    CS.to_csv(ROOT/f"{PFX}_ClassAnatomy.csv",index=False)
    TH.to_csv(ROOT/f"{PFX}_ThresholdSummary.csv",index=False)
    LS.to_csv(ROOT/f"{PFX}_LiquiditySummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=H1_DEMAND_15M_VISUAL_FAMILY\nDEV_PARENT={dev}\nREF_PARENT={ref}\n"
        f"NORMALIZABLE={len(L)}\nEXCLUDED_NONPOSITIVE_RISK={excluded}\n"
        f"RAW_END={end.isoformat()}\nANCHOR=FIRST_TOUCH_15M_CLOSE\n"
        "RISK_UNIT=ANCHOR_MINUS_DEMAND_LOW\nPATH_START=STRICTLY_AFTER_ANCHOR_BAR\n"
        "INVALIDATION=FIRST_RAW5_LOW_LE_DEMAND_LOW_EXCLUDE_BAR\n"
        "PRIMARY_LABEL_HORIZON=24H\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S1 — Real Expansion Universe","",
        "**Detector-independent expansion labeling. No entry/filter/TP optimization.**","",
        "## Parent integrity","",
        f"- Raw endpoint: `{end.isoformat()}`",
        f"- Frozen parent family: **{len(fam)}** = DEV **{dev}** + REF **{ref}**",
        f"- Normalizable event-risk paths: **{len(L)}**; excluded non-positive risk: **{excluded}**","",
        "## 24h economic expansion census","",
        "| Period | Parent | Valid/normalizable | Censored | Failure <0.5R | Local 0.5-1R | 1-1.5R | 1.5-2R | >=2R | >=1R total |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.parent} | {r.normalizable} | {r.right_censored} | {r.failure} | "
            f"{r.local_only} | {r.expander_1r} | {r.strong_expander} | {r.extreme_expander} | {r.economic_expander_ge1r} |"
        )

    lines += ["","## Year stability","",
        "| Year | N | Valid 24h | >=1R | >=1R rate | >=1.5R | >=1.5R rate |",
        "|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.n} | {r.valid_24h} | {r.ge1r} | {fmt_pct(r.ge1r_rate)} | "
            f"{r.ge1_5r} | {fmt_pct(r.ge1_5r_rate)} |"
        )

    lines += ["","## Threshold reach and cleanliness","",
        "| Period | Threshold | Eligible | Reach | Rate | Med time | Med MAE before hit | Clean before -0.5R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in TH.itertuples(index=False):
        clean="—" if not np.isfinite(r.clean) else f"{int(r.clean)} ({fmt_pct(r.clean_rate_of_eligible)})"
        lines.append(
            f"| {r.period} | {r.threshold_r:.2f}R | {r.eligible} | {r.reached} | {fmt_pct(r.reach_rate)} | "
            f"{fmt_num(r.median_touch_hours,2)}h | {fmt_num(r.median_mae_before_touch_r)}R | {clean} |"
        )

    lines += ["","## Causal real-liquidity reach","",
        "| Period | Objective | Available | Med distance | Hit before invalid | Hit <=24h | Med time if hit |",
        "|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in LS.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.objective} | {r.available} | {fmt_num(r.median_distance_r)}R | "
            f"{r.hit_before_invalid} ({fmt_pct(r.hit_before_invalid_rate)}) | "
            f"{r.hit_24h}/{r.eligible_24h} ({fmt_pct(r.hit_24h_rate)}) | {fmt_num(r.median_touch_hours,2)}h |"
        )

    lines += ["","## Interpretation boundary",
        "B39-S1 freezes the outcome universe only.",
        "The event risk unit is a normalization device, not a recommended live entry/SL.",
        "B39-S2 may now work backward from >=1R / >=1.5R expansion events and compare them with LOCAL_ONLY and FAILURE lookalikes using only pre-event structure."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S1_REAL_EXPANSION_UNIVERSE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
