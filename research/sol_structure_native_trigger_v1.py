#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_structure_library_v1 as v1
import sol_structure_trigger_matrix_v1 as mx
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURE_NATIVE_TRIGGER_V1"
YEARS = v1.YEARS
TRIGGER_MAX_BARS = 12

DETECTORS = (
    ("SWEEP_RECLAIM", "RETEST_HOLD_BREAK"),
    ("HL_SETUP", "BREAK_INTERVENING_HIGH"),
    ("BREAKOUT_PULLBACK_SETUP", "RECOVERY_HIGH_BREAK"),
    ("FAILED_BREAKDOWN_RECLAIM", "RETEST_RECLAIM_HIGH_BREAK"),
)
DETECTOR_IDS = tuple(f"{s}__{t}" for s, t in DETECTORS)


def emit(rows: list[dict], s: pd.Series, trigger: str, signal_i: int, idx, op, hi, lo, cl,
         trigger_level: float, extra: dict | None = None) -> None:
    detector = f"{s.structure}__{trigger}"
    meta = {
        "context_structure": str(s.structure),
        "entry_trigger": trigger,
        "setup_time": s.setup_time,
        "setup_i": int(s.setup_i),
        "bars_after_setup": int(signal_i - int(s.setup_i)),
        "minutes_after_setup": int((signal_i - int(s.setup_i)) * 5),
        "anchor_level": float(s.anchor_level),
        "anchor_pivot_i": int(s.anchor_pivot_i),
        "secondary_level": float(s.secondary_level) if np.isfinite(s.secondary_level) else np.nan,
        "secondary_pivot_i": int(s.secondary_pivot_i),
        "native_trigger_level": float(trigger_level),
    }
    if extra:
        meta.update(extra)
    v1.add_signal(rows, detector, signal_i, idx, op, hi, lo, cl, meta)


def apply_native_triggers(setups: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    rows: list[dict] = []

    for _, s in setups.iterrows():
        structure = str(s.structure)
        if structure not in {x[0] for x in DETECTORS}:
            continue
        setup_i = int(s.setup_i)
        last_scan = min(setup_i + TRIGGER_MAX_BARS, len(x5) - v1.FUTURE_BARS - 2)
        if last_scan <= setup_i:
            continue

        # A. SWEEP_RECLAIM -> retest/hold swept level -> break retest-bar high.
        if structure == "SWEEP_RECLAIM":
            anchor = float(s.anchor_level)
            retest_i = None
            retest_high = np.nan
            for i in range(setup_i + 1, last_scan + 1):
                if cl[i] < anchor:
                    break
                if retest_i is None:
                    if lo[i] <= anchor and cl[i] >= anchor:
                        retest_i = int(i)
                        retest_high = float(hi[i])
                    continue
                if cl[i] > retest_high:
                    emit(rows, s, "RETEST_HOLD_BREAK", i, idx, op, hi, lo, cl,
                         retest_high, {"retest_i": retest_i, "retest_time": idx[retest_i]})
                    break

        # B. HL_SETUP -> break the intervening H1 while HL remains valid.
        elif structure == "HL_SETUP":
            hl = float(s.secondary_level)
            h1 = float(s.anchor_level)
            if not np.isfinite(hl):
                continue
            for i in range(setup_i + 1, last_scan + 1):
                if cl[i] < hl:
                    break
                if cl[i] > h1:
                    emit(rows, s, "BREAK_INTERVENING_HIGH", i, idx, op, hi, lo, cl, h1)
                    break

        # C. BREAKOUT_PULLBACK_SETUP -> break recovery high frozen at setup completion.
        elif structure == "BREAKOUT_PULLBACK_SETUP":
            breakout_level = float(s.anchor_level)
            pivot_i = int(s.secondary_pivot_i)
            if pivot_i < 0 or pivot_i > setup_i:
                continue
            recovery_high = float(np.max(hi[pivot_i:setup_i + 1]))
            for i in range(setup_i + 1, last_scan + 1):
                if cl[i] < breakout_level:
                    break
                if cl[i] > recovery_high:
                    emit(rows, s, "RECOVERY_HIGH_BREAK", i, idx, op, hi, lo, cl,
                         recovery_high, {"recovery_high_start_i": pivot_i})
                    break

        # D. FAILED_BREAKDOWN_RECLAIM -> retest reclaimed level -> break reclaim-bar high.
        elif structure == "FAILED_BREAKDOWN_RECLAIM":
            anchor = float(s.anchor_level)
            reclaim_high = float(hi[setup_i])
            retest_i = None
            for i in range(setup_i + 1, last_scan + 1):
                if cl[i] < anchor:
                    break
                if retest_i is None:
                    if lo[i] <= anchor and cl[i] >= anchor:
                        retest_i = int(i)
                    continue
                if cl[i] > reclaim_high:
                    emit(rows, s, "RETEST_RECLAIM_HIGH_BREAK", i, idx, op, hi, lo, cl,
                         reclaim_high, {"retest_i": retest_i, "retest_time": idx[retest_i]})
                    break

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no native-trigger trades detected")
    out = out.sort_values(["structure", "entry_time", "setup_time"]).drop_duplicates(
        ["structure", "entry_time", "setup_time"], keep="first"
    )
    return out.reset_index(drop=True)


def summarize(setups: pd.DataFrame, trades: pd.DataFrame):
    pooled_rows, yearly_rows = [], []
    setup_counts = setups.groupby("structure").size().to_dict()

    for structure, trigger in DETECTORS:
        detector = f"{structure}__{trigger}"
        g = trades[trades.structure == detector].copy()
        e = v1.econ(g)
        setup_n = int(setup_counts.get(structure, 0))
        ratio = float(g.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(g) else np.nan
        pos_years = 0

        for year in YEARS:
            gy = g[g.year == year].copy()
            ey = v1.econ(gy)
            if ey["pnl_usd"] > 0:
                pos_years += 1
            yearly_rows.append({
                "detector": detector,
                "structure": structure,
                "trigger": trigger,
                "year": year,
                "n": ey["n"],
                "wr60": ey["wr"],
                "expectancy60_pct": ey["expectancy_pct"],
                "pf60": ey["pf"],
                "pnl60_usd": ey["pnl_usd"],
                "max_dd_usd": ey["max_dd_usd"],
                "max_loss_streak": ey["max_loss_streak"],
                "clean_up_impulse_rate": float(gy.clean_up_impulse.mean()) if len(gy) else np.nan,
                "median_mfe60_pct": float(gy.mfe60_pct.median()) if len(gy) else np.nan,
                "median_mae60_pct": float(gy.mae60_pct.median()) if len(gy) else np.nan,
                "median_mfe_mae_ratio": float(gy.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(gy) else np.nan,
                "median_trigger_delay_min": float(gy.minutes_after_setup.median()) if len(gy) else np.nan,
            })

        gates = {
            "n_ge_100": e["n"] >= 100,
            "expectancy_positive": bool(np.isfinite(e["expectancy_pct"]) and e["expectancy_pct"] > 0),
            "pf_ge_1_15": bool(np.isfinite(e["pf"]) and e["pf"] >= 1.15),
            "positive_pnl_years_ge_4_of_5": pos_years >= 4,
            "median_mfe_mae_ge_1_20": bool(np.isfinite(ratio) and ratio >= 1.20),
        }
        pooled_rows.append({
            "detector": detector,
            "structure": structure,
            "trigger": trigger,
            "setup_n": setup_n,
            "triggered_n": e["n"],
            "trigger_rate": e["n"] / setup_n if setup_n else np.nan,
            "wr60": e["wr"],
            "expectancy60_pct": e["expectancy_pct"],
            "pf60": e["pf"],
            "pnl60_usd": e["pnl_usd"],
            "max_dd_usd": e["max_dd_usd"],
            "max_loss_streak": e["max_loss_streak"],
            "clean_up_impulse_rate": float(g.clean_up_impulse.mean()) if len(g) else np.nan,
            "median_mfe60_pct": float(g.mfe60_pct.median()) if len(g) else np.nan,
            "median_mae60_pct": float(g.mae60_pct.median()) if len(g) else np.nan,
            "median_mfe_mae_ratio": ratio,
            "median_trigger_delay_min": float(g.minutes_after_setup.median()) if len(g) else np.nan,
            "positive_pnl_years": pos_years,
            **{f"gate_{k}": v for k, v in gates.items()},
            "verdict": "PASS_TO_CHARACTERIZATION" if all(gates.values()) else "REJECTED_AS_DEFINED",
        })

    return pd.DataFrame(pooled_rows), pd.DataFrame(yearly_rows)


def pfmt(v):
    return v1.pfmt(v)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Reuse frozen structure contexts exactly from Matrix V1.
    setups = mx.detect_setups(x5)
    setups = setups[setups.structure.isin([x[0] for x in DETECTORS])].copy().reset_index(drop=True)
    trades = apply_native_triggers(setups, x5)
    pooled, yearly = summarize(setups, trades)

    setups.to_csv(ROOT / f"{PFX}_SetupEvents.csv", index=False)
    trades.to_csv(ROOT / f"{PFX}_TriggeredTrades.csv", index=False)
    pooled.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)

    lines = [
        "# SOL Structure-Specific Native Trigger V1 — Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Structural setup records: **{len(setups)}**",
        f"- Native-triggered trade records: **{len(trades)}**",
        "- Evaluation: 2020-2024; 2025+ remained CLOSED.",
        "- Structure is context only. Entry occurs only after the preregistered native trigger.",
        "- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% RT cost.", "",
        "## Native trigger scorecard", "",
        "| Structure | Native trigger | Setup N | Trigger N | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in pooled.iterrows():
        lines.append(
            f"| {r.structure} | {r.trigger} | {int(r.setup_n)} | {int(r.triggered_n)} | "
            f"{float(r.trigger_rate)*100:.2f}% | {float(r.wr60)*100 if np.isfinite(r.wr60) else np.nan:.2f}% | "
            f"{float(r.expectancy60_pct) if np.isfinite(r.expectancy60_pct) else np.nan:.4f}% | {pfmt(r.pf60)} | "
            f"${float(r.pnl60_usd):.2f} | ${float(r.max_dd_usd) if np.isfinite(r.max_dd_usd) else np.nan:.2f} | "
            f"{float(r.clean_up_impulse_rate)*100 if np.isfinite(r.clean_up_impulse_rate) else np.nan:.2f}% | "
            f"{float(r.median_mfe_mae_ratio) if np.isfinite(r.median_mfe_mae_ratio) else np.nan:.3f} | "
            f"{float(r.median_trigger_delay_min) if np.isfinite(r.median_trigger_delay_min) else np.nan:.1f}m | "
            f"{int(r.positive_pnl_years)}/5 | **{r.verdict}** |"
        )

    lines += ["", "## Yearly economics", ""]
    for detector in DETECTOR_IDS:
        structure, trigger = detector.split("__", 1)
        lines += [f"### {structure} → {trigger}", "",
                  "| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in yearly[yearly.detector == detector].iterrows():
            lines.append(
                f"| {int(r.year)} | {int(r.n)} | {float(r.wr60)*100 if np.isfinite(r.wr60) else np.nan:.2f}% | "
                f"{float(r.expectancy60_pct) if np.isfinite(r.expectancy60_pct) else np.nan:.4f}% | {pfmt(r.pf60)} | "
                f"${float(r.pnl60_usd):.2f} | {float(r.clean_up_impulse_rate)*100 if np.isfinite(r.clean_up_impulse_rate) else np.nan:.2f}% | "
                f"{float(r.median_mfe_mae_ratio) if np.isfinite(r.median_mfe_mae_ratio) else np.nan:.3f} | "
                f"{float(r.median_trigger_delay_min) if np.isfinite(r.median_trigger_delay_min) else np.nan:.1f}m |"
            )
        lines.append("")

    lines += ["## Frozen gate audit", ""]
    for _, r in pooled.iterrows():
        lines.append(f"### {r.detector} — {r.verdict}")
        for gate in ["n_ge_100", "expectancy_positive", "pf_ge_1_15", "positive_pnl_years_ge_4_of_5", "median_mfe_mae_ge_1_20"]:
            lines.append(f"- {'PASS' if bool(r['gate_'+gate]) else 'FAIL'} — `{gate}`")
        lines.append("")

    passing = pooled.loc[pooled.verdict == "PASS_TO_CHARACTERIZATION", "detector"].tolist()
    lines += [
        "## Interpretation rule", "",
        "PASS_TO_CHARACTERIZATION means this exact structure + native trigger may advance to its own execution / TP / SL characterization.",
        "REJECTED_AS_DEFINED rejects only this exact entry trigger for that structure. Do not rescue it on 2020-2024 by retuning the trigger window, levels, hours, indicators, regime filters, TP or SL.", "",
        "PASSING_NATIVE_DETECTORS=" + (",".join(passing) if passing else "NONE"),
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    status = "PASSING_NATIVE_DETECTORS=" + (",".join(passing) if passing else "NONE")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print(text)
    print(status)


if __name__ == "__main__":
    main()
