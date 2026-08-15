#!/usr/bin/env python3
"""V7-A — frozen regime-aligned failed breakout / liquidity sweep + reclaim.

Research only. No live/order integration.

Primary hypothesis (frozen before results):
- Use the existing trade-independent 1H mode3_regime classifier.
- Trade only BULL_MARKUP and BEAR_MARKDOWN; skip accumulation/distribution/unknown.
- On 5m, define the reference liquidity pool as the previous 12 completed bars (1h).
- BULL_MARKUP: current 5m low strictly sweeps below prior-12 low, then closes back above
  that level with a bullish candle -> LONG.
- BEAR_MARKDOWN: current 5m high strictly sweeps above prior-12 high, then closes back below
  that level with a bearish candle -> SHORT.
- Dual-sweep candles are excluded.
- Entry at sweep/reclaim 5m close; stop at that 5m extreme; target 1R.
- Tracking starts next 5m bar; same-child TP+SL ambiguity excluded; horizon 72h.
- One position per pair: no new entry until the prior position resolves/ambiguously closes/censors.

No Fibonacci, OI, funding, taker, extra EMA gate, body-ratio threshold, TP/SL sweep,
lookback sweep, pair filter, direction filter, or post-hoc threshold selection.
"""

import bisect
import csv
import io
import json
import math
import statistics
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone

import numpy as np

from mode3_regime.regime import Regime, RegimeConfig, classify_regime_series

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 120
LOOKBACK_5M = 12
RR = 1.0
HORIZON_5M = 72 * 12
KLINE_MONTHLY = "https://data.binance.vision/data/futures/um/monthly/klines"
KLINE_DAILY = "https://data.binance.vision/data/futures/um/daily/klines"
UA = {"User-Agent": "bababot-v7-regime-research/1.0"}


def http_bytes(url, tries=3, timeout=30):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as ex:
            last = ex
    raise RuntimeError(f"download_failed {url}: {last}")


def _dt_ms(v):
    return datetime.fromtimestamp(int(float(v)) / 1000.0, tz=timezone.utc)


def _months(start, end):
    y, m = start.year, start.month
    out = []
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        if m == 12:
            y += 1; m = 1
        else:
            m += 1
    return out


def _month_bounds(y, m):
    lo = datetime(y, m, 1, tzinfo=timezone.utc)
    hi = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if m == 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc)
    return lo, hi


def _daily_dates(lo, hi):
    d = lo.date(); end = (hi - timedelta(microseconds=1)).date()
    while d <= end:
        yield d
        d += timedelta(days=1)


def _parse_kline_zip(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    out = []
    for r in csv.reader(io.StringIO(txt)):
        if not r:
            continue
        try:
            t = _dt_ms(r[0]); o = float(r[1]); h = float(r[2]); l = float(r[3]); c = float(r[4]); v = float(r[5])
        except Exception:
            continue
        out.append({"t": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return out


def load_klines(symbol, tf, start, end):
    out = []
    for y, m in _months(start, end):
        mlo, mhi = _month_bounds(y, m)
        seg_lo = max(start, mlo); seg_hi = min(end, mhi)
        ym = f"{y:04d}-{m:02d}"
        monthly = f"{KLINE_MONTHLY}/{symbol}/{tf}/{symbol}-{tf}-{ym}.zip"
        try:
            out.extend(_parse_kline_zip(http_bytes(monthly, tries=2)))
            continue
        except Exception:
            pass
        for d in _daily_dates(seg_lo, seg_hi):
            ds = d.isoformat()
            daily = f"{KLINE_DAILY}/{symbol}/{tf}/{symbol}-{tf}-{ds}.zip"
            try:
                out.extend(_parse_kline_zip(http_bytes(daily, tries=2)))
            except Exception:
                continue
    dedup = {r["t"]: r for r in out if start <= r["t"] < end}
    return sorted(dedup.values(), key=lambda x: x["t"])


def build_regime_map(rows_1h):
    H = np.array([r["high"] for r in rows_1h], dtype=float)
    L = np.array([r["low"] for r in rows_1h], dtype=float)
    C = np.array([r["close"] for r in rows_1h], dtype=float)
    V = np.array([r["volume"] for r in rows_1h], dtype=float)
    states = classify_regime_series(H, L, C, V, RegimeConfig(), warmup=100)
    close_times = [r["t"] + timedelta(hours=1) for r in rows_1h]
    return close_times, states


def regime_at(signal_close, close_times, states):
    i = bisect.bisect_right(close_times, signal_close) - 1
    if i < 0:
        return Regime.UNKNOWN
    return states[i].regime


def resolve(rows5, idx, direction, entry, stop, target):
    end = min(len(rows5), idx + 1 + HORIZON_5M)
    if idx + 1 >= len(rows5):
        return "CENSORED", rows5[idx]["t"] + timedelta(minutes=5)
    for j in range(idx + 1, end):
        b = rows5[j]
        if direction == "LONG":
            tp = b["high"] >= target; sl = b["low"] <= stop
        else:
            tp = b["low"] <= target; sl = b["high"] >= stop
        if tp and sl:
            return "AMBIGUOUS", b["t"] + timedelta(minutes=5)
        if tp:
            return "WIN", b["t"] + timedelta(minutes=5)
        if sl:
            return "LOSS", b["t"] + timedelta(minutes=5)
    release = rows5[end - 1]["t"] + timedelta(minutes=5) if end > idx + 1 else rows5[idx]["t"] + timedelta(hours=72)
    return "CENSORED", release


def candidate_at(rows5, i):
    if i < LOOKBACK_5M:
        return None
    b = rows5[i]
    hist = rows5[i - LOOKBACK_5M:i]
    prior_low = min(x["low"] for x in hist)
    prior_high = max(x["high"] for x in hist)
    bull = b["low"] < prior_low and b["close"] > prior_low and b["close"] > b["open"]
    bear = b["high"] > prior_high and b["close"] < prior_high and b["close"] < b["open"]
    if bull and bear:
        return {"kind": "DUAL", "prior_low": prior_low, "prior_high": prior_high}
    if bull:
        return {"kind": "LONG", "prior_level": prior_low}
    if bear:
        return {"kind": "SHORT", "prior_level": prior_high}
    return None


def stat(events):
    resolved = [e for e in events if e["outcome"] in ("WIN", "LOSS")]
    n = len(resolved); w = sum(e["outcome"] == "WIN" for e in resolved)
    return {
        "signals": len(events), "resolved": n, "wins": w, "losses": n - w,
        "wr_pct": round(100.0 * w / n, 2) if n else None,
        "ambiguous": sum(e["outcome"] == "AMBIGUOUS" for e in events),
        "censored": sum(e["outcome"] == "CENSORED" for e in events),
    }


def median(events, key):
    xs = [float(e[key]) for e in events if e.get(key) is not None and math.isfinite(float(e[key]))]
    return round(statistics.median(xs), 8) if xs else None


def process_pair(symbol, rows1, rows5, sample_start, sample_end):
    close_times, states = build_regime_map(rows1)
    events = []; all_candidates = []; release_time = sample_start
    regime_signal_counts = Counter(); dual = 0; blocked_overlap = 0

    for i in range(LOOKBACK_5M, len(rows5)):
        b = rows5[i]
        signal_close = b["t"] + timedelta(minutes=5)
        if not (sample_start <= signal_close < sample_end):
            continue
        cand = candidate_at(rows5, i)
        if not cand:
            continue
        if cand["kind"] == "DUAL":
            dual += 1
            continue

        rg = regime_at(signal_close, close_times, states)
        regime_signal_counts[rg.value] += 1
        direction = cand["kind"]
        aligned = (direction == "LONG" and rg == Regime.BULL_MARKUP) or (direction == "SHORT" and rg == Regime.BEAR_MARKDOWN)

        entry = b["close"]
        stop = b["low"] if direction == "LONG" else b["high"]
        risk = entry - stop if direction == "LONG" else stop - entry
        if risk <= 0:
            continue
        target = entry + risk * RR if direction == "LONG" else entry - risk * RR
        outcome, ot = resolve(rows5, i, direction, entry, stop, target)
        base = {
            "symbol": symbol, "signal_time": signal_close, "direction": direction,
            "regime": rg.value, "aligned": aligned, "entry": entry, "stop": stop,
            "target": target, "risk_pct": 100.0 * risk / entry,
            "sweep_depth_pct": 100.0 * ((cand["prior_level"] - b["low"]) / cand["prior_level"] if direction == "LONG" else (b["high"] - cand["prior_level"]) / cand["prior_level"]),
            "outcome": outcome, "outcome_time": ot,
        }
        all_candidates.append(base)

        if not aligned:
            continue
        if signal_close < release_time:
            blocked_overlap += 1
            continue
        events.append(base)
        release_time = ot if ot is not None else signal_close + timedelta(hours=72)

    return events, all_candidates, {
        "regime_candidate_counts": dict(regime_signal_counts), "dual_sweeps_excluded": dual,
        "aligned_signals_blocked_one_position": blocked_overlap,
    }


def main():
    now = datetime.now(timezone.utc)
    today0 = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    sample_end = today0 - timedelta(days=3)  # full 72h outcome availability
    sample_start = sample_end - timedelta(days=DAYS)
    load_start = sample_start - timedelta(days=8)
    load_end = today0

    all_events = []; candidate_pool = []; coverage = {}; errors = {}; diagnostics = {}
    for p in PAIRS:
        try:
            r1 = load_klines(p, "1h", load_start, load_end)
            r5 = load_klines(p, "5m", load_start, load_end)
            ev, pool, diag = process_pair(p, r1, r5, sample_start, sample_end)
            all_events.extend(ev); candidate_pool.extend(pool); diagnostics[p] = diag
            coverage[p] = {
                "bars_1h": len(r1), "bars_5m": len(r5), "executed_aligned_events": len(ev),
                "candidate_pool": len(pool),
                "first_1h": r1[0]["t"].isoformat() if r1 else None,
                "last_1h": r1[-1]["t"].isoformat() if r1 else None,
                "first_5m": r5[0]["t"].isoformat() if r5 else None,
                "last_5m": r5[-1]["t"].isoformat() if r5 else None,
            }
        except Exception as ex:
            errors[p] = str(ex)

    overall = stat(all_events)
    by_pair = {p: stat([e for e in all_events if e["symbol"] == p]) for p in PAIRS}
    by_direction = {d: stat([e for e in all_events if e["direction"] == d]) for d in ("LONG", "SHORT")}

    cut = sample_start + timedelta(days=60)
    by_time = {
        "first_60d": stat([e for e in all_events if e["signal_time"] < cut]),
        "last_60d": stat([e for e in all_events if e["signal_time"] >= cut]),
        "cut": cut.isoformat(),
    }

    # Diagnostics only: resolve every candidate independently to compare aligned vs non-aligned setup quality.
    aligned_pool = [e for e in candidate_pool if e["aligned"]]
    nonaligned_pool = [e for e in candidate_pool if not e["aligned"]]
    pool_diag = {"aligned_independent": stat(aligned_pool), "nonaligned_independent": stat(nonaligned_pool)}

    resolved = [e for e in all_events if e["outcome"] in ("WIN", "LOSS")]
    wins = [e for e in resolved if e["outcome"] == "WIN"]
    losses = [e for e in resolved if e["outcome"] == "LOSS"]
    wl_diag = {
        "risk_pct": {"winner_median": median(wins, "risk_pct"), "loser_median": median(losses, "risk_pct")},
        "sweep_depth_pct": {"winner_median": median(wins, "sweep_depth_pct"), "loser_median": median(losses, "sweep_depth_pct")},
    }

    pair_pass = sum(1 for x in by_pair.values() if x["resolved"] >= 5 and (x["wr_pct"] or 0) > 50)
    dir_pass = all(by_direction[d]["resolved"] >= 10 and (by_direction[d]["wr_pct"] or 0) > 50 for d in by_direction)
    time_pass = all(by_time[k]["resolved"] >= 10 and (by_time[k]["wr_pct"] or 0) > 50 for k in ("first_60d", "last_60d"))
    earns = bool(overall["resolved"] >= 40 and (overall["wr_pct"] or 0) >= 70 and pair_pass >= 3 and dir_pass and time_pass)

    result = {
        "phase": "V7-A",
        "status": "FROZEN_REGIME_ALIGNED_FAILED_BREAKOUT_120D_SCREEN",
        "frozen_definition": {
            "regime": "existing mode3_regime 1H RegimeConfig defaults; latest fully completed 1H bar only",
            "tradeable_regimes": ["bull_markup", "bear_markdown"],
            "skip": ["accumulation", "distribution", "unknown"],
            "liquidity_reference": "previous 12 completed 5m bars (1h), current bar excluded",
            "long": "BULL_MARKUP + low<prior12_low + close>prior12_low + close>open",
            "short": "BEAR_MARKDOWN + high>prior12_high + close<prior12_high + close<open",
            "dual_sweep": "excluded", "entry": "5m signal close",
            "stop": "signal candle sweep extreme", "target": "1R",
            "tracking": "next 5m onward, <=72h; same-child TP+SL ambiguous excluded",
            "position_rule": "one position per pair; new aligned signals blocked until prior position releases",
            "threshold_sweep": False, "other_filters": False,
        },
        "predeclared_gate": {
            "overall_wr_pct": ">=70", "resolved_n": ">=40",
            "pair_distribution": ">=3/4 pairs each resolved>=5 and WR>50",
            "both_directions": "LONG and SHORT each resolved>=10 and WR>50",
            "both_60d_halves": "each resolved>=10 and WR>50",
        },
        "sample_start": sample_start.isoformat(), "sample_end_exclusive": sample_end.isoformat(),
        "coverage": coverage, "overall": overall, "by_pair": by_pair,
        "by_direction": by_direction, "by_time": by_time,
        "candidate_pool_diagnostic_only": pool_diag,
        "winner_loser_diagnostic_only": wl_diag,
        "mechanics_diagnostics": diagnostics,
        "gate_checks": {"pairs_passing": pair_pass, "direction_check": dir_pass, "time_check": time_pass, "earns_971d_validation": earns},
        "errors": errors,
        "notes": {
            "scientific_lock": "No alternate lookback, regime threshold, wick depth, body ratio, pair, side, RR, stop, or TP may be promoted post-hoc from this sample.",
            "interpretation": "Primary result is one-position aligned-regime execution. Candidate-pool comparison is diagnostic only.",
        },
    }
    print("V7_A_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
