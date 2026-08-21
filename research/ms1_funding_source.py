#!/usr/bin/env python3
from __future__ import annotations
import io, zipfile
import pandas as pd
import requests

BASE='https://data.binance.vision/data/futures/um'
SYMBOL='BTCUSDT'

def month_iter(start,end):
    cur=pd.Timestamp(start.year,start.month,1,tz='UTC')
    last=pd.Timestamp(end.year,end.month,1,tz='UTC')
    while cur<=last:
        yield cur.year,cur.month
        cur+=pd.offsets.MonthBegin(1)

def read_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-discovery-ms1-data/1.0'})
    if r.status_code==404:return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(name) as f:return pd.read_csv(f)

def load_archived_funding():
    frames=[]
    for y,m in month_iter(pd.Timestamp('2022-12-01',tz='UTC'),pd.Timestamp('2026-07-31',tz='UTC')):
        ym=f'{y:04d}-{m:02d}'
        url=f'{BASE}/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{ym}.zip'
        df=read_zip(url)
        if df is None:continue
        df.columns=[str(c).strip().lower() for c in df.columns]
        tc='calc_time' if 'calc_time' in df.columns else 'fundingtime'
        rc='last_funding_rate' if 'last_funding_rate' in df.columns else 'fundingrate'
        vals=pd.to_numeric(df[tc],errors='coerce')
        if vals.notna().mean()>.9:
            unit='us' if vals.dropna().median()>1e14 else 'ms'
            ts=pd.to_datetime(vals,unit=unit,utc=True)
        else:
            ts=pd.to_datetime(df[tc],utc=True,errors='coerce')
        frames.append(pd.DataFrame({'ts':ts,'funding_rate':pd.to_numeric(df[rc],errors='coerce')}))
    if not frames:raise RuntimeError('no archived funding')
    return pd.concat(frames,ignore_index=True).dropna().drop_duplicates('ts').sort_values('ts')

def load_recent_funding():
    start=int(pd.Timestamp('2026-08-01',tz='UTC').timestamp()*1000)
    end=int(pd.Timestamp('2026-08-21',tz='UTC').timestamp()*1000)
    errors=[]
    for url in ['https://www.binance.com/fapi/v1/fundingRate','https://fapi.binance.com/fapi/v1/fundingRate']:
        try:
            r=requests.get(url,params={'symbol':SYMBOL,'startTime':start,'endTime':end,'limit':1000},timeout=60,headers={'User-Agent':'bababot-discovery-ms1-data/1.0'})
            if r.status_code!=200:
                errors.append(f'{url}:{r.status_code}');continue
            a=r.json()
            if not isinstance(a,list) or not a:
                errors.append(f'{url}:empty');continue
            z=pd.DataFrame(a)
            out=pd.DataFrame({'ts':pd.to_datetime(pd.to_numeric(z['fundingTime']),unit='ms',utc=True),'funding_rate':pd.to_numeric(z['fundingRate'],errors='coerce')}).dropna()
            if len(out)>=20:return out
            errors.append(f'{url}:few rows')
        except Exception as e:errors.append(f'{url}:{type(e).__name__}')
    raise RuntimeError('recent funding unavailable '+' | '.join(errors))
