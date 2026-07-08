"""
Mode3 Backtest Endpoint - FastAPI router.
Wiring di app.py:
    from mode3_backtest_endpoint import router as mode3_clean_router
    app.include_router(mode3_clean_router)
"""
import os
from dataclasses import asdict
from fastapi import APIRouter, Query
from typing import Optional
import sqlite3
import numpy as np
from datetime import datetime

from mode3 import Mode3Config, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3", tags=["mode3"])

# Use same DB path as app.py
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def load_candles_from_db(symbol, timeframe, start_ts, end_ts, db_path=None):
    """Load candles from SQLite DB (klines table, matching app.py schema)."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND timeframe = ?
          AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC
        """,
        (symbol, timeframe, start_ts, end_ts),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


@router.get("/backtest")
def backtest_mode3(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(30, ge=1, le=365),
    va_window: int = Query(50, ge=20, le=200),
    tp_pct: float = Query(0.006, ge=0.001, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    fee_pct: float = Query(0.001),
    slippage_pct: float = Query(0.0005),
):
    """
    Backtest Mode3 switcher on historical candles.
    Returns per-trade breakdown + summary metrics + per-tool stats.
    """
    config = Mode3Config(
        va_window=va_window,
        tp_pct=tp_pct,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
    )

    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles_from_db(symbol, timeframe, start_ts, end_ts)

    if len(rows) < config.startup_warmup_candles:
        return {
            "error": f"Not enough candles: got {len(rows)}, need >= {config.startup_warmup_candles}",
            "db_path_used": DB_PATH,
            "trades": [],
        }

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, config.ema_period)
    switcher = Switcher(config)

    for i in range(len(rows)):
        vah, val, poc = compute_va_at_bar(
            highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low,
        )
        switcher.process_candle(
            bar_idx=i,
            o=opens[i], h=highs[i], l=lows[i], c=closes[i], v=volumes[i],
            ema20=ema20[i],
            vah=vah, val=val, poc=poc,
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

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "candles_processed": len(rows),
        "config": asdict(config),
        "summary": {
            "total_trades": n,
            "win_rate_pct": round(wr, 2),
            "wins": len(wins),
            "losses": len(losses),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_pct": round(total_pnl_pct, 3),
            "capital_start": config.capital_usd,
            "capital_end": round(config.capital_usd + total_pnl_usd, 2),
        },
        "per_tool": tool_stats,
        "trades": [
            {
                "tool": t.tool,
                "side": t.side,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "entry_bar": t.entry_bar,
                "exit_bar": t.exit_bar,
                "exit_type": t.exit_type,
                "pnl_pct": round(t.pnl_pct * 100, 3),
                "pnl_usd": round(t.pnl_usd, 2),
            }
            for t in trades
        ],
        "final_state": switcher.state,
    }


@router.get("/health")
def mode3_health():
    return {"status": "ok", "module": "mode3", "version": "0.21", "db_path": DB_PATH}
