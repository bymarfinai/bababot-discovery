#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_r4c_h22_execution_policy_freeze as r4c

ROOT = Path(__file__).resolve().parent.parent
OUT_LEDGER = ROOT / "BNB_R4D_H22_HOLD_SWEEP_LEDGER.csv"
OUT_SUMMARY = ROOT / "BNB_R4D_H22_HOLD_SWEEP_SUMMARY.csv"
OUT_RANKING = ROOT / "BNB_R4D_H22_HOLD_SWEEP_RANKING.csv"
OUT_RESULT = ROOT / "BNB_R4D_H22_HOLD_SWEEP_RESULT.md"
OUT_STATUS = ROOT / "BNB_R4D_H22_HOLD_SWEEP_Status.txt"

HOLDS = (360, 480, 720, 960)
END = pd.Timestamp("2026-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def money(x):
    return "nan" if not finite(x) else f"${float(x):+.2f}"


def pct(x):
    return "nan" if not finite(x) else f"{100*float(x):.2f}%"


def hold_gate_row(hold: int, S: pd.DataFrame) -> dict:
    s0 = S[S.slippage_bps_per_side == 0].set_index("period")
    annual_flags = []
    annual_exps = []
    annual_nets = []
    for y in (2022, 2023, 2024, 2025):
        r = s0.loc[str(y)]
        annual_exps.append(float(r.expectancy))
        annual_nets.append(float(r.net_pnl))
        annual_flags.append(bool(
            int(r.trades) >= 24
            and finite(r.win_rate) and float(r.win_rate) >= .52
            and float(r.net_pnl) > 0
            and finite(r.expectancy) and float(r.expectancy) > 0
            and finite(r.pf) and float(r.pf) >= 1.15
            and finite(r.max_dd) and float(r.max_dd) <= 160.0
        ))

    p0 = s0.loc["2022-2025"]
    pooled0 = bool(
        int(p0.trades) >= 96
        and finite(p0.win_rate) and float(p0.win_rate) >= .55
        and float(p0.net_pnl) > 0
        and finite(p0.expectancy) and float(p0.expectancy) >= .50
        and finite(p0.pf) and float(p0.pf) >= 1.25
        and finite(p0.max_dd) and float(p0.max_dd) <= 160.0
    )

    s2 = S[S.slippage_bps_per_side == 2].set_index("period")
    p2 = s2.loc["2022-2025"]
    pos_years_2 = sum(float(s2.loc[str(y)].net_pnl) > 0 for y in (2022, 2023, 2024, 2025))
    stress2 = bool(
        float(p2.net_pnl) > 0
        and finite(p2.expectancy) and float(p2.expectancy) > 0
        and finite(p2.pf) and float(p2.pf) >= 1.15
        and pos_years_2 >= 3
    )

    supported = bool(all(annual_flags) and pooled0 and stress2)
    return {
        "hold_min": int(hold),
        "annual_gates_passed": int(sum(annual_flags)),
        "y2022_gate": bool(annual_flags[0]),
        "y2023_gate": bool(annual_flags[1]),
        "y2024_gate": bool(annual_flags[2]),
        "y2025_gate": bool(annual_flags[3]),
        "pooled_gate": pooled0,
        "stress2_gate": stress2,
        "positive_years_2bps": int(pos_years_2),
        "min_annual_exp": float(min(annual_exps)),
        "min_annual_net": float(min(annual_nets)),
        "pooled_trades": int(p0.trades),
        "pooled_wr": float(p0.win_rate),
        "pooled_net": float(p0.net_pnl),
        "pooled_exp": float(p0.expectancy),
        "pooled_pf": float(p0.pf),
        "pooled_dd": float(p0.max_dd),
        "pooled_ls": int(p0.max_loss_streak),
        "formal_supported": supported,
    }


def main():
    r4c.validate_frozen_target()
    base.synthetic_tests()
    x5, coverage = base.load5("BNBUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if idx.max() < pd.Timestamp("2025-12-31 23:55:00", tz="UTC"):
        raise RuntimeError(f"2025 dataset incomplete; max timestamp {idx.max()}")
    # Hard-close 2026 before feature construction and scoring.
    x = x5[idx < END].copy()

    ledgers = []
    summaries = []
    ranks = []

    original_hold = r4c.HOLD
    try:
        for hold in HOLDS:
            r4c.HOLD = int(hold)
            L, _ = r4c.build_consensus_ledger(x)
            if L.empty:
                raise AssertionError(f"empty execution ledger for hold {hold}")
            L = L.copy()
            L.insert(0, "hold_min", int(hold))
            S = r4c.summarize_ledger(L)
            S.insert(0, "hold_min", int(hold))
            ledgers.append(L)
            summaries.append(S)
            ranks.append(hold_gate_row(hold, S))
    finally:
        r4c.HOLD = original_hold

    LED = pd.concat(ledgers, ignore_index=True).sort_values(["hold_min", "entry_ts"]).reset_index(drop=True)
    SUM = pd.concat(summaries, ignore_index=True).sort_values(["hold_min", "slippage_bps_per_side", "period"]).reset_index(drop=True)
    R = pd.DataFrame(ranks)

    # Exact preregistered lexicographic ranking.
    R = R.sort_values(
        [
            "annual_gates_passed", "pooled_gate", "stress2_gate", "min_annual_exp",
            "pooled_exp", "pooled_pf", "pooled_dd", "hold_min",
        ],
        ascending=[False, False, False, False, False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    R.insert(0, "rank", np.arange(1, len(R) + 1))

    supported = R[R.formal_supported]
    selected = R.iloc[0]
    if len(supported):
        status = "BNB_R4D_H22_FORMAL_HOLD_SUPPORTED"
        selection_label = "FORMALLY_SUPPORTED"
    else:
        status = "BNB_R4D_H22_NO_FORMAL_HOLD_SUPPORTED"
        selection_label = "BEST_EXECUTION_CANDIDATE_NOT_FORMALLY_SUPPORTED"

    LED.to_csv(OUT_LEDGER, index=False)
    SUM.to_csv(OUT_SUMMARY, index=False)
    R.to_csv(OUT_RANKING, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB R4d — H22 Hold-Duration Sweep", "",
        "**Execution-duration optimization diagnostic only. Entry policy is frozen. 2025 is already observed; 2026 REMAINS CLOSED.**", "",
        f"Raw BNBUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen entry policy: **H22 WIB / RV_HIGH__RANGE_MID / 2-of-3 LB180-LB240-LB360 / earliest qualifying anchor / one position per day / LONG**.",
        "Only tested variable: **Hold 360 / 480 / 720 / 960 minutes**.", "",
        "## Ranked hold comparison — 0 bps pooled", "",
        "| Rank | Hold | Annual gates | Pooled gate | 2bps stress | N | WR | Net | Exp | PF | DD | LS | Min annual Exp | Formal |",
        "|---:|---:|---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in R.itertuples(index=False):
        lines.append(
            f"| {int(r.rank)} | {int(r.hold_min)}m | {int(r.annual_gates_passed)}/4 | {'Y' if r.pooled_gate else 'N'} | {'Y' if r.stress2_gate else 'N'} | "
            f"{int(r.pooled_trades)} | {pct(r.pooled_wr)} | {money(r.pooled_net)} | {money(r.pooled_exp)} | {float(r.pooled_pf):.3f} | "
            f"{money(r.pooled_dd)} | {int(r.pooled_ls)} | {money(r.min_annual_exp)} | {'Y' if r.formal_supported else 'N'} |"
        )

    lines += ["", "## Annual 0-bps metrics", ""]
    for hold in HOLDS:
        lines += [f"### Hold {hold}m", "", "| Year | N | WR | Net | Exp | PF | DD | LS |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        G = SUM[(SUM.hold_min == hold) & (SUM.slippage_bps_per_side == 0)]
        for y in (2022, 2023, 2024, 2025):
            r = G[G.period.astype(str) == str(y)].iloc[0]
            lines.append(
                f"| {y} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} |"
            )
        lines.append("")

    lines += ["## Pooled slippage stress", "", "| Hold | Slip/side | N | WR | Net | Exp | PF | DD |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for hold in HOLDS:
        G = SUM[(SUM.hold_min == hold) & (SUM.period.astype(str) == "2022-2025")]
        for r in G.sort_values("slippage_bps_per_side").itertuples(index=False):
            lines.append(
                f"| {hold}m | {int(r.slippage_bps_per_side)} bps | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} |"
            )

    lines += [
        "", "## Frozen decision", "",
        f"Selected hold by preregistered ranking: **{int(selected.hold_min)} minutes ({int(selected.hold_min)//60}h)**.",
        f"Selection status: **{selection_label}**.",
        f"Formal supported holds: **{len(supported)}**.",
        f"Overall status: **{status}**.", "",
        "No entry threshold, character, lookback voters, anchor policy, TP/SL, weekday rule, or ranking criterion was changed after observing hold results.",
        "2026 remains unopened and is reserved for forward/shadow validation after an execution duration is frozen.",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())
    print(f"STATUS={status}")


if __name__ == "__main__":
    main()
