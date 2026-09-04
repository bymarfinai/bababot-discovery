#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A14_PATH = Path(__file__).resolve().parent / "sol_long_e20_conditional_protection_a14.py"
spec = importlib.util.spec_from_file_location("sol_a14", A14_PATH)
a14 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a14)
a11 = a14.a11
a2 = a14.a2

OUT_MD = ROOT / "SOL_LONG_E10_FAIL_GUARD_A16_Result.md"
OUT_DEV = ROOT / "SOL_LONG_E10_FAIL_GUARD_A16_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_E10_FAIL_GUARD_A16_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_E10_FAIL_GUARD_A16_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_E10_FAIL_GUARD_A16_Status.txt"

LANES = ("G_FAST10", "G_SHALLOW25", "G_FAST10_SHALLOW25", "G_FAST10_OR_SHALLOW25")
EPS = 1e-12


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def key4(role, partition, execution_start, entry_ts):
    return (str(role), str(partition), pd.Timestamp(execution_start), pd.Timestamp(entry_ts))


def idx_of(idx, ts):
    t = pd.Timestamp(ts)
    i = int(idx.searchsorted(t, "left"))
    return i if i < len(idx) and idx[i] == t else -1


def guarded_signal(m, entry_ts, exit_ts, H, R, lane):
    sig = a14.signal_for_trade(m, entry_ts, exit_ts, H, R, "CP_E10_5_FULL")
    if sig is None:
        return None
    idx, lo = m["idx"], m["low"]
    ei = idx_of(idx, entry_ts)
    e20_i = int(sig["e20_i"])
    if ei < 0 or e20_i < ei:
        return None
    entry_to_e20 = float((idx[e20_i] - pd.Timestamp(entry_ts)) / pd.Timedelta(minutes=1))
    seg_lo = np.asarray(lo[ei:e20_i+1], dtype=float)
    mae = max(0.0, (H - float(np.min(seg_lo))) / R) if len(seg_lo) else np.nan
    fast = entry_to_e20 <= 10.0 + EPS
    shallow = pd.notna(mae) and mae <= 0.25 + EPS
    if lane == "G_FAST10": allow = fast
    elif lane == "G_SHALLOW25": allow = shallow
    elif lane == "G_FAST10_SHALLOW25": allow = fast and shallow
    elif lane == "G_FAST10_OR_SHALLOW25": allow = fast or shallow
    else: raise ValueError(lane)
    if not allow:
        return None
    return {**sig, "entry_to_e20_min": entry_to_e20, "running_mae_R_to_e20": mae}


def candidate_trade(m, *, role, partition, dev_block, execution_start, parent_entry_ts,
                    component, entry_ts, entry_price, exit_ts, exit_price, exit_reason,
                    baseline_pnl, baseline_pnl_5bps, H, L, R, lane):
    idx, op = m["idx"], m["open"]
    sig = guarded_signal(m, entry_ts, exit_ts, H, R, lane)
    xi = idx_of(idx, exit_ts)
    if xi < 0:
        raise RuntimeError(f"baseline exit timestamp missing {exit_ts}")
    intervention = False
    signal_ts = pd.NaT
    action_ts = pd.Timestamp(exit_ts)
    action_price = float(exit_price)
    reason = str(exit_reason)
    entry_to_e20 = np.nan
    mae = np.nan
    if sig is not None:
        si = int(sig["signal_i"])
        ni = si + 1
        if ni < xi and ni < len(idx):
            intervention = True
            signal_ts = idx[si]
            action_ts = idx[ni]
            action_price = float(op[ni])
            reason = "A16_GUARDED_E10_FAIL"
            entry_to_e20 = float(sig["entry_to_e20_min"])
            mae = float(sig["running_mae_R_to_e20"])
    ret = action_price / float(entry_price) - 1.0 if intervention else float(exit_price) / float(entry_price) - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - a2.STRESS) * a2.NOTIONAL
    return {
        "role": role, "partition": partition, "dev_block": dev_block,
        "execution_start": execution_start, "parent_entry_ts": parent_entry_ts,
        "lane": lane, "component": component, "H": H, "L": L, "R": R,
        "entry_ts": entry_ts, "entry_price": float(entry_price),
        "baseline_exit_ts": exit_ts, "baseline_exit_price": float(exit_price),
        "baseline_exit_reason": str(exit_reason), "baseline_pnl": float(baseline_pnl),
        "baseline_pnl_5bps": float(baseline_pnl_5bps), "intervention": intervention,
        "signal_ts": signal_ts, "candidate_exit_ts": action_ts if intervention else pd.Timestamp(exit_ts),
        "candidate_exit_price": action_price if intervention else float(exit_price),
        "candidate_exit_reason": reason, "candidate_pnl": pnl, "candidate_pnl_5bps": pnl5,
        "guard_entry_to_e20_min": entry_to_e20, "guard_running_mae_R_to_e20": mae,
    }


def simulate_lane(parent, h2, m, lane):
    pmap = {key4(r.role, r.partition, r.execution_start, r.entry_ts): r for _, r in parent.iterrows()}
    hmap = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in h2.iterrows()}
    prows=[]
    for _, r in parent.iterrows():
        prows.append(candidate_trade(m, role=r.role, partition=r.partition, dev_block=r.dev_block,
            execution_start=r.execution_start, parent_entry_ts=r.entry_ts, component="PARENT",
            entry_ts=r.entry_ts, entry_price=r.entry_price, exit_ts=r.exit_ts, exit_price=r.exit_price,
            exit_reason=r.exit_reason, baseline_pnl=r.pnl, baseline_pnl_5bps=r.pnl_5bps,
            H=float(r.H), L=float(r.L), R=float(r.R), lane=lane))
    pr = pd.DataFrame(prows)
    cpm = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}
    hrows=[]
    for k, hr in hmap.items():
        cp = cpm.get(k)
        if cp is None: raise RuntimeError(f"candidate parent mapping missing {k}")
        if float(cp.candidate_pnl) > 0: continue
        hrows.append(candidate_trade(m, role=hr.role, partition=hr.partition, dev_block=hr.dev_block,
            execution_start=hr.execution_start, parent_entry_ts=hr.parent_entry_ts, component="REC_H2",
            entry_ts=hr.recovery_entry_ts, entry_price=hr.recovery_entry_price,
            exit_ts=hr.recovery_exit_ts, exit_price=hr.recovery_exit_price, exit_reason=hr.recovery_exit_reason,
            baseline_pnl=hr.recovery_pnl, baseline_pnl_5bps=hr.recovery_pnl_5bps,
            H=float(hr.H), L=float(hr.L), R=float(hr.R), lane=lane))
    return pr, pd.DataFrame(hrows)


def development_row(parent_q, h2_q, pr, rr, lane):
    s = a14.summarize(parent_q, h2_q, pr, rr)
    pos_raw=0; pos_stress=0; adequate=0; block={}
    for bi in range(6):
        pb = parent_q[pd.to_numeric(parent_q.dev_block, errors="coerce") == bi]
        hb = h2_q[pd.to_numeric(h2_q.dev_block, errors="coerce") == bi]
        pcb = pr[pd.to_numeric(pr.dev_block, errors="coerce") == bi]
        rrb = rr[pd.to_numeric(rr.dev_block, errors="coerce") == bi] if rr is not None and len(rr) else pd.DataFrame()
        bx,bx5 = a14.stack_vals(pb,hb,candidate=False); cx,cx5 = a14.stack_vals(pcb,rrb,candidate=True)
        d=float(cx.sum()-bx.sum()); d5=float(cx5.sum()-bx5.sum())
        block[f"b{bi+1}_net_improvement"]=d; block[f"b{bi+1}_net_improvement_5bps"]=d5
        if len(bx) >= 20:
            adequate += 1
            if d > 0: pos_raw += 1
            if d5 > 0: pos_stress += 1
    eligible = bool(
        s["stack_net_improvement"] > 0 and s["stack_net_improvement_5bps"] > 0
        and s["candidate_stack_pf"] > s["base_stack_pf"]
        and s["candidate_stack_pf_5bps"] > s["base_stack_pf_5bps"]
        and s["candidate_episode_gross_loss"] <= s["base_episode_gross_loss"] + 1e-12
        and s["candidate_episode_wr"] >= s["base_episode_wr"] - 1e-12
        and s["winner_preservation"] >= 0.98
        and pos_raw >= 4 and pos_stress >= 4
    )
    return {"lane":lane, **s, "adequate_blocks":adequate, "positive_blocks_raw":pos_raw,
            "positive_blocks_5bps":pos_stress, "eligible":eligible, **block}


def choose_dev(dev):
    q=dev[dev.eligible].copy()
    if q.empty: return None
    complexity={"G_FAST10":0,"G_SHALLOW25":1,"G_FAST10_SHALLOW25":2,"G_FAST10_OR_SHALLOW25":3}
    q["complexity"] = q.lane.map(complexity)
    return q.sort_values(["stack_net_improvement_5bps","stack_net_improvement","winner_preservation","candidate_stack_pf_5bps","complexity"],
                         ascending=[False,False,False,False,True]).iloc[0]


def main():
    parent,h2,m,coverage = a11.load_system()
    cd_parent=parent[(parent.role=="CENTRAL")&(parent.partition=="development")].copy()
    cd_h2=h2[(h2.role=="CENTRAL")&(h2.partition=="development")].copy()
    dev_rows=[]; dev_frames={}
    for lane in LANES:
        pr,rr=simulate_lane(cd_parent,cd_h2,m,lane)
        dev_frames[lane]=(pr,rr)
        dev_rows.append(development_row(cd_parent,cd_h2,pr,rr,lane))
    dev=pd.DataFrame(dev_rows)
    win=choose_dev(dev)
    oos_rows=[]; selected=[]; supported=False; reason="No Development guard passed"; frozen=None
    if win is not None:
        frozen=str(win.lane)
        prd,rrd=dev_frames[frozen]; prd=prd.copy(); prd["selection_scope"]="DEVELOPMENT_FROZEN_WINNER"; selected.append(prd)
        if len(rrd): rrd=rrd.copy(); rrd["selection_scope"]="DEVELOPMENT_FROZEN_WINNER"; selected.append(rrd)
        for (role,part),pq in parent.groupby(["role","partition"],sort=False):
            if role=="CENTRAL" and part=="development": continue
            if part not in ["external","reference_validation"]: continue
            hq=h2[(h2.role==role)&(h2.partition==part)].copy()
            pr,rr=simulate_lane(pq,hq,m,frozen)
            s=a14.summarize(pq,hq,pr,rr)
            oos_rows.append({"role":role,"partition":part,"lane":frozen,**s})
            if len(pr): pr=pr.copy(); pr["selection_scope"]="FROZEN_OOS"; selected.append(pr)
            if len(rr): rr=rr.copy(); rr["selection_scope"]="FROZEN_OOS"; selected.append(rr)
        oos=pd.DataFrame(oos_rows)
        ce=oos[(oos.role=="CENTRAL")&(oos.partition=="external")]
        cr=oos[(oos.role=="CENTRAL")&(oos.partition=="reference_validation")]
        central_ok=False
        if len(ce)==1 and len(cr)==1:
            central_ok=all(
                float(r.stack_net_improvement)>0 and float(r.stack_net_improvement_5bps)>0
                and float(r.candidate_stack_pf)>=float(r.base_stack_pf)
                and float(r.candidate_stack_pf_5bps)>=float(r.base_stack_pf_5bps)
                and float(r.winner_preservation)>=0.98
                and float(r.candidate_episode_gross_loss)<=float(r.base_episode_gross_loss)+1e-12
                for _,r in pd.concat([ce,cr]).iterrows())
        sup=oos[oos.role.isin(["CLOCK_SUPPORT","REF_SUPPORT"])].copy()
        raw_pos=int((sup.stack_net_improvement>0).sum()); stress_pos=int((sup.stack_net_improvement_5bps>0).sum())
        support_ok=len(sup)>=4 and raw_pos>=3 and stress_pos>=3
        supported=bool(central_ok and support_ok)
        reason=f"central_ok={central_ok}; support positive raw={raw_pos}/4; support positive 5bps={stress_pos}/4"
    else:
        oos=pd.DataFrame()

    dev.to_csv(OUT_DEV,index=False); oos.to_csv(OUT_OOS,index=False)
    trades=pd.concat(selected,ignore_index=True) if selected else pd.DataFrame(); trades.to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG E10-Fail False-Positive Guard — A16 Result","",f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.","",
           "A16 guards the rejected A14 CP_E10_5_FULL signal using only A15-supported trigger-time dimensions.","",
           "## Central Development","",
           "| Lane | Parent interventions | H2 retained | H2 interventions | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |",
           "|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|"]
    for _,r in dev.iterrows():
        lines.append(f"| {r.lane} | {int(r.parent_interventions)} | {int(r.h2_retained_n)} | {int(r.h2_interventions)} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.base_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${fmt(r.base_episode_gross_loss)}→${fmt(r.candidate_episode_gross_loss)} | {fmt(r.base_stack_pf)}→{fmt(r.candidate_stack_pf)} | ${fmt(r.stack_net_improvement)} | {fmt(r.base_stack_pf_5bps)}→{fmt(r.candidate_stack_pf_5bps)} | ${fmt(r.stack_net_improvement_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if r.eligible else 'NO'} |")
    lines += ["",f"Frozen Development winner: **{frozen if frozen else 'NONE'}**.",""]
    if len(oos):
        lines += ["","## Frozen OOS","",
                  "| Role | Partition | Winner preserved | Episode WR base→new | Gross loss base→new | PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ |",
                  "|---|---|---:|---|---|---|---:|---|---:|"]
        for _,r in oos.iterrows():
            lines.append(f"| {r.role} | {r.partition} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.base_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${fmt(r.base_episode_gross_loss)}→${fmt(r.candidate_episode_gross_loss)} | {fmt(r.base_stack_pf)}→{fmt(r.candidate_stack_pf)} | ${fmt(r.stack_net_improvement)} | {fmt(r.base_stack_pf_5bps)}→{fmt(r.candidate_stack_pf_5bps)} | ${fmt(r.stack_net_improvement_5bps)} |")
    status="SOL_LONG_E10_FAIL_GUARD_A16_SUPPORTED" if supported else "SOL_LONG_E10_FAIL_GUARD_A16_REJECTED"
    lines += ["","## Decision","",f"- Validation: **{reason}**.","",f"**Status: {status}**","",
              "A rejected result must not be salvaged by OOS retuning. A supported result may be benchmarked as an additive exit-efficiency improvement to A2+A4.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))

if __name__=="__main__": main()
