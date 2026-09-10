#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e3_drive_strength_fast as e3
import eth_economic_first_e6_lowdrive_management as e6

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E7_HARVEST_RIDGE"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

TPS = (0.0050, 0.0055, 0.0060, 0.0065, 0.0070, 0.0075, 0.0080)
HOLDS = (540, 600, 660, 720, 780, 840, 900)

SEED = {
    "trades": 153,
    "win_rate": 0.784313725,
    "net_pnl": 64.300335,
    "expectancy": 0.420264,
    "pf": 1.321183,
    "max_dd": 44.427636,
    "max_loss_streak": 4,
    "positive_blocks": 4,
}


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def approx(a, b, tol=1e-5):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def dev_scan(x5):
    rows = []
    for tp in TPS:
        for hold in HOLDS:
            s, _ = e6.simulate(x5, "development", tp, None, hold, False)
            rows.append({"tp_pct": tp, "hold_min": hold, **s})
    D = pd.DataFrame(rows)
    if len(D) != 49:
        raise AssertionError(f"expected 49 candidates, got {len(D)}")

    seed = D[(np.isclose(D.tp_pct, 0.0060)) & (D.hold_min == 720)].iloc[0]
    checks = {
        "trades": int(seed.trades) == SEED["trades"],
        "win_rate": approx(seed.win_rate, SEED["win_rate"]),
        "net_pnl": approx(seed.net_pnl, SEED["net_pnl"]),
        "expectancy": approx(seed.expectancy, SEED["expectancy"]),
        "pf": approx(seed.pf, SEED["pf"]),
        "max_dd": approx(seed.max_dd, SEED["max_dd"]),
        "max_loss_streak": int(seed.max_loss_streak) == SEED["max_loss_streak"],
        "positive_blocks": int(seed.positive_blocks) == SEED["positive_blocks"],
    }
    if not all(checks.values()):
        raise AssertionError(f"E6 seed reproduction failed: {checks}; observed={seed.to_dict()}")

    D["ridge_gate"] = (
        (D.trades >= 140) &
        (D.win_rate >= 0.75) &
        (D.net_pnl > 0) &
        (D.expectancy >= 0.40) &
        (D.pf >= 1.20) &
        (D.max_dd <= 60.0) &
        (D.max_loss_streak <= 5) &
        (D.positive_blocks >= 3)
    )
    return D


def key(tp, hold):
    return (round(float(tp), 6), int(hold))


def neighbors(tp, hold):
    ti = TPS.index(float(tp)); hi = HOLDS.index(int(hold)); out = []
    if ti > 0: out.append(key(TPS[ti-1], hold))
    if ti + 1 < len(TPS): out.append(key(TPS[ti+1], hold))
    if hi > 0: out.append(key(tp, HOLDS[hi-1]))
    if hi + 1 < len(HOLDS): out.append(key(tp, HOLDS[hi+1]))
    return out


def build(D):
    D = D.copy()
    lookup = {key(r.tp_pct, r.hold_min): r for r in D.itertuples(index=False)}
    nav, ns, stable = [], [], []
    for r in D.itertuples(index=False):
        ks = neighbors(r.tp_pct, r.hold_min)
        sup = 0
        for k in ks:
            x = lookup[k]
            ok = (
                int(x.trades) >= 140 and
                float(x.win_rate) >= 0.70 and
                float(x.expectancy) >= 0.20 and
                float(x.net_pnl) > 0 and
                float(x.pf) >= 1.10 and
                float(x.max_dd) <= 80.0 and
                int(x.positive_blocks) >= 2
            )
            sup += int(ok)
        need = 2 if len(ks) >= 3 else 1
        nav.append(len(ks)); ns.append(sup); stable.append(sup >= need)
    D["neighbors_available"] = nav
    D["neighbors_supportive"] = ns
    D["local_stable"] = stable
    D["candidate_eligible"] = D.ridge_gate & D.local_stable
    D["boundary"] = D.tp_pct.isin((min(TPS), max(TPS))) | D.hold_min.isin((min(HOLDS), max(HOLDS)))
    C = D[D.candidate_eligible].copy().sort_values(
        ["expectancy", "win_rate", "pf", "max_dd", "max_loss_streak", "hold_min", "tp_pct"],
        ascending=[False, False, False, True, True, True, True],
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    return D, C


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low {coverage}")

    D0 = dev_scan(x5)
    D, C = build(D0)
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    seed = D[(np.isclose(D.tp_pct, 0.0060)) & (D.hold_min == 720)].iloc[0]
    lines = [
        "# ETH Economic-First E7 — High-WR Harvest Ridge Refinement Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen signal: **17:00 UTC / LB360 / causal B0_20 / MOMENTUM / exact-open entry / NO SL**.",
        "Fixed economics: **$500 notional / $0.75 round-trip fee / no compounding**.",
        f"Development candidates: **{len(D)}**.",
        f"Ridge-gate passers: **{int(D.ridge_gate.sum())}**; ridge + local-stability passers: **{len(C)}**.", "",
        "## E6 seed reproduction", "",
        f"TP0.60% / hold720m reproduced: N **{int(seed.trades)}**, WR **{pct(seed.win_rate)}**, net **{money(seed.net_pnl)}**, exp **{money(seed.expectancy)}/trade**, PF **{seed.pf:.3f}**, DD **{money(seed.max_dd)}**, loss streak **{int(seed.max_loss_streak)}**, blocks **{int(seed.positive_blocks)}/4**.", "",
        "## Development ridge atlas", "",
        "| # | TP | Hold | N | WR | Net | Exp | PF | DD | L-streak | TP/Time | Blocks | Gate | Neigh | Eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    top = D.sort_values(["expectancy", "win_rate", "pf", "max_dd"], ascending=[False, False, False, True]).head(15)
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {i} | {100*r.tp_pct:.2f}% | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.tp_exit_rate)}/{pct(r.time_exit_rate)} | {int(r.positive_blocks)}/4 | {'YES' if r.ridge_gate else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {'YES' if r.candidate_eligible else 'NO'} |"
        )

    if len(C) == 0:
        status = "ETH_ECONOMIC_FIRST_E7_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "", "No Development ridge candidate met the preregistered ridge + local-stability gates.", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    tp = float(sel.tp_pct); hold = int(sel.hold_min)
    lines += ["", "## Development-selected ridge", "",
              f"**TP {100*tp:.2f}% / NO SL / hold {hold}m**", "",
              f"N **{int(sel.trades)}**, WR **{pct(sel.win_rate)}**, net **{money(sel.net_pnl)}**, exp **{money(sel.expectancy)}/trade**, PF **{sel.pf:.3f}**, DD **{money(sel.max_dd)}**, loss streak **{int(sel.max_loss_streak)}**, blocks **{int(sel.positive_blocks)}/4**, neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**."]

    _, Tdev = e6.simulate(x5, "development", tp, None, hold, True)
    if bool(sel.boundary):
        status = "ETH_ECONOMIC_FIRST_E7_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        Tdev.to_csv(OUT_TRADES, index=False)
        lines += ["", "Winner touches a preregistered TP/hold sentinel; holdouts remain closed and no second-best is substituted.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    hrows, tlist, allok = [], [Tdev], True
    for part in ("external", "reference_validation"):
        s, T = e6.simulate(x5, part, tp, None, hold, True)
        ok = (
            s.get("trades", 0) >= 50 and
            s.get("win_rate", 0) >= 0.70 and
            s.get("net_pnl", -1) > 0 and
            s.get("expectancy", -1) > 0 and
            s.get("pf", 0) >= 1.10 and
            s.get("max_dd", 1e9) <= 100.0 and
            s.get("max_loss_streak", 99) <= 7
        )
        hrows.append({"partition": part, **s, "replication_pass": bool(ok)})
        allok = allok and bool(ok)
        tlist.append(T)

    H = pd.DataFrame(hrows)
    H.to_csv(OUT_SUMMARY, index=False)
    allT = pd.concat(tlist, ignore_index=True).sort_values("entry_ts")
    allT.to_csv(OUT_TRADES, index=False)

    status = "ETH_ECONOMIC_FIRST_E7_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E7_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")
    lines += ["", "## Historical replication", "",
              "| Partition | N | WR | Net | Exp | PF | DD | L-streak | TP/Time | Gate |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.tp_exit_rate)}/{pct(r.time_exit_rate)} | {'PASS' if r.replication_pass else 'FAIL'} |")

    sa = e3.summarize(allT.net_pnl.to_numpy(float), allT.gross_pnl.to_numpy(float), 0)
    lines += ["", "## Combined historical — descriptive", "",
              f"N **{sa['trades']}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{sa['max_loss_streak']}**.", "",
              "BTC A3.9 context: WR 56.83%, exp +$0.6887/trade, PF 1.431, DD $31.636, loss streak 4.", "",
              f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
