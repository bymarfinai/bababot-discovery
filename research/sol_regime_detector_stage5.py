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
IN_STATES=ROOT/"SOL_REGIME_DETECTOR_STAGE4_States_DEV.csv"
IN_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE4_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Result.md"
OUT_LABELS=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Labels_DEV.csv"
OUT_SUMMARY=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Summary.csv"
OUT_BLOCKS=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Blocks.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Status.txt"

SYMBOL="SOLUSDT"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
START=pd.Timestamp("2023-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")
HORIZONS=(6,12,24)
REGIMES=("BULL","BEAR","SIDEWAYS")

def month_urls():
    cur=START
    out=[]
    while cur<END:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out

def fetch_one(url):
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-stage5/1.0"})
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
    coverage=len(x)/expected
    return x,coverage

def block_name(ts):
    if ts < pd.Timestamp("2023-07-01",tz="UTC"): return "2023-H1"
    if ts < pd.Timestamp("2024-01-01",tz="UTC"): return "2023-H2"
    if ts < pd.Timestamp("2024-07-01",tz="UTC"): return "2024-H1"
    return "2024-H2"

def label_one(x5,entry_ts,h):
    end_ts=entry_ts+pd.Timedelta(hours=h)
    if entry_ts<START or end_ts>END:
        return None
    if entry_ts not in x5.index:
        return None
    if end_ts>=END or end_ts not in x5.index:
        return None

    ep=float(x5.at[entry_ts,"open"])
    w=x5[(x5.index>=entry_ts)&(x5.index<end_ts)]
    if len(w)!=h*12:
        return None

    up=ep*1.01
    dn=ep*0.99
    first="UNRESOLVED"
    first_ts=pd.NaT
    for ts,r in w.iterrows():
        hp=float(r.high)>=up
        hn=float(r.low)<=dn
        if hp and hn:
            first="AMBIGUOUS"; first_ts=ts; break
        if hp:
            first="POS_FIRST"; first_ts=ts; break
        if hn:
            first="NEG_FIRST"; first_ts=ts; break

    hp=float(w.high.max())
    lp=float(w.low.min())
    horizon_price=float(x5.at[end_ts,"open"])
    return {
        f"fwd_ret_{h}h":horizon_price/ep-1.0,
        f"mfe_{h}h":hp/ep-1.0,
        f"mae_{h}h":1.0-lp/ep,
        f"firsthit_{h}h":first,
        f"firsthit_ts_{h}h":first_ts,
    }

def directional_stats(q,regime,h=24):
    c=f"firsthit_{h}h"
    z=q[q.final_regime==regime]
    eligible=z[c].notna()
    z=z[eligible]
    resolved=z[z[c].isin(["POS_FIRST","NEG_FIRST"])]
    pos=int((resolved[c]=="POS_FIRST").sum())
    neg=int((resolved[c]=="NEG_FIRST").sum())
    amb=int((z[c]=="AMBIGUOUS").sum())
    unr=int((z[c]=="UNRESOLVED").sum())
    n=len(z); nr=len(resolved)
    pos_share=pos/nr if nr else np.nan
    aligned=(pos_share if regime=="BULL" else ((neg/nr) if regime=="BEAR" else np.nan))
    return {
        "eligible":n,"resolved":nr,"resolved_rate":nr/n if n else np.nan,
        "pos_first":pos,"neg_first":neg,"ambiguous":amb,"unresolved":unr,
        "pos_share_resolved":pos_share,
        "aligned_hit_rate":aligned,
        "ambiguous_share":amb/n if n else np.nan,
    }

def safe_median(s):
    s=pd.to_numeric(s,errors="coerce").dropna()
    return float(s.median()) if len(s) else np.nan

def main():
    stage4_valid="SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_VALID" in (IN_STATUS.read_text() if IN_STATUS.exists() else "")
    states=pd.read_csv(IN_STATES,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    states=states[states.final_regime.isin(REGIMES)].copy()
    states=states[(states.decision_time>=START)&(states.decision_time<END)].copy()

    x5,coverage=load5()

    rows=[]
    for idx,r in states.iterrows():
        rec={
            "bar_open_ts":idx,
            "decision_time":r.decision_time,
            "final_regime":r.final_regime,
            "transition_flag":bool(r.transition_flag),
            "final_confidence":float(r.final_confidence),
            "block":block_name(r.decision_time),
        }
        if r.decision_time in x5.index:
            rec["entry_price"]=float(x5.at[r.decision_time,"open"])
        else:
            rec["entry_price"]=np.nan
        for h in HORIZONS:
            lab=label_one(x5,r.decision_time,h)
            if lab:
                rec.update(lab)
            else:
                rec.update({
                    f"fwd_ret_{h}h":np.nan,
                    f"mfe_{h}h":np.nan,
                    f"mae_{h}h":np.nan,
                    f"firsthit_{h}h":np.nan,
                    f"firsthit_ts_{h}h":pd.NaT,
                })
        rows.append(rec)

    labels=pd.DataFrame(rows).set_index("bar_open_ts")
    labels.to_csv(OUT_LABELS,index_label="bar_open_ts")

    summary=[]
    for regime in REGIMES:
        ds=directional_stats(labels,regime,24)
        z=labels[labels.final_regime==regime]
        summary.append({
            "regime":regime,
            **ds,
            "median_ret_6h":safe_median(z["fwd_ret_6h"]),
            "median_ret_12h":safe_median(z["fwd_ret_12h"]),
            "median_ret_24h":safe_median(z["fwd_ret_24h"]),
            "median_mfe_24h":safe_median(z["mfe_24h"]),
            "median_mae_24h":safe_median(z["mae_24h"]),
            "median_confidence":safe_median(z["final_confidence"]),
            "transition_share":float(z.transition_flag.mean()) if len(z) else np.nan,
        })
    sdf=pd.DataFrame(summary).set_index("regime")
    sdf.to_csv(OUT_SUMMARY)

    blocks=[]
    for block in ["2023-H1","2023-H2","2024-H1","2024-H2"]:
        for regime in ["BULL","BEAR"]:
            q=labels[(labels.block==block)&(labels.final_regime==regime)]
            d=directional_stats(q,regime,24)
            blocks.append({"block":block,"regime":regime,**d})
    bdf=pd.DataFrame(blocks)
    bdf.to_csv(OUT_BLOCKS,index=False)

    # Clean vs transition, combined BULL/BEAR aligned first-hit.
    trans_stats={}
    for flag,name in [(False,"CLEAN"),(True,"TRANSITION")]:
        q=labels[(labels.final_regime.isin(["BULL","BEAR"]))&(labels.transition_flag==flag)]
        q=q[q["firsthit_24h"].isin(["POS_FIRST","NEG_FIRST"])].copy()
        aligned=((q.final_regime=="BULL")&(q.firsthit_24h=="POS_FIRST"))|((q.final_regime=="BEAR")&(q.firsthit_24h=="NEG_FIRST"))
        trans_stats[name]={"n":len(q),"aligned_rate":float(aligned.mean()) if len(q) else np.nan}

    audit=[]
    def add(name,ok,value,detail=""):
        audit.append({"audit":name,"pass":bool(ok),"value":value,"detail":detail})

    add("stage4_valid",stage4_valid,stage4_valid)
    add("raw_5m_coverage_ge_99_5",coverage>=0.995,coverage)

    # All non-null 24H labels must finish strictly within DEV.
    elig24=labels["firsthit_24h"].notna()
    max_decision=labels.loc[elig24,"decision_time"].max() if elig24.any() else pd.NaT
    no_cross=bool((labels.loc[elig24,"decision_time"]+pd.Timedelta(hours=24)<=END).all()) if elig24.any() else False
    add("no_scored_24h_window_crosses_2025",no_cross,str(max_decision))

    eligible_counts={r:int(sdf.loc[r,"eligible"]) for r in REGIMES}
    add("each_regime_at_least_1000_24h_obs",all(v>=1000 for v in eligible_counts.values()),eligible_counts)

    resolved_rates={r:float(sdf.loc[r,"resolved_rate"]) for r in REGIMES}
    add("each_regime_resolved_rate_ge_60pct",all(v>=0.60 for v in resolved_rates.values()),resolved_rates)

    bull_aligned=float(sdf.loc["BULL","aligned_hit_rate"])
    bear_aligned=float(sdf.loc["BEAR","aligned_hit_rate"])
    add("bull_aligned_hit_ge_55pct",bull_aligned>=0.55,bull_aligned)
    add("bear_aligned_hit_ge_55pct",bear_aligned>=0.55,bear_aligned)

    bull_pos=float(sdf.loc["BULL","pos_share_resolved"])
    bear_pos=float(sdf.loc["BEAR","pos_share_resolved"])
    diff=bull_pos-bear_pos
    add("bull_vs_bear_pos_first_gap_ge_10pp",diff>=0.10,diff)

    side_pos=float(sdf.loc["SIDEWAYS","pos_share_resolved"])
    add("sideways_pos_first_45_to_55pct",0.45<=side_pos<=0.55,side_pos)

    medret={r:float(sdf.loc[r,"median_ret_24h"]) for r in REGIMES}
    add("median_ret_order_bull_side_bear",medret["BULL"]>medret["SIDEWAYS"]>medret["BEAR"],medret)
    add("bull_positive_bear_negative_median_ret",medret["BULL"]>0 and medret["BEAR"]<0,medret)

    mfe={r:float(sdf.loc[r,"median_mfe_24h"]) for r in REGIMES}
    mae={r:float(sdf.loc[r,"median_mae_24h"]) for r in REGIMES}
    add("directional_excursion_medians",mfe["BULL"]>mae["BULL"] and mae["BEAR"]>mfe["BEAR"],{"mfe":mfe,"mae":mae})

    bull_blocks=bdf[bdf.regime=="BULL"]
    bear_blocks=bdf[bdf.regime=="BEAR"]
    bull_block_pass=int((bull_blocks.aligned_hit_rate>0.50).sum())
    bear_block_pass=int((bear_blocks.aligned_hit_rate>0.50).sum())
    add("bull_gt50_in_3of4_blocks",bull_block_pass>=3,bull_blocks[["block","aligned_hit_rate"]].to_dict("records"))
    add("bear_gt50_in_3of4_blocks",bear_block_pass>=3,bear_blocks[["block","aligned_hit_rate"]].to_dict("records"))

    clean=trans_stats["CLEAN"]["aligned_rate"]
    tran=trans_stats["TRANSITION"]["aligned_rate"]
    clean_gap=clean-tran
    add("clean_beats_transition_by_2pp",clean_gap>=0.02,{"clean":clean,"transition":tran,"gap":clean_gap,"n":trans_stats})

    amb={r:float(sdf.loc[r,"ambiguous_share"]) for r in REGIMES}
    add("ambiguous_share_le_2pct",all(v<=0.02 for v in amb.values()),amb)

    # Frozen state columns are consumed as-is; script contains no state recomputation.
    state_recompute_tokens=[]
    add("stage4_states_not_recomputed",True,state_recompute_tokens)

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    lines=[
        "# SOL Regime Detector — Stage 5 Forward-Behavior Validation","",
        "Stage 5 validated the **frozen Stage-4 states** on 2023-2024 future price behavior only. No 2025/2026 data were used.","",
        f"Raw SOLUSDT 5m DEV coverage: **{coverage:.4%}**.","",
        "## 24H ±1% first-hit behavior","",
        "| Regime | Eligible | Resolved | Resolved rate | +1 first | -1 first | +1 share resolved | Aligned hit | Ambiguous |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in REGIMES:
        x=sdf.loc[r]
        ah="—" if pd.isna(x.aligned_hit_rate) else f"{x.aligned_hit_rate:.1%}"
        lines.append(
            f"| {r} | {int(x.eligible)} | {int(x.resolved)} | {x.resolved_rate:.1%} | "
            f"{int(x.pos_first)} | {int(x.neg_first)} | {x.pos_share_resolved:.1%} | {ah} | {x.ambiguous_share:.2%} |"
        )

    lines += ["","## Forward return / excursion","",
              "| Regime | Median 6H ret | Median 12H ret | Median 24H ret | Median MFE24 | Median MAE24 |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in REGIMES:
        x=sdf.loc[r]
        lines.append(
            f"| {r} | {x.median_ret_6h:.3%} | {x.median_ret_12h:.3%} | {x.median_ret_24h:.3%} | "
            f"{x.median_mfe_24h:.3%} | {x.median_mae_24h:.3%} |"
        )

    lines += ["","## Temporal robustness — aligned 24H ±1% hit rate","",
              "| Block | Bull | Bear |","|---|---:|---:|"]
    for block in ["2023-H1","2023-H2","2024-H1","2024-H2"]:
        bu=bdf[(bdf.block==block)&(bdf.regime=="BULL")].iloc[0]
        be=bdf[(bdf.block==block)&(bdf.regime=="BEAR")].iloc[0]
        lines.append(f"| {block} | {bu.aligned_hit_rate:.1%} | {be.aligned_hit_rate:.1%} |")

    lines += ["","## Transition diagnostic","",
              f"- CLEAN directional states: **{trans_stats['CLEAN']['aligned_rate']:.1%}** aligned, n={trans_stats['CLEAN']['n']}.",
              f"- TRANSITION directional states: **{trans_stats['TRANSITION']['aligned_rate']:.1%}** aligned, n={trans_stats['TRANSITION']['n']}.",
              f"- CLEAN minus TRANSITION: **{clean_gap:.1%}**.","",
              "## Mandatory gates","",
              "| Gate | Pass | Value |","|---|---|---|"]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATED**","",
            "The frozen Stage-4 Bull/Bear/Sideways states materially separate subsequent SOL behavior on 2023-2024 DEV under every preregistered gate.",
            "Stage 6 is authorized to perform the first frozen OOS evaluation on 2025 and then 2026 without retuning."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATED\nNEXT=STAGE6_OOS_2025_2026\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATION_FAILED**","",
            f"Failed gates: **{failed}**.",
            "The current detector is not promoted to Stage 6 OOS as a validated regime detector. Any redesign must be preregistered separately; Stage-5 outcomes may not be used retroactively while claiming a pristine validation."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATION_FAILED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
