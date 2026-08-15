"""V4-A2 First Retest Quality Test.

Purpose
-------
Measure whether V4-A1 structural demand/supply zones behave like real support/
resistance on their FIRST future retest.

This is still a research-quality test, NOT a trading strategy:
  - zones are generated causally using the frozen V4-A1 definition;
  - no V2 regime gate;
  - no absorption/order-flow filter;
  - no fee/PnL optimization;
  - first retest only;
  - geometric 1R test uses the zone width as risk;
  - 1m child candles resolve intrahour barrier ordering;
  - if ordering is unknowable inside the entry minute, result is AMBIGUOUS and
    excluded from WR rather than guessed.

GET /v4/first-retest?symbol=BTCUSDT&days=120&rr=1.0
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


def _load_1m(symbol: str, start_ms: int, end_ms: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT open_time, open, high, low, close
            FROM klines
            WHERE symbol=? AND timeframe='1m' AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, start_ms, end_ms),
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


def _first_retest_index(zone, H, L, T, max_retest_hours):
    """First future 1H candle whose range overlaps the zone interval."""
    start = int(zone["bos_bar"]) + 1
    max_ms = int(max_retest_hours * HOUR_MS)
    bos_ms = T[int(zone["bos_bar"])]
    for j in range(start, len(T)):
        if T[j] - bos_ms > max_ms:
            return None
        if float(L[j]) <= float(zone["zone_high"]) and float(H[j]) >= float(zone["zone_low"]):
            return j
    return None


def _levels(zone, rr):
    zlo = float(zone["zone_low"])
    zhi = float(zone["zone_high"])
    width = zhi - zlo
    if width <= 0:
        return None
    if zone["side"] == "DEMAND":
        entry = zhi                 # proximal edge approached from above
        stop = zlo                  # distal edge = structural break
        target = entry + rr * width
    else:
        entry = zlo                 # proximal edge approached from below
        stop = zhi
        target = entry - rr * width
    return entry, stop, target, width


def _resolve_with_1m(zone, retest_i, T1h, m_rows, m_times, rr, outcome_hours):
    """Resolve entry -> +/-R ordering using 1m children.

    We never award a target or stop inside the SAME 1m bar that first touches
    the entry boundary because OHLC does not reveal whether that excursion was
    before or after entry. Such cases are AMBIGUOUS_ENTRY_MINUTE.
    """
    lv = _levels(zone, rr)
    if lv is None:
        return {"outcome": "INVALID_ZONE"}
    entry, stop, target, width = lv

    retest_ms = int(T1h[retest_i])
    entry_window_end = retest_ms + HOUR_MS
    horizon_end = retest_ms + int(outcome_hours * HOUR_MS)

    k0 = bisect.bisect_left(m_times, retest_ms)
    k_entry = None
    k = k0
    while k < len(m_rows) and m_times[k] < entry_window_end:
        _, o, h, l, c = m_rows[k]
        if float(l) <= entry <= float(h):
            k_entry = k
            break
        k += 1

    if k_entry is None:
        return {"outcome": "NO_1M_ENTRY", "entry": entry, "stop": stop, "target": target}

    # Entry minute itself has unknowable within-minute ordering.
    _, _, eh, el, _ = m_rows[k_entry]
    if zone["side"] == "DEMAND":
        entry_minute_barrier = float(el) <= stop or float(eh) >= target
    else:
        entry_minute_barrier = float(eh) >= stop or float(el) <= target
    if entry_minute_barrier:
        return {
            "outcome": "AMBIGUOUS_ENTRY_MINUTE",
            "entry_time": _ts(m_times[k_entry]),
            "entry": entry, "stop": stop, "target": target, "risk": width,
        }

    for k in range(k_entry + 1, len(m_rows)):
        t, _, h, l, _ = m_rows[k]
        if t >= horizon_end:
            break
        h = float(h); l = float(l)
        if zone["side"] == "DEMAND":
            hit_target = h >= target
            hit_stop = l <= stop
        else:
            hit_target = l <= target
            hit_stop = h >= stop

        if hit_target and hit_stop:
            return {
                "outcome": "AMBIGUOUS_1M",
                "entry_time": _ts(m_times[k_entry]),
                "resolution_time": _ts(t),
                "entry": entry, "stop": stop, "target": target, "risk": width,
            }
        if hit_target:
            return {
                "outcome": "BOUNCE",
                "entry_time": _ts(m_times[k_entry]),
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - m_times[k_entry]) / MINUTE_MS),
                "entry": entry, "stop": stop, "target": target, "risk": width,
            }
        if hit_stop:
            return {
                "outcome": "BREAK",
                "entry_time": _ts(m_times[k_entry]),
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - m_times[k_entry]) / MINUTE_MS),
                "entry": entry, "stop": stop, "target": target, "risk": width,
            }

    data_end = m_times[-1] + MINUTE_MS if m_times else 0
    outcome = "CENSORED" if data_end < horizon_end else "UNRESOLVED"
    return {
        "outcome": outcome,
        "entry_time": _ts(m_times[k_entry]),
        "entry": entry, "stop": stop, "target": target, "risk": width,
    }


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


@router.get("")
def first_retest_quality(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    base_bars: int = Query(3, ge=2, le=5),
    base_search: int = Query(8, ge=4, le=20),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    bos_buffer_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_retest_hours: int = Query(720, ge=1, le=2160),
    outcome_hours: int = Query(72, ge=1, le=720),
    sample_limit: int = Query(30, ge=0, le=100),
):
    symbol = symbol.upper().strip()

    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + base_search + 10):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones = _build_a1_zones(
        rows, swing_lb, swing_atr, base_bars, base_search,
        min_displacement_atr, bos_buffer_atr,
    )
    if not zones:
        return {
            "phase": "V4-A2", "symbol": symbol, "requested_days": days,
            "error": "No V4-A1 zones generated with these frozen parameters",
        }

    m_rows = _load_1m(symbol, T[0], T[-1] + HOUR_MS)
    if not m_rows:
        return {
            "phase": "V4-A2", "symbol": symbol,
            "error": "No 1m child data available; refusing biased 1H intrabar assumptions",
        }
    m_times = [int(r[0]) for r in m_rows]

    results = []
    no_retest = 0
    for z in zones:
        r_i = _first_retest_index(z, H, L, T, max_retest_hours)
        if r_i is None:
            no_retest += 1
            item = dict(z)
            item.update({
                "outcome": "NO_RETEST",
                "retest_bar": None,
                "retest_time": None,
                "retest_age_hours": None,
            })
            results.append(item)
            continue

        age_h = round((T[r_i] - T[int(z["bos_bar"])]) / HOUR_MS, 2)
        width = float(z["zone_high"]) - float(z["zone_low"])
        if z["side"] == "DEMAND":
            penetration = (float(z["zone_high"]) - float(L[r_i])) / width if width > 0 else None
        else:
            penetration = (float(H[r_i]) - float(z["zone_low"])) / width if width > 0 else None

        resolution = _resolve_with_1m(z, r_i, T, m_rows, m_times, rr, outcome_hours)
        item = dict(z)
        item.update({
            "retest_bar": r_i,
            "retest_time": _ts(T[r_i]),
            "retest_age_hours": age_h,
            "first_touch_penetration_zone_width": round(float(penetration), 4) if penetration is not None else None,
        })
        item.update(resolution)
        results.append(item)

    overall = _stats(results)
    demand = _stats(results, "DEMAND")
    supply = _stats(results, "SUPPLY")

    resolved_rows = [x for x in results if x["outcome"] in {"BOUNCE", "BREAK"}]
    ages = [x["retest_age_hours"] for x in resolved_rows if x.get("retest_age_hours") is not None]
    mins = [x.get("minutes_to_resolution") for x in resolved_rows if x.get("minutes_to_resolution") is not None]

    def med(vals):
        return round(float(np.median(vals)), 2) if vals else None

    sample = results[-sample_limit:] if sample_limit else []
    return {
        "phase": "V4-A2",
        "status": "FIRST_RETEST_QUALITY_TEST",
        "symbol": symbol,
        "requested_days": days,
        "data": {
            "one_hour_rows": len(rows),
            "one_minute_rows": len(m_rows),
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
            "first_retest": "first future 1H candle overlapping the structural zone",
            "entry_reference": "proximal zone edge",
            "risk": "full zone width to distal edge",
            "target": f"{rr:.2f}R from proximal edge",
            "rr": rr,
            "max_retest_hours": max_retest_hours,
            "outcome_horizon_hours": outcome_hours,
            "same_entry_minute_barrier": "AMBIGUOUS; excluded rather than guessed",
            "same_later_1m_bar_both_barriers": "AMBIGUOUS; excluded rather than guessed",
        },
        "causality": {
            "zone_generation": "causal through BOS close",
            "outcome_data": "future data used only for evaluation label",
            "intrabar_order": "1m child candles",
            "regime_gate": False,
            "absorption_filter": False,
            "fees_or_pnl": False,
            "live_trading_changes": False,
        },
        "zone_counts": {
            "generated": len(zones),
            "no_retest_within_limit": no_retest,
        },
        "result": {
            "overall": overall,
            "demand": demand,
            "supply": supply,
            "median_retest_age_hours_resolved": med(ages),
            "median_minutes_to_resolution": med(mins),
        },
        "interpretation_rule": {
            "promising": "raw first-retest WR around 60-65%+ at 1R with healthy sample and both sides/pairs contributing",
            "target_70pct": "reserved for later V4-B after 1m absorption confirmation; not required from raw zones",
            "do_not_optimize_here": "do not tune many A1 parameters against this same 120d result",
        },
        "sample": sample,
        "next_phase": "V4-A3 feature/bucket analysis if A2 shows separation; otherwise revise zone mechanism before adding absorption",
    }
