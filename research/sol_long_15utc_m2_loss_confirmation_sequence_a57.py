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

OUT_EVENTS = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_EVENTS.csv"
OUT_MOTIFS = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_MOTIFS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_BLOCKS.csv"
OUT_CONT = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_CONTINUOUS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_Status.txt"

PARTS = ("development", "external", "reference_validation")
WARNING_FAMILIES = ("W10", "W05")
GUARD_BY_WARNING = {"W10": "G3_POST_H10", "W05": "G2_POST_H05"}
EXPECTED_PARENT = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_WARNING = {
    "W10": {"development": 300, "external": 192, "reference_validation": 184},
    "W05": {"development": 219, "external": 148, "reference_validation": 138},
}
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12

MOTIFS = (
    "LOWER_CLOSE_1", "LOWER_HIGH_1", "RANGE_CONTRACT_1", "BODY_CONTRACT_1",
    "LOWER_HIGH_AND_CLOSE_1", "TWO_LOWER_CLOSES", "TWO_LOWER_HIGHS",
    "TWO_RANGE_CONTRACTIONS", "TWO_BODY_CONTRACTIONS", "TWO_NEAR_H10",
    "TWO_NEAR_H05", "H05_DEEPEN_FROM_H10",
)
CONT = (
    "close_H_R", "high_H_R", "low_H_R", "body_R", "abs_body_R", "range_R",
    "close_change_R", "high_change_R", "range_change_R",
)


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def fmt(v, d=3):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def ratio(a, b):
    if pd.isna(a) or pd.isna(b): return np.nan
    if b <= EPS: return np.inf if a > EPS else np.nan
    return float(a / b)


def bar_pos(index, ts):
    i = int(index.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(index) or index[i] != pd.Timestamp(ts):
        raise RuntimeError(f"timestamp missing: {ts}")
    return i


def terminal_label(r):
    if str(r.exit_reason) == "TARGET":
        return "RECOVER_E40", pd.Timestamp(r.exit_ts)
    if pd.notna(r.h1_break_ts) and pd.notna(r.invalidation_close_ts):
        return "FAILED_BREAK", pd.Timestamp(r.invalidation_close_ts)
    if str(r.exit_reason).startswith("TIME"):
        return "UNRESOLVED_TIME", pd.Timestamp(r.exit_ts)
    raise RuntimeError(f"unrecognized terminal {r.partition} {r.entry_ts} {r.exit_reason}")


def warning_features(x, r, warning_ts):
    i = bar_pos(x.index, warning_ts)
    if i < 2:
        raise RuntimeError(f"insufficient prior candles {warning_ts}")
    c0, c1, c2 = x.iloc[i], x.iloc[i-1], x.iloc[i-2]
    H, R = float(r.H), float(r.R)
    if R <= 0: raise RuntimeError("nonpositive R")

    def vals(c):
        o, h, lo, cl = map(float, [c.open, c.high, c.low, c.close])
        return o, h, lo, cl, h-lo, abs(cl-o)

    o0,h0,l0,cl0,r0,b0 = vals(c0)
    o1,h1,l1,cl1,r1,b1 = vals(c1)
    o2,h2,l2,cl2,r2,b2 = vals(c2)

    cur_h10 = H < cl0 <= H + 0.10*R + EPS
    prev_h10 = H < cl1 <= H + 0.10*R + EPS
    cur_h05 = H < cl0 <= H + 0.05*R + EPS
    prev_h05 = H < cl1 <= H + 0.05*R + EPS
    prev_upper_h10 = H + 0.05*R < cl1 <= H + 0.10*R + EPS

    out = {
        "close_H_R": (cl0-H)/R,
        "high_H_R": (h0-H)/R,
        "low_H_R": (l0-H)/R,
        "body_R": (cl0-o0)/R,
        "abs_body_R": b0/R,
        "range_R": r0/R,
        "close_change_R": (cl0-cl1)/R,
        "high_change_R": (h0-h1)/R,
        "range_change_R": (r0-r1)/R,
        "LOWER_CLOSE_1": bool(cl0 < cl1-EPS),
        "LOWER_HIGH_1": bool(h0 < h1-EPS),
        "RANGE_CONTRACT_1": bool(r0 <= r1+EPS),
        "BODY_CONTRACT_1": bool(b0 <= b1+EPS),
        "LOWER_HIGH_AND_CLOSE_1": bool(cl0 < cl1-EPS and h0 < h1-EPS),
        "TWO_LOWER_CLOSES": bool(cl0 < cl1-EPS and cl1 < cl2-EPS),
        "TWO_LOWER_HIGHS": bool(h0 < h1-EPS and h1 < h2-EPS),
        "TWO_RANGE_CONTRACTIONS": bool(r0 <= r1+EPS and r1 <= r2+EPS),
        "TWO_BODY_CONTRACTIONS": bool(b0 <= b1+EPS and b1 <= b2+EPS),
        "TWO_NEAR_H10": bool(cur_h10 and prev_h10),
        "TWO_NEAR_H05": bool(cur_h05 and prev_h05),
        "H05_DEEPEN_FROM_H10": bool(cur_h05 and prev_upper_h10),
    }
    return out


def build_events(x, m):
    rows=[]; errors=[]
    parent_counts={}
    for part in PARTS:
        q=a53.parent(m, part).copy()
        parent_counts[part]=len(q)
        if len(q)!=EXPECTED_PARENT[part]:
            errors.append(f"{part} parent {len(q)} != {EXPECTED_PARENT[part]}")
        for wf in WARNING_FAMILIES:
            n=0
            guard=GUARD_BY_WARNING[wf]
            for _,r in q.iterrows():
                g=a53.simulate(m, r, guard)
                if not bool(g["guard_exit"]):
                    continue
                n += 1
                wts=pd.Timestamp(g["warning_ts"])
                label, terminal_ts=terminal_label(r)
                # A53 target / terminal precedence must guarantee the warning is causal.
                if terminal_ts <= wts:
                    errors.append(f"noncausal {part} {wf} {r.entry_ts}: {wts} >= {terminal_ts}")
                    continue
                f=warning_features(x, r, wts)
                row={
                    "partition":part, "warning_family":wf, "dev_block":r.dev_block,
                    "execution_start":r.execution_start, "entry_ts":r.entry_ts,
                    "warning_ts":wts, "warning_known_ts":wts+BAR,
                    "terminal_label":label, "terminal_event_ts":terminal_ts,
                    "parent_exit_ts":r.exit_ts, "parent_exit_reason":r.exit_reason,
                    "parent_pnl":float(r.pnl), "parent_pnl_5bps":float(r.pnl_5bps),
                    "H":float(r.H), "L":float(r.L), "R":float(r.R),
                }
                row.update(f); rows.append(row)
            exp=EXPECTED_WARNING[wf][part]
            if n!=exp: errors.append(f"{part} {wf} warning {n} != {exp}")
    e=pd.DataFrame(rows)
    return e, errors, parent_counts


def cohort_stats(q, motif):
    fail=q[q.terminal_label=="FAILED_BREAK"]
    tar=q[q.terminal_label=="RECOVER_E40"]
    if len(fail)==0 or len(tar)==0:
        return {"fail_n":len(fail),"target_n":len(tar),"fail_hit":np.nan,"target_hit":np.nan,"gap":np.nan,"ratio":np.nan}
    fh=float(fail[motif].fillna(False).astype(bool).mean())
    th=float(tar[motif].fillna(False).astype(bool).mean())
    return {"fail_n":len(fail),"target_n":len(tar),"fail_hit":fh,"target_hit":th,"gap":fh-th,"ratio":ratio(fh,th)}


def dev_blocks(e, wf, motif):
    rows=[]; adequate=same=0
    q=e[(e.partition=="development")&(e.warning_family==wf)&(e.terminal_label.isin(["FAILED_BREAK","RECOVER_E40"]))]
    for bi in range(6):
        b=q[pd.to_numeric(q.dev_block,errors="coerce")==bi]
        s=cohort_stats(b,motif)
        ok=s["fail_n"]>=10 and s["target_n"]>=2
        if ok:
            adequate += 1
            if pd.notna(s["gap"]) and s["gap"]>0: same += 1
        rows.append({"warning_family":wf,"motif":motif,"dev_block":bi,"adequate":ok,**s})
    return rows,adequate,same


def analyze_motifs(e):
    rows=[]; block_rows=[]
    for wf in WARNING_FAMILIES:
        dev=e[(e.partition=="development")&(e.warning_family==wf)]
        for motif in MOTIFS:
            ds=cohort_stats(dev,motif)
            br,adequate,same=dev_blocks(e,wf,motif); block_rows.extend(br)
            dev_supported=bool(
                ds["fail_n"]>=80 and ds["target_n"]>=20 and
                pd.notna(ds["fail_hit"]) and ds["fail_hit"]>=0.30-EPS and
                ds["target_hit"]<=0.25+EPS and ds["gap"]>=0.20-EPS and
                ds["ratio"]>=2.0-EPS and adequate>=4 and same>=4
            )
            row={
                "warning_family":wf,"motif":motif,
                "dev_fail_n":ds["fail_n"],"dev_target_n":ds["target_n"],
                "dev_fail_hit":ds["fail_hit"],"dev_target_hit":ds["target_hit"],
                "dev_gap":ds["gap"],"dev_ratio":ds["ratio"],
                "adequate_dev_blocks":adequate,"same_direction_dev_blocks":same,
                "development_supported":dev_supported,
                "external_fail_n":np.nan,"external_target_n":np.nan,
                "external_fail_hit":np.nan,"external_target_hit":np.nan,"external_gap":np.nan,"external_ratio":np.nan,
                "reference_fail_n":np.nan,"reference_target_n":np.nan,
                "reference_fail_hit":np.nan,"reference_target_hit":np.nan,"reference_gap":np.nan,"reference_ratio":np.nan,
                "replicated":False,
            }
            if dev_supported:
                oos_ok=True
                for part,prefix in (("external","external"),("reference_validation","reference")):
                    s=cohort_stats(e[(e.partition==part)&(e.warning_family==wf)],motif)
                    for k,v in (("fail_n",s["fail_n"]),("target_n",s["target_n"]),("fail_hit",s["fail_hit"]),("target_hit",s["target_hit"]),("gap",s["gap"]),("ratio",s["ratio"])):
                        row[f"{prefix}_{k}"]=v
                    pp=bool(
                        s["fail_n"]>=40 and s["target_n"]>=15 and
                        pd.notna(s["fail_hit"]) and s["fail_hit"]>s["target_hit"] and
                        s["fail_hit"]>=0.20-EPS and s["target_hit"]<=0.35+EPS and
                        s["gap"]>=0.15-EPS and s["ratio"]>=1.5-EPS
                    )
                    oos_ok = oos_ok and pp
                row["replicated"]=bool(oos_ok)
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(block_rows)


def analyze_cont(e):
    rows=[]
    for part in PARTS:
        for wf in WARNING_FAMILIES:
            q=e[(e.partition==part)&(e.warning_family==wf)&(e.terminal_label.isin(["FAILED_BREAK","RECOVER_E40"]))]
            for f in CONT:
                a=pd.to_numeric(q.loc[q.terminal_label=="FAILED_BREAK",f],errors="coerce").dropna()
                b=pd.to_numeric(q.loc[q.terminal_label=="RECOVER_E40",f],errors="coerce").dropna()
                rows.append({
                    "partition":part,"warning_family":wf,"feature":f,
                    "fail_n":len(a),"target_n":len(b),
                    "fail_median":float(a.median()) if len(a) else np.nan,
                    "target_median":float(b.median()) if len(b) else np.nan,
                    "gap":float(a.median()-b.median()) if len(a) and len(b) else np.nan,
                })
    return pd.DataFrame(rows)


def outcome_counts(e):
    return e.groupby(["partition","warning_family","terminal_label"]).size().reset_index(name="n")


def write_result(e,motifs,blocks,cont,coverage,errors):
    replicated=motifs[motifs.replicated==True].copy() if len(motifs) else pd.DataFrame()
    if errors:
        status="SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_RECONCILIATION_FAIL"
    elif len(replicated):
        status="SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_SUPPORTED_FOR_A58"
    else:
        status="SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_INCONCLUSIVE"

    lines=[
        "# SOL LONG 15:00 UTC M2 Loss-Confirmation Sequence Anatomy — A57 Result","",
        f"Raw SOLUSDT 5m coverage: **{100.0*coverage:.4f}%**.","",
        "A57 inspects only the first frozen H10/H05 warning candle and the 1–2 completed candles immediately before it. No post-warning candle enters a motif.","",
        "## Reconciliation","",
        f"Rows: **{len(e)}**. Errors: **{len(errors)}**.","",
        "| Partition | Warning | Total | Failed-break | E40 target | Unresolved time |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for part in PARTS:
        for wf in WARNING_FAMILIES:
            q=e[(e.partition==part)&(e.warning_family==wf)]
            lines.append(f"| {part} | {wf} | {len(q)} | {int((q.terminal_label=='FAILED_BREAK').sum())} | {int((q.terminal_label=='RECOVER_E40').sum())} | {int((q.terminal_label=='UNRESOLVED_TIME').sum())} |")
    if errors:
        lines += ["","Validation errors:"]+[f"- {x}" for x in errors]

    lines += ["","## Replicated live-causal sequence motifs","",
              "| Warning | Motif | Dev fail/target | Dev gap | Dev ratio | Ext fail/target | Ext gap | RefVal fail/target | RefVal gap |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    if len(replicated):
        for _,r in replicated.sort_values(["warning_family","dev_gap"],ascending=[True,False]).iterrows():
            lines.append(
                f"| {r.warning_family} | {r.motif} | {pct(r.dev_fail_hit)} / {pct(r.dev_target_hit)} | {100*r.dev_gap:.1f}pp | {fmt(r.dev_ratio,2)}x | "
                f"{pct(r.external_fail_hit)} / {pct(r.external_target_hit)} | {100*r.external_gap:.1f}pp | "
                f"{pct(r.reference_fail_hit)} / {pct(r.reference_target_hit)} | {100*r.reference_gap:.1f}pp |"
            )
    else:
        lines.append("| - | No motif passed Development + both OOS gates | - | - | - | - | - | - | - |")

    lines += ["","## Strongest Development motifs","",
              "| Warning | Motif | Fail hit | Target hit | Gap | Ratio | Blocks | Dev supported | Replicated |",
              "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for wf in WARNING_FAMILIES:
        z=motifs[motifs.warning_family==wf].sort_values(["development_supported","dev_gap"],ascending=[False,False]).head(8)
        for _,r in z.iterrows():
            lines.append(f"| {wf} | {r.motif} | {pct(r.dev_fail_hit)} | {pct(r.dev_target_hit)} | {100*r.dev_gap:.1f}pp | {fmt(r.dev_ratio,2)}x | {int(r.same_direction_dev_blocks)}/{int(r.adequate_dev_blocks)} | {bool(r.development_supported)} | {bool(r.replicated)} |")

    lines += ["","## Report-only continuous warning-candle anatomy","",
              "These are diagnostics only; A57 does not derive a threshold from them.","",
              "| Partition | Warning | Feature | Fail median | E40 median | Gap |",
              "|---|---|---|---:|---:|---:|"]
    # concise: show close/high/body/range only
    for part in PARTS:
        for wf in WARNING_FAMILIES:
            z=cont[(cont.partition==part)&(cont.warning_family==wf)&(cont.feature.isin(["close_H_R","high_H_R","body_R","range_R"]))]
            for _,r in z.iterrows():
                lines.append(f"| {part} | {wf} | {r.feature} | {fmt(r.fail_median)} | {fmt(r.target_median)} | {fmt(r.gap)} |")

    lines += ["","## Decision","",f"**Status: {status}**",""
    ]
    if len(replicated):
        lines += ["A58 is authorized to simulate each replicated motif **standalone** as a next-open guard. No combinations or threshold retuning are authorized.",""]
    else:
        lines += ["No A58 sequence guard is authorized from this frozen motif family.",""]
    lines += ["Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    e,errors,_=build_events(x,m)
    motifs,blocks=analyze_motifs(e) if not errors else (pd.DataFrame(),pd.DataFrame())
    cont=analyze_cont(e) if len(e) else pd.DataFrame()
    e.to_csv(OUT_EVENTS,index=False)
    motifs.to_csv(OUT_MOTIFS,index=False)
    blocks.to_csv(OUT_BLOCKS,index=False)
    cont.to_csv(OUT_CONT,index=False)
    status=write_result(e,motifs,blocks,cont,coverage,errors)
    print(status)
    if errors:
        for xerr in errors: print("ERROR:",xerr)
        raise SystemExit(2)

if __name__ == "__main__":
    main()
