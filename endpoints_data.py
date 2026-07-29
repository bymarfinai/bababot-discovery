"""Data endpoints: /data/status, /data/list-files, /data/db-size, /data/vacuum, /fetch-data, /fetch-status, /strategies."""
import os
import time
import sqlite3
import threading
from pathlib import Path
from fastapi import APIRouter, Security
from shared import DB_PATH, ALL_PAIRS, ALL_TIMEFRAMES, FetchDataRequest, verify_token, fetch_state

router = APIRouter()


@router.get("/data/list-files")
def list_volume_files():
    try:
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


@router.get("/data/db-size")
def db_size():
    try:
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


@router.get("/data/vacuum")
def vacuum_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")
        conn.close()
        size_mb = round(os.path.getsize(DB_PATH) / 1024 / 1024, 1)
        return {"ok": True, "db_size_mb": size_mb}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/data/status")
def data_status():
    if not Path(DB_PATH).exists():
        return {"status": "error", "error": "database not found"}
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT symbol, timeframe, COUNT(*) as candles,
                   MIN(open_time) as first_ts, MAX(open_time) as last_ts
            FROM klines GROUP BY symbol, timeframe ORDER BY symbol, timeframe
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
        last_row = conn.execute("SELECT MAX(open_time) FROM klines").fetchone()
        last_fetch = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(last_row[0] / 1000)) if last_row and last_row[0] else None
        breakdown = []
        for symbol, tfs in pairs.items():
            for tf, info in tfs.items():
                breakdown.append({"symbol": symbol, "timeframe": tf, "candles": info["candles"]})
        return {"status": "ok", "total_candles": total_candles, "last_fetch": last_fetch, "pairs": pairs, "breakdown": breakdown}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


@router.get("/strategies")
def list_strategies():
    from backtesting_core import ENTRY_LOGICS
    return {
        "entry_logics": ENTRY_LOGICS,
        "supported_pairs": ALL_PAIRS,
        "supported_timeframes": ALL_TIMEFRAMES,
        "directions": ["long", "short", "both"],
    }


def _fetch_via_binance_vision(days, pairs, timeframes, db_path):
    """Fetch OHLCV from data.binance.vision (bulk CSV downloads)."""
    import requests, zipfile, csv, io
    from datetime import datetime, timedelta
    total_fetched = 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS klines (
        symbol TEXT, timeframe TEXT, open_time INTEGER,
        open REAL, high REAL, low REAL, close REAL, volume REAL,
        close_time INTEGER, quote_volume REAL, trades INTEGER,
        taker_buy_volume REAL, taker_buy_quote_volume REAL,
        PRIMARY KEY (symbol, timeframe, open_time))""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_klines_sym_tf ON klines(symbol, timeframe)")
    conn.commit()
    end_date = datetime.utcnow() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    base_url = "https://data.binance.vision/data/futures/um/daily/klines"
    total_tasks = len(pairs) * len(timeframes)
    completed = 0
    for pair in pairs:
        for tf in timeframes:
            completed += 1
            pair_candles = 0
            errors = 0
            for i, date_str in enumerate(dates):
                fetch_state["progress"] = f"[{completed}/{total_tasks}] {pair} {tf} — day {i+1}/{len(dates)}"
                date_ts_start = int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)
                existing = cursor.execute("SELECT COUNT(*) FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?",
                    (pair, tf, date_ts_start, date_ts_start + 86400000)).fetchone()[0]
                if existing > 0:
                    continue
                try:
                    r = requests.get(f"{base_url}/{pair}/{tf}/{pair}-{tf}-{date_str}.zip", timeout=30)
                    if r.status_code != 200:
                        if r.status_code != 404: errors += 1
                        continue
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    csv_data = z.read(z.namelist()[0]).decode("utf-8")
                    rows = []
                    for row in csv.reader(io.StringIO(csv_data)):
                        if len(row) < 11: continue
                        try:
                            rows.append((pair, tf, int(row[0]), float(row[1]), float(row[2]), float(row[3]),
                                float(row[4]), float(row[5]), int(row[6]), float(row[7]), int(row[8]),
                                float(row[9]), float(row[10])))
                        except: continue
                    if rows:
                        cursor.executemany("INSERT OR REPLACE INTO klines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
                        conn.commit()
                        pair_candles += len(rows)
                        total_fetched += len(rows)
                        fetch_state["total_candles"] = total_fetched
                except:
                    errors += 1
                    if errors > 10: break
                time.sleep(0.1)
    conn.close()
    return total_fetched


@router.post("/fetch-data")
def fetch_data(req: FetchDataRequest):
    if fetch_state["status"] == "running":
        return {"status": "already_running", "message": "Check /fetch-status"}
    pairs = req.pairs or ALL_PAIRS
    timeframes = req.timeframes or ALL_TIMEFRAMES
    fetch_state.update({"status": "running", "days": req.days, "progress": "Starting...", "total_candles": 0, "error": None})
    def run_fetch():
        try:
            total = _fetch_via_binance_vision(req.days, pairs, timeframes, DB_PATH)
            fetch_state["status"] = "done"
            fetch_state["progress"] = f"Completed — {total:,} candles"
        except Exception as e:
            fetch_state["status"] = "error"
            fetch_state["error"] = str(e)
    threading.Thread(target=run_fetch, daemon=True).start()
    return {"status": "fetching", "days": req.days, "pairs": pairs, "timeframes": timeframes}


@router.get("/fetch-status")
def fetch_status_endpoint():
    result = {"fetch_state": fetch_state, "total_candles": 0, "breakdown": []}
    if Path(DB_PATH).exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            result["total_candles"] = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            result["breakdown"] = [{"symbol": r[0], "timeframe": r[1], "candles": r[2]}
                for r in conn.execute("SELECT symbol, timeframe, COUNT(*) FROM klines GROUP BY symbol, timeframe ORDER BY symbol, timeframe").fetchall()]
            conn.close()
        except Exception as e:
            result["error"] = str(e)
    return result
