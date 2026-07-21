"""BBC Sweep Endpoint — batch parameter sweep with DB storage.

POST /mode3_bbc/sweep — queue sweep job with parameter grid
GET  /mode3_bbc/sweep/results — query results with filters
GET  /mode3_bbc/sweep/status — check job progress

Results stored in bbc_sweep_results table for dashboard consumption.
"""
import os, json, time, hashlib, sqlite3
from datetime import datetime
from dataclasses import asdict
from fastapi import APIRouter, Query, Body
from typing import Optional, List
import numpy as np
from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3_bbc/sweep", tags=["bbc_sweep"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _init_sweep_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS bbc_sweep_results (
        id TEXT PRIMARY KEY,
        created_at TEXT,
        symbol TEXT, timeframe TEXT, days INTEGER,
        ema_period INTEGER, tp_pct REAL, sl_pct REAL,
        bull_body REAL, bear_body REAL, sw_body REAL,
        direct_transition INTEGER, trailing_ema INTEGER,
        trailing_ema_period INTEGER, trailing_ema_max_tp REAL,
        total_trades INTEGER, win_rate REAL, total_pnl REAL,
        bull_trades INTEGER, bull_wr REAL, bull_pnl REAL,
        bear_trades INTEGER, bear_wr REAL, bear_pnl REAL,
        sw_trades INTEGER, sw_wr REAL, sw_pnl REAL,
        max_drawdown REAL, max_streak INTEGER,
        config_json TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS bbc_sweep_jobs (
        id TEXT PRIMARY KEY,
        created_at TEXT, status TEXT,
        total_combos INTEGER, completed INTEGER,
        params_json TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sweep_symbol ON bbc_sweep_results(symbol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sweep_pnl ON bbc_sweep_results(total_pnl DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sweep_wr ON bbc_sweep_results(win_rate DESC)")
    conn.commit(); conn.close()

def _make_id(symbol, timeframe, days, config):
    key = f"{symbol}_{timeframe}_{days}_{json.dumps(config, sort_keys=True)}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

def _load_candles(symbol, timeframe, days):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ts = now_ms - (days * 86400 * 1000)
    cur.execute("SELECT open_time, open, high, low, close, volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC",
        (symbol, timeframe, start_ts, now_ms))
    rows = cur.fetchall(); conn.close(); return rows, start_ts, now_ms

def _run_single_backtest(symbol, timeframe, days, params):
    rows, start_ts, end_ts = _load_candles(symbol, timeframe, days)
    config = Mode3BBCConfig(**{k: v for k, v in params.items() if hasattr(Mode3BBCConfig, k)})
    if len(rows) < config.startup_warmup_candles:
        return None
    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)
    ema = compute_ema_series(closes, config.ema_period)
    vahs, vals, pocs = [], [], []
    for i in range(len(rows)):
        vah, val, poc = compute_va_at_bar(highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low)
        vahs.append(vah); vals.append(val); pocs.append(poc)
    switcher = Switcher(config)
    if config.trailing_ema_enabled:
        switcher.trailing_ema_series = compute_ema_series(closes, config.trailing_ema_period)
    if config.bull_mtf_15m_enabled or config.bear_mtf_15m_enabled or config.sideways_mtf_15m_enabled:
        from mode3_bbc_endpoint import compute_mtf_bull_entry, compute_mtf_bear_entry, compute_mtf_sideways_entry
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT open_time, open, high, low, close, volume FROM klines WHERE symbol=? AND timeframe='15m' AND open_time>=? AND open_time<? ORDER BY open_time ASC",
            (symbol, start_ts, end_ts))
        rows_15m = cur.fetchall(); conn.close()
        if rows_15m:
            if config.bull_mtf_15m_enabled:
                ec, el = compute_mtf_bull_entry(rows, rows_15m)
                switcher.mtf_bull_entry_close = ec; switcher.mtf_bull_entry_low = el
            if config.bear_mtf_15m_enabled:
                ec, eh = compute_mtf_bear_entry(rows, rows_15m)
                switcher.mtf_bear_entry_close = ec; switcher.mtf_bear_entry_high = eh
            if config.sideways_mtf_15m_enabled:
                sc, sh, lc, ll = compute_mtf_sideways_entry(rows, rows_15m, vahs, vals)
                switcher.mtf_sideways_short_entry_close = sc; switcher.mtf_sideways_short_entry_high = sh
                switcher.mtf_sideways_long_entry_close = lc; switcher.mtf_sideways_long_entry_low = ll
    for i in range(len(rows)):
        switcher.process_candle(bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i],
            ema20=ema[i], vah=vahs[i], val=vals[i], poc=pocs[i])
    trades = switcher.trades
    n = len(trades)
    if n == 0: return None
    wins = sum(1 for t in trades if t.pnl_usd > 0)
    total_pnl = sum(t.pnl_usd for t in trades)
    equity = 0; peak_eq = 0; max_dd = 0
    max_streak = 0; cur_streak = 0
    for t in trades:
        equity += t.pnl_usd
        if equity > peak_eq: peak_eq = equity
        dd = peak_eq - equity
        if dd > max_dd: max_dd = dd
        if t.pnl_usd <= 0: cur_streak += 1; max_streak = max(max_streak, cur_streak)
        else: cur_streak = 0
    tool_data = {}
    for tool in ['BULL', 'BEAR', 'SIDEWAYS']:
        tt = [t for t in trades if t.tool == tool]
        if tt:
            tw = sum(1 for t in tt if t.pnl_usd > 0)
            tool_data[tool] = {'count': len(tt), 'wr': round(100*tw/len(tt), 2), 'pnl': round(sum(t.pnl_usd for t in tt), 2)}
        else:
            tool_data[tool] = {'count': 0, 'wr': 0, 'pnl': 0}
    return {
        'total_trades': n, 'win_rate': round(100*wins/n, 2), 'total_pnl': round(total_pnl, 2),
        'bull': tool_data['BULL'], 'bear': tool_data['BEAR'], 'sw': tool_data['SIDEWAYS'],
        'max_drawdown': round(max_dd, 2), 'max_streak': max_streak
    }


@router.post("")
def start_sweep(
    symbols: List[str] = Body(default=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]),
    timeframe: str = Body(default="1h"),
    days: int = Body(default=925),
    ema_periods: List[int] = Body(default=[7, 10, 14, 20]),
    tp_pcts: List[float] = Body(default=[0.007, 0.008, 0.009, 0.01, 0.011, 0.012, 0.013]),
    sl_pcts: List[float] = Body(default=[0.008, 0.01, 0.013, 0.015, 0.02]),
    bull_bodies: List[float] = Body(default=[0.4, 0.5, 0.6, 0.7]),
    bear_bodies: List[float] = Body(default=[0.4, 0.5, 0.6, 0.7]),
    trailing_modes: List[bool] = Body(default=[False]),
):
    """Start batch sweep. Validates symbols have data in DB first."""
    _init_sweep_tables()

    # ── VALIDATE: check which symbols actually have data ──
    conn = sqlite3.connect(DB_PATH)
    valid_symbols = []
    missing_symbols = []
    for sym in symbols:
        count = conn.execute(
            "SELECT COUNT(*) FROM klines WHERE symbol=? AND timeframe=?",
            (sym, timeframe)
        ).fetchone()[0]
        if count >= 100:
            valid_symbols.append(sym)
        else:
            missing_symbols.append({"symbol": sym, "candles": count})
    conn.close()

    if not valid_symbols:
        return {
            "error": f"No data in DB for ANY of the requested symbols",
            "missing": missing_symbols,
            "hint": "Fetch candle data first via data_fetcher or add pairs to DB"
        }

    # ── Generate combos (only for valid symbols) ──
    combos = []
    for sym in valid_symbols:
        for ema in ema_periods:
            for tp in tp_pcts:
                for sl in sl_pcts:
                    for bb in bull_bodies:
                        for rb in bear_bodies:
                            for trail in trailing_modes:
                                combos.append({
                                    'symbol': sym, 'timeframe': timeframe, 'days': days,
                                    'ema_period': ema, 'tp_pct': tp, 'sl_pct': sl,
                                    'bull_body_ratio_min': bb, 'bear_body_ratio_min': rb,
                                    'direct_transition_enabled': True, 'sideways_body_ratio_min': 0.6,
                                    'trailing_ema_enabled': trail,
                                    'trailing_ema_period': 5 if trail else 7,
                                    'trailing_ema_max_tp_pct': 0.05 if trail else 0.0,
                                })
    job_id = hashlib.md5(f"{time.time()}_{len(combos)}".encode()).hexdigest()[:12]
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO bbc_sweep_jobs (id, created_at, status, total_combos, completed, params_json) VALUES (?,?,?,?,?,?)",
        (job_id, datetime.utcnow().isoformat(), 'queued', len(combos), 0, json.dumps(combos)))
    conn.commit(); conn.close()

    result = {"job_id": job_id, "total_combos": len(combos), "status": "queued",
              "symbols_valid": valid_symbols}
    if missing_symbols:
        result["warning"] = f"Skipped {len(missing_symbols)} symbols with no data"
        result["missing"] = missing_symbols
    return result


@router.get("/run/{job_id}")
def run_sweep_batch(job_id: str, batch_size: int = Query(default=10, ge=1, le=50)):
    _init_sweep_tables()
    conn = sqlite3.connect(DB_PATH)
    job = conn.execute("SELECT status, total_combos, completed, params_json FROM bbc_sweep_jobs WHERE id=?", (job_id,)).fetchone()
    if not job: conn.close(); return {"error": "Job not found"}
    status, total, completed, params_json = job
    if status == 'done': conn.close(); return {"status": "done", "completed": completed, "total": total}
    combos = json.loads(params_json)
    remaining = combos[completed:]
    batch = remaining[:batch_size]
    results_added = 0
    for params in batch:
        sym = params.pop('symbol'); tf = params.pop('timeframe'); d = params.pop('days')
        result = _run_single_backtest(sym, tf, d, params)
        if result:
            rid = _make_id(sym, tf, d, params)
            try:
                conn.execute("""INSERT OR REPLACE INTO bbc_sweep_results
                    (id, created_at, symbol, timeframe, days, ema_period, tp_pct, sl_pct,
                     bull_body, bear_body, sw_body, direct_transition, trailing_ema,
                     trailing_ema_period, trailing_ema_max_tp,
                     total_trades, win_rate, total_pnl,
                     bull_trades, bull_wr, bull_pnl,
                     bear_trades, bear_wr, bear_pnl,
                     sw_trades, sw_wr, sw_pnl,
                     max_drawdown, max_streak, config_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rid, datetime.utcnow().isoformat(), sym, tf, d,
                     params.get('ema_period', 20), params.get('tp_pct', 0.013), params.get('sl_pct', 0.013),
                     params.get('bull_body_ratio_min', 0.5), params.get('bear_body_ratio_min', 0.6),
                     params.get('sideways_body_ratio_min', 0.6),
                     1 if params.get('direct_transition_enabled') else 0,
                     1 if params.get('trailing_ema_enabled') else 0,
                     params.get('trailing_ema_period', 7), params.get('trailing_ema_max_tp_pct', 0.0),
                     result['total_trades'], result['win_rate'], result['total_pnl'],
                     result['bull']['count'], result['bull']['wr'], result['bull']['pnl'],
                     result['bear']['count'], result['bear']['wr'], result['bear']['pnl'],
                     result['sw']['count'], result['sw']['wr'], result['sw']['pnl'],
                     result['max_drawdown'], result['max_streak'],
                     json.dumps(params)))
                results_added += 1
            except Exception as e:
                print(f"[SWEEP] Error saving result: {e}")
        completed += 1
    new_status = 'done' if completed >= total else 'running'
    conn.execute("UPDATE bbc_sweep_jobs SET status=?, completed=? WHERE id=?", (new_status, completed, job_id))
    conn.commit(); conn.close()
    return {"status": new_status, "completed": completed, "total": total, "batch_processed": len(batch), "results_added": results_added}


@router.get("/status/{job_id}")
def sweep_status(job_id: str):
    _init_sweep_tables()
    conn = sqlite3.connect(DB_PATH)
    job = conn.execute("SELECT status, total_combos, completed, created_at FROM bbc_sweep_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job: return {"error": "Job not found"}
    return {"job_id": job_id, "status": job[0], "total": job[1], "completed": job[2], "created_at": job[3],
            "progress_pct": round(100 * job[2] / job[1], 1) if job[1] > 0 else 0}


@router.get("/results")
def sweep_results(
    symbol: Optional[str] = Query(None),
    min_wr: float = Query(0, ge=0, le=100),
    min_pnl: float = Query(-99999),
    min_trades: int = Query(0, ge=0),
    ema_period: Optional[int] = Query(None),
    sort_by: str = Query("total_pnl", regex="^(total_pnl|win_rate|total_trades|max_drawdown|bull_wr|bear_wr)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    _init_sweep_tables()
    conn = sqlite3.connect(DB_PATH)
    where = ["win_rate >= ?", "total_pnl >= ?", "total_trades >= ?"]
    params = [min_wr, min_pnl, min_trades]
    if symbol:
        where.append("symbol = ?"); params.append(symbol)
    if ema_period:
        where.append("ema_period = ?"); params.append(ema_period)
    where_clause = " AND ".join(where)
    sort_dir = "DESC" if sort_by in ("total_pnl", "win_rate", "total_trades", "bull_wr", "bear_wr") else "ASC"

    count = conn.execute(f"SELECT COUNT(*) FROM bbc_sweep_results WHERE {where_clause}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT id, symbol, ema_period, tp_pct, sl_pct, bull_body, bear_body,
            trailing_ema, trailing_ema_period, trailing_ema_max_tp,
            total_trades, win_rate, total_pnl,
            bull_trades, bull_wr, bull_pnl,
            bear_trades, bear_wr, bear_pnl,
            sw_trades, sw_wr, sw_pnl,
            max_drawdown, max_streak
        FROM bbc_sweep_results WHERE {where_clause}
        ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?""",
        params + [limit, offset]).fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0], "symbol": r[1], "ema_period": r[2],
            "tp_pct": r[3], "sl_pct": r[4], "bull_body": r[5], "bear_body": r[6],
            "trailing_ema": bool(r[7]), "trailing_ema_period": r[8], "trailing_ema_max_tp": r[9],
            "total_trades": r[10], "win_rate": r[11], "total_pnl": r[12],
            "bull_trades": r[13], "bull_wr": r[14], "bull_pnl": r[15],
            "bear_trades": r[16], "bear_wr": r[17], "bear_pnl": r[18],
            "sw_trades": r[19], "sw_wr": r[20], "sw_pnl": r[21],
            "max_drawdown": r[22], "max_streak": r[23],
        })
    return {"total_results": count, "showing": len(results), "offset": offset, "results": results}


@router.delete("/results")
def clear_results():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM bbc_sweep_results")
    conn.execute("DELETE FROM bbc_sweep_jobs")
    conn.commit(); conn.close()
    return {"status": "cleared"}
