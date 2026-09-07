#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_STATES = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_STATES.csv"
OUT_METRICS = ROOT / "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_METRICS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_BLOCKS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_Status.txt"

PARTS = ("development", "external", "reference_validation")
FAIL = "FAILED_BREAK"
TARGET = "RECOVER_E40"
TIME = "UNRESOLVED_TIME"
K = 3
FEATURE = "latest_range_R"
EXPECTED = {
    "development": {FAIL: 233, TARGET: 63, TIME: 4},
    "external": {FAIL: 133, TARGET: 54, TIME: 5},
    "reference_validation": {FAIL: 134, TARGET: 48, TIME: 2},
}
REF_DEV_FAIL_MED = 0.07096
REF_DEV_TARGET_MED = 0.08531
REF_TOL = 0.002
EPS = 1e-12


def pct(x):
    return "-" if pd.isna(x) else f"{100.0 * float(x):.1f}%"


def ratio(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    if b <= EPS:
        return np.inf if a > EPS else np.nan
    return float(a / b)


def fmt_ratio(x):
    if pd.isna(x): return "-"
    if np.isinf(x): return "inf"
    return f"{float(x):.2f}x"


def one_partition(q: pd.DataFrame, threshold: float) -> dict:
    f = q[q.terminal_label == FAIL].copy()
    t = q[q.terminal_label == TARGET].copy()
    u = q[q.terminal_label == TIME].copy()
    fh = float((f[FEATURE] <= threshold).mean()) if len(f) else np.nan
    th = float((t[FEATURE] <= threshold).mean()) if len(t) else np.nan
    uh = float((u[FEATURE] <= threshold).mean()) if len(u) else np.nan
    return {
        "n": len(q),
        "fail_n": len(f),
        "target_n": len(t),
        "time_n": len(u),
        "fail_median": float(f[FEATURE].median()) if len(f) else np.nan,
        "target_median": float(t[FEATURE].median()) if len(t) else np.nan,
        "fail_hit": fh,
        "target_hit": th,
        "gap": fh - th if pd.notna(fh) and pd.notna(th) else np.nan,
        "ratio": ratio(fh, th),
        "compressed_n": int((q[FEATURE] <= threshold).sum()),
        "compressed_rate": float((q[FEATURE] <= threshold).mean()) if len(q) else np.nan,
        "time_hit": uh,
    }


def main():
    errors = []
    if not IN_STATES.exists():
        raise FileNotFoundError(IN_STATES)

    s = pd.read_csv(IN_STATES)
    required = {"partition", "dev_block", "entry_ts", "warning_ts", "terminal_label", "minute_k", FEATURE}
    missing = sorted(required - set(s.columns))
    if missing:
        errors.append(f"missing columns {missing}")

    if not errors:
        s[FEATURE] = pd.to_numeric(s[FEATURE], errors="coerce")
        s["minute_k"] = pd.to_numeric(s.minute_k, errors="coerce")
        q = s[s.minute_k == K].copy()
        if len(q) != 676:
            errors.append(f"K3 row count {len(q)} != 676")
        if q[FEATURE].isna().any():
            errors.append(f"K3 missing {FEATURE}: {int(q[FEATURE].isna().sum())}")
        dup = q.duplicated(["partition", "entry_ts", "warning_ts"], keep=False)
        if dup.any():
            errors.append(f"duplicate K3 events: {int(dup.sum())}")

        for p in PARTS:
            z = q[q.partition == p]
            for lab, n_exp in EXPECTED[p].items():
                n = int((z.terminal_label == lab).sum())
                if n != n_exp:
                    errors.append(f"{p} {lab} {n} != {n_exp}")

        # Threshold derivation is deliberately isolated to Development K3 only.
        d = q[q.partition == "development"].copy()
        df = d[d.terminal_label == FAIL][FEATURE]
        dt = d[d.terminal_label == TARGET][FEATURE]
        if len(df) < 200 or len(dt) < 50:
            errors.append(f"Development support fail/target={len(df)}/{len(dt)}")
        dev_fail_med = float(df.median()) if len(df) else np.nan
        dev_target_med = float(dt.median()) if len(dt) else np.nan
        threshold = (dev_fail_med + dev_target_med) / 2.0

        if not np.isfinite(dev_fail_med) or not np.isfinite(dev_target_med):
            errors.append("nonfinite Development medians")
        elif not (dev_fail_med < dev_target_med):
            errors.append(f"Development median direction invalid {dev_fail_med} >= {dev_target_med}")
        if np.isfinite(dev_fail_med) and abs(dev_fail_med - REF_DEV_FAIL_MED) > REF_TOL:
            errors.append(f"Development fail median drift {dev_fail_med:.8f}")
        if np.isfinite(dev_target_med) and abs(dev_target_med - REF_DEV_TARGET_MED) > REF_TOL:
            errors.append(f"Development target median drift {dev_target_med:.8f}")
        if not np.isfinite(threshold) or threshold <= 0:
            errors.append(f"invalid threshold {threshold}")
        elif not (dev_fail_med < threshold < dev_target_med):
            errors.append(f"threshold not strictly between medians {threshold}")
    else:
        q = pd.DataFrame()
        dev_fail_med = dev_target_med = threshold = np.nan

    if errors:
        status = "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_RECONCILIATION_FAIL"
        OUT_STATUS.write_text(status + "\n" + "\n".join(errors) + "\n", encoding="utf-8")
        OUT_MD.write_text(
            "# SOL LONG 15:00 UTC W10 1m Range Compression — A60 Result\n\n"
            f"**Status: {status}**\n\n" + "\n".join(f"- {e}" for e in errors) +
            "\n\nResearch only. Live Baba Bot remains unchanged.\n",
            encoding="utf-8",
        )
        raise RuntimeError("; ".join(errors))

    # Only after the Development-derived threshold is frozen do we score every partition.
    rows = []
    for p in PARTS:
        z = q[q.partition == p].copy()
        m = one_partition(z, threshold)
        m.update({"partition": p, "minute_k": K, "feature": FEATURE, "threshold": threshold})
        rows.append(m)
    metrics = pd.DataFrame(rows)

    # Frozen Development block diagnostics using the one full-Development threshold.
    blocks = []
    d = q[q.partition == "development"].copy()
    for b in sorted(pd.to_numeric(d.dev_block, errors="coerce").dropna().unique()):
        z = d[pd.to_numeric(d.dev_block, errors="coerce") == b].copy()
        m = one_partition(z, threshold)
        eligible = bool(m["fail_n"] >= 10 and m["target_n"] >= 3)
        bad_direction = bool(eligible and m["fail_hit"] > m["target_hit"])
        blocks.append({
            "dev_block": int(b), "threshold": threshold, "eligible": eligible,
            "bad_direction": bad_direction, **m,
        })
    block_df = pd.DataFrame(blocks)

    dev = metrics[metrics.partition == "development"].iloc[0]
    eligible_blocks = block_df[block_df.eligible.astype(bool)]
    good_blocks = int(eligible_blocks.bad_direction.astype(bool).sum())
    eligible_block_n = len(eligible_blocks)

    dev_checks = {
        "fail_gt_target": bool(dev.fail_hit > dev.target_hit),
        "gap_ge_10pp": bool(dev.gap >= 0.10 - EPS),
        "ratio_ge_1p25": bool(dev.ratio >= 1.25 - EPS),
        "fail_hit_ge_45pct": bool(dev.fail_hit >= 0.45 - EPS),
        "blocks_ge_4of6": bool(good_blocks >= 4 and eligible_block_n >= 4),
    }
    dev_pass = all(dev_checks.values())

    oos_checks = {}
    oos_pass = {}
    for p in ("external", "reference_validation"):
        r = metrics[metrics.partition == p].iloc[0]
        checks = {
            "support": bool(r.fail_n >= 100 and r.target_n >= 35),
            "fail_gt_target": bool(r.fail_hit > r.target_hit),
            "gap_ge_5pp": bool(r.gap >= 0.05 - EPS),
            "ratio_ge_1p15": bool(r.ratio >= 1.15 - EPS),
            "fail_hit_ge_40pct": bool(r.fail_hit >= 0.40 - EPS),
        }
        oos_checks[p] = checks
        oos_pass[p] = all(checks.values())

    if not dev_pass:
        status = "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_INCONCLUSIVE"
    elif all(oos_pass.values()):
        status = "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_SUPPORTED_FOR_LIVE_REVALIDATION"
    else:
        status = "SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_DEVELOPMENT_ONLY"

    metrics["development_gate"] = dev_pass
    metrics["partition_oos_gate"] = metrics.partition.map(lambda p: np.nan if p == "development" else oos_pass[p])
    metrics.to_csv(OUT_METRICS, index=False)
    block_df.to_csv(OUT_BLOCKS, index=False)
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15:00 UTC W10 1m Range Compression Revalidation — A60 Result",
        "",
        "A60 tests one locked continuous candidate from A58: K3 latest completed 1m range normalized by R. The threshold is derived from Development only and then frozen before scoring External or Reference Validation.",
        "",
        "## Frozen threshold derivation",
        "",
        f"- Development FAILED_BREAK median: **{dev_fail_med:.6f}R**",
        f"- Development RECOVER_E40 median: **{dev_target_med:.6f}R**",
        f"- Frozen midpoint threshold T: **{threshold:.6f}R**",
        f"- Compression rule: `latest_range_R <= {threshold:.9f}` at **K3 only**.",
        "",
        "## Partition discrimination",
        "",
        "| Partition | Fail N | Target N | Time N | Fail hit | Target hit | Gap | Ratio | Compressed | Time hit | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in metrics.iterrows():
        if r.partition == "development":
            gate = "PASS" if dev_pass else "fail"
        else:
            gate = "PASS" if oos_pass[r.partition] else "fail"
        lines.append(
            f"| {r.partition} | {int(r.fail_n)} | {int(r.target_n)} | {int(r.time_n)} | "
            f"{pct(r.fail_hit)} | {pct(r.target_hit)} | {100*r.gap:.1f}pp | {fmt_ratio(r.ratio)} | "
            f"{int(r.compressed_n)} ({pct(r.compressed_rate)}) | {pct(r.time_hit)} | {gate} |"
        )

    lines += [
        "",
        "## Development six-block direction",
        "",
        "| Block | Fail N | Target N | Fail hit | Target hit | Gap | Ratio | Eligible | Bad direction |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in block_df.iterrows():
        lines.append(
            f"| {int(r.dev_block)} | {int(r.fail_n)} | {int(r.target_n)} | {pct(r.fail_hit)} | "
            f"{pct(r.target_hit)} | {100*r.gap:.1f}pp | {fmt_ratio(r.ratio)} | "
            f"{bool(r.eligible)} | {bool(r.bad_direction)} |"
        )

    lines += [
        "",
        f"Bad direction in eligible Development blocks: **{good_blocks}/{eligible_block_n}**.",
        "",
        "## Frozen gate details",
        "",
        "Development: " + ", ".join(f"{k}={'PASS' if v else 'fail'}" for k, v in dev_checks.items()),
        "",
        "External: " + ", ".join(f"{k}={'PASS' if v else 'fail'}" for k, v in oos_checks["external"].items()),
        "",
        "Reference Validation: " + ", ".join(f"{k}={'PASS' if v else 'fail'}" for k, v in oos_checks["reference_validation"].items()),
        "",
        "## Decision",
        "",
        f"**Status: {status}**",
        "",
        "A60 remains conditional on the completed first-W10 cohort and is therefore anatomy/revalidation only. A supported result authorizes only a later replay across all live-causal post-breakout opportunities; it does not authorize an exit or position-management rule.",
        "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
