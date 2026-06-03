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
from backtesting_core import Backtester, StrategyConfig, BacktestResult, ENTRY_LOGICS

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
    timeframe: str = "15m"
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None  # Level 2: AND confirmation
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
    """List semua entry logics dan capabilities."""
    return {
        "entry_logics": ENTRY_LOGICS,
        "multi_entry": {
            "supported": True,
            "description": "Set entry_logic_2 for AND confirmation (both must fire within 3 candles)",
            "example": {"entry_logic": "supertrend_flip", "entry_logic_2": "macd_cross"}
        },
        "supported_pairs": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT"],
        "supported_timeframes": ["15m", "1h"],
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
