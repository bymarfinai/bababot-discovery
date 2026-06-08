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
from backtesting_core import Backtester, StrategyConfig, BacktestResult, ENTRY_LOGICS, calc_correlation, run_feature_study, run_marthias_study, test_ai_rules, bootstrap_validate_rules, run_sltp_optimization

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
    include_instances: bool = True  # False = summary only (smaller response)

@app.post("/backtest/feature-study")
def feature_study(req: FeatureStudyRequest, _=Security(verify_token)):
    """
    Marthias Method Step 3-4: Feature Study + Discover Differentiator.
    Runs signal across full data, extracts per-instance features, classifies outcomes.
    """
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

# ============================================================
# PIPELINE 2 CRON — Background thread hits Worker run-next
# ============================================================

import requests as _requests

_p2_cron_running = False
_p2_cron_lock = threading.Lock()
_p2_interval = int(os.environ.get("P2_CRON_INTERVAL", "180"))  # default 3 minutes
_p2_worker_url = os.environ.get("P2_WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev/discovery/marthias/run-next")

def _p2_cron_loop():
    global _p2_cron_running
    print(f"[P2 Cron] Started, interval={_p2_interval}s, url={_p2_worker_url}")
    while _p2_cron_running:
        try:
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

# Auto-start P2 cron on app startup
@app.on_event("startup")
def _auto_start_p2_cron():
    if os.environ.get("P2_CRON_ENABLED", "true").lower() == "true":
        global _p2_cron_running
        _p2_cron_running = True
        t = threading.Thread(target=_p2_cron_loop, daemon=True)
        t.start()
        print(f"[P2 Cron] Auto-started on startup")
