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
PFX="BNB_B40_S11_MILESTONE_RUNNER_PROTECTION"

XP1_SIGNATURE="3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8"
XP1_MIN=60.0

POLICIES=[
    "BASE_XP1_T15_UNPROTECTED",
    "PROTECT_T05_TOUCH_T15",
    "PROTECT_ANCHOR_TOUCH_T15",
    "PROTECT_HL5_TOUCH_T15",
    "BASE_XP1_T2_UNPROTECTED",
    "PROTECT_T05_TOUCH_T2",
    "PROTECT_ANCHOR_TOUCH_T2",
    "PROTECT_HL5_TOUCH_T2",
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

def parse_policy(policy):
    target="T15" if policy.endswith("T15") else "T2"
    if policy.startswith("BASE_"): mode="NONE"
    elif "T05_TOUCH" in policy: mode="T05"
    elif "ANCHOR_TOUCH" in policy: mode="ANCHOR"
    elif "HL5_TOUCH" in policy: mode="HL5"
    else: raise RuntimeError(policy)
    return mode,target

def first_target_after(raw5,start_ts,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return pd.NaT
    z=np.flatnonzero(raw5.high.to_numpy(float,copy=False)[i0:i1]>=target)
    return idx[i0+int(z[0])] if len(z) else pd.NaT

def resolve_protected(raw5,r,policy,deadline):
    mode,target_name=parse_policy(policy)
    if mode=="NONE":
        base_policy="XP1_EXTEND_T15" if target_name=="T15" else "XP1_EXTEND_T2"
        z=s10.resolve_policy(raw5,r,base_policy,deadline)
        return {
            **z,
            "runner_started":bool(z["xp1_active"] and z["t1_hit"]),
            "protection_exit":False,
            "protection_price":np.nan,
            "protection_mode":"NONE",
            "catastrophic_exit":z["status"]=="STOP_BEFORE_FULL_TARGET",
            "samebar_stop_first":False,
            "hl_updates":0,
        }

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
    runner_target=t15 if target_name=="T15" else t2
    xp_deadline=pd.Timestamp(r.first_retest_ts)+pd.Timedelta(minutes=XP1_MIN)

    xp1=False
    xp1_ts=pd.NaT
    t1_hit=False
    t15_hit=False
    t2_hit=False
    t1_ts=pd.NaT
    t15_ts=pd.NaT
    t2_ts=pd.NaT

    runner_started=False
    runner_start_bar=None
    stop_floor=None
    pending_floor=None
    hl_updates=0
    samebar_stop_first=False
    post_t1_lows=[]  # tuples (bar_index, low)
    protection_exit=False
    protection_price=np.nan
    catastrophic_exit=False
    status=None
    realized=0.0
    resolution_ts=pd.NaT

    for j,i in enumerate(range(i0,i1)):
        b=raw5.iloc[i]
        ts=idx[i]
        high=float(b.high); low=float(b.low)

        # Pending dynamic floor becomes active only from the bar after confirmation.
        if pending_floor is not None:
            stop_floor=pending_floor if stop_floor is None else max(stop_floor,pending_floor)
            pending_floor=None

        if (not xp1) and ts<=xp_deadline and high>=t05:
            xp1=True; xp1_ts=ts

        if high>=t1 and not t1_hit:
            t1_hit=True; t1_ts=ts
        if high>=t15 and not t15_hit:
            t15_hit=True; t15_ts=ts
        if high>=t2 and not t2_hit:
            t2_hit=True; t2_ts=ts

        # Non-XP1 trades always remain FIXED_T1 controls.
        if not xp1:
            if high>=t1:
                realized=(t1-entry)/risk
                status="TARGET_T1_NO_XP1"
                resolution_ts=ts
                break
        else:
            # Once T1 trades, runner mode begins.
            if (not runner_started) and high>=t1:
                runner_started=True
                runner_start_bar=i
                # If the same bar reaches farther target, monotonic upside path makes target executable.
                if high>=runner_target:
                    realized=(runner_target-entry)/risk
                    status=f"TARGET_{target_name}_SAME_MILESTONE_BAR"
                    resolution_ts=ts
                    break
                # Static protection intentionally activates on NEXT raw5 bar.
                if mode=="T05":
                    pending_floor=t05
                elif mode=="ANCHOR":
                    pending_floor=anchor
                elif mode=="HL5":
                    # T1 bar serves only as left context; the pivot itself must be post-T1.
                    post_t1_lows=[(i,low)]
            elif runner_started:
                # Resting target and resting protection are both active.
                target_here=high>=runner_target
                stop_here=(stop_floor is not None and low<=stop_floor)

                if target_here and stop_here:
                    # Conservative preregistered ordering.
                    samebar_stop_first=True
                    protection_exit=True
                    protection_price=float(stop_floor)
                    realized=(float(stop_floor)-entry)/risk
                    status="PROTECTION_STOP_SAMEBAR_CONSERVATIVE"
                    resolution_ts=ts
                    break
                if stop_here:
                    protection_exit=True
                    protection_price=float(stop_floor)
                    realized=(float(stop_floor)-entry)/risk
                    status="PROTECTION_STOP"
                    resolution_ts=ts
                    break
                if target_here:
                    realized=(runner_target-entry)/risk
                    status=f"TARGET_{target_name}_RUNNER"
                    resolution_ts=ts
                    break

                if mode=="HL5":
                    post_t1_lows.append((i,low))

        # Catastrophic structural failure is checked only after intrabar target/protection.
        if ((j+1)%3==0) and float(b.close)<floor:
            realized=(float(b.close)-entry)/risk
            catastrophic_exit=True
            status="CATASTROPHIC_CLOSE15"
            resolution_ts=ts
            break

        # Dynamic pivot confirmation happens at bar close; newly confirmed floor starts NEXT bar.
        if mode=="HL5" and runner_started and len(post_t1_lows)>=3:
            (ia,la),(ib,lb),(ic,lc)=post_t1_lows[-3:]
            if ib>runner_start_bar and lb<la and lb<lc and lb>t05:
                new_floor=float(lb)
                current=stop_floor if stop_floor is not None else -np.inf
                queued=pending_floor if pending_floor is not None else -np.inf
                if new_floor>max(current,queued):
                    pending_floor=new_floor
                    hl_updates+=1

    if status is None:
        status="UNRESOLVED"
        resolution_ts=pd.NaT

    return {
        "status":status,
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
        "runner_started":bool(runner_started),
        "protection_exit":bool(protection_exit),
        "protection_price":protection_price,
        "protection_mode":mode,
        "catastrophic_exit":bool(catastrophic_exit),
        "samebar_stop_first":bool(samebar_stop_first),
        "hl_updates":int(hl_updates),
    }

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    pos=q[q.realized_r>1e-12]
    neg=q[q.realized_r<-1e-12]
    zer=q[np.abs(q.realized_r)<=1e-12]
    ps=float(pos.realized_r.sum()) if len(pos) else 0.0
    ns=abs(float(neg.realized_r.sum())) if len(neg) else 0.0

    runners=q[q.runner_started]
    prot=q[q.protection_exit]

    return {
        "n":len(q),
        "runner_n":len(runners),
        "runner_rate":len(runners)/len(q) if len(q) else np.nan,
        "target_hits":int(q.status.str.startswith("TARGET_").sum()),
        "protection_exits":len(prot),
        "catastrophic_exits":int(q.catastrophic_exit.sum()),
        "unresolved":int((q.status=="UNRESOLVED").sum()),
        "samebar_stop_first":int(q.samebar_stop_first.sum()),
        "positive_n":len(pos),"negative_n":len(neg),"zero_n":len(zer),
        "expectancy_r":float(q.realized_r.mean()) if len(q) else np.nan,
        "total_r":float(q.realized_r.sum()),
        "pf":ps/ns if ns>0 else (np.inf if ps>0 else np.nan),
        "max_dd_r":maxdd(q.realized_r.tolist()),
        "max_loss_streak":maxls(q.realized_r.tolist()),
        "median_realized_r":float(q.realized_r.median()) if len(q) else np.nan,
        "median_protection_r":float(prot.realized_r.median()) if len(prot) else np.nan,
        "mean_protection_r":float(prot.realized_r.mean()) if len(prot) else np.nan,
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
            "parent":"B40_S10_XP1_RUNNERS",
            "xp1_signature":XP1_SIGNATURE,
            "milestone":"XP1_PLUS_T1",
            "runner_targets":["T1.5","T2"],
            "protection":["NONE","T0.5_TOUCH","ANCHOR_TOUCH","CONFIRMED_HL5_TOUCH"],
            "samebar":"STOP_FIRST_CONSERVATIVE",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    rows=[]
    for r in Q.itertuples(index=False):
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        fixed=s10.resolve_policy(raw5,r,"FIXED_T1",deadline)
        for policy in POLICIES:
            z=resolve_protected(raw5,r,policy,deadline)
            target_name="T15" if policy.endswith("T15") else "T2"
            target_price=(float(r.target_anchor_1r)+0.5*float(r.event_risk)) if target_name=="T15" else (float(r.target_anchor_1r)+1.0*float(r.event_risk))
            later_target=pd.NaT
            if z["protection_exit"] and pd.notna(z["resolution_ts"]):
                later_target=first_target_after(raw5,z["resolution_ts"],target_price,deadline)
            rows.append({
                "zone_id":r.zone_id,
                "period":r.period,
                "year":int(r.year),
                "first_retest_ts":r.first_retest_ts,
                "signal_ts":r.signal_ts,
                "policy":policy,
                "runner_target":target_name,
                "status":z["status"],
                "resolution_ts":z["resolution_ts"],
                "realized_r":z["realized_r"],
                "fixed_t1_r":float(fixed["realized_r"]),
                "xp1_active":z["xp1_active"],
                "t1_hit":z["t1_hit"],
                "t15_hit":z["t15_hit"],
                "t2_hit":z["t2_hit"],
                "runner_started":z["runner_started"],
                "protection_exit":z["protection_exit"],
                "protection_price":z["protection_price"],
                "protection_mode":z["protection_mode"],
                "catastrophic_exit":z["catastrophic_exit"],
                "samebar_stop_first":z["samebar_stop_first"],
                "hl_updates":z["hl_updates"],
                "later_target_after_protection":pd.notna(later_target),
                "later_target_ts":later_target,
            })

    E=pd.DataFrame(rows)
    E["incremental_vs_fixed_t1_r"]=E.realized_r-E.fixed_t1_r

    for per,n in {"DEV":286,"REF":160}.items():
        for policy in POLICIES:
            z=E[(E.period==per)&(E.policy==policy)]
            if len(z)!=n:
                raise RuntimeError(f"row parity drift {per} {policy}: {len(z)} != {n}")

    # Frozen S10 parity for unprotected controls and runner cohort.
    expected={
        ("DEV","BASE_XP1_T15_UNPROTECTED"):(-0.0026184988461730807,93,71),
        ("REF","BASE_XP1_T15_UNPROTECTED"):(0.10414146030743787,57,46),
        ("DEV","BASE_XP1_T2_UNPROTECTED"):(-0.028768926571244035,93,71),
        ("REF","BASE_XP1_T2_UNPROTECTED"):(0.12018378488852513,57,46),
    }
    for (per,policy),(exp,xpn,run_n) in expected.items():
        z=E[(E.period==per)&(E.policy==policy)]
        got=float(z.realized_r.mean())
        if abs(got-exp)>1e-12:
            raise RuntimeError(f"S10 control expectancy drift {per} {policy}: {got} != {exp}")
        if int(z.xp1_active.sum())!=xpn or int(z.runner_started.sum())!=run_n:
            raise RuntimeError(f"S10 runner cohort drift {per} {policy}")

    # Matching unprotected baseline per target family.
    baselines=[]
    for target,base_policy in [("T15","BASE_XP1_T15_UNPROTECTED"),("T2","BASE_XP1_T2_UNPROTECTED")]:
        b=E[E.policy==base_policy][["zone_id","realized_r","status"]].copy()
        b=b.rename(columns={"realized_r":"matching_base_r","status":"matching_base_status"})
        b["runner_target"]=target
        baselines.append(b)
    BM=pd.concat(baselines,ignore_index=True)
    E=E.merge(BM,on=["zone_id","runner_target"],how="left",validate="many_to_one")
    E["incremental_vs_matching_base_r"]=E.realized_r-E.matching_base_r

    # Continuation preservation: matching unprotected target winners.
    E["matching_true_continuation"]=E.matching_base_status.str.startswith("TARGET_")
    E["continuation_retained"]=E.matching_true_continuation & E.status.str.startswith("TARGET_")
    E["continuation_cut"]=E.matching_true_continuation & E.protection_exit

    SUM=[]
    for per in ["DEV","REF"]:
        for policy in POLICIES:
            q=E[(E.period==per)&(E.policy==policy)]
            d=summarize(q)
            cont=q[q.matching_true_continuation]
            bad=q[~q.matching_true_continuation]
            prot_bad=bad[bad.protection_exit]
            d.update({
                "delta_vs_fixed_t1_mean_r":float(q.incremental_vs_fixed_t1_r.mean()),
                "delta_vs_matching_base_mean_r":float(q.incremental_vs_matching_base_r.mean()),
                "delta_vs_matching_base_total_r":float(q.incremental_vs_matching_base_r.sum()),
                "true_continuations":len(cont),
                "continuation_retained":int(cont.continuation_retained.sum()),
                "continuation_cut":int(cont.continuation_cut.sum()),
                "continuation_retention_rate":float(cont.continuation_retained.mean()) if len(cont) else np.nan,
                "giveback_protection_exits":len(prot_bad),
                "median_giveback_protection_r":float(prot_bad.realized_r.median()) if len(prot_bad) else np.nan,
                "median_giveback_improvement_r":float(prot_bad.incremental_vs_matching_base_r.median()) if len(prot_bad) else np.nan,
                "nonpos_to_positive":int(((prot_bad.matching_base_r<=0)&(prot_bad.realized_r>0)).sum()),
            })
            SUM.append({"period":per,"policy":policy,**d})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for policy in POLICIES:
            q=E[(E.year==y)&(E.policy==policy)]
            if len(q):
                d=summarize(q)
                cont=q[q.matching_true_continuation]
                d.update({
                    "delta_vs_fixed_t1_mean_r":float(q.incremental_vs_fixed_t1_r.mean()),
                    "delta_vs_matching_base_mean_r":float(q.incremental_vs_matching_base_r.mean()),
                    "continuation_retention_rate":float(cont.continuation_retained.mean()) if len(cont) else np.nan,
                })
                Y.append({"year":y,"policy":policy,**d})
    Y=pd.DataFrame(Y)

    # Runner-only diagnostics.
    RD=[]
    for per in ["DEV","REF"]:
        for policy in POLICIES:
            q=E[(E.period==per)&(E.policy==policy)&(E.runner_started)]
            cont=q[q.matching_true_continuation]
            cuts=q[q.continuation_cut]
            RD.append({
                "period":per,"policy":policy,"runner_n":len(q),
                "target_hits":int(q.status.str.startswith("TARGET_").sum()),
                "protection_exits":int(q.protection_exit.sum()),
                "catastrophic_exits":int(q.catastrophic_exit.sum()),
                "unresolved":int((q.status=="UNRESOLVED").sum()),
                "continuations":len(cont),
                "continuation_retained":int(cont.continuation_retained.sum()),
                "continuation_cut":len(cuts),
                "retention_rate":float(cont.continuation_retained.mean()) if len(cont) else np.nan,
                "later_target_after_cut":int(cuts.later_target_after_protection.sum()) if len(cuts) else 0,
                "median_protection_r":float(q.loc[q.protection_exit,"realized_r"].median()) if q.protection_exit.any() else np.nan,
                "incremental_vs_base_total_r":float(q.incremental_vs_matching_base_r.sum()),
            })
    RD=pd.DataFrame(RD)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    RD.to_csv(ROOT/f"{PFX}_RunnerDiagnostics.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S10_XP1_RUNNER\n"
        f"XP1_SIGNATURE_SHA256={XP1_SIGNATURE}\n"
        f"S11_SIGNATURE_SHA256={signature}\n"
        "RUNNER_MILESTONE=XP1_PLUS_T1\n"
        "RUNNER_TARGETS=T1.5,T2\n"
        "PROTECTIONS=NONE,T0.5_TOUCH,ANCHOR_TOUCH,CONFIRMED_POST_T1_HL5_TOUCH\n"
        "STATIC_PROTECTION_ACTIVATION=NEXT_RAW5_BAR_AFTER_T1\n"
        "HL5_PIVOT=1L1R_AND_ABOVE_T0.5\n"
        "SAME_BAR_TARGET_STOP=STOP_FIRST_CONSERVATIVE\n"
        "NO_PARTIAL_EXIT=TRUE\nNO_PARAMETER_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S11 — Milestone Runner Protection","",
        f"XP1 signature: `{XP1_SIGNATURE}`",
        f"S11 signature: `{signature}`","",
        "Protection is allowed only after XP1 is active AND T1 has traded. Non-runner trades remain FIXED_T1.","",
        "## Whole-policy economics","",
        "| Period | Policy | Runner N | Target hits | Protect exits | Catastrophic | Unresolved | Exp/signal | Total R | PF | MaxDD | Δ vs T1 | Δ vs unprotected | Continuation retained | Protection med R |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.runner_n} | {r.target_hits} | {r.protection_exits} | "
            f"{r.catastrophic_exits} | {r.unresolved} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.pf)} | {fmt_num(r.max_dd_r)}R | {fmt_num(r.delta_vs_fixed_t1_mean_r)}R | "
            f"{fmt_num(r.delta_vs_matching_base_mean_r)}R | {r.continuation_retained}/{r.true_continuations} "
            f"({fmt_pct(r.continuation_retention_rate)}) | {fmt_num(r.median_protection_r)}R |"
        )

    lines += ["","## Runner-only diagnostics","",
        "| Period | Policy | Runner | Target | Protect | Catastrophic | Unresolved | Continuation retained | Cut continuations | Later target after cut | Incremental vs base |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in RD.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.runner_n} | {r.target_hits} | {r.protection_exits} | "
            f"{r.catastrophic_exits} | {r.unresolved} | {r.continuation_retained}/{r.continuations} "
            f"({fmt_pct(r.retention_rate)}) | {r.continuation_cut} | {r.later_target_after_cut} | "
            f"{fmt_num(r.incremental_vs_base_total_r)}R |"
        )

    lines += ["","## Annual stability","",
        "| Year | Policy | Exp/signal | Total R | PF | MaxDD | Δ vs T1 | Δ vs unprotected | Continuation retention |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.policy} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.pf)} | {fmt_num(r.max_dd_r)}R | {fmt_num(r.delta_vs_fixed_t1_mean_r)}R | "
            f"{fmt_num(r.delta_vs_matching_base_mean_r)}R | {fmt_pct(r.continuation_retention_rate)} |"
        )

    lines += ["","## Interpretation boundary",
        "S11 changes runner protection only after the frozen XP1 + T1 milestone.",
        "Static protection begins on the next raw 5m bar after T1; dynamic HL5 protection begins only after causal pivot confirmation.",
        "Same-bar runner target and protection touch is resolved conservatively as STOP-FIRST.",
        "No partial exit, new target distance, pivot-width search, or leverage/PnL conversion is introduced."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S11_MILESTONE_RUNNER_PROTECTION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
