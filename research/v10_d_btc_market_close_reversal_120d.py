#!/usr/bin/env python3
"""V10-D — BTC major-market close reversal audit.

Research only. Tests BTC around official Tokyo/London/New York cash-market closes.
Two causal screens over the same 2x120d windows:
1) CLOSE_IMPULSE_REVERSAL: last 15m before official close; trade opposite direction from
   the market-close price for the next 60m.
2) POST_CLOSE_DAY_EXTREME_SWEEP: freeze current UTC-day high/low-so-far at official close;
   during first 2h after close, require a 5m sweep through the known level and same-bar
   close back inside. Enter reversal at reclaim close; evaluate signed return 60m later.

No TP/SL, no threshold sweep, no fees/slippage, no live changes.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

from research.v7_f_fib_120d_archive_audit import load_series

PAIR="BTCUSDT"
PREV_START=datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START=datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END=datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
DATA_START=(PREV_START-timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
DATA_END=(LATEST_END+timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)

CLOSES={
    "TOKYO":("Asia/Tokyo",15,30),
    "LONDON":("Europe/London",16,30),
    "NEW_YORK":("America/New_York",16,0),
}


def dt_utc(ms): return datetime.fromtimestamp(int(ms)/1000,tz=timezone.utc)

def block_name(t):
    if PREV_START<=t<LATEST_START: return "previous_120d"
    if LATEST_START<=t<LATEST_END: return "latest_120d"
    return None

def market_close_utc(day_utc,session):
    tz_name,hh,mm=CLOSES[session]; tz=ZoneInfo(tz_name)
    c=[]
    for delta in (-1,0,1):
        local_date=(day_utc+timedelta(days=delta)).astimezone(tz).date()
        u=datetime(local_date.year,local_date.month,local_date.day,hh,mm,tzinfo=tz).astimezone(timezone.utc)
        if u.date()==day_utc.date(): c.append(u)
    return sorted(c)[0] if c else None

def close_at_or_after(rows,target):
    for r in rows:
        if dt_utc(r[2])>=target: return float(r[6])
    return None

def stats(xs):
    w=sum(x>0 for x in xs); l=sum(x<0 for x in xs); f=len(xs)-w-l; res=w+l
    return {"n":len(xs),"resolved":res,"wins":w,"losses":l,"flat":f,
            "wr_pct":round(100*w/res,2) if res else None,
            "mean_signed_ret_pct":round(sum(xs)/len(xs),5) if xs else None,
            "median_signed_ret_pct":round(median(xs),5) if xs else None}

def signed(entry,exit_px,direction):
    raw=100*(exit_px-entry)/entry
    return raw if direction=="BUY" else -raw


def main():
    rows=load_series(PAIR,"5m",DATA_START,DATA_END)
    by_day=defaultdict(list)
    for r in rows: by_day[dt_utc(r[2]).date()].append(r)
    for d in by_day: by_day[d].sort(key=lambda r:int(r[2]))

    out={s:{"CLOSE_IMPULSE":{"previous_120d":[],"latest_120d":[]},
            "POST_CLOSE_EXTREME":{"previous_120d":[],"latest_120d":[],"events":[]}}
         for s in CLOSES}

    for d,day_rows in sorted(by_day.items()):
        if len(day_rows)<200: continue
        day_start=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)
        for session in CLOSES:
            ct=market_close_utc(day_start,session)
            if ct is None: continue
            b=block_name(ct)
            if not b: continue

            # 1) last 15m impulse before official close -> opposite next 60m.
            pre15=[r for r in day_rows if ct-timedelta(minutes=15)<=dt_utc(r[2])<ct]
            if len(pre15)>=3:
                op=float(pre15[0][3]); last_close=float(pre15[-1][6])
                if last_close!=op:
                    direction="SELL" if last_close>op else "BUY"
                    exit_px=close_at_or_after(day_rows,ct+timedelta(minutes=60))
                    if exit_px is not None:
                        out[session]["CLOSE_IMPULSE"][b].append(signed(last_close,exit_px,direction))

            # 2) freeze UTC-day H/L-so-far at close, then post-close sweep+reclaim within 2h.
            pre=[r for r in day_rows if dt_utc(r[2])<ct]
            if not pre: continue
            hsf=max(float(r[4]) for r in pre); lsf=min(float(r[5]) for r in pre)
            post=[r for r in day_rows if ct<=dt_utc(r[2])<ct+timedelta(hours=2)]
            candidates=[]
            for r in post:
                t=dt_utc(r[2]); h=float(r[4]); l=float(r[5]); c=float(r[6])
                if h>hsf and c<hsf: candidates.append((t,"HIGH","SELL",c))
                if l<lsf and c>lsf: candidates.append((t,"LOW","BUY",c))
            if candidates:
                t,side,direction,entry=sorted(candidates,key=lambda x:x[0])[0]
                exit_px=close_at_or_after(day_rows,t+timedelta(minutes=60))
                if exit_px is not None:
                    ret=signed(entry,exit_px,direction)
                    out[session]["POST_CLOSE_EXTREME"][b].append(ret)
                    out[session]["POST_CLOSE_EXTREME"]["events"].append({"block":b,"side":side,"ret60":ret})

    results=[]
    for s in CLOSES:
        ci=out[s]["CLOSE_IMPULSE"]
        pc=out[s]["POST_CLOSE_EXTREME"]
        events=pc["events"]
        by_side={}
        for side in ("HIGH","LOW"):
            p=[e["ret60"] for e in events if e["block"]=="previous_120d" and e["side"]==side]
            v=[e["ret60"] for e in events if e["block"]=="latest_120d" and e["side"]==side]
            by_side[side]={"previous_120d":stats(p),"latest_120d":stats(v),"combined":stats(p+v)}
        results.append({
            "session":s,
            "close_impulse_reversal":{"previous_120d":stats(ci["previous_120d"]),"latest_120d":stats(ci["latest_120d"]),"combined":stats(ci["previous_120d"]+ci["latest_120d"])},
            "post_close_day_extreme_sweep_reversal":{"previous_120d":stats(pc["previous_120d"]),"latest_120d":stats(pc["latest_120d"]),"combined":stats(pc["previous_120d"]+pc["latest_120d"]),"by_swept_side":by_side}
        })

    result={"phase":"V10-D","status":"BTC_MARKET_CLOSE_REVERSAL_2X120D","definition":{
        "pair":PAIR,"tf":"5m","official_closes":{k:{"tz":v[0],"hour":v[1],"minute":v[2]} for k,v in CLOSES.items()},
        "close_impulse":"last15m before close => trade opposite for next60m",
        "post_close_extreme":"freeze current UTC-day high/low-so-far at close; first2h post-close sweep+same-bar reclaim => reversal; exit60m later",
        "tp_sl":None,"fees_slippage":"not applied","threshold_sweep":False,"live_changes":False},
        "results":results}
    print("V10_D_RESULT",json.dumps(result,separators=(",",":")))

if __name__=="__main__": main()
