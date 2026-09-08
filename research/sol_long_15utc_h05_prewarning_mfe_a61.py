#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A53_PATH = Path(__file__).resolve().parent / "sol_long_15utc_executable_guard_a53.py"
spec = importlib.util.spec_from_file_location("a53", A53_PATH)
a53 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a53)
a2 = a53.a2

IN_COHORT = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_COHORT.csv"
OUT_EVENTS = ROOT / "SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_EVENTS.csv"
OUT_METRICS = ROOT / "SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_METRICS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_BLOCKS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_Status.txt"

PARTS = ("development", "external", "reference_validation")
FAIL = "FAILED_BREAK"
TARGET = "RECOVER_E40"
TIME = "UNRESOLVED_TIME"
EXPECTED_PARENT = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_COHORT = {"development": 219, "external": 148, "reference_validation": 138}
EXPECTED_FAIL = {"development": 184, "external": 113, "reference_validation": 107}
EXPECTED_TARGET = {"development": 31, "external": 32, "reference_validation": 29}
EXPECTED_TIME = {"development": 4, "external": 3, "reference_validation": 2}
EPS = 1e-12


def pct(x):
    return "-" if pd.isna(x) else f"{100.0*float(x):.1f}%"


def num(x, d=4):
    return "-" if pd.isna(x) else f"{float(x):.{d}f}"


def ratioval(a, b):
    if pd.isna(a) or pd.isna(b): return np.nan
    if b <= EPS: return np.inf if a > EPS else np.nan
    return float(a / b)


def ratiofmt(x):
    if pd.isna(x): return "-"
    if np.isinf(x): return "inf"
    return f"{float(x):.2f}x"


def bar_pos(idx, ts):
    t = pd.Timestamp(ts)
    i = int(idx.searchsorted(t, "left"))
    if i >= len(idx) or idx[i] != t:
        raise RuntimeError(f"timestamp parity failure: {t}")
    return i


def partition_metrics(q, threshold):
    f = q[q.outcome == FAIL]
    t = q[q.outcome == TARGET]
    u = q[q.outcome == TIME]
    fh = float((f.prewarning_mfe_R <= threshold).mean()) if len(f) else np.nan
    th = float((t.prewarning_mfe_R <= threshold).mean()) if len(t) else np.nan
    uh = float((u.prewarning_mfe_R <= threshold).mean()) if len(u) else np.nan
    return {
        "n": len(q), "fail_n": len(f), "target_n": len(t), "time_n": len(u),
        "fail_median_mfe_R": float(f.prewarning_mfe_R.median()) if len(f) else np.nan,
        "target_median_mfe_R": float(t.prewarning_mfe_R.median()) if len(t) else np.nan,
        "time_median_mfe_R": float(u.prewarning_mfe_R.median()) if len(u) else np.nan,
        "fail_hit_rate": fh, "target_hit_rate": th, "time_hit_rate": uh,
        "gap": fh-th if pd.notna(fh) and pd.notna(th) else np.nan,
        "ratio": ratioval(fh, th),
        "low_mfe_n": int((q.prewarning_mfe_R <= threshold).sum()),
        "low_mfe_rate": float((q.prewarning_mfe_R <= threshold).mean()) if len(q) else np.nan,
    }


def fail_result(status, errors):
    OUT_STATUS.write_text(status + "\n" + "\n".join(errors) + "\n", encoding="utf-8")
    lines = ["# SOL LONG 15:00 UTC H05 Pre-warning MFE — A61 Result", "", f"**Status: {status}**", ""]
    lines += [f"- {e}" for e in errors]
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    errors=[]
    if not IN_COHORT.exists():
        raise FileNotFoundError(IN_COHORT)

    c = pd.read_csv(IN_COHORT)
    required={"partition","dev_block","entry_ts","warning_ts","warning_known_ts","H","R","outcome"}
    miss=sorted(required-set(c.columns))
    if miss: errors.append(f"missing cohort columns {miss}")

    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    idx=m["idx"]; hi=m["high"]

    if not errors:
        for col in ("entry_ts","warning_ts","warning_known_ts"):
            c[col]=pd.to_datetime(c[col], utc=True, errors="coerce")
        c["H"]=pd.to_numeric(c.H, errors="coerce")
        c["R"]=pd.to_numeric(c.R, errors="coerce")
        if c[["entry_ts","warning_ts","warning_known_ts","H","R"]].isna().any().any():
            errors.append("missing/nonparseable cohort time or H/R")
        if (c.R <= 0).any(): errors.append("nonpositive R")

    rows=[]
    if not errors:
        for part in PARTS:
            cp=c[c.partition==part].copy()
            if len(cp)!=EXPECTED_COHORT[part]: errors.append(f"{part} cohort {len(cp)} != {EXPECTED_COHORT[part]}")
            for lab,exp in ((FAIL,EXPECTED_FAIL[part]),(TARGET,EXPECTED_TARGET[part]),(TIME,EXPECTED_TIME[part])):
                got=int((cp.outcome==lab).sum())
                if got!=exp: errors.append(f"{part} {lab} {got} != {exp}")

            parent=a53.parent(m, part).copy()
            if len(parent)!=EXPECTED_PARENT[part]: errors.append(f"{part} parent {len(parent)} != {EXPECTED_PARENT[part]}")
            parent["entry_ts_key"]=pd.to_datetime(parent.entry_ts, utc=True)
            if parent.entry_ts_key.duplicated().any():
                errors.append(f"{part} duplicate parent entry_ts")
                continue
            pmap={pd.Timestamp(r.entry_ts_key): r for _,r in parent.iterrows()}

            for _,r in cp.iterrows():
                et=pd.Timestamp(r.entry_ts); wt=pd.Timestamp(r.warning_ts); wkt=pd.Timestamp(r.warning_known_ts)
                pr=pmap.get(et)
                if pr is None:
                    errors.append(f"{part} no parent mapping {et}")
                    continue
                bt=pd.Timestamp(pr.h1_break_ts) if pd.notna(pr.h1_break_ts) else pd.NaT
                if pd.isna(bt):
                    errors.append(f"{part} missing breakout confirmation {et}")
                    continue
                start=max(et,bt)
                if start>wt:
                    errors.append(f"{part} start after warning {et}: {start}>{wt}")
                    continue
                if wkt != wt + pd.Timedelta(minutes=5):
                    errors.append(f"{part} warning-known parity {et}")
                    continue
                si=bar_pos(idx,start); wi=bar_pos(idx,wt)
                if wi<si:
                    errors.append(f"{part} bad bar order {et}")
                    continue
                mx=float(np.max(np.asarray(hi[si:wi+1],float)))
                mfe=(mx-float(r.H))/float(r.R)
                if not np.isfinite(mfe) or mfe < -EPS:
                    errors.append(f"{part} invalid MFE {et}: {mfe}")
                    continue
                rows.append({
                    "partition":part,"dev_block":r.dev_block,"entry_ts":et,
                    "breakout_confirmation_ts":bt,"measurement_start_ts":start,
                    "warning_ts":wt,"warning_known_ts":wkt,"outcome":r.outcome,
                    "H":float(r.H),"R":float(r.R),"prewarning_mfe_R":max(0.0,mfe),
                })

    ev=pd.DataFrame(rows)
    if not errors:
        if len(ev)!=sum(EXPECTED_COHORT.values()): errors.append(f"event rows {len(ev)} != 505")
        if ev.duplicated(["partition","entry_ts","warning_ts"]).any(): errors.append("duplicate mapped events")
        for part in PARTS:
            z=ev[ev.partition==part]
            f=int((z.outcome==FAIL).sum()); t=int((z.outcome==TARGET).sum())
            minf=180 if part=="development" else 100
            mint=30 if part=="development" else 25
            if f<minf or t<mint: errors.append(f"{part} support fail/target {f}/{t}")

    if errors:
        status="SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_RECONCILIATION_FAIL"
        fail_result(status,errors)
        raise RuntimeError("; ".join(errors[:20]))

    d=ev[ev.partition=="development"]
    med_fail=float(d[d.outcome==FAIL].prewarning_mfe_R.median())
    med_target=float(d[d.outcome==TARGET].prewarning_mfe_R.median())
    threshold=(med_fail+med_target)/2.0
    if not (np.isfinite(med_fail) and np.isfinite(med_target) and med_fail<med_target):
        errors.append(f"Development median direction fail={med_fail} target={med_target}")
    if not (np.isfinite(threshold) and threshold>0 and med_fail<threshold<med_target):
        errors.append(f"invalid threshold {threshold}")
    if errors:
        status="SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_RECONCILIATION_FAIL"
        fail_result(status,errors)
        raise RuntimeError("; ".join(errors))

    ev["low_mfe"] = ev.prewarning_mfe_R <= threshold
    metrics=[]
    for part in PARTS:
        z=ev[ev.partition==part]
        metrics.append({"partition":part,"threshold":threshold,**partition_metrics(z,threshold)})
    met=pd.DataFrame(metrics)

    blocks=[]
    for b in range(6):
        z=d[pd.to_numeric(d.dev_block,errors="coerce")==b]
        q=partition_metrics(z,threshold)
        adequate=bool(q["fail_n"]>=10 and q["target_n"]>=3)
        same=bool(adequate and q["fail_hit_rate"]>q["target_hit_rate"])
        blocks.append({"dev_block":b,"threshold":threshold,"adequate":adequate,"same_bad_direction":same,**q})
    bdf=pd.DataFrame(blocks)
    adequate=bdf[bdf.adequate.astype(bool)]
    same_n=int(adequate.same_bad_direction.astype(bool).sum())

    dm=met[met.partition=="development"].iloc[0]
    dev_pass=bool(
        dm.fail_hit_rate > dm.target_hit_rate and
        dm.gap >= 0.15-EPS and dm.ratio >= 1.35-EPS and dm.fail_hit_rate >= 0.50-EPS and
        len(adequate)>0 and same_n>=5
    )

    oos_pass={}
    for part in ("external","reference_validation"):
        z=met[met.partition==part].iloc[0]
        oos_pass[part]=bool(
            z.fail_hit_rate > z.target_hit_rate and z.gap >= 0.10-EPS and
            z.ratio >= 1.20-EPS and z.fail_hit_rate >= 0.45-EPS
        )

    if dev_pass and all(oos_pass.values()):
        status="SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_SUPPORTED_FOR_EXECUTABLE_TEST"
    elif dev_pass:
        status="SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_DEVELOPMENT_ONLY"
    else:
        status="SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_INCONCLUSIVE"

    ev.to_csv(OUT_EVENTS,index=False)
    met.to_csv(OUT_METRICS,index=False)
    bdf.to_csv(OUT_BLOCKS,index=False)
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")

    lines=[
        "# SOL LONG 15:00 UTC H05 Pre-warning MFE — A61 Result","",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
        "A61 evaluates one causal feature only: maximum favorable high extension from breakout confirmation (or entry if later) through the completed first POST_H05 warning bar.","",
        "## Frozen threshold","",
        f"- Development FAILED_BREAK median MFE: **{med_fail:.4f}R**",
        f"- Development RECOVER_E40 median MFE: **{med_target:.4f}R**",
        f"- Frozen midpoint threshold T: **{threshold:.4f}R**",
        "- LOW_MFE = prewarning_mfe_R <= T","",
        "## Partition replication","",
        "| Partition | Fail N | Target N | Fail median | Target median | Fail LOW_MFE | Target LOW_MFE | Gap | Ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _,r in met.iterrows():
        lines.append(f"| {r.partition} | {int(r.fail_n)} | {int(r.target_n)} | {num(r.fail_median_mfe_R)}R | {num(r.target_median_mfe_R)}R | {pct(r.fail_hit_rate)} | {pct(r.target_hit_rate)} | {pct(r.gap)} | {ratiofmt(r.ratio)} |")
    lines += ["","## Development block consistency","",
              "| Block | Fail N | Target N | Fail hit | Target hit | Adequate | Same bad direction |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in bdf.iterrows():
        lines.append(f"| {int(r.dev_block)} | {int(r.fail_n)} | {int(r.target_n)} | {pct(r.fail_hit_rate)} | {pct(r.target_hit_rate)} | {'yes' if r.adequate else 'no'} | {'yes' if r.same_bad_direction else 'no'} |")
    lines += ["",f"Adequate Development blocks with same bad direction: **{same_n}/{len(adequate)}**.","",
              "## Frozen gate decision","",
              f"- Development: **{'PASS' if dev_pass else 'FAIL'}**",
              f"- External: **{'PASS' if oos_pass['external'] else 'FAIL'}**",
              f"- Reference Validation: **{'PASS' if oos_pass['reference_validation'] else 'FAIL'}**","",
              "## Decision","",f"**Status: {status}**","" ]
    if status.endswith("SUPPORTED_FOR_EXECUTABLE_TEST"):
        lines.append("A61 authorizes one next experiment only: executable selective H05 exit at the next 5m open when G2_POST_H05 AND LOW_MFE, using this frozen T without retuning.")
    elif status.endswith("DEVELOPMENT_ONLY"):
        lines.append("The Development separation did not replicate in both untouched OOS partitions. Do not retune T or the MFE window.")
    else:
        lines.append("The preregistered Development gate failed. Do not rescue the hypothesis by moving T or changing the MFE window.")
    lines += ["","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
