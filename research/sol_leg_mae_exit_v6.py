#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_LEG_MAE_EXIT_V6"
SYMBOL="SOLUSDT"
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")
SL_GRIDS={
    "L2":[1.00,1.25,1.50,2.00],
    "L3":[1.00,1.25,1.50,2.00,2.50,3.00],
    "L5":[1.00,1.50,2.00,2.50,3.00,4.00,5.00],
}
PARENTS=("NEW_LONG_BUILD","ABSORPTION_RELEASE")

def period(name,end):
    if name=="2023":return v1.T0,v1.T1
    if name=="2024":return v1.T1,v1.T2
    if name=="2025":return v1.T2,v1.T3
    return v1.T3,end

def week_start(ts):
    t=pd.Timestamp(ts)
    return (t-pd.Timedelta(days=t.weekday())).normalize()

def period_weeks(start,end):
    a=week_start(start);b=week_start(end-pd.Timedelta(seconds=1))
    return pd.date_range(a,b,freq="7D",tz="UTC")

def sim_signals(signal_times,x5,tp,sl,hold5):
    idx=x5.index
    op=x5.open.astype(float).to_numpy()
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()
    cl=x5.close.astype(float).to_numpy()
    active=pd.Timestamp.min.tz_localize("UTC")
    rows=[]
    for st in signal_times:
        et=st+pd.Timedelta(minutes=15)
        if et<=active:continue
        p=int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:continue
        entry=float(op[p]);tgt=entry*(1+tp/100);stop=entry*(1-sl/100)
        last=min(p+hold5-1,len(idx)-1)
        ex=last;reason="TIME";gross=(float(cl[last])/entry-1)*100
        for j in range(p,last+1):
            ht=hi[j]>=tgt;hs=lo[j]<=stop
            if ht and hs:
                reason="SL_AMBIG";ex=j;gross=-sl;break
            if hs:
                reason="SL";ex=j;gross=-sl;break
            if ht:
                reason="TP";ex=j;gross=tp;break
        net=gross-v1.COST
        rows.append({"signal_time":st,"entry_time":idx[p],"exit_time":idx[ex],
                     "outcome":reason,"gross":gross,"net":net,"pnl":net/100*v1.NOTIONAL})
        active=idx[ex]
    return pd.DataFrame(rows)

def metrics(trades,start,end):
    z=trades[(trades.entry_time>=start)&(trades.entry_time<end)].copy() if len(trades) else trades.copy()
    weeks=period_weeks(start,end);weekly=pd.Series(0.0,index=weeks)
    if len(z):
        for _,r in z.iterrows():
            w=week_start(r.entry_time)
            if w in weekly.index:weekly.loc[w]+=float(r.net)
    n=len(z);wins=int((z.outcome=="TP").sum()) if n else 0
    return {
        "n":n,
        "wr":wins/n if n else np.nan,
        "trades_week":n/len(weeks) if len(weeks) else np.nan,
        "exp":float(z.net.mean()) if n else np.nan,
        "pnl":float(z.pnl.sum()) if n else 0.0,
        "weekly_mean":float(weekly.mean()) if len(weeks) else np.nan,
        "weekly_median":float(weekly.median()) if len(weeks) else np.nan,
        "positive_weeks":float((weekly>0).mean()) if len(weeks) else np.nan,
        "weeks_ge5":float((weekly>=5).mean()) if len(weeks) else np.nan,
        "weeks_ge10":float((weekly>=10).mean()) if len(weeks) else np.nan,
    }

def mae_eventual_hits(signal_times,x5,tp,hold5):
    idx=x5.index
    op=x5.open.astype(float).to_numpy()
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()
    rows=[]
    for st in signal_times:
        et=st+pd.Timedelta(minutes=15)
        p=int(idx.searchsorted(et))
        if p>=len(idx) or idx[p]!=et:continue
        entry=float(op[p]);tgt=entry*(1+tp/100);last=min(p+hold5-1,len(idx)-1)
        hits=np.flatnonzero(hi[p:last+1]>=tgt)
        if not len(hits):continue
        hit=p+int(hits[0])
        # Conservative bar-level MAE includes low of target-touch bar because intrabar order is unknown.
        minlow=float(np.min(lo[p:hit+1]))
        mae=max(0.0,(1-minlow/entry)*100)
        rows.append({"signal_time":st,"entry_time":et,"target":tp,"mae_pct":mae,
                     "hours_to_target":(idx[hit]-et).total_seconds()/3600})
    return pd.DataFrame(rows)

def mae_summary(df,state,target,end):
    out=[]
    for yr in ("2023","2024","2025","2026"):
        a,b=period(yr,end)
        z=df[(df.entry_time>=a)&(df.entry_time<b)] if len(df) else df
        vals=z.mae_pct.to_numpy(float) if len(z) else np.array([])
        out.append({
            "state":state,"target":target,"partition":yr,"eventual_hits":len(vals),
            "mae_p25":float(np.quantile(vals,.25)) if len(vals) else np.nan,
            "mae_p50":float(np.quantile(vals,.50)) if len(vals) else np.nan,
            "mae_p75":float(np.quantile(vals,.75)) if len(vals) else np.nan,
            "mae_p90":float(np.quantile(vals,.90)) if len(vals) else np.nan,
            "hours_to_target_median":float(z.hours_to_target.median()) if len(z) else np.nan,
        })
    return out

def hit_rates(trades,legs,tp,start,end):
    if not len(trades):return {"legs":0,"leg_hit_rate":np.nan,"early_leg_hit_rate":np.nan}
    return v1.leg_hit_stats(trades[["entry_time"]],legs,tp,start,end)

def main():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(END_CAP,x5.index[-1]+pd.Timedelta(minutes=5))

    print("load flow",flush=True);flow,_=v3.load_flow15(end)
    print("load metrics",flush=True);metrics,_=v3.load_metrics(end)
    print("load funding",flush=True);funding,_=v3.load_funding(end)
    q,_=v1.build_features(x5);q=v3.join_external(q,flow,metrics,funding);q,states=v4.build_states(q)
    edges={n:(m.fillna(False)&(~m.shift(1).fillna(False))) for n,m in states.items()}
    legs=v1.zigzag_long_legs(q,end)

    mae_rows=[];grid_rows=[];trade_frames=[]
    selected=[]
    for target,spec in v1.TARGETS.items():
        tp=float(spec["tp"]);hold5=int(spec["hold5"])
        for state in PARENTS:
            sig=q.index[edges[state].fillna(False).to_numpy()]
            md=mae_eventual_hits(sig,x5,tp,hold5)
            mae_rows.extend(mae_summary(md,state,target,end))

            configs=[]
            trade_map={}
            for sl in SL_GRIDS[target]:
                tr=sim_signals(sig,x5,tp,float(sl),hold5)
                trade_map[sl]=tr
                row={"target":target,"state":state,"tp":tp,"sl":sl,"rr":tp/sl}
                for yr in ("2023","2024","2025","2026"):
                    a,b=period(yr,end);m=metrics(tr,a,b)
                    for k,v in m.items():row[f"{yr}_{k}"]=v
                configs.append(row);grid_rows.append(row.copy())
            cfg=pd.DataFrame(configs)
            elig=cfg[cfg["2024_exp"]>0].copy()
            if len(elig):
                rank=elig.sort_values(["2024_weekly_mean","2024_exp","2024_wr"],ascending=[False,False,False])
                status="ELIGIBLE_POSITIVE_2024"
            else:
                rank=cfg.sort_values(["2024_weekly_mean","2024_exp","2024_wr"],ascending=[False,False,False])
                status="FRONTIER_NO_POSITIVE_2024"
            ch=rank.iloc[0];sl=float(ch.sl);tr=trade_map[sl]
            srow={"target":target,"state":state,"status":status,"tp":tp,"sl":sl,"rr":tp/sl}
            yrm={}
            for yr in ("2023","2024","2025","2026"):
                a,b=period(yr,end);m=metrics(tr,a,b);yrm[yr]=m
                hr=hit_rates(tr,legs,tp,a,b)
                for k,v in m.items():srow[f"{yr}_{k}"]=v
                srow[f"{yr}_leg_hit"]=hr["leg_hit_rate"];srow[f"{yr}_early_hit"]=hr["early_leg_hit_rate"]
            nref=yrm["2025"]["n"]+yrm["2026"]["n"]
            refexp=(yrm["2025"]["n"]*yrm["2025"]["exp"]+yrm["2026"]["n"]*yrm["2026"]["exp"])/nref if nref else np.nan
            gate=(yrm["2024"]["exp"]>0 and yrm["2025"]["exp"]>0 and yrm["2026"]["exp"]>0 and refexp>0
                  and yrm["2024"]["trades_week"]>=1 and yrm["2025"]["trades_week"]>=1)
            srow["ref_2025_2026_exp"]=refexp;srow["gate"]=gate
            selected.append(srow)
            if len(tr):
                tt=tr.copy();tt.insert(0,"state",state);tt.insert(0,"target",target);tt.insert(2,"sl",sl)
                trade_frames.append(tt)

    mae=pd.DataFrame(mae_rows);grid=pd.DataFrame(grid_rows);sel=pd.DataFrame(selected)
    mae.to_csv(ROOT/(PFX+"_MAE.csv"),index=False)
    grid.to_csv(ROOT/(PFX+"_SLGrid.csv"),index=False)
    sel.to_csv(ROOT/(PFX+"_Selected.csv"),index=False)
    if trade_frames:pd.concat(trade_frames,ignore_index=True).to_csv(ROOT/(PFX+"_SelectedTrades.csv"),index=False)

    lines=["# SOL Leg MAE / Exit Geometry V6 — Result","",
           "- price coverage: **%.5f%%**"%(cov*100),
           "- parents: **NEW_LONG_BUILD + ABSORPTION_RELEASE rising edges**",
           "- all SL candidates preserve **RR >= 1:1**",
           "","## MAE before eventual target (diagnostic, stop ignored)","",
           "|State|Target|Year|Eventual hits|MAE p25|p50|p75|p90|Median hrs to target|",
           "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in mae.iterrows():
        lines.append("|%s|%s|%s|%d|%.2f%%|%.2f%%|%.2f%%|%.2f%%|%.1f|"%(r.state,r.target,r.partition,int(r.eventual_hits),
            r.mae_p25,r.mae_p50,r.mae_p75,r.mae_p90,r.hours_to_target_median))
    lines+=["","## 2024-selected SL frozen transfer","",
            "|Target|State|TP/SL|RR|Status|2024 WR/exp/wk|2025 WR/exp/wk|2026 WR/exp/wk|2025+26 exp|PASS|",
            "|---|---|---|---:|---|---|---|---|---:|---|"]
    for _,r in sel.iterrows():
        lines.append("|%s|%s|%.2f/%.2f|%.2f|%s|%.1f%% / %+.3f%% / %+.2f%%|%.1f%% / %+.3f%% / %+.2f%%|%.1f%% / %+.3f%% / %+.2f%%|%+.3f%%|%s|"%(
            r.target,r.state,r.tp,r.sl,r.rr,r.status,
            r["2024_wr"]*100,r["2024_exp"],r["2024_weekly_mean"],
            r["2025_wr"]*100,r["2025_exp"],r["2025_weekly_mean"],
            r["2026_wr"]*100,r["2026_exp"],r["2026_weekly_mean"],
            r.ref_2025_2026_exp,"YES" if r.gate else "NO"))
    passed=sel[sel.gate]
    verdict="EXIT_GEOMETRY_PROMISING__"+"__".join((passed.target+"_"+passed.state).tolist()) if len(passed) else "NO_EXIT_GEOMETRY_GATE_PASS_V6"
    lines+=["","# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
