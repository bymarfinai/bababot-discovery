"""Shared state and utilities for all endpoint routers."""
import os
import sqlite3
from pathlib import Path
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester

DB_PATH = os.environ.get("DB_PATH", "market_data.db")
API_TOKEN = os.environ.get("BACKTEST_API_TOKEN", "")
security = HTTPBearer(auto_error=False)

bt = Backtester(db_path=DB_PATH)

ALL_PAIRS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "YFIUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "PEPEUSDT"]
ALL_TIMEFRAMES = ["5m", "15m", "1h", "4h"]

fetch_state = {"status": "idle", "days": 0, "progress": "", "total_candles": 0, "error": None}

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_TOKEN:
        return True
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return True

# ── Pydantic models (shared across routers) ──
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
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    include_equity: bool = False
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
