import sqlite3

DB_PATH = "/app/data/market_data.db"

print("Connecting to database...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Disabling journal mode for faster deletion...")
cursor.execute("PRAGMA journal_mode = OFF")

print("Deleting klines rows where timeframe IN ('3m', '5m')...")
cursor.execute("DELETE FROM klines WHERE timeframe IN ('3m', '5m')")
deleted = cursor.rowcount
conn.commit()
print(f"Deleted {deleted} rows.")

cursor.execute("SELECT COUNT(*) FROM klines")
remaining = cursor.fetchone()[0]
print(f"Remaining rows in klines table: {remaining}")

conn.close()
print("Database connection closed. Cleanup complete.")
