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

OUT_TRADES = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_Status.txt"

PARTS = ["development", "external", "reference_validation"]
EXPECTED_COUNTS = {"development": 601, "external": 281, "reference_validation": 337}
EPS = 1e-12

FEATURE_FAMILY = {
    "fill_delay_min": "TIMING",
    "prefill_bar_count": "TIMING",
    "immediate_fill": "TIMING",
    "prefill_last_close_location_R": "LOCATION",
    "prefill_last_close_distance_H_R": "LOCATION",
    "prefill_min_low_location_R": "LOCATION",
    "prefill_max_close_location_R": "LOCATION",
    "prefill_close_range_R": "LOCATION",
    "prefill_realized_close_path_R": "PATH",
    "prefill_signed_efficiency": "PATH",
    "prefill_upstep_fraction": "PATH",
    "prefill_upper80_close_fraction": "PRESSURE",
    "prefill_upper90_close_fraction": "PRESSURE",
    "prefill_nearH10_high_fraction": "PRESSURE",
    "prefill_nearH05_high_fraction": "PRESSURE",
    "prefill_nearH05_episode_count": "PRESSURE",
    "prefill_last30_range_R": "LATE_STATE",
    "prefill_last30_efficiency": "LATE_STATE",
    "prefill_last30_upstep_fraction": "LATE_STATE",
    "prefill_last60_range_R": "LATE_STATE",
    "prefill_last60_efficiency": "LATE_STATE",
    "prefill_last60_upstep_fraction": "LATE_STATE",
}
FEATURES = list(FEATURE_FAMILY)


def path_efficiency(q: pd.DataFrame) -> float:
    if len(q) == 0:
        return np.nan
    cl = q.close.to_numpy(dtype=float)
    first = float(q.open.iloc[0])
    steps = np.diff(np.concatenate(([first], cl)))
    path = float(np.abs(steps).sum())
    return float((cl[-1] - first) / path) if path > EPS else 0.0


def upstep_fraction(q: pd.DataFrame) -> float:
    if len(q) == 0:
        return np.nan
    cl = q.close.to_numpy(dtype=float)
    first = float(q.open.iloc[0])
    steps = np.diff(np.concatenate(([first], cl)))
    return float(np.mean(steps > 0)) if len(steps) else np.nan


def episode_count(mask: np.ndarray) -> int:
    if len(mask) == 0:
        return 0
    m = mask.astype(bool)
    starts = m & np.concatenate(([True], ~m[:-1]))
    return int(starts.sum())


def prefill_features(x: pd.DataFrame, r: pd.Series) -> dict:
    es = pd.Timestamp(r.execution_start)
    et = pd.Timestamp(r.entry_ts)
    H, L, R = float(r.H), float(r.L), float(r.R)
    if pd.isna(et) or et < es:
        raise ValueError("entry before execution_start or missing")
    if R <= EPS:
        raise ValueError("non-positive R")

    q = x[(x.index >= es) & (x.index < et)].copy()
    if len(q) and not bool((q.index < et).all()):
        raise ValueError("prefill leakage")

    delay = float((et - es) / pd.Timedelta(minutes=1))
    out = {
        "fill_delay_min": delay,
        "prefill_bar_count": float(len(q)),
        "immediate_fill": 1.0 if len(q) == 0 else 0.0,
    }

    if len(q) == 0:
        for f in FEATURES:
            out.setdefault(f, np.nan)
        out["fill_delay_min"] = delay
        out["prefill_bar_count"] = 0.0
        out["immediate_fill"] = 1.0
        return out

    cl = q.close.to_numpy(dtype=float)
    hi = q.high.to_numpy(dtype=float)
    lo = q.low.to_numpy(dtype=float)
    upper80 = L + 0.80 * R
    upper90 = L + 0.90 * R
    near10 = H - 0.10 * R
    near05 = H - 0.05 * R
    first = float(q.open.iloc[0])
    steps = np.diff(np.concatenate(([first], cl)))
    realized = float(np.abs(steps).sum())

    out.update({
        "prefill_last_close_location_R": (float(cl[-1]) - L) / R,
        "prefill_last_close_distance_H_R": (H - float(cl[-1])) / R,
        "prefill_min_low_location_R": (float(np.min(lo)) - L) / R,
        "prefill_max_close_location_R": (float(np.max(cl)) - L) / R,
        "prefill_close_range_R": (float(np.max(cl)) - float(np.min(cl))) / R,
        "prefill_realized_close_path_R": realized / R,
        "prefill_signed_efficiency": float((cl[-1] - first) / realized) if realized > EPS else 0.0,
        "prefill_upstep_fraction": float(np.mean(steps > 0)) if len(steps) else np.nan,
        "prefill_upper80_close_fraction": float(np.mean(cl >= upper80)),
        "prefill_upper90_close_fraction": float(np.mean(cl >= upper90)),
        "prefill_nearH10_high_fraction": float(np.mean(hi >= near10)),
        "prefill_nearH05_high_fraction": float(np.mean(hi >= near05)),
        "prefill_nearH05_episode_count": float(episode_count(hi >= near05)),
    })

    for mins in [30, 60]:
        n = mins // 5
        if len(q) >= n:
            z = q.iloc[-n:]
            out[f"prefill_last{mins}_range_R"] = float(z.high.max() - z.low.min()) / R
            out[f"prefill_last{mins}_efficiency"] = path_efficiency(z)
            out[f"prefill_last{mins}_upstep_fraction"] = upstep_fraction(z)
        else:
            out[f"prefill_last{mins}_range_R"] = np.nan
            out[f"prefill_last{mins}_efficiency"] = np.nan
            out[f"prefill_last{mins}_upstep_fraction"] = np.nan

    return out


def main() -> None:
    parent = a45.load_parent()
    counts = parent.groupby("partition").size().to_dict()
    count_ok = all(int(counts.get(k, 0)) == v for k, v in EXPECTED_COUNTS.items())
    ts_ok = bool((pd.to_datetime(parent.entry_ts, utc=True) >= pd.to_datetime(parent.execution_start, utc=True)).all())

    x, coverage = a45.a2.a1.load5()
    enriched, errors = [], []
    for idx, r in parent.iterrows():
        try:
            z = r.to_dict()
            z.update(prefill_features(x, r))
            z["stress_outcome"] = "WIN" if float(r.pnl_5bps) > 0 else "FAIL"
            z["raw_outcome"] = "WIN" if float(r.pnl) > 0 else "FAIL"
            enriched.append(z)
        except Exception as exc:
            errors.append((int(idx), str(exc)))

    trades = pd.DataFrame(enriched)
    full_recon = bool(count_ok and ts_ok and not errors and len(trades) == sum(EXPECTED_COUNTS.values()))

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
        status = "SOL_LONG_15UTC_PREFILL_PATH_A47B_RECONCILIATION_FAIL"
    elif bool(features.replicated_directional.any()):
        status = "SOL_LONG_15UTC_PREFILL_PATH_A47B_SUPPORTED_FOR_A47C"
    else:
        status = "SOL_LONG_15UTC_PREFILL_PATH_A47B_INCONCLUSIVE"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC Pre-Fill Path Anatomy — A47B Result", "",
        "A47B keeps the A20 parent frozen and uses only completed 5m bars from 15:00 UTC strictly before the frozen resting-H entry timestamp.", "",
        f"Raw SOLUSDT 5m coverage: **{100.0*coverage:.4f}%**.",
        f"Count reconciliation: **{count_ok}**. Timestamp causality: **{ts_ok}**. Enriched rows: **{len(trades)}/{sum(EXPECTED_COUNTS.values())}**. Errors: **{len(errors)}**.", "",
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

    lines += ["", "## Replicated pre-fill separators", "",
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

    lines += ["", "## Strongest Development diagnostics", "",
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
    lines += ["", "## Decision", "", f"Replicated directional features: **{rep_n}**. Strong replicated: **{strong_n}**.", "", f"**Status: {status}**", ""]
    if errors:
        lines += ["First errors:", ""] + [f"- row {i}: {e}" for i, e in errors[:10]] + [""]
    lines += ["A47B changes no trade. A47C is authorized only when a replicated causal pre-fill separator exists.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
