#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7D within-state separator."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s7 as s7
import sol_indicator_relationship_s7b as s7b
import sol_indicator_relationship_s7c as s7c

ROOT=Path(__file__).resolve().parent.parent

OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_AUDIT.csv"
OUT_BASELINE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_A_CELL_BASELINE.csv"
OUT_IMPORTANCE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_B_MODEL_IMPORTANCE.csv"
OUT_THRESH=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_C_TRAIN_THRESHOLDS.csv"
OUT_SELECT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_D_DEV_SELECT.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_E_VALIDATION.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_F_SIDE.csv"
OUT_SCORE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_G_SCORE_OUTCOME.csv"
OUT_COMP=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_H_ACCEPTED_COMPOSITION.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_I_TRADES.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7D_Status.txt"

TP=0.01
SL=0.01
COST=0.0015
NOTIONAL=500.0
BAR=pd.Timedelta(minutes=5)

TRAIN_START=pd.Timestamp("2023-01-01T00:00:00Z")
TRAIN_END=pd.Timestamp("2024-01-01T00:00:00Z")
SELECT_START=pd.Timestamp("2024-01-01T00:00:00Z")
SELECT_END=pd.Timestamp("2025-01-01T00:00:00Z")
VAL25_START=pd.Timestamp("2025-01-01T00:00:00Z")
VAL25_END=pd.Timestamp("2026-01-01T00:00:00Z")
VAL26_START=pd.Timestamp("2026-01-01T00:00:00Z")
VAL26_END=s3.END

NUM_FEATURES=[
    "oi_chg_15m","oi_chg_1h","oi_chg_4h",
    "taker_imb_15m","taker_imb_1h","taker_imb_change_1h",
    "quotevol_z_24h","quotevol_ratio_1h","trades_ratio_1h",
    "loc_24h","dist_high_24h","dist_low_24h",
    "breakout_up_24h","breakout_down_24h","impulse5m_prev",
    "rv8","rv24","atr14_pct","dist_high8","accel4v12","close_loc",
]
CAT_FEATURES=["cell_id"]
RETENTION=[1.00,0.80,0.60,0.50,0.40,0.30]
MODELS=["M1_LOGIT","M2_RF"]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def split_name(ts):
    t=pd.Timestamp(ts)
    if TRAIN_START<=t<TRAIN_END: return "train_2023"
    if SELECT_START<=t<SELECT_END: return "dev_select_2024"
    if VAL25_START<=t<VAL25_END: return "validation_2025"
    if VAL26_START<=t<VAL26_END: return "validation_2026"
    return None

def coverage_days(split,raw):
    raw_end=pd.Timestamp(raw.ts.max())+BAR
    spans={
        "train_2023":(TRAIN_START,TRAIN_END),
        "dev_select_2024":(SELECT_START,SELECT_END),
        "validation_2025":(VAL25_START,VAL25_END),
        "validation_2026":(VAL26_START,VAL26_END),
    }
    st,en=spans[split]
    en=min(en,raw_end)
    return max(0.0,float((en-st)/pd.Timedelta(days=1)))

def prepare():
    raw,a=s7b.prepare()
    return raw.sort_values("ts").reset_index(drop=True),a.sort_values("decision_time").reset_index(drop=True)

def build_dataset(raw,a):
    posmap={t:i for i,t in enumerate(raw.ts)}
    q=a[a.episode_onset&a.future_complete_4h].sort_values("decision_time")
    rows=[]
    for r in q.itertuples(index=False):
        t=pd.Timestamp(r.decision_time)
        split=split_name(t)
        if split is None: continue
        side=r.base_signal
        if side not in {"LONG","SHORT"}: continue
        p=posmap.get(t)
        if p is None: continue
        out=s7c.trade_outcome(raw,p,side)
        if out is None: continue
        row={
            "split":split,"onset_ts":t,"entry_ts":t,"side":side,
            "market_state":r.market_state,"regime":r.regime,
            "cell_id":f"{r.regime}|{r.market_state}|{side}",
        }
        for f in NUM_FEATURES:
            row[f]=getattr(r,f)
        row.update(out)
        rows.append(row)
    return pd.DataFrame(rows)

def baseline_cells(df):
    rows=[]
    for split in ["train_2023","dev_select_2024","validation_2025","validation_2026"]:
        q=df[df.split==split]
        for cell,g in q.groupby("cell_id",sort=True):
            n=len(g)
            rows.append({
                "split":split,"cell_id":cell,"n":n,
                "tp_rate":float((g.exit_reason=="TP").mean()) if n else np.nan,
                "sl_rate":float((g.exit_reason=="SL").mean()) if n else np.nan,
                "time_rate":float((g.exit_reason=="TIME").mean()) if n else np.nan,
                "long_share":float((g.side=="LONG").mean()) if n else np.nan,
            })
    return pd.DataFrame(rows)

def make_preprocessor(scale_numeric):
    num_steps=[("impute",SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scale",StandardScaler()))
    num_pipe=Pipeline(num_steps)
    cat_pipe=Pipeline([
        ("impute",SimpleImputer(strategy="most_frequent")),
        ("onehot",OneHotEncoder(handle_unknown="ignore",sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num",num_pipe,NUM_FEATURES),
        ("cat",cat_pipe,CAT_FEATURES),
    ],remainder="drop")

def build_model(name):
    if name=="M1_LOGIT":
        return Pipeline([
            ("prep",make_preprocessor(True)),
            ("model",LogisticRegression(
                penalty="l2",C=1.0,solver="lbfgs",max_iter=3000,random_state=42
            )),
        ])
    if name=="M2_RF":
        return Pipeline([
            ("prep",make_preprocessor(False)),
            ("model",RandomForestClassifier(
                n_estimators=400,max_depth=4,min_samples_leaf=40,
                max_features="sqrt",class_weight=None,random_state=42,n_jobs=-1
            )),
        ])
    raise ValueError(name)

def feature_names(pipe):
    prep=pipe.named_steps["prep"]
    return list(prep.get_feature_names_out())

def fit_models(df):
    tr=df[df.split=="train_2023"].copy()
    X=tr[NUM_FEATURES+CAT_FEATURES]
    y=tr.label_tp.to_numpy(int)
    fitted={}
    imp_rows=[]
    for name in MODELS:
        model=build_model(name)
        model.fit(X,y)
        fitted[name]=model
        names=feature_names(model)
        est=model.named_steps["model"]
        if name=="M1_LOGIT":
            vals=est.coef_[0]
            metric="standardized_coef"
        else:
            vals=est.feature_importances_
            metric="feature_importance"
        for f,v in zip(names,vals):
            imp_rows.append({"model":name,"feature":f,"metric":metric,"value":float(v)})
        if name=="M1_LOGIT":
            imp_rows.append({"model":name,"feature":"INTERCEPT","metric":"intercept","value":float(est.intercept_[0])})
    return fitted,pd.DataFrame(imp_rows)

def score_models(df,fitted):
    out={}
    X=df[NUM_FEATURES+CAT_FEATURES]
    for name,model in fitted.items():
        z=df.copy()
        z["score"]=model.predict_proba(X)[:,1]
        z["model"]=name
        out[name]=z
    return out

def train_thresholds(scored):
    rows=[]
    lookup={}
    for name,df in scored.items():
        s=df.loc[df.split=="train_2023","score"].dropna().to_numpy(float)
        for frac in RETENTION:
            th=-np.inf if frac>=1 else float(np.quantile(s,1-frac,method="linear"))
            rows.append({"model":name,"retention_fraction":frac,"score_threshold":th,
                         "train_score_n":len(s)})
            lookup[(name,frac)]=th
    return pd.DataFrame(rows),lookup

def simulate_scored(df,split,threshold,raw,model,retention):
    base=df[df.split==split].copy()
    q=base[base.score>=threshold].sort_values(["entry_ts","onset_ts"])
    candidate_n=len(q)
    rows=[];active_until=None
    for r in q.itertuples(index=False):
        et=pd.Timestamp(r.entry_ts)
        if active_until is not None and et<active_until:
            continue
        rows.append({
            "split":split,"model":model,"retention_fraction":retention,
            "score_threshold":threshold,"score":float(r.score),
            "onset_ts":r.onset_ts,"entry_ts":et,"side":r.side,
            "cell_id":r.cell_id,"market_state":r.market_state,"regime":r.regime,
            "entry_price":float(r.entry_price),"exit_ts":r.exit_ts,
            "exit_price":float(r.exit_price),"exit_reason":r.exit_reason,
            "samebar_sl":bool(r.samebar_sl),"hold_min":float(r.hold_min),
            "gross_return":float(r.gross_return),"net_return":float(r.net_return),
            "net_pnl_usd":float(r.net_pnl_usd),
        })
        active_until=pd.Timestamp(r.exit_ts)
    t=pd.DataFrame(rows)
    m=s7.summarize_trades(t,coverage_days(split,raw),candidate_n)
    m["candidate_accept_fraction"]=float(candidate_n/len(base)) if len(base) else np.nan
    return m,t

def eligible(m):
    return m["trades_per_day"]>=1.0 and m["target_wr"]>=0.70 and m["net_expectancy_return"]>0 and m["profit_factor"]>1

def choose(select):
    e=select[select.target_eligible].copy()
    if len(e):
        q=e.sort_values(
            ["target_wr","net_expectancy_return","trades_per_day","retention_fraction","model"],
            ascending=[False,False,False,False,True]
        ).iloc[0]
        return str(q.model),float(q.retention_fraction),float(q.score_threshold),True,"TARGET_ELIGIBLE"
    p=select[select.trades_per_day>=1.0].copy()
    if len(p):
        q=p.sort_values(
            ["target_wr","net_expectancy_return","trades_per_day","retention_fraction","model"],
            ascending=[False,False,False,False,True]
        ).iloc[0]
        return str(q.model),float(q.retention_fraction),float(q.score_threshold),False,"DIAGNOSTIC_TARGET_NOT_MET"
    q=select.sort_values(
        ["trades_per_day","target_wr","net_expectancy_return","retention_fraction","model"],
        ascending=[False,False,False,False,True]
    ).iloc[0]
    return str(q.model),float(q.retention_fraction),float(q.score_threshold),False,"DIAGNOSTIC_NO_1TPD"

def side_rows(trades,split,raw):
    rows=[];days=coverage_days(split,raw)
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        m=s7.summarize_trades(g,days,len(g))
        row={"split":split,"side":side};row.update(m);rows.append(row)
    return rows

def score_outcome(df,model):
    rows=[]
    for split in ["train_2023","dev_select_2024","validation_2025","validation_2026"]:
        q=df[df.split==split]
        for outcome in ["TP","SL","TIME"]:
            g=q[q.exit_reason==outcome]
            if len(g):
                qq=g.score.quantile([.1,.25,.5,.75,.9])
                rows.append({
                    "model":model,"split":split,"outcome":outcome,"n":len(g),
                    "p10":float(qq.loc[.1]),"p25":float(qq.loc[.25]),
                    "median":float(qq.loc[.5]),"p75":float(qq.loc[.75]),"p90":float(qq.loc[.9]),
                })
            else:
                rows.append({"model":model,"split":split,"outcome":outcome,"n":0,
                             "p10":np.nan,"p25":np.nan,"median":np.nan,"p75":np.nan,"p90":np.nan})
    return rows

def composition(trades):
    rows=[]
    if not len(trades): return pd.DataFrame()
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

def audit(df,select,model,frac,th,trades):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    parent=(ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_Status.txt").read_text().strip()
    add("parent_stage7c_target_not_met",parent=="SOL_INDICATOR_RELATIONSHIP_S7C_TARGET_NOT_MET",parent)
    add("model_set_exact",MODELS==["M1_LOGIT","M2_RF"],MODELS)
    add("retention_grid_exact",RETENTION==[1.0,.8,.6,.5,.4,.3],RETENTION)
    add("feature_count_exact",len(NUM_FEATURES)==21,len(NUM_FEATURES))
    add("selected_from_2024_only",True,{"model":model,"retention":frac,"threshold":th})
    add("selected_retention_in_grid",frac in RETENTION,frac)
    add("selected_threshold_finite_or_all",np.isfinite(th) or frac==1.0,th)
    forbidden=[c for c in NUM_FEATURES if c.lower().startswith(("btcd","usdtd","ema","rsi"))]
    add("no_forbidden_new_indicator",len(forbidden)==0,forbidden)
    overlap=0
    if len(trades):
        for split in ["dev_select_2024","validation_2025","validation_2026"]:
            g=trades[trades.split==split].sort_values("entry_ts")
            if len(g)>1:
                prev=pd.to_datetime(g.exit_ts,utc=True).shift(1)
                cur=pd.to_datetime(g.entry_ts,utc=True)
                overlap+=int((cur<prev).fillna(False).sum())
    add("one_position_no_overlap",overlap==0,overlap)
    add("train_2023_present",int((df.split=="train_2023").sum())>0,int((df.split=="train_2023").sum()))
    add("dev_select_rows_present",len(select)>0,len(select))
    return pd.DataFrame(rows)

def main():
    raw,a=prepare()
    ds=build_dataset(raw,a)
    baseline=baseline_cells(ds)
    baseline.to_csv(OUT_BASELINE,index=False)

    fitted,importance=fit_models(ds)
    importance.to_csv(OUT_IMPORTANCE,index=False)
    scored=score_models(ds,fitted)
    thresholds,lookup=train_thresholds(scored)
    thresholds.to_csv(OUT_THRESH,index=False)

    select_rows=[]
    for model in MODELS:
        for frac in RETENTION:
            th=lookup[(model,frac)]
            m,_=simulate_scored(scored[model],"dev_select_2024",th,raw,model,frac)
            row={"model":model,"retention_fraction":frac,"score_threshold":th}
            row.update(m);row["target_eligible"]=eligible(m);select_rows.append(row)
    select=pd.DataFrame(select_rows)
    select.to_csv(OUT_SELECT,index=False)

    selected_model,selected_frac,selected_th,dev_eligible,selection_status=choose(select)

    val_rows=[];all_trades=[];side_all=[]
    selected_df=scored[selected_model]
    for split in ["train_2023","dev_select_2024","validation_2025","validation_2026"]:
        m,t=simulate_scored(selected_df,split,selected_th,raw,selected_model,selected_frac)
        gate=eligible(m) if split!="train_2023" else False
        row={"split":split,"model":selected_model,"retention_fraction":selected_frac,
             "score_threshold":selected_th,"gate_pass":gate}
        row.update(m);val_rows.append(row)
        if len(t): all_trades.append(t)
        if split!="train_2023": side_all.extend(side_rows(t,split,raw))
    val=pd.DataFrame(val_rows)
    val.to_csv(OUT_VAL,index=False)
    trades=pd.concat(all_trades,ignore_index=True) if all_trades else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_all);side.to_csv(OUT_SIDE,index=False)

    score_rows=[]
    for model in MODELS:
        score_rows.extend(score_outcome(scored[model],model))
    score=pd.DataFrame(score_rows);score.to_csv(OUT_SCORE,index=False)
    comp=composition(trades);comp.to_csv(OUT_COMP,index=False)

    gates=val[val.split.isin(["dev_select_2024","validation_2025","validation_2026"])].gate_pass
    promotion=bool(dev_eligible and len(gates)==3 and gates.all())
    adf=audit(ds,select,selected_model,selected_frac,selected_th,trades)
    adf.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(adf["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7D_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7D_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7D_TARGET_NOT_MET"

    payload={
        "status":status,"selected_model":selected_model,"selected_retention":selected_frac,
        "selected_threshold":selected_th,"selection_status":selection_status,
        "dev_target_eligible":bool(dev_eligible),"promotion_gate_pass":bool(promotion and audit_pass),
        "dev_select":select.to_dict(orient="records"),"validation":val.to_dict(orient="records"),
        "importance":importance.to_dict(orient="records"),"side_diagnostics":side.to_dict(orient="records"),
        "accepted_composition":comp.to_dict(orient="records"),"audit_pass":audit_pass,
        "audit":adf.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 7D Result","",
        "**Within-state pre-entry separator. 2023 train -> 2024 select -> 2025/2026 validation.**","",
        "## Baseline R3 cell outcomes","",
        "| Split | Cell | N | TP | SL | TIME |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in baseline.itertuples(index=False):
        lines.append(f"| {r.split} | {r.cell_id} | {r.n} | {pct(r.tp_rate)} | {pct(r.sl_rate)} | {pct(r.time_rate)} |")

    lines += ["","## 2024 DEV_SELECT model × retention grid","",
        "| Model | Top retained | Fixed score >= | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in select.itertuples(index=False):
        thtxt="ALL" if not np.isfinite(r.score_threshold) else f"{r.score_threshold:.4f}"
        lines.append(f"| {r.model} | {100*r.retention_fraction:.0f}% | {thtxt} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {'YES' if r.target_eligible else 'NO'} |")

    thtxt="ALL" if not np.isfinite(selected_th) else f"{selected_th:.4f}"
    lines += ["",f"Selected: **{selected_model}, top-{100*selected_frac:.0f}% train-score threshold ({thtxt})** ({selection_status}).","",
        "## Frozen evaluation","",
        "| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in val.itertuples(index=False):
        gate="TRAIN" if r.split=="train_2023" else ("PASS" if r.gate_pass else "FAIL")
        lines.append(f"| {r.split} | {r.executed_trades} | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {gate} |")

    lines += ["","## Selected-candidate side diagnostics","",
        "| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(f"| {r.split} | {r.side} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |")

    lines += ["","## Most influential fitted inputs",""]
    for model in MODELS:
        q=importance[(importance.model==model)&(importance.feature!="INTERCEPT")].copy()
        q["abs_value"]=q.value.abs()
        q=q.sort_values("abs_value",ascending=False).head(8)
        lines.append(f"**{model}**")
        for r in q.itertuples(index=False):
            lines.append(f"- {r.feature}: {r.value:.4f}")

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += ["**PROMOTION GATE: PASS.**",
                  "The frozen within-state separator met >=1 trade/day, >=70% TP-hit WR, positive expectancy and PF>1 on 2024, 2025 and 2026."]
    elif dev_eligible:
        lines += ["**PROMOTION GATE: FAIL IN VALIDATION.**",
                  "A 2024 within-state separator met the full target but its exact frozen model/cutoff failed at least one later validation gate."]
    else:
        lines += ["**PROMOTION GATE: FAIL — within-state magnitude information did not achieve >=70% WR at >=1 trade/day on 2024.**",
                  "No feature deletion, cell deletion, new model or cutoff rescue is allowed after these results."]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
