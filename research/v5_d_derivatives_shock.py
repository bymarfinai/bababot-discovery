#!/usr/bin/env python3
"""V5-D — frozen derivatives shock / capitulation reversal test.

Research-only. Event originates from abnormal price + OI shock, with all
thresholds frozen before reading results.

Definition:
- Aggregate fixed UTC 15m bars from official 5m kline + OI metrics.
- For each pair, compute causal z-scores from the immediately preceding
  672 completed 15m bars (7 days), excluding the current bar.
- Shock if abs(price-return z) >= 2.0 AND OI-return z <= -2.0.
- Trigger only on transition from non-shock to shock.
- Enter after shock 15m closes, REVERSAL against the shock price direction.
- Stop at shock extreme; target 1R; track from next 5m bar, horizon 72h.
- Same-child TP+SL ambiguity excluded.

No S/R, EMA, Fibonacci, funding, positioning, taker, magnitude sweep, pair
filter, direction filter, or live integration.
"""
import json
import math
import statistics
from datetime import datetime, timedelta, timezone

import v5_c_derivatives_native as src

PAIRS = src.PAIRS
BASELINE_15M = 7 * 24 * 4  # 672 bars
Z_PRICE = 2.0
Z_OI = -2.0
RR = 1.0
HORIZON_5M = 72 * 12
DAYS = 120


def stat(rows):
    resolved = [r for r in rows if r.get("outcome") in ("WIN", "LOSS")]
    n = len(resolved)
    w = sum(r["outcome"] == "WIN" for r in resolved)
    return {
        "events": len(rows), "resolved": n, "wins": w, "losses": n-w,
        "wr_pct": round(100.0*w/n, 2) if n else None,
        "ambiguous": sum(r.get("outcome") == "AMBIGUOUS" for r in rows),
        "censored": sum(r.get("outcome") == "CENSORED" for r in rows),
    }


def floor_15m(t):
    m = (t.minute // 15) * 15
    return t.replace(minute=m, second=0, microsecond=0)


def aggregate_15m(rows):
    buckets = {}
    for r in rows:
        k = floor_15m(r["t"])
        buckets.setdefault(k, []).append(r)
    out = []
    for t in sorted(buckets):
        xs = sorted(buckets[t], key=lambda x: x["t"])
        # Require all three 5m children and exact expected starts.
        expected = [t + timedelta(minutes=5*i) for i in range(3)]
        if len(xs) != 3 or [x["t"] for x in xs] != expected:
            continue
        oi0 = xs[0].get("oi"); oi1 = xs[-1].get("oi")
        if not oi0 or oi1 is None:
            continue
        o = xs[0]["open"]; c = xs[-1]["close"]
        if not o:
            continue
        out.append({
            "t": t,
            "open": o, "high": max(x["high"] for x in xs),
            "low": min(x["low"] for x in xs), "close": c,
            "price_ret": c/o - 1.0,
            "oi_ret": oi1/oi0 - 1.0,
        })
    return out


def mean_sd(xs):
    if len(xs) < 2:
        return None, None
    mu = statistics.mean(xs)
    sd = statistics.stdev(xs)
    return mu, sd


def z(v, mu, sd):
    return (v-mu)/sd if sd and sd > 0 else None


def shock_candidates(b15):
    out = []
    prev_shock = False
    for i in range(BASELINE_15M, len(b15)):
        hist = b15[i-BASELINE_15M:i]
        pmu, psd = mean_sd([x["price_ret"] for x in hist])
        omu, osd = mean_sd([x["oi_ret"] for x in hist])
        zp = z(b15[i]["price_ret"], pmu, psd)
        zo = z(b15[i]["oi_ret"], omu, osd)
        is_shock = zp is not None and zo is not None and abs(zp) >= Z_PRICE and zo <= Z_OI
        if is_shock and not prev_shock:
            x = dict(b15[i])
            x["z_price"] = zp; x["z_oi"] = zo
            out.append(x)
        prev_shock = is_shock
    return out


def resolve_5m(rows, event):
    t0 = event["t"] + timedelta(minutes=15)
    d = event["entry_dir"]
    stop = event["stop"]; target = event["target"]
    future = [r for r in rows if t0 <= r["t"] < t0 + timedelta(hours=72)]
    if not future:
        return "CENSORED", None
    for b in future[:HORIZON_5M]:
        hit_tp = (b["high"] >= target) if d > 0 else (b["low"] <= target)
        hit_sl = (b["low"] <= stop) if d > 0 else (b["high"] >= stop)
        if hit_tp and hit_sl:
            return "AMBIGUOUS", b["t"]
        if hit_tp:
            return "WIN", b["t"]
        if hit_sl:
            return "LOSS", b["t"]
    return "CENSORED", future[min(len(future), HORIZON_5M)-1]["t"]


def build_events(symbol, rows, sample_start, sample_end):
    b15 = aggregate_15m(rows)
    shocks = shock_candidates(b15)
    events = []
    for s in shocks:
        if not (sample_start <= s["t"] < sample_end):
            continue
        shock_dir = 1 if s["price_ret"] > 0 else -1 if s["price_ret"] < 0 else 0
        if shock_dir == 0:
            continue
        entry_dir = -shock_dir
        entry = s["close"]
        stop = s["high"] if entry_dir < 0 else s["low"]
        risk = stop-entry if entry_dir < 0 else entry-stop
        if risk <= 0:
            continue
        target = entry + entry_dir * RR * risk
        e = {
            "symbol": symbol, "signal_time": s["t"],
            "shock_direction": "UP" if shock_dir > 0 else "DOWN",
            "trade_direction": "SHORT" if entry_dir < 0 else "LONG",
            "entry_dir": entry_dir, "entry": entry, "stop": stop,
            "target": target, "risk_pct": 100.0*risk/entry,
            "price_ret_pct": 100.0*s["price_ret"],
            "oi_ret_pct": 100.0*s["oi_ret"],
            "z_price": s["z_price"], "z_oi": s["z_oi"],
        }
        outcome, ot = resolve_5m(rows, {**s, **e})
        e["outcome"] = outcome; e["outcome_time"] = ot
        events.append(e)
    return events, b15


def median(rows, key):
    xs = [float(r[key]) for r in rows if r.get(key) is not None and math.isfinite(float(r[key]))]
    return round(statistics.median(xs), 8) if xs else None


def by_time(rows):
    resolved = [r for r in rows if r.get("outcome") in ("WIN", "LOSS")]
    if not resolved:
        return {}
    end = max(r["signal_time"] for r in resolved)
    cut = end - timedelta(days=60)
    return {
        "first_60d": stat([r for r in resolved if r["signal_time"] < cut]),
        "last_60d": stat([r for r in resolved if r["signal_time"] >= cut]),
        "cut": cut.isoformat(), "end": end.isoformat(),
    }


def main():
    now = datetime.now(timezone.utc)
    # Full 72h outcome availability: end sample three full UTC days back.
    today0 = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    sample_end = today0 - timedelta(days=3)
    sample_start = sample_end - timedelta(days=DAYS)
    load_start = sample_start - timedelta(days=7, minutes=15)
    load_end = today0

    all_events = []; coverage = {}; errors = {}
    for p in PAIRS:
        try:
            kl = src.load_klines(p, load_start, load_end)
            mt = src.load_metrics(p, load_start, load_end)
            rows = src.align(kl, mt)
            ev, b15 = build_events(p, rows, sample_start, sample_end)
            all_events.extend(ev)
            coverage[p] = {
                "klines": len(kl), "metrics": len(mt), "aligned_5m": len(rows),
                "bars_15m": len(b15), "events": len(ev),
                "first": rows[0]["t"].isoformat() if rows else None,
                "last": rows[-1]["t"].isoformat() if rows else None,
            }
        except Exception as ex:
            errors[p] = str(ex)

    resolved = [r for r in all_events if r.get("outcome") in ("WIN", "LOSS")]
    overall = stat(all_events)
    by_pair = {p: stat([r for r in all_events if r["symbol"] == p]) for p in PAIRS}
    by_dir = {d: stat([r for r in all_events if r["trade_direction"] == d]) for d in ("LONG", "SHORT")}
    bt = by_time(all_events)

    pair_ok = sum(1 for z0 in by_pair.values() if z0["resolved"] >= 5 and (z0["wr_pct"] or 0) > 50)
    dir_ok = all(by_dir[d]["resolved"] >= 10 and (by_dir[d]["wr_pct"] or 0) > 50 for d in by_dir)
    time_ok = bool(bt) and all(bt[k]["resolved"] >= 10 and (bt[k]["wr_pct"] or 0) > 50 for k in ("first_60d", "last_60d"))

    wins = [r for r in resolved if r["outcome"] == "WIN"]
    losses = [r for r in resolved if r["outcome"] == "LOSS"]
    diag = {}
    for f in ("z_price", "z_oi", "price_ret_pct", "oi_ret_pct", "risk_pct"):
        diag[f] = {"winner_median": median(wins, f), "loser_median": median(losses, f)}

    earns = bool(overall["resolved"] >= 20 and (overall["wr_pct"] or 0) >= 70 and pair_ok >= 3 and dir_ok and time_ok)
    result = {
        "phase": "V5-D",
        "status": "FROZEN_2SIGMA_CAPITULATION_REVERSAL_120D_SCREEN",
        "frozen_definition": {
            "sample": "120 fully resolvable days ending 72h before latest full UTC day",
            "bar": "fixed non-overlapping UTC 15m",
            "baseline": "previous 672 completed 15m bars (7d), pair-specific, current bar excluded",
            "shock": "abs(price_return_z)>=2.0 AND oi_return_z<=-2.0",
            "trigger": "first transition from non-shock to shock",
            "entry": "after shock 15m closes, reversal against shock price direction",
            "stop": "shock 15m extreme", "target": "1R",
            "tracking": "next 5m bar onward; same-child TP+SL ambiguous excluded; 72h horizon",
            "threshold_sweep": False, "other_filters": False,
            "primary_hypothesis": "statistically abnormal OI-contraction capitulation has short-term reversal edge",
        },
        "predeclared_gate": {
            "overall_wr_pct": ">=70", "resolved_n": ">=20",
            "pair_distribution": ">=3/4 pairs each resolved>=5 and WR>50",
            "both_directions": "LONG and SHORT each resolved>=10 and WR>50",
            "both_60d_halves": "each resolved>=10 and WR>50",
        },
        "sample_start": sample_start.isoformat(), "sample_end_exclusive": sample_end.isoformat(),
        "coverage": coverage, "overall": overall, "by_pair": by_pair,
        "by_direction": by_dir, "by_time": bt, "diagnostics_only": diag,
        "gate_checks": {"pairs_passing": pair_ok, "direction_check": dir_ok, "time_check": time_ok, "earns_971d_validation": earns},
        "errors": errors,
        "notes": {"interpretation": "No alternate z threshold, baseline, direction, stop, or shock definition may be promoted post-hoc from this sample.", "next": "Only a passing frozen event earns 971d validation; otherwise reject this exact capitulation-reversal mechanism."},
    }
    print("V5_D_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
