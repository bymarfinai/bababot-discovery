#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R1_H00_ROBUST"
HOUR_WIB = 0
LOOKBACKS = (60, 120, 180, 240, 360)
HOLDS = (120, 240, 360, 480)
EXPECTED_RULES = 90
EXPECTED_GRID = len(LOOKBACKS) * len(HOLDS) * EXPECTED_RULES
TRAIN_START = pd.Timestamp("2022-01-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")
YEARS = (2022, 2023)
HALVES = (
    ("2022H1", pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2022-07-01", tz="UTC")),
    ("2022H2", pd.Timestamp("2022-07-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC")),
    ("2023H1", pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2023-07-01", tz="UTC")),
    ("2023H2", pd.Timestamp("2023-07-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")),
)

OUT_GRID = ROOT / f"{PFX}_TrainGrid.csv"
OUT_REGIONS = ROOT / f"{PFX}_TrainRegions.csv"
OUT_LOCK = ROOT / f"{PFX}_FrozenCandidate.csv"
OUT_RESULT = ROOT / f"{PFX}_TrainResult.md"
OUT_STATUS = ROOT / f"{PFX}_TrainStatus.txt"


def clocks_for_hour(h: int):
    base = ((h - 7) % 24) * 60
    return tuple((base + q) % 1440 for q in (0, 15, 30, 45))


def finite(x):
    return bool(np.isfinite(x))


def pct(x):
    return "nan" if not finite(x) else f"{100.0*float(x):.2f}%"


def money(x):
    return "nan" if not finite(x) else f"${float(x):+.2f}"


def stats_from_df(T: pd.DataFrame):
    if len(T) == 0:
        return e12.summarize(np.array([]), np.array([]))
    return e12.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def period_stats(T: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    if len(T) == 0:
        return stats_from_df(T)
    m = (pd.DatetimeIndex(T.entry_ts) >= start) & (pd.DatetimeIndex(T.exit_ts) < end)
    return stats_from_df(T.loc[m])


def candidate_events(cache, lb: int, hold: int, rule: str):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ex = pd.DatetimeIndex(ex)
        m = valid & (pre >= TRAIN_START) & (ent >= TRAIN_START) & (ex < TRAIN_END) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
            })
    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def evaluate(cache, lb: int, hold: int, rule: str):
    T = candidate_events(cache, lb, hold, rule)
    pooled = stats_from_df(T)
    row = {
        "hour_wib": HOUR_WIB,
        "lookback_min": lb,
        "hold_min": hold,
        "character_rule": rule,
        **pooled,
    }

    supportive_anchors = 0
    evaluable_anchors = 0
    for clock in e12.CLOCKS:
        A = T.loc[T.clock == clock]
        s = stats_from_df(A)
        ev = s["trades"] >= 30
        sup = bool(
            ev and finite(s["win_rate"]) and s["win_rate"] >= .52 and
            s["net_pnl"] > 0 and finite(s["expectancy"]) and s["expectancy"] > 0 and
            finite(s["pf"]) and s["pf"] >= 1.05 and finite(s["max_dd"]) and s["max_dd"] <= 125 and
            s["max_loss_streak"] <= 10
        )
        evaluable_anchors += int(ev)
        supportive_anchors += int(sup)
    row["evaluable_anchors"] = evaluable_anchors
    row["supportive_anchors"] = supportive_anchors

    good_year_wr55 = 0
    year_strict = True
    plateau_years = True
    for y in YEARS:
        ys = period_stats(T, pd.Timestamp(f"{y}-01-01", tz="UTC"), pd.Timestamp(f"{y+1}-01-01", tz="UTC"))
        row.update({
            f"y{y}_trades": ys["trades"], f"y{y}_wr": ys["win_rate"],
            f"y{y}_net": ys["net_pnl"], f"y{y}_exp": ys["expectancy"], f"y{y}_pf": ys["pf"],
        })
        yok = bool(
            ys["trades"] >= 40 and finite(ys["win_rate"]) and ys["win_rate"] >= .52 and
            ys["net_pnl"] > 0 and finite(ys["expectancy"]) and ys["expectancy"] > 0 and
            finite(ys["pf"]) and ys["pf"] >= 1.05
        )
        year_strict &= yok
        good_year_wr55 += int(finite(ys["win_rate"]) and ys["win_rate"] >= .55)
        pok = bool(
            ys["trades"] >= 25 and finite(ys["expectancy"]) and ys["expectancy"] > 0 and
            finite(ys["pf"]) and ys["pf"] >= 1.00
        )
        plateau_years &= pok

    half_positive = 0
    half_n_ok = True
    half_floor_ok = True
    min_half_exp = np.inf
    for name, start, end in HALVES:
        hs = period_stats(T, start, end)
        row.update({
            f"{name}_trades": hs["trades"], f"{name}_wr": hs["win_rate"],
            f"{name}_exp": hs["expectancy"], f"{name}_pf": hs["pf"],
        })
        half_n_ok &= hs["trades"] >= 15
        positive = finite(hs["expectancy"]) and hs["expectancy"] > 0 and finite(hs["pf"]) and hs["pf"] > 1.00
        half_positive += int(positive)
        expv = hs["expectancy"] if finite(hs["expectancy"]) else -np.inf
        min_half_exp = min(min_half_exp, expv)
        half_floor_ok &= expv >= -0.75

    row["positive_halves"] = half_positive
    row["min_half_exp"] = float(min_half_exp)
    row["temporal_gate"] = bool(half_n_ok and half_positive >= 3 and half_floor_ok)

    row["strict_gate"] = bool(
        pooled["trades"] >= 120 and finite(pooled["win_rate"]) and pooled["win_rate"] >= .55 and
        pooled["net_pnl"] > 0 and finite(pooled["expectancy"]) and pooled["expectancy"] >= .50 and
        finite(pooled["pf"]) and pooled["pf"] >= 1.20 and finite(pooled["max_dd"]) and pooled["max_dd"] <= 125 and
        pooled["max_loss_streak"] <= 8 and year_strict and good_year_wr55 >= 1 and
        evaluable_anchors >= 3 and supportive_anchors >= 3
    )
    row["plateau_supportive"] = bool(
        pooled["trades"] >= 100 and finite(pooled["win_rate"]) and pooled["win_rate"] >= .52 and
        pooled["net_pnl"] > 0 and finite(pooled["expectancy"]) and pooled["expectancy"] > 0 and
        finite(pooled["pf"]) and pooled["pf"] >= 1.05 and finite(pooled["max_dd"]) and pooled["max_dd"] <= 150 and
        pooled["max_loss_streak"] <= 10 and plateau_years
    )
    row["strict_temporal"] = bool(row["strict_gate"] and row["temporal_gate"])
    return row


def connected_components(cells):
    cells = set(cells)
    comps = []
    while cells:
        seed = cells.pop()
        stack = [seed]
        comp = {seed}
        while stack:
            i, j = stack.pop()
            for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if n in cells:
                    cells.remove(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def build_regions(D: pd.DataFrame):
    li = {v:i for i,v in enumerate(LOOKBACKS)}
    hi = {v:i for i,v in enumerate(HOLDS)}
    rows = []
    region_cells = {}
    rid = 0
    for rule in e12.RULES:
        R = D[(D.character_rule == rule) & D.plateau_supportive].copy()
        coords = [(li[int(r.lookback_min)], hi[int(r.hold_min)]) for r in R.itertuples(index=False)]
        for comp in connected_components(coords):
            rid += 1
            C = []
            for i,j in comp:
                rr = D[(D.character_rule == rule) & (D.lookback_min == LOOKBACKS[i]) & (D.hold_min == HOLDS[j])].iloc[0]
                C.append(rr)
            Cdf = pd.DataFrame(C)
            stricts = Cdf[Cdf.strict_temporal]
            lbs = sorted(set(int(x) for x in Cdf.lookback_min))
            holds = sorted(set(int(x) for x in Cdf.hold_min))
            qualifies = len(Cdf) >= 4 and len(lbs) >= 2 and len(holds) >= 2 and len(stricts) >= 1
            rows.append({
                "region_id": rid,
                "character_rule": rule,
                "cells": len(Cdf),
                "lookbacks": ";".join(map(str,lbs)),
                "holds": ";".join(map(str,holds)),
                "strict_temporal_cells": len(stricts),
                "median_expectancy": float(Cdf.expectancy.median()),
                "median_pf": float(Cdf.pf.median()),
                "median_max_dd": float(Cdf.max_dd.median()),
                "qualifies": bool(qualifies),
            })
            region_cells[rid] = (comp, Cdf)
    return pd.DataFrame(rows), region_cells


def select_frozen(D: pd.DataFrame, regions: pd.DataFrame, region_cells):
    Q = regions[regions.qualifies].copy()
    if len(Q) == 0:
        return None, None
    Q = Q.sort_values(
        ["strict_temporal_cells", "cells", "median_expectancy", "median_pf", "median_max_dd", "character_rule", "region_id"],
        ascending=[False, False, False, False, True, True, True],
    ).reset_index(drop=True)
    reg = Q.iloc[0]
    comp, Cdf = region_cells[int(reg.region_id)]
    stricts = Cdf[Cdf.strict_temporal].copy()
    li = {v:i for i,v in enumerate(LOOKBACKS)}
    hi = {v:i for i,v in enumerate(HOLDS)}
    dists = []
    for r in stricts.itertuples(index=False):
        p = (li[int(r.lookback_min)], hi[int(r.hold_min)])
        dist = sum(abs(p[0]-q[0]) + abs(p[1]-q[1]) for q in comp)
        dists.append(dist)
    stricts["region_manhattan_sum"] = dists
    stricts = stricts.sort_values(
        ["region_manhattan_sum", "hold_min", "lookback_min", "character_rule"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)
    return reg, stricts.iloc[0]


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    if len(e12.RULES) != EXPECTED_RULES:
        raise AssertionError(f"rule grammar drift: {len(e12.RULES)}")

    # Hard firewall: train engine receives no 2024+ bars.
    xtrain = x5.loc[pd.DatetimeIndex(x5.index) < TRAIN_END].copy()
    e12.CLOCKS = clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    cache = e12.prep(xtrain)

    rows = [evaluate(cache, lb, hold, rule) for lb in LOOKBACKS for hold in HOLDS for rule in e12.RULES]
    D = pd.DataFrame(rows)
    if len(D) != EXPECTED_GRID:
        raise AssertionError(f"grid mismatch {len(D)} != {EXPECTED_GRID}")
    D.to_csv(OUT_GRID, index=False)

    regions, region_cells = build_regions(D)
    regions.to_csv(OUT_REGIONS, index=False)
    reg, frozen = select_frozen(D, regions, region_cells)

    lines = [
        "# ETH R1 H00 — Robust Native Discovery TRAIN Result", "",
        "**TRAIN ONLY: 2022-2023. 2024 VALIDATION NOT EVALUATED. OOS 2025+ CLOSED.**", "",
        f"Coverage check from source loader: {coverage:.4%}. Train engine was hard-sliced to timestamps before 2024-01-01.",
        f"Frozen coarse grid: {len(LOOKBACKS)} lookbacks x {len(HOLDS)} holds x {len(e12.RULES)} rules = **{len(D):,} cells**.",
        f"Strict train cells: **{int(D.strict_gate.sum())}**; strict+temporal: **{int(D.strict_temporal.sum())}**; plateau-supportive cells: **{int(D.plateau_supportive.sum())}**.",
        f"Qualifying robust regions: **{int(regions.qualifies.sum()) if len(regions) else 0}**.", "",
    ]

    if frozen is None:
        status = "ETH_R1_H00_NO_ROBUST_TRAIN_REGION"
        OUT_STATUS.write_text(status + "\n")
        if OUT_LOCK.exists():
            OUT_LOCK.unlink()
        lines += ["## Verdict", "", "**NO_ROBUST_TRAIN_REGION**", "", "2024 remains unopened for this hour; no validation candidate exists."]
    else:
        lock = pd.DataFrame([{
            "hour_wib": HOUR_WIB,
            "region_id": int(reg.region_id),
            "character_rule": str(frozen.character_rule),
            "lookback_min": int(frozen.lookback_min),
            "hold_min": int(frozen.hold_min),
            "train_trades": int(frozen.trades),
            "train_wr": float(frozen.win_rate),
            "train_net": float(frozen.net_pnl),
            "train_exp": float(frozen.expectancy),
            "train_pf": float(frozen.pf),
            "train_dd": float(frozen.max_dd),
            "train_ls": int(frozen.max_loss_streak),
            "positive_halves": int(frozen.positive_halves),
            "min_half_exp": float(frozen.min_half_exp),
            "region_cells": int(reg.cells),
            "region_strict_temporal_cells": int(reg.strict_temporal_cells),
            "region_median_exp": float(reg.median_expectancy),
            "region_median_pf": float(reg.median_pf),
            "region_median_dd": float(reg.median_max_dd),
            "validation_opened": False,
        }])
        lock.to_csv(OUT_LOCK, index=False)
        status = "ETH_R1_H00_TRAIN_CANDIDATE_FROZEN"
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "## Frozen candidate selected from TRAIN only", "",
            f"Region **{int(reg.region_id)}**, rule **{frozen.character_rule}**.",
            f"Frozen representative: **LB{int(frozen.lookback_min)} / H{int(frozen.hold_min)}**.",
            f"Train N {int(frozen.trades)}, WR {pct(frozen.win_rate)}, net {money(frozen.net_pnl)}, exp {money(frozen.expectancy)}, PF {float(frozen.pf):.3f}, DD {money(frozen.max_dd)}, LS {int(frozen.max_loss_streak)}.",
            f"Temporal: {int(frozen.positive_halves)}/4 positive half-years; minimum half-year expectancy {money(frozen.min_half_exp)}.",
            f"Region: {int(reg.cells)} supportive cells, {int(reg.strict_temporal_cells)} strict+temporal cells, median exp {money(reg.median_expectancy)}, median PF {float(reg.median_pf):.3f}.", "",
            "**Candidate is now frozen. The next stage may evaluate this exact candidate once on 2024; no alternate candidate is allowed if it fails.**",
        ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
