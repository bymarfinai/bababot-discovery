"""V4-A1 Structural Zone Generator — causal support/resistance research.

Purpose
-------
Generate demand/supply zones from a structural event, without entry logic,
forward outcome labels, absorption, or live-trading integration.

Flow:
    confirmed causal swing -> BOS close -> displacement -> pre-break base zone

GET /v4/structural-zone/generate?symbol=BTCUSDT&days=120

V4-A1 is deliberately only a zone-generation / feature-inventory phase.
First-retest BOUNCE/BREAK labels belong to V4-A2.
"""

import os
import sqlite3
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Query

router = APIRouter(prefix="/v4/structural-zone", tags=["v4_structural_zone"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _load(symbol: str, timeframe: str, days: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        start_ms = now_ms - days * 86_400_000
        cur = conn.cursor()
        cur.execute(
            """
            SELECT open_time, open, high, low, close, volume
            FROM klines
            WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, timeframe, start_ms, now_ms),
        )
        return cur.fetchall()
    finally:
        conn.close()


def _atr(high, low, close, period=14):
    n = len(close)
    out = np.zeros(n, dtype=float)
    if n < 2:
        return out
    for i in range(1, n):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        if i < period:
            out[i] = (out[i - 1] * (i - 1) + tr) / i
        else:
            out[i] = out[i - 1] + (tr - out[i - 1]) / period
    return out


def _pctile(values, q):
    if not values:
        return None
    return round(float(np.percentile(np.asarray(values, dtype=float), q)), 4)


def _summary(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not vals:
        return {"n": 0, "p25": None, "median": None, "p75": None}
    return {
        "n": len(vals),
        "p25": _pctile(vals, 25),
        "median": _pctile(vals, 50),
        "p75": _pctile(vals, 75),
    }


class CausalSwingTracker:
    """Swing is only visible after `lookback` future bars have completed.

    At processing bar i, the candidate is i-lookback. Therefore no bar after i
    is inspected and the swing can only be used from its confirmation time on.
    """

    def __init__(self, lookback=10, min_atr_mult=0.5):
        self.lb = int(lookback)
        self.min_atr = float(min_atr_mult)
        self.confirmed_highs = []
        self.confirmed_lows = []

    def update(self, i, high, low, atr):
        cand = i - self.lb
        if cand < self.lb:
            return

        left = max(0, cand - self.lb)
        right = min(i + 1, cand + self.lb + 1)  # right edge <= current bar i
        atr_val = atr[cand] if atr[cand] > 0 else 1.0
        min_sig = self.min_atr * atr_val

        is_high = all(high[k] <= high[cand] for k in range(left, right) if k != cand)
        if is_high:
            local_low = float(np.min(low[left:right]))
            if high[cand] - local_low >= min_sig:
                if not self.confirmed_highs or self.confirmed_highs[-1]["bar"] != cand:
                    self.confirmed_highs.append(
                        {"confirmed_at": i, "bar": cand, "price": float(high[cand])}
                    )

        is_low = all(low[k] >= low[cand] for k in range(left, right) if k != cand)
        if is_low:
            local_high = float(np.max(high[left:right]))
            if local_high - low[cand] >= min_sig:
                if not self.confirmed_lows or self.confirmed_lows[-1]["bar"] != cand:
                    self.confirmed_lows.append(
                        {"confirmed_at": i, "bar": cand, "price": float(low[cand])}
                    )

    @property
    def last_high(self):
        return self.confirmed_highs[-1] if self.confirmed_highs else None

    @property
    def last_low(self):
        return self.confirmed_lows[-1] if self.confirmed_lows else None


def _compression_base(high, low, atr, bos_i, search_bars, base_bars):
    """Find the tightest completed base window immediately before BOS.

    All candidate windows end before bos_i. The search is deterministic and
    causal. We intentionally do NOT hard-filter compression in V4-A1; its ATR
    width is retained as a feature for V4-A3 instead of tuning it now.
    """
    latest_end = bos_i - 1
    earliest_start = max(0, bos_i - search_bars)
    if latest_end - earliest_start + 1 < base_bars:
        return None

    candidates = []
    for start in range(earliest_start, latest_end - base_bars + 2):
        end = start + base_bars - 1
        if end >= bos_i:
            continue
        a = float(atr[end])
        if a <= 0:
            continue
        z_low = float(np.min(low[start : end + 1]))
        z_high = float(np.max(high[start : end + 1]))
        width_atr = (z_high - z_low) / a
        # Tightest base wins; latest wins exact/near ties.
        candidates.append((width_atr, -end, start, end, z_low, z_high))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]))
    width_atr, _, start, end, z_low, z_high = candidates[0]
    return {
        "start": start,
        "end": end,
        "low": z_low,
        "high": z_high,
        "width_atr": float(width_atr),
    }


def _ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _zone_features(
    side,
    i,
    swing,
    base,
    O,
    H,
    L,
    C,
    V,
    ATR,
    T,
):
    a = float(ATR[i]) if ATR[i] > 0 else 1.0
    rng = float(H[i] - L[i])
    body_ratio = abs(float(C[i] - O[i])) / rng if rng > 0 else 0.0
    if side == "DEMAND":
        bos_distance_atr = (float(C[i]) - swing["price"]) / a
        displacement_atr = (float(C[i]) - base["high"]) / a
        close_location = (float(C[i]) - float(L[i])) / rng if rng > 0 else 0.5
    else:
        bos_distance_atr = (swing["price"] - float(C[i])) / a
        displacement_atr = (base["low"] - float(C[i])) / a
        close_location = (float(H[i]) - float(C[i])) / rng if rng > 0 else 0.5

    base_vol = float(np.median(V[base["start"] : base["end"] + 1]))
    vol_expansion = float(V[i]) / base_vol if base_vol > 0 else None

    return {
        "side": side,
        "bos_bar": i,
        "bos_time": _ts(T[i]),
        "bos_close": round(float(C[i]), 8),
        "broken_swing_bar": swing["bar"],
        "broken_swing_confirmed_at": swing["confirmed_at"],
        "broken_swing_time": _ts(T[swing["bar"]]),
        "broken_swing_price": round(float(swing["price"]), 8),
        "zone_start_bar": base["start"],
        "zone_end_bar": base["end"],
        "zone_start_time": _ts(T[base["start"]]),
        "zone_end_time": _ts(T[base["end"]]),
        "zone_low": round(float(base["low"]), 8),
        "zone_high": round(float(base["high"]), 8),
        "zone_mid": round((float(base["low"]) + float(base["high"])) / 2.0, 8),
        "zone_width_atr": round(float(base["width_atr"]), 4),
        "base_to_bos_bars": int(i - base["end"]),
        "bos_distance_atr": round(float(bos_distance_atr), 4),
        "displacement_atr": round(float(displacement_atr), 4),
        "bos_body_ratio": round(float(body_ratio), 4),
        "bos_close_location": round(float(close_location), 4),
        "volume_expansion": round(float(vol_expansion), 4) if vol_expansion is not None else None,
        "atr": round(a, 8),
    }


@router.get("/generate")
def generate_structural_zones(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(120, ge=30, le=1500),
    timeframe: str = Query("1h"),
    swing_lb: int = Query(10, ge=3, le=30),
    swing_atr: float = Query(0.5, ge=0.0, le=3.0),
    base_bars: int = Query(3, ge=2, le=5),
    base_search: int = Query(8, ge=4, le=20),
    min_displacement_atr: float = Query(1.0, ge=0.0, le=5.0),
    bos_buffer_atr: float = Query(0.0, ge=0.0, le=2.0),
    sample_limit: int = Query(40, ge=0, le=200),
):
    """Generate V4-A1 candidate structural zones.

    Demand zone:
      - a swing high was confirmed causally before this bar;
      - previous close was not above it;
      - current close breaks above it (+ optional ATR buffer);
      - the pre-break base to BOS close displacement meets threshold.

    Supply is exactly symmetric.

    No future candle is consulted after the BOS bar. No retest or trade result
    is evaluated here; this is intentional to keep V4-A1 scientifically clean.
    """
    symbol = symbol.upper().strip()
    if timeframe not in {"1h", "4h", "15m"}:
        return {"error": "timeframe must be one of 15m, 1h, 4h"}

    rows = _load(symbol, timeframe, days)
    if len(rows) < max(80, swing_lb * 4 + base_search + 10):
        return {"error": f"Not enough {timeframe} data: {len(rows)} rows"}

    T = [int(r[0]) for r in rows]
    O = np.asarray([r[1] for r in rows], dtype=float)
    H = np.asarray([r[2] for r in rows], dtype=float)
    L = np.asarray([r[3] for r in rows], dtype=float)
    C = np.asarray([r[4] for r in rows], dtype=float)
    V = np.asarray([r[5] for r in rows], dtype=float)
    ATR = _atr(H, L, C, 14)

    tracker = CausalSwingTracker(swing_lb, swing_atr)
    zones = []
    rejected = {
        "no_base": 0,
        "displacement_below_threshold": 0,
        "bos_buffer_not_met": 0,
    }
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
            crossed = prev_close <= sh["price"] and close > threshold
            if crossed:
                base = _compression_base(H, L, ATR, i, base_search, base_bars)
                if base is None:
                    rejected["no_base"] += 1
                else:
                    feat = _zone_features("DEMAND", i, sh, base, O, H, L, C, V, ATR, T)
                    if feat["displacement_atr"] >= min_displacement_atr:
                        feat["zone_id"] = f"{symbol}-D-{T[i]}"
                        zones.append(feat)
                        used_high_bars.add(sh["bar"])
                    else:
                        rejected["displacement_below_threshold"] += 1

        sl = tracker.last_low
        if sl and sl["confirmed_at"] < i and sl["bar"] not in used_low_bars:
            threshold = sl["price"] - bos_buffer_atr * a
            crossed = prev_close >= sl["price"] and close < threshold
            if crossed:
                base = _compression_base(H, L, ATR, i, base_search, base_bars)
                if base is None:
                    rejected["no_base"] += 1
                else:
                    feat = _zone_features("SUPPLY", i, sl, base, O, H, L, C, V, ATR, T)
                    if feat["displacement_atr"] >= min_displacement_atr:
                        feat["zone_id"] = f"{symbol}-S-{T[i]}"
                        zones.append(feat)
                        used_low_bars.add(sl["bar"])
                    else:
                        rejected["displacement_below_threshold"] += 1

    demand = [z for z in zones if z["side"] == "DEMAND"]
    supply = [z for z in zones if z["side"] == "SUPPLY"]

    feature_summary = {
        "zone_width_atr": _summary([z["zone_width_atr"] for z in zones]),
        "displacement_atr": _summary([z["displacement_atr"] for z in zones]),
        "bos_distance_atr": _summary([z["bos_distance_atr"] for z in zones]),
        "bos_body_ratio": _summary([z["bos_body_ratio"] for z in zones]),
        "bos_close_location": _summary([z["bos_close_location"] for z in zones]),
        "volume_expansion": _summary([z["volume_expansion"] for z in zones]),
        "base_to_bos_bars": _summary([z["base_to_bos_bars"] for z in zones]),
    }

    sample = zones[-sample_limit:] if sample_limit else []
    return {
        "phase": "V4-A1",
        "status": "ZONE_GENERATION_ONLY",
        "symbol": symbol,
        "timeframe": timeframe,
        "requested_days": days,
        "rows": len(rows),
        "data_start": _ts(T[0]),
        "data_end": _ts(T[-1]),
        "causality": {
            "swing_confirmation_delay_bars": swing_lb,
            "future_bars_used_after_bos": 0,
            "forward_outcome_label": False,
            "absorption_filter": False,
            "regime_gate": False,
            "live_trading_changes": False,
        },
        "definition": {
            "event": "confirmed causal swing broken by close",
            "zone": f"tightest {base_bars}-bar compression base within prior {base_search} completed bars",
            "displacement": "distance from zone proximal edge to BOS close, normalized by ATR14",
            "deduplication": "one accepted BOS zone per broken confirmed swing",
        },
        "params": {
            "swing_lb": swing_lb,
            "swing_atr": swing_atr,
            "base_bars": base_bars,
            "base_search": base_search,
            "min_displacement_atr": min_displacement_atr,
            "bos_buffer_atr": bos_buffer_atr,
        },
        "counts": {
            "total": len(zones),
            "demand": len(demand),
            "supply": len(supply),
        },
        "rejected": rejected,
        "feature_summary": feature_summary,
        "zones_sample": sample,
        "next_phase": "V4-A2 first-retest BOUNCE/BREAK 1R labeling; not implemented in this endpoint",
    }
