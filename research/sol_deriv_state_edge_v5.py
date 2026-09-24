#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_long_leg_capture_v1 as v1
import sol_orderflow_ignition_v3 as v3
import sol_deriv_state_v4 as v4

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_DERIV_STATE_EDGE_V5"
SYMBOL="SOLUSDT"
END_CAP=pd.Timestamp("2026-09-24",tz="UTC")

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

def weighted_exp(a,b):
    n=a["n"]+b["n"]
    return (a["n"]*a["exp"]+b["n"]*b["exp"])/n if n else np.nan

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
    q,states=v4.build_states(q)

    needed=["oi60_z7d","oi240_z7d","topvg_z7d","topacct_z7d","taker60_z7d","quoteburst_z7d",
            "flow_imb60","funding_z30","price_ret1h","prior_price_ret1h","price_ret15"]

    # Rising-edge only. First bar of a True episode is eligible.
    edges={name:(m.fillna(False)&(~m.shift(1).fillna(False))) for name,m in states.items()}

    legs=v1.zigzag_long_legs(q,end)
    weekly=v1.add_leg_availability(v1.weekly_range_table(q,end),legs)

    rows=[];gates=[];trade_frames=[]
    for target,spec in v1.TARGETS.items():
        tp=float(spec["tp"])
        outs=v1.build_outcomes(q,x5,tp,float(spec["sl"]),int(spec["hold5"]),end)
        d=make_eval_df(q,outs,needed)

        for sname,edge_all in edges.items():
            edge=edge_all.reindex(d.index).fillna(False).astype(float).to_numpy()
            yr={}
            for pname in ("2023","2024","2025","2026"):
                a,b=period(pname,end)
                met=v1.evaluate(d,edge,.5,outs,a,b,tp,weekly,tp)
                tdf=v1.selected_trades_df(d,edge,.5,outs,a,b)
                hit=v1.leg_hit_stats(tdf,legs,tp,a,b)
                r={"target":target,"state":sname,"partition":pname,**met,
                   "legs":hit["legs"],"leg_hit_rate":hit["hit_rate"],"early_leg_hit_rate":hit["early_hit_rate"]}
                rows.append(r);yr[pname]=r
                if len(tdf):
                    tdf.insert(0,"partition",pname);tdf.insert(0,"state",sname);tdf.insert(0,"target",target)
                    trade_frames.append(tdf)

            refexp=weighted_exp(yr["2025"],yr["2026"])
            gate=(yr["2024"]["exp"]>0 and yr["2025"]["exp"]>0 and yr["2026"]["exp"]>0
                  and refexp>0 and yr["2024"]["trades_week"]>=1 and yr["2025"]["trades_week"]>=1)
            gates.append({"target":target,"state":sname,"gate":gate,
                          "ref_2025_2026_exp":refexp,
                          "exp_2023":yr["2023"]["exp"],"exp_2024":yr["2024"]["exp"],
                          "exp_2025":yr["2025"]["exp"],"exp_2026":yr["2026"]["exp"],
                          "tpw_2024":yr["2024"]["trades_week"],"tpw_2025":yr["2025"]["trades_week"],
                          "weekly_2024":yr["2024"]["weekly_mean"],"weekly_2025":yr["2025"]["weekly_mean"],
                          "weekly_2026":yr["2026"]["weekly_mean"]})

    out=pd.DataFrame(rows)
    gate=pd.DataFrame(gates).sort_values(["gate","ref_2025_2026_exp"],ascending=[False,False])
    out.to_csv(ROOT/(PFX+"_Results.csv"),index=False)
    gate.to_csv(ROOT/(PFX+"_Gate.csv"),index=False)
    if trade_frames:pd.concat(trade_frames,ignore_index=True).to_csv(ROOT/(PFX+"_Trades.csv"),index=False)

    lines=["# SOL Derivatives-State Rising Edge V5 — Result","",
           "- price coverage: **%.5f%%**"%(cov*100),
           "- event semantics: **OFF->ON rising edge only**",
           "- state rules: **unchanged from V4**",
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
            "|Target|State|2025+26 exp|2024 tpw|2025 tpw|Weekly 2024|2025|2026|PASS|",
            "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for _,r in gate.iterrows():
        lines.append("|%s|%s|%+.3f%%|%.2f|%.2f|%+.2f%%|%+.2f%%|%+.2f%%|%s|"%(r.target,r.state,r.ref_2025_2026_exp,
            r.tpw_2024,r.tpw_2025,r.weekly_2024,r.weekly_2025,r.weekly_2026,"YES" if r.gate else "NO"))

    passed=gate[gate.gate]
    verdict="RISING_EDGE_PROMISING__"+"__".join((passed.target+"_"+passed.state).tolist()) if len(passed) else "NO_RISING_EDGE_GATE_PASS_V5"
    lines+=["","# VERDICT: "+verdict]
    txt="\n".join(lines)+"\n"
    (ROOT/(PFX+"_Result.md")).write_text(txt,encoding="utf-8")
    (ROOT/(PFX+"_Status.txt")).write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
