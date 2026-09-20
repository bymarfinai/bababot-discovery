#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_adaptive_risk_manager_v1 as rm
import sol_adaptive_tp_v1 as tp
import sol_route_specific_tp_v2 as rtp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_STRUCTURAL_COMPLETION_EXIT_V1"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
RETRO_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)


def pf(rs):
    s=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(s[s>0].sum())
    neg=float(-s[s<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


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


def metrics(rows):
    g=rows.copy()
    if g.empty:
        return {}

    pos=g[g.event_label==1]
    neg=g[g.event_label==0]
    rs=g.realized_r.astype(float)

    out={
        "trades_n":len(g),
        "completion_exit_n":int((g.exit_type=="TIME_EXIT").sum()),
        "completion_exit_rate":float((g.exit_type=="TIME_EXIT").mean()),
        "sl_hit_n":int((g.exit_type=="STOP").sum()),
        "sl_hit_rate":float((g.exit_type=="STOP").mean()),
        "win_rate":float((rs>0).mean()),
        "mean_r":float(rs.mean()),
        "median_r":float(rs.median()),
        "pf_r":float(pf(rs)),
        "cum_r":float(rs.sum()),
        "max_dd_r":float(max_dd(rs)),
        "max_loss_streak":int(max_loss_streak(rs)),
        "median_time_to_exit_min":float(pd.to_numeric(g.time_to_exit_min,errors="coerce").median()),
        "positive_n":len(pos),
        "positive_mean_r":float(pos.realized_r.mean()) if len(pos) else np.nan,
        "positive_survival_to_completion":float((pos.exit_type=="TIME_EXIT").mean()) if len(pos) else np.nan,
        "negative_n":len(neg),
        "negative_mean_r":float(neg.realized_r.mean()) if len(neg) else np.nan,
    }

    for side in ("BUY_SIDE","SELL_SIDE"):
        z=g[g.side==side]
        out[f"{side.lower()}_n"]=len(z)
        out[f"{side.lower()}_mean_r"]=float(z.realized_r.mean()) if len(z) else np.nan
        out[f"{side.lower()}_pf_r"]=float(pf(z.realized_r)) if len(z) else np.nan

    for score in (3,4):
        z=g[g.anatomy_score==score]
        out[f"score{score}_n"]=len(z)
        out[f"score{score}_mean_r"]=float(z.realized_r.mean()) if len(z) else np.nan
        out[f"score{score}_pf_r"]=float(pf(z.realized_r)) if len(z) else np.nan

    return out


def yearly(rows):
    g=rows.copy()
    g["year"]=pd.to_datetime(g.entry_time,utc=True).dt.year.astype(int)
    out=[]
    for y,z in g.groupby("year"):
        out.append({
            "year":int(y),
            "n":len(z),
            "mean_r":float(z.realized_r.mean()),
            "cum_r":float(z.realized_r.sum()),
            "pf_r":float(pf(z.realized_r)),
            "win_rate":float((z.realized_r>0).mean()),
        })
    return pd.DataFrame(out)


def halfyear(rows):
    g=rows.copy()
    ts=pd.to_datetime(g.entry_time,utc=True)
    g["half"]=np.where(ts.dt.month<=6,"H1","H2")
    out=[]
    for h,z in g.groupby("half"):
        out.append({
            "half":h,
            "n":len(z),
            "mean_r":float(z.realized_r.mean()),
            "cum_r":float(z.realized_r.sum()),
            "pf_r":float(pf(z.realized_r)),
        })
    return pd.DataFrame(out)


def construction_gates(m,y):
    positive_years=int((y.cum_r>0).sum()) if len(y) else 0
    gates={
        "trades_n_ge_180":int(m["trades_n"])>=180,
        "mean_r_ge_0_05":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>=.05),
        "pf_ge_1_10":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.10),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "positive_years_ge_4_of_5":positive_years>=4,
        "buy_mean_r_gt_0":bool(np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0),
        "sell_mean_r_gt_0":bool(np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0),
        "score3_mean_r_gt_0":bool(np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0_if_n_ge20":bool(
            int(m["score4_n"])<20 or
            (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
    }
    return gates,positive_years


def retro_gates(m,h):
    h1=float(h.loc[h.half=="H1","cum_r"].iloc[0]) if len(h[h.half=="H1"]) else np.nan
    h2=float(h.loc[h.half=="H2","cum_r"].iloc[0]) if len(h[h.half=="H2"]) else np.nan
    return {
        "trades_n_ge_40":int(m["trades_n"])>=40,
        "mean_r_ge_0_05":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>=.05),
        "pf_ge_1_10":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.10),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "buy_mean_r_gt_0":bool(np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0),
        "sell_mean_r_gt_0":bool(np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0),
        "score3_mean_r_gt_0":bool(np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0_if_n_ge5":bool(
            int(m["score4_n"])<5 or
            (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
        "h1_cum_r_gt_0":bool(np.isfinite(h1) and h1>0),
        "h2_cum_r_gt_0":bool(np.isfinite(h2) and h2>0),
    }


def monitor_gates(m):
    sample={"trades_n_ge_20":int(m["trades_n"])>=20}
    quality={
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_05":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.05),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "buy_mean_r_gt_0_if_n_ge10":bool(
            int(m["buy_side_n"])<10 or
            (np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0)
        ),
        "sell_mean_r_gt_0_if_n_ge10":bool(
            int(m["sell_side_n"])<10 or
            (np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0)
        ),
        "score3_mean_r_gt_0_if_n_ge10":bool(
            int(m["score3_n"])<10 or
            (np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0)
        ),
        "score4_mean_r_gt_0_if_n_ge5":bool(
            int(m["score4_n"])<5 or
            (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
    }
    return sample,quality


def comparator_metrics(trades,x5):
    z=trades.copy()
    if "structural_reward_r" not in z.columns:
        side=z.side.astype(str)
        entry=pd.to_numeric(z.entry_price,errors="coerce")
        target=pd.to_numeric(z.structural_target,errors="coerce")
        risk=pd.to_numeric(z.initial_risk_price,errors="coerce")
        favorable=np.where(
            side.eq("BUY_SIDE"),
            entry-target,
            target-entry,
        )
        z["structural_reward_r"]=favorable/risk

    fixed=tp.simulate_candidate(z,x5,"FIXED_150R")
    route=rtp.simulate_router(z,x5)
    fm=tp.metrics(fixed,"FIXED_150R") if len(fixed) else {}
    rm=tp.metrics(route,rtp.ROUTER_NAME) if len(route) else {}
    return fixed,route,fm,rm


def fmt(v,d=3):
    if not np.isfinite(v):
        return "inf" if np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"


def render(title,m,fixed=None,route=None):
    lines=[
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- Structural-completion/time exits: **{int(m['completion_exit_n'])} ({pct(m['completion_exit_rate'])})**",
        f"- SL hits: **{int(m['sl_hit_n'])} ({pct(m['sl_hit_rate'])})**",
        f"- Gross WR: **{pct(m['win_rate'])}**",
        f"- Mean realized R: **{fmt(m['mean_r'])}R**",
        f"- Median realized R: **{fmt(m['median_r'])}R**",
        f"- PF: **{fmt(m['pf_r'])}**",
        f"- Cumulative R: **{fmt(m['cum_r'])}R**",
        f"- Max DD: **{fmt(m['max_dd_r'])}R**",
        f"- Max losing streak: **{int(m['max_loss_streak'])}**",
        f"- Positive-event mean R: **{fmt(m['positive_mean_r'])}R**",
        f"- Positive survival to completion: **{pct(m['positive_survival_to_completion'])}**",
        f"- Negative-event mean R: **{fmt(m['negative_mean_r'])}R**",
        f"- BUY mean R / PF: **{fmt(m['buy_side_mean_r'])} / {fmt(m['buy_side_pf_r'])}**",
        f"- SELL mean R / PF: **{fmt(m['sell_side_mean_r'])} / {fmt(m['sell_side_pf_r'])}**",
        f"- Score-3 mean R / PF: **{fmt(m['score3_mean_r'])} / {fmt(m['score3_pf_r'])}**",
        f"- Score-4 mean R / PF: **{fmt(m['score4_mean_r'])} / {fmt(m['score4_pf_r'])}**",
        f"- Median time-to-exit: **{fmt(m['median_time_to_exit_min'],1)} min**",
    ]
    if fixed:
        lines.append(f"- Comparator FIXED 1.5R mean/PF: **{fmt(fixed['mean_r'])}R / {fmt(fixed['pf_r'])}**")
    if route:
        lines.append(f"- Comparator route-specific TP mean/PF: **{fmt(route['mean_r'])}R / {fmt(route['pf_r'])}**")
    lines.append("")
    return lines


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Historical construction audit.
    tc,_,_,xc=rm.prepare_period(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    rc=rm.simulate_policy(tc,xc,"STATIC_RECLAIM_EXTREME")
    mc=metrics(rc)
    yc=yearly(rc)
    _,_,mfc,mrtc=comparator_metrics(tc,xc)
    cgates,posyears=construction_gates(mc,yc)
    passc=all(cgates.values())

    rc.to_csv(ROOT/f"{PFX}_ConstructionTrades.csv",index=False)
    yc.to_csv(ROOT/f"{PFX}_ConstructionYears.csv",index=False)
    pd.DataFrame([{**mc,**{f"gate_{k}":v for k,v in cgates.items()}}]).to_csv(
        ROOT/f"{PFX}_ConstructionMetrics.csv",index=False
    )

    lines=[
        "# SOL Structural-Completion Exit V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Exit rule: **static RECLAIM_EXTREME SL; otherwise exit when frozen structural state is known**.",
        "- No price TP and no post-entry tightening.",
        "- 2025 is retrospective consistency; 2026 is non-independent replication only.",""
    ]
    lines+=render("Historical construction audit 2020-2024",mc,mfc,mrtc)
    lines+=["## Construction gate audit",""]
    for k,v in cgates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    if not passc:
        verdict="STRUCTURAL_COMPLETION_EXIT_FAILED_HISTORICAL_AUDIT"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025Metrics.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025HalfYear.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_mean_r":mc["mean_r"],
            "construction_pf":mc["pf_r"],
            "construction_cum_r":mc["cum_r"],
            "retrospective_2025_opened":False,
            "monitor_2026_opened":False,
            "verdict":verdict,
        }])
        lines+=["",f"**VERDICT: {verdict}**","",
                "2025/2026 were not used because the exact exit failed the frozen historical viability gates.","",
                "2027_PLUS=CLOSED"]
    else:
        # Retrospective 2025 consistency.
        t25,_,_,x25=rm.prepare_period(x5,RETRO_END,[2025])
        r25=rm.simulate_policy(t25,x25,"STATIC_RECLAIM_EXTREME")
        m25=metrics(r25)
        h25=halfyear(r25)
        _,_,mf25,mrt25=comparator_metrics(t25,x25)
        g25=retro_gates(m25,h25)
        pass25=all(g25.values())

        r25.to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        h25.to_csv(ROOT/f"{PFX}_Retrospective2025HalfYear.csv",index=False)
        pd.DataFrame([{
            **m25,
            "fixed150_mean_r":mf25["mean_r"],
            "fixed150_pf":mf25["pf_r"],
            "route_tp_mean_r":mrt25["mean_r"],
            "route_tp_pf":mrt25["pf_r"],
            **{f"gate_{k}":v for k,v in g25.items()}
        }]).to_csv(ROOT/f"{PFX}_Retrospective2025Metrics.csv",index=False)

        lines+=["","## Retrospective 2025 consistency",""]
        lines+=render("",m25,mf25,mrt25)[2:]
        lines+=["## 2025 half-year","",
                "| Half | N | Mean R | Cum R | PF |",
                "|---|---:|---:|---:|---:|"]
        for _,r in h25.iterrows():
            lines.append(f"| {r['half']} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.cum_r)} | {fmt(r.pf_r)} |")
        lines+=["","## 2025 consistency gate audit",""]
        for k,v in g25.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not pass25:
            verdict="STRUCTURAL_COMPLETION_EXIT_NOT_CONSISTENT_2025"
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
            summary=pd.DataFrame([{
                "coverage":coverage,
                "construction_mean_r":mc["mean_r"],
                "construction_pf":mc["pf_r"],
                "retrospective_2025_mean_r":m25["mean_r"],
                "retrospective_2025_pf":m25["pf_r"],
                "retrospective_2025_consistent":False,
                "monitor_2026_opened":False,
                "verdict":verdict,
            }])
            lines+=["",f"**VERDICT: {verdict}**","",
                    "2026 monitor remained unopened.","",
                    "2027_PLUS=CLOSED"]
        else:
            latest=(x5.index.max()+BAR5).floor("h")
            if latest<=RETRO_END:
                latest=RETRO_END

            t26,_,_,x26=rm.prepare_period(x5,latest,[2026])
            r26=rm.simulate_policy(t26,x26,"STATIC_RECLAIM_EXTREME")
            if len(r26):
                m26=metrics(r26)
                _,_,mf26,mrt26=comparator_metrics(t26,x26)
            else:
                m26={
                    "trades_n":0,"completion_exit_n":0,"completion_exit_rate":np.nan,
                    "sl_hit_n":0,"sl_hit_rate":np.nan,"win_rate":np.nan,
                    "mean_r":np.nan,"median_r":np.nan,"pf_r":np.nan,"cum_r":0.0,
                    "max_dd_r":np.nan,"max_loss_streak":0,"median_time_to_exit_min":np.nan,
                    "positive_n":0,"positive_mean_r":np.nan,"positive_survival_to_completion":np.nan,
                    "negative_n":0,"negative_mean_r":np.nan,
                    "buy_side_n":0,"buy_side_mean_r":np.nan,"buy_side_pf_r":np.nan,
                    "sell_side_n":0,"sell_side_mean_r":np.nan,"sell_side_pf_r":np.nan,
                    "score3_n":0,"score3_mean_r":np.nan,"score3_pf_r":np.nan,
                    "score4_n":0,"score4_mean_r":np.nan,"score4_pf_r":np.nan,
                }
                mf26=mrt26={}

            sample26,quality26=monitor_gates(m26)
            if not all(sample26.values()):
                verdict="STRUCTURAL_COMPLETION_EXIT_AWAITING_NEW_HOLDOUT"
            elif all(quality26.values()):
                verdict="STRUCTURAL_COMPLETION_EXIT_CANDIDATE_REPLICATED_NOT_INDEPENDENT"
            else:
                verdict="STRUCTURAL_COMPLETION_EXIT_2026_MONITOR_DID_NOT_REPLICATE"

            r26.to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame([{
                **m26,
                "data_end":latest,
                "fixed150_mean_r":mf26.get("mean_r",np.nan),
                "fixed150_pf":mf26.get("pf_r",np.nan),
                "route_tp_mean_r":mrt26.get("mean_r",np.nan),
                "route_tp_pf":mrt26.get("pf_r",np.nan),
                **{f"sample_{k}":v for k,v in sample26.items()},
                **{f"gate_{k}":v for k,v in quality26.items()},
                "verdict":verdict,
            }]).to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)

            summary=pd.DataFrame([{
                "coverage":coverage,
                "construction_mean_r":mc["mean_r"],
                "construction_pf":mc["pf_r"],
                "retrospective_2025_mean_r":m25["mean_r"],
                "retrospective_2025_pf":m25["pf_r"],
                "retrospective_2025_consistent":True,
                "monitor_2026_opened":True,
                "monitor_2026_data_end":latest,
                "monitor_2026_mean_r":m26["mean_r"],
                "monitor_2026_pf":m26["pf_r"],
                "verdict":verdict,
            }])

            lines+=["","## 2025 status","","**PASS — retrospective consistency gates passed.**",""]
            lines+=render("2026 YTD non-independent replication monitor",m26,mf26,mrt26)
            lines+=["## 2026 monitor gate audit",""]
            for k,v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            for k,v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["",f"**VERDICT: {verdict}**","",
                    "A passing result is a replicated candidate, not independent validation. Fresh future data is still required.","",
                    "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
