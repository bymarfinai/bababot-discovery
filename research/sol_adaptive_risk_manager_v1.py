#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_sl_v1 as sl
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ADAPTIVE_RISK_MANAGER_V1"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

POLICIES=(
    "STATIC_RECLAIM_EXTREME",
    "HALF_RISK_AFTER_025R",
    "HALF_RISK_AFTER_050R",
    "HALF_RISK_AFTER_075R",
    "BE_AFTER_025R",
    "BE_AFTER_050R",
    "BE_AFTER_075R",
)


def max_dd(rs):
    s=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    if s.empty:
        return np.nan
    eq=s.cumsum()
    peak=eq.cummax().clip(lower=0.0)
    return float((peak-eq).max())


def max_loss_streak(rs):
    best=cur=0
    for x in pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna():
        if x<0:
            cur+=1
            best=max(best,cur)
        else:
            cur=0
    return best


def med(s):
    s=pd.to_numeric(s,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    return float(s.median()) if len(s) else np.nan


def policy_params(policy):
    if policy=="STATIC_RECLAIM_EXTREME":
        return None,None
    if "025R" in policy:
        trig=.25
    elif "050R" in policy:
        trig=.50
    elif "075R" in policy:
        trig=.75
    else:
        raise ValueError(policy)

    if policy.startswith("HALF_RISK"):
        managed_loss=.50
    elif policy.startswith("BE_"):
        managed_loss=0.0
    else:
        raise ValueError(policy)

    return trig,managed_loss


def prepare_period(x5,end_time,years):
    entries,pop,h1,x=sl.prepare_period(x5,end_time,years)
    stops=sl.evaluate_policy(entries,pop,h1,x,"RECLAIM_EXTREME")
    if stops.empty:
        return pd.DataFrame(),pop,h1,x

    keep=[
        "candidate_id","stop_price","initial_risk_range_units","outcome_known_time"
    ]
    z=entries.merge(
        stops[keep],
        on="candidate_id",
        how="inner",
        validate="one_to_one"
    )
    z["initial_risk_price"]=abs(
        pd.to_numeric(z.stop_price,errors="coerce")-
        pd.to_numeric(z.entry_price,errors="coerce")
    )
    return z.reset_index(drop=True),pop,h1,x


def horizon_exit(x5,outcome_known_time):
    i=int(x5.index.searchsorted(pd.Timestamp(outcome_known_time),side="left"))
    if i<len(x5):
        return i,x5.index[i],float(x5.iloc[i].open)
    if len(x5):
        return len(x5)-1,x5.index[-1],float(x5.iloc[-1].close)
    return -1,pd.NaT,np.nan


def simulate_policy(trades,x5,policy):
    rows=[]
    idx=x5.index
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()

    trig_r,managed_loss_r=policy_params(policy)

    for _,r in trades.iterrows():
        entry=float(r.entry_price)
        initial_stop=float(r.stop_price)
        risk=float(r.initial_risk_price)
        if not (np.isfinite(entry) and np.isfinite(initial_stop) and np.isfinite(risk) and risk>0):
            continue

        short=(str(r.side)=="BUY_SIDE")
        start=int(r.entry_i_5m)
        end=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
        end=min(end,len(x5))
        if start<0 or start>=end:
            continue

        trigger_price=np.nan
        managed_stop=np.nan
        if trig_r is not None:
            trigger_price=entry-trig_r*risk if short else entry+trig_r*risk
            if managed_loss_r==0:
                managed_stop=entry
            else:
                managed_stop=entry+managed_loss_r*risk if short else entry-managed_loss_r*risk

        active_stop=initial_stop
        triggered=False
        trigger_i=-1
        trigger_time=pd.NaT
        stop_hit=False
        stop_i=-1
        stop_time=pd.NaT
        exit_type="TIME_EXIT"
        exit_i=-1
        exit_time=pd.NaT
        exit_price=np.nan
        realized=np.nan
        same_bar_managed_stop=False

        for i in range(start,end):
            # Existing stop always wins if both stop and new trigger are reachable intrabar.
            current_stop_hit=bool(hi[i]>=active_stop) if short else bool(lo[i]<=active_stop)
            if current_stop_hit:
                stop_hit=True
                stop_i=i
                stop_time=idx[i]
                exit_type="STOP"
                exit_i=i
                exit_time=idx[i]
                exit_price=active_stop
                realized=((entry-active_stop)/risk) if short else ((active_stop-entry)/risk)
                break

            if trig_r is not None and not triggered:
                trigger_hit=bool(lo[i]<=trigger_price) if short else bool(hi[i]>=trigger_price)
                if trigger_hit:
                    triggered=True
                    trigger_i=i
                    trigger_time=idx[i]
                    active_stop=managed_stop

                    # Conservative same-bar rule after trigger activation.
                    tightened_hit=bool(hi[i]>=active_stop) if short else bool(lo[i]<=active_stop)
                    if tightened_hit:
                        stop_hit=True
                        stop_i=i
                        stop_time=idx[i]
                        same_bar_managed_stop=True
                        exit_type="STOP"
                        exit_i=i
                        exit_time=idx[i]
                        exit_price=active_stop
                        realized=((entry-active_stop)/risk) if short else ((active_stop-entry)/risk)
                        break

        if exit_type=="TIME_EXIT":
            ei,et,ep=horizon_exit(x5,r.outcome_known_time)
            if ei<0 or not np.isfinite(ep):
                continue
            exit_i=ei
            exit_time=et
            exit_price=ep
            realized=((entry-ep)/risk) if short else ((ep-entry)/risk)

        rows.append({
            "policy":policy,
            "candidate_id":r.candidate_id,
            "side":r.side,
            "anatomy_score":int(r.anatomy_score),
            "assigned_route":r.assigned_route,
            "event_label":int(r.event_label),
            "outcome":r.outcome,
            "entry_time":r.entry_time,
            "entry_i_5m":start,
            "entry_price":entry,
            "initial_stop":initial_stop,
            "initial_risk_price":risk,
            "initial_risk_range_units":float(r.initial_risk_range_units),
            "trigger_r":trig_r if trig_r is not None else np.nan,
            "trigger_price":trigger_price,
            "managed_loss_r":managed_loss_r if managed_loss_r is not None else np.nan,
            "managed_stop":managed_stop,
            "management_triggered":int(triggered),
            "trigger_i_5m":trigger_i,
            "trigger_time":trigger_time,
            "outcome_known_time":r.outcome_known_time,
            "stop_hit":int(stop_hit),
            "stop_i_5m":stop_i,
            "stop_time":stop_time,
            "same_bar_managed_stop_hit":int(same_bar_managed_stop),
            "exit_type":exit_type,
            "exit_i_5m":exit_i,
            "exit_time":exit_time,
            "exit_price":float(exit_price),
            "realized_r":float(realized),
            "time_to_exit_min":float(
                (pd.Timestamp(exit_time)-pd.Timestamp(r.entry_time)).total_seconds()/60.0
            ),
        })

    return pd.DataFrame(rows)


def metrics(rows,policy):
    g=rows[rows.policy==policy].copy()
    if g.empty:
        return {}

    pos=g[g.event_label==1]
    neg=g[g.event_label==0]
    out={
        "policy":policy,
        "trades_n":len(g),
        "positive_n":len(pos),
        "positive_survivor_n":int((pos.exit_type=="TIME_EXIT").sum()),
        "positive_survival_rate":float((pos.exit_type=="TIME_EXIT").mean()) if len(pos) else np.nan,
        "management_trigger_rate":float(g.management_triggered.mean()),
        "negative_n":len(neg),
        "negative_stop_hit_rate":float((neg.exit_type=="STOP").mean()) if len(neg) else np.nan,
        "negative_mean_realized_r":float(neg.realized_r.mean()) if len(neg) else np.nan,
        "negative_median_realized_r":float(neg.realized_r.median()) if len(neg) else np.nan,
        "all_mean_realized_r":float(g.realized_r.mean()),
        "cum_realized_r":float(g.realized_r.sum()),
        "max_dd_r":float(max_dd(g.realized_r)),
        "max_loss_streak":int(max_loss_streak(g.realized_r)),
        "median_time_to_exit_min":med(g.time_to_exit_min),
        "same_bar_managed_stop_hit_n":int(g.same_bar_managed_stop_hit.sum()),
    }

    for side in ("BUY_SIDE","SELL_SIDE"):
        z=pos[pos.side==side]
        out[f"{side.lower()}_positive_n"]=len(z)
        out[f"{side.lower()}_positive_survival"]=float((z.exit_type=="TIME_EXIT").mean()) if len(z) else np.nan

    for score in (3,4):
        z=pos[pos.anatomy_score==score]
        out[f"score{score}_positive_n"]=len(z)
        out[f"score{score}_positive_survival"]=float((z.exit_type=="TIME_EXIT").mean()) if len(z) else np.nan

    return out


def construction_select(trades,x5):
    allrows=[]
    mets=[]
    for p in POLICIES:
        r=simulate_policy(trades,x5,p)
        allrows.append(r)
        mets.append(metrics(r,p))

    rows=pd.concat(allrows,ignore_index=True)
    mt=pd.DataFrame(mets)
    base=mt[mt.policy=="STATIC_RECLAIM_EXTREME"].iloc[0]

    adaptive=mt[mt.policy!="STATIC_RECLAIM_EXTREME"].copy()
    adaptive["negative_improvement_vs_static"]=adaptive.negative_mean_realized_r-float(base.negative_mean_realized_r)
    adaptive["cum_improvement_vs_static"]=adaptive.cum_realized_r-float(base.cum_realized_r)

    adaptive["eligible"]=(
        (adaptive.trades_n>=180)
        & (adaptive.positive_n>=100)
        & (adaptive.positive_survival_rate>=.85)
        & (adaptive.buy_side_positive_survival>=.80)
        & (adaptive.sell_side_positive_survival>=.80)
        & (adaptive.score3_positive_survival>=.85)
        & (
            (adaptive.score4_positive_n<10)
            | (adaptive.score4_positive_survival>=.70)
        )
        & (adaptive.negative_improvement_vs_static>=.15)
        & (adaptive.cum_realized_r>float(base.cum_realized_r))
    )

    mt=mt.merge(
        adaptive[["policy","negative_improvement_vs_static","cum_improvement_vs_static","eligible"]],
        on="policy",how="left"
    )
    mt["eligible"]=mt["eligible"].fillna(False).astype(bool)

    elig=mt[mt.eligible].copy()
    winner=None
    if len(elig):
        elig=elig.sort_values(
            ["negative_mean_realized_r","all_mean_realized_r","max_dd_r","positive_survival_rate","policy"],
            ascending=[False,False,True,False,True]
        )
        winner=elig.iloc[0].to_dict()

    return rows,mt,base.to_dict(),winner


def confirmation_gates(m,static_m):
    return {
        "trades_n_ge_40":int(m["trades_n"])>=40,
        "positive_n_ge_25":int(m["positive_n"])>=25,
        "positive_survival_ge_80pct":bool(np.isfinite(m["positive_survival_rate"]) and m["positive_survival_rate"]>=.80),
        "buy_positive_survival_ge_75pct":bool(np.isfinite(m["buy_side_positive_survival"]) and m["buy_side_positive_survival"]>=.75),
        "sell_positive_survival_ge_75pct":bool(np.isfinite(m["sell_side_positive_survival"]) and m["sell_side_positive_survival"]>=.75),
        "score3_positive_survival_ge_80pct":bool(np.isfinite(m["score3_positive_survival"]) and m["score3_positive_survival"]>=.80),
        "score4_positive_survival_ge_60pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_survival"]) and m["score4_positive_survival"]>=.60)
        ),
        "negative_mean_improves_static_by_0_10r":bool(
            np.isfinite(m["negative_mean_realized_r"])
            and np.isfinite(static_m["negative_mean_realized_r"])
            and m["negative_mean_realized_r"]-static_m["negative_mean_realized_r"]>=.10
        ),
        "all_mean_realized_r_gt_static":bool(
            np.isfinite(m["all_mean_realized_r"])
            and np.isfinite(static_m["all_mean_realized_r"])
            and m["all_mean_realized_r"]>static_m["all_mean_realized_r"]
        ),
    }


def monitor_gates(m,static_m):
    sample={
        "trades_n_ge_20":int(m["trades_n"])>=20,
        "positive_n_ge_10":int(m["positive_n"])>=10,
    }
    quality={
        "positive_survival_ge_75pct":bool(np.isfinite(m["positive_survival_rate"]) and m["positive_survival_rate"]>=.75),
        "buy_survival_ge_65pct_if_n_ge5":bool(
            int(m["buy_side_positive_n"])<5 or
            (np.isfinite(m["buy_side_positive_survival"]) and m["buy_side_positive_survival"]>=.65)
        ),
        "sell_survival_ge_65pct_if_n_ge5":bool(
            int(m["sell_side_positive_n"])<5 or
            (np.isfinite(m["sell_side_positive_survival"]) and m["sell_side_positive_survival"]>=.65)
        ),
        "score3_survival_ge_75pct_if_n_ge5":bool(
            int(m["score3_positive_n"])<5 or
            (np.isfinite(m["score3_positive_survival"]) and m["score3_positive_survival"]>=.75)
        ),
        "score4_survival_ge_55pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_survival"]) and m["score4_positive_survival"]>=.55)
        ),
        "negative_mean_realized_r_gt_static":bool(
            np.isfinite(m["negative_mean_realized_r"])
            and np.isfinite(static_m["negative_mean_realized_r"])
            and m["negative_mean_realized_r"]>static_m["negative_mean_realized_r"]
        ),
        "all_mean_realized_r_gt_static":bool(
            np.isfinite(m["all_mean_realized_r"])
            and np.isfinite(static_m["all_mean_realized_r"])
            and m["all_mean_realized_r"]>static_m["all_mean_realized_r"]
        ),
    }
    return sample,quality


def render(title,m,static=None):
    pct=lambda v:"n/a" if not np.isfinite(v) else f"{v*100:.2f}%"
    num=lambda v,d=3:"n/a" if not np.isfinite(v) else f"{v:.{d}f}"
    lines=[
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- Positive events: **{int(m['positive_n'])}**",
        f"- Positive survival: **{pct(m['positive_survival_rate'])}**",
        f"- BUY positive survival: **{pct(m['buy_side_positive_survival'])}**",
        f"- SELL positive survival: **{pct(m['sell_side_positive_survival'])}**",
        f"- Score-3 positive survival: **{pct(m['score3_positive_survival'])}**",
        f"- Score-4 positive survival: **{pct(m['score4_positive_survival'])}**",
        f"- Management trigger rate: **{pct(m['management_trigger_rate'])}**",
        f"- Negative stop-hit rate: **{pct(m['negative_stop_hit_rate'])}**",
        f"- Negative mean realized R: **{num(m['negative_mean_realized_r'])}R**",
        f"- Negative median realized R: **{num(m['negative_median_realized_r'])}R**",
        f"- All-trade mean realized R at structural horizon: **{num(m['all_mean_realized_r'])}R**",
        f"- Cumulative realized R: **{num(m['cum_realized_r'])}R**",
        f"- Max DD: **{num(m['max_dd_r'])}R**",
        f"- Max losing streak: **{int(m['max_loss_streak'])}**",
        f"- Median time-to-exit: **{num(m['median_time_to_exit_min'],1)} min**",
        f"- Same-bar managed-stop hits: **{int(m['same_bar_managed_stop_hit_n'])**}",
    ]
    if static is not None:
        lines += [
            f"- Negative-mean improvement vs static: **{num(m['negative_mean_realized_r']-static['negative_mean_realized_r'])}R**",
            f"- All-mean improvement vs static: **{num(m['all_mean_realized_r']-static['all_mean_realized_r'])}R**",
        ]
    lines.append("")
    return lines


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Construction.
    tc,pc,hc,xc=prepare_period(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    crows,cmetrics,cstatic,winner=construction_select(tc,xc)

    crows.to_csv(ROOT/f"{PFX}_ConstructionTrades.csv",index=False)
    cmetrics.to_csv(ROOT/f"{PFX}_ConstructionMetrics.csv",index=False)

    if winner is None:
        verdict="NO_ADAPTIVE_RISK_MANAGER_CONSTRUCTION_RULE"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_trades":len(tc),
            "winner":"",
            "confirmation_2025_opened":False,
            "monitor_2026_opened":False,
            "verdict":verdict
        }])
        lines=[
            "# SOL Adaptive Risk Manager V1 — Result","",
            f"- Coverage: **{coverage*100:.6f}%**",
            f"- Construction trades: **{len(tc)}**",
            "- No adaptive post-entry risk manager met all frozen construction gates.",
            "",
            f"**VERDICT: {verdict}**","",
            "2027_PLUS=CLOSED"
        ]
    else:
        pname=str(winner["policy"])

        # 2025 confirmation; evaluate winner and static comparator independently.
        t25,p25,h25,x25=prepare_period(x5,CONFIRM_END,[2025])
        r25=simulate_policy(t25,x25,pname)
        rs25=simulate_policy(t25,x25,"STATIC_RECLAIM_EXTREME")
        m25=metrics(r25,pname)
        ms25=metrics(rs25,"STATIC_RECLAIM_EXTREME")
        g25=confirmation_gates(m25,ms25)
        pass25=all(g25.values())

        r25.to_csv(ROOT/f"{PFX}_Confirmation2025Trades.csv",index=False)
        pd.DataFrame([{
            **m25,
            "static_negative_mean_realized_r":ms25["negative_mean_realized_r"],
            "static_all_mean_realized_r":ms25["all_mean_realized_r"],
            **{f"gate_{k}":v for k,v in g25.items()}
        }]).to_csv(ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False)

        lines=[
            "# SOL Adaptive Risk Manager V1 — Result","",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Frozen construction winner: **{pname}**",
            "- Initial SL remains RECLAIM_EXTREME.",
            "- No TP is used in this experiment.",
            "- 2026 is secondary replication only, not independent validation.",""
        ]
        lines+=render("Construction 2020-2024",winner,cstatic)
        lines+=render("Frozen 2025 confirmation",m25,ms25)
        lines+=["## 2025 gate audit",""]
        for k,v in g25.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not pass25:
            verdict="ADAPTIVE_RISK_MANAGER_NOT_CONFIRMED_2025"
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
            summary=pd.DataFrame([{
                "coverage":coverage,
                "winner":pname,
                "construction_positive_survival":winner["positive_survival_rate"],
                "construction_negative_mean_r":winner["negative_mean_realized_r"],
                "confirmation_2025_positive_survival":m25["positive_survival_rate"],
                "confirmation_2025_negative_mean_r":m25["negative_mean_realized_r"],
                "confirmation_2025_passed":False,
                "monitor_2026_opened":False,
                "verdict":verdict
            }])
            lines+=["",f"**VERDICT: {verdict}**","",
                    "- 2026 monitor was not used because the frozen manager failed 2025 confirmation.","",
                    "2027_PLUS=CLOSED"]
        else:
            latest=(x5.index.max()+BAR5).floor("h")
            if latest<=CONFIRM_END:
                latest=CONFIRM_END

            t26,p26,h26,x26=prepare_period(x5,latest,[2026])
            r26=simulate_policy(t26,x26,pname)
            rs26=simulate_policy(t26,x26,"STATIC_RECLAIM_EXTREME")

            if len(r26):
                m26=metrics(r26,pname)
                ms26=metrics(rs26,"STATIC_RECLAIM_EXTREME")
            else:
                m26={
                    "policy":pname,"trades_n":0,"positive_n":0,
                    "positive_survival_rate":np.nan,"management_trigger_rate":np.nan,
                    "negative_n":0,"negative_stop_hit_rate":np.nan,
                    "negative_mean_realized_r":np.nan,"negative_median_realized_r":np.nan,
                    "all_mean_realized_r":np.nan,"cum_realized_r":0.0,
                    "max_dd_r":np.nan,"max_loss_streak":0,
                    "median_time_to_exit_min":np.nan,"same_bar_managed_stop_hit_n":0,
                    "buy_side_positive_n":0,"buy_side_positive_survival":np.nan,
                    "sell_side_positive_n":0,"sell_side_positive_survival":np.nan,
                    "score3_positive_n":0,"score3_positive_survival":np.nan,
                    "score4_positive_n":0,"score4_positive_survival":np.nan,
                }
                ms26=m26.copy()

            sample26,quality26=monitor_gates(m26,ms26)
            if not all(sample26.values()):
                verdict="ADAPTIVE_RISK_MANAGER_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT"
            elif all(quality26.values()):
                verdict="ADAPTIVE_RISK_MANAGER_CANDIDATE_REPLICATED_NOT_INDEPENDENT"
            else:
                verdict="ADAPTIVE_RISK_MANAGER_2026_MONITOR_DID_NOT_REPLICATE"

            r26.to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame([{
                **m26,
                "data_end":latest,
                "static_negative_mean_realized_r":ms26["negative_mean_realized_r"],
                "static_all_mean_realized_r":ms26["all_mean_realized_r"],
                **{f"sample_{k}":v for k,v in sample26.items()},
                **{f"gate_{k}":v for k,v in quality26.items()},
                "verdict":verdict
            }]).to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)

            summary=pd.DataFrame([{
                "coverage":coverage,
                "winner":pname,
                "construction_positive_survival":winner["positive_survival_rate"],
                "construction_negative_mean_r":winner["negative_mean_realized_r"],
                "confirmation_2025_positive_survival":m25["positive_survival_rate"],
                "confirmation_2025_negative_mean_r":m25["negative_mean_realized_r"],
                "confirmation_2025_passed":True,
                "monitor_2026_opened":True,
                "monitor_2026_data_end":latest,
                "monitor_2026_positive_survival":m26["positive_survival_rate"],
                "monitor_2026_negative_mean_r":m26["negative_mean_realized_r"],
                "verdict":verdict
            }])

            lines+=["","## 2025 verdict","","**PASS — frozen risk manager confirmed historically.**",""]
            lines+=render("2026 YTD secondary replication monitor",m26,ms26)
            lines+=["## 2026 sample audit",""]
            for k,v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["","## 2026 monitor quality audit",""]
            for k,v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["",f"**VERDICT: {verdict}**","",
                    "Passing 2026 is replication only. If this layer holds, TP may be re-run against the frozen risk-managed stack.","",
                    "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
