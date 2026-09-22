#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S8_STRUCTURAL_INVALIDATION_SEMANTICS"
SRC=ROOT/"results/bnb_b40_s7/BNB_B40_S7_SD1_ENTRY_GEOMETRY_Ledger.csv.gz"

SD1_SIGNATURE="c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0"

CANDS=[
    ("PROTECTED_LOW_TOUCH","PROTECTED_LOW","TOUCH"),
    ("PROTECTED_LOW_CLOSE5","PROTECTED_LOW","CLOSE5"),
    ("PROTECTED_LOW_CLOSE15","PROTECTED_LOW","CLOSE15"),
    ("REACTION_LOW_TOUCH","REACTION_LOW","TOUCH"),
    ("REACTION_LOW_CLOSE5","REACTION_LOW","CLOSE5"),
    ("REACTION_LOW_CLOSE15","REACTION_LOW","CLOSE15"),
]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def boolify(s):
    if s.dtype==bool:return s
    return s.astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})

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
            cur+=1
            mx=max(mx,cur)
        else:
            cur=0
    return mx

def resolve_candidate(raw5,signal_ts,entry,level,target,deadline,semantics):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:
        return {"status":"UNRESOLVED","resolution_ts":pd.NaT,"exit_price":np.nan,"realized_r":0.0}

    risk=entry-level
    if not np.isfinite(risk) or risk<=0:
        return {"status":"UNAVAILABLE","resolution_ts":pd.NaT,"exit_price":np.nan,"realized_r":0.0}

    for j,i in enumerate(range(i0,i1)):
        b=raw5.iloc[i]
        target_here=float(b.high)>=target

        if semantics=="TOUCH":
            stop_here=float(b.low)<=level
            if target_here and stop_here:
                return {"status":"AMBIGUOUS","resolution_ts":idx[i],"exit_price":np.nan,"realized_r":0.0}
            if target_here:
                rr=(target-entry)/risk
                return {"status":"WIN","resolution_ts":idx[i],"exit_price":target,"realized_r":float(rr)}
            if stop_here:
                return {"status":"LOSS","resolution_ts":idx[i],"exit_price":level,"realized_r":-1.0}

        elif semantics=="CLOSE5":
            # target is resting intrabar; close-trigger only exists at bar completion.
            if target_here:
                rr=(target-entry)/risk
                return {"status":"WIN","resolution_ts":idx[i],"exit_price":target,"realized_r":float(rr)}
            if float(b.close)<level:
                rr=(float(b.close)-entry)/risk
                return {"status":"LOSS","resolution_ts":idx[i],"exit_price":float(b.close),"realized_r":float(rr)}

        elif semantics=="CLOSE15":
            # Same post-SD1 alignment as the 3x5m SD1 reaction window:
            # every third completed raw5 close after SD1 is a completed 15m reaction window.
            if target_here:
                rr=(target-entry)/risk
                return {"status":"WIN","resolution_ts":idx[i],"exit_price":target,"realized_r":float(rr)}
            if ((j+1)%3==0) and float(b.close)<level:
                rr=(float(b.close)-entry)/risk
                return {"status":"LOSS","resolution_ts":idx[i],"exit_price":float(b.close),"realized_r":float(rr)}
        else:
            raise RuntimeError(f"unknown semantics {semantics}")

    return {"status":"UNRESOLVED","resolution_ts":pd.NaT,"exit_price":np.nan,"realized_r":0.0}

def first_target_after(raw5,start_ts,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return pd.NaT
    hi=raw5.high.to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(hi>=target)
    return idx[i0+int(z[0])] if len(z) else pd.NaT

def false_stop_anatomy(raw5,stop_ts,later_target_ts,level,risk):
    if pd.isna(stop_ts) or pd.isna(later_target_ts) or risk<=0:
        return np.nan,np.nan
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(stop_ts),side="left"))
    i1=int(idx.searchsorted(pd.Timestamp(later_target_ts),side="right"))
    seg=raw5.iloc[i0:i1]
    if not len(seg):return np.nan,np.nan
    mins=float((pd.Timestamp(later_target_ts)-pd.Timestamp(stop_ts))/pd.Timedelta(minutes=1))
    overshoot=max(0.0,(level-float(seg.low.min()))/risk)
    return mins,overshoot

def load_parent():
    if not SRC.exists():raise RuntimeError(f"missing frozen S7 ledger: {SRC}")
    L=pd.read_csv(SRC,compression="gzip")
    for c in ["first_retest_ts","signal_ts","fill_ts","resolution_ts"]:
        if c in L.columns:
            L[c]=pd.to_datetime(L[c],utc=True,errors="coerce")
    for c in ["available","survived","GE1R","GE1_5R","GE2R","LOCAL_ONLY_SURVIVOR"]:
        if c in L.columns:
            L[c]=boolify(L[c])

    Q=L[L.candidate.eq("MARKET_SD1_CLOSE")].copy()
    exp={
        "DEV":(286,149,115,22),
        "REF":(160,87,59,14),
    }
    for per,(n,w,l,u) in exp.items():
        z=Q[Q.period==per]
        got=(len(z),int((z.status=="WIN").sum()),int((z.status=="LOSS").sum()),int((z.status=="UNRESOLVED").sum()))
        if got!=(n,w,l,u):
            raise RuntimeError(f"S7 MARKET baseline parity drift {per}: {got} != {(n,w,l,u)}")
    return Q

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    avail=q[q.available].copy()
    resolved=avail[avail.status.isin(["WIN","LOSS"])].copy()
    w=resolved[resolved.status=="WIN"]
    l=resolved[resolved.status=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    ge1=avail[avail.GE1R]
    false=ge1[(ge1.status=="LOSS") & ge1.later_target_after_stop]
    surv=avail[avail.survived]
    cons=avail[~avail.survived]
    local=avail[avail.LOCAL_ONLY_SURVIVOR]

    return {
        "signals":len(q),
        "available":len(avail),
        "availability_rate":len(avail)/len(q) if len(q) else np.nan,
        "median_level_distance_event_r":float(avail.level_distance_event_r.median()) if len(avail) else np.nan,
        "median_risk_compression":float(avail.risk_compression.median()) if len(avail) else np.nan,
        "resolved":len(resolved),
        "wins":len(w),"losses":len(l),
        "ambiguous":int((avail.status=="AMBIGUOUS").sum()),
        "unresolved":int((avail.status=="UNRESOLVED").sum()),
        "wr":len(w)/len(resolved) if len(resolved) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "mean_win_r":float(w.realized_r.mean()) if len(w) else np.nan,
        "median_loss_r":float(l.realized_r.median()) if len(l) else np.nan,
        "mean_loss_r":float(l.realized_r.mean()) if len(l) else np.nan,
        "loss_r_q10":float(l.realized_r.quantile(.10)) if len(l) else np.nan,
        "expectancy_per_signal":float(avail.realized_r.sum()/len(q)) if len(q) else np.nan,
        "total_r":float(avail.realized_r.sum()),
        "pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_dd_r":maxdd(avail.realized_r.tolist()) if len(avail) else np.nan,
        "max_loss_streak":maxls(avail.realized_r.tolist()) if len(avail) else np.nan,

        "ge1_available":len(ge1),
        "ge1_retained_win":int((ge1.status=="WIN").sum()),
        "ge1_false_stop":len(false),
        "ge1_false_stop_rate":len(false)/len(ge1) if len(ge1) else np.nan,
        "median_stop_to_later_target_min":float(false.stop_to_later_target_min.median()) if len(false) else np.nan,
        "median_false_stop_overshoot_r":float(false.false_stop_overshoot_r.median()) if len(false) else np.nan,

        "survive_available":len(surv),
        "survive_stopped":int((surv.status=="LOSS").sum()),
        "survive_stop_rate":float((surv.status=="LOSS").mean()) if len(surv) else np.nan,

        "consumed_available":len(cons),
        "consumed_stopped":int((cons.status=="LOSS").sum()),
        "consumed_catch_rate":float((cons.status=="LOSS").mean()) if len(cons) else np.nan,
        "consumed_won_target_first":int((cons.status=="WIN").sum()),

        "local_only_available":len(local),
        "local_only_stopped":int((local.status=="LOSS").sum()),
        "local_only_stop_rate":float((local.status=="LOSS").mean()) if len(local) else np.nan,
    }

def main():
    Q=load_parent()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)
    end=raw5.index.max()

    signature=hashlib.sha256(
        json.dumps({
            "parent":"B40_S7_MARKET_SD1_CLOSE",
            "sd1_signature":SD1_SIGNATURE,
            "levels":["PROTECTED_LOW","REACTION_LOW"],
            "semantics":["TOUCH","CLOSE5","CLOSE15"],
            "target":"ANCHOR_PLUS_1_EVENT_R",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    rows=[]
    for r in Q.itertuples(index=False):
        entry=float(r.sd1_close)
        target=float(r.target_anchor_1r)
        protected=float(r.floor)
        reaction=float(r.reaction_low)
        er=float(r.event_risk)
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))
        baseline_risk=entry-protected

        level_defs={"PROTECTED_LOW":protected,"REACTION_LOW":reaction}

        for cand,level_name,sem in CANDS:
            level=float(level_defs[level_name])
            available=bool(np.isfinite(level) and level<entry-1e-12 and entry-level>0)
            if available:
                z=resolve_candidate(raw5,r.signal_ts,entry,level,target,deadline,sem)
                status=z["status"]; rt=z["resolution_ts"]; exit_price=z["exit_price"]; rr=z["realized_r"]
            else:
                status="UNAVAILABLE"; rt=pd.NaT; exit_price=np.nan; rr=0.0

            risk=entry-level if available else np.nan
            comp=1.0-risk/baseline_risk if available and baseline_risk>0 else np.nan

            later=False; later_ts=pd.NaT; mins=np.nan; overs=np.nan
            if available and status=="LOSS":
                later_ts=first_target_after(raw5,rt,target,deadline)
                later=pd.notna(later_ts)
                if later:
                    mins,overs=false_stop_anatomy(raw5,rt,later_ts,level,risk)

            rows.append({
                "zone_id":r.zone_id,
                "period":r.period,
                "year":int(r.year),
                "first_retest_ts":r.first_retest_ts,
                "signal_ts":r.signal_ts,
                "candidate":cand,
                "level_name":level_name,
                "semantics":sem,
                "available":available,
                "entry":entry,
                "level":level,
                "target":target,
                "event_risk":er,
                "baseline_protected_risk":baseline_risk,
                "level_distance_event_r":risk/er if available and er>0 else np.nan,
                "risk_compression":comp,
                "status":status,
                "resolution_ts":rt,
                "exit_price":exit_price,
                "realized_r":rr,
                "survived":bool(r.survived),
                "GE1R":bool(r.GE1R),
                "GE1_5R":bool(r.GE1_5R),
                "GE2R":bool(r.GE2R),
                "LOCAL_ONLY_SURVIVOR":bool(r.LOCAL_ONLY_SURVIVOR),
                "later_target_after_stop":bool(later),
                "later_target_ts":later_ts,
                "stop_to_later_target_min":mins,
                "false_stop_overshoot_r":overs,
            })

    E=pd.DataFrame(rows)

    for per,n in {"DEV":286,"REF":160}.items():
        for cand,_,_ in CANDS:
            z=E[(E.period==per)&(E.candidate==cand)]
            if len(z)!=n:
                raise RuntimeError(f"row parity drift {per} {cand}: {len(z)} != {n}")

    # Baseline must reproduce S7 MARKET raw protected-low touch economics.
    for per,exp in {"DEV":(149,115,22),"REF":(87,59,14)}.items():
        z=E[(E.period==per)&(E.candidate=="PROTECTED_LOW_TOUCH")]
        got=(int((z.status=="WIN").sum()),int((z.status=="LOSS").sum()),int((z.status=="UNRESOLVED").sum()))
        if got!=exp:
            raise RuntimeError(f"protected-touch parity drift {per}: {got} != {exp}")

    SUM=[]
    for per in ["DEV","REF"]:
        for cand,_,_ in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            SUM.append({"period":per,"candidate":cand,**summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for cand,_,_ in CANDS:
            q=E[(E.year==y)&(E.candidate==cand)]
            if len(q):
                Y.append({"year":y,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    FS=E[(E.GE1R)&(E.status=="LOSS")&(E.later_target_after_stop)].copy()
    FSS=[]
    for per in ["DEV","REF"]:
        for cand,_,_ in CANDS:
            q=FS[(FS.period==per)&(FS.candidate==cand)]
            FSS.append({
                "period":per,"candidate":cand,"false_stops":len(q),
                "median_stop_to_later_target_min":float(q.stop_to_later_target_min.median()) if len(q) else np.nan,
                "median_overshoot_r":float(q.false_stop_overshoot_r.median()) if len(q) else np.nan,
            })
    FSS=pd.DataFrame(FSS)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FS.to_csv(ROOT/f"{PFX}_FalseStopLedger.csv.gz",index=False,compression="gzip")
    FSS.to_csv(ROOT/f"{PFX}_FalseStopSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT=B40_S7_MARKET_SD1_CLOSE\n"
        f"SD1_SIGNATURE_SHA256={SD1_SIGNATURE}\n"
        f"S8_SIGNATURE_SHA256={signature}\n"
        "ENTRY=MARKET_SD1_CLOSE\n"
        "TARGET=ANCHOR_PLUS_1_EVENT_R\n"
        "LEVELS=PROTECTED_LOW,REACTION_LOW\n"
        "SEMANTICS=TOUCH,CLOSE5,CLOSE15\n"
        "CLOSE_EXIT_PRICE=ACTUAL_COMPLETED_CLOSE\n"
        "NO_BUFFERS=TRUE\nNO_THRESHOLD_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S8 — Structural Invalidation Semantics Discovery","",
        f"Frozen SD1 signature: `{SD1_SIGNATURE}`",
        f"S8 signature: `{signature}`","",
        "Entry = MARKET_SD1_CLOSE. Target = anchor +1 event-R. Only structural invalidation level/semantics change.","",
        "## Invalidation audit","",
        "| Period | Candidate | Avail | Level dist | Compression | W-L | WR | Med WIN R | Med LOSS R | Loss q10 | Exp/signal | Total R | PF | GE1 retained | False stop | Survivor stopped | Consumed caught |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.available}/{r.signals} | "
            f"{fmt_num(r.median_level_distance_event_r)} event-R | {fmt_pct(r.median_risk_compression)} | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.median_loss_r)}R | {fmt_num(r.loss_r_q10)}R | "
            f"{fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | {fmt_num(r.pf)} | "
            f"{r.ge1_retained_win}/{r.ge1_available} | {r.ge1_false_stop} ({fmt_pct(r.ge1_false_stop_rate)}) | "
            f"{r.survive_stopped}/{r.survive_available} ({fmt_pct(r.survive_stop_rate)}) | "
            f"{r.consumed_stopped}/{r.consumed_available} ({fmt_pct(r.consumed_catch_rate)}) |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | W-L | WR | Med LOSS R | Exp/signal | Total R | GE1 false-stop | Consumed caught |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.wins}-{r.losses} | {fmt_pct(r.wr)} | "
            f"{fmt_num(r.median_loss_r)}R | {fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | "
            f"{r.ge1_false_stop}/{r.ge1_available} ({fmt_pct(r.ge1_false_stop_rate)}) | "
            f"{r.consumed_stopped}/{r.consumed_available} ({fmt_pct(r.consumed_catch_rate)}) |"
        )

    lines += ["","## False-stop anatomy","",
        "| Period | Candidate | False stops | Med stop→later target | Med overshoot below level |",
        "|---|---|---:|---:|---:|"
    ]
    for r in FSS.itertuples(index=False):
        if r.false_stops:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_stops} | "
                f"{fmt_num(r.median_stop_to_later_target_min,1)}m | {fmt_num(r.median_overshoot_r)} initial-R |"
            )

    lines += ["","## Interpretation boundary",
        "S8 changes only structural invalidation semantics; demand construction, SD1, and market entry remain frozen.",
        "CLOSE5/CLOSE15 losses use the actual completed close, so tail loss can exceed -1R.",
        "A close-based rule is not preferred merely because it reduces false stops; DEV/REF expectancy and loss-tail behavior must also remain acceptable.",
        "No final TP or XP1 runner policy is changed in S8."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S8_STRUCTURAL_INVALIDATION_SEMANTICS_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
