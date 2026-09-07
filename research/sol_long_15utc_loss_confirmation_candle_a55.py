#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A17_PATH = Path(__file__).resolve().parent / "sol_long_multi_clock_expansion_a17.py"
spec = importlib.util.spec_from_file_location("a17", A17_PATH)
a17 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a17)
a4 = a17.a4; a3 = a4.a3; a2 = a17.a2

OUT_PAIRS = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_PAIRS.csv"
OUT_CONT = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_CONTINUOUS.csv"
OUT_BIN = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_BINARY.csv"
OUT_COV = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_COVERAGE.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_Status.txt"

REF_MIN = 360
HOUR = 15
BAR = pd.Timedelta(minutes=5)
PARTS = ("development", "external", "reference_validation")
LEADS = (15, 10, 5)
EXPECTED_PARENT = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_LOSS = {"development": 357, "external": 166, "reference_validation": 187}
EXPECTED_M0 = {"development": 37, "external": 13, "reference_validation": 26}
EXPECTED_M2 = {"development": 262, "external": 137, "reference_validation": 140}
EPS = 1e-12

CONT_FEATURES = (
    "body_R", "abs_body_R", "range_R", "upper_wick_R", "lower_wick_R",
    "close_location", "body_fraction", "upper_wick_fraction", "lower_wick_fraction",
    "close_H_R", "high_H_R", "low_H_R", "close_L_R",
    "close_change_R", "high_change_R", "low_change_R", "range_change_R", "close_location_change",
)
BIN_FEATURES = (
    "BEARISH", "LOWER_CLOSE", "LOWER_HIGH", "LOWER_LOW", "INSIDE_BAR", "OUTSIDE_BAR",
    "M2_CLOSE_H05", "M2_CLOSE_H10", "M0_CLOSE_L25", "M0_CLOSE_L10",
)


def fmt(v, d=3):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"

def ratio(a, b):
    if pd.isna(a) or pd.isna(b): return np.nan
    if b <= EPS: return np.inf if a > EPS else np.nan
    return float(a / b)

def bar_pos(idx, ts):
    i = int(idx.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(idx) or idx[i] != pd.Timestamp(ts):
        return -1
    return i


def parent(m, part):
    q = a17.simulate_cell(m, part, REF_MIN, HOUR, "A55", "CENTRAL").copy()
    if q.empty: return q
    q["loss_class"] = [a3.loss_class(r) for _, r in q.iterrows()]
    q["economic_win"] = pd.to_numeric(q.pnl, errors="coerce") > 0
    q["mechanism"] = "OTHER"
    loss = ~q.economic_win
    has_inv = q.invalidation_close_ts.notna()
    has_break = q.h1_break_ts.notna()
    q.loc[loss & has_inv & ~has_break, "mechanism"] = "M0_REFERENCE_INVALIDATION"
    q.loc[loss & has_inv & has_break, "mechanism"] = "M2_FAILED_BREAK"
    q.loc[loss & ~has_inv, "mechanism"] = "M1_TIME_NO_STRUCTURAL_FAIL"
    q.loc[q.economic_win, "mechanism"] = "ECONOMIC_POSITIVE"
    return q.sort_values("entry_ts").reset_index(drop=True)


def candle_features(x, ts, H, L, R, mechanism):
    i = bar_pos(x.index, ts)
    if i <= 0: raise RuntimeError(f"missing candle/previous candle {ts}")
    c = x.iloc[i]; p = x.iloc[i-1]
    o, h, lo, cl = map(float, [c.open, c.high, c.low, c.close])
    po, ph, plo, pcl = map(float, [p.open, p.high, p.low, p.close])
    rng = h-lo; prng = ph-plo
    body = cl-o
    upper = h-max(o,cl); lower = min(o,cl)-lo
    loc = (cl-lo)/rng if rng > EPS else 0.5
    ploc = (pcl-plo)/prng if prng > EPS else 0.5
    return {
        "body_R": body/R,
        "abs_body_R": abs(body)/R,
        "range_R": rng/R,
        "upper_wick_R": upper/R,
        "lower_wick_R": lower/R,
        "close_location": loc,
        "body_fraction": abs(body)/rng if rng > EPS else 0.0,
        "upper_wick_fraction": upper/rng if rng > EPS else 0.0,
        "lower_wick_fraction": lower/rng if rng > EPS else 0.0,
        "close_H_R": (cl-H)/R,
        "high_H_R": (h-H)/R,
        "low_H_R": (lo-H)/R,
        "close_L_R": (cl-L)/R,
        "close_change_R": (cl-pcl)/R,
        "high_change_R": (h-ph)/R,
        "low_change_R": (lo-plo)/R,
        "range_change_R": (rng-prng)/R,
        "close_location_change": loc-ploc,
        "BEARISH": bool(cl < o-EPS),
        "LOWER_CLOSE": bool(cl < pcl-EPS),
        "LOWER_HIGH": bool(h < ph-EPS),
        "LOWER_LOW": bool(lo < plo-EPS),
        "INSIDE_BAR": bool(h <= ph+EPS and lo >= plo-EPS),
        "OUTSIDE_BAR": bool(h >= ph-EPS and lo <= plo+EPS),
        "M2_CLOSE_H05": bool(mechanism=="M2_FAILED_BREAK" and cl > H+EPS and cl <= H+0.05*R+EPS),
        "M2_CLOSE_H10": bool(mechanism=="M2_FAILED_BREAK" and cl > H+EPS and cl <= H+0.10*R+EPS),
        "M0_CLOSE_L25": bool(mechanism=="M0_REFERENCE_INVALIDATION" and cl >= L-EPS and cl <= L+0.25*R+EPS),
        "M0_CLOSE_L10": bool(mechanism=="M0_REFERENCE_INVALIDATION" and cl >= L-EPS and cl <= L+0.10*R+EPS),
    }


def control_live_and_state(r, ts, mechanism):
    ts = pd.Timestamp(ts)
    if ts < pd.Timestamp(r.entry_ts): return False
    if pd.Timestamp(r.exit_ts) <= ts: return False
    if pd.notna(r.invalidation_close_ts) and pd.Timestamp(r.invalidation_close_ts) <= ts: return False
    br = pd.Timestamp(r.h1_break_ts) if pd.notna(r.h1_break_ts) else pd.NaT
    if mechanism == "M2_FAILED_BREAK":
        return bool(pd.notna(br) and br <= ts)
    if mechanism == "M0_REFERENCE_INVALIDATION":
        return bool(pd.isna(br) or br > ts)
    return False


def eligible_loss_snapshot(r, lead):
    if pd.isna(r.invalidation_close_ts): return None
    fail_ts = pd.Timestamp(r.invalidation_close_ts)
    ts = fail_ts - pd.Timedelta(minutes=int(lead))
    if ts < pd.Timestamp(r.entry_ts): return None
    br = pd.Timestamp(r.h1_break_ts) if pd.notna(r.h1_break_ts) else pd.NaT
    if r.mechanism == "M2_FAILED_BREAK" and (pd.isna(br) or br > ts): return None
    if r.mechanism == "M0_REFERENCE_INVALIDATION" and pd.notna(br) and br <= ts: return None
    age = int((ts - pd.Timestamp(r.entry_ts)) / pd.Timedelta(minutes=1))
    return ts, age


def choose_control(qpos, lossrow, age_min, mechanism, x):
    candidates=[]
    for _, w in qpos.iterrows():
        if str(lossrow.partition)=="development":
            lb = pd.to_numeric(pd.Series([lossrow.dev_block]), errors="coerce").iloc[0]
            wb = pd.to_numeric(pd.Series([w.dev_block]), errors="coerce").iloc[0]
            if pd.isna(lb) or pd.isna(wb) or int(lb)!=int(wb): continue
        ts = pd.Timestamp(w.entry_ts) + pd.Timedelta(minutes=int(age_min))
        if bar_pos(x.index, ts) <= 0: continue
        if not control_live_and_state(w, ts, mechanism): continue
        dist = abs((pd.Timestamp(w.execution_start)-pd.Timestamp(lossrow.execution_start)).total_seconds())
        candidates.append((dist, pd.Timestamp(w.execution_start), pd.Timestamp(w.entry_ts), w, ts))
    if not candidates: return None
    candidates.sort(key=lambda z:(z[0],z[1],z[2]))
    return candidates[0][3], candidates[0][4]


def build_pairs(m, x):
    parents={p:parent(m,p) for p in PARTS}
    errors=[]
    for p,q in parents.items():
        if len(q)!=EXPECTED_PARENT[p]: errors.append(f"{p} parent {len(q)} != {EXPECTED_PARENT[p]}")
        if int((~q.economic_win).sum())!=EXPECTED_LOSS[p]: errors.append(f"{p} losses mismatch")
        if int((q.mechanism=="M0_REFERENCE_INVALIDATION").sum())!=EXPECTED_M0[p]: errors.append(f"{p} M0 mismatch")
        if int((q.mechanism=="M2_FAILED_BREAK").sum())!=EXPECTED_M2[p]: errors.append(f"{p} M2 mismatch")
    if errors: raise RuntimeError("; ".join(errors))

    rows=[]; cov=[]
    for p in PARTS:
        q=parents[p]
        pos=q[q.economic_win].copy()
        for mech in ("M2_FAILED_BREAK","M0_REFERENCE_INVALIDATION"):
            losses=q[q.mechanism==mech].copy()
            for lead in LEADS:
                eligible=matched=0
                for _,r in losses.iterrows():
                    e=eligible_loss_snapshot(r,lead)
                    if e is None: continue
                    loss_ts, age=e; eligible += 1
                    ctl=choose_control(pos,r,age,mech,x)
                    if ctl is None: continue
                    w, ctl_ts=ctl; matched += 1
                    lf=candle_features(x,loss_ts,float(r.H),float(r.L),float(r.R),mech)
                    wf=candle_features(x,ctl_ts,float(w.H),float(w.L),float(w.R),mech)
                    z={
                        "partition":p,"mechanism":mech,"lead_min":lead,
                        "loss_entry_ts":r.entry_ts,"loss_execution_start":r.execution_start,"loss_dev_block":r.dev_block,
                        "loss_snapshot_ts":loss_ts,"loss_failure_ts":r.invalidation_close_ts,"loss_age_min":age,
                        "loss_class":r.loss_class,"loss_pnl":float(r.pnl),
                        "control_entry_ts":w.entry_ts,"control_execution_start":w.execution_start,"control_dev_block":w.dev_block,
                        "control_snapshot_ts":ctl_ts,"control_exit_ts":w.exit_ts,"control_exit_reason":w.exit_reason,"control_pnl":float(w.pnl),
                    }
                    for f in CONT_FEATURES+BIN_FEATURES:
                        z[f"loss__{f}"]=lf[f]; z[f"control__{f}"]=wf[f]
                    rows.append(z)
                cov.append({"partition":p,"mechanism":mech,"lead_min":lead,"loss_n":len(losses),"eligible_n":eligible,"matched_n":matched,
                            "eligible_rate":eligible/len(losses) if len(losses) else np.nan,
                            "match_rate":matched/eligible if eligible else np.nan})
    pairs=pd.DataFrame(rows)
    coverage=pd.DataFrame(cov)
    return pairs,coverage


def cont_stats(q, f):
    a=pd.to_numeric(q[f"loss__{f}"],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    b=pd.to_numeric(q[f"control__{f}"],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    n=min(len(a),len(b))
    if n==0: return {"n":0,"loss_med":np.nan,"control_med":np.nan,"gap":np.nan,"effect":np.nan}
    lm=float(a.median()); cm=float(b.median()); gap=lm-cm
    ai=float(a.quantile(.75)-a.quantile(.25)); bi=float(b.quantile(.75)-b.quantile(.25)); den=(ai+bi)/2
    eff=abs(gap)/den if den>EPS else (np.inf if abs(gap)>EPS else 0.0)
    return {"n":n,"loss_med":lm,"control_med":cm,"gap":gap,"effect":eff}

def bin_stats(q,f):
    if len(q)==0: return {"n":0,"loss_hit":np.nan,"control_hit":np.nan,"gap":np.nan,"ratio":np.nan}
    a=q[f"loss__{f}"].fillna(False).astype(bool); b=q[f"control__{f}"].fillna(False).astype(bool)
    ah=float(a.mean()); bh=float(b.mean())
    return {"n":len(q),"loss_hit":ah,"control_hit":bh,"gap":ah-bh,"ratio":ratio(ah,bh)}


def block_cont(q,f,sign,mech):
    adequate=same=0
    for bi in range(6):
        b=q[pd.to_numeric(q.loss_dev_block,errors="coerce")==bi]
        s=cont_stats(b,f)
        if s["n"]>=5:
            adequate+=1
            if sign!=0 and pd.notna(s["gap"]) and int(np.sign(s["gap"]))==sign: same+=1
    ok=(adequate>=5 and same>=5) if mech=="M2_FAILED_BREAK" else (adequate>=3 and same==adequate)
    return adequate,same,ok

def block_bin(q,f,mech):
    adequate=same=0
    for bi in range(6):
        b=q[pd.to_numeric(q.loss_dev_block,errors="coerce")==bi]
        s=bin_stats(b,f)
        if s["n"]>=5:
            adequate+=1
            if pd.notna(s["gap"]) and s["gap"]>0: same+=1
    ok=(adequate>=5 and same>=5) if mech=="M2_FAILED_BREAK" else (adequate>=3 and same==adequate)
    return adequate,same,ok


def analyze_cont(pairs):
    rows=[]
    for mech in ("M2_FAILED_BREAK","M0_REFERENCE_INVALIDATION"):
      for lead in LEADS:
        devq=pairs[(pairs.partition=="development")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
        for f in CONT_FEATURES:
            ds=cont_stats(devq,f); sign=int(np.sign(ds["gap"])) if pd.notna(ds["gap"]) else 0
            adequate,same,block_ok=block_cont(devq,f,sign,mech)
            min_dev=40 if mech=="M2_FAILED_BREAK" else 20
            dev_eligible=bool(ds["n"]>=min_dev and pd.notna(ds["effect"]) and ds["effect"]>=.30 and block_ok)
            es=rs={"n":0,"loss_med":np.nan,"control_med":np.nan,"gap":np.nan,"effect":np.nan}
            replicated=False
            if dev_eligible:
                eq=pairs[(pairs.partition=="external")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
                rq=pairs[(pairs.partition=="reference_validation")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
                es=cont_stats(eq,f); rs=cont_stats(rq,f)
                min_oos=20 if mech=="M2_FAILED_BREAK" else 8
                replicated=bool(sign!=0 and es["n"]>=min_oos and rs["n"]>=min_oos
                                and pd.notna(es["gap"]) and int(np.sign(es["gap"]))==sign and es["effect"]>=.10
                                and pd.notna(rs["gap"]) and int(np.sign(rs["gap"]))==sign and rs["effect"]>=.10)
            rows.append({"mechanism":mech,"lead_min":lead,"feature":f,
                         "dev_n":ds["n"],"dev_loss_median":ds["loss_med"],"dev_control_median":ds["control_med"],"dev_gap":ds["gap"],"dev_effect":ds["effect"],
                         "adequate_dev_blocks":adequate,"same_sign_dev_blocks":same,"dev_eligible":dev_eligible,
                         "external_n":es["n"],"external_loss_median":es["loss_med"],"external_control_median":es["control_med"],"external_gap":es["gap"],"external_effect":es["effect"],
                         "reference_n":rs["n"],"reference_loss_median":rs["loss_med"],"reference_control_median":rs["control_med"],"reference_gap":rs["gap"],"reference_effect":rs["effect"],
                         "replicated":replicated})
    return pd.DataFrame(rows)


def analyze_bin(pairs):
    rows=[]
    for mech in ("M2_FAILED_BREAK","M0_REFERENCE_INVALIDATION"):
      for lead in LEADS:
        devq=pairs[(pairs.partition=="development")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
        for f in BIN_FEATURES:
            if mech=="M2_FAILED_BREAK" and f.startswith("M0_"): continue
            if mech=="M0_REFERENCE_INVALIDATION" and f.startswith("M2_"): continue
            ds=bin_stats(devq,f); adequate,same,block_ok=block_bin(devq,f,mech)
            min_hit=.40 if mech=="M2_FAILED_BREAK" else .30
            dev_eligible=bool(ds["n"]>0 and ds["loss_hit"]>=min_hit and ds["gap"]>=.20 and ds["ratio"]>=1.50 and block_ok)
            es=rs={"n":0,"loss_hit":np.nan,"control_hit":np.nan,"gap":np.nan,"ratio":np.nan}
            replicated=False
            if dev_eligible:
                eq=pairs[(pairs.partition=="external")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
                rq=pairs[(pairs.partition=="reference_validation")&(pairs.mechanism==mech)&(pairs.lead_min==lead)]
                es=bin_stats(eq,f); rs=bin_stats(rq,f)
                min_oos=.20 if mech=="M2_FAILED_BREAK" else .15
                replicated=bool(es["n"]>0 and rs["n"]>0
                                and es["loss_hit"]>=min_oos and es["gap"]>=.10 and es["ratio"]>=1.25
                                and rs["loss_hit"]>=min_oos and rs["gap"]>=.10 and rs["ratio"]>=1.25)
            rows.append({"mechanism":mech,"lead_min":lead,"feature":f,
                         "dev_n":ds["n"],"dev_loss_hit":ds["loss_hit"],"dev_control_hit":ds["control_hit"],"dev_gap":ds["gap"],"dev_ratio":ds["ratio"],
                         "adequate_dev_blocks":adequate,"same_bad_dev_blocks":same,"dev_eligible":dev_eligible,
                         "external_n":es["n"],"external_loss_hit":es["loss_hit"],"external_control_hit":es["control_hit"],"external_gap":es["gap"],"external_ratio":es["ratio"],
                         "reference_n":rs["n"],"reference_loss_hit":rs["loss_hit"],"reference_control_hit":rs["control_hit"],"reference_gap":rs["gap"],"reference_ratio":rs["ratio"],
                         "replicated":replicated})
    return pd.DataFrame(rows)


def control_reuse(pairs):
    if pairs.empty: return pd.DataFrame()
    z=pairs.groupby(["partition","mechanism","lead_min","control_entry_ts"]).size().reset_index(name="uses")
    return z.groupby(["partition","mechanism","lead_min"]).agg(unique_controls=("control_entry_ts","nunique"),max_control_reuse=("uses","max"),mean_control_reuse=("uses","mean")).reset_index()


def main():
    x,coverage_raw=a2.a1.load5()
    m=a2.make_market_with_open(x)
    pairs,cov=build_pairs(m,x)
    pairs.to_csv(OUT_PAIRS,index=False)
    reuse=control_reuse(pairs)
    cov=cov.merge(reuse,on=["partition","mechanism","lead_min"],how="left")
    cov.to_csv(OUT_COV,index=False)
    cont=analyze_cont(pairs); binary=analyze_bin(pairs)
    cont.to_csv(OUT_CONT,index=False); binary.to_csv(OUT_BIN,index=False)

    rc=cont[cont.replicated==True].copy() if len(cont) else pd.DataFrame()
    rb=binary[binary.replicated==True].copy() if len(binary) else pd.DataFrame()
    candidates=[]
    for _,r in rb.iterrows(): candidates.append((int(r.lead_min),0,-float(r.dev_gap),"BINARY",str(r.mechanism),str(r.feature)))
    for _,r in rc.iterrows(): candidates.append((int(r.lead_min),1,-float(r.dev_effect),"CONTINUOUS",str(r.mechanism),str(r.feature)))
    candidates.sort(key=lambda z:(-z[0],z[1],z[2],z[4],z[5]))
    primary=candidates[0] if candidates else None
    status="SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_SUPPORTED_FOR_A56" if primary else "SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_INCONCLUSIVE"
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")

    lines=["# SOL LONG 15:00 UTC Loss Confirmation Candle Anatomy — A55 Result","",
           "A55 compares fixed pre-terminal completed candles with deterministic same-age, same-state eventual-positive parent controls. No exit is changed and no continuous threshold is scanned.","",
           f"Raw SOLUSDT 5m coverage: **{100*coverage_raw:.4f}%**.","",
           "## Matched snapshot coverage","",
           "| Part | Mechanism | Lead | Loss N | Eligible | Matched | Match/eligible | Unique controls | Max reuse |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in cov.iterrows():
        lines.append(f"| {r.partition} | {r.mechanism} | {int(r.lead_min)}m | {int(r.loss_n)} | {int(r.eligible_n)} | {int(r.matched_n)} | {pct(r.match_rate)} | {int(r.unique_controls) if pd.notna(r.unique_controls) else 0} | {int(r.max_control_reuse) if pd.notna(r.max_control_reuse) else 0} |")

    lines += ["","## Replicated binary candle states",""]
    if len(rb):
        lines += ["| Mechanism | Lead | Feature | Dev loss/control | Gap | Ratio | External loss/control | RefVal loss/control |",
                  "|---|---:|---|---:|---:|---:|---:|---:|"]
        for _,r in rb.sort_values(["lead_min","dev_gap"],ascending=[False,False]).iterrows():
            lines.append(f"| {r.mechanism} | {int(r.lead_min)}m | {r.feature} | {pct(r.dev_loss_hit)} / {pct(r.dev_control_hit)} | {100*r.dev_gap:.1f}pp | {fmt(r.dev_ratio,2)}x | {pct(r.external_loss_hit)} / {pct(r.external_control_hit)} | {pct(r.reference_loss_hit)} / {pct(r.reference_control_hit)} |")
    else: lines.append("None.")

    lines += ["","## Replicated continuous candle characteristics",""]
    if len(rc):
        lines += ["| Mechanism | Lead | Feature | Dev loss/control med | Effect | External effect | RefVal effect |",
                  "|---|---:|---|---:|---:|---:|---:|"]
        for _,r in rc.sort_values(["lead_min","dev_effect"],ascending=[False,False]).iterrows():
            lines.append(f"| {r.mechanism} | {int(r.lead_min)}m | {r.feature} | {fmt(r.dev_loss_median)} / {fmt(r.dev_control_median)} | {fmt(r.dev_effect)} | {fmt(r.external_effect)} | {fmt(r.reference_effect)} |")
    else: lines.append("None.")

    lines += ["","## Strongest Development diagnostics (not automatically valid OOS)",""]
    topb=binary.sort_values(["dev_eligible","dev_gap"],ascending=[False,False]).head(10)
    lines += ["### Binary","","| Mechanism | Lead | Feature | Loss hit | Control hit | Gap | Blocks | Dev eligible | Replicated |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in topb.iterrows():
        lines.append(f"| {r.mechanism} | {int(r.lead_min)}m | {r.feature} | {pct(r.dev_loss_hit)} | {pct(r.dev_control_hit)} | {100*r.dev_gap:.1f}pp | {int(r.same_bad_dev_blocks)}/{int(r.adequate_dev_blocks)} | {'yes' if r.dev_eligible else 'no'} | {'yes' if r.replicated else 'no'} |")
    topc=cont.sort_values(["dev_eligible","dev_effect"],ascending=[False,False]).head(10)
    lines += ["","### Continuous","","| Mechanism | Lead | Feature | Loss med | Control med | Effect | Blocks | Dev eligible | Replicated |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in topc.iterrows():
        lines.append(f"| {r.mechanism} | {int(r.lead_min)}m | {r.feature} | {fmt(r.dev_loss_median)} | {fmt(r.dev_control_median)} | {fmt(r.dev_effect)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {'yes' if r.dev_eligible else 'no'} | {'yes' if r.replicated else 'no'} |")

    lines += ["","## Decision",""]
    if primary:
        lead,_,_,kind,mech,feat=primary
        lines.append(f"Primary replicated Loss Confirmation Candle characteristic: **{kind} / {mech} / {feat} at {lead}m pre-terminal lead**.")
        lines.append("")
        lines.append("This is an anatomy result only. A56 must test causal next-open economics; no live exit is authorized by A55.")
    else:
        lines.append("No preregistered candle characteristic replicated strongly enough to qualify as a Loss Confirmation Candle.")
    lines += ["",f"**Status: {status}**","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("coverage",coverage_raw,"pairs",len(pairs),"rep_bin",len(rb),"rep_cont",len(rc),"status",status)

if __name__=="__main__": main()
