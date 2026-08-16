#!/usr/bin/env python3
"""V10-C — BTC London sweep RR1 + excursion audit.

Research-only follow-up to V10-B. Signal definitions are frozen:
A) London current UTC-day HIGH-so-far sweep + same 5m bar close back below -> SELL.
B) London previous-day LOW sweep + same 5m bar close back above -> BUY.

Entry = trigger 5m close. Natural structural SL = trigger bar sweep extreme.
TP = 1R. Tracking begins on the NEXT 5m bar. Horizon = 60m.
If TP and SL are both touched in the same child 5m bar, outcome is AMBIGUOUS and excluded.
If neither is touched within 60m, outcome is CENSORED and excluded from resolved WR.
Also reports 60m MFE/MAE in % and R units. No parameter sweep, no fees/slippage, no live changes.
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
LONDON_TZ = ZoneInfo("Europe/London")
HORIZON_MIN = 60


def dt_utc(ms):
    return datetime.fromtimestamp(int(ms)/1000, tz=timezone.utc)


def block_name(t):
    if PREV_START <= t < LATEST_START:
        return "previous_120d"
    if LATEST_START <= t < LATEST_END:
        return "latest_120d"
    return None


def london_open_utc(day_utc):
    candidates=[]
    for delta in (-1,0,1):
        local_date=(day_utc+timedelta(days=delta)).astimezone(LONDON_TZ).date()
        local_dt=datetime(local_date.year,local_date.month,local_date.day,8,0,tzinfo=LONDON_TZ)
        u=local_dt.astimezone(timezone.utc)
        if u.date()==day_utc.date():
            candidates.append(u)
    return sorted(candidates)[0] if candidates else None


def pct(a,b):
    return 100.0*(a-b)/b if b else 0.0


def summarize(events):
    resolved=[e for e in events if e["outcome"] in ("WIN","LOSS")]
    wins=sum(e["outcome"]=="WIN" for e in resolved)
    losses=sum(e["outcome"]=="LOSS" for e in resolved)
    amb=sum(e["outcome"]=="AMBIGUOUS" for e in events)
    cens=sum(e["outcome"]=="CENSORED" for e in events)
    def med(key):
        vals=[e[key] for e in events if e.get(key) is not None]
        return round(median(vals),4) if vals else None
    def mean(key):
        vals=[e[key] for e in events if e.get(key) is not None]
        return round(sum(vals)/len(vals),4) if vals else None
    return {
        "n":len(events),"resolved":len(resolved),"wins":wins,"losses":losses,
        "wr_pct":round(100*wins/len(resolved),2) if resolved else None,
        "ambiguous":amb,"censored":cens,
        "median_stop_pct":med("stop_pct"),"mean_stop_pct":mean("stop_pct"),
        "median_mfe_pct":med("mfe_pct"),"median_mae_pct":med("mae_pct"),
        "median_mfe_R":med("mfe_R"),"median_mae_R":med("mae_R"),
        "mean_mfe_R":mean("mfe_R"),"mean_mae_R":mean("mae_R"),
    }


def evaluate(day_rows, trigger_idx, direction, entry, sl):
    risk=abs(entry-sl)
    if risk<=0:
        return None
    tp=entry+risk if direction=="BUY" else entry-risk
    start=trigger_idx+1
    end_t=dt_utc(day_rows[trigger_idx][2])+timedelta(minutes=HORIZON_MIN)
    path=[]
    for r in day_rows[start:]:
        t=dt_utc(r[2])
        if t>=end_t:
            break
        path.append(r)
    if not path:
        return None
    outcome="CENSORED"
    for r in path:
        h=float(r[4]); l=float(r[5])
        if direction=="SELL":
            hit_tp=l<=tp; hit_sl=h>=sl
        else:
            hit_tp=h>=tp; hit_sl=l<=sl
        if hit_tp and hit_sl:
            outcome="AMBIGUOUS"; break
        if hit_tp:
            outcome="WIN"; break
        if hit_sl:
            outcome="LOSS"; break
    highs=[float(r[4]) for r in path]; lows=[float(r[5]) for r in path]
    if direction=="SELL":
        mfe=max(0.0, entry-min(lows)); mae=max(0.0, max(highs)-entry)
    else:
        mfe=max(0.0, max(highs)-entry); mae=max(0.0, entry-min(lows))
    return {
        "outcome":outcome,
        "stop_pct":100*risk/entry,
        "mfe_pct":100*mfe/entry,
        "mae_pct":100*mae/entry,
        "mfe_R":mfe/risk,
        "mae_R":mae/risk,
    }


def main():
    rows=load_series(PAIR,"5m",DATA_START,DATA_END)
    by_day=defaultdict(list)
    for r in rows:
        by_day[dt_utc(r[2]).date()].append(r)
    for d in by_day:
        by_day[d].sort(key=lambda r:int(r[2]))
    days=sorted(by_day)
    idxmap={d:i for i,d in enumerate(days)}

    events={
        "HOD_SOFAR_SELL":{"previous_120d":[],"latest_120d":[]},
        "PDL_BUY":{"previous_120d":[],"latest_120d":[]},
    }

    for d in days:
        day_rows=by_day[d]
        if len(day_rows)<200: continue
        day_start=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)
        open_t=london_open_utc(day_start)
        if open_t is None: continue
        b=block_name(open_t)
        if not b: continue
        window_end=open_t+timedelta(hours=2)
        open_idxs=[i for i,r in enumerate(day_rows) if open_t<=dt_utc(r[2])<window_end]
        if not open_idxs: continue

        pre=[r for r in day_rows if dt_utc(r[2])<open_t]
        if pre:
            hsf=max(float(r[4]) for r in pre)
            for i in open_idxs:
                r=day_rows[i]; h=float(r[4]); c=float(r[6])
                if h>hsf and c<hsf:
                    e=evaluate(day_rows,i,"SELL",c,h)
                    if e:
                        e.update({"date":str(d),"entry_time":dt_utc(r[2]).isoformat(),"direction":"SELL","level_type":"HOD_SOFAR"})
                        events["HOD_SOFAR_SELL"][b].append(e)
                    break

        j=idxmap[d]
        if j>0 and (d-days[j-1]).days==1:
            prev=by_day[days[j-1]]
            pdl=min(float(r[5]) for r in prev)
            for i in open_idxs:
                r=day_rows[i]; l=float(r[5]); c=float(r[6])
                if l<pdl and c>pdl:
                    e=evaluate(day_rows,i,"BUY",c,l)
                    if e:
                        e.update({"date":str(d),"entry_time":dt_utc(r[2]).isoformat(),"direction":"BUY","level_type":"PDL"})
                        events["PDL_BUY"][b].append(e)
                    break

    result={
        "phase":"V10-C","status":"BTC_LONDON_SWEEP_RR1_EXCURSION",
        "definition":{
            "pair":PAIR,"tf":"5m","session":"London 08:00 local (DST aware)",
            "post_open_signal_window":"2h","horizon_after_entry":"60m",
            "setup_A":"current UTC-day high-so-far sweep + same 5m close back below => SELL",
            "setup_B":"previous-day low sweep + same 5m close back above => BUY",
            "entry":"trigger 5m close","sl":"trigger bar sweep extreme","tp":"1R",
            "tracking":"next 5m bar onward","same_child_tp_sl":"AMBIGUOUS excluded",
            "unresolved_60m":"CENSORED excluded","fees_slippage":"not applied","live_changes":False,
        },
        "results":{}
    }
    for name,blocks in events.items():
        p=blocks["previous_120d"]; v=blocks["latest_120d"]
        result["results"][name]={
            "previous_120d":summarize(p),
            "latest_120d":summarize(v),
            "combined":summarize(p+v),
        }
    print("V10_C_RESULT",json.dumps(result,separators=(",",":")))

if __name__=="__main__":
    main()
