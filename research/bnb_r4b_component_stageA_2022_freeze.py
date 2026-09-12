#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
OUT_CELLS = ROOT / "BNB_R4B_STAGEA_2022_ALL_CELLS.csv"
OUT_ALL = ROOT / "BNB_R4B_STAGEA_2022_ALL_COMPONENTS.csv"
OUT_COMPONENTS = ROOT / "BNB_R4B_STAGEA_2022_FROZEN_COMPONENTS.csv"
OUT_FROZEN_CELLS = ROOT / "BNB_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
OUT_RESULT = ROOT / "BNB_R4B_STAGEA_2022_COMPONENT_FREEZE.md"
OUT_STATUS = ROOT / "BNB_R4B_STAGEA_2022_Status.txt"

START = pd.Timestamp("2022-01-01", tz="UTC")
MID = pd.Timestamp("2022-07-01", tz="UTC")
END = pd.Timestamp("2023-01-01", tz="UTC")

LOOKBACKS = [30, 60, 120, 180, 240, 360]
HOLDS = [240, 360, 480, 720, 960]
NOTIONAL = 500.0
FEE = 0.75
RULES = tuple(engine.RULES)


def finite(x):
    return bool(np.isfinite(x))


def stats(net, gross):
    return engine.summarize(np.asarray(net, float), np.asarray(gross, float))


def hour_clocks(hour_wib: int) -> tuple[int, int, int, int]:
    utc_hour = (int(hour_wib) - 7) % 24
    b = utc_hour * 60
    return (b, b + 15, b + 30, b + 45)


def score_cell(cache, clocks, lb: int, hold: int, rule: str) -> dict:
    pooled = []
    positive_anchors = 0
    anchor_ns = []
    anchor_exps = []
    anchor_pfs = []

    for clock in clocks:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        m = valid & (ent >= START) & (ex < END) & masks[rule]
        gross = NOTIONAL * np.asarray(delta, float)[m]
        net = gross - FEE
        ts = ent[m]
        s = stats(net, gross)
        anchor_ns.append(int(s["trades"]))
        anchor_exps.append(float(s["expectancy"]) if finite(s["expectancy"]) else np.nan)
        anchor_pfs.append(float(s["pf"]) if finite(s["pf"]) else np.nan)
        if s["trades"] > 0 and finite(s["expectancy"]) and s["expectancy"] > 0 and finite(s["pf"]) and s["pf"] > 1:
            positive_anchors += 1
        if len(net):
            pooled.append(pd.DataFrame({"entry_ts": ts, "gross": gross, "net": net, "clock": int(clock)}))

    if pooled:
        T = pd.concat(pooled, ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        ps = stats(T.net.to_numpy(float), T.gross.to_numpy(float))
    else:
        T = pd.DataFrame(columns=["entry_ts", "gross", "net", "clock"])
        ps = stats([], [])

    if len(T):
        idx = pd.DatetimeIndex(T.entry_ts)
        m1 = idx < MID
        m2 = idx >= MID
        h1 = stats(T.loc[m1, "net"].to_numpy(float), T.loc[m1, "gross"].to_numpy(float))
        h2 = stats(T.loc[m2, "net"].to_numpy(float), T.loc[m2, "gross"].to_numpy(float))
    else:
        h1 = stats([], [])
        h2 = stats([], [])

    min_half_exp = min(
        float(h1["expectancy"]) if finite(h1["expectancy"]) else -np.inf,
        float(h2["expectancy"]) if finite(h2["expectancy"]) else -np.inf,
    )

    eligible = bool(
        ps["trades"] >= 50
        and finite(ps["win_rate"]) and ps["win_rate"] >= .52
        and ps["net_pnl"] > 0
        and finite(ps["expectancy"]) and ps["expectancy"] > 0
        and finite(ps["pf"]) and ps["pf"] >= 1.15
        and finite(ps["max_dd"]) and ps["max_dd"] <= 160.0
        and positive_anchors >= 2
        and finite(h1["expectancy"]) and h1["expectancy"] > 0
        and finite(h1["pf"]) and h1["pf"] > 1
        and finite(h2["expectancy"]) and h2["expectancy"] > 0
        and finite(h2["pf"]) and h2["pf"] > 1
    )

    row = {
        "lookback_min": int(lb),
        "hold_min": int(hold),
        "character_rule": str(rule),
        "trades": int(ps["trades"]),
        "wr": float(ps["win_rate"]) if finite(ps["win_rate"]) else np.nan,
        "net": float(ps["net_pnl"]),
        "exp": float(ps["expectancy"]) if finite(ps["expectancy"]) else np.nan,
        "pf": float(ps["pf"]) if finite(ps["pf"]) else np.nan,
        "dd": float(ps["max_dd"]) if finite(ps["max_dd"]) else np.nan,
        "ls": int(ps["max_loss_streak"]),
        "positive_anchors": int(positive_anchors),
        "H1_n": int(h1["trades"]),
        "H1_wr": float(h1["win_rate"]) if finite(h1["win_rate"]) else np.nan,
        "H1_exp": float(h1["expectancy"]) if finite(h1["expectancy"]) else np.nan,
        "H1_pf": float(h1["pf"]) if finite(h1["pf"]) else np.nan,
        "H2_n": int(h2["trades"]),
        "H2_wr": float(h2["win_rate"]) if finite(h2["win_rate"]) else np.nan,
        "H2_exp": float(h2["expectancy"]) if finite(h2["expectancy"]) else np.nan,
        "H2_pf": float(h2["pf"]) if finite(h2["pf"]) else np.nan,
        "min_half_exp": float(min_half_exp),
        "economic_support": bool(eligible),
    }
    for i, clock in enumerate(clocks):
        row[f"a{clock}_n"] = anchor_ns[i]
        row[f"a{clock}_exp"] = anchor_exps[i]
        row[f"a{clock}_pf"] = anchor_pfs[i]
    return row


def connected_components(coords: set[tuple[int, int]], li: dict[int, int], hi: dict[int, int]):
    unseen = set(coords)
    out = []
    while unseen:
        seed = min(unseen, key=lambda z: (hi[z[1]], li[z[0]], z[0], z[1]))
        q = deque([seed])
        unseen.remove(seed)
        comp = {seed}
        while q:
            lb, hold = q.popleft()
            i, j = li[lb], hi[hold]
            nbrs = []
            for nlb, nhold in unseen:
                if abs(li[nlb] - i) + abs(hi[nhold] - j) == 1:
                    nbrs.append((nlb, nhold))
            for n in nbrs:
                unseen.remove(n)
                comp.add(n)
                q.append(n)
        out.append(sorted(comp, key=lambda z: (hi[z[1]], li[z[0]], z[0], z[1])))
    return out


def rank_components(d: pd.DataFrame) -> pd.DataFrame:
    return d.sort_values(
        [
            "component_size", "halo_economic_support_count", "halo_economic_support_ratio",
            "component_min_half_exp_floor", "component_exp_floor", "component_exp_mean",
            "component_pf_median", "component_dd_max", "character_rule", "min_hold", "min_lb",
        ],
        ascending=[False, False, False, False, False, False, False, True, True, True, True],
        kind="mergesort",
    )


def main():
    if len(RULES) != 90:
        raise AssertionError(f"expected 90 rules, got {len(RULES)}")

    base.synthetic_tests()
    x5, coverage = base.load5("BNBUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if not bool((idx >= START).any()):
        raise RuntimeError("dataset contains no 2022 bars")
    if idx.max() < pd.Timestamp("2022-12-31 23:55:00", tz="UTC"):
        raise RuntimeError(f"2022 dataset incomplete; max timestamp is {idx.max()}")

    # Retain any pre-2022 history for causal warm-up; never expose 2023+ in Stage A features.
    x = x5[idx < END].copy()
    li = {v: i for i, v in enumerate(LOOKBACKS)}
    hi = {v: i for i, v in enumerate(HOLDS)}

    all_cell_frames = []
    all_summaries = []
    cell_lookup = {}

    for hour in range(24):
        clocks = hour_clocks(hour)
        engine.CLOCKS = clocks
        engine.LOOKBACKS = tuple(LOOKBACKS)
        engine.HOLDS = tuple(HOLDS)
        cache = engine.prep(x)

        rows = []
        for lb in LOOKBACKS:
            for hold in HOLDS:
                for rule in RULES:
                    r = score_cell(cache, clocks, lb, hold, rule)
                    r["hour_wib"] = int(hour)
                    rows.append(r)
        D = pd.DataFrame(rows)
        if len(D) != 2700:
            raise AssertionError(f"H{hour:02d}: expected 2700 cells, got {len(D)}")
        all_cell_frames.append(D)

        for rule, G in D.groupby(D.character_rule.astype(str), sort=True):
            E = G[G.economic_support].copy()
            if E.empty:
                continue
            coords = {(int(r.lookback_min), int(r.hold_min)) for r in E.itertuples(index=False)}
            comps = connected_components(coords, li, hi)
            for raw_id, comp in enumerate(comps, start=1):
                comp_set = set(comp)
                C = E[E.apply(lambda z: (int(z.lookback_min), int(z.hold_min)) in comp_set, axis=1)].copy()
                halo_coords = set()
                for r in G.itertuples(index=False):
                    pt = (int(r.lookback_min), int(r.hold_min))
                    if min(abs(li[pt[0]] - li[c[0]]) + abs(hi[pt[1]] - hi[c[1]]) for c in comp) <= 1:
                        halo_coords.add(pt)
                H = G[G.apply(lambda z: (int(z.lookback_min), int(z.hold_min)) in halo_coords, axis=1)].copy()
                econ_h = H[H.economic_support].copy()
                summary = {
                    "hour_wib": int(hour),
                    "character_rule": str(rule),
                    "raw_component_id": int(raw_id),
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
                    "component_ls_max": int(C.ls.max()),
                    "min_lb": min(c[0] for c in comp),
                    "max_lb": max(c[0] for c in comp),
                    "min_hold": min(c[1] for c in comp),
                    "max_hold": max(c[1] for c in comp),
                    "component_cells": ";".join(f"LB{lb}/H{hold}" for lb, hold in comp),
                }
                all_summaries.append(summary)
                cell_lookup[(hour, str(rule), raw_id)] = C.copy()

    CELLS = pd.concat(all_cell_frames, ignore_index=True)
    if len(CELLS) != 64800:
        raise AssertionError(f"expected 64800 total cells, got {len(CELLS)}")
    CELLS = CELLS.sort_values(["hour_wib", "character_rule", "hold_min", "lookback_min"]).reset_index(drop=True)
    CELLS.to_csv(OUT_CELLS, index=False)

    ALL = pd.DataFrame(all_summaries)
    if ALL.empty:
        raise AssertionError("no connected economic components found")
    ALL = ALL.sort_values(["hour_wib", "character_rule", "raw_component_id"]).reset_index(drop=True)
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
                    "hour_wib": int(hour),
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
                    "dev_positive_anchors": int(cr.positive_anchors),
                    "dev_H1_n": int(cr.H1_n),
                    "dev_H1_wr": float(cr.H1_wr),
                    "dev_H1_exp": float(cr.H1_exp),
                    "dev_H1_pf": float(cr.H1_pf),
                    "dev_H2_n": int(cr.H2_n),
                    "dev_H2_wr": float(cr.H2_wr),
                    "dev_H2_exp": float(cr.H2_exp),
                    "dev_H2_pf": float(cr.H2_pf),
                    "dev_min_half_exp": float(cr.min_half_exp),
                })

    F = pd.DataFrame(frozen_summaries).sort_values(["hour_wib", "component_rank"]).reset_index(drop=True)
    FC = pd.DataFrame(frozen_cells).sort_values(["hour_wib", "component_rank", "hold_min", "lookback_min"]).reset_index(drop=True)
    F.to_csv(OUT_COMPONENTS, index=False)
    FC.to_csv(OUT_FROZEN_CELLS, index=False)

    if F.hour_wib.nunique() != 24:
        missing = sorted(set(range(24)) - set(F.hour_wib.astype(int).unique()))
        raise AssertionError(f"no frozen component for WIB hours: {missing}")

    lines = [
        "# BNB R4b — Stage A 2022 Connected-Component Freeze", "",
        "**2022 ONLY. COMPONENTS FROZEN BEFORE 2023. 2023-2026 CLOSED.**", "",
        f"Raw BNBUSDT 5m coverage: **{coverage:.4%}**.",
        f"Raw Stage-A search cells: **{len(CELLS):,}** across 24 WIB hours.",
        f"Economic-support cells: **{int(CELLS.economic_support.sum()):,}**.",
        f"Connected components discovered: **{len(ALL):,}**.",
        f"Frozen components: **{len(F)}** across 24 WIB hours; frozen member cells: **{len(FC)}**.", "",
        "| Hour | Rank | Character | Size | Timing cells | Halo support | WR min/mean | Exp floor/mean | Half-exp floor | PF med | DD max | LS max |",
        "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in F.itertuples(index=False):
        lines.append(
            f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {r.component_cells} | "
            f"{int(r.halo_economic_support_count)}/{int(r.halo_cell_count)} | "
            f"{100*float(r.component_wr_min):.2f}%/{100*float(r.component_wr_mean):.2f}% | "
            f"${float(r.component_exp_floor):+.2f}/${float(r.component_exp_mean):+.2f} | "
            f"${float(r.component_min_half_exp_floor):+.2f} | {float(r.component_pf_median):.3f} | "
            f"${float(r.component_dd_max):.2f} | {int(r.component_ls_max)} |"
        )

    lines += [
        "",
        "The frozen unit is the connected BNB economic plateau, not a post-hoc best coordinate.",
        "Loss streak is retained as a risk-clustering diagnostic and was not a Stage-A hard rejection gate.",
        "B27/B28 outcomes did not seed or rank this search.",
        "Component membership is now immutable for Stage B; no cell may be added or removed after 2023 is inspected.",
        "2023-2026 remain unopened in this Stage-A run.",
        "",
        "**Status: BNB_R4B_2022_COMPONENTS_FROZEN**",
        "",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("BNB_R4B_2022_COMPONENTS_FROZEN\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
