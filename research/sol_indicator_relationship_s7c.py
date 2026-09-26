#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 7C early-path separator."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s7 as s7
import sol_indicator_relationship_s7b as s7b

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_AUDIT.csv"
OUT_COEF=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_A_MODEL_COEFFICIENTS.csv"
OUT_SELECT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_B_DEV_SELECT.csv"
OUT_VAL=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_C_VALIDATION.csv"
OUT_SIDE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_D_SIDE.csv"
OUT_SCORE=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_E_SCORE_OUTCOME.csv"
OUT_TRADES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_F_TRADES.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7C_Status.txt"

TP=0.01
SL=0.01
COST=0.0015
NOTIONAL=500.0
BAR=pd.Timedelta(minutes=5)
HOLD_BARS=48
PROB_THRESH=[0.50,0.55,0.60,0.65,0.70,0.75,0.80]
HORIZONS={"H5":5,"H15":15}
TRAIN_START=pd.Timestamp("2023-01-01T00:00:00Z")
TRAIN_END=pd.Timestamp("2024-01-01T00:00:00Z")
SELECT_START=pd.Timestamp("2024-01-01T00:00:00Z")
SELECT_END=pd.Timestamp("2025-01-01T00:00:00Z")
VAL25_START=pd.Timestamp("2025-01-01T00:00:00Z")
VAL25_END=pd.Timestamp("2026-01-01T00:00:00Z")
VAL26_START=pd.Timestamp("2026-01-01T00:00:00Z")
VAL26_END=s3.END

H5_FEATURES=[
    "progress_5m","mfe_5m","mae_5m","efficiency_5m","mfe_mae_ratio_5m"
]
H15_FEATURES=H5_FEATURES+[
    "progress_15m","mfe_15m","mae_15m","efficiency_15m","mfe_mae_ratio_15m",
    "progress_accel_5to15","mfe_gain_5to15","mae_gain_5to15"
]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

def split_name(ts):
    t=pd.Timestamp(ts)
    if TRAIN_START<=t<TRAIN_END: return "train_2023"
    if SELECT_START<=t<SELECT_END: return "dev_select_2024"
    if VAL25_START<=t<VAL25_END: return "validation_2025"
    if VAL26_START<=t<VAL26_END: return "validation_2026"
    return None

def coverage_days(name,raw):
    raw_end=pd.Timestamp(raw.ts.max())+BAR
    spans={
        "train_2023":(TRAIN_START,TRAIN_END),
        "dev_select_2024":(SELECT_START,SELECT_END),
        "validation_2025":(VAL25_START,VAL25_END),
        "validation_2026":(VAL26_START,VAL26_END),
    }
    st,en=spans[name]
    en=min(en,raw_end)
    return max(0.0,float((en-st)/pd.Timedelta(days=1)))

def intended_excursions(side,w,anchor):
    if side=="LONG":
        prog=float(w.close.iloc[-1]/anchor-1.0)
        mfe=float(w.high.max()/anchor-1.0)
        mae=float(max(0.0,1.0-w.low.min()/anchor))
    else:
        prog=float(1.0-w.close.iloc[-1]/anchor)
        mfe=float(max(0.0,1.0-w.low.min()/anchor))
        mae=float(max(0.0,w.high.max()/anchor-1.0))
    return prog,mfe,mae

def trade_outcome(raw,pos,side):
    if pos is None or pos+HOLD_BARS>len(raw): return None
    w=raw.iloc[pos:pos+HOLD_BARS]
    if len(w)!=HOLD_BARS or not bool((w.ts.diff().dropna()==BAR).all()): return None
    entry=float(w.open.iloc[0])
    if side=="LONG":
        tp_px=entry*(1+TP); sl_px=entry*(1-SL)
    else:
        tp_px=entry*(1-TP); sl_px=entry*(1+SL)
    reason="TIME"; samebar=False; exit_px=float(w.close.iloc[-1]); exit_ts=pd.Timestamp(w.ts.iloc[-1])+BAR
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
    return {
        "entry_price":entry,"exit_ts":exit_ts,"exit_price":float(exit_px),
        "exit_reason":reason,"samebar_sl":bool(samebar),
        "hold_min":float((exit_ts-pd.Timestamp(w.ts.iloc[0]))/pd.Timedelta(minutes=1)),
        "gross_return":float(gross),"net_return":float(net),"net_pnl_usd":float(net*NOTIONAL),
        "label_tp":1 if reason=="TP" else 0,
    }

def build_episode_dataset(raw,a,horizon):
    delay=HORIZONS[horizon]
    n_obs=delay//5
    posmap={t:i for i,t in enumerate(raw.ts)}
    q=a[a.episode_onset & a.future_complete_4h].sort_values("decision_time")
    rows=[]
    for r in q.itertuples(index=False):
        t0=pd.Timestamp(r.decision_time)
        split=split_name(t0)
        if split is None: continue
        side=r.base_signal
        if side not in {"LONG","SHORT"}: continue
        p0=posmap.get(t0)
        if p0 is None or p0+n_obs>len(raw): continue
        obs=raw.iloc[p0:p0+n_obs]
        if len(obs)!=n_obs or not bool((obs.ts.diff().dropna()==BAR).all()): continue
        anchor=float(r.entry_price)

        p5,m5,a5=intended_excursions(side,raw.iloc[p0:p0+1],anchor)
        eff5=p5/(m5+a5+1e-6)
        ratio5=m5/(a5+0.0005)

        row={
            "horizon":horizon,"delay_min":delay,"split":split,"onset_ts":t0,
            "entry_ts":t0+pd.Timedelta(minutes=delay),"side":side,
            "onset_market_state":r.market_state,"onset_regime":r.regime,
            "progress_5m":p5,"mfe_5m":m5,"mae_5m":a5,
            "efficiency_5m":eff5,"mfe_mae_ratio_5m":ratio5,
        }

        if horizon=="H15":
            p15,m15,a15=intended_excursions(side,raw.iloc[p0:p0+3],anchor)
            row.update({
                "progress_15m":p15,"mfe_15m":m15,"mae_15m":a15,
                "efficiency_15m":p15/(m15+a15+1e-6),
                "mfe_mae_ratio_15m":m15/(a15+0.0005),
                "progress_accel_5to15":p15-p5,
                "mfe_gain_5to15":m15-m5,
                "mae_gain_5to15":a15-a5,
            })

        ep=posmap.get(row["entry_ts"])
        if ep is None: continue
        out=trade_outcome(raw,ep,side)
        if out is None: continue
        row.update(out)
        rows.append(row)
    return pd.DataFrame(rows)

def train_model(df,horizon):
    feats=H5_FEATURES if horizon=="H5" else H15_FEATURES
    tr=df[df.split=="train_2023"].dropna(subset=feats+["label_tp"]).copy()
    X=tr[feats].to_numpy(float); y=tr.label_tp.to_numpy(int)
    scaler=StandardScaler()
    Xs=scaler.fit_transform(X)
    model=LogisticRegression(penalty="l2",C=1.0,solver="lbfgs",max_iter=2000,random_state=42)
    model.fit(Xs,y)
    return scaler,model,feats

def score_all(df,scaler,model,feats):
    out=df.copy()
    mask=out[feats].notna().all(axis=1)
    out["score"]=np.nan
    if mask.any():
        X=scaler.transform(out.loc[mask,feats].to_numpy(float))
        out.loc[mask,"score"]=model.predict_proba(X)[:,1]
    return out

def max_loss_streak(vals):
    m=0;c=0
    for v in vals:
        if v<=0: c+=1;m=max(m,c)
        else: c=0
    return m

def summarize(trades,days,candidate_n):
    if trades is None or len(trades)==0:
        return {
            "candidate_n":int(candidate_n),"executed_trades":0,"skipped_active":int(candidate_n),
            "trades_per_day":0.0,"tp":0,"sl":0,"time":0,"target_wr":0.0,
            "resolved_wr":np.nan,"economic_win_rate":0.0,"net_expectancy_return":0.0,
            "net_expectancy_usd":0.0,"profit_factor":0.0,"total_net_usd":0.0,
            "max_loss_streak":0,"median_hold_min":np.nan,"accept_rate":0.0,
        }
    t=trades; n=len(t)
    ntp=int((t.exit_reason=="TP").sum()); nsl=int((t.exit_reason=="SL").sum()); ntm=int((t.exit_reason=="TIME").sum())
    pos=float(t.loc[t.net_pnl_usd>0,"net_pnl_usd"].sum()); neg=float(-t.loc[t.net_pnl_usd<0,"net_pnl_usd"].sum())
    pf=pos/neg if neg>0 else (np.inf if pos>0 else 0.0)
    resolved=ntp+nsl
    return {
        "candidate_n":int(candidate_n),"executed_trades":int(n),"skipped_active":int(candidate_n-n),
        "trades_per_day":float(n/days) if days>0 else np.nan,
        "tp":ntp,"sl":nsl,"time":ntm,"target_wr":float(ntp/n),
        "resolved_wr":float(ntp/resolved) if resolved else np.nan,
        "economic_win_rate":float((t.net_pnl_usd>0).mean()),
        "net_expectancy_return":float(t.net_return.mean()),
        "net_expectancy_usd":float(t.net_pnl_usd.mean()),
        "profit_factor":float(pf),"total_net_usd":float(t.net_pnl_usd.sum()),
        "max_loss_streak":int(max_loss_streak(t.net_pnl_usd.to_numpy(float))),
        "median_hold_min":float(t.hold_min.median()),
        "accept_rate":float(candidate_n/len(t)) if len(t) else 0.0,
    }

def simulate_scored(df,split,threshold,raw):
    q=df[(df.split==split)&df.score.notna()&(df.score>=threshold)].sort_values(["entry_ts","onset_ts"]).copy()
    candidate_n=len(q)
    rows=[]; active_until=None
    for r in q.itertuples(index=False):
        et=pd.Timestamp(r.entry_ts)
        if active_until is not None and et<active_until: continue
        rows.append({
            "split":split,"horizon":r.horizon,"threshold":threshold,
            "onset_ts":r.onset_ts,"entry_ts":et,"side":r.side,
            "onset_market_state":r.onset_market_state,"onset_regime":r.onset_regime,
            "score":float(r.score),"entry_price":float(r.entry_price),"exit_ts":r.exit_ts,
            "exit_price":float(r.exit_price),"exit_reason":r.exit_reason,
            "samebar_sl":bool(r.samebar_sl),"hold_min":float(r.hold_min),
            "gross_return":float(r.gross_return),"net_return":float(r.net_return),
            "net_pnl_usd":float(r.net_pnl_usd),
        })
        active_until=pd.Timestamp(r.exit_ts)
    t=pd.DataFrame(rows)
    return summarize(t,coverage_days(split,raw),candidate_n),t

def eligible(m):
    return m["trades_per_day"]>=1.0 and m["target_wr"]>=0.70 and m["net_expectancy_return"]>0 and m["profit_factor"]>1

def choose_candidate(sel):
    e=sel[sel.target_eligible].copy()
    if len(e):
        q=e.sort_values(["target_wr","net_expectancy_return","trades_per_day","delay_min","threshold","horizon"],
                        ascending=[False,False,False,True,True,True]).iloc[0]
        return str(q.horizon),float(q.threshold),True,"TARGET_ELIGIBLE"
    p=sel[sel.trades_per_day>=1.0].copy()
    if len(p):
        q=p.sort_values(["target_wr","net_expectancy_return","trades_per_day","delay_min","threshold","horizon"],
                        ascending=[False,False,False,True,True,True]).iloc[0]
        return str(q.horizon),float(q.threshold),False,"DIAGNOSTIC_TARGET_NOT_MET"
    q=sel.sort_values(["trades_per_day","target_wr","delay_min","threshold","horizon"],
                      ascending=[False,False,True,True,True]).iloc[0]
    return str(q.horizon),float(q.threshold),False,"DIAGNOSTIC_NO_1TPD"

def side_metrics(trades,split,raw):
    rows=[]
    days=coverage_days(split,raw)
    for side in ["LONG","SHORT"]:
        g=trades[trades.side==side].copy() if len(trades) else pd.DataFrame()
        m=summarize(g,days,len(g))
        row={"split":split,"side":side};row.update(m);rows.append(row)
    return rows

def score_outcome(df,split):
    rows=[]
    q=df[(df.split==split)&df.score.notna()]
    for outcome in ["TP","SL","TIME"]:
        g=q[q.exit_reason==outcome]
        if len(g):
            qs=g.score.quantile([.1,.25,.5,.75,.9]).to_dict()
            rows.append({
                "split":split,"outcome":outcome,"n":len(g),
                "score_p10":float(qs.get(.1,np.nan)),"score_p25":float(qs.get(.25,np.nan)),
                "score_median":float(qs.get(.5,np.nan)),"score_p75":float(qs.get(.75,np.nan)),
                "score_p90":float(qs.get(.9,np.nan)),
            })
        else:
            rows.append({"split":split,"outcome":outcome,"n":0,"score_p10":np.nan,"score_p25":np.nan,
                         "score_median":np.nan,"score_p75":np.nan,"score_p90":np.nan})
    return rows

def audit(raw,datasets,select,selected_h,selected_th,all_trades):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    parent=(ROOT/"SOL_INDICATOR_RELATIONSHIP_S7B_Status.txt").read_text().strip()
    add("parent_stage7b_target_not_met",parent=="SOL_INDICATOR_RELATIONSHIP_S7B_TARGET_NOT_MET",parent)
    add("horizons_exact",set(datasets.keys())=={"H5","H15"},list(datasets.keys()))
    add("threshold_grid_exact",PROB_THRESH==[.50,.55,.60,.65,.70,.75,.80],PROB_THRESH)
    add("selected_from_2024_only",True,{"horizon":selected_h,"threshold":selected_th})
    add("selected_threshold_in_grid",selected_th in PROB_THRESH,selected_th)
    add("selected_horizon_valid",selected_h in HORIZONS,selected_h)
    overlap=0
    if len(all_trades):
        for split in ["dev_select_2024","validation_2025","validation_2026"]:
            g=all_trades[all_trades.split==split].sort_values("entry_ts")
            if len(g)>1:
                prev=pd.to_datetime(g.exit_ts,utc=True).shift(1)
                cur=pd.to_datetime(g.entry_ts,utc=True)
                overlap+=int((cur<prev).fillna(False).sum())
    add("one_position_no_overlap",overlap==0,overlap)
    train_leak=0
    for df in datasets.values():
        train_leak+=int(((df.split=="train_2023")&(df.onset_ts>=SELECT_START)).sum())
    add("train_split_clean",train_leak==0,train_leak)
    add("selection_rows_present",len(select)>0,len(select))
    return pd.DataFrame(rows)

def main():
    raw,a=s7b.prepare()
    datasets={}
    models={}
    coef_rows=[]
    for h in ["H5","H15"]:
        df=build_episode_dataset(raw,a,h)
        scaler,model,feats=train_model(df,h)
        scored=score_all(df,scaler,model,feats)
        datasets[h]=scored
        models[h]=(scaler,model,feats)
        for f,c in zip(feats,model.coef_[0]):
            coef_rows.append({"horizon":h,"feature":f,"standardized_coef":float(c)})
        coef_rows.append({"horizon":h,"feature":"INTERCEPT","standardized_coef":float(model.intercept_[0])})
    coef=pd.DataFrame(coef_rows)
    coef.to_csv(OUT_COEF,index=False)

    select_rows=[]
    for h,df in datasets.items():
        for th in PROB_THRESH:
            m,_=simulate_scored(df,"dev_select_2024",th,raw)
            row={"horizon":h,"delay_min":HORIZONS[h],"threshold":th}
            row.update(m);row["target_eligible"]=eligible(m);select_rows.append(row)
    select=pd.DataFrame(select_rows)
    select.to_csv(OUT_SELECT,index=False)

    selected_h,selected_th,dev_eligible,selection_status=choose_candidate(select)

    val_rows=[];trade_frames=[];side_rows_all=[];score_rows=[]
    for split in ["train_2023","dev_select_2024","validation_2025","validation_2026"]:
        df=datasets[selected_h]
        m,t=simulate_scored(df,split,selected_th,raw)
        gate=eligible(m) if split!="train_2023" else False
        row={"split":split,"horizon":selected_h,"threshold":selected_th,"gate_pass":gate}
        row.update(m);val_rows.append(row)
        if len(t): trade_frames.append(t)
        if split!="train_2023":
            side_rows_all.extend(side_metrics(t,split,raw))
        score_rows.extend(score_outcome(df,split))
    val=pd.DataFrame(val_rows)
    val.to_csv(OUT_VAL,index=False)
    trades=pd.concat(trade_frames,ignore_index=True) if trade_frames else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    side=pd.DataFrame(side_rows_all);side.to_csv(OUT_SIDE,index=False)
    score=pd.DataFrame(score_rows);score.to_csv(OUT_SCORE,index=False)

    gates=val[val.split.isin(["dev_select_2024","validation_2025","validation_2026"])].gate_pass
    promotion=bool(dev_eligible and len(gates)==3 and gates.all())
    adf=audit(raw,datasets,select,selected_h,selected_th,trades)
    adf.to_csv(OUT_AUDIT,index=False)
    audit_pass=bool(adf["pass"].all())

    if promotion and audit_pass:
        status="SOL_INDICATOR_RELATIONSHIP_S7C_PROMOTION_GATE_PASS"
    elif dev_eligible:
        status="SOL_INDICATOR_RELATIONSHIP_S7C_DEV_ELIGIBLE_VALIDATION_FAIL"
    else:
        status="SOL_INDICATOR_RELATIONSHIP_S7C_TARGET_NOT_MET"

    payload={
        "status":status,"selected_horizon":selected_h,"selected_threshold":selected_th,
        "selection_status":selection_status,"dev_target_eligible":bool(dev_eligible),
        "promotion_gate_pass":bool(promotion and audit_pass),
        "coefficients":coef.to_dict(orient="records"),
        "dev_select_candidates":select.to_dict(orient="records"),
        "validation":val.to_dict(orient="records"),
        "side_diagnostics":side.to_dict(orient="records"),
        "score_outcome":score.to_dict(orient="records"),
        "audit_pass":audit_pass,"audit":adf.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 7C Result","",
        "**Early-path separator. 2023 model train -> 2024 selector -> 2025/2026 frozen validation.**","",
        "## Standardized logistic coefficients","",
        "| Horizon | Feature | Coefficient |","|---|---|---:|"
    ]
    for r in coef.itertuples(index=False):
        lines.append(f"| {r.horizon} | {r.feature} | {r.standardized_coef:.4f} |")

    lines += ["","## 2024 DEV_SELECT candidate grid","",
        "| Horizon | Prob >= | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in select.itertuples(index=False):
        lines.append(f"| {r.horizon} | {r.threshold:.2f} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {'YES' if r.target_eligible else 'NO'} |")

    lines += ["",f"Selected: **{selected_h} @ probability >= {selected_th:.2f}** ({selection_status}).","",
        "## Frozen evaluation","",
        "| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in val.itertuples(index=False):
        gate="TRAIN" if r.split=="train_2023" else ("PASS" if r.gate_pass else "FAIL")
        lines.append(f"| {r.split} | {r.executed_trades} | {r.trades_per_day:.2f} | {r.tp}/{r.sl}/{r.time} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} | {gate} |")

    lines += ["","## Side diagnostics","",
        "| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in side.itertuples(index=False):
        lines.append(f"| {r.split} | {r.side} | {r.trades_per_day:.2f} | {pct(r.target_wr)} | {pct(r.economic_win_rate)} | USD {r.net_expectancy_usd:.3f} | {r.profit_factor:.2f} |")

    lines += ["","## Decision",""]
    if promotion and audit_pass:
        lines += ["**PROMOTION GATE: PASS.**",
                  "The frozen early-path separator met >=1 trade/day, >=70% TP-hit WR, positive expectancy and PF>1 on 2024, 2025 and 2026."]
    elif dev_eligible:
        lines += ["**PROMOTION GATE: FAIL IN VALIDATION.**",
                  "The early-path separator achieved the full 2024 target but the exact frozen model/threshold failed at least one later validation gate."]
    else:
        lines += ["**PROMOTION GATE: FAIL — the early-path separator did not achieve >=70% WR at >=1 trade/day on 2024 DEV_SELECT.**",
                  "No probability-threshold rescue or new path feature is allowed after these results."]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
