#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import sol_reset_winner_first_v1 as wf1

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_15M_CHARACTER_MINING_V3"
TP=1.0
SL=1.0
COST=0.15
NOTIONAL=500.0
HOLD=288
CFGS=((4,80),(6,80),(8,80),(8,150))
QS=(.50,.55,.60,.65,.70,.75,.80,.825,.85,.875,.90,.915,.93,.945,.96,.97,.98,.985,.99)

T0=pd.Timestamp("2023-01-01",tz="UTC")
T1=pd.Timestamp("2024-01-01",tz="UTC")
T2=pd.Timestamp("2025-01-01",tz="UTC")
T3=pd.Timestamp("2026-01-01",tz="UTC")

def rs(x,rule,n):
    agg={"open":("open","first"),"high":("high","max"),"low":("low","min"),"close":("close","last"),"n":("close","count")}
    if "volume" in x.columns:
        agg["volume"]=("volume","sum")
    z=x.resample(rule,label="left",closed="left").agg(**agg)
    return z[z.n==n].drop(columns=["n"]).dropna().copy()

def tr(x):
    pc=x.close.shift(1)
    return pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)

def tf(x,p):
    z=x.copy()
    z[p+"_atr"]=tr(z).rolling(20,min_periods=20).mean()
    z[p+"_ema"]=z.close.ewm(span=20,adjust=False,min_periods=20).mean()
    for n in (1,3,6):
        z[p+"_ret"+str(n)]=z.close.pct_change(n)*100
    z[p+"_dist_ema"]=(z.close-z[p+"_ema"])/z[p+"_atr"].replace(0,np.nan)
    z[p+"_ema_slope"]=(z[p+"_ema"]-z[p+"_ema"].shift(3))/z[p+"_atr"].replace(0,np.nan)
    return z

def features(x5):
    q=rs(x5,"15min",3)
    h1=tf(rs(x5,"1h",12),"h1")
    h4=tf(rs(x5,"4h",48),"h4")
    h1["h1_ret24"]=h1.close.pct_change(24)*100
    h1["lo72"]=h1.low.rolling(72,min_periods=72).min()
    h1["hi72"]=h1.high.rolling(72,min_periods=72).max()
    h1["h1_loc72"]=(h1.close-h1.lo72)/(h1.hi72-h1.lo72).replace(0,np.nan)

    q["signal_end"]=q.index+pd.Timedelta(minutes=15)
    q["atr20"]=tr(q).rolling(20,min_periods=20).mean()
    q["ema20"]=q.close.ewm(span=20,adjust=False,min_periods=20).mean()
    q["rng"]=q.high-q.low
    q["body"]=q.close-q.open
    q["body_norm"]=q.body/q.rng.replace(0,np.nan)
    q["close_loc"]=(q.close-q.low)/q.rng.replace(0,np.nan)
    q["lower_wick"]=(np.minimum(q.open,q.close)-q.low)/q.rng.replace(0,np.nan)
    q["range_atr"]=q.rng/q.atr20.replace(0,np.nan)
    q["body_atr"]=q.body.abs()/q.atr20.replace(0,np.nan)
    q["atr_pct"]=q.atr20/q.close*100
    q["dist_ema20"]=(q.close-q.ema20)/q.atr20.replace(0,np.nan)
    q["ema20_slope"]=(q.ema20-q.ema20.shift(4))/q.atr20.replace(0,np.nan)

    cols=[]
    for n in (1,2,4,8,16,32):
        c="ret"+str(n);q[c]=q.close.pct_change(n)*100;cols.append(c)
    cols += ["body_norm","close_loc","lower_wick","range_atr","body_atr","atr_pct","dist_ema20","ema20_slope"]

    for n in (4,8,16,32,96):
        lo=q.low.rolling(n,min_periods=n).min()
        hi=q.high.rolling(n,min_periods=n).max()
        c="loc"+str(n);q[c]=(q.close-lo)/(hi-lo).replace(0,np.nan);cols.append(c)

    for n in (4,8,16,32):
        plo=q.low.shift(1).rolling(n,min_periods=n).min()
        phi=q.high.shift(1).rolling(n,min_periods=n).max()
        q["dist_low"+str(n)]=(q.close-plo)/q.atr20.replace(0,np.nan)
        q["dist_high"+str(n)]=(phi-q.close)/q.atr20.replace(0,np.nan)
        q["sweep_reclaim"+str(n)]=((q.low<plo)&(q.close>plo)).astype(float)
        q["break_high"+str(n)]=(q.close>phi).astype(float)
        cols += ["dist_low"+str(n),"dist_high"+str(n),"sweep_reclaim"+str(n),"break_high"+str(n)]

    for n in (4,8):
        pr=q.high.shift(1).rolling(n,min_periods=n).max()-q.low.shift(1).rolling(n,min_periods=n).min()
        q["compression"+str(n)]=pr/q.atr20.replace(0,np.nan)
        cols.append("compression"+str(n))

    c1=["h1_loc72","h1_ret1","h1_ret3","h1_ret6","h1_ret24","h1_dist_ema","h1_ema_slope"]
    c4=["h4_ret1","h4_ret3","h4_ret6","h4_dist_ema","h4_ema_slope"]
    a1=h1[c1].copy();a1["avail1"]=a1.index+pd.Timedelta(hours=1)
    a4=h4[c4].copy();a4["avail4"]=a4.index+pd.Timedelta(hours=4)
    q["bar_start"]=q.index
    q=pd.merge_asof(q.reset_index(drop=True).sort_values("signal_end"),a1.dropna().sort_values("avail1"),
                    left_on="signal_end",right_on="avail1",direction="backward")
    q=pd.merge_asof(q.sort_values("signal_end"),a4.dropna().sort_values("avail4"),
                    left_on="signal_end",right_on="avail4",direction="backward")
    q.index=pd.DatetimeIndex(q.bar_start)
    q=q.drop(columns=["bar_start"])
    return q.sort_index(),cols+c1+c4

@dataclass
class O:
    entry_time:pd.Timestamp
    exit_time:pd.Timestamp
    outcome:str
    net:float
    pnl:float

def outcomes(q,x5):
    idx=x5.index
    op=x5.open.astype(float).to_numpy()
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()
    cl=x5.close.astype(float).to_numpy()
    end=min(pd.Timestamp("2026-09-24",tz="UTC"),idx[-1]+pd.Timedelta(minutes=5))
    out={}
    for st in q.index[(q.index>=T0-pd.Timedelta(days=2))&(q.index<end)]:
        et=st+pd.Timedelta(minutes=15)
        p=int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:
            continue
        e=float(op[p]);tp=e*1.01;sl=e*.99
        last=min(p+HOLD-1,len(idx)-1)
        ex=last;reason="TIME";gross=(float(cl[last])/e-1)*100
        for j in range(p,last+1):
            ht=hi[j]>=tp;hs=lo[j]<=sl
            if ht and hs:
                reason="SL_AMBIG";ex=j;gross=-1.0;break
            if hs:
                reason="SL";ex=j;gross=-1.0;break
            if ht:
                reason="TP";ex=j;gross=1.0;break
        net=gross-COST
        out[st]=O(et,idx[ex],reason,net,net/100*NOTIONAL)
    return out

def dataset(q,cols,outs):
    d=q[cols].copy()
    d["entry_time"]=[outs[t].entry_time if t in outs else pd.NaT for t in d.index]
    d["exit_time"]=[outs[t].exit_time if t in outs else pd.NaT for t in d.index]
    d["y"]=[1 if t in outs and outs[t].outcome=="TP" else (0 if t in outs else np.nan) for t in d.index]
    d=d.dropna(subset=cols+["entry_time","exit_time","y"])
    d["y"]=d.y.astype(int)
    return d

def ev(d,p,thr,outs,start,end):
    picked=d.index[(p>=thr)&(d.entry_time>=start)&(d.entry_time<end)]
    active=pd.Timestamp.min.tz_localize("UTC");ts=[]
    for st in picked:
        o=outs[st]
        if o.entry_time<=active:
            continue
        ts.append(o);active=o.exit_time
    n=len(ts);w=sum(o.outcome=="TP" for o in ts);days=(end-start).total_seconds()/86400
    return {"n":n,"wr":w/n if n else np.nan,"tpd":n/days,
            "exp":float(np.mean([o.net for o in ts])) if n else np.nan,
            "pnl":float(np.sum([o.pnl for o in ts])) if n else 0.0,
            "timeouts":sum(o.outcome=="TIME" for o in ts)}

def main():
    wf1.v3.v1.base.fetch_one=wf1.v3.v1.fetch_one_with_volume
    x5,cov=wf1.v3.v1.base.load5("SOLUSDT")
    if cov<.995:
        raise RuntimeError("coverage too low")
    x5=x5.sort_index()
    q,cols=features(x5)
    outs=outcomes(q,x5)
    d=dataset(q,cols,outs)
    end26=min(pd.Timestamp("2026-09-24",tz="UTC"),x5.index[-1]+pd.Timedelta(minutes=5))
    train=d[(d.entry_time>=T0)&(d.entry_time<T1)&(d.exit_time<T1)]
    val=d[(d.entry_time>=T1)&(d.entry_time<T2)&(d.exit_time<T2)]
    r25=d[(d.entry_time>=T2)&(d.entry_time<T3)&(d.exit_time<T3)]
    r26=d[(d.entry_time>=T3)&(d.entry_time<end26)]
    if min(len(train),len(val),len(r25),len(r26))<1000:
        raise RuntimeError("partition too small")

    cand=[];models={}
    for depth,leaf in CFGS:
        m=RandomForestClassifier(n_estimators=240,max_depth=depth,min_samples_leaf=leaf,max_features="sqrt",random_state=42,n_jobs=-1)
        m.fit(train[cols].astype(float),train.y)
        models[(depth,leaf)]=m
        p=m.predict_proba(val[cols].astype(float))[:,1]
        for qt in QS:
            th=float(np.quantile(p,qt))
            z=ev(val,p,th,outs,T1,T2)
            if z["tpd"]>=1:
                cand.append({"depth":depth,"leaf":leaf,"quantile":qt,"threshold":th,**z})
    c=pd.DataFrame(cand)
    if c.empty:
        raise RuntimeError("no >=1/day validation threshold")
    c=c.sort_values(["wr","exp","tpd"],ascending=[False,False,False]).reset_index(drop=True)
    ch=c.iloc[0]
    m=models[(int(ch.depth),int(ch.leaf))];th=float(ch.threshold)
    metrics={}
    for name,z,s,e in (("VAL2024",val,T1,T2),("REF2025",r25,T2,T3),("REF2026",r26,T3,end26)):
        p=m.predict_proba(z[cols].astype(float))[:,1]
        metrics[name]=ev(z,p,th,outs,s,e)
    full=all(x["wr"]>=.70 and x["tpd"]>=1 and x["exp"]>0 for x in metrics.values())

    imp=pd.DataFrame({"feature":cols,"importance":m.feature_importances_}).sort_values("importance",ascending=False)
    pv=m.predict_proba(val[cols].astype(float))[:,1]
    sel=val[pv>=th]
    prof=[]
    for f in imp.head(15).feature:
        prof.append({"feature":f,"importance":float(imp.loc[imp.feature==f,"importance"].iloc[0]),
                     "all_median":float(val[f].median()),"selected_median":float(sel[f].median()),
                     "shift":float(sel[f].median()-val[f].median())})
    prof=pd.DataFrame(prof)

    c.head(100).to_csv(ROOT/(PFX+"_ValidationThresholds.csv"),index=False)
    imp.to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)
    prof.to_csv(ROOT/(PFX+"_SelectedProfile.csv"),index=False)
    pd.DataFrame([{"partition":k,**v} for k,v in metrics.items()]).to_csv(ROOT/(PFX+"_Transfer.csv"),index=False)

    lines=["# SOL 15M Character Mining V3 — Result","",
           f"- 5m coverage: **{cov*100:.5f}%**",
           f"- train 2023 rows: **{len(train):,}**",
           f"- validation 2024 rows: **{len(val):,}**",
           f"- reference 2025 rows: **{len(r25):,}**",
           f"- reference 2026 rows: **{len(r26):,}**","",
           "Economics: **TP +1.0% / SL -1.0% (RR 1:1), 0.15% RT cost, USD500 notional.**","",
           "## Selected on 2024 only","",
           f"- RF depth **{int(ch.depth)}**, min leaf **{int(ch.leaf)}**",
           f"- quantile **{float(ch['quantile']):.3f}**, threshold **{th:.6f}**",
           f"- 2024 WR **{ch.wr*100:.2f}%**, frequency **{ch.tpd:.3f}/day**, net exp **{ch.exp:.4f}%/trade**","",
           "## Frozen transfer","",
           "|Partition|N|WR|Trades/day|Net exp/trade|PnL USD500|Timeouts|",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("VAL2024","REF2025","REF2026"):
        x=metrics[name]
        lines.append(f"|{name}|{x['n']}|{x['wr']*100:.2f}%|{x['tpd']:.3f}|{x['exp']:.4f}%|{x['pnl']:.2f}|{x['timeouts']}|")
    lines += ["","## Top structural predictors","",
              "|Feature|Importance|All median|Selected median|Shift|","|---|---:|---:|---:|---:|"]
    for _,r in prof.head(12).iterrows():
        lines.append(f"|{r.feature}|{r.importance:.4f}|{r.all_median:.4f}|{r.selected_median:.4f}|{r['shift']:+.4f}|")
    verdict="FULL_TARGET_PASS_FOUND" if full else "NO_FULL_PASS__LEARNED_CHARACTER_FRONTIER"
    lines += ["", "# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
