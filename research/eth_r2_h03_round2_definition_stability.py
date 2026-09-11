#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R2_H03_R2"
OUT_GRID = ROOT / f"{PFX}_DefinitionGrid.csv"
OUT_TIMING = ROOT / f"{PFX}_TimingStability.csv"
OUT_REGIONS = ROOT / f"{PFX}_Regions.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HOUR_WIB = 3
LOOKBACKS = r1.LOOKBACKS
HOLDS = r1.HOLDS
TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")
DEFINITIONS = {
    "LOOSE": (0.60, 0.30, 0.70),
    "BASE": (2.0/3.0, 1.0/3.0, 2.0/3.0),
    "TIGHT": (0.75, 0.375, 0.625),
}


def key_for(label: str) -> str:
    return f"R2_H03_RV_RANGE_{label}"


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    # Hard firewall: Round 2 receives no 2024+ bars.
    xtrain = x5.loc[pd.DatetimeIndex(x5.index) < TRAIN_END].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    cache = e12.prep(xtrain)

    # Add the three preregistered nested definitions to every cached state mask.
    for pack in cache.values():
        S, ent, pre, ex, valid, xp, delta, masks = pack
        rv = S.rv_pct.to_numpy(float)
        rg = S.range_pct.to_numpy(float)
        finite = np.isfinite(rv) & np.isfinite(rg)
        for label, (rv_lo, range_lo, range_hi) in DEFINITIONS.items():
            masks[key_for(label)] = finite & (rv >= rv_lo) & (rg >= range_lo) & (rg < range_hi)

    rows = []
    for label in DEFINITIONS:
        k = key_for(label)
        for lb in LOOKBACKS:
            for hold in HOLDS:
                row = r1.evaluate(cache, int(lb), int(hold), k)
                row["definition"] = label
                rows.append(row)
    D = pd.DataFrame(rows)
    expected = len(DEFINITIONS) * len(LOOKBACKS) * len(HOLDS)
    if len(D) != expected:
        raise AssertionError(f"Round-2 grid mismatch {len(D)} != {expected}")
    D.to_csv(OUT_GRID, index=False)

    timing_rows = []
    for lb in LOOKBACKS:
        for hold in HOLDS:
            G = D[(D.lookback_min == lb) & (D.hold_min == hold)].copy()
            if set(G.definition) != set(DEFINITIONS):
                raise AssertionError("missing preregistered definition")
            loose = G[G.definition == "LOOSE"].iloc[0]
            base = G[G.definition == "BASE"].iloc[0]
            tight = G[G.definition == "TIGHT"].iloc[0]
            med_exp = float(G.expectancy.median())
            med_pf = float(G.pf.median())
            stable = bool(
                bool(base.plateau_supportive) and
                (bool(loose.plateau_supportive) or bool(tight.plateau_supportive)) and
                med_exp > 0 and med_pf >= 1.05
            )
            timing_rows.append({
                "lookback_min": int(lb),
                "hold_min": int(hold),
                "LOOSE_supportive": bool(loose.plateau_supportive),
                "BASE_supportive": bool(base.plateau_supportive),
                "TIGHT_supportive": bool(tight.plateau_supportive),
                "supportive_definitions": int(G.plateau_supportive.astype(bool).sum()),
                "BASE_strict_temporal": bool(base.strict_temporal),
                "median_expectancy": med_exp,
                "median_pf": med_pf,
                "definition_stable": stable,
            })
    T = pd.DataFrame(timing_rows)
    T.to_csv(OUT_TIMING, index=False)

    li = {v:i for i,v in enumerate(LOOKBACKS)}
    hi = {v:i for i,v in enumerate(HOLDS)}
    coords = [(li[int(r.lookback_min)], hi[int(r.hold_min)]) for r in T[T.definition_stable].itertuples(index=False)]
    comps = r1.connected_components(coords)
    region_rows = []
    for rid, comp in enumerate(comps, 1):
        cells = []
        for i, j in comp:
            cells.append(T[(T.lookback_min == LOOKBACKS[i]) & (T.hold_min == HOLDS[j])].iloc[0])
        C = pd.DataFrame(cells)
        lbs = sorted(set(int(x) for x in C.lookback_min))
        holds = sorted(set(int(x) for x in C.hold_min))
        base_strict = int(C.BASE_strict_temporal.astype(bool).sum())
        med_exp = float(C.median_expectancy.median())
        med_pf = float(C.median_pf.median())
        qualifies = bool(
            len(C) >= 4 and len(lbs) >= 2 and len(holds) >= 2 and base_strict >= 1 and
            med_exp > 0 and med_pf >= 1.05
        )
        region_rows.append({
            "region_id": rid,
            "cells": len(C),
            "lookbacks": ";".join(map(str, lbs)),
            "holds": ";".join(map(str, holds)),
            "BASE_strict_temporal_cells": base_strict,
            "median_timing_median_exp": med_exp,
            "median_timing_median_pf": med_pf,
            "qualifies": qualifies,
        })
    R = pd.DataFrame(region_rows, columns=[
        "region_id","cells","lookbacks","holds","BASE_strict_temporal_cells",
        "median_timing_median_exp","median_timing_median_pf","qualifies"
    ])
    R.to_csv(OUT_REGIONS, index=False)

    n_support = {label: int(D[D.definition == label].plateau_supportive.astype(bool).sum()) for label in DEFINITIONS}
    n_strict = {label: int(D[D.definition == label].strict_temporal.astype(bool).sum()) for label in DEFINITIONS}
    n_stable = int(T.definition_stable.astype(bool).sum())
    n_qual = int(R.qualifies.astype(bool).sum()) if len(R) else 0

    if n_qual > 0:
        status = "ETH_R2_H03_R2_DEFINITION_ROBUST_TIMING_REGION"
        verdict = "DEFINITION_ROBUST_TIMING_REGION"
    else:
        status = "ETH_R2_H03_R2_CHARACTER_DEFINITION_OR_TIMING_FRAGILE"
        verdict = "CHARACTER_DEFINITION_OR_TIMING_FRAGILE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH R2 H03 — Round 2 Definition Stability", "",
        "**2022–2023 ONLY. 2024 HARD LOCKED. OOS 2025+ CLOSED.**", "",
        f"Source coverage: {coverage:.4%}.",
        "Character hypothesis: RV_HIGH × RANGE_MID, tested with preregistered nested LOOSE/BASE/TIGHT percentile definitions.",
        f"Frozen timing grid: {len(LOOKBACKS)} lookbacks × {len(HOLDS)} holds = {len(T)} timings; {len(D)} definition/timing cells.", "",
        "| Definition | Plateau-supportive cells | Strict+temporal cells |",
        "|---|---:|---:|",
    ]
    for label in ("LOOSE", "BASE", "TIGHT"):
        lines.append(f"| {label} | {n_support[label]} | {n_strict[label]} |")
    lines += [
        "", f"Definition-stable timing cells: **{n_stable}/20**.",
        f"Qualifying connected robust regions: **{n_qual}**.", "",
        "## Verdict", "", f"**{verdict}**", "",
    ]
    if n_qual:
        lines.append("The H03 high-RV/mid-range character survives preregistered definition perturbation as a broad timing region. 2024 remains locked; the next round must be preregistered before execution.")
    else:
        lines.append("The H03 high-RV/mid-range character did not produce a sufficiently broad definition-stable timing region. No observed definition is selected as a rescue winner and 2024 remains locked.")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
