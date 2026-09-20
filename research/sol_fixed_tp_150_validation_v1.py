#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_tp_v1 as tp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_FIXED_TP_150_VALIDATION_V1"
CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)
CANDIDATE="FIXED_150R"
FROZEN_CONSTRUCTION_MAX_DD=8.564768906532136

def half_metrics(rows):
    x=rows.copy()
    ts=pd.to_datetime(x.entry_time,utc=True)
    x["half"]=np.where(ts.dt.month<=6,"H1","H2")
    out=[]
    for h,g in x.groupby("half"):
        out.append({
            "half":h,
            "n":len(g),
            "mean_r":float(g.realized_r.mean()),
            "cum_r":float(g.realized_r.sum()),
            "pf_r":float(tp.pf(g.realized_r)),
        })
    return pd.DataFrame(out)

def confirmation_gates(m,half):
    h1=float(half.loc[half.half=="H1","cum_r"].iloc[0]) if len(half[half.half=="H1"]) else np.nan
    h2=float(half.loc[half.half=="H2","cum_r"].iloc[0]) if len(half[half.half=="H2"]) else np.nan
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
        "max_dd_le_1_5x_construction":bool(
            np.isfinite(m["max_dd_r"]) and m["max_dd_r"]<=1.5*FROZEN_CONSTRUCTION_MAX_DD
        ),
    }

def monitor_gates(m):
    sample={"trades_n_ge_20":int(m["trades_n"])>=20}
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
    }
    return sample,quality

def fmt(v,d=3):
    return "n/a" if not np.isfinite(v) else ("inf" if np.isinf(v) else f"{v:.{d}f}")

def pct(v):
    return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

def render(title,m):
    return [
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- TP / SL / time exit: **{int(m['tp_n'])} / {int(m['sl_n'])} / {int(m['time_exit_n'])}**",
        f"- Gross WR: **{pct(m['win_rate'])}**",
        f"- Mean realized R: **{fmt(m['mean_r'])}R**",
        f"- Median realized R: **{fmt(m['median_r'])}R**",
        f"- PF: **{fmt(m['pf_r'])}**",
        f"- Cumulative R: **{fmt(m['cum_r'])}R**",
        f"- Max DD: **{fmt(m['max_dd_r'])}R**",
        f"- Max losing streak: **{int(m['max_loss_streak'])}**",
        f"- BUY mean R / PF: **{fmt(m['buy_side_mean_r'])} / {fmt(m['buy_side_pf_r'])}**",
        f"- SELL mean R / PF: **{fmt(m['sell_side_mean_r'])} / {fmt(m['sell_side_pf_r'])}**",
        f"- Score-3 mean R / PF: **{fmt(m['score3_mean_r'])} / {fmt(m['score3_pf_r'])}**",
        f"- Score-4 mean R / PF: **{fmt(m['score4_mean_r'])} / {fmt(m['score4_pf_r'])}**",
        f"- Median time-to-exit: **{fmt(m['median_time_to_exit_min'],1)} min**",
        ""
    ]

def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Construction audit only, exact frozen candidate.
    tc,_,_,xc=tp.prepared_trades(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    rc=tp.simulate_candidate(tc,xc,CANDIDATE)
    mc=tp.metrics(rc,CANDIDATE)
    yc=tp.yearly(rc,CANDIDATE)

    rc.to_csv(ROOT/f"{PFX}_ConstructionAuditTrades.csv",index=False)
    pd.DataFrame([mc]).to_csv(ROOT/f"{PFX}_ConstructionAuditMetrics.csv",index=False)
    yc.to_csv(ROOT/f"{PFX}_ConstructionAuditYears.csv",index=False)

    # First TP-economic confirmation: 2025.
    t25,_,_,x25=tp.prepared_trades(x5,CONFIRM_END,[2025])
    r25=tp.simulate_candidate(t25,x25,CANDIDATE)
    m25=tp.metrics(r25,CANDIDATE)
    h25=half_metrics(r25)
    g25=confirmation_gates(m25,h25)
    pass25=all(g25.values())

    r25.to_csv(ROOT/f"{PFX}_Confirmation2025Trades.csv",index=False)
    h25.to_csv(ROOT/f"{PFX}_Confirmation2025HalfYear.csv",index=False)
    pd.DataFrame([{**m25,**{f"gate_{k}":v for k,v in g25.items()}}]).to_csv(
        ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False
    )

    lines=[
        "# SOL Fixed TP 1.5R Economic Validation V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Full upstream stack frozen.",
        "- TP frozen at **1.5R** only.",
        "- 2025 is the first TP-economic confirmation year.",
        "- No fees/slippage yet.",""
    ]
    lines+=render("Construction audit 2020-2024",mc)
    lines+=["## Frozen 2025 confirmation",""]+render("",m25)[2:]
    lines+=["## 2025 half-year","",
            "| Half | N | Mean R | Cum R | PF |",
            "|---|---:|---:|---:|---:|"]
    for _,r in h25.iterrows():
        lines.append(f"| {r['half']} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.cum_r)} | {fmt(r.pf_r)} |")
    lines+=["","## 2025 gate audit",""]
    for k,v in g25.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    if not pass25:
        verdict="FIXED_150R_ECONOMICS_NOT_CONFIRMED_2025"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_mean_r":mc["mean_r"],
            "construction_pf":mc["pf_r"],
            "confirmation_2025_mean_r":m25["mean_r"],
            "confirmation_2025_pf":m25["pf_r"],
            "confirmation_2025_cum_r":m25["cum_r"],
            "confirmation_2025_passed":False,
            "monitor_2026_opened":False,
            "verdict":verdict
        }])
        lines+=["",f"**VERDICT: {verdict}**","",
                "- 2026 monitor remained unopened.","",
                "2027_PLUS=CLOSED"]
    else:
        latest=(x5.index.max()+BAR5).floor("h")
        if latest<=CONFIRM_END:
            latest=CONFIRM_END
        t26,_,_,x26=tp.prepared_trades(x5,latest,[2026])
        r26=tp.simulate_candidate(t26,x26,CANDIDATE)
        m26=tp.metrics(r26,CANDIDATE) if len(r26) else {
            "candidate":CANDIDATE,"trades_n":0,"tp_n":0,"sl_n":0,"time_exit_n":0,
            "win_rate":np.nan,"mean_r":np.nan,"median_r":np.nan,"pf_r":np.nan,"cum_r":0.0,
            "max_dd_r":np.nan,"max_loss_streak":0,"median_time_to_exit_min":np.nan,
            "positive_event_tp_rate":np.nan,"negative_event_tp_rate":np.nan,
            "buy_side_n":0,"buy_side_mean_r":np.nan,"buy_side_pf_r":np.nan,
            "sell_side_n":0,"sell_side_mean_r":np.nan,"sell_side_pf_r":np.nan,
            "score3_n":0,"score3_mean_r":np.nan,"score3_pf_r":np.nan,
            "score4_n":0,"score4_mean_r":np.nan,"score4_pf_r":np.nan,
        }
        sample26,quality26=monitor_gates(m26)

        if not all(sample26.values()):
            verdict="FIXED_150R_CONFIRMED_2025_AWAITING_NEW_HOLDOUT"
        elif all(quality26.values()):
            verdict="FIXED_150R_ECONOMICS_REPLICATED_NOT_INDEPENDENT"
        else:
            verdict="FIXED_150R_2026_MONITOR_DID_NOT_REPLICATE"

        r26.to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
        pd.DataFrame([{
            **m26,
            "data_end":latest,
            **{f"sample_{k}":v for k,v in sample26.items()},
            **{f"gate_{k}":v for k,v in quality26.items()},
            "verdict":verdict
        }]).to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)

        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_mean_r":mc["mean_r"],
            "construction_pf":mc["pf_r"],
            "confirmation_2025_mean_r":m25["mean_r"],
            "confirmation_2025_pf":m25["pf_r"],
            "confirmation_2025_cum_r":m25["cum_r"],
            "confirmation_2025_passed":True,
            "monitor_2026_opened":True,
            "monitor_2026_data_end":latest,
            "monitor_2026_mean_r":m26["mean_r"],
            "monitor_2026_pf":m26["pf_r"],
            "monitor_2026_cum_r":m26["cum_r"],
            "verdict":verdict
        }])

        lines+=["","## 2025 verdict","","**PASS — FIXED 1.5R economics confirmed in 2025.**",""]
        lines+=render("2026 YTD secondary replication monitor",m26)
        lines+=["## 2026 monitor audit",""]
        for k,v in sample26.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        for k,v in quality26.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        lines+=["",f"**VERDICT: {verdict}**","",
                "Next layer after a pass is full-stack cost/slippage and production-readiness validation.","",
                "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
