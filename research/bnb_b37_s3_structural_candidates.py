#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1
import bnb_b37_s1b_visual_equivalent as s1b

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S3_STRUCTURAL_CANDIDATES"

CANDS=[
    "H4D_H1_PROXIMAL_RECLAIM",
    "H4D_H1_CLEAN_PROXIMAL_RECLAIM",
    "H4D_H1_BULLISH_PROXIMAL_RECLAIM",
    "H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM",
]

def build():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(f"raw coverage low: {diag}")
    a1=b31.load_a1()
    ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity mismatch: {ident}")

    b1=s1.exact_bars(raw,"1h",12)
    b4=s1.exact_bars(raw,"4h",48)
    zones=s1.h4_demand_zones(b4)
    fam,_=s1b.classify(b1,zones)
    v=fam[fam.visual_equivalent].copy()
    if len(v)!=201:
        raise RuntimeError(f"frozen family drift: expected 201 got {len(v)}")

    width=(v.demand_high-v.demand_low).astype(float)
    c1=v.touch_close.astype(float)>v.demand_high.astype(float)
    c2=c1 & (v.touch_low.astype(float)>=v.demand_low.astype(float))
    c3=c1 & (v.touch_close.astype(float)>v.touch_open.astype(float))
    c4=c2 & ((v.expansion_high.astype(float)-v.h4_bos_close.astype(float))<=width)

    out=v[[
        "zone_id","activation_ts","origin_ts","h4_bos_ts","broken_h4_swing_ts",
        "broken_h4_level","h4_bos_close","demand_low","demand_high",
        "expansion_pivot_ts","expansion_high","first_touch_ts",
        "touch_open","touch_high","touch_low","touch_close"
    ]].copy()
    out["retest_year"]=pd.to_datetime(out.first_touch_ts,utc=True).dt.year.astype(int)
    out["demand_width"]=width.to_numpy(float)
    out["H4D_H1_PROXIMAL_RECLAIM"]=c1.to_numpy(bool)
    out["H4D_H1_CLEAN_PROXIMAL_RECLAIM"]=c2.to_numpy(bool)
    out["H4D_H1_BULLISH_PROXIMAL_RECLAIM"]=c3.to_numpy(bool)
    out["H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM"]=c4.to_numpy(bool)

    support=[]
    for c in CANDS:
        row={"candidate":c,"total":int(out[c].sum())}
        for y in [2022,2023,2024]:
            row[str(y)]=int(out.loc[out.retest_year==y,c].sum())
        support.append(row)
    S=pd.DataFrame(support)

    overlap=[]
    for a in CANDS:
        row={"candidate":a}
        for b in CANDS:
            row[b]=int((out[a] & out[b]).sum())
        overlap.append(row)
    O=pd.DataFrame(overlap)

    out.to_csv(ROOT/f"{PFX}_Membership.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Support.csv",index=False)
    O.to_csv(ROOT/f"{PFX}_Overlap.csv",index=False)

    lines=[
      "# BNB B37-S3 — Named Structural Detector Candidates","",
      "**STEP 3 — HYPOTHESIS FORMATION ONLY**","",
      "Frozen parent: **201 B37-S1B visual-equivalent events**. No outcome labels were used in this Step-3 output.","",
      "## Candidate definitions","",
      "1. **H4D_H1_PROXIMAL_RECLAIM** — first H1 retest closes above H4 demand_high.",
      "2. **H4D_H1_CLEAN_PROXIMAL_RECLAIM** — C1 plus retest low never violates demand_low.",
      "3. **H4D_H1_BULLISH_PROXIMAL_RECLAIM** — C1 plus the H1 retest candle closes above its open.",
      "4. **H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM** — C2 plus pre-retest expansion above the H4 BOS close is no more than one demand-zone width.","",
      "## Structural support only","",
      "| Candidate | Total | 2022 | 2023 | 2024 |",
      "|---|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.candidate} | {r.total} | {getattr(r,'_2')} | {getattr(r,'_3')} | {getattr(r,'_4')} |")

    lines += ["","## Interpretation",
      "- Candidate support is frequency only; **it is not a success rate**.",
      "- C1 tests whether the core character is simply a decisive proximal reclaim.",
      "- C2 asks whether keeping the distal H4 demand intact matters.",
      "- C3 asks whether the reaction candle itself must be bullish.",
      "- C4 tests the Step-2 overextension observation using one native zone-width as the only geometric boundary.","",
      "## Step-3 decision",
      "**FOUR NAMED CAUSAL STRUCTURAL HYPOTHESES FROZEN.**",
      "No candidate is promoted or rejected in Step 3. Step 4 must implement these as explicit detector states; Step 5 performs validation without changing their definitions."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B37_S3_CANDIDATES_FROZEN\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    build()
