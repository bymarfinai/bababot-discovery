"""
Causal BBC backtest endpoint.

This simulator removes the same-hour 15m look-ahead from the legacy BBC
backtest. A completed 1H candle can only arm a setup; entry is allowed on the
next hour's completed 15m candles. Stops and targets are evaluated only after
the 15m entry candle closes.
"""

import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc_causal"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _load_rows(symbol, timeframe, start_ms, end_ms):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            "SELECT open_time, open, high, low, close, volume "
            "FROM klines WHERE symbol=? AND timeframe=? "
            "AND open_time>=? AND open_time<? ORDER BY open_time ASC",
            (symbol, timeframe, start_ms, end_ms),
        ).fetchall()
    finally:
        conn.close()


def _ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(float(value) * alpha + out[-1] * (1.0 - alpha))
    return out


def _value_area(rows, window, pct_high=85.0, pct_low=15.0):
    vah = [None] * len(rows)
    val = [None] * len(rows)
    poc = [None] * len(rows)
    for i in range(window, len(rows)):
        sample = rows[i - window:i]
        highs = sorted(float(r[2]) for r in sample)
        lows = sorted(float(r[3]) for r in sample)
        closes = [float(r[4]) for r in sample]
        volumes = [float(r[5]) for r in sample]
        def percentile(values, pct):
            if len(values) == 1:
                return values[0]
            pos = (len(values) - 1) * pct / 100.0
            lo = int(pos)
            hi = min(lo + 1, len(values) - 1)
            frac = pos - lo
            return values[lo] + (values[hi] - values[lo]) * frac
        vah[i] = percentile(highs, pct_high)
        val[i] = percentile(lows, pct_low)
        total_volume = sum(volumes) or 1.0
        typical = [
            (float(r[2]) + float(r[3]) + float(r[4])) / 3.0
            for r in sample
        ]
        poc[i] = sum(typical[j] * volumes[j] for j in range(len(sample))) / total_volume
    return vah, val, poc


def _body_ratio(o, h, l, c):
    span = h - l
    return abs(c - o) / span if span > 0 else 0.0


@dataclass
class CausalPosition:
    tool: str
    side: str
    entry_price: float
    sl: float
    tp: float
    entry_hour: int
    entry_time: int
    peak_high: float
    trough_low: float


@dataclass
class CausalTrade:
    tool: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: int
    exit_time: int
    exit_type: str
    pnl_pct: float
    pnl_usd: float


def _capture_signal(switcher, bar_idx):
    position = switcher.position
    if position is None:
        return None
    signal = {
        "tool": position.tool,
        "side": position.side,
        "bar_idx": bar_idx,
        "entry_trigger": position.entry_trigger,
    }
    # The legacy switcher is used as a 1H signal/state machine only. The
    # actual position is owned by this causal simulator.
    switcher.position = None
    return signal


def _sync_state_after_exit(switcher, position, exit_type):
    if position.tool == "BULL":
        if exit_type == "TP":
            switcher.state = "BULL"
            switcher.bull_stay_warmup = True
        else:
            switcher.state = "WAIT_SEE_BULLISH"
            switcher.bull_stay_warmup = False
            switcher.markers.peak_high_bull = position.peak_high
            switcher.markers.hh_breach_case = "B"
    elif position.tool == "BEAR":
        if exit_type == "TP":
            switcher.state = "BEAR"
            switcher.bear_stay_warmup = True
        else:
            switcher.state = "WAIT_SEE_BEARISH"
            switcher.bear_stay_warmup = False
            switcher.markers.trough_low_bear = position.trough_low
            switcher.markers.ll_breach_case = "B"
    elif position.tool == "SIDEWAYS":
        switcher.state = "SIDEWAYS" if exit_type == "TP" else (
            "BULL" if position.side == "SHORT" else "BEAR"
        )


def _confirm_signal(signal, candle15, ema15, vah, val, sideways_body_ratio):
    o, h, l, c = map(float, candle15[1:5])
    if signal["tool"] == "BULL":
        return l <= ema15 and c > ema15 and c > o
    if signal["tool"] == "BEAR":
        return h >= ema15 and c < ema15 and c < o
    if signal["tool"] == "SIDEWAYS":
        if signal["side"] == "SHORT":
            return vah is not None and h >= vah and c <= vah and _body_ratio(o, h, l, c) >= sideways_body_ratio
        return val is not None and l <= val and c >= val and _body_ratio(o, h, l, c) >= sideways_body_ratio
    return False


def _make_position(signal, candle15, candle_index, hour_index, cfg, vah, val):
    price = float(candle15[4])
    side = signal["side"]
    if signal["tool"] == "SIDEWAYS":
        if side == "LONG":
            sl = float(candle15[3])
            tp = price * (1.0 + cfg.sideways_tp_pct)
        else:
            sl = float(candle15[2])
            tp = price * (1.0 - cfg.sideways_tp_pct)
    elif side == "LONG":
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
        entry_time=int(candle15[0]),
        peak_high=float(candle15[2]),
        trough_low=float(candle15[3]),
    )


def _close_trade(position, exit_price, exit_time, exit_type, cfg):
    if position.side == "LONG":
        raw_pct = (exit_price - position.entry_price) / position.entry_price
    else:
        raw_pct = (position.entry_price - exit_price) / position.entry_price
    net_pct = raw_pct - cfg.total_cost_pct()
    return CausalTrade(
        tool=position.tool,
        side=position.side,
        entry_price=position.entry_price,
        exit_price=exit_price,
        entry_time=position.entry_time,
        exit_time=int(exit_time),
        exit_type=exit_type,
        pnl_pct=net_pct,
        pnl_usd=net_pct * cfg.notional(),
    )


def _summary(trades):
    wins = [t for t in trades if t.pnl_usd > 0]
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    loss_streak = 0
    max_loss_streak = 0
    for trade in trades:
        equity += trade.pnl_usd
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if trade.pnl_usd <= 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0
    by_tool = {}
    for tool in ("SIDEWAYS", "BULL", "BEAR"):
        subset = [t for t in trades if t.tool == tool]
        if subset:
            tool_wins = sum(t.pnl_usd > 0 for t in subset)
            by_tool[tool] = {
                "count": len(subset),
                "wr_pct": round(100.0 * tool_wins / len(subset), 2),
                "pnl_usd": round(sum(t.pnl_usd for t in subset), 2),
            }
    return {
        "total_trades": len(trades),
        "win_rate_pct": round(100.0 * len(wins) / len(trades), 2) if trades else 0.0,
        "wins": len(wins),
        "losses": len(trades) - len(wins),
        "total_pnl_usd": round(sum(t.pnl_usd for t in trades), 2),
        "capital_start": 100.0,
        "capital_end": round(100.0 + sum(t.pnl_usd for t in trades), 2),
        "max_drawdown_usd": round(max_dd, 2),
        "max_loss_streak": max_loss_streak,
        "exit_type_breakdown": {
            kind: sum(t.exit_type == kind for t in trades)
            for kind in ("TP", "SL", "REVERSE", "END")
            if any(t.exit_type == kind for t in trades)
        },
    }, by_tool


@router.get("/causal-backtest")
def causal_backtest(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    mtf_ema_period: int = Query(20, ge=5, le=100),
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
    if len(rows) < va_window + 5:
        return {"error": f"Not enough candles: {len(rows)}", "trades": []}
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if not rows15:
        return {"error": "15m data is required for causal entry timing", "trades": []}

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
    closes = [float(r[4]) for r in rows]
    ema = _ema_series(closes, ema_period)
    vah, val, poc = _value_area(rows, va_window)
    closes15 = [float(r[4]) for r in rows15]
    ema15 = _ema_series(closes15, mtf_ema_period)
    idx15 = {int(r[0]): i for i, r in enumerate(rows15)}
    by_hour = {}
    for r in rows15:
        by_hour.setdefault(int(r[0]) // (60 * 60 * 1000), []).append(r)

    switcher = Switcher(cfg)
    warmup = cfg.startup_warmup_candles
    for i in range(min(warmup, len(rows))):
        switcher.process_candle(
            i, float(rows[i][1]), float(rows[i][2]), float(rows[i][3]),
            float(rows[i][4]), ema[i], vah[i], val[i], poc[i]
        )
        switcher.position = None

    pending = None
    active: Optional[CausalPosition] = None
    trades = []
    processed_start = max(warmup, va_window + 1)

    for i in range(processed_start, len(rows)):
        hour_time = int(rows[i][0])
        hour_key = hour_time // (60 * 60 * 1000)
        candles15 = sorted(by_hour.get(hour_key, []), key=lambda r: int(r[0]))

        # Resolve the setup armed by the preceding completed 1H candle.
        for c15 in candles15:
            c15_time = int(c15[0])
            j15 = idx15.get(c15_time)
            if j15 is None:
                continue
            if active is not None:
                active.peak_high = max(active.peak_high, float(c15[2]))
                active.trough_low = min(active.trough_low, float(c15[3]))
                if active.side == "LONG":
                    if float(c15[3]) < active.sl:
                        trades.append(_close_trade(active, active.sl, c15_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                    elif float(c15[2]) >= active.tp:
                        trades.append(_close_trade(active, active.tp, c15_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                else:
                    if float(c15[2]) > active.sl:
                        trades.append(_close_trade(active, active.sl, c15_time, "SL", cfg))
                        _sync_state_after_exit(switcher, active, "SL")
                        active = None
                    elif float(c15[3]) <= active.tp:
                        trades.append(_close_trade(active, active.tp, c15_time, "TP", cfg))
                        _sync_state_after_exit(switcher, active, "TP")
                        active = None
                continue
            if pending is not None and _confirm_signal(
                pending, c15, ema15[j15], vah[i - 1] if i > 0 else None,
                val[i - 1] if i > 0 else None, sideways_body_ratio_min
            ):
                active = _make_position(
                    pending, c15, j15, i, cfg,
                    vah[i - 1] if i > 0 else None,
                    val[i - 1] if i > 0 else None,
                )
                pending = None

        # Only now, after this 1H candle has closed, update the signal machine.
        switcher.process_candle(
            i, float(rows[i][1]), float(rows[i][2]), float(rows[i][3]),
            float(rows[i][4]), ema[i], vah[i], val[i], poc[i]
        )
        signal = _capture_signal(switcher, i)

        if active is not None and signal is not None and signal["side"] != active.side:
            trades.append(_close_trade(active, float(rows[i][4]), hour_time, "REVERSE", cfg))
            _sync_state_after_exit(switcher, active, "REVERSE")
            active = None

        if active is None and signal is not None:
            pending = signal

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
        "entry_timing": "next_completed_15m_after_1h_close",
        "candles_processed": len(rows),
        "candles_15m": len(rows15),
        "config": asdict(cfg),
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result


@router.get("/health-causal")
def causal_health():
    return {"status": "ok", "module": "mode3_bbc_causal", "causal": True}
