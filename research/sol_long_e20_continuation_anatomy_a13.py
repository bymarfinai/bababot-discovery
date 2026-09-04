#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A11_PATH = Path(__file__).resolve().parent / "sol_long_progressive_risk_floor_a11.py"
spec = importlib.util.spec_from_file_location("sol_a11", A11_PATH)
a11 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a11)
a4 = a11.a4
a2 = a11.a2

OUT_MD = ROOT / "SOL_LONG_E20_CONTINUATION_ANATOMY_A13_Result.md"
OUT_COHORT = ROOT / "SOL_LONG_E20_CONTINUATION_ANATOMY_A13_COHORT.csv"
OUT_SNAP = ROOT / "SOL_LONG_E20_CONTINUATION_ANATOMY_A13_SNAPSHOTS.csv"
OUT_SEP = ROOT / "SOL_LONG_E20_CONTINUATION_ANATOMY_A13_SEPARATION.csv"
OUT_STATUS = ROOT / "SOL_LONG_E20_CONTINUATION_ANATOMY_A13_Status.txt"

SNAP_MINS = (5, 10, 15, 30, 60)
E10_R = 0.10
E20_R = 0.20
E25_R = 0.25
E30_R = 0.30
TARGET_R = 0.40
EPS = 1e-12
CONT = "E20_TO_E40_CONTINUATION"
STALL = "E20_STALLER"


def fmt_num(v, d=3):
    if pd.isna(v):
        return "-"
    return f"{float(v):.{d}f}"


def fmt_pct(v):
    if pd.isna(v):
        return "-"
    return f"{100.0 * float(v):.1f}%"


def idx_of(idx, ts):
    t = pd.Timestamp(ts)
    i = int(idx.searchsorted(t, "left"))
    if i >= len(idx) or idx[i] != t:
        return -1
    return i


def trade_records(parent, h2):
    rows = []
    for _, r in parent.iterrows():
        rows.append({
            "role": r.role,
            "partition": r.partition,
            "dev_block": r.dev_block,
            "execution_start": pd.Timestamp(r.execution_start),
            "component": "PARENT",
            "parent_entry_ts": pd.Timestamp(r.entry_ts),
            "entry_ts": pd.Timestamp(r.entry_ts),
            "entry_price": float(r.entry_price),
            "break_ts": pd.Timestamp(r.h1_break_ts) if pd.notna(r.h1_break_ts) else pd.NaT,
            "exit_ts": pd.Timestamp(r.exit_ts),
            "exit_reason": str(r.exit_reason),
            "baseline_pnl": float(r.pnl),
            "baseline_pnl_5bps": float(r.pnl_5bps),
            "H": float(r.H),
            "L": float(r.L),
            "R": float(r.R),
        })
    for _, r in h2.iterrows():
        rows.append({
            "role": r.role,
            "partition": r.partition,
            "dev_block": r.dev_block,
            "execution_start": pd.Timestamp(r.execution_start),
            "component": "REC_H2",
            "parent_entry_ts": pd.Timestamp(r.parent_entry_ts),
            "entry_ts": pd.Timestamp(r.recovery_entry_ts),
            "entry_price": float(r.recovery_entry_price),
            "break_ts": pd.Timestamp(r.recovery_break_ts) if pd.notna(r.recovery_break_ts) else pd.NaT,
            "exit_ts": pd.Timestamp(r.recovery_exit_ts),
            "exit_reason": str(r.recovery_exit_reason),
            "baseline_pnl": float(r.recovery_pnl),
            "baseline_pnl_5bps": float(r.recovery_pnl_5bps),
            "H": float(r.H),
            "L": float(r.L),
            "R": float(r.R),
        })
    return pd.DataFrame(rows)


def consecutive_true_ending(x):
    n = 0
    for v in x[::-1]:
        if bool(v):
            n += 1
        else:
            break
    return n


def build_anatomy(parent, h2, m):
    idx, hi, lo, cl = m["idx"], m["high"], m["low"], m["close"]
    trades = trade_records(parent, h2)
    cohort_rows = []
    snap_rows = []

    for _, t in trades.iterrows():
        ei = idx_of(idx, t.entry_ts)
        xi = idx_of(idx, t.exit_ts)
        if ei < 0 or xi < 0 or xi < ei:
            continue
        H, R = float(t.H), float(t.R)
        e10 = H + E10_R * R
        e20 = H + E20_R * R
        e25 = H + E25_R * R
        e30 = H + E30_R * R

        # Frozen trade is active through the bar carrying a frozen target exit.
        e20_i = -1
        for i in range(ei, xi + 1):
            if float(hi[i]) >= e20 - EPS:
                e20_i = i
                break
        if e20_i < 0:
            continue

        outcome = CONT if str(t.exit_reason) == "TARGET" else STALL
        break_i = idx_of(idx, t.break_ts) if pd.notna(t.break_ts) else -1
        pre_cl = np.asarray(cl[ei:e20_i + 1], dtype=float)
        pre_hi = np.asarray(hi[ei:e20_i + 1], dtype=float)
        pre_lo = np.asarray(lo[ei:e20_i + 1], dtype=float)
        e20_close_R = (float(cl[e20_i]) - H) / R
        entry_to_e20 = float((idx[e20_i] - idx[ei]) / pd.Timedelta(minutes=1))
        break_to_e20 = float((idx[e20_i] - idx[break_i]) / pd.Timedelta(minutes=1)) if break_i >= 0 and break_i <= e20_i else np.nan
        cohort_rows.append({
            "role": t.role,
            "partition": t.partition,
            "dev_block": t.dev_block,
            "execution_start": t.execution_start,
            "component": t.component,
            "parent_entry_ts": t.parent_entry_ts,
            "entry_ts": t.entry_ts,
            "exit_ts": t.exit_ts,
            "exit_reason": t.exit_reason,
            "baseline_pnl": t.baseline_pnl,
            "baseline_pnl_5bps": t.baseline_pnl_5bps,
            "outcome": outcome,
            "H": H,
            "L": float(t.L),
            "R": R,
            "e20_ts": idx[e20_i],
            "entry_to_e20_min": entry_to_e20,
            "break_to_e20_min": break_to_e20,
            "e20_bar_close_R": e20_close_R,
            "e20_bar_close_vs_E20_R": e20_close_R - E20_R,
            "running_mfe_R_at_E20": max(0.0, (float(np.max(pre_hi)) - H) / R),
            "running_mae_R_to_E20": max(0.0, (H - float(np.min(pre_lo))) / R),
            "closes_gt_H_to_E20": int(np.sum(pre_cl > H)),
            "closes_ge_E10_to_E20": int(np.sum(pre_cl >= e10)),
        })

        for sm in SNAP_MINS:
            zi = e20_i + sm // 5
            snapshot_ts = idx[zi] if zi < len(idx) else pd.NaT
            exited = zi >= xi
            base = {
                "role": t.role,
                "partition": t.partition,
                "dev_block": t.dev_block,
                "execution_start": t.execution_start,
                "component": t.component,
                "parent_entry_ts": t.parent_entry_ts,
                "outcome": outcome,
                "e20_ts": idx[e20_i],
                "snapshot_min": sm,
                "snapshot_ts": snapshot_ts,
                "baseline_exited_by_snapshot": bool(exited),
                "baseline_exit_reason": t.exit_reason if exited else "ACTIVE",
                "baseline_exit_after_e20_min": float((idx[xi] - idx[e20_i]) / pd.Timedelta(minutes=1)),
            }
            if zi >= len(idx) or exited:
                base.update({
                    "close_R": np.nan,
                    "close_vs_E20_R": np.nan,
                    "post_e20_peak_R": np.nan,
                    "post_e20_giveback_from_peak_R": np.nan,
                    "post_e20_mae_below_E20_R": np.nan,
                    "closes_ge_E20": np.nan,
                    "fraction_closes_ge_E20": np.nan,
                    "closes_gt_H": np.nan,
                    "fraction_closes_gt_H": np.nan,
                    "consecutive_closes_ge_E20": np.nan,
                    "E25_by_snapshot": False,
                    "E30_by_snapshot": False,
                    "closed_back_le_E10": False,
                    "closed_back_le_H": False,
                })
                snap_rows.append(base)
                continue

            seg_cl = np.asarray(cl[e20_i:zi + 1], dtype=float)
            seg_hi = np.asarray(hi[e20_i:zi + 1], dtype=float)
            seg_lo = np.asarray(lo[e20_i:zi + 1], dtype=float)
            peak_R = (float(np.max(seg_hi)) - H) / R
            close_R = (float(cl[zi]) - H) / R
            # maximum completed-close giveback from the running post-E20 high watermark
            running_peak = -np.inf
            max_giveback = 0.0
            for hh, cc in zip(seg_hi, seg_cl):
                running_peak = max(running_peak, float(hh))
                max_giveback = max(max_giveback, (running_peak - float(cc)) / R)
            ge20 = seg_cl >= e20
            gtH = seg_cl > H
            base.update({
                "close_R": close_R,
                "close_vs_E20_R": close_R - E20_R,
                "post_e20_peak_R": peak_R,
                "post_e20_giveback_from_peak_R": max_giveback,
                "post_e20_mae_below_E20_R": max(0.0, (e20 - float(np.min(seg_lo))) / R),
                "closes_ge_E20": int(np.sum(ge20)),
                "fraction_closes_ge_E20": float(np.mean(ge20)),
                "closes_gt_H": int(np.sum(gtH)),
                "fraction_closes_gt_H": float(np.mean(gtH)),
                "consecutive_closes_ge_E20": consecutive_true_ending(ge20.tolist()),
                "E25_by_snapshot": bool(np.max(seg_hi) >= e25 - EPS),
                "E30_by_snapshot": bool(np.max(seg_hi) >= e30 - EPS),
                "closed_back_le_E10": bool(np.any(seg_cl <= e10 + EPS)),
                "closed_back_le_H": bool(np.any(seg_cl <= H + EPS)),
            })
            snap_rows.append(base)

    return pd.DataFrame(cohort_rows), pd.DataFrame(snap_rows)


def cohort_summary(c):
    rows = []
    for (role, part, comp, out), q in c.groupby(["role", "partition", "component", "outcome"], sort=False):
        rows.append({
            "role": role,
            "partition": part,
            "component": comp,
            "outcome": out,
            "n": len(q),
            "median_entry_to_e20_min": float(q.entry_to_e20_min.median()),
            "median_break_to_e20_min": float(q.break_to_e20_min.median()) if q.break_to_e20_min.notna().any() else np.nan,
            "median_e20_bar_close_R": float(q.e20_bar_close_R.median()),
            "median_close_vs_E20_R": float(q.e20_bar_close_vs_E20_R.median()),
            "median_mae_to_e20_R": float(q.running_mae_R_to_E20.median()),
            "median_closes_gt_H_to_E20": float(q.closes_gt_H_to_E20.median()),
        })
    # pooled rows
    for (role, part, out), q in c.groupby(["role", "partition", "outcome"], sort=False):
        rows.append({
            "role": role,
            "partition": part,
            "component": "POOLED",
            "outcome": out,
            "n": len(q),
            "median_entry_to_e20_min": float(q.entry_to_e20_min.median()),
            "median_break_to_e20_min": float(q.break_to_e20_min.median()) if q.break_to_e20_min.notna().any() else np.nan,
            "median_e20_bar_close_R": float(q.e20_bar_close_R.median()),
            "median_close_vs_E20_R": float(q.e20_bar_close_vs_E20_R.median()),
            "median_mae_to_e20_R": float(q.running_mae_R_to_E20.median()),
            "median_closes_gt_H_to_E20": float(q.closes_gt_H_to_E20.median()),
        })
    return pd.DataFrame(rows)


def qstats(x):
    y = pd.to_numeric(x, errors="coerce").dropna()
    if not len(y):
        return np.nan, np.nan, np.nan
    return float(y.quantile(.25)), float(y.quantile(.50)), float(y.quantile(.75))


def snapshot_summary(s):
    continuous = [
        "close_R", "close_vs_E20_R", "post_e20_peak_R", "post_e20_giveback_from_peak_R",
        "post_e20_mae_below_E20_R", "closes_ge_E20", "fraction_closes_ge_E20",
        "closes_gt_H", "fraction_closes_gt_H", "consecutive_closes_ge_E20",
    ]
    binary = ["baseline_exited_by_snapshot", "E25_by_snapshot", "E30_by_snapshot", "closed_back_le_E10", "closed_back_le_H"]
    rows = []
    grouping = ["role", "partition", "component", "outcome", "snapshot_min"]
    frames = [s]
    pooled = s.copy()
    pooled["component"] = "POOLED"
    frames.append(pooled)
    all_s = pd.concat(frames, ignore_index=True)
    for keys, q in all_s.groupby(grouping, sort=False):
        role, part, comp, out, sm = keys
        row = {"role": role, "partition": part, "component": comp, "outcome": out, "snapshot_min": sm, "n": len(q)}
        for f in continuous:
            a, b, c = qstats(q[f])
            row[f"{f}_q25"] = a
            row[f"{f}_q50"] = b
            row[f"{f}_q75"] = c
            row[f"{f}_n"] = int(pd.to_numeric(q[f], errors="coerce").notna().sum())
        for f in binary:
            row[f"{f}_rate"] = float(q[f].astype(bool).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def add_sep(rows, *, role, part, comp, stage, sm, feature, kind, cont_q, stall_q, meaningful_min):
    if kind == "median":
        cx = pd.to_numeric(cont_q[feature], errors="coerce").dropna()
        sx = pd.to_numeric(stall_q[feature], errors="coerce").dropna()
        cv = float(cx.median()) if len(cx) else np.nan
        sv = float(sx.median()) if len(sx) else np.nan
        cn, sn = len(cx), len(sx)
    elif kind == "rate":
        cv = float(cont_q[feature].astype(bool).mean()) if len(cont_q) else np.nan
        sv = float(stall_q[feature].astype(bool).mean()) if len(stall_q) else np.nan
        cn, sn = len(cont_q), len(stall_q)
    else:
        raise ValueError(kind)
    gap = cv - sv if pd.notna(cv) and pd.notna(sv) else np.nan
    rows.append({
        "role": role, "partition": part, "component": comp, "stage": stage,
        "snapshot_min": sm, "feature": feature, "kind": kind,
        "continuation_n": cn, "staller_n": sn,
        "continuation_value": cv, "staller_value": sv,
        "continuation_minus_staller": gap,
        "meaningful_min_abs_gap": meaningful_min,
        "development_meaningful": bool(pd.notna(gap) and abs(gap) >= meaningful_min),
    })


def separation(c, s):
    rows = []
    # Anchor features; direction is learned on Development then must replicate OOS.
    anchor = [
        ("entry_to_e20_min", "median", 10.0),
        ("break_to_e20_min", "median", 10.0),
        ("e20_bar_close_R", "median", 0.03),
        ("e20_bar_close_vs_E20_R", "median", 0.03),
        ("running_mae_R_to_E20", "median", 0.03),
        ("closes_gt_H_to_E20", "median", 1.0),
        ("closes_ge_E10_to_E20", "median", 1.0),
    ]
    snap = [
        ("close_R", "median", 0.03),
        ("close_vs_E20_R", "median", 0.03),
        ("post_e20_peak_R", "median", 0.03),
        ("post_e20_giveback_from_peak_R", "median", 0.03),
        ("post_e20_mae_below_E20_R", "median", 0.03),
        ("closes_ge_E20", "median", 1.0),
        ("fraction_closes_ge_E20", "median", 0.10),
        ("consecutive_closes_ge_E20", "median", 1.0),
        ("E25_by_snapshot", "rate", 0.10),
        ("E30_by_snapshot", "rate", 0.10),
        ("closed_back_le_E10", "rate", 0.10),
        ("closed_back_le_H", "rate", 0.10),
    ]

    for role in c.role.unique():
        for part in c[c.role == role].partition.unique():
            for comp in ["POOLED", "PARENT", "REC_H2"]:
                cq0 = c[(c.role == role) & (c.partition == part)]
                if comp != "POOLED":
                    cq0 = cq0[cq0.component == comp]
                cont_q = cq0[cq0.outcome == CONT]
                stall_q = cq0[cq0.outcome == STALL]
                if len(cont_q) and len(stall_q):
                    for f, kind, mg in anchor:
                        add_sep(rows, role=role, part=part, comp=comp, stage="ANCHOR", sm=0,
                                feature=f, kind=kind, cont_q=cont_q, stall_q=stall_q, meaningful_min=mg)

                sq0 = s[(s.role == role) & (s.partition == part)]
                if comp != "POOLED":
                    sq0 = sq0[sq0.component == comp]
                for sm in SNAP_MINS:
                    z = sq0[sq0.snapshot_min == sm]
                    cont_s = z[z.outcome == CONT]
                    stall_s = z[z.outcome == STALL]
                    if not len(cont_s) or not len(stall_s):
                        continue
                    for f, kind, mg in snap:
                        add_sep(rows, role=role, part=part, comp=comp, stage="SNAPSHOT", sm=sm,
                                feature=f, kind=kind, cont_q=cont_s, stall_q=stall_s, meaningful_min=mg)
    return pd.DataFrame(rows)


def decision(c, sep):
    cd = c[(c.role == "CENTRAL") & (c.partition == "development")]
    n_cont = int((cd.outcome == CONT).sum())
    n_stall = int((cd.outcome == STALL).sum())
    if n_cont < 80 or n_stall < 40:
        return False, f"Central Development pooled E20 N gate failed: continuation={n_cont}, staller={n_stall}", pd.DataFrame()

    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development") & (sep.component == "POOLED")].copy()
    ext = sep[(sep.role == "CENTRAL") & (sep.partition == "external") & (sep.component == "POOLED")].copy()
    rv = sep[(sep.role == "CENTRAL") & (sep.partition == "reference_validation") & (sep.component == "POOLED")].copy()
    keys = ["stage", "snapshot_min", "feature"]
    z = dev.merge(ext[keys + ["continuation_n", "staller_n", "continuation_minus_staller"]], on=keys, how="left", suffixes=("_dev", "_ext"))
    z = z.merge(rv[keys + ["continuation_n", "staller_n", "continuation_minus_staller"]], on=keys, how="left")
    z = z.rename(columns={
        "continuation_n": "continuation_n_refval",
        "staller_n": "staller_n_refval",
        "continuation_minus_staller": "continuation_minus_staller_refval",
    })
    z["dev_sign"] = np.sign(z.continuation_minus_staller_dev)
    z["same_direction"] = (
        (z.dev_sign != 0)
        & (np.sign(z.continuation_minus_staller_ext) == z.dev_sign)
        & (np.sign(z.continuation_minus_staller_refval) == z.dev_sign)
    )
    z["central_oos_n_ok"] = (
        (z.continuation_n_ext >= 20) & (z.staller_n_ext >= 15)
        & (z.continuation_n_refval >= 20) & (z.staller_n_refval >= 15)
    )
    z["replicated_candidate"] = z.development_meaningful.astype(bool) & z.same_direction & z.central_oos_n_ok

    # Support contradiction check: candidate direction cannot be reversed in both partitions of both support roles.
    candidates = z[z.replicated_candidate].copy()
    kept = []
    for _, r in candidates.iterrows():
        support = sep[(sep.role.isin(["CLOCK_SUPPORT", "REF_SUPPORT"])) & (sep.component == "POOLED")
                      & (sep.stage == r.stage) & (sep.snapshot_min == r.snapshot_min) & (sep.feature == r.feature)]
        signs = np.sign(pd.to_numeric(support.continuation_minus_staller, errors="coerce").dropna())
        reversed_count = int((signs == -r.dev_sign).sum())
        same_count = int((signs == r.dev_sign).sum())
        rr = r.to_dict()
        rr["support_same_direction"] = same_count
        rr["support_reversed"] = reversed_count
        rr["support_ok"] = not (len(signs) >= 4 and reversed_count >= 3)
        kept.append(rr)
    good = pd.DataFrame(kept)
    if len(good):
        good = good[good.support_ok].copy()
    supported = len(good) > 0
    reason = f"{len(good)} Development-meaningful fixed E20 dimensions replicate across both central OOS cells without broad support contradiction" if supported else "No Development-meaningful E20 dimension passed central OOS replication + support-direction gate"
    return supported, reason, good


def main():
    parent, h2, m, coverage = a11.load_system()
    cohort, snaps = build_anatomy(parent, h2, m)
    csum = cohort_summary(cohort)
    ssum = snapshot_summary(snaps)
    sep = separation(cohort, snaps)
    supported, reason, good = decision(cohort, sep)

    cohort.to_csv(OUT_COHORT, index=False)
    ssum.to_csv(OUT_SNAP, index=False)
    sep.to_csv(OUT_SEP, index=False)

    lines = [
        "# SOL LONG E20 Continuation vs Staller Anatomy — A13 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A13 is forensic only. The supported strategy remains A2 parent + A4 REC_H2; rejected A6/A8/A10/A11/A12 remain absent.", "",
        "## E20 cohort anatomy", "",
        "| Role | Partition | Component | Outcome | N | Median entry→E20 | Median break→E20 | Median E20 close | Median close vs E20 | Median MAE to E20 | Median closes >H |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in csum.iterrows():
        if r.component != "POOLED":
            continue
        lines.append(
            f"| {r.role} | {r.partition} | {r.component} | {r.outcome} | {int(r.n)} | {fmt_num(r.median_entry_to_e20_min,0)}m | {fmt_num(r.median_break_to_e20_min,0)}m | {fmt_num(r.median_e20_bar_close_R,3)}R | {fmt_num(r.median_close_vs_E20_R,3)}R | {fmt_num(r.median_mae_to_e20_R,3)}R | {fmt_num(r.median_closes_gt_H_to_E20,1)} |"
        )

    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development") & (sep.component == "POOLED")].copy()
    dev["abs_gap"] = dev.continuation_minus_staller.abs()
    lines += ["", "## Largest Central Development fixed separations", "",
              "| Stage | Snapshot | Feature | Cont N | Stall N | Continuation | Staller | Gap | Meaningful |",
              "|---|---:|---|---:|---:|---:|---:|---:|---|"]
    for _, r in dev.sort_values("abs_gap", ascending=False).head(24).iterrows():
        lines.append(
            f"| {r.stage} | +{int(r.snapshot_min)}m | {r.feature} | {int(r.continuation_n)} | {int(r.staller_n)} | {fmt_num(r.continuation_value,3)} | {fmt_num(r.staller_value,3)} | {fmt_num(r.continuation_minus_staller,3)} | {'YES' if r.development_meaningful else 'NO'} |"
        )

    lines += ["", "## Replicated A14 candidate dimensions", ""]
    if good is None or good.empty:
        lines.append("None.")
    else:
        lines.append("| Stage | Snapshot | Feature | Dev gap | External gap | RefVal gap | Support same/reversed |")
        lines.append("|---|---:|---|---:|---:|---:|---:|")
        for _, r in good.sort_values(["stage", "snapshot_min", "feature"]).iterrows():
            lines.append(
                f"| {r.stage} | +{int(r.snapshot_min)}m | {r.feature} | {fmt_num(r.continuation_minus_staller_dev,3)} | {fmt_num(r.continuation_minus_staller_ext,3)} | {fmt_num(r.continuation_minus_staller_refval,3)} | {int(r.support_same_direction)}/{int(r.support_reversed)} |"
            )

    status = "SOL_LONG_E20_CONTINUATION_A13_SUPPORTED_FOR_A14" if supported else "SOL_LONG_E20_CONTINUATION_A13_INCONCLUSIVE"
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "",
              "If supported, A14 may preregister only a small conditional protection family derived from rounded Central Development quantiles/discrete states. Clean continuation must remain eligible for E40.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
