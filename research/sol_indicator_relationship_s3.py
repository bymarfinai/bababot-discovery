#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 3.

Stage 3A: single-indicator relationship discovery.
Stage 3B: completed 5m impulse -> future expansion mapping.
Research-only. No live trading code is touched.
"""
from __future__ import annotations
import io, json, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3_Result.md"
OUT_JSON = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3_Result.json"
OUT_BUCKETS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3A_BUCKETS.csv"
OUT_FEATURES = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3A_FEATURE_SUMMARY.csv"
OUT_COVERAGE = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3A_COVERAGE.csv"
OUT_IMPULSE = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3B_IMPULSE_EXPANSION.csv"
OUT_STATUS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S3_Status.txt"

SYMBOL = "SOLUSDT"
BASE = "https://data.binance.vision/data/futures/um"
FAPI = "https://fapi.binance.com"
START = pd.Timestamp("2022-12-20T00:00:00Z")
SCORE_START = pd.Timestamp("2023-01-01T00:00:00Z")
END = pd.Timestamp("2026-09-26T00:00:00Z")
DEV_END = pd.Timestamp("2025-01-01T00:00:00Z")
VAL25_END = pd.Timestamp("2026-01-01T00:00:00Z")
BAR = pd.Timedelta(minutes=5)
HORIZONS_H = (1, 2, 4, 8)
IMPULSE_THRESH = (0.005, 0.0075, 0.010, 0.015, 0.020, 0.030)
EXP_THRESH = (0.005, 0.010, 0.020, 0.030)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bababot-sol-s3/1.0"})

FEATURES = [
    "quotevol_15m","quotevol_ratio_1h","quotevol_z_24h","trades_ratio_1h",
    "taker_buy_ratio_15m","taker_imb_15m","taker_imb_1h","taker_imb_change_1h",
    "loc_24h","dist_high_24h","dist_low_24h","breakout_up_24h","breakout_down_24h",
    "oi_value","oi_chg_15m","oi_chg_1h","oi_chg_4h",
    "funding_rate","funding_z_30","funding_change",
]
ZERO_MASS = {"breakout_up_24h","breakout_down_24h"}

def partition(ts):
    if ts < SCORE_START: return None
    if ts < DEV_END: return "development"
    if ts < VAL25_END: return "validation_2025"
    if ts < END: return "validation_2026"
    return None

def get_bytes(url, timeout=60):
    last = None
    for attempt in range(4):
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 404: return None
            r.raise_for_status()
            return r.content
        except Exception as exc:
            last = exc
            time.sleep(0.5*(attempt+1))
    raise RuntimeError(f"download failed {url}: {last}")

def read_zip_csv(url, header="infer"):
    data = get_bytes(url)
    if data is None: return None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names: return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh, header=header)

def fetch_kline_month(url):
    df = read_zip_csv(url, header=None)
    if df is None or df.empty: return None
    df = df.iloc[:, :12].copy()
    df.columns = ["open_time","open","high","low","close","volume","close_time",
                  "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
    return df

def load_klines():
    urls = []
    cur = pd.Timestamp(START.year, START.month, 1, tz="UTC")
    cutoff = pd.Timestamp("2026-09-01T00:00:00Z")
    while cur < cutoff:
        ym = cur.strftime("%Y-%m")
        urls.append(f"{BASE}/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    frames = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs = [ex.submit(fetch_kline_month,u) for u in urls]
        for f in as_completed(fs):
            z=f.result()
            if z is not None and len(z): frames.append(z)
    cur_ms = int(cutoff.timestamp()*1000)
    end_ms = int(END.timestamp()*1000)
    rows=[]
    while cur_ms < end_ms:
        p={"symbol":SYMBOL,"interval":"5m","startTime":cur_ms,"endTime":end_ms-1,"limit":1500}
        r=SESSION.get(f"{FAPI}/fapi/v1/klines",params=p,timeout=30);r.raise_for_status();z=r.json()
        if not z: break
        rows.extend(z)
        nxt=int(z[-1][0])+300000
        if nxt<=cur_ms: break
        cur_ms=nxt
        time.sleep(.03)
    if rows:
        frames.append(pd.DataFrame(rows,columns=["open_time","open","high","low","close","volume","close_time",
                                                 "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]))
    if not frames: raise RuntimeError("no kline data")
    x=pd.concat(frames,ignore_index=True)
    ot=pd.to_numeric(x.open_time,errors="coerce")
    ot=np.where(ot>1e14,ot/1000.,ot)
    x["ts"]=pd.to_datetime(ot,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close","volume","quote_volume","trades","taker_buy_quote"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna(subset=["ts","open","high","low","close","quote_volume","trades","taker_buy_quote"])
    x=x.drop_duplicates("ts").sort_values("ts")
    return x[(x.ts>=START)&(x.ts<END)].reset_index(drop=True)

def fetch_metric_day(d):
    ds=d.strftime("%Y-%m-%d")
    url=f"{BASE}/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{ds}.zip"
    try:
        df=read_zip_csv(url)
        if df is None or df.empty: return None
        df.columns=[str(c).strip().lower() for c in df.columns]
        tc=next((c for c in ["create_time","timestamp","time"] if c in df.columns),None)
        oc="sum_open_interest_value" if "sum_open_interest_value" in df.columns else None
        if tc is None or oc is None: return None
        raw=df[tc]
        if pd.api.types.is_numeric_dtype(raw):
            v=pd.to_numeric(raw,errors="coerce")
            unit="us" if v.dropna().median()>1e14 else "ms"
            ts=pd.to_datetime(v,unit=unit,utc=True,errors="coerce")
        else:
            ts=pd.to_datetime(raw,utc=True,errors="coerce")
        return pd.DataFrame({"ts":ts,"oi_value":pd.to_numeric(df[oc],errors="coerce")}).dropna()
    except Exception:
        return None

def load_metrics():
    days=list(pd.date_range(START.normalize(),END.normalize()-pd.Timedelta(days=1),freq="D",tz="UTC"))
    frames=[]
    with ThreadPoolExecutor(max_workers=40) as ex:
        fs=[ex.submit(fetch_metric_day,d) for d in days]
        for f in as_completed(fs):
            z=f.result()
            if z is not None and len(z): frames.append(z)
    if not frames: return pd.DataFrame(columns=["ts","oi_value"])
    return pd.concat(frames,ignore_index=True).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)

def load_funding():
    rows=[];cur=int(START.timestamp()*1000);end_ms=int(END.timestamp()*1000)
    while cur<end_ms:
        p={"symbol":SYMBOL,"startTime":cur,"endTime":end_ms-1,"limit":1000}
        r=SESSION.get(f"{FAPI}/fapi/v1/fundingRate",params=p,timeout=30);r.raise_for_status();z=r.json()
        if not z: break
        rows.extend(z);nxt=int(z[-1]["fundingTime"])+1
        if nxt<=cur: break
        cur=nxt;time.sleep(.03)
    if not rows: return pd.DataFrame(columns=["ts","funding_rate","funding_z_30","funding_change"])
    f=pd.DataFrame(rows)
    f["ts"]=pd.to_datetime(pd.to_numeric(f.fundingTime),unit="ms",utc=True)
    f["funding_rate"]=pd.to_numeric(f.fundingRate,errors="coerce")
    f=f[["ts","funding_rate"]].dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    pm=f.funding_rate.shift(1).rolling(30,min_periods=10).mean()
    ps=f.funding_rate.shift(1).rolling(30,min_periods=10).std()
    f["funding_z_30"]=(f.funding_rate-pm)/ps.replace(0,np.nan)
    f["funding_change"]=f.funding_rate.diff()
    return f

def build_15m(raw):
    z=raw.set_index("ts")
    cnt=z.close.resample("15min",label="right",closed="left").count()
    a=z.resample("15min",label="right",closed="left").agg(
        open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),
        quotevol_15m=("quote_volume","sum"),trades_15m=("trades","sum"),
        taker_buy_quote_15m=("taker_buy_quote","sum"))
    a=a[cnt==3].dropna().copy()
    a["decision_time"]=a.index
    a["entry_price"]=z.open.reindex(a.index)
    a=a.dropna(subset=["entry_price"])
    q=a.quotevol_15m;tr=a.trades_15m
    a["quotevol_ratio_1h"]=q/q.shift(1).rolling(4,min_periods=4).mean().replace(0,np.nan)
    a["trades_ratio_1h"]=tr/tr.shift(1).rolling(4,min_periods=4).mean().replace(0,np.nan)
    m=q.shift(1).rolling(96,min_periods=72).mean();s=q.shift(1).rolling(96,min_periods=72).std()
    a["quotevol_z_24h"]=(q-m)/s.replace(0,np.nan)
    a["taker_buy_ratio_15m"]=a.taker_buy_quote_15m/q.replace(0,np.nan)
    a["taker_imb_15m"]=2*a.taker_buy_ratio_15m-1
    ptb=a.taker_buy_quote_15m.shift(1).rolling(4,min_periods=4).sum()
    pq=q.shift(1).rolling(4,min_periods=4).sum()
    a["taker_imb_1h"]=2*ptb/pq.replace(0,np.nan)-1
    a["taker_imb_change_1h"]=a.taker_imb_15m-a.taker_imb_1h
    ph=a.high.shift(1).rolling(96,min_periods=96).max()
    pl=a.low.shift(1).rolling(96,min_periods=96).min()
    rg=(ph-pl).replace(0,np.nan)
    a["loc_24h"]=(a.close-pl)/rg
    a["dist_high_24h"]=a.close/ph-1
    a["dist_low_24h"]=a.close/pl-1
    a["breakout_up_24h"]=np.maximum(0,a.close/ph-1)
    a["breakout_down_24h"]=np.maximum(0,pl/a.close-1)
    return a.reset_index(drop=True)

def asof_values(times,src,col,tol=pd.Timedelta(minutes=10)):
    if src.empty: return np.full(len(times),np.nan),np.full(len(times),np.nan)
    left=pd.DataFrame({"t":pd.to_datetime(times,utc=True)}).sort_values("t")
    right=src[["ts",col]].dropna().sort_values("ts").rename(columns={"ts":"src_ts"})
    m=pd.merge_asof(left,right,left_on="t",right_on="src_ts",direction="backward",tolerance=tol)
    age=(m.t-m.src_ts).dt.total_seconds()/60.
    return m[col].to_numpy(float),age.to_numpy(float)

def add_derivatives(a,metrics,funding):
    t=pd.DatetimeIndex(a.decision_time)
    cur,age=asof_values(t,metrics,"oi_value")
    a["oi_value"]=cur;a["oi_age_min"]=age
    for nm,d in [("15m",pd.Timedelta(minutes=15)),("1h",pd.Timedelta(hours=1)),("4h",pd.Timedelta(hours=4))]:
        prev,_=asof_values(t-d,metrics,"oi_value")
        a[f"oi_chg_{nm}"]=np.where((cur>0)&(prev>0),np.log(cur)-np.log(prev),np.nan)
    if funding.empty:
        for c in ["funding_rate","funding_z_30","funding_change"]: a[c]=np.nan
        return a
    left=pd.DataFrame({"t":t}).sort_values("t")
    right=funding.sort_values("ts").rename(columns={"ts":"src_ts"})
    m=pd.merge_asof(left,right,left_on="t",right_on="src_ts",direction="backward")
    for c in ["funding_rate","funding_z_30","funding_change"]: a[c]=m[c].to_numpy(float)
    return a

def exact_future(raw,pos,h):
    n=h*12
    if pos is None or pos<0 or pos+n>len(raw): return None
    w=raw.iloc[pos:pos+n]
    if len(w)!=n or w.ts.iloc[0]+BAR*(n-1)!=w.ts.iloc[-1]: return None
    if not bool((w.ts.diff().dropna()==BAR).all()): return None
    return w

def first_touch(w,e):
    up=e*1.01;dn=e*.99;ui=di=None
    for j,r in enumerate(w.itertuples(index=False)):
        if ui is None and float(r.high)>=up: ui=j
        if di is None and float(r.low)<=dn: di=j
    if ui is None and di is None:return "NONE"
    if ui is not None and di is not None:
        if ui==di:return "AMBIGUOUS"
        return "LONG" if ui<di else "SHORT"
    return "LONG" if ui is not None else "SHORT"

def add_targets(a,raw):
    pm={t:i for i,t in enumerate(raw.ts)}
    lab=[];ret=[];mu=[];md=[];ok=[]
    for r in a.itertuples(index=False):
        p=pm.get(r.decision_time);w=exact_future(raw,p,4)
        if w is None:
            lab.append(None);ret.append(np.nan);mu.append(np.nan);md.append(np.nan);ok.append(False);continue
        e=float(r.entry_price)
        lab.append(first_touch(w,e));ret.append(float(w.close.iloc[-1]/e-1))
        mu.append(float(w.high.max()/e-1));md.append(float(w.low.min()/e-1));ok.append(True)
    a["target_1pct_4h"]=lab;a["fwd_ret_4h"]=ret;a["max_up_4h"]=mu;a["max_down_4h"]=md
    a["future_complete_4h"]=ok
    a["partition"]=[partition(t) for t in a.decision_time]
    return a

def frozen_cuts(a,feat):
    s=pd.to_numeric(a.loc[a.partition=="development",feat],errors="coerce").dropna()
    if s.empty:return {"mode":"empty","cuts":[]}
    if feat in ZERO_MASS:
        nz=s[s>0]
        if len(nz)<30:return {"mode":"zero_mass","cuts":[]}
        return {"mode":"zero_mass","cuts":[float(x) for x in nz.quantile([1/3,2/3])]}
    return {"mode":"quintile","cuts":[float(x) for x in s.quantile([.2,.4,.6,.8])]}

def bucket(v,spec):
    if pd.isna(v):return None
    c=spec["cuts"]
    if spec["mode"]=="zero_mass":
        if float(v)<=0:return "ZERO"
        if len(c)<2:return "POS"
        if v<=c[0]:return "LOW"
        if v<=c[1]:return "MID"
        return "HIGH"
    if spec["mode"]=="quintile":
        return f"Q{int(np.searchsorted(np.asarray(c,float),float(v),side='right'))+1}"
    return None

def bord(b):
    if b is None:return 99
    if b.startswith("Q"):return int(b[1:])
    return {"ZERO":0,"LOW":1,"MID":2,"HIGH":3,"POS":1}.get(b,99)

def vrate(s,v):
    return float((s==v).mean()) if len(s) else np.nan

def analyze_feature(a,feat,spec):
    z=a[["decision_time","partition","target_1pct_4h","fwd_ret_4h","max_up_4h","max_down_4h",feat]].copy()
    z=z[z.partition.notna()&z.target_1pct_4h.notna()]
    z["bucket"]=[bucket(v,spec) for v in z[feat]]
    z=z[z.bucket.notna()]
    rows=[]
    for p in ["development","validation_2025","validation_2026"]:
        q=z[z.partition==p]
        for b in sorted(q.bucket.unique(),key=bord):
            g=q[q.bucket==b]
            rows.append({"feature":feat,"partition":p,"bucket":b,"bucket_order":bord(b),"n":len(g),
                         "long_rate":vrate(g.target_1pct_4h,"LONG"),"short_rate":vrate(g.target_1pct_4h,"SHORT"),
                         "none_rate":vrate(g.target_1pct_4h,"NONE"),"ambiguous_rate":vrate(g.target_1pct_4h,"AMBIGUOUS"),
                         "median_fwd_ret_4h":float(g.fwd_ret_4h.median()),"median_max_up_4h":float(g.max_up_4h.median()),
                         "median_max_down_4h":float(g.max_down_4h.median())})
    return rows

def summarize_feature(bdf,feat):
    z=bdf[bdf.feature==feat];o={"feature":feat};deltas={};adequate=True;signs=[]
    for p in ["development","validation_2025","validation_2026"]:
        q=z[z.partition==p].sort_values("bucket_order")
        if q.empty:
            d=np.nan;lo_n=hi_n=0;adequate=False
        else:
            lo=q.iloc[0];hi=q.iloc[-1]
            d=float((hi.long_rate-hi.short_rate)-(lo.long_rate-lo.short_rate))
            lo_n=int(lo.n);hi_n=int(hi.n);need=200 if p=="development" else 100
            adequate=adequate and lo_n>=need and hi_n>=need
        deltas[p]=d;signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
        o[f"{p}_delta_D"]=d;o[f"{p}_low_n"]=lo_n;o[f"{p}_high_n"]=hi_n
    dd,d25,d26=deltas["development"],deltas["validation_2025"],deltas["validation_2026"]
    if adequate and np.isfinite(dd) and abs(dd)>=.05 and np.sign(dd)!=0 and np.sign(d25)==np.sign(dd) and np.sign(d26)==np.sign(dd) and abs(d25)>=.02 and abs(d26)>=.02:
        cls="REPLICATED_DIRECTIONAL"
    elif all(np.isfinite(v) and abs(v)<.02 for v in [dd,d25,d26]):
        cls="NON_INFORMATIVE"
    else: cls="UNSTABLE_OR_WEAK"
    o["classification"]=cls;o["same_sign_all"]=bool(signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0])
    return o

def coverage_row(a,feat):
    z=a[a.partition.notna()];q=z[z[feat].notna()]
    return {"feature":feat,"rows_total":len(z),"rows_available":len(q),"coverage":len(q)/len(z) if len(z) else np.nan,
            "first_time":None if q.empty else str(q.decision_time.min()),"last_time":None if q.empty else str(q.decision_time.max())}

def event_metrics(raw,i,direction,h):
    w=exact_future(raw,i+1,h)
    if w is None:return None
    e=float(raw.open.iloc[i+1])
    if direction=="UP":
        same=float(w.high.max()/e-1);adv=float(max(0,1-w.low.min()/e))
    else:
        same=float(max(0,1-w.low.min()/e));adv=float(max(0,w.high.max()/e-1))
    return same,adv

def time_same_1pct(raw,i,direction):
    w=exact_future(raw,i+1,8)
    if w is None:return np.nan
    e=float(raw.open.iloc[i+1]);target=e*(1.01 if direction=="UP" else .99)
    for j,r in enumerate(w.itertuples(index=False)):
        hit=float(r.high)>=target if direction=="UP" else float(r.low)<=target
        if hit:return float((j+1)*5)
    return np.nan

def impulse_analysis(raw,deoverlap):
    rr=(raw.close/raw.open-1).to_numpy(float);rows=[]
    for direction in ["UP","DOWN"]:
        for th in IMPULSE_THRESH:
            sel=[];last=-10**9
            for i,v in enumerate(rr):
                hit=v>=th if direction=="UP" else v<=-th
                if not hit or i+1>=len(raw):continue
                if deoverlap and i-last<48:continue
                sel.append(i);last=i
            for p in ["development","validation_2025","validation_2026"]:
                ids=[i for i in sel if partition(raw.ts.iloc[i]+BAR)==p]
                vals={h:[] for h in HORIZONS_H};advs={h:[] for h in HORIZONS_H};times=[];valid=[]
                for i in ids:
                    ms={h:event_metrics(raw,i,direction,h) for h in HORIZONS_H}
                    if any(v is None for v in ms.values()):continue
                    valid.append(i)
                    for h,(s,a) in ms.items():vals[h].append(s);advs[h].append(a)
                    times.append(time_same_1pct(raw,i,direction))
                o={"mode":"deoverlap_4h" if deoverlap else "all_events","partition":p,"direction":direction,
                   "impulse_threshold":th,"n":len(valid)}
                for h in HORIZONS_H:
                    ar=np.asarray(vals[h],float);aa=np.asarray(advs[h],float)
                    for ex in EXP_THRESH:o[f"p_expand_{int(ex*10000)}bp_{h}h"]=float((ar>=ex).mean()) if len(ar) else np.nan
                    o[f"median_same_mfe_{h}h"]=float(np.median(ar)) if len(ar) else np.nan
                    o[f"p75_same_mfe_{h}h"]=float(np.percentile(ar,75)) if len(ar) else np.nan
                    o[f"median_adverse_{h}h"]=float(np.median(aa)) if len(aa) else np.nan
                aa=np.asarray(advs[4],float);o["p_reversal_1pct_4h"]=float((aa>=.01).mean()) if len(aa) else np.nan
                tt=np.asarray(times,float);tt=tt[np.isfinite(tt)]
                o["median_time_same_1pct_min"]=float(np.median(tt)) if len(tt) else np.nan
                rows.append(o)
    return rows

def fp(v,d=1):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.{d}f}%"

def main():
    raw=load_klines();metrics=load_metrics();funding=load_funding()
    gaps=int((raw.ts.diff().dropna()!=BAR).sum())
    exp=int((raw.ts.iloc[-1]-raw.ts.iloc[0])/BAR)+1
    cov=len(raw)/exp

    a=add_targets(add_derivatives(build_15m(raw),metrics,funding),raw)
    a=a[(a.decision_time>=SCORE_START)&(a.decision_time<END)].copy()

    cuts={};br=[];cr=[]
    for feat in FEATURES:
        spec=frozen_cuts(a,feat);cuts[feat]=spec;br.extend(analyze_feature(a,feat,spec));cr.append(coverage_row(a,feat))
    bdf=pd.DataFrame(br);fs=pd.DataFrame([summarize_feature(bdf,f) for f in FEATURES]);cv=pd.DataFrame(cr)
    imp=pd.DataFrame(impulse_analysis(raw,False)+impulse_analysis(raw,True))
    bdf.to_csv(OUT_BUCKETS,index=False);fs.to_csv(OUT_FEATURES,index=False);cv.to_csv(OUT_COVERAGE,index=False);imp.to_csv(OUT_IMPULSE,index=False)

    rep=fs[fs.classification=="REPLICATED_DIRECTIONAL"];weak=fs[fs.classification=="UNSTABLE_OR_WEAK"];non=fs[fs.classification=="NON_INFORMATIVE"]
    status="SOL_INDICATOR_RELATIONSHIP_S3_COMPLETED_WITH_REPLICATED_SINGLE_INDICATORS" if len(rep) else "SOL_INDICATOR_RELATIONSHIP_S3_COMPLETED_NO_REPLICATED_SINGLE_INDICATOR"
    report={"protocol":"SOL_INDICATOR_RELATIONSHIP_S3","status":status,"frozen_end_exclusive":str(END),
            "raw":{"rows":len(raw),"first":str(raw.ts.min()),"last":str(raw.ts.max()),"coverage":cov,"gap_count":gaps},
            "metrics":{"rows":len(metrics),"first":None if metrics.empty else str(metrics.ts.min()),"last":None if metrics.empty else str(metrics.ts.max())},
            "funding":{"rows":len(funding),"first":None if funding.empty else str(funding.ts.min()),"last":None if funding.empty else str(funding.ts.max())},
            "decision_rows":len(a),"partitions":a.groupby("partition").size().to_dict(),"cuts":cuts,
            "feature_classification":fs.to_dict(orient="records")}
    OUT_JSON.write_text(json.dumps(report,indent=2,default=str)+"\n")

    lines=["# SOL Indicator Relationship Discovery — Stage 3 Result","","**Research only. Live BabaBot untouched.**","",
           "## Data integrity","",f"- Frozen end-exclusive: **{END}**.",
           f"- SOLUSDT raw 5m: **{len(raw):,} rows**, coverage **{cov:.4%}**, detected gaps **{gaps}**.",
           f"- Raw range: **{raw.ts.min()} -> {raw.ts.max()}**.",
           f"- OI metrics rows: **{len(metrics):,}**; range **{None if metrics.empty else metrics.ts.min()} -> {None if metrics.empty else metrics.ts.max()}**.",
           f"- Funding rows: **{len(funding):,}**; range **{None if funding.empty else funding.ts.min()} -> {None if funding.empty else funding.ts.max()}**.",
           f"- Stage 3A decision rows: **{len(a):,}**.","",
           "## Stage 3A — frozen single-indicator classification","",
           "| Feature | Class | Dev delta-D | 2025 delta-D | 2026 delta-D | Same sign |",
           "|---|---|---:|---:|---:|---:|"]
    for r in fs.itertuples(index=False):
        lines.append(f"| {r.feature} | {r.classification} | {fp(r.development_delta_D)} | {fp(r.validation_2025_delta_D)} | {fp(r.validation_2026_delta_D)} | {'YES' if r.same_sign_all else 'NO'} |")
    lines += ["",f"Replicated directional: **{len(rep)} / {len(fs)}**. Unstable/weak: **{len(weak)}**. Non-informative: **{len(non)}**.","",
              "Full frozen-bucket detail is persisted in SOL_INDICATOR_RELATIONSHIP_S3A_BUCKETS.csv.","",
              "## Stage 3B — 5m impulse -> expansion","",
              "Cumulative impulse thresholds: 0.50%, 0.75%, 1.00%, 1.50%, 2.00%, 3.00%.","",
              "| Partition | Dir | 5m impulse >= | N | +1% further in 4h | Opposite 1% reversal | Median 4h MFE |",
              "|---|---|---:|---:|---:|---:|---:|"]
    v=imp[imp["mode"]=="all_events"]
    for r in v.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.direction} | {100*r.impulse_threshold:.2f}% | {int(r.n)} | {fp(getattr(r,'p_expand_100bp_4h'))} | {fp(r.p_reversal_1pct_4h)} | {fp(r.median_same_mfe_4h,2)} |")
    lines += ["","A 4h de-overlapped sensitivity table is included in SOL_INDICATOR_RELATIONSHIP_S3B_IMPULSE_EXPANSION.csv.","",
              "## Stage 3 verdict",""]
    if len(rep):
        lines.append("At least one preregistered single indicator meets the frozen cross-partition directional-replication gate. Stage 4 may test interactions, but Stage 3 anatomy is not a deployable signal.")
    else:
        lines.append("No preregistered single indicator meets the frozen cross-partition directional-replication gate. Stage 4 may still test preregistered interactions because interaction effects can exist without strong marginal effects.")
    lines += ["",f"**Status: {status}**","",
              "Stage 3B is descriptive expansion anatomy. It does not change the frozen Stage 2 primary target or authorize a 5m impulse trading rule."]
    OUT_MD.write_text("\n".join(lines)+"\n");OUT_STATUS.write_text(status+"\n")
    print(status);print(OUT_MD.read_text())

if __name__=="__main__":
    main()
