#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A4_PATH = Path(__file__).resolve().parent / "sol_long_h1_loss_recovery_a4.py"
spec = importlib.util.spec_from_file_location("sol_a4", A4_PATH)
a4 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a4)
a2 = a4.a2

OUT_MD = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_Result.md"
OUT_EP = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_EPISODES.csv"
OUT_DAMAGE = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_DAMAGE.csv"
OUT_CLASS = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_LOSS_CLASSES.csv"
OUT_SNAP = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_SNAPSHOTS.csv"
OUT_SEP = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_SEPARATION.csv"
OUT_STATUS = ROOT / "SOL_LONG_H1_RESIDUAL_FAILURE_A5_Status.txt"

SNAP_MINS = (5, 10, 15, 30, 60)
EPS = 1e-12


def fmt_num(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100.0 * float(v):.1f}%"


def load_system():
    parent = a4.load_parent()
    a3c = a4.load_a3_classes()
    parent = parent.merge(
        a3c,
        on=["role", "partition", "execution_start", "entry_ts", "exit_ts"],
        how="left",
        validate="one_to_one",
    )
    if parent.loss_class.isna().any():
        raise RuntimeError("A3 loss-class merge parity failure")
    _, m, coverage = a4.market()
    return parent, m, coverage


def build_episodes(parent, m):
    rows = []
    rec_by_key = {}
    for _, r in parent.iterrows():
        key = (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_ts))
        parent_pnl = float(r.pnl)
        parent_pnl5 = float(r.pnl_5bps)
        rec = None
        latent = None
        if parent_pnl <= 0:
            rec = a4.simulate_recovery(m, r, 2)
            latent = a4.latent_anatomy_one(m, r)
        rec_pnl = float(rec["recovery_pnl"]) if rec is not None else 0.0
        rec_pnl5 = float(rec["recovery_pnl_5bps"]) if rec is not None else 0.0
        ep = parent_pnl + rec_pnl
        ep5 = parent_pnl5 + rec_pnl5
        latent_hit = bool(latent["latent_target_recovered"]) if latent is not None else False

        if parent_pnl > 0:
            eclass = "PARENT_WIN"
        elif rec is not None and ep > 0:
            eclass = "H2_ECONOMIC_RESCUE"
        elif latent_hit:
            eclass = "RESIDUAL_LATENT_RECOVERABLE"
        else:
            eclass = "RESIDUAL_TRUE_FAILURE_PROXY"

        row = {
            "role": r.role,
            "partition": r.partition,
            "dev_block": r.dev_block,
            "execution_start": r.execution_start,
            "parent_entry_ts": r.entry_ts,
            "parent_exit_ts": r.exit_ts,
            "loss_class": r.loss_class,
            "H": float(r.H),
            "L": float(r.L),
            "R": float(r.R),
            "parent_pnl": parent_pnl,
            "parent_pnl_5bps": parent_pnl5,
            "h2_eligible": rec is not None,
            "h2_recovery_entry_ts": rec["recovery_entry_ts"] if rec is not None else pd.NaT,
            "h2_recovery_exit_ts": rec["recovery_exit_ts"] if rec is not None else pd.NaT,
            "h2_recovery_reason": rec["recovery_exit_reason"] if rec is not None else "NONE",
            "h2_recovery_pnl": rec_pnl,
            "h2_recovery_pnl_5bps": rec_pnl5,
            "episode_pnl": ep,
            "episode_pnl_5bps": ep5,
            "episode_class": eclass,
            "latent_target_recovered": latent_hit,
            "latent_recovery_min": latent["latent_recovery_min"] if latent is not None else np.nan,
            "latent_target_visit": latent["latent_target_visit"] if latent is not None else np.nan,
        }
        rows.append(row)
        if rec is not None:
            rec_by_key[key] = rec
    return pd.DataFrame(rows), rec_by_key


def snapshot_one(m, entry_ts, exit_ts, H, L, R, snap_min):
    idx = m["idx"]
    ei = int(idx.searchsorted(pd.Timestamp(entry_ts), "left"))
    xi = int(idx.searchsorted(pd.Timestamp(exit_ts), "left"))
    if ei >= len(idx) or xi >= len(idx) or idx[ei] != pd.Timestamp(entry_ts) or idx[xi] != pd.Timestamp(exit_ts):
        return None
    si = ei + (snap_min // 5) - 1
    if si > xi or si >= len(idx):
        return None
    hi = np.asarray(m["high"][ei:si + 1], dtype=float)
    lo = np.asarray(m["low"][ei:si + 1], dtype=float)
    cl = np.asarray(m["close"][ei:si + 1], dtype=float)
    close_R = (float(cl[-1]) - H) / R
    return {
        "close_R": close_R,
        "running_mfe_R": max(0.0, (float(np.max(hi)) - H) / R),
        "running_mae_R": max(0.0, (H - float(np.min(lo))) / R),
        "break_confirmed_by_snapshot": bool(np.any(cl > H)),
        "closes_above_H": int(np.sum(cl > H)),
        "closes_le_H": int(np.sum(cl <= H)),
        "close_minus_L_R": (float(cl[-1]) - L) / R,
    }


def build_snapshots(parent, episodes, rec_by_key, m):
    emap = {
        (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.parent_entry_ts)): r
        for _, r in episodes.iterrows()
    }
    rows = []
    for _, r in parent.iterrows():
        key = (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_ts))
        e = emap[key]
        for sm in SNAP_MINS:
            z = snapshot_one(m, r.entry_ts, r.exit_ts, float(r.H), float(r.L), float(r.R), sm)
            if z is not None:
                rows.append({
                    "role": r.role,
                    "partition": r.partition,
                    "execution_start": r.execution_start,
                    "attempt": "PARENT",
                    "snapshot_min": sm,
                    "episode_class": e.episode_class,
                    "loss_class": r.loss_class,
                    **z,
                })
        rec = rec_by_key.get(key)
        if rec is not None:
            for sm in SNAP_MINS:
                z = snapshot_one(
                    m,
                    rec["recovery_entry_ts"],
                    rec["recovery_exit_ts"],
                    float(r.H), float(r.L), float(r.R), sm,
                )
                if z is not None:
                    rows.append({
                        "role": r.role,
                        "partition": r.partition,
                        "execution_start": r.execution_start,
                        "attempt": "H2",
                        "snapshot_min": sm,
                        "episode_class": e.episode_class,
                        "loss_class": r.loss_class,
                        **z,
                    })
    return pd.DataFrame(rows)


def damage_summary(ep):
    rows = []
    for (role, part), q in ep.groupby(["role", "partition"], sort=False):
        residual = q[q.episode_pnl <= 0].copy()
        true = q[q.episode_class == "RESIDUAL_TRUE_FAILURE_PROXY"].copy()
        latent = q[q.episode_class == "RESIDUAL_LATENT_RECOVERABLE"].copy()
        resc = q[q.episode_class == "H2_ECONOMIC_RESCUE"].copy()
        gl = float(-residual.episode_pnl.sum()) if len(residual) else 0.0
        gl5 = float(-residual.episode_pnl_5bps.sum()) if len(residual) else 0.0
        true_gl = float(-true.episode_pnl.sum()) if len(true) else 0.0
        never = residual[residual.loss_class.isin(["L0_NEVER_BREAK_REFERENCE_INVALIDATION", "L1_NEVER_BREAK_TIME"])]
        failed = residual[residual.loss_class.isin([
            "L2_BREAK_FAST_FAIL_5M", "L3_BREAK_FAST_FAIL_10M", "L4_BREAK_FAIL_30M", "L5_BREAK_FAIL_LATE", "L6_BREAK_TIME_OR_OTHER"
        ])]
        rows.append({
            "role": role,
            "partition": part,
            "parent_n": len(q),
            "parent_win_n": int((q.parent_pnl > 0).sum()),
            "parent_loss_n": int((q.parent_pnl <= 0).sum()),
            "h2_eligible_n": int(q.h2_eligible.sum()),
            "h2_rescue_n": len(resc),
            "residual_n": len(residual),
            "latent_residual_n": len(latent),
            "true_failure_proxy_n": len(true),
            "residual_gross_loss": gl,
            "residual_gross_loss_5bps": gl5,
            "true_failure_proxy_gross_loss": true_gl,
            "true_failure_share_residual_loss": true_gl / gl if gl > 0 else np.nan,
            "never_break_share_residual_loss": float(-never.episode_pnl.sum()) / gl if gl > 0 else np.nan,
            "failed_break_share_residual_loss": float(-failed.episode_pnl.sum()) / gl if gl > 0 else np.nan,
            "median_residual_loss": float((-residual.episode_pnl).median()) if len(residual) else np.nan,
            "q90_residual_loss": float((-residual.episode_pnl).quantile(0.90)) if len(residual) else np.nan,
            "max_residual_loss": float(-residual.episode_pnl.min()) if len(residual) else np.nan,
        })
    return pd.DataFrame(rows)


def loss_class_summary(ep):
    rows = []
    residual = ep[ep.episode_pnl <= 0].copy()
    for (role, part, lc, ec), q in residual.groupby(["role", "partition", "loss_class", "episode_class"], sort=False):
        rows.append({
            "role": role,
            "partition": part,
            "loss_class": lc,
            "episode_class": ec,
            "n": len(q),
            "gross_loss": float(-q.episode_pnl.sum()),
            "gross_loss_5bps": float(-q.episode_pnl_5bps.sum()),
            "median_loss": float((-q.episode_pnl).median()),
            "q90_loss": float((-q.episode_pnl).quantile(0.90)),
            "h2_eligible_rate": float(q.h2_eligible.mean()),
            "latent_target_rate": float(q.latent_target_recovered.mean()),
        })
    return pd.DataFrame(rows)


def snapshot_summary(snaps):
    features = [
        "close_R", "running_mfe_R", "running_mae_R", "closes_above_H", "closes_le_H", "close_minus_L_R"
    ]
    rows = []
    for (role, part, attempt, sm, ec), q in snaps.groupby(
        ["role", "partition", "attempt", "snapshot_min", "episode_class"], sort=False
    ):
        base = {
            "role": role, "partition": part, "attempt": attempt,
            "snapshot_min": sm, "episode_class": ec, "n": len(q),
            "break_confirmed_rate": float(q.break_confirmed_by_snapshot.mean()),
        }
        for f in features:
            x = pd.to_numeric(q[f], errors="coerce").dropna()
            base[f"{f}_q25"] = float(x.quantile(0.25)) if len(x) else np.nan
            base[f"{f}_q50"] = float(x.quantile(0.50)) if len(x) else np.nan
            base[f"{f}_q75"] = float(x.quantile(0.75)) if len(x) else np.nan
        rows.append(base)
    return pd.DataFrame(rows)


def separation(snaps):
    features = [
        "close_R", "running_mfe_R", "running_mae_R", "break_confirmed_by_snapshot",
        "closes_above_H", "closes_le_H", "close_minus_L_R",
    ]
    rows = []
    for (role, part, attempt, sm), q in snaps.groupby(["role", "partition", "attempt", "snapshot_min"], sort=False):
        true = q[q.episode_class == "RESIDUAL_TRUE_FAILURE_PROXY"]
        good = q[q.episode_class != "RESIDUAL_TRUE_FAILURE_PROXY"]
        if len(true) < 5 or len(good) < 5:
            continue
        for f in features:
            a = pd.to_numeric(good[f], errors="coerce").dropna().astype(float)
            b = pd.to_numeric(true[f], errors="coerce").dropna().astype(float)
            if len(a) < 5 or len(b) < 5:
                continue
            gmed = float(a.median())
            tmed = float(b.median())
            diff = gmed - tmed
            pooled = pd.concat([a, b], ignore_index=True)
            iqr = float(pooled.quantile(0.75) - pooled.quantile(0.25))
            scale = iqr if iqr > EPS else 1.0
            rows.append({
                "role": role, "partition": part, "attempt": attempt, "snapshot_min": sm,
                "feature": f, "good_n": len(a), "true_n": len(b),
                "good_median": gmed, "true_median": tmed,
                "good_minus_true": diff,
                "iqr_scaled_abs_gap": abs(diff) / scale,
            })
    return pd.DataFrame(rows)


def support_decision(damage, sep):
    cd = damage[(damage.role == "CENTRAL") & (damage.partition == "development")]
    if cd.empty:
        return False, "Central Development missing", pd.DataFrame()
    r = cd.iloc[0]
    if int(r.residual_n) <= 0:
        return False, "No residual losses", pd.DataFrame()
    if int(r.true_failure_proxy_n) < 40:
        return False, "True-failure proxy N < 40", pd.DataFrame()
    if float(r.true_failure_share_residual_loss) < 0.25:
        return False, "True-failure proxy <25% residual loss dollars", pd.DataFrame()

    dev = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].copy()
    ext = sep[(sep.role == "CENTRAL") & (sep.partition == "external")].copy()
    rv = sep[(sep.role == "CENTRAL") & (sep.partition == "reference_validation")].copy()
    keys = ["attempt", "snapshot_min", "feature"]
    z = dev.merge(ext[keys + ["good_minus_true"]], on=keys, how="left", suffixes=("_dev", "_ext"))
    z = z.merge(rv[keys + ["good_minus_true"]], on=keys, how="left")
    z = z.rename(columns={"good_minus_true": "good_minus_true_refval"})
    z["dev_sign"] = np.sign(z.good_minus_true_dev)
    z["ext_sign"] = np.sign(z.good_minus_true_ext)
    z["refval_sign"] = np.sign(z.good_minus_true_refval)
    z["nonzero_dev"] = z.dev_sign != 0
    z["both_oos_contradict"] = (
        z.good_minus_true_ext.notna() & z.good_minus_true_refval.notna()
        & (z.ext_sign == -z.dev_sign) & (z.refval_sign == -z.dev_sign)
    )
    eligible = z[z.nonzero_dev & ~z.both_oos_contradict].copy()
    if eligible.empty:
        return False, "No causal snapshot separation survives qualitative OOS direction check", z
    return True, "Residual true-failure damage is material and causal separation is visible", z


def main():
    parent, m, coverage = load_system()
    episodes, rec_by_key = build_episodes(parent, m)

    # Frozen parity: Central Development parent must remain A2.
    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")]
    if len(cd_parent) != 617:
        raise RuntimeError(f"Central Development parent N parity failed: {len(cd_parent)}")
    if abs(float(cd_parent.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("Central Development parent net parity failed")

    damage = damage_summary(episodes)
    classes = loss_class_summary(episodes)
    raw_snaps = build_snapshots(parent, episodes, rec_by_key, m)
    snaps = snapshot_summary(raw_snaps)
    sep = separation(raw_snaps)
    supported, reason, repl = support_decision(damage, sep)

    episodes.to_csv(OUT_EP, index=False)
    damage.to_csv(OUT_DAMAGE, index=False)
    classes.to_csv(OUT_CLASS, index=False)
    snaps.to_csv(OUT_SNAP, index=False)
    sep.to_csv(OUT_SEP, index=False)

    cd = damage[(damage.role == "CENTRAL") & (damage.partition == "development")].iloc[0]
    cdclasses = classes[(classes.role == "CENTRAL") & (classes.partition == "development")].sort_values("gross_loss", ascending=False)
    devsep = sep[(sep.role == "CENTRAL") & (sep.partition == "development")].sort_values("iqr_scaled_abs_gap", ascending=False)

    lines = [
        "# SOL LONG H1 Residual Failure — A5 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A5 is forensic only. Frozen A2 parent and frozen A4 `REC_H2` are unchanged.", "",
        "## Residual damage after H2 overlay", "",
        "| Role | Partition | Parent N | Parent losses | H2 eligible | H2 rescues | Residual N | Latent residual | True-failure proxy | Residual loss $ | True-failure share $ | Never-break share $ | Failed-break share $ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in damage.iterrows():
        lines.append(
            f"| {r.role} | {r.partition} | {int(r.parent_n)} | {int(r.parent_loss_n)} | {int(r.h2_eligible_n)} | {int(r.h2_rescue_n)} | {int(r.residual_n)} | {int(r.latent_residual_n)} | {int(r.true_failure_proxy_n)} | ${r.residual_gross_loss:.2f} | {fmt_pct(r.true_failure_share_residual_loss)} | {fmt_pct(r.never_break_share_residual_loss)} | {fmt_pct(r.failed_break_share_residual_loss)} |"
        )

    lines += [
        "", "## Central Development residual loss classes", "",
        "| Original loss class | Residual label | N | Gross loss $ | Median loss | Q90 loss | H2 eligible |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in cdclasses.iterrows():
        lines.append(
            f"| {r.loss_class} | {r.episode_class} | {int(r.n)} | ${r.gross_loss:.2f} | ${r.median_loss:.2f} | ${r.q90_loss:.2f} | {fmt_pct(r.h2_eligible_rate)} |"
        )

    lines += [
        "", "## Strongest Central Development causal separations (descriptive)", "",
        "Positive `good - true` means the non-true-failure group has the larger value; negative means the true-failure proxy has the larger value.", "",
        "| Attempt | Snapshot | Feature | Good N | True N | Good median | True median | Good-True | IQR-scaled gap |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in devsep.head(18).iterrows():
        lines.append(
            f"| {r.attempt} | +{int(r.snapshot_min)}m | {r.feature} | {int(r.good_n)} | {int(r.true_n)} | {fmt_num(r.good_median,3)} | {fmt_num(r.true_median,3)} | {fmt_num(r.good_minus_true,3)} | {fmt_num(r.iqr_scaled_abs_gap,2)} |"
        )

    lines += [
        "", "## A5 decision", "",
        f"- Central Development residual N: **{int(cd.residual_n)}**.",
        f"- True-failure proxy N: **{int(cd.true_failure_proxy_n)}**.",
        f"- True-failure proxy share of residual gross-loss dollars: **{fmt_pct(cd.true_failure_share_residual_loss)}**.",
        f"- Decision reason: **{reason}**.", "",
        f"**Status: {'SOL_LONG_H1_RESIDUAL_FAILURE_A5_SUPPORTED_FOR_A6' if supported else 'SOL_LONG_H1_RESIDUAL_FAILURE_A5_INCONCLUSIVE'}**", "",
        "A5 does not authorize a trading change. If supported, A6 must preregister a small early-invalidation family using Development quantiles only, then freeze it before OOS evaluation.", "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(
        ("SOL_LONG_H1_RESIDUAL_FAILURE_A5_SUPPORTED_FOR_A6" if supported else "SOL_LONG_H1_RESIDUAL_FAILURE_A5_INCONCLUSIVE") + "\n",
        encoding="utf-8",
    )

    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
