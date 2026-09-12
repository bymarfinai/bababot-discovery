#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R3_H05_STAGEA"
OUT_GRID = ROOT / f"{PFX}_2022_DevGrid.csv"
OUT_LOCK = ROOT / f"{PFX}_FrozenDevCandidate.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HOUR_WIB = 5
LOOKBACKS = r1.LOOKBACKS
HOLDS = r1.HOLDS
START = pd.Timestamp("2022-01-01", tz="UTC")
MID = pd.Timestamp("2022-07-01", tz="UTC")
END = pd.Timestamp("2023-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T)


def ts_utc(values):
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True))


def period(T: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    if len(T) == 0:
        return stats(T)
    ent = ts_utc(T.entry_ts)
    ex = ts_utc(T.exit_ts)
    m = (ent >= start) & (ex < end)
    return stats(T.loc[m])


def anchor_positive(T: pd.DataFrame, clock: int):
    s = stats(T[T.clock == clock])
    return bool(
        s["trades"] >= 12 and finite(s["expectancy"]) and s["expectancy"] > 0 and
        finite(s["pf"]) and s["pf"] > 1
    )


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x = x5[(idx >= START) & (idx < END)].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    cache = e12.prep(x)

    rows = []
    for rule in e12.RULES:
        for lb in LOOKBACKS:
            for hold in HOLDS:
                T = r1.candidate_events(cache, int(lb), int(hold), str(rule))
                s = stats(T)
                h1 = period(T, START, MID)
                h2 = period(T, MID, END)
                pos_a = sum(int(anchor_positive(T, c)) for c in e12.CLOCKS)
                halves_ok = bool(
                    h1["trades"] > 0 and h2["trades"] > 0 and
                    finite(h1["expectancy"]) and h1["expectancy"] > 0 and finite(h1["pf"]) and h1["pf"] > 1 and
                    finite(h2["expectancy"]) and h2["expectancy"] > 0 and finite(h2["pf"]) and h2["pf"] > 1
                )
                eligible = bool(
                    s["trades"] >= 60 and finite(s["win_rate"]) and s["win_rate"] >= .55 and
                    s["net_pnl"] > 0 and finite(s["expectancy"]) and s["expectancy"] >= .50 and
                    finite(s["pf"]) and s["pf"] >= 1.20 and finite(s["max_dd"]) and s["max_dd"] <= 125 and
                    halves_ok and pos_a >= 2
                )
                rows.append({
                    "character_rule": str(rule), "lookback_min": int(lb), "hold_min": int(hold),
                    "trades": int(s["trades"]), "wr": float(s["win_rate"]) if finite(s["win_rate"]) else np.nan,
                    "net": float(s["net_pnl"]), "exp": float(s["expectancy"]) if finite(s["expectancy"]) else np.nan,
                    "pf": float(s["pf"]) if finite(s["pf"]) else np.nan,
                    "dd": float(s["max_dd"]) if finite(s["max_dd"]) else np.nan, "ls": int(s["max_loss_streak"]),
                    "H1_trades": int(h1["trades"]), "H1_exp": float(h1["expectancy"]) if finite(h1["expectancy"]) else np.nan,
                    "H1_pf": float(h1["pf"]) if finite(h1["pf"]) else np.nan,
                    "H2_trades": int(h2["trades"]), "H2_exp": float(h2["expectancy"]) if finite(h2["expectancy"]) else np.nan,
                    "H2_pf": float(h2["pf"]) if finite(h2["pf"]) else np.nan,
                    "min_half_exp": min(float(h1["expectancy"]), float(h2["expectancy"])) if finite(h1["expectancy"]) and finite(h2["expectancy"]) else -np.inf,
                    "positive_anchors": int(pos_a), "dev_eligible": eligible,
                })

    D = pd.DataFrame(rows)
    if len(D) != 1800:
        raise AssertionError(f"expected 1800 cells, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)

    E = D[D.dev_eligible].copy()
    lines = [
        "# ETH R3 H05 — Stage A 2022 Development Freeze", "",
        "**2022 ONLY. 2023 UNOPENED. 2024 HARD LOCKED. 2025+ CLOSED.**", "",
        f"Source coverage: {coverage:.4%}. Grid: 90 rules × 20 coarse timings = **{len(D)} cells**.",
        f"Development-eligible cells under the preregistered practical-stability protocol: **{len(E)}**.",
        "Maximum loss streak is diagnostic only and is not an eligibility gate.", "",
    ]

    if len(E) == 0:
        status = "ETH_R3_H05_NO_2022_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        if OUT_LOCK.exists(): OUT_LOCK.unlink()
        lines += ["## Verdict", "", "**NO_2022_DEV_CANDIDATE**", "", "2023 remains unopened; 2024 remains locked."]
    else:
        E = E.sort_values(
            ["min_half_exp", "exp", "pf", "dd", "ls", "trades", "character_rule", "hold_min", "lookback_min"],
            ascending=[False, False, False, True, True, False, True, True, True],
        ).reset_index(drop=True)
        rep = E.iloc[0]
        pd.DataFrame([{
            "character_rule": rep.character_rule,
            "dev_lb": int(rep.lookback_min), "dev_hold": int(rep.hold_min),
            "dev_n": int(rep.trades), "dev_wr": float(rep.wr), "dev_net": float(rep.net),
            "dev_exp": float(rep.exp), "dev_pf": float(rep.pf), "dev_dd": float(rep.dd), "dev_ls": int(rep.ls),
            "dev_H1_exp": float(rep.H1_exp), "dev_H1_pf": float(rep.H1_pf),
            "dev_H2_exp": float(rep.H2_exp), "dev_H2_pf": float(rep.H2_pf),
            "dev_positive_anchors": int(rep.positive_anchors), "test_2023_opened": False,
        }]).to_csv(OUT_LOCK, index=False)
        status = "ETH_R3_H05_2022_DEV_CANDIDATE_FROZEN"
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "## Frozen Development representative", "",
            f"Rule: **{rep.character_rule}**", f"Timing: **LB{int(rep.lookback_min)} / H{int(rep.hold_min)}**",
            f"N **{int(rep.trades)}**, WR **{100*float(rep.wr):.2f}%**, Net **${float(rep.net):+.2f}**, Exp **${float(rep.exp):+.2f}**, PF **{float(rep.pf):.3f}**, DD **${float(rep.dd):.2f}**, LS **{int(rep.ls)}**.",
            f"2022 H1 Exp ${float(rep.H1_exp):+.2f}/PF {float(rep.H1_pf):.3f}; H2 Exp ${float(rep.H2_exp):+.2f}/PF {float(rep.H2_pf):.3f}; positive anchors {int(rep.positive_anchors)}/4.", "",
            "The representative is now frozen. Stage B may open 2023 only for the same rule and the preregistered one-step local LB/Hold neighborhood.",
        ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
