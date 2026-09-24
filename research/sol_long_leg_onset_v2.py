#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import sol_long_leg_capture_v1 as v1

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_LONG_LEG_ONSET_V2"
CFGS=((4,100),(6,100),(8,100),(8,200))
QUANTILES=v1.QUANTILES

def onset_labels(index,q,legs,threshold):
    y=pd.Series(0,index=index,dtype=int)
    eligible=legs[legs.leg_pct>=threshold]
    for _,r in eligible.iterrows():
        span=index[(index>=r.start)&(index<=r.peak)]
        if len(span)==0:
            continue
        amp=float(r.peak_px-r.start_px)
        if amp<=0:
            continue
        prog=(q.loc[span,"close"].astype(float)-float(r.start_px))/amp
        early=span[(prog>=-0.05)&(prog<=0.25)]
        if len(early):
            y.loc[early]=1
    return y

def candidate_early_hit(d,p,thr,outs,legs,target,start,end):
    tdf=v1.selected_trades_df(d,p,thr,outs,start,end)
    x=v1.leg_hit_stats(tdf,legs,target,start,end)
    return x["early_hit_rate"],x["hit_rate"]

def main():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5("SOLUSDT")
    if cov<0.995:
        raise RuntimeError("coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:
            x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(pd.Timestamp("2026-09-24",tz="UTC"),x5.index[-1]+pd.Timedelta(minutes=5))

    q,cols=v1.build_features(x5)
    legs=v1.zigzag_long_legs(q,end)
    weekly=v1.add_leg_availability(v1.weekly_range_table(q,end),legs)

    rows=[]
    models=[]
    feats=[]
    alltrades=[]

    for target,spec in v1.TARGETS.items():
        tp=float(spec["tp"]); sl=float(spec["sl"]); hold5=int(spec["hold5"])
        outs=v1.build_outcomes(q,x5,tp,sl,hold5,end)
        d=v1.make_dataset(q,cols,outs)
        d["onset"]=onset_labels(d.index,q,legs,tp)

        train_end=v1.T1-pd.Timedelta(days=7)
        train=d[(d.entry_time>=v1.T0)&(d.entry_time<train_end)].copy()
        val=d[(d.entry_time>=v1.T1)&(d.entry_time<v1.T2)&(d.exit_time<v1.T2)].copy()
        r25=d[(d.entry_time>=v1.T2)&(d.entry_time<v1.T3)&(d.exit_time<v1.T3)].copy()
        r26=d[(d.entry_time>=v1.T3)&(d.entry_time<end)].copy()

        pos=int(train.onset.sum())
        if pos<100:
            raise RuntimeError("too few onset positives "+target)

        cand=[]
        fitted={}
        for depth,leaf in CFGS:
            m=RandomForestClassifier(
                n_estimators=280,max_depth=depth,min_samples_leaf=leaf,
                max_features="sqrt",class_weight="balanced_subsample",
                random_state=84,n_jobs=-1
            )
            m.fit(train[cols].astype(float),train.onset)
            fitted[(depth,leaf)]=m
            pv=m.predict_proba(val[cols].astype(float))[:,1]
            for qt in QUANTILES:
                thr=float(np.quantile(pv,qt))
                met=v1.evaluate(val,pv,thr,outs,v1.T1,v1.T2,tp,weekly,tp)
                eh,lh=candidate_early_hit(val,pv,thr,outs,legs,tp,v1.T1,v1.T2)
                cand.append({"target":target,"depth":depth,"leaf":leaf,"quantile":qt,"threshold":thr,
                             "train_onset_n":pos,"early_hit":eh,"leg_hit":lh,**met})

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
        m=fitted[(int(ch["depth"]),int(ch["leaf"]))]
        thr=float(ch["threshold"])

        imp=pd.DataFrame({"feature":cols,"importance":m.feature_importances_}).sort_values("importance",ascending=False)
        for _,r in imp.head(15).iterrows():
            feats.append({"target":target,"feature":r["feature"],"importance":r["importance"]})

        models.append({"target":target,"selection_status":status,"train_onset_n":pos,
                       "depth":int(ch["depth"]),"leaf":int(ch["leaf"]),
                       "quantile":float(ch["quantile"]),"threshold":thr,
                       "val_wr":float(ch["wr"]),"val_trades_week":float(ch["trades_week"]),
                       "val_exp":float(ch["exp"]),"val_weekly_mean":float(ch["weekly_mean"]),
                       "val_early_hit":float(ch["early_hit"]) if pd.notna(ch["early_hit"]) else np.nan,
                       "val_leg_hit":float(ch["leg_hit"]) if pd.notna(ch["leg_hit"]) else np.nan})

        for pname,z,start,stop in (("VAL2024",val,v1.T1,v1.T2),("REF2025",r25,v1.T2,v1.T3),("REF2026",r26,v1.T3,end)):
            p=m.predict_proba(z[cols].astype(float))[:,1]
            met=v1.evaluate(z,p,thr,outs,start,stop,tp,weekly,tp)
            tdf=v1.selected_trades_df(z,p,thr,outs,start,stop)
            hit=v1.leg_hit_stats(tdf,legs,tp,start,stop)
            rows.append({"target":target,"partition":pname,**met,
                         "legs":hit["legs"],"leg_hit_rate":hit["hit_rate"],"early_leg_hit_rate":hit["early_hit_rate"]})
            if len(tdf):
                tdf.insert(0,"partition",pname);tdf.insert(0,"target",target)
                alltrades.append(tdf)

        c.sort_values(["weekly_mean","early_hit"],ascending=[False,False]).head(100).to_csv(
            ROOT/(PFX+"_"+target+"_ValidationGrid.csv"),index=False)

    models=pd.DataFrame(models)
    transfer=pd.DataFrame(rows)
    featdf=pd.DataFrame(feats)
    models.to_csv(ROOT/(PFX+"_SelectedModels.csv"),index=False)
    transfer.to_csv(ROOT/(PFX+"_Transfer.csv"),index=False)
    featdf.to_csv(ROOT/(PFX+"_FeatureImportance.csv"),index=False)
    if alltrades:
        pd.concat(alltrades,ignore_index=True).to_csv(ROOT/(PFX+"_SelectedTrades.csv"),index=False)

    lines=["# SOL Long Leg Onset V2 — Result","",
           "- 5m coverage: **%.5f%%**" % (cov*100),
           "- ex-post 1%% reversal long legs: **%s**" % format(len(legs),","),
           "",
           "Training target: **first 25% of L2/L3/L5 leg amplitude**, not generic TP-before-SL.",
           "",
           "## Selected models",""]
    for _,r in models.iterrows():
        lines.append("- **%s**: %s; onset positives %d; RF %d/%d; q %.3f; 2024 mean weekly %.2f%%; WR %.2f%%; early-hit %.1f%%." % (
            r["target"],r["selection_status"],r["train_onset_n"],r["depth"],r["leaf"],r["quantile"],
            r["val_weekly_mean"],r["val_wr"]*100,r["val_early_hit"]*100 if pd.notna(r["val_early_hit"]) else np.nan))
    lines += ["","## Frozen transfer","",
              "|Target|Partition|WR|Trades/wk|Exp/trade|Mean weekly net|Median weekly net|Leg hit|Early hit|Weeks>=10%|",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in transfer.iterrows():
        lines.append("|%s|%s|%.2f%%|%.2f|%.3f%%|%.2f%%|%.2f%%|%.1f%%|%.1f%%|%.1f%%|" % (
            r["target"],r["partition"],r["wr"]*100,r["trades_week"],r["exp"],r["weekly_mean"],r["weekly_median"],
            r["leg_hit_rate"]*100 if pd.notna(r["leg_hit_rate"]) else np.nan,
            r["early_leg_hit_rate"]*100 if pd.notna(r["early_leg_hit_rate"]) else np.nan,
            r["weeks_ge10"]*100))
    robust=[]
    for target in v1.TARGETS:
        z=transfer[transfer.target==target]
        if len(z)==3 and (z.exp>0).all() and (z.trades_week>=3).all():
            robust.append(target)
    verdict="ONSET_TRANSFER_POSITIVE__"+("_".join(robust)) if robust else "NO_ROBUST_ONSET_TRANSFER"
    lines += ["","# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
