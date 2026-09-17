#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_structure_library_v1 as v1
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURE_TRIGGER_MATRIX_V1"
YEARS = v1.YEARS
STRUCTURES = (
    "SWEEP_RECLAIM",
    "HL_SETUP",
    "BREAKOUT_PULLBACK_SETUP",
    "FAILED_BREAKDOWN_RECLAIM",
)
TRIGGERS = (
    "MICRO_BOS",
    "BULLISH_DISPLACEMENT",
    "PULLBACK_RESUME",
)
COMBOS = tuple(f"{s}__{t}" for s in STRUCTURES for t in TRIGGERS)
TRIGGER_MAX_BARS = 6
DISP_BODY_MULT = 1.5
DISP_CLOSE_LOC = 0.75
BODY_LOOKBACK = 20


def latest_high_between(high_hist: list[dict], a: int, b: int):
    for h in reversed(high_hist):
        if a < h["pivot_i"] < b:
            return h
        if h["pivot_i"] <= a:
            break
    return None


def latest_unconsumed_high(high_hist: list[dict], consumed: set[int]):
    for h in reversed(high_hist):
        if h["pivot_i"] not in consumed:
            return h
    return None


def add_setup(rows: list[dict], structure: str, setup_i: int, idx, invalid_level: float,
              anchor_level: float, anchor_pivot_i: int, secondary_level=np.nan,
              secondary_pivot_i: int = -1):
    if setup_i < max(v1.TRAIL_BARS - 1, BODY_LOOKBACK - 1):
        return
    t = idx[setup_i]
    if t < v1.MODEL_START or t >= v1.MODEL_END:
        return
    rows.append({
        "structure": structure,
        "setup_i": int(setup_i),
        "setup_time": t,
        "year": int(t.year),
        "invalid_level": float(invalid_level),
        "anchor_level": float(anchor_level),
        "anchor_pivot_i": int(anchor_pivot_i),
        "secondary_level": float(secondary_level) if np.isfinite(secondary_level) else np.nan,
        "secondary_pivot_i": int(secondary_pivot_i),
    })


def detect_setups(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = v1.compute_pivots(hi, lo)

    low_hist: list[dict] = []
    high_hist: list[dict] = []
    rows: list[dict] = []

    # Sweep-reclaim state.
    sweep_anchor = None

    # Failed-breakdown state.
    failed_anchor = None
    failed_break = None

    # Breakout-pullback state.
    consumed_highs: set[int] = set()
    bo_anchor = None
    bo_event = None

    start = max(v1.TRAIL_BARS - 1, v1.PIVOT_ORDER + 4)
    for i in range(start, len(x5) - v1.FUTURE_BARS - TRIGGER_MAX_BARS - 2):
        # Newly confirmed highs.
        for h in highs_by_confirm.get(i, []):
            high_hist.append(h)
            if bo_event is None and h["pivot_i"] not in consumed_highs:
                bo_anchor = h

        # Newly confirmed lows.
        for l2 in lows_by_confirm.get(i, []):
            # BREAKOUT_PULLBACK_SETUP: first confirmed pivot low after breakout.
            if bo_event is not None and l2["pivot_i"] > bo_event["breakout_i"]:
                level = float(bo_event["level"])
                no_close_loss = bool(np.all(cl[bo_event["breakout_i"] + 1:i + 1] >= level)) if i > bo_event["breakout_i"] else True
                pivot_bar_reclaim = bool(lo[l2["pivot_i"]] <= level and cl[l2["pivot_i"]] > level)
                if no_close_loss and pivot_bar_reclaim:
                    add_setup(
                        rows, "BREAKOUT_PULLBACK_SETUP", i, idx,
                        invalid_level=level,
                        anchor_level=level,
                        anchor_pivot_i=int(bo_event["high_pivot_i"]),
                        secondary_level=float(l2["price"]),
                        secondary_pivot_i=int(l2["pivot_i"]),
                    )
                bo_event = None
                bo_anchor = latest_unconsumed_high(high_hist, consumed_highs)

            prev_low = low_hist[-1] if low_hist else None
            h1 = latest_high_between(high_hist, prev_low["pivot_i"], l2["pivot_i"]) if prev_low is not None else None
            if prev_low is not None and h1 is not None and l2["price"] > prev_low["price"]:
                add_setup(
                    rows, "HL_SETUP", i, idx,
                    invalid_level=float(l2["price"]),
                    anchor_level=float(h1["price"]),
                    anchor_pivot_i=int(h1["pivot_i"]),
                    secondary_level=float(l2["price"]),
                    secondary_pivot_i=int(l2["pivot_i"]),
                )

            low_hist.append(l2)
            sweep_anchor = l2
            failed_anchor = l2
            failed_break = None

        # SWEEP_RECLAIM structure completes on reclaim close.
        if sweep_anchor is not None and i > sweep_anchor["confirm_i"]:
            level = float(sweep_anchor["price"])
            if cl[i] < level:
                sweep_anchor = None
            elif lo[i] < level and cl[i] > level:
                add_setup(
                    rows, "SWEEP_RECLAIM", i, idx,
                    invalid_level=level,
                    anchor_level=level,
                    anchor_pivot_i=int(sweep_anchor["pivot_i"]),
                )
                sweep_anchor = None

        # FAILED_BREAKDOWN_RECLAIM structure completes after a close-below then reclaim <=3 bars.
        if failed_break is not None:
            if i > failed_break["deadline_i"]:
                failed_break = None
            elif cl[i] > failed_break["level"]:
                add_setup(
                    rows, "FAILED_BREAKDOWN_RECLAIM", i, idx,
                    invalid_level=float(failed_break["level"]),
                    anchor_level=float(failed_break["level"]),
                    anchor_pivot_i=int(failed_break["pivot_i"]),
                )
                failed_break = None
        if (
            failed_break is None and failed_anchor is not None
            and i > failed_anchor["confirm_i"] and cl[i] < failed_anchor["price"]
        ):
            failed_break = {
                "level": float(failed_anchor["price"]),
                "pivot_i": int(failed_anchor["pivot_i"]),
                "break_i": int(i),
                "deadline_i": int(i + 3),
            }

        # Breakout state for future BREAKOUT_PULLBACK_SETUP.
        if bo_event is not None and i > bo_event["breakout_i"] and cl[i] < bo_event["level"]:
            bo_event = None
            bo_anchor = latest_unconsumed_high(high_hist, consumed_highs)
        if bo_event is None:
            if bo_anchor is None:
                bo_anchor = latest_unconsumed_high(high_hist, consumed_highs)
            if bo_anchor is not None and i > bo_anchor["confirm_i"] and cl[i] > bo_anchor["price"]:
                consumed_highs.add(int(bo_anchor["pivot_i"]))
                bo_event = {
                    "level": float(bo_anchor["price"]),
                    "high_pivot_i": int(bo_anchor["pivot_i"]),
                    "breakout_i": int(i),
                }
                bo_anchor = None

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no structural setups detected")
    out = out.sort_values(["structure", "setup_time"]).drop_duplicates(["structure", "setup_time"], keep="first")
    return out.reset_index(drop=True)


def trigger_fires(trigger: str, setup_i: int, i: int, op, hi, lo, cl, body_ref: float) -> bool:
    j = i - setup_i
    if trigger == "MICRO_BOS":
        if j < 4:
            return False
        return bool(cl[i] > float(np.max(hi[i-3:i])))

    if trigger == "BULLISH_DISPLACEMENT":
        rng = float(hi[i] - lo[i])
        if rng <= 0 or not np.isfinite(body_ref) or body_ref <= 0:
            return False
        body = float(cl[i] - op[i])
        close_loc = float((cl[i] - lo[i]) / rng)
        return bool(body > 0 and body >= DISP_BODY_MULT * body_ref and close_loc >= DISP_CLOSE_LOC)

    if trigger == "PULLBACK_RESUME":
        if j < 2:
            return False
        prior_pullback = any(cl[k] < cl[k-1] for k in range(setup_i + 1, i))
        return bool(prior_pullback and cl[i] > op[i] and cl[i] > hi[i-1])

    raise ValueError(trigger)


def apply_triggers(setups: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    rows: list[dict] = []

    for _, s in setups.iterrows():
        setup_i = int(s.setup_i)
        if setup_i - BODY_LOOKBACK + 1 < 0:
            continue
        body_hist = np.abs(cl[setup_i - BODY_LOOKBACK + 1:setup_i + 1] - op[setup_i - BODY_LOOKBACK + 1:setup_i + 1])
        body_ref = float(np.median(body_hist))

        for trigger in TRIGGERS:
            fired = False
            for i in range(setup_i + 1, min(setup_i + TRIGGER_MAX_BARS + 1, len(x5) - v1.FUTURE_BARS - 1)):
                # Structure invalidates before a trigger if a completed close loses invalidation level.
                if cl[i] < float(s.invalid_level):
                    break
                if trigger_fires(trigger, setup_i, i, op, hi, lo, cl, body_ref):
                    combo = f"{s.structure}__{trigger}"
                    v1.add_signal(rows, combo, i, idx, op, hi, lo, cl, {
                        "context_structure": str(s.structure),
                        "entry_trigger": trigger,
                        "setup_time": s.setup_time,
                        "setup_i": setup_i,
                        "bars_after_setup": int(i - setup_i),
                        "minutes_after_setup": int((i - setup_i) * 5),
                        "anchor_level": float(s.anchor_level),
                        "anchor_pivot_i": int(s.anchor_pivot_i),
                        "secondary_level": float(s.secondary_level) if np.isfinite(s.secondary_level) else np.nan,
                        "secondary_pivot_i": int(s.secondary_pivot_i),
                    })
                    fired = True
                    break
            # Explicit for readability; each trigger is independent per setup.
            if fired:
                continue

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no triggered trades detected")
    out = out.sort_values(["structure", "entry_time", "setup_time"]).drop_duplicates(["structure", "entry_time", "setup_time"], keep="first")
    return out.reset_index(drop=True)


def summarize(setups: pd.DataFrame, trades: pd.DataFrame):
    pooled_rows, year_rows = [], []
    setup_counts = setups.groupby("structure").size().to_dict()

    for combo in COMBOS:
        structure, trigger = combo.split("__", 1)
        g = trades[trades.structure == combo].copy()
        e = v1.econ(g)
        ratio = float(g.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(g) else np.nan
        clean = float(g.clean_up_impulse.mean()) if len(g) else np.nan
        setup_n = int(setup_counts.get(structure, 0))
        pos_years = 0
        for y in YEARS:
            gy = g[g.year == y].copy()
            ey = v1.econ(gy)
            if ey["pnl_usd"] > 0:
                pos_years += 1
            year_rows.append({
                "combo": combo,
                "structure": structure,
                "trigger": trigger,
                "year": y,
                "n": ey["n"],
                "wr60": ey["wr"],
                "expectancy60_pct": ey["expectancy_pct"],
                "pf60": ey["pf"],
                "pnl60_usd": ey["pnl_usd"],
                "max_dd_usd": ey["max_dd_usd"],
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
            "combo": combo,
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
            "clean_up_impulse_rate": clean,
            "median_mfe60_pct": float(g.mfe60_pct.median()) if len(g) else np.nan,
            "median_mae60_pct": float(g.mae60_pct.median()) if len(g) else np.nan,
            "median_mfe_mae_ratio": ratio,
            "median_trigger_delay_min": float(g.minutes_after_setup.median()) if len(g) else np.nan,
            "positive_pnl_years": pos_years,
            **{f"gate_{k}": v for k, v in gates.items()},
            "verdict": "PASS_TO_CHARACTERIZATION" if all(gates.values()) else "REJECTED_AS_DEFINED",
        })
    return pd.DataFrame(pooled_rows), pd.DataFrame(year_rows)


def pfmt(v):
    return v1.pfmt(v)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    setups = detect_setups(x5)
    trades = apply_triggers(setups, x5)
    pooled, yearly = summarize(setups, trades)

    setups.to_csv(ROOT / f"{PFX}_SetupEvents.csv", index=False)
    trades.to_csv(ROOT / f"{PFX}_TriggeredTrades.csv", index=False)
    pooled.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)

    lines = [
        "# SOL Structure × Trigger Matrix V1 — Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Structural setups detected: **{len(setups)}**",
        f"- Triggered trade records across 12 combinations: **{len(trades)}**",
        "- Evaluation: 2020-2024; 2025+ remained CLOSED.",
        "- A structure is context only; entry occurs only after a frozen post-structure trigger.",
        "- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% RT cost.", "",
        "## Structure × trigger scorecard", "",
        "| Structure | Trigger | Setup N | Trigger N | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in pooled.iterrows():
        lines.append(
            f"| {r.structure} | {r.trigger} | {int(r.setup_n)} | {int(r.triggered_n)} | {float(r.trigger_rate)*100:.2f}% | "
            f"{float(r.wr60)*100 if np.isfinite(r.wr60) else np.nan:.2f}% | {float(r.expectancy60_pct) if np.isfinite(r.expectancy60_pct) else np.nan:.4f}% | "
            f"{pfmt(r.pf60)} | ${float(r.pnl60_usd):.2f} | ${float(r.max_dd_usd) if np.isfinite(r.max_dd_usd) else np.nan:.2f} | "
            f"{float(r.clean_up_impulse_rate)*100 if np.isfinite(r.clean_up_impulse_rate) else np.nan:.2f}% | "
            f"{float(r.median_mfe_mae_ratio) if np.isfinite(r.median_mfe_mae_ratio) else np.nan:.3f} | "
            f"{float(r.median_trigger_delay_min) if np.isfinite(r.median_trigger_delay_min) else np.nan:.1f}m | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |"
        )

    lines += ["", "## Passing combinations", ""]
    passing = pooled.loc[pooled.verdict == "PASS_TO_CHARACTERIZATION", "combo"].tolist()
    if passing:
        lines.extend([f"- **{x}**" for x in passing])
    else:
        lines.append("- NONE")

    lines += ["", "## Frozen gate audit", ""]
    for _, r in pooled.iterrows():
        lines.append(f"### {r.combo} — {r.verdict}")
        for c in ["n_ge_100", "expectancy_positive", "pf_ge_1_15", "positive_pnl_years_ge_4_of_5", "median_mfe_mae_ge_1_20"]:
            lines.append(f"- {'PASS' if bool(r['gate_'+c]) else 'FAIL'} — `{c}`")
        lines.append("")

    lines += [
        "## Interpretation rule", "",
        "PASS_TO_CHARACTERIZATION means this exact structure×trigger pair may advance to structure-specific execution / TP / SL characterization.",
        "REJECTED_AS_DEFINED means do not rescue this pair on 2020-2024 by changing structure rules, trigger thresholds/window, hours, indicators, regime filters, TP or SL.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    status = "PASSING_COMBOS=" + (",".join(passing) if passing else "NONE")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print(text)
    print(status)


if __name__ == "__main__":
    main()
