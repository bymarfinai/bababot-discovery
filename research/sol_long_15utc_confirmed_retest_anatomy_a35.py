#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A34_PATH = Path(__file__).resolve().parent / "sol_long_15utc_rc30c2_delayed_confirm_a34.py"
spec = importlib.util.spec_from_file_location("a34", A34_PATH)
a34 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a34)
a26 = a34.a26; a2 = a34.a2

OUT_MD = ROOT / "SOL_LONG_15UTC_CONFIRMED_RETEST_ANATOMY_A35_Result.md"
OUT_COHORT = ROOT / "SOL_LONG_15UTC_CONFIRMED_RETEST_ANATOMY_A35_COHORT.csv"
OUT_SUM = ROOT / "SOL_LONG_15UTC_CONFIRMED_RETEST_ANATOMY_A35_SUMMARY.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_CONFIRMED_RETEST_ANATOMY_A35_Status.txt"
CELLS = a34.CELLS
TARGET_R = 0.40


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def one(m, r):
    z = a34.rc30c2_signal(m, r)
    if z is None: return None
    signal, endpos = z
    ci = a34.confirmation_index(m, r, "DC10_C12", signal, endpos)
    if ci < 0: return None

    idx = m["idx"]; hi = m["high"]; lo = m["low"]; cl = m["close"]
    H = float(r.H); R = float(r.R)
    e05 = H + 0.05 * R; e10 = H + 0.10 * R; e40 = H + TARGET_R * R

    e40_i = -1; fail_i = -1; e10_i = -1; e05_i = -1; h_i = -1
    # Start after the completed confirmation bar. This keeps the future anatomy causal.
    for i in range(ci + 1, endpos):
        if e10_i < 0 and float(lo[i]) <= e10: e10_i = i
        if e05_i < 0 and float(lo[i]) <= e05: e05_i = i
        if h_i < 0 and float(lo[i]) <= H: h_i = i
        if float(hi[i]) >= e40:
            e40_i = i
            break
        if float(cl[i]) <= H:
            fail_i = i
            break

    terminal_i = e40_i if e40_i >= 0 else (fail_i if fail_i >= 0 else endpos - 1)
    seg_lo = np.asarray(lo[ci + 1:terminal_i + 1], float)
    seg_cl = np.asarray(cl[ci + 1:terminal_i + 1], float)
    seg_hi = np.asarray(hi[ci + 1:terminal_i + 1], float)

    # Strictly-before avoids same-bar intrabar-order ambiguity.
    e10_before_e40 = bool(e10_i >= 0 and (e40_i < 0 or e10_i < e40_i))
    e05_before_e40 = bool(e05_i >= 0 and (e40_i < 0 or e05_i < e40_i))
    h_before_e40 = bool(h_i >= 0 and (e40_i < 0 or h_i < e40_i))

    e10_to_e40 = bool(e10_i >= 0 and e40_i >= 0 and e10_i < e40_i and (fail_i < 0 or e40_i < fail_i))
    e05_to_e40 = bool(e05_i >= 0 and e40_i >= 0 and e05_i < e40_i and (fail_i < 0 or e40_i < fail_i))

    return {
        "role": r.role, "partition": r.partition, "dev_block": r.dev_block,
        "execution_start": r.execution_start, "entry_ts": r.entry_ts, "exit_ts": r.exit_ts,
        "H": H, "L": float(r.L), "R": R,
        "signal_ts": idx[signal], "confirm_ts": idx[ci],
        "confirm_close_R": (float(cl[ci]) - H) / R,
        "eventual_E40": e40_i >= 0,
        "terminal": "E40" if e40_i >= 0 else ("H_FAIL" if fail_i >= 0 else "TIME"),
        "terminal_ts": idx[terminal_i],
        "e10_retest": e10_i >= 0, "e10_retest_before_E40": e10_before_e40,
        "e10_retest_ts": idx[e10_i] if e10_i >= 0 else pd.NaT,
        "e10_retest_min": float((idx[e10_i] - idx[ci]) / pd.Timedelta(minutes=1)) if e10_i >= 0 else np.nan,
        "e10_retest_to_E40": e10_to_e40,
        "e05_retest": e05_i >= 0, "e05_retest_before_E40": e05_before_e40,
        "e05_retest_ts": idx[e05_i] if e05_i >= 0 else pd.NaT,
        "e05_retest_min": float((idx[e05_i] - idx[ci]) / pd.Timedelta(minutes=1)) if e05_i >= 0 else np.nan,
        "e05_retest_to_E40": e05_to_e40,
        "H_touch": h_i >= 0, "H_touch_before_E40": h_before_e40,
        "min_low_R": ((float(seg_lo.min()) - H) / R) if len(seg_lo) else np.nan,
        "min_close_R": ((float(seg_cl.min()) - H) / R) if len(seg_cl) else np.nan,
        "max_high_R": ((float(seg_hi.max()) - H) / R) if len(seg_hi) else np.nan,
    }


def build(m):
    rows = []
    for role, ref, hour in CELLS:
        for part in ("development", "external", "reference_validation"):
            p = a26.parent_cell(m, part, role, ref, hour)
            for _, r in p[p.pnl <= 0].iterrows():
                z = one(m, r)
                if z is not None:
                    z["ref_min"] = ref; z["hour"] = hour; rows.append(z)
    return pd.DataFrame(rows)


def summarize(t):
    rows = []
    for (role, part), q in t.groupby(["role", "partition"], sort=False):
        winners = q[q.eventual_E40.astype(bool)]
        e10 = q[q.e10_retest_before_E40.astype(bool)]
        e05 = q[q.e05_retest_before_E40.astype(bool)]
        rows.append({
            "role": role, "partition": part, "n": len(q),
            "eventual_E40_n": len(winners), "eventual_E40_rate": float(q.eventual_E40.mean()),
            "winner_e10_retest_rate": float(winners.e10_retest_before_E40.mean()) if len(winners) else np.nan,
            "winner_e05_retest_rate": float(winners.e05_retest_before_E40.mean()) if len(winners) else np.nan,
            "all_e10_retest_rate": float(q.e10_retest_before_E40.mean()),
            "all_e05_retest_rate": float(q.e05_retest_before_E40.mean()),
            "e10_retest_to_E40_rate": float(e10.e10_retest_to_E40.mean()) if len(e10) else np.nan,
            "e05_retest_to_E40_rate": float(e05.e05_retest_to_E40.mean()) if len(e05) else np.nan,
            "median_e10_retest_min": float(e10.e10_retest_min.median()) if len(e10) else np.nan,
            "median_e05_retest_min": float(e05.e05_retest_min.median()) if len(e05) else np.nan,
            "median_min_low_R_E40": float(winners.min_low_R.median()) if len(winners) else np.nan,
            "median_min_low_R_nonE40": float(q.loc[~q.eventual_E40.astype(bool), "min_low_R"].median()) if (~q.eventual_E40.astype(bool)).any() else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    x, coverage = a2.a1.load5(); m = a2.make_market_with_open(x)
    cohort = build(m); summary = summarize(cohort)
    cohort.to_csv(OUT_COHORT, index=False); summary.to_csv(OUT_SUM, index=False)

    cd = summary[(summary.role == "CENTRAL") & (summary.partition == "development")]
    ce = summary[(summary.role == "CENTRAL") & (summary.partition == "external")]
    cr = summary[(summary.role == "CENTRAL") & (summary.partition == "reference_validation")]
    support = summary[(summary.role != "CENTRAL") & summary.partition.isin(["external", "reference_validation"])]

    supported = False
    reason = "Required Central cohorts missing"
    if len(cd) == len(ce) == len(cr) == 1:
        d = cd.iloc[0]; e = ce.iloc[0]; r = cr.iloc[0]
        support_nonzero = int((pd.to_numeric(support.winner_e10_retest_rate, errors="coerce") > 0).sum())
        supported = bool(
            int(d.n) >= 25 and int(d.eventual_E40_n) >= 10
            and float(d.winner_e10_retest_rate) >= 0.40
            and pd.notna(d.e10_retest_to_E40_rate) and float(d.e10_retest_to_E40_rate) >= 0.35
            and pd.notna(e.winner_e10_retest_rate) and float(e.winner_e10_retest_rate) > 0
            and pd.notna(r.winner_e10_retest_rate) and float(r.winner_e10_retest_rate) > 0
            and support_nonzero >= 3
        )
        reason = f"Dev winner E10 retest={pct(d.winner_e10_retest_rate)}, E10->E40={pct(d.e10_retest_to_E40_rate)}; Central OOS winner E10 retest={pct(e.winner_e10_retest_rate)}/{pct(r.winner_e10_retest_rate)}; support nonzero={support_nonzero}/4"

    status = "SOL_LONG_15UTC_CONFIRMED_RETEST_A35_SUPPORTED_FOR_A36" if supported else "SOL_LONG_15UTC_CONFIRMED_RETEST_A35_INCONCLUSIVE"
    lines = ["# SOL LONG 15:00 UTC Confirmed-Recovery Retest Anatomy — A35 Result", "", f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
             "A35 is forensic only. It studies the exact A34 DC10_C12 confirmation cohort and asks whether confirmed E40 continuations offer a cheaper E10/E05 retest before target.", "", "## Summary", "",
             "| Role | Partition | N | E40 rate | Winner→E10 retest | Winner→E05 retest | All E10 retest | E10 retest→E40 | Median E10 retest | E40 median min-low | Non-E40 median min-low |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, z in summary.iterrows():
        lines.append(f"| {z.role} | {z.partition} | {int(z.n)} | {pct(z.eventual_E40_rate)} | {pct(z.winner_e10_retest_rate)} | {pct(z.winner_e05_retest_rate)} | {pct(z.all_e10_retest_rate)} | {pct(z.e10_retest_to_E40_rate)} | {fmt(z.median_e10_retest_min,0)}m | {fmt(z.median_min_low_R_E40,3)}R | {fmt(z.median_min_low_R_nonE40,3)}R |")
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "",
              "If supported, A36 may test one fixed confirmation-then-E10 resting retest entry. E05 remains diagnostic unless separately authorized by A35 evidence.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8"); OUT_STATUS.write_text(status + "\n", encoding="utf-8"); print(status)

if __name__ == "__main__": main()
