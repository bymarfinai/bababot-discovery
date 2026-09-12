#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
FROZEN_CELLS = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
STABLE_PLATEAUS = ROOT / "ETH_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
STAGEB_CELLS = ROOT / "ETH_R4B_STAGEB_2023_CELL_RESULTS.csv"
STAGEC_CELLS = ROOT / "ETH_R4B_STAGEC_2024_COMPONENT_CELL_RESULTS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGE_D_2025_FINAL_OOS_CELLS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGE_D_2025_FINAL_OOS.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGE_D_2025_Status.txt"

START = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def stats(T):
    return r1.stats_from_df(T)


def events_for_period(cache, lb: int, hold: int, rule: str):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        m = valid & (ent >= START) & (ex < END) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
            })
    return pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "clock", "gross", "net"])


def main():
    frozen = pd.read_csv(FROZEN_CELLS)
    stable = pd.read_csv(STABLE_PLATEAUS)
    b23 = pd.read_csv(STAGEB_CELLS)
    c24 = pd.read_csv(STAGEC_CELLS)

    if len(stable) != 1:
        raise AssertionError(f"Stage D requires exactly one R4b stable plateau, got {len(stable)}")

    s = stable.iloc[0]
    hour = int(s.hour_wib)
    rank = int(s.component_rank)
    rule = str(s.character_rule)
    C = frozen[
        (frozen.hour_wib == hour)
        & (frozen.component_rank == rank)
        & (frozen.character_rule.astype(str) == rule)
    ].copy()

    if hour != 4 or rule != "DRIVE_DOWN__STR_B80_100" or len(C) != 5:
        raise AssertionError(f"Unexpected final OOS target: H{hour:02d} {rule}, cells={len(C)}")
    if len(C) != int(s.component_size):
        raise AssertionError("frozen component cell count mismatch")

    expected = {(120,240),(180,240),(240,240),(180,360),(240,360)}
    actual = set(zip(C.lookback_min.astype(int), C.hold_min.astype(int)))
    if actual != expected:
        raise AssertionError(f"Frozen H04 timing set changed: {sorted(actual)}")

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if not bool((idx >= START).any()):
        raise RuntimeError("dataset contains no 2025 bars")
    if idx.max() < pd.Timestamp("2025-12-31 23:55:00", tz="UTC"):
        raise RuntimeError(f"2025 dataset incomplete; max timestamp is {idx.max()}")

    # Full prior history is retained for indicator warm-up. Only 2025 events are scored.
    x = x5[idx < END].copy()
    e12.CLOCKS = r1.clocks_for_hour(hour)
    e12.LOOKBACKS = sorted(C.lookback_min.astype(int).unique().tolist())
    e12.HOLDS = sorted(C.hold_min.astype(int).unique().tolist())
    cache = e12.prep(x)

    rows = []
    for c in C.itertuples(index=False):
        lb = int(c.lookback_min)
        hold = int(c.hold_min)
        T = events_for_period(cache, lb, hold, rule)
        st = stats(T)
        wr = float(st["win_rate"]) if finite(st["win_rate"]) else np.nan
        exp = float(st["expectancy"]) if finite(st["expectancy"]) else np.nan
        pf = float(st["pf"]) if finite(st["pf"]) else np.nan
        dd = float(st["max_dd"]) if finite(st["max_dd"]) else np.nan

        dev_wr = float(c.dev_wr)
        dev_exp = float(c.dev_exp)
        dev_pf = float(c.dev_pf)
        dev_dd = float(c.dev_dd)
        dev_ls = int(c.dev_ls)
        wr_change_pp = 100 * (wr - dev_wr) if finite(wr) else -np.inf
        exp_ret = exp / dev_exp if dev_exp > 0 and finite(exp) else -np.inf
        pf_ret = pf / dev_pf if dev_pf > 0 and finite(pf) else -np.inf
        dd_cap = min(160.0, 1.50 * dev_dd + 20.0)
        ls_warning = max(12, dev_ls + 4)

        viable = bool(
            st["trades"] >= 50
            and finite(wr) and wr >= .52
            and st["net_pnl"] > 0
            and finite(exp) and exp > 0
            and finite(pf) and pf >= 1.15
            and finite(dd) and dd <= dd_cap
        )
        strict = bool(
            viable
            and wr_change_pp >= -5.0
            and exp_ret >= .60
            and pf_ret >= .70
        )

        p23 = b23[
            (b23.hour_wib == hour)
            & (b23.component_rank == rank)
            & (b23.lookback_min == lb)
            & (b23.hold_min == hold)
        ].iloc[0]
        p24 = c24[
            (c24.hour_wib == hour)
            & (c24.component_rank == rank)
            & (c24.lookback_min == lb)
            & (c24.hold_min == hold)
        ].iloc[0]

        rows.append({
            "hour_wib": hour,
            "component_rank": rank,
            "character_rule": rule,
            "lookback_min": lb,
            "hold_min": hold,
            "dev2022_n": int(c.dev_n),
            "dev2022_wr": dev_wr,
            "dev2022_net": float(c.dev_net),
            "dev2022_exp": dev_exp,
            "dev2022_pf": dev_pf,
            "dev2022_dd": dev_dd,
            "dev2022_ls": dev_ls,
            "test2023_n": int(p23.test_n),
            "test2023_wr": float(p23.test_wr),
            "test2023_net": float(p23.test_net),
            "test2023_exp": float(p23.test_exp),
            "test2023_pf": float(p23.test_pf),
            "y2024_n": int(p24.y2024_n),
            "y2024_wr": float(p24.y2024_wr),
            "y2024_net": float(p24.y2024_net),
            "y2024_exp": float(p24.y2024_exp),
            "y2024_pf": float(p24.y2024_pf),
            "oos2025_n": int(st["trades"]),
            "oos2025_wr": wr,
            "oos2025_net": float(st["net_pnl"]),
            "oos2025_exp": exp,
            "oos2025_pf": pf,
            "oos2025_dd": dd,
            "oos2025_ls": int(st["max_loss_streak"]),
            "wr_change_vs_2022_pp": wr_change_pp,
            "exp_retention_vs_2022": exp_ret,
            "pf_retention_vs_2022": pf_ret,
            "dd_cap": dd_cap,
            "ls_warning_threshold": ls_warning,
            "risk_clustering_warning": bool(st["max_loss_streak"] > ls_warning),
            "economically_viable_2025": viable,
            "strict_stable_vs_2022_2025": strict,
        })

    R = pd.DataFrame(rows).sort_values(["hold_min", "lookback_min"]).reset_index(drop=True)
    R.to_csv(OUT_CELLS, index=False)

    n = len(R)
    viable_n = int(R.economically_viable_2025.sum())
    strict_n = int(R.strict_stable_vs_2022_2025.sum())
    median_wr = float(R.oos2025_wr.median())
    median_exp = float(R.oos2025_exp.median())
    median_pf = float(R.oos2025_pf.median())
    total_net = float(R.oos2025_net.sum())
    max_dd = float(R.oos2025_dd.max())

    if viable_n / n >= .50 and median_exp > 0 and median_pf >= 1.15:
        verdict = "FINAL_OOS_PLATEAU_PASS"
    elif viable_n >= 2 or (median_exp > 0 and median_pf > 1.00):
        verdict = "PARTIAL_FINAL_OOS_PERSISTENCE"
    else:
        verdict = "FINAL_OOS_PLATEAU_FAIL"

    lines = [
        "# ETH R4b — Stage D 2025 Final Full-Year OOS", "",
        "**2025 FINAL FULL-YEAR OOS. FROZEN H04 PLATEAU ONLY. NO RESELECTION. 2026 REMAINS CLOSED.**", "",
        f"Frozen plateau: **H{hour:02d} {rule}**, component rank **{rank}**, size **{n}**.",
        f"2025 economically viable cells: **{viable_n}/{n}**; strict-stable vs 2022: **{strict_n}/{n}**.",
        f"2025 component medians: WR **{100*median_wr:.2f}%**, Exp **${median_exp:+.2f}**, PF **{median_pf:.3f}**.",
        f"Sum of per-cell Net (descriptive, overlapping variants): **${total_net:+.2f}**; max cell DD **${max_dd:.2f}**.",
        f"Final OOS verdict: **{verdict}**.", "",
        "| LB/Hold | 2022 WR/Exp/PF | 2023 WR/Exp/PF | 2024 WR/Exp/PF | 2025 N | 2025 WR | Net | Exp | PF | DD | LS | Viable | Strict retain | Risk warn |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|",
    ]
    for r in R.itertuples(index=False):
        lines.append(
            f"| LB{int(r.lookback_min)}/H{int(r.hold_min)} | "
            f"{100*float(r.dev2022_wr):.2f}% / ${float(r.dev2022_exp):+.2f} / {float(r.dev2022_pf):.3f} | "
            f"{100*float(r.test2023_wr):.2f}% / ${float(r.test2023_exp):+.2f} / {float(r.test2023_pf):.3f} | "
            f"{100*float(r.y2024_wr):.2f}% / ${float(r.y2024_exp):+.2f} / {float(r.y2024_pf):.3f} | "
            f"{int(r.oos2025_n)} | {100*float(r.oos2025_wr):.2f}% | ${float(r.oos2025_net):+.2f} | ${float(r.oos2025_exp):+.2f} | {float(r.oos2025_pf):.3f} | ${float(r.oos2025_dd):.2f} | {int(r.oos2025_ls)} | "
            f"{'Y' if r.economically_viable_2025 else 'N'} | {'Y' if r.strict_stable_vs_2022_2025 else 'N'} | {'Y' if r.risk_clustering_warning else 'N'} |"
        )

    lines += [
        "",
        "The verdict is based on the entire five-cell frozen plateau, not a post-hoc best 2025 coordinate.",
        "The per-cell Net sum is descriptive only because timing variants overlap and is not a portfolio PnL.",
        "2026 remains unopened and is not used anywhere in this stage.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(verdict + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
