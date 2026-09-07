#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A45_PATH = Path(__file__).resolve().parent / "sol_long_15utc_parent_prerange_anatomy_a45.py"
spec = importlib.util.spec_from_file_location("sol_a45", A45_PATH)
a45 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a45)

OUT_TRADES = ROOT / "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_Status.txt"

PARTS = ["development", "external", "reference_validation"]
EXPECTED_COUNTS = {"development": 601, "external": 281, "reference_validation": 337}
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12

FEATURE_FAMILY = {
    # pre-reference regime
    "pre6_return_R": "PRE_REGIME", "pre12_return_R": "PRE_REGIME", "pre24_return_R": "PRE_REGIME",
    "pre6_range_R": "PRE_REGIME", "pre12_range_R": "PRE_REGIME", "pre24_range_R": "PRE_REGIME",
    "ref_to_pre6_range_ratio": "PRE_REGIME", "ref_to_pre12_range_ratio": "PRE_REGIME", "ref_to_pre24_range_ratio": "PRE_REGIME",
    "H_vs_pre6_high_R": "PRE_REGIME", "H_vs_pre12_high_R": "PRE_REGIME", "H_vs_pre24_high_R": "PRE_REGIME",
    "L_vs_pre6_low_R": "PRE_REGIME", "L_vs_pre12_low_R": "PRE_REGIME", "L_vs_pre24_low_R": "PRE_REGIME",
    # pressure/freshness
    "close_upper70_fraction": "H_PRESSURE", "close_upper80_fraction": "H_PRESSURE", "close_upper90_fraction": "H_PRESSURE",
    "high_nearH10_fraction": "H_PRESSURE", "high_nearH05_fraction": "H_PRESSURE",
    "close_nearH10_fraction": "H_PRESSURE", "close_nearH05_fraction": "H_PRESSURE",
    "last_exact_H_age_min": "H_PRESSURE", "first_to_last_nearH05_span_min": "H_PRESSURE",
    "nearH05_after_first_H_fraction": "H_PRESSURE",
    # late compression
    "late30_range_R": "LATE_COMPRESSION", "late60_range_R": "LATE_COMPRESSION", "late90_range_R": "LATE_COMPRESSION",
    "late30_to_prior330_range_ratio": "LATE_COMPRESSION", "late60_to_prior300_range_ratio": "LATE_COMPRESSION",
    "late90_to_prior270_range_ratio": "LATE_COMPRESSION", "distance_to_H_R_at_15": "LATE_COMPRESSION",
    # approach quality
    "approach30_efficiency": "APPROACH", "approach60_efficiency": "APPROACH", "approach120_efficiency": "APPROACH",
    "upstep_fraction_30": "APPROACH", "upstep_fraction_60": "APPROACH", "upstep_fraction_120": "APPROACH",
    "upper80_fraction_last30": "APPROACH", "upper80_fraction_last60": "APPROACH", "upper80_fraction_last120": "APPROACH",
}
FEATURES = list(FEATURE_FAMILY)


def window_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, expected: int) -> pd.DataFrame:
    q = x[(x.index >= start) & (x.index < end)].copy()
    if len(q) != expected or q.index[0] != start or q.index[-1] != end - BAR:
        raise ValueError(f"incomplete window {start} {end} expected={expected} got={len(q)}")
    return q


def range_value(q: pd.DataFrame) -> float:
    return float(q.high.max() - q.low.min())


def return_value(q: pd.DataFrame) -> float:
    return float(q.close.iloc[-1] - q.open.iloc[0])


def approach_efficiency(q: pd.DataFrame) -> float:
    cl = q.close.to_numpy(dtype=float)
    first = float(q.open.iloc[0])
    steps = np.diff(np.concatenate(([first], cl)))
    path = float(np.abs(steps).sum())
    return float((cl[-1] - first) / path) if path > EPS else 0.0


def upstep_fraction(q: pd.DataFrame) -> float:
    cl = q.close.to_numpy(dtype=float)
    first = float(q.open.iloc[0])
    steps = np.diff(np.concatenate(([first], cl)))
    return float(np.mean(steps > 0)) if len(steps) else np.nan


def feature_row(x: pd.DataFrame, r: pd.Series) -> dict:
    es = pd.Timestamp(r.execution_start)
    rs = es - pd.Timedelta(hours=6)  # 09:00 for 15UTC decision
    ref = window_slice(x, rs, es, 72)
    pre6 = window_slice(x, rs - pd.Timedelta(hours=6), rs, 72)
    pre12 = window_slice(x, rs - pd.Timedelta(hours=12), rs, 144)
    pre24 = window_slice(x, rs - pd.Timedelta(hours=24), rs, 288)

    H, L, R = float(r.H), float(r.L), float(r.R)
    if R <= EPS:
        raise ValueError("non-positive frozen R")
    tol = max(1e-8, abs(R) * 1e-9)
    if not (
        np.isclose(float(ref.high.max()), H, rtol=1e-10, atol=tol)
        and np.isclose(float(ref.low.min()), L, rtol=1e-10, atol=tol)
        and np.isclose(range_value(ref), R, rtol=1e-10, atol=tol)
    ):
        raise ValueError("frozen H/L/R mismatch")

    out: dict[str, float] = {}
    for hours, q in [(6, pre6), (12, pre12), (24, pre24)]:
        pr = range_value(q)
        out[f"pre{hours}_return_R"] = return_value(q) / R
        out[f"pre{hours}_range_R"] = pr / R
        out[f"ref_to_pre{hours}_range_ratio"] = R / pr if pr > EPS else np.nan
        out[f"H_vs_pre{hours}_high_R"] = (H - float(q.high.max())) / R
        out[f"L_vs_pre{hours}_low_R"] = (L - float(q.low.min())) / R

    close = ref.close.to_numpy(dtype=float)
    high = ref.high.to_numpy(dtype=float)
    upper70 = L + 0.70 * R
    upper80 = L + 0.80 * R
    upper90 = L + 0.90 * R
    nearH10 = H - 0.10 * R
    nearH05 = H - 0.05 * R

    out.update({
        "close_upper70_fraction": float(np.mean(close >= upper70)),
        "close_upper80_fraction": float(np.mean(close >= upper80)),
        "close_upper90_fraction": float(np.mean(close >= upper90)),
        "high_nearH10_fraction": float(np.mean(high >= nearH10)),
        "high_nearH05_fraction": float(np.mean(high >= nearH05)),
        "close_nearH10_fraction": float(np.mean(close >= nearH10)),
        "close_nearH05_fraction": float(np.mean(close >= nearH05)),
    })

    exact_h = np.where(np.isclose(high, H, rtol=1e-10, atol=tol))[0]
    if len(exact_h):
        last_i = int(exact_h[-1])
        out["last_exact_H_age_min"] = float((72 - (last_i + 1)) * 5)
    else:
        out["last_exact_H_age_min"] = np.nan

    near = np.where(high >= nearH05)[0]
    if len(near):
        first_near, last_near = int(near[0]), int(near[-1])
        out["first_to_last_nearH05_span_min"] = float((last_near - first_near) * 5)
        after = high[first_near:] >= nearH05
        out["nearH05_after_first_H_fraction"] = float(np.mean(after))
    else:
        out["first_to_last_nearH05_span_min"] = 0.0
        out["nearH05_after_first_H_fraction"] = 0.0

    for mins in [30, 60, 90]:
        n = mins // 5
        late = ref.iloc[-n:]
        prior = ref.iloc[:-n]
        lr = range_value(late)
        pr = range_value(prior)
        out[f"late{mins}_range_R"] = lr / R
        out[f"late{mins}_to_prior{360-mins}_range_ratio"] = lr / pr if pr > EPS else np.nan

    out["distance_to_H_R_at_15"] = (H - float(ref.close.iloc[-1])) / R

    for mins in [30, 60, 120]:
        n = mins // 5
        q = ref.iloc[-n:]
        out[f"approach{mins}_efficiency"] = approach_efficiency(q)
        out[f"upstep_fraction_{mins}"] = upstep_fraction(q)
        out[f"upper80_fraction_last{mins}"] = float(np.mean(q.close.to_numpy(dtype=float) >= upper80))

    return out


def main() -> None:
    parent = a45.load_parent()
    counts = parent.groupby("partition").size().to_dict()
    count_ok = all(int(counts.get(k, 0)) == v for k, v in EXPECTED_COUNTS.items())

    x, coverage = a45.a2.a1.load5()
    enriched = []
    errors = []
    for idx, r in parent.iterrows():
        try:
            z = r.to_dict()
            z.update(feature_row(x, r))
            z["stress_outcome"] = "WIN" if float(r.pnl_5bps) > 0 else "FAIL"
            z["raw_outcome"] = "WIN" if float(r.pnl) > 0 else "FAIL"
            enriched.append(z)
        except Exception as exc:
            errors.append((int(idx), str(exc)))

    trades = pd.DataFrame(enriched)
    full_recon = bool(count_ok and not errors and len(trades) == sum(EXPECTED_COUNTS.values()))

    feature_rows = []
    if full_recon:
        for feature in FEATURES:
            dev = a45.effect_stats(trades[trades.partition == "development"], feature)
            ext = a45.effect_stats(trades[trades.partition == "external"], feature)
            refv = a45.effect_stats(trades[trades.partition == "reference_validation"], feature)
            pooled_sign = int(np.sign(dev["gap"])) if pd.notna(dev["gap"]) else 0

            adequate_blocks = 0
            same_sign_blocks = 0
            row = {"family": FEATURE_FAMILY[feature], "feature": feature}
            for bi in range(6):
                b = trades[(trades.partition == "development") & (pd.to_numeric(trades.dev_block, errors="coerce") == bi)]
                bs = a45.effect_stats(b, feature)
                adequate = bool(bs["win_n"] >= 20 and bs["fail_n"] >= 20)
                if adequate:
                    adequate_blocks += 1
                    if pooled_sign != 0 and pd.notna(bs["gap"]) and int(np.sign(bs["gap"])) == pooled_sign:
                        same_sign_blocks += 1
                row[f"b{bi+1}_gap"] = bs["gap"]
                row[f"b{bi+1}_effect_IQR"] = bs["effect"]

            counts_ok = bool(
                dev["win_n"] >= 100 and dev["fail_n"] >= 100
                and ext["win_n"] >= 50 and ext["fail_n"] >= 50
                and refv["win_n"] >= 50 and refv["fail_n"] >= 50
            )
            dev_effect_ok = bool(pd.notna(dev["effect"]) and dev["effect"] >= 0.25)
            block_ok = bool(adequate_blocks >= 4 and same_sign_blocks >= 4)
            oos_sign_ok = bool(
                pooled_sign != 0
                and pd.notna(ext["gap"]) and int(np.sign(ext["gap"])) == pooled_sign
                and pd.notna(refv["gap"]) and int(np.sign(refv["gap"])) == pooled_sign
            )
            oos_effect_ok = bool(
                pd.notna(ext["effect"]) and ext["effect"] >= 0.10
                and pd.notna(refv["effect"]) and refv["effect"] >= 0.10
            )
            replicated = bool(counts_ok and dev_effect_ok and block_ok and oos_sign_ok and oos_effect_ok)
            strong = bool(replicated and dev["effect"] >= 0.35 and same_sign_blocks >= 5)

            row.update({
                "dev_win_n": dev["win_n"], "dev_fail_n": dev["fail_n"],
                "dev_win_median": dev["win_median"], "dev_fail_median": dev["fail_median"],
                "dev_gap": dev["gap"], "dev_effect_IQR": dev["effect"],
                "adequate_dev_blocks": adequate_blocks, "same_sign_dev_blocks": same_sign_blocks,
                "external_win_n": ext["win_n"], "external_fail_n": ext["fail_n"],
                "external_win_median": ext["win_median"], "external_fail_median": ext["fail_median"],
                "external_gap": ext["gap"], "external_effect_IQR": ext["effect"],
                "reference_win_n": refv["win_n"], "reference_fail_n": refv["fail_n"],
                "reference_win_median": refv["win_median"], "reference_fail_median": refv["fail_median"],
                "reference_gap": refv["gap"], "reference_effect_IQR": refv["effect"],
                "counts_ok": counts_ok, "dev_effect_ok": dev_effect_ok, "block_ok": block_ok,
                "oos_sign_ok": oos_sign_ok, "oos_effect_ok": oos_effect_ok,
                "replicated_directional": replicated, "strong_replicated": strong,
            })
            feature_rows.append(row)

    features = pd.DataFrame(feature_rows)
    if len(features):
        features = features.sort_values(
            ["strong_replicated", "replicated_directional", "dev_effect_IQR"],
            ascending=[False, False, False], na_position="last"
        ).reset_index(drop=True)

    trades.to_csv(OUT_TRADES, index=False)
    features.to_csv(OUT_FEATURES, index=False)

    if not full_recon:
        status = "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_RECONCILIATION_FAIL"
    elif bool(features.replicated_directional.any()):
        status = "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_SUPPORTED_FOR_A48"
    else:
        status = "SOL_LONG_15UTC_PREENTRY_QUALITY_A47_INCONCLUSIVE"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC Pre-Entry Quality Anatomy — A47 Result", "",
        "A47 keeps the A20 `R360/15 / E0_RESTING_H -> E40` parent frozen and studies only information known before the 15:00 UTC resting order.", "",
        f"Raw SOLUSDT 5m coverage: **{100.0 * coverage:.4f}%**.",
        f"Count reconciliation: **{count_ok}**. Enriched rows: **{len(trades)}/{sum(EXPECTED_COUNTS.values())}**. Window/geometry errors: **{len(errors)}**.", "",
        "## Frozen parent economics", "",
        "| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for part in PARTS:
        s = a45.summary(parent[parent.partition == part])
        lines.append(
            f"| {part} | {s['n']} | {a45.pct(s['wr'])} | {a45.fmt(s['pf'],2)} | ${a45.fmt(s['net'],2)} | "
            f"{a45.pct(s['wr_5bps'])} | {a45.fmt(s['pf_5bps'],2)} | ${a45.fmt(s['net_5bps'],2)} |"
        )

    lines += ["", "## Replicated pre-entry separators", "",
              "| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    if len(features) and bool(features.replicated_directional.any()):
        for _, r in features[features.replicated_directional == True].iterrows():
            lines.append(
                f"| {r.family} | {r.feature} | {a45.fmt(r.dev_win_median)} | {a45.fmt(r.dev_fail_median)} | "
                f"{a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | "
                f"{a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_effect_IQR)} | {'YES' if bool(r.strong_replicated) else 'NO'} |"
            )
    else:
        lines.append("| - | none | - | - | - | - | - | - | - |")

    lines += ["", "## Strongest Development diagnostics (not promoted unless replicated)", "",
              "| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |",
              "|---|---|---:|---:|---|---|---:|"]
    if len(features):
        for _, r in features.head(12).iterrows():
            lines.append(
                f"| {r.family} | {r.feature} | {a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | "
                f"{a45.fmt(r.external_gap)}/{a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_gap)}/{a45.fmt(r.reference_effect_IQR)} | "
                f"{'YES' if bool(r.replicated_directional) else 'NO'} |"
            )

    rep_n = int(features.replicated_directional.sum()) if len(features) else 0
    strong_n = int(features.strong_replicated.sum()) if len(features) else 0
    lines += ["", "## Decision", "",
              f"Replicated directional features: **{rep_n}**. Strong replicated: **{strong_n}**.", "",
              f"**Status: {status}**", ""]
    if errors:
        lines += ["First reconciliation errors:", ""] + [f"- row {i}: {e}" for i, e in errors[:10]] + [""]
    lines += ["A47 changes no trade. A48 is authorized only when A47 finds at least one replicated pre-entry separator.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
