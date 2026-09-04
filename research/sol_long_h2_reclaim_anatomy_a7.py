#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A5_PATH = Path(__file__).resolve().parent / "sol_long_h1_residual_failure_a5.py"
spec = importlib.util.spec_from_file_location("sol_a5", A5_PATH)
a5 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a5)
a4 = a5.a4

OUT_MD = ROOT / "SOL_LONG_H2_RECLAIM_ANATOMY_A7_Result.md"
OUT_ANAT = ROOT / "SOL_LONG_H2_RECLAIM_ANATOMY_A7_EPISODES.csv"
OUT_SUM = ROOT / "SOL_LONG_H2_RECLAIM_ANATOMY_A7_SUMMARY.csv"
OUT_SNAP = ROOT / "SOL_LONG_H2_RECLAIM_ANATOMY_A7_SNAPSHOTS.csv"
OUT_STATUS = ROOT / "SOL_LONG_H2_RECLAIM_ANATOMY_A7_Status.txt"
SNAP_MINS = (5, 10, 15, 30, 60)
TARGET_R = 0.40


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def fmt_num(v, d=2):
    return "-" if pd.isna(v) else f"{float(v):.{d}f}"


def build_anatomy(parent, episodes, m):
    pmap = {
        (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_ts)): r
        for _, r in parent.iterrows()
    }
    rows = []
    snaps = []
    idx = m["idx"]
    hi = m["high"]
    lo = m["low"]
    cl = m["close"]

    q = episodes[(episodes.parent_pnl <= 0) & episodes.h2_eligible].copy()
    for _, e in q.iterrows():
        key = (e.role, e.partition, pd.Timestamp(e.execution_start), pd.Timestamp(e.parent_entry_ts))
        r = pmap[key]
        w = a4.recovery_window(m, r)
        if w is None:
            continue
        _, _, endpos, _ = w
        xit = pd.Timestamp(e.h2_recovery_exit_ts)
        xi = int(idx.searchsorted(xit, "left"))
        if xi >= len(idx) or idx[xi] != xit or xi >= endpos:
            continue
        H, R = float(e.H), float(e.R)
        target = H + TARGET_R * R

        reclaim_i = -1
        for i in range(xi, endpos):
            if float(cl[i]) > H:
                reclaim_i = i
                break

        target_i = -1
        for i in range(xi, endpos):
            if float(hi[i]) >= target:
                target_i = i
                break

        causal_target_i = -1
        if reclaim_i >= 0:
            for i in range(reclaim_i + 1, endpos):
                if float(hi[i]) >= target:
                    causal_target_i = i
                    break

        pre_end = reclaim_i + 1 if reclaim_i >= 0 else endpos
        seg_lo = np.asarray(lo[xi:pre_end], dtype=float)
        seg_cl = np.asarray(cl[xi:pre_end], dtype=float)
        min_close_R = (float(np.min(seg_cl)) - H) / R if len(seg_cl) else np.nan
        max_adverse_R = max(0.0, (H - float(np.min(seg_lo))) / R) if len(seg_lo) else np.nan
        closes_le = int(np.sum(seg_cl <= H)) if len(seg_cl) else 0

        rows.append({
            "role": e.role,
            "partition": e.partition,
            "dev_block": e.dev_block,
            "execution_start": e.execution_start,
            "episode_class": e.episode_class,
            "loss_class": e.loss_class,
            "parent_pnl": e.parent_pnl,
            "h2_recovery_pnl": e.h2_recovery_pnl,
            "episode_pnl": e.episode_pnl,
            "h2_exit_reason": e.h2_recovery_reason,
            "h2_entry_ts": e.h2_recovery_entry_ts,
            "h2_exit_ts": e.h2_recovery_exit_ts,
            "post_exit_reclaim": reclaim_i >= 0,
            "reclaim_ts": idx[reclaim_i] if reclaim_i >= 0 else pd.NaT,
            "reclaim_min": ((idx[reclaim_i] - xit) / pd.Timedelta(minutes=1)) if reclaim_i >= 0 else np.nan,
            "closes_le_H_before_reclaim": closes_le,
            "min_close_R_before_reclaim": min_close_R,
            "max_adverse_R_before_reclaim": max_adverse_R,
            "target_after_h2_exit": target_i >= 0,
            "target_after_h2_exit_min": ((idx[target_i] - xit) / pd.Timedelta(minutes=1)) if target_i >= 0 else np.nan,
            "target_after_causal_reclaim": causal_target_i >= 0,
            "reclaim_to_target_min": ((idx[causal_target_i] - idx[reclaim_i]) / pd.Timedelta(minutes=1)) if causal_target_i >= 0 else np.nan,
        })

        for sm in SNAP_MINS:
            si = xi + (sm // 5) - 1
            if si >= endpos:
                continue
            seg_hi = np.asarray(hi[xi:si + 1], dtype=float)
            seg_lo2 = np.asarray(lo[xi:si + 1], dtype=float)
            seg_cl2 = np.asarray(cl[xi:si + 1], dtype=float)
            snaps.append({
                "role": e.role,
                "partition": e.partition,
                "episode_class": e.episode_class,
                "snapshot_min": sm,
                "close_R": (float(cl[si]) - H) / R,
                "running_mfe_R": max(0.0, (float(np.max(seg_hi)) - H) / R),
                "running_mae_R": max(0.0, (H - float(np.min(seg_lo2))) / R),
                "reclaim_by_snapshot": bool(np.any(seg_cl2 > H)),
                "closes_above_H": int(np.sum(seg_cl2 > H)),
                "closes_le_H": int(np.sum(seg_cl2 <= H)),
            })
    return pd.DataFrame(rows), pd.DataFrame(snaps)


def summarize(anat):
    rows = []
    for (role, part, ec), q in anat.groupby(["role", "partition", "episode_class"], sort=False):
        rc = q[q.post_exit_reclaim]
        rows.append({
            "role": role, "partition": part, "episode_class": ec, "n": len(q),
            "reclaim_rate": float(q.post_exit_reclaim.mean()),
            "median_reclaim_min": float(rc.reclaim_min.median()) if len(rc) else np.nan,
            "target_after_exit_rate": float(q.target_after_h2_exit.mean()),
            "target_after_causal_reclaim_rate": float(q.target_after_causal_reclaim.mean()),
            "median_reclaim_to_target_min": float(q.loc[q.target_after_causal_reclaim, "reclaim_to_target_min"].median()) if q.target_after_causal_reclaim.any() else np.nan,
            "median_closes_le_H_before_reclaim": float(rc.closes_le_H_before_reclaim.median()) if len(rc) else np.nan,
            "median_min_close_R_before_reclaim": float(rc.min_close_R_before_reclaim.median()) if len(rc) else np.nan,
            "median_max_adverse_R_before_reclaim": float(rc.max_adverse_R_before_reclaim.median()) if len(rc) else np.nan,
        })
    return pd.DataFrame(rows)


def snapshot_summary(s):
    rows = []
    for (role, part, ec, sm), q in s.groupby(["role", "partition", "episode_class", "snapshot_min"], sort=False):
        rows.append({
            "role": role, "partition": part, "episode_class": ec, "snapshot_min": sm, "n": len(q),
            "reclaim_by_snapshot_rate": float(q.reclaim_by_snapshot.mean()),
            "median_close_R": float(q.close_R.median()),
            "median_running_mfe_R": float(q.running_mfe_R.median()),
            "median_running_mae_R": float(q.running_mae_R.median()),
            "median_closes_above_H": float(q.closes_above_H.median()),
            "median_closes_le_H": float(q.closes_le_H.median()),
        })
    return pd.DataFrame(rows)


def getrow(summary, role, part, ec):
    z = summary[(summary.role == role) & (summary.partition == part) & (summary.episode_class == ec)]
    return None if z.empty else z.iloc[0]


def main():
    parent, m, coverage = a5.load_system()
    episodes, _ = a5.build_episodes(parent, m)
    anat, raw_snaps = build_anatomy(parent, episodes, m)
    summary = summarize(anat)
    snaps = snapshot_summary(raw_snaps)

    anat.to_csv(OUT_ANAT, index=False)
    summary.to_csv(OUT_SUM, index=False)
    snaps.to_csv(OUT_SNAP, index=False)

    cd_l = getrow(summary, "CENTRAL", "development", "RESIDUAL_LATENT_RECOVERABLE")
    cd_t = getrow(summary, "CENTRAL", "development", "RESIDUAL_TRUE_FAILURE_PROXY")
    ce_l = getrow(summary, "CENTRAL", "external", "RESIDUAL_LATENT_RECOVERABLE")
    ce_t = getrow(summary, "CENTRAL", "external", "RESIDUAL_TRUE_FAILURE_PROXY")
    cr_l = getrow(summary, "CENTRAL", "reference_validation", "RESIDUAL_LATENT_RECOVERABLE")
    cr_t = getrow(summary, "CENTRAL", "reference_validation", "RESIDUAL_TRUE_FAILURE_PROXY")

    supported = False
    reason = "Required cohorts missing"
    if all(x is not None for x in [cd_l, cd_t, ce_l, ce_t, cr_l, cr_t]):
        dev_gap = float(cd_l.reclaim_rate - cd_t.reclaim_rate)
        ext_gap = float(ce_l.reclaim_rate - ce_t.reclaim_rate)
        ref_gap = float(cr_l.reclaim_rate - cr_t.reclaim_rate)
        supported = bool(
            int(cd_l.n) >= 40
            and float(cd_l.reclaim_rate) >= 0.50
            and dev_gap >= 0.15
            and float(cd_l.target_after_causal_reclaim_rate) >= 0.50
            and ext_gap > 0
            and ref_gap > 0
        )
        reason = f"Development reclaim gap={dev_gap:.1%}; External gap={ext_gap:.1%}; RefVal gap={ref_gap:.1%}"

    lines = [
        "# SOL LONG H2 Reclaim Anatomy — A7 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A7 is forensic only. It studies what happens after the frozen H2 recovery exits.", "",
        "## Reclaim anatomy", "",
        "| Role | Partition | Episode class | N | Post-exit reclaim | Median reclaim | E40 after exit | E40 after causal reclaim | Reclaim→E40 median | Median adverse before reclaim |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in summary.iterrows():
        if r.episode_class not in ["RESIDUAL_LATENT_RECOVERABLE", "RESIDUAL_TRUE_FAILURE_PROXY"]:
            continue
        lines.append(
            f"| {r.role} | {r.partition} | {r.episode_class} | {int(r.n)} | {fmt_pct(r.reclaim_rate)} | {fmt_num(r.median_reclaim_min,0)}m | {fmt_pct(r.target_after_exit_rate)} | {fmt_pct(r.target_after_causal_reclaim_rate)} | {fmt_num(r.median_reclaim_to_target_min,0)}m | {fmt_num(r.median_max_adverse_R_before_reclaim,3)}R |"
        )

    lines += ["", "## Central Development post-H2-exit snapshots", "",
              "| Class | Snapshot | N | Reclaimed | Median close | Median MFE | Median MAE |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    z = snaps[(snaps.role == "CENTRAL") & (snaps.partition == "development") & snaps.episode_class.isin(["RESIDUAL_LATENT_RECOVERABLE", "RESIDUAL_TRUE_FAILURE_PROXY"])].sort_values(["snapshot_min", "episode_class"])
    for _, r in z.iterrows():
        lines.append(
            f"| {r.episode_class} | +{int(r.snapshot_min)}m | {int(r.n)} | {fmt_pct(r.reclaim_by_snapshot_rate)} | {fmt_num(r.median_close_R,3)}R | {fmt_num(r.median_running_mfe_R,3)}R | {fmt_num(r.median_running_mae_R,3)}R |"
        )

    status = "SOL_LONG_H2_RECLAIM_ANATOMY_A7_SUPPORTED_FOR_REENTRY" if supported else "SOL_LONG_H2_RECLAIM_ANATOMY_A7_INCONCLUSIVE"
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "",
              "If supported, the next stage may test a reclaim-confirmed next-open re-entry. It may not substitute a resting H3/H4 retry.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
