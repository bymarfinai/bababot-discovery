#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import sol_economic_first_h00_long_07_08wib_character as grammar

ROOT = Path(__file__).resolve().parent.parent
HOUR = int(os.environ.get("SOL_R4C_HOUR_WIB", "1"))
if HOUR < 0 or HOUR > 23:
    raise ValueError(f"invalid SOL_R4C_HOUR_WIB={HOUR}")

PFX = f"SOL_R4C_H{HOUR:02d}_ETHSTYLE_LONG_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_PROVENANCE = ROOT / f"{PFX}_Provenance.md"

# WIB = UTC+7. Four quarter-hour anchors define exactly one WIB hour.
UTC_BASE = ((HOUR - 7) % 24) * 60
CLOCKS = tuple((UTC_BASE + q) % 1440 for q in (0, 15, 30, 45))


def main() -> None:
    grammar.CLOCKS = CLOCKS
    grammar.base.synthetic_tests()
    x5, coverage = grammar.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    cache = grammar.prepare(x5)
    D, C = grammar.build_grid(cache)
    if len(D) != 3240:
        raise AssertionError(f"expected 3240 candidates, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        f"# SOL R4c — H{HOUR:02d} ETH-Style LONG Character Discovery", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        f"Time habitat: **{HOUR:02d}:00–{(HOUR+1)%24:02d}:00 WIB only**.",
        "Scientific grammar/gates are frozen from the established one-hour economic-first method; only the hour changes.",
        "Development-era consistency: 2022, 2023, 2024. OOS is not opened by this runner.",
        f"Character rules: **{len(grammar.RULES)}**; lookbacks: **{len(grammar.LOOKBACKS)}**; holds: **{len(grammar.HOLDS)}**; candidates: **{len(D)}**; full-gate passers: **{len(C)}**.", "",
        "## Best Development LONG characters", "",
        "| # | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Anchors | 2022 WR/Exp | 2023 WR/Exp | 2024 WR/Exp | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    top = D.sort_values(
        ["candidate_gate", "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf"],
        ascending=[False, False, False, False, False, False],
    ).head(25)
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {i} | `{r.character_rule}` | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | "
            f"{grammar.pct(r.win_rate)} | {grammar.money(r.net_pnl)} | {grammar.money(r.expectancy)} | {float(r.pf):.3f} | {grammar.money(r.max_dd)} | "
            f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | "
            f"{grammar.pct(r.y2022_wr)}/{grammar.money(r.y2022_exp)} | "
            f"{grammar.pct(r.y2023_wr)}/{grammar.money(r.y2023_exp)} | "
            f"{grammar.pct(r.y2024_wr)}/{grammar.money(r.y2024_exp)} | {'YES' if r.candidate_gate else 'NO'} |"
        )

    if C.empty:
        status = f"SOL_R4C_H{HOUR:02d}_NO_LONG_CHARACTER"
        lines += ["", f"**Status: {status}**", "",
                  f"No H{HOUR:02d} LONG character passed the unchanged anchor-stability + pooled-economics + all-era gates.",
                  "No gate relaxation. No replacement candidate is promoted.", "", "Research/shadow only."]
    else:
        s = C.iloc[0]
        atlas = grammar.selected_anchor_atlas(s)
        atlas.to_csv(OUT_ATLAS, index=False)
        status = f"SOL_R4C_H{HOUR:02d}_LONG_CHARACTER_FOUND"
        lines += ["", "## Development-selected LONG character", "",
                  f"**{s['character_rule']} / LB{int(s['lookback_min'])} / hold{int(s['hold_min'])}m**", "",
                  f"Pooled N **{int(s['trades'])}**, WR **{grammar.pct(s['win_rate'])}**, net **{grammar.money(s['net_pnl'])}**, "
                  f"exp **{grammar.money(s['expectancy'])}/trade**, PF **{float(s['pf']):.3f}**, DD **{grammar.money(s['max_dd'])}**, "
                  f"loss streak **{int(s['max_loss_streak'])}**, supportive anchors **{int(s['supportive_anchors'])}/{int(s['evaluable_anchors'])}**.", "",
                  "### Cross-era Development", "",
                  f"- 2022: N {int(s['y2022_trades'])}, WR {grammar.pct(s['y2022_wr'])}, exp {grammar.money(s['y2022_exp'])}, PF {float(s['y2022_pf']):.3f}",
                  f"- 2023: N {int(s['y2023_trades'])}, WR {grammar.pct(s['y2023_wr'])}, exp {grammar.money(s['y2023_exp'])}, PF {float(s['y2023_pf']):.3f}",
                  f"- 2024: N {int(s['y2024_trades'])}, WR {grammar.pct(s['y2024_wr'])}, exp {grammar.money(s['y2024_exp'])}, PF {float(s['y2024_pf']):.3f}", "",
                  "### Quarter-hour anchor atlas", "",
                  "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in atlas.itertuples(index=False):
            lines.append(
                f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {grammar.pct(r.win_rate)} | {grammar.money(r.net_pnl)} | "
                f"{grammar.money(r.expectancy)} | {float(r.pf):.3f} | {grammar.money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |"
            )
        lines += ["", f"**Status: {status}**", "", "Freeze this selected hourly character for bounded follow-up; do not reopen this hour's grid after later validation.", "", "Research/shadow only."]

    OUT_STATUS.write_text(status + "\n")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_PROVENANCE.write_text(
        f"# SOL R4c H{HOUR:02d} ETH-Style — Provenance\n\n"
        f"- Hour: H{HOUR:02d} WIB only.\n"
        "- Direction: LONG.\n"
        "- Frozen search grammar: 90 rules × 6 lookbacks × 6 holds = 3,240 candidates.\n"
        "- Frozen economic/anchor/all-era gates inherited unchanged from the established SOL/ETH one-hour economic-first method.\n"
        "- Development consistency uses 2022/2023/2024.\n"
        "- No gate relaxation or replacement after observing the hour result.\n"
    )
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
