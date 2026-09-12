#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "ETH_R3_H04_STAGEB_FrozenStableCandidate.csv"
OUT_EVENTS = ROOT / "ETH_R3_H04_STAGEC_2024_Events.csv"
OUT_SUMMARY = ROOT / "ETH_R3_H04_STAGEC_2024_Summary.csv"
OUT_RESULT = ROOT / "ETH_R3_H04_STAGEC_Result.md"
OUT_STATUS = ROOT / "ETH_R3_H04_STAGEC_Status.txt"

HOUR_WIB = 4
START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")


def finite(x): return bool(np.isfinite(x))
def stats(T: pd.DataFrame): return r1.stats_from_df(T)


def main():
    if not LOCK_PATH.exists(): raise FileNotFoundError(LOCK_PATH)
    lock = pd.read_csv(LOCK_PATH).iloc[0]
    rule = str(lock.character_rule)
    lb, hold = int(lock.test_lb), int(lock.test_hold)

    dev_wr, test_wr = float(lock.dev_wr), float(lock.test_wr)
    dev_exp, test_exp = float(lock.dev_exp), float(lock.test_exp)
    dev_pf, test_pf = float(lock.dev_pf), float(lock.test_pf)
    dev_dd, test_dd = float(lock.dev_dd), float(lock.test_dd)
    dev_ls, test_ls = int(lock.dev_ls), int(lock.test_ls)

    mean_wr = (dev_wr + test_wr) / 2.0
    mean_exp = (dev_exp + test_exp) / 2.0
    mean_pf = (dev_pf + test_pf) / 2.0
    wr_floor = max(.52, mean_wr - .06)
    exp_floor = .55 * mean_exp
    pf_floor = max(1.15, .65 * mean_pf)
    dd_cap = 1.6 * max(dev_dd, test_dd) + 20.0
    ls_cap = max(12, max(dev_ls, test_ls) + 3)

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low: {coverage}")

    # Use historical bars causally for indicator warm-up, but only score entries/exits fully inside 2024.
    idx = pd.to_datetime(x5.index, utc=True)
    x = x5[idx < END].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = [lb]
    e12.HOLDS = [hold]
    cache = e12.prep(x)
    T = r1.candidate_events(cache, lb, hold, rule).copy()
    if len(T):
        entry = pd.to_datetime(T.entry_ts, utc=True)
        exit_ = pd.to_datetime(T.exit_ts, utc=True)
        T = T[(entry >= START) & (exit_ < END)].copy().reset_index(drop=True)
    T.to_csv(OUT_EVENTS, index=False)
    s = stats(T)

    wr = float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
    exp = float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
    pf = float(s["pf"]) if finite(s["pf"]) else np.nan
    dd = float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
    ls = int(s["max_loss_streak"])
    passed = bool(
        s["trades"] >= 40 and finite(wr) and wr >= wr_floor and s["net_pnl"] > 0 and
        finite(exp) and exp >= exp_floor and finite(pf) and pf >= pf_floor and
        finite(dd) and dd <= dd_cap and ls <= ls_cap
    )

    pd.DataFrame([{
        "character_rule": rule, "lookback_min": lb, "hold_min": hold,
        "trades": int(s["trades"]), "wr": wr, "net": float(s["net_pnl"]), "exp": exp,
        "pf": pf, "dd": dd, "ls": ls,
        "mean_2022_2023_wr": mean_wr, "wr_floor": wr_floor,
        "mean_2022_2023_exp": mean_exp, "exp_floor": exp_floor,
        "mean_2022_2023_pf": mean_pf, "pf_floor": pf_floor,
        "dd_cap": dd_cap, "ls_cap": ls_cap, "passed": passed,
    }]).to_csv(OUT_SUMMARY, index=False)

    status = "ETH_R3_H04_ROBUST_STABLE_HABITAT" if passed else "ETH_R3_H04_2024_CONFIRMATION_FAIL"
    OUT_STATUS.write_text(status + "\n")
    verdict = "ROBUST_STABLE_HABITAT" if passed else "2024_CONFIRMATION_FAIL"
    lines = [
        "# ETH R3 H04 — Stage C One-Shot 2024 Confirmation", "",
        "**FROZEN RULE AND COORDINATE. NO 2024 RESELECTION. 2025+ OOS CLOSED.**", "",
        f"Frozen candidate: **{rule} / LB{lb} / H{hold}**.",
        f"2022 Development: WR {100*dev_wr:.2f}%, Exp ${dev_exp:+.2f}, PF {dev_pf:.3f}, DD ${dev_dd:.2f}, LS {dev_ls}.",
        f"2023 Test: WR {100*test_wr:.2f}%, Exp ${test_exp:+.2f}, PF {test_pf:.3f}, DD ${test_dd:.2f}, LS {test_ls}.", "",
        "## Frozen 2024 gates", "",
        f"WR >= **{100*wr_floor:.2f}%**; Exp >= **${exp_floor:+.2f}**; PF >= **{pf_floor:.3f}**; DD <= **${dd_cap:.2f}**; LS <= **{ls_cap}**; N >= 40; Net > 0.", "",
        "## 2024 result", "",
        f"N **{int(s['trades'])}**, WR **{100*wr:.2f}%**, Net **${float(s['net_pnl']):+.2f}**, Exp **${exp:+.2f}**, PF **{pf:.3f}**, DD **${dd:.2f}**, LS **{ls}**.", "",
        "## Verdict", "", f"**{verdict}**", "",
    ]
    if passed:
        lines.append("The H04 edge survived 2022 Development → 2023 local stability → one-shot 2024 confirmation with acceptable degradation. It is a research-qualified robust stable habitat; 2025+ remains closed final OOS/reference.")
    else:
        lines.append("The frozen H04 candidate failed at least one preregistered 2024 confirmation gate. No rescue/reselection is permitted and 2025+ remains closed.")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__": main()
