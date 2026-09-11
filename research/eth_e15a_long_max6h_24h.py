#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_economic_first_e12a_long_13_14wib_character as e12
import eth_e13c_e12_native_hold_sequential as e13c

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E15A_LONG_MAX6H_24H"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_PASSERS = ROOT / f"{PFX}_FormalPassers.csv"
OUT_HOURS = ROOT / f"{PFX}_HourSummary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HOLDS = (60, 120, 240, 360)
LOOKBACKS = (15, 30, 60, 120, 240, 360)
YEARS = (2022, 2023, 2024)


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def clocks_for_hour(hour_wib: int):
    b = ((hour_wib - 7) % 24) * 60
    return tuple((b + q) % 1440 for q in (0, 15, 30, 45))


def rank_passers(D: pd.DataFrame) -> pd.DataFrame:
    C = D[D.candidate_gate].copy().sort_values(
        ["min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd",
         "max_loss_streak", "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    return C


def representative(D: pd.DataFrame):
    Z = D.copy().sort_values(
        ["candidate_gate", "anchor_gate", "pooled_gate", "era_gate", "min_year_exp",
         "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd", "max_loss_streak",
         "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    return Z.iloc[0]


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    # Freeze the altered search family globally for exact reuse of E12 candidate evaluator.
    e12.HOLDS = HOLDS
    e12.LOOKBACKS = LOOKBACKS

    all_grids = []
    all_passers = []
    hour_rows = []

    for hour in range(24):
        e12.CLOCKS = clocks_for_hour(hour)
        cache = e12.prep(x5)
        rows = [e12.candidate(cache, lb, hold, rule)
                for lb in LOOKBACKS for hold in HOLDS for rule in e12.RULES]
        D = pd.DataFrame(rows)
        if len(D) != 2160:
            raise AssertionError(f"hour {hour}: expected 2160 candidates, got {len(D)}")
        D.insert(0, "hour_wib", hour)
        C = rank_passers(D)
        if len(C):
            C.insert(0, "hour_wib", hour)
            all_passers.append(C)
        r = representative(D)
        hour_rows.append({
            "hour_wib": hour,
            "formal_status": "PASS" if bool(r.candidate_gate) else "FAIL",
            "full_gate_passers": int(D.candidate_gate.sum()),
            "character_rule": r.character_rule,
            "lookback_min": int(r.lookback_min),
            "hold_min": int(r.hold_min),
            "trades": int(r.trades),
            "win_rate": float(r.win_rate) if np.isfinite(r.win_rate) else np.nan,
            "net_pnl": float(r.net_pnl),
            "expectancy": float(r.expectancy) if np.isfinite(r.expectancy) else np.nan,
            "pf": float(r.pf) if np.isfinite(r.pf) else np.nan,
            "max_dd": float(r.max_dd) if np.isfinite(r.max_dd) else np.nan,
            "max_loss_streak": int(r.max_loss_streak),
            "supportive_anchors": int(r.supportive_anchors),
            "evaluable_anchors": int(r.evaluable_anchors),
            "anchor_gate": bool(r.anchor_gate),
            "pooled_gate": bool(r.pooled_gate),
            "era_gate": bool(r.era_gate),
            "min_year_exp": float(r.min_year_exp),
            "years_wr55": int(r.years_wr55),
            "y2022_wr": float(r.y2022_wr) if np.isfinite(r.y2022_wr) else np.nan,
            "y2022_exp": float(r.y2022_exp) if np.isfinite(r.y2022_exp) else np.nan,
            "y2023_wr": float(r.y2023_wr) if np.isfinite(r.y2023_wr) else np.nan,
            "y2023_exp": float(r.y2023_exp) if np.isfinite(r.y2023_exp) else np.nan,
            "y2024_wr": float(r.y2024_wr) if np.isfinite(r.y2024_wr) else np.nan,
            "y2024_exp": float(r.y2024_exp) if np.isfinite(r.y2024_exp) else np.nan,
        })
        all_grids.append(D)
        print(f"hour {hour:02d}: passers={int(D.candidate_gate.sum())} rep={r.character_rule}/LB{int(r.lookback_min)}/H{int(r.hold_min)} status={'PASS' if bool(r.candidate_gate) else 'FAIL'}")

    G = pd.concat(all_grids, ignore_index=True)
    H = pd.DataFrame(hour_rows)
    P = pd.concat(all_passers, ignore_index=True) if all_passers else pd.DataFrame()
    G.to_csv(OUT_GRID, index=False)
    H.to_csv(OUT_HOURS, index=False)
    P.to_csv(OUT_PASSERS, index=False)

    pass_hours = H[H.formal_status == "PASS"]
    status = "ETH_E15A_MAX6H_CHARACTER_MAP_FOUND" if len(pass_hours) else "ETH_E15A_NO_MAX6H_FORMAL_PASS_HOURS"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH E15A — 24H LONG Character Rediscovery, Max Hold 6h", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "LONG only. Holds frozen to **60/120/240/360m**; no TP/SL, DCA, SHORT, or sequential selector.",
        f"Search: **24 hours x 2,160 candidates/hour = {len(G):,} Development candidates**.",
        f"Formal PASS hours: **{len(pass_hours)}/24**; total formal full-gate candidates: **{len(P)}**.", "",
        "## 24-hour representative map", "",
        "| WIB | Status | Passers | Character | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Anchors | Min-year exp | Y>=55 |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in H.itertuples(index=False):
        lines.append(
            f"| {int(r.hour_wib):02d} | {r.formal_status} | {int(r.full_gate_passers)} | {r.character_rule} | "
            f"{int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {money(r.min_year_exp)} | {int(r.years_wr55)}/3 |"
        )

    lines += ["", "## Formal PASS detail", ""]
    if len(pass_hours) == 0:
        lines.append("No hour produced a full-gate passer under the max-6h search family.")
    else:
        for r in pass_hours.itertuples(index=False):
            lines += [
                f"### {int(r.hour_wib):02d}:00–{(int(r.hour_wib)+1)%24:02d}:00 WIB",
                f"- {r.character_rule} / LB{int(r.lookback_min)} / H{int(r.hold_min)}",
                f"- N {int(r.trades)}, WR {pct(r.win_rate)}, net {money(r.net_pnl)}, exp {money(r.expectancy)}, PF {r.pf:.3f}, DD {money(r.max_dd)}, LS {int(r.max_loss_streak)}",
                f"- era: 2022 {pct(r.y2022_wr)}/{money(r.y2022_exp)}, 2023 {pct(r.y2023_wr)}/{money(r.y2023_exp)}, 2024 {pct(r.y2024_wr)}/{money(r.y2024_exp)}", ""
            ]

    lines += ["## Status", "", f"**{status}**", "", "Research/shadow only. No OOS exposure and no live authorization."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
