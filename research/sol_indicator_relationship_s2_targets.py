#!/usr/bin/env python3
"""Stage 2 deterministic SOL indicator-relationship outcome builder.

Input: canonical raw SOLUSDT 5m OHLC CSV.
Required columns: ts, open, high, low, close.
The timestamp is the 5m bar OPEN timestamp in UTC.

This script intentionally uses no volume, taker, OI, funding, breakout,
regime, or other candidate explanatory feature.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BAR = pd.Timedelta(minutes=5)
HORIZONS = (1, 2, 4, 8)
PRIMARY_H = 4
BARRIER = 0.01


def load_raw(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    need = {"ts", "open", "high", "low", "close"}
    missing = need.difference(x.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    x = x[list(need)].copy()
    x["ts"] = pd.to_datetime(x["ts"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = (
        x.dropna()
        .drop_duplicates("ts")
        .sort_values("ts")
        .reset_index(drop=True)
    )
    if x.empty:
        raise ValueError("no usable rows")

    dt = x.ts.diff().dropna()
    bad = dt[dt != BAR]
    # Gaps are permitted globally; each outcome horizon is separately marked
    # incomplete rather than silently forward-filled.
    x.attrs["gap_count"] = int(len(bad))
    return x


def exact_window(x: pd.DataFrame, pos: int, n: int) -> pd.DataFrame | None:
    end = pos + n
    if end > len(x):
        return None
    w = x.iloc[pos:end]
    if len(w) != n:
        return None
    expected_last = x.ts.iloc[pos] + BAR * (n - 1)
    if w.ts.iloc[-1] != expected_last:
        return None
    if not bool((w.ts.diff().dropna() == BAR).all()):
        return None
    return w


def first_touch(w: pd.DataFrame, entry: float) -> tuple[str, float | None, float | None]:
    up = entry * (1.0 + BARRIER)
    dn = entry * (1.0 - BARRIER)
    up_time = None
    dn_time = None

    for j, r in enumerate(w.itertuples(index=False)):
        hit_up = float(r.high) >= up
        hit_dn = float(r.low) <= dn
        # Bar-end upper-bound timing: a hit in the entry bar is <=5 minutes.
        elapsed = float((j + 1) * 5)

        if hit_up and up_time is None:
            up_time = elapsed
        if hit_dn and dn_time is None:
            dn_time = elapsed

        if hit_up and hit_dn:
            # If neither side was known to have hit in an earlier bar, ordering
            # inside this 5m candle is unknowable from OHLC.
            if (up_time == elapsed) and (dn_time == elapsed):
                return "AMBIGUOUS", up_time, dn_time

        if up_time is not None and dn_time is None:
            return "LONG", up_time, dn_time
        if dn_time is not None and up_time is None:
            return "SHORT", up_time, dn_time

    return "NONE", up_time, dn_time


def excursion(w: pd.DataFrame, entry: float) -> dict[str, float]:
    max_up = float(w.high.max() / entry - 1.0)
    max_down = float(w.low.min() / entry - 1.0)
    return {
        "max_up": max_up,
        "max_down": max_down,
        "mfe_long": max_up,
        "mae_long": abs(min(0.0, max_down)),
        "mfe_short": abs(min(0.0, max_down)),
        "mae_short": max(0.0, max_up),
    }


def build_targets(x: pd.DataFrame) -> pd.DataFrame:
    pos_by_ts = {t: i for i, t in enumerate(x.ts)}
    rows = []

    # 15m decision grid. At t, prior bars are completed and the raw 5m bar
    # opening at t supplies the next-open entry reference.
    decisions = x.loc[x.ts.dt.minute.isin([0, 15, 30, 45]), "ts"]

    for t in decisions:
        pos = pos_by_ts[t]
        entry = float(x.open.iloc[pos])
        row = {
            "decision_time": t,
            "entry_time": t,
            "entry_price": entry,
        }

        global_up = None
        global_dn = None

        for h in HORIZONS:
            n = h * 12
            w = exact_window(x, pos, n)
            complete_key = f"future_data_complete_{h}h"
            row[complete_key] = w is not None

            if w is None:
                row[f"target_1pct_{h}h"] = None
                row[f"fwd_ret_{h}h"] = np.nan
                for k in ["max_up", "max_down", "mfe_long", "mae_long", "mfe_short", "mae_short"]:
                    row[f"{k}_{h}h"] = np.nan
                continue

            label, up_t, dn_t = first_touch(w, entry)
            row[f"target_1pct_{h}h"] = label

            # Close of the final 5m bar in [t, t+h), which ends exactly at t+h.
            row[f"fwd_ret_{h}h"] = float(w.close.iloc[-1] / entry - 1.0)

            ex = excursion(w, entry)
            for k, v in ex.items():
                row[f"{k}_{h}h"] = v

            if h == max(HORIZONS):
                global_up = up_t
                global_dn = dn_t

        p = row.get(f"target_1pct_{PRIMARY_H}h")
        row["long_win_1pct_4h"] = int(p == "LONG") if p is not None else np.nan
        row["short_win_1pct_4h"] = int(p == "SHORT") if p is not None else np.nan
        row["time_to_up_1pct_min"] = global_up
        row["time_to_down_1pct_min"] = global_dn
        rows.append(row)

    out = pd.DataFrame(rows)
    return out


def summarize(y: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        c = f"target_1pct_{h}h"
        vc = y[c].value_counts(dropna=False)
        rows.append({
            "horizon": f"{h}h",
            "rows": int(len(y)),
            "complete": int(y[f"future_data_complete_{h}h"].sum()),
            "long": int(vc.get("LONG", 0)),
            "short": int(vc.get("SHORT", 0)),
            "none": int(vc.get("NONE", 0)),
            "ambiguous": int(vc.get("AMBIGUOUS", 0)),
            "missing": int(y[c].isna().sum()),
        })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--summary", type=Path)
    args = ap.parse_args()

    x = load_raw(args.input)
    y = build_targets(x)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    y.to_csv(args.output, index=False)

    s = summarize(y)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        s.to_csv(args.summary, index=False)

    print(f"raw_rows={len(x)} gap_count={x.attrs.get('gap_count', 0)}")
    print(f"target_rows={len(y)}")
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
