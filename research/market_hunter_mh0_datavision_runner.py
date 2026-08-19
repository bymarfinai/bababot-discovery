#!/usr/bin/env python3
"""Data-source adapter for the frozen MH0 protocol.

Only replaces historical transport (restricted Binance REST -> official
Data Vision archives). It does not alter universe, features, ranking,
entry timing, controls, costs, or evaluation rules in MH0.
"""
from __future__ import annotations

import csv
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

import market_hunter_mh0_cross_sectional as mh

BASE = "https://data.binance.vision/data/futures/um"


def _fetch_zip(url: str):
    try:
        r=requests.get(url,timeout=30,headers={"User-Agent":"bababot-mh0-datavision/1.0"})
        if r.status_code==404:
            return []
        r.raise_for_status()
        z=zipfile.ZipFile(io.BytesIO(r.content))
        name=z.namelist()[0]
        out=[]
        with z.open(name) as f:
            reader=csv.reader(io.TextIOWrapper(f,encoding="utf-8"))
            for row in reader:
                if len(row)<11: continue
                try:
                    ts=int(row[0])
                except Exception:
                    continue
                # Defensive normalization if an archive ever emits microseconds.
                if ts>100_000_000_000_000:
                    ts//=1000
                row=list(row);row[0]=ts
                out.append(row)
        return out
    except Exception as e:
        print(f"archive warning {url}: {e}")
        return []


def archive_request(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> list:
    # Complete months use monthly archives. The frozen partial end month uses daily archives.
    start_month=pd.Timestamp(start.strftime("%Y-%m-01"),tz="UTC")
    end_month=pd.Timestamp(end.strftime("%Y-%m-01"),tz="UTC")
    jobs=[]
    cur=start_month
    while cur<end_month:
        ym=cur.strftime("%Y-%m")
        jobs.append(f"{BASE}/monthly/klines/{symbol}/1h/{symbol}-1h-{ym}.zip")
        cur=cur+pd.offsets.MonthBegin(1)
    day=end_month
    while day<end.normalize():
        ds=day.strftime("%Y-%m-%d")
        jobs.append(f"{BASE}/daily/klines/{symbol}/1h/{symbol}-1h-{ds}.zip")
        day+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs=[ex.submit(_fetch_zip,u) for u in jobs]
        for f in as_completed(futs):
            rows.extend(f.result())
    lo=int(start.timestamp()*1000);hi=int(end.timestamp()*1000)
    rows=[r for r in rows if lo<=int(r[0])<hi]
    rows.sort(key=lambda r:int(r[0]))
    return rows


def main():
    mh._request=archive_request
    mh.main()


if __name__=="__main__":
    main()
