#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
from scipy.special import logsumexp

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_EXTERNAL_EVENT_DETECTORS_V8"
SYMBOL="SOLUSDT"
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")
COST=0.15
NOTIONAL=500.0
HOLD5=288
EXITS=((1.0,1.0),(1.5,1.0),(1.5,1.5),(2.0,1.0),(2.0,1.5),(2.0,2.0),(3.0,1.5),(3.0,2.0),(3.0,3.0))
_X5_CACHE=None
_OUTCOME_CACHE={}

def resample_complete(x5):
    z=x5.resample("15min",label="left",closed="left").agg(
        open=("open","first"),high=("high","max"),low=("low","min"),
        close=("close","last"),n=("close","count"))
    return z[z.n==3].drop(columns=["n"]).dropna().copy()

def cusum_up(logret,vol,alpha):
    out=np.zeros(len(logret),dtype=bool)
    sp=0.0;sn=0.0
    rv=logret.to_numpy(float);vv=vol.to_numpy(float)
    for i,(r,v) in enumerate(zip(rv,vv)):
        if not np.isfinite(r) or not np.isfinite(v) or v<=0:
            continue
        h=alpha*v
        sp=max(0.0,sp+r);sn=min(0.0,sn+r)
        if sp>=h:
            out[i]=True;sp=0.0;sn=0.0
        elif sn<=-h:
            sp=0.0;sn=0.0
    return out

def directional_change_up(close,theta):
    p=close.to_numpy(float)
    out=np.zeros(len(p),dtype=bool)
    if len(p)==0:return out
    event_type=None
    ext=p[0]
    for i in range(1,len(p)):
        cur=p[i]
        ch=(cur-ext)/ext
        if event_type=="upturn":
            if ch<=-theta:
                event_type="downturn";ext=cur
            elif cur>ext:
                ext=cur
        elif event_type=="downturn":
            if ch>=theta:
                out[i]=True
                event_type="upturn";ext=cur
            elif cur<ext:
                ext=cur
        else:
            if ch>=theta:
                out[i]=True
                event_type="upturn";ext=cur
            elif ch<=-theta:
                event_type="downturn";ext=cur
    return out

def page_hinkley_up(z,delta,threshold,min_instances=32,alpha=.9999):
    x=z.to_numpy(float)
    out=np.zeros(len(x),dtype=bool)
    n=0;mean=0.0;sum_inc=0.0;min_inc=float("inf")
    for i,val in enumerate(x):
        if not np.isfinite(val):
            continue
        n+=1
        mean += (val-mean)/n
        dev=val-mean
        sum_inc=alpha*sum_inc+dev-delta
        if sum_inc<min_inc:min_inc=sum_inc
        if n>=min_instances and (sum_inc-min_inc)>threshold:
            out[i]=True
            n=0;mean=0.0;sum_inc=0.0;min_inc=float("inf")
    return out

def bocd_up(z,ret4,hazard,max_run=256):
    x=z.to_numpy(float);r4=ret4.to_numpy(float)
    out=np.zeros(len(x),dtype=bool)
    log_r=np.array([0.0],dtype=float)
    means=np.array([0.0],dtype=float)
    precs=np.array([1.0],dtype=float)
    logh=math.log(hazard);log1=math.log(1-hazard)
    prev_mode=0
    log2pi=math.log(2*math.pi)
    for i,val in enumerate(x):
        if not np.isfinite(val):
            continue
        varpred=1.0+1.0/precs
        logpred=-0.5*(log2pi+np.log(varpred)+((val-means)**2)/varpred)
        growth=log_r+logpred+log1
        cp=logsumexp(log_r+logpred+logh)
        newlog=np.concatenate(([cp],growth))
        newprec=np.concatenate(([1.0],precs+1.0))
        newmean=np.concatenate(([0.0],(means*precs+val)/(precs+1.0)))
        if len(newlog)>max_run+1:
            newlog=newlog[:max_run+1];newprec=newprec[:max_run+1];newmean=newmean[:max_run+1]
        newlog-=logsumexp(newlog)
        mode=int(np.argmax(newlog))
        if prev_mode>=16 and mode<=3 and np.isfinite(r4[i]) and r4[i]>0:
            out[i]=True
        prev_mode=mode
        log_r,precs,means=newlog,newprec,newmean
    return out

def period_bounds(end):
    return {
        "2023":(pd.Timestamp("2023-01-01",tz="UTC"),pd.Timestamp("2024-01-01",tz="UTC")),
        "2024":(pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2025-01-01",tz="UTC")),
        "2025":(pd.Timestamp("2025-01-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
        "2026":(pd.Timestamp("2026-01-01",tz="UTC"),end),
    }

def week_start(ts):
    t=pd.Timestamp(ts)
    return (t-pd.Timedelta(days=t.weekday())).normalize()

def weeks_between(start,end):
    return pd.date_range(week_start(start),week_start(end-pd.Timedelta(seconds=1)),freq="7D",tz="UTC")

def resolve_signal(st,x5,tp,sl):
    global _X5_CACHE,_OUTCOME_CACHE
    key=(int(pd.Timestamp(st).value),float(tp),float(sl))
    if key in _OUTCOME_CACHE:
        return _OUTCOME_CACHE[key]
    if _X5_CACHE is None:
        _X5_CACHE=(x5.index,x5.open.astype(float).to_numpy(),x5.high.astype(float).to_numpy(),
                   x5.low.astype(float).to_numpy(),x5.close.astype(float).to_numpy())
    idx,O,H,L,C=_X5_CACHE
    p=int(idx.searchsorted(st+pd.Timedelta(minutes=15)))
    if p>=len(idx) or idx[p]!=st+pd.Timedelta(minutes=15):
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
    out={"signal_time":st,"entry_time":idx[p],"exit_time":idx[ex],"outcome":reason,
         "win":int(reason=="TP"),"net":net,"pnl":net/100*NOTIONAL}
    _OUTCOME_CACHE[key]=out
    return out

def simulate(signal_times,x5,tp,sl,start,end):
    active=pd.Timestamp.min.tz_localize("UTC");rows=[]
    for st in signal_times:
        z=resolve_signal(st,x5,tp,sl)
        if z is None:continue
        if z["entry_time"]<start or z["entry_time"]>=end or z["entry_time"]<=active:continue
        rows.append(z);active=z["exit_time"]
    return pd.DataFrame(rows)

def metrics(tr,start,end):
    weeks=weeks_between(start,end);w=pd.Series(0.0,index=weeks)
    if len(tr):
        for _,r in tr.iterrows():
            ww=week_start(r.entry_time)
            if ww in w.index:w.loc[ww]+=float(r.net)
    n=len(tr);wins=int(tr.win.sum()) if n else 0
    days=(end-start).total_seconds()/86400
    return {"n":n,"wr":wins/n if n else np.nan,"trades_day":n/days if days else np.nan,
            "trades_week":n/len(weeks) if len(weeks) else np.nan,
            "exp":float(tr.net.mean()) if n else np.nan,"pnl":float(tr.pnl.sum()) if n else 0.0,
            "weekly_mean":float(w.mean()),"weekly_median":float(w.median())}

def build_context(x5,end,q15):
    print("load external derivatives context",flush=True)
    flow,_=v3.load_flow15(end)
    metric_df,_=v3.load_metrics(end)
    funding,_=v3.load_funding(end)
    q,_=v1.build_features(x5)
    q=v3.join_external(q,flow,metric_df,funding)
    q,states=v4.build_states(q)
    state=states["NEW_LONG_BUILD"].reindex(q15.index).fillna(False)
    return state

def main():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(END_CAP,x5.index[-1]+pd.Timedelta(minutes=5))
    q=resample_complete(x5)
    q=q[(q.index>=pd.Timestamp("2022-12-01",tz="UTC"))&(q.index<end)].copy()
    logp=np.log(q.close.astype(float))
    lr=logp.diff()
    vol=lr.shift(1).rolling(96,min_periods=48).std()
    z=lr/vol.replace(0,np.nan)
    ret4=q.close.pct_change(4)
    state=build_context(x5,end,q)

    detectors=[]
    for a in (1.0,1.5,2.0,2.5,3.0):
        detectors.append(("CUSUM_UP",f"alpha={a:g}",cusum_up(lr,vol,a)))
    for th in (.005,.0075,.01,.0125,.015):
        detectors.append(("DIRECTIONAL_CHANGE_UP",f"theta={th*100:.2f}%",directional_change_up(q.close,th)))
    for d,t in ((0.0,5.0),(.05,5.0),(.05,10.0),(.10,10.0),(.10,15.0)):
        detectors.append(("PAGE_HINKLEY_UP",f"delta={d:g},lambda={t:g}",page_hinkley_up(z,d,t)))
    for h in (1/48,1/96,1/192):
        print("BOCD hazard",h,flush=True)
        detectors.append(("BOCD_UP",f"hazard=1/{round(1/h)}",bocd_up(z,ret4,h)))

    bounds=period_bounds(end)
    grid=[]
    for family,param,mask in detectors:
        base=pd.Series(mask,index=q.index).fillna(False)
        for cmode in ("EVENT_ONLY","EVENT_IN_NEW_LONG_STATE"):
            m=base if cmode=="EVENT_ONLY" else (base&state)
            sig=q.index[m.to_numpy()]
            for tp,sl in EXITS:
                row={"family":family,"param":param,"context":cmode,"tp":tp,"sl":sl,"rr":tp/sl,
                     "raw_events":int(m.sum())}
                for yr,(a,b) in bounds.items():
                    tr=simulate(sig,x5,tp,sl,a,b)
                    mm=metrics(tr,a,b)
                    for k,v in mm.items():row[f"{yr}_{k}"]=v
                grid.append(row)
    g=pd.DataFrame(grid)
    g.to_csv(ROOT/(PFX+"_Grid.csv"),index=False)

    selected=[]
    for family in g.family.unique():
        zf=g[g.family==family].copy()
        elig=zf[(zf["2023_trades_day"]>=1)&(zf["2023_exp"]>0)].copy()
        if len(elig):
            rank=elig.sort_values(["2023_wr","2023_exp","2023_trades_day"],ascending=[False,False,False])
            status="ELIGIBLE_2023"
        else:
            freq=zf[zf["2023_trades_day"]>=1].copy()
            rank=(freq if len(freq) else zf).sort_values(["2023_wr","2023_exp","2023_trades_day"],ascending=[False,False,False])
            status="NO_POSITIVE_2023"
        ch=rank.iloc[0].copy()
        full=bool(ch["2024_wr"]>=.70 and ch["2024_trades_day"]>=1 and ch["2024_exp"]>0)
        near=bool(ch["2024_wr"]>=.65 and ch["2024_trades_day"]>=1 and ch["2024_exp"]>0)
        rec=ch.to_dict();rec["selection_status"]=status;rec["full_gate_2024"]=full;rec["near_gate_2024"]=near
        selected.append(rec)
    sel=pd.DataFrame(selected)
    sel.to_csv(ROOT/(PFX+"_SelectedFamilies.csv"),index=False)

    promotable=sel[sel.full_gate_2024|sel.near_gate_2024].copy()
    if len(promotable):
        champ=promotable.sort_values(["full_gate_2024","2024_wr","2024_exp","2024_trades_day"],ascending=[False,False,False,False]).iloc[0]
        verdict="EXTERNAL_EVENT_PROMOTABLE__"+str(champ.family)
    else:
        champ=sel.sort_values(["2024_wr","2024_exp","2024_trades_day"],ascending=[False,False,False]).iloc[0]
        verdict="NO_EXTERNAL_EVENT_GATE_PASS_V8"

    lines=["# SOL External Event Detectors V8 — Result","",
           f"- 5m coverage: **{cov*100:.5f}%**",
           f"- complete 15m bars in research window: **{len(q):,}**",
           "- families: **CUSUM / Directional Change / Page-Hinkley / BOCD**",
           "- all family parameters/exits/context modes selected on **2023 only**",
           "","## Frozen family candidates","",
           "|Family|2023-selected trigger|Context|TP/SL|2023 WR/day/exp|2024 WR/day/exp|2025 WR/day/exp|2026 WR/day/exp|2024 gate|",
           "|---|---|---|---|---|---|---|---|---|"]
    for _,r in sel.iterrows():
        gate="FULL" if r.full_gate_2024 else ("NEAR" if r.near_gate_2024 else "NO")
        lines.append("|%s|%s|%s|%.1f/%.1f|%.1f%% / %.2f / %+.3f%%|%.1f%% / %.2f / %+.3f%%|%.1f%% / %.2f / %+.3f%%|%.1f%% / %.2f / %+.3f%%|%s|"%(
            r.family,r.param,r.context,r.tp,r.sl,
            r["2023_wr"]*100,r["2023_trades_day"],r["2023_exp"],
            r["2024_wr"]*100,r["2024_trades_day"],r["2024_exp"],
            r["2025_wr"]*100,r["2025_trades_day"],r["2025_exp"],
            r["2026_wr"]*100,r["2026_trades_day"],r["2026_exp"],gate))
    lines+=["","## Best 2024 frozen candidate","",
            f"- family: **{champ.family}**",
            f"- trigger: **{champ.param}**",
            f"- context: **{champ.context}**",
            f"- exit: **TP {champ.tp:.1f}% / SL {champ.sl:.1f}% (RR {champ.rr:.2f})**",
            f"- 2024: **{champ['2024_wr']*100:.2f}% WR**, **{champ['2024_trades_day']:.2f}/day**, **{champ['2024_exp']:+.3f}% exp/trade**",
            "",f"# VERDICT: {verdict}"]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
