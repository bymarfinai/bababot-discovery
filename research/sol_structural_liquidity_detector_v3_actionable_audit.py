#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_STRUCTURAL_LIQUIDITY_DETECTOR_V3_ACTIONABLE_AUDIT"
CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
HOLDOUT_END=pd.Timestamp("2026-01-01",tz="UTC")
SCORE_THRESHOLD=3

def wilson(successes:int,n:int,z:float=1.96):
    if n<=0: return np.nan,np.nan
    p=successes/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)/n)+z*z/(4*n*n))/den
    return center-half,center+half

def rate(df):
    return float(df.event_label.mean()) if len(df) else np.nan

def actionable(df):
    x=df.copy()
    ri=pd.to_numeric(x.resolution_i_h1,errors="coerce")
    qi=pd.to_numeric(x.reclaim_i_h1,errors="coerce")
    same=(ri>=0)&(ri==qi)
    return x.loc[~same].copy().reset_index(drop=True)

def side_rows(base,sel,phase):
    rows=[]
    for side in ("BUY_SIDE","SELL_SIDE"):
        b=base[base.side==side]
        s=sel[sel.side==side]
        rows.append({
            "phase":phase,"side":side,
            "baseline_n":len(b),"baseline_rate":rate(b),
            "selected_n":len(s),"selected_rate":rate(s),
            "lift":rate(s)-rate(b) if len(s) and len(b) else np.nan
        })
    return rows

def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low {coverage:.6%}")

    construction=v3.add_conditions(v3.build_population(x5,CONSTRUCTION_END))
    construction=construction[construction.sweep_year.isin([2020,2021,2022,2023,2024])].copy()
    holdout=v3.add_conditions(v3.build_population(x5,HOLDOUT_END))
    holdout=holdout[holdout.sweep_year==2025].copy()

    construction_a=actionable(construction)
    holdout_a=actionable(holdout)

    csel=construction_a[construction_a.anatomy_score>=SCORE_THRESHOLD].copy()
    hsel=holdout_a[holdout_a.anatomy_score>=SCORE_THRESHOLD].copy()

    base=rate(holdout_a); sr=rate(hsel); lift=sr-base
    succ=int(hsel.event_label.sum())
    wlo,whi=wilson(succ,len(hsel))

    side=pd.DataFrame(side_rows(construction_a,csel,"CONSTRUCTION_2020_2024")+side_rows(holdout_a,hsel,"HOLDOUT_2025"))
    hs=side[side.phase=="HOLDOUT_2025"].set_index("side")

    gates={
        "selected_2025_n_ge_50":len(hsel)>=50,
        "selected_2025_rate_ge_45pct":bool(np.isfinite(sr) and sr>=.45),
        "lift_ge_15pp":bool(np.isfinite(lift) and lift>=.15),
        "wilson_lower_ge_35pct":bool(np.isfinite(wlo) and wlo>=.35),
        "buy_side_above_baseline":bool(hs.loc["BUY_SIDE","selected_rate"]>hs.loc["BUY_SIDE","baseline_rate"]),
        "sell_side_above_baseline":bool(hs.loc["SELL_SIDE","selected_rate"]>hs.loc["SELL_SIDE","baseline_rate"]),
    }
    verdict="VALIDATED_ACTIONABLE_STRUCTURAL_LIQUIDITY_DETECTOR" if all(gates.values()) else "ACTIONABLE_DETECTOR_NOT_VALIDATED_AS_DEFINED"

    construction_a.to_csv(ROOT/f"{PFX}_ConstructionActionable.csv",index=False)
    holdout_a.to_csv(ROOT/f"{PFX}_Holdout2025Actionable.csv",index=False)
    hsel.to_csv(ROOT/f"{PFX}_Holdout2025Selected.csv",index=False)
    side.to_csv(ROOT/f"{PFX}_SideSummary.csv",index=False)

    summary=pd.DataFrame([{
        "coverage":coverage,
        "construction_raw_n":len(construction),
        "construction_actionable_n":len(construction_a),
        "construction_selected_n":len(csel),
        "construction_baseline_rate":rate(construction_a),
        "construction_selected_rate":rate(csel),
        "holdout_raw_n":len(holdout),
        "holdout_actionable_n":len(holdout_a),
        "holdout_selected_n":len(hsel),
        "holdout_baseline_rate":base,
        "holdout_selected_rate":sr,
        "holdout_lift":lift,
        "wilson_lower":wlo,"wilson_upper":whi,
        **{f"gate_{k}":v for k,v in gates.items()},
        "verdict":verdict
    }])
    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    pct=lambda v:"n/a" if not np.isfinite(v) else f"{v*100:.2f}%"
    lines=[
        "# SOL Structural Liquidity Detector V3 — Actionability Audit","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Detector frozen unchanged at **SCORE >= 3**.",
        "- Exclusion only: rows already structurally resolved on the reclaim H1 candle.",
        "- No entry, TP, SL, PnL, hour, indicator, or regime changes.","",
        "## Construction 2020-2024","",
        f"- Raw physical events: **{len(construction):,}**",
        f"- Actionable physical events: **{len(construction_a):,}**",
        f"- Actionable baseline rate: **{pct(rate(construction_a))}**",
        f"- SCORE>=3 actionable: N=**{len(csel):,}**, rate=**{pct(rate(csel))}**",
        f"- Lift: **{(rate(csel)-rate(construction_a))*100:.2f} pp**","",
        "## Frozen 2025 audit","",
        f"- Raw events: **{len(holdout):,}**",
        f"- Actionable events: **{len(holdout_a):,}**",
        f"- Actionable baseline: **{pct(base)}**",
        f"- SCORE>=3 actionable: N=**{len(hsel)}**, rate=**{pct(sr)}**",
        f"- Lift: **{lift*100:.2f} pp**",
        f"- Wilson 95% CI: **{pct(wlo)} – {pct(whi)}**",
        f"- BUY_SIDE: selected **{pct(hs.loc['BUY_SIDE','selected_rate'])}** vs baseline **{pct(hs.loc['BUY_SIDE','baseline_rate'])}**",
        f"- SELL_SIDE: selected **{pct(hs.loc['SELL_SIDE','selected_rate'])}** vs baseline **{pct(hs.loc['SELL_SIDE','baseline_rate'])}**","",
        "## Gate audit",""
    ]
    for k,v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
    lines += ["",f"**VERDICT: {verdict}**","",
              "A passing verdict means the frozen detector still enriches future structural consequences when every signal is genuinely actionable only after the reclaim close.","",
              "2026_PLUS=CLOSED"]
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2026_PLUS=CLOSED\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
