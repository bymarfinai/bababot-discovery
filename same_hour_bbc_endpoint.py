"""
Same-hour causal BBC timing: arm on 15m candle #3, enter on #4.

The previous completed 1H EMA is used for the #3 arm condition. The #4
confirmation uses a completed 15m candle and the 15m EMA. The final 1H
signal is processed only after the fourth 15m candle closes.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher
from causal_bbc_endpoint import (
    _load_rows, _ema_series, _value_area, _body_ratio,
    _capture_signal, _sync_state_after_exit, _make_position,
    _close_trade, _summary, CausalPosition,
)

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc_same_hour"])


def _arm_direction(candles15, reference_ema):
    """Arm from the first three completed 15m candles of an hour."""
    if len(candles15) < 3 or reference_ema is None:
        return None
    first = candles15[0]
    third = candles15[2]
    o = float(first[1])
    h = max(float(c[2]) for c in candles15[:3])
    l = min(float(c[3]) for c in candles15[:3])
    c = float(third[4])
    bull = l <= reference_ema and c >= reference_ema
    bear = h >= reference_ema and c <= reference_ema
    if bull and bear:
        return "LONG" if c >= o else "SHORT"
    if bull:
        return "LONG"
    if bear:
        return "SHORT"
    return None


def _confirm_fourth(candle15, ema15, direction, body_ratio):
    o, h, l, c = map(float, candle15[1:5])
    if direction == "LONG":
        return l <= ema15 and c > ema15 and c > o and _body_ratio(o, h, l, c) >= body_ratio
    return h >= ema15 and c < ema15 and c < o and _body_ratio(o, h, l, c) >= body_ratio


@router.get("/causal-3to4-backtest")
def causal_3to4_backtest(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    mtf_ema_period: int = Query(20, ge=5, le=100),
    use_15m_confirmation: bool = Query(True),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    bull_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    bear_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    sideways_body_ratio_min: float = Query(0.6, ge=0.0, le=1.0),
    sideways_tp_pct: float = Query(0.015, ge=0.001, le=0.10),
    enable_sideways_trades: bool = Query(False),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    include_trades: bool = Query(False),
):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ms = now_ms - end_days_ago * 86400 * 1000
    start_ms = end_ms - days * 86400 * 1000
    rows = _load_rows(symbol, timeframe, start_ms, end_ms)
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if len(rows) < va_window + 5:
        return {"error": f"Not enough candles: {len(rows)}", "trades": []}
    if not rows15:
        return {"error": "15m data is required", "trades": []}

    cfg = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        bear_tp_pct=bear_tp_pct,
        bear_sl_pct=bear_sl_pct,
        sideways_tp_pct=sideways_tp_pct,
        sideways_body_ratio_min=sideways_body_ratio_min,
        bull_body_ratio_min=bull_body_ratio_min,
        bear_body_ratio_min=bear_body_ratio_min,
        enable_sideways_trades=enable_sideways_trades,
        entry_usd=entry_usd,
        leverage=leverage,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
    )
    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    vah, val, poc = _value_area(rows, va_window)
    ema15 = _ema_series([float(r[4]) for r in rows15], mtf_ema_period)
    idx15 = {int(r[0]): i for i, r in enumerate(rows15)}
    by_hour = {}
    for r in rows15:
        by_hour.setdefault(int(r[0]) // (60 * 60 * 1000), []).append(r)
    for bars in by_hour.values():
        bars.sort(key=lambda r: int(r[0]))

    switcher = Switcher(cfg)
    warmup = cfg.startup_warmup_candles
    for i in range(min(warmup, len(rows))):
        switcher.process_candle(
            i, float(rows[i][1]), float(rows[i][2]), float(rows[i][3]),
            float(rows[i][4]), ema1h[i], vah[i], val[i], poc[i]
        )
        switcher.position = None

    active: Optional[CausalPosition] = None
    trades = []
    processed_start = max(warmup, va_window + 1)

    for i in range(processed_start, len(rows)):
        hour_time = int(rows[i][0])
        bars = by_hour.get(hour_time // (60 * 60 * 1000), [])
        if len(bars) < 4:
            continue

        # Existing positions are evaluated on each completed 15m bar. The
        # entry bar itself is never evaluated for an exit.
        for bar in bars:
            j = idx15.get(int(bar[0]))
            if j is None or active is None:
                continue
            active.peak_high = max(active.peak_high, float(bar[2]))
            active.trough_low = min(active.trough_low, float(bar[3]))
            if active.side == "LONG":
                if float(bar[3]) < active.sl:
                    trades.append(_close_trade(active, active.sl, int(bar[0]), "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                elif float(bar[2]) >= active.tp:
                    trades.append(_close_trade(active, active.tp, int(bar[0]), "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
            else:
                if float(bar[2]) > active.sl:
                    trades.append(_close_trade(active, active.sl, int(bar[0]), "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                elif float(bar[3]) <= active.tp:
                    trades.append(_close_trade(active, active.tp, int(bar[0]), "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None

        # Candle #3 is observed before the final 1H candle is known.
        reference_ema = ema1h[i - 1] if i > 0 else None
        armed = _arm_direction(bars[:3], reference_ema)

        # Process the completed 1H candle only after candle #4 closes.
        switcher.process_candle(
            i, float(rows[i][1]), float(rows[i][2]), float(rows[i][3]),
            float(rows[i][4]), ema1h[i], vah[i], val[i], poc[i]
        )
        signal = _capture_signal(switcher, i)

        if active is not None and signal is not None and signal["side"] != active.side:
            trades.append(_close_trade(active, float(rows[i][4]), hour_time, "REVERSE", cfg))
            _sync_state_after_exit(switcher, active, "REVERSE")
            active = None

        # The fourth 15m candle can be used only after the 1H signal and
        # candle #3 arm are both available.
        if active is None and signal is not None and len(bars) >= 4:
            direction = signal["side"]
            if signal["tool"] in ("BULL", "BEAR") and armed == direction:
                fourth = bars[3]
                j4 = idx15.get(int(fourth[0]))
                if j4 is not None:
                    ratio = bull_body_ratio_min if direction == "LONG" else bear_body_ratio_min
                    if (not use_15m_confirmation or
                            _confirm_fourth(fourth, ema15[j4], direction, ratio)):
                        active = _make_position(
                            signal, fourth, j4, i, cfg,
                            vah[i], val[i],
                        )

    if active is not None:
        last = rows[-1]
        trades.append(_close_trade(active, float(last[4]), int(last[0]), "END", cfg))

    summary, per_tool = _summary(trades)
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "end_days_ago": end_days_ago,
        "causal": True,
        "entry_timing": "same_hour_candle_3_arm_candle_4_entry",
        "main_1h_ema_period": ema_period,
        "mtf_15m_ema_period": mtf_ema_period,
        "use_15m_confirmation": use_15m_confirmation,
        "candles_processed": len(rows),
        "candles_15m": len(rows15),
        "config": asdict(cfg),
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result


@router.get("/health-3to4")
def causal_3to4_health():
    return {"status": "ok", "module": "mode3_bbc_same_hour", "causal": True}
