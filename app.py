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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester, StrategyConfig, BacktestResult, ENTRY_LOGICS

app = FastAPI(title="BabaBot Backtesting API", version="1.2.0")
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
        "endpoints": ["/backtest", "/backtest/batch", "/health", "/strategies", "/fetch-data", "/fetch-status"]
    }

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
    return result.to_dict()

@app.post("/backtest/batch")
def run_batch_backtest(req: BatchBacktestRequest, _=Security(verify_token)):
    if len(req.configs) > 50:
        raise HTTPException(status_code=400, detail="Max 50 configs per batch request")
    
    results = []
    for r in req.configs:
        single_result = run_backtest(r)
        results.append(single_result)
    
    meets = [r for r in results if r.get("meets_criteria")]
    return {
        "total": len(results),
        "meets_criteria": len(meets),
        "results": results
    }
