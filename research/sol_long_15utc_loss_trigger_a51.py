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

OUT_EVENTS = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_EVENTS.csv"
OUT_CLASS = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_CLASS_SUMMARY.csv"
OUT_WARN = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_WARNING_SUMMARY.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_Status.txt"

REF_MIN = 360
HOUR = 15
TARGET_R = 0.40
BAR = pd.Timedelta(minutes=5)
HORIZON = pd.Timedelta(minutes=720)
PARTS = ("development", "external", "reference_validation")
EXPECTED_N = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_LOSS = {"development": 357, "external": 166, "reference_validation": 187}
EPS = 1e-12


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def parent(m, part):
    q = a17.simulate_cell(m, part, REF_MIN, HOUR, "A51", "CENTRAL").copy()
    if q.empty: return q
    q["loss_class"] = [a3.loss_class(r) for _, r in q.iterrows()]
    return q.sort_values("entry_ts").reset_index(drop=True)


def bar_pos(idx, ts):
    if pd.isna(ts): return -1
    i = int(idx.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(idx) or idx[i] != pd.Timestamp(ts):
        raise RuntimeError(f"timestamp parity failure: {ts}")
    return i


def first_ts(idx, positions):
    return idx[positions[0]] if positions else pd.NaT


def analyze_trade(m, r):
    idx, hi, lo, cl = m["idx"], m["high"], m["low"], m["close"]
    ei = bar_pos(idx, r.entry_ts)
    xi = bar_pos(idx, r.exit_ts)
    bi = bar_pos(idx, r.h1_break_ts) if pd.notna(r.h1_break_ts) else -1
    ii = bar_pos(idx, r.invalidation_close_ts) if pd.notna(r.invalidation_close_ts) else -1
    H, L, R = float(r.H), float(r.L), float(r.R)
    if R <= 0: raise RuntimeError("nonpositive R")
    session_end = pd.Timestamp(r.execution_start) + HORIZON
    final_bar_ts = session_end - BAR
    final_i = bar_pos(idx, final_bar_ts)

    # Independent mechanical trigger audit against the frozen A2 state machine.
    recon_i = -1
    recon_type = "NONE"
    confirmed = False
    # E0 evaluates invalidation from the bar after entry. Break confirmation can be the entry bar.
    if bi == ei:
        confirmed = True
    for i in range(ei + 1, final_i + 1):
        if not confirmed and bi >= 0 and i >= bi:
            confirmed = True
        if confirmed:
            if float(cl[i]) <= H + EPS:
                recon_i = i; recon_type = "FAILED_BREAK"; break
        else:
            if float(cl[i]) < L - EPS:
                recon_i = i; recon_type = "REFERENCE_INVALIDATION"; break

    is_win = float(r.pnl) > 0
    if is_win:
        mechanism = "WIN_TARGET"
    elif ii >= 0 and bi >= 0:
        mechanism = "M2_FAILED_BREAK"
    elif ii >= 0 and bi < 0 and ii == final_i:
        mechanism = "M0F_REFERENCE_INVALIDATION_FINAL_BAR"
    elif ii >= 0 and bi < 0:
        mechanism = "M0_REFERENCE_INVALIDATION"
    else:
        mechanism = "M1_TIME_NO_STRUCTURAL_FAIL"

    trigger_ts = idx[ii] if ii >= 0 else pd.NaT
    trigger_known_ts = trigger_ts + BAR if pd.notna(trigger_ts) else pd.NaT
    trigger_final = bool(ii == final_i and ii >= 0)
    next_open_available = bool(ii >= 0 and ii < final_i)
    # On normal invalidation, the invalidating 5m candle close and the next bar open are the same physical instant.
    # On final-bar invalidation A2 uses that final close, also the same physical instant as trigger knowledge.
    execution_effective_ts = trigger_known_ts if ii >= 0 else (pd.Timestamp(r.exit_ts) + BAR if str(r.exit_reason).startswith("TIME") else pd.Timestamp(r.exit_ts))
    nominal_trigger_exit_min = float((pd.Timestamp(r.exit_ts) - trigger_ts) / pd.Timedelta(minutes=1)) if pd.notna(trigger_ts) else np.nan
    executable_lead_min = float((execution_effective_ts - trigger_known_ts) / pd.Timedelta(minutes=1)) if pd.notna(trigger_known_ts) else np.nan

    trigger_close_R = (float(cl[ii]) - H) / R if ii >= 0 else np.nan
    prev_close_R = (float(cl[ii-1]) - H) / R if ii > ei else np.nan
    path_end = ii if ii >= 0 else min(xi, final_i)
    seg_hi = np.asarray(hi[ei:path_end+1], float)
    seg_lo = np.asarray(lo[ei:path_end+1], float)
    running_mfe = max(0.0, (float(seg_hi.max()) - H) / R) if len(seg_hi) else np.nan
    running_mae = max(0.0, (H - float(seg_lo.min())) / R) if len(seg_lo) else np.nan
    closes_above = int((np.asarray(cl[bi:path_end], float) > H).sum()) if bi >= 0 and path_end > bi else (1 if bi == path_end and bi >= 0 and float(cl[bi]) > H else 0)
    max_ext_before_trigger = max(0.0, (float(np.max(hi[bi:ii])) - H) / R) if bi >= 0 and ii > bi else 0.0 if bi >= 0 and ii >= 0 else np.nan

    entry_to_trigger = float((trigger_ts - pd.Timestamp(r.entry_ts)) / pd.Timedelta(minutes=1)) if pd.notna(trigger_ts) else np.nan
    break_to_trigger = float((trigger_ts - pd.Timestamp(r.h1_break_ts)) / pd.Timedelta(minutes=1)) if pd.notna(trigger_ts) and pd.notna(r.h1_break_ts) else np.nan

    # Fixed warning events. All warning timestamps are bar labels; information becomes known at bar close (+5m).
    pre_end = bi if bi >= 0 else (ii if ii >= 0 else min(xi, final_i) + 1)
    pre_positions = list(range(ei, max(ei, pre_end)))
    w_l25 = [i for i in pre_positions if float(cl[i]) <= L + 0.25*R]
    w_l10 = [i for i in pre_positions if float(cl[i]) <= L + 0.10*R]
    warn_l25_ts = first_ts(idx, w_l25)
    warn_l10_ts = first_ts(idx, w_l10)

    warn_h10_ts = pd.NaT; warn_h05_ts = pd.NaT
    no_ext05_5 = False; no_ext10_10 = False
    if bi >= 0:
        stop = ii if ii >= 0 else min(xi, final_i) + 1
        post_positions = list(range(bi, max(bi, stop)))
        h10 = [i for i in post_positions if H < float(cl[i]) <= H + 0.10*R]
        h05 = [i for i in post_positions if H < float(cl[i]) <= H + 0.05*R]
        warn_h10_ts = first_ts(idx, h10)
        warn_h05_ts = first_ts(idx, h05)
        p5_end = min(bi + 2, stop)  # breakout bar + first following bar, if still alive
        p10_end = min(bi + 3, stop)
        if p5_end > bi:
            no_ext05_5 = bool(float(np.max(hi[bi:p5_end])) < H + 0.05*R)
        if p10_end > bi:
            no_ext10_10 = bool(float(np.max(hi[bi:p10_end])) < H + 0.10*R)

    no_break = {}
    for mins in (30, 60, 120, 180, 240, 360):
        t = pd.Timestamp(r.entry_ts) + pd.Timedelta(minutes=mins)
        alive = t <= execution_effective_ts
        no_break[f"no_break_{mins}m"] = bool(alive and (pd.isna(r.h1_break_ts) or pd.Timestamp(r.h1_break_ts) >= t))

    def lead(ts):
        if pd.isna(ts) or pd.isna(trigger_ts): return np.nan
        # +5m cancels for both warning and trigger close knowledge times.
        return float((trigger_ts - pd.Timestamp(ts)) / pd.Timedelta(minutes=1))

    return {
        "partition": r.partition, "dev_block": r.dev_block,
        "execution_start": r.execution_start, "entry_ts": r.entry_ts,
        "exit_ts": r.exit_ts, "exit_reason": r.exit_reason,
        "pnl": float(r.pnl), "pnl_5bps": float(r.pnl_5bps),
        "outcome": "WIN" if is_win else "LOSS", "loss_class": r.loss_class,
        "H": H, "L": L, "R": R,
        "break_ts": r.h1_break_ts,
        "mechanism": mechanism,
        "trigger_type": recon_type if recon_i >= 0 else "NONE",
        "trigger_ts": trigger_ts,
        "trigger_known_ts": trigger_known_ts,
        "trigger_on_final_bar": trigger_final,
        "next_open_available": next_open_available,
        "execution_effective_ts": execution_effective_ts,
        "nominal_trigger_to_exit_min": nominal_trigger_exit_min,
        "executable_lead_min": executable_lead_min,
        "entry_to_trigger_min": entry_to_trigger,
        "break_to_trigger_min": break_to_trigger,
        "trigger_close_R": trigger_close_R,
        "prev_close_R": prev_close_R,
        "running_mfe_R_at_trigger": running_mfe,
        "running_mae_R_at_trigger": running_mae,
        "closes_above_H_before_trigger": closes_above,
        "max_extension_R_before_trigger": max_ext_before_trigger,
        "recon_trigger_matches_simulator": bool((ii < 0 and recon_i < 0) or (ii == recon_i)),
        "recon_type_matches_state": bool((ii < 0 and recon_type == "NONE") or (bi >= 0 and recon_type == "FAILED_BREAK") or (bi < 0 and recon_type == "REFERENCE_INVALIDATION")),
        "warn_pre_L25_ts": warn_l25_ts, "warn_pre_L25_lead_min": lead(warn_l25_ts),
        "warn_pre_L10_ts": warn_l10_ts, "warn_pre_L10_lead_min": lead(warn_l10_ts),
        "warn_post_H10_ts": warn_h10_ts, "warn_post_H10_lead_min": lead(warn_h10_ts),
        "warn_post_H05_ts": warn_h05_ts, "warn_post_H05_lead_min": lead(warn_h05_ts),
        "no_ext_005R_by_5m": no_ext05_5,
        "no_ext_010R_by_10m": no_ext10_10,
        **no_break,
    }


def class_summary(e):
    rows=[]
    losses=e[e.outcome=="LOSS"].copy()
    for (part,lc),q in losses.groupby(["partition","loss_class"], sort=False):
        mech=q.mechanism.value_counts().index[0] if len(q) else "-"
        rows.append({
            "partition":part,"loss_class":lc,"n":len(q),"modal_mechanism":mech,
            "mechanism_purity":float((q.mechanism==mech).mean()),
            "median_entry_to_trigger_min":float(pd.to_numeric(q.entry_to_trigger_min,errors="coerce").median()),
            "median_break_to_trigger_min":float(pd.to_numeric(q.break_to_trigger_min,errors="coerce").median()),
            "median_trigger_close_R":float(pd.to_numeric(q.trigger_close_R,errors="coerce").median()),
            "median_prev_close_R":float(pd.to_numeric(q.prev_close_R,errors="coerce").median()),
            "median_mfe_R_at_trigger":float(pd.to_numeric(q.running_mfe_R_at_trigger,errors="coerce").median()),
            "median_mae_R_at_trigger":float(pd.to_numeric(q.running_mae_R_at_trigger,errors="coerce").median()),
            "median_closes_above_H_before_trigger":float(pd.to_numeric(q.closes_above_H_before_trigger,errors="coerce").median()),
            "median_max_extension_R_before_trigger":float(pd.to_numeric(q.max_extension_R_before_trigger,errors="coerce").median()),
            "median_nominal_trigger_to_exit_min":float(pd.to_numeric(q.nominal_trigger_to_exit_min,errors="coerce").median()),
            "median_executable_lead_min":float(pd.to_numeric(q.executable_lead_min,errors="coerce").median()),
            "final_bar_trigger_rate":float(q.trigger_on_final_bar.mean()),
        })
    return pd.DataFrame(rows)


def warning_summary(e):
    rows=[]
    losses=e[e.outcome=="LOSS"].copy()
    timestamp_warns=[("PRE_L25","warn_pre_L25_ts","warn_pre_L25_lead_min"),("PRE_L10","warn_pre_L10_ts","warn_pre_L10_lead_min"),("POST_H10","warn_post_H10_ts","warn_post_H10_lead_min"),("POST_H05","warn_post_H05_ts","warn_post_H05_lead_min")]
    bool_warns=[("NO_EXT_005R_BY_5M","no_ext_005R_by_5m"),("NO_EXT_010R_BY_10M","no_ext_010R_by_10m")]+[(f"NO_BREAK_{m}M",f"no_break_{m}m") for m in (30,60,120,180,240,360)]
    for (part,lc),q in losses.groupby(["partition","loss_class"],sort=False):
        for name,col,leadcol in timestamp_warns:
            hit=q[col].notna()
            lead=pd.to_numeric(q.loc[hit,leadcol],errors="coerce")
            rows.append({"partition":part,"loss_class":lc,"warning":name,"n":len(q),"hit_n":int(hit.sum()),"coverage":float(hit.mean()),"median_lead_min":float(lead.median()) if len(lead) else np.nan})
        for name,col in bool_warns:
            hit=q[col].fillna(False).astype(bool)
            rows.append({"partition":part,"loss_class":lc,"warning":name,"n":len(q),"hit_n":int(hit.sum()),"coverage":float(hit.mean()),"median_lead_min":np.nan})
    return pd.DataFrame(rows)


def validate(e):
    errors=[]
    for p in PARTS:
        q=e[e.partition==p]
        if len(q)!=EXPECTED_N[p]: errors.append(f"{p} N {len(q)} != {EXPECTED_N[p]}")
        nl=int((q.outcome=="LOSS").sum())
        if nl!=EXPECTED_LOSS[p]: errors.append(f"{p} loss N {nl} != {EXPECTED_LOSS[p]}")
    if len(e)!=1219: errors.append(f"total N {len(e)} != 1219")
    if int((e.outcome=="LOSS").sum())!=710: errors.append(f"total losses {int((e.outcome=='LOSS').sum())} != 710")
    structural=e[(e.outcome=="LOSS") & (e.mechanism!="M1_TIME_NO_STRUCTURAL_FAIL")]
    if not structural.recon_trigger_matches_simulator.all(): errors.append("independent trigger timestamp mismatch")
    if not structural.recon_type_matches_state.all(): errors.append("independent trigger state mismatch")
    l1=e[(e.outcome=="LOSS") & (e.loss_class=="L1_NEVER_BREAK_TIME") & e.trigger_ts.notna()]
    bad_l1=l1[~((l1.exit_reason.astype(str)=="TIME_AFTER_FINAL_INVALIDATION") & l1.trigger_on_final_bar)]
    if len(bad_l1): errors.append(f"L1 has {len(bad_l1)} unexplained structural triggers")
    other=e[(e.outcome=="LOSS") & ~e.loss_class.astype(str).str.startswith(tuple(["L0_","L1_","L2_","L3_","L4_","L5_"]))]
    if len(other): errors.append(f"unexpected loss classes N={len(other)}")
    return errors


def write_result(e,cs,ws,coverage,errors):
    losses=e[e.outcome=="LOSS"].copy()
    mech=losses.mechanism.value_counts()
    pooled=cs.groupby("loss_class",as_index=False).agg(n=("n","sum"),median_entry_to_trigger_min=("median_entry_to_trigger_min","median"),median_break_to_trigger_min=("median_break_to_trigger_min","median"),median_trigger_close_R=("median_trigger_close_R","median"),median_prev_close_R=("median_prev_close_R","median"),median_max_extension_R_before_trigger=("median_max_extension_R_before_trigger","median"),median_executable_lead_min=("median_executable_lead_min","median"))
    lines=["# SOL LONG 15:00 UTC Universal Loss Trigger Anatomy — A51 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","","A51 audits the frozen R360/15UTC `E0_RESTING_H -> E40` state machine. It does not modify trading rules.","","## Reconciliation","",f"Trades: **{len(e)}**; raw losses: **{len(losses)}**; errors: **{len(errors)}**.",""]
    if errors:
        lines += ["Validation errors:"]+[f"- {x}" for x in errors]+[""]
    lines += ["## Core trigger finding","",f"- `M0_REFERENCE_INVALIDATION`: **{int(mech.get('M0_REFERENCE_INVALIDATION',0))}** losses.",f"- `M0F_REFERENCE_INVALIDATION_FINAL_BAR`: **{int(mech.get('M0F_REFERENCE_INVALIDATION_FINAL_BAR',0))}** losses.",f"- `M1_TIME_NO_STRUCTURAL_FAIL`: **{int(mech.get('M1_TIME_NO_STRUCTURAL_FAIL',0))}** losses.",f"- `M2_FAILED_BREAK`: **{int(mech.get('M2_FAILED_BREAK',0))}** losses.","","For M2, the terminal event is the same across L2/L3/L4/L5: **first completed 5m close `<= H` after a completed close `> H` confirmed breakout**. The legacy classes are latency buckets, not different trigger mechanisms.","","For M0, the terminal event is **first completed close `< L` before breakout confirmation**. L1 is a time-expiry bucket unless the frozen final-bar edge places a structural invalidation into `TIME_AFTER_FINAL_INVALIDATION`.","","Important execution semantics: candle timestamps label bar opens. A failed/invalidation bar becomes known at its close (`trigger_ts + 5m`), which is the same physical instant as the normal next-bar open. Therefore the nominal timestamp gap is generally 5m, but **actionable lead after terminal confirmation is 0m**.","","## Pooled legacy class anatomy","","| Class | N | Entry→trigger | Break→trigger | Trigger close | Prev close | Max ext before trigger | Actionable lead |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    order=["L0_NEVER_BREAK_REFERENCE_INVALIDATION","L1_NEVER_BREAK_TIME","L2_BREAK_FAST_FAIL_5M","L3_BREAK_FAST_FAIL_10M","L4_BREAK_FAIL_30M","L5_BREAK_FAIL_LATE"]
    for lc in order:
        z=pooled[pooled.loss_class==lc]
        if z.empty: continue
        r=z.iloc[0]
        lines.append(f"| {lc} | {int(r.n)} | {fmt(r.median_entry_to_trigger_min,0)}m | {fmt(r.median_break_to_trigger_min,0)}m | {fmt(r.median_trigger_close_R,3)}R | {fmt(r.median_prev_close_R,3)}R | {fmt(r.median_max_extension_R_before_trigger,3)}R | {fmt(r.median_executable_lead_min,0)}m |")
    lines += ["","## Partition trigger counts","","| Partition | L0 | L1 | L2 | L3 | L4 | L5 |","|---|---:|---:|---:|---:|---:|---:|"]
    for p in PARTS:
        q=losses[losses.partition==p]
        vals=[]
        for prefix in ("L0_","L1_","L2_","L3_","L4_","L5_"):
            vals.append(int(q.loss_class.astype(str).str.startswith(prefix).sum()))
        lines.append(f"| {p} | " + " | ".join(str(x) for x in vals) + " |")
    lines += ["","## Fixed early-warning diagnostics","","The full warning table is persisted in `SOL_LONG_15UTC_LOSS_TRIGGER_A51_WARNING_SUMMARY.csv`. These diagnostics are anatomy only; A51 does not promote a warning or threshold.",""]
    # Show pooled warning coverage by loss class for concise inspection.
    wp=ws.groupby(["loss_class","warning"],as_index=False).agg(hit_n=("hit_n","sum"),n=("n","sum"))
    wp["coverage"]=wp.hit_n/wp.n
    for lc in order:
        z=wp[wp.loss_class==lc].sort_values(["coverage","hit_n"],ascending=False).head(4)
        if z.empty: continue
        lines += [f"### {lc}","","| Warning | Coverage |","|---|---:|"]
        for _,r in z.iterrows(): lines.append(f"| {r.warning} | {pct(r.coverage)} |")
        lines.append("")
    status="SOL_LONG_15UTC_LOSS_TRIGGER_A51_COMPLETE" if not errors else "SOL_LONG_15UTC_LOSS_TRIGGER_A51_INVALID_RECONCILIATION"
    lines += ["## Decision","",f"**Status: {status}**","","A51 establishes the actual failure state machine. Any attempt to exit earlier than the terminal close must be a separately preregistered warning/guard study (A52+), because terminal confirmation itself provides no executable lead before the current next-open exit.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    rows=[]
    for part in PARTS:
        q=parent(m,part)
        for _,r in q.iterrows(): rows.append(analyze_trade(m,r))
    e=pd.DataFrame(rows)
    cs=class_summary(e); ws=warning_summary(e); errors=validate(e)
    e.to_csv(OUT_EVENTS,index=False); cs.to_csv(OUT_CLASS,index=False); ws.to_csv(OUT_WARN,index=False)
    status=write_result(e,cs,ws,coverage,errors)
    print(status)
    if errors:
        for x in errors: print("ERROR:",x)
        raise SystemExit(2)

if __name__=="__main__": main()
