#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_LONG_LEG_CAPTURE_V1"
COST = 0.15
NOTIONAL = 500.0
REVERSAL = 0.01
TARGETS = {
    "L2": {"tp": 2.0, "sl": 1.0, "hold5": 288},
    "L3": {"tp": 3.0, "sl": 1.0, "hold5": 576},
    "L5": {"tp": 5.0, "sl": 1.0, "hold5": 864},
}
CFGS = ((4,100),(6,100),(8,100),(8,200))
QUANTILES = (.50,.55,.60,.65,.70,.75,.80,.825,.85,.875,.90,.915,.93,.945,.96,.97,.98,.985,.99)

T0 = pd.Timestamp("2023-01-01", tz="UTC")
T1 = pd.Timestamp("2024-01-01", tz="UTC")
T2 = pd.Timestamp("2025-01-01", tz="UTC")
T3 = pd.Timestamp("2026-01-01", tz="UTC")

def resample_complete(x, rule, expected):
    agg = {
        "open": ("open","first"),
        "high": ("high","max"),
        "low": ("low","min"),
        "close": ("close","last"),
        "n": ("close","count"),
    }
    if "volume" in x.columns:
        agg["volume"] = ("volume","sum")
    z = x.resample(rule, label="left", closed="left").agg(**agg)
    return z[z.n == expected].drop(columns=["n"]).dropna().copy()

def true_range(x):
    pc = x.close.shift(1)
    return pd.concat([
        x.high-x.low,
        (x.high-pc).abs(),
        (x.low-pc).abs()
    ], axis=1).max(axis=1)

def add_tf(x, p):
    z = x.copy()
    z[p+"_atr20"] = true_range(z).rolling(20, min_periods=20).mean()
    z[p+"_ema20"] = z.close.ewm(span=20, adjust=False, min_periods=20).mean()
    for n in (1,3,6):
        z[p+"_ret"+str(n)] = z.close.pct_change(n)*100
    z[p+"_dist_ema"] = (z.close-z[p+"_ema20"]) / z[p+"_atr20"].replace(0,np.nan)
    z[p+"_ema_slope"] = (z[p+"_ema20"]-z[p+"_ema20"].shift(3)) / z[p+"_atr20"].replace(0,np.nan)
    z[p+"_ema_accel"] = z[p+"_ema_slope"] - z[p+"_ema_slope"].shift(3)
    return z

def build_features(x5):
    q = resample_complete(x5, "15min", 3)
    h1 = add_tf(resample_complete(x5, "1h", 12), "h1")
    h4 = add_tf(resample_complete(x5, "4h", 48), "h4")

    q["signal_end"] = q.index + pd.Timedelta(minutes=15)
    q["atr20"] = true_range(q).rolling(20, min_periods=20).mean()
    q["ema20"] = q.close.ewm(span=20, adjust=False, min_periods=20).mean()
    q["rng"] = q.high-q.low
    q["body"] = q.close-q.open
    q["body_norm"] = q.body / q.rng.replace(0,np.nan)
    q["close_loc"] = (q.close-q.low) / q.rng.replace(0,np.nan)
    q["lower_wick"] = (np.minimum(q.open,q.close)-q.low) / q.rng.replace(0,np.nan)
    q["upper_wick"] = (q.high-np.maximum(q.open,q.close)) / q.rng.replace(0,np.nan)
    q["range_atr"] = q.rng / q.atr20.replace(0,np.nan)
    q["body_atr"] = q.body.abs() / q.atr20.replace(0,np.nan)
    q["atr_pct"] = q.atr20/q.close*100
    q["dist_ema20"] = (q.close-q.ema20)/q.atr20.replace(0,np.nan)
    q["ema20_slope"] = (q.ema20-q.ema20.shift(4))/q.atr20.replace(0,np.nan)
    q["ema20_accel"] = q.ema20_slope-q.ema20_slope.shift(4)

    cols = []
    for n in (1,2,4,8,16,32,64):
        c = "ret"+str(n)
        q[c] = q.close.pct_change(n)*100
        cols.append(c)
    cols += ["body_norm","close_loc","lower_wick","upper_wick","range_atr","body_atr",
             "atr_pct","dist_ema20","ema20_slope","ema20_accel"]

    if "volume" in q.columns:
        q["vol_med32"] = q.volume.shift(1).rolling(32,min_periods=32).median()
        q["vol_ratio"] = q.volume/q.vol_med32.replace(0,np.nan)
        q["vol_change4"] = q.volume/q.volume.shift(4).replace(0,np.nan)
        cols += ["vol_ratio","vol_change4"]

    for n in (8,16,32,96,192):
        lo = q.low.rolling(n,min_periods=n).min()
        hi = q.high.rolling(n,min_periods=n).max()
        q["loc"+str(n)] = (q.close-lo)/(hi-lo).replace(0,np.nan)
        q["rebound_low"+str(n)] = (q.close-lo)/q.atr20.replace(0,np.nan)
        q["drawdown_high"+str(n)] = (hi-q.close)/q.atr20.replace(0,np.nan)
        cols += ["loc"+str(n),"rebound_low"+str(n),"drawdown_high"+str(n)]

    for n in (4,8,16,32):
        plo = q.low.shift(1).rolling(n,min_periods=n).min()
        phi = q.high.shift(1).rolling(n,min_periods=n).max()
        q["dist_low"+str(n)] = (q.close-plo)/q.atr20.replace(0,np.nan)
        q["dist_high"+str(n)] = (phi-q.close)/q.atr20.replace(0,np.nan)
        q["sweep_reclaim"+str(n)] = ((q.low<plo)&(q.close>plo)).astype(float)
        q["break_high"+str(n)] = (q.close>phi).astype(float)
        cols += ["dist_low"+str(n),"dist_high"+str(n),"sweep_reclaim"+str(n),"break_high"+str(n)]

    for n in (4,8,16):
        pr = q.high.shift(1).rolling(n,min_periods=n).max() - q.low.shift(1).rolling(n,min_periods=n).min()
        q["compression"+str(n)] = pr/q.atr20.replace(0,np.nan)
        cols.append("compression"+str(n))

    h1["h1_ret24"] = h1.close.pct_change(24)*100
    h1["h1_lo72"] = h1.low.rolling(72,min_periods=72).min()
    h1["h1_hi72"] = h1.high.rolling(72,min_periods=72).max()
    h1["h1_loc72"] = (h1.close-h1.h1_lo72)/(h1.h1_hi72-h1.h1_lo72).replace(0,np.nan)
    h1_cols = ["h1_ret1","h1_ret3","h1_ret6","h1_ret24","h1_dist_ema","h1_ema_slope","h1_ema_accel","h1_loc72"]

    h4["h4_ret12"] = h4.close.pct_change(12)*100
    h4["h4_lo42"] = h4.low.rolling(42,min_periods=42).min()
    h4["h4_hi42"] = h4.high.rolling(42,min_periods=42).max()
    h4["h4_loc42"] = (h4.close-h4.h4_lo42)/(h4.h4_hi42-h4.h4_lo42).replace(0,np.nan)
    h4_cols = ["h4_ret1","h4_ret3","h4_ret6","h4_ret12","h4_dist_ema","h4_ema_slope","h4_ema_accel","h4_loc42"]

    c1 = h1[h1_cols].copy()
    c1["avail1"] = c1.index + pd.Timedelta(hours=1)
    c4 = h4[h4_cols].copy()
    c4["avail4"] = c4.index + pd.Timedelta(hours=4)

    q["bar_start"] = q.index
    q = pd.merge_asof(
        q.reset_index(drop=True).sort_values("signal_end"),
        c1.dropna().sort_values("avail1"),
        left_on="signal_end", right_on="avail1", direction="backward"
    )
    q = pd.merge_asof(
        q.sort_values("signal_end"),
        c4.dropna().sort_values("avail4"),
        left_on="signal_end", right_on="avail4", direction="backward"
    )
    q.index = pd.DatetimeIndex(q.bar_start)
    q = q.drop(columns=["bar_start"])
    return q.sort_index(), cols+h1_cols+h4_cols

def week_start(ts):
    t = pd.Timestamp(ts)
    return (t - pd.Timedelta(days=t.weekday())).normalize()

def weekly_range_table(q, end):
    z = q[(q.index>=T0)&(q.index<end)].copy()
    z["week"] = [week_start(t) for t in z.index]
    g = z.groupby("week").agg(week_high=("high","max"),week_low=("low","min"),bars=("close","size"))
    g["high_low_pct"] = (g.week_high/g.week_low-1)*100
    return g

def zigzag_long_legs(q, end, reversal=REVERSAL):
    z = q[(q.index>=T0)&(q.index<end)]
    idx = z.index
    px = z.close.astype(float).to_numpy()
    if len(px)<2:
        return pd.DataFrame()
    direction = 0
    lo_i = hi_i = 0
    lo = hi = px[0]
    legs = []
    for i in range(1,len(px)):
        p = px[i]
        if direction == 0:
            if p < lo:
                lo = p; lo_i = i
            if p > hi:
                hi = p; hi_i = i
            if p >= lo*(1+reversal):
                direction = 1
                peak = p; peak_i = i
                start_i = lo_i; start_px = lo
            elif p <= hi*(1-reversal):
                direction = -1
                trough = p; trough_i = i
        elif direction == 1:
            if p > peak:
                peak = p; peak_i = i
            elif p <= peak*(1-reversal):
                ret = (peak/start_px-1)*100
                legs.append((idx[start_i],idx[peak_i],start_px,peak,ret))
                direction = -1
                trough = p; trough_i = i
        else:
            if p < trough:
                trough = p; trough_i = i
            elif p >= trough*(1+reversal):
                direction = 1
                start_i = trough_i; start_px = trough
                peak = p; peak_i = i
    if direction == 1 and peak_i > start_i:
        ret = (peak/start_px-1)*100
        legs.append((idx[start_i],idx[peak_i],start_px,peak,ret))
    out = pd.DataFrame(legs,columns=["start","peak","start_px","peak_px","leg_pct"])
    if len(out):
        out["week"] = [week_start(t) for t in out.start]
        out["duration_h"] = (out.peak-out.start).dt.total_seconds()/3600
    return out

def add_leg_availability(weekly, legs):
    out = weekly.copy()
    for th in (2,3,5):
        if len(legs):
            s = legs[legs.leg_pct>=th].groupby("week").leg_pct.sum()
            n = legs[legs.leg_pct>=th].groupby("week").size()
            out["long_leg_"+str(th)+"_pct"] = s.reindex(out.index).fillna(0.0)
            out["long_leg_"+str(th)+"_n"] = n.reindex(out.index).fillna(0).astype(int)
        else:
            out["long_leg_"+str(th)+"_pct"] = 0.0
            out["long_leg_"+str(th)+"_n"] = 0
    return out

@dataclass
class Outcome:
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    outcome: str
    gross: float
    net: float
    pnl: float

def build_outcomes(q, x5, tp, sl, hold5, end):
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    out = {}
    for st in q.index[(q.index>=T0-pd.Timedelta(days=4))&(q.index<end)]:
        et = st+pd.Timedelta(minutes=15)
        p = int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:
            continue
        e = float(op[p])
        target = e*(1+tp/100)
        stop = e*(1-sl/100)
        last = min(p+hold5-1,len(idx)-1)
        ex = last
        reason = "TIME"
        gross = (float(cl[last])/e-1)*100
        for j in range(p,last+1):
            ht = hi[j]>=target
            hs = lo[j]<=stop
            if ht and hs:
                reason="SL_AMBIG"; ex=j; gross=-sl; break
            if hs:
                reason="SL"; ex=j; gross=-sl; break
            if ht:
                reason="TP"; ex=j; gross=tp; break
        net = gross-COST
        out[st] = Outcome(st,et,idx[ex],reason,gross,net,net/100*NOTIONAL)
    return out

def make_dataset(q, cols, outs):
    d = q[cols].copy()
    d["entry_time"] = [outs[t].entry_time if t in outs else pd.NaT for t in d.index]
    d["exit_time"] = [outs[t].exit_time if t in outs else pd.NaT for t in d.index]
    d["y"] = [1 if t in outs and outs[t].outcome=="TP" else (0 if t in outs else np.nan) for t in d.index]
    d = d.dropna(subset=cols+["entry_time","exit_time","y"]).copy()
    d["y"] = d.y.astype(int)
    return d

def period_weeks(start,end):
    first = week_start(start)
    last = week_start(end-pd.Timedelta(seconds=1))
    return pd.date_range(first,last,freq="7D",tz="UTC")

def evaluate(d, probs, thr, outs, start, end, tp, available_weekly, leg_threshold):
    chosen = d.index[(probs>=thr)&(d.entry_time>=start)&(d.entry_time<end)]
    active = pd.Timestamp.min.tz_localize("UTC")
    trades = []
    for st in chosen:
        o = outs[st]
        if o.entry_time<=active:
            continue
        trades.append(o)
        active=o.exit_time

    weeks = period_weeks(start,end)
    wrs = pd.Series(0.0,index=weeks)
    for o in trades:
        w=week_start(o.entry_time)
        if w in wrs.index:
            wrs.loc[w] += o.net

    n=len(trades)
    wins=sum(o.outcome=="TP" for o in trades)
    days=(end-start).total_seconds()/86400
    week_count=len(weeks)
    available_col="long_leg_"+str(int(leg_threshold))+"_pct"
    av=available_weekly.reindex(weeks)[available_col].fillna(0.0) if available_col in available_weekly.columns else pd.Series(0.0,index=weeks)
    gross_winner_pct=sum(o.gross for o in trades if o.outcome=="TP")
    available_sum=float(av.sum())
    return {
        "n":n,
        "wr":wins/n if n else np.nan,
        "trades_week":n/week_count if week_count else np.nan,
        "trades_day":n/days if days else np.nan,
        "exp":float(np.mean([o.net for o in trades])) if n else np.nan,
        "pnl":float(np.sum([o.pnl for o in trades])) if n else 0.0,
        "weekly_mean":float(wrs.mean()) if week_count else np.nan,
        "weekly_median":float(wrs.median()) if week_count else np.nan,
        "weeks_ge5":float((wrs>=5).mean()) if week_count else np.nan,
        "weeks_ge10":float((wrs>=10).mean()) if week_count else np.nan,
        "positive_weeks":float((wrs>0).mean()) if week_count else np.nan,
        "gross_to_available":gross_winner_pct/available_sum if available_sum>0 else np.nan,
        "timeouts":sum(o.outcome=="TIME" for o in trades),
    }

def oracle_eval(d, outs, start, end, available_weekly, leg_threshold):
    eligible=[st for st in d.index if d.loc[st,"entry_time"]>=start and d.loc[st,"entry_time"]<end and outs[st].outcome=="TP"]
    active=pd.Timestamp.min.tz_localize("UTC")
    trades=[]
    for st in eligible:
        o=outs[st]
        if o.entry_time<=active:
            continue
        trades.append(o);active=o.exit_time
    weeks=period_weeks(start,end)
    s=pd.Series(0.0,index=weeks)
    for o in trades:
        w=week_start(o.entry_time)
        if w in s.index:
            s.loc[w]+=o.net
    return {
        "n":len(trades),
        "trades_week":len(trades)/len(weeks) if len(weeks) else np.nan,
        "weekly_mean":float(s.mean()) if len(weeks) else np.nan,
        "weekly_median":float(s.median()) if len(weeks) else np.nan,
        "weeks_ge10":float((s>=10).mean()) if len(weeks) else np.nan,
    }

def leg_hit_stats(trades_df, legs, threshold, start, end):
    zlegs=legs[(legs.leg_pct>=threshold)&(legs.start>=start)&(legs.start<end)]
    if len(zlegs)==0:
        return {"legs":0,"hit_rate":np.nan,"early_hit_rate":np.nan}
    entries=pd.DatetimeIndex(trades_df.entry_time) if len(trades_df) else pd.DatetimeIndex([])
    hit=0;early=0
    for _,r in zlegs.iterrows():
        e=entries[(entries>=r.start)&(entries<=r.peak)]
        if len(e):
            hit+=1
            halfway=r.start+(r.peak-r.start)/2
            if e[0]<=halfway:
                early+=1
    return {"legs":len(zlegs),"hit_rate":hit/len(zlegs),"early_hit_rate":early/len(zlegs)}

def selected_trades_df(d, probs, thr, outs, start, end):
    chosen=d.index[(probs>=thr)&(d.entry_time>=start)&(d.entry_time<end)]
    active=pd.Timestamp.min.tz_localize("UTC");rows=[]
    for st in chosen:
        o=outs[st]
        if o.entry_time<=active:
            continue
        rows.append({"signal_time":st,"entry_time":o.entry_time,"exit_time":o.exit_time,
                     "outcome":o.outcome,"gross":o.gross,"net":o.net,"pnl":o.pnl})
        active=o.exit_time
    return pd.DataFrame(rows)

def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5,cov = wf1.v3.v1.base.load5("SOLUSDT")
    if cov<0.995:
        raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:
            x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(pd.Timestamp("2026-09-24",tz="UTC"),x5.index[-1]+pd.Timedelta(minutes=5))

    q,cols=build_features(x5)
    legs=zigzag_long_legs(q,end)
    weekly=add_leg_availability(weekly_range_table(q,end),legs)
    weekly.to_csv(ROOT/(PFX+"_WeeklyOpportunity.csv"))
    legs.to_csv(ROOT/(PFX+"_ExPostLongLegs.csv"),index=False)

    opportunity=[]
    for name,start,stop in (("2023",T0,T1),("2024",T1,T2),("2025",T2,T3),("2026",T3,end)):
        weeks=period_weeks(start,stop)
        w=weekly.reindex(weeks).fillna(0)
        row={"period":name,"weeks":len(w),
             "hl_mean":float(w.high_low_pct.mean()),"hl_median":float(w.high_low_pct.median()),
             "hl_ge15":float((w.high_low_pct>=15).mean())}
        for th in (2,3,5):
            c="long_leg_"+str(th)+"_pct"
            row["leg"+str(th)+"_mean"]=float(w[c].mean())
            row["leg"+str(th)+"_median"]=float(w[c].median())
            row["leg"+str(th)+"_ge10"]=float((w[c]>=10).mean())
        opportunity.append(row)
    opp=pd.DataFrame(opportunity)
    opp.to_csv(ROOT/(PFX+"_OpportunitySummary.csv"),index=False)

    transfer_rows=[]
    model_rows=[]
    feature_rows=[]
    trade_files=[]

    for target,spec in TARGETS.items():
        tp=float(spec["tp"]);sl=float(spec["sl"]);hold5=int(spec["hold5"])
        outs=build_outcomes(q,x5,tp,sl,hold5,end)
        d=make_dataset(q,cols,outs)
        train=d[(d.entry_time>=T0)&(d.entry_time<T1)&(d.exit_time<T1)].copy()
        val=d[(d.entry_time>=T1)&(d.entry_time<T2)&(d.exit_time<T2)].copy()
        r25=d[(d.entry_time>=T2)&(d.entry_time<T3)&(d.exit_time<T3)].copy()
        r26=d[(d.entry_time>=T3)&(d.entry_time<end)].copy()
        if min(len(train),len(val),len(r25),len(r26))<1000:
            raise RuntimeError("insufficient rows for "+target)

        candidates=[]
        fitted={}
        for depth,leaf in CFGS:
            m=RandomForestClassifier(
                n_estimators=260,
                max_depth=depth,
                min_samples_leaf=leaf,
                max_features="sqrt",
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1
            )
            m.fit(train[cols].astype(float),train.y)
            fitted[(depth,leaf)]=m
            pv=m.predict_proba(val[cols].astype(float))[:,1]
            for qt in QUANTILES:
                thr=float(np.quantile(pv,qt))
                met=evaluate(val,pv,thr,outs,T1,T2,tp,weekly,tp)
                candidates.append({"target":target,"depth":depth,"leaf":leaf,"quantile":qt,"threshold":thr,**met})

        c=pd.DataFrame(candidates)
        elig=c[(c.trades_week>=3)&(c.exp>0)].copy()
        if len(elig):
            ranked=elig.sort_values(["weekly_mean","weekly_median","wr","trades_week"],ascending=[False,False,False,False])
            selection_status="ELIGIBLE_POSITIVE"
        else:
            freq=c[c.trades_week>=3].copy()
            ranked=(freq if len(freq) else c).sort_values(["weekly_mean","weekly_median","wr","trades_week"],ascending=[False,False,False,False])
            selection_status="FRONTIER_NO_ELIGIBLE"
        ch=ranked.iloc[0]
        m=fitted[(int(ch["depth"]),int(ch["leaf"]))]
        thr=float(ch["threshold"])

        imp=pd.DataFrame({"feature":cols,"importance":m.feature_importances_}).sort_values("importance",ascending=False)
        for _,r in imp.head(15).iterrows():
            feature_rows.append({"target":target,"feature":r["feature"],"importance":r["importance"]})

        model_rows.append({
            "target":target,"selection_status":selection_status,
            "depth":int(ch["depth"]),"leaf":int(ch["leaf"]),
            "quantile":float(ch["quantile"]),"threshold":thr,
            "val_wr":float(ch["wr"]),"val_trades_week":float(ch["trades_week"]),
            "val_exp":float(ch["exp"]),"val_weekly_mean":float(ch["weekly_mean"]),
            "val_weekly_median":float(ch["weekly_median"])
        })

        for pname,z,start,stop in (("VAL2024",val,T1,T2),("REF2025",r25,T2,T3),("REF2026",r26,T3,end)):
            p=m.predict_proba(z[cols].astype(float))[:,1]
            met=evaluate(z,p,thr,outs,start,stop,tp,weekly,tp)
            tdf=selected_trades_df(z,p,thr,outs,start,stop)
            lhs=leg_hit_stats(tdf,legs,tp,start,stop)
            oracle=oracle_eval(z,outs,start,stop,weekly,tp)
            transfer_rows.append({
                "target":target,"partition":pname,**met,
                "legs":lhs["legs"],"leg_hit_rate":lhs["hit_rate"],"early_leg_hit_rate":lhs["early_hit_rate"],
                "oracle_n":oracle["n"],"oracle_trades_week":oracle["trades_week"],
                "oracle_weekly_mean":oracle["weekly_mean"],"oracle_weekly_median":oracle["weekly_median"],
                "oracle_weeks_ge10":oracle["weeks_ge10"]
            })
            if len(tdf):
                tdf.insert(0,"partition",pname)
                tdf.insert(0,"target",target)
                trade_files.append(tdf)

        c.sort_values(["weekly_mean","weekly_median"],ascending=[False,False]).head(100).to_csv(
            ROOT/(PFX+"_"+target+"_ValidationGrid.csv"),index=False
        )

    models=pd.DataFrame(model_rows)
    transfer=pd.DataFrame(transfer_rows)
    feats=pd.DataFrame(feature_rows)
    models.to_csv(ROOT/(PFX+"_SelectedModels.csv"),index=False)
    transfer.to_csv(ROOT/(PFX+"_Transfer.csv"),index=False)
    feats.to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)
    if trade_files:
        pd.concat(trade_files,ignore_index=True).to_csv(ROOT/(PFX+"_SelectedTrades.csv"),index=False)

    lines=["# SOL Long Leg Capture V1 — Result","",
           "- 5m coverage: **%.5f%%**" % (cov*100),
           "- complete 15m bars: **%s**" % format(len(q),","),
           "- ex-post long legs (1%% reversal segmentation): **%s**" % format(len(legs),","),
           "",
           "## A. Weekly opportunity census","",
           "|Period|HL mean|HL median|Weeks HL>=15%|>=2% legs mean/wk|>=3% legs mean/wk|>=5% legs mean/wk|Weeks with >=10% in >=2% long legs|",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in opp.iterrows():
        lines.append("|%s|%.2f%%|%.2f%%|%.1f%%|%.2f%%|%.2f%%|%.2f%%|%.1f%%|" % (
            r["period"],r["hl_mean"],r["hl_median"],r["hl_ge15"]*100,
            r["leg2_mean"],r["leg3_mean"],r["leg5_mean"],r["leg2_ge10"]*100))

    lines += ["","## B. Frozen causal detector transfer","",
              "|Target|Partition|WR|Trades/wk|Exp/trade|Mean weekly net|Median weekly net|Weeks >=5%|Weeks >=10%|Leg hit|Early hit|Oracle mean/wk|",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in transfer.iterrows():
        lines.append("|%s|%s|%.2f%%|%.2f|%.3f%%|%.2f%%|%.2f%%|%.1f%%|%.1f%%|%.1f%%|%.1f%%|%.2f%%|" % (
            r["target"],r["partition"],r["wr"]*100,r["trades_week"],r["exp"],
            r["weekly_mean"],r["weekly_median"],r["weeks_ge5"]*100,r["weeks_ge10"]*100,
            r["leg_hit_rate"]*100 if pd.notna(r["leg_hit_rate"]) else np.nan,
            r["early_leg_hit_rate"]*100 if pd.notna(r["early_leg_hit_rate"]) else np.nan,
            r["oracle_weekly_mean"]))

    lines += ["","## C. Selected 2024 configurations",""]
    for _,r in models.iterrows():
        lines.append("- **%s**: %s; RF depth %d / leaf %d; q %.3f; 2024 WR %.2f%%; %.2f trades/week; mean weekly %.2f%%." % (
            r["target"],r["selection_status"],r["depth"],r["leaf"],r["quantile"],
            r["val_wr"]*100,r["val_trades_week"],r["val_weekly_mean"]))

    robust=[]
    for target in TARGETS:
        z=transfer[transfer.target==target]
        if len(z)==3 and (z.exp>0).all() and (z.trades_week>=3).all():
            robust.append(target)
    if robust:
        verdict="TRANSFER_POSITIVE__"+("_".join(robust))
    else:
        verdict="NO_ROBUST_LEG_CAPTURE_YET"

    lines += ["","## D. Interpretation gate","",
              "The ex-post opportunity census is an upper-bound description of movement, not a tradable backtest.",
              "The oracle columns are hindsight ceilings and must never be treated as executable performance.",
              "Only the frozen causal detector rows count as strategy evidence.",
              "",
              "# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
