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
import bnb_b38_s24_major_runner_failure_audit as s24

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S25_WEAK_TP1_BODY_SKIP"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727
MAJOR_ROOM_CUT_R=0.30105633802816506
TP1_BODY_Q25_R=0.016161308565709815

CONFIGS=[
    "BASELINE_TP1",
    "S20_IMMEDIATE",
    "S23_ADAPTIVE_MAJOR_50_50_BE",
    "S25_SKIP_WEAK_TP1_BODY",
]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

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

def summarize(q,base_s20=None,base_s23=None):
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
    }
    if base_s20 is not None:
        b=base_s20.set_index("zone_id").realized_r
        qq=q.set_index("zone_id")
        ids=qq.index.intersection(b.index)
        out["incremental_r_vs_s20"]=float(qq.loc[ids,"realized_r"].sum()-b.loc[ids].sum())
    else:
        out["incremental_r_vs_s20"]=np.nan
    if base_s23 is not None:
        b=base_s23.set_index("zone_id").realized_r
        qq=q.set_index("zone_id")
        ids=qq.index.intersection(b.index)
        sv=b.loc[ids]; nv=qq.loc[ids,"realized_r"]
        out["incremental_r_vs_s23"]=float(nv.sum()-sv.sum())
        out["s23_positive"]=int((sv>0).sum())
        out["s23_positive_retained"]=int(((sv>0)&(nv>0)).sum())
        out["s23_positive_to_negative"]=int(((sv>0)&(nv<0)).sum())
        out["s23_negative_to_positive"]=int(((sv<0)&(nv>0)).sum())
    else:
        out["incremental_r_vs_s23"]=np.nan
        out["s23_positive"]=np.nan
        out["s23_positive_retained"]=np.nan
        out["s23_positive_to_negative"]=np.nan
        out["s23_negative_to_positive"]=np.nan
    return out

def first_tp1_idx(raw5,entry_ts,tp1,end):
    idx=raw5.index
    i0=int(idx.searchsorted(entry_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    a=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(a>=tp1)
    return i0+int(z[0]) if len(z) else None

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

    aux=[]
    for r in P.itertuples(index=False):
        s20_clean=False; s20_ts=pd.NaT; s20_r=np.nan
        if bool(r.is_wide_q4):
            z=s20.eval_5m_signal(
                raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),
                float(r.tp1),float(r.reclaim_close),"CLOSE_BELOW",end
            )
            if z["signal_status"]=="CLEAN_SIGNAL":
                s20_clean=True; s20_ts=z["signal_ts"]
                s20_r=(float(z["exit_price"])-float(r.entry_price))/float(r.entry_price-r.touch_low_sl)

        tp1_i=None; body_r=np.nan
        if r.baseline_outcome=="WIN":
            tp1_i=first_tp1_idx(raw5,r.entry_ts,float(r.tp1),end)
            if tp1_i is None: raise RuntimeError(f"TP1 missing {r.zone_id}")
            risk=float(r.entry_price-r.touch_low_sl)
            b=raw5.iloc[tp1_i]
            body_r=(float(b.close)-float(b.open))/risk

        aux.append({
            "zone_id":r.zone_id,"s20_clean":s20_clean,"s20_ts":s20_ts,"s20_r":s20_r,
            "tp1_i":tp1_i if tp1_i is not None else np.nan,
            "tp1_bar_body_r":body_r,
            "weak_tp1_body":bool(np.isfinite(body_r) and body_r<=TP1_BODY_Q25_R),
        })
    P=P.merge(pd.DataFrame(aux),on="zone_id",how="left",validate="one_to_one")

    rows=[]
    for r in P.itertuples(index=False):
        entry=float(r.entry_price); sl=float(r.touch_low_sl); tp1=float(r.tp1)

        baseline=float(r.baseline_realized_r)
        s20_real=float(r.s20_r) if bool(r.s20_clean) else baseline
        s20_rt=r.s20_ts if bool(r.s20_clean) else r.baseline_resolution_ts

        # Reproduce exact S23.
        if bool(r.s20_clean):
            s23_real=float(r.s20_r); s23_rt=r.s20_ts; s23_status="S20_CUT"
        elif r.baseline_outcome!="WIN":
            s23_real=baseline; s23_rt=r.baseline_resolution_ts; s23_status="NO_TP1"
        elif not bool(r.major_runner_eligible):
            s23_real=baseline; s23_rt=r.baseline_resolution_ts; s23_status="NOT_PROMOTED"
        else:
            tp1_ts=raw5.index[int(r.tp1_i)]
            s23_status,s23_rt,s23_real=s23.runner_resolve(
                raw5,tp1_ts,entry,sl,tp1,float(r.major_nearest),end
            )

        # S25 differs only for eligible, surviving TP1 trades with weak body:
        # full TP1 instead of runner.
        if bool(r.s20_clean):
            s25_real=float(r.s20_r); s25_rt=r.s20_ts; s25_status="S20_CUT"
        elif r.baseline_outcome!="WIN":
            s25_real=baseline; s25_rt=r.baseline_resolution_ts; s25_status="NO_TP1"
        elif not bool(r.major_runner_eligible):
            s25_real=baseline; s25_rt=r.baseline_resolution_ts; s25_status="NOT_PROMOTED"
        elif bool(r.weak_tp1_body):
            s25_real=baseline; s25_rt=r.baseline_resolution_ts; s25_status="SKIP_WEAK_BODY_FULL_TP1"
        else:
            tp1_ts=raw5.index[int(r.tp1_i)]
            s25_status,s25_rt,s25_real=s23.runner_resolve(
                raw5,tp1_ts,entry,sl,tp1,float(r.major_nearest),end
            )

        common={
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "major_runner_eligible":bool(r.major_runner_eligible),
            "weak_tp1_body":bool(r.weak_tp1_body),
            "tp1_bar_body_r":r.tp1_bar_body_r,
            "s20_clean":bool(r.s20_clean),
        }
        rows += [
            {**common,"config":"BASELINE_TP1","realized_r":baseline,"status":"BASELINE","resolution_ts":r.baseline_resolution_ts},
            {**common,"config":"S20_IMMEDIATE","realized_r":s20_real,"status":"S20","resolution_ts":s20_rt},
            {**common,"config":"S23_ADAPTIVE_MAJOR_50_50_BE","realized_r":float(s23_real),"status":s23_status,"resolution_ts":s23_rt},
            {**common,"config":"S25_SKIP_WEAK_TP1_BODY","realized_r":float(s25_real),"status":s25_status,"resolution_ts":s25_rt},
        ]

    L=pd.DataFrame(rows)

    # Hard parity against persisted S23.
    s23q=L[L.config=="S23_ADAPTIVE_MAJOR_50_50_BE"]
    checks={
        "DEV_TOTAL":float(s23q[s23q.period=="DEV"].realized_r.sum()),
        "REF_TOTAL":float(s23q[s23q.period=="REF"].realized_r.sum()),
        "DEV_POS":int((s23q[s23q.period=="DEV"].realized_r>0).sum()),
        "REF_POS":int((s23q[s23q.period=="REF"].realized_r>0).sum()),
        "DEV_RUNNER":int(((s23q.period=="DEV")&s23q.status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT","BE_EXIT","AMBIGUOUS_SAME_BAR","PARTIAL_OPEN"])).sum()),
        "REF_RUNNER":int(((s23q.period=="REF")&s23q.status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT","BE_EXIT","AMBIGUOUS_SAME_BAR","PARTIAL_OPEN"])).sum()),
    }
    if abs(checks["DEV_TOTAL"]-23.24248766315734)>1e-9 or abs(checks["REF_TOTAL"]-1.8717965804698047)>1e-9:
        raise RuntimeError(f"S23 total parity drift {checks}")
    if checks["DEV_POS"]!=315 or checks["REF_POS"]!=199 or checks["DEV_RUNNER"]!=90 or checks["REF_RUNNER"]!=56:
        raise RuntimeError(f"S23 cohort parity drift {checks}")

    SUM=[]
    for per in ["DEV","REF"]:
        b20=L[(L.period==per)&(L.config=="S20_IMMEDIATE")][["zone_id","realized_r"]]
        b23=L[(L.period==per)&(L.config=="S23_ADAPTIVE_MAJOR_50_50_BE")][["zone_id","realized_r"]]
        for cfg in CONFIGS:
            q=L[(L.period==per)&(L.config==cfg)]
            SUM.append({
                "period":per,"config":cfg,
                **summarize(q,b20 if cfg=="S25_SKIP_WEAK_TP1_BODY" else None,
                            b23 if cfg=="S25_SKIP_WEAK_TP1_BODY" else None)
            })
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        b20=L[(L.year==y)&(L.config=="S20_IMMEDIATE")][["zone_id","realized_r"]]
        b23=L[(L.year==y)&(L.config=="S23_ADAPTIVE_MAJOR_50_50_BE")][["zone_id","realized_r"]]
        for cfg in CONFIGS:
            q=L[(L.year==y)&(L.config==cfg)]
            if len(q):
                Y.append({
                    "year":y,"config":cfg,
                    **summarize(q,b20 if cfg=="S25_SKIP_WEAK_TP1_BODY" else None,
                                b23 if cfg=="S25_SKIP_WEAK_TP1_BODY" else None)
                })
    Y=pd.DataFrame(Y)

    # Runner cohort diagnostics.
    RC=[]
    for per in ["DEV","REF"]:
        q25=L[(L.period==per)&(L.config=="S25_SKIP_WEAK_TP1_BODY")]
        runner_candidates=q25[
            q25.major_runner_eligible &
            (~q25.s20_clean) &
            q25.status.isin(["SKIP_WEAK_BODY_FULL_TP1","MAJOR_SAME_TP1_BAR","MAJOR_HIT","BE_EXIT","AMBIGUOUS_SAME_BAR","PARTIAL_OPEN"])
        ]
        skips=runner_candidates[runner_candidates.status=="SKIP_WEAK_BODY_FULL_TP1"]
        active=runner_candidates[runner_candidates.status!="SKIP_WEAK_BODY_FULL_TP1"]

        # Original S23 outcomes for exactly skipped IDs.
        s23map=L[(L.period==per)&(L.config=="S23_ADAPTIVE_MAJOR_50_50_BE")].set_index("zone_id")
        ids=skips.zone_id.tolist()
        old=s23map.loc[ids] if ids else s23map.iloc[0:0]
        RC.append({
            "period":per,
            "runner_candidates":len(runner_candidates),
            "weak_body_skips":len(skips),
            "active_runners":len(active),
            "major_hits":int(active.status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT"]).sum()),
            "be_exits":int((active.status=="BE_EXIT").sum()),
            "ambiguous":int((active.status=="AMBIGUOUS_SAME_BAR").sum()),
            "partial_open":int((active.status=="PARTIAL_OPEN").sum()),
            "skip_full_tp1_r":float(skips.realized_r.sum()) if len(skips) else 0.0,
            "skip_original_s23_r":float(old.realized_r.sum()) if len(old) else 0.0,
            "skip_incremental_r":float(skips.realized_r.sum()-old.realized_r.sum()) if len(skips) else 0.0,
            "skip_original_major_hits":int(old.status.isin(["MAJOR_SAME_TP1_BAR","MAJOR_HIT"]).sum()) if len(old) else 0,
            "skip_original_be":int((old.status=="BE_EXIT").sum()) if len(old) else 0,
            "skip_original_ambiguous":int((old.status=="AMBIGUOUS_SAME_BAR").sum()) if len(old) else 0,
        })
    RC=pd.DataFrame(RC)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    RC.to_csv(ROOT/f"{PFX}_RunnerCohort.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\n"
        f"WIDE_CUT={WIDE_CUT:.18f}\nMAJOR_ROOM_CUT_R={MAJOR_ROOM_CUT_R:.17f}\n"
        f"TP1_BODY_Q25_R={TP1_BODY_Q25_R:.18f}\n"
        "SKIP_RULE=TP1_BAR_BODY_R_LE_Q25_THEN_FULL_TP1\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S25 — Weak TP1 Body Runner-Skip Validation","",
        f"Frozen E2 signature: `{sig}`",
        f"Frozen S24 weak-body cut: `tp1_bar_body_r <= {TP1_BODY_Q25_R:.18f}R`","",
        "## Overall economics","",
        "| Period | Config | + / - / 0 | Positive rate | Med +R | Exp | Total R | PF | Max DD | Max L | ΔR vs S23 | ΔR vs S20 | S23 + retained |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        d23=fmt_num(r.incremental_r_vs_s23) if np.isfinite(r.incremental_r_vs_s23) else "—"
        d20=fmt_num(r.incremental_r_vs_s20) if np.isfinite(r.incremental_r_vs_s20) else "—"
        ret=(f"{int(r.s23_positive_retained)}/{int(r.s23_positive)}" if np.isfinite(r.s23_positive) else "—")
        lines.append(
            f"| {r.period} | {r.config} | {r.positive}/{r.negative}/{r.zero} | {fmt_pct(r.positive_rate)} | "
            f"{fmt_num(r.median_positive_r)}R | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.profit_factor)} | {fmt_num(r.max_drawdown_r)}R | {r.max_loss_streak} | "
            f"{d23}R | {d20}R | {ret} |"
        )

    lines += ["","## Runner cohort after weak-body skip","",
        "| Period | Candidates | Weak-body skips | Active runners | Major hit | BE | Ambig | Open | Skip full-TP1 R | Skip old-S23 R | Skip ΔR | Old skip HIT/BE/Amb |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in RC.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.runner_candidates} | {r.weak_body_skips} | {r.active_runners} | "
            f"{r.major_hits} | {r.be_exits} | {r.ambiguous} | {r.partial_open} | "
            f"{fmt_num(r.skip_full_tp1_r)}R | {fmt_num(r.skip_original_s23_r)}R | "
            f"{fmt_num(r.skip_incremental_r)}R | {r.skip_original_major_hits}/{r.skip_original_be}/{r.skip_original_ambiguous} |"
        )

    lines += ["","## Annual S25 stability","",
        "| Year | Config | Exp | Total R | + / - | ΔR vs S23 |",
        "|---:|---|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        d23=fmt_num(r.incremental_r_vs_s23) if np.isfinite(r.incremental_r_vs_s23) else "—"
        lines.append(
            f"| {r.year} | {r.config} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{r.positive}/{r.negative} | {d23}R |"
        )

    lines += ["","## Interpretation boundary",
      "S25 validates exactly one frozen weak-TP1-body skip rule.",
      "No threshold, feature combination, runner split, or target is retuned from S25 outcomes.",
      "A promotion requires unchanged REF improvement/preservation and positive-trade retention."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S25_WEAK_TP1_BODY_SKIP_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
