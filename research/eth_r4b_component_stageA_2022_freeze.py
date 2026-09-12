#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_ALL = ROOT / "ETH_R4B_STAGEA_2022_ALL_COMPONENTS.csv"
OUT_COMPONENTS = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENTS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGEA_2022_COMPONENT_FREEZE.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGEA_2022_Status.txt"

LOOKBACKS = [60, 120, 180, 240, 360]
HOLDS = [120, 240, 360, 480]


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def economic_support(D: pd.DataFrame) -> pd.Series:
    return (
        (D.trades >= 50) & np.isfinite(D.wr) & (D.wr >= .52) &
        (D.net > 0) & np.isfinite(D.exp) & (D.exp > 0) &
        np.isfinite(D.pf) & (D.pf >= 1.15) & np.isfinite(D.dd) & (D.dd <= 160) &
        np.isfinite(D.H1_exp) & (D.H1_exp > 0) & np.isfinite(D.H1_pf) & (D.H1_pf > 1) &
        np.isfinite(D.H2_exp) & (D.H2_exp > 0) & np.isfinite(D.H2_pf) & (D.H2_pf > 1) &
        (D.positive_anchors >= 2)
    )


def components(coords: set[tuple[int, int]], li: dict[int, int], hi: dict[int, int]):
    unseen = set(coords)
    out = []
    while unseen:
        seed = min(unseen, key=lambda z: (hi[z[1]], li[z[0]], z[0], z[1]))
        q = deque([seed]); unseen.remove(seed); comp = {seed}
        while q:
            lb, hold = q.popleft()
            i, j = li[lb], hi[hold]
            for nlb, nhold in coords:
                if (nlb, nhold) in unseen and abs(li[nlb] - i) + abs(hi[nhold] - j) == 1:
                    unseen.remove((nlb, nhold)); comp.add((nlb, nhold)); q.append((nlb, nhold))
        out.append(sorted(comp, key=lambda z: (hi[z[1]], li[z[0]], z[0], z[1])))
    return out


def rank_components(d: pd.DataFrame) -> pd.DataFrame:
    return d.sort_values(
        ["component_size", "halo_economic_support_count", "halo_economic_support_ratio",
         "component_min_half_exp_floor", "component_exp_floor", "component_exp_mean",
         "component_pf_median", "component_dd_max", "character_rule", "min_hold", "min_lb"],
        ascending=[False, False, False, False, False, False, False, True, True, True, True],
        kind="mergesort",
    )


def main():
    li = {v: i for i, v in enumerate(LOOKBACKS)}
    hi = {v: i for i, v in enumerate(HOLDS)}
    all_summaries = []
    cell_lookup = {}

    for hour in range(24):
        p = ROOT / f"ETH_R3_H{hour:02d}_STAGEA_2022_DevGrid.csv"
        if not p.exists(): raise FileNotFoundError(p)
        D = pd.read_csv(p)
        if len(D) != 1800: raise AssertionError(f"H{hour:02d}: expected 1800 cells, got {len(D)}")
        D["dev_eligible"] = as_bool(D.dev_eligible)
        numeric = ["lookback_min","hold_min","trades","wr","net","exp","pf","dd","ls","H1_exp","H1_pf","H2_exp","H2_pf","min_half_exp","positive_anchors"]
        for c in numeric: D[c] = pd.to_numeric(D[c], errors="coerce")
        D["economic_support"] = economic_support(D)

        for rule, G in D.groupby(D.character_rule.astype(str), sort=True):
            E = G[G.dev_eligible].copy()
            if E.empty: continue
            coords = {(int(r.lookback_min), int(r.hold_min)) for r in E.itertuples(index=False)}
            comps = components(coords, li, hi)
            for raw_id, comp in enumerate(comps, start=1):
                C = E[E.apply(lambda z: (int(z.lookback_min), int(z.hold_min)) in set(comp), axis=1)].copy()
                all_rule_coords = [(int(r.lookback_min), int(r.hold_min)) for r in G.itertuples(index=False)]
                halo_coords = set()
                for x in all_rule_coords:
                    if min(abs(li[x[0]] - li[c[0]]) + abs(hi[x[1]] - hi[c[1]]) for c in comp) <= 1:
                        halo_coords.add(x)
                H = G[G.apply(lambda z: (int(z.lookback_min), int(z.hold_min)) in halo_coords, axis=1)].copy()
                econ_h = H[H.economic_support].copy()
                summary = {
                    "hour_wib": hour,
                    "character_rule": str(rule),
                    "raw_component_id": raw_id,
                    "component_size": int(len(C)),
                    "halo_cell_count": int(len(H)),
                    "halo_economic_support_count": int(len(econ_h)),
                    "halo_economic_support_ratio": float(len(econ_h) / len(H)) if len(H) else 0.0,
                    "component_min_half_exp_floor": float(C.min_half_exp.min()),
                    "component_min_half_exp_mean": float(C.min_half_exp.mean()),
                    "component_exp_floor": float(C.exp.min()),
                    "component_exp_mean": float(C.exp.mean()),
                    "component_pf_median": float(C.pf.median()),
                    "component_dd_max": float(C.dd.max()),
                    "component_wr_min": float(C.wr.min()),
                    "component_wr_mean": float(C.wr.mean()),
                    "component_trade_sum": int(C.trades.sum()),
                    "min_lb": min(c[0] for c in comp),
                    "max_lb": max(c[0] for c in comp),
                    "min_hold": min(c[1] for c in comp),
                    "max_hold": max(c[1] for c in comp),
                    "component_cells": ";".join(f"LB{lb}/H{hold}" for lb, hold in comp),
                }
                all_summaries.append(summary)
                cell_lookup[(hour, str(rule), raw_id)] = C.copy()

    ALL = pd.DataFrame(all_summaries)
    if ALL.empty: raise AssertionError("no connected components found")
    ALL.to_csv(OUT_ALL, index=False)

    frozen_summaries = []
    frozen_cells = []
    for hour in range(24):
        A = rank_components(ALL[ALL.hour_wib == hour].copy()).reset_index(drop=True)
        K = A.head(3).copy()
        K.insert(1, "component_rank", np.arange(1, len(K) + 1, dtype=int))
        for s in K.itertuples(index=False):
            frozen_summaries.append(s._asdict())
            C = cell_lookup[(hour, str(s.character_rule), int(s.raw_component_id))].copy()
            C = C.sort_values(["hold_min", "lookback_min"]).reset_index(drop=True)
            for cr in C.itertuples(index=False):
                frozen_cells.append({
                    "hour_wib": hour,
                    "component_rank": int(s.component_rank),
                    "character_rule": str(s.character_rule),
                    "raw_component_id": int(s.raw_component_id),
                    "component_size": int(s.component_size),
                    "lookback_min": int(cr.lookback_min),
                    "hold_min": int(cr.hold_min),
                    "dev_n": int(cr.trades),
                    "dev_wr": float(cr.wr),
                    "dev_net": float(cr.net),
                    "dev_exp": float(cr.exp),
                    "dev_pf": float(cr.pf),
                    "dev_dd": float(cr.dd),
                    "dev_ls": int(cr.ls),
                    "dev_H1_exp": float(cr.H1_exp),
                    "dev_H1_pf": float(cr.H1_pf),
                    "dev_H2_exp": float(cr.H2_exp),
                    "dev_H2_pf": float(cr.H2_pf),
                    "dev_min_half_exp": float(cr.min_half_exp),
                    "dev_positive_anchors": int(cr.positive_anchors),
                })

    F = pd.DataFrame(frozen_summaries).sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    C = pd.DataFrame(frozen_cells).sort_values(["hour_wib","component_rank","hold_min","lookback_min"]).reset_index(drop=True)
    F.to_csv(OUT_COMPONENTS, index=False)
    C.to_csv(OUT_CELLS, index=False)

    if len(F.groupby("hour_wib")) != 24: raise AssertionError("frozen components do not cover 24 hours")

    lines = [
        "# ETH R4b — Stage A 2022 Connected-Component Freeze", "",
        "**2022 ONLY. COMPONENTS FROZEN BEFORE R4b 2023. 2024-2026 CLOSED.**", "",
        f"Frozen components: **{len(F)}** across 24 WIB hours; frozen strict-eligible timing cells: **{len(C)}**.", "",
        "| Hour | Rank | Character | Size | Timing cells | Halo econ support | WR min/mean | Exp floor/mean | PF median | DD max |",
        "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for r in F.itertuples(index=False):
        lines.append(
            f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {r.component_cells} | "
            f"{int(r.halo_economic_support_count)}/{int(r.halo_cell_count)} | {100*float(r.component_wr_min):.2f}%/{100*float(r.component_wr_mean):.2f}% | "
            f"${float(r.component_exp_floor):+.2f}/${float(r.component_exp_mean):+.2f} | {float(r.component_pf_median):.3f} | ${float(r.component_dd_max):.2f} |"
        )
    lines += ["", "The component membership is now immutable for R4b Stage B. No cell may be added or removed after 2023 is inspected."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("ETH_R4B_2022_COMPONENTS_FROZEN\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
