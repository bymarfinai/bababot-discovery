#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_H04_OOS_FAILURE_ANATOMY_A1"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_SHIFT = ROOT / f"{PFX}_FeatureShift.csv"
OUT_TERCILES = ROOT / f"{PFX}_FeatureTercileEconomics.csv"
OUT_PATH = ROOT / f"{PFX}_PathSummary.csv"
OUT_CALENDAR = ROOT / f"{PFX}_CalendarEconomics.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (240, 255, 270, 285)
RULE = "EFF_LOW__RANGE_HIGH"
LOOKBACK = 360
HOLD = 240
PARTITIONS = ("external", "development", "reference_validation")

FEATURES = (
    "raw_efficiency",
    "raw_range",
    "drive_return",
    "eff_pct",
    "range_pct",
    "ret_24h",
    "ret_72h",
    "ret_7d",
    "range_24h",
    "range_72h",
    "loc_24h",
    "loc_7d",
)


def stats_from_df(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return engine.summarize(np.array([]), np.array([]))
    return engine.summarize(df.net.to_numpy(float), df.gross.to_numpy(float))


def qtile(x: pd.Series, q: float) -> float:
    z = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    return float(np.quantile(z, q)) if len(z) else np.nan


def fmt_pct(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def fmt_num(x: float, digits: int = 4) -> str:
    return "nan" if not np.isfinite(x) else f"{float(x):.{digits}f}"


def fmt_money(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def window_metrics(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    entry_ix: int,
    bars: int,
) -> tuple[float, float, float]:
    start = entry_ix - bars
    if start < 0:
        return np.nan, np.nan, np.nan
    start_open = float(opens[start])
    entry_open = float(opens[entry_ix])
    if start_open <= 0 or entry_open <= 0:
        return np.nan, np.nan, np.nan
    ret = entry_open / start_open - 1.0
    h = float(np.max(highs[start:entry_ix]))
    l = float(np.min(lows[start:entry_ix]))
    width = h - l
    realized_range = width / start_open if width > 0 else 0.0
    location = (entry_open - l) / width if width > 0 else np.nan
    return ret, realized_range, float(np.clip(location, 0.0, 1.0)) if np.isfinite(location) else np.nan


def build_cohort(x5: pd.DataFrame) -> pd.DataFrame:
    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    pieces: list[pd.DataFrame] = []

    for clock in CLOCKS:
        frame = engine.state_frame(x5, clock, LOOKBACK)
        masks = engine.masks_for_frame(frame)
        exit_ts, valid, returns = engine.hold_returns(x5, frame, HOLD)
        entry_ts = pd.DatetimeIndex(frame.entry_ts)
        pre_ts = pd.DatetimeIndex(frame.pre_ts)
        entry_ix = frame.entry_ix.to_numpy(int)
        pre_ix = frame.pre_ix.to_numpy(int)

        partition_name = np.full(len(frame), "", dtype=object)
        in_formal_partition = np.zeros(len(frame), dtype=bool)
        for part in PARTITIONS:
            a, z = base.PARTS[part]
            m = valid & (pre_ts >= a) & (entry_ts >= a) & (exit_ts < z)
            partition_name[m] = part
            in_formal_partition |= m

        selected = in_formal_partition & masks[RULE]
        idxs = np.flatnonzero(selected)
        rows = []
        for k in idxs:
            ei = int(entry_ix[k])
            pi = int(pre_ix[k])
            xi = ei + HOLD // engine.BAR_MIN
            if pi < 0 or xi >= len(x5) or xi <= ei:
                continue

            path = opens[pi:ei + 1]
            diffs = np.diff(path)
            denom = float(np.abs(diffs).sum())
            raw_eff = abs(float(path[-1] - path[0])) / denom if denom > 0 else np.nan
            pre_high = float(np.max(highs[pi:ei]))
            pre_low = float(np.min(lows[pi:ei]))
            raw_range = (pre_high - pre_low) / float(path[0]) if path[0] > 0 else np.nan

            ret24, rr24, loc24 = window_metrics(opens, highs, lows, ei, 24 * 60 // engine.BAR_MIN)
            ret72, rr72, _ = window_metrics(opens, highs, lows, ei, 72 * 60 // engine.BAR_MIN)
            ret7d, _, loc7d = window_metrics(opens, highs, lows, ei, 7 * 24 * 60 // engine.BAR_MIN)

            entry_price = float(opens[ei])
            exit_price = float(opens[xi])
            gross_return = exit_price / entry_price - 1.0
            future_high = float(np.max(highs[ei:xi]))
            future_low = float(np.min(lows[ei:xi]))
            mfe = future_high / entry_price - 1.0
            mae = future_low / entry_price - 1.0
            gross = engine.NOTIONAL * gross_return
            net = gross - engine.FEE

            rows.append({
                "partition": partition_name[k],
                "clock_utc": engine.hhmm(clock),
                "clock_wib": engine.wib(clock),
                "entry_ts": entry_ts[k],
                "exit_ts": exit_ts[k],
                "year": int(entry_ts[k].year),
                "month": int(entry_ts[k].month),
                "weekday": entry_ts[k].day_name(),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "gross_return": gross_return,
                "gross": gross,
                "net": net,
                "raw_efficiency": raw_eff,
                "raw_range": raw_range,
                "drive_return": float(frame.drive_return.iloc[k]),
                "eff_pct": float(frame.eff_pct.iloc[k]),
                "range_pct": float(frame.range_pct.iloc[k]),
                "ret_24h": ret24,
                "ret_72h": ret72,
                "ret_7d": ret7d,
                "range_24h": rr24,
                "range_72h": rr72,
                "loc_24h": loc24,
                "loc_7d": loc7d,
                "mfe_pct": mfe,
                "mae_pct": mae,
                "giveback_pct": mfe - gross_return,
                "mfe_ge_1_net_loss": bool(mfe >= 0.01 and net <= 0),
                "mfe_ge_2_net_loss": bool(mfe >= 0.02 and net <= 0),
            })
        if rows:
            pieces.append(pd.DataFrame(rows))

    if not pieces:
        raise RuntimeError("frozen H04 cohort is empty")
    out = pd.concat(pieces, ignore_index=True).sort_values(["entry_ts", "clock_utc"]).reset_index(drop=True)
    return out


def frozen_terciles(trades: pd.DataFrame) -> dict[str, tuple[float, float]]:
    dev = trades[trades.partition == "development"]
    bounds: dict[str, tuple[float, float]] = {}
    for feature in FEATURES:
        q1 = qtile(dev[feature], 1 / 3)
        q2 = qtile(dev[feature], 2 / 3)
        if not np.isfinite(q1) or not np.isfinite(q2):
            raise RuntimeError(f"cannot freeze terciles for {feature}")
        bounds[feature] = (q1, q2)
    return bounds


def label_bins(values: pd.Series, q1: float, q2: float) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    out = pd.Series(index=values.index, dtype="object")
    out.loc[x <= q1] = "LOW"
    out.loc[(x > q1) & (x <= q2)] = "MID"
    out.loc[x > q2] = "HIGH"
    out.loc[~np.isfinite(x)] = "NA"
    return out


def psi_for_group(group: pd.DataFrame, feature: str, q1: float, q2: float) -> float:
    dev = group.attrs.get("development_reference")
    if dev is None:
        raise RuntimeError("missing development reference for PSI")
    dev_bins = label_bins(dev[feature], q1, q2)
    grp_bins = label_bins(group[feature], q1, q2)
    labels = ("LOW", "MID", "HIGH")
    eps = 1e-6
    d = np.array([(dev_bins == b).mean() for b in labels], float)
    g = np.array([(grp_bins == b).mean() for b in labels], float)
    d = np.clip(d, eps, None); g = np.clip(g, eps, None)
    d = d / d.sum(); g = g / g.sum()
    return float(np.sum((g - d) * np.log(g / d)))


def feature_shift(trades: pd.DataFrame, bounds: dict[str, tuple[float, float]]) -> pd.DataFrame:
    dev = trades[trades.partition == "development"].copy()
    groups = {
        "external": trades[trades.partition == "external"],
        "development": dev,
        "reference_validation": trades[trades.partition == "reference_validation"],
        "2025": trades[trades.year == 2025],
        "2026": trades[trades.year == 2026],
    }
    rows = []
    for feature in FEATURES:
        q1, q2 = bounds[feature]
        for name, g0 in groups.items():
            g = g0.copy()
            vals = pd.to_numeric(g[feature], errors="coerce").dropna()
            g.attrs["development_reference"] = dev
            rows.append({
                "feature": feature,
                "cohort": name,
                "n": int(len(vals)),
                "median": float(vals.median()) if len(vals) else np.nan,
                "q25": float(vals.quantile(.25)) if len(vals) else np.nan,
                "q75": float(vals.quantile(.75)) if len(vals) else np.nan,
                "dev_q33": q1,
                "dev_q67": q2,
                "psi_vs_development": 0.0 if name == "development" else psi_for_group(g, feature, q1, q2),
            })
    return pd.DataFrame(rows)


def tercile_economics(trades: pd.DataFrame, bounds: dict[str, tuple[float, float]]) -> pd.DataFrame:
    rows = []
    for feature in FEATURES:
        q1, q2 = bounds[feature]
        bins = label_bins(trades[feature], q1, q2)
        for part in PARTITIONS:
            part_mask = trades.partition == part
            for band in ("LOW", "MID", "HIGH"):
                z = trades[part_mask & (bins == band)]
                s = stats_from_df(z)
                rows.append({
                    "feature": feature,
                    "dev_q33": q1,
                    "dev_q67": q2,
                    "partition": part,
                    "tercile": band,
                    **s,
                })
    return pd.DataFrame(rows)


def path_stats(df: pd.DataFrame) -> dict:
    s = stats_from_df(df)
    return {
        **s,
        "median_mfe_pct": float(df.mfe_pct.median()) if len(df) else np.nan,
        "median_mae_pct": float(df.mae_pct.median()) if len(df) else np.nan,
        "median_giveback_pct": float(df.giveback_pct.median()) if len(df) else np.nan,
        "mfe_ge_1_net_loss_rate": float(df.mfe_ge_1_net_loss.mean()) if len(df) else np.nan,
        "mfe_ge_2_net_loss_rate": float(df.mfe_ge_2_net_loss.mean()) if len(df) else np.nan,
    }


def path_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTITIONS:
        z = trades[trades.partition == part]
        rows.append({"split_type": "partition", "split_value": part, **path_stats(z)})
    for year in sorted(trades.year.unique()):
        z = trades[trades.year == year]
        rows.append({"split_type": "year", "split_value": str(int(year)), **path_stats(z)})
    return pd.DataFrame(rows)


def calendar_economics(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dimension in ("clock_wib", "weekday", "month"):
        for part in PARTITIONS:
            p = trades[trades.partition == part]
            for value, z in p.groupby(dimension, sort=True):
                rows.append({
                    "dimension": dimension,
                    "partition": part,
                    "value": str(value),
                    **stats_from_df(z),
                    "median_mfe_pct": float(z.mfe_pct.median()),
                    "median_mae_pct": float(z.mae_pct.median()),
                    "median_giveback_pct": float(z.giveback_pct.median()),
                })
    return pd.DataFrame(rows)


def main() -> None:
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    trades = build_cohort(x5)
    bounds = frozen_terciles(trades)
    shift = feature_shift(trades, bounds)
    terciles = tercile_economics(trades, bounds)
    paths = path_summary(trades)
    calendar = calendar_economics(trades)

    trades.to_csv(OUT_TRADES, index=False)
    shift.to_csv(OUT_SHIFT, index=False)
    terciles.to_csv(OUT_TERCILES, index=False)
    paths.to_csv(OUT_PATH, index=False)
    calendar.to_csv(OUT_CALENDAR, index=False)

    status = "SOL_H04_OOS_FAILURE_ANATOMY_A1_DIAGNOSTICS_COMPLETE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# SOL H04 OOS Failure Anatomy A1 — Diagnostic Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Frozen cohort: **{RULE} / LB{LOOKBACK} / hold{HOLD}m**, anchors 11:00/11:15/11:30/11:45 WIB.",
        "No entry, exit, threshold, rule, lookback, hold, or anchor was optimized in this experiment.",
        "",
        "## Frozen-cohort path economics",
        "",
        "| Split | N | WR | Net | Exp | PF | DD | LS | Med MFE | Med MAE | Med giveback | +1% MFE→loss | +2% MFE→loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in paths.itertuples(index=False):
        lines.append(
            f"| {r.split_type}:{r.split_value} | {int(r.trades)} | {fmt_pct(r.win_rate)} | {fmt_money(r.net_pnl)} | "
            f"{fmt_money(r.expectancy)} | {r.pf:.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{fmt_pct(r.median_mfe_pct)} | {fmt_pct(r.median_mae_pct)} | {fmt_pct(r.median_giveback_pct)} | "
            f"{fmt_pct(r.mfe_ge_1_net_loss_rate)} | {fmt_pct(r.mfe_ge_2_net_loss_rate)} |"
        )

    lines += [
        "",
        "## Pre-entry distribution-shift overview",
        "",
        "PSI uses Development-frozen tercile bins and is descriptive only.",
        "",
        "| Feature | Cohort | N | Median | Q25 | Q75 | PSI vs Dev |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    focus = shift[shift.cohort.isin(["external", "development", "reference_validation", "2025", "2026"])]
    for r in focus.itertuples(index=False):
        lines.append(
            f"| {r.feature} | {r.cohort} | {int(r.n)} | {fmt_num(r.median)} | {fmt_num(r.q25)} | "
            f"{fmt_num(r.q75)} | {fmt_num(r.psi_vs_development, 3)} |"
        )

    lines += [
        "",
        "## Output files",
        "",
        f"- `{OUT_TRADES.name}` — exact frozen H04 trade cohort plus preregistered features and path diagnostics.",
        f"- `{OUT_SHIFT.name}` — distribution shifts and PSI.",
        f"- `{OUT_TERCILES.name}` — economics inside Development-frozen feature terciles.",
        f"- `{OUT_PATH.name}` — partition/year path degradation diagnostics.",
        f"- `{OUT_CALENDAR.name}` — anchor/weekday/month diagnostics.",
        "",
        f"**Status: {status}**",
        "",
        "This run intentionally does not promote a filter or force an anatomy label. Scientific interpretation is a separate persisted verdict under the preregistered labels.",
        "",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
