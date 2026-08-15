"""V4-A1.2 Liquidity-Created Structural Zones.

Same causal liquidity event for every geometry:
  confirmed swing sweep -> same-candle reclaim/rejection -> opposing BOS.

Only the zone geometry changes; event selection is held fixed:
  pocket        : wick extreme <-> swept swing level
  reaction_body : wick extreme <-> far body edge of sweep candle
  reaction_range: full sweep-candle high-low range

This lets us test whether the liquidity thesis failed, or whether the original
pocket was simply too thin for a 5m execution model.
"""

from fastapi import APIRouter, Query
import numpy as np

from v4_structural_zone_endpoint import _load, _atr, _ts, CausalSwingTracker

router = APIRouter(prefix="/v4/liquidity-zone", tags=["v4_liquidity_zone"])
ZONE_MODES = {"pocket", "reaction_body", "reaction_range"}


def _median_prior_volume(V, i, lookback=20):
    lo = max(0, i - lookback)
    xs = V[lo:i]
    if len(xs) == 0:
        return None
    m = float(np.median(xs))
    return m if m > 0 else None


def _geometry(side, event, sweep_i, O, H, L, C, zone_mode):
    liquidity = float(event["liquidity_price"])
    extreme = float(event["sweep_extreme"])
    if zone_mode == "pocket":
        return (extreme, liquidity) if side == "DEMAND" else (liquidity, extreme)
    if zone_mode == "reaction_body":
        if side == "DEMAND":
            return float(L[sweep_i]), max(float(O[sweep_i]), float(C[sweep_i]))
        return min(float(O[sweep_i]), float(C[sweep_i])), float(H[sweep_i])
    if zone_mode == "reaction_range":
        return float(L[sweep_i]), float(H[sweep_i])
    raise ValueError(f"unsupported zone_mode={zone_mode}")


def _zone_from_event(side, event, bos_i, O, H, L, C, V, ATR, T, zone_mode="pocket"):
    a_bos = float(ATR[bos_i]) if ATR[bos_i] > 0 else 1.0
    sweep_i = int(event["sweep_bar"])
    a_sweep = float(ATR[sweep_i]) if ATR[sweep_i] > 0 else 1.0
    liquidity = float(event["liquidity_price"])
    zone_low, zone_high = _geometry(side, event, sweep_i, O, H, L, C, zone_mode)

    if side == "DEMAND":
        sweep_depth_atr = (liquidity - float(event["sweep_extreme"])) / a_sweep
        reclaim_atr = (float(C[sweep_i]) - liquidity) / a_sweep
        bos_distance_atr = (float(C[bos_i]) - float(event["opposing_price"])) / a_bos
        displacement_atr = (float(C[bos_i]) - liquidity) / a_bos
        rng = float(H[sweep_i] - L[sweep_i])
        sweep_close_location = ((float(C[sweep_i]) - float(L[sweep_i])) / rng) if rng > 0 else 0.5
    else:
        sweep_depth_atr = (float(event["sweep_extreme"]) - liquidity) / a_sweep
        reclaim_atr = (liquidity - float(C[sweep_i])) / a_sweep
        bos_distance_atr = (float(event["opposing_price"]) - float(C[bos_i])) / a_bos
        displacement_atr = (liquidity - float(C[bos_i])) / a_bos
        rng = float(H[sweep_i] - L[sweep_i])
        sweep_close_location = ((float(H[sweep_i]) - float(C[sweep_i])) / rng) if rng > 0 else 0.5

    sweep_rng = float(H[sweep_i] - L[sweep_i])
    sweep_body_ratio = abs(float(C[sweep_i] - O[sweep_i])) / sweep_rng if sweep_rng > 0 else 0.0
    prior_vol = _median_prior_volume(V, sweep_i, 20)
    sweep_volume_expansion = float(V[sweep_i]) / prior_vol if prior_vol else None

    return {
        "side": side,
        "zone_mode": zone_mode,
        "zone_id": f"LQ-{zone_mode}-{side[0]}-{T[bos_i]}-{T[sweep_i]}",
        "bos_bar": int(bos_i),
        "bos_time": _ts(T[bos_i]),
        "bos_close": round(float(C[bos_i]), 8),
        "sweep_bar": sweep_i,
        "sweep_time": _ts(T[sweep_i]),
        "sweep_extreme": round(float(event["sweep_extreme"]), 8),
        "sweep_open": round(float(O[sweep_i]), 8),
        "sweep_close": round(float(C[sweep_i]), 8),
        "sweep_high": round(float(H[sweep_i]), 8),
        "sweep_low": round(float(L[sweep_i]), 8),
        "liquidity_swing_bar": int(event["liquidity_bar"]),
        "liquidity_swing_confirmed_at": int(event["liquidity_confirmed_at"]),
        "liquidity_price": round(liquidity, 8),
        "opposing_swing_bar": int(event["opposing_bar"]),
        "opposing_swing_confirmed_at": int(event["opposing_confirmed_at"]),
        "opposing_price": round(float(event["opposing_price"]), 8),
        "zone_low": round(float(zone_low), 8),
        "zone_high": round(float(zone_high), 8),
        "zone_mid": round((float(zone_low) + float(zone_high)) / 2.0, 8),
        "zone_width_atr": round((float(zone_high) - float(zone_low)) / a_sweep, 4),
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
                          min_displacement_atr=1.0, zone_mode="pocket"):
    if zone_mode not in ZONE_MODES:
        raise ValueError(f"zone_mode must be one of {sorted(ZONE_MODES)}")

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

        next_pd = []
        for ev in pending_demand:
            age = i - ev["sweep_bar"]
            if age > max_bos_bars:
                rejected["expired_before_bos"] += 1
                continue
            if float(C[i]) < float(ev["sweep_extreme"]):
                rejected["invalidated_before_bos"] += 1
                continue
            if float(C[i]) > float(ev["opposing_price"]):
                feat = _zone_from_event("DEMAND", ev, i, O, H, L, C, V, ATR, T, zone_mode)
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
            if float(C[i]) < float(ev["opposing_price"]):
                feat = _zone_from_event("SUPPLY", ev, i, O, H, L, C, V, ATR, T, zone_mode)
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

        if sl and sl["confirmed_at"] < i and sl["bar"] not in used_low_bars:
            if float(L[i]) < float(sl["price"]) and float(C[i]) > float(sl["price"]):
                depth = (float(sl["price"]) - float(L[i])) / a
                if depth < min_sweep_depth_atr:
                    rejected["sweep_too_shallow"] += 1
                elif not sh or sh["confirmed_at"] >= i:
                    rejected["no_opposing_structure"] += 1
                else:
                    pending_demand.append({
                        "sweep_bar": i,
                        "sweep_extreme": float(L[i]),
                        "liquidity_bar": sl["bar"],
                        "liquidity_confirmed_at": sl["confirmed_at"],
                        "liquidity_price": float(sl["price"]),
                        "opposing_bar": sh["bar"],
                        "opposing_confirmed_at": sh["confirmed_at"],
                        "opposing_price": float(sh["price"]),
                    })
                    used_low_bars.add(sl["bar"])

        if sh and sh["confirmed_at"] < i and sh["bar"] not in used_high_bars:
            if float(H[i]) > float(sh["price"]) and float(C[i]) < float(sh["price"]):
                depth = (float(H[i]) - float(sh["price"])) / a
                if depth < min_sweep_depth_atr:
                    rejected["sweep_too_shallow"] += 1
                elif not sl or sl["confirmed_at"] >= i:
                    rejected["no_opposing_structure"] += 1
                else:
                    pending_supply.append({
                        "sweep_bar": i,
                        "sweep_extreme": float(H[i]),
                        "liquidity_bar": sh["bar"],
                        "liquidity_confirmed_at": sh["confirmed_at"],
                        "liquidity_price": float(sh["price"]),
                        "opposing_bar": sl["bar"],
                        "opposing_confirmed_at": sl["confirmed_at"],
                        "opposing_price": float(sl["price"]),
                    })
                    used_high_bars.add(sh["bar"])

        same_d = []
        for ev in pending_demand:
            if ev["sweep_bar"] == i and float(C[i]) > float(ev["opposing_price"]):
                feat = _zone_from_event("DEMAND", ev, i, O, H, L, C, V, ATR, T, zone_mode)
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
                feat = _zone_from_event("SUPPLY", ev, i, O, H, L, C, V, ATR, T, zone_mode)
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
    zone_mode: str = Query("pocket"),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    min_sweep_depth_atr: float = Query(0.0, ge=0.0, le=2.0),
    max_bos_bars: int = Query(12, ge=1, le=48),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    sample_limit: int = Query(40, ge=0, le=200),
):
    symbol = symbol.upper().strip()
    zone_mode = zone_mode.lower().strip()
    if zone_mode not in ZONE_MODES:
        return {"error": f"zone_mode must be one of {sorted(ZONE_MODES)}"}
    rows = _load(symbol, "1h", days)
    if len(rows) < max(100, swing_lb * 4 + 20):
        return {"error": f"Not enough 1h data: {len(rows)} rows"}

    T, O, H, L, C, ATR, zones, rejected = build_liquidity_zones(
        rows, swing_lb, swing_atr, min_sweep_depth_atr,
        max_bos_bars, min_displacement_atr, zone_mode,
    )
    demand = [z for z in zones if z["side"] == "DEMAND"]
    supply = [z for z in zones if z["side"] == "SUPPLY"]

    descriptions = {
        "pocket": "wick extreme to swept swing level",
        "reaction_body": "wick extreme to far body edge of sweep candle",
        "reaction_range": "full sweep candle high-low range",
    }
    return {
        "phase": "V4-A1.2",
        "status": "LIQUIDITY_CREATED_ZONE_GENERATION_ONLY",
        "symbol": symbol,
        "requested_days": days,
        "rows": len(rows),
        "data_start": _ts(T[0]),
        "data_end": _ts(T[-1]),
        "definition": {
            "structure_tf": "1h",
            "zone_mode": zone_mode,
            "zone_geometry": descriptions[zone_mode],
            "swing_lb": swing_lb,
            "swing_atr": swing_atr,
            "same_candle_sweep_reclaim": True,
            "min_sweep_depth_atr": min_sweep_depth_atr,
            "max_bos_bars": max_bos_bars,
            "min_displacement_atr": min_displacement_atr,
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
    }
