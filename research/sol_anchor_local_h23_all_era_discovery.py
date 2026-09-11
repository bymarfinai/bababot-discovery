#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ANCHOR_LOCAL_H23_ALL_ERA_DISCOVERY"
OUT_GRID = ROOT / f"{PFX}_Grid.csv"
OUT_PASSERS = ROOT / f"{PFX}_Passers.csv"
OUT_SELECTED = ROOT / f"{PFX}_Selected.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (1380, 1395, 1410, 1425)  # 23:00 / 23:15 / 23:30 / 23:45 UTC
LOOKBACKS = engine.LOOKBACKS
HOLDS = engine.HOLDS
RULES = engine.RULES
PARTITIONS = ("external", "development", "reference_validation")
DISCOVERY_END = pd.Timestamp("2026-07-30T00:00:00Z")


def era_gate(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 20
        and np.isfinite(stats["win_rate"])
        and stats["win_rate"] >= 0.52
        and stats["net_pnl"] > 0
        and np.isfinite(stats["expectancy"])
        and stats["expectancy"] > 0
        and np.isfinite(stats["pf"])
        and stats["pf"] >= 1.05
        and stats["max_dd"] <= 125
        and stats["max_loss_streak"] <= 8
    )


def combined_gate(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 120
        and np.isfinite(stats["win_rate"])
        and stats["win_rate"] >= 0.55
        and stats["net_pnl"] > 0
        and np.isfinite(stats["expectancy"])
        and stats["expectancy"] >= 1.00
        and np.isfinite(stats["pf"])
        and stats["pf"] >= 1.30
        and stats["max_dd"] <= 150
        and stats["max_loss_streak"] <= 8
    )


def fmt_pct(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"{100 * float(x):.2f}%"


def fmt_money(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def evaluate(clock: int, lookback: int, hold: int, rule: str,
             entry_ts: pd.DatetimeIndex, pre_ts: pd.DatetimeIndex,
             exit_ts: pd.DatetimeIndex, valid: np.ndarray,
             returns: np.ndarray, masks: dict[str, np.ndarray]) -> dict:
    rule_mask = masks[rule]
    era_stats = {}
    combined_mask = np.zeros(len(entry_ts), dtype=bool)

    for partition in PARTITIONS:
        start, end = base.PARTS[partition]
        selected = (
            valid
            & (pre_ts >= start)
            & (entry_ts >= start)
            & (exit_ts < end)
            & rule_mask
        )
        gross = engine.NOTIONAL * returns[selected]
        net = gross - engine.FEE
        stats = engine.summarize(net, gross)
        era_stats[partition] = stats
        combined_mask |= selected

    gross_all = engine.NOTIONAL * returns[combined_mask]
    net_all = gross_all - engine.FEE
    total = engine.summarize(net_all, gross_all)

    era_passes = {p: era_gate(era_stats[p]) for p in PARTITIONS}
    wr55_count = sum(
        np.isfinite(era_stats[p]["win_rate"]) and era_stats[p]["win_rate"] >= 0.55
        for p in PARTITIONS
    )
    all_era_pass = all(era_passes.values()) and wr55_count >= 2
    total_pass = combined_gate(total)
    full_pass = bool(all_era_pass and total_pass)

    era_wrs = [era_stats[p]["win_rate"] for p in PARTITIONS]
    era_exps = [era_stats[p]["expectancy"] for p in PARTITIONS]
    min_era_wr = min(era_wrs) if all(np.isfinite(x) for x in era_wrs) else np.nan
    min_era_exp = min(era_exps) if all(np.isfinite(x) for x in era_exps) else np.nan

    row = {
        "clock_utc": engine.hhmm(clock),
        "clock_wib": engine.wib(clock),
        "lookback_min": lookback,
        "hold_min": hold,
        "character_rule": rule,
        **total,
        "min_era_wr": min_era_wr,
        "min_era_expectancy": min_era_exp,
        "eras_wr_ge_55": int(wr55_count),
        "all_era_gate": bool(all_era_pass),
        "combined_gate": bool(total_pass),
        "full_gate": full_pass,
    }
    for partition in PARTITIONS:
        s = era_stats[partition]
        prefix = {
            "external": "ext",
            "development": "dev",
            "reference_validation": "ref",
        }[partition]
        row.update({
            f"{prefix}_trades": s["trades"],
            f"{prefix}_win_rate": s["win_rate"],
            f"{prefix}_net_pnl": s["net_pnl"],
            f"{prefix}_expectancy": s["expectancy"],
            f"{prefix}_pf": s["pf"],
            f"{prefix}_max_dd": s["max_dd"],
            f"{prefix}_max_loss_streak": s["max_loss_streak"],
            f"{prefix}_gate": era_passes[partition],
        })
    return row


def main() -> None:
    base.END = DISCOVERY_END
    x5, coverage = base.load5("SOLUSDT")
    if x5.index.max() < DISCOVERY_END - pd.Timedelta(minutes=5):
        raise RuntimeError(
            f"discovery data incomplete: last={x5.index.max()} required={DISCOVERY_END - pd.Timedelta(minutes=5)}"
        )

    rows = []
    for clock in CLOCKS:
        for lookback in LOOKBACKS:
            frame = engine.state_frame(x5, clock, lookback)
            entry_ts = pd.DatetimeIndex(frame.entry_ts)
            pre_ts = pd.DatetimeIndex(frame.pre_ts)
            masks = engine.masks_for_frame(frame)
            for hold in HOLDS:
                exit_ts, valid, returns = engine.hold_returns(x5, frame, hold)
                for rule in RULES:
                    rows.append(evaluate(
                        clock, lookback, hold, rule,
                        entry_ts, pre_ts, exit_ts, valid, returns, masks,
                    ))

    grid = pd.DataFrame(rows)
    grid.to_csv(OUT_GRID, index=False)

    passers = grid.loc[grid.full_gate].copy()
    rank_cols = [
        "clock_utc", "min_era_wr", "min_era_expectancy",
        "win_rate", "expectancy", "max_dd", "trades",
    ]
    passers = passers.sort_values(
        rank_cols,
        ascending=[True, False, False, False, False, True, False],
    ).reset_index(drop=True)
    passers.to_csv(OUT_PASSERS, index=False)

    selected_rows = []
    for clock in CLOCKS:
        hh = engine.hhmm(clock)
        subset = passers.loc[passers.clock_utc == hh]
        if len(subset):
            selected_rows.append(subset.iloc[0].to_dict())
    selected = pd.DataFrame(selected_rows)
    selected.to_csv(OUT_SELECTED, index=False)

    status = f"SOL_ANCHOR_LOCAL_H23_{len(selected)}_OF_4_ROBUST_ANCHORS"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# SOL H23 Exact-Anchor All-Era Discovery Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Discovery history ends: **{DISCOVERY_END.isoformat()}** exclusive.",
        "Direction: **LONG only**.",
        "Four quarter-hour anchors were evaluated independently; no anchor pooling was used.",
        f"Search space: **{len(grid):,}** candidates (4 anchors × 90 rules × 6 lookbacks × 6 holds).",
        f"Full-gate passers: **{len(passers):,}**.",
        "",
        "## Selected robust character per exact anchor",
        "",
        "| UTC | WIB | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Min-era WR | Min-era Exp | Ext WR/Exp | Dev WR/Exp | Ref WR/Exp |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    selected_map = {row["clock_utc"]: row for _, row in selected.iterrows()} if len(selected) else {}
    for clock in CLOCKS:
        utc = engine.hhmm(clock)
        wib = engine.wib(clock)
        if utc not in selected_map:
            lines.append(f"| {utc} | {wib} | NO_ROBUST_CHARACTER | - | - | - | - | - | - | - | - | - | - | - | - | - |")
            continue
        r = selected_map[utc]
        lines.append(
            f"| {utc} | {wib} | {r['character_rule']} | {int(r['lookback_min'])}m | {int(r['hold_min'])}m | "
            f"{int(r['trades'])} | {fmt_pct(r['win_rate'])} | {fmt_money(r['net_pnl'])} | {fmt_money(r['expectancy'])} | "
            f"{r['pf']:.3f} | {fmt_money(r['max_dd'])} | {fmt_pct(r['min_era_wr'])} | {fmt_money(r['min_era_expectancy'])} | "
            f"{fmt_pct(r['ext_win_rate'])}/{fmt_money(r['ext_expectancy'])} | "
            f"{fmt_pct(r['dev_win_rate'])}/{fmt_money(r['dev_expectancy'])} | "
            f"{fmt_pct(r['ref_win_rate'])}/{fmt_money(r['ref_expectancy'])} |"
        )

    known = grid.loc[
        (grid.clock_utc == "23:45")
        & (grid.character_rule == "DRIVE_DOWN__STR_B80_100")
        & (grid.lookback_min == 15)
        & (grid.hold_min == 120)
    ]
    lines += [
        "",
        "## Prior 06:45 WIB lineage check",
        "",
    ]
    if len(known) == 1:
        r = known.iloc[0]
        lines += [
            f"The previously isolated **DRIVE_DOWN__STR_B80_100 / LB15 / hold120** at 23:45 UTC has N **{int(r.trades)}**, WR **{fmt_pct(r.win_rate)}**, net **{fmt_money(r.net_pnl)}**, expectancy **{fmt_money(r.expectancy)}**, PF **{r.pf:.3f}**, DD **{fmt_money(r.max_dd)}** across the three discovery eras.",
            f"Its all-era gate = **{'PASS' if r.all_era_gate else 'FAIL'}**, combined gate = **{'PASS' if r.combined_gate else 'FAIL'}**, full gate = **{'PASS' if r.full_gate else 'FAIL'}**.",
        ]

    lines += [
        "",
        "## Top full-gate candidates by anchor",
        "",
    ]
    for clock in CLOCKS:
        utc = engine.hhmm(clock)
        wib = engine.wib(clock)
        lines += [f"### {utc} UTC / {wib} WIB", ""]
        subset = passers.loc[passers.clock_utc == utc].head(10)
        if not len(subset):
            lines += ["No full-gate passer.", ""]
            continue
        lines += [
            "| # | Character | LB | Hold | N | WR | Exp | PF | DD | Min-era WR | Min-era Exp |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for idx, (_, r) in enumerate(subset.iterrows(), 1):
            lines.append(
                f"| {idx} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | "
                f"{fmt_pct(r.win_rate)} | {fmt_money(r.expectancy)} | {r.pf:.3f} | {fmt_money(r.max_dd)} | "
                f"{fmt_pct(r.min_era_wr)} | {fmt_money(r.min_era_expectancy)} |"
            )
        lines.append("")

    lines += [
        "## Scientific status",
        "",
        f"**Status: {status}**",
        "",
        "These are all-era robust discovery candidates, not clean OOS confirmations. No August 2026 or later data influenced this scan.",
        "",
        "Research/shadow only. No live-trading authorization or profit guarantee.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
