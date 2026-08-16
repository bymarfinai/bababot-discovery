"""BTC temporal discovery — weekday x hour causal scan.

Purpose
-------
Discover recurring BTC directional edges by local weekday/hour without touching
live trading. This is a discovery endpoint, not a production strategy.

Frozen baseline:
- BTCUSDT only
- 15m completed Binance Futures candles from the existing Railway DB
- entry = open of the exact local clock-hour (marketable at that timestamp)
- horizons = 15m, 30m, 60m, 120m, 240m
- all 7 x 24 = 168 weekday/hour slots scanned
- BUY/SELL direction is selected from the observed sign of forward return
- MFE/MAE is measured inside the same forward horizon
- stability is reported over 8 chronological blocks
- no EMA, regime, HOD/LOD, session, or other price-action filters

The endpoint intentionally returns both raw-WR and stability-first leaderboards.
That lets research search for the strongest edge while still seeing whether it
repeats through time.
"""

import math
import os
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

router = APIRouter(prefix="/research/btc-temporal", tags=["btc_temporal_discovery"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

TF_MS = 15 * 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000
HORIZONS = (15, 30, 60, 120, 240)
HORIZON_BARS = {m: m // 15 for m in HORIZONS}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
THRESHOLDS_PCT = (0.3, 0.5, 0.8, 1.0)


def _median(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.median(vals)) if vals else None


def _mean(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.mean(vals)) if vals else None


def _round(x, n=4):
    return round(float(x), n) if x is not None and math.isfinite(float(x)) else None


def _load_15m(symbol: str, days: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        max_ts = cur.execute(
            "SELECT MAX(open_time) FROM klines WHERE symbol=? AND timeframe='15m'",
            (symbol,),
        ).fetchone()[0]
        if max_ts is None:
            return [], None, None
        end_ms = int(max_ts) + TF_MS
        start_ms = end_ms - int(days * DAY_MS)
        rows = cur.execute(
            """
            SELECT open_time, open, high, low, close
            FROM klines
            WHERE symbol=? AND timeframe='15m'
              AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, start_ms, end_ms),
        ).fetchall()
        return rows, start_ms, end_ms
    finally:
        conn.close()


def _first_touch(path, entry: float, direction: int, threshold_pct: float):
    """15m-bar first-touch approximation; same-bar TP+SL is AMBIGUOUS."""
    fav = entry * (1.0 + direction * threshold_pct / 100.0)
    adv = entry * (1.0 - direction * threshold_pct / 100.0)
    for r in path:
        hi = float(r[2]); lo = float(r[3])
        if direction > 0:
            hit_f = hi >= fav
            hit_a = lo <= adv
        else:
            hit_f = lo <= fav
            hit_a = hi >= adv
        if hit_f and hit_a:
            return "AMBIGUOUS"
        if hit_f:
            return "FAVORABLE"
        if hit_a:
            return "ADVERSE"
    return "NONE"


def _event_metrics(events, direction: int, blocks: int):
    if not events:
        return None

    signed_returns = [direction * e["ret_pct"] for e in events]
    wins = sum(x > 0 for x in signed_returns)
    losses = sum(x < 0 for x in signed_returns)
    flats = len(events) - wins - losses
    resolved = wins + losses

    mfe = []
    mae = []
    for e in events:
        entry = e["entry"]
        if direction > 0:
            mfe.append(100.0 * (e["max_high"] - entry) / entry)
            mae.append(100.0 * (entry - e["min_low"]) / entry)
        else:
            mfe.append(100.0 * (entry - e["min_low"]) / entry)
            mae.append(100.0 * (e["max_high"] - entry) / entry)

    med_mfe = _median(mfe)
    med_mae = _median(mae)
    block_stats = []
    for b in range(blocks):
        xs = [direction * e["ret_pct"] for e in events if e["block"] == b]
        bw = sum(x > 0 for x in xs)
        bl = sum(x < 0 for x in xs)
        br = bw + bl
        block_stats.append({
            "block": b + 1,
            "n": len(xs),
            "resolved": br,
            "wr_pct": _round(100.0 * bw / br, 2) if br else None,
            "avg_signed_return_pct": _round(_mean(xs), 4),
        })

    wrs = [x["wr_pct"] for x in block_stats if x["wr_pct"] is not None]
    positive_blocks = sum(x > 50.0 for x in wrs)
    strong_blocks = sum(x >= 60.0 for x in wrs)
    very_strong_blocks = sum(x >= 65.0 for x in wrs)

    ft = {}
    for threshold in THRESHOLDS_PCT:
        counts = defaultdict(int)
        for e in events:
            counts[_first_touch(e["path"], e["entry"], direction, threshold)] += 1
        decisive = counts["FAVORABLE"] + counts["ADVERSE"]
        ft[str(threshold)] = {
            "favorable": counts["FAVORABLE"],
            "adverse": counts["ADVERSE"],
            "ambiguous": counts["AMBIGUOUS"],
            "none": counts["NONE"],
            "decisive_wr_pct": _round(100.0 * counts["FAVORABLE"] / decisive, 2) if decisive else None,
        }

    return {
        "n": len(events),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "wr_pct": _round(100.0 * wins / resolved, 2) if resolved else None,
        "avg_signed_return_pct": _round(_mean(signed_returns), 4),
        "median_signed_return_pct": _round(_median(signed_returns), 4),
        "median_mfe_pct": _round(med_mfe, 4),
        "median_mae_pct": _round(med_mae, 4),
        "mfe_mae_ratio": _round(med_mfe / med_mae, 4) if med_mfe is not None and med_mae and med_mae > 0 else None,
        "positive_blocks_gt50": positive_blocks,
        "strong_blocks_ge60": strong_blocks,
        "very_strong_blocks_ge65": very_strong_blocks,
        "median_block_wr_pct": _round(_median(wrs), 2),
        "min_block_wr_pct": _round(min(wrs), 2) if wrs else None,
        "max_block_wr_pct": _round(max(wrs), 2) if wrs else None,
        "blocks": block_stats,
        "first_touch_symmetric_pct": ft,
    }


def _compact(r):
    return {
        "weekday": r["weekday"],
        "hour_local": r["hour_local"],
        "slot": r["slot"],
        "direction": r["direction"],
        "horizon_min": r["horizon_min"],
        "n": r["n"],
        "wr_pct": r["wr_pct"],
        "avg_signed_return_pct": r["avg_signed_return_pct"],
        "median_signed_return_pct": r["median_signed_return_pct"],
        "median_mfe_pct": r["median_mfe_pct"],
        "median_mae_pct": r["median_mae_pct"],
        "mfe_mae_ratio": r["mfe_mae_ratio"],
        "positive_blocks_gt50": r["positive_blocks_gt50"],
        "strong_blocks_ge60": r["strong_blocks_ge60"],
        "very_strong_blocks_ge65": r["very_strong_blocks_ge65"],
        "median_block_wr_pct": r["median_block_wr_pct"],
        "min_block_wr_pct": r["min_block_wr_pct"],
        "first_touch_symmetric_pct": r["first_touch_symmetric_pct"],
    }


@router.get("")
def btc_temporal_discovery(
    days: int = Query(971, ge=240, le=1500),
    tz_offset_hours: int = Query(7, ge=-12, le=14),
    blocks: int = Query(8, ge=4, le=12),
    top_n: int = Query(30, ge=5, le=168),
    min_n: int = Query(80, ge=20, le=250),
):
    symbol = "BTCUSDT"
    rows, start_ms, end_ms = _load_15m(symbol, days)
    if not rows or start_ms is None or end_ms is None:
        return {"error": "No BTCUSDT 15m data in DB"}

    expected = max(1, int((end_ms - start_ms) / TF_MS))
    coverage_pct = 100.0 * len(rows) / expected
    by_ts = {int(r[0]): r for r in rows}
    tz = timezone(timedelta(hours=tz_offset_hours))
    span = max(1, end_ms - start_ms)

    # slot -> horizon -> list[event]
    events = defaultdict(lambda: defaultdict(list))
    missing_forward = 0

    for r in rows:
        ts = int(r[0])
        dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).astimezone(tz)
        if dt.minute != 0:
            continue
        block = min(blocks - 1, max(0, int((ts - start_ms) * blocks / span)))
        slot = (dt.weekday(), dt.hour)
        entry = float(r[1])
        if entry <= 0:
            continue

        for horizon in HORIZONS:
            hbars = HORIZON_BARS[horizon]
            path = []
            ok = True
            for k in range(hbars):
                rr = by_ts.get(ts + k * TF_MS)
                if rr is None:
                    ok = False
                    break
                path.append(rr)
            if not ok:
                missing_forward += 1
                continue
            final_close = float(path[-1][4])
            max_high = max(float(x[2]) for x in path)
            min_low = min(float(x[3]) for x in path)
            events[slot][horizon].append({
                "ts": ts,
                "block": block,
                "entry": entry,
                "ret_pct": 100.0 * (final_close - entry) / entry,
                "max_high": max_high,
                "min_low": min_low,
                "path": path,
            })

    all_candidates = []
    per_slot = {}
    for wd in range(7):
        for hour in range(24):
            slot_key = (wd, hour)
            slot_name = f"{WEEKDAYS[wd]} {hour:02d}:00"
            horizon_rows = []
            for horizon in HORIZONS:
                xs = events.get(slot_key, {}).get(horizon, [])
                if len(xs) < min_n:
                    continue
                up = sum(e["ret_pct"] > 0 for e in xs)
                down = sum(e["ret_pct"] < 0 for e in xs)
                direction = 1 if up >= down else -1
                m = _event_metrics(xs, direction, blocks)
                if not m:
                    continue
                rec = {
                    "weekday": WEEKDAYS[wd],
                    "weekday_index_monday0": wd,
                    "hour_local": hour,
                    "slot": slot_name,
                    "direction": "BUY" if direction > 0 else "SELL",
                    "horizon_min": horizon,
                    **m,
                }
                horizon_rows.append(rec)
                all_candidates.append(rec)

            if horizon_rows:
                # Stability-first best horizon for this slot. WR remains the final tie-breaker.
                best = sorted(
                    horizon_rows,
                    key=lambda x: (
                        x["very_strong_blocks_ge65"],
                        x["strong_blocks_ge60"],
                        x["positive_blocks_gt50"],
                        x["median_block_wr_pct"] if x["median_block_wr_pct"] is not None else -1,
                        x["wr_pct"] if x["wr_pct"] is not None else -1,
                        x["mfe_mae_ratio"] if x["mfe_mae_ratio"] is not None else -1,
                    ),
                    reverse=True,
                )[0]
                per_slot[slot_name] = {
                    "best_horizon": _compact(best),
                    "all_horizons": [_compact(x) for x in horizon_rows],
                }

    raw_wr = sorted(
        all_candidates,
        key=lambda x: (
            x["wr_pct"] if x["wr_pct"] is not None else -1,
            x["median_block_wr_pct"] if x["median_block_wr_pct"] is not None else -1,
            x["n"],
        ),
        reverse=True,
    )[:top_n]

    # One entry per weekday/hour, so neighboring horizons do not occupy the whole leaderboard.
    slot_bests = [v["best_horizon"] for v in per_slot.values()]
    robust = sorted(
        slot_bests,
        key=lambda x: (
            x["very_strong_blocks_ge65"],
            x["strong_blocks_ge60"],
            x["positive_blocks_gt50"],
            x["median_block_wr_pct"] if x["median_block_wr_pct"] is not None else -1,
            x["wr_pct"] if x["wr_pct"] is not None else -1,
            x["mfe_mae_ratio"] if x["mfe_mae_ratio"] is not None else -1,
        ),
        reverse=True,
    )[:top_n]

    tracked = {}
    for name in ("Sunday 23:00", "Sunday 01:00", "Tuesday 01:00", "Tuesday 20:00", "Thursday 09:00", "Friday 09:00"):
        if name in per_slot:
            tracked[name] = per_slot[name]

    return {
        "phase": "A1",
        "status": "BTC_WEEKDAY_HOUR_FULL_DISCOVERY",
        "symbol": symbol,
        "definition": {
            "timezone_offset_hours": tz_offset_hours,
            "timezone_label": "WIB" if tz_offset_hours == 7 else f"UTC{tz_offset_hours:+d}",
            "entry": "open of exact local clock-hour 15m candle",
            "horizons_min": list(HORIZONS),
            "direction_selection": "BUY if positive forward returns >= negative; otherwise SELL",
            "mfe_mae": "within the same forward horizon from entry price",
            "stability_blocks": blocks,
            "filters": "none; pure temporal discovery",
            "live_trading_changes": False,
        },
        "data": {
            "requested_days": days,
            "rows_15m": len(rows),
            "expected_rows_15m": expected,
            "coverage_pct": _round(coverage_pct, 3),
            "start_utc": datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).isoformat(),
            "end_utc_exclusive": datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc).isoformat(),
            "missing_forward_windows": missing_forward,
        },
        "acceptance_context": {
            "research_intent": "find the strongest repeatable temporal BTC edge, then deepen winners",
            "raw_wr_is_discovery_not_final_strategy": True,
            "next_phase": "A2 zoom into top slots by minute/15m entry timing and causal context",
        },
        "leaderboard_stability_first": robust,
        "leaderboard_raw_wr": [_compact(x) for x in raw_wr],
        "tracked_candidates": tracked,
        "slot_count_evaluated": len(per_slot),
    }
