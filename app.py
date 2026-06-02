"""
BabaBot AI Strategy Discovery — Step 1C: API Endpoint
FastAPI server expose POST /backtest endpoint.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8000
    
    POST /backtest
    {
        "symbol": "BTCUSDT",
        "timeframe": "5m", 
        "entry_logic": "ema_cross",
        "indicators": {"ema_fast": 9, "ema_slow": 21},
        "sl_pct": 0.3,
        "tp_pct": 0.8,
        "days": 90
    }
"""

import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester, StrategyConfig, BacktestResult

app = FastAPI(title="BabaBot Backtesting API", version="1.0.0")
security = HTTPBearer(auto_error=False)

# Auth token dari environment variable
API_TOKEN = os.environ.get("BACKTEST_API_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

bt = Backtester(db_path=DB_PATH)


# ============================================================
# REQUEST / RESPONSE MODELS
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


# ============================================================
# AUTH
# ============================================================

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_TOKEN:
        return True  # No token configured = open (dev mode)
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
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/backtest", "/backtest/batch", "/health", "/strategies"]
    }

@app.get("/health")
def health():
    import sqlite3
    from pathlib import Path
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
    """List semua entry logics yang tersedia."""
    return {
        "entry_logics": [
            "ema_cross",
            "ema_cross_rsi",
            "ema_trend_pullback",
            "rsi_ob_os",
            "macd_cross",
            "macd_zero",
            "bb_bounce",
            "stoch_cross",
        ],
        "supported_pairs": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT"],
        "supported_timeframes": ["1m", "3m", "5m", "15m", "1h"],
        "directions": ["long", "short", "both"],
        "session_filters": ["asia", "london", "ny", None]
    }

@app.post("/backtest")
def run_backtest(req: BacktestRequest, _=Security(verify_token)):
    """
    Run single backtest.
    Returns comprehensive metrics.
    """
    # Merge default indicators dengan yang dikirim
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
    """
    Run multiple backtests sekaligus.
    Returns list of results.
    Max 50 configs per request.
    """
    if len(req.configs) > 50:
        raise HTTPException(status_code=400, detail="Max 50 configs per batch request")
    
    results = []
    for r in req.configs:
        single_result = run_backtest(r)
        results.append(single_result)
    
    # Summary
    meets = [r for r in results if r.get("meets_criteria")]
    return {
        "total": len(results),
        "meets_criteria": len(meets),
        "results": results
    }
