#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_orb_entry_structure_character_v1 as char

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ORB_E2_ECONOMICS_V1"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_YEAR = ROOT / f"{PFX}_Yearly.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HORIZONS = (15, 30, 60, 120)
NOTIONAL_USD = 500.0
ROUNDTRIP_COST = 0.0015  # 0.15%
BAR = pd.Timedelta(minutes=5)


def max_dd(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    eq = np.cumsum(np.asarray(pnls, dtype=float))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def max_loss_streak(pnls: list[float]) -> int:
    best = cur = 0
    for x in pnls:
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def profit_factor(pnls: list[float]) -> float:
    pos = sum(x for x in pnls if x > 0)
    neg = -sum(x for x in pnls if x < 0)
    if neg <= 0:
        return float("inf") if pos > 0 else np.nan
    return pos / neg


def e2_path_diagnostics(x5: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in ev.itertuples(index=False):
        ts = pd.Timestamp(getattr(r, "E2_RETEST_LEVEL_time"))
        ep = float(getattr(r, "E2_RETEST_LEVEL_price"))
        z = x5[(x5.index >= ts) & (x5.index < ts + pd.Timedelta(minutes=120))]
        if z.empty:
            mfe = mae = np.nan
        else:
            mfe = (float(z.high.max()) / ep - 1.0) * 100.0
            mae = (float(z.low.min()) / ep - 1.0) * 100.0
        rows.append((mfe, mae))
    out = ev.copy()
    out["E2_mfe_120m_pct"] = [x[0] for x in rows]
    out["E2_mae_120m_pct"] = [x[1] for x in rows]
    return out


def summarize(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trades = ev.copy()
    summary_rows = []
    yearly_rows = []

    trades["year"] = pd.to_datetime(trades["date"]).dt.year
    for h in HORIZONS:
        gross_pct = pd.to_numeric(trades[f"E2_RETEST_LEVEL_ret_{h}m_pct"], errors="coerce")
        gross_dec = gross_pct / 100.0
        net_dec = gross_dec - ROUNDTRIP_COST
        pnl = net_dec * NOTIONAL_USD
        trades[f"gross_ret_{h}m_pct"] = gross_pct
        trades[f"net_ret_{h}m_pct"] = net_dec * 100.0
        trades[f"pnl_{h}m_usd"] = pnl

        valid = gross_pct.notna()
        gp = gross_pct[valid]
        nd = net_dec[valid]
        pp = pnl[valid]
        ordered = trades.loc[valid].assign(_pnl=pp).sort_values("date")
        pnls = ordered._pnl.tolist()

        summary_rows.append({
            "horizon_min": h,
            "n": int(valid.sum()),
            "gross_hit_rate": float((gp > 0).mean()),
            "net_win_rate": float((nd > 0).mean()),
            "gross_mean_ret_pct": float(gp.mean()),
            "net_mean_ret_pct": float((nd * 100.0).mean()),
            "net_pnl_usd": float(pp.sum()),
            "expectancy_usd": float(pp.mean()),
            "profit_factor": float(profit_factor(pnls)),
            "max_drawdown_usd": float(max_dd(pnls)),
            "max_loss_streak": int(max_loss_streak(pnls)),
        })

        for year, g in trades.loc[valid].groupby("year"):
            y_pnl = g[f"pnl_{h}m_usd"].astype(float)
            y_net = g[f"net_ret_{h}m_pct"].astype(float)
            yearly_rows.append({
                "horizon_min": h,
                "year": int(year),
                "n": len(g),
                "net_win_rate": float((y_net > 0).mean()),
                "net_pnl_usd": float(y_pnl.sum()),
                "expectancy_usd": float(y_pnl.mean()),
                "profit_factor": float(profit_factor(y_pnl.tolist())),
            })

    return trades, pd.DataFrame(summary_rows), pd.DataFrame(yearly_rows)


def main() -> None:
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = char.collect(x5)
    if len(ev) != 145:
        raise RuntimeError(f"frozen population changed: expected 145, got {len(ev)}")
    ev = e2_path_diagnostics(x5, ev)

    trades, summary, yearly = summarize(ev)
    trades.to_csv(OUT_TRADES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    yearly.to_csv(OUT_YEAR, index=False)

    lines = [
        "# SOL ORB E2 Retest Economics v1 — Development",
        "",
        f"- Data coverage: {coverage:.6%}",
        f"- Frozen structure population: **{len(ev)}**",
        "- Entry: **E2_RETEST_LEVEL = ORB High on retest**",
        f"- Reference notional: **${NOTIONAL_USD:.0f}/trade**",
        f"- Round-trip cost: **{ROUNDTRIP_COST:.2%}**",
        "- Fixed time exits only; no TP/SL optimization; Reference/OOS closed.",
        "",
        "## Economics",
        "",
        "| Exit | N | Gross hit | Net WR | Gross mean | Net mean | Net PnL | Exp/trade | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        pf = "inf" if np.isinf(r.profit_factor) else f"{r.profit_factor:.3f}"
        lines.append(
            f"| +{int(r.horizon_min)}m | {int(r.n)} | {r.gross_hit_rate:.1%} | {r.net_win_rate:.1%} | "
            f"{r.gross_mean_ret_pct:.3f}% | {r.net_mean_ret_pct:.3f}% | ${r.net_pnl_usd:.2f} | "
            f"${r.expectancy_usd:.3f} | {pf} | ${r.max_drawdown_usd:.2f} | {int(r.max_loss_streak)} |"
        )

    lines += ["", "## Year stability", "", "| Exit | Year | N | Net WR | Net PnL | Exp/trade | PF |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in yearly.sort_values(["horizon_min", "year"]).itertuples(index=False):
        pf = "inf" if np.isinf(r.profit_factor) else f"{r.profit_factor:.3f}"
        lines.append(
            f"| +{int(r.horizon_min)}m | {int(r.year)} | {int(r.n)} | {r.net_win_rate:.1%} | ${r.net_pnl_usd:.2f} | ${r.expectancy_usd:.3f} | {pf} |"
        )

    mfe = pd.to_numeric(trades["E2_mfe_120m_pct"], errors="coerce")
    mae = pd.to_numeric(trades["E2_mae_120m_pct"], errors="coerce")
    lines += [
        "",
        "## E2 path diagnostic",
        "",
        f"- Median 120m MFE from conservative post-retest fill clock: **{mfe.median():.3f}%**",
        f"- Median 120m MAE from conservative post-retest fill clock: **{mae.median():.3f}%**",
        "",
        "## Boundary",
        "",
        "Development-only economics. No retest-quality filter was added. A positive result does not promote a live rule and does not authorize opening Reference/OOS. Any further filter or risk-management rule requires a new preregistration.",
    ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("COMPLETE_DEVELOPMENT_E2_ECONOMICS_ONLY\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
