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

OUT_COHORT = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_COHORT.csv"
OUT_SNAP = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_SNAPSHOTS.csv"
OUT_CAND = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_CANDIDATES.csv"
OUT_DIAG = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_DIAGNOSTICS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_Status.txt"

REF_MIN = 360
HOUR = 15
TARGET_R = 0.40
BAR = pd.Timedelta(minutes=5)
HORIZON = pd.Timedelta(minutes=720)
PARTS = ("development", "external", "reference_validation")
EXPECTED_PARENT = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_COHORT = {"development": 219, "external": 148, "reference_validation": 138}
EXPECTED_WIN = {"development": 37, "external": 38, "reference_validation": 32}
EXPECTED_FAIL = {"development": 182, "external": 110, "reference_validation": 106}
SNAPS = (5, 10, 15, 30)
CANDIDATES = (
    "C1_STILL_H05_5M",
    "C2_NOT_ABOVE_H10_5M",
    "C3_NO_CLOSE_ABOVE_H10_10M",
    "C4_STILL_H05_10M",
    "C5_NO_CLOSE_ABOVE_H10_15M",
)
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


def parent(m, part):
    q = a17.simulate_cell(m, part, REF_MIN, HOUR, "A54", "CENTRAL").copy()
    if q.empty: return q
    q["loss_class"] = [a3.loss_class(r) for _, r in q.iterrows()]
    return q.sort_values("entry_ts").reset_index(drop=True)


def is_post_h05(close_i, H, R):
    return bool(close_i > H + EPS and close_i <= H + 0.05 * R + EPS)


def find_post_h05(m, r):
    """Exact A53 G2 warning opportunity, but observe rather than exit."""
    idx, hi, cl = m["idx"], m["high"], m["close"]
    ei = bar_pos(idx, r.entry_ts)
    end_ts = pd.Timestamp(r.execution_start) + HORIZON
    endpos = int(idx.searchsorted(end_ts, "left"))
    bi = bar_pos(idx, r.h1_break_ts) if pd.notna(r.h1_break_ts) else -1
    H, L, R = float(r.H), float(r.L), float(r.R)
    target = H + TARGET_R * R
    confirmed = bool(bi == ei)

    # Exact A53 special case: entry candle can be a warning opportunity.
    if confirmed and is_post_h05(float(cl[ei]), H, R):
        return ei

    for i in range(ei + 1, endpos):
        if not confirmed and bi >= 0 and i >= bi:
            confirmed = True
        if float(hi[i]) >= target:
            return -1
        bad = (float(cl[i]) <= H + EPS) if confirmed else (float(cl[i]) < L - EPS)
        if bad:
            return -1
        if confirmed and is_post_h05(float(cl[i]), H, R):
            return i
    return -1


def terminal_after_warning(m, r, wi):
    idx, hi, cl = m["idx"], m["high"], m["close"]
    end_ts = pd.Timestamp(r.execution_start) + HORIZON
    endpos = int(idx.searchsorted(end_ts, "left"))
    H, R = float(r.H), float(r.R)
    target = H + TARGET_R * R
    for i in range(wi + 1, endpos):
        if float(hi[i]) >= target:
            return "RECOVER_E40", i
        if float(cl[i]) <= H + EPS:
            return "FAILED_BREAK", i
    # For this cohort frozen parent should never land here.
    return "OTHER", endpos - 1


def state_and_features(m, r, wi, terminal_kind, terminal_i, mins):
    idx, hi, lo, cl = m["idx"], m["high"], m["low"], m["close"]
    H, R = float(r.H), float(r.R)
    k = mins // 5
    oi = wi + k
    if oi >= len(idx):
        raise RuntimeError("snapshot beyond market")

    # Terminal event at/before observation dominates state.
    if terminal_i <= oi:
        state = "TARGET_BY_T" if terminal_kind == "RECOVER_E40" else "TERMINAL_FAIL_BY_T"
        alive = False
        latest_i = terminal_i
    else:
        alive = True
        latest_i = oi
        c = float(cl[latest_i])
        if c <= H + EPS:
            raise RuntimeError("alive snapshot has terminal close")
        if c <= H + 0.05 * R + EPS:
            state = "ALIVE_H05"
        elif c <= H + 0.10 * R + EPS:
            state = "ALIVE_H10"
        else:
            state = "ALIVE_ABOVE_H10"

    # Path diagnostics use only bars completed after warning through observation or earlier terminal.
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
        "snapshot_min": mins,
        "state": state,
        "alive": alive,
        "latest_close_R": close_R,
        "running_high_extension_R": run_high_R,
        "running_low_depth_R": run_low_depth_R,
        "closes_H05": n_h05,
        "closes_H10": n_h10,
        "closes_above_H10": n_above_h10,
        "close_above_H10_by_T": close_above_h10,
        "high_touch_H10_by_T": high_touch_h10,
    }


def first_after(idx, start_i, end_i, predicate):
    for i in range(start_i, end_i + 1):
        if predicate(i): return i
    return -1


def analyze_trade(m, r, wi):
    idx, cl = m["idx"], m["close"]
    H, R = float(r.H), float(r.R)
    outcome, ti = terminal_after_warning(m, r, wi)
    if outcome == "OTHER":
        raise RuntimeError(f"unexpected post-H05 OTHER outcome {r.partition} {r.entry_ts}")

    escape05_i = first_after(idx, wi + 1, ti, lambda i: float(cl[i]) > H + 0.05 * R + EPS)
    escape10_i = first_after(idx, wi + 1, ti, lambda i: float(cl[i]) > H + 0.10 * R + EPS)
    fail_i = ti if outcome == "FAILED_BREAK" else -1

    base = {
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_pnl": float(r.pnl),
        "parent_pnl_5bps": float(r.pnl_5bps),
        "parent_loss_class": r.loss_class,
        "H": H, "L": float(r.L), "R": R,
        "warning_ts": idx[wi],
        "warning_known_ts": idx[wi] + BAR,
        "warning_close_R": (float(cl[wi]) - H) / R,
        "outcome": outcome,
        "terminal_event_ts": idx[ti],
        "terminal_known_ts": idx[ti] + BAR,
        "warning_to_terminal_min": float((idx[ti] - idx[wi]) / pd.Timedelta(minutes=1)),
        "first_escape_H05_ts": idx[escape05_i] if escape05_i >= 0 else pd.NaT,
        "first_escape_H10_ts": idx[escape10_i] if escape10_i >= 0 else pd.NaT,
        "first_fail_ts": idx[fail_i] if fail_i >= 0 else pd.NaT,
    }

    snaps=[]
    for sm in SNAPS:
        z = state_and_features(m, r, wi, outcome, ti, sm)
        snaps.append({**base, **z})

    # Candidate booleans. Full-cohort denominator: unavailable because terminal/target before T => False.
    smap = {z["snapshot_min"]: z for z in snaps}
    s5, s10, s15 = smap[5], smap[10], smap[15]
    cands = {
        "C1_STILL_H05_5M": bool(s5["alive"] and s5["state"] == "ALIVE_H05"),
        "C2_NOT_ABOVE_H10_5M": bool(s5["alive"] and s5["state"] in ("ALIVE_H05", "ALIVE_H10")),
        "C3_NO_CLOSE_ABOVE_H10_10M": bool(s10["alive"] and not s10["close_above_H10_by_T"]),
        "C4_STILL_H05_10M": bool(s10["alive"] and s10["state"] == "ALIVE_H05"),
        "C5_NO_CLOSE_ABOVE_H10_15M": bool(s15["alive"] and not s15["close_above_H10_by_T"]),
    }
    return base, snaps, cands


def build(m):
    cohort=[]; snaps=[]; cand_rows=[]; parent_counts={}
    for part in PARTS:
        q = parent(m, part)
        parent_counts[part] = len(q)
        for _, r in q.iterrows():
            wi = find_post_h05(m, r)
            if wi < 0: continue
            base, ss, cc = analyze_trade(m, r, wi)
            cohort.append(base)
            snaps.extend(ss)
            for name, hit in cc.items():
                cand_rows.append({
                    "partition": part, "dev_block": r.dev_block, "entry_ts": r.entry_ts,
                    "outcome": base["outcome"], "candidate": name, "hit": bool(hit),
                    "terminal_event_ts": base["terminal_event_ts"],
                })
    return pd.DataFrame(cohort), pd.DataFrame(snaps), pd.DataFrame(cand_rows), parent_counts


def validate(cohort, parent_counts):
    errors=[]
    for p in PARTS:
        if parent_counts.get(p) != EXPECTED_PARENT[p]:
            errors.append(f"{p} parent {parent_counts.get(p)} != {EXPECTED_PARENT[p]}")
        q=cohort[cohort.partition==p]
        w=int((q.outcome=="RECOVER_E40").sum()); f=int((q.outcome=="FAILED_BREAK").sum())
        if len(q)!=EXPECTED_COHORT[p]: errors.append(f"{p} cohort {len(q)} != {EXPECTED_COHORT[p]}")
        if w!=EXPECTED_WIN[p]: errors.append(f"{p} winners {w} != {EXPECTED_WIN[p]}")
        if f!=EXPECTED_FAIL[p]: errors.append(f"{p} fails {f} != {EXPECTED_FAIL[p]}")
        if not (pd.to_datetime(q.warning_known_ts, utc=True) < pd.to_datetime(q.terminal_known_ts, utc=True)).all():
            errors.append(f"{p} warning not before terminal")
    if len(cohort)!=505: errors.append(f"total cohort {len(cohort)} != 505")
    if int((cohort.outcome=="RECOVER_E40").sum())!=107: errors.append("total winners != 107")
    if int((cohort.outcome=="FAILED_BREAK").sum())!=398: errors.append("total fails != 398")
    return errors


def candidate_summary(cands, cohort):
    rows=[]
    for part in PARTS:
        for name in CANDIDATES:
            q=cands[(cands.partition==part)&(cands.candidate==name)].copy()
            bad=q[q.outcome=="FAILED_BREAK"]; win=q[q.outcome=="RECOVER_E40"]
            br=float(bad.hit.mean()) if len(bad) else np.nan
            wr=float(win.hit.mean()) if len(win) else np.nan
            ratio=np.inf if wr==0 and br>0 else (br/wr if wr>0 else np.nan)
            leads=[]
            for _, r in bad[bad.hit].iterrows():
                horizon = {"C1_STILL_H05_5M":5,"C2_NOT_ABOVE_H10_5M":5,"C3_NO_CLOSE_ABOVE_H10_10M":10,"C4_STILL_H05_10M":10,"C5_NO_CLOSE_ABOVE_H10_15M":15}[name]
                # Candidate known horizon minutes after warning close; terminal known time difference simplifies below.
                warn = cohort[(cohort.partition==part)&(cohort.entry_ts==r.entry_ts)].iloc[0]
                cand_known = pd.Timestamp(warn.warning_known_ts) + pd.Timedelta(minutes=horizon)
                lead=float((pd.Timestamp(warn.terminal_known_ts)-cand_known)/pd.Timedelta(minutes=1))
                leads.append(lead)
            rows.append({
                "partition":part,"candidate":name,"bad_n":len(bad),"win_n":len(win),
                "bad_hit_n":int(bad.hit.sum()),"win_hit_n":int(win.hit.sum()),
                "bad_hit_rate":br,"win_hit_rate":wr,"gap":br-wr,"ratio":ratio,
                "median_lead_min":float(pd.Series(leads,dtype=float).median()) if leads else np.nan,
            })
    out=pd.DataFrame(rows)

    # Development block consistency and frozen gates.
    for name in CANDIDATES:
        same=0; adequate=0
        q=cands[(cands.partition=="development")&(cands.candidate==name)]
        for bi in range(6):
            b=q[pd.to_numeric(q.dev_block,errors="coerce")==bi]
            bad=b[b.outcome=="FAILED_BREAK"]; win=b[b.outcome=="RECOVER_E40"]
            if len(bad)>0 and len(win)>0:
                adequate += 1
                if float(bad.hit.mean()) > float(win.hit.mean()): same += 1
        out.loc[(out.partition=="development")&(out.candidate==name),"adequate_blocks"] = adequate
        out.loc[(out.partition=="development")&(out.candidate==name),"same_direction_blocks"] = same

    dev_support={}
    for name in CANDIDATES:
        d=out[(out.partition=="development")&(out.candidate==name)].iloc[0]
        dev_support[name]=bool(
            d.bad_hit_rate >= 0.30-EPS and d.gap >= 0.20-EPS and d.ratio >= 1.50-EPS and
            d.same_direction_blocks >= 5 and d.median_lead_min >= 5-EPS
        )
        out.loc[(out.partition=="development")&(out.candidate==name),"development_supported"] = dev_support[name]

    for name in CANDIDATES:
        replicated=dev_support[name]
        if replicated:
            for part in ("external","reference_validation"):
                z=out[(out.partition==part)&(out.candidate==name)].iloc[0]
                pp=bool(z.bad_hit_rate>z.win_hit_rate and z.gap>=0.15-EPS and z.ratio>=1.25-EPS and z.bad_hit_rate>=0.20-EPS)
                out.loc[(out.partition==part)&(out.candidate==name),"oos_pass"] = pp
                replicated = replicated and pp
        out.loc[out.candidate==name,"replicated"] = bool(replicated)
    return out


def diagnostics(snaps):
    rows=[]
    feats=("latest_close_R","running_high_extension_R","running_low_depth_R","closes_H05","closes_H10","closes_above_H10")
    for (part,sm),q in snaps.groupby(["partition","snapshot_min"],sort=False):
        for outcome in ("RECOVER_E40","FAILED_BREAK"):
            z=q[q.outcome==outcome]
            states=z.state.value_counts(normalize=True)
            for state,rate in states.items():
                rows.append({"partition":part,"snapshot_min":sm,"outcome":outcome,"kind":"STATE","feature":state,"n":len(z),"value":float(rate)})
            for f in feats:
                x=pd.to_numeric(z[f],errors="coerce").dropna()
                rows.append({"partition":part,"snapshot_min":sm,"outcome":outcome,"kind":"MEDIAN","feature":f,"n":len(x),"value":float(x.median()) if len(x) else np.nan})
    return pd.DataFrame(rows)


def choose_primary(summary):
    reps=[]
    horizon={"C1_STILL_H05_5M":5,"C2_NOT_ABOVE_H10_5M":5,"C3_NO_CLOSE_ABOVE_H10_10M":10,"C4_STILL_H05_10M":10,"C5_NO_CLOSE_ABOVE_H10_15M":15}
    for name in CANDIDATES:
        if bool(summary[summary.candidate==name].replicated.iloc[0]):
            d=summary[(summary.partition=="development")&(summary.candidate==name)].iloc[0]
            reps.append((horizon[name],-float(d.gap),float(d.win_hit_rate),name))
    if not reps: return None
    reps.sort()
    return reps[0][3]


def write_result(cohort, summary, diagnostics, coverage, errors, primary):
    status = "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_SUPPORTED_FOR_A55" if (not errors and primary is not None) else "SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_INCONCLUSIVE"
    lines=[
        "# SOL LONG 15:00 UTC Post-H05 Secondary Trigger Anatomy — A54 Result","",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
        "A54 observes the frozen parent after the first live `POST_H05` warning. No exit is changed and no new price threshold is scanned.","",
        "## Reconciliation","",
        f"POST_H05 cohort: **{len(cohort)}** = **{int((cohort.outcome=='RECOVER_E40').sum())} E40 winners + {int((cohort.outcome=='FAILED_BREAK').sum())} failed-break losers**. Errors: **{len(errors)}**.","",
        "| Partition | Cohort | Recover E40 | Failed break | Median warning→terminal winner | Median warning→terminal fail |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for p in PARTS:
        q=cohort[cohort.partition==p]; w=q[q.outcome=="RECOVER_E40"]; f=q[q.outcome=="FAILED_BREAK"]
        lines.append(f"| {p} | {len(q)} | {len(w)} | {len(f)} | {fmt(pd.to_numeric(w.warning_to_terminal_min,errors='coerce').median(),0)}m | {fmt(pd.to_numeric(f.warning_to_terminal_min,errors='coerce').median(),0)}m |")

    lines += ["","## Fixed actionable candidate discrimination","",
              "| Candidate | Part | Fail hit | Winner hit | Gap | Ratio | Lead | Dev blocks | Replicated |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in CANDIDATES:
        for p in PARTS:
            r=summary[(summary.partition==p)&(summary.candidate==name)].iloc[0]
            blocks = f"{int(r.same_direction_blocks)}/{int(r.adequate_blocks)}" if p=="development" and pd.notna(r.get("same_direction_blocks",np.nan)) else "-"
            lines.append(f"| {name} | {p} | {pct(r.bad_hit_rate)} | {pct(r.win_hit_rate)} | {pct(r.gap)} | {fmt(r.ratio,2)}x | {fmt(r.median_lead_min,0)}m | {blocks} | {'YES' if bool(r.replicated) else 'no'} |")

    # Compact state table for the two outcomes, pooled across partitions.
    lines += ["","## Pooled post-warning state progression","",
              "| T | Outcome | terminal fail | target | alive H05 | alive H10 | alive >H10 |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    ss = pd.read_csv(OUT_SNAP) if OUT_SNAP.exists() else None
    if ss is not None:
        for sm in SNAPS:
            for outc in ("FAILED_BREAK","RECOVER_E40"):
                q=ss[(pd.to_numeric(ss.snapshot_min,errors='coerce')==sm)&(ss.outcome==outc)]
                rates=q.state.value_counts(normalize=True)
                lines.append(f"| +{sm}m | {outc} | {pct(rates.get('TERMINAL_FAIL_BY_T',0.0))} | {pct(rates.get('TARGET_BY_T',0.0))} | {pct(rates.get('ALIVE_H05',0.0))} | {pct(rates.get('ALIVE_H10',0.0))} | {pct(rates.get('ALIVE_ABOVE_H10',0.0))} |")

    reps=[n for n in CANDIDATES if bool(summary[summary.candidate==n].replicated.iloc[0])]
    lines += ["","## Decision","",f"Replicated actionable secondary triggers: **{', '.join(reps) if reps else 'none'}**.",""]
    if primary:
        lines += [f"Frozen earliest primary trigger for A55: **{primary}**.",""]
    lines += [f"**Status: {status}**","",
              "A54 is anatomy only. A supported candidate must be separately executed in A55 at the next available open; no live rule changes are authorized here.","",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    cohort,snaps,cands,parent_counts=build(m)
    errors=validate(cohort,parent_counts)
    cohort.to_csv(OUT_COHORT,index=False)
    snaps.to_csv(OUT_SNAP,index=False)
    summary=candidate_summary(cands,cohort)
    diagnostics=globals()["diagnostics"](snaps)
    summary.to_csv(OUT_CAND,index=False)
    diagnostics.to_csv(OUT_DIAG,index=False)
    primary=choose_primary(summary) if not errors else None
    status=write_result(cohort,summary,diagnostics,coverage,errors,primary)
    print(status)
    if errors:
        raise RuntimeError("; ".join(errors))

if __name__=="__main__":
    main()
