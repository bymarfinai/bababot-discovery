#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1
import eth_economic_first_e3_drive_strength_fast as e3
import eth_economic_first_e9_cross_era_character as e9

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E10A_FINE_REGION"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (360, 375, 390, 405, 420)  # 06:00 .. 07:00 UTC
LOOKBACKS = (180, 210, 240, 270, 300)
HOLDS = (600, 660, 720, 780, 840)
MODE = "MOMENTUM"
REGIME = "B40_60"
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def pct(x): return f"{100*float(x):.2f}%"
def money(x): return f"${float(x):+.2f}"


def summarize(net: np.ndarray, gross: np.ndarray) -> dict:
    return e9.summarize_arr(np.asarray(net, float), np.asarray(gross, float))


def candidate(x5: pd.DataFrame, clock: int, lb: int, hold: int) -> dict:
    S = e3.signal_frame(x5, clock, lb)
    ent = pd.DatetimeIndex(S.entry_ts)
    pre = pd.DatetimeIndex(S.pre_ts)
    strength = S.strength_pct.to_numpy(float)
    sign = np.where(S.drive_return.to_numpy(float) > 0, 1.0, -1.0)
    ex, valid, xp, delta, _ = e3.hold_base(x5, S, hold)
    pa, pz = base.PARTS["development"]
    rm = e9.regime_mask(strength, REGIME)
    base_dev = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & rm
    gross_all = NOTIONAL * sign * delta
    net_all = gross_all - FEE

    dev_mask = np.zeros(len(S), dtype=bool)
    ys = {}
    for y in YEARS:
        ya = pd.Timestamp(f"{y}-01-01", tz="UTC")
        yz = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
        ym = base_dev & (pre >= ya) & (ent >= ya) & (ex < yz)
        dev_mask |= ym
        ys[y] = summarize(net_all[ym], gross_all[ym])

    s = summarize(net_all[dev_mask], gross_all[dev_mask])
    row = {
        "clock_min_utc": clock, "clock_utc": hhmm(clock), "clock_wib": wib(clock),
        "lookback_min": lb, "mode": MODE, "strength_regime": REGIME, "hold_min": hold,
        **s,
    }
    for y in YEARS:
        z = ys[y]
        row.update({
            f"y{y}_trades": z.get("trades", 0),
            f"y{y}_wr": z.get("win_rate", np.nan),
            f"y{y}_net": z.get("net_pnl", 0.0),
            f"y{y}_exp": z.get("expectancy", np.nan),
            f"y{y}_pf": z.get("pf", np.nan),
        })
    return row


def scan(x5: pd.DataFrame) -> pd.DataFrame:
    rows = [candidate(x5, c, lb, h) for c in CLOCKS for lb in LOOKBACKS for h in HOLDS]
    D = pd.DataFrame(rows)
    if len(D) != 125:
        raise AssertionError(f"expected 125 candidates, got {len(D)}")
    return D


def seed_invariant(D: pd.DataFrame):
    s = D[(D.clock_min_utc == 390) & (D.lookback_min == 240) & (D.hold_min == 720)]
    if len(s) != 1:
        raise AssertionError("E9 seed missing or duplicated")
    s = s.iloc[0]
    checks = {
        "trades": (int(s.trades), 164),
        "max_loss_streak": (int(s.max_loss_streak), 5),
        "y2022_trades": (int(s.y2022_trades), 55),
        "y2023_trades": (int(s.y2023_trades), 53),
        "y2024_trades": (int(s.y2024_trades), 56),
    }
    for name, (got, exp) in checks.items():
        if got != exp:
            raise AssertionError(f"seed invariant {name}: {got} != {exp}")
    floats = {
        "win_rate": (s.win_rate, 0.6036585366),
        "net_pnl": (s.net_pnl, 513.487172),
        "expectancy": (s.expectancy, 3.131019),
        "pf": (s.pf, 1.920575),
        "max_dd": (s.max_dd, 80.879419),
        "y2022_wr": (s.y2022_wr, 0.6363636364),
        "y2022_exp": (s.y2022_exp, 5.428064),
        "y2022_pf": (s.y2022_pf, 2.291820),
        "y2023_wr": (s.y2023_wr, 0.6226415094),
        "y2023_exp": (s.y2023_exp, 3.035058),
        "y2023_pf": (s.y2023_pf, 2.355878),
        "y2024_wr": (s.y2024_wr, 0.5535714286),
        "y2024_exp": (s.y2024_exp, 0.965814),
        "y2024_pf": (s.y2024_pf, 1.259965),
    }
    for name, (got, exp) in floats.items():
        if not math.isclose(float(got), float(exp), rel_tol=0, abs_tol=1e-5):
            raise AssertionError(f"seed invariant {name}: {got} != {exp}")


def key(c, lb, h): return (int(c), int(lb), int(h))


def neighbors(r):
    c, lb, h = int(r.clock_min_utc), int(r.lookback_min), int(r.hold_min)
    ci, li, hi = CLOCKS.index(c), LOOKBACKS.index(lb), HOLDS.index(h)
    ks = []
    if ci > 0: ks.append(key(CLOCKS[ci-1], lb, h))
    if ci + 1 < len(CLOCKS): ks.append(key(CLOCKS[ci+1], lb, h))
    if li > 0: ks.append(key(c, LOOKBACKS[li-1], h))
    if li + 1 < len(LOOKBACKS): ks.append(key(c, LOOKBACKS[li+1], h))
    if hi > 0: ks.append(key(c, lb, HOLDS[hi-1]))
    if hi + 1 < len(HOLDS): ks.append(key(c, lb, HOLDS[hi+1]))
    return ks


def build(D: pd.DataFrame):
    D = D.copy()
    era_gate = np.ones(len(D), dtype=bool)
    for y in YEARS:
        era_gate &= (
            (D[f"y{y}_trades"] >= 40) &
            (D[f"y{y}_wr"] >= .52) &
            (D[f"y{y}_net"] > 0) &
            (D[f"y{y}_exp"] > 0) &
            (D[f"y{y}_pf"] >= 1.05)
        ).to_numpy(bool)
    agg = (
        (D.trades >= 140) & (D.win_rate >= .58) & (D.net_pnl > 0) &
        (D.expectancy >= 1.50) & (D.pf >= 1.40) &
        (D.max_dd <= 100) & (D.max_loss_streak <= 6)
    )
    D["era_gate"] = era_gate
    D["candidate_gate"] = agg & era_gate
    D["min_era_exp"] = D[[f"y{y}_exp" for y in YEARS]].min(axis=1)
    D["min_era_wr"] = D[[f"y{y}_wr" for y in YEARS]].min(axis=1)
    D["positive_era_count"] = sum((D[f"y{y}_net"] > 0).astype(int) for y in YEARS)

    lookup = {key(r.clock_min_utc, r.lookback_min, r.hold_min): r for r in D.itertuples(index=False)}
    avail, supportive, stable = [], [], []
    for r in D.itertuples(index=False):
        ks = neighbors(r); sup = 0
        for k in ks:
            x = lookup[k]
            ok = (
                int(x.trades) >= 140 and float(x.win_rate) >= .55 and float(x.net_pnl) > 0 and
                float(x.expectancy) >= .75 and float(x.pf) >= 1.20 and float(x.max_dd) <= 125 and
                int(x.positive_era_count) == 3
            )
            sup += int(ok)
        n = len(ks)
        need = 4 if n == 6 else max(2, math.ceil(.60 * n))
        avail.append(n); supportive.append(sup); stable.append(sup >= need)
    D["neighbors_available"] = avail
    D["neighbors_supportive"] = supportive
    D["local_stable"] = stable
    D["candidate_eligible"] = D.candidate_gate & D.local_stable
    D["boundary"] = (
        D.clock_min_utc.isin((min(CLOCKS), max(CLOCKS))) |
        D.lookback_min.isin((min(LOOKBACKS), max(LOOKBACKS))) |
        D.hold_min.isin((min(HOLDS), max(HOLDS)))
    )

    C = D[D.candidate_eligible].copy().sort_values(
        ["min_era_exp", "min_era_wr", "expectancy", "win_rate", "pf", "max_dd", "max_loss_streak", "hold_min", "lookback_min", "clock_min_utc"],
        ascending=[False, False, False, False, False, True, True, True, True, True]
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return D, C


def selected_trade_df(x5: pd.DataFrame, part: str, sel) -> pd.DataFrame:
    c = int(sel["clock_min_utc"]); lb = int(sel["lookback_min"]); h = int(sel["hold_min"])
    S = e3.signal_frame(x5, c, lb)
    ent = pd.DatetimeIndex(S.entry_ts); pre = pd.DatetimeIndex(S.pre_ts)
    strength = S.strength_pct.to_numpy(float)
    ex, valid, xp, delta, sign = e3.hold_base(x5, S, h)
    pa, pz = base.PARTS[part]
    m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & e9.regime_mask(strength, REGIME)
    if part == "development":
        same_year = np.zeros(len(S), dtype=bool)
        for y in YEARS:
            ya = pd.Timestamp(f"{y}-01-01", tz="UTC"); yz = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
            same_year |= (pre >= ya) & (ent >= ya) & (ex < yz)
        m &= same_year
    gross = NOTIONAL * sign * delta
    net = gross - FEE
    idx = np.where(m)[0]
    return pd.DataFrame({
        "partition": part,
        "clock_utc": hhmm(c), "clock_wib": wib(c),
        "lookback_min": lb, "mode": MODE, "strength_regime": REGIME, "hold_min": h,
        "pre_ts": pre[idx], "entry_ts": ent[idx], "exit_ts": ex[idx],
        "pre_price": S.pre_price.to_numpy(float)[idx], "entry_price": S.entry_price.to_numpy(float)[idx], "exit_price": xp[idx],
        "drive_return": S.drive_return.to_numpy(float)[idx], "strength_pct": strength[idx],
        "trade_side": np.where(sign[idx] > 0, "LONG", "SHORT"),
        "gross_pnl": gross[idx], "fee": FEE, "net_pnl": net[idx], "net_positive": net[idx] > 0,
    })


def stats(T: pd.DataFrame) -> dict:
    if len(T) == 0: return summarize(np.array([]), np.array([]))
    return summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float))


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low {coverage}")

    D0 = scan(x5)
    seed_invariant(D0)
    D, C = build(D0)
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    seed = D[(D.clock_min_utc == 390) & (D.lookback_min == 240) & (D.hold_min == 720)].iloc[0]
    lines = [
        "# ETH Economic-First E10A — Fine Cross-Era Region Refinement Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen family: **MOMENTUM / causal B40_60 / exact-open entry and exit / no TP / no SL**.",
        f"Fine Development candidates: **{len(D)}**.",
        f"Candidate-gate passers: **{int(D.candidate_gate.sum())}**; candidate + local-stability passers: **{len(C)}**.", "",
        "## E9 seed reproduction", "",
        f"06:30 UTC (13:30 WIB) / LB240 / hold720: N **{int(seed.trades)}**, WR **{pct(seed.win_rate)}**, net **{money(seed.net_pnl)}**, exp **{money(seed.expectancy)}/trade**, PF **{seed.pf:.3f}**, DD **{money(seed.max_dd)}**, loss streak **{int(seed.max_loss_streak)}**.", "",
        "## Fine region atlas", "",
        "| # | UTC | WIB | LB | Hold | N | WR | Net | Exp | PF | DD | 2022 WR/Exp | 2023 WR/Exp | 2024 WR/Exp | Gate | Neigh | Eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    top = D.sort_values(["min_era_exp", "min_era_wr", "expectancy", "win_rate"], ascending=[False, False, False, False]).head(20)
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {i} | {r.clock_utc} | {r.clock_wib} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | "
            f"{pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | {'YES' if r.candidate_gate else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {'YES' if r.candidate_eligible else 'NO'} |"
        )

    if len(C) == 0:
        status = "ETH_ECONOMIC_FIRST_E10A_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "", "Fine-grid region did not earn OOS exposure. No gate relaxation or second-best substitution.", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text()); return

    sel = C.iloc[0]
    lines += ["", "## Development-selected fine winner", "",
              f"**{sel['clock_utc']} UTC ({sel['clock_wib']} WIB) / MOMENTUM / LB{int(sel['lookback_min'])} / B40_60 / hold{int(sel['hold_min'])}m**", "",
              f"N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, loss streak **{int(sel['max_loss_streak'])}**, min-era WR **{pct(sel['min_era_wr'])}**, min-era exp **{money(sel['min_era_exp'])}**, neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**."]

    Tdev = selected_trade_df(x5, "development", sel)
    if bool(sel["boundary"]):
        status = "ETH_ECONOMIC_FIRST_E10A_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        Tdev.to_csv(OUT_TRADES, index=False)
        lines += ["", "Winner touches a preregistered fine-grid sentinel; holdouts remain closed.", "", f"**Status: {status}**", "", "Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text()); return

    hrows = []; trades = [Tdev]; all_ok = True
    for part in ("external", "reference_validation"):
        T = selected_trade_df(x5, part, sel)
        s = stats(T)
        ok = (
            s.get("trades", 0) >= 50 and s.get("win_rate", 0) >= .55 and s.get("net_pnl", -1) > 0 and
            s.get("expectancy", -1) >= .50 and s.get("pf", 0) >= 1.15 and
            s.get("max_dd", 1e9) <= 150 and s.get("max_loss_streak", 99) <= 8
        )
        hrows.append({"partition": part, **s, "replication_pass": bool(ok)})
        trades.append(T); all_ok &= bool(ok)
    H = pd.DataFrame(hrows)
    H.to_csv(OUT_SUMMARY, index=False)
    allT = pd.concat(trades, ignore_index=True).sort_values("entry_ts")
    allT.to_csv(OUT_TRADES, index=False)
    sa = stats(allT)
    status = "ETH_ECONOMIC_FIRST_E10A_SUPPORTED" if all_ok else "ETH_ECONOMIC_FIRST_E10A_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines += ["", "## Historical replication", "",
              "| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    lines += ["", "## Combined historical — descriptive", "",
              f"N **{int(sa['trades'])}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{int(sa['max_loss_streak'])}**.", "",
              "BTC A3.9 context: WR56.83%, exp+$0.6887/trade, PF1.431, DD$31.636, loss streak4.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
