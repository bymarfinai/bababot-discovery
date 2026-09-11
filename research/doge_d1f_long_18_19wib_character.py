#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

# Reuse D1D's already-frozen helper/ranking implementation and the same
# pair-agnostic E12 engine. D1F changes only the clock habitat and labels.
import doge_d1d_long_16_17wib_character as frozen

engine = frozen.engine
ROOT = Path(__file__).resolve().parent.parent
PFX = "DOGE_D1F_LONG_18_19WIB_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

# Frozen D1F habitat only: 11:00..11:45 UTC = 18:00..18:45 WIB.
engine.CLOCKS = (660, 675, 690, 705)

pct = frozen.pct
money = frozen.money
gate_failure = frozen.gate_failure
near_miss_table = frozen.near_miss_table


def main():
    engine.base.synthetic_tests()
    x5, coverage = engine.base.load5("DOGEUSDT")
    if coverage < .995:
        raise RuntimeError(f"DOGEUSDT raw 5m coverage too low: {coverage:.6%} < 99.5%")

    cache = engine.prep(x5)
    D, C = engine.build_grid(cache)
    if len(D) != 3240:
        raise AssertionError(f"expected 3240 candidates, got {len(D)}")

    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    anchor_count = int(D.anchor_gate.sum())
    pooled_count = int(D.pooled_gate.sum())
    era_count = int(D.era_gate.sum())
    full_count = int(D.candidate_gate.sum())

    lines = [
        "# DOGE D1F — 18:00–19:00 WIB LONG Character Discovery Result", "",
        f"Raw DOGEUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **18:00–19:00 WIB only** (11:00, 11:15, 11:30, 11:45 UTC anchors).",
        "Development only; OOS remained closed by preregistration.",
        f"Character rules: **{len(engine.RULES)}**; total candidates: **{len(D)}**.", "",
        "## Gate counts", "",
        f"- anchor gate: **{anchor_count} / 3,240**",
        f"- pooled gate: **{pooled_count} / 3,240**",
        f"- era gate: **{era_count} / 3,240**",
        f"- full gate: **{full_count} / 3,240**", "",
    ]

    rank = near_miss_table(D)
    top = rank.head(25)
    lines += [
        "## Top Development candidates / near-misses", "",
        "| # | Character | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Anchors | Gates | Failure |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {i} | {r.character_rule} | {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | "
            f"{pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | "
            f"{money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | "
            f"{int(r.gates_passed)}/3 | {gate_failure(r)} |"
        )

    if len(C) == 0:
        status = "DOGE_D1F_NO_LONG_CHARACTER"
        best = rank.iloc[0]
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "", "## Formal verdict", "", f"**Status: {status}**", "",
            "No 18:00–19:00 WIB DOGE LONG candidate passed anchor + pooled + all-era gates simultaneously.", "",
            "### Strongest preregistered near-miss", "",
            f"**{best['character_rule']} / LB{int(best['lookback_min'])} / hold{int(best['hold_min'])}m**", "",
            f"N **{int(best['trades'])}**, WR **{pct(best['win_rate'])}**, net **{money(best['net_pnl'])}**, "
            f"expectancy **{money(best['expectancy'])}/trade**, PF **{float(best['pf']):.3f}**, "
            f"DD **{money(best['max_dd'])}**, max loss streak **{int(best['max_loss_streak'])}**, "
            f"supportive anchors **{int(best['supportive_anchors'])}/{int(best['evaluable_anchors'])}**.",
            f"Failure mechanism: **{gate_failure(best)}**.", "",
            f"2022: N {int(best['y2022_trades'])}, WR {pct(best['y2022_wr'])}, exp {money(best['y2022_exp'])}, PF {float(best['y2022_pf']):.3f}.",
            f"2023: N {int(best['y2023_trades'])}, WR {pct(best['y2023_wr'])}, exp {money(best['y2023_exp'])}, PF {float(best['y2023_pf']):.3f}.",
            f"2024: N {int(best['y2024_trades'])}, WR {pct(best['y2024_wr'])}, exp {money(best['y2024_exp'])}, PF {float(best['y2024_pf']):.3f}.", "",
            "Near-miss is descriptive only; no gate relaxation or retroactive promotion is allowed.",
            "OOS remains closed. Research/shadow only."
        ]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    atlas = engine.selected_anchor_atlas(D, sel)
    atlas.to_csv(OUT_ATLAS, index=False)
    status = "DOGE_D1F_LONG_CHARACTER_FOUND"
    OUT_STATUS.write_text(status + "\n")
    lines += [
        "", "## Development-selected formal LONG character", "",
        f"**{sel['character_rule']} / LB{int(sel['lookback_min'])} / hold{int(sel['hold_min'])}m**", "",
        f"Pooled N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, "
        f"exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, "
        f"max loss streak **{int(sel['max_loss_streak'])}**, supportive anchors **{int(sel['supportive_anchors'])}/4**.", "",
        "### Anchor atlas", "",
        "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in atlas.itertuples(index=False):
        lines.append(
            f"| {r.clock_utc} | {r.clock_wib} | {r.trades} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |"
        )
    lines += [
        "", "### Cross-era Development", "",
        f"2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}.",
        f"2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}.",
        f"2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}.", "",
        f"**Status: {status}**", "",
        "This is a local DOGE hour character only, not the full DOGE character. The 24-hour LONG sweep remains mandatory.",
        "OOS remains closed. Research/shadow only."
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
