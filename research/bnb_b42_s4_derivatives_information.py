#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, math, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B42_S4_DERIVATIVES_INFO"
SYMBOL="BNBUSDT"
BASE="https://data.binance.vision/data/futures/um"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2026-08-26T00:00:00Z")
FETCH_START=pd.Timestamp("2021-12-20T00:00:00Z")
PARENT_SIG="ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd"

def verify():
    txt=(ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Freeze.txt").read_text()
    if f"S1_SIGNATURE_SHA256={PARENT_SIG}" not in txt: raise RuntimeError("parent mismatch")

def get_zip(url, timeout=45):
    last=None
    for k in range(4):
        try:
            r=requests.get(url,timeout=timeout,headers={"User-Agent":"bababot-b42-s4/1.0"})
            if r.status_code==404:return None
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                ns=[n for n in z.namelist() if n.lower().endswith(".csv")]
                if not ns:return None
                return z.read(ns[0])
        except Exception as e:
            last=e; time.sleep(1.5**k)
    raise RuntimeError(f"fetch failed {url}: {last}")

def daily_dates():
    return pd.date_range(FETCH_START.floor("D"),END.floor("D"),freq="D",tz="UTC")

def month_starts():
    return pd.date_range(pd.Timestamp(FETCH_START.year,FETCH_START.month,1,tz="UTC"),
                         pd.Timestamp(END.year,END.month,1,tz="UTC"),freq="MS")

def fetch_metrics_day(d):
    ds=d.strftime("%Y-%m-%d")
    url=f"{BASE}/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{ds}.zip"
    b=get_zip(url)
    if b is None:return None
    try:
        q=pd.read_csv(io.BytesIO(b))
    except Exception:
        q=pd.read_csv(io.BytesIO(b),header=None)
    q["_source_date"]=ds
    return q

def load_metrics():
    frames=[]; missing=[]
    dates=list(daily_dates())
    with ThreadPoolExecutor(max_workers=24) as ex:
        fut={ex.submit(fetch_metrics_day,d):d for d in dates}
        for f in as_completed(fut):
            q=f.result()
            if q is None:missing.append(fut[f].strftime("%Y-%m-%d"))
            else:frames.append(q)
    if not frames:return pd.DataFrame(),{"requested":len(dates),"found":0,"missing":len(missing)}
    x=pd.concat(frames,ignore_index=True,sort=False)
    return x,{"requested":len(dates),"found":len(frames),"missing":len(missing),"missing_sample":sorted(missing)[:20]}

def fetch_month(kind,tf,m):
    ym=m.strftime("%Y-%m")
    if kind=="premiumIndexKlines":
        url=f"{BASE}/monthly/{kind}/{SYMBOL}/{tf}/{SYMBOL}-{tf}-{ym}.zip"
    else:
        url=f"{BASE}/monthly/{kind}/{SYMBOL}/{SYMBOL}-{kind}-{ym}.zip"
    return ym,get_zip(url)

def load_premium():
    rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fut=[ex.submit(fetch_month,"premiumIndexKlines","15m",m) for m in month_starts()]
        for f in as_completed(fut):
            ym,b=f.result()
            if b is None:continue
            q=pd.read_csv(io.BytesIO(b),header=None)
            if q.shape[1]<5:continue
            ts=pd.to_numeric(q.iloc[:,0],errors="coerce")
            ts=np.where(ts>100_000_000_000_000,ts/1000,ts)
            z=pd.DataFrame({"open_ts":pd.to_datetime(ts,unit="ms",utc=True,errors="coerce"),
                            "premium_close":pd.to_numeric(q.iloc[:,4],errors="coerce")})
            rows.append(z)
    if not rows:return pd.DataFrame()
    p=pd.concat(rows,ignore_index=True).dropna().drop_duplicates("open_ts").sort_values("open_ts")
    p["ts"]=p.open_ts+pd.Timedelta(minutes=15)
    p=p[(p.ts>=FETCH_START)&(p.ts<=END+pd.Timedelta(minutes=15))].copy()
    s=p.set_index("ts").premium_close
    refmean=s.rolling("7D",closed="left",min_periods=192).mean()
    refstd=s.rolling("7D",closed="left",min_periods=192).std(ddof=0)
    p=p.set_index("ts")
    p["premium_z_7d"]=(p.premium_close-refmean)/refstd
    p["premium_change_60m"]=p.premium_close-p.premium_close.shift(4)
    return p.reset_index()

def load_funding():
    rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fut=[ex.submit(fetch_month,"fundingRate","",m) for m in month_starts()]
        for f in as_completed(fut):
            ym,b=f.result()
            if b is None:continue
            q=pd.read_csv(io.BytesIO(b))
            # normalize flexible official archive headers
            q.columns=[str(c).strip().lower() for c in q.columns]
            tcol="calc_time" if "calc_time" in q.columns else ("fundingtime" if "fundingtime" in q.columns else None)
            rcol="last_funding_rate" if "last_funding_rate" in q.columns else ("fundingrate" if "fundingrate" in q.columns else None)
            if tcol is None or rcol is None:
                continue
            vals=pd.to_numeric(q[tcol],errors="coerce")
            med=vals.dropna().median() if vals.notna().any() else np.nan
            unit="us" if np.isfinite(med) and med>1e14 else "ms"
            rows.append(pd.DataFrame({"ts":pd.to_datetime(vals,unit=unit,utc=True,errors="coerce"),
                                      "latest_funding":pd.to_numeric(q[rcol],errors="coerce")}))
    if not rows:return pd.DataFrame()
    return pd.concat(rows,ignore_index=True).dropna().drop_duplicates("ts").sort_values("ts")

def normalize_metrics(x):
    if x.empty:return x,{}
    schema=list(map(str,x.columns))
    lower={str(c).strip().lower():c for c in x.columns}
    tcol=next((lower[k] for k in lower if k in ("create_time","timestamp","time")),None)
    if tcol is None:
        tcol=next((lower[k] for k in lower if "time" in k),None)
    if tcol is None:raise RuntimeError(f"metrics timestamp column missing {schema}")
    tsraw=x[tcol]
    num=pd.to_numeric(tsraw,errors="coerce")
    if num.notna().mean()>.95:
        vals=num.to_numpy()
        vals=np.where(vals>100_000_000_000_000,vals/1000,vals)
        ts=pd.to_datetime(vals,unit="ms",utc=True,errors="coerce")
    else:
        ts=pd.to_datetime(tsraw,utc=True,errors="coerce")
    m=pd.DataFrame({"ts":ts})
    wanted=[
      "sum_open_interest","sum_open_interest_value",
      "count_toptrader_long_short_ratio","sum_toptrader_long_short_ratio",
      "count_long_short_ratio","sum_taker_long_short_vol_ratio"
    ]
    found={}
    for w in wanted:
        c=lower.get(w)
        if c is not None:
            m[w]=pd.to_numeric(x[c],errors="coerce"); found[w]=str(c)
    m=m.dropna(subset=["ts"]).drop_duplicates("ts",keep="last").sort_values("ts")
    return m,{"raw_schema":schema,"mapped":found,"rows":len(m),"first":str(m.ts.min()),"last":str(m.ts.max())}

def metric_features(m):
    q=m.set_index("ts").copy()
    if "sum_open_interest" in q:
        q["oi_level_log"]=np.log(q.sum_open_interest.where(q.sum_open_interest>0))
        for n,name in [(3,"15m"),(12,"60m"),(48,"240m")]:
            q[f"oi_change_{name}"]=q.sum_open_interest/q.sum_open_interest.shift(n)-1
    if "sum_open_interest_value" in q:
        for n,name in [(12,"60m"),(48,"240m")]:
            q[f"oi_value_change_{name}"]=q.sum_open_interest_value/q.sum_open_interest_value.shift(n)-1
    for c in ["count_long_short_ratio","count_toptrader_long_short_ratio","sum_toptrader_long_short_ratio","sum_taker_long_short_vol_ratio"]:
        if c in q:
            q[f"log_{c}"]=np.log(q[c].where(q[c]>0))
    if "sum_taker_long_short_vol_ratio" in q:
        q["taker_change_60m"]=np.log(q.sum_taker_long_short_vol_ratio.where(q.sum_taker_long_short_vol_ratio>0))-np.log(q.sum_taker_long_short_vol_ratio.shift(12).where(q.sum_taker_long_short_vol_ratio.shift(12)>0))
    return q.reset_index()

def align_backward(left,right,max_age=None):
    a=left.sort_values("decision_ts").copy()
    r=right.sort_values("ts").copy().rename(columns={"ts":"_source_ts"})
    a["decision_ts"]=pd.to_datetime(a["decision_ts"],utc=True).astype("datetime64[ns, UTC]")
    r["_source_ts"]=pd.to_datetime(r["_source_ts"],utc=True).astype("datetime64[ns, UTC]")
    z=pd.merge_asof(a,r,left_on="decision_ts",right_on="_source_ts",direction="backward")
    if max_age is not None:
        age=(z.decision_ts-z._source_ts)
        bad=age>max_age
        cols=[c for c in r.columns if c!="_source_ts"]
        z.loc[bad,cols]=np.nan
    return z.drop(columns=["_source_ts"])

def auc_rank(y,x):
    ok=np.isfinite(x)
    yy=np.asarray(y)[ok].astype(int); xx=np.asarray(x)[ok].astype(float)
    n1=int(yy.sum()); n0=len(yy)-n1
    if n1==0 or n0==0:return np.nan
    ranks=pd.Series(xx).rank(method="average").to_numpy()
    return float((ranks[yy==1].sum()-n1*(n1+1)/2)/(n1*n0))

def main():
    verify()
    L=pd.read_csv(ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Ledger.csv.gz",
                  compression="gzip",parse_dates=["decision_ts","decision_day"])
    L=L[(L.decision_ts>=START)&(L.decision_ts<=END)].copy()
    L["y"]=L.outcome.eq("WIN").astype(int)
    L["dir"]=np.where(L.side.eq("LONG"),1.0,-1.0)

    rawm,mdiag=load_metrics()
    m,mschema=normalize_metrics(rawm)
    mf=metric_features(m) if not m.empty else pd.DataFrame()
    p=load_premium()
    f=load_funding()

    # one row per timestamp first, then duplicate to long/short via merge against L
    base=L[["decision_ts","decision_day","year","side","dir","y","outcome"]].copy()
    z=align_backward(base,mf,pd.Timedelta(minutes=20)) if not mf.empty else base.copy()
    if not p.empty:z=align_backward(z,p,pd.Timedelta(minutes=30))
    if not f.empty:
        z=align_backward(z,f,pd.Timedelta(hours=24))

    # merge_asof ts naming can collide; rebuild source ages not used in tests.
    # Directional transforms
    maps={
      "log_count_long_short_ratio":"directional_global_account_log_ratio",
      "log_count_toptrader_long_short_ratio":"directional_top_account_log_ratio",
      "log_sum_toptrader_long_short_ratio":"directional_top_position_log_ratio",
      "log_sum_taker_long_short_vol_ratio":"directional_taker_log_ratio",
    }
    for src,dst in maps.items():
        if src in z:z[dst]=z[src]*z.dir
    if "premium_close" in z:z["directional_premium"]=z.premium_close*z.dir
    if "premium_z_7d" in z:z["directional_premium_z_7d"]=z.premium_z_7d*z.dir
    if "premium_change_60m" in z:z["directional_premium_change_60m"]=z.premium_change_60m*z.dir
    if "latest_funding" in z:z["directional_funding"]=z.latest_funding*z.dir

    candidate=[
      "oi_level_log","oi_change_15m","oi_change_60m","oi_change_240m",
      "oi_value_change_60m","oi_value_change_240m",
      "directional_global_account_log_ratio","directional_top_account_log_ratio",
      "directional_top_position_log_ratio","directional_taker_log_ratio","taker_change_60m",
      "premium_close","premium_z_7d","premium_change_60m",
      "directional_premium","directional_premium_z_7d","directional_premium_change_60m",
      "latest_funding","directional_funding"
    ]
    candidate=[c for c in candidate if c in z.columns]

    cov=[]
    total_dev=int((z.year<=2024).sum()); total_ref=int((z.year>=2025).sum())
    eligible=[]
    for c in candidate:
        nd=int(z.loc[z.year<=2024,c].notna().sum()); nr=int(z.loc[z.year>=2025,c].notna().sum())
        cd=nd/total_dev; cr=nr/total_ref
        ok=cd>=.90 and cr>=.90
        cov.append({"feature":c,"dev_n":nd,"ref_n":nr,"dev_coverage":cd,"ref_coverage":cr,"eligible":ok})
        if ok:eligible.append(c)
    C=pd.DataFrame(cov)

    rows=[]; byyear=[]
    for c in eligible:
        dev=z[(z.year<=2024)&z[c].notna()]
        ref=z[(z.year>=2025)&z[c].notna()]
        rawdev=auc_rank(dev.y,dev[c])
        orient=1.0 if rawdev>=.5 else -1.0
        adev=auc_rank(dev.y,dev[c]*orient); aref=auc_rank(ref.y,ref[c]*orient)
        yrs=[]
        for y in [2022,2023,2024,2025,2026]:
            q=z[(z.year==y)&z[c].notna()]
            ay=auc_rank(q.y,q[c]*orient)
            yrs.append(ay)
            byyear.append({"feature":c,"year":y,"n":len(q),"auc":ay})
        stable=int(sum(np.isfinite(a) and a>=.53 for a in yrs))
        nominated=bool(len(dev)>=50000 and len(ref)>=25000 and adev>=.58 and aref>=.55 and stable>=4 and aref>=.50)
        rows.append({
          "feature":c,"orientation":int(orient),"dev_n":len(dev),"ref_n":len(ref),
          "dev_auc":adev,"ref_auc":aref,"years_auc_ge53":stable,
          "dev_win_median":float(dev.loc[dev.y==1,c].median()),"dev_nonwin_median":float(dev.loc[dev.y==0,c].median()),
          "ref_win_median":float(ref.loc[ref.y==1,c].median()),"ref_nonwin_median":float(ref.loc[ref.y==0,c].median()),
          "nominated":nominated
        })
    R=pd.DataFrame(rows).sort_values(["nominated","ref_auc","dev_auc"],ascending=[False,False,False]) if rows else pd.DataFrame()
    Y=pd.DataFrame(byyear)
    status=("BNB_B42_S4_DERIVATIVES_INFORMATION_READY" if len(R) and R.nominated.any()
            else "BNB_B42_S4_NO_DERIVATIVES_DISCRIMINATORY_EDGE" if len(eligible)
            else "BNB_B42_S4_DERIVATIVES_HISTORY_INSUFFICIENT")

    sig=sha256(json.dumps({
      "parent":PARENT_SIG,"sources":["daily_metrics","monthly_premiumIndexKlines_15m","monthly_fundingRate"],
      "coverage_gate":.90,"auc_gate":{"dev":.58,"ref":.55,"years_ge53":4},
      "funding_max_age_h":24,"metrics_max_age_min":20,"premium_max_age_min":30
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    C.to_csv(ROOT/f"{PFX}_Coverage.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_FeatureAUC.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    z[[c for c in ["decision_ts","year","side","y","outcome"]+candidate if c in z.columns]].to_csv(ROOT/f"{PFX}_Aligned.csv.gz",index=False,compression="gzip")
    schema={"metrics_download":mdiag,"metrics_schema":mschema,
            "premium_rows":len(p),"premium_first":str(p.ts.min()) if len(p) else None,"premium_last":str(p.ts.max()) if len(p) else None,
            "funding_rows":len(f),"funding_first":str(f.ts.min()) if len(f) else None,"funding_last":str(f.ts.max()) if len(f) else None}
    (ROOT/f"{PFX}_Schema.json").write_text(json.dumps(schema,indent=2)+"\n")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n")
    (ROOT/f"{PFX}_Freeze.txt").write_text(f"S4_SIGNATURE_SHA256={sig}\nPARENT_S1_SIGNATURE_SHA256={PARENT_SIG}\n")

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.2f}%"
    lines=["# BNB B42-S4 — Historical Derivatives Information Result","",f"**Status: {status}**","",f"Signature: `{sig}`","",
           "## Archive audit","",f"- Metrics archive files found: **{mdiag.get('found',0)}/{mdiag.get('requested',0)}**.",
           f"- Metrics rows: **{mschema.get('rows',0):,}**; first **{mschema.get('first')}**; last **{mschema.get('last')}**.",
           f"- Metrics mapped fields: `{json.dumps(mschema.get('mapped',{}),sort_keys=True)}`.",
           f"- Premium rows: **{len(p):,}**.",
           f"- Funding rows: **{len(f):,}**.","","## Coverage","",
           "| Feature | DEV N | REF N | DEV cov | REF cov | Eligible |","|---|---:|---:|---:|---:|---|"]
    for r in C.itertuples(index=False):
        lines.append(f"| {r.feature} | {r.dev_n} | {r.ref_n} | {pct(r.dev_coverage)} | {pct(r.ref_coverage)} | {'YES' if r.eligible else 'NO'} |")
    lines += ["","## Discrimination","","| Feature | Orient | DEV AUC | REF AUC | Years >=.53 | Nominate |",
              "|---|---:|---:|---:|---:|---|"]
    for r in R.itertuples(index=False):
        lines.append(f"| {r.feature} | {r.orientation:+d} | **{r.dev_auc:.3f}** | **{r.ref_auc:.3f}** | {r.years_auc_ge53} | {'YES' if r.nominated else 'NO'} |")
    lines+=["","## Decision",f"**{status}**","",
            ("At least one derivatives feature carries robust incremental discriminatory information and may advance to B42-S5 combined selection."
             if status.endswith("INFORMATION_READY") else
             "No S4 derivatives feature is eligible for promotion under the frozen gates; do not hyperopt these same features to force S5.")]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
