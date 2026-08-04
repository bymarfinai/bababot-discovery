"""
Causal EMA7 sniper backtest.

This endpoint tests sequential 15m break/reclaim patterns against the
previous completed 1H EMA7. Entries are scheduled at the next 15m candle
open, so no entry is booked at a price that was known only after the
confirmation candle closed.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig
from causal_bbc_endpoint import (
    _load_rows, _ema_series, _body_ratio, _close_trade, _summary,
    CausalPosition,
)

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc_sniper"])

CONCEPTS = {
    "single_rejection": "one 15m wick sweep and reclaim",
    "wick_reclaim": "adjacent 15m wick sweep then reclaim",
    "close_reclaim": "adjacent 15m close break then reclaim",
    "strict_3to4": "15m candle #3 break then candle #4 reclaim",
    "cross_hour": "candle #4 break then next hour candle #1 reclaim",
    "confirmed_reclaim": "any adjacent break/reclaim plus completed 1H EMA7 confirmation",
}


def _bar(row):
    return (
        float(row[1]), float(row[2]), float(row[3]), float(row[4])
    )


def _context_ok(side, previous_close, reference_ema):
    if side == "LONG":
        return previous_close > reference_ema
    return previous_close < reference_ema


def _is_break(row, reference_ema, side, mode):
    _, high, low, close = _bar(row)
    if side == "LONG":
        if mode == "wick":
            return low <= reference_ema and close >= reference_ema
        if mode == "close":
            return close < reference_ema
        return low <= reference_ema
    if mode == "wick":
        return high >= reference_ema and close <= reference_ema
    if mode == "close":
        return close > reference_ema
    return high >= reference_ema


def _is_reclaim(row, reference_ema, side, body_min):
    o, high, low, close = _bar(row)
    ratio = _body_ratio(o, high, low, close)
    if side == "LONG":
        return (
            low <= reference_ema
            and close > reference_ema
            and close > o
            and ratio >= body_min
        )
    return (
        high >= reference_ema
        and close < reference_ema
        and close < o
        and ratio >= body_min
    )


def _single_rejection(row, reference_ema, side, body_min):
    return _is_reclaim(row, reference_ema, side, body_min)


def _final_1h_direction(row, ema, bull_body_min, bear_body_min):
    o, high, low, close = _bar(row)
    if (
        low <= ema
        and close > ema
        and close > o
        and _body_ratio(o, high, low, close) >= bull_body_min
    ):
        return "LONG"
    if (
        high >= ema
        and close < ema
        and close < o
        and _body_ratio(o, high, low, close) >= bear_body_min
    ):
        return "SHORT"
    return None


def _make_open_position(signal, row, hour_index, cfg, price):
    side = signal["side"]
    if side == "LONG":
        sl = price * (1.0 - cfg.sl_pct)
        tp = price * (1.0 + cfg.tp_pct)
    else:
        sl = price * (1.0 + cfg.get_bear_sl_pct())
        tp = price * (1.0 - cfg.get_bear_tp_pct())
    return CausalPosition(
        tool=signal["tool"],
        side=side,
        entry_price=price,
        sl=sl,
        tp=tp,
        entry_hour=hour_index,
        entry_time=int(row[0]),
        peak_high=float(row[2]),
        trough_low=float(row[3]),
    )


def _pattern_sides(row, reference_ema, body_min, mode="either"):
    sides = []
    for side in ("LONG", "SHORT"):
        if _single_rejection(row, reference_ema, side, body_min):
            sides.append(side)
    if len(sides) > 1:
        return ["LONG" if float(row[4]) >= float(row[1]) else "SHORT"]
    return sides


@router.get("/causal-sniper")
def causal_sniper(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    concept: str = Query("single_rejection"),
    break_mode: str = Query("wick"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    bull_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    bear_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    include_trades: bool = Query(False),
):
    if concept not in CONCEPTS:
        return {"error": f"Unknown concept: {concept}", "available_concepts": CONCEPTS}
    if break_mode not in ("wick", "close", "either"):
        return {"error": "break_mode must be wick, close, or either"}

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ms = now_ms - end_days_ago * 86400 * 1000
    start_ms = end_ms - days * 86400 * 1000

    rows = _load_rows(symbol, timeframe, start_ms, end_ms)
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if len(rows) < va_window + 5:
        return {"error": f"Not enough 1H candles: {len(rows)}", "trades": []}
    if not rows15:
        return {"error": "15m data is required", "trades": []}

    cfg = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        bear_tp_pct=bear_tp_pct,
        bear_sl_pct=bear_sl_pct,
        bull_body_ratio_min=bull_body_ratio_min,
        bear_body_ratio_min=bear_body_ratio_min,
        entry_usd=entry_usd,
        leverage=leverage,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        enable_sideways_trades=False,
    )

    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    by_hour = {}
    for row in rows15:
        by_hour.setdefault(int(row[0]) // (60 * 60 * 1000), []).append(row)
    for bars in by_hour.values():
        bars.sort(key=lambda r: int(r[0]))

    def first_next_bar(hour_index, bar_index):
        current = by_hour.get(int(rows[hour_index][0]) // (60 * 60 * 1000), [])
        if bar_index + 1 < len(current):
            return current[bar_index + 1], hour_index
        if hour_index + 1 < len(rows):
            following = by_hour.get(
                int(rows[hour_index + 1][0]) // (60 * 60 * 1000), []
            )
            if following:
                return following[0], hour_index + 1
        return None, None

    active: Optional[CausalPosition] = None
    scheduled = {}
    trades = []
    pattern_events = 0
    skipped_while_in_position = 0
    cross_hour_break = None
    first_hour = max(va_window + 1, 2)

    for i in range(first_hour, len(rows) - 1):
        bars = by_hour.get(int(rows[i][0]) // (60 * 60 * 1000), [])
        if len(bars) < 4:
            continue
        bars = bars[:4]
        ref_ema = ema1h[i - 1]
        previous_close = float(rows[i - 1][4])
        body_for = {"LONG": bull_body_ratio_min, "SHORT": bear_body_ratio_min}
        hour_pattern = None

        for j, bar in enumerate(bars):
            bar_time = int(bar[0])

            pending = scheduled.pop(bar_time, None)
            if pending is not None and active is None:
                active = _make_open_position(
                    {"tool": "BULL" if pending["side"] == "LONG" else "BEAR",
                     "side": pending["side"]},
                    bar, pending["hour_index"], cfg, float(bar[1])
                )

            if active is not None:
                active.peak_high = max(active.peak_high, float(bar[2]))
                active.trough_low = min(active.trough_low, float(bar[3]))
                if active.side == "LONG":
                    if float(bar[3]) < active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        active = None
                    elif float(bar[2]) >= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        active = None
                else:
                    if float(bar[2]) > active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        active = None
                    elif float(bar[3]) <= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        active = None

            if active is not None:
                continue

            # Cross-hour pattern: prior hour's #4 break, current hour's #1 reclaim.
            if concept == "cross_hour" and j == 0 and cross_hour_break is not None:
                cross = cross_hour_break
                if _is_reclaim(
                    bar, cross["ema"], cross["side"], body_for[cross["side"]]
                ):
                    next_bar, next_hour = first_next_bar(i, j)
                    if next_bar is not None:
                        scheduled[int(next_bar[0])] = {
                            "side": cross["side"], "hour_index": next_hour
                        }
                        pattern_events += 1
                cross_hour_break = None

            if concept == "single_rejection":
                sides = _pattern_sides(
                    bar, ref_ema, body_for["LONG"], break_mode
                )
                if sides:
                    next_bar, next_hour = first_next_bar(i, j)
                    if next_bar is not None:
                        side = sides[0]
                        if _context_ok(side, previous_close, ref_ema):
                            scheduled[int(next_bar[0])] = {
                                "side": side, "hour_index": next_hour
                            }
                            pattern_events += 1
                    continue

            if concept in ("wick_reclaim", "close_reclaim", "confirmed_reclaim"):
                mode = "wick" if concept == "wick_reclaim" else "close"
                for side in ("LONG", "SHORT"):
                    if not _context_ok(side, previous_close, ref_ema):
                        continue
                    if j == 0:
                        continue
                    if _is_break(bars[j - 1], ref_ema, side, mode) and _is_reclaim(
                        bar, ref_ema, side, body_for[side]
                    ):
                        if concept == "confirmed_reclaim":
                            hour_pattern = side
                            pattern_events += 1
                        else:
                            next_bar, next_hour = first_next_bar(i, j)
                            if next_bar is not None:
                                scheduled[int(next_bar[0])] = {
                                    "side": side, "hour_index": next_hour
                                }
                                pattern_events += 1
                        break

            if concept == "strict_3to4" and j == 3:
                for side in ("LONG", "SHORT"):
                    if _context_ok(side, previous_close, ref_ema):
                        if _is_break(bars[2], ref_ema, side, break_mode) and _is_reclaim(
                            bars[3], ref_ema, side, body_for[side]
                        ):
                            next_bar, next_hour = first_next_bar(i, j)
                            if next_bar is not None:
                                scheduled[int(next_bar[0])] = {
                                    "side": side, "hour_index": next_hour
                                }
                                pattern_events += 1
                            break

            if concept == "cross_hour" and j == 3:
                for side in ("LONG", "SHORT"):
                    if _context_ok(side, previous_close, ref_ema) and _is_break(
                        bar, ref_ema, side, break_mode
                    ):
                        cross_hour_break = {
                            "side": side, "ema": ref_ema, "hour_index": i
                        }
                        break

        if concept == "confirmed_reclaim" and hour_pattern is not None:
            final = _final_1h_direction(
                rows[i], ema1h[i], bull_body_ratio_min, bear_body_ratio_min
            )
            if final == hour_pattern:
                next_bars = by_hour.get(
                    int(rows[i + 1][0]) // (60 * 60 * 1000), []
                )
                if next_bars:
                    scheduled[int(next_bars[0][0])] = {
                        "side": final, "hour_index": i + 1
                    }

    if active is not None:
        last = rows[-1]
        trades.append(_close_trade(active, float(last[4]), int(last[0]), "END", cfg))

    summary, per_tool = _summary(trades)
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "concept": concept,
        "concept_definition": CONCEPTS[concept],
        "break_mode": break_mode,
        "causal": True,
        "main_1h_ema_period": ema_period,
        "reference_ema": "previous_completed_1h_ema",
        "entry_timing": "next_completed_15m_open",
        "sideways": "skipped",
        "pattern_events": pattern_events,
        "skipped_while_in_position": skipped_while_in_position,
        "candles_processed": len(rows),
        "config": asdict(cfg),
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result


@router.get("/causal-sniper-health")
def causal_sniper_health():
    return {"status": "ok", "module": "mode3_bbc_sniper", "causal": True}
