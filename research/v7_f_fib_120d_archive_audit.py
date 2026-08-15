#!/usr/bin/env python3
"""V7-F — fixed Fibonacci 61.8-70.5 audit in non-overlapping 120d blocks.

Research only. Reconstructs the 971d 1H+5m OHLCV dataset from official
Binance USD-M archive files into an isolated temporary SQLite DB, then calls
the unchanged V4-B2 Fibonacci forensic implementation.

No threshold sweep. Fixed RR=1, confirm_bars=3, band=61.8-70.5.
The 971-day stream is computed once and then bucketed into 8 x 120d blocks
plus the final 11d remainder. This avoids window-boundary recomputation.
"""
import csv
import io
import json
import math
import os
import sqlite3
import time
import zipfile
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PAIRS=["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
TFS=["1h","5m"]
DAYS=971
BLOCK_DAYS=120
BAND="61.8-70.5"
DB="/tmp/v7_f_fib_market.db"
MONTHLY="https://data.binance.vision/data/futures/um/monthly/klines"
DAILY="https://data.binance.vision/data/futures/um/daily/klines"


def http_bytes(url, tries=2, timeout=35):
    last=None
    for i in range(tries):
        try:
            req=Request(url,headers={"User-Agent":"BabaBot-V7-F/1.0"})
            with urlopen(req,timeout=timeout) as r:return r.read()
        except (HTTPError,URLError,TimeoutError) as e:
            last=e
            if isinstance(e,HTTPError) and e.code==404:break
            time.sleep(min(i+1,2))
    raise RuntimeError(f"GET failed {url}: {last}")


def months(start,end):
    y,m=start.year,start.month
    while (y,m) <= (end.year,end.month):
        yield y,m
        if m==12:y,m=y+1,1
        else:m+=1


def month_bounds(y,m):
    lo=datetime(y,m,1,tzinfo=timezone.utc)
    hi=datetime(y+1,1,1,tzinfo=timezone.utc) if m==12 else datetime(y,m+1,1,tzinfo=timezone.utc)
    return lo,hi


def daily_dates(lo,hi):
    d=lo.date(); end=(hi-timedelta(microseconds=1)).date()
    while d<=end:
        yield d; d+=timedelta(days=1)


def parse_zip(raw,symbol,tf,start_ms,end_ms):
    z=zipfile.ZipFile(io.BytesIO(raw)); txt=z.read(z.namelist()[0]).decode("utf-8-sig")
    out=[]
    for r in csv.reader(io.StringIO(txt)):
        if len(r)<11:continue
        try:
            t=int(float(r[0])); o=float(r[1]); h=float(r[2]); l=float(r[3]); c=float(r[4]); v=float(r[5])
            close_t=int(float(r[6])); quote_v=float(r[7]); trades=int(float(r[8])); taker_v=float(r[9]); taker_q=float(r[10])
        except Exception:continue
        if t>10_000_000_000_000:t//=1000
        if close_t>10_000_000_000_000:close_t//=1000
        if start_ms<=t<end_ms:
            out.append((symbol,tf,t,o,h,l,c,v,close_t,quote_v,trades,taker_v,taker_q))
    return out


def load_series(symbol,tf,start,end):
    start_ms=int(start.timestamp()*1000); end_ms=int(end.timestamp()*1000); out=[]
    for y,m in months(start,end):
        mlo,mhi=month_bounds(y,m); seg_lo=max(start,mlo); seg_hi=min(end,mhi)
        ym=f"{y:04d}-{m:02d}"; url=f"{MONTHLY}/{symbol}/{tf}/{symbol}-{tf}-{ym}.zip"
        try:
            out.extend(parse_zip(http_bytes(url),symbol,tf,start_ms,end_ms)); continue
        except Exception:pass
        for d in daily_dates(seg_lo,seg_hi):
            ds=d.isoformat(); url=f"{DAILY}/{symbol}/{tf}/{symbol}-{tf}-{ds}.zip"
            try:out.extend(parse_zip(http_bytes(url),symbol,tf,start_ms,end_ms))
            except Exception:continue
    dedup={r[2]:r for r in out}
    return [dedup[k] for k in sorted(dedup)]


def stat(xs):
    n=len(xs); w=sum(x["win"] for x in xs)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":round(100*w/n,2) if n else None}


def wilson(w,n,z=1.96):
    if not n:return [None,None]
    p=w/n; den=1+z*z/n; ctr=(p+z*z/(2*n))/den
    rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(ctr-rad),2),round(100*(ctr+rad),2)]


def main():
    end=datetime.now(timezone.utc)
    start=end-timedelta(days=DAYS)
    if os.path.exists(DB):os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for p in PAIRS:
        coverage[p]={}
        for tf in TFS:
            rows=load_series(p,tf,start,end)
            conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows); conn.commit()
            coverage[p][tf]={"rows":len(rows),"first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,"last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None}
    conn.close()

    os.environ["DB_PATH"]=DB
    from v4_context_fib_forensic_endpoint import context_fib_forensic

    events=[]; source={}; errors={}
    for p in PAIRS:
        d=context_fib_forensic(symbols=p,days=DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        source[p]={"overall":d.get("overall"),"fib_bands":d.get("fib_bands"),"errors":d.get("errors")}
        if d.get("errors"):errors[p]=d["errors"]
        sample=d.get("sample") or []
        if int((d.get("overall") or {}).get("n",0) or 0)>len(sample):
            raise RuntimeError(f"sample truncated for {p}: {d.get('overall')} > {len(sample)}")
        for x in sample:
            if x.get("outcome") not in ("BOUNCE","BREAK") or x.get("fib_band")!=BAND:continue
            t=datetime.fromisoformat(x["confirm_time"])
            if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
            events.append({"pair":p,"t":t.astimezone(timezone.utc),"win":1 if x["outcome"]=="BOUNCE" else 0,"side":x.get("side")})
    events.sort(key=lambda x:x["t"])

    blocks=[]
    for i in range(8):
        lo=start+timedelta(days=120*i); hi=lo+timedelta(days=120)
        xs=[x for x in events if lo<=x["t"]<hi]
        s=stat(xs); s["wilson95_pct"]=wilson(s["wins"],s["n"])
        blocks.append({"block":i+1,"start":lo.isoformat(),"end_exclusive":hi.isoformat(),"fixed_band":s,
                       "by_pair":{p:stat([x for x in xs if x["pair"]==p]) for p in PAIRS},
                       "by_side":{side:stat([x for x in xs if x["side"]==side]) for side in ("DEMAND","SUPPLY")}})
    rem_lo=start+timedelta(days=960); rem=[x for x in events if rem_lo<=x["t"]<end]
    remainder={"days":11,"start":rem_lo.isoformat(),"end_exclusive":end.isoformat(),"fixed_band":stat(rem),"by_pair":{p:stat([x for x in rem if x["pair"]==p]) for p in PAIRS}}
    overall=stat(events)
    block_n=sum(b["fixed_band"]["n"] for b in blocks)+remainder["fixed_band"]["n"]
    block_w=sum(b["fixed_band"]["wins"] for b in blocks)+remainder["fixed_band"]["wins"]
    valid=[b["fixed_band"] for b in blocks if b["fixed_band"]["n"]]
    result={
        "phase":"V7-F",
        "status":"OFFICIAL_ARCHIVE_FIXED_FIB_120D_AUDIT",
        "definition":{"history_days":DAYS,"fixed_fib_band":BAND,"rr":1.0,"confirm_bars":3,"blocks":"8x120d + 11d remainder","overlap":False,"recompute_per_block":False,"threshold_sweep":False},
        "window":{"start":start.isoformat(),"end_exclusive":end.isoformat()},
        "coverage":coverage,"errors":errors,
        "fixed_band_overall":overall,
        "historical_b4_fingerprint":{"n":120,"wins":61,"losses":59,"wr_pct":50.83},
        "blocks_120d":blocks,"remainder_11d":remainder,
        "consistency":{"sum_n":block_n,"sum_wins":block_w,"matches_overall":block_n==overall["n"] and block_w==overall["wins"]},
        "dispersion":{"min_wr_pct":min((x["wr_pct"] for x in valid),default=None),"max_wr_pct":max((x["wr_pct"] for x in valid),default=None),"blocks_wr_ge70":sum((x["wr_pct"] or 0)>=70 for x in valid),"blocks_wr_ge80":sum((x["wr_pct"] or 0)>=80 for x in valid)},
        "source_pair_diagnostics":source,
    }
    print("V7_FIB120_ARCHIVE_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
