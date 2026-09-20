#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s2_h1d_15m_archetypes as s2
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s4_adaptive_execution_score as s4

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S6R_HISTORICAL_REFERENCE"

DEV_START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
REF_START=pd.Timestamp("2025-01-01T00:00:00Z")

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level","tp2_rr"),
}

ARCHES=[
    "A_CLEAN_PROXIMAL_RECLAIM",
    "B_CLEAN_IN_ZONE_HOLD",
    "C_SWEEP_FULL_RECLAIM",
    "D_SWEEP_PARTIAL_RECLAIM",
]

def safe_rate(q,col):
    return float(q[col].astype(bool).mean()) if len(q) else np.nan

def med(q,col):
    x=pd.to_numeric(q[col],errors="coerce").dropna()
    return float(x.median()) if len(x) else np.nan

def streak_loss(seq):
    mx=cur=0
    for x in seq:
        if x=="LOSS":
            cur+=1; mx=max(mx,cur)
        else:
            cur=0
    return mx

def max_dd(rs):
    if not rs:return np.nan
    cum=np.cumsum(np.asarray(rs,float))
    peak=np.maximum.accumulate(np.concatenate([[0.0],cum]))[:-1]
    return float(np.max(peak-cum))

def perf(q):
    w=q[q.outcome=="WIN"]; l=q[q.outcome=="LOSS"]
    r=pd.concat([w,l]).sort_values(["entry_ts","zone_id"])
    n=len(r)
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0
    return {
        "plans":len(q),
        "resolved":n,
        "wins":len(w),
        "losses":len(l),
        "ambiguous":int((q.outcome=="AMBIGUOUS_SAME_5M").sum()),
        "unresolved":int((q.outcome=="UNRESOLVED").sum()),
        "hit_rate":len(w)/n if n else np.nan,
        "expectancy_r":float(r.realized_r.mean()) if n else np.nan,
        "total_r":float(r.realized_r.sum()) if n else np.nan,
        "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_loss_streak":streak_loss(r.outcome.tolist()),
        "max_drawdown_r":max_dd(r.realized_r.tolist()) if n else np.nan,
    }

def structural_outcomes(exec_b,fam,end):
    old=s1.END
    s1.END=end
    try:
        return s1.outcomes(exec_b,fam)
    finally:
        s1.END=old

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    data_end=raw.index.max()

    # Extend frozen B38 algorithms only by their data horizon.
    s1.START=DEV_START
    s1.END=data_end
    s3.END=data_end
    s4.END=data_end

    h1=s1.exact_exec(raw,"1h",12)
    m15=s1.exact_exec(raw,"15min",3)
    raw5=raw[["open","high","low","close"]].copy().astype(float)
    h1=h1[h1.index<=data_end].copy()
    m15=m15[m15.index<=data_end].copy()

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=DEV_START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=data_end)
    ].copy()

    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END].copy()
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>=REF_START].copy()
    if len(dev)!=788:
        raise RuntimeError(f"development parent drift: {len(dev)} != 788")

    # Structural path outcomes for all events, then join archetype.
    OL=structural_outcomes(m15,fam,data_end)
    OL["archetype"]=[s2.classify(r) for r in OL.itertuples(index=False)]
    OL["period"]=np.where(pd.to_datetime(OL.first_touch_ts,utc=True)<=DEV_END,"DEV","REF")
    OL["year"]=pd.to_datetime(OL.first_touch_ts,utc=True).dt.year.astype(int)

    struct=[]
    for period,q0 in OL.groupby("period"):
        for a in ARCHES:
            q=q0[q0.archetype==a]
            struct.append({
                "period":period,"archetype":a,"n":len(q),
                "share":len(q)/len(q0) if len(q0) else np.nan,
                "r1_rate":safe_rate(q,"reaction_R1"),
                "r2_1zw_rate":safe_rate(q,"rebound_1zw_R2"),
                "r3_2zw_rate":safe_rate(q,"rebound_2zw_R3"),
                "r4_full_rate":safe_rate(q,"full_continuation_R4"),
                "mfe_zw_median":med(q,"mfe_zw"),
            })
    S=pd.DataFrame(struct)

    # Reference yearly structure census.
    yearly_struct=[]
    for y in [2025,2026]:
        q=OL[(OL.period=="REF")&(OL.year==y)]
        row={"year":y,"parent_n":len(q)}
        for a in ARCHES:
            row[a]=int((q.archetype==a).sum())
        yearly_struct.append(row)
    YS=pd.DataFrame(yearly_struct)

    # Adaptive execution over the complete family and then freeze to ref period.
    P=s3.adaptive_plan(m15,h1,fam)
    devp=P[pd.to_datetime(P.first_touch_ts,utc=True)<=DEV_END]
    dc=devp.execution_status.value_counts().to_dict()
    if len(devp)!=788 or dc.get("ENTRY",0)!=690 or dc.get("CANCELLED_DEMAND_ACCEPTANCE",0)!=98:
        raise RuntimeError(f"S3 dev parity drift {len(devp)} {dc}")

    refp=P[pd.to_datetime(P.first_touch_ts,utc=True)>=REF_START].copy()
    entries=refp[refp.execution_status=="ENTRY"].copy()

    rows=[]
    no_target=0
    for r in entries.itertuples(index=False):
        pol,tcol,rrcol=MODE_POLICY[r.execution_mode]
        tp=getattr(r,tcol); rr=getattr(r,rrcol)
        if not np.isfinite(tp) or not np.isfinite(rr):
            no_target+=1
            continue
        outcome,rt=s4.resolve(raw5,r.entry_ts,float(r.sl_reference),float(tp))
        realized=float(rr) if outcome=="WIN" else (-1.0 if outcome=="LOSS" else np.nan)
        rows.append({
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "entry_ts":r.entry_ts,
            "year":int(pd.Timestamp(r.first_touch_ts).year),
            "execution_mode":r.execution_mode,
            "selected_target":pol,
            "entry_price":float(r.entry_price),
            "sl_reference":float(r.sl_reference),
            "target_level":float(tp),
            "target_rr":float(rr),
            "outcome":outcome,
            "resolution_ts":rt,
            "realized_r":realized,
        })
    L=pd.DataFrame(rows)
    pooled=perf(L)

    BM=[]
    for mode,q in L.groupby("execution_mode"):
        BM.append({"execution_mode":mode,**perf(q)})
    BM=pd.DataFrame(BM)

    BY=[]
    for y in [2025,2026]:
        BY.append({"year":y,**perf(L[L.year==y])})
    BY=pd.DataFrame(BY)

    # Overall structure shares.
    def share_for(period,names):
        q=OL[OL.period==period]
        return float(q.archetype.isin(names).mean()) if len(q) else np.nan

    summary=pd.DataFrame([{
        "data_end":data_end,
        "dev_parent_n":len(dev),
        "ref_parent_n":len(ref),
        "ref_2025_n":int((pd.to_datetime(ref.first_touch_ts,utc=True).dt.year==2025).sum()),
        "ref_2026_n":int((pd.to_datetime(ref.first_touch_ts,utc=True).dt.year==2026).sum()),
        "dev_full_reclaim_share":share_for("DEV",[ARCHES[0],ARCHES[2]]),
        "ref_full_reclaim_share":share_for("REF",[ARCHES[0],ARCHES[2]]),
        "dev_inzone_share":share_for("DEV",[ARCHES[1],ARCHES[3]]),
        "ref_inzone_share":share_for("REF",[ARCHES[1],ARCHES[3]]),
        "ref_entry_plans":len(entries),
        "ref_no_policy_target":no_target,
        **{f"policy_{k}":v for k,v in pooled.items()},
    }])

    OL.to_csv(ROOT/f"{PFX}_StructuralLedger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_ArchetypeComparison.csv",index=False)
    YS.to_csv(ROOT/f"{PFX}_YearlyStructure.csv",index=False)
    L.to_csv(ROOT/f"{PFX}_PolicyLedger.csv.gz",index=False,compression="gzip")
    BM.to_csv(ROOT/f"{PFX}_PolicyByMode.csv",index=False)
    BY.to_csv(ROOT/f"{PFX}_PolicyByYear.csv",index=False)
    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=3):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S6R — Historical Reference Character Test","",
      "**2025-2026 HISTORICAL REFERENCE — NOT A CLEAN OOS CLAIM**","",
      f"Available data through **{data_end}**.","",
      "## Structural persistence",
      f"- Development parent 2022-2024: **{len(dev)}**",
      f"- Reference parent 2025-2026*: **{len(ref)}**",
      f"- Reference 2025 / 2026*: **{int((pd.to_datetime(ref.first_touch_ts,utc=True).dt.year==2025).sum())} / {int((pd.to_datetime(ref.first_touch_ts,utc=True).dt.year==2026).sum())}**",
      f"- Full-reclaim archetype share A+C: development **{pct(share_for('DEV',[ARCHES[0],ARCHES[2]]))}**, reference **{pct(share_for('REF',[ARCHES[0],ARCHES[2]]))}**.",
      f"- In-zone archetype share B+D: development **{pct(share_for('DEV',[ARCHES[1],ARCHES[3]]))}**, reference **{pct(share_for('REF',[ARCHES[1],ARCHES[3]]))}**.","",
      "## Archetype path comparison","",
      "| Archetype | DEV N | REF N | DEV +1ZW | REF +1ZW | DEV +2ZW | REF +2ZW | DEV full cont | REF full cont | REF MFE med |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for a in ARCHES:
        d=S[(S.period=="DEV")&(S.archetype==a)].iloc[0]
        r=S[(S.period=="REF")&(S.archetype==a)].iloc[0]
        lines.append(
            f"| {a} | {int(d.n)} | {int(r.n)} | {pct(d.r2_1zw_rate)} | {pct(r.r2_1zw_rate)} | "
            f"{pct(d.r3_2zw_rate)} | {pct(r.r3_2zw_rate)} | {pct(d.r4_full_rate)} | {pct(r.r4_full_rate)} | {num(r.mfe_zw_median,2)}ZW |"
        )

    lines += ["","## Frozen S5 policy on 2025-2026 reference","",
      f"- Reference ENTRY plans: **{len(entries)}**",
      f"- Required target unavailable: **{no_target}**",
      f"- Resolved W-L: **{pooled['wins']}-{pooled['losses']}**",
      f"- Hit rate: **{pct(pooled['hit_rate'])}**",
      f"- Expectancy: **{num(pooled['expectancy_r'])}R/trade**",
      f"- Total realized R: **{num(pooled['total_r'])}R**",
      f"- Profit factor: **{num(pooled['profit_factor'])}**",
      f"- Max loss streak: **{pooled['max_loss_streak']}**",
      f"- Max cumulative-R drawdown: **{num(pooled['max_drawdown_r'])}R**","",
      "### By execution mode","",
      "| Mode | Resolved | W-L | Hit rate | Expectancy | PF | Max L streak | Max DD |",
      "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in BM.itertuples(index=False):
        lines.append(
            f"| {r.execution_mode} | {r.resolved} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | "
            f"{num(r.expectancy_r)}R | {num(r.profit_factor)} | {r.max_loss_streak} | {num(r.max_drawdown_r)}R |"
        )

    lines += ["","### By year","",
      "| Year | Resolved | W-L | Hit rate | Expectancy | PF |",
      "|---:|---:|---:|---:|---:|---:|"
    ]
    for r in BY.itertuples(index=False):
        lines.append(f"| {r.year} | {r.resolved} | {r.wins}-{r.losses} | {pct(r.hit_rate)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} |")

    lines += ["","## Interpretation boundary",
      "This directly tests whether the frozen B38 character persists in later available data. It is historical reference evidence only; no rule was changed after reading the result."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S6R_HISTORICAL_REFERENCE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
