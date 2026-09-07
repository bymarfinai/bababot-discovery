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

OUT_COHORT = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_COHORT.csv"
OUT_SNAP = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_SNAPSHOTS.csv"
OUT_CAND = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_CANDIDATES.csv"
OUT_DIAG = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_DIAGNOSTICS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_Status.txt"

BAR = pd.Timedelta(minutes=5)
HORIZON = pd.Timedelta(minutes=720)
PARTS = ("development", "external", "reference_validation")
EXPECTED_PARENT = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_COHORT = {"development": 219, "external": 148, "reference_validation": 138}
EXPECTED_TARGET = {"development": 31, "external": 32, "reference_validation": 29}
EXPECTED_FAIL = {"development": 184, "external": 113, "reference_validation": 107}
EXPECTED_UNRESOLVED = {"development": 4, "external": 3, "reference_validation": 2}
SNAPS = (5, 10, 15, 30)
CANDIDATES = (
    "C1_STILL_H05_5M",
    "C2_NOT_ABOVE_H10_5M",
    "C3_NO_CLOSE_ABOVE_H10_10M",
    "C4_STILL_H05_10M",
    "C5_NO_CLOSE_ABOVE_H10_15M",
)
HORIZON_BY_CAND = {
    "C1_STILL_H05_5M": 5,
    "C2_NOT_ABOVE_H10_5M": 5,
    "C3_NO_CLOSE_ABOVE_H10_10M": 10,
    "C4_STILL_H05_10M": 10,
    "C5_NO_CLOSE_ABOVE_H10_15M": 15,
}
EPS = 1e-12


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"

def bar_pos(idx, ts):
    i = int(idx.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(idx) or idx[i] != pd.Timestamp(ts):
        raise RuntimeError(f"timestamp parity failure: {ts}")
    return i


def terminal_label(m, r):
    idx = m["idx"]
    if str(r.exit_reason) == "TARGET":
        return "RECOVER_E40", bar_pos(idx, r.exit_ts)
    if pd.notna(r.h1_break_ts) and pd.notna(r.invalidation_close_ts):
        return "FAILED_BREAK", bar_pos(idx, r.invalidation_close_ts)
    if str(r.exit_reason).startswith("TIME"):
        end_ts = pd.Timestamp(r.execution_start) + HORIZON
        return "UNRESOLVED_TIME", bar_pos(idx, end_ts - BAR)
    raise RuntimeError(f"unrecognized frozen parent terminal: {r.partition} {r.entry_ts} {r.exit_reason}")


def state_and_features(m, r, wi, terminal_kind, terminal_i, mins):
    idx, hi, lo, cl = m["idx"], m["high"], m["low"], m["close"]
    H, R = float(r.H), float(r.R)
    oi = wi + mins // 5
    if oi >= len(idx): raise RuntimeError("snapshot beyond market")
    if terminal_i <= oi:
        state = "TARGET_BY_T" if terminal_kind == "RECOVER_E40" else "TERMINAL_FAIL_BY_T"
        alive = False
        latest_i = terminal_i
    else:
        alive = True
        latest_i = oi
        c = float(cl[latest_i])
        if c <= H + EPS:
            raise RuntimeError(f"alive snapshot has terminal close: {r.partition} {r.entry_ts} +{mins}")
        if c <= H + 0.05 * R + EPS:
            state = "ALIVE_H05"
        elif c <= H + 0.10 * R + EPS:
            state = "ALIVE_H10"
        else:
            state = "ALIVE_ABOVE_H10"

    path_end = min(oi, terminal_i)
    start = wi + 1
    if path_end >= start:
        s_hi = np.asarray(hi[start:path_end + 1], float)
        s_lo = np.asarray(lo[start:path_end + 1], float)
        s_cl = np.asarray(cl[start:path_end + 1], float)
        close_R = (float(cl[latest_i]) - H) / R
        run_high_R = max(0.0, (float(s_hi.max()) - H) / R)
        run_low_depth_R = max(0.0, (H - float(s_lo.min())) / R)
        n_h05 = int(((s_cl > H) & (s_cl <= H + 0.05 * R + EPS)).sum())
        n_h10 = int(((s_cl > H + 0.05 * R + EPS) & (s_cl <= H + 0.10 * R + EPS)).sum())
        n_above_h10 = int((s_cl > H + 0.10 * R + EPS).sum())
        close_above_h10 = bool((s_cl > H + 0.10 * R + EPS).any())
        high_touch_h10 = bool((s_hi >= H + 0.10 * R - EPS).any())
    else:
        close_R = np.nan; run_high_R = np.nan; run_low_depth_R = np.nan
        n_h05 = n_h10 = n_above_h10 = 0
        close_above_h10 = False; high_touch_h10 = False
    return {
        "snapshot_min": mins, "state": state, "alive": alive,
        "latest_close_R": close_R,
        "running_high_extension_R": run_high_R,
        "running_low_depth_R": run_low_depth_R,
        "closes_H05": n_h05, "closes_H10": n_h10, "closes_above_H10": n_above_h10,
        "close_above_H10_by_T": close_above_h10,
        "high_touch_H10_by_T": high_touch_h10,
    }


def analyze_primary(m, r, warning_ts):
    idx, cl = m["idx"], m["close"]
    wi = bar_pos(idx, warning_ts)
    outcome, ti = terminal_label(m, r)
    H, R = float(r.H), float(r.R)
    if outcome == "UNRESOLVED_TIME":
        return {
            "partition": r.partition, "dev_block": r.dev_block, "execution_start": r.execution_start,
            "entry_ts": r.entry_ts, "parent_exit_ts": r.exit_ts, "parent_exit_reason": r.exit_reason,
            "parent_pnl": float(r.pnl), "parent_pnl_5bps": float(r.pnl_5bps), "parent_loss_class": r.loss_class,
            "H": H, "L": float(r.L), "R": R,
            "warning_ts": idx[wi], "warning_known_ts": idx[wi] + BAR,
            "warning_close_R": (float(cl[wi]) - H) / R,
            "outcome": outcome, "terminal_event_ts": idx[ti], "terminal_known_ts": idx[ti] + BAR,
            "warning_to_terminal_min": float((idx[ti]-idx[wi])/pd.Timedelta(minutes=1)),
        }, [], {}

    if ti <= wi:
        raise RuntimeError(f"warning not before primary terminal {r.partition} {r.entry_ts}")

    def first_close(level):
        for i in range(wi + 1, ti + 1):
            if float(cl[i]) > level + EPS: return i
        return -1
    e05 = first_close(H + 0.05 * R)
    e10 = first_close(H + 0.10 * R)
    base = {
        "partition": r.partition, "dev_block": r.dev_block, "execution_start": r.execution_start,
        "entry_ts": r.entry_ts, "parent_exit_ts": r.exit_ts, "parent_exit_reason": r.exit_reason,
        "parent_pnl": float(r.pnl), "parent_pnl_5bps": float(r.pnl_5bps), "parent_loss_class": r.loss_class,
        "H": H, "L": float(r.L), "R": R,
        "warning_ts": idx[wi], "warning_known_ts": idx[wi] + BAR,
        "warning_close_R": (float(cl[wi]) - H) / R,
        "outcome": outcome,
        "terminal_event_ts": idx[ti], "terminal_known_ts": idx[ti] + BAR,
        "warning_to_terminal_min": float((idx[ti] - idx[wi]) / pd.Timedelta(minutes=1)),
        "first_escape_H05_ts": idx[e05] if e05 >= 0 else pd.NaT,
        "first_escape_H10_ts": idx[e10] if e10 >= 0 else pd.NaT,
        "first_fail_ts": idx[ti] if outcome == "FAILED_BREAK" else pd.NaT,
    }
    snaps=[]
    for sm in SNAPS:
        snaps.append({**base, **state_and_features(m, r, wi, outcome, ti, sm)})
    smap={z["snapshot_min"]:z for z in snaps}
    s5,s10,s15=smap[5],smap[10],smap[15]
    cands={
        "C1_STILL_H05_5M": bool(s5["alive"] and s5["state"]=="ALIVE_H05"),
        "C2_NOT_ABOVE_H10_5M": bool(s5["alive"] and s5["state"] in ("ALIVE_H05","ALIVE_H10")),
        "C3_NO_CLOSE_ABOVE_H10_10M": bool(s10["alive"] and not s10["close_above_H10_by_T"]),
        "C4_STILL_H05_10M": bool(s10["alive"] and s10["state"]=="ALIVE_H05"),
        "C5_NO_CLOSE_ABOVE_H10_15M": bool(s15["alive"] and not s15["close_above_H10_by_T"]),
    }
    return base, snaps, cands


def build(m):
    cohort=[]; snaps=[]; cand_rows=[]; parent_counts={}
    for part in PARTS:
        q=a53.parent(m,part); parent_counts[part]=len(q)
        for _,r in q.iterrows():
            g=a53.simulate(m,r,"G2_POST_H05")
            if not bool(g["guard_exit"]): continue
            base,ss,cc=analyze_primary(m,r,g["warning_ts"])
            cohort.append(base); snaps.extend(ss)
            for name,hit in cc.items():
                cand_rows.append({"partition":part,"dev_block":r.dev_block,"entry_ts":r.entry_ts,
                                  "outcome":base["outcome"],"candidate":name,"hit":bool(hit),
                                  "terminal_event_ts":base["terminal_event_ts"],
                                  "warning_known_ts":base["warning_known_ts"]})
    return pd.DataFrame(cohort),pd.DataFrame(snaps),pd.DataFrame(cand_rows),parent_counts


def validate(cohort,parent_counts):
    errors=[]
    for p in PARTS:
        if parent_counts.get(p)!=EXPECTED_PARENT[p]: errors.append(f"{p} parent {parent_counts.get(p)} != {EXPECTED_PARENT[p]}")
        q=cohort[cohort.partition==p]
        nt=int((q.outcome=="RECOVER_E40").sum()); nf=int((q.outcome=="FAILED_BREAK").sum()); nu=int((q.outcome=="UNRESOLVED_TIME").sum())
        if len(q)!=EXPECTED_COHORT[p]: errors.append(f"{p} cohort {len(q)} != {EXPECTED_COHORT[p]}")
        if nt!=EXPECTED_TARGET[p]: errors.append(f"{p} target {nt} != {EXPECTED_TARGET[p]}")
        if nf!=EXPECTED_FAIL[p]: errors.append(f"{p} fail {nf} != {EXPECTED_FAIL[p]}")
        if nu!=EXPECTED_UNRESOLVED[p]: errors.append(f"{p} unresolved {nu} != {EXPECTED_UNRESOLVED[p]}")
    if len(cohort)!=505: errors.append(f"total cohort {len(cohort)} != 505")
    if int((cohort.outcome=="RECOVER_E40").sum())!=92: errors.append("total target != 92")
    if int((cohort.outcome=="FAILED_BREAK").sum())!=404: errors.append("total fail != 404")
    if int((cohort.outcome=="UNRESOLVED_TIME").sum())!=9: errors.append("total unresolved != 9")
    return errors


def candidate_summary(cands,cohort):
    rows=[]
    for p in PARTS:
        for name in CANDIDATES:
            q=cands[(cands.partition==p)&(cands.candidate==name)]
            bad=q[q.outcome=="FAILED_BREAK"]; tar=q[q.outcome=="RECOVER_E40"]
            br=float(bad.hit.mean()) if len(bad) else np.nan
            tr=float(tar.hit.mean()) if len(tar) else np.nan
            ratio=np.inf if tr==0 and br>0 else (br/tr if tr>0 else np.nan)
            leads=[]
            for _,rr in bad[bad.hit].iterrows():
                cand_known=pd.Timestamp(rr.warning_known_ts)+pd.Timedelta(minutes=HORIZON_BY_CAND[name])
                terminal_known=pd.Timestamp(rr.terminal_event_ts)+BAR
                leads.append(float((terminal_known-cand_known)/pd.Timedelta(minutes=1)))
            rows.append({"partition":p,"candidate":name,"fail_n":len(bad),"target_n":len(tar),
                         "fail_hit_n":int(bad.hit.sum()),"target_hit_n":int(tar.hit.sum()),
                         "fail_hit_rate":br,"target_hit_rate":tr,"gap":br-tr,"ratio":ratio,
                         "median_lead_min":float(pd.Series(leads,dtype=float).median()) if leads else np.nan})
    out=pd.DataFrame(rows)
    dev_support={}
    for name in CANDIDATES:
        q=cands[(cands.partition=="development")&(cands.candidate==name)]
        same=0; adequate=0
        for bi in range(6):
            b=q[pd.to_numeric(q.dev_block,errors="coerce")==bi]
            bad=b[b.outcome=="FAILED_BREAK"]; tar=b[b.outcome=="RECOVER_E40"]
            if len(bad)>0 and len(tar)>0:
                adequate+=1
                if float(bad.hit.mean())>float(tar.hit.mean()): same+=1
        mask=(out.partition=="development")&(out.candidate==name)
        out.loc[mask,"adequate_blocks"]=adequate; out.loc[mask,"same_direction_blocks"]=same
        d=out[mask].iloc[0]
        dev_support[name]=bool(d.fail_hit_rate>=0.30-EPS and d.gap>=0.20-EPS and d.ratio>=1.50-EPS and same>=5 and d.median_lead_min>=5-EPS)
        out.loc[mask,"development_supported"]=dev_support[name]
    for name in CANDIDATES:
        replicated=dev_support[name]
        if replicated:
            for p in ("external","reference_validation"):
                z=out[(out.partition==p)&(out.candidate==name)].iloc[0]
                pp=bool(z.fail_hit_rate>z.target_hit_rate and z.gap>=0.15-EPS and z.ratio>=1.25-EPS and z.fail_hit_rate>=0.20-EPS)
                out.loc[(out.partition==p)&(out.candidate==name),"oos_pass"]=pp
                replicated=replicated and pp
        out.loc[out.candidate==name,"replicated"]=bool(replicated)
    return out


def diagnostics(snaps):
    rows=[]
    feats=("latest_close_R","running_high_extension_R","running_low_depth_R","closes_H05","closes_H10","closes_above_H10")
    for (p,sm),q in snaps.groupby(["partition","snapshot_min"],sort=False):
        for outcome in ("RECOVER_E40","FAILED_BREAK"):
            z=q[q.outcome==outcome]
            for state,rate in z.state.value_counts(normalize=True).items():
                rows.append({"partition":p,"snapshot_min":sm,"outcome":outcome,"kind":"STATE","feature":state,"n":len(z),"value":float(rate)})
            for f in feats:
                x=pd.to_numeric(z[f],errors="coerce").dropna()
                rows.append({"partition":p,"snapshot_min":sm,"outcome":outcome,"kind":"MEDIAN","feature":f,"n":len(x),"value":float(x.median()) if len(x) else np.nan})
    return pd.DataFrame(rows)


def choose_primary(summary):
    reps=[]
    for name in CANDIDATES:
        if bool(summary[summary.candidate==name].replicated.iloc[0]):
            d=summary[(summary.partition=="development")&(summary.candidate==name)].iloc[0]
            reps.append((HORIZON_BY_CAND[name],-float(d.gap),float(d.target_hit_rate),name))
    if not reps: return None
    reps.sort(); return reps[0][3]


def write_result(cohort,snaps,summary,coverage,errors,primary):
    status="SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_SUPPORTED_FOR_A55" if (not errors and primary is not None) else "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC Post-H05 Secondary Trigger Anatomy — A54 Result","",
           f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
           "A54 observes the frozen parent after the first live `POST_H05` warning. No exit is changed and no new price threshold is scanned.","",
           "## Reconciliation","",
           f"Total POST_H05 cohort: **{len(cohort)}** = **{int((cohort.outcome=='RECOVER_E40').sum())} TARGET + {int((cohort.outcome=='FAILED_BREAK').sum())} FAILED_BREAK + {int((cohort.outcome=='UNRESOLVED_TIME').sum())} quarantined TIME**. Errors: **{len(errors)}**.","",
           "| Partition | Total | TARGET | FAILED_BREAK | TIME quarantine | Median warning→target | Median warning→fail |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for p in PARTS:
        q=cohort[cohort.partition==p]; t=q[q.outcome=="RECOVER_E40"]; f=q[q.outcome=="FAILED_BREAK"]
        lines.append(f"| {p} | {len(q)} | {len(t)} | {len(f)} | {int((q.outcome=='UNRESOLVED_TIME').sum())} | {fmt(pd.to_numeric(t.warning_to_terminal_min,errors='coerce').median(),0)}m | {fmt(pd.to_numeric(f.warning_to_terminal_min,errors='coerce').median(),0)}m |")
    lines += ["","## Fixed actionable candidate discrimination","",
              "| Candidate | Part | Fail hit | Target hit | Gap | Ratio | Lead | Dev blocks | Replicated |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in CANDIDATES:
        for p in PARTS:
            r=summary[(summary.partition==p)&(summary.candidate==name)].iloc[0]
            blocks=f"{int(r.same_direction_blocks)}/{int(r.adequate_blocks)}" if p=="development" and pd.notna(r.get("same_direction_blocks",np.nan)) else "-"
            lines.append(f"| {name} | {p} | {pct(r.fail_hit_rate)} | {pct(r.target_hit_rate)} | {pct(r.gap)} | {fmt(r.ratio,2)}x | {fmt(r.median_lead_min,0)}m | {blocks} | {'YES' if bool(r.replicated) else 'no'} |")
    lines += ["","## Pooled post-warning state progression","",
              "| T | Outcome | terminal fail | target | alive H05 | alive H10 | alive >H10 |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    for sm in SNAPS:
        for outcome in ("FAILED_BREAK","RECOVER_E40"):
            q=snaps[(pd.to_numeric(snaps.snapshot_min,errors="coerce")==sm)&(snaps.outcome==outcome)]
            rates=q.state.value_counts(normalize=True)
            lines.append(f"| +{sm}m | {outcome} | {pct(rates.get('TERMINAL_FAIL_BY_T',0.0))} | {pct(rates.get('TARGET_BY_T',0.0))} | {pct(rates.get('ALIVE_H05',0.0))} | {pct(rates.get('ALIVE_H10',0.0))} | {pct(rates.get('ALIVE_ABOVE_H10',0.0))} |")
    reps=[n for n in CANDIDATES if bool(summary[summary.candidate==n].replicated.iloc[0])]
    lines += ["","## Decision","",f"Replicated actionable secondary triggers: **{', '.join(reps) if reps else 'none'}**.",""]
    if primary: lines += [f"Frozen earliest primary trigger for A55: **{primary}**.",""]
    lines += [f"**Status: {status}**","",
              "A54 is anatomy only. A supported candidate must be separately executed in A55 at the next available open; no live rule changes are authorized here.","",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    cohort,snaps,cands,parent_counts=build(m)
    errors=validate(cohort,parent_counts)
    cohort.to_csv(OUT_COHORT,index=False); snaps.to_csv(OUT_SNAP,index=False)
    summary=candidate_summary(cands,cohort); diag=diagnostics(snaps)
    summary.to_csv(OUT_CAND,index=False); diag.to_csv(OUT_DIAG,index=False)
    primary=choose_primary(summary) if not errors else None
    status=write_result(cohort,snaps,summary,coverage,errors,primary)
    print(status)
    if errors: raise RuntimeError("; ".join(errors))

if __name__=="__main__": main()
