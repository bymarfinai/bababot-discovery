#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structural_liquidity_anatomy_v2 as v2
import sol_structural_liquidity_detector_v3 as v3

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ADAPTIVE_ENTRY_V1_ACTIONABLE"

CONSTRUCTION_END = pd.Timestamp("2025-01-01", tz="UTC")
CONFIRM_END = pd.Timestamp("2026-01-01", tz="UTC")
ENTRY_WINDOW = pd.Timedelta(hours=6)
BAR5 = pd.Timedelta(minutes=5)

VARIANTS = (
    "BASELINE_MARKET",
    "GAP_25",
    "GAP_50",
    "GAP_75",
    "LIQUIDITY_LEVEL",
    "RECLAIM_BODY_MID",
    "RECLAIM_OPEN",
    "FIVE_MIN_REVERSAL_BREAK",
)

ADAPTIVE_VARIANTS = tuple(v for v in VARIANTS if v != "BASELINE_MARKET")


def rate(df: pd.DataFrame) -> float:
    return float(df.event_label.mean()) if len(df) else np.nan


def actionable_detector_population(x5: pd.DataFrame, end_time: pd.Timestamp, years) -> tuple[pd.DataFrame, pd.DataFrame]:
    feats = v3.add_conditions(v3.build_population(x5, end_time))
    feats = feats[feats.sweep_year.isin(years)].copy()

    ri = pd.to_numeric(feats.resolution_i_h1, errors="coerce")
    qi = pd.to_numeric(feats.reclaim_i_h1, errors="coerce")
    same_resolved = (ri >= 0) & (ri == qi)
    feats = feats.loc[~same_resolved].copy()

    det = feats[feats.anatomy_score >= 3].copy().reset_index(drop=True)
    x = x5[x5.index < end_time].copy()
    h1 = fc1.build_h1(x)
    return det, h1


def event_context(row, h1: pd.DataFrame, x5: pd.DataFrame):
    hidx = h1.index
    hi1 = h1.high.astype(float).to_numpy()
    lo1 = h1.low.astype(float).to_numpy()
    op1 = h1.open.astype(float).to_numpy()
    cl1 = h1.close.astype(float).to_numpy()

    reclaim_i = int(row.reclaim_i_h1)
    sweep_i = int(row.sweep_i_h1)

    if reclaim_i < 0 or reclaim_i >= len(h1) or sweep_i < 0 or sweep_i >= len(h1):
        return None

    unit = v2.prior_median_range(hi1, lo1, sweep_i)
    if not np.isfinite(unit) or unit <= 0:
        return None

    reclaim_time = pd.Timestamp(row.reclaim_time)
    signal_time = reclaim_time + pd.Timedelta(hours=1)

    pos = int(x5.index.searchsorted(signal_time, side="left"))
    if pos >= len(x5):
        return None
    baseline_time = x5.index[pos]
    if baseline_time < signal_time:
        return None
    baseline_price = float(x5.iloc[pos].open)

    resolution_i = int(row.resolution_i_h1) if pd.notna(row.resolution_i_h1) else -1
    deadline = signal_time + ENTRY_WINDOW
    outcome_known_time = signal_time + pd.Timedelta(hours=15)

    if resolution_i >= 0:
        resolution_start = pd.Timestamp(row.resolution_time)
        resolution_close = resolution_start + pd.Timedelta(hours=1)
        deadline = min(deadline, resolution_close)
        outcome_known_time = resolution_close

    if baseline_time >= deadline:
        return None

    return {
        "side": str(row.side),
        "signal_time": signal_time,
        "deadline": deadline,
        "outcome_known_time": outcome_known_time,
        "baseline_i_5m": pos,
        "baseline_time": baseline_time,
        "baseline_price": baseline_price,
        "range_unit": float(unit),
        "reclaim_i_h1": reclaim_i,
        "reclaim_open": float(op1[reclaim_i]),
        "reclaim_high": float(hi1[reclaim_i]),
        "reclaim_low": float(lo1[reclaim_i]),
        "reclaim_close": float(cl1[reclaim_i]),
        "liquidity_level": float(row.level),
        "structural_target": float(row.significant_opposite_level),
    }


def limit_price(variant: str, c: dict) -> float:
    rc = c["reclaim_close"]
    lvl = c["liquidity_level"]
    if variant == "GAP_25":
        return rc + .25 * (lvl - rc)
    if variant == "GAP_50":
        return rc + .50 * (lvl - rc)
    if variant == "GAP_75":
        return rc + .75 * (lvl - rc)
    if variant == "LIQUIDITY_LEVEL":
        return lvl
    if variant == "RECLAIM_BODY_MID":
        return .5 * (c["reclaim_open"] + c["reclaim_close"])
    if variant == "RECLAIM_OPEN":
        return c["reclaim_open"]
    raise ValueError(variant)


def fill_limit(x5: pd.DataFrame, c: dict, price: float):
    start = int(c["baseline_i_5m"])
    idx = x5.index
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    for i in range(start, len(x5)):
        if idx[i] >= c["deadline"]:
            break
        if c["side"] == "BUY_SIDE":
            if hi[i] >= price:
                return i, idx[i], float(price)
        else:
            if lo[i] <= price:
                return i, idx[i], float(price)
    return None


def fill_break(x5: pd.DataFrame, c: dict):
    start = int(c["baseline_i_5m"])
    idx = x5.index
    cl = x5.close.astype(float).to_numpy()
    op = x5.open.astype(float).to_numpy()

    for i in range(start, len(x5) - 1):
        bar_close_time = idx[i] + BAR5
        if bar_close_time >= c["deadline"]:
            break

        if c["side"] == "BUY_SIDE":
            trigger = cl[i] < c["reclaim_low"]
        else:
            trigger = cl[i] > c["reclaim_high"]

        if not trigger:
            continue

        entry_i = i + 1
        if idx[entry_i] >= c["deadline"]:
            return None
        return entry_i, idx[entry_i], float(op[entry_i])
    return None


def adverse_excursion_positive(x5: pd.DataFrame, c: dict, fill_i: int, entry: float):
    idx = x5.index
    end = int(idx.searchsorted(c["outcome_known_time"], side="left"))
    end = max(end, fill_i + 1)
    end = min(end, len(x5))
    q = x5.iloc[fill_i:end]
    if q.empty:
        return np.nan
    if c["side"] == "BUY_SIDE":
        adverse = float(q.high.max()) - entry
    else:
        adverse = entry - float(q.low.min())
    return max(0.0, adverse) / c["range_unit"]


def eval_variant(pop: pd.DataFrame, h1: pd.DataFrame, x5: pd.DataFrame, variant: str):
    rows = []

    for _, r in pop.iterrows():
        c = event_context(r, h1, x5)
        if c is None:
            continue

        if variant == "BASELINE_MARKET":
            fill = (c["baseline_i_5m"], c["baseline_time"], c["baseline_price"])
        elif variant == "FIVE_MIN_REVERSAL_BREAK":
            fill = fill_break(x5, c)
        else:
            fill = fill_limit(x5, c, limit_price(variant, c))

        base = {
            "variant": variant,
            "candidate_id": r.candidate_id,
            "side": r.side,
            "sweep_time": r.sweep_time,
            "reclaim_time": r.reclaim_time,
            "signal_time": c["signal_time"],
            "deadline": c["deadline"],
            "outcome": r.outcome,
            "event_label": int(r.event_label),
            "anatomy_score": int(r.anatomy_score),
            "baseline_entry_time": c["baseline_time"],
            "baseline_entry_price": c["baseline_price"],
            "range_unit": c["range_unit"],
            "structural_target": c["structural_target"],
            "filled": int(fill is not None),
        }

        if fill is None:
            rows.append({
                **base,
                "entry_i_5m": -1,
                "entry_time": pd.NaT,
                "entry_price": np.nan,
                "time_to_fill_min": np.nan,
                "directional_improvement_range_units": np.nan,
                "structural_target_distance_range_units": np.nan,
                "positive_adverse_excursion_range_units": np.nan,
            })
            continue

        fill_i, fill_time, entry = fill

        if c["side"] == "BUY_SIDE":
            improvement = (entry - c["baseline_price"]) / c["range_unit"]
            target_dist = (entry - c["structural_target"]) / c["range_unit"]
        else:
            improvement = (c["baseline_price"] - entry) / c["range_unit"]
            target_dist = (c["structural_target"] - entry) / c["range_unit"]

        ae = np.nan
        if int(r.event_label) == 1:
            ae = adverse_excursion_positive(x5, c, fill_i, entry)

        rows.append({
            **base,
            "entry_i_5m": int(fill_i),
            "entry_time": fill_time,
            "entry_price": float(entry),
            "time_to_fill_min": float((fill_time - c["signal_time"]).total_seconds() / 60.0),
            "directional_improvement_range_units": float(improvement),
            "structural_target_distance_range_units": float(target_dist),
            "positive_adverse_excursion_range_units": float(ae) if np.isfinite(ae) else np.nan,
        })

    return pd.DataFrame(rows)


def metrics(rows: pd.DataFrame, variant: str):
    g = rows[rows.variant == variant].copy()
    if g.empty:
        return {}

    filled = g[g.filled == 1].copy()
    pos = g[g.event_label == 1].copy()
    neg = g[g.event_label == 0].copy()
    pos_fill = filled[filled.event_label == 1].copy()

    def med(s):
        s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        return float(s.median()) if len(s) else np.nan

    def q25(s):
        s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        return float(s.quantile(.25)) if len(s) else np.nan

    out = {
        "variant": variant,
        "signal_n": len(g),
        "filled_n": len(filled),
        "fill_rate": len(filled) / len(g) if len(g) else np.nan,
        "positive_n": len(pos),
        "positive_filled_n": len(pos_fill),
        "positive_capture_rate": len(pos_fill) / len(pos) if len(pos) else np.nan,
        "negative_n": len(neg),
        "negative_filled_n": int(((g.event_label == 0) & (g.filled == 1)).sum()),
        "negative_fill_rate": float(((neg.filled == 1).mean())) if len(neg) else np.nan,
        "filled_event_rate": float(filled.event_label.mean()) if len(filled) else np.nan,
        "detector_baseline_rate": float(g.event_label.mean()),
        "median_time_to_fill_min": med(filled.time_to_fill_min),
        "median_improvement_all": med(filled.directional_improvement_range_units),
        "median_improvement_positive": med(pos_fill.directional_improvement_range_units),
        "p25_improvement_positive": q25(pos_fill.directional_improvement_range_units),
        "median_target_distance_positive": med(pos_fill.structural_target_distance_range_units),
        "median_positive_adverse_excursion": med(pos_fill.positive_adverse_excursion_range_units),
    }

    for side in ("BUY_SIDE", "SELL_SIDE"):
        z = g[(g.side == side) & (g.event_label == 1)]
        out[f"{side.lower()}_positive_n"] = len(z)
        out[f"{side.lower()}_positive_filled_n"] = int((z.filled == 1).sum())
        out[f"{side.lower()}_positive_capture"] = float((z.filled == 1).mean()) if len(z) else np.nan

    return out


def construction_table(pop, h1, x5):
    all_rows = []
    mrows = []

    for v in VARIANTS:
        r = eval_variant(pop, h1, x5, v)
        all_rows.append(r)
        mrows.append(metrics(r, v))

    rows = pd.concat(all_rows, ignore_index=True)
    m = pd.DataFrame(mrows)

    baseline = float(pop.event_label.mean())
    adaptive = m[m.variant != "BASELINE_MARKET"].copy()
    adaptive["eligible"] = (
        (adaptive.filled_n >= 150)
        & (adaptive.positive_capture_rate >= .70)
        & (adaptive.filled_event_rate >= baseline - .03)
        & (adaptive.median_improvement_positive > 0)
        & (adaptive.p25_improvement_positive >= -.05)
        & (adaptive.buy_side_positive_capture >= .60)
        & (adaptive.sell_side_positive_capture >= .60)
    )

    elig = adaptive[adaptive.eligible].copy()
    winner = None
    if len(elig):
        elig = elig.sort_values(
            [
                "median_improvement_positive",
                "p25_improvement_positive",
                "positive_capture_rate",
                "filled_event_rate",
                "median_time_to_fill_min",
                "variant",
            ],
            ascending=[False, False, False, False, True, True],
        )
        winner = elig.iloc[0].to_dict()

    return rows, m, winner


def confirmation_pass(m: dict):
    gates = {
        "filled_n_ge_40": int(m["filled_n"]) >= 40,
        "positive_capture_ge_65pct": bool(np.isfinite(m["positive_capture_rate"]) and m["positive_capture_rate"] >= .65),
        "filled_event_rate_not_below_baseline_minus_5pp": bool(
            np.isfinite(m["filled_event_rate"]) and m["filled_event_rate"] >= m["detector_baseline_rate"] - .05
        ),
        "median_positive_improvement_gt_0": bool(
            np.isfinite(m["median_improvement_positive"]) and m["median_improvement_positive"] > 0
        ),
        "buy_positive_capture_ge_55pct": bool(
            np.isfinite(m["buy_side_positive_capture"]) and m["buy_side_positive_capture"] >= .55
        ),
        "sell_positive_capture_ge_55pct": bool(
            np.isfinite(m["sell_side_positive_capture"]) and m["sell_side_positive_capture"] >= .55
        ),
    }
    return gates


def holdout_verdict(m: dict):
    sample = {
        "detector_signals_n_ge_30": int(m["signal_n"]) >= 30,
        "filled_n_ge_20": int(m["filled_n"]) >= 20,
        "positive_n_ge_10": int(m["positive_n"]) >= 10,
    }

    quality = {
        "positive_capture_ge_60pct": bool(np.isfinite(m["positive_capture_rate"]) and m["positive_capture_rate"] >= .60),
        "filled_event_rate_not_below_baseline_minus_5pp": bool(
            np.isfinite(m["filled_event_rate"]) and m["filled_event_rate"] >= m["detector_baseline_rate"] - .05
        ),
        "median_positive_improvement_gt_0": bool(
            np.isfinite(m["median_improvement_positive"]) and m["median_improvement_positive"] > 0
        ),
    }

    for side in ("buy_side", "sell_side"):
        pn = int(m[f"{side}_positive_n"])
        cap = m[f"{side}_positive_capture"]
        quality[f"{side}_capture_ge_50pct_if_n_ge5"] = bool(pn < 5 or (np.isfinite(cap) and cap >= .50))

    if not all(sample.values()):
        verdict = "2026_ENTRY_HOLDOUT_INSUFFICIENT_SAMPLE"
    elif all(quality.values()):
        verdict = "VALIDATED_ADAPTIVE_ENTRY"
    else:
        verdict = "ADAPTIVE_ENTRY_NOT_VALIDATED_AS_DEFINED"

    return sample, quality, verdict


def main():
    x5, coverage = v3.load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Pass 1: construction only. 2025 and 2026 are not processed by the structural engine.
    construction, h1c = actionable_detector_population(x5, CONSTRUCTION_END, [2020, 2021, 2022, 2023, 2024])
    crows, cmetrics, winner = construction_table(construction, h1c, x5[x5.index < CONSTRUCTION_END])

    crows.to_csv(ROOT / f"{PFX}_ConstructionEntries.csv", index=False)
    cmetrics.to_csv(ROOT / f"{PFX}_ConstructionMetrics.csv", index=False)

    if winner is None:
        verdict = "NO_ADAPTIVE_ENTRY_CONSTRUCTION_RULE"
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Confirmation2025Entries.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Confirmation2025Metrics.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2026Entries.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2026Metrics.csv", index=False)

        summary = pd.DataFrame([{
            "coverage": coverage,
            "construction_signal_n": len(construction),
            "winner": "",
            "confirmation_2025_opened": False,
            "holdout_2026_opened": False,
            "verdict": verdict,
        }])
        summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

        lines = [
            "# SOL Adaptive Entry V1 — Result", "",
            f"- Coverage: **{coverage*100:.6f}%**",
            f"- Construction actionable detector signals: **{len(construction)}**",
            "- No adaptive entry variant met the frozen construction gates.",
            "- 2025 was not opened for entry confirmation.",
            "- 2026 remained unopened.",
            "",
            f"**VERDICT: {verdict}**",
            "",
            "2027_PLUS=CLOSED",
        ]
    else:
        winner_name = str(winner["variant"])

        # Pass 2: only after winner is frozen, process through 2025.
        p25, h125 = actionable_detector_population(x5, CONFIRM_END, [2025])
        x25 = x5[x5.index < CONFIRM_END]
        r25 = eval_variant(p25, h125, x25, winner_name)
        m25 = metrics(r25, winner_name)
        gates25 = confirmation_pass(m25)
        pass25 = all(gates25.values())

        r25.to_csv(ROOT / f"{PFX}_Confirmation2025Entries.csv", index=False)
        pd.DataFrame([{**m25, **{f"gate_{k}": v for k, v in gates25.items()}}]).to_csv(
            ROOT / f"{PFX}_Confirmation2025Metrics.csv", index=False
        )

        if not pass25:
            verdict = "ADAPTIVE_ENTRY_NOT_CONFIRMED_2025"
            pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2026Entries.csv", index=False)
            pd.DataFrame().to_csv(ROOT / f"{PFX}_Holdout2026Metrics.csv", index=False)

            summary = pd.DataFrame([{
                "coverage": coverage,
                "construction_signal_n": len(construction),
                "winner": winner_name,
                "construction_filled_n": int(winner["filled_n"]),
                "construction_positive_capture": float(winner["positive_capture_rate"]),
                "construction_positive_improvement": float(winner["median_improvement_positive"]),
                "confirmation_2025_opened": True,
                "confirmation_2025_passed": False,
                "holdout_2026_opened": False,
                "verdict": verdict,
            }])
            summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

            lines = [
                "# SOL Adaptive Entry V1 — Result", "",
                f"- Coverage: **{coverage*100:.6f}%**",
                f"- Frozen construction winner: **{winner_name}**",
                f"- Construction positive-event capture: **{winner['positive_capture_rate']*100:.2f}%**",
                f"- Construction median positive improvement: **{winner['median_improvement_positive']:.4f} H1 range units**",
                "",
                "## Frozen 2025 confirmation", "",
                f"- Signals: **{m25['signal_n']}**",
                f"- Filled: **{m25['filled_n']}**",
                f"- Positive-event capture: **{m25['positive_capture_rate']*100:.2f}%**",
                f"- Filled structural-event rate: **{m25['filled_event_rate']*100:.2f}%** vs detector baseline **{m25['detector_baseline_rate']*100:.2f}%**",
                f"- Median positive improvement: **{m25['median_improvement_positive']:.4f} range units**",
                "",
                "## 2025 gate audit", "",
            ]
            for k, v in gates25.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines += [
                "",
                f"**VERDICT: {verdict}**",
                "- 2026 remained unopened.",
                "",
                "2027_PLUS=CLOSED",
            ]
        else:
            # Pass 3: now open 2026 YTD.
            latest_end = (x5.index.max() + BAR5).floor("h")
            if latest_end <= CONFIRM_END:
                latest_end = CONFIRM_END

            p26, h126 = actionable_detector_population(x5, latest_end, [2026])
            x26 = x5[x5.index < latest_end]
            r26 = eval_variant(p26, h126, x26, winner_name)
            m26 = metrics(r26, winner_name) if len(r26) else {
                "variant": winner_name, "signal_n": 0, "filled_n": 0,
                "positive_n": 0, "positive_capture_rate": np.nan,
                "filled_event_rate": np.nan, "detector_baseline_rate": np.nan,
                "median_improvement_positive": np.nan,
                "buy_side_positive_n": 0, "buy_side_positive_capture": np.nan,
                "sell_side_positive_n": 0, "sell_side_positive_capture": np.nan,
            }
            sample26, quality26, verdict = holdout_verdict(m26)

            r26.to_csv(ROOT / f"{PFX}_Holdout2026Entries.csv", index=False)
            pd.DataFrame([{
                **m26,
                "data_end": latest_end,
                **{f"sample_{k}": v for k, v in sample26.items()},
                **{f"gate_{k}": v for k, v in quality26.items()},
                "verdict": verdict,
            }]).to_csv(ROOT / f"{PFX}_Holdout2026Metrics.csv", index=False)

            summary = pd.DataFrame([{
                "coverage": coverage,
                "construction_signal_n": len(construction),
                "winner": winner_name,
                "construction_filled_n": int(winner["filled_n"]),
                "construction_positive_capture": float(winner["positive_capture_rate"]),
                "construction_filled_event_rate": float(winner["filled_event_rate"]),
                "construction_positive_improvement": float(winner["median_improvement_positive"]),
                "confirmation_2025_opened": True,
                "confirmation_2025_passed": True,
                "confirmation_2025_signal_n": int(m25["signal_n"]),
                "confirmation_2025_filled_n": int(m25["filled_n"]),
                "confirmation_2025_positive_capture": float(m25["positive_capture_rate"]),
                "confirmation_2025_positive_improvement": float(m25["median_improvement_positive"]),
                "holdout_2026_opened": True,
                "holdout_2026_data_end": latest_end,
                "holdout_2026_signal_n": int(m26["signal_n"]),
                "holdout_2026_filled_n": int(m26["filled_n"]),
                "holdout_2026_positive_n": int(m26["positive_n"]),
                "holdout_2026_positive_capture": float(m26["positive_capture_rate"]) if np.isfinite(m26["positive_capture_rate"]) else np.nan,
                "holdout_2026_positive_improvement": float(m26["median_improvement_positive"]) if np.isfinite(m26["median_improvement_positive"]) else np.nan,
                "verdict": verdict,
            }])
            summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

            def pct(v):
                return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

            lines = [
                "# SOL Adaptive Entry V1 — Result", "",
                f"- 5m coverage: **{coverage*100:.6f}%**",
                f"- Frozen construction winner: **{winner_name}**",
                "- Actionable detector frozen at SCORE>=3; same-reclaim-bar outcomes excluded.",
                "- No SL, TP, PnL, hour, indicator, or regime optimization.",
                "",
                "## Construction 2020-2024", "",
                f"- Detector signals: **{len(construction)}**",
                f"- Winner fills: **{int(winner['filled_n'])}**",
                f"- Positive-event capture: **{winner['positive_capture_rate']*100:.2f}%**",
                f"- Filled structural-event rate: **{winner['filled_event_rate']*100:.2f}%** vs detector baseline **{winner['detector_baseline_rate']*100:.2f}%**",
                f"- Median positive price improvement: **{winner['median_improvement_positive']:.4f} H1 range units**",
                f"- P25 positive improvement: **{winner['p25_improvement_positive']:.4f}**",
                f"- Median time to fill: **{winner['median_time_to_fill_min']:.1f} min**",
                "",
                "## Frozen 2025 confirmation", "",
                f"- Signals: **{m25['signal_n']}**",
                f"- Filled: **{m25['filled_n']}**",
                f"- Positive events: **{m25['positive_n']}**, filled **{m25['positive_filled_n']}**",
                f"- Positive-event capture: **{pct(m25['positive_capture_rate'])}**",
                f"- Filled structural-event rate: **{pct(m25['filled_event_rate'])}** vs detector baseline **{pct(m25['detector_baseline_rate'])}**",
                f"- Median positive improvement: **{m25['median_improvement_positive']:.4f} range units**",
                f"- BUY positive capture: **{pct(m25['buy_side_positive_capture'])}**",
                f"- SELL positive capture: **{pct(m25['sell_side_positive_capture'])}**",
                "",
                "## Untouched 2026 YTD", "",
                f"- Data through: **{latest_end}**",
                f"- Detector signals: **{m26['signal_n']}**",
                f"- Filled: **{m26['filled_n']}**",
                f"- Positive events: **{m26['positive_n']}**",
                f"- Positive-event capture: **{pct(m26['positive_capture_rate'])}**",
                f"- Filled structural-event rate: **{pct(m26['filled_event_rate'])}** vs detector baseline **{pct(m26['detector_baseline_rate'])}**",
                f"- Median positive improvement: **{m26['median_improvement_positive']:.4f} range units**" if np.isfinite(m26["median_improvement_positive"]) else "- Median positive improvement: **n/a**",
                f"- BUY positive capture: **{pct(m26['buy_side_positive_capture'])}**",
                f"- SELL positive capture: **{pct(m26['sell_side_positive_capture'])}**",
                "",
                "## 2026 sample audit", "",
            ]
            for k, v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines += ["", "## 2026 quality audit", ""]
            for k, v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines += [
                "",
                f"**VERDICT: {verdict}**",
                "",
                "This verdict concerns execution timing/location only. SL and TP remain undiscovered.",
                "",
                "2027_PLUS=CLOSED",
            ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n2027_PLUS=CLOSED\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
