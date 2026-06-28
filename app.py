"""
BabaBot AI Strategy Discovery — Backtesting API
FastAPI server with /backtest + /fetch-data endpoints.

Updated: Support custom pairs + timeframes in /fetch-data via ccxt.
"""

import os
import threading
import sqlite3
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester, StrategyConfig, BacktestResult, ENTRY_LOGICS, calc_correlation, run_feature_study, run_marthias_study, test_ai_rules, bootstrap_validate_rules, run_sltp_optimization, run_paper_test, DCAConfig, backtest_dca, backtest_deret_statistik, analyze_deviation_clusters
# REMOVED: live_bot.py (Iron Legion) and dca_bot.py — superseded by baret_live.py
from baret_bot import start_baret, stop_baret, baret_status, get_baret_log
from baret_live import start_baret_live, stop_baret_live, baret_live_status, get_baret_live_log, close_position, close_all_positions, start_account_bot, stop_account_bot, account_bot_status
from ultron_engine import ultron_status, get_ultron_log, manual_analyze, clear_pair_skip, clear_hour_skip, clear_buffer_adjustment
from tick_discovery import (
        start_tick_discovery, stop_tick_discovery, get_discovery_status, get_discovery_log,
        extract_tick_events, analyze_tick_stats,
        start_sweep_engine, stop_sweep_engine, get_sweep_status,
        pause_sweep_engine, resume_sweep_engine,
        profile_winning_combo,
        cluster_levels, _load_data as td_load_data, DB_PATH as TD_DB_PATH,
    )
app = FastAPI(title="BabaBot Backtesting API", version="1.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer(auto_error=False)

API_TOKEN = os.environ.get("BACKTEST_API_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

bt = Backtester(db_path=DB_PATH)

fetch_state = {"status": "idle", "days": 0, "progress": "", "total_candles": 0, "error": None}

ALL_PAIRS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "PEPEUSDT"]
ALL_TIMEFRAMES = ["5m", "15m", "1h", "4h"]


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None
    indicators: dict = {}
    sl_pct: float = 0.6
    tp_pct: float = 1.2
    fee_pct: float = 0.10
    slippage_pct: float = 0.01
    initial_capital: float = 10000.0
    position_size_pct: float = 10.5
    days: int = 90
    train_pct: float = 75.0
    start_date: Optional[str] = None  # "2024-01-01"
    end_date: Optional[str] = None    # "2024-12-31"
    include_equity: bool = False      # Stage 10: return equity curve data
    direction: str = "both"
    session_filter: Optional[str] = None
    trend_filter: Optional[str] = None
    volatility_filter: Optional[str] = None
    volume_filter: Optional[str] = None
    regime_filter: Optional[str] = None
    use_atr_sl_tp: bool = False
    sl_atr_mult: float = 1.5
    tp_atr_mult: float = 3.0

class BatchBacktestRequest(BaseModel):
    configs: list[BacktestRequest]

class CorrelationRequest(BaseModel):
    configs: list[BacktestRequest]
    labels: Optional[list[str]] = None

class FetchDataRequest(BaseModel):
    days: int = 365
    pairs: Optional[list[str]] = None
    timeframes: Optional[list[str]] = None


# ============================================================
# AUTH
# ============================================================

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_TOKEN:
        return True
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return True


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():
    return {
        "service": "BabaBot Backtesting API",
        "version": "1.2.0",
        "status": "running",
        "endpoints": ["/backtest", "/backtest/batch", "/backtest/feature-study", "/backtest/marthias-study", "/health", "/data/status", "/strategies", "/fetch-data", "/fetch-status"]
    }

@app.get("/data/list-files")
def list_volume_files():
    """List all files on the data volume with sizes"""
    try:
        import os
        data_dir = os.path.dirname(DB_PATH) or "."
        files = []
        for f in os.listdir(data_dir):
            fp = os.path.join(data_dir, f)
            if os.path.isfile(fp):
                size_mb = round(os.path.getsize(fp) / 1024 / 1024, 2)
                files.append({"file": f, "size_mb": size_mb})
        files.sort(key=lambda x: x["size_mb"], reverse=True)
        return {"ok": True, "dir": data_dir, "files": files}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/data/db-size")
def db_size():
    """Check database table sizes and disk usage"""
    try:
        import os
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        tables = []
        for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            table = row[0]
            count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            tables.append({"table": table, "rows": count})
        tables.sort(key=lambda x: x["rows"], reverse=True)
        tf_breakdown = []
        try:
            for row in c.execute("SELECT timeframe, COUNT(*), COUNT(DISTINCT symbol) FROM klines GROUP BY timeframe ORDER BY COUNT(*) DESC"):
                tf_breakdown.append({"timeframe": row[0], "rows": row[1], "pairs": row[2]})
        except: pass
        db_size_mb = round(os.path.getsize(DB_PATH) / 1024 / 1024, 1)
        conn.close()
        return {"ok": True, "db_size_mb": db_size_mb, "tables": tables, "klines_by_tf": tf_breakdown}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/data/vacuum")
def vacuum_db():
    """Reclaim disk space after deletes"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")
        conn.close()
        import os
        size_mb = round(os.path.getsize(DB_PATH) / 1024 / 1024, 1)
        return {"ok": True, "db_size_mb": size_mb}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/health")
def health():
    db_ok = Path(DB_PATH).exists()
    candle_count = 0
    if db_ok:
        try:
            conn = sqlite3.connect(DB_PATH)
            candle_count = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            conn.close()
        except:
            pass
    return {
        "status": "ok",
        "db_exists": db_ok,
        "total_candles": candle_count,
        "db_path": DB_PATH
    }

@app.get("/data/status")
def data_status():
    """Per pair × TF candle availability — used by dashboard Data Health tab."""
    if not Path(DB_PATH).exists():
        return {"status": "error", "error": "database not found"}
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Per pair × TF breakdown
        rows = conn.execute("""
            SELECT symbol, timeframe,
                   COUNT(*) as candles,
                   MIN(open_time) as first_ts,
                   MAX(open_time) as last_ts
            FROM klines
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe
        """).fetchall()
        
        pairs = {}
        total_candles = 0
        for symbol, tf, candles, first_ts, last_ts in rows:
            if symbol not in pairs:
                pairs[symbol] = {}
            days_available = round((last_ts - first_ts) / 86_400_000, 1) if last_ts and first_ts else 0
            pairs[symbol][tf] = {
                "candles": candles,
                "first_date": time.strftime("%Y-%m-%d", time.gmtime(first_ts / 1000)) if first_ts else None,
                "last_date": time.strftime("%Y-%m-%d", time.gmtime(last_ts / 1000)) if last_ts else None,
                "days": days_available,
            }
            total_candles += candles
        
        # Last fetch timestamp (most recent candle across all data)
        last_row = conn.execute("SELECT MAX(open_time) FROM klines").fetchone()
        last_fetch = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(last_row[0] / 1000)) if last_row and last_row[0] else None
        
        # Flat breakdown array (for dashboard compatibility)
        breakdown = []
        for symbol, tfs in pairs.items():
            for tf, info in tfs.items():
                breakdown.append({"symbol": symbol, "timeframe": tf, "candles": info["candles"]})
        
        return {
            "status": "ok",
            "total_candles": total_candles,
            "last_fetch": last_fetch,
            "pairs": pairs,
            "breakdown": breakdown,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()

@app.get("/strategies")
def list_strategies():
    return {
        "entry_logics": ENTRY_LOGICS,
        "multi_entry": {
            "supported": True,
            "description": "Set entry_logic_2 for AND confirmation (both must fire within 3 candles)",
            "example": {"entry_logic": "supertrend_flip", "entry_logic_2": "macd_cross"}
        },
        "supported_pairs": ALL_PAIRS,
        "supported_timeframes": ALL_TIMEFRAMES,
        "directions": ["long", "short", "both"],
        "filters": {
            "session_filter": ["asia", "london", "ny", "london_ny"],
            "trend_filter": ["ema200_long", "ema200_short", "adx_direction"],
            "volatility_filter": ["atr_min", "atr_max", "bb_squeeze"],
            "volume_filter": ["volume_spike", "taker_buy"],
            "regime_filter": ["trending", "ranging"],
        },
        "defaults": {
            "fee_pct": 0.10,
            "initial_capital": 10000,
            "position_size_pct": 10.5,
            "sl_range": "0.4-0.8%",
            "tp_min": "1.0%"
        }
    }


# ============================================================
# DATA FETCHER — data.binance.vision (bulk CSV download)
# ============================================================

def fetch_via_binance_vision(days: int, pairs: list[str], timeframes: list[str], db_path: str):
    """
    Fetch OHLCV from data.binance.vision (bulk CSV downloads).
    Same approach as data_fetcher.py but supports custom pairs/timeframes.
    URL: https://data.binance.vision/data/futures/um/daily/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{DATE}.zip
    """
    global fetch_state
    import requests
    import zipfile
    import csv
    import io
    from datetime import datetime, timedelta
    
    total_fetched = 0
    total_tasks = len(pairs) * len(timeframes)
    completed = 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS klines (
            symbol TEXT,
            timeframe TEXT,
            open_time INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            close_time INTEGER,
            quote_volume REAL,
            trades INTEGER,
            taker_buy_volume REAL,
            taker_buy_quote_volume REAL,
            PRIMARY KEY (symbol, timeframe, open_time)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_klines_sym_tf ON klines(symbol, timeframe)")
    conn.commit()
    
    # Generate date list
    end_date = datetime.utcnow() - timedelta(days=1)  # yesterday (today might not be complete)
    start_date = end_date - timedelta(days=days)
    
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    
    base_url = "https://data.binance.vision/data/futures/um/daily/klines"
    
    for pair in pairs:
        for tf in timeframes:
            completed += 1
            pair_candles = 0
            skipped = 0
            errors = 0
            
            for i, date_str in enumerate(dates):
                fetch_state["progress"] = f"[{completed}/{total_tasks}] {pair} {tf} — day {i+1}/{len(dates)}"
                
                # Check if date already exists (skip logic)
                date_ts_start = int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)
                date_ts_end = date_ts_start + 86400000  # +24h in ms
                
                existing = cursor.execute(
                    "SELECT COUNT(*) FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?",
                    (pair, tf, date_ts_start, date_ts_end)
                ).fetchone()[0]
                
                if existing > 0:
                    skipped += 1
                    continue
                
                # Download ZIP
                zip_url = f"{base_url}/{pair}/{tf}/{pair}-{tf}-{date_str}.zip"
                try:
                    r = requests.get(zip_url, timeout=30)
                    if r.status_code == 404:
                        # No data for this date (pair might not exist yet)
                        continue
                    if r.status_code != 200:
                        errors += 1
                        continue
                    
                    # Extract CSV from ZIP
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    csv_name = z.namelist()[0]
                    csv_data = z.read(csv_name).decode("utf-8")
                    
                    # Parse CSV — Binance klines CSV format:
                    # open_time, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_vol, taker_buy_quote_vol, ignore
                    rows = []
                    reader = csv.reader(io.StringIO(csv_data))
                    for row in reader:
                        if len(row) < 11:
                            continue
                        try:
                            rows.append((
                                pair, tf,
                                int(row[0]),       # open_time
                                float(row[1]),     # open
                                float(row[2]),     # high
                                float(row[3]),     # low
                                float(row[4]),     # close
                                float(row[5]),     # volume
                                int(row[6]),       # close_time
                                float(row[7]),     # quote_volume
                                int(row[8]),       # trades
                                float(row[9]),     # taker_buy_volume
                                float(row[10]),    # taker_buy_quote_volume
                            ))
                        except (ValueError, IndexError):
                            continue
                    
                    if rows:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO klines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            rows
                        )
                        conn.commit()
                        pair_candles += len(rows)
                        total_fetched += len(rows)
                        fetch_state["total_candles"] = total_fetched
                    
                except Exception as e:
                    errors += 1
                    if errors > 10:
                        fetch_state["progress"] = f"[{completed}/{total_tasks}] {pair} {tf} — too many errors, skipping"
                        break
                    continue
                
                time.sleep(0.1)  # gentle rate limit
            
            fetch_state["progress"] = f"[{completed}/{total_tasks}] {pair} {tf} done — {pair_candles:,} new, {skipped} skipped"
    
    conn.close()
    return total_fetched


# ============================================================
# FETCH-DATA ENDPOINTS
# ============================================================

@app.post("/fetch-data")
def fetch_data(req: FetchDataRequest):
    """
    Trigger data fetch. Supports custom pairs and timeframes.
    If pairs/timeframes not specified, uses defaults.
    """
    global fetch_state
    
    if fetch_state["status"] == "running":
        return {"status": "already_running", "days": fetch_state["days"], "message": "Fetch already in progress. Check /fetch-status"}
    
    pairs = req.pairs or ALL_PAIRS
    timeframes = req.timeframes or ALL_TIMEFRAMES
    
    fetch_state = {"status": "running", "days": req.days, "progress": "Starting...", "total_candles": 0, "error": None}
    
    def run_fetch():
        global fetch_state
        try:
            if req.pairs or req.timeframes:
                # Custom pairs/timeframes — use direct Binance API
                total = fetch_via_binance_vision(req.days, pairs, timeframes, DB_PATH)
                fetch_state["status"] = "done"
                fetch_state["progress"] = f"Completed fetching {req.days} days data — {total:,} candles"
            else:
                # Default — use existing data_fetcher for backward compatibility
                try:
                    from data_fetcher import fetch_all
                    fetch_all(days=req.days, db_path=DB_PATH)
                    fetch_state["status"] = "done"
                    fetch_state["progress"] = f"Completed fetching {req.days} days data"
                except ImportError:
                    # data_fetcher not available, fallback to direct API
                    total = fetch_via_binance_vision(req.days, ALL_PAIRS, ALL_TIMEFRAMES, DB_PATH)
                    fetch_state["status"] = "done"
                    fetch_state["progress"] = f"Completed fetching {req.days} days data — {total:,} candles"
        except Exception as e:
            fetch_state["status"] = "error"
            fetch_state["progress"] = f"Error: {str(e)}"
            fetch_state["error"] = str(e)
    
    threading.Thread(target=run_fetch, daemon=True).start()
    
    return {
        "status": "fetching",
        "days": req.days,
        "pairs": pairs,
        "timeframes": timeframes,
        "message": f"Fetching {req.days} days for {len(pairs)} pairs x {len(timeframes)} TFs in background. Check /fetch-status for progress."
    }

@app.get("/fetch-status")
def fetch_status_endpoint():
    result = {
        "fetch_state": fetch_state,
        "total_candles": 0,
        "breakdown": []
    }
    
    if Path(DB_PATH).exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            total = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            pairs = conn.execute("""
                SELECT symbol, timeframe, COUNT(*) as cnt,
                       MIN(open_time) as first_ts,
                       MAX(open_time) as last_ts
                FROM klines 
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """).fetchall()
            conn.close()
            
            result["total_candles"] = total
            result["breakdown"] = [
                {
                    "symbol": r[0],
                    "timeframe": r[1],
                    "candles": r[2],
                    "first_date": r[3],
                    "last_date": r[4]
                } for r in pairs
            ]
        except Exception as e:
            result["error"] = str(e)
    
    return result


# ============================================================
# BACKTEST ENDPOINTS
# ============================================================

@app.post("/backtest")
def run_backtest(req: BacktestRequest, _=Security(verify_token)):
    default_indicators = {
        "ema_fast": 9, "ema_slow": 21,
        "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
        "bb_period": 20, "bb_std": 2.0,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "atr_period": 14, "stoch_k": 14, "stoch_d": 3, "adx_period": 14,
    }
    merged_indicators = {**default_indicators, **req.indicators}
    
    config = StrategyConfig(
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        indicators=merged_indicators,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        fee_pct=req.fee_pct,
        slippage_pct=req.slippage_pct,
        initial_capital=req.initial_capital,
        position_size_pct=req.position_size_pct,
        days=req.days,
        train_pct=req.train_pct,
        start_date=req.start_date,
        end_date=req.end_date,
        direction=req.direction,
        session_filter=req.session_filter,
        trend_filter=req.trend_filter,
        volatility_filter=req.volatility_filter,
        volume_filter=req.volume_filter,
        regime_filter=req.regime_filter,
        use_atr_sl_tp=req.use_atr_sl_tp,
        sl_atr_mult=req.sl_atr_mult,
        tp_atr_mult=req.tp_atr_mult,
    )
    
    result = bt.run(config)
    d = result.to_dict()
    if not req.include_equity:
        d.pop("equity_curve", None)
    return d

@app.post("/backtest/batch")
def run_batch_backtest(req: BatchBacktestRequest, _=Security(verify_token)):
    if len(req.configs) > 50:
        raise HTTPException(status_code=400, detail="Max 50 configs per batch request")
    
    results = []
    for r in req.configs:
        # Normalize entry_logic — lowercase + validate
        if r.entry_logic:
            r.entry_logic = r.entry_logic.lower()
        if r.entry_logic_2:
            r.entry_logic_2 = r.entry_logic_2.lower()
        
        # Skip if entry_logic not in backtester
        if r.entry_logic and r.entry_logic not in ENTRY_LOGICS:
            results.append({
                "symbol": r.symbol, "timeframe": r.timeframe,
                "entry_logic": r.entry_logic, "sl_pct": r.sl_pct, "tp_pct": r.tp_pct,
                "win_rate": 0, "profit_per_day": 0, "total_trades": 0,
                "status": "no_trades", "error": f"unknown entry_logic: {r.entry_logic}",
                "long_trades": 0, "short_trades": 0, "meets_criteria": False,
            })
            continue
        if r.entry_logic_2 and r.entry_logic_2 not in ENTRY_LOGICS:
            results.append({
                "symbol": r.symbol, "timeframe": r.timeframe,
                "entry_logic": r.entry_logic, "entry_logic_2": r.entry_logic_2,
                "sl_pct": r.sl_pct, "tp_pct": r.tp_pct,
                "win_rate": 0, "profit_per_day": 0, "total_trades": 0,
                "status": "no_trades", "error": f"unknown entry_logic_2: {r.entry_logic_2}",
                "long_trades": 0, "short_trades": 0, "meets_criteria": False,
            })
            continue
        
        single_result = run_backtest(r)
        single_result["sl_pct"] = r.sl_pct
        single_result["tp_pct"] = r.tp_pct
        single_result.pop("equity_curve", None)
        results.append(single_result)
    
    meets = [r for r in results if r.get("meets_criteria")]
    return {
        "total": len(results),
        "meets_criteria": len(meets),
        "results": results
    }


@app.post("/backtest/correlation")
def run_correlation(req: CorrelationRequest, _=Security(verify_token)):
    """
    Run multiple backtests and analyze correlation between them.
    Returns individual results + correlation matrix.
    """
    if len(req.configs) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 configs for correlation")
    if len(req.configs) > 10:
        raise HTTPException(status_code=400, detail="Max 10 configs per correlation request")
    
    # Run backtests and collect trade lists
    default_indicators = {
        "ema_fast": 9, "ema_slow": 21,
        "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
        "bb_period": 20, "bb_std": 2.0,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "atr_period": 14, "stoch_k": 14, "stoch_d": 3, "adx_period": 14,
    }
    
    all_trade_lists = []
    results = []
    labels = req.labels or []
    
    for i, r in enumerate(req.configs):
        merged_indicators = {**default_indicators, **r.indicators}
        config = StrategyConfig(
            symbol=r.symbol.upper(),
            timeframe=r.timeframe,
            entry_logic=r.entry_logic,
            entry_logic_2=r.entry_logic_2,
            indicators=merged_indicators,
            sl_pct=r.sl_pct,
            tp_pct=r.tp_pct,
            fee_pct=r.fee_pct,
            slippage_pct=r.slippage_pct,
            initial_capital=r.initial_capital,
            position_size_pct=r.position_size_pct,
            days=r.days,
            train_pct=r.train_pct,
            start_date=r.start_date,
            end_date=r.end_date,
            direction=r.direction,
            session_filter=r.session_filter,
            trend_filter=r.trend_filter,
            volatility_filter=r.volatility_filter,
            volume_filter=r.volume_filter,
            regime_filter=r.regime_filter,
            use_atr_sl_tp=r.use_atr_sl_tp,
            sl_atr_mult=r.sl_atr_mult,
            tp_atr_mult=r.tp_atr_mult,
        )
        
        # Get raw trades for correlation
        data = bt._load_data(config.symbol, config.timeframe, config.days, config.start_date, config.end_date)
        result = bt.run(config)
        results.append(result.to_dict())
        
        if data and len(data['close']) >= 100:
            from backtesting_core import precompute_indicators, get_signals, apply_filters, simulate_trades
            ind = precompute_indicators(data, config)
            signals = get_signals(data, ind, config)
            signals = apply_filters(data, ind, signals, config)
            trades = simulate_trades(data, ind, signals, config, 0)
            all_trade_lists.append(trades)
        else:
            all_trade_lists.append([])
        
        if i >= len(labels):
            labels.append(f"{config.symbol}_{config.timeframe}_{config.entry_logic}")
    
    # Run correlation analysis
    correlation = calc_correlation(all_trade_lists, labels)
    
    return {
        "results": results,
        "correlation": correlation
    }

class MultiPeriodRequest(BaseModel):
    config: BacktestRequest
    periods: list[dict] = []  # [{"label": "2024", "start": "2024-01-01", "end": "2024-12-31"}, ...]

@app.post("/backtest/multiperiod")
def run_multiperiod(req: MultiPeriodRequest, _=Security(verify_token)):
    """
    Run one strategy config across multiple time periods.
    Returns results per period for walk-forward validation.
    """
    if len(req.periods) > 10:
        raise HTTPException(status_code=400, detail="Max 10 periods")
    
    # If no periods specified, default to per-year 2024/2025/2026
    periods = req.periods or [
        {"label": "2024", "start": "2024-01-01", "end": "2024-12-31"},
        {"label": "2025", "start": "2025-01-01", "end": "2025-12-31"},
        {"label": "2026", "start": "2026-01-01", "end": "2026-06-05"},
    ]
    
    default_indicators = {
        "ema_fast": 9, "ema_slow": 21,
        "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
        "bb_period": 20, "bb_std": 2.0,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "atr_period": 14, "stoch_k": 14, "stoch_d": 3, "adx_period": 14,
    }
    merged_indicators = {**default_indicators, **req.config.indicators}
    
    period_results = []
    for p in periods:
        config = StrategyConfig(
            symbol=req.config.symbol.upper(),
            timeframe=req.config.timeframe,
            entry_logic=req.config.entry_logic,
            entry_logic_2=req.config.entry_logic_2,
            indicators=merged_indicators,
            sl_pct=req.config.sl_pct,
            tp_pct=req.config.tp_pct,
            fee_pct=req.config.fee_pct,
            slippage_pct=req.config.slippage_pct,
            initial_capital=req.config.initial_capital,
            position_size_pct=req.config.position_size_pct,
            days=req.config.days,
            train_pct=req.config.train_pct,
            start_date=p["start"],
            end_date=p["end"],
            direction=req.config.direction,
            session_filter=req.config.session_filter,
            trend_filter=req.config.trend_filter,
            volatility_filter=req.config.volatility_filter,
            volume_filter=req.config.volume_filter,
            regime_filter=req.config.regime_filter,
            use_atr_sl_tp=req.config.use_atr_sl_tp,
            sl_atr_mult=req.config.sl_atr_mult,
            tp_atr_mult=req.config.tp_atr_mult,
        )
        result = bt.run(config)
        r = result.to_dict()
        r["period_label"] = p["label"]
        r["period_start"] = p["start"]
        r["period_end"] = p["end"]
        period_results.append(r)
    
    # Consistency check: is strategy profitable in ALL periods?
    profitable_periods = sum(1 for r in period_results if r.get("profit_per_day", 0) > 0 and r.get("status") == "ok")
    consistent = profitable_periods == len(periods)
    
    return {
        "strategy": f"{req.config.entry_logic} {req.config.symbol} {req.config.timeframe}",
        "periods": period_results,
        "total_periods": len(periods),
        "profitable_periods": profitable_periods,
        "consistent": consistent,
    }


# ============================================================
# MARTHIAS METHOD — Feature Study Endpoint
# ============================================================

class FeatureStudyRequest(BaseModel):
    symbol: str = "SOLUSDT"
    timeframe: str = "4h"
    entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    days: int = 365
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    include_instances: bool = True
    extra_features: Optional[list] = None

@app.post("/backtest/feature-study")
def feature_study(req: FeatureStudyRequest, _=Security(verify_token)):
    result = run_feature_study(
        backtester=bt,
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        days=req.days,
        start_date=req.start_date,
        end_date=req.end_date,
        extra_features=req.extra_features,
    )
    
    if not req.include_instances and result.get("status") == "ok":
        result.pop("instances", None)
    
    return result


# ============================================================
# MARTHIAS METHOD — Full Study Endpoint (Session 2)
# ============================================================

class MarthiasStudyRequest(BaseModel):
    symbol: str = "SOLUSDT"
    timeframe: str = "4h"
    entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    days: int = 365
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_per_group: int = 10  # minimum instances per group (winners/losers)

@app.post("/backtest/marthias-study")
def marthias_study(req: MarthiasStudyRequest, _=Security(verify_token)):
    """
    Full Marthias Method pipeline:
    Feature Study → T-test Importance → Filter Recommendation.
    Returns baseline WR, ranked features, and recommended filter with projected WR.
    """
    result = run_marthias_study(
        backtester=bt,
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        days=req.days,
        start_date=req.start_date,
        end_date=req.end_date,
        min_per_group=req.min_per_group,
    )
    
    return result


# ============================================================
# AI RULE TESTER — Validate AI suggested rules against data
# ============================================================

class TestRulesRequest(BaseModel):
    symbol: str = "SOLUSDT"
    timeframe: str = "4h"
    entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    days: int = 365
    rules: list = []

@app.post("/backtest/test-rules")
def backtest_test_rules(req: TestRulesRequest, _=Security(verify_token)):
    """Test AI-suggested rules against actual backtested data."""
    result = test_ai_rules(
        backtester=bt,
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        days=req.days,
        rules=req.rules,
    )
    return result


# ============================================================
# BOOTSTRAP VALIDATION — Test if rules generalize
# ============================================================

class BootstrapRequest(BaseModel):
    symbol: str = "SOLUSDT"
    timeframe: str = "4h"
    entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    days: int = 365
    rules: list = []
    n_iterations: int = 100

@app.post("/backtest/bootstrap-validate")
def bootstrap_validate_endpoint(req: BootstrapRequest, _=Security(verify_token)):
    """Bootstrap validate rules — test if they generalize or overfit."""
    result = bootstrap_validate_rules(
        backtester=bt,
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        days=req.days,
        rules=req.rules,
        n_iterations=req.n_iterations,
    )
    return result


# ============================================================
# SL/TP OPTIMIZATION — Preset testing + TP discovery
# ============================================================

class SLTPOptRequest(BaseModel):
    symbol: str = "SOLUSDT"
    timeframe: str = "4h"
    entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None
    days: int = 365
    rule_filter: Optional[str] = None
    sl_presets: list = [0.4, 0.6, 0.8]
    tp_base: float = 1.0

@app.post("/backtest/sltp-optimize")
def sltp_optimize(req: SLTPOptRequest, _=Security(verify_token)):
    """Test SL presets + discover optimal TP via wick data."""
    result = run_sltp_optimization(
        backtester=bt,
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        entry_logic=req.entry_logic,
        entry_logic_2=req.entry_logic_2,
        days=req.days,
        rule_filter=req.rule_filter,
        sl_presets=req.sl_presets,
        tp_base=req.tp_base,
    )
    return result


# Paper Run endpoint
class PaperRunRequest(BaseModel):
    symbol: str
    timeframe: str
    entry_logic: str
    entry_logic_2: Optional[str] = None
    rule: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    discovery_days: int = 365

@app.post("/backtest/paper-run")
def paper_run_endpoint(req: PaperRunRequest):
    try:
        bt = Backtester(db_path=DB_PATH)
        result = run_paper_test(
            bt,
            symbol=req.symbol.upper(),
            timeframe=req.timeframe,
            entry_logic=req.entry_logic,
            entry_logic_2=req.entry_logic_2,
            sl_pct=req.sl_pct,
            tp_pct=req.tp_pct,
            rule_filter=req.rule,
            discovery_days=req.discovery_days,
        )
        return result
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

# ── F2: Equity curve with rule filter ──
class EquityCurveRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    fee_pct: float = 0.10
    initial_capital: float = 10000.0
    position_size_pct: float = 10.5
    days: int = 1825
    direction: str = "both"
    rule_filter: Optional[str] = None

@app.post("/backtest/equity-curve")
def get_equity_curve(req: EquityCurveRequest, _=Security(verify_token)):
    """Run feature study, apply rule filter, return equity curve."""
    try:
        from backtesting_core import run_feature_study, parse_rule, _downsample
        import numpy as np

        study = run_feature_study(
            backtester=bt,
            symbol=req.symbol.upper(),
            timeframe=req.timeframe,
            entry_logic=req.entry_logic,
            entry_logic_2=req.entry_logic_2,
            sl_pct=req.sl_pct,
            tp_pct=req.tp_pct,
            days=req.days,
        )
        if study.get("status") == "error":
            return {"ok": False, "error": study.get("error", "Feature study failed")}

        instances = study.get("instances", [])
        if not instances:
            return {"ok": False, "error": "No instances found"}

        # Apply rule filter if provided
        filtered = instances
        if req.rule_filter:
            conditions = parse_rule(req.rule_filter)
            if conditions:
                filtered = []
                for inst in instances:
                    features = inst.get("features", {})
                    all_pass = True
                    for feat, op, val in conditions:
                        fv = features.get(feat)
                        if fv is None or not isinstance(fv, (int, float)):
                            all_pass = False
                            break
                        if op == ">=" and not (fv >= val): all_pass = False; break
                        elif op == "<=" and not (fv <= val): all_pass = False; break
                        elif op == ">" and not (fv > val): all_pass = False; break
                        elif op == "<" and not (fv < val): all_pass = False; break
                        elif op == "==" and not (fv == val): all_pass = False; break
                        elif op == "!=" and not (fv != val): all_pass = False; break
                    if all_pass:
                        filtered.append(inst)

        if not filtered:
            return {"ok": False, "error": "No trades after rule filter"}

        # Sort by entry timestamp
        filtered.sort(key=lambda x: x.get("entry_ts", 0))

        # Compute equity curve
        pnls = np.array([inst["pnl_dollar"] for inst in filtered])
        equity = req.initial_capital + np.cumsum(pnls)
        equity = np.insert(equity, 0, req.initial_capital)

        total = len(filtered)
        wins = sum(1 for inst in filtered if inst.get("outcome", "") != "loss")
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        net_profit = round(float(np.sum(pnls)), 2)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        max_dd = round(float(np.max(drawdown)), 2)
        
        # Timestamps for X axis (entry_ts of each trade, plus initial point)
        timestamps = [filtered[0]["entry_ts"] - 86400000] + [inst["entry_ts"] for inst in filtered]

        return {
            "ok": True,
            "total_trades": total,
            "win_rate": win_rate,
            "net_profit": net_profit,
            "max_drawdown": max_dd,
            "equity_curve": _downsample(equity.tolist(), 100),
            "timestamps": _downsample(timestamps, 100),
            "baseline_instances": len(instances),
            "filtered_instances": len(filtered),
            "rule_applied": req.rule_filter or "none",
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

# ── P2: Walk-forward validation ──
class WalkForwardRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    fee_pct: float = 0.10
    initial_capital: float = 10000.0
    position_size_pct: float = 10.5
    direction: str = "both"
    train_months: int = 24
    test_months: int = 6
    step_months: int = 6
    rule_filter: Optional[str] = None

@app.post("/backtest/walk-forward")
def run_walk_forward(req: WalkForwardRequest, _=Security(verify_token)):
    """Rolling window walk-forward: train on N months, test on M months, slide by step."""
    try:
        from datetime import datetime, timedelta
        import numpy as np

        # Build windows from 2021-01-01 to now
        start = datetime(2021, 1, 1)
        end = datetime.now()
        windows = []
        cursor = start

        while True:
            train_end = cursor + timedelta(days=req.train_months * 30)
            test_end = train_end + timedelta(days=req.test_months * 30)
            if test_end > end:
                break
            windows.append({
                "train_start": cursor.strftime("%Y-%m-%d"),
                "train_end": train_end.strftime("%Y-%m-%d"),
                "test_start": train_end.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d"),
                "label": f"{cursor.strftime('%y/%m')}→{test_end.strftime('%y/%m')}",
            })
            cursor += timedelta(days=req.step_months * 30)

        if not windows:
            return {"ok": False, "error": "Not enough data for walk-forward windows"}

        results = []
        for w in windows:
            # Train period (with rule filter)
            train_r = _backtest_with_rule(
                req.symbol, req.timeframe, req.entry_logic, req.entry_logic_2,
                req.sl_pct, req.tp_pct, req.fee_pct,
                start_date=w["train_start"], end_date=w["train_end"],
                rule_filter=req.rule_filter,
            )

            # Test period (with rule filter)
            test_r = _backtest_with_rule(
                req.symbol, req.timeframe, req.entry_logic, req.entry_logic_2,
                req.sl_pct, req.tp_pct, req.fee_pct,
                start_date=w["test_start"], end_date=w["test_end"],
                rule_filter=req.rule_filter,
            )

            results.append({
                "label": w["label"],
                "train_start": w["train_start"], "train_end": w["train_end"],
                "test_start": w["test_start"], "test_end": w["test_end"],
                "train_wr": train_r.get("win_rate", 0),
                "train_trades": train_r.get("total_trades", 0),
                "test_wr": test_r.get("win_rate", 0),
                "test_trades": test_r.get("total_trades", 0),
                "test_profit": test_r.get("net_profit", 0),
                "test_dd": test_r.get("max_drawdown", 0),
                "wr_gap": round(abs((train_r.get("win_rate", 0) or 0) - (test_r.get("win_rate", 0) or 0)), 1),
            })

        # Verdict
        valid_windows = [r for r in results if r["test_trades"] >= 3]
        if not valid_windows:
            verdict = "INSUFFICIENT_DATA"
        else:
            avg_gap = sum(r["wr_gap"] for r in valid_windows) / len(valid_windows)
            profitable = sum(1 for r in valid_windows if r["test_profit"] > 0)
            if avg_gap <= 10 and profitable >= len(valid_windows) * 0.6:
                verdict = "ROBUST"
            elif avg_gap <= 15 and profitable >= len(valid_windows) * 0.4:
                verdict = "ACCEPTABLE"
            else:
                verdict = "OVERFITTING_RISK"

        return {
            "ok": True,
            "windows": results,
            "total_windows": len(results),
            "valid_windows": len(valid_windows),
            "verdict": verdict,
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

# ── Helper: backtest with Pipeline 2 rule filter ──
def _backtest_with_rule(symbol, timeframe, entry_logic, entry_logic_2, sl_pct, tp_pct,
                        fee_pct, days=1825, start_date=None, end_date=None, rule_filter=None):
    """Run feature study + apply rule filter, return filtered metrics."""
    from backtesting_core import run_feature_study, parse_rule
    import numpy as np

    study = run_feature_study(
        backtester=bt, symbol=symbol.upper(), timeframe=timeframe,
        entry_logic=entry_logic, entry_logic_2=entry_logic_2,
        sl_pct=sl_pct, tp_pct=tp_pct, days=days,
        start_date=start_date, end_date=end_date,
    )
    instances = study.get("instances", [])
    if not instances:
        return {"win_rate": 0, "total_trades": 0, "net_profit": 0, "max_drawdown": 0, "profit_per_day": 0, "filtered": 0, "baseline": 0}

    # Apply rule filter
    filtered = instances
    if rule_filter:
        conditions = parse_rule(rule_filter)
        if conditions:
            filtered = []
            for inst in instances:
                features = inst.get("features", {})
                all_pass = True
                for feat, op, val in conditions:
                    fv = features.get(feat)
                    if fv is None or not isinstance(fv, (int, float)):
                        all_pass = False; break
                    if op == ">=" and not (fv >= val): all_pass = False; break
                    elif op == "<=" and not (fv <= val): all_pass = False; break
                    elif op == ">" and not (fv > val): all_pass = False; break
                    elif op == "<" and not (fv < val): all_pass = False; break
                    elif op == "==" and not (fv == val): all_pass = False; break
                    elif op == "!=" and not (fv != val): all_pass = False; break
                if all_pass:
                    filtered.append(inst)

    if not filtered:
        return {"win_rate": 0, "total_trades": 0, "net_profit": 0, "max_drawdown": 0, "profit_per_day": 0, "filtered": 0, "baseline": len(instances)}

    # Apply fee adjustment to pnl
    position_size = 10000 * 10.5 / 100  # $1,050
    total_fee_per_trade = position_size * fee_pct * 2 / 100  # entry + exit

    total = len(filtered)
    wins = sum(1 for inst in filtered if inst.get("outcome", "") != "loss")
    pnls = []
    for inst in filtered:
        raw_pnl = inst.get("pnl_dollar", 0)
        adjusted_pnl = raw_pnl - total_fee_per_trade + (position_size * 0.10 * 2 / 100)  # remove old fee, add new
        pnls.append(adjusted_pnl)

    net_profit = round(sum(pnls), 2)
    equity = np.array([10000 + sum(pnls[:i+1]) for i in range(len(pnls))])
    equity = np.insert(equity, 0, 10000)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak * 100
    max_dd = round(float(np.max(dd)), 2) if len(dd) > 0 else 0

    # Regime breakdown from filtered trades
    regime_map = {0: "sideways", 1: "bull", -1: "bear", 2: "shock"}
    regime_stats = {}
    for inst in filtered:
        rg = regime_map.get(inst.get("regime", 0), "unknown")
        if rg not in regime_stats:
            regime_stats[rg] = {"wins": 0, "total": 0}
        regime_stats[rg]["total"] += 1
        if inst.get("outcome", "") != "loss":
            regime_stats[rg]["wins"] += 1
    for rg in regime_stats:
        s = regime_stats[rg]
        s["win_rate"] = round(s["wins"] / s["total"] * 100, 2) if s["total"] > 0 else 0
        s["trades"] = s["total"]

    return {
        "win_rate": round(wins / total * 100, 2) if total > 0 else 0,
        "total_trades": total,
        "net_profit": net_profit,
        "max_drawdown": max_dd,
        "profit_per_day": round(net_profit / max(days, 1), 2),
        "filtered": total,
        "baseline": len(instances),
        "regime_stats": regime_stats,
    }

# ── P2: Fee comparison ──
class FeeCompareRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None
    sl_pct: float = 0.6
    tp_pct: float = 1.5
    days: int = 1825
    direction: str = "both"
    rule_filter: Optional[str] = None

@app.post("/backtest/fee-compare")
def run_fee_compare(req: FeeCompareRequest, _=Security(verify_token)):
    """Run same strategy with different fee levels to see real impact."""
    try:
        fee_tiers = [
            {"label": "Backtester default", "fee": 0.10},
            {"label": "Binance taker (VIP0)", "fee": 0.04},
            {"label": "Binance maker (VIP0)", "fee": 0.02},
            {"label": "Zero fee (best case)", "fee": 0.00},
        ]
        results = []
        for tier in fee_tiers:
            r = _backtest_with_rule(
                req.symbol, req.timeframe, req.entry_logic, req.entry_logic_2,
                req.sl_pct, req.tp_pct, tier["fee"], req.days,
                rule_filter=req.rule_filter,
            )
            results.append({
                "label": tier["label"],
                "fee_pct": tier["fee"],
                **r,
            })
        return {"ok": True, "tiers": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── P3: Combined equity for portfolio ──
class CombinedEquityRequest(BaseModel):
    strategies: list[dict]  # [{symbol, timeframe, entry_logic, entry_logic_2, sl_pct, tp_pct}]
    days: int = 1825

@app.post("/backtest/combined-equity")
def run_combined_equity(req: CombinedEquityRequest, _=Security(verify_token)):
    """Run multiple strategies, merge equity curves into one portfolio."""
    try:
        import numpy as np
        from backtesting_core import _downsample

        all_trades = []
        per_strategy = []

        for s in req.strategies[:10]:
            config = StrategyConfig(
                symbol=s.get("symbol", "BTCUSDT").upper(),
                timeframe=s.get("timeframe", "1h"),
                entry_logic=s.get("entry_logic", "ema_cross"),
                entry_logic_2=s.get("entry_logic_2"),
                sl_pct=s.get("sl_pct", 0.6), tp_pct=s.get("tp_pct", 1.5),
                fee_pct=0.04, initial_capital=10000,
                position_size_pct=10.5 / len(req.strategies),
                days=req.days, direction="both",
            )
            result = bt.run(config)
            r = result.to_dict()

            # Collect trades with timestamps for merging
            trades = r.get("trades", [])
            label = f"{s.get('symbol','?')}_{s.get('timeframe','?')}_{s.get('entry_logic','?')}"
            for t in trades:
                all_trades.append({
                    "ts": t.get("entry_ts", 0),
                    "pnl": t.get("pnl", 0),
                    "strategy": label,
                })
            per_strategy.append({
                "label": label,
                "win_rate": r.get("win_rate", 0),
                "total_trades": r.get("total_trades", 0),
                "net_profit": r.get("net_profit", 0),
                "max_drawdown": r.get("max_drawdown", 0),
            })

        if not all_trades:
            return {"ok": False, "error": "No trades from any strategy"}

        # Sort all trades by timestamp, compute combined equity
        all_trades.sort(key=lambda x: x["ts"])
        capital = 10000.0
        pnls = np.array([t["pnl"] for t in all_trades])
        equity = capital + np.cumsum(pnls)
        equity = np.insert(equity, 0, capital)
        timestamps = [all_trades[0]["ts"] - 86400000] + [t["ts"] for t in all_trades]

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        max_dd = round(float(np.max(drawdown)), 2)
        net = round(float(np.sum(pnls)), 2)
        total = len(all_trades)
        wins = sum(1 for t in all_trades if t["pnl"] > 0)

        return {
            "ok": True,
            "equity_curve": _downsample(equity.tolist(), 100),
            "timestamps": _downsample(timestamps, 100),
            "total_trades": total,
            "win_rate": round(wins / total * 100, 2) if total > 0 else 0,
            "net_profit": net,
            "max_drawdown": max_dd,
            "per_strategy": per_strategy,
            "strategy_count": len(per_strategy),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# ============================================================
# DERET STATISTIK — Predicted Range Entry Strategy
# ============================================================

@app.post("/backtest/deret-statistik")
def run_deret_backtest(req: dict, _=Security(verify_token)):
    """Single deret statistik backtest."""
    try:
        result = backtest_deret_statistik(
            db_path=DB_PATH,
            symbol=req.get("symbol", "ETHUSDT").upper(),
            timeframe=req.get("timeframe", "4h"),
            window=req.get("window", 5),
            buffer_pct=req.get("buffer_pct", 0.5),
            tp_pct=req.get("tp_pct", 1.0),
            sl_pct=req.get("sl_pct", 1.0),
            days=req.get("days", 1825),
            mode=req.get("mode", "baret"),
            buffer2_pct=req.get("buffer2_pct", 1.0),
            close_filter_pct=req.get("close_filter_pct", 0.3),
            max_hold=req.get("max_hold", 4),
            sub_candle_tf=req.get("sub_candle_tf", None),
        )
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/backtest/deret-statistik/sweep")
def run_deret_sweep(req: dict, _=Security(verify_token)):
    """Sweep all pairs × TFs × buffer/TP/SL combinations. Find optimal per combo."""
    try:
        pairs = req.get("pairs", ["ETHUSDT","SOLUSDT","AVAXUSDT","DOGEUSDT","LINKUSDT","XRPUSDT","DOTUSDT","BTCUSDT","1000PEPEUSDT"])
        tfs = req.get("timeframes", ["15m","1h","4h"])
        buffers = req.get("buffers", [0.3, 0.5, 0.8, 1.0])
        tps = req.get("tps", [0.5, 0.8, 1.0, 1.5])
        sls = req.get("sls", [0.5, 0.8, 1.0, 1.5])
        window = req.get("window", 5)
        days = req.get("days", 1825)
        
        all_results = []
        best_per_combo = {}
        
        for symbol in pairs:
            for tf in tfs:
                combo_key = f"{symbol}_{tf}"
                best = None
                for buf in buffers:
                    for tp in tps:
                        for sl in sls:
                            r = backtest_deret_statistik(
                                db_path=DB_PATH, symbol=symbol, timeframe=tf,
                                window=window, buffer_pct=buf, tp_pct=tp, sl_pct=sl, days=days,
                                max_hold=req.get("max_hold", 4),
                                sub_candle_tf=req.get("sub_candle_tf", "1m"),
                            )
                            if r.get("status") != "ok":
                                continue
                            r["combo"] = combo_key
                            all_results.append(r)
                            # Track best: WR ≥ 75%, most profit/day, min 10 trades
                            if (r["win_rate"] >= 75 and r["total_trades"] >= 10 and
                                r["profit_per_day"] >= 2.0 and
                                (best is None or r["profit_per_day"] > best["profit_per_day"])):
                                best = r
                
                if best:
                    best_per_combo[combo_key] = best
        
        # Summary
        passed = [r for r in all_results if r["win_rate"] >= 75 and r["total_trades"] >= 10 and r["profit_per_day"] >= 2.0]
        
        return {
            "ok": True,
            "total_tested": len(all_results),
            "passed": len(passed),
            "best_per_combo": best_per_combo,
            "top_10": sorted(passed, key=lambda x: x["profit_per_day"], reverse=True)[:10],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# DCA BACKTEST ENDPOINT
# ============================================================

@app.post("/backtest/dca")
def run_dca_backtest(req: dict, _=Security(verify_token)):
    """Run DCA backtest for a strategy. Compares DCA vs traditional SL/TP."""
    try:
        dca_cfg = DCAConfig(
            symbol=req.get("symbol", "ETHUSDT").upper(),
            timeframe=req.get("timeframe", "4h"),
            entry_logic=req.get("entry_logic", "ema_cross"),
            entry_logic_2=req.get("entry_logic_2"),
            entry_usd=req.get("entry_usd", 1.0),
            leverage=req.get("leverage", 50),
            max_levels=req.get("max_levels", 5),
            tp_pct=req.get("tp_pct", 1.0),
            cut_pct=req.get("cut_pct", 2.0),
            capital_pool=req.get("capital_pool", 100.0),
            days=req.get("days", 1825),
            direction=req.get("direction", "both"),
        )
        if req.get("spacing"):
            dca_cfg.spacing = req["spacing"]

        rule_filter = req.get("rule_filter", req.get("rule", ""))
        result = backtest_dca(DB_PATH, dca_cfg, rule_filter=rule_filter or None)
        return {"ok": True, **result}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/backtest/dca/sweep")
def run_dca_sweep(req: dict, _=Security(verify_token)):
    """Single DCA sweep (manual, one-off). For autonomous loop use /dca/start."""
    try:
        symbols = req.get("symbols", ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT",
                                       "XRPUSDT", "DOGEUSDT", "LINKUSDT", "YFIUSDT",
                                       "1000PEPEUSDT"])
        symbols = [s for s in symbols if s != "BTCUSDT"]
        timeframes = req.get("timeframes", ["15m", "1h", "4h"])
        entry_logics = req.get("entry_logics", ENTRY_LOGICS[:10])
        max_combos = req.get("max_combos", 50)

        results = []
        count = 0
        for symbol in symbols:
            for tf in timeframes:
                for logic in entry_logics:
                    if count >= max_combos: break
                    count += 1
                    dca_cfg = DCAConfig(symbol=symbol, timeframe=tf, entry_logic=logic, days=req.get("days", 1825))
                    r = backtest_dca(DB_PATH, dca_cfg)
                    if r.get("status") == "ok" and r.get("total_sessions", 0) > 0:
                        results.append(r)
        results.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
        return {"ok": True, "total_tested": count, "results": results[:50]}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# ============================================================
# DCA MODE — REMOVED (superseded by baret_bot sweep_dca mode)
# ============================================================


# ============================================================
# PIPELINE 2 CRON — Background thread hits Worker run-next
# ============================================================

import requests as _requests

_p2_cron_running = False
_p2_cron_lock = threading.Lock()
_p2_interval = int(os.environ.get("P2_CRON_INTERVAL", "60"))  # default 1 minute
_p2_worker_url = os.environ.get("P2_WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev/discovery/marthias/run-next")

def _p2_cron_loop():
    global _p2_cron_running
    print(f"[P2 Cron] Started, interval={_p2_interval}s, url={_p2_worker_url}")
    while _p2_cron_running:
        try:
            # ── SWEEP JOBS FIRST ──
            try:
                # Auto-reset jobs stuck in 'running' for >10 min
                base_url = _p2_worker_url.replace('/marthias/run-next', '')
                try:
                    _requests.post(f"{base_url}/sweep/reset", json={"auto": True}, timeout=5)
                except:
                    pass
                
                sweep_resp = _requests.post(f"{base_url}/sweep/process-next", json={}, timeout=10)
                sweep_data = sweep_resp.json()
                if sweep_data.get("ok") and not sweep_data.get("queue_empty"):
                    job = sweep_data
                    symbol = job["symbol"]
                    timeframe = job["timeframe"]
                    entry_logic = job["entry_logic"]
                    entry_logic_2 = job.get("entry_logic_2")
                    days = job.get("days", 1825)
                    job_id = job["job_id"]
                    session_id = job["session_id"]
                    
                    print(f"[Sweep] Processing {symbol}·{timeframe} {entry_logic}")
                    results = []
                    for sl in [0.4, 0.6, 0.8]:
                        for tp in [1.0, 1.5, 2.0]:
                            try:
                                req = BacktestRequest(
                                    symbol=symbol, timeframe=timeframe,
                                    entry_logic=entry_logic, entry_logic_2=entry_logic_2 or "",
                                    indicators={}, sl_pct=sl, tp_pct=tp,
                                    days=days, train_pct=75.0, direction="both"
                                )
                                r = run_backtest(req)
                                r["sl_pct"] = sl
                                r["tp_pct"] = tp
                                r["symbol"] = symbol
                                r["timeframe"] = timeframe
                                r["entry_logic"] = entry_logic
                                r["entry_logic_2"] = entry_logic_2
                                r.pop("equity_curve", None)
                                if r.get("status") == "ok" and r.get("total_trades", 0) >= 5:
                                    results.append(r)
                            except Exception as e:
                                print(f"[Sweep] Backtest error: {e}")
                    
                    results.sort(key=lambda x: (-x.get("win_rate", 0), -x.get("profit_per_day", 0)))
                    results = results[:20]
                    best_wr = results[0]["win_rate"] if results else 0
                    icon = "⭐" if best_wr >= 55 else "✅" if best_wr >= 50 else "❌" if best_wr > 0 else "⏭"
                    print(f"[Sweep] {icon} {symbol}·{timeframe}: WR={best_wr:.1f}%")
                    
                    try:
                        base_url = _p2_worker_url.replace('/marthias/run-next', '')
                        _requests.post(f"{base_url}/sweep/save-result", json={
                            "job_id": job_id, "session_id": session_id,
                            "entry_logic": entry_logic, "entry_logic_2": entry_logic_2,
                            "symbol": symbol, "timeframe": timeframe,
                            "results": results,
                        }, timeout=15)
                    except Exception as e:
                        print(f"[Sweep] Save error: {e}")
                    
                    time.sleep(5)
                    pass  # Process 1 sweep job per cycle, then continue to seed + P2
            except Exception as e:
                print(f"[Sweep] Error: {e}")
            
            # ── AUTO SEED Pipeline 2 queue ──
            try:
                base_url = _p2_worker_url.replace('/marthias/run-next', '')
                seed_resp = _requests.post(f"{base_url}/marthias/seed-queue", json={}, timeout=15)
                seed_data = seed_resp.json()
                if seed_data.get("queued", 0) > 0:
                    print(f"[Seed] 🌱 {seed_data['queued']} new combos queued to Pipeline 2")
            except Exception as e:
                print(f"[Seed] Error: {e}")
            
            # ── PIPELINE 2 ──
            with _p2_cron_lock:
                resp = _requests.post(_p2_worker_url, json={}, timeout=300)
                data = resp.json()
                status = data.get("status", "?")
                combo = data.get("combo", "")
                if status == "skipped":
                    print(f"[P2 Cron] Skipped: {combo} ({data.get('instances',0)} inst)")
                elif status == "ok":
                    best = data.get("best_rule", {})
                    print(f"[P2 Cron] OK: {combo} | WR {best.get('wr','?')}% | saved={data.get('saved')}")
                elif status == "queue_empty":
                    print("[P2 Cron] Queue empty")
                else:
                    print(f"[P2 Cron] {status}: {combo}")
        except Exception as e:
            print(f"[P2 Cron] Error: {e}")
        time.sleep(_p2_interval)

@app.get("/p2-cron/start")
def p2_cron_start():
    global _p2_cron_running
    if _p2_cron_running:
        return {"ok": True, "message": "Already running", "interval": _p2_interval}
    _p2_cron_running = True
    t = threading.Thread(target=_p2_cron_loop, daemon=True)
    t.start()
    return {"ok": True, "message": f"P2 cron started, interval={_p2_interval}s"}

@app.get("/p2-cron/stop")
def p2_cron_stop():
    global _p2_cron_running
    _p2_cron_running = False
    return {"ok": True, "message": "P2 cron stopped"}

@app.get("/p2-cron/status")
def p2_cron_status():
    return {"running": _p2_cron_running, "interval": _p2_interval, "url": _p2_worker_url}

@app.get("/sweep-cron/status")
def sweep_cron_status():
    return {"info": "Sweep integrated into P2 cron", "p2_running": _p2_cron_running}

# Auto-start P2 cron on app startup
@app.on_event("startup")
def _auto_start_p2_cron():
    if os.environ.get("P2_CRON_ENABLED", "true").lower() == "true":
        global _p2_cron_running
        _p2_cron_running = True
        t = threading.Thread(target=_p2_cron_loop, daemon=True)
        t.start()
        print(f"[P2 Cron] Auto-started (includes sweep processing)")

# ============================================================
# P4 — LIVE BOT CONTROL (Iron Legion REMOVED — use baret-live)
# ============================================================

@app.on_event("startup")
def _auto_start_bot():
    if os.environ.get("BARET_LIVE_ENABLED", "false").lower() == "true":
        mode = os.environ.get("BARET_LIVE_MODE", "baret")
        pos_usd = float(os.environ.get("BARET_LIVE_POSITION", "10"))
        min_wr = float(os.environ.get("BARET_LIVE_MIN_WR", "75"))
        max_dd = float(os.environ.get("BARET_LIVE_MAX_DD", "20"))
        result = start_baret_live(mode=mode, position_usd=pos_usd, min_wr=min_wr, max_dd=max_dd)

# ============================================================
# BARET — Deret Statistik Discovery Mode (Ultron Loop)
# ============================================================

@app.get("/baret/start")
def baret_start_endpoint(mode: str = "baret", timeframes: str = ""):
    """Start Baret discovery — auto-stops P1 cron + DCA. timeframes: comma-separated e.g. '15m,1h'"""
    global _p2_cron_running
    _p2_cron_running = False
    tfs = [t.strip() for t in timeframes.split(",") if t.strip()] or None
    return start_baret(DB_PATH, mode=mode, timeframes=tfs)

@app.get("/baret/stop")
def baret_stop_endpoint():
    return stop_baret()

@app.get("/baret/status")
def baret_status_endpoint():
    return baret_status()

@app.get("/baret/log")
def baret_log_endpoint(limit: int = 200):
    return {"ok": True, "log": get_baret_log(limit)}

# ============================================================
# CLUSTERING — Optimal SL/TP dari distribusi deviation
# ============================================================

@app.post("/backtest/clustering")
def run_clustering(req: dict, _=Security(verify_token)):
    """Analyze deviation clusters for optimal SL/TP per pair."""
    try:
        result = analyze_deviation_clusters(
            db_path=DB_PATH,
            symbol=req.get("symbol", "SOLUSDT").upper(),
            timeframe=req.get("timeframe", "4h"),
            window=req.get("window", 10),
            days=req.get("days", 1825),
            buffer_pct=req.get("buffer_pct", 0.8),
        )
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================
# BARET LIVE TRADING — Demo execution
# ============================================================

@app.get("/baret-live/start")
def baret_live_start(mode: str = "baret", position_usd: float = 10.0, min_wr: float = 75.0, max_dd: float = 20.0, min_ppd: float = 0.0, leverage: int = 50, max_bh: float = 100.0, buffer: float = None, tp: float = None, sl: float = None, sort_by: str = "profit", use_custom_configs: bool = False):
    """Start Baret live demo trading. Configs pulled from D1 based on filters or custom configs."""
    return start_baret_live(mode=mode, position_usd=position_usd, min_wr=min_wr, max_dd=max_dd, min_ppd=min_ppd, leverage=leverage, max_bh=max_bh, buffer=buffer, tp=tp, sl=sl, sort_by=sort_by, use_custom_configs=use_custom_configs)

@app.get("/baret-live/stop")
def baret_live_stop():
    return stop_baret_live()

@app.get("/baret-live/status")
def baret_live_status_endpoint():
    return baret_live_status()

@app.get("/baret-live/log")
def baret_live_log_endpoint(limit: int = 200):
    return {"ok": True, "log": get_baret_live_log(limit)}

@app.get("/server-ip")
def server_ip():
    """Get Railway server's outbound IP."""
    try:
        import requests as _req
        r = _req.get("https://api.ipify.org?format=json", timeout=5)
        return {"ok": True, "ip": r.json().get("ip")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/baret-live/close")
def baret_live_close(symbol: str = None, account_id: int = None):
    """Close positions. Use account_id for multi-account support."""
    if account_id:
        from baret_live import _account_bots, close_position as cp, close_all_positions as cap
        bot = _account_bots.get(int(account_id))
        if not bot:
            return {"ok": False, "error": f"Account {account_id} not found or not running"}
        client = bot.get("client")
        if symbol:
            return cp(symbol, client=client)
        return cap(client=client)
    if symbol:
        return close_position(symbol)
    return close_all_positions()

@app.get("/baret-live/start-account")
def baret_live_start_account(account_id: int = 0, mode: str = "baret_dca"):
    """Start bot for a specific trading account."""
    return start_account_bot(account_id, mode=mode)

@app.get("/baret-live/stop-account")
def baret_live_stop_account(account_id: int = 0):
    """Stop bot for a specific trading account."""
    return stop_account_bot(account_id)

@app.get("/baret-live/account-status")
def baret_live_account_status(account_id: int = None):
    """Get status of account bots."""
    return account_bot_status(account_id)

# ============================================================
# ULTRON PHASE 2 — Decision Engine Endpoints
# ============================================================

@app.get("/ultron/status")
def ultron_status_endpoint():
    """Get Ultron Phase 2 state: active decisions, config, skips."""
    return ultron_status()

@app.get("/ultron/log")
def ultron_log_endpoint(limit: int = 100):
    """Get Ultron activity log."""
    return {"ok": True, "log": get_ultron_log(limit)}

@app.post("/ultron/analyze")
def ultron_analyze_endpoint():
    """Manually trigger Ultron analysis (from Jarvis or dashboard)."""
    return manual_analyze()

@app.post("/ultron/clear-skip")
def ultron_clear_skip(symbol: str = None, hour: int = None):
    """Clear a skip decision. Called after Jarvis override."""
    if symbol:
        clear_pair_skip(symbol)
        return {"ok": True, "message": f"Pair skip cleared: {symbol}"}
    if hour is not None:
        clear_hour_skip(hour)
        return {"ok": True, "message": f"Hour skip cleared: {hour}"}
    return {"ok": False, "error": "Provide symbol or hour"}

@app.post("/ultron/clear-buffer")
def ultron_clear_buffer(symbol: str = ""):
    """Clear buffer adjustment for a pair."""
    clear_buffer_adjustment(symbol)
    return {"ok": True, "message": f"Buffer adjustment cleared: {symbol}"}
# ════════════════════════════════════════════════════════════
# TICK DISCOVERY ENDPOINTS — paste at bottom of app.py
# ════════════════════════════════════════════════════════════
# Also add this import at top of app.py:
#   from tick_discovery import (
#       start_tick_discovery, stop_tick_discovery,
#       get_discovery_status, get_discovery_log,
#       extract_tick_events, analyze_tick_stats,
#   )
# ════════════════════════════════════════════════════════════

@app.get("/tick/start")
def tick_start(
    pairs: str = None,       # comma-separated, e.g. "BTCUSDT,ETHUSDT"
    timeframes: str = None,  # comma-separated, e.g. "15m,1h,4h"
    window: int = 10,
    buffer_pct: float = 0.8,
    buffer2_pct: float = 1.0,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    days: int = 1825,
):
    pair_list = pairs.split(",") if pairs else None
    tf_list = timeframes.split(",") if timeframes else None
    return start_tick_discovery(
        pairs=pair_list, timeframes=tf_list,
        window=window, buffer_pct=buffer_pct, buffer2_pct=buffer2_pct,
        tp_pct=tp_pct, sl_pct=sl_pct, days=days,
    )

@app.get("/tick/stop")
def tick_stop():
    return stop_tick_discovery()

@app.get("/tick/status")
def tick_status():
    return get_discovery_status()

@app.get("/tick/log")
def tick_log(limit: int = 200):
    return {"ok": True, "log": get_discovery_log(limit)}

@app.get("/tick/analyze")
def tick_analyze(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    window: int = 10,
    buffer_pct: float = 0.8,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    group_by: str = "hour_utc",
    days: int = 1825,
):
    return analyze_tick_stats(
        symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        group_by=group_by, days=days,
    )

@app.get("/tick/extract")
def tick_extract(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    window: int = 10,
    buffer_pct: float = 0.8,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    days: int = 1825,
    save: bool = True,
):
    return extract_tick_events(
        symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        days=days, save_to_d1=save,
    )
@app.get("/tick/candle-range")
def candle_range(symbol: str = "SOLUSDT", timeframe: str = "4h", days: int = 1825):
    import sqlite3
    from collections import defaultdict
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    
    rows = conn.execute("""
        SELECT open, high, low, close, open_time FROM klines 
        WHERE symbol = ? AND timeframe = ? ORDER BY open_time ASC
    """, (symbol, timeframe)).fetchall()
    
    sub_rows = conn.execute("""
        SELECT open, high, low, close, open_time FROM klines 
        WHERE symbol = ? AND timeframe = '1m' ORDER BY open_time ASC
    """, (symbol,)).fetchall()
    conn.close()
    
    if not rows or not sub_rows: return {"error": "no data"}
    
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][4]
        rows = [r for r in rows if r[4] >= last_time - ms_limit]
    
    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)
    
    sub_groups = defaultdict(list)
    for sr in sub_rows:
        pt = (sr[4] // parent_ms) * parent_ms
        sub_groups[pt].append(sr)
    
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]
    results = []
    total = len(rows)
    
    for t in thresholds:
        long_minutes = []
        short_minutes = []
        long_miss = 0
        short_miss = 0
        
        for r in rows:
            candle_open = r[0]
            long_target = candle_open * (1 + t / 100)
            short_target = candle_open * (1 - t / 100)
            pt = (r[4] // parent_ms) * parent_ms
            subs = sub_groups.get(pt, [])
            
            long_found = False
            short_found = False
            for idx, sc in enumerate(subs):
                if not long_found and sc[1] >= long_target:
                    long_minutes.append(idx)
                    long_found = True
                if not short_found and sc[2] <= short_target:
                    short_minutes.append(idx)
                    short_found = True
                if long_found and short_found:
                    break
            
            if not long_found: long_miss += 1
            if not short_found: short_miss += 1
        
        def calc_stats(minutes):
            if not minutes: return None
            s = sorted(minutes)
            n = len(s)
            avg = round(sum(s) / n, 1)
            median = s[n // 2]
            p25 = s[int(n * 0.25)]
            p75 = s[int(n * 0.75)]
            std = round((sum((x - avg) ** 2 for x in s) / n) ** 0.5, 1)
            consistency = round(sum(1 for x in s if abs(x - avg) <= std) / n * 100, 1)
            return {
                "avg_min": avg, "median_min": median,
                "p25_min": p25, "p75_min": p75,
                "min_min": s[0], "max_min": s[-1],
                "std_min": std, "consistency_pct": consistency,
            }
        
        results.append({
            "tp_pct": t,
            "long_hit_pct": round(len(long_minutes) / total * 100, 1),
            "short_hit_pct": round(len(short_minutes) / total * 100, 1),
            "long_timing": calc_stats(long_minutes),
            "short_timing": calc_stats(short_minutes),
        })
    
    return {"symbol": symbol, "timeframe": timeframe, "total_candles": total, "results": results}
@app.get("/tick/sweep")
def tick_sweep(
    pairs: str = None,
    timeframes: str = None,
    window: int = 10,
    days: int = 1825,
    modes: str = "both",
    position_usd: float = 100,
    leverage: int = 50,
):
    pair_list = pairs.split(",") if pairs else None
    tf_list = timeframes.split(",") if timeframes else None
    return start_sweep_engine(
        pairs=pair_list, timeframes=tf_list,
        window=window, days=days, modes=modes,
        position_usd=position_usd, leverage=leverage,
    )
 
@app.get("/tick/sweep-stop")
def tick_sweep_stop():
    return stop_sweep_engine()

@app.get("/tick/sweep-pause")
def tick_sweep_pause():
    return pause_sweep_engine()

@app.get("/tick/sweep-resume")
def tick_sweep_resume():
    return resume_sweep_engine()

@app.get("/tick/sweep-status")
def tick_sweep_status():
    return get_sweep_status()

@app.get("/tick/cluster")
def tick_cluster(
    symbol: str = "DOGEUSDT",
    timeframe: str = "4h",
    window: int = 10,
    days: int = 1825,
):
    """Run clustering analysis for a single pair×tf (standalone, outside sweep)."""
    rows, sub_lookup = td_load_data(TD_DB_PATH, symbol, timeframe, "1m")
    if len(rows) < window + 20:
        return {"error": "insufficient data", "rows": len(rows)}
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        rows = [r for r in rows if r[5] >= last_time - ms_limit]
    return cluster_levels(
        rows, sub_lookup, symbol, timeframe,
        window=window, days=days, save_to_d1=True,
    )

@app.get("/tick/profile")
def tick_profile(
    symbol: str = "DOGEUSDT",
    timeframe: str = "4h",
    window: int = 10,
    buffer_pct: float = 2.0,
    tp_pct: float = 1.0,
    sl_pct: float = 2.0,
    buffer2_pct: float = 1.5,
    close_filter_pct: float = 0,
    days: int = 1825,
):
    return profile_winning_combo(
        symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        buffer2_pct=buffer2_pct, close_filter_pct=close_filter_pct, days=days,
    )
"""
Paste ini di PALING BAWAH app.py
Test hipotesis: close_position predict first_extreme
"""

@app.get("/tick/test-close-position")
def test_close_position(symbol: str = "DOGEUSDT", timeframe: str = "4h", window: int = 10, days: int = 1825):
    import sqlite3
    from collections import defaultdict
    from datetime import datetime, timezone

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    rows = conn.execute("""
        SELECT open, high, low, close, volume, open_time
        FROM klines WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
    """, (symbol, timeframe)).fetchall()

    sub_rows = conn.execute("""
        SELECT open, high, low, close, open_time
        FROM klines WHERE symbol = ? AND timeframe = '1m'
        ORDER BY open_time ASC
    """, (symbol,)).fetchall()
    conn.close()

    if not rows or not sub_rows:
        return {"error": "no data"}

    # TF → ms
    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)

    # Group 1m by parent candle
    sub_groups = defaultdict(list)
    for sr in sub_rows:
        pt = (sr[4] // parent_ms) * parent_ms
        sub_groups[pt].append({"h": sr[1], "l": sr[2]})

    n = len(rows)
    opens = [r[0] for r in rows]
    highs = [r[1] for r in rows]
    lows = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    # Limit days
    if days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        cutoff = last_time - ms_limit
        start_idx = 0
        for idx, r in enumerate(rows):
            if r[5] >= cutoff:
                start_idx = idx
                break
        start_idx = max(start_idx, window)
    else:
        start_idx = window

    # Buckets for close_position
    buckets = {
        "very_low_0_15": (0, 0.15),
        "low_15_30": (0.15, 0.30),
        "mid_low_30_45": (0.30, 0.45),
        "mid_45_55": (0.45, 0.55),
        "mid_high_55_70": (0.55, 0.70),
        "high_70_85": (0.70, 0.85),
        "very_high_85_100": (0.85, 1.01),
    }

    results = {b: {"total": 0, "high_first": 0, "low_first": 0, "none": 0} for b in buckets}
    raw_data = []

    for i in range(start_idx, len(close_ratios)):
        if i + 1 >= n:
            break

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window

        pred_high = highs[i] * avg_h
        pred_low = lows[i] * avg_l
        pred_close = closes[i] * avg_c

        pred_range = pred_high - pred_low
        if pred_range <= 0:
            continue

        close_position = (pred_close - pred_low) / pred_range

        # Get 1m data for next candle
        candle_time = times[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_groups.get(parent_ts, [])
        if not subs:
            continue

        # Determine first_extreme from 1m
        min_ph, min_pl = None, None
        for sc_idx, sc in enumerate(subs):
            if min_ph is None and sc["h"] >= pred_high:
                min_ph = sc_idx
            if min_pl is None and sc["l"] <= pred_low:
                min_pl = sc_idx
            if min_ph is not None and min_pl is not None:
                break

        if min_ph is not None and min_pl is not None:
            first_extreme = "HIGH" if min_ph < min_pl else "LOW"
        elif min_ph is not None:
            first_extreme = "HIGH"
        elif min_pl is not None:
            first_extreme = "LOW"
        else:
            first_extreme = "NONE"

        # Bucket
        for bname, (lo, hi) in buckets.items():
            if lo <= close_position < hi:
                results[bname]["total"] += 1
                if first_extreme == "HIGH":
                    results[bname]["high_first"] += 1
                elif first_extreme == "LOW":
                    results[bname]["low_first"] += 1
                else:
                    results[bname]["none"] += 1
                break

        raw_data.append({"cp": round(close_position, 3), "fe": first_extreme})

    # Format output
    table = []
    for bname, (lo, hi) in buckets.items():
        d = results[bname]
        if d["total"] == 0:
            continue
        high_pct = round(d["high_first"] / d["total"] * 100, 1)
        low_pct = round(d["low_first"] / d["total"] * 100, 1)

        # Hipotesis: close dekat low → HIGH_FIRST, close dekat high → LOW_FIRST
        if high_pct > low_pct:
            predict = "SHORT"
            confidence = high_pct
        elif low_pct > high_pct:
            predict = "LONG"
            confidence = low_pct
        else:
            predict = "SKIP"
            confidence = 50

        table.append({
            "bucket": bname,
            "range": f"{lo:.0%}-{hi:.0%}",
            "total": d["total"],
            "high_first": d["high_first"],
            "high_first_pct": high_pct,
            "low_first": d["low_first"],
            "low_first_pct": low_pct,
            "none": d["none"],
            "predicted_direction": predict,
            "confidence": confidence,
        })

    # Overall correlation
    total_candles = sum(d["total"] for d in results.values())
    correct_hipotesis = 0  # close < 0.3 → HIGH, close > 0.7 → LOW
    total_testable = 0
    for bname, d in results.items():
        if "very_low" in bname or "low_15" in bname:
            correct_hipotesis += d["high_first"]
            total_testable += d["total"]
        elif "very_high" in bname or "high_70" in bname:
            correct_hipotesis += d["low_first"]
            total_testable += d["total"]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "total_candles": total_candles,
        "hipotesis": "close dekat low → HIGH_FIRST (SHORT), close dekat high → LOW_FIRST (LONG)",
        "table": table,
        "hipotesis_test": {
            "testable_candles": total_testable,
            "correct": correct_hipotesis,
            "accuracy": round(correct_hipotesis / total_testable * 100, 1) if total_testable > 0 else 0,
            "description": "close_position < 0.30 → HIGH_FIRST, close_position > 0.70 → LOW_FIRST",
        }
    }
"""
Paste di PALING BAWAH app.py (setelah test-close-position endpoint)
Backtest Open Entry pakai close_position sebagai direction signal
"""

@app.get("/tick/backtest-close-position")
def backtest_close_position(
    symbol: str = "DOGEUSDT",
    timeframe: str = "4h",
    window: int = 10,
    days: int = 1825,
    tp_pct: float = 0.5,
    sl_pct: float = 0.5,
    long_threshold: float = 0.70,
    short_threshold: float = 0.30,
    position_usd: float = 100,
    leverage: int = 50,
):
    import sqlite3
    from collections import defaultdict
    from datetime import datetime, timezone

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    rows = conn.execute("""
        SELECT open, high, low, close, volume, open_time
        FROM klines WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
    """, (symbol, timeframe)).fetchall()

    sub_rows = conn.execute("""
        SELECT open, high, low, close, open_time
        FROM klines WHERE symbol = ? AND timeframe = '1m'
        ORDER BY open_time ASC
    """, (symbol,)).fetchall()
    conn.close()

    if not rows or not sub_rows:
        return {"error": "no data"}

    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)

    sub_groups = defaultdict(list)
    for sr in sub_rows:
        pt = (sr[4] // parent_ms) * parent_ms
        sub_groups[pt].append({"o": sr[0], "h": sr[1], "l": sr[2], "c": sr[3]})

    n = len(rows)
    opens = [r[0] for r in rows]
    highs = [r[1] for r in rows]
    lows = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    notional = position_usd * leverage
    fee = notional * 0.07 / 100  # 0.07% roundtrip

    trades = []

    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break

        # Predicted range
        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window

        pred_high = highs[i] * avg_h
        pred_low = lows[i] * avg_l
        pred_close = closes[i] * avg_c

        pred_range = pred_high - pred_low
        if pred_range <= 0:
            continue

        close_position = (pred_close - pred_low) / pred_range

        # Direction from close_position
        if close_position >= long_threshold:
            direction = "LONG"
        elif close_position <= short_threshold:
            direction = "SHORT"
        else:
            continue  # SKIP

        # Entry at open of next candle
        candle_time = times[i + 1]
        candle_open = opens[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_groups.get(parent_ts, [])
        if not subs:
            continue

        # TP / SL prices
        if direction == "LONG":
            tp_price = candle_open * (1 + tp_pct / 100)
            sl_price = candle_open * (1 - sl_pct / 100)
        else:
            tp_price = candle_open * (1 - tp_pct / 100)
            sl_price = candle_open * (1 + sl_pct / 100)

        # Walk 1m — which hits first?
        exit_price = None
        exit_reason = None
        exit_minute = 0
        for sc_idx, sc in enumerate(subs):
            if direction == "LONG":
                if sc["h"] >= tp_price:
                    exit_price = tp_price; exit_reason = "TP"; exit_minute = sc_idx; break
                if sc["l"] <= sl_price:
                    exit_price = sl_price; exit_reason = "SL"; exit_minute = sc_idx; break
            else:
                if sc["l"] <= tp_price:
                    exit_price = tp_price; exit_reason = "TP"; exit_minute = sc_idx; break
                if sc["h"] >= sl_price:
                    exit_price = sl_price; exit_reason = "SL"; exit_minute = sc_idx; break

        if exit_reason is None:
            exit_price = closes[i + 1]
            exit_reason = "CLOSE"
            exit_minute = len(subs)

        if direction == "LONG":
            pnl_pct = (exit_price - candle_open) / candle_open * 100
        else:
            pnl_pct = (candle_open - exit_price) / candle_open * 100

        pnl_dollar = notional * pnl_pct / 100 - fee

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)

        trades.append({
            "win": pnl_dollar > 0,
            "pnl": round(pnl_dollar, 2),
            "side": direction,
            "exit_reason": exit_reason,
            "exit_minute": exit_minute,
            "close_position": round(close_position, 3),
            "hour_utc": dt.hour,
            "day_of_week": dt.weekday(),
        })

    # ── Compile results ──
    if not trades:
        return {"error": "no trades"}

    total = len(trades)
    wins = sum(1 for t in trades if t["win"])
    wr = round(wins / total * 100, 1)
    total_pnl = round(sum(t["pnl"] for t in trades), 2)

    first_ts = times[window + 1]
    last_ts = times[-1]
    period_days = max((last_ts - first_ts) / 86400000, 1)
    ppd = round(total_pnl / period_days, 2)
    trades_per_day = round(total / period_days, 2)

    # Per direction
    longs = [t for t in trades if t["side"] == "LONG"]
    shorts = [t for t in trades if t["side"] == "SHORT"]

    # Per hour
    hour_stats = defaultdict(lambda: {"w": 0, "t": 0, "pnl": 0})
    for t in trades:
        h = t["hour_utc"]
        hour_stats[h]["t"] += 1
        hour_stats[h]["pnl"] += t["pnl"]
        if t["win"]:
            hour_stats[h]["w"] += 1

    per_hour = {}
    for h, s in sorted(hour_stats.items()):
        per_hour[str(h)] = {
            "trades": s["t"],
            "wr": round(s["w"] / s["t"] * 100, 1) if s["t"] > 0 else 0,
            "pnl": round(s["pnl"], 2),
        }

    # Per close_position bucket
    cp_stats = defaultdict(lambda: {"w": 0, "t": 0, "pnl": 0})
    for t in trades:
        cp = t["close_position"]
        if cp >= 0.85:
            b = "85-100"
        elif cp >= 0.70:
            b = "70-85"
        elif cp <= 0.15:
            b = "0-15"
        elif cp <= 0.30:
            b = "15-30"
        else:
            b = "30-70"
        cp_stats[b]["t"] += 1
        cp_stats[b]["pnl"] += t["pnl"]
        if t["win"]:
            cp_stats[b]["w"] += 1

    per_bucket = {}
    for b, s in cp_stats.items():
        per_bucket[b] = {
            "trades": s["t"],
            "wr": round(s["w"] / s["t"] * 100, 1) if s["t"] > 0 else 0,
            "pnl": round(s["pnl"], 2),
        }

    # Exit reason
    tp_trades = [t for t in trades if t["exit_reason"] == "TP"]
    sl_trades = [t for t in trades if t["exit_reason"] == "SL"]
    close_trades = [t for t in trades if t["exit_reason"] == "CLOSE"]

    # Timing
    tp_minutes = [t["exit_minute"] for t in tp_trades]
    sl_minutes = [t["exit_minute"] for t in sl_trades]

    # Max DD
    equity = 0
    peak = 0
    max_dd = 0
    for t in trades:
        equity += t["pnl"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    # Weekly WR
    week_wrs = defaultdict(lambda: {"w": 0, "l": 0})
    for idx, t in enumerate(trades):
        wk = idx // 42  # ~42 trades per week estimate
        if t["win"]:
            week_wrs[wk]["w"] += 1
        else:
            week_wrs[wk]["l"] += 1

    weekly_wr_list = []
    for wk in week_wrs.values():
        tot = wk["w"] + wk["l"]
        if tot >= 2:
            weekly_wr_list.append(round(wk["w"] / tot * 100, 1))

    # Walk-forward
    split = int(total * 0.8)
    train_wr = round(sum(1 for t in trades[:split] if t["win"]) / split * 100, 1) if split > 0 else 0
    test_wr = round(sum(1 for t in trades[split:] if t["win"]) / (total - split) * 100, 1) if total > split else 0
    wf_ratio = round(test_wr / train_wr, 2) if train_wr > 0 else 0

    # Worst streak
    worst_streak = 0
    streak = 0
    for t in trades:
        if not t["win"]:
            streak += 1
            worst_streak = max(worst_streak, streak)
        else:
            streak = 0

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "config": {
            "tp_pct": tp_pct, "sl_pct": sl_pct,
            "long_threshold": long_threshold, "short_threshold": short_threshold,
            "window": window,
        },
        "results": {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": wr,
            "total_pnl": total_pnl,
            "profit_per_day": ppd,
            "trades_per_day": trades_per_day,
            "max_drawdown": round(max_dd, 2),
        },
        "direction_breakdown": {
            "long": {
                "trades": len(longs),
                "wr": round(sum(1 for t in longs if t["win"]) / len(longs) * 100, 1) if longs else 0,
                "pnl": round(sum(t["pnl"] for t in longs), 2),
            },
            "short": {
                "trades": len(shorts),
                "wr": round(sum(1 for t in shorts if t["win"]) / len(shorts) * 100, 1) if shorts else 0,
                "pnl": round(sum(t["pnl"] for t in shorts), 2),
            },
        },
        "per_bucket": per_bucket,
        "per_hour": per_hour,
        "exit_reasons": {
            "TP": len(tp_trades),
            "SL": len(sl_trades),
            "CLOSE": len(close_trades),
        },
        "timing": {
            "avg_tp_min": round(sum(tp_minutes) / len(tp_minutes), 1) if tp_minutes else 0,
            "median_tp_min": sorted(tp_minutes)[len(tp_minutes)//2] if tp_minutes else 0,
            "avg_sl_min": round(sum(sl_minutes) / len(sl_minutes), 1) if sl_minutes else 0,
            "median_sl_min": sorted(sl_minutes)[len(sl_minutes)//2] if sl_minutes else 0,
        },
        "stability": {
            "train_wr": train_wr,
            "test_wr": test_wr,
            "walk_forward_ratio": wf_ratio,
            "worst_streak": worst_streak,
            "p5_weekly_wr": round(sorted(weekly_wr_list)[max(0, int(len(weekly_wr_list)*0.05))], 1) if weekly_wr_list else 0,
            "consistency_pct": round(sum(1 for w in weekly_wr_list if w >= 50) / len(weekly_wr_list) * 100, 1) if weekly_wr_list else 0,
        },
    }
"""
Paste di PALING BAWAH app.py
Pertanyaan simpel: dari open, naik 0.5% dulu atau turun 0.5% dulu?
Signal apa yang predict ini?
"""

@app.get("/tick/first-move")
def first_move(symbol: str = "DOGEUSDT", timeframe: str = "4h", window: int = 10, move_pct: float = 0.5):
    import sqlite3
    from collections import defaultdict
    from datetime import datetime, timezone

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT open, high, low, close, volume, open_time
        FROM klines WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
    """, (symbol, timeframe)).fetchall()
    sub_rows = conn.execute("""
        SELECT open, high, low, close, open_time
        FROM klines WHERE symbol = ? AND timeframe = '1m'
        ORDER BY open_time ASC
    """, (symbol,)).fetchall()
    conn.close()

    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)

    sub_groups = defaultdict(list)
    for sr in sub_rows:
        pt = (sr[4] // parent_ms) * parent_ms
        sub_groups[pt].append({"h": sr[1], "l": sr[2]})

    n = len(rows)
    opens = [r[0] for r in rows]
    highs = [r[1] for r in rows]
    lows = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    records = []

    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break

        candle_time = times[i + 1]
        candle_open = opens[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_groups.get(parent_ts, [])
        if not subs:
            continue

        up_target = candle_open * (1 + move_pct / 100)
        down_target = candle_open * (1 - move_pct / 100)

        # Walk 1m: which hits first?
        first_move = None
        first_minute = None
        for sc_idx, sc in enumerate(subs):
            up_hit = sc["h"] >= up_target
            down_hit = sc["l"] <= down_target
            if up_hit and down_hit:
                first_move = "BOTH"
                first_minute = sc_idx
                break
            elif up_hit:
                first_move = "UP"
                first_minute = sc_idx
                break
            elif down_hit:
                first_move = "DOWN"
                first_minute = sc_idx
                break

        if first_move is None:
            first_move = "NEITHER"
            first_minute = len(subs)

        # Context signals
        prev_dir = "bullish" if closes[i] > opens[i] else ("bearish" if closes[i] < opens[i] else "doji")
        prev_range = round((highs[i] - lows[i]) / opens[i] * 100, 4) if opens[i] > 0 else 0

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low = lows[i] * avg_l
        pred_close = closes[i] * avg_c
        pred_range = pred_high - pred_low
        close_position = (pred_close - pred_low) / pred_range if pred_range > 0 else 0.5

        # Where did prev candle close within its own range?
        prev_candle_range = highs[i] - lows[i]
        prev_close_position = (closes[i] - lows[i]) / prev_candle_range if prev_candle_range > 0 else 0.5

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)

        records.append({
            "first_move": first_move,
            "first_minute": first_minute,
            "prev_dir": prev_dir,
            "prev_range": prev_range,
            "close_position": round(close_position, 3),
            "prev_close_position": round(prev_close_position, 3),
            "hour": dt.hour,
            "dow": dt.weekday(),
        })

    # ── Analysis ──
    total = len(records)
    up_count = sum(1 for r in records if r["first_move"] == "UP")
    down_count = sum(1 for r in records if r["first_move"] == "DOWN")
    both_count = sum(1 for r in records if r["first_move"] == "BOTH")
    neither_count = sum(1 for r in records if r["first_move"] == "NEITHER")

    # Helper: for a subset, what % is UP first?
    def up_pct(subset):
        if not subset:
            return 0, 0
        up = sum(1 for r in subset if r["first_move"] == "UP")
        down = sum(1 for r in subset if r["first_move"] == "DOWN")
        t = up + down
        return round(up / t * 100, 1) if t > 0 else 0, t

    # ── Signal 1: prev_direction ──
    by_prev_dir = {}
    for pd in ["bullish", "bearish", "doji"]:
        subset = [r for r in records if r["prev_dir"] == pd]
        pct, cnt = up_pct(subset)
        by_prev_dir[pd] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt}

    # ── Signal 2: prev_close_position (where prev candle closed in its range) ──
    by_prev_cp = {}
    for label, lo, hi in [("bottom_0_20", 0, 0.2), ("low_20_40", 0.2, 0.4), ("mid_40_60", 0.4, 0.6), ("high_60_80", 0.6, 0.8), ("top_80_100", 0.8, 1.01)]:
        subset = [r for r in records if lo <= r["prev_close_position"] < hi]
        pct, cnt = up_pct(subset)
        by_prev_cp[label] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt}

    # ── Signal 3: close_position (predicted) ──
    by_cp = {}
    for label, lo, hi in [("very_low_0_20", 0, 0.2), ("low_20_40", 0.2, 0.4), ("mid_40_60", 0.4, 0.6), ("high_60_80", 0.6, 0.8), ("very_high_80_100", 0.8, 1.01)]:
        subset = [r for r in records if lo <= r["close_position"] < hi]
        pct, cnt = up_pct(subset)
        by_cp[label] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt}

    # ── Signal 4: hour ──
    by_hour = {}
    for h in sorted(set(r["hour"] for r in records)):
        subset = [r for r in records if r["hour"] == h]
        pct, cnt = up_pct(subset)
        by_hour[str(h)] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt}

    # ── Signal 5: prev_range (vol) ──
    all_ranges = sorted(r["prev_range"] for r in records)
    p33 = all_ranges[len(all_ranges) // 3]
    p66 = all_ranges[2 * len(all_ranges) // 3]
    by_vol = {}
    for label, lo, hi in [("low_vol", 0, p33), ("mid_vol", p33, p66), ("high_vol", p66, 999)]:
        subset = [r for r in records if lo <= r["prev_range"] < hi]
        pct, cnt = up_pct(subset)
        by_vol[label] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt, "range": f"{lo:.2f}-{hi:.2f}%"}

    # ── Signal 6: COMBO prev_dir + prev_close_position ──
    by_combo = {}
    for pd in ["bullish", "bearish"]:
        for cp_label, lo, hi in [("bottom_0_20", 0, 0.2), ("low_20_40", 0.2, 0.4), ("mid_40_60", 0.4, 0.6), ("high_60_80", 0.6, 0.8), ("top_80_100", 0.8, 1.01)]:
            subset = [r for r in records if r["prev_dir"] == pd and lo <= r["prev_close_position"] < hi]
            pct, cnt = up_pct(subset)
            if cnt >= 50:
                by_combo[f"{pd}_{cp_label}"] = {"up_first_pct": pct, "down_first_pct": round(100 - pct, 1), "trades": cnt}

    # ── Timing ──
    up_minutes = [r["first_minute"] for r in records if r["first_move"] == "UP"]
    down_minutes = [r["first_minute"] for r in records if r["first_move"] == "DOWN"]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "move_pct": move_pct,
        "total_candles": total,
        "overall": {
            "up_first": up_count,
            "down_first": down_count,
            "both_same_minute": both_count,
            "neither": neither_count,
            "up_first_pct": round(up_count / (up_count + down_count) * 100, 1) if (up_count + down_count) > 0 else 0,
        },
        "timing": {
            "up_median_min": sorted(up_minutes)[len(up_minutes)//2] if up_minutes else 0,
            "down_median_min": sorted(down_minutes)[len(down_minutes)//2] if down_minutes else 0,
        },
        "by_prev_direction": by_prev_dir,
        "by_prev_close_position": by_prev_cp,
        "by_predicted_close_position": by_cp,
        "by_hour": by_hour,
        "by_prev_vol": by_vol,
        "by_combo_dir_cp": by_combo,
    }
