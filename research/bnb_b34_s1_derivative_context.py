#!/usr/bin/env python3
from __future__ import annotations
import io, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B34_S1_DERIVATIVE_CONTEXT"
PARENT=ROOT/"results"/"bnb_b33_s2"/"BNB_B33_S2_LIFECYCLE_ENTRY_Entries.csv.gz"
BASE="https://data.binance.vision/data/futures/um"
SYMBOL="BNBUSDT"
DEV=[2022,2023,2024]; REF=[2025,2026]
EPS=1e-12

def wilson(h,n,z=1.959963984540054):
    if n<=0:return np.nan
    p=h/n; den=1+z*z/n; cen=p+z*z/(2*n)
    mar=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (cen-mar)/den

def fetch_metric_day(day):
    ds=pd.Timestamp(day).strftime("%Y-%m-%d")
    url=f"{BASE}/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{ds}.zip"
    try:
        r=requests.get(url,timeout=35,headers={"User-Agent":"bababot-b34/1.0"})
        if r.status_code==404:return None
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:return None
            with zf.open(names[0]) as fh: df=pd.read_csv(fh)
        df.columns=[str(c).strip().lower() for c in df.columns]
        aliases={
          "ts":["create_time","timestamp","time"],
          "oi":["sum_open_interest_value"],
          "top":["sum_toptrader_long_short_ratio"],
          "global_ls":["count_long_short_ratio"],
          "taker":["sum_taker_long_short_vol_ratio"],
        }
        cols={}
        for k,opts in aliases.items():
            for o in opts:
                if o in df.columns: cols[k]=o; break
        if len(cols)!=len(aliases):return None
        raw=df[cols["ts"]]
        if pd.api.types.is_numeric_dtype(raw):
            v=pd.to_numeric(raw,errors="coerce")
            med=v.dropna().median()
            unit="us" if med>1e14 else "ms"
            ts=pd.to_datetime(v,unit=unit,utc=True,errors="coerce")
        else:
            ts=pd.to_datetime(raw,utc=True,errors="coerce")
        out=pd.DataFrame({
          "ts":ts,
          "oi":pd.to_numeric(df[cols["oi"]],errors="coerce"),
          "top":pd.to_numeric(df[cols["top"]],errors="coerce"),
          "global_ls":pd.to_numeric(df[cols["global_ls"]],errors="coerce"),
          "taker":pd.to_numeric(df[cols["taker"]],errors="coerce"),
        }).replace([np.inf,-np.inf],np.nan).dropna()
        return out
    except Exception as e:
        print(f"metric_day_error {ds} {type(e).__name__} {e}",flush=True)
        return None

def load_metrics(entries):
    days=set()
    for t in pd.to_datetime(entries.entry_ts,utc=True).dropna():
        d=t.normalize()
        days.add(d); days.add(d-pd.Timedelta(days=1))
    frames=[]
    ds=sorted(days)
    with ThreadPoolExecutor(max_workers=40) as ex:
        fut=[ex.submit(fetch_metric_day,d) for d in ds]
        done=0
        for f in as_completed(fut):
            z=f.result(); done+=1
            if z is not None and len(z):frames.append(z)
            if done%200==0:print(f"metrics {done}/{len(fut)}",flush=True)
    if not frames:raise RuntimeError("no derivatives metrics")
    m=pd.concat(frames,ignore_index=True).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return m

def feature_at(m,entry):
    ts=m.ts.to_numpy(dtype="datetime64[ns]")
    e=np.datetime64(pd.Timestamp(entry).tz_convert("UTC").tz_localize(None))
    i=int(np.searchsorted(ts,e,side="left"))-1
    if i<0:return None
    cur=m.iloc[i]; cts=pd.Timestamp(cur.ts)
    lag=pd.Timestamp(entry)-cts
    if lag<pd.Timedelta(0) or lag>pd.Timedelta(minutes=10):return None
    target=cts-pd.Timedelta(minutes=60)
    j=int(np.searchsorted(ts,np.datetime64(target.tz_localize(None)),side="right"))-1
    if j<0:return None
    p=m.iloc[j]
    age=cts-pd.Timestamp(p.ts)
    if age<pd.Timedelta(minutes=55) or age>pd.Timedelta(minutes=70):return None
    vals=[cur.oi,cur.top,cur.global_ls,cur.taker,p.oi]
    vals=[float(v) for v in vals]
    if any((not math.isfinite(v) or v<=0) for v in vals):return None
    return {
      "metric_ts":cts,
      "metric_lag_min":lag.total_seconds()/60.0,
      "oi_chg60":math.log(float(cur.oi)/float(p.oi)),
      "taker_ls":float(cur.taker),
      "top_pos_ls":float(cur.top),
      "global_ls":float(cur.global_ls),
    }

def align(entries,m):
    rows=[]
    for r in entries.itertuples(index=False):
        f=feature_at(m,r.entry_ts)
        if f is None:continue
        rows.append({
          "phase_ts":r.phase_ts,"entry_ts":r.entry_ts,"year":int(pd.Timestamp(r.entry_ts).year),
          "signed_30":float(r.signed_30),"signed_60":float(r.signed_60),"signed_120":float(r.signed_120),
          **f
        })
    return pd.DataFrame(rows)

def masks(z):
    g1=z.oi_chg60>0
    g2=g1 & (z.taker_ls>1.0)
    g3=g2 & (z.top_pos_ls>z.global_ls)
    return {
      "G0_BASELINE":pd.Series(True,index=z.index),
      "G1_OI_EXPANSION":g1,
      "G2_OI_TAKER_CONFIRM":g2,
      "G3_OI_TAKER_SMART_CONFIRM":g3,
    }

def stat(z,parent_n,years):
    n=len(z)
    hit=(z.signed_60>EPS) if n else pd.Series(dtype=bool)
    out={
      "n":n,"participation":n/parent_n if parent_n else np.nan,
      "hit_60":float(hit.mean()) if n else np.nan,
      "wilson_60":wilson(int(hit.sum()),n) if n else np.nan,
      "hit_30":float((z.signed_30>EPS).mean()) if n else np.nan,
      "hit_120":float((z.signed_120>EPS).mean()) if n else np.nan,
      "median_signed_60":float(z.signed_60.median()) if n else np.nan,
    }
    for y in years:
        q=z[z.year==y]
        out[f"n_{y}"]=len(q)
        out[f"hit_{y}"]=float((q.signed_60>EPS).mean()) if len(q) else np.nan
    return out

def evaluate_dev(z):
    mm=masks(z); base=stat(z,len(z),DEV); rows=[]
    for gid,mask in mm.items():
        q=z[mask].copy(); s=stat(q,len(z),DEV)
        worst=min(s[f"hit_{y}"] for y in DEV) if all(np.isfinite(s[f"hit_{y}"]) for y in DEV) else np.nan
        improve=s["hit_60"]-base["hit_60"] if np.isfinite(s["hit_60"]) else np.nan
        aux=max(s["hit_30"],s["hit_120"]) if np.isfinite(s["hit_30"]) and np.isfinite(s["hit_120"]) else np.nan
        gate=(gid!="G0_BASELINE" and s["n"]>=300 and min(s[f"n_{y}"] for y in DEV)>=75 and
              s["participation"]>=.10 and s["hit_60"]>=.56 and s["wilson_60"]>.53 and
              worst>=.53 and improve>=.015 and aux>=.55)
        rows.append({"gate_id":gid,**s,"worst_year_hit":worst,"improvement_vs_g0":improve,"aux_best":aux,"dev_gate":gate})
    return pd.DataFrame(rows),base

def gate_mask(z,gid):
    return masks(z)[gid]

def evaluate_ref(z,gid):
    base=stat(z,len(z),REF); q=z[gate_mask(z,gid)].copy(); s=stat(q,len(z),REF)
    improve=s["hit_60"]-base["hit_60"] if np.isfinite(s["hit_60"]) else np.nan
    aux=max(s["hit_30"],s["hit_120"]) if np.isfinite(s["hit_30"]) and np.isfinite(s["hit_120"]) else np.nan
    ok=(s["n"]>=100 and s["n_2025"]>=50 and s["n_2026"]>=25 and s["participation"]>=.10 and
        s["hit_60"]>=.54 and s["wilson_60"]>.51 and s["hit_2025"]>.51 and s["hit_2026"]>.51 and
        improve>=.01 and aux>=.53)
    return {**s,"improvement_vs_g0":improve,"aux_best":aux,"reference_gate":ok},base

def pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.2f}%"

def main():
    if not PARENT.exists():raise RuntimeError(f"missing frozen B33 parent {PARENT}")
    p=pd.read_csv(PARENT,compression="gzip",parse_dates=["phase_ts","entry_ts"])
    p=p[(p.detector_id=="F1LE")&(p.policy_id=="E1")&p.entry_ts.notna()&p.signed_60.notna()].copy()
    dev=p[p.phase_year.isin(DEV)].copy()
    if len(dev)!=3014:raise RuntimeError(f"parent identity mismatch dev N={len(dev)} expected 3014")
    raw_hit=float((dev.signed_60>EPS).mean())
    if abs(raw_hit-0.540478)<1e-4:
        pass
    else:
        raise RuntimeError(f"parent identity mismatch dev hit={raw_hit:.8f}")

    md=load_metrics(dev); zd=align(dev,md)
    if len(zd)<.90*len(dev):raise RuntimeError(f"development derivatives alignment too low {len(zd)}/{len(dev)}")
    D,base=evaluate_dev(zd)
    passers=D[D.dev_gate].sort_values(["worst_year_hit","wilson_60","hit_60","n","gate_id"],ascending=[False,False,False,False,True])
    selected=None if passers.empty else str(passers.iloc[0].gate_id)

    ref_opened=False; R=None; ref_base=None; zr=None
    status="BNB_B34_S1_NO_DEVELOPMENT_GATE"
    if selected is not None:
        ref_opened=True
        ref=p[p.phase_year.isin(REF)].copy()
        mr=load_metrics(ref); zr=align(ref,mr)
        if len(zr)<.85*len(ref):raise RuntimeError(f"reference derivatives alignment too low {len(zr)}/{len(ref)}")
        R,ref_base=evaluate_ref(zr,selected)
        status="BNB_B34_S1_DERIVATIVE_CONTEXT_PASS" if R["reference_gate"] else "BNB_B34_S1_REFERENCE_REJECT"

    D.to_csv(ROOT/f"{PFX}_Development.csv",index=False)
    zd.to_csv(ROOT/f"{PFX}_DevelopmentAligned.csv.gz",index=False,compression="gzip")
    if zr is not None:zr.to_csv(ROOT/f"{PFX}_ReferenceAligned.csv.gz",index=False,compression="gzip")
    rows=["# BNB B34-S1 — Derivatives-Confirmed Liquidity Sweep Result","",f"**Status: {status}**","",
          "Frozen parent: F1LE liquidity sweep LONG EARLY + E1 native-level retest.","",
          "## Integrity",f"- Frozen B33 development parent: **N={len(dev):,}**, +60 hit **{pct(raw_hit)}**.",
          f"- Causally aligned development derivatives rows: **{len(zd):,}/{len(dev):,} ({len(zd)/len(dev):.2%})**.",
          "- Every derivative observation is strictly before entry; max staleness 10 minutes.","",
          "## Development","",
          "| Gate | N | Part. | +60 | Wilson | Worst year | Improvement | +30 | +120 | Pass |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in D.itertuples(index=False):
        rows.append(f"| {r.gate_id} | {r.n} | {pct(r.participation)} | {pct(r.hit_60)} | {pct(r.wilson_60)} | {pct(r.worst_year_hit)} | {pct(r.improvement_vs_g0)} | {pct(r.hit_30)} | {pct(r.hit_120)} | {'PASS' if r.dev_gate else '—'} |")
    rows += ["",f"Development winner: **{selected or 'NONE'}**."]
    if selected is None:
        rows += ["","Reference 2025-2026 remained **UNOPENED** by protocol."]
    else:
        rows += ["","## One-shot reference",f"- Frozen gate: **{selected}**",f"- Aligned parent N: **{len(zr):,}**",
                 f"- Selected N: **{R['n']:,}**; +60 **{pct(R['hit_60'])}**; Wilson **{pct(R['wilson_60'])}**.",
                 f"- 2025: N={R['n_2025']}, +60={pct(R['hit_2025'])}; 2026: N={R['n_2026']}, +60={pct(R['hit_2026'])}.",
                 f"- Improvement vs reference G0: **{pct(R['improvement_vs_g0'])}**.",
                 f"- Reference gate: **{'PASS' if R['reference_gate'] else 'FAIL'}**."]
    rows += ["","## Decision",f"**{status}**","",
             "No TP/SL/PnL/economic optimization was performed. Economics is authorized only after a B34-S1 reference pass."]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    pd.DataFrame([{"selected_gate":selected or "NONE","reference_opened":ref_opened,"status":status}]).to_csv(ROOT/f"{PFX}_Selection.csv",index=False)
    print("\n".join(rows),flush=True)

if __name__=="__main__":
    main()
