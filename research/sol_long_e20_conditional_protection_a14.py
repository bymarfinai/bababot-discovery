#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A11_PATH = Path(__file__).resolve().parent / "sol_long_progressive_risk_floor_a11.py"
spec = importlib.util.spec_from_file_location("sol_a11", A11_PATH)
a11 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a11)
a4 = a11.a4
a2 = a11.a2

OUT_MD = ROOT / "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_Result.md"
OUT_DEV = ROOT / "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_Status.txt"

LANES = ("CP_ANCHOR_FULL", "CP_ANCHOR_HALF", "CP_E10_5_FULL", "CP_E10_10_FULL")
E10_R = 0.10
E20_R = 0.20
STRESS = a2.STRESS
EPS = 1e-12


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def fmt_num(v, d=2):
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
    if i >= len(idx) or idx[i] != t:
        return -1
    return i


def signal_for_trade(m, entry_ts, exit_ts, H, R, lane):
    idx, hi, cl = m["idx"], m["high"], m["close"]
    ei = idx_of(idx, entry_ts)
    xi = idx_of(idx, exit_ts)
    if ei < 0 or xi < 0 or xi < ei:
        return None
    e10 = H + E10_R * R
    e20 = H + E20_R * R
    e20_i = -1
    for i in range(ei, xi + 1):
        if float(hi[i]) >= e20 - EPS:
            e20_i = i
            break
    if e20_i < 0:
        return None

    if lane in ("CP_ANCHOR_FULL", "CP_ANCHOR_HALF"):
        if float(cl[e20_i]) < e20 - EPS:
            return {"signal_i": e20_i, "e20_i": e20_i, "signal_reason": "WEAK_E20_CLOSE"}
        return None

    max_steps = 1 if lane == "CP_E10_5_FULL" else 2
    for j in range(1, max_steps + 1):
        i = e20_i + j
        if i >= xi or i >= len(idx):
            break
        if float(cl[i]) <= e10 + EPS:
            return {"signal_i": i, "e20_i": e20_i, "signal_reason": f"E10_FAIL_{j*5}M"}
    return None


def candidate_trade(m, *, role, partition, dev_block, execution_start, parent_entry_ts,
                    component, entry_ts, entry_price, exit_ts, exit_price, exit_reason,
                    baseline_pnl, baseline_pnl_5bps, H, L, R, lane):
    idx, op = m["idx"], m["open"]
    sig = signal_for_trade(m, entry_ts, exit_ts, H, R, lane)
    xi = idx_of(idx, exit_ts)
    if xi < 0:
        raise RuntimeError(f"baseline exit timestamp missing {exit_ts}")

    intervention = False
    signal_ts = pd.NaT
    action_ts = pd.Timestamp(exit_ts)
    action_price = float(exit_price)
    cand_exit_reason = str(exit_reason)
    partial_frac = 0.0

    if sig is not None:
        signal_i = int(sig["signal_i"])
        ni = signal_i + 1
        # Cannot act after or at a frozen exit that already occurs first.
        if ni < xi and ni < len(idx):
            intervention = True
            signal_ts = idx[signal_i]
            action_ts = idx[ni]
            action_price = float(op[ni])
            cand_exit_reason = "A14_" + str(sig["signal_reason"])

    if intervention and lane == "CP_ANCHOR_HALF":
        partial_frac = 0.50
        ret_action = action_price / float(entry_price) - 1.0
        ret_runner = float(exit_price) / float(entry_price) - 1.0
        ret = partial_frac * ret_action + (1.0 - partial_frac) * ret_runner
        final_exit_ts = pd.Timestamp(exit_ts)
        final_exit_price = float(exit_price)
        cand_exit_reason = "A14_WEAK_E20_HALF+" + str(exit_reason)
    elif intervention:
        ret = action_price / float(entry_price) - 1.0
        final_exit_ts = action_ts
        final_exit_price = action_price
    else:
        ret = float(exit_price) / float(entry_price) - 1.0
        final_exit_ts = pd.Timestamp(exit_ts)
        final_exit_price = float(exit_price)

    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    return {
        "role": role, "partition": partition, "dev_block": dev_block,
        "execution_start": execution_start, "parent_entry_ts": parent_entry_ts,
        "lane": lane, "component": component,
        "H": H, "L": L, "R": R,
        "entry_ts": entry_ts, "entry_price": float(entry_price),
        "baseline_exit_ts": exit_ts, "baseline_exit_price": float(exit_price),
        "baseline_exit_reason": str(exit_reason),
        "baseline_pnl": float(baseline_pnl), "baseline_pnl_5bps": float(baseline_pnl_5bps),
        "intervention": intervention,
        "signal_ts": signal_ts,
        "candidate_exit_ts": final_exit_ts,
        "candidate_exit_price": final_exit_price,
        "candidate_exit_reason": cand_exit_reason,
        "partial_fraction": partial_frac,
        "candidate_pnl": pnl,
        "candidate_pnl_5bps": pnl5,
    }


def simulate_lane(parent, h2, m, lane):
    pmap = {key4(r.role, r.partition, r.execution_start, r.entry_ts): r for _, r in parent.iterrows()}
    hmap = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in h2.iterrows()}
    prows = []
    for _, r in parent.iterrows():
        prows.append(candidate_trade(
            m, role=r.role, partition=r.partition, dev_block=r.dev_block,
            execution_start=r.execution_start, parent_entry_ts=r.entry_ts,
            component="PARENT", entry_ts=r.entry_ts, entry_price=r.entry_price,
            exit_ts=r.exit_ts, exit_price=r.exit_price, exit_reason=r.exit_reason,
            baseline_pnl=r.pnl, baseline_pnl_5bps=r.pnl_5bps,
            H=float(r.H), L=float(r.L), R=float(r.R), lane=lane,
        ))
    pr = pd.DataFrame(prows)
    cpm = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}

    hrows = []
    for k, hr in hmap.items():
        cp = cpm.get(k)
        if cp is None:
            raise RuntimeError(f"candidate parent mapping missing {k}")
        # Keep frozen A4 recovery only when candidate parent remains raw non-positive.
        if float(cp.candidate_pnl) > 0:
            continue
        hrows.append(candidate_trade(
            m, role=hr.role, partition=hr.partition, dev_block=hr.dev_block,
            execution_start=hr.execution_start, parent_entry_ts=hr.parent_entry_ts,
            component="REC_H2", entry_ts=hr.recovery_entry_ts,
            entry_price=hr.recovery_entry_price, exit_ts=hr.recovery_exit_ts,
            exit_price=hr.recovery_exit_price, exit_reason=hr.recovery_exit_reason,
            baseline_pnl=hr.recovery_pnl, baseline_pnl_5bps=hr.recovery_pnl_5bps,
            H=float(hr.H), L=float(hr.L), R=float(hr.R), lane=lane,
        ))
    return pr, pd.DataFrame(hrows)


def h2_map(h2):
    return {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in h2.iterrows()}


def baseline_episode(parent_q, h2_q):
    hm = h2_map(h2_q)
    rows = []
    for _, r in parent_q.iterrows():
        k = key4(r.role, r.partition, r.execution_start, r.entry_ts)
        hr = hm.get(k)
        hp = float(hr.recovery_pnl) if hr is not None and float(r.pnl) <= 0 else 0.0
        hp5 = float(hr.recovery_pnl_5bps) if hr is not None and float(r.pnl) <= 0 else 0.0
        rows.append({"dev_block": r.dev_block, "episode_pnl": float(r.pnl)+hp, "episode_pnl_5bps": float(r.pnl_5bps)+hp5})
    return pd.DataFrame(rows)


def candidate_episode(pr, rr):
    rm = {}
    if rr is not None and len(rr):
        rm = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in rr.iterrows()}
    rows = []
    for _, r in pr.iterrows():
        k = key4(r.role, r.partition, r.execution_start, r.parent_entry_ts)
        hr = rm.get(k)
        hp = float(hr.candidate_pnl) if hr is not None else 0.0
        hp5 = float(hr.candidate_pnl_5bps) if hr is not None else 0.0
        rows.append({"dev_block": r.dev_block, "episode_pnl": float(r.candidate_pnl)+hp, "episode_pnl_5bps": float(r.candidate_pnl_5bps)+hp5})
    return pd.DataFrame(rows)


def stack_vals(parent_q, h2_q, candidate=False):
    if candidate:
        x = pd.to_numeric(parent_q.candidate_pnl, errors="coerce")
        x5 = pd.to_numeric(parent_q.candidate_pnl_5bps, errors="coerce")
        if h2_q is not None and len(h2_q):
            x = pd.concat([x, pd.to_numeric(h2_q.candidate_pnl, errors="coerce")], ignore_index=True)
            x5 = pd.concat([x5, pd.to_numeric(h2_q.candidate_pnl_5bps, errors="coerce")], ignore_index=True)
    else:
        x = pd.to_numeric(parent_q.pnl, errors="coerce")
        x5 = pd.to_numeric(parent_q.pnl_5bps, errors="coerce")
        if h2_q is not None and len(h2_q):
            x = pd.concat([x, pd.to_numeric(h2_q.recovery_pnl, errors="coerce")], ignore_index=True)
            x5 = pd.concat([x5, pd.to_numeric(h2_q.recovery_pnl_5bps, errors="coerce")], ignore_index=True)
    return x, x5


def summarize(parent_base, h2_base, pr, rr):
    be = baseline_episode(parent_base, h2_base)
    ce = candidate_episode(pr, rr)
    bx, bx5 = stack_vals(parent_base, h2_base, candidate=False)
    cx, cx5 = stack_vals(pr, rr, candidate=True)
    base_winners = parent_base[pd.to_numeric(parent_base.pnl, errors="coerce") > 0]
    cpmap = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}
    preserved = 0
    for _, r in base_winners.iterrows():
        k = key4(r.role, r.partition, r.execution_start, r.entry_ts)
        if k in cpmap and float(cpmap[k].candidate_pnl) > 0:
            preserved += 1
    wp = preserved / len(base_winners) if len(base_winners) else np.nan
    return {
        "parent_n": len(parent_base),
        "parent_interventions": int(pr.intervention.astype(bool).sum()),
        "h2_retained_n": len(rr) if rr is not None else 0,
        "h2_interventions": int(rr.intervention.astype(bool).sum()) if rr is not None and len(rr) else 0,
        "winner_preservation": wp,
        "base_episode_wr": float((be.episode_pnl > 0).mean()),
        "candidate_episode_wr": float((ce.episode_pnl > 0).mean()),
        "base_episode_pf": pf(be.episode_pnl),
        "candidate_episode_pf": pf(ce.episode_pnl),
        "base_episode_net": float(be.episode_pnl.sum()),
        "candidate_episode_net": float(ce.episode_pnl.sum()),
        "base_episode_gross_loss": float(-be.loc[be.episode_pnl <= 0, "episode_pnl"].sum()),
        "candidate_episode_gross_loss": float(-ce.loc[ce.episode_pnl <= 0, "episode_pnl"].sum()),
        "base_stack_pf": pf(bx), "candidate_stack_pf": pf(cx),
        "base_stack_net": float(bx.sum()), "candidate_stack_net": float(cx.sum()),
        "stack_net_improvement": float(cx.sum()-bx.sum()),
        "base_stack_pf_5bps": pf(bx5), "candidate_stack_pf_5bps": pf(cx5),
        "base_stack_net_5bps": float(bx5.sum()), "candidate_stack_net_5bps": float(cx5.sum()),
        "stack_net_improvement_5bps": float(cx5.sum()-bx5.sum()),
    }


def development_row(parent_q, h2_q, pr, rr, lane):
    s = summarize(parent_q, h2_q, pr, rr)
    pos_raw = 0
    pos_stress = 0
    adequate = 0
    block = {}
    for bi in range(6):
        pb = parent_q[pd.to_numeric(parent_q.dev_block, errors="coerce") == bi]
        hb = h2_q[pd.to_numeric(h2_q.dev_block, errors="coerce") == bi]
        pcb = pr[pd.to_numeric(pr.dev_block, errors="coerce") == bi]
        rrb = rr[pd.to_numeric(rr.dev_block, errors="coerce") == bi] if rr is not None and len(rr) else pd.DataFrame()
        bx, bx5 = stack_vals(pb, hb, candidate=False)
        cx, cx5 = stack_vals(pcb, rrb, candidate=True)
        d = float(cx.sum()-bx.sum())
        d5 = float(cx5.sum()-bx5.sum())
        block[f"b{bi+1}_net_improvement"] = d
        block[f"b{bi+1}_net_improvement_5bps"] = d5
        if len(bx) >= 20:
            adequate += 1
            if d > 0: pos_raw += 1
            if d5 > 0: pos_stress += 1
    eligible = bool(
        s["parent_n"] == len(parent_q)
        and s["stack_net_improvement"] > 0
        and s["stack_net_improvement_5bps"] > 0
        and s["candidate_stack_pf"] > s["base_stack_pf"]
        and s["candidate_stack_pf_5bps"] > s["base_stack_pf_5bps"]
        and s["candidate_episode_gross_loss"] <= s["base_episode_gross_loss"] + 1e-9
        and s["candidate_episode_wr"] >= s["base_episode_wr"] - 1e-12
        and s["winner_preservation"] >= 0.98
        and pos_raw >= 4 and pos_stress >= 4
    )
    return {"lane": lane, **s, "adequate_blocks": adequate, "positive_blocks": pos_raw,
            "positive_blocks_5bps": pos_stress, "eligible": eligible, **block}


def choose_dev(dev):
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    return q.sort_values([
        "stack_net_improvement_5bps", "stack_net_improvement", "candidate_episode_wr",
        "candidate_stack_pf_5bps", "lane"
    ], ascending=[False, False, False, False, True]).iloc[0]


def main():
    parent, h2, m, coverage = a11.load_system()
    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    cd_h2 = h2[(h2.role == "CENTRAL") & (h2.partition == "development")].copy()
    if len(cd_parent) != 617:
        raise RuntimeError(f"A2 Central Development parity failed: {len(cd_parent)}")

    dev_rows = []
    dev_trades = {}
    for lane in LANES:
        pr_all, rr_all = simulate_lane(parent, h2, m, lane)
        pr = pr_all[(pr_all.role == "CENTRAL") & (pr_all.partition == "development")].copy()
        rr = rr_all[(rr_all.role == "CENTRAL") & (rr_all.partition == "development")].copy()
        dev_rows.append(development_row(cd_parent, cd_h2, pr, rr, lane))
        dev_trades[lane] = (pr_all, rr_all)
    dev = pd.DataFrame(dev_rows)
    winner = choose_dev(dev)

    frozen_lane = None
    oos_rows = []
    selected_frames = []
    supported = False
    reason = "No Development conditional-protection lane passed"
    if winner is not None:
        frozen_lane = str(winner.lane)
        pr_all, rr_all = dev_trades[frozen_lane]
        zd = pd.concat([
            pr_all[(pr_all.role == "CENTRAL") & (pr_all.partition == "development")],
            rr_all[(rr_all.role == "CENTRAL") & (rr_all.partition == "development")]
        ], ignore_index=True)
        zd["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
        selected_frames.append(zd)

        for (role, part), pq in parent.groupby(["role", "partition"], sort=False):
            if role == "CENTRAL" and part == "development":
                continue
            if part not in ["external", "reference_validation"]:
                continue
            hq = h2[(h2.role == role) & (h2.partition == part)].copy()
            pr = pr_all[(pr_all.role == role) & (pr_all.partition == part)].copy()
            rr = rr_all[(rr_all.role == role) & (rr_all.partition == part)].copy()
            s = summarize(pq, hq, pr, rr)
            oos_rows.append({"role": role, "partition": part, "lane": frozen_lane, **s})
            if len(pr) or len(rr):
                zz = pd.concat([pr, rr], ignore_index=True)
                zz["selection_scope"] = "FROZEN_OOS"
                selected_frames.append(zz)
        oos = pd.DataFrame(oos_rows)

        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        cr = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        central_ok = False
        if len(ce) == 1 and len(cr) == 1:
            central_ok = all(
                float(r.stack_net_improvement) > 0
                and float(r.stack_net_improvement_5bps) > 0
                and float(r.candidate_stack_pf) >= float(r.base_stack_pf)
                and float(r.candidate_stack_pf_5bps) >= float(r.base_stack_pf_5bps)
                and float(r.candidate_episode_gross_loss) <= float(r.base_episode_gross_loss) + 1e-9
                and float(r.winner_preservation) >= 0.97
                for _, r in pd.concat([ce, cr]).iterrows()
            )
        support = oos[oos.role.isin(["CLOCK_SUPPORT", "REF_SUPPORT"])].copy()
        raw_pos = int((support.stack_net_improvement > 0).sum())
        stress_pos = int((support.stack_net_improvement_5bps > 0).sum())
        support_ok = len(support) >= 4 and raw_pos >= 3 and stress_pos >= 3
        supported = bool(central_ok and support_ok)
        reason = f"central_ok={central_ok}; support positive raw={raw_pos}/4; support positive 5bps={stress_pos}/4"
    else:
        oos = pd.DataFrame()

    dev.to_csv(OUT_DEV, index=False)
    oos.to_csv(OUT_OOS, index=False)
    trades = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame()
    trades.to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG E20 Conditional Protection — A14 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A14 tests only A13-derived conditional E20 weakness states on the supported A2+A4 stack.", "",
        "## Central Development", "",
        "| Lane | Parent interventions | H2 retained | H2 interventions | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |",
        "|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.parent_interventions)} | {int(r.h2_retained_n)} | {int(r.h2_interventions)} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.base_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${fmt_num(r.base_episode_gross_loss)}→${fmt_num(r.candidate_episode_gross_loss)} | {fmt_num(r.base_stack_pf)}→{fmt_num(r.candidate_stack_pf)} | ${fmt_num(r.stack_net_improvement)} | {fmt_num(r.base_stack_pf_5bps)}→{fmt_num(r.candidate_stack_pf_5bps)} | ${fmt_num(r.stack_net_improvement_5bps)} | {int(r.positive_blocks)}/{int(r.positive_blocks_5bps)} | {'YES' if r.eligible else 'NO'} |"
        )
    lines += ["", f"Frozen Development winner: **{frozen_lane if frozen_lane else 'NONE'}**.", ""]

    if len(oos):
        lines += ["", "## Frozen OOS", "",
                  "| Role | Partition | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ |",
                  "|---|---|---:|---|---|---|---:|---|---:|"]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.base_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${fmt_num(r.base_episode_gross_loss)}→${fmt_num(r.candidate_episode_gross_loss)} | {fmt_num(r.base_stack_pf)}→{fmt_num(r.candidate_stack_pf)} | ${fmt_num(r.stack_net_improvement)} | {fmt_num(r.base_stack_pf_5bps)}→{fmt_num(r.candidate_stack_pf_5bps)} | ${fmt_num(r.stack_net_improvement_5bps)} |"
            )

    status = "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_SUPPORTED" if supported else "SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_REJECTED"
    lines += ["", "## Decision", "", f"- Validation: **{reason}**.", "", f"**Status: {status}**", "",
              "A rejected result must not be salvaged by OOS retuning. A supported result authorizes only the frozen A14 rule for subsequent full-stack benchmarking.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
