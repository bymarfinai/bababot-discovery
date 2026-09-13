#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_orb_structure_detector_v1 as detector

ROOT = Path(__file__).resolve().parent.parent
OUT_EVENTS = ROOT / "SOL_ORB_STRUCTURE_DETECTOR_V1_DevelopmentEvents.csv"
OUT_SUMMARY = ROOT / "SOL_ORB_STRUCTURE_DETECTOR_V1_DevelopmentSummary.csv"
OUT_RESULT = ROOT / "SOL_ORB_STRUCTURE_DETECTOR_V1_Result.md"
OUT_STATUS = ROOT / "SOL_ORB_STRUCTURE_DETECTOR_V1_Status.txt"

DEV_START, DEV_END = base.PARTS["development"]
HOUR = 23


def main() -> None:
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"SOLUSDT 5m coverage too low: {coverage:.6%}")

    # Keep the inherited economic-first Development universe: weekdays only,
    # 2022-01-01 <= timestamp < 2025-01-01. OOS/reference data remains closed.
    q = x5[(x5.index >= DEV_START) & (x5.index < DEV_END)].copy()
    q = q[q.index.weekday < 5]
    q = q[q.index.hour == HOUR].copy()
    q = q.reset_index().rename(columns={q.index.name or "index": "timestamp"})
    if "ts" in q.columns and "timestamp" not in q.columns:
        q = q.rename(columns={"ts": "timestamp"})
    if "timestamp" not in q.columns:
        q = q.rename(columns={q.columns[0]: "timestamp"})

    rows = []
    for _, g in q.groupby(q.timestamp.dt.date):
        d = detector.detect_session(g)
        if d is not None:
            rows.append(detector.asdict(d))
    events = pd.DataFrame(rows)
    if events.empty:
        raise RuntimeError("no detector events produced")

    events.to_csv(OUT_EVENTS, index=False)
    summary = (
        events.groupby(["structure", "signal"], dropna=False)
        .size().reset_index(name="sessions")
        .sort_values(["sessions", "structure"], ascending=[False, True])
    )
    total = len(events)
    summary["share"] = summary.sessions / total
    summary.to_csv(OUT_SUMMARY, index=False)

    long_n = int((events.signal == "LONG").sum())
    breakout_n = int(events.breakout_time.notna().sum())
    retest_n = int(events.retest_time.notna().sum())
    accept_n = int(events.acceptance_time.notna().sum())

    lines = [
        "# SOL ORB Structure Detector v1 — Development Result",
        "",
        f"- Data coverage: {coverage:.6%}",
        f"- Universe: weekdays, Development only ({DEV_START} to {DEV_END}), H23 UTC",
        f"- Sessions classified: **{total}**",
        f"- Any upside breakout: **{breakout_n} ({breakout_n/total:.2%})**",
        f"- Retest observed: **{retest_n} ({retest_n/total:.2%})**",
        f"- Acceptance observed: **{accept_n} ({accept_n/total:.2%})**",
        f"- Full BREAK -> RETEST -> ACCEPT LONG signals: **{long_n} ({long_n/total:.2%})**",
        "",
        "## Structure prevalence",
        "",
        "| Structure | Signal | Sessions | Share |",
        "|---|---|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(f"| {r.structure} | {r.signal} | {r.sessions} | {r.share:.2%} |")
    lines += [
        "",
        "## Boundary",
        "",
        "This result measures structural prevalence only. It does not establish profitability,",
        "does not optimize TP/SL, and does not open Reference Validation/OOS.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("COMPLETE_DEVELOPMENT_STRUCTURE_PREVALENCE_ONLY\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
