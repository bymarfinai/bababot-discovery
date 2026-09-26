#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7 signal rule discovery."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s6 as s6

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7_AUDIT.csv"
OUT_FAMILY=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7A_FAMILY_DEV.csv"
OUT_GRID=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_TPSL_DEV.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_VALIDATION.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_TRADES.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_SIDE_DIAGNOSTICS.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7_Status.txt"

PARTS=["development","validation_2025","validation_2026"]
RULES=[
    "R1_CORE_DIRECTIONAL_STATES",
    "R2_DIRECTIONAL_PLUS_EXPANSION",
    "R3_STABLE_REGIME_CELLS",
    "R4_CORE_PLUS_STABLE_ADDITIONS",
]
GRID=[
    ("TP1.00_SL1.00",0.0100,0.0100),
    ("TP1.25_SL1.00",0.0125,0.0100),
    ("TP1.25_SL1.25",0.0125,0.0125),
    ("TP1.50_SL1.00",0.0150,0.0100),
    ("TP1.50_SL1.25",0.0150,0.0125),
    ("TP1.50_SL1.50",0.0150,0.0150),
    ("TP2.00_SL1.00",0.0200,0.0100),
    ("TP2.00_SL1.25",0.0200,0.0125),
    ("TP2.00_SL1.50",0.0200,0.0150),
]
BASE_COST=0.0015
STRESS_COST=0.0025
NOTIONAL=500.0
HOLD_BARS=48
BAR=pd.Timedelta(minutes=5)

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def family_signal(row,rule):
    st=row.market_state
    reg=row.regime
    if rule=="R1_CORE_DIRECTIONAL_STATES":
        if st in {"DOWN_POSITION_BUILD","HIGHLOC_SELL_ABSORPTION_LIKE"}: return "LONG"
        if st in {"POST_BREAKDOWN_UNWIND_30M","UP_UNWIND_LIKE","HIGHLOC_BUY_EXHAUSTION_LIKE"}: return "SHORT"
        return "NO_TRADE"
    if rule=="R2_DIRECTIONAL_PLUS_EXPANSION":
        if st=="DOWN_POSITION_BUILD": return "LONG"
        if st in {"POST_BREAKDOWN_UNWIND_30M","UP_UNWIND_LIKE"}: return "SHORT"
        return "NO_TRADE"
    if rule=="R3_STABLE_REGIME_CELLS":
        if (reg=="SIDEWAYS" and st=="HIGHLOC_BUY_BUILD") or (reg=="TRANSITION" and st=="HIGHLOC_SELL_ABSORPTION_LIKE"):
            return "LONG"
        if ((reg=="BULL" and st=="DELEVERAGING")
            or (reg=="SIDEWAYS" and st=="HIGHLOC_BUY_EXHAUSTION_LIKE")
            or (reg=="SIDEWAYS" and st=="DELEVERAGING")
            or (reg=="TRANSITION" and st=="HIGHLOC_BUY_EXHAUSTION_LIKE")):
            return "SHORT"
        return "NO_TRADE"
    if rule=="R4_CORE_PLUS_STABLE_ADDITIONS":
        if st in {"DOWN_POSITION_BUILD","HIGHLOC_SELL_ABSORPTION_LIKE"}: return "LONG"
        if st in {"POST_BREAKDOWN_UNWIND_30M","UP_UNWIND_LIKE","HIGHLOC_BUY_EXHAUSTION_LIKE"}: return "SHORT"
        if reg=="SIDEWAYS" and st=="HIGHLOC_BUY_BUILD": return "LONG"
        if (reg=="BULL" and st=="DELEVERAGING") or (reg=="SIDEWAYS" and st=="DELEVERAGING"): return "SHORT"
        return "NO_TRADE"
    raise ValueError(rule)

def prepare():
    raw,a=s6.prepare_relationship_data()
    specs=s6.load_stage4_specs()
    hourly=s6.build_hourly_regime(raw)
    a=s6.attach_regime(a,hourly)
    a=s6.attach_buckets(a,specs)
    a=s6.build_state_tags(a)
    return raw.sort_values("ts").reset_index(drop=True),a.sort_values("decision_time").reset_index(drop=True)

def coverage_days(raw,part):
    raw_end=pd.Timestamp(raw.ts.max())+BAR
    if part=="development":
        st=s3.SCORE_START; en=min(s3.DEV_END,raw_end)
    elif part=="validation_2025":
        st=s3.DEV_END; en=min(s3.VAL25_END,raw_end)
    elif part=="validation_2026":
        st=s3.VAL25_END; en=min(s3.END,raw_end)
    else:
        raise ValueError(part)
    return max(0.0,float((en-st)/pd.Timedelta(days=1)))

def max_loss_streak(vals):
    m=0;c=0
    for v in vals:
        if v<=0:
            c+=1;m=max(m,c)
        else:
            c=0
    return m

def summarize_trades(trades,days,raw_signals=0):
    if trades is None or len(trades)==0:
        return {
            "raw_signals":int(raw_signals),"executed_trades":0,"skipped_active":int(raw_signals),
            "trades_per_day":0.0,"tp":0,"sl":0,"time":0,"samebar_sl":0,
            "target_wr":0.0,"resolved_wr":np.nan,"economic_win_rate":0.0,
            "net_expectancy_return":0.0,"net_expectancy_usd":0.0,"profit_factor":0.0,
            "total_net_usd":0.0,"max_loss_streak":0,"median_hold_min":np.nan,
        }
    t=trades
    n=len(t); ntp=int((t.exit_reason=="TP").sum()); nsl=int((t.exit_reason=="SL").sum())
    ntm=int((t.exit_reason=="TIME").sum()); sb=int(t.samebar_sl.sum())
    pos=float(t.loc[t.net_pnl_usd>0,"net_pnl_usd"].sum())
    neg=float(-t.loc[t.net_pnl_usd<0,"net_pnl_usd"].sum())
    pf=(pos/neg) if neg>0 else (np.inf if pos>0 else 0.0)
    resolved=ntp+nsl
    return {
        "raw_signals":int(raw_signals),"executed_trades":int(n),"skipped_active":int(raw_signals-n),
        "trades_per_day":float(n/days) if days>0 else np.nan,
        "tp":ntp,"sl":nsl,"time":ntm,"samebar_sl":sb,
        "target_wr":float(ntp/n),
        "resolved_wr":float(ntp/resolved) if resolved else np.nan,
        "economic_win_rate":float((t.net_pnl_usd>0).mean()),
        "net_expectancy_return":float(t.net_return.mean()),
        "net_expectancy_usd":float(t.net_pnl_usd.mean()),
        "profit_factor":float(pf),
        "total_net_usd":float(t.net_pnl_usd.sum()),
        "max_loss_streak":int(max_loss_streak(t.net_pnl_usd.to_numpy(float))),
        "median_hold_min":float(t.hold_min.median()),
    }

def simulate(a,raw,rule,tp,sl,part,cost=BASE_COST):
    q=a[(a.partition==part)&a.future_complete_4h].copy()
    q["signal"]=[family_signal(r,rule) for r in q.itertuples(index=False)]
    q=q[q.signal!="NO_TRADE"].sort_values("decision_time")
    raw_signals=len(q)
    days=coverage_days(raw,part)
    posmap={t:i for i,t in enumerate(raw.ts)}
    rows=[]
    active_until=None
    for r in q.itertuples(index=False):
        t=pd.Timestamp(r.decision_time)
        if active_until is not None and t<active_until:
            continue
        p=posmap.get(t)
        if p is None or p+HOLD_BARS>len(raw):
            continue
        w=raw.iloc[p:p+HOLD_BARS]
        if len(w)!=HOLD_BARS or w.ts.iloc[0]!=t or w.ts.iloc[-1]!=t+pd.Timedelta(hours=4)-BAR:
            continue
        if not bool((w.ts.diff().dropna()==BAR).all()):
            continue

        entry=float(r.entry_price)
        side=r.signal
        if side=="LONG":
            tp_px=entry*(1+tp); sl_px=entry*(1-sl)
        else:
            tp_px=entry*(1-tp); sl_px=entry*(1+sl)

        reason="TIME"; samebar=False
        exit_px=float(w.close.iloc[-1]); exit_ts=t+pd.Timedelta(hours=4)
        for br in w.itertuples(index=False):
            if side=="LONG":
                hit_tp=float(br.high)>=tp_px; hit_sl=float(br.low)<=sl_px
            else:
                hit_tp=float(br.low)<=tp_px; hit_sl=float(br.high)>=sl_px
            if hit_tp and hit_sl:
                reason="SL"; samebar=True; exit_px=sl_px; exit_ts=pd.Timestamp(br.ts)+BAR; break
            if hit_sl:
                reason="SL"; exit_px=sl_px; exit_ts=pd.Timestamp(br.ts)+BAR; break
            if hit_tp:
                reason="TP"; exit_px=tp_px; exit_ts=pd.Timestamp(br.ts)+BAR; break

        sign=1.0 if side=="LONG" else -1.0
        gross=sign*(exit_px/entry-1.0)
        net=gross-cost
        rows.append({
            "partition":part,"rule":rule,"config":f"TP{tp*100:.2f}_SL{sl*100:.2f}",
            "tp_pct":tp,"sl_pct":sl,"rr":tp/sl,"cost":cost,
            "decision_time":t,"entry_ts":t,"entry_price":entry,"side":side,
            "market_state":r.market_state,"regime":r.regime,
            "exit_ts":exit_ts,"exit_price":float(exit_px),"exit_reason":reason,
            "samebar_sl":bool(samebar),"hold_min":float((exit_ts-t)/pd.Timedelta(minutes=1)),
            "gross_return":float(gross),"net_return":float(net),"net_pnl_usd":float(net*NOTIONAL),
        })
        active_until=exit_ts

    trades=pd.DataFrame(rows)
    return summarize_trades(trades,days,raw_signals),trades

def row_with_meta(metrics,**meta):
    out=dict(meta);out.update(metrics);return out

def select_family(fam):
    elig=fam[(fam.trades_per_day>=1.0)&(fam.net_expectancy_return>0)&(fam.profit_factor>1)].copy()
    if len(elig):
        q=elig.sort_values(["target_wr","net_expectancy_return","trades_per_day","rule"],
                           ascending=[False,False,False,True]).iloc[0]
        return str(q.rule),"ELIGIBLE_FAMILY"
    pool=fam[fam.trades_per_day>=1.0].copy()
    if len(pool):
        q=pool.sort_values(["target_wr","net_expectancy_return","trades_per_day","rule"],
                           ascending=[False,False,False,True]).iloc[0]
        return str(q.rule),"DIAGNOSTIC_FAMILY_NO_ECONOMIC_ELIGIBLE"
    q=fam.sort_values(["trades_per_day","target_wr","net_expectancy_return","rule"],
                      ascending=[False,False,False,True]).iloc[0]
    return str(q.rule),"DIAGNOSTIC_FAMILY_NO_1TPD"

def target_eligible_row(r):
    return (
        float(r["trades_per_day"])>=1.0 and float(r["target_wr"])>=0.70
        and float(r["net_expectancy_return"])>0 and float(r["profit_factor"])>1
        and float(r["tp_pct"])>=0.01 and float(r["rr"])>=1.0
    )

def select_config(grid):
    mask=grid.apply(lambda r: target_eligible_row(r),axis=1)
    elig=grid[mask].copy()
    if len(elig):
        q=elig.sort_values(["target_wr","net_expectancy_return","trades_per_day","rr","config"],
                           ascending=[False,False,False,False,True]).iloc[0]
        return str(q.config),True,"TARGET_ELIGIBLE"
    pool=grid[grid.trades_per_day>=1.0].copy()
    if len(pool):
        q=pool.sort_values(["target_wr","net_expectancy_return","rr","config"],
                           ascending=[False,False,False,True]).iloc[0]
        return str(q.config),False,"DIAGNOSTIC_CONFIG_TARGET_NOT_MET"
    q=grid.sort_values(["trades_per_day","target_wr","net_expectancy_return","rr","config"],
                       ascending=[False,False,False,False,True]).iloc[0]
    return str(q.config),False,"DIAGNOSTIC_CONFIG_NO_1TPD"

def validation_pass_metrics(m):
    return m["trades_per_day"]>=1.0 and m["target_wr"]>=0.70 and m["net_expectancy_return"]>0 and m["profit_factor"]>1

def side_summary(trades,part,days):
    rows=[]
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        m=summarize_trades(g,days,len(g))
        rows.append(row_with_meta(m,partition=part,side=side))
    return rows

def make_audit(raw,a,selected_trades,selected_rule,tp,sl,dev_eligible):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    s6status=(ROOT/"SOL_INDICATOR_RELATIONSHIP_S6_Status.txt").read_text().strip()
    add("stage6_completed",s6status=="SOL_INDICATOR_RELATIONSHIP_S6_COMPLETED_WITH_REPLICATED_STATES",s6status)
    add("decision_rows_match_stage6",len(a)==130848,len(a))
    add("grid_tp_ge_1pct",all(tp0>=.01 for _,tp0,_ in GRID),min(tp0 for _,tp0,_ in GRID))
    add("grid_rr_ge_1",all(tp0/sl0>=1 for _,tp0,sl0 in GRID),min(tp0/sl0 for _,tp0,sl0 in GRID))
    add("selected_config_valid",tp>=.01 and tp/sl>=1,{"tp":tp,"sl":sl,"rr":tp/sl})
    rawopen=raw.set_index("ts").open
    chk=a[a.future_complete_4h].copy()
    aligned=rawopen.reindex(pd.DatetimeIndex(chk.decision_time)).to_numpy(float)
    diff=np.nanmax(np.abs(aligned-chk.entry_price.to_numpy(float))) if len(chk) else np.inf
    add("entry_anchor_matches_raw_5m_open",np.isfinite(diff) and diff<=1e-12,float(diff))
    overlap=0
    for p in PARTS:
        g=selected_trades[selected_trades.partition==p].sort_values("entry_ts") if len(selected_trades) else pd.DataFrame()
        if len(g)>1:
            prev_exit=pd.to_datetime(g.exit_ts,utc=True).shift(1)
            cur=pd.to_datetime(g.entry_ts,utc=True)
            overlap+=int((cur<prev_exit).fillna(False).sum())
    add("one_position_no_overlap",overlap==0,overlap)
    add("selection_family_from_dev_only",True,selected_rule)
    add("selection_config_from_dev_only",True,{"tp":tp,"sl":sl,"dev_target_eligible":dev_eligible})
    add("base_cost_exact",BASE_COST==0.0015,BASE_COST)
    return pd.DataFrame(rows)

def main():
    raw,a=prepare()

    fam_rows=[]
    for rule in RULES:
        m,_=simulate(a,raw,rule,.01,.01,"development",BASE_COST)
        fam_rows.append(row_with_meta(m,rule=rule,tp_pct=.01,sl_pct=.01,rr=1.0))
    fam=pd.DataFrame(fam_rows)
    fam.to_csv(OUT_FAMILY,index=False)
    selected_rule,family_status=select_family(fam)

    grid_rows=[]
    for name,tp0,sl0 in GRID:
        m,_=simulate(a,raw,selected_rule,tp0,sl0,"development",BASE_COST)
        grid_rows.append(row_with_meta(m,config=name,rule=selected_rule,tp_pct=tp0,sl_pct=sl0,rr=tp0/sl0))
    grid=pd.DataFrame(grid_rows)
    grid.to_csv(OUT_GRID,index=False)
    selected_config,dev_eligible,config_status=select_config(grid)
    cr=grid[grid.config==selected_config].iloc[0]
    tp=float(cr.tp_pct); sl=float(cr.sl_pct)

    val_rows=[]; all_trades=[]; side_rows=[]; stress={}
    for p in PARTS:
        m,t=simulate(a,raw,selected_rule,tp,sl,p,BASE_COST)
        val_rows.append(row_with_meta(m,partition=p,rule=selected_rule,config=selected_config,
                                      tp_pct=tp,sl_pct=sl,rr=tp/sl,cost=BASE_COST,
                                      gate_pass=validation_pass_metrics(m)))
        if len(t): all_trades.append(t)
        side_rows.extend(side_summary(t,p,coverage_days(raw,p)))
        sm,_=simulate(a,raw,selected_rule,tp,sl,p,STRESS_COST)
        stress[p]=sm

    val=pd.DataFrame(val_rows)
    val.to_csv(OUT_VAL,index=False)
    trades=pd.concat(all_trades,ignore_index=True) if all_trades else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_rows)
    side.to_csv(OUT_SIDE,index=False)

    promotion=bool(dev_eligible and val.gate_pass.all())
    audit=make_audit(raw,a,trades,selected_rule,tp,sl,dev_eligible)
    audit.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(audit["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7_TARGET_NOT_MET"

    payload={
        "status":status,"selected_rule":selected_rule,"family_selection_status":family_status,
        "selected_config":selected_config,"config_selection_status":config_status,
        "dev_target_eligible":bool(dev_eligible),"promotion_gate_pass":bool(promotion and audit_pass),
        "base_cost":BASE_COST,"stress_cost":STRESS_COST,"notional_usd":NOTIONAL,
        "family_dev":fam.to_dict(orient="records"),"grid_dev":grid.to_dict(orient="records"),
        "validation":val.to_dict(orient="records"),"stress_validation":stress,
        "side_diagnostics":side.to_dict(orient="records"),"audit_pass":audit_pass,
        "audit":audit.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
      "# SOL Indicator Relationship Discovery — Stage 7 Result","",
      "**Frozen Stage-6 states -> executable LONG/SHORT/NO-TRADE rules. Research only.**","",
      "## Stage 7A — DEV family selection at TP1% / SL1%","",
      "| Rule | Trades | Trades/day | Target WR | Econ WR | Net exp | PF | Total net |",
      "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in fam.itertuples(index=False):
        lines.append(f"| {r.rule} | {r.executed_trades} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | USD {r.total_net_usd:.2f} |")
    lines += ["",f"DEV-selected family: **{selected_rule}** ({family_status}).","",
      "## Stage 7B — DEV TP/SL grid for selected family","",
      "| Config | Trades/day | Target WR | Resolved WR | Net exp | PF | Total net | Eligible |",
      "|---|---:|---:|---:|---:|---:|---:|---|"]
    for _,r in grid.iterrows():
        eligible=target_eligible_row(r)
        lines.append(f"| {r['config']} | {r['trades_per_day']:.2f} | {pct(r['target_wr'])} | {pct(r['resolved_wr'])} | USD {r['net_expectancy_usd']:.3f} | {r['profit_factor']:.2f} | USD {r['total_net_usd']:.2f} | {'YES' if eligible else 'NO'} |")
    lines += ["",f"Selected config: **{selected_config}** ({config_status}).","",
      "## Stage 7C — frozen validation","",
      "| Partition | Trades | Trades/day | TP / SL / TIME | Target WR | Econ WR | Net exp | PF | Total net | Gate |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in val.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.executed_trades} | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | USD {r.total_net_usd:.2f} | {'PASS' if r.gate_pass else 'FAIL'} |")

    lines += ["","## Side diagnostics for frozen rule/config","",
      "| Partition | Side | Trades | Trades/day | Target WR | Econ WR | Net exp | PF |",
      "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.side} | {r.executed_trades} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |")

    lines += ["","## 0.25% round-trip cost stress","",
      "| Partition | Target WR | Net exp | PF | Total net |",
      "|---|---:|---:|---:|---:|"]
    for p in PARTS:
        rr=stress[p]
        lines.append(f"| {p} | {pct(rr['target_wr'])} | USD {rr['net_expectancy_usd']:.3f} | {rr['profit_factor']:.2f} | USD {rr['total_net_usd']:.2f} |")

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += ["**PROMOTION GATE: PASS**","",
          "The exact DEV-selected rule/config met >=1 trade/day, >=70% TP-hit rate, positive net expectancy and PF>1 in DEV, 2025 and 2026 without retuning."]
    elif dev_eligible:
        lines += ["**PROMOTION GATE: FAIL — validation did not replicate the full target.**","",
          "A DEV configuration met the target, but the exact frozen configuration failed at least one 2025/2026 gate. No rescue retuning is permitted in Stage 7."]
    else:
        lines += ["**PROMOTION GATE: FAIL — the >=70% target was not achieved in DEV under the frozen >=1 trade/day constraint.**","",
          "The selected configuration is diagnostic only. Validation is reported for transparency, but it cannot be promoted even if a later partition looks better."]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
