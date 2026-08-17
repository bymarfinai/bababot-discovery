#!/usr/bin/env python3
"""F5.18 frozen slow-health shadow check.

Frozen before inspecting post-2026-07-30 persistence details:
Friday15 BUY -> F5.12 HIDDEN_CORE_EMA -> P15 continuous persistence ->
prior 13 completed frozen-parent Friday average PnL < 0 -> HALF_RISK_STOP -0.35%.

All other Friday occurrences retain the frozen parent TP2.0/SL0.7/6h.
No SHORT, no filter, no tuning. Research only; live BBC untouched.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
import numpy as np
import pandas as pd

from f517_regime_attribution import (
    SYMBOL, BASE, CACHE, NOTIONAL, ROUND_TRIP_FEE,
    load_klines, get_zip_csv, simulate_parent, load_metrics_for_date,
    first_warning_and_persistence, simulate_half_risk, metrics_summary,
)

OOS_DATES = [pd.Timestamp(x, tz="UTC") for x in ["2026-07-31", "2026-08-07", "2026-08-14"]]


def load_daily_klines(start: str, end: str) -> pd.DataFrame:
    frames=[]
    for d in pd.date_range(pd.Timestamp(start,tz="UTC"), pd.Timestamp(end,tz="UTC"), freq="D"):
        ds=d.strftime("%Y-%m-%d")
        url=f"{BASE}/daily/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ds}.zip"
        df=get_zip_csv(url,f"{SYMBOL}-5m-{ds}.zip")
        if df is None:
            raise RuntimeError(f"missing daily kline {ds}")
        if len(df.columns)==12 and str(df.columns[0]).isdigit():
            p=CACHE/f"{SYMBOL}-5m-{ds}.zip"
            with zipfile.ZipFile(p) as zf:
                name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
                with zf.open(name) as fh:
                    df=pd.read_csv(fh,header=None)
        df=df.iloc[:,:12].copy()
        df.columns=["open_time","open","high","low","close","volume","close_time",
                    "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
        for c in ["open","high","low","close","volume","quote_volume","taker_buy_quote"]:
            df[c]=pd.to_numeric(df[c],errors="coerce")
        ot=pd.to_numeric(df.open_time,errors="coerce")
        unit="us" if ot.dropna().median()>1e14 else "ms"
        df["ts"]=pd.to_datetime(ot,unit=unit,utc=True)
        frames.append(df[["ts","open","high","low","close","volume","quote_volume","taker_buy_quote"]])
    return pd.concat(frames,ignore_index=True)


def extend_klines() -> pd.DataFrame:
    base=load_klines().reset_index(drop=True)
    aug=load_daily_klines("2026-08-01","2026-08-15")
    out=pd.concat([base,aug],ignore_index=True).dropna(subset=["ts","open","high","low","close"])
    out=out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    out["ema7"]=out.close.ewm(span=7,adjust=False).mean()
    out["ema20"]=out.close.ewm(span=20,adjust=False).mean()
    out["ema_spread"]=out.ema7/out.ema20-1.0
    out["ret5"]=out.close.pct_change()
    out["taker_imb"]=np.where(out.quote_volume>0,2*out.taker_buy_quote/out.quote_volume-1,np.nan)
    return out.set_index("ts",drop=False)


def main():
    print("F5.18 frozen shadow boot",flush=True)
    k=extend_klines()

    hist_dates=[d for d in pd.date_range(pd.Timestamp("2023-12-02",tz="UTC"),pd.Timestamp("2026-07-30",tz="UTC"),inclusive="left",freq="D") if d.weekday()==4]
    hist=[]
    for d in hist_dates:
        et=pd.Timestamp(d.date(),tz="UTC")+pd.Timedelta(hours=8)
        hist.append(simulate_parent(k,et))
    hs=metrics_summary(hist)
    if hs["n"]!=138 or hs["wins"]!=66 or abs(hs["pnl"]-64.630)>0.05:
        raise AssertionError(f"historical reproduction failed: {hs}")
    print("Historical reproduction PASS",hs,flush=True)

    prior_pnls=[t.pnl for t in hist]
    rows=[]
    parents=[]
    managed=[]
    for d in OOS_DATES:
        et=pd.Timestamp(d.date(),tz="UTC")+pd.Timedelta(hours=8)
        slow13=float(np.mean(prior_pnls[-13:]))
        p=simulate_parent(k,et)
        mdf=load_metrics_for_date(d)
        fw=first_warning_and_persistence(k,mdf,p) if mdf is not None else {"first_warning":None,"p15_t":None}
        p15=fw.get("p15_t")
        gate=bool(slow13<0 and p15 is not None)
        m=simulate_half_risk(k,p,p15) if gate else p
        parents.append(p); managed.append(m)
        rows.append({
            "date":str(d.date()),
            "slow13":slow13,
            "slow_negative":slow13<0,
            "parent_reason":p.reason,
            "parent_pnl":p.pnl,
            "first_warning":str(fw.get("first_warning")) if fw.get("first_warning") is not None else None,
            "p15_persistent":p15 is not None,
            "p15_decision":str(p15) if p15 is not None else None,
            "shadow_gate":gate,
            "managed_reason":m.reason,
            "managed_pnl":m.pnl,
            "delta":m.pnl-p.pnl,
        })
        # Causal next-Friday health ledger always uses frozen full-size parent outcome.
        prior_pnls.append(p.pnl)

    print(pd.DataFrame(rows).to_string(index=False),flush=True)
    print("PARENT",metrics_summary(parents),flush=True)
    print("SHADOW",metrics_summary(managed),flush=True)
    print("DELTA",sum(m.pnl-p.pnl for p,m in zip(parents,managed)),flush=True)
    pd.DataFrame(rows).to_csv("f518_rows.csv",index=False)
    import json
    Path("f518_result.json").write_text(json.dumps({
        "status":"F5.18_FROZEN_SHADOW_COMPLETE",
        "rows":rows,
        "parent":metrics_summary(parents),
        "shadow":metrics_summary(managed),
        "delta":sum(m.pnl-p.pnl for p,m in zip(parents,managed)),
    },indent=2,default=str))

if __name__=="__main__":
    main()
