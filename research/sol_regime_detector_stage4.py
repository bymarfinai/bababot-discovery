#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
IN_SCORES=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Scores_DEV.csv"
IN_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_DETECTOR_STAGE4_Result.md"
OUT_STATES=ROOT/"SOL_REGIME_DETECTOR_STAGE4_States_DEV.csv"
OUT_SWITCHES=ROOT/"SOL_REGIME_DETECTOR_STAGE4_Switches.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_DETECTOR_STAGE4_Audit.csv"
OUT_PREFIX=ROOT/"SOL_REGIME_DETECTOR_STAGE4_PrefixAudit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE4_Status.txt"

START=pd.Timestamp("2023-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")

NORMAL_BARS=3
NORMAL_MARGIN=0.08
FAST_BARS=2
FAST_ADV=0.18
LOW_MARGIN=0.08
LOW_INCUMBENT=0.45
TRANSITION_PENALTY=0.70

CHECKPOINTS=[
    pd.Timestamp("2023-06-30T23:00:00Z"),
    pd.Timestamp("2023-12-31T23:00:00Z"),
    pd.Timestamp("2024-06-30T23:00:00Z"),
    pd.Timestamp("2024-12-31T22:00:00Z"),
]

SCORE_COL={"BULL":"BullScore","BEAR":"BearScore","SIDEWAYS":"SidewaysScore"}
REGIMES=["BULL","BEAR","SIDEWAYS"]

def clip01(x):
    return float(min(max(x,0.0),1.0))

def run_lengths(s:pd.Series):
    vals=[]
    if len(s)==0:
        return vals
    cur=s.iloc[0]; n=1
    for x in s.iloc[1:]:
        if x==cur:
            n+=1
        else:
            vals.append((cur,n))
            cur=x; n=1
    vals.append((cur,n))
    return vals

def summarize_runs(s:pd.Series):
    vals=run_lengths(s)
    out={}
    for r in REGIMES:
        a=[n for k,n in vals if k==r]
        out[r]={
            "runs":len(a),
            "median":float(np.median(a)) if a else np.nan,
            "p90":float(np.quantile(a,.9)) if a else np.nan,
            "onebar":sum(1 for n in a if n==1),
        }
    return out,vals

def state_machine(df:pd.DataFrame):
    rows=[]
    switches=[]

    incumbent=None
    duration=0
    candidate=None
    cand_count=0
    cand_min_margin=np.inf
    cand_min_adv=np.inf

    for ts,r in df.iterrows():
        raw=r["provisional_regime"]
        finite=(raw in REGIMES) and all(pd.notna(r[c]) for c in ["BullScore","BearScore","SidewaysScore"])

        switch_event=False
        switch_reason=""
        old_incumbent=incumbent

        if not finite:
            if incumbent is None:
                rows.append({
                    "bar_open_ts":ts,
                    "final_regime":"UNAVAILABLE",
                    "transition_flag":True,
                    "final_confidence":np.nan,
                    "regime_duration_hours":0,
                    "challenger_regime":"",
                    "challenger_streak":0,
                    "switch_event":False,
                    "switch_reason":"UNAVAILABLE",
                    "incumbent_score":np.nan,
                    "incumbent_advantage":np.nan,
                })
                continue
            duration+=1
        elif incumbent is None:
            incumbent=raw
            duration=1
            candidate=None
            cand_count=0
            cand_min_margin=np.inf
            cand_min_adv=np.inf
            switch_event=True
            switch_reason="STARTUP_SEED"
        else:
            if raw==incumbent:
                candidate=None
                cand_count=0
                cand_min_margin=np.inf
                cand_min_adv=np.inf
                duration+=1
            else:
                inc_score=float(r[SCORE_COL[incumbent]])
                chal_score=float(r[SCORE_COL[raw]])
                adv=chal_score-inc_score
                margin=float(r["score_margin"])

                if candidate==raw:
                    cand_count+=1
                    cand_min_margin=min(cand_min_margin,margin)
                    cand_min_adv=min(cand_min_adv,adv)
                else:
                    candidate=raw
                    cand_count=1
                    cand_min_margin=margin
                    cand_min_adv=adv

                normal_ok=(cand_count>=NORMAL_BARS and cand_min_margin>=NORMAL_MARGIN)
                fast_ok=(cand_count>=FAST_BARS and cand_min_adv>=FAST_ADV)

                if fast_ok or normal_ok:
                    old=incumbent
                    incumbent=raw
                    duration=1
                    switch_event=True
                    switch_reason="FAST_2BAR" if fast_ok else "NORMAL_3BAR"
                    switches.append({
                        "bar_open_ts":ts,
                        "old_regime":old,
                        "new_regime":incumbent,
                        "reason":switch_reason,
                        "challenger_streak":cand_count,
                        "min_margin_in_streak":cand_min_margin,
                        "min_advantage_in_streak":cand_min_adv,
                    })
                    candidate=None
                    cand_count=0
                    cand_min_margin=np.inf
                    cand_min_adv=np.inf
                else:
                    duration+=1

        if incumbent is None:
            inc_score=np.nan
            inc_adv=np.nan
            transition=True
            confidence=np.nan
        else:
            inc_score=float(r[SCORE_COL[incumbent]]) if finite else np.nan
            others=[float(r[SCORE_COL[x]]) for x in REGIMES if x!=incumbent] if finite else []
            inc_adv=inc_score-max(others) if finite else np.nan
            transition=(
                (not finite) or
                (raw!=incumbent) or
                (float(r["score_margin"])<LOW_MARGIN) or
                (inc_score<LOW_INCUMBENT) or
                (candidate is not None and cand_count>0)
            )
            if finite:
                adv_norm=clip01(0.5+inc_adv/0.30)
                base=clip01(0.70*inc_score+0.30*adv_norm)
                confidence=clip01(base*(TRANSITION_PENALTY if transition else 1.0))
            else:
                confidence=np.nan

        rows.append({
            "bar_open_ts":ts,
            "final_regime":incumbent if incumbent is not None else "UNAVAILABLE",
            "transition_flag":bool(transition),
            "final_confidence":confidence,
            "regime_duration_hours":duration,
            "challenger_regime":candidate or "",
            "challenger_streak":cand_count,
            "switch_event":bool(switch_event),
            "switch_reason":switch_reason,
            "incumbent_score":inc_score,
            "incumbent_advantage":inc_adv,
        })

    out=pd.DataFrame(rows).set_index("bar_open_ts")
    sw=pd.DataFrame(switches)
    return out,sw

def verify_switches(sw:pd.DataFrame):
    if sw.empty:
        return True,[]
    bad=[]
    for i,r in sw.iterrows():
        if r.reason=="FAST_2BAR":
            ok=(int(r.challenger_streak)>=FAST_BARS and float(r.min_advantage_in_streak)>=FAST_ADV-1e-12)
        elif r.reason=="NORMAL_3BAR":
            ok=(int(r.challenger_streak)>=NORMAL_BARS and float(r.min_margin_in_streak)>=NORMAL_MARGIN-1e-12)
        else:
            ok=False
        if not ok:
            bad.append(int(i))
    return len(bad)==0,bad

def prefix_audit(df,full_states):
    rows=[]
    cols=[
        "final_regime","transition_flag","final_confidence","regime_duration_hours",
        "challenger_regime","challenger_streak","incumbent_score","incumbent_advantage"
    ]
    for cp in CHECKPOINTS:
        p=df[df.index<=cp].copy()
        st,_=state_machine(p)
        if cp not in st.index or cp not in full_states.index:
            rows.append({"checkpoint":cp,"pass":False,"max_numeric_diff":np.inf,"categorical_mismatch":999})
            continue
        a=full_states.loc[cp]; b=st.loc[cp]
        nd=0.0; cm=0
        for c in cols:
            av=a[c]; bv=b[c]
            if c in ["final_regime","transition_flag","challenger_regime"]:
                if str(av)!=str(bv): cm+=1
            else:
                if pd.isna(av) and pd.isna(bv): continue
                if pd.isna(av)!=pd.isna(bv):
                    nd=np.inf
                else:
                    nd=max(nd,abs(float(av)-float(bv)))
        rows.append({"checkpoint":cp,"pass":bool(nd<=1e-12 and cm==0),"max_numeric_diff":nd,"categorical_mismatch":cm})
    return pd.DataFrame(rows)

def main():
    stage3_status=IN_STATUS.read_text() if IN_STATUS.exists() else ""
    stage3_valid="SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_VALID" in stage3_status

    df=pd.read_csv(IN_SCORES,parse_dates=["bar_open_ts"]).set_index("bar_open_ts").sort_index()
    df=df[(df.index>=START)&(df.index<END)].copy()

    states,sw=state_machine(df)
    export=pd.concat([
        df[["decision_time","partition","BullScore","BearScore","SidewaysScore","provisional_regime","score_margin","confidence_raw"]],
        states
    ],axis=1)
    export.to_csv(OUT_STATES,index_label="bar_open_ts")
    sw.to_csv(OUT_SWITCHES,index=False)

    audit=[]
    def add(name,ok,value,detail=""):
        audit.append({"audit":name,"pass":bool(ok),"value":value,"detail":detail})

    add("stage3_valid",stage3_valid,stage3_valid)

    years=sorted(set(export.index.year.tolist()))
    add("no_2025_2026_rows",all(y in (2023,2024) for y in years),years)

    valid=export[export.final_regime.isin(REGIMES)].copy()
    add("final_regime_only_three_classes",set(valid.final_regime.unique()).issubset(set(REGIMES)),sorted(valid.final_regime.unique().tolist()))
    add("transition_is_separate_flag",valid.transition_flag.dtype==bool or valid.transition_flag.dropna().isin([True,False]).all(),str(valid.transition_flag.dtype))

    conf=valid.final_confidence.dropna()
    add("confidence_in_0_1",bool(((conf>=0)&(conf<=1)).all()),[float(conf.min()),float(conf.max())] if len(conf) else [])

    pa=prefix_audit(df,states)
    pa.to_csv(OUT_PREFIX,index=False)
    add("prefix_causality_all_checkpoints",bool(pa["pass"].all()),f"{int(pa['pass'].sum())}/{len(pa)}")

    sw_ok,bad_sw=verify_switches(sw)
    add("all_switches_obey_frozen_rules",sw_ok,bad_sw)

    forbidden=[c for c in export.columns if any(k in c.lower() for k in [
        "forward","future","tp_","sl_","mfe","mae","outcome","trade_result"
    ])]
    add("no_future_outcome_fields",len(forbidden)==0,forbidden)

    shares=valid.final_regime.value_counts(normalize=True)
    share_dict={r:float(shares.get(r,0.0)) for r in REGIMES}
    add("nondegenerate_final_class_shares",all(v>=0.05 for v in share_dict.values()),share_dict)

    trans_share=float(valid.transition_flag.mean())
    add("transition_share_5_to_60pct",0.05<=trans_share<=0.60,trans_share)

    raw_valid=df[df.provisional_regime.isin(REGIMES)].provisional_regime
    raw_runs,raw_vals=summarize_runs(raw_valid)
    final_runs,final_vals=summarize_runs(valid.final_regime)

    raw_switches=max(0,len(raw_vals)-1)
    final_switches=max(0,len(final_vals)-1)
    ratio=(final_switches/raw_switches) if raw_switches else 0.0
    add("final_switches_le_70pct_raw",ratio<=0.70,{"raw":raw_switches,"final":final_switches,"ratio":ratio})

    onebar_total=sum(1 for _,n in final_vals if n==1)
    onebar_share=onebar_total/len(final_vals) if final_vals else 0.0
    add("onebar_final_runs_le_10pct",onebar_share<=0.10,onebar_share)

    med_ok=True
    med_detail={}
    for r in REGIMES:
        rm=raw_runs[r]["median"]
        fm=final_runs[r]["median"]
        ok=(pd.notna(rm) and pd.notna(fm) and fm>=rm)
        med_detail[r]={"raw":rm,"final":fm,"pass":bool(ok)}
        med_ok &= bool(ok)
    add("median_duration_not_lower_than_raw",med_ok,med_detail)

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    lines=[
        "# SOL Regime Detector — Stage 4 Hysteresis / Transition Result","",
        "Stage 4 used **2023–2024 only**. No forward return, TP/SL, trade outcome, 2025, or 2026 data were used.","",
        "## Mandatory audits","",
        "| Audit | Pass | Value |","|---|---|---|"
    ]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Raw vs final regime distribution","",
              "| Regime | Raw share | Final share | Raw median run | Final median run | Final P90 run |",
              "|---|---:|---:|---:|---:|---:|"]
    raw_share=raw_valid.value_counts(normalize=True)
    for r in REGIMES:
        lines.append(
            f"| {r} | {float(raw_share.get(r,0)):.1%} | {share_dict[r]:.1%} | "
            f"{raw_runs[r]['median']:.1f}h | {final_runs[r]['median']:.1f}h | {final_runs[r]['p90']:.1f}h |"
        )

    lines += ["","## State-machine stability","",
              f"- Raw provisional switches: **{raw_switches}**.",
              f"- Final regime switches: **{final_switches}**.",
              f"- Switch retention ratio: **{ratio:.1%}** of raw switching.",
              f"- One-bar final runs: **{onebar_total}/{len(final_vals)} ({onebar_share:.1%})**.",
              f"- Transition-flag share: **{trans_share:.1%}**.",
              f"- Confirmed non-startup switches logged: **{len(sw)}**.","",
              "## Prefix causality","",
              "| Checkpoint | Pass | Max numeric diff | Categorical mismatch |",
              "|---|---|---:|---:|"]
    for _,r in pa.iterrows():
        lines.append(f"| {r.checkpoint} | {'PASS' if r['pass'] else 'FAIL'} | {r.max_numeric_diff} | {int(r.categorical_mismatch)} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_VALID**","",
            "The causal hysteresis / transition layer passed all frozen stability and replay audits.",
            "The detector now has a final-form state output suitable for Stage 5 forward-behavior validation.",
            "Stage 5 may test whether BULL / BEAR / SIDEWAYS actually separate subsequent SOL behavior, but may not retroactively change Stage-4 rules."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_VALID\nNEXT=STAGE5_REGIME_VALIDATION\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_REJECTED**","",
            f"Failed audits: **{failed}**.",
            "Stage 5 is blocked. Any revised hysteresis must be preregistered before rerunning."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_REJECTED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
