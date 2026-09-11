#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

# Reuse only the frozen pair-agnostic E12 search engine/grammar/gates.
# No ETH-selected coordinate or ETH result is imported into DOGE selection.
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "DOGE_D1A_LONG_13_14WIB_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def gate_failure(r):
    failures = []
    if not bool(r.anchor_gate):
        failures.append("anchor breadth/stability")
    if not bool(r.pooled_gate):
        pooled_reasons = []
        if int(r.trades) < 160:
            pooled_reasons.append("N")
        if not np.isfinite(r.win_rate) or float(r.win_rate) < .55:
            pooled_reasons.append("WR")
        if float(r.net_pnl) <= 0:
            pooled_reasons.append("net")
        if not np.isfinite(r.expectancy) or float(r.expectancy) < .50:
            pooled_reasons.append("expectancy")
        if not np.isfinite(r.pf) or float(r.pf) < 1.20:
            pooled_reasons.append("PF")
        if not np.isfinite(r.max_dd) or float(r.max_dd) > 125:
            pooled_reasons.append("DD")
        if int(r.max_loss_streak) > 8:
            pooled_reasons.append("loss streak")
        failures.append("pooled(" + ", ".join(pooled_reasons) + ")")
    if not bool(r.era_gate):
        failures.append("cross-era stability")
    return "; ".join(failures) if failures else "none"


def near_miss_table(D):
    X = D.copy()
    X["gates_passed"] = X[["anchor_gate", "pooled_gate", "era_gate"]].astype(int).sum(axis=1)
    return X.sort_values(
        ["gates_passed", "supportive_anchors", "min_year_exp", "expectancy", "win_rate", "pf", "max_dd", "max_loss_streak"],
        ascending=[False, False, False, False, False, False, True, True],
    ).reset_index(drop=True)


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
        "# DOGE D1A — 13:00–14:00 WIB LONG Character Discovery Result", "",
        f"Raw DOGEUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **13:00–14:00 WIB only** (06:00, 06:15, 06:30, 06:45 UTC anchors).",
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
        status = "DOGE_D1A_NO_LONG_CHARACTER"
        best = rank.iloc[0]
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "", "## Formal verdict", "",
            f"**Status: {status}**", "",
            "No 13:00–14:00 WIB DOGE LONG candidate passed anchor + pooled + all-era gates simultaneously.", "",
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
    status = "DOGE_D1A_LONG_CHARACTER_FOUND"
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
