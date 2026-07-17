"""Funding Rate + Open Interest data endpoint.

Fetches from Binance via ccxt, caches to SQLite.
Used for BBC discovery: correlate FR/OI with trade outcomes.
"""
import os, time, sqlite3
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter(prefix="/data", tags=["data"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _init_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS funding_rate (
        symbol TEXT, timestamp INTEGER, rate REAL,
        PRIMARY KEY (symbol, timestamp))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS open_interest (
        symbol TEXT, timestamp INTEGER, oi REAL, oi_value REAL,
        PRIMARY KEY (symbol, timestamp))""")
    conn.commit(); conn.close()


def _fetch_funding_rate(symbol, start_ts, end_ts):
    """Fetch funding rate from Binance via ccxt."""
    import ccxt
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    all_rates = []
    since = start_ts
    while since < end_ts:
        try:
            rates = exchange.fetch_funding_rate_history(symbol, since=since, limit=1000)
            if not rates: break
            all_rates.extend(rates)
            since = rates[-1]['timestamp'] + 1
            if len(rates) < 1000: break
            time.sleep(0.1)
        except Exception as e:
            print(f"[FR] Error fetching {symbol}: {e}")
            break
    return all_rates


def _fetch_open_interest(symbol, start_ts, end_ts):
    """Fetch historical open interest from Binance."""
    import requests as req
    all_oi = []
    end = end_ts
    while end > start_ts:
        try:
            r = req.get("https://fapi.binance.com/futures/data/openInterestHist",
                params={"symbol": symbol.replace("/", ""), "period": "1h",
                        "startTime": start_ts, "endTime": end, "limit": 500}, timeout=30)
            data = r.json()
            if not isinstance(data, list) or not data: break
            all_oi.extend(data)
            end = data[0]['timestamp'] - 1
            if len(data) < 500: break
            time.sleep(0.2)
        except Exception as e:
            print(f"[OI] Error fetching {symbol}: {e}")
            break
    return all_oi


@router.get("/funding_rate")
def get_funding_rate(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(30, ge=1, le=1000),
):
    """Get funding rate data. Fetches from Binance if not cached."""
    _init_tables()
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ts = now_ms - (days * 86400 * 1000)

    conn = sqlite3.connect(DB_PATH)
    # Check cache
    rows = conn.execute(
        "SELECT timestamp, rate FROM funding_rate WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
        (symbol, start_ts, now_ms)).fetchall()

    if len(rows) < days * 2:  # expect ~3 per day, minimum 2
        print(f"[FR] Cache miss for {symbol} ({len(rows)} rows), fetching...")
        ccxt_symbol = symbol.replace("USDT", "/USDT")
        rates = _fetch_funding_rate(ccxt_symbol, start_ts, now_ms)
        if rates:
            for r in rates:
                try:
                    conn.execute("INSERT OR IGNORE INTO funding_rate (symbol, timestamp, rate) VALUES (?,?,?)",
                        (symbol, r['timestamp'], r['info'].get('fundingRate', r.get('fundingRate', 0))))
                except: pass
            conn.commit()
            rows = conn.execute(
                "SELECT timestamp, rate FROM funding_rate WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
                (symbol, start_ts, now_ms)).fetchall()

    conn.close()
    return {
        "symbol": symbol, "days": days, "count": len(rows),
        "rates": [{"timestamp": r[0], "rate": r[1]} for r in rows]
    }


@router.get("/open_interest")
def get_open_interest(
    symbol: str = Query("BTCUSDT"),
    days: int = Query(30, ge=1, le=1000),
):
    """Get open interest data. Fetches from Binance if not cached."""
    _init_tables()
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ts = now_ms - (days * 86400 * 1000)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT timestamp, oi, oi_value FROM open_interest WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
        (symbol, start_ts, now_ms)).fetchall()

    if len(rows) < days * 12:  # expect 24 per day, minimum 12
        print(f"[OI] Cache miss for {symbol} ({len(rows)} rows), fetching...")
        oi_data = _fetch_open_interest(symbol, start_ts, now_ms)
        if oi_data:
            for o in oi_data:
                try:
                    conn.execute("INSERT OR IGNORE INTO open_interest (symbol, timestamp, oi, oi_value) VALUES (?,?,?,?)",
                        (symbol, o['timestamp'], float(o['sumOpenInterest']), float(o['sumOpenInterestValue'])))
                except: pass
            conn.commit()
            rows = conn.execute(
                "SELECT timestamp, oi, oi_value FROM open_interest WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
                (symbol, start_ts, now_ms)).fetchall()

    conn.close()
    return {
        "symbol": symbol, "days": days, "count": len(rows),
        "data": [{"timestamp": r[0], "oi": r[1], "oi_value": r[2]} for r in rows]
    }
