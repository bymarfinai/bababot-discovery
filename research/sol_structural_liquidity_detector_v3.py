#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import time
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_reset_winner_first_v1 as wf1
import sol_structural_liquidity_discovery_v1 as v1
import sol_structural_liquidity_anatomy_v2 as v2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURAL_LIQUIDITY_DETECTOR_V3"

CONSTRUCTION_YEARS = (2020, 2021, 2022, 2023, 2024)
HOLDOUT_YEAR = 2025

A_MAX = 2.073485713625842
B_MAX = 1.4084118083030879
C_MIN = 0.4999999999999881
D_MIN = 0.6013241386375646

CONSTRUCTION_END = pd.Timestamp("2025-01-01", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-01-01", tz="UTC")


def load5_with_retry(symbol: str):
    base = wf1.v3.v1.base
    original = wf1.v3.v1.fetch_one_with_volume

    def retry_fetch(*args, **kwargs):
        last = None
        for attempt in range(4):
            try:
                return original(*args, **kwargs)
            except Exception as e:
                last = e
                if attempt < 3:
                    time.sleep(2.0 * (attempt + 1))
        raise last

    base.fetch_one = retry_fetch
    return base.load5(symbol)


def wilson(successes: int, n: int, z: float = 1.96):
    if n <= 0:
        return np.nan, np.nan
    p = successes / n
    den = 1.0 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt((p*(1-p)/n) + z*z/(4*n*n)) / den
    return center - half, center + half


def event_rate(df: pd.DataFrame) -> float:
    return float(df.event_label.mean()) if len(df) else np.nan


def build_population(x5: pd.DataFrame, end_time: pd.Timestamp) -> pd.DataFrame:
    # Only bars before end_time are ever exposed to the structural engine.
    x = x5[x5.index < end_time].copy()
    h1 = fc1.build_h1(x)

    # V1 uses this global boundary causally for candidate activation and right-censoring.
    old_end = v1.MODEL_END
    try:
        v1.MODEL_END = end_time
        candidates0 = v1.generate_candidates(h1)
        _, sweeps = v1.label_candidates(h1, candidates0)
    finally:
        v1.MODEL_END = old_end

    events = v2.dedup_physical_events(sweeps, h1)
    features = v2.extract_features(events, h1)
    features["sweep_year"] = pd.to_datetime(features.sweep_time, utc=True).dt.year.astype(int)
    return features.reset_index(drop=True)


def add_conditions(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    a = pd.to_numeric(x["source_to_opposite_structure_range_units"], errors="coerce")
    b = pd.to_numeric(x["approach_start_distance_to_level_range_units"], errors="coerce")
    c = pd.to_numeric(x["reclaim_directional_body_range_units"], errors="coerce")
    d = pd.to_numeric(x["reclaim_close_inside_range_units"], errors="coerce")

    x["cond_A"] = (a <= A_MAX).fillna(False).astype(int)
    x["cond_B"] = (b <= B_MAX).fillna(False).astype(int)
    x["cond_C"] = (c >= C_MIN).fillna(False).astype(int)
    x["cond_D"] = (d >= D_MIN).fillna(False).astype(int)
    x["anatomy_score"] = x[["cond_A", "cond_B", "cond_C", "cond_D"]].sum(axis=1).astype(int)
    return x


def side_stats(df: pd.DataFrame):
    rows = []
    for side in ("BUY_SIDE", "SELL_SIDE"):
        g = df[df.side == side]
        rows.append({"side": side, "n": len(g), "rate": event_rate(g)})
    return pd.DataFrame(rows)


def construction_candidates(construction: pd.DataFrame):
    baseline = event_rate(construction)
    side_base = side_stats(construction).set_index("side")
    rows = []

    for k in (1, 2, 3, 4):
        g = construction[construction.anatomy_score >= k].copy()
        r = event_rate(g)
        succ = int(g.event_label.sum()) if len(g) else 0
        lo, hi = wilson(succ, len(g))
        side_sel = side_stats(g).set_index("side")

        buy_better = (
            "BUY_SIDE" in side_sel.index and len(g[g.side == "BUY_SIDE"]) > 0
            and np.isfinite(side_sel.loc["BUY_SIDE", "rate"])
            and np.isfinite(side_base.loc["BUY_SIDE", "rate"])
            and side_sel.loc["BUY_SIDE", "rate"] > side_base.loc["BUY_SIDE", "rate"]
        )
        sell_better = (
            "SELL_SIDE" in side_sel.index and len(g[g.side == "SELL_SIDE"]) > 0
            and np.isfinite(side_sel.loc["SELL_SIDE", "rate"])
            and np.isfinite(side_base.loc["SELL_SIDE", "rate"])
            and side_sel.loc["SELL_SIDE", "rate"] > side_base.loc["SELL_SIDE", "rate"]
        )

        lift = r - baseline if np.isfinite(r) and np.isfinite(baseline) else np.nan
        eligible = bool(
            len(g) >= 150
            and np.isfinite(r) and r >= .40
            and np.isfinite(lift) and lift >= .12
            and buy_better
            and sell_better
        )

        rows.append({
            "rule": f"SCORE_GE_{k}",
            "score_threshold": k,
            "selected_n": len(g),
            "structural_event_n": succ,
            "selected_rate": r,
            "baseline_rate": baseline,
            "lift": lift,
            "wilson_lower": lo,
            "wilson_upper": hi,
            "buy_n": int((g.side == "BUY_SIDE").sum()),
            "buy_rate": event_rate(g[g.side == "BUY_SIDE"]),
            "buy_baseline": float(side_base.loc["BUY_SIDE", "rate"]),
            "sell_n": int((g.side == "SELL_SIDE").sum()),
            "sell_rate": event_rate(g[g.side == "SELL_SIDE"]),
            "sell_baseline": float(side_base.loc["SELL_SIDE", "rate"]),
            "eligible": eligible,
        })

    out = pd.DataFrame(rows)
    elig = out[out.eligible].copy()
    if elig.empty:
        return out, None

    elig = elig.sort_values(
        ["wilson_lower", "selected_rate", "selected_n", "score_threshold"],
        ascending=[False, False, False, False],
    )
    return out, elig.iloc[0].to_dict()


def score_diagnostics(df: pd.DataFrame, phase: str):
    rows = []
    base = event_rate(df)
    for score in range(5):
        g = df[df.anatomy_score == score]
        succ = int(g.event_label.sum()) if len(g) else 0
        lo, hi = wilson(succ, len(g))
        rows.append({
            "phase": phase,
            "score": score,
            "n": len(g),
            "event_n": succ,
            "event_rate": event_rate(g),
            "baseline_rate": base,
            "wilson_lower": lo,
            "wilson_upper": hi,
        })
    return pd.DataFrame(rows)


def holdout_audit(holdout: pd.DataFrame, threshold: int):
    selected = holdout[holdout.anatomy_score >= threshold].copy()
    baseline = event_rate(holdout)
    rate = event_rate(selected)
    lift = rate - baseline if np.isfinite(rate) and np.isfinite(baseline) else np.nan
    succ = int(selected.event_label.sum()) if len(selected) else 0
    wlo, whi = wilson(succ, len(selected))

    side_base = side_stats(holdout).set_index("side")
    side_sel = side_stats(selected).set_index("side")

    buy_rate = float(side_sel.loc["BUY_SIDE", "rate"]) if "BUY_SIDE" in side_sel.index else np.nan
    sell_rate = float(side_sel.loc["SELL_SIDE", "rate"]) if "SELL_SIDE" in side_sel.index else np.nan
    buy_base = float(side_base.loc["BUY_SIDE", "rate"]) if "BUY_SIDE" in side_base.index else np.nan
    sell_base = float(side_base.loc["SELL_SIDE", "rate"]) if "SELL_SIDE" in side_base.index else np.nan

    gates = {
        "selected_2025_n_ge_50": len(selected) >= 50,
        "selected_2025_rate_ge_45pct": bool(np.isfinite(rate) and rate >= .45),
        "lift_vs_2025_baseline_ge_15pp": bool(np.isfinite(lift) and lift >= .15),
        "wilson_lower_ge_35pct": bool(np.isfinite(wlo) and wlo >= .35),
        "buy_side_above_baseline": bool(np.isfinite(buy_rate) and np.isfinite(buy_base) and buy_rate > buy_base),
        "sell_side_above_baseline": bool(np.isfinite(sell_rate) and np.isfinite(sell_base) and sell_rate > sell_base),
    }

    summary = {
        "baseline_n": len(holdout),
        "baseline_rate": baseline,
        "selected_n": len(selected),
        "selected_event_n": succ,
        "selected_rate": rate,
        "lift": lift,
        "wilson_lower": wlo,
        "wilson_upper": whi,
        "buy_selected_n": int((selected.side == "BUY_SIDE").sum()),
        "buy_selected_rate": buy_rate,
        "buy_baseline_rate": buy_base,
        "sell_selected_n": int((selected.side == "SELL_SIDE").sum()),
        "sell_selected_rate": sell_rate,
        "sell_baseline_rate": sell_base,
        **{f"gate_{k}": v for k, v in gates.items()},
        "verdict": "VALIDATED_STRUCTURAL_LIQUIDITY_DETECTOR" if all(gates.values()) else "DETECTOR_NOT_VALIDATED_AS_DEFINED",
    }
    return selected, summary


def halfyear_diag(holdout: pd.DataFrame, threshold: int):
    x = holdout.copy()
    ts = pd.to_datetime(x.sweep_time, utc=True)
    x["half"] = np.where(ts.dt.month <= 6, "2025_H1", "2025_H2")
    rows = []
    for half in ("2025_H1", "2025_H2"):
        b = x[x.half == half]
        s = b[b.anatomy_score >= threshold]
        rows.append({
            "half": half,
            "baseline_n": len(b),
            "baseline_rate": event_rate(b),
            "selected_n": len(s),
            "selected_rate": event_rate(s),
            "lift": event_rate(s) - event_rate(b) if len(s) and len(b) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    x5, coverage = load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # PASS 1: construction engine stops at 2025-01-01.
    construction = add_conditions(build_population(x5, CONSTRUCTION_END))
    construction = construction[construction.sweep_year.isin(CONSTRUCTION_YEARS)].copy()

    candidates, selected_rule = construction_candidates(construction)
    construction_diag = score_diagnostics(construction, "CONSTRUCTION_2020_2024")

    construction.to_csv(ROOT / f"{PFX}_ConstructionEvents.csv", index=False)
    candidates.to_csv(ROOT / f"{PFX}_ConstructionCandidates.csv", index=False)
    construction_diag.to_csv(ROOT / f"{PFX}_ConstructionScoreDiagnostic.csv", index=False)

    if selected_rule is None:
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2025Events.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2025Selected.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2025ScoreDiagnostic.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2025HalfYear.csv", index=False)

        status = "NO_CONSTRUCTION_DETECTOR"
        summary = pd.DataFrame([{
            "coverage": coverage,
            "construction_n": len(construction),
            "construction_baseline_rate": event_rate(construction),
            "selected_rule": "",
            "holdout_opened": False,
            "verdict": status,
        }])
        summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

        lines = [
            "# SOL Structural Liquidity Detector V3 — Result",
            "",
            f"- Coverage: **{coverage*100:.6f}%**",
            f"- Construction physical events 2020-2024: **{len(construction):,}**",
            f"- Construction baseline structural-event rate: **{event_rate(construction)*100:.2f}%**",
            "- 2025 remained unopened because no score rule met the preregistered construction gates.",
            "",
            f"**VERDICT: {status}**",
            "",
            "2026_PLUS=CLOSED",
        ]
    else:
        threshold = int(selected_rule["score_threshold"])

        # PASS 2: only now expose the structural engine to bars through 2025.
        all_to_2025 = add_conditions(build_population(x5, HOLDOUT_END))
        holdout = all_to_2025[all_to_2025.sweep_year == HOLDOUT_YEAR].copy()

        selected_holdout, hs = holdout_audit(holdout, threshold)
        holdout_diag = score_diagnostics(holdout, "UNTOUCHED_2025")
        half = halfyear_diag(holdout, threshold)

        holdout.to_csv(ROOT / f"{PFX}_Holdout2025Events.csv", index=False)
        selected_holdout.to_csv(ROOT / f"{PFX}_Holdout2025Selected.csv", index=False)
        holdout_diag.to_csv(ROOT / f"{PFX}_Holdout2025ScoreDiagnostic.csv", index=False)
        half.to_csv(ROOT / f"{PFX}_Holdout2025HalfYear.csv", index=False)

        summary = pd.DataFrame([{
            "coverage": coverage,
            "construction_n": len(construction),
            "construction_baseline_rate": event_rate(construction),
            "selected_rule": selected_rule["rule"],
            "selected_score_threshold": threshold,
            "construction_selected_n": int(selected_rule["selected_n"]),
            "construction_selected_rate": float(selected_rule["selected_rate"]),
            "construction_lift": float(selected_rule["lift"]),
            "construction_wilson_lower": float(selected_rule["wilson_lower"]),
            "holdout_opened": True,
            **hs,
        }])
        summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

        def pct(v):
            return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

        lines = [
            "# SOL Structural Liquidity Detector V3 — Result",
            "",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            "- Four V2 anatomy thresholds were frozen unchanged.",
            "- 2020-2024 used only for combination construction.",
            "- 2025 opened only after the score rule was frozen.",
            "- 2026+ CLOSED.",
            "- No entry, TP, SL, PnL, hour, session, indicator, or regime filter.",
            "",
            "## Frozen construction rule",
            "",
            f"**{selected_rule['rule']}**",
            "",
            f"- Construction baseline: N={len(construction):,}, rate={pct(event_rate(construction))}",
            f"- Construction selected: N={int(selected_rule['selected_n']):,}, rate={pct(float(selected_rule['selected_rate']))}",
            f"- Construction lift: **{float(selected_rule['lift'])*100:.2f} pp**",
            f"- Construction Wilson lower: **{pct(float(selected_rule['wilson_lower']))}**",
            "",
            "## Untouched 2025 validation",
            "",
            f"- Baseline: N={int(hs['baseline_n']):,}, structural-event rate={pct(float(hs['baseline_rate']))}",
            f"- Detector selected: N={int(hs['selected_n']):,}, structural-event rate=**{pct(float(hs['selected_rate']))}**",
            f"- Lift: **{float(hs['lift'])*100:.2f} pp**",
            f"- Wilson 95% CI: **{pct(float(hs['wilson_lower']))} – {pct(float(hs['wilson_upper']))}**",
            f"- BUY_SIDE: N={int(hs['buy_selected_n'])}, selected={pct(float(hs['buy_selected_rate']))}, baseline={pct(float(hs['buy_baseline_rate']))}",
            f"- SELL_SIDE: N={int(hs['sell_selected_n'])}, selected={pct(float(hs['sell_selected_rate']))}, baseline={pct(float(hs['sell_baseline_rate']))}",
            "",
            "## 2025 half-year diagnostic",
            "",
            "| Half | Baseline N | Baseline | Selected N | Selected | Lift |",
            "|---|---:|---:|---:|---:|---:|",
        ]

        for _, r in half.iterrows():
            lift_txt = f"{r.lift*100:.2f} pp" if np.isfinite(r.lift) else "n/a"
            lines.append(
                f"| {r['half']} | {int(r.baseline_n)} | {pct(float(r.baseline_rate))} | "
                f"{int(r.selected_n)} | {pct(float(r.selected_rate))} | {lift_txt} |"
            )

        lines += ["", "## Frozen validation gate audit", ""]
        for k in (
            "selected_2025_n_ge_50",
            "selected_2025_rate_ge_45pct",
            "lift_vs_2025_baseline_ge_15pp",
            "wilson_lower_ge_35pct",
            "buy_side_above_baseline",
            "sell_side_above_baseline",
        ):
            lines.append(f"- {'PASS' if bool(hs['gate_'+k]) else 'FAIL'} — {k}")

        lines += [
            "",
            f"**VERDICT: {hs['verdict']}**",
            "",
            "The verdict concerns structural-liquidity classification at reclaim close only. It does not define a trade entry or economics.",
            "",
            "2026_PLUS=CLOSED",
        ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        str(summary.iloc[0]["verdict"]) + "\n2026_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
