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
OUT_MD = ROOT / "SOL_LONG_TWO_ZONE_BENCHMARK_A19_Result.md"
OUT_SUMMARY = ROOT / "SOL_LONG_TWO_ZONE_BENCHMARK_A19_SUMMARY.csv"
OUT_COMPONENTS = ROOT / "SOL_LONG_TWO_ZONE_BENCHMARK_A19_COMPONENTS.csv"
OUT_STATUS = ROOT / "SOL_LONG_TWO_ZONE_BENCHMARK_A19_Status.txt"

NEW_REF = 420
NEW_HOUR = 3
TARGET_R = 0.40


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


def partition_years(partition):
    a, z = a2.part_bounds(partition)
    return float((z - a) / pd.Timedelta(days=365.2425))


def to_component_parent(q, zone, component):
    if q.empty: return pd.DataFrame()
    return pd.DataFrame({
        "partition": q.partition.astype(str),
        "zone": zone,
        "component": component,
        "entry_ts": pd.to_datetime(q.entry_ts, utc=True),
        "exit_ts": pd.to_datetime(q.exit_ts, utc=True),
        "pnl": pd.to_numeric(q.pnl, errors="coerce"),
        "pnl_5bps": pd.to_numeric(q.pnl_5bps, errors="coerce"),
    })


def to_component_h2(q):
    if q.empty: return pd.DataFrame()
    return pd.DataFrame({
        "partition": q.partition.astype(str),
        "zone": "18UTC_MATURE",
        "component": "REC_H2",
        "entry_ts": pd.to_datetime(q.recovery_entry_ts, utc=True),
        "exit_ts": pd.to_datetime(q.recovery_exit_ts, utc=True),
        "pnl": pd.to_numeric(q.recovery_pnl, errors="coerce"),
        "pnl_5bps": pd.to_numeric(q.recovery_pnl_5bps, errors="coerce"),
    })


def max_drawdown(q, col):
    if q.empty: return 0.0
    z = q.sort_values(["exit_ts", "entry_ts"]).copy()
    eq = pd.to_numeric(z[col], errors="coerce").fillna(0.0).cumsum()
    peak = eq.cummax().clip(lower=0.0)
    dd = peak - eq
    return float(dd.max()) if len(dd) else 0.0


def stats(q, partition):
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    years = partition_years(partition)
    exposure = float(((q.exit_ts - q.entry_ts) / pd.Timedelta(hours=1)).clip(lower=0).sum()) if len(q) else 0.0
    weeks = years * 365.2425 / 7.0
    net = float(p.sum())
    net5 = float(p5.sum())
    return {
        "n": len(q),
        "trades_per_week": len(q) / weeks if weeks > 0 else np.nan,
        "wr": float((p > 0).mean()) if len(q) else np.nan,
        "pf": pf(p),
        "expectancy": float(p.mean()) if len(q) else np.nan,
        "net": net,
        "wr_5bps": float((p5 > 0).mean()) if len(q) else np.nan,
        "pf_5bps": pf(p5),
        "expectancy_5bps": float(p5.mean()) if len(q) else np.nan,
        "net_5bps": net5,
        "max_drawdown": max_drawdown(q, "pnl"),
        "max_drawdown_5bps": max_drawdown(q, "pnl_5bps"),
        "annualized_net": net / years if years > 0 else np.nan,
        "annualized_net_5bps": net5 / years if years > 0 else np.nan,
        "exposure_hours": exposure,
        "net_per_exposure_hour": net / exposure if exposure > 0 else np.nan,
        "net_per_exposure_hour_5bps": net5 / exposure if exposure > 0 else np.nan,
    }


def overlap_rate(newq, matureq):
    if newq.empty: return np.nan
    intervals = [(pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)) for _, r in matureq.iterrows()]
    hit = 0
    for _, r in newq.iterrows():
        a, b = pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)
        if any(a <= mb and b >= ma for ma, mb in intervals):
            hit += 1
    return hit / len(newq)


def peak_concurrency(q):
    events = []
    for _, r in q.iterrows():
        a, b = pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)
        events.append((a, 1))
        events.append((b, -1))
    # exits before entries at identical timestamps
    events.sort(key=lambda x: (x[0], x[1]))
    cur = 0
    best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


def main():
    parent = a4.load_parent()
    parent = parent[parent.role == "CENTRAL"].copy()

    h2 = pd.read_csv(IN_H2)
    for c in ["recovery_entry_ts", "recovery_exit_ts"]:
        h2[c] = pd.to_datetime(h2[c], utc=True, errors="coerce")
    h2 = h2[(h2.role == "CENTRAL") & (pd.to_numeric(h2.visit_n, errors="coerce") == 2) & (h2.lane.astype(str) == "REC_H2")].copy()

    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)

    mature_parent = to_component_parent(parent, "18UTC_MATURE", "PARENT")
    mature_h2 = to_component_h2(h2)
    mature = pd.concat([mature_parent, mature_h2], ignore_index=True)

    new_parts = []
    for partition in ("development", "external", "reference_validation"):
        q = a2.trades_for(m, partition, NEW_REF, NEW_HOUR, "E0_RESTING_H", TARGET_R)
        new_parts.append(to_component_parent(q, "03UTC_EXPANSION", "PARENT"))
    new = pd.concat(new_parts, ignore_index=True)
    combined = pd.concat([mature, new], ignore_index=True)
    combined.to_csv(OUT_COMPONENTS, index=False)

    rows = []
    supported = True
    for partition in ("development", "external", "reference_validation"):
        mq = mature[mature.partition == partition].copy()
        nq = new[new.partition == partition].copy()
        cq = combined[combined.partition == partition].copy()
        ms = stats(mq, partition)
        ns = stats(nq, partition)
        cs = stats(cq, partition)
        ov = overlap_rate(nq, mq)
        pk = peak_concurrency(cq)
        pass_part = bool(
            cs["net"] > ms["net"]
            and cs["net_5bps"] > ms["net_5bps"]
            and cs["pf"] > 1.0
            and cs["pf_5bps"] > 1.0
            and ns["net"] > 0
            and ns["net_5bps"] > 0
        )
        supported = supported and pass_part
        rows.append({
            "partition": partition,
            **{f"mature_{k}": v for k, v in ms.items()},
            **{f"new_{k}": v for k, v in ns.items()},
            **{f"combined_{k}": v for k, v in cs.items()},
            "incremental_net": cs["net"] - ms["net"],
            "incremental_net_5bps": cs["net_5bps"] - ms["net_5bps"],
            "frequency_uplift": cs["trades_per_week"] / ms["trades_per_week"] - 1.0 if ms["trades_per_week"] else np.nan,
            "new_overlap_with_mature_rate": ov,
            "peak_concurrent_components": pk,
            "pass": pass_part,
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT_SUMMARY, index=False)

    status = "SOL_LONG_TWO_ZONE_A19_SUPPORTED_ADDITIVE_EXPANSION" if supported else "SOL_LONG_TWO_ZONE_A19_BENCHMARK_CAUTION"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG Two-Zone Operational Benchmark — A19 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "Frozen architecture: **18:00 UTC = A2 parent + A4 REC_H2; 03:00 UTC = A17 parent only**. A18 H2 transfer remains rejected.", "",
        "## Partition benchmark", "",
        "| Partition | Mature trades/wk | Mature PF | Mature Net | Mature 5bps PF | Mature 5bps Net | New 03 PF | New 03 Net | New 03 5bps PF | New 03 5bps Net | Combined trades/wk | Combined PF | Combined Net | Combined 5bps PF | Combined 5bps Net | Frequency uplift | New overlap | Peak conc. |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in out.iterrows():
        lines.append(
            f"| {r.partition} | {fmt(r.mature_trades_per_week)} | {fmt(r.mature_pf)} | ${fmt(r.mature_net)} | {fmt(r.mature_pf_5bps)} | ${fmt(r.mature_net_5bps)} | {fmt(r.new_pf)} | ${fmt(r.new_net)} | {fmt(r.new_pf_5bps)} | ${fmt(r.new_net_5bps)} | {fmt(r.combined_trades_per_week)} | {fmt(r.combined_pf)} | ${fmt(r.combined_net)} | {fmt(r.combined_pf_5bps)} | ${fmt(r.combined_net_5bps)} | {pct(r.frequency_uplift)} | {pct(r.new_overlap_with_mature_rate)} | {int(r.peak_concurrent_components)} |"
        )

    lines += ["", "## Drawdown / capital efficiency", "",
              "| Partition | Mature DD | Combined DD | Mature 5bps DD | Combined 5bps DD | Mature $/exposure-h | Combined $/exposure-h | Mature annual net | Combined annual net |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in out.iterrows():
        lines.append(
            f"| {r.partition} | ${fmt(r.mature_max_drawdown)} | ${fmt(r.combined_max_drawdown)} | ${fmt(r.mature_max_drawdown_5bps)} | ${fmt(r.combined_max_drawdown_5bps)} | ${fmt(r.mature_net_per_exposure_hour,3)} | ${fmt(r.combined_net_per_exposure_hour,3)} | ${fmt(r.mature_annualized_net)} | ${fmt(r.combined_annualized_net)} |"
        )

    lines += ["", "## Decision", "", f"**Status: {status}**", "",
              "A19 is an additive portfolio benchmark, not a live single-position scheduler. Reported overlap is diagnostic; no trade was altered using future overlap information.", "",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
