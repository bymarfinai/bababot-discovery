#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_H23_0645_ANCHOR_LOCAL_FORWARD"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 23 * 60 + 45  # 23:45 UTC = 06:45 WIB
LOOKBACK = 15
HOLD = 120
RULE = "DRIVE_DOWN__STR_B80_100"
FWD_START = pd.Timestamp("2026-08-01T00:00:00Z")
FWD_END = pd.Timestamp("2026-09-12T00:00:00Z")


def support_gate(stats: dict) -> bool:
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


def pct(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"{100 * float(value):.2f}%"


def money(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"${float(value):+.2f}"


def main() -> None:
    # Extend the existing raw-data loader only to the preregistered forward end.
    # Historical bars are required solely for causal rolling-state construction.
    base.END = FWD_END
    x5, coverage = base.load5("SOLUSDT")
    required_last = FWD_END - pd.Timedelta(minutes=5)
    if x5.index.max() < required_last:
        raise RuntimeError(
            f"forward data incomplete: last={x5.index.max()} required={required_last}"
        )

    frame = engine.state_frame(x5, CLOCK, LOOKBACK)
    masks = engine.masks_for_frame(frame)
    exit_ts, valid, returns = engine.hold_returns(x5, frame, HOLD)
    entry_ts = pd.DatetimeIndex(frame.entry_ts)

    selected = (
        valid
        & (entry_ts >= FWD_START)
        & (entry_ts < FWD_END)
        & (exit_ts < FWD_END)
        & masks[RULE]
    )

    gross = engine.NOTIONAL * returns[selected]
    net = gross - engine.FEE
    stats = engine.summarize(net, gross)

    selected_rows = frame.loc[selected].copy().reset_index(drop=True)
    selected_exit_ts = pd.DatetimeIndex(exit_ts[selected])
    entry_price = selected_rows.entry_price.to_numpy(float)
    selected_returns = returns[selected]
    exit_price = entry_price * (1.0 + selected_returns)

    trades = pd.DataFrame({
        "entry_ts": pd.DatetimeIndex(selected_rows.entry_ts),
        "exit_ts": selected_exit_ts,
        "clock_utc": "23:45",
        "clock_wib": "06:45",
        "rule": RULE,
        "lookback_min": LOOKBACK,
        "hold_min": HOLD,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "drive_return": selected_rows.drive_return.to_numpy(float),
        "strength_pct": selected_rows.strength_pct.to_numpy(float),
        "gross_pnl": gross,
        "net_pnl": net,
    })
    trades.to_csv(OUT_TRADES, index=False)

    if stats["trades"] < 40:
        status = "SOL_H23_0645_FORWARD_INSUFFICIENT_SAMPLE"
        formal_gate = False
    else:
        formal_gate = support_gate(stats)
        status = (
            "SOL_H23_0645_FORWARD_SUPPORT_PASS"
            if formal_gate
            else "SOL_H23_0645_FORWARD_SUPPORT_FAIL"
        )

    summary = pd.DataFrame([{
        "forward_start": FWD_START,
        "forward_end_exclusive": FWD_END,
        "source_last_bar": x5.index.max(),
        "coverage": coverage,
        "clock_utc": "23:45",
        "clock_wib": "06:45",
        "rule": RULE,
        "lookback_min": LOOKBACK,
        "hold_min": HOLD,
        **stats,
        "support_gate_evaluable": stats["trades"] >= 40,
        "support_gate": formal_gate,
        "status": status,
    }])
    summary.to_csv(OUT_SUMMARY, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# SOL H23 06:45 WIB Anchor-Local Forward Shadow Result",
        "",
        f"Forward window: **{FWD_START.isoformat()}** to **{FWD_END.isoformat()}** exclusive.",
        f"Raw source last 5m bar: **{x5.index.max().isoformat()}**.",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "",
        "Frozen candidate: **23:45 UTC / 06:45 WIB — DRIVE_DOWN__STR_B80_100 / LB15 / hold120m**.",
        "No alternate clock, rule, lookback, hold, entry, or exit was scanned.",
        "",
        "## Forward aggregate",
        "",
        f"- N: **{stats['trades']}**",
        f"- WR: **{pct(stats['win_rate'])}**",
        f"- Net PnL: **{money(stats['net_pnl'])}**",
        f"- Expectancy: **{money(stats['expectancy'])}/trade**",
        f"- PF: **{stats['pf']:.3f}**" if np.isfinite(stats['pf']) else "- PF: **nan**",
        f"- Max DD: **{money(stats['max_dd'])}**",
        f"- Max loss streak: **{stats['max_loss_streak']}**",
        f"- Max win streak: **{stats['max_win_streak']}**",
        "",
        "## Exact forward trades",
        "",
        "| Entry UTC | Exit UTC | Entry | Exit | Net |",
        "|---|---|---:|---:|---:|",
    ]
    for row in trades.itertuples(index=False):
        lines.append(
            f"| {row.entry_ts} | {row.exit_ts} | {row.entry_price:.6f} | "
            f"{row.exit_price:.6f} | {money(row.net_pnl)} |"
        )

    lines += [
        "",
        "## Formal readout",
        "",
        f"**Status: {status}**",
        "",
    ]
    if stats["trades"] < 40:
        lines += [
            "The frozen supportive gate requires N >= 40. This first forward window is therefore formally insufficient regardless of observed WR or PnL.",
            "The result is a shadow observation only and must not be used to tune or replace the candidate.",
        ]
    else:
        lines.append(
            "The frozen single-anchor supportive gate is "
            + ("PASS." if formal_gate else "FAIL.")
        )

    lines += [
        "",
        "Research/shadow only. No live-trading authorization or profit guarantee.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
