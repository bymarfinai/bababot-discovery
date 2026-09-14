#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_A1_STRUCTURE_FINGERPRINT"
OUT_FP = ROOT / f"{PFX}.csv.gz"
OUT_SANITY = ROOT / f"{PFX}_Sanity.md"
OUT_STATES = ROOT / f"{PFX}_StateCoverage.csv"
OUT_SCHEMA = ROOT / f"{PFX}_Schema.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SYMBOL = "BNBUSDT"
BAR = pd.Timedelta(minutes=5)
PREFIX_CUTOFF_OPEN = pd.Timestamp("2025-01-01T00:00:00Z")
MIN_COVERAGE = 0.995

HORIZONS = {"15": 3, "30": 6, "60": 12, "120": 24, "360": 72}

NUMERIC_FEATURES = [
    "ret_15", "ret_30", "ret_60", "ret_120", "ret_360",
    "disp_atr_15", "disp_atr_30", "disp_atr_60", "disp_atr_120", "disp_atr_360",
    "eff_30", "eff_60", "eff_120", "eff_360",
    "up_frac_30", "up_frac_60", "up_frac_120",
    "true_range", "atr_30", "atr_60", "atr_120", "atr_360",
    "atr30_atr360", "atr60_atr360",
    "rv_30", "rv_60", "rv_120", "rv_360", "rv60_rv360",
    "body_range", "close_location",
    "range_pos_60", "range_pos_120", "range_pos_360",
    "dist_prior_high_60_atr", "dist_prior_low_60_atr",
    "dist_prior_high_120_atr", "dist_prior_low_120_atr",
    "sweep_high_60", "sweep_low_60", "break_high_60", "break_low_60",
    "utc_hour", "utc_minute", "wib_hour", "wib_quarter", "day_of_week",
    "tod_sin", "tod_cos",
]

CATEGORICAL_FEATURES = [
    "structure_state", "trend_state", "efficiency_state", "vol_state",
    "range_state", "liquidity_state", "path_state", "wib_bucket",
    "era", "character_token",
]
CORE_STATES = [
    "structure_state", "trend_state", "efficiency_state", "vol_state",
    "range_state", "liquidity_state", "path_state", "wib_bucket",
]
FORBIDDEN_SCHEMA_TOKENS = (
    "future", "forward", "outcome", "target", "entry", "exit",
    "tp", "sl", "pnl", "profit", "win", "loss", "label",
)


def safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    return a.astype(float) / b.astype(float).replace(0.0, np.nan)


def directional_efficiency(close: pd.Series, n: int) -> pd.Series:
    path = close.diff().abs().rolling(n, min_periods=n).sum()
    net = (close - close.shift(n)).abs()
    return safe_div(net, path)


def up_fraction(close: pd.Series, n: int) -> pd.Series:
    return (close.diff() > 0).astype(float).rolling(n, min_periods=n).mean()


def rolling_rv(logret: pd.Series, n: int) -> pd.Series:
    return logret.rolling(n, min_periods=n).std(ddof=0)


def state_trend(v: pd.Series) -> pd.Series:
    out = np.select(
        [v < -1.0, v < -0.35, v <= 0.35, v <= 1.0],
        ["STRONG_DOWN", "DOWN", "FLAT", "UP"], default="STRONG_UP",
    )
    return pd.Series(out, index=v.index, dtype="object")


def state_eff(v: pd.Series) -> pd.Series:
    return pd.Series(np.select([v < 0.25, v < 0.55], ["LOW", "MID"], default="HIGH"), index=v.index, dtype="object")


def state_vol(v: pd.Series) -> pd.Series:
    return pd.Series(np.select([v < 0.80, v <= 1.25], ["COMPRESS", "NORMAL"], default="EXPAND"), index=v.index, dtype="object")


def state_range(v: pd.Series) -> pd.Series:
    return pd.Series(np.select([v < 1.0 / 3.0, v <= 2.0 / 3.0], ["LOW", "MID"], default="HIGH"), index=v.index, dtype="object")


def state_liquidity(f: pd.DataFrame) -> pd.Series:
    sh = f["sweep_high_60"].astype(bool); sl = f["sweep_low_60"].astype(bool)
    bh = f["break_high_60"].astype(bool); bl = f["break_low_60"].astype(bool)
    out = np.select(
        [sh & sl, sl, sh, bl, bh],
        ["SWEEP_BOTH", "SWEEP_LOW", "SWEEP_HIGH", "BREAK_LOW", "BREAK_HIGH"],
        default="NONE",
    )
    return pd.Series(out, index=f.index, dtype="object")


def state_path(f: pd.DataFrame) -> pd.Series:
    long = f["disp_atr_360"]; short = f["disp_atr_60"]
    conds = [
        (long > 0.75) & (short < -0.25),
        (long > 0.75) & (short > 0.25),
        long > 0.75,
        (long < -0.75) & (short > 0.25),
        (long < -0.75) & (short < -0.25),
        long < -0.75,
    ]
    vals = ["PULLBACK_FROM_UP", "CONT_UP", "UP_PAUSE", "PULLBACK_FROM_DOWN", "CONT_DOWN", "DOWN_PAUSE"]
    return pd.Series(np.select(conds, vals, default="MIXED_RANGE"), index=f.index, dtype="object")


def state_structure(high_now, low_now, high_prev, low_prev, atr360) -> pd.Series:
    tol = 0.10 * atr360
    h_up = high_now > high_prev + tol; h_dn = high_now < high_prev - tol
    l_up = low_now > low_prev + tol; l_dn = low_now < low_prev - tol
    out = np.select(
        [h_up & l_up, h_dn & l_dn, h_up & l_dn, h_dn & l_up],
        ["HH_HL", "LH_LL", "HH_LL", "LH_HL"], default="OVERLAP",
    )
    return pd.Series(out, index=high_now.index, dtype="object")


def wib_bucket(hour: pd.Series) -> pd.Series:
    out = np.select([hour < 6, hour < 12, hour < 18], ["WIB_00_05", "WIB_06_11", "WIB_12_17"], default="WIB_18_23")
    return pd.Series(out, index=hour.index, dtype="object")


def era(index: pd.DatetimeIndex) -> pd.Series:
    y = index.year
    vals = np.select(
        [y <= 2021, y == 2022, y == 2023, y == 2024, y == 2025],
        ["2020_2021", "2022", "2023", "2024", "2025"], default="2026_PRE_B29",
    )
    return pd.Series(vals, index=index, dtype="object")


def build_fingerprint(raw: pd.DataFrame) -> pd.DataFrame:
    """Build features only from bars fully closed by each decision timestamp."""
    if not raw.index.is_monotonic_increasing or raw.index.has_duplicates:
        raise AssertionError("raw index must be unique and monotonic")

    x = raw[["open", "high", "low", "close"]].astype(float).copy()
    # Binance kline timestamp is bar-open time; make causality explicit.
    x.index = pd.DatetimeIndex(x.index) + BAR
    x.index.name = "decision_ts"

    prev_close = x["close"].shift(1)
    tr = pd.concat([
        x["high"] - x["low"],
        (x["high"] - prev_close).abs(),
        (x["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    f = pd.DataFrame(index=x.index)
    f["true_range"] = tr
    atr = {}
    for name, n in (("30", 6), ("60", 12), ("120", 24), ("360", 72)):
        atr[name] = tr.rolling(n, min_periods=n).mean()
        f[f"atr_{name}"] = atr[name]

    logret = np.log(x["close"]).diff()
    for name, n in HORIZONS.items():
        f[f"ret_{name}"] = x["close"].pct_change(n)
        f[f"disp_atr_{name}"] = safe_div(x["close"] - x["close"].shift(n), atr["360"])

    for name, n in (("30", 6), ("60", 12), ("120", 24), ("360", 72)):
        f[f"eff_{name}"] = directional_efficiency(x["close"], n)
        f[f"rv_{name}"] = rolling_rv(logret, n)
    for name, n in (("30", 6), ("60", 12), ("120", 24)):
        f[f"up_frac_{name}"] = up_fraction(x["close"], n)

    f["atr30_atr360"] = safe_div(f["atr_30"], f["atr_360"])
    f["atr60_atr360"] = safe_div(f["atr_60"], f["atr_360"])
    f["rv60_rv360"] = safe_div(f["rv_60"], f["rv_360"])

    candle_range = x["high"] - x["low"]
    f["body_range"] = safe_div((x["close"] - x["open"]).abs(), candle_range)
    f["close_location"] = safe_div((x["close"] - x["low"]) - (x["high"] - x["close"]), candle_range)

    for name, n in (("60", 12), ("120", 24), ("360", 72)):
        rh = x["high"].rolling(n, min_periods=n).max()
        rl = x["low"].rolling(n, min_periods=n).min()
        f[f"range_pos_{name}"] = safe_div(x["close"] - rl, rh - rl)

    # Liquidity references exclude the current bar.
    prior_high_60 = x["high"].shift(1).rolling(12, min_periods=12).max()
    prior_low_60 = x["low"].shift(1).rolling(12, min_periods=12).min()
    prior_high_120 = x["high"].shift(1).rolling(24, min_periods=24).max()
    prior_low_120 = x["low"].shift(1).rolling(24, min_periods=24).min()
    f["dist_prior_high_60_atr"] = safe_div(prior_high_60 - x["close"], f["atr_360"])
    f["dist_prior_low_60_atr"] = safe_div(x["close"] - prior_low_60, f["atr_360"])
    f["dist_prior_high_120_atr"] = safe_div(prior_high_120 - x["close"], f["atr_360"])
    f["dist_prior_low_120_atr"] = safe_div(x["close"] - prior_low_120, f["atr_360"])
    f["sweep_high_60"] = ((x["high"] > prior_high_60) & (x["close"] <= prior_high_60)).astype(float)
    f["sweep_low_60"] = ((x["low"] < prior_low_60) & (x["close"] >= prior_low_60)).astype(float)
    f["break_high_60"] = (x["close"] > prior_high_60).astype(float)
    f["break_low_60"] = (x["close"] < prior_low_60).astype(float)

    # Compare most recent completed 60m window with the preceding 60m window.
    high_now = x["high"].rolling(12, min_periods=12).max()
    low_now = x["low"].rolling(12, min_periods=12).min()
    high_prev = x["high"].shift(12).rolling(12, min_periods=12).max()
    low_prev = x["low"].shift(12).rolling(12, min_periods=12).min()

    idx = f.index
    f["utc_hour"] = idx.hour.astype(float)
    f["utc_minute"] = idx.minute.astype(float)
    wib_hour_values = ((idx.hour + 7) % 24).astype(int)
    f["wib_hour"] = wib_hour_values.astype(float)
    f["wib_quarter"] = (idx.minute // 15).astype(float)
    f["day_of_week"] = idx.dayofweek.astype(float)
    minute_of_day_wib = (wib_hour_values * 60 + idx.minute).astype(float)
    angle = 2.0 * np.pi * minute_of_day_wib / 1440.0
    f["tod_sin"] = np.sin(angle); f["tod_cos"] = np.cos(angle)

    f["structure_state"] = state_structure(high_now, low_now, high_prev, low_prev, f["atr_360"])
    f["trend_state"] = state_trend(f["disp_atr_120"])
    f["efficiency_state"] = state_eff(f["eff_120"])
    f["vol_state"] = state_vol(f["atr60_atr360"])
    f["range_state"] = state_range(f["range_pos_120"])
    f["liquidity_state"] = state_liquidity(f)
    f["path_state"] = state_path(f)
    f["wib_bucket"] = wib_bucket(pd.Series(wib_hour_values, index=idx))
    f["era"] = era(idx)

    f = f[(f.index.minute % 15) == 0].copy()
    numeric = f[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan)
    valid = numeric.notna().all(axis=1)
    f = f.loc[valid].copy()
    f[NUMERIC_FEATURES] = numeric.loc[valid].astype(float)

    f["character_token"] = (
        f["structure_state"].astype(str) + "|" + f["trend_state"].astype(str) + "|" +
        f["efficiency_state"].astype(str) + "|" + f["vol_state"].astype(str) + "|" +
        f["range_state"].astype(str) + "|" + f["liquidity_state"].astype(str) + "|" +
        f["path_state"].astype(str) + "|" + f["wib_bucket"].astype(str)
    )
    return f[NUMERIC_FEATURES + CATEGORICAL_FEATURES].sort_index()


def schema_guard(fp: pd.DataFrame):
    problems = []
    expected = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    if list(fp.columns) != expected:
        problems.append("column order/schema differs from preregistered list")
    for col in [c.lower() for c in fp.columns]:
        for token in FORBIDDEN_SCHEMA_TOKENS:
            if token in col:
                problems.append(f"forbidden outcome/execution token in schema: {col}")
    return len(problems) == 0, problems


def fingerprint_hash(fp: pd.DataFrame) -> str:
    q = fp.reset_index().copy()
    h = pd.util.hash_pandas_object(q, index=False).to_numpy(np.uint64)
    return sha256(h.tobytes()).hexdigest()


def causal_invariant(full: pd.DataFrame, prefix: pd.DataFrame) -> dict:
    common = full.index.intersection(prefix.index)
    if len(common) == 0:
        return {"rows": 0, "index_equal": False, "numeric_equal": False, "categorical_equal": False, "max_abs_diff": np.inf, "pass": False}
    a = full.loc[common]; b = prefix.loc[common]
    av = a[NUMERIC_FEATURES].to_numpy(float); bv = b[NUMERIC_FEATURES].to_numpy(float)
    diff = np.abs(av - bv)
    max_abs = float(np.nanmax(diff)) if diff.size else 0.0
    numeric_equal = bool(np.allclose(av, bv, rtol=1e-12, atol=1e-12, equal_nan=True))
    categorical_equal = bool((a[CATEGORICAL_FEATURES].astype(str).to_numpy() == b[CATEGORICAL_FEATURES].astype(str).to_numpy()).all())
    index_equal = bool(a.index.equals(b.index))
    return {"rows": int(len(common)), "index_equal": index_equal, "numeric_equal": numeric_equal, "categorical_equal": categorical_equal, "max_abs_diff": max_abs, "pass": bool(index_equal and numeric_equal and categorical_equal)}


def state_coverage(fp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in CORE_STATES + ["era"]:
        vc = fp[feature].astype(str).value_counts(dropna=False); total = int(vc.sum())
        for value, n in vc.items():
            rows.append({"feature": feature, "state": value, "count": int(n), "share": float(n / total) if total else np.nan})
    return pd.DataFrame(rows).sort_values(["feature", "count"], ascending=[True, False])


def schema_table(fp: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{
        "column": c,
        "family": "numeric" if c in NUMERIC_FEATURES else "categorical",
        "dtype": str(fp[c].dtype),
        "missing": int(fp[c].isna().sum()),
        "unique": int(fp[c].nunique(dropna=True)),
    } for c in fp.columns])


def main():
    if base.END != pd.Timestamp("2026-08-26T00:00:00Z"):
        raise AssertionError(f"unexpected frozen loader END: {base.END}")

    raw, coverage = base.load5(SYMBOL)
    raw_dup = bool(raw.index.has_duplicates); raw_mono = bool(raw.index.is_monotonic_increasing)
    full = build_fingerprint(raw)
    prefix_raw = raw[raw.index < PREFIX_CUTOFF_OPEN].copy()
    prefix = build_fingerprint(prefix_raw)

    inv = causal_invariant(full, prefix)
    schema_ok, schema_problems = schema_guard(full)
    finite_ok = bool(np.isfinite(full[NUMERIC_FEATURES].to_numpy(float)).all())
    categorical_ok = bool(full[CATEGORICAL_FEATURES].notna().all().all())
    decision_dup = bool(full.index.has_duplicates); decision_mono = bool(full.index.is_monotonic_increasing)
    grid_ok = bool(((full.index.minute % 15) == 0).all())
    states = state_coverage(full)
    core_uniques = {c: int(full[c].nunique()) for c in CORE_STATES}
    state_variance_ok = bool(all(v >= 2 for v in core_uniques.values()))
    boundary_ok = bool(len(full) and full.index.max() <= base.END)

    gates = {
        "coverage": bool(coverage >= MIN_COVERAGE),
        "raw_integrity": bool(raw_mono and not raw_dup),
        "decision_integrity": bool(decision_mono and not decision_dup and grid_ok),
        "causal_invariant": bool(inv["pass"]),
        "numeric_finite": finite_ok,
        "categorical_populated": categorical_ok,
        "state_variance": state_variance_ok,
        "schema_guard": schema_ok,
        "frozen_boundary": boundary_ok,
    }
    passed = bool(all(gates.values()))
    status = "BNB_B29_A1_STRUCTURE_FINGERPRINT_PASS" if passed else "BNB_B29_A1_STRUCTURE_FINGERPRINT_FAIL"

    full.reset_index().to_csv(OUT_FP, index=False, compression="gzip")
    states.to_csv(OUT_STATES, index=False)
    schema_table(full).to_csv(OUT_SCHEMA, index=False)
    OUT_STATUS.write_text(status + "\n")

    fp_hash = fingerprint_hash(full); prefix_hash = fingerprint_hash(prefix)
    top_tokens = full["character_token"].value_counts().head(10)
    lines = [
        "# BNB B29 A1 — Structure Fingerprint Sanity Result", "", f"**Status: {status}**", "",
        "A1 validates representation and causality only. It does **not** evaluate trading edge, entry, TP, SL, WR, PnL, or RTD.", "",
        "## Frozen data", "", f"- Symbol: `{SYMBOL}`",
        f"- Raw 5m open-time span: `{raw.index.min()}` to `{raw.index.max()}`",
        f"- Last fully closed bar represented: `{raw.index.max() + BAR}`", f"- Loader frozen END: `{base.END}`",
        f"- Raw rows: {len(raw):,}", f"- Raw coverage: {coverage:.6%}", "- Post-2026-08-26 data touched: **NO**", "",
        "## Fingerprint", "", f"- 15m decision rows after warm-up: {len(full):,}",
        f"- First usable decision: `{full.index.min()}`", f"- Last usable decision: `{full.index.max()}`",
        f"- Numeric features: {len(NUMERIC_FEATURES)}", f"- Categorical/context features: {len(CATEGORICAL_FEATURES)}",
        f"- Character tokens observed: {full['character_token'].nunique():,}", f"- Deterministic fingerprint hash: `{fp_hash}`", "",
        "## Anti-leak prefix invariant", "", f"- Prefix raw cutoff: `{PREFIX_CUTOFF_OPEN}`",
        f"- Prefix fingerprint hash: `{prefix_hash}`", f"- Overlapping decision rows checked: {inv['rows']:,}",
        f"- Index identical: {inv['index_equal']}", f"- Numeric identical within 1e-12: {inv['numeric_equal']}",
        f"- Categorical exactly identical: {inv['categorical_equal']}", f"- Maximum absolute numeric difference: {inv['max_abs_diff']:.3e}",
        f"- Causal invariant: **{'PASS' if inv['pass'] else 'FAIL'}**", "", "## Acceptance gates", "",
    ]
    for name, ok in gates.items():
        lines.append(f"- `{name}`: **{'PASS' if ok else 'FAIL'}**")
    lines += ["", "## Core state cardinality", "", "| State family | Observed states |", "|---|---:|"]
    for c in CORE_STATES:
        lines.append(f"| `{c}` | {core_uniques[c]} |")
    lines += ["", "## Ten most common diagnostic character tokens", "", "| Token | N | Share |", "|---|---:|---:|"]
    for token, n in top_tokens.items():
        lines.append(f"| `{token}` | {int(n)} | {float(n / len(full)):.2%} |")
    if schema_problems:
        lines += ["", "## Schema problems", ""] + [f"- {p}" for p in schema_problems]
    lines += ["", "## Decision", "", f"**{status}**", "",
              "If PASS, the only permitted next phase is B29 A2 Character Memory / similarity construction using this frozen A1 representation. Entry and TP/SL work remain blocked.", "", "No live orders were placed."]
    OUT_SANITY.write_text("\n".join(lines) + "\n")
    print(OUT_SANITY.read_text())


if __name__ == "__main__":
    main()
