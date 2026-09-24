#!/usr/bin/env python3
from __future__ import annotations
import io, time, zipfile, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import vectorbt as vbt

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B42_S1_OPPORTUNITY_ATLAS"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
SYMBOL="BNBUSDT"
RAW_START=pd.Timestamp("2021-12-01T00:00:00Z")
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2026-08-26T00:00:00Z")
BAR5=pd.Timedelta(minutes=5)
HORIZON_BARS=144
TP=0.01
SL=0.01

def urls():
    m=pd.Timestamp(RAW_START.year,RAW_START.month,1,tz="UTC")
    em=pd.Timestamp(END.year,END.month,1,tz="UTC")
    out=[]
    while m<=em:
        ym=m.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        m+=pd.offsets.MonthBegin(1)
    return out

def fetch(u):
    last=None
    for k in range(5):
        try:
            r=requests.get(u,timeout=90,headers={"User-Agent":"bababot-b42-s1/1.0"})
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                n=[x for x in z.namelist() if x.lower().endswith(".csv")][0]
                with z.open(n) as f:
                    return pd.read_csv(
                        f,header=None,usecols=[0,1,2,3,4,5],
                        names=["ts","open","high","low","close","volume"])
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
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts",keep="last").sort_values("ts")
    # Binance open timestamp -> close timestamp convention used in BNB research lineage.
    x["ts"]=x["ts"]+BAR5
    x=x.set_index("ts")[["open","high","low","close","volume"]].astype(float)
    x=x[(x.index>=RAW_START+BAR5)&(x.index<=END+pd.Timedelta(days=1))].copy()
    exp=int((x.index[-1]-x.index[0])/BAR5)+1
    coverage=len(x)/exp
    h=sha256(pd.util.hash_pandas_object(x.reset_index(),index=False).values.tobytes()).hexdigest()
    return x,{"rows":len(x),"coverage":coverage,"sha256":h,"first":x.index[0],"last":x.index[-1],"files":len(urls())}

def label_one(high,low,close,opens,i,side):
    entry_i=i+1
    if entry_i>=len(high): return None
    end=min(entry_i+HORIZON_BARS,len(high))
    if end<=entry_i: return None
    entry=float(opens[entry_i])
    if side=="LONG":
        tp=entry*(1+TP); sl=entry*(1-SL)
        tp_hit=np.flatnonzero(high[entry_i:end]>=tp)
        sl_hit=np.flatnonzero(low[entry_i:end]<=sl)
    else:
        tp=entry*(1-TP); sl=entry*(1+SL)
        tp_hit=np.flatnonzero(low[entry_i:end]<=tp)
        sl_hit=np.flatnonzero(high[entry_i:end]>=sl)
    a=int(tp_hit[0]) if len(tp_hit) else None
    b=int(sl_hit[0]) if len(sl_hit) else None
    if a is not None and b is not None and a==b:
        outcome="AMBIGUOUS"; first=a
    elif a is not None and (b is None or a<b):
        outcome="WIN"; first=a
    elif b is not None and (a is None or b<a):
        outcome="LOSS"; first=b
    else:
        outcome="TIMEOUT"; first=None
    last_i=end-1
    signed_timeout=(float(close[last_i])/entry-1.0)*(1 if side=="LONG" else -1)
    return {
        "side":side,"entry_i":entry_i,"entry":entry,"tp":tp,"sl":sl,
        "outcome":outcome,
        "first_touch_bars":None if first is None else first+1,
        "first_touch_min":None if first is None else (first+1)*5,
        "timeout_signed_return":signed_timeout,
        "horizon_bars":end-entry_i,
    }

def daily_summary(z,label):
    days=pd.Index(sorted(z.decision_day.unique()))
    w=z[z.outcome=="WIN"].groupby("decision_day").size().reindex(days,fill_value=0)
    wl=z[(z.outcome=="WIN")&(z.side=="LONG")].groupby("decision_day").size().reindex(days,fill_value=0)
    ws=z[(z.outcome=="WIN")&(z.side=="SHORT")].groupby("decision_day").size().reindex(days,fill_value=0)
    return {
        "period":label,"days":len(days),
        "days_ge1_win":int((w>=1).sum()),"days_ge1_win_pct":float((w>=1).mean()),
        "days_ge1_long_win_pct":float((wl>=1).mean()),
        "days_ge1_short_win_pct":float((ws>=1).mean()),
        "wins_per_day_q25":float(w.quantile(.25)),
        "wins_per_day_median":float(w.median()),
        "wins_per_day_q75":float(w.quantile(.75)),
        "days_ge5_win_pct":float((w>=5).mean()),
        "days_ge10_win_pct":float((w>=10).mean()),
    }

def main():
    raw,diag=load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    if getattr(vbt,"__version__",None)!="1.1.0":
        raise RuntimeError(f"vectorbt version mismatch {getattr(vbt,'__version__',None)}")

    idx=raw.index
    decision=np.flatnonzero(
        (idx>=START)&(idx<=END)&
        (idx.minute%15==0)&
        (np.arange(len(idx))+1<len(idx))
    )
    high=raw.high.to_numpy(); low=raw.low.to_numpy()
    close=raw.close.to_numpy(); opens=raw.open.to_numpy()
    rows=[]
    for n,i in enumerate(decision):
        t=idx[i]
        for side in ("LONG","SHORT"):
            q=label_one(high,low,close,opens,i,side)
            if q is None: continue
            rows.append({
                "decision_ts":t,"decision_day":t.floor("D"),"year":t.year,
                "decision_close":float(close[i]),**q
            })
        if (n+1)%25000==0: print(f"labeled {n+1}/{len(decision)} decisions",flush=True)
    L=pd.DataFrame(rows)
    L["period"]=np.where(L.year<=2024,"DEV","REF")

    counts=(L.groupby(["period","side","outcome"]).size().rename("n").reset_index())
    yearly=(L.groupby(["year","side","outcome"]).size().rename("n").reset_index())
    ds=pd.DataFrame([
        daily_summary(L,"ALL"),
        daily_summary(L[L.period=="DEV"],"DEV"),
        daily_summary(L[L.period=="REF"],"REF"),
    ])

    allr=ds[ds.period=="ALL"].iloc[0]
    dev=ds[ds.period=="DEV"].iloc[0]
    ref=ds[ds.period=="REF"].iloc[0]
    passed=(
        allr.days_ge1_win_pct>=.95 and dev.days_ge1_win_pct>=.95 and
        ref.days_ge1_win_pct>=.90 and allr.wins_per_day_median>=5
    )
    status="BNB_B42_S1_OPPORTUNITY_ATLAS_READY" if passed else "BNB_B42_S1_OPPORTUNITY_SUPPLY_INSUFFICIENT"

    sig=sha256(json.dumps({
        "symbol":SYMBOL,"start":str(START),"end":str(END),
        "decision":"15m_completed_bar","entry":"next_5m_open",
        "tp":TP,"sl":SL,"horizon_bars":HORIZON_BARS,
        "ambiguous":"exclude_from_win","vectorbt":"1.1.0"
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    counts.to_csv(ROOT/f"{PFX}_Counts.csv",index=False)
    yearly.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    ds.to_csv(ROOT/f"{PFX}_DailySupply.csv",index=False)
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"S1_SIGNATURE_SHA256={sig}\nVECTORBT_VERSION=1.1.0\n"
        f"RAW_SHA256={diag['sha256']}\n",encoding="utf-8")

    def pct(x): return f"{100*x:.2f}%"
    lines=[
      "# BNB B42-S1 — 1% Opportunity Atlas Result","",
      f"**Status: {status}**","",f"Signature: `{sig}`","",
      "## Integrity",
      f"- vectorbt: **{vbt.__version__}**",
      f"- 5m rows: **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**",
      f"- normalized raw SHA256: `{diag['sha256']}`",
      f"- decision timestamps: **{len(decision):,}**",
      f"- directional candidates: **{len(L):,}**","",
      "## Daily opportunity supply","",
      "| Period | Days | >=1 WIN day | >=1 LONG | >=1 SHORT | Q25 wins/day | Median | Q75 | >=5/day | >=10/day |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in ds.itertuples(index=False):
        lines.append(f"| {r.period} | {r.days} | {pct(r.days_ge1_win_pct)} | {pct(r.days_ge1_long_win_pct)} | {pct(r.days_ge1_short_win_pct)} | {r.wins_per_day_q25:.1f} | **{r.wins_per_day_median:.1f}** | {r.wins_per_day_q75:.1f} | {pct(r.days_ge5_win_pct)} | {pct(r.days_ge10_win_pct)} |")
    lines += ["","## Directional candidate outcomes","",
      "| Period | Side | Outcome | N |","|---|---|---|---:|"]
    for r in counts.itertuples(index=False):
        lines.append(f"| {r.period} | {r.side} | {r.outcome} | {r.n:,} |")
    lines += ["","## Interpretation",
      "- S1 measures *opportunity existence*, not predictability.",
      "- A WIN means a causal next-5m-open entry had +1% touched before -1% within 12h.",
      "- No hindsight-selected setup is promoted from S1.",
      "","## Decision",f"**{status}**",
      "",
      ("Movement supply is sufficient. Advance to B42-S2 fingerprint discovery with frozen S1 labels."
       if passed else
       "Movement supply itself fails the preregistered daily gate; do not pursue an 80% classifier under this label definition.")
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
