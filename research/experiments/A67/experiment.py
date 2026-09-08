#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

BAR = pd.Timedelta(minutes=5)
PARTS = ("development", "external", "reference_validation")
SHOW = {"development": "Development", "external": "External Validation", "reference_validation": "Reference Validation"}
PARENT = {"development": 601, "external": 281, "reference_validation": 337}
LOSSES = {"development": 357, "external": 166, "reference_validation": 187}
L0 = {"development": 37, "external": 13, "reference_validation": 26}
WINNERS = {"development": 244, "external": 115, "reference_validation": 150}
AGES = (60, 120)
EPS = 1e-12
DIR = {
    "largest_mae_extension_share": "lower",
    "mae_extension_bar_fraction": "higher",
    "down_close_step_fraction": "higher",
    "close_path_efficiency_to_worst": "higher",
    "worst_bar_close_location": "lower",
}


def load_a66(root: Path):
    p = root / "research" / "experiments" / "A66" / "experiment.py"
    s = importlib.util.spec_from_file_location("a67_a66", p)
    m = importlib.util.module_from_spec(s)
    assert s.loader is not None
    s.loader.exec_module(m)
    return m


def formation_features(market, r, age, a66):
    idx = market["idx"]
    s = a66.startbar(r.entry_ts)
    t = a66.lastbar(r.entry_ts, age)
    a = a66.pos(idx, s)
    b = a66.pos(idx, t)

    lo_full = np.asarray(market["low"][a:b + 1], float)
    hi_full = np.asarray(market["high"][a:b + 1], float)
    cl_full = np.asarray(market["close"][a:b + 1], float)
    H, R = float(r.H), float(r.R)
    if R <= 0 or len(lo_full) == 0 or len(hi_full) != len(lo_full) or len(cl_full) != len(lo_full):
        raise RuntimeError(f"bad A67 path geometry {r.entry_ts} age={age}")

    worst_i = int(np.argmin(lo_full))
    worst_low = float(lo_full[worst_i])
    adverse_depth = max(0.0, H - worst_low)
    mae = adverse_depth / R

    lo = lo_full[:worst_i + 1]
    hi = hi_full[:worst_i + 1]
    cl = cl_full[:worst_i + 1]
    n = len(lo)
    if n == 0:
        raise RuntimeError(f"empty A67 formation window {r.entry_ts} age={age}")

    running_min = np.minimum.accumulate(lo)
    running_depth = np.maximum(0.0, H - running_min)
    extensions = np.diff(np.concatenate(([0.0], running_depth)))
    extensions = np.maximum(0.0, extensions)

    if adverse_depth > EPS:
        largest_extension_share = float(np.max(extensions) / adverse_depth)
    else:
        largest_extension_share = 0.0
    extension_bar_fraction = float(np.mean(extensions > EPS))

    close_path = np.concatenate(([H], cl))
    close_steps = np.diff(close_path)
    down_close_fraction = float(np.mean(close_steps < -EPS)) if len(close_steps) else 0.0
    total_close_path = float(np.sum(np.abs(close_steps)))
    close_efficiency = max(0.0, H - float(cl[-1])) / total_close_path if total_close_path > EPS else 0.0

    worst_range = float(hi[-1] - lo[-1])
    close_location = (float(cl[-1]) - float(lo[-1])) / worst_range if worst_range > EPS else 0.5
    close_location = float(np.clip(close_location, 0.0, 1.0))

    f = {
        "running_mae_R": mae,
        "largest_mae_extension_share": largest_extension_share,
        "mae_extension_bar_fraction": extension_bar_fraction,
        "down_close_step_fraction": down_close_fraction,
        "close_path_efficiency_to_worst": close_efficiency,
        "worst_bar_close_location": close_location,
    }
    if not all(np.isfinite(v) for v in f.values()):
        raise RuntimeError(f"nonfinite A67 feature at {r.entry_ts} age={age}")

    anchor_ts = idx[a + worst_i]
    return s, t, anchor_ts, f


def choose_control(pool, case, case_f, age, market, a66):
    idx = market["idx"]
    candidates = []
    for _, w in pool.iterrows():
        if case.partition == "development":
            cb = pd.to_numeric(pd.Series([case.dev_block]), errors="coerce").iloc[0]
            wb = pd.to_numeric(pd.Series([w.dev_block]), errors="coerce").iloc[0]
            if pd.isna(cb) or pd.isna(wb) or int(cb) != int(wb):
                continue
        t = a66.lastbar(w.entry_ts, age)
        try:
            a66.pos(idx, a66.startbar(w.entry_ts))
            a66.pos(idx, t)
        except RuntimeError:
            continue
        if not a66.eligible_winner(w, t):
            continue
        _, _, anchor, wf = formation_features(market, w, age, a66)
        mae_gap = abs(float(wf["running_mae_R"]) - float(case_f["running_mae_R"]))
        calendar_gap = abs((pd.Timestamp(w.execution_start) - pd.Timestamp(case.execution_start)).total_seconds())
        candidates.append((mae_gap, calendar_gap, pd.Timestamp(w.execution_start), pd.Timestamp(w.entry_ts), w, anchor, wf))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return candidates[0][4], candidates[0][5], candidates[0][6], float(candidates[0][0])


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a66 = load_a66(root)
    a65 = a66.load_a65(root)
    a55 = a65.load_a55(root)
    x, cov = a55.a2.a1.load5()
    market = a55.a2.make_market_with_open(x)
    idx = market["idx"]
    parents = {p: a55.parent(market, p) for p in PARTS}

    recon_rows = []
    errors = []
    for p, q in parents.items():
        parent_n = len(q)
        loss_n = int((~q.economic_win).sum())
        l0_n = int((q.mechanism == "M0_REFERENCE_INVALIDATION").sum())
        winner_n = int(q.economic_win.sum())
        recon_rows.append(dict(partition=p, parent_n=parent_n, loss_n=loss_n, l0_n=l0_n, winner_n=winner_n))
        if parent_n != PARENT[p]: errors.append(f"{p} parent {parent_n}!={PARENT[p]}")
        if loss_n != LOSSES[p]: errors.append(f"{p} losses {loss_n}!={LOSSES[p]}")
        if l0_n != L0[p]: errors.append(f"{p} L0 {l0_n}!={L0[p]}")
        if winner_n != WINNERS[p]: errors.append(f"{p} winners {winner_n}!={WINNERS[p]}")
    if errors:
        raise RuntimeError("; ".join(errors))
    recon = pd.DataFrame(recon_rows)

    rows = []
    coverage_rows = []
    for p, q in parents.items():
        cases = q[q.mechanism == "M0_REFERENCE_INVALIDATION"]
        controls = q[q.economic_win]
        for age in AGES:
            eligible = matched = 0
            used, mae_gaps = [], []
            for _, r in cases.iterrows():
                t = a66.lastbar(r.entry_ts, age)
                a66.pos(idx, a66.startbar(r.entry_ts))
                a66.pos(idx, t)
                if not a66.eligible_l0(r, t):
                    continue
                eligible += 1
                cs, ct, ca, cf = formation_features(market, r, age, a66)
                chosen = choose_control(controls, r, cf, age, market, a66)
                if chosen is None:
                    continue
                w, wa, wf, mae_gap = chosen
                ws, wt, wa_check, _ = formation_features(market, w, age, a66)
                if pd.Timestamp(wa) != pd.Timestamp(wa_check):
                    raise RuntimeError(f"A67 control anchor mismatch {w.entry_ts} age={age}")
                matched += 1
                used.append(str(pd.Timestamp(w.entry_ts)))
                mae_gaps.append(mae_gap)
                z = {
                    "partition": p, "snapshot_age_min": age,
                    "case_entry_ts": r.entry_ts, "case_execution_start": r.execution_start, "case_dev_block": r.dev_block,
                    "case_exit_ts": r.exit_ts, "case_invalidation_close_ts": r.invalidation_close_ts,
                    "case_measurement_start_ts": cs, "case_last_completed_bar_ts": ct, "case_formation_anchor_ts": ca, "case_pnl": float(r.pnl),
                    "control_entry_ts": w.entry_ts, "control_execution_start": w.execution_start, "control_dev_block": w.dev_block,
                    "control_exit_ts": w.exit_ts, "control_break_ts": w.h1_break_ts, "control_invalidation_close_ts": w.invalidation_close_ts,
                    "control_measurement_start_ts": ws, "control_last_completed_bar_ts": wt, "control_formation_anchor_ts": wa, "control_pnl": float(w.pnl),
                    "case__running_mae_R": cf["running_mae_R"], "control__running_mae_R": wf["running_mae_R"],
                    "abs_running_mae_R_match_gap": mae_gap,
                }
                for f in DIR:
                    z[f"case__{f}"] = cf[f]
                    z[f"control__{f}"] = wf[f]
                rows.append(z)
            counter = Counter(used)
            gaps = pd.Series(mae_gaps, dtype=float)
            coverage_rows.append(dict(
                partition=p, snapshot_age_min=age, l0_total=len(cases), winner_total=len(controls), eligible_l0_n=eligible,
                matched_n=matched, match_rate=matched / eligible if eligible else np.nan, unique_control_n=len(counter),
                reused_match_n=sum(max(0, v - 1) for v in counter.values()), max_control_reuse=max(counter.values()) if counter else 0,
                median_abs_mae_gap=float(gaps.median()) if len(gaps) else np.nan,
                p75_abs_mae_gap=float(gaps.quantile(0.75)) if len(gaps) else np.nan,
                max_abs_mae_gap=float(gaps.max()) if len(gaps) else np.nan,
            ))

    events = pd.DataFrame(rows)
    coverage = pd.DataFrame(coverage_rows)
    if events.empty or events.duplicated(["partition", "snapshot_age_min", "case_entry_ts"]).any():
        raise RuntimeError("empty or duplicate A67 events")

    blocks = []
    for age in AGES:
        for f, direction in DIR.items():
            for block_i in range(6):
                q = events[(events.partition == "development") & (events.snapshot_age_min == age) & (pd.to_numeric(events.case_dev_block, errors="coerce") == block_i)]
                s = a66.stat(q, f)
                adequate = s["n"] >= 5
                blocks.append(dict(snapshot_age_min=age, feature=f, direction=direction, dev_block=block_i, **s,
                                   adequate=adequate, direction_ok=adequate and a66.direction_ok(s["median_gap"], direction)))
    blocks = pd.DataFrame(blocks)

    metrics = []
    for p in PARTS:
        for age in AGES:
            for f, direction in DIR.items():
                s = a66.stat(events[(events.partition == p) & (events.snapshot_age_min == age)], f)
                adequate_blocks = same_direction_blocks = 0
                block_pass = False
                if p == "development":
                    b = blocks[(blocks.snapshot_age_min == age) & (blocks.feature == f)]
                    aa = b[b.adequate]
                    adequate_blocks = len(aa)
                    same_direction_blocks = int(aa.direction_ok.sum())
                    block_pass = adequate_blocks >= 3 and same_direction_blocks == adequate_blocks
                metrics.append(dict(partition=p, snapshot_age_min=age, feature=f, direction=direction, **s,
                                    direction_ok=a66.direction_ok(s["median_gap"], direction), adequate_dev_blocks=adequate_blocks,
                                    same_direction_dev_blocks=same_direction_blocks, dev_block_rule_pass=block_pass))
    metrics = pd.DataFrame(metrics)
    metrics["development_eligible"] = False
    metrics["oos_replication_pass"] = False
    metrics["full_snapshot_replication"] = False

    replicated = {f: [] for f in DIR}
    for age in AGES:
        for f in DIR:
            dm = (metrics.partition == "development") & (metrics.snapshot_age_min == age) & (metrics.feature == f)
            d = metrics[dm].iloc[0]
            dev_pass = bool(d.n >= 20 and d.direction_ok and d.effect >= 0.30 - EPS and d.dev_block_rule_pass)
            metrics.loc[dm, "development_eligible"] = dev_pass
            oos = []
            for p in ("external", "reference_validation"):
                mm = (metrics.partition == p) & (metrics.snapshot_age_min == age) & (metrics.feature == f)
                rr = metrics[mm].iloc[0]
                ok = bool(dev_pass and rr.n >= 8 and rr.direction_ok and rr.effect >= 0.10 - EPS)
                metrics.loc[mm, "oos_replication_pass"] = ok
                oos.append(ok)
            full = dev_pass and all(oos)
            metrics.loc[(metrics.snapshot_age_min == age) & (metrics.feature == f), "full_snapshot_replication"] = full
            if full:
                replicated[f].append(age)

    supported = [f for f, ages in replicated.items() if ages == [60, 120]]
    status = "SOL_LONG_15UTC_L0_MAE_FORMATION_DOWNSIDE_ACCEPTANCE_A67_SUPPORTED" if supported else "SOL_LONG_15UTC_L0_MAE_FORMATION_DOWNSIDE_ACCEPTANCE_A67_INCONCLUSIVE"

    prefix = "SOL_LONG_15UTC_L0_MAE_FORMATION_DOWNSIDE_ACCEPTANCE_A67"
    artifacts = []
    for name, df in {"EVENTS": events, "COVERAGE": coverage, "METRICS": metrics, "BLOCKS": blocks, "RECONCILIATION": recon}.items():
        p = out / f"{prefix}_{name}.csv"
        df.to_csv(p, index=False)
        artifacts.append(p)
    status_path = out / f"{prefix}_Status.txt"
    status_path.write_text(status + "\n")
    artifacts.append(status_path)

    fmt = lambda v: "-" if pd.isna(v) else ("inf" if np.isinf(v) else f"{float(v):.3f}")
    result_path = out / f"{prefix}_Result.md"
    lines = [
        "# SOL LONG 15:00 UTC L0 MAE Formation and Downside-Acceptance Anatomy — A67 Result", "",
        f"**Gate status: {status}**", "", f"Raw SOLUSDT 5m coverage: **{100 * cov:.4f}%**.", "",
        "A67 conditions L0-vs-winner comparison on nearest running_mae_R severity at the same fixed age, then measures only the pre-worst formation path through the first snapshot-worst bar. No post-worst recovery/reclaim information is used. It is descriptive/mechanistic only; live Baba Bot is unchanged.", "",
        "## Reconciliation", "", "| Partition | Parent | Losses | L0/M0 | Winners |", "|---|---:|---:|---:|---:|"
    ]
    for _, r in recon.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.winner_n)} |")
    lines += ["", "## MAE-conditioned matching", "", "| Partition | Age | Eligible L0 | Matched | Unique winners | Max reuse | Median |ΔMAE| | P75 |ΔMAE| | Max |ΔMAE| |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in coverage.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.snapshot_age_min)}m | {int(r.eligible_l0_n)} | {int(r.matched_n)} | {int(r.unique_control_n)} | {int(r.max_control_reuse)}x | {fmt(r.median_abs_mae_gap)}R | {fmt(r.p75_abs_mae_gap)}R | {fmt(r.max_abs_mae_gap)}R |")
    lines += ["", "## Formation/downside-acceptance replication", "", "| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |", "|---:|---|---:|---:|---:|---:|---|"]
    for age in AGES:
        for f in DIR:
            d = metrics[(metrics.partition == "development") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            e = metrics[(metrics.partition == "external") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            rr = metrics[(metrics.partition == "reference_validation") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            lines.append(f"| {age}m | {f} | {fmt(d.median_gap)}/{fmt(d.effect)} | {int(d.same_direction_dev_blocks)}/{int(d.adequate_dev_blocks)} | {fmt(e.median_gap)}/{fmt(e.effect)} | {fmt(rr.median_gap)}/{fmt(rr.effect)} | {'YES' if d.full_snapshot_replication else 'NO'} |")
    lines += ["", "## Strict 2-of-2 family rule", ""]
    for f in DIR:
        ages = replicated[f]
        lines.append(f"- `{f}`: {ages if ages else 'none'} -> **{'SUPPORTED' if ages == [60, 120] else 'NO'}**")
    lines += ["", f"Supported formation/downside-acceptance feature families: **{', '.join(supported) if supported else 'none'}**.", "",
              "Interpretation boundary: A67 is MAE-conditioned pre-worst formation anatomy only. It does not authorize a threshold, composite, gate, exit, partial derisk, re-arm, or live intervention.", "", "Research only. Live Baba Bot remains unchanged."]
    result_path.write_text("\n".join(lines) + "\n")
    artifacts.append(result_path)

    observed = {
        "execution_parent": {"range": "R360", "hour": "15UTC", "entry": "E0_RESTING_H", "target": "E40"},
        "central_losses_total": 710,
        "l0_total": 76,
        "partitions": {
            "Development": {"central_losses": 357, "l0": 37},
            "External Validation": {"central_losses": 166, "l0": 13},
            "Reference Validation": {"central_losses": 187, "l0": 26}
        }
    }
    summary = {
        "gate_status": status,
        "market_coverage": float(cov),
        "supported_formation_feature_families": supported,
        "replicated_snapshots_by_feature": replicated,
        "matched_pairs_by_partition_snapshot": {f"{r.partition}:{int(r.snapshot_age_min)}m": int(r.matched_n) for _, r in coverage.iterrows()},
        "median_abs_mae_match_gap_by_partition_snapshot": {f"{r.partition}:{int(r.snapshot_age_min)}m": float(r.median_abs_mae_gap) for _, r in coverage.iterrows()},
        "interpretation_boundary": "mae_conditioned_pre_worst_formation_anatomy_only_no_intervention"
    }
    return {"observed": observed, "summary": summary, "artifacts": [p.relative_to(root).as_posix() for p in artifacts]}
