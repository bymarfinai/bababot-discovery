#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import time
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_EXECUTION_FEASIBILITY_AUDIT_V1"

TRADES_PATH=ROOT/"SOL_FINAL_TRADABLE_UNIVERSE_AUDIT_V1_Trades.csv"
OBS_END=pd.Timestamp("2026-09-21 00:00:00",tz="UTC")

MAKER_BPS=2.0
TAKER_BPS=5.0
BNB_DISC=0.90
SLIPPAGE_GRID=(0.0,0.5,1.0,2.0,3.0,5.0)
CURRENT_HALF_SPREAD_BPS=0.44748735848171584

FUNDING_URL="https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOL="SOLUSDT"


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


def load_trades():
    if not TRADES_PATH.exists():
        raise FileNotFoundError(TRADES_PATH)
    x=pd.read_csv(TRADES_PATH)
    x["entry_time"]=pd.to_datetime(x.entry_time,utc=True)
    x["exit_time"]=pd.to_datetime(x.exit_time,utc=True)
    x=x.sort_values(["entry_time","candidate_id"]).reset_index(drop=True)

    if len(x)!=302:
        raise RuntimeError(f"expected exact frozen 302 trades, got {len(x)}")

    x["position_direction"]=np.where(x.side.astype(str).eq("SELL_SIDE"),"LONG","SHORT")
    x["entry_liquidity"]=np.where(
        pd.to_numeric(x.anatomy_score,errors="coerce").eq(4),
        "MAKER",
        "TAKER"
    )
    x["exit_liquidity"]="TAKER"
    x["taker_legs"]=np.where(x.entry_liquidity.eq("TAKER"),2,1)
    x["maker_legs"]=np.where(x.entry_liquidity.eq("MAKER"),1,0)
    return x


def fetch_funding(start:pd.Timestamp,end:pd.Timestamp)->pd.DataFrame:
    start_ms=int(start.timestamp()*1000)
    end_ms=int(end.timestamp()*1000)
    rows=[]
    cur=start_ms
    sess=requests.Session()

    for _ in range(100):
        last=None
        data=None
        for attempt in range(5):
            try:
                r=sess.get(
                    FUNDING_URL,
                    params={"symbol":SYMBOL,"startTime":cur,"endTime":end_ms,"limit":1000},
                    timeout=30,
                )
                r.raise_for_status()
                data=r.json()
                break
            except Exception as e:
                last=e
                time.sleep(1.5*(attempt+1))
        if data is None:
            raise RuntimeError(f"funding fetch failed after retries: {last}")
        if not data:
            break
        rows.extend(data)

        mx=max(int(z["fundingTime"]) for z in data)
        nxt=mx+1
        if nxt<=cur:
            raise RuntimeError("funding pagination did not advance")
        cur=nxt
        if mx>=end_ms or len(data)<1000:
            break

    if not rows:
        raise RuntimeError("no funding rows returned")

    f=pd.DataFrame(rows)
    f["funding_time"]=pd.to_datetime(pd.to_numeric(f.fundingTime,errors="coerce"),unit="ms",utc=True)
    f["funding_rate"]=pd.to_numeric(f.fundingRate,errors="coerce")
    if "markPrice" in f.columns:
        f["mark_price"]=pd.to_numeric(f.markPrice,errors="coerce")
    else:
        f["mark_price"]=np.nan
    f=f[(f.funding_time>=start)&(f.funding_time<=end)].copy()
    return f[["funding_time","funding_rate","mark_price"]].drop_duplicates("funding_time").sort_values("funding_time").reset_index(drop=True)


def attach_funding(trades:pd.DataFrame,funding:pd.DataFrame)->pd.DataFrame:
    out=[]
    ft=funding.funding_time.to_numpy()
    fr=funding.funding_rate.to_numpy(dtype=float)
    mp=funding.mark_price.to_numpy(dtype=float)

    for _,r in trades.iterrows():
        et=np.datetime64(pd.Timestamp(r.entry_time).to_datetime64())
        xt=np.datetime64(pd.Timestamp(r.exit_time).to_datetime64())
        mask=(ft>et)&(ft<=xt)

        sign=1.0 if r.position_direction=="LONG" else -1.0
        prices=np.where(np.isfinite(mp[mask]),mp[mask],float(r.entry_price))
        rates=fr[mask]
        funding_cost_price=float(np.sum(sign*prices*rates)) if mask.any() else 0.0

        z=r.to_dict()
        z["funding_event_n"]=int(mask.sum())
        z["funding_cost_price"]=funding_cost_price
        z["funding_r"]=funding_cost_price/float(r.initial_risk_price)
        out.append(z)

    return pd.DataFrame(out)


def execution_rows(trades:pd.DataFrame,slip_bps:float,maker_bps:float,taker_bps:float,include_funding:bool=True)->pd.DataFrame:
    out=[]
    slip=slip_bps/10000.0

    for _,r in trades.iterrows():
        entry=float(r.entry_price)
        exitp=float(r.exit_price)
        risk=float(r.initial_risk_price)
        if risk<=0:
            continue

        is_long=r.position_direction=="LONG"
        entry_is_taker=r.entry_liquidity=="TAKER"

        if entry_is_taker:
            entry_exec=entry*(1+slip) if is_long else entry*(1-slip)
            entry_fee_bps=taker_bps
        else:
            entry_exec=entry
            entry_fee_bps=maker_bps

        exit_exec=exitp*(1-slip) if is_long else exitp*(1+slip)
        exit_fee_bps=taker_bps

        price_pnl=(exit_exec-entry_exec) if is_long else (entry_exec-exit_exec)
        price_r=price_pnl/risk

        commission_price=entry_exec*(entry_fee_bps/10000.0)+exit_exec*(exit_fee_bps/10000.0)
        commission_r=commission_price/risk

        funding_r=float(r.funding_r) if include_funding else 0.0
        net_r=price_r-commission_r-funding_r

        z=r.to_dict()
        z.update({
            "slippage_bps_per_taker_leg":float(slip_bps),
            "maker_fee_bps":float(maker_bps),
            "taker_fee_bps":float(taker_bps),
            "entry_exec_price":entry_exec,
            "exit_exec_price":exit_exec,
            "price_r_after_slippage":price_r,
            "commission_r":commission_r,
            "funding_r_applied":funding_r,
            "total_cost_r":float(r.realized_r)-net_r,
            "net_r":net_r,
        })
        out.append(z)
    return pd.DataFrame(out)


def subset_metrics(g:pd.DataFrame,col="net_r"):
    if len(g)==0:
        return {
            "n":0,"mean_r":np.nan,"median_r":np.nan,"pf_r":np.nan,"cum_r":0.0,
            "win_rate":np.nan,"max_dd_r":np.nan,"max_loss_streak":0,
            "median_cost_r":np.nan
        }
    x=pd.to_numeric(g[col],errors="coerce")
    return {
        "n":len(g),
        "mean_r":float(x.mean()),
        "median_r":float(x.median()),
        "pf_r":float(pf(x)),
        "cum_r":float(x.sum()),
        "win_rate":float((x>0).mean()),
        "max_dd_r":float(max_dd(x)),
        "max_loss_streak":int(max_loss_streak(x)),
        "median_cost_r":float(pd.to_numeric(g.total_cost_r,errors="coerce").median()) if "total_cost_r" in g else np.nan,
    }


def components(df):
    return {
        "ALL":df,
        "BUY_SIDE":df[df.side=="BUY_SIDE"],
        "SELL_SIDE":df[df.side=="SELL_SIDE"],
        "SCORE3_ALL":df[pd.to_numeric(df.anatomy_score,errors="coerce")==3],
        "SCORE3_BUY_SIDE_SHORT":df[(pd.to_numeric(df.anatomy_score,errors="coerce")==3)&(df.side=="BUY_SIDE")],
        "SCORE3_SELL_SIDE_LONG":df[(pd.to_numeric(df.anatomy_score,errors="coerce")==3)&(df.side=="SELL_SIDE")],
        "SCORE4_SELL_SIDE_LONG":df[(pd.to_numeric(df.anatomy_score,errors="coerce")==4)&(df.side=="SELL_SIDE")],
    }


def scenario_table(trades):
    rows=[]
    for s in SLIPPAGE_GRID:
        ex=execution_rows(trades,s,MAKER_BPS,TAKER_BPS,include_funding=True)
        for name,g in components(ex).items():
            rows.append({
                "scenario":"REGULAR_FEE_PLUS_FUNDING",
                "slippage_bps_per_taker_leg":s,
                "component":name,
                **subset_metrics(g),
            })

    # Fee only, explicit no-funding reference.
    ex_fee=execution_rows(trades,0.0,MAKER_BPS,TAKER_BPS,include_funding=False)
    for name,g in components(ex_fee).items():
        rows.append({
            "scenario":"REGULAR_FEE_ONLY_NO_FUNDING",
            "slippage_bps_per_taker_leg":0.0,
            "component":name,
            **subset_metrics(g),
        })

    # BNB discounted fee-only and fee+funding references.
    ex_bnb=execution_rows(trades,0.0,MAKER_BPS*BNB_DISC,TAKER_BPS*BNB_DISC,include_funding=False)
    for name,g in components(ex_bnb).items():
        rows.append({
            "scenario":"BNB_DISCOUNT_FEE_ONLY_NO_FUNDING",
            "slippage_bps_per_taker_leg":0.0,
            "component":name,
            **subset_metrics(g),
        })

    ex_bnb_f=execution_rows(trades,0.0,MAKER_BPS*BNB_DISC,TAKER_BPS*BNB_DISC,include_funding=True)
    for name,g in components(ex_bnb_f).items():
        rows.append({
            "scenario":"BNB_DISCOUNT_FEE_PLUS_FUNDING",
            "slippage_bps_per_taker_leg":0.0,
            "component":name,
            **subset_metrics(g),
        })

    return pd.DataFrame(rows)


def component_frame(trades,name):
    return components(trades)[name].copy()


def objective_at_slip(trades,name,slip,kind):
    ex=execution_rows(component_frame(trades,name),slip,MAKER_BPS,TAKER_BPS,include_funding=True)
    m=subset_metrics(ex)
    return m["mean_r"] if kind=="mean" else m["pf_r"]


def solve_budget(trades,name,kind,target,lo=0.0,hi=50.0):
    flo=objective_at_slip(trades,name,lo,kind)
    fhi=objective_at_slip(trades,name,hi,kind)

    if not np.isfinite(flo):
        return np.nan
    if kind=="mean":
        if flo<=target:
            return 0.0
        if np.isfinite(fhi) and fhi>target:
            return hi
        for _ in range(60):
            mid=(lo+hi)/2
            v=objective_at_slip(trades,name,mid,kind)
            if v>target:
                lo=mid
            else:
                hi=mid
        return (lo+hi)/2

    # PF target.
    if flo<target:
        return 0.0
    if np.isfinite(fhi) and fhi>=target:
        return hi
    for _ in range(60):
        mid=(lo+hi)/2
        v=objective_at_slip(trades,name,mid,kind)
        if np.isfinite(v) and v>=target:
            lo=mid
        else:
            hi=mid
    return (lo+hi)/2


def budgets(trades):
    rows=[]
    for name in components(trades).keys():
        rows.append({
            "component":name,
            "breakeven_slippage_bps_per_taker_leg_mean0":solve_budget(trades,name,"mean",0.0),
            "max_slippage_bps_per_taker_leg_pf_ge_1_10":solve_budget(trades,name,"pf",1.10),
        })
    return pd.DataFrame(rows)


def funding_summary(trades):
    rows=[]
    for name,g in components(trades).items():
        rows.append({
            "component":name,
            "n":len(g),
            "trades_with_funding_n":int((g.funding_event_n>0).sum()),
            "funding_event_n":int(g.funding_event_n.sum()),
            "mean_funding_r":float(g.funding_r.mean()),
            "median_funding_r":float(g.funding_r.median()),
            "cum_funding_r":float(g.funding_r.sum()),
        })
    return pd.DataFrame(rows)


def maker_taker_summary(trades):
    rows=[]
    for name,g in components(trades).items():
        rows.append({
            "component":name,
            "n":len(g),
            "maker_entry_n":int((g.entry_liquidity=="MAKER").sum()),
            "taker_entry_n":int((g.entry_liquidity=="TAKER").sum()),
            "taker_exit_n":len(g),
            "maker_legs":int(g.maker_legs.sum()),
            "taker_legs":int(g.taker_legs.sum()),
        })
    return pd.DataFrame(rows)


def gate_audit(trades,scenarios,budget_df):
    primary=scenarios[
        (scenarios.scenario=="REGULAR_FEE_PLUS_FUNDING")
        &(scenarios.slippage_bps_per_taker_leg==0.5)
    ].set_index("component")
    b=budget_df.set_index("component")

    gates={
        "all_mean_net_r_gt_0":bool(primary.loc["ALL","mean_r"]>0),
        "all_pf_ge_1_10":bool(primary.loc["ALL","pf_r"]>=1.10),
        "all_cum_net_r_gt_0":bool(primary.loc["ALL","cum_r"]>0),
        "score3_mean_net_r_gt_0":bool(primary.loc["SCORE3_ALL","mean_r"]>0),
        "score3_pf_ge_1_05":bool(primary.loc["SCORE3_ALL","pf_r"]>=1.05),
        "score4_long_mean_net_r_gt_0":bool(primary.loc["SCORE4_SELL_SIDE_LONG","mean_r"]>0),
        "score4_long_pf_ge_1_20":bool(primary.loc["SCORE4_SELL_SIDE_LONG","pf_r"]>=1.20),
        "buy_side_mean_net_r_gt_0":bool(primary.loc["BUY_SIDE","mean_r"]>0),
        "sell_side_mean_net_r_gt_0":bool(primary.loc["SELL_SIDE","mean_r"]>0),
        "all_breakeven_slippage_ge_1bps_per_taker_leg":bool(
            b.loc["ALL","breakeven_slippage_bps_per_taker_leg_mean0"]>=1.0
        ),
        "current_half_spread_below_breakeven_budget":bool(
            CURRENT_HALF_SPREAD_BPS < b.loc["ALL","breakeven_slippage_bps_per_taker_leg_mean0"]
        ),
    }
    return gates,primary


def fmt(v,d=3):
    if v is None or not np.isfinite(v):
        return "inf" if v is not None and np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"


def main():
    trades=load_trades()
    start=trades.entry_time.min().floor("D")-pd.Timedelta(days=1)
    funding=fetch_funding(start,OBS_END)
    trades=attach_funding(trades,funding)

    scenarios=scenario_table(trades)
    budget_df=budgets(trades)
    fund=funding_summary(trades)
    mt=maker_taker_summary(trades)

    gates,primary=gate_audit(trades,scenarios,budget_df)
    passed=all(gates.values())
    verdict=(
        "SOL_EXECUTION_FEASIBLE_UNDER_BASELINE_BINANCE_ASSUMPTIONS"
        if passed else
        "SOL_EXECUTION_NOT_FEASIBLE_UNDER_BASELINE_BINANCE_ASSUMPTIONS"
    )

    # Persist scenario-specific primary trade rows.
    primary_trades=execution_rows(trades,0.5,MAKER_BPS,TAKER_BPS,include_funding=True)

    funding.to_csv(ROOT/f"{PFX}_FundingHistory.csv",index=False)
    trades.to_csv(ROOT/f"{PFX}_TradesWithFunding.csv",index=False)
    primary_trades.to_csv(ROOT/f"{PFX}_PrimaryScenarioTrades.csv",index=False)
    scenarios.to_csv(ROOT/f"{PFX}_ScenarioMetrics.csv",index=False)
    budget_df.to_csv(ROOT/f"{PFX}_BreakEvenBudgets.csv",index=False)
    fund.to_csv(ROOT/f"{PFX}_FundingSummary.csv",index=False)
    mt.to_csv(ROOT/f"{PFX}_MakerTakerMix.csv",index=False)
    pd.DataFrame([{"gate":k,"pass":v} for k,v in gates.items()]).to_csv(ROOT/f"{PFX}_GateAudit.csv",index=False)

    prim=primary
    allp=prim.loc["ALL"]
    feeonly=scenarios[
        (scenarios.scenario=="REGULAR_FEE_ONLY_NO_FUNDING")
        &(scenarios.component=="ALL")
    ].iloc[0]
    bnbfee=scenarios[
        (scenarios.scenario=="BNB_DISCOUNT_FEE_ONLY_NO_FUNDING")
        &(scenarios.component=="ALL")
    ].iloc[0]
    reg0=scenarios[
        (scenarios.scenario=="REGULAR_FEE_PLUS_FUNDING")
        &(scenarios.slippage_bps_per_taker_leg==0.0)
        &(scenarios.component=="ALL")
    ].iloc[0]
    b=budget_df.set_index("component")
    fs=fund.set_index("component")
    mts=mt.set_index("component")

    summary=pd.DataFrame([{
        "trade_n":len(trades),
        "maker_entry_n":int(mts.loc["ALL","maker_entry_n"]),
        "taker_entry_n":int(mts.loc["ALL","taker_entry_n"]),
        "taker_exit_n":int(mts.loc["ALL","taker_exit_n"]),
        "regular_fee_only_mean_r":float(feeonly.mean_r),
        "bnb_discount_fee_only_mean_r":float(bnbfee.mean_r),
        "regular_fee_plus_funding_mean_r":float(reg0.mean_r),
        "primary_slippage_bps_per_taker_leg":0.5,
        "primary_mean_net_r":float(allp.mean_r),
        "primary_pf":float(allp.pf_r),
        "primary_cum_r":float(allp.cum_r),
        "funding_trades_n":int(fs.loc["ALL","trades_with_funding_n"]),
        "cum_funding_r":float(fs.loc["ALL","cum_funding_r"]),
        "breakeven_slippage_bps_per_taker_leg":float(b.loc["ALL","breakeven_slippage_bps_per_taker_leg_mean0"]),
        "pf110_slippage_budget_bps_per_taker_leg":float(b.loc["ALL","max_slippage_bps_per_taker_leg_pf_ge_1_10"]),
        "current_half_spread_bps":CURRENT_HALF_SPREAD_BPS,
        "gates_passed":sum(bool(v) for v in gates.values()),
        "gates_total":len(gates),
        "verdict":verdict,
    }])
    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    lines=[
        "# SOL Execution Feasibility Audit V1 — Result","",
        "- Frozen 302-trade final universe; no strategy rule changed.",
        f"- Binance regular-user commission model: maker **{MAKER_BPS:.1f} bps**, taker **{TAKER_BPS:.1f} bps** per leg.",
        "- Score 3: taker entry + taker exit.",
        "- Score-4 LONG: maker GAP25 entry + taker exit.",
        f"- Current SOLUSDT half-spread calibration: **{CURRENT_HALF_SPREAD_BPS:.3f} bps**.",
        "- Historical SOLUSDT funding is applied trade-by-trade.","",
        "## Actual maker/taker mix","",
        f"- Maker entries: **{int(mts.loc['ALL','maker_entry_n'])}**",
        f"- Taker entries: **{int(mts.loc['ALL','taker_entry_n'])}**",
        f"- Taker exits: **{int(mts.loc['ALL','taker_exit_n'])}**",
        f"- Total maker legs: **{int(mts.loc['ALL','maker_legs'])}**",
        f"- Total taker legs: **{int(mts.loc['ALL','taker_legs'])}**","",
        "## Cost decomposition — ALL","",
        f"- Gross mean R before execution costs: **{fmt(float(trades.realized_r.mean()))}R**",
        f"- Regular fee only, no funding/slippage: **{fmt(float(feeonly.mean_r))}R**, PF **{fmt(float(feeonly.pf_r))}**",
        f"- BNB-discount fee only: **{fmt(float(bnbfee.mean_r))}R**, PF **{fmt(float(bnbfee.pf_r))}**",
        f"- Regular fees + historical funding, zero slippage: **{fmt(float(reg0.mean_r))}R**, PF **{fmt(float(reg0.pf_r))}**",
        f"- Funding crossed by **{int(fs.loc['ALL','trades_with_funding_n'])}/{len(trades)}** trades; cumulative funding cost/credit: **{fmt(float(fs.loc['ALL','cum_funding_r']))}R**.","",
        "## Slippage stress — regular fees + funding","",
        "| Slippage per taker leg | ALL mean R | PF | Cum R | Score3 mean | Score4 LONG mean |",
        "|---:|---:|---:|---:|---:|---:|",
    ]

    reg=scenarios[scenarios.scenario=="REGULAR_FEE_PLUS_FUNDING"]
    for s in SLIPPAGE_GRID:
        q=reg[reg.slippage_bps_per_taker_leg==s].set_index("component")
        lines.append(
            f"| {s:.1f} bps | {fmt(q.loc['ALL','mean_r'])} | {fmt(q.loc['ALL','pf_r'])} | "
            f"{fmt(q.loc['ALL','cum_r'])} | {fmt(q.loc['SCORE3_ALL','mean_r'])} | "
            f"{fmt(q.loc['SCORE4_SELL_SIDE_LONG','mean_r'])} |"
        )

    lines+=["","## Primary scenario — regular fees + 0.5 bps/taker-leg slippage + funding","",
            "| Component | N | Mean net R | PF | Cum R | Win rate | Max DD |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("ALL","BUY_SIDE","SELL_SIDE","SCORE3_ALL","SCORE3_BUY_SIDE_SHORT","SCORE3_SELL_SIDE_LONG","SCORE4_SELL_SIDE_LONG"):
        r=prim.loc[name]
        lines.append(
            f"| {name} | {int(r.n)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {fmt(r.cum_r)} | {pct(r.win_rate)} | {fmt(r.max_dd_r)} |"
        )

    lines+=["","## Break-even execution budget","",
            "| Component | Mean=0 extra slippage / taker leg | Max slippage for PF>=1.10 |",
            "|---|---:|---:|"]
    for _,r in budget_df.iterrows():
        lines.append(
            f"| {r.component} | {fmt(r.breakeven_slippage_bps_per_taker_leg_mean0)} bps | "
            f"{fmt(r.max_slippage_bps_per_taker_leg_pf_ge_1_10)} bps |"
        )

    lines+=["","## Frozen gate audit",""]
    for k,v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines+=["",f"**VERDICT: {verdict}**","",
            f"Passed **{sum(bool(v) for v in gates.values())}/{len(gates)}** frozen execution-feasibility gates.","",
            "This is an execution-cost feasibility audit, not proof of live fills."]

    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
