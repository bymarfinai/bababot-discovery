#!/usr/bin/env python3
from __future__ import annotations

import io, json, math, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeClassifier

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_AGGTRADE_IGNITION_V7B"
SYMBOL="SOLUSDT"
END=pd.Timestamp("2025-01-01",tz="UTC")
COST=0.15
TP=2.0
SL=2.0
HOLD5=288
NOTIONAL=500.0
QUANTILES=(.50,.60,.70,.75,.80,.85,.90,.925,.95,.96,.97,.98,.985,.99)
UA={"User-Agent":"bababot-sol-v7b/1.0"}
BASE="https://data.binance.vision/data/futures/um/daily/aggTrades/SOLUSDT"

def week_start(ts):
    t=pd.Timestamp(ts)
    return (t-pd.Timedelta(days=t.weekday())).normalize()

def weeks_between(start,end):
    return pd.date_range(week_start(start),week_start(end-pd.Timedelta(seconds=1)),freq="7D",tz="UTC")

def single_outcome(st,x5):
    idx=x5.index
    et=st+pd.Timedelta(minutes=15)
    p=int(idx.searchsorted(et))
    if p>=len(idx) or idx[p]!=et:return None
    O=x5.open.astype(float).to_numpy();H=x5.high.astype(float).to_numpy();L=x5.low.astype(float).to_numpy();C=x5.close.astype(float).to_numpy()
    entry=float(O[p]);tp=entry*(1+TP/100);sl=entry*(1-SL/100)
    last=min(p+HOLD5-1,len(idx)-1)
    ex=last;reason="TIME";gross=(float(C[last])/entry-1)*100
    for j in range(p,last+1):
        ht=H[j]>=tp;hs=L[j]<=sl
        if ht and hs:
            reason="SL_AMBIG";gross=-SL;ex=j;break
        if hs:
            reason="SL";gross=-SL;ex=j;break
        if ht:
            reason="TP";gross=TP;ex=j;break
    net=gross-COST
    return {"entry_time":idx[p],"exit_time":idx[ex],"entry":entry,"reason":reason,
            "win":int(reason=="TP"),"gross":gross,"net":net,"pnl":net/100*NOTIONAL}

def load_events():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError(f"5m coverage too low {cov}")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    print("load 15m flow",flush=True);flow,_=v3.load_flow15(END)
    print("load derivatives metrics",flush=True);metric_df,_=v3.load_metrics(END)
    print("load funding",flush=True);funding,_=v3.load_funding(END)
    q,_=v1.build_features(x5)
    q=v3.join_external(q,flow,metric_df,funding)
    q,states=v4.build_states(q)
    parent=states["NEW_LONG_BUILD"].fillna(False)
    edge=parent & (~parent.shift(1).fillna(False))
    times=q.index[edge.to_numpy()]
    times=times[(times>=v1.T0)&(times<v1.T2)]
    rows=[]
    for i,st in enumerate(times):
        o=single_outcome(st,x5)
        if o is None:continue
        rows.append({"event_id":i,"signal_time":st,"year":st.year,"day":st.strftime("%Y-%m-%d"),**o})
    ev=pd.DataFrame(rows).sort_values("signal_time").reset_index(drop=True)
    return x5,ev,cov

def max_run(side):
    if len(side)==0:return np.nan
    if len(side)==1:return 1.0
    changes=np.flatnonzero(side[1:]!=side[:-1])+1
    lens=np.diff(np.r_[0,changes,len(side)])
    return float(lens.max()) if len(lens) else float(len(side))

def slice_stats(t,p,q,side,lo,hi,prefix):
    a=int(np.searchsorted(t,lo,"left"));b=int(np.searchsorted(t,hi,"left"))
    if b<=a:
        return {f"{prefix}_{k}":np.nan for k in (
            "buy_quote","sell_quote","total_quote","delta","delta_ratio","count","count_imb",
            "price_ret","price_per_delta","top5_share","max_run","flip_rate","inter_ms_median")}
    tt=t[a:b];pp=p[a:b];qq=q[a:b];ss=side[a:b]
    buy=ss>0;sell=ss<0
    bq=float(qq[buy].sum());sq=float(qq[sell].sum());tot=bq+sq;delta=bq-sq
    n=len(ss);bn=int(buy.sum());sn=int(sell.sum())
    dr=delta/tot if tot>0 else np.nan
    ret=float(pp[-1]/pp[0]-1) if len(pp)>1 and pp[0]>0 else 0.0
    eff=ret/abs(dr) if np.isfinite(dr) and abs(dr)>1e-12 else np.nan
    k=max(1,int(math.ceil(.05*n)))
    top=float(np.partition(qq,n-k)[n-k:].sum()/tot) if n and tot>0 else np.nan
    flip=float(np.mean(ss[1:]!=ss[:-1])) if n>1 else 0.0
    inter=float(np.median(np.diff(tt))) if n>1 else np.nan
    return {
        f"{prefix}_buy_quote":bq,f"{prefix}_sell_quote":sq,f"{prefix}_total_quote":tot,
        f"{prefix}_delta":delta,f"{prefix}_delta_ratio":dr,f"{prefix}_count":float(n),
        f"{prefix}_count_imb":(bn-sn)/n if n else np.nan,
        f"{prefix}_price_ret":ret,f"{prefix}_price_per_delta":eff,
        f"{prefix}_top5_share":top,f"{prefix}_max_run":max_run(ss),
        f"{prefix}_flip_rate":flip,f"{prefix}_inter_ms_median":inter,
    }

def quick_stats(t,q,side,lo,hi):
    a=int(np.searchsorted(t,lo,"left"));b=int(np.searchsorted(t,hi,"left"))
    if b<=a:return {"n":0,"quote":0.0,"dr":np.nan}
    qq=q[a:b];ss=side[a:b];buy=ss>0;sell=ss<0
    bq=float(qq[buy].sum());sq=float(qq[sell].sum());tot=bq+sq
    return {"n":b-a,"quote":tot,"dr":(bq-sq)/tot if tot>0 else np.nan}

def parse_day(ds,events):
    url=f"{BASE}/SOLUSDT-aggTrades-{ds}.zip"
    err=None
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=90,headers=UA)
            if r.status_code==404:return [],{"day":ds,"status":404,"events":len(events),"covered":0}
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:raise RuntimeError("no csv in zip")
                with zf.open(names[0]) as fh:df=pd.read_csv(fh)
            break
        except Exception as e:
            err=f"{type(e).__name__}: {e}"
            if attempt==2:return [],{"day":ds,"status":"ERR","error":err,"events":len(events),"covered":0}
            time.sleep(1.5*(attempt+1))
    df.columns=[str(c).strip().lower() for c in df.columns]
    aliases={
        "price":["price"],"qty":["quantity","qty"],"time":["transact_time","time","timestamp"],
        "maker":["is_buyer_maker","m"]
    }
    col={}
    for k,opts in aliases.items():
        for o in opts:
            if o in df.columns:col[k]=o;break
    if len(col)<4:
        return [],{"day":ds,"status":"SCHEMA","columns":";".join(df.columns),"events":len(events),"covered":0}
    t=pd.to_numeric(df[col["time"]],errors="coerce").to_numpy()
    med=np.nanmedian(t)
    if med>1e14:t=t/1000.0
    t=t.astype(np.int64)
    p=pd.to_numeric(df[col["price"]],errors="coerce").to_numpy(float)
    qty=pd.to_numeric(df[col["qty"]],errors="coerce").to_numpy(float)
    q=p*qty
    mk=df[col["maker"]]
    if mk.dtype==bool:maker=mk.to_numpy(bool)
    else:maker=mk.astype(str).str.lower().isin(["true","1","t"]).to_numpy(bool)
    side=np.where(maker,-1,1).astype(np.int8)
    ok=np.isfinite(p)&np.isfinite(q)&(q>=0)
    t=t[ok];p=p[ok];q=q[ok];side=side[ok]
    order=np.argsort(t,kind="stable");t=t[order];p=p[order];q=q[order];side=side[order]
    out=[];covered=0
    for _,e in events.iterrows():
        end=int(pd.Timestamp(e.entry_time).timestamp()*1000)
        start=end-15*60*1000
        base=slice_stats(t,p,q,side,start,end,"ag15")
        if not np.isfinite(base["ag15_count"]) or base["ag15_count"]<=0:
            continue
        covered+=1
        feat=dict(base)
        for sec,label in ((300,"ag5"),(60,"ag1"),(30,"ag30s")):
            feat.update(slice_stats(t,p,q,side,end-sec*1000,end,label))
        prev4=quick_stats(t,q,side,end-5*60*1000,end-60*1000)
        final1=quick_stats(t,q,side,end-60*1000,end)
        prev30=quick_stats(t,q,side,end-60*1000,end-30*1000)
        final30=quick_stats(t,q,side,end-30*1000,end)
        feat["ag_delta_accel_1m_vs_prev4m"]=(final1["dr"]-prev4["dr"]) if np.isfinite(final1["dr"]) and np.isfinite(prev4["dr"]) else np.nan
        feat["ag_delta_accel_30s_vs_prev30s"]=(final30["dr"]-prev30["dr"]) if np.isfinite(final30["dr"]) and np.isfinite(prev30["dr"]) else np.nan
        feat["ag_count_burst_1m_vs_prev4m"]=(final1["n"]/(prev4["n"]/4)) if prev4["n"]>0 else np.nan
        feat["ag_quote_burst_1m_vs_prev4m"]=(final1["quote"]/(prev4["quote"]/4)) if prev4["quote"]>0 else np.nan
        feat["ag_count_burst_30s_vs_prev30s"]=(final30["n"]/prev30["n"]) if prev30["n"]>0 else np.nan
        feat["ag_quote_burst_30s_vs_prev30s"]=(final30["quote"]/prev30["quote"]) if prev30["quote"]>0 else np.nan
        out.append({"event_id":int(e.event_id),**feat})
    return out,{"day":ds,"status":200,"bytes":len(r.content),"events":len(events),"covered":covered}

def extract_features(events):
    groups=[(ds,g.copy()) for ds,g in events.groupby("day",sort=True)]
    rows=[];diag=[];done=0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(parse_day,ds,g):ds for ds,g in groups}
        for f in as_completed(futs):
            rr,dd=f.result();rows.extend(rr);diag.append(dd);done+=1
            if done%50==0:print(f"aggTrades days {done}/{len(groups)} features {len(rows)}",flush=True)
    feat=pd.DataFrame(rows)
    dg=pd.DataFrame(diag)
    return feat,dg

def simulate_selected(signal_times,x5,start,end):
    idx=x5.index;O=x5.open.astype(float).to_numpy();H=x5.high.astype(float).to_numpy();L=x5.low.astype(float).to_numpy();C=x5.close.astype(float).to_numpy()
    active=pd.Timestamp.min.tz_localize("UTC");rows=[]
    for st in sorted(pd.to_datetime(signal_times,utc=True)):
        et=st+pd.Timedelta(minutes=15)
        if et<start or et>=end or et<=active:continue
        p=int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:continue
        entry=float(O[p]);tp=entry*(1+TP/100);sl=entry*(1-SL/100);last=min(p+HOLD5-1,len(idx)-1)
        reason="TIME";gross=(float(C[last])/entry-1)*100;ex=last
        for j in range(p,last+1):
            ht=H[j]>=tp;hs=L[j]<=sl
            if ht and hs:reason="SL_AMBIG";gross=-SL;ex=j;break
            if hs:reason="SL";gross=-SL;ex=j;break
            if ht:reason="TP";gross=TP;ex=j;break
        net=gross-COST
        rows.append({"signal_time":st,"entry_time":idx[p],"exit_time":idx[ex],"reason":reason,"win":int(reason=="TP"),"net":net,"pnl":net/100*NOTIONAL})
        active=idx[ex]
    return pd.DataFrame(rows)

def strat_metrics(tr,start,end):
    weeks=weeks_between(start,end);w=pd.Series(0.0,index=weeks)
    if len(tr):
        for _,r in tr.iterrows():
            ww=week_start(r.entry_time)
            if ww in w.index:w.loc[ww]+=float(r.net)
    n=len(tr);wins=int(tr.win.sum()) if n else 0
    return {"n":n,"wins":wins,"wr":wins/n if n else np.nan,"trades_week":n/len(weeks),
            "exp":float(tr.net.mean()) if n else np.nan,"pnl":float(tr.pnl.sum()) if n else 0.0,
            "weekly_mean":float(w.mean()),"weekly_median":float(w.median()),
            "positive_weeks":float((w>0).mean()),"weeks_ge10":float((w>=10).mean())}

def smd(win,loss):
    a=np.asarray(win,float);b=np.asarray(loss,float)
    a=a[np.isfinite(a)];b=b[np.isfinite(b)]
    if len(a)<5 or len(b)<5:return np.nan
    va=np.var(a,ddof=1);vb=np.var(b,ddof=1);den=math.sqrt(((len(a)-1)*va+(len(b)-1)*vb)/(len(a)+len(b)-2))
    return (np.mean(a)-np.mean(b))/den if den>0 else np.nan

def forensic(df,features):
    rows=[]
    for yr in (2023,2024):
        z=df[df.year==yr]
        for c in features:
            a=pd.to_numeric(z.loc[z.win==1,c],errors="coerce").to_numpy(float)
            b=pd.to_numeric(z.loc[z.win==0,c],errors="coerce").to_numpy(float)
            s=smd(a,b)
            vals=pd.to_numeric(z[c],errors="coerce")
            mask=vals.notna()
            auc=np.nan
            if mask.sum()>20 and z.loc[mask,"win"].nunique()==2:
                try:
                    aa=roc_auc_score(z.loc[mask,"win"],vals[mask]);auc=max(aa,1-aa)
                except Exception:pass
            rows.append({"year":yr,"feature":c,"win_median":float(np.nanmedian(a)) if len(a) else np.nan,
                         "loss_median":float(np.nanmedian(b)) if len(b) else np.nan,"smd":s,"auc_oriented":auc})
    out=pd.DataFrame(rows)
    p=out.pivot(index="feature",columns="year",values="smd")
    stable=[]
    for c in features:
        if c not in p.index or 2023 not in p.columns or 2024 not in p.columns:continue
        a=p.loc[c,2023];b=p.loc[c,2024]
        if pd.notna(a) and pd.notna(b) and abs(a)>=.10 and abs(b)>=.10 and np.sign(a)==np.sign(b):
            stable.append({"feature":c,"smd_2023":a,"smd_2024":b,"min_abs_smd":min(abs(a),abs(b))})
    return out,pd.DataFrame(stable).sort_values("min_abs_smd",ascending=False) if stable else pd.DataFrame(columns=["feature","smd_2023","smd_2024","min_abs_smd"])

def main():
    x5,events,cov=load_events()
    print("parent events",len(events),"2023",int((events.year==2023).sum()),"2024",int((events.year==2024).sum()),flush=True)
    feat,diag=extract_features(events)
    events.to_csv(ROOT/(PFX+"_ParentEvents.csv"),index=False)
    diag.to_csv(ROOT/(PFX+"_DownloadDiagnostics.csv"),index=False)
    if feat.empty:raise RuntimeError("no aggTrade features")
    df=events.merge(feat,on="event_id",how="left")
    df.to_csv(ROOT/(PFX+"_EventFeatures.csv"),index=False)
    covrows=[]
    for yr in (2023,2024):
        z=df[df.year==yr];good=(pd.to_numeric(z.ag15_count,errors="coerce").fillna(0)>0)
        covrows.append({"year":yr,"events":len(z),"covered":int(good.sum()),"coverage":float(good.mean())})
    covdf=pd.DataFrame(covrows);covdf.to_csv(ROOT/(PFX+"_Coverage.csv"),index=False)
    if (covdf.coverage<.95).any():
        verdict="BLOCKED_DATA_COVERAGE"
        (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n")
        print(covdf.to_string(index=False));print("VERDICT",verdict)
        return

    meta={"event_id","signal_time","year","day","entry_time","exit_time","entry","reason","win","gross","net","pnl"}
    features=[c for c in df.columns if c not in meta and c.startswith("ag")]
    work=df.dropna(subset=["ag15_count"]).copy()
    fr,stable=forensic(work,features)
    fr.to_csv(ROOT/(PFX+"_Forensics.csv"),index=False);stable.to_csv(ROOT/(PFX+"_StableDifferentiators.csv"),index=False)

    tr=work[work.year==2023].copy();va=work[work.year==2024].copy()
    med={c:float(pd.to_numeric(tr[c],errors="coerce").median()) for c in features}
    Xtr=pd.DataFrame({c:pd.to_numeric(tr[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features})
    Xva=pd.DataFrame({c:pd.to_numeric(va[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features})
    ytr=tr.win.astype(int)

    models={
        "TREE":DecisionTreeClassifier(max_depth=2,min_samples_leaf=80,class_weight="balanced",random_state=314),
        "RF":RandomForestClassifier(n_estimators=300,max_depth=5,min_samples_leaf=80,max_features="sqrt",class_weight="balanced_subsample",random_state=314,n_jobs=-1),
    }
    grid=[];imps=[]
    baseline_tr=simulate_selected(va.signal_time.tolist(),x5,v1.T1,v1.T2)
    baseline=strat_metrics(baseline_tr,v1.T1,v1.T2)
    for name,m in models.items():
        m.fit(Xtr,ytr)
        p=m.predict_proba(Xva)[:,1]
        imp=getattr(m,"feature_importances_",np.zeros(len(features)))
        for c,v in zip(features,imp):imps.append({"model":name,"feature":c,"importance":float(v)})
        for q in QUANTILES:
            th=float(np.quantile(p,q))
            sig=va.loc[p>=th,"signal_time"].tolist()
            trades=simulate_selected(sig,x5,v1.T1,v1.T2)
            met=strat_metrics(trades,v1.T1,v1.T2)
            grid.append({"model":name,"quantile":q,"threshold":th,"selected_events":len(sig),**met})
    g=pd.DataFrame(grid);g.to_csv(ROOT/(PFX+"_Grid2024.csv"),index=False)
    pd.DataFrame(imps).sort_values(["model","importance"],ascending=[True,False]).to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)

    elig=g[(g.trades_week>=7)&(g.exp>0)].copy()
    if len(elig):
        rank=elig.sort_values(["wr","weekly_mean","exp","n"],ascending=[False,False,False,False])
        status="POSITIVE_DAILY_FRONTIER"
    else:
        freq=g[g.trades_week>=7].copy()
        rank=(freq if len(freq) else g).sort_values(["wr","weekly_mean","exp","n"],ascending=[False,False,False,False])
        status="NO_POSITIVE_DAILY_CONFIG"
    best=rank.iloc[0].to_dict()
    full=bool(best["trades_week"]>=7 and best["exp"]>0 and best["wr"]>=.70)
    near=bool(best["trades_week"]>=7 and best["exp"]>0 and best["wr"]>=.65)
    verdict="FULL_DEV_GATE" if full else ("NEAR_DEV_GATE" if near else "NO_V7B_PROMOTION_GATE")
    selected={**best,"selection_status":status,"full_gate":full,"near_gate":near,"verdict":verdict,
              "baseline_wr":baseline["wr"],"baseline_trades_week":baseline["trades_week"],"baseline_exp":baseline["exp"],"baseline_weekly_mean":baseline["weekly_mean"]}
    pd.DataFrame([selected]).to_csv(ROOT/(PFX+"_Selected.csv"),index=False)

    lines=[
        "# SOL High-Resolution AggTrade Ignition V7B — Result","",
        f"- 5m price coverage: **{cov*100:.5f}%**",
        f"- parent NEW_LONG_BUILD rising-edge events: **{len(events):,}**",
        f"- 2023 event coverage: **{covdf.loc[covdf.year==2023,'coverage'].iloc[0]*100:.2f}%**",
        f"- 2024 event coverage: **{covdf.loc[covdf.year==2024,'coverage'].iloc[0]*100:.2f}%**",
        f"- stable forensic differentiators: **{len(stable)}**","",
        "## Parent baseline 2024","",
        f"- N **{baseline['n']}**, WR **{baseline['wr']*100:.2f}%**, trades/week **{baseline['trades_week']:.2f}**, exp/trade **{baseline['exp']:+.3f}%**, mean weekly **{baseline['weekly_mean']:+.2f}%**.","",
        "## Best frozen V7B development configuration","",
        f"- model: **{best['model']}**",
        f"- score quantile: **{best['quantile']:.3f}**",
        f"- N **{int(best['n'])}**, WR **{best['wr']*100:.2f}%**, trades/week **{best['trades_week']:.2f}**",
        f"- exp/trade **{best['exp']:+.3f}%**, mean weekly **{best['weekly_mean']:+.2f}%**, median weekly **{best['weekly_median']:+.2f}%**",
        "","## Stable differentiators",""
    ]
    if len(stable):
        for _,r in stable.head(15).iterrows():
            lines.append(f"- {r.feature}: SMD 2023 {r.smd_2023:+.3f}, 2024 {r.smd_2024:+.3f}")
    else:lines.append("- none passed the preregistered stability rule")
    lines+=["",f"# VERDICT: {verdict}"]
    (ROOT/(PFX+"_Result.md")).write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
