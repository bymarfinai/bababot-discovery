#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1
import bnb_b37_s4_causal_state_machine as s4

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S5_OOS_VALIDATION"
OOS_START=pd.Timestamp("2025-01-01T00:00:00Z")
DEV_START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
CANDS=s4.CANDS
EXPECTED={
 "H4D_H1_PROXIMAL_RECLAIM":133,
 "H4D_H1_CLEAN_PROXIMAL_RECLAIM":115,
 "H4D_H1_BULLISH_PROXIMAL_RECLAIM":27,
 "H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM":40,
}

def wilson(k,n,z=1.959963984540054):
    if n<=0:return (np.nan,np.nan)
    p=k/n
    den=1+(z*z/n)
    center=(p+(z*z/(2*n)))/den
    half=(z*math.sqrt((p*(1-p)/n)+(z*z/(4*n*n))))/den
    return center-half,center+half

def structural_outcome(b1,r,data_end):
    q=b1[(b1.index>r.first_touch_ts)&(b1.index<=data_end)]
    up=float(r.expansion_high); dn=float(r.demand_low)
    for t,c in q.iterrows():
        close=float(c.close); hi=float(c.high); lo=float(c.low)
        if hi>up and lo<dn and dn<=close<=up:
            return "AMBIGUOUS_SAME_BAR",t
        if close>up:
            return "WIN_CONTINUATION",t
        if close<dn:
            return "LOSS_INVALIDATION",t
    return "UNRESOLVED",pd.NaT

def score_group(df):
    w=int((df.outcome=="WIN_CONTINUATION").sum())
    l=int((df.outcome=="LOSS_INVALIDATION").sum())
    a=int((df.outcome=="AMBIGUOUS_SAME_BAR").sum())
    u=int((df.outcome=="UNRESOLVED").sum())
    n=w+l
    rate=(w/n) if n else np.nan
    lo,hi=wilson(w,n)
    return {"events":len(df),"resolved_n":n,"win":w,"loss":l,"ambiguous":a,"unresolved":u,
            "rate":rate,"wilson_lo":lo,"wilson_hi":hi}

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    b1=s1.exact_bars(raw,"1h",12)
    b4=s1.exact_bars(raw,"4h",48)
    data_end=min(b1.index.max(),b4.index.max()+pd.Timedelta(hours=3))
    # Outcomes require H1 only; detector replay gets every complete H1/H4 bar available.
    sm,rejects,transitions,zones=s4.replay(b1,b4)

    # Pre-reference implementation integrity check.
    ts=pd.to_datetime(sm.first_touch_ts,utc=True)
    dev=sm[(ts>=DEV_START)&(ts<=DEV_END)].copy()
    if len(dev)!=201:
        raise RuntimeError(f"dev parent drift before OOS scoring: {len(dev)} != 201")
    for c,n in EXPECTED.items():
        got=int(dev[c].sum())
        if got!=n:
            raise RuntimeError(f"dev candidate drift {c}: {got} != {n}")

    oos=sm[pd.to_datetime(sm.first_touch_ts,utc=True)>=OOS_START].copy()
    oos=oos[pd.to_datetime(oos.first_touch_ts,utc=True)<=data_end].copy()

    rows=[]
    for r in oos.itertuples(index=False):
        outcome,resolution_ts=structural_outcome(b1,r,data_end)
        base={
            "zone_id":r.zone_id,
            "activation_ts":r.activation_ts,
            "first_touch_ts":r.first_touch_ts,
            "retest_year":int(pd.Timestamp(r.first_touch_ts).year),
            "demand_low":float(r.demand_low),
            "demand_high":float(r.demand_high),
            "expansion_high":float(r.expansion_high),
            "outcome":outcome,
            "resolution_ts":resolution_ts,
        }
        for c in CANDS:
            base[c]=bool(getattr(r,c))
        rows.append(base)
    L=pd.DataFrame(rows)

    parent=score_group(L)
    stats=[]
    yearly=[]
    for c in CANDS:
        q=L[L[c]].copy()
        s=score_group(q)
        s["candidate"]=c

        year_scores={}
        for y in [2025,2026]:
            qy=q[q.retest_year==y]
            sy=score_group(qy)
            year_scores[y]=sy
            yearly.append({"candidate":c,"year":y,**sy})

        support_pass=bool(
            s["resolved_n"]>=20 and
            year_scores[2025]["resolved_n"]>=8 and
            year_scores[2026]["resolved_n"]>=8
        )
        pooled_gt50=bool(np.isfinite(s["rate"]) and s["rate"]>0.50)
        wilson_gt50=bool(np.isfinite(s["wilson_lo"]) and s["wilson_lo"]>0.50)
        y2025_gt50=bool(np.isfinite(year_scores[2025]["rate"]) and year_scores[2025]["rate"]>0.50)
        y2026_gt50=bool(np.isfinite(year_scores[2026]["rate"]) and year_scores[2026]["rate"]>0.50)
        parent_uplift=bool(np.isfinite(s["rate"]) and np.isfinite(parent["rate"]) and s["rate"]>parent["rate"])

        if not support_pass:
            verdict="INSUFFICIENT_OOS_SUPPORT"
        elif pooled_gt50 and wilson_gt50 and y2025_gt50 and y2026_gt50 and parent_uplift:
            verdict="OOS_STRUCTURAL_EDGE_VALIDATED"
        else:
            verdict="OOS_STRUCTURAL_EDGE_NOT_VALIDATED"

        s.update({
            "support_pass":support_pass,
            "pooled_gt_50":pooled_gt50,
            "wilson_lcb_gt_50":wilson_gt50,
            "y2025_gt_50":y2025_gt50,
            "y2026_gt_50":y2026_gt50,
            "beats_parent":parent_uplift,
            "parent_rate":parent["rate"],
            "verdict":verdict,
        })
        stats.append(s)

    S=pd.DataFrame(stats)
    Y=pd.DataFrame(yearly)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_CandidateStats.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_Yearly.csv",index=False)
    pd.DataFrame([{"scope":"PARENT",**parent}]).to_csv(ROOT/f"{PFX}_Parent.csv",index=False)

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.2f}%"

    lines=[
      "# BNB B37-S5 — Frozen Detector Out-of-Sample Validation","",
      "**STEP 5 — TRUE OOS VALIDATION**","",
      f"Reference opened: **2025-01-01 through {data_end}**.",
      "Detector definitions were frozen before this period was scored.","",
      "## Integrity",
      f"- Raw rows: **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**.",
      f"- Development replay parent: **{len(dev)} / 201**.",
      "- Development candidate totals: **133 / 115 / 27 / 40**, exact match.",
      "- 2025-2026 was scored only after the implementation integrity check passed.","",
      "## OOS parent baseline",
      f"- Parent events: **{parent['events']}**.",
      f"- Resolved: **{parent['resolved_n']}**; WIN **{parent['win']}**, LOSS **{parent['loss']}**, ambiguous **{parent['ambiguous']}**, unresolved **{parent['unresolved']}**.",
      f"- Structural continuation rate: **{pct(parent['rate'])}**.",
      f"- 95% Wilson CI: **{pct(parent['wilson_lo'])} – {pct(parent['wilson_hi'])}**.","",
      "## Frozen candidate validation","",
      "| Candidate | Events | Resolved | WIN-LOSS | Rate | 95% Wilson LCB | 2025 | 2026* | vs Parent | Verdict |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in S.itertuples(index=False):
        y25=Y[(Y.candidate==r.candidate)&(Y.year==2025)].iloc[0]
        y26=Y[(Y.candidate==r.candidate)&(Y.year==2026)].iloc[0]
        uplift=(r.rate-r.parent_rate) if np.isfinite(r.rate) and np.isfinite(r.parent_rate) else np.nan
        lines.append(
            f"| {r.candidate} | {r.events} | {r.resolved_n} | {r.win}-{r.loss} | {pct(r.rate)} | {pct(r.wilson_lo)} | "
            f"{pct(y25.rate)} ({int(y25.resolved_n)}) | {pct(y26.rate)} ({int(y26.resolved_n)}) | "
            f"{'—' if not np.isfinite(uplift) else f'{100*uplift:+.2f}pp'} | **{r.verdict}** |"
        )

    lines += ["","## Gate audit"]
    for r in S.itertuples(index=False):
        lines += [
          f"### {r.candidate}",
          f"- support >=20 pooled and >=8 each year: **{'PASS' if r.support_pass else 'FAIL'}**",
          f"- pooled rate >50%: **{'PASS' if r.pooled_gt_50 else 'FAIL'}**",
          f"- 95% Wilson LCB >50%: **{'PASS' if r.wilson_lcb_gt_50 else 'FAIL'}**",
          f"- 2025 >50%: **{'PASS' if r.y2025_gt_50 else 'FAIL'}**",
          f"- 2026* >50%: **{'PASS' if r.y2026_gt_50 else 'FAIL'}**",
          f"- beats contemporaneous parent: **{'PASS' if r.beats_parent else 'FAIL'}**",
          f"- verdict: **{r.verdict}**",""
        ]

    validated=S[S.verdict=="OOS_STRUCTURAL_EDGE_VALIDATED"].candidate.tolist()
    insufficient=S[S.verdict=="INSUFFICIENT_OOS_SUPPORT"].candidate.tolist()
    if validated:
        final="BNB_B37_S5_OOS_VALIDATED_"+"_".join([f"C{CANDS.index(c)+1}" for c in validated])
        summary="Validated detector(s): "+", ".join(validated)
    else:
        final="BNB_B37_S5_NO_OOS_STRUCTURAL_EDGE_VALIDATED"
        summary="No frozen candidate satisfied the full OOS structural-edge gate."
    lines += ["## Step-5 verdict",f"**{summary}**"]
    if insufficient:
        lines.append("Insufficient-support candidate(s): "+", ".join(insufficient)+".")
    lines += ["",
      "No threshold rescue, time slicing, indicator/derivative filter, TP/SL, PnL, leverage, or fee model was introduced.",
      "Only a Step-5 validated detector may proceed to Step 6 trading-economics testing."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(final+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
