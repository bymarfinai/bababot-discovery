#!/usr/bin/env python3
from __future__ import annotations
import csv, io, math, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B36_H1_E1_PREMIUM_RECOVERY"
PARENT=ROOT/"results"/"bnb_b35"/"BNB_B35_H1_SWEEP_LONG_EntryLedger.csv.gz"
BASE="https://data.binance.vision/data/futures/um"
SYMBOL="BNBUSDT"
DEV=[2022,2023,2024]; REF=[2025,2026]
STUDY_END=pd.Timestamp("2026-08-26T00:00:00Z")
EPS=1e-12

def wilson(h,n,z=1.959963984540054):
    if n<=0:return np.nan
    p=h/n; den=1+z*z/n; cen=p+z*z/(2*n)
    mar=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (cen-mar)/den

def month_urls(start,end):
    cur=pd.Timestamp(start.year,start.month,1,tz="UTC")
    last=pd.Timestamp(end.year,end.month,1,tz="UTC")
    out=[]
    while cur<=last:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/monthly/premiumIndexKlines/{SYMBOL}/15m/{SYMBOL}-15m-{ym}.zip")
        cur+=pd.offsets.MonthBegin(1)
    return out

def fetch_zip(url):
    last=None
    for k in range(4):
        try:
            r=requests.get(url,timeout=60,headers={"User-Agent":"bababot-b36/1.0"})
            if r.status_code==404:return []
            r.raise_for_status(); rows=[]
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:return []
                with zf.open(names[0]) as fh:
                    for row in csv.reader(io.TextIOWrapper(fh,encoding="utf-8")):
                        if len(row)<5:continue
                        try:ts=int(row[0]); pc=float(row[4])
                        except Exception:continue
                        if ts>100_000_000_000_000:ts//=1000
                        rows.append((ts,pc))
            return rows
        except Exception as e:
            last=e; time.sleep(2**k)
    raise RuntimeError(f"premium fetch failed {url}: {last}")

def load_premium(start,end):
    urls=month_urls(start,end); rows=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs=[ex.submit(fetch_zip,u) for u in urls]
        for f in as_completed(fs):rows.extend(f.result())
    if not rows:raise RuntimeError("no BNB premium index rows")
    p=pd.DataFrame(rows,columns=["open_ms","p_close"])
    p["open_ts"]=pd.to_datetime(pd.to_numeric(p.open_ms),unit="ms",utc=True,errors="coerce")
    p["close_ts"]=p.open_ts+pd.Timedelta(minutes=15)
    p=p.dropna().drop_duplicates("close_ts").sort_values("close_ts")
    p=p[(p.close_ts>=start-pd.Timedelta(days=8))&(p.close_ts<end+pd.Timedelta(days=1))].copy()
    p=p.set_index("close_ts",drop=False)
    s=p.p_close.astype(float)
    p["prior7_mean"]=s.rolling("7D",closed="left",min_periods=192).mean()
    p["prior7_std"]=s.rolling("7D",closed="left",min_periods=192).std(ddof=0)
    p["premium_z"]=(s-p.prior7_mean)/p.prior7_std
    return p

def feat_at(p,entry):
    idx=p.index
    i=int(idx.searchsorted(entry,side="left"))-1
    if i<0:return None
    cur=p.iloc[i]; cts=pd.Timestamp(cur.close_ts)
    lag=entry-cts
    if lag<=pd.Timedelta(0) or lag>pd.Timedelta(minutes=30):return None
    z=float(cur.premium_z)
    if not math.isfinite(z):return None
    target=cts-pd.Timedelta(minutes=60)
    j=int(idx.searchsorted(target,side="right"))-1
    if j<0:return None
    prev=p.iloc[j]; age=cts-pd.Timestamp(prev.close_ts)
    if age<pd.Timedelta(minutes=45) or age>pd.Timedelta(minutes=75):return None
    delta=float(cur.p_close)-float(prev.p_close)
    if not math.isfinite(delta):return None
    return {"premium_ts":cts,"premium_lag_min":lag.total_seconds()/60.0,
            "premium_close":float(cur.p_close),"premium_z":z,"premium_delta_60":delta}

def align(parent,p):
    rows=[]
    for r in parent.itertuples(index=False):
        f=feat_at(p,pd.Timestamp(r.entry_ts))
        if f is None:continue
        rows.append({"event_ts":r.event_ts,"entry_ts":r.entry_ts,"year":int(r.event_year),
                     "signed_60":float(r.signed_60),"signed_120":float(r.signed_120),"signed_240":float(r.signed_240),**f})
    return pd.DataFrame(rows)

def stats(z,parent_n,years):
    n=len(z); hit=(z.signed_120>EPS) if n else pd.Series(dtype=bool); h=int(hit.sum()) if n else 0
    d={"n":n,"participation":n/parent_n if parent_n else np.nan,
       "hit_120":h/n if n else np.nan,"wilson_120":wilson(h,n),
       "median_signed_120":float(z.signed_120.median()) if n else np.nan,
       "hit_60":float((z.signed_60>EPS).mean()) if n else np.nan,
       "hit_240":float((z.signed_240>EPS).mean()) if n else np.nan}
    for y in years:
        q=z[z.year==y]; d[f"n_{y}"]=len(q); d[f"hit_{y}"]=float((q.signed_120>EPS).mean()) if len(q) else np.nan
    return d

def cohorts(z):
    return {
      "P0_ALIGNED_BASELINE":pd.Series(True,index=z.index),
      "P1_NEGATIVE_PREMIUM":z.premium_z<0,
      "P2_NEGATIVE_RECOVERING":(z.premium_z<0)&(z.premium_delta_60>0),
    }

def development(z):
    masks=cohorts(z); base=stats(z,len(z),DEV); rows=[]
    for gid,m in masks.items():
        q=z[m].copy(); s=stats(q,len(z),DEV)
        worst=min(s[f"hit_{y}"] for y in DEV) if all(np.isfinite(s[f"hit_{y}"]) for y in DEV) else np.nan
        improve=s["hit_120"]-base["hit_120"] if np.isfinite(s["hit_120"]) else np.nan
        aux=max(s["hit_60"],s["hit_240"]) if np.isfinite(s["hit_60"]) and np.isfinite(s["hit_240"]) else np.nan
        eligible=(gid=="P2_NEGATIVE_RECOVERING")
        gate=(eligible and s["n"]>=160 and min(s[f"n_{y}"] for y in DEV)>=40 and s["participation"]>=.20 and
              s["hit_120"]>=.57 and s["wilson_120"]>.53 and worst>=.53 and s["median_signed_120"]>0 and
              improve>=.015 and aux>=.54)
        rows.append({"gate_id":gid,**s,"worst_dev_hit":worst,"improvement_vs_p0":improve,"aux_best":aux,
                     "promotion_eligible":eligible,"dev_gate":gate})
    return pd.DataFrame(rows)

def reference(z):
    masks=cohorts(z); base=stats(z,len(z),REF)
    q=z[masks["P2_NEGATIVE_RECOVERING"]].copy(); s=stats(q,len(z),REF)
    improve=s["hit_120"]-base["hit_120"] if np.isfinite(s["hit_120"]) else np.nan
    aux=max(s["hit_60"],s["hit_240"]) if np.isfinite(s["hit_60"]) and np.isfinite(s["hit_240"]) else np.nan
    gate=(s["n"]>=80 and s["n_2025"]>=40 and s["n_2026"]>=20 and s["participation"]>=.20 and
          s["hit_120"]>=.54 and s["wilson_120"]>.51 and s["hit_2025"]>.51 and s["hit_2026"]>.51 and
          s["median_signed_120"]>0 and improve>=.01 and aux>=.53)
    return {**s,"improvement_vs_p0":improve,"aux_best":aux,"reference_gate":gate},base

def pct(x):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:.2f}%"

def main():
    if not PARENT.exists():raise RuntimeError(f"missing frozen B35 ledger {PARENT}")
    x=pd.read_csv(PARENT,compression="gzip",parse_dates=["event_ts","entry_ts"])
    x=x[(x.entry_id=="E1")&x.entry_ts.notna()&x.signed_120.notna()].copy()
    dev=x[x.event_year.isin(DEV)].copy()
    if len(dev)!=805:raise RuntimeError(f"B35 E1 parent mismatch N={len(dev)} expected 805")
    parent_hit=float((dev.signed_120>EPS).mean())
    if abs(parent_hit-0.5540372670807453)>1e-12:raise RuntimeError(f"B35 parent hit mismatch {parent_hit}")

    pdv=load_premium(pd.Timestamp("2021-12-01T00:00:00Z"),pd.Timestamp("2025-01-01T00:00:00Z"))
    zd=align(dev,pdv)
    if zd.empty:raise RuntimeError("no development premium alignment")
    D=development(zd)
    D.to_csv(ROOT/f"{PFX}_Development.csv",index=False)
    zd.to_csv(ROOT/f"{PFX}_DevelopmentAligned.csv.gz",index=False,compression="gzip")
    p2=D[D.gate_id=="P2_NEGATIVE_RECOVERING"].iloc[0]
    opened=bool(p2.dev_gate); R=None; zr=None
    status="BNB_B36_NO_DEVELOPMENT_PREMIUM_GATE"

    if opened:
        ref=x[x.event_year.isin(REF)].copy()
        pr=load_premium(pd.Timestamp("2024-12-01T00:00:00Z"),STUDY_END)
        zr=align(ref,pr)
        if zr.empty:raise RuntimeError("no reference premium alignment")
        R,rb=reference(zr)
        zr.to_csv(ROOT/f"{PFX}_ReferenceAligned.csv.gz",index=False,compression="gzip")
        pd.DataFrame([R]).to_csv(ROOT/f"{PFX}_Reference.csv",index=False)
        status="BNB_B36_PREMIUM_REFERENCE_PASS" if R["reference_gate"] else "BNB_B36_PREMIUM_REFERENCE_REJECT"

    rows=["# BNB B36 — 1H Sweep + Premium Recovery Result","",f"**Status: {status}**","",
          "Frozen parent: B35 H1 1H sweep-reclaim LONG + E1 native-level retest.","",
          "## Integrity",f"- B35 development parent N **{len(dev)}**, +120 **{pct(parent_hit)}**.",
          f"- Premium-aligned development N **{len(zd)}/{len(dev)} ({len(zd)/len(dev):.2%})**.",
          "- Premium bar close is strictly before frozen entry; max staleness 30m.","",
          "## Development","","| Gate | Eligible | N | Part. | +120 | Wilson | Worst year | Improvement | +60 | +240 | Pass |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in D.itertuples(index=False):
        rows.append(f"| {r.gate_id} | {'YES' if r.promotion_eligible else 'NO'} | {r.n} | {pct(r.participation)} | {pct(r.hit_120)} | {pct(r.wilson_120)} | {pct(r.worst_dev_hit)} | {pct(r.improvement_vs_p0)} | {pct(r.hit_60)} | {pct(r.hit_240)} | {'PASS' if r.dev_gate else '—'} |")
    if not opened:
        rows+=["","P2 development failed; reference 2025-2026 remained **UNOPENED**."]
    else:
        rows+=["","## One-shot reference",f"- P2 N **{R['n']}**, participation **{pct(R['participation'])}**.",
               f"- +120 **{pct(R['hit_120'])}**, Wilson **{pct(R['wilson_120'])}**, improvement **{pct(R['improvement_vs_p0'])}**.",
               f"- 2025 **{pct(R['hit_2025'])}** (N={R['n_2025']}); 2026* **{pct(R['hit_2026'])}** (N={R['n_2026']}).",
               f"- +60 **{pct(R['hit_60'])}**, +240 **{pct(R['hit_240'])}**.",
               f"- Reference gate **{'PASS' if R['reference_gate'] else 'FAIL'}**."]
    rows+=["","## Decision",f"**{status}**","",
           "No premium magnitude tuning, no B35 entry changes, and no economics were performed."]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    pd.DataFrame([{"reference_opened":opened,"status":status}]).to_csv(ROOT/f"{PFX}_Selection.csv",index=False)
    print("\n".join(rows),flush=True)

if __name__=="__main__":
    main()
