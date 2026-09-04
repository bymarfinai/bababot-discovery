#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A17_PATH = Path(__file__).resolve().parent / "sol_long_multi_clock_expansion_a17.py"
spec = importlib.util.spec_from_file_location("sol_a17", A17_PATH)
a17 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a17)

a2 = a17.a2
IN_ATLAS = ROOT / "SOL_LONG_VISIT_BREAK_A1_ATLAS.csv"
OUT_MD = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_Result.md"
OUT_DEV = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_TRADES.csv"
OUT_CELLS = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_CELLS.csv"
OUT_STATUS = ROOT / "SOL_LONG_ADDITIONAL_CLOCKS_A20_Status.txt"

SUPPORTED_CLOCKS = (18, 3)
ALREADY_TESTED_HOURS = {18, 3, 8, 13}
MAX_CANDIDATES = 4


def distance_to_supported(h: int) -> int:
    return min(a17.clock_distance(h, s) for s in SUPPORTED_CLOCKS)


def derive_cells(atlas: pd.DataFrame) -> pd.DataFrame:
    q = atlas[
        (pd.to_numeric(atlas.dominant_visit, errors="coerce") == 2)
        & atlas.topology_supported.astype(bool)
        & (pd.to_numeric(atlas.same_dom_blocks, errors="coerce") >= 4)
        & (pd.to_numeric(atlas.dominant_opportunity_n, errors="coerce") >= 100)
    ].copy()
    q["distance_to_supported"] = q.hour.astype(int).map(distance_to_supported)
    q = q[(q.distance_to_supported > 2) & (~q.hour.astype(int).isin(ALREADY_TESTED_HOURS))].copy()
    q = a17.rank_cells(q)

    chosen = []
    for _, r in q.iterrows():
        h = int(r.hour)
        if any(a17.clock_distance(h, int(x.hour)) <= 2 for x in chosen):
            continue
        chosen.append(r)
        if len(chosen) >= MAX_CANDIDATES:
            break
    if not chosen:
        raise RuntimeError("A20 atlas derivation produced no untouched candidate clocks")

    rows = []
    for rank_i, r in enumerate(chosen, start=1):
        ref, hour, dom = int(r.ref_min), int(r.hour), int(r.dominant_visit)
        chours = a17.parse_int_list(r.clock_support_hours)
        cq = atlas[(atlas.ref_min.astype(int) == ref) & atlas.hour.astype(int).isin(chours) & (atlas.dominant_visit.astype(int) == dom)].copy()
        if cq.empty:
            raise RuntimeError(f"No clock support for R{ref}/{hour:02d}")
        crow = a17.rank_cells(cq).iloc[0]
        rmins = a17.parse_int_list(r.ref_support_mins)
        rq = atlas[(atlas.hour.astype(int) == hour) & atlas.ref_min.astype(int).isin(rmins) & (atlas.dominant_visit.astype(int) == dom)].copy()
        if rq.empty:
            raise RuntimeError(f"No reference support for R{ref}/{hour:02d}")
        rrow = a17.rank_cells(rq).iloc[0]
        rows.append({
            "candidate": f"A20_Z{rank_i}_R{ref}_H{hour:02d}",
            "anatomy_rank": rank_i,
            "ref_min": ref,
            "hour": hour,
            "distance_to_supported": distance_to_supported(hour),
            "dominant_visit": dom,
            "same_dom_blocks": int(r.same_dom_blocks),
            "dominant_opportunity_n": int(r.dominant_opportunity_n),
            "dominant_break_conversion": float(r.dominant_break_conversion),
            "dominant_median_extension_R": float(r.dominant_median_extension_R),
            "clock_support_ref_min": int(crow.ref_min),
            "clock_support_hour": int(crow.hour),
            "ref_support_ref_min": int(rrow.ref_min),
            "ref_support_hour": int(rrow.hour),
        })
    return pd.DataFrame(rows)


def existing_windows(m):
    mature_parent, mature_h2, windows = a17.load_mature_windows()
    for part in ("development", "external", "reference_validation"):
        q03 = a17.simulate_cell(m, part, 420, 3, "A17_R420_H03", "EXISTING_03")
        for _, r in q03.iterrows():
            windows.append((part, pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)))
    return mature_parent, mature_h2, windows


def dev_summary(q, c, mature_parent, mature_h2, windows):
    row = a17.dev_row(q, c.candidate, mature_parent, mature_h2, windows)
    row["anatomy_rank"] = int(c.anatomy_rank)
    row["ref_min"] = int(c.ref_min)
    row["hour"] = int(c.hour)
    row["existing_two_zone_overlap_rate"] = a17.overlap_rate(q, "development", windows)
    return row


def write_result(cells, dev, oos, winner, coverage, status):
    lines = [
        "# SOL LONG Additional Untouched Clocks — A20 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "A20 continues Stage 12 using only untouched clock candidates derived from the old A1 anatomy atlas. Supported 18:00 and 03:00 clusters remain frozen; A17-tested 08:00 and 13:00 are not retuned.", "",
        "## Frozen untouched candidates", "",
        "| Candidate | Ref | Clock UTC | Distance to supported clock | Stable blocks | Break conversion | Median extension | Clock support | Ref support |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in cells.iterrows():
        lines.append(f"| {r.candidate} | {int(r.ref_min)}m | {int(r.hour):02d}:00 | {int(r.distance_to_supported)}h | {int(r.same_dom_blocks)}/6 | {a17.pct(r.dominant_break_conversion)} | {a17.fmt(r.dominant_median_extension_R,3)}R | R{int(r.clock_support_ref_min)}/{int(r.clock_support_hour):02d} | R{int(r.ref_support_ref_min)}/{int(r.ref_support_hour):02d} |")

    lines += ["", "## Central Development economics", "",
              "| Candidate | N | Trades/wk | WR | PF | Net | 5bps PF | 5bps Net | +blocks raw/stress | Existing-portfolio overlap | Pass |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    for _, r in dev.iterrows():
        lines.append(f"| {r.candidate} | {int(r.n)} | {a17.fmt(r.trades_per_week,2)} | {a17.pct(r.wr)} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {a17.pct(r.existing_two_zone_overlap_rate)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["", f"Frozen Development winner: **{winner.candidate if winner is not None else 'NONE'}**.", ""]

    if winner is not None and len(oos):
        lines += ["## Frozen OOS", "",
                  "| Role | Partition | Cell | N | WR | PF | Net | 5bps PF | 5bps Net |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|"]
        for _, r in oos.iterrows():
            lines.append(f"| {r.role} | {r.partition} | R{int(r.ref_min)}/{int(r.hour):02d} | {int(r.n)} | {a17.pct(r.wr)} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} |")
        exact = oos[oos.role == "CANDIDATE"]
        support = oos[oos.role != "CANDIDATE"]
        central_ok = bool(len(exact) == 2 and (exact.net > 0).all() and (exact.net_5bps > 0).all() and (exact.pf > 1).all() and (exact.pf_5bps > 1).all())
        lines += ["", f"Validation: **central_ok={central_ok}; support positive raw={int((support.net>0).sum())}/4; support positive 5bps={int((support.net_5bps>0).sum())}/4**.", ""]

    lines += ["## Decision", "", f"**Status: {status}**", "",
              "A20 promotes only a supported parent habitat. Recovery is not inherited; any recovery transfer requires a separate preregistered test.", "",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    atlas = pd.read_csv(IN_ATLAS)
    cells = derive_cells(atlas)
    cells.to_csv(OUT_CELLS, index=False)

    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)
    mature_parent, mature_h2, windows = existing_windows(m)

    dev_rows, all_trades = [], []
    for _, c in cells.iterrows():
        q = a17.simulate_cell(m, "development", c.ref_min, c.hour, c.candidate, "CANDIDATE")
        all_trades.append(q)
        dev_rows.append(dev_summary(q, c, mature_parent, mature_h2, windows))
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV, index=False)
    winner = a17.choose_winner(dev)

    oos_rows = []
    if winner is not None:
        c = cells[cells.candidate == winner.candidate].iloc[0]
        tests = [
            ("CANDIDATE", int(c.ref_min), int(c.hour)),
            ("CLOCK_SUPPORT", int(c.clock_support_ref_min), int(c.clock_support_hour)),
            ("REF_SUPPORT", int(c.ref_support_ref_min), int(c.ref_support_hour)),
        ]
        for role, ref, hour in tests:
            for part in ("external", "reference_validation"):
                q = a17.simulate_cell(m, part, ref, hour, c.candidate, role)
                all_trades.append(q)
                oos_rows.append({"candidate": c.candidate, "role": role, "partition": part, "ref_min": ref, "hour": hour, **a17.stats(q, part)})
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)

    if winner is None:
        status = "SOL_LONG_ADDITIONAL_CLOCKS_A20_REJECTED_DEVELOPMENT"
    else:
        exact = oos[oos.role == "CANDIDATE"]
        support = oos[oos.role != "CANDIDATE"]
        central_ok = bool(len(exact) == 2 and (exact.net > 0).all() and (exact.net_5bps > 0).all() and (exact.pf > 1).all() and (exact.pf_5bps > 1).all())
        support_raw = int((support.net > 0).sum())
        support_stress = int((support.net_5bps > 0).sum())
        status = "SOL_LONG_ADDITIONAL_CLOCKS_A20_SUPPORTED" if central_ok and support_raw >= 3 and support_stress >= 3 else "SOL_LONG_ADDITIONAL_CLOCKS_A20_REJECTED_OOS"

    trades = pd.concat([q for q in all_trades if q is not None and len(q)], ignore_index=True) if any(q is not None and len(q) for q in all_trades) else pd.DataFrame()
    trades.to_csv(OUT_TRADES, index=False)
    write_result(cells, dev, oos, winner, coverage, status)
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
