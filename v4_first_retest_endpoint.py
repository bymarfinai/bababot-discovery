"""V4-A2 First Retest Quality Test — 5m execution baseline.

Purpose
-------
Measure whether V4-A1 structural demand/supply zones behave like real support/
resistance on their FIRST future retest.

Architecture:
    1H causal structure -> V4-A1 zone -> first 5m/15m retest -> +/-R outcome

This is still a research-quality test, NOT a trading strategy:
  - zones are generated causally using the frozen V4-A1 definition;
  - 1H creates structure; child timeframe only observes the future retest;
  - 5m is the default child timeframe; 15m is available as a robustness check;
  - no V2 regime gate;
  - no absorption/order-flow filter;
  - no fee/PnL optimization;
  - first retest only;
  - geometric R uses full zone width as risk;
  - if entry and TP/SL ordering is unknowable inside one child candle, the
    observation is AMBIGUOUS and excluded from WR rather than guessed.

GET /v4/first-retest?symbol=BTCUSDT&days=120&rr=1.0&execution_tf=5m
"""

import bisect
import sqlite3
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Query

from v4_structural_zone_endpoint import (
    DB_PATH,
    CausalSwingTracker,
    _atr,
    _compression_base,
    _load,
    _ts,
    _zone_features,
)

router = APIRouter(prefix="/v4/first-retest", tags=["v4_first_retest"])

HOUR_MS = 3_600_000
MINUTE_MS = 60_000
TF_MS = {"5m": 5 * MINUTE_MS, "15m": 15 * MINUTE_MS}


def _load_child(symbol: str, timeframe: str, start_ms: int, end_ms: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT open_time, open, high, low, close
            FROM klines
            WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, timeframe, start_ms, end_ms),
        )
        return cur.fetchall()
    finally:
        conn.close()


def _build_a1_zones(rows, swing_lb, swing_atr, base_bars, base_search,
                    min_displacement_atr, bos_buffer_atr):
    """Reproduce the frozen V4-A1 generator exactly for A2 evaluation."""
    T = [int(r[0]) for r in rows]
    O = np.asarray([r[1] for r in rows], dtype=float)
    H = np.asarray([r[2] for r in rows], dtype=float)
    L = np.asarray([r[3] for r in rows], dtype=float)
    C = np.asarray([r[4] for r in rows], dtype=float)
    V = np.asarray([r[5] for r in rows], dtype=float)
    ATR = _atr(H, L, C, 14)

    tracker = CausalSwingTracker(swing_lb, swing_atr)
    zones = []
    used_high_bars = set()
    used_low_bars = set()

    for i in range(len(rows)):
        tracker.update(i, H, L, ATR)
        if i < 1 or ATR[i] <= 0:
            continue

        prev_close = float(C[i - 1])
        close = float(C[i])
        a = float(ATR[i])

        sh = tracker.last_high
        if sh and sh["confirmed_at"] < i and sh["bar"] not in used_high_bars:
            threshold = sh["price"] + bos_buffer_atr * a
            if prev_close <= sh["price"] and close > threshold:
                base = _compression_base(H, L, ATR, i, base_search, base_bars)
                if base is not None:
                    feat = _zone_features("DEMAND", i, sh, base, O, H, L, C, V, ATR, T)
                    if feat["displacement_atr"] >= min_displacement_atr:
                        feat["zone_id"] = f"A2-D-{T[i]}"
                        zones.append(feat)
                        used_high_bars.add(sh["bar"])

        sl = tracker.last_low
        if sl and sl["confirmed_at"] < i and sl["bar"] not in used_low_bars:
            threshold = sl["price"] - bos_buffer_atr * a
            if prev_close >= sl["price"] and close < threshold:
                base = _compression_base(H, L, ATR, i, base_search, base_bars)
                if base is not None:
                    feat = _zone_features("SUPPLY", i, sl, base, O, H, L, C, V, ATR, T)
                    if feat["displacement_atr"] >= min_displacement_atr:
                        feat["zone_id"] = f"A2-S-{T[i]}"
                        zones.append(feat)
                        used_low_bars.add(sl["bar"])

    return T, O, H, L, C, ATR, zones


def _levels(zone, rr):
    zlo = float(zone["zone_low"])
    zhi = float(zone["zone_high"])
    width = zhi - zlo
    if width <= 0:
        return None
    if zone["side"] == "DEMAND":
        entry = zhi                 # proximal edge approached from above
        stop = zlo                  # distal edge = structural invalidation
        target = entry + rr * width
    else:
        entry = zlo                 # proximal edge approached from below
        stop = zhi
        target = entry - rr * width
    return entry, stop, target, width


def _coverage(child_rows, start_ms, end_ms, execution_tf):
    step = TF_MS[execution_tf]
    expected = max(1, int((end_ms - start_ms) / step))
    actual = len(child_rows)
    return {
        "expected_rows": expected,
        "actual_rows": actual,
        "coverage_pct": round(100.0 * actual / expected, 2),
    }


def _resolve_first_retest(zone, T1h, child_rows, child_times, execution_tf,
                          rr, max_retest_hours, outcome_hours):
    """Find first child-TF retest after BOS close, then resolve +/-R.

    The structural BOS is known only after its 1H candle closes. Therefore the
    child scan starts at bos_open_time + 1 hour. This prevents using any child
    candle from inside the still-forming BOS hour.
    """
    lv = _levels(zone, rr)
    if lv is None:
        return {"outcome": "INVALID_ZONE"}
    entry, stop, target, width = lv

    bos_bar = int(zone["bos_bar"])
    bos_close_ms = int(T1h[bos_bar]) + HOUR_MS
    max_retest_ms = bos_close_ms + int(max_retest_hours * HOUR_MS)
    step_ms = TF_MS[execution_tf]

    k0 = bisect.bisect_left(child_times, bos_close_ms)
    k_entry = None
    for k in range(k0, len(child_rows)):
        t, _, h, l, _ = child_rows[k]
        if t > max_retest_ms:
            break
        if float(l) <= entry <= float(h):
            k_entry = k
            break

    if k_entry is None:
        return {
            "outcome": "NO_RETEST",
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk": width,
        }

    entry_t, _, entry_h, entry_l, _ = child_rows[k_entry]
    age_h = round((entry_t - bos_close_ms) / HOUR_MS, 4)

    # We know the candle touched entry, but not the within-candle path. If that
    # same candle also reaches stop/target, do not invent an ordering.
    if zone["side"] == "DEMAND":
        hit_stop_same = float(entry_l) <= stop
        hit_target_same = float(entry_h) >= target
        penetration = (entry - float(entry_l)) / width
    else:
        hit_stop_same = float(entry_h) >= stop
        hit_target_same = float(entry_l) <= target
        penetration = (float(entry_h) - entry) / width

    base = {
        "retest_time": _ts(entry_t),
        "retest_age_hours": age_h,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk": width,
        "first_touch_penetration_zone_width": round(float(penetration), 4),
        "execution_tf": execution_tf,
    }

    if hit_stop_same or hit_target_same:
        base.update({
            "outcome": "AMBIGUOUS_ENTRY_BAR",
            "same_bar_hit_stop": bool(hit_stop_same),
            "same_bar_hit_target": bool(hit_target_same),
        })
        return base

    horizon_end = entry_t + int(outcome_hours * HOUR_MS)
    for k in range(k_entry + 1, len(child_rows)):
        t, _, h, l, _ = child_rows[k]
        if t >= horizon_end:
            break
        h = float(h)
        l = float(l)

        if zone["side"] == "DEMAND":
            hit_target = h >= target
            hit_stop = l <= stop
        else:
            hit_target = l <= target
            hit_stop = h >= stop

        if hit_target and hit_stop:
            base.update({
                "outcome": "AMBIGUOUS_CHILD_BAR",
                "resolution_time": _ts(t),
            })
            return base
        if hit_target:
            base.update({
                "outcome": "BOUNCE",
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - entry_t) / MINUTE_MS),
            })
            return base
        if hit_stop:
            base.update({
                "outcome": "BREAK",
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - entry_t) / MINUTE_MS),
            })
            return base

    data_end = child_times[-1] + step_ms if child_times else 0
    base["outcome"] = "CENSORED" if data_end < horizon_end else "UNRESOLVED"
    return base


def _stats(items, side=None):
    xs = [x for x in items if side is None or x["side"] == side]
    counts = {}
    for x in xs:
        o = x["outcome"]
        counts[o] = counts.get(o, 0) + 1
    wins = counts.get("BOUNCE", 0)
    losses = counts.get("BREAK", 0)
    resolved = wins + losses
    wr = round(100.0 * wins / resolved, 2) if resolved else None
    return {
        "zones": len(xs),
        "resolved": resolved,
        "bounce": wins,
        "break": losses,
        "wr_pct": wr,
        "excluded_from_wr": len(xs) - resolved,
        "outcome_counts": counts,
    }


def _median(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 2) if vals else None


@router.get("")
def first_retest_quality(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    execution_tf: str = Query("5m"),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    base_bars: int = Query(3, ge=2, le=5),
    base_search: int = Query(8, ge=4, le=20),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    bos_buffer_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_retest_hours: int = Query(720, ge=1, le=2160),
    outcome_hours: int = Query(72, ge=1, le=720),
    min_child_coverage_pct: float = Query(95.0, ge=50.0, le=100.0),
    sample_limit: int = Query(30, ge=0, le=100),
):
    symbol = symbol.upper().strip()
    execution_tf = execution_tf.lower().strip()
    if execution_tf not in TF_MS:
        return {"error": "execution_tf must be 5m or 15m"}

    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + base_search + 10):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones = _build_a1_zones(
        rows, swing_lb, swing_atr, base_bars, base_search,
        min_displacement_atr, bos_buffer_atr,
    )
    if not zones:
        return {
            "phase": "V4-A2",
            "symbol": symbol,
            "requested_days": days,
            "error": "No V4-A1 zones generated with these frozen parameters",
        }

    child_start = T[0]
    child_end = T[-1] + HOUR_MS
    child_rows = _load_child(symbol, execution_tf, child_start, child_end)
    if not child_rows:
        return {
            "phase": "V4-A2",
            "symbol": symbol,
            "execution_tf": execution_tf,
            "error": f"No {execution_tf} child data available. Fetch it before evaluating A2.",
            "fetch_hint": {
                "endpoint": "/fetch-data",
                "days": days,
                "pairs": [symbol],
                "timeframes": [execution_tf],
            },
        }

    coverage = _coverage(child_rows, child_start, child_end, execution_tf)
    if coverage["coverage_pct"] < min_child_coverage_pct:
        return {
            "phase": "V4-A2",
            "symbol": symbol,
            "execution_tf": execution_tf,
            "error": "Child timeframe coverage below required threshold; refusing a biased WR estimate",
            "coverage": coverage,
            "minimum_required_pct": min_child_coverage_pct,
        }

    child_times = [int(r[0]) for r in child_rows]
    results = []
    for z in zones:
        resolution = _resolve_first_retest(
            z, T, child_rows, child_times, execution_tf, rr,
            max_retest_hours, outcome_hours,
        )
        item = dict(z)
        item.update(resolution)
        results.append(item)

    overall = _stats(results)
    demand = _stats(results, "DEMAND")
    supply = _stats(results, "SUPPLY")

    resolved_rows = [x for x in results if x["outcome"] in {"BOUNCE", "BREAK"}]
    ages = [x.get("retest_age_hours") for x in resolved_rows]
    mins = [x.get("minutes_to_resolution") for x in resolved_rows]

    sample = results[-sample_limit:] if sample_limit else []
    return {
        "phase": "V4-A2",
        "status": "FIRST_RETEST_QUALITY_TEST",
        "symbol": symbol,
        "requested_days": days,
        "data": {
            "one_hour_rows": len(rows),
            "child_timeframe": execution_tf,
            "child_rows": len(child_rows),
            "coverage": coverage,
            "start": _ts(T[0]),
            "end": _ts(T[-1]),
        },
        "frozen_a1_definition": {
            "swing_lb": swing_lb,
            "swing_atr": swing_atr,
            "base_bars": base_bars,
            "base_search": base_search,
            "min_displacement_atr": min_displacement_atr,
            "bos_buffer_atr": bos_buffer_atr,
        },
        "a2_definition": {
            "structure_timeframe": "1h",
            "execution_timeframe": execution_tf,
            "first_retest": f"first {execution_tf} candle after 1H BOS close that touches the proximal zone edge",
            "entry_reference": "proximal zone edge",
            "risk": "full zone width to distal edge",
            "target": f"{rr:.2f}R from proximal edge",
            "rr": rr,
            "max_retest_hours": max_retest_hours,
            "outcome_horizon_hours": outcome_hours,
            "same_entry_bar_barrier": "AMBIGUOUS; excluded rather than guessed",
            "same_child_bar_tp_and_sl": "AMBIGUOUS; excluded rather than guessed",
            "regime_gate": False,
            "absorption_filter": False,
            "fees_pnl": False,
        },
        "zone_count": len(zones),
        "overall": overall,
        "demand": demand,
        "supply": supply,
        "diagnostics": {
            "median_retest_age_hours_resolved": _median(ages),
            "median_minutes_to_resolution": _median(mins),
            "ambiguous_entry_bars": sum(1 for x in results if x["outcome"] == "AMBIGUOUS_ENTRY_BAR"),
            "ambiguous_child_bars": sum(1 for x in results if x["outcome"] == "AMBIGUOUS_CHILD_BAR"),
            "no_retest": sum(1 for x in results if x["outcome"] == "NO_RETEST"),
        },
        "results_sample": sample,
        "next_phase": "V4-A3 feature separation only if A2 shows a meaningful raw structural-zone edge",
    }
