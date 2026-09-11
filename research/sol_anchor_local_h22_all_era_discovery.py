#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine
import sol_anchor_local_h23_all_era_discovery as common


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ANCHOR_LOCAL_H22_ALL_ERA_DISCOVERY"
OUT_GRID = ROOT / f"{PFX}_Grid.csv"
OUT_PASSERS = ROOT / f"{PFX}_Passers.csv"
OUT_SELECTED = ROOT / f"{PFX}_Selected.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (1320, 1335, 1350, 1365)  # 22:00..22:45 UTC = 05:00..05:45 WIB
DISCOVERY_END = pd.Timestamp("2026-07-30T00:00:00Z")


def fmt_pct(x: float) -> str:
    return common.fmt_pct(x)


def fmt_money(x: float) -> str:
    return common.fmt_money(x)


def main() -> None:
    base.END = DISCOVERY_END
    x5, coverage = base.load5("SOLUSDT")
    required_last = DISCOVERY_END - pd.Timedelta(minutes=5)
    if x5.index.max() < required_last:
        raise RuntimeError(f"discovery data incomplete: last={x5.index.max()} required={required_last}")

    rows = []
    for clock in CLOCKS:
        for lookback in engine.LOOKBACKS:
            frame = engine.state_frame(x5, clock, lookback)
            entry_ts = pd.DatetimeIndex(frame.entry_ts)
            pre_ts = pd.DatetimeIndex(frame.pre_ts)
            masks = engine.masks_for_frame(frame)
            for hold in engine.HOLDS:
                exit_ts, valid, returns = engine.hold_returns(x5, frame, hold)
                for rule in engine.RULES:
                    rows.append(common.evaluate(
                        clock, lookback, hold, rule,
                        entry_ts, pre_ts, exit_ts, valid, returns, masks,
                    ))

    grid = pd.DataFrame(rows)
    grid.to_csv(OUT_GRID, index=False)

    passers = grid.loc[grid.full_gate].copy().sort_values(
        ["clock_utc", "min_era_wr", "min_era_expectancy", "win_rate", "expectancy", "max_dd", "trades"],
        ascending=[True, False, False, False, False, True, False],
    ).reset_index(drop=True)
    passers.to_csv(OUT_PASSERS, index=False)

    chosen = []
    for clock in CLOCKS:
        subset = passers.loc[passers.clock_utc == engine.hhmm(clock)]
        if len(subset):
            chosen.append(subset.iloc[0].to_dict())
    selected = pd.DataFrame(chosen)
    selected.to_csv(OUT_SELECTED, index=False)

    status = f"SOL_ANCHOR_LOCAL_H22_{len(selected)}_OF_4_ROBUST_ANCHORS"
    OUT_STATUS.write_text(status + "\n")

    selected_map = {row["clock_utc"]: row for _, row in selected.iterrows()} if len(selected) else {}
    lines = [
        "# SOL H22 Exact-Anchor All-Era Discovery Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Discovery history ends: **{DISCOVERY_END.isoformat()}** exclusive.",
        "Direction: **LONG only**.",
        "Four H22 quarter-hour anchors were evaluated independently; no anchor pooling was used.",
        f"Search space: **{len(grid):,}** candidates (4 anchors × 90 rules × 6 lookbacks × 6 holds).",
        f"Full-gate passers: **{len(passers):,}**.",
        "",
        "## Selected robust character per exact anchor",
        "",
        "| UTC | WIB | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Min-era WR | Min-era Exp | Ext WR/Exp | Dev WR/Exp | Ref WR/Exp |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
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

    lines += ["", "## Top full-gate candidates by anchor", ""]
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
        "## Scientific status", "",
        f"**Status: {status}**", "",
        "These are all-era robust discovery candidates, not clean OOS confirmations. No August 2026 or later data influenced this scan.", "",
        "Research/shadow only. No live-trading authorization or profit guarantee.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
