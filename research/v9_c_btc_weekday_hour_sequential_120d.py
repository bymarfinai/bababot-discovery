#!/usr/bin/env python3
"""V9-C — BTC sequential weekday/hour seasonality audit.

Research only. Processes BTC one weekday at a time (MON -> SUN).
For each weekday, scan all 24 WIB hours.
Previous 120d chooses BUY/SELL direction independently for each hour.
That direction is frozen and evaluated in the latest 120d.
No TP/SL; pure 1H open-to-close directional screen.
No threshold tuning and no live changes.
"""

import json
from datetime import datetime, timedelta, timezone
from research.v7_f_fib_120d_archive_audit import load_series

PAIR = "BTCUSDT"
PREV_START = datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START = datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END = datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
DATA_START = PREV_START - timedelta(days=2)
DATA_END = LATEST_END + timedelta(days=1)
WEEKDAYS = ["MON","TUE","WED","THU","FRI","SAT","SUN"]


def wib_dt(ms):
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc) + timedelta(hours=7)


def block(dt_utc):
    if PREV_START <= dt_utc < LATEST_START:
        return "previous_120d"
    if LATEST_START <= dt_utc < LATEST_END:
        return "latest_120d"
    return None


def stats(rets, direction):
    signed = [r if direction == "BUY" else -r for r in rets]
    wins = sum(x > 0 for x in signed)
    losses = sum(x < 0 for x in signed)
    flat = len(signed) - wins - losses
    resolved = wins + losses
    return {
        "n": len(signed), "resolved": resolved, "wins": wins, "losses": losses, "flat": flat,
        "wr_pct": round(100*wins/resolved, 2) if resolved else None,
        "mean_signed_ret_pct": round(sum(signed)/len(signed), 5) if signed else None,
    }


def main():
    rows = load_series(PAIR, "1h", DATA_START, DATA_END)
    cells = {wd:{h:{"previous_120d":[],"latest_120d":[]} for h in range(24)} for wd in WEEKDAYS}
    for x in rows:
        t = int(x[2]); o = float(x[3]); c = float(x[6])
        dt_utc = datetime.fromtimestamp(t/1000, tz=timezone.utc)
        b = block(dt_utc)
        if not b or o <= 0: continue
        local = wib_dt(t)
        wd = WEEKDAYS[local.weekday()]
        h = local.hour
        ret = 100.0*(c-o)/o
        cells[wd][h][b].append(ret)

    weekday_results = []
    for wd in WEEKDAYS:
        hours=[]
        for h in range(24):
            prev = cells[wd][h]["previous_120d"]
            latest = cells[wd][h]["latest_120d"]
            buy_prev = stats(prev, "BUY")
            sell_prev = stats(prev, "SELL")
            # Freeze direction using previous 120d only. Tie -> mean signed return; final tie -> BUY.
            if (sell_prev["wr_pct"] or 0) > (buy_prev["wr_pct"] or 0):
                direction="SELL"
            elif (sell_prev["wr_pct"] or 0) < (buy_prev["wr_pct"] or 0):
                direction="BUY"
            else:
                direction = "SELL" if (sell_prev["mean_signed_ret_pct"] or 0) > (buy_prev["mean_signed_ret_pct"] or 0) else "BUY"
            p = stats(prev,direction)
            v = stats(latest,direction)
            comb = stats(prev+latest,direction)
            min_wr = min(p["wr_pct"],v["wr_pct"]) if p["wr_pct"] is not None and v["wr_pct"] is not None else None
            hours.append({"hour_wib":h,"direction":direction,"previous_120d":p,"latest_120d":v,"combined":comb,"min_wr_pct":min_wr,"wr_change_pp":round(v["wr_pct"]-p["wr_pct"],2) if p["wr_pct"] is not None and v["wr_pct"] is not None else None})
        ranked=sorted(hours,key=lambda r:((r["min_wr_pct"] if r["min_wr_pct"] is not None else -1),(r["combined"]["wr_pct"] if r["combined"]["wr_pct"] is not None else -1)),reverse=True)
        stable70=[r for r in ranked if r["previous_120d"]["resolved"]>=15 and r["latest_120d"]["resolved"]>=15 and r["previous_120d"]["wr_pct"]>=70 and r["latest_120d"]["wr_pct"]>=70]
        stable60=[r for r in ranked if r["previous_120d"]["resolved"]>=15 and r["latest_120d"]["resolved"]>=15 and r["previous_120d"]["wr_pct"]>=60 and r["latest_120d"]["wr_pct"]>=60]
        weekday_results.append({"weekday":wd,"all_24_hours":hours,"top5":ranked[:5],"stable_ge70":stable70,"stable_ge60":stable60,"best":ranked[0]})

    result={
        "phase":"V9-C","status":"BTC_SEQUENTIAL_WEEKDAY_HOUR_120D",
        "definition":{
            "pair":PAIR,"timezone":"WIB UTC+7","tf":"1h","entry":"1h open","exit":"same 1h close",
            "previous_120d":{"start":PREV_START.isoformat(),"end_exclusive":LATEST_START.isoformat()},
            "latest_120d":{"start":LATEST_START.isoformat(),"end_exclusive":LATEST_END.isoformat()},
            "selection":"for each weekday/hour previous 120d chooses BUY/SELL; latest 120d is frozen-direction validation",
            "weekday_order":WEEKDAYS,"tp_sl":None,"fees_slippage":"not applied","live_changes":False
        },
        "coverage":{"rows":len(rows),"first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,"last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None},
        "weekday_results":weekday_results
    }
    print("V9_C_RESULT",json.dumps(result,separators=(",",":")))

if __name__ == "__main__": main()
