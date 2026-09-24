#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_DERIV_STATE_V4"
SYMBOL="SOLUSDT"
START=pd.Timestamp("2023-01-01",tz="UTC")
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")

def roll_z(s,window=672,min_periods=192):
    x=pd.to_numeric(s,errors="coerce")
    mu=x.shift(1).rolling(window,min_periods=min_periods).mean()
    sd=x.shift(1).rolling(window,min_periods=min_periods).std()
    return (x-mu)/sd.replace(0,np.nan)

def build_states(q):
    z=q.copy()
    z["oi60_z7d"]=roll_z(z.metric_oi_chg60)
    z["oi240_z7d"]=roll_z(z.metric_oi_chg240)
    z["topvg_z7d"]=roll_z(z.metric_top_vs_global)
    z["topacct_z7d"]=roll_z(z.metric_topacct_log)
    z["taker60_z7d"]=roll_z(z.flow_imb60)
    z["quoteburst_z7d"]=roll_z(z.flow_quote_burst)
    z["price_ret1h"]=z.close/z.close.shift(4)-1
    z["prior_price_ret1h"]=z.close.shift(4)/z.close.shift(8)-1
    z["price_ret15"]=z.close/z.close.shift(1)-1

    base=(z.price_ret1h>0)&(z.flow_imb60>0)&(z.oi60_z7d>0)
    states={}
    states["NEW_LONG_BUILD"]=base
    states["FRESH_LONG_BUILD"]=base&(z.topvg_z7d<0)
    states["SHORT_SQUEEZE"]=(z.price_ret1h>0)&(z.flow_imb60>0)&(z.oi60_z7d<0)&(z.topvg_z7d<0)
    states["LOW_FUNDING_SQUEEZE"]=states["SHORT_SQUEEZE"]&(z.funding_z30<0)
    states["ABSORPTION_RELEASE"]=(z.prior_price_ret1h<=0)&(z.price_ret15>0)&(z.flow_imb60>0)&(z.oi60_z7d>=0)
    states["DELEVERAGING_REVERSAL"]=(z.price_ret1h>0)&(z.oi60_z7d<0)&(z.funding_z30<0)
    return z,states

def period(name,end):
    if name=="2023": return v1.T0,v1.T1
    if name=="2024": return v1.T1,v1.T2
    if name=="2025": return v1.T2,v1.T3
    return v1.T3,end

def make_eval_df(q,outs,needed):
    d=q[needed].copy()
    d["entry_time"]=[outs[t].entry_time if t in outs else pd.NaT for t in d.index]
    d["exit_time"]=[outs[t].exit_time if t in outs else pd.NaT for t in d.index]
    d["y"]=[1 if t in outs and outs[t].outcome=="TP" else (0 if t in outs else np.nan) for t in d.index]
    d=d.dropna(subset=needed+["entry_time","exit_time","y"]).copy()
    d["y"]=d.y.astype(int)
    return d

def combine_exp(rows):
    n=sum(r["n"] for r in rows)
    if not n:return np.nan
    return sum(r["n"]*r["exp"] for r in rows)/n

def main():
    v1.wf1.v3.v1.base.fetch_one=v1.wf1.v3.v1.fetch_one_with_volume
    x5,cov=v1.wf1.v3.v1.base.load5(SYMBOL)
    if cov<.995:raise RuntimeError("5m coverage too low")
    x5=x5.sort_index().copy()
    for c in ("open","high","low","close","volume"):
        if c in x5.columns:x5[c]=pd.to_numeric(x5[c],errors="coerce")
    x5=x5.dropna(subset=["open","high","low","close"])
    end=min(END_CAP,x5.index[-1]+pd.Timedelta(minutes=5))

    print("load flow",flush=True)
    flow,_=v3.load_flow15(end)
    print("load metrics",flush=True)
    metrics,_=v3.load_metrics(end)
    print("load funding",flush=True)
    funding,_=v3.load_funding(end)

    q,_=v1.build_features(x5)
    q=v3.join_external(q,flow,metrics,funding)
    q,states=build_states(q)
    needed=["oi60_z7d","oi240_z7d","topvg_z7d","topacct_z7d","taker60_z7d","quoteburst_z7d",
            "flow_imb60","funding_z30","price_ret1h","prior_price_ret1h","price_ret15"]
    legs=v1.zigzag_long_legs(q,end)
    weekly=v1.add_leg_availability(v1.weekly_range_table(q,end),legs)

    rows=[];trade_frames=[]
    gates=[]
    for target,spec in v1.TARGETS.items():
        tp=float(spec["tp"])
        outs=v1.build_outcomes(q,x5,tp,float(spec["sl"]),int(spec["hold5"]),end)
        d=make_eval_df(q,outs,needed)
        for sname,mask_all in states.items():
            mask=mask_all.reindex(d.index).fillna(False).astype(float).to_numpy()
            target_rows=[]
            for pname in ("2023","2024","2025","2026"):
                a,b=period(pname,end)
                met=v1.evaluate(d,mask,.5,outs,a,b,tp,weekly,tp)
                tdf=v1.selected_trades_df(d,mask,.5,outs,a,b)
                hit=v1.leg_hit_stats(tdf,legs,tp,a,b)
                r={"target":target,"state":sname,"partition":pname,**met,
                   "legs":hit["legs"],"leg_hit_rate":hit["hit_rate"],"early_leg_hit_rate":hit["early_hit_rate"]}
                rows.append(r);target_rows.append(r)
                if len(tdf):
                    tdf.insert(0,"partition",pname);tdf.insert(0,"state",sname);tdf.insert(0,"target",target)
                    trade_frames.append(tdf)
            yr={r["partition"]:r for r in target_rows}
            pos_years=sum(1 for y in ("2023","2024","2025","2026") if yr[y]["exp"]>0)
            refexp=combine_exp([yr["2025"],yr["2026"]])
            gate=(pos_years>=3 and yr["2025"]["exp"]>0 and yr["2026"]["exp"]>0 and refexp>0
                  and yr["2024"]["trades_week"]>=2 and yr["2025"]["trades_week"]>=2)
            gates.append({"target":target,"state":sname,"positive_years":pos_years,
                          "ref_2025_2026_exp":refexp,"gate":gate,
                          "exp_2023":yr["2023"]["exp"],"exp_2024":yr["2024"]["exp"],
                          "exp_2025":yr["2025"]["exp"],"exp_2026":yr["2026"]["exp"],
                          "tpw_2024":yr["2024"]["trades_week"],"tpw_2025":yr["2025"]["trades_week"]})

    out=pd.DataFrame(rows)
    gate=pd.DataFrame(gates).sort_values(["gate","positive_years","ref_2025_2026_exp"],ascending=[False,False,False])
    out.to_csv(ROOT/(PFX+"_Results.csv"),index=False)
    gate.to_csv(ROOT/(PFX+"_Gate.csv"),index=False)
    if trade_frames:pd.concat(trade_frames,ignore_index=True).to_csv(ROOT/(PFX+"_Trades.csv"),index=False)

    lines=["# SOL Derivatives-State Transition V4 — Result","",
           "- price coverage: **%.5f%%**"%(cov*100),
           "- state rules: **6 frozen sign-based states**",
           "- threshold tuning: **NONE**",
           "","## Calendar transfer","",
           "|Target|State|Year|WR|Trades/wk|Exp/trade|Mean weekly|Median weekly|Leg hit|Early hit|",
           "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in out.iterrows():
        lines.append("|%s|%s|%s|%.2f%%|%.2f|%+.3f%%|%+.2f%%|%+.2f%%|%.1f%%|%.1f%%|"%(
            r.target,r.state,r.partition,r.wr*100,r.trades_week,r.exp,r.weekly_mean,r.weekly_median,
            r.leg_hit_rate*100 if pd.notna(r.leg_hit_rate) else np.nan,
            r.early_leg_hit_rate*100 if pd.notna(r.early_leg_hit_rate) else np.nan))
    lines+=["","## Gate ranking","",
            "|Target|State|Positive years|2025+26 exp|2024 tpw|2025 tpw|PASS|",
            "|---|---|---:|---:|---:|---:|---|"]
    for _,r in gate.iterrows():
        lines.append("|%s|%s|%d|%+.3f%%|%.2f|%.2f|%s|"%(r.target,r.state,int(r.positive_years),r.ref_2025_2026_exp,r.tpw_2024,r.tpw_2025,"YES" if r.gate else "NO"))
    passed=gate[gate.gate]
    verdict="DERIV_STATE_PROMISING__"+"__".join((passed.target+"_"+passed.state).tolist()) if len(passed) else "NO_DERIV_STATE_GATE_PASS_V4"
    lines+=["","# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
