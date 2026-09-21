#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_final_tradable_universe_audit_v1 as base
import sol_adaptive_risk_manager_v1 as rm
import sol_structural_liquidity_detector_v3 as v3

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1"
OBS_END = pd.Timestamp("2026-09-21 00:00:00", tz="UTC")
YEARS = (2020, 2021, 2022, 2023, 2024, 2025, 2026)


def attach_conditions(entries, pop):
    cols = ["candidate_id", "cond_A", "cond_B", "cond_C", "cond_D"]
    meta = pop[cols].drop_duplicates("candidate_id").copy()
    return entries.merge(meta, on="candidate_id", how="left", validate="one_to_one")


def original_universe(entries):
    x = entries.copy()
    tradable = (
        (pd.to_numeric(x.anatomy_score, errors="coerce") == 3)
        |
        (
            (pd.to_numeric(x.anatomy_score, errors="coerce") == 4)
            & x.side.astype(str).eq("SELL_SIDE")
        )
    )
    x = x[tradable].copy().reset_index(drop=True)
    x["universe_component"] = np.where(
        pd.to_numeric(x.anatomy_score, errors="coerce") == 3,
        "SCORE3_ALL",
        "SCORE4_SELL_SIDE_LONG",
    )
    return x


def filtered_universe(entries):
    x = original_universe(entries)

    missing_c = (
        (pd.to_numeric(x.anatomy_score, errors="coerce") == 3)
        & x.side.astype(str).eq("SELL_SIDE")
        & pd.to_numeric(x.cond_A, errors="coerce").eq(1)
        & pd.to_numeric(x.cond_B, errors="coerce").eq(1)
        & pd.to_numeric(x.cond_C, errors="coerce").eq(0)
        & pd.to_numeric(x.cond_D, errors="coerce").eq(1)
    )

    kept = x.loc[~missing_c].copy().reset_index(drop=True)
    removed = x.loc[missing_c].copy().reset_index(drop=True)
    return kept, removed


def simulate(universe, x5):
    r = rm.simulate_policy(universe, x5, "STATIC_RECLAIM_EXTREME")
    if r.empty:
        return r
    comp = universe[["candidate_id", "universe_component"]].drop_duplicates("candidate_id")
    r = r.merge(comp, on="candidate_id", how="left", validate="one_to_one")
    return r.sort_values(["entry_time", "candidate_id"]).reset_index(drop=True)


def component_table(trades):
    rows = []
    groups = [
        ("ALL", trades),
        ("BUY_SIDE", trades[trades.side == "BUY_SIDE"]),
        ("SELL_SIDE", trades[trades.side == "SELL_SIDE"]),
        ("SCORE3_ALL", trades[trades.anatomy_score == 3]),
        ("SCORE3_BUY_SIDE", trades[(trades.anatomy_score == 3) & (trades.side == "BUY_SIDE")]),
        ("SCORE3_SELL_SIDE", trades[(trades.anatomy_score == 3) & (trades.side == "SELL_SIDE")]),
        ("SCORE4_SELL_SIDE_LONG", trades[(trades.anatomy_score == 4) & (trades.side == "SELL_SIDE")]),
    ]
    for name, g in groups:
        rows.append({"component": name, **base.metrics(g)})
    return pd.DataFrame(rows)


def removed_year_table(removed_trades):
    if removed_trades.empty:
        return pd.DataFrame(columns=["year"])
    z = removed_trades.copy()
    z["year"] = pd.to_datetime(z.entry_time, utc=True).dt.year.astype(int)
    rows = []
    for year, g in z.groupby("year", sort=True):
        rows.append({"year": int(year), **base.metrics(g)})
    return pd.DataFrame(rows)


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"


def fmt(v, d=3):
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def main():
    rawbase = v3.wf1.v3.v1.base
    rawbase.END = OBS_END

    x5, coverage = v3.load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    entries, pop, _, x = rm.prepare_period(x5, OBS_END, list(YEARS))
    entries = attach_conditions(entries, pop)

    original = original_universe(entries)
    filtered, removed_entries = filtered_universe(entries)

    original_trades = simulate(original, x)
    filtered_trades = simulate(filtered, x)
    removed_ids = set(removed_entries.candidate_id.astype(str))
    removed_trades = original_trades[
        original_trades.candidate_id.astype(str).isin(removed_ids)
    ].copy().reset_index(drop=True)

    allm = base.metrics(filtered_trades)
    years, halves = base.period_tables(filtered_trades)
    components = component_table(filtered_trades)
    loyo = base.leave_one_year_out(filtered_trades)
    boot = base.bootstrap_summary(filtered_trades)
    rolling = base.rolling_table(filtered_trades)
    friction = base.friction_table(filtered_trades)

    gates, extras = base.gate_audit(allm, years, components, loyo, boot, rolling, friction)
    passed = all(gates.values())
    verdict = (
        "SOL_C_FILTERED_UNIVERSE_RETROSPECTIVELY_ROBUST"
        if passed
        else "SOL_C_FILTERED_UNIVERSE_NOT_ROBUST_AS_DEFINED"
    )

    om = base.metrics(original_trades)
    rmv = base.metrics(removed_trades)
    winner_retention = (
        float((pd.to_numeric(filtered_trades.realized_r, errors="coerce") > 0).sum())
        / float((pd.to_numeric(original_trades.realized_r, errors="coerce") > 0).sum())
        if len(original_trades) and (pd.to_numeric(original_trades.realized_r, errors="coerce") > 0).sum() > 0
        else np.nan
    )
    trade_retention = len(filtered_trades) / len(original_trades) if len(original_trades) else np.nan

    filtered_trades.to_csv(ROOT / f"{PFX}_Trades.csv", index=False)
    original_trades.to_csv(ROOT / f"{PFX}_OriginalUniverseTrades.csv", index=False)
    removed_trades.to_csv(ROOT / f"{PFX}_RemovedMissingCTrades.csv", index=False)
    removed_year_table(removed_trades).to_csv(ROOT / f"{PFX}_RemovedMissingCYearMetrics.csv", index=False)
    years.to_csv(ROOT / f"{PFX}_YearMetrics.csv", index=False)
    halves.to_csv(ROOT / f"{PFX}_HalfYearMetrics.csv", index=False)
    components.to_csv(ROOT / f"{PFX}_ComponentMetrics.csv", index=False)
    loyo.to_csv(ROOT / f"{PFX}_LeaveOneYearOut.csv", index=False)
    boot.to_csv(ROOT / f"{PFX}_BootstrapSummary.csv", index=False)
    rolling.to_csv(ROOT / f"{PFX}_Rolling20.csv", index=False)
    friction.to_csv(ROOT / f"{PFX}_FrictionStress.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(
        ROOT / f"{PFX}_GateAudit.csv", index=False
    )

    b = boot.iloc[0]
    summary = {
        "coverage": coverage,
        "observation_end": OBS_END,
        "original_n": len(original_trades),
        "filtered_n": len(filtered_trades),
        "removed_n": len(removed_trades),
        "trade_retention": trade_retention,
        "winner_retention": winner_retention,
        "original_mean_r": om["mean_r"],
        "original_pf": om["pf_r"],
        "filtered_mean_r": allm["mean_r"],
        "filtered_pf": allm["pf_r"],
        "filtered_cum_r": allm["cum_r"],
        "filtered_max_dd_r": allm["max_dd_r"],
        "removed_mean_r": rmv["mean_r"],
        "removed_pf": rmv["pf_r"],
        "removed_cum_r": rmv["cum_r"],
        "bootstrap_prob_mean_gt_0": float(b.prob_mean_gt_0),
        "bootstrap_p05_mean_r": float(b.mean_r_p05),
        "bootstrap_median_pf": float(b.pf_p50),
        **extras,
        "gates_passed": sum(bool(v) for v in gates.values()),
        "gates_total": len(gates),
        "verdict": verdict,
    }
    pd.DataFrame([summary]).to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

    c = components.set_index("component")
    lines = [
        "# SOL Score-3 SELL Missing-C Hard-Failure Universe V1 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        f"- Observation end: **{OBS_END}**",
        "- Change vs prior final universe: remove only Score-3 SELL Missing-C.",
        "- Entry, SL, exit, friction model, and robustness gates are unchanged.",
        "- This is retrospective robustness evidence, not untouched live validation.",
        "",
        "## Preservation",
        "",
        f"- Original universe trades: **{len(original_trades)}**",
        f"- Filtered universe trades: **{len(filtered_trades)}**",
        f"- Removed Missing-C trades: **{len(removed_trades)}**",
        f"- Trade retention: **{pct(trade_retention)}**",
        f"- Gross-winner retention: **{pct(winner_retention)}**",
        "",
        "## Removed Missing-C cohort",
        "",
        f"- Mean R / PF: **{fmt(rmv['mean_r'])} / {fmt(rmv['pf_r'])}**",
        f"- Cumulative R: **{fmt(rmv['cum_r'])}R**",
        f"- Event rate / WR: **{pct(rmv['event_rate'])} / {pct(rmv['win_rate'])}**",
        "",
        "## Filtered full-universe economics",
        "",
        f"- Trades: **{allm['n']}**",
        f"- Structural-event rate: **{pct(allm['event_rate'])}**",
        f"- Gross WR: **{pct(allm['win_rate'])}**",
        f"- Mean / median R: **{fmt(allm['mean_r'])} / {fmt(allm['median_r'])}**",
        f"- PF: **{fmt(allm['pf_r'])}**",
        f"- Cumulative: **{fmt(allm['cum_r'])}R**",
        f"- Max DD: **{fmt(allm['max_dd_r'])}R**",
        f"- Max losing streak: **{allm['max_loss_streak']}**",
        "",
        "## Components",
        "",
        "| Component | N | Event rate | Mean R | PF | Cum R | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for name in ("BUY_SIDE", "SELL_SIDE", "SCORE3_ALL", "SCORE3_BUY_SIDE", "SCORE3_SELL_SIDE", "SCORE4_SELL_SIDE_LONG"):
        r = c.loc[name]
        lines.append(
            f"| {name} | {int(r.n)} | {pct(r.event_rate)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {fmt(r.cum_r)} | {fmt(r.max_dd_r)} |"
        )

    lines += [
        "",
        "## Yearly robustness",
        "",
        "| Year | N | Mean R | PF | Cum R | Max DD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in years.iterrows():
        lines.append(
            f"| {int(r.year)} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {fmt(r.cum_r)} | {fmt(r.max_dd_r)} |"
        )

    lines += [
        "",
        "## Robustness stress",
        "",
        f"- Leave-one-year-out: **{int(loyo.pass_mean_gt_0.sum())}/{len(loyo)} mean-positive**, **{int(loyo.pass_pf_ge_1_10.sum())}/{len(loyo)} PF>=1.10**.",
        f"- Bootstrap P(mean>0): **{pct(float(b.prob_mean_gt_0))}**.",
        f"- Bootstrap mean-R 5th percentile: **{fmt(float(b.mean_r_p05))}R**.",
        f"- Bootstrap median PF: **{fmt(float(b.pf_p50))}**.",
        f"- Rolling-20 positive-mean share: **{pct(extras['rolling_positive_share'])}**.",
        f"- Worst rolling-20 mean: **{fmt(extras['rolling_worst_mean_r'])}R**.",
        "",
        "## Friction stress",
        "",
        "| Round-trip friction | Mean net R | PF | Cum net R | Max DD |",
        "|---:|---:|---:|---:|---:|",
    ]
    for _, r in friction.iterrows():
        lines.append(
            f"| {int(r.round_trip_bps)} bps | {fmt(r.mean_net_r)} | {fmt(r.pf_net_r)} | {fmt(r.cum_net_r)} | {fmt(r.max_dd_net_r)} |"
        )

    lines += ["", "## Frozen gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines += [
        "",
        f"**VERDICT: {verdict}**",
        "",
        f"Passed **{sum(bool(v) for v in gates.values())}/{len(gates)}** frozen gates.",
        "",
        "Per preregistration, no rescue rule was added after reading this result.",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
