#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A3_PATH = Path(__file__).resolve().parent / "sol_long_h1_loss_anatomy_a3.py"
spec = importlib.util.spec_from_file_location("sol_a3", A3_PATH)
a3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a3)
a2 = a3.a2

IN_PARENT = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_TRADES.csv"
IN_A3 = ROOT / "SOL_LONG_H1_LOSS_ANATOMY_A3_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_Result.md"
OUT_ANAT = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_ANATOMY.csv"
OUT_DEV = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_Status.txt"

VISITS = (2, 3, 4)
TARGET_R = 0.40
RECOVERY_MIN = 720
RECOVERY_BARS = RECOVERY_MIN // 5
STRESS = a2.STRESS
EPS = 1e-12


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def load_parent():
    p = pd.read_csv(IN_PARENT)
    for c in ["execution_start", "h1_ts", "h1_break_ts", "entry_ts", "exit_ts", "invalidation_close_ts"]:
        p[c] = pd.to_datetime(p[c], utc=True, errors="coerce")
    q = p[(p.family == "E0_RESTING_H") & (np.isclose(pd.to_numeric(p.target_R, errors="coerce"), TARGET_R))].copy()
    if "candidate_scope" in q.columns:
        q = q[q.candidate_scope == "FROZEN_WINNER"].copy()
    if q.empty:
        raise RuntimeError("Frozen A2 parent not found")
    return q.sort_values(["role", "partition", "entry_ts"]).reset_index(drop=True)


def load_a3_classes():
    t = pd.read_csv(IN_A3)
    for c in ["execution_start", "entry_ts", "exit_ts"]:
        t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    keep = ["role", "partition", "execution_start", "entry_ts", "exit_ts", "loss_class"]
    return t[keep].copy()


def market():
    x, coverage = a2.a1.load5()
    return x, a2.make_market_with_open(x), coverage


def episode_starts(m, entry_i, endpos, H):
    hi = m["high"]
    starts = []
    in_ep = False
    for i in range(entry_i, endpos):
        touching = float(hi[i]) >= H
        if touching and not in_ep:
            starts.append(i)
            in_ep = True
        elif not touching:
            in_ep = False
    return starts


def recovery_window(m, r):
    idx = m["idx"]
    ei = int(idx.searchsorted(pd.Timestamp(r.entry_ts), "left"))
    xi = int(idx.searchsorted(pd.Timestamp(r.exit_ts), "left"))
    if ei >= len(idx) or xi >= len(idx) or idx[ei] != r.entry_ts or idx[xi] != r.exit_ts:
        return None
    watch_end_ts = pd.Timestamp(r.exit_ts) + pd.Timedelta(minutes=RECOVERY_MIN)
    endpos = int(idx.searchsorted(watch_end_ts, "left"))
    endpos = min(endpos, len(idx))
    pa, pz = a2.part_bounds(r.partition)
    endpos = min(endpos, int(idx.searchsorted(pz, "left")))
    if endpos <= xi:
        return None
    eps = episode_starts(m, ei, endpos, float(r.H))
    return ei, xi, endpos, eps


def latent_anatomy_one(m, r):
    w = recovery_window(m, r)
    if w is None:
        return None
    ei, xi, endpos, eps = w
    idx, hi = m["idx"], m["high"]
    H, R = float(r.H), float(r.R)
    target = H + TARGET_R * R
    hit_i = -1
    for i in range(xi, endpos):
        if float(hi[i]) >= target:
            hit_i = i
            break
    target_visit = np.nan
    target_visit_start = pd.NaT
    target_visit_eligible = False
    if hit_i >= 0:
        for j, st in enumerate(eps, start=1):
            nxt = eps[j] if j < len(eps) else endpos
            if st <= hit_i < nxt:
                target_visit = j
                target_visit_start = idx[st]
                target_visit_eligible = st >= xi
                break
    return {
        "role": r.role,
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "parent_entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_pnl": float(r.pnl),
        "parent_pnl_5bps": float(r.pnl_5bps),
        "loss_class": r.loss_class,
        "latent_target_recovered": hit_i >= 0,
        "latent_recovery_min": ((idx[hit_i] - pd.Timestamp(r.exit_ts)) / pd.Timedelta(minutes=1)) if hit_i >= 0 else np.nan,
        "latent_target_visit": target_visit,
        "latent_target_visit_start": target_visit_start,
        "latent_target_visit_entry_eligible": target_visit_eligible,
        "visit_count_through_watch": len(eps),
    }


def simulate_recovery(m, r, visit_n):
    w = recovery_window(m, r)
    if w is None:
        return None
    ei, xi, endpos, eps = w
    if len(eps) < visit_n:
        return None
    vi = eps[visit_n - 1]
    if vi < xi:
        return None
    idx = m["idx"]
    op, hi, cl = m["open"], m["high"], m["close"]
    H, L, R = float(r.H), float(r.L), float(r.R)
    target = H + TARGET_R * R
    entry_price = float(op[vi]) if float(op[vi]) > H else H
    confirmed = float(cl[vi]) > H
    exit_i = endpos - 1
    exit_price = float(cl[exit_i])
    reason = "TIME"
    break_i = vi if confirmed else -1
    invalid_i = -1

    for i in range(vi + 1, endpos):
        if not confirmed and float(cl[i]) > H:
            confirmed = True
            break_i = i

        if float(hi[i]) >= target:
            exit_i = i
            exit_price = target
            reason = "TARGET"
            break

        bad = (float(cl[i]) <= H) if confirmed else (float(cl[i]) < L)
        if bad:
            invalid_i = i
            ni = i + 1
            if ni < endpos:
                exit_i = ni
                exit_price = float(op[ni])
                reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            else:
                exit_i = i
                exit_price = float(cl[i])
                reason = "TIME_AFTER_FINAL_INVALIDATION"
            break

    ret = exit_price / entry_price - 1.0
    pnl = ret * a2.NOTIONAL
    ret5 = ret - STRESS
    pnl5 = ret5 * a2.NOTIONAL
    parent_pnl = float(r.pnl)
    parent_pnl5 = float(r.pnl_5bps)
    return {
        "role": r.role,
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "loss_class": r.loss_class,
        "visit_n": visit_n,
        "lane": f"REC_H{visit_n}",
        "H": H,
        "L": L,
        "R": R,
        "parent_entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_pnl": parent_pnl,
        "parent_pnl_5bps": parent_pnl5,
        "recovery_entry_ts": idx[vi],
        "recovery_entry_price": entry_price,
        "recovery_break_ts": idx[break_i] if break_i >= 0 else pd.NaT,
        "recovery_exit_ts": idx[exit_i],
        "recovery_exit_price": exit_price,
        "recovery_exit_reason": reason,
        "recovery_pnl": pnl,
        "recovery_pnl_5bps": pnl5,
        "recovery_won": pnl > 0,
        "recovery_won_5bps": pnl5 > 0,
        "combined_episode_pnl": parent_pnl + pnl,
        "combined_episode_pnl_5bps": parent_pnl5 + pnl5,
        "rescued": parent_pnl + pnl > 0,
        "rescued_5bps": parent_pnl5 + pnl5 > 0,
    }


def summarize_recovery(t, base_parent, partition):
    if t.empty:
        return {
            "n": 0, "wr": np.nan, "pf": np.nan, "expectancy": np.nan, "net": 0.0,
            "wr_5bps": np.nan, "pf_5bps": np.nan, "expectancy_5bps": np.nan, "net_5bps": 0.0,
            "rescue_rate": np.nan, "rescue_rate_5bps": np.nan,
            "combined_pf": np.nan, "combined_expectancy": np.nan, "combined_net": 0.0,
            "combined_pf_5bps": np.nan, "combined_expectancy_5bps": np.nan, "combined_net_5bps": 0.0,
            "represented_parent_loss": 0.0,
            "overlay_pf": pf(base_parent.pnl), "overlay_net": float(base_parent.pnl.sum()),
            "overlay_pf_5bps": pf(base_parent.pnl_5bps), "overlay_net_5bps": float(base_parent.pnl_5bps.sum()),
        }
    rec = pd.to_numeric(t.recovery_pnl, errors="coerce")
    rec5 = pd.to_numeric(t.recovery_pnl_5bps, errors="coerce")
    comb = pd.to_numeric(t.combined_episode_pnl, errors="coerce")
    comb5 = pd.to_numeric(t.combined_episode_pnl_5bps, errors="coerce")
    overlay_vals = pd.concat([pd.to_numeric(base_parent.pnl, errors="coerce"), rec], ignore_index=True)
    overlay_vals5 = pd.concat([pd.to_numeric(base_parent.pnl_5bps, errors="coerce"), rec5], ignore_index=True)
    return {
        "n": len(t),
        "wr": float((rec > 0).mean()), "pf": pf(rec), "expectancy": float(rec.mean()), "net": float(rec.sum()),
        "wr_5bps": float((rec5 > 0).mean()), "pf_5bps": pf(rec5), "expectancy_5bps": float(rec5.mean()), "net_5bps": float(rec5.sum()),
        "rescue_rate": float((comb > 0).mean()), "rescue_rate_5bps": float((comb5 > 0).mean()),
        "combined_pf": pf(comb), "combined_expectancy": float(comb.mean()), "combined_net": float(comb.sum()),
        "combined_pf_5bps": pf(comb5), "combined_expectancy_5bps": float(comb5.mean()), "combined_net_5bps": float(comb5.sum()),
        "represented_parent_loss": float(-pd.to_numeric(t.parent_pnl, errors="coerce").sum()),
        "overlay_pf": pf(overlay_vals), "overlay_net": float(overlay_vals.sum()),
        "overlay_pf_5bps": pf(overlay_vals5), "overlay_net_5bps": float(overlay_vals5.sum()),
    }


def dev_lane_summary(t, base_parent, visit_n):
    s = summarize_recovery(t, base_parent, "development")
    positive_blocks = 0
    adequate_blocks = 0
    block_cols = {}
    for bi in range(6):
        z = t[t.dev_block == bi]
        zn = len(z)
        znet = float(z.recovery_pnl.sum()) if zn else 0.0
        if zn >= 5:
            adequate_blocks += 1
            if znet > 0:
                positive_blocks += 1
        block_cols[f"b{bi+1}_n"] = zn
        block_cols[f"b{bi+1}_net"] = znet
    eligible = bool(
        s["n"] >= 40
        and pd.notna(s["pf"]) and s["pf"] > 1.15
        and s["expectancy"] > 0
        and pd.notna(s["pf_5bps"]) and s["pf_5bps"] > 1.00
        and s["expectancy_5bps"] > 0
        and pd.notna(s["rescue_rate"]) and s["rescue_rate"] >= 0.25
        and s["net"] > 0
        and positive_blocks >= 4
    )
    return {
        "visit_n": visit_n, "lane": f"REC_H{visit_n}", **s,
        "adequate_blocks": adequate_blocks, "positive_blocks": positive_blocks,
        "eligible": eligible, **block_cols,
    }


def choose_dev(dev):
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    return q.sort_values(
        ["net_5bps", "rescue_rate", "pf_5bps", "pf", "visit_n"],
        ascending=[False, False, False, False, True],
    ).iloc[0]


def anatomy_summary(anat):
    rows = []
    for (role, part, lc), q in anat.groupby(["role", "partition", "loss_class"], sort=False):
        hit = q[q.latent_target_recovered]
        visits = pd.to_numeric(hit.latent_target_visit, errors="coerce").dropna()
        mode = int(visits.mode().iloc[0]) if len(visits) and not visits.mode().empty else np.nan
        rows.append({
            "role": role, "partition": part, "loss_class": lc, "n": len(q),
            "latent_recovery_rate": float(q.latent_target_recovered.mean()),
            "median_recovery_min": float(hit.latent_recovery_min.median()) if len(hit) else np.nan,
            "modal_target_visit": mode,
            "eligible_visit_target_rate": float(hit.latent_target_visit_entry_eligible.mean()) if len(hit) else np.nan,
            "median_parent_loss": float((-q.parent_pnl).median()),
        })
    return pd.DataFrame(rows)


def fmt_pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def fmt_num(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def main():
    parent = load_parent()
    a3c = load_a3_classes()
    parent = parent.merge(a3c, on=["role", "partition", "execution_start", "entry_ts", "exit_ts"], how="left", validate="one_to_one")
    if parent.loss_class.isna().any():
        raise RuntimeError("A3 loss-class merge parity failure")
    losers = parent[parent.pnl <= 0].copy()
    x, m, coverage = market()

    anatomy_rows = []
    for _, r in losers.iterrows():
        z = latent_anatomy_one(m, r)
        if z is not None:
            anatomy_rows.append(z)
    anatomy = pd.DataFrame(anatomy_rows)
    anat_sum = anatomy_summary(anatomy)
    anatomy.to_csv(OUT_ANAT, index=False)

    cd_parent = parent[(parent.role == "CENTRAL") & (parent.partition == "development")].copy()
    if len(cd_parent) != 617 or abs(float(cd_parent.pnl.sum()) - 314.0598611635086) > 1e-6:
        raise RuntimeError("A2 central Development parent parity failed")

    dev_rows = []
    dev_trades = []
    cd_losers = losers[(losers.role == "CENTRAL") & (losers.partition == "development")]
    for vn in VISITS:
        rows = []
        for _, r in cd_losers.iterrows():
            z = simulate_recovery(m, r, vn)
            if z is not None:
                rows.append(z)
        t = pd.DataFrame(rows)
        if not t.empty:
            dev_trades.append(t)
        dev_rows.append(dev_lane_summary(t, cd_parent, vn))
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV, index=False)
    winner = choose_dev(dev)

    all_trades = list(dev_trades)
    oos_rows = []
    if winner is not None:
        vn = int(winner.visit_n)
        cells = [
            ("CENTRAL", "external"), ("CENTRAL", "reference_validation"),
            ("CLOCK_SUPPORT", "external"), ("CLOCK_SUPPORT", "reference_validation"),
            ("REF_SUPPORT", "external"), ("REF_SUPPORT", "reference_validation"),
        ]
        for role, part in cells:
            bp = parent[(parent.role == role) & (parent.partition == part)].copy()
            bl = losers[(losers.role == role) & (losers.partition == part)].copy()
            rows = []
            for _, r in bl.iterrows():
                z = simulate_recovery(m, r, vn)
                if z is not None:
                    rows.append(z)
            t = pd.DataFrame(rows)
            if not t.empty:
                all_trades.append(t)
            s = summarize_recovery(t, bp, part)
            oos_rows.append({"role": role, "partition": part, "visit_n": vn, "lane": f"REC_H{vn}", **s})
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    trades.to_csv(OUT_TRADES, index=False)

    supported = False
    if winner is not None and not oos.empty:
        ce = oos[(oos.role == "CENTRAL") & (oos.partition == "external")]
        cr = oos[(oos.role == "CENTRAL") & (oos.partition == "reference_validation")]
        support = oos[oos.role != "CENTRAL"]
        supported = bool(
            len(ce) == 1 and len(cr) == 1
            and float(ce.iloc[0].net) > 0 and float(cr.iloc[0].net) > 0
            and float(ce.iloc[0].net_5bps) > 0 and float(cr.iloc[0].net_5bps) > 0
            and float(ce.iloc[0].overlay_net) > float(parent[(parent.role == "CENTRAL") & (parent.partition == "external")].pnl.sum())
            and float(cr.iloc[0].overlay_net) > float(parent[(parent.role == "CENTRAL") & (parent.partition == "reference_validation")].pnl.sum())
            and float(ce.iloc[0].rescue_rate) > 0 and float(cr.iloc[0].rescue_rate) > 0
            and int((support.net > 0).sum()) >= 3
        )

    status = "SOL_LONG_H1_LOSS_RECOVERY_A4_SUPPORTED" if supported else "SOL_LONG_H1_LOSS_RECOVERY_A4_FAILED"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# SOL LONG H1 Loss Recovery — A4 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "A4 keeps every frozen A2 parent loss unchanged and asks whether one later resting-H recovery entry can make the combined episode profitable.", "",
        "## Central Development latent recovery anatomy", "",
        "| Parent loss class | N | Target eventually hit after exit | Median time to E40 | Modal target visit | Target visit entry-eligible | Median original loss |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    az = anat_sum[(anat_sum.role == "CENTRAL") & (anat_sum.partition == "development")].sort_values("n", ascending=False)
    for _, r in az.iterrows():
        mv = "-" if pd.isna(r.modal_target_visit) else f"H{int(r.modal_target_visit)}"
        lines.append(f"| {r.loss_class} | {int(r.n)} | {fmt_pct(r.latent_recovery_rate)} | {fmt_num(r.median_recovery_min,0)}m | {mv} | {fmt_pct(r.eligible_visit_target_rate)} | ${r.median_parent_loss:.2f} |")

    lines += ["", "## Development recovery-lane economics", "",
              "| Lane | N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | Rescue rate | 5bps rescue | Overlay PF | Overlay net | +blocks | Pass |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in dev.iterrows():
        lines.append(f"| {r.lane} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | ${r.expectancy:.2f} | ${r.net:.2f} | {fmt_num(r.pf_5bps)} | ${r.expectancy_5bps:.2f} | {fmt_pct(r.rescue_rate)} | {fmt_pct(r.rescue_rate_5bps)} | {fmt_num(r.overlay_pf)} | ${r.overlay_net:.2f} | {int(r.positive_blocks)}/6 | {'YES' if bool(r.eligible) else 'NO'} |")

    if winner is None:
        lines += ["", "## Development decision", "", "No preregistered H2/H3/H4 recovery lane passed the Development gate. OOS recovery entry economics were not opened for substitution."]
    else:
        lines += ["", "## Frozen Development recovery lane", "",
                  f"- Lane: **{winner.lane}**.",
                  f"- Recovery N: **{int(winner.n)}**; WR **{fmt_pct(winner.wr)}**; PF **{fmt_num(winner.pf)}**; expectancy **${winner.expectancy:.2f}**; net **${winner.net:.2f}**.",
                  f"- 5bps PF **{fmt_num(winner.pf_5bps)}**; expectancy **${winner.expectancy_5bps:.2f}**.",
                  f"- Episode rescue rate: **{fmt_pct(winner.rescue_rate)}**; 5bps **{fmt_pct(winner.rescue_rate_5bps)}**.",
                  f"- Frozen A2 Central Development PF/net becomes **{fmt_num(winner.overlay_pf)} / ${winner.overlay_net:.2f}** when the recovery overlay is added as an extra trade.",
                  "", "## OOS recovery economics", "",
                  "| Role | Partition | N | WR | PF | Exp | Net | 5bps PF | 5bps Net | Rescue rate | Overlay PF | Overlay net |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in oos.iterrows():
            lines.append(f"| {r.role} | {r.partition} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | ${r.expectancy:.2f} | ${r.net:.2f} | {fmt_num(r.pf_5bps)} | ${r.net_5bps:.2f} | {fmt_pct(r.rescue_rate)} | {fmt_num(r.overlay_pf)} | ${r.overlay_net:.2f} |")

    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if supported:
        lines.append("A later canonical H-visit can be used as a supported second-chance recovery overlay under the preregistered gates. This is still research-only and is not promoted to the live bot.")
    elif winner is not None:
        lines.append("A Development recovery lane existed, but it did not replicate strongly enough across the preregistered OOS/support gates. Do not substitute another visit post hoc.")
    else:
        lines.append("The H2/H3/H4 second-chance family did not produce a Development-supported recovery overlay. The latent recovery anatomy remains useful for diagnosing whether losses recover too late, at the wrong visit, or with insufficient payoff to offset the original loss.")
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
