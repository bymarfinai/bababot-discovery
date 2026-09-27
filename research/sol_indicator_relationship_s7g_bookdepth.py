#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7G-B bookDepth directional anatomy."""
from __future__ import annotations

import concurrent.futures as cf
import io
import json
import math
import os
from pathlib import Path
import time
import zipfile

import numpy as np
import pandas as pd
import requests

import sol_indicator_relationship_s7d as s7d

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_Result.json"
OUT_COVER=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_COVERAGE.csv"
OUT_EVENTS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_EVENT_FEATURES.csv"
OUT_BUCKETS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_BUCKETS.csv"
OUT_SUMMARY=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_SUMMARY.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_B_Status.txt"

BASE="https://data.binance.vision/data/futures/um/daily/bookDepth/SOLUSDT"
CACHE=Path("/tmp/sol_s7g_bookdepth")
CACHE.mkdir(parents=True,exist_ok=True)

MAX_AGE_SEC=90.0
FEATURES=[
    "signed_depth_imb_1","signed_depth_imb_2","signed_depth_imb_5",
    "signed_notional_imb_1","signed_notional_imb_2","signed_notional_imb_5",
    "signed_depth_slope_1to5","signed_notional_slope_1to5",
    "depth_imb1_change_1m","depth_imb1_change_5m","depth_imb1_change_15m",
    "depth_imb5_change_1m","depth_imb5_change_5m","depth_imb5_change_15m",
    "notional_imb1_change_1m","notional_imb1_change_5m","notional_imb1_change_15m",
]
PARTS=["development","validation_2025","validation_2026"]

def gpart(split):
    if split in {"train_2023","dev_select_2024"}: return "development"
    if split=="validation_2025": return "validation_2025"
    if split=="validation_2026": return "validation_2026"
    return None

def url_for(day):
    ds=pd.Timestamp(day).strftime("%Y-%m-%d")
    return f"{BASE}/SOLUSDT-bookDepth-{ds}.zip"

def path_for(day):
    ds=pd.Timestamp(day).strftime("%Y-%m-%d")
    return CACHE/f"SOLUSDT-bookDepth-{ds}.zip"

def download_one(day):
    p=path_for(day)
    if p.exists() and p.stat().st_size>100:
        return str(day),True,p.stat().st_size,"cached"
    u=url_for(day)
    for attempt in range(4):
        try:
            r=requests.get(u,timeout=45,headers={"User-Agent":"bababot-stage7g/1.0"})
            if r.status_code==404:
                return str(day),False,0,"404"
            r.raise_for_status()
            p.write_bytes(r.content)
            return str(day),True,p.stat().st_size,"downloaded"
        except Exception as e:
            if attempt==3:
                return str(day),False,0,f"{type(e).__name__}:{e}"
            time.sleep(1.5*(attempt+1))
    return str(day),False,0,"unknown"

def read_day(day):
    p=path_for(day)
    if not p.exists(): return None
    try:
        with zipfile.ZipFile(p) as z:
            names=[n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names: return None
            with z.open(names[0]) as fh:
                df=pd.read_csv(fh)
    except Exception:
        return None
    need={"timestamp","percentage","depth","notional"}
    if not need.issubset(df.columns): return None
    df=df[list(need)].copy()
    df["timestamp"]=pd.to_datetime(df["timestamp"],utc=True,errors="coerce")
    df["percentage"]=pd.to_numeric(df["percentage"],errors="coerce")
    df["depth"]=pd.to_numeric(df["depth"],errors="coerce")
    df["notional"]=pd.to_numeric(df["notional"],errors="coerce")
    df=df.dropna().sort_values("timestamp")
    if df.empty: return None
    piv=df.pivot_table(index="timestamp",columns="percentage",values=["depth","notional"],aggfunc="last")
    piv=piv.sort_index()
    return piv

def raw_imb(row,field,p):
    try:
        bid=float(row[(field,-float(p))]);ask=float(row[(field,float(p))])
    except Exception:
        try:
            bid=float(row[(field,-p)]);ask=float(row[(field,p)])
        except Exception:
            return np.nan
    den=bid+ask
    return (bid-ask)/den if np.isfinite(den) and den>0 else np.nan

def raw_slope(row,field):
    try:
        b1=float(row[(field,-1)]);b5=float(row[(field,-5)])
        a1=float(row[(field,1)]);a5=float(row[(field,5)])
    except Exception:
        return np.nan
    vals=[b1,b5,a1,a5]
    if not all(np.isfinite(x) and x>0 for x in vals): return np.nan
    return math.log(b5/b1)-math.log(a5/a1)

def snapshot_before(piv,target):
    if piv is None or len(piv)==0:
        return None,np.nan
    idx=piv.index.searchsorted(target,side="right")-1
    if idx<0: return None,np.nan
    ts=piv.index[idx]
    age=float((target-ts)/pd.Timedelta(seconds=1))
    if age<0 or age>MAX_AGE_SEC:
        return None,age
    return piv.iloc[idx],age

def event_features(piv,t,side):
    sign=1.0 if side=="LONG" else -1.0
    cur,age=snapshot_before(piv,t)
    out={"book_snapshot_age_sec":age}
    if cur is None:
        for f in FEATURES: out[f]=np.nan
        return out
    rawd={p:raw_imb(cur,"depth",p) for p in [1,2,5]}
    rawn={p:raw_imb(cur,"notional",p) for p in [1,2,5]}
    for p in [1,2,5]:
        out[f"signed_depth_imb_{p}"]=sign*rawd[p]
        out[f"signed_notional_imb_{p}"]=sign*rawn[p]
    out["signed_depth_slope_1to5"]=sign*raw_slope(cur,"depth")
    out["signed_notional_slope_1to5"]=sign*raw_slope(cur,"notional")

    for mins in [1,5,15]:
        lag,lag_age=snapshot_before(piv,t-pd.Timedelta(minutes=mins))
        out[f"lag{mins}_age_sec"]=lag_age
        if lag is None:
            ld1=ld5=ln1=np.nan
        else:
            ld1=raw_imb(lag,"depth",1)
            ld5=raw_imb(lag,"depth",5)
            ln1=raw_imb(lag,"notional",1)
        out[f"depth_imb1_change_{mins}m"]=sign*(rawd[1]-ld1) if np.isfinite(rawd[1]) and np.isfinite(ld1) else np.nan
        out[f"depth_imb5_change_{mins}m"]=sign*(rawd[5]-ld5) if np.isfinite(rawd[5]) and np.isfinite(ld5) else np.nan
        out[f"notional_imb1_change_{mins}m"]=sign*(rawn[1]-ln1) if np.isfinite(rawn[1]) and np.isfinite(ln1) else np.nan
    return out

def assemble_features(ds):
    events=ds.copy()
    events["g_partition"]=events["split"].map(gpart)
    events=events[events.g_partition.notna()].sort_values("onset_ts").reset_index(drop=True)
    events["event_date"]=pd.to_datetime(events.onset_ts,utc=True).dt.floor("D")

    # Needed files: event dates plus previous day for lagged observations near midnight.
    needed=set(events.event_date.tolist())
    early=events[pd.to_datetime(events.onset_ts,utc=True).dt.hour.eq(0) &
                 pd.to_datetime(events.onset_ts,utc=True).dt.minute.lt(16)]
    needed.update((early.event_date-pd.Timedelta(days=1)).tolist())
    needed=sorted(needed)

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        dl=list(ex.map(download_one,needed))
    dl_df=pd.DataFrame(dl,columns=["date","download_ok","bytes","note"])

    rows=[]
    cadence=[]
    for day,g in events.groupby("event_date",sort=True):
        piv=read_day(day)
        # add previous day only when required for early onsets
        if (pd.to_datetime(g.onset_ts,utc=True).dt.hour.eq(0) &
            pd.to_datetime(g.onset_ts,utc=True).dt.minute.lt(16)).any():
            prev=read_day(day-pd.Timedelta(days=1))
            if prev is not None:
                piv=pd.concat([prev,piv]) if piv is not None else prev
                piv=piv[~piv.index.duplicated(keep="last")].sort_index()
        if piv is not None and len(piv)>1:
            diffs=np.diff(piv.index.view("i8"))/1e9
            if len(diffs):
                cadence.extend([float(np.median(diffs)),float(np.percentile(diffs,95))])
        for r in g.itertuples(index=False):
            base={
                "split":r.split,"g_partition":r.g_partition,
                "onset_ts":r.onset_ts,"side":r.side,"cell_id":r.cell_id,
                "exit_reason":r.exit_reason,"label_tp":r.label_tp,
            }
            base.update(event_features(piv,pd.Timestamp(r.onset_ts),r.side))
            rows.append(base)
    return pd.DataFrame(rows),dl_df,cadence

def coverage_table(ev):
    rows=[]
    for p in PARTS:
        g=ev[ev.g_partition==p]
        row={"partition":p,"n":len(g)}
        row["current_snapshot_coverage"]=float(g.signed_depth_imb_1.notna().mean()) if len(g) else 0
        row["all_features_coverage"]=float(g[FEATURES].notna().all(axis=1).mean()) if len(g) else 0
        ages=g.book_snapshot_age_sec[g.signed_depth_imb_1.notna()]
        row["snapshot_age_p50_sec"]=float(ages.median()) if len(ages) else np.nan
        row["snapshot_age_p95_sec"]=float(ages.quantile(.95)) if len(ages) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def tertile_spec(x):
    q=x.dropna().quantile([1/3,2/3])
    return float(q.iloc[0]),float(q.iloc[1])

def bucket(v,q1,q2):
    if not np.isfinite(v): return None
    if v<=q1: return "LOW"
    if v>=q2: return "HIGH"
    return "MID"

def anatomy(ev):
    resolved=ev[ev.exit_reason.isin(["TP","SL"])].copy()
    dev=resolved[resolved.g_partition=="development"]
    bucket_rows=[];sum_rows=[]
    for f in FEATURES:
        q1,q2=tertile_spec(dev[f])
        deltas={}
        ns={}
        for p in PARTS:
            g=resolved[resolved.g_partition==p].copy()
            g["bucket"]=[bucket(v,q1,q2) for v in g[f].to_numpy(float)]
            rates={}
            counts={}
            for b in ["LOW","MID","HIGH"]:
                z=g[g.bucket==b]
                n=len(z);counts[b]=n
                tp=float((z.exit_reason=="TP").mean()) if n else np.nan
                rates[b]=tp
                bucket_rows.append({
                    "feature":f,"partition":p,"bucket":b,
                    "q1_dev":q1,"q2_dev":q2,"n":n,"tp_rate":tp,
                })
            deltas[p]=rates["HIGH"]-rates["LOW"] if np.isfinite(rates["HIGH"]) and np.isfinite(rates["LOW"]) else np.nan
            ns[p]=(counts["LOW"],counts["HIGH"])
        dd=deltas["development"];d25=deltas["validation_2025"];d26=deltas["validation_2026"]
        ndev=ns["development"];n25=ns["validation_2025"];n26=ns["validation_2026"]
        support=(ndev[0]>=150 and ndev[1]>=150 and n25[0]>=75 and n25[1]>=75 and n26[0]>=75 and n26[1]>=75)
        same=(np.isfinite(dd) and np.sign(dd)!=0 and np.sign(d25)==np.sign(dd) and np.sign(d26)==np.sign(dd))
        rep=bool(support and abs(dd)>=.08 and same and abs(d25)>=.04 and abs(d26)>=.04)
        sum_rows.append({
            "feature":f,"q1_dev":q1,"q2_dev":q2,
            "development_delta_tp":dd,
            "validation_2025_delta_tp":d25,
            "validation_2026_delta_tp":d26,
            "development_low_n":ndev[0],"development_high_n":ndev[1],
            "validation_2025_low_n":n25[0],"validation_2025_high_n":n25[1],
            "validation_2026_low_n":n26[0],"validation_2026_high_n":n26[1],
            "classification":"REPLICATED_DIRECTIONAL_MICROSTRUCTURE" if rep else "WEAK_OR_UNSTABLE",
        })
    return pd.DataFrame(bucket_rows),pd.DataFrame(sum_rows)

def main():
    raw,a=s7d.prepare()
    ds=s7d.build_dataset(raw,a)

    ev,dl,cadence=assemble_features(ds)
    cover=coverage_table(ev)
    cover.to_csv(OUT_COVER,index=False)
    ev.to_csv(OUT_EVENTS,index=False)

    source_pass=bool((cover.current_snapshot_coverage>=.95).all() and (cover.all_features_coverage>=.95).all())
    if source_pass:
        buckets,summary=anatomy(ev)
    else:
        buckets=pd.DataFrame()
        summary=pd.DataFrame()
    buckets.to_csv(OUT_BUCKETS,index=False)
    summary.to_csv(OUT_SUMMARY,index=False)

    reps=summary[summary.classification=="REPLICATED_DIRECTIONAL_MICROSTRUCTURE"] if len(summary) else pd.DataFrame()
    if not source_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7G_B_SOURCE_COVERAGE_FAIL"
    elif len(reps):
        status="SOL_INDICATOR_RELATIONSHIP_S7G_B_COMPLETED_WITH_REPLICATED_FEATURES"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7G_B_COMPLETED_NO_REPLICATED_FEATURE"
    OUT_STATUS.write_text(status+"\n")

    payload={
        "status":status,"source_pass":source_pass,
        "event_rows":len(ev),
        "coverage":cover.to_dict(orient="records"),
        "download_success_days":int(dl.download_ok.sum()),"download_needed_days":len(dl),
        "cadence_daily_summary_seconds":{
            "median_of_daily_stats":float(np.median(cadence)) if cadence else np.nan,
            "p95_of_daily_stats":float(np.percentile(cadence,95)) if cadence else np.nan,
        },
        "replicated_features":reps.to_dict(orient="records") if len(reps) else [],
        "summary":summary.to_dict(orient="records") if len(summary) else [],
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")

    def pp(x):
        return "-" if x is None or not np.isfinite(x) else f"{100*x:.1f}%"
    lines=["# SOL Indicator Relationship Discovery — Stage 7G-B Result","",
           "**Historical Binance Vision SOLUSDT bookDepth; backward-only causal alignment.**","",
           "## Source/event coverage","",
           "| Partition | Events | Current snapshot | All 17 features | age p50 | age p95 |",
           "|---|---:|---:|---:|---:|---:|"]
    for r in cover.itertuples(index=False):
        lines.append(
            f"| {r.partition} | {r.n} | {pp(r.current_snapshot_coverage)} | {pp(r.all_features_coverage)} | "
            f"{r.snapshot_age_p50_sec:.1f}s | {r.snapshot_age_p95_sec:.1f}s |"
        )
    lines += ["",f"Source gate: **{'PASS' if source_pass else 'FAIL'}**.",""]

    if source_pass:
        lines += ["## Frozen single-feature replication atlas","",
                  "| Feature | DEV ΔTP | 2025 ΔTP | 2026 ΔTP | Class |",
                  "|---|---:|---:|---:|---|"]
        for r in summary.sort_values("development_delta_tp",key=lambda s:s.abs(),ascending=False).itertuples(index=False):
            lines.append(
                f"| {r.feature} | {pp(r.development_delta_tp)} | {pp(r.validation_2025_delta_tp)} | "
                f"{pp(r.validation_2026_delta_tp)} | {r.classification} |"
            )
        lines += ["","## Replicated features",""]
        if len(reps):
            for r in reps.itertuples(index=False):
                lines.append(
                    f"- **{r.feature}**: ΔTP DEV {pp(r.development_delta_tp)}, "
                    f"2025 {pp(r.validation_2025_delta_tp)}, 2026 {pp(r.validation_2026_delta_tp)}."
                )
        else:
            lines.append("- none")
    else:
        lines += ["Outcome-bearing anatomy was not run because the preregistered source coverage gate failed."]

    lines += ["",
              "BookDepth here is cumulative depth/notional in percentage bands, not raw per-price L2. Therefore these results do not prove exact wall placement, spread behavior, sweep, or absorption.",
              "",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
