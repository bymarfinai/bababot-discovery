#!/usr/bin/env python3
from __future__ import annotations
import io, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B31_S1_SWING_STRUCTURE_LIBRARY"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
SYMBOL="BNBUSDT"
BAR5=pd.Timedelta(minutes=5); BAR15=pd.Timedelta(minutes=15)
RAW_START=pd.Timestamp("2021-11-01T00:00:00Z")
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2026-08-26T00:00:00Z")
YEARS=[2022,2023,2024,2025,2026]
COOLDOWN=pd.Timedelta(minutes=60)
A1=ROOT/"frozen_a1"/"BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz"
A1_SHA="eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa"
DETECTORS=[
("S01","SWING_LOW_SWEEP_RECLAIM","LONG"),("S02","HH_HL_SETUP","LONG"),
("S03","BREAK_RETEST_HOLD","LONG"),("S04","FAILED_BREAKDOWN_RECLAIM","LONG"),
("S05","SWING_HIGH_SWEEP_REJECT","SHORT"),("S06","LL_LH_SETUP","SHORT"),
("S07","BREAK_RETEST_REJECT","SHORT"),("S08","FAILED_BREAKOUT_REJECT","SHORT")]

def fsha(p):
    h=sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def urls():
    m=pd.Timestamp(RAW_START.year,RAW_START.month,1,tz="UTC")
    em=pd.Timestamp(END.year,END.month,1,tz="UTC")
    out=[]
    while m<=em:
        ym=m.strftime("%Y-%m"); out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        m+=pd.offsets.MonthBegin(1)
    return out

def fetch(u):
    last=None
    for k in range(5):
        try:
            r=requests.get(u,timeout=90,headers={"User-Agent":"bababot-b31-s1/1.0"}); r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                n=[x for x in z.namelist() if x.lower().endswith(".csv")][0]
                with z.open(n) as f:
                    return pd.read_csv(f,header=None,usecols=[0,1,2,3,4],names=["ts","open","high","low","close"])
        except Exception as e:
            last=e; time.sleep(2**k)
    raise RuntimeError(f"fetch failed {u}: {last}")

def load_raw():
    fs=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut=[ex.submit(fetch,u) for u in urls()]
        for f in as_completed(fut): fs.append(f.result())
    x=pd.concat(fs,ignore_index=True)
    t=pd.to_numeric(x.ts,errors="coerce")
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x["ts"]=pd.to_datetime(t,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close"]: x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts",keep="last").sort_values("ts")
    x=x[(x.ts>=RAW_START)&(x.ts<END+pd.Timedelta(days=1))].copy()
    x["ts"]=x["ts"]+BAR5
    x=x.set_index("ts")[["open","high","low","close"]].astype(float)
    exp=int((x.index[-1]-x.index[0])/BAR5)+1
    cov=len(x)/exp
    h=sha256(pd.util.hash_pandas_object(x.reset_index(),index=False).values.tobytes()).hexdigest()
    return x,{"rows":len(x),"coverage":cov,"sha256":h,"first":x.index[0],"last":x.index[-1],"files":len(urls())}

def load_a1():
    if fsha(A1)!=A1_SHA: raise RuntimeError("A1 SHA mismatch")
    q=pd.read_csv(A1,compression="gzip",low_memory=False)
    q["decision_ts"]=pd.to_datetime(q["decision_ts"],utc=True)
    return q.set_index("decision_ts").sort_index()

def identity(raw,a1):
    idx=a1.index[(a1.index>=START)&(a1.index<=END)]
    idx=idx[idx.isin(raw.index)&(idx-BAR15).isin(raw.index)]
    rr=raw.close.reindex(idx).to_numpy()/raw.close.reindex(idx-BAR15).to_numpy()-1.0
    imm=pd.to_numeric(a1.ret_15.reindex(idx),errors="coerce").to_numpy()
    maxret=float(np.nanmax(np.abs(rr-imm)))
    q=raw.reindex(idx); rng=q.high-q.low
    cl=((q.close-q.low)-(q.high-q.close))/rng.replace(0,np.nan)
    immcl=pd.to_numeric(a1.close_location.reindex(idx),errors="coerce")
    maxcl=float((cl-immcl).abs().dropna().max())
    return {"n":len(idx),"max_ret15_diff":maxret,"max_close_location_diff":maxcl}

def bars15(raw):
    same2=(raw.index.to_series().diff().eq(BAR5)&raw.index.to_series().diff(2).eq(BAR5*2))
    b=pd.DataFrame(index=raw.index)
    b["open"]=raw.open.shift(2)
    b["high"]=raw.high.rolling(3,min_periods=3).max()
    b["low"]=raw.low.rolling(3,min_periods=3).min()
    b["close"]=raw.close
    b=b[(b.index.minute%15==0)&same2].copy()
    return b[(b.index>=START-pd.Timedelta(days=7))&(b.index<=END)]

def pivots(b):
    hi=b.high.to_numpy(); lo=b.low.to_numpy(); idx=b.index
    ph=[]; pl=[]
    for i in range(2,len(b)-2):
        if hi[i]>max(hi[i-2],hi[i-1],hi[i+1],hi[i+2]):
            ph.append((idx[i+2],idx[i],float(hi[i])))
        if lo[i]<min(lo[i-2],lo[i-1],lo[i+1],lo[i+2]):
            pl.append((idx[i+2],idx[i],float(lo[i])))
    return ph,pl

def cooldown(df):
    keep=[]
    last={}
    for r in df.sort_values(["event_ts","structure_id"]).itertuples(index=False):
        prev=last.get(r.structure_id)
        if prev is None or r.event_ts-prev>=COOLDOWN:
            keep.append(r); last[r.structure_id]=r.event_ts
    return pd.DataFrame(keep,columns=df.columns)

def detect(b):
    ph,pl=pivots(b)
    highs_by_confirm={}
    lows_by_confirm={}
    for z in ph: highs_by_confirm.setdefault(z[0],[]).append(z)
    for z in pl: lows_by_confirm.setdefault(z[0],[]).append(z)
    ah=[]; al=[]; rows=[]
    active_brk_hi=None; active_brk_lo=None
    prev_close=None
    names={i:(n,d) for i,n,d in DETECTORS}
    for i,(t,r) in enumerate(b.iterrows()):
        # use only pivots known before current bar for current-bar sweep/break logic
        last_hi=ah[-1] if ah else None; last_lo=al[-1] if al else None
        if t>=START:
            if last_lo and r.low<last_lo[2] and r.close>=last_lo[2]:
                rows.append((t,"S01",names["S01"][0],names["S01"][1],last_lo[2],last_lo[1]))
            if last_hi and r.high>last_hi[2] and r.close<=last_hi[2]:
                rows.append((t,"S05",names["S05"][0],names["S05"][1],last_hi[2],last_hi[1]))
            # mature existing break states first
            if active_brk_hi is not None:
                level,start_i,pivot_ts=active_brk_hi
                if i-start_i>4: active_brk_hi=None
                elif i>start_i and r.low<=level and r.close>level:
                    rows.append((t,"S03",names["S03"][0],names["S03"][1],level,pivot_ts)); active_brk_hi=None
            if active_brk_lo is not None:
                level,start_i,pivot_ts=active_brk_lo
                if i-start_i>4: active_brk_lo=None
                elif i>start_i and r.high>=level and r.close<level:
                    rows.append((t,"S07",names["S07"][0],names["S07"][1],level,pivot_ts)); active_brk_lo=None
            # failed break states use separate attributes on local function namespace
            fb=getattr(detect,"fb",None)
            if fb:
                kind,level,start_i,pivot_ts=fb
                if i-start_i>4: detect.fb=None
                elif i>start_i and kind=="DOWN" and r.close>=level:
                    rows.append((t,"S04",names["S04"][0],names["S04"][1],level,pivot_ts)); detect.fb=None
                elif i>start_i and kind=="UP" and r.close<=level:
                    rows.append((t,"S08",names["S08"][0],names["S08"][1],level,pivot_ts)); detect.fb=None
            # initiate fresh breaks only if prior close was on the other side
            if prev_close is not None and last_hi and prev_close<=last_hi[2] and r.close>last_hi[2]:
                active_brk_hi=(last_hi[2],i,last_hi[1]); detect.fb=("UP",last_hi[2],i,last_hi[1])
            if prev_close is not None and last_lo and prev_close>=last_lo[2] and r.close<last_lo[2]:
                active_brk_lo=(last_lo[2],i,last_lo[1]); detect.fb=("DOWN",last_lo[2],i,last_lo[1])
        # now confirm pivots whose right-side evidence closes at t
        new_lows=lows_by_confirm.get(t,[])
        new_highs=highs_by_confirm.get(t,[])
        for z in new_highs: ah.append(z)
        for z in new_lows: al.append(z)
        if t>=START:
            for z in new_lows:
                if len(al)>=2 and len(ah)>=2:
                    prev_l=al[-2]; new_l=al[-1]; prev_h=ah[-2]; last_h=ah[-1]
                    if new_l[2]>prev_l[2] and last_h[2]>prev_h[2] and prev_l[1]<last_h[1]<new_l[1]:
                        rows.append((t,"S02",names["S02"][0],names["S02"][1],new_l[2],new_l[1]))
            for z in new_highs:
                if len(ah)>=2 and len(al)>=2:
                    prev_h=ah[-2]; new_h=ah[-1]; prev_l=al[-2]; last_l=al[-1]
                    if new_h[2]<prev_h[2] and last_l[2]<prev_l[2] and prev_h[1]<last_l[1]<new_h[1]:
                        rows.append((t,"S06",names["S06"][0],names["S06"][1],new_h[2],new_h[1]))
        prev_close=float(r.close)
    if hasattr(detect,"fb"): delattr(detect,"fb")
    e=pd.DataFrame(rows,columns=["event_ts","structure_id","structure","direction","level","level_pivot_ts"])
    if len(e): e=e[(e.event_ts>=START)&(e.event_ts<=END)]
    return cooldown(e)

def summary(e):
    obs=(END-START)/pd.Timedelta(days=1)
    out=[]
    for sid,name,direction in DETECTORS:
        z=e[e.structure_id==sid].sort_values("event_ts"); n=len(z)
        cnt={y:int((z.event_ts.dt.year==y).sum()) for y in YEARS}
        eras=sum(v>=15 for v in cnt.values()); mx=max(cnt.values())/n if n else np.nan
        viable=n>=120 and eras>=4 and mx<=.35
        gaps=z.event_ts.diff().dropna()/pd.Timedelta(hours=1)
        out.append({"structure_id":sid,"structure":name,"direction":direction,"n":n,**{f"n_{y}":cnt[y] for y in YEARS},
                    "per365":n/obs*365,"median_gap_h":float(gaps.median()) if len(gaps) else np.nan,
                    "eras_ge15":eras,"max_era_share":mx,"status":"STRUCTURALLY_VIABLE" if viable else "INSUFFICIENT_STRUCTURE_SAMPLE"})
    return pd.DataFrame(out)

def overlap(e):
    sets={sid:set(e.loc[e.structure_id==sid,"event_ts"]) for sid,_,_ in DETECTORS}
    rows=[]
    for a,na,_ in DETECTORS:
        for b,nb,_ in DETECTORS:
            if a>=b: continue
            inter=len(sets[a]&sets[b]); union=len(sets[a]|sets[b])
            if inter: rows.append({"a":a,"structure_a":na,"b":b,"structure_b":nb,"same_ts":inter,"jaccard":inter/union})
    return pd.DataFrame(rows)

def render(s,diag,ident):
    status="BNB_B31_S1_SWING_STRUCTURE_LIBRARY_READY" if (s.status=="STRUCTURALLY_VIABLE").any() else "BNB_B31_S1_NO_VIABLE_SWING_STRUCTURE"
    L=["# BNB B31-S1 — Causal Swing-Structure Detector Library Result","",f"**Status: {status}**","",
       "S1 is structure-only. No entry or outcome/economic metric is evaluated.","","## Integrity",
       f"- Raw files: **{diag['files']}**; rows **{diag['rows']:,}**; coverage **{diag['coverage']:.6%}**",
       f"- Raw normalized SHA256: `{diag['sha256']}`",
       f"- A1 identity checks: ret15 max diff **{ident['max_ret15_diff']:.12g}**; close-location max diff **{ident['max_close_location_diff']:.12g}**","",
       "## Swing structure census","","| ID | Structure | Side | N | 2022 | 2023 | 2024 | 2025 | 2026* | /yr | Med gap | Eras>=15 | Max era | Status |",
       "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in s.itertuples(index=False):
        L.append(f"| {r.structure_id} | {r.structure} | {r.direction} | {r.n} | {r.n_2022} | {r.n_2023} | {r.n_2024} | {r.n_2025} | {r.n_2026} | {r.per365:.1f} | {r.median_gap_h:.1f}h | {r.eras_ge15} | {100*r.max_era_share:.1f}% | {r.status} |")
    L+=["","## Decision",f"**{status}**","",f"Viable swing structures: **{int((s.status=='STRUCTURALLY_VIABLE').sum())}/8**.","Only viable detectors may advance independently to structure-specific entry discovery.","No live orders were placed."]
    return "\n".join(L)+"\n"

def main():
    raw,diag=load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=load_a1(); ident=identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8: raise RuntimeError(f"identity fail {ident}")
    b=bars15(raw); e=detect(b); s=summary(e); ov=overlap(e); txt=render(s,diag,ident)
    s.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    ov.to_csv(ROOT/f"{PFX}_Overlap.csv",index=False)
    e.to_csv(ROOT/f"{PFX}_Events.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    status="BNB_B31_S1_SWING_STRUCTURE_LIBRARY_READY" if (s.status=="STRUCTURALLY_VIABLE").any() else "BNB_B31_S1_NO_VIABLE_SWING_STRUCTURE"
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**diag,**ident})+"\n",encoding="utf-8")
    print(txt,flush=True)
if __name__=="__main__": main()
