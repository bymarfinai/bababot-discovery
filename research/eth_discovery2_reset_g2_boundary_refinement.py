#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_discovery2_reset_g1_geometry as g1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G2_BOUNDARY_REFINEMENT"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedSessionAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 90  # 01:30 UTC, frozen from supported G1
SIDE = "LONG"
REFS = tuple(range(60, 301, 30))
EXES = tuple(range(300, 781, 60))
G1_REF = 180
G1_EXE = 480


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def dev_scan(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ref_min in REFS:
        for exe_min in EXES:
            r = g1.analyze_geometry(x5, CLOCK, ref_min, exe_min, "development", False)[SIDE]
            rows.append(r)
    D = pd.DataFrame(rows)
    if len(D) != len(REFS) * len(EXES):
        raise AssertionError(f"expected {len(REFS)*len(EXES)} candidates, got {len(D)}")
    return D


def neighbor_keys(ref_min: int, exe_min: int):
    keys = []
    for rr in (ref_min - 30, ref_min + 30):
        if rr in REFS:
            keys.append((rr, exe_min))
    for ee in (exe_min - 60, exe_min + 60):
        if ee in EXES:
            keys.append((ref_min, ee))
    return keys


def build_leaderboard(D: pd.DataFrame):
    D = D.copy()
    D["dev_gate"] = (
        (D.signals >= 80) &
        (D.continuation_rate >= .75) &
        (D.resolved_same_side_rate >= .80) &
        (D.wilson_lb95 >= .65) &
        (D.positive_blocks >= 3)
    )

    lookup = {(int(r.reference_min), int(r.execution_min)): r for r in D.itertuples(index=False)}
    n_av, n_sup, stable = [], [], []
    for r in D.itertuples(index=False):
        keys = neighbor_keys(int(r.reference_min), int(r.execution_min))
        support = 0
        for k in keys:
            x = lookup[k]
            if int(x.signals) >= 60 and float(x.continuation_rate) >= .70 and float(x.resolved_same_side_rate) >= .77:
                support += 1
        nav = len(keys)
        need = max(2, math.ceil(.60 * nav))
        n_av.append(nav)
        n_sup.append(support)
        stable.append(support >= need)

    D["neighbors_available"] = n_av
    D["neighbors_supportive"] = n_sup
    D["local_stable"] = stable
    D["candidate_eligible"] = D.dev_gate & D.local_stable
    D["total_span_min"] = D.reference_min + D.execution_min
    D["outer_boundary"] = (
        D.reference_min.isin((min(REFS), max(REFS))) |
        D.execution_min.isin((min(EXES), max(EXES)))
    )

    C = D[D.candidate_eligible].copy()
    C = C.sort_values(
        ["wilson_lb95", "min_qualified_block_cont", "continuation_rate",
         "resolved_same_side_rate", "signals", "median_minutes_to_target",
         "total_span_min", "reference_min", "execution_min"],
        ascending=[False, False, False, False, False, True, True, True, True]
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return D, C


def holdout_scan(x5: pd.DataFrame, sel: pd.Series):
    rows, audits = [], []
    all_ok = True
    for part in ("external", "reference_validation"):
        r = g1.analyze_geometry(
            x5, CLOCK, int(sel.reference_min), int(sel.execution_min), part, False
        )[SIDE]
        ok = (
            int(r["signals"]) >= 40 and
            float(r["continuation_rate"]) >= .70 and
            float(r["resolved_same_side_rate"]) >= .78 and
            int(r["same_side"]) > int(r["opposite"]) and
            float(r["wilson_lb95"]) >= .58
        )
        r["replication_pass"] = bool(ok)
        rows.append(r)
        all_ok = all_ok and bool(ok)
        audits.append(g1.analyze_geometry(
            x5, CLOCK, int(sel.reference_min), int(sel.execution_min), part, True
        )[SIDE])

    audits.insert(1, g1.analyze_geometry(
        x5, CLOCK, int(sel.reference_min), int(sel.execution_min), "development", True
    )[SIDE])
    return pd.DataFrame(rows), pd.concat(audits, ignore_index=True), all_ok


def write_no_candidate(coverage: float):
    status = "ETH_DISCOVERY2_RESET_G2_NO_DEV_CANDIDATE"
    OUT_STATUS.write_text(status + "\n")
    lines = [
        "# ETH Discovery 2 Reset — G2 Boundary Refinement Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        f"Frozen side/clock: **{SIDE} / {g1.hhmm(CLOCK)} UTC ({g1.wib(CLOCK)} WIB)**.",
        f"Scanned **{len(REFS)} reference durations × {len(EXES)} execution horizons = {len(REFS)*len(EXES)}** Development candidates.", "",
        "No candidate passed the preregistered Development + local-duration-stability gates.", "",
        f"**Status: {status}**", "",
        "Research/shadow only. No live promotion."
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


def main():
    g1.base.synthetic_tests()
    x5, coverage = g1.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    D = dev_scan(x5)
    D2, C = build_leaderboard(D)
    D2.to_csv(OUT_DEV, index=False)
    C.to_csv(OUT_LEADER, index=False)

    if len(C) == 0:
        write_no_candidate(coverage)
        return

    sel = C.iloc[0]
    boundary = bool(sel.outer_boundary)
    parent = D2[(D2.reference_min == G1_REF) & (D2.execution_min == G1_EXE)].iloc[0]

    lines = [
        "# ETH Discovery 2 Reset — G2 Boundary Refinement Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        f"Frozen side/clock: **{SIDE} / {g1.hhmm(CLOCK)} UTC ({g1.wib(CLOCK)} WIB)**.",
        f"Scanned **{len(REFS)} reference durations × {len(EXES)} execution horizons = {len(REFS)*len(EXES)}** Development candidates.",
        "External and Reference Validation were not used for Development selection.", "",
        "## Development-selected duration geometry", "",
        f"**R{int(sel.reference_min)} / E{int(sel.execution_min)}**",
        f"Reference: {g1.hhmm(CLOCK)}–{g1.hhmm(CLOCK+int(sel.reference_min))} UTC ({g1.wib(CLOCK)}–{g1.wib(CLOCK+int(sel.reference_min))} WIB).",
        f"Execution: {g1.hhmm(CLOCK+int(sel.reference_min))}–{g1.hhmm(CLOCK+int(sel.reference_min)+int(sel.execution_min))} UTC ({g1.wib(CLOCK+int(sel.reference_min))}–{g1.wib(CLOCK+int(sel.reference_min)+int(sel.execution_min))} WIB).",
        f"Signals **{int(sel.signals)}**; continuation **{pct(sel.continuation_rate)}**; resolved same-side **{pct(sel.resolved_same_side_rate)}**; Wilson LB **{pct(sel.wilson_lb95)}**.",
        f"Median signal→continuation **{float(sel.median_minutes_to_target):.0f}m**; supportive neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; positive blocks **{int(sel.positive_blocks)}/4**.", "",
        "Development blocks:", "",
        "| Block | Signals | Continuation | Resolved |", "|---:|---:|---:|---:|"
    ]
    for b in range(1,5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {pct(sel[f'block{b}_cont'])} | {pct(sel[f'block{b}_resolved'])} |")

    lines += [
        "", "## G1 parent coordinate on the same Development data", "",
        "| Geometry | Signals | Continuation | Resolved | Wilson LB | Neighbors | Blocks |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| G1 R{G1_REF}/E{G1_EXE} | {int(parent.signals)} | {pct(parent.continuation_rate)} | {pct(parent.resolved_same_side_rate)} | {pct(parent.wilson_lb95)} | {int(parent.neighbors_supportive)}/{int(parent.neighbors_available)} | {int(parent.positive_blocks)}/4 |",
        f"| G2 selected R{int(sel.reference_min)}/E{int(sel.execution_min)} | {int(sel.signals)} | {pct(sel.continuation_rate)} | {pct(sel.resolved_same_side_rate)} | {pct(sel.wilson_lb95)} | {int(sel.neighbors_supportive)}/{int(sel.neighbors_available)} | {int(sel.positive_blocks)}/4 |", ""
    ]

    if boundary:
        status = "ETH_DISCOVERY2_RESET_G2_BOUNDARY_STILL_OPEN"
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "## Boundary decision", "",
            "The Development winner lies on an outer sentinel boundary. Per preregistration, duration geometry is **not localized** and historical holdouts are not opened to rescue it.", "",
            "## Top Development candidates", "",
            "| # | Ref m | Exe m | Signals | Cont. | Resolved | Wilson | Neigh. | Blocks | Boundary |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
        ]
        for _, r in C.head(20).iterrows():
            lines.append(f"| {int(r.dev_rank)} | {int(r.reference_min)} | {int(r.execution_min)} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 | {'YES' if bool(r.outer_boundary) else 'NO'} |")
        lines += ["", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    H, A, supported = holdout_scan(x5, sel)
    H.to_csv(OUT_OOS, index=False)
    A.to_csv(OUT_AUDIT, index=False)
    status = "ETH_DISCOVERY2_RESET_G2_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G2_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines += [
        "## Boundary decision", "",
        "The Development winner is strictly inside all sentinel boundaries, so the duration coordinate is localized for historical replication.", "",
        "## Historical replication", "",
        "| Partition | Signals | Continuation | Resolved | Wilson LB | Same/Opp | Gate |",
        "|---|---:|---:|---:|---:|---:|---|"
    ]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.same_side)}/{int(r.opposite)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")

    lines += [
        "", "## Top Development candidates", "",
        "| # | Ref m | Exe m | Signals | Cont. | Resolved | Wilson | Neigh. | Blocks | Boundary |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for _, r in C.head(20).iterrows():
        lines.append(f"| {int(r.dev_rank)} | {int(r.reference_min)} | {int(r.execution_min)} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 | {'YES' if bool(r.outer_boundary) else 'NO'} |")

    lines += [
        "", f"**Status: {status}**", "",
        "G2 freezes duration geometry only if SUPPORTED. Downstream structure and entry must still be rediscovered; old L06 remains historical comparison only.",
        "Research/shadow only. No live promotion."
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
