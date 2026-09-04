#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A19_PATH = Path(__file__).resolve().parent / "sol_long_two_zone_benchmark_a19.py"
spec = importlib.util.spec_from_file_location("sol_a19", A19_PATH)
a19 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a19)
a4 = a19.a4
a2 = a19.a2

IN_H2 = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_Result.md"
OUT_SUMMARY = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_SUMMARY.csv"
OUT_COMPONENTS = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv"
OUT_STATUS = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_Status.txt"

TARGET_R = 0.40
Z03 = (420, 3)
Z15 = (360, 15)


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def parent_components(m, cell, zone):
    out = []
    for partition in ("development", "external", "reference_validation"):
        q = a2.trades_for(m, partition, cell[0], cell[1], "E0_RESTING_H", TARGET_R)
        out.append(a19.to_component_parent(q, zone, "PARENT"))
    return pd.concat(out, ignore_index=True)


def overlap_rate(newq, baseq):
    return a19.overlap_rate(newq, baseq)


def main():
    parent = a4.load_parent()
    parent = parent[parent.role == "CENTRAL"].copy()

    h2 = pd.read_csv(IN_H2)
    for c in ["recovery_entry_ts", "recovery_exit_ts"]:
        h2[c] = pd.to_datetime(h2[c], utc=True, errors="coerce")
    h2 = h2[(h2.role == "CENTRAL") & (pd.to_numeric(h2.visit_n, errors="coerce") == 2) & (h2.lane.astype(str) == "REC_H2")].copy()

    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)

    z18 = pd.concat([
        a19.to_component_parent(parent, "18UTC_MATURE", "PARENT"),
        a19.to_component_h2(h2),
    ], ignore_index=True)
    z03 = parent_components(m, Z03, "03UTC_PARENT")
    z15 = parent_components(m, Z15, "15UTC_PARENT")
    two = pd.concat([z18, z03], ignore_index=True)
    three = pd.concat([z18, z03, z15], ignore_index=True)
    three.to_csv(OUT_COMPONENTS, index=False)

    rows = []
    supported = True
    for partition in ("development", "external", "reference_validation"):
        q18 = z18[z18.partition == partition].copy()
        q03 = z03[z03.partition == partition].copy()
        q15 = z15[z15.partition == partition].copy()
        q2 = two[two.partition == partition].copy()
        q3 = three[three.partition == partition].copy()
        s18 = a19.stats(q18, partition)
        s03 = a19.stats(q03, partition)
        s15 = a19.stats(q15, partition)
        s2 = a19.stats(q2, partition)
        s3 = a19.stats(q3, partition)
        ov15 = overlap_rate(q15, q2)
        peak = a19.peak_concurrency(q3)
        pass_part = bool(
            s15["net"] > 0 and s15["net_5bps"] > 0
            and s3["net"] > s2["net"] and s3["net_5bps"] > s2["net_5bps"]
            and s3["pf"] > 1.0 and s3["pf_5bps"] > 1.0
        )
        supported = supported and pass_part
        rows.append({
            "partition": partition,
            **{f"z18_{k}": v for k, v in s18.items()},
            **{f"z03_{k}": v for k, v in s03.items()},
            **{f"z15_{k}": v for k, v in s15.items()},
            **{f"two_{k}": v for k, v in s2.items()},
            **{f"three_{k}": v for k, v in s3.items()},
            "incremental_15_net": s3["net"] - s2["net"],
            "incremental_15_net_5bps": s3["net_5bps"] - s2["net_5bps"],
            "frequency_uplift_vs_two": s3["trades_per_week"] / s2["trades_per_week"] - 1.0 if s2["trades_per_week"] else np.nan,
            "frequency_uplift_vs_18": s3["trades_per_week"] / s18["trades_per_week"] - 1.0 if s18["trades_per_week"] else np.nan,
            "z15_overlap_with_two_zone": ov15,
            "peak_concurrent_components": peak,
            "pass": pass_part,
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT_SUMMARY, index=False)

    status = "SOL_LONG_THREE_ZONE_A24_SUPPORTED_ADDITIVE_EXPANSION" if supported else "SOL_LONG_THREE_ZONE_A24_BENCHMARK_CAUTION"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG Three-Zone Portfolio Benchmark — A24 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "Frozen architecture: **03:00/R420 parent-only + 15:00/R360 parent-only + 18:00/R240 parent + REC_H2**. A18 and A23 recovery transfers remain rejected.", "",
        "## Partition benchmark", "",
        "| Partition | 18 PF | 18 Net | 03 PF | 03 Net | 15 PF | 15 Net | Two-zone PF | Two-zone Net | Three-zone trades/wk | Three-zone PF | Three-zone Net | Three-zone 5bps PF | Three-zone 5bps Net | +15 net raw/stress | Freq uplift vs two | Freq uplift vs 18 | 15 overlap | Peak conc. |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for _, r in out.iterrows():
        lines.append(
            f"| {r.partition} | {fmt(r.z18_pf)} | ${fmt(r.z18_net)} | {fmt(r.z03_pf)} | ${fmt(r.z03_net)} | {fmt(r.z15_pf)} | ${fmt(r.z15_net)} | {fmt(r.two_pf)} | ${fmt(r.two_net)} | {fmt(r.three_trades_per_week)} | {fmt(r.three_pf)} | ${fmt(r.three_net)} | {fmt(r.three_pf_5bps)} | ${fmt(r.three_net_5bps)} | ${fmt(r.incremental_15_net)}/${fmt(r.incremental_15_net_5bps)} | {pct(r.frequency_uplift_vs_two)} | {pct(r.frequency_uplift_vs_18)} | {pct(r.z15_overlap_with_two_zone)} | {int(r.peak_concurrent_components)} |"
        )

    lines += ["", "## Drawdown / capital efficiency", "",
              "| Partition | Two-zone DD | Three-zone DD | Two-zone 5bps DD | Three-zone 5bps DD | Two-zone $/exposure-h | Three-zone $/exposure-h | Two-zone annual net | Three-zone annual net |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in out.iterrows():
        lines.append(
            f"| {r.partition} | ${fmt(r.two_max_drawdown)} | ${fmt(r.three_max_drawdown)} | ${fmt(r.two_max_drawdown_5bps)} | ${fmt(r.three_max_drawdown_5bps)} | ${fmt(r.two_net_per_exposure_hour,3)} | ${fmt(r.three_net_per_exposure_hour,3)} | ${fmt(r.two_annualized_net)} | ${fmt(r.three_annualized_net)} |"
        )

    lines += ["", "## Decision", "", f"**Status: {status}**", "",
              "A24 is an additive portfolio audit, not a live concurrency scheduler. Overlap is diagnostic and no trade is altered using future information.", "",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
