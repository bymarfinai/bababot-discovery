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

OUT_MD = ROOT / "SOL_LONG_H1_EARLY_INVALIDATION_A6_Result.md"
OUT_DEV = ROOT / "SOL_LONG_H1_EARLY_INVALIDATION_A6_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_H1_EARLY_INVALIDATION_A6_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_H1_EARLY_INVALIDATION_A6_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_H1_EARLY_INVALIDATION_A6_Status.txt"

# name: (snapshot_min, adverse_close_depth_R, max_running_mfe_R, complexity_rank)
RULES = {
    "P30_D12": (30, 0.12, None, 0),
    "P30_D12_M07": (30, 0.12, 0.07, 1),
    "P60_D22": (60, 0.22, None, 0),
    "P60_D22_M06": (60, 0.22, 0.06, 1),
}
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
    parent = a4.load_parent()
    _, m, coverage = a4.market()
    return parent, m, coverage


def simulate_rule(m, r, lane):
    sm, depth, mfe_cap, complexity = RULES[lane]
    idx = m["idx"]
    ei = int(idx.searchsorted(pd.Timestamp(r.entry_ts), "left"))
    xi = int(idx.searchsorted(pd.Timestamp(r.exit_ts), "left"))
    if ei >= len(idx) or xi >= len(idx) or idx[ei] != r.entry_ts or idx[xi] != r.exit_ts:
        raise RuntimeError(f"Timestamp parity failure: {r.entry_ts}")

    base_pnl = float(r.pnl)
    base_pnl5 = float(r.pnl_5bps)
    out = {
        "role": r.role,
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "entry_ts": r.entry_ts,
        "original_exit_ts": r.exit_ts,
        "lane": lane,
        "snapshot_min": sm,
        "depth_R": depth,
        "mfe_cap_R": mfe_cap,
        "complexity_rank": complexity,
        "original_pnl": base_pnl,
        "original_pnl_5bps": base_pnl5,
        "original_won": base_pnl > 0,
        "triggered": False,
        "trigger_close_R": np.nan,
        "trigger_running_mfe_R": np.nan,
        "candidate_exit_ts": r.exit_ts,
        "candidate_exit_price": float(r.exit_price),
        "candidate_exit_reason": r.exit_reason,
        "candidate_pnl": base_pnl,
        "candidate_pnl_5bps": base_pnl5,
        "candidate_won": base_pnl > 0,
        "candidate_won_5bps": base_pnl5 > 0,
    }

    si = ei + (sm // 5) - 1
    # Must still be open after the completed snapshot bar.
    if si >= xi or si >= len(idx):
        return out

    cl = np.asarray(m["close"][ei:si + 1], dtype=float)
    hi = np.asarray(m["high"][ei:si + 1], dtype=float)
    H, R = float(r.H), float(r.R)
    if R <= 0:
        raise RuntimeError("nonpositive R")

    # Parent that has established breakout is outside this intervention.
    if np.any(cl > H):
        return out

    close_R = (float(cl[-1]) - H) / R
    run_mfe = max(0.0, (float(np.max(hi)) - H) / R)
    if close_R > -depth + EPS:
        return out
    if mfe_cap is not None and run_mfe > mfe_cap + EPS:
        return out

    ni = si + 1
    if ni >= len(idx):
        return out
    exit_price = float(m["open"][ni])
    ret = exit_price / float(r.entry_price) - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    out.update({
        "triggered": True,
        "trigger_close_R": close_R,
        "trigger_running_mfe_R": run_mfe,
        "candidate_exit_ts": idx[ni],
        "candidate_exit_price": exit_price,
        "candidate_exit_reason": "A6_EARLY_INVALIDATION",
        "candidate_pnl": pnl,
        "candidate_pnl_5bps": pnl5,
        "candidate_won": pnl > 0,
        "candidate_won_5bps": pnl5 > 0,
    })
    return out


def simulate_frame(m, q, lane):
    return pd.DataFrame([simulate_rule(m, r, lane) for _, r in q.iterrows()])


def metrics(t):
    base = pd.to_numeric(t.original_pnl, errors="coerce")
    cand = pd.to_numeric(t.candidate_pnl, errors="coerce")
    base5 = pd.to_numeric(t.original_pnl_5bps, errors="coerce")
    cand5 = pd.to_numeric(t.candidate_pnl_5bps, errors="coerce")
    orig_win = t.original_won.astype(bool)
    winner_pres = float(t.loc[orig_win, "candidate_won"].mean()) if orig_win.any() else np.nan
    base_gl = float(-base[base <= 0].sum())
    cand_gl = float(-cand[cand <= 0].sum())
    return {
        "n": len(t),
        "triggered_n": int(t.triggered.sum()),
        "trigger_rate": float(t.triggered.mean()),
        "original_winners_triggered": int((t.triggered & t.original_won).sum()),
        "original_losers_triggered": int((t.triggered & ~t.original_won).sum()),
        "winner_preservation": winner_pres,
        "baseline_pf": pf(base),
        "candidate_pf": pf(cand),
        "baseline_net": float(base.sum()),
        "candidate_net": float(cand.sum()),
        "net_improvement": float(cand.sum() - base.sum()),
        "baseline_pf_5bps": pf(base5),
        "candidate_pf_5bps": pf(cand5),
        "baseline_net_5bps": float(base5.sum()),
        "candidate_net_5bps": float(cand5.sum()),
        "net_improvement_5bps": float(cand5.sum() - base5.sum()),
        "baseline_gross_loss": base_gl,
        "candidate_gross_loss": cand_gl,
        "gross_loss_reduction": base_gl - cand_gl,
        "expectancy": float(cand.mean()),
        "expectancy_5bps": float(cand5.mean()),
    }


def development_row(t, lane):
    s = metrics(t)
    block = {}
    adequate = 0
    nonneg = 0
    worst = np.nan
    deltas = []
    for bi in range(6):
        z = t[t.dev_block == bi]
        trig = int(z.triggered.sum()) if len(z) else 0
        imp = float(z.candidate_pnl.sum() - z.original_pnl.sum()) if len(z) else 0.0
        imp5 = float(z.candidate_pnl_5bps.sum() - z.original_pnl_5bps.sum()) if len(z) else 0.0
        block[f"b{bi+1}_triggered"] = trig
        block[f"b{bi+1}_improvement"] = imp
        block[f"b{bi+1}_improvement_5bps"] = imp5
        if trig >= 3:
            adequate += 1
            deltas.append(imp)
            if imp >= -EPS:
                nonneg += 1
    if deltas:
        worst = min(deltas)
    sm, depth, mfe_cap, complexity = RULES[lane]
    eligible = bool(
        s["net_improvement"] > 0
        and s["net_improvement_5bps"] > 0
        and s["candidate_pf"] > s["baseline_pf"]
        and s["candidate_pf_5bps"] > s["baseline_pf_5bps"]
        and s["gross_loss_reduction"] > 0
        and s["winner_preservation"] >= 0.95
        and adequate >= 4
        and nonneg >= 4
        and (pd.isna(worst) or worst >= -25.0)
    )
    return {
        "lane": lane,
        "snapshot_min": sm,
        "depth_R": depth,
        "mfe_cap_R": mfe_cap,
        "complexity_rank": complexity,
        **s,
        "adequate_blocks": adequate,
        "nonnegative_adequate_blocks": nonneg,
        "worst_adequate_block_improvement": worst,
        "eligible": eligible,
        **block,
    }


def choose_lane(dev):
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    q = q.sort_values(
        ["net_improvement_5bps", "net_improvement", "winner_preservation", "gross_loss_reduction", "complexity_rank", "snapshot_min"],
        ascending=[False, False, False, False, True, False],
    )
    return q.iloc[0]


def main():
    parent, m, coverage = load_system()
    cd = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    if len(cd) != 617:
        raise RuntimeError(f"Central Development N parity failed: {len(cd)}")
    if abs(float(cd.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("Central Development baseline net parity failed")

    dev_rows = []
    dev_trades = {}
    for lane in RULES:
        t = simulate_frame(m, cd, lane)
        if len(t) != len(cd):
            raise RuntimeError("Development N parity failure")
        dev_trades[lane] = t
        dev_rows.append(development_row(t, lane))
    dev = pd.DataFrame(dev_rows)
    winner = choose_lane(dev)

    oos_rows = []
    selected_frames = []
    supported = False
    status_reason = "No Development lane passed"
    frozen_lane = None

    if winner is not None:
        frozen_lane = str(winner.lane)
        # Persist selected Development trade-level effects too.
        zdev = dev_trades[frozen_lane].copy()
        zdev["selection_scope"] = "DEVELOPMENT_FROZEN_WINNER"
        selected_frames.append(zdev)

        for (role, part), q in parent.groupby(["role", "partition"], sort=False):
            if role == "CENTRAL" and part == "development":
                continue
            # Only frozen OOS/support cells; no Development support selection.
            if part not in ["external", "reference_validation"]:
                continue
            t = simulate_frame(m, q, frozen_lane)
            s = metrics(t)
            oos_rows.append({"role": role, "partition": part, "lane": frozen_lane, **s})
            t["selection_scope"] = "FROZEN_OOS"
            selected_frames.append(t)
        oos = pd.DataFrame(oos_rows)

        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        cr = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        central_ok = False
        if len(ce) == 1 and len(cr) == 1:
            central_ok = all(
                float(x.net_improvement) > 0
                and float(x.net_improvement_5bps) > 0
                and float(x.winner_preservation) >= 0.93
                and float(x.gross_loss_reduction) > 0
                for _, x in pd.concat([ce, cr]).iterrows()
            )
        support = oos[oos.role.isin(["CLOCK_SUPPORT", "REF_SUPPORT"])].copy()
        raw_nonneg = int((support.net_improvement >= -EPS).sum())
        stress_nonneg = int((support.net_improvement_5bps >= -EPS).sum())
        support_ok = len(support) >= 4 and raw_nonneg >= 3 and stress_nonneg >= 3
        supported = bool(central_ok and support_ok)
        status_reason = (
            f"central_ok={central_ok}; support raw nonnegative={raw_nonneg}/4; support 5bps nonnegative={stress_nonneg}/4"
        )
    else:
        oos = pd.DataFrame()

    dev.to_csv(OUT_DEV, index=False)
    oos.to_csv(OUT_OOS, index=False)
    if selected_frames:
        pd.concat(selected_frames, ignore_index=True).to_csv(OUT_TRADES, index=False)
    else:
        pd.DataFrame().to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG H1 Early Invalidation — A6 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A6 changes only the parent pre-break exit. A4 H2 recovery is not used for Development selection.", "",
        "## Central Development", "",
        "| Lane | Triggers | Winners triggered | Losers triggered | Winner preserved | PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ | Gross-loss reduction | Blocks nonneg/adequate | Pass |",
        "|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.triggered_n)} | {int(r.original_winners_triggered)} | {int(r.original_losers_triggered)} | {fmt_pct(r.winner_preservation)} | {fmt_num(r.baseline_pf)}→{fmt_num(r.candidate_pf)} | ${r.net_improvement:.2f} | {fmt_num(r.baseline_pf_5bps)}→{fmt_num(r.candidate_pf_5bps)} | ${r.net_improvement_5bps:.2f} | ${r.gross_loss_reduction:.2f} | {int(r.nonnegative_adequate_blocks)}/{int(r.adequate_blocks)} | {'YES' if r.eligible else 'NO'} |"
        )

    if winner is not None:
        lines += ["", f"Frozen Development winner: **{frozen_lane}**.", "", "## Frozen OOS", "",
                  "| Role | Partition | Triggers | Winner preserved | PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ | Gross-loss reduction |",
                  "|---|---|---:|---:|---|---:|---|---:|---:|"]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | {int(r.triggered_n)} | {fmt_pct(r.winner_preservation)} | {fmt_num(r.baseline_pf)}→{fmt_num(r.candidate_pf)} | ${r.net_improvement:.2f} | {fmt_num(r.baseline_pf_5bps)}→{fmt_num(r.candidate_pf_5bps)} | ${r.net_improvement_5bps:.2f} | ${r.gross_loss_reduction:.2f} |"
            )

    status = "SOL_LONG_H1_EARLY_INVALIDATION_A6_SUPPORTED" if supported else "SOL_LONG_H1_EARLY_INVALIDATION_A6_REJECTED"
    lines += [
        "", "## Decision", "",
        f"- Frozen lane: **{frozen_lane or 'NONE'}**.",
        f"- Validation: **{status_reason}**.", "",
        f"**Status: {status}**", "",
        "If supported, the next stage must integrate the frozen early-invalidation rule with the frozen H2 recovery mechanism and recompute episode economics causally. If rejected, do not salvage it with OOS threshold retuning.", "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
