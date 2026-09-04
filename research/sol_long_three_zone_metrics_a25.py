#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INFILE = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv"
OUT_MD = ROOT / "SOL_LONG_THREE_ZONE_METRICS_A25_Result.md"
OUT_PORT = ROOT / "SOL_LONG_THREE_ZONE_METRICS_A25_PORTFOLIO.csv"
OUT_ZONE = ROOT / "SOL_LONG_THREE_ZONE_METRICS_A25_ZONES.csv"
OUT_STATUS = ROOT / "SOL_LONG_THREE_ZONE_METRICS_A25_Status.txt"

PART_ORDER = ["development", "external", "reference_validation"]
ZONE_ORDER = ["03UTC_EXPANSION", "15UTC_EXPANSION", "18UTC_MATURE"]


def pf(s):
    x = pd.to_numeric(s, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def max_streak(vals, pred):
    best = cur = 0
    for v in vals:
        if pred(float(v)):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_dd(q, col):
    z = q.sort_values(["exit_ts", "entry_ts"]).copy()
    eq = pd.to_numeric(z[col], errors="coerce").fillna(0.0).cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max()) if len(eq) else 0.0


def aggregate_period(q, col, freq):
    z = q.copy()
    z["bucket"] = z.exit_ts.dt.to_period(freq).dt.start_time.dt.tz_localize("UTC")
    g = z.groupby("bucket", as_index=False).agg(
        pnl=(col, "sum"),
        trades=(col, "size"),
        wins=(col, lambda x: int((pd.to_numeric(x, errors="coerce") > 0).sum())),
        losses=(col, lambda x: int((pd.to_numeric(x, errors="coerce") <= 0).sum())),
    ).sort_values("bucket")
    return g


def metric_row(q, partition, scope, zone="ALL"):
    q = q.sort_values(["exit_ts", "entry_ts"]).copy()
    years = {
        "development": 3.0,
        "external": 2.0,
        "reference_validation": (pd.Timestamp("2026-07-30", tz="UTC") - pd.Timestamp("2025-01-01", tz="UTC")) / pd.Timedelta(days=365.2425),
    }[partition]
    weeks_span = years * 365.2425 / 7.0

    out = {"partition": partition, "scope": scope, "zone": zone}
    for suffix, col in [("raw", "pnl"), ("stress", "pnl_5bps")]:
        p = pd.to_numeric(q[col], errors="coerce")
        wins = p[p > 0]
        losses = p[p <= 0]
        daily = aggregate_period(q, col, "D")
        weekly = aggregate_period(q, col, "W-MON")

        out.update({
            f"n_{suffix}": len(p),
            f"trades_per_week_{suffix}": len(p) / weeks_span,
            f"wr_{suffix}": float((p > 0).mean()) if len(p) else np.nan,
            f"pf_{suffix}": pf(p),
            f"expectancy_{suffix}": float(p.mean()) if len(p) else np.nan,
            f"net_{suffix}": float(p.sum()),
            f"max_drawdown_{suffix}": max_dd(q, col),
            f"max_loss_streak_{suffix}": max_streak(p.tolist(), lambda v: v <= 0),
            f"max_win_streak_{suffix}": max_streak(p.tolist(), lambda v: v > 0),
            f"max_loss_trade_{suffix}": float(p.min()) if len(p) else np.nan,
            f"max_win_trade_{suffix}": float(p.max()) if len(p) else np.nan,
            f"min_win_trade_{suffix}": float(wins.min()) if len(wins) else np.nan,
            f"avg_win_trade_{suffix}": float(wins.mean()) if len(wins) else np.nan,
            f"median_win_trade_{suffix}": float(wins.median()) if len(wins) else np.nan,
            f"avg_loss_trade_{suffix}": float(losses.mean()) if len(losses) else np.nan,
            f"median_loss_trade_{suffix}": float(losses.median()) if len(losses) else np.nan,
            f"payoff_ratio_{suffix}": float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) and losses.mean() != 0 else np.nan,
            f"active_days_{suffix}": len(daily),
            f"positive_day_rate_{suffix}": float((daily.pnl > 0).mean()) if len(daily) else np.nan,
            f"avg_daily_pnl_{suffix}": float(daily.pnl.mean()) if len(daily) else np.nan,
            f"median_daily_pnl_{suffix}": float(daily.pnl.median()) if len(daily) else np.nan,
            f"best_day_{suffix}": float(daily.pnl.max()) if len(daily) else np.nan,
            f"worst_day_{suffix}": float(daily.pnl.min()) if len(daily) else np.nan,
            f"max_losing_day_streak_{suffix}": max_streak(daily.pnl.tolist(), lambda v: v <= 0),
            f"avg_trades_per_active_day_{suffix}": float(daily.trades.mean()) if len(daily) else np.nan,
            f"avg_wins_per_active_day_{suffix}": float(daily.wins.mean()) if len(daily) else np.nan,
            f"median_wins_per_active_day_{suffix}": float(daily.wins.median()) if len(daily) else np.nan,
            f"max_wins_in_day_{suffix}": int(daily.wins.max()) if len(daily) else 0,
            f"active_weeks_{suffix}": len(weekly),
            f"positive_week_rate_{suffix}": float((weekly.pnl > 0).mean()) if len(weekly) else np.nan,
            f"avg_weekly_pnl_{suffix}": float(weekly.pnl.mean()) if len(weekly) else np.nan,
            f"median_weekly_pnl_{suffix}": float(weekly.pnl.median()) if len(weekly) else np.nan,
            f"best_week_{suffix}": float(weekly.pnl.max()) if len(weekly) else np.nan,
            f"worst_week_{suffix}": float(weekly.pnl.min()) if len(weekly) else np.nan,
            f"max_losing_week_streak_{suffix}": max_streak(weekly.pnl.tolist(), lambda v: v <= 0),
            f"avg_trades_per_active_week_{suffix}": float(weekly.trades.mean()) if len(weekly) else np.nan,
            f"avg_wins_per_active_week_{suffix}": float(weekly.wins.mean()) if len(weekly) else np.nan,
        })
    return out


def fnum(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def main():
    q = pd.read_csv(INFILE)
    q["entry_ts"] = pd.to_datetime(q.entry_ts, utc=True)
    q["exit_ts"] = pd.to_datetime(q.exit_ts, utc=True)
    for c in ["pnl", "pnl_5bps"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")

    rows = []
    zone_rows = []
    for part in PART_ORDER:
        p = q[q.partition == part].copy()
        rows.append(metric_row(p, part, "THREE_ZONE", "ALL"))
        for zone in ZONE_ORDER:
            z = p[p.zone == zone].copy()
            if len(z):
                zone_rows.append(metric_row(z, part, "ZONE", zone))

    port = pd.DataFrame(rows)
    zones = pd.DataFrame(zone_rows)
    port.to_csv(OUT_PORT, index=False)
    zones.to_csv(OUT_ZONE, index=False)

    lines = [
        "# SOL LONG Three-Zone Complete Metrics Audit — A25 Result", "",
        "Trade definition: every actual entry is one component trade; the 18UTC REC_H2 recovery is therefore a separate trade from its parent. Daily/weekly PnL aggregates components by exit timestamp. Positive-day/week rate is the share of active days/weeks with net PnL > 0.", "",
        "## Portfolio — raw", "",
        "| Partition | N | Trades/wk | WR | PF | Exp | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Avg win | Avg loss | Payoff |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in port.iterrows():
        lines.append(f"| {r.partition} | {int(r.n_raw)} | {fnum(r.trades_per_week_raw)} | {pct(r.wr_raw)} | {fnum(r.pf_raw)} | ${fnum(r.expectancy_raw)} | ${fnum(r.net_raw)} | ${fnum(r.max_drawdown_raw)} | {int(r.max_loss_streak_raw)} | ${fnum(r.max_loss_trade_raw)} | ${fnum(r.min_win_trade_raw)} | ${fnum(r.avg_win_trade_raw)} | ${fnum(r.avg_loss_trade_raw)} | {fnum(r.payoff_ratio_raw)} |")

    lines += ["", "## Portfolio — 5bps stress", "",
        "| Partition | N | Trades/wk | WR | PF | Exp | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Avg win | Avg loss | Payoff |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in port.iterrows():
        lines.append(f"| {r.partition} | {int(r.n_stress)} | {fnum(r.trades_per_week_stress)} | {pct(r.wr_stress)} | {fnum(r.pf_stress)} | ${fnum(r.expectancy_stress)} | ${fnum(r.net_stress)} | ${fnum(r.max_drawdown_stress)} | {int(r.max_loss_streak_stress)} | ${fnum(r.max_loss_trade_stress)} | ${fnum(r.min_win_trade_stress)} | ${fnum(r.avg_win_trade_stress)} | ${fnum(r.avg_loss_trade_stress)} | {fnum(r.payoff_ratio_stress)} |")

    lines += ["", "## Daily — raw", "",
        "| Partition | Active days | Positive-day rate | Avg PnL/day | Median | Best day | Worst day | Losing-day streak | Avg trades/day | Avg wins/day | Median wins/day | Max wins/day |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in port.iterrows():
        lines.append(f"| {r.partition} | {int(r.active_days_raw)} | {pct(r.positive_day_rate_raw)} | ${fnum(r.avg_daily_pnl_raw)} | ${fnum(r.median_daily_pnl_raw)} | ${fnum(r.best_day_raw)} | ${fnum(r.worst_day_raw)} | {int(r.max_losing_day_streak_raw)} | {fnum(r.avg_trades_per_active_day_raw)} | {fnum(r.avg_wins_per_active_day_raw)} | {fnum(r.median_wins_per_active_day_raw)} | {int(r.max_wins_in_day_raw)} |")

    lines += ["", "## Weekly — raw", "",
        "| Partition | Active weeks | Positive-week rate | Avg PnL/week | Median | Best week | Worst week | Losing-week streak | Avg trades/active week | Avg wins/active week |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in port.iterrows():
        lines.append(f"| {r.partition} | {int(r.active_weeks_raw)} | {pct(r.positive_week_rate_raw)} | ${fnum(r.avg_weekly_pnl_raw)} | ${fnum(r.median_weekly_pnl_raw)} | ${fnum(r.best_week_raw)} | ${fnum(r.worst_week_raw)} | {int(r.max_losing_week_streak_raw)} | {fnum(r.avg_trades_per_active_week_raw)} | {fnum(r.avg_wins_per_active_week_raw)} |")

    lines += ["", "## Weekly — 5bps stress", "",
        "| Partition | Positive-week rate | Avg PnL/week | Median | Best week | Worst week | Losing-week streak |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in port.iterrows():
        lines.append(f"| {r.partition} | {pct(r.positive_week_rate_stress)} | ${fnum(r.avg_weekly_pnl_stress)} | ${fnum(r.median_weekly_pnl_stress)} | ${fnum(r.best_week_stress)} | ${fnum(r.worst_week_stress)} | {int(r.max_losing_week_streak_stress)} |")

    lines += ["", "## Habitat breakdown — raw", "",
        "| Partition | Habitat | N | Trades/wk | WR | PF | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Positive-week rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    names = {"03UTC_EXPANSION":"03UTC/R420 parent", "15UTC_EXPANSION":"15UTC/R360 parent", "18UTC_MATURE":"18UTC/R240 parent + H2 entries"}
    for _, r in zones.iterrows():
        lines.append(f"| {r.partition} | {names.get(r.zone,r.zone)} | {int(r.n_raw)} | {fnum(r.trades_per_week_raw)} | {pct(r.wr_raw)} | {fnum(r.pf_raw)} | ${fnum(r.net_raw)} | ${fnum(r.max_drawdown_raw)} | {int(r.max_loss_streak_raw)} | ${fnum(r.max_loss_trade_raw)} | ${fnum(r.min_win_trade_raw)} | {pct(r.positive_week_rate_raw)} |")

    OUT_MD.write_text("\n".join(lines)+"\n", encoding="utf-8")
    OUT_STATUS.write_text("SOL_LONG_THREE_ZONE_A25_METRICS_AUDIT_COMPLETE\n", encoding="utf-8")
    print("SOL_LONG_THREE_ZONE_A25_METRICS_AUDIT_COMPLETE")

if __name__ == "__main__":
    main()
