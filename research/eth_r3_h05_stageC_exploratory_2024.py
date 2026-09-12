#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
DEV_LOCK = ROOT / "ETH_R3_H05_STAGEA_FrozenDevCandidate.csv"
TEST_NEIGHBOR = ROOT / "ETH_R3_H05_STAGEB_2023_LocalNeighborhood.csv"
OUT_EVENTS = ROOT / "ETH_R3_H05_STAGEC_2024_Events.csv"
OUT_NEIGHBOR = ROOT / "ETH_R3_H05_STAGEC_2024_LocalNeighborhood.csv"
OUT_RESULT = ROOT / "ETH_R3_H05_STAGEC_Exploratory2024_Result.md"
OUT_STATUS = ROOT / "ETH_R3_H05_STAGEC_Exploratory2024_Status.txt"

HOUR_WIB = 5
START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")


def finite(x):
    return bool(np.isfinite(x))


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T)


def events_for_period(cache, lb: int, hold: int, rule: str) -> pd.DataFrame:
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        # Explicit 2024 scoring window. Do not reuse r1.candidate_events(), whose
        # original training helper is hard-wired to TRAIN_END=2024-01-01.
        m = valid & (ent >= START) & (ex < END) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "lookback_min": int(lb),
                "hold_min": int(hold),
                "gross": float(g),
                "net": float(n),
            })
    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "lookback_min", "hold_min", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def main():
    if not DEV_LOCK.exists():
        raise FileNotFoundError(DEV_LOCK)
    if not TEST_NEIGHBOR.exists():
        raise FileNotFoundError(TEST_NEIGHBOR)

    dev = pd.read_csv(DEV_LOCK).iloc[0]
    n23 = pd.read_csv(TEST_NEIGHBOR)
    rule = str(dev.character_rule)
    dev_lb = int(dev.dev_lb)
    dev_hold = int(dev.dev_hold)
    dev_wr = float(dev.dev_wr)
    dev_exp = float(dev.dev_exp)
    dev_pf = float(dev.dev_pf)
    dev_net = float(dev.dev_net)
    dev_dd = float(dev.dev_dd)
    dev_ls = int(dev.dev_ls)

    coords = [
        (int(r.lookback_min), int(r.hold_min), int(r.manhattan_distance))
        for r in n23.itertuples(index=False)
    ]
    expected = {(180, 240), (120, 240), (180, 120), (180, 360), (240, 240)}
    if {(lb, hold) for lb, hold, _ in coords} != expected:
        raise AssertionError(f"2023 neighborhood drifted: {coords}")

    exact23 = n23[(n23.lookback_min == dev_lb) & (n23.hold_min == dev_hold)].iloc[0]

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    # Keep all causal history before 2025 for indicator warm-up; score only 2024 entries/exits.
    x = x5[idx < END].copy()
    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = sorted({lb for lb, _, _ in coords})
    e12.HOLDS = sorted({hold for _, hold, _ in coords})
    cache = e12.prep(x)

    dd_cap = min(160.0, 1.50 * dev_dd + 20.0)
    ls_warning = max(12, dev_ls + 4)
    rows = []
    all_events = []
    for lb, hold, dist in coords:
        T = events_for_period(cache, lb, hold, rule)
        if len(T):
            all_events.append(T)
        s = stats(T)
        wr = float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
        exp = float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
        pf = float(s["pf"]) if finite(s["pf"]) else np.nan
        dd = float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
        viable = bool(
            s["trades"] >= 50 and finite(wr) and wr >= .52 and s["net_pnl"] > 0 and
            finite(exp) and exp > 0 and finite(pf) and pf >= 1.15 and
            finite(dd) and dd <= dd_cap
        )
        rows.append({
            "character_rule": rule,
            "lookback_min": lb,
            "hold_min": hold,
            "manhattan_distance": dist,
            "trades": int(s["trades"]),
            "wr": wr,
            "net": float(s["net_pnl"]),
            "exp": exp,
            "pf": pf,
            "dd": dd,
            "ls": int(s["max_loss_streak"]),
            "dd_cap": dd_cap,
            "ls_warning_threshold": ls_warning,
            "risk_clustering_warning": bool(s["max_loss_streak"] > ls_warning),
            "economically_viable": viable,
            "exp_retention_vs_2022": exp / dev_exp if dev_exp > 0 and finite(exp) else np.nan,
            "pf_retention_vs_2022": pf / dev_pf if dev_pf > 0 and finite(pf) else np.nan,
            "wr_change_vs_2022_pp": 100.0 * (wr - dev_wr) if finite(wr) else np.nan,
        })

    D = pd.DataFrame(rows).sort_values(["manhattan_distance", "lookback_min", "hold_min"]).reset_index(drop=True)
    D.to_csv(OUT_NEIGHBOR, index=False)
    if all_events:
        pd.concat(all_events, ignore_index=True).sort_values(["lookback_min", "hold_min", "entry_ts", "clock"]).to_csv(OUT_EVENTS, index=False)
    else:
        pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "lookback_min", "hold_min", "gross", "net"]).to_csv(OUT_EVENTS, index=False)

    exact24 = D[(D.lookback_min == dev_lb) & (D.hold_min == dev_hold)].iloc[0]
    local_viable = int(D.economically_viable.sum())
    status = "ETH_R3_H05_EXPLORATORY_2024_DIAGNOSTIC_COMPLETE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH R3 H05 — Exploratory 2024 Diagnostic", "",
        "**EXPLORATORY ONLY. FORMAL 2023 STAGE-B VERDICT REMAINS TEST_DEGRADATION_FAIL. 2025+ CLOSED.**", "",
        f"Frozen character: **{rule}**. Development coordinate: **LB{dev_lb} / H{dev_hold}**.",
        f"2024 evaluated only the same 5-cell one-step neighborhood already fixed before this run. No 2024 reselection is permitted.",
        f"Source coverage: {coverage:.4%}. Stage-B DD envelope reused: **${dd_cap:.2f}**. LS warning threshold: **{ls_warning}** (diagnostic only).", "",
        "## Exact coordinate three-year comparison", "",
        "| Period | N | WR | Net | Exp | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| 2022 Development | {int(dev.dev_n)} | {100*dev_wr:.2f}% | ${dev_net:+.2f} | ${dev_exp:+.2f} | {dev_pf:.3f} | ${dev_dd:.2f} | {dev_ls} |",
        f"| 2023 Test exact | {int(exact23.trades)} | {100*float(exact23.wr):.2f}% | ${float(exact23.net):+.2f} | ${float(exact23.exp):+.2f} | {float(exact23.pf):.3f} | ${float(exact23.dd):.2f} | {int(exact23.ls)} |",
        f"| 2024 Exploratory exact | {int(exact24.trades)} | {100*float(exact24.wr):.2f}% | ${float(exact24.net):+.2f} | ${float(exact24.exp):+.2f} | {float(exact24.pf):.3f} | ${float(exact24.dd):.2f} | {int(exact24.ls)} |", "",
        "## Fixed local neighborhood in 2024", "",
        "| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | Exp retain vs 2022 | Viable | Risk warn |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for r in D.itertuples(index=False):
        lines.append(
            f"| {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.manhattan_distance)} | {int(r.trades)} | "
            f"{100*float(r.wr):.2f}% | ${float(r.net):+.2f} | ${float(r.exp):+.2f} | {float(r.pf):.3f} | "
            f"${float(r.dd):.2f} | {int(r.ls)} | {100*float(r.exp_retention_vs_2022):.1f}% | "
            f"{'Y' if r.economically_viable else 'N'} | {'Y' if r.risk_clustering_warning else 'N'} |"
        )

    lines += [
        "", "## Diagnostic summary", "",
        f"2024 economically viable local cells: **{local_viable}/{len(D)}**.",
        f"Exact coordinate 2024 economically viable: **{'YES' if bool(exact24.economically_viable) else 'NO'}**.",
        "This stage is descriptive and cannot retroactively change the preregistered 2023 Stage-B fail into a formal validation pass.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
