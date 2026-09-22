#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b40_s8_structural_invalidation_semantics as s8

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S9_PROTECTED_LOW_FAILURE_PRECURSOR"

CANDS=[
    "P1_FIRST_CLOSE5_BELOW",
    "P2_FULL_BODY5_BELOW",
    "P3_TWO_CONSEC_CLOSE5_BELOW",
    "P4_RECLAIM_ATTEMPT_REJECT",
]
BASELINE="BASELINE_CLOSE15"

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
            cur+=1; mx=max(mx,cur)
        else:
            cur=0
    return mx

def baseline_close15(raw5,r,deadline):
    return s8.resolve_candidate(
        raw5,
        r.signal_ts,
        float(r.sd1_close),
        float(r.floor),
        float(r.target_anchor_1r),
        deadline,
        "CLOSE15"
    )

def first_target_after(raw5,start_ts,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return pd.NaT
    hi=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(hi>=target)
    return idx[i0+int(z[0])] if len(z) else pd.NaT

def reclaim_flags(raw5,signal_ts,level,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    i1=min(len(idx),int(idx.searchsorted(pd.Timestamp(deadline),side="right")))
    if i0>=i1:
        return False,False
    next5=bool(float(raw5.close.iloc[i0])>=level)
    upto=min(i1,i0+3)
    within15=bool((raw5.close.iloc[i0:upto]>=level).any())
    return next5,within15

def eval_precursor(raw5,r,deadline,cand):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(r.signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    entry=float(r.sd1_close)
    level=float(r.floor)
    target=float(r.target_anchor_1r)
    risk=entry-level

    below_history=[]
    first_breach_i=None

    for j,i in enumerate(range(i0,i1)):
        b=raw5.iloc[i]
        target_here=float(b.high)>=target
        if target_here:
            return {"status":"NO_SIGNAL_TARGET_FIRST","signal_ts":pd.NaT,"exit_price":np.nan}

        is_baseline_fail=((j+1)%3==0) and float(b.close)<level

        signal=False
        if cand=="P1_FIRST_CLOSE5_BELOW":
            signal=float(b.close)<level

        elif cand=="P2_FULL_BODY5_BELOW":
            signal=float(b.open)<level and float(b.close)<level

        elif cand=="P3_TWO_CONSEC_CLOSE5_BELOW":
            signal=(len(below_history)>=1 and below_history[-1] and float(b.close)<level)

        elif cand=="P4_RECLAIM_ATTEMPT_REJECT":
            if first_breach_i is not None and i==first_breach_i+1:
                signal=float(b.high)>=level and float(b.close)<level

        else:
            raise RuntimeError(cand)

        if signal:
            if is_baseline_fail:
                return {"status":"SAME_AS_BASELINE","signal_ts":idx[i],"exit_price":float(b.close)}
            rr=(float(b.close)-entry)/risk
            return {"status":"CLEAN_SIGNAL","signal_ts":idx[i],"exit_price":float(b.close),"realized_r":float(rr)}

        if first_breach_i is None and float(b.close)<level:
            first_breach_i=i

        below_history.append(float(b.close)<level)

        if is_baseline_fail:
            return {"status":"BASELINE_FAILURE_FIRST","signal_ts":pd.NaT,"exit_price":np.nan}

    return {"status":"NO_SIGNAL_END","signal_ts":pd.NaT,"exit_price":np.nan}

def false_exit_anatomy(raw5,signal_ts,level,target,deadline,entry,risk):
    later=first_target_after(raw5,signal_ts,target,deadline)
    if pd.isna(later):
        return {
            "later_target_ts":pd.NaT,
            "minutes_signal_to_target":np.nan,
            "reclaim_next5":False,
            "reclaim_within15":False,
            "overshoot_r":np.nan
        }
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="left"))
    i1=int(idx.searchsorted(pd.Timestamp(later),side="right"))
    seg=raw5.iloc[i0:i1]
    next5,within15=reclaim_flags(raw5,signal_ts,level,deadline)
    overs=max(0.0,(level-float(seg.low.min()))/risk) if len(seg) and risk>0 else np.nan
    return {
        "later_target_ts":later,
        "minutes_signal_to_target":float((later-pd.Timestamp(signal_ts))/pd.Timedelta(minutes=1)),
        "reclaim_next5":next5,
        "reclaim_within15":within15,
        "overshoot_r":overs
    }

def summarize(q,base_exp):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    bl=q[q.baseline_status=="LOSS"]
    bw=q[q.baseline_status=="WIN"]
    clean=q[q.precursor_status=="CLEAN_SIGNAL"]
    cap=clean[clean.baseline_status=="LOSS"]
    false=clean[clean.baseline_status=="WIN"]

    cf=q.copy()
    cf["cf_r"]=np.where(cf.precursor_status=="CLEAN_SIGNAL",cf.precursor_realized_r,cf.baseline_realized_r)
    pos=float(cf.loc[cf.cf_r>0,"cf_r"].sum())
    neg=abs(float(cf.loc[cf.cf_r<0,"cf_r"].sum()))
    exp=float(cf.cf_r.mean()) if len(cf) else np.nan

    return {
        "n":len(q),
        "baseline_wins":len(bw),
        "baseline_losses":len(bl),
        "clean_signals":len(clean),
        "signal_rate":len(clean)/len(q) if len(q) else np.nan,
        "loss_captured":len(cap),
        "loss_capture_rate":len(cap)/len(bl) if len(bl) else np.nan,
        "winner_false_exit":len(false),
        "winner_false_exit_rate":len(false)/len(bw) if len(bw) else np.nan,
        "precision_loss":len(cap)/len(clean) if len(clean) else np.nan,
        "median_precursor_exit_r_loss":float(cap.precursor_realized_r.median()) if len(cap) else np.nan,
        "median_baseline_loss_r_captured":float(cap.baseline_realized_r.median()) if len(cap) else np.nan,
        "median_r_saved":float((cap.precursor_realized_r-cap.baseline_realized_r).median()) if len(cap) else np.nan,
        "median_lead_to_baseline_failure_min":float(cap.lead_to_baseline_failure_min.median()) if len(cap) else np.nan,
        "median_false_exit_to_target_min":float(false.minutes_signal_to_target.median()) if len(false) else np.nan,
        "false_reclaim_next5_rate":float(false.reclaim_next5.mean()) if len(false) else np.nan,
        "false_reclaim_within15_rate":float(false.reclaim_within15.mean()) if len(false) else np.nan,
        "cf_expectancy_r":exp,
        "cf_total_r":float(cf.cf_r.sum()),
        "cf_pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "cf_max_dd_r":maxdd(cf.cf_r.tolist()),
        "cf_max_loss_streak":maxls(cf.cf_r.tolist()),
        "delta_vs_baseline":exp-base_exp,
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
            "parent":"B40_S8_PROTECTED_LOW_CLOSE15",
            "candidates":CANDS,
            "level":"PROTECTED_LOW",
            "target":"ANCHOR_PLUS_1_EVENT_R",
            "strictly_before_baseline_close15":True,
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    baseline_exp={
        "DEV":-0.014735246869563585,
        "REF":0.13469997139091092,
    }

    rows=[]
    basecheck={"DEV":{"WIN":0,"LOSS":0,"UNRESOLVED":0},"REF":{"WIN":0,"LOSS":0,"UNRESOLVED":0}}

    for r in Q.itertuples(index=False):
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        bz=baseline_close15(raw5,r,deadline)
        bs=bz["status"]; br=float(bz["realized_r"]); bt=bz["resolution_ts"]
        if bs in basecheck[r.period]:basecheck[r.period][bs]+=1

        for cand in CANDS:
            z=eval_precursor(raw5,r,deadline,cand)
            pr=z.get("realized_r",np.nan)
            lead=np.nan
            if z["status"]=="CLEAN_SIGNAL" and bs=="LOSS" and pd.notna(bt):
                lead=float((pd.Timestamp(bt)-pd.Timestamp(z["signal_ts"]))/pd.Timedelta(minutes=1))

            anat={
                "later_target_ts":pd.NaT,
                "minutes_signal_to_target":np.nan,
                "reclaim_next5":False,
                "reclaim_within15":False,
                "overshoot_r":np.nan,
            }
            if z["status"]=="CLEAN_SIGNAL" and bs=="WIN":
                entry=float(r.sd1_close)
                level=float(r.floor)
                target=float(r.target_anchor_1r)
                anat=false_exit_anatomy(
                    raw5,z["signal_ts"],level,target,deadline,entry,entry-level
                )

            rows.append({
                "zone_id":r.zone_id,
                "period":r.period,
                "year":int(r.year),
                "signal_ts":r.signal_ts,
                "candidate":cand,
                "baseline_status":bs,
                "baseline_realized_r":br,
                "baseline_resolution_ts":bt,
                "precursor_status":z["status"],
                "precursor_ts":z["signal_ts"],
                "precursor_exit_price":z["exit_price"],
                "precursor_realized_r":pr,
                "lead_to_baseline_failure_min":lead,
                "survived":bool(r.survived),
                "GE1R":bool(r.GE1R),
                **anat,
            })

    expected={
        "DEV":{"WIN":163,"LOSS":94,"UNRESOLVED":29},
        "REF":{"WIN":99,"LOSS":44,"UNRESOLVED":17},
    }
    if basecheck!=expected:
        raise RuntimeError(f"S8 close15 baseline parity drift {basecheck}")

    E=pd.DataFrame(rows)

    SUM=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            SUM.append({
                "period":per,"candidate":cand,
                **summarize(q,baseline_exp[per])
            })
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        per="DEV" if y<=2024 else "REF"
        for cand in CANDS:
            q=E[(E.year==y)&(E.candidate==cand)]
            if len(q):
                bl=q[q.baseline_status=="LOSS"]
                bw=q[q.baseline_status=="WIN"]
                clean=q[q.precursor_status=="CLEAN_SIGNAL"]
                cap=clean[clean.baseline_status=="LOSS"]
                false=clean[clean.baseline_status=="WIN"]
                cf=q.copy()
                cf["cf_r"]=np.where(cf.precursor_status=="CLEAN_SIGNAL",cf.precursor_realized_r,cf.baseline_realized_r)
                Y.append({
                    "year":y,"candidate":cand,"n":len(q),
                    "loss_captured":len(cap),"baseline_losses":len(bl),
                    "loss_capture_rate":len(cap)/len(bl) if len(bl) else np.nan,
                    "winner_false_exit":len(false),"baseline_wins":len(bw),
                    "winner_false_exit_rate":len(false)/len(bw) if len(bw) else np.nan,
                    "precision_loss":len(cap)/len(clean) if len(clean) else np.nan,
                    "median_r_saved":float((cap.precursor_realized_r-cap.baseline_realized_r).median()) if len(cap) else np.nan,
                    "cf_expectancy_r":float(cf.cf_r.mean()),
                    "cf_total_r":float(cf.cf_r.sum()),
                })
    Y=pd.DataFrame(Y)

    FS=E[(E.precursor_status=="CLEAN_SIGNAL")&(E.baseline_status=="WIN")].copy()
    FSS=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=FS[(FS.period==per)&(FS.candidate==cand)]
            FSS.append({
                "period":per,"candidate":cand,
                "false_exits":len(q),
                "reclaim_next5_rate":float(q.reclaim_next5.mean()) if len(q) else np.nan,
                "reclaim_within15_rate":float(q.reclaim_within15.mean()) if len(q) else np.nan,
                "median_signal_to_target_min":float(q.minutes_signal_to_target.median()) if len(q) else np.nan,
                "median_overshoot_r":float(q.overshoot_r.median()) if len(q) else np.nan,
            })
    FSS=pd.DataFrame(FSS)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FSS.to_csv(ROOT/f"{PFX}_FalseExitSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S8_PROTECTED_LOW_CLOSE15\n"
        f"S9_SIGNATURE_SHA256={signature}\n"
        "LEVEL=PROTECTED_LOW\n"
        "BASELINE=ALIGNED_CLOSE15_BELOW_PROTECTED_LOW\n"
        "CANDIDATES=P1_FIRST_CLOSE5_BELOW,P2_FULL_BODY5_BELOW,P3_TWO_CONSEC_CLOSE5_BELOW,P4_RECLAIM_ATTEMPT_REJECT\n"
        "PRECURSOR_MUST_BE_STRICTLY_BEFORE_BASELINE=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S9 — Protected-Low Failure Precursor / Exit Timing","",
        f"S9 signature: `{signature}`",
        "Parent structural failure = aligned 15m close below protected-low. Entry/target/level unchanged.","",
        "## Precursor audit","",
        "| Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | Med early loss R | Med baseline loss R | Med R saved | Lead to failure | CF Exp | Δ vs baseline | Total R | PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.clean_signals}/{r.n} ({fmt_pct(r.signal_rate)}) | "
            f"{r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.precision_loss)} | {fmt_num(r.median_precursor_exit_r_loss)}R | "
            f"{fmt_num(r.median_baseline_loss_r_captured)}R | {fmt_num(r.median_r_saved)}R | "
            f"{fmt_num(r.median_lead_to_baseline_failure_min,1)}m | {fmt_num(r.cf_expectancy_r)}R | "
            f"{fmt_num(r.delta_vs_baseline)}R | {fmt_num(r.cf_total_r)}R | {fmt_num(r.cf_pf)} |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | Med R saved | CF Exp | Total R |",
        "|---:|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.precision_loss)} | {fmt_num(r.median_r_saved)}R | "
            f"{fmt_num(r.cf_expectancy_r)}R | {fmt_num(r.cf_total_r)}R |"
        )

    lines += ["","## False-exit rescue anatomy","",
        "| Period | Candidate | False exits | Reclaim next5 | Reclaim <=15m | Med signal→target | Med overshoot |",
        "|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in FSS.itertuples(index=False):
        if r.false_exits:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_exits} | "
                f"{fmt_pct(r.reclaim_next5_rate)} | {fmt_pct(r.reclaim_within15_rate)} | "
                f"{fmt_num(r.median_signal_to_target_min,1)}m | {fmt_num(r.median_overshoot_r)}R |"
            )

    lines += ["","## Interpretation boundary",
        "S9 tests earlier timing only; protected-low remains the structural level.",
        "A precursor is rejected unless it improves counterfactual expectancy in both DEV and REF while keeping false exits very low.",
        "Signals occurring on the same bar as the aligned 15m baseline failure are not credited as earlier.",
        "No TP, XP1 runner, or entry logic changes in S9."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S9_PROTECTED_LOW_FAILURE_PRECURSOR_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
