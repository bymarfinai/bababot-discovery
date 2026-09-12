#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as legacy

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_R4B_STAGEA"
OUT_GRID = ROOT / f"{PFX}_2022_DevGrid.csv"
OUT_ALL_COMPONENTS = ROOT / f"{PFX}_2022_ALL_COMPONENTS.csv"
OUT_FROZEN = ROOT / f"{PFX}_2022_FROZEN_COMPONENTS.csv"
OUT_RESULT = ROOT / f"{PFX}_2022_COMPONENT_FREEZE.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

LOOKBACKS = (60, 120, 180, 240, 360)
HOLDS = (120, 240, 360, 480)
HOURS_WIB = range(24)
START = pd.Timestamp("2022-01-01", tz="UTC")
MID = pd.Timestamp("2022-07-01", tz="UTC")
END = pd.Timestamp("2023-01-01", tz="UTC")
MIN_COMPONENT_SIZE = 2
MAX_COMPONENTS_PER_HOUR = 3


def finite(x) -> bool:
    return bool(np.isfinite(x))


def clocks_for_hour(h: int) -> tuple[int, int, int, int]:
    base = ((int(h) - 7) % 24) * 60
    return tuple((base + q) % 1440 for q in (0, 15, 30, 45))


def stats(T: pd.DataFrame) -> dict:
    if len(T) == 0:
        return legacy.summarize(np.array([]), np.array([]))
    return legacy.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def period_stats(T: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    if len(T) == 0:
        return stats(T)
    ent = pd.DatetimeIndex(pd.to_datetime(T.entry_ts, utc=True))
    ex = pd.DatetimeIndex(pd.to_datetime(T.exit_ts, utc=True))
    return stats(T.loc[(ent >= start) & (ex < end)])


def anchor_positive(T: pd.DataFrame, clock: int) -> bool:
    s = stats(T[T.clock == int(clock)])
    return bool(
        s["trades"] >= 12 and finite(s["expectancy"]) and s["expectancy"] > 0 and
        finite(s["pf"]) and s["pf"] > 1
    )


def prepare_hour(x5: pd.DataFrame, hour_wib: int) -> dict:
    cache = {}
    for lb in LOOKBACKS:
        for clock in clocks_for_hour(hour_wib):
            frame = legacy.state_frame(x5, int(clock), int(lb))
            masks = legacy.masks_for_frame(frame)
            entry_ts = pd.DatetimeIndex(pd.to_datetime(frame.entry_ts, utc=True))
            pre_ts = pd.DatetimeIndex(pd.to_datetime(frame.pre_ts, utc=True))
            for hold in HOLDS:
                exit_ts, valid, returns = legacy.hold_returns(x5, frame, int(hold))
                cache[(int(clock), int(lb), int(hold))] = (
                    entry_ts, pre_ts, pd.DatetimeIndex(pd.to_datetime(exit_ts, utc=True)),
                    np.asarray(valid, bool), np.asarray(returns, float), masks,
                )
    return cache


def candidate_events(cache: dict, hour_wib: int, lb: int, hold: int, rule: str) -> pd.DataFrame:
    rows = []
    for clock in clocks_for_hour(hour_wib):
        ent, pre, ex, valid, returns, masks = cache[(int(clock), int(lb), int(hold))]
        m = valid & (pre >= START) & (ent >= START) & (ex < END) & np.asarray(masks[str(rule)], bool)
        gross = legacy.NOTIONAL * returns[m]
        net = gross - legacy.FEE
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


def eval_cell(cache: dict, hour_wib: int, lb: int, hold: int, rule: str) -> dict:
    T = candidate_events(cache, hour_wib, lb, hold, rule)
    s = stats(T)
    h1 = period_stats(T, START, MID)
    h2 = period_stats(T, MID, END)
    pos_a = sum(int(anchor_positive(T, c)) for c in clocks_for_hour(hour_wib))
    halves_ok = bool(
        h1["trades"] > 0 and h2["trades"] > 0 and
        finite(h1["expectancy"]) and h1["expectancy"] > 0 and finite(h1["pf"]) and h1["pf"] > 1 and
        finite(h2["expectancy"]) and h2["expectancy"] > 0 and finite(h2["pf"]) and h2["pf"] > 1
    )
    eligible = bool(
        s["trades"] >= 60 and finite(s["win_rate"]) and s["win_rate"] >= .55 and
        s["net_pnl"] > 0 and finite(s["expectancy"]) and s["expectancy"] >= .50 and
        finite(s["pf"]) and s["pf"] >= 1.20 and finite(s["max_dd"]) and s["max_dd"] <= 125 and
        halves_ok and pos_a >= 2
    )
    min_half_exp = min(float(h1["expectancy"]), float(h2["expectancy"])) if finite(h1["expectancy"]) and finite(h2["expectancy"]) else -np.inf
    return {
        "hour_wib": int(hour_wib),
        "character_rule": str(rule),
        "lookback_min": int(lb),
        "hold_min": int(hold),
        "trades": int(s["trades"]),
        "wr": float(s["win_rate"]) if finite(s["win_rate"]) else np.nan,
        "net": float(s["net_pnl"]),
        "exp": float(s["expectancy"]) if finite(s["expectancy"]) else np.nan,
        "pf": float(s["pf"]) if finite(s["pf"]) else np.nan,
        "dd": float(s["max_dd"]) if finite(s["max_dd"]) else np.nan,
        "ls": int(s["max_loss_streak"]),
        "H1_trades": int(h1["trades"]),
        "H1_exp": float(h1["expectancy"]) if finite(h1["expectancy"]) else np.nan,
        "H1_pf": float(h1["pf"]) if finite(h1["pf"]) else np.nan,
        "H2_trades": int(h2["trades"]),
        "H2_exp": float(h2["expectancy"]) if finite(h2["expectancy"]) else np.nan,
        "H2_pf": float(h2["pf"]) if finite(h2["pf"]) else np.nan,
        "min_half_exp": float(min_half_exp),
        "positive_anchors": int(pos_a),
        "dev_eligible": bool(eligible),
    }


def halo_supportive(r: pd.Series) -> bool:
    return bool(
        int(r.trades) >= 55 and finite(r.wr) and float(r.wr) >= .52 and
        float(r.net) > 0 and finite(r.exp) and float(r.exp) > 0 and
        finite(r.pf) and float(r.pf) >= 1.10 and finite(r.dd) and float(r.dd) <= 160 and
        int(r.ls) <= 12 and finite(r.H1_exp) and float(r.H1_exp) > 0 and
        finite(r.H2_exp) and float(r.H2_exp) > 0 and finite(r.min_half_exp) and float(r.min_half_exp) > 0 and
        int(r.positive_anchors) >= 2
    )


def connected_components(coords: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    remaining = set(coords)
    comps = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        comp = {seed}
        while stack:
            i, j = stack.pop()
            for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if n in remaining:
                    remaining.remove(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def cell_label(lb: int, hold: int) -> str:
    return f"LB{int(lb)}/H{int(hold)}"


def build_components(D: pd.DataFrame) -> pd.DataFrame:
    li = {v:i for i,v in enumerate(LOOKBACKS)}
    hi = {v:i for i,v in enumerate(HOLDS)}
    inv_l = {i:v for v,i in li.items()}
    inv_h = {i:v for v,i in hi.items()}
    rows = []
    for hour in HOURS_WIB:
        H = D[D.hour_wib == int(hour)]
        for rule in legacy.RULES:
            R = H[(H.character_rule == str(rule)) & H.dev_eligible.astype(bool)]
            coords = {(li[int(r.lookback_min)], hi[int(r.hold_min)]) for r in R.itertuples(index=False)}
            for comp in connected_components(coords):
                if len(comp) < MIN_COMPONENT_SIZE:
                    continue
                labels = sorted((inv_l[i], inv_h[j]) for i,j in comp)
                C = R[R.apply(lambda r: (li[int(r.lookback_min)], hi[int(r.hold_min)]) in comp, axis=1)].copy()
                halo_coords = set()
                for i,j in comp:
                    for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                        if n in comp:
                            continue
                        if n[0] in inv_l and n[1] in inv_h:
                            halo_coords.add(n)
                positive_halo = 0
                for i,j in halo_coords:
                    q = H[(H.character_rule == str(rule)) & (H.lookback_min == inv_l[i]) & (H.hold_min == inv_h[j])]
                    if len(q) == 1 and halo_supportive(q.iloc[0]):
                        positive_halo += 1
                exps = C.exp.to_numpy(float)
                pfs = C.pf.to_numpy(float)
                dds = C.dd.to_numpy(float)
                rows.append({
                    "hour_wib": int(hour),
                    "character_rule": str(rule),
                    "component_size": int(len(comp)),
                    "component_cells": ";".join(cell_label(lb,h) for lb,h in labels),
                    "positive_halo": int(positive_halo),
                    "positive_exp_cells": int(np.sum(np.isfinite(exps) & (exps > 0))),
                    "wr_min": float(C.wr.min()),
                    "wr_mean": float(C.wr.mean()),
                    "exp_floor": float(np.nanmin(exps)),
                    "exp_mean": float(np.nanmean(exps)),
                    "pf_median": float(np.nanmedian(pfs)),
                    "dd_max": float(np.nanmax(dds)),
                    "ls_max": int(C.ls.max()),
                })
    return pd.DataFrame(rows)


def freeze_top_components(C: pd.DataFrame) -> pd.DataFrame:
    if len(C) == 0:
        return C.copy()
    frozen = []
    for hour in HOURS_WIB:
        H = C[C.hour_wib == int(hour)].copy()
        if len(H) == 0:
            continue
        H = H.sort_values(
            ["component_size", "positive_halo", "positive_exp_cells", "exp_floor", "exp_mean", "character_rule", "component_cells"],
            ascending=[False, False, False, False, False, True, True],
        ).head(MAX_COMPONENTS_PER_HOUR).reset_index(drop=True)
        H["component_rank"] = np.arange(1, len(H)+1)
        frozen.append(H)
    if not frozen:
        return pd.DataFrame(columns=list(C.columns)+["component_rank"])
    return pd.concat(frozen, ignore_index=True)


def main():
    legacy.base.synthetic_tests()
    x5, coverage = legacy.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x = x5[(idx >= START) & (idx < END)].copy()

    rows = []
    for hour in HOURS_WIB:
        print(f"Stage A 2022 H{hour:02d} WIB", flush=True)
        cache = prepare_hour(x, int(hour))
        for rule in legacy.RULES:
            for lb in LOOKBACKS:
                for hold in HOLDS:
                    rows.append(eval_cell(cache, int(hour), int(lb), int(hold), str(rule)))

    D = pd.DataFrame(rows)
    expected = 24 * len(legacy.RULES) * len(LOOKBACKS) * len(HOLDS)
    if len(D) != expected:
        raise AssertionError(f"expected {expected} grid cells, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)

    C = build_components(D)
    C.to_csv(OUT_ALL_COMPONENTS, index=False)
    F = freeze_top_components(C)
    F.to_csv(OUT_FROZEN, index=False)

    eligible = int(D.dev_eligible.astype(bool).sum())
    ncomp = int(len(C))
    nfrozen = int(len(F))
    nhours = int(F.hour_wib.nunique()) if len(F) else 0

    lines = [
        "# SOL R4b — Stage A 2022 Connected-Component Freeze", "",
        "**2022 ONLY. 2023-2026 were not evaluated by this Stage-A engine.**", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Grid evaluated: **{len(D):,}** cells = 24 WIB hours × 90 characters × 5 lookbacks × 4 holds.",
        f"Strict-eligible 2022 cells: **{eligible:,}**.",
        f"Connected components with size >=2: **{ncomp:,}**.",
        f"Frozen top components: **{nfrozen:,}** across **{nhours}** WIB hours.", "",
        "Stage-A strict eligibility includes positive economics in both 2022 halves and at least two positive quarter-hour anchors. Maximum loss streak is diagnostic only for strict membership, matching ETH R4b.", "",
        "## Frozen components", "",
        "| Hour WIB | Rank | Character | Size | Timing cells | Halo | WR min/mean | Exp floor/mean | PF median | DD max |",
        "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    if len(F):
        for r in F.sort_values(["hour_wib","component_rank"]).itertuples(index=False):
            lines.append(
                f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | `{r.character_rule}` | {int(r.component_size)} | "
                f"{r.component_cells} | {int(r.positive_halo)} | {100*float(r.wr_min):.2f}%/{100*float(r.wr_mean):.2f}% | "
                f"${float(r.exp_floor):+.2f}/${float(r.exp_mean):+.2f} | {float(r.pf_median):.3f} | ${float(r.dd_max):.2f} |"
            )
        status = "SOL_R4B_STAGEA_2022_COMPONENTS_FROZEN"
    else:
        lines += ["| - | - | - | - | - | - | - | - | - | - |", "", "**No valid connected plateau was found. R4b stops before 2023.**"]
        status = "SOL_R4B_STAGEA_NO_CONNECTED_PLATEAU"
    lines += ["", "Component membership and ranking are now frozen. No 2023 information influenced this result."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(status+"\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
