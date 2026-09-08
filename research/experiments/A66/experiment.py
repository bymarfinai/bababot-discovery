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
    "max_reclaim_fraction_of_mae": "lower",
    "half_reclaim_latency_fraction": "higher",
    "longest_half_reclaim_run_fraction": "lower",
    "post_half_reclaim_hold_fraction": "lower",
    "late_mae_extension_fraction": "higher",
}


def load_a65(root: Path):
    p = root / "research" / "experiments" / "A65" / "experiment.py"
    s = importlib.util.spec_from_file_location("a66_a65", p)
    m = importlib.util.module_from_spec(s)
    assert s.loader is not None
    s.loader.exec_module(m)
    return m


def pos(idx, t):
    t = pd.Timestamp(t)
    i = int(idx.searchsorted(t, "left"))
    if i >= len(idx) or idx[i] != t:
        raise RuntimeError(f"timestamp parity failure {t}")
    return i


def startbar(entry):
    return pd.Timestamp(entry) + BAR


def lastbar(entry, age):
    return pd.Timestamp(entry) + pd.Timedelta(minutes=age) - BAR


def eligible_l0(r, t):
    return bool(r.mechanism == "M0_REFERENCE_INVALIDATION" and pd.notna(r.invalidation_close_ts) and pd.isna(r.h1_break_ts) and pd.Timestamp(r.invalidation_close_ts) > t and pd.Timestamp(r.exit_ts) > t)


def eligible_winner(r, t):
    return bool(bool(r.economic_win) and pd.Timestamp(r.exit_ts) > t and (pd.isna(r.h1_break_ts) or pd.Timestamp(r.h1_break_ts) > t) and (pd.isna(r.invalidation_close_ts) or pd.Timestamp(r.invalidation_close_ts) > t))


def longest_true_run(mask: np.ndarray) -> int:
    best = cur = 0
    for v in mask:
        if bool(v):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def sequence_features(market, r, age):
    idx = market["idx"]
    s = startbar(r.entry_ts)
    t = lastbar(r.entry_ts, age)
    a = pos(idx, s)
    b = pos(idx, t)
    lo = np.asarray(market["low"][a:b + 1], float)
    cl = np.asarray(market["close"][a:b + 1], float)
    H, R = float(r.H), float(r.R)
    if R <= 0 or len(lo) == 0 or len(cl) != len(lo):
        raise RuntimeError(f"bad path geometry {r.entry_ts} age={age}")

    worst_i = int(np.argmin(lo))
    worst_low = float(lo[worst_i])
    adverse_depth = max(0.0, H - worst_low)
    mae = adverse_depth / R
    post_cl = cl[worst_i:]

    if adverse_depth <= EPS:
        max_reclaim_fraction = 0.0
        latency = 1.0
        longest_run_fraction = 0.0
        hold_fraction = 0.0
    else:
        half_level = worst_low + 0.50 * adverse_depth
        max_reclaim_fraction = max(0.0, float(np.max(post_cl)) - worst_low) / adverse_depth
        above = post_cl >= half_level
        hit = np.flatnonzero(above)
        if len(hit) == 0:
            latency = 1.0
            hold_fraction = 0.0
        else:
            first_hit = int(hit[0])
            latency = float(first_hit / max(1, len(post_cl) - 1))
            hold_fraction = float(np.mean(above[first_hit:]))
        longest_run_fraction = float(longest_true_run(above) / max(1, len(post_cl)))

    midpoint_last = lastbar(r.entry_ts, age // 2)
    mb = pos(idx, midpoint_last)
    if mb < a or mb > b:
        raise RuntimeError(f"bad midpoint geometry {r.entry_ts} age={age}")
    mid_lo = np.asarray(market["low"][a:mb + 1], float)
    midpoint_mae = max(0.0, (H - float(np.min(mid_lo))) / R)
    late_extension = max(0.0, mae - midpoint_mae) / max(mae, EPS) if mae > EPS else 0.0

    f = {
        "running_mae_R": mae,
        "max_reclaim_fraction_of_mae": max_reclaim_fraction,
        "half_reclaim_latency_fraction": latency,
        "longest_half_reclaim_run_fraction": longest_run_fraction,
        "post_half_reclaim_hold_fraction": hold_fraction,
        "late_mae_extension_fraction": late_extension,
    }
    if not all(np.isfinite(v) for v in f.values()):
        raise RuntimeError(f"nonfinite A66 feature at {r.entry_ts} age={age}")
    return s, t, f


def choose_control(pool, case, case_f, age, market):
    idx = market["idx"]
    candidates = []
    for _, w in pool.iterrows():
        if case.partition == "development":
            cb = pd.to_numeric(pd.Series([case.dev_block]), errors="coerce").iloc[0]
            wb = pd.to_numeric(pd.Series([w.dev_block]), errors="coerce").iloc[0]
            if pd.isna(cb) or pd.isna(wb) or int(cb) != int(wb):
                continue
        t = lastbar(w.entry_ts, age)
        try:
            pos(idx, startbar(w.entry_ts))
            pos(idx, t)
        except RuntimeError:
            continue
        if not eligible_winner(w, t):
            continue
        _, _, wf = sequence_features(market, w, age)
        mae_gap = abs(float(wf["running_mae_R"]) - float(case_f["running_mae_R"]))
        calendar_gap = abs((pd.Timestamp(w.execution_start) - pd.Timestamp(case.execution_start)).total_seconds())
        candidates.append((mae_gap, calendar_gap, pd.Timestamp(w.execution_start), pd.Timestamp(w.entry_ts), w, wf))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return candidates[0][4], candidates[0][5], float(candidates[0][0])


def stat(q, f):
    a = pd.to_numeric(q[f"case__{f}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    b = pd.to_numeric(q[f"control__{f}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = min(len(a), len(b))
    if not n:
        return dict(n=0, case_median=np.nan, control_median=np.nan, median_gap=np.nan, effect=np.nan)
    am = float(a.median())
    bm = float(b.median())
    gap = am - bm
    iqr = (float(a.quantile(0.75) - a.quantile(0.25)) + float(b.quantile(0.75) - b.quantile(0.25))) / 2.0
    effect = abs(gap) / iqr if iqr > EPS else (np.inf if abs(gap) > EPS else 0.0)
    return dict(n=n, case_median=am, control_median=bm, median_gap=gap, effect=effect)


def direction_ok(gap, direction):
    return bool(pd.notna(gap) and ((direction == "lower" and gap < -EPS) or (direction == "higher" and gap > EPS)))


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a65 = load_a65(root)
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
                t = lastbar(r.entry_ts, age)
                pos(idx, startbar(r.entry_ts)); pos(idx, t)
                if not eligible_l0(r, t):
                    continue
                eligible += 1
                cs, ct, cf = sequence_features(market, r, age)
                chosen = choose_control(controls, r, cf, age, market)
                if chosen is None:
                    continue
                w, wf, mae_gap = chosen
                ws, wt, _ = sequence_features(market, w, age)
                matched += 1
                used.append(str(pd.Timestamp(w.entry_ts)))
                mae_gaps.append(mae_gap)
                z = {
                    "partition": p, "snapshot_age_min": age,
                    "case_entry_ts": r.entry_ts, "case_execution_start": r.execution_start, "case_dev_block": r.dev_block,
                    "case_exit_ts": r.exit_ts, "case_invalidation_close_ts": r.invalidation_close_ts,
                    "case_measurement_start_ts": cs, "case_last_completed_bar_ts": ct, "case_pnl": float(r.pnl),
                    "control_entry_ts": w.entry_ts, "control_execution_start": w.execution_start, "control_dev_block": w.dev_block,
                    "control_exit_ts": w.exit_ts, "control_break_ts": w.h1_break_ts, "control_invalidation_close_ts": w.invalidation_close_ts,
                    "control_measurement_start_ts": ws, "control_last_completed_bar_ts": wt, "control_pnl": float(w.pnl),
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
        raise RuntimeError("empty or duplicate A66 events")

    blocks = []
    for age in AGES:
        for f, direction in DIR.items():
            for block_i in range(6):
                q = events[(events.partition == "development") & (events.snapshot_age_min == age) & (pd.to_numeric(events.case_dev_block, errors="coerce") == block_i)]
                s = stat(q, f)
                adequate = s["n"] >= 5
                blocks.append(dict(snapshot_age_min=age, feature=f, direction=direction, dev_block=block_i, **s, adequate=adequate, direction_ok=adequate and direction_ok(s["median_gap"], direction)))
    blocks = pd.DataFrame(blocks)

    metrics = []
    for p in PARTS:
        for age in AGES:
            for f, direction in DIR.items():
                s = stat(events[(events.partition == p) & (events.snapshot_age_min == age)], f)
                adequate_blocks = same_direction_blocks = 0
                block_pass = False
                if p == "development":
                    b = blocks[(blocks.snapshot_age_min == age) & (blocks.feature == f)]
                    a = b[b.adequate]
                    adequate_blocks = len(a)
                    same_direction_blocks = int(a.direction_ok.sum())
                    block_pass = adequate_blocks >= 3 and same_direction_blocks == adequate_blocks
                metrics.append(dict(partition=p, snapshot_age_min=age, feature=f, direction=direction, **s,
                                    direction_ok=direction_ok(s["median_gap"], direction), adequate_dev_blocks=adequate_blocks,
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
                r = metrics[mm].iloc[0]
                ok = bool(dev_pass and r.n >= 8 and r.direction_ok and r.effect >= 0.10 - EPS)
                metrics.loc[mm, "oos_replication_pass"] = ok
                oos.append(ok)
            full = dev_pass and all(oos)
            metrics.loc[(metrics.snapshot_age_min == age) & (metrics.feature == f), "full_snapshot_replication"] = full
            if full:
                replicated[f].append(age)

    supported = [f for f, ages in replicated.items() if ages == [60, 120]]
    status = "SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66_SUPPORTED" if supported else "SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66_INCONCLUSIVE"

    prefix = "SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66"
    artifacts = []
    for name, df in {"EVENTS": events, "COVERAGE": coverage, "METRICS": metrics, "BLOCKS": blocks, "RECONCILIATION": recon}.items():
        p = out / f"{prefix}_{name}.csv"; df.to_csv(p, index=False); artifacts.append(p)
    status_path = out / f"{prefix}_Status.txt"; status_path.write_text(status + "\n"); artifacts.append(status_path)

    fmt = lambda v: "-" if pd.isna(v) else ("inf" if np.isinf(v) else f"{float(v):.3f}")
    result_path = out / f"{prefix}_Result.md"
    lines = ["# SOL LONG 15:00 UTC L0 MAE-Conditioned Reclaim Sequence Anatomy — A66 Result", "", f"**Gate status: {status}**", "", f"Raw SOLUSDT 5m coverage: **{100 * cov:.4f}%**.", "", "A66 conditions L0-vs-winner comparison on nearest running_mae_R severity at the same fixed age, then tests preregistered reclaim-sequence geometry. It is descriptive/mechanistic only; A64 remains closed and live Baba Bot is unchanged.", "", "## Reconciliation", "", "| Partition | Parent | Losses | L0/M0 | Winners |", "|---|---:|---:|---:|---:|"]
    for _, r in recon.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.winner_n)} |")
    lines += ["", "## MAE-conditioned matching", "", "| Partition | Age | Eligible L0 | Matched | Unique winners | Max reuse | Median |ΔMAE| | P75 |ΔMAE| | Max |ΔMAE| |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in coverage.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.snapshot_age_min)}m | {int(r.eligible_l0_n)} | {int(r.matched_n)} | {int(r.unique_control_n)} | {int(r.max_control_reuse)}x | {fmt(r.median_abs_mae_gap)}R | {fmt(r.p75_abs_mae_gap)}R | {fmt(r.max_abs_mae_gap)}R |")
    lines += ["", "## Reclaim-sequence replication", "", "| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |", "|---:|---|---:|---:|---:|---:|---|"]
    for age in AGES:
        for f in DIR:
            d = metrics[(metrics.partition == "development") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            e = metrics[(metrics.partition == "external") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            r = metrics[(metrics.partition == "reference_validation") & (metrics.snapshot_age_min == age) & (metrics.feature == f)].iloc[0]
            lines.append(f"| {age}m | {f} | {fmt(d.median_gap)}/{fmt(d.effect)} | {int(d.same_direction_dev_blocks)}/{int(d.adequate_dev_blocks)} | {fmt(e.median_gap)}/{fmt(e.effect)} | {fmt(r.median_gap)}/{fmt(r.effect)} | {'YES' if d.full_snapshot_replication else 'NO'} |")
    lines += ["", "## Strict 2-of-2 family rule", ""]
    for f in DIR:
        ages = replicated[f]
        lines.append(f"- `{f}`: {ages if ages else 'none'} -> **{'SUPPORTED' if ages == [60, 120] else 'NO'}**")
    lines += ["", f"Supported reclaim-sequence feature families: **{', '.join(supported) if supported else 'none'}**.", "", "Interpretation boundary: A66 is MAE-conditioned sequence anatomy only. It does not authorize a threshold, composite, gate, exit, partial derisk, re-arm, or live intervention.", "", "Research only. Live Baba Bot remains unchanged."]
    result_path.write_text("\n".join(lines) + "\n"); artifacts.append(result_path)

    observed = {"execution_parent": {"range": "R360", "hour": "15UTC", "entry": "E0_RESTING_H", "target": "E40"}, "central_losses_total": 710, "l0_total": 76,
                "partitions": {"Development": {"central_losses": 357, "l0": 37}, "External Validation": {"central_losses": 166, "l0": 13}, "Reference Validation": {"central_losses": 187, "l0": 26}}}
    summary = {"gate_status": status, "market_coverage": float(cov), "supported_reclaim_sequence_feature_families": supported,
               "replicated_snapshots_by_feature": replicated,
               "matched_pairs_by_partition_snapshot": {f"{r.partition}:{int(r.snapshot_age_min)}m": int(r.matched_n) for _, r in coverage.iterrows()},
               "median_abs_mae_match_gap_by_partition_snapshot": {f"{r.partition}:{int(r.snapshot_age_min)}m": float(r.median_abs_mae_gap) for _, r in coverage.iterrows()},
               "interpretation_boundary": "mae_conditioned_reclaim_sequence_anatomy_only_no_intervention"}
    return {"observed": observed, "summary": summary, "artifacts": [p.relative_to(root).as_posix() for p in artifacts]}
