#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4
import sol_dc_overshoot_anatomy_v9 as v9

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_DC_OVERSHOOT_DETECTOR_V10"
SYMBOL="SOLUSDT"
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")
T0=pd.Timestamp("2023-01-01",tz="UTC")
T1=pd.Timestamp("2024-01-01",tz="UTC")
T2=pd.Timestamp("2025-01-01",tz="UTC")
T3=pd.Timestamp("2026-01-01",tz="UTC")
THETA=.005
COST=.15
NOTIONAL=500.0
HOLD5=288
QUANTILES=(.50,.60,.70,.75,.80,.85,.90,.925,.95,.96,.97,.98,.985,.99)

FEATURES={
    "OS2":["ret1","dist_ema20","ema20_slope","bars_peak_trough"],
    "OS3":["ret1","up_amp_pct","ret4","atr_pct","ret8","bars_trough_confirm","bars_peak_trough"],
}
TARGETS={
    "OS2":{"label":"os2","tp":2.0,"sl":2.0},
    "OS3":{"label":"os3","tp":3.0,"sl":3.0},
}

def week_start(ts):
    t=pd.Timestamp(ts)
    return (t-pd.Timedelta(days=t.weekday())).normalize()

def weeks_between(start,end):
    return pd.date_range(week_start(start),week_start(end-pd.Timedelta(seconds=1)),freq="7D",tz="UTC")

def build_dataset():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:
        raise RuntimeError(f"5m coverage too low: {cov:.6%}")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:
            x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(END_CAP,x5.index[-1]+pd.Timedelta(minutes=5))

    print("load causal derivatives context",flush=True)
    flow,_=v3.load_flow15(end)
    metric_df,_=v3.load_metrics(end)
    funding,_=v3.load_funding(end)
    q,_=v1.build_features(x5)
    q=v3.join_external(q,flow,metric_df,funding)
    q,states=v4.build_states(q)
    q=q[(q.index>=pd.Timestamp("2022-12-01",tz="UTC"))&(q.index<end)].copy()

    ev=v9.dc_events(q.close,THETA)
    up=ev[(ev.kind=="UP")&(ev.signal_time>=T0)&(ev.signal_time<end)].copy()
    state=states["NEW_LONG_BUILD"].reindex(q.index).fillna(False)
    up=up[state.reindex(pd.DatetimeIndex(up.signal_time)).fillna(False).to_numpy()]
    lab=v9.attach_overshoot_labels(up,x5)
    if lab.empty:
        raise RuntimeError("no DC overshoot cycles")
    lab.index=pd.DatetimeIndex(lab.signal_time)

    needed=sorted(set(FEATURES["OS2"]+FEATURES["OS3"]))
    qjoin=q[[c for c in needed if c in q.columns]].reindex(lab.index)
    for c in needed:
        if c in lab.columns:
            continue
        if c not in qjoin.columns:
            raise RuntimeError(f"missing frozen feature {c}")
        lab[c]=qjoin[c].to_numpy()
    lab["year"]=lab.signal_time.dt.year
    lab=lab[(lab.signal_time>=T0)&(lab.signal_time<end)].copy()
    return x5,lab,end,cov

_OUTCOME_CACHE={}
_X5_CACHE=None

def resolve(st,x5,tp,sl):
    global _X5_CACHE,_OUTCOME_CACHE
    key=(int(pd.Timestamp(st).value),float(tp),float(sl))
    if key in _OUTCOME_CACHE:
        return _OUTCOME_CACHE[key]
    if _X5_CACHE is None:
        _X5_CACHE=(x5.index,x5.open.astype(float).to_numpy(),x5.high.astype(float).to_numpy(),
                   x5.low.astype(float).to_numpy(),x5.close.astype(float).to_numpy())
    idx,O,H,L,C=_X5_CACHE
    et=pd.Timestamp(st)+pd.Timedelta(minutes=15)
    p=int(idx.searchsorted(et))
    if p>=len(idx) or idx[p]!=et:
        _OUTCOME_CACHE[key]=None
        return None
    entry=float(O[p]);T=entry*(1+tp/100);S=entry*(1-sl/100)
    last=min(p+HOLD5-1,len(idx)-1)
    ex=last;reason="TIME";gross=(float(C[last])/entry-1)*100
    for j in range(p,last+1):
        ht=H[j]>=T;hs=L[j]<=S
        if ht and hs:
            reason="SL_AMBIG";gross=-sl;ex=j;break
        if hs:
            reason="SL";gross=-sl;ex=j;break
        if ht:
            reason="TP";gross=tp;ex=j;break
    net=gross-COST
    out={"signal_time":pd.Timestamp(st),"entry_time":idx[p],"exit_time":idx[ex],
         "outcome":reason,"win":int(reason=="TP"),"net":net,"pnl":net/100*NOTIONAL}
    _OUTCOME_CACHE[key]=out
    return out

def simulate(signal_times,x5,tp,sl,start,end):
    active=pd.Timestamp.min.tz_localize("UTC")
    rows=[]
    for st in sorted(pd.to_datetime(signal_times,utc=True)):
        o=resolve(st,x5,tp,sl)
        if o is None:
            continue
        if o["entry_time"]<start or o["entry_time"]>=end or o["entry_time"]<=active:
            continue
        rows.append(o);active=o["exit_time"]
    return pd.DataFrame(rows)

def metrics(tr,start,end):
    weeks=weeks_between(start,end)
    weekly=pd.Series(0.0,index=weeks)
    if len(tr):
        for _,r in tr.iterrows():
            w=week_start(r.entry_time)
            if w in weekly.index:
                weekly.loc[w]+=float(r.net)
    n=len(tr);wins=int(tr.win.sum()) if n else 0
    days=(end-start).total_seconds()/86400
    return {
        "n":n,"wr":wins/n if n else np.nan,"trades_day":n/days if days else np.nan,
        "trades_week":n/len(weeks) if len(weeks) else np.nan,
        "exp":float(tr.net.mean()) if n else np.nan,"pnl":float(tr.pnl.sum()) if n else 0.0,
        "weekly_mean":float(weekly.mean()) if len(weeks) else np.nan,
        "weekly_median":float(weekly.median()) if len(weeks) else np.nan,
        "positive_weeks":float((weekly>0).mean()) if len(weeks) else np.nan,
    }

def prep(train,other,features):
    med={}
    for c in features:
        x=pd.to_numeric(train[c],errors="coerce").replace([np.inf,-np.inf],np.nan)
        med[c]=float(x.median())
    def make(df):
        return pd.DataFrame({
            c:pd.to_numeric(df[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c])
            for c in features
        },index=df.index)
    return make(train),make(other),med

def model_family():
    return {
        "LOGIT":Pipeline([
            ("scale",StandardScaler()),
            ("model",LogisticRegression(C=1.0,class_weight="balanced",max_iter=2000,random_state=314))
        ]),
        "TREE":DecisionTreeClassifier(max_depth=2,min_samples_leaf=50,class_weight="balanced",random_state=314),
        "RF":RandomForestClassifier(n_estimators=300,max_depth=4,min_samples_leaf=50,max_features="sqrt",
                                    class_weight="balanced_subsample",random_state=314,n_jobs=-1),
    }

def evaluate_target(name,spec,features,df,x5,end):
    label=spec["label"];tp=spec["tp"];sl=spec["sl"]
    train=df[(df.signal_time>=T0)&(df.signal_time<T1)].copy()
    val=df[(df.signal_time>=T1)&(df.signal_time<T2)].copy()
    r25=df[(df.signal_time>=T2)&(df.signal_time<T3)].copy()
    r26=df[(df.signal_time>=T3)&(df.signal_time<end)].copy()
    if min(len(train),len(val),len(r25),len(r26))<100:
        raise RuntimeError(f"partition too small for {name}")

    Xtr,Xval,med=prep(train,val,features)
    X25=pd.DataFrame({c:pd.to_numeric(r25[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features},index=r25.index)
    X26=pd.DataFrame({c:pd.to_numeric(r26[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features},index=r26.index)
    y=train[label].astype(int)

    grid=[];fitted={}
    for mname,model in model_family().items():
        model.fit(Xtr,y);fitted[mname]=model
        pv=model.predict_proba(Xval)[:,1]
        for q in QUANTILES:
            th=float(np.quantile(pv,q))
            sig=val.loc[pv>=th,"signal_time"].tolist()
            tr=simulate(sig,x5,tp,sl,T1,T2)
            mm=metrics(tr,T1,T2)
            grid.append({"target":name,"model":mname,"quantile":q,"threshold":th,
                         "selected_events":len(sig),**mm})
    g=pd.DataFrame(grid)
    elig=g[(g.trades_day>=1)&(g.exp>0)].copy()
    if len(elig):
        rank=elig.sort_values(["wr","exp","weekly_mean","n"],ascending=[False,False,False,False])
        status="ELIGIBLE_2024"
    else:
        freq=g[g.trades_day>=1].copy()
        rank=(freq if len(freq) else g).sort_values(["wr","exp","weekly_mean","n"],ascending=[False,False,False,False])
        status="NO_POSITIVE_DAILY_2024"
    ch=rank.iloc[0]
    model=fitted[str(ch.model)];th=float(ch.threshold)

    transfer=[]
    for pname,part,X,a,b in (
        ("VAL2024",val,Xval,T1,T2),
        ("REF2025",r25,X25,T2,T3),
        ("REF2026",r26,X26,T3,end),
    ):
        p=model.predict_proba(X)[:,1]
        sig=part.loc[p>=th,"signal_time"].tolist()
        tr=simulate(sig,x5,tp,sl,a,b)
        mm=metrics(tr,a,b)
        transfer.append({"target":name,"partition":pname,"model":str(ch.model),
                         "threshold":th,"quantile":float(ch["quantile"]),"tp":tp,"sl":sl,
                         "selected_events":len(sig),**mm})

    tdf=pd.DataFrame(transfer)
    full=bool(((tdf.wr>=.70)&(tdf.trades_day>=1)&(tdf.exp>0)).all())
    selected={"target":name,"status":status,"model":str(ch.model),"quantile":float(ch["quantile"]),
              "threshold":th,"tp":tp,"sl":sl,"full_gate":full,
              "val_wr":float(ch.wr),"val_trades_day":float(ch.trades_day),"val_exp":float(ch.exp)}
    return g,tdf,selected

def main():
    x5,df,end,cov=build_dataset()
    df.to_csv(ROOT/(PFX+"_Events.csv"),index=False)

    grids=[];transfers=[];selected=[]
    for name,spec in TARGETS.items():
        g,t,s=evaluate_target(name,spec,FEATURES[name],df,x5,end)
        grids.append(g);transfers.append(t);selected.append(s)
    grid=pd.concat(grids,ignore_index=True)
    transfer=pd.concat(transfers,ignore_index=True)
    sel=pd.DataFrame(selected)
    grid.to_csv(ROOT/(PFX+"_Grid2024.csv"),index=False)
    transfer.to_csv(ROOT/(PFX+"_Transfer.csv"),index=False)
    sel.to_csv(ROOT/(PFX+"_Selected.csv"),index=False)

    passed=sel[sel.full_gate]
    verdict="V10_DETECTOR_GATE_PASS__"+"__".join(passed.target.tolist()) if len(passed) else "NO_V10_DETECTOR_GATE_PASS"

    lines=["# SOL DC Overshoot Detector V10 — Result","",
           f"- 5m coverage: **{cov*100:.5f}%**",
           f"- total frozen DC-context cycles through 2026: **{len(df):,}**",
           "","## Frozen detector transfer","",
           "|Target|Partition|Model|WR|Trades/day|Exp/trade|Mean weekly|N|",
           "|---|---|---|---:|---:|---:|---:|---:|"]
    for _,r in transfer.iterrows():
        lines.append(f"|{r.target}|{r.partition}|{r.model}|{r.wr*100:.2f}%|{r.trades_day:.3f}|{r.exp:+.3f}%|{r.weekly_mean:+.2f}%|{int(r.n)}|")
    lines+=["","## Selection",""]
    for _,r in sel.iterrows():
        lines.append(f"- **{r.target}**: {r.status}; {r.model}, q={r['quantile']:.3f}; 2024 WR {r.val_wr*100:.2f}%, {r.val_trades_day:.3f}/day, exp {r.val_exp:+.3f}%; full gate={'YES' if r.full_gate else 'NO'}.")
    lines+=["",f"# VERDICT: {verdict}"]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
