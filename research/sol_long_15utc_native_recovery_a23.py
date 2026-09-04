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

OUT_MD = ROOT / "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_Result.md"
OUT_DEV = ROOT / "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_Status.txt"

TARGET_R = 0.40
VISITS = (2, 3, 4)
CENTRAL = (360, 15)
CLOCK_SUPPORT = (360, 16)
REF_SUPPORT = (300, 15)


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def parent_for(m, partition, ref_min, hour, role):
    q = a2.trades_for(m, partition, int(ref_min), int(hour), "E0_RESTING_H", TARGET_R)
    if q.empty:
        return q
    q = q.copy()
    q["role"] = role
    q["loss_class"] = "A20_PARENT_LOSS"
    return q


def recoveries_for(m, parent, visit_n):
    rows = []
    for _, r in parent[parent.pnl <= 0].iterrows():
        z = a4.simulate_recovery(m, r, int(visit_n))
        if z is not None:
            rows.append(z)
    return pd.DataFrame(rows)


def parent_stats(parent):
    p = pd.to_numeric(parent.pnl, errors="coerce")
    p5 = pd.to_numeric(parent.pnl_5bps, errors="coerce")
    return {
        "parent_n": len(parent),
        "parent_pf": pf(p),
        "parent_net": float(p.sum()),
        "parent_pf_5bps": pf(p5),
        "parent_net_5bps": float(p5.sum()),
    }


def summarize(parent, rec, partition):
    ps = parent_stats(parent)
    rs = a4.summarize_recovery(rec, parent, partition)
    return {**ps, **{f"recovery_{k}": v for k, v in rs.items()}}


def development_row(parent, rec, visit_n):
    s = summarize(parent, rec, "development")
    adequate = pos_raw = pos_stress = 0
    blocks = {}
    for bi in range(6):
        z = rec[pd.to_numeric(rec.dev_block, errors="coerce") == bi] if len(rec) else pd.DataFrame()
        n = len(z)
        nr = float(pd.to_numeric(z.recovery_pnl, errors="coerce").sum()) if n else 0.0
        ns = float(pd.to_numeric(z.recovery_pnl_5bps, errors="coerce").sum()) if n else 0.0
        blocks[f"b{bi+1}_n"] = n
        blocks[f"b{bi+1}_net"] = nr
        blocks[f"b{bi+1}_net_5bps"] = ns
        if n >= 5:
            adequate += 1
            pos_raw += int(nr > 0)
            pos_stress += int(ns > 0)
    eligible = bool(
        s["recovery_n"] >= 60
        and pd.notna(s["recovery_pf"]) and s["recovery_pf"] > 1.15
        and s["recovery_expectancy"] > 0 and s["recovery_net"] > 0
        and pd.notna(s["recovery_pf_5bps"]) and s["recovery_pf_5bps"] > 1.00
        and s["recovery_expectancy_5bps"] > 0 and s["recovery_net_5bps"] > 0
        and pd.notna(s["recovery_rescue_rate"]) and s["recovery_rescue_rate"] >= 0.20
        and s["recovery_overlay_pf"] > s["parent_pf"]
        and s["recovery_overlay_pf_5bps"] > s["parent_pf_5bps"]
        and s["recovery_overlay_net"] > s["parent_net"]
        and s["recovery_overlay_net_5bps"] > s["parent_net_5bps"]
        and adequate >= 4 and pos_raw >= 4 and pos_stress >= 4
    )
    return {
        "visit_n": visit_n,
        "lane": f"REC_H{visit_n}",
        **s,
        "adequate_blocks": adequate,
        "positive_blocks_raw": pos_raw,
        "positive_blocks_5bps": pos_stress,
        "eligible": eligible,
        **blocks,
    }


def choose_winner(dev):
    q = dev[dev.eligible.astype(bool)].copy()
    if q.empty:
        return None
    return q.sort_values(
        ["recovery_net_5bps", "recovery_pf_5bps", "recovery_net", "recovery_rescue_rate", "visit_n"],
        ascending=[False, False, False, False, True], kind="mergesort"
    ).iloc[0]


def oos_pass(oos):
    exact = oos[oos.role == "CENTRAL"]
    support = oos[oos.role != "CENTRAL"]
    central_ok = bool(
        len(exact) == 2
        and (exact.recovery_net > 0).all()
        and (exact.recovery_net_5bps > 0).all()
        and (exact.recovery_overlay_pf > exact.parent_pf).all()
        and (exact.recovery_overlay_pf_5bps > exact.parent_pf_5bps).all()
        and (exact.recovery_overlay_net > exact.parent_net).all()
        and (exact.recovery_overlay_net_5bps > exact.parent_net_5bps).all()
    )
    sr = int((support.recovery_net > 0).sum())
    ss = int((support.recovery_net_5bps > 0).sum())
    return bool(central_ok and sr >= 3 and ss >= 3), central_ok, sr, ss


def write_result(dev, oos, winner, coverage, status):
    lines = [
        "# SOL LONG 15:00 UTC Native Recovery — A23 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "A23 calibrates one bounded recovery visit natively inside the A20-supported R360/15 habitat. H2/H3/H4 are Development candidates; only one may be frozen for OOS.", "",
        "## Central Development", "",
        "| Lane | N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | Rescue raw/stress | Overlay PF raw/stress | Overlay net raw/stress | +blocks raw/stress | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.lane} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_expectancy)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_expectancy_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.recovery_rescue_rate)}/{pct(r.recovery_rescue_rate_5bps)} | {fmt(r.recovery_overlay_pf)}/{fmt(r.recovery_overlay_pf_5bps)} | ${fmt(r.recovery_overlay_net)}/${fmt(r.recovery_overlay_net_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )
    lines += ["", f"Frozen Development winner: **{winner.lane if winner is not None else 'NONE'}**.", ""]
    if len(oos):
        lines += [
            "## Frozen OOS", "",
            "| Role | Partition | Cell | Lane | N | PF | Net | 5bps PF | 5bps Net | Overlay PF raw/stress | Overlay net raw/stress |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---|---|",
        ]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | R{int(r.ref_min)}/{int(r.hour):02d} | {r.lane} | {int(r.recovery_n)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {fmt(r.recovery_overlay_pf)}/{fmt(r.recovery_overlay_pf_5bps)} | ${fmt(r.recovery_overlay_net)}/${fmt(r.recovery_overlay_net_5bps)} |"
            )
        passed, central_ok, sr, ss = oos_pass(oos)
        lines += ["", f"Validation: **central_ok={central_ok}; support positive raw={sr}/4; support positive 5bps={ss}/4**.", ""]
    lines += ["## Decision", "", f"**Status: {status}**", "", "A rejected A23 leaves the A20 15:00 habitat parent-only. No OOS retuning.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    x, m, coverage = a4.market()
    pdev = parent_for(m, "development", *CENTRAL, "CENTRAL")
    dev_rows, all_rec = [], []
    for vn in VISITS:
        rec = recoveries_for(m, pdev, vn)
        if len(rec): all_rec.append(rec)
        dev_rows.append(development_row(pdev, rec, vn))
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV, index=False)
    winner = choose_winner(dev)

    oos_rows = []
    if winner is not None:
        vn = int(winner.visit_n)
        for role, cell in [("CENTRAL", CENTRAL), ("CLOCK_SUPPORT", CLOCK_SUPPORT), ("REF_SUPPORT", REF_SUPPORT)]:
            for partition in ("external", "reference_validation"):
                p = parent_for(m, partition, *cell, role)
                r = recoveries_for(m, p, vn)
                if len(r): all_rec.append(r)
                oos_rows.append({"role": role, "partition": partition, "ref_min": cell[0], "hour": cell[1], "lane": f"REC_H{vn}", **summarize(p, r, partition)})
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)

    if winner is None:
        status = "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_REJECTED_DEVELOPMENT"
    else:
        passed, _, _, _ = oos_pass(oos)
        status = "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_SUPPORTED" if passed else "SOL_LONG_15UTC_NATIVE_RECOVERY_A23_REJECTED_OOS"
    pd.concat(all_rec, ignore_index=True).to_csv(OUT_TRADES, index=False) if all_rec else pd.DataFrame().to_csv(OUT_TRADES, index=False)
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    write_result(dev, oos, winner, coverage, status)
    print(status)


if __name__ == "__main__":
    main()
