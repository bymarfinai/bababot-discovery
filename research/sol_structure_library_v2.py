#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_structure_library_v1 as v1
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURE_LIBRARY_V2"
STRUCTURES = (
    "FAILED_BREAKDOWN_RECLAIM",
    "INSIDE_BAR_COMPRESSION_BREAKOUT",
    "MATURE_HH_HL_CONTINUATION",
    "BREAKOUT_HOLD_CONTINUATION",
)
YEARS = v1.YEARS


def latest_high_between(high_hist: list[dict], a: int, b: int):
    for h in reversed(high_hist):
        if a < h["pivot_i"] < b:
            return h
        if h["pivot_i"] <= a:
            break
    return None


def detect_all(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = v1.compute_pivots(hi, lo)

    low_hist: list[dict] = []
    high_hist: list[dict] = []
    rows: list[dict] = []

    # Detector 1 state.
    latest_low_anchor = None
    failed_break = None

    # Detector 3 state.
    mature_candidate = None

    # Detector 4 state.
    latest_high_anchor = None
    used_breakout_highs: set[int] = set()
    hold_event = None

    start = max(v1.TRAIL_BARS - 1, v1.PIVOT_ORDER + 4)
    for i in range(start, len(x5) - v1.FUTURE_BARS - 1):
        # Confirm newly knowable pivots first. A pivot confirmed on bar i may be
        # used by signals at i because the entire confirmation bar is completed.
        for h in highs_by_confirm.get(i, []):
            high_hist.append(h)
            if h["pivot_i"] not in used_breakout_highs:
                latest_high_anchor = h

        for l3 in lows_by_confirm.get(i, []):
            # Build mature HH-HL candidate from L1-H1-L2-H2-L3.
            if len(low_hist) >= 2:
                l1 = low_hist[-2]
                l2 = low_hist[-1]
                h1 = latest_high_between(high_hist, l1["pivot_i"], l2["pivot_i"])
                h2 = latest_high_between(high_hist, l2["pivot_i"], l3["pivot_i"])
                if (
                    h1 is not None and h2 is not None
                    and l2["price"] > l1["price"]
                    and h2["price"] > h1["price"]
                    and l3["price"] > l2["price"]
                ):
                    mature_candidate = {"l1": l1, "h1": h1, "l2": l2, "h2": h2, "l3": l3}
                else:
                    mature_candidate = None

            low_hist.append(l3)
            latest_low_anchor = l3
            # A newly confirmed pivot low supersedes any older pending failed-breakdown anchor.
            failed_break = None

        # 1) FAILED_BREAKDOWN_RECLAIM.
        if failed_break is not None:
            if i > failed_break["deadline_i"]:
                failed_break = None
            elif cl[i] > failed_break["level"]:
                v1.add_signal(rows, "FAILED_BREAKDOWN_RECLAIM", i, idx, op, hi, lo, cl, {
                    "anchor_level": float(failed_break["level"]),
                    "anchor_pivot_i": int(failed_break["pivot_i"]),
                    "secondary_level": np.nan,
                    "secondary_pivot_i": -1,
                })
                failed_break = None
        if (
            failed_break is None and latest_low_anchor is not None
            and i > latest_low_anchor["confirm_i"]
            and cl[i] < latest_low_anchor["price"]
        ):
            failed_break = {
                "level": float(latest_low_anchor["price"]),
                "pivot_i": int(latest_low_anchor["pivot_i"]),
                "break_i": i,
                "deadline_i": i + 3,
            }

        # 2) INSIDE_BAR_COMPRESSION_BREAKOUT: mother + 2 inside bars + breakout.
        m = i - 3
        if m >= 0:
            inside1 = hi[i-2] <= hi[m] and lo[i-2] >= lo[m]
            inside2 = hi[i-1] <= hi[m] and lo[i-1] >= lo[m]
            if inside1 and inside2 and cl[i] > hi[m]:
                v1.add_signal(rows, "INSIDE_BAR_COMPRESSION_BREAKOUT", i, idx, op, hi, lo, cl, {
                    "anchor_level": float(hi[m]),
                    "anchor_pivot_i": int(m),
                    "secondary_level": float(lo[m]),
                    "secondary_pivot_i": int(m),
                })

        # 3) MATURE_HH_HL_CONTINUATION.
        if mature_candidate is not None:
            support = float(mature_candidate["l3"]["price"])
            trigger = float(mature_candidate["h2"]["price"])
            if cl[i] < support:
                mature_candidate = None
            elif i > mature_candidate["l3"]["confirm_i"] and cl[i] > trigger:
                v1.add_signal(rows, "MATURE_HH_HL_CONTINUATION", i, idx, op, hi, lo, cl, {
                    "anchor_level": trigger,
                    "anchor_pivot_i": int(mature_candidate["h2"]["pivot_i"]),
                    "secondary_level": support,
                    "secondary_pivot_i": int(mature_candidate["l3"]["pivot_i"]),
                })
                mature_candidate = None

        # 4) BREAKOUT_HOLD_CONTINUATION.
        if hold_event is not None:
            if i <= hold_event["breakout_i"]:
                pass
            elif cl[i] <= hold_event["level"]:
                hold_event = None
            else:
                hold_event["hold_count"] += 1
                if hold_event["hold_count"] == 3:
                    v1.add_signal(rows, "BREAKOUT_HOLD_CONTINUATION", i, idx, op, hi, lo, cl, {
                        "anchor_level": float(hold_event["level"]),
                        "anchor_pivot_i": int(hold_event["pivot_i"]),
                        "secondary_level": np.nan,
                        "secondary_pivot_i": -1,
                    })
                    hold_event = None

        if hold_event is None and latest_high_anchor is not None:
            if (
                latest_high_anchor["pivot_i"] not in used_breakout_highs
                and i > latest_high_anchor["confirm_i"]
                and cl[i] > latest_high_anchor["price"]
            ):
                used_breakout_highs.add(int(latest_high_anchor["pivot_i"]))
                hold_event = {
                    "level": float(latest_high_anchor["price"]),
                    "pivot_i": int(latest_high_anchor["pivot_i"]),
                    "breakout_i": i,
                    "hold_count": 0,
                }
                latest_high_anchor = None

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no V2 structural events detected")
    out = out.sort_values(["structure", "entry_time", "signal_time"]).drop_duplicates(["structure", "entry_time"], keep="first")
    return out.reset_index(drop=True)


def summaries(events: pd.DataFrame):
    pooled_rows, year_rows = [], []
    for s in STRUCTURES:
        g = events[events.structure == s].copy()
        e = v1.econ(g)
        ratio = float(g.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(g) else np.nan
        clean = float(g.clean_up_impulse.mean()) if len(g) else np.nan
        pos_years = 0
        for y in YEARS:
            gy = g[g.year == y].copy()
            ey = v1.econ(gy)
            if ey["pnl_usd"] > 0:
                pos_years += 1
            year_rows.append({
                "structure": s, "year": y, "n": ey["n"], "wr60": ey["wr"],
                "expectancy60_pct": ey["expectancy_pct"], "pf60": ey["pf"],
                "pnl60_usd": ey["pnl_usd"], "max_dd_usd": ey["max_dd_usd"],
                "max_loss_streak": ey["max_loss_streak"],
                "clean_up_impulse_rate": float(gy.clean_up_impulse.mean()) if len(gy) else np.nan,
                "median_mfe_mae_ratio": float(gy.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(gy) else np.nan,
            })
        gates = {
            "n_ge_100": e["n"] >= 100,
            "expectancy_positive": bool(np.isfinite(e["expectancy_pct"]) and e["expectancy_pct"] > 0),
            "pf_ge_1_15": bool(np.isfinite(e["pf"]) and e["pf"] >= 1.15),
            "positive_pnl_years_ge_4_of_5": pos_years >= 4,
            "median_mfe_mae_ge_1_20": bool(np.isfinite(ratio) and ratio >= 1.20),
        }
        pooled_rows.append({
            "structure": s, "n": e["n"], "wr60": e["wr"], "expectancy60_pct": e["expectancy_pct"],
            "pf60": e["pf"], "pnl60_usd": e["pnl_usd"], "max_dd_usd": e["max_dd_usd"],
            "max_loss_streak": e["max_loss_streak"], "clean_up_impulse_rate": clean,
            "median_mfe60_pct": float(g.mfe60_pct.median()) if len(g) else np.nan,
            "median_mae60_pct": float(g.mae60_pct.median()) if len(g) else np.nan,
            "median_mfe_mae_ratio": ratio, "positive_pnl_years": pos_years,
            **{f"gate_{k}": v for k, v in gates.items()},
            "verdict": "PASS_TO_CHARACTERIZATION" if all(gates.values()) else "REJECTED_AS_DEFINED",
        })
    return pd.DataFrame(pooled_rows), pd.DataFrame(year_rows)


def overlap_table(events: pd.DataFrame) -> pd.DataFrame:
    times = {s: set(events.loc[events.structure == s, "entry_time"].tolist()) for s in STRUCTURES}
    rows = []
    for a in STRUCTURES:
        for b in STRUCTURES:
            ov = len(times[a] & times[b])
            rows.append({"structure_a": a, "structure_b": b, "overlap_n": ov,
                         "pct_of_a": ov / len(times[a]) if times[a] else np.nan,
                         "pct_of_b": ov / len(times[b]) if times[b] else np.nan})
    return pd.DataFrame(rows)


def pfmt(v):
    return v1.pfmt(v)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    events = detect_all(x5)
    pooled, yearly = summaries(events)
    overlap = overlap_table(events)

    events.to_csv(ROOT / f"{PFX}_Events.csv", index=False)
    pooled.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    overlap.to_csv(ROOT / f"{PFX}_Overlap.csv", index=False)

    lines = [
        "# SOL Structural Detector Library V2 — Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Total detected structure-events: **{len(events)}**",
        "- Evaluation: 2020-2024; 2025+ remained CLOSED.",
        "- Entry: next 5m open after causal structure signal; fixed +60m diagnostic; 0.15% RT cost.", "",
        "## Pooled detector scorecard", "",
        "| Structure | N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE | MAE | MFE/MAE | Positive years | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in pooled.iterrows():
        lines.append(f"| {r.structure} | {int(r.n)} | {float(r.wr60)*100:.2f}% | {float(r.expectancy60_pct):.4f}% | {pfmt(r.pf60)} | ${float(r.pnl60_usd):.2f} | ${float(r.max_dd_usd):.2f} | {int(r.max_loss_streak)} | {float(r.clean_up_impulse_rate)*100:.2f}% | {float(r.median_mfe60_pct):.3f}% | {float(r.median_mae60_pct):.3f}% | {float(r.median_mfe_mae_ratio):.3f} | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |")

    lines += ["", "## Per-year economics", ""]
    for s in STRUCTURES:
        lines += [f"### {s}", "", "| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in yearly[yearly.structure == s].iterrows():
            wr = float(r.wr60)*100 if np.isfinite(r.wr60) else np.nan
            ex = float(r.expectancy60_pct) if np.isfinite(r.expectancy60_pct) else np.nan
            ci = float(r.clean_up_impulse_rate)*100 if np.isfinite(r.clean_up_impulse_rate) else np.nan
            rr = float(r.median_mfe_mae_ratio) if np.isfinite(r.median_mfe_mae_ratio) else np.nan
            lines.append(f"| {int(r.year)} | {int(r.n)} | {wr:.2f}% | {ex:.4f}% | {pfmt(r.pf60)} | ${float(r.pnl60_usd):.2f} | {ci:.2f}% | {rr:.3f} |")
        lines.append("")

    lines += ["## Frozen gate audit", ""]
    gate_names = ["n_ge_100", "expectancy_positive", "pf_ge_1_15", "positive_pnl_years_ge_4_of_5", "median_mfe_mae_ge_1_20"]
    for _, r in pooled.iterrows():
        lines.append(f"### {r.structure} — {r.verdict}")
        for g in gate_names:
            lines.append(f"- {'PASS' if bool(r['gate_'+g]) else 'FAIL'} — `{g}`")
        lines.append("")
    lines += [
        "## Interpretation rule", "",
        "PASS_TO_CHARACTERIZATION means this exact structure may advance to its own structure-specific execution/TP/SL characterization stage.",
        "REJECTED_AS_DEFINED means do not rescue this exact detector on 2020-2024 by changing its structural definition, hours, indicators, TP or SL; move to a different explicitly defined structure.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    passing = pooled.loc[pooled.verdict == "PASS_TO_CHARACTERIZATION", "structure"].tolist()
    status = "PASSING_STRUCTURES=" + (",".join(passing) if passing else "NONE")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print(text)
    print(status)


if __name__ == "__main__":
    main()
