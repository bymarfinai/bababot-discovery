#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A4_PATH = Path(__file__).resolve().parent / "sol_long_h1_loss_recovery_a4.py"
spec = importlib.util.spec_from_file_location("sol_a4", A4_PATH)
a4 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a4)
a2 = a4.a2

IN_H2 = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_Result.md"
OUT_DEV = ROOT / "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_Status.txt"

TARGET_R = 0.40
STRESS = a2.STRESS
EPS = 1e-12
LANES = ("RF_LOOSE", "RF_BALANCED", "RF_TIGHT", "RF_GIVEBACK15")


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


def load_system():
    parent = a4.load_parent()
    _, m, coverage = a4.market()
    h2 = pd.read_csv(IN_H2)
    for c in ["execution_start", "parent_entry_ts", "parent_exit_ts", "recovery_entry_ts", "recovery_break_ts", "recovery_exit_ts"]:
        h2[c] = pd.to_datetime(h2[c], utc=True, errors="coerce")
    h2 = h2[(pd.to_numeric(h2.visit_n, errors="coerce") == 2) & (h2.lane.astype(str) == "REC_H2")].copy()
    h2 = h2.sort_values(["role", "partition", "execution_start", "parent_entry_ts"]).reset_index(drop=True)
    return parent, h2, m, coverage


def floor_R(lane: str, mfe_R: float):
    if lane == "RF_LOOSE":
        if mfe_R >= 0.30 - EPS: return 0.15
        if mfe_R >= 0.20 - EPS: return 0.05
        return None
    if lane == "RF_BALANCED":
        if mfe_R >= 0.35 - EPS: return 0.25
        if mfe_R >= 0.25 - EPS: return 0.15
        if mfe_R >= 0.15 - EPS: return 0.05
        return None
    if lane == "RF_TIGHT":
        if mfe_R >= 0.30 - EPS: return 0.20
        if mfe_R >= 0.20 - EPS: return 0.10
        if mfe_R >= 0.10 - EPS: return 0.05
        return None
    if lane == "RF_GIVEBACK15":
        if mfe_R < 0.20 - EPS:
            return None
        return max(0.05, mfe_R - 0.15)
    raise ValueError(lane)


def next_open_exit(m, close_i: int, endpos: int):
    ni = close_i + 1
    if ni < endpos:
        return ni, float(m["open"][ni])
    return close_i, float(m["close"][close_i])


def replay_parent(m, r, lane):
    idx, op, hi, cl = m["idx"], m["open"], m["high"], m["close"]
    entry_ts = pd.Timestamp(r.entry_ts)
    ei = int(idx.searchsorted(entry_ts, "left"))
    if ei >= len(idx) or idx[ei] != entry_ts:
        raise RuntimeError(f"parent entry timestamp parity failure {entry_ts}")

    _, pz = a2.part_bounds(r.partition)
    end_ts = min(pd.Timestamp(r.execution_start) + pd.Timedelta(minutes=a2.a1.XMIN), pz)
    endpos = min(int(idx.searchsorted(end_ts, "left")), len(idx))
    if endpos <= ei:
        raise RuntimeError("parent lifecycle end before entry")

    H, L, R = float(r.H), float(r.L), float(r.R)
    target = H + TARGET_R * R
    entry_price = float(r.entry_price)
    break_i = -1
    if pd.notna(r.h1_break_ts):
        break_i = int(idx.searchsorted(pd.Timestamp(r.h1_break_ts), "left"))
    confirmed = break_i == ei
    running_mfe_R = max(0.0, (float(hi[ei]) - H) / R)
    active_floor_R = None

    exit_i = endpos - 1
    exit_price = float(cl[exit_i])
    reason = "TIME"
    ratchet_triggered = False

    for i in range(ei + 1, endpos):
        if not confirmed and break_i >= 0 and i >= break_i:
            confirmed = True

        # Preserve frozen target priority.
        if float(hi[i]) >= target:
            exit_i, exit_price, reason = i, target, "TARGET"
            break

        running_mfe_R = max(running_mfe_R, max(0.0, (float(hi[i]) - H) / R))
        if confirmed:
            fr = floor_R(lane, running_mfe_R)
            if fr is not None:
                active_floor_R = fr if active_floor_R is None else max(active_floor_R, fr)

        # Ratchet adds information only when close is still above H; <=H is already frozen failed-break.
        if confirmed and active_floor_R is not None:
            floor_px = H + active_floor_R * R
            if float(cl[i]) > H and float(cl[i]) <= floor_px + EPS:
                exit_i, exit_price = next_open_exit(m, i, endpos)
                reason = "RATCHET_FLOOR"
                ratchet_triggered = True
                break

        bad = (float(cl[i]) <= H) if confirmed else (float(cl[i]) < L)
        if bad:
            exit_i, exit_price = next_open_exit(m, i, endpos)
            reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            break

    ret = exit_price / entry_price - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    return {
        "role": r.role, "partition": r.partition, "dev_block": r.dev_block,
        "execution_start": r.execution_start, "parent_entry_ts": r.entry_ts,
        "lane": lane, "component": "PARENT", "H": H, "L": L, "R": R,
        "entry_ts": r.entry_ts, "entry_price": entry_price,
        "baseline_exit_ts": r.exit_ts, "baseline_exit_reason": r.exit_reason,
        "baseline_pnl": float(r.pnl), "baseline_pnl_5bps": float(r.pnl_5bps),
        "candidate_exit_ts": idx[exit_i], "candidate_exit_price": exit_price,
        "candidate_exit_reason": reason, "candidate_pnl": pnl, "candidate_pnl_5bps": pnl5,
        "ratchet_triggered": ratchet_triggered,
        "final_active_floor_R": active_floor_R,
        "running_mfe_R_at_exit": running_mfe_R,
    }


def replay_h2(m, hr, parent_row, lane):
    idx, op, hi, cl = m["idx"], m["open"], m["high"], m["close"]
    w = a4.recovery_window(m, parent_row)
    if w is None:
        raise RuntimeError("A4 recovery window missing for persisted H2 trade")
    _, _, endpos, _ = w
    entry_ts = pd.Timestamp(hr.recovery_entry_ts)
    ei = int(idx.searchsorted(entry_ts, "left"))
    if ei >= len(idx) or idx[ei] != entry_ts or ei >= endpos:
        raise RuntimeError(f"H2 entry timestamp parity failure {entry_ts}")

    H, L, R = float(hr.H), float(hr.L), float(hr.R)
    target = H + TARGET_R * R
    entry_price = float(hr.recovery_entry_price)
    confirmed = float(cl[ei]) > H
    break_i = -1
    if pd.notna(hr.recovery_break_ts):
        break_i = int(idx.searchsorted(pd.Timestamp(hr.recovery_break_ts), "left"))
    running_mfe_R = max(0.0, (float(hi[ei]) - H) / R)
    active_floor_R = None

    exit_i = endpos - 1
    exit_price = float(cl[exit_i])
    reason = "TIME"
    ratchet_triggered = False

    for i in range(ei + 1, endpos):
        if not confirmed and float(cl[i]) > H:
            confirmed = True
            if break_i < 0:
                break_i = i

        if float(hi[i]) >= target:
            exit_i, exit_price, reason = i, target, "TARGET"
            break

        running_mfe_R = max(running_mfe_R, max(0.0, (float(hi[i]) - H) / R))
        if confirmed:
            fr = floor_R(lane, running_mfe_R)
            if fr is not None:
                active_floor_R = fr if active_floor_R is None else max(active_floor_R, fr)

        if confirmed and active_floor_R is not None:
            floor_px = H + active_floor_R * R
            if float(cl[i]) > H and float(cl[i]) <= floor_px + EPS:
                exit_i, exit_price = next_open_exit(m, i, endpos)
                reason = "RATCHET_FLOOR"
                ratchet_triggered = True
                break

        bad = (float(cl[i]) <= H) if confirmed else (float(cl[i]) < L)
        if bad:
            exit_i, exit_price = next_open_exit(m, i, endpos)
            reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            break

    ret = exit_price / entry_price - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    return {
        "role": hr.role, "partition": hr.partition, "dev_block": hr.dev_block,
        "execution_start": hr.execution_start, "parent_entry_ts": hr.parent_entry_ts,
        "lane": lane, "component": "REC_H2", "H": H, "L": L, "R": R,
        "entry_ts": hr.recovery_entry_ts, "entry_price": entry_price,
        "baseline_exit_ts": hr.recovery_exit_ts, "baseline_exit_reason": hr.recovery_exit_reason,
        "baseline_pnl": float(hr.recovery_pnl), "baseline_pnl_5bps": float(hr.recovery_pnl_5bps),
        "candidate_exit_ts": idx[exit_i], "candidate_exit_price": exit_price,
        "candidate_exit_reason": reason, "candidate_pnl": pnl, "candidate_pnl_5bps": pnl5,
        "ratchet_triggered": ratchet_triggered,
        "final_active_floor_R": active_floor_R,
        "running_mfe_R_at_exit": running_mfe_R,
    }


def parent_maps(parent):
    return {key4(r.role, r.partition, r.execution_start, r.entry_ts): r for _, r in parent.iterrows()}


def h2_maps(h2):
    return {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in h2.iterrows()}


def simulate_lane(parent, h2, m, lane):
    pmap = parent_maps(parent)
    hmap = h2_maps(h2)
    prows = [replay_parent(m, r, lane) for _, r in parent.iterrows()]
    pr = pd.DataFrame(prows)
    cparent = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}

    hrows = []
    for k, hr in hmap.items():
        cp = cparent.get(k)
        if cp is None:
            raise RuntimeError(f"candidate parent mapping missing {k}")
        # Recovery remains a second chance after a losing parent episode only.
        if float(cp.candidate_pnl) > 0:
            continue
        base_parent = pmap[k]
        hrows.append(replay_h2(m, hr, base_parent, lane))
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
        rows.append({
            "role": r.role, "partition": r.partition, "dev_block": r.dev_block,
            "execution_start": r.execution_start, "parent_entry_ts": r.entry_ts,
            "episode_pnl": float(r.pnl) + hp,
            "episode_pnl_5bps": float(r.pnl_5bps) + hp5,
        })
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
        rows.append({
            "role": r.role, "partition": r.partition, "dev_block": r.dev_block,
            "execution_start": r.execution_start, "parent_entry_ts": r.parent_entry_ts,
            "episode_pnl": float(r.candidate_pnl) + hp,
            "episode_pnl_5bps": float(r.candidate_pnl_5bps) + hp5,
        })
    return pd.DataFrame(rows)


def stack_values(parent_q, h2_q, candidate=False):
    if candidate:
        p = pd.to_numeric(parent_q.candidate_pnl, errors="coerce")
        p5 = pd.to_numeric(parent_q.candidate_pnl_5bps, errors="coerce")
        if h2_q is not None and len(h2_q):
            h = pd.to_numeric(h2_q.candidate_pnl, errors="coerce")
            h5 = pd.to_numeric(h2_q.candidate_pnl_5bps, errors="coerce")
            p = pd.concat([p, h], ignore_index=True)
            p5 = pd.concat([p5, h5], ignore_index=True)
        return p, p5
    p = pd.to_numeric(parent_q.pnl, errors="coerce")
    p5 = pd.to_numeric(parent_q.pnl_5bps, errors="coerce")
    if h2_q is not None and len(h2_q):
        h = pd.to_numeric(h2_q.recovery_pnl, errors="coerce")
        h5 = pd.to_numeric(h2_q.recovery_pnl_5bps, errors="coerce")
        p = pd.concat([p, h], ignore_index=True)
        p5 = pd.concat([p5, h5], ignore_index=True)
    return p, p5


def summarize_cell(parent_base, h2_base, pr, rr):
    be = baseline_episode(parent_base, h2_base)
    ce = candidate_episode(pr, rr)
    bv, bv5 = stack_values(parent_base, h2_base, candidate=False)
    cv, cv5 = stack_values(pr, rr, candidate=True)
    winners = parent_base[pd.to_numeric(parent_base.pnl, errors="coerce") > 0]
    cand_map = {key4(r.role, r.partition, r.execution_start, r.parent_entry_ts): r for _, r in pr.iterrows()}
    preserved = 0
    for _, w in winners.iterrows():
        z = cand_map[key4(w.role, w.partition, w.execution_start, w.entry_ts)]
        preserved += int(float(z.candidate_pnl) > 0)
    wp = preserved / len(winners) if len(winners) else np.nan

    b_ep = pd.to_numeric(be.episode_pnl, errors="coerce")
    c_ep = pd.to_numeric(ce.episode_pnl, errors="coerce")
    b_ep5 = pd.to_numeric(be.episode_pnl_5bps, errors="coerce")
    c_ep5 = pd.to_numeric(ce.episode_pnl_5bps, errors="coerce")
    return {
        "parent_n": len(parent_base),
        "parent_ratchet_triggers": int(pr.ratchet_triggered.astype(bool).sum()),
        "retained_h2_n": 0 if rr is None else len(rr),
        "h2_ratchet_triggers": 0 if rr is None or not len(rr) else int(rr.ratchet_triggered.astype(bool).sum()),
        "parent_winner_preservation": wp,
        "new_negative_original_winners": int(len(winners) - preserved),
        "baseline_parent_wr": float((pd.to_numeric(parent_base.pnl, errors="coerce") > 0).mean()),
        "candidate_parent_wr": float((pd.to_numeric(pr.candidate_pnl, errors="coerce") > 0).mean()),
        "baseline_episode_wr": float((b_ep > 0).mean()),
        "candidate_episode_wr": float((c_ep > 0).mean()),
        "episode_wr_delta": float((c_ep > 0).mean() - (b_ep > 0).mean()),
        "baseline_episode_pf": pf(b_ep), "candidate_episode_pf": pf(c_ep),
        "baseline_episode_net": float(b_ep.sum()), "candidate_episode_net": float(c_ep.sum()),
        "baseline_episode_gross_loss": float(-b_ep[b_ep <= 0].sum()),
        "candidate_episode_gross_loss": float(-c_ep[c_ep <= 0].sum()),
        "baseline_episode_wr_5bps": float((b_ep5 > 0).mean()),
        "candidate_episode_wr_5bps": float((c_ep5 > 0).mean()),
        "baseline_episode_pf_5bps": pf(b_ep5), "candidate_episode_pf_5bps": pf(c_ep5),
        "baseline_episode_net_5bps": float(b_ep5.sum()), "candidate_episode_net_5bps": float(c_ep5.sum()),
        "baseline_stack_pf": pf(bv), "candidate_stack_pf": pf(cv),
        "baseline_stack_net": float(bv.sum()), "candidate_stack_net": float(cv.sum()),
        "stack_net_improvement": float(cv.sum() - bv.sum()),
        "baseline_stack_pf_5bps": pf(bv5), "candidate_stack_pf_5bps": pf(cv5),
        "baseline_stack_net_5bps": float(bv5.sum()), "candidate_stack_net_5bps": float(cv5.sum()),
        "stack_net_improvement_5bps": float(cv5.sum() - bv5.sum()),
    }


def development_row(parent, h2, pr, rr, lane):
    pb = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    hb = h2[(h2.role == "CENTRAL") & (h2.partition == "development")].copy()
    cp = pr[(pr.role == "CENTRAL") & (pr.partition == "development")].copy()
    cr = rr[(rr.role == "CENTRAL") & (rr.partition == "development")].copy() if len(rr) else rr
    s = summarize_cell(pb, hb, cp, cr)

    raw_pos = 0; stress_pos = 0; adequate = 0
    block_cols = {}
    for bi in range(6):
        pbb = pb[pd.to_numeric(pb.dev_block, errors="coerce") == bi]
        hbb = hb[pd.to_numeric(hb.dev_block, errors="coerce") == bi]
        cpp = cp[pd.to_numeric(cp.dev_block, errors="coerce") == bi]
        crr = cr[pd.to_numeric(cr.dev_block, errors="coerce") == bi] if len(cr) else cr
        bs, bs5 = stack_values(pbb, hbb, candidate=False)
        cs, cs5 = stack_values(cpp, crr, candidate=True)
        d = float(cs.sum() - bs.sum()); d5 = float(cs5.sum() - bs5.sum())
        n = len(pbb)
        block_cols[f"b{bi+1}_n"] = n
        block_cols[f"b{bi+1}_delta"] = d
        block_cols[f"b{bi+1}_delta_5bps"] = d5
        if n >= 20:
            adequate += 1
            raw_pos += int(d > 0)
            stress_pos += int(d5 > 0)

    eligible = bool(
        s["parent_n"] == 617
        and s["stack_net_improvement"] > 0
        and s["stack_net_improvement_5bps"] > 0
        and s["candidate_stack_pf"] > s["baseline_stack_pf"] + EPS
        and s["candidate_stack_pf_5bps"] > s["baseline_stack_pf_5bps"] + EPS
        and s["candidate_episode_gross_loss"] <= s["baseline_episode_gross_loss"] + EPS
        and s["candidate_episode_wr"] + EPS >= s["baseline_episode_wr"]
        and s["parent_winner_preservation"] >= 0.98
        and raw_pos >= 4 and stress_pos >= 4
    )
    return {"lane": lane, **s, "adequate_blocks": adequate,
            "positive_blocks": raw_pos, "positive_blocks_5bps": stress_pos,
            "eligible": eligible, **block_cols}


def choose_dev(dev):
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    q["simple_rank"] = q.lane.map({"RF_LOOSE": 0, "RF_BALANCED": 1, "RF_TIGHT": 2, "RF_GIVEBACK15": 3})
    return q.sort_values(
        ["stack_net_improvement_5bps", "stack_net_improvement", "episode_wr_delta", "candidate_stack_pf_5bps", "simple_rank"],
        ascending=[False, False, False, False, True],
    ).iloc[0]


def main():
    parent, h2, m, coverage = load_system()
    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")]
    if len(cd_parent) != 617:
        raise RuntimeError(f"A2 Central Development parity failed: {len(cd_parent)}")
    if abs(float(cd_parent.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("A2 Central Development net parity failed")

    dev_rows = []
    simulations = {}
    for lane in LANES:
        pr, rr = simulate_lane(parent, h2, m, lane)
        simulations[lane] = (pr, rr)
        dev_rows.append(development_row(parent, h2, pr, rr, lane))
    dev = pd.DataFrame(dev_rows)
    winner = choose_dev(dev)

    oos_rows = []
    selected_frames = []
    frozen_lane = None
    supported = False
    reason = "No Development ratchet passed"

    if winner is not None:
        frozen_lane = str(winner.lane)
        pr, rr = simulations[frozen_lane]
        dpr = pr[(pr.role == "CENTRAL") & (pr.partition == "development")].copy()
        dpr["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
        selected_frames.append(dpr)
        if len(rr):
            drr = rr[(rr.role == "CENTRAL") & (rr.partition == "development")].copy()
            drr["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
            selected_frames.append(drr)

        for (role, part), pb in parent.groupby(["role", "partition"], sort=False):
            if role == "CENTRAL" and part == "development":
                continue
            if part not in ["external", "reference_validation"]:
                continue
            hb = h2[(h2.role == role) & (h2.partition == part)].copy()
            cp = pr[(pr.role == role) & (pr.partition == part)].copy()
            cr = rr[(rr.role == role) & (rr.partition == part)].copy() if len(rr) else rr
            s = summarize_cell(pb, hb, cp, cr)
            oos_rows.append({"role": role, "partition": part, "lane": frozen_lane, **s})
            if len(cp):
                z = cp.copy(); z["selection_scope"] = "FROZEN_OOS"; selected_frames.append(z)
            if len(cr):
                z = cr.copy(); z["selection_scope"] = "FROZEN_OOS"; selected_frames.append(z)
        oos = pd.DataFrame(oos_rows)

        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        rv = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        central_ok = False
        if len(ce) == 1 and len(rv) == 1:
            central_ok = all(
                float(r.stack_net_improvement) > 0
                and float(r.stack_net_improvement_5bps) > 0
                and float(r.candidate_stack_pf) + EPS >= float(r.baseline_stack_pf)
                and float(r.candidate_stack_pf_5bps) + EPS >= float(r.baseline_stack_pf_5bps)
                and float(r.candidate_episode_gross_loss) <= float(r.baseline_episode_gross_loss) + EPS
                and float(r.parent_winner_preservation) >= 0.97
                for _, r in pd.concat([ce, rv]).iterrows()
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
        "# SOL LONG Progressive Risk Floor — A11 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A11 tests progressive profit floors on the supported A2 parent + A4 REC_H2 stack. Rejected A6/A8/A10 mechanisms remain absent.", "",
        "## Central Development", "",
        "| Lane | Parent triggers | H2 retained | H2 triggers | Winner preserved | Episode WR base→new | Episode gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |",
        "|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.parent_ratchet_triggers)} | {int(r.retained_h2_n)} | {int(r.h2_ratchet_triggers)} | {fmt_pct(r.parent_winner_preservation)} | {fmt_pct(r.baseline_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${r.baseline_episode_gross_loss:.2f}→${r.candidate_episode_gross_loss:.2f} | {fmt_num(r.baseline_stack_pf)}→{fmt_num(r.candidate_stack_pf)} | ${r.stack_net_improvement:.2f} | {fmt_num(r.baseline_stack_pf_5bps)}→{fmt_num(r.candidate_stack_pf_5bps)} | ${r.stack_net_improvement_5bps:.2f} | {int(r.positive_blocks)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )

    lines += ["", f"Frozen Development winner: **{frozen_lane or 'NONE'}**.", ""]
    if len(oos):
        lines += [
            "## Frozen OOS", "",
            "| Role | Partition | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ |",
            "|---|---|---:|---|---|---|---:|---|---:|",
        ]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | {fmt_pct(r.parent_winner_preservation)} | {fmt_pct(r.baseline_episode_wr)}→{fmt_pct(r.candidate_episode_wr)} | ${r.baseline_episode_gross_loss:.2f}→${r.candidate_episode_gross_loss:.2f} | {fmt_num(r.baseline_stack_pf)}→{fmt_num(r.candidate_stack_pf)} | ${r.stack_net_improvement:.2f} | {fmt_num(r.baseline_stack_pf_5bps)}→{fmt_num(r.candidate_stack_pf_5bps)} | ${r.stack_net_improvement_5bps:.2f} |"
            )

    status = "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_SUPPORTED" if supported else "SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_REJECTED"
    lines += ["", "## Decision", "", f"- Validation: **{reason}**.", "", f"**Status: {status}**", "",
              "A supported result authorizes only the frozen ratchet for further full-stack residual/benchmark analysis. A rejected result must not be rescued by OOS retuning.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
