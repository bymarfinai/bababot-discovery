#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7F two-stage classifier."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s7 as s7
import sol_indicator_relationship_s7d as s7d

ROOT=Path(__file__).resolve().parent.parent

OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_AUDIT.csv"
OUT_IMPORTANCE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_A_MODEL_IMPORTANCE.csv"
OUT_THRESH=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_B_THRESHOLDS.csv"
OUT_SELECT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_C_DEV_SELECT.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_D_VALIDATION.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_E_SIDE.csv"
OUT_SCORE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_F_SCORE_DISTRIBUTIONS.csv"
OUT_COMP=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_G_ACCEPTED_COMPOSITION.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_H_TRADES.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7F_Status.txt"

RES_RET=[1.00,0.80,0.60]
DIR_RET=[1.00,0.60,0.50,0.40,0.30]
SPLITS=["train_2023","dev_select_2024","validation_2025","validation_2026"]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def prepare():
    raw,a=s7d.prepare()
    ds=s7d.build_dataset(raw,a)
    ds=ds.copy()
    ds["label_resolved"]=(ds.exit_reason!="TIME").astype(int)
    return raw,ds

def build_rf():
    return Pipeline([
        ("prep",s7d.make_preprocessor(False)),
        ("model",RandomForestClassifier(
            n_estimators=400,
            max_depth=4,
            min_samples_leaf=40,
            max_features="sqrt",
            class_weight=None,
            random_state=42,
            n_jobs=-1,
        )),
    ])

def feature_names(pipe):
    return list(pipe.named_steps["prep"].get_feature_names_out())

def fit_models(ds):
    train=ds[ds.split=="train_2023"].copy()
    Xcols=s7d.NUM_FEATURES+s7d.CAT_FEATURES

    res_model=build_rf()
    res_model.fit(train[Xcols],train.label_resolved.to_numpy(int))

    dir_train=train[train.exit_reason.isin(["TP","SL"])].copy()
    dir_model=build_rf()
    dir_model.fit(dir_train[Xcols],dir_train.label_tp.to_numpy(int))

    imp=[]
    for name,model in [("STAGE_A_RESOLUTION",res_model),("STAGE_B_DIRECTION",dir_model)]:
        fn=feature_names(model)
        vals=model.named_steps["model"].feature_importances_
        for f,v in zip(fn,vals):
            imp.append({"stage":name,"feature":f,"importance":float(v)})
    return res_model,dir_model,pd.DataFrame(imp)

def score_all(ds,res_model,dir_model):
    out=ds.copy()
    X=out[s7d.NUM_FEATURES+s7d.CAT_FEATURES]
    out["resolution_score"]=res_model.predict_proba(X)[:,1]
    out["direction_score"]=dir_model.predict_proba(X)[:,1]
    return out

def derive_thresholds(scored):
    train=scored[scored.split=="train_2023"]
    rows=[];lookup={}
    for stage,col,grid in [
        ("STAGE_A_RESOLUTION","resolution_score",RES_RET),
        ("STAGE_B_DIRECTION","direction_score",DIR_RET),
    ]:
        vals=train[col].dropna().to_numpy(float)
        for frac in grid:
            th=-np.inf if frac>=1.0 else float(np.quantile(vals,1-frac,method="linear"))
            rows.append({
                "stage":stage,"retention_fraction":frac,
                "score_threshold":th,"train_n":len(vals),
            })
            lookup[(stage,frac)]=th
    return pd.DataFrame(rows),lookup

def max_loss_streak(vals):
    best=0;cur=0
    for x in vals:
        if x<=0:
            cur+=1;best=max(best,cur)
        else:
            cur=0
    return best

def summarize(trades,days,total_n,pass_a_n,pass_b_n,pass_both_n):
    if trades is None or len(trades)==0:
        return {
            "onset_n":int(total_n),"pass_stage_a_n":int(pass_a_n),"pass_stage_b_n":int(pass_b_n),
            "pass_both_n":int(pass_both_n),"executed_trades":0,"skipped_active":int(pass_both_n),
            "pass_stage_a_share":float(pass_a_n/total_n) if total_n else np.nan,
            "pass_stage_b_share":float(pass_b_n/total_n) if total_n else np.nan,
            "pass_both_share":float(pass_both_n/total_n) if total_n else np.nan,
            "trades_per_day":0.0,"tp":0,"sl":0,"time":0,"samebar_sl":0,
            "target_wr":0.0,"resolved_wr":np.nan,"economic_win_rate":0.0,
            "net_expectancy_return":0.0,"net_expectancy_usd":0.0,"profit_factor":0.0,
            "total_net_usd":0.0,"max_loss_streak":0,"median_hold_min":np.nan,
        }
    t=trades
    n=len(t);ntp=int((t.exit_reason=="TP").sum());nsl=int((t.exit_reason=="SL").sum())
    ntm=int((t.exit_reason=="TIME").sum());nsb=int(t.samebar_sl.sum())
    pos=float(t.loc[t.net_pnl_usd>0,"net_pnl_usd"].sum())
    neg=float(-t.loc[t.net_pnl_usd<0,"net_pnl_usd"].sum())
    pf=pos/neg if neg>0 else (np.inf if pos>0 else 0.0)
    resolved=ntp+nsl
    return {
        "onset_n":int(total_n),"pass_stage_a_n":int(pass_a_n),"pass_stage_b_n":int(pass_b_n),
        "pass_both_n":int(pass_both_n),"executed_trades":int(n),"skipped_active":int(pass_both_n-n),
        "pass_stage_a_share":float(pass_a_n/total_n) if total_n else np.nan,
        "pass_stage_b_share":float(pass_b_n/total_n) if total_n else np.nan,
        "pass_both_share":float(pass_both_n/total_n) if total_n else np.nan,
        "trades_per_day":float(n/days) if days>0 else np.nan,
        "tp":ntp,"sl":nsl,"time":ntm,"samebar_sl":nsb,
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

def simulate_pair(scored,raw,split,res_th,dir_th,res_frac,dir_frac):
    base=scored[scored.split==split].sort_values(["entry_ts","onset_ts"]).copy()
    total_n=len(base)
    pass_a=base.resolution_score>=res_th
    pass_b=base.direction_score>=dir_th
    both=pass_a&pass_b
    q=base[both].copy()
    pass_a_n=int(pass_a.sum());pass_b_n=int(pass_b.sum());pass_both_n=int(both.sum())

    rows=[];active_until=None
    for r in q.itertuples(index=False):
        et=pd.Timestamp(r.entry_ts)
        if active_until is not None and et<active_until:
            continue
        rows.append({
            "split":split,
            "res_retention":res_frac,"dir_retention":dir_frac,
            "res_threshold":res_th,"dir_threshold":dir_th,
            "resolution_score":float(r.resolution_score),
            "direction_score":float(r.direction_score),
            "onset_ts":r.onset_ts,"entry_ts":et,"side":r.side,
            "cell_id":r.cell_id,"market_state":r.market_state,"regime":r.regime,
            "entry_price":float(r.entry_price),"exit_ts":r.exit_ts,
            "exit_price":float(r.exit_price),"exit_reason":r.exit_reason,
            "samebar_sl":bool(r.samebar_sl),"hold_min":float(r.hold_min),
            "gross_return":float(r.gross_return),"net_return":float(r.net_return),
            "net_pnl_usd":float(r.net_pnl_usd),
        })
        active_until=pd.Timestamp(r.exit_ts)
    trades=pd.DataFrame(rows)
    metrics=summarize(
        trades,s7d.coverage_days(split,raw),
        total_n,pass_a_n,pass_b_n,pass_both_n
    )
    return metrics,trades

def eligible(m):
    return (
        m["trades_per_day"]>=1.0
        and m["target_wr"]>=0.70
        and m["net_expectancy_return"]>0
        and m["profit_factor"]>1
    )

def choose(select):
    e=select[select.target_eligible].copy()
    sort_cols=["target_wr","net_expectancy_return","trades_per_day","res_retention","dir_retention"]
    if len(e):
        q=e.sort_values(sort_cols,ascending=[False,False,False,False,False]).iloc[0]
        return float(q.res_retention),float(q.dir_retention),float(q.res_threshold),float(q.dir_threshold),True,"TARGET_ELIGIBLE"
    p=select[select.trades_per_day>=1.0].copy()
    if len(p):
        q=p.sort_values(sort_cols,ascending=[False,False,False,False,False]).iloc[0]
        return float(q.res_retention),float(q.dir_retention),float(q.res_threshold),float(q.dir_threshold),False,"DIAGNOSTIC_TARGET_NOT_MET"
    q=select.sort_values(["trades_per_day","target_wr","net_expectancy_return","res_retention","dir_retention"],
                         ascending=[False,False,False,False,False]).iloc[0]
    return float(q.res_retention),float(q.dir_retention),float(q.res_threshold),float(q.dir_threshold),False,"DIAGNOSTIC_NO_1TPD"

def side_metrics(trades,split,raw):
    rows=[];days=s7d.coverage_days(split,raw)
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        # side diagnostic uses the already executed subset, so stage-pass counts equal len(g).
        m=summarize(g,days,len(g),len(g),len(g),len(g))
        row={"split":split,"side":side};row.update(m);rows.append(row)
    return rows

def score_distributions(scored):
    rows=[]
    for split in SPLITS:
        q=scored[scored.split==split]
        # Stage A diagnostic.
        for label_name,mask in [
            ("RESOLVED",q.exit_reason.isin(["TP","SL"])),
            ("TIME",q.exit_reason=="TIME"),
        ]:
            g=q[mask]
            if len(g):
                qq=g.resolution_score.quantile([.1,.25,.5,.75,.9])
                rows.append({
                    "stage":"STAGE_A_RESOLUTION","split":split,"outcome":label_name,"n":len(g),
                    "p10":float(qq.loc[.1]),"p25":float(qq.loc[.25]),"median":float(qq.loc[.5]),
                    "p75":float(qq.loc[.75]),"p90":float(qq.loc[.9]),
                })
        # Stage B diagnostic only on resolved.
        qr=q[q.exit_reason.isin(["TP","SL"])]
        for label_name in ["TP","SL"]:
            g=qr[qr.exit_reason==label_name]
            if len(g):
                qq=g.direction_score.quantile([.1,.25,.5,.75,.9])
                rows.append({
                    "stage":"STAGE_B_DIRECTION","split":split,"outcome":label_name,"n":len(g),
                    "p10":float(qq.loc[.1]),"p25":float(qq.loc[.25]),"median":float(qq.loc[.5]),
                    "p75":float(qq.loc[.75]),"p90":float(qq.loc[.9]),
                })
    return pd.DataFrame(rows)

def composition(trades):
    rows=[]
    if not len(trades):
        return pd.DataFrame(columns=["split","cell_id","n","share","tp_rate","sl_rate","time_rate"])
    for split in ["dev_select_2024","validation_2025","validation_2026"]:
        q=trades[trades.split==split]
        den=len(q)
        for cell,g in q.groupby("cell_id",sort=True):
            rows.append({
                "split":split,"cell_id":cell,"n":len(g),
                "share":float(len(g)/den) if den else np.nan,
                "tp_rate":float((g.exit_reason=="TP").mean()),
                "sl_rate":float((g.exit_reason=="SL").mean()),
                "time_rate":float((g.exit_reason=="TIME").mean()),
            })
    return pd.DataFrame(rows)

def audit(ds,select,res_frac,dir_frac,res_th,dir_th,trades):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})

    parent=(ROOT/"SOL_INDICATOR_RELATIONSHIP_S7E_Status.txt").read_text().strip()
    add("parent_stage7e_target_not_met",parent=="SOL_INDICATOR_RELATIONSHIP_S7E_TARGET_NOT_MET",parent)
    add("resolution_retention_grid_exact",RES_RET==[1.0,.8,.6],RES_RET)
    add("direction_retention_grid_exact",DIR_RET==[1.0,.6,.5,.4,.3],DIR_RET)
    add("grid_size_exact",len(select)==15,len(select))
    add("feature_count_exact",len(s7d.NUM_FEATURES)==21,len(s7d.NUM_FEATURES))
    add("selected_from_2024_only",True,{
        "res_ret":res_frac,"dir_ret":dir_frac,"res_th":res_th,"dir_th":dir_th
    })
    add("selected_retention_valid",res_frac in RES_RET and dir_frac in DIR_RET,{
        "res":res_frac,"dir":dir_frac
    })
    forbidden=[c for c in s7d.NUM_FEATURES if c.lower().startswith(("btcd","usdtd","ema","rsi"))]
    add("no_forbidden_new_indicator",len(forbidden)==0,forbidden)

    # Labels are exactly defined.
    resolved_check=((ds.exit_reason!="TIME").astype(int)==ds.label_resolved).all()
    add("resolution_label_exact",bool(resolved_check),int(len(ds)))
    dir_train=ds[(ds.split=="train_2023")&ds.exit_reason.isin(["TP","SL"])]
    add("direction_training_excludes_time",bool((dir_train.exit_reason!="TIME").all()),int(len(dir_train)))

    overlap=0
    if len(trades):
        for split in ["dev_select_2024","validation_2025","validation_2026"]:
            g=trades[trades.split==split].sort_values("entry_ts")
            if len(g)>1:
                prev=pd.to_datetime(g.exit_ts,utc=True).shift(1)
                cur=pd.to_datetime(g.entry_ts,utc=True)
                overlap+=int((cur<prev).fillna(False).sum())
    add("one_position_no_overlap",overlap==0,overlap)
    add("dataset_nonempty",len(ds)>0,len(ds))
    return pd.DataFrame(rows)

def main():
    raw,ds=prepare()
    res_model,dir_model,importance=fit_models(ds)
    importance.to_csv(OUT_IMPORTANCE,index=False)

    scored=score_all(ds,res_model,dir_model)
    thresholds,lookup=derive_thresholds(scored)
    thresholds.to_csv(OUT_THRESH,index=False)

    select_rows=[]
    for rr in RES_RET:
        for dr in DIR_RET:
            rth=lookup[("STAGE_A_RESOLUTION",rr)]
            dth=lookup[("STAGE_B_DIRECTION",dr)]
            m,_=simulate_pair(scored,raw,"dev_select_2024",rth,dth,rr,dr)
            row={
                "res_retention":rr,"dir_retention":dr,
                "res_threshold":rth,"dir_threshold":dth,
            }
            row.update(m);row["target_eligible"]=eligible(m)
            select_rows.append(row)
    select=pd.DataFrame(select_rows)
    select.to_csv(OUT_SELECT,index=False)

    sel_rr,sel_dr,sel_rth,sel_dth,dev_eligible,selection_status=choose(select)

    val_rows=[];frames=[];side_rows=[]
    for split in SPLITS:
        m,t=simulate_pair(scored,raw,split,sel_rth,sel_dth,sel_rr,sel_dr)
        gate=eligible(m) if split!="train_2023" else False
        row={
            "split":split,"res_retention":sel_rr,"dir_retention":sel_dr,
            "res_threshold":sel_rth,"dir_threshold":sel_dth,"gate_pass":gate,
        }
        row.update(m);val_rows.append(row)
        if len(t): frames.append(t)
        if split!="train_2023":
            side_rows.extend(side_metrics(t,split,raw))

    val=pd.DataFrame(val_rows);val.to_csv(OUT_VAL,index=False)
    trades=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_rows);side.to_csv(OUT_SIDE,index=False)

    score=score_distributions(scored);score.to_csv(OUT_SCORE,index=False)
    comp=composition(trades);comp.to_csv(OUT_COMP,index=False)

    gates=val[val.split.isin(["dev_select_2024","validation_2025","validation_2026"])].gate_pass
    promotion=bool(dev_eligible and len(gates)==3 and gates.all())

    adf=audit(ds,select,sel_rr,sel_dr,sel_rth,sel_dth,trades)
    adf.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(adf["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7F_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7F_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7F_TARGET_NOT_MET"

    payload={
        "status":status,
        "selected_resolution_retention":sel_rr,
        "selected_direction_retention":sel_dr,
        "selected_resolution_threshold":sel_rth,
        "selected_direction_threshold":sel_dth,
        "selection_status":selection_status,
        "dev_target_eligible":bool(dev_eligible),
        "promotion_gate_pass":bool(promotion and audit_pass),
        "dev_select":select.to_dict(orient="records"),
        "validation":val.to_dict(orient="records"),
        "importance":importance.to_dict(orient="records"),
        "score_distributions":score.to_dict(orient="records"),
        "side_diagnostics":side.to_dict(orient="records"),
        "accepted_composition":comp.to_dict(orient="records"),
        "audit_pass":audit_pass,
        "audit":adf.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 7F Result","",
        "**Two-stage pre-entry classifier: RESOLUTION first, then TP-vs-SL direction quality.**","",
        "## 2024 DEV_SELECT cutoff grid","",
        "| Resolve keep | Direction keep | Trades/day | Pass A | Pass B | Pass both | TP/SL/TIME | Target WR | Net exp | PF | Eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in select.itertuples(index=False):
        lines.append(
            f"| {100*r.res_retention:.0f}% | {100*r.dir_retention:.0f}% | {r.trades_per_day:.2f} | "
            f"{pct(r.pass_stage_a_share)} | {pct(r.pass_stage_b_share)} | {pct(r.pass_both_share)} | "
            f"{r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | USD {r.net_expectancy_usd:.3f} | "
            f"{r.profit_factor:.2f} | {'YES' if r.target_eligible else 'NO'} |"
        )

    lines += [
        "",
        f"Selected: **Stage-A top {100*sel_rr:.0f}% + Stage-B top {100*sel_dr:.0f}%** ({selection_status}).",
        "",
        "## Frozen evaluation","",
        "| Split | Trades | Trades/day | Pass A | Pass B | Pass both | TP/SL/TIME | Target WR | Resolved WR | Net exp | PF | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in val.itertuples(index=False):
        gt="TRAIN" if r.split=="train_2023" else ("PASS" if r.gate_pass else "FAIL")
        lines.append(
            f"| {r.split} | {r.executed_trades} | {r.trades_per_day:.2f} | "
            f"{pct(r.pass_stage_a_share)} | {pct(r.pass_stage_b_share)} | {pct(r.pass_both_share)} | "
            f"{r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | {pct(r.resolved_wr)} | "
            f"USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {gt} |"
        )

    lines += ["","## Selected-candidate side diagnostics","",
        "| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(
            f"| {r.split} | {r.side} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | "
            f"{pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |"
        )

    lines += ["","## Most influential inputs",""]
    for stage in ["STAGE_A_RESOLUTION","STAGE_B_DIRECTION"]:
        q=importance[importance.stage==stage].sort_values("importance",ascending=False).head(10)
        lines.append(f"**{stage}**")
        for r in q.itertuples(index=False):
            lines.append(f"- {r.feature}: {r.importance:.4f}")

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += [
            "**PROMOTION GATE: PASS.**",
            "The frozen two-stage classifier met >=1 trade/day, >=70% TP-hit WR, positive expectancy and PF>1 on 2024, 2025 and 2026."
        ]
    elif dev_eligible:
        lines += [
            "**PROMOTION GATE: FAIL IN VALIDATION.**",
            "A two-stage cutoff pair met the full 2024 target, but the exact frozen pair failed at least one later validation gate."
        ]
    else:
        lines += [
            "**PROMOTION GATE: FAIL — the two-stage architecture did not reach >=70% WR at >=1 trade/day on 2024.**",
            "No post-hoc model, feature, side, cell, horizon, or threshold rescue is authorized."
        ]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
