#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as old

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def overlap_ratio_of_new_bar(current_low,current_high,bar_low,bar_high):
    rng=bar_high-bar_low
    if rng<=0: return 0.0
    inter=max(0.0,min(current_high,bar_high)-max(current_low,bar_low))
    return inter/rng

def build_candidates(h1):
    hp,lp=old.pivots_df(h1)
    hp=hp.sort_values("confirm_ts").reset_index(drop=True)
    lp=lp.sort_values("confirm_ts").reset_index(drop=True)

    highs_by_confirm={}
    for r in hp.itertuples(index=False):
        highs_by_confirm.setdefault(r.confirm_ts,[]).append((r.pivot_ts,float(r.level)))

    active_highs=[]
    used_highs=set()
    rows=[]
    prev_close=None
    idx=h1.index

    for i,(t,b) in enumerate(h1.iterrows()):
        latest=active_highs[-1] if active_highs else None
        if latest is not None and prev_close is not None:
            swing_ts,broken_level=latest
            if swing_ts not in used_highs and prev_close<=broken_level and float(b.close)>broken_level:
                # Latest confirmed pivot low strictly before BOS, within previous 8 H1 bars.
                eligible=lp[(lp.confirm_ts<t)&(lp.pivot_ts<t)]
                if len(eligible):
                    eligible=eligible.copy()
                    eligible["bars_back"]=[i-int(idx.get_loc(x)) for x in eligible.pivot_ts]
                    eligible=eligible[(eligible.bars_back>=1)&(eligible.bars_back<=8)]
                if len(eligible):
                    seed=eligible.sort_values(["confirm_ts","pivot_ts"]).iloc[-1]
                    seed_i=int(idx.get_loc(seed.pivot_ts))
                    base_idxs=[seed_i]
                    cur_lo=float(h1.low.iloc[seed_i])
                    cur_hi=float(h1.high.iloc[seed_i])
                    overlaps=[]
                    # Expand forward by objective overlap, max total base size 4, BOS excluded.
                    for j in range(seed_i+1,min(i,seed_i+4)):
                        blo=float(h1.low.iloc[j]); bhi=float(h1.high.iloc[j])
                        ov=overlap_ratio_of_new_bar(cur_lo,cur_hi,blo,bhi)
                        if ov<0.50:
                            break
                        base_idxs.append(j)
                        overlaps.append(ov)
                        cur_lo=min(cur_lo,blo)
                        cur_hi=max(cur_hi,bhi)

                    dep_start=base_idxs[-1]+1
                    if dep_start<i:  # at least one completed departure bar before BOS.
                        protected_low=min(float(h1.low.iloc[j]) for j in base_idxs)
                        if float(h1.low.iloc[dep_start:i+1].min())>=protected_low-1e-12:
                            base_low=protected_low
                            base_high=max(float(h1.high.iloc[j]) for j in base_idxs)
                            if base_high>base_low:
                                base_width=base_high-base_low
                                dep=h1.iloc[dep_start:i+1]
                                close_arr=dep.close.to_numpy(float)
                                if len(close_arr)>1:
                                    denom=float(np.abs(np.diff(close_arr)).sum())
                                    eff=abs(float(close_arr[-1]-close_arr[0]))/denom if denom>0 else 0.0
                                else:
                                    eff=1.0
                                dep_net=(float(b.close)-float(h1.close.iloc[dep_start]))/base_width
                                bos_overshoot=(float(b.close)-broken_level)/base_width
                                bos_rng=float(b.high-b.low)
                                bos_body=abs(float(b.close-b.open))
                                bos_body_frac=bos_body/bos_rng if bos_rng>0 else np.nan

                                # Formation FVG: any bullish 3-candle gap in departure->BOS.
                                fvg_sizes=[]
                                for k in range(max(2,dep_start),i+1):
                                    gap=float(h1.low.iloc[k]-h1.high.iloc[k-2])
                                    if gap>0:
                                        fvg_sizes.append(gap/base_width)
                                has_fvg=bool(fvg_sizes)
                                max_fvg=max(fvg_sizes) if fvg_sizes else 0.0

                                # Sweep of prior confirmed pivot-low by source seed.
                                prior_lows=lp[(lp.confirm_ts<=seed.confirm_ts)&(lp.pivot_ts<seed.pivot_ts)]
                                prior_low=float(prior_lows.iloc[-1].level) if len(prior_lows) else np.nan
                                seed_low=float(seed.level)
                                swept_prior=bool(np.isfinite(prior_low) and seed_low<prior_low and float(b.close)>prior_low)

                                base_ranges=np.array([float(h1.high.iloc[j]-h1.low.iloc[j]) for j in base_idxs],float)
                                base_bodies=np.array([abs(float(h1.close.iloc[j]-h1.open.iloc[j])) for j in base_idxs],float)
                                base_body_frac=float(np.mean(np.divide(base_bodies,base_ranges,out=np.zeros_like(base_bodies),where=base_ranges>0))) if len(base_ranges) else np.nan

                                rows.append({
                                    "zone_id":f"B40_D_{t.isoformat()}",
                                    "activation_ts":t,
                                    "broken_swing_ts":swing_ts,
                                    "broken_level":broken_level,
                                    "bos_open":float(b.open),"bos_high":float(b.high),
                                    "bos_low":float(b.low),"bos_close":float(b.close),
                                    "seed_pivot_ts":seed.pivot_ts,
                                    "seed_confirm_ts":seed.confirm_ts,
                                    "seed_low":seed_low,
                                    "base_start_ts":idx[base_idxs[0]],
                                    "base_end_ts":idx[base_idxs[-1]],
                                    "base_candles":len(base_idxs),
                                    "base_low":base_low,
                                    "base_high":base_high,
                                    "base_width":base_width,
                                    "protected_low":protected_low,
                                    "base_mean_added_overlap":float(np.mean(overlaps)) if overlaps else 1.0,
                                    "base_mean_body_frac":base_body_frac,
                                    "departure_start_ts":idx[dep_start],
                                    "departure_bars":int(i-dep_start+1),
                                    "departure_net_progress_zone_r":dep_net,
                                    "departure_efficiency":eff,
                                    "bos_overshoot_zone_r":bos_overshoot,
                                    "bos_body_frac":bos_body_frac,
                                    "has_bull_fvg":has_fvg,
                                    "max_bull_fvg_zone_r":max_fvg,
                                    "prior_confirmed_low":prior_low,
                                    "predeparture_swept_prior_low":swept_prior,
                                    "source_age_at_activation_h":float((t-seed.pivot_ts)/pd.Timedelta(hours=1)),
                                })
                                used_highs.add(swing_ts)

        for ev in highs_by_confirm.get(t,[]):
            active_highs.append(ev)
        prev_close=float(b.close)

    return pd.DataFrame(rows)

def approach_features(m15,touch_i,zone):
    start=max(0,touch_i-8)
    q=m15.iloc[start:touch_i]
    out={
        "approach_bars":len(q),
        "approach_slope_per_zone_r":np.nan,
        "approach_efficiency":np.nan,
        "approach_overlap_mean":np.nan,
        "approach_net_progress_zone_r":np.nan,
        "last1_bear_progress_zone_r":np.nan,
        "last2_bear_progress_zone_r":np.nan,
        "last3_bear_progress_zone_r":np.nan,
        "touch_local_liquidity_sweep":False,
    }
    zw=float(zone.base_width)
    if len(q)>=2 and zw>0:
        closes=q.close.to_numpy(float)
        x=np.arange(len(closes),dtype=float)
        out["approach_slope_per_zone_r"]=float(np.polyfit(x,closes,1)[0]/zw)
        denom=float(np.abs(np.diff(closes)).sum())
        out["approach_efficiency"]=abs(float(closes[-1]-closes[0]))/denom if denom>0 else 0.0
        out["approach_net_progress_zone_r"]=float((closes[-1]-closes[0])/zw)
        ovs=[]
        for j in range(1,len(q)):
            lo1=float(q.low.iloc[j-1]); hi1=float(q.high.iloc[j-1])
            lo2=float(q.low.iloc[j]); hi2=float(q.high.iloc[j])
            rng2=hi2-lo2
            if rng2>0:
                ovs.append(max(0.0,min(hi1,hi2)-max(lo1,lo2))/rng2)
        out["approach_overlap_mean"]=float(np.mean(ovs)) if ovs else np.nan

    touch=m15.iloc[touch_i]
    tc=float(touch.close)
    for n in [1,2,3]:
        if touch_i-n>=0 and zw>0:
            ref=float(m15.close.iloc[touch_i-n])
            out[f"last{n}_bear_progress_zone_r"]=(tc-ref)/zw

    if touch_i>=3:
        prev_min=float(m15.low.iloc[touch_i-3:touch_i].min())
        out["touch_local_liquidity_sweep"]=bool(float(touch.low)<prev_min and float(touch.close)>prev_min)
    return out

def first_retest(m15,z,end):
    idx=m15.index
    i0=int(idx.searchsorted(pd.Timestamp(z.activation_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(end),side="right"))
    lo=m15.low.to_numpy(float,copy=False); hi=m15.high.to_numpy(float,copy=False)
    for i in range(i0,i1):
        if lo[i]<=float(z.base_high) and hi[i]>=float(z.base_low):
            return i
    return None

def evaluate_path(m15,touch_i,anchor,floor,risk,end):
    idx=m15.index
    deadline=min(pd.Timestamp(end),idx[touch_i]+pd.Timedelta(hours=24))
    i0=touch_i+1
    i1=int(idx.searchsorted(deadline,side="right"))
    thresholds=[0.5,1.0,1.5,2.0]
    hit={x:False for x in thresholds}
    hit_ts={x:pd.NaT for x in thresholds}
    mfe=0.0
    consumption_ts=pd.NaT
    survival="CENSORED"

    for i in range(i0,i1):
        b=m15.iloc[i]
        vals={x:float(b.high)>=anchor+x*risk for x in thresholds}
        consumed=float(b.close)<floor
        if vals[0] and consumed:
            survival="AMBIGUOUS"
            consumption_ts=idx[i]
            break
        if consumed:
            survival="CONSUMED"
            consumption_ts=idx[i]
            break
        for x in thresholds:
            if (not hit[x]) and vals[x]:
                hit[x]=True; hit_ts[x]=idx[i]
        mfe=max(mfe,(float(b.high)-anchor)/risk)
        if hit[0] and survival=="CENSORED":
            survival="SURVIVE"

    # If survived, continue measuring expansion only until first later clean consumption or horizon.
    if survival=="SURVIVE":
        start_after=i0
        mfe=0.0
        hit={x:False for x in thresholds}
        hit_ts={x:pd.NaT for x in thresholds}
        consumption_ts=pd.NaT
        for i in range(i0,i1):
            b=m15.iloc[i]
            vals={x:float(b.high)>=anchor+x*risk for x in thresholds}
            consumed=float(b.close)<floor
            # Same bar threshold/consumption: do not credit new threshold due ordering ambiguity.
            if consumed:
                consumption_ts=idx[i]
                break
            for x in thresholds:
                if (not hit[x]) and vals[x]:
                    hit[x]=True; hit_ts[x]=idx[i]
            mfe=max(mfe,(float(b.high)-anchor)/risk)

    return {
        "survival_status":survival,
        "consumption_ts":consumption_ts,
        "mfe_pre_consumption_24h_r":float(max(0.0,mfe)),
        **{f"hit_{str(x).replace('.','_')}r":bool(hit[x]) for x in thresholds},
        **{f"time_to_{str(x).replace('.','_')}r_min":
           (float((hit_ts[x]-idx[touch_i])/pd.Timedelta(minutes=1)) if pd.notna(hit_ts[x]) else np.nan)
           for x in thresholds},
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    old.START=START; old.END=end
    h1=old.exact_exec(raw,"1h",12); h1=h1[(h1.index>=START-pd.Timedelta(days=30))&(h1.index<=end)].copy()
    m15=old.exact_exec(raw,"15min",3); m15=m15[(m15.index>=START-pd.Timedelta(days=30))&(m15.index<=end)].copy()

    Z=build_candidates(h1)
    rows=[]
    for z in Z.itertuples(index=False):
        if pd.Timestamp(z.activation_ts)<START or pd.Timestamp(z.activation_ts)>end:
            continue
        ti=first_retest(m15,z,end)
        if ti is None:
            continue
        t=m15.index[ti]
        touch=m15.iloc[ti]
        anchor=float(touch.close)
        floor=float(z.protected_low)
        risk=anchor-floor
        normalizable=bool(risk>0)

        rec={
            **z._asdict(),
            "period":period(t),
            "year":int(t.year),
            "first_retest_ts":t,
            "touch_open":float(touch.open),"touch_high":float(touch.high),
            "touch_low":float(touch.low),"touch_close":anchor,
            "zone_age_at_retest_h":float((t-pd.Timestamp(z.activation_ts))/pd.Timedelta(hours=1)),
            "normalizable":normalizable,
            "event_risk":risk if normalizable else np.nan,
        }
        rec.update(approach_features(m15,ti,z))
        if normalizable:
            rec.update(evaluate_path(m15,ti,anchor,floor,risk,end))
        else:
            rec.update({
                "survival_status":"NONPOSITIVE_RISK","consumption_ts":pd.NaT,
                "mfe_pre_consumption_24h_r":np.nan,
                "hit_0_5r":False,"hit_1_0r":False,"hit_1_5r":False,"hit_2_0r":False,
                "time_to_0_5r_min":np.nan,"time_to_1_0r_min":np.nan,
                "time_to_1_5r_min":np.nan,"time_to_2_0r_min":np.nan,
            })
        rows.append(rec)

    L=pd.DataFrame(rows)
    if not len(L):
        raise RuntimeError("no B40 candidates")

    N=L[L.normalizable].copy()
    def label(r):
        if r.survival_status=="CONSUMED": return "CONSUMED"
        if r.survival_status=="AMBIGUOUS": return "AMBIGUOUS"
        if r.survival_status=="CENSORED": return "CENSORED"
        if bool(r.hit_2_0r): return "EXTREME_2R"
        if bool(r.hit_1_5r): return "STRONG_1_5R"
        if bool(r.hit_1_0r): return "EXPANDER_1R"
        if bool(r.hit_0_5r): return "SURVIVED_LOCAL_ONLY"
        return "CENSORED"
    N["outcome_class"]=[label(r) for r in N.itertuples(index=False)]
    L=L.merge(N[["zone_id","outcome_class"]],on="zone_id",how="left")

    census=[]
    for per in ["DEV","REF"]:
        q=N[N.period==per]
        census.append({
            "period":per,"n":len(q),
            "survive":int((q.survival_status=="SURVIVE").sum()),
            "consumed":int((q.survival_status=="CONSUMED").sum()),
            "ambiguous":int((q.survival_status=="AMBIGUOUS").sum()),
            "censored":int((q.survival_status=="CENSORED").sum()),
            "hit_0_5r":int(q.hit_0_5r.sum()),"hit_1_0r":int(q.hit_1_0r.sum()),
            "hit_1_5r":int(q.hit_1_5r.sum()),"hit_2_0r":int(q.hit_2_0r.sum()),
            "median_mfe":float(q.mfe_pre_consumption_24h_r.median()) if len(q) else np.nan,
            "median_t_0_5":float(q.time_to_0_5r_min.median()) if q.hit_0_5r.any() else np.nan,
            "median_t_1_0":float(q.time_to_1_0r_min.median()) if q.hit_1_0r.any() else np.nan,
            "median_t_1_5":float(q.time_to_1_5r_min.median()) if q.hit_1_5r.any() else np.nan,
            "median_t_2_0":float(q.time_to_2_0r_min.median()) if q.hit_2_0r.any() else np.nan,
        })
    C=pd.DataFrame(census)

    Y=[]
    for y in sorted(N.year.unique()):
        q=N[N.year==y]
        Y.append({
            "year":int(y),"n":len(q),
            "survive_rate":float((q.survival_status=="SURVIVE").mean()) if len(q) else np.nan,
            "consumed_rate":float((q.survival_status=="CONSUMED").mean()) if len(q) else np.nan,
            "hit_1r_rate":float(q.hit_1_0r.mean()) if len(q) else np.nan,
            "hit_1_5r_rate":float(q.hit_1_5r.mean()) if len(q) else np.nan,
            "hit_2r_rate":float(q.hit_2_0r.mean()) if len(q) else np.nan,
        })
    Y=pd.DataFrame(Y)

    formation_cols=[
        "base_candles","base_width","base_mean_added_overlap","base_mean_body_frac",
        "departure_bars","departure_net_progress_zone_r","departure_efficiency",
        "bos_overshoot_zone_r","bos_body_frac","has_bull_fvg","max_bull_fvg_zone_r",
        "predeparture_swept_prior_low","source_age_at_activation_h"
    ]
    retest_cols=[
        "zone_age_at_retest_h","approach_bars","approach_slope_per_zone_r",
        "approach_efficiency","approach_overlap_mean","approach_net_progress_zone_r",
        "last1_bear_progress_zone_r","last2_bear_progress_zone_r","last3_bear_progress_zone_r",
        "touch_local_liquidity_sweep"
    ]

    desc=[]
    for per in ["DEV","REF"]:
        q=N[N.period==per]
        for scope,cols in [("FORMATION",formation_cols),("RETEST",retest_cols)]:
            for col in cols:
                x=q[col]
                if x.dtype==bool:
                    desc.append({"period":per,"scope":scope,"feature":col,"n":int(x.notna().sum()),
                                 "mean":float(x.mean()),"q25":np.nan,"median":np.nan,"q75":np.nan})
                else:
                    x=pd.to_numeric(x,errors="coerce").dropna()
                    desc.append({"period":per,"scope":scope,"feature":col,"n":len(x),
                                 "mean":float(x.mean()) if len(x) else np.nan,
                                 "q25":float(x.quantile(.25)) if len(x) else np.nan,
                                 "median":float(x.median()) if len(x) else np.nan,
                                 "q75":float(x.quantile(.75)) if len(x) else np.nan})
    D=pd.DataFrame(desc)

    L.to_csv(ROOT/f"{PFX}_CandidateLedger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_Census.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    D.to_csv(ROOT/f"{PFX}_DescriptorDistribution.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        "TIMEFRAME_ZONE=H1\n"
        "BOS=CONFIRMED_H1_SWING_HIGH_CROSSED_BY_H1_CLOSE\n"
        "SOURCE_SEED=LATEST_CONFIRMED_H1_PIVOT_LOW_WITHIN_PREVIOUS_8_BARS\n"
        "BASE_EXPANSION=FORWARD_RANGE_OVERLAP_GTE_50PCT_MAX_4_CANDLES\n"
        "ZONE_BOUNDS=BASE_LOW_TO_BASE_HIGH\n"
        "PROTECTED_LOW=BASE_LOW\n"
        "RETEST=FIRST_15M_RANGE_INTERSECTION_AFTER_ACTIVATION\n"
        "SURVIVAL=PLUS_0_5_EVENT_R_BEFORE_15M_CLOSE_BELOW_PROTECTED_LOW\n"
        "HORIZON=24H_FROM_FIRST_RETEST\n"
        "NO_B39_D1_FILTER=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S1 — Demand Survival vs Expansion Universe","",
        "Demand candidate is now anchored to a confirmed H1 pivot-low source/base, not the last bearish candle before BOS.",
        "B39 D1 is not used in candidate construction or outcome labeling.","",
        "## Universe census","",
        "| Period | N | Survive >=0.5R | Consumed | Ambiguous | Censored | >=1R | >=1.5R | >=2R | Median MFE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.n} | {r.survive} ({fmt_pct(r.survive/r.n if r.n else np.nan)}) | "
            f"{r.consumed} ({fmt_pct(r.consumed/r.n if r.n else np.nan)}) | {r.ambiguous} | {r.censored} | "
            f"{r.hit_1_0r} ({fmt_pct(r.hit_1_0r/r.n if r.n else np.nan)}) | "
            f"{r.hit_1_5r} ({fmt_pct(r.hit_1_5r/r.n if r.n else np.nan)}) | "
            f"{r.hit_2_0r} ({fmt_pct(r.hit_2_0r/r.n if r.n else np.nan)}) | {fmt_num(r.median_mfe)}R |"
        )
    lines += ["","## Threshold timing","",
        "| Period | Med to 0.5R | Med to 1R | Med to 1.5R | Med to 2R |",
        "|---|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.period} | {fmt_num(r.median_t_0_5,1)}m | {fmt_num(r.median_t_1_0,1)}m | "
            f"{fmt_num(r.median_t_1_5,1)}m | {fmt_num(r.median_t_2_0,1)}m |"
        )
    lines += ["","## Year stability","",
        "| Year | N | Survival | Consumed | >=1R | >=1.5R | >=2R |",
        "|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.n} | {fmt_pct(r.survive_rate)} | {fmt_pct(r.consumed_rate)} | "
            f"{fmt_pct(r.hit_1r_rate)} | {fmt_pct(r.hit_1_5r_rate)} | {fmt_pct(r.hit_2r_rate)} |"
        )
    lines += ["","## Boundary",
        "S1 creates the unbiased structural universe only.",
        "No formation or retest feature is ranked, selected, filtered, or promoted in S1.",
        "S2 must analyze SURVIVED versus CONSUMED; expansion quality is a separate downstream question."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
