#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json, math
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S6_FROZEN_EXPANSION_CANDIDATE"
S1=ROOT/"results/bnb_b40_s1/BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_CandidateLedger.csv.gz"
S3=ROOT/"results/bnb_b40_s3/BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY_DecisionLedger.csv.gz"

FAST_MIN=60.0
NARROW_CUT=0.006155789474971198
P5_RANGE_CUT=0.4509029031810024

TARGETS=["GE1R","GE1_5R","GE2R"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def boolify(s):
    if s.dtype==bool:return s
    return s.astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})

def wilson(k,n,z=1.959963984540054):
    if n<=0:return np.nan,np.nan
    p=k/n
    den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return centre-half,centre+half

def load_parent():
    if not S1.exists(): raise RuntimeError(f"missing {S1}")
    A=pd.read_csv(S1,compression="gzip")
    for c in ["first_retest_ts","consumption_ts","survival_resolution_ts","activation_ts"]:
        if c in A.columns:
            A[c]=pd.to_datetime(A[c],utc=True,errors="coerce")
    A["normalizable"]=boolify(A.normalizable)
    for c in ["hit_1_0r","hit_1_5r","hit_2_0r"]:
        A[c]=boolify(A[c])

    Q=A[A.normalizable & A.survival_status.eq("SURVIVE")].copy()
    Q["GE1R"]=Q.hit_1_0r.astype(bool)
    Q["GE1_5R"]=Q.hit_1_5r.astype(bool)
    Q["GE2R"]=Q.hit_2_0r.astype(bool)
    Q["base_width_pct"]=pd.to_numeric(Q.base_width,errors="coerce")/pd.to_numeric(Q.bos_close,errors="coerce")
    Q["XP1_FAST_PROOF60"]=pd.to_numeric(Q.time_to_0_5r_min,errors="coerce")<=FAST_MIN
    Q["B1_NARROW_SOURCE_Q1"]=pd.to_numeric(Q.base_width_pct,errors="coerce")<=NARROW_CUT

    expected={"DEV":(500,361,266,205),"REF":(309,231,168,134)}
    for per,(n,a,b,c) in expected.items():
        z=Q[Q.period==per]
        got=(len(z),int(z.GE1R.sum()),int(z.GE1_5R.sum()),int(z.GE2R.sum()))
        if got!=(n,a,b,c):
            raise RuntimeError(f"parent parity drift {per}: {got}")
    return Q

def whole_metric(q,flag):
    passed=q[q[flag].astype(bool)].copy()
    out={
        "n":len(q),
        "pass_n":len(passed),
        "pass_rate":len(passed)/len(q) if len(q) else np.nan,
        "median_proof_min_pass":float(pd.to_numeric(passed.time_to_0_5r_min,errors="coerce").median()) if len(passed) else np.nan,
    }
    for t in TARGETS:
        total=int(q[t].sum())
        success=int(passed[t].sum())
        base=float(q[t].mean()) if len(q) else np.nan
        precision=float(passed[t].mean()) if len(passed) else np.nan
        out[f"{t}_base"]=base
        out[f"{t}_pass_success"]=success
        out[f"{t}_precision"]=precision
        out[f"{t}_uplift_pp"]=100*(precision-base) if np.isfinite(precision) and np.isfinite(base) else np.nan
        out[f"{t}_relative_lift"]=precision/base if np.isfinite(precision) and base>0 else np.nan
        out[f"{t}_retention"]=success/total if total else np.nan
    loc=int((~passed.GE1R).sum()) if len(passed) else 0
    out["GE1R_local_only_false_positive"]=loc
    out["GE1R_local_only_rate_in_pass"]=loc/len(passed) if len(passed) else np.nan
    lo,hi=wilson(int(passed.GE1R.sum()),len(passed))
    out["GE1R_wilson_lo"]=lo
    out["GE1R_wilson_hi"]=hi
    return out

def first_post_touch_bars(raw5,ts,n):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(ts),side="right"))
    if i0+n>len(raw5):return None
    return raw5.iloc[i0:i0+n]

def build_b2(Q):
    if not S3.exists(): raise RuntimeError(f"missing {S3}")
    B=pd.read_csv(S3,compression="gzip")
    for c in ["first_retest_ts","decision_ts"]:
        if c in B.columns:B[c]=pd.to_datetime(B[c],utc=True,errors="coerce")
    p5=B[B.decision.eq("PLUS5_CLOSE")][["zone_id","p5_range_r"]].copy()
    if p5.zone_id.duplicated().any(): raise RuntimeError("duplicate p5 zone_id")
    M=Q.merge(p5,on="zone_id",how="left",validate="one_to_one")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)

    status=[]
    for r in M.itertuples(index=False):
        bars=first_post_touch_bars(raw5,r.first_retest_ts,1)
        if bars is None:
            status.append("CENSORED"); continue
        target=float(r.touch_close)+1.0*float(r.event_risk)
        if bool((bars.high>=target).any()):
            status.append("TOO_FAST_GE1")
        else:
            status.append("ELIGIBLE")
    M["b2_status"]=status
    M["B2_STRONG_P5_RANGE_Q4"]=pd.to_numeric(M.p5_range_r,errors="coerce")>P5_RANGE_CUT
    return M

def b2_metric(q):
    e=q[q.b2_status.eq("ELIGIBLE")].copy()
    p=e[e.B2_STRONG_P5_RANGE_Q4].copy()
    base=float(e.GE1R.mean()) if len(e) else np.nan
    prec=float(p.GE1R.mean()) if len(p) else np.nan
    total=int(e.GE1R.sum())
    succ=int(p.GE1R.sum())
    lo,hi=wilson(succ,len(p))
    return {
        "n":len(q),
        "eligible":len(e),
        "eligible_GE1R":total,
        "eligible_base_GE1R":base,
        "too_fast_GE1R":int((q.b2_status=="TOO_FAST_GE1").sum()),
        "pass_n":len(p),
        "pass_rate_eligible":len(p)/len(e) if len(e) else np.nan,
        "pass_GE1R":succ,
        "pass_GE1R_precision":prec,
        "uplift_pp":100*(prec-base) if np.isfinite(prec) and np.isfinite(base) else np.nan,
        "retention_residual_GE1R":succ/total if total else np.nan,
        "wilson_lo":lo,"wilson_hi":hi,
    }

def main():
    Q=load_parent()

    signature=hashlib.sha256(
        json.dumps({
            "primary":"XP1_FAST_PROOF60",
            "time_to_0_5r_min_lte":FAST_MIN,
            "parent":"B40_S1_TRUE_SURVIVORS",
            "primary_outcome":"GE1R",
        },sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    rows=[]
    for candidate,role in [
        ("XP1_FAST_PROOF60","PRIMARY"),
        ("B1_NARROW_SOURCE_Q1","BENCHMARK"),
    ]:
        for per in ["DEV","REF"]:
            rows.append({
                "candidate":candidate,"role":role,"period":per,
                **whole_metric(Q[Q.period==per],candidate)
            })
    S=pd.DataFrame(rows)

    # Year metrics for whole-survivor candidates.
    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=Q[Q.year==y]
        if not len(q):continue
        for candidate,role in [
            ("XP1_FAST_PROOF60","PRIMARY"),
            ("B1_NARROW_SOURCE_Q1","BENCHMARK"),
        ]:
            Y.append({"year":y,"candidate":candidate,"role":role,**whole_metric(q,candidate)})
    Y=pd.DataFrame(Y)

    M=build_b2(Q)
    b2rows=[]
    for per in ["DEV","REF"]:
        b2rows.append({"period":per,**b2_metric(M[M.period==per])})
    B2=pd.DataFrame(b2rows)

    B2Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=M[M.year==y]
        if len(q):
            B2Y.append({"year":y,**b2_metric(q)})
    B2Y=pd.DataFrame(B2Y)

    # Hard frozen checks from S5.
    for per,exp in {
        "DEV":(500,476,337,24),
        "REF":(309,297,219,12),
    }.items():
        r=B2[B2.period==per].iloc[0]
        got=(int(r.n),int(r.eligible),int(r.eligible_GE1R),int(r.too_fast_GE1R))
        if got!=exp:
            raise RuntimeError(f"B2 S5 parity drift {per}: {got} != {exp}")

    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    B2.to_csv(ROOT/f"{PFX}_P5Benchmark.csv",index=False)
    B2Y.to_csv(ROOT/f"{PFX}_P5BenchmarkByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PRIMARY=XP1_FAST_PROOF60\n"
        f"PRIMARY_SIGNATURE_SHA256={signature}\n"
        f"FAST_PROOF_MIN_LTE={FAST_MIN:.1f}\n"
        f"NARROW_SOURCE_BASE_WIDTH_PCT_LTE={NARROW_CUT:.18f}\n"
        f"P5_RANGE_R_GT={P5_RANGE_CUT:.16f}\n"
        "PARENT=B40_S1_TRUE_SURVIVORS\n"
        "NO_COMBINATIONS=TRUE\nNO_THRESHOLD_SEARCH=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S6 — Frozen Expansion Candidate Validation","",
        f"Primary: **XP1_FAST_PROOF60** — +0.5R survival proof within <=60m.",
        f"Signature: `{signature}`","",
        "## Whole-survivor validation","",
        "| Candidate | Period | PASS | >=1R precision | Base | Uplift | >=1R retention | >=1.5R precision | >=2R precision | >=2R retention | Local-only in PASS |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.candidate} | {r.period} | {r.pass_n}/{r.n} ({fmt_pct(r.pass_rate)}) | "
            f"{r.GE1R_pass_success}/{r.pass_n} ({fmt_pct(r.GE1R_precision)}) | {fmt_pct(r.GE1R_base)} | "
            f"{fmt_num(r.GE1R_uplift_pp,1)}pp | {fmt_pct(r.GE1R_retention)} | "
            f"{fmt_pct(r.GE1_5R_precision)} | {fmt_pct(r.GE2R_precision)} | {fmt_pct(r.GE2R_retention)} | "
            f"{r.GE1R_local_only_false_positive}/{r.pass_n} ({fmt_pct(r.GE1R_local_only_rate_in_pass)}) |"
        )

    lines += ["","## XP1 yearly stability","",
              "| Year | PASS | >=1R precision | Base | Uplift | >=1.5R | >=2R | >=1R retention |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in Y[Y.candidate=="XP1_FAST_PROOF60"].itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.pass_n}/{r.n} | {fmt_pct(r.GE1R_precision)} | {fmt_pct(r.GE1R_base)} | "
            f"{fmt_num(r.GE1R_uplift_pp,1)}pp | {fmt_pct(r.GE1_5R_precision)} | {fmt_pct(r.GE2R_precision)} | "
            f"{fmt_pct(r.GE1R_retention)} |"
        )

    lines += ["","## Frozen strong-first-5m-range benchmark","",
              "| Period | Eligible | PASS | Residual >=1R precision | Base | Uplift | Residual >=1R retention | Too-fast >=1R excluded |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in B2.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.eligible} | {r.pass_n}/{r.eligible} ({fmt_pct(r.pass_rate_eligible)}) | "
            f"{r.pass_GE1R}/{r.pass_n} ({fmt_pct(r.pass_GE1R_precision)}) | {fmt_pct(r.eligible_base_GE1R)} | "
            f"{fmt_num(r.uplift_pp,1)}pp | {fmt_pct(r.retention_residual_GE1R)} | {r.too_fast_GE1R} |"
        )

    lines += ["","## Interpretation boundary",
        "XP1 is a post-survival expansion-state candidate: it becomes known only when +0.5 event-R has actually been reached.",
        "B1 and B2 are frozen benchmarks only and are not combined with XP1 in S6.",
        "S6 validates continuation probability; it does not yet define live entry, stop, or take-profit geometry.",
        "REF has already been inspected in earlier B40 stages and is confirmation data, not pristine OOS."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S6_FROZEN_EXPANSION_CANDIDATE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
