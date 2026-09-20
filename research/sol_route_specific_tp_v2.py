#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_tp_v1 as tp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ROUTE_SPECIFIC_TP_V2"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

ROUTER_NAME="SCORE3_100R__SCORE4_150R"
UNIFORM_NAME="FIXED_150R"


def reward_r(score:int)->float:
    if score==3:
        return 1.0
    if score==4:
        return 1.5
    raise ValueError(f"unexpected anatomy score {score}")


def simulate_router(trades:pd.DataFrame,x5:pd.DataFrame)->pd.DataFrame:
    rows=[]
    idx=x5.index
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()

    for _,r in trades.iterrows():
        entry=float(r.entry_price)
        stop=float(r.stop_price)
        risk=float(r.initial_risk_price)
        if not (np.isfinite(entry) and np.isfinite(stop) and np.isfinite(risk) and risk>0):
            continue

        score=int(r.anatomy_score)
        rr=reward_r(score)
        short=(str(r.side)=="BUY_SIDE")
        target=entry-rr*risk if short else entry+rr*risk

        start=int(r.entry_i_5m)
        end=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
        end=min(end,len(x5))
        if start<0 or start>=end:
            continue

        exit_type="TIME_EXIT"
        exit_i=-1
        exit_time=pd.NaT
        exit_price=np.nan
        realized=np.nan

        for i in range(start,end):
            sl_hit=bool(hi[i]>=stop) if short else bool(lo[i]<=stop)
            tp_hit=bool(lo[i]<=target) if short else bool(hi[i]>=target)

            if sl_hit:
                exit_type="SL"
                exit_i=i
                exit_time=idx[i]
                exit_price=stop
                realized=-1.0
                break

            if tp_hit:
                exit_type="TP"
                exit_i=i
                exit_time=idx[i]
                exit_price=target
                realized=rr
                break

        if exit_type=="TIME_EXIT":
            ei,et,ep=tp.time_exit_price(x5,r.outcome_known_time)
            if ei<0 or not np.isfinite(ep):
                continue
            exit_i=ei
            exit_time=et
            exit_price=ep
            realized=((entry-ep)/risk) if short else ((ep-entry)/risk)

        rows.append({
            "candidate":ROUTER_NAME,
            "candidate_id":r.candidate_id,
            "side":r.side,
            "anatomy_score":score,
            "assigned_route":r.assigned_route,
            "event_label":int(r.event_label),
            "outcome":r.outcome,
            "entry_time":r.entry_time,
            "entry_i_5m":int(r.entry_i_5m),
            "entry_price":entry,
            "stop_price":stop,
            "initial_risk_price":risk,
            "initial_risk_range_units":float(r.initial_risk_range_units),
            "structural_target":float(r.structural_target),
            "structural_reward_r":float(r.structural_reward_r),
            "reward_r":rr,
            "tp_price":target,
            "outcome_known_time":r.outcome_known_time,
            "exit_type":exit_type,
            "exit_i_5m":int(exit_i),
            "exit_time":exit_time,
            "exit_price":float(exit_price),
            "realized_r":float(realized),
            "time_to_exit_min":float(
                (pd.Timestamp(exit_time)-pd.Timestamp(r.entry_time)).total_seconds()/60.0
            ),
        })

    return pd.DataFrame(rows)


def halfyear(rows,candidate):
    g=rows[rows.candidate==candidate].copy()
    ts=pd.to_datetime(g.entry_time,utc=True)
    g["half"]=np.where(ts.dt.month<=6,"H1","H2")
    out=[]
    for h,gh in g.groupby("half"):
        out.append({
            "candidate":candidate,
            "half":h,
            "n":len(gh),
            "mean_r":float(gh.realized_r.mean()),
            "cum_r":float(gh.realized_r.sum()),
            "pf_r":float(tp.pf(gh.realized_r)),
        })
    return pd.DataFrame(out)


def construction_gates(m,y):
    posyears=int((y.cum_r>0).sum()) if len(y) else 0
    gates={
        "n_ge_180":int(m["trades_n"])>=180,
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_15":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.15),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "positive_years_ge_4_of_5":posyears>=4,
        "buy_mean_r_gt_0":bool(np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0),
        "sell_mean_r_gt_0":bool(np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0),
        "score3_mean_r_gt_0":bool(np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0":bool(np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0),
    }
    return gates,posyears


def consistency_gates(m,half,uniform_m):
    h1=float(half.loc[half.half=="H1","cum_r"].iloc[0]) if len(half[half.half=="H1"]) else np.nan
    h2=float(half.loc[half.half=="H2","cum_r"].iloc[0]) if len(half[half.half=="H2"]) else np.nan
    return {
        "n_ge_40":int(m["trades_n"])>=40,
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_05":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.05),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "buy_mean_r_gt_0":bool(np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0),
        "sell_mean_r_gt_0":bool(np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0),
        "score3_mean_r_gt_0":bool(np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0_if_n_ge5":bool(
            int(m["score4_n"])<5 or (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
        "h1_cum_r_gt_0":bool(np.isfinite(h1) and h1>0),
        "h2_cum_r_gt_0":bool(np.isfinite(h2) and h2>0),
        "mean_r_gt_uniform_150r":bool(
            np.isfinite(m["mean_r"]) and np.isfinite(uniform_m["mean_r"]) and m["mean_r"]>uniform_m["mean_r"]
        ),
    }


def monitor_gates(m,uniform_m):
    sample={"n_ge_20":int(m["trades_n"])>=20}
    quality={
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_05":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.05),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "buy_mean_r_gt_0_if_n_ge10":bool(
            int(m["buy_side_n"])<10 or (np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0)
        ),
        "sell_mean_r_gt_0_if_n_ge10":bool(
            int(m["sell_side_n"])<10 or (np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0)
        ),
        "score3_mean_r_gt_0_if_n_ge10":bool(
            int(m["score3_n"])<10 or (np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0)
        ),
        "score4_mean_r_gt_0_if_n_ge5":bool(
            int(m["score4_n"])<5 or (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
        "mean_r_ge_uniform_150r":bool(
            np.isfinite(m["mean_r"]) and np.isfinite(uniform_m["mean_r"]) and m["mean_r"]>=uniform_m["mean_r"]
        ),
    }
    return sample,quality


def fmt(v,d=3):
    return "n/a" if not np.isfinite(v) else ("inf" if np.isinf(v) else f"{v:.{d}f}")


def pct(v):
    return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"


def render(title,m,uniform=None):
    lines=[
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- TP / SL / TIME_EXIT: **{int(m['tp_n'])} / {int(m['sl_n'])} / {int(m['time_exit_n'])}**",
        f"- Gross WR: **{pct(m['win_rate'])}**",
        f"- Mean R: **{fmt(m['mean_r'])}R**",
        f"- PF: **{fmt(m['pf_r'])}**",
        f"- Cumulative R: **{fmt(m['cum_r'])}R**",
        f"- Max DD: **{fmt(m['max_dd_r'])}R**",
        f"- BUY mean R: **{fmt(m['buy_side_mean_r'])}R**",
        f"- SELL mean R: **{fmt(m['sell_side_mean_r'])}R**",
        f"- Score-3 mean R / PF: **{fmt(m['score3_mean_r'])} / {fmt(m['score3_pf_r'])}**",
        f"- Score-4 mean R / PF: **{fmt(m['score4_mean_r'])} / {fmt(m['score4_pf_r'])}**",
        f"- Median exit time: **{fmt(m['median_time_to_exit_min'],1)} min**",
    ]
    if uniform is not None:
        lines+= [
            f"- Uniform 1.5R comparator mean R: **{fmt(uniform['mean_r'])}R**",
            f"- Mean-R delta vs uniform 1.5R: **{fmt(m['mean_r']-uniform['mean_r'])}R/trade**",
        ]
    lines.append("")
    return lines


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Historical construction audit.
    tc,_,_,xc=tp.prepared_trades(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    rc=simulate_router(tc,xc)
    uc=tp.simulate_candidate(tc,xc,UNIFORM_NAME)
    mc=tp.metrics(rc,ROUTER_NAME)
    muc=tp.metrics(uc,UNIFORM_NAME)
    yc=tp.yearly(rc,ROUTER_NAME)
    cgates,posyears=construction_gates(mc,yc)

    rc.to_csv(ROOT/f"{PFX}_ConstructionTrades.csv",index=False)
    pd.DataFrame([{**mc,**{f"gate_{k}":v for k,v in cgates.items()}}]).to_csv(
        ROOT/f"{PFX}_ConstructionMetrics.csv",index=False
    )
    yc.to_csv(ROOT/f"{PFX}_ConstructionYears.csv",index=False)

    lines=[
        "# SOL Route-Specific TP V2 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- TP router frozen: **score 3 -> 1.0R; score 4 -> 1.5R**.",
        "- Initial SL remains RECLAIM_EXTREME.",
        "- 2025 is retrospective for this hypothesis, not untouched validation.",""
    ]
    lines+=render("Historical construction audit 2020-2024",mc,muc)
    lines+=["## Construction gate audit",""]
    for k,v in cgates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    if not all(cgates.values()):
        verdict="ROUTE_SPECIFIC_TP_FAILED_HISTORICAL_CONSTRUCTION_AUDIT"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025Metrics.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_mean_r":mc["mean_r"],
            "construction_pf":mc["pf_r"],
            "construction_uniform_150_mean_r":muc["mean_r"],
            "retrospective_2025_opened":False,
            "monitor_2026_opened":False,
            "verdict":verdict
        }])
        lines+=["",f"**VERDICT: {verdict}**","",
                "2025/2026 were not used because the exact router failed its own historical viability gates.","",
                "2027_PLUS=CLOSED"]
    else:
        # Retrospective 2025 consistency check.
        t25,_,_,x25=tp.prepared_trades(x5,CONFIRM_END,[2025])
        r25=simulate_router(t25,x25)
        u25=tp.simulate_candidate(t25,x25,UNIFORM_NAME)
        m25=tp.metrics(r25,ROUTER_NAME)
        mu25=tp.metrics(u25,UNIFORM_NAME)
        h25=halfyear(r25,ROUTER_NAME)
        g25=consistency_gates(m25,h25,mu25)
        pass25=all(g25.values())

        r25.to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        h25.to_csv(ROOT/f"{PFX}_Retrospective2025HalfYear.csv",index=False)
        pd.DataFrame([{
            **m25,
            "uniform_150_mean_r":mu25["mean_r"],
            "uniform_150_pf":mu25["pf_r"],
            **{f"gate_{k}":v for k,v in g25.items()}
        }]).to_csv(ROOT/f"{PFX}_Retrospective2025Metrics.csv",index=False)

        lines+=["","## Retrospective 2025 consistency check",""]
        lines+=render("",m25,mu25)[2:]
        lines+=["## 2025 half-year","",
                "| Half | N | Mean R | Cum R | PF |",
                "|---|---:|---:|---:|---:|"]
        for _,r in h25.iterrows():
            lines.append(f"| {r['half']} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.cum_r)} | {fmt(r.pf_r)} |")
        lines+=["","## 2025 consistency gates",""]
        for k,v in g25.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not pass25:
            verdict="ROUTE_SPECIFIC_TP_NOT_CONSISTENT_2025"
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
            summary=pd.DataFrame([{
                "coverage":coverage,
                "construction_mean_r":mc["mean_r"],
                "construction_pf":mc["pf_r"],
                "retrospective_2025_mean_r":m25["mean_r"],
                "retrospective_2025_pf":m25["pf_r"],
                "uniform_150_2025_mean_r":mu25["mean_r"],
                "retrospective_2025_consistent":False,
                "monitor_2026_opened":False,
                "verdict":verdict
            }])
            lines+=["",f"**VERDICT: {verdict}**","",
                    "2026 monitor remained unopened.","",
                    "2027_PLUS=CLOSED"]
        else:
            latest=(x5.index.max()+BAR5).floor("h")
            if latest<=CONFIRM_END:
                latest=CONFIRM_END

            t26,_,_,x26=tp.prepared_trades(x5,latest,[2026])
            r26=simulate_router(t26,x26)
            u26=tp.simulate_candidate(t26,x26,UNIFORM_NAME)
            if len(r26):
                m26=tp.metrics(r26,ROUTER_NAME)
                mu26=tp.metrics(u26,UNIFORM_NAME)
            else:
                m26={
                    "candidate":ROUTER_NAME,"trades_n":0,"tp_n":0,"sl_n":0,"time_exit_n":0,
                    "win_rate":np.nan,"mean_r":np.nan,"median_r":np.nan,"pf_r":np.nan,"cum_r":0.0,
                    "max_dd_r":np.nan,"max_loss_streak":0,"median_time_to_exit_min":np.nan,
                    "positive_event_tp_rate":np.nan,"negative_event_tp_rate":np.nan,
                    "buy_side_n":0,"buy_side_mean_r":np.nan,"buy_side_pf_r":np.nan,
                    "sell_side_n":0,"sell_side_mean_r":np.nan,"sell_side_pf_r":np.nan,
                    "score3_n":0,"score3_mean_r":np.nan,"score3_pf_r":np.nan,
                    "score4_n":0,"score4_mean_r":np.nan,"score4_pf_r":np.nan,
                }
                mu26={**m26,"candidate":UNIFORM_NAME}

            sample26,quality26=monitor_gates(m26,mu26)

            if not all(sample26.values()):
                verdict="ROUTE_SPECIFIC_TP_AWAITING_NEW_HOLDOUT"
            elif all(quality26.values()):
                verdict="ROUTE_SPECIFIC_TP_CANDIDATE_REPLICATED_NOT_INDEPENDENT"
            else:
                verdict="ROUTE_SPECIFIC_TP_2026_MONITOR_DID_NOT_REPLICATE"

            r26.to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame([{
                **m26,
                "data_end":latest,
                "uniform_150_mean_r":mu26["mean_r"],
                "uniform_150_pf":mu26["pf_r"],
                **{f"sample_{k}":v for k,v in sample26.items()},
                **{f"gate_{k}":v for k,v in quality26.items()},
                "verdict":verdict
            }]).to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)

            summary=pd.DataFrame([{
                "coverage":coverage,
                "construction_mean_r":mc["mean_r"],
                "construction_pf":mc["pf_r"],
                "retrospective_2025_mean_r":m25["mean_r"],
                "retrospective_2025_pf":m25["pf_r"],
                "uniform_150_2025_mean_r":mu25["mean_r"],
                "retrospective_2025_consistent":True,
                "monitor_2026_opened":True,
                "monitor_2026_data_end":latest,
                "monitor_2026_mean_r":m26["mean_r"],
                "monitor_2026_pf":m26["pf_r"],
                "uniform_150_2026_mean_r":mu26["mean_r"],
                "verdict":verdict
            }])

            lines+=["","## 2025 status","","**PASS — retrospective consistency gates passed.**",""]
            lines+=render("2026 YTD non-independent replication monitor",m26,mu26)
            lines+=["## 2026 monitor gates",""]
            for k,v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            for k,v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["",f"**VERDICT: {verdict}**","",
                    "A pass is still not independent validation. Fresh future data is required before the adaptive TP can be called validated.","",
                    "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
