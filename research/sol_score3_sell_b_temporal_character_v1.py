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
PFX = "SOL_SCORE3_SELL_B_TEMPORAL_CHARACTER_V1"

DISCOVERY_END = pd.Timestamp("2026-01-01 00:00:00", tz="UTC")
OBS_END = pd.Timestamp("2026-09-21 00:00:00", tz="UTC")
DISCOVERY_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
HOLDOUT_YEARS = [2026]

ENTRY_VARIANT = "FIVE_MIN_REVERSAL_BREAK"
STOP_POLICY = "RECLAIM_EXTREME"
RISK_POLICY = "STATIC_RECLAIM_EXTREME"
TEMPORAL_SCORE_MIN = 2


def pf(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    gp = float(s[s > 0].sum())
    gl = float(-s[s < 0].sum())
    if gl <= 0:
        return math.inf if gp > 0 else np.nan
    return gp / gl


def max_dd(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def missing_b_population(x5, end_time, years):
    pop, h1 = e1.actionable_detector_population(x5, end_time, years)
    for c in ("cond_A", "cond_B", "cond_C", "cond_D", "approach_bars", "reclaim_delay_h1_bars"):
        pop[c] = pd.to_numeric(pop[c], errors="coerce")

    cohort = pop[
        (pd.to_numeric(pop.anatomy_score, errors="coerce") == 3)
        & pop.side.astype(str).eq("SELL_SIDE")
        & pop.cond_A.eq(1)
        & pop.cond_B.eq(0)
        & pop.cond_C.eq(1)
        & pop.cond_D.eq(1)
    ].copy().reset_index(drop=True)

    cohort["temporal_confirmation_score"] = (
        pd.to_numeric(cohort.approach_bars, errors="coerce")
        + pd.to_numeric(cohort.reclaim_delay_h1_bars, errors="coerce")
    )
    cohort["temporal_character"] = (
        cohort.temporal_confirmation_score >= TEMPORAL_SCORE_MIN
    ).astype(int)

    x = x5[x5.index < end_time].copy()
    return cohort, h1, x


def current_route_trades(pop, h1, x5):
    if pop.empty:
        return pd.DataFrame(), pd.DataFrame()

    signals = e1.eval_variant(pop, h1, x5, ENTRY_VARIANT)
    signals = signals.copy()
    signals["assigned_route"] = "SCORE3_FIVE_MIN_REVERSAL_BREAK"

    filled = signals[signals.filled == 1].copy().reset_index(drop=True)
    if filled.empty:
        return signals, pd.DataFrame()

    meta_cols = [
        "candidate_id", "level", "sweep_extreme", "reclaim_i_h1",
        "resolution_i_h1", "resolution_time",
        "cond_A", "cond_B", "cond_C", "cond_D",
        "approach_bars", "reclaim_delay_h1_bars",
        "temporal_confirmation_score", "temporal_character",
    ]
    meta = pop[meta_cols].drop_duplicates("candidate_id")
    filled = filled.merge(meta, on="candidate_id", how="left", validate="one_to_one")

    stops = sl.evaluate_policy(filled, pop, h1, x5, STOP_POLICY)
    if stops.empty:
        return signals, pd.DataFrame()

    stop_cols = ["candidate_id", "stop_price", "initial_risk_range_units", "outcome_known_time"]
    z = filled.merge(stops[stop_cols], on="candidate_id", how="inner", validate="one_to_one")
    z["initial_risk_price"] = (
        pd.to_numeric(z.stop_price, errors="coerce")
        - pd.to_numeric(z.entry_price, errors="coerce")
    ).abs()

    trades = rm.simulate_policy(z, x5, RISK_POLICY)
    if trades.empty:
        return signals, trades

    char = z[
        ["candidate_id", "approach_bars", "reclaim_delay_h1_bars",
         "temporal_confirmation_score", "temporal_character"]
    ].drop_duplicates("candidate_id")
    trades = trades.merge(char, on="candidate_id", how="left", validate="one_to_one")
    trades = trades.sort_values(["entry_time", "candidate_id"]).reset_index(drop=True)
    return signals, trades


def friction_series(trades, bps):
    gross = pd.to_numeric(trades.realized_r, errors="coerce")
    entry = pd.to_numeric(trades.entry_price, errors="coerce")
    risk = pd.to_numeric(trades.initial_risk_price, errors="coerce")
    return gross - (entry * (bps / 10000.0)) / risk


def metrics(trades):
    if trades is None or trades.empty:
        return {
            "n": 0, "event_rate": np.nan, "win_rate": np.nan,
            "mean_r": np.nan, "pf_r": np.nan, "cum_r": 0.0,
            "max_dd_r": np.nan,
            "net10_mean_r": np.nan, "net10_pf": np.nan,
            "net20_mean_r": np.nan, "net20_pf": np.nan,
        }

    r = pd.to_numeric(trades.realized_r, errors="coerce")
    n10 = friction_series(trades, 10)
    n20 = friction_series(trades, 20)
    return {
        "n": int(len(trades)),
        "event_rate": float(pd.to_numeric(trades.event_label, errors="coerce").mean()),
        "win_rate": float((r > 0).mean()),
        "mean_r": float(r.mean()),
        "pf_r": float(pf(r)),
        "cum_r": float(r.sum()),
        "max_dd_r": float(max_dd(r)),
        "net10_mean_r": float(n10.mean()),
        "net10_pf": float(pf(n10)),
        "net20_mean_r": float(n20.mean()),
        "net20_pf": float(pf(n20)),
    }


def audit_period(x5, end_time, years, label):
    pop, h1, x = missing_b_population(x5, end_time, years)
    signals, trades = current_route_trades(pop, h1, x)

    baseline = trades.copy()
    selected = trades[
        pd.to_numeric(trades.temporal_confirmation_score, errors="coerce") >= TEMPORAL_SCORE_MIN
    ].copy()

    bm = metrics(baseline)
    sm = metrics(selected)

    signal_ids = set(signals.loc[signals.filled == 1, "candidate_id"].astype(str)) if len(signals) else set()
    pop_filled = pop[pop.candidate_id.astype(str).isin(signal_ids)].copy()
    selected_pop_filled = pop_filled[
        pd.to_numeric(pop_filled.temporal_confirmation_score, errors="coerce") >= TEMPORAL_SCORE_MIN
    ].copy()

    row = {
        "period": label,
        "population_n": int(len(pop)),
        "filled_population_n": int(len(pop_filled)),
        "selected_filled_population_n": int(len(selected_pop_filled)),
        "retention": float(len(selected) / len(baseline)) if len(baseline) else np.nan,
        "event_capture": (
            float(pd.to_numeric(selected.event_label, errors="coerce").sum())
            / float(pd.to_numeric(baseline.event_label, errors="coerce").sum())
            if len(baseline) and pd.to_numeric(baseline.event_label, errors="coerce").sum() > 0
            else np.nan
        ),
        "gross_winner_retention": (
            float((pd.to_numeric(selected.realized_r, errors="coerce") > 0).sum())
            / float((pd.to_numeric(baseline.realized_r, errors="coerce") > 0).sum())
            if len(baseline) and (pd.to_numeric(baseline.realized_r, errors="coerce") > 0).sum() > 0
            else np.nan
        ),
        **{f"baseline_{k}": v for k, v in bm.items()},
        **{f"selected_{k}": v for k, v in sm.items()},
    }

    baseline["cohort"] = "BASELINE_MISSING_B"
    selected["cohort"] = "TEMPORAL_SCORE_GE_2"
    return pop, signals, baseline, selected, row


def fmt(v, d=3):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v:.{d}f}"


def pct(v):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{100*v:.2f}%"


def main():
    base = v3.wf1.v3.v1.base
    base.END = OBS_END

    x5, coverage = v3.load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    dpop, dsig, dbase, dsel, drow = audit_period(
        x5, DISCOVERY_END, DISCOVERY_YEARS, "DISCOVERY_2020_2025"
    )

    # Rule is already frozen before this call. 2026 is opened only here.
    hpop, hsig, hbase, hsel, hrow = audit_period(
        x5, OBS_END, HOLDOUT_YEARS, "UNTOUCHED_2026_TO_2026_09_21"
    )

    sample_gates = {
        "baseline_missing_b_n_ge_5": int(hrow["baseline_n"]) >= 5,
        "selected_n_ge_5": int(hrow["selected_n"]) >= 5,
        "selected_retention_ge_40pct": bool(np.isfinite(hrow["retention"]) and hrow["retention"] >= .40),
    }
    structural_gates = {
        "selected_event_rate_ge_65pct": bool(
            np.isfinite(hrow["selected_event_rate"]) and hrow["selected_event_rate"] >= .65
        ),
        "selected_event_rate_gt_baseline": bool(
            np.isfinite(hrow["selected_event_rate"])
            and np.isfinite(hrow["baseline_event_rate"])
            and hrow["selected_event_rate"] > hrow["baseline_event_rate"]
        ),
    }
    trading_gates = {
        "gross_wr_ge_60pct": bool(np.isfinite(hrow["selected_win_rate"]) and hrow["selected_win_rate"] >= .60),
        "gross_mean_r_gt_0": bool(np.isfinite(hrow["selected_mean_r"]) and hrow["selected_mean_r"] > 0),
        "gross_pf_ge_1_15": bool(np.isfinite(hrow["selected_pf_r"]) and hrow["selected_pf_r"] >= 1.15),
        "net10_mean_r_gt_0": bool(np.isfinite(hrow["selected_net10_mean_r"]) and hrow["selected_net10_mean_r"] > 0),
        "net10_pf_ge_1_10": bool(np.isfinite(hrow["selected_net10_pf"]) and hrow["selected_net10_pf"] >= 1.10),
        "net20_mean_r_ge_0": bool(np.isfinite(hrow["selected_net20_mean_r"]) and hrow["selected_net20_mean_r"] >= 0),
        "net20_pf_ge_1_00": bool(np.isfinite(hrow["selected_net20_pf"]) and hrow["selected_net20_pf"] >= 1.00),
    }

    if not all(sample_gates.values()):
        verdict = "MISSING_B_TEMPORAL_CHARACTER_HOLDOUT_INSUFFICIENT_SAMPLE"
    elif all(structural_gates.values()) and all(trading_gates.values()):
        verdict = "MISSING_B_TEMPORAL_CHARACTER_HOLDOUT_SUPPORTED"
    else:
        verdict = "MISSING_B_TEMPORAL_CHARACTER_NOT_VALIDATED"

    pd.DataFrame([drow, hrow]).to_csv(ROOT / f"{PFX}_PeriodSummary.csv", index=False)
    pd.DataFrame(
        [{"gate_group": "sample", "gate": k, "pass": v} for k, v in sample_gates.items()]
        + [{"gate_group": "structural", "gate": k, "pass": v} for k, v in structural_gates.items()]
        + [{"gate_group": "trading", "gate": k, "pass": v} for k, v in trading_gates.items()]
    ).to_csv(ROOT / f"{PFX}_HoldoutGateAudit.csv", index=False)

    dpop.to_csv(ROOT / f"{PFX}_DiscoveryPopulation.csv", index=False)
    dbase.to_csv(ROOT / f"{PFX}_DiscoveryBaselineTrades.csv", index=False)
    dsel.to_csv(ROOT / f"{PFX}_DiscoverySelectedTrades.csv", index=False)
    hpop.to_csv(ROOT / f"{PFX}_Holdout2026Population.csv", index=False)
    hbase.to_csv(ROOT / f"{PFX}_Holdout2026BaselineTrades.csv", index=False)
    hsel.to_csv(ROOT / f"{PFX}_Holdout2026SelectedTrades.csv", index=False)

    summary = {
        "coverage": coverage,
        "observation_end": OBS_END,
        "temporal_score_min": TEMPORAL_SCORE_MIN,
        **{f"discovery_{k}": v for k, v in drow.items() if k != "period"},
        **{f"holdout_{k}": v for k, v in hrow.items() if k != "period"},
        "sample_gates_passed": sum(bool(v) for v in sample_gates.values()),
        "sample_gates_total": len(sample_gates),
        "structural_gates_passed": sum(bool(v) for v in structural_gates.values()),
        "structural_gates_total": len(structural_gates),
        "trading_gates_passed": sum(bool(v) for v in trading_gates.values()),
        "trading_gates_total": len(trading_gates),
        "verdict": verdict,
    }
    pd.DataFrame([summary]).to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

    lines = [
        "# SOL Score-3 SELL Missing-B Temporal Character V1 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        f"- Frozen character: **approach_bars + reclaim_delay_h1_bars >= {TEMPORAL_SCORE_MIN}**.",
        "- Entry / SL / structural-completion exit unchanged.",
        "- 2020-2025 is discovery evidence; 2026 is the frozen holdout.",
        "",
        "## Discovery replay 2020-2025",
        "",
        f"- Baseline N: **{int(drow['baseline_n'])}**",
        f"- Selected N / retention: **{int(drow['selected_n'])} / {pct(drow['retention'])}**",
        f"- Structural-event rate: **{pct(drow['baseline_event_rate'])} -> {pct(drow['selected_event_rate'])}**",
        f"- Gross WR: **{pct(drow['baseline_win_rate'])} -> {pct(drow['selected_win_rate'])}**",
        f"- Gross mean R / PF: **{fmt(drow['selected_mean_r'])} / {fmt(drow['selected_pf_r'])}**",
        f"- 10 bps mean R / PF: **{fmt(drow['selected_net10_mean_r'])} / {fmt(drow['selected_net10_pf'])}**",
        f"- 20 bps mean R / PF: **{fmt(drow['selected_net20_mean_r'])} / {fmt(drow['selected_net20_pf'])}**",
        f"- Existing gross-winner retention: **{pct(drow['gross_winner_retention'])}**",
        "",
        "## Untouched 2026 holdout through 2026-09-21 00:00 UTC",
        "",
        f"- Baseline Missing-B N: **{int(hrow['baseline_n'])}**",
        f"- Selected N / retention: **{int(hrow['selected_n'])} / {pct(hrow['retention'])}**",
        f"- Structural-event rate: **{pct(hrow['baseline_event_rate'])} -> {pct(hrow['selected_event_rate'])}**",
        f"- Structural-event capture: **{pct(hrow['event_capture'])}**",
        f"- Gross WR: **{pct(hrow['baseline_win_rate'])} -> {pct(hrow['selected_win_rate'])}**",
        f"- Gross mean R / PF: **{fmt(hrow['selected_mean_r'])} / {fmt(hrow['selected_pf_r'])}**",
        f"- 10 bps mean R / PF: **{fmt(hrow['selected_net10_mean_r'])} / {fmt(hrow['selected_net10_pf'])}**",
        f"- 20 bps mean R / PF: **{fmt(hrow['selected_net20_mean_r'])} / {fmt(hrow['selected_net20_pf'])}**",
        "",
        "### Frozen gates",
        "",
    ]
    for group, gates in (
        ("Sample", sample_gates),
        ("Structural", structural_gates),
        ("Trading", trading_gates),
    ):
        lines.append(f"**{group}**")
        for k, v in gates.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        lines.append("")

    lines += [
        f"**VERDICT: {verdict}**",
        "",
        "No 2026 subgroup mining or post-holdout rule rescue was performed.",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
