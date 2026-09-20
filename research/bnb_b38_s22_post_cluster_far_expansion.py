#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s14_post_tp1_continuation as s14
import bnb_b38_s18_wide_sl_structural_invalidation as s18
import bnb_b38_s20_post_entry_failure_character as s20

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S22_POST_CLUSTER_FAR_EXPANSION"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727

TARGETS=["MAJOR_NEAREST","H1_NEAREST","EXPANSION","R_0_50","R_1_00"]

NUM_FEATURES=[
    "tp1_r","tp2_r","tp1_to_tp2_gap_r","known_target_count","objective_room_from_tp2_r",
    "minutes_entry_to_tp1","minutes_tp1_to_tp2","minutes_entry_to_tp2","cluster_gap_r_per_minute",
    "cluster_path_efficiency","cluster_green_rate","cluster_close_above_tp1_rate",
    "cluster_max_pullback_r","cluster_mae_from_tp1_r",
    "last1_progress_r","last3_progress_r","last3_green_rate","distance_remaining_tp2_r",
    "tp2_close_above_r","tp2_bar_body_r","tp2_bar_range_r","tp2_close_location",
]
BIN_FEATURES=["tp2_accept"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def first_touch_idx(raw5,start_ts,level,kind,end):
    if not np.isfinite(level): return None
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def target_level(r,label):
    entry=float(r.entry_price); risk=entry-float(r.touch_low_sl)
    if label=="MAJOR_NEAREST": return float(r.major_nearest) if np.isfinite(r.major_nearest) else np.nan
    if label=="H1_NEAREST": return float(r.h1_nearest) if np.isfinite(r.h1_nearest) else np.nan
    if label=="EXPANSION": return float(r.expansion_target) if np.isfinite(r.expansion_target) else np.nan
    if label=="R_0_50": return entry+0.50*risk
    if label=="R_1_00": return entry+1.00*risk
    raise RuntimeError(label)

def feature_row(raw5,r,tp1_i,tp2_i):
    idx=raw5.index
    entry=float(r.entry_price); sl=float(r.touch_low_sl); risk=entry-sl
    tp1=float(r.tp1); tp2=float(r.tp2)
    t1=idx[tp1_i]; t2=idx[tp2_i]

    # Completed 5m bars strictly before TP2 touch bar, beginning at TP1 touch bar.
    pre=raw5.iloc[tp1_i:tp2_i].copy()
    inner=raw5.iloc[tp1_i+1:tp2_i].copy()

    mins_e_t1=float((t1-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1))
    mins_t1_t2=float((t2-t1)/pd.Timedelta(minutes=1))
    mins_e_t2=float((t2-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1))
    gap_r=(tp2-tp1)/risk

    if len(pre)>=2:
        closes=pre.close.to_numpy(float)
        denom=float(np.abs(np.diff(closes)).sum())
        path_eff=(float(closes[-1])-float(closes[0]))/denom if denom>0 else np.nan
    else:
        path_eff=np.nan

    green=float((inner.close>inner.open).mean()) if len(inner) else np.nan
    above=float((inner.close>=tp1).mean()) if len(inner) else np.nan
    mae=(float(inner.low.min())-tp1)/risk if len(inner) else np.nan

    max_pb=np.nan
    if len(pre):
        highs=pre.high.to_numpy(float)
        lows=pre.low.to_numpy(float)
        run=-np.inf; m=0.0
        for h,l in zip(highs,lows):
            run=max(run,float(h))
            m=max(m,run-float(l))
        max_pb=m/risk

    last1=np.nan; last3=np.nan; last3g=np.nan; remain=np.nan
    if len(pre):
        remain=(tp2-float(pre.close.iloc[-1]))/risk
    if len(pre)>=2:
        last1=(float(pre.close.iloc[-1])-float(pre.close.iloc[-2]))/risk
    if len(pre)>=4:
        last3=(float(pre.close.iloc[-1])-float(pre.close.iloc[-4]))/risk
        q=pre.iloc[-3:]
        last3g=float((q.close>q.open).mean())

    b=raw5.iloc[tp2_i]
    rng=float(b.high-b.low)
    cloc=(float(b.close-b.low)/rng) if rng>0 else np.nan

    return {
        "tp1_touch_ts":t1,"tp2_touch_ts":t2,
        "tp1_r":(tp1-entry)/risk,
        "tp2_r":(tp2-entry)/risk,
        "tp1_to_tp2_gap_r":gap_r,
        "known_target_count":float(r.known_target_count),
        "minutes_entry_to_tp1":mins_e_t1,
        "minutes_tp1_to_tp2":mins_t1_t2,
        "minutes_entry_to_tp2":mins_e_t2,
        "cluster_gap_r_per_minute":gap_r/mins_t1_t2 if mins_t1_t2>0 else np.nan,
        "cluster_path_efficiency":path_eff,
        "cluster_green_rate":green,
        "cluster_close_above_tp1_rate":above,
        "cluster_max_pullback_r":max_pb,
        "cluster_mae_from_tp1_r":mae,
        "last1_progress_r":last1,
        "last3_progress_r":last3,
        "last3_green_rate":last3g,
        "distance_remaining_tp2_r":remain,
        "tp2_accept":bool(float(b.close)>=tp2),
        "tp2_close_above_r":(float(b.close)-tp2)/risk,
        "tp2_bar_body_r":(float(b.close)-float(b.open))/risk,
        "tp2_bar_range_r":rng/risk,
        "tp2_close_location":cloc,
    }

def robust_effect(q,feature):
    a=pd.to_numeric(q.loc[q.label=="EXPANDER",feature],errors="coerce").dropna()
    b=pd.to_numeric(q.loc[q.label=="STOPPER",feature],errors="coerce").dropna()
    allx=pd.to_numeric(q[feature],errors="coerce").dropna()
    if not len(a) or not len(b) or len(allx)<4:return np.nan,np.nan,np.nan
    iqr=float(allx.quantile(.75)-allx.quantile(.25))
    ma=float(a.median()); mb=float(b.median())
    eff=(ma-mb)/iqr if iqr>0 else np.nan
    return ma,mb,eff

def binary_effect(q,feature):
    a=q.loc[q.label=="EXPANDER",feature]
    b=q.loc[q.label=="STOPPER",feature]
    if not len(a) or not len(b):return np.nan,np.nan,np.nan
    ma=float(a.astype(float).mean()); mb=float(b.astype(float).mean())
    return ma,mb,ma-mb

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
    raw5,m15,h1,P,sig=s14.build_frozen(raw,end)
    if sig!=EXPECTED_SIGNATURE: raise RuntimeError(f"signature drift {sig}")

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=pd.Timestamp("2022-01-01T00:00:00Z"))&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    F=fam.set_index("zone_id")

    structs=[]
    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        rec=s18.reconstruct_e2(m15,fr,end)
        if rec is None or pd.Timestamp(rec["entry_ts"])!=pd.Timestamp(r.entry_ts):
            raise RuntimeError(f"E2 reconstruction drift {r.zone_id}")
        structs.append({
            "zone_id":r.zone_id,
            "reclaim_close":float(m15.close.iloc[rec["reclaim_i"]]),
        })
    P=P.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    P["is_wide_q4"]=P.baseline_sl_pct>WIDE_CUT

    # Freeze S20 early-cut status.
    cut=[]
    for r in P.itertuples(index=False):
        is_cut=False; cut_ts=pd.NaT
        if bool(r.is_wide_q4):
            z=s20.eval_5m_signal(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),
                                 float(r.tp1),float(r.reclaim_close),"CLOSE_BELOW",end)
            if z["signal_status"]=="CLEAN_SIGNAL":
                is_cut=True; cut_ts=z["signal_ts"]
        cut.append({"zone_id":r.zone_id,"s20_cut":is_cut,"s20_cut_ts":cut_ts})
    P=P.merge(pd.DataFrame(cut),on="zone_id",how="left",validate="one_to_one")

    # Expansion population: S20 survivor + causal TP2 + TP2 hit before original SL.
    pop=[]
    for r in P.itertuples(index=False):
        if bool(r.s20_cut): continue
        if not np.isfinite(r.tp2) or not (float(r.tp2)>float(r.tp1)): continue
        tp1_i=first_touch_idx(raw5,r.entry_ts,float(r.tp1),"HIGH",end)
        tp2_i=first_touch_idx(raw5,r.entry_ts,float(r.tp2),"HIGH",end)
        sl_i=first_touch_idx(raw5,r.entry_ts,float(r.touch_low_sl),"LOW",end)
        if tp1_i is None or tp2_i is None: continue
        if sl_i is not None and not (tp2_i<sl_i): continue
        if tp1_i>tp2_i: raise RuntimeError(f"target ordering drift {r.zone_id}")

        fr=feature_row(raw5,r,tp1_i,tp2_i)
        pop.append({**r._asdict(),**fr,"tp1_idx":tp1_i,"tp2_idx":tp2_i,"sl_idx":sl_i})
    Q=pd.DataFrame(pop)
    if not len(Q): raise RuntimeError("empty expansion population")

    # Target-level label ledger.
    rows=[]
    idx=raw5.index
    for r in Q.itertuples(index=False):
        risk=float(r.entry_price-r.touch_low_sl)
        for target in TARGETS:
            lvl=target_level(r,target)
            if not np.isfinite(lvl) or not (lvl>float(r.tp2)+1e-12):
                continue
            room=(lvl-float(r.tp2))/risk

            # first target touch after entry; because lvl>TP2, same index means rapid same-bar expansion
            ti=first_touch_idx(raw5,r.entry_ts,lvl,"HIGH",end)
            far_before=ti is not None and ti<=int(r.tp2_idx)

            if far_before:
                label="FAR_BEFORE_DECISION"
                resolution_ts=idx[ti]
                minutes_after=0.0
            else:
                ti2=first_touch_idx(raw5,r.tp2_touch_ts,lvl,"HIGH",end)
                si2=first_touch_idx(raw5,r.tp2_touch_ts,float(r.touch_low_sl),"LOW",end)
                if ti2 is not None and si2 is not None and ti2==si2:
                    label="AMBIGUOUS"
                    resolution_ts=idx[ti2]; minutes_after=np.nan
                elif ti2 is not None and (si2 is None or ti2<si2):
                    label="EXPANDER"
                    resolution_ts=idx[ti2]
                    minutes_after=float((resolution_ts-pd.Timestamp(r.tp2_touch_ts))/pd.Timedelta(minutes=1))
                elif si2 is not None:
                    label="STOPPER"
                    resolution_ts=idx[si2]; minutes_after=np.nan
                else:
                    label="UNRESOLVED"; resolution_ts=pd.NaT; minutes_after=np.nan

            row={
                "zone_id":r.zone_id,"period":r.period,"year":r.year,"target":target,
                "label":label,"target_level":lvl,"objective_room_from_tp2_r":room,
                "resolution_ts":resolution_ts,"minutes_tp2_to_far":minutes_after,
            }
            for f in NUM_FEATURES:
                if f=="objective_room_from_tp2_r": row[f]=room
                else: row[f]=getattr(r,f)
            for f in BIN_FEATURES: row[f]=getattr(r,f)
            rows.append(row)
    L=pd.DataFrame(rows)

    # Target baseline.
    TB=[]
    for per in ["DEV","REF"]:
        for target in TARGETS:
            q=L[(L.period==per)&(L.target==target)]
            if not len(q): continue
            pre=q[q.label=="FAR_BEFORE_DECISION"]
            post=q[q.label.isin(["EXPANDER","STOPPER"])]
            ex=post[post.label=="EXPANDER"]; st=post[post.label=="STOPPER"]
            TB.append({
                "period":per,"target":target,"available":len(q),
                "far_before_decision":len(pre),
                "far_before_decision_rate":len(pre)/len(q),
                "post_decision_resolved":len(post),
                "expanders":len(ex),"stoppers":len(st),
                "post_decision_expansion_rate":len(ex)/len(post) if len(post) else np.nan,
                "median_room_from_tp2_r":float(q.objective_room_from_tp2_r.median()),
                "median_minutes_tp2_to_far":float(ex.minutes_tp2_to_far.median()) if len(ex) else np.nan,
                "ambiguous":int((q.label=="AMBIGUOUS").sum()),
                "unresolved":int((q.label=="UNRESOLVED").sum()),
            })
    TB=pd.DataFrame(TB)

    # Feature comparison target-by-target.
    FC=[]
    for target in TARGETS:
        for feature in NUM_FEATURES+BIN_FEATURES:
            vals={}
            for per in ["DEV","REF"]:
                q=L[(L.target==target)&(L.period==per)&(L.label.isin(["EXPANDER","STOPPER"]))]
                if feature in BIN_FEATURES:
                    me,ms,eff=binary_effect(q,feature)
                else:
                    me,ms,eff=robust_effect(q,feature)
                vals[per]=(me,ms,eff,len(q))
            de=vals["DEV"][2]; re=vals["REF"][2]
            consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            score=min(abs(de),abs(re)) if consistent else 0.0
            FC.append({
                "target":target,"feature":feature,
                "dev_expander":vals["DEV"][0],"dev_stopper":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_expander":vals["REF"][0],"ref_stopper":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":consistent,"robust_score":score,
            })
    FC=pd.DataFrame(FC)
    RANK=FC.sort_values(["target","direction_consistent","robust_score"],ascending=[True,False,False]).copy()

    # DEV quartile cuts and unchanged REF band audit.
    CUT=[]; BA=[]
    for target in TARGETS:
        dev=L[(L.target==target)&(L.period=="DEV")&(L.label.isin(["EXPANDER","STOPPER"]))]
        for feature in NUM_FEATURES:
            x=pd.to_numeric(dev[feature],errors="coerce").dropna()
            if len(x)<8: continue
            c1=float(x.quantile(.25)); c2=float(x.quantile(.50)); c3=float(x.quantile(.75))
            CUT.append({"target":target,"feature":feature,"q25":c1,"q50":c2,"q75":c3,"dev_n":len(x)})
            for per in ["DEV","REF"]:
                q=L[(L.target==target)&(L.period==per)&(L.label.isin(["EXPANDER","STOPPER"]))].copy()
                q["_x"]=pd.to_numeric(q[feature],errors="coerce")
                q=q[np.isfinite(q._x)].copy()
                q["band"]=[band_name(float(v),c1,c2,c3) for v in q._x]
                for band in ["Q1","Q2","Q3","Q4"]:
                    z=q[q.band==band]
                    if not len(z): continue
                    BA.append({
                        "target":target,"feature":feature,"period":per,"band":band,
                        "n":len(z),"expanders":int((z.label=="EXPANDER").sum()),
                        "expansion_rate":float((z.label=="EXPANDER").mean()),
                    })
    CUT=pd.DataFrame(CUT); BA=pd.DataFrame(BA)

    # Population census.
    census=[]
    for per in ["DEV","REF"]:
        pp=P[P.period==per]; qq=Q[Q.period==per]
        census.append({
            "period":per,"all_e2":len(pp),
            "s20_cut":int(pp.s20_cut.sum()),
            "s20_survivors":int((~pp.s20_cut).sum()),
            "tp2_cluster_survivors":len(qq),
        })
    C=pd.DataFrame(census)

    Q.to_csv(ROOT/f"{PFX}_Population.csv.gz",index=False,compression="gzip")
    L.to_csv(ROOT/f"{PFX}_TargetLedger.csv.gz",index=False,compression="gzip")
    TB.to_csv(ROOT/f"{PFX}_TargetBaseline.csv",index=False)
    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    RANK.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    BA.to_csv(ROOT/f"{PFX}_BandAudit.csv",index=False)
    C.to_csv(ROOT/f"{PFX}_Census.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\n"
        "S20_FAILURE=CLOSE5_BELOW_RECLAIM_CLOSE\nDECISION=TP2_TOUCH_5M_BAR_CLOSE\n",
        encoding="utf-8"
    )

    lines=[
      "# BNB B38-S22 — Post-Cluster Far Expansion Character","",
      f"Frozen E2 signature: `{sig}`","",
      "S20 downside layer is frozen. Expansion decision is available only at the close of the first 5m TP2-touch bar.","",
      "## Expansion population census","",
      "| Period | All E2 | S20 cut | S20 survivors | Reached TP2 cluster |",
      "|---|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(f"| {r.period} | {r.all_e2} | {r.s20_cut} | {r.s20_survivors} | {r.tp2_cluster_survivors} |")

    lines += ["","## Far-objective baseline after TP2","",
      "| Period | Objective | Available | Far before decision | Post-decision E-S | Expansion rate | Med room beyond TP2 | Med TP2→far |",
      "|---|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in TB.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.target} | {r.available} | {r.far_before_decision} ({fmt_pct(r.far_before_decision_rate)}) | "
            f"{r.expanders}-{r.stoppers} | {fmt_pct(r.post_decision_expansion_rate)} | "
            f"{fmt_num(r.median_room_from_tp2_r)}R | {fmt_num(r.median_minutes_tp2_to_far,1)}m |"
        )

    lines += ["","## Strongest directionally consistent features by objective","",
      "| Objective | Feature | DEV effect | REF effect | DEV E/S med | REF E/S med |",
      "|---|---|---:|---:|---:|---:|"
    ]
    for target in TARGETS:
        q=RANK[(RANK.target==target)&(RANK.direction_consistent)].head(8)
        for r in q.itertuples(index=False):
            lines.append(
                f"| {r.target} | {r.feature} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
                f"{fmt_num(r.dev_expander)}/{fmt_num(r.dev_stopper)} | {fmt_num(r.ref_expander)}/{fmt_num(r.ref_stopper)} |"
            )

    lines += ["","## Interpretation boundary",
      "S22 discovers post-cluster expansion character only.",
      "Far objectives already reached on the TP2-touch bar are explicitly marked as too fast for a decision made at TP2 close.",
      "No adaptive TP, runner sizing, or threshold is promoted in this stage."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S22_POST_CLUSTER_FAR_EXPANSION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
