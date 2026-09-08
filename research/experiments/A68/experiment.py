#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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
WINNERS = {"development": 244, "external": 115, "reference_validation": 150}
HORIZONS = (30, 60, 120)
PRIMARY_HORIZONS = (30, 60)
CORE_FEATURES = ("short_close_return_R", "short_excursion_dominance_R")
FEATURE_NEUTRAL = {
    "short_close_return_R": 0.0,
    "short_excursion_dominance_R": 0.0,
    "short_capture_fraction": 0.5,
}
FEATURES = tuple(FEATURE_NEUTRAL)
EPS = 1e-12


def load_a55(root: Path):
    p = root / "research" / "sol_long_15utc_loss_confirmation_candle_a55.py"
    s = importlib.util.spec_from_file_location("a68_a55", p)
    m = importlib.util.module_from_spec(s)
    assert s.loader is not None
    s.loader.exec_module(m)
    return m


def pos(idx, ts):
    ts = pd.Timestamp(ts)
    i = int(idx.searchsorted(ts, "left"))
    if i >= len(idx) or idx[i] != ts:
        raise RuntimeError(f"timestamp parity failure {ts}")
    return i


def event_features(x: pd.DataFrame, r, horizon: int):
    signal_ts = pd.Timestamp(r.invalidation_close_ts)
    origin_ts = signal_ts + BAR
    last_ts = origin_ts + pd.Timedelta(minutes=int(horizon)) - BAR
    a = pos(x.index, origin_ts)
    b = pos(x.index, last_ts)
    if b < a:
        raise RuntimeError(f"bad A68 forward window {r.entry_ts} horizon={horizon}")

    q = x.iloc[a : b + 1]
    if len(q) != int(horizon // 5):
        raise RuntimeError(f"A68 bar-count mismatch {r.entry_ts} horizon={horizon} n={len(q)}")

    R = float(r.R)
    if not np.isfinite(R) or R <= 0:
        raise RuntimeError(f"bad R for A68 {r.entry_ts}")

    origin_open = float(q.iloc[0].open)
    final_close = float(q.iloc[-1].close)
    min_low = float(pd.to_numeric(q.low, errors="coerce").min())
    max_high = float(pd.to_numeric(q.high, errors="coerce").max())
    vals = (origin_open, final_close, min_low, max_high)
    if not all(np.isfinite(v) for v in vals):
        raise RuntimeError(f"nonfinite A68 price path {r.entry_ts} horizon={horizon}")

    short_close_return_R = (origin_open - final_close) / R
    short_mfe_R = max(0.0, (origin_open - min_low) / R)
    short_mae_R = max(0.0, (max_high - origin_open) / R)
    short_excursion_dominance_R = short_mfe_R - short_mae_R
    den = short_mfe_R + short_mae_R
    short_capture_fraction = short_mfe_R / den if den > EPS else 0.5

    return {
        "signal_ts": signal_ts,
        "origin_ts": origin_ts,
        "last_completed_bar_ts": last_ts,
        "origin_open": origin_open,
        "final_close": final_close,
        "min_forward_low": min_low,
        "max_forward_high": max_high,
        "short_close_return_R": float(short_close_return_R),
        "short_mfe_R": float(short_mfe_R),
        "short_mae_R": float(short_mae_R),
        "short_excursion_dominance_R": float(short_excursion_dominance_R),
        "short_capture_fraction": float(short_capture_fraction),
        "short_close_positive": bool(short_close_return_R > 0),
    }


def neutral_stat(q: pd.DataFrame, feature: str):
    neutral = float(FEATURE_NEUTRAL[feature])
    a = pd.to_numeric(q[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(a) == 0:
        return {
            "n": 0,
            "neutral_reference": neutral,
            "median": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "iqr": np.nan,
            "centered_median": np.nan,
            "effect": np.nan,
            "direction_ok": False,
        }
    med = float(a.median())
    p25 = float(a.quantile(0.25))
    p75 = float(a.quantile(0.75))
    iqr = p75 - p25
    centered = med - neutral
    effect = abs(centered) / iqr if iqr > EPS else (np.inf if abs(centered) > EPS else 0.0)
    return {
        "n": int(len(a)),
        "neutral_reference": neutral,
        "median": med,
        "p25": p25,
        "p75": p75,
        "iqr": float(iqr),
        "centered_median": float(centered),
        "effect": float(effect),
        "direction_ok": bool(centered > EPS),
    }


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a55 = load_a55(root)
    x, raw_cov = a55.a2.a1.load5()
    market = a55.a2.make_market_with_open(x)
    parents = {p: a55.parent(market, p) for p in PARTS}

    recon_rows = []
    errors = []
    for p, q in parents.items():
        parent_n = len(q)
        loss_n = int((~q.economic_win).sum())
        l0_n = int((q.mechanism == "M0_REFERENCE_INVALIDATION").sum())
        winner_n = int(q.economic_win.sum())
        recon_rows.append({
            "partition": p,
            "parent_n": parent_n,
            "loss_n": loss_n,
            "l0_n": l0_n,
            "winner_n": winner_n,
        })
        if parent_n != PARENT[p]:
            errors.append(f"{p} parent {parent_n}!={PARENT[p]}")
        if loss_n != LOSSES[p]:
            errors.append(f"{p} losses {loss_n}!={LOSSES[p]}")
        if l0_n != L0[p]:
            errors.append(f"{p} L0 {l0_n}!={L0[p]}")
        if winner_n != WINNERS[p]:
            errors.append(f"{p} winners {winner_n}!={WINNERS[p]}")
    if errors:
        raise RuntimeError("; ".join(errors))
    recon = pd.DataFrame(recon_rows)

    rows = []
    coverage_rows = []
    parity_rows = []
    for p, q in parents.items():
        cases = q[q.mechanism == "M0_REFERENCE_INVALIDATION"].copy()
        if cases.invalidation_close_ts.isna().any():
            raise RuntimeError(f"{p} A68 M0 contains missing invalidation timestamp")

        parity = []
        for _, r in cases.iterrows():
            origin_ts = pd.Timestamp(r.invalidation_close_ts) + BAR
            same = bool(pd.Timestamp(r.exit_ts) == origin_ts)
            parity.append(same)
        parity_rows.append({
            "partition": p,
            "l0_n": len(cases),
            "parent_exit_equals_causal_origin_n": int(sum(parity)),
            "parent_exit_equals_causal_origin_rate": float(np.mean(parity)) if parity else np.nan,
        })

        for horizon in HORIZONS:
            eligible = 0
            missing = 0
            for _, r in cases.iterrows():
                origin_ts = pd.Timestamp(r.invalidation_close_ts) + BAR
                last_ts = origin_ts + pd.Timedelta(minutes=int(horizon)) - BAR
                try:
                    pos(x.index, origin_ts)
                    pos(x.index, last_ts)
                except RuntimeError:
                    missing += 1
                    continue
                f = event_features(x, r, horizon)
                eligible += 1
                rows.append({
                    "partition": p,
                    "horizon_min": int(horizon),
                    "entry_ts": r.entry_ts,
                    "execution_start": r.execution_start,
                    "dev_block": r.dev_block,
                    "parent_exit_ts": r.exit_ts,
                    "parent_pnl": float(r.pnl),
                    "parent_R": float(r.R),
                    "invalidation_close_ts": r.invalidation_close_ts,
                    "parent_exit_equals_causal_origin": bool(pd.Timestamp(r.exit_ts) == pd.Timestamp(f["origin_ts"])),
                    **f,
                })
            coverage_rows.append({
                "partition": p,
                "horizon_min": int(horizon),
                "l0_total": int(len(cases)),
                "eligible_n": int(eligible),
                "missing_forward_data_n": int(missing),
                "eligible_rate": float(eligible / len(cases)) if len(cases) else np.nan,
            })

    events = pd.DataFrame(rows)
    coverage = pd.DataFrame(coverage_rows)
    parity = pd.DataFrame(parity_rows)
    if events.empty:
        raise RuntimeError("empty A68 events")
    if events.duplicated(["partition", "horizon_min", "entry_ts"]).any():
        raise RuntimeError("duplicate A68 events")

    blocks = []
    for horizon in HORIZONS:
        for feature in FEATURES:
            for block_i in range(6):
                q = events[
                    (events.partition == "development")
                    & (events.horizon_min == horizon)
                    & (pd.to_numeric(events.dev_block, errors="coerce") == block_i)
                ]
                s = neutral_stat(q, feature)
                adequate = bool(s["n"] >= 5)
                blocks.append({
                    "horizon_min": int(horizon),
                    "feature": feature,
                    "dev_block": int(block_i),
                    **s,
                    "adequate": adequate,
                    "block_direction_ok": bool(adequate and s["direction_ok"]),
                })
    blocks = pd.DataFrame(blocks)

    metrics = []
    for p in PARTS:
        for horizon in HORIZONS:
            for feature in FEATURES:
                q = events[(events.partition == p) & (events.horizon_min == horizon)]
                s = neutral_stat(q, feature)
                adequate_blocks = 0
                same_direction_blocks = 0
                block_rule_pass = False
                if p == "development":
                    b = blocks[(blocks.horizon_min == horizon) & (blocks.feature == feature)]
                    aa = b[b.adequate]
                    adequate_blocks = int(len(aa))
                    same_direction_blocks = int(aa.block_direction_ok.sum())
                    block_rule_pass = bool(adequate_blocks >= 3 and same_direction_blocks == adequate_blocks)
                metrics.append({
                    "partition": p,
                    "horizon_min": int(horizon),
                    "feature": feature,
                    **s,
                    "adequate_dev_blocks": adequate_blocks,
                    "same_direction_dev_blocks": same_direction_blocks,
                    "dev_block_rule_pass": block_rule_pass,
                    "development_eligible": False,
                    "oos_replication_pass": False,
                    "full_horizon_replication": False,
                })
    metrics = pd.DataFrame(metrics)

    full_by_feature = {f: [] for f in FEATURES}
    for horizon in HORIZONS:
        for feature in FEATURES:
            dm = (
                (metrics.partition == "development")
                & (metrics.horizon_min == horizon)
                & (metrics.feature == feature)
            )
            d = metrics[dm].iloc[0]
            dev_pass = bool(
                d.n >= 20
                and d.direction_ok
                and d.effect >= 0.30 - EPS
                and d.dev_block_rule_pass
            )
            metrics.loc[dm, "development_eligible"] = dev_pass

            oos_pass = []
            for p in ("external", "reference_validation"):
                mm = (
                    (metrics.partition == p)
                    & (metrics.horizon_min == horizon)
                    & (metrics.feature == feature)
                )
                r = metrics[mm].iloc[0]
                ok = bool(
                    dev_pass
                    and r.n >= 8
                    and r.direction_ok
                    and r.effect >= 0.10 - EPS
                )
                metrics.loc[mm, "oos_replication_pass"] = ok
                oos_pass.append(ok)

            full = bool(dev_pass and all(oos_pass))
            metrics.loc[
                (metrics.horizon_min == horizon) & (metrics.feature == feature),
                "full_horizon_replication",
            ] = full
            if full:
                full_by_feature[feature].append(int(horizon))

    supported_core = [
        f for f in CORE_FEATURES
        if all(h in full_by_feature[f] for h in PRIMARY_HORIZONS)
    ]
    status = (
        "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_SUPPORTED"
        if supported_core
        else "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_INCONCLUSIVE"
    )

    prefix = "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68"
    artifacts = []
    for name, df in {
        "EVENTS": events,
        "COVERAGE": coverage,
        "METRICS": metrics,
        "BLOCKS": blocks,
        "PARITY": parity,
        "RECONCILIATION": recon,
    }.items():
        p = out / f"{prefix}_{name}.csv"
        df.to_csv(p, index=False)
        artifacts.append(p)

    status_path = out / f"{prefix}_Status.txt"
    status_path.write_text(status + "\n")
    artifacts.append(status_path)

    def fmt(v, d=3):
        if pd.isna(v):
            return "-"
        if np.isinf(v):
            return "inf"
        return f"{float(v):.{d}f}"

    result_path = out / f"{prefix}_Result.md"
    lines = [
        "# SOL LONG 15:00 UTC M0 Reference-Invalidation Downside-Continuation Anatomy — A68 Result",
        "",
        f"**Gate status: {status}**",
        "",
        f"Raw SOLUSDT 5m coverage: **{100 * raw_cov:.4f}%**.",
        "",
        "A68 starts only after the frozen M0 invalidating candle has completed. The directional origin is fixed to the open of the next 5m bar, so the invalidation candle itself is never used as a short fill. A68 is anatomy only; it does not simulate a short TP/SL or modify live Baba Bot.",
        "",
        "## Reconciliation",
        "",
        "| Partition | Parent | Losses | L0/M0 | Winners |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in recon.iterrows():
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.winner_n)} |"
        )

    lines += [
        "",
        "## Causal-origin parity",
        "",
        "| Partition | L0/M0 | Parent exit = next-bar origin | Rate |",
        "|---|---:|---:|---:|",
    ]
    for _, r in parity.iterrows():
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.l0_n)} | {int(r.parent_exit_equals_causal_origin_n)} | {100*float(r.parent_exit_equals_causal_origin_rate):.1f}% |"
        )

    lines += [
        "",
        "## Forward-data coverage",
        "",
        "| Partition | Horizon | Eligible | Total M0 | Coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in coverage.iterrows():
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.horizon_min)}m | {int(r.eligible_n)} | {int(r.l0_total)} | {100*float(r.eligible_rate):.1f}% |"
        )

    lines += [
        "",
        "## Directional anatomy",
        "",
        "| Partition | Horizon | Feature | N | Median | Neutral | Centered | Effect | Dev blocks | Dev pass | OOS pass | Full |",
        "|---|---:|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for _, r in metrics.iterrows():
        blocks_txt = "-"
        if r.partition == "development":
            blocks_txt = f"{int(r.same_direction_dev_blocks)}/{int(r.adequate_dev_blocks)}"
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.horizon_min)}m | `{r.feature}` | {int(r.n)} | {fmt(r['median'])} | {fmt(r.neutral_reference)} | {fmt(r.centered_median)} | {fmt(r.effect)} | {blocks_txt} | {'YES' if bool(r.development_eligible) else 'NO'} | {'YES' if bool(r.oos_replication_pass) else 'NO'} | {'YES' if bool(r.full_horizon_replication) else 'NO'} |"
        )

    lines += [
        "",
        "## Primary 30m/60m family gate",
        "",
    ]
    for f in CORE_FEATURES:
        got = sorted(h for h in full_by_feature[f] if h in PRIMARY_HORIZONS)
        lines.append(f"- `{f}`: replicated primary horizons = {got}; strict 2-of-2 = {'YES' if f in supported_core else 'NO'}.")
    lines.append(f"- `short_capture_fraction` is corroborative only; replicated horizons = {sorted(full_by_feature['short_capture_fraction'])}.")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "A supported result means confirmed M0 structural failure is followed by replicated downside-continuation anatomy from a causal next-bar origin. It does not establish tradable short economics. Any stop, target, costs, sizing, leverage, re-entry, or combined long-plus-short PnL must be tested in a separately preregistered experiment.",
        "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    result_path.write_text("\n".join(lines) + "\n")
    artifacts.append(result_path)

    summary = {
        "status": status,
        "supported_core_feature_families": supported_core,
        "full_replication_horizons": full_by_feature,
        "raw_5m_coverage": float(raw_cov),
        "interpretation_boundary": "post_invalidation_directional_anatomy_only_no_short_economics",
    }
    observed = {
        "reconciliation": recon.to_dict(orient="records"),
        "coverage": coverage.to_dict(orient="records"),
        "causal_origin_parity": parity.to_dict(orient="records"),
        "metrics": metrics.to_dict(orient="records"),
    }
    return {
        "observed": observed,
        "summary": summary,
        "artifacts": [p.relative_to(root).as_posix() for p in artifacts],
    }
