#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b40_s8_structural_invalidation_semantics as s8
import bnb_b40_s10_tp_xp1_runner_geometry as s10
import bnb_b40_s12_post_t1_runner_failure_character as s12

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S13_POST_T1_FAILURE_PERSISTENCE_RESCUE"

XP1_SIGNATURE=s12.XP1_SIGNATURE
CANDS=[
    "P1_ANCHOR_TWO_CONSEC_CLOSE5",
    "P2_ANCHOR_THREE_CONSEC_CLOSE5",
    "P3_T05_THEN_ANCHOR_CLOSE5",
    "P4_ANCHOR_RECLAIM_REJECT5",
]
TARGETS=["T15","T2"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def resolve_candidate(raw5,r,cand,target_name,deadline,frozen_runner,frozen_t1_ts,fixed_result):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(r.signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))

    entry=float(r.sd1_close)
    protected=float(r.floor)
    er=float(r.event_risk)
    anchor=float(r.target_anchor_1r)-er
    risk=entry-protected
    if risk<=0:
        return {"status":"UNAVAILABLE","realized_r":0.0,"runner_started":False}

    t05=anchor+0.5*er
    runner_target=anchor+(1.5 if target_name=="T15" else 2.0)*er

    if not frozen_runner or pd.isna(frozen_t1_ts):
        return {
            "status":"NON_RUNNER_FIXED_T1",
            "realized_r":float(fixed_result["realized_r"]),
            "resolution_ts":fixed_result["resolution_ts"],
            "xp1_active":False,
            "runner_started":False,
            "target_hit":str(fixed_result["status"]).startswith("TARGET_"),
            "failure_signal":False,
            "failure_level":np.nan,
            "same_as_catastrophic":False,
            "catastrophic":str(fixed_result["status"])=="STOP_BEFORE_FULL_TARGET",
        }

    t1_i=int(idx.searchsorted(pd.Timestamp(frozen_t1_ts),side="left"))
    if t1_i>=len(raw5) or idx[t1_i]!=pd.Timestamp(frozen_t1_ts):
        raise RuntimeError(f"frozen T1 timestamp not found: {frozen_t1_ts}")

    if float(raw5.high.iloc[t1_i])>=runner_target:
        return {
            "status":"TARGET_RUNNER_SAME_T1_BAR",
            "realized_r":float((runner_target-entry)/risk),
            "resolution_ts":idx[t1_i],
            "xp1_active":True,
            "runner_started":True,
            "target_hit":True,
            "failure_signal":False,
            "failure_level":np.nan,
            "same_as_catastrophic":False,
            "catastrophic":False,
        }

    scan0=t1_i+1
    if scan0>=i1:
        return {
            "status":"UNRESOLVED","realized_r":0.0,"resolution_ts":pd.NaT,
            "xp1_active":True,"runner_started":True,"target_hit":False,
            "failure_signal":False,"failure_level":np.nan,
            "same_as_catastrophic":False,"catastrophic":False,
        }

    below_anchor_streak=0
    prev_below_anchor=False
    prev_below_t05=False

    for i in range(scan0,i1):
        b=raw5.iloc[i]
        ts=idx[i]
        high=float(b.high)
        close=float(b.close)

        if high>=runner_target:
            return {
                "status":"TARGET_RUNNER",
                "realized_r":float((runner_target-entry)/risk),
                "resolution_ts":ts,
                "xp1_active":True,"runner_started":True,"target_hit":True,
                "failure_signal":False,"failure_level":np.nan,
                "same_as_catastrophic":False,"catastrophic":False,
            }

        below_anchor=close<anchor
        below_t05=close<t05
        below_anchor_streak=(below_anchor_streak+1) if below_anchor else 0

        sig=False
        level=anchor

        if cand=="P1_ANCHOR_TWO_CONSEC_CLOSE5":
            sig=below_anchor_streak>=2
        elif cand=="P2_ANCHOR_THREE_CONSEC_CLOSE5":
            sig=below_anchor_streak>=3
        elif cand=="P3_T05_THEN_ANCHOR_CLOSE5":
            sig=prev_below_t05 and below_anchor
        elif cand=="P4_ANCHOR_RECLAIM_REJECT5":
            sig=prev_below_anchor and high>=anchor and below_anchor
        else:
            raise RuntimeError(cand)

        j=i-i0
        cat_here=((j+1)%3==0) and close<protected

        if sig:
            realized=float((close-entry)/risk)
            if cat_here:
                return {
                    "status":"FAILURE_SAME_AS_CATASTROPHIC",
                    "realized_r":realized,"resolution_ts":ts,
                    "xp1_active":True,"runner_started":True,"target_hit":False,
                    "failure_signal":False,"failure_level":anchor,
                    "same_as_catastrophic":True,"catastrophic":True,
                }
            return {
                "status":"FAILURE_SIGNAL",
                "realized_r":realized,"resolution_ts":ts,
                "xp1_active":True,"runner_started":True,"target_hit":False,
                "failure_signal":True,"failure_level":anchor,
                "same_as_catastrophic":False,"catastrophic":False,
            }

        if cat_here:
            return {
                "status":"CATASTROPHIC_CLOSE15",
                "realized_r":float((close-entry)/risk),
                "resolution_ts":ts,
                "xp1_active":True,"runner_started":True,"target_hit":False,
                "failure_signal":False,"failure_level":np.nan,
                "same_as_catastrophic":False,"catastrophic":True,
            }

        prev_below_anchor=below_anchor
        prev_below_t05=below_t05

    return {
        "status":"UNRESOLVED","realized_r":0.0,"resolution_ts":pd.NaT,
        "xp1_active":True,"runner_started":True,"target_hit":False,
        "failure_signal":False,"failure_level":np.nan,
        "same_as_catastrophic":False,"catastrophic":False,
    }

def main():
    Q=s8.load_parent()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1()
    ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    raw5=raw[["open","high","low","close"]].astype(float)
    end=raw5.index.max()

    signature=hashlib.sha256(
        json.dumps({
            "parent":"B40_S12_POST_T1_FAILURE_CHARACTER",
            "xp1_signature":XP1_SIGNATURE,
            "levels":["T0.5","ANCHOR"],
            "states":CANDS,
            "runner_targets":TARGETS,
            "target_priority":"INTRABAR_BEFORE_CLOSE_SIGNAL",
            "threshold_search":False,
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    base_map={}
    fixed_map={}
    for r in Q.itertuples(index=False):
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        fixed=s10.resolve_policy(raw5,r,"FIXED_T1",deadline)
        fixed_map[r.zone_id]=fixed
        for target_name,policy in [("T15","XP1_EXTEND_T15"),("T2","XP1_EXTEND_T2")]:
            z=s10.resolve_policy(raw5,r,policy,deadline)
            if bool(z["xp1_active"] and z["t1_hit"]):
                if z["status"].startswith("TARGET_"):
                    bs="TARGET"
                elif z["status"]=="STOP_BEFORE_FULL_TARGET":
                    bs="CATASTROPHIC"
                elif z["status"]=="UNRESOLVED":
                    bs="UNRESOLVED"
                else:
                    bs=z["status"]
            else:
                bs="NON_RUNNER"
            base_map[(r.zone_id,target_name)]={
                "r":float(z["realized_r"]),
                "status":bs,
                "resolution_ts":z["resolution_ts"],
                "runner":bool(z["xp1_active"] and z["t1_hit"]),
                "t1_ts":z["t1_ts"],
            }

    rows=[]
    for r in Q.itertuples(index=False):
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        fixed=fixed_map[r.zone_id]
        entry=float(r.sd1_close)
        protected=float(r.floor)
        er=float(r.event_risk)
        anchor=float(r.target_anchor_1r)-er

        for target_name in TARGETS:
            base=base_map[(r.zone_id,target_name)]
            runner_target=anchor+(1.5 if target_name=="T15" else 2.0)*er

            for cand in CANDS:
                z=resolve_candidate(
                    raw5,r,cand,target_name,deadline,
                    base["runner"],base["t1_ts"],fixed
                )

                later=pd.NaT
                reclaim_next5=False
                reclaim15=False
                overshoot_abs=np.nan
                minutes_to_target=np.nan

                if z["failure_signal"] and base["status"]=="TARGET" and pd.notna(z["resolution_ts"]):
                    later=s12.first_target_after(raw5,z["resolution_ts"],runner_target,deadline)
                    if pd.notna(later):
                        minutes_to_target=float(
                            (pd.Timestamp(later)-pd.Timestamp(z["resolution_ts"]))/
                            pd.Timedelta(minutes=1)
                        )
                        reclaim_next5,reclaim15,overshoot_abs=s12.reclaim_diag(
                            raw5,z["resolution_ts"],float(z["failure_level"]),later
                        )

                lead=np.nan
                if z["failure_signal"] and base["status"]=="CATASTROPHIC" and pd.notna(base["resolution_ts"]):
                    lead=float(
                        (pd.Timestamp(base["resolution_ts"])-pd.Timestamp(z["resolution_ts"]))/
                        pd.Timedelta(minutes=1)
                    )

                rows.append({
                    "zone_id":r.zone_id,
                    "period":r.period,
                    "year":int(r.year),
                    "first_retest_ts":r.first_retest_ts,
                    "signal_ts":r.signal_ts,
                    "target_family":target_name,
                    "candidate":cand,
                    "status":z["status"],
                    "resolution_ts":z["resolution_ts"],
                    "realized_r":z["realized_r"],
                    "xp1_active":z["xp1_active"],
                    "runner_started":z["runner_started"],
                    "target_hit":z["target_hit"],
                    "failure_signal":z["failure_signal"],
                    "failure_level":z["failure_level"],
                    "same_as_catastrophic":z["same_as_catastrophic"],
                    "catastrophic":z["catastrophic"],
                    "base_status":base["status"],
                    "base_r":base["r"],
                    "base_resolution_ts":base["resolution_ts"],
                    "fixed_t1_r":float(fixed["realized_r"]),
                    "incremental_vs_base_r":float(z["realized_r"]-base["r"]),
                    "incremental_vs_fixed_t1_r":float(z["realized_r"]-float(fixed["realized_r"])),
                    "lead_to_base_resolution_min":lead,
                    "later_target_after_signal":pd.notna(later),
                    "later_target_ts":later,
                    "minutes_to_later_target":minutes_to_target,
                    "reclaim_next5":reclaim_next5,
                    "reclaim_within15":reclaim15,
                    "overshoot_below_failure_level_event_r":(
                        overshoot_abs/er if np.isfinite(overshoot_abs) and er>0 else np.nan
                    ),
                })

    E=pd.DataFrame(rows)

    for per,n in {"DEV":286,"REF":160}.items():
        for target in TARGETS:
            for cand in CANDS:
                z=E[(E.period==per)&(E.target_family==target)&(E.candidate==cand)]
                if len(z)!=n:
                    raise RuntimeError(f"row parity drift {per} {target} {cand}: {len(z)} != {n}")

    expected={
        ("DEV","T15"):(71,59,10,2),
        ("REF","T15"):(46,35,10,1),
        ("DEV","T2"):(71,45,16,10),
        ("REF","T2"):(46,30,13,3),
    }
    for (per,target),(rn,w,l,u) in expected.items():
        z=E[(E.period==per)&(E.target_family==target)&(E.candidate==CANDS[0])]
        run=z[z.runner_started]
        got=(
            len(run),
            int((run.base_status=="TARGET").sum()),
            int((run.base_status=="CATASTROPHIC").sum()),
            int((run.base_status=="UNRESOLVED").sum())
        )
        if got!=(rn,w,l,u):
            raise RuntimeError(f"runner control parity drift {per} {target}: {got} != {(rn,w,l,u)}")

    SUM=[]
    for per in ["DEV","REF"]:
        for target in TARGETS:
            for cand in CANDS:
                q=E[(E.period==per)&(E.target_family==target)&(E.candidate==cand)]
                SUM.append({"period":per,"target_family":target,"candidate":cand,**s12.summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for target in TARGETS:
            for cand in CANDS:
                q=E[(E.year==y)&(E.target_family==target)&(E.candidate==cand)]
                if len(q):
                    Y.append({"year":y,"target_family":target,"candidate":cand,**s12.summarize(q)})
    Y=pd.DataFrame(Y)

    ADV=[]
    for target in TARGETS:
        for cand in CANDS:
            dev=SUM[(SUM.period=="DEV")&(SUM.target_family==target)&(SUM.candidate==cand)].iloc[0]
            ref=SUM[(SUM.period=="REF")&(SUM.target_family==target)&(SUM.candidate==cand)].iloc[0]
            yy=Y[(Y.target_family==target)&(Y.candidate==cand)]
            annual_nonneg=int((yy.delta_vs_base_mean_r>=-1e-12).sum())
            passes=bool(
                dev.delta_vs_fixed_t1_mean_r>0 and ref.delta_vs_fixed_t1_mean_r>0 and
                dev.delta_vs_base_mean_r>0 and ref.delta_vs_base_mean_r>0 and
                dev.catastrophic_capture_rate>=0.80 and ref.catastrophic_capture_rate>=0.80 and
                dev.winner_false_exit_rate<=0.15 and ref.winner_false_exit_rate<=0.15 and
                annual_nonneg>=4
            )
            ADV.append({
                "target_family":target,
                "candidate":cand,
                "dev_delta_vs_t1":dev.delta_vs_fixed_t1_mean_r,
                "ref_delta_vs_t1":ref.delta_vs_fixed_t1_mean_r,
                "dev_delta_vs_base":dev.delta_vs_base_mean_r,
                "ref_delta_vs_base":ref.delta_vs_base_mean_r,
                "dev_cat_capture":dev.catastrophic_capture_rate,
                "ref_cat_capture":ref.catastrophic_capture_rate,
                "dev_false_exit":dev.winner_false_exit_rate,
                "ref_false_exit":ref.winner_false_exit_rate,
                "annual_nonneg_vs_base":annual_nonneg,
                "passes_advance_rule":passes,
            })
    ADV=pd.DataFrame(ADV)

    FALSE=E[(E.failure_signal)&(E.base_status=="TARGET")].copy()
    CAP=E[(E.failure_signal)&(E.base_status=="CATASTROPHIC")].copy()

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    ADV.to_csv(ROOT/f"{PFX}_AdvanceAudit.csv",index=False)
    FALSE.to_csv(ROOT/f"{PFX}_FalseExitLedger.csv.gz",index=False,compression="gzip")
    CAP.to_csv(ROOT/f"{PFX}_CapturedFailureLedger.csv.gz",index=False,compression="gzip")

    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S12_POST_T1_FAILURE_CHARACTER\n"
        f"XP1_SIGNATURE_SHA256={XP1_SIGNATURE}\n"
        f"S13_SIGNATURE_SHA256={signature}\n"
        "RUNNER_COHORT=XP1_PLUS_T1\n"
        "LEVELS=T0.5,ANCHOR\n"
        "CANDIDATES=P1_ANCHOR_TWO_CONSEC_CLOSE5,P2_ANCHOR_THREE_CONSEC_CLOSE5,P3_T05_THEN_ANCHOR_CLOSE5,P4_ANCHOR_RECLAIM_REJECT5\n"
        "FAILURE_EVALUATION_START=STRICTLY_AFTER_T1_MILESTONE_BAR\n"
        "TARGET_PRIORITY=INTRABAR_BEFORE_CLOSE_FAILURE\n"
        "NO_NEW_LEVELS=TRUE\nNO_THRESHOLD_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S13 — Post-T1 Failure Persistence / Rescue Confirmation","",
        f"XP1 signature: {XP1_SIGNATURE}",
        f"S13 signature: {signature}","",
        "S13 keeps T0.5 / ANCHOR only and asks whether persistence or failed reclaim makes the S12 warning executable.","",
        "## Persistence / rescue audit","",
        "| Period | Target | Candidate | Signal | Cat captured | Winner false-exit | Precision | Med exit R | Med R improve | Lead to cat | Later target after false exit | CF Exp | Δ vs T1 | Δ vs unprotected | PF | MaxDD |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.target_family} | {r.candidate} | "
            f"{r.clean_signals}/{r.runner_n} ({fmt_pct(r.signal_rate_runner)}) | "
            f"{r.catastrophic_captured}/{r.base_catastrophic} ({fmt_pct(r.catastrophic_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.base_target_winners} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_nontarget)} | {fmt_num(r.median_failure_exit_r)}R | "
            f"{fmt_num(r.median_r_improve_vs_base)}R | {fmt_num(r.median_lead_to_cat_min,1)}m | "
            f"{r.later_target_after_false_exit}/{r.winner_false_exit} ({fmt_pct(r.later_target_after_false_exit_rate)}) | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.delta_vs_fixed_t1_mean_r)}R | "
            f"{fmt_num(r.delta_vs_base_mean_r)}R | {fmt_num(r.pf)} | {fmt_num(r.max_dd_r)}R |"
        )

    lines += ["","## Advance-rule audit","",
        "| Target | Candidate | DEV Δbase | REF Δbase | DEV cat | REF cat | DEV false | REF false | Annual >=0 | PASS |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in ADV.itertuples(index=False):
        lines.append(
            f"| {r.target_family} | {r.candidate} | {fmt_num(r.dev_delta_vs_base)}R | "
            f"{fmt_num(r.ref_delta_vs_base)}R | {fmt_pct(r.dev_cat_capture)} | {fmt_pct(r.ref_cat_capture)} | "
            f"{fmt_pct(r.dev_false_exit)} | {fmt_pct(r.ref_false_exit)} | "
            f"{r.annual_nonneg_vs_base}/5 | {'YES' if r.passes_advance_rule else 'NO'} |"
        )

    lines += ["","## Interpretation boundary",
        "S13 changes only post-warning confirmation semantics; entry, structural failure, XP1, T1 milestone and farther targets remain frozen.",
        "A target traded intrabar always has priority over a close-based failure confirmation on the same 5m bar.",
        "No candidate is promoted unless the preregistered cross-period and annual advance rule is passed."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(
        "BNB_B40_S13_POST_T1_FAILURE_PERSISTENCE_RESCUE_COMPLETE\n",
        encoding="utf-8"
    )
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
