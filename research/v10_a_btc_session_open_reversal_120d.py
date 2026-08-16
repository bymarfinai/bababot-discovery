#!/usr/bin/env python3
"""V10-A — BTC session-open reversal audit, 2x120d.

Hypothesis: the first 15-minute move after a major equity-session open tends to reverse.
Research only; no live changes.

Frozen rule:
- BTCUSDT 5m official Binance USD-M archive via existing loader.
- Sessions: Tokyo 09:00 Asia/Tokyo, London 08:00 Europe/London,
  New York 09:30 America/New_York.
- Weekdays only (Mon-Fri); exchange holidays are not filtered in this first screen.
- Opening impulse = open of first 5m bar to close of third 5m bar (15m).
- If opening impulse UP -> theoretical reversal direction SELL.
- If opening impulse DOWN -> theoretical reversal direction BUY.
- Entry = close of third 5m bar.
- Outcome = close exactly 60 minutes after entry vs entry price.
- Win when 60m signed return is positive in reversal direction.
- Compare previous 120d vs latest 120d. No TP/SL, fees, slippage, or threshold sweep.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from research.v7_f_fib_120d_archive_audit import load_series

PAIR = "BTCUSDT"
PREV_START = datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START = datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END = datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
DATA_START = PREV_START - timedelta(days=2)
DATA_END = LATEST_END + timedelta(days=2)

SESSIONS = {
    "TOKYO": {"tz": "Asia/Tokyo", "hour": 9, "minute": 0},
    "LONDON": {"tz": "Europe/London", "hour": 8, "minute": 0},
    "NEW_YORK": {"tz": "America/New_York", "hour": 9, "minute": 30},
}


def block_for(dt_utc):
    if PREV_START <= dt_utc < LATEST_START:
        return "previous_120d"
    if LATEST_START <= dt_utc < LATEST_END:
        return "latest_120d"
    return None


def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0


def summarize(events):
    resolved = [e for e in events if e["outcome"] != "FLAT"]
    wins = sum(e["outcome"] == "WIN" for e in resolved)
    losses = sum(e["outcome"] == "LOSS" for e in resolved)
    signed = [e["signed_ret_pct"] for e in events]
    return {
        "n": len(events),
        "resolved": len(resolved),
        "wins": wins,
        "losses": losses,
        "flat": len(events) - len(resolved),
        "wr_pct": round(100.0 * wins / len(resolved), 2) if resolved else None,
        "mean_signed_ret_pct": round(sum(signed) / len(signed), 5) if signed else None,
        "median_signed_ret_pct": round(sorted(signed)[len(signed)//2], 5) if signed else None,
    }


def main():
    rows = load_series(PAIR, "5m", DATA_START, DATA_END)
    # Map open timestamp ms -> (open, close)
    bars = {int(x[2]): (float(x[3]), float(x[6])) for x in rows}
    events = []

    # Iterate UTC dates with padding; session local date determines Mon-Fri eligibility.
    d0 = DATA_START.date() - timedelta(days=1)
    d1 = DATA_END.date() + timedelta(days=1)
    d = d0
    while d <= d1:
        for session, cfg in SESSIONS.items():
            tz = ZoneInfo(cfg["tz"])
            # Build session open using this calendar date in session-local timezone.
            local_open = datetime(d.year, d.month, d.day, cfg["hour"], cfg["minute"], tzinfo=tz)
            if local_open.weekday() >= 5:
                continue
            open_utc = local_open.astimezone(timezone.utc)
            b = block_for(open_utc)
            if not b:
                continue
            t0 = int(open_utc.timestamp() * 1000)
            t5 = t0 + 5 * 60 * 1000
            t10 = t0 + 10 * 60 * 1000
            # Entry after 15m = close of bar that opens at t+10m.
            # 60m later close = close of bar opening at t+70m (ends t+75m),
            # i.e. exactly 60m after the t+15 entry timestamp.
            t70 = t0 + 70 * 60 * 1000
            if any(t not in bars for t in (t0, t5, t10, t70)):
                continue
            opening_open = bars[t0][0]
            opening_close = bars[t10][1]
            entry = opening_close
            exit_price = bars[t70][1]
            impulse = pct(opening_open, opening_close)
            if impulse == 0:
                continue
            reversal_direction = "SELL" if impulse > 0 else "BUY"
            raw_ret = pct(entry, exit_price)
            signed = raw_ret if reversal_direction == "BUY" else -raw_ret
            outcome = "WIN" if signed > 0 else ("LOSS" if signed < 0 else "FLAT")
            events.append({
                "session": session,
                "block": b,
                "local_date": local_open.date().isoformat(),
                "open_utc": open_utc.isoformat(),
                "open_wib": (open_utc + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M"),
                "opening_impulse": "UP" if impulse > 0 else "DOWN",
                "opening_impulse_pct": round(impulse, 5),
                "reversal_direction": reversal_direction,
                "signed_ret_pct": round(signed, 5),
                "outcome": outcome,
            })
        d += timedelta(days=1)

    by = defaultdict(list)
    for e in events:
        by[(e["session"], e["block"])].append(e)
        by[(e["session"], e["block"], e["opening_impulse"])].append(e)

    session_results = []
    for session in SESSIONS:
        prev = summarize(by[(session, "previous_120d")])
        latest = summarize(by[(session, "latest_120d")])
        combined = summarize(by[(session, "previous_120d")] + by[(session, "latest_120d")])
        split = {}
        for impulse in ("UP", "DOWN"):
            split[impulse] = {
                "reversal_direction": "SELL" if impulse == "UP" else "BUY",
                "previous_120d": summarize(by[(session, "previous_120d", impulse)]),
                "latest_120d": summarize(by[(session, "latest_120d", impulse)]),
                "combined": summarize(by[(session, "previous_120d", impulse)] + by[(session, "latest_120d", impulse)]),
            }
        session_results.append({
            "session": session,
            "previous_120d": prev,
            "latest_120d": latest,
            "combined": combined,
            "opening_impulse_split": split,
            "stable_ge60": bool(prev["wr_pct"] is not None and latest["wr_pct"] is not None and prev["wr_pct"] >= 60 and latest["wr_pct"] >= 60),
            "stable_ge70": bool(prev["wr_pct"] is not None and latest["wr_pct"] is not None and prev["wr_pct"] >= 70 and latest["wr_pct"] >= 70),
        })

    result = {
        "phase": "V10-A",
        "status": "BTC_SESSION_OPEN_15M_REVERSAL_2X120D",
        "definition": {
            "pair": PAIR,
            "tf": "5m",
            "sessions": SESSIONS,
            "opening_impulse": "first 15m open-to-close",
            "rule": "UP first15m => SELL; DOWN first15m => BUY",
            "entry": "close of first 15m",
            "exit": "close 60m after entry",
            "previous_120d": {"start": PREV_START.isoformat(), "end_exclusive": LATEST_START.isoformat()},
            "latest_120d": {"start": LATEST_START.isoformat(), "end_exclusive": LATEST_END.isoformat()},
            "exchange_holidays_filtered": False,
            "tp_sl": None,
            "fees_slippage": "not applied",
            "threshold_sweep": False,
            "live_changes": False,
        },
        "coverage": {
            "rows": len(rows),
            "first": datetime.fromtimestamp(rows[0][2] / 1000, tz=timezone.utc).isoformat() if rows else None,
            "last": datetime.fromtimestamp(rows[-1][2] / 1000, tz=timezone.utc).isoformat() if rows else None,
            "events": len(events),
        },
        "session_results": session_results,
    }
    print("V10_A_RESULT", json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
