#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7B.

Failure decomposition + finite causal entry-trigger confirmation study.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s7 as s7

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_AUDIT.csv"
OUT_DECOMP_AGE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_A_FAILURE_BY_AGE.csv"
OUT_DECOMP_PATH=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_A_FAILURE_PATH.csv"
OUT_DEV=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_B_TRIGGER_DEV.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_C_VALIDATION.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_D_SIDE.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_E_TRADES.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_Status.txt"

BASE_RULE="R3_STABLE_REGIME_CELLS"
TP=0.01
SL=0.01
COST=0.0015
NOTIONAL=500.0
BAR=pd.Timedelta(minutes=5)
HOLD_BARS=48
PARTS=["development","validation_2025","validation_2026"]

TRIGGERS=[
    "T0_ONSET",
    "T1_PRICE_CONFIRM_5M",
    "T2_PRICE_CONFIRM_15M",
    "T3_PRICE_CONFIRM_30M",
    "T4_STATE_PERSIST_15M",
    "T5_STATE_PERSIST_30M",
    "T6_PERSIST15_AND_PRICE15",
    "T7_PERSIST30_AND_PRICE30",
]
DELAY_MIN={
    "T0_ONSET":0,
    "T1_PRICE_CONFIRM_5M":5,
    "T2_PRICE_CONFIRM_15M":15,
    "T3_PRICE_CONFIRM_30M":30,
    "T4_STATE_PERSIST_15M":15,
    "T5_STATE_PERSIST_30M":30,
    "T6_PERSIST15_AND_PRICE15":15,
    "T7_PERSIST30_AND_PRICE30":30,
}

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def prepare():
    raw,a=s7.prepare()
    a=a.copy()
    a["base_signal"]=[s7.family_signal(r,BASE_RULE) for r in a.itertuples(index=False)]
    sig=a.set_index("decision_time").base_signal
    prev=sig.reindex(pd.DatetimeIndex(a.decision_time)-pd.Timedelta(minutes=15)).to_numpy()
    cur=a.base_signal.to_numpy()
    a["episode_onset"]=(cur!="NO_TRADE")&(prev!=cur)

    onset_ts=[]
    current_onset=None
    current_dir="NO_TRADE"
    for r in a.itertuples(index=False):
        if r.base_signal=="NO_TRADE":
            current_onset=None
            current_dir="NO_TRADE"
            onset_ts.append(pd.NaT)
            continue
        if current_onset is None or r.base_signal!=current_dir or bool(r.episode_onset):
            current_onset=pd.Timestamp(r.decision_time)
            current_dir=r.base_signal
        onset_ts.append(current_onset)
    a["episode_onset_ts"]=pd.to_datetime(onset_ts,utc=True)
    a["episode_age_min"]=(pd.to_datetime(a.decision_time,utc=True)-a.episode_onset_ts).dt.total_seconds()/60.0
    return raw,a

def age_bucket(v):
    if not np.isfinite(v): return "UNKNOWN"
    if v==0: return "ONSET"
    if v==15: return "15m"
    if v==30: return "30m"
    if 45<=v<=60: return "45-60m"
    if v>60: return ">60m"
    return "OTHER"

def intended_ret(side,px,entry):
    sign=1.0 if side=="LONG" else -1.0
    return sign*(float(px)/float(entry)-1.0)

def failure_decomposition(raw,a):
    p=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_TRADES.csv"
    if not p.exists():
        raise RuntimeError("Stage 7 trades artifact missing")
    t=pd.read_csv(p)
    t["entry_ts"]=pd.to_datetime(t.entry_ts,utc=True)
    amap=a.set_index("decision_time")
    posmap={ts:i for i,ts in enumerate(raw.ts)}

    rows=[]
    for r in t.itertuples(index=False):
        et=pd.Timestamp(r.entry_ts)
        if et not in amap.index:
            continue
        ar=amap.loc[et]
        i=posmap.get(et)
        if i is None or i+6>len(raw):
            continue
        w5=raw.iloc[i:i+1]
        w15=raw.iloc[i:i+3]
        w30=raw.iloc[i:i+6]
        entry=float(r.entry_price)
        side=r.side
        first5=intended_ret(side,w5.close.iloc[-1],entry)
        ret15=intended_ret(side,w15.close.iloc[-1],entry)
        ret30=intended_ret(side,w30.close.iloc[-1],entry)
        if side=="LONG":
            mfe15=float(w15.high.max()/entry-1.0)
            mae15=float(max(0.0,1.0-w15.low.min()/entry))
        else:
            mfe15=float(max(0.0,1.0-w15.low.min()/entry))
            mae15=float(max(0.0,w15.high.max()/entry-1.0))
        rows.append({
            "partition":r.partition,"exit_reason":r.exit_reason,"side":side,
            "entry_ts":et,"episode_age_min":float(ar.episode_age_min),
            "age_bucket":age_bucket(float(ar.episode_age_min)),
            "first5_intended_ret":first5,"ret15_intended":ret15,"ret30_intended":ret30,
            "mfe15":mfe15,"mae15":mae15,
        })
    d=pd.DataFrame(rows)

    age_rows=[]
    order=["ONSET","15m","30m","45-60m",">60m"]
    for part in PARTS:
        for ab in order:
            g=d[(d.partition==part)&(d.age_bucket==ab)]
            n=len(g)
            age_rows.append({
                "partition":part,"age_bucket":ab,"n":n,
                "tp_rate":float((g.exit_reason=="TP").mean()) if n else np.nan,
                "sl_rate":float((g.exit_reason=="SL").mean()) if n else np.nan,
                "time_rate":float((g.exit_reason=="TIME").mean()) if n else np.nan,
            })
    age_df=pd.DataFrame(age_rows)

    path_rows=[]
    for part in PARTS:
        for outcome in ["TP","SL","TIME"]:
            g=d[(d.partition==part)&(d.exit_reason==outcome)]
            path_rows.append({
                "partition":part,"outcome":outcome,"n":len(g),
                "median_first5_intended_ret":float(g.first5_intended_ret.median()) if len(g) else np.nan,
                "median_ret15_intended":float(g.ret15_intended.median()) if len(g) else np.nan,
                "median_ret30_intended":float(g.ret30_intended.median()) if len(g) else np.nan,
                "median_mfe15":float(g.mfe15.median()) if len(g) else np.nan,
                "median_mae15":float(g.mae15.median()) if len(g) else np.nan,
            })
    return age_df,pd.DataFrame(path_rows),d

def exact_raw_close(raw,pos,n_bars):
    if pos is None or pos+n_bars>len(raw):
        return None
    w=raw.iloc[pos:pos+n_bars]
    if len(w)!=n_bars: return None
    if not bool((w.ts.diff().dropna()==BAR).all()): return None
    return float(w.close.iloc[-1])

def candidate_entries(raw,a,trigger,part):
    q=a[(a.partition==part)&a.episode_onset&a.future_complete_4h].copy()
    q=q.sort_values("decision_time")
    sig=a.set_index("decision_time").base_signal
    posmap={ts:i for i,ts in enumerate(raw.ts)}
    rows=[]

    for r in q.itertuples(index=False):
        t0=pd.Timestamp(r.decision_time)
        side=r.base_signal
        if side not in {"LONG","SHORT"}: continue
        p0=posmap.get(t0)
        if p0 is None: continue
        anchor=float(r.entry_price)

        price5=False; price15=False; price30=False
        c5=exact_raw_close(raw,p0,1)
        c15=exact_raw_close(raw,p0,3)
        c30=exact_raw_close(raw,p0,6)
        if c5 is not None:
            price5=(c5>anchor) if side=="LONG" else (c5<anchor)
        if c15 is not None:
            price15=(c15>anchor) if side=="LONG" else (c15<anchor)
        if c30 is not None:
            price30=(c30>anchor) if side=="LONG" else (c30<anchor)

        s15=sig.get(t0+pd.Timedelta(minutes=15),"NO_TRADE")
        s30=sig.get(t0+pd.Timedelta(minutes=30),"NO_TRADE")
        persist15=(s15==side)
        persist30=(s15==side and s30==side)

        delay=DELAY_MIN[trigger]
        ok=False
        if trigger=="T0_ONSET": ok=True
        elif trigger=="T1_PRICE_CONFIRM_5M": ok=price5
        elif trigger=="T2_PRICE_CONFIRM_15M": ok=price15
        elif trigger=="T3_PRICE_CONFIRM_30M": ok=price30
        elif trigger=="T4_STATE_PERSIST_15M": ok=persist15
        elif trigger=="T5_STATE_PERSIST_30M": ok=persist30
        elif trigger=="T6_PERSIST15_AND_PRICE15": ok=persist15 and price15
        elif trigger=="T7_PERSIST30_AND_PRICE30": ok=persist30 and price30
        if not ok: continue

        et=t0+pd.Timedelta(minutes=delay)
        ep=posmap.get(et)
        if ep is None or ep+HOLD_BARS>len(raw): continue
        # Prevent partition crossing by requiring entry time remain in same frozen partition.
        if s3.partition(et)!=part: continue
        rows.append({
            "partition":part,"trigger":trigger,"onset_ts":t0,"entry_ts":et,
            "side":side,"onset_market_state":r.market_state,"onset_regime":r.regime,
        })
    return pd.DataFrame(rows)

def simulate_trigger(raw,candidates,part,trigger):
    days=s7.coverage_days(raw,part)
    if candidates is None or len(candidates)==0:
        return s7.summarize_trades(pd.DataFrame(),days,0),pd.DataFrame()
    c=candidates.sort_values(["entry_ts","onset_ts"]).copy()
    raw_signals=len(c)
    posmap={ts:i for i,ts in enumerate(raw.ts)}
    rows=[]; active_until=None

    for r in c.itertuples(index=False):
        et=pd.Timestamp(r.entry_ts)
        if active_until is not None and et<active_until:
            continue
        p=posmap.get(et)
        if p is None or p+HOLD_BARS>len(raw): continue
        w=raw.iloc[p:p+HOLD_BARS]
        if len(w)!=HOLD_BARS or w.ts.iloc[0]!=et or w.ts.iloc[-1]!=et+pd.Timedelta(hours=4)-BAR:
            continue
        if not bool((w.ts.diff().dropna()==BAR).all()): continue

        entry=float(w.open.iloc[0]); side=r.side
        if side=="LONG":
            tp_px=entry*(1+TP); sl_px=entry*(1-SL)
        else:
            tp_px=entry*(1-TP); sl_px=entry*(1+SL)

        reason="TIME"; samebar=False; exit_px=float(w.close.iloc[-1]); exit_ts=et+pd.Timedelta(hours=4)
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
        net=gross-COST
        rows.append({
            "partition":part,"trigger":trigger,"onset_ts":r.onset_ts,"entry_ts":et,
            "side":side,"onset_market_state":r.onset_market_state,"onset_regime":r.onset_regime,
            "entry_price":entry,"exit_ts":exit_ts,"exit_price":float(exit_px),
            "exit_reason":reason,"samebar_sl":bool(samebar),
            "hold_min":float((exit_ts-et)/pd.Timedelta(minutes=1)),
            "gross_return":float(gross),"net_return":float(net),"net_pnl_usd":float(net*NOTIONAL),
        })
        active_until=exit_ts
    trades=pd.DataFrame(rows)
    return s7.summarize_trades(trades,days,raw_signals),trades

def target_eligible(m):
    return m["trades_per_day"]>=1.0 and m["target_wr"]>=0.70 and m["net_expectancy_return"]>0 and m["profit_factor"]>1

def select_trigger(dev):
    elig=dev[dev.target_eligible].copy()
    if len(elig):
        q=elig.sort_values(["target_wr","net_expectancy_return","trades_per_day","delay_min","trigger"],
            ascending=[False,False,False,True,True]).iloc[0]
        return str(q.trigger),True,"TARGET_ELIGIBLE"
    pool=dev[dev.trades_per_day>=1.0].copy()
    if len(pool):
        q=pool.sort_values(["target_wr","net_expectancy_return","delay_min","trigger"],
            ascending=[False,False,True,True]).iloc[0]
        return str(q.trigger),False,"DIAGNOSTIC_TRIGGER_TARGET_NOT_MET"
    q=dev.sort_values(["trades_per_day","target_wr","delay_min","trigger"],
        ascending=[False,False,True,True]).iloc[0]
    return str(q.trigger),False,"DIAGNOSTIC_TRIGGER_NO_1TPD"

def side_rows(trades,part,raw):
    out=[]
    days=s7.coverage_days(raw,part)
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        m=s7.summarize_trades(g,days,len(g))
        row={"partition":part,"side":side}; row.update(m); out.append(row)
    return out

def audit(raw,a,dev,selected,all_trades):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    s7status=(ROOT/"SOL_INDICATOR_RELATIONSHIP_S7_Status.txt").read_text().strip()
    add("parent_stage7_target_not_met",s7status=="SOL_INDICATOR_RELATIONSHIP_S7_TARGET_NOT_MET",s7status)
    add("base_rule_frozen",BASE_RULE=="R3_STABLE_REGIME_CELLS",BASE_RULE)
    add("tp_sl_frozen_1pct",TP==.01 and SL==.01,{"tp":TP,"sl":SL})
    add("trigger_count_exact",len(TRIGGERS)==8,TRIGGERS)
    add("dev_selection_only",True,selected)
    overlap=0
    if len(all_trades):
        for p in PARTS:
            g=all_trades[all_trades.partition==p].sort_values("entry_ts")
            if len(g)>1:
                prev=pd.to_datetime(g.exit_ts,utc=True).shift(1)
                cur=pd.to_datetime(g.entry_ts,utc=True)
                overlap+=int((cur<prev).fillna(False).sum())
    add("one_position_no_overlap",overlap==0,overlap)
    add("entry_delays_frozen",all(DELAY_MIN[t] in {0,5,15,30} for t in TRIGGERS),DELAY_MIN)
    add("all_dev_rows_have_target_flag","target_eligible" in dev.columns,int(len(dev)))
    return pd.DataFrame(rows)

def main():
    raw,a=prepare()

    age_df,path_df,_=failure_decomposition(raw,a)
    age_df.to_csv(OUT_DECOMP_AGE,index=False)
    path_df.to_csv(OUT_DECOMP_PATH,index=False)

    dev_rows=[]
    dev_trades={}
    for trigger in TRIGGERS:
        cand=candidate_entries(raw,a,trigger,"development")
        m,t=simulate_trigger(raw,cand,"development",trigger)
        row={"trigger":trigger,"delay_min":DELAY_MIN[trigger]}
        row.update(m); row["target_eligible"]=target_eligible(m)
        dev_rows.append(row); dev_trades[trigger]=t
    dev=pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV,index=False)

    selected,dev_eligible,selection_status=select_trigger(dev)

    val_rows=[]; trades_all=[]; side_all=[]
    for p in PARTS:
        cand=candidate_entries(raw,a,selected,p)
        m,t=simulate_trigger(raw,cand,p,selected)
        gate=target_eligible(m)
        row={"partition":p,"trigger":selected,"delay_min":DELAY_MIN[selected],"gate_pass":gate}
        row.update(m); val_rows.append(row)
        if len(t): trades_all.append(t)
        side_all.extend(side_rows(t,p,raw))
    val=pd.DataFrame(val_rows)
    val.to_csv(OUT_VAL,index=False)
    trades=pd.concat(trades_all,ignore_index=True) if trades_all else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_all)
    side.to_csv(OUT_SIDE,index=False)

    promotion=bool(dev_eligible and val.gate_pass.all())
    adf=audit(raw,a,dev,selected,trades)
    adf.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(adf["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7B_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7B_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7B_TARGET_NOT_MET"

    payload={
        "status":status,"selected_trigger":selected,"selection_status":selection_status,
        "dev_target_eligible":bool(dev_eligible),"promotion_gate_pass":bool(promotion and audit_pass),
        "dev_triggers":dev.to_dict(orient="records"),
        "validation":val.to_dict(orient="records"),
        "failure_by_age":age_df.to_dict(orient="records"),
        "failure_path":path_df.to_dict(orient="records"),
        "side_diagnostics":side.to_dict(orient="records"),
        "audit_pass":audit_pass,"audit":adf.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=["# SOL Indicator Relationship Discovery — Stage 7B Result","",
      "**Entry-trigger / failure decomposition. Frozen R3 base rule, TP1% / SL1%.**","",
      "## A. Stage-7 failure by episode age","",
      "| Partition | Episode age | N | TP | SL | TIME |",
      "|---|---|---:|---:|---:|---:|"]
    for r in age_df.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.age_bucket} | {r.n} | {pct(r.tp_rate)} | {pct(r.sl_rate)} | {pct(r.time_rate)} |")

    lines += ["","## B. Early path anatomy by final outcome","",
      "| Partition | Outcome | N | first 5m | 15m | 30m | 15m MFE | 15m MAE |",
      "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in path_df.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.outcome} | {r.n} | {pct(r.median_first5_intended_ret)} | {pct(r.median_ret15_intended)} | {pct(r.median_ret30_intended)} | {pct(r.median_mfe15)} | {pct(r.median_mae15)} |")

    lines += ["","## C. DEV trigger candidates","",
      "| Trigger | Delay | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |",
      "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in dev.itertuples(index=False):
        lines.append(f"| {r.trigger} | {r.delay_min}m | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {'YES' if r.target_eligible else 'NO'} |")

    lines += ["",f"DEV-selected trigger: **{selected}** ({selection_status}).","",
      "## D. Frozen validation","",
      "| Partition | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in val.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.executed_trades} | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {'PASS' if r.gate_pass else 'FAIL'} |")

    lines += ["","## E. Selected-trigger side diagnostics","",
      "| Partition | Side | Trades/day | Target WR | Econ WR | Net exp | PF |",
      "|---|---|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(f"| {r.partition} | {r.side} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |")

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += ["**PROMOTION GATE: PASS.**",
          "A frozen onset/confirmation trigger achieved >=1 trade/day, >=70% TP-hit WR, positive expectancy and PF>1 in DEV, 2025 and 2026."]
    elif dev_eligible:
        lines += ["**PROMOTION GATE: FAIL IN VALIDATION.**",
          "A trigger met the full DEV target but failed at least one untouched validation gate. No rescue retuning is allowed."]
    else:
        lines += ["**PROMOTION GATE: FAIL — entry timing alone did not reach the >=70% DEV target at >=1 trade/day.**",
          "The selected trigger is diagnostic only. Stage 7B does not authorize adding ad-hoc thresholds after seeing these results."]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
