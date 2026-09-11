#!/usr/bin/env python3
"""Preregistered forward Reference Validation for the four frozen SOL hourly LONG winners."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ECONOMIC_FIRST_4WINNER_REFERENCE_VALIDATION"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_ATLAS = ROOT / f"{PFX}_AnchorAtlas.csv"
OUT_YEARLY = ROOT / f"{PFX}_Yearly.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

WINNERS = (
    {
        "hour": "H04",
        "utc": "04:00-05:00",
        "wib": "11:00-12:00",
        "clocks": (240, 255, 270, 285),
        "rule": "EFF_LOW__RANGE_HIGH",
        "lookback": 360,
        "hold": 240,
        "dev_n": 201,
        "dev_wr_pct": 62.19,
        "dev_dd": 118.37,
    },
    {
        "hour": "H15",
        "utc": "15:00-16:00",
        "wib": "22:00-23:00",
        "clocks": (900, 915, 930, 945),
        "rule": "EFF_HIGH__RANGE_LOW",
        "lookback": 240,
        "hold": 960,
        "dev_n": 171,
        "dev_wr_pct": 60.82,
        "dev_dd": 119.05,
    },
    {
        "hour": "H22",
        "utc": "22:00-23:00",
        "wib": "05:00-06:00",
        "clocks": (1320, 1335, 1350, 1365),
        "rule": "EFF_LOW__EXT_MID",
        "lookback": 240,
        "hold": 360,
        "dev_n": 285,
        "dev_wr_pct": 59.30,
        "dev_dd": 93.85,
    },
    {
        "hour": "H23",
        "utc": "23:00-00:00",
        "wib": "06:00-07:00",
        "clocks": (1380, 1395, 1410, 1425),
        "rule": "DRIVE_DOWN__STR_B80_100",
        "lookback": 15,
        "hold": 120,
        "dev_n": 306,
        "dev_wr_pct": 60.13,
        "dev_dd": 90.21,
    },
)

PARTITIONS = {
    "development": (base.PARTS["development"][0], base.PARTS["development"][1], (2022, 2023, 2024)),
    "reference_validation": (
        base.PARTS["reference_validation"][0],
        base.PARTS["reference_validation"][1],
        (2025, 2026),
    ),
}


def pct(v: float) -> str:
    return "-" if not np.isfinite(v) else f"{100 * float(v):.2f}%"


def money(v: float) -> str:
    return "-" if not np.isfinite(v) else f"${float(v):+.2f}"


def clock_label(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def anchor_supportive(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 40
        and stats["win_rate"] >= 0.52
        and stats["net_pnl"] > 0
        and stats["expectancy"] > 0
        and stats["pf"] >= 1.05
        and stats["max_dd"] <= 125
        and stats["max_loss_streak"] <= 10
    )


def pooled_gate(stats: dict) -> bool:
    return bool(
        stats["trades"] >= 160
        and stats["win_rate"] >= 0.55
        and stats["net_pnl"] > 0
        and stats["expectancy"] >= 0.50
        and stats["pf"] >= 1.20
        and stats["max_dd"] <= 125
        and stats["max_loss_streak"] <= 8
    )


def era_gate(year_stats: list[dict]) -> bool:
    each_ok = all(
        r["trades"] >= 40
        and r["win_rate"] >= 0.52
        and r["net_pnl"] > 0
        and r["expectancy"] > 0
        and r["pf"] >= 1.05
        for r in year_stats
    )
    years_wr55 = sum(r["win_rate"] >= 0.55 for r in year_stats)
    return bool(each_ok and years_wr55 >= 2)


def evaluate_one(x5: pd.DataFrame, winner: dict, partition: str):
    start, end, years = PARTITIONS[partition]
    anchor_rows = []
    pooled_frames = []

    for clock in winner["clocks"]:
        frame = engine.state_frame(x5, clock, winner["lookback"])
        masks = engine.masks_for_frame(frame)
        exit_ts, valid, returns = engine.hold_returns(x5, frame, winner["hold"])
        entry_ts = pd.DatetimeIndex(frame.entry_ts)
        pre_ts = pd.DatetimeIndex(frame.pre_ts)
        chosen = (
            valid
            & (pre_ts >= start)
            & (entry_ts >= start)
            & (exit_ts < end)
            & masks[winner["rule"]]
        )
        gross = engine.NOTIONAL * returns[chosen]
        net = gross - engine.FEE
        stats = engine.summarize(net, gross)
        evaluable = stats["trades"] >= 40
        supportive = anchor_supportive(stats)
        anchor_rows.append({
            "partition": partition,
            "hour": winner["hour"],
            "utc_hour": winner["utc"],
            "wib_hour": winner["wib"],
            "character_rule": winner["rule"],
            "lookback_min": winner["lookback"],
            "hold_min": winner["hold"],
            "clock_utc": clock_label(clock),
            **stats,
            "evaluable": evaluable,
            "supportive": supportive,
        })
        if len(net):
            pooled_frames.append(pd.DataFrame({
                "entry_ts": entry_ts[chosen],
                "clock": clock,
                "gross": gross,
                "net": net,
            }))

    if pooled_frames:
        trades = pd.concat(pooled_frames, ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        pooled = engine.summarize(trades.net.to_numpy(float), trades.gross.to_numpy(float))
    else:
        trades = pd.DataFrame(columns=["entry_ts", "clock", "gross", "net"])
        pooled = engine.summarize(np.array([]), np.array([]))

    year_rows = []
    year_stats = []
    for year in years:
        q = trades[pd.DatetimeIndex(trades.entry_ts).year == year] if len(trades) else trades
        stats = engine.summarize(q.net.to_numpy(float), q.gross.to_numpy(float))
        year_stats.append(stats)
        year_rows.append({
            "partition": partition,
            "hour": winner["hour"],
            "year": year,
            **stats,
            "year_gate_basic": bool(
                stats["trades"] >= 40
                and stats["win_rate"] >= 0.52
                and stats["net_pnl"] > 0
                and stats["expectancy"] > 0
                and stats["pf"] >= 1.05
            ),
            "wr55": bool(stats["win_rate"] >= 0.55),
        })

    evaluable_anchors = sum(r["evaluable"] for r in anchor_rows)
    supportive_anchors = sum(r["supportive"] for r in anchor_rows)
    a_gate = bool(evaluable_anchors >= 3 and supportive_anchors >= 3)
    p_gate = pooled_gate(pooled)
    e_gate = era_gate(year_stats)
    candidate_gate = bool(a_gate and p_gate and e_gate)

    summary = {
        "partition": partition,
        "hour": winner["hour"],
        "utc_hour": winner["utc"],
        "wib_hour": winner["wib"],
        "character_rule": winner["rule"],
        "lookback_min": winner["lookback"],
        "hold_min": winner["hold"],
        **pooled,
        "evaluable_anchors": evaluable_anchors,
        "supportive_anchors": supportive_anchors,
        "anchor_gate": a_gate,
        "pooled_gate": p_gate,
        "era_gate": e_gate,
        "candidate_gate": candidate_gate,
        "years_wr55": sum(r["win_rate"] >= 0.55 for r in year_stats),
    }
    return summary, anchor_rows, year_rows


def parity_assert(winner: dict, summary: dict) -> None:
    assert summary["candidate_gate"], f"{winner['hour']} Development gate parity failed"
    assert int(summary["trades"]) == winner["dev_n"], (
        f"{winner['hour']} Development N parity failed: {summary['trades']} != {winner['dev_n']}"
    )
    assert round(100 * float(summary["win_rate"]), 2) == winner["dev_wr_pct"], (
        f"{winner['hour']} Development WR parity failed: {100*summary['win_rate']:.2f} != {winner['dev_wr_pct']:.2f}"
    )
    assert round(float(summary["max_dd"]), 2) == winner["dev_dd"], (
        f"{winner['hour']} Development DD parity failed: {summary['max_dd']:.2f} != {winner['dev_dd']:.2f}"
    )


def render_result(coverage: float, summaries: pd.DataFrame, yearly: pd.DataFrame) -> str:
    dev = summaries[summaries.partition == "development"].copy()
    ref = summaries[summaries.partition == "reference_validation"].copy()
    pass_count = int(ref.candidate_gate.astype(bool).sum())
    if pass_count == 4:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_ALL_PASS"
    elif pass_count == 0:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_NONE_PASS"
    else:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_PARTIAL_PASS"

    lines = [
        "# SOL Economic-First — Four-Winner Reference Validation Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.",
        "",
        "Primary forward OOS: **2025-01-01 UTC through 2026-07-30 UTC (exclusive end)**.",
        "August 2026 remained unopened.",
        "No rule, lookback, hold, clock, fee, feature definition, or gate threshold was changed.",
        "",
        "## Development parity audit",
        "",
        "All four frozen winners reproduced their Development candidate gate plus frozen N/WR/DD checkpoints before OOS interpretation.",
        "",
        "| Hour | Character | LB | Hold | N | WR | Exp | PF | DD | Anchors | Gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.hour} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | "
            f"{int(r.trades)} | {pct(r.win_rate)} | {money(r.expectancy)} | {r.pf:.3f} | "
            f"{money(r.max_dd)} | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | "
            f"{'PASS' if r.candidate_gate else 'FAIL'} |"
        )

    lines += [
        "",
        "## Reference Validation",
        "",
        "| Hour (WIB) | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Loss streak | Anchors | Anchor | Pooled | Era | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for _, r in ref.iterrows():
        lines.append(
            f"| {r.hour} ({r.wib_hour}) | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | "
            f"{int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | "
            f"{r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | "
            f"{'PASS' if r.anchor_gate else 'FAIL'} | {'PASS' if r.pooled_gate else 'FAIL'} | "
            f"{'PASS' if r.era_gate else 'FAIL'} | "
            f"**{'REFERENCE_VALIDATED' if r.candidate_gate else 'REFERENCE_NOT_VALIDATED'}** |"
        )

    lines += ["", "## Forward-year detail", ""]
    for hour in ref.hour:
        lines.append(f"### {hour}")
        lines.append("")
        lines.append("| Year | N | WR | Net | Exp | PF | DD | Basic year gate | WR>=55% |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---|---|")
        q = yearly[(yearly.partition == "reference_validation") & (yearly.hour == hour)]
        for _, r in q.iterrows():
            lines.append(
                f"| {int(r.year)} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
                f"{money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | "
                f"{'PASS' if r.year_gate_basic else 'FAIL'} | {'YES' if r.wr55 else 'NO'} |"
            )
        lines.append("")

    lines += [
        "## Frozen decision",
        "",
        f"**{status}**",
        "",
        f"Validated winners: **{pass_count}/4**.",
        "",
        "A failed winner is not retuned or replaced after seeing Reference Validation. August 2026 remains unopened as the next final holdout.",
        "",
        "Research/shadow only. No live promotion or profit guarantee.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    x5, coverage = base.load5("SOLUSDT")
    summaries = []
    atlas = []
    yearly = []

    # Development parity is executed first. Any mismatch aborts the run before OOS is interpreted.
    for winner in WINNERS:
        summary, arows, yrows = evaluate_one(x5, winner, "development")
        parity_assert(winner, summary)
        summaries.append(summary)
        atlas.extend(arows)
        yearly.extend(yrows)

    # Frozen forward Reference Validation. No search or reranking occurs here.
    for winner in WINNERS:
        summary, arows, yrows = evaluate_one(x5, winner, "reference_validation")
        summaries.append(summary)
        atlas.extend(arows)
        yearly.extend(yrows)

    sdf = pd.DataFrame(summaries)
    adf = pd.DataFrame(atlas)
    ydf = pd.DataFrame(yearly)
    sdf.to_csv(OUT_SUMMARY, index=False)
    adf.to_csv(OUT_ATLAS, index=False)
    ydf.to_csv(OUT_YEARLY, index=False)

    ref = sdf[sdf.partition == "reference_validation"]
    passes = int(ref.candidate_gate.astype(bool).sum())
    if passes == 4:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_ALL_PASS"
    elif passes == 0:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_NONE_PASS"
    else:
        status = "SOL_4WINNER_REFERENCE_VALIDATION_PARTIAL_PASS"
    OUT_STATUS.write_text(status + "\n")
    OUT_RESULT.write_text(render_result(coverage, sdf, ydf))
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
