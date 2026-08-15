#!/usr/bin/env python3
"""V5-C — derivatives-native leveraged buildup -> unwind/flush test.

Research-only. The event originates from price x OI dynamics, not from any
support/resistance or V4 signal.

Frozen event definition before reading results:
1) Buildup phase: the 12 completed 5m bars immediately preceding the flush
   window (60m) have non-zero net price direction and net OI increase > 0.
2) Flush phase: the next 3 completed 5m bars (15m) have net price movement
   opposite the buildup direction and net OI decrease < 0.
3) Trigger only on the first causal transition into that same-direction event
   state; overlapping repeats while the condition remains true are suppressed.
4) Enter after the third flush bar closes, in the flush direction.
5) Stop at the 15m flush extreme; target = 1R; tracking begins on the next 5m
   bar. Same-bar TP+SL ambiguity is excluded. Horizon = 72h.

No magnitude threshold, no lookback sweep, no S/R, EMA, Fibonacci, funding,
long/short, or taker filter, and no live integration.
"""
import bisect
import csv
import io
import json
import math
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone

import v5_a2_derivatives_forensic as base

PAIRS = base.PAIRS
DAYS = 120
BUILD_BARS = 12
FLUSH_BARS = 3
HORIZON_BARS = 72 * 12
RR = 1.0
KLINE_MONTHLY = "https://data.binance.vision/data/futures/um/monthly/klines"
KLINE_DAILY = "https://data.binance.vision/data/futures/um/daily/klines"
METRICS_MONTHLY = "https://data.binance.vision/data/futures/um/monthly/metrics"
METRICS_DAILY = "https://data.binance.vision/data/futures/um/daily/metrics"


def stat(rows):
    resolved = [r for r in rows if r.get("outcome") in ("WIN", "LOSS")]
    n = len(resolved)
    w = sum(r["outcome"] == "WIN" for r in resolved)
    return {
        "events": len(rows),
        "resolved": n,
        "wins": w,
        "losses": n-w,
        "wr_pct": round(100.0*w/n, 2) if n else None,
        "ambiguous": sum(r.get("outcome") == "AMBIGUOUS" for r in rows),
        "censored": sum(r.get("outcome") == "CENSORED" for r in rows),
    }


def _dt_ms(v):
    return datetime.fromtimestamp(int(float(v))/1000.0, tz=timezone.utc)


def _months(start, end):
    y, m = start.year, start.month
    out=[]
    while (y,m) <= (end.year,end.month):
        out.append((y,m))
        if m == 12:
            y += 1; m = 1
        else:
            m += 1
    return out


def _month_bounds(y,m):
    lo = datetime(y,m,1,tzinfo=timezone.utc)
    if m == 12:
        hi = datetime(y+1,1,1,tzinfo=timezone.utc)
    else:
        hi = datetime(y,m+1,1,tzinfo=timezone.utc)
    return lo,hi


def _parse_kline_zip(raw):
    z=zipfile.ZipFile(io.BytesIO(raw))
    txt=z.read(z.namelist()[0]).decode("utf-8-sig")
    out=[]
    for r in csv.reader(io.StringIO(txt)):
        if not r: continue
        try:
            t=_dt_ms(r[0]); o=float(r[1]); h=float(r[2]); l=float(r[3]); c=float(r[4])
        except Exception:
            continue
        out.append({"t":t,"open":o,"high":h,"low":l,"close":c})
    return out


def _parse_metrics_zip(raw):
    z=zipfile.ZipFile(io.BytesIO(raw))
    txt=z.read(z.namelist()[0]).decode("utf-8-sig")
    out=[]
    for r in csv.DictReader(io.StringIO(txt)):
        try:
            t=datetime.strptime(r["create_time"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            oi=base.finite(r.get("sum_open_interest"))
        except Exception:
            continue
        if oi is not None:
            out.append({"t":t,"oi":oi})
    return out


def _daily_dates(lo,hi):
    d=lo.date()
    end=(hi-timedelta(microseconds=1)).date()
    while d <= end:
        yield d
        d += timedelta(days=1)


def load_klines(symbol,start,end):
    out=[]
    for y,m in _months(start,end):
        mlo,mhi=_month_bounds(y,m)
        seg_lo=max(start,mlo); seg_hi=min(end,mhi)
        ym=f"{y:04d}-{m:02d}"
        url=f"{KLINE_MONTHLY}/{symbol}/5m/{symbol}-5m-{ym}.zip"
        try:
            out.extend(_parse_kline_zip(base.http_bytes(url,tries=2)))
            continue
        except Exception:
            pass
        for d in _daily_dates(seg_lo,seg_hi):
            ds=d.isoformat()
            url=f"{KLINE_DAILY}/{symbol}/5m/{symbol}-5m-{ds}.zip"
            try:
                out.extend(_parse_kline_zip(base.http_bytes(url,tries=2)))
            except Exception:
                continue
    dedup={r["t"]:r for r in out if start <= r["t"] < end}
    return sorted(dedup.values(),key=lambda x:x["t"])


def load_metrics(symbol,start,end):
    out=[]
    for y,m in _months(start,end):
        mlo,mhi=_month_bounds(y,m)
        seg_lo=max(start,mlo); seg_hi=min(end,mhi)
        ym=f"{y:04d}-{m:02d}"
        url=f"{METRICS_MONTHLY}/{symbol}/{symbol}-metrics-{ym}.zip"
        try:
            out.extend(_parse_metrics_zip(base.http_bytes(url,tries=2)))
            continue
        except Exception:
            pass
        for d in _daily_dates(seg_lo,seg_hi):
            ds=d.isoformat()
            url=f"{METRICS_DAILY}/{symbol}/{symbol}-metrics-{ds}.zip"
            try:
                out.extend(_parse_metrics_zip(base.http_bytes(url,tries=2)))
            except Exception:
                continue
    dedup={r["t"]:r for r in out if start <= r["t"] < end}
    return sorted(dedup.values(),key=lambda x:x["t"])


def align(klines,metrics):
    mts=[r["t"] for r in metrics]
    rows=[]
    for k in klines:
        i=bisect.bisect_right(mts,k["t"])-1
        if i < 0: continue
        m=metrics[i]
        lag=(k["t"]-m["t"]).total_seconds()/60.0
        if lag < 0 or lag > 5.1:
            continue
        x=dict(k); x["oi"]=m["oi"]; x["oi_t"]=m["t"]; x["oi_lag_min"]=lag
        rows.append(x)
    return rows


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def candidate_at(rows,i):
    if i < BUILD_BARS + FLUSH_BARS - 1:
        return None
    flush=rows[i-FLUSH_BARS+1:i+1]
    build=rows[i-FLUSH_BARS-BUILD_BARS+1:i-FLUSH_BARS+1]
    if len(build) != BUILD_BARS or len(flush) != FLUSH_BARS:
        return None
    bp=build[-1]["close"]/build[0]["open"]-1.0
    bo=build[-1]["oi"]/build[0]["oi"]-1.0 if build[0]["oi"] else 0.0
    fp=flush[-1]["close"]/flush[0]["open"]-1.0
    fo=flush[-1]["oi"]/flush[0]["oi"]-1.0 if flush[0]["oi"] else 0.0
    bd=sign(bp); fd=sign(fp)
    if bd == 0 or fd == 0 or bo <= 0 or fo >= 0 or fd != -bd:
        return None
    entry_dir=fd
    entry=flush[-1]["close"]
    stop=min(x["low"] for x in flush) if entry_dir > 0 else max(x["high"] for x in flush)
    risk=entry-stop if entry_dir > 0 else stop-entry
    if risk <= 0:
        return None
    target=entry + entry_dir*RR*risk
    return {
        "signal_time":flush[-1]["t"],
        "build_direction":"UP" if bd>0 else "DOWN",
        "trade_direction":"LONG" if entry_dir>0 else "SHORT",
        "entry_dir":entry_dir,
        "entry":entry,
        "stop":stop,
        "target":target,
        "risk_pct":100.0*risk/entry,
        "build_price_ret_pct":100.0*bp,
        "build_oi_ret_pct":100.0*bo,
        "flush_price_ret_pct":100.0*fp,
        "flush_oi_ret_pct":100.0*fo,
        "build_start":build[0]["t"],
        "flush_start":flush[0]["t"],
    }


def resolve(rows,i,event):
    d=event["entry_dir"]; stop=event["stop"]; target=event["target"]
    end=min(len(rows),i+1+HORIZON_BARS)
    for j in range(i+1,end):
        b=rows[j]
        hit_tp=(b["high"] >= target) if d>0 else (b["low"] <= target)
        hit_sl=(b["low"] <= stop) if d>0 else (b["high"] >= stop)
        if hit_tp and hit_sl:
            return "AMBIGUOUS", b["t"]
        if hit_tp:
            return "WIN", b["t"]
        if hit_sl:
            return "LOSS", b["t"]
    return "CENSORED", rows[end-1]["t"] if end>i+1 else None


def detect_events(symbol,rows):
    events=[]
    prev_active_dir=None
    for i in range(len(rows)):
        c=candidate_at(rows,i)
        cur_dir=c["entry_dir"] if c else None
        if c is not None and cur_dir != prev_active_dir:
            outcome,outcome_time=resolve(rows,i,c)
            c.update({"symbol":symbol,"outcome":outcome,"outcome_time":outcome_time})
            events.append(c)
        prev_active_dir=cur_dir
    return events


def median(rows,key):
    xs=[base.finite(r.get(key)) for r in rows]
    xs=[x for x in xs if x is not None]
    return round(statistics.median(xs),8) if xs else None


def by_time(rows):
    resolved=[r for r in rows if r.get("outcome") in ("WIN","LOSS")]
    if not resolved: return {}
    end=max(r["signal_time"] for r in resolved)
    cut=end-timedelta(days=60)
    return {
        "first_60d":stat([r for r in resolved if r["signal_time"] < cut]),
        "last_60d":stat([r for r in resolved if r["signal_time"] >= cut]),
        "cut":cut.isoformat(),
        "end":end.isoformat(),
    }


def main():
    # Use the last fully completed UTC day, plus enough warmup/history to
    # detect the first event and enough forward data to resolve late events.
    today=datetime.now(timezone.utc).date()
    sample_end=datetime.combine(today,datetime.min.time(),tzinfo=timezone.utc)
    sample_start=sample_end-timedelta(days=DAYS)
    load_start=sample_start-timedelta(hours=2)
    load_end=sample_end+timedelta(hours=1)

    all_events=[]; coverage={}; errors={}
    for p in PAIRS:
        try:
            kl=load_klines(p,load_start,load_end)
            mt=load_metrics(p,load_start,load_end)
            rows=align(kl,mt)
            ev=detect_events(p,rows)
            ev=[r for r in ev if sample_start <= r["signal_time"] < sample_end]
            all_events.extend(ev)
            coverage[p]={
                "klines":len(kl),"metrics":len(mt),"aligned":len(rows),"events":len(ev),
                "first":rows[0]["t"].isoformat() if rows else None,
                "last":rows[-1]["t"].isoformat() if rows else None,
            }
        except Exception as e:
            errors[p]=str(e)

    resolved=[r for r in all_events if r.get("outcome") in ("WIN","LOSS")]
    by_pair={p:stat([r for r in all_events if r["symbol"]==p]) for p in PAIRS}
    by_dir={d:stat([r for r in all_events if r["trade_direction"]==d]) for d in ("LONG","SHORT")}
    bt=by_time(all_events)
    overall=stat(all_events)
    pair_ok=sum(1 for p,z in by_pair.items() if z["resolved"]>=5 and (z["wr_pct"] or 0)>50.0)
    dir_ok=all(by_dir[d]["resolved"]>=10 and (by_dir[d]["wr_pct"] or 0)>50.0 for d in by_dir)
    time_ok=bool(bt) and all(bt[k]["resolved"]>=10 and (bt[k]["wr_pct"] or 0)>50.0 for k in ("first_60d","last_60d"))

    wins=[r for r in resolved if r["outcome"]=="WIN"]
    losses=[r for r in resolved if r["outcome"]=="LOSS"]
    fields=["risk_pct","build_price_ret_pct","build_oi_ret_pct","flush_price_ret_pct","flush_oi_ret_pct"]
    diagnostics={f:{"winner_median":median(wins,f),"loser_median":median(losses,f)} for f in fields}

    result={
        "phase":"V5-C",
        "status":"DERIVATIVES_NATIVE_FROZEN_120D_SCREEN",
        "frozen_definition":{
            "sample":"last 120 fully completed UTC days",
            "event":"60m nonzero price direction + net OI up, followed immediately by 15m opposite price move + net OI down",
            "trigger":"first transition only; overlapping same-direction repeats suppressed",
            "entry":"after 15m flush closes, in flush direction",
            "stop":"15m flush extreme",
            "target":"1R",
            "tracking":"next 5m bar onward; same-child TP+SL ambiguous excluded; 72h horizon",
            "magnitude_thresholds":None,
            "threshold_sweep":False,
            "support_resistance":False,
            "other_filters":False,
            "primary_hypothesis":"forced unwind displacement has short-term continuation edge",
        },
        "predeclared_gate":{
            "overall_wr_pct":">=70",
            "resolved_n":">=20",
            "pair_distribution":">=3/4 pairs each resolved>=5 and WR>50",
            "both_directions":"LONG and SHORT each resolved>=10 and WR>50",
            "both_60d_halves":"each resolved>=10 and WR>50",
        },
        "sample_start":sample_start.isoformat(),
        "sample_end_exclusive":sample_end.isoformat(),
        "coverage":coverage,
        "overall":overall,
        "by_pair":by_pair,
        "by_direction":by_dir,
        "by_time":bt,
        "diagnostics_only":diagnostics,
        "gate_checks":{
            "pairs_passing":pair_ok,
            "direction_check":dir_ok,
            "time_check":time_ok,
            "earns_971d_validation":bool(
                overall["resolved"]>=20 and (overall["wr_pct"] or 0)>=70.0
                and pair_ok>=3 and dir_ok and time_ok
            ),
        },
        "errors":errors,
        "notes":{
            "interpretation":"No alternative direction, window, stop, or magnitude threshold may be promoted post-hoc from this same sample.",
            "next":"Only a passing frozen event earns 971d validation; otherwise reject this exact derivatives-native mechanism.",
        },
    }
    print("V5_C_RESULT",json.dumps(result,separators=(",",":"),default=str))


if __name__ == "__main__":
    main()
