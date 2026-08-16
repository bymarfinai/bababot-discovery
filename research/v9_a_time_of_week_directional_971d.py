#!/usr/bin/env python3
"""V9-A — causal time-of-week directional seasonality audit.

Research only. No live changes. No TP/SL or indicator tuning.

Question:
  Does a fixed pair x weekday x WIB hour have a persistent 1H directional bias?

Method:
- Official Binance USD-M 1H archive only.
- Frozen 971d window used by V7-F/G/H.
- 8 non-overlapping 120d blocks + 11d remainder.
- First 4 blocks (480d) are discovery.
- For each pair x weekday x hour, direction is selected ONLY from discovery
  majority (BUY if close>open more often, SELL otherwise).
- That direction is frozen and evaluated on blocks 5-8 (480d validation).
- A directionally correct trade means the 1H candle close is on the chosen
  side of its open. Entry time is therefore known ex ante at the candle open.
- Hours are Asia/Jakarta / WIB (UTC+7).
- No fees/slippage/TP/SL yet: this is a pure directional-bias screen.
- Validation binomial p-values are reported, plus Bonferroni across the
  discovery-selected >=60% candidates to control multiple-testing risk.
"""

import json
import math
from datetime import datetime, timedelta, timezone

from research.v7_f_fib_120d_archive_audit import load_series

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 971
BLOCK_DAYS = 120
WINDOW_START = datetime.fromisoformat("2023-12-18T15:11:15.831175+00:00")
WINDOW_END = datetime.fromisoformat("2026-08-15T15:11:15.831175+00:00")
WIB = timezone(timedelta(hours=7))
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def pct(x):
    return round(100.0 * x, 4)


def one_sided_binom_p(k, n, p=0.5):
    if n <= 0:
        return None
    s = 0.0
    for i in range(k, n + 1):
        s += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    return min(1.0, s)


def stats(rows, direction):
    if not rows:
        return {"n": 0, "wins": 0, "losses": 0, "wr_pct": None,
                "mean_signed_ret_pct": None, "median_signed_ret_pct": None,
                "binom_p_one_sided": None}
    mult = 1.0 if direction == "BUY" else -1.0
    signed = [mult * r["ret"] for r in rows]
    wins = sum(x > 0 for x in signed)
    losses = sum(x < 0 for x in signed)
    # exact flat candles are ignored from denominator; practically rare.
    n = wins + losses
    if not n:
        return {"n": 0, "wins": 0, "losses": 0, "wr_pct": None,
                "mean_signed_ret_pct": None, "median_signed_ret_pct": None,
                "binom_p_one_sided": None}
    vals = sorted(x for x in signed if x != 0)
    med = vals[len(vals)//2] if vals else 0.0
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr_pct": round(100.0 * wins / n, 2),
        "mean_signed_ret_pct": round(100.0 * sum(vals) / len(vals), 5),
        "median_signed_ret_pct": round(100.0 * med, 5),
        "binom_p_one_sided": round(one_sided_binom_p(wins, n), 8),
    }


def main():
    rows_all = []
    coverage = {}
    for pair in PAIRS:
        raw = load_series(pair, "1h", WINDOW_START, WINDOW_END)
        coverage[pair] = {
            "rows": len(raw),
            "first": datetime.fromtimestamp(raw[0][2]/1000, tz=timezone.utc).isoformat() if raw else None,
            "last": datetime.fromtimestamp(raw[-1][2]/1000, tz=timezone.utc).isoformat() if raw else None,
        }
        for r in raw:
            t = datetime.fromtimestamp(int(r[2])/1000, tz=timezone.utc)
            if not (WINDOW_START <= t < WINDOW_END):
                continue
            delta = (t - WINDOW_START).total_seconds()
            block = int(delta // (BLOCK_DAYS * 86400)) + 1
            if block < 1 or block > 9:
                continue
            o = float(r[3]); c = float(r[6])
            if o <= 0:
                continue
            local = t.astimezone(WIB)
            rows_all.append({
                "pair": pair,
                "t": t,
                "block": block,
                "weekday": local.weekday(),
                "hour_wib": local.hour,
                "ret": c / o - 1.0,
            })

    candidates = []
    all_cells = []
    for pair in PAIRS:
        for wd in range(7):
            for hour in range(24):
                cell = [r for r in rows_all if r["pair"] == pair and r["weekday"] == wd and r["hour_wib"] == hour and r["block"] <= 8]
                disc = [r for r in cell if 1 <= r["block"] <= 4]
                val = [r for r in cell if 5 <= r["block"] <= 8]
                up = sum(r["ret"] > 0 for r in disc)
                dn = sum(r["ret"] < 0 for r in disc)
                if up == dn:
                    direction = None
                else:
                    direction = "BUY" if up > dn else "SELL"
                if direction is None:
                    continue
                ds = stats(disc, direction)
                vs = stats(val, direction)
                blocks = []
                for b in range(1, 9):
                    bs = stats([r for r in cell if r["block"] == b], direction)
                    blocks.append({"block": b, **bs})
                item = {
                    "pair": pair,
                    "weekday": WEEKDAYS[wd],
                    "hour_wib": hour,
                    "direction": direction,
                    "discovery": ds,
                    "validation": vs,
                    "blocks_120d": blocks,
                    "blocks_wr_ge55": sum(1 for x in blocks if x["n"] >= 12 and (x["wr_pct"] or 0) >= 55.0),
                    "blocks_wr_ge60": sum(1 for x in blocks if x["n"] >= 12 and (x["wr_pct"] or 0) >= 60.0),
                    "blocks_wr_ge70": sum(1 for x in blocks if x["n"] >= 12 and (x["wr_pct"] or 0) >= 70.0),
                }
                all_cells.append(item)
                if ds["n"] >= 60 and (ds["wr_pct"] or 0) >= 60.0:
                    candidates.append(item)

    m = max(1, len(candidates))
    for x in candidates:
        p = x["validation"]["binom_p_one_sided"]
        x["validation_bonferroni_p"] = round(min(1.0, (p or 1.0) * m), 8)
        x["passes_60_60"] = (
            x["validation"]["n"] >= 60
            and (x["validation"]["wr_pct"] or 0) >= 60.0
            and (x["validation"]["mean_signed_ret_pct"] or 0) > 0
        )
        x["validation_wr_ge70"] = (x["validation"]["wr_pct"] or 0) >= 70.0

    candidates.sort(key=lambda x: (
        x["passes_60_60"],
        x["validation"]["wr_pct"] or 0,
        x["discovery"]["wr_pct"] or 0,
        x["validation"]["mean_signed_ret_pct"] or -999,
    ), reverse=True)

    stable = [x for x in candidates if x["passes_60_60"]]
    val70 = [x for x in stable if x["validation_wr_ge70"]]

    # Same clock slot across multiple pairs in validation, descriptive only.
    cross_pair = []
    for wd in range(7):
        for hour in range(24):
            xs = [x for x in stable if x["weekday"] == WEEKDAYS[wd] and x["hour_wib"] == hour]
            if len(xs) >= 2:
                cross_pair.append({
                    "weekday": WEEKDAYS[wd], "hour_wib": hour,
                    "pairs": [{"pair": x["pair"], "direction": x["direction"], "validation_wr_pct": x["validation"]["wr_pct"]} for x in xs]
                })

    result = {
        "phase": "V9-A",
        "status": "TIME_OF_WEEK_DIRECTIONAL_DISCOVERY_VALIDATION",
        "definition": {
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "timezone": "Asia/Jakarta UTC+7 (WIB)",
            "structure_tf": "1h",
            "entry": "1h candle open at fixed weekday/hour",
            "outcome": "direction correct if 1h close is on selected side of open",
            "discovery": "blocks 1-4 (480d); choose BUY/SELL majority per pair x weekday x WIB hour",
            "validation": "blocks 5-8 (480d); frozen direction",
            "candidate_discovery_gate": "n>=60 and WR>=60%",
            "stable_gate": "validation n>=60, WR>=60%, mean signed 1h return >0",
            "target_70": "reported, not used to tune",
            "tp_sl": None,
            "fees_slippage": "not applied; pure direction screen",
            "threshold_sweep": False,
            "live_changes": False,
        },
        "coverage": coverage,
        "total_hourly_rows": len(rows_all),
        "tested_cells": len(all_cells),
        "discovery_candidates_n": len(candidates),
        "stable_60_60_n": len(stable),
        "validation_ge70_n": len(val70),
        "top_candidates": candidates[:30],
        "stable_candidates": stable,
        "validation_ge70_candidates": val70,
        "cross_pair_stable_slots": cross_pair,
        "multiple_testing_note": "validation one-sided binomial p plus Bonferroni across discovery-selected candidates; selection still exploratory and requires executable TP/SL follow-up",
    }
    print("V9_A_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
