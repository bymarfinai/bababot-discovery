#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "audit_parts"
OUT_SUMMARY = ROOT / "SOL_ECONOMIC_FIRST_DD15_24H_AUDIT.csv"
OUT_PASSERS = ROOT / "SOL_ECONOMIC_FIRST_DD15_PASSERS.csv"
OUT_REPORT = ROOT / "SOL_ECONOMIC_FIRST_DD15_24H_AUDIT.md"


def pct(x: float) -> str:
    return f"{100 * float(x):.2f}%"


def money(x: float) -> str:
    return f"${float(x):+,.2f}"


def main() -> None:
    summaries = pd.concat([pd.read_csv(p) for p in sorted(PARTS.glob("H*_summary.csv"))], ignore_index=True)
    if len(summaries) != 24 or int(summaries.candidate_count.sum()) != 77_760:
        raise AssertionError(f"incomplete audit: hours={len(summaries)} candidates={summaries.candidate_count.sum()}")
    summaries = summaries.sort_values("hour").reset_index(drop=True)
    passer_files = sorted(PARTS.glob("H*_passers.csv"))
    passers = []
    for p in passer_files:
        frame = pd.read_csv(p)
        if len(frame):
            frame.insert(0, "hour", int(p.name[1:3]))
            passers.append(frame)
    all_passers = pd.concat(passers, ignore_index=True) if passers else pd.DataFrame()
    summaries.to_csv(OUT_SUMMARY, index=False)
    all_passers.to_csv(OUT_PASSERS, index=False)

    lines = [
        "# SOL Economic-First — DD15 Full-Gate 24-Hour Audit",
        "",
        "## Frozen interpretation",
        "",
        "This is a re-score of the same 77,760 Development candidates, not a new discovery search.",
        "The only pooled-gate change is `max DD / net profit <= 15%`; the former pooled `max DD <= $125` test is removed.",
        "Anchor support remains under its original gate, including anchor DD <= $125. All sample, expectancy, PF, loss-streak, and 2022/2023/2024 gates remain unchanged. Pooled WR is evaluated strictly as >55%.",
        "",
        "## Hour audit",
        "",
        "| H | UTC | WIB | Old | New | Rescued | Lost | Status / exact leading fail |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for r in summaries.itertuples(index=False):
        reason = "PASS" if r.status == "PASS" else f"FAIL — {r.best_fail_reasons}"
        lines.append(f"| H{int(r.hour):02d} | {r.utc} | {r.wib} | {int(r.old_passers)} | {int(r.new_passers)} | {int(r.rescued_passers)} | {int(r.lost_passers)} | {reason} |")

    original = all_passers[all_passers.old_candidate_gate] if len(all_passers) else all_passers
    rescued = all_passers[all_passers.rescued] if len(all_passers) else all_passers
    lost_total = int(summaries.lost_passers.sum())
    lines += [
        "",
        "## Final full-pass shortlist",
        "",
        "| H | Character | LB | Hold | N | WR | Net | Exp | PF | DD | DD/Net | L-streak | Anchors | Origin |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    if len(all_passers):
        for r in all_passers.sort_values(["hour", "new_rank"]).itertuples(index=False):
            origin = "RESCUED" if r.rescued else "ORIGINAL"
            lines.append(
                f"| H{int(r.hour):02d} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | "
                f"{int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | "
                f"{r.pf:.3f} | {money(r.max_dd)} | {pct(r.dd_ratio)} | {int(r.max_loss_streak)} | "
                f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {origin} |"
            )
    else:
        lines.append("| — | No candidate passed | — | — | — | — | — | — | — | — | — | — | — | — |")

    lines += [
        "",
        "## Status changes",
        "",
        f"- Original passers retained: **{len(original)}** candidate variants.",
        f"- NO PASS -> PASS rescued variants: **{len(rescued)}**.",
        f"- PASS -> FAIL under proportional DD: **{lost_total}**.",
        f"- Full-pass hours after re-score: **{int((summaries.new_passers > 0).sum())}/24**.",
        "",
        "No OOS, exact-anchor/local-ridge, TP/SL fitting, or live promotion was opened by this audit.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n")
    print(OUT_REPORT.read_text())


if __name__ == "__main__":
    main()
