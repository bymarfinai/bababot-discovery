#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURE_DISCOVERY_B1"
SYMBOL = "SOLUSDT"
DEV_START = pd.Timestamp("2022-01-01", tz="UTC")
DEV_END = pd.Timestamp("2025-01-01", tz="UTC")
LOAD_START = pd.Timestamp("2021-12-01", tz="UTC")
LOAD_END = pd.Timestamp("2025-01-01 08:00", tz="UTC")
BASE = "https://data.binance.vision/data/futures/um"
HORIZONS = (60, 120, 240, 480)
COOLDOWN = pd.Timedelta(hours=8)

VARIANTS = (
    ("IMPULSE_PULLBACK", 3), ("IMPULSE_PULLBACK", 4), ("IMPULSE_PULLBACK", 6),
    ("COMPRESSION_EXPANSION", 4), ("COMPRESSION_EXPANSION", 6), ("COMPRESSION_EXPANSION", 8),
    ("SWEEP_RECLAIM", 8), ("SWEEP_RECLAIM", 12), ("SWEEP_RECLAIM", 20),
)


def urls() -> list[str]:
    out: list[str] = []
    month = LOAD_START.normalize().replace(day=1)
    last_full_month = pd.Timestamp("2024-12-01", tz="UTC")
    while month <= last_full_month:
        ym = month.strftime("%Y-%m")
        out.append(f"{BASE}/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        month += pd.offsets.MonthBegin(1)
    out.append(f"{BASE}/daily/klines/{SYMBOL}/5m/{SYMBOL}-5m-2025-01-01.zip")
    return out


def fetch_one(url: str) -> pd.DataFrame | None:
    request = urllib.request.Request(url, headers={"User-Agent": "bababot-sol-structure-b1/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            return None
        with archive.open(names[0]) as fh:
            return pd.read_csv(
                fh, header=None, usecols=[0, 1, 2, 3, 4],
                names=["ts", "open", "high", "low", "close"],
            )


def load5() -> tuple[pd.DataFrame, float]:
    frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_one, url) for url in urls()]
        for future in as_completed(futures):
            frame = future.result()
            if frame is not None and len(frame):
                frames.append(frame)
    if not frames:
        raise RuntimeError("no SOLUSDT 5m data")
    x = pd.concat(frames, ignore_index=True)
    raw_ts = pd.to_numeric(x.ts, errors="coerce")
    raw_ts = np.where(raw_ts > 100_000_000_000_000, raw_ts / 1000.0, raw_ts)
    x["ts"] = pd.to_datetime(raw_ts, unit="ms", utc=True, errors="coerce")
    for column in ("open", "high", "low", "close"):
        x[column] = pd.to_numeric(x[column], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= LOAD_START) & (x.ts < LOAD_END)].set_index("ts")
    expected = int((x.index[-1] - x.index[0]) / pd.Timedelta(minutes=5)) + 1
    coverage = len(x) / expected
    if coverage < .995:
        raise RuntimeError(f"SOLUSDT 5m coverage too low: {coverage:.6f}")
    return x, coverage


def bars15(x5: pd.DataFrame) -> pd.DataFrame:
    x = x5.resample("15min", label="right", closed="left").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), count=("close", "count"),
    )
    x = x[x["count"] == 3].drop(columns="count")
    prior_close = x.close.shift(1)
    tr = pd.concat([
        x.high - x.low,
        (x.high - prior_close).abs(),
        (x.low - prior_close).abs(),
    ], axis=1).max(axis=1)
    x["atr"] = tr.shift(1).rolling(48, min_periods=48).mean()
    return x


def _event(family: str, parameter: int, ts: pd.Timestamp, direction: int,
           ref: float, atr: float, detail: dict) -> dict:
    return {
        "family": family, "variant": f"{family}_{parameter}", "parameter": parameter,
        "signal_ts": ts, "direction": direction, "reference": ref, "atr": atr, **detail,
    }


def detect_impulse_pullback(x: pd.DataFrame, length: int) -> list[dict]:
    rows: list[dict] = []
    start = max(50, length + 3)
    for i in range(start, len(x)):
        ts = x.index[i]
        if not (DEV_START <= ts < DEV_END):
            continue
        atr = float(x.atr.iloc[i])
        if not np.isfinite(atr) or atr <= 0:
            continue
        origin = float(x.close.iloc[i - length - 2])
        impulse_end = float(x.close.iloc[i - 2])
        impulse = impulse_end - origin
        direction = 1 if impulse > 0 else -1
        path = np.abs(np.diff(x.close.iloc[i - length - 2:i - 1].to_numpy(float))).sum()
        efficiency = abs(impulse) / path if path > 0 else 0.0
        pullback = float(x.close.iloc[i]) - impulse_end
        depth = abs(pullback) / abs(impulse) if impulse != 0 else np.inf
        opposite = pullback * direction < 0
        pb = x.iloc[i - 1:i + 1]
        origin_intact = float(pb.low.min()) > origin if direction > 0 else float(pb.high.max()) < origin
        if abs(impulse) >= 1.2 * atr and efficiency >= .65 and opposite and .20 <= depth <= .60 and origin_intact:
            rows.append(_event("IMPULSE_PULLBACK", length, ts, direction, float(x.close.iloc[i]), atr,
                               {"strength": abs(impulse) / atr, "quality": efficiency, "depth": depth}))
    return rows


def detect_compression_expansion(x: pd.DataFrame, length: int) -> list[dict]:
    rolling_range = x.high.rolling(length).max() - x.low.rolling(length).min()
    historical_median = rolling_range.shift(length).rolling(40, min_periods=40).median()
    rows: list[dict] = []
    for i in range(max(60, 2 * length + 40), len(x)):
        ts = x.index[i]
        if not (DEV_START <= ts < DEV_END):
            continue
        atr = float(x.atr.iloc[i])
        comp_range = float(rolling_range.iloc[i - 1])
        median_range = float(historical_median.iloc[i - 1])
        if not all(np.isfinite(v) and v > 0 for v in (atr, comp_range, median_range)):
            continue
        comp = x.iloc[i - length:i]
        high, low = float(comp.high.max()), float(comp.low.min())
        bar = x.iloc[i]
        bar_range = float(bar.high - bar.low)
        body_ratio = abs(float(bar.close - bar.open)) / bar_range if bar_range > 0 else 0.0
        direction = 1 if float(bar.close) > high else (-1 if float(bar.close) < low else 0)
        if comp_range <= .65 * median_range and direction and body_ratio >= .60 and bar_range >= .80 * atr:
            rows.append(_event("COMPRESSION_EXPANSION", length, ts, direction, float(bar.close), atr,
                               {"strength": bar_range / atr, "quality": body_ratio,
                                "depth": comp_range / median_range}))
    return rows


def detect_sweep_reclaim(x: pd.DataFrame, lookback: int) -> list[dict]:
    rows: list[dict] = []
    for i in range(max(50, lookback + 1), len(x)):
        ts = x.index[i]
        if not (DEV_START <= ts < DEV_END):
            continue
        atr = float(x.atr.iloc[i])
        if not np.isfinite(atr) or atr <= 0:
            continue
        prior = x.iloc[i - lookback:i]
        high, low = float(prior.high.max()), float(prior.low.min())
        bar = x.iloc[i]
        bar_range = float(bar.high - bar.low)
        if bar_range <= 0:
            continue
        body = abs(float(bar.close - bar.open))
        lower_wick = min(float(bar.open), float(bar.close)) - float(bar.low)
        upper_wick = float(bar.high) - max(float(bar.open), float(bar.close))
        close_location = (float(bar.close) - float(bar.low)) / bar_range
        bull = float(bar.low) < low and float(bar.close) > low
        bear = float(bar.high) > high and float(bar.close) < high
        if bull == bear:
            continue
        direction = 1 if bull else -1
        dominant = lower_wick >= 1.5 * max(body, 1e-12) and close_location >= .55 if bull else (
            upper_wick >= 1.5 * max(body, 1e-12) and close_location <= .45)
        if dominant:
            swept = (low - float(bar.low)) if bull else (float(bar.high) - high)
            wick = lower_wick if bull else upper_wick
            rows.append(_event("SWEEP_RECLAIM", lookback, ts, direction, float(bar.close), atr,
                               {"strength": swept / atr, "quality": wick / max(body, 1e-12),
                                "depth": close_location if bull else 1.0 - close_location}))
    return rows


def cooldown(events: list[dict]) -> list[dict]:
    kept: list[dict] = []
    last: dict[tuple[str, int], pd.Timestamp] = {}
    for event in sorted(events, key=lambda row: row["signal_ts"]):
        key = (event["variant"], event["direction"])
        if key not in last or event["signal_ts"] - last[key] >= COOLDOWN:
            kept.append(event)
            last[key] = event["signal_ts"]
    return kept


def path_metrics(x5: pd.DataFrame, event: dict, minutes: int) -> dict:
    ts, ref, atr, direction = event["signal_ts"], event["reference"], event["atr"], event["direction"]
    path = x5[(x5.index >= ts) & (x5.index < ts + pd.Timedelta(minutes=minutes))]
    if len(path) != minutes // 5:
        return {"close_r": np.nan, "mfe": np.nan, "mae": np.nan, "barrier": "MISSING"}
    if direction > 0:
        mfe = (float(path.high.max()) - ref) / atr
        mae = (ref - float(path.low.min())) / atr
        favorable, adverse = path.high >= ref + atr, path.low <= ref - atr
        close_r = (float(path.close.iloc[-1]) - ref) / atr
    else:
        mfe = (ref - float(path.low.min())) / atr
        mae = (float(path.high.max()) - ref) / atr
        favorable, adverse = path.low <= ref - atr, path.high >= ref + atr
        close_r = (ref - float(path.close.iloc[-1])) / atr
    barrier = "UNRESOLVED"
    for fav, adv in zip(favorable.to_numpy(bool), adverse.to_numpy(bool)):
        if fav and adv:
            barrier = "DUAL_TOUCH"
            break
        if fav:
            barrier = "WIN"
            break
        if adv:
            barrier = "LOSS"
            break
    return {"close_r": close_r, "mfe": max(0.0, mfe), "mae": max(0.0, mae), "barrier": barrier}


def attach_outcomes(x5: pd.DataFrame, events: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for event in events:
        row = dict(event)
        row["year"] = event["signal_ts"].year
        row["hour_utc"] = event["signal_ts"].hour
        for minutes in HORIZONS:
            metrics = path_metrics(x5, event, minutes)
            for key, value in metrics.items():
                row[f"h{minutes}_{key}"] = value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["family", "parameter", "signal_ts"]).reset_index(drop=True)


def summarize_group(group: pd.DataFrame, horizon: int) -> dict:
    barrier = group[f"h{horizon}_barrier"]
    wins = int((barrier == "WIN").sum())
    losses = int((barrier == "LOSS").sum())
    resolved = wins + losses
    event_ratio = group[f"h{horizon}_mfe"] / group[f"h{horizon}_mae"].clip(lower=1e-6)
    return {
        "events": len(group), "resolved": resolved,
        "win_rate": wins / resolved if resolved else np.nan,
        "mean_close_r": group[f"h{horizon}_close_r"].mean(),
        "median_close_r": group[f"h{horizon}_close_r"].median(),
        "mean_mfe": group[f"h{horizon}_mfe"].mean(),
        "mean_mae": group[f"h{horizon}_mae"].mean(),
        "median_mfe_mae_ratio": event_ratio.replace([np.inf, -np.inf], np.nan).median(),
    }


def evaluate(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries, years, clocks, gates = [], [], [], []
    for (family, variant, parameter), group in events.groupby(["family", "variant", "parameter"], sort=True):
        horizon_stats = {}
        for horizon in HORIZONS:
            stats = summarize_group(group, horizon)
            horizon_stats[horizon] = stats
            summaries.append({"family": family, "variant": variant, "parameter": parameter,
                              "scope": "ALL", "year": "ALL", "horizon_min": horizon, **stats})
        year_stats = {}
        for year in (2022, 2023, 2024):
            yg = group[group.year == year]
            stats = summarize_group(yg, 240)
            year_stats[year] = stats
            years.append({"family": family, "variant": variant, "parameter": parameter,
                          "year": year, "horizon_min": 240, **stats})
        counts = group.hour_utc.value_counts().sort_index()
        for hour, count in counts.items():
            clocks.append({"family": family, "variant": variant, "parameter": parameter,
                           "hour_utc": int(hour), "events": int(count), "share": count / len(group)})
        primary = horizon_stats[240]
        checks = {
            "N>=180": len(group) >= 180,
            "resolved>=120": primary["resolved"] >= 120,
            "each_year_N>=40": all(year_stats[y]["events"] >= 40 for y in year_stats),
            "WR4h>55%": np.isfinite(primary["win_rate"]) and primary["win_rate"] > .55,
            "mean_close_R4h>0": primary["mean_close_r"] > 0,
            "median_MFE_MAE>=1.15": primary["median_mfe_mae_ratio"] >= 1.15,
            "3of4_horizons_positive": sum(horizon_stats[h]["mean_close_r"] > 0 for h in HORIZONS) >= 3,
            "each_year_mean_R4h>0": all(year_stats[y]["mean_close_r"] > 0 for y in year_stats),
            "max_clock_share<=25%": (counts.max() / len(group)) <= .25,
        }
        failures = [name for name, passed in checks.items() if not passed]
        gates.append({
            "family": family, "variant": variant, "parameter": parameter, **primary,
            "min_year_mean_close_r": min(year_stats[y]["mean_close_r"] for y in year_stats),
            "max_clock_share": counts.max() / len(group),
            **{f"check_{name}": passed for name, passed in checks.items()},
            "pass": all(checks.values()), "fail_reasons": ";".join(failures) if failures else "PASS",
        })
    return pd.DataFrame(summaries), pd.DataFrame(years), pd.DataFrame(clocks), pd.DataFrame(gates)


def choose_shortlist(gates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    family_rows, selected = [], []
    for family, group in gates.groupby("family", sort=True):
        passing = group[group["pass"]].copy()
        robust = len(passing) >= 2
        representative = ""
        if robust:
            winner = passing.sort_values(
                ["min_year_mean_close_r", "win_rate", "events"], ascending=False
            ).iloc[0]
            representative = winner.variant
            selected.append(winner.to_dict())
        family_rows.append({"family": family, "passing_variants": len(passing),
                            "neighborhood_robust": robust, "representative": representative})
    return pd.DataFrame(family_rows), pd.DataFrame(selected)


def synthetic_tests() -> None:
    idx = pd.date_range("2024-01-01", periods=12, freq="5min", tz="UTC")
    up = pd.DataFrame({"open": 100.0, "high": 100.2, "low": 99.8, "close": 100.0}, index=idx)
    up.loc[idx[1], "high"] = 101.1
    event = {"signal_ts": idx[0], "reference": 100.0, "atr": 1.0, "direction": 1}
    assert path_metrics(up, event, 60)["barrier"] == "WIN"
    down = up.copy(); down["high"] = 100.2; down.loc[idx[1], "low"] = 98.9
    assert path_metrics(down, event, 60)["barrier"] == "LOSS"
    both = up.copy(); both.loc[idx[1], ["high", "low"]] = [101.1, 98.9]
    assert path_metrics(both, event, 60)["barrier"] == "DUAL_TOUCH"


def report(coverage: float, events: pd.DataFrame, gates: pd.DataFrame,
           families: pd.DataFrame, shortlist: pd.DataFrame) -> None:
    status = "B1_PASS" if len(shortlist) else "B1_NO_PASS"
    lines = [
        "# SOL Structure Discovery B1 — Development Result", "",
        f"Development-only SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "B1 evaluated the nine preregistered dynamic-structure variants. No entry, TP, SL, clock, or OOS optimization was performed.", "",
        "## Variant gates", "",
        "| Family | Variant | N | Resolved | WR 4h | Mean R 4h | Median MFE/MAE | Min yearly R | Max clock | Verdict | Exact failure reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, row in gates.sort_values(["family", "parameter"]).iterrows():
        lines.append(
            f"| {row['family']} | {row['variant']} | {int(row['events'])} | {int(row['resolved'])} | "
            f"{100*row['win_rate']:.2f}% | {row['mean_close_r']:+.3f}R | {row['median_mfe_mae_ratio']:.3f} | "
            f"{row['min_year_mean_close_r']:+.3f}R | {100*row['max_clock_share']:.2f}% | "
            f"**{'PASS' if row['pass'] else 'FAIL'}** | {row['fail_reasons']} |"
        )
    lines += ["", "## Family robustness", "",
              "| Family | Passing neighbors | Robust | Representative |",
              "|---|---:|---|---|"]
    for row in families.itertuples(index=False):
        lines.append(f"| {row.family} | {int(row.passing_variants)}/3 | {'PASS' if row.neighborhood_robust else 'FAIL'} | {row.representative or '—'} |")
    lines += ["", "## Decision", ""]
    if len(shortlist):
        lines.append("Frozen B1 representatives: " + ", ".join(shortlist.variant.astype(str)) + ".")
        lines.append("These are discovery candidates only. Freeze them before a separately preregistered validation stage.")
    else:
        lines.append("No family achieved 2-of-3 neighborhood robustness. Stop B1; do not repair thresholds or add variants post-result.")
    lines += ["", f"**Status: {status}**", "", "Research only; no live-trading authorization."]
    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    synthetic_tests()
    if args.self_test:
        print("synthetic tests passed")
        return
    x5, coverage = load5()
    x15 = bars15(x5)
    raw: list[dict] = []
    for family, parameter in VARIANTS:
        if family == "IMPULSE_PULLBACK":
            raw.extend(detect_impulse_pullback(x15, parameter))
        elif family == "COMPRESSION_EXPANSION":
            raw.extend(detect_compression_expansion(x15, parameter))
        else:
            raw.extend(detect_sweep_reclaim(x15, parameter))
    retained = cooldown(raw)
    events = attach_outcomes(x5, retained)
    summaries, years, clocks, gates = evaluate(events)
    families, shortlist = choose_shortlist(gates)
    events.to_csv(ROOT / f"{PFX}_Events.csv", index=False)
    summaries.to_csv(ROOT / f"{PFX}_Horizons.csv", index=False)
    years.to_csv(ROOT / f"{PFX}_Years.csv", index=False)
    clocks.to_csv(ROOT / f"{PFX}_Clocks.csv", index=False)
    gates.to_csv(ROOT / f"{PFX}_Gates.csv", index=False)
    families.to_csv(ROOT / f"{PFX}_Families.csv", index=False)
    shortlist.to_csv(ROOT / f"{PFX}_Shortlist.csv", index=False)
    report(coverage, events, gates, families, shortlist)


if __name__ == "__main__":
    main()
