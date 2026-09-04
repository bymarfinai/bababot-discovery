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

OUT_MD = ROOT / "SOL_LONG_H2_RECLAIM_QUALITY_A9_Result.md"
OUT_ANAT = ROOT / "SOL_LONG_H2_RECLAIM_QUALITY_A9_ANATOMY.csv"
OUT_SNAP = ROOT / "SOL_LONG_H2_RECLAIM_QUALITY_A9_SNAPSHOTS.csv"
OUT_SEP = ROOT / "SOL_LONG_H2_RECLAIM_QUALITY_A9_SEPARATION.csv"
OUT_STATUS = ROOT / "SOL_LONG_H2_RECLAIM_QUALITY_A9_Status.txt"
SNAP_MINS = (5, 10, 15, 30, 60)
TARGET_R = 0.40

CLASSES = ("RESIDUAL_LATENT_RECOVERABLE", "RESIDUAL_TRUE_FAILURE_PROXY")


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def fmt_num(v, d=3):
    if pd.isna(v): return "-"
    return f"{float(v):.{d}f}"


def load_system():
    parent, m, coverage = a5.load_system()
    episodes, _ = a5.build_episodes(parent, m)
    return parent, episodes, m, coverage


def parent_lookup(parent):
    return {
        (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_ts)): r
        for _, r in parent.iterrows()
    }


def first_reclaim(idx, cl, start_i, endpos, H):
    for i in range(start_i, endpos):
        if float(cl[i]) > H:
            return i
    return -1


def cycles_after_reclaim(cl, signal_i, endpos, H):
    cycles = 0
    above = False
    for i in range(signal_i, endpos):
        now = float(cl[i]) > H
        if now and not above:
            cycles += 1
        above = now
    return cycles


def anatomy(parent, episodes, m):
    pmap = parent_lookup(parent)
    idx, hi, lo, cl = m["idx"], m["high"], m["low"], m["close"]
    rows, snaps = [], []
    q = episodes[
        (episodes.parent_pnl <= 0)
        & episodes.h2_eligible.astype(bool)
        & episodes.episode_class.isin(CLASSES)
    ].copy()

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
        si = first_reclaim(idx, cl, xi, endpos, H)
        has = si >= 0

        base = {
            "role": e.role,
            "partition": e.partition,
            "dev_block": e.dev_block,
            "execution_start": e.execution_start,
            "episode_class": e.episode_class,
            "loss_class": e.loss_class,
            "H": H, "L": float(e.L), "R": R,
            "h2_exit_ts": xit,
            "has_reclaim": has,
            "reclaim_ts": idx[si] if has else pd.NaT,
            "reclaim_min": ((idx[si] - xit) / pd.Timedelta(minutes=1)) if has else np.nan,
            "initial_consecutive_closes_above_H": np.nan,
            "first_failure_min": np.nan,
            "max_close_R_before_first_failure": np.nan,
            "max_high_R_before_first_failure": np.nan,
            "max_adverse_R_before_first_failure": np.nan,
            "E40_before_first_failure": False,
            "E40_eventually_after_reclaim": False,
            "reclaim_failure_cycles": np.nan,
        }
        if not has:
            rows.append(base)
            continue

        # Persistence beginning with the signal close itself.
        failure_i = -1
        consec = 0
        for i in range(si, endpos):
            if float(cl[i]) > H:
                consec += 1
            else:
                failure_i = i
                break
        pre_end = failure_i + 1 if failure_i >= 0 else endpos
        seg_cl = np.asarray(cl[si:pre_end], dtype=float)
        seg_hi = np.asarray(hi[si:pre_end], dtype=float)
        seg_lo = np.asarray(lo[si:pre_end], dtype=float)
        first_failure_min = ((idx[failure_i] - idx[si]) / pd.Timedelta(minutes=1)) if failure_i >= 0 else np.nan
        max_close_R = (float(np.max(seg_cl)) - H) / R if len(seg_cl) else np.nan
        max_high_R = max(0.0, (float(np.max(seg_hi)) - H) / R) if len(seg_hi) else np.nan
        max_adv_R = max(0.0, (H - float(np.min(seg_lo))) / R) if len(seg_lo) else np.nan

        first_fail_boundary = failure_i if failure_i >= 0 else endpos
        e40_before = any(float(hi[i]) >= target for i in range(si, first_fail_boundary))
        e40_eventual = any(float(hi[i]) >= target for i in range(si, endpos))
        cycles = cycles_after_reclaim(cl, si, endpos, H)
        base.update({
            "initial_consecutive_closes_above_H": consec,
            "first_failure_min": first_failure_min,
            "max_close_R_before_first_failure": max_close_R,
            "max_high_R_before_first_failure": max_high_R,
            "max_adverse_R_before_first_failure": max_adv_R,
            "E40_before_first_failure": e40_before,
            "E40_eventually_after_reclaim": e40_eventual,
            "reclaim_failure_cycles": cycles,
        })
        rows.append(base)

        for sm in SNAP_MINS:
            # +5m after signal means the next completed 5m bar.
            zi = si + sm // 5
            if zi >= endpos:
                continue
            seg_cl2 = np.asarray(cl[si:zi + 1], dtype=float)
            seg_hi2 = np.asarray(hi[si:zi + 1], dtype=float)
            seg_lo2 = np.asarray(lo[si:zi + 1], dtype=float)
            n_above = int(np.sum(seg_cl2 > H))
            n_le = int(np.sum(seg_cl2 <= H))
            snaps.append({
                "role": e.role,
                "partition": e.partition,
                "dev_block": e.dev_block,
                "execution_start": e.execution_start,
                "episode_class": e.episode_class,
                "snapshot_min": sm,
                "close_R": (float(cl[zi]) - H) / R,
                "running_mfe_R": max(0.0, (float(np.max(seg_hi2)) - H) / R),
                "running_mae_R": max(0.0, (H - float(np.min(seg_lo2))) / R),
                "closes_above_H": n_above,
                "closes_le_H": n_le,
                "fraction_closes_above_H": n_above / len(seg_cl2),
                "failed_by_snapshot": bool(np.any(seg_cl2[1:] <= H)) if len(seg_cl2) > 1 else False,
                "E10_by_snapshot": bool(np.max(seg_hi2) >= H + 0.10 * R),
                "E20_by_snapshot": bool(np.max(seg_hi2) >= H + 0.20 * R),
            })
    return pd.DataFrame(rows), pd.DataFrame(snaps)


def anatomy_summary(a):
    rows = []
    for (role, part, ec), q in a.groupby(["role", "partition", "episode_class"], sort=False):
        r = q[q.has_reclaim].copy()
        rows.append({
            "role": role, "partition": part, "episode_class": ec,
            "n": len(q), "reclaimed_n": len(r), "reclaim_rate": float(q.has_reclaim.mean()),
            "median_reclaim_min": float(r.reclaim_min.median()) if len(r) else np.nan,
            "median_initial_consecutive_above": float(r.initial_consecutive_closes_above_H.median()) if len(r) else np.nan,
            "q75_initial_consecutive_above": float(r.initial_consecutive_closes_above_H.quantile(.75)) if len(r) else np.nan,
            "median_first_failure_min": float(r.first_failure_min.median()) if r.first_failure_min.notna().any() else np.nan,
            "median_max_close_R_before_failure": float(r.max_close_R_before_first_failure.median()) if len(r) else np.nan,
            "median_max_high_R_before_failure": float(r.max_high_R_before_first_failure.median()) if len(r) else np.nan,
            "E40_before_first_failure_rate": float(r.E40_before_first_failure.mean()) if len(r) else np.nan,
            "E40_eventual_rate": float(r.E40_eventually_after_reclaim.mean()) if len(r) else np.nan,
            "median_cycles": float(r.reclaim_failure_cycles.median()) if len(r) else np.nan,
        })
    return pd.DataFrame(rows)


def snapshot_summary(s):
    continuous = ["close_R", "running_mfe_R", "running_mae_R", "closes_above_H", "closes_le_H", "fraction_closes_above_H"]
    binary = ["failed_by_snapshot", "E10_by_snapshot", "E20_by_snapshot"]
    rows = []
    for (role, part, ec, sm), q in s.groupby(["role", "partition", "episode_class", "snapshot_min"], sort=False):
        row = {"role": role, "partition": part, "episode_class": ec, "snapshot_min": sm, "n": len(q)}
        for f in continuous:
            x = pd.to_numeric(q[f], errors="coerce").dropna()
            row[f"{f}_q25"] = float(x.quantile(.25)) if len(x) else np.nan
            row[f"{f}_q50"] = float(x.quantile(.50)) if len(x) else np.nan
            row[f"{f}_q75"] = float(x.quantile(.75)) if len(x) else np.nan
        for f in binary:
            row[f"{f}_rate"] = float(q[f].astype(bool).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def separation(s):
    features = [
        ("close_R", "median"),
        ("running_mfe_R", "median"),
        ("closes_above_H", "median"),
        ("fraction_closes_above_H", "median"),
        ("E10_by_snapshot", "rate"),
        ("E20_by_snapshot", "rate"),
    ]
    rows = []
    for (role, part, sm), q in s.groupby(["role", "partition", "snapshot_min"], sort=False):
        lat = q[q.episode_class == "RESIDUAL_LATENT_RECOVERABLE"]
        tru = q[q.episode_class == "RESIDUAL_TRUE_FAILURE_PROXY"]
        if len(lat) < 5 or len(tru) < 5:
            continue
        for f, kind in features:
            if kind == "rate":
                lv = float(lat[f].astype(bool).mean()); tv = float(tru[f].astype(bool).mean())
            else:
                lv = float(pd.to_numeric(lat[f], errors="coerce").median()); tv = float(pd.to_numeric(tru[f], errors="coerce").median())
            rows.append({
                "role": role, "partition": part, "snapshot_min": sm, "feature": f,
                "latent_n": len(lat), "true_n": len(tru),
                "latent_value": lv, "true_value": tv, "latent_minus_true": lv - tv,
            })
    return pd.DataFrame(rows)


def decision(a_summary, sep):
    cd_lat = a_summary[(a_summary.role == "CENTRAL") & (a_summary.partition == "development") & (a_summary.episode_class == "RESIDUAL_LATENT_RECOVERABLE")]
    cd_true = a_summary[(a_summary.role == "CENTRAL") & (a_summary.partition == "development") & (a_summary.episode_class == "RESIDUAL_TRUE_FAILURE_PROXY")]
    if cd_lat.empty or cd_true.empty or int(cd_lat.iloc[0].reclaimed_n) < 40 or int(cd_true.iloc[0].reclaimed_n) < 40:
        return False, "Central Development reclaimed class N below gate", pd.DataFrame()

    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].copy()
    ext = sep[(sep.role == "CENTRAL") & (sep.partition == "external")].copy()
    rv = sep[(sep.role == "CENTRAL") & (sep.partition == "reference_validation")].copy()
    keys = ["snapshot_min", "feature"]
    z = dev.merge(ext[keys + ["latent_n", "true_n", "latent_minus_true"]], on=keys, how="left", suffixes=("_dev", "_ext"))
    z = z.merge(rv[keys + ["latent_n", "true_n", "latent_minus_true"]], on=keys, how="left")
    z = z.rename(columns={"latent_n": "latent_n_refval", "true_n": "true_n_refval", "latent_minus_true": "latent_minus_true_refval"})
    z["same_positive_direction"] = (
        (z.latent_minus_true_dev > 0)
        & (z.latent_minus_true_ext > 0)
        & (z.latent_minus_true_refval > 0)
        & (z.latent_n_ext >= 20) & (z.true_n_ext >= 20)
        & (z.latent_n_refval >= 20) & (z.true_n_refval >= 20)
    )
    good = z[z.same_positive_direction].copy()
    if good.empty:
        return False, "No same-direction persistence feature replicated in both central OOS cells", z
    return True, f"{len(good)} fixed snapshot persistence comparisons replicate latent>true across both central OOS cells", z


def main():
    parent, episodes, m, coverage = load_system()
    a, raw_s = anatomy(parent, episodes, m)
    asum = anatomy_summary(a)
    ssum = snapshot_summary(raw_s)
    sep = separation(raw_s)
    supported, reason, repl = decision(asum, sep)

    a.to_csv(OUT_ANAT, index=False)
    ssum.to_csv(OUT_SNAP, index=False)
    sep.to_csv(OUT_SEP, index=False)

    lines = [
        "# SOL LONG H2 Reclaim Quality — A9 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A9 is forensic only. A8 remains rejected; no trading rule is changed.", "",
        "## Reclaim persistence anatomy", "",
        "| Role | Partition | Class | N | Reclaimed | Median consecutive >H | Q75 consecutive >H | Median failure time | Median max close | E40 before first failure | E40 eventual | Median cycles |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in asum.iterrows():
        if r.episode_class not in CLASSES: continue
        lines.append(
            f"| {r.role} | {r.partition} | {r.episode_class} | {int(r.n)} | {int(r.reclaimed_n)} | {fmt_num(r.median_initial_consecutive_above,1)} | {fmt_num(r.q75_initial_consecutive_above,1)} | {fmt_num(r.median_first_failure_min,0)}m | {fmt_num(r.median_max_close_R_before_failure,3)}R | {fmt_pct(r.E40_before_first_failure_rate)} | {fmt_pct(r.E40_eventual_rate)} | {fmt_num(r.median_cycles,1)} |"
        )

    cd = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].copy()
    cd["abs_gap"] = cd.latent_minus_true.abs()
    lines += ["", "## Central Development fixed post-reclaim separations", "",
              "| Snapshot | Feature | Latent N | True N | Latent | True | Gap |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    for _, r in cd.sort_values("abs_gap", ascending=False).head(20).iterrows():
        lines.append(f"| +{int(r.snapshot_min)}m | {r.feature} | {int(r.latent_n)} | {int(r.true_n)} | {fmt_num(r.latent_value,3)} | {fmt_num(r.true_value,3)} | {fmt_num(r.latent_minus_true,3)} |")

    if len(repl):
        good = repl[repl.same_positive_direction].copy()
        lines += ["", "## Replicated candidate dimensions", ""]
        if good.empty:
            lines.append("None.")
        else:
            lines.append("| Snapshot | Feature | Dev gap | External gap | RefVal gap |")
            lines.append("|---:|---|---:|---:|---:|")
            for _, r in good.iterrows():
                lines.append(f"| +{int(r.snapshot_min)}m | {r.feature} | {fmt_num(r.latent_minus_true_dev,3)} | {fmt_num(r.latent_minus_true_ext,3)} | {fmt_num(r.latent_minus_true_refval,3)} |")

    status = "SOL_LONG_H2_RECLAIM_QUALITY_A9_SUPPORTED_FOR_A10" if supported else "SOL_LONG_H2_RECLAIM_QUALITY_A9_INCONCLUSIVE"
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "",
              "If supported, A10 may preregister only a small persistence-confirmed re-entry family derived from rounded Central Development state counts/quantiles. A8 RC30 itself stays rejected.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
