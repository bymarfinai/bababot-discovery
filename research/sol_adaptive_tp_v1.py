#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_adaptive_sl_v1 as sl
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ADAPTIVE_TP_V1"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

CANDIDATES=(
    "FIXED_075R",
    "FIXED_100R",
    "FIXED_150R",
    "STRUCTURAL_CAP_100R",
    "STRUCTURAL_CAP_150R",
    "STRUCTURAL_CAP_200R",
)


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


def reward_r(candidate,structural_reward_r):
    if candidate=="FIXED_075R": return .75
    if candidate=="FIXED_100R": return 1.0
    if candidate=="FIXED_150R": return 1.5
    if candidate=="STRUCTURAL_CAP_100R":
        return float(np.clip(structural_reward_r,.50,1.00))
    if candidate=="STRUCTURAL_CAP_150R":
        return float(np.clip(structural_reward_r,.50,1.50))
    if candidate=="STRUCTURAL_CAP_200R":
        return float(np.clip(structural_reward_r,.50,2.00))
    raise ValueError(candidate)


def prepared_trades(x5,end_time,years):
    entries,pop,h1,x=sl.prepare_period(x5,end_time,years)
    stops=sl.evaluate_policy(entries,pop,h1,x,"RECLAIM_EXTREME")
    if stops.empty:
        return pd.DataFrame(),pop,h1,x

    keep=[
        "candidate_id","stop_price","initial_risk_range_units",
        "outcome_known_time"
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

    side=z.side.astype(str)
    target=pd.to_numeric(z.structural_target,errors="coerce")
    entry=pd.to_numeric(z.entry_price,errors="coerce")
    risk=pd.to_numeric(z.initial_risk_price,errors="coerce")

    favorable=np.where(
        side.eq("BUY_SIDE"),
        entry-target,
        target-entry
    )
    z["structural_reward_r"]=favorable/risk
    return z.reset_index(drop=True),pop,h1,x


def time_exit_price(x5,outcome_known_time):
    idx=int(x5.index.searchsorted(pd.Timestamp(outcome_known_time),side="left"))
    if idx<len(x5) and x5.index[idx]==pd.Timestamp(outcome_known_time):
        return idx,x5.index[idx],float(x5.iloc[idx].open)
    if idx<len(x5):
        return idx,x5.index[idx],float(x5.iloc[idx].open)
    if len(x5):
        return len(x5)-1,x5.index[-1],float(x5.iloc[-1].close)
    return -1,pd.NaT,np.nan


def simulate_candidate(trades,x5,candidate):
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

        rr=reward_r(candidate,float(r.structural_reward_r))
        short=(str(r.side)=="BUY_SIDE")
        tp=entry-rr*risk if short else entry+rr*risk

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
            tp_hit=bool(lo[i]<=tp) if short else bool(hi[i]>=tp)

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
                exit_price=tp
                realized=rr
                break

        if exit_type=="TIME_EXIT":
            ei,et,ep=time_exit_price(x5,r.outcome_known_time)
            if ei<0 or not np.isfinite(ep):
                continue
            exit_i=ei
            exit_time=et
            exit_price=ep
            realized=((entry-ep)/risk) if short else ((ep-entry)/risk)

        rows.append({
            "candidate":candidate,
            "candidate_id":r.candidate_id,
            "side":r.side,
            "anatomy_score":int(r.anatomy_score),
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
            "tp_price":tp,
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


def metrics(rows,candidate):
    g=rows[rows.candidate==candidate].copy()
    if g.empty:
        return {}

    pos=g[g.event_label==1]
    neg=g[g.event_label==0]
    rs=g.realized_r.astype(float)

    out={
        "candidate":candidate,
        "trades_n":len(g),
        "tp_n":int((g.exit_type=="TP").sum()),
        "tp_rate":float((g.exit_type=="TP").mean()),
        "sl_n":int((g.exit_type=="SL").sum()),
        "sl_rate":float((g.exit_type=="SL").mean()),
        "time_exit_n":int((g.exit_type=="TIME_EXIT").sum()),
        "time_exit_rate":float((g.exit_type=="TIME_EXIT").mean()),
        "win_rate":float((rs>0).mean()),
        "mean_r":float(rs.mean()),
        "median_r":float(rs.median()),
        "pf_r":float(pf(rs)),
        "cum_r":float(rs.sum()),
        "max_dd_r":float(max_dd(rs)),
        "max_loss_streak":int(max_loss_streak(rs)),
        "median_time_to_exit_min":float(pd.to_numeric(g.time_to_exit_min,errors="coerce").median()),
        "positive_event_tp_rate":float((pos.exit_type=="TP").mean()) if len(pos) else np.nan,
        "negative_event_tp_rate":float((neg.exit_type=="TP").mean()) if len(neg) else np.nan,
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


def yearly(rows,candidate):
    g=rows[rows.candidate==candidate].copy()
    g["year"]=pd.to_datetime(g.entry_time,utc=True).dt.year.astype(int)
    out=[]
    for y,gy in g.groupby("year"):
        out.append({
            "candidate":candidate,
            "year":int(y),
            "n":len(gy),
            "mean_r":float(gy.realized_r.mean()),
            "cum_r":float(gy.realized_r.sum()),
            "pf_r":float(pf(gy.realized_r)),
            "win_rate":float((gy.realized_r>0).mean()),
        })
    return pd.DataFrame(out)


def halfyear(rows,candidate):
    g=rows[rows.candidate==candidate].copy()
    ts=pd.to_datetime(g.entry_time,utc=True)
    g["half"]=np.where(ts.dt.month<=6,"H1","H2")
    out=[]
    for h,gh in g.groupby("half"):
        out.append({
            "half":h,
            "n":len(gh),
            "mean_r":float(gh.realized_r.mean()),
            "cum_r":float(gh.realized_r.sum()),
            "pf_r":float(pf(gh.realized_r)),
        })
    return pd.DataFrame(out)


def construction_select(trades,x5):
    allrows=[]
    mets=[]
    years_all=[]

    for c in CANDIDATES:
        r=simulate_candidate(trades,x5,c)
        allrows.append(r)
        m=metrics(r,c)
        y=yearly(r,c)
        years_all.append(y)

        posyears=int((y.cum_r>0).sum()) if len(y) else 0
        elig=bool(
            m
            and m["trades_n"]>=180
            and np.isfinite(m["mean_r"]) and m["mean_r"]>=.15
            and np.isfinite(m["pf_r"]) and m["pf_r"]>=1.25
            and np.isfinite(m["positive_event_tp_rate"]) and m["positive_event_tp_rate"]>=.60
            and posyears>=4
            and np.isfinite(m["buy_side_mean_r"]) and m["buy_side_mean_r"]>0
            and np.isfinite(m["sell_side_mean_r"]) and m["sell_side_mean_r"]>0
            and np.isfinite(m["score3_mean_r"]) and m["score3_mean_r"]>0
            and (
                int(m["score4_n"])<20
                or (np.isfinite(m["score4_mean_r"]) and m["score4_mean_r"]>0)
            )
        )
        m["positive_years"]=posyears
        m["eligible"]=elig
        mets.append(m)

    rows=pd.concat(allrows,ignore_index=True)
    mt=pd.DataFrame(mets)
    yt=pd.concat(years_all,ignore_index=True)

    elig=mt[mt.eligible].copy()
    winner=None
    if len(elig):
        elig=elig.sort_values(
            ["mean_r","pf_r","max_dd_r","positive_event_tp_rate","median_time_to_exit_min","candidate"],
            ascending=[False,False,True,False,True,True]
        )
        winner=elig.iloc[0].to_dict()

    return rows,mt,yt,winner


def confirmation_gates(m,half):
    h1=float(half.loc[half.half=="H1","cum_r"].iloc[0]) if len(half[half.half=="H1"]) else np.nan
    h2=float(half.loc[half.half=="H2","cum_r"].iloc[0]) if len(half[half.half=="H2"]) else np.nan
    return {
        "trades_n_ge_40":int(m["trades_n"])>=40,
        "mean_r_ge_0_10":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>=.10),
        "pf_ge_1_15":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.15),
        "positive_event_tp_rate_ge_55pct":bool(
            np.isfinite(m["positive_event_tp_rate"]) and m["positive_event_tp_rate"]>=.55
        ),
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
        "pf_ge_1_10":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.10),
        "positive_event_tp_rate_ge_50pct":bool(
            np.isfinite(m["positive_event_tp_rate"]) and m["positive_event_tp_rate"]>=.50
        ),
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


def render(title,m):
    pct=lambda v:"n/a" if not np.isfinite(v) else f"{v*100:.2f}%"
    num=lambda v,d=3:"n/a" if not np.isfinite(v) else f"{v:.{d}f}"
    pfmt=lambda v:"n/a" if not np.isfinite(v) else ("inf" if np.isinf(v) else f"{v:.3f}")
    return [
        f"## {title}","",
        f"- Trades: **{int(m['trades_n'])}**",
        f"- TP hit: **{int(m['tp_n'])} ({pct(m['tp_rate'])})**",
        f"- SL hit: **{int(m['sl_n'])} ({pct(m['sl_rate'])})**",
        f"- Time exit: **{int(m['time_exit_n'])} ({pct(m['time_exit_rate'])})**",
        f"- Gross WR: **{pct(m['win_rate'])}**",
        f"- Mean realized R: **{num(m['mean_r'])}R**",
        f"- Median realized R: **{num(m['median_r'])}R**",
        f"- PF: **{pfmt(m['pf_r'])}**",
        f"- Cumulative R: **{num(m['cum_r'])}R**",
        f"- Max DD: **{num(m['max_dd_r'])}R**",
        f"- Max losing streak: **{int(m['max_loss_streak'])}**",
        f"- Positive-event TP rate: **{pct(m['positive_event_tp_rate'])}**",
        f"- Negative-event TP rate: **{pct(m['negative_event_tp_rate'])}**",
        f"- BUY mean R / PF: **{num(m['buy_side_mean_r'])} / {pfmt(m['buy_side_pf_r'])}**",
        f"- SELL mean R / PF: **{num(m['sell_side_mean_r'])} / {pfmt(m['sell_side_pf_r'])}**",
        f"- Score-3 mean R / PF: **{num(m['score3_mean_r'])} / {pfmt(m['score3_pf_r'])}**",
        f"- Score-4 mean R / PF: **{num(m['score4_mean_r'])} / {pfmt(m['score4_pf_r'])}**",
        f"- Median time-to-exit: **{num(m['median_time_to_exit_min'],1)} min**",
        ""
    ]


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Construction.
    tc,pc,hc,xc=prepared_trades(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024])
    crows,cmetrics,cyears,winner=construction_select(tc,xc)
    crows.to_csv(ROOT/f"{PFX}_ConstructionTrades.csv",index=False)
    cmetrics.to_csv(ROOT/f"{PFX}_ConstructionMetrics.csv",index=False)
    cyears.to_csv(ROOT/f"{PFX}_ConstructionYearSummary.csv",index=False)

    if winner is None:
        verdict="NO_ADAPTIVE_TP_CONSTRUCTION_RULE"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Confirmation2025HalfYear.csv",index=False)
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
            "# SOL Adaptive TP V1 — Result","",
            f"- Coverage: **{coverage*100:.6f}%**",
            f"- Construction trades: **{len(tc)}**",
            "- No frozen TP candidate met all construction gates.",
            "",
            f"**VERDICT: {verdict}**","",
            "2027_PLUS=CLOSED"
        ]
    else:
        cname=str(winner["candidate"])

        # 2025 confirmation.
        t25,p25,h25,x25=prepared_trades(x5,CONFIRM_END,[2025])
        r25=simulate_candidate(t25,x25,cname)
        m25=metrics(r25,cname)
        half25=halfyear(r25,cname)
        g25=confirmation_gates(m25,half25)
        pass25=all(g25.values())

        r25.to_csv(ROOT/f"{PFX}_Confirmation2025Trades.csv",index=False)
        pd.DataFrame([{**m25,**{f"gate_{k}":v for k,v in g25.items()}}]).to_csv(
            ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False
        )
        half25.to_csv(ROOT/f"{PFX}_Confirmation2025HalfYear.csv",index=False)

        lines=[
            "# SOL Adaptive TP V1 — Result","",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Frozen TP construction winner: **{cname}**",
            "- Detector, entry router, and RECLAIM_EXTREME SL unchanged.",
            "- Gross R only; fees/slippage remain for final ready-to-trade validation.",
            "- 2026 is a secondary monitor, not an untouched TP holdout.",""
        ]
        lines+=render("Construction 2020-2024",winner)
        lines+=render("Frozen 2025 confirmation",m25)
        lines+=["## 2025 half-year","",
                "| Half | N | Mean R | Cum R | PF |",
                "|---|---:|---:|---:|---:|"]
        for _,r in half25.iterrows():
            pfv="inf" if np.isinf(r.pf_r) else f"{r.pf_r:.3f}"
            lines.append(f"| {r['half']} | {int(r.n)} | {r.mean_r:.3f} | {r.cum_r:.3f} | {pfv} |")

        lines+=["","## 2025 gate audit",""]
        for k,v in g25.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        if not pass25:
            verdict="ADAPTIVE_TP_NOT_CONFIRMED_2025"
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Trades.csv",index=False)
            pd.DataFrame().to_csv(ROOT/f"{PFX}_Monitor2026Metrics.csv",index=False)
            summary=pd.DataFrame([{
                "coverage":coverage,
                "winner":cname,
                "construction_mean_r":winner["mean_r"],
                "construction_pf":winner["pf_r"],
                "confirmation_2025_mean_r":m25["mean_r"],
                "confirmation_2025_pf":m25["pf_r"],
                "confirmation_2025_passed":False,
                "monitor_2026_opened":False,
                "verdict":verdict
            }])
            lines+=["",f"**VERDICT: {verdict}**","",
                    "- 2026 monitor was not used because TP failed frozen 2025 confirmation.","",
                    "2027_PLUS=CLOSED"]
        else:
            latest=(x5.index.max()+BAR5).floor("h")
            if latest<=CONFIRM_END:
                latest=CONFIRM_END

            t26,p26,h26,x26=prepared_trades(x5,latest,[2026])
            r26=simulate_candidate(t26,x26,cname)
            m26=metrics(r26,cname) if len(r26) else {
                "candidate":cname,"trades_n":0,"tp_n":0,"tp_rate":np.nan,
                "sl_n":0,"sl_rate":np.nan,"time_exit_n":0,"time_exit_rate":np.nan,
                "win_rate":np.nan,"mean_r":np.nan,"median_r":np.nan,"pf_r":np.nan,
                "cum_r":0.0,"max_dd_r":np.nan,"max_loss_streak":0,
                "median_time_to_exit_min":np.nan,"positive_event_tp_rate":np.nan,
                "negative_event_tp_rate":np.nan,
                "buy_side_n":0,"buy_side_mean_r":np.nan,"buy_side_pf_r":np.nan,
                "sell_side_n":0,"sell_side_mean_r":np.nan,"sell_side_pf_r":np.nan,
                "score3_n":0,"score3_mean_r":np.nan,"score3_pf_r":np.nan,
                "score4_n":0,"score4_mean_r":np.nan,"score4_pf_r":np.nan,
            }
            sample26,quality26=monitor_gates(m26)

            if not all(sample26.values()):
                verdict="ADAPTIVE_TP_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT"
            elif all(quality26.values()):
                verdict="ADAPTIVE_TP_CANDIDATE_REPLICATED_NOT_INDEPENDENT"
            else:
                verdict="ADAPTIVE_TP_2026_MONITOR_DID_NOT_REPLICATE"

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
                "winner":cname,
                "construction_mean_r":winner["mean_r"],
                "construction_pf":winner["pf_r"],
                "confirmation_2025_mean_r":m25["mean_r"],
                "confirmation_2025_pf":m25["pf_r"],
                "confirmation_2025_passed":True,
                "monitor_2026_opened":True,
                "monitor_2026_data_end":latest,
                "monitor_2026_mean_r":m26["mean_r"],
                "monitor_2026_pf":m26["pf_r"],
                "verdict":verdict
            }])

            lines+=["","## 2025 verdict","","**PASS — frozen TP candidate confirmed historically.**",""]
            lines+=render("2026 YTD secondary replication monitor",m26)
            lines+=["## 2026 monitor sample audit",""]
            for k,v in sample26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["","## 2026 monitor quality audit",""]
            for k,v in quality26.items():
                lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
            lines+=["",f"**VERDICT: {verdict}**","",
                    "Passing 2026 is replication only, not independent validation. Final ready-to-trade validation must freeze costs/slippage and the entire stack.","",
                    "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
