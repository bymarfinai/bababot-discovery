#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s4_adaptive_execution_score as s4

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S5_ADAPTIVE_POLICY"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")
FORWARD_FREEZE=pd.Timestamp("2026-09-20T06:30:00Z")

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1_FULL_EXIT","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1_FULL_EXIT","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1_FULL_EXIT","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2_FULL_EXIT","tp2_level","tp2_rr"),
}

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

def max_dd(rs):
    if not rs:return np.nan
    cum=np.cumsum(np.asarray(rs,float))
    peaks=np.maximum.accumulate(np.concatenate([[0.0],cum]))[:-1]
    return float(np.max(peaks-cum))

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
    mw,ml=streaks(resolved.outcome.tolist())
    return {
        "plans":len(q),"resolved_n":n,"wins":len(wins),"losses":len(losses),
        "ambiguous":len(amb),"unresolved":len(unr),"hit_rate":wr,
        "expectancy_r":exp,"total_r":total,"profit_factor":pf,
        "max_win_streak":mw,"max_loss_streak":ml,
        "max_drawdown_r":max_dd(resolved.realized_r.tolist()) if n else np.nan,
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=END].copy()
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=END].copy()
    raw5=raw[["open","high","low","close"]].copy().astype(float)
    raw5=raw5[raw5.index<=END].copy()

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&(pd.to_datetime(fam.first_touch_ts,utc=True)<=END)].copy()
    if len(fam)!=788: raise RuntimeError(f"parent drift {len(fam)} != 788")

    P=s3.adaptive_plan(m15,h1,fam)
    if len(P)!=788: raise RuntimeError(f"plan drift {len(P)} != 788")
    c=P.execution_status.value_counts().to_dict()
    if c.get("ENTRY",0)!=690 or c.get("CANCELLED_DEMAND_ACCEPTANCE",0)!=98:
        raise RuntimeError(f"S3 integrity drift {c}")

    E=P[P.execution_status=="ENTRY"].copy()
    rows=[]
    no_target=0
    for r in E.itertuples(index=False):
        if r.execution_mode not in MODE_POLICY:
            raise RuntimeError(f"unknown mode {r.execution_mode}")
        policy,tcol,rrcol=MODE_POLICY[r.execution_mode]
        tp=getattr(r,tcol); rr=getattr(r,rrcol)
        if not np.isfinite(tp) or not np.isfinite(rr):
            no_target+=1
            rows.append({
                "zone_id":r.zone_id,"entry_ts":r.entry_ts,"retest_year":int(pd.Timestamp(r.first_touch_ts).year),
                "execution_mode":r.execution_mode,"selected_policy":policy,
                "entry_price":r.entry_price,"sl_reference":r.sl_reference,
                "target_level":np.nan,"target_rr":np.nan,
                "outcome":"NO_POLICY_TARGET","resolution_ts":pd.NaT,"realized_r":np.nan
            })
            continue
        outcome,rt=s4.resolve(raw5,r.entry_ts,float(r.sl_reference),float(tp))
        realized=float(rr) if outcome=="WIN" else (-1.0 if outcome=="LOSS" else np.nan)
        rows.append({
            "zone_id":r.zone_id,"entry_ts":r.entry_ts,"retest_year":int(pd.Timestamp(r.first_touch_ts).year),
            "execution_mode":r.execution_mode,"selected_policy":policy,
            "entry_price":float(r.entry_price),"sl_reference":float(r.sl_reference),
            "target_level":float(tp),"target_rr":float(rr),
            "outcome":outcome,"resolution_ts":rt,"realized_r":realized
        })

    L=pd.DataFrame(rows)
    scored=L[L.outcome!="NO_POLICY_TARGET"].copy()

    pooled=summarize(scored)
    bymode=[]
    for mode,q in scored.groupby("execution_mode"):
        bymode.append({"execution_mode":mode,**summarize(q)})
    M=pd.DataFrame(bymode)

    byyear=[]
    for y in [2022,2023,2024]:
        byyear.append({"year":y,**summarize(scored[scored.retest_year==y])})
    Y=pd.DataFrame(byyear)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    pd.DataFrame([{"scope":"COMPOSITE_POLICY",**pooled,"no_policy_target":no_target}]).to_csv(ROOT/f"{PFX}_Pooled.csv",index=False)
    M.to_csv(ROOT/f"{PFX}_ByMode.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)

    manifest=pd.DataFrame([{
        "identity":"BNB_B38_S5_ADAPTIVE_POLICY_V1",
        "freeze_timestamp_utc":FORWARD_FREEZE.isoformat(),
        "prospective_data_must_be_after_utc":FORWARD_FREEZE.isoformat(),
        "entry_logic":"B38-S3 frozen",
        "sl_logic":"B38-S3 frozen",
        "immediate_clean_target":"TP1",
        "immediate_sweep_target":"TP1",
        "delayed_clean_target":"TP1",
        "delayed_sweep_target":"TP2",
        "missing_required_target_action":"NO_POLICY_TARGET",
    }])
    manifest.to_csv(ROOT/f"{PFX}_ForwardManifest.csv",index=False)

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=2):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S5 — Frozen Adaptive Policy Candidate","",
      "**DEVELOPMENT POLICY FREEZE — NOT INDEPENDENT OOS VALIDATION**","",
      "## Frozen mode -> objective mapping",
      "- IMMEDIATE_CLEAN_RECLAIM -> **TP1**",
      "- IMMEDIATE_SWEEP_RECLAIM -> **TP1**",
      "- DELAYED_CLEAN_RECLAIM -> **TP1**",
      "- DELAYED_SWEEP_RECLAIM -> **TP2**","",
      "Entry and structural SL remain exactly B38-S3.","",
      "## Development composite characterization",
      f"- Frozen ENTRY plans: **690**",
      f"- Plans with required structural target available: **{len(scored)}**",
      f"- NO_POLICY_TARGET: **{no_target}**",
      f"- Resolved W-L: **{pooled['wins']}-{pooled['losses']}**",
      f"- Hit rate: **{pct(pooled['hit_rate'])}**",
      f"- Expectancy: **{num(pooled['expectancy_r'])}R / trade**",
      f"- Total realized R: **{num(pooled['total_r'])}R**",
      f"- Profit factor: **{num(pooled['profit_factor'])}**",
      f"- Max win streak: **{pooled['max_win_streak']}**",
      f"- Max loss streak: **{pooled['max_loss_streak']}**",
      f"- Max cumulative-R drawdown: **{num(pooled['max_drawdown_r'])}R**","",
      "## By execution mode","",
      "| Mode | Resolved | W-L | Hit rate | Expectancy | PF | Max L streak | Max DD |",
      "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in M.itertuples(index=False):
        lines.append(f"| {r.execution_mode} | {r.resolved_n} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} | {r.max_loss_streak} | {num(r.max_drawdown_r)}R |")

    lines += ["","## Development year stability","",
      "| Year | Resolved | W-L | Hit rate | Expectancy | PF |",
      "|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(f"| {r.year} | {r.resolved_n} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} |")

    lines += ["","## Prospective freeze",
      f"**Immutable from {FORWARD_FREEZE.isoformat()} onward.**",
      "Only market bars strictly after this timestamp may be used as clean prospective evidence for this policy identity.",
      "No target switching, mode filtering, RR filtering, entry adjustment, or SL adjustment is permitted during forward validation.","",
      "## Status",
      "**ADAPTIVE POLICY CANDIDATE FROZEN — READY FOR PROSPECTIVE FORWARD VALIDATION.**"
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S5_ADAPTIVE_POLICY_FROZEN_FORWARD_READY\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
