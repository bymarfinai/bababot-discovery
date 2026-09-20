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
import bnb_b38_s23_adaptive_major_runner as s23

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S24_MAJOR_RUNNER_FAILURE_AUDIT"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727
MAJOR_ROOM_CUT_R=0.30105633802816506

NUM_FEATURES=[
    "major_room_from_tp2_r","tp1_r","tp2_r","tp1_to_tp2_gap_r","room_tp1_to_major_r",
    "known_target_count","minutes_entry_to_tp1","pre_tp1_path_efficiency","pre_tp1_green_rate",
    "pre_tp1_max_pullback_r","pre_tp1_mae_r","last1_progress_r","last3_progress_r","last3_green_rate",
    "tp1_close_above_r","tp1_bar_body_r","tp1_bar_range_r","tp1_close_location",
    "baseline_sl_pct",
]
BIN_FEATURES=["tp1_accept","is_wide_q4"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def robust_effect(q,feature):
    a=pd.to_numeric(q.loc[q.label=="HIT",feature],errors="coerce").dropna()
    b=pd.to_numeric(q.loc[q.label=="BE",feature],errors="coerce").dropna()
    allx=pd.to_numeric(q[feature],errors="coerce").dropna()
    if not len(a) or not len(b) or len(allx)<4:return np.nan,np.nan,np.nan
    iqr=float(allx.quantile(.75)-allx.quantile(.25))
    ma=float(a.median()); mb=float(b.median())
    eff=(ma-mb)/iqr if iqr>0 else np.nan
    return ma,mb,eff

def binary_effect(q,feature):
    a=q.loc[q.label=="HIT",feature].astype(float)
    b=q.loc[q.label=="BE",feature].astype(float)
    if not len(a) or not len(b):return np.nan,np.nan,np.nan
    ma=float(a.mean()); mb=float(b.mean())
    return ma,mb,ma-mb

def band_name(x,c1,c2,c3):
    if not np.isfinite(x): return "NA"
    if x<=c1:return "Q1"
    if x<=c2:return "Q2"
    if x<=c3:return "Q3"
    return "Q4"

def first_tp1_idx(raw5,entry_ts,tp1,end):
    idx=raw5.index
    i0=int(idx.searchsorted(entry_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    a=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(a>=tp1)
    return i0+int(z[0]) if len(z) else None

def feature_row(raw5,r,tp1_i):
    idx=raw5.index
    entry=float(r.entry_price); sl=float(r.touch_low_sl); risk=entry-sl
    tp1=float(r.tp1); tp2=float(r.tp2); major=float(r.major_nearest)
    t1=idx[tp1_i]

    start_i=int(idx.searchsorted(pd.Timestamp(r.entry_ts),side="right"))
    pre=raw5.iloc[start_i:tp1_i].copy()

    if len(pre)>=2:
        closes=pre.close.to_numpy(float)
        denom=float(np.abs(np.diff(closes)).sum())
        path=(float(closes[-1])-float(closes[0]))/denom if denom>0 else np.nan
    else:
        path=np.nan

    green=float((pre.close>pre.open).mean()) if len(pre) else np.nan
    mae=(float(pre.low.min())-entry)/risk if len(pre) else np.nan

    max_pb=np.nan
    if len(pre):
        run=-np.inf; m=0.0
        for h,l in zip(pre.high.to_numpy(float),pre.low.to_numpy(float)):
            run=max(run,float(h))
            m=max(m,run-float(l))
        max_pb=m/risk

    last1=np.nan; last3=np.nan; last3g=np.nan
    if len(pre)>=2:
        last1=(float(pre.close.iloc[-1])-float(pre.close.iloc[-2]))/risk
    if len(pre)>=4:
        last3=(float(pre.close.iloc[-1])-float(pre.close.iloc[-4]))/risk
        q=pre.iloc[-3:]
        last3g=float((q.close>q.open).mean())

    b=raw5.iloc[tp1_i]
    rng=float(b.high-b.low)
    cloc=float((b.close-b.low)/rng) if rng>0 else np.nan

    return {
        "tp1_touch_ts":t1,
        "major_room_from_tp2_r":(major-tp2)/risk,
        "tp1_r":(tp1-entry)/risk,
        "tp2_r":(tp2-entry)/risk,
        "tp1_to_tp2_gap_r":(tp2-tp1)/risk,
        "room_tp1_to_major_r":(major-tp1)/risk,
        "known_target_count":float(r.known_target_count),
        "minutes_entry_to_tp1":float((t1-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)),
        "pre_tp1_path_efficiency":path,
        "pre_tp1_green_rate":green,
        "pre_tp1_max_pullback_r":max_pb,
        "pre_tp1_mae_r":mae,
        "last1_progress_r":last1,
        "last3_progress_r":last3,
        "last3_green_rate":last3g,
        "tp1_accept":bool(float(b.close)>=tp1),
        "tp1_close_above_r":(float(b.close)-tp1)/risk,
        "tp1_bar_body_r":(float(b.close)-float(b.open))/risk,
        "tp1_bar_range_r":rng/risk,
        "tp1_close_location":cloc,
        "baseline_sl_pct":float(r.baseline_sl_pct),
        "is_wide_q4":bool(r.is_wide_q4),
    }

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
            raise RuntimeError(f"E2 reconstruct drift {r.zone_id}")
        structs.append({"zone_id":r.zone_id,"reclaim_close":float(m15.close.iloc[rec["reclaim_i"]])})
    P=P.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    P["is_wide_q4"]=P.baseline_sl_pct>WIDE_CUT
    P["major_room_from_tp2_r"]=np.where(
        np.isfinite(P.major_nearest)&np.isfinite(P.tp2)&(P.major_nearest>P.tp2),
        (P.major_nearest-P.tp2)/(P.entry_price-P.touch_low_sl),np.nan
    )
    P["major_runner_eligible"]=(
        np.isfinite(P.tp2)&(P.tp2>P.tp1)&
        np.isfinite(P.major_nearest)&(P.major_nearest>P.tp2)&
        np.isfinite(P.major_room_from_tp2_r)&
        (P.major_room_from_tp2_r<=MAJOR_ROOM_CUT_R)
    )

    # S20 cut status.
    cut=[]
    for r in P.itertuples(index=False):
        c=False
        if bool(r.is_wide_q4):
            z=s20.eval_5m_signal(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),
                                 float(r.tp1),float(r.reclaim_close),"CLOSE_BELOW",end)
            c=z["signal_status"]=="CLEAN_SIGNAL"
        cut.append({"zone_id":r.zone_id,"s20_cut":c})
    P=P.merge(pd.DataFrame(cut),on="zone_id",how="left",validate="one_to_one")

    rows=[]
    for r in P.itertuples(index=False):
        if not bool(r.major_runner_eligible): continue
        if bool(r.s20_cut): continue
        if r.baseline_outcome!="WIN": continue

        t1=first_tp1_idx(raw5,r.entry_ts,float(r.tp1),end)
        if t1 is None: raise RuntimeError(f"TP1 missing {r.zone_id}")
        status,rt,rr=s23.runner_resolve(
            raw5,raw5.index[t1],float(r.entry_price),float(r.touch_low_sl),
            float(r.tp1),float(r.major_nearest),end
        )
        if status in ("MAJOR_SAME_TP1_BAR","MAJOR_HIT"): label="HIT"
        elif status=="BE_EXIT": label="BE"
        elif status=="AMBIGUOUS_SAME_BAR": label="AMBIGUOUS"
        elif status=="PARTIAL_OPEN": label="OPEN"
        else: raise RuntimeError(status)

        f=feature_row(raw5,r,t1)
        rows.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "runner_status":status,"label":label,"runner_realized_r":rr,
            **f
        })
    L=pd.DataFrame(rows)

    # Hard parity to exact S23 promoted TP1 runner cohort.
    got={
        "DEV_N":int((L.period=="DEV").sum()),
        "DEV_HIT":int(((L.period=="DEV")&(L.label=="HIT")).sum()),
        "DEV_BE":int(((L.period=="DEV")&(L.label=="BE")).sum()),
        "DEV_AMB":int(((L.period=="DEV")&(L.label=="AMBIGUOUS")).sum()),
        "REF_N":int((L.period=="REF").sum()),
        "REF_HIT":int(((L.period=="REF")&(L.label=="HIT")).sum()),
        "REF_BE":int(((L.period=="REF")&(L.label=="BE")).sum()),
        "REF_AMB":int(((L.period=="REF")&(L.label=="AMBIGUOUS")).sum()),
    }
    exp={"DEV_N":90,"DEV_HIT":44,"DEV_BE":43,"DEV_AMB":3,
         "REF_N":56,"REF_HIT":21,"REF_BE":34,"REF_AMB":1}
    if got!=exp: raise RuntimeError(f"S23 runner parity drift got={got} expected={exp}")

    BASE=[]
    for per in ["DEV","REF"]:
        q=L[L.period==per]
        BASE.append({
            "period":per,"runner_n":len(q),
            "hits":int((q.label=="HIT").sum()),"be":int((q.label=="BE").sum()),
            "ambiguous":int((q.label=="AMBIGUOUS").sum()),"open":int((q.label=="OPEN").sum()),
            "hit_rate_ex_amb":float((q.label=="HIT").sum()/q.label.isin(["HIT","BE"]).sum())
        })
    BASE=pd.DataFrame(BASE)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=L[L.year==y]
        if len(q):
            den=int(q.label.isin(["HIT","BE"]).sum())
            Y.append({
                "year":y,"runner_n":len(q),"hits":int((q.label=="HIT").sum()),
                "be":int((q.label=="BE").sum()),"ambiguous":int((q.label=="AMBIGUOUS").sum()),
                "hit_rate_ex_amb":int((q.label=="HIT").sum())/den if den else np.nan,
                "runner_total_r":float(q.runner_realized_r.sum())
            })
    Y=pd.DataFrame(Y)

    FC=[]
    for feature in NUM_FEATURES+BIN_FEATURES:
        vals={}
        for per in ["DEV","REF"]:
            q=L[(L.period==per)&L.label.isin(["HIT","BE"])]
            if feature in BIN_FEATURES:
                mh,mb,eff=binary_effect(q,feature)
            else:
                mh,mb,eff=robust_effect(q,feature)
            vals[per]=(mh,mb,eff,len(q))
        de=vals["DEV"][2]; re=vals["REF"][2]
        consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
        score=min(abs(de),abs(re)) if consistent else 0.0
        FC.append({
            "feature":feature,
            "dev_hit":vals["DEV"][0],"dev_be":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
            "ref_hit":vals["REF"][0],"ref_be":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
            "direction_consistent":consistent,"robust_score":score
        })
    FC=pd.DataFrame(FC)
    RANK=FC.sort_values(["direction_consistent","robust_score"],ascending=[False,False]).copy()

    CUT=[]; BA=[]
    dev=L[(L.period=="DEV")&L.label.isin(["HIT","BE"])]
    for feature in NUM_FEATURES:
        x=pd.to_numeric(dev[feature],errors="coerce").dropna()
        if len(x)<8: continue
        c1=float(x.quantile(.25)); c2=float(x.quantile(.50)); c3=float(x.quantile(.75))
        CUT.append({"feature":feature,"q25":c1,"q50":c2,"q75":c3,"dev_n":len(x)})
        for scope, q0 in [
            ("DEV",L[(L.period=="DEV")&L.label.isin(["HIT","BE"])]),
            ("REF",L[(L.period=="REF")&L.label.isin(["HIT","BE"])]),
            ("2025",L[(L.year==2025)&L.label.isin(["HIT","BE"])]),
            ("2026",L[(L.year==2026)&L.label.isin(["HIT","BE"])])
        ]:
            q=q0.copy()
            q["_x"]=pd.to_numeric(q[feature],errors="coerce")
            q=q[np.isfinite(q._x)].copy()
            q["band"]=[band_name(float(v),c1,c2,c3) for v in q._x]
            for band in ["Q1","Q2","Q3","Q4"]:
                z=q[q.band==band]
                if not len(z): continue
                den=int(z.label.isin(["HIT","BE"]).sum())
                BA.append({
                    "scope":scope,"feature":feature,"band":band,"n":len(z),
                    "hits":int((z.label=="HIT").sum()),
                    "hit_rate":int((z.label=="HIT").sum())/den if den else np.nan
                })
    CUT=pd.DataFrame(CUT); BA=pd.DataFrame(BA)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    BASE.to_csv(ROOT/f"{PFX}_Baseline.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    RANK.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    BA.to_csv(ROOT/f"{PFX}_BandAudit.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\n"
        f"MAJOR_ROOM_CUT_R={MAJOR_ROOM_CUT_R:.17f}\nS23_RUNNER_PARITY={got}\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S24 — Major Runner Failure Character Audit","",
        f"Frozen E2 signature: `{sig}`","",
        "## Runner baseline","",
        "| Period | Runner N | HIT | BE | Amb | Hit rate ex-amb |",
        "|---|---:|---:|---:|---:|---:|"
    ]
    for r in BASE.itertuples(index=False):
        lines.append(f"| {r.period} | {r.runner_n} | {r.hits} | {r.be} | {r.ambiguous} | {fmt_pct(r.hit_rate_ex_amb)} |")

    lines += ["","## Year anatomy","",
        "| Year | Runner N | HIT | BE | Amb | Hit rate | Runner total R |",
        "|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(f"| {r.year} | {r.runner_n} | {r.hits} | {r.be} | {r.ambiguous} | {fmt_pct(r.hit_rate_ex_amb)} | {fmt_num(r.runner_total_r)}R |")

    lines += ["","## Strongest directionally consistent pre-runner features","",
        "| Feature | DEV effect | REF effect | DEV HIT/BE med | REF HIT/BE med |",
        "|---|---:|---:|---:|---:|"
    ]
    for r in RANK[RANK.direction_consistent].head(12).itertuples(index=False):
        lines.append(
            f"| {r.feature} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
            f"{fmt_num(r.dev_hit)}/{fmt_num(r.dev_be)} | {fmt_num(r.ref_hit)}/{fmt_num(r.ref_be)} |"
        )

    lines += ["","## Interpretation boundary",
      "S24 is diagnostic only and does not modify S23.",
      "2026 is evaluated only after DEV cuts are frozen.",
      "A skip filter requires a separate preregistered S25 validation."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S24_MAJOR_RUNNER_FAILURE_AUDIT_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
