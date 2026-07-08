"""
Mode3 Backtest Endpoint - FastAPI router.
v0.25: auto-log experiments to SQLite
v0.26: trailing SL support
"""
import os
import json as jsonlib
from dataclasses import asdict
from fastapi import APIRouter, Query, Body
from typing import Optional
import sqlite3
import numpy as np
from datetime import datetime

from mode3 import Mode3Config, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3", tags=["mode3"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _ensure_experiments_table():
    """Create experiments table if not exists. v0.26 adds trailing_sl_pct column."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mode3_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            version TEXT,
            symbol TEXT,
            timeframe TEXT,
            days INTEGER,
            cap_pct REAL,
            tp_pct REAL,
            va_window INTEGER,
            entry_usd REAL,
            leverage REAL,
            fee_pct REAL,
            slippage_pct REAL,
            total_trades INTEGER,
            wins INTEGER,
            losses INTEGER,
            wr_pct REAL,
            pnl_usd REAL,
            pnl_pct REAL,
            sw_count INTEGER, sw_wr REAL, sw_pnl REAL,
            bull_count INTEGER, bull_wr REAL, bull_pnl REAL,
            bear_count INTEGER, bear_wr REAL, bear_pnl REAL,
            blocked_count INTEGER,
            final_state TEXT,
            config_json TEXT,
            notes TEXT,
            trailing_sl_pct REAL DEFAULT 0.0
        )
    """)
    # v0.26 migration: add column if table was created by older version
    try:
        conn.execute("ALTER TABLE mode3_experiments ADD COLUMN trailing_sl_pct REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass  # already exists
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_symbol_tf ON mode3_experiments(symbol, timeframe)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_days_cap_tp ON mode3_experiments(days, cap_pct, tp_pct)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_pnl ON mode3_experiments(pnl_usd)")
    conn.commit()
    conn.close()


def _log_experiment(config, result, symbol, timeframe, days):
    try:
        _ensure_experiments_table()
        s = result['summary']
        pt = result.get('per_tool', {})
        sw = pt.get('SIDEWAYS', {})
        bl = pt.get('BULL', {})
        br = pt.get('BEAR', {})
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO mode3_experiments (
                timestamp, version, symbol, timeframe, days,
                cap_pct, tp_pct, va_window, entry_usd, leverage, fee_pct, slippage_pct,
                total_trades, wins, losses, wr_pct, pnl_usd, pnl_pct,
                sw_count, sw_wr, sw_pnl,
                bull_count, bull_wr, bull_pnl,
                bear_count, bear_wr, bear_pnl,
                blocked_count, final_state, config_json, trailing_sl_pct
            ) VALUES (?,?,?,?,?, ?,?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?,?)
        """, (
            int(datetime.utcnow().timestamp()), '0.26', symbol, timeframe, days,
            config.sideways_ema_distance_cap, config.tp_pct, config.va_window,
            config.entry_usd, config.leverage, config.fee_pct_roundtrip, config.slippage_pct,
            s['total_trades'], s['wins'], s['losses'], s['win_rate_pct'],
            s['total_pnl_usd'], s['total_pnl_pct'],
            sw.get('count', 0), sw.get('wr_pct', 0), sw.get('pnl_usd', 0),
            bl.get('count', 0), bl.get('wr_pct', 0), bl.get('pnl_usd', 0),
            br.get('count', 0), br.get('wr_pct', 0), br.get('pnl_usd', 0),
            s.get('sideways_blocked_count', 0), result.get('final_state', ''),
            jsonlib.dumps(asdict(config)), config.trailing_sl_pct,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Failed to log experiment: {e}")


def load_candles_from_db(symbol, timeframe, start_ts, end_ts, db_path=None):
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
    sideways_ema_dist_cap: float = Query(0.005, ge=0.0, le=0.05),
    trailing_sl_pct: float = Query(0.0, ge=0.0, le=0.05),
    log_result: bool = Query(True),
):
    """
    Backtest Mode3 switcher.
    v0.26: trailing_sl_pct (0=disabled, e.g. 0.003 = 0.3%).
    """
    config = Mode3Config(
        va_window=va_window,
        tp_pct=tp_pct,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
        sideways_ema_distance_cap=sideways_ema_dist_cap,
        trailing_sl_pct=trailing_sl_pct,
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

    # v0.26: trailing SL stats
    trailing_exits = sum(1 for t in trades if t.exit_type == 'TRAILING_SL')
    fixed_sl_exits = sum(1 for t in trades if t.exit_type == 'SL')
    trailed_positions = sum(1 for t in trades if t.sl_trailed)

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

    result = {
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
            "sideways_blocked_count": switcher._sideways_blocked_count,
            "trailing_sl_exits": trailing_exits,
            "fixed_sl_exits": fixed_sl_exits,
            "positions_with_trailing_active": trailed_positions,
        },
        "per_tool": tool_stats,
        "trades": [
            {
                "tool": t.tool, "side": t.side,
                "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
                "entry_bar": t.entry_bar, "exit_bar": t.exit_bar,
                "exit_type": t.exit_type,
                "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2),
                "sl_level": round(t.sl_level, 2), "tp_level": round(t.tp_level, 2),
                "initial_sl": round(t.initial_sl, 2),
                "sl_trailed": t.sl_trailed,
                "ema_at_entry": round(t.ema_at_entry, 2), "ema_at_exit": round(t.ema_at_exit, 2),
            }
            for t in trades
        ],
        "final_state": switcher.state,
    }

    if log_result:
        _log_experiment(config, result, symbol, timeframe, days)

    return result


@router.get("/experiments")
def list_experiments(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    days: Optional[int] = None,
    min_pnl: Optional[float] = None,
    max_pnl: Optional[float] = None,
    order_by: str = Query("pnl_usd", regex="^(pnl_usd|wr_pct|timestamp|total_trades)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
):
    _ensure_experiments_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    q = "SELECT * FROM mode3_experiments WHERE 1=1"
    params = []
    if symbol:
        q += " AND symbol = ?"
        params.append(symbol)
    if timeframe:
        q += " AND timeframe = ?"
        params.append(timeframe)
    if days is not None:
        q += " AND days = ?"
        params.append(days)
    if min_pnl is not None:
        q += " AND pnl_usd >= ?"
        params.append(min_pnl)
    if max_pnl is not None:
        q += " AND pnl_usd <= ?"
        params.append(max_pnl)
    q += f" ORDER BY {order_by} {order.upper()} LIMIT ?"
    params.append(limit)

    rows = conn.execute(q, params).fetchall()
    conn.close()

    return {
        "count": len(rows),
        "experiments": [
            {
                "id": r["id"],
                "date": datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M UTC"),
                "symbol": r["symbol"], "tf": r["timeframe"], "days": r["days"],
                "cap%": round(r["cap_pct"]*100, 3),
                "tp%": round(r["tp_pct"]*100, 3),
                "trail%": round((r["trailing_sl_pct"] or 0)*100, 3),
                "trades": r["total_trades"], "wr%": r["wr_pct"],
                "pnl$": r["pnl_usd"],
                "sw": f"{r['sw_count']}/{r['sw_wr']}%/${r['sw_pnl']:.2f}",
                "bull": f"{r['bull_count']}/{r['bull_wr']}%/${r['bull_pnl']:.2f}",
                "bear": f"{r['bear_count']}/{r['bear_wr']}%/${r['bear_pnl']:.2f}",
                "notes": r["notes"] or "",
            }
            for r in rows
        ],
    }


@router.get("/experiments/summary")
def experiments_summary():
    _ensure_experiments_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM mode3_experiments").fetchone()[0]
    if total == 0:
        conn.close()
        return {"total_experiments": 0, "message": "No experiments logged yet"}

    top = conn.execute("""
        SELECT symbol, timeframe, days, cap_pct, tp_pct, trailing_sl_pct, total_trades, wr_pct, pnl_usd
        FROM mode3_experiments ORDER BY pnl_usd DESC LIMIT 10
    """).fetchall()

    best_per_combo = conn.execute("""
        SELECT symbol, timeframe, days,
               MAX(pnl_usd) as best_pnl,
               (SELECT cap_pct FROM mode3_experiments e2
                WHERE e2.symbol=e1.symbol AND e2.timeframe=e1.timeframe AND e2.days=e1.days
                ORDER BY pnl_usd DESC LIMIT 1) as best_cap,
               (SELECT tp_pct FROM mode3_experiments e2
                WHERE e2.symbol=e1.symbol AND e2.timeframe=e1.timeframe AND e2.days=e1.days
                ORDER BY pnl_usd DESC LIMIT 1) as best_tp,
               (SELECT trailing_sl_pct FROM mode3_experiments e2
                WHERE e2.symbol=e1.symbol AND e2.timeframe=e1.timeframe AND e2.days=e1.days
                ORDER BY pnl_usd DESC LIMIT 1) as best_trail
        FROM mode3_experiments e1
        GROUP BY symbol, timeframe, days
        ORDER BY best_pnl DESC
    """).fetchall()

    cap_tp = conn.execute("""
        SELECT days, cap_pct, tp_pct, trailing_sl_pct, pnl_usd, wr_pct, total_trades
        FROM mode3_experiments
        WHERE symbol='BTCUSDT' AND timeframe='1h'
        ORDER BY days, cap_pct, tp_pct, trailing_sl_pct
    """).fetchall()

    conn.close()

    return {
        "total_experiments": total,
        "top_10_by_pnl": [
            {"symbol": r["symbol"], "tf": r["timeframe"], "days": r["days"],
             "cap%": round(r["cap_pct"]*100, 3), "tp%": round(r["tp_pct"]*100, 3),
             "trail%": round((r["trailing_sl_pct"] or 0)*100, 3),
             "trades": r["total_trades"], "wr%": r["wr_pct"], "pnl$": r["pnl_usd"]}
            for r in top
        ],
        "best_per_combo": [
            {"symbol": r["symbol"], "tf": r["timeframe"], "days": r["days"],
             "best_cap%": round(r["best_cap"]*100, 3), "best_tp%": round(r["best_tp"]*100, 3),
             "best_trail%": round((r["best_trail"] or 0)*100, 3),
             "best_pnl$": r["best_pnl"]}
            for r in best_per_combo
        ],
        "btc_1h_grid": [
            {"days": r["days"], "cap%": round(r["cap_pct"]*100, 3),
             "tp%": round(r["tp_pct"]*100, 3),
             "trail%": round((r["trailing_sl_pct"] or 0)*100, 3),
             "pnl$": r["pnl_usd"],
             "wr%": r["wr_pct"], "trades": r["total_trades"]}
            for r in cap_tp
        ],
    }


@router.post("/experiments/note")
def add_note(id: int = Query(...), note: str = Body(...)):
    _ensure_experiments_table()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE mode3_experiments SET notes = ? WHERE id = ?", (note, id))
    conn.commit()
    conn.close()
    return {"ok": True, "id": id, "note": note}


@router.delete("/experiments/{exp_id}")
def delete_experiment(exp_id: int):
    _ensure_experiments_table()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM mode3_experiments WHERE id = ?", (exp_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "deleted_id": exp_id}


@router.get("/candles-debug")
def candles_debug(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(30, ge=1, le=365),
    va_window: int = Query(50, ge=20, le=200),
    bar_start: int = Query(0, ge=0),
    bar_end: int = Query(20, ge=1),
):
    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles_from_db(symbol, timeframe, start_ts, end_ts)

    if len(rows) == 0:
        return {"error": "no candles", "trades": []}

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, 20)

    bar_end = min(bar_end, len(rows))
    bar_start = min(bar_start, len(rows) - 1)

    candles = []
    for i in range(bar_start, bar_end):
        vah, val, poc = compute_va_at_bar(
            highs, lows, closes, volumes, i,
            va_window, 85.0, 15.0,
        )
        candles.append({
            "bar_idx": i, "open_time": rows[i][0],
            "o": round(opens[i], 2), "h": round(highs[i], 2),
            "l": round(lows[i], 2), "c": round(closes[i], 2),
            "v": round(volumes[i], 2),
            "ema20": round(ema20[i], 2),
            "vah": round(vah, 2) if vah else None,
            "val": round(val, 2) if val else None,
            "poc": round(poc, 2) if poc else None,
            "close_above_ema": bool(closes[i] > ema20[i]),
            "high_touches_ema": bool(highs[i] >= ema20[i]),
            "low_touches_ema": bool(lows[i] <= ema20[i]),
            "range_pct": round((highs[i] - lows[i]) / opens[i] * 100, 3),
        })

    return {
        "symbol": symbol, "timeframe": timeframe,
        "total_candles": len(rows), "bar_range": [bar_start, bar_end],
        "candles": candles,
    }


@router.get("/health")
def mode3_health():
    return {"status": "ok", "module": "mode3", "version": "0.26", "db_path": DB_PATH,
            "features": ["auto-log experiments", "trailing SL", "distance filter"]}
