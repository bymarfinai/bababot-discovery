#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as grammar

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_R4C_H00_ETHSTYLE_LONG_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_PROVENANCE = ROOT / f"{PFX}_Provenance.md"

# 00:00, 00:15, 00:30, 00:45 WIB = 17:00..17:45 UTC on prior UTC date.
CLOCKS = (1020, 1035, 1050, 1065)


def main():
    # Reuse the SOL-native causal state engine and the exact ETH-style one-hour
    # economic-first grammar/gates already implemented in the SOL character engine.
    # Only the one-hour habitat changes.
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
        "# SOL R4c — H00 ETH-Style LONG Character Discovery", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **00:00–01:00 WIB only** (17:00, 17:15, 17:30, 17:45 UTC anchors).",
        "Scientific grammar and gates: **same one-hour economic-first method used by ETH E12A/E12B; SOL-native data/state engine**.",
        "Development spans the predeclared 2022–2024 development eras; OOS is not opened by this runner.",
        f"Character rules: **{len(grammar.RULES)}**; lookbacks: **{len(grammar.LOOKBACKS)}**; holds: **{len(grammar.HOLDS)}**; total candidates: **{len(D)}**; full-gate passers: **{len(C)}**.", "",
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
            f"{grammar.pct(r.y2024_wr)}/{grammar.money(r.y2024_exp)} | "
            f"{'YES' if r.candidate_gate else 'NO'} |"
        )

    if len(C) == 0:
        status = "SOL_R4C_H00_NO_LONG_CHARACTER"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "",
                  "No H00 LONG character passed the unchanged one-hour anchor-stability + pooled-economics + all-era gates.",
                  "No gate relaxation. No replacement candidate is promoted.", "", "Research/shadow only."]
    else:
        selected = C.iloc[0]
        atlas = grammar.selected_anchor_atlas(selected)
        atlas.to_csv(OUT_ATLAS, index=False)
        status = "SOL_R4C_H00_LONG_CHARACTER_FOUND"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", "## Development-selected LONG character", "",
                  f"**{selected['character_rule']} / LB{int(selected['lookback_min'])} / hold{int(selected['hold_min'])}m**", "",
                  f"Pooled N **{int(selected['trades'])}**, WR **{grammar.pct(selected['win_rate'])}**, net **{grammar.money(selected['net_pnl'])}**, "
                  f"exp **{grammar.money(selected['expectancy'])}/trade**, PF **{float(selected['pf']):.3f}**, DD **{grammar.money(selected['max_dd'])}**, "
                  f"loss streak **{int(selected['max_loss_streak'])}**, supportive anchors **{int(selected['supportive_anchors'])}/{int(selected['evaluable_anchors'])}**.", "",
                  "### Cross-era Development", "",
                  f"- 2022: N {int(selected['y2022_trades'])}, WR {grammar.pct(selected['y2022_wr'])}, exp {grammar.money(selected['y2022_exp'])}, PF {float(selected['y2022_pf']):.3f}",
                  f"- 2023: N {int(selected['y2023_trades'])}, WR {grammar.pct(selected['y2023_wr'])}, exp {grammar.money(selected['y2023_exp'])}, PF {float(selected['y2023_pf']):.3f}",
                  f"- 2024: N {int(selected['y2024_trades'])}, WR {grammar.pct(selected['y2024_wr'])}, exp {grammar.money(selected['y2024_exp'])}, PF {float(selected['y2024_pf']):.3f}", "",
                  "### Quarter-hour anchor atlas", "",
                  "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|---|" ]
        for r in atlas.itertuples(index=False):
            lines.append(
                f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {grammar.pct(r.win_rate)} | "
                f"{grammar.money(r.net_pnl)} | {grammar.money(r.expectancy)} | {float(r.pf):.3f} | "
                f"{grammar.money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |"
            )
        lines += ["", f"**Status: {status}**", "",
                  "Freeze this selected H00 character for the next bounded follow-up. Do not reopen the H00 grid after seeing later-period validation.", "", "Research/shadow only."]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_PROVENANCE.write_text(
        "# SOL R4c H00 ETH-Style — Provenance\n\n"
        "- Parent R4b checkpoint: `128747de04df3c7f69a259a3980ab800c0708d47`.\n"
        "- Branch: `sol-r4c-hourly-character-scan`.\n"
        "- Hour only: H00 = 00:00–01:00 WIB.\n"
        "- Direction: LONG.\n"
        "- Search grammar: 90 character rules × 6 lookbacks × 6 holds = 3,240 candidates.\n"
        "- Lookbacks/holds and economic gates are inherited from the existing SOL economic-first character engine, which mirrors the ETH E12A/E12B one-hour method.\n"
        "- 2022/2023/2024 are treated as development-era consistency checks in this runner.\n"
        "- No gate relaxation after observing H00.\n"
        "- The earlier fixed-H120 H00 diagnostic is retained separately and is not used to select this grid winner.\n"
    )
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
