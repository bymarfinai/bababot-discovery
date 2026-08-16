#!/usr/bin/env python3
"""V9-D — rank frozen BTC weekday/hour candidates across 8 adjacent 120d blocks.

Purpose: find the strongest/durable BTC time-of-week directional candidates,
not to tune new hours/directions.

Candidates are frozen from V9-C's two most recent 120d blocks. We now look
back across six additional 120d blocks. Entry/exit remains pure 1H open->close.
All timestamps are classified in WIB (UTC+7).
Research only; no live changes, no TP/SL, no fees/slippage.
"""

import json
import statistics
from datetime import datetime, timedelta, timezone
from research.v7_f_fib_120d_archive_audit import load_series

PAIR = "BTCUSDT"
BLOCK_DAYS = 120
N_BLOCKS = 8
END = datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
START = END - timedelta(days=BLOCK_DAYS * N_BLOCKS)
DATA_START = START - timedelta(days=2)
DATA_END = END + timedelta(days=1)

# Frozen shortlist from V9-C. No new hour/direction search here.
CANDIDATES = [
    {"weekday": "TUE", "hour_wib": 1, "direction": "SELL"},
    {"weekday": "TUE", "hour_wib": 20, "direction": "SELL"},
    {"weekday": "THU", "hour_wib": 9, "direction": "SELL"},
    {"weekday": "THU", "hour_wib": 2, "direction": "BUY"},
    {"weekday": "FRI", "hour_wib": 9, "direction": "SELL"},
    {"weekday": "FRI", "hour_wib": 23, "direction": "BUY"},
    {"weekday": "SUN", "hour_wib": 23, "direction": "SELL"},
    {"weekday": "SUN", "hour_wib": 1, "direction": "BUY"},
    {"weekday": "SUN", "hour_wib": 14, "direction": "BUY"},
]
WEEKDAY_NUM = {"MON":0,"TUE":1,"WED":2,"THU":3,"FRI":4,"SAT":5,"SUN":6}


def wib_dt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc) + timedelta(hours=7)


def block_index(dt_utc):
    if not (START <= dt_utc < END):
        return None
    idx = int((dt_utc - START).total_seconds() // (BLOCK_DAYS * 86400))
    return idx if 0 <= idx < N_BLOCKS else None


def stat(rets, direction):
    signed = [r if direction == "BUY" else -r for r in rets]
    resolved = [x for x in signed if x != 0]
    wins = sum(x > 0 for x in resolved)
    losses = sum(x < 0 for x in resolved)
    return {
        "n": len(signed),
        "resolved": len(resolved),
        "wins": wins,
        "losses": losses,
        "wr_pct": round(100.0 * wins / len(resolved), 2) if resolved else None,
        "mean_signed_ret_pct": round(sum(signed) / len(signed), 5) if signed else None,
    }


def main():
    rows = load_series(PAIR, "1h", DATA_START, DATA_END)
    bars = []
    for x in rows:
        t = int(x[2])
        dt_utc = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        bi = block_index(dt_utc)
        if bi is None:
            continue
        o = float(x[3]); c = float(x[6])
        if o <= 0:
            continue
        ret_pct = 100.0 * (c / o - 1.0)
        wd = wib_dt(t).weekday()
        hr = wib_dt(t).hour
        bars.append((bi, wd, hr, ret_pct))

    ranked = []
    for cand in CANDIDATES:
        wd = WEEKDAY_NUM[cand["weekday"]]
        hr = cand["hour_wib"]
        direction = cand["direction"]
        block_stats = []
        all_rets = []
        for bi in range(N_BLOCKS):
            rs = [r for b,w,h,r in bars if b == bi and w == wd and h == hr]
            all_rets.extend(rs)
            st = stat(rs, direction)
            st["block"] = bi + 1
            st["start"] = (START + timedelta(days=BLOCK_DAYS * bi)).isoformat()
            st["end_exclusive"] = (START + timedelta(days=BLOCK_DAYS * (bi + 1))).isoformat()
            block_stats.append(st)

        wrs = [s["wr_pct"] for s in block_stats if s["wr_pct"] is not None]
        recent2 = block_stats[-2:]
        older6 = block_stats[:-2]
        older_wrs = [s["wr_pct"] for s in older6 if s["wr_pct"] is not None]
        recent_wrs = [s["wr_pct"] for s in recent2 if s["wr_pct"] is not None]
        overall = stat(all_rets, direction)
        item = {
            **cand,
            "blocks_120d": block_stats,
            "overall_8_blocks": overall,
            "median_block_wr_pct": round(statistics.median(wrs), 2),
            "min_block_wr_pct": min(wrs),
            "max_block_wr_pct": max(wrs),
            "blocks_ge60": sum(x >= 60 for x in wrs),
            "blocks_ge70": sum(x >= 70 for x in wrs),
            "older6_median_wr_pct": round(statistics.median(older_wrs), 2),
            "older6_blocks_ge60": sum(x >= 60 for x in older_wrs),
            "recent2_min_wr_pct": min(recent_wrs),
            "recent2_mean_wr_pct": round(sum(recent_wrs)/len(recent_wrs), 2),
        }
        ranked.append(item)

    # Find the best durable candidate: prioritize block consistency first,
    # then long-run median, then recent floor, then overall WR.
    ranked.sort(key=lambda x: (
        x["blocks_ge60"],
        x["median_block_wr_pct"],
        x["recent2_min_wr_pct"],
        x["overall_8_blocks"]["wr_pct"],
    ), reverse=True)

    result = {
        "phase": "V9-D",
        "status": "BTC_FROZEN_SHORTLIST_8X120D_RANKING",
        "definition": {
            "pair": PAIR,
            "tf": "1h",
            "timezone": "WIB UTC+7",
            "entry": "fixed weekday/hour 1h open",
            "exit": "same 1h close",
            "window_start": START.isoformat(),
            "window_end": END.isoformat(),
            "blocks": N_BLOCKS,
            "block_days": BLOCK_DAYS,
            "candidate_selection": "frozen from V9-C recent 2x120d; no new hour/direction search",
            "ranking_priority": "blocks_ge60 > median_block_WR > recent2_min_WR > overall_WR",
            "tp_sl": None,
            "fees_slippage": "not applied",
            "live_changes": False,
        },
        "coverage": {
            "rows": len(rows),
            "first": datetime.fromtimestamp(rows[0][2]/1000, tz=timezone.utc).isoformat() if rows else None,
            "last": datetime.fromtimestamp(rows[-1][2]/1000, tz=timezone.utc).isoformat() if rows else None,
        },
        "ranked_candidates": ranked,
        "winner": ranked[0] if ranked else None,
    }
    print("V9_D_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
