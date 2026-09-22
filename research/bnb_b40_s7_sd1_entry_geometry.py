#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S7_SD1_ENTRY_GEOMETRY"
S1=ROOT/"results/bnb_b40_s1/BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_CandidateLedger.csv.gz"
S3=ROOT/"results/bnb_b40_s3/BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY_DecisionLedger.csv.gz"

SD1_SIGNATURE="c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0"

CANDS=[
    "MARKET_SD1_CLOSE",
    "LIMIT_HALF_RETRACE",
    "LIMIT_TOUCH_ANCHOR",
    "LIMIT_ZONE_HIGH",
    "LIMIT_REACTION_LOW",
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

def first_touch_idx(raw5,start_ts,level,kind,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def resolve_after(raw5,start_ts,entry,floor,target,deadline):
    idx=raw5.index
    ti=first_touch_idx(raw5,start_ts,target,"HIGH",deadline)
    si=first_touch_idx(raw5,start_ts,floor,"LOW",deadline)
    rr=(target-entry)/(entry-floor)
    if ti is None and si is None:
        return {"status":"UNRESOLVED","resolution_ts":pd.NaT,"realized_r":0.0}
    if ti is not None and si is not None and ti==si:
        return {"status":"AMBIGUOUS_AFTER_ENTRY","resolution_ts":idx[ti],"realized_r":0.0}
    if ti is not None and (si is None or ti<si):
        return {"status":"WIN","resolution_ts":idx[ti],"realized_r":float(rr)}
    return {"status":"LOSS","resolution_ts":idx[si],"realized_r":-1.0}

def limit_trade(raw5,signal_ts,limit,floor,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:
        return {"status":"NO_FILL_END","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":0.0}

    lo=raw5.low.to_numpy(float,copy=False)
    hi=raw5.high.to_numpy(float,copy=False)

    fill_i=None
    for i in range(i0,i1):
        target_here=hi[i]>=target
        floor_here=lo[i]<=floor
        can_fill=lo[i]<=limit<=hi[i]

        if can_fill:
            if target_here or floor_here:
                return {
                    "status":"AMBIGUOUS_FILL_BAR","fill_ts":idx[i],
                    "resolution_ts":idx[i],"realized_r":0.0
                }
            fill_i=i
            break

        if target_here and floor_here:
            return {
                "status":"NO_FILL_AMBIGUOUS_RESOLUTION","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }
        if target_here:
            return {
                "status":"NO_FILL_TARGET_FIRST","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }
        if floor_here:
            return {
                "status":"NO_FILL_FLOOR_FIRST","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }

    if fill_i is None:
        return {"status":"NO_FILL_END","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":0.0}

    z=resolve_after(raw5,idx[fill_i],limit,floor,target,deadline)
    return {
        "status":z["status"],"fill_ts":idx[fill_i],
        "resolution_ts":z["resolution_ts"],"realized_r":z["realized_r"]
    }

def load_cohort():
    if not S1.exists():raise RuntimeError(f"missing {S1}")
    if not S3.exists():raise RuntimeError(f"missing {S3}")

    A=pd.read_csv(S1,compression="gzip")
    B=pd.read_csv(S3,compression="gzip")

    for c in ["first_retest_ts","activation_ts","consumption_ts","survival_resolution_ts"]:
        if c in A.columns:A[c]=pd.to_datetime(A[c],utc=True,errors="coerce")
    for c in ["first_retest_ts","decision_ts"]:
        if c in B.columns:B[c]=pd.to_datetime(B[c],utc=True,errors="coerce")

    for c in ["normalizable","hit_1_0r","hit_1_5r","hit_2_0r"]:
        if c in A.columns:A[c]=boolify(A[c])
    for c in ["survived","CLOSE15_ABOVE_ANCHOR"]:
        B[c]=boolify(B[c])

    Q=B[
        (B.decision=="PLUS15_CLOSE")&
        (B.decision_status=="ELIGIBLE")&
        (B.CLOSE15_ABOVE_ANCHOR)
    ].copy()

    exp={"DEV":(286,235,51),"REF":(160,137,23)}
    for per,(n,s,c) in exp.items():
        z=Q[Q.period==per]
        got=(len(z),int(z.survived.sum()),int((~z.survived).sum()))
        if got!=(n,s,c):
            raise RuntimeError(f"SD1 parity drift {per}: {got} != {(n,s,c)}")

    cols=[
        "zone_id","base_high","protected_low","hit_1_0r","hit_1_5r","hit_2_0r",
        "time_to_0_5r_min","mfe_pre_consumption_24h_r"
    ]
    P=A[cols].copy()
    if P.zone_id.duplicated().any():raise RuntimeError("S1 duplicate zone_id")

    Q=Q.merge(P,on="zone_id",how="left",validate="one_to_one")
    if Q.protected_low.isna().any():raise RuntimeError("missing S1 merge rows")

    Q["GE1R"]=Q.hit_1_0r.astype(bool)
    Q["GE1_5R"]=Q.hit_1_5r.astype(bool)
    Q["GE2R"]=Q.hit_2_0r.astype(bool)
    Q["LOCAL_ONLY_SURVIVOR"]=Q.survived & (~Q.GE1R)
    return Q

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    avail=q[q.available].copy()
    filled=avail[avail.status.isin(["WIN","LOSS","UNRESOLVED","AMBIGUOUS_AFTER_ENTRY"])].copy()
    resolved=filled[filled.status.isin(["WIN","LOSS"])].copy()
    w=resolved[resolved.status=="WIN"]
    l=resolved[resolved.status=="LOSS"]
    nofill=avail[avail.status.str.startswith("NO_FILL")].copy()

    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    fill_ids=set(filled.zone_id)
    win_ids=set(w.zone_id)
    loss_ids=set(l.zone_id)
    nofill_ids=set(nofill.zone_id)

    ge1=avail[avail.GE1R]
    survivors=avail[avail.survived]
    consumed=avail[~avail.survived]
    local=avail[avail.LOCAL_ONLY_SURVIVOR]

    filled_delay=filled[pd.notna(filled.fill_ts)].copy()
    if len(filled_delay):
        delays=(pd.to_datetime(filled_delay.fill_ts,utc=True)-pd.to_datetime(filled_delay.signal_ts,utc=True))/pd.Timedelta(minutes=1)
        med_delay=float(delays.median())
    else:
        med_delay=np.nan

    return {
        "signals":len(q),
        "available":len(avail),
        "filled":len(filled),
        "fill_rate":len(filled)/len(avail) if len(avail) else np.nan,
        "resolved":len(resolved),
        "wins":len(w),
        "losses":len(l),
        "wr_resolved":len(w)/len(resolved) if len(resolved) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "mean_win_r":float(w.realized_r.mean()) if len(w) else np.nan,
        "expectancy_per_filled":float(filled.realized_r.mean()) if len(filled) else np.nan,
        "expectancy_per_signal":float(avail.realized_r.sum()/len(q)) if len(q) else np.nan,
        "total_r":float(avail.realized_r.sum()),
        "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_drawdown_r":maxdd(avail.realized_r.tolist()) if len(avail) else np.nan,
        "max_loss_streak":maxls(avail.realized_r.tolist()) if len(avail) else np.nan,
        "median_entry_improvement_event_r":float(avail.entry_improvement_event_r.median()) if len(avail) else np.nan,
        "median_risk_compression":float(avail.risk_compression_vs_market.median()) if len(avail) else np.nan,
        "median_target_rr":float(avail.target_rr.median()) if len(avail) else np.nan,
        "median_fill_delay_min":med_delay,

        "ge1_available":len(ge1),
        "ge1_filled":len(set(ge1.zone_id)&fill_ids),
        "ge1_resolve_win":len(set(ge1.zone_id)&win_ids),
        "ge1_missed_nofill":len(set(ge1.zone_id)&nofill_ids),
        "ge1_became_loss":len(set(ge1.zone_id)&loss_ids),

        "survive_available":len(survivors),
        "survive_filled":len(set(survivors.zone_id)&fill_ids),
        "survive_missed_nofill":len(set(survivors.zone_id)&nofill_ids),

        "consumed_available":len(consumed),
        "consumed_avoided_nofill":len(set(consumed.zone_id)&nofill_ids),
        "consumed_avoid_rate":len(set(consumed.zone_id)&nofill_ids)/len(consumed) if len(consumed) else np.nan,

        "local_only_available":len(local),
        "local_only_avoided_nofill":len(set(local.zone_id)&nofill_ids),
        "local_only_avoid_rate":len(set(local.zone_id)&nofill_ids)/len(local) if len(local) else np.nan,

        "ambiguous_fill_bar":int((avail.status=="AMBIGUOUS_FILL_BAR").sum()),
        "ambiguous_after_entry":int((avail.status=="AMBIGUOUS_AFTER_ENTRY").sum()),
        "unresolved_after_entry":int((avail.status=="UNRESOLVED").sum()),
    }

def main():
    Q=load_cohort()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    raw5=raw[["open","high","low","close"]].astype(float)
    end=raw5.index.max()

    signature=hashlib.sha256(
        json.dumps({
            "parent_detector":"SD1_CLOSE15_ABOVE_ANCHOR",
            "parent_signature":SD1_SIGNATURE,
            "entries":CANDS,
            "audit_target":"ANCHOR_PLUS_1_EVENT_R",
            "audit_floor":"PROTECTED_LOW",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    rows=[]
    for r in Q.itertuples(index=False):
        anchor=float(r.touch_close)
        er=float(r.event_risk)
        floor=float(r.protected_low)
        target=anchor+er
        signal=float(anchor+float(r.p15_close_r)*er)
        reaction_low=float(anchor+float(r.p15_low_r)*er)
        zone_high=float(r.base_high)
        deadline=min(end,pd.Timestamp(r.first_retest_ts)+pd.Timedelta(hours=24))

        levels={
            "MARKET_SD1_CLOSE":signal,
            "LIMIT_HALF_RETRACE":anchor+0.50*(signal-anchor),
            "LIMIT_TOUCH_ANCHOR":anchor,
            "LIMIT_ZONE_HIGH":zone_high,
            "LIMIT_REACTION_LOW":reaction_low,
        }

        market_risk=signal-floor

        for cand in CANDS:
            entry=float(levels[cand])
            available=bool(
                np.isfinite(entry) and
                entry>floor+1e-12 and
                entry<target-1e-12 and
                (cand=="MARKET_SD1_CLOSE" or entry<signal-1e-12)
            )

            if not available:
                status="UNAVAILABLE"
                fill_ts=pd.NaT
                res_ts=pd.NaT
                rr=0.0
            elif cand=="MARKET_SD1_CLOSE":
                z=resolve_after(raw5,r.decision_ts,entry,floor,target,deadline)
                status=z["status"]
                fill_ts=r.decision_ts
                res_ts=z["resolution_ts"]
                rr=z["realized_r"]
            else:
                z=limit_trade(raw5,r.decision_ts,entry,floor,target,deadline)
                status=z["status"]
                fill_ts=z["fill_ts"]
                res_ts=z["resolution_ts"]
                rr=z["realized_r"]

            risk=entry-floor if available else np.nan
            target_rr=(target-entry)/risk if available and risk>0 else np.nan

            rows.append({
                "zone_id":r.zone_id,
                "period":r.period,
                "year":int(r.year),
                "first_retest_ts":r.first_retest_ts,
                "signal_ts":r.decision_ts,
                "candidate":cand,
                "available":available,
                "anchor":anchor,
                "sd1_close":signal,
                "candidate_entry":entry,
                "reaction_low":reaction_low,
                "zone_high":zone_high,
                "floor":floor,
                "target_anchor_1r":target,
                "event_risk":er,
                "entry_improvement_event_r":(signal-entry)/er if available else np.nan,
                "risk_compression_vs_market":1.0-risk/market_risk if available and market_risk>0 else np.nan,
                "target_rr":target_rr,
                "status":status,
                "fill_ts":fill_ts,
                "resolution_ts":res_ts,
                "realized_r":rr,
                "survived":bool(r.survived),
                "GE1R":bool(r.GE1R),
                "GE1_5R":bool(r.GE1_5R),
                "GE2R":bool(r.GE2R),
                "LOCAL_ONLY_SURVIVOR":bool(r.LOCAL_ONLY_SURVIVOR),
            })

    E=pd.DataFrame(rows)

    # exact entry candidate rows per frozen signal
    for per,n in {"DEV":286,"REF":160}.items():
        for cand in CANDS:
            z=E[(E.period==per)&(E.candidate==cand)]
            if len(z)!=n:
                raise RuntimeError(f"entry row parity drift {per} {cand}: {len(z)} != {n}")

    SUM=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            SUM.append({"period":per,"candidate":cand,**summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for cand in CANDS:
            q=E[(E.year==y)&(E.candidate==cand)]
            if len(q):
                Y.append({"year":y,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    ST=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            for st,z in q.groupby("status"):
                ST.append({"period":per,"candidate":cand,"status":st,"n":len(z)})
    ST=pd.DataFrame(ST)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StatusCensus.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_DETECTOR=SD1_CLOSE15_ABOVE_ANCHOR\n"
        f"PARENT_SIGNATURE_SHA256={SD1_SIGNATURE}\n"
        f"ENTRY_STUDY_SIGNATURE_SHA256={signature}\n"
        "AUDIT_TARGET=ANCHOR_PLUS_1_EVENT_R\n"
        "AUDIT_FLOOR=PROTECTED_LOW\n"
        "ORDER_ACTIVATION=STRICTLY_AFTER_SD1_DECISION_BAR\n"
        "DEADLINE=24H_FROM_FIRST_RETEST\n"
        "CANDIDATES=MARKET_SD1_CLOSE,LIMIT_HALF_RETRACE,LIMIT_TOUCH_ANCHOR,LIMIT_ZONE_HIGH,LIMIT_REACTION_LOW\n"
        "XP1_USED_FOR_ENTRY=FALSE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S7 — Frozen SD1 Post-Confirmation Entry Geometry","",
        f"Frozen SD1 signature: `{SD1_SIGNATURE}`",
        f"Entry-study signature: `{signature}`","",
        "Cohort = SD1 PASS only. XP1 is NOT used for entry selection.",
        "Audit target = anchor +1 event-R; structural audit floor = protected_low; all limits activate strictly after SD1 closes.","",
        "## Entry geometry","",
        "| Period | Candidate | Fill | W-L | WR | Med WIN R | Exp/fill | Exp/signal | Total R | PF | Med target R:R | Improvement | Risk compression | GE1 fill/win | GE1 missed | GE1→LOSS | Consumed avoided | Local-only avoided |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.filled}/{r.available} ({fmt_pct(r.fill_rate)}) | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr_resolved)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.expectancy_per_filled)}R | {fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.profit_factor)} | {fmt_num(r.median_target_rr)} | "
            f"{fmt_num(r.median_entry_improvement_event_r)} event-R | {fmt_pct(r.median_risk_compression)} | "
            f"{r.ge1_filled}/{r.ge1_resolve_win} of {r.ge1_available} | {r.ge1_missed_nofill} | "
            f"{r.ge1_became_loss} | {r.consumed_avoided_nofill}/{r.consumed_available} ({fmt_pct(r.consumed_avoid_rate)}) | "
            f"{r.local_only_avoided_nofill}/{r.local_only_available} ({fmt_pct(r.local_only_avoid_rate)}) |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | Fill | W-L | WR | Exp/signal | Total R | Med target R:R | GE1 missed | Consumed avoided |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.filled}/{r.available} | {r.wins}-{r.losses} | "
            f"{fmt_pct(r.wr_resolved)} | {fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.median_target_rr)} | {r.ge1_missed_nofill} | {r.consumed_avoided_nofill} |"
        )

    lines += ["","## Interpretation boundary",
        "S7 changes entry geometry only; H1 demand and SD1 remain frozen.",
        "No-fill, ambiguous, and unresolved cases contribute 0R to per-signal audit economics.",
        "The protected-low floor and +1 event-R objective are audit geometry, not yet final SL/TP.",
        "A deeper entry is not preferred automatically if it improves R:R by missing too many genuine expanders or selectively filling weak pullbacks."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S7_SD1_ENTRY_GEOMETRY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
