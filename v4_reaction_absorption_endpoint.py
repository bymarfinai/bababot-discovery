"""V4-B Reaction / Absorption Confirmation.

Hypothesis
----------
A structural zone is only a location of interest. It becomes tradable only when
5m taker flow attacks the zone but price fails to structurally progress, then
closes back out of the zone.

Frozen baseline:
  1H V4-A1 structural zone
  -> first future 5m touch after BOS close
  -> within <=3 completed 5m bars:
       * cumulative signed taker quote delta is AGAINST the intended trade
       * no close invalidates the distal edge before confirmation
       * close reclaims beyond the proximal edge
  -> entry at confirmation close
  -> stop at distal edge
  -> target = 1R

Demand absorption example:
  net aggressive sells (negative taker delta) attack demand, yet price cannot
  close below the distal edge and then closes back above zone_high.

Supply is symmetric.

No EMA/regime gate, no delta magnitude threshold, no parameter optimization,
no fee/PnL optimization, and no live-trading integration are used here.
"""

import bisect
import sqlite3
from fastapi import APIRouter, Query

from v4_structural_zone_endpoint import _load, _ts
from v4_first_retest_endpoint import (
    DB_PATH,
    HOUR_MS,
    MINUTE_MS,
    TF_MS,
    _build_a1_zones,
    _coverage,
)

router = APIRouter(prefix="/v4/reaction-absorption", tags=["v4_reaction_absorption"])


def _load_child_full(symbol: str, timeframe: str, start_ms: int, end_ms: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT open_time, open, high, low, close,
                   quote_volume, taker_buy_quote_volume
            FROM klines
            WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, timeframe, start_ms, end_ms),
        ).fetchall()
    finally:
        conn.close()


def _bar_delta_quote(row):
    quote = float(row[5] or 0.0)
    taker_buy_quote = float(row[6] or 0.0)
    return 2.0 * taker_buy_quote - quote


def _find_confirmation(zone, T1h, child_rows, child_times,
                       confirm_bars: int, max_retest_hours: int):
    """Find first zone touch and causal 5m absorption/reclaim confirmation."""
    zlo = float(zone["zone_low"])
    zhi = float(zone["zone_high"])
    if zhi <= zlo:
        return {"signal_status": "INVALID_ZONE"}

    bos_i = int(zone["bos_bar"])
    bos_close_ms = int(T1h[bos_i]) + HOUR_MS
    max_retest_ms = bos_close_ms + int(max_retest_hours * HOUR_MS)

    k0 = bisect.bisect_left(child_times, bos_close_ms)
    touch_k = None
    for k in range(k0, len(child_rows)):
        t, _, h, l, _, _, _ = child_rows[k]
        if t > max_retest_ms:
            break
        if float(l) <= zhi and float(h) >= zlo:
            touch_k = k
            break

    if touch_k is None:
        return {"signal_status": "NO_RETEST"}

    cum_delta = 0.0
    cum_quote = 0.0
    end_k = min(len(child_rows), touch_k + confirm_bars)

    for k in range(touch_k, end_k):
        t, o, h, l, c, quote, tbq = child_rows[k]
        c = float(c)
        quote = float(quote or 0.0)
        delta = 2.0 * float(tbq or 0.0) - quote
        cum_delta += delta
        cum_quote += quote

        # Structural invalidation is based on CLOSE, not wick. A pre-entry wick
        # through the zone is allowed; it can itself be part of the absorption.
        if zone["side"] == "DEMAND":
            if c < zlo:
                return {
                    "signal_status": "INVALIDATED_BEFORE_CONFIRM",
                    "touch_time": _ts(child_rows[touch_k][0]),
                    "invalidated_time": _ts(t),
                }
            reclaimed = c > zhi
            pressure_against_trade = cum_delta < 0.0
        else:
            if c > zhi:
                return {
                    "signal_status": "INVALIDATED_BEFORE_CONFIRM",
                    "touch_time": _ts(child_rows[touch_k][0]),
                    "invalidated_time": _ts(t),
                }
            reclaimed = c < zlo
            pressure_against_trade = cum_delta > 0.0

        if reclaimed and pressure_against_trade:
            delta_pct = 100.0 * cum_delta / cum_quote if cum_quote > 0 else 0.0
            return {
                "signal_status": "CONFIRMED",
                "touch_k": touch_k,
                "confirm_k": k,
                "touch_time": _ts(child_rows[touch_k][0]),
                "confirm_time": _ts(t),
                "bars_to_confirm": int(k - touch_k + 1),
                "cumulative_delta_quote": round(float(cum_delta), 4),
                "cumulative_delta_pct": round(float(delta_pct), 4),
                "entry": c,
            }

    delta_pct = 100.0 * cum_delta / cum_quote if cum_quote > 0 else 0.0
    return {
        "signal_status": "NO_CONFIRM",
        "touch_time": _ts(child_rows[touch_k][0]),
        "cumulative_delta_quote": round(float(cum_delta), 4),
        "cumulative_delta_pct": round(float(delta_pct), 4),
    }


def _resolve_after_confirmation(zone, confirm, child_rows, rr: float,
                                outcome_hours: int):
    if confirm.get("signal_status") != "CONFIRMED":
        return {"outcome": None}

    entry = float(confirm["entry"])
    zlo = float(zone["zone_low"])
    zhi = float(zone["zone_high"])

    if zone["side"] == "DEMAND":
        stop = zlo
        risk = entry - stop
        target = entry + rr * risk
    else:
        stop = zhi
        risk = stop - entry
        target = entry - rr * risk

    if risk <= 0:
        return {"outcome": "INVALID_RISK"}

    k0 = int(confirm["confirm_k"]) + 1
    entry_t = int(child_rows[int(confirm["confirm_k"])][0])
    horizon_end = entry_t + int(outcome_hours * HOUR_MS)

    for k in range(k0, len(child_rows)):
        t, _, h, l, _, _, _ = child_rows[k]
        if t >= horizon_end:
            break
        h = float(h); l = float(l)

        if zone["side"] == "DEMAND":
            hit_tp = h >= target
            hit_sl = l <= stop
        else:
            hit_tp = l <= target
            hit_sl = h >= stop

        if hit_tp and hit_sl:
            return {
                "outcome": "AMBIGUOUS_CHILD_BAR",
                "resolution_time": _ts(t),
                "stop": stop, "target": target, "risk": risk,
            }
        if hit_tp:
            return {
                "outcome": "BOUNCE",
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - entry_t) / MINUTE_MS),
                "stop": stop, "target": target, "risk": risk,
            }
        if hit_sl:
            return {
                "outcome": "BREAK",
                "resolution_time": _ts(t),
                "minutes_to_resolution": int((t - entry_t) / MINUTE_MS),
                "stop": stop, "target": target, "risk": risk,
            }

    data_end = int(child_rows[-1][0]) + TF_MS["5m"] if child_rows else 0
    return {
        "outcome": "CENSORED" if data_end < horizon_end else "UNRESOLVED",
        "stop": stop, "target": target, "risk": risk,
    }


def _stats(items, side=None):
    xs = [x for x in items if side is None or x["side"] == side]
    signals = [x for x in xs if x.get("signal_status") == "CONFIRMED"]
    resolved = [x for x in signals if x.get("outcome") in {"BOUNCE", "BREAK"}]
    wins = sum(x["outcome"] == "BOUNCE" for x in resolved)
    losses = sum(x["outcome"] == "BREAK" for x in resolved)
    touched = sum(x.get("signal_status") not in {"NO_RETEST", "INVALID_ZONE"} for x in xs)
    counts = {}
    for x in xs:
        s = x.get("signal_status", "UNKNOWN")
        counts[s] = counts.get(s, 0) + 1
    out_counts = {}
    for x in signals:
        o = x.get("outcome") or "NONE"
        out_counts[o] = out_counts.get(o, 0) + 1
    return {
        "zones": len(xs),
        "touched": touched,
        "confirmed_signals": len(signals),
        "confirmation_rate_of_touches_pct": round(100.0 * len(signals) / touched, 2) if touched else None,
        "resolved": len(resolved),
        "bounce": wins,
        "break": losses,
        "wr_pct": round(100.0 * wins / len(resolved), 2) if resolved else None,
        "signal_status_counts": counts,
        "outcome_counts": out_counts,
    }


@router.get("")
def reaction_absorption_test(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    execution_tf: str = Query("5m"),
    confirm_bars: int = Query(3, ge=1, le=12),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    base_bars: int = Query(3, ge=2, le=5),
    base_search: int = Query(8, ge=4, le=20),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    bos_buffer_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_retest_hours: int = Query(720, ge=1, le=2160),
    outcome_hours: int = Query(72, ge=1, le=720),
    min_child_coverage_pct: float = Query(95.0, ge=50.0, le=100.0),
    sample_limit: int = Query(50, ge=0, le=200),
):
    symbol = symbol.upper().strip()
    execution_tf = execution_tf.lower().strip()
    if execution_tf != "5m":
        return {"error": "V4-B frozen baseline uses execution_tf=5m only"}

    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + base_search + 10):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones = _build_a1_zones(
        rows, swing_lb, swing_atr, base_bars, base_search,
        min_displacement_atr, bos_buffer_atr,
    )
    if not zones:
        return {"phase": "V4-B", "symbol": symbol, "error": "No A1 structural zones"}

    child_start = T[0]
    child_end = T[-1] + HOUR_MS
    child_rows = _load_child_full(symbol, "5m", child_start, child_end)
    if not child_rows:
        return {"phase": "V4-B", "symbol": symbol, "error": "No 5m child data"}

    coverage = _coverage(child_rows, child_start, child_end, "5m")
    if coverage["coverage_pct"] < min_child_coverage_pct:
        return {
            "phase": "V4-B", "symbol": symbol,
            "error": "5m coverage below threshold; refusing biased WR estimate",
            "coverage": coverage,
        }

    child_times = [int(r[0]) for r in child_rows]
    results = []
    for z in zones:
        conf = _find_confirmation(
            z, T, child_rows, child_times, confirm_bars, max_retest_hours,
        )
        outcome = _resolve_after_confirmation(z, conf, child_rows, rr, outcome_hours)
        item = dict(z)
        item.update(conf)
        item.update(outcome)
        results.append(item)

    overall = _stats(results)
    demand = _stats(results, "DEMAND")
    supply = _stats(results, "SUPPLY")

    resolved = [x for x in results if x.get("outcome") in {"BOUNCE", "BREAK"}]
    return {
        "phase": "V4-B",
        "status": "REACTION_ABSORPTION_CONFIRMATION_TEST",
        "symbol": symbol,
        "requested_days": days,
        "data": {
            "one_hour_rows": len(rows),
            "child_timeframe": "5m",
            "child_rows": len(child_rows),
            "coverage": coverage,
            "start": _ts(T[0]),
            "end": _ts(T[-1]),
        },
        "frozen_definition": {
            "location": "V4-A1 1H structural zone only; zone is not an entry signal",
            "first_touch_only": True,
            "confirmation_window_5m_bars": confirm_bars,
            "signed_taker_quote_delta": "2*taker_buy_quote_volume - quote_volume",
            "demand_absorption": "cumulative delta < 0 while no close below distal; confirm on close > proximal",
            "supply_absorption": "cumulative delta > 0 while no close above distal; confirm on close < proximal",
            "delta_magnitude_threshold": None,
            "entry": "5m confirmation close",
            "stop": "zone distal edge",
            "target": f"{rr:.2f}R from actual entry",
            "outcome_scan_begins": "next 5m candle after confirmation close",
            "regime_gate": False,
            "fees_pnl": False,
        },
        "zone_count": len(zones),
        "overall": overall,
        "demand": demand,
        "supply": supply,
        "diagnostics": {
            "ambiguous_child_bars": sum(x.get("outcome") == "AMBIGUOUS_CHILD_BAR" for x in results),
            "median_abs_delta_pct_resolved": round(
                sorted(abs(float(x.get("cumulative_delta_pct", 0.0))) for x in resolved)[len(resolved)//2], 4
            ) if resolved else None,
        },
        "results_sample": results[-sample_limit:] if sample_limit else [],
        "gate": {
            "feasibility": "confirmation should materially improve raw A1 WR and retain enough samples across pairs/time",
            "strategy_target": ">=70% WR at RR >=1:1 before 971d validation",
        },
    }
