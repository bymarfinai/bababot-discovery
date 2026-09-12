#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
FROZEN_CELLS = ROOT / "BNB_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
FINAL_ROBUST = ROOT / "BNB_R4B_STAGED_2025_FINAL_ROBUST_PLATEAUS.csv"
OUT_LEDGER = ROOT / "BNB_R4C_H22_EXECUTION_LEDGER.csv"
OUT_SUMMARY = ROOT / "BNB_R4C_H22_EXECUTION_SUMMARY.csv"
OUT_ANCHORS = ROOT / "BNB_R4C_H22_ANCHOR_DIAGNOSTIC.csv"
OUT_RESULT = ROOT / "BNB_R4C_H22_EXECUTION_POLICY_RESULT.md"
OUT_STATUS = ROOT / "BNB_R4C_H22_EXECUTION_POLICY_Status.txt"

START = pd.Timestamp("2022-01-01", tz="UTC")
END = pd.Timestamp("2026-01-01", tz="UTC")
HOUR_WIB = 22
RANK = 3
RULE = "RV_HIGH__RANGE_MID"
CLOCKS = (900, 915, 930, 945)  # 15:00..15:45 UTC = 22:00..22:45 WIB
VOTER_LBS = (180, 240, 360)
HOLD = 720
NOTIONAL = 500.0
FEE = 0.75
SLIPPAGE_BPS = (0, 2, 5, 10)
EXPECTED_CELLS = {(180,360),(180,480),(180,720),(240,720),(360,720),(180,960),(240,960)}


def finite(x):
    return bool(np.isfinite(x))


def fmt_money(x):
    return "nan" if not finite(x) else f"${float(x):+.2f}"


def fmt_pct(x):
    return "nan" if not finite(x) else f"{100*float(x):.2f}%"


def hhmm(m: int) -> str:
    return f"{m//60:02d}:{m%60:02d}"


def wib_clock(m: int) -> str:
    x = (m + 7*60) % 1440
    return hhmm(x)


def stats_from_net(net: np.ndarray, gross: np.ndarray) -> dict:
    if len(net) == 0:
        return {
            "trades":0,"win_rate":np.nan,"net_pnl":0.0,"expectancy":np.nan,
            "pf":np.nan,"max_dd":np.nan,"max_loss_streak":0,"max_win_streak":0,
        }
    return engine.summarize(np.asarray(net,float), np.asarray(gross,float))


def validate_frozen_target() -> None:
    frozen = pd.read_csv(FROZEN_CELLS)
    C = frozen[
        (frozen.hour_wib == HOUR_WIB)
        & (frozen.component_rank == RANK)
        & (frozen.character_rule.astype(str) == RULE)
    ].copy()
    actual = set(zip(C.lookback_min.astype(int), C.hold_min.astype(int)))
    if actual != EXPECTED_CELLS:
        raise AssertionError(f"H22 frozen plateau changed: {sorted(actual)}")

    robust = pd.read_csv(FINAL_ROBUST)
    R = robust[
        (robust.hour_wib == HOUR_WIB)
        & (robust.component_rank == RANK)
        & (robust.character_rule.astype(str) == RULE)
    ]
    if len(R) != 1 or str(R.iloc[0].verdict) != "FINAL_OOS_PLATEAU_PASS":
        raise AssertionError("R4c target is not the frozen R4b final robust H22 plateau")


def build_consensus_ledger(x5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine.CLOCKS = CLOCKS
    engine.LOOKBACKS = VOTER_LBS
    engine.HOLDS = (HOLD,)
    cache = engine.prep(x5)

    candidates = []
    anchor_rows = []

    for clock in CLOCKS:
        per_lb = {}
        for lb in VOTER_LBS:
            S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, HOLD)]
            ent = pd.DatetimeIndex(ent)
            ex = pd.DatetimeIndex(ex)
            m = np.asarray(masks[RULE], bool)
            per_lb[lb] = {
                "S":S,"ent":ent,"ex":ex,"valid":np.asarray(valid,bool),
                "xp":np.asarray(xp,float),"delta":np.asarray(delta,float),"mask":m,
                "index":{ts:i for i,ts in enumerate(ent)},
            }

        base_lb = VOTER_LBS[0]
        B = per_lb[base_lb]
        for i, ts in enumerate(B["ent"]):
            exit_ts = B["ex"][i]
            if ts < START or ts >= END or exit_ts >= END or not B["valid"][i]:
                continue
            # Keep year-boundary handling consistent with the annual R4b tests.
            if ts.year != exit_ts.year:
                continue

            active = []
            valid_votes = 0
            for lb in VOTER_LBS:
                P = per_lb[lb]
                j = P["index"].get(ts)
                if j is None or not P["valid"][j]:
                    continue
                valid_votes += 1
                if bool(P["mask"][j]):
                    active.append(lb)
            votes = len(active)
            eligible = bool(valid_votes == len(VOTER_LBS) and votes >= 2)
            anchor_rows.append({
                "entry_ts":ts,"clock_utc":hhmm(clock),"clock_wib":wib_clock(clock),
                "valid_voters":valid_votes,"votes":votes,
                "lb180":int(180 in active),"lb240":int(240 in active),"lb360":int(360 in active),
                "eligible":eligible,
            })
            if not eligible:
                continue

            entry_price = float(B["S"].entry_price.iloc[i])
            exit_price = float(B["xp"][i])
            gross = float(NOTIONAL * B["delta"][i])
            candidates.append({
                "entry_ts":ts,"exit_ts":exit_ts,"clock_min_utc":clock,
                "clock_utc":hhmm(clock),"clock_wib":wib_clock(clock),
                "votes":votes,"active_lbs":";".join(str(x) for x in active),
                "entry_price":entry_price,"exit_price":exit_price,
                "gross_pnl":gross,
            })

    A = pd.DataFrame(anchor_rows).sort_values(["entry_ts","clock_utc"]).reset_index(drop=True)
    if not candidates:
        return pd.DataFrame(), A

    C = pd.DataFrame(candidates).sort_values(["entry_ts","clock_min_utc"]).reset_index(drop=True)
    C["wib_day"] = pd.DatetimeIndex(C.entry_ts).tz_convert("Asia/Jakarta").date
    # Earliest qualifying H22 anchor only.
    C = C.groupby("wib_day", as_index=False, sort=True).head(1).sort_values("entry_ts").reset_index(drop=True)

    keep = []
    last_exit = None
    for r in C.itertuples(index=False):
        ts = pd.Timestamp(r.entry_ts)
        ex = pd.Timestamp(r.exit_ts)
        if last_exit is not None and ts < last_exit:
            continue
        keep.append(True)
        last_exit = ex
    # H720 should prevent next-day H22 overlap; assert rather than silently change the rule.
    if len(keep) != len(C):
        raise AssertionError("unexpected overlapping H22 policy positions")

    L = C.copy()
    L["year"] = pd.DatetimeIndex(L.entry_ts).year
    for bps in SLIPPAGE_BPS:
        slip = NOTIONAL * (2.0 * bps / 10000.0)
        L[f"implementation_cost_{bps}bps"] = FEE + slip
        L[f"net_{bps}bps"] = L.gross_pnl - (FEE + slip)
    return L, A


def summarize_ledger(L: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bps in SLIPPAGE_BPS:
        for label, G in [(str(y), L[L.year == y]) for y in (2022,2023,2024,2025)] + [("2022-2025", L)]:
            st = stats_from_net(G[f"net_{bps}bps"].to_numpy(float), G.gross_pnl.to_numpy(float))
            rows.append({
                "period":label,"slippage_bps_per_side":bps,
                "trades":int(st["trades"]),"win_rate":st["win_rate"],"net_pnl":st["net_pnl"],
                "expectancy":st["expectancy"],"pf":st["pf"],"max_dd":st["max_dd"],
                "max_loss_streak":int(st["max_loss_streak"]),"max_win_streak":int(st["max_win_streak"]),
            })
    return pd.DataFrame(rows)


def gate_summary(S: pd.DataFrame) -> tuple[bool, dict]:
    s0 = S[S.slippage_bps_per_side == 0].set_index("period")
    annual = []
    for y in (2022,2023,2024,2025):
        r = s0.loc[str(y)]
        annual.append(bool(
            int(r.trades) >= 24 and finite(r.win_rate) and float(r.win_rate) >= .52
            and float(r.net_pnl) > 0 and finite(r.expectancy) and float(r.expectancy) > 0
            and finite(r.pf) and float(r.pf) >= 1.15
            and finite(r.max_dd) and float(r.max_dd) <= 160.0
        ))
    p0 = s0.loc["2022-2025"]
    pooled0 = bool(
        int(p0.trades) >= 96 and finite(p0.win_rate) and float(p0.win_rate) >= .55
        and float(p0.net_pnl) > 0 and finite(p0.expectancy) and float(p0.expectancy) >= .50
        and finite(p0.pf) and float(p0.pf) >= 1.25
        and finite(p0.max_dd) and float(p0.max_dd) <= 160.0
    )

    s2 = S[S.slippage_bps_per_side == 2].set_index("period")
    p2 = s2.loc["2022-2025"]
    pos_years_2 = sum(float(s2.loc[str(y)].net_pnl) > 0 for y in (2022,2023,2024,2025))
    stress2 = bool(
        float(p2.net_pnl) > 0 and finite(p2.expectancy) and float(p2.expectancy) > 0
        and finite(p2.pf) and float(p2.pf) >= 1.15 and pos_years_2 >= 3
    )
    passed = bool(all(annual) and pooled0 and stress2)
    return passed, {
        "annual0":annual,"pooled0":pooled0,"stress2":stress2,"positive_years_2bps":int(pos_years_2)
    }


def main():
    validate_frozen_target()
    base.synthetic_tests()
    x5, coverage = base.load5("BNBUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if idx.max() < pd.Timestamp("2025-12-31 23:55:00", tz="UTC"):
        raise RuntimeError(f"2025 dataset incomplete; max timestamp {idx.max()}")
    # Hard-close 2026 before any feature construction.
    x = x5[idx < END].copy()

    L, A = build_consensus_ledger(x)
    if L.empty:
        raise AssertionError("R4c consensus ledger is empty")
    S = summarize_ledger(L)
    passed, gates = gate_summary(S)

    L.to_csv(OUT_LEDGER, index=False)
    S.to_csv(OUT_SUMMARY, index=False)

    anchor_diag = (
        A.groupby(["clock_utc","clock_wib"], as_index=False)
        .agg(observations=("entry_ts","size"), eligible=("eligible","sum"), mean_votes=("votes","mean"))
    )
    selected_counts = L.groupby(["clock_utc","clock_wib"], as_index=False).size().rename(columns={"size":"selected_trades"})
    anchor_diag = anchor_diag.merge(selected_counts, on=["clock_utc","clock_wib"], how="left").fillna({"selected_trades":0})
    anchor_diag["selected_trades"] = anchor_diag.selected_trades.astype(int)
    anchor_diag.to_csv(OUT_ANCHORS, index=False)

    status = "BNB_R4C_H22_EXECUTION_POLICY_SUPPORTED" if passed else "BNB_R4C_H22_EXECUTION_POLICY_NOT_SUPPORTED"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB R4c — H22 Plateau Execution Policy Freeze", "",
        "**2022-2025 execution-synthesis diagnostic only. 2025 is not re-labeled as fresh OOS. 2026 REMAINS CLOSED.**", "",
        f"Raw BNBUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen R4b target: **H22 WIB / RV_HIGH__RANGE_MID / rank 3**.",
        "Policy: **2-of-3 unique-lookback consensus (LB180/LB240/LB360), earliest qualifying H22 anchor, H720, one position/day, no pyramiding**.",
        f"True de-duplicated trades, 2022-2025: **{len(L)}**.", "",
        "## Execution metrics", "",
        "| Period | Slip/side | N | WR | Net | Exp/trade | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {int(r.slippage_bps_per_side)} bps | {int(r.trades)} | {fmt_pct(r.win_rate)} | "
            f"{fmt_money(r.net_pnl)} | {fmt_money(r.expectancy)} | {float(r.pf):.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} |"
        )

    lines += ["", "## Anchor usage", "", "| UTC | WIB | Eligible observations | Selected trades | Mean votes |", "|---:|---:|---:|---:|---:|"]
    for r in anchor_diag.itertuples(index=False):
        lines.append(f"| {r.clock_utc} | {r.clock_wib} | {int(r.eligible)} | {int(r.selected_trades)} | {float(r.mean_votes):.2f} |")

    lines += [
        "", "## Frozen gate audit", "",
        f"- 0 bps annual gates: **{sum(gates['annual0'])}/4 pass**.",
        f"- 0 bps pooled gate: **{'PASS' if gates['pooled0'] else 'FAIL'}**.",
        f"- 2 bps/side stress gate: **{'PASS' if gates['stress2'] else 'FAIL'}**; positive years **{gates['positive_years_2bps']}/4**.",
        f"- Loss streak remains diagnostic only.", "",
        f"**Status: {status}**", "",
        "The execution policy was frozen from plateau topology, not from the best 2025 coordinate.",
        "No alternative consensus threshold, hold, coordinate, TP/SL, or weekday rule was searched after observing this output.",
        "The inherited R4b signal universe is weekday-only; weekend generalization is not tested here.",
        "2026 remains unopened and is reserved for later forward/shadow validation.", "",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())
    print(f"STATUS={status}")


if __name__ == "__main__":
    main()
