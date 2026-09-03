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

IN_PARENT = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_Result.md"
OUT_TAX = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_TAXONOMY.csv"
OUT_SNAP = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_SNAPSHOTS.csv"
OUT_TRADES = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_Status.txt"

SNAP_MINS = (5, 10, 15, 30)
EPS = 1e-12


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    return np.inf if gl == 0 and gp > 0 else (gp / gl if gl > 0 else np.nan)


def loss_class(r):
    if float(r.pnl) > 0:
        return "WIN"
    confirmed = pd.notna(r.h1_break_ts)
    if not confirmed:
        if str(r.exit_reason) == "REFERENCE_INVALIDATION":
            return "L0_NEVER_BREAK_REFERENCE_INVALIDATION"
        return "L1_NEVER_BREAK_TIME"
    if pd.notna(r.invalidation_close_ts):
        d = (pd.Timestamp(r.invalidation_close_ts) - pd.Timestamp(r.h1_break_ts)) / pd.Timedelta(minutes=1)
        if d <= 5 + EPS:
            return "L2_BREAK_FAST_FAIL_5M"
        if d <= 10 + EPS:
            return "L3_BREAK_FAST_FAIL_10M"
        if d <= 30 + EPS:
            return "L4_BREAK_FAIL_30M"
        return "L5_BREAK_FAIL_LATE"
    return "L6_BREAK_TIME_OR_OTHER"


def mfe_band(x):
    if pd.isna(x):
        return "NA"
    x = float(x)
    if x < 0.05:
        return "M0_<0.05R"
    if x < 0.10:
        return "M1_0.05-<0.10R"
    if x < 0.20:
        return "M2_0.10-<0.20R"
    if x < 0.40:
        return "M3_0.20-<0.40R"
    return "M4_>=0.40R"


def load_parent():
    t = pd.read_csv(IN_PARENT)
    for c in ["execution_start", "h1_ts", "h1_break_ts", "entry_ts", "exit_ts", "invalidation_close_ts"]:
        t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    q = t[(t.family == "E0_RESTING_H") & (np.isclose(pd.to_numeric(t.target_R, errors="coerce"), 0.40))].copy()
    if "candidate_scope" in q.columns:
        q = q[q.candidate_scope == "FROZEN_WINNER"].copy()
    if q.empty:
        raise RuntimeError("Frozen A2 E0_RESTING_H/E40 parent trades not found")
    return q.sort_values(["role", "partition", "entry_ts"]).reset_index(drop=True)


def add_path_features(t, m):
    idx = m["idx"]
    hi = m["high"]
    lo = m["low"]
    cl = m["close"]
    rows = []
    snaps = []
    for _, r0 in t.iterrows():
        r = r0.to_dict()
        ei = int(idx.searchsorted(pd.Timestamp(r0.entry_ts), "left"))
        xi = int(idx.searchsorted(pd.Timestamp(r0.exit_ts), "left"))
        if ei >= len(idx) or xi >= len(idx) or idx[ei] != r0.entry_ts or idx[xi] != r0.exit_ts:
            raise RuntimeError(f"Timestamp parity failure for {r0.entry_ts}")
        if xi < ei:
            raise RuntimeError("exit before entry")
        H = float(r0.H); R = float(r0.R)
        if R <= 0:
            raise RuntimeError("nonpositive R")
        path_hi = hi[ei:xi+1]
        path_lo = lo[ei:xi+1]
        mfe = max(0.0, (float(np.max(path_hi)) - H) / R) if len(path_hi) else np.nan
        mae = max(0.0, (H - float(np.min(path_lo))) / R) if len(path_lo) else np.nan
        entry_delay = (pd.Timestamp(r0.entry_ts) - pd.Timestamp(r0.execution_start)) / pd.Timedelta(minutes=1)
        break_delay = ((pd.Timestamp(r0.h1_break_ts) - pd.Timestamp(r0.entry_ts)) / pd.Timedelta(minutes=1)) if pd.notna(r0.h1_break_ts) else np.nan
        fail_delay = ((pd.Timestamp(r0.invalidation_close_ts) - pd.Timestamp(r0.h1_break_ts)) / pd.Timedelta(minutes=1)) if pd.notna(r0.h1_break_ts) and pd.notna(r0.invalidation_close_ts) else np.nan
        hold_min = (pd.Timestamp(r0.exit_ts) - pd.Timestamp(r0.entry_ts)) / pd.Timedelta(minutes=1)
        lc = loss_class(r0)
        r.update({
            "loss_class": lc,
            "mfe_R": mfe,
            "mae_R": mae,
            "mfe_band": mfe_band(mfe) if lc != "WIN" else "WIN",
            "exec_to_entry_min": float(entry_delay),
            "entry_to_break_min": float(break_delay) if pd.notna(break_delay) else np.nan,
            "break_to_fail_min": float(fail_delay) if pd.notna(fail_delay) else np.nan,
            "hold_min": float(hold_min),
        })
        rows.append(r)

        for sm in SNAP_MINS:
            # Entry timestamp is the opening time of the H1 bar. +5m snapshot means close of that entry bar.
            si = ei + (sm // 5) - 1
            if si >= len(idx) or si > xi:
                continue
            seg_hi = hi[ei:si+1]
            seg_lo = lo[ei:si+1]
            seg_cl = cl[ei:si+1]
            snap_close_R = (float(cl[si]) - H) / R
            run_mfe = max(0.0, (float(np.max(seg_hi)) - H) / R)
            run_mae = max(0.0, (H - float(np.min(seg_lo))) / R)
            close_gt = np.asarray(seg_cl, dtype=float) > H
            snaps.append({
                "role": r0.role,
                "partition": r0.partition,
                "execution_start": r0.execution_start,
                "entry_ts": r0.entry_ts,
                "snapshot_min": sm,
                "outcome": "WIN" if float(r0.pnl) > 0 else "LOSS",
                "loss_class": lc,
                "pnl": float(r0.pnl),
                "close_R": snap_close_R,
                "running_mfe_R": run_mfe,
                "running_mae_R": run_mae,
                "break_confirmed_by_snapshot": bool(close_gt.any()),
                "closes_above_H": int(close_gt.sum()),
            })
    return pd.DataFrame(rows), pd.DataFrame(snaps)


def group_summary(t):
    rows = []
    for (role, part), q in t.groupby(["role", "partition"], sort=False):
        gp = float(q.loc[q.pnl > 0, "pnl"].sum())
        gl = float(-q.loc[q.pnl <= 0, "pnl"].sum())
        rows.append({
            "role": role, "partition": part, "n": len(q),
            "win_n": int((q.pnl > 0).sum()), "loss_n": int((q.pnl <= 0).sum()),
            "gross_profit": gp, "gross_loss": gl, "pf": pf(q.pnl),
            "net": float(q.pnl.sum()),
        })
    return pd.DataFrame(rows)


def taxonomy(t):
    rows = []
    for (role, part), q in t.groupby(["role", "partition"], sort=False):
        losses = q[q.pnl <= 0].copy()
        gross_loss = float(-losses.pnl.sum())
        nloss = len(losses)
        for lc, z in losses.groupby("loss_class"):
            loss_dollars = float(-z.pnl.sum())
            rows.append({
                "role": role, "partition": part, "loss_class": lc,
                "n": len(z), "share_losers": len(z)/nloss if nloss else np.nan,
                "gross_loss_dollars": loss_dollars,
                "share_gross_loss": loss_dollars/gross_loss if gross_loss > 0 else np.nan,
                "mean_loss_dollars": float((-z.pnl).mean()),
                "median_loss_dollars": float((-z.pnl).median()),
                "median_mfe_R": float(z.mfe_R.median()),
                "median_mae_R": float(z.mae_R.median()),
                "median_hold_min": float(z.hold_min.median()),
                "median_entry_to_break_min": float(z.entry_to_break_min.median()) if z.entry_to_break_min.notna().any() else np.nan,
                "median_break_to_fail_min": float(z.break_to_fail_min.median()) if z.break_to_fail_min.notna().any() else np.nan,
            })
    return pd.DataFrame(rows)


def snapshot_summary(s):
    rows = []
    for (role, part, sm, outcome), q in s.groupby(["role", "partition", "snapshot_min", "outcome"], sort=False):
        rows.append({
            "role": role, "partition": part, "snapshot_min": sm, "outcome": outcome, "n": len(q),
            "median_close_R": float(q.close_R.median()),
            "median_running_mfe_R": float(q.running_mfe_R.median()),
            "median_running_mae_R": float(q.running_mae_R.median()),
            "break_confirmed_rate": float(q.break_confirmed_by_snapshot.mean()),
            "median_closes_above_H": float(q.closes_above_H.median()),
        })
    return pd.DataFrame(rows)


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def fmt_num(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def main():
    parent = load_parent()
    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)
    t, snaps = add_path_features(parent, m)

    # Parent parity against persisted A2 outcomes.
    central_dev = t[(t.role == "CENTRAL") & (t.partition == "development")]
    if len(central_dev) != 617:
        raise RuntimeError(f"A2 central Development N parity failed: {len(central_dev)}")
    if abs(float(central_dev.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("A2 central Development net parity failed")

    gs = group_summary(t)
    tax = taxonomy(t)
    ss = snapshot_summary(snaps)
    t.to_csv(OUT_TRADES, index=False)
    tax.to_csv(OUT_TAX, index=False)
    snaps.to_csv(OUT_SNAP, index=False)

    cd = central_dev.copy()
    cdl = cd[cd.pnl <= 0].copy()
    cd_tax = tax[(tax.role == "CENTRAL") & (tax.partition == "development")].sort_values("share_gross_loss", ascending=False)
    max_loss = float(-cdl.pnl.min()) if len(cdl) else np.nan
    top10 = cdl.nsmallest(10, "pnl")
    top10_counts = top10.loss_class.value_counts().to_dict()

    lines = [
        "# SOL LONG H1 Loss Anatomy — A3 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A3 is forensic only: frozen A2 `E0_RESTING_H -> E40` trades are not filtered, rescored, or altered.", "",
        "## Parent parity / overall economics", "",
        "| Role | Partition | N | Wins | Losses | PF | Gross profit | Gross loss | Net |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in gs.iterrows():
        lines.append(f"| {r.role} | {r.partition} | {int(r.n)} | {int(r.win_n)} | {int(r.loss_n)} | {fmt_num(r.pf)} | ${r.gross_profit:.2f} | ${r.gross_loss:.2f} | ${r.net:.2f} |")

    lines += ["", "## Central Development loss taxonomy", "",
              "| Loss class | N | Share losers | Gross-loss $ | Share gross loss | Median loss | Median MFE | Median MAE | Median hold |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in cd_tax.iterrows():
        lines.append(f"| {r.loss_class} | {int(r.n)} | {fmt_pct(r.share_losers)} | ${r.gross_loss_dollars:.2f} | {fmt_pct(r.share_gross_loss)} | ${r.median_loss_dollars:.2f} | {r.median_mfe_R:.3f}R | {r.median_mae_R:.3f}R | {r.median_hold_min:.0f}m |")

    lines += ["", "## Central Development fixed causal snapshots", "",
              "| Snapshot | Outcome | N observable | Median close vs H | Median running MFE | Median running MAE | Break confirmed | Median closes >H |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    z = ss[(ss.role == "CENTRAL") & (ss.partition == "development")].sort_values(["snapshot_min", "outcome"])
    for _, r in z.iterrows():
        lines.append(f"| +{int(r.snapshot_min)}m | {r.outcome} | {int(r.n)} | {r.median_close_R:.3f}R | {r.median_running_mfe_R:.3f}R | {r.median_running_mae_R:.3f}R | {fmt_pct(r.break_confirmed_rate)} | {r.median_closes_above_H:.1f} |")

    lines += ["", "## OOS replication of loss classes", "",
              "| Role | Partition | Dominant gross-loss class | Share gross loss | Never-break gross-loss share | <=30m failed-break gross-loss share |",
              "|---|---|---|---:|---:|---:|"]
    for (role, part), q in tax.groupby(["role", "partition"], sort=False):
        dom = q.sort_values("share_gross_loss", ascending=False).iloc[0]
        never = q[q.loss_class.isin(["L0_NEVER_BREAK_REFERENCE_INVALIDATION", "L1_NEVER_BREAK_TIME"])].gross_loss_dollars.sum()
        fast = q[q.loss_class.isin(["L2_BREAK_FAST_FAIL_5M", "L3_BREAK_FAST_FAIL_10M", "L4_BREAK_FAIL_30M"])].gross_loss_dollars.sum()
        total = q.gross_loss_dollars.sum()
        lines.append(f"| {role} | {part} | {dom.loss_class} | {fmt_pct(dom.share_gross_loss)} | {fmt_pct(never/total if total else np.nan)} | {fmt_pct(fast/total if total else np.nan)} |")

    lines += ["", "## Tail damage", "", f"- Central Development maximum single loss: **${max_loss:.2f}**.",
              f"- Central Development top-10 worst-loss class composition: **{top10_counts}**.", "",
              "## Decision", ""]

    never_cd = cd_tax[cd_tax.loss_class.isin(["L0_NEVER_BREAK_REFERENCE_INVALIDATION", "L1_NEVER_BREAK_TIME"])].gross_loss_dollars.sum()
    fast_cd = cd_tax[cd_tax.loss_class.isin(["L2_BREAK_FAST_FAIL_5M", "L3_BREAK_FAST_FAIL_10M", "L4_BREAK_FAIL_30M"])].gross_loss_dollars.sum()
    total_cd = cd_tax.gross_loss_dollars.sum()
    dom_cd = cd_tax.iloc[0] if len(cd_tax) else None
    status = "SOL_LONG_H1_LOSS_ANATOMY_A3_COMPLETED"
    lines += [f"**Status: {status}**", "",
              f"Central Development never-break classes contribute **{fmt_pct(never_cd/total_cd if total_cd else np.nan)}** of gross loss; confirmed-break failures within 30m contribute **{fmt_pct(fast_cd/total_cd if total_cd else np.nan)}**.",
              (f"Largest Central Development gross-loss class: **{dom_cd.loss_class} ({fmt_pct(dom_cd.share_gross_loss)})**." if dom_cd is not None else "No losses."),
              "", "A3 does not authorize a filter or stop change. Any intervention must be separately preregistered and judged on preserved winners plus actual PF/expectancy under OOS and stress.", "", "Research only. Live Baba Bot remains unchanged."]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
