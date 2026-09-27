#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf
import json
from pathlib import Path
import requests
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
OUT_CSV=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A2_FULL_ARCHIVE_COVERAGE.csv"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A2_FULL_ARCHIVE_COVERAGE.json"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A2_Status.txt"

BASE="https://data.binance.vision/data/futures/um/daily"
SYMBOL="SOLUSDT"
TYPES=["bookDepth","aggTrades"]
START=pd.Timestamp("2023-01-01",tz="UTC")
END=pd.Timestamp("2026-09-24",tz="UTC")

def make_url(dtype,date):
    d=date.strftime("%Y-%m-%d")
    return f"{BASE}/{dtype}/{SYMBOL}/{SYMBOL}-{dtype}-{d}.zip"

def probe(item):
    dtype,date=item
    u=make_url(dtype,date)
    try:
        r=requests.head(u,allow_redirects=True,timeout=20,headers={"User-Agent":"bababot-research/1.0"})
        return {
            "data_type":dtype,"date":date.strftime("%Y-%m-%d"),"status":r.status_code,
            "exists":r.status_code==200,
            "content_length":int(r.headers.get("content-length","0") or 0),
        }
    except Exception:
        return {"data_type":dtype,"date":date.strftime("%Y-%m-%d"),"status":-1,"exists":False,"content_length":0}

def main():
    dates=list(pd.date_range(START,END,freq="D"))
    tasks=[(dtype,d) for dtype in TYPES for d in dates]
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        rows=list(ex.map(probe,tasks))
    df=pd.DataFrame(rows)
    df.to_csv(OUT_CSV,index=False)

    summary={}
    for dtype in TYPES:
        q=df[df.data_type==dtype]
        by_year={}
        for y,g in q.groupby(pd.to_datetime(q.date).dt.year):
            by_year[str(y)]={
                "days":int(len(g)),"exists":int(g.exists.sum()),
                "coverage":float(g.exists.mean()),
            }
        summary[dtype]={
            "days":int(len(q)),"exists":int(q.exists.sum()),
            "coverage":float(q.exists.mean()),
            "total_bytes":int(q.loc[q.exists,"content_length"].sum()),
            "year":by_year,
            "core_eligible":bool(q.exists.mean()>=0.95),
        }
    payload={"start":str(START),"end":str(END),"summary":summary}
    OUT_JSON.write_text(json.dumps(payload,indent=2)+"\n")
    status="SOL_INDICATOR_RELATIONSHIP_S7G_A2_COMPLETED"
    OUT_STATUS.write_text(status+"\n")
    print(json.dumps(payload,indent=2))

if __name__=="__main__":
    main()
