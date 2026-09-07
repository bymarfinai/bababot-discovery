#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A2_PATH = Path(__file__).resolve().parent / "sol_long_h1_entry_econ_a2.py"
spec = importlib.util.spec_from_file_location("sol_a2", A2_PATH)
a2 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a2)

IN_A20 = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_TRADES.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_Status.txt"

CANDIDATE = "A20_Z1_R360_H15"
PARTS = ["development", "external", "reference_validation"]
EXPECTED_COUNTS = {"development": 601, "external": 281, "reference_validation": 337}
REF_MIN = 360
HOUR = 15
BAR = pd.Timedelta(minutes=5)
N_REF = REF_MIN // 5
EPS = 1e-12

FEATURES = [
    "range_width_pct",
    "open_location_R",
    "close_location_R",
    "net_return_R",
    "first_half_return_R",
    "second_half_return_R",
    "last60_return_R",
    "last120_return_R",
    "realized_close_path_R",
    "signed_path_efficiency",
    "high_time_fraction",
    "low_time_fraction",
    "high_minus_low_time_fraction",
    "first_half_range_fraction",
    "second_half_range_fraction",
    "mean_bar_range_R",
    "last60_bar_range_ratio",
]


def pf(vals) -> float:
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl <= EPS:
        return np.inf if gp > EPS else np.nan
    return gp / gl


def fmt(v, d=3):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0 * float(v):.1f}%"


def load_parent() -> pd.DataFrame:
    t = pd.read_csv(IN_A20)
    for c in ["execution_start", "h1_ts", "h1_break_ts", "entry_ts", "exit_ts", "invalidation_close_ts"]:
        if c in t.columns:
            t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    for c in ["ref_min", "hour", "H", "L", "R", "pnl", "pnl_5bps", "dev_block"]:
        if c in t.columns:
            t[c] = pd.to_numeric(t[c], errors="coerce")
    q = t[
        (t.candidate.astype(str) == CANDIDATE)
        & (t.role.astype(str) == "CANDIDATE")
        & (t.partition.astype(str).isin(PARTS))
        & (t.ref_min == REF_MIN)
        & (t.hour == HOUR)
    ].copy()
    return q.sort_values(["partition", "execution_start", "entry_ts"]).reset_index(drop=True)


def range_features(ref: pd.DataFrame, stored_R: float) -> dict:
    op = ref.open.to_numpy(dtype=float)
    hi = ref.high.to_numpy(dtype=float)
    lo = ref.low.to_numpy(dtype=float)
    cl = ref.close.to_numpy(dtype=float)
    R = float(stored_R)
    if len(ref) != N_REF or R <= EPS:
        raise ValueError("invalid reference window")

    first_open = float(op[0])
    last_close = float(cl[-1])
    mid_close = float(cl[(N_REF // 2) - 1])
    H = float(np.max(hi))
    L = float(np.min(lo))

    close_steps = np.diff(np.concatenate(([first_open], cl)))
    realized_abs = float(np.abs(close_steps).sum())
    bar_range = hi - lo
    prior300 = float(np.mean(bar_range[:-12]))
    last60 = float(np.mean(bar_range[-12:]))

    return {
        "range_width_pct": R / last_close if abs(last_close) > EPS else np.nan,
        "open_location_R": (first_open - L) / R,
        "close_location_R": (last_close - L) / R,
        "net_return_R": (last_close - first_open) / R,
        "first_half_return_R": (mid_close - first_open) / R,
        "second_half_return_R": (last_close - mid_close) / R,
        "last60_return_R": (last_close - float(cl[-13])) / R,
        "last120_return_R": (last_close - float(cl[-25])) / R,
        "realized_close_path_R": realized_abs / R,
        "signed_path_efficiency": (last_close - first_open) / realized_abs if realized_abs > EPS else 0.0,
        "high_time_fraction": float(np.argmax(hi)) / float(N_REF - 1),
        "low_time_fraction": float(np.argmin(lo)) / float(N_REF - 1),
        "high_minus_low_time_fraction": float(np.argmax(hi) - np.argmin(lo)) / float(N_REF - 1),
        "first_half_range_fraction": (float(np.max(hi[:36])) - float(np.min(lo[:36]))) / R,
        "second_half_range_fraction": (float(np.max(hi[36:])) - float(np.min(lo[36:]))) / R,
        "mean_bar_range_R": float(np.mean(bar_range)) / R,
        "last60_bar_range_ratio": last60 / prior300 if prior300 > EPS else np.nan,
    }


def effect_stats(q: pd.DataFrame, feature: str) -> dict:
    w = pd.to_numeric(q.loc[q.stress_outcome == "WIN", feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    f = pd.to_numeric(q.loc[q.stress_outcome == "FAIL", feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(w) == 0 or len(f) == 0:
        return {"win_n": len(w), "fail_n": len(f), "win_median": np.nan, "fail_median": np.nan, "gap": np.nan, "effect": np.nan}
    wm = float(w.median())
    fm = float(f.median())
    gap = wm - fm
    wi = float(w.quantile(0.75) - w.quantile(0.25))
    fi = float(f.quantile(0.75) - f.quantile(0.25))
    pooled_iqr = (wi + fi) / 2.0
    if pooled_iqr > EPS:
        effect = abs(gap) / pooled_iqr
    elif abs(gap) > EPS:
        effect = np.inf
    else:
        effect = 0.0
    return {"win_n": len(w), "fail_n": len(f), "win_median": wm, "fail_median": fm, "gap": gap, "effect": effect}


def summary(q: pd.DataFrame) -> dict:
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    return {
        "n": len(q),
        "wr": float((p > 0).mean()) if len(q) else np.nan,
        "pf": pf(p),
        "net": float(p.sum()),
        "wr_5bps": float((p5 > 0).mean()) if len(q) else np.nan,
        "pf_5bps": pf(p5),
        "net_5bps": float(p5.sum()),
    }


def main():
    parent = load_parent()
    counts = parent.groupby("partition").size().to_dict()
    count_ok = all(int(counts.get(k, 0)) == v for k, v in EXPECTED_COUNTS.items())

    x, coverage = a2.a1.load5()
    enriched = []
    ref_ok = True
    bad_rows = []

    for ridx, r in parent.iterrows():
        es = pd.Timestamp(r.execution_start)
        rs = es - pd.Timedelta(minutes=REF_MIN)
        ref = x[(x.index >= rs) & (x.index < es)].copy()
        complete = bool(
            len(ref) == N_REF
            and len(ref) > 0
            and ref.index[0] == rs
            and ref.index[-1] == es - BAR
        )
        if not complete:
            ref_ok = False
            bad_rows.append((int(ridx), "reference_bar_count_or_boundary"))
            continue

        H2 = float(ref.high.max())
        L2 = float(ref.low.min())
        R2 = H2 - L2
        tol = max(1e-8, abs(float(r.R)) * 1e-9)
        geometry_ok = bool(
            np.isclose(H2, float(r.H), rtol=1e-10, atol=tol)
            and np.isclose(L2, float(r.L), rtol=1e-10, atol=tol)
            and np.isclose(R2, float(r.R), rtol=1e-10, atol=tol)
        )
        if not geometry_ok:
            ref_ok = False
            bad_rows.append((int(ridx), "H_L_R_mismatch"))
            continue

        z = r.to_dict()
        z.update(range_features(ref, float(r.R)))
        z["reference_start"] = rs
        z["reference_end"] = es
        z["stress_outcome"] = "WIN" if float(r.pnl_5bps) > 0 else "FAIL"
        z["raw_outcome"] = "WIN" if float(r.pnl) > 0 else "FAIL"
        enriched.append(z)

    trades = pd.DataFrame(enriched)
    full_recon = bool(count_ok and ref_ok and len(trades) == sum(EXPECTED_COUNTS.values()))

    feature_rows = []
    if full_recon:
        for feature in FEATURES:
            dev = effect_stats(trades[trades.partition == "development"], feature)
            ext = effect_stats(trades[trades.partition == "external"], feature)
            refv = effect_stats(trades[trades.partition == "reference_validation"], feature)

            pooled_sign = int(np.sign(dev["gap"])) if pd.notna(dev["gap"]) else 0
            adequate_blocks = 0
            same_sign_blocks = 0
            block_gaps = []
            block_effects = []
            for bi in range(6):
                b = trades[(trades.partition == "development") & (pd.to_numeric(trades.dev_block, errors="coerce") == bi)]
                bs = effect_stats(b, feature)
                adequate = bool(bs["win_n"] >= 20 and bs["fail_n"] >= 20)
                if adequate:
                    adequate_blocks += 1
                    if pd.notna(bs["gap"]) and pooled_sign != 0 and int(np.sign(bs["gap"])) == pooled_sign:
                        same_sign_blocks += 1
                block_gaps.append(bs["gap"])
                block_effects.append(bs["effect"])

            counts_ok = bool(
                dev["win_n"] >= 100 and dev["fail_n"] >= 100
                and ext["win_n"] >= 50 and ext["fail_n"] >= 50
                and refv["win_n"] >= 50 and refv["fail_n"] >= 50
            )
            dev_effect_ok = bool(pd.notna(dev["effect"]) and dev["effect"] >= 0.30)
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

            row = {
                "feature": feature,
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
                "replicated_directional": replicated,
            }
            for bi, (gap, eff) in enumerate(zip(block_gaps, block_effects), start=1):
                row[f"b{bi}_gap"] = gap
                row[f"b{bi}_effect_IQR"] = eff
            feature_rows.append(row)

    features = pd.DataFrame(feature_rows)
    if len(features):
        features = features.sort_values(["replicated_directional", "dev_effect_IQR"], ascending=[False, False], na_position="last")

    trades.to_csv(OUT_TRADES, index=False)
    features.to_csv(OUT_FEATURES, index=False)

    if not full_recon:
        status = "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_RECONCILIATION_FAIL"
    elif bool(features.replicated_directional.any()):
        status = "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_SUPPORTED_FOR_NEXT_TEST"
    else:
        status = "SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_INCONCLUSIVE"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC Parent Pre-Range Anatomy — A45 Result", "",
        "A45 keeps the A20 `R360/15` E0/E40 parent frozen and uses only the 72 completed 5m candles in the 09:00–15:00 UTC reference range.", "",
        f"Raw SOLUSDT 5m coverage: **{100.0*coverage:.4f}%**.",
        f"A20 count reconciliation: **{count_ok}**. H/L/R + 72-bar reference reconciliation: **{ref_ok}**. Enriched rows: **{len(trades)}/{sum(EXPECTED_COUNTS.values())}**.", "",
        "## Frozen parent economics", "",
        "| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for part in PARTS:
        s = summary(parent[parent.partition == part])
        lines.append(f"| {part} | {s['n']} | {pct(s['wr'])} | {fmt(s['pf'],2)} | ${fmt(s['net'],2)} | {pct(s['wr_5bps'])} | {fmt(s['pf_5bps'],2)} | ${fmt(s['net_5bps'],2)} |")

    if bad_rows:
        lines += ["", "## Reconciliation failures", ""]
        for i, reason in bad_rows[:20]:
            lines.append(f"- row {i}: {reason}")

    lines += ["", "## Replicated decision-time separators", "",
              "| Feature | Dev gap | Dev effect | Dev block sign | External gap/effect | RefVal gap/effect |",
              "|---|---:|---:|---:|---:|---:|"]
    replicated = features[features.replicated_directional] if len(features) else pd.DataFrame()
    if len(replicated):
        for _, r in replicated.iterrows():
            lines.append(
                f"| {r.feature} | {fmt(r.dev_gap)} | {fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | "
                f"{fmt(r.external_gap)}/{fmt(r.external_effect_IQR)} | {fmt(r.reference_gap)}/{fmt(r.reference_effect_IQR)} |"
            )
    else:
        lines.append("| none | - | - | - | - | - |")

    if len(features):
        lines += ["", "## Strongest Development effects (diagnostic)", "",
                  "These are not promoted unless `replicated_directional=True`.", "",
                  "| Feature | Dev effect | Dev block sign | External effect/sign | RefVal effect/sign | Replicated |",
                  "|---|---:|---:|---:|---:|---:|"]
        for _, r in features.head(8).iterrows():
            dsign = int(np.sign(r.dev_gap)) if pd.notna(r.dev_gap) else 0
            esign = int(np.sign(r.external_gap)) if pd.notna(r.external_gap) else 0
            rsign = int(np.sign(r.reference_gap)) if pd.notna(r.reference_gap) else 0
            lines.append(
                f"| {r.feature} | {fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | "
                f"{fmt(r.external_effect_IQR)}/{esign:+d} | {fmt(r.reference_effect_IQR)}/{rsign:+d} | {'YES' if bool(r.replicated_directional) else 'NO'} |"
            )

    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if status.endswith("SUPPORTED_FOR_NEXT_TEST"):
        lines += [
            "At least one feature known at 15:00 UTC before resting-order placement separated later stress winners/failers in Development, stayed directionally stable across Development blocks, and replicated with minimum effect in both frozen validation pools.",
            "A separately preregistered next experiment may test one minimal Development-derived guard. A45 itself changes no trade.", "",
        ]
    elif status.endswith("INCONCLUSIVE"):
        lines += [
            "No frozen pre-range feature met the preregistered Development stability + dual-OOS replication rule. Do not invent a 15UTC parent filter from weak or one-pool effects.", "",
        ]
    else:
        lines += ["Reconciliation failed. No anatomy conclusion is valid.", ""]
    lines += ["Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
