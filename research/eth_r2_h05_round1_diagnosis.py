#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
GRID_PATH = ROOT / "ETH_R1_H05_ROBUST_TrainGrid.csv"
OUT_FAMILY = ROOT / "ETH_R2_H05_R1_FamilyDiagnosis.csv"
OUT_CELL = ROOT / "ETH_R2_H05_R1_CellDiagnosis.csv"
OUT_RESULT = ROOT / "ETH_R2_H05_R1_Result.md"
OUT_STATUS = ROOT / "ETH_R2_H05_R1_Status.txt"

HOUR_WIB = 5
TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")
HALVES = r1.HALVES


def finite(x):
    return bool(np.isfinite(x))


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T)


def support_anchor(s):
    return bool(
        s["trades"] >= 30 and finite(s["win_rate"]) and s["win_rate"] >= .52 and
        s["net_pnl"] > 0 and finite(s["expectancy"]) and s["expectancy"] > 0 and
        finite(s["pf"]) and s["pf"] >= 1.05 and finite(s["max_dd"]) and s["max_dd"] <= 125 and
        s["max_loss_streak"] <= 10
    )


def comp_summary(F: pd.DataFrame):
    li = {v:i for i,v in enumerate(r1.LOOKBACKS)}
    hi = {v:i for i,v in enumerate(r1.HOLDS)}
    coords = [(li[int(x.lookback_min)], hi[int(x.hold_min)]) for x in F.itertuples(index=False)]
    comps = r1.connected_components(coords)
    return len(comps), max((len(c) for c in comps), default=0)


def main():
    if not GRID_PATH.exists():
        raise FileNotFoundError(GRID_PATH)
    D = pd.read_csv(GRID_PATH)
    if len(D) != 1800:
        raise AssertionError(f"expected frozen R1 H05 grid of 1800 cells, got {len(D)}")

    # R2 Round 1 may only diagnose rule families already supportive in frozen R1 H05.
    S = D[D.plateau_supportive.astype(bool)].copy()
    rules = sorted(S.character_rule.unique())
    if not rules:
        OUT_STATUS.write_text("ETH_R2_H05_R1_NO_FAMILY_HYPOTHESIS\n")
        OUT_FAMILY.write_text("character_rule,supportive_cells\n")
        OUT_CELL.write_text("character_rule,lookback_min,hold_min\n")
        OUT_RESULT.write_text("# ETH R2 H05 Round 1\n\nNO_FAMILY_HYPOTHESIS: R1 H05 contained no supportive family.\n")
        return

    # Hard firewall: the cache is built from pre-2024 bars only.
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    xtrain = x5.loc[pd.DatetimeIndex(x5.index) < TRAIN_END].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = r1.LOOKBACKS
    e12.HOLDS = r1.HOLDS
    cache = e12.prep(xtrain)

    cell_rows = []
    for rr in S.itertuples(index=False):
        T = r1.candidate_events(cache, int(rr.lookback_min), int(rr.hold_min), str(rr.character_rule))
        row = {
            "character_rule": str(rr.character_rule),
            "lookback_min": int(rr.lookback_min),
            "hold_min": int(rr.hold_min),
            "strict_gate": bool(rr.strict_gate),
            "temporal_gate": bool(rr.temporal_gate),
            "strict_temporal": bool(rr.strict_temporal),
            "pooled_trades": int(rr.trades),
            "pooled_wr": float(rr.win_rate),
            "pooled_net": float(rr.net_pnl),
            "pooled_exp": float(rr.expectancy),
            "pooled_pf": float(rr.pf),
            "pooled_dd": float(rr.max_dd),
            "pooled_ls": int(rr.max_loss_streak),
            "positive_halves_r1": int(rr.positive_halves),
            "supportive_anchors_r1": int(rr.supportive_anchors),
            "evaluable_anchors_r1": int(rr.evaluable_anchors),
        }
        pos_net_sum = 0.0
        half_net = []
        positive_halves = 0
        for name, start, end in HALVES:
            H = T[(pd.DatetimeIndex(T.entry_ts) >= start) & (pd.DatetimeIndex(T.exit_ts) < end)]
            hs = stats(H)
            row[f"{name}_trades"] = int(hs["trades"])
            row[f"{name}_wr"] = float(hs["win_rate"]) if finite(hs["win_rate"]) else np.nan
            row[f"{name}_net"] = float(hs["net_pnl"])
            row[f"{name}_exp"] = float(hs["expectancy"]) if finite(hs["expectancy"]) else np.nan
            row[f"{name}_pf"] = float(hs["pf"]) if finite(hs["pf"]) else np.nan
            half_net.append(float(hs["net_pnl"]))
            if hs["net_pnl"] > 0:
                pos_net_sum += float(hs["net_pnl"])
            if finite(hs["expectancy"]) and hs["expectancy"] > 0 and finite(hs["pf"]) and hs["pf"] > 1:
                positive_halves += 1
        row["positive_halves_recalc"] = positive_halves
        row["max_positive_half_share"] = (
            max((max(v, 0.0) for v in half_net), default=0.0) / pos_net_sum if pos_net_sum > 0 else np.nan
        )

        anchor_support = 0
        anchor_eval = 0
        anchor_nets = []
        for i, clock in enumerate(e12.CLOCKS):
            A = T[T.clock == clock]
            a = stats(A)
            ev = a["trades"] >= 30
            sup = support_anchor(a)
            anchor_eval += int(ev)
            anchor_support += int(sup)
            anchor_nets.append(float(a["net_pnl"]))
            row[f"anchor{i}_clock_utc_min"] = int(clock)
            row[f"anchor{i}_trades"] = int(a["trades"])
            row[f"anchor{i}_wr"] = float(a["win_rate"]) if finite(a["win_rate"]) else np.nan
            row[f"anchor{i}_net"] = float(a["net_pnl"])
            row[f"anchor{i}_exp"] = float(a["expectancy"]) if finite(a["expectancy"]) else np.nan
            row[f"anchor{i}_pf"] = float(a["pf"]) if finite(a["pf"]) else np.nan
            row[f"anchor{i}_supportive"] = bool(sup)
        row["supportive_anchors_recalc"] = anchor_support
        row["evaluable_anchors_recalc"] = anchor_eval
        pos_anchor = sum(max(v, 0.0) for v in anchor_nets)
        row["max_positive_anchor_share"] = (
            max((max(v, 0.0) for v in anchor_nets), default=0.0) / pos_anchor if pos_anchor > 0 else np.nan
        )
        cell_rows.append(row)

    C = pd.DataFrame(cell_rows)
    C.to_csv(OUT_CELL, index=False)

    family_rows = []
    for rule in rules:
        F = S[S.character_rule == rule].copy()
        FC = C[C.character_rule == rule].copy()
        ncomp, maxcomp = comp_summary(F)
        strict_temporal_cells = int(F.strict_temporal.astype(bool).sum())
        best_pos_halves = int(FC.positive_halves_recalc.max()) if len(FC) else 0
        anchor_best = int(FC.supportive_anchors_recalc.max()) if len(FC) else 0
        max_half_conc = float(FC.max_positive_half_share.min()) if len(FC) else np.nan
        max_anchor_conc = float(FC.max_positive_anchor_share.min()) if len(FC) else np.nan

        flags = []
        if maxcomp < 4:
            flags.append("TIMING_FRAGILITY")
        if best_pos_halves < 3:
            flags.append("TEMPORAL_FRAGILITY")
        if anchor_best < 3:
            flags.append("ANCHOR_FRAGILITY")
        if int(FC.pooled_trades.min()) < 100:
            flags.append("SAMPLE_INSUFFICIENCY")
        if float(FC.pooled_exp.median()) <= 0 or float(FC.pooled_pf.median()) <= 1.05:
            flags.append("ECONOMIC_WEAKNESS")
        if not flags:
            flags = ["PLATEAU_GEOMETRY_ONLY"]

        family_rows.append({
            "character_rule": rule,
            "supportive_cells": len(F),
            "connected_components": ncomp,
            "max_component_cells": maxcomp,
            "strict_temporal_cells": strict_temporal_cells,
            "best_positive_halves": best_pos_halves,
            "best_supportive_anchors": anchor_best,
            "median_expectancy": float(FC.pooled_exp.median()),
            "median_pf": float(FC.pooled_pf.median()),
            "min_best_half_concentration": max_half_conc,
            "min_best_anchor_concentration": max_anchor_conc,
            "failure_modes": ";".join(flags),
        })

    FAM = pd.DataFrame(family_rows)
    # Frozen diagnostic ranking: evidence of strict+temporal first, then topology breadth, then support count,
    # then temporal/anchor breadth, then family median economics. This does NOT freeze a trading candidate.
    FAM = FAM.sort_values(
        ["strict_temporal_cells", "max_component_cells", "supportive_cells", "best_positive_halves",
         "best_supportive_anchors", "median_expectancy", "median_pf", "character_rule"],
        ascending=[False, False, False, False, False, False, False, True],
    ).reset_index(drop=True)
    FAM["diagnostic_rank"] = np.arange(1, len(FAM) + 1)
    FAM.to_csv(OUT_FAMILY, index=False)

    top = FAM.iloc[0]
    warrants = bool(
        int(top.strict_temporal_cells) >= 1 or
        (int(top.max_component_cells) >= 2 and int(top.supportive_cells) >= 2 and int(top.best_positive_halves) >= 3)
    )
    if warrants:
        status = "ETH_R2_H05_R1_ONE_FAMILY_HYPOTHESIS"
        hypothesis = (
            f"Round-2 family: {top.character_rule}. Test whether the character itself is stable under "
            "pre-registered threshold/definition perturbation while keeping the coarse timing grid and 2024 lock fixed. "
            "Do not fine-tune LB/Hold around the R1 point."
        )
    else:
        status = "ETH_R2_H05_R1_NO_FAMILY_HYPOTHESIS"
        hypothesis = "No family has enough internal structure to justify a Round-2 hypothesis."
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH R2 H05 — Round 1 Structural Diagnosis", "",
        "**DIAGNOSTIC ONLY. 2022–2023 ONLY. 2024 HARD LOCKED. OOS 2025+ CLOSED.**", "",
        f"Source coverage: {coverage:.4%}. Frozen R1 H05 supportive families diagnosed: **{len(FAM)}**.", "",
        "| Rank | Family | Supportive cells | Max component | Strict+temporal | Best + halves | Best anchors | Med exp | Med PF | Failure modes |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in FAM.itertuples(index=False):
        lines.append(
            f"| {int(r.diagnostic_rank)} | {r.character_rule} | {int(r.supportive_cells)} | {int(r.max_component_cells)} | "
            f"{int(r.strict_temporal_cells)} | {int(r.best_positive_halves)}/4 | {int(r.best_supportive_anchors)}/4 | "
            f"${float(r.median_expectancy):+.2f} | {float(r.median_pf):.3f} | {r.failure_modes} |"
        )
    lines += ["", "## Round-1 verdict", "", f"**{status.replace('ETH_R2_H05_R1_', '')}**", "", hypothesis, "",
              "No 2024 data were evaluated and no validation candidate was frozen."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
