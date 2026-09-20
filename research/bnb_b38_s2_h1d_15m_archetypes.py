#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S2_H1D_15M_ARCHETYPES"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")
ARCHES=[
    "A_CLEAN_PROXIMAL_RECLAIM",
    "B_CLEAN_IN_ZONE_HOLD",
    "C_SWEEP_FULL_RECLAIM",
    "D_SWEEP_PARTIAL_RECLAIM",
]

def safe_div(a,b):
    if not np.isfinite(a) or not np.isfinite(b) or abs(b)<1e-12:return np.nan
    return float(a/b)

def classify(r):
    clean=float(r.touch_low)>=float(r.demand_low)
    full=float(r.touch_close)>float(r.demand_high)
    if clean and full:return ARCHES[0]
    if clean and not full:return ARCHES[1]
    if (not clean) and full:return ARCHES[2]
    return ARCHES[3]

def known_geometry(exec_b,fam):
    highs,_=s1.pivots_df(exec_b)
    rows=[]
    for r in fam.itertuples(index=False):
        width=float(r.demand_width)
        tr=float(r.touch_high-r.touch_low)
        before=exec_b[exec_b.index<r.first_touch_ts].tail(7)

        # nearest already-confirmed 15m pivot high above touch close, confirmed before retest.
        q=highs[(highs.confirm_ts<r.first_touch_ts)&
                (highs.pivot_ts>r.expansion_pivot_ts)&
                (highs.level>float(r.touch_close))]
        if len(q):
            nr=q.sort_values(["pivot_ts","confirm_ts"]).iloc[-1]
            nearest_ts=nr.pivot_ts
            nearest_high=float(nr.level)
        else:
            nearest_ts=r.expansion_pivot_ts
            nearest_high=float(r.expansion_high)

        comp=np.nan
        if len(before)>=6:
            rg=(before.high-before.low).to_numpy(float)
            prev=float(np.median(rg[-6:-3])); last=float(np.median(rg[-3:]))
            comp=safe_div(last,prev)

        rows.append({
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "archetype":classify(r),
            "penetration_fraction":safe_div(float(r.demand_high-r.touch_low),width),
            "close_zone_fraction":safe_div(float(r.touch_close-r.demand_low),width),
            "touch_close_location":safe_div(float(r.touch_close-r.touch_low),tr),
            "touch_bullish":bool(float(r.touch_close)>float(r.touch_open)),
            "pullback_bars":int(r.pullback_bars),
            "expansion_above_bos_zw":safe_div(float(r.expansion_high-r.bos_close),width),
            "expansion_above_demand_zw":safe_div(float(r.expansion_high-r.demand_high),width),
            "risk_close_to_demand_low_zw":safe_div(float(r.touch_close-r.demand_low),width),
            "risk_close_to_touch_low_zw":safe_div(float(r.touch_close-r.touch_low),width),
            "nearest_overhead_pivot_ts":nearest_ts,
            "nearest_overhead_pivot_high":nearest_high,
            "room_to_nearest_pivot_zw":safe_div(float(nearest_high-r.touch_close),width),
            "room_to_expansion_high_zw":safe_div(float(r.expansion_high-r.touch_close),width),
            "approach_compression_3v3":comp,
            "approach_compressed":bool(np.isfinite(comp) and comp<=1.0),
        })
    return pd.DataFrame(rows)

def forward_path(exec_b,fam):
    idx=exec_b.index
    rows=[]
    for r in fam.itertuples(index=False):
        start_i=int(idx.searchsorted(r.first_touch_ts,side="right"))
        end_i=int(idx.searchsorted(END,side="right"))
        width=float(r.demand_width)
        t1=float(r.demand_high+width)
        t2=float(r.demand_high+2*width)
        tfull=float(r.expansion_high)

        hit1=hit2=hitfull=False
        bars1=np.nan
        invalid_ts=pd.NaT
        invalid_bars=np.nan
        max_close=-np.inf
        min_low_to_1=float(r.touch_low)

        for j,i in enumerate(range(start_i,end_i),start=1):
            bar=exec_b.iloc[i]
            c=float(bar.close); lo=float(bar.low)
            if c<float(r.demand_low):
                invalid_ts=idx[i]; invalid_bars=float(j)
                break
            max_close=max(max_close,c)
            if not hit1:
                min_low_to_1=min(min_low_to_1,lo)
            if c>t1 and not hit1:
                hit1=True; bars1=float(j)
            if c>t2:hit2=True
            if c>tfull:hitfull=True

        if max_close==-np.inf:max_close=np.nan
        mfe=safe_div(max_close-float(r.demand_high),width) if np.isfinite(max_close) else np.nan
        mae1=safe_div(float(r.touch_close)-min_low_to_1,width) if hit1 else np.nan

        rows.append({
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "rebound_1zw":hit1,
            "rebound_2zw":hit2,
            "full_continuation":hitfull,
            "mfe_zw":mfe,
            "bars_to_1zw":bars1,
            "mae_before_1zw_from_touch_close_zw":mae1,
            "invalid_ts":invalid_ts,
            "bars_to_invalidation":invalid_bars,
        })
    return pd.DataFrame(rows)

def med(q,col):
    x=pd.to_numeric(q[col],errors="coerce").dropna()
    return float(x.median()) if len(x) else np.nan

def qtile(q,col,p):
    x=pd.to_numeric(q[col],errors="coerce").dropna()
    return float(x.quantile(p)) if len(x) else np.nan

def rate(q,col):
    return float(q[col].astype(bool).mean()) if len(q) else np.nan

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    h1=s1.exact_exec(raw,"1h",12)
    m15=s1.exact_exec(raw,"15min",3)
    h1=h1[h1.index<=END].copy()
    m15=m15[m15.index<=END].copy()

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=END)].copy()
    if len(fam)!=788:
        raise RuntimeError(f"frozen B38-S1 H1D/15m family drift: {len(fam)} != 788")

    G=known_geometry(m15,fam)
    F=forward_path(m15,fam)
    L=fam.merge(G,on=["zone_id","first_touch_ts"],how="left").merge(F,on=["zone_id","first_touch_ts"],how="left")
    L["retest_year"]=pd.to_datetime(L.first_touch_ts,utc=True).dt.year.astype(int)

    # Integrity: exhaustive, one archetype per event.
    if L.archetype.isna().any() or len(L)!=788:
        raise RuntimeError("archetype assignment incomplete")
    if set(L.archetype.unique())-set(ARCHES):
        raise RuntimeError("unknown archetype")

    summary=[]
    yearly=[]
    for a in ARCHES:
        q=L[L.archetype==a].copy()
        row={
            "archetype":a,
            "n":len(q),
            "share":len(q)/len(L),
            "r1zw_rate":rate(q,"rebound_1zw"),
            "r2zw_rate":rate(q,"rebound_2zw"),
            "full_cont_rate":rate(q,"full_continuation"),
            "mfe_med":med(q,"mfe_zw"),
            "mfe_p25":qtile(q,"mfe_zw",.25),
            "mfe_p75":qtile(q,"mfe_zw",.75),
            "risk_demand_med":med(q,"risk_close_to_demand_low_zw"),
            "risk_touchlow_med":med(q,"risk_close_to_touch_low_zw"),
            "room_nearest_med":med(q,"room_to_nearest_pivot_zw"),
            "room_expansion_med":med(q,"room_to_expansion_high_zw"),
            "bars_to_1zw_med":med(q[q.rebound_1zw],"bars_to_1zw"),
            "mae_to_1zw_med":med(q[q.rebound_1zw],"mae_before_1zw_from_touch_close_zw"),
            "bullish_touch_rate":rate(q,"touch_bullish"),
            "compressed_rate":rate(q[q.approach_compression_3v3.notna()],"approach_compressed"),
        }
        for y in [2022,2023,2024]:
            qy=q[q.retest_year==y]
            row[f"n_{y}"]=len(qy)
            row[f"r1zw_{y}"]=rate(qy,"rebound_1zw")
            yearly.append({
                "archetype":a,"year":y,"n":len(qy),
                "r1zw_rate":rate(qy,"rebound_1zw"),
                "r2zw_rate":rate(qy,"rebound_2zw"),
                "full_cont_rate":rate(qy,"full_continuation"),
                "mfe_med":med(qy,"mfe_zw"),
            })
        summary.append(row)

    S=pd.DataFrame(summary)
    Y=pd.DataFrame(yearly)
    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_Yearly.csv",index=False)

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x):
        return "—" if not np.isfinite(x) else f"{x:.2f}"

    lines=[
      "# BNB B38-S2 — H1 Demand / 15m Structural Archetype Discovery","",
      "**2022-2024 DEVELOPMENT STUDY — NO OOS CLAIM**","",
      "Frozen parent: **788 H1-demand / 15m-execution visual-family events**.","",
      "## Primary archetypes","",
      "- **A CLEAN_PROXIMAL_RECLAIM**: distal demand holds; first 15m close reclaims above demand_high.",
      "- **B CLEAN_IN_ZONE_HOLD**: distal demand holds; first 15m close remains inside demand.",
      "- **C SWEEP_FULL_RECLAIM**: 15m low sweeps below demand_low, then close recovers above demand_high.",
      "- **D SWEEP_PARTIAL_RECLAIM**: 15m low sweeps below demand_low, then close recovers only inside demand.","",
      "## Archetype census and path","",
      "| Archetype | N | Share | 2022/23/24 | +1ZW | +2ZW | Full cont. | MFE median | MFE IQR |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.archetype} | {r.n} | {pct(r.share)} | {r.n_2022}/{r.n_2023}/{r.n_2024} | "
            f"{pct(r.r1zw_rate)} | {pct(r.r2zw_rate)} | {pct(r.full_cont_rate)} | "
            f"{num(r.mfe_med)}ZW | {num(r.mfe_p25)}–{num(r.mfe_p75)}ZW |"
        )

    lines += ["","## Geometry available at the retest close","",
      "| Archetype | Risk to demand_low | Risk to touch low | Room nearest 15m pivot | Room expansion high | Bullish touch | Compressed approach |",
      "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.archetype} | {num(r.risk_demand_med)}ZW | {num(r.risk_touchlow_med)}ZW | "
            f"{num(r.room_nearest_med)}ZW | {num(r.room_expansion_med)}ZW | "
            f"{pct(r.bullish_touch_rate)} | {pct(r.compressed_rate)} |"
        )

    lines += ["","## Successful +1ZW path","",
      "| Archetype | Median bars to +1ZW | Median adverse excursion before +1ZW |",
      "|---|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.archetype} | {num(r.bars_to_1zw_med)} x15m | {num(r.mae_to_1zw_med)}ZW |")

    lines += ["","## Year-by-year +1ZW rebound","",
      "| Archetype | 2022 | 2023 | 2024 |",
      "|---|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.archetype} | {pct(r.r1zw_2022)} | {pct(r.r1zw_2023)} | {pct(r.r1zw_2024)} |")

    lines += ["","## Adaptive-execution questions created by S2",
      "- **A CLEAN_PROXIMAL_RECLAIM:** test whether reclaim-close can be an immediate trigger and demand_low a structural invalidation reference.",
      "- **B CLEAN_IN_ZONE_HOLD:** test a delayed confirmation trigger because price has not yet reclaimed the proximal edge.",
      "- **C SWEEP_FULL_RECLAIM:** test whether the sweep low becomes the better structural invalidation reference than the original demand_low.",
      "- **D SWEEP_PARTIAL_RECLAIM:** test whether entry must wait for a later 15m micro-BOS / proximal reclaim.",
      "",
      "**No entry, SL, or TP rule is selected in S2.** The archetypes and their geometry are now mapped for B38-S3 adaptive execution design."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S2_ARCHETYPES_MAPPED\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
