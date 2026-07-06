"""
BabaBot AI Strategy Discovery — Step 1A: Data Fetcher
Tarik historical klines dari Binance data.binance.vision (bulk CSV).

Usage:
    python data_fetcher.py                  # Fetch semua pair & timeframe (default 90 hari)
    python data_fetcher.py --days 180       # Fetch 180 hari terakhir
    python data_fetcher.py --pair BTCUSDT   # Fetch 1 pair aja
    python data_fetcher.py --tf 5m          # Fetch 1 timeframe aja
    python data_fetcher.py --check          # Cek isi database
"""

import requests
import sqlite3
import csv
import io
import zipfile
import time
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "LINKUSDT", "AVAXUSDT", "ADAUSDT",
]
TIMEFRAMES = ["1m", "15m", "1h", "4h"]
DEFAULT_DAYS = 1825
DB_PATH = Path(__file__).parent / "market_data.db"
BASE_URL = "https://data.binance.vision/data/futures/um/daily/klines"


# ============================================================
# DATABASE
# ============================================================

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS klines (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            close_time INTEGER NOT NULL,
            quote_volume REAL NOT NULL,
            trades INTEGER NOT NULL,
            taker_buy_volume REAL NOT NULL,
            taker_buy_quote_volume REAL NOT NULL,
            PRIMARY KEY (symbol, timeframe, open_time)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_klines_lookup 
        ON klines (symbol, timeframe, open_time)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fetch_log (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            fetch_date TEXT NOT NULL,
            candles_added INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (symbol, timeframe, fetch_date)
        )
    """)
    conn.commit()
    return conn


# ============================================================
# BINANCE DATA VISION (Bulk CSV Download)
# ============================================================

def fetch_daily_klines(symbol: str, timeframe: str, date_str: str) -> list:
    """
    Download 1 hari klines dari data.binance.vision.
    date_str format: "2026-05-01"
    Returns list of kline tuples.
    """
    url = f"{BASE_URL}/{symbol}/{timeframe}/{symbol}-{timeframe}-{date_str}.zip"
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return []  # Data belum tersedia untuk tanggal ini
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    ⚠️ {date_str}: {e}")
        return []
    
    # Unzip dan parse CSV
    try:
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        csv_filename = zf.namelist()[0]
        with zf.open(csv_filename) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8'))
            rows = []
            for row in reader:
                if len(row) < 11:
                    continue
                try:
                    rows.append((
                        symbol,
                        timeframe,
                        int(row[0]),      # open_time
                        float(row[1]),    # open
                        float(row[2]),    # high
                        float(row[3]),    # low
                        float(row[4]),    # close
                        float(row[5]),    # volume
                        int(row[6]),      # close_time
                        float(row[7]),    # quote_volume
                        int(row[8]),      # trades
                        float(row[9]),    # taker_buy_volume
                        float(row[10]),   # taker_buy_quote_volume
                    ))
                except (ValueError, IndexError):
                    continue
            return rows
    except Exception as e:
        print(f"    ⚠️ Parse error {date_str}: {e}")
        return []


def save_klines(conn: sqlite3.Connection, rows: list, symbol: str, timeframe: str, date_str: str) -> int:
    if not rows:
        return 0
    conn.executemany("""
        INSERT OR IGNORE INTO klines 
        (symbol, timeframe, open_time, open, high, low, close, volume,
         close_time, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.execute("""
        INSERT OR REPLACE INTO fetch_log (symbol, timeframe, fetch_date, candles_added, fetched_at)
        VALUES (?, ?, ?, ?, ?)
    """, (symbol, timeframe, date_str, len(rows), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return len(rows)


def is_date_fetched(conn: sqlite3.Connection, symbol: str, timeframe: str, date_str: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM fetch_log WHERE symbol=? AND timeframe=? AND fetch_date=?",
        (symbol, timeframe, date_str)
    ).fetchone()
    return row is not None


# ============================================================
# MAIN FETCH
# ============================================================

def fetch_pair_timeframe(conn, symbol: str, timeframe: str, days: int) -> dict:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days)
    
    total_new = 0
    skipped = 0
    errors = 0
    
    current = start_date
    while current < today:  # Skip hari ini (belum complete)
        date_str = current.strftime("%Y-%m-%d")
        
        if is_date_fetched(conn, symbol, timeframe, date_str):
            skipped += 1
            current += timedelta(days=1)
            continue
        
        rows = fetch_daily_klines(symbol, timeframe, date_str)
        if rows:
            saved = save_klines(conn, rows, symbol, timeframe, date_str)
            total_new += saved
        else:
            errors += 1
        
        current += timedelta(days=1)
        time.sleep(0.15)  # Rate limit courtesy
    
    total = conn.execute(
        "SELECT COUNT(*) FROM klines WHERE symbol=? AND timeframe=?",
        (symbol, timeframe)
    ).fetchone()[0]
    
    return {
        "symbol": symbol, "timeframe": timeframe,
        "new_candles": total_new, "total_candles": total,
        "skipped_days": skipped, "errors": errors,
        "status": "ok"
    }


def fetch_all(pairs=None, timeframes=None, days=DEFAULT_DAYS, db_path=DB_PATH) -> list:
    pairs = pairs or PAIRS
    timeframes = timeframes or TIMEFRAMES
    conn = init_db(db_path)
    results = []
    total_jobs = len(pairs) * len(timeframes)
    current = 0
    
    print(f"\n{'='*60}")
    print(f"🤖 BabaBot Data Fetcher v1.0")
    print(f"{'='*60}")
    print(f"Source: data.binance.vision (Futures USDM)")
    print(f"Pairs: {', '.join(pairs)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Days: {days} | DB: {db_path}")
    print(f"{'='*60}\n")
    
    for symbol in pairs:
        for tf in timeframes:
            current += 1
            print(f"[{current}/{total_jobs}] {symbol} {tf}...", end=" ", flush=True)
            
            try:
                r = fetch_pair_timeframe(conn, symbol, tf, days)
                results.append(r)
                print(f"✅ +{r['new_candles']} new | {r['total_candles']} total | {r['skipped_days']} skipped")
            except Exception as e:
                print(f"❌ {e}")
                results.append({"symbol": symbol, "timeframe": tf, "status": "error", "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FETCH SUMMARY")
    print(f"{'='*60}")
    total_new = sum(r.get("new_candles", 0) for r in results)
    total_all = sum(r.get("total_candles", 0) for r in results)
    total_err = sum(1 for r in results if r["status"] == "error")
    print(f"  New candles fetched: {total_new:,}")
    print(f"  Total candles in DB: {total_all:,}")
    if total_err:
        print(f"  Errors: {total_err}")
    db_size = Path(db_path).stat().st_size / (1024 * 1024)
    print(f"  Database size: {db_size:.1f} MB")
    print(f"{'='*60}\n")
    
    conn.close()
    return results


# ============================================================
# DATA CHECK
# ============================================================

def check_data(db_path=DB_PATH):
    if not Path(db_path).exists():
        print("Database belum ada. Run fetch dulu.")
        return
    
    conn = sqlite3.connect(db_path)
    print(f"\n{'='*60}")
    print(f"📋 DATA INVENTORY — {db_path}")
    print(f"{'='*60}")
    
    rows = conn.execute("""
        SELECT symbol, timeframe, 
               COUNT(*) as candles,
               MIN(open_time) as first_ts,
               MAX(open_time) as last_ts
        FROM klines 
        GROUP BY symbol, timeframe
        ORDER BY symbol, timeframe
    """).fetchall()
    
    if not rows:
        print("  (empty)")
    else:
        current_symbol = None
        for symbol, tf, count, first_ts, last_ts in rows:
            if symbol != current_symbol:
                if current_symbol:
                    print()
                print(f"  {symbol}:")
                current_symbol = symbol
            first_dt = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            print(f"    {tf:>4}: {count:>8,} candles | {first_dt} → {last_dt}")
    
    db_size = Path(db_path).stat().st_size / (1024 * 1024)
    print(f"\n  Total DB size: {db_size:.1f} MB")
    print(f"{'='*60}\n")
    conn.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BabaBot Data Fetcher")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--pair", type=str, help="e.g. BTCUSDT")
    parser.add_argument("--tf", type=str, help="e.g. 5m")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    
    args = parser.parse_args()
    
    if args.check:
        check_data(args.db)
    else:
        pairs = [args.pair.upper()] if args.pair else None
        timeframes = [args.tf] if args.tf else None
        fetch_all(pairs=pairs, timeframes=timeframes, days=args.days, db_path=args.db)
        check_data(args.db)
