#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ECONOMIC_FIRST_OOS_VALIDATION"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_PARTS = ROOT / f"{PFX}_PartitionSummary.csv"
OUT_ANCHORS = ROOT / f"{PFX}_AnchorAtlas.csv"
OUT_YEARS = ROOT / f"{PFX}_YearAtlas.csv"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

PARTITIONS = ("external", "reference_validation")
WINNERS = (
    {
        "hour": "H04",
        "utc": "04:00-05:00",
        "wib": "11:00-12:00",
        "clocks": (240, 255, 270, 285),
        "rule": "EFF_LOW__RANGE_HIGH",
        "lookback": 360,
        "hold": 240,
    },
    {
        "hour": "H15",
        "utc": "15:00-16:00",
        "wib": "22:00-23:00",
        "clocks": (900, 915, 930, 945),
        "rule": "EFF_HIGH__RANGE_LOW",
        "lookback": 240,
        "hold": 960,
    },
    {
        "hour": "H22",
        "utc": "22:00-23:00",
        "wib": "05:00-06:00",
        "clocks": (1320, 1335, 1350, 1365),
        "rule": "EFF_LOW__EXT_MID",
        "lookback": 240,
        "hold": 360,
    },
    {
        "hour": "H23",
        "utc": "23:00-00:00",
        "wib": "06:00-07:00",
        "clocks": (1380, 1395, 1410, 1425),
        "rule": "DRIVE_DOWN__STR_B80_100",
        "lookback": 15,
        "hold": 120,
    },
)


def partition_support(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 40
        and np.isfinite(stats["win_rate"])
        and stats["win_rate"] >= 0.52
        and stats["net_pnl"] > 0
        and np.isfinite(stats["expectancy"])
        and stats["expectancy"] > 0
        and np.isfinite(stats["pf"])
        and stats["pf"] >= 1.05
        and stats["max_dd"] <= 125
        and stats["max_loss_streak"] <= 10
    )


def pooled_gate(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 160
        and np.isfinite(stats["win_rate"])
        and stats["win_rate"] >= 0.55
        and stats["net_pnl"] > 0
        and np.isfinite(stats["expectancy"])
        and stats["expectancy"] >= 0.50
        and np.isfinite(stats["pf"])
        and stats["pf"] >= 1.20
        and stats["max_dd"] <= 125
        and stats["max_loss_streak"] <= 8
    )


def trades_for_partition(
    x5: pd.DataFrame,
    winner: dict,
    partition: str,
) -> tuple[pd.DataFrame, list[dict]]:
    part_start, part_end = base.PARTS[partition]
    pieces = []
    anchor_rows = []

    for clock in winner["clocks"]:
        frame = engine.state_frame(x5, clock, winner["lookback"])
        masks = engine.masks_for_frame(frame)
        exit_ts, valid, returns = engine.hold_returns(x5, frame, winner["hold"])
        entry_ts = pd.DatetimeIndex(frame.entry_ts)
        pre_ts = pd.DatetimeIndex(frame.pre_ts)
        selected = (
            valid
            & (pre_ts >= part_start)
            & (entry_ts >= part_start)
            & (exit_ts < part_end)
            & masks[winner["rule"]]
        )
        gross = engine.NOTIONAL * returns[selected]
        net = gross - engine.FEE
        stats = engine.summarize(net, gross)
        anchor_rows.append({
            "hour": winner["hour"],
            "partition": partition,
            "clock_utc": engine.hhmm(clock),
            "clock_wib": engine.wib(clock),
            **stats,
            "supportive": partition_support(stats),
        })
        if len(net):
            pieces.append(pd.DataFrame({
                "hour": winner["hour"],
                "partition": partition,
                "clock_utc": engine.hhmm(clock),
                "clock_wib": engine.wib(clock),
                "entry_ts": entry_ts[selected],
                "exit_ts": exit_ts[selected],
                "gross": gross,
                "net": net,
            }))

    if pieces:
        trades = pd.concat(pieces, ignore_index=True).sort_values(
            ["entry_ts", "clock_utc"]
        ).reset_index(drop=True)
    else:
        trades = pd.DataFrame(columns=[
            "hour", "partition", "clock_utc", "clock_wib",
            "entry_ts", "exit_ts", "gross", "net",
        ])
    return trades, anchor_rows


def stats_from_trades(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return engine.summarize(np.array([]), np.array([]))
    return engine.summarize(
        trades.net.to_numpy(float),
        trades.gross.to_numpy(float),
    )


def fmt_pct(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"{100 * float(value):.2f}%"


def fmt_money(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"${float(value):+.2f}"


def main() -> None:
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    summary_rows = []
    partition_rows = []
    anchor_rows = []
    year_rows = []
    all_trades = []

    for winner in WINNERS:
        part_trades: dict[str, pd.DataFrame] = {}
        part_gate: dict[str, bool] = {}

        for partition in PARTITIONS:
            trades, anchors = trades_for_partition(x5, winner, partition)
            part_trades[partition] = trades
            all_trades.append(trades)
            anchor_rows.extend(anchors)
            stats = stats_from_trades(trades)
            passed = partition_support(stats)
            part_gate[partition] = passed
            partition_rows.append({
                "hour": winner["hour"],
                "utc_habitat": winner["utc"],
                "wib_habitat": winner["wib"],
                "rule": winner["rule"],
                "lookback_min": winner["lookback"],
                "hold_min": winner["hold"],
                "partition": partition,
                **stats,
                "partition_support_gate": passed,
            })

        combined = pd.concat(
            [part_trades[p] for p in PARTITIONS], ignore_index=True
        ).sort_values(["entry_ts", "clock_utc"]).reset_index(drop=True)
        combined_stats = stats_from_trades(combined)
        combined_pass = pooled_gate(combined_stats)
        replicated = bool(
            part_gate["external"]
            and part_gate["reference_validation"]
            and combined_pass
        )
        summary_rows.append({
            "hour": winner["hour"],
            "utc_habitat": winner["utc"],
            "wib_habitat": winner["wib"],
            "rule": winner["rule"],
            "lookback_min": winner["lookback"],
            "hold_min": winner["hold"],
            **combined_stats,
            "external_support_gate": part_gate["external"],
            "reference_validation_support_gate": part_gate["reference_validation"],
            "combined_oos_pooled_gate": combined_pass,
            "oos_replicated": replicated,
        })

        if len(combined):
            years = sorted(pd.DatetimeIndex(combined.entry_ts).year.unique())
            for year in years:
                mask = pd.DatetimeIndex(combined.entry_ts).year == year
                y = combined.loc[mask]
                ys = stats_from_trades(y)
                year_rows.append({
                    "hour": winner["hour"],
                    "year": int(year),
                    **ys,
                })

    summary = pd.DataFrame(summary_rows)
    partitions = pd.DataFrame(partition_rows)
    anchors = pd.DataFrame(anchor_rows)
    years = pd.DataFrame(year_rows)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

    summary.to_csv(OUT_SUMMARY, index=False)
    partitions.to_csv(OUT_PARTS, index=False)
    anchors.to_csv(OUT_ANCHORS, index=False)
    years.to_csv(OUT_YEARS, index=False)
    trades.to_csv(OUT_TRADES, index=False)

    replicated_count = int(summary.oos_replicated.sum())
    status = f"SOL_ECONOMIC_FIRST_OOS_{replicated_count}_OF_4_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# SOL Economic-First — Frozen-Winner OOS Validation Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "",
        "The four Development winners were evaluated without rescanning or changing rule, lookback, hold, clocks, fee, or validation thresholds.",
        "External = 2020–2021; Reference Validation = 2025-01-01 through 2026-07-29. August 2026 remains excluded.",
        "",
        "## Formal replication summary",
        "",
        "| Hour | WIB | Frozen character | LB | Hold | OOS N | WR | Net | Exp | PF | DD | Loss streak | External | RefVal | Pooled | Verdict |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.hour} | {row.wib_habitat} | {row.rule} | {int(row.lookback_min)}m | {int(row.hold_min)}m | "
            f"{int(row.trades)} | {fmt_pct(row.win_rate)} | {fmt_money(row.net_pnl)} | {fmt_money(row.expectancy)} | "
            f"{row.pf:.3f} | {fmt_money(row.max_dd)} | {int(row.max_loss_streak)} | "
            f"{'PASS' if row.external_support_gate else 'FAIL'} | "
            f"{'PASS' if row.reference_validation_support_gate else 'FAIL'} | "
            f"{'PASS' if row.combined_oos_pooled_gate else 'FAIL'} | "
            f"{'OOS_REPLICATED' if row.oos_replicated else 'OOS_NOT_REPLICATED'} |"
        )

    lines += [
        "",
        "## Partition detail",
        "",
        "| Hour | Partition | N | WR | Net | Exp | PF | DD | Loss streak | Support gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in partitions.itertuples(index=False):
        lines.append(
            f"| {row.hour} | {row.partition} | {int(row.trades)} | {fmt_pct(row.win_rate)} | "
            f"{fmt_money(row.net_pnl)} | {fmt_money(row.expectancy)} | {row.pf:.3f} | "
            f"{fmt_money(row.max_dd)} | {int(row.max_loss_streak)} | "
            f"{'PASS' if row.partition_support_gate else 'FAIL'} |"
        )

    lines += [
        "",
        "## Formal verdict",
        "",
        f"**{replicated_count} / 4 frozen hourly winners replicated out-of-sample.**",
        "",
        f"**Status: {status}**",
        "",
        "No failed winner is replaced by its Development runner-up in this experiment. No threshold relaxation or post-hoc subset is permitted.",
        "",
        "Research/shadow only. This validation is not a live-trading authorization or profit guarantee.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
