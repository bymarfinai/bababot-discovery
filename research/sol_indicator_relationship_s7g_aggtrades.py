#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7G-C raw aggTrades directional flow."""
from __future__ import annotations

import concurrent.futures as cf
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import sol_indicator_relationship_s7d as s7d

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_Result.json"
OUT_COVER=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_COVERAGE.csv"
OUT_EVENTS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_EVENT_FEATURES.csv"
OUT_BUCKETS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_BUCKETS.csv"
OUT_SUMMARY=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_SUMMARY.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_C_Status.txt"

BASE="https://data.binance.vision/data/futures/um/daily/aggTrades/SOLUSDT"
FEATURES=[
    "signed_taker_notional_imb_30s","signed_taker_notional_imb_1m","signed_taker_notional_imb_5m",
    "signed_trade_count_imb_30s","signed_trade_count_imb_1m","signed_trade_count_imb_5m",
    "signed_large_notional_imb_1m","signed_large_notional_imb_5m",
    "signed_flow_accel_30s_vs_5m","signed_flow_accel_1m_vs_5m",
    "signed_last20_aggressor_mean","signed_last50_aggressor_mean",
]
PARTS=["development","validation_2025","validation_2026"]

def gpart(split):
    if split in {"train_2023","dev_select_2024"}: return "development"
    if split=="validation_2025": return "validation_2025"
    if split=="validation_2026": return "validation_2026"
    return None

def url_for(day):
    ds=pd.Timestamp(day).strftime("%Y-%m-%d")
    return f"{BASE}/SOLUSDT-aggTrades-{ds}.zip"

def fetch_day(day):
    u=url_for(day)
    for attempt in range(5):
        try:
            r=requests.get(u,timeout=90,headers={"User-Agent":"bababot-stage7g-c/1.0"})
            if r.status_code==404:
                return None,0,"404"
            r.raise_for_status()
            return r.content,len(r.content),"ok"
        except Exception as e:
            if attempt==4:
                return None,0,f"{type(e).__name__}:{e}"
            time.sleep(1.5*(attempt+1))
    return None,0,"unknown"

def parse_bytes(data):
    if data is None: return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names=[n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names: return None
            with z.open(names[0]) as fh:
                df=pd.read_csv(fh,usecols=[
                    "price","quantity","transact_time","is_buyer_maker"
                ])
    except Exception:
        return None
    for c in ["price","quantity","transact_time"]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["price","quantity","transact_time"])
    if df.empty: return None
    tm=df.transact_time.to_numpy(np.float64)
    # Futures timestamps are expected in ms; tolerate microseconds if archive changes.
    if np.nanmedian(tm)>1e14:
        tm=tm/1000.0
    tm=tm.astype(np.int64)
    price=df.price.to_numpy(float)
    qty=df.quantity.to_numpy(float)
    bm=df.is_buyer_maker
    if pd.api.types.is_bool_dtype(bm):
        is_bm=bm.to_numpy(bool)
    else:
        is_bm=bm.astype(str).str.lower().isin(["true","1"]).to_numpy(bool)
    aggr=np.where(is_bm,-1.0,1.0)
    order=np.argsort(tm,kind="mergesort")
    return {
        "t":tm[order],
        "price":price[order],
        "qty":qty[order],
        "aggr":aggr[order],
    }

def merge_arrays(a,b):
    if a is None: return b
    if b is None: return a
    out={k:np.concatenate([a[k],b[k]]) for k in a}
    order=np.argsort(out["t"],kind="mergesort")
    return {k:v[order] for k,v in out.items()}

def window_stats(arr,t_ms,window_ms,side_sign,large=False):
    ts=arr["t"]
    hi=np.searchsorted(ts,t_ms,side="right")
    lo=np.searchsorted(ts,t_ms-window_ms,side="left")
    if hi<=lo:
        return np.nan,np.nan,0
    price=arr["price"][lo:hi]
    qty=arr["qty"][lo:hi]
    aggr=arr["aggr"][lo:hi]
    notional=price*qty
    ok=np.isfinite(notional)&(notional>0)&np.isfinite(aggr)
    notional=notional[ok];aggr=aggr[ok]
    if len(notional)==0: return np.nan,np.nan,0
    if large:
        if len(notional)<10: return np.nan,np.nan,len(notional)
        cut=float(np.quantile(notional,.90,method="linear"))
        m=notional>=cut
        notional=notional[m];aggr=aggr[m]
        if len(notional)==0: return np.nan,np.nan,0
    denom=float(notional.sum())
    nimb=float((aggr*notional).sum()/denom) if denom>0 else np.nan
    cimb=float(aggr.mean())
    return side_sign*nimb,side_sign*cimb,len(notional)

def last_n_mean(arr,t_ms,n,side_sign):
    hi=np.searchsorted(arr["t"],t_ms,side="right")
    lo5=np.searchsorted(arr["t"],t_ms-300_000,side="left")
    if hi-lo5<n: return np.nan
    return float(side_sign*arr["aggr"][hi-n:hi].mean())

def event_features(arr,t,side):
    if arr is None:
        return {f:np.nan for f in FEATURES}
    t_ms=int(pd.Timestamp(t).timestamp()*1000)
    s=1.0 if side=="LONG" else -1.0
    n30,c30,_=window_stats(arr,t_ms,30_000,s,False)
    n1,c1,_=window_stats(arr,t_ms,60_000,s,False)
    n5,c5,_=window_stats(arr,t_ms,300_000,s,False)
    l1,_,_=window_stats(arr,t_ms,60_000,s,True)
    l5,_,_=window_stats(arr,t_ms,300_000,s,True)
    return {
        "signed_taker_notional_imb_30s":n30,
        "signed_taker_notional_imb_1m":n1,
        "signed_taker_notional_imb_5m":n5,
        "signed_trade_count_imb_30s":c30,
        "signed_trade_count_imb_1m":c1,
        "signed_trade_count_imb_5m":c5,
        "signed_large_notional_imb_1m":l1,
        "signed_large_notional_imb_5m":l5,
        "signed_flow_accel_30s_vs_5m":n30-n5 if np.isfinite(n30) and np.isfinite(n5) else np.nan,
        "signed_flow_accel_1m_vs_5m":n1-n5 if np.isfinite(n1) and np.isfinite(n5) else np.nan,
        "signed_last20_aggressor_mean":last_n_mean(arr,t_ms,20,s),
        "signed_last50_aggressor_mean":last_n_mean(arr,t_ms,50,s),
    }

def process_day(args):
    day,records=args
    data,size,note=fetch_day(day)
    arr=parse_bytes(data)
    # Need previous day only for events in first 5 minutes UTC.
    early=any((pd.Timestamp(r["onset_ts"]).hour==0 and pd.Timestamp(r["onset_ts"]).minute<5) for r in records)
    prev_bytes=0
    if early:
        pdata,psize,_=fetch_day(pd.Timestamp(day)-pd.Timedelta(days=1))
        prev_bytes=psize
        parr=parse_bytes(pdata)
        arr=merge_arrays(parr,arr)
    rows=[]
    for r in records:
        base={
            "split":r["split"],"g_partition":r["g_partition"],
            "onset_ts":r["onset_ts"],"side":r["side"],
            "cell_id":r["cell_id"],"exit_reason":r["exit_reason"],
            "label_tp":r["label_tp"],
        }
        base.update(event_features(arr,r["onset_ts"],r["side"]))
        rows.append(base)
    return rows,{"date":str(day),"ok":arr is not None,"bytes":size+prev_bytes,"note":note}

def assemble(ds):
    ev=ds.copy()
    ev["g_partition"]=ev["split"].map(gpart)
    ev=ev[ev.g_partition.notna()].sort_values("onset_ts").reset_index(drop=True)
    ev["event_date"]=pd.to_datetime(ev.onset_ts,utc=True).dt.floor("D")
    tasks=[]
    for day,g in ev.groupby("event_date",sort=True):
        records=g[["split","g_partition","onset_ts","side","cell_id","exit_reason","label_tp"]].to_dict(orient="records")
        tasks.append((day,records))
    rows=[];downloads=[]
    # Parallelism intentionally modest because daily files can be large once decompressed.
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for rr,meta in ex.map(process_day,tasks):
            rows.extend(rr);downloads.append(meta)
    return pd.DataFrame(rows),pd.DataFrame(downloads)

def coverage(ev):
    rows=[]
    for p in PARTS:
        g=ev[ev.g_partition==p]
        complete=g[FEATURES].notna().all(axis=1)
        rows.append({
            "partition":p,"n":len(g),
            "all_features_coverage":float(complete.mean()) if len(g) else 0.0,
            **{f"{f}_coverage":float(g[f].notna().mean()) if len(g) else 0.0 for f in FEATURES}
        })
    return pd.DataFrame(rows)

def tertile_spec(s):
    q=s.dropna().quantile([1/3,2/3])
    return float(q.iloc[0]),float(q.iloc[1])

def bucket(v,q1,q2):
    if not np.isfinite(v): return None
    if v<=q1: return "LOW"
    if v>=q2: return "HIGH"
    return "MID"

def anatomy(ev):
    resolved=ev[ev.exit_reason.isin(["TP","SL"])].copy()
    dev=resolved[resolved.g_partition=="development"]
    brows=[];srows=[]
    for f in FEATURES:
        q1,q2=tertile_spec(dev[f])
        deltas={};ns={}
        for p in PARTS:
            g=resolved[resolved.g_partition==p].copy()
            g["bucket"]=[bucket(v,q1,q2) for v in g[f].to_numpy(float)]
            rates={};counts={}
            for b in ["LOW","MID","HIGH"]:
                z=g[g.bucket==b];n=len(z)
                tp=float((z.exit_reason=="TP").mean()) if n else np.nan
                counts[b]=n;rates[b]=tp
                brows.append({"feature":f,"partition":p,"bucket":b,"q1_dev":q1,"q2_dev":q2,"n":n,"tp_rate":tp})
            deltas[p]=rates["HIGH"]-rates["LOW"] if np.isfinite(rates["HIGH"]) and np.isfinite(rates["LOW"]) else np.nan
            ns[p]=(counts["LOW"],counts["HIGH"])
        dd=deltas["development"];d25=deltas["validation_2025"];d26=deltas["validation_2026"]
        nd=ns["development"];n25=ns["validation_2025"];n26=ns["validation_2026"]
        support=nd[0]>=150 and nd[1]>=150 and n25[0]>=75 and n25[1]>=75 and n26[0]>=75 and n26[1]>=75
        same=np.isfinite(dd) and np.sign(dd)!=0 and np.sign(d25)==np.sign(dd) and np.sign(d26)==np.sign(dd)
        rep=bool(support and abs(dd)>=.08 and same and abs(d25)>=.04 and abs(d26)>=.04)
        srows.append({
            "feature":f,"q1_dev":q1,"q2_dev":q2,
            "development_delta_tp":dd,"validation_2025_delta_tp":d25,"validation_2026_delta_tp":d26,
            "development_low_n":nd[0],"development_high_n":nd[1],
            "validation_2025_low_n":n25[0],"validation_2025_high_n":n25[1],
            "validation_2026_low_n":n26[0],"validation_2026_high_n":n26[1],
            "classification":"REPLICATED_DIRECTIONAL_MICROSTRUCTURE" if rep else "WEAK_OR_UNSTABLE",
        })
    return pd.DataFrame(brows),pd.DataFrame(srows)

def main():
    raw,a=s7d.prepare()
    ds=s7d.build_dataset(raw,a)
    ev,dl=assemble(ds)
    ev.to_csv(OUT_EVENTS,index=False)
    cov=coverage(ev);cov.to_csv(OUT_COVER,index=False)
    source_pass=bool((cov.all_features_coverage>=.95).all())
    if source_pass:
        buckets,summary=anatomy(ev)
    else:
        buckets=pd.DataFrame();summary=pd.DataFrame()
    buckets.to_csv(OUT_BUCKETS,index=False);summary.to_csv(OUT_SUMMARY,index=False)
    reps=summary[summary.classification=="REPLICATED_DIRECTIONAL_MICROSTRUCTURE"] if len(summary) else pd.DataFrame()

    if not source_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7G_C_SOURCE_COVERAGE_FAIL"
    elif len(reps):
        status="SOL_INDICATOR_RELATIONSHIP_S7G_C_COMPLETED_WITH_REPLICATED_FEATURES"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7G_C_COMPLETED_NO_REPLICATED_FEATURE"
    OUT_STATUS.write_text(status+"\n")

    payload={
        "status":status,"source_pass":source_pass,"event_rows":len(ev),
        "download_days":len(dl),"download_ok_days":int(dl.ok.sum()),"download_bytes":int(dl.bytes.sum()),
        "coverage":cov.to_dict(orient="records"),
        "replicated_features":reps.to_dict(orient="records") if len(reps) else [],
        "summary":summary.to_dict(orient="records") if len(summary) else [],
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")

    def pp(x):
        return "-" if x is None or not np.isfinite(x) else f"{100*x:.1f}%"
    lines=["# SOL Indicator Relationship Discovery — Stage 7G-C Result","",
           "**Historical Binance Vision SOLUSDT aggTrades; pre-onset aggressor-flow anatomy.**","",
           "## Feature coverage","",
           "| Partition | Events | All 12 features |",
           "|---|---:|---:|"]
    for r in cov.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.n} | {pp(r.all_features_coverage)} |")
    lines += ["",f"Source gate: **{'PASS' if source_pass else 'FAIL'}**.",""]
    if source_pass:
        lines += ["## Frozen single-feature replication atlas","",
                  "| Feature | DEV ΔTP | 2025 ΔTP | 2026 ΔTP | Class |",
                  "|---|---:|---:|---:|---|"]
        for r in summary.sort_values("development_delta_tp",key=lambda s:s.abs(),ascending=False).itertuples(index=False):
            lines.append(f"| {r.feature} | {pp(r.development_delta_tp)} | {pp(r.validation_2025_delta_tp)} | {pp(r.validation_2026_delta_tp)} | {r.classification} |")
        lines += ["","## Replicated features",""]
        if len(reps):
            for r in reps.itertuples(index=False):
                lines.append(f"- **{r.feature}**: DEV {pp(r.development_delta_tp)}, 2025 {pp(r.validation_2025_delta_tp)}, 2026 {pp(r.validation_2026_delta_tp)}.")
        else:
            lines.append("- none")
    else:
        lines.append("Outcome-bearing anatomy was not run because source/feature coverage failed.")
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
