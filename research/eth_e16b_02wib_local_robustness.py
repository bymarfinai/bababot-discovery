#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_GRID = ROOT / "ETH_E16A_02_03WIB_Grid.csv"
PFX = "ETH_E16B_02WIB_LOCAL_ROBUSTNESS"

OUT_NEIGHBORHOODS = ROOT / f"{PFX}_Neighborhoods.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_JACKKNIFE = ROOT / f"{PFX}_Jackknife.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SPECS = (
    {
        "label": "PRIMARY_RV_HIGH_RANGE_MID",
        "rule": "RV_HIGH__RANGE_MID",
        "center_lb": 150,
        "center_hold": 300,
        "lookbacks": (120, 150, 180),
        "holds": (270, 300, 330),
    },
    {
        "label": "SECONDARY_DRIVE_DOWN_STR_B60_80",
        "rule": "DRIVE_DOWN__STR_B60_80",
        "center_lb": 120,
        "center_hold": 330,
        "lookbacks": (90, 120, 150),
        "holds": (300, 330, 360),
    },
)
YEARS = (2022, 2023, 2024)


def pct(x):
    return "nan" if not np.isfinite(float(x)) else f"{100.0 * float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(float(x)) else f"${float(x):+.2f}"


def economic_support(df: pd.DataFrame) -> pd.Series:
    m = (
        (df.trades >= 160) &
        (df.win_rate >= 0.55) &
        (df.net_pnl > 0) &
        (df.expectancy >= 0.50) &
        (df.pf >= 1.20) &
        (df.max_dd <= 150.0) &
        (df.max_loss_streak <= 10)
    )
    for y in YEARS:
        m &= (df[f"y{y}_exp"] > 0) & (df[f"y{y}_pf"] > 1.0)
    return m


def neighborhood(grid: pd.DataFrame, spec: dict) -> pd.DataFrame:
    n = grid[
        (grid.character_rule == spec["rule"]) &
        (grid.lookback_min.isin(spec["lookbacks"])) &
        (grid.hold_min.isin(spec["holds"]))
    ].copy()
    if len(n) != 9:
        raise AssertionError(f"{spec['label']}: expected 9 cells, found {len(n)}")
    n["study"] = spec["label"]
    n["is_center"] = (n.lookback_min == spec["center_lb"]) & (n.hold_min == spec["center_hold"])
    n["distance"] = (
        (n.lookback_min - spec["center_lb"]).abs() / 30.0 +
        (n.hold_min - spec["center_hold"]).abs() / 30.0
    )
    n["is_axial"] = n["distance"] == 1.0
    n["economically_supportive"] = economic_support(n)
    if int(n.is_center.sum()) != 1:
        raise AssertionError(f"{spec['label']}: center missing/duplicated")
    if not bool(n.loc[n.is_center, "candidate_gate"].iloc[0]):
        raise AssertionError(f"{spec['label']}: frozen E16A center no longer full-gate PASS")
    return n.sort_values(["lookback_min", "hold_min"]).reset_index(drop=True)


def plateau_summary(n: pd.DataFrame, spec: dict) -> dict:
    support_n = int(n.economically_supportive.sum())
    axial = n[n.is_axial]
    if len(axial) != 4:
        raise AssertionError(f"{spec['label']}: expected 4 axial neighbors, found {len(axial)}")
    axial_support = int(axial.economically_supportive.sum())
    formal_n = int(n.candidate_gate.sum())
    med_wr = float(n.win_rate.median())
    med_exp = float(n.expectancy.median())
    med_pf = float(n.pf.median())
    center = n[n.is_center].iloc[0]
    plateau_pass = bool(
        bool(center.candidate_gate) and support_n >= 5 and axial_support >= 3 and
        med_wr >= 0.55 and med_exp >= 0.50 and med_pf >= 1.20
    )
    spike = bool(support_n <= 3 or axial_support <= 1)
    plateau_status = "PLATEAU_PASS" if plateau_pass else ("SPIKE_RISK" if spike else "MIXED")
    return {
        "study": spec["label"],
        "character_rule": spec["rule"],
        "center_lb": spec["center_lb"],
        "center_hold": spec["center_hold"],
        "formal_pass_cells": formal_n,
        "supportive_cells": support_n,
        "supportive_pct": support_n / 9.0,
        "axial_supportive": axial_support,
        "axial_supportive_pct": axial_support / 4.0,
        "median_wr": med_wr,
        "median_expectancy": med_exp,
        "median_pf": med_pf,
        "min_expectancy": float(n.expectancy.min()),
        "max_expectancy": float(n.expectancy.max()),
        "min_pf": float(n.pf.min()),
        "max_dd_worst": float(n.max_dd.max()),
        "plateau_status": plateau_status,
    }


def jackknife(n: pd.DataFrame, spec: dict) -> pd.DataFrame:
    rows = []
    for held in YEARS:
        train = [y for y in YEARS if y != held]
        x = n.copy()
        eligible = pd.Series(True, index=x.index)
        for y in train:
            eligible &= (
                (x[f"y{y}_wr"] >= 0.52) &
                (x[f"y{y}_exp"] > 0) &
                (x[f"y{y}_pf"] > 1.0)
            )
        e = x[eligible].copy()
        if len(e) == 0:
            rows.append({
                "study": spec["label"], "held_out_year": held, "eligible_train_cells": 0,
                "selected_lb": np.nan, "selected_hold": np.nan,
                "train_min_exp": np.nan, "train_mean_exp": np.nan,
                "train_min_pf": np.nan, "train_mean_wr": np.nan,
                "held_trades": 0, "held_wr": np.nan, "held_exp": np.nan, "held_pf": np.nan,
                "heldout_pass": False,
            })
            continue
        exp_cols = [f"y{y}_exp" for y in train]
        pf_cols = [f"y{y}_pf" for y in train]
        wr_cols = [f"y{y}_wr" for y in train]
        e["train_min_exp"] = e[exp_cols].min(axis=1)
        e["train_mean_exp"] = e[exp_cols].mean(axis=1)
        e["train_min_pf"] = e[pf_cols].min(axis=1)
        e["train_mean_wr"] = e[wr_cols].mean(axis=1)
        e = e.sort_values(
            ["train_min_exp", "train_mean_exp", "train_min_pf", "train_mean_wr", "distance", "hold_min", "lookback_min"],
            ascending=[False, False, False, False, True, True, True],
        )
        s = e.iloc[0]
        ht = int(s[f"y{held}_trades"])
        hw = float(s[f"y{held}_wr"])
        he = float(s[f"y{held}_exp"])
        hp = float(s[f"y{held}_pf"])
        hp_ok = bool(ht >= 40 and hw >= 0.52 and he > 0 and hp > 1.0)
        rows.append({
            "study": spec["label"], "held_out_year": held, "eligible_train_cells": len(e),
            "selected_lb": int(s.lookback_min), "selected_hold": int(s.hold_min),
            "train_min_exp": float(s.train_min_exp), "train_mean_exp": float(s.train_mean_exp),
            "train_min_pf": float(s.train_min_pf), "train_mean_wr": float(s.train_mean_wr),
            "held_trades": ht, "held_wr": hw, "held_exp": he, "held_pf": hp,
            "heldout_pass": hp_ok,
        })
    return pd.DataFrame(rows)


def classify(plateau: str, held_passes: int) -> str:
    if plateau == "PLATEAU_PASS" and held_passes == 3:
        return "ROBUST_STRONG"
    if plateau == "PLATEAU_PASS" and held_passes == 2:
        return "ROBUST_MODERATE"
    if plateau == "SPIKE_RISK" or held_passes <= 1:
        return "OVERFIT_RISK_HIGH"
    return "ROBUSTNESS_MIXED"


def main():
    if not IN_GRID.exists():
        raise FileNotFoundError(IN_GRID)
    grid = pd.read_csv(IN_GRID)
    required = {
        "lookback_min", "hold_min", "character_rule", "trades", "win_rate", "net_pnl",
        "expectancy", "pf", "max_dd", "max_loss_streak", "candidate_gate"
    }
    for y in YEARS:
        required |= {f"y{y}_trades", f"y{y}_wr", f"y{y}_exp", f"y{y}_pf"}
    missing = sorted(required - set(grid.columns))
    if missing:
        raise AssertionError(f"missing E16A columns: {missing}")

    ns, sums, jks = [], [], []
    for spec in SPECS:
        n = neighborhood(grid, spec)
        s = plateau_summary(n, spec)
        j = jackknife(n, spec)
        held_passes = int(j.heldout_pass.sum())
        s["jackknife_passes"] = held_passes
        s["jackknife_total"] = 3
        s["robustness_class"] = classify(s["plateau_status"], held_passes)
        ns.append(n)
        sums.append(s)
        jks.append(j)

    N = pd.concat(ns, ignore_index=True)
    S = pd.DataFrame(sums)
    J = pd.concat(jks, ignore_index=True)
    N.to_csv(OUT_NEIGHBORHOODS, index=False)
    S.to_csv(OUT_SUMMARY, index=False)
    J.to_csv(OUT_JACKKNIFE, index=False)

    primary = S[S.study == SPECS[0]["label"]].iloc[0]
    secondary = S[S.study == SPECS[1]["label"]].iloc[0]
    status = f"ETH_E16B_PRIMARY_{primary.robustness_class}"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH E16B — 02:00–03:00 WIB Local Robustness / Overfit Diagnostic", "",
        "**Development-only. OOS CLOSED. No live authorization.**", "",
        "E16B does not search for a new rule. It tests the preregistered 3×3 parameter neighborhoods around the two E16A formal passers and then performs leave-one-year-out local selection.", "",
        "## Plateau summary", "",
        "| Study | Formal PASS cells | Supportive cells | Axial supportive | Median WR | Median Exp | Median PF | Plateau | Jackknife | Classification |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.study} | {int(r.formal_pass_cells)}/9 | {int(r.supportive_cells)}/9 | {int(r.axial_supportive)}/4 | "
            f"{pct(r.median_wr)} | {money(r.median_expectancy)} | {float(r.median_pf):.3f} | {r.plateau_status} | "
            f"{int(r.jackknife_passes)}/3 | **{r.robustness_class}** |"
        )

    for spec in SPECS:
        n = N[N.study == spec["label"]].copy()
        lines += ["", f"## {spec['label']} — 3×3 neighborhood", "",
                  "| LB | Hold | N | WR | Exp | PF | DD | Era | Full gate | Supportive | Center/Axial |",
                  "|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
        for r in n.sort_values(["lookback_min", "hold_min"]).itertuples(index=False):
            marker = "CENTER" if bool(r.is_center) else ("AXIAL" if bool(r.is_axial) else "CORNER")
            lines.append(
                f"| {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {pct(r.win_rate)} | "
                f"{money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {bool(r.era_gate)} | "
                f"{bool(r.candidate_gate)} | {bool(r.economically_supportive)} | {marker} |"
            )
        jj = J[J.study == spec["label"]]
        lines += ["", "### Leave-one-year-out", "",
                  "| Held out | Selected LB/H | Eligible train cells | Held N | Held WR | Held Exp | Held PF | Pass |",
                  "|---:|---|---:|---:|---:|---:|---:|---|"]
        for r in jj.itertuples(index=False):
            sel = "none" if not np.isfinite(r.selected_lb) else f"LB{int(r.selected_lb)}/H{int(r.selected_hold)}"
            lines.append(
                f"| {int(r.held_out_year)} | {sel} | {int(r.eligible_train_cells)} | {int(r.held_trades)} | "
                f"{pct(r.held_wr)} | {money(r.held_exp)} | {('nan' if not np.isfinite(r.held_pf) else f'{float(r.held_pf):.3f}')} | {bool(r.heldout_pass)} |"
            )

    lines += [
        "", "## Verdict", "",
        f"Primary E16A center: **{primary.robustness_class}** ({primary.plateau_status}, jackknife {int(primary.jackknife_passes)}/3).",
        f"Secondary E16A center: **{secondary.robustness_class}** ({secondary.plateau_status}, jackknife {int(secondary.jackknife_passes)}/3).", "",
        "This is still Development-only robustness evidence, not true out-of-sample validation. OOS remains closed.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
