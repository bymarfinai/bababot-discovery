#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b40_s8_structural_invalidation_semantics as s8

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S10_TP_XP1_RUNNER_GEOMETRY"

XP1_SIGNATURE="3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8"
XP1_MIN=60.0

POLICIES=[
    "FIXED_T1",
    "FIXED_T15",
    "FIXED_T2",
    "XP1_EXTEND_T15",
    "XP1_EXTEND_T2",
    "XP1_SCALE50_T15",
    "XP1_SCALE50_T2",
]

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

def resolve_policy(raw5,r,policy,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(r.signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))

    entry=float(r.sd1_close)
    floor=float(r.floor)
    er=float(r.event_risk)
    anchor=float(r.target_anchor_1r)-er
    risk=entry-floor
    if risk<=0:
        return {"status":"UNAVAILABLE","realized_r":0.0}

    t05=anchor+0.5*er
    t1=anchor+1.0*er
    t15=anchor+1.5*er
    t2=anchor+2.0*er
    xp_deadline=pd.Timestamp(r.first_retest_ts)+pd.Timedelta(minutes=XP1_MIN)

    rr1=(t1-entry)/risk
    rr15=(t15-entry)/risk
    rr2=(t2-entry)/risk

    xp1=False
    xp1_ts=pd.NaT
    t1_hit=False
    t15_hit=False
    t2_hit=False
    t1_ts=pd.NaT
    t15_ts=pd.NaT
    t2_ts=pd.NaT
    realized=0.0
    runner_weight=1.0
    partial_realized=False
    stop_after_partial=False
    resolution_ts=pd.NaT
    exit_status=None

    for j,i in enumerate(range(i0,i1)):
        b=raw5.iloc[i]
        ts=idx[i]
        high=float(b.high)

        # XP1 becomes causally active on a bar that reaches T0.5 within 60m of first retest.
        if (not xp1) and ts<=xp_deadline and high>=t05:
            xp1=True
            xp1_ts=ts

        if high>=t1 and not t1_hit:
            t1_hit=True; t1_ts=ts
        if high>=t15 and not t15_hit:
            t15_hit=True; t15_ts=ts
        if high>=t2 and not t2_hit:
            t2_hit=True; t2_ts=ts

        # Target execution has intrabar priority over close-based structural failure.
        if policy=="FIXED_T1":
            if high>=t1:
                realized=rr1; resolution_ts=ts; exit_status="TARGET_T1"
                break

        elif policy=="FIXED_T15":
            if high>=t15:
                realized=rr15; resolution_ts=ts; exit_status="TARGET_T15"
                break

        elif policy=="FIXED_T2":
            if high>=t2:
                realized=rr2; resolution_ts=ts; exit_status="TARGET_T2"
                break

        elif policy=="XP1_EXTEND_T15":
            target=t15 if xp1 else t1
            if high>=target:
                realized=(rr15 if xp1 else rr1)
                resolution_ts=ts
                exit_status="TARGET_T15_XP1" if xp1 else "TARGET_T1_NO_XP1"
                break

        elif policy=="XP1_EXTEND_T2":
            target=t2 if xp1 else t1
            if high>=target:
                realized=(rr2 if xp1 else rr1)
                resolution_ts=ts
                exit_status="TARGET_T2_XP1" if xp1 else "TARGET_T1_NO_XP1"
                break

        elif policy in ("XP1_SCALE50_T15","XP1_SCALE50_T2"):
            runner_target=t15 if policy.endswith("T15") else t2
            runner_rr=rr15 if policy.endswith("T15") else rr2

            if not xp1:
                if high>=t1:
                    realized=rr1; resolution_ts=ts; exit_status="TARGET_T1_NO_XP1"
                    break
            else:
                if (not partial_realized) and high>=t1:
                    realized += 0.5*rr1
                    runner_weight=0.5
                    partial_realized=True
                if partial_realized and high>=runner_target:
                    realized += 0.5*runner_rr
                    runner_weight=0.0
                    resolution_ts=ts
                    exit_status="TARGET_RUNNER"
                    break
        else:
            raise RuntimeError(policy)

        # Structural failure only on each aligned third completed raw-5m close.
        if ((j+1)%3==0) and float(b.close)<floor:
            close_r=(float(b.close)-entry)/risk
            if policy.startswith("XP1_SCALE50") and partial_realized:
                realized += runner_weight*close_r
                stop_after_partial=True
                runner_weight=0.0
                exit_status="STOP_AFTER_PARTIAL"
            else:
                realized=close_r
                runner_weight=0.0
                exit_status="STOP_BEFORE_FULL_TARGET"
            resolution_ts=ts
            break

    if exit_status is None:
        exit_status="UNRESOLVED"
        resolution_ts=pd.NaT
        # Closed partial remains realized; open weight contributes 0R by prereg.
    
    return {
        "status":exit_status,
        "resolution_ts":resolution_ts,
        "realized_r":float(realized),
        "xp1_active":bool(xp1),
        "xp1_ts":xp1_ts,
        "t1_hit":bool(t1_hit),
        "t15_hit":bool(t15_hit),
        "t2_hit":bool(t2_hit),
        "t1_ts":t1_ts,
        "t15_ts":t15_ts,
        "t2_ts":t2_ts,
        "partial_realized":bool(partial_realized),
        "stop_after_partial":bool(stop_after_partial),
        "remaining_weight_at_end":float(runner_weight if exit_status=="UNRESOLVED" else 0.0),
        "rr_t1":float(rr1),
        "rr_t15":float(rr15),
        "rr_t2":float(rr2),
    }

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    pos=q[q.realized_r>1e-12]
    neg=q[q.realized_r<-1e-12]
    zer=q[np.abs(q.realized_r)<=1e-12]
    positive=float(pos.realized_r.sum()) if len(pos) else 0.0
    negative=abs(float(neg.realized_r.sum())) if len(neg) else 0.0

    xp=q[q.xp1_active]
    xp_t1=xp[xp.t1_hit]
    xp_t15=xp[xp.t15_hit]
    xp_t2=xp[xp.t2_hit]

    return {
        "n":len(q),
        "xp1_active":len(xp),
        "xp1_rate":len(xp)/len(q) if len(q) else np.nan,
        "full_target_hit":int(q.status.str.startswith("TARGET").sum()),
        "full_target_hit_rate":float(q.status.str.startswith("TARGET").mean()) if len(q) else np.nan,
        "any_t1_hit":int(q.t1_hit.sum()),
        "any_t1_hit_rate":float(q.t1_hit.mean()) if len(q) else np.nan,
        "stop_before_any_target":int(((q.status=="STOP_BEFORE_FULL_TARGET")&(~q.t1_hit)).sum()),
        "stop_after_partial":int(q.stop_after_partial.sum()),
        "unresolved":int((q.status=="UNRESOLVED").sum()),
        "positive_n":len(pos),
        "negative_n":len(neg),
        "zero_n":len(zer),
        "positive_rate":len(pos)/len(q) if len(q) else np.nan,
        "negative_rate":len(neg)/len(q) if len(q) else np.nan,
        "zero_rate":len(zer)/len(q) if len(q) else np.nan,
        "median_positive_r":float(pos.realized_r.median()) if len(pos) else np.nan,
        "mean_positive_r":float(pos.realized_r.mean()) if len(pos) else np.nan,
        "median_negative_r":float(neg.realized_r.median()) if len(neg) else np.nan,
        "mean_negative_r":float(neg.realized_r.mean()) if len(neg) else np.nan,
        "expectancy_r":float(q.realized_r.mean()) if len(q) else np.nan,
        "total_r":float(q.realized_r.sum()),
        "pf":positive/negative if negative>0 else (np.inf if positive>0 else np.nan),
        "max_dd_r":maxdd(q.realized_r.tolist()) if len(q) else np.nan,
        "max_loss_streak":maxls(q.realized_r.tolist()) if len(q) else np.nan,
        "median_realized_r":float(q.realized_r.median()) if len(q) else np.nan,
        "q10_realized_r":float(q.realized_r.quantile(.10)) if len(q) else np.nan,
        "q90_realized_r":float(q.realized_r.quantile(.90)) if len(q) else np.nan,
        "xp_t1":len(xp_t1),
        "xp_t15":len(xp_t15),
        "xp_t2":len(xp_t2),
        "xp_t1_to_t15":len(xp_t15)/len(xp_t1) if len(xp_t1) else np.nan,
        "xp_t1_to_t2":len(xp_t2)/len(xp_t1) if len(xp_t1) else np.nan,
        "xp_stop_after_partial":int(xp.stop_after_partial.sum()) if len(xp) else 0,
        "xp_unresolved":int((xp.status=="UNRESOLVED").sum()) if len(xp) else 0,
    }

def main():
    Q=s8.load_parent()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)
    end=raw5.index.max()

    signature=hashlib.sha256(
        json.dumps({
            "parent":"B40_S7_MARKET_SD1_CLOSE",
            "structural_invalidation":"PROTECTED_LOW_CLOSE15",
            "xp1_signature":XP1_SIGNATURE,
            "xp1_minutes":XP1_MIN,
            "policies":POLICIES,
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    rows=[]
    for r in Q.itertuples(index=False):
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        for policy in POLICIES:
            z=resolve_policy(raw5,r,policy,deadline)
            rows.append({
                "zone_id":r.zone_id,
                "period":r.period,
                "year":int(r.year),
                "first_retest_ts":r.first_retest_ts,
                "signal_ts":r.signal_ts,
                "policy":policy,
                "entry":float(r.sd1_close),
                "protected_low":float(r.floor),
                "event_risk":float(r.event_risk),
                "anchor":float(r.target_anchor_1r)-float(r.event_risk),
                "status":z["status"],
                "resolution_ts":z["resolution_ts"],
                "realized_r":z["realized_r"],
                "xp1_active":z["xp1_active"],
                "xp1_ts":z["xp1_ts"],
                "t1_hit":z["t1_hit"],
                "t15_hit":z["t15_hit"],
                "t2_hit":z["t2_hit"],
                "t1_ts":z["t1_ts"],
                "t15_ts":z["t15_ts"],
                "t2_ts":z["t2_ts"],
                "partial_realized":z["partial_realized"],
                "stop_after_partial":z["stop_after_partial"],
                "remaining_weight_at_end":z["remaining_weight_at_end"],
                "rr_t1":z["rr_t1"],
                "rr_t15":z["rr_t15"],
                "rr_t2":z["rr_t2"],
                "survived":bool(r.survived),
                "GE1R":bool(r.GE1R),
                "GE1_5R":bool(r.GE1_5R),
                "GE2R":bool(r.GE2R),
            })

    E=pd.DataFrame(rows)

    for per,n in {"DEV":286,"REF":160}.items():
        for policy in POLICIES:
            z=E[(E.period==per)&(E.policy==policy)]
            if len(z)!=n:
                raise RuntimeError(f"row parity drift {per} {policy}: {len(z)} != {n}")

    # FIXED_T1 must reproduce B40-S8 PROTECTED_LOW_CLOSE15 exactly.
    expected={
        "DEV":(163,94,29,-0.014735246869563585),
        "REF":(99,44,17,0.13469997139091092),
    }
    for per,(w,l,u,exp_r) in expected.items():
        z=E[(E.period==per)&(E.policy=="FIXED_T1")]
        got=(int((z.status=="TARGET_T1").sum()),int((z.status=="STOP_BEFORE_FULL_TARGET").sum()),int((z.status=="UNRESOLVED").sum()))
        if got!=(w,l,u):
            raise RuntimeError(f"FIXED_T1 status parity drift {per}: {got} != {(w,l,u)}")
        if abs(float(z.realized_r.mean())-exp_r)>1e-12:
            raise RuntimeError(f"FIXED_T1 expectancy drift {per}: {z.realized_r.mean()} != {exp_r}")

    # XP1 activation itself is policy invariant.
    for per in ["DEV","REF"]:
        counts=[]
        for policy in POLICIES:
            z=E[(E.period==per)&(E.policy==policy)]
            counts.append(int(z.xp1_active.sum()))
        if len(set(counts))!=1:
            raise RuntimeError(f"XP1 activation drift across policies {per}: {counts}")

    # Add identical-signal incremental R versus FIXED_T1.
    base=E[E.policy=="FIXED_T1"][["zone_id","realized_r"]].rename(columns={"realized_r":"fixed_t1_r"})
    E=E.merge(base,on="zone_id",how="left",validate="many_to_one")
    E["incremental_vs_fixed_t1_r"]=E.realized_r-E.fixed_t1_r

    SUM=[]
    for per in ["DEV","REF"]:
        for policy in POLICIES:
            q=E[(E.period==per)&(E.policy==policy)]
            d=summarize(q)
            d["incremental_vs_fixed_t1_total_r"]=float(q.incremental_vs_fixed_t1_r.sum())
            d["incremental_vs_fixed_t1_mean_r"]=float(q.incremental_vs_fixed_t1_r.mean())
            SUM.append({"period":per,"policy":policy,**d})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for policy in POLICIES:
            q=E[(E.year==y)&(E.policy==policy)]
            if len(q):
                d=summarize(q)
                d["incremental_vs_fixed_t1_total_r"]=float(q.incremental_vs_fixed_t1_r.sum())
                d["incremental_vs_fixed_t1_mean_r"]=float(q.incremental_vs_fixed_t1_r.mean())
                Y.append({"year":y,"policy":policy,**d})
    Y=pd.DataFrame(Y)

    XD=[]
    for per in ["DEV","REF"]:
        for policy in [p for p in POLICIES if p.startswith("XP1_")]:
            q=E[(E.period==per)&(E.policy==policy)&(E.xp1_active)]
            XD.append({
                "period":per,"policy":policy,"xp1_n":len(q),
                "t1_hit":int(q.t1_hit.sum()),
                "t15_hit":int(q.t15_hit.sum()),
                "t2_hit":int(q.t2_hit.sum()),
                "t1_to_t15":float(q.t15_hit.sum()/q.t1_hit.sum()) if q.t1_hit.sum() else np.nan,
                "t1_to_t2":float(q.t2_hit.sum()/q.t1_hit.sum()) if q.t1_hit.sum() else np.nan,
                "stop_after_partial":int(q.stop_after_partial.sum()),
                "unresolved":int((q.status=="UNRESOLVED").sum()),
                "incremental_vs_fixed_t1_total_r":float(q.incremental_vs_fixed_t1_r.sum()),
                "incremental_vs_fixed_t1_mean_r":float(q.incremental_vs_fixed_t1_r.mean()) if len(q) else np.nan,
            })
    XD=pd.DataFrame(XD)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    XD.to_csv(ROOT/f"{PFX}_XP1Diagnostics.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S7_MARKET_SD1_CLOSE\n"
        f"STRUCTURAL_INVALIDATION=PROTECTED_LOW_CLOSE15\n"
        f"XP1_SIGNATURE_SHA256={XP1_SIGNATURE}\n"
        f"S10_SIGNATURE_SHA256={signature}\n"
        "XP1_FAST_PROOF_MINUTES_LTE=60\n"
        "TARGETS_EVENT_R=0.5,1.0,1.5,2.0\n"
        "PARTIAL_WEIGHT=0.5\n"
        "UNRESOLVED_OPEN_WEIGHT_REALIZED_R=0\n"
        "NO_TRAILING_STOP=TRUE\nNO_WEIGHT_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S10 — TP / XP1 Runner Geometry","",
        f"XP1 signature: `{XP1_SIGNATURE}`",
        f"S10 signature: `{signature}`","",
        "Entry = MARKET_SD1_CLOSE. Structural failure = aligned 15m close below protected-low.",
        "XP1 activates causally on +0.5 event-R within <=60m from first retest.","",
        "## TP / runner economics","",
        "| Period | Policy | XP1 | Full target | Positive | Negative | Exp/signal | Total R | PF | MaxDD | Med +R | Med -R | Δ vs T1 | T1→1.5 XP1 | T1→2 XP1 | Stop after partial |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.xp1_active}/{r.n} ({fmt_pct(r.xp1_rate)}) | "
            f"{r.full_target_hit}/{r.n} ({fmt_pct(r.full_target_hit_rate)}) | "
            f"{r.positive_n}/{r.n} ({fmt_pct(r.positive_rate)}) | {r.negative_n}/{r.n} ({fmt_pct(r.negative_rate)}) | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | {fmt_num(r.pf)} | {fmt_num(r.max_dd_r)}R | "
            f"{fmt_num(r.median_positive_r)}R | {fmt_num(r.median_negative_r)}R | "
            f"{fmt_num(r.incremental_vs_fixed_t1_mean_r)}R | {fmt_pct(r.xp_t1_to_t15)} | {fmt_pct(r.xp_t1_to_t2)} | "
            f"{r.stop_after_partial} |"
        )

    lines += ["","## Annual stability","",
        "| Year | Policy | Exp/signal | Total R | PF | Positive | Negative | Δ vs T1 | MaxDD |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.policy} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.pf)} | {fmt_pct(r.positive_rate)} | {fmt_pct(r.negative_rate)} | "
            f"{fmt_num(r.incremental_vs_fixed_t1_mean_r)}R | {fmt_num(r.max_dd_r)}R |"
        )

    lines += ["","## XP1 runner diagnostics","",
        "| Period | Policy | XP1 N | T1 | T1.5 | T2 | T1→1.5 | T1→2 | Stop after partial | Unresolved | Incremental vs T1 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in XD.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.xp1_n} | {r.t1_hit} | {r.t15_hit} | {r.t2_hit} | "
            f"{fmt_pct(r.t1_to_t15)} | {fmt_pct(r.t1_to_t2)} | {r.stop_after_partial} | {r.unresolved} | "
            f"{fmt_num(r.incremental_vs_fixed_t1_total_r)}R |"
        )

    lines += ["","## Interpretation boundary",
        "S10 changes TP/runner geometry only; demand, SD1, entry, protected-low, and close15 structural failure remain frozen.",
        "XP1 is activated from the live raw path; future B40-S6 labels are not used to turn runners on.",
        "Unresolved open runner weight contributes 0R rather than an invented mark-to-market value.",
        "No leverage or dollar PnL is inferred from R in this stage."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S10_TP_XP1_RUNNER_GEOMETRY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
