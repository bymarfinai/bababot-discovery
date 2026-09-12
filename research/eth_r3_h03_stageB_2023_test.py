#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "ETH_R3_H03_STAGEA_FrozenDevCandidate.csv"
OUT_NEIGHBOR = ROOT / "ETH_R3_H03_STAGEB_2023_LocalNeighborhood.csv"
OUT_LOCK = ROOT / "ETH_R3_H03_STAGEB_FrozenStableCandidate.csv"
OUT_RESULT = ROOT / "ETH_R3_H03_STAGEB_Result.md"
OUT_STATUS = ROOT / "ETH_R3_H03_STAGEB_Status.txt"

HOUR_WIB = 3
LOOKBACKS = list(r1.LOOKBACKS)
HOLDS = list(r1.HOLDS)
START = pd.Timestamp("2023-01-01", tz="UTC")
END = pd.Timestamp("2024-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T)


def main():
    if not LOCK_PATH.exists():
        raise FileNotFoundError(LOCK_PATH)
    lock = pd.read_csv(LOCK_PATH).iloc[0]
    rule = str(lock.character_rule)
    dev_lb = int(lock.dev_lb)
    dev_hold = int(lock.dev_hold)
    dev_wr = float(lock.dev_wr)
    dev_exp = float(lock.dev_exp)
    dev_pf = float(lock.dev_pf)
    dev_dd = float(lock.dev_dd)
    dev_ls = int(lock.dev_ls)

    li = {v: i for i, v in enumerate(LOOKBACKS)}
    hi = {v: i for i, v in enumerate(HOLDS)}
    di, dj = li[dev_lb], hi[dev_hold]
    coords = []
    for lb in LOOKBACKS:
        for hold in HOLDS:
            dist = abs(li[lb] - di) + abs(hi[hold] - dj)
            if dist <= 1:
                coords.append((lb, hold, dist))

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    # Stage B sees only 2023 bars; 2024+ is excluded.
    x = x5[(pd.DatetimeIndex(x5.index) >= START) & (pd.DatetimeIndex(x5.index) < END)].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    cache = e12.prep(x)

    rows = []
    dd_cap = min(160.0, 1.50 * dev_dd + 20.0)
    ls_cap = min(12, dev_ls + 4)
    for lb, hold, dist in coords:
        T = r1.candidate_events(cache, int(lb), int(hold), rule)
        s = stats(T)
        wr = float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
        exp = float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
        pf = float(s["pf"]) if finite(s["pf"]) else np.nan
        dd = float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
        wr_drop_pp = 100.0 * (wr - dev_wr) if finite(wr) else -np.inf
        exp_ret = exp / dev_exp if dev_exp > 0 and finite(exp) else -np.inf
        pf_ret = pf / dev_pf if dev_pf > 0 and finite(pf) else -np.inf
        viable = bool(
            s["trades"] >= 50 and finite(wr) and wr >= .52 and s["net_pnl"] > 0 and
            finite(exp) and exp > 0 and finite(pf) and pf >= 1.15 and
            finite(dd) and dd <= dd_cap and s["max_loss_streak"] <= ls_cap
        )
        stable = bool(
            viable and wr >= dev_wr - .05 and exp_ret >= .60 and pf_ret >= .70
        )
        rows.append({
            "character_rule": rule, "lookback_min": int(lb), "hold_min": int(hold), "manhattan_distance": int(dist),
            "trades": int(s["trades"]), "wr": wr, "net": float(s["net_pnl"]), "exp": exp, "pf": pf,
            "dd": dd, "ls": int(s["max_loss_streak"]), "wr_change_pp": wr_drop_pp,
            "exp_retention": exp_ret, "pf_retention": pf_ret,
            "dd_cap": dd_cap, "ls_cap": ls_cap, "economically_viable": viable, "performance_stable": stable,
        })

    N = pd.DataFrame(rows).sort_values(["manhattan_distance", "lookback_min", "hold_min"]).reset_index(drop=True)
    N.to_csv(OUT_NEIGHBOR, index=False)
    viable = N[N.economically_viable].copy()
    stable = N[N.performance_stable].copy()

    lines = [
        "# ETH R3 H03 — Stage B 2023 Practical Stability Test", "",
        "**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**", "",
        f"Frozen Development: **{rule} / LB{dev_lb} / H{dev_hold}**; WR {100*dev_wr:.2f}%, Exp ${dev_exp:+.2f}, PF {dev_pf:.3f}, DD ${dev_dd:.2f}, LS {dev_ls}.",
        f"Preregistered one-step local neighborhood contains **{len(N)}** timing cells. Economically viable in 2023: **{len(viable)}**; performance-stable: **{len(stable)}**.", "",
        "| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for r in N.itertuples(index=False):
        lines.append(
            f"| {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.manhattan_distance)} | {int(r.trades)} | {100*float(r.wr):.2f}% | ${float(r.net):+.2f} | ${float(r.exp):+.2f} | {float(r.pf):.3f} | ${float(r.dd):.2f} | {int(r.ls)} | {float(r.wr_change_pp):+.2f}pp | {100*float(r.exp_retention):.1f}% | {100*float(r.pf_retention):.1f}% | {'Y' if r.economically_viable else 'N'} | {'Y' if r.performance_stable else 'N'} |"
        )

    if len(stable) == 0:
        status = "ETH_R3_H03_TEST_DEGRADATION_FAIL"
        OUT_STATUS.write_text(status + "\n")
        if OUT_LOCK.exists():
            OUT_LOCK.unlink()
        lines += ["", "## Verdict", "", "**TEST_DEGRADATION_FAIL**", "", "No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened."]
    elif len(viable) < 2:
        status = "ETH_R3_H03_LOCAL_NEIGHBORHOOD_FAIL"
        OUT_STATUS.write_text(status + "\n")
        if OUT_LOCK.exists():
            OUT_LOCK.unlink()
        lines += ["", "## Verdict", "", "**LOCAL_NEIGHBORHOOD_FAIL**", "", "A stable point exists, but fewer than two local timing cells are economically viable. 2024 remains unopened."]
    else:
        stable = stable.sort_values(
            ["manhattan_distance", "exp_retention", "wr_change_pp", "pf", "dd", "hold_min", "lookback_min"],
            ascending=[True, False, False, False, True, True, True],
        ).reset_index(drop=True)
        rep = stable.iloc[0]
        pd.DataFrame([{
            "character_rule": rule,
            "dev_lb": dev_lb, "dev_hold": dev_hold, "dev_n": int(lock.dev_n), "dev_wr": dev_wr,
            "dev_net": float(lock.dev_net), "dev_exp": dev_exp, "dev_pf": dev_pf, "dev_dd": dev_dd, "dev_ls": dev_ls,
            "test_lb": int(rep.lookback_min), "test_hold": int(rep.hold_min), "test_distance": int(rep.manhattan_distance),
            "test_n": int(rep.trades), "test_wr": float(rep.wr), "test_net": float(rep.net), "test_exp": float(rep.exp),
            "test_pf": float(rep.pf), "test_dd": float(rep.dd), "test_ls": int(rep.ls),
            "wr_change_pp": float(rep.wr_change_pp), "exp_retention": float(rep.exp_retention), "pf_retention": float(rep.pf_retention),
            "local_viable_cells": int(len(viable)), "local_stable_cells": int(len(stable)), "validation_2024_opened": False,
        }]).to_csv(OUT_LOCK, index=False)
        status = "ETH_R3_H03_STABLE_EDGE_FROZEN"
        OUT_STATUS.write_text(status + "\n")
        lines += [
            "", "## Verdict", "", "**STABLE_EDGE_FROZEN**", "",
            f"Frozen 2023 local coordinate: **LB{int(rep.lookback_min)} / H{int(rep.hold_min)}** (distance {int(rep.manhattan_distance)} from Development).",
            f"2023 N {int(rep.trades)}, WR {100*float(rep.wr):.2f}%, Net ${float(rep.net):+.2f}, Exp ${float(rep.exp):+.2f}, PF {float(rep.pf):.3f}, DD ${float(rep.dd):.2f}, LS {int(rep.ls)}.",
            f"Retention versus 2022: WR change {float(rep.wr_change_pp):+.2f}pp, Exp {100*float(rep.exp_retention):.1f}%, PF {100*float(rep.pf_retention):.1f}%. Local viable cells {len(viable)}/{len(N)}.",
            "The stable edge is frozen. 2024 may now be opened once at the frozen 2023 coordinate; no reselection is allowed.",
        ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
