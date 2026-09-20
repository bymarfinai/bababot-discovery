#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s14_post_tp1_continuation as s14
import bnb_b38_s18_wide_sl_structural_invalidation as s18
import bnb_b38_s20_post_entry_failure_character as s20

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S23_ADAPTIVE_MAJOR_RUNNER"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727
MAJOR_ROOM_CUT_R=0.30105633802816506
CONFIGS=["BASELINE_TP1","S20_IMMEDIATE","S23_ADAPTIVE_MAJOR_50_50_BE"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def first_touch_idx(raw5,start_ts,level,kind,end,side="right"):
    if not np.isfinite(level): return None
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side=side))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def maxdd(rs):
    if not len(rs): return np.nan
    a=np.asarray(rs,float)
    c=np.cumsum(a)
    peaks=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(peaks-c))

def maxls(vals):
    cur=mx=0
    for x in vals:
        if x<0:
            cur+=1; mx=max(mx,cur)
        else:
            cur=0
    return mx

def summarize(q,base_s20=None):
    q=q.sort_values(["entry_ts","zone_id"]).copy()
    pos=q[q.realized_r>0]
    neg=q[q.realized_r<0]
    pf=float(pos.realized_r.sum())/abs(float(neg.realized_r.sum())) if len(neg) else (np.inf if len(pos) else np.nan)
    out={
        "trades":len(q),
        "positive":len(pos),
        "negative":len(neg),
        "zero":int((q.realized_r==0).sum()),
        "positive_rate":len(pos)/len(q) if len(q) else np.nan,
        "median_positive_r":float(pos.realized_r.median()) if len(pos) else np.nan,
        "expectancy_r":float(q.realized_r.mean()) if len(q) else np.nan,
        "total_r":float(q.realized_r.sum()) if len(q) else np.nan,
        "profit_factor":pf,
        "max_drawdown_r":maxdd(q.realized_r.tolist()) if len(q) else np.nan,
        "max_loss_streak":maxls(q.realized_r.tolist()),
        "promoted":int(q.major_runner_eligible.sum()) if "major_runner_eligible" in q else 0,
        "promoted_share":float(q.major_runner_eligible.mean()) if "major_runner_eligible" in q and len(q) else np.nan,
        "promoted_tp1_reached":int(((q.major_runner_eligible)&(q.tp1_reached)).sum()) if "tp1_reached" in q else 0,
        "runner_major_hit":int((q.runner_status=="MAJOR_HIT").sum()) if "runner_status" in q else 0,
        "runner_be":int((q.runner_status=="BE_EXIT").sum()) if "runner_status" in q else 0,
        "runner_ambiguous":int((q.runner_status=="AMBIGUOUS_SAME_BAR").sum()) if "runner_status" in q else 0,
        "runner_partial_open":int((q.runner_status=="PARTIAL_OPEN").sum()) if "runner_status" in q else 0,
        "runner_same_tp1_bar_major":int((q.runner_status=="MAJOR_SAME_TP1_BAR").sum()) if "runner_status" in q else 0,
    }
    if base_s20 is not None:
        b=base_s20.set_index("zone_id").realized_r
        qq=q.set_index("zone_id")
        common=qq.index.intersection(b.index)
        sv=b.loc[common]
        nv=qq.loc[common,"realized_r"]
        out["s20_positive"]=int((sv>0).sum())
        out["s20_positive_retained"]=int(((sv>0)&(nv>0)).sum())
        out["s20_positive_to_negative"]=int(((sv>0)&(nv<0)).sum())
        out["s20_negative_to_positive"]=int(((sv<0)&(nv>0)).sum())
        out["incremental_r_vs_s20"]=float(nv.sum()-sv.sum())
    else:
        out["s20_positive"]=np.nan
        out["s20_positive_retained"]=np.nan
        out["s20_positive_to_negative"]=np.nan
        out["s20_negative_to_positive"]=np.nan
        out["incremental_r_vs_s20"]=np.nan
    return out

def runner_resolve(raw5,tp1_ts,entry,sl,tp1,major,end):
    idx=raw5.index
    risk=entry-sl
    tp1_r=(tp1-entry)/risk
    major_r=(major-entry)/risk
    partial=0.5*tp1_r

    i=int(idx.get_loc(pd.Timestamp(tp1_ts)))
    # Major on TP1 touch bar is reachable after crossing TP1; BE is not active yet.
    if float(raw5.high.iloc[i])>=major:
        return "MAJOR_SAME_TP1_BAR",pd.Timestamp(tp1_ts),float(partial+0.5*major_r)

    # BE protection starts strictly after TP1 touch bar.
    start=pd.Timestamp(tp1_ts)
    mi=first_touch_idx(raw5,start,major,"HIGH",end,side="right")
    bi=first_touch_idx(raw5,start,entry,"LOW",end,side="right")
    if mi is None and bi is None:
        return "PARTIAL_OPEN",pd.NaT,float(partial)
    if mi is not None and bi is not None and mi==bi:
        return "AMBIGUOUS_SAME_BAR",idx[mi],float(partial)
    if mi is not None and (bi is None or mi<bi):
        return "MAJOR_HIT",idx[mi],float(partial+0.5*major_r)
    return "BE_EXIT",idx[bi],float(partial)

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    raw5,m15,h1,P,sig=s14.build_frozen(raw,end)
    if sig!=EXPECTED_SIGNATURE: raise RuntimeError(f"signature drift {sig}")
    if int((P.period=="DEV").sum())!=440 or int((P.period=="REF").sum())!=272:
        raise RuntimeError("plan parity drift")

    # Exact E2 reclaim level reconstruction for S20.
    structs=[]
    for r in P.itertuples(index=False):
        # s14 build_frozen derives the same family used by S18 reconstruct;
        # reconstruct only needs the family row, so rebuild through S18 helper context.
        pass
    # Rebuild family once.
    import bnb_b38_s1_lower_tf_demand_rebound as s1
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
        if abs(float(rec["entry_price"])-float(r.entry_price))>1e-10:
            raise RuntimeError(f"E2 price drift {r.zone_id}")
        structs.append({
            "zone_id":r.zone_id,
            "reclaim_close":float(m15.close.iloc[rec["reclaim_i"]]),
        })
    P=P.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    P["is_wide_q4"]=P.baseline_sl_pct>WIDE_CUT

    # Freeze eligibility using only entry-known geometry.
    P["major_room_from_tp2_r"]=np.where(
        np.isfinite(P.major_nearest)&np.isfinite(P.tp2)&(P.major_nearest>P.tp2),
        (P.major_nearest-P.tp2)/(P.entry_price-P.touch_low_sl),
        np.nan
    )
    P["major_runner_eligible"]=(
        np.isfinite(P.tp2)&(P.tp2>P.tp1)&
        np.isfinite(P.major_nearest)&(P.major_nearest>P.tp2)&
        np.isfinite(P.major_room_from_tp2_r)&
        (P.major_room_from_tp2_r<=MAJOR_ROOM_CUT_R)
    )

    # Compute S20 signal once and TP1 reach flag.
    xs=[]
    for r in P.itertuples(index=False):
        s20_clean=False; s20_ts=pd.NaT; s20_r=np.nan
        if bool(r.is_wide_q4):
            z=s20.eval_5m_signal(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),
                                 float(r.tp1),float(r.reclaim_close),"CLOSE_BELOW",end)
            if z["signal_status"]=="CLEAN_SIGNAL":
                s20_clean=True; s20_ts=z["signal_ts"]
                s20_r=(float(z["exit_price"])-float(r.entry_price))/float(r.entry_price-r.touch_low_sl)
        tp1_reached=(r.baseline_outcome=="WIN")
        xs.append({
            "zone_id":r.zone_id,"s20_clean":s20_clean,"s20_ts":s20_ts,"s20_r":s20_r,
            "tp1_reached":tp1_reached,
        })
    P=P.merge(pd.DataFrame(xs),on="zone_id",how="left",validate="one_to_one")

    rows=[]
    for r in P.itertuples(index=False):
        entry=float(r.entry_price); sl=float(r.touch_low_sl); tp1=float(r.tp1)
        # baseline
        rows.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "config":"BASELINE_TP1","realized_r":float(r.baseline_realized_r),
            "major_runner_eligible":bool(r.major_runner_eligible),"tp1_reached":bool(r.tp1_reached),
            "runner_status":"NONE","resolution_ts":r.baseline_resolution_ts,
            "s20_clean":bool(r.s20_clean),"major_room_from_tp2_r":r.major_room_from_tp2_r,
        })
        # S20 immediate
        s20_real=float(r.s20_r) if bool(r.s20_clean) else float(r.baseline_realized_r)
        s20_rt=r.s20_ts if bool(r.s20_clean) else r.baseline_resolution_ts
        rows.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "config":"S20_IMMEDIATE","realized_r":s20_real,
            "major_runner_eligible":bool(r.major_runner_eligible),"tp1_reached":bool(r.tp1_reached),
            "runner_status":"NONE","resolution_ts":s20_rt,
            "s20_clean":bool(r.s20_clean),"major_room_from_tp2_r":r.major_room_from_tp2_r,
        })

        # S23: S20 cut takes precedence.
        if bool(r.s20_clean):
            real=float(r.s20_r); rt=r.s20_ts; rs="S20_CUT"
        elif r.baseline_outcome!="WIN":
            real=float(r.baseline_realized_r); rt=r.baseline_resolution_ts; rs="NO_TP1"
        elif not bool(r.major_runner_eligible):
            real=float(r.baseline_realized_r); rt=r.baseline_resolution_ts; rs="NOT_PROMOTED"
        else:
            rs,rt,real=runner_resolve(
                raw5,pd.Timestamp(r.baseline_resolution_ts),entry,sl,tp1,float(r.major_nearest),end
            )

        rows.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "config":"S23_ADAPTIVE_MAJOR_50_50_BE","realized_r":float(real),
            "major_runner_eligible":bool(r.major_runner_eligible),"tp1_reached":bool(r.tp1_reached),
            "runner_status":rs,"resolution_ts":rt,
            "s20_clean":bool(r.s20_clean),"major_room_from_tp2_r":r.major_room_from_tp2_r,
        })

    L=pd.DataFrame(rows)

    # Hard parity: S20 result must reproduce prior totals.
    chk=L[L.config=="S20_IMMEDIATE"]
    dev=float(chk[chk.period=="DEV"].realized_r.sum())
    ref=float(chk[chk.period=="REF"].realized_r.sum())
    if abs(dev-20.477668670966324)>1e-9 or abs(ref-1.4048249469810346)>1e-9:
        raise RuntimeError(f"S20 parity drift DEV={dev} REF={ref}")

    SUM=[]
    for per in ["DEV","REF"]:
        base20=L[(L.period==per)&(L.config=="S20_IMMEDIATE")][["zone_id","realized_r"]]
        for cfg in CONFIGS:
            q=L[(L.period==per)&(L.config==cfg)]
            SUM.append({"period":per,"config":cfg,**summarize(q,base20 if cfg=="S23_ADAPTIVE_MAJOR_50_50_BE" else None)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        base20=L[(L.year==y)&(L.config=="S20_IMMEDIATE")][["zone_id","realized_r"]]
        for cfg in CONFIGS:
            q=L[(L.year==y)&(L.config==cfg)]
            if len(q):
                Y.append({"year":y,"config":cfg,**summarize(q,base20 if cfg=="S23_ADAPTIVE_MAJOR_50_50_BE" else None)})
    Y=pd.DataFrame(Y)

    # Promoted cohort detail under S23.
    PC=[]
    q=L[(L.config=="S23_ADAPTIVE_MAJOR_50_50_BE")&L.major_runner_eligible]
    for per in ["DEV","REF"]:
        z=q[q.period==per]
        PC.append({
            "period":per,"eligible":len(z),
            "s20_cut_before_tp1":int((z.runner_status=="S20_CUT").sum()),
            "no_tp1":int((z.runner_status=="NO_TP1").sum()),
            "tp1_promoted":int(z.runner_status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT","BE_EXIT","AMBIGUOUS_SAME_BAR","PARTIAL_OPEN"]).sum()),
            "major_hit":int(z.runner_status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT"]).sum()),
            "be_exit":int((z.runner_status=="BE_EXIT").sum()),
            "ambiguous":int((z.runner_status=="AMBIGUOUS_SAME_BAR").sum()),
            "partial_open":int((z.runner_status=="PARTIAL_OPEN").sum()),
            "median_room_r":float(z.major_room_from_tp2_r.median()) if len(z) else np.nan,
            "total_r":float(z.realized_r.sum()) if len(z) else np.nan,
        })
    PC=pd.DataFrame(PC)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    PC.to_csv(ROOT/f"{PFX}_PromotedCohort.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\n"
        f"S20_FAILURE=CLOSE5_BELOW_RECLAIM_CLOSE\nMAJOR_ROOM_CUT_R={MAJOR_ROOM_CUT_R:.17f}\n"
        "RUNNER_SPLIT=0.5_TP1_0.5_MAJOR\nRUNNER_STOP=BE_FROM_NEXT_5M_BAR\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S23 — Adaptive Major Runner Economics","",
        f"Frozen E2 signature: `{sig}`",
        f"Frozen Major-room cut: `<= {MAJOR_ROOM_CUT_R:.15f}R`","",
        "## Overall economics","",
        "| Period | Config | + / - / 0 | Positive rate | Med +R | Exp | Total R | PF | Max DD | Max L | ΔR vs S20 | S20 + retained |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        inc=fmt_num(r.incremental_r_vs_s20) if np.isfinite(r.incremental_r_vs_s20) else "—"
        ret=(f"{int(r.s20_positive_retained)}/{int(r.s20_positive)}" if np.isfinite(r.s20_positive) else "—")
        lines.append(
            f"| {r.period} | {r.config} | {r.positive}/{r.negative}/{r.zero} | {fmt_pct(r.positive_rate)} | "
            f"{fmt_num(r.median_positive_r)}R | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.profit_factor)} | {fmt_num(r.max_drawdown_r)}R | {r.max_loss_streak} | {inc}R | {ret} |"
        )

    lines += ["","## Promoted cohort","",
        "| Period | Eligible | S20 cut | No TP1 | TP1 promoted | Major hit | BE | Ambig | Open | Median room | Cohort total R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in PC.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.eligible} | {r.s20_cut_before_tp1} | {r.no_tp1} | {r.tp1_promoted} | "
            f"{r.major_hit} | {r.be_exit} | {r.ambiguous} | {r.partial_open} | "
            f"{fmt_num(r.median_room_r)}R | {fmt_num(r.total_r)}R |"
        )

    lines += ["","## Annual S23 stability","",
        "| Year | Config | Exp | Total R | + / - | ΔR vs S20 |",
        "|---:|---|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        inc=fmt_num(r.incremental_r_vs_s20) if np.isfinite(r.incremental_r_vs_s20) else "—"
        lines.append(
            f"| {r.year} | {r.config} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{r.positive}/{r.negative} | {inc}R |"
        )

    lines += ["","## Interpretation boundary",
      "S23 validates one frozen adaptive Major-runner policy only.",
      "No alternate room cut, split ratio, stop rule, or target is selected from this result.",
      "REF must support the same unchanged policy before promotion."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S23_ADAPTIVE_MAJOR_RUNNER_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
