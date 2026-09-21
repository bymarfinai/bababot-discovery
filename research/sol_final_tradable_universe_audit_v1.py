#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_adaptive_risk_manager_v1 as rm
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_FINAL_TRADABLE_UNIVERSE_AUDIT_V1"
OBS_END=pd.Timestamp("2026-09-21 00:00:00",tz="UTC")
YEARS=(2020,2021,2022,2023,2024,2025,2026)
ROLL_N=20
BOOT_N=10_000
BOOT_SEED=42
FRICTION_BPS=(10,20,30)


def pf(x):
    s=pd.Series(x,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(s[s>0].sum())
    neg=float(-s[s<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def max_dd(x):
    s=pd.Series(x,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    if s.empty:
        return np.nan
    eq=s.cumsum()
    peak=eq.cummax().clip(lower=0.0)
    return float((peak-eq).max())


def max_loss_streak(x):
    best=cur=0
    for v in pd.Series(x,dtype=float).replace([np.inf,-np.inf],np.nan).dropna():
        if v<0:
            cur+=1
            best=max(best,cur)
        else:
            cur=0
    return best


def metrics(g):
    if g is None or len(g)==0:
        return {
            "n":0,"event_rate":np.nan,"win_rate":np.nan,"mean_r":np.nan,
            "median_r":np.nan,"pf_r":np.nan,"cum_r":0.0,"max_dd_r":np.nan,
            "max_loss_streak":0,"median_hold_min":np.nan,
            "stop_rate":np.nan,"structural_exit_rate":np.nan
        }
    r=pd.to_numeric(g.realized_r,errors="coerce")
    return {
        "n":len(g),
        "event_rate":float(pd.to_numeric(g.event_label,errors="coerce").mean()),
        "win_rate":float((r>0).mean()),
        "mean_r":float(r.mean()),
        "median_r":float(r.median()),
        "pf_r":float(pf(r)),
        "cum_r":float(r.sum()),
        "max_dd_r":float(max_dd(r)),
        "max_loss_streak":int(max_loss_streak(r)),
        "median_hold_min":float(pd.to_numeric(g.time_to_exit_min,errors="coerce").median()),
        "stop_rate":float((g.exit_type=="STOP").mean()),
        "structural_exit_rate":float((g.exit_type=="TIME_EXIT").mean()),
    }


def build_universe(entries):
    x=entries.copy()
    tradable=(
        (pd.to_numeric(x.anatomy_score,errors="coerce")==3)
        |
        (
            (pd.to_numeric(x.anatomy_score,errors="coerce")==4)
            & x.side.astype(str).eq("SELL_SIDE")
        )
    )
    x=x[tradable].copy().reset_index(drop=True)
    x["universe_component"]=np.where(
        pd.to_numeric(x.anatomy_score,errors="coerce")==3,
        "SCORE3_ALL",
        "SCORE4_SELL_SIDE_LONG"
    )
    return x


def period_tables(trades):
    z=trades.copy()
    ts=pd.to_datetime(z.entry_time,utc=True)
    z["year"]=ts.dt.year.astype(int)
    z["half"]=ts.dt.year.astype(str)+"-"+np.where(ts.dt.month<=6,"H1","H2")

    years=[]
    for y,g in z.groupby("year",sort=True):
        years.append({"year":int(y),**metrics(g)})

    halves=[]
    for h,g in z.groupby("half",sort=True):
        halves.append({"half":h,**metrics(g)})

    return pd.DataFrame(years),pd.DataFrame(halves)


def component_table(trades):
    rows=[]
    for name,g in [
        ("ALL",trades),
        ("BUY_SIDE",trades[trades.side=="BUY_SIDE"]),
        ("SELL_SIDE",trades[trades.side=="SELL_SIDE"]),
        ("SCORE3_ALL",trades[trades.anatomy_score==3]),
        ("SCORE3_BUY_SIDE",trades[(trades.anatomy_score==3)&(trades.side=="BUY_SIDE")]),
        ("SCORE3_SELL_SIDE",trades[(trades.anatomy_score==3)&(trades.side=="SELL_SIDE")]),
        ("SCORE4_SELL_SIDE_LONG",trades[(trades.anatomy_score==4)&(trades.side=="SELL_SIDE")]),
    ]:
        rows.append({"component":name,**metrics(g)})
    return pd.DataFrame(rows)


def leave_one_year_out(trades):
    z=trades.copy()
    z["year"]=pd.to_datetime(z.entry_time,utc=True).dt.year.astype(int)
    rows=[]
    for y in YEARS:
        g=z[z.year!=y].copy()
        m=metrics(g)
        rows.append({
            "excluded_year":y,
            **m,
            "pass_mean_gt_0":bool(np.isfinite(m["mean_r"]) and m["mean_r"]>0),
            "pass_pf_ge_1_10":bool(np.isfinite(m["pf_r"]) and m["pf_r"]>=1.10),
        })
    return pd.DataFrame(rows)


def bootstrap_summary(trades):
    vals=pd.to_numeric(trades.realized_r,errors="coerce").dropna().to_numpy(dtype=float)
    if len(vals)==0:
        raise RuntimeError("no R values for bootstrap")
    rng=np.random.default_rng(BOOT_SEED)

    means=np.empty(BOOT_N,dtype=float)
    pfs=np.empty(BOOT_N,dtype=float)
    n=len(vals)

    for i in range(BOOT_N):
        s=vals[rng.integers(0,n,size=n)]
        means[i]=float(np.mean(s))
        pfs[i]=float(pf(s))

    finite_pf=pfs[np.isfinite(pfs)]
    row={
        "seed":BOOT_SEED,
        "bootstrap_n":BOOT_N,
        "trade_n":n,
        "prob_mean_gt_0":float(np.mean(means>0)),
        "mean_r_p05":float(np.quantile(means,.05)),
        "mean_r_p50":float(np.quantile(means,.50)),
        "mean_r_p95":float(np.quantile(means,.95)),
        "pf_p05":float(np.quantile(finite_pf,.05)) if len(finite_pf) else np.nan,
        "pf_p50":float(np.quantile(finite_pf,.50)) if len(finite_pf) else np.nan,
        "pf_p95":float(np.quantile(finite_pf,.95)) if len(finite_pf) else np.nan,
    }
    return pd.DataFrame([row])


def rolling_table(trades):
    z=trades.sort_values(["entry_time","candidate_id"]).reset_index(drop=True)
    rows=[]
    if len(z)<ROLL_N:
        return pd.DataFrame()
    for start in range(0,len(z)-ROLL_N+1):
        g=z.iloc[start:start+ROLL_N]
        m=metrics(g)
        rows.append({
            "start_i":start,
            "end_i":start+ROLL_N-1,
            "start_time":g.entry_time.iloc[0],
            "end_time":g.entry_time.iloc[-1],
            "n":ROLL_N,
            "mean_r":m["mean_r"],
            "pf_r":m["pf_r"],
            "cum_r":m["cum_r"],
        })
    return pd.DataFrame(rows)


def friction_table(trades):
    rows=[]
    entry=pd.to_numeric(trades.entry_price,errors="coerce")
    risk=pd.to_numeric(trades.initial_risk_price,errors="coerce")
    gross=pd.to_numeric(trades.realized_r,errors="coerce")

    for bps in FRICTION_BPS:
        friction=(entry*(bps/10000.0))/risk
        net=gross-friction
        rows.append({
            "round_trip_bps":bps,
            "n":int(net.notna().sum()),
            "median_friction_r":float(friction.median()),
            "p75_friction_r":float(friction.quantile(.75)),
            "mean_net_r":float(net.mean()),
            "median_net_r":float(net.median()),
            "pf_net_r":float(pf(net)),
            "cum_net_r":float(net.sum()),
            "max_dd_net_r":float(max_dd(net)),
            "max_loss_streak_net":int(max_loss_streak(net)),
        })
    return pd.DataFrame(rows)


def bool_no_two_consecutive_negative(years):
    y=years.sort_values("year").reset_index(drop=True)
    neg=(pd.to_numeric(y.cum_r,errors="coerce")<0).tolist()
    return not any(neg[i] and neg[i+1] for i in range(len(neg)-1))


def gate_audit(allm,years,components,loyo,boot,rolling,friction):
    comp=components.set_index("component")
    score3=comp.loc["SCORE3_ALL"]
    score4l=comp.loc["SCORE4_SELL_SIDE_LONG"]
    buy=comp.loc["BUY_SIDE"]
    sell=comp.loc["SELL_SIDE"]

    pos_years=int((pd.to_numeric(years.cum_r,errors="coerce")>0).sum())
    rolling_positive_share=float((rolling.mean_r>0).mean()) if len(rolling) else np.nan
    rolling_worst=float(rolling.mean_r.min()) if len(rolling) else np.nan
    b=boot.iloc[0]
    f20=friction[friction.round_trip_bps==20].iloc[0]
    f30=friction[friction.round_trip_bps==30].iloc[0]

    gates={
        "core_n_ge_250":int(allm["n"])>=250,
        "core_mean_r_ge_0_08":bool(np.isfinite(allm["mean_r"]) and allm["mean_r"]>=.08),
        "core_pf_ge_1_20":bool(np.isfinite(allm["pf_r"]) and allm["pf_r"]>=1.20),
        "core_cum_r_gt_0":bool(np.isfinite(allm["cum_r"]) and allm["cum_r"]>0),
        "core_max_dd_le_15r":bool(np.isfinite(allm["max_dd_r"]) and allm["max_dd_r"]<=15),
        "core_max_loss_streak_le_8":int(allm["max_loss_streak"])<=8,
        "core_positive_years_ge_5":pos_years>=5,
        "core_no_two_consecutive_negative_years":bool_no_two_consecutive_negative(years),

        "component_score3_n_ge_200":int(score3["n"])>=200,
        "component_score3_mean_gt_0":bool(np.isfinite(score3["mean_r"]) and score3["mean_r"]>0),
        "component_score3_pf_ge_1_10":bool(np.isfinite(score3["pf_r"]) and score3["pf_r"]>=1.10),
        "component_score4_long_n_ge_20":int(score4l["n"])>=20,
        "component_score4_long_mean_gt_0":bool(np.isfinite(score4l["mean_r"]) and score4l["mean_r"]>0),
        "component_score4_long_pf_ge_1_20":bool(np.isfinite(score4l["pf_r"]) and score4l["pf_r"]>=1.20),
        "component_buy_mean_gt_0":bool(np.isfinite(buy["mean_r"]) and buy["mean_r"]>0),
        "component_sell_mean_gt_0":bool(np.isfinite(sell["mean_r"]) and sell["mean_r"]>0),

        "loyo_all_mean_gt_0":bool(loyo.pass_mean_gt_0.all()),
        "loyo_all_pf_ge_1_10":bool(loyo.pass_pf_ge_1_10.all()),

        "bootstrap_prob_mean_gt_0_ge_99pct":bool(float(b.prob_mean_gt_0)>=.99),
        "bootstrap_p05_mean_gt_0":bool(float(b.mean_r_p05)>0),
        "bootstrap_median_pf_gt_1_20":bool(float(b.pf_p50)>1.20),

        "rolling_positive_mean_share_ge_70pct":bool(np.isfinite(rolling_positive_share) and rolling_positive_share>=.70),
        "rolling_worst_mean_gt_neg_0_35r":bool(np.isfinite(rolling_worst) and rolling_worst>-.35),

        "friction_20bps_mean_gt_0":bool(np.isfinite(f20.mean_net_r) and f20.mean_net_r>0),
        "friction_20bps_pf_ge_1_10":bool(np.isfinite(f20.pf_net_r) and f20.pf_net_r>=1.10),
        "friction_30bps_mean_gt_0":bool(np.isfinite(f30.mean_net_r) and f30.mean_net_r>0),
    }

    extras={
        "positive_years":pos_years,
        "rolling_positive_share":rolling_positive_share,
        "rolling_worst_mean_r":rolling_worst,
    }
    return gates,extras


def fmt(v,d=3):
    if v is None or not np.isfinite(v):
        return "inf" if v is not None and np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"


def main():
    # Freeze raw observation horizon before loading.
    base=v3.wf1.v3.v1.base
    base.END=OBS_END

    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    entries,_,_,x=rm.prepare_period(x5,OBS_END,list(YEARS))
    universe=build_universe(entries)

    results=rm.simulate_policy(universe,x,"STATIC_RECLAIM_EXTREME")
    if results.empty:
        raise RuntimeError("no final-universe trades")

    # Attach universe component and preserve deterministic chronological ordering.
    component_map=universe[["candidate_id","universe_component"]].drop_duplicates("candidate_id")
    results=results.merge(component_map,on="candidate_id",how="left",validate="one_to_one")
    results=results.sort_values(["entry_time","candidate_id"]).reset_index(drop=True)

    allm=metrics(results)
    years,halves=period_tables(results)
    components=component_table(results)
    loyo=leave_one_year_out(results)
    boot=bootstrap_summary(results)
    rolling=rolling_table(results)
    friction=friction_table(results)

    gates,extras=gate_audit(allm,years,components,loyo,boot,rolling,friction)
    passed=all(gates.values())
    verdict="SOL_FINAL_UNIVERSE_RETROSPECTIVELY_ROBUST" if passed else "SOL_FINAL_UNIVERSE_NOT_ROBUST_AS_DEFINED"

    # Persist.
    results.to_csv(ROOT/f"{PFX}_Trades.csv",index=False)
    years.to_csv(ROOT/f"{PFX}_YearMetrics.csv",index=False)
    halves.to_csv(ROOT/f"{PFX}_HalfYearMetrics.csv",index=False)
    components.to_csv(ROOT/f"{PFX}_ComponentMetrics.csv",index=False)
    loyo.to_csv(ROOT/f"{PFX}_LeaveOneYearOut.csv",index=False)
    boot.to_csv(ROOT/f"{PFX}_BootstrapSummary.csv",index=False)
    rolling.to_csv(ROOT/f"{PFX}_Rolling20.csv",index=False)
    friction.to_csv(ROOT/f"{PFX}_FrictionStress.csv",index=False)
    pd.DataFrame([{"gate":k,"pass":v} for k,v in gates.items()]).to_csv(ROOT/f"{PFX}_GateAudit.csv",index=False)

    summary={
        "coverage":coverage,
        "observation_end":OBS_END,
        **{f"all_{k}":v for k,v in allm.items()},
        **extras,
        "bootstrap_prob_mean_gt_0":float(boot.iloc[0].prob_mean_gt_0),
        "bootstrap_p05_mean_r":float(boot.iloc[0].mean_r_p05),
        "bootstrap_median_pf":float(boot.iloc[0].pf_p50),
        "gates_passed":sum(bool(v) for v in gates.values()),
        "gates_total":len(gates),
        "verdict":verdict,
    }
    pd.DataFrame([summary]).to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    c=components.set_index("component")
    lines=[
        "# SOL Final Tradable Universe Audit V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        f"- Observation end: **{OBS_END}**",
        "- Frozen universe: Score 3 both sides + Score 4 SELL_SIDE/LONG only.",
        "- Score 4 BUY_SIDE/SHORT is excluded.",
        "- Entry, SL, and structural-completion exit are unchanged.",
        "- All evidence here is retrospective; no independent validation claim.","",
        "## Full-universe economics","",
        f"- Trades: **{allm['n']}**",
        f"- Structural-event rate: **{pct(allm['event_rate'])}**",
        f"- Gross WR: **{pct(allm['win_rate'])}**",
        f"- Mean / median R: **{fmt(allm['mean_r'])} / {fmt(allm['median_r'])}**",
        f"- PF: **{fmt(allm['pf_r'])}**",
        f"- Cumulative: **{fmt(allm['cum_r'])}R**",
        f"- Max DD: **{fmt(allm['max_dd_r'])}R**",
        f"- Max losing streak: **{allm['max_loss_streak']}**",
        f"- Median holding time: **{fmt(allm['median_hold_min'],1)} min**",
        f"- SL / structural-completion exits: **{pct(allm['stop_rate'])} / {pct(allm['structural_exit_rate'])}**","",
        "## Components","",
        "| Component | N | Event rate | Mean R | PF | Cum R | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("BUY_SIDE","SELL_SIDE","SCORE3_ALL","SCORE3_BUY_SIDE","SCORE3_SELL_SIDE","SCORE4_SELL_SIDE_LONG"):
        r=c.loc[name]
        lines.append(
            f"| {name} | {int(r.n)} | {pct(r.event_rate)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {fmt(r.cum_r)} | {fmt(r.max_dd_r)} |"
        )

    lines+=["","## Yearly robustness","",
            "| Year | N | Mean R | PF | Cum R | Max DD |",
            "|---|---:|---:|---:|---:|---:|"]
    for _,r in years.iterrows():
        lines.append(
            f"| {int(r.year)} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {fmt(r.cum_r)} | {fmt(r.max_dd_r)} |"
        )

    b=boot.iloc[0]
    lines+=["","## Robustness stress","",
            f"- Leave-one-year-out: **{int(loyo.pass_mean_gt_0.sum())}/{len(loyo)} mean-positive**, **{int(loyo.pass_pf_ge_1_10.sum())}/{len(loyo)} PF>=1.10**.",
            f"- Bootstrap P(mean>0): **{pct(float(b.prob_mean_gt_0))}**.",
            f"- Bootstrap mean-R 5th percentile: **{fmt(float(b.mean_r_p05))}R**.",
            f"- Bootstrap median PF: **{fmt(float(b.pf_p50))}**.",
            f"- Rolling-20 positive-mean share: **{pct(extras['rolling_positive_share'])}**.",
            f"- Worst rolling-20 mean: **{fmt(extras['rolling_worst_mean_r'])}R**.","",
            "## Friction stress","",
            "| Total round-trip friction | Mean net R | PF | Cum net R | Max DD |",
            "|---:|---:|---:|---:|---:|"]
    for _,r in friction.iterrows():
        lines.append(
            f"| {int(r.round_trip_bps)} bps | {fmt(r.mean_net_r)} | {fmt(r.pf_net_r)} | {fmt(r.cum_net_r)} | {fmt(r.max_dd_net_r)} |"
        )

    lines+=["","## Frozen gate audit",""]
    for k,v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines+=["",
            f"**VERDICT: {verdict}**","",
            f"Passed **{sum(bool(v) for v in gates.values())}/{len(gates)}** frozen gates.",""]

    if passed:
        lines += [
            "Operational interpretation: the reduced SOL stack is retrospectively robust enough to freeze for forward/paper execution validation.",
            "This is not independent live validation and does not yet justify claiming production trading performance."
        ]
    else:
        lines += [
            "Operational interpretation: the reduced SOL stack did not satisfy the preregistered retrospective robustness standard.",
            "Per stop-rule, do not rescue it with new TP/SL/session/indicator tuning in this audit."
        ]

    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
