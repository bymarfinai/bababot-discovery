#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_DC_OVERSHOOT_ANATOMY_V9"
SYMBOL="SOLUSDT"
THETA=.005
T0=pd.Timestamp("2023-01-01",tz="UTC")
T1=pd.Timestamp("2024-01-01",tz="UTC")
T2=pd.Timestamp("2025-01-01",tz="UTC")

def dc_events(close,theta):
    p=close.to_numpy(float);idx=close.index
    rows=[]
    if len(p)<2:return pd.DataFrame()
    event_type=None
    ext_i=0;ext=p[0]
    last_peak_i=None;last_peak_px=None
    for i in range(1,len(p)):
        cur=p[i];ch=(cur-ext)/ext
        if event_type=="upturn":
            if ch<=-theta:
                # downturn confirmation; ext is known peak
                rows.append({"kind":"DOWN","signal_time":idx[i],"ext_time":idx[ext_i],"ext_px":ext,
                             "confirm_px":cur})
                last_peak_i=ext_i;last_peak_px=ext
                event_type="downturn";ext_i=i;ext=cur
            elif cur>ext:
                ext_i=i;ext=cur
        elif event_type=="downturn":
            if ch>=theta:
                trough_i=ext_i;trough=ext
                path=p[trough_i:i+1]
                denom=float(np.abs(np.diff(path)).sum()) if len(path)>1 else np.nan
                eff=(cur-trough)/denom if denom and denom>0 else np.nan
                row={"kind":"UP","signal_time":idx[i],"ext_time":idx[trough_i],"ext_px":trough,
                     "confirm_px":cur,"up_amp_pct":(cur/trough-1)*100,
                     "excess_pct":(cur/trough-1-theta)*100,
                     "bars_trough_confirm":i-trough_i,
                     "path_efficiency":eff}
                if last_peak_i is not None and last_peak_px is not None and last_peak_i<trough_i:
                    row["prev_peak_time"]=idx[last_peak_i]
                    row["prev_peak_px"]=last_peak_px
                    row["downswing_pct"]=(1-trough/last_peak_px)*100
                    row["bars_peak_trough"]=trough_i-last_peak_i
                else:
                    row["prev_peak_time"]=pd.NaT;row["prev_peak_px"]=np.nan
                    row["downswing_pct"]=np.nan;row["bars_peak_trough"]=np.nan
                rows.append(row)
                event_type="upturn";ext_i=i;ext=cur
            elif cur<ext:
                ext_i=i;ext=cur
        else:
            if ch>=theta:
                path=p[ext_i:i+1]
                denom=float(np.abs(np.diff(path)).sum()) if len(path)>1 else np.nan
                rows.append({"kind":"UP","signal_time":idx[i],"ext_time":idx[ext_i],"ext_px":ext,
                             "confirm_px":cur,"up_amp_pct":(cur/ext-1)*100,
                             "excess_pct":(cur/ext-1-theta)*100,
                             "bars_trough_confirm":i-ext_i,
                             "path_efficiency":(cur-ext)/denom if denom and denom>0 else np.nan,
                             "prev_peak_time":pd.NaT,"prev_peak_px":np.nan,
                             "downswing_pct":np.nan,"bars_peak_trough":np.nan})
                event_type="upturn";ext_i=i;ext=cur
            elif ch<=-theta:
                rows.append({"kind":"DOWN","signal_time":idx[i],"ext_time":idx[ext_i],"ext_px":ext,
                             "confirm_px":cur})
                last_peak_i=ext_i;last_peak_px=ext
                event_type="downturn";ext_i=i;ext=cur
    ev=pd.DataFrame(rows)
    if ev.empty:return ev
    ev=ev.sort_values("signal_time").reset_index(drop=True)
    # next opposite down-confirmation for each up event
    downs=ev[ev.kind=="DOWN"]["signal_time"].to_numpy()
    next_down=[]
    for _,r in ev.iterrows():
        if r.kind!="UP":next_down.append(pd.NaT);continue
        j=np.searchsorted(downs,np.datetime64(r.signal_time.to_datetime64()),side="right")
        next_down.append(pd.Timestamp(downs[j],tz="UTC") if j<len(downs) else pd.NaT)
    ev["next_down_signal"]=next_down
    return ev

def smd(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    a=a[np.isfinite(a)];b=b[np.isfinite(b)]
    if len(a)<20 or len(b)<20:return np.nan
    va=np.var(a,ddof=1);vb=np.var(b,ddof=1)
    den=math.sqrt(((len(a)-1)*va+(len(b)-1)*vb)/(len(a)+len(b)-2))
    return (np.mean(a)-np.mean(b))/den if den>0 else np.nan

def attach_overshoot_labels(events,x5):
    idx=x5.index;H=x5.high.astype(float).to_numpy();O=x5.open.astype(float).to_numpy()
    rows=[]
    for _,r in events.iterrows():
        st=pd.Timestamp(r.signal_time)
        et=st+pd.Timedelta(minutes=15)
        p=int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:continue
        if pd.isna(r.next_down_signal):continue
        end_t=pd.Timestamp(r.next_down_signal)+pd.Timedelta(minutes=15)
        j=int(idx.searchsorted(end_t,side="right"))-1
        if j<p:continue
        entry=float(O[p]);mfe=(float(np.max(H[p:j+1]))/entry-1)*100
        rr=r.to_dict();rr["entry_time"]=idx[p];rr["cycle_end"]=idx[j];rr["mfe_pct"]=mfe
        for t in (1,2,3):rr[f"os{t}"]=int(mfe>=t)
        rows.append(rr)
    return pd.DataFrame(rows)

def build_features():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    print("load causal flow/context",flush=True)
    flow,_=v3.load_flow15(T2);metrics,_=v3.load_metrics(T2);funding,_=v3.load_funding(T2)
    q,base_cols=v1.build_features(x5)
    q=v3.join_external(q,flow,metrics,funding)
    q,states=v4.build_states(q)
    q=q[(q.index>=pd.Timestamp("2022-12-01",tz="UTC"))&(q.index<T2)].copy()
    ev=dc_events(q.close,THETA)
    up=ev[(ev.kind=="UP")&(ev.signal_time>=T0)&(ev.signal_time<T2)].copy()
    state=states["NEW_LONG_BUILD"].reindex(q.index).fillna(False)
    up=up[state.reindex(pd.DatetimeIndex(up.signal_time)).to_numpy()]
    lab=attach_overshoot_labels(up,x5)
    if lab.empty:raise RuntimeError("no eligible overshoot cycles")
    lab.index=pd.DatetimeIndex(lab.signal_time)
    causal=[
        "body_norm","close_loc","lower_wick","upper_wick","range_atr","body_atr","atr_pct",
        "dist_ema20","ema20_slope","ema20_accel",
        "ret1","ret2","ret4","ret8","ret16",
        "compression4","compression8","compression16",
        "oi60_z7d","oi240_z7d","topvg_z7d","topacct_z7d","taker60_z7d","quoteburst_z7d",
        "funding_z30","flow_imb60","price_ret1h","prior_price_ret1h","price_ret15"
    ]
    causal=[c for c in causal if c in q.columns]
    join=q[causal].reindex(lab.index)
    for c in causal:lab[c]=join[c].to_numpy()
    # DC anatomy fields are causal at confirmation.
    dc_cols=["up_amp_pct","excess_pct","bars_trough_confirm","path_efficiency","downswing_pct","bars_peak_trough"]
    features=dc_cols+causal
    lab["year"]=lab.signal_time.dt.year
    return x5,lab,features,cov

def analyze(df,features,label):
    rows=[]
    for yr in (2023,2024):
        z=df[df.year==yr]
        for f in features:
            vals=pd.to_numeric(z[f],errors="coerce")
            win=vals[z[label]==1].to_numpy(float);loss=vals[z[label]==0].to_numpy(float)
            s=smd(win,loss);auc=np.nan
            m=vals.notna()
            if m.sum()>50 and z.loc[m,label].nunique()==2:
                try:
                    a=roc_auc_score(z.loc[m,label],vals[m]);auc=max(a,1-a)
                except Exception:pass
            rows.append({"label":label,"year":yr,"feature":f,
                         "win_median":float(np.nanmedian(win)) if len(win) else np.nan,
                         "loss_median":float(np.nanmedian(loss)) if len(loss) else np.nan,
                         "smd":s,"auc_oriented":auc})
    out=pd.DataFrame(rows)
    stable=[]
    for f in features:
        a=out[(out.year==2023)&(out.feature==f)]
        b=out[(out.year==2024)&(out.feature==f)]
        if a.empty or b.empty:continue
        a=a.iloc[0];b=b.iloc[0]
        if pd.notna(a.smd) and pd.notna(b.smd) and pd.notna(a.auc_oriented) and pd.notna(b.auc_oriented):
            if np.sign(a.smd)==np.sign(b.smd) and abs(a.smd)>=.15 and abs(b.smd)>=.15 and a.auc_oriented>=.55 and b.auc_oriented>=.55:
                stable.append({"label":label,"feature":f,"smd_2023":a.smd,"smd_2024":b.smd,
                               "auc_2023":a.auc_oriented,"auc_2024":b.auc_oriented,
                               "min_abs_smd":min(abs(a.smd),abs(b.smd)),"min_auc":min(a.auc_oriented,b.auc_oriented)})
    st=pd.DataFrame(stable)
    if len(st):st=st.sort_values(["min_abs_smd","min_auc"],ascending=False)
    return out,st

def main():
    x5,df,features,cov=build_features()
    df.to_csv(ROOT/(PFX+"_Events.csv"),index=False)
    counts=[]
    allstats=[];allstable=[]
    for label in ("os1","os2","os3"):
        for yr in (2023,2024):
            z=df[df.year==yr]
            counts.append({"label":label,"year":yr,"events":len(z),"successes":int(z[label].sum()),"rate":float(z[label].mean())})
        st,stable=analyze(df,features,label);allstats.append(st)
        if len(stable):allstable.append(stable)
    counts=pd.DataFrame(counts);stats=pd.concat(allstats,ignore_index=True)
    stable=pd.concat(allstable,ignore_index=True) if allstable else pd.DataFrame(columns=["label","feature","smd_2023","smd_2024","auc_2023","auc_2024","min_abs_smd","min_auc"])
    counts.to_csv(ROOT/(PFX+"_Counts.csv"),index=False)
    stats.to_csv(ROOT/(PFX+"_FeatureStats.csv"),index=False)
    stable.to_csv(ROOT/(PFX+"_StableSeparators.csv"),index=False)

    eligible=[]
    for label in ("os1","os2","os3"):
        c23=counts[(counts.label==label)&(counts.year==2023)].iloc[0]
        c24=counts[(counts.label==label)&(counts.year==2024)].iloc[0]
        nstable=int((stable.label==label).sum()) if len(stable) else 0
        if c23.events>=500 and c24.events>=500 and nstable>=3:eligible.append(label)
    verdict="ANATOMY_GATE_PASS__"+"__".join(eligible) if eligible else "NO_OVERSHOOT_ANATOMY_GATE_V9"

    lines=["# SOL DC Overshoot Anatomy V9 — Result","",
           f"- 5m coverage: **{cov*100:.5f}%**",
           f"- eligible DC upturn cycles: **{len(df):,}**",
           "- frozen event: **theta 0.50% Directional Change upturn + NEW_LONG_BUILD context**",
           "","## Overshoot base rates","",
           "|Label|Year|Events|Successes|Rate|Stable separators|","|---|---:|---:|---:|---:|---:|"]
    for _,r in counts.iterrows():
        nst=int(((stable.label==r.label)).sum()) if len(stable) else 0
        lines.append(f"|{r.label}|{int(r.year)}|{int(r.events)}|{int(r.successes)}|{r.rate*100:.2f}%|{nst}|")
    lines+=["","## Stable separators",""]
    if len(stable):
        for _,r in stable.head(30).iterrows():
            lines.append(f"- **{r.label} / {r.feature}**: SMD23 {r.smd_2023:+.3f}, SMD24 {r.smd_2024:+.3f}; AUC23 {r.auc_2023:.3f}, AUC24 {r.auc_2024:.3f}")
    else:lines.append("- none")
    lines+=["",f"# VERDICT: {verdict}"]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
