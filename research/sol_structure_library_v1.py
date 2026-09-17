#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURE_LIBRARY_V1"
MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
PIVOT_ORDER = 2
FUTURE_BARS = 12
TRAIL_BARS = 288
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
UP_FLOOR_PCT = 0.75
UP_SIGMA_MULT = 1.5
DOWN_FRAC = 0.50
YEARS = (2020, 2021, 2022, 2023, 2024)
STRUCTURES = (
    "SWEEP_RECLAIM",
    "HL_CONTINUATION",
    "BREAKOUT_FIRST_PULLBACK",
    "LL_REVERSAL_BREAK",
)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {
            "n": 0, "wr": np.nan, "expectancy_pct": np.nan,
            "pnl_usd": 0.0, "pf": np.nan, "max_dd_usd": np.nan,
            "max_loss_streak": 0,
        }
    r = g.net60_pct.astype(float)
    p = g.pnl60_usd.astype(float)
    return {
        "n": int(len(g)),
        "wr": float((r > 0).mean()),
        "expectancy_pct": float(r.mean()),
        "pnl_usd": float(p.sum()),
        "pf": float(profit_factor(p)),
        "max_dd_usd": float(max_drawdown(p)),
        "max_loss_streak": int(max_loss_streak(p)),
    }


def pfmt(v) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def compute_pivots(hi: np.ndarray, lo: np.ndarray):
    lows_by_confirm: dict[int, list[dict]] = {}
    highs_by_confirm: dict[int, list[dict]] = {}
    n = len(hi)
    o = PIVOT_ORDER
    for j in range(o, n - o):
        left_lo = lo[j-o:j]
        right_lo = lo[j+1:j+o+1]
        left_hi = hi[j-o:j]
        right_hi = hi[j+1:j+o+1]
        if lo[j] < float(np.min(left_lo)) and lo[j] <= float(np.min(right_lo)):
            c = j + o
            lows_by_confirm.setdefault(c, []).append({"pivot_i": j, "confirm_i": c, "price": float(lo[j])})
        if hi[j] > float(np.max(left_hi)) and hi[j] >= float(np.max(right_hi)):
            c = j + o
            highs_by_confirm.setdefault(c, []).append({"pivot_i": j, "confirm_i": c, "price": float(hi[j])})
    return lows_by_confirm, highs_by_confirm


def add_signal(rows: list[dict], structure: str, signal_i: int, idx, op, hi, lo, cl, meta: dict):
    if signal_i < TRAIL_BARS - 1:
        return
    signal_time = idx[signal_i]
    if signal_time < MODEL_START or signal_time >= MODEL_END:
        return
    entry_i = signal_i + 1
    last_i = entry_i + FUTURE_BARS - 1
    if last_i >= len(idx):
        return
    entry_time = idx[entry_i]
    last_time = idx[last_i]
    if entry_time >= MODEL_END or last_time >= MODEL_END:
        return
    if entry_time != signal_time + pd.Timedelta(minutes=5):
        return
    if last_time != entry_time + pd.Timedelta(minutes=55):
        return

    trailing_close = cl[signal_i - TRAIL_BARS + 1:signal_i + 1]
    lr = np.diff(np.log(trailing_close))
    if len(lr) < 250:
        return
    sigma60 = float(np.std(lr, ddof=1) * np.sqrt(12.0) * 100.0)
    if not np.isfinite(sigma60) or sigma60 <= 0:
        return

    entry = float(op[entry_i])
    fhi = hi[entry_i:last_i + 1]
    flo = lo[entry_i:last_i + 1]
    exitp = float(cl[last_i])
    if not (np.isfinite(entry) and entry > 0 and np.isfinite(fhi).all() and np.isfinite(flo).all() and np.isfinite(exitp)):
        return

    gross = float((exitp / entry - 1.0) * 100.0)
    net = gross - ROUNDTRIP_COST_PCT
    mfe = float((np.max(fhi) / entry - 1.0) * 100.0)
    mae = float((np.min(flo) / entry - 1.0) * 100.0)
    ratio = float(mfe / abs(mae)) if abs(mae) > 1e-9 else np.nan
    t_mfe = int((np.argmax(fhi) + 1) * 5)
    t_mae = int((np.argmin(flo) + 1) * 5)

    thr = max(UP_FLOOR_PCT, UP_SIGMA_MULT * sigma60)
    up = entry * (1.0 + thr / 100.0)
    dn = entry * (1.0 - DOWN_FRAC * thr / 100.0)
    up_touch = fhi >= up
    dn_touch = flo <= dn
    up_any = bool(up_touch.any())
    dn_any = bool(dn_touch.any())
    up_i = int(np.argmax(up_touch)) if up_any else 999
    dn_i = int(np.argmax(dn_touch)) if dn_any else 999
    clean = int(up_any and (not dn_any or up_i < dn_i))
    if up_any and dn_any and up_i == dn_i:
        clean = 0

    rows.append({
        "structure": structure,
        "signal_time": signal_time,
        "entry_time": entry_time,
        "year": int(signal_time.year),
        "entry_price": entry,
        "exit60_price": exitp,
        "gross60_pct": gross,
        "net60_pct": net,
        "pnl60_usd": net / 100.0 * NOTIONAL,
        "win60": int(net > 0),
        "mfe60_pct": mfe,
        "mae60_pct": mae,
        "mfe_mae_ratio": ratio,
        "time_to_mfe_min": t_mfe,
        "time_to_mae_min": t_mae,
        "sigma60_pct": sigma60,
        "impulse_threshold_pct": thr,
        "clean_up_impulse": clean,
        **meta,
    })


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


def detect_all(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = compute_pivots(hi, lo)

    low_hist: list[dict] = []
    high_hist: list[dict] = []
    rows: list[dict] = []

    sweep_anchor = None
    hl_candidate = None
    ll_candidate = None

    consumed_highs: set[int] = set()
    bo_anchor = None
    bo_event = None

    for i in range(PIVOT_ORDER, len(x5) - FUTURE_BARS - 1):
        new_highs = highs_by_confirm.get(i, [])
        for h in new_highs:
            high_hist.append(h)
            if bo_event is None:
                bo_anchor = latest_unconsumed_high(high_hist, consumed_highs)

        new_lows = lows_by_confirm.get(i, [])
        for l2 in new_lows:
            # BREAKOUT_FIRST_PULLBACK consumes the first confirmed pivot low after breakout.
            if bo_event is not None and l2["pivot_i"] > bo_event["breakout_i"]:
                level = bo_event["level"]
                no_close_loss = bool(np.all(cl[bo_event["breakout_i"] + 1:i + 1] >= level)) if i > bo_event["breakout_i"] else True
                qualifies = bool(lo[l2["pivot_i"]] <= level and cl[l2["pivot_i"]] > level and no_close_loss)
                if qualifies:
                    add_signal(rows, "BREAKOUT_FIRST_PULLBACK", i, idx, op, hi, lo, cl, {
                        "anchor_level": level,
                        "anchor_pivot_i": bo_event["high_pivot_i"],
                        "secondary_level": float(l2["price"]),
                        "secondary_pivot_i": int(l2["pivot_i"]),
                    })
                bo_event = None
                bo_anchor = latest_unconsumed_high(high_hist, consumed_highs)

            prev_low = low_hist[-1] if low_hist else None
            h1 = latest_high_between(high_hist, prev_low["pivot_i"], l2["pivot_i"]) if prev_low is not None else None

            # A newer confirmed pivot low replaces pending continuation/reversal candidates.
            hl_candidate = None
            ll_candidate = None
            if prev_low is not None and h1 is not None:
                if l2["price"] > prev_low["price"]:
                    hl_candidate = {"l1": prev_low, "l2": l2, "h1": h1}
                elif l2["price"] < prev_low["price"]:
                    ll_candidate = {"l1": prev_low, "l2": l2, "h1": h1}

            low_hist.append(l2)
            sweep_anchor = l2

        # SWEEP_RECLAIM: a signal must occur on a bar later than pivot confirmation.
        if sweep_anchor is not None and i > sweep_anchor["confirm_i"]:
            lvl = sweep_anchor["price"]
            if cl[i] < lvl:
                sweep_anchor = None
            elif lo[i] < lvl and cl[i] > lvl:
                add_signal(rows, "SWEEP_RECLAIM", i, idx, op, hi, lo, cl, {
                    "anchor_level": float(lvl),
                    "anchor_pivot_i": int(sweep_anchor["pivot_i"]),
                    "secondary_level": np.nan,
                    "secondary_pivot_i": -1,
                })
                sweep_anchor = None

        # HL_CONTINUATION.
        if hl_candidate is not None:
            support = hl_candidate["l2"]["price"]
            trigger = hl_candidate["h1"]["price"]
            if cl[i] < support:
                hl_candidate = None
            elif cl[i] > trigger:
                add_signal(rows, "HL_CONTINUATION", i, idx, op, hi, lo, cl, {
                    "anchor_level": float(trigger),
                    "anchor_pivot_i": int(hl_candidate["h1"]["pivot_i"]),
                    "secondary_level": float(support),
                    "secondary_pivot_i": int(hl_candidate["l2"]["pivot_i"]),
                })
                hl_candidate = None

        # LL_REVERSAL_BREAK.
        if ll_candidate is not None:
            support = ll_candidate["l2"]["price"]
            trigger = ll_candidate["h1"]["price"]
            if cl[i] < support:
                ll_candidate = None
            elif cl[i] > trigger:
                add_signal(rows, "LL_REVERSAL_BREAK", i, idx, op, hi, lo, cl, {
                    "anchor_level": float(trigger),
                    "anchor_pivot_i": int(ll_candidate["h1"]["pivot_i"]),
                    "secondary_level": float(support),
                    "secondary_pivot_i": int(ll_candidate["l2"]["pivot_i"]),
                })
                ll_candidate = None

        # BREAKOUT_FIRST_PULLBACK lifecycle.
        if bo_event is not None:
            if i > bo_event["breakout_i"] and cl[i] < bo_event["level"]:
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
                    "breakout_i": i,
                }
                bo_anchor = None

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no structural events detected")
    out = out.sort_values(["structure", "entry_time", "signal_time"]).drop_duplicates(["structure", "entry_time"], keep="first")
    return out.reset_index(drop=True)


def summaries(events: pd.DataFrame):
    pooled_rows = []
    year_rows = []
    for s in STRUCTURES:
        g = events[events.structure == s].copy()
        e = econ(g)
        ratio = float(g.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(g) else np.nan
        clean = float(g.clean_up_impulse.mean()) if len(g) else np.nan
        positive_years = 0
        for y in YEARS:
            gy = g[g.year == y].copy()
            ey = econ(gy)
            if ey["pnl_usd"] > 0:
                positive_years += 1
            year_rows.append({
                "structure": s,
                "year": y,
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
            })

        gates = {
            "n_ge_100": e["n"] >= 100,
            "expectancy_positive": bool(np.isfinite(e["expectancy_pct"]) and e["expectancy_pct"] > 0),
            "pf_ge_1_15": bool(np.isfinite(e["pf"]) and e["pf"] >= 1.15),
            "positive_pnl_years_ge_4_of_5": positive_years >= 4,
            "median_mfe_mae_ge_1_20": bool(np.isfinite(ratio) and ratio >= 1.20),
        }
        verdict = "PASS_TO_CHARACTERIZATION" if all(gates.values()) else "REJECTED_AS_DEFINED"
        pooled_rows.append({
            "structure": s,
            "n": e["n"],
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
            "median_time_to_mfe_min": float(g.time_to_mfe_min.median()) if len(g) else np.nan,
            "median_time_to_mae_min": float(g.time_to_mae_min.median()) if len(g) else np.nan,
            "positive_pnl_years": positive_years,
            **{f"gate_{k}": v for k, v in gates.items()},
            "verdict": verdict,
        })
    return pd.DataFrame(pooled_rows), pd.DataFrame(year_rows)


def overlap_table(events: pd.DataFrame) -> pd.DataFrame:
    times = {s: set(events.loc[events.structure == s, "entry_time"].tolist()) for s in STRUCTURES}
    rows = []
    for a in STRUCTURES:
        for b in STRUCTURES:
            ov = len(times[a] & times[b])
            rows.append({
                "structure_a": a,
                "structure_b": b,
                "overlap_n": ov,
                "pct_of_a": ov / len(times[a]) if times[a] else np.nan,
                "pct_of_b": ov / len(times[b]) if times[b] else np.nan,
            })
    return pd.DataFrame(rows)


def main():
    # Reuse only repository data access. No V4/V5 detector semantics are imported.
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
        "# SOL Structural Detector Library V1 — Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Total detected structure-events: **{len(events)}**",
        "- Evaluation: 2020-2024; 2025+ remained CLOSED.",
        "- Entry: next 5m open after causal structure signal; fixed +60m diagnostic; 0.15% RT cost.", "",
        "## Pooled detector scorecard", "",
        "| Structure | N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE | MAE | MFE/MAE | Positive years | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in pooled.iterrows():
        lines.append(
            f"| {r.structure} | {int(r.n)} | {float(r.wr60)*100:.2f}% | {float(r.expectancy60_pct):.4f}% | {pfmt(r.pf60)} | ${float(r.pnl60_usd):.2f} | ${float(r.max_dd_usd):.2f} | {int(r.max_loss_streak)} | {float(r.clean_up_impulse_rate)*100:.2f}% | {float(r.median_mfe60_pct):.3f}% | {float(r.median_mae60_pct):.3f}% | {float(r.median_mfe_mae_ratio):.3f} | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |"
        )

    lines += ["", "## Per-year economics", ""]
    for s in STRUCTURES:
        lines += [f"### {s}", "", "| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in yearly[yearly.structure == s].iterrows():
            lines.append(
                f"| {int(r.year)} | {int(r.n)} | {float(r.wr60)*100 if np.isfinite(r.wr60) else np.nan:.2f}% | {float(r.expectancy60_pct) if np.isfinite(r.expectancy60_pct) else np.nan:.4f}% | {pfmt(r.pf60)} | ${float(r.pnl60_usd):.2f} | {float(r.clean_up_impulse_rate)*100 if np.isfinite(r.clean_up_impulse_rate) else np.nan:.2f}% | {float(r.median_mfe_mae_ratio) if np.isfinite(r.median_mfe_mae_ratio) else np.nan:.3f} |"
            )
        lines.append("")

    lines += ["## Frozen gate audit", ""]
    for _, r in pooled.iterrows():
        lines.append(f"### {r.structure} — {r.verdict}")
        for c in ["n_ge_100", "expectancy_positive", "pf_ge_1_15", "positive_pnl_years_ge_4_of_5", "median_mfe_mae_ge_1_20"]:
            lines.append(f"- {'PASS' if bool(r['gate_'+c]) else 'FAIL'} — `{c}`")
        lines.append("")

    lines += [
        "## Interpretation rule", "",
        "PASS_TO_CHARACTERIZATION means this exact market structure has enough pre-exit-optimization evidence to justify a separate structure-specific execution/TP/SL characterization stage.",
        "REJECTED_AS_DEFINED means do not rescue this detector on 2020-2024 by changing pivot order, thresholds, timing windows, hours, indicators, regime filters, TP or SL. Move to another explicitly defined structure instead.",
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
