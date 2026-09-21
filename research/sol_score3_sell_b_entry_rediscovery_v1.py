#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_structural_liquidity_detector_v3 as v3
import sol_adaptive_entry_v1_actionable as e1
import sol_adaptive_sl_v1 as sl
import sol_adaptive_risk_manager_v1 as rm

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SCORE3_SELL_B_ENTRY_REDISCOVERY_V1"
CONSTRUCTION_END = pd.Timestamp("2025-01-01", tz="UTC")
CONFIRM_END = pd.Timestamp("2026-01-01", tz="UTC")

VARIANTS = tuple(e1.VARIANTS)
CURRENT = "FIVE_MIN_REVERSAL_BREAK"


def pf(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_dd(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def b_population(x5, end_time, years):
    pop, h1 = e1.actionable_detector_population(x5, end_time, years)
    for c in ("cond_A", "cond_B", "cond_C", "cond_D"):
        pop[c] = pd.to_numeric(pop[c], errors="coerce")
    z = pop[
        (pd.to_numeric(pop.anatomy_score, errors="coerce") == 3)
        & pop.side.astype(str).eq("SELL_SIDE")
        & pop.cond_A.eq(1)
        & pop.cond_B.eq(0)
        & pop.cond_C.eq(1)
        & pop.cond_D.eq(1)
    ].copy().reset_index(drop=True)
    x = x5[x5.index < end_time].copy()
    return z, h1, x


def simulate_variant(pop, h1, x5, variant):
    signals = e1.eval_variant(pop, h1, x5, variant)
    if signals.empty:
        return signals, pd.DataFrame()

    signals = signals.copy()
    signals["assigned_route"] = "SCORE3_B_" + variant
    filled = signals[signals.filled == 1].copy().reset_index(drop=True)
    if filled.empty:
        return signals, pd.DataFrame()

    # eval_variant intentionally emits entry fields only. Re-attach the
    # structural metadata required by the frozen RECLAIM_EXTREME stop engine.
    meta_cols = [
        "candidate_id", "level", "sweep_extreme", "reclaim_i_h1",
        "resolution_i_h1", "resolution_time"
    ]
    meta = pop[meta_cols].drop_duplicates("candidate_id")
    filled = filled.merge(meta, on="candidate_id", how="left", validate="one_to_one")

    stops = sl.evaluate_policy(filled, pop, h1, x5, "RECLAIM_EXTREME")
    if stops.empty:
        return signals, pd.DataFrame()

    keep = ["candidate_id", "stop_price", "initial_risk_range_units", "outcome_known_time"]
    z = filled.merge(stops[keep], on="candidate_id", how="inner", validate="one_to_one")
    z["initial_risk_price"] = (
        pd.to_numeric(z.stop_price, errors="coerce")
        - pd.to_numeric(z.entry_price, errors="coerce")
    ).abs()

    trades = rm.simulate_policy(z, x5, "STATIC_RECLAIM_EXTREME")
    if len(trades):
        trades = trades.copy()
        trades["variant"] = variant
    return signals, trades


def friction_metrics(trades, bps):
    if trades is None or trades.empty:
        return {"mean": np.nan, "pf": np.nan, "cum": 0.0, "dd": np.nan}
    gross = pd.to_numeric(trades.realized_r, errors="coerce")
    entry = pd.to_numeric(trades.entry_price, errors="coerce")
    risk = pd.to_numeric(trades.initial_risk_price, errors="coerce")
    net = gross - (entry * (bps / 10000.0)) / risk
    return {
        "mean": float(net.mean()),
        "pf": float(pf(net)),
        "cum": float(net.sum()),
        "dd": float(max_dd(net)),
    }


def route_metrics(signals, trades, baseline_winner_ids=None):
    filled = signals[signals.filled == 1].copy() if len(signals) else signals.copy()
    positives = signals[signals.event_label == 1].copy() if len(signals) else signals.copy()
    pos_filled = filled[filled.event_label == 1].copy() if len(filled) else filled.copy()
    r = pd.to_numeric(trades.realized_r, errors="coerce") if len(trades) else pd.Series(dtype=float)

    years_positive = 0
    if len(trades):
        z = trades.copy()
        z["year"] = pd.to_datetime(z.entry_time, utc=True).dt.year.astype(int)
        y = z.groupby("year").realized_r.sum()
        years_positive = int((y > 0).sum())

    if baseline_winner_ids is None:
        winner_retention = np.nan
    else:
        denom = len(baseline_winner_ids)
        if denom == 0:
            winner_retention = np.nan
        else:
            cand_wins = set(
                trades.loc[pd.to_numeric(trades.realized_r, errors="coerce") > 0, "candidate_id"].astype(str)
            ) if len(trades) else set()
            winner_retention = len(cand_wins.intersection(baseline_winner_ids)) / denom

    f10 = friction_metrics(trades, 10)
    f20 = friction_metrics(trades, 20)

    return {
        "signal_n": int(len(signals)),
        "filled_n": int(len(filled)),
        "fill_rate": float(len(filled) / len(signals)) if len(signals) else np.nan,
        "structural_positive_n": int(len(positives)),
        "structural_positive_filled_n": int(len(pos_filled)),
        "positive_capture": float(len(pos_filled) / len(positives)) if len(positives) else np.nan,
        "event_rate_filled": float(filled.event_label.mean()) if len(filled) else np.nan,
        "gross_win_n": int((r > 0).sum()) if len(r) else 0,
        "gross_wr": float((r > 0).mean()) if len(r) else np.nan,
        "gross_mean_r": float(r.mean()) if len(r) else np.nan,
        "gross_pf": float(pf(r)) if len(r) else np.nan,
        "gross_cum_r": float(r.sum()) if len(r) else 0.0,
        "gross_max_dd_r": float(max_dd(r)) if len(r) else np.nan,
        "positive_years": years_positive,
        "baseline_winner_retention": winner_retention,
        "net10_mean_r": f10["mean"],
        "net10_pf": f10["pf"],
        "net10_cum_r": f10["cum"],
        "net10_max_dd_r": f10["dd"],
        "net20_mean_r": f20["mean"],
        "net20_pf": f20["pf"],
        "net20_cum_r": f20["cum"],
        "net20_max_dd_r": f20["dd"],
    }


def construction():
    x5, coverage = v3.load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    pop, h1, x = b_population(x5, CONSTRUCTION_END, [2020, 2021, 2022, 2023, 2024])
    by_variant = {}
    signal_parts = []
    trade_parts = []

    for variant in VARIANTS:
        sig, tr = simulate_variant(pop, h1, x, variant)
        by_variant[variant] = (sig, tr)
        if len(sig):
            q = sig.copy()
            q["variant_eval"] = variant
            signal_parts.append(q)
        if len(tr):
            trade_parts.append(tr)

    base_sig, base_tr = by_variant[CURRENT]
    baseline_winner_ids = set(
        base_tr.loc[pd.to_numeric(base_tr.realized_r, errors="coerce") > 0, "candidate_id"].astype(str)
    )
    base_m = route_metrics(base_sig, base_tr, baseline_winner_ids)

    rows = []
    for variant in VARIANTS:
        sig, tr = by_variant[variant]
        m = route_metrics(sig, tr, baseline_winner_ids)
        m["variant"] = variant
        m["filled_retention_vs_current"] = (
            m["filled_n"] / base_m["filled_n"] if base_m["filled_n"] else np.nan
        )
        m["eligible"] = bool(
            np.isfinite(m["filled_retention_vs_current"]) and m["filled_retention_vs_current"] >= .70
            and np.isfinite(m["positive_capture"]) and m["positive_capture"] >= .70
            and np.isfinite(m["baseline_winner_retention"]) and m["baseline_winner_retention"] >= .75
            and np.isfinite(m["gross_mean_r"]) and m["gross_mean_r"] > 0
            and np.isfinite(m["net10_mean_r"]) and m["net10_mean_r"] > 0
            and np.isfinite(m["net10_pf"]) and m["net10_pf"] >= 1.10
            and np.isfinite(m["net20_mean_r"]) and m["net20_mean_r"] > 0
            and np.isfinite(m["net20_pf"]) and m["net20_pf"] >= 1.05
            and int(m["positive_years"]) >= 4
        )
        rows.append(m)

    mt = pd.DataFrame(rows)
    elig = mt[mt.eligible].copy()
    winner = None
    if len(elig):
        elig = elig.sort_values(
            ["net20_mean_r", "net20_pf", "baseline_winner_retention", "filled_n", "variant"],
            ascending=[False, False, False, False, True],
        )
        winner = str(elig.iloc[0].variant)

    signals_all = pd.concat(signal_parts, ignore_index=True) if signal_parts else pd.DataFrame()
    trades_all = pd.concat(trade_parts, ignore_index=True) if trade_parts else pd.DataFrame()
    return x5, coverage, mt, signals_all, trades_all, winner


def confirmation(x5, winner):
    pop, h1, x = b_population(x5, CONFIRM_END, [2025])

    base_sig, base_tr = simulate_variant(pop, h1, x, CURRENT)
    winner_sig, winner_tr = simulate_variant(pop, h1, x, winner)

    baseline_winner_ids = set(
        base_tr.loc[pd.to_numeric(base_tr.realized_r, errors="coerce") > 0, "candidate_id"].astype(str)
    )
    bm = route_metrics(base_sig, base_tr, baseline_winner_ids)
    wm = route_metrics(winner_sig, winner_tr, baseline_winner_ids)
    wm["variant"] = winner
    wm["filled_retention_vs_current"] = wm["filled_n"] / bm["filled_n"] if bm["filled_n"] else np.nan

    gates = {
        "signal_n_ge_10": wm["signal_n"] >= 10,
        "filled_n_ge_8": wm["filled_n"] >= 8,
        "positive_capture_ge_60pct": bool(np.isfinite(wm["positive_capture"]) and wm["positive_capture"] >= .60),
        "current_winner_retention_ge_70pct": bool(np.isfinite(wm["baseline_winner_retention"]) and wm["baseline_winner_retention"] >= .70),
        "gross_mean_r_gt_0": bool(np.isfinite(wm["gross_mean_r"]) and wm["gross_mean_r"] > 0),
        "net10_mean_r_gt_0": bool(np.isfinite(wm["net10_mean_r"]) and wm["net10_mean_r"] > 0),
        "net10_pf_ge_1_05": bool(np.isfinite(wm["net10_pf"]) and wm["net10_pf"] >= 1.05),
        "net20_mean_r_ge_0": bool(np.isfinite(wm["net20_mean_r"]) and wm["net20_mean_r"] >= 0),
        "net20_pf_ge_1_00": bool(np.isfinite(wm["net20_pf"]) and wm["net20_pf"] >= 1.00),
    }
    return bm, wm, gates, base_tr, winner_tr


def fmt(v, d=3):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v:.{d}f}"


def pct(v):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{100*v:.2f}%"


def main():
    x5, coverage, cmetrics, csignals, ctrades, winner = construction()

    cmetrics.to_csv(ROOT / f"{PFX}_ConstructionMetrics.csv", index=False)
    csignals.to_csv(ROOT / f"{PFX}_ConstructionSignals.csv", index=False)
    ctrades.to_csv(ROOT / f"{PFX}_ConstructionTrades.csv", index=False)

    lines = [
        "# SOL Score-3 SELL Missing-B Entry Rediscovery V1 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Scope: Score-3 SELL_SIDE with only condition B missing.",
        "- Entry variants are pre-existing; SL and structural-completion exit are frozen.",
        "- Route selection uses 2020-2024 only.",
        "",
        "## Construction 2020-2024",
        "",
        "| Variant | Filled | Pos capture | Win retention | Gross mean R | PF | 10bps mean/PF | 20bps mean/PF | +Years | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in cmetrics.iterrows():
        lines.append(
            f"| {r.variant} | {int(r.filled_n)} | {pct(r.positive_capture)} | {pct(r.baseline_winner_retention)} | "
            f"{fmt(r.gross_mean_r)} | {fmt(r.gross_pf)} | {fmt(r.net10_mean_r)}/{fmt(r.net10_pf)} | "
            f"{fmt(r.net20_mean_r)}/{fmt(r.net20_pf)} | {int(r.positive_years)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )

    if winner is None:
        verdict = "NO_MISSING_B_ENTRY_ROUTE_CONSTRUCTION_WINNER"
        lines += [
            "",
            f"**VERDICT: {verdict}**",
            "",
            "No route passed every frozen construction gate. Per preregistration, 2025 was not opened.",
        ]
        (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
        pd.DataFrame([{"coverage": coverage, "winner": "", "verdict": verdict}]).to_csv(
            ROOT / f"{PFX}_Summary.csv", index=False
        )
        print("\n".join(lines))
        return

    bm, wm, gates, base25, winner25 = confirmation(x5, winner)
    pd.DataFrame([{"route": "CURRENT_" + CURRENT, **bm}, {"route": "WINNER_" + winner, **wm}]).to_csv(
        ROOT / f"{PFX}_Confirmation2025Metrics.csv", index=False
    )
    base25.assign(eval_route="CURRENT_" + CURRENT).to_csv(
        ROOT / f"{PFX}_Confirmation2025CurrentTrades.csv", index=False
    )
    winner25.assign(eval_route="WINNER_" + winner).to_csv(
        ROOT / f"{PFX}_Confirmation2025WinnerTrades.csv", index=False
    )
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(
        ROOT / f"{PFX}_Confirmation2025Gates.csv", index=False
    )

    passed = all(gates.values())
    verdict = "MISSING_B_ENTRY_ROUTE_RETROSPECTIVELY_SUPPORTED_2025" if passed else "MISSING_B_ENTRY_ROUTE_NOT_SUPPORTED_2025"

    lines += [
        "",
        f"## Frozen construction winner: **{winner}**",
        "",
        "## 2025 confirmation",
        "",
        f"- Current route gross mean/PF: **{fmt(bm['gross_mean_r'])} / {fmt(bm['gross_pf'])}**",
        f"- Winner gross mean/PF: **{fmt(wm['gross_mean_r'])} / {fmt(wm['gross_pf'])}**",
        f"- Winner positive-event capture: **{pct(wm['positive_capture'])}**",
        f"- Current-winner retention: **{pct(wm['baseline_winner_retention'])}**",
        f"- Winner 10 bps mean/PF: **{fmt(wm['net10_mean_r'])} / {fmt(wm['net10_pf'])}**",
        f"- Winner 20 bps mean/PF: **{fmt(wm['net20_mean_r'])} / {fmt(wm['net20_pf'])}**",
        "",
        "### Confirmation gates",
        "",
    ]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines += [
        "",
        f"**VERDICT: {verdict}**",
        "",
        "No 2026 data is opened by this V1 experiment.",
    ]

    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    pd.DataFrame([{
        "coverage": coverage,
        "winner": winner,
        "confirmation_gates_passed": sum(bool(v) for v in gates.values()),
        "confirmation_gates_total": len(gates),
        "verdict": verdict,
    }]).to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
