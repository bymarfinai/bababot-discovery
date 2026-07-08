"""
DB Recovery Script - runs before app startup.
- If DB is readable: no-op
- If corrupt: backup + try .recover, else create fresh empty schema
"""
import os
import sqlite3
import shutil
import subprocess

DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def test_db(path):
    try:
        conn = sqlite3.connect(path)
        conn.execute("SELECT COUNT(*) FROM klines").fetchone()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] Test failed: {e}")
        return False


def create_fresh_schema(path):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS klines (
            symbol TEXT, timeframe TEXT, open_time INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            close_time INTEGER, quote_volume REAL, trades INTEGER,
            taker_buy_volume REAL, taker_buy_quote_volume REAL,
            PRIMARY KEY (symbol, timeframe, open_time)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_klines_sym_tf ON klines(symbol, timeframe)")
    conn.commit()
    conn.close()


def try_recover(corrupt_path, target_path):
    """Try sqlite3 .recover CLI."""
    try:
        result = subprocess.run(
            f"sqlite3 {corrupt_path} '.recover' | sqlite3 {target_path}",
            shell=True, capture_output=True, text=True, timeout=300,
        )
        print(f"[DB] Recover stdout: {result.stdout[:500]}")
        print(f"[DB] Recover stderr: {result.stderr[:500]}")
        return test_db(target_path)
    except Exception as e:
        print(f"[DB] Recover failed: {e}")
        return False


def main():
    print(f"[DB] Checking {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("[DB] Not exists, creating fresh schema")
        create_fresh_schema(DB_PATH)
        return

    if test_db(DB_PATH):
        print("[DB] OK, no recovery needed")
        return

    print("[DB] Corrupt! Starting recovery flow...")
    backup = DB_PATH + ".corrupt.bak"
    if os.path.exists(backup):
        os.remove(backup)
    shutil.move(DB_PATH, backup)
    print(f"[DB] Corrupt backup at {backup}")

    if try_recover(backup, DB_PATH):
        print("[DB] Recovery SUCCESS via .recover")
        return

    print("[DB] Recovery failed, creating fresh empty schema")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    create_fresh_schema(DB_PATH)
    print("[DB] Fresh DB ready. Use /fetch-data to populate.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[DB] Recovery script fatal error: {e}")
