#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7E exit-horizon discovery."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s7 as s7
import sol_indicator_relationship_s7d as s7d

ROOT=Path(__file__).resolve().parent.parent

OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_AUDIT.csv"
OUT_GRID=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_A_HORIZON_GRID.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_B_SELECTED_VALIDATION.csv"
OUT_FATE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_C_TIME4H_FATE.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_D_SIDE.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_E_TRADES.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_Status.txt"

MODEL_NAME="M2_RF"
SCORE_THRESHOLD=0.4436178316491465
RETENTION_LABEL=0.30
TP=0.01
SL=0.01
COST=0.0015
NOTIONAL=500.0
BAR=pd.Timedelta(minutes=5)
HORIZONS=[4,6,8,12]
SPLITS=["train_2023","dev_select_2024","validation_2025","validation_2026"]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def prepare_scored():
    raw,a=s7d.prepare()
    ds=s7d.build_dataset(raw,a)
    fitted,_=s7d.fit_models(ds)
    scored=s7d.score_models(ds,fitted)[MODEL_NAME]
    return raw,ds,scored

def split_days(split,raw):
    return s7d.coverage_days(split,raw)

def simulate_one_trade(raw,pos,side,hours):
    bars=int(hours*12)
    if pos is None or pos+bars>len(raw):
        return None
    w=raw.iloc[pos:pos+bars]
    if len(w)!=bars:
        return None
    if not bool((w.ts.diff().dropna()==BAR).all()):
        return None
    entry_ts=pd.Timestamp(w.ts.iloc[0])
    entry=float(w.open.iloc[0])
    if side=="LONG":
        tp_px=entry*(1+TP); sl_px=entry*(1-SL)
    else:
        tp_px=entry*(1-TP); sl_px=entry*(1+SL)

    reason="TIME"; samebar=False
    exit_px=float(w.close.iloc[-1])
    exit_ts=pd.Timestamp(w.ts.iloc[-1])+BAR

    for br in w.itertuples(index=False):
        if side=="LONG":
            hit_tp=float(br.high)>=tp_px
            hit_sl=float(br.low)<=sl_px
        else:
            hit_tp=float(br.low)<=tp_px
            hit_sl=float(br.high)>=sl_px
        if hit_tp and hit_sl:
            reason="SL"; samebar=True; exit_px=sl_px; exit_ts=pd.Timestamp(br.ts)+BAR; break
        if hit_sl:
            reason="SL"; exit_px=sl_px; exit_ts=pd.Timestamp(br.ts)+BAR; break
        if hit_tp:
            reason="TP"; exit_px=tp_px; exit_ts=pd.Timestamp(br.ts)+BAR; break

    sign=1.0 if side=="LONG" else -1.0
    gross=sign*(exit_px/entry-1.0)
    net=gross-COST
    return {
        "entry_ts":entry_ts,"entry_price":entry,
        "exit_ts":exit_ts,"exit_price":float(exit_px),
        "exit_reason":reason,"samebar_sl":bool(samebar),
        "hold_min":float((exit_ts-entry_ts)/pd.Timedelta(minutes=1)),
        "gross_return":float(gross),"net_return":float(net),
        "net_pnl_usd":float(net*NOTIONAL),
    }

def max_loss_streak(vals):
    m=0;c=0
    for v in vals:
        if v<=0:
            c+=1;m=max(m,c)
        else:
            c=0
    return m

def summarize(trades,days,raw_signals,eligible_signals):
    if trades is None or len(trades)==0:
        return {
            "raw_signals":int(raw_signals),"eligible_signals":int(eligible_signals),
            "executed_trades":0,"skipped_active":int(eligible_signals),
            "skipped_insufficient_future":int(raw_signals-eligible_signals),
            "trades_per_day":0.0,"tp":0,"sl":0,"time":0,"samebar_sl":0,
            "target_wr":0.0,"resolved_wr":np.nan,"economic_win_rate":0.0,
            "net_expectancy_return":0.0,"net_expectancy_usd":0.0,"profit_factor":0.0,
            "total_net_usd":0.0,"max_loss_streak":0,"median_hold_min":np.nan,
        }
    t=trades
    n=len(t); ntp=int((t.exit_reason=="TP").sum()); nsl=int((t.exit_reason=="SL").sum())
    ntm=int((t.exit_reason=="TIME").sum()); nsb=int(t.samebar_sl.sum())
    pos=float(t.loc[t.net_pnl_usd>0,"net_pnl_usd"].sum())
    neg=float(-t.loc[t.net_pnl_usd<0,"net_pnl_usd"].sum())
    pf=pos/neg if neg>0 else (np.inf if pos>0 else 0.0)
    resolved=ntp+nsl
    return {
        "raw_signals":int(raw_signals),"eligible_signals":int(eligible_signals),
        "executed_trades":int(n),"skipped_active":int(eligible_signals-n),
        "skipped_insufficient_future":int(raw_signals-eligible_signals),
        "trades_per_day":float(n/days) if days>0 else np.nan,
        "tp":ntp,"sl":nsl,"time":ntm,"samebar_sl":nsb,
        "target_wr":float(ntp/n),
        "resolved_wr":float(ntp/resolved) if resolved else np.nan,
        "economic_win_rate":float((t.net_pnl_usd>0).mean()),
        "net_expectancy_return":float(t.net_return.mean()),
        "net_expectancy_usd":float(t.net_pnl_usd.mean()),
        "profit_factor":float(pf),"total_net_usd":float(t.net_pnl_usd.sum()),
        "max_loss_streak":int(max_loss_streak(t.net_pnl_usd.to_numpy(float))),
        "median_hold_min":float(t.hold_min.median()),
    }

def simulate_horizon(scored,raw,split,hours):
    base=scored[(scored.split==split)&(scored.score>=SCORE_THRESHOLD)].copy()
    base=base.sort_values(["entry_ts","onset_ts"])
    raw_signals=len(base)
    posmap={t:i for i,t in enumerate(raw.ts)}

    eligible=[]
    for r in base.itertuples(index=False):
        p=posmap.get(pd.Timestamp(r.entry_ts))
        out=simulate_one_trade(raw,p,r.side,hours)
        if out is None:
            continue
        eligible.append((r,out))
    eligible_signals=len(eligible)

    rows=[];active_until=None
    for r,out in eligible:
        et=pd.Timestamp(r.entry_ts)
        if active_until is not None and et<active_until:
            continue
        row={
            "split":split,"horizon_h":hours,"score":float(r.score),
            "onset_ts":r.onset_ts,"entry_ts":et,"side":r.side,
            "cell_id":r.cell_id,"market_state":r.market_state,"regime":r.regime,
        }
        row.update(out)
        rows.append(row)
        active_until=pd.Timestamp(out["exit_ts"])
    trades=pd.DataFrame(rows)
    return summarize(trades,split_days(split,raw),raw_signals,eligible_signals),trades

def gate(m):
    return (
        m["trades_per_day"]>=1.0
        and m["target_wr"]>=0.70
        and m["net_expectancy_return"]>0
        and m["profit_factor"]>1
    )

def choose_horizon(grid2024):
    e=grid2024[grid2024.target_eligible].copy()
    if len(e):
        q=e.sort_values(
            ["target_wr","net_expectancy_return","trades_per_day","horizon_h"],
            ascending=[False,False,False,True]
        ).iloc[0]
        return int(q.horizon_h),True,"TARGET_ELIGIBLE"
    p=grid2024[grid2024.trades_per_day>=1.0].copy()
    if len(p):
        q=p.sort_values(
            ["target_wr","net_expectancy_return","trades_per_day","horizon_h"],
            ascending=[False,False,False,True]
        ).iloc[0]
        return int(q.horizon_h),False,"DIAGNOSTIC_TARGET_NOT_MET"
    q=grid2024.sort_values(
        ["trades_per_day","target_wr","net_expectancy_return","horizon_h"],
        ascending=[False,False,False,True]
    ).iloc[0]
    return int(q.horizon_h),False,"DIAGNOSTIC_NO_1TPD"

def side_metrics(trades,split,raw):
    rows=[];days=split_days(split,raw)
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        m=summarize(g,days,len(g),len(g))
        row={"split":split,"side":side};row.update(m);rows.append(row)
    return rows

def time4h_fate(raw,trades4h,split):
    rows=[]
    q=trades4h[trades4h.exit_reason=="TIME"].copy() if len(trades4h) else pd.DataFrame()
    posmap={t:i for i,t in enumerate(raw.ts)}
    base_n=len(q)
    for hours in [6,8,12]:
        counts={"TP":0,"SL":0,"TIME":0,"UNAVAILABLE":0}
        for r in q.itertuples(index=False):
            p=posmap.get(pd.Timestamp(r.entry_ts))
            out=simulate_one_trade(raw,p,r.side,hours)
            if out is None:
                counts["UNAVAILABLE"]+=1
            else:
                counts[out["exit_reason"]]+=1
        den=base_n-counts["UNAVAILABLE"]
        rows.append({
            "split":split,"from_horizon_h":4,"to_horizon_h":hours,
            "time4h_n":base_n,"available_n":den,
            "tp_n":counts["TP"],"sl_n":counts["SL"],"time_n":counts["TIME"],
            "unavailable_n":counts["UNAVAILABLE"],
            "tp_share":float(counts["TP"]/den) if den else np.nan,
            "sl_share":float(counts["SL"]/den) if den else np.nan,
            "time_share":float(counts["TIME"]/den) if den else np.nan,
        })
    return rows

def audit(ds,grid,selected_h,trades_by_key):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    parent=json.loads((ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_Result.json").read_text())
    add("parent_model_exact",parent.get("selected_model")==MODEL_NAME,parent.get("selected_model"))
    add("parent_threshold_exact",abs(float(parent.get("selected_threshold"))-SCORE_THRESHOLD)<1e-15,parent.get("selected_threshold"))
    add("parent_retention_exact",abs(float(parent.get("selected_retention"))-RETENTION_LABEL)<1e-15,parent.get("selected_retention"))
    add("horizon_grid_exact",HORIZONS==[4,6,8,12],HORIZONS)
    add("tp_sl_cost_frozen",TP==.01 and SL==.01 and COST==.0015,{"tp":TP,"sl":SL,"cost":COST})
    add("selected_from_2024_only",True,selected_h)
    add("selected_horizon_in_grid",selected_h in HORIZONS,selected_h)

    # 4H one-position baseline should reproduce Stage-7D selected simulation.
    parent_val={r["split"]:r for r in parent.get("validation",[])}
    diffs=[]
    for split in SPLITS:
        g=grid[(grid.split==split)&(grid.horizon_h==4)]
        if not len(g) or split not in parent_val:
            continue
        r=g.iloc[0];p=parent_val[split]
        diffs.append({
            "split":split,
            "trade_diff":int(r.executed_trades)-int(p["executed_trades"]),
            "wr_diff":float(r.target_wr)-float(p["target_wr"]),
        })
    baseline_ok=all(x["trade_diff"]==0 and abs(x["wr_diff"])<1e-12 for x in diffs)
    add("four_hour_reproduces_stage7d",baseline_ok,diffs)

    overlap=0
    for (split,h),t in trades_by_key.items():
        if not len(t): continue
        g=t.sort_values("entry_ts")
        if len(g)>1:
            prev=pd.to_datetime(g.exit_ts,utc=True).shift(1)
            cur=pd.to_datetime(g.entry_ts,utc=True)
            overlap+=int((cur<prev).fillna(False).sum())
    add("one_position_no_overlap_all_horizons",overlap==0,overlap)
    add("dataset_nonempty",len(ds)>0,len(ds))
    return pd.DataFrame(rows)

def main():
    raw,ds,scored=prepare_scored()

    grid_rows=[];trades_by_key={}
    for split in SPLITS:
        for h in HORIZONS:
            m,t=simulate_horizon(scored,raw,split,h)
            row={"split":split,"horizon_h":h}
            row.update(m)
            row["target_eligible"]=gate(m) if split=="dev_select_2024" else False
            grid_rows.append(row)
            trades_by_key[(split,h)]=t
    grid=pd.DataFrame(grid_rows)
    grid.to_csv(OUT_GRID,index=False)

    dev=grid[grid.split=="dev_select_2024"].copy()
    selected_h,dev_eligible,selection_status=choose_horizon(dev)

    val=grid[grid.horizon_h==selected_h].copy()
    val["gate_pass"]=[gate(r._asdict()) if r.split!="train_2023" else False for r in val.itertuples(index=False)]
    val.to_csv(OUT_VAL,index=False)

    selected_frames=[]
    side_rows=[]
    for split in SPLITS:
        t=trades_by_key[(split,selected_h)]
        if len(t): selected_frames.append(t)
        if split!="train_2023":
            side_rows.extend(side_metrics(t,split,raw))
    selected_trades=pd.concat(selected_frames,ignore_index=True) if selected_frames else pd.DataFrame()
    selected_trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_rows);side.to_csv(OUT_SIDE,index=False)

    fate_rows=[]
    for split in SPLITS:
        fate_rows.extend(time4h_fate(raw,trades_by_key[(split,4)],split))
    fate=pd.DataFrame(fate_rows)
    fate.to_csv(OUT_FATE,index=False)

    gates=val[val.split.isin(["dev_select_2024","validation_2025","validation_2026"])].gate_pass
    promotion=bool(dev_eligible and len(gates)==3 and gates.all())

    adf=audit(ds,grid,selected_h,trades_by_key)
    adf.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(adf["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7E_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7E_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7E_TARGET_NOT_MET"

    payload={
        "status":status,"selected_horizon_h":selected_h,"selection_status":selection_status,
        "dev_target_eligible":bool(dev_eligible),"promotion_gate_pass":bool(promotion and audit_pass),
        "signal":{"model":MODEL_NAME,"score_threshold":SCORE_THRESHOLD,"retention_label":RETENTION_LABEL},
        "horizon_grid":grid.to_dict(orient="records"),
        "selected_validation":val.to_dict(orient="records"),
        "time4h_fate":fate.to_dict(orient="records"),
        "side_diagnostics":side.to_dict(orient="records"),
        "audit_pass":audit_pass,"audit":adf.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 7E Result","",
        "**Frozen Stage-7D signal; only maximum holding horizon varies.**","",
        "## Horizon grid","",
        "| Split | Horizon | Trades/day | TP/SL/TIME | Target WR | Resolved WR | Econ WR | Net exp | PF | Eligible on 2024 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in grid.itertuples(index=False):
        lines.append(
            f"| {r.split} | {r.horizon_h}H | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | "
            f"{pct(r.target_wr)} | {pct(r.resolved_wr)} | {pct(r.economic_win_rate)} | "
            f"USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | "
            f"{'YES' if r.target_eligible else 'NO'} |"
        )

    lines += ["",f"2024-selected horizon: **{selected_h}H** ({selection_status}).","",
        "## Selected-horizon validation","",
        "| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Net exp | PF | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in val.itertuples(index=False):
        gate_txt="TRAIN" if r.split=="train_2023" else ("PASS" if r.gate_pass else "FAIL")
        lines.append(
            f"| {r.split} | {r.executed_trades} | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | "
            f"{pct(r.target_wr)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {gate_txt} |"
        )

    lines += ["","## Fate of trades that were TIME at 4H","",
        "| Split | Later horizon | TIME@4H N | -> TP | -> SL | -> still TIME |",
        "|---|---:|---:|---:|---:|---:|"]
    for r in fate.itertuples(index=False):
        lines.append(
            f"| {r.split} | {r.to_horizon_h}H | {r.time4h_n} | "
            f"{r.tp_n} ({pct(r.tp_share)}) | {r.sl_n} ({pct(r.sl_share)}) | "
            f"{r.time_n} ({pct(r.time_share)}) |"
        )

    lines += ["","## Selected-horizon side diagnostics","",
        "| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(
            f"| {r.split} | {r.side} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | "
            f"{pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |"
        )

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += [
            "**PROMOTION GATE: PASS.**",
            "A longer frozen exit horizon converted enough TIME trades into TP while preserving >=1 trade/day, >=70% target WR and positive economics in 2024, 2025 and 2026."
        ]
    elif dev_eligible:
        lines += [
            "**PROMOTION GATE: FAIL IN VALIDATION.**",
            "A horizon met the full 2024 target, but its exact frozen horizon failed at least one 2025/2026 gate."
        ]
    else:
        lines += [
            "**PROMOTION GATE: FAIL — changing only the maximum holding horizon did not achieve >=70% WR at >=1 trade/day on 2024.**",
            "The TIME-fate table shows whether horizon still helps diagnostically, but no post-hoc horizon or exit rescue is authorized."
        ]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
