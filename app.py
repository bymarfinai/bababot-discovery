"""
BabaBot AI Strategy Discovery — Step 1C: API Endpoint
FastAPI server expose POST /backtest endpoint.

Usage:
    uvicorn app:app --host 0.0.0.0 --port $PORT
"""

import os
import subprocess
import threading
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester, StrategyConfig

app = FastAPI(title="BabaBot Backtesting API", version="1.0.0")
security = HTTPBearer(auto_error=False)

API_TOKEN = os.environ.get("BACKTEST_API_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

bt = Backtester(db_path=DB_PATH)

# Track fetch status
fetch_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None,
}


# ============================================================
# REQUEST MODELS
# ============================================================

class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "5m"
    entry_logic: str = "ema_cross"
    indicators: dict = {}
    sl_pct: float = 0.3
    tp_pct: float = 0.8
    fee_pct: float = 0.08
    slippage_pct: float = 0.02
    initial_capital: float = 1000.0
    position_size_pct: float = 100.0
    days: int = 90
    train_pct: float = 75.0
    direction: str = "both"
    session_filter: Optional[str] = None

class BatchBacktestRequest(BaseModel):
    configs: list[BacktestRequest]

class FetchRequest(BaseModel):
    days: int = 90
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
# BACKGROUND FETCH
# ============================================================

def _run_fetch(days: int, pairs: Optional[list], timeframes: Optional[list]):
    global fetch_status
    fetch_status["running"] = True
    fetch_status["error"] = None
    
    try:
        from data_fetcher import fetch_all
        results = fetch_all(
            pairs=pairs,
            timeframes=timeframes,
            days=days,
            db_path=DB_PATH
        )
        
        total_new = sum(r.get("new_candles", 0) for r in results)
        total_all = sum(r.get("total_candles", 0) for r in results)
        errors = sum(1 for r in results if r.get("status") == "error")
        
        from datetime import datetime, timezone
        fetch_status["last_result"] = {
            "new_candles": total_new,
            "total_candles": total_all,
            "errors": errors,
            "configs_run": len(results),
        }
        fetch_status["last_run"] = datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        fetch_status["error"] = str(e)
    finally:
        fetch_status["running"] = False


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():
    return {
        "service": "BabaBot Backtesting API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/backtest", "/backtest/batch", "/health", "/strategies", "/fetch-data", "/fetch-status"]
    }

@app.get("/health")
def health():
    db_ok = Path(DB_PATH).exists()
    candle_count = 0
    pairs_info = []
    if db_ok:
        try:
            conn = sqlite3.connect(DB_PATH)
            candle_count = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            pairs_info = conn.execute("""
                SELECT symbol, timeframe, COUNT(*) as candles
                FROM klines GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """).fetchall()
            conn.close()
        except:
            pass
    
    return {
        "status": "ok",
        "db_exists": db_ok,
        "total_candles": candle_count,
        "db_path": DB_PATH,
        "data": [{"symbol": r[0], "timeframe": r[1], "candles": r[2]} for r in pairs_info],
        "fetch_running": fetch_status["running"],
        "last_fetch": fetch_status["last_run"],
    }

@app.get("/strategies")
def list_strategies():
    return {
        "entry_logics": [
            "ema_cross", "ema_cross_rsi", "ema_trend_pullback",
            "rsi_ob_os", "macd_cross", "macd_zero",
            "bb_bounce", "stoch_cross",
        ],
        "supported_pairs": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT"],
        "supported_timeframes": ["1m", "3m", "5m", "15m", "1h"],
        "directions": ["long", "short", "both"],
        "session_filters": ["asia", "london", "ny", None]
    }

@app.post("/fetch-data")
def fetch_data(req: FetchRequest, background_tasks: BackgroundTasks, _=Security(verify_token)):
    """
    Trigger data fetch dari Binance di background.
    Tidak blocking — langsung return, fetch jalan di background.
    Cek progress di /fetch-status
    """
    if fetch_status["running"]:
        return {
            "status": "already_running",
            "message": "Fetch sedang berjalan. Cek /fetch-status untuk progress."
        }
    
    background_tasks.add_task(
        _run_fetch,
        days=req.days,
        pairs=req.pairs,
        timeframes=req.timeframes
    )
    
    return {
        "status": "started",
        "message": f"Fetching {req.days} hari data di background.",
        "pairs": req.pairs or ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT"],
        "timeframes": req.timeframes or ["1m", "3m", "5m", "15m", "1h"],
        "check_progress": "/fetch-status"
    }

@app.get("/fetch-status")
def get_fetch_status():
    """Cek status fetch yang sedang atau sudah berjalan."""
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
        "running": fetch_status["running"],
        "last_run": fetch_status["last_run"],
        "last_result": fetch_status["last_result"],
        "error": fetch_status["error"],
        "current_candles_in_db": candle_count,
    }

@app.post("/backtest")
def run_backtest(req: BacktestRequest, _=Security(verify_token)):
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail="Database belum ada. Hit POST /fetch-data dulu untuk download data."
        )
    
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
    )
    
    result = bt.run(config)
    return result.to_dict()

@app.post("/backtest/batch")
def run_batch_backtest(req: BatchBacktestRequest, _=Security(verify_token)):
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail="Database belum ada. Hit POST /fetch-data dulu."
        )
    
    if len(req.configs) > 50:
        raise HTTPException(status_code=400, detail="Max 50 configs per batch")
    
    results = []
    for r in req.configs:
        single = run_backtest(r)
        results.append(single)
    
    meets = [r for r in results if r.get("meets_criteria")]
    return {
        "total": len(results),
        "meets_criteria": len(meets),
        "results": results
    }
