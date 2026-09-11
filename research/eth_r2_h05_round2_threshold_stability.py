#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R2_H05_R2"
OUT_GRID = ROOT / f"{PFX}_ThresholdGrid.csv"
OUT_TIMING = ROOT / f"{PFX}_TimingStability.csv"
OUT_REGIONS = ROOT / f"{PFX}_Regions.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HOUR_WIB = 5
THRESHOLDS = (0.70, 0.80, 0.90)
LOOKBACKS = r1.LOOKBACKS
HOLDS = r1.HOLDS
TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")


def key_for(t: float) -> str:
    return f"R2_DRIVE_DOWN_STR_GE_{int(round(t*100)):02d}"


def finite(x):
    return bool(np.isfinite(x))


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    # Hard firewall: no 2024+ bars enter the Round-2 cache.
    xtrain = x5.loc[pd.DatetimeIndex(x5.index) < TRAIN_END].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    cache = e12.prep(xtrain)

    # Add the three preregistered nested character definitions to the cached masks.
    for (_, _, _), pack in cache.items():
        S, ent, pre, ex, valid, xp, delta, masks = pack
        drive = S.drive_return.to_numpy(float)
        strength = S.strength_pct.to_numpy(float)
        for t in THRESHOLDS:
            masks[key_for(t)] = np.isfinite(drive) & np.isfinite(strength) & (drive < 0) & (strength >= t)

    rows = []
    for t in THRESHOLDS:
        k = key_for(t)
        for lb in LOOKBACKS:
            for hold in HOLDS:
                row = r1.evaluate(cache, int(lb), int(hold), k)
                row["threshold"] = t
                row["threshold_label"] = f"T{int(round(t*100))}"
                rows.append(row)
    D = pd.DataFrame(rows)
    if len(D) != len(THRESHOLDS) * len(LOOKBACKS) * len(HOLDS):
        raise AssertionError("Round-2 grid size mismatch")
    D.to_csv(OUT_GRID, index=False)

    timing_rows = []
    for lb in LOOKBACKS:
        for hold in HOLDS:
            G = D[(D.lookback_min == lb) & (D.hold_min == hold)].sort_values("threshold")
            if len(G) != 3:
                raise AssertionError("missing threshold perturbation")
            g70 = G[G.threshold == .70].iloc[0]
            g80 = G[G.threshold == .80].iloc[0]
            g90 = G[G.threshold == .90].iloc[0]
            supportive_count = int(G.plateau_supportive.astype(bool).sum())
            med_exp = float(G.expectancy.median())
            med_pf = float(G.pf.median())
            stable = bool(
                bool(g80.plateau_supportive) and
                (bool(g70.plateau_supportive) or bool(g90.plateau_supportive)) and
                med_exp > 0 and med_pf >= 1.05
            )
            timing_rows.append({
                "lookback_min": int(lb),
                "hold_min": int(hold),
                "T70_supportive": bool(g70.plateau_supportive),
                "T80_supportive": bool(g80.plateau_supportive),
                "T90_supportive": bool(g90.plateau_supportive),
                "supportive_thresholds": supportive_count,
                "T80_strict_temporal": bool(g80.strict_temporal),
                "median_expectancy": med_exp,
                "median_pf": med_pf,
                "threshold_stable": stable,
            })
    T = pd.DataFrame(timing_rows)
    T.to_csv(OUT_TIMING, index=False)

    li = {v:i for i,v in enumerate(LOOKBACKS)}
    hi = {v:i for i,v in enumerate(HOLDS)}
    coords = [(li[int(r.lookback_min)], hi[int(r.hold_min)]) for r in T[T.threshold_stable].itertuples(index=False)]
    comps = r1.connected_components(coords)
    region_rows = []
    for rid, comp in enumerate(comps, 1):
        cells = []
        for i, j in comp:
            cells.append(T[(T.lookback_min == LOOKBACKS[i]) & (T.hold_min == HOLDS[j])].iloc[0])
        C = pd.DataFrame(cells)
        lbs = sorted(set(int(x) for x in C.lookback_min))
        holds = sorted(set(int(x) for x in C.hold_min))
        t80_strict = int(C.T80_strict_temporal.astype(bool).sum())
        med_exp = float(C.median_expectancy.median())
        med_pf = float(C.median_pf.median())
        qualifies = bool(
            len(C) >= 4 and len(lbs) >= 2 and len(holds) >= 2 and t80_strict >= 1 and
            med_exp > 0 and med_pf >= 1.05
        )
        region_rows.append({
            "region_id": rid,
            "cells": len(C),
            "lookbacks": ";".join(map(str, lbs)),
            "holds": ";".join(map(str, holds)),
            "T80_strict_temporal_cells": t80_strict,
            "median_timing_median_exp": med_exp,
            "median_timing_median_pf": med_pf,
            "qualifies": qualifies,
        })
    R = pd.DataFrame(region_rows, columns=[
        "region_id","cells","lookbacks","holds","T80_strict_temporal_cells",
        "median_timing_median_exp","median_timing_median_pf","qualifies"
    ])
    R.to_csv(OUT_REGIONS, index=False)

    n_support = {f"T{int(t*100)}": int(D[D.threshold == t].plateau_supportive.astype(bool).sum()) for t in THRESHOLDS}
    n_strict = {f"T{int(t*100)}": int(D[D.threshold == t].strict_temporal.astype(bool).sum()) for t in THRESHOLDS}
    n_stable = int(T.threshold_stable.astype(bool).sum())
    n_qual = int(R.qualifies.astype(bool).sum()) if len(R) else 0

    if n_qual > 0:
        status = "ETH_R2_H05_R2_THRESHOLD_ROBUST_TIMING_REGION"
        verdict = "THRESHOLD_ROBUST_TIMING_REGION"
    else:
        status = "ETH_R2_H05_R2_CHARACTER_THRESHOLD_OR_TIMING_FRAGILE"
        verdict = "CHARACTER_THRESHOLD_OR_TIMING_FRAGILE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH R2 H05 — Round 2 Threshold Stability", "",
        "**2022–2023 ONLY. 2024 HARD LOCKED. OOS 2025+ CLOSED.**", "",
        f"Source coverage: {coverage:.4%}.",
        "Character hypothesis: DRIVE_DOWN + upper-tail strength, perturbed at T70/T80/T90.",
        f"Frozen timing grid: {len(LOOKBACKS)} lookbacks × {len(HOLDS)} holds = {len(T)} timings; 60 threshold/timing cells.", "",
        "| Threshold | Plateau-supportive cells | Strict+temporal cells |",
        "|---|---:|---:|",
    ]
    for label in ("T70","T80","T90"):
        lines.append(f"| {label} | {n_support[label]} | {n_strict[label]} |")
    lines += ["", f"Threshold-stable timing cells: **{n_stable}/20**.", f"Qualifying connected robust regions: **{n_qual}**.", "",
              "## Verdict", "", f"**{verdict}**", ""]
    if n_qual:
        lines.append("The upper-tail down-drive character survives threshold perturbation as a broad timing region. Round 3 may test walk-forward/executable robustness, but 2024 remains locked.")
    else:
        lines.append("The preregistered upper-tail down-drive character did not produce a sufficiently broad threshold-stable timing region. No threshold winner is selected and 2024 remains locked.")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
