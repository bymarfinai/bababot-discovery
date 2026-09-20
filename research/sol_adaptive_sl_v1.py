#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_entry_v1_actionable as e1
import sol_adaptive_entry_router_v2 as router
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ADAPTIVE_SL_V1"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)
MIN_STOP_R=0.05

POLICIES=(
    "RECLAIM_EXTREME",
    "SWEEP_EXTREME",
    "LIQUIDITY_BUFFER_025",
    "SWEEP_BUFFER_010",
    "SWEEP_BUFFER_025",
    "ROUTE_LOCAL",
    "ROUTE_LOCAL_BUFFER_010",
)


def med(s):
    s=pd.to_numeric(s,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    return float(s.median()) if len(s) else np.nan


def q75(s):
    s=pd.to_numeric(s,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    return float(s.quantile(.75)) if len(s) else np.nan


def prepare_period(x5,end_time,years):
    pop,h1=e1.actionable_detector_population(x5,end_time,years)
    x=x5[x5.index<end_time].copy()
    entries=router.route_entries(pop,h1,x)
    entries=entries[entries.filled==1].copy().reset_index(drop=True)

    cols=[
        "candidate_id","level","sweep_extreme","reclaim_i_h1","resolution_i_h1",
        "resolution_time","outcome","event_label","anatomy_score","side",
        "sweep_time","reclaim_time"
    ]
    meta=pop[cols].drop_duplicates("candidate_id").copy()
    z=entries.merge(meta,on=["candidate_id","side","outcome","event_label","anatomy_score","sweep_time","reclaim_time"],how="left",validate="many_to_one")
    return z,pop,h1,x


def context_for_row(r,pop_by_id,h1,x5):
    if r.candidate_id not in pop_by_id:
        return None
    pr=pop_by_id[r.candidate_id]
    return e1.event_context(pr,h1,x5)


def raw_stop(policy,r,c,x5,h1):
    short=(str(r.side)=="BUY_SIDE")
    R=float(r.range_unit)
    if not np.isfinite(R) or R<=0:
        return np.nan

    reclaim_i=int(r.reclaim_i_h1)
    if reclaim_i<0 or reclaim_i>=len(h1):
        return np.nan
    rh=float(h1.iloc[reclaim_i].high)
    rl=float(h1.iloc[reclaim_i].low)
    sweep=float(r.sweep_extreme)
    level=float(r.level)

    if policy=="RECLAIM_EXTREME":
        return rh if short else rl

    if policy=="SWEEP_EXTREME":
        return sweep

    if policy=="LIQUIDITY_BUFFER_025":
        return level + .25*R if short else level - .25*R

    if policy=="SWEEP_BUFFER_010":
        return sweep + .10*R if short else sweep - .10*R

    if policy=="SWEEP_BUFFER_025":
        return sweep + .25*R if short else sweep - .25*R

    if policy in ("ROUTE_LOCAL","ROUTE_LOCAL_BUFFER_010"):
        if int(r.anatomy_score)==3:
            entry_i=int(r.entry_i_5m)
            trig_i=entry_i-1
            if trig_i<0 or trig_i>=len(x5):
                return np.nan
            anchor=float(x5.iloc[trig_i].high if short else x5.iloc[trig_i].low)
        else:
            anchor=sweep

        if policy=="ROUTE_LOCAL_BUFFER_010":
            return anchor + .10*R if short else anchor - .10*R
        return anchor

    raise ValueError(policy)


def executable_stop(raw,entry,R,short):
    if not np.isfinite(raw) or not np.isfinite(entry) or not np.isfinite(R) or R<=0:
        return np.nan
    if short:
        return max(float(raw),float(entry)+MIN_STOP_R*R)
    return min(float(raw),float(entry)-MIN_STOP_R*R)


def scan_stop(x5,entry_i,stop,short,outcome_known_time):
    idx=x5.index
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()

    end=int(idx.searchsorted(pd.Timestamp(outcome_known_time),side="left"))
    end=min(end,len(x5))
    if entry_i<0 or entry_i>=end:
        return False,-1,pd.NaT,np.nan

    for i in range(entry_i,end):
        hit=bool(hi[i]>=stop) if short else bool(lo[i]<=stop)
        if hit:
            return True,int(i),idx[i],float((idx[i]-idx[entry_i]).total_seconds()/60.0)
    return False,-1,pd.NaT,np.nan


def positive_mae_utilization(x5,entry_i,entry,stop,short,outcome_known_time):
    idx=x5.index
    end=int(idx.searchsorted(pd.Timestamp(outcome_known_time),side="left"))
    end=min(end,len(x5))
    if entry_i<0 or entry_i>=end:
        return np.nan
    q=x5.iloc[entry_i:end]
    if q.empty:
        return np.nan
    risk=abs(float(stop)-float(entry))
    if risk<=0:
        return np.nan
    adverse=(float(q.high.max())-entry) if short else (entry-float(q.low.min()))
    return max(0.0,adverse)/risk


def evaluate_policy(entries,pop,h1,x5,policy):
    pop_by_id={r.candidate_id:r for _,r in pop.iterrows()}
    rows=[]

    for _,r in entries.iterrows():
        c=context_for_row(r,pop_by_id,h1,x5)
        if c is None:
            continue

        R=float(r.range_unit)
        entry=float(r.entry_price)
        short=(str(r.side)=="BUY_SIDE")
        raw=raw_stop(policy,r,c,x5,h1)
        stop=executable_stop(raw,entry,R,short)
        if not np.isfinite(stop):
            continue

        risk=abs(stop-entry)/R
        entry_i=int(r.entry_i_5m)

        hit,hit_i,hit_time,time_to_stop=scan_stop(
            x5,entry_i,stop,short,c["outcome_known_time"]
        )

        util=np.nan
        if int(r.event_label)==1:
            util=positive_mae_utilization(
                x5,entry_i,entry,stop,short,c["outcome_known_time"]
            )

        rows.append({
            "policy":policy,
            "candidate_id":r.candidate_id,
            "side":r.side,
            "anatomy_score":int(r.anatomy_score),
            "assigned_route":r.assigned_route,
            "outcome":r.outcome,
            "event_label":int(r.event_label),
            "entry_time":r.entry_time,
            "entry_i_5m":entry_i,
            "entry_price":entry,
            "range_unit":R,
            "raw_stop":raw,
            "stop_price":stop,
            "initial_risk_range_units":risk,
            "outcome_known_time":c["outcome_known_time"],
            "stop_hit":int(hit),
            "stop_hit_i_5m":hit_i,
            "stop_hit_time":hit_time,
            "time_to_stop_min":time_to_stop,
            "same_entry_bar_stop_hit":int(hit and hit_i==entry_i),
            "positive_mae_over_stop":util,
        })

    return pd.DataFrame(rows)


def metrics(rows,policy):
    g=rows[rows.policy==policy].copy()
    if g.empty:
        return {}

    pos=g[g.event_label==1]
    neg=g[g.event_label==0]
    survivors=g[g.stop_hit==0]

    out={
        "policy":policy,
        "filled_n":len(g),
        "positive_n":len(pos),
        "positive_survivor_n":int((pos.stop_hit==0).sum()),
        "positive_survival_rate":float((pos.stop_hit==0).mean()) if len(pos) else np.nan,
        "negative_n":len(neg),
        "negative_stop_hit_n":int((neg.stop_hit==1).sum()),
        "negative_stop_hit_rate":float((neg.stop_hit==1).mean()) if len(neg) else np.nan,
        "survivor_n":len(survivors),
        "survivor_event_rate":float(survivors.event_label.mean()) if len(survivors) else np.nan,
        "median_initial_risk":med(g.initial_risk_range_units),
        "p75_initial_risk":q75(g.initial_risk_range_units),
        "median_negative_time_to_stop_min":med(neg.loc[neg.stop_hit==1,"time_to_stop_min"]),
        "median_positive_mae_over_stop":med(pos.positive_mae_over_stop),
        "same_entry_bar_stop_hit_n":int(g.same_entry_bar_stop_hit.sum()),
    }

    for side in ("BUY_SIDE","SELL_SIDE"):
        z=pos[pos.side==side]
        out[f"{side.lower()}_positive_n"]=len(z)
        out[f"{side.lower()}_positive_survival"]=float((z.stop_hit==0).mean()) if len(z) else np.nan

    for score in (3,4):
        z=pos[pos.anatomy_score==score]
        out[f"score{score}_positive_n"]=len(z)
        out[f"score{score}_positive_survival"]=float((z.stop_hit==0).mean()) if len(z) else np.nan

    return out


def construction_select(entries,pop,h1,x5):
    allrows=[]
    mets=[]
    for p in POLICIES:
        r=evaluate_policy(entries,pop,h1,x5,p)
        allrows.append(r)
        m=metrics(r,p)
        elig=bool(
            m
            and m["filled_n"]>=180
            and m["positive_n"]>=100
            and np.isfinite(m["positive_survival_rate"]) and m["positive_survival_rate"]>=.90
            and np.isfinite(m["buy_side_positive_survival"]) and m["buy_side_positive_survival"]>=.85
            and np.isfinite(m["sell_side_positive_survival"]) and m["sell_side_positive_survival"]>=.85
            and np.isfinite(m["score3_positive_survival"]) and m["score3_positive_survival"]>=.90
            and (
                int(m["score4_positive_n"])<10
                or (np.isfinite(m["score4_positive_survival"]) and m["score4_positive_survival"]>=.75)
            )
        )
        m["eligible"]=elig
        mets.append(m)

    rows=pd.concat(allrows,ignore_index=True)
    mt=pd.DataFrame(mets)
    elig=mt[mt.eligible].copy()
    winner=None
    if len(elig):
        elig=elig.sort_values(
            ["median_initial_risk","p75_initial_risk","negative_stop_hit_rate","positive_survival_rate","policy"],
            ascending=[True,True,False,False,True]
        )
        winner=elig.iloc[0].to_dict()
    return rows,mt,winner


def confirm_gates(m,construction_median):
    return {
        "filled_n_ge_40":int(m["filled_n"])>=40,
        "positive_n_ge_25":int(m["positive_n"])>=25,
        "positive_survival_ge_85pct":bool(np.isfinite(m["positive_survival_rate"]) and m["positive_survival_rate"]>=.85),
        "buy_positive_survival_ge_80pct":bool(np.isfinite(m["buy_side_positive_survival"]) and m["buy_side_positive_survival"]>=.80),
        "sell_positive_survival_ge_80pct":bool(np.isfinite(m["sell_side_positive_survival"]) and m["sell_side_positive_survival"]>=.80),
        "score3_positive_survival_ge_85pct":bool(np.isfinite(m["score3_positive_survival"]) and m["score3_positive_survival"]>=.85),
        "score4_positive_survival_ge_65pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_survival"]) and m["score4_positive_survival"]>=.65)
        ),
        "median_risk_le_1_5x_construction":bool(
            np.isfinite(m["median_initial_risk"]) and m["median_initial_risk"]<=1.5*construction_median
        ),
    }


def monitor_gates(m,construction_median):
    sample={
        "filled_n_ge_20":int(m["filled_n"])>=20,
        "positive_n_ge_10":int(m["positive_n"])>=10,
    }
    quality={
        "positive_survival_ge_80pct":bool(np.isfinite(m["positive_survival_rate"]) and m["positive_survival_rate"]>=.80),
        "buy_survival_ge_70pct_if_n_ge5":bool(
            int(m["buy_side_positive_n"])<5 or
            (np.isfinite(m["buy_side_positive_survival"]) and m["buy_side_positive_survival"]>=.70)
        ),
        "sell_survival_ge_70pct_if_n_ge5":bool(
            int(m["sell_side_positive_n"])<5 or
            (np.isfinite(m["sell_side_positive_survival"]) and m["sell_side_positive_survival"]>=.70)
        ),
        "score3_survival_ge_80pct_if_n_ge5":bool(
            int(m["score3_positive_n"])<5 or
            (np.isfinite(m["score3_positive_survival"]) and m["score3_positive_survival"]>=.80)
        ),
        "score4_survival_ge_60pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_survival"]) and m["score4_positive_survival"]>=.60)
        ),
        "median_risk_le_1_75x_construction":bool(
            np.isfinite(m["median_initial_risk"]) and m["median_initial_risk"]<=1.75*construction_median
        ),
    }
    return sample,quality


def render(title,m):
    pct=lambda v:"n/a" if not np.isfinite(v) else f"{v*100:.2f}%"
    num=lambda v,d=4:"n/a" if not np.isfinite(v) else f"{v:.{d}f}"
    return [
        f"## {title}","",
        f"- Filled router entries: **{int(m['filled_n'])}**",
        f"- Positive structural entries: **{int(m['positive_n'])}**",
        f"- Positive survival: **{pct(m['positive_survival_rate'])}**",
        f"- BUY positive survival: **{pct(m['buy_side_positive_survival'])}**",
        f"- SELL positive survival: **{pct(m['sell_side_positive_survival'])}**",
        f"- Score-3 positive survival: **{pct(m['score3_positive_survival'])}**",
        f"- Score-4 positive survival: **{pct(m['score4_positive_survival'])}**",
        f"- Negative stop-hit rate: **{pct(m['negative_stop_hit_rate'])}**",
        f"- Survivor structural-event rate: **{pct(m['survivor_event_rate'])}**",
        f"- Median initial risk: **{num(m['median_initial_risk'])} H1 range units**",
        f"- P75 initial risk: **{num(m['p75_initial_risk'])}**",
        f"- Median negative time-to-stop: **{num(m['median_negative_time_to_stop_min'],1)} min**",
        f"- Median positive MAE/stop: **{num(m['median_positive_mae_over_stop'])}**",
        f"- Same-entry-bar stop hits: **{int(m['same_entry_bar_stop_hit_n'])}**",
        ""
    ]


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Construction 2020-2024.
    ec,pc,hc,xc=prepare_period(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    crows,cmetrics,winner=construction_select(ec,pc,hc,xc)

    crows.to_csv(ROOT/f"{PFX}_ConstructionStops.csv",index=False)
    cmetrics.to_csv(ROOT/f"{PFX}_ConstructionMetrics.csv",index=False)

    if winner is None:
        verdict="NO_ADAPTIVE_SL_CONSTRUCTION_RULE"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Stops.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Stops.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_filled_n":len(ec),
            "winner":"",
            "confirmation_2025_opened":False,
            "monitor_2026_opened":False,
            "verdict":verdict
        }])
        lines=[
            "# SOL Adaptive SL V1 — Result","",
            f"- Coverage: **{coverage*100:.6f}%**",
            f"- Construction router fills: **{len(ec)}**",
            "- No frozen stop policy met all construction winner-preservation gates.",
            "",
            f"**VERDICT: {verdict}**","",
            "2027_PLUS=CLOSED"
        ]
    else:
        pname=str(winner["policy"])
        construction_median=float(winner["median_initial_risk"])

        # Frozen 2025 confirmation.
        e25,p25,h25,x25=prepare_period(x5,CONFIRM_END,[2025])
        r25=evaluate_policy(e25,p25,h25,x25,pname)
        m25=metrics(r25,pname)
        g25=confirm_gates(m25,construction_median)
        pass25=all(g25.values())

        r25.to_csv(ROOT/f"{PFX}_Confirmation2025Stops.csv",index=False)
        pd.DataFrame([{**m25,**{f"gate_{k}":v for k,v in g25.items()}}]).to_csv(
            ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False
        )

        lines=[
            "# SOL Adaptive SL V1 — Result","",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Frozen SL construction winner: **{pname}**",
            "- Upstream detector and adaptive-entry router are unchanged.",
            "- No TP, PnL, hour, indicator, or regime optimization.",
            "- 2026 is a secondary monitor, NOT an untouched SL holdout.",""
        ]
        lines+=render("Construction 2020-2024",winner)
        lines+=render("Frozen 2025 confirmation",m25)
        lines+=["## 2025 gate audit",""]
        for k,v in g25.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not pass25:
            verdict="ADAPTIVE_SL_NOT_CONFIRMED_2025"
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Stops.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
            summary=pd.DataFrame([{
                "coverage":coverage,
                "winner":pname,
                "construction_median_risk":construction_median,
                "construction_positive_survival":winner["positive_survival_rate"],
                "confirmation_2025_positive_survival":m25["positive_survival_rate"],
                "confirmation_2025_passed":False,
                "monitor_2026_opened":False,
                "verdict":verdict
            }])
            lines+=["",f"**VERDICT: {verdict}**","",
                    "- 2026 monitor was not used because the frozen SL failed 2025 confirmation.","",
                    "2027_PLUS=CLOSED"]
        else:
            latest=(x5.index.max()+BAR5).floor("h")
            if latest<=CONFIRM_END:
                latest=CONFIRM_END

            e26,p26,h26,x26=prepare_period(x5,latest,[2026])
            r26=evaluate_policy(e26,p26,h26,x26,pname)
            m26=metrics(r26,pname) if len(r26) else {
                "policy":pname,"filled_n":0,"positive_n":0,
                "positive_survival_rate":np.nan,
                "buy_side_positive_n":0,"buy_side_positive_survival":np.nan,
                "sell_side_positive_n":0,"sell_side_positive_survival":np.nan,
                "score3_positive_n":0,"score3_positive_survival":np.nan,
                "score4_positive_n":0,"score4_positive_survival":np.nan,
                "negative_stop_hit_rate":np.nan,"survivor_event_rate":np.nan,
                "median_initial_risk":np.nan,"p75_initial_risk":np.nan,
                "median_negative_time_to_stop_min":np.nan,
                "median_positive_mae_over_stop":np.nan,
                "same_entry_bar_stop_hit_n":0,
            }
            sample26,quality26=monitor_gates(m26,construction_median)

            if not all(sample26.values()):
                verdict="ADAPTIVE_SL_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT"
            elif all(quality26.values()):
                verdict="ADAPTIVE_SL_CANDIDATE_REPLICATED_NOT_INDEPENDENT"
            else:
                verdict="ADAPTIVE_SL_2026_MONITOR_DID_NOT_REPLICATE"

            r26.to_csv(ROOT/f"{PFX}_Monitor2026Stops.csv",index=False)
            pd.DataFrame([{
                **m26,
                "data_end":latest,
                **{f"sample_{k}":v for k,v in sample26.items()},
                **{f"gate_{k}":v for k,v in quality26.items()},
                "verdict":verdict
            }]).to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)

            summary=pd.DataFrame([{
                "coverage":coverage,
                "winner":pname,
                "construction_median_risk":construction_median,
                "construction_positive_survival":winner["positive_survival_rate"],
                "confirmation_2025_positive_survival":m25["positive_survival_rate"],
                "confirmation_2025_passed":True,
                "monitor_2026_opened":True,
                "monitor_2026_data_end":latest,
                "monitor_2026_positive_survival":m26["positive_survival_rate"],
                "monitor_2026_median_risk":m26["median_initial_risk"],
                "verdict":verdict
            }])

            lines+=["","## 2025 verdict","","**PASS — frozen SL candidate confirmed historically.**",""]
            lines+=render("2026 YTD secondary replication monitor",m26)
            lines+=["## 2026 monitor sample audit",""]
            for k,v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["","## 2026 monitor quality audit",""]
            for k,v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["",f"**VERDICT: {verdict}**","",
                    "This is not labeled fully validated SL because 2026 was already observed during entry work. A genuinely new holdout is still required for that claim.","",
                    "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
