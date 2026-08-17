#!/usr/bin/env python3
"""Saturday T-Method S5.2E — Timing / Path Robustness.

Research only; live BBC untouched. No immunity action is applied.

Frozen cohort: exact 43 FLOW_EMA_PROTECT warnings from S5.2B/S5.2D.
S5.2D found a Saturday-native latent-runner mechanism before warning:
  earlier +0.50 hinge + earlier warning + stronger retained path + positive EMA slope.

S5.2E does NOT optimize thresholds. It tests that mechanism using only coarse,
predeclared natural bins tied to already-used strategy geometry and clock windows,
plus four chronological folds.

Natural bins:
- +0.50 hinge age: <=120m / 125-240m / >240m (same S5.2A descriptive bins)
- warning age: <=240m / 245-360m / >360m (4h / 6h clock windows)
- retained floor: <+0.20 / +0.20..<+0.30 / >=+0.30
- post-hinge high-water close: <+0.40 / +0.40..<+0.50 / >=+0.50
- EMA7/EMA20 slope: positive vs nonpositive

No bin is chosen for trading. Future-DEEP is forensic outcome only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52
import s52d_pre_warning_latent_runner_immunity_atlas as d52

OUT = Path(os.getenv("S52E_OUT", "s52e_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83

CORE_FEATURES = [
    "time_to05_min",
    "warning_min",
    "posthinge_max_close_progress",
    "posthinge_min_close_progress",
    "warning_ema20_slope60",
    "warning_ema7_slope60",
]


def rank_auc(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=bool)
    m = np.isfinite(x)
    x, y = x[m], y[m]
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    r = pd.Series(x).rank(method="average").to_numpy()
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def build_warning_cohort():
    k = s50.load_klines()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]
    rows = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        pre = a50.pre_context(k, t)
        s240 = a50.state240(k, t, tr)
        base_pnl = a50.a719_pnl(k, f, t, tr, s240)
        base_exit = b52.a719_exit_time(t, tr, s240)
        h05, h08 = a52.first_hinges(k, t, tr)
        mem = a52.prehinge_memory(k, t, tr, h05) if h05 is not None else {
            "prior_failure": False,
            "hinge_taker": np.nan,
            "hinge_ema_dist": np.nan,
            "hinge_ema_slope60": np.nan,
        }
        ev = b52.first_action_event(
            k, t, tr, base_exit, h05,
            bool(mem.get("prior_failure", False)),
            mem.get("hinge_taker", np.nan),
            adaptive=False,
        )
        if ev is None:
            continue
        pp, reason, _, _ = b52.protected_pnl(k, f, t, tr, base_exit, base_pnl, ev)
        r = {
            "idx": i,
            "date": tr.date,
            "pre_state": pre["pre_state"],
            "prior_failure": bool(mem.get("prior_failure", False)),
            "a719_pnl": float(base_pnl),
            "protect_pnl": float(pp),
            "protect_delta": float(pp - base_pnl),
            "eventual_deep": bool(h08 is not None),
            "protect_reason": reason,
        }
        r.update(d52.event_features(k, t, tr, h05, ev, mem))
        rows.append(r)
    df = pd.DataFrame(rows).sort_values("idx").reset_index(drop=True)

    # Frozen parity.
    if len(df) != 43 or (int((df.idx < SPLIT).sum()), int((df.idx >= SPLIT).sum())) != (28, 15):
        raise RuntimeError("43-event D/V parity failed")
    if int(df.eventual_deep.sum()) != 19 or int((~df.eventual_deep).sum()) != 24:
        raise RuntimeError("deep/nondeep parity failed")
    if int((df.eventual_deep & (df.protect_delta < 0)).sum()) != 15:
        raise RuntimeError("damaged deep parity failed")
    if abs(df.loc[df.eventual_deep, "protect_delta"].sum() + 81.5693647) > 0.02:
        raise RuntimeError("deep economics parity failed")
    if abs(df.loc[~df.eventual_deep, "protect_delta"].sum() - 29.2215077) > 0.02:
        raise RuntimeError("nondeep economics parity failed")
    return df


def bin_rate(df, family, label, mask):
    g = df[mask]
    d = g[g.idx < SPLIT]
    v = g[g.idx >= SPLIT]
    def rate(x):
        return float(x.eventual_deep.mean()) if len(x) else np.nan
    return {
        "family": family,
        "bin": label,
        "n": len(g), "deep_rate": rate(g),
        "disc_n": len(d), "disc_deep_rate": rate(d),
        "val_n": len(v), "val_deep_rate": rate(v),
    }


def add_natural_bins(df):
    rows = []
    # Same time-to-hinge descriptive bins used previously.
    rows += [
        bin_rate(df, "HINGE_AGE", "<=120m", df.time_to05_min <= 120),
        bin_rate(df, "HINGE_AGE", "125-240m", (df.time_to05_min > 120) & (df.time_to05_min <= 240)),
        bin_rate(df, "HINGE_AGE", ">240m", df.time_to05_min > 240),
    ]
    # Natural 4h / 6h warning-age windows.
    rows += [
        bin_rate(df, "WARNING_AGE", "<=240m", df.warning_min <= 240),
        bin_rate(df, "WARNING_AGE", "245-360m", (df.warning_min > 240) & (df.warning_min <= 360)),
        bin_rate(df, "WARNING_AGE", ">360m", df.warning_min > 360),
    ]
    # Existing protect/giveback geometry levels.
    rows += [
        bin_rate(df, "RETAINED_FLOOR", "<+0.20", df.posthinge_min_close_progress < .002),
        bin_rate(df, "RETAINED_FLOOR", "+0.20..<+0.30", (df.posthinge_min_close_progress >= .002) & (df.posthinge_min_close_progress < .003)),
        bin_rate(df, "RETAINED_FLOOR", ">=+0.30", df.posthinge_min_close_progress >= .003),
    ]
    rows += [
        bin_rate(df, "HIGH_WATER_CLOSE", "<+0.40", df.posthinge_max_close_progress < .004),
        bin_rate(df, "HIGH_WATER_CLOSE", "+0.40..<+0.50", (df.posthinge_max_close_progress >= .004) & (df.posthinge_max_close_progress < .005)),
        bin_rate(df, "HIGH_WATER_CLOSE", ">=+0.50", df.posthinge_max_close_progress >= .005),
    ]
    rows += [
        bin_rate(df, "EMA20_SLOPE", "POS", df.warning_ema20_slope60 > 0),
        bin_rate(df, "EMA20_SLOPE", "NONPOS", df.warning_ema20_slope60 <= 0),
        bin_rate(df, "EMA7_SLOPE", "POS", df.warning_ema7_slope60 > 0),
        bin_rate(df, "EMA7_SLOPE", "NONPOS", df.warning_ema7_slope60 <= 0),
    ]
    return pd.DataFrame(rows)


def fold_stability(df):
    # Four contiguous folds by warning chronology; no shuffling.
    folds = np.array_split(np.arange(len(df)), 4)
    rows = []
    for fi, pos in enumerate(folds, 1):
        g = df.iloc[pos]
        for feat in CORE_FEATURES:
            de = g[g.eventual_deep]
            nd = g[~g.eventual_deep]
            md = float(de[feat].median()) if len(de) and de[feat].notna().any() else np.nan
            mn = float(nd[feat].median()) if len(nd) and nd[feat].notna().any() else np.nan
            direction = "DEEP_HIGH" if np.isfinite(md) and np.isfinite(mn) and md > mn else (
                "DEEP_LOW" if np.isfinite(md) and np.isfinite(mn) and md < mn else "TIE"
            )
            rows.append({
                "fold": fi,
                "start_idx": int(g.idx.min()),
                "end_idx": int(g.idx.max()),
                "n": len(g),
                "deep_n": int(g.eventual_deep.sum()),
                "nondeep_n": int((~g.eventual_deep).sum()),
                "feature": feat,
                "deep_median": md,
                "nondeep_median": mn,
                "auc_deep_high": rank_auc(g[feat], g.eventual_deep),
                "direction": direction,
            })
    return pd.DataFrame(rows)


def summarize_folds(folds):
    expected = {
        "time_to05_min": "DEEP_LOW",
        "warning_min": "DEEP_LOW",
        "posthinge_max_close_progress": "DEEP_HIGH",
        "posthinge_min_close_progress": "DEEP_HIGH",
        "warning_ema20_slope60": "DEEP_HIGH",
        "warning_ema7_slope60": "DEEP_HIGH",
    }
    rows = []
    for feat, exp in expected.items():
        g = folds[folds.feature.eq(feat)]
        valid = g[g.direction.ne("TIE")]
        match = int((valid.direction == exp).sum())
        rows.append({
            "feature": feat,
            "expected_direction": exp,
            "folds_matching": match,
            "folds_valid": len(valid),
            "match_rate": float(match / len(valid)) if len(valid) else np.nan,
            "median_fold_auc": float(g.auc_deep_high.median()) if g.auc_deep_high.notna().any() else np.nan,
        })
    return pd.DataFrame(rows)


def family_monotonicity(bins):
    # Expected ordering only, no fitted thresholds.
    order_map = {
        "HINGE_AGE": ["<=120m", "125-240m", ">240m"],
        "WARNING_AGE": ["<=240m", "245-360m", ">360m"],
        "RETAINED_FLOOR": ["<+0.20", "+0.20..<+0.30", ">=+0.30"],
        "HIGH_WATER_CLOSE": ["<+0.40", "+0.40..<+0.50", ">=+0.50"],
    }
    rows = []
    for fam, order in order_map.items():
        g = bins[bins.family.eq(fam)].set_index("bin").reindex(order)
        for period, col in [("full", "deep_rate"), ("disc", "disc_deep_rate"), ("val", "val_deep_rate")]:
            vals = g[col].to_numpy(dtype=float)
            finite = vals[np.isfinite(vals)]
            if len(finite) < 2:
                direction = "INSUFFICIENT"
            elif fam in ("HINGE_AGE", "WARNING_AGE"):
                direction = "EXPECTED" if np.all(np.diff(finite) <= 1e-12) else "NOT_MONOTONIC"
            else:
                direction = "EXPECTED" if np.all(np.diff(finite) >= -1e-12) else "NOT_MONOTONIC"
            rows.append({"family": fam, "period": period, "assessment": direction})
    return pd.DataFrame(rows)


def main():
    df = build_warning_cohort()
    df.to_csv(OUT / "s52e_warning_cohort.csv", index=False)

    bins = add_natural_bins(df)
    bins.to_csv(OUT / "s52e_natural_bins.csv", index=False)
    folds = fold_stability(df)
    folds.to_csv(OUT / "s52e_fold_features.csv", index=False)
    foldsum = summarize_folds(folds)
    foldsum.to_csv(OUT / "s52e_fold_summary.csv", index=False)
    mono = family_monotonicity(bins)
    mono.to_csv(OUT / "s52e_bin_monotonicity.csv", index=False)

    # Robustness verdict is descriptive: mechanism is considered supported when
    # at least 4/6 core continuous features match expected direction in >=3/4
    # chronological folds, AND early warning-age ordering is expected in both D/V.
    strong = foldsum[(foldsum.folds_valid >= 3) & (foldsum.folds_matching >= 3)]
    warn_mono = mono[(mono.family == "WARNING_AGE") & (mono.period.isin(["disc", "val"]))]
    mechanism_support = bool(len(strong) >= 4 and len(warn_mono) == 2 and (warn_mono.assessment == "EXPECTED").all())

    summary = {
        "events": len(df),
        "deep": int(df.eventual_deep.sum()),
        "nondeep": int((~df.eventual_deep).sum()),
        "strong_fold_features": strong.feature.tolist(),
        "strong_fold_feature_count": len(strong),
        "warning_age_disc_val_monotonic": bool(len(warn_mono) == 2 and (warn_mono.assessment == "EXPECTED").all()),
        "mechanism_support": mechanism_support,
        "fold_summary": foldsum.to_dict(orient="records"),
        "bin_monotonicity": mono.to_dict(orient="records"),
        "natural_bins": bins.to_dict(orient="records"),
    }
    (OUT / "s52e_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x):
        return "NA" if not np.isfinite(x) else f"{100*x:.1f}%"

    lines = [
        "# BTC Temporal Saturday T-Method S5.2E — Timing / Path Robustness",
        "",
        "**Status:** COMPLETE — ROBUSTNESS ONLY; NO IMMUNITY ACTION",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen cohort",
        f"- Exact warning cohort: **{len(df)}**",
        f"- Latent future-deep: **{int(df.eventual_deep.sum())}**; nondeep: **{int((~df.eventual_deep).sum())}**",
        "- No PnL threshold optimization and no future label used in a trading rule.",
        "",
        "## Natural-bin deep rates",
        "| Family | Bin | N | Deep | D N/rate | V N/rate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in bins.iterrows():
        lines.append(f"| {r.family} | {r['bin']} | {int(r.n)} | {pct(r.deep_rate)} | {int(r.disc_n)}/{pct(r.disc_deep_rate)} | {int(r.val_n)}/{pct(r.val_deep_rate)} |")
    lines += [
        "",
        "## Four chronological folds",
        "| Feature | Expected | Matching folds | Valid folds | Match rate | Median fold AUC |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in foldsum.iterrows():
        lines.append(f"| {r.feature} | {r.expected_direction} | {int(r.folds_matching)} | {int(r.folds_valid)} | {pct(r.match_rate)} | {r.median_fold_auc:.3f} |")
    lines += [
        "",
        "## Natural-bin monotonicity",
        "| Family | Full | Discovery | Validation |",
        "|---|---|---|---|",
    ]
    for fam in ["HINGE_AGE", "WARNING_AGE", "RETAINED_FLOOR", "HIGH_WATER_CLOSE"]:
        q = mono[mono.family.eq(fam)].set_index("period")
        lines.append(f"| {fam} | {q.loc['full','assessment']} | {q.loc['disc','assessment']} | {q.loc['val','assessment']} |")
    lines += [
        "",
        "## Verdict",
        f"- Core features matching expected direction in >=3/4 folds: **{len(strong)}/6** — {', '.join(strong.feature.tolist()) if len(strong) else 'none'}",
        f"- Warning-age natural bins monotonic in both discovery and validation: **{'YES' if summary['warning_age_disc_val_monotonic'] else 'NO'}**",
        f"- Predeclared mechanism support gate: **{'PASS' if mechanism_support else 'FAIL'}**",
        "",
        "A PASS means the timing/path mechanism is robust enough to justify a separate, predeclared immunity ACTION test next; it does not itself promote an immunity rule.",
    ]
    (OUT / "S5.2E_CHECKPOINT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
