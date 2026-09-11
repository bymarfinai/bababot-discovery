#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ROBUSTNESS_FIRST_V2"
OUT_GRID = ROOT / f"{PFX}_Grid.csv"
OUT_PASSERS = ROOT / f"{PFX}_Passers.csv"
OUT_TOP = ROOT / f"{PFX}_Top50.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

RESEARCH_START = pd.Timestamp("2022-01-01", tz="UTC")
RESEARCH_END = pd.Timestamp("2026-07-30", tz="UTC")
YEARS = (2022, 2023, 2024, 2025, 2026)
LOOKBACKS = tuple(engine.LOOKBACKS)
HOLDS = tuple(engine.HOLDS)
RULES = tuple(engine.RULES)
NOTIONAL = float(engine.NOTIONAL)
FEE = float(engine.FEE)

# Hard performance gate.
POOL_N_MIN = 250
POOL_WR_MIN = 0.60
POOL_EXP_MIN = 1.50
POOL_PF_MIN = 1.70
POOL_DD_MAX = 175.0
POOL_LOSS_STREAK_MAX = 8

# Chronological fold gate.
YEAR_N_MIN = 20
YEAR_WR_MIN = 0.55
YEAR_PF_MIN = 1.15
YEARS_WR60_MIN = 3

# Anchor gate.
ANCHOR_N_MIN = 25
ANCHOR_WR_MIN = 0.55
ANCHOR_EXP_MIN = 0.0
ANCHOR_PF_MIN = 1.20
ANCHOR_DD_MAX = 150.0
ANCHOR_LOSS_STREAK_MAX = 10

# Overlap-adjusted effective N.
EFF_N_MIN = 100
EFF_RATIO_MIN = 0.35

# Immediate parameter-neighborhood gate.
NEIGH_WR_MIN = 0.56
NEIGH_EXP_MIN = 0.50
NEIGH_PF_MIN = 1.25
NEIGH_POSITIVE_YEARS_MIN = 4
NEIGH_SUPPORT_MIN = 2


def money(v: float) -> str:
    return "nan" if not np.isfinite(v) else f"${v:+.2f}"


def pct(v: float) -> str:
    return "nan" if not np.isfinite(v) else f"{100.0 * v:.2f}%"


def hour_wib(hour: int) -> str:
    a = (hour + 7) % 24
    b = (a + 1) % 24
    return f"{a:02d}:00-{b:02d}:00"


def hourly_clocks(hour: int) -> tuple[int, int, int, int]:
    base = hour * 60
    return (base, base + 15, base + 30, base + 45)


def exposure_cluster_count(trades: pd.DataFrame) -> int:
    if len(trades) == 0:
        return 0
    q = trades.sort_values(["entry_ts", "exit_ts"]).reset_index(drop=True)
    clusters = 0
    cluster_end = None
    for entry, exit_ in zip(q.entry_ts, q.exit_ts):
        if cluster_end is None or entry >= cluster_end:
            clusters += 1
            cluster_end = exit_
        elif exit_ > cluster_end:
            cluster_end = exit_
    return int(clusters)


def year_bounds(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(f"{year}-01-01", tz="UTC")
    end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
    if year == 2026:
        end = RESEARCH_END
    return start, end


def empty_stats() -> dict:
    return engine.summarize(np.array([], float), np.array([], float))


def build_hour_cache(x5: pd.DataFrame, hour: int) -> dict:
    cache: dict = {}
    clocks = hourly_clocks(hour)
    for lookback in LOOKBACKS:
        for clock in clocks:
            frame = engine.state_frame(x5, clock, lookback)
            entry_ts = pd.DatetimeIndex(frame.entry_ts)
            pre_ts = pd.DatetimeIndex(frame.pre_ts)
            masks = engine.masks_for_frame(frame)
            for hold in HOLDS:
                exit_ts, valid, returns = engine.hold_returns(x5, frame, hold)
                cache[(clock, lookback, hold)] = (
                    entry_ts,
                    pre_ts,
                    pd.DatetimeIndex(exit_ts),
                    valid,
                    returns,
                    masks,
                )
    return cache


def eval_candidate(cache: dict, hour: int, lookback: int, hold: int, rule: str) -> dict:
    anchor_rows = []
    pooled_frames = []

    for clock in hourly_clocks(hour):
        entry_ts, pre_ts, exit_ts, valid, returns, masks = cache[(clock, lookback, hold)]
        selected = (
            valid
            & (pre_ts >= RESEARCH_START)
            & (entry_ts >= RESEARCH_START)
            & (exit_ts < RESEARCH_END)
            & masks[rule]
        )
        gross = NOTIONAL * returns[selected]
        net = gross - FEE
        stats = engine.summarize(net, gross)
        evaluable = stats["trades"] >= ANCHOR_N_MIN
        supportive = bool(
            evaluable
            and stats["win_rate"] >= ANCHOR_WR_MIN
            and stats["net_pnl"] > 0
            and stats["expectancy"] > ANCHOR_EXP_MIN
            and stats["pf"] >= ANCHOR_PF_MIN
            and stats["max_dd"] <= ANCHOR_DD_MAX
            and stats["max_loss_streak"] <= ANCHOR_LOSS_STREAK_MAX
        )
        anchor_rows.append((clock, stats, evaluable, supportive))
        if len(net):
            pooled_frames.append(pd.DataFrame({
                "pre_ts": pre_ts[selected],
                "entry_ts": entry_ts[selected],
                "exit_ts": exit_ts[selected],
                "clock": clock,
                "gross": gross,
                "net": net,
            }))

    if pooled_frames:
        trades = pd.concat(pooled_frames, ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        pooled = engine.summarize(trades.net.to_numpy(float), trades.gross.to_numpy(float))
    else:
        trades = pd.DataFrame(columns=["pre_ts", "entry_ts", "exit_ts", "clock", "gross", "net"])
        pooled = empty_stats()

    row = {
        "hour_utc": hour,
        "hour_wib": hour_wib(hour),
        "character_rule": rule,
        "lookback_min": lookback,
        "hold_min": hold,
        **pooled,
        "evaluable_anchors": int(sum(x[2] for x in anchor_rows)),
        "supportive_anchors": int(sum(x[3] for x in anchor_rows)),
    }

    for clock, stats, evaluable, supportive in anchor_rows:
        suffix = f"a{clock % 1440:04d}"
        row[f"{suffix}_n"] = stats["trades"]
        row[f"{suffix}_wr"] = stats["win_rate"]
        row[f"{suffix}_exp"] = stats["expectancy"]
        row[f"{suffix}_pf"] = stats["pf"]
        row[f"{suffix}_dd"] = stats["max_dd"]
        row[f"{suffix}_evaluable"] = bool(evaluable)
        row[f"{suffix}_supportive"] = bool(supportive)

    years_wr60 = 0
    all_years_pass = True
    positive_year_exp = 0
    for year in YEARS:
        ys, ye = year_bounds(year)
        q = trades[(trades.pre_ts >= ys) & (trades.entry_ts >= ys) & (trades.exit_ts < ye)]
        stats = engine.summarize(q.net.to_numpy(float), q.gross.to_numpy(float)) if len(q) else empty_stats()
        basic = bool(
            stats["trades"] >= YEAR_N_MIN
            and stats["win_rate"] >= YEAR_WR_MIN
            and stats["net_pnl"] > 0
            and stats["expectancy"] > 0
            and stats["pf"] >= YEAR_PF_MIN
        )
        if stats["expectancy"] > 0:
            positive_year_exp += 1
        if stats["win_rate"] >= 0.60:
            years_wr60 += 1
        all_years_pass = all_years_pass and basic
        row[f"y{year}_n"] = stats["trades"]
        row[f"y{year}_wr"] = stats["win_rate"]
        row[f"y{year}_net"] = stats["net_pnl"]
        row[f"y{year}_exp"] = stats["expectancy"]
        row[f"y{year}_pf"] = stats["pf"]
        row[f"y{year}_dd"] = stats["max_dd"]
        row[f"y{year}_pass"] = basic

    eff_n = exposure_cluster_count(trades)
    eff_ratio = (eff_n / pooled["trades"]) if pooled["trades"] else 0.0

    anchor_gate = bool(row["evaluable_anchors"] >= 3 and row["supportive_anchors"] >= 3)
    pooled_gate = bool(
        pooled["trades"] >= POOL_N_MIN
        and pooled["win_rate"] >= POOL_WR_MIN
        and pooled["net_pnl"] > 0
        and pooled["expectancy"] >= POOL_EXP_MIN
        and pooled["pf"] >= POOL_PF_MIN
        and pooled["max_dd"] <= POOL_DD_MAX
        and pooled["max_loss_streak"] <= POOL_LOSS_STREAK_MAX
    )
    era_gate = bool(all_years_pass and years_wr60 >= YEARS_WR60_MIN)
    effn_gate = bool(eff_n >= EFF_N_MIN and eff_ratio >= EFF_RATIO_MIN)

    row.update({
        "positive_year_exp_count": positive_year_exp,
        "years_wr60": years_wr60,
        "effective_n": eff_n,
        "effective_n_ratio": eff_ratio,
        "anchor_gate": anchor_gate,
        "pooled_gate": pooled_gate,
        "era_gate": era_gate,
        "effective_n_gate": effn_gate,
        "pre_neighborhood_gate": bool(anchor_gate and pooled_gate and era_gate and effn_gate),
    })
    return row


def immediate_neighbors(row: pd.Series) -> list[tuple[int, int]]:
    li = LOOKBACKS.index(int(row.lookback_min))
    hi = HOLDS.index(int(row.hold_min))
    out: list[tuple[int, int]] = []
    if li > 0:
        out.append((LOOKBACKS[li - 1], int(row.hold_min)))
    if li + 1 < len(LOOKBACKS):
        out.append((LOOKBACKS[li + 1], int(row.hold_min)))
    if hi > 0:
        out.append((int(row.lookback_min), HOLDS[hi - 1]))
    if hi + 1 < len(HOLDS):
        out.append((int(row.lookback_min), HOLDS[hi + 1]))
    return out


def soft_neighbor(row: pd.Series) -> bool:
    return bool(
        row.win_rate >= NEIGH_WR_MIN
        and row.net_pnl > 0
        and row.expectancy >= NEIGH_EXP_MIN
        and row.pf >= NEIGH_PF_MIN
        and row.positive_year_exp_count >= NEIGH_POSITIVE_YEARS_MIN
    )


def add_neighborhood_gate(grid: pd.DataFrame) -> pd.DataFrame:
    grid = grid.copy()
    grid["available_neighbors"] = 0
    grid["supportive_neighbors"] = 0
    grid["neighborhood_gate"] = False

    lookup = {
        (int(r.hour_utc), str(r.character_rule), int(r.lookback_min), int(r.hold_min)): idx
        for idx, r in grid.iterrows()
    }

    for idx, row in grid.iterrows():
        keys = immediate_neighbors(row)
        available = 0
        supportive = 0
        for lb, hold in keys:
            nidx = lookup.get((int(row.hour_utc), str(row.character_rule), int(lb), int(hold)))
            if nidx is None:
                continue
            available += 1
            if soft_neighbor(grid.loc[nidx]):
                supportive += 1
        grid.at[idx, "available_neighbors"] = available
        grid.at[idx, "supportive_neighbors"] = supportive
        grid.at[idx, "neighborhood_gate"] = bool(available >= 2 and supportive >= NEIGH_SUPPORT_MIN)

    grid["candidate_gate"] = grid.pre_neighborhood_gate & grid.neighborhood_gate
    return grid


def rank_passers(passers: pd.DataFrame) -> pd.DataFrame:
    if len(passers) == 0:
        return passers.copy()
    return passers.sort_values(
        ["win_rate", "expectancy", "pf", "effective_n", "max_dd", "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, True, True, True, True],
    ).reset_index(drop=True)


def render_result(grid: pd.DataFrame, passers: pd.DataFrame, coverage: float) -> str:
    pre = grid[grid.pre_neighborhood_gate].copy()
    top = grid.sort_values(
        ["pre_neighborhood_gate", "win_rate", "expectancy", "pf", "max_dd"],
        ascending=[False, False, False, False, True],
    ).head(20)

    lines = [
        "# SOL Robustness-First Discovery V2 — Result",
        "",
        f"Raw SOLUSDT 5m coverage through 2026-07-30: **{100*coverage:.4f}%**.",
        "August 2026 was not loaded or scored.",
        f"Raw candidate universe: **{len(grid):,}**.",
        f"Pre-neighborhood robust passers: **{len(pre)}**.",
        f"Full robustness-first passers: **{len(passers)}**.",
        "",
        "## Frozen gates",
        "",
        "Pooled: N>=250, WR>=60%, Exp>=+$1.50, PF>=1.70, DD<=$175, loss streak<=8.",
        "Every 2022/2023/2024/2025/2026-YTD fold: N>=20, WR>=55%, positive economics, PF>=1.15; >=3 folds WR>=60%.",
        "Within-hour anchors: >=3 evaluable and >=3 supportive.",
        "Overlap-adjusted effective N: >=100 clusters and ratio>=0.35.",
        "Neighborhood: >=2 immediate LB/hold neighbors meet frozen soft-support thresholds.",
        "",
    ]

    if len(passers):
        winner = passers.iloc[0]
        lines += [
            "## Selected V2 character",
            "",
            f"**H{int(winner.hour_utc):02d} ({winner.hour_wib} WIB) — {winner.character_rule} / LB{int(winner.lookback_min)} / Hold{int(winner.hold_min)}m**",
            "",
            f"N **{int(winner.trades)}**, effective N **{int(winner.effective_n)}** ({100*winner.effective_n_ratio:.1f}% of raw), WR **{pct(winner.win_rate)}**, net **{money(winner.net_pnl)}**, expectancy **{money(winner.expectancy)}/trade**, PF **{winner.pf:.3f}**, DD **{money(winner.max_dd)}**, loss streak **{int(winner.max_loss_streak)}**.",
            f"Anchors **{int(winner.supportive_anchors)}/{int(winner.evaluable_anchors)}** supportive/evaluable; neighbors **{int(winner.supportive_neighbors)}/{int(winner.available_neighbors)}** supportive/available.",
            "",
            "### Chronological folds",
            "",
            "| Year | N | WR | Net | Exp | PF | DD | Gate |",
            "|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for year in YEARS:
            lines.append(
                f"| {year} | {int(winner[f'y{year}_n'])} | {pct(winner[f'y{year}_wr'])} | {money(winner[f'y{year}_net'])} | {money(winner[f'y{year}_exp'])} | {winner[f'y{year}_pf']:.3f} | {money(winner[f'y{year}_dd'])} | {'PASS' if winner[f'y{year}_pass'] else 'FAIL'} |"
            )
        lines += ["", "## All full passers", ""]
        lines += ["| # | Hour WIB | Character | LB | Hold | N | EffN | WR | Exp | PF | DD | Anchors | Neighbors |",
                  "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for i, r in passers.head(50).iterrows():
            lines.append(
                f"| {i+1} | {r.hour_wib} | {r.character_rule} | {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {int(r.effective_n)} | {pct(r.win_rate)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {int(r.supportive_neighbors)}/{int(r.available_neighbors)} |"
            )
        status = "SOL_ROBUSTNESS_FIRST_V2_CHARACTER_FOUND"
    else:
        lines += [
            "## Decision",
            "",
            "No candidate passed all preregistered high-performance and robustness gates. Gates were not relaxed.",
            "",
            "## Strongest diagnostics",
            "",
            "| Hour WIB | Character | LB | Hold | N | EffN | WR | Exp | PF | DD | Anchor | Era | EffN | Neigh |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
        ]
        for _, r in top.iterrows():
            lines.append(
                f"| {r.hour_wib} | {r.character_rule} | {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {int(r.effective_n)} | {pct(r.win_rate)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {'PASS' if r.anchor_gate else 'FAIL'} | {'PASS' if r.era_gate else 'FAIL'} | {'PASS' if r.effective_n_gate else 'FAIL'} | {'PASS' if r.neighborhood_gate else 'FAIL'} |"
            )
        status = "SOL_ROBUSTNESS_FIRST_V2_NO_CHARACTER"

    lines += [
        "",
        f"**Status: {status}**",
        "",
        "Research/shadow only. August 2026 remains unopened for a separately preregistered holdout.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    # Hard cut the shared loader before any download. August 2026 is not loaded.
    engine.base.END = RESEARCH_END
    x5, coverage = engine.base.load5("SOLUSDT")
    if x5.index.max() >= RESEARCH_END:
        raise AssertionError("research loader crossed frozen end")

    rows = []
    for hour in range(24):
        print(f"scanning H{hour:02d} {hour_wib(hour)} WIB", flush=True)
        cache = build_hour_cache(x5, hour)
        for lookback in LOOKBACKS:
            for hold in HOLDS:
                for rule in RULES:
                    rows.append(eval_candidate(cache, hour, lookback, hold, rule))

    grid = pd.DataFrame(rows)
    expected = 24 * len(LOOKBACKS) * len(HOLDS) * len(RULES)
    if len(grid) != expected:
        raise AssertionError(f"candidate count mismatch {len(grid)} != {expected}")

    grid = add_neighborhood_gate(grid)
    passers = rank_passers(grid[grid.candidate_gate].copy())
    top = grid.sort_values(
        ["candidate_gate", "pre_neighborhood_gate", "win_rate", "expectancy", "pf", "max_dd"],
        ascending=[False, False, False, False, False, True],
    ).head(50)

    grid.to_csv(OUT_GRID, index=False)
    passers.to_csv(OUT_PASSERS, index=False)
    top.to_csv(OUT_TOP, index=False)

    result = render_result(grid, passers, coverage)
    OUT_RESULT.write_text(result)
    status = "SOL_ROBUSTNESS_FIRST_V2_CHARACTER_FOUND" if len(passers) else "SOL_ROBUSTNESS_FIRST_V2_NO_CHARACTER"
    OUT_STATUS.write_text(status + "\n")
    print(result)


if __name__ == "__main__":
    main()
