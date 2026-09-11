#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as e12a

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E12H_LONG_20_21WIB_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (780, 795, 810, 825)  # 13:00..13:45 UTC = 20:00..20:45 WIB


def pct(x): return e12a.pct(x)
def money(x): return e12a.money(x)


def main():
    e12a.CLOCKS = CLOCKS
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    cache = e12a.prep(x5)
    D, C = e12a.build_grid(cache)
    if len(D) != 3240:
        raise AssertionError(f"expected 3240 candidates, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Economic-First E12H — 20:00–21:00 WIB LONG Character Discovery Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **20:00–21:00 WIB only** (13:00, 13:15, 13:30, 13:45 UTC anchors).",
        "Scientific grammar and gates: **identical to preregistered E12A–E12G; only the hour changed**.",
        "Development only; OOS remained closed by preregistration.",
        f"Character rules: **{len(e12a.RULES)}**; total Development candidates: **{len(D)}**; full-gate passers: **{len(C)}**.", "",
        "## Best Development LONG characters", "",
        "| # | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Anchors | 2022 WR/Exp | 2023 | 2024 | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    top = D.sort_values(["candidate_gate","min_year_exp","supportive_anchors","expectancy","win_rate","pf"], ascending=[False,False,False,False,False,False]).head(25)
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(f"| {i} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | {'YES' if r.candidate_gate else 'NO'} |")

    if len(C) == 0:
        status = "ETH_ECONOMIC_FIRST_E12H_NO_LONG_CHARACTER"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "", "No 20:00–21:00 WIB LONG character passed the preregistered anchor-stability + pooled-economics + all-era gates.", "No gate relaxation and no OOS exposure.", "", "Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    atlas = e12a.selected_anchor_atlas(D, sel)
    atlas.to_csv(OUT_ATLAS, index=False)
    status = "ETH_ECONOMIC_FIRST_E12H_LONG_CHARACTER_FOUND"
    OUT_STATUS.write_text(status + "\n")
    lines += ["", "## Development-selected LONG character", "", f"**{sel['character_rule']} / LB{int(sel['lookback_min'])} / hold{int(sel['hold_min'])}m**", "", f"Pooled N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, loss streak **{int(sel['max_loss_streak'])}**, supportive anchors **{int(sel['supportive_anchors'])}/{int(sel['evaluable_anchors'])}**.", "", "### Cross-era Development", "", f"- 2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}", f"- 2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}", f"- 2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}", "", "### Quarter-hour anchor atlas", "", "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |", "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in atlas.itertuples(index=False):
        lines.append(f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |")
    lines += ["", f"**Status: {status}**", "", "Discovery-only: OOS stays closed.", "", "Research/shadow only."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
