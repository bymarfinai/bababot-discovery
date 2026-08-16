#!/usr/bin/env python3
"""V10-B — BTC session-open daily-extreme reversal audit.

Research only. Tests the clarified hypothesis:
At major market opens BTC may push into a daily extreme/known daily level and then reverse.

Two layers:
1) Diagnostic (hindsight, explicitly non-executable): does the eventual UTC-day high/low occur
   within 2h after Tokyo/London/New York open, and does price reverse over the next 60m?
2) Causal/executable screen using only known levels at the time:
   A. Previous-day high/low (PDH/PDL), all sessions.
   B. Current UTC-day high/low-so-far before session open, London/New York only.
   A setup requires a sweep through the known level and a 5m close back inside that level
   within the next 2h. Entry is at the reclaim 5m close; outcome is close 60m later.

No TP/SL, no fee/slippage, no threshold sweep, no live changes.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

from research.v7_f_fib_120d_archive_audit import load_series

PAIR = "BTCUSDT"
PREV_START = datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START = datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END = datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
DATA_START = (PREV_START - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
DATA_END = (LATEST_END + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)

SESSIONS = {
    "TOKYO": ("Asia/Tokyo", 9, 0),
    "LONDON": ("Europe/London", 8, 0),
    "NEW_YORK": ("America/New_York", 9, 30),
}


def dt_utc(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)


def block_name(t):
    if PREV_START <= t < LATEST_START:
        return "previous_120d"
    if LATEST_START <= t < LATEST_END:
        return "latest_120d"
    return None


def session_open_utc(day_utc, session):
    tz_name, hh, mm = SESSIONS[session]
    tz = ZoneInfo(tz_name)
    # Use the exchange-local calendar date corresponding to the UTC day around the event.
    # For these sessions, generating candidates from day-1/day/day+1 and selecting the one
    # whose UTC date equals day_utc.date() is robust across DST.
    candidates = []
    for delta in (-1, 0, 1):
        local_date = (day_utc + timedelta(days=delta)).astimezone(tz).date()
        local_dt = datetime(local_date.year, local_date.month, local_date.day, hh, mm, tzinfo=tz)
        u = local_dt.astimezone(timezone.utc)
        if u.date() == day_utc.date():
            candidates.append(u)
    if not candidates:
        return None
    return sorted(candidates)[0]


def stats(outcomes):
    # outcome entries are signed returns in reversal direction; >0 win.
    wins = sum(x > 0 for x in outcomes)
    losses = sum(x < 0 for x in outcomes)
    flat = len(outcomes) - wins - losses
    resolved = wins + losses
    return {
        "n": len(outcomes),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "wr_pct": round(100 * wins / resolved, 2) if resolved else None,
        "mean_signed_ret_pct": round(sum(outcomes) / len(outcomes), 5) if outcomes else None,
        "median_signed_ret_pct": round(median(outcomes), 5) if outcomes else None,
    }


def row_price(row, idx):
    return float(row[idx])


def close_at_or_after(rows, target):
    for r in rows:
        if dt_utc(r[2]) >= target:
            return float(r[6]), dt_utc(r[2])
    return None, None


def find_reclaim(rows_window, level, side):
    """Return (entry_close, entry_time) on first causal sweep+reclaim.

    side HIGH: bar high > level and close < level -> reversal SELL.
    side LOW:  bar low < level and close > level -> reversal BUY.
    Strict crossing avoids counting mere equality.
    """
    for r in rows_window:
        high = float(r[4]); low = float(r[5]); close = float(r[6])
        if side == "HIGH" and high > level and close < level:
            return close, dt_utc(r[2])
        if side == "LOW" and low < level and close > level:
            return close, dt_utc(r[2])
    return None, None


def signed_ret(entry, exit_px, direction):
    raw = 100.0 * (exit_px - entry) / entry
    return raw if direction == "BUY" else -raw


def main():
    rows = load_series(PAIR, "5m", DATA_START, DATA_END)
    by_day = defaultdict(list)
    for r in rows:
        by_day[dt_utc(r[2]).date()].append(r)
    for d in by_day:
        by_day[d].sort(key=lambda r: int(r[2]))

    diagnostic = {s: {"previous_120d": [], "latest_120d": []} for s in SESSIONS}
    diagnostic_meta = {s: {"previous_120d": [], "latest_120d": []} for s in SESSIONS}
    causal = {}
    for s in SESSIONS:
        causal[s] = {
            "PDH_PDL": {"previous_120d": [], "latest_120d": [], "events": []},
            "DAY_SO_FAR": {"previous_120d": [], "latest_120d": [], "events": []},
        }

    sorted_days = sorted(by_day)
    day_index = {d: i for i, d in enumerate(sorted_days)}

    for d in sorted_days:
        day_rows = by_day[d]
        if len(day_rows) < 200:
            continue
        day_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        day_high = max(float(r[4]) for r in day_rows)
        day_low = min(float(r[5]) for r in day_rows)
        day_high_times = [dt_utc(r[2]) for r in day_rows if float(r[4]) == day_high]
        day_low_times = [dt_utc(r[2]) for r in day_rows if float(r[5]) == day_low]

        prev_rows = None
        idx = day_index[d]
        if idx > 0:
            pd = sorted_days[idx - 1]
            if (d - pd).days == 1:
                prev_rows = by_day[pd]
        pdh = max(float(r[4]) for r in prev_rows) if prev_rows else None
        pdl = min(float(r[5]) for r in prev_rows) if prev_rows else None

        for session in SESSIONS:
            open_t = session_open_utc(day_start, session)
            if open_t is None:
                continue
            b = block_name(open_t)
            if not b:
                continue
            window_end = open_t + timedelta(hours=2)
            opening_window = [r for r in day_rows if open_t <= dt_utc(r[2]) < window_end]
            if not opening_window:
                continue

            # Layer 1: eventual daily extreme formed during 2h post-open window.
            high_in = any(open_t <= t < window_end for t in day_high_times)
            low_in = any(open_t <= t < window_end for t in day_low_times)
            diag_events = []
            if high_in:
                extreme_t = min(t for t in day_high_times if open_t <= t < window_end)
                exit_px, exit_t = close_at_or_after(day_rows, extreme_t + timedelta(minutes=60))
                if exit_px is not None:
                    ret = signed_ret(day_high, exit_px, "SELL")
                    diagnostic[session][b].append(ret)
                    diag_events.append({"type":"DAILY_HIGH","ret60":ret})
            if low_in:
                extreme_t = min(t for t in day_low_times if open_t <= t < window_end)
                exit_px, exit_t = close_at_or_after(day_rows, extreme_t + timedelta(minutes=60))
                if exit_px is not None:
                    ret = signed_ret(day_low, exit_px, "BUY")
                    diagnostic[session][b].append(ret)
                    diag_events.append({"type":"DAILY_LOW","ret60":ret})
            diagnostic_meta[session][b].append({
                "date": str(d), "high_in_2h": high_in, "low_in_2h": low_in,
                "events": diag_events,
            })

            # Layer 2A: PDH/PDL sweep+reclaim.
            if pdh is not None and pdl is not None:
                high_entry, high_t = find_reclaim(opening_window, pdh, "HIGH")
                low_entry, low_t = find_reclaim(opening_window, pdl, "LOW")
                candidates = []
                if high_entry is not None:
                    candidates.append((high_t, "HIGH", high_entry, "SELL", pdh))
                if low_entry is not None:
                    candidates.append((low_t, "LOW", low_entry, "BUY", pdl))
                if candidates:
                    # One trade per session/day: earliest causal reclaim.
                    event_t, side, entry, direction, level = sorted(candidates, key=lambda x: x[0])[0]
                    exit_px, _ = close_at_or_after(day_rows, event_t + timedelta(minutes=60))
                    if exit_px is not None:
                        r = signed_ret(entry, exit_px, direction)
                        causal[session]["PDH_PDL"][b].append(r)
                        causal[session]["PDH_PDL"]["events"].append({
                            "date":str(d),"block":b,"side":side,"direction":direction,"ret60":r
                        })

            # Layer 2B: current UTC-day high/low known immediately before session open.
            # Not meaningful for Tokyo because Tokyo open is 00:00 UTC.
            if session != "TOKYO":
                pre = [r for r in day_rows if dt_utc(r[2]) < open_t]
                if pre:
                    hsf = max(float(r[4]) for r in pre)
                    lsf = min(float(r[5]) for r in pre)
                    high_entry, high_t = find_reclaim(opening_window, hsf, "HIGH")
                    low_entry, low_t = find_reclaim(opening_window, lsf, "LOW")
                    candidates = []
                    if high_entry is not None:
                        candidates.append((high_t, "HIGH", high_entry, "SELL", hsf))
                    if low_entry is not None:
                        candidates.append((low_t, "LOW", low_entry, "BUY", lsf))
                    if candidates:
                        event_t, side, entry, direction, level = sorted(candidates, key=lambda x: x[0])[0]
                        exit_px, _ = close_at_or_after(day_rows, event_t + timedelta(minutes=60))
                        if exit_px is not None:
                            r = signed_ret(entry, exit_px, direction)
                            causal[session]["DAY_SO_FAR"][b].append(r)
                            causal[session]["DAY_SO_FAR"]["events"].append({
                                "date":str(d),"block":b,"side":side,"direction":direction,"ret60":r
                            })

    session_results = []
    for s in SESSIONS:
        diag_summary = {}
        for b in ("previous_120d", "latest_120d"):
            meta = diagnostic_meta[s][b]
            days = len(meta)
            any_extreme = sum(1 for x in meta if x["high_in_2h"] or x["low_in_2h"])
            high_days = sum(1 for x in meta if x["high_in_2h"])
            low_days = sum(1 for x in meta if x["low_in_2h"])
            diag_summary[b] = {
                "session_days": days,
                "days_any_eventual_daily_extreme_in_first2h": any_extreme,
                "pct_days_any_extreme": round(100*any_extreme/days,2) if days else None,
                "days_daily_high_in_first2h": high_days,
                "days_daily_low_in_first2h": low_days,
                "reversal_60m_from_extreme": stats(diagnostic[s][b]),
            }
        diag_comb = diagnostic[s]["previous_120d"] + diagnostic[s]["latest_120d"]

        causal_summary = {}
        for level_type in ("PDH_PDL", "DAY_SO_FAR"):
            if s == "TOKYO" and level_type == "DAY_SO_FAR":
                causal_summary[level_type] = None
                continue
            p = causal[s][level_type]["previous_120d"]
            v = causal[s][level_type]["latest_120d"]
            combined = p + v
            events = causal[s][level_type]["events"]
            by_side = {}
            for side in ("HIGH", "LOW"):
                side_rets = [e["ret60"] for e in events if e["side"] == side]
                side_p = [e["ret60"] for e in events if e["side"] == side and e["block"] == "previous_120d"]
                side_v = [e["ret60"] for e in events if e["side"] == side and e["block"] == "latest_120d"]
                by_side[side] = {"previous_120d":stats(side_p),"latest_120d":stats(side_v),"combined":stats(side_rets)}
            causal_summary[level_type] = {
                "previous_120d": stats(p),
                "latest_120d": stats(v),
                "combined": stats(combined),
                "by_swept_side": by_side,
            }

        session_results.append({
            "session": s,
            "diagnostic_eventual_daily_extreme": {
                **diag_summary,
                "combined_reversal_60m_from_extreme": stats(diag_comb),
            },
            "causal_known_level_reversal": causal_summary,
        })

    result = {
        "phase":"V10-B",
        "status":"BTC_SESSION_DAILY_EXTREME_REVERSAL_2X120D",
        "definition":{
            "pair":PAIR,"tf":"5m","daily_definition":"Binance UTC day 00:00-24:00 UTC",
            "sessions":{k:{"tz":v[0],"hour":v[1],"minute":v[2]} for k,v in SESSIONS.items()},
            "post_open_window":"2h","reversal_horizon":"60m after extreme/reclaim",
            "diagnostic":"eventual daily high/low occurs within first2h after session open; hindsight only",
            "causal_PDH_PDL":"sweep previous-day high/low then 5m close back inside",
            "causal_DAY_SO_FAR":"London/NY only: sweep current UTC-day high/low-so-far then 5m close back inside",
            "one_trade_per_session_day":"earliest reclaim if both sides trigger",
            "previous_120d":{"start":PREV_START.isoformat(),"end_exclusive":LATEST_START.isoformat()},
            "latest_120d":{"start":LATEST_START.isoformat(),"end_exclusive":LATEST_END.isoformat()},
            "tp_sl":None,"fees_slippage":"not applied","threshold_sweep":False,"live_changes":False,
        },
        "coverage":{"rows":len(rows),"first":dt_utc(rows[0][2]).isoformat() if rows else None,"last":dt_utc(rows[-1][2]).isoformat() if rows else None},
        "session_results":session_results,
    }
    print("V10_B_RESULT", json.dumps(result,separators=(",",":")))

if __name__ == "__main__":
    main()
