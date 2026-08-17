#!/usr/bin/env python3
"""S6.0 — Saturday Dynamic Direction Oracle Opportunity.

Research only; live BBC untouched.

Purpose
-------
Measure whether the frozen Saturday BUY strategy's weakest cohort (trades that
never reach +0.50% favorable excursion) contains enough opposite-direction
opportunity to justify a new dynamic BUY-vs-SELL research branch.

IMPORTANT: `NO +0.50` is a hindsight label. This script is an ORACLE CAPACITY
study only, NOT a causal trading rule.

Frozen mirrored SELL geometry:
- same Saturday 18:00 WIB / 11:00 UTC entry open;
- TP 2.60%, SL 1.20%, max hold 18h;
- adverse-first on same-5m ambiguity;
- same $500 fixed notional and $0.75 round-trip fee;
- funding cashflow sign reversed correctly for a short.

No threshold sweep, no classifier, no alternate entry, no management tuning.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50

OUT = Path(os.getenv("S60_OUT", "s60_out"))
OUT.mkdir(parents=True, exist_ok=True)
HINGE = 0.005
SPLIT = 83


@dataclass
class ShortTrade:
    date: str
    entry_t: str
    exit_t: str
    entry: float
    exit_px: float
    reason: str
    gross_ret: float
    price_pnl: float
    fee: float
    funding: float
    pnl: float
    mfe: float
    mae: float
    funding_events: int


def simulate_short(k: pd.DataFrame, f: pd.DataFrame, entry_t: pd.Timestamp) -> ShortTrade:
    """Mirror the frozen Saturday BUY parent into a causal static SHORT."""
    entry = float(k.loc[entry_t, "open"])
    tp_px = entry * (1.0 - s50.TP)
    sl_px = entry * (1.0 + s50.SL)
    end_t = entry_t + pd.Timedelta(minutes=s50.HOLD_MIN)
    bars = k[(k.index >= entry_t) & (k.index < end_t)]
    if len(bars) != s50.HOLD_MIN // 5:
        raise RuntimeError(f"incomplete bars {entry_t}: {len(bars)}")

    mfe = 0.0  # favorable for SHORT = price moves down
    mae = 0.0  # adverse for SHORT = price moves up
    reason = "TIMEOUT"
    exit_t = end_t
    exit_px = float(bars.iloc[-1].close)

    for b in bars.itertuples(index=False):
        mfe = max(mfe, 1.0 - float(b.low) / entry)
        mae = max(mae, float(b.high) / entry - 1.0)
        hit_sl = float(b.high) >= sl_px
        hit_tp = float(b.low) <= tp_px
        # Frozen adverse-first ambiguity, mirrored for SHORT.
        if hit_sl:
            reason = "SL"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = sl_px
            break
        if hit_tp:
            reason = "TP"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = tp_px
            break

    # USDT linear perpetual, fixed entry notional: qty = N / entry.
    # Short price PnL = qty * (entry - exit) = N * (1 - exit/entry).
    gross_ret = 1.0 - exit_px / entry
    price_pnl = s50.NOTIONAL * gross_ret
    fund_charge_long, fn = s50.funding_cost(k, f, entry_t, exit_t, entry)
    # Positive funding is received by shorts; negative funding is paid by shorts.
    pnl = price_pnl - s50.FEE + fund_charge_long

    return ShortTrade(
        date=str(entry_t.date()), entry_t=str(entry_t), exit_t=str(exit_t),
        entry=entry, exit_px=exit_px, reason=reason,
        gross_ret=float(gross_ret), price_pnl=float(price_pnl), fee=float(s50.FEE),
        funding=float(-fund_charge_long), pnl=float(pnl),
        mfe=float(mfe), mae=float(mae), funding_events=int(fn),
    )


def metrics(pnls: np.ndarray) -> dict:
    p = np.asarray(pnls, dtype=float)
    wins = int((p > 0).sum())
    pos = float(p[p > 0].sum())
    neg = float(-p[p <= 0].sum())
    eq = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = float((peak[1:] - eq).max()) if len(eq) else 0.0
    ls = cur = 0
    for x in p:
        if x <= 0:
            cur += 1
            ls = max(ls, cur)
        else:
            cur = 0
    return {
        "n": int(len(p)), "wins": wins, "losses": int(len(p)-wins),
        "wr": float(wins / len(p)) if len(p) else np.nan,
        "pnl": float(p.sum()), "expectancy": float(p.mean()) if len(p) else np.nan,
        "pf": float(pos / neg) if neg > 0 else float("inf"),
        "max_dd": dd, "loss_streak": int(ls),
    }


def main():
    k = s50.load_klines()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    longs = [s50.simulate(k, f, t) for t in entries]
    shorts = [simulate_short(k, f, t) for t in entries]

    long_p = np.array([x.pnl for x in longs], dtype=float)
    short_p = np.array([x.pnl for x in shorts], dtype=float)
    long_mfe = np.array([x.mfe for x in longs], dtype=float)
    no05 = long_mfe < HINGE - 1e-12

    # Frozen parity from S5.0/S5.2A.
    if len(entries) != 139 or abs(long_p.sum() - 87.199692) > 0.02:
        raise RuntimeError("frozen parent parity fail")
    if int(no05.sum()) != 50:
        raise RuntimeError(f"NO+0.5 parity fail: {int(no05.sum())}, expected 50")
    if int((~no05).sum()) != 89:
        raise RuntimeError("+0.5 cohort parity fail")

    # Oracle hybrid: keep frozen BUY on the 89 that eventually prove +0.5;
    # flip the 50 hindsight NO+0.5 cohort to static mirrored SHORT from entry.
    hybrid = np.where(no05, short_p, long_p)

    # Stronger theoretical per-trade best-direction upper bound for context only.
    best_direction = np.maximum(long_p, short_p)

    rows = []
    for i, (t, lg, sh) in enumerate(zip(entries, longs, shorts)):
        rows.append({
            "idx": i, "period": "discovery" if i < SPLIT else "validation",
            "date": lg.date, "entry_t": str(t),
            "long_no05": bool(no05[i]),
            "long_mfe": float(lg.mfe), "long_mae": float(lg.mae),
            "long_reason": lg.reason, "long_pnl": float(lg.pnl),
            "short_mfe": float(sh.mfe), "short_mae": float(sh.mae),
            "short_reason": sh.reason, "short_pnl": float(sh.pnl),
            "short_wins_where_long_loses": bool(lg.pnl <= 0 and sh.pnl > 0),
            "short_better_than_long": bool(sh.pnl > lg.pnl),
            "oracle_hybrid_pnl": float(hybrid[i]),
            "best_direction_pnl": float(best_direction[i]),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "s60_trade_rows.csv", index=False)

    cohort = df[df.long_no05].copy()
    proven = df[~df.long_no05].copy()

    def period_metrics(g: pd.DataFrame, col: str):
        return metrics(g[col].to_numpy(float))

    cohort_stats = {
        "long_original": period_metrics(cohort, "long_pnl"),
        "mirrored_short": period_metrics(cohort, "short_pnl"),
        "short_positive_n": int((cohort.short_pnl > 0).sum()),
        "short_better_n": int((cohort.short_pnl > cohort.long_pnl).sum()),
        "buy_loss_to_short_win_n": int(((cohort.long_pnl <= 0) & (cohort.short_pnl > 0)).sum()),
        "both_loss_n": int(((cohort.long_pnl <= 0) & (cohort.short_pnl <= 0)).sum()),
        "both_win_n": int(((cohort.long_pnl > 0) & (cohort.short_pnl > 0)).sum()),
    }

    halves = {}
    for period in ["discovery", "validation"]:
        g = cohort[cohort.period == period]
        halves[period] = {
            "n": int(len(g)),
            "long": period_metrics(g, "long_pnl"),
            "short": period_metrics(g, "short_pnl"),
            "buy_loss_to_short_win_n": int(((g.long_pnl <= 0) & (g.short_pnl > 0)).sum()),
            "short_better_n": int((g.short_pnl > g.long_pnl).sum()),
        }

    # Required directional opportunity checks. These are not a promotion gate;
    # they answer whether S6 direction discovery has enough capacity to pursue.
    hybrid_m = metrics(hybrid)
    parent_m = metrics(long_p)
    short_all_m = metrics(short_p)
    best_m = metrics(best_direction)
    proven_long_m = period_metrics(proven, "long_pnl")

    target70_wins = int(np.ceil(0.70 * len(entries)))
    additional_wins_needed_parent = max(0, target70_wins - parent_m["wins"])
    additional_wins_delivered_hybrid = hybrid_m["wins"] - parent_m["wins"]

    opportunity = {
        "parent": parent_m,
        "short_all_139": short_all_m,
        "proven_buy_89": proven_long_m,
        "no05_cohort": cohort_stats,
        "no05_halves": halves,
        "oracle_hybrid_89buy_50short": hybrid_m,
        "per_trade_best_direction_upper_bound": best_m,
        "target70": {
            "wins_required": target70_wins,
            "parent_wins": parent_m["wins"],
            "additional_wins_needed": additional_wins_needed_parent,
            "oracle_hybrid_wins": hybrid_m["wins"],
            "oracle_hybrid_additional_wins": additional_wins_delivered_hybrid,
            "oracle_hybrid_reaches_70": bool(hybrid_m["wr"] >= 0.70),
        },
    }
    (OUT / "s60_summary.json").write_text(json.dumps(opportunity, indent=2, default=float))

    def money(x): return f"${x:+.3f}"
    def pct(x): return f"{100*x:.2f}%"

    md = [
        "# S6.0 — Saturday Dynamic Direction Oracle Opportunity",
        "",
        "**Status:** COMPLETE — ORACLE CAPACITY ONLY; NOT A CAUSAL RULE",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen question",
        "For the exact 50 frozen Saturday BUY trades that never reach +0.50% favorable excursion, what happens if direction is mirrored to SHORT from the exact same 18:00 WIB entry using TP2.6/SL1.2/max18h?",
        "",
        "`NO +0.50` is hindsight and cannot be used live. This measures whether dynamic direction is worth learning.",
        "",
        "## Parity",
        f"- Saturday entries: **{len(entries)}**",
        f"- Frozen BUY parent: **{money(parent_m['pnl'])}**, WR **{pct(parent_m['wr'])}**",
        f"- Reached +0.50: **{int((~no05).sum())}**",
        f"- Never +0.50: **{int(no05.sum())}**",
        "",
        "## Exact 50 NO+0.50 cohort",
        f"- original BUY: **{cohort_stats['long_original']['wins']}/{cohort_stats['long_original']['n']} wins = {pct(cohort_stats['long_original']['wr'])}**, PnL **{money(cohort_stats['long_original']['pnl'])}**",
        f"- mirrored SHORT: **{cohort_stats['mirrored_short']['wins']}/{cohort_stats['mirrored_short']['n']} wins = {pct(cohort_stats['mirrored_short']['wr'])}**, PnL **{money(cohort_stats['mirrored_short']['pnl'])}**",
        f"- BUY loss -> SHORT win: **{cohort_stats['buy_loss_to_short_win_n']}**",
        f"- SHORT better than BUY: **{cohort_stats['short_better_n']}/{len(cohort)}**",
        f"- both directions lose: **{cohort_stats['both_loss_n']}**",
        "",
        "## Chronology split of the NO+0.50 cohort",
    ]
    for period in ["discovery", "validation"]:
        h = halves[period]
        md += [
            f"### {period.title()}",
            f"- N **{h['n']}**",
            f"- BUY WR **{pct(h['long']['wr'])}**, PnL **{money(h['long']['pnl'])}**",
            f"- mirrored SHORT WR **{pct(h['short']['wr'])}**, PnL **{money(h['short']['pnl'])}**",
            f"- BUY loss -> SHORT win **{h['buy_loss_to_short_win_n']}**",
            f"- SHORT better **{h['short_better_n']}/{h['n']}**",
            "",
        ]

    md += [
        "## Hindsight hybrid capacity",
        "Keep original BUY for the 89 trades that eventually reach +0.50; replace the exact 50 NO+0.50 trades with mirrored SHORT from entry.",
        f"- hybrid WR **{pct(hybrid_m['wr'])}** = {hybrid_m['wins']}/{hybrid_m['n']}",
        f"- hybrid PnL **{money(hybrid_m['pnl'])}**",
        f"- PF **{hybrid_m['pf']:.3f}**, DD **{hybrid_m['max_dd']:.3f}**, LS **{hybrid_m['loss_streak']}**",
        "",
        "## 70% feasibility arithmetic",
        f"- 70% of 139 requires **{target70_wins} wins**.",
        f"- frozen parent has **{parent_m['wins']} wins**, so needs **+{additional_wins_needed_parent}**.",
        f"- hindsight direction hybrid adds **{additional_wins_delivered_hybrid} wins** and ends at **{pct(hybrid_m['wr'])}**.",
        f"- oracle hybrid reaches 70%? **{'YES' if hybrid_m['wr'] >= 0.70 else 'NO'}**",
        "",
        "## Context-only ceiling",
        "Per-trade best of static BUY vs static SHORT is a stronger hindsight upper bound, not a strategy.",
        f"- best-direction upper-bound WR **{pct(best_m['wr'])}**, PnL **{money(best_m['pnl'])}**",
        "",
        "## Research decision",
        "This milestone does not create a classifier. If mirrored SHORT materially recovers the NO+0.50 cohort in both discovery and validation, the next clean milestone is to search PRE-ENTRY causal features that distinguish future BUY-proven vs opposite-direction opportunities. If not, do not force a dynamic-direction model just to chase 70%.",
    ]
    (OUT / "S6.0_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(opportunity, indent=2, default=float))


if __name__ == "__main__":
    main()
