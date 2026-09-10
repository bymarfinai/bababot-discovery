#!/usr/bin/env python3
"""Technical-only G4 runner correction.

The preregistered candidate family, gates, ranking, and holdout rules remain unchanged.
This wrapper fixes pandas Series attribute collision for the column named `mode`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import eth_discovery2_reset_g4_entry_discovery as g4


def fixed_spec_from_row(r):
    if r["kind"] == "NEXT_OPEN":
        return {"label": "NEXT_OPEN", "kind": "NEXT_OPEN", "q": np.nan, "wait_min": 0}
    return {
        "label": str(r["mode"]),
        "kind": "LIMIT",
        "q": float(r["q"]),
        "wait_min": int(r["wait_min"]),
    }


g4.spec_from_row = fixed_spec_from_row


def main():
    g4.g1.base.synthetic_tests()
    x5, coverage = g4.g1.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    Cdev = g4.build_b00_cases(x5, "development")
    Pdev = g4.g3.build_parent_sessions(x5, "development")
    if len(Pdev) != 206:
        raise AssertionError(f"unexpected frozen G2 parent pressure count {len(Pdev)}")
    if len(Cdev) != 184:
        raise AssertionError(f"unexpected frozen G3 DIRECT B00 count {len(Cdev)}")

    D, audits = g4.dev_scan(x5, Cdev)
    D2, L = g4.build_leaderboard(D)
    D2.to_csv(g4.OUT_DEV, index=False)
    L.to_csv(g4.OUT_LEADER, index=False)

    lines = [
        "# ETH Discovery 2 Reset — G4 ETH-Native Entry Discovery Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen lineage: **LONG / 01:30 UTC / R180 / E720 / HIGH-side pressure → DIRECT B00**.",
        f"Development frozen B00 cases: **{len(Cdev)}**.",
        "G4 compares executable entry price × patience only. No TP/SL/PnL is tested.", "",
        "## Development entry atlas", "",
        "| Candidate | Fills | Part. | Entry excess R | Improve vs N/O | E10 | E20 | Eff E10 | Eff E20 | Wilson Eff E10 | Blocks | Neigh. | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in D2.itertuples(index=False):
        imp = "-" if pd.isna(r.median_entry_improvement_R) else f"{float(r.median_entry_improvement_R):+.3f}R"
        excess = "-" if pd.isna(r.median_entry_excess_R) else f"{float(r.median_entry_excess_R):.3f}"
        neigh = "-" if r.kind == "NEXT_OPEN" else f"{int(r.neighbors_supportive)}/{int(r.neighbors_available)}"
        lines.append(
            f"| {r.mode} | {int(r.fills)}/{int(r.b00_cases)} | {g4.pct(r.participation)} | {excess} | {imp} | "
            f"{g4.pct(r.e10_rate)} | {g4.pct(r.e20_rate)} | {g4.pct(r.effective_e10)} | {g4.pct(r.effective_e20)} | "
            f"{g4.pct(r.wilson_lb_effective_e10)} | {int(r.positive_blocks)}/4 | {neigh} | {'PASS' if bool(r.candidate_eligible) else 'FAIL'} |"
        )

    if len(L) == 0:
        status = "ETH_DISCOVERY2_RESET_G4_NO_DEV_CANDIDATE"
        g4.OUT_STATUS.write_text(status + "\n")
        lines += ["", "No candidate passed the preregistered Development entry + stability gates.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        g4.OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(g4.OUT_RESULT.read_text())
        return

    sel = L.iloc[0]
    selected_mode = str(sel["mode"])
    lines += [
        "", "## Development-selected entry", "",
        f"**{selected_mode}**",
        f"Fills **{int(sel['fills'])}/{int(sel['b00_cases'])} ({g4.pct(sel['participation'])})**; median entry excess **{float(sel['median_entry_excess_R']):.3f}R**; median improvement vs NEXT_OPEN **{float(sel['median_entry_improvement_R']):+.3f}R**.",
        f"Conditional E10 **{g4.pct(sel['e10_rate'])}**; E20 **{g4.pct(sel['e20_rate'])}**; effective E10 **{g4.pct(sel['effective_e10'])}**; effective E20 **{g4.pct(sel['effective_e20'])}**; Wilson effective E10 **{g4.pct(sel['wilson_lb_effective_e10'])}**.",
        f"Median B00→fill **{float(sel['median_b00_to_fill_min']):.0f}m**; median fill→E10 **{float(sel['median_fill_to_e10_min']):.0f}m**; positive blocks **{int(sel['positive_blocks'])}/4**.", "",
        "Development blocks:", "", "| Block | B00 N | Fill part. | Eff E10 | Eff E20 |", "|---:|---:|---:|---:|---:|"
    ]
    for b in range(1,5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {g4.pct(sel[f'block{b}_part'])} | {g4.pct(sel[f'block{b}_eff10'])} | {g4.pct(sel[f'block{b}_eff20'])} |")

    if bool(sel["upper_boundary"]):
        status = "ETH_DISCOVERY2_RESET_G4_ENTRY_BOUNDARY_OPEN"
        g4.OUT_STATUS.write_text(status + "\n")
        audits[selected_mode].to_csv(g4.OUT_AUDIT, index=False)
        lines += ["", "Selected resting-limit coordinate lies on the preregistered upper q/wait sentinel. Holdouts remain closed; no second-best substitution.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        g4.OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(g4.OUT_RESULT.read_text())
        return

    H, Ahold, supported = g4.holdout_scan(x5, sel)
    Adev = audits[selected_mode]
    H.to_csv(g4.OUT_OOS, index=False)
    pd.concat([Adev, Ahold], ignore_index=True).to_csv(g4.OUT_AUDIT, index=False)
    status = "ETH_DISCOVERY2_RESET_G4_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G4_CANDIDATE_NOT_REPLICATED"
    g4.OUT_STATUS.write_text(status + "\n")

    lines += ["", "## Historical replication", "", "| Partition | B00 | Fills | Part. | Improve | E10 | E20 | Eff E10 | Eff E20 | Wilson | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        imp = 0.0 if pd.isna(r.median_entry_improvement_R) else float(r.median_entry_improvement_R)
        lines.append(f"| {r.partition} | {int(r.b00_cases)} | {int(r.fills)} | {g4.pct(r.participation)} | {imp:+.3f}R | {g4.pct(r.e10_rate)} | {g4.pct(r.e20_rate)} | {g4.pct(r.effective_e10)} | {g4.pct(r.effective_e20)} | {g4.pct(r.wilson_lb_effective_e10)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")

    lines += ["", "## Development leaderboard", "", "| # | Candidate | Fills | Part. | Improve | Eff E10 | Eff E20 | Wilson | Boundary |", "|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in L.itertuples(index=False):
        imp = 0.0 if pd.isna(r.median_entry_improvement_R) else float(r.median_entry_improvement_R)
        lines.append(f"| {int(r.dev_rank)} | {r.mode} | {int(r.fills)} | {g4.pct(r.participation)} | {imp:+.3f}R | {g4.pct(r.effective_e10)} | {g4.pct(r.effective_e20)} | {g4.pct(r.wilson_lb_effective_e10)} | {'YES' if bool(r.upper_boundary) else 'NO'} |")

    lines += ["", f"**Status: {status}**", "", "G4 validates entry geometry only. Economics remain undiscovered on the reset lineage.", "Research/shadow only. No live promotion."]
    g4.OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(g4.OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
