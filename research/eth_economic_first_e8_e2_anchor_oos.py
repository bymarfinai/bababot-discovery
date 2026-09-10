#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e2_drive_response as e2

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E8_E2_ANCHOR_OOS"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 17 * 60
LOOKBACK = 360
HOLD = 720
MODE = "MOMENTUM"


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low {coverage}")

    rows = []
    trades = []
    for part in ("development", "external", "reference_validation"):
        T = e2.trade_frame(x5, part, CLOCK, LOOKBACK, HOLD, MODE)
        s = e2.e1.summarize(T, 4 if part == "development" else 0)
        rows.append({"partition": part, **s})
        trades.append(T)

    S = pd.DataFrame(rows)
    D = S[S.partition == "development"].iloc[0]
    # Rounded reproduction checks against published E2 anchor.
    checks = {
        "n": int(D.trades) == 781,
        "wr": abs(float(D.win_rate) - 0.4763) <= 0.0002,
        "net": abs(float(D.net_pnl) - 481.58) <= 0.10,
        "exp": abs(float(D.expectancy) - 0.62) <= 0.02,
        "pf": abs(float(D.pf) - 1.155) <= 0.002,
        "dd": abs(float(D.max_dd) - 315.01) <= 0.20,
    }
    if not all(checks.values()):
        raise AssertionError(f"E2 Development reproduction failed: {checks}; observed={D.to_dict()}")

    oos = S[S.partition != "development"].copy()
    oos["economic_sign_pass"] = (
        (oos.trades >= 300) &
        (oos.net_pnl > 0) &
        (oos.expectancy > 0) &
        (oos.pf > 1.0)
    )
    supported = bool(oos.economic_sign_pass.all())
    status = "ETH_ECONOMIC_FIRST_E8_RAW_ANCHOR_SIGN_REPLICATED" if supported else "ETH_ECONOMIC_FIRST_E8_RAW_ANCHOR_NOT_REPLICATED"

    S2 = S.merge(oos[["partition", "economic_sign_pass"]], on="partition", how="left")
    S2.to_csv(OUT_SUMMARY, index=False)
    pd.concat(trades, ignore_index=True).to_csv(OUT_TRADES, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH Economic-First E8 — Raw E2 Anchor OOS Audit Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen one-coordinate audit: **17:00 UTC / LB360 / MOMENTUM / hold720m / no strength filter / no TP / no SL**.",
        "Fixed economics: **$500 notional / $0.75 round-trip fee / no compounding**.", "",
        "## Development reproduction", "",
        f"N **{int(D.trades)}**, WR **{pct(D.win_rate)}**, net **{money(D.net_pnl)}**, exp **{money(D.expectancy)}/trade**, PF **{D.pf:.3f}**, DD **{money(D.max_dd)}**, loss streak **{int(D.max_loss_streak)}**.", "",
        "## OOS audit", "",
        "| Partition | N | WR | Net | Exp | PF | DD | L-streak | Economic sign |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in oos.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.economic_sign_pass else 'FAIL'} |")

    allT = pd.concat(trades, ignore_index=True)
    sa = e2.e1.summarize(allT, 0)
    lines += ["", "## Combined historical — descriptive", "",
              f"N **{sa['trades']}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{sa['max_loss_streak']}**.", "",
              f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
