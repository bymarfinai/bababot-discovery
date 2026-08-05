"""
Causal 1H-state + 15m EMA rejection backtest.

A completed 1H BBC state supplies the directional bias. During the next
1H, the first completed 15m candle that rejects the current 15m EMA
in the state direction schedules a market entry at the next 15m open.
The 1H state EMA period remains configurable independently. Positions are
evaluated on completed 15m candles.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher, Position
from causal_bbc_endpoint import (
    _load_rows, _ema_series, _value_area, _body_ratio, _close_trade,
    _summary, CausalPosition, _sync_state_after_exit,
)

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc_state_mtf_reject"])

HOUR_MS = 60 * 60 * 1000


def _state_side(state):
    if state == "BULL":
        return "LONG"
    if state == "BEAR":
        return "SHORT"
    return None


def _rejects_ema(row, ema, side, body_min):
    o = float(row[1])
    h = float(row[2])
    l = float(row[3])
    c = float(row[4])
    ratio = _body_ratio(o, h, l, c)
    if side == "LONG":
        return l <= ema and c > ema and c > o and ratio >= body_min
    return h >= ema and c < ema and c < o and ratio >= body_min


def _dummy_position(pos: CausalPosition):
    if pos.side == "LONG":
        sl = 0.0
        tp = float("inf")
    else:
        sl = float("inf")
        tp = 0.0
    return Position(
        tool=pos.tool,
        side=pos.side,
        entry_price=pos.entry_price,
        entry_bar=pos.entry_hour,
        entry_high=pos.peak_high,
        entry_low=pos.trough_low,
        sl_level=sl,
        tp_level=tp,
        peak_high=pos.peak_high,
        trough_low=pos.trough_low,
        ema_at_entry=0.0,
        entry_trigger="state_reject_hold",
        be_triggered=True,
        original_sl=sl,
    )


def _make_position(side, row, hour_index, cfg, price=None):
    price = float(row[1]) if price is None else float(price)
    if side == "LONG":
        sl = price * (1.0 - cfg.sl_pct)
        tp = price * (1.0 + cfg.tp_pct)
        tool = "BULL"
    else:
        sl = price * (1.0 + cfg.get_bear_sl_pct())
        tp = price * (1.0 - cfg.get_bear_tp_pct())
        tool = "BEAR"
    return CausalPosition(
        tool=tool,
        side=side,
        entry_price=price,
        sl=sl,
        tp=tp,
        entry_hour=hour_index,
        entry_time=int(row[0]),
        peak_high=float(row[2]),
        trough_low=float(row[3]),
    )


@router.get("/causal-state-mtf-reject")
def causal_state_reject(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    reject_ema_period: int = Query(7, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    bull_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    bear_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    fee_pct: float = Query(0.001, ge=0.0, le=0.10),
    slippage_pct: float = Query(0.0005, ge=0.0, le=0.10),
    entry_timing: str = Query("next_open"),
    include_trades: bool = Query(False),
):
    if entry_timing not in ("next_open", "close"):
        return {
            "error": "entry_timing must be next_open or close",
            "trades": [],
        }
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
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        enable_sideways_trades=False,
    )
    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    ema15 = _ema_series([float(r[4]) for r in rows15], reject_ema_period)
    ema15_by_time = {
        int(row[0]): ema15[j] for j, row in enumerate(rows15)
    }
    vah, val, poc = _value_area(rows, va_window)

    by_hour = {}
    for row in rows15:
        by_hour.setdefault(int(row[0]) // HOUR_MS, []).append(row)
    for bars in by_hour.values():
        bars.sort(key=lambda r: int(r[0]))

    switcher = Switcher(cfg)
    active: Optional[CausalPosition] = None
    scheduled = {}
    trades = []
    rejection_events = 0
    canceled_state_mismatch = 0
    ignored_switcher_entries = 0
    first_hour = max(va_window + 1, 1)

    for i, row in enumerate(rows):
        hour_key = int(row[0]) // HOUR_MS
        bars = by_hour.get(hour_key, [])
        if len(bars) < 4:
            continue
        bars = bars[:4]
        state_at_hour_start = switcher.state

        for j, bar in enumerate(bars):
            bar_time = int(bar[0])
            pending = scheduled.pop(bar_time, None)
            if pending is not None and active is None:
                # A signal scheduled across an hour boundary is canceled if
                # the completed 1H state changed before execution.
                if pending["signal_hour"] == i or _state_side(switcher.state) == pending["side"]:
                    active = _make_position(pending["side"], bar, i, cfg)
                else:
                    canceled_state_mismatch += 1

            exited_this_bar = False
            if active is not None:
                active.peak_high = max(active.peak_high, float(bar[2]))
                active.trough_low = min(active.trough_low, float(bar[3]))
                if active.side == "LONG":
                    if float(bar[3]) < active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                        exited_this_bar = True
                    elif float(bar[2]) >= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                        exited_this_bar = True
                else:
                    if float(bar[2]) > active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                        exited_this_bar = True

                    elif float(bar[3]) <= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                        exited_this_bar = True

            # A position or a pending entry blocks another entry for this pair.
            if active is not None or scheduled or exited_this_bar:
                continue

            # Exit synchronization can change BULL/BEAR into a WAIT state
            # within the same hour; always read the current state here.
            current_state_side = _state_side(switcher.state)
            bar_ema = ema15_by_time.get(bar_time)
            if bar_ema is not None and current_state_side is not None:
                body_min = (
                    bull_body_ratio_min if current_state_side == "LONG"
                    else bear_body_ratio_min
                )
                if _rejects_ema(bar, bar_ema, current_state_side, body_min):
                    if entry_timing == "close":
                        # The signal is known at this completed 15m close.
                        # No intrabar exit is credited to the same candle.
                        active = _make_position(
                            current_state_side,
                            bar,
                            i,
                            cfg,
                            price=float(bar[4]),
                        )
                        rejection_events += 1
                    else:
                        next_bar = None
                        next_hour = i
                        if j + 1 < len(bars):
                            next_bar = bars[j + 1]
                        elif i + 1 < len(rows):
                            next_bars = by_hour.get(
                                int(rows[i + 1][0]) // HOUR_MS, []
                            )
                            if next_bars:
                                next_bar = next_bars[0]
                                next_hour = i + 1
                        if next_bar is not None:
                            scheduled[int(next_bar[0])] = {
                                "side": current_state_side,
                                "signal_hour": i,
                                "source_bar": bar_time,
                            }
                            rejection_events += 1

        # Keep the full Switcher state current at the completed 1H close.
        # If a real position is open, block new Switcher entries while it is
        # held; otherwise discard direct 1H entries because this endpoint
        # tests only the state-based 15m trigger.
        if active is not None:
            switcher.position = _dummy_position(active)
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            switcher.position = None
        else:
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            if switcher.position is not None:
                ignored_switcher_entries += 1
                switcher.position = None

    if active is not None:
        last = rows15[-1]
        trades.append(_close_trade(active, float(last[4]), int(last[0]), "END", cfg))

    summary, per_tool = _summary(trades)
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "end_days_ago": end_days_ago,
        "causal": True,
        "state_based": True,
        "entry_timing": (
            "completed_15m_close"
            if entry_timing == "close"
            else "next_15m_open_after_ema7_rejection"
        ),
        "reference_ema": "completed_15m_ema",
        "reject_ema_period": reject_ema_period,
        "exit_model": "completed_15m_ohlc",
        "main_1h_ema_period": ema_period,
        "config": asdict(cfg),
        "rejection_events": rejection_events,
        "canceled_state_mismatch": canceled_state_mismatch,
        "ignored_switcher_entries": ignored_switcher_entries,
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result



def _make_limit_position(side, row, hour_index, cfg, price):
    if side == "LONG":
        sl = price * (1.0 - cfg.sl_pct)
        tp = price * (1.0 + cfg.tp_pct)
        tool = "BULL"
    else:
        sl = price * (1.0 + cfg.get_bear_sl_pct())
        tp = price * (1.0 - cfg.get_bear_tp_pct())
        tool = "BEAR"
    return CausalPosition(
        tool=tool,
        side=side,
        entry_price=price,
        sl=sl,
        tp=tp,
        entry_hour=hour_index,
        entry_time=int(row[0]),
        peak_high=float(row[2]),
        trough_low=float(row[3]),
    )


@router.get("/causal-state-mtf-limit")
def causal_state_limit(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    limit_ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    fee_pct: float = Query(0.001, ge=0.0, le=0.10),
    slippage_pct: float = Query(0.0005, ge=0.0, le=0.10),
    include_trades: bool = Query(False),
):
    """
    Causal limit diagnostic: use the previous completed 1H state as the
    directional gate, arm one limit at the previous completed 15m EMA,
    expire it at that 15m candle close, and re-arm on the next candle.
    """
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
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        enable_sideways_trades=False,
    )
    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    closes15 = [float(r[4]) for r in rows15]
    ema15 = _ema_series(closes15, limit_ema_period)
    ema15_before = {
        int(rows15[j][0]): ema15[j - 1]
        for j in range(1, len(rows15))
    }
    vah, val, poc = _value_area(rows, va_window)

    by_hour = {}
    for row in rows15:
        by_hour.setdefault(int(row[0]) // HOUR_MS, []).append(row)
    for bars in by_hour.values():
        bars.sort(key=lambda r: int(r[0]))

    switcher = Switcher(cfg)
    active: Optional[CausalPosition] = None
    trades = []
    order_attempts = 0
    fills = 0
    fills_with_reclaim = 0
    fills_without_reclaim = 0
    ignored_switcher_entries = 0
    no_reentry_after_exit = 0

    for i, row in enumerate(rows):
        hour_key = int(row[0]) // HOUR_MS
        bars = by_hour.get(hour_key, [])
        if len(bars) < 4:
            continue
        bars = bars[:4]

        for bar in bars:
            bar_time = int(bar[0])
            exited_this_bar = False

            if active is not None:
                active.peak_high = max(active.peak_high, float(bar[2]))
                active.trough_low = min(active.trough_low, float(bar[3]))
                if active.side == "LONG":
                    if float(bar[3]) < active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                        exited_this_bar = True
                    elif float(bar[2]) >= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                        exited_this_bar = True
                else:
                    if float(bar[2]) > active.sl:
                        trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                        exited_this_bar = True
                    elif float(bar[3]) <= active.tp:
                        trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                        exited_this_bar = True

            if active is not None:
                continue
            if exited_this_bar:
                no_reentry_after_exit += 1
                continue

            state_side = _state_side(switcher.state)
            level = ema15_before.get(bar_time)
            if state_side is None or level is None:
                continue

            # This order exists only for this one 15m candle.
            order_attempts += 1
            o = float(bar[1])
            h = float(bar[2])
            l = float(bar[3])
            c = float(bar[4])
            if state_side == "LONG":
                touched = l <= level
                fill_price = o if o <= level else level
                reclaim = c > level and c > o
            else:
                touched = h >= level
                fill_price = o if o >= level else level
                reclaim = c < level and c < o
            if not touched:
                continue

            fills += 1
            if reclaim:
                fills_with_reclaim += 1
            else:
                fills_without_reclaim += 1
            active = _make_limit_position(state_side, bar, i, cfg, fill_price)

            # Conservative completed-15m wick model: SL before TP if both
            # are touched in the fill candle, because intrabar order is unknown.
            if state_side == "LONG":
                if l < active.sl:
                    trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                    no_reentry_after_exit += 1
                elif h >= active.tp:
                    trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
                    no_reentry_after_exit += 1
            else:
                if h > active.sl:
                    trades.append(_close_trade(active, active.sl, bar_time, "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                    no_reentry_after_exit += 1
                elif l <= active.tp:
                    trades.append(_close_trade(active, active.tp, bar_time, "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
                    no_reentry_after_exit += 1

        # Update the 1H state only after all four 15m candles have completed.
        if active is not None:
            switcher.position = _dummy_position(active)
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            switcher.position = None
        else:
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            if switcher.position is not None:
                ignored_switcher_entries += 1
                switcher.position = None

    if active is not None:
        last = rows15[-1]
        trades.append(_close_trade(active, float(last[4]), int(last[0]), "END", cfg))

    summary, per_tool = _summary(trades)
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "end_days_ago": end_days_ago,
        "causal": True,
        "state_based": True,
        "entry_timing": "one_candle_limit_at_previous_completed_15m_ema",
        "main_1h_ema_period": ema_period,
        "limit_ema_period": limit_ema_period,
        "exit_model": "completed_15m_ohlc",
        "order_attempts": order_attempts,
        "fills": fills,
        "fill_rate_pct": round(100.0 * fills / order_attempts, 2)
        if order_attempts else 0.0,
        "fills_with_reclaim": fills_with_reclaim,
        "fills_without_reclaim": fills_without_reclaim,
        "ignored_switcher_entries": ignored_switcher_entries,
        "no_reentry_after_exit": no_reentry_after_exit,
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result


@router.get("/health-state-mtf-reject")
def state_mtf_reject_health():
    return {
        "status": "ok",
        "module": "mode3_bbc_state_mtf_reject",
        "causal": True,
    }
