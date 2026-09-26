#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
IN_SCORES=ROOT/"SOL_REGIME_PHASE_STAGE6C_Scores_DEV.csv"
IN_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6C_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_PHASE_STAGE6D_Result.md"
OUT_LABELS=ROOT/"SOL_REGIME_PHASE_STAGE6D_Labels_DEV.csv"
OUT_PHASE=ROOT/"SOL_REGIME_PHASE_STAGE6D_PhaseSummary.csv"
OUT_BLOCKS=ROOT/"SOL_REGIME_PHASE_STAGE6D_Blocks.csv"
OUT_AUC=ROOT/"SOL_REGIME_PHASE_STAGE6D_AUC.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_PHASE_STAGE6D_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_PHASE_STAGE6D_Status.txt"

SYMBOL="SOLUSDT"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
START=pd.Timestamp("2023-01-01T00:00:00Z")
START24=pd.Timestamp("2024-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")
HORIZONS=(6,12,24)

PHASES=["EarlyExpansion","HealthyContinuation","MatureTrend","Exhaustion","Transition"]
CONT_GROUP={"EarlyExpansion","HealthyContinuation"}
RISK_GROUP={"Exhaustion","Transition"}

def month_urls():
    cur=START
    out=[]
    while cur<END:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out

def fetch_one(url):
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-stage6d/1.0"})
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"no csv in {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,header=None,usecols=[0,1,2,3,4,5],
                names=["ts","open","high","low","close","volume"]
            )

def load5():
    frames=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs=[ex.submit(fetch_one,u) for u in month_urls()]
        for fut in as_completed(futs):
            frames.append(fut.result())
    x=pd.concat(frames,ignore_index=True)
    t=pd.to_numeric(x.ts,errors="coerce")
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x["ts"]=pd.to_datetime(t,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=START)&(x.ts<END)].set_index("ts")
    expected=int((END-START)/pd.Timedelta(minutes=5))
    return x,len(x)/expected

def block(ts):
    if ts<pd.Timestamp("2023-07-01",tz="UTC"): return "2023-H1"
    if ts<pd.Timestamp("2024-01-01",tz="UTC"): return "2023-H2"
    if ts<pd.Timestamp("2024-07-01",tz="UTC"): return "2024-H1"
    return "2024-H2"

def future_label(x5,ts,h,side):
    end=ts+pd.Timedelta(hours=h)
    if ts<START or end>=END:
        return None
    try:
        i0=x5.index.get_loc(ts)
        i1=x5.index.get_loc(end)
    except KeyError:
        return None
    if not isinstance(i0,(int,np.integer)) or not isinstance(i1,(int,np.integer)):
        return None
    if i1-i0 != h*12:
        return None

    ep=float(x5.iloc[i0].open)
    w=x5.iloc[i0:i1]
    highs=w.high.to_numpy(float)
    lows=w.low.to_numpy(float)
    up=ep*1.01
    dn=ep*0.99
    upm=highs>=up
    dnm=lows<=dn
    anym=upm|dnm

    first="UNRESOLVED"
    if anym.any():
        k=int(np.argmax(anym))
        if upm[k] and dnm[k]:
            first="AMBIGUOUS"
        elif upm[k]:
            first="POS_FIRST"
        else:
            first="NEG_FIRST"

    sign=1.0 if side=="BULL" else -1.0
    rawret=float(x5.iloc[i1].open)/ep-1.0
    aligned_hit=np.nan
    if first in ("POS_FIRST","NEG_FIRST"):
        aligned_hit=(first=="POS_FIRST") if side=="BULL" else (first=="NEG_FIRST")

    if side=="BULL":
        mfe=float(np.max(highs))/ep-1.0
        mae=1.0-float(np.min(lows))/ep
    else:
        mfe=1.0-float(np.min(lows))/ep
        mae=float(np.max(highs))/ep-1.0

    return {
        f"firsthit_{h}h":first,
        f"aligned_hit_{h}h":aligned_hit,
        f"aligned_ret_{h}h":rawret*sign,
        f"aligned_mfe_{h}h":mfe,
        f"aligned_mae_{h}h":mae,
    }

def auc_rank(y,score):
    y=np.asarray(y,dtype=int)
    s=pd.Series(score).astype(float)
    m=np.isfinite(s.to_numpy()) & np.isfinite(y)
    y=y[m]
    s=s[m]
    n1=int((y==1).sum())
    n0=int((y==0).sum())
    if n1==0 or n0==0:
        return np.nan
    ranks=s.rank(method="average").to_numpy(float)
    sum_r1=float(ranks[y==1].sum())
    u1=sum_r1-n1*(n1+1)/2.0
    return u1/(n1*n0)

def phase_stats(q,phase):
    z=q[q.selected_phase==phase]
    e=z[z.firsthit_24h.notna()]
    r=e[e.firsthit_24h.isin(["POS_FIRST","NEG_FIRST"])]
    return {
        "phase":phase,
        "rows":len(z),
        "eligible24":len(e),
        "resolved24":len(r),
        "resolved_rate":len(r)/len(e) if len(e) else np.nan,
        "aligned_hit24":float(pd.to_numeric(r.aligned_hit_24h,errors="coerce").mean()) if len(r) else np.nan,
        "median_ret24":float(pd.to_numeric(e.aligned_ret_24h,errors="coerce").median()) if len(e) else np.nan,
        "median_mfe24":float(pd.to_numeric(e.aligned_mfe_24h,errors="coerce").median()) if len(e) else np.nan,
        "median_mae24":float(pd.to_numeric(e.aligned_mae_24h,errors="coerce").median()) if len(e) else np.nan,
        "ambiguous_share":float((e.firsthit_24h=="AMBIGUOUS").mean()) if len(e) else np.nan,
    }

def group_stats(q,phases):
    z=q[q.selected_phase.isin(phases)]
    e=z[z.firsthit_24h.notna()]
    r=e[e.firsthit_24h.isin(["POS_FIRST","NEG_FIRST"])]
    return {
        "rows":len(z),
        "eligible24":len(e),
        "resolved24":len(r),
        "aligned_hit24":float(pd.to_numeric(r.aligned_hit_24h,errors="coerce").mean()) if len(r) else np.nan,
        "median_ret24":float(pd.to_numeric(e.aligned_ret_24h,errors="coerce").median()) if len(e) else np.nan,
    }

def main():
    stage6c="SOL_REGIME_PHASE_STAGE6C_SCORING_VALID" in (IN_STATUS.read_text() if IN_STATUS.exists() else "")
    sc=pd.read_csv(IN_SCORES,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    sc=sc[(sc.index>=START)&(sc.index<END)].copy()

    bull_dir=pd.to_numeric(sc.bull_DirectionEvidence,errors="coerce")
    bear_dir=pd.to_numeric(sc.bear_DirectionEvidence,errors="coerce")
    side=np.where(bull_dir>bear_dir,"BULL",np.where(bear_dir>bull_dir,"BEAR","UNAVAILABLE"))
    sc["selected_side"]=side

    phase=[]
    cont=[]
    rem=[]
    rev=[]
    early=[]
    healthy=[]
    mature=[]
    exhaust=[]
    trans=[]
    for _,r in sc.iterrows():
        s=r.selected_side
        if s=="BULL":
            p="bull_"
        elif s=="BEAR":
            p="bear_"
        else:
            phase.append("UNAVAILABLE")
            for arr in (cont,rem,rev,early,healthy,mature,exhaust,trans):
                arr.append(np.nan)
            continue
        phase.append(r[p+"provisional_phase"])
        cont.append(r[p+"ContinuationQualityScore"])
        rem.append(r[p+"RemainingEnergyScore"])
        rev.append(r[p+"ReversalRiskScore"])
        early.append(r[p+"EarlyExpansionScore"])
        healthy.append(r[p+"HealthyContinuationScore"])
        mature.append(r[p+"MatureTrendScore"])
        exhaust.append(r[p+"ExhaustionScore"])
        trans.append(r[p+"TransitionScore"])

    sc["selected_phase"]=phase
    sc["selected_ContinuationQualityScore"]=cont
    sc["selected_RemainingEnergyScore"]=rem
    sc["selected_ReversalRiskScore"]=rev
    sc["selected_EarlyExpansionScore"]=early
    sc["selected_HealthyContinuationScore"]=healthy
    sc["selected_MatureTrendScore"]=mature
    sc["selected_ExhaustionScore"]=exhaust
    sc["selected_TransitionScore"]=trans
    sc["direction_margin"]=(bull_dir-bear_dir).abs()

    x5,coverage=load5()

    rows=[]
    for idx,r in sc.iterrows():
        if r.selected_side not in ("BULL","BEAR"):
            continue
        rec={
            "bar_open_ts":idx,
            "decision_time":r.decision_time,
            "selected_side":r.selected_side,
            "selected_phase":r.selected_phase,
            "direction_margin":float(r.direction_margin),
            "ContinuationQualityScore":float(r.selected_ContinuationQualityScore),
            "RemainingEnergyScore":float(r.selected_RemainingEnergyScore),
            "ReversalRiskScore":float(r.selected_ReversalRiskScore),
            "EarlyExpansionScore":float(r.selected_EarlyExpansionScore),
            "HealthyContinuationScore":float(r.selected_HealthyContinuationScore),
            "MatureTrendScore":float(r.selected_MatureTrendScore),
            "ExhaustionScore":float(r.selected_ExhaustionScore),
            "TransitionScore":float(r.selected_TransitionScore),
            "block":block(r.decision_time),
            "year":r.decision_time.year,
        }
        for h in HORIZONS:
            lab=future_label(x5,r.decision_time,h,r.selected_side)
            if lab:
                rec.update(lab)
            else:
                rec.update({
                    f"firsthit_{h}h":np.nan,
                    f"aligned_hit_{h}h":np.nan,
                    f"aligned_ret_{h}h":np.nan,
                    f"aligned_mfe_{h}h":np.nan,
                    f"aligned_mae_{h}h":np.nan,
                })
        rows.append(rec)

    lab=pd.DataFrame(rows).set_index("bar_open_ts").sort_index()
    lab.to_csv(OUT_LABELS,index_label="bar_open_ts")

    ps=pd.DataFrame([phase_stats(lab,p) for p in PHASES])
    ps.to_csv(OUT_PHASE,index=False)

    blocks=[]
    for b in ["2023-H1","2023-H2","2024-H1","2024-H2"]:
        q=lab[lab.block==b]
        cg=group_stats(q,CONT_GROUP)
        rg=group_stats(q,RISK_GROUP)
        blocks.append({
            "block":b,
            "continuation_n":cg["resolved24"],
            "continuation_hit":cg["aligned_hit24"],
            "risk_n":rg["resolved24"],
            "risk_hit":rg["aligned_hit24"],
            "gap":cg["aligned_hit24"]-rg["aligned_hit24"],
        })
    bdf=pd.DataFrame(blocks)
    bdf.to_csv(OUT_BLOCKS,index=False)

    auc_rows=[]
    for period,q in [
        ("2023_24",lab),
        ("2023",lab[lab.year==2023]),
        ("2024",lab[lab.year==2024]),
    ]:
        r=q[q.firsthit_24h.isin(["POS_FIRST","NEG_FIRST"])].copy()
        y=pd.to_numeric(r.aligned_hit_24h,errors="coerce").astype(int).to_numpy()
        for c in ["ContinuationQualityScore","RemainingEnergyScore","ReversalRiskScore"]:
            auc_rows.append({"period":period,"score":c,"n":len(r),"auc":auc_rank(y,r[c].to_numpy(float))})
    aucdf=pd.DataFrame(auc_rows)
    aucdf.to_csv(OUT_AUC,index=False)

    pmap=ps.set_index("phase")
    healthy_hit=float(pmap.loc["HealthyContinuation","aligned_hit24"])
    early_hit=float(pmap.loc["EarlyExpansion","aligned_hit24"])
    exhaust_hit=float(pmap.loc["Exhaustion","aligned_hit24"])
    trans_hit=float(pmap.loc["Transition","aligned_hit24"])

    cont_all=group_stats(lab,CONT_GROUP)
    risk_all=group_stats(lab,RISK_GROUP)
    q24=lab[lab.year==2024]
    cont24=group_stats(q24,CONT_GROUP)
    risk24=group_stats(q24,RISK_GROUP)

    def aucv(period,score):
        return float(aucdf[(aucdf.period==period)&(aucdf.score==score)].iloc[0].auc)

    audit=[]
    def add(name,ok,value):
        audit.append({"audit":name,"pass":bool(ok),"value":value})

    add("stage6c_valid",stage6c,stage6c)
    add("raw_5m_coverage_ge_99_5",coverage>=0.995,coverage)

    used=lab[lab.firsthit_24h.notna()]
    nocross=bool((used.decision_time+pd.Timedelta(hours=24)<=END).all()) if len(used) else False
    add("no_24h_window_crosses_2025",nocross,str(used.decision_time.max()) if len(used) else "")

    amb=float((used.firsthit_24h=="AMBIGUOUS").mean()) if len(used) else np.nan
    add("ambiguous_24h_share_le_2pct",amb<=0.02,amb)

    counts={p:int(pmap.loc[p,"eligible24"]) for p in PHASES}
    add("each_phase_ge_200_eligible24",all(v>=200 for v in counts.values()),counts)

    add("healthy_hit_ge_55pct",healthy_hit>=0.55,healthy_hit)
    add("early_hit_ge_53pct",early_hit>=0.53,early_hit)
    add("exhaustion_hit_le_50pct",exhaust_hit<=0.50,exhaust_hit)
    add("transition_hit_le_52pct",trans_hit<=0.52,trans_hit)

    he_gap=healthy_hit-exhaust_hit
    add("healthy_minus_exhaustion_ge_7pp",he_gap>=0.07,he_gap)

    group_gap=cont_all["aligned_hit24"]-risk_all["aligned_hit24"]
    add("continuation_group_minus_risk_ge_5pp",group_gap>=0.05,{
        "continuation":cont_all["aligned_hit24"],"risk":risk_all["aligned_hit24"],"gap":group_gap
    })
    ret_gap=cont_all["median_ret24"]-risk_all["median_ret24"]
    add("continuation_median_ret_gt_risk",ret_gap>0,{
        "continuation":cont_all["median_ret24"],"risk":risk_all["median_ret24"],"gap":ret_gap
    })

    add("2024_continuation_hit_ge_55pct",cont24["aligned_hit24"]>=0.55,cont24["aligned_hit24"])
    gap24=cont24["aligned_hit24"]-risk24["aligned_hit24"]
    add("2024_continuation_minus_risk_ge_5pp",gap24>=0.05,{
        "continuation":cont24["aligned_hit24"],"risk":risk24["aligned_hit24"],"gap":gap24
    })

    block_good=int((bdf.continuation_hit>0.50).sum())
    add("continuation_gt50_in_3of4_blocks",block_good>=3,bdf[["block","continuation_hit"]].to_dict("records"))

    auc_c=aucv("2023_24","ContinuationQualityScore")
    auc_e=aucv("2023_24","RemainingEnergyScore")
    auc_r=aucv("2023_24","ReversalRiskScore")
    add("continuation_quality_auc_ge_055",auc_c>=0.55,auc_c)
    add("remaining_energy_auc_ge_053",auc_e>=0.53,auc_e)
    add("reversal_risk_auc_le_047",auc_r<=0.47,auc_r)

    auc_c24=aucv("2024","ContinuationQualityScore")
    auc_r24=aucv("2024","ReversalRiskScore")
    add("2024_continuation_quality_auc_ge_054",auc_c24>=0.54,auc_c24)
    add("2024_reversal_risk_auc_le_048",auc_r24<=0.48,auc_r24)

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    lines=[
        "# SOL Regime + Phase V2 — Stage 6D DEV Future-Behavior Validation","",
        "Stage 6D tested frozen Stage-6C scores on 2023-2024 only. **2025/2026 remain unopened.**","",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.","",
        "## Phase outcome separation — selected directional side","",
        "| Phase | Eligible 24H | Resolved | Aligned hit | Median aligned ret24 | MFE24 | MAE24 |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for p in PHASES:
        x=pmap.loc[p]
        lines.append(
            f"| {p} | {int(x.eligible24)} | {int(x.resolved24)} | {x.aligned_hit24:.1%} | "
            f"{x.median_ret24:.3%} | {x.median_mfe24:.3%} | {x.median_mae24:.3%} |"
        )

    lines += ["","## Group separation","",
              "| Population | Continuation hit | Late/Risk hit | Gap | Continuation median ret | Risk median ret |",
              "|---|---:|---:|---:|---:|---:|",
              f"| 2023-24 | {cont_all['aligned_hit24']:.1%} | {risk_all['aligned_hit24']:.1%} | {group_gap:+.1%} | {cont_all['median_ret24']:.3%} | {risk_all['median_ret24']:.3%} |",
              f"| 2024 only | {cont24['aligned_hit24']:.1%} | {risk24['aligned_hit24']:.1%} | {gap24:+.1%} | {cont24['median_ret24']:.3%} | {risk24['median_ret24']:.3%} |",
              "","## Half-year robustness","",
              "| Block | Continuation hit | Late/Risk hit | Gap |",
              "|---|---:|---:|---:|"]
    for _,r in bdf.iterrows():
        lines.append(f"| {r.block} | {r.continuation_hit:.1%} | {r.risk_hit:.1%} | {r.gap:+.1%} |")

    lines += ["","## Threshold-free score ranking (AUC)","",
              "| Period | Continuation Quality | Remaining Energy | Reversal Risk |",
              "|---|---:|---:|---:|"]
    for per in ["2023_24","2023","2024"]:
        lines.append(
            f"| {per} | {aucv(per,'ContinuationQualityScore'):.3f} | "
            f"{aucv(per,'RemainingEnergyScore'):.3f} | {aucv(per,'ReversalRiskScore'):.3f} |"
        )

    lines += ["","## Mandatory gates","",
              "| Gate | Pass | Value |","|---|---|---|"]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATED**","",
            "The frozen phase / remaining-energy model materially separates continuation from late/risk states on DEV and internal 2024 temporal validation.",
            "Stage 6E is authorized to open the first frozen external holdout: 2025. No retuning is permitted before that run."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATED\nNEXT=STAGE6E_OOS_2025\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATION_FAILED**","",
            f"Failed gates: **{failed}**.",
            "2025 remains unopened. The current frozen V2 phase model is not promoted to OOS."
        ]
        OUT_STATUS.write_text("SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATION_FAILED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
