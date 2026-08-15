"""V4-A1.3 — Liquidity-Validated Displacement Origin / Order Block.

Hypothesis
----------
A liquidity sweep is context, not the support/resistance zone itself.
After a causal sweep + reclaim/rejection, the zone is the LAST opposite-color
1H candle after the sweep and before the validating opposing BOS.

Demand:
  confirmed swing-low sweep/reclaim -> last bearish candle after sweep ->
  bullish opposing BOS -> body/range of that bearish candle = demand origin.
Supply is symmetric with the last bullish candle.

The sweep/BOS event definition is frozen from V4-A1.1. Only two predeclared
zone geometries are exposed: body (baseline) and full range (robustness).
First future retest is evaluated on 5m/15m using the same causal A2 resolver.
No regime, absorption, EMA, fee/PnL, or live-trading integration.
"""

from fastapi import APIRouter, Query
import numpy as np

from v4_structural_zone_endpoint import _load, _ts
from v4_liquidity_zone_endpoint import build_liquidity_zones
from v4_first_retest_endpoint import (
    HOUR_MS,
    TF_MS,
    _load_child,
    _coverage,
    _resolve_first_retest,
    _stats,
    _median,
)

router = APIRouter(prefix="/v4/liquidity-origin-retest", tags=["v4_liquidity_origin_retest"])


def _origin_from_event(event, O, H, L, C, ATR, T, zone_mode="body",
                       min_origin_displacement_atr=1.0):
    side = event["side"]
    sweep_i = int(event["sweep_bar"])
    bos_i = int(event["bos_bar"])
    if bos_i <= sweep_i:
        return None, "same_bar_bos_no_post_sweep_origin"

    # Deterministic last opposite-color candle in [sweep, BOS).
    candidates = []
    for k in range(sweep_i, bos_i):
        if side == "DEMAND" and float(C[k]) < float(O[k]):
            candidates.append(k)
        elif side == "SUPPLY" and float(C[k]) > float(O[k]):
            candidates.append(k)
    if not candidates:
        return None, "no_opposite_origin_candle"

    k = candidates[-1]
    if zone_mode == "body":
        zlo = min(float(O[k]), float(C[k]))
        zhi = max(float(O[k]), float(C[k]))
    elif zone_mode == "range":
        zlo = float(L[k])
        zhi = float(H[k])
    else:
        return None, "invalid_zone_mode"

    if zhi <= zlo:
        return None, "zero_width_origin"

    a_bos = float(ATR[bos_i]) if float(ATR[bos_i]) > 0 else 1.0
    a_origin = float(ATR[k]) if float(ATR[k]) > 0 else 1.0
    if side == "DEMAND":
        origin_displacement_atr = (float(C[bos_i]) - zhi) / a_bos
    else:
        origin_displacement_atr = (zlo - float(C[bos_i])) / a_bos

    if origin_displacement_atr < min_origin_displacement_atr:
        return None, "origin_displacement_below_threshold"

    rng = float(H[k] - L[k])
    body_ratio = abs(float(C[k] - O[k])) / rng if rng > 0 else 0.0

    z = dict(event)
    z.update({
        "zone_id": f"LQO-{side[0]}-{zone_mode}-{T[bos_i]}-{T[k]}",
        "zone_mode": zone_mode,
        "origin_bar": int(k),
        "origin_time": _ts(T[k]),
        "origin_open": round(float(O[k]), 8),
        "origin_high": round(float(H[k]), 8),
        "origin_low": round(float(L[k]), 8),
        "origin_close": round(float(C[k]), 8),
        "zone_low": round(zlo, 8),
        "zone_high": round(zhi, 8),
        "zone_mid": round((zlo + zhi) / 2.0, 8),
        "zone_width_atr": round((zhi - zlo) / a_origin, 4),
        "origin_body_ratio": round(body_ratio, 4),
        "origin_displacement_atr": round(float(origin_displacement_atr), 4),
        "bars_sweep_to_origin": int(k - sweep_i),
        "bars_origin_to_bos": int(bos_i - k),
    })
    return z, None


def build_liquidity_origin_zones(rows, swing_lb=10, swing_atr=0.5,
                                 min_sweep_depth_atr=0.0, max_bos_bars=12,
                                 min_displacement_atr=1.0, zone_mode="body",
                                 min_origin_displacement_atr=1.0):
    T, O, H, L, C, ATR, events, event_rejected = build_liquidity_zones(
        rows, swing_lb, swing_atr, min_sweep_depth_atr,
        max_bos_bars, min_displacement_atr, zone_mode="pocket",
    )
    zones = []
    rejected = {
        "same_bar_bos_no_post_sweep_origin": 0,
        "no_opposite_origin_candle": 0,
        "zero_width_origin": 0,
        "origin_displacement_below_threshold": 0,
    }
    for ev in events:
        z, why = _origin_from_event(
            ev, O, H, L, C, ATR, T, zone_mode,
            min_origin_displacement_atr,
        )
        if z is None:
            rejected[why] = rejected.get(why, 0) + 1
        else:
            zones.append(z)
    return T, O, H, L, C, ATR, zones, {
        "event_rejected": event_rejected,
        "origin_rejected": rejected,
        "validated_liquidity_events": len(events),
    }


@router.get("")
def liquidity_origin_first_retest(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    execution_tf: str = Query("5m"),
    zone_mode: str = Query("body"),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    min_sweep_depth_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_bos_bars: int = Query(12, ge=1, le=48),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    min_origin_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    max_retest_hours: int = Query(720, ge=1, le=2160),
    outcome_hours: int = Query(72, ge=1, le=720),
    min_child_coverage_pct: float = Query(95.0, ge=50.0, le=100.0),
    sample_limit: int = Query(30, ge=0, le=200),
):
    symbol = symbol.upper().strip()
    execution_tf = execution_tf.lower().strip()
    zone_mode = zone_mode.lower().strip()
    if execution_tf not in TF_MS:
        return {"error": "execution_tf must be 5m or 15m"}
    if zone_mode not in {"body", "range"}:
        return {"error": "zone_mode must be body or range"}

    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + 20):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones, rejected = build_liquidity_origin_zones(
        rows, swing_lb, swing_atr, min_sweep_depth_atr,
        max_bos_bars, min_displacement_atr, zone_mode,
        min_origin_displacement_atr,
    )
    if not zones:
        return {
            "phase": "V4-A1.3",
            "status": "LIQUIDITY_VALIDATED_ORIGIN_FIRST_RETEST",
            "symbol": symbol,
            "zone_mode": zone_mode,
            "zone_count": 0,
            "rejected": rejected,
            "error": "No liquidity-validated displacement-origin zones generated",
        }

    child_start = T[0]
    child_end = T[-1] + HOUR_MS
    child_rows = _load_child(symbol, execution_tf, child_start, child_end)
    if not child_rows:
        return {"phase": "V4-A1.3", "symbol": symbol,
                "error": f"No {execution_tf} child data available"}
    coverage = _coverage(child_rows, child_start, child_end, execution_tf)
    if coverage["coverage_pct"] < min_child_coverage_pct:
        return {
            "phase": "V4-A1.3", "symbol": symbol,
            "error": "Child timeframe coverage below threshold; refusing biased WR",
            "coverage": coverage,
        }

    child_times = [int(r[0]) for r in child_rows]
    results = []
    for z in zones:
        res = _resolve_first_retest(
            z, T, child_rows, child_times, execution_tf, rr,
            max_retest_hours, outcome_hours,
        )
        item = dict(z)
        item.update(res)
        results.append(item)

    overall = _stats(results)
    demand = _stats(results, "DEMAND")
    supply = _stats(results, "SUPPLY")
    resolved = [x for x in results if x["outcome"] in {"BOUNCE", "BREAK"}]

    return {
        "phase": "V4-A1.3",
        "status": "LIQUIDITY_VALIDATED_ORIGIN_FIRST_RETEST",
        "symbol": symbol,
        "requested_days": days,
        "zone_mode": zone_mode,
        "data": {
            "one_hour_rows": len(rows),
            "child_timeframe": execution_tf,
            "child_rows": len(child_rows),
            "coverage": coverage,
            "start": _ts(T[0]),
            "end": _ts(T[-1]),
        },
        "frozen_definition": {
            "structure_timeframe": "1h",
            "execution_timeframe": execution_tf,
            "event": "confirmed liquidity sweep/reclaim -> opposing BOS",
            "origin": "last opposite-color 1H candle in [sweep, BOS)",
            "zone_mode": zone_mode,
            "min_origin_displacement_atr": min_origin_displacement_atr,
            "rr": rr,
            "first_retest_only": True,
            "regime_gate": False,
            "absorption_filter": False,
            "fees_pnl": False,
        },
        "zone_count": len(zones),
        "overall": overall,
        "demand": demand,
        "supply": supply,
        "diagnostics": {
            "median_retest_age_hours_resolved": _median([x.get("retest_age_hours") for x in resolved]),
            "median_minutes_to_resolution": _median([x.get("minutes_to_resolution") for x in resolved]),
            "ambiguous_entry_bars": sum(x["outcome"] == "AMBIGUOUS_ENTRY_BAR" for x in results),
            "ambiguous_child_bars": sum(x["outcome"] == "AMBIGUOUS_CHILD_BAR" for x in results),
            "no_retest": sum(x["outcome"] == "NO_RETEST" for x in results),
            "rejected": rejected,
        },
        "results_sample": results[-sample_limit:] if sample_limit else [],
        "gate": {
            "raw_zone_target": ">=60-65% WR at RR 1:1 with cross-pair consistency",
            "strategy_target": ">=70% WR at RR >=1:1 only after later confirmation",
        },
    }
