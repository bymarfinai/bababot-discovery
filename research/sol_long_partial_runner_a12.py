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

OUT_MD = ROOT / "SOL_LONG_PARTIAL_RUNNER_A12_Result.md"
OUT_DEV = ROOT / "SOL_LONG_PARTIAL_RUNNER_A12_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_PARTIAL_RUNNER_A12_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_PARTIAL_RUNNER_A12_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_PARTIAL_RUNNER_A12_Status.txt"

TARGET_R = 0.40
PARTIAL_R = 0.20
STRESS = a2.STRESS
EPS = 1e-12
LANES = ("PP20_25", "PP20_50", "HY20_25", "HY20_50")


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


def lane_params(lane):
    if lane == "PP20_25": return 0.25, False
    if lane == "PP20_50": return 0.50, False
    if lane == "HY20_25": return 0.25, True
    if lane == "HY20_50": return 0.50, True
    raise ValueError(lane)


def runner_floor_R(lane, running_mfe_R):
    _, hybrid = lane_params(lane)
    if not hybrid:
        return None
    if running_mfe_R >= 0.35 - EPS:
        return 0.20
    if running_mfe_R >= 0.30 - EPS:
        return 0.10
    return None


def next_open_exit(m, close_i, endpos):
    ni = close_i + 1
    if ni < endpos:
        return ni, float(m["open"][ni])
    return close_i, float(m["close"][close_i])


def weighted_trade_result(entry_price, partial_price, partial_frac, partial_hit, runner_exit_price):
    if partial_hit:
        ret_partial = partial_price / entry_price - 1.0
        ret_runner = runner_exit_price / entry_price - 1.0
        ret = partial_frac * ret_partial + (1.0 - partial_frac) * ret_runner
    else:
        ret = runner_exit_price / entry_price - 1.0
    pnl = ret * a2.NOTIONAL
    ret5 = ret - STRESS
    pnl5 = ret5 * a2.NOTIONAL
    return ret, pnl, ret5, pnl5


def replay_core(m, *, role, partition, dev_block, execution_start, parent_entry_ts,
                entry_ts, entry_price, H, L, R, endpos, confirmed_initial,
                break_ts, dynamic_confirm, baseline_exit_ts, baseline_exit_reason,
                baseline_pnl, baseline_pnl_5bps, lane, component):
    idx, hi, cl = m["idx"], m["high"], m["close"]
    ei = int(idx.searchsorted(pd.Timestamp(entry_ts), "left"))
    if ei >= len(idx) or idx[ei] != pd.Timestamp(entry_ts) or ei >= endpos:
        raise RuntimeError(f"{component} entry timestamp parity failure {entry_ts}")

    partial_frac, hybrid = lane_params(lane)
    partial_px = H + PARTIAL_R * R
    target_px = H + TARGET_R * R
    confirmed = bool(confirmed_initial)
    break_i = -1
    if pd.notna(break_ts):
        break_i = int(idx.searchsorted(pd.Timestamp(break_ts), "left"))

    running_mfe_R = max(0.0, (float(hi[ei]) - H) / R)
    partial_hit = False
    partial_ts = pd.NaT
    active_floor_R = None
    runner_floor_triggered = False

    exit_i = endpos - 1
    exit_price = float(cl[exit_i])
    reason = "TIME"

    for i in range(ei + 1, endpos):
        if not confirmed:
            if break_i >= 0 and i >= break_i:
                confirmed = True
            elif dynamic_confirm and float(cl[i]) > H:
                confirmed = True

        # Resting E20 partial fills before an E40 runner target if both are traversed.
        if not partial_hit and float(hi[i]) >= partial_px:
            partial_hit = True
            partial_ts = idx[i]

        # Remaining runner keeps the frozen E40 target.
        if float(hi[i]) >= target_px:
            exit_i, exit_price, reason = i, target_px, "TARGET"
            break

        running_mfe_R = max(running_mfe_R, max(0.0, (float(hi[i]) - H) / R))
        if partial_hit and confirmed and hybrid:
            fr = runner_floor_R(lane, running_mfe_R)
            if fr is not None:
                active_floor_R = fr if active_floor_R is None else max(active_floor_R, fr)

        if partial_hit and confirmed and active_floor_R is not None:
            floor_px = H + active_floor_R * R
            if float(cl[i]) > H and float(cl[i]) <= floor_px + EPS:
                exit_i, exit_price = next_open_exit(m, i, endpos)
                reason = "RUNNER_FLOOR"
                runner_floor_triggered = True
                break

        bad = (float(cl[i]) <= H) if confirmed else (float(cl[i]) < L)
        if bad:
            exit_i, exit_price = next_open_exit(m, i, endpos)
            reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            break

    ret, pnl, ret5, pnl5 = weighted_trade_result(
        float(entry_price), partial_px, partial_frac, partial_hit, exit_price
    )
    return {
        "role": role, "partition": partition, "dev_block": dev_block,
        "execution_start": execution_start, "parent_entry_ts": parent_entry_ts,
        "lane": lane, "component": component, "H": H, "L": L, "R": R,
        "entry_ts": entry_ts, "entry_price": float(entry_price),
        "partial_fraction": partial_frac, "partial_hit": partial_hit,
        "partial_ts": partial_ts, "partial_price": partial_px if partial_hit else np.nan,
        "baseline_exit_ts": baseline_exit_ts, "baseline_exit_reason": baseline_exit_reason,
        "baseline_pnl": float(baseline_pnl), "baseline_pnl_5bps": float(baseline_pnl_5bps),
        "candidate_exit_ts": idx[exit_i], "candidate_exit_price": exit_price,
        "candidate_exit_reason": reason, "candidate_return": ret,
        "candidate_pnl": pnl, "candidate_return_5bps": ret5, "candidate_pnl_5bps": pnl5,
        "runner_floor_triggered": runner_floor_triggered,
        "final_active_floor_R": active_floor_R,
        "running_mfe_R_at_exit": running_mfe_R,
    }


def replay_parent(m, r, lane):
    idx = m["idx"]
    entry_ts = pd.Timestamp(r.entry_ts)
    ei = int(idx.searchsorted(entry_ts, "left"))
    if ei >= len(idx) or idx[ei] != entry_ts:
        raise RuntimeError(f"parent entry timestamp parity failure {entry_ts}")
    _, pz = a2.part_bounds(r.partition)
    end_ts = min(pd.Timestamp(r.execution_start) + pd.Timedelta(minutes=a2.a1.XMIN), pz)
    endpos = min(int(idx.searchsorted(end_ts, "left")), len(idx))
    break_ts = r.h1_break_ts
    confirmed_initial = pd.notna(break_ts) and pd.Timestamp(break_ts) == entry_ts
    return replay_core(
        m, role=r.role, partition=r.partition, dev_block=r.dev_block,
        execution_start=r.execution_start, parent_entry_ts=r.entry_ts,
        entry_ts=r.entry_ts, entry_price=float(r.entry_price),
        H=float(r.H), L=float(r.L), R=float(r.R), endpos=endpos,
        confirmed_initial=confirmed_initial, break_ts=break_ts, dynamic_confirm=False,
        baseline_exit_ts=r.exit_ts, baseline_exit_reason=r.exit_reason,
        baseline_pnl=r.pnl, baseline_pnl_5bps=r.pnl_5bps,
        lane=lane, component="PARENT",
    )


def replay_h2(m, hr, parent_row, lane):
    w = a4.recovery_window(m, parent_row)
    if w is None:
        raise RuntimeError("A4 recovery window missing for persisted H2 trade")
    _, _, endpos, _ = w
    entry_ts = pd.Timestamp(hr.recovery_entry_ts)
    idx, cl = m["idx"], m["close"]
    ei = int(idx.searchsorted(entry_ts, "left"))
    if ei >= len(idx) or idx[ei] != entry_ts or ei >= endpos:
        raise RuntimeError(f"H2 entry timestamp parity failure {entry_ts}")
    confirmed_initial = bool(float(cl[ei]) > float(hr.H))
    return replay_core(
        m, role=hr.role, partition=hr.partition, dev_block=hr.dev_block,
        execution_start=hr.execution_start, parent_entry_ts=hr.parent_entry_ts,
        entry_ts=hr.recovery_entry_ts, entry_price=float(hr.recovery_entry_price),
        H=float(hr.H), L=float(hr.L), R=float(hr.R), endpos=endpos,
        confirmed_initial=confirmed_initial, break_ts=hr.recovery_break_ts, dynamic_confirm=True,
        baseline_exit_ts=hr.recovery_exit_ts, baseline_exit_reason=hr.recovery_exit_reason,
        baseline_pnl=hr.recovery_pnl, baseline_pnl_5bps=hr.recovery_pnl_5bps,
        lane=lane, component="REC_H2",
    )


def parent_maps(parent):
    return {key4(r.role, r.partition, r.execution_start, r.entry_ts): r for _, r in parent.iterrows()}


def h2_maps(h2):
    return {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in h2.iterrows()}


def simulate_lane(parent, h2, m, lane):
    pmap = parent_maps(parent)
    hmap = h2_maps(h2)
    pr = pd.DataFrame([replay_parent(m, r, lane) for _, r in parent.iterrows()])
    cpm = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}
    hrows = []
    for k, hr in hmap.items():
        cp = cpm.get(k)
        if cp is None:
            raise RuntimeError(f"candidate parent mapping missing {k}")
        if float(cp.candidate_pnl) > 0:
            continue
        hrows.append(replay_h2(m, hr, pmap[k], lane))
    rr = pd.DataFrame(hrows)
    return pr, rr


def baseline_episode(parent_q, h2_q):
    hm = h2_maps(h2_q)
    rows = []
    for _, r in parent_q.iterrows():
        k = key4(r.role, r.partition, r.execution_start, r.entry_ts)
        hr = hm.get(k)
        hp = float(hr.recovery_pnl) if hr is not None and float(r.pnl) <= 0 else 0.0
        hp5 = float(hr.recovery_pnl_5bps) if hr is not None and float(r.pnl) <= 0 else 0.0
        rows.append({"role": r.role, "partition": r.partition, "dev_block": r.dev_block,
                     "execution_start": r.execution_start, "parent_entry_ts": r.entry_ts,
                     "episode_pnl": float(r.pnl) + hp,
                     "episode_pnl_5bps": float(r.pnl_5bps) + hp5})
    return pd.DataFrame(rows)


def candidate_episode(pr_q, rr_q):
    rm = {}
    if rr_q is not None and len(rr_q):
        rm = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in rr_q.iterrows()}
    rows = []
    for _, r in pr_q.iterrows():
        k = key4(r.role, r.partition, r.execution_start, r.parent_entry_ts)
        hr = rm.get(k)
        hp = float(hr.candidate_pnl) if hr is not None else 0.0
        hp5 = float(hr.candidate_pnl_5bps) if hr is not None else 0.0
        rows.append({"role": r.role, "partition": r.partition, "dev_block": r.dev_block,
                     "execution_start": r.execution_start, "parent_entry_ts": r.parent_entry_ts,
                     "episode_pnl": float(r.candidate_pnl) + hp,
                     "episode_pnl_5bps": float(r.candidate_pnl_5bps) + hp5})
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


def block_stack_net(parent_q, h2_q, bi, candidate=False):
    pq = parent_q[pd.to_numeric(parent_q.dev_block, errors="coerce") == bi]
    if h2_q is None or not len(h2_q):
        hq = pd.DataFrame()
    else:
        hq = h2_q[pd.to_numeric(h2_q.dev_block, errors="coerce") == bi]
    x, x5 = stack_vals(pq, hq, candidate=candidate)
    return float(x.sum()), float(x5.sum()), len(x)


def summarize(parent_base, h2_base, pr, rr):
    be = baseline_episode(parent_base, h2_base)
    ce = candidate_episode(pr, rr)
    bx, bx5 = stack_vals(parent_base, h2_base, candidate=False)
    cx, cx5 = stack_vals(pr, rr, candidate=True)
    bpw = parent_base[pd.to_numeric(parent_base.pnl, errors="coerce") > 0]
    win_keys = {key4(r.role, r.partition, r.execution_start, r.entry_ts) for _, r in bpw.iterrows()}
    cpmap = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}
    preserved = sum(1 for k in win_keys if k in cpmap and float(cpmap[k].candidate_pnl) > 0)
    winner_preservation = preserved / len(win_keys) if win_keys else np.nan
    return {
        "parent_n": len(parent_base),
        "parent_partial_hits": int(pr.partial_hit.sum()),
        "h2_retained_n": 0 if rr is None else len(rr),
        "h2_partial_hits": 0 if rr is None or not len(rr) else int(rr.partial_hit.sum()),
        "parent_runner_floor_triggers": int(pr.runner_floor_triggered.sum()),
        "h2_runner_floor_triggers": 0 if rr is None or not len(rr) else int(rr.runner_floor_triggered.sum()),
        "winner_preservation": winner_preservation,
        "episode_wr_base": float((be.episode_pnl > 0).mean()),
        "episode_wr_new": float((ce.episode_pnl > 0).mean()),
        "episode_pf_base": pf(be.episode_pnl), "episode_pf_new": pf(ce.episode_pnl),
        "episode_net_base": float(be.episode_pnl.sum()), "episode_net_new": float(ce.episode_pnl.sum()),
        "episode_gross_loss_base": float(-be.loc[be.episode_pnl <= 0, "episode_pnl"].sum()),
        "episode_gross_loss_new": float(-ce.loc[ce.episode_pnl <= 0, "episode_pnl"].sum()),
        "stack_pf_base": pf(bx), "stack_pf_new": pf(cx),
        "stack_net_base": float(bx.sum()), "stack_net_new": float(cx.sum()),
        "stack_net_improvement": float(cx.sum() - bx.sum()),
        "stack_pf_5bps_base": pf(bx5), "stack_pf_5bps_new": pf(cx5),
        "stack_net_5bps_base": float(bx5.sum()), "stack_net_5bps_new": float(cx5.sum()),
        "stack_net_improvement_5bps": float(cx5.sum() - bx5.sum()),
    }


def development_row(parent_q, h2_q, pr, rr, lane):
    s = summarize(parent_q, h2_q, pr, rr)
    pos_raw = pos_stress = adequate = 0
    block = {}
    for bi in range(6):
        b0, b05, n0 = block_stack_net(parent_q, h2_q, bi, candidate=False)
        b1, b15, n1 = block_stack_net(pr, rr, bi, candidate=True)
        dr, ds = b1 - b0, b15 - b05
        block[f"b{bi+1}_n"] = n1
        block[f"b{bi+1}_net_delta"] = dr
        block[f"b{bi+1}_net_delta_5bps"] = ds
        if n0 >= 5 and n1 >= 5:
            adequate += 1
            if dr > 0: pos_raw += 1
            if ds > 0: pos_stress += 1
    eligible = bool(
        s["parent_n"] == len(parent_q)
        and s["stack_net_improvement"] > 0
        and s["stack_net_improvement_5bps"] > 0
        and s["stack_pf_new"] > s["stack_pf_base"]
        and s["stack_pf_5bps_new"] > s["stack_pf_5bps_base"]
        and s["episode_gross_loss_new"] <= s["episode_gross_loss_base"] + 1e-9
        and s["episode_wr_new"] >= s["episode_wr_base"] - 1e-12
        and s["winner_preservation"] >= 0.98
        and pos_raw >= 4 and pos_stress >= 4
    )
    return {"lane": lane, **s, "adequate_blocks": adequate,
            "positive_blocks_raw": pos_raw, "positive_blocks_5bps": pos_stress,
            "eligible": eligible, **block}


def choose_dev(dev):
    q = dev[dev.eligible].copy()
    if q.empty: return None
    q["hybrid"] = q.lane.str.startswith("HY")
    q["partial_frac"] = q.lane.map(lambda x: lane_params(x)[0])
    return q.sort_values(
        ["stack_net_improvement_5bps", "stack_net_improvement", "stack_pf_5bps_new",
         "episode_wr_new", "hybrid", "partial_frac"],
        ascending=[False, False, False, False, True, True],
    ).iloc[0]


def main():
    parent, h2, m, coverage = a11.load_system()
    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    cd_h2 = h2[(h2.role == "CENTRAL") & (h2.partition == "development")].copy()
    if len(cd_parent) != 617:
        raise RuntimeError(f"A2 central Development N parity failed: {len(cd_parent)}")
    if abs(float(cd_parent.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("A2 central Development net parity failed")

    dev_rows, dev_frames = [], {}
    for lane in LANES:
        pr, rr = simulate_lane(cd_parent, cd_h2, m, lane)
        dev_frames[lane] = (pr, rr)
        dev_rows.append(development_row(cd_parent, cd_h2, pr, rr, lane))
    dev = pd.DataFrame(dev_rows)
    winner = choose_dev(dev)

    oos_rows = []
    selected_frames = []
    supported = False
    frozen_lane = None
    reason = "No Development partial/runner lane passed"

    if winner is not None:
        frozen_lane = str(winner.lane)
        prd, rrd = dev_frames[frozen_lane]
        prd = prd.copy(); prd["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
        selected_frames.append(prd)
        if len(rrd):
            rrd = rrd.copy(); rrd["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
            selected_frames.append(rrd)

        for (role, part), pq in parent.groupby(["role", "partition"], sort=False):
            if role == "CENTRAL" and part == "development":
                continue
            if part not in ["external", "reference_validation"]:
                continue
            hq = h2[(h2.role == role) & (h2.partition == part)].copy()
            pr, rr = simulate_lane(pq.copy(), hq, m, frozen_lane)
            s = summarize(pq.copy(), hq, pr, rr)
            oos_rows.append({"role": role, "partition": part, "lane": frozen_lane, **s})
            pr = pr.copy(); pr["selection_scope"] = "FROZEN_OOS"; selected_frames.append(pr)
            if len(rr):
                rr = rr.copy(); rr["selection_scope"] = "FROZEN_OOS"; selected_frames.append(rr)
        oos = pd.DataFrame(oos_rows)

        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        cr = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        central_ok = False
        if len(ce) == 1 and len(cr) == 1:
            central_ok = all(
                float(r.stack_net_improvement) > 0
                and float(r.stack_net_improvement_5bps) > 0
                and float(r.stack_pf_new) >= float(r.stack_pf_base) - 1e-12
                and float(r.stack_pf_5bps_new) >= float(r.stack_pf_5bps_base) - 1e-12
                and float(r.episode_gross_loss_new) <= float(r.episode_gross_loss_base) + 1e-9
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
    if selected_frames:
        pd.concat(selected_frames, ignore_index=True).to_csv(OUT_TRADES, index=False)
    else:
        pd.DataFrame().to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG Partial Profit + Progressive Runner Floor — A12 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A12 tests partial E20 monetization with an E40 runner on the supported A2 parent + A4 REC_H2 stack. Rejected A6/A8/A10/A11 mechanisms remain absent.", "",
        "## Central Development", "",
        "| Lane | Parent E20 hits | H2 retained | H2 E20 hits | Runner-floor triggers P/H2 | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.parent_partial_hits)} | {int(r.h2_retained_n)} | {int(r.h2_partial_hits)} | {int(r.parent_runner_floor_triggers)}/{int(r.h2_runner_floor_triggers)} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.episode_wr_base)}→{fmt_pct(r.episode_wr_new)} | ${r.episode_gross_loss_base:.2f}→${r.episode_gross_loss_new:.2f} | {fmt_num(r.stack_pf_base)}→{fmt_num(r.stack_pf_new)} | ${r.stack_net_improvement:.2f} | {fmt_num(r.stack_pf_5bps_base)}→{fmt_num(r.stack_pf_5bps_new)} | ${r.stack_net_improvement_5bps:.2f} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )
    lines += ["", f"Frozen Development winner: **{frozen_lane or 'NONE'}**.", ""]

    if len(oos):
        lines += ["", "## Frozen OOS", "",
                  "| Role | Partition | Parent E20 hits | H2 retained | Winner preserved | Episode WR base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | Gross loss base→new |",
                  "|---|---|---:|---:|---:|---|---|---:|---|---:|---|"]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | {int(r.parent_partial_hits)} | {int(r.h2_retained_n)} | {fmt_pct(r.winner_preservation)} | {fmt_pct(r.episode_wr_base)}→{fmt_pct(r.episode_wr_new)} | {fmt_num(r.stack_pf_base)}→{fmt_num(r.stack_pf_new)} | ${r.stack_net_improvement:.2f} | {fmt_num(r.stack_pf_5bps_base)}→{fmt_num(r.stack_pf_5bps_new)} | ${r.stack_net_improvement_5bps:.2f} | ${r.episode_gross_loss_base:.2f}→${r.episode_gross_loss_new:.2f} |"
            )

    status = "SOL_LONG_PARTIAL_RUNNER_A12_SUPPORTED" if supported else "SOL_LONG_PARTIAL_RUNNER_A12_REJECTED"
    lines += ["", "## Decision", "", f"- Validation: **{reason}**.", "", f"**Status: {status}**", "",
              "A supported result authorizes only the frozen partial/runner lane for subsequent full-stack benchmarking. A rejected result must not be rescued by OOS retuning.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
