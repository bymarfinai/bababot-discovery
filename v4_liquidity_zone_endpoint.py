"""V4-A1.1 Liquidity-Created Structural Zones.

Research hypothesis
-------------------
A support/resistance zone is only created after a confirmed liquidity level is
swept and reclaimed/rejected, then price breaks the opposing confirmed
structure within a bounded number of 1H bars.

Demand:
    confirmed swing low -> wick below low -> same-candle close back above low
    -> bullish BOS of the opposing confirmed swing high -> demand zone

Supply is symmetric.

The zone is the swept liquidity pocket itself:
    demand: [sweep wick low, swept swing-low price]
    supply: [swept swing-high price, sweep wick high]

No future retest/outcome is used here. Zone becomes known only when BOS closes.
"""

from fastapi import APIRouter, Query
import numpy as np

from v4_structural_zone_endpoint import _load, _atr, _ts, CausalSwingTracker

router = APIRouter(prefix="/v4/liquidity-zone", tags=["v4_liquidity_zone"])


def _median_prior_volume(V, i, lookback=20):
    lo = max(0, i - lookback)
    xs = V[lo:i]
    if len(xs) == 0:
        return None
    m = float(np.median(xs))
    return m if m > 0 else None


def _zone_from_event(side, event, bos_i, O, H, L, C, V, ATR, T):
    a_bos = float(ATR[bos_i]) if ATR[bos_i] > 0 else 1.0
    sweep_i = int(event["sweep_bar"])
    a_sweep = float(ATR[sweep_i]) if ATR[sweep_i] > 0 else 1.0

    if side == "DEMAND":
        zone_low = float(event["sweep_extreme"])
        zone_high = float(event["liquidity_price"])
        sweep_depth_atr = (zone_high - zone_low) / a_sweep
        reclaim_atr = (float(C[sweep_i]) - zone_high) / a_sweep
        bos_distance_atr = (float(C[bos_i]) - float(event["opposing_price"])) / a_bos
        displacement_atr = (float(C[bos_i]) - zone_high) / a_bos
        rng = float(H[sweep_i] - L[sweep_i])
        sweep_close_location = ((float(C[sweep_i]) - float(L[sweep_i])) / rng) if rng > 0 else 0.5
    else:
        zone_low = float(event["liquidity_price"])
        zone_high = float(event["sweep_extreme"])
        sweep_depth_atr = (zone_high - zone_low) / a_sweep
        reclaim_atr = (zone_low - float(C[sweep_i])) / a_sweep
        bos_distance_atr = (float(event["opposing_price"]) - float(C[bos_i])) / a_bos
        displacement_atr = (zone_low - float(C[bos_i])) / a_bos
        rng = float(H[sweep_i] - L[sweep_i])
        sweep_close_location = ((float(H[sweep_i]) - float(C[sweep_i])) / rng) if rng > 0 else 0.5

    sweep_rng = float(H[sweep_i] - L[sweep_i])
    sweep_body_ratio = abs(float(C[sweep_i] - O[sweep_i])) / sweep_rng if sweep_rng > 0 else 0.0
    prior_vol = _median_prior_volume(V, sweep_i, 20)
    sweep_volume_expansion = float(V[sweep_i]) / prior_vol if prior_vol else None

    return {
        "side": side,
        "zone_id": f"LQ-{side[0]}-{T[bos_i]}-{T[sweep_i]}",
        "bos_bar": int(bos_i),
        "bos_time": _ts(T[bos_i]),
        "bos_close": round(float(C[bos_i]), 8),
        "sweep_bar": sweep_i,
        "sweep_time": _ts(T[sweep_i]),
        "sweep_extreme": round(float(event["sweep_extreme"]), 8),
        "liquidity_swing_bar": int(event["liquidity_bar"]),
        "liquidity_swing_confirmed_at": int(event["liquidity_confirmed_at"]),
        "liquidity_price": round(float(event["liquidity_price"]), 8),
        "opposing_swing_bar": int(event["opposing_bar"]),
        "opposing_swing_confirmed_at": int(event["opposing_confirmed_at"]),
        "opposing_price": round(float(event["opposing_price"]), 8),
        "zone_low": round(zone_low, 8),
        "zone_high": round(zone_high, 8),
        "zone_mid": round((zone_low + zone_high) / 2.0, 8),
        "zone_width_atr": round((zone_high - zone_low) / a_sweep, 4),
        "sweep_depth_atr": round(float(sweep_depth_atr), 4),
        "sweep_reclaim_atr": round(float(reclaim_atr), 4),
        "sweep_body_ratio": round(float(sweep_body_ratio), 4),
        "sweep_close_location": round(float(sweep_close_location), 4),
        "sweep_volume_expansion": round(float(sweep_volume_expansion), 4) if sweep_volume_expansion is not None else None,
        "bars_sweep_to_bos": int(bos_i - sweep_i),
        "bos_distance_atr": round(float(bos_distance_atr), 4),
        "displacement_atr": round(float(displacement_atr), 4),
        "atr_sweep": round(a_sweep, 8),
        "atr_bos": round(a_bos, 8),
    }


def build_liquidity_zones(rows, swing_lb=10, swing_atr=0.5,
                          min_sweep_depth_atr=0.0, max_bos_bars=12,
                          min_displacement_atr=1.0):
    T = [int(r[0]) for r in rows]
    O = np.asarray([r[1] for r in rows], dtype=float)
    H = np.asarray([r[2] for r in rows], dtype=float)
    L = np.asarray([r[3] for r in rows], dtype=float)
    C = np.asarray([r[4] for r in rows], dtype=float)
    V = np.asarray([r[5] for r in rows], dtype=float)
    ATR = _atr(H, L, C, 14)

    tracker = CausalSwingTracker(swing_lb, swing_atr)
    zones = []
    pending_demand = []
    pending_supply = []
    used_low_bars = set()
    used_high_bars = set()
    rejected = {
        "no_opposing_structure": 0,
        "sweep_too_shallow": 0,
        "expired_before_bos": 0,
        "invalidated_before_bos": 0,
        "displacement_below_threshold": 0,
    }

    for i in range(len(rows)):
        tracker.update(i, H, L, ATR)
        if ATR[i] <= 0:
            continue

        # Resolve previously created demand events causally on the current close.
        next_pd = []
        for ev in pending_demand:
            age = i - ev["sweep_bar"]
            if age > max_bos_bars:
                rejected["expired_before_bos"] += 1
                continue
            if float(C[i]) < float(ev["sweep_extreme"]):
                rejected["invalidated_before_bos"] += 1
                continue
            crossed = float(C[i]) > float(ev["opposing_price"])
            if crossed:
                feat = _zone_from_event("DEMAND", ev, i, O, H, L, C, V, ATR, T)
                if feat["displacement_atr"] >= min_displacement_atr:
                    zones.append(feat)
                else:
                    rejected["displacement_below_threshold"] += 1
                continue
            next_pd.append(ev)
        pending_demand = next_pd

        next_ps = []
        for ev in pending_supply:
            age = i - ev["sweep_bar"]
            if age > max_bos_bars:
                rejected["expired_before_bos"] += 1
                continue
            if float(C[i]) > float(ev["sweep_extreme"]):
                rejected["invalidated_before_bos"] += 1
                continue
            crossed = float(C[i]) < float(ev["opposing_price"])
            if crossed:
                feat = _zone_from_event("SUPPLY", ev, i, O, H, L, C, V, ATR, T)
                if feat["displacement_atr"] >= min_displacement_atr:
                    zones.append(feat)
                else:
                    rejected["displacement_below_threshold"] += 1
                continue
            next_ps.append(ev)
        pending_supply = next_ps

        if i < 1:
            continue
        a = float(ATR[i])
        sl = tracker.last_low
        sh = tracker.last_high

        # Demand liquidity sweep: low trades below confirmed swing low, but the
        # same 1H candle closes back above it. Opposing high must already be
        # confirmed at sweep time; later swings are never substituted.
        if sl and sl["confirmed_at"] < i and sl["bar"] not in used_low_bars:
            if float(L[i]) < float(sl["price"]) and float(C[i]) > float(sl["price"]):
                depth = (float(sl["price"]) - float(L[i])) / a
                if depth < min_sweep_depth_atr:
                    rejected["sweep_too_shallow"] += 1
                elif not sh or sh["confirmed_at"] >= i:
                    rejected["no_opposing_structure"] += 1
                else:
                    ev = {
                        "sweep_bar": i,
                        "sweep_extreme": float(L[i]),
                        "liquidity_bar": sl["bar"],
                        "liquidity_confirmed_at": sl["confirmed_at"],
                        "liquidity_price": float(sl["price"]),
                        "opposing_bar": sh["bar"],
                        "opposing_confirmed_at": sh["confirmed_at"],
                        "opposing_price": float(sh["price"]),
                    }
                    pending_demand.append(ev)
                    used_low_bars.add(sl["bar"])

        # Supply is symmetric.
        if sh and sh["confirmed_at"] < i and sh["bar"] not in used_high_bars:
            if float(H[i]) > float(sh["price"]) and float(C[i]) < float(sh["price"]):
                depth = (float(H[i]) - float(sh["price"])) / a
                if depth < min_sweep_depth_atr:
                    rejected["sweep_too_shallow"] += 1
                elif not sl or sl["confirmed_at"] >= i:
                    rejected["no_opposing_structure"] += 1
                else:
                    ev = {
                        "sweep_bar": i,
                        "sweep_extreme": float(H[i]),
                        "liquidity_bar": sh["bar"],
                        "liquidity_confirmed_at": sh["confirmed_at"],
                        "liquidity_price": float(sh["price"]),
                        "opposing_bar": sl["bar"],
                        "opposing_confirmed_at": sl["confirmed_at"],
                        "opposing_price": float(sl["price"]),
                    }
                    pending_supply.append(ev)
                    used_high_bars.add(sh["bar"])

        # Allow a very strong sweep candle to complete BOS on the same 1H bar.
        # The opposing swing was already known before this candle, so causality
        # is preserved. This block only examines events created on i.
        same_d = []
        for ev in pending_demand:
            if ev["sweep_bar"] == i and float(C[i]) > float(ev["opposing_price"]):
                feat = _zone_from_event("DEMAND", ev, i, O, H, L, C, V, ATR, T)
                if feat["displacement_atr"] >= min_displacement_atr:
                    zones.append(feat)
                else:
                    rejected["displacement_below_threshold"] += 1
            else:
                same_d.append(ev)
        pending_demand = same_d

        same_s = []
        for ev in pending_supply:
            if ev["sweep_bar"] == i and float(C[i]) < float(ev["opposing_price"]):
                feat = _zone_from_event("SUPPLY", ev, i, O, H, L, C, V, ATR, T)
                if feat["displacement_atr"] >= min_displacement_atr:
                    zones.append(feat)
                else:
                    rejected["displacement_below_threshold"] += 1
            else:
                same_s.append(ev)
        pending_supply = same_s

    return T, O, H, L, C, ATR, zones, rejected


@router.get("/generate")
def generate_liquidity_zones(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    min_sweep_depth_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_bos_bars: int = Query(12, ge=1, le=48),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    sample_limit: int = Query(40, ge=0, le=200),
):
    symbol = symbol.upper().strip()
    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + 20):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones, rejected = build_liquidity_zones(
        rows, swing_lb, swing_atr, min_sweep_depth_atr,
        max_bos_bars, min_displacement_atr,
    )
    demand = [z for z in zones if z["side"] == "DEMAND"]
    supply = [z for z in zones if z["side"] == "SUPPLY"]

    return {
        "phase": "V4-A1.1",
        "status": "LIQUIDITY_CREATED_ZONE_GENERATION_ONLY",
        "symbol": symbol,
        "requested_days": days,
        "rows": len(rows),
        "data_start": _ts(T[0]),
        "data_end": _ts(T[-1]),
        "definition": {
            "structure_tf": "1h",
            "swing_lb": swing_lb,
            "swing_atr": swing_atr,
            "same_candle_sweep_reclaim": True,
            "min_sweep_depth_atr": min_sweep_depth_atr,
            "max_bos_bars": max_bos_bars,
            "min_displacement_atr": min_displacement_atr,
            "demand_zone": "[sweep wick low, swept confirmed swing-low price]",
            "supply_zone": "[swept confirmed swing-high price, sweep wick high]",
            "opposing_structure_frozen_at_sweep": True,
            "future_retest_used": False,
            "regime_gate": False,
            "absorption_filter": False,
        },
        "zone_count": len(zones),
        "demand_count": len(demand),
        "supply_count": len(supply),
        "rejected": rejected,
        "zones_sample": zones[-sample_limit:] if sample_limit else [],
        "next": "Evaluate first future 5m retest at RR 1:1 before any extra filter.",
    }
