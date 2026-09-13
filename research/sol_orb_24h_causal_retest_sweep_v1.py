#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ORB_24H_CAUSAL_RETEST_SWEEP_V1"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv"
OUT_STRUCT = ROOT / f"{PFX}_StructureByHour.csv"
OUT_ECON = ROOT / f"{PFX}_EconomicsByHour.csv"
OUT_YEAR = ROOT / f"{PFX}_YearStability.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

DEV_START, DEV_END = base.PARTS["development"]
BAR = pd.Timedelta(minutes=5)
HORIZONS = (15, 30, 60, 120)
NOTIONAL = 500.0
ROUNDTRIP_COST_PCT = 0.15


def row_at(x: pd.DataFrame, ts: pd.Timestamp):
    try:
        r = x.loc[ts]
    except KeyError:
        return None
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    return r


def close_after(x: pd.DataFrame, decision_ts: pd.Timestamp, minutes: int):
    ts = decision_ts + pd.Timedelta(minutes=minutes) - BAR
    r = row_at(x, ts)
    return np.nan if r is None else float(r.close)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).fillna(0.0)
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    dd = peak - eq
    return float(dd.max())


def detect_one(x5: pd.DataFrame, start: pd.Timestamp):
    # Require the three complete ORB bars.
    orb_times = [start + i * BAR for i in range(3)]
    orb_rows = [row_at(x5, t) for t in orb_times]
    if any(r is None for r in orb_rows):
        return None

    oh = max(float(r.high) for r in orb_rows)
    ol = min(float(r.low) for r in orb_rows)
    om = (oh + ol) / 2.0
    if oh <= ol:
        return None

    # Breakout habitat is frozen to the anchor hour: HH:15 through HH:55.
    breakout_ts = None
    breakout_row = None
    for i in range(3, 12):
        ts = start + i * BAR
        r = row_at(x5, ts)
        if r is None:
            continue
        if float(r.close) > oh:
            breakout_ts = ts
            breakout_row = r
            break

    out = {
        "session_start": start,
        "hour_utc": int(start.hour),
        "hour_wib": int((start.hour + 7) % 24),
        "year": int(start.year),
        "orb_high": oh,
        "orb_low": ol,
        "orb_mid": om,
        "orb_range_pct": (oh / float(orb_rows[0].open) - ol / float(orb_rows[0].open)) * 100.0,
        "breakout_time": pd.NaT,
        "retest_time": pd.NaT,
        "acceptance_time": pd.NaT,
        "has_breakout": False,
        "has_retest": False,
        "has_acceptance_after_retest": False,
        "entry_price": np.nan,
        "decision_time": pd.NaT,
    }
    for h in HORIZONS:
        out[f"gross_ret_{h}m_pct"] = np.nan
        out[f"net_ret_{h}m_pct"] = np.nan
        out[f"pnl_{h}m_usd"] = np.nan

    if breakout_ts is None:
        return out

    out["has_breakout"] = True
    out["breakout_time"] = breakout_ts

    # Full preregistered 30m window may cross the next UTC hour.
    post = []
    for j in range(1, 7):
        ts = breakout_ts + j * BAR
        r = row_at(x5, ts)
        if r is not None:
            post.append((ts, r))

    retest_ts = None
    retest_row = None
    for ts, r in post:
        if float(r.low) <= oh and float(r.close) >= om:
            retest_ts = ts
            retest_row = r
            break

    if retest_ts is None:
        return out

    out["has_retest"] = True
    out["retest_time"] = retest_ts
    out["entry_price"] = oh
    decision_ts = retest_ts + BAR
    out["decision_time"] = decision_ts

    # Acceptance is diagnostic only and must occur strictly after the retest bar.
    for ts, r in post:
        if ts > retest_ts and float(r.close) > oh:
            out["has_acceptance_after_retest"] = True
            out["acceptance_time"] = ts
            break

    for h in HORIZONS:
        xp = close_after(x5, decision_ts, h)
        if not np.isfinite(xp):
            continue
        gross = (xp / oh - 1.0) * 100.0
        net = gross - ROUNDTRIP_COST_PCT
        out[f"gross_ret_{h}m_pct"] = gross
        out[f"net_ret_{h}m_pct"] = net
        out[f"pnl_{h}m_usd"] = net / 100.0 * NOTIONAL

    return out


def collect(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= DEV_START) & (x5.index < DEV_END)].copy()
    # Generate session anchors from dates actually present in Development.
    days = pd.Index(q.index.normalize().unique()).sort_values()
    rows = []
    for day in days:
        if day.weekday() >= 5:
            continue
        for hour in range(24):
            start = day + pd.Timedelta(hours=hour)
            d = detect_one(x5, start)
            if d is not None:
                rows.append(d)
    return pd.DataFrame(rows)


def summarize_structure(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for hour, g in ev.groupby("hour_utc"):
        n = len(g)
        nb = int(g.has_breakout.sum())
        nr = int(g.has_retest.sum())
        na = int(g.has_acceptance_after_retest.sum())
        rows.append({
            "hour_utc": int(hour),
            "hour_wib": int((hour + 7) % 24),
            "sessions": n,
            "breakouts": nb,
            "breakout_rate": nb / n if n else np.nan,
            "causal_retests": nr,
            "retest_rate_all_sessions": nr / n if n else np.nan,
            "retest_rate_given_breakout": nr / nb if nb else np.nan,
            "later_acceptances": na,
            "accept_rate_given_retest": na / nr if nr else np.nan,
        })
    return pd.DataFrame(rows).sort_values("hour_utc")


def summarize_econ(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    z = ev[ev.has_retest].copy()
    for hour, g in z.groupby("hour_utc"):
        for h in HORIZONS:
            col = f"pnl_{h}m_usd"
            netcol = f"net_ret_{h}m_pct"
            grosscol = f"gross_ret_{h}m_pct"
            gg = g.dropna(subset=[col]).sort_values("decision_time")
            pnls = gg[col].astype(float)
            rows.append({
                "hour_utc": int(hour),
                "hour_wib": int((hour + 7) % 24),
                "exit_minutes": h,
                "n": len(gg),
                "gross_hit": float((gg[grosscol] > 0).mean()) if len(gg) else np.nan,
                "net_wr": float((gg[netcol] > 0).mean()) if len(gg) else np.nan,
                "gross_mean_pct": float(gg[grosscol].mean()) if len(gg) else np.nan,
                "net_mean_pct": float(gg[netcol].mean()) if len(gg) else np.nan,
                "net_pnl_usd": float(pnls.sum()) if len(gg) else np.nan,
                "expectancy_usd": float(pnls.mean()) if len(gg) else np.nan,
                "profit_factor": profit_factor(pnls),
                "max_dd_usd": max_drawdown(pnls),
                "max_loss_streak": max_loss_streak(pnls),
            })
    return pd.DataFrame(rows).sort_values(["hour_utc", "exit_minutes"])


def summarize_year(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    z = ev[ev.has_retest].copy()
    for (hour, year), g in z.groupby(["hour_utc", "year"]):
        for h in HORIZONS:
            col = f"pnl_{h}m_usd"
            netcol = f"net_ret_{h}m_pct"
            gg = g.dropna(subset=[col]).sort_values("decision_time")
            pnls = gg[col].astype(float)
            rows.append({
                "hour_utc": int(hour),
                "hour_wib": int((hour + 7) % 24),
                "year": int(year),
                "exit_minutes": h,
                "n": len(gg),
                "net_wr": float((gg[netcol] > 0).mean()) if len(gg) else np.nan,
                "net_pnl_usd": float(pnls.sum()) if len(gg) else np.nan,
                "expectancy_usd": float(pnls.mean()) if len(gg) else np.nan,
                "profit_factor": profit_factor(pnls),
            })
    return pd.DataFrame(rows).sort_values(["hour_utc", "exit_minutes", "year"])


def pfmt(x):
    if pd.isna(x):
        return "-"
    if np.isinf(x):
        return "inf"
    return f"{float(x):.3f}"


def main():
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = collect(x5)
    if ev.empty:
        raise RuntimeError("no sessions generated")
    ev.to_csv(OUT_EVENTS, index=False)

    st = summarize_structure(ev)
    ec = summarize_econ(ev)
    yr = summarize_year(ev)
    st.to_csv(OUT_STRUCT, index=False)
    ec.to_csv(OUT_ECON, index=False)
    yr.to_csv(OUT_YEAR, index=False)

    lines = [
        "# SOL ORB 24H Causal Retest Sweep v1 — Development",
        "",
        f"- Data coverage: {coverage:.6%}",
        f"- Development sessions evaluated: **{len(ev)}**",
        "- LONG only; 15m ORB; breakout must occur inside anchor hour.",
        "- E2 enters every causal ORB-high retest, independent of future acceptance.",
        f"- Economics: ${NOTIONAL:.0f}/trade, {ROUNDTRIP_COST_PCT:.2f}% round-trip cost, fixed time exits only.",
        "- Reference/OOS remains closed.",
        "",
        "## Structure map",
        "",
        "| UTC | WIB | Sessions | Breakout | Retest | Accept after retest |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for r in st.itertuples(index=False):
        lines.append(
            f"| {r.hour_utc:02d}:00 | {r.hour_wib:02d}:00 | {int(r.sessions)} | "
            f"{int(r.breakouts)} ({r.breakout_rate:.1%}) | {int(r.causal_retests)} ({r.retest_rate_all_sessions:.1%}) | "
            f"{int(r.later_acceptances)} ({r.accept_rate_given_retest:.1%} of retests) |"
        )

    for h in HORIZONS:
        lines += [
            "",
            f"## Economics — fixed +{h}m exit",
            "",
            "| UTC | WIB | N | Net WR | Net PnL | Exp/trade | PF | Max DD | Max LS |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        zz = ec[ec.exit_minutes == h].sort_values("hour_utc")
        for r in zz.itertuples(index=False):
            lines.append(
                f"| {r.hour_utc:02d}:00 | {r.hour_wib:02d}:00 | {int(r.n)} | {r.net_wr:.1%} | "
                f"${r.net_pnl_usd:.2f} | ${r.expectancy_usd:.3f} | {pfmt(r.profit_factor)} | "
                f"${r.max_dd_usd:.2f} | {int(r.max_loss_streak)} |"
            )

    # Year-stable diagnostic: all three Development years positive net PnL and PF>1.
    lines += ["", "## Three-year stability diagnostic", ""]
    stable_rows = []
    for (hour, h), g in yr.groupby(["hour_utc", "exit_minutes"]):
        years = set(g.year.astype(int).tolist())
        stable = years.issuperset({2022, 2023, 2024}) and bool((g.net_pnl_usd > 0).all()) and bool((g.profit_factor > 1.0).all())
        if stable:
            pooled = ec[(ec.hour_utc == hour) & (ec.exit_minutes == h)].iloc[0]
            stable_rows.append((int(hour), int((hour + 7) % 24), int(h), int(pooled.n), float(pooled.expectancy_usd), float(pooled.profit_factor), float(pooled.net_pnl_usd)))
    if stable_rows:
        lines += ["| UTC | WIB | Exit | N | Exp/trade | PF | Net PnL |", "|---:|---:|---:|---:|---:|---:|---:|"]
        for hour, wib, h, n, ex, pf, pnl in sorted(stable_rows, key=lambda x: (-x[4], x[0], x[2])):
            lines.append(f"| {hour:02d}:00 | {wib:02d}:00 | +{h}m | {n} | ${ex:.3f} | {pfmt(pf)} | ${pnl:.2f} |")
    else:
        lines.append("No hour/exit combination was positive with PF>1 in all three Development years.")

    lines += [
        "",
        "## Boundary",
        "",
        "This is a Development-only 24h map. It corrects future-acceptance selection bias for E2 by entering every causally eligible retest. It does not authorize hour cherry-picking, threshold tuning, or opening Reference/OOS. Any hour selection derived from this map requires a separately preregistered confirmation step.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("COMPLETE_DEVELOPMENT_24H_CAUSAL_RETEST_SWEEP\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
