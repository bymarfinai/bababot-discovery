"""
cleanup_klines.py — Disk-full resistant version

Hapus data timeframe 3m dan 5m dari database.
Robust untuk kondisi disk 100% penuh — pakai MEMORY journal dan batch delete kecil.
"""

import sqlite3
import os
import sys
import time

DB_PATH = "/app/data/market_data.db"

print("=" * 60)
print("KLINES CLEANUP — Disk-full resistant version")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Step 1: Hapus journal/WAL files yang mungkin nyangkut (free space)
# ─────────────────────────────────────────────────────────────
print("\n[Step 1] Cleaning up hanging journal files...")
for suffix in ["-journal", "-wal", "-shm"]:
    journal_file = DB_PATH + suffix
    if os.path.exists(journal_file):
        size_mb = os.path.getsize(journal_file) / (1024 * 1024)
        try:
            os.remove(journal_file)
            print(f"  ✅ Removed {os.path.basename(journal_file)} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ⚠️ Could not remove {journal_file}: {e}")
    else:
        print(f"  ℹ️  {os.path.basename(journal_file)} not present")

# Free space check
try:
    stat = os.statvfs("/app/data")
    free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
    total_mb = (stat.f_blocks * stat.f_frsize) / (1024 * 1024)
    print(f"\n[Disk] Free: {free_mb:.1f} MB / Total: {total_mb:.1f} MB")
except Exception as e:
    print(f"[Disk] Could not check free space: {e}")

# ─────────────────────────────────────────────────────────────
# Step 2: Open DB dengan MEMORY journal (no disk write for journal)
# ─────────────────────────────────────────────────────────────
print("\n[Step 2] Opening DB with MEMORY journal...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Try to set journal mode to MEMORY (no disk journal needed)
journal_mode_set = False
for mode in ["MEMORY", "OFF"]:
    try:
        cursor.execute(f"PRAGMA journal_mode = {mode}")
        result = cursor.fetchone()
        print(f"  ✅ Journal mode: {result[0] if result else mode}")
        journal_mode_set = True
        break
    except Exception as e:
        print(f"  ⚠️ Journal mode {mode} failed: {e}")

if not journal_mode_set:
    print("  ❌ Could not set any journal mode. Cleanup may fail.")

# Disable sync (faster + no disk sync required)
try:
    cursor.execute("PRAGMA synchronous = OFF")
    print("  ✅ Synchronous: OFF")
except Exception as e:
    print(f"  ⚠️ Could not disable sync: {e}")

# Temp store in memory
try:
    cursor.execute("PRAGMA temp_store = MEMORY")
    print("  ✅ Temp store: MEMORY")
except Exception as e:
    print(f"  ⚠️ Could not set temp store: {e}")

# ─────────────────────────────────────────────────────────────
# Step 3: Check what data exists before delete
# ─────────────────────────────────────────────────────────────
print("\n[Step 3] Current data counts:")
try:
    for tf in ["1m", "3m", "5m", "15m", "1h", "4h"]:
        try:
            cursor.execute("SELECT COUNT(*) FROM klines WHERE timeframe = ?", (tf,))
            count = cursor.fetchone()[0]
            print(f"  {tf}: {count:,} rows")
        except Exception as e:
            print(f"  {tf}: query failed ({e})")
except Exception as e:
    print(f"  Count query failed: {e}")

# ─────────────────────────────────────────────────────────────
# Step 4: Delete in TINY batches (safer for disk-full)
# ─────────────────────────────────────────────────────────────
def delete_in_batches(tf, initial_batch=100):
    """Delete rows in progressively bigger batches as space frees up."""
    total_deleted = 0
    batch_size = initial_batch
    consecutive_failures = 0

    while True:
        try:
            cursor.execute(
                "DELETE FROM klines WHERE rowid IN "
                "(SELECT rowid FROM klines WHERE timeframe = ? LIMIT ?)",
                (tf, batch_size)
            )
            deleted = cursor.rowcount
            conn.commit()

            if deleted == 0:
                print(f"  ✅ {tf}: All rows deleted (total {total_deleted:,})")
                break

            total_deleted += deleted
            consecutive_failures = 0

            # Progressively increase batch size as space frees up
            if total_deleted % 10000 == 0:
                batch_size = min(batch_size * 2, 50000)

            # Log every 50k rows
            if total_deleted % 50000 == 0:
                print(f"  ⏳ {tf}: deleted {total_deleted:,} rows (batch size: {batch_size:,})")

        except sqlite3.OperationalError as e:
            error_str = str(e).lower()
            if "disk is full" in error_str or "database or disk" in error_str:
                consecutive_failures += 1
                if consecutive_failures > 3:
                    print(f"  ❌ {tf}: Disk full after {total_deleted:,} rows. Stopping.")
                    break
                # Reduce batch size and retry
                batch_size = max(batch_size // 4, 10)
                print(f"  ⚠️ {tf}: Disk pressure — reducing batch to {batch_size}, retrying...")
                time.sleep(0.5)
            else:
                print(f"  ❌ {tf}: Unexpected error: {e}")
                break

    return total_deleted


print("\n[Step 4] Deleting 3m data...")
deleted_3m = delete_in_batches("3m")

print("\n[Step 5] Deleting 5m data...")
deleted_5m = delete_in_batches("5m")

# ─────────────────────────────────────────────────────────────
# Step 6: VACUUM untuk reclaim space (opsional, skip kalau masih penuh)
# ─────────────────────────────────────────────────────────────
print("\n[Step 6] VACUUM to reclaim disk space...")
try:
    # Check free space first
    stat = os.statvfs("/app/data")
    free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
    print(f"  Free space before VACUUM: {free_mb:.1f} MB")

    if free_mb < 100:
        print("  ⚠️ Skip VACUUM — need at least 100MB free (VACUUM makes copy of DB)")
        print("     Data already deleted, DB file just not compacted yet.")
    else:
        cursor.execute("VACUUM")
        print("  ✅ VACUUM complete")
except Exception as e:
    print(f"  ⚠️ VACUUM failed: {e}")
    print("     (Data deleted successfully, just DB file not compacted)")

# ─────────────────────────────────────────────────────────────
# Step 7: Final counts + free space
# ─────────────────────────────────────────────────────────────
print("\n[Final] Remaining data counts:")
try:
    for tf in ["1m", "15m", "1h", "4h"]:
        try:
            cursor.execute("SELECT COUNT(*) FROM klines WHERE timeframe = ?", (tf,))
            count = cursor.fetchone()[0]
            print(f"  {tf}: {count:,} rows")
        except Exception as e:
            print(f"  {tf}: query failed ({e})")
except Exception as e:
    print(f"  Final count query failed: {e}")

try:
    stat = os.statvfs("/app/data")
    free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
    print(f"\n[Disk] Free space after cleanup: {free_mb:.1f} MB")
except:
    pass

conn.close()

print("\n" + "=" * 60)
print(f"CLEANUP DONE — Deleted {deleted_3m:,} rows (3m) + {deleted_5m:,} rows (5m)")
print("=" * 60)
