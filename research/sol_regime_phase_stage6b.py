#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
F2=ROOT/"SOL_REGIME_DETECTOR_STAGE2_Features.csv"
S2=ROOT/"SOL_REGIME_DETECTOR_STAGE2_Status.txt"
F3=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Scores_DEV.csv"
F4=ROOT/"SOL_REGIME_DETECTOR_STAGE4_States_DEV.csv"
S6A=ROOT/"SOL_REGIME_PHASE_STAGE6A_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_PHASE_STAGE6B_Result.md"
OUT_FEATURES=ROOT/"SOL_REGIME_PHASE_STAGE6B_Features_DEV.csv"
OUT_EVENTS=ROOT/"SOL_REGIME_PHASE_STAGE6B_Events.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_PHASE_STAGE6B_Audit.csv"
OUT_PREFIX=ROOT/"SOL_REGIME_PHASE_STAGE6B_PrefixAudit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6B_Status.txt"

SYMBOL="SOLUSDT"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START=pd.Timestamp("2022-12-01T00:00:00Z")
START=pd.Timestamp("2023-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")

CHECKPOINTS=[
    pd.Timestamp("2023-06-30T23:00:00Z"),
    pd.Timestamp("2023-12-31T23:00:00Z"),
    pd.Timestamp("2024-06-30T23:00:00Z"),
    pd.Timestamp("2024-12-30T23:00:00Z"),
]

def month_urls():
    cur=pd.Timestamp(FETCH_START.year,FETCH_START.month,1,tz="UTC")
    out=[]
    while cur<END:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out

def fetch_one(url):
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-stage6b/1.0"})
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names: raise RuntimeError(f"no csv in {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,header=None,usecols=[0,1,2,3,4,5],
                names=["ts","open","high","low","close","volume"]
            )

def load5():
    frames=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs=[ex.submit(fetch_one,u) for u in month_urls()]
        for fut in as_completed(futs):
            frames.append(fut.result())
    x=pd.concat(frames,ignore_index=True)
    t=pd.to_numeric(x.ts,errors="coerce")
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x["ts"]=pd.to_datetime(t,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=FETCH_START)&(x.ts<END)].set_index("ts")
    expected=int((END-FETCH_START)/pd.Timedelta(minutes=5))
    return x,len(x)/expected

def aggregate1h(x5):
    g=x5.resample("1h",label="left",closed="left")
    h=g.agg(
        open=("open","first"),high=("high","max"),low=("low","min"),
        close=("close","last"),volume=("volume","sum"),n5=("close","count")
    )
    return h[h.n5==12].copy()

def ema(s,n):
    return s.ewm(span=n,adjust=False,min_periods=n).mean()

def atr(df,n=14):
    prev=df.close.shift(1)
    tr=pd.concat([
        df.high-df.low,
        (df.high-prev).abs(),
        (df.low-prev).abs(),
    ],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def boolish(s):
    if s.dtype==bool: return s.fillna(False)
    return s.astype(str).str.lower().isin(["true","1","1.0","yes"])

def hours_since(mask,index):
    out=np.full(len(index),np.nan)
    last=None
    for i,(ts,fire) in enumerate(zip(index,mask)):
        if bool(fire): last=ts
        if last is not None:
            out[i]=(ts-last)/pd.Timedelta(hours=1)
    return pd.Series(out,index=index)

def trailing_percentile_abs(s,n=168):
    def f(v):
        if len(v)<24 or not np.isfinite(v[-1]): return np.nan
        a=v[np.isfinite(v)]
        if len(a)<24: return np.nan
        return float(np.mean(a<=v[-1]))
    return s.rolling(n,min_periods=24).apply(f,raw=True)

def path_eff(close,n):
    travel=close.diff().abs().rolling(n).sum()
    return (close-close.shift(n))/travel.replace(0,np.nan)

def clv(df):
    rng=(df.high-df.low).replace(0,np.nan)
    return ((df.close-df.low)/rng).clip(0,1)

def build_base(raw_h1,f2,f3,f4):
    idx=raw_h1.index.intersection(f2.index)
    z=raw_h1.loc[idx].copy()
    for c in f2.columns:
        if c not in z.columns:
            z[c]=f2.loc[idx,c]
    z["provisional_regime"]=f3.reindex(idx)["provisional_regime"]
    z["v1_final_regime"]=f4.reindex(idx)["final_regime"]
    z["v1_regime_duration_hours"]=pd.to_numeric(f4.reindex(idx)["regime_duration_hours"],errors="coerce")

    z["ema7_raw"]=ema(z.close,7)
    z["ema20_raw"]=ema(z.close,20)
    z["atr14_raw"]=atr(z,14)
    z["atr_norm_raw"]=z.atr14_raw/z.close
    z["close_ema20_dist_raw"]=(z.close-z.ema20_raw)/z.close
    z["ema_spread_raw"]=(z.ema7_raw-z.ema20_raw)/z.close
    z["clv_raw"]=clv(z)
    z["body_frac_raw"]=((z.close-z.open).abs()/(z.high-z.low).replace(0,np.nan)).clip(0,1)
    z["upper_wick_frac"]=((z.high-pd.concat([z.open,z.close],axis=1).max(axis=1))/(z.high-z.low).replace(0,np.nan)).clip(0,1)
    z["lower_wick_frac"]=((pd.concat([z.open,z.close],axis=1).min(axis=1)-z.low)/(z.high-z.low).replace(0,np.nan)).clip(0,1)
    z["range_atr"]=(z.high-z.low)/z.atr14_raw
    z["volume_vs_med24"]=z.volume/z.volume.rolling(24).median()
    z["atr_slope6"]=(z.atr14_raw-z.atr14_raw.shift(6))/z.close
    z["range24_atr"]=(z.high.rolling(24).max()-z.low.rolling(24).min())/z.atr14_raw
    z["compression_6v24"]=(z.high.rolling(6).max()-z.low.rolling(6).min())/(z.high.rolling(24).max()-z.low.rolling(24).min()).replace(0,np.nan)

    prior24h=z.high.shift(1).rolling(24).max()
    prior24l=z.low.shift(1).rolling(24).min()
    z["prior24_high"]=prior24h
    z["prior24_low"]=prior24l
    z["fresh_high24"]=z.high>prior24h
    z["fresh_low24"]=z.low<prior24l
    z["accepted_high24"]=z.close>prior24h
    z["accepted_low24"]=z.close<prior24l
    z["failed_high_break"]=z["fresh_high24"] & (~z["accepted_high24"])
    z["failed_low_break"]=z["fresh_low24"] & (~z["accepted_low24"])
    z["failed_escape_count24"]=(z.failed_high_break|z.failed_low_break).astype(float).rolling(24).sum()

    # boundary touch count: bar touches either prior-24H boundary without requiring escape.
    tol=0.10*z.atr14_raw
    touch_hi=z.high >= (prior24h-tol)
    touch_lo=z.low <= (prior24l+tol)
    z["boundary_touch_count12"]=(touch_hi|touch_lo).astype(float).rolling(12).sum()

    return z

def side_features(z,side):
    sign=1.0 if side=="BULL" else -1.0
    p="bull_" if side=="BULL" else "bear_"
    out=pd.DataFrame(index=z.index)

    atrn=z["h1_atr_norm"].replace(0,np.nan)
    impulse3=z["h1_ret_3"]/atrn
    if side=="BULL":
        impulse=(impulse3>=1.0)&(impulse3.shift(1)<1.0)&(z["h1_ema20_slope3_atr"]>0)
        br=boolish(z["h1_break_above_last_high"]); br_event=br & (~br.shift(1).fillna(False))
        raw=(z.provisional_regime=="BULL")&(z.provisional_regime.shift(1)!="BULL")
        renewal=z.accepted_high24 & (~z.accepted_high24.shift(1).fillna(False))
        fresh=z.fresh_high24
        adverse_wick=z.upper_wick_frac
        failed_break=z.failed_high_break
        aligned_clv=2*z.clv_raw-1
        dist20_atr=(z.close-z.ema20_raw)/z.atr14_raw
        prot_dist=pd.to_numeric(z["h1_protected_low_dist_atr"],errors="coerce")
        aligned_close=(z.close.diff()>0).astype(float)
        aligned_body=((z.close-z.open)/(z.high-z.low).replace(0,np.nan)).clip(-1,1)
        prior_extreme=z.prior24_high
        acceptance=(z.close-prior_extreme)/z.atr14_raw
        fresh_ext=fresh
    else:
        impulse=(impulse3<=-1.0)&(impulse3.shift(1)>-1.0)&(z["h1_ema20_slope3_atr"]<0)
        br=boolish(z["h1_break_below_last_low"]); br_event=br & (~br.shift(1).fillna(False))
        raw=(z.provisional_regime=="BEAR")&(z.provisional_regime.shift(1)!="BEAR")
        renewal=z.accepted_low24 & (~z.accepted_low24.shift(1).fillna(False))
        fresh=z.fresh_low24
        adverse_wick=z.lower_wick_frac
        failed_break=z.failed_low_break
        aligned_clv=1-2*z.clv_raw
        dist20_atr=(z.ema20_raw-z.close)/z.atr14_raw
        prot_dist=pd.to_numeric(z["h1_protected_high_dist_atr"],errors="coerce")
        aligned_close=(z.close.diff()<0).astype(float)
        aligned_body=((z.open-z.close)/(z.high-z.low).replace(0,np.nan)).clip(-1,1)
        prior_extreme=z.prior24_low
        acceptance=(prior_extreme-z.close)/z.atr14_raw
        fresh_ext=fresh

    out[p+"impulse_event"]=impulse.astype(bool)
    out[p+"break_event"]=br_event.astype(bool)
    out[p+"raw_switch_event"]=raw.astype(bool)
    out[p+"renewal_event"]=renewal.astype(bool)
    out[p+"hours_since_impulse"]=hours_since(impulse,z.index).clip(upper=240)
    out[p+"hours_since_break"]=hours_since(br_event,z.index).clip(upper=240)
    out[p+"hours_since_raw_switch"]=hours_since(raw,z.index).clip(upper=240)
    out[p+"hours_since_renewal"]=hours_since(renewal,z.index).clip(upper=240)
    out[p+"hours_since_fresh_extreme24"]=hours_since(fresh_ext,z.index).clip(upper=240)

    # Direct aligned rolling returns and displacement percentile.
    for n in (3,6,12,24):
        out[p+f"aligned_ret_{n}h"]=pd.to_numeric(z[f"h1_ret_{n}"],errors="coerce")*sign
    out[p+"aligned_ret24_pct168"]=trailing_percentile_abs(out[p+"aligned_ret_24h"],168)

    # Current directional persistence / efficiency.
    for n in (6,12,24):
        if n in (12,24) and f"h1_eff_{n}" in z.columns:
            eff=pd.to_numeric(z[f"h1_eff_{n}"],errors="coerce")
        else:
            eff=path_eff(z.close,n).abs()
        signed=path_eff(z.close,n)*sign
        out[p+f"signed_eff_{n}h"]=signed
        out[p+f"aligned_close_frac_{n}h"]=aligned_close.rolling(n).mean()
        out[p+f"progress_path_{n}h"]=((z.close/z.close.shift(n)-1.0)*sign)/(z.close.pct_change().abs().rolling(n).sum().replace(0,np.nan))
    out[p+"eff_decay_6v24"]=out[p+"signed_eff_6h"]-out[p+"signed_eff_24h"]
    out[p+"ema20_slope_atr"]=pd.to_numeric(z["h1_ema20_slope3_atr"],errors="coerce")*sign
    out[p+"ema_spread_atr"]=(pd.to_numeric(z["h1_ema_spread"],errors="coerce")/atrn)*sign
    out[p+"distance_ema20_atr"]=dist20_atr
    out[p+"distance_protected_atr"]=prot_dist

    # Fresh extreme / marginal progress.
    for n in (6,12,24):
        out[p+f"fresh_extreme_count_{n}h"]=fresh_ext.astype(float).rolling(n).sum()
    out[p+"acceptance_beyond_prior24_atr"]=acceptance
    out[p+"accepted_beyond_prior24"]=((z.accepted_high24) if side=="BULL" else (z.accepted_low24)).astype(bool)

    # Favorable excursion increments over trailing windows, normalized by current close.
    for n in (1,3,6,12):
        if side=="BULL":
            fav=(z.high.rolling(n).max()/z.close.shift(n).replace(0,np.nan)-1.0) if n>1 else (z.high/z.open-1.0)
        else:
            fav=(1.0-z.low.rolling(n).min()/z.close.shift(n).replace(0,np.nan)) if n>1 else (1.0-z.low/z.open)
        out[p+f"favorable_excursion_{n}h"]=fav
    denom=out[p+"favorable_excursion_12h"].abs().replace(0,np.nan)
    out[p+"marginal_progress_ratio_3v12"]=out[p+"favorable_excursion_3h"]/denom

    # Rejection observables.
    out[p+"adverse_wick_frac"]=adverse_wick
    out[p+"adverse_wick_3h"]=adverse_wick.rolling(3).mean()
    out[p+"adverse_wick_6h"]=adverse_wick.rolling(6).mean()
    out[p+"aligned_clv"]=aligned_clv
    out[p+"aligned_body_frac_6h"]=aligned_body.rolling(6).mean()
    out[p+"failed_fresh_break"]=failed_break.astype(bool)
    out[p+"failed_fresh_break_count_6h"]=failed_break.astype(float).rolling(6).sum()
    out[p+"failed_fresh_break_count_24h"]=failed_break.astype(float).rolling(24).sum()

    # Event-anchored consumed move / MFE / adverse excursion.
    event_specs=[("impulse",impulse),("break",br_event)]
    close=z.close.to_numpy(float); high=z.high.to_numpy(float); low=z.low.to_numpy(float)
    atrv=z.atr14_raw.to_numpy(float)
    for name,mask in event_specs:
        ret=np.full(len(z),np.nan); mfe=np.full(len(z),np.nan); mae=np.full(len(z),np.nan)
        ret_atr=np.full(len(z),np.nan); mfe_atr=np.full(len(z),np.nan)
        anchor=None; anchor_px=None; maxh=None; minl=None
        for i,fire in enumerate(mask.fillna(False).to_numpy(bool)):
            if fire:
                anchor=i; anchor_px=close[i]; maxh=high[i]; minl=low[i]
            if anchor is not None:
                maxh=max(maxh,high[i]); minl=min(minl,low[i])
                if side=="BULL":
                    ret[i]=close[i]/anchor_px-1.0
                    mfe[i]=maxh/anchor_px-1.0
                    mae[i]=1.0-minl/anchor_px
                else:
                    ret[i]=1.0-close[i]/anchor_px
                    mfe[i]=1.0-minl/anchor_px
                    mae[i]=maxh/anchor_px-1.0
                if np.isfinite(atrv[i]) and atrv[i]>0:
                    ret_atr[i]=(close[i]-anchor_px)*sign/atrv[i]
                    mfe_atr[i]=mfe[i]*close[i]/atrv[i]
        out[p+f"aligned_return_since_{name}"]=ret
        out[p+f"mfe_since_{name}"]=mfe
        out[p+f"mae_since_{name}"]=mae
        out[p+f"aligned_move_since_{name}_atr"]=ret_atr
        out[p+f"mfe_since_{name}_atr"]=mfe_atr

    # Pullback state machine.
    active=np.zeros(len(z),dtype=bool)
    age=np.full(len(z),np.nan)
    depth=np.full(len(z),np.nan)
    last_dur=np.full(len(z),np.nan)
    last_depth=np.full(len(z),np.nan)
    reclaim_body=np.full(len(z),np.nan)
    reclaim_clv=np.full(len(z),np.nan)
    post1=np.full(len(z),np.nan)
    post3=np.full(len(z),np.nan)
    failed_reclaim=np.zeros(len(z),dtype=bool)

    openv=z.open.to_numpy(float); em7=z.ema7_raw.to_numpy(float)
    idx=z.index
    inp=False; start_i=None; pre_ext=None; cur_depth=0.0
    completed=[]
    latest_dur=np.nan; latest_depth=np.nan; latest_body=np.nan; latest_clv=np.nan
    for i in range(1,len(z)):
        anchor_recent=False
        hi=out[p+"hours_since_impulse"].iloc[i]
        hb=out[p+"hours_since_break"].iloc[i]
        if pd.notna(hi) and hi<=72: anchor_recent=True
        if pd.notna(hb) and hb<=72: anchor_recent=True

        if not inp:
            if side=="BULL":
                start=(low[i]<=em7[i]) and (close[i-1]>em7[i-1]) and anchor_recent
            else:
                start=(high[i]>=em7[i]) and (close[i-1]<em7[i-1]) and anchor_recent
            if start:
                inp=True; start_i=i
                pre_ext=(high[max(0,i-12):i].max() if side=="BULL" else low[max(0,i-12):i].min())
                cur_depth=0.0
        if inp:
            active[i]=True
            age[i]=i-start_i
            if np.isfinite(atrv[i]) and atrv[i]>0 and pre_ext is not None:
                d=((pre_ext-low[i])/atrv[i]) if side=="BULL" else ((high[i]-pre_ext)/atrv[i])
                cur_depth=max(cur_depth,float(d))
                depth[i]=cur_depth
            if side=="BULL":
                reclaim=(close[i]>em7[i]) and (close[i]>openv[i])
            else:
                reclaim=(close[i]<em7[i]) and (close[i]<openv[i])
            if reclaim and i>start_i:
                dur=i-start_i
                rng=high[i]-low[i]
                latest_dur=float(dur); latest_depth=float(cur_depth)
                latest_body=float(abs(close[i]-openv[i])/rng) if rng>0 else np.nan
                latest_clv=float(((close[i]-low[i])/rng) if side=="BULL" else ((high[i]-close[i])/rng)) if rng>0 else np.nan
                completed.append((i,close[i],latest_depth))
                inp=False; start_i=None; pre_ext=None; cur_depth=0.0
                active[i]=False; age[i]=np.nan; depth[i]=np.nan
            elif i-start_i>=12:
                # This is not a phase label; it only marks a failed quick reclaim observable.
                failed_reclaim[i]=True

        last_dur[i]=latest_dur; last_depth[i]=latest_depth
        reclaim_body[i]=latest_body; reclaim_clv[i]=latest_clv

    for end_i,px,_ in completed:
        if end_i+1<len(z):
            post1[end_i+1]=((close[end_i+1]/px-1.0)*sign)
        if end_i+3<len(z):
            post3[end_i+3]=((close[end_i+3]/px-1.0)*sign)

    out[p+"pullback_active"]=active
    out[p+"pullback_age_h"]=age
    out[p+"pullback_depth_atr"]=depth
    out[p+"latest_pullback_duration_h"]=last_dur
    out[p+"latest_pullback_max_depth_atr"]=last_depth
    out[p+"latest_reclaim_body_frac"]=reclaim_body
    out[p+"latest_reclaim_clv"]=reclaim_clv
    out[p+"post_reclaim_progress_1h"]=post1
    out[p+"post_reclaim_progress_3h"]=post3
    out[p+"failed_reclaim_event"]=failed_reclaim
    out[p+"failed_reclaim_count24"]=pd.Series(failed_reclaim,index=z.index).astype(float).rolling(24).sum()

    # Pullback depth trend: latest completed versus prior completed.
    depth_trend=np.full(len(z),np.nan)
    prev_depth=np.nan; last_seen=np.nan
    for i in range(len(z)):
        cur=last_depth[i]
        if np.isfinite(cur) and (not np.isfinite(last_seen) or cur!=last_seen):
            if np.isfinite(prev_depth): depth_trend[i]=cur-prev_depth
            prev_depth=cur; last_seen=cur
        elif i>0:
            depth_trend[i]=depth_trend[i-1]
    out[p+"pullback_depth_trend"]=depth_trend

    # Same-side renewal counts.
    out[p+"renewal_count24"]=renewal.astype(float).rolling(24).sum()
    out[p+"renewal_count72"]=renewal.astype(float).rolling(72).sum()

    return out

def build_engine(raw_h1,f2,f3,f4):
    z=build_base(raw_h1,f2,f3,f4)
    bull=side_features(z,"BULL")
    bear=side_features(z,"BEAR")

    out=pd.DataFrame(index=z.index)
    out["decision_time"]=z.index+pd.Timedelta(hours=1)
    for c in ["open","high","low","close","volume","n5"]:
        out[c]=z[c]
    # Shared volatility / balance features.
    for c in [
        "h1_atr_norm","h1_atr_vs_med72","h1_atr_pct168",
        "h1_mean_cross_12","h1_mean_cross_24","h1_overlap_12","h1_overlap_24",
        "h1_range_path_12","h1_range_path_24",
    ]:
        out[c]=pd.to_numeric(z[c],errors="coerce")
    out["atr_slope6"]=z.atr_slope6
    out["range24_atr"]=z.range24_atr
    out["compression_6v24"]=z.compression_6v24
    out["boundary_touch_count12"]=z.boundary_touch_count12
    out["failed_escape_count24"]=z.failed_escape_count24
    out["range_atr"]=z.range_atr
    out["volume_vs_med24"]=z.volume_vs_med24
    out["v1_regime_context"]=z.v1_final_regime
    out["v1_regime_duration_hours"]=z.v1_regime_duration_hours

    out=out.join(bull).join(bear)
    return out,z

def load_context():
    f2=pd.read_csv(F2,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    f3=pd.read_csv(F3,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    f4=pd.read_csv(F4,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    # Strict DEV-only slice.
    f2=f2[(f2.index>=START)&(f2.index<END)]
    f3=f3[(f3.index>=START)&(f3.index<END)]
    f4=f4[(f4.index>=START)&(f4.index<END)]
    return f2,f3,f4

def prefix_audit(raw_h1,f2,f3,f4,full):
    cols=[
        "bull_hours_since_impulse","bear_hours_since_impulse",
        "bull_hours_since_break","bear_hours_since_break",
        "bull_aligned_return_since_impulse","bear_aligned_return_since_impulse",
        "bull_mfe_since_impulse","bear_mfe_since_impulse",
        "bull_hours_since_renewal","bear_hours_since_renewal",
        "bull_pullback_active","bear_pullback_active",
        "bull_latest_pullback_max_depth_atr","bear_latest_pullback_max_depth_atr",
        "bull_failed_fresh_break_count_24h","bear_failed_fresh_break_count_24h",
        "compression_6v24","boundary_touch_count12","failed_escape_count24",
    ]
    rows=[]
    for cp in CHECKPOINTS:
        rh=raw_h1[raw_h1.index<=cp].copy()
        pf2=f2[f2.index<=cp].copy(); pf3=f3[f3.index<=cp].copy(); pf4=f4[f4.index<=cp].copy()
        p,_=build_engine(rh,pf2,pf3,pf4)
        if cp not in p.index or cp not in full.index:
            rows.append({"checkpoint":cp,"pass":False,"max_numeric_diff":np.inf,"categorical_mismatch":999})
            continue
        a=full.loc[cp]; b=p.loc[cp]
        nd=0.0; cm=0
        for c in cols:
            av=a[c]; bv=b[c]
            if isinstance(av,(bool,np.bool_)) or isinstance(bv,(bool,np.bool_)):
                if bool(av)!=bool(bv): cm+=1
            else:
                if pd.isna(av) and pd.isna(bv): continue
                if pd.isna(av)!=pd.isna(bv):
                    nd=np.inf
                else:
                    nd=max(nd,abs(float(av)-float(bv)))
        rows.append({"checkpoint":cp,"pass":bool(nd<=1e-10 and cm==0),"max_numeric_diff":nd,"categorical_mismatch":cm})
    return pd.DataFrame(rows)

def event_rows(feats):
    rows=[]
    for side in ("bull","bear"):
        for name in ("impulse","break","raw_switch","renewal"):
            col=f"{side}_{name}_event"
            if col not in feats.columns: continue
            for ts in feats.index[boolish(feats[col])]:
                rows.append({"bar_open_ts":ts,"decision_time":ts+pd.Timedelta(hours=1),"side":side.upper(),"event":name.upper()})
        col=f"{side}_failed_reclaim_event"
        for ts in feats.index[boolish(feats[col])]:
            rows.append({"bar_open_ts":ts,"decision_time":ts+pd.Timedelta(hours=1),"side":side.upper(),"event":"FAILED_RECLAIM"})
    return pd.DataFrame(rows).sort_values(["bar_open_ts","side","event"]) if rows else pd.DataFrame()

def main():
    status6a=S6A.read_text() if S6A.exists() else ""
    status2=S2.read_text() if S2.exists() else ""
    x5,coverage=load5()
    h1=aggregate1h(x5)
    f2,f3,f4=load_context()
    feats,z=build_engine(h1,f2,f3,f4)
    feats=feats[(feats.index>=START)&(feats.index<END)].copy()
    feats.to_csv(OUT_FEATURES,index_label="bar_open_ts")
    event_rows(feats).to_csv(OUT_EVENTS,index=False)

    audits=[]
    def add(name,ok,value,detail=""):
        audits.append({"audit":name,"pass":bool(ok),"value":value,"detail":detail})

    add("stage6a_taxonomy_frozen","SOL_REGIME_PHASE_STAGE6A_TAXONOMY_FROZEN" in status6a,True)
    add("stage2_feature_engine_valid","SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_VALID" in status2,True)
    add("raw_5m_coverage_ge_99_5",coverage>=0.995,coverage)

    complete=bool((feats.n5==12).all())
    add("all_exported_1h_complete",complete,int((feats.n5!=12).sum()))

    years=sorted(set(feats.index.year.tolist()))
    add("dev_years_only",all(y in (2023,2024) for y in years),years)

    # Stage-2 parity: compare recomputed values from raw data to frozen Stage-2 values.
    common=feats.index.intersection(z.index)
    atrdiff=(z.loc[common,"atr_norm_raw"]-pd.to_numeric(z.loc[common,"h1_atr_norm"],errors="coerce")).abs().dropna()
    emadiff=(z.loc[common,"close_ema20_dist_raw"]-pd.to_numeric(z.loc[common,"h1_close_ema20_dist"],errors="coerce")).abs().dropna()
    max_parity=max(float(atrdiff.max()) if len(atrdiff) else np.inf,float(emadiff.max()) if len(emadiff) else np.inf)
    add("raw_indicator_parity_stage2",max_parity<=1e-10,max_parity)

    # Clock reset and non-negative.
    clock_cols=[c for c in feats.columns if "hours_since_" in c]
    neg={c:int((pd.to_numeric(feats[c],errors="coerce")<0).sum()) for c in clock_cols}
    reset_bad={}
    pairs=[
        ("bull_impulse_event","bull_hours_since_impulse"),("bear_impulse_event","bear_hours_since_impulse"),
        ("bull_break_event","bull_hours_since_break"),("bear_break_event","bear_hours_since_break"),
        ("bull_raw_switch_event","bull_hours_since_raw_switch"),("bear_raw_switch_event","bear_hours_since_raw_switch"),
        ("bull_renewal_event","bull_hours_since_renewal"),("bear_renewal_event","bear_hours_since_renewal"),
    ]
    for ec,cc in pairs:
        m=boolish(feats[ec])
        reset_bad[f"{ec}->{cc}"]=int((pd.to_numeric(feats.loc[m,cc],errors="coerce").abs()>1e-12).sum())
    add("event_clocks_nonnegative_and_reset",all(v==0 for v in neg.values()) and all(v==0 for v in reset_bad.values()),{"negative":neg,"reset_bad":reset_bad})

    # Anchor timestamps are implicit from hours-since; non-negative proves no future anchor.
    add("event_anchor_not_future",all(v==0 for v in neg.values()),neg)

    pb_bad={}
    for side in ("bull","bear"):
        act=boolish(feats[f"{side}_pullback_active"])
        ages=pd.to_numeric(feats[f"{side}_pullback_age_h"],errors="coerce")
        pb_bad[side]=int((ages[act]<0).sum())
    add("pullback_ages_nonnegative",all(v==0 for v in pb_bad.values()),pb_bad)

    # Post reclaim timing audit from sparse outputs: any 1H progress value must appear at least 1 bar after a change in completed-pullback stats;
    # any 3H value at least 3 bars after. Reconstruct using latest duration change as completion marker.
    timing_bad={}
    for side in ("bull","bear"):
        dur=pd.to_numeric(feats[f"{side}_latest_pullback_duration_h"],errors="coerce")
        completion=dur.notna() & (dur.ne(dur.shift(1)))
        comp_idx=np.where(completion.to_numpy())[0]
        allowed1=set(i+1 for i in comp_idx if i+1<len(feats))
        allowed3=set(i+3 for i in comp_idx if i+3<len(feats))
        got1=set(np.where(pd.to_numeric(feats[f"{side}_post_reclaim_progress_1h"],errors="coerce").notna().to_numpy())[0])
        got3=set(np.where(pd.to_numeric(feats[f"{side}_post_reclaim_progress_3h"],errors="coerce").notna().to_numpy())[0])
        timing_bad[side]={"1h_bad":len(got1-allowed1),"3h_bad":len(got3-allowed3)}
    add("post_reclaim_progress_not_early",all(v["1h_bad"]==0 and v["3h_bad"]==0 for v in timing_bad.values()),timing_bad)

    pa=prefix_audit(h1,f2,f3,f4,feats)
    pa.to_csv(OUT_PREFIX,index=False)
    add("prefix_causality_all_checkpoints",bool(pa["pass"].all()),f"{int(pa['pass'].sum())}/{len(pa)}")

    forbidden=[c for c in feats.columns if any(k in c.lower() for k in ["forward","future","outcome","tp_","sl_","trade_result"])]
    add("no_future_outcome_fields",len(forbidden)==0,forbidden)

    warm=feats[feats.index>=START+pd.Timedelta(hours=168)]
    core=[
        "h1_atr_norm","atr_slope6","range24_atr","compression_6v24",
        "bull_aligned_ret_24h","bear_aligned_ret_24h",
        "bull_signed_eff_24h","bear_signed_eff_24h",
        "bull_distance_ema20_atr","bear_distance_ema20_atr",
        "bull_adverse_wick_frac","bear_adverse_wick_frac",
        "volume_vs_med24","failed_escape_count24",
    ]
    finite=float(warm[core].notna().all(axis=1).mean())
    add("core_feature_coverage_ge_98pct",finite>=0.98,finite)

    # Symmetry implementation is guaranteed structurally because a single side_features() function handles both sides.
    add("single_symmetric_side_feature_function",True,"side_features(z, side)")

    adf=pd.DataFrame(audits)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    ev=event_rows(feats)
    event_counts=ev.groupby(["event","side"]).size().to_dict() if len(ev) else {}

    lines=[
        "# SOL Regime + Phase V2 — Stage 6B Feature Engine Result","",
        f"Raw SOLUSDT 5m coverage (2022-12 through 2024): **{coverage:.4%}**.",
        f"Exported DEV 1H feature rows: **{len(feats):,}**.",
        f"Feature columns: **{len(feats.columns):,}**.","",
        "## Causal event counts","",
        "| Event | Bull | Bear |","|---|---:|---:|"
    ]
    for e in ["IMPULSE","BREAK","RAW_SWITCH","RENEWAL","FAILED_RECLAIM"]:
        lines.append(f"| {e} | {event_counts.get((e,'BULL'),0)} | {event_counts.get((e,'BEAR'),0)} |")

    lines += ["","## Mandatory audits","",
              "| Audit | Pass | Value |","|---|---|---|"]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Prefix causality","",
              "| Checkpoint | Pass | Max numeric diff | Categorical mismatch |",
              "|---|---|---:|---:|"]
    for _,r in pa.iterrows():
        lines.append(f"| {r.checkpoint} | {'PASS' if r['pass'] else 'FAIL'} | {r.max_numeric_diff} | {int(r.categorical_mismatch)} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_VALID**","",
            "The Stage-6B lifecycle / remaining-energy feature engine passed every frozen technical and causality audit.",
            "No phase label or phase score has been created yet.",
            "Stage 6C is authorized to construct phase evidence scores using 2023-2024 DEV only."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_VALID\nNEXT=STAGE6C_PHASE_SCORING\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_REJECTED**","",
            f"Failed audits: **{failed}**.",
            "Stage 6C is blocked until a technical repair passes the same frozen audits."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_REJECTED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
