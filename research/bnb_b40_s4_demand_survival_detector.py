#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json, math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S4_DEMAND_SURVIVAL_DETECTOR"
SRC=ROOT/"results/bnb_b40_s3/BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY_DecisionLedger.csv.gz"

SPECS={
    "SD1_CLOSE15_ABOVE_ANCHOR":{
        "feature":"CLOSE15_ABOVE_ANCHOR",
        "role":"PRIMARY",
    },
    "B1_ALL3_ABOVE_ANCHOR":{
        "feature":"ALL3_CLOSES_ABOVE_ANCHOR",
        "role":"STRICT_BENCHMARK",
    },
    "B2_BREAK_TOUCH_HIGH":{
        "feature":"CLOSE15_BREAK_TOUCH_HIGH",
        "role":"STRICT_BENCHMARK",
    },
}
PRIMARY="SD1_CLOSE15_ABOVE_ANCHOR"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def wilson(k,n,z=1.959963984540054):
    if n<=0:return np.nan,np.nan
    p=k/n
    den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return centre-half,centre+half

def load():
    if not SRC.exists():
        raise RuntimeError(f"missing frozen B40-S3 ledger: {SRC}")
    L=pd.read_csv(SRC,compression="gzip")
    for c in ["first_retest_ts","decision_ts"]:
        L[c]=pd.to_datetime(L[c],utc=True,errors="coerce")
    for c in [x["feature"] for x in SPECS.values()]:
        if L[c].dtype!=bool:
            L[c]=L[c].astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})
    L["survived"]=L["survived"].astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})
    Q=L[(L.decision=="PLUS15_CLOSE")&(L.decision_status=="ELIGIBLE")].copy()
    exp={"DEV":(532,391,141),"REF":(307,228,79)}
    for per,(n,s,c) in exp.items():
        q=Q[Q.period==per]
        got=(len(q),int(q.survived.sum()),int((~q.survived).sum()))
        if got!=(n,s,c):
            raise RuntimeError(f"S3 +15 parity drift {per}: {got} != {(n,s,c)}")
    return L,Q

def metric(q,feature,parent_survive_total,too_fast_survive):
    base=float(q.survived.mean()) if len(q) else np.nan
    passed=q[q[feature].astype(bool)].copy()
    rejected=q[~q[feature].astype(bool)].copy()
    ps=int(passed.survived.sum())
    pc=int((~passed.survived).sum())
    es=int(q.survived.sum())
    ec=int((~q.survived).sum())
    lo,hi=wilson(ps,len(passed))
    return {
        "eligible":len(q),
        "eligible_survive":es,
        "eligible_consumed":ec,
        "base_survival_rate":base,
        "pass_n":len(passed),
        "pass_rate":len(passed)/len(q) if len(q) else np.nan,
        "pass_survive":ps,
        "pass_consumed":pc,
        "pass_survival_precision":ps/len(passed) if len(passed) else np.nan,
        "pass_precision_wilson_lo":lo,
        "pass_precision_wilson_hi":hi,
        "uplift_pp":100*((ps/len(passed))-base) if len(passed) else np.nan,
        "relative_lift":(ps/len(passed))/base if len(passed) and base>0 else np.nan,
        "survivor_retention":ps/es if es else np.nan,
        "consumed_rejection":int((~rejected.survived).sum())/ec if ec else np.nan,
        "false_pass_consumed_rate":pc/ec if ec else np.nan,
        "rejected_survive":int(rejected.survived.sum()),
        "rejected_consumed":int((~rejected.survived).sum()),
        "too_fast_survive":too_fast_survive,
        "whole_parent_survive":parent_survive_total,
        "whole_parent_survivor_capture":ps/parent_survive_total if parent_survive_total else np.nan,
    }

def main():
    L,Q=load()

    spec_signature=hashlib.sha256(
        json.dumps({
            "primary":PRIMARY,
            "feature":SPECS[PRIMARY]["feature"],
            "decision":"PLUS15_CLOSE",
            "parent":"B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    parent_survive={"DEV":500,"REF":309}
    too_fast={"DEV":109,"REF":81}

    rows=[]
    for det,spec in SPECS.items():
        for per in ["DEV","REF"]:
            q=Q[Q.period==per]
            rows.append({
                "detector":det,
                "role":spec["role"],
                "period":per,
                **metric(q,spec["feature"],parent_survive[per],too_fast[per])
            })
    S=pd.DataFrame(rows)

    # Hard parity with S3 published state audit for primary.
    expected_primary={
        "DEV":(286,235,51),
        "REF":(160,137,23),
    }
    for per,(pn,ps,pc) in expected_primary.items():
        r=S[(S.detector==PRIMARY)&(S.period==per)].iloc[0]
        got=(int(r.pass_n),int(r.pass_survive),int(r.pass_consumed))
        if got!=(pn,ps,pc):
            raise RuntimeError(f"Primary frozen-state parity drift {per}: {got} != {(pn,ps,pc)}")

    # Year metrics: use period-specific parent counts from TOUCH_CLOSE and resolved-too-fast counts from +15 census.
    touch=L[(L.decision=="TOUCH_CLOSE")&(L.decision_status=="ELIGIBLE")]
    plus15_all=L[L.decision=="PLUS15_CLOSE"]
    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=Q[Q.year==y]
        if not len(q): continue
        p=touch[touch.year==y]
        t=plus15_all[(plus15_all.year==y)&(plus15_all.decision_status=="TOO_FAST_SURVIVE")]
        for det,spec in SPECS.items():
            Y.append({
                "year":y,
                "detector":det,
                "role":spec["role"],
                **metric(q,spec["feature"],int(p.survived.sum()),len(t))
            })
    Y=pd.DataFrame(Y)

    # Operational classifier bookkeeping:
    # Fast survivors have already proven survival; unresolved cohort uses SD1.
    OP=[]
    for per in ["DEV","REF"]:
        q=Q[Q.period==per]
        spec=SPECS[PRIMARY]
        passed=q[q[spec["feature"]].astype(bool)]
        total_parent=parent_survive[per] + (157 if per=="DEV" else 94)  # eligible survive+consumed parent only
        op_true_survive=too_fast[per]+int(passed.survived.sum())
        op_false_pass=int((~passed.survived).sum())
        # consumed resolved before +15 are correctly known consumed and not passed
        fast_consumed=int(((L.decision=="PLUS15_CLOSE")&(L.period==per)&(L.decision_status=="TOO_FAST_CONSUMED")).sum())
        unresolved_reject=q[~q[spec["feature"]].astype(bool)]
        op_true_reject=fast_consumed+int((~unresolved_reject.survived).sum())
        OP.append({
            "period":per,
            "fast_survive_resolved":too_fast[per],
            "fast_consumed_resolved":fast_consumed,
            "sd1_pass_survive":int(passed.survived.sum()),
            "sd1_pass_consumed":op_false_pass,
            "sd1_reject_survive":int(unresolved_reject.survived.sum()),
            "sd1_reject_consumed":int((~unresolved_reject.survived).sum()),
            "known_or_predicted_survive":op_true_survive+op_false_pass,
            "correct_survive_among_positive":op_true_survive,
            "operational_positive_precision":op_true_survive/(op_true_survive+op_false_pass) if op_true_survive+op_false_pass else np.nan,
            "parent_survivor_recognition":op_true_survive/parent_survive[per],
            "consumed_correctly_rejected":op_true_reject,
        })
    OP=pd.DataFrame(OP)

    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    OP.to_csv(ROOT/f"{PFX}_OperationalView.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PRIMARY={PRIMARY}\n"
        f"PRIMARY_FEATURE={SPECS[PRIMARY]['feature']}\n"
        f"DETECTOR_SIGNATURE_SHA256={spec_signature}\n"
        "DECISION=PLUS15_CLOSE\n"
        "PARENT=B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY\n"
        "DEV_ELIGIBLE=532\nREF_ELIGIBLE=307\n"
        "NO_THRESHOLD_SEARCH=TRUE\nNO_COMBINATION_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S4 — Frozen Demand Survival Detector Validation","",
        f"Primary detector: **{PRIMARY}**",
        f"Signature: `{spec_signature}`",
        "Rule: at +15m after first retest, PASS iff completed reaction window closes above the original touch anchor.","",
        "## Frozen +15m detector validation","",
        "| Detector | Period | Eligible | PASS | Survival precision | Base | Uplift | Survivor retention | Consumed rejection | False-pass consumed | Whole-parent survivor capture |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.detector} | {r.period} | {r.eligible} | {r.pass_n} ({fmt_pct(r.pass_rate)}) | "
            f"{r.pass_survive}/{r.pass_n} ({fmt_pct(r.pass_survival_precision)}) | {fmt_pct(r.base_survival_rate)} | "
            f"{fmt_num(r.uplift_pp,1)}pp | {fmt_pct(r.survivor_retention)} | "
            f"{fmt_pct(r.consumed_rejection)} | {r.pass_consumed}/{r.eligible_consumed} ({fmt_pct(r.false_pass_consumed_rate)}) | "
            f"{fmt_pct(r.whole_parent_survivor_capture)} |"
        )

    lines += ["","## Primary year stability","",
        "| Year | Eligible | PASS | Survival precision | Base | Uplift | Survivor retention | Consumed rejection |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y[Y.detector==PRIMARY].itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.eligible} | {r.pass_n} | {fmt_pct(r.pass_survival_precision)} | "
            f"{fmt_pct(r.base_survival_rate)} | {fmt_num(r.uplift_pp,1)}pp | "
            f"{fmt_pct(r.survivor_retention)} | {fmt_pct(r.consumed_rejection)} |"
        )

    lines += ["","## Operational state-recognition view","",
        "| Period | Fast survive already resolved | Fast consumed already resolved | SD1 pass S/C | SD1 reject S/C | Positive precision | Parent survivor recognition |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in OP.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.fast_survive_resolved} | {r.fast_consumed_resolved} | "
            f"{r.sd1_pass_survive}/{r.sd1_pass_consumed} | {r.sd1_reject_survive}/{r.sd1_reject_consumed} | "
            f"{fmt_pct(r.operational_positive_precision)} | {fmt_pct(r.parent_survivor_recognition)} |"
        )

    lines += ["","## Interpretation boundary",
        "S4 validates demand SURVIVAL only.",
        "The strict benchmarks are reported but cannot replace the preregistered primary detector in this stage.",
        "REF has already been inspected during B40 discovery, so it is confirmation data rather than pristine out-of-sample evidence.",
        "No expansion, entry, SL, or TP conclusion is implied by a survival PASS."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S4_DEMAND_SURVIVAL_DETECTOR_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
