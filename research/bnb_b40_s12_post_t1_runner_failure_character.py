#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b40_s8_structural_invalidation_semantics as s8
import bnb_b40_s10_tp_xp1_runner_geometry as s10

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S12_POST_T1_RUNNER_FAILURE_CHARACTER"

XP1_SIGNATURE="3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8"
XP1_MIN=60.0

CANDS=[
    "F1_T05_CLOSE5",
    "F2_T05_CLOSE15",
    "F3_ANCHOR_CLOSE5",
    "F4_ANCHOR_CLOSE15",
    "F5_T05_TWO_CONSEC_CLOSE5",
    "F6_T05_RECLAIM_ATTEMPT_REJECT",
]
TARGETS=["T15","T2"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def maxdd(rs):
    if not len(rs):return np.nan
    a=np.asarray(rs,float)
    c=np.cumsum(a)
    peaks=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(peaks-c))

def maxls(vals):
    cur=mx=0
    for x in vals:
        if x<0:
            cur+=1;mx=max(mx,cur)
        else:
            cur=0
    return mx

def first_target_after(raw5,start_ts,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return pd.NaT
    arr=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=target)
    return idx[i0+int(z[0])] if len(z) else pd.NaT

def reclaim_diag(raw5,signal_ts,level,later_target_ts):
    if pd.isna(signal_ts) or pd.isna(later_target_ts):
        return False,False,np.nan
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    it=int(idx.searchsorted(pd.Timestamp(later_target_ts),side="right"))
    if i0>=it:
        return False,False,np.nan
    next5=bool(float(raw5.close.iloc[i0])>=level) if i0<len(raw5) else False
    upto=min(it,i0+3)
    within15=bool((raw5.close.iloc[i0:upto]>=level).any()) if upto>i0 else False
    seg=raw5.iloc[int(idx.searchsorted(pd.Timestamp(signal_ts),side="left")):it]
    overs=max(0.0,(level-float(seg.low.min()))) if len(seg) else np.nan
    return next5,within15,overs

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
    runner_target=(anchor+1.5*er) if target_name=="T15" else (anchor+2.0*er)

    # Freeze runner eligibility and milestone timestamp directly from S10.
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

    # If farther target is reached on the frozen T1 milestone bar, target wins before S12 can activate.
    milestone_bar=raw5.iloc[t1_i]
    if float(milestone_bar.high)>=runner_target:
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

    runner_post_count=0
    prev_below_t05=False
    status=None
    realized=0.0
    resolution_ts=pd.NaT
    failure_signal=False
    failure_level=np.nan
    same_as_cat=False
    catastrophic=False
    target_hit=False

    scan0=t1_i+1
    if scan0>=i1:
        return {
            "status":"UNRESOLVED","realized_r":0.0,"resolution_ts":pd.NaT,
            "xp1_active":True,"runner_started":True,"target_hit":False,
            "failure_signal":False,"failure_level":np.nan,
            "same_as_catastrophic":False,"catastrophic":False,
        }

    for i in range(scan0,i1):
        b=raw5.iloc[i]
        ts=idx[i]
        high=float(b.high)
        close=float(b.close)
        runner_post_count+=1

        # Resting farther target has intrabar priority.
        if high>=runner_target:
            realized=(runner_target-entry)/risk
            status="TARGET_RUNNER"
            resolution_ts=ts
            target_hit=True
            break

        sig=False
        level=np.nan
        below_t05=close<t05

        if cand=="F1_T05_CLOSE5":
            sig=below_t05
            level=t05
        elif cand=="F2_T05_CLOSE15":
            sig=(runner_post_count%3==0) and below_t05
            level=t05
        elif cand=="F3_ANCHOR_CLOSE5":
            sig=close<anchor
            level=anchor
        elif cand=="F4_ANCHOR_CLOSE15":
            sig=(runner_post_count%3==0) and close<anchor
            level=anchor
        elif cand=="F5_T05_TWO_CONSEC_CLOSE5":
            sig=prev_below_t05 and below_t05
            level=t05
        elif cand=="F6_T05_RECLAIM_ATTEMPT_REJECT":
            sig=prev_below_t05 and float(b.high)>=t05 and below_t05
            level=t05
        else:
            raise RuntimeError(cand)

        # Catastrophic alignment remains frozen to raw5 bars after SD1 decision, not to post-T1 windows.
        j=i-i0
        cat_here=((j+1)%3==0) and close<protected

        if sig:
            realized=float((close-entry)/risk)
            resolution_ts=ts
            failure_level=float(level)
            if cat_here:
                status="FAILURE_SAME_AS_CATASTROPHIC"
                same_as_cat=True
                catastrophic=True
            else:
                status="FAILURE_SIGNAL"
                failure_signal=True
            break

        if cat_here:
            realized=float((close-entry)/risk)
            status="CATASTROPHIC_CLOSE15"
            resolution_ts=ts
            catastrophic=True
            break

        prev_below_t05=below_t05

    if status is None:
        status="UNRESOLVED"

    return {
        "status":status,
        "realized_r":float(realized),
        "resolution_ts":resolution_ts,
        "xp1_active":True,
        "runner_started":True,
        "target_hit":bool(target_hit),
        "failure_signal":bool(failure_signal),
        "failure_level":failure_level,
        "same_as_catastrophic":bool(same_as_cat),
        "catastrophic":bool(catastrophic),
    }

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    pos=q[q.realized_r>1e-12]
    neg=q[q.realized_r<-1e-12]
    zer=q[np.abs(q.realized_r)<=1e-12]
    ps=float(pos.realized_r.sum()) if len(pos) else 0.0
    ns=abs(float(neg.realized_r.sum())) if len(neg) else 0.0
    run=q[q.runner_started]
    sig=run[run.failure_signal]
    base_loss=run[run.base_status=="CATASTROPHIC"]
    base_win=run[run.base_status=="TARGET"]
    base_unres=run[run.base_status=="UNRESOLVED"]
    cap=sig[sig.base_status=="CATASTROPHIC"]
    false=sig[sig.base_status=="TARGET"]
    unres_exit=sig[sig.base_status=="UNRESOLVED"]
    return {
        "n":len(q),
        "runner_n":len(run),
        "clean_signals":len(sig),
        "signal_rate_runner":len(sig)/len(run) if len(run) else np.nan,
        "base_catastrophic":len(base_loss),
        "catastrophic_captured":len(cap),
        "catastrophic_capture_rate":len(cap)/len(base_loss) if len(base_loss) else np.nan,
        "base_target_winners":len(base_win),
        "winner_false_exit":len(false),
        "winner_false_exit_rate":len(false)/len(base_win) if len(base_win) else np.nan,
        "base_unresolved":len(base_unres),
        "unresolved_exited":len(unres_exit),
        "signal_precision_nontarget":(len(cap)+len(unres_exit))/len(sig) if len(sig) else np.nan,
        "median_failure_exit_r":float(sig.realized_r.median()) if len(sig) else np.nan,
        "median_r_improve_vs_base":float(sig.incremental_vs_base_r.median()) if len(sig) else np.nan,
        "median_cat_r_saved":float(cap.incremental_vs_base_r.median()) if len(cap) else np.nan,
        "median_lead_to_cat_min":float(cap.lead_to_base_resolution_min.median()) if len(cap) else np.nan,
        "median_false_exit_to_target_min":float(false.minutes_to_later_target.median()) if len(false) else np.nan,
        "later_target_after_false_exit":int(false.later_target_after_signal.sum()) if len(false) else 0,
        "later_target_after_false_exit_rate":float(false.later_target_after_signal.mean()) if len(false) else np.nan,
        "false_reclaim_next5_rate":float(false.reclaim_next5.mean()) if len(false) else np.nan,
        "false_reclaim_within15_rate":float(false.reclaim_within15.mean()) if len(false) else np.nan,
        "expectancy_r":float(q.realized_r.mean()) if len(q) else np.nan,
        "total_r":float(q.realized_r.sum()),
        "pf":ps/ns if ns>0 else (np.inf if ps>0 else np.nan),
        "max_dd_r":maxdd(q.realized_r.tolist()) if len(q) else np.nan,
        "max_loss_streak":maxls(q.realized_r.tolist()) if len(q) else np.nan,
        "delta_vs_fixed_t1_mean_r":float(q.incremental_vs_fixed_t1_r.mean()) if len(q) else np.nan,
        "delta_vs_base_mean_r":float(q.incremental_vs_base_r.mean()) if len(q) else np.nan,
    }

def main():
    Q=s8.load_parent()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)
    end=raw5.index.max()

    signature=hashlib.sha256(
        json.dumps({
            "parent":"B40_S11_XP1_T1_RUNNER",
            "xp1_signature":XP1_SIGNATURE,
            "levels":["T0.5","ANCHOR"],
            "states":CANDS,
            "runner_targets":TARGETS,
            "target_priority":"INTRABAR_BEFORE_CLOSE_SIGNAL",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    # Matching frozen controls from S10.
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
        risk=entry-protected

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
                    later=first_target_after(raw5,z["resolution_ts"],runner_target,deadline)
                    if pd.notna(later):
                        minutes_to_target=float((pd.Timestamp(later)-pd.Timestamp(z["resolution_ts"]))/pd.Timedelta(minutes=1))
                        lvl=float(z["failure_level"])
                        reclaim_next5,reclaim15,overshoot_abs=reclaim_diag(raw5,z["resolution_ts"],lvl,later)

                lead=np.nan
                if z["failure_signal"] and base["status"]=="CATASTROPHIC" and pd.notna(base["resolution_ts"]):
                    lead=float((pd.Timestamp(base["resolution_ts"])-pd.Timestamp(z["resolution_ts"]))/pd.Timedelta(minutes=1))

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
                    "overshoot_below_failure_level_event_r":(overshoot_abs/er if np.isfinite(overshoot_abs) and er>0 else np.nan),
                })

    E=pd.DataFrame(rows)

    for per,n in {"DEV":286,"REF":160}.items():
        for target in TARGETS:
            for cand in CANDS:
                z=E[(E.period==per)&(E.target_family==target)&(E.candidate==cand)]
                if len(z)!=n:
                    raise RuntimeError(f"row parity drift {per} {target} {cand}: {len(z)} != {n}")

    # Frozen runner cohort / control parity.
    expected={
        ("DEV","T15"):(71,59,10,2),
        ("REF","T15"):(46,35,10,1),
        ("DEV","T2"):(71,45,16,10),
        ("REF","T2"):(46,30,13,3),
    }
    for (per,target),(rn,w,l,u) in expected.items():
        z=E[(E.period==per)&(E.target_family==target)&(E.candidate==CANDS[0])]
        run=z[z.runner_started]
        got=(len(run),int((run.base_status=="TARGET").sum()),int((run.base_status=="CATASTROPHIC").sum()),int((run.base_status=="UNRESOLVED").sum()))
        if got!=(rn,w,l,u):
            raise RuntimeError(f"runner control parity drift {per} {target}: {got} != {(rn,w,l,u)}")

    SUM=[]
    for per in ["DEV","REF"]:
        for target in TARGETS:
            for cand in CANDS:
                q=E[(E.period==per)&(E.target_family==target)&(E.candidate==cand)]
                SUM.append({"period":per,"target_family":target,"candidate":cand,**summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for target in TARGETS:
            for cand in CANDS:
                q=E[(E.year==y)&(E.target_family==target)&(E.candidate==cand)]
                if len(q):
                    Y.append({"year":y,"target_family":target,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    FALSE=E[(E.failure_signal)&(E.base_status=="TARGET")].copy()
    CAP=E[(E.failure_signal)&(E.base_status=="CATASTROPHIC")].copy()

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FALSE.to_csv(ROOT/f"{PFX}_FalseExitLedger.csv.gz",index=False,compression="gzip")
    CAP.to_csv(ROOT/f"{PFX}_CapturedFailureLedger.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S11_XP1_T1_RUNNER\n"
        f"XP1_SIGNATURE_SHA256={XP1_SIGNATURE}\n"
        f"S12_SIGNATURE_SHA256={signature}\n"
        "RUNNER_COHORT=XP1_PLUS_T1\n"
        "LEVELS=T0.5,ANCHOR\n"
        "CANDIDATES=F1_T05_CLOSE5,F2_T05_CLOSE15,F3_ANCHOR_CLOSE5,F4_ANCHOR_CLOSE15,F5_T05_TWO_CONSEC_CLOSE5,F6_T05_RECLAIM_ATTEMPT_REJECT\n"
        "FAILURE_EVALUATION_START=STRICTLY_AFTER_T1_MILESTONE_BAR\n"
        "TARGET_PRIORITY=INTRABAR_BEFORE_CLOSE_FAILURE\n"
        "NO_NEW_LEVELS=TRUE\nNO_THRESHOLD_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S12 — Post-T1 Runner Failure Character","",
        f"XP1 signature: `{XP1_SIGNATURE}`",
        f"S12 signature: `{signature}`","",
        "Failure-state evaluation starts strictly after XP1 + T1. Touch behavior is not retested.","",
        "## Failure-character audit","",
        "| Period | Target | Candidate | Signal | Cat loss captured | Winner false-exit | Precision non-target | Med exit R | Med R improve | Lead to cat | Later target after false exit | CF Exp | Δ vs T1 | Δ vs unprotected | PF | MaxDD |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.target_family} | {r.candidate} | {r.clean_signals}/{r.runner_n} ({fmt_pct(r.signal_rate_runner)}) | "
            f"{r.catastrophic_captured}/{r.base_catastrophic} ({fmt_pct(r.catastrophic_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.base_target_winners} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_nontarget)} | {fmt_num(r.median_failure_exit_r)}R | "
            f"{fmt_num(r.median_r_improve_vs_base)}R | {fmt_num(r.median_lead_to_cat_min,1)}m | "
            f"{r.later_target_after_false_exit}/{r.winner_false_exit} ({fmt_pct(r.later_target_after_false_exit_rate)}) | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.delta_vs_fixed_t1_mean_r)}R | "
            f"{fmt_num(r.delta_vs_base_mean_r)}R | {fmt_num(r.pf)} | {fmt_num(r.max_dd_r)}R |"
        )

    lines += ["","## Annual stability","",
        "| Year | Target | Candidate | Cat capture | Winner false-exit | CF Exp | Δ vs T1 | Δ vs unprotected |",
        "|---:|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.target_family} | {r.candidate} | "
            f"{r.catastrophic_captured}/{r.base_catastrophic} ({fmt_pct(r.catastrophic_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.base_target_winners} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.delta_vs_fixed_t1_mean_r)}R | {fmt_num(r.delta_vs_base_mean_r)}R |"
        )

    lines += ["","## Interpretation boundary",
        "S12 tests acceptance/persistence semantics at frozen T0.5 and anchor levels only.",
        "Runner targets remain T1.5/T2 and catastrophic protected-low CLOSE15 remains unchanged.",
        "Close-based failure never pre-empts a runner target already traded during the same raw 5m bar.",
        "No touch-stop, partial exit, new level, leverage, or dollar-PnL logic is introduced."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S12_POST_T1_RUNNER_FAILURE_CHARACTER_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
