#!/usr/bin/env python3
from __future__ import annotations

import csv, io, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier

import sol_long_leg_capture_v1 as v1
import sol_long_leg_onset_v2 as v2

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ORDERFLOW_IGNITION_V3"
BASE="https://data.binance.vision/data/futures/um"
SYMBOL="SOLUSDT"
START=pd.Timestamp("2023-01-01",tz="UTC")
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")
CFGS=((4,100),(6,100),(8,100),(8,200))
QUANTILES=v1.QUANTILES
UA={"User-Agent":"bababot-sol-orderflow-v3/1.0"}

def get_zip_csv(url, timeout=45):
    r=requests.get(url,timeout=timeout,headers=UA)
    if r.status_code==404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh)

def fetch_kline15_month(month):
    ym=month.strftime("%Y-%m")
    url=f"{BASE}/monthly/klines/{SYMBOL}/15m/{SYMBOL}-15m-{ym}.zip"
    try:
        r=requests.get(url,timeout=60,headers=UA)
        if r.status_code==404:
            return None
        r.raise_for_status()
        rows=[]
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            name=[n for n in zf.namelist() if n.lower().endswith(".csv")][0]
            with zf.open(name) as fh:
                for row in csv.reader(io.TextIOWrapper(fh,encoding="utf-8")):
                    if len(row)<11:
                        continue
                    try:
                        ts=int(float(row[0]))
                    except Exception:
                        continue
                    if ts>100_000_000_000_000:
                        ts//=1000
                    try:
                        rows.append([
                            ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),
                            float(row[5]),float(row[7]),float(row[8]),float(row[9]),float(row[10])
                        ])
                    except Exception:
                        continue
        if not rows:
            return None
        return pd.DataFrame(rows,columns=["ts_ms","open","high","low","close","volume","quote_volume","trades","taker_buy_base","taker_buy_quote"])
    except Exception as e:
        return ("ERR","kline",ym,type(e).__name__,str(e)[:120])

def fetch_kline15_day(day):
    ds=day.strftime("%Y-%m-%d")
    url=f"{BASE}/daily/klines/{SYMBOL}/15m/{SYMBOL}-15m-{ds}.zip"
    try:
        r=requests.get(url,timeout=45,headers=UA)
        if r.status_code==404:
            return None
        r.raise_for_status()
        rows=[]
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            name=[n for n in zf.namelist() if n.lower().endswith(".csv")][0]
            with zf.open(name) as fh:
                for row in csv.reader(io.TextIOWrapper(fh,encoding="utf-8")):
                    if len(row)<11:
                        continue
                    try:
                        ts=int(float(row[0]))
                    except Exception:
                        continue
                    if ts>100_000_000_000_000:
                        ts//=1000
                    try:
                        rows.append([
                            ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),
                            float(row[5]),float(row[7]),float(row[8]),float(row[9]),float(row[10])
                        ])
                    except Exception:
                        continue
        if not rows:
            return None
        return pd.DataFrame(rows,columns=["ts_ms","open","high","low","close","volume","quote_volume","trades","taker_buy_base","taker_buy_quote"])
    except Exception as e:
        return ("ERR","kline_day",ds,type(e).__name__,str(e)[:120])

def load_flow15(end):
    months=list(pd.date_range(pd.Timestamp("2022-12-01",tz="UTC"),pd.Timestamp(end.year,end.month,1,tz="UTC"),freq="MS",tz="UTC"))
    frames=[];errs=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs=[ex.submit(fetch_kline15_month,m) for m in months]
        for f in as_completed(futs):
            z=f.result()
            if isinstance(z,tuple): errs.append(z)
            elif z is not None and len(z): frames.append(z)
    # Daily fallback for the current/end month because monthly archive may not yet exist.
    m0=pd.Timestamp(end.year,end.month,1,tz="UTC")
    days=list(pd.date_range(m0,end-pd.Timedelta(days=1),freq="D",tz="UTC"))
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs=[ex.submit(fetch_kline15_day,d) for d in days]
        for f in as_completed(futs):
            z=f.result()
            if isinstance(z,tuple): errs.append(z)
            elif z is not None and len(z): frames.append(z)
    if not frames:
        raise RuntimeError("no Data Vision 15m flow klines")
    x=pd.concat(frames,ignore_index=True)
    x["ts"]=pd.to_datetime(pd.to_numeric(x.ts_ms),unit="ms",utc=True)
    x=x.drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=START-pd.Timedelta(days=7))&(x.ts<end)].copy()

    qv=x.quote_volume.replace(0,np.nan)
    x["flow_imb15"]=2*x.taker_buy_quote/qv-1
    for n,name in ((2,"30"),(4,"60")):
        buy=x.taker_buy_quote.rolling(n,min_periods=n).sum()
        q=x.quote_volume.rolling(n,min_periods=n).sum().replace(0,np.nan)
        x["flow_imb"+name]=2*buy/q-1
    x["flow_accel"]=x.flow_imb15-x.flow_imb60
    x["quote_med32"]=x.quote_volume.shift(1).rolling(32,min_periods=16).median()
    x["trades_med32"]=x.trades.shift(1).rolling(32,min_periods=16).median()
    x["flow_quote_burst"]=x.quote_volume/x.quote_med32.replace(0,np.nan)
    x["flow_trade_burst"]=x.trades/x.trades_med32.replace(0,np.nan)
    x["avg_quote_trade"]=x.quote_volume/x.trades.replace(0,np.nan)
    x["avg_quote_trade_med32"]=x.avg_quote_trade.shift(1).rolling(32,min_periods=16).median()
    x["flow_size_burst"]=x.avg_quote_trade/x.avg_quote_trade_med32.replace(0,np.nan)
    x["flow_ret15"]=x.close/x.open-1
    x["flow_align"]=x.flow_ret15*x.flow_imb15
    x["flow_buy_on_red"]=np.where((x.flow_ret15<0)&(x.flow_imb15>0),x.flow_imb15,0.0)
    x["flow_sell_on_green"]=np.where((x.flow_ret15>0)&(x.flow_imb15<0),-x.flow_imb15,0.0)
    cols=["ts","flow_imb15","flow_imb30","flow_imb60","flow_accel","flow_quote_burst","flow_trade_burst","flow_size_burst","flow_align","flow_buy_on_red","flow_sell_on_green"]
    return x[cols].replace([np.inf,-np.inf],np.nan),errs

def fetch_metric_day(day):
    ds=day.strftime("%Y-%m-%d")
    url=f"{BASE}/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{ds}.zip"
    try:
        df=get_zip_csv(url)
        if df is None:
            return None
        df.columns=[str(c).strip().lower() for c in df.columns]
        def pick(*names):
            for n in names:
                if n in df.columns:
                    return n
            return None
        tc=pick("create_time","timestamp","time")
        oi=pick("sum_open_interest_value")
        top=pick("sum_toptrader_long_short_ratio")
        glob=pick("count_long_short_ratio")
        taker=pick("sum_taker_long_short_vol_ratio")
        topacct=pick("count_toptrader_long_short_ratio")
        if not all([tc,oi,top,glob,taker]):
            return ("ERR","metrics_cols",ds,"missing",",".join(df.columns))
        raw=df[tc]
        if pd.api.types.is_numeric_dtype(raw):
            v=pd.to_numeric(raw,errors="coerce")
            unit="us" if v.dropna().median()>1e14 else "ms"
            ts=pd.to_datetime(v,unit=unit,utc=True,errors="coerce")
        else:
            ts=pd.to_datetime(raw,utc=True,errors="coerce")
        out=pd.DataFrame({
            "ts":ts,
            "metric_oi":pd.to_numeric(df[oi],errors="coerce"),
            "metric_top":pd.to_numeric(df[top],errors="coerce"),
            "metric_global":pd.to_numeric(df[glob],errors="coerce"),
            "metric_taker":pd.to_numeric(df[taker],errors="coerce"),
        })
        out["metric_topacct"]=pd.to_numeric(df[topacct],errors="coerce") if topacct else np.nan
        return out.dropna(subset=["ts","metric_oi","metric_top","metric_global","metric_taker"])
    except Exception as e:
        return ("ERR","metrics",ds,type(e).__name__,str(e)[:120])

def load_metrics(end):
    days=list(pd.date_range((START-pd.Timedelta(days=2)).normalize(),end-pd.Timedelta(days=1),freq="D",tz="UTC"))
    frames=[];errs=[]
    with ThreadPoolExecutor(max_workers=32) as ex:
        futs=[ex.submit(fetch_metric_day,d) for d in days]
        done=0
        for f in as_completed(futs):
            z=f.result();done+=1
            if isinstance(z,tuple): errs.append(z)
            elif z is not None and len(z): frames.append(z)
            if done%300==0: print("metrics",done,"/",len(days),flush=True)
    if not frames:
        raise RuntimeError("no SOL metrics archives")
    m=pd.concat(frames,ignore_index=True).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    m=m[(m.ts>=START-pd.Timedelta(days=2))&(m.ts<end)].copy()
    for c in ["metric_oi","metric_top","metric_global","metric_taker","metric_topacct"]:
        m[c]=pd.to_numeric(m[c],errors="coerce")
    safe=lambda s: np.log(s.where(s>0))
    m["metric_oi_log"]=safe(m.metric_oi)
    m["metric_taker_log"]=safe(m.metric_taker)
    m["metric_top_log"]=safe(m.metric_top)
    m["metric_global_log"]=safe(m.metric_global)
    m["metric_top_vs_global"]=m.metric_top_log-m.metric_global_log
    for lag,name in ((3,"15"),(12,"60"),(48,"240")):
        m["metric_oi_chg"+name]=m.metric_oi_log-m.metric_oi_log.shift(lag)
        m["metric_taker_chg"+name]=m.metric_taker_log-m.metric_taker_log.shift(lag)
    m["metric_top_chg60"]=m.metric_top_log-m.metric_top_log.shift(12)
    m["metric_global_chg60"]=m.metric_global_log-m.metric_global_log.shift(12)
    if m.metric_topacct.notna().sum()>100:
        m["metric_topacct_log"]=safe(m.metric_topacct)
        m["metric_topacct_chg60"]=m.metric_topacct_log-m.metric_topacct_log.shift(12)
    else:
        m["metric_topacct_log"]=np.nan
        m["metric_topacct_chg60"]=np.nan
    cols=["ts","metric_oi_chg15","metric_oi_chg60","metric_oi_chg240","metric_taker_log","metric_taker_chg15","metric_taker_chg60","metric_top_vs_global","metric_top_chg60","metric_global_chg60","metric_topacct_log","metric_topacct_chg60"]
    return m[cols].replace([np.inf,-np.inf],np.nan),errs

def fetch_funding_month(month):
    ym=month.strftime("%Y-%m")
    url=f"{BASE}/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{ym}.zip"
    try:
        df=get_zip_csv(url,timeout=60)
        if df is None:return None
        df.columns=[str(c).strip().lower() for c in df.columns]
        tc="calc_time" if "calc_time" in df.columns else ("fundingtime" if "fundingtime" in df.columns else None)
        rc="last_funding_rate" if "last_funding_rate" in df.columns else ("fundingrate" if "fundingrate" in df.columns else None)
        if tc is None or rc is None:return ("ERR","funding_cols",ym,"missing",",".join(df.columns))
        raw=df[tc]
        if pd.api.types.is_numeric_dtype(raw):
            v=pd.to_numeric(raw,errors="coerce");unit="us" if v.dropna().median()>1e14 else "ms"
            ts=pd.to_datetime(v,unit=unit,utc=True,errors="coerce")
        else:
            ts=pd.to_datetime(raw,utc=True,errors="coerce")
        return pd.DataFrame({"ts":ts,"funding_rate":pd.to_numeric(df[rc],errors="coerce")}).dropna()
    except Exception as e:
        return ("ERR","funding",ym,type(e).__name__,str(e)[:120])

def load_funding(end):
    months=list(pd.date_range(pd.Timestamp("2022-12-01",tz="UTC"),pd.Timestamp(end.year,end.month,1,tz="UTC"),freq="MS",tz="UTC"))
    frames=[];errs=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(fetch_funding_month,m) for m in months]
        for f in as_completed(futs):
            z=f.result()
            if isinstance(z,tuple):errs.append(z)
            elif z is not None and len(z):frames.append(z)
    if not frames:
        return pd.DataFrame(columns=["ts","funding_rate","funding_z30","funding_chg"]),errs
    f=pd.concat(frames,ignore_index=True).drop_duplicates("ts").sort_values("ts")
    f=f[(f.ts>=START-pd.Timedelta(days=60))&(f.ts<end)].copy()
    f["funding_mean30"]=f.funding_rate.rolling(30,min_periods=10).mean()
    f["funding_sd30"]=f.funding_rate.rolling(30,min_periods=10).std()
    f["funding_z30"]=(f.funding_rate-f.funding_mean30)/f.funding_sd30.replace(0,np.nan)
    f["funding_chg"]=f.funding_rate-f.funding_rate.shift(1)
    return f[["ts","funding_rate","funding_z30","funding_chg"]].replace([np.inf,-np.inf],np.nan),errs

def probe_liquidation(ds):
    url=f"{BASE}/daily/liquidationSnapshot/{SYMBOL}/{SYMBOL}-liquidationSnapshot-{ds}.zip"
    try:
        r=requests.get(url,timeout=30,headers=UA)
        out={"date":ds,"status":r.status_code,"exists":r.status_code==200,"rows":0}
        if r.status_code!=200:return out
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:return out
            with zf.open(names[0]) as fh:df=pd.read_csv(fh)
        out["rows"]=len(df);out["columns"]=";".join(str(c) for c in df.columns)
        return out
    except Exception as e:
        return {"date":ds,"exists":False,"status":None,"rows":0,"error":type(e).__name__}

def join_external(q,flow,metrics,funding):
    z=q.copy()
    # Same completed 15m candle: flow row keyed by bar start.
    f=flow.set_index("ts")
    z=z.join(f,how="left")
    z["signal_end"]=z.index+pd.Timedelta(minutes=15)
    z["bar_start"]=z.index
    m=metrics.copy().sort_values("ts")
    z=pd.merge_asof(z.reset_index(drop=True).sort_values("signal_end"),m,
                    left_on="signal_end",right_on="ts",direction="backward",
                    tolerance=pd.Timedelta(minutes=15),allow_exact_matches=False,
                    suffixes=("","_metric_ts"))
    if "ts" in z.columns:z=z.drop(columns=["ts"])
    if len(funding):
        ff=funding.sort_values("ts")
        z=pd.merge_asof(z.sort_values("signal_end"),ff,left_on="signal_end",right_on="ts",
                        direction="backward",allow_exact_matches=False,suffixes=("","_fund_ts"))
        if "ts" in z.columns:z=z.drop(columns=["ts"])
    else:
        z["funding_rate"]=np.nan;z["funding_z30"]=np.nan;z["funding_chg"]=np.nan
    z.index=pd.DatetimeIndex(z.bar_start)
    return z.drop(columns=["bar_start"]).sort_index()

def select_and_eval(target,spec,d,cols,outs,legs,weekly,feature_set,end):
    train_end=v1.T1-pd.Timedelta(days=7)
    train=d[(d.entry_time>=v1.T0)&(d.entry_time<train_end)].copy()
    val=d[(d.entry_time>=v1.T1)&(d.entry_time<v1.T2)&(d.exit_time<v1.T2)].copy()
    r25=d[(d.entry_time>=v1.T2)&(d.entry_time<v1.T3)&(d.exit_time<v1.T3)].copy()
    r26=d[(d.entry_time>=v1.T3)&(d.entry_time<end)].copy()
    if min(len(train),len(val),len(r25),len(r26))<1000:
        raise RuntimeError(f"insufficient rows {target} {feature_set}: "+str([len(train),len(val),len(r25),len(r26)]))
    pos=int(train.onset.sum())
    if pos<100:raise RuntimeError(f"too few onset positives {target} {feature_set}: {pos}")

    cand=[];models={}
    tp=float(spec["tp"])
    for depth,leaf in CFGS:
        model=RandomForestClassifier(n_estimators=260,max_depth=depth,min_samples_leaf=leaf,
            max_features="sqrt",class_weight="balanced_subsample",random_state=314,n_jobs=-1)
        model.fit(train[cols].astype(float),train.onset)
        models[(depth,leaf)]=model
        pv=model.predict_proba(val[cols].astype(float))[:,1]
        for qt in QUANTILES:
            thr=float(np.quantile(pv,qt))
            met=v1.evaluate(val,pv,thr,outs,v1.T1,v1.T2,tp,weekly,tp)
            eh,lh=v2.candidate_early_hit(val,pv,thr,outs,legs,tp,v1.T1,v1.T2)
            cand.append({"target":target,"feature_set":feature_set,"depth":depth,"leaf":leaf,
                "quantile":qt,"threshold":thr,"train_onset_n":pos,"early_hit":eh,"leg_hit":lh,**met})
    c=pd.DataFrame(cand)
    elig=c[(c.trades_week>=3)&(c.exp>0)].copy()
    if len(elig):
        ranked=elig.sort_values(["weekly_mean","early_hit","wr","weekly_median"],ascending=[False,False,False,False])
        status="ELIGIBLE_POSITIVE"
    else:
        freq=c[c.trades_week>=3].copy()
        ranked=(freq if len(freq) else c).sort_values(["weekly_mean","early_hit","wr","weekly_median"],ascending=[False,False,False,False])
        status="FRONTIER_NO_ELIGIBLE"
    ch=ranked.iloc[0]
    model=models[(int(ch.depth),int(ch.leaf))];thr=float(ch.threshold)

    transfer=[];trades=[]
    for pname,z,start,stop in (("VAL2024",val,v1.T1,v1.T2),("REF2025",r25,v1.T2,v1.T3),("REF2026",r26,v1.T3,end)):
        p=model.predict_proba(z[cols].astype(float))[:,1]
        met=v1.evaluate(z,p,thr,outs,start,stop,tp,weekly,tp)
        tdf=v1.selected_trades_df(z,p,thr,outs,start,stop)
        hit=v1.leg_hit_stats(tdf,legs,tp,start,stop)
        transfer.append({"target":target,"feature_set":feature_set,"partition":pname,**met,
                         "legs":hit["legs"],"leg_hit_rate":hit["hit_rate"],"early_leg_hit_rate":hit["early_hit_rate"]})
        if len(tdf):
            tdf.insert(0,"partition",pname);tdf.insert(0,"feature_set",feature_set);tdf.insert(0,"target",target)
            trades.append(tdf)
    imp=pd.DataFrame({"target":target,"feature_set":feature_set,"feature":cols,"importance":model.feature_importances_}).sort_values("importance",ascending=False)
    selected={"target":target,"feature_set":feature_set,"selection_status":status,"train_onset_n":pos,
              "depth":int(ch.depth),"leaf":int(ch.leaf),"quantile":float(ch["quantile"]),"threshold":thr,
              "val_wr":float(ch.wr),"val_trades_week":float(ch.trades_week),"val_exp":float(ch.exp),
              "val_weekly_mean":float(ch.weekly_mean),"val_early_hit":float(ch.early_hit) if pd.notna(ch.early_hit) else np.nan}
    return selected,transfer,imp,pd.concat(trades,ignore_index=True) if trades else pd.DataFrame(),c

def main():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(END_CAP,x5.index[-1]+pd.Timedelta(minutes=5))

    print("loading flow15",flush=True)
    flow,flow_err=load_flow15(end)
    print("flow rows",len(flow),"errs",len(flow_err),flush=True)
    print("loading metrics",flush=True)
    metrics,metric_err=load_metrics(end)
    print("metric rows",len(metrics),"errs",len(metric_err),flush=True)
    print("loading funding",flush=True)
    funding,funding_err=load_funding(end)
    print("funding rows",len(funding),"errs",len(funding_err),flush=True)

    probe_dates=["2023-03-15","2023-10-15","2024-03-15","2024-10-15","2025-03-15","2025-10-15","2026-03-15","2026-09-15"]
    liq=[probe_liquidation(d) for d in probe_dates]
    liqdf=pd.DataFrame(liq);liqdf.to_csv(ROOT/(PFX+"_LiquidationProbe.csv"),index=False)

    q,price_cols=v1.build_features(x5)
    q=join_external(q,flow,metrics,funding)

    base_flow=["flow_imb15","flow_imb30","flow_imb60","flow_accel","flow_quote_burst","flow_trade_burst","flow_size_burst",
               "flow_align","flow_buy_on_red","flow_sell_on_green","metric_oi_chg15","metric_oi_chg60","metric_oi_chg240",
               "metric_taker_log","metric_taker_chg15","metric_taker_chg60","metric_top_vs_global","metric_top_chg60",
               "metric_global_chg60","funding_rate","funding_z30","funding_chg"]
    if q.metric_topacct_log.notna().sum()>1000:
        base_flow += ["metric_topacct_log","metric_topacct_chg60"]

    # Coverage: retain only fields with >=90% coverage over 2023-2026 feature rows.
    coverage={c:float(q.loc[(q.index>=START)&(q.index<end),c].notna().mean()) for c in base_flow}
    flow_cols=[c for c in base_flow if coverage[c]>=.90]
    if len(flow_cols)<12:
        raise RuntimeError("insufficient independent flow field coverage "+str(coverage))

    q[flow_cols]=q[flow_cols].replace([np.inf,-np.inf],np.nan)
    # Causal forward-fill is NOT used for 15m/metrics. Funding was backward-asof already.
    feature_sets={"FLOW_ONLY":flow_cols,"PRICE_PLUS_FLOW":price_cols+flow_cols}

    legs=v1.zigzag_long_legs(q,end)
    weekly=v1.add_leg_availability(v1.weekly_range_table(q,end),legs)

    selected_rows=[];transfer_rows=[];imp_frames=[];trade_frames=[];grid_frames=[]
    for target,spec in v1.TARGETS.items():
        outs=v1.build_outcomes(q,x5,float(spec["tp"]),float(spec["sl"]),int(spec["hold5"]),end)
        # Construct dataset with all candidate feature columns once.
        all_cols=list(dict.fromkeys(price_cols+flow_cols))
        d=v1.make_dataset(q,all_cols,outs)
        d["onset"]=v2.onset_labels(d.index,q,legs,float(spec["tp"]))
        for fs,cols in feature_sets.items():
            dd=d.dropna(subset=cols).copy()
            s,tr,imp,tdf,grid=select_and_eval(target,spec,dd,cols,outs,legs,weekly,fs,end)
            selected_rows.append(s);transfer_rows.extend(tr);imp_frames.append(imp.head(20));grid_frames.append(grid)
            if len(tdf):trade_frames.append(tdf)

    sel=pd.DataFrame(selected_rows);transfer=pd.DataFrame(transfer_rows)
    imp=pd.concat(imp_frames,ignore_index=True);grid=pd.concat(grid_frames,ignore_index=True)
    sel.to_csv(ROOT/(PFX+"_SelectedModels.csv"),index=False)
    transfer.to_csv(ROOT/(PFX+"_Transfer.csv"),index=False)
    imp.to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)
    grid.to_csv(ROOT/(PFX+"_ValidationGrid.csv"),index=False)
    if trade_frames:pd.concat(trade_frames,ignore_index=True).to_csv(ROOT/(PFX+"_SelectedTrades.csv"),index=False)
    pd.DataFrame([{"feature":k,"coverage":v} for k,v in coverage.items()]).to_csv(ROOT/(PFX+"_FeatureCoverage.csv"),index=False)

    lines=["# SOL Order-Flow / Liquidity Ignition V3 — Result","",
           "- 5m price coverage: **%.5f%%**"%(cov*100),
           "- Data Vision 15m flow rows: **%s**"%format(len(flow),","),
           "- derivatives metrics rows: **%s**"%format(len(metrics),","),
           "- funding rows: **%s**"%format(len(funding),","),
           "- independent flow fields retained at >=90%% coverage: **%d**"%len(flow_cols),
           "- liquidation probe usable dates: **%d/%d**"%(int(((liqdf.exists==True)&(liqdf.rows>0)).sum()),len(liqdf)),
           "","## Frozen transfer","",
           "|Target|Features|Partition|WR|Trades/wk|Exp/trade|Mean weekly|Median weekly|Leg hit|Early hit|Weeks>=10%|",
           "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in transfer.iterrows():
        lines.append("|%s|%s|%s|%.2f%%|%.2f|%.3f%%|%.2f%%|%.2f%%|%.1f%%|%.1f%%|%.1f%%|"%(r.target,r.feature_set,r.partition,
            r.wr*100,r.trades_week,r.exp,r.weekly_mean,r.weekly_median,
            r.leg_hit_rate*100 if pd.notna(r.leg_hit_rate) else np.nan,
            r.early_leg_hit_rate*100 if pd.notna(r.early_leg_hit_rate) else np.nan,r.weeks_ge10*100))
    lines+=["","## Selected 2024 models",""]
    for _,r in sel.iterrows():
        lines.append("- **%s / %s**: %s; RF %d/%d; q %.3f; 2024 mean weekly %.2f%%; WR %.2f%%; early-hit %.1f%%."%(
            r.target,r.feature_set,r.selection_status,r.depth,r.leaf,r["quantile"],r.val_weekly_mean,r.val_wr*100,
            r.val_early_hit*100 if pd.notna(r.val_early_hit) else np.nan))
    robust=[]
    for target in v1.TARGETS:
        for fs in feature_sets:
            z=transfer[(transfer.target==target)&(transfer.feature_set==fs)]
            if len(z)==3 and (z.exp>0).all() and (z.trades_week.iloc[:2]>=3).all():
                robust.append(target+"_"+fs)
    verdict="ORDERFLOW_TRANSFER_POSITIVE__"+("__".join(robust)) if robust else "NO_ROBUST_ORDERFLOW_IGNITION_V3"
    lines+=["","## Data-integrity note","",
            "Liquidation snapshot is not used unless historical archive probe coverage is adequate. No synthetic liquidation proxy is treated as liquidation data.",
            "All metrics/funding joins are backward-only and strictly before next-15m-open entry.",
            "","# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
