"""
Mode4 Backtest Endpoint v0.2 — trend-following with 5 improvement options.
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


def compute_htf_alignment(rows_1h, symbol, start_ts, end_ts, ema_period=20):
    """For each 1h bar, compute the 4h EMA20 and close at that point.
    Returns two lists aligned to rows_1h length: [htf_ema], [htf_close]
    """
    rows_4h = load_candles(symbol, '4h', start_ts - 30*86400*1000, end_ts)
    if not rows_4h:
        return None, None

    closes_4h = np.array([r[4] for r in rows_4h], dtype=float)
    ema_4h = compute_ema_series(closes_4h, ema_period)
    ts_4h = [r[0] for r in rows_4h]
    ONE_4H_MS = 4 * 60 * 60 * 1000

    # For each 1h bar, find the last 4h bar that CLOSED before this 1h bar
    htf_ema_at_bar = []
    htf_close_at_bar = []
    idx_4h = 0
    for r in rows_1h:
        t_1h = r[0]
        # Find last 4h bar with open_time + 4h <= t_1h (i.e. that 4h bar has closed)
        while idx_4h + 1 < len(ts_4h) and ts_4h[idx_4h + 1] + ONE_4H_MS <= t_1h:
            idx_4h += 1
        if ts_4h[idx_4h] + ONE_4H_MS <= t_1h:
            htf_ema_at_bar.append(float(ema_4h[idx_4h]))
            htf_close_at_bar.append(float(closes_4h[idx_4h]))
        else:
            htf_ema_at_bar.append(None)
            htf_close_at_bar.append(None)

    return htf_ema_at_bar, htf_close_at_bar


@router.get("/backtest")
def backtest_mode4(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(190, ge=1, le=365),
    tp_pct: float = Query(0.010, ge=0.001, le=0.05),
    sl_pct: float = Query(0.005, ge=0.001, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    min_volume_ratio: float = Query(1.5, ge=0.0, le=5.0),
    min_slope_pct: float = Query(0.010, ge=0.0, le=0.1),
    # Improvement toggles
    confirmation_bars: int = Query(1, ge=1, le=5),
    use_htf_filter: bool = Query(False),
    use_atr_sl: bool = Query(False),
    atr_sl_mult: float = Query(1.5, ge=0.5, le=5.0),
    use_trailing_stop: bool = Query(False),
    trail_activation_pct: float = Query(0.005, ge=0.001, le=0.05),
    trail_distance_pct: float = Query(0.003, ge=0.001, le=0.05),
    use_bos_entry: bool = Query(False),
    bos_window: int = Query(20, ge=5, le=100),
):
    config = Mode4Config(
        tp_pct=tp_pct, sl_pct=sl_pct,
        entry_usd=entry_usd, leverage=leverage,
        min_volume_ratio=min_volume_ratio,
        min_slope_pct=min_slope_pct,
        confirmation_bars=confirmation_bars,
        use_htf_filter=use_htf_filter,
        use_atr_sl=use_atr_sl,
        atr_sl_mult=atr_sl_mult,
        use_trailing_stop=use_trailing_stop,
        trail_activation_pct=trail_activation_pct,
        trail_distance_pct=trail_distance_pct,
        use_bos_entry=use_bos_entry,
        bos_window=bos_window,
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

    # HTF preprocessing
    if use_htf_filter:
        htf_ema, htf_close = compute_htf_alignment(rows, symbol, start_ts, end_ts)
        switcher.htf_ema_at_bar = htf_ema
        switcher.htf_close_at_bar = htf_close

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

    exit_types = {}
    for t in trades:
        exit_types[t.exit_type] = exit_types.get(t.exit_type, 0) + 1

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
            "blocked_confirmation": switcher._blocked_confirmation,
            "blocked_htf": switcher._blocked_htf,
            "blocked_bos": switcher._blocked_bos,
        },
        "per_side": {"LONG": side_stats(longs), "SHORT": side_stats(shorts)},
        "exit_types": exit_types,
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
    return {"status": "ok", "module": "mode4", "version": "0.2", "type": "trend-following"}


# Auto-registration hack
def _auto_register_with_app():
    import sys, time
    for _ in range(120):
        time.sleep(0.5)
        for mod_name, mod in list(sys.modules.items()):
            if mod is None: continue
            try:
                candidate = getattr(mod, 'app', None)
            except Exception:
                continue
            if candidate is None: continue
            if type(candidate).__name__ == 'FastAPI':
                for r in candidate.routes:
                    if hasattr(r, 'path') and r.path.startswith('/mode4/'):
                        return
                try:
                    candidate.include_router(router)
                    if hasattr(candidate, 'openapi_schema'):
                        candidate.openapi_schema = None
                    print(f"[INIT] Mode4 auto-registered via '{mod_name}'")
                    return
                except Exception as e:
                    print(f"[WARN] Mode4 include_router failed: {e}")
                    return


import threading as _threading
_threading.Thread(target=_auto_register_with_app, daemon=True).start()
