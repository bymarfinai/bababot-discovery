#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "SOL_R4C_24H_ETHSTYLE_LONG_CHARACTER_SUMMARY.csv"
OUT_PASS = ROOT / "SOL_R4C_24H_ETHSTYLE_LONG_CHARACTER_PASSERS.csv"
OUT_MD = ROOT / "SOL_R4C_24H_ETHSTYLE_LONG_CHARACTER_SUMMARY.md"
OUT_STATUS = ROOT / "SOL_R4C_24H_ETHSTYLE_LONG_CHARACTER_Status.txt"

RANK_COLS = ["candidate_gate", "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf"]
RANK_ASC = [False, False, False, False, False, False]


def truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


def fmt_pct(v):
    return "n/a" if pd.isna(v) else f"{100*float(v):.2f}%"


def fmt_money(v):
    return "n/a" if pd.isna(v) else f"${float(v):+,.2f}"


def fmt_num(v, n=3):
    return "n/a" if pd.isna(v) else f"{float(v):.{n}f}"


def main() -> None:
    rows = []
    for h in range(24):
        pfx = f"SOL_R4C_H{h:02d}_ETHSTYLE_LONG_CHARACTER"
        grid_path = ROOT / f"{pfx}_DevelopmentGrid.csv"
        leader_path = ROOT / f"{pfx}_DevelopmentLeaderboard.csv"
        status_path = ROOT / f"{pfx}_Status.txt"
        if not grid_path.exists() or not status_path.exists():
            raise FileNotFoundError(f"missing authoritative hourly output for H{h:02d}")

        D = pd.read_csv(grid_path)
        if len(D) != 3240:
            raise AssertionError(f"H{h:02d}: expected 3240 cells, got {len(D)}")
        status = status_path.read_text().strip()
        C = pd.read_csv(leader_path) if leader_path.exists() and leader_path.stat().st_size > 0 else pd.DataFrame()

        # Reproduce the exact frozen hourly ranking used by the discovery runner.
        sortD = D.copy()
        sortD["candidate_gate"] = sortD["candidate_gate"].map(truthy)
        best = sortD.sort_values(RANK_COLS, ascending=RANK_ASC).iloc[0]
        passers = sortD[sortD.candidate_gate].copy()

        official_pass = status.endswith("_LONG_CHARACTER_FOUND")
        if official_pass != (len(passers) > 0):
            raise AssertionError(f"H{h:02d}: status/passers mismatch: {status} vs {len(passers)}")

        # For passing hours, selected row is the first full-gate passer under the same ranking.
        selected = passers.sort_values(RANK_COLS, ascending=RANK_ASC).iloc[0] if official_pass else best
        rows.append({
            "hour_wib": h,
            "window_wib": f"{h:02d}:00-{(h+1)%24:02d}:00",
            "status": status,
            "official_pass": official_pass,
            "full_gate_passers": int(len(passers)),
            "row_role": "SELECTED_PASSER" if official_pass else "BEST_NEAR_MISS",
            "character_rule": selected["character_rule"],
            "lookback_min": int(selected["lookback_min"]),
            "hold_min": int(selected["hold_min"]),
            "trades": int(selected["trades"]),
            "win_rate": float(selected["win_rate"]),
            "net_pnl": float(selected["net_pnl"]),
            "expectancy": float(selected["expectancy"]),
            "pf": float(selected["pf"]),
            "max_dd": float(selected["max_dd"]),
            "max_loss_streak": int(selected["max_loss_streak"]),
            "supportive_anchors": int(selected["supportive_anchors"]),
            "evaluable_anchors": int(selected["evaluable_anchors"]),
            "min_year_exp": float(selected["min_year_exp"]),
            "y2022_trades": int(selected["y2022_trades"]),
            "y2022_wr": float(selected["y2022_wr"]),
            "y2022_exp": float(selected["y2022_exp"]),
            "y2022_pf": float(selected["y2022_pf"]),
            "y2023_trades": int(selected["y2023_trades"]),
            "y2023_wr": float(selected["y2023_wr"]),
            "y2023_exp": float(selected["y2023_exp"]),
            "y2023_pf": float(selected["y2023_pf"]),
            "y2024_trades": int(selected["y2024_trades"]),
            "y2024_wr": float(selected["y2024_wr"]),
            "y2024_exp": float(selected["y2024_exp"]),
            "y2024_pf": float(selected["y2024_pf"]),
        })

    S = pd.DataFrame(rows).sort_values("hour_wib").reset_index(drop=True)
    S.to_csv(OUT_CSV, index=False)
    P = S[S.official_pass].copy()
    P.to_csv(OUT_PASS, index=False)

    lines = [
        "# SOL R4c — 24-Hour ETH-Style LONG Character Summary", "",
        "This is the authoritative roll-up of H00–H23. Every hour used the same frozen 90-rule × 6-lookback × 6-hold grammar (3,240 candidates/hour), the same quarter-hour anchor gates, and the same 2022/2023/2024 development-era consistency gates. No hourly result changed the method used by another hour.", "",
        f"- Hours tested: **24/24**",
        f"- Candidates evaluated: **{24*3240:,}**",
        f"- Official PASS hours: **{len(P)}**",
        f"- Official NO-PASS hours: **{24-len(P)}**", "",
        "## Hour-by-hour verdict", "",
        "| WIB window | Verdict | Passers | Role | Character | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Anchors |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.window_wib} | {'PASS' if r.official_pass else 'NO PASS'} | {r.full_gate_passers} | {r.row_role} | `{r.character_rule}` | "
            f"{r.lookback_min}m | {r.hold_min}m | {r.trades} | {fmt_pct(r.win_rate)} | {fmt_money(r.net_pnl)} | "
            f"{fmt_money(r.expectancy)} | {fmt_num(r.pf)} | {fmt_money(r.max_dd)} | {r.max_loss_streak} | "
            f"{r.supportive_anchors}/{r.evaluable_anchors} |"
        )

    lines += ["", "## Official PASS set", ""]
    if P.empty:
        lines += ["**No hour passed the full frozen gate.**"]
        overall = "SOL_R4C_24H_NO_FULL_GATE_PASSERS"
    else:
        for r in P.itertuples(index=False):
            lines.append(
                f"- **H{r.hour_wib:02d} / {r.window_wib} WIB** — `{r.character_rule}` / LB{r.lookback_min} / hold{r.hold_min}m; "
                f"N {r.trades}, WR {fmt_pct(r.win_rate)}, net {fmt_money(r.net_pnl)}, exp {fmt_money(r.expectancy)}/trade, "
                f"PF {fmt_num(r.pf)}, DD {fmt_money(r.max_dd)}, LS {r.max_loss_streak}, anchors {r.supportive_anchors}/{r.evaluable_anchors}."
            )
        overall = f"SOL_R4C_24H_{len(P)}_FULL_GATE_PASSERS"

    lines += ["", "## Interpretation guardrails", "",
              "- A `BEST_NEAR_MISS` is descriptive only and is **not promoted**.",
              "- The full gate remains unchanged after seeing all 24 hours.",
              "- This roll-up is development research; it does not open or consume a new OOS period.",
              "- R4b H05 is a separate frozen-cohort result and should be compared as a benchmark, not silently substituted into this R4c selection set.", "",
              f"**Status: {overall}**", ""]

    OUT_MD.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(overall + "\n")
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
