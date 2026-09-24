#!/usr/bin/env python3
from __future__ import annotations

import io, math, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

import sol_long_leg_capture_v1 as v1
import sol_aggtrade_ignition_v7b as v7b

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_SPOT_FUTURES_IGNITION_V7C"
BASE="https://data.binance.vision/data/spot/daily/aggTrades/SOLUSDT"
UA={"User-Agent":"bababot-sol-v7c/1.0"}
QUANTILES=v7b.QUANTILES

def parse_spot_day(ds,events):
    url=f"{BASE}/SOLUSDT-aggTrades-{ds}.zip"
    err=None
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=90,headers=UA)
            if r.status_code==404:return [],{"day":ds,"status":404,"events":len(events),"covered":0}
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:raise RuntimeError("no csv")
                with zf.open(names[0]) as fh:df=pd.read_csv(fh,header=None)
            break
        except Exception as e:
            err=f"{type(e).__name__}: {e}"
            if attempt==2:return [],{"day":ds,"status":"ERR","error":err,"events":len(events),"covered":0}
            time.sleep(1.5*(attempt+1))
    if df.shape[1] < 7:
        return [],{"day":ds,"status":"SCHEMA","columns":df.shape[1],"events":len(events),"covered":0}
    names=["agg_trade_id","price","quantity","first_trade_id","last_trade_id","transact_time","is_buyer_maker","is_best_match"]
    df=df.iloc[:,:min(len(names),df.shape[1])].copy()
    df.columns=names[:df.shape[1]]
    t=pd.to_numeric(df["transact_time"],errors="coerce").to_numpy()
    med=np.nanmedian(t)
    if med>1e14:t=t/1000.0
    t=t.astype(np.float64)
    p=pd.to_numeric(df["price"],errors="coerce").to_numpy(float)
    qty=pd.to_numeric(df["quantity"],errors="coerce").to_numpy(float)
    q=p*qty
    mk=df["is_buyer_maker"]
    if mk.dtype==bool:maker=mk.to_numpy(bool)
    else:maker=mk.astype(str).str.lower().isin(["true","1","t"]).to_numpy(bool)
    side=np.where(maker,-1,1).astype(np.int8)
    ok=np.isfinite(t)&np.isfinite(p)&np.isfinite(q)&(q>=0)
    t=t[ok].astype(np.int64);p=p[ok];q=q[ok];side=side[ok]
    order=np.argsort(t,kind="stable");t=t[order];p=p[order];q=q[order];side=side[order]
    out=[];covered=0
    for _,e in events.iterrows():
        end=int(pd.Timestamp(e.entry_time).timestamp()*1000);start=end-15*60*1000
        base=v7b.slice_stats(t,p,q,side,start,end,"sp15")
        if not np.isfinite(base["sp15_count"]) or base["sp15_count"]<=0:continue
        covered+=1;feat=dict(base)
        for sec,label in ((300,"sp5"),(60,"sp1"),(30,"sp30s")):
            feat.update(v7b.slice_stats(t,p,q,side,end-sec*1000,end,label))
        prev4=v7b.quick_stats(t,q,side,end-5*60*1000,end-60*1000)
        final1=v7b.quick_stats(t,q,side,end-60*1000,end)
        prev30=v7b.quick_stats(t,q,side,end-60*1000,end-30*1000)
        final30=v7b.quick_stats(t,q,side,end-30*1000,end)
        feat["sp_delta_accel_1m_vs_prev4m"]=(final1["dr"]-prev4["dr"]) if np.isfinite(final1["dr"]) and np.isfinite(prev4["dr"]) else np.nan
        feat["sp_delta_accel_30s_vs_prev30s"]=(final30["dr"]-prev30["dr"]) if np.isfinite(final30["dr"]) and np.isfinite(prev30["dr"]) else np.nan
        feat["sp_count_burst_1m_vs_prev4m"]=(final1["n"]/(prev4["n"]/4)) if prev4["n"]>0 else np.nan
        feat["sp_quote_burst_1m_vs_prev4m"]=(final1["quote"]/(prev4["quote"]/4)) if prev4["quote"]>0 else np.nan
        feat["sp_count_burst_30s_vs_prev30s"]=(final30["n"]/prev30["n"]) if prev30["n"]>0 else np.nan
        feat["sp_quote_burst_30s_vs_prev30s"]=(final30["quote"]/prev30["quote"]) if prev30["quote"]>0 else np.nan
        out.append({"event_id":int(e.event_id),**feat})
    return out,{"day":ds,"status":200,"bytes":len(r.content),"events":len(events),"covered":covered}

def extract_spot(events):
    groups=[(ds,g.copy()) for ds,g in events.groupby("day",sort=True)]
    rows=[];diag=[];done=0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(parse_spot_day,ds,g):ds for ds,g in groups}
        for f in as_completed(futs):
            rr,dd=f.result();rows.extend(rr);diag.append(dd);done+=1
            if done%50==0:print(f"spot days {done}/{len(groups)} features {len(rows)}",flush=True)
    return pd.DataFrame(rows),pd.DataFrame(diag)

def add_cross(df):
    z=df.copy()
    for w in ("15","5","1","30s"):
        pairs=[
            ("delta_ratio","delta_diff","sub"),
            ("count_imb","countimb_diff","sub"),
            ("price_ret","price_ret_diff","sub"),
        ]
        for base,name,_ in pairs:
            a=f"sp{w}_{base}";b=f"ag{w}_{base}"
            if a in z and b in z:z[f"cross_{w}_{name}"]=z[a]-z[b]
        a=f"sp{w}_delta_ratio";b=f"ag{w}_delta_ratio"
        if a in z and b in z:z[f"cross_{w}_delta_alignment"]=z[a]*z[b]
    for suffix in ("count_burst_1m_vs_prev4m","quote_burst_1m_vs_prev4m","count_burst_30s_vs_prev30s","quote_burst_30s_vs_prev30s"):
        a="sp_"+suffix;b="ag_"+suffix
        if a in z and b in z:z["cross_"+suffix+"_diff"]=z[a]-z[b]
    return z

def fit_eval(work,features,x5,feature_set):
    tr=work[work.year==2023].copy();va=work[work.year==2024].copy()
    med={c:float(pd.to_numeric(tr[c],errors="coerce").replace([np.inf,-np.inf],np.nan).median()) for c in features}
    Xtr=pd.DataFrame({c:pd.to_numeric(tr[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features})
    Xva=pd.DataFrame({c:pd.to_numeric(va[c],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[c]) for c in features})
    ytr=tr.win.astype(int)
    models={
        "TREE":DecisionTreeClassifier(max_depth=2,min_samples_leaf=80,class_weight="balanced",random_state=314),
        "RF":RandomForestClassifier(n_estimators=300,max_depth=5,min_samples_leaf=80,max_features="sqrt",class_weight="balanced_subsample",random_state=314,n_jobs=-1),
    }
    grid=[];imp=[]
    for name,m in models.items():
        m.fit(Xtr,ytr);p=m.predict_proba(Xva)[:,1]
        fi=getattr(m,"feature_importances_",np.zeros(len(features)))
        for c,v in zip(features,fi):imp.append({"feature_set":feature_set,"model":name,"feature":c,"importance":float(v)})
        for q in QUANTILES:
            th=float(np.quantile(p,q));sig=va.loc[p>=th,"signal_time"].tolist()
            trades=v7b.simulate_selected(sig,x5,v1.T1,v1.T2);met=v7b.strat_metrics(trades,v1.T1,v1.T2)
            grid.append({"feature_set":feature_set,"model":name,"quantile":q,"threshold":th,"selected_events":len(sig),**met})
    return pd.DataFrame(grid),pd.DataFrame(imp)

def main():
    x5,events,cov=v7b.load_events()
    print("extract futures",flush=True);fut,fdiag=v7b.extract_features(events)
    print("extract spot",flush=True);spot,sdiag=extract_spot(events)
    fdiag.to_csv(ROOT/(PFX+"_FuturesDiagnostics.csv"),index=False)
    sdiag.to_csv(ROOT/(PFX+"_SpotDiagnostics.csv"),index=False)
    df=events.merge(fut,on="event_id",how="left").merge(spot,on="event_id",how="left")
    df=add_cross(df)
    df.to_csv(ROOT/(PFX+"_EventFeatures.csv"),index=False)
    covrows=[]
    for yr in (2023,2024):
        z=df[df.year==yr]
        fg=pd.to_numeric(z.ag15_count,errors="coerce").fillna(0)>0
        sg=pd.to_numeric(z.sp15_count,errors="coerce").fillna(0)>0
        covrows.append({"year":yr,"events":len(z),"futures_covered":int(fg.sum()),"spot_covered":int(sg.sum()),
                        "both_covered":int((fg&sg).sum()),"both_coverage":float((fg&sg).mean())})
    covdf=pd.DataFrame(covrows);covdf.to_csv(ROOT/(PFX+"_Coverage.csv"),index=False)
    if (covdf.both_coverage<.95).any():
        verdict="BLOCKED_DATA_COVERAGE"
        (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n")
        print(covdf.to_string(index=False));print("VERDICT",verdict);return
    work=df[(pd.to_numeric(df.ag15_count,errors="coerce").fillna(0)>0)&(pd.to_numeric(df.sp15_count,errors="coerce").fillna(0)>0)].copy()
    spot_cols=[c for c in work.columns if c.startswith("sp")]
    cross_cols=[c for c in work.columns if c.startswith("cross_")]
    sets={"SPOT_ONLY":spot_cols,"SPOT_CROSS":spot_cols+cross_cols}
    allgrid=[];allimp=[];allfor=[];allstable=[]
    for fs,cols in sets.items():
        fr,stable=v7b.forensic(work,cols);fr.insert(0,"feature_set",fs);allfor.append(fr)
        if len(stable):stable.insert(0,"feature_set",fs);allstable.append(stable)
        g,imp=fit_eval(work,cols,x5,fs);allgrid.append(g);allimp.append(imp)
    grid=pd.concat(allgrid,ignore_index=True);imps=pd.concat(allimp,ignore_index=True)
    fors=pd.concat(allfor,ignore_index=True)
    stable=pd.concat(allstable,ignore_index=True) if allstable else pd.DataFrame(columns=["feature_set","feature","smd_2023","smd_2024","min_abs_smd"])
    grid.to_csv(ROOT/(PFX+"_Grid2024.csv"),index=False);imps.to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)
    fors.to_csv(ROOT/(PFX+"_Forensics.csv"),index=False);stable.to_csv(ROOT/(PFX+"_StableDifferentiators.csv"),index=False)
    baseline=v7b.strat_metrics(v7b.simulate_selected(work.loc[work.year==2024,"signal_time"].tolist(),x5,v1.T1,v1.T2),v1.T1,v1.T2)
    elig=grid[(grid.trades_week>=7)&(grid.exp>0)].copy()
    if len(elig):
        rank=elig.sort_values(["wr","weekly_mean","exp","n"],ascending=[False,False,False,False]);status="POSITIVE_DAILY_FRONTIER"
    else:
        freq=grid[grid.trades_week>=7].copy()
        rank=(freq if len(freq) else grid).sort_values(["wr","weekly_mean","exp","n"],ascending=[False,False,False,False]);status="NO_POSITIVE_DAILY_CONFIG"
    best=rank.iloc[0].to_dict()
    full=bool(best["trades_week"]>=7 and best["exp"]>0 and best["wr"]>=.70)
    near=bool(best["trades_week"]>=7 and best["exp"]>0 and best["wr"]>=.65)
    verdict="FULL_DEV_GATE" if full else ("NEAR_DEV_GATE" if near else "NO_V7C_PROMOTION_GATE")
    selected={**best,"selection_status":status,"full_gate":full,"near_gate":near,"verdict":verdict,
              "baseline_wr":baseline["wr"],"baseline_trades_week":baseline["trades_week"],"baseline_exp":baseline["exp"],"baseline_weekly_mean":baseline["weekly_mean"]}
    pd.DataFrame([selected]).to_csv(ROOT/(PFX+"_Selected.csv"),index=False)
    lines=["# SOL Spot-vs-Futures Ignition V7C — Result","",
           f"- 5m coverage: **{cov*100:.5f}%**",
           f"- parent events: **{len(events):,}**",
           f"- 2023 both-source coverage: **{covdf.loc[covdf.year==2023,'both_coverage'].iloc[0]*100:.2f}%**",
           f"- 2024 both-source coverage: **{covdf.loc[covdf.year==2024,'both_coverage'].iloc[0]*100:.2f}%**",
           f"- stable differentiators across feature sets: **{len(stable)}**","",
           "## Baseline 2024","",
           f"- N {baseline['n']}, WR {baseline['wr']*100:.2f}%, trades/week {baseline['trades_week']:.2f}, exp {baseline['exp']:+.3f}%, weekly {baseline['weekly_mean']:+.2f}%.","",
           "## Best V7C configuration","",
           f"- feature set **{best['feature_set']}**, model **{best['model']}**, quantile **{best['quantile']:.3f}**",
           f"- N {int(best['n'])}, WR **{best['wr']*100:.2f}%**, trades/week **{best['trades_week']:.2f}**",
           f"- exp **{best['exp']:+.3f}%/trade**, weekly **{best['weekly_mean']:+.2f}%**","",
           "## Stable differentiators",""]
    if len(stable):
        for _,r in stable.sort_values("min_abs_smd",ascending=False).head(15).iterrows():
            lines.append(f"- {r.feature_set} / {r.feature}: SMD23 {r.smd_2023:+.3f}, SMD24 {r.smd_2024:+.3f}")
    else:lines.append("- none")
    lines+=["",f"# VERDICT: {verdict}"]
    (ROOT/(PFX+"_Result.md")).write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
