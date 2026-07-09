"""
Mode4 Backtest Endpoint — Trend-Following.
Auto-registers with app.py's FastAPI instance via delayed threading hack.
"""
import os
from dataclasses import asdict
from fastapi import APIRouter, Query
import sqlite3
import numpy as np
from datetime import datetime

from mode4 import Mode4Config, Switcher, compute_ema_series

router = APIRouter(prefix="/mode4", tags=["mode4"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def load_candles(symbol, timeframe, start_ts, end_ts):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC
    """, (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall()
    conn.close()
    return rows


@router.get("/backtest")
def backtest_mode4(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(90, ge=1, le=365),
    tp_pct: float = Query(0.010, ge=0.001, le=0.05),
    sl_pct: float = Query(0.005, ge=0.001, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    min_volume_ratio: float = Query(1.5, ge=0.0, le=5.0),
    min_slope_pct: float = Query(0.010, ge=0.0, le=0.1),
):
    config = Mode4Config(
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        entry_usd=entry_usd,
        leverage=leverage,
        min_volume_ratio=min_volume_ratio,
        min_slope_pct=min_slope_pct,
    )

    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles(symbol, timeframe, start_ts, end_ts)

    if len(rows) < config.startup_warmup_candles:
        return {"error": f"Not enough candles: got {len(rows)}", "trades": []}

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, config.ema_period)
    switcher = Switcher(config)

    for i in range(len(rows)):
        switcher.process_candle(i, opens[i], highs[i], lows[i], closes[i], volumes[i], ema20[i])

    trades = switcher.trades
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    total_pnl = sum(t.pnl_usd for t in trades)
    wr = 100.0 * len(wins) / n if n > 0 else 0

    longs = [t for t in trades if t.side == 'LONG']
    shorts = [t for t in trades if t.side == 'SHORT']

    def side_stats(ts):
        if not ts: return {"count": 0, "wr_pct": 0, "pnl_usd": 0}
        w = [t for t in ts if t.pnl_usd > 0]
        return {
            "count": len(ts),
            "wr_pct": round(100.0 * len(w) / len(ts), 2),
            "pnl_usd": round(sum(t.pnl_usd for t in ts), 2),
        }

    return {
        "symbol": symbol, "timeframe": timeframe, "days": days,
        "candles_processed": len(rows),
        "config": asdict(config),
        "summary": {
            "total_trades": n,
            "win_rate_pct": round(wr, 2),
            "wins": len(wins), "losses": len(losses),
            "total_pnl_usd": round(total_pnl, 2),
            "blocked_volume": switcher._blocked_volume,
            "blocked_slope": switcher._blocked_slope,
        },
        "per_side": {"LONG": side_stats(longs), "SHORT": side_stats(shorts)},
        "trades": [
            {"tool": t.tool, "side": t.side,
             "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
             "entry_bar": t.entry_bar, "exit_bar": t.exit_bar, "exit_type": t.exit_type,
             "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2)}
            for t in trades
        ],
    }


@router.get("/health")
def mode4_health():
    return {"status": "ok", "module": "mode4", "version": "0.1", "type": "trend-following"}


# ==================================================================
# AUTO-REGISTRATION HACK
# Since we can't modify app.py easily, this module registers itself
# with the FastAPI app instance via delayed polling of sys.modules.
# Triggered when mode3_backtest_endpoint imports us (see that file).
# ==================================================================
def _auto_register_with_app():
    """Poll sys.modules for FastAPI app instance, then register mode4 router."""
    import sys, time
    for _ in range(120):  # try for 60 seconds
        time.sleep(0.5)
        for mod_name, mod in list(sys.modules.items()):
            if mod is None: continue
            try:
                candidate = getattr(mod, 'app', None)
            except Exception:
                continue
            if candidate is None: continue
            if type(candidate).__name__ == 'FastAPI':
                # Check if already registered
                for r in candidate.routes:
                    if hasattr(r, 'path') and r.path.startswith('/mode4/'):
                        return  # already mounted
                try:
                    candidate.include_router(router)
                    print(f"[INIT] Mode4 auto-registered via '{mod_name}' module")
                    # Refresh OpenAPI schema
                    if hasattr(candidate, 'openapi_schema'):
                        candidate.openapi_schema = None
                    return
                except Exception as e:
                    print(f"[WARN] Mode4 include_router failed: {e}")
                    return


import threading as _threading
_threading.Thread(target=_auto_register_with_app, daemon=True).start()
