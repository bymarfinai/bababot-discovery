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

OUT_MD = ROOT / "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_Result.md"
OUT_DEV = ROOT / "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_Status.txt"

TARGET_R = 0.40
VISIT_N = 2
CENTRAL = (420, 3)
CLOCK_SUPPORT = (420, 4)
REF_SUPPORT = (480, 3)
STRESS = a2.STRESS


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
    q["loss_class"] = "A17_PARENT_LOSS"
    return q


def recoveries_for(m, parent):
    rows = []
    if parent.empty:
        return pd.DataFrame()
    for _, r in parent[parent.pnl <= 0].iterrows():
        z = a4.simulate_recovery(m, r, VISIT_N)
        if z is not None:
            rows.append(z)
    return pd.DataFrame(rows)


def parent_stats(parent):
    p = pd.to_numeric(parent.pnl, errors="coerce")
    p5 = pd.to_numeric(parent.pnl_5bps, errors="coerce")
    return {
        "parent_n": len(parent),
        "parent_wr": float((p > 0).mean()) if len(parent) else np.nan,
        "parent_pf": pf(p),
        "parent_expectancy": float(p.mean()) if len(parent) else np.nan,
        "parent_net": float(p.sum()),
        "parent_pf_5bps": pf(p5),
        "parent_expectancy_5bps": float(p5.mean()) if len(parent) else np.nan,
        "parent_net_5bps": float(p5.sum()),
    }


def episode_stats(parent, rec):
    rmap = {}
    if rec is not None and len(rec):
        for _, r in rec.iterrows():
            key = (str(r.execution_start), str(r.parent_entry_ts))
            rmap[key] = r
    raw = []
    stress = []
    for _, p in parent.iterrows():
        key = (str(p.execution_start), str(p.entry_ts))
        rr = rmap.get(key)
        add = float(rr.recovery_pnl) if rr is not None else 0.0
        add5 = float(rr.recovery_pnl_5bps) if rr is not None else 0.0
        raw.append(float(p.pnl) + add)
        stress.append(float(p.pnl_5bps) + add5)
    x = pd.Series(raw, dtype=float)
    x5 = pd.Series(stress, dtype=float)
    return {
        "episode_wr": float((x > 0).mean()) if len(x) else np.nan,
        "episode_pf": pf(x),
        "episode_net": float(x.sum()),
        "episode_gross_loss": float(-x[x <= 0].sum()),
        "episode_wr_5bps": float((x5 > 0).mean()) if len(x5) else np.nan,
        "episode_pf_5bps": pf(x5),
        "episode_net_5bps": float(x5.sum()),
        "episode_gross_loss_5bps": float(-x5[x5 <= 0].sum()),
    }


def summarize(parent, rec, partition):
    ps = parent_stats(parent)
    rs = a4.summarize_recovery(rec, parent, partition)
    es = episode_stats(parent, rec)
    return {**ps, **{f"recovery_{k}": v for k, v in rs.items()}, **es}


def development_row(parent, rec):
    s = summarize(parent, rec, "development")
    pos_raw = 0
    pos_stress = 0
    adequate = 0
    blocks = {}
    for bi in range(6):
        z = rec[pd.to_numeric(rec.dev_block, errors="coerce") == bi] if len(rec) else pd.DataFrame()
        n = len(z)
        net = float(pd.to_numeric(z.recovery_pnl, errors="coerce").sum()) if n else 0.0
        net5 = float(pd.to_numeric(z.recovery_pnl_5bps, errors="coerce").sum()) if n else 0.0
        blocks[f"b{bi+1}_n"] = n
        blocks[f"b{bi+1}_net"] = net
        blocks[f"b{bi+1}_net_5bps"] = net5
        if n >= 5:
            adequate += 1
            if net > 0: pos_raw += 1
            if net5 > 0: pos_stress += 1

    eligible = bool(
        s["recovery_n"] >= 80
        and pd.notna(s["recovery_pf"]) and s["recovery_pf"] > 1.10
        and pd.notna(s["recovery_pf_5bps"]) and s["recovery_pf_5bps"] > 1.00
        and s["recovery_expectancy"] > 0
        and s["recovery_net"] > 0
        and s["recovery_expectancy_5bps"] > 0
        and s["recovery_net_5bps"] > 0
        and pd.notna(s["recovery_rescue_rate"]) and s["recovery_rescue_rate"] >= 0.20
        and pd.notna(s["recovery_rescue_rate_5bps"]) and s["recovery_rescue_rate_5bps"] > 0
        and s["recovery_overlay_pf"] > s["parent_pf"]
        and s["recovery_overlay_pf_5bps"] > s["parent_pf_5bps"]
        and s["recovery_overlay_net"] > s["parent_net"]
        and s["recovery_overlay_net_5bps"] > s["parent_net_5bps"]
        and adequate >= 4
        and pos_raw >= 4
        and pos_stress >= 4
    )
    return {
        "role": "CENTRAL",
        "partition": "development",
        "ref_min": CENTRAL[0],
        "hour": CENTRAL[1],
        **s,
        "adequate_blocks": adequate,
        "positive_blocks_raw": pos_raw,
        "positive_blocks_5bps": pos_stress,
        "eligible": eligible,
        **blocks,
    }


def oos_pass(oos):
    central = oos[oos.role == "CENTRAL"].copy()
    support = oos[oos.role != "CENTRAL"].copy()
    if len(central) != 2:
        return False, False, 0, 0
    central_ok = bool(
        (central.recovery_net > 0).all()
        and (central.recovery_net_5bps > 0).all()
        and (central.recovery_overlay_pf > central.parent_pf).all()
        and (central.recovery_overlay_pf_5bps > central.parent_pf_5bps).all()
        and (central.recovery_rescue_rate > 0).all()
    )
    sr = int((support.recovery_net > 0).sum())
    ss = int((support.recovery_net_5bps > 0).sum())
    return central_ok and sr >= 3 and ss >= 3, central_ok, sr, ss


def write_result(dev, oos, coverage, status):
    r = dev.iloc[0]
    lines = [
        "# SOL LONG New-Zone H2 Recovery Transfer — A18 Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.",
        "",
        "A18 tests only A4 REC_H2 on the A17-supported R420/03 parent zone. H3/H4 and all rejected Stage-11 interventions remain absent.",
        "",
        "## Central Development",
        "",
        "| Parent N | Parent PF | Parent Net | H2 N | H2 WR | H2 PF | H2 Exp | H2 Net | 5bps PF | 5bps Exp | 5bps Net | Rescue raw/stress | Overlay PF raw/stress | +blocks raw/stress | Pass |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
        f"| {int(r.parent_n)} | {fmt(r.parent_pf)} | ${fmt(r.parent_net)} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_expectancy)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_expectancy_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.recovery_rescue_rate)}/{pct(r.recovery_rescue_rate_5bps)} | {fmt(r.recovery_overlay_pf)}/{fmt(r.recovery_overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |",
        "",
        f"Parent-only net → parent+H2 net: **${fmt(r.parent_net)} → ${fmt(r.recovery_overlay_net)}** raw; **${fmt(r.parent_net_5bps)} → ${fmt(r.recovery_overlay_net_5bps)}** after 5bps.",
        "",
    ]
    if len(oos):
        lines += [
            "## Frozen OOS",
            "",
            "| Role | Partition | Cell | Parent PF | Parent Net | H2 N | H2 PF | H2 Net | 5bps H2 PF | 5bps H2 Net | Rescue raw/stress | Overlay PF raw/stress |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
        for _, z in oos.iterrows():
            lines.append(
                f"| {z.role} | {z.partition} | R{int(z.ref_min)}/{int(z.hour):02d} | {fmt(z.parent_pf)} | ${fmt(z.parent_net)} | {int(z.recovery_n)} | {fmt(z.recovery_pf)} | ${fmt(z.recovery_net)} | {fmt(z.recovery_pf_5bps)} | ${fmt(z.recovery_net_5bps)} | {pct(z.recovery_rescue_rate)}/{pct(z.recovery_rescue_rate_5bps)} | {fmt(z.recovery_overlay_pf)}/{fmt(z.recovery_overlay_pf_5bps)} |"
            )
        passed, central_ok, sr, ss = oos_pass(oos)
        lines += ["", f"Validation: **central_ok={central_ok}; support positive raw={sr}/4; support positive 5bps={ss}/4**.", ""]

    lines += [
        "## Decision", "",
        f"**Status: {status}**", "",
        "A supported A18 promotes REC_H2 only for the A17 R420/03 zone and authorizes subsequent two-zone capital/concurrency benchmarking. A rejected A18 leaves the A17 parent valid by itself.", "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    x, m, coverage = a4.market()

    pdev = parent_for(m, "development", CENTRAL[0], CENTRAL[1], "CENTRAL")
    rdev = recoveries_for(m, pdev)
    dev = pd.DataFrame([development_row(pdev, rdev)])
    dev.to_csv(OUT_DEV, index=False)

    oos_rows = []
    all_rec = [rdev] if len(rdev) else []
    if bool(dev.iloc[0].eligible):
        cells = [
            ("CENTRAL", CENTRAL),
            ("CLOCK_SUPPORT", CLOCK_SUPPORT),
            ("REF_SUPPORT", REF_SUPPORT),
        ]
        for role, (ref_min, hour) in cells:
            for partition in ("external", "reference_validation"):
                p = parent_for(m, partition, ref_min, hour, role)
                r = recoveries_for(m, p)
                if len(r): all_rec.append(r)
                oos_rows.append({
                    "role": role,
                    "partition": partition,
                    "ref_min": ref_min,
                    "hour": hour,
                    **summarize(p, r, partition),
                })
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)

    if not bool(dev.iloc[0].eligible):
        status = "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_REJECTED_DEVELOPMENT"
    else:
        passed, _, _, _ = oos_pass(oos)
        status = "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_SUPPORTED_FOR_TWO_ZONE_BENCHMARK" if passed else "SOL_LONG_NEW_ZONE_H2_RECOVERY_A18_REJECTED_OOS"

    trades = pd.concat(all_rec, ignore_index=True) if all_rec else pd.DataFrame()
    trades.to_csv(OUT_TRADES, index=False)
    write_result(dev, oos, coverage, status)
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
