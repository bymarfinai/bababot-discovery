"""V4-A1.1 liquidity-created zone first-retest evaluator.

Architecture:
    1H confirmed liquidity sweep/reclaim -> opposing BOS -> liquidity pocket zone
    -> first future 5m retest -> +/-1R outcome

No regime, absorption, fee/PnL, or parameter optimization is applied here.
"""

from fastapi import APIRouter, Query

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

router = APIRouter(prefix="/v4/liquidity-retest", tags=["v4_liquidity_retest"])


@router.get("")
def liquidity_first_retest(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    execution_tf: str = Query("5m"),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    min_sweep_depth_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_bos_bars: int = Query(12, ge=1, le=48),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    max_retest_hours: int = Query(720, ge=1, le=2160),
    outcome_hours: int = Query(72, ge=1, le=720),
    min_child_coverage_pct: float = Query(95.0, ge=50.0, le=100.0),
    sample_limit: int = Query(30, ge=0, le=200),
):
    symbol = symbol.upper().strip()
    execution_tf = execution_tf.lower().strip()
    if execution_tf not in TF_MS:
        return {"error": "execution_tf must be 5m or 15m"}

    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + 20):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones, rejected = build_liquidity_zones(
        rows, swing_lb, swing_atr, min_sweep_depth_atr,
        max_bos_bars, min_displacement_atr,
    )
    if not zones:
        return {
            "phase": "V4-A1.1",
            "status": "LIQUIDITY_FIRST_RETEST_TEST",
            "symbol": symbol,
            "requested_days": days,
            "zone_count": 0,
            "rejected": rejected,
            "error": "No liquidity-created zones generated with frozen baseline parameters",
        }

    child_start = T[0]
    child_end = T[-1] + HOUR_MS
    child_rows = _load_child(symbol, execution_tf, child_start, child_end)
    if not child_rows:
        return {
            "phase": "V4-A1.1",
            "symbol": symbol,
            "execution_tf": execution_tf,
            "error": f"No {execution_tf} child data available. Fetch it before evaluation.",
        }

    coverage = _coverage(child_rows, child_start, child_end, execution_tf)
    if coverage["coverage_pct"] < min_child_coverage_pct:
        return {
            "phase": "V4-A1.1",
            "symbol": symbol,
            "execution_tf": execution_tf,
            "error": "Child timeframe coverage below required threshold; refusing biased WR estimate",
            "coverage": coverage,
            "minimum_required_pct": min_child_coverage_pct,
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
        "phase": "V4-A1.1",
        "status": "LIQUIDITY_FIRST_RETEST_TEST",
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
        "frozen_definition": {
            "structure_timeframe": "1h",
            "execution_timeframe": execution_tf,
            "swing_lb": swing_lb,
            "swing_atr": swing_atr,
            "same_candle_sweep_reclaim": True,
            "min_sweep_depth_atr": min_sweep_depth_atr,
            "opposing_structure_frozen_at_sweep": True,
            "max_bos_bars": max_bos_bars,
            "min_displacement_atr": min_displacement_atr,
            "zone": "swept liquidity pocket between wick extreme and swept swing level",
            "first_retest": "first child-TF touch after validating 1H BOS close",
            "risk": "full liquidity-pocket width",
            "target": f"{rr:.2f}R from proximal edge",
            "rr": rr,
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
            "generator_rejected": rejected,
        },
        "results_sample": results[-sample_limit:] if sample_limit else [],
        "gate": {
            "raw_zone_target": "roughly >=60-65% WR at RR 1:1 with cross-pair consistency before adding absorption",
            "target_strategy": ">=70% WR at RR >=1:1 only after later confirmation stage",
        },
    }
