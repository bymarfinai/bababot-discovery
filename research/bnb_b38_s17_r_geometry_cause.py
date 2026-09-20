#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s14_post_tp1_continuation as s14

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S17_R_GEOMETRY_CAUSE"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.2f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def cuts(x):
    x=pd.Series(x).dropna().astype(float)
    return tuple(float(v) for v in np.quantile(x,[.25,.5,.75]))

def band(v,c):
    if not np.isfinite(v): return "NA"
    q1,q2,q3=c
    if v<=q1:return "Q1_LOW"
    if v<=q2:return "Q2"
    if v<=q3:return "Q3"
    return "Q4_HIGH"

def summarize(q):
    r=q[q.baseline_outcome.isin(["WIN","LOSS"])].copy()
    w=r[r.baseline_outcome=="WIN"]; l=r[r.baseline_outcome=="LOSS"]
    n=len(r); wins=len(w); losses=len(l)
    wr=wins/n if n else np.nan
    avg_win=float(w.baseline_realized_r.mean()) if wins else np.nan
    med_win=float(w.baseline_realized_r.median()) if wins else np.nan
    be_req=(losses/wins) if wins else np.nan
    margin=avg_win-be_req if np.isfinite(avg_win) and np.isfinite(be_req) else np.nan
    exp=float(r.baseline_realized_r.mean()) if n else np.nan
    total=float(r.baseline_realized_r.sum()) if n else np.nan
    return {
        "n":n,"wins":wins,"losses":losses,"wr":wr,
        "avg_win_r":avg_win,"median_win_r":med_win,
        "breakeven_avg_win_r":be_req,"avg_win_margin_r":margin,
        "expectancy_r":exp,"total_r":total,
        "median_sl_pct":float(r.sl_pct.median()) if n else np.nan,
        "median_tp_pct":float(r.tp_pct.median()) if n else np.nan,
        "median_tp1_r":float(r.tp1_r.median()) if n else np.nan,
        "mean_sl_pct":float(r.sl_pct.mean()) if n else np.nan,
        "mean_tp_pct":float(r.tp_pct.mean()) if n else np.nan,
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    end=raw.index.max()
    raw5,m15,h1,P,sig=s14.build_frozen(raw,end)
    if sig!=EXPECTED_SIGNATURE: raise RuntimeError(f"signature drift {sig}")

    if int((P.period=="DEV").sum())!=440 or int((P.period=="REF").sum())!=272:
        raise RuntimeError("parity drift")

    L=P[["zone_id","period","year","entry_ts","entry_price","touch_low_sl","tp1","baseline_outcome","baseline_realized_r"]].copy()
    L["sl_abs"]=L.entry_price-L.touch_low_sl
    L["tp_abs"]=L.tp1-L.entry_price
    L["sl_pct"]=L.sl_abs/L.entry_price
    L["tp_pct"]=L.tp_abs/L.entry_price
    L["tp1_r"]=L.tp_abs/L.sl_abs

    # aggregate
    A=[]
    for per in ["DEV","REF"]:
        A.append({"scope":per,**summarize(L[L.period==per])})
    A=pd.DataFrame(A)

    # annual
    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=L[L.year==y]
        if len(q): Y.append({"year":y,**summarize(q)})
    Y=pd.DataFrame(Y)

    # outcome geometry
    O=[]
    for per in ["DEV","REF"]:
        for out in ["WIN","LOSS"]:
            q=L[(L.period==per)&(L.baseline_outcome==out)]
            O.append({
                "period":per,"outcome":out,"n":len(q),
                "median_sl_pct":float(q.sl_pct.median()),
                "median_tp_pct":float(q.tp_pct.median()),
                "median_tp1_r":float(q.tp1_r.median()),
                "mean_sl_pct":float(q.sl_pct.mean()),
                "mean_tp_pct":float(q.tp_pct.mean()),
                "mean_tp1_r":float(q.tp1_r.mean()),
            })
    O=pd.DataFrame(O)

    dev=L[L.period=="DEV"]
    c_sl=cuts(dev.sl_pct); c_tp=cuts(dev.tp_pct); c_r=cuts(dev.tp1_r)

    B=[]
    for feature,c in [("sl_pct",c_sl),("tp_pct",c_tp),("tp1_r",c_r)]:
        for per in ["DEV","REF"]:
            q=L[L.period==per].copy()
            q["band"]=[band(float(v),c) for v in q[feature]]
            for b in ["Q1_LOW","Q2","Q3","Q4_HIGH"]:
                z=q[q.band==b]
                if len(z):
                    B.append({"feature":feature,"period":per,"band":b,
                              "cut_q25":c[0],"cut_q50":c[1],"cut_q75":c[2],
                              **summarize(z)})
    B=pd.DataFrame(B)

    # direct relation: how much of negative expectation is simply winner payoff shortfall
    D=[]
    for scope,q in [("DEV",L[L.period=="DEV"]),("REF",L[L.period=="REF"])] + [(str(y),L[L.year==y]) for y in [2022,2023,2024,2025,2026]]:
        s=summarize(q)
        # if losses are -1R, expectancy = WR*avg_win - (1-WR)
        implied=s["wr"]*s["avg_win_r"]-(1-s["wr"]) if np.isfinite(s["wr"]) else np.nan
        D.append({
            "scope":scope,"wr":s["wr"],"avg_win_r":s["avg_win_r"],
            "breakeven_avg_win_r":s["breakeven_avg_win_r"],
            "shortfall_r":s["avg_win_r"]-s["breakeven_avg_win_r"],
            "implied_expectancy_r":implied,
            "actual_expectancy_r":s["expectancy_r"],
            "median_sl_pct":s["median_sl_pct"],
            "median_tp_pct":s["median_tp_pct"],
            "median_tp1_r":s["median_tp1_r"],
        })
    D=pd.DataFrame(D)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Aggregate.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    O.to_csv(ROOT/f"{PFX}_OutcomeGeometry.csv",index=False)
    B.to_csv(ROOT/f"{PFX}_QuartileAudit.csv",index=False)
    D.to_csv(ROOT/f"{PFX}_ExpectancyDecomposition.csv",index=False)

    lines=[
      "# BNB B38-S17 — R Geometry Cause Audit","",
      f"Frozen E2 signature: `{sig}`","",
      "## Expectancy decomposition","",
      "| Scope | WR | Avg WIN R | Break-even Avg WIN R | Margin | Exp | Median SL % | Median TP % | Median TP1 R |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in D.itertuples(index=False):
        lines.append(
          f"| {r.scope} | {fmt_pct(r.wr)} | {fmt_num(r.avg_win_r)}R | {fmt_num(r.breakeven_avg_win_r)}R | "
          f"{fmt_num(r.shortfall_r)}R | {fmt_num(r.actual_expectancy_r)}R | "
          f"{fmt_pct(r.median_sl_pct)} | {fmt_pct(r.median_tp_pct)} | {fmt_num(r.median_tp1_r)}R |"
        )
    lines += ["","## WIN vs LOSS geometry","",
      "| Period | Outcome | N | Med SL % | Med TP % | Med TP1 R | Mean SL % | Mean TP % | Mean TP1 R |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in O.itertuples(index=False):
        lines.append(
          f"| {r.period} | {r.outcome} | {r.n} | {fmt_pct(r.median_sl_pct)} | {fmt_pct(r.median_tp_pct)} | "
          f"{fmt_num(r.median_tp1_r)}R | {fmt_pct(r.mean_sl_pct)} | {fmt_pct(r.mean_tp_pct)} | {fmt_num(r.mean_tp1_r)}R |"
        )
    lines += ["","## DEV-frozen quartile audit","",
      "Same DEV cuts are applied unchanged to REF.",""
    ]
    for feature in ["sl_pct","tp_pct","tp1_r"]:
        q=B[B.feature==feature]
        cr=q.iloc[0]
        lines += [
          f"### {feature}",
          f"Cuts: Q25={cr.cut_q25:.6f}, Q50={cr.cut_q50:.6f}, Q75={cr.cut_q75:.6f}",
          "",
          "| Period | Band | N | WR | Avg WIN R | BE Avg WIN | Exp | Med SL % | Med TP % | Med TP1 R |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
        ]
        for r in q.itertuples(index=False):
            lines.append(
              f"| {r.period} | {r.band} | {r.n} | {fmt_pct(r.wr)} | {fmt_num(r.avg_win_r)}R | "
              f"{fmt_num(r.breakeven_avg_win_r)}R | {fmt_num(r.expectancy_r)}R | "
              f"{fmt_pct(r.median_sl_pct)} | {fmt_pct(r.median_tp_pct)} | {fmt_num(r.median_tp1_r)}R |"
            )
        lines.append("")
    lines += [
      "## Interpretation boundary",
      "S17 diagnoses payoff geometry only. It does not promote a narrower SL, farther TP, or entry filter.",
      "If negative expectancy is caused mainly by low winner R rather than a higher loss rate, the next experiment must improve reward/risk without inventing a tighter stop that destroys valid winners."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S17_R_GEOMETRY_CAUSE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
