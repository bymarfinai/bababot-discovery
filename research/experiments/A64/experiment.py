#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

BAR = pd.Timedelta(minutes=5)
AGES = (60, 120)
QUANTILES = (0.25, 0.50, 0.75)
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
NOTIONAL = 500.0
STRESS = 0.0005
EPS = 1e-12


def load_a55(root: Path):
    p = root / "research" / "sol_long_15utc_loss_confirmation_candle_a55.py"
    spec = importlib.util.spec_from_file_location("a64_a55", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def pos(idx, ts):
    ts = pd.Timestamp(ts)
    i = int(idx.searchsorted(ts, "left"))
    if i >= len(idx) or idx[i] != ts:
        raise RuntimeError(f"timestamp parity failure: {ts}")
    return i


def snapshot_last_bar(entry_ts, age):
    return pd.Timestamp(entry_ts) + pd.Timedelta(minutes=int(age)) - BAR


def execution_ts(entry_ts, age):
    return pd.Timestamp(entry_ts) + pd.Timedelta(minutes=int(age))


def prebreak_live_at_snapshot(r, age):
    last = snapshot_last_bar(r.entry_ts, age)
    execute = execution_ts(r.entry_ts, age)
    if pd.Timestamp(r.exit_ts) <= execute:
        return False
    if pd.notna(r.h1_break_ts) and pd.Timestamp(r.h1_break_ts) <= last:
        return False
    return True


def running_mae_R(market, r, age):
    idx = market["idx"]
    start = pd.Timestamp(r.entry_ts) + BAR
    last = snapshot_last_bar(r.entry_ts, age)
    a = pos(idx, start)
    b = pos(idx, last)
    if b < a:
        raise RuntimeError(f"empty A64 path {r.entry_ts} age={age}")
    lows = np.asarray(market["low"][a : b + 1], dtype=float)
    H = float(r.H)
    R = float(r.R)
    if R <= 0 or not len(lows):
        raise RuntimeError(f"invalid A64 range/path {r.entry_ts} age={age}")
    value = max(0.0, (H - float(lows.min())) / R)
    if not np.isfinite(value):
        raise RuntimeError(f"nonfinite A64 MAE {r.entry_ts} age={age}")
    return value


def nearest_rank(values, q):
    x = sorted(float(v) for v in values if np.isfinite(v))
    if not x:
        raise RuntimeError("nearest_rank received empty values")
    rank = max(1, int(math.ceil(float(q) * len(x))))
    return x[rank - 1], rank


def profit_factor(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl <= EPS:
        return np.inf if gp > EPS else np.nan
    return gp / gl


def max_dd(vals):
    x = pd.to_numeric(vals, errors="coerce").fillna(0.0).to_numpy(float)
    eq = np.concatenate([[0.0], np.cumsum(x)])
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq))


def max_loss_streak(vals):
    best = 0
    cur = 0
    for v in pd.to_numeric(vals, errors="coerce").fillna(0.0):
        if float(v) <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def baseline_row(r):
    return {
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_exit_reason": r.exit_reason,
        "mechanism": r.mechanism,
        "baseline_winner": bool(float(r.pnl) > 0),
        "baseline_pnl": float(r.pnl),
        "baseline_pnl_5bps": float(r.pnl_5bps),
        "triggered": False,
        "snapshot_age_min": np.nan,
        "threshold": np.nan,
        "running_mae_R": np.nan,
        "exit_ts": r.exit_ts,
        "exit_price": float(r.exit_price),
        "pnl": float(r.pnl),
        "pnl_5bps": float(r.pnl_5bps),
        "delta_pnl": 0.0,
        "delta_pnl_5bps": 0.0,
    }


def simulate_rule(market, q, age, threshold):
    idx = market["idx"]
    op = market["open"]
    rows = []
    for _, r in q.iterrows():
        z = baseline_row(r)
        z["snapshot_age_min"] = int(age)
        z["threshold"] = float(threshold)
        if prebreak_live_at_snapshot(r, age):
            mae = running_mae_R(market, r, age)
            z["running_mae_R"] = mae
            if mae + EPS >= float(threshold):
                xt = execution_ts(r.entry_ts, age)
                xi = pos(idx, xt)
                exit_price = float(op[xi])
                entry_price = float(r.entry_price)
                ret = exit_price / entry_price - 1.0
                pnl = ret * NOTIONAL
                pnl5 = (ret - STRESS) * NOTIONAL
                z.update(
                    triggered=True,
                    exit_ts=xt,
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_5bps=pnl5,
                    delta_pnl=pnl - float(r.pnl),
                    delta_pnl_5bps=pnl5 - float(r.pnl_5bps),
                )
        rows.append(z)
    return pd.DataFrame(rows).sort_values("entry_ts").reset_index(drop=True)


def metrics(q):
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    base_win = q.baseline_winner.astype(bool)
    l0 = q.mechanism.eq("M0_REFERENCE_INVALIDATION")
    other_loss = (~base_win) & (~l0)
    triggered = q.triggered.astype(bool)
    winner_delta = float(pd.to_numeric(q.loc[base_win, "delta_pnl"], errors="coerce").sum())
    l0_delta = float(pd.to_numeric(q.loc[l0, "delta_pnl"], errors="coerce").sum())
    other_loss_delta = float(pd.to_numeric(q.loc[other_loss, "delta_pnl"], errors="coerce").sum())
    return {
        "n": len(q),
        "wr": float((p > 0).mean()),
        "pf": profit_factor(p),
        "net": float(p.sum()),
        "expectancy": float(p.mean()),
        "max_dd": max_dd(p),
        "max_loss_streak": max_loss_streak(p),
        "wr_5bps": float((p5 > 0).mean()),
        "pf_5bps": profit_factor(p5),
        "net_5bps": float(p5.sum()),
        "expectancy_5bps": float(p5.mean()),
        "max_dd_5bps": max_dd(p5),
        "max_loss_streak_5bps": max_loss_streak(p5),
        "trigger_count": int(triggered.sum()),
        "trigger_rate": float(triggered.mean()),
        "l0_trigger_count": int((triggered & l0).sum()),
        "other_loss_trigger_count": int((triggered & other_loss).sum()),
        "winner_trigger_count": int((triggered & base_win).sum()),
        "winner_flips_nonpositive": int((base_win & (p <= 0)).sum()),
        "winner_pnl_delta": winner_delta,
        "winner_damage": max(0.0, -winner_delta),
        "l0_pnl_delta": l0_delta,
        "other_loss_pnl_delta": other_loss_delta,
        "delta_net": float(pd.to_numeric(q.delta_pnl, errors="coerce").sum()),
        "delta_net_5bps": float(pd.to_numeric(q.delta_pnl_5bps, errors="coerce").sum()),
    }


def baseline_metrics(q):
    rows = pd.DataFrame([baseline_row(r) for _, r in q.iterrows()])
    return metrics(rows)


def development_blocks(trades, candidate_id):
    rows = []
    for block in range(6):
        x = trades[pd.to_numeric(trades.dev_block, errors="coerce") == block]
        rows.append(
            {
                "candidate_id": candidate_id,
                "dev_block": block,
                "n": len(x),
                "delta_net": float(pd.to_numeric(x.delta_pnl, errors="coerce").sum()),
                "delta_net_5bps": float(pd.to_numeric(x.delta_pnl_5bps, errors="coerce").sum()),
            }
        )
    return rows


def dev_gate(m, base, pos_raw_blocks, pos_stress_blocks, source_n):
    clauses = {
        "source_support": source_n >= 20,
        "raw_net": m["net"] > base["net"] + EPS,
        "stress_net": m["net_5bps"] > base["net_5bps"] + EPS,
        "raw_pf": m["pf"] > base["pf"] + EPS,
        "stress_pf": m["pf_5bps"] > base["pf_5bps"] + EPS,
        "stress_wr": m["wr_5bps"] + EPS >= base["wr_5bps"],
        "raw_dd": m["max_dd"] <= base["max_dd"] + EPS,
        "raw_blocks": pos_raw_blocks >= 4,
        "stress_blocks": pos_stress_blocks >= 4,
        "l0_positive": m["l0_pnl_delta"] > EPS,
        "l0_gt_winner_damage": m["l0_pnl_delta"] > m["winner_damage"] + EPS,
    }
    return clauses, all(clauses.values())


def oos_gate(m, base):
    clauses = {
        "raw_net": m["net"] > base["net"] + EPS,
        "stress_net": m["net_5bps"] > base["net_5bps"] + EPS,
        "raw_pf": m["pf"] > base["pf"] + EPS,
        "stress_pf": m["pf_5bps"] > base["pf_5bps"] + EPS,
        "stress_wr": m["wr_5bps"] + EPS >= base["wr_5bps"],
        "raw_dd": m["max_dd"] <= base["max_dd"] + EPS,
        "l0_positive": m["l0_pnl_delta"] > EPS,
        "l0_gt_winner_damage": m["l0_pnl_delta"] > m["winner_damage"] + EPS,
    }
    return clauses, all(clauses.values())


def fmoney(v):
    return f"${float(v):.2f}"


def fnum(v, d=3):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def fpct(v):
    return f"{100.0 * float(v):.1f}%"


def run(context):
    root = Path(context["repo_root"])
    out = Path(context["results_dir"])
    out.mkdir(parents=True, exist_ok=True)

    a55 = load_a55(root)
    raw5, coverage = a55.a2.a1.load5()
    market = a55.a2.make_market_with_open(raw5)
    parents = {p: a55.parent(market, p) for p in PARTS}

    recon_rows = []
    errors = []
    for p, q in parents.items():
        parent_n = len(q)
        loss_n = int((~q.economic_win).sum())
        l0_n = int(q.mechanism.eq("M0_REFERENCE_INVALIDATION").sum())
        winner_n = int((pd.to_numeric(q.pnl, errors="coerce") > 0).sum())
        recon_rows.append({"partition": p, "parent_n": parent_n, "loss_n": loss_n, "l0_n": l0_n, "winner_n": winner_n})
        if parent_n != PARENT[p]: errors.append(f"{p} parent {parent_n}!={PARENT[p]}")
        if loss_n != LOSSES[p]: errors.append(f"{p} losses {loss_n}!={LOSSES[p]}")
        if l0_n != L0[p]: errors.append(f"{p} L0 {l0_n}!={L0[p]}")
        if winner_n != WINNERS[p]: errors.append(f"{p} winners {winner_n}!={WINNERS[p]}")
        # Frozen baseline values must be internally identical to themselves under the A64 envelope.
        for _, r in q.iterrows():
            if not np.isfinite(float(r.pnl)) or not np.isfinite(float(r.pnl_5bps)):
                errors.append(f"{p} nonfinite parent PnL {r.entry_ts}")
    if errors:
        raise RuntimeError("; ".join(errors[:30]))
    recon = pd.DataFrame(recon_rows)

    dev = parents["development"]
    base_dev = baseline_metrics(dev)

    threshold_rows = []
    candidate_defs = []
    for age in AGES:
        source = []
        for _, r in dev[dev.mechanism.eq("M0_REFERENCE_INVALIDATION")].iterrows():
            if prebreak_live_at_snapshot(r, age):
                source.append(running_mae_R(market, r, age))
        if len(source) < 20:
            threshold_rows.append({"snapshot_age_min": age, "source_n": len(source), "quantile": np.nan, "rank": np.nan, "threshold": np.nan, "eligible": False})
            continue
        seen = set()
        for qtile in QUANTILES:
            threshold, rank = nearest_rank(source, qtile)
            key = round(float(threshold), 15)
            duplicate = key in seen
            threshold_rows.append({"snapshot_age_min": age, "source_n": len(source), "quantile": qtile, "rank": rank, "threshold": threshold, "eligible": True, "duplicate_threshold": duplicate})
            if duplicate:
                continue
            seen.add(key)
            candidate_defs.append({"age": age, "quantile": qtile, "threshold": threshold, "source_n": len(source)})
    thresholds = pd.DataFrame(threshold_rows)

    candidate_rows = []
    block_rows = []
    dev_trade_rows = []
    candidate_metrics = {}
    for c in candidate_defs:
        cid = f"A{c['age']}_Q{int(round(c['quantile'] * 100)):02d}"
        trades = simulate_rule(market, dev, c["age"], c["threshold"])
        for row in trades.to_dict("records"):
            row["candidate_id"] = cid
            dev_trade_rows.append(row)
        m = metrics(trades)
        br = development_blocks(trades, cid)
        block_rows.extend(br)
        pos_raw = sum(1 for r in br if r["delta_net"] > EPS)
        pos_stress = sum(1 for r in br if r["delta_net_5bps"] > EPS)
        clauses, passed = dev_gate(m, base_dev, pos_raw, pos_stress, c["source_n"])
        row = {
            "candidate_id": cid,
            "snapshot_age_min": c["age"],
            "source_quantile": c["quantile"],
            "source_n": c["source_n"],
            "threshold": c["threshold"],
            **m,
            "positive_raw_blocks": pos_raw,
            "positive_stress_blocks": pos_stress,
            **{f"gate__{k}": v for k, v in clauses.items()},
            "development_gate_pass": passed,
        }
        candidate_rows.append(row)
        candidate_metrics[cid] = (row, trades)

    candidates = pd.DataFrame(candidate_rows)
    blocks = pd.DataFrame(block_rows)
    dev_trades = pd.DataFrame(dev_trade_rows)
    passing = candidates[candidates.development_gate_pass.astype(bool)].copy() if not candidates.empty else pd.DataFrame()

    selected = None
    if not passing.empty:
        passing = passing.sort_values(
            ["delta_net_5bps", "delta_net", "winner_damage", "snapshot_age_min", "threshold"],
            ascending=[False, False, True, True, False],
            kind="mergesort",
        )
        selected = passing.iloc[0].to_dict()

    oos_metric_rows = []
    selected_trade_rows = []
    oos_pass = {}
    if selected is not None:
        cid = selected["candidate_id"]
        age = int(selected["snapshot_age_min"])
        threshold = float(selected["threshold"])
        # Persist the selected Development trade set too.
        for row in candidate_metrics[cid][1].to_dict("records"):
            row["candidate_id"] = cid
            selected_trade_rows.append(row)
        for p in ("external", "reference_validation"):
            base = baseline_metrics(parents[p])
            trades = simulate_rule(market, parents[p], age, threshold)
            m = metrics(trades)
            clauses, passed = oos_gate(m, base)
            oos_pass[p] = passed
            oos_metric_rows.append({"partition": p, "variant": "BASELINE", **base, "gate_pass": np.nan})
            oos_metric_rows.append({"partition": p, "variant": cid, **m, **{f"gate__{k}": v for k, v in clauses.items()}, "gate_pass": passed})
            for row in trades.to_dict("records"):
                row["candidate_id"] = cid
                selected_trade_rows.append(row)
        status = (
            "SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_SUPPORTED"
            if all(oos_pass.values())
            else "SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_OOS"
        )
    else:
        status = "SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_DEVELOPMENT"

    oos_metrics = pd.DataFrame(oos_metric_rows)
    selected_trades = pd.DataFrame(selected_trade_rows)

    artifacts = []
    frames = {
        "RECONCILIATION": recon,
        "THRESHOLDS": thresholds,
        "DEVELOPMENT_CANDIDATES": candidates,
        "DEVELOPMENT_BLOCKS": blocks,
        "DEVELOPMENT_CANDIDATE_TRADES": dev_trades,
    }
    if selected is not None:
        frames["OOS_METRICS"] = oos_metrics
        frames["SELECTED_TRADES"] = selected_trades
    for name, df in frames.items():
        path = out / f"SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_{name}.csv"
        df.to_csv(path, index=False)
        artifacts.append(path)

    status_path = out / "SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_Status.txt"
    status_path.write_text(status + "\n")
    artifacts.append(status_path)

    result_path = out / "SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_Result.md"
    lines = [
        "# SOL LONG 15:00 UTC L0 Early MAE Economic Translation — A64 Result",
        "",
        f"**Gate status: {status}**",
        "",
        f"Raw SOLUSDT 5m coverage: **{100.0 * coverage:.4f}%**.",
        "",
        "A64 is the preregistered economic translation of the A62+A63 `running_mae_R` mechanism-specific signal. Threshold learning is Development-only; OOS is opened only if a Development candidate passes every frozen gate.",
        "",
        "## Reconciliation",
        "",
        "| Partition | Parent | Losses | L0/M0 | Raw winners |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in recon.iterrows():
        lines.append(f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} | {int(r.winner_n)} |")
    lines += [
        "",
        "## Development threshold family",
        "",
        "| Age | Source N | Quantile | Rank | Threshold running_mae_R | Duplicate |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in thresholds.iterrows():
        if pd.isna(r.get("quantile")):
            lines.append(f"| {int(r.snapshot_age_min)}m | {int(r.source_n)} | - | - | - | - |")
        else:
            lines.append(f"| {int(r.snapshot_age_min)}m | {int(r.source_n)} | Q{int(round(100*r.quantile))} | {int(r['rank'])} | {fnum(r.threshold, 6)} | {'YES' if bool(r.get('duplicate_threshold', False)) else 'NO'} |")
    lines += [
        "",
        "## Development candidate economics",
        "",
        "| Candidate | Threshold | Triggers | L0 trig | Winners trig | Net Δ | PF | 5bps Net Δ | 5bps PF | DD | L0 Δ | Winner Δ | Blocks raw/stress | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in candidates.iterrows():
        lines.append(
            f"| {r.candidate_id} | {fnum(r.threshold,6)} | {int(r.trigger_count)} | {int(r.l0_trigger_count)} | {int(r.winner_trigger_count)} | {fmoney(r.delta_net)} | {fnum(r.pf,2)} | {fmoney(r.delta_net_5bps)} | {fnum(r.pf_5bps,2)} | {fmoney(r.max_dd)} | {fmoney(r.l0_pnl_delta)} | {fmoney(r.winner_pnl_delta)} | {int(r.positive_raw_blocks)}/6 / {int(r.positive_stress_blocks)}/6 | {'PASS' if r.development_gate_pass else 'FAIL'} |"
        )
    if selected is None:
        lines += [
            "",
            "## Development decision",
            "",
            "No preregistered Development candidate passed every gate. Per protocol, External and Reference Validation intervention economics were not computed and cannot be used to rescue A64.",
        ]
    else:
        lines += [
            "",
            "## Frozen Development-selected rule",
            "",
            f"Selected `{selected['candidate_id']}`: age **{int(selected['snapshot_age_min'])}m**, exact threshold **{float(selected['threshold']):.9f} running_mae_R**. This rule was frozen by the preregistered Development ranking before OOS intervention computation.",
            "",
            "## OOS confirmation",
            "",
            "| Partition | Variant | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net | DD | Triggers | L0 Δ | Winner Δ | ΔNet | Gate |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for _, r in oos_metrics.iterrows():
            gate = "-" if pd.isna(r.gate_pass) else ("PASS" if bool(r.gate_pass) else "FAIL")
            lines.append(
                f"| {SHOW[r.partition]} | {r.variant} | {fpct(r.wr)} | {fnum(r.pf,2)} | {fmoney(r.net)} | {fpct(r.wr_5bps)} | {fnum(r.pf_5bps,2)} | {fmoney(r.net_5bps)} | {fmoney(r.max_dd)} | {int(r.trigger_count)} | {fmoney(r.l0_pnl_delta)} | {fmoney(r.winner_pnl_delta)} | {fmoney(r.delta_net)} | {gate} |"
            )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "A64 judges economic feasibility, not WR aesthetics. A rejection does not authorize threshold/age rescue, partial sizing, re-arm, or feature combination. A support result would still require a separate deployment/forward-validation decision before live use.",
        "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    result_path.write_text("\n".join(lines) + "\n")
    artifacts.append(result_path)

    observed = {
        "execution_parent": {"range": "R360", "hour": "15UTC", "entry": "E0_RESTING_H", "target": "E40"},
        "central_losses_total": 710,
        "l0_total": 76,
        "partitions": {
            "Development": {"central_losses": 357, "l0": 37, "parent": 601, "winners": 244},
            "External Validation": {"central_losses": 166, "l0": 13, "parent": 281, "winners": 115},
            "Reference Validation": {"central_losses": 187, "l0": 26, "parent": 337, "winners": 150},
        },
    }
    summary = {
        "gate_status": status,
        "market_coverage": float(coverage),
        "development_candidate_count": int(len(candidates)),
        "development_pass_count": int(candidates.development_gate_pass.sum()) if not candidates.empty else 0,
        "selected_rule": None if selected is None else {
            "candidate_id": selected["candidate_id"],
            "snapshot_age_min": int(selected["snapshot_age_min"]),
            "threshold": float(selected["threshold"]),
        },
        "oos_gate_pass": oos_pass,
        "interpretation_boundary": "economic_feasibility_only_no_live_authorization",
    }
    return {
        "observed": observed,
        "summary": summary,
        "artifacts": [p.relative_to(root).as_posix() for p in artifacts],
    }
