#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A5_PATH = Path(__file__).resolve().parent / "sol_long_h1_residual_failure_a5.py"
spec = importlib.util.spec_from_file_location("sol_a5", A5_PATH)
a5 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a5)
a4 = a5.a4
a2 = a4.a2

OUT_MD = ROOT / "SOL_LONG_H2_RECLAIM_REENTRY_A8_Result.md"
OUT_DEV = ROOT / "SOL_LONG_H2_RECLAIM_REENTRY_A8_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_H2_RECLAIM_REENTRY_A8_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_H2_RECLAIM_REENTRY_A8_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_H2_RECLAIM_REENTRY_A8_Status.txt"

WINDOWS = {"RC10": 10, "RC15": 15, "RC30": 30, "RC60": 60}
TARGET_R = 0.40
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
    return "-" if pd.isna(v) else f"{100.0 * float(v):.1f}%"


def load_system():
    parent, m, coverage = a5.load_system()
    episodes, _ = a5.build_episodes(parent, m)
    return parent, episodes, m, coverage


def parent_map(parent):
    return {
        (r.role, r.partition, pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_ts)): r
        for _, r in parent.iterrows()
    }


def eligible_episodes(episodes):
    return episodes[
        (episodes.parent_pnl <= 0)
        & episodes.h2_eligible.astype(bool)
        & (episodes.episode_pnl <= 0)
        & (episodes.h2_recovery_reason.astype(str) != "TARGET")
    ].copy()


def simulate_one(m, e, r, lane):
    window_min = WINDOWS[lane]
    w = a4.recovery_window(m, r)
    if w is None:
        return None
    _, _, endpos, _ = w
    idx = m["idx"]
    op, hi, cl = m["open"], m["high"], m["close"]
    xit = pd.Timestamp(e.h2_recovery_exit_ts)
    xi = int(idx.searchsorted(xit, "left"))
    if xi >= len(idx) or idx[xi] != xit or xi >= endpos:
        return None

    # Completed closes at +5m ... +window_min after the H2 exit timestamp.
    # xi is the opening timestamp of the H2 exit bar; the bar close is the first completed observation.
    search_end = min(xi + window_min // 5, endpos)
    signal_i = -1
    H, R = float(e.H), float(e.R)
    target = H + TARGET_R * R
    for i in range(xi, search_end):
        if float(cl[i]) > H:
            signal_i = i
            break
    if signal_i < 0:
        return None

    entry_i = signal_i + 1
    if entry_i >= endpos:
        return None
    entry_price = float(op[entry_i])
    exit_i = endpos - 1
    exit_price = float(cl[exit_i])
    reason = "TIME"
    invalid_i = -1

    # Target is deliberately not credited on signal or re-entry bar.
    for i in range(entry_i + 1, endpos):
        if float(hi[i]) >= target:
            exit_i = i
            exit_price = target
            reason = "TARGET"
            break
        if float(cl[i]) <= H:
            invalid_i = i
            ni = i + 1
            if ni < endpos:
                exit_i = ni
                exit_price = float(op[ni])
                reason = "FAILED_RECLAIM"
            else:
                exit_i = i
                exit_price = float(cl[i])
                reason = "TIME_AFTER_FINAL_FAILED_RECLAIM"
            break

    ret = exit_price / entry_price - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    comb = float(e.episode_pnl) + pnl
    comb5 = float(e.episode_pnl_5bps) + pnl5
    return {
        "role": e.role,
        "partition": e.partition,
        "dev_block": e.dev_block,
        "execution_start": e.execution_start,
        "loss_class": e.loss_class,
        "episode_class_before_a8": e.episode_class,
        "lane": lane,
        "window_min": window_min,
        "H": H,
        "L": float(e.L),
        "R": R,
        "parent_pnl": float(e.parent_pnl),
        "parent_pnl_5bps": float(e.parent_pnl_5bps),
        "h2_recovery_pnl": float(e.h2_recovery_pnl),
        "h2_recovery_pnl_5bps": float(e.h2_recovery_pnl_5bps),
        "episode_pnl_before_a8": float(e.episode_pnl),
        "episode_pnl_before_a8_5bps": float(e.episode_pnl_5bps),
        "h2_exit_ts": xit,
        "reclaim_signal_ts": idx[signal_i],
        "reclaim_signal_close": float(cl[signal_i]),
        "reentry_ts": idx[entry_i],
        "reentry_price": entry_price,
        "a8_exit_ts": idx[exit_i],
        "a8_exit_price": exit_price,
        "a8_exit_reason": reason,
        "a8_invalidation_close_ts": idx[invalid_i] if invalid_i >= 0 else pd.NaT,
        "a8_pnl": pnl,
        "a8_pnl_5bps": pnl5,
        "a8_won": pnl > 0,
        "a8_won_5bps": pnl5 > 0,
        "combined_episode_pnl": comb,
        "combined_episode_pnl_5bps": comb5,
        "rescued": comb > 0,
        "rescued_5bps": comb5 > 0,
    }


def simulate_lane(m, eps, pmap, lane):
    rows = []
    for _, e in eps.iterrows():
        key = (e.role, e.partition, pd.Timestamp(e.execution_start), pd.Timestamp(e.parent_entry_ts))
        r = pmap.get(key)
        if r is None:
            raise RuntimeError(f"Parent mapping failure: {key}")
        z = simulate_one(m, e, r, lane)
        if z is not None:
            rows.append(z)
    return pd.DataFrame(rows)


def overlay_base(parent_q, episodes_q):
    vals = [pd.to_numeric(parent_q.pnl, errors="coerce")]
    vals5 = [pd.to_numeric(parent_q.pnl_5bps, errors="coerce")]
    h2 = episodes_q[(episodes_q.parent_pnl <= 0) & episodes_q.h2_eligible.astype(bool)]
    if len(h2):
        vals.append(pd.to_numeric(h2.h2_recovery_pnl, errors="coerce"))
        vals5.append(pd.to_numeric(h2.h2_recovery_pnl_5bps, errors="coerce"))
    return pd.concat(vals, ignore_index=True), pd.concat(vals5, ignore_index=True)


def summarize(t, parent_q, episodes_q):
    base, base5 = overlay_base(parent_q, episodes_q)
    if t.empty:
        return {
            "n": 0, "wr": np.nan, "pf": np.nan, "expectancy": np.nan, "net": 0.0,
            "wr_5bps": np.nan, "pf_5bps": np.nan, "expectancy_5bps": np.nan, "net_5bps": 0.0,
            "rescue_rate": np.nan, "rescue_rate_5bps": np.nan,
            "baseline_overlay_pf": pf(base), "baseline_overlay_net": float(base.sum()),
            "candidate_overlay_pf": pf(base), "candidate_overlay_net": float(base.sum()),
            "overlay_net_improvement": 0.0,
            "baseline_overlay_pf_5bps": pf(base5), "baseline_overlay_net_5bps": float(base5.sum()),
            "candidate_overlay_pf_5bps": pf(base5), "candidate_overlay_net_5bps": float(base5.sum()),
            "overlay_net_improvement_5bps": 0.0,
        }
    p = pd.to_numeric(t.a8_pnl, errors="coerce")
    p5 = pd.to_numeric(t.a8_pnl_5bps, errors="coerce")
    cand = pd.concat([base, p], ignore_index=True)
    cand5 = pd.concat([base5, p5], ignore_index=True)
    return {
        "n": len(t),
        "wr": float((p > 0).mean()), "pf": pf(p), "expectancy": float(p.mean()), "net": float(p.sum()),
        "wr_5bps": float((p5 > 0).mean()), "pf_5bps": pf(p5), "expectancy_5bps": float(p5.mean()), "net_5bps": float(p5.sum()),
        "rescue_rate": float(t.rescued.mean()), "rescue_rate_5bps": float(t.rescued_5bps.mean()),
        "baseline_overlay_pf": pf(base), "baseline_overlay_net": float(base.sum()),
        "candidate_overlay_pf": pf(cand), "candidate_overlay_net": float(cand.sum()),
        "overlay_net_improvement": float(cand.sum() - base.sum()),
        "baseline_overlay_pf_5bps": pf(base5), "baseline_overlay_net_5bps": float(base5.sum()),
        "candidate_overlay_pf_5bps": pf(cand5), "candidate_overlay_net_5bps": float(cand5.sum()),
        "overlay_net_improvement_5bps": float(cand5.sum() - base5.sum()),
    }


def development_row(t, parent_q, episodes_q, lane):
    s = summarize(t, parent_q, episodes_q)
    adequate = 0
    positive = 0
    block = {}
    for bi in range(6):
        z = t[t.dev_block == bi] if len(t) else t
        n = len(z)
        net = float(z.a8_pnl.sum()) if n else 0.0
        net5 = float(z.a8_pnl_5bps.sum()) if n else 0.0
        block[f"b{bi+1}_n"] = n
        block[f"b{bi+1}_net"] = net
        block[f"b{bi+1}_net_5bps"] = net5
        if n >= 5:
            adequate += 1
            if net > 0:
                positive += 1
    eligible = bool(
        s["n"] >= 40
        and pd.notna(s["pf"]) and s["pf"] > 1.15
        and s["expectancy"] > 0
        and pd.notna(s["pf_5bps"]) and s["pf_5bps"] > 1.00
        and s["expectancy_5bps"] > 0
        and s["net"] > 0
        and pd.notna(s["rescue_rate"]) and s["rescue_rate"] >= 0.20
        and s["overlay_net_improvement"] > 0
        and s["overlay_net_improvement_5bps"] > 0
        and positive >= 4
    )
    return {"lane": lane, "window_min": WINDOWS[lane], **s,
            "adequate_blocks": adequate, "positive_blocks": positive, "eligible": eligible, **block}


def choose_dev(dev):
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    return q.sort_values(
        ["overlay_net_improvement_5bps", "net_5bps", "rescue_rate", "pf_5bps", "window_min"],
        ascending=[False, False, False, False, True],
    ).iloc[0]


def main():
    parent, episodes, m, coverage = load_system()
    pmap = parent_map(parent)
    eps = eligible_episodes(episodes)

    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    cd_eps_all = episodes[(episodes.role == "CENTRAL") & (episodes.partition == "development")].copy()
    cd_eps = eps[(eps.role == "CENTRAL") & (eps.partition == "development")].copy()
    if len(cd_parent) != 617:
        raise RuntimeError(f"A2 central Development N parity failed: {len(cd_parent)}")
    if abs(float(cd_parent.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("A2 central Development net parity failed")

    dev_rows, dev_trades = [], {}
    for lane in WINDOWS:
        t = simulate_lane(m, cd_eps, pmap, lane)
        dev_trades[lane] = t
        dev_rows.append(development_row(t, cd_parent, cd_eps_all, lane))
    dev = pd.DataFrame(dev_rows)
    winner = choose_dev(dev)

    oos_rows = []
    selected_frames = []
    supported = False
    frozen_lane = None
    reason = "No Development reclaim window passed"

    if winner is not None:
        frozen_lane = str(winner.lane)
        zdev = dev_trades[frozen_lane].copy()
        zdev["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
        selected_frames.append(zdev)

        for (role, part), pq in parent.groupby(["role", "partition"], sort=False):
            if role == "CENTRAL" and part == "development":
                continue
            if part not in ["external", "reference_validation"]:
                continue
            eq_all = episodes[(episodes.role == role) & (episodes.partition == part)].copy()
            eq = eps[(eps.role == role) & (eps.partition == part)].copy()
            t = simulate_lane(m, eq, pmap, frozen_lane)
            s = summarize(t, pq, eq_all)
            oos_rows.append({"role": role, "partition": part, "lane": frozen_lane, **s})
            if len(t):
                t["selection_scope"] = "FROZEN_OOS"
                selected_frames.append(t)
        oos = pd.DataFrame(oos_rows)

        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        cr = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        central_ok = False
        if len(ce) == 1 and len(cr) == 1:
            central_ok = all(
                float(r.net) > 0
                and float(r.net_5bps) > 0
                and float(r.overlay_net_improvement) > 0
                and float(r.overlay_net_improvement_5bps) > 0
                and float(r.rescue_rate) > 0
                for _, r in pd.concat([ce, cr]).iterrows()
            )
        support = oos[oos.role.isin(["CLOCK_SUPPORT", "REF_SUPPORT"])].copy()
        raw_pos = int((support.net > 0).sum())
        stress_pos = int((support.net_5bps > 0).sum())
        support_ok = len(support) >= 4 and raw_pos >= 3 and stress_pos >= 3
        supported = bool(central_ok and support_ok)
        reason = f"central_ok={central_ok}; support positive raw={raw_pos}/4; support positive 5bps={stress_pos}/4"
    else:
        oos = pd.DataFrame()

    dev.to_csv(OUT_DEV, index=False)
    oos.to_csv(OUT_OOS, index=False)
    (pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame()).to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG H2 Reclaim Re-entry — A8 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A8 tests confirmed reclaim next-open re-entry after a losing frozen H2 recovery. No resting H3/H4 retry is used.", "",
        "## Central Development", "",
        "| Lane | A8 N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | Rescue | 5bps Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ | +blocks | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | ${r.expectancy:.2f} | ${r.net:.2f} | {fmt_num(r.pf_5bps)} | ${r.expectancy_5bps:.2f} | ${r.net_5bps:.2f} | {fmt_pct(r.rescue_rate)} | {fmt_pct(r.rescue_rate_5bps)} | {fmt_num(r.baseline_overlay_pf)}→{fmt_num(r.candidate_overlay_pf)} | ${r.overlay_net_improvement:.2f} | {fmt_num(r.baseline_overlay_pf_5bps)}→{fmt_num(r.candidate_overlay_pf_5bps)} | ${r.overlay_net_improvement_5bps:.2f} | {int(r.positive_blocks)}/{int(r.adequate_blocks)} | {'YES' if r.eligible else 'NO'} |"
        )

    if winner is not None:
        lines += ["", f"Frozen Development winner: **{frozen_lane}**.", "", "## Frozen OOS", "",
                  "| Role | Partition | N | PF | Net | 5bps PF | 5bps Net | Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---:|"]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | {int(r.n)} | {fmt_num(r.pf)} | ${r.net:.2f} | {fmt_num(r.pf_5bps)} | ${r.net_5bps:.2f} | {fmt_pct(r.rescue_rate)} | {fmt_num(r.baseline_overlay_pf)}→{fmt_num(r.candidate_overlay_pf)} | ${r.overlay_net_improvement:.2f} | {fmt_num(r.baseline_overlay_pf_5bps)}→{fmt_num(r.candidate_overlay_pf_5bps)} | ${r.overlay_net_improvement_5bps:.2f} |"
            )

    status = "SOL_LONG_H2_RECLAIM_REENTRY_A8_SUPPORTED" if supported else "SOL_LONG_H2_RECLAIM_REENTRY_A8_REJECTED"
    lines += ["", "## Decision", "", f"- Frozen lane: **{frozen_lane or 'NONE'}**.", f"- Validation: **{reason}**.", "", f"**Status: {status}**", "",
              "If supported, the next stage should recompute the fully frozen H1 + H2 + reclaim-reentry episode economics, residual-loss anatomy, and benchmark against the prior SOL stack before any exit optimization.", "",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
