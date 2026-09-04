#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A14_PATH = Path(__file__).resolve().parent / "sol_long_e20_conditional_protection_a14.py"
spec = importlib.util.spec_from_file_location("sol_a14", A14_PATH)
a14 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a14)
a11 = a14.a11
a2 = a14.a2

OUT_MD = ROOT / "SOL_LONG_E10_FAIL_TRIGGER_ANATOMY_A15_Result.md"
OUT_ANAT = ROOT / "SOL_LONG_E10_FAIL_TRIGGER_ANATOMY_A15_ANATOMY.csv"
OUT_SUM = ROOT / "SOL_LONG_E10_FAIL_TRIGGER_ANATOMY_A15_SUMMARY.csv"
OUT_SEP = ROOT / "SOL_LONG_E10_FAIL_TRIGGER_ANATOMY_A15_SEPARATION.csv"
OUT_STATUS = ROOT / "SOL_LONG_E10_FAIL_TRIGGER_ANATOMY_A15_Status.txt"

TARGET_R = 0.40
E20_R = 0.20
E25_R = 0.25
E30_R = 0.30
EPS = 1e-12
OUTCOMES = ("TRIGGERED_E40_RECOVERY", "TRIGGERED_TRUE_STALLER")

CONT_FEATURES = [
    "entry_to_e20_min", "break_to_e20_min", "e20_bar_close_R", "e20_bar_close_vs_E20_R",
    "running_mae_R_to_e20", "closes_gt_H_to_e20", "trigger_close_R", "trigger_close_vs_E10_R",
    "trigger_high_R", "trigger_low_R", "trigger_body_R", "trigger_upper_wick_R", "trigger_lower_wick_R",
    "post_e20_peak_R", "giveback_peak_to_trigger_close_R", "running_mfe_R_to_trigger",
]
BIN_FEATURES = ["trigger_traded_E25", "trigger_traded_E30"]
TIME_FEATURES = {"entry_to_e20_min", "break_to_e20_min"}
COUNT_FEATURES = {"closes_gt_H_to_e20"}


def fmt(v, d=3):
    if pd.isna(v): return "-"
    return f"{float(v):.{d}f}"


def fmt_pct(v):
    if pd.isna(v): return "-"
    return f"{100.0*float(v):.1f}%"


def idx_of(idx, ts):
    t = pd.Timestamp(ts)
    i = int(idx.searchsorted(t, "left"))
    return i if i < len(idx) and idx[i] == t else -1


def trade_row(m, *, role, partition, dev_block, execution_start, component,
              entry_ts, exit_ts, exit_reason, H, L, R, break_ts):
    sig = a14.signal_for_trade(m, entry_ts, exit_ts, H, R, "CP_E10_5_FULL")
    if sig is None:
        return None
    idx, op, hi, lo, cl = m["idx"], m["open"], m["high"], m["low"], m["close"]
    ei = idx_of(idx, entry_ts)
    xi = idx_of(idx, exit_ts)
    if ei < 0 or xi < 0:
        return None
    si = int(sig["signal_i"])
    e20_i = int(sig["e20_i"])
    # Match A14 actual-intervention semantics exactly.
    if si + 1 >= xi:
        return None
    bi = idx_of(idx, break_ts) if pd.notna(break_ts) else -1

    pre_lo = np.asarray(lo[ei:e20_i+1], dtype=float)
    pre_cl = np.asarray(cl[ei:e20_i+1], dtype=float)
    through_hi = np.asarray(hi[ei:si+1], dtype=float)
    local_hi = np.asarray(hi[e20_i:si+1], dtype=float)

    o = float(op[si]); h = float(hi[si]); l = float(lo[si]); c = float(cl[si])
    body_hi = max(o, c); body_lo = min(o, c)
    e20_close_R = (float(cl[e20_i]) - H) / R
    peak_local_R = (float(np.max(local_hi)) - H) / R
    close_R = (c - H) / R
    outcome = "TRIGGERED_E40_RECOVERY" if str(exit_reason) == "TARGET" else "TRIGGERED_TRUE_STALLER"

    return {
        "role": role, "partition": partition, "dev_block": dev_block, "execution_start": execution_start,
        "component": component, "outcome": outcome,
        "entry_ts": pd.Timestamp(entry_ts), "e20_ts": idx[e20_i], "trigger_ts": idx[si],
        "baseline_exit_ts": pd.Timestamp(exit_ts), "baseline_exit_reason": str(exit_reason),
        "H": H, "L": L, "R": R,
        "entry_to_e20_min": float((idx[e20_i] - pd.Timestamp(entry_ts)) / pd.Timedelta(minutes=1)),
        "break_to_e20_min": float((idx[e20_i] - idx[bi]) / pd.Timedelta(minutes=1)) if bi >= 0 and bi <= e20_i else np.nan,
        "e20_bar_close_R": e20_close_R,
        "e20_bar_close_vs_E20_R": e20_close_R - E20_R,
        "running_mae_R_to_e20": max(0.0, (H - float(np.min(pre_lo))) / R) if len(pre_lo) else np.nan,
        "closes_gt_H_to_e20": int(np.sum(pre_cl > H)),
        "trigger_close_R": close_R,
        "trigger_close_vs_E10_R": close_R - a14.E10_R,
        "trigger_high_R": (h - H) / R,
        "trigger_low_R": (l - H) / R,
        "trigger_body_R": abs(c - o) / R,
        "trigger_upper_wick_R": max(0.0, (h - body_hi) / R),
        "trigger_lower_wick_R": max(0.0, (body_lo - l) / R),
        "trigger_traded_E25": h >= H + E25_R * R - EPS,
        "trigger_traded_E30": h >= H + E30_R * R - EPS,
        "post_e20_peak_R": peak_local_R,
        "giveback_peak_to_trigger_close_R": peak_local_R - close_R,
        "running_mfe_R_to_trigger": max(0.0, (float(np.max(through_hi)) - H) / R) if len(through_hi) else np.nan,
    }


def build_anatomy(parent, h2, m):
    rows = []
    for _, r in parent.iterrows():
        z = trade_row(
            m, role=r.role, partition=r.partition, dev_block=r.dev_block, execution_start=r.execution_start,
            component="PARENT", entry_ts=r.entry_ts, exit_ts=r.exit_ts, exit_reason=r.exit_reason,
            H=float(r.H), L=float(r.L), R=float(r.R), break_ts=r.h1_break_ts,
        )
        if z is not None: rows.append(z)
    for _, r in h2.iterrows():
        z = trade_row(
            m, role=r.role, partition=r.partition, dev_block=r.dev_block, execution_start=r.execution_start,
            component="REC_H2", entry_ts=r.recovery_entry_ts, exit_ts=r.recovery_exit_ts,
            exit_reason=r.recovery_exit_reason, H=float(r.H), L=float(r.L), R=float(r.R),
            break_ts=r.recovery_break_ts,
        )
        if z is not None: rows.append(z)
    return pd.DataFrame(rows)


def pooled(a):
    if a.empty: return a.copy()
    p = a.copy(); p["component"] = "POOLED"
    return pd.concat([a, p], ignore_index=True)


def summary_table(a):
    rows = []
    for (role, part, comp, outcome), q in a.groupby(["role", "partition", "component", "outcome"], sort=False):
        row = {"role": role, "partition": part, "component": comp, "outcome": outcome, "n": len(q)}
        for f in CONT_FEATURES:
            x = pd.to_numeric(q[f], errors="coerce").dropna()
            row[f+"_q25"] = float(x.quantile(.25)) if len(x) else np.nan
            row[f+"_q50"] = float(x.quantile(.50)) if len(x) else np.nan
            row[f+"_q75"] = float(x.quantile(.75)) if len(x) else np.nan
        for f in BIN_FEATURES:
            row[f+"_rate"] = float(q[f].astype(bool).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def material(feature, gap):
    if pd.isna(gap): return False
    if feature in TIME_FEATURES: return abs(gap) >= 5.0
    if feature in COUNT_FEATURES: return abs(gap) >= 1.0
    if feature in BIN_FEATURES: return abs(gap) >= 0.15
    return abs(gap) >= 0.03


def separation(a):
    rows = []
    p = a[a.component == "POOLED"].copy()
    for (role, part), q in p.groupby(["role", "partition"], sort=False):
        rec = q[q.outcome == "TRIGGERED_E40_RECOVERY"]
        sta = q[q.outcome == "TRIGGERED_TRUE_STALLER"]
        if len(rec) == 0 or len(sta) == 0: continue
        for f in CONT_FEATURES:
            rv = float(pd.to_numeric(rec[f], errors="coerce").median())
            sv = float(pd.to_numeric(sta[f], errors="coerce").median())
            gap = rv - sv
            rows.append({"role": role, "partition": part, "feature": f, "recovery_n": len(rec), "staller_n": len(sta),
                         "recovery_value": rv, "staller_value": sv, "gap": gap, "material": material(f, gap)})
        for f in BIN_FEATURES:
            rv = float(rec[f].astype(bool).mean()); sv = float(sta[f].astype(bool).mean()); gap = rv - sv
            rows.append({"role": role, "partition": part, "feature": f, "recovery_n": len(rec), "staller_n": len(sta),
                         "recovery_value": rv, "staller_value": sv, "gap": gap, "material": material(f, gap)})
    return pd.DataFrame(rows)


def decision(sep):
    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].copy()
    ext = sep[(sep.role == "CENTRAL") & (sep.partition == "external")].copy()
    ref = sep[(sep.role == "CENTRAL") & (sep.partition == "reference_validation")].copy()
    if dev.empty:
        return False, "Central Development trigger cohort missing", pd.DataFrame()
    dn_r = int(dev.recovery_n.iloc[0]); dn_s = int(dev.staller_n.iloc[0])
    if dn_r < 5 or dn_s < 30:
        return False, f"Central Development trigger cohort below gate: recovery={dn_r}, staller={dn_s}", pd.DataFrame()
    z = dev[["feature","recovery_n","staller_n","gap","material"]].rename(columns={"gap":"dev_gap"})
    z = z.merge(ext[["feature","recovery_n","staller_n","gap"]].rename(columns={"recovery_n":"ext_recovery_n","staller_n":"ext_staller_n","gap":"ext_gap"}), on="feature", how="left")
    z = z.merge(ref[["feature","recovery_n","staller_n","gap"]].rename(columns={"recovery_n":"ref_recovery_n","staller_n":"ref_staller_n","gap":"ref_gap"}), on="feature", how="left")
    supp = sep[sep.role.isin(["CLOCK_SUPPORT","REF_SUPPORT"])].copy()
    same_counts=[]; reversed_counts=[]
    for _, r in z.iterrows():
        s = supp[supp.feature == r.feature]
        same = int(((s.gap * r.dev_gap) > 0).sum())
        rev = int(((s.gap * r.dev_gap) < 0).sum())
        same_counts.append(same); reversed_counts.append(rev)
    z["support_same"] = same_counts; z["support_reversed"] = reversed_counts
    z["replicated"] = (
        z.material.astype(bool)
        & z.ext_gap.notna() & z.ref_gap.notna()
        & (z.ext_recovery_n >= 3) & (z.ext_staller_n >= 10)
        & (z.ref_recovery_n >= 3) & (z.ref_staller_n >= 10)
        & ((z.dev_gap * z.ext_gap) > 0) & ((z.dev_gap * z.ref_gap) > 0)
        & (z.support_same >= 3)
    )
    good = z[z.replicated].copy()
    if good.empty:
        return False, "No material trigger-time feature replicated through both central OOS cells and >=3/4 supports", z
    return True, f"{len(good)} trigger-time features replicate for an A16 guard", z


def main():
    parent, h2, m, coverage = a11.load_system()
    a = build_anatomy(parent, h2, m)
    ap = pooled(a)
    summ = summary_table(ap)
    sep = separation(ap)
    supported, reason, repl = decision(sep)

    a.to_csv(OUT_ANAT, index=False)
    summ.to_csv(OUT_SUM, index=False)
    sep.to_csv(OUT_SEP, index=False)

    lines = [
        "# SOL LONG E10-Fail Trigger Anatomy — A15 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A15 is forensic only. It studies actual A14 CP_E10_5_FULL intervention triggers; no trade rule is changed.", "",
        "## Trigger cohorts", "",
        "| Role | Partition | Component | Outcome | N | Entry→E20 | E20 close | Trigger close | Trigger low | Peak→close giveback | MFE to trigger |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    q = summ[summ.component.isin(["POOLED","PARENT","REC_H2"])].copy()
    for _, r in q.iterrows():
        lines.append(f"| {r.role} | {r.partition} | {r.component} | {r.outcome} | {int(r.n)} | {fmt(r.entry_to_e20_min_q50,0)}m | {fmt(r.e20_bar_close_R_q50)}R | {fmt(r.trigger_close_R_q50)}R | {fmt(r.trigger_low_R_q50)}R | {fmt(r.giveback_peak_to_trigger_close_R_q50)}R | {fmt(r.running_mfe_R_to_trigger_q50)}R |")

    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].copy()
    if len(dev):
        dev["abs_gap"] = dev.gap.abs()
        lines += ["", "## Central Development trigger-time separations", "",
                  "| Feature | Recovery N | Staller N | Recovery | Staller | Gap | Material |",
                  "|---|---:|---:|---:|---:|---:|---|"]
        for _, r in dev.sort_values("abs_gap", ascending=False).iterrows():
            lines.append(f"| {r.feature} | {int(r.recovery_n)} | {int(r.staller_n)} | {fmt(r.recovery_value)} | {fmt(r.staller_value)} | {fmt(r.gap)} | {'YES' if r.material else 'NO'} |")

    if len(repl):
        good = repl[repl.replicated].copy()
        lines += ["", "## Replicated A16 guard dimensions", ""]
        if good.empty:
            lines.append("None.")
        else:
            lines += ["| Feature | Dev gap | External gap | RefVal gap | Support same/reversed |",
                      "|---|---:|---:|---:|---:|"]
            for _, r in good.iterrows():
                lines.append(f"| {r.feature} | {fmt(r.dev_gap)} | {fmt(r.ext_gap)} | {fmt(r.ref_gap)} | {int(r.support_same)}/{int(r.support_reversed)} |")

    status = "SOL_LONG_E10_FAIL_TRIGGER_A15_SUPPORTED_FOR_A16" if supported else "SOL_LONG_E10_FAIL_TRIGGER_A15_INCONCLUSIVE"
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "",
              "If supported, A16 may test only a tiny false-positive guard derived from rounded Central Development quantiles/state values. OOS cannot choose the guard.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n", encoding="utf-8")
    OUT_STATUS.write_text(status+"\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
