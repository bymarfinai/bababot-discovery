#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A26_PATH = Path(__file__).resolve().parent / "sol_long_15utc_loss_conversion_a26.py"
spec = importlib.util.spec_from_file_location("sol_a26", A26_PATH)
a26 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a26)

IN_LOSSES = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_LOSSES.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_Status.txt"

PARTS = ["development", "external", "reference_validation"]
EXPECTED = {"development": 115, "external": 51, "reference_validation": 68}
LOSS_CLASS = "L2_BREAK_FAST_FAIL_5M"
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12

FEATURE_FAMILY = {
    "prebreak_last_close_distance_H_R": "PRE_BREAK_APPROACH",
    "prebreak_return15_R": "PRE_BREAK_APPROACH",
    "prebreak_return30_R": "PRE_BREAK_APPROACH",
    "prebreak_return60_R": "PRE_BREAK_APPROACH",
    "prebreak_range30_R": "PRE_BREAK_APPROACH",
    "prebreak_range60_R": "PRE_BREAK_APPROACH",
    "prebreak_upper80_close_fraction60": "PRE_BREAK_APPROACH",
    "prebreak_nearH10_high_fraction60": "PRE_BREAK_APPROACH",
    "break_close_excess_R": "BREAK_CANDLE",
    "break_high_excess_R": "BREAK_CANDLE",
    "break_body_R": "BREAK_CANDLE",
    "break_range_R": "BREAK_CANDLE",
    "break_upper_wick_R": "BREAK_CANDLE",
    "break_lower_wick_R": "BREAK_CANDLE",
    "break_close_location": "BREAK_CANDLE",
    "fail_close_R": "FAILURE_CANDLE",
    "fail_low_R": "FAILURE_CANDLE",
    "fail_depth_below_H_R": "FAILURE_CANDLE",
    "fail_body_R": "FAILURE_CANDLE",
    "fail_range_R": "FAILURE_CANDLE",
    "fail_upper_wick_R": "FAILURE_CANDLE",
    "fail_lower_wick_R": "FAILURE_CANDLE",
    "fail_close_location": "FAILURE_CANDLE",
    "breakclose_to_failclose_drop_R": "BREAK_TO_FAIL",
    "breakhigh_to_faillow_excursion_R": "BREAK_TO_FAIL",
    "max_excess_H_by_fail_R": "BREAK_TO_FAIL",
    "max_depth_H_by_fail_R": "BREAK_TO_FAIL",
    "entry_to_break_min": "TIMING",
    "entry_to_failure_close_min": "TIMING",
}
FEATURES = list(FEATURE_FAMILY)


def fmt(v, d=3):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0 * float(v):.1f}%"


def load_l2() -> pd.DataFrame:
    t = pd.read_csv(IN_LOSSES)
    for c in ["execution_start", "entry_ts", "exit_ts"]:
        t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    for c in ["H", "L", "R", "pnl", "pnl_5bps", "dev_block", "entry_to_break_min", "break_to_fail_min"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")
    q = t[
        (t.role.astype(str) == "CENTRAL")
        & (t.partition.astype(str).isin(PARTS))
        & (t.loss_class.astype(str) == LOSS_CLASS)
    ].copy()
    return q.sort_values(["partition", "entry_ts"]).reset_index(drop=True)


def candle_features(row: pd.Series, x: pd.DataFrame) -> dict:
    H, L, R = float(row.H), float(row.L), float(row.R)
    entry = pd.Timestamp(row.entry_ts)
    break_ts = entry + pd.Timedelta(minutes=float(row.entry_to_break_min))
    fail_ts = break_ts + pd.Timedelta(minutes=float(row.break_to_fail_min))
    fail_close_ts = fail_ts + BAR

    if abs(float(row.break_to_fail_min) - 5.0) > 1e-9:
        raise ValueError("non-5m row inside L2")
    if fail_close_ts != pd.Timestamp(row.exit_ts):
        raise ValueError(f"failure close != frozen exit: {fail_close_ts} vs {row.exit_ts}")
    if break_ts not in x.index or fail_ts not in x.index:
        raise ValueError("break/failure candle missing")

    br = x.loc[break_ts]
    fl = x.loc[fail_ts]
    pre = x[(x.index < break_ts) & (x.index >= break_ts - pd.Timedelta(minutes=60))].copy()

    def ret(nbars: int) -> float:
        if len(pre) < nbars + 1:
            return np.nan
        c = pre.close.to_numpy(dtype=float)
        return (float(c[-1]) - float(c[-(nbars + 1)])) / R

    def rr(nbars: int) -> float:
        if len(pre) < nbars:
            return np.nan
        z = pre.iloc[-nbars:]
        return (float(z.high.max()) - float(z.low.min())) / R

    if len(pre):
        p60 = pre.iloc[-12:]
        upper80 = float((p60.close >= L + 0.80 * R).mean())
        nearh10 = float((p60.high >= H - 0.10 * R).mean())
        pre_dist = (H - float(pre.close.iloc[-1])) / R
    else:
        upper80 = nearh10 = pre_dist = np.nan

    bo, bh, bl, bc = map(float, [br.open, br.high, br.low, br.close])
    fo, fh, flw, fc = map(float, [fl.open, fl.high, fl.low, fl.close])
    brng = bh - bl
    frng = fh - flw

    path = x[(x.index >= entry) & (x.index <= fail_ts)]
    max_hi = float(path.high.max()) if len(path) else bh
    min_lo = float(path.low.min()) if len(path) else flw

    return {
        "break_ts": break_ts,
        "failure_ts": fail_ts,
        "failure_close_ts": fail_close_ts,
        "prebreak_last_close_distance_H_R": pre_dist,
        "prebreak_return15_R": ret(3),
        "prebreak_return30_R": ret(6),
        "prebreak_return60_R": ret(12),
        "prebreak_range30_R": rr(6),
        "prebreak_range60_R": rr(12),
        "prebreak_upper80_close_fraction60": upper80,
        "prebreak_nearH10_high_fraction60": nearh10,
        "break_close_excess_R": (bc - H) / R,
        "break_high_excess_R": (bh - H) / R,
        "break_body_R": (bc - bo) / R,
        "break_range_R": brng / R,
        "break_upper_wick_R": (bh - max(bo, bc)) / R,
        "break_lower_wick_R": (min(bo, bc) - bl) / R,
        "break_close_location": (bc - bl) / brng if brng > EPS else 0.5,
        "fail_close_R": (fc - H) / R,
        "fail_low_R": (flw - H) / R,
        "fail_depth_below_H_R": (H - fc) / R,
        "fail_body_R": (fc - fo) / R,
        "fail_range_R": frng / R,
        "fail_upper_wick_R": (fh - max(fo, fc)) / R,
        "fail_lower_wick_R": (min(fo, fc) - flw) / R,
        "fail_close_location": (fc - flw) / frng if frng > EPS else 0.5,
        "breakclose_to_failclose_drop_R": (bc - fc) / R,
        "breakhigh_to_faillow_excursion_R": (bh - flw) / R,
        "max_excess_H_by_fail_R": max(0.0, (max_hi - H) / R),
        "max_depth_H_by_fail_R": max(0.0, (H - min_lo) / R),
        "entry_to_break_min": float(row.entry_to_break_min),
        "entry_to_failure_close_min": float((fail_close_ts - entry) / pd.Timedelta(minutes=1)),
    }


def effect_stats(q: pd.DataFrame, feature: str) -> dict:
    a = pd.to_numeric(q.loc[q.latent_class == "LATENT_RECOVERABLE", feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    b = pd.to_numeric(q.loc[q.latent_class == "TRUE_FAILURE_PROXY", feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(a) == 0 or len(b) == 0:
        return {"latent_n": len(a), "true_n": len(b), "latent_median": np.nan, "true_median": np.nan, "gap": np.nan, "effect": np.nan}
    am = float(a.median()); bm = float(b.median()); gap = am - bm
    aiqr = float(a.quantile(.75) - a.quantile(.25)); biqr = float(b.quantile(.75) - b.quantile(.25))
    denom = (aiqr + biqr) / 2.0
    effect = abs(gap) / denom if denom > EPS else (np.inf if abs(gap) > EPS else 0.0)
    return {"latent_n": len(a), "true_n": len(b), "latent_median": am, "true_median": bm, "gap": gap, "effect": effect}


def main() -> None:
    cohort = load_l2()
    counts = cohort.groupby("partition").size().to_dict()
    count_ok = all(int(counts.get(k, 0)) == v for k, v in EXPECTED.items())

    x, coverage = a26.a2.a1.load5()
    enriched = []
    errors = []
    for i, r in cohort.iterrows():
        try:
            z = r.to_dict()
            z.update(candle_features(r, x))
            enriched.append(z)
        except Exception as e:
            errors.append((int(i), str(e)))

    trades = pd.DataFrame(enriched)
    causal_ok = bool(count_ok and len(errors) == 0 and len(trades) == sum(EXPECTED.values()))
    trades.to_csv(OUT_TRADES, index=False)

    rows = []
    if causal_ok:
        for feature in FEATURES:
            dev = effect_stats(trades[trades.partition == "development"], feature)
            ext = effect_stats(trades[trades.partition == "external"], feature)
            rv = effect_stats(trades[trades.partition == "reference_validation"], feature)
            sign = int(np.sign(dev["gap"])) if pd.notna(dev["gap"]) else 0

            adequate = same = 0
            block_gaps = []
            for bi in range(6):
                b = trades[(trades.partition == "development") & (pd.to_numeric(trades.dev_block, errors="coerce") == bi)]
                bs = effect_stats(b, feature)
                ok = bs["latent_n"] >= 5 and bs["true_n"] >= 5
                if ok:
                    adequate += 1
                    if sign != 0 and pd.notna(bs["gap"]) and int(np.sign(bs["gap"])) == sign:
                        same += 1
                block_gaps.append(bs["gap"])

            counts_ok = bool(
                dev["latent_n"] >= 40 and dev["true_n"] >= 40
                and ext["latent_n"] >= 20 and ext["true_n"] >= 20
                and rv["latent_n"] >= 20 and rv["true_n"] >= 20
            )
            oos_sign_ok = bool(
                sign != 0
                and pd.notna(ext["gap"]) and int(np.sign(ext["gap"])) == sign
                and pd.notna(rv["gap"]) and int(np.sign(rv["gap"])) == sign
            )
            block_ok = bool(adequate >= 4 and same >= 4)
            directional = bool(counts_ok and block_ok and oos_sign_ok)
            strong = bool(
                directional
                and pd.notna(dev["effect"]) and dev["effect"] >= 0.30
                and pd.notna(ext["effect"]) and ext["effect"] >= 0.10
                and pd.notna(rv["effect"]) and rv["effect"] >= 0.10
            )
            row = {
                "family": FEATURE_FAMILY[feature], "feature": feature,
                "dev_latent_n": dev["latent_n"], "dev_true_n": dev["true_n"],
                "dev_latent_median": dev["latent_median"], "dev_true_median": dev["true_median"],
                "dev_gap": dev["gap"], "dev_effect_IQR": dev["effect"],
                "adequate_dev_blocks": adequate, "same_sign_dev_blocks": same,
                "external_latent_n": ext["latent_n"], "external_true_n": ext["true_n"],
                "external_gap": ext["gap"], "external_effect_IQR": ext["effect"],
                "reference_latent_n": rv["latent_n"], "reference_true_n": rv["true_n"],
                "reference_gap": rv["gap"], "reference_effect_IQR": rv["effect"],
                "counts_ok": counts_ok, "block_ok": block_ok, "oos_sign_ok": oos_sign_ok,
                "directionally_replicated": directional, "strong_replicated": strong,
            }
            for j, g in enumerate(block_gaps, 1): row[f"b{j}_gap"] = g
            rows.append(row)

    features = pd.DataFrame(rows)
    if len(features):
        features = features.sort_values(["strong_replicated", "directionally_replicated", "dev_effect_IQR"], ascending=[False, False, False], na_position="last")
    features.to_csv(OUT_FEATURES, index=False)

    directional_n = int(features.directionally_replicated.sum()) if len(features) else 0
    strong_n = int(features.strong_replicated.sum()) if len(features) else 0
    if not causal_ok:
        status = "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_RECONCILIATION_FAIL"
    elif directional_n > 0:
        status = "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_SUPPORTED_FOR_A50B"
    else:
        status = "SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_INCONCLUSIVE"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC L2 Fast-Fail Anatomy — A50 Result", "",
        "A50 isolates `L2_BREAK_FAST_FAIL_5M` from the frozen A20 15UTC parent and compares latent-recoverable versus true-failure L2 using only information available by the completed 5m failure candle.", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.",
        f"Count reconciliation: **{count_ok}**. Causal/timestamp reconciliation: **{causal_ok}**. Enriched rows: **{len(trades)}/{sum(EXPECTED.values())}**. Errors: **{len(errors)}**.", "",
        "## Cohort", "",
        "| Partition | L2 N | Latent recoverable | True failure | Latent rate | Median recovery (latent) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for part in PARTS:
        q = trades[trades.partition == part]
        lat = q[q.latent_class == "LATENT_RECOVERABLE"]
        tru = q[q.latent_class == "TRUE_FAILURE_PROXY"]
        lines.append(f"| {part} | {len(q)} | {len(lat)} | {len(tru)} | {pct(len(lat)/len(q) if len(q) else np.nan)} | {fmt(pd.to_numeric(lat.latent_recovery_min, errors='coerce').median() if len(lat) else np.nan,0)}m |")
    lines += ["", "## Replicated separators at/before L2 failure", "",
              "| Family | Feature | Dev latent med | Dev true med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    rep = features[features.directionally_replicated == True] if len(features) else pd.DataFrame()
    if len(rep):
        for _, r in rep.iterrows():
            lines.append(f"| {r.family} | {r.feature} | {fmt(r.dev_latent_median)} | {fmt(r.dev_true_median)} | {fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {fmt(r.external_effect_IQR)} | {fmt(r.reference_effect_IQR)} | {'YES' if bool(r.strong_replicated) else 'NO'} |")
    else:
        lines.append("| - | none | - | - | - | - | - | - | - |")

    lines += ["", "## Strongest Development diagnostics", "",
              "| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |",
              "|---|---|---:|---:|---|---|---:|"]
    for _, r in features.head(15).iterrows():
        lines.append(f"| {r.family} | {r.feature} | {fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {fmt(r.external_gap)}/{fmt(r.external_effect_IQR)} | {fmt(r.reference_gap)}/{fmt(r.reference_effect_IQR)} | {'YES' if bool(r.directionally_replicated) else 'NO'} |")

    lines += ["", "## Decision", "", f"Directionally replicated features: **{directional_n}**. Strong replicated: **{strong_n}**.", "", f"**Status: {status}**", ""]
    if directional_n:
        lines.append("A50B is authorized to test one minimal causal decision rule at the L2 failure decision point. Development chooses the rule; External and Reference Validation remain untouched until frozen.")
    else:
        lines.append("No A50B rule is authorized from this feature family. Do not threshold-mine the failed diagnostics.")
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
