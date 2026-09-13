#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as base


ROOT = Path(__file__).resolve().parent.parent
DD_RATIO_LIMIT = 0.15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, required=True, choices=range(24))
    parser.add_argument("--input-dir", type=Path)
    return parser.parse_args()


def new_pooled_gate(row: pd.Series) -> bool:
    return bool(
        row["trades"] >= 160
        and np.isfinite(row["win_rate"])
        and row["win_rate"] > 0.55
        and row["net_pnl"] > 0
        and np.isfinite(row["expectancy"])
        and row["expectancy"] >= 0.50
        and np.isfinite(row["pf"])
        and row["pf"] >= 1.20
        and np.isfinite(row["max_dd"])
        and row["max_dd"] <= DD_RATIO_LIMIT * row["net_pnl"]
        and row["max_loss_streak"] <= 8
    )


def fail_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    if not bool(row["anchor_gate"]): reasons.append("anchor_gate")
    if row["trades"] < 160: reasons.append("N<160")
    if not np.isfinite(row["win_rate"]) or row["win_rate"] <= 0.55: reasons.append("WR<=55%")
    if row["net_pnl"] <= 0: reasons.append("net<=0")
    if not np.isfinite(row["expectancy"]) or row["expectancy"] < 0.50: reasons.append("expectancy<0.50")
    if not np.isfinite(row["pf"]) or row["pf"] < 1.20: reasons.append("PF<1.20")
    if not np.isfinite(row["dd_ratio"]) or row["dd_ratio"] > DD_RATIO_LIMIT: reasons.append("DD/net>15%")
    if row["max_loss_streak"] > 8: reasons.append("loss_streak>8")
    if not bool(row["era_gate"]): reasons.append("all_era_gate")
    return ";".join(reasons) if reasons else "PASS"


def main() -> None:
    args = parse_args()
    hour = args.hour
    base.CLOCKS = tuple(hour * 60 + q for q in (0, 15, 30, 45))

    base.base.synthetic_tests()
    x5, coverage = base.base.load5("SOLUSDT")
    cache = base.prepare(x5)
    development, _ = base.build_grid(cache)

    development["old_candidate_gate"] = development["candidate_gate"].astype(bool)
    development["dd_ratio"] = np.where(
        development["net_pnl"] > 0,
        development["max_dd"] / development["net_pnl"],
        np.inf,
    )
    development["new_pooled_gate"] = development.apply(new_pooled_gate, axis=1)
    development["new_candidate_gate"] = (
        development["anchor_gate"].astype(bool)
        & development["new_pooled_gate"].astype(bool)
        & development["era_gate"].astype(bool)
    )
    development["rescued"] = development["new_candidate_gate"] & ~development["old_candidate_gate"]
    development["lost"] = development["old_candidate_gate"] & ~development["new_candidate_gate"]
    development["fail_reasons"] = development.apply(fail_reasons, axis=1)

    ranked = development.sort_values(
        ["new_candidate_gate", "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf",
         "dd_ratio", "max_loss_streak", "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    passers = ranked[ranked["new_candidate_gate"]].copy()
    passers["new_rank"] = np.arange(1, len(passers) + 1)

    old_n = int(development["old_candidate_gate"].sum())
    new_n = int(development["new_candidate_gate"].sum())
    rescued_n = int(development["rescued"].sum())
    lost_n = int(development["lost"].sum())
    best_fail = ranked.loc[~ranked["new_candidate_gate"]].iloc[0]
    summary = pd.DataFrame([{
        "hour": hour,
        "utc": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00",
        "wib": f"{(hour + 7) % 24:02d}:00-{(hour + 8) % 24:02d}:00",
        "coverage": coverage,
        "candidate_count": len(development),
        "old_passers": old_n,
        "new_passers": new_n,
        "rescued_passers": rescued_n,
        "lost_passers": lost_n,
        "status": "PASS" if new_n else "FAIL",
        "best_fail_rule": best_fail["character_rule"] if not new_n else "",
        "best_fail_lb": int(best_fail["lookback_min"]) if not new_n else "",
        "best_fail_hold": int(best_fail["hold_min"]) if not new_n else "",
        "best_fail_reasons": best_fail["fail_reasons"] if not new_n else "",
    }])

    out = args.input_dir or ROOT / "audit_parts"
    out.mkdir(parents=True, exist_ok=True)
    cols = [
        "lookback_min", "hold_min", "character_rule", "trades", "win_rate", "net_pnl", "expectancy",
        "pf", "max_dd", "dd_ratio", "max_loss_streak", "supportive_anchors", "evaluable_anchors",
        "y2022_trades", "y2022_wr", "y2022_exp", "y2022_pf", "y2023_trades", "y2023_wr",
        "y2023_exp", "y2023_pf", "y2024_trades", "y2024_wr", "y2024_exp", "y2024_pf",
        "old_candidate_gate", "new_candidate_gate", "rescued", "lost", "new_rank",
    ]
    summary.to_csv(out / f"H{hour:02d}_summary.csv", index=False)
    passers[cols].to_csv(out / f"H{hour:02d}_passers.csv", index=False)
    ranked.head(50).to_csv(out / f"H{hour:02d}_top50.csv", index=False)
    print(summary.to_string(index=False))
    if len(passers):
        print(passers[cols].to_string(index=False))


if __name__ == "__main__":
    main()
