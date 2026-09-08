#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

BAR = pd.Timedelta(minutes=5)
PARTS = ("development", "external", "reference_validation")
SHOW = {
    "development": "Development",
    "external": "External Validation",
    "reference_validation": "Reference Validation",
}
PARENT = {"development": 601, "external": 281, "reference_validation": 337}
LOSSES = {"development": 357, "external": 166, "reference_validation": 187}
L0 = {"development": 37, "external": 13, "reference_validation": 26}
M1 = {"development": 58, "external": 16, "reference_validation": 21}
AGES = (60, 120)
EPS = 1e-12
DIR = {
    "running_mae_R": "higher",
    "close_H_R": "lower",
    "drawdown_from_best_R": "higher",
}


def load_a55(root: Path):
    p = root / "research" / "sol_long_15utc_loss_confirmation_candle_a55.py"
    s = importlib.util.spec_from_file_location("a63_a55", p)
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
    return bool(
        r.mechanism == "M0_REFERENCE_INVALIDATION"
        and pd.notna(r.invalidation_close_ts)
        and pd.isna(r.h1_break_ts)
        and pd.Timestamp(r.invalidation_close_ts) > t
        and pd.Timestamp(r.exit_ts) > t
    )


def eligible_m1(r, t):
    return bool(
        r.mechanism == "M1_TIME_NO_STRUCTURAL_FAIL"
        and pd.Timestamp(r.exit_ts) > t
        and (pd.isna(r.h1_break_ts) or pd.Timestamp(r.h1_break_ts) > t)
        and (pd.isna(r.invalidation_close_ts) or pd.Timestamp(r.invalidation_close_ts) > t)
    )


def choose_control(pool, case, age, idx):
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
        if not eligible_m1(w, t):
            continue
        d = abs((pd.Timestamp(w.execution_start) - pd.Timestamp(case.execution_start)).total_seconds())
        candidates.append((d, pd.Timestamp(w.execution_start), pd.Timestamp(w.entry_ts), w, t))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return candidates[0][3], candidates[0][4]


def features(m, r, age):
    idx = m["idx"]
    s = startbar(r.entry_ts)
    t = lastbar(r.entry_ts, age)
    a = pos(idx, s)
    b = pos(idx, t)
    hi = np.asarray(m["high"][a : b + 1], float)
    lo = np.asarray(m["low"][a : b + 1], float)
    cl = np.asarray(m["close"][a : b + 1], float)
    H, R = float(r.H), float(r.R)
    if R <= 0:
        raise RuntimeError(f"nonpositive R at {r.entry_ts}")
    mx = float(hi.max())
    mn = float(lo.min())
    c = float(cl[-1])
    f = {
        "running_mae_R": max(0.0, (H - mn) / R),
        "close_H_R": (c - H) / R,
        "drawdown_from_best_R": (mx - c) / R,
    }
    if not all(np.isfinite(v) for v in f.values()):
        raise RuntimeError(f"bad feature row {r.entry_ts} age {age}")
    return s, t, f


def stat(q, f):
    a = pd.to_numeric(q[f"case__{f}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    b = pd.to_numeric(q[f"control__{f}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = min(len(a), len(b))
    if not n:
        return dict(n=0, case_median=np.nan, control_median=np.nan, median_gap=np.nan, effect=np.nan)
    am = float(a.median())
    bm = float(b.median())
    gap = am - bm
    iqr = (
        float(a.quantile(0.75) - a.quantile(0.25))
        + float(b.quantile(0.75) - b.quantile(0.25))
    ) / 2.0
    effect = abs(gap) / iqr if iqr > EPS else (np.inf if abs(gap) > EPS else 0.0)
    return dict(n=n, case_median=am, control_median=bm, median_gap=gap, effect=effect)


def direction_ok(gap, direction):
    return bool(
        pd.notna(gap)
        and ((direction == "lower" and gap < -EPS) or (direction == "higher" and gap > EPS))
    )


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a55 = load_a55(root)
    x, cov = a55.a2.a1.load5()
    market = a55.a2.make_market_with_open(x)
    idx = market["idx"]
    parents = {p: a55.parent(market, p) for p in PARTS}

    recon = []
    errors = []
    for p, q in parents.items():
        parent_n = len(q)
        loss_n = int((~q.economic_win).sum())
        l0_n = int((q.mechanism == "M0_REFERENCE_INVALIDATION").sum())
        m1_n = int((q.mechanism == "M1_TIME_NO_STRUCTURAL_FAIL").sum())
        recon.append(
            dict(partition=p, parent_n=parent_n, loss_n=loss_n, l0_n=l0_n, m1_n=m1_n)
        )
        if parent_n != PARENT[p]:
            errors.append(f"{p} parent {parent_n}!={PARENT[p]}")
        if loss_n != LOSSES[p]:
            errors.append(f"{p} losses {loss_n}!={LOSSES[p]}")
        if l0_n != L0[p]:
            errors.append(f"{p} L0 {l0_n}!={L0[p]}")
        if m1_n != M1[p]:
            errors.append(f"{p} M1 {m1_n}!={M1[p]}")
    if errors:
        raise RuntimeError("; ".join(errors))
    recon = pd.DataFrame(recon)

    rows = []
    coverage = []
    for p, q in parents.items():
        cases = q[q.mechanism == "M0_REFERENCE_INVALIDATION"]
        controls = q[q.mechanism == "M1_TIME_NO_STRUCTURAL_FAIL"]
        for age in AGES:
            eligible = 0
            matched = 0
            used = []
            for _, r in cases.iterrows():
                t = lastbar(r.entry_ts, age)
                pos(idx, startbar(r.entry_ts))
                pos(idx, t)
                if not eligible_l0(r, t):
                    continue
                eligible += 1
                chosen = choose_control(controls, r, age, idx)
                if chosen is None:
                    continue
                w, wt = chosen
                cs, ct, cf = features(market, r, age)
                ws, wtt, wf = features(market, w, age)
                matched += 1
                used.append(str(pd.Timestamp(w.entry_ts)))
                z = {
                    "partition": p,
                    "snapshot_age_min": age,
                    "case_entry_ts": r.entry_ts,
                    "case_execution_start": r.execution_start,
                    "case_dev_block": r.dev_block,
                    "case_invalidation_close_ts": r.invalidation_close_ts,
                    "case_exit_ts": r.exit_ts,
                    "case_measurement_start_ts": cs,
                    "case_last_completed_bar_ts": ct,
                    "case_pnl": float(r.pnl),
                    "control_entry_ts": w.entry_ts,
                    "control_execution_start": w.execution_start,
                    "control_dev_block": w.dev_block,
                    "control_break_ts": w.h1_break_ts,
                    "control_invalidation_close_ts": w.invalidation_close_ts,
                    "control_exit_ts": w.exit_ts,
                    "control_measurement_start_ts": ws,
                    "control_last_completed_bar_ts": wtt,
                    "control_pnl": float(w.pnl),
                }
                for f in DIR:
                    z[f"case__{f}"] = cf[f]
                    z[f"control__{f}"] = wf[f]
                rows.append(z)
            counter = Counter(used)
            coverage.append(
                dict(
                    partition=p,
                    snapshot_age_min=age,
                    l0_total=len(cases),
                    m1_total=len(controls),
                    eligible_l0_n=eligible,
                    matched_n=matched,
                    match_rate=matched / eligible if eligible else np.nan,
                    unique_control_n=len(counter),
                    reused_match_n=sum(max(0, v - 1) for v in counter.values()),
                    max_control_reuse=max(counter.values()) if counter else 0,
                )
            )

    events = pd.DataFrame(rows)
    coverage = pd.DataFrame(coverage)
    if events.empty or events.duplicated(["partition", "snapshot_age_min", "case_entry_ts"]).any():
        raise RuntimeError("empty or duplicate A63 events")

    blocks = []
    for age in AGES:
        for f, direction in DIR.items():
            for block_i in range(6):
                q = events[
                    (events.partition == "development")
                    & (events.snapshot_age_min == age)
                    & (pd.to_numeric(events.case_dev_block, errors="coerce") == block_i)
                ]
                s = stat(q, f)
                adequate = s["n"] >= 5
                blocks.append(
                    dict(
                        snapshot_age_min=age,
                        feature=f,
                        direction=direction,
                        dev_block=block_i,
                        **s,
                        adequate=adequate,
                        direction_ok=adequate and direction_ok(s["median_gap"], direction),
                    )
                )
    blocks = pd.DataFrame(blocks)

    metrics = []
    for p in PARTS:
        for age in AGES:
            for f, direction in DIR.items():
                s = stat(events[(events.partition == p) & (events.snapshot_age_min == age)], f)
                adequate_blocks = 0
                same_direction_blocks = 0
                block_pass = False
                if p == "development":
                    b = blocks[(blocks.snapshot_age_min == age) & (blocks.feature == f)]
                    a = b[b.adequate]
                    adequate_blocks = len(a)
                    same_direction_blocks = int(a.direction_ok.sum())
                    block_pass = adequate_blocks >= 3 and same_direction_blocks == adequate_blocks
                metrics.append(
                    dict(
                        partition=p,
                        snapshot_age_min=age,
                        feature=f,
                        direction=direction,
                        **s,
                        direction_ok=direction_ok(s["median_gap"], direction),
                        adequate_dev_blocks=adequate_blocks,
                        same_direction_dev_blocks=same_direction_blocks,
                        dev_block_rule_pass=block_pass,
                    )
                )
    metrics = pd.DataFrame(metrics)
    metrics["development_eligible"] = False
    metrics["oos_replication_pass"] = False
    metrics["full_snapshot_replication"] = False

    replicated = {f: [] for f in DIR}
    for age in AGES:
        for f in DIR:
            dm = (
                (metrics.partition == "development")
                & (metrics.snapshot_age_min == age)
                & (metrics.feature == f)
            )
            d = metrics[dm].iloc[0]
            dev_pass = bool(
                d.n >= 20
                and d.direction_ok
                and d.effect >= 0.30 - EPS
                and d.dev_block_rule_pass
            )
            metrics.loc[dm, "development_eligible"] = dev_pass
            oos_passes = []
            for p in ("external", "reference_validation"):
                mm = (
                    (metrics.partition == p)
                    & (metrics.snapshot_age_min == age)
                    & (metrics.feature == f)
                )
                r = metrics[mm].iloc[0]
                ok = bool(dev_pass and r.n >= 8 and r.direction_ok and r.effect >= 0.10 - EPS)
                metrics.loc[mm, "oos_replication_pass"] = ok
                oos_passes.append(ok)
            full = dev_pass and all(oos_passes)
            metrics.loc[
                (metrics.snapshot_age_min == age) & (metrics.feature == f),
                "full_snapshot_replication",
            ] = full
            if full:
                replicated[f].append(age)

    specific = [f for f, ages in replicated.items() if ages == [60, 120]]
    status = (
        "SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED"
        if specific
        else "SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_NOT_SPECIFIC"
    )

    dataframes = {
        "EVENTS": events,
        "COVERAGE": coverage,
        "METRICS": metrics,
        "BLOCKS": blocks,
        "RECONCILIATION": recon,
    }
    artifacts = []
    for name, df in dataframes.items():
        p = out / f"SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_{name}.csv"
        df.to_csv(p, index=False)
        artifacts.append(p)

    status_path = out / "SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_Status.txt"
    status_path.write_text(status + "\n")
    artifacts.append(status_path)

    result_path = out / "SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_Result.md"
    fmt = lambda v: "-" if pd.isna(v) else ("inf" if np.isinf(v) else f"{float(v):.3f}")
    lines = [
        "# SOL LONG 15:00 UTC L0 Early Progress Specificity — A63 Result",
        "",
        f"**Gate status: {status}**",
        "",
        f"Raw SOLUSDT 5m coverage: **{100 * cov:.4f}%**.",
        "",
        "A63 compares frozen L0/M0 reference-invalidation losses against frozen M1 time/no-structural-fail losses at the same early ages. It is descriptive/mechanistic only; live Baba Bot is unchanged.",
        "",
        "## Reconciliation",
        "",
        "| Partition | Parent | Losses | L0/M0 | M1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in recon.iterrows():
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.m1_n)} |"
        )
    lines += [
        "",
        "## Snapshot matching",
        "",
        "| Partition | Age | Eligible L0 | Matched M1 | Unique controls | Max reuse |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in coverage.iterrows():
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.snapshot_age_min)}m | {int(r.eligible_l0_n)} | {int(r.matched_n)} | {int(r.unique_control_n)} | {int(r.max_control_reuse)}x |"
        )
    lines += [
        "",
        "## Specificity replication",
        "",
        "| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for age in AGES:
        for f in DIR:
            d = metrics[
                (metrics.partition == "development")
                & (metrics.snapshot_age_min == age)
                & (metrics.feature == f)
            ].iloc[0]
            e = metrics[
                (metrics.partition == "external")
                & (metrics.snapshot_age_min == age)
                & (metrics.feature == f)
            ].iloc[0]
            r = metrics[
                (metrics.partition == "reference_validation")
                & (metrics.snapshot_age_min == age)
                & (metrics.feature == f)
            ].iloc[0]
            lines.append(
                f"| {age}m | {f} | {fmt(d.median_gap)}/{fmt(d.effect)} | {int(d.same_direction_dev_blocks)}/{int(d.adequate_dev_blocks)} | {fmt(e.median_gap)}/{fmt(e.effect)} | {fmt(r.median_gap)}/{fmt(r.effect)} | {'YES' if d.full_snapshot_replication else 'NO'} |"
            )
    lines += ["", "## 2-of-2 specificity rule", ""]
    for f in DIR:
        ages = replicated[f]
        lines.append(
            f"- `{f}`: {ages if ages else 'none'} -> **{'L0-SPECIFIC' if ages == [60, 120] else 'NO'}**"
        )
    lines += [
        "",
        f"L0-specific feature families: **{', '.join(specific) if specific else 'none'}**.",
        "",
        "A63 does not authorize any threshold, composite, gate, derisk, position-size change, or exit. A specificity result is still not an economic intervention result.",
        "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    result_path.write_text("\n".join(lines) + "\n")
    artifacts.append(result_path)

    observed = {
        "execution_parent": {"range": "R360", "hour": "15UTC", "entry": "E0_RESTING_H", "target": "E40"},
        "central_losses_total": 710,
        "l0_total": 76,
        "m1_total": 95,
        "partitions": {
            "Development": {"central_losses": 357, "l0": 37, "m1": 58},
            "External Validation": {"central_losses": 166, "l0": 13, "m1": 16},
            "Reference Validation": {"central_losses": 187, "l0": 26, "m1": 21},
        },
    }
    summary = {
        "gate_status": status,
        "market_coverage": float(cov),
        "l0_specific_feature_families": specific,
        "replicated_snapshots_by_feature": replicated,
        "matched_pairs_by_partition_snapshot": {
            f"{r.partition}:{int(r.snapshot_age_min)}m": int(r.matched_n)
            for _, r in coverage.iterrows()
        },
        "interpretation_boundary": "mechanism_specificity_only_no_executable_intervention",
    }
    return {
        "observed": observed,
        "summary": summary,
        "artifacts": [p.relative_to(root).as_posix() for p in artifacts],
    }
