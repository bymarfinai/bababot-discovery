#!/usr/bin/env python3
"""G0 — preregistered global/pooled BTC regime dataset + label audit.

Research only; live BBC untouched.

Preregistration:
    BTC_Global_Regime_G0_Preregistration.md

This script intentionally performs NO model fitting and NO threshold sweep.
It constructs one causal market-state row per clock hour and assigns the locked,
symmetric 50bp / 6h first-passage direction label.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("G0_OUT", "g0_out"))
OUT.mkdir(parents=True, exist_ok=True)

HIST_START = pd.Timestamp("2023-12-02", tz="UTC")
HIST_END = pd.Timestamp("2026-07-30", tz="UTC")  # exclusive; same frozen cutoff convention
LABEL_HOURS = 6
BARRIER = 0.0050
STEP = pd.Timedelta(minutes=5)
HORIZON_BARS = LABEL_HOURS * 12

FEATURES = [
    "ret1h", "ret3h", "ret6h", "ret12h", "ret24h",
    "ema_spread", "dist_ema20", "ema20_slope1h",
    "loc24", "range6", "range24", "range6_to_24",
    "taker1h", "taker4h",
    "rv1h", "rv6h", "atr20_pct",
]


def taker_imbalance(x: pd.DataFrame) -> float:
    q = float(x.quote_volume.sum())
    tb = float(x.taker_buy_quote.sum())
    return (2.0 * tb / q - 1.0) if q > 0 else np.nan


def range_pct(x: pd.DataFrame) -> float:
    if x.empty:
        return np.nan
    lo = float(x.low.min())
    hi = float(x.high.max())
    return (hi / lo - 1.0) if lo > 0 else np.nan


def expected_index(start: pd.Timestamp, periods: int) -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=periods, freq="5min", tz="UTC")


def is_contiguous(x: pd.DataFrame, start: pd.Timestamp, periods: int) -> bool:
    if len(x) != periods:
        return False
    return x.index.equals(expected_index(start, periods))


def feature_row(k: pd.DataFrame, t: pd.Timestamp) -> tuple[dict | None, str | None]:
    """All features use bars strictly before t."""
    pre_t = t - STEP
    required_oldest = t - pd.Timedelta(hours=24) - STEP
    if required_oldest not in k.index or pre_t not in k.index:
        return None, "missing_preentry_anchor"

    # Require continuous 24h + one prior anchor bar. This is stricter than merely
    # having values and prevents silent feature-window gaps.
    x24 = k[(k.index >= t - pd.Timedelta(hours=24)) & (k.index < t)]
    if not is_contiguous(x24, t - pd.Timedelta(hours=24), 24 * 12):
        return None, "noncontiguous_preentry_24h"

    pre = k.loc[pre_t]

    def close_at(ts: pd.Timestamp) -> float:
        return float(k.loc[ts, "close"]) if ts in k.index else np.nan

    rets = {}
    last_close = float(pre.close)
    for h in [1, 3, 6, 12, 24]:
        anchor_t = t - pd.Timedelta(hours=h) - STEP
        anchor = close_at(anchor_t)
        rets[f"ret{h}h"] = last_close / anchor - 1.0 if np.isfinite(anchor) and anchor > 0 else np.nan

    e20_prev_t = t - pd.Timedelta(hours=1) - STEP
    e20_prev = float(k.loc[e20_prev_t, "ema20"]) if e20_prev_t in k.index else np.nan
    ema20_slope1h = float(pre.ema20) / e20_prev - 1.0 if np.isfinite(e20_prev) and e20_prev > 0 else np.nan

    lo24 = float(x24.low.min())
    hi24 = float(x24.high.max())
    loc24 = (last_close - lo24) / (hi24 - lo24) if hi24 > lo24 else 0.5

    x6 = k[(k.index >= t - pd.Timedelta(hours=6)) & (k.index < t)]
    x4 = k[(k.index >= t - pd.Timedelta(hours=4)) & (k.index < t)]
    x1 = k[(k.index >= t - pd.Timedelta(hours=1)) & (k.index < t)]
    r6 = range_pct(x6)
    r24 = range_pct(x24)

    # Realized volatility = sample std of completed 5m log returns whose bar
    # timestamps fall inside each pre-entry window. The shift source is also
    # strictly pre-entry.
    lr = k["logret5"]
    rv1 = float(lr.loc[x1.index].std(ddof=1))
    rv6 = float(lr.loc[x6.index].std(ddof=1))

    row = {
        **rets,
        "ema_spread": float(pre.ema7) / float(pre.ema20) - 1.0,
        "dist_ema20": last_close / float(pre.ema20) - 1.0,
        "ema20_slope1h": ema20_slope1h,
        "loc24": float(loc24),
        "range6": float(r6),
        "range24": float(r24),
        "range6_to_24": float(r6 / r24) if np.isfinite(r6) and np.isfinite(r24) and r24 > 0 else np.nan,
        "taker1h": float(taker_imbalance(x1)),
        "taker4h": float(taker_imbalance(x4)),
        "rv1h": rv1,
        "rv6h": rv6,
        "atr20_pct": float(pre.atr20) / last_close if last_close > 0 else np.nan,
    }
    return row, None


def label_row(k: pd.DataFrame, t: pd.Timestamp) -> tuple[str | None, str | None, int | None]:
    """Locked 50bp / 6h symmetric first-passage label.

    Returns (label, exclusion_or_neutral_reason, minutes_to_first_hit).
    Same-candle dual hits are NEUTRAL; no OHLC intrabar ordering is invented.
    """
    if t not in k.index:
        return None, "missing_decision_bar", None
    bars = k[(k.index >= t) & (k.index < t + pd.Timedelta(hours=LABEL_HOURS))]
    if not is_contiguous(bars, t, HORIZON_BARS):
        return None, "noncontiguous_or_incomplete_label_horizon", None

    ep = float(k.loc[t, "open"])
    down = ep * (1.0 - BARRIER)
    up = ep * (1.0 + BARRIER)

    for i, b in enumerate(bars.itertuples(index=False)):
        sell_hit = float(b.low) <= down
        buy_hit = float(b.high) >= up
        if sell_hit and buy_hit:
            return "NEUTRAL", "same_bar_dual_touch", i * 5 + 5
        if sell_hit:
            return "SELL_COMPATIBLE", "down_first", i * 5 + 5
        if buy_hit:
            return "BUY_COMPATIBLE", "up_first", i * 5 + 5
    return "NEUTRAL", "no_50bp_hit_6h", None


def prepare(k: pd.DataFrame) -> pd.DataFrame:
    k = k.copy().sort_index()
    k["ema7"] = k.close.ewm(span=7, adjust=False).mean()
    k["ema20"] = k.close.ewm(span=20, adjust=False).mean()
    k["logret5"] = np.log(k.close / k.close.shift(1))
    prev_close = k.close.shift(1)
    tr = pd.concat([
        k.high - k.low,
        (k.high - prev_close).abs(),
        (k.low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Locked implementation of preregistered "20-bar 5m ATR": simple rolling
    # mean of standard true range over the previous/current completed 20 bars.
    k["atr20"] = tr.rolling(20, min_periods=20).mean()
    return k


def build_rows(k: pd.DataFrame, times: list[pd.Timestamp]) -> tuple[pd.DataFrame, Counter]:
    rows = []
    excluded = Counter()
    for t in times:
        if t.minute != 0:
            continue
        feat, ferr = feature_row(k, t)
        if ferr:
            excluded[ferr] += 1
            continue
        label, lreason, hit_min = label_row(k, t)
        if label is None:
            excluded[lreason or "label_unknown"] += 1
            continue
        rows.append({
            "decision_t_utc": t,
            "decision_t_wib": t + pd.Timedelta(hours=7),
            "entry_open": float(k.loc[t, "open"]),
            "label": label,
            "label_reason": lreason,
            "first_hit_min": hit_min,
            **feat,
        })
    return pd.DataFrame(rows), excluded


def class_metrics(df: pd.DataFrame) -> dict:
    n = len(df)
    c = df.label.value_counts().to_dict() if n else {}
    return {
        "n": int(n),
        "counts": {x: int(c.get(x, 0)) for x in ["SELL_COMPATIBLE", "BUY_COMPATIBLE", "NEUTRAL"]},
        "rates": {x: (float(c.get(x, 0) / n) if n else None) for x in ["SELL_COMPATIBLE", "BUY_COMPATIBLE", "NEUTRAL"]},
    }


def feature_audit(df: pd.DataFrame) -> dict:
    out = {}
    for f in FEATURES:
        vals = pd.to_numeric(df[f], errors="coerce").to_numpy(float)
        finite = np.isfinite(vals)
        out[f] = {
            "finite_n": int(finite.sum()),
            "finite_rate": float(finite.mean()) if len(vals) else None,
            "missing_or_nonfinite_n": int((~finite).sum()),
        }
    return out


def tuesday_crosscheck(k: pd.DataFrame, hist: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Existing A5.11 parity must still pass before G0 can be accepted.
    parity = tue.historical_parity(k)

    hist_idx = hist.set_index("decision_t_utc")
    rows = []
    for t in tue.entries(k):
        if t not in hist_idx.index:
            rows.append({"date_wib": str((t + pd.Timedelta(hours=7)).date()), "decision_t_utc": t, "label": "MISSING"})
            continue
        r = hist_idx.loc[t]
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()),
            "decision_t_utc": t,
            "label": str(r.label),
            "label_reason": str(r.label_reason),
            "first_hit_min": None if pd.isna(r.first_hit_min) else int(r.first_hit_min),
        })

    # Build August Tuesday labels directly from the frozen post-cutoff timestamps.
    aug_times = tue.entries(
        k,
        pd.Timestamp("2026-08-01", tz="UTC"),
        pd.Timestamp("2026-08-19", tz="UTC"),
    )
    for t in aug_times:
        label, reason, hit_min = label_row(k, t)
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()),
            "decision_t_utc": t,
            "label": label or "MISSING",
            "label_reason": reason,
            "first_hit_min": hit_min,
        })

    td = pd.DataFrame(rows)
    hist_td = td[~td.date_wib.isin(["2026-08-04", "2026-08-11", "2026-08-18"])]
    aug_td = td[td.date_wib.isin(["2026-08-04", "2026-08-11", "2026-08-18"])]
    summary = {
        "historical_n": int(len(hist_td)),
        "historical_labels": class_metrics(hist_td.rename(columns={"label": "label"})),
        "august": aug_td.to_dict(orient="records"),
        "a511_parity": parity,
    }
    return td, summary


def yearly_distribution(df: pd.DataFrame) -> list[dict]:
    x = df.copy()
    x["year"] = pd.to_datetime(x.decision_t_utc, utc=True).dt.year
    out = []
    for y, g in x.groupby("year"):
        out.append({"year": int(y), **class_metrics(g)})
    return out


def main() -> None:
    raw = tue.load_extended()
    k = prepare(raw)

    # Candidate hourly timestamps are taken from actual data timestamps; integrity
    # checks below decide eligibility.
    hist_times = [
        t for t in k.index
        if HIST_START <= t < HIST_END and t.minute == 0
    ]
    hist, excluded = build_rows(k, hist_times)
    if hist.empty:
        raise RuntimeError("G0 produced zero historical rows")

    fa = feature_audit(hist)
    cm = class_metrics(hist)
    yd = yearly_distribution(hist)
    td, ts = tuesday_crosscheck(k, hist)

    same_bar_dual = int((hist.label_reason == "same_bar_dual_touch").sum())
    timeout_neutral = int((hist.label_reason == "no_50bp_hit_6h").sum())

    checks = {
        "causal_integrity_by_construction": True,
        "intrabar_dual_touch_is_neutral": bool(
            ((hist.label_reason != "same_bar_dual_touch") | (hist.label == "NEUTRAL")).all()
        ),
        "coverage_ge_15000": bool(len(hist) >= 15000),
        "sell_class_ge_20pct": bool(cm["rates"]["SELL_COMPATIBLE"] >= 0.20),
        "buy_class_ge_20pct": bool(cm["rates"]["BUY_COMPATIBLE"] >= 0.20),
        "all_features_finite_ge_99pct": bool(all(v["finite_rate"] >= 0.99 for v in fa.values())),
        "a511_historical_parity_pass": bool(ts["a511_parity"].get("pass")),
        "tuesday_historical_n139": bool(ts["historical_n"] == 139),
    }
    passed = bool(all(checks.values()))

    summary = {
        "status": "G0_PASS_ADVANCE_TO_G1" if passed else "G0_STOP_GATE_FAILED",
        "preregistration": "BTC_Global_Regime_G0_Preregistration.md",
        "historical_window": {"start": str(HIST_START), "end_exclusive": str(HIST_END)},
        "label": {"barrier": BARRIER, "horizon_hours": LABEL_HOURS, "same_bar_dual_touch": "NEUTRAL"},
        "features": FEATURES,
        "candidate_hourly_states": int(len(hist_times)),
        "eligible_historical_states": int(len(hist)),
        "excluded": dict(excluded),
        "class_distribution": cm,
        "same_bar_dual_touch_n": same_bar_dual,
        "neutral_timeout_n": timeout_neutral,
        "yearly_distribution": yd,
        "feature_audit": fa,
        "tuesday_crosscheck": ts,
        "acceptance_checks": checks,
        "pass": passed,
        "guardrail": "G0 is dataset/label audit only. No predictive or tradable edge is claimed; live BBC untouched.",
    }

    # Machine-readable outputs.
    hist.to_csv(OUT / "g0_pooled_hourly_states.csv", index=False)
    td.to_csv(OUT / "g0_tuesday_crosscheck.csv", index=False)
    (OUT / "g0_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G0 Result",
        "",
        f"**Status: {'PASS — advance to G1' if passed else 'STOP — acceptance gate failed'}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Locked label",
        "One hourly market state; 50bp symmetric first-passage over the next 6h. Down first = SELL_COMPATIBLE, up first = BUY_COMPATIBLE, neither or same-5m-bar dual touch = NEUTRAL.",
        "",
        "## Historical pooled dataset",
        f"- Candidate hourly states: **{len(hist_times):,}**",
        f"- Eligible states: **{len(hist):,}**",
        f"- Excluded: **{sum(excluded.values()):,}** — `{dict(excluded)}`",
        f"- SELL_COMPATIBLE: **{cm['counts']['SELL_COMPATIBLE']:,} ({pct(cm['rates']['SELL_COMPATIBLE'])})**",
        f"- BUY_COMPATIBLE: **{cm['counts']['BUY_COMPATIBLE']:,} ({pct(cm['rates']['BUY_COMPATIBLE'])})**",
        f"- NEUTRAL: **{cm['counts']['NEUTRAL']:,} ({pct(cm['rates']['NEUTRAL'])})**",
        f"- Same-bar dual-touch neutrals: **{same_bar_dual:,}**",
        f"- No-50bp-in-6h neutrals: **{timeout_neutral:,}**",
        "",
        "## Yearly class distribution",
        "| Year | N | SELL | BUY | NEUTRAL |",
        "|---:|---:|---:|---:|---:|",
    ]
    for y in yd:
        lines.append(
            f"| {y['year']} | {y['n']:,} | {pct(y['rates']['SELL_COMPATIBLE'])} | {pct(y['rates']['BUY_COMPATIBLE'])} | {pct(y['rates']['NEUTRAL'])} |"
        )

    lines += [
        "",
        "## Feature finite-value audit",
        "| Feature | Finite | Missing/nonfinite |",
        "|---|---:|---:|",
    ]
    for f in FEATURES:
        a = fa[f]
        lines.append(f"| {f} | {pct(a['finite_rate'])} | {a['missing_or_nonfinite_n']:,} |")

    lines += [
        "",
        "## Frozen Tuesday cross-check",
        f"- Historical Tuesday rows: **{ts['historical_n']}**",
        f"- Historical Tuesday label rates: SELL **{pct(ts['historical_labels']['rates']['SELL_COMPATIBLE'])}**, BUY **{pct(ts['historical_labels']['rates']['BUY_COMPATIBLE'])}**, NEUTRAL **{pct(ts['historical_labels']['rates']['NEUTRAL'])}**.",
        f"- Frozen A5.11 historical parity: **{'PASS' if ts['a511_parity'].get('pass') else 'FAIL'}**.",
        "",
        "### August Tuesday labels — report only",
        "| Date WIB | G0 label | Reason | First hit min |",
        "|---|---|---|---:|",
    ]
    for r in ts["august"]:
        lines.append(f"| {r['date_wib']} | {r['label']} | {r.get('label_reason')} | {r.get('first_hit_min')} |")

    lines += [
        "",
        "## Acceptance gate",
    ]
    for kcheck, v in checks.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{kcheck}`")
    lines += [
        "",
        f"**Final G0 verdict: {'PASS. Dataset/label layer is viable; proceed to preregistered embargoed G1 baseline.' if passed else 'STOP. Do not tune G0 after seeing the failure; diagnose and preregister a new experiment.'}**",
        "",
        "G0 does not fit a model and does not claim a tradable edge.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G0_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
