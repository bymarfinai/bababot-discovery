#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
COHORT_PATH = ROOT / "ETH_R4_STAGEA_2022_FROZEN_COHORT.csv"
OUT_NEIGHBORS = ROOT / "ETH_R4_STAGEB_2023_CANDIDATE_NEIGHBORHOODS.csv"
OUT_VERDICTS = ROOT / "ETH_R4_STAGEB_2023_CANDIDATE_VERDICTS.csv"
OUT_SURVIVORS = ROOT / "ETH_R4_STAGEB_2023_SURVIVORS.csv"
OUT_RESULT = ROOT / "ETH_R4_STAGEB_2023_COHORT_SCREEN.md"
OUT_STATUS = ROOT / "ETH_R4_STAGEB_2023_Status.txt"

LOOKBACKS = list(r1.LOOKBACKS)
HOLDS = list(r1.HOLDS)
START = pd.Timestamp("2023-01-01", tz="UTC")
END = pd.Timestamp("2024-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T)


def main():
    if not COHORT_PATH.exists():
        raise FileNotFoundError(COHORT_PATH)
    cohort = pd.read_csv(COHORT_PATH)
    if cohort.empty:
        raise AssertionError("frozen R4 cohort is empty")
    if sorted(cohort.hour_wib.unique().tolist()) != list(range(24)):
        raise AssertionError("frozen R4 cohort does not cover all 24 WIB hours")

    li = {v: i for i, v in enumerate(LOOKBACKS)}
    hi = {v: i for i, v in enumerate(HOLDS)}

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x23 = x5[(idx >= START) & (idx < END)].copy()

    all_rows = []
    verdict_rows = []
    survivor_rows = []

    for hour in range(24):
        H = cohort[cohort.hour_wib == hour].sort_values("candidate_rank").copy()
        e12.CLOCKS = r1.clocks_for_hour(hour)
        e12.LOOKBACKS = LOOKBACKS
        e12.HOLDS = HOLDS
        cache = e12.prep(x23)

        for c in H.itertuples(index=False):
            rule = str(c.character_rule)
            dev_lb = int(c.lookback_min); dev_hold = int(c.hold_min)
            dev_wr = float(c.wr); dev_exp = float(c.exp); dev_pf = float(c.pf)
            dev_dd = float(c.dd); dev_ls = int(c.ls)
            di, dj = li[dev_lb], hi[dev_hold]
            coords = []
            for lb in LOOKBACKS:
                for hold in HOLDS:
                    dist = abs(li[lb] - di) + abs(hi[hold] - dj)
                    if dist <= 1:
                        coords.append((int(lb), int(hold), int(dist)))

            dd_cap = min(160.0, 1.50 * dev_dd + 20.0)
            ls_warning = max(12, dev_ls + 4)
            local_rows = []
            for lb, hold, dist in coords:
                T = r1.candidate_events(cache, lb, hold, rule)
                s = stats(T)
                wr = float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
                exp = float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
                pf = float(s["pf"]) if finite(s["pf"]) else np.nan
                dd = float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
                wr_change_pp = 100.0 * (wr - dev_wr) if finite(wr) else -np.inf
                exp_ret = exp / dev_exp if dev_exp > 0 and finite(exp) else -np.inf
                pf_ret = pf / dev_pf if dev_pf > 0 and finite(pf) else -np.inf
                viable = bool(
                    s["trades"] >= 50 and finite(wr) and wr >= .52 and s["net_pnl"] > 0 and
                    finite(exp) and exp > 0 and finite(pf) and pf >= 1.15 and
                    finite(dd) and dd <= dd_cap
                )
                stable = bool(
                    viable and wr_change_pp >= -5.0 and exp_ret >= .60 and pf_ret >= .70
                )
                row = {
                    "hour_wib": hour,
                    "candidate_rank": int(c.candidate_rank),
                    "character_rule": rule,
                    "dev_lb": dev_lb,
                    "dev_hold": dev_hold,
                    "test_lb": lb,
                    "test_hold": hold,
                    "manhattan_distance": dist,
                    "dev_n": int(c.trades),
                    "dev_wr": dev_wr,
                    "dev_exp": dev_exp,
                    "dev_pf": dev_pf,
                    "dev_dd": dev_dd,
                    "dev_ls": dev_ls,
                    "strict_support_count_2022": int(c.strict_support_count),
                    "economic_support_count_2022": int(c.economic_support_count),
                    "test_n": int(s["trades"]),
                    "test_wr": wr,
                    "test_net": float(s["net_pnl"]),
                    "test_exp": exp,
                    "test_pf": pf,
                    "test_dd": dd,
                    "test_ls": int(s["max_loss_streak"]),
                    "wr_change_pp": wr_change_pp,
                    "exp_retention": exp_ret,
                    "pf_retention": pf_ret,
                    "dd_cap": dd_cap,
                    "ls_warning_threshold": ls_warning,
                    "risk_clustering_warning": bool(s["max_loss_streak"] > ls_warning),
                    "economically_viable": viable,
                    "performance_stable": stable,
                }
                local_rows.append(row)
                all_rows.append(row)

            N = pd.DataFrame(local_rows)
            viable = N[N.economically_viable].copy()
            stable = N[N.performance_stable].copy()
            exact = N[(N.test_lb == dev_lb) & (N.test_hold == dev_hold)].iloc[0]

            if len(stable) >= 1 and len(viable) >= 2:
                verdict = "STABLE_EDGE_FROZEN"
                S = stable.sort_values(
                    ["manhattan_distance", "exp_retention", "wr_change_pp", "test_pf", "test_dd", "test_ls", "test_hold", "test_lb"],
                    ascending=[True, False, False, False, True, True, True, True],
                    kind="mergesort",
                ).iloc[0]
                survivor_rows.append({
                    "hour_wib": hour,
                    "candidate_rank": int(c.candidate_rank),
                    "character_rule": rule,
                    "dev_lb": dev_lb,
                    "dev_hold": dev_hold,
                    "dev_n": int(c.trades),
                    "dev_wr": dev_wr,
                    "dev_exp": dev_exp,
                    "dev_pf": dev_pf,
                    "dev_dd": dev_dd,
                    "dev_ls": dev_ls,
                    "plateau_strict_support_2022": int(c.strict_support_count),
                    "plateau_economic_support_2022": int(c.economic_support_count),
                    "test_lb": int(S.test_lb),
                    "test_hold": int(S.test_hold),
                    "test_distance": int(S.manhattan_distance),
                    "test_n": int(S.test_n),
                    "test_wr": float(S.test_wr),
                    "test_net": float(S.test_net),
                    "test_exp": float(S.test_exp),
                    "test_pf": float(S.test_pf),
                    "test_dd": float(S.test_dd),
                    "test_ls": int(S.test_ls),
                    "wr_change_pp": float(S.wr_change_pp),
                    "exp_retention": float(S.exp_retention),
                    "pf_retention": float(S.pf_retention),
                    "local_viable_cells": int(len(viable)),
                    "local_stable_cells": int(len(stable)),
                    "risk_clustering_warning": bool(S.risk_clustering_warning),
                    "validation_2024_opened": False,
                })
            elif len(stable) >= 1:
                verdict = "LOCAL_NEIGHBORHOOD_FAIL"
            else:
                verdict = "TEST_DEGRADATION_FAIL"

            verdict_rows.append({
                "hour_wib": hour,
                "candidate_rank": int(c.candidate_rank),
                "character_rule": rule,
                "dev_lb": dev_lb,
                "dev_hold": dev_hold,
                "dev_wr": dev_wr,
                "dev_exp": dev_exp,
                "dev_pf": dev_pf,
                "plateau_strict_support_2022": int(c.strict_support_count),
                "plateau_economic_support_2022": int(c.economic_support_count),
                "exact_test_n": int(exact.test_n),
                "exact_test_wr": float(exact.test_wr),
                "exact_test_net": float(exact.test_net),
                "exact_test_exp": float(exact.test_exp),
                "exact_test_pf": float(exact.test_pf),
                "exact_test_dd": float(exact.test_dd),
                "exact_test_ls": int(exact.test_ls),
                "local_viable_cells": int(len(viable)),
                "local_stable_cells": int(len(stable)),
                "verdict": verdict,
            })

    NEI = pd.DataFrame(all_rows)
    VER = pd.DataFrame(verdict_rows).sort_values(["hour_wib", "candidate_rank"]).reset_index(drop=True)
    SUR = pd.DataFrame(survivor_rows)
    if not SUR.empty:
        SUR = SUR.sort_values(["hour_wib", "candidate_rank"]).reset_index(drop=True)

    NEI.to_csv(OUT_NEIGHBORS, index=False)
    VER.to_csv(OUT_VERDICTS, index=False)
    SUR.to_csv(OUT_SURVIVORS, index=False)

    survivor_hours = sorted(SUR.hour_wib.unique().tolist()) if not SUR.empty else []
    lines = [
        "# ETH R4 — Stage B 2023 Frozen-Cohort Screen", "",
        "**R4 COHORT WAS FROZEN FROM 2022 BEFORE THIS SCREEN. 2024 NOT OPENED HERE. 2025-2026 CLOSED.**", "",
        f"Candidates tested: **{len(VER)}**. Formal stable survivors: **{len(SUR)}** across **{len(survivor_hours)}** WIB hours.",
        f"Survivor hours: **{', '.join(f'H{h:02d}' for h in survivor_hours) if survivor_hours else 'NONE'}**.", "",
        "| Hour | Rank | Character | Dev timing | Dev WR | Dev Exp | 2023 exact WR | Exact Exp | Exact PF | Viable local | Stable local | Verdict |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in VER.itertuples(index=False):
        lines.append(
            f"| H{int(r.hour_wib):02d} | {int(r.candidate_rank)} | {r.character_rule} | LB{int(r.dev_lb)}/H{int(r.dev_hold)} | "
            f"{100*float(r.dev_wr):.2f}% | ${float(r.dev_exp):+.2f} | {100*float(r.exact_test_wr):.2f}% | "
            f"${float(r.exact_test_exp):+.2f} | {float(r.exact_test_pf):.3f} | {int(r.local_viable_cells)} | {int(r.local_stable_cells)} | {r.verdict} |"
        )

    if not SUR.empty:
        lines += ["", "## Frozen R4 survivors eligible for a separate 2024 confirmation", "",
                  "| Hour | Rank | Character | 2022 center | Frozen 2023 coordinate | 2023 WR | Exp | PF | Viable/Stable local |", 
                  "|---:|---:|---|---|---|---:|---:|---:|---:|"]
        for r in SUR.itertuples(index=False):
            lines.append(
                f"| H{int(r.hour_wib):02d} | {int(r.candidate_rank)} | {r.character_rule} | LB{int(r.dev_lb)}/H{int(r.dev_hold)} | "
                f"LB{int(r.test_lb)}/H{int(r.test_hold)} | {100*float(r.test_wr):.2f}% | ${float(r.test_exp):+.2f} | {float(r.test_pf):.3f} | "
                f"{int(r.local_viable_cells)}/{int(r.local_stable_cells)} |"
            )

    lines += ["", "No failed cohort member may be replaced or rescued after observing these 2023 results."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("ETH_R4_STAGEB_COMPLETE\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
