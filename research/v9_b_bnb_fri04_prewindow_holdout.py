#!/usr/bin/env python3
"""V9-B — independent pre-window holdout for frozen V9-A time slot.

Frozen candidate selected by V9-A:
  BNBUSDT, Friday 04:00 WIB, BUY, 1H open -> 1H close direction.

This script tests the exact slot on the 971 days immediately BEFORE the
V9-A 2023-12-18..2026-08-15 window. No slot/day/hour/direction changes.
Research only; no live changes; no TP/SL or fee tuning.
"""

import json
from datetime import datetime, timedelta, timezone

from research.v7_f_fib_120d_archive_audit import load_series

PAIR = "BNBUSDT"
DAYS = 971
BLOCK_DAYS = 120
WINDOW_END = datetime.fromisoformat("2023-12-18T15:11:15.831175+00:00")
WINDOW_START = WINDOW_END - timedelta(days=DAYS)
WIB = timezone(timedelta(hours=7))
TARGET_WEEKDAY = 4  # Friday, Monday=0
TARGET_HOUR = 4
DIRECTION = "BUY"


def stat(rows):
    vals = [r["ret"] for r in rows if r["ret"] != 0]
    n = len(vals)
    w = sum(x > 0 for x in vals)
    s = sorted(vals)
    return {
        "n": n,
        "wins": w,
        "losses": n - w,
        "wr_pct": round(100.0*w/n, 2) if n else None,
        "mean_signed_ret_pct": round(100.0*sum(vals)/n, 5) if n else None,
        "median_signed_ret_pct": round(100.0*s[len(s)//2], 5) if n else None,
    }


def main():
    raw = load_series(PAIR, "1h", WINDOW_START, WINDOW_END)
    rows = []
    for r in raw:
        t = datetime.fromtimestamp(int(r[2])/1000, tz=timezone.utc)
        if not (WINDOW_START <= t < WINDOW_END):
            continue
        local = t.astimezone(WIB)
        if local.weekday() != TARGET_WEEKDAY or local.hour != TARGET_HOUR:
            continue
        o = float(r[3]); c = float(r[6])
        if o <= 0:
            continue
        delta = (t - WINDOW_START).total_seconds()
        block = int(delta // (BLOCK_DAYS*86400)) + 1
        rows.append({"t": t, "block": block, "ret": c/o - 1.0})

    full = [r for r in rows if 1 <= r["block"] <= 8]
    rem = [r for r in rows if r["block"] == 9]
    blocks = []
    for b in range(1, 9):
        blocks.append({"block": b, **stat([r for r in full if r["block"] == b])})
    first = [r for r in full if r["block"] <= 4]
    second = [r for r in full if r["block"] >= 5]
    overall = stat(full)
    first_s = stat(first); second_s = stat(second)
    checks = {
        "overall_n_ge120_wr_ge60": overall["n"] >= 120 and (overall["wr_pct"] or 0) >= 60.0,
        "mean_return_positive": (overall["mean_signed_ret_pct"] or 0) > 0,
        "both_halves_wr_ge55": (first_s["wr_pct"] or 0) >= 55.0 and (second_s["wr_pct"] or 0) >= 55.0,
        "at_least_6_of_8_blocks_wr_ge50": sum(1 for x in blocks if (x["wr_pct"] or 0) >= 50.0) >= 6,
    }
    result = {
        "phase": "V9-B",
        "status": "INDEPENDENT_PREWINDOW_TIME_SLOT_HOLDOUT",
        "definition": {
            "pair": PAIR, "weekday": "FRI", "hour_wib": TARGET_HOUR,
            "direction": DIRECTION, "tf": "1h",
            "entry": "1h open", "exit": "1h close",
            "window_start": WINDOW_START.isoformat(), "window_end": WINDOW_END.isoformat(),
            "selection": "none; exact frozen V9-A candidate",
            "tp_sl": None, "fees_slippage": "not applied", "live_changes": False,
        },
        "coverage": {
            "rows": len(raw),
            "first": datetime.fromtimestamp(raw[0][2]/1000, tz=timezone.utc).isoformat() if raw else None,
            "last": datetime.fromtimestamp(raw[-1][2]/1000, tz=timezone.utc).isoformat() if raw else None,
        },
        "full_8_blocks": overall,
        "chronological_halves": {"blocks_1_4": first_s, "blocks_5_8": second_s},
        "blocks_120d": blocks,
        "remainder_11d": stat(rem),
        "replication_gate": {"checks": checks, "passed": all(checks.values())},
        "verdict": "PASS_PREWINDOW_REPLICATION" if all(checks.values()) else "FAIL_PREWINDOW_REPLICATION",
    }
    print("V9_B_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
