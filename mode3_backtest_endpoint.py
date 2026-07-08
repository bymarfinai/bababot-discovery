"""
Mode3 Backtest Endpoint - FastAPI router. v0.33 (BEAR volume + MTF entry mirror).
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mode3_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            version TEXT, symbol TEXT, timeframe TEXT, days INTEGER,
            cap_pct REAL, tp_pct REAL, va_window INTEGER,
            entry_usd REAL, leverage REAL, fee_pct REAL, slippage_pct REAL,
            total_trades INTEGER, wins INTEGER, losses INTEGER, wr_pct REAL,
            pnl_usd REAL, pnl_pct REAL,
            sw_count INTEGER, sw_wr REAL, sw_pnl REAL,
            bull_count INTEGER, bull_wr REAL, bull_pnl REAL,
            bear_count INTEGER, bear_wr REAL, bear_pnl REAL,
            blocked_count INTEGER, final_state TEXT, config_json TEXT, notes TEXT
        )
    """)
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
        sw = pt.get('SIDEWAYS', {}); bl = pt.get('BULL', {}); br = pt.get('BEAR', {})
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO mode3_experiments (
                timestamp, version, symbol, timeframe, days,
                cap_pct, tp_pct, va_window, entry_usd, leverage, fee_pct, slippage_pct,
                total_trades, wins, losses, wr_pct, pnl_usd, pnl_pct,
                sw_count, sw_wr, sw_pnl, bull_count, bull_wr, bull_pnl, bear_count, bear_wr, bear_pnl,
                blocked_count, final_state, config_json
            ) VALUES (?,?,?,?,?, ?,?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?)
        """, (
            int(datetime.utcnow().timestamp()), '0.33', symbol, timeframe, days,
            config.sideways_ema_distance_cap, config.tp_pct, config.va_window,
            config.entry_usd, config.leverage, config.fee_pct_roundtrip, config.slippage_pct,
            s['total_trades'], s['wins'], s['losses'], s['win_rate_pct'],
            s['total_pnl_usd'], s['total_pnl_pct'],
            sw.get('count', 0), sw.get('wr_pct', 0), sw.get('pnl_usd', 0),
            bl.get('count', 0), bl.get('wr_pct', 0), bl.get('pnl_usd', 0),
            br.get('count', 0), br.get('wr_pct', 0), br.get('pnl_usd', 0),
            s.get('sideways_blocked_count', 0), result.get('final_state', ''),
            jsonlib.dumps(asdict(config)),
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
    cur.execute("""
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC
    """, (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall()
    conn.close()
    return rows


def compute_mtf_bull_confirm(rows_1h, rows_15m, strict=False):
    if not rows_15m: return [False] * len(rows_1h)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    highs_15m = np.array([r[2] for r in rows_15m], dtype=float)
    lows_15m = np.array([r[3] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ema_15m = compute_ema_series(closes_15m, 20)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    confirm = []
    for r in rows_1h:
        t_1h = r[0]
        ok = False
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None: continue
            basic = (lows_15m[j] <= ema_15m[j] and closes_15m[j] > ema_15m[j]
                     and closes_15m[j] > opens_15m[j])
            if not basic: continue
            if strict:
                rng = highs_15m[j] - lows_15m[j]
                if rng > 0:
                    close_pos = (closes_15m[j] - lows_15m[j]) / rng
                    if close_pos < 0.7: continue
            ok = True
            break
        confirm.append(ok)
    return confirm


def compute_mtf_bull_entry(rows_1h, rows_15m):
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    lows_15m = np.array([r[3] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ema_15m = compute_ema_series(closes_15m, 20)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    entry_closes, entry_lows = [], []
    for r in rows_1h:
        t_1h = r[0]
        fc, fl = None, None
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None: continue
            if (lows_15m[j] <= ema_15m[j] and closes_15m[j] > ema_15m[j]
                    and closes_15m[j] > opens_15m[j]):
                fc = float(closes_15m[j]); fl = float(lows_15m[j]); break
        entry_closes.append(fc); entry_lows.append(fl)
    return entry_closes, entry_lows


def compute_mtf_bear_entry(rows_1h, rows_15m):
    """
    Mirror of compute_mtf_bull_entry for BEAR (SHORT direction).
    Find first 15m candle inside 1h bar with bearish reject pattern:
      high_15m >= ema20_15m AND close_15m < ema20_15m AND close_15m < open_15m
    Return (list of close_or_None, list of high_or_None).
    """
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    highs_15m = np.array([r[2] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ema_15m = compute_ema_series(closes_15m, 20)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    entry_closes, entry_highs = [], []
    for r in rows_1h:
        t_1h = r[0]
        fc, fh = None, None
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None: continue
            if (highs_15m[j] >= ema_15m[j] and closes_15m[j] < ema_15m[j]
                    and closes_15m[j] < opens_15m[j]):
                fc = float(closes_15m[j]); fh = float(highs_15m[j]); break
        entry_closes.append(fc); entry_highs.append(fh)
    return entry_closes, entry_highs


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
    chop_max_crossings: int = Query(6, ge=0, le=20),
    trailing_sl_pct: float = Query(0.0, ge=0.0, le=0.05),
    bull_confirmation_candle: bool = Query(False),
    bull_min_ema_distance_pct: float = Query(0.0, ge=0.0, le=0.02),
    bull_min_volume_ratio: float = Query(0.0, ge=0.0, le=5.0),
    bull_disable_downtrend: bool = Query(False),
    bull_max_candle_range_pct: float = Query(0.0, ge=0.0, le=0.05),
    bull_mtf_15m_confirm: bool = Query(False),
    bull_mtf_15m_strict: bool = Query(False),
    bull_mtf_15m_entry: bool = Query(False),
    bear_min_volume_ratio: float = Query(0.0, ge=0.0, le=5.0),
    bear_mtf_15m_entry: bool = Query(False),
    log_result: bool = Query(True),
):
    config = Mode3Config(
        va_window=va_window,
        tp_pct=tp_pct,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
        sideways_ema_distance_cap=sideways_ema_dist_cap,
        chop_max_crossings=chop_max_crossings,
        trailing_sl_pct=trailing_sl_pct,
        bull_confirmation_candle=bull_confirmation_candle,
        bull_min_ema_distance_pct=bull_min_ema_distance_pct,
        bull_min_volume_ratio=bull_min_volume_ratio,
        bull_disable_downtrend=bull_disable_downtrend,
        bull_max_candle_range_pct=bull_max_candle_range_pct,
        bull_mtf_15m_confirm=bull_mtf_15m_confirm,
        bull_mtf_15m_strict=bull_mtf_15m_strict,
        bull_mtf_15m_entry=bull_mtf_15m_entry,
        bear_min_volume_ratio=bear_min_volume_ratio,
        bear_mtf_15m_entry=bear_mtf_15m_entry,
    )

    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles_from_db(symbol, timeframe, start_ts, end_ts)

    if len(rows) < config.startup_warmup_candles:
        return {"error": f"Not enough candles: got {len(rows)}, need >= {config.startup_warmup_candles}",
                "db_path_used": DB_PATH, "trades": []}

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, config.ema_period)
    switcher = Switcher(config)

    # Preprocess 15m MTF data (BULL and/or BEAR)
    if (bull_mtf_15m_confirm or bull_mtf_15m_entry or bear_mtf_15m_entry):
        rows_15m = load_candles_from_db(symbol, '15m', start_ts, end_ts)
        if rows_15m:
            if bull_mtf_15m_confirm:
                switcher.mtf_bull_confirm = compute_mtf_bull_confirm(rows, rows_15m, strict=bull_mtf_15m_strict)
            if bull_mtf_15m_entry:
                ec, el = compute_mtf_bull_entry(rows, rows_15m)
                switcher.mtf_bull_entry_close = ec
                switcher.mtf_bull_entry_low = el
            if bear_mtf_15m_entry:
                ec, eh = compute_mtf_bear_entry(rows, rows_15m)
                switcher.mtf_bear_entry_close = ec
                switcher.mtf_bear_entry_high = eh

    for i in range(len(rows)):
        vah, val, poc = compute_va_at_bar(highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low)
        switcher.process_candle(bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i], v=volumes[i],
            ema20=ema20[i], vah=vah, val=val, poc=poc)

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

    result = {
        "symbol": symbol, "timeframe": timeframe, "days": days,
        "candles_processed": len(rows),
        "config": asdict(config),
        "summary": {
            "total_trades": n,
            "win_rate_pct": round(wr, 2),
            "wins": len(wins), "losses": len(losses),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_pct": round(total_pnl_pct, 3),
            "capital_start": config.capital_usd,
            "capital_end": round(config.capital_usd + total_pnl_usd, 2),
            "sideways_blocked_count": switcher._sideways_blocked_count,
            "chop_blocked_count": switcher._chop_blocked_count,
            "bull_blocked_ema_dist": switcher._bull_blocked_ema_dist,
            "bull_blocked_volume": switcher._bull_blocked_volume,
            "bull_blocked_slope": switcher._bull_blocked_slope,
            "bull_blocked_confirm": switcher._bull_blocked_confirm,
            "bull_blocked_range": switcher._bull_blocked_range,
            "bull_blocked_mtf": switcher._bull_blocked_mtf,
            "bear_blocked_volume": switcher._bear_blocked_volume,
            "bear_blocked_mtf": switcher._bear_blocked_mtf,
        },
        "per_tool": tool_stats,
        "trades": [
            {"tool": t.tool, "side": t.side,
             "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
             "entry_bar": t.entry_bar, "exit_bar": t.exit_bar, "exit_type": t.exit_type,
             "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2),
             "sl_level": round(t.sl_level, 2), "tp_level": round(t.tp_level, 2),
             "sl_distance_pct": round(abs(t.entry_price - t.sl_level) / t.entry_price * 100, 3),
             "ema_at_entry": round(t.ema_at_entry, 2), "ema_at_exit": round(t.ema_at_exit, 2)}
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
    if symbol: q += " AND symbol = ?"; params.append(symbol)
    if timeframe: q += " AND timeframe = ?"; params.append(timeframe)
    if days is not None: q += " AND days = ?"; params.append(days)
    if min_pnl is not None: q += " AND pnl_usd >= ?"; params.append(min_pnl)
    if max_pnl is not None: q += " AND pnl_usd <= ?"; params.append(max_pnl)
    q += f" ORDER BY {order_by} {order.upper()} LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {
        "count": len(rows),
        "experiments": [
            {"id": r["id"],
             "date": datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M UTC"),
             "symbol": r["symbol"], "tf": r["timeframe"], "days": r["days"],
             "cap%": round(r["cap_pct"]*100, 3), "tp%": round(r["tp_pct"]*100, 3),
             "trades": r["total_trades"], "wr%": r["wr_pct"], "pnl$": r["pnl_usd"],
             "sw": f"{r['sw_count']}/{r['sw_wr']}%/${r['sw_pnl']:.2f}",
             "bull": f"{r['bull_count']}/{r['bull_wr']}%/${r['bull_pnl']:.2f}",
             "bear": f"{r['bear_count']}/{r['bear_wr']}%/${r['bear_pnl']:.2f}",
             "notes": r["notes"] or ""} for r in rows
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
        return {"total_experiments": 0}
    top = conn.execute("""
        SELECT symbol, timeframe, days, cap_pct, tp_pct, total_trades, wr_pct, pnl_usd
        FROM mode3_experiments ORDER BY pnl_usd DESC LIMIT 10
    """).fetchall()
    conn.close()
    return {
        "total_experiments": total,
        "top_10_by_pnl": [
            {"symbol": r["symbol"], "tf": r["timeframe"], "days": r["days"],
             "cap%": round(r["cap_pct"]*100, 3), "tp%": round(r["tp_pct"]*100, 3),
             "trades": r["total_trades"], "wr%": r["wr_pct"], "pnl$": r["pnl_usd"]}
            for r in top
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


@router.get("/health")
def mode3_health():
    return {"status": "ok", "module": "mode3", "version": "0.33", "db_path": DB_PATH,
            "features": ["chop_filter", "trailing_sl", "bull_filters", "bull_mtf_entry", "bear_volume", "bear_mtf_entry"]}
