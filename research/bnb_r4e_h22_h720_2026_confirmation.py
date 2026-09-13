#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_r4c_h22_execution_policy_freeze as r4c

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_R4E_H22_H720_2026_CONFIRMATION"
OUT_LEDGER = ROOT / f"{PFX}_LEDGER.csv"
OUT_SUMMARY = ROOT / f"{PFX}_SUMMARY.csv"
OUT_ANCHORS = ROOT / f"{PFX}_ANCHORS.csv"
OUT_RESULT = ROOT / f"{PFX}_RESULT.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

START_2026 = pd.Timestamp("2026-01-01T00:00:00Z")
FREEZE_TS = pd.Timestamp("2026-09-13T05:36:03Z")  # 12:36:03 WIB
FROZEN_HOLD = 720
SLIPPAGE_BPS = (0, 2, 5, 10)


def finite(x):
    return bool(np.isfinite(x))


def money(x):
    return "nan" if not finite(x) else f"${float(x):+.2f}"


def pct(x):
    return "nan" if not finite(x) else f"{100*float(x):.2f}%"


def summarize_segment(G: pd.DataFrame, segment: str) -> list[dict]:
    rows = []
    for bps in SLIPPAGE_BPS:
        if G.empty:
            st = r4c.stats_from_net(np.asarray([], float), np.asarray([], float))
        else:
            st = r4c.stats_from_net(
                G[f"net_{bps}bps"].to_numpy(float),
                G.gross_pnl.to_numpy(float),
            )
        rows.append({
            "segment": segment,
            "slippage_bps_per_side": int(bps),
            "trades": int(st["trades"]),
            "win_rate": st["win_rate"],
            "net_pnl": st["net_pnl"],
            "expectancy": st["expectancy"],
            "pf": st["pf"],
            "max_dd": st["max_dd"],
            "max_loss_streak": int(st["max_loss_streak"]),
            "max_win_streak": int(st["max_win_streak"]),
        })
    return rows


def economic_gate(r) -> bool:
    return bool(
        finite(r.win_rate) and float(r.win_rate) >= .52
        and float(r.net_pnl) > 0
        and finite(r.expectancy) and float(r.expectancy) > 0
        and finite(r.pf) and float(r.pf) >= 1.15
        and finite(r.max_dd) and float(r.max_dd) <= 160.0
    )


def stress2_gate(r) -> bool:
    return bool(
        float(r.net_pnl) > 0
        and finite(r.expectancy) and float(r.expectancy) > 0
        and finite(r.pf) and float(r.pf) >= 1.15
    )


def main():
    # Validate that the inherited topology is still exactly the R4b final H22 plateau.
    r4c.validate_frozen_target()
    if r4c.RULE != "RV_HIGH__RANGE_MID":
        raise AssertionError("frozen R4c rule changed")
    if tuple(r4c.VOTER_LBS) != (180, 240, 360):
        raise AssertionError("frozen R4c voter lookbacks changed")
    if tuple(r4c.CLOCKS) != (900, 915, 930, 945):
        raise AssertionError("frozen R4c H22 anchors changed")

    base.synthetic_tests()
    x5, coverage = base.load5("BNBUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    latest_bar = idx.max()
    if latest_bar < FREEZE_TS:
        raise RuntimeError(f"dataset has not reached R4e freeze timestamp; max={latest_bar}")

    # A fixed-hold trade is observable when its exit timestamp has an available 5m bar.
    # r4c excludes exit_ts >= END, so END is set one bar after the latest available bar.
    data_end = latest_bar + pd.Timedelta(minutes=5)

    old_start, old_end, old_hold = r4c.START, r4c.END, r4c.HOLD
    try:
        r4c.START = START_2026
        r4c.END = data_end
        r4c.HOLD = FROZEN_HOLD
        L, A = r4c.build_consensus_ledger(x5)
    finally:
        r4c.START, r4c.END, r4c.HOLD = old_start, old_end, old_hold

    if L.empty:
        raise AssertionError("no completed frozen H22 H720 trades found in 2026")

    L = L.copy().sort_values("entry_ts").reset_index(drop=True)
    L.insert(0, "segment", np.where(pd.DatetimeIndex(L.entry_ts) < FREEZE_TS,
                                      "2026_PRE_FREEZE_OOS", "POST_FREEZE_PROSPECTIVE"))
    L["freeze_ts_utc"] = FREEZE_TS.isoformat()
    L["data_latest_bar_utc"] = latest_bar.isoformat()
    L.to_csv(OUT_LEDGER, index=False)

    pre = L[L.segment == "2026_PRE_FREEZE_OOS"].copy()
    post = L[L.segment == "POST_FREEZE_PROSPECTIVE"].copy()
    S = pd.DataFrame(
        summarize_segment(pre, "2026_PRE_FREEZE_OOS")
        + summarize_segment(post, "POST_FREEZE_PROSPECTIVE")
    )
    S.to_csv(OUT_SUMMARY, index=False)

    # Anchor diagnostics remain segment-separated so future prospective reruns cannot blur history.
    if A.empty:
        AD = pd.DataFrame(columns=["segment","clock_utc","clock_wib","observations","eligible","mean_votes","selected_trades"])
    else:
        A = A.copy()
        A["segment"] = np.where(pd.DatetimeIndex(A.entry_ts) < FREEZE_TS,
                                "2026_PRE_FREEZE_OOS", "POST_FREEZE_PROSPECTIVE")
        A = A[(pd.DatetimeIndex(A.entry_ts) >= START_2026) & (pd.DatetimeIndex(A.entry_ts) < data_end)]
        AD = (
            A.groupby(["segment","clock_utc","clock_wib"], as_index=False)
             .agg(observations=("entry_ts","size"), eligible=("eligible","sum"), mean_votes=("votes","mean"))
        )
        SC = (
            L.groupby(["segment","clock_utc","clock_wib"], as_index=False)
             .size().rename(columns={"size":"selected_trades"})
        )
        AD = AD.merge(SC, on=["segment","clock_utc","clock_wib"], how="left").fillna({"selected_trades":0})
        AD["selected_trades"] = AD.selected_trades.astype(int)
    AD.to_csv(OUT_ANCHORS, index=False)

    p0 = S[(S.segment == "2026_PRE_FREEZE_OOS") & (S.slippage_bps_per_side == 0)].iloc[0]
    p2 = S[(S.segment == "2026_PRE_FREEZE_OOS") & (S.slippage_bps_per_side == 2)].iloc[0]
    mature = int(p0.trades) >= 24
    econ = economic_gate(p0)
    s2pass = stress2_gate(p2)

    if mature:
        status = "BNB_R4E_2026_FORMAL_CONFIRMATION_PASS" if (econ and s2pass) else "BNB_R4E_2026_FORMAL_CONFIRMATION_FAIL"
    else:
        status = "BNB_R4E_2026_SAMPLE_NOT_MATURE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB R4e — H22 H720 Frozen 2026 Confirmation", "",
        "**Confirmation only. No 2026 value is used to alter the frozen policy.**", "",
        f"Raw 5m coverage: **{coverage:.4%}**.",
        f"Latest available 5m bar: **{latest_bar.isoformat()}**.",
        f"R4e freeze timestamp: **{FREEZE_TS.isoformat()}**.",
        "Frozen policy: **BNBUSDT LONG / H22 WIB / RV_HIGH__RANGE_MID / 2-of-3 LB180-LB240-LB360 / earliest qualifying anchor / H720 / one position per day / no pyramiding**.", "",
        "## Segment metrics", "",
        "| Segment | Slip/side | N | WR | Net | Exp | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.segment} | {int(r.slippage_bps_per_side)} bps | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} |"
            if finite(r.pf) else
            f"| {r.segment} | {int(r.slippage_bps_per_side)} bps | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | nan | {money(r.max_dd)} | {int(r.max_loss_streak)} |"
        )

    lines += [
        "", "## Frozen 2026 pre-freeze gate audit", "",
        f"- Sample maturity: **{int(p0.trades)}/24 trades** — {'MATURE' if mature else 'NOT MATURE'}.",
        f"- 0-bps non-N economic thresholds: **{'PASS' if econ else 'FAIL'}**.",
        f"- 2-bps/side stress thresholds: **{'PASS' if s2pass else 'FAIL'}**.",
        f"- Formal status: **{status}**.", "",
        "Pre-freeze 2026 is historical OOS, not prospective. Post-freeze entries are the prospective shadow segment.",
        "If the prospective segment has zero trades on this first run, that is expected and must not be treated as a failure.",
        "No rescue filters, anchor cherry-picking, or threshold changes are permitted after this output.",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())
    print(f"STATUS={status}")


if __name__ == "__main__":
    main()
