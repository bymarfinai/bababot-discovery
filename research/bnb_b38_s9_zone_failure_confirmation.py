#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S9_ZONE_FAILURE_CONFIRMATION"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
REF_START=pd.Timestamp("2025-01-01T00:00:00Z")

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level","tp2_rr"),
}
CONDS=[
    "BASELINE_ALL",
    "K1_BREAK_FIRST_TOUCH_HIGH",
    "K2_BULLISH_DISPLACEMENT_BREAK_PREV_HIGH",
    "K3_TWO_CLOSE_PROXIMAL_HOLD",
    "K4_POST_TOUCH_CONFIRMED_MICRO_BOS",
    "K5_BREAK_TOUCH_HIGH_AND_TWO_CLOSE_HOLD",
]

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def zone_validity(m15,fam,end):
    idx=m15.index
    rows=[]
    for r in fam.itertuples(index=False):
        z1=float(r.demand_high+r.demand_width)
        i0=int(idx.searchsorted(r.first_touch_ts,side="right"))
        i1=int(idx.searchsorted(end,side="right"))
        valid=False
        invalid_ts=pd.NaT
        z1_ts=pd.NaT
        for i in range(i0,i1):
            c=float(m15.close.iloc[i]); t=idx[i]
            if c<float(r.demand_low):
                invalid_ts=t
                break
            if c>z1:
                valid=True; z1_ts=t
                break
        rows.append({
            "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,
            "zone_1zw_valid":valid,"z1_hit_ts":z1_ts,"zone_invalid_ts":invalid_ts,
        })
    return pd.DataFrame(rows)

def resolve(raw5,entry_ts,entry,sl,tp,end):
    idx=raw5.index
    i0=int(idx.searchsorted(entry_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return "UNRESOLVED",pd.NaT
    hi=raw5.high.to_numpy(float,copy=False)[i0:i1]
    lo=raw5.low.to_numpy(float,copy=False)[i0:i1]
    th=np.flatnonzero(hi>=tp)
    sh=np.flatnonzero(lo<=sl)
    ti=int(th[0]) if len(th) else None
    si=int(sh[0]) if len(sh) else None
    if ti is None and si is None:return "UNRESOLVED",pd.NaT
    if ti is not None and si is not None and ti==si:return "AMBIGUOUS",idx[i0+ti]
    if ti is not None and (si is None or ti<si):return "WIN",idx[i0+ti]
    return "LOSS",idx[i0+si]

def bools_for_entry(m15,piv_hi,r,famrow):
    idx=m15.index
    if r.entry_ts not in idx:
        raise RuntimeError(f"entry ts missing from 15m {r.entry_ts}")
    i=idx.get_loc(r.entry_ts)
    bar=m15.iloc[i]
    prev=m15.iloc[i-1] if i>0 else None
    entry_close=float(bar.close)
    entry_open=float(bar.open)

    k1=entry_close>float(famrow.touch_high)
    k2=bool(prev is not None and entry_close>entry_open and entry_close>float(prev.high))
    k3=bool(prev is not None and float(prev.close)>float(r.demand_high) and entry_close>float(r.demand_high))

    q=piv_hi[
        (piv_hi.pivot_ts>=r.first_touch_ts)&
        (piv_hi.confirm_ts<=r.entry_ts)&
        (piv_hi.pivot_ts<r.entry_ts)
    ]
    if len(q):
        latest=q.sort_values(["confirm_ts","pivot_ts"]).iloc[-1]
        k4=entry_close>float(latest.level)
        micro_level=float(latest.level)
        micro_pivot_ts=latest.pivot_ts
    else:
        k4=False; micro_level=np.nan; micro_pivot_ts=pd.NaT

    return {
        "K1_BREAK_FIRST_TOUCH_HIGH":k1,
        "K2_BULLISH_DISPLACEMENT_BREAK_PREV_HIGH":k2,
        "K3_TWO_CLOSE_PROXIMAL_HOLD":k3,
        "K4_POST_TOUCH_CONFIRMED_MICRO_BOS":k4,
        "K5_BREAK_TOUCH_HIGH_AND_TWO_CLOSE_HOLD":bool(k1 and k3),
        "micro_bos_level":micro_level,
        "micro_bos_pivot_ts":micro_pivot_ts,
    }

def summarize(q,allq):
    basew=allq[allq.baseline_outcome=="WIN"]
    basel=allq[allq.baseline_outcome=="LOSS"]
    acc=q[q.accepted]
    aw=acc[acc.baseline_outcome=="WIN"]
    al=acc[acc.baseline_outcome=="LOSS"]
    rej=q[~q.accepted]
    rejw=rej[rej.baseline_outcome=="WIN"]
    rejl=rej[rej.baseline_outcome=="LOSS"]
    zfrej=rejl[~rejl.zone_1zw_valid]
    nzrej=rejl[rejl.zone_1zw_valid]
    return {
        "baseline_resolved":len(allq),
        "baseline_wins":len(basew),"baseline_losses":len(basel),
        "accepted_resolved":len(acc),
        "accepted_wins":len(aw),"accepted_losses":len(al),
        "accepted_wr":len(aw)/len(acc) if len(acc) else np.nan,
        "trade_retention":len(acc)/len(allq) if len(allq) else np.nan,
        "baseline_win_retained":len(aw),
        "baseline_win_retention":len(aw)/len(basew) if len(basew) else np.nan,
        "baseline_win_rejected":len(rejw),
        "baseline_loss_rejected":len(rejl),
        "zone_failure_loss_rejected":len(zfrej),
        "valid_zone_loss_rejected":len(nzrej),
        "loss_rejected_per_win_sacrificed":len(rejl)/len(rejw) if len(rejw) else (np.inf if len(rejl) else np.nan),
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end=raw.index.max()

    s1.START=START;s1.END=end;s3.END=end
    h1=s1.exact_exec(raw,"1h",12);h1=h1[h1.index<=end]
    m15=s1.exact_exec(raw,"15min",3);m15=m15[m15.index<=end]
    raw5=raw[["open","high","low","close"]].astype(float)
    piv_hi,_=s1.pivots_df(m15)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()
    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>=REF_START]
    if len(dev)!=788 or len(ref)!=463:
        raise RuntimeError(f"parent parity drift dev={len(dev)} ref={len(ref)}")

    Z=zone_validity(m15,fam,end)
    P=s3.adaptive_plan(m15,h1,fam)
    E=P[P.execution_status=="ENTRY"].copy()
    E=E.merge(Z,on=["zone_id","first_touch_ts"],how="left",validate="one_to_one")
    F=fam.set_index(["zone_id","first_touch_ts"])

    rows=[]
    for r in E.itertuples(index=False):
        pol,tcol,rrcol=MODE_POLICY[r.execution_mode]
        tp=getattr(r,tcol)
        if not np.isfinite(tp):
            continue
        out,rt=resolve(raw5,r.entry_ts,float(r.entry_price),float(r.sl_reference),float(tp),end)
        if out not in ("WIN","LOSS"):
            continue
        famrow=F.loc[(r.zone_id,r.first_touch_ts)]
        bs=bools_for_entry(m15,piv_hi,r,famrow)
        base={
            "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":period(r.first_touch_ts),
            "execution_mode":r.execution_mode,"entry_ts":r.entry_ts,
            "baseline_outcome":out,"baseline_resolution_ts":rt,
            "zone_1zw_valid":bool(r.zone_1zw_valid),
            "micro_bos_level":bs["micro_bos_level"],"micro_bos_pivot_ts":bs["micro_bos_pivot_ts"],
        }
        for cond in CONDS:
            accepted=True if cond=="BASELINE_ALL" else bool(bs[cond])
            rows.append({**base,"condition":cond,"accepted":accepted})

    L=pd.DataFrame(rows)
    S=[]
    for per in ["DEV","REF"]:
        allq=L[(L.period==per)&(L.condition=="BASELINE_ALL")].copy()
        for cond in CONDS:
            q=L[(L.period==per)&(L.condition==cond)].copy()
            S.append({"period":per,"condition":cond,**summarize(q,allq)})
    S=pd.DataFrame(S)

    BM=[]
    for per in ["DEV","REF"]:
        for mode in sorted(L.execution_mode.unique()):
            allq=L[(L.period==per)&(L.condition=="BASELINE_ALL")&(L.execution_mode==mode)]
            if not len(allq):continue
            for cond in CONDS:
                q=L[(L.period==per)&(L.condition==cond)&(L.execution_mode==mode)]
                BM.append({"period":per,"execution_mode":mode,"condition":cond,**summarize(q,allq)})
    BM=pd.DataFrame(BM)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    BM.to_csv(ROOT/f"{PFX}_ByMode.csv",index=False)

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.2f}"

    lines=[
      "# BNB B38-S9 — Genuine Zone-Failure Structural Confirmation Audit","",
      "**No numeric threshold scan. Existing S3 entry decision only. S5 TP/SL unchanged.**","",
      "## Overall preservation / avoidance","",
      "| Period | Condition | Accepted W-L | WR | Trade retained | WIN retained | WIN rejected | LOSS rejected | Genuine zone-fail rejected | Valid-zone loss rejected | Loss reject / WIN sacrificed |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
          f"| {r.period} | {r.condition} | {r.accepted_wins}-{r.accepted_losses} | {pct(r.accepted_wr)} | "
          f"{pct(r.trade_retention)} | {r.baseline_win_retained}/{r.baseline_wins} ({pct(r.baseline_win_retention)}) | "
          f"{r.baseline_win_rejected} | {r.baseline_loss_rejected} | {r.zone_failure_loss_rejected} | "
          f"{r.valid_zone_loss_rejected} | {num(r.loss_rejected_per_win_sacrificed)} |"
        )

    lines += ["","## By execution mode","",
      "| Period | Mode | Condition | Accepted W-L | WR | WIN retention | Zone-fail rejected |",
      "|---|---|---|---:|---:|---:|---:|"
    ]
    for r in BM.itertuples(index=False):
        if r.condition=="BASELINE_ALL":continue
        lines.append(
            f"| {r.period} | {r.execution_mode} | {r.condition} | {r.accepted_wins}-{r.accepted_losses} | "
            f"{pct(r.accepted_wr)} | {pct(r.baseline_win_retention)} | {r.zone_failure_loss_rejected} |"
        )

    lines += ["","## Interpretation boundary",
      "A rejected trade is an avoided entry, not a converted WIN.",
      "The primary question is whether any native structural confirmation rejects genuine zone failures at a much higher rate than it rejects baseline WINs.",
      "No K-condition is promoted to a final detector in S9."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S9_ZONE_FAILURE_CONFIRMATION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
