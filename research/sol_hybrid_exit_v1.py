#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_adaptive_risk_manager_v1 as rm
import sol_adaptive_tp_v1 as tp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_HYBRID_EXIT_V1"

END_2024=pd.Timestamp("2025-01-01",tz="UTC")
END_2025=pd.Timestamp("2026-01-01",tz="UTC")
FRESH_CUTOFF=pd.Timestamp("2026-08-26 00:00:00",tz="UTC")
BAR5=pd.Timedelta(minutes=5)


def pf(rs):
    s=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def max_dd(rs):
    s=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    if s.empty: return np.nan
    eq=s.cumsum(); peak=eq.cummax().clip(lower=0.0)
    return float((peak-eq).max())


def max_ls(rs):
    cur=best=0
    for x in pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna():
        if x<0:
            cur+=1; best=max(best,cur)
        else:
            cur=0
    return best


def hybrid_simulate(trades: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    parts=[]

    s3=trades[trades.anatomy_score==3].copy()
    if len(s3):
        a=rm.simulate_policy(s3,x5,"STATIC_RECLAIM_EXTREME").copy()
        a["hybrid_route"]="SCORE3_STRUCTURAL_COMPLETION"
        a["exit_type_norm"]=a.exit_type.replace({"STOP":"SL"})
        cols=[
            "candidate_id","side","anatomy_score","assigned_route","event_label","outcome",
            "entry_time","entry_price","initial_risk_price","outcome_known_time",
            "exit_type_norm","exit_time","exit_price","realized_r","time_to_exit_min","hybrid_route"
        ]
        parts.append(a[cols])

    s4=trades[trades.anatomy_score==4].copy()
    if len(s4):
        b=tp.simulate_candidate(s4,x5,"FIXED_150R").copy()
        b["hybrid_route"]="SCORE4_FIXED_150R"
        b["exit_type_norm"]=b.exit_type
        cols=[
            "candidate_id","side","anatomy_score","assigned_route","event_label","outcome",
            "entry_time","entry_price","initial_risk_price","outcome_known_time",
            "exit_type_norm","exit_time","exit_price","realized_r","time_to_exit_min","hybrid_route"
        ]
        parts.append(b[cols])

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts,ignore_index=True).sort_values(["entry_time","candidate_id"]).reset_index(drop=True)


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return {}
    rs=g.realized_r.astype(float)
    out={
        "trades_n":len(g),
        "tp_n":int((g.exit_type_norm=="TP").sum()),
        "sl_n":int((g.exit_type_norm=="SL").sum()),
        "time_exit_n":int((g.exit_type_norm=="TIME_EXIT").sum()),
        "win_rate":float((rs>0).mean()),
        "mean_r":float(rs.mean()),
        "median_r":float(rs.median()),
        "pf_r":float(pf(rs)),
        "cum_r":float(rs.sum()),
        "max_dd_r":float(max_dd(rs)),
        "max_loss_streak":int(max_ls(rs)),
        "median_time_to_exit_min":float(pd.to_numeric(g.time_to_exit_min,errors="coerce").median()),
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


def yearly(g):
    x=g.copy(); x["year"]=pd.to_datetime(x.entry_time,utc=True).dt.year.astype(int)
    rows=[]
    for y,z in x.groupby("year"):
        rows.append({"year":int(y),"n":len(z),"mean_r":float(z.realized_r.mean()),
                     "cum_r":float(z.realized_r.sum()),"pf_r":float(pf(z.realized_r))})
    return pd.DataFrame(rows)


def halfyear(g):
    x=g.copy(); ts=pd.to_datetime(x.entry_time,utc=True)
    x["half"]=np.where(ts.dt.month<=6,"H1","H2")
    rows=[]
    for h,z in x.groupby("half"):
        rows.append({"half":h,"n":len(z),"mean_r":float(z.realized_r.mean()),
                     "cum_r":float(z.realized_r.sum()),"pf_r":float(pf(z.realized_r))})
    return pd.DataFrame(rows)


def comparators(trades,x5):
    # tp.prepared_trades already includes structural_reward_r required by tp simulator.
    fixed=tp.simulate_candidate(trades,x5,"FIXED_150R")
    # all structural-completion comparator
    structural=rm.simulate_policy(trades,x5,"STATIC_RECLAIM_EXTREME")
    fm=tp.metrics(fixed,"FIXED_150R") if len(fixed) else {}
    sm={
        "mean_r":float(structural.realized_r.mean()),
        "pf_r":float(pf(structural.realized_r)),
        "cum_r":float(structural.realized_r.sum())
    } if len(structural) else {}
    return fm,sm


def hist_gates(m,y):
    py=int((y.cum_r>0).sum()) if len(y) else 0
    return {
        "n_ge_180":int(m["trades_n"])>=180,
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_15":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.15),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "positive_years_ge_4_of_5":py>=4,
        "buy_mean_r_gt_0":bool(np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0),
        "sell_mean_r_gt_0":bool(np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0),
        "score3_mean_r_gt_0":bool(np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0_if_n_ge20":bool(
            int(m["score4_n"])<20 or (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
    }


def gates_2025(m,h):
    h1=float(h.loc[h.half=="H1","cum_r"].iloc[0]) if len(h[h.half=="H1"]) else np.nan
    h2=float(h.loc[h.half=="H2","cum_r"].iloc[0]) if len(h[h.half=="H2"]) else np.nan
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
    }


def gates_2026_pre(m):
    return {
        "n_ge_20":int(m["trades_n"])>=20,
        "mean_r_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
        "pf_ge_1_05":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.05),
        "cum_r_gt_0":bool(np.isfinite(m["cum_r"]) and m["cum_r"]>0),
        "score3_mean_r_gt_0_if_n_ge10":bool(
            int(m["score3_n"])<10 or (np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0)
        ),
        "score4_mean_r_gt_0_if_n_ge5":bool(
            int(m["score4_n"])<5 or (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
        ),
    }


def fresh_gates(m):
    sample={
        "n_ge_30":int(m.get("trades_n",0))>=30,
        "score3_n_ge_15":int(m.get("score3_n",0))>=15,
        "score4_n_ge_5":int(m.get("score4_n",0))>=5,
    }
    quality={
        "mean_r_gt_0":bool(np.isfinite(m.get("mean_r",np.nan)) and m["mean_r"]>0),
        "pf_ge_1_10":bool(np.isfinite(m.get("pf_r",np.nan)) and m["pf_r"]>=1.10),
        "cum_r_gt_0":bool(np.isfinite(m.get("cum_r",np.nan)) and m["cum_r"]>0),
        "buy_mean_r_gt_0_if_n_ge10":bool(
            int(m.get("buy_side_n",0))<10 or
            (np.isfinite(m.get("buy_side_mean_r",np.nan)) and m["buy_side_mean_r"]>0)
        ),
        "sell_mean_r_gt_0_if_n_ge10":bool(
            int(m.get("sell_side_n",0))<10 or
            (np.isfinite(m.get("sell_side_mean_r",np.nan)) and m["sell_side_mean_r"]>0)
        ),
        "score3_mean_r_gt_0":bool(np.isfinite(m.get("score3_mean_r",np.nan)) and m["score3_mean_r"]>0),
        "score4_mean_r_gt_0":bool(np.isfinite(m.get("score4_mean_r",np.nan)) and m["score4_mean_r"]>0),
    }
    return sample,quality


def fmt(v,d=3):
    if v is None or not np.isfinite(v):
        return "inf" if v is not None and np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{v*100:.2f}%"


def render(title,m,fixed=None,structural=None):
    if not m:
        return [f"## {title}","","- No eligible trades.",""]
    lines=[
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- TP / SL / TIME_EXIT: **{int(m['tp_n'])} / {int(m['sl_n'])} / {int(m['time_exit_n'])}**",
        f"- Gross WR: **{pct(m['win_rate'])}**",
        f"- Mean R: **{fmt(m['mean_r'])}R**",
        f"- Median R: **{fmt(m['median_r'])}R**",
        f"- PF: **{fmt(m['pf_r'])}**",
        f"- Cumulative R: **{fmt(m['cum_r'])}R**",
        f"- Max DD: **{fmt(m['max_dd_r'])}R**",
        f"- Max losing streak: **{int(m['max_loss_streak'])}**",
        f"- BUY mean/PF: **{fmt(m['buy_side_mean_r'])} / {fmt(m['buy_side_pf_r'])}**",
        f"- SELL mean/PF: **{fmt(m['sell_side_mean_r'])} / {fmt(m['sell_side_pf_r'])}**",
        f"- Score-3 mean/PF: **{fmt(m['score3_mean_r'])} / {fmt(m['score3_pf_r'])}**",
        f"- Score-4 mean/PF: **{fmt(m['score4_mean_r'])} / {fmt(m['score4_pf_r'])}**",
        f"- Median exit time: **{fmt(m['median_time_to_exit_min'],1)} min**",
    ]
    if fixed:
        lines.append(f"- Uniform 1.5R comparator mean/PF: **{fmt(fixed.get('mean_r',np.nan))} / {fmt(fixed.get('pf_r',np.nan))}**")
    if structural:
        lines.append(f"- All-structural-completion comparator mean/PF: **{fmt(structural.get('mean_r',np.nan))} / {fmt(structural.get('pf_r',np.nan))}**")
    lines.append("")
    return lines


def prep(x5,end_time,years):
    return tp.prepared_trades(x5,end_time,years)


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    latest=(x5.index.max()+BAR5).floor("h")
    if latest<END_2025: latest=END_2025

    # 2020-2024 retrospective.
    t0,_,_,x0=prep(x5,END_2024,[2020,2021,2022,2023,2024])
    r0=hybrid_simulate(t0,x0); m0=metrics(r0); y0=yearly(r0)
    f0,s0=comparators(t0,x0); g0=hist_gates(m0,y0)
    r0.to_csv(ROOT/f"{PFX}_Historical2020_2024Trades.csv",index=False)
    y0.to_csv(ROOT/f"{PFX}_Historical2020_2024Years.csv",index=False)
    pd.DataFrame([{**m0,**{f"gate_{k}":v for k,v in g0.items()}}]).to_csv(ROOT/f"{PFX}_Historical2020_2024Metrics.csv",index=False)

    lines=[
        "# SOL Hybrid Exit V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Frozen hybrid: **Score 3 -> structural completion; Score 4 -> fixed 1.5R**.",
        f"- Fresh cutoff frozen at **{FRESH_CUTOFF}**.",
        "- All earlier data are retrospective for this hypothesis.",""
    ]
    lines+=render("Retrospective 2020-2024 audit",m0,f0,s0)
    lines+=["## 2020-2024 gate audit",""]
    for k,v in g0.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    if not all(g0.values()):
        verdict="HYBRID_EXIT_FAILED_HISTORICAL_AUDIT"
        summary={"coverage":coverage,"latest_data":latest,"verdict":verdict}
        for p in ("Retrospective2025Trades.csv","Retrospective2025Metrics.csv","Retrospective2025HalfYear.csv","Retrospective2026PreCutoffTrades.csv","Retrospective2026PreCutoffMetrics.csv","FreshHoldoutTrades.csv","FreshHoldoutMetrics.csv"):
            pd.DataFrame().to_csv(ROOT/f"{PFX}_{p}",index=False)
    else:
        # 2025 retrospective.
        t25,_,_,x25=prep(x5,END_2025,[2025])
        r25=hybrid_simulate(t25,x25); m25=metrics(r25); h25=halfyear(r25)
        f25,s25=comparators(t25,x25); g25=gates_2025(m25,h25)
        r25.to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        h25.to_csv(ROOT/f"{PFX}_Retrospective2025HalfYear.csv",index=False)
        pd.DataFrame([{**m25,**{f"gate_{k}":v for k,v in g25.items()}}]).to_csv(ROOT/f"{PFX}_Retrospective2025Metrics.csv",index=False)

        lines+=[""]+render("Retrospective 2025 consistency",m25,f25,s25)
        lines+=["## 2025 half-year","",
                "| Half | N | Mean R | Cum R | PF |",
                "|---|---:|---:|---:|---:|"]
        for _,r in h25.iterrows():
            lines.append(f"| {r['half']} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.cum_r)} | {fmt(r.pf_r)} |")
        lines+=["","## 2025 gate audit",""]
        for k,v in g25.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not all(g25.values()):
            verdict="HYBRID_EXIT_NOT_CONSISTENT_2025"
            summary={"coverage":coverage,"latest_data":latest,"retrospective_2025_mean_r":m25["mean_r"],"verdict":verdict}
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffTrades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffMetrics.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutMetrics.csv",index=False)
        else:
            # Build full available 2026 once, then split strictly by entry timestamp.
            t26,_,_,x26=prep(x5,latest,[2026])
            pre=t26[pd.to_datetime(t26.entry_time,utc=True)<FRESH_CUTOFF].copy()
            fresh=t26[pd.to_datetime(t26.entry_time,utc=True)>=FRESH_CUTOFF].copy()

            rpre=hybrid_simulate(pre,x26); mpre=metrics(rpre); gpre=gates_2026_pre(mpre)
            fpre,spre=comparators(pre,x26) if len(pre) else ({},{})
            rpre.to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffTrades.csv",index=False)
            pd.DataFrame([{**mpre,**{f"gate_{k}":v for k,v in gpre.items()}}]).to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffMetrics.csv",index=False)

            lines+=[""]+render("Retrospective 2026 pre-cutoff consistency",mpre,fpre,spre)
            lines+=["## 2026 pre-cutoff gate audit",""]
            for k,v in gpre.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

            if not all(gpre.values()):
                verdict="HYBRID_EXIT_NOT_CONSISTENT_2026_PRE_CUTOFF"
                summary={"coverage":coverage,"latest_data":latest,"retrospective_2026_pre_mean_r":mpre["mean_r"],"verdict":verdict}
                pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
                pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutMetrics.csv",index=False)
            else:
                rfresh=hybrid_simulate(fresh,x26) if len(fresh) else pd.DataFrame()
                mfresh=metrics(rfresh) if len(rfresh) else {}
                sample,quality=fresh_gates(mfresh)
                rfresh.to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
                pd.DataFrame([{
                    **mfresh,
                    "cutoff":FRESH_CUTOFF,
                    "latest_data":latest,
                    **{f"sample_{k}":v for k,v in sample.items()},
                    **{f"gate_{k}":v for k,v in quality.items()},
                }]).to_csv(ROOT/f"{PFX}_FreshHoldoutMetrics.csv",index=False)

                lines+=["","## Frozen candidate status","",
                        "**PASS — all retrospective consistency audits passed. Hybrid rule is now frozen.**",""]
                lines+=render("Fresh post-cutoff holdout",mfresh)
                lines+=["## Fresh holdout audit",""]
                for k,v in sample.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
                for k,v in quality.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

                if not all(sample.values()):
                    verdict="HYBRID_EXIT_CANDIDATE_FROZEN_AWAITING_FRESH_HOLDOUT"
                elif all(quality.values()):
                    verdict="HYBRID_EXIT_VALIDATED_ON_FRESH_HOLDOUT"
                else:
                    verdict="HYBRID_EXIT_FAILED_FRESH_HOLDOUT"

                summary={
                    "coverage":coverage,"latest_data":latest,
                    "historical_mean_r":m0["mean_r"],
                    "retrospective_2025_mean_r":m25["mean_r"],
                    "retrospective_2026_pre_mean_r":mpre["mean_r"],
                    "fresh_trades_n":mfresh.get("trades_n",0),
                    "fresh_mean_r":mfresh.get("mean_r",np.nan),
                    "fresh_pf":mfresh.get("pf_r",np.nan),
                    "verdict":verdict
                }

    lines+=["",f"**VERDICT: {verdict}**","",
            "No pre-cutoff evidence is labeled independent validation. The rule is not allowed to change after this freeze.",""]
    pd.DataFrame([summary]).to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
