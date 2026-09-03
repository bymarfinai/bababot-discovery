#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_EVENTS = ROOT / "SOL_LONG_VISIT_BREAK_A1_EVENTS.csv"
OUT_MD = ROOT / "SOL_LONG_FIRST_BREAK_A1B_Result.md"
OUT_SUMMARY = ROOT / "SOL_LONG_FIRST_BREAK_A1B_SUMMARY.csv"
OUT_STATUS = ROOT / "SOL_LONG_FIRST_BREAK_A1B_Status.txt"
VISITS = (1, 2, 3, 4, 5)
ROLES = ("CENTRAL", "CLOCK_SUPPORT", "REF_SUPPORT")
PARTS = ("development", "external", "reference_validation")


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def num(v):
    return "-" if pd.isna(v) else f"{float(v):.3f}R"


def main():
    e = pd.read_csv(IN_EVENTS)
    e["first_break_visit"] = pd.to_numeric(e.first_break_visit, errors="coerce").fillna(0).astype(int)
    e["visits_reached"] = pd.to_numeric(e.visits_reached, errors="coerce").fillna(0).astype(int)
    rows = []
    combo_rows = []

    for role in ROLES:
        for part in PARTS:
            q = e[(e.role == role) & (e.partition == part)].copy()
            h1_opp = int((q.visits_reached >= 1).sum())
            total_breaks = int(q.first_break_visit.isin(VISITS).sum())
            local = []
            for j in VISITS:
                opp = int((q.visits_reached >= j).sum())
                b = q[q.first_break_visit == j]
                n = len(b)
                share = n / total_breaks if total_breaks else np.nan
                incidence = n / h1_opp if h1_opp else np.nan
                conditional = n / opp if opp else np.nan
                medext = float(b.extension_before_reclaim_R.median()) if n else np.nan
                r = {
                    "role": role,
                    "partition": part,
                    "visit": j,
                    "sessions_n": len(q),
                    "h1_opportunity_n": h1_opp,
                    "visit_opportunity_n": opp,
                    "first_break_total_n": total_breaks,
                    "first_break_n": n,
                    "first_break_share": share,
                    "session_incidence": incidence,
                    "conditional_conversion": conditional,
                    "median_extension_R": medext,
                }
                rows.append(r)
                local.append(r)
            valid = [r for r in local if pd.notna(r["first_break_share"])]
            modal = sorted(valid, key=lambda r: (-r["first_break_share"], r["visit"]))[0]["visit"] if valid else 0
            combo_rows.append({
                "role": role,
                "partition": part,
                "modal_visit": modal,
                "sessions_n": len(q),
                "first_break_total_n": total_breaks,
            })

    s = pd.DataFrame(rows)
    combos = pd.DataFrame(combo_rows)
    s.to_csv(OUT_SUMMARY, index=False)

    modal_values = combos.modal_visit.tolist()
    supported = len(combos) == 9 and all(v == modal_values[0] and v > 0 for v in modal_values)
    modal = int(modal_values[0]) if supported else 0
    status = f"SOL_LONG_FIRST_BREAK_A1B_H{modal}_MODAL_SUPPORTED" if supported else "SOL_LONG_FIRST_BREAK_A1B_VISIT_ORDER_UNSTABLE"

    lines = [
        "# SOL LONG First-Break Visit Audit — A1B Result",
        "",
        "A1B does not search parameters. It re-expresses the frozen A1 selected events using the denominator that directly answers: **where does the first completed-close upside breakout happen most often?**",
        "",
        "## Modal first-break visit by frozen topology role and partition",
        "",
        "| Role | Partition | Sessions | First breaks H1-H5 | Modal visit |",
        "|---|---|---:|---:|---:|",
    ]
    for _, r in combos.iterrows():
        lines.append(f"| {r.role} | {r.partition} | {int(r.sessions_n)} | {int(r.first_break_total_n)} | H{int(r.modal_visit) if int(r.modal_visit) else '-'} |")

    for role in ROLES:
        lines += ["", f"## {role} first-break distribution", "", "| Partition | H1 | H2 | H3 | H4 | H5 |", "|---|---:|---:|---:|---:|---:|"]
        for part in PARTS:
            q = s[(s.role == role) & (s.partition == part)].sort_values("visit")
            vals = [pct(x) for x in q.first_break_share.tolist()]
            lines.append(f"| {part} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} | {vals[4]} |")

    central_dev = s[(s.role == "CENTRAL") & (s.partition == "development")].sort_values("visit")
    lines += [
        "",
        "## Central Development funnel and anatomy",
        "",
        "| Visit | Opportunity N | First-break N | Share of first breaks | Conditional conversion | Median extension |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in central_dev.iterrows():
        lines.append(
            f"| H{int(r.visit)} | {int(r.visit_opportunity_n)} | {int(r.first_break_n)} | {pct(r.first_break_share)} | {pct(r.conditional_conversion)} | {num(r.median_extension_R)} |"
        )

    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if supported:
        lines += [
            f"Across all **9/9 frozen role × partition combinations**, the modal first upside breakout occurs at **H{modal}**.",
            "",
            f"Therefore the A1 Development selection of H2 was a conditional-survivor effect, not evidence that most SOL LONG breakouts begin at H2. The correct structural statement from the frozen A1 topology is: **the first completed-close breakout is most often an H{modal} event**.",
            "",
            "This still does not define the entry. The next experiment may study whether entry should occur before that visit, on the breakout confirmation, or on a post-break retest.",
        ]
    else:
        lines += [
            "The modal first-break visit is not invariant across all frozen role × partition combinations. Entry research remains blocked because visit order itself is unstable.",
        ]
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(status + "\n")


if __name__ == "__main__":
    main()
