"""Mode3 BBC Backtest Endpoint — /mode3_bbc/backtest.
Filter-free variant of Mode3 for testing pure state machine + entry logic.
"""
import os
from dataclasses import asdict
from fastapi import APIRouter, Query
import sqlite3
import numpy as np
from datetime import datetime

from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def load_candles_from_db(symbol, timeframe, start_ts, end_ts):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT open_time, open, high, low, close, volume FROM klines
        WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC""", (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall()
    conn.close()
    return rows


@router.get("/backtest")
def backtest_mode3_bbc(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(30, ge=1, le=1500),
    end_days_ago: int = Query(0, ge=0, le=1500),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.012, ge=0.001, le=0.05),
    sideways_tp_pct: float = Query(0.003, ge=0.0, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    fee_pct: float = Query(0.001),
    slippage_pct: float = Query(0.0005),
):
    config = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sideways_tp_pct=sideways_tp_pct,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
    )

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ts = now_ms - (end_days_ago * 86400 * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles_from_db(symbol, timeframe, start_ts, end_ts)

    if len(rows) < config.startup_warmup_candles:
        return {"error": f"Not enough candles: {len(rows)}", "trades": []}

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, config.ema_period)

    vahs, vals = [], []
    for i in range(len(rows)):
        vah, val, _poc = compute_va_at_bar(
            highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low,
        )
        vahs.append(vah)
        vals.append(val)

    switcher = Switcher(config)

    for i in range(len(rows)):
        switcher.process_candle(
            bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i],
            ema20=ema20[i], vah=vahs[i], val=vals[i],
        )

    trades = switcher.trades
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    total_pnl_usd = sum(t.pnl_usd for t in trades)
    total_pnl_pct = sum(t.pnl_pct for t in trades) * 100
    wr = 100.0 * len(wins) / n if n > 0 else 0

    tool_stats = {}
    for tool in ['SIDEWAYS', 'BULL', 'BEAR']:
        tt = [t for t in trades if t.tool == tool]
        if tt:
            tw = [t for t in tt if t.pnl_usd > 0]
            tool_stats[tool] = {
                "count": len(tt),
                "wr_pct": round(100.0 * len(tw) / len(tt), 2),
                "pnl_usd": round(sum(t.pnl_usd for t in tt), 2),
                "pnl_pct": round(sum(t.pnl_pct for t in tt) * 100, 3),
            }

    exit_type_breakdown = {}
    for t in trades:
        exit_type_breakdown[t.exit_type] = exit_type_breakdown.get(t.exit_type, 0) + 1

    trade_list = []
    for t in trades:
        trade_list.append({
            "tool": t.tool, "side": t.side,
            "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
            "entry_bar": t.entry_bar, "exit_bar": t.exit_bar, "exit_type": t.exit_type,
            "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2),
            "sl_level": round(t.sl_level, 2), "tp_level": round(t.tp_level, 2),
            "sl_distance_pct": round(abs(t.entry_price - t.sl_level) / t.entry_price * 100, 3),
            "ema_at_entry": round(t.ema_at_entry, 2), "ema_at_exit": round(t.ema_at_exit, 2),
            "peak_high": round(t.peak_high, 2), "trough_low": round(t.trough_low, 2),
        })

    return {
        "symbol": symbol, "timeframe": timeframe, "days": days, "end_days_ago": end_days_ago,
        "candles_processed": len(rows),
        "period_start_utc": datetime.utcfromtimestamp(start_ts / 1000).strftime('%Y-%m-%d'),
        "period_end_utc": datetime.utcfromtimestamp(end_ts / 1000).strftime('%Y-%m-%d'),
        "config": asdict(config),
        "summary": {
            "total_trades": n,
            "win_rate_pct": round(wr, 2),
            "wins": len(wins), "losses": len(losses),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_pct": round(total_pnl_pct, 3),
            "capital_start": config.capital_usd,
            "capital_end": round(config.capital_usd + total_pnl_usd, 2),
            "sideways_entries_attempted": switcher._sideways_entries,
            "bull_entries_attempted": switcher._bull_entries,
            "bear_entries_attempted": switcher._bear_entries,
            "exit_type_breakdown": exit_type_breakdown,
        },
        "per_tool": tool_stats,
        "trades": trade_list,
        "final_state": switcher.state,
    }


@router.get("/health")
def mode3_bbc_health():
    return {"status": "ok", "module": "mode3_bbc", "version": "0.1", "db_path": DB_PATH}
