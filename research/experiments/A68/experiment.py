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
PRIMARY = (30, 60)
CORE = ("short_close_return_R", "short_excursion_dominance_R")
NEUTRAL = {
    "short_close_return_R": 0.0,
    "short_excursion_dominance_R": 0.0,
    "short_capture_fraction": 0.5,
}
FEATURES = tuple(NEUTRAL)
EPS = 1e-12
EXECUTION_PARENT = {"range": "R360", "hour": "15UTC", "entry": "E0_RESTING_H", "target": "E40"}


def load_a55(root: Path):
    p = root / "research" / "sol_long_15utc_loss_confirmation_candle_a55.py"
    spec = importlib.util.spec_from_file_location("a68_a55", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def pos(idx, ts):
    ts = pd.Timestamp(ts)
    i = int(idx.searchsorted(ts, "left"))
    if i >= len(idx) or idx[i] != ts:
        raise RuntimeError(f"timestamp parity failure {ts}")
    return i


def forward_features(x: pd.DataFrame, r, horizon: int):
    signal_ts = pd.Timestamp(r.invalidation_close_ts)
    origin_ts = signal_ts + BAR
    last_ts = origin_ts + pd.Timedelta(minutes=horizon) - BAR
    a = pos(x.index, origin_ts)
    b = pos(x.index, last_ts)
    q = x.iloc[a:b + 1]
    if len(q) != horizon // 5:
        raise RuntimeError(f"A68 bar-count mismatch {r.entry_ts} H={horizon}: {len(q)}")
    R = float(r.R)
    if not np.isfinite(R) or R <= 0:
        raise RuntimeError(f"bad parent R {r.entry_ts}")
    origin = float(q.iloc[0].open)
    close = float(q.iloc[-1].close)
    low = float(pd.to_numeric(q.low, errors="coerce").min())
    high = float(pd.to_numeric(q.high, errors="coerce").max())
    if not all(np.isfinite(v) for v in (origin, close, low, high)):
        raise RuntimeError(f"nonfinite A68 path {r.entry_ts} H={horizon}")
    mfe = max(0.0, (origin - low) / R)
    mae = max(0.0, (high - origin) / R)
    den = mfe + mae
    close_ret = (origin - close) / R
    return {
        "signal_ts": signal_ts,
        "origin_ts": origin_ts,
        "last_completed_bar_ts": last_ts,
        "origin_open": origin,
        "final_close": close,
        "min_forward_low": low,
        "max_forward_high": high,
        "short_close_return_R": float(close_ret),
        "short_mfe_R": float(mfe),
        "short_mae_R": float(mae),
        "short_excursion_dominance_R": float(mfe - mae),
        "short_capture_fraction": float(mfe / den if den > EPS else 0.5),
        "short_close_positive": bool(close_ret > 0),
    }


def stat(q: pd.DataFrame, feature: str):
    neutral = float(NEUTRAL[feature])
    a = pd.to_numeric(q[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if a.empty:
        return dict(n=0, neutral_reference=neutral, median=np.nan, p25=np.nan, p75=np.nan,
                    iqr=np.nan, centered_median=np.nan, effect=np.nan, direction_ok=False)
    med = float(a.median())
    p25 = float(a.quantile(.25))
    p75 = float(a.quantile(.75))
    iqr = p75 - p25
    centered = med - neutral
    effect = abs(centered) / iqr if iqr > EPS else (np.inf if abs(centered) > EPS else 0.0)
    return dict(n=int(len(a)), neutral_reference=neutral, median=med, p25=p25, p75=p75,
                iqr=float(iqr), centered_median=float(centered), effect=float(effect),
                direction_ok=bool(centered > EPS))


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a55 = load_a55(root)
    x, raw_cov = a55.a2.a1.load5()
    market = a55.a2.make_market_with_open(x)
    parents = {p: a55.parent(market, p) for p in PARTS}

    recon_rows = []
    for p, q in parents.items():
        got = {
            "parent_n": len(q),
            "loss_n": int((~q.economic_win).sum()),
            "l0_n": int((q.mechanism == "M0_REFERENCE_INVALIDATION").sum()),
            "winner_n": int(q.economic_win.sum()),
        }
        expected = (PARENT[p], LOSSES[p], L0[p], WINNERS[p])
        actual = (got["parent_n"], got["loss_n"], got["l0_n"], got["winner_n"])
        if actual != expected:
            raise RuntimeError(f"A68 frozen reconciliation failed {p}: {actual}!={expected}")
        recon_rows.append({"partition": p, **got})
    recon = pd.DataFrame(recon_rows)

    rows, cov_rows, parity_rows = [], [], []
    for p, q in parents.items():
        cases = q[q.mechanism == "M0_REFERENCE_INVALIDATION"].copy()
        if cases.invalidation_close_ts.isna().any():
            raise RuntimeError(f"{p}: M0 missing invalidation timestamp")

        parity_flags = [
            bool(pd.Timestamp(r.exit_ts) == pd.Timestamp(r.invalidation_close_ts) + BAR)
            for _, r in cases.iterrows()
        ]
        parity_rows.append({
            "partition": p,
            "l0_n": int(len(cases)),
            "parent_exit_equals_causal_origin_n": int(sum(parity_flags)),
            "parent_exit_equals_causal_origin_rate": float(np.mean(parity_flags)),
        })

        for h in HORIZONS:
            eligible = missing = 0
            for _, r in cases.iterrows():
                origin = pd.Timestamp(r.invalidation_close_ts) + BAR
                last = origin + pd.Timedelta(minutes=h) - BAR
                try:
                    pos(x.index, origin)
                    pos(x.index, last)
                except RuntimeError:
                    missing += 1
                    continue
                f = forward_features(x, r, h)
                eligible += 1
                rows.append({
                    "partition": p,
                    "horizon_min": h,
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
            cov_rows.append({
                "partition": p,
                "horizon_min": h,
                "l0_total": int(len(cases)),
                "eligible_n": int(eligible),
                "missing_forward_data_n": int(missing),
                "eligible_rate": float(eligible / len(cases)),
            })

    events = pd.DataFrame(rows)
    coverage = pd.DataFrame(cov_rows)
    parity = pd.DataFrame(parity_rows)
    if events.empty or events.duplicated(["partition", "horizon_min", "entry_ts"]).any():
        raise RuntimeError("A68 empty or duplicate events")

    block_rows = []
    for h in HORIZONS:
        for f in FEATURES:
            for bi in range(6):
                q = events[(events.partition == "development") & (events.horizon_min == h)
                           & (pd.to_numeric(events.dev_block, errors="coerce") == bi)]
                s = stat(q, f)
                adequate = s["n"] >= 5
                block_rows.append({"horizon_min": h, "feature": f, "dev_block": bi, **s,
                                   "adequate": bool(adequate),
                                   "block_direction_ok": bool(adequate and s["direction_ok"])})
    blocks = pd.DataFrame(block_rows)

    metric_rows = []
    for p in PARTS:
        for h in HORIZONS:
            for f in FEATURES:
                s = stat(events[(events.partition == p) & (events.horizon_min == h)], f)
                adequate = same = 0
                block_pass = False
                if p == "development":
                    b = blocks[(blocks.horizon_min == h) & (blocks.feature == f)]
                    a = b[b.adequate]
                    adequate = int(len(a))
                    same = int(a.block_direction_ok.sum())
                    block_pass = bool(adequate >= 3 and same == adequate)
                metric_rows.append({"partition": p, "horizon_min": h, "feature": f, **s,
                                    "adequate_dev_blocks": adequate,
                                    "same_direction_dev_blocks": same,
                                    "dev_block_rule_pass": block_pass,
                                    "development_eligible": False,
                                    "oos_replication_pass": False,
                                    "full_horizon_replication": False})
    metrics = pd.DataFrame(metric_rows)

    replicated = {f: [] for f in FEATURES}
    for h in HORIZONS:
        for f in FEATURES:
            dm = (metrics.partition == "development") & (metrics.horizon_min == h) & (metrics.feature == f)
            d = metrics[dm].iloc[0]
            dev_pass = bool(d.n >= 20 and d.direction_ok and d.effect >= .30 - EPS and d.dev_block_rule_pass)
            metrics.loc[dm, "development_eligible"] = dev_pass
            oos = []
            for p in ("external", "reference_validation"):
                mm = (metrics.partition == p) & (metrics.horizon_min == h) & (metrics.feature == f)
                r = metrics[mm].iloc[0]
                ok = bool(dev_pass and r.n >= 8 and r.direction_ok and r.effect >= .10 - EPS)
                metrics.loc[mm, "oos_replication_pass"] = ok
                oos.append(ok)
            full = bool(dev_pass and all(oos))
            metrics.loc[(metrics.horizon_min == h) & (metrics.feature == f), "full_horizon_replication"] = full
            if full:
                replicated[f].append(h)

    supported_core = [f for f in CORE if all(h in replicated[f] for h in PRIMARY)]
    status = (
        "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_SUPPORTED"
        if supported_core else
        "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_INCONCLUSIVE"
    )

    prefix = "SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68"
    artifacts = []
    tables = {
        "EVENTS": events,
        "COVERAGE": coverage,
        "METRICS": metrics,
        "BLOCKS": blocks,
        "PARITY": parity,
        "RECONCILIATION": recon,
    }
    for suffix, df in tables.items():
        p = out / f"{prefix}_{suffix}.csv"
        df.to_csv(p, index=False)
        artifacts.append(p)

    sp = out / f"{prefix}_Status.txt"
    sp.write_text(status + "\n", encoding="utf-8")
    artifacts.append(sp)

    def fmt(v, d=3):
        if pd.isna(v): return "-"
        if np.isinf(v): return "inf"
        return f"{float(v):.{d}f}"

    rp = out / f"{prefix}_Result.md"
    lines = [
        "# SOL LONG 15:00 UTC M0 Reference-Invalidation Downside-Continuation Anatomy — A68 Result",
        "",
        f"**Gate status: {status}**",
        "",
        f"Raw SOLUSDT 5m coverage: **{100*float(raw_cov):.4f}%**.",
        "",
        "A68 measures only after the M0 invalidating candle is complete. Directional origin is the next 5m bar open; same-bar reversal is prohibited. No TP/SL economics are simulated.",
        "",
        "## Reconciliation",
        "",
        "| Partition | Parent | Losses | L0/M0 | Winners |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in recon.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.winner_n)} |")
    lines += ["", "## Causal-origin parity", "", "| Partition | L0/M0 | Parent exit = next-bar origin | Rate |",
              "|---|---:|---:|---:|"]
    for _, r in parity.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.l0_n)} | {int(r.parent_exit_equals_causal_origin_n)} | {100*float(r.parent_exit_equals_causal_origin_rate):.1f}% |")
    lines += ["", "## Forward-data coverage", "", "| Partition | Horizon | Eligible | L0/M0 | Coverage |",
              "|---|---:|---:|---:|---:|"]
    for _, r in coverage.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.horizon_min)}m | {int(r.eligible_n)} | {int(r.l0_total)} | {100*float(r.eligible_rate):.1f}% |")
    lines += ["", "## Directional anatomy", "",
              "| Partition | H | Feature | N | Median | Neutral | Centered | Effect | Dev blocks | Dev pass | OOS pass | Full |",
              "|---|---:|---|---:|---:|---:|---:|---:|---|---|---|---|"]
    for _, r in metrics.iterrows():
        bt = "-" if r.partition != "development" else f"{int(r.same_direction_dev_blocks)}/{int(r.adequate_dev_blocks)}"
        lines.append(
            f"| {SHOW[r.partition]} | {int(r.horizon_min)}m | `{r.feature}` | {int(r.n)} | {fmt(r['median'])} | {fmt(r.neutral_reference)} | {fmt(r.centered_median)} | {fmt(r.effect)} | {bt} | {'YES' if bool(r.development_eligible) else 'NO'} | {'YES' if bool(r.oos_replication_pass) else 'NO'} | {'YES' if bool(r.full_horizon_replication) else 'NO'} |"
        )
    lines += ["", "## Primary family gate", ""]
    for f in CORE:
        got = [h for h in replicated[f] if h in PRIMARY]
        lines.append(f"- `{f}` primary replicated horizons: {got}; strict 2-of-2 = {'YES' if f in supported_core else 'NO'}.")
    lines.append(f"- `short_capture_fraction` corroborative replicated horizons: {replicated['short_capture_fraction']}.")
    lines += ["", "## Interpretation boundary", "",
              "Supported means post-invalidation downside continuation replicated from a causal next-bar origin. It does not establish tradable reverse-short economics; stop, target, cost, sizing, leverage, and combined long-plus-short economics require a separate preregistered experiment.",
              "", "Research only. Live Baba Bot remains unchanged."]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    artifacts.append(rp)

    observed = {
        "execution_parent": EXECUTION_PARENT,
        "central_losses_total": 710,
        "l0_total": 76,
        "partitions": {
            "Development": {"central_losses": 357, "l0": 37},
            "External Validation": {"central_losses": 166, "l0": 13},
            "Reference Validation": {"central_losses": 187, "l0": 26},
        },
        "reconciliation": recon.to_dict(orient="records"),
        "coverage": coverage.to_dict(orient="records"),
        "causal_origin_parity": parity.to_dict(orient="records"),
        "metrics": metrics.to_dict(orient="records"),
    }
    summary = {
        "status": status,
        "supported_core_feature_families": supported_core,
        "full_replication_horizons": replicated,
        "raw_5m_coverage": float(raw_cov),
        "interpretation_boundary": "post_invalidation_directional_anatomy_only_no_short_economics",
    }
    return {
        "observed": observed,
        "summary": summary,
        "artifacts": [p.relative_to(root).as_posix() for p in artifacts],
    }
