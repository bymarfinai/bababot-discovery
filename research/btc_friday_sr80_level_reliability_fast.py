#!/usr/bin/env python3
"""Fast transport wrapper for frozen SR80.

Only replaces historical BTCUSDT 5m download transport with concurrent official
Binance Data Vision monthly archive reads. The SR80 research definition, labels,
features, split, tree and gates remain in btc_friday_sr80_level_reliability.py.
"""
from __future__ import annotations
import csv, io, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import requests

import btc_friday_sr80_level_reliability as sr

BASE="https://data.binance.vision/data/futures/um"
START=pd.Timestamp("2023-11-01T00:00:00Z")
END=pd.Timestamp("2026-08-01T00:00:00Z")

def fetch_month(ym:str):
    url=f"{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{ym}.zip"
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-sr80-fast/1.0"})
    if r.status_code==404:return []
    r.raise_for_status(); out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<8:continue
                try: ts=int(row[0])
                except Exception: continue
                if ts>100_000_000_000_000: ts//=1000
                try:
                    out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),float(row[7])])
                except Exception: continue
    return out

def fast_load():
    months=[]; cur=pd.Timestamp(START.year,START.month,1,tz='UTC'); last=pd.Timestamp(2026,7,1,tz='UTC')
    while cur<=last:
        months.append(cur.strftime('%Y-%m')); cur+=pd.offsets.MonthBegin(1)
    rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs={ex.submit(fetch_month,m):m for m in months}
        for f in as_completed(fs): rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','volume','quote_volume'])
    if x.empty: raise RuntimeError('no Data Vision rows')
    x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=START)&(x.ts<END)].copy()
    if len(x)<250000: raise RuntimeError(f'insufficient 5m rows {len(x)}')
    x['ema7']=x['close'].ewm(span=7,adjust=False).mean()
    x['ema20']=x['close'].ewm(span=20,adjust=False).mean()
    x['ema_spread']=x['ema7']/x['ema20']-1.0
    x['ret5']=x['close'].pct_change()
    x['taker_imb']=np.nan
    x=x.set_index('ts',drop=False)
    return x

if __name__=='__main__':
    sr.f517.load_klines=fast_load
    sr.main()
