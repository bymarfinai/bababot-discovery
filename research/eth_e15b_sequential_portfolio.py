#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E15B_SEQUENTIAL_PORTFOLIO"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv"
OUT_ACCEPTED = ROOT / f"{PFX}_Accepted.csv"
OUT_BLOCKED = ROOT / f"{PFX}_Blocked.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_YEARS = ROOT / f"{PFX}_Years.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

# Frozen directly from the two formal E15A max-6h Development PASS components.
COMPONENTS = (
    {"component": "01WIB_H6", "hour_wib": 1, "lookback_min": 240, "hold_min": 360,
     "rule": "RV_HIGH__RANGE_MID", "expected_n": 247},
    {"component": "03WIB_H4", "hour_wib": 3, "lookback_min": 360, "hold_min": 240,
     "rule": "RV_HIGH__RANGE_MID", "expected_n": 250},
)
YEARS = (2022, 2023, 2024)


def clocks_for_hour(h: int):
    base = ((h - 7) % 24) * 60
    return tuple((base + q) % 1440 for q in (0, 15, 30, 45))


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def extract_component(x5, spec):
    pa, pz = e12.base.PARTS["development"]
    rows = []
    lb = int(spec["lookback_min"])
    hold = int(spec["hold_min"])
    rule = spec["rule"]
    for clock in clocks_for_hour(int(spec["hour_wib"])):
        S = e12.e11.state_frame(x5, clock, lb)
        ent = pd.DatetimeIndex(S.entry_ts)
        pre = pd.DatetimeIndex(S.pre_ts)
        masks = e12.masks_for_frame(S)
        ex, valid, xp, delta, _ = e12.e3.hold_base(x5, S, hold)
        ex = pd.DatetimeIndex(ex)
        m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for i, (entry_ts, exit_ts, g, n) in enumerate(zip(ent[m], ex[m], gross, net)):
            rows.append({
                "component": spec["component"],
                "hour_wib": int(spec["hour_wib"]),
                "anchor_utc_min": int(clock),
                "lookback_min": lb,
                "hold_min": hold,
                "character_rule": rule,
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "gross": float(g),
                "net": float(n),
            })
    T = pd.DataFrame(rows).sort_values(["entry_ts", "anchor_utc_min"]).reset_index(drop=True)
    if len(T) != int(spec["expected_n"]):
        raise AssertionError(f"{spec['component']} extraction mismatch: {len(T)} != {spec['expected_n']}")
    return T


def stats(T: pd.DataFrame):
    if len(T) == 0:
        return e12.summarize(np.array([]), np.array([]))
    return e12.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def replay_flat(T: pd.DataFrame):
    T = T.sort_values(["entry_ts", "hour_wib", "anchor_utc_min"]).reset_index(drop=True)
    accepted = []
    blocked = []
    open_until = None
    for r in T.itertuples(index=False):
        entry = pd.Timestamp(r.entry_ts)
        exit_ = pd.Timestamp(r.exit_ts)
        if open_until is None or entry >= open_until:
            accepted.append(r._asdict())
            open_until = exit_
        else:
            d = r._asdict()
            d["blocked_by_open_until"] = open_until
            blocked.append(d)
    A = pd.DataFrame(accepted)
    B = pd.DataFrame(blocked)
    return A, B


def summary_row(name, source, accepted, blocked):
    s = stats(accepted)
    return {
        "replay": name,
        "source_signals": int(len(source)),
        "accepted_trades": int(len(accepted)),
        "blocked_signals": int(len(blocked)),
        "blocked_pct": (len(blocked) / len(source)) if len(source) else np.nan,
        "win_rate": s["win_rate"],
        "net_pnl": s["net_pnl"],
        "expectancy": s["expectancy"],
        "pf": s["pf"],
        "max_dd": s["max_dd"],
        "max_loss_streak": int(s["max_loss_streak"]),
        "max_win_streak": int(s["max_win_streak"]),
    }


def year_rows(replay_name, T):
    out = []
    years = pd.DatetimeIndex(T.entry_ts).year if len(T) else np.array([], int)
    for y in YEARS:
        Y = T.loc[years == y].copy() if len(T) else T.copy()
        s = stats(Y)
        out.append({
            "replay": replay_name, "year": y, "trades": int(s["trades"]),
            "win_rate": s["win_rate"], "net_pnl": s["net_pnl"],
            "expectancy": s["expectancy"], "pf": s["pf"],
            "max_dd": s["max_dd"], "max_loss_streak": int(s["max_loss_streak"]),
        })
    return out


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")

    parts = [extract_component(x5, spec) for spec in COMPONENTS]
    E = pd.concat(parts, ignore_index=True).sort_values(["entry_ts", "hour_wib", "anchor_utc_min"]).reset_index(drop=True)
    E.to_csv(OUT_EVENTS, index=False)

    replays = []
    all_acc = []
    all_blk = []
    years = []

    # Individual flat-only replays expose within-hour anchor overlap.
    for spec, T in zip(COMPONENTS, parts):
        A, B = replay_flat(T)
        name = f"{spec['component']}_FLAT_ONLY"
        replays.append(summary_row(name, T, A, B))
        years += year_rows(name, A)
        if len(A):
            X = A.copy(); X.insert(0, "replay", name); all_acc.append(X)
        if len(B):
            X = B.copy(); X.insert(0, "replay", name); all_blk.append(X)

    # Combined chronological one-position replay. No future knowledge and no priority override:
    # the earliest eligible signal enters; all later signals while occupied are blocked.
    A, B = replay_flat(E)
    combined_name = "01WIB_H6_PLUS_03WIB_H4_FLAT_ONLY"
    replays.append(summary_row(combined_name, E, A, B))
    years += year_rows(combined_name, A)
    if len(A):
        X = A.copy(); X.insert(0, "replay", combined_name); all_acc.append(X)
    if len(B):
        X = B.copy(); X.insert(0, "replay", combined_name); all_blk.append(X)

    # Independent pooled baseline is diagnostic only; it intentionally allows overlap.
    independent_name = "INDEPENDENT_POOLED_DIAGNOSTIC"
    replays.append(summary_row(independent_name, E, E, E.iloc[0:0].copy()))
    years += year_rows(independent_name, E)

    S = pd.DataFrame(replays)
    Y = pd.DataFrame(years)
    S.to_csv(OUT_SUMMARY, index=False)
    Y.to_csv(OUT_YEARS, index=False)
    pd.concat(all_acc, ignore_index=True).to_csv(OUT_ACCEPTED, index=False)
    pd.concat(all_blk, ignore_index=True).to_csv(OUT_BLOCKED, index=False)

    c = S[S.replay == combined_name].iloc[0]
    cy = Y[Y.replay == combined_name]
    contrib = A.groupby("component").size().to_dict() if len(A) else {}
    blocked_by = B.groupby("component").size().to_dict() if len(B) else {}

    # E15B is a preservation test, not a new search. The gate is fixed before results:
    # positive pooled economics, WR>=55, PF>=1.20, exp>=0.50, DD<=125, LS<=8,
    # and every Development year must remain positive expectancy/PF>1 with >=20 trades.
    year_ok = bool(len(cy) == 3 and ((cy.trades >= 20) & (cy.expectancy > 0) & (cy.pf > 1.0)).all())
    survival = bool(
        c.accepted_trades >= 90 and np.isfinite(c.win_rate) and c.win_rate >= .55 and
        c.net_pnl > 0 and np.isfinite(c.expectancy) and c.expectancy >= .50 and
        np.isfinite(c.pf) and c.pf >= 1.20 and np.isfinite(c.max_dd) and c.max_dd <= 125 and
        c.max_loss_streak <= 8 and year_ok
    )
    status = "ETH_E15B_SEQUENTIAL_SURVIVES" if survival else "ETH_E15B_SEQUENTIAL_DOES_NOT_PASS_FROZEN_GATE"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH E15B — Sequential / One-Position Portfolio Replay", "",
        "**Status:** Development-only. OOS CLOSED. No live authorization.", "",
        "## Frozen question", "",
        "Do the two formal E15A max-6h LONG components remain economically valid after overlapping anchor signals and cross-hour position overlap are removed by a realistic one-position-at-a-time replay?", "",
        "## Frozen inputs", "",
        "- 01:00–02:00 WIB: `RV_HIGH__RANGE_MID / LB240 / H360`.",
        "- 03:00–04:00 WIB: `RV_HIGH__RANGE_MID / LB360 / H240`.",
        "- Same ETHUSDT 5m source, Development partition (2022/2023/2024), $500 notional and $0.75 fee as E12/E15A.",
        "- Entry policy: chronological earliest eligible signal while flat; every later signal before the active trade exits is blocked.",
        "- No future knowledge, no signal replacement, no OOS exposure.", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.", "",
        "## Replay results", "",
        "| Replay | Source | Accepted | Blocked | Blocked % | WR | Net | Exp | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.replay} | {int(r.source_signals)} | {int(r.accepted_trades)} | {int(r.blocked_signals)} | "
            f"{pct(r.blocked_pct)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | "
            f"{float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} |"
        )
    lines += ["", "## Combined sequential year stability", "",
              "| Year | N | WR | Net | Exp | PF | DD | LS |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in cy.itertuples(index=False):
        lines.append(f"| {int(r.year)} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} |")
    lines += [
        "", "## Portfolio mechanics", "",
        f"Accepted contribution: **01WIB_H6={int(contrib.get('01WIB_H6', 0))}**, **03WIB_H4={int(contrib.get('03WIB_H4', 0))}**.",
        f"Blocked signals: **01WIB_H6={int(blocked_by.get('01WIB_H6', 0))}**, **03WIB_H4={int(blocked_by.get('03WIB_H4', 0))}**.", "",
        "## Frozen preservation gate", "",
        "Combined sequential replay requires N>=90, WR>=55%, net>0, expectancy>=+$0.50/trade, PF>=1.20, DD<= $125, max loss streak<=8, plus each Development year N>=20 with positive expectancy and PF>1.0.", "",
        "## Verdict", "",
        f"**{status}**", "",
        "This is a preservation test of the already-selected E15A components, not a new optimization search.",
        "Research/shadow only. OOS remains closed and nothing here authorizes live deployment.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
