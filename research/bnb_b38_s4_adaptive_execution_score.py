#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S4_ADAPTIVE_EXECUTION_SCORE"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")
POLICIES=[
    ("TP1_FULL_EXIT","tp1_level","tp1_rr"),
    ("TP2_FULL_EXIT","tp2_level","tp2_rr"),
    ("TP3_FULL_EXIT","tp3_level","tp3_rr"),
]

def resolve(raw5, entry_ts, sl, tp):
    q=raw5[(raw5.index>entry_ts)&(raw5.index<=END)]
    for t,b in q.iterrows():
        stop=bool(float(b.low)<=sl)
        target=bool(float(b.high)>=tp)
        if stop and target:
            return "AMBIGUOUS_SAME_5M",t
        if target:
            return "WIN",t
        if stop:
            return "LOSS",t
    return "UNRESOLVED",pd.NaT

def streaks(seq):
    maxw=maxl=curw=curl=0
    for x in seq:
        if x=="WIN":
            curw+=1; curl=0; maxw=max(maxw,curw)
        elif x=="LOSS":
            curl+=1; curw=0; maxl=max(maxl,curl)
        else:
            curw=curl=0
    return maxw,maxl

def max_drawdown(rs):
    if len(rs)==0:return np.nan
    cum=np.cumsum(np.asarray(rs,dtype=float))
    peak=np.maximum.accumulate(np.concatenate([[0.0],cum]))[:-1]
    dd=peak-cum
    return float(np.max(dd)) if len(dd) else 0.0

def summarize(q):
    wins=q[q.outcome=="WIN"]
    losses=q[q.outcome=="LOSS"]
    amb=q[q.outcome=="AMBIGUOUS_SAME_5M"]
    unr=q[q.outcome=="UNRESOLVED"]
    resolved=pd.concat([wins,losses]).sort_values(["entry_ts","zone_id"])
    n=len(resolved)
    wr=len(wins)/n if n else np.nan
    exp=float(resolved.realized_r.mean()) if n else np.nan
    total=float(resolved.realized_r.sum()) if n else np.nan
    pos=float(wins.realized_r.sum()) if len(wins) else 0.0
    neg=abs(float(losses.realized_r.sum())) if len(losses) else 0.0
    pf=(pos/neg) if neg>0 else (np.inf if pos>0 else np.nan)
    winr=wins.target_rr.dropna()
    seq=resolved.outcome.tolist()
    mw,ml=streaks(seq)
    mdd=max_drawdown(resolved.realized_r.tolist()) if n else np.nan

    conservative=q[q.outcome!="UNRESOLVED"].copy()
    if len(conservative):
        cons_r=np.where(conservative.outcome=="WIN",conservative.target_rr,-1.0)
        cons_exp=float(np.mean(cons_r))
    else:
        cons_exp=np.nan

    return {
        "plans":len(q),
        "resolved_n":n,
        "wins":len(wins),
        "losses":len(losses),
        "ambiguous":len(amb),
        "unresolved":len(unr),
        "hit_rate":wr,
        "win_r_median":float(winr.median()) if len(winr) else np.nan,
        "win_r_p25":float(winr.quantile(.25)) if len(winr) else np.nan,
        "win_r_p75":float(winr.quantile(.75)) if len(winr) else np.nan,
        "expectancy_r":exp,
        "total_r":total,
        "profit_factor":pf,
        "max_win_streak":mw,
        "max_loss_streak":ml,
        "max_drawdown_r":mdd,
        "ambiguous_as_loss_expectancy_r":cons_exp,
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    h1=s1.exact_exec(raw,"1h",12)
    m15=s1.exact_exec(raw,"15min",3)
    h1=h1[h1.index<=END].copy()
    m15=m15[m15.index<=END].copy()
    raw5=raw[["open","high","low","close"]].copy().astype(float)
    raw5=raw5[raw5.index<=END].copy()

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=END)
    ].copy()
    if len(fam)!=788:
        raise RuntimeError(f"parent drift {len(fam)} != 788")

    P=s3.adaptive_plan(m15,h1,fam)
    if len(P)!=788:
        raise RuntimeError(f"plan drift {len(P)} != 788")
    counts=P.execution_status.value_counts().to_dict()
    if counts.get("ENTRY",0)!=690 or counts.get("CANCELLED_DEMAND_ACCEPTANCE",0)!=98 or counts.get("NO_TRIGGER_BY_END",0)!=0:
        raise RuntimeError(f"S3 integrity drift {counts}")

    E=P[P.execution_status=="ENTRY"].copy()
    if (E.risk_abs<=0).any():
        raise RuntimeError("non-positive structural risk found")

    scored=[]
    for r in E.itertuples(index=False):
        for policy,tcol,rrcol in POLICIES:
            tp=getattr(r,tcol)
            rr=getattr(r,rrcol)
            if not np.isfinite(tp) or not np.isfinite(rr):
                continue
            if not (float(tp)>float(r.entry_price)>float(r.sl_reference)):
                raise RuntimeError(f"invalid ladder geometry {r.zone_id} {policy}")
            outcome,resolution_ts=resolve(raw5,r.entry_ts,float(r.sl_reference),float(tp))
            realized=float(rr) if outcome=="WIN" else (-1.0 if outcome=="LOSS" else np.nan)
            scored.append({
                "zone_id":r.zone_id,
                "entry_ts":r.entry_ts,
                "retest_year":int(pd.Timestamp(r.first_touch_ts).year),
                "first_touch_archetype":r.first_touch_archetype,
                "execution_mode":r.execution_mode,
                "policy":policy,
                "entry_price":float(r.entry_price),
                "sl_reference":float(r.sl_reference),
                "target_level":float(tp),
                "target_rr":float(rr),
                "risk_abs":float(r.risk_abs),
                "risk_pct":float(r.risk_pct),
                "outcome":outcome,
                "resolution_ts":resolution_ts,
                "realized_r":realized,
            })
    L=pd.DataFrame(scored)

    pooled=[]
    bymode=[]
    byyear=[]
    for policy,_,_ in POLICIES:
        q=L[L.policy==policy].copy()
        pooled.append({"policy":policy,**summarize(q)})
        for mode,qm in q.groupby("execution_mode"):
            bymode.append({"policy":policy,"execution_mode":mode,**summarize(qm)})
        for y in [2022,2023,2024]:
            qy=q[q.retest_year==y]
            byyear.append({"policy":policy,"year":y,**summarize(qy)})

    S=pd.DataFrame(pooled)
    M=pd.DataFrame(bymode)
    Y=pd.DataFrame(byyear)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Pooled.csv",index=False)
    M.to_csv(ROOT/f"{PFX}_ByMode.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=2):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S4 — Frozen Adaptive Execution Score","",
      "**2022-2024 DEVELOPMENT EXECUTION CHARACTERIZATION — NOT OOS**","",
      "Integrity passed: **788 parent events -> 690 frozen ENTRY plans + 98 frozen cancellations**.","",
      "Target/SL ordering is resolved from exact **5m bars strictly after each 15m entry close**. Same-5m target+SL touches are reported as ambiguous.","",
      "## Pooled structural-objective policies","",
      "| Policy | Plans | Resolved | W-L | Hit rate | Median win R | Expectancy | Total R | PF | W streak | L streak | Max DD | Ambig | Unres |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.policy} | {r.plans} | {r.resolved_n} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | "
            f"{num(r.win_r_median)}R | {num(r.expectancy_r)}R | {num(r.total_r)}R | {num(r.profit_factor)} | "
            f"{r.max_win_streak} | {r.max_loss_streak} | {num(r.max_drawdown_r)}R | {r.ambiguous} | {r.unresolved} |"
        )

    lines += ["","## By adaptive execution mode — TP1","",
      "| Mode | Resolved | W-L | Hit rate | Median win R | Expectancy | PF | Max L streak | Max DD |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    Q=M[M.policy=="TP1_FULL_EXIT"]
    for r in Q.itertuples(index=False):
        lines.append(
            f"| {r.execution_mode} | {r.resolved_n} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | "
            f"{num(r.win_r_median)}R | {num(r.expectancy_r)}R | {num(r.profit_factor)} | "
            f"{r.max_loss_streak} | {num(r.max_drawdown_r)}R |"
        )

    lines += ["","## By adaptive execution mode — TP2","",
      "| Mode | Resolved | W-L | Hit rate | Median win R | Expectancy | PF | Max L streak | Max DD |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    Q=M[M.policy=="TP2_FULL_EXIT"]
    for r in Q.itertuples(index=False):
        lines.append(
            f"| {r.execution_mode} | {r.resolved_n} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | "
            f"{num(r.win_r_median)}R | {num(r.expectancy_r)}R | {num(r.profit_factor)} | "
            f"{r.max_loss_streak} | {num(r.max_drawdown_r)}R |"
        )

    lines += ["","## Year stability","",
      "| Policy | 2022 hit / Exp | 2023 hit / Exp | 2024 hit / Exp |",
      "|---|---:|---:|---:|"
    ]
    for policy,_,_ in POLICIES:
        vals=[]
        for y in [2022,2023,2024]:
            r=Y[(Y.policy==policy)&(Y.year==y)].iloc[0]
            vals.append(f"{pct(r.hit_rate)} / {num(r.expectancy_r)}R")
        lines.append(f"| {policy} | {vals[0]} | {vals[1]} | {vals[2]} |")

    lines += ["","## Ambiguity sensitivity","",
      "Main expectancy excludes same-5m ambiguous outcomes. A separately persisted sensitivity treats every ambiguous outcome as -1R; no rule is changed from that sensitivity.","",
      "## S4 interpretation boundary",
      "These results describe the frozen adaptive execution engine with equal 1R risk per signal. They are **not** a dollar portfolio simulation, do not include fees/slippage, and do not establish independent OOS validation.",
      "No entry, SL, TP, mode, or RR filter was changed after outcomes were read."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S4_FROZEN_ENGINE_SCORED\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
