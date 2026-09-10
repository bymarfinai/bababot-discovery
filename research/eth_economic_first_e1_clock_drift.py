#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E1_CLOCK_DRIFT"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

NOTIONAL = 500.0
FEE = 0.75
CLOCKS = tuple(range(0, 1440, 30))
HOLDS = (15, 30, 60, 90, 120, 180, 240, 360, 480, 720, 960)
SIDES = ("LONG", "SHORT")
BAR_MIN = 5

BTC = {
    "trades": 139,
    "wr": .5683,
    "net": 95.734,
    "exp": .6887,
    "pf": 1.431,
    "dd": 31.636,
    "loss_streak": 4,
}


def hhmm(m: int) -> str:
    m %= 1440
    return f"{m//60:02d}:{m%60:02d}"


def wib(m: int) -> str:
    return hhmm(m + 420)


def profit_factor(pnls: np.ndarray) -> float:
    pos = float(pnls[pnls > 0].sum())
    neg = float(-pnls[pnls < 0].sum())
    if neg == 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def max_drawdown(pnls: np.ndarray) -> float:
    if len(pnls) == 0:
        return np.nan
    c = np.cumsum(pnls.astype(float))
    peaks = np.maximum.accumulate(np.r_[0.0, c])
    return float(np.max(peaks[1:] - c)) if len(c) else 0.0


def streaks(pnls: np.ndarray):
    ml = mw = cl = cw = 0
    for p in pnls:
        if p > 0:
            cw += 1; cl = 0; mw = max(mw, cw)
        else:
            cl += 1; cw = 0; ml = max(ml, cl)
    return int(ml), int(mw)


def trade_frame(x5: pd.DataFrame, part: str, clock: int, hold: int, side: str) -> pd.DataFrame:
    pa, pz = base.PARTS[part]
    days = pd.date_range(pa.normalize(), pz.normalize(), freq="D", tz="UTC")
    days = days[np.array([d.weekday() < 5 for d in days], dtype=bool)]
    ent_ts = days + pd.Timedelta(minutes=int(clock))
    exit_ts = ent_ts + pd.Timedelta(minutes=int(hold))
    keep = (ent_ts >= pa) & (exit_ts < pz) & (exit_ts < base.END)
    ent_ts = ent_ts[keep]; exit_ts = exit_ts[keep]
    if len(ent_ts) == 0:
        return pd.DataFrame()

    ei = x5.index.get_indexer(ent_ts)
    xi = x5.index.get_indexer(exit_ts)
    expected_bars = int(hold) // BAR_MIN
    complete = (ei >= 0) & (xi >= 0) & ((xi - ei) == expected_bars)
    ent_ts = ent_ts[complete]; exit_ts = exit_ts[complete]
    ei = ei[complete]; xi = xi[complete]
    if len(ei) == 0:
        return pd.DataFrame()

    ep = x5.open.to_numpy(float)[ei]
    xp = x5.open.to_numpy(float)[xi]
    sign = 1.0 if side == "LONG" else -1.0
    gross_ret = sign * (xp - ep) / ep
    gross = NOTIONAL * gross_ret
    net = gross - FEE
    return pd.DataFrame({
        "partition": part,
        "side": side,
        "clock_min_utc": int(clock),
        "clock_utc": hhmm(clock),
        "clock_wib": wib(clock),
        "hold_min": int(hold),
        "entry_ts": ent_ts,
        "exit_ts": exit_ts,
        "entry_price": ep,
        "exit_price": xp,
        "gross_return": gross_ret,
        "gross_pnl": gross,
        "fee": FEE,
        "net_pnl": net,
        "net_positive": net > 0,
    })


def summarize(T: pd.DataFrame, blocks: int = 4) -> dict:
    if T is None or len(T) == 0:
        return {}
    T = T.sort_values("entry_ts").reset_index(drop=True)
    p = T.net_pnl.to_numpy(float)
    ml, mw = streaks(p)
    out = {
        "trades": int(len(T)),
        "net_wins": int((p > 0).sum()),
        "net_losses": int((p <= 0).sum()),
        "win_rate": float((p > 0).mean()),
        "gross_pnl": float(T.gross_pnl.sum()),
        "fees": float(T.fee.sum()),
        "net_pnl": float(p.sum()),
        "expectancy": float(p.mean()),
        "net_per_100": float(p.mean() * 100.0),
        "pf": float(profit_factor(p)),
        "max_dd": float(max_drawdown(p)),
        "max_loss_streak": ml,
        "max_win_streak": mw,
    }
    if blocks:
        positive = 0
        arrs = np.array_split(np.arange(len(T)), blocks)
        for bi, ix in enumerate(arrs, 1):
            B = T.iloc[ix]
            bp = B.net_pnl.to_numpy(float)
            bnet = float(bp.sum())
            bwr = float((bp > 0).mean()) if len(bp) else np.nan
            out[f"block{bi}_n"] = int(len(B))
            out[f"block{bi}_net"] = bnet
            out[f"block{bi}_wr"] = bwr
            if bnet > 0:
                positive += 1
        out["positive_blocks"] = int(positive)
    return out


def dev_scan(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for clock in CLOCKS:
        for hold in HOLDS:
            for side in SIDES:
                T = trade_frame(x5, "development", clock, hold, side)
                s = summarize(T, 4)
                rows.append({
                    "clock_min_utc": clock,
                    "clock_utc": hhmm(clock),
                    "clock_wib": wib(clock),
                    "hold_min": hold,
                    "side": side,
                    **s,
                })
    D = pd.DataFrame(rows)
    if len(D) != 1056:
        raise AssertionError(f"expected 1056 candidates, got {len(D)}")
    return D


def neighbor_keys(r):
    clock = int(r.clock_min_utc); hold = int(r.hold_min); side = r.side
    hi = HOLDS.index(hold)
    keys = [((clock - 30) % 1440, hold, side), ((clock + 30) % 1440, hold, side)]
    if hi > 0:
        keys.append((clock, HOLDS[hi - 1], side))
    if hi + 1 < len(HOLDS):
        keys.append((clock, HOLDS[hi + 1], side))
    return keys


def build_leaderboard(D: pd.DataFrame):
    D = D.copy()
    D["healthy_gate"] = (
        (D.trades >= 700) &
        (D.win_rate >= .52) &
        (D.net_pnl > 0) &
        (D.expectancy >= .10) &
        (D.pf >= 1.10) &
        (D.max_dd <= 100.0) &
        (D.max_loss_streak <= 10) &
        (D.positive_blocks >= 3)
    )
    lookup = {(int(r.clock_min_utc), int(r.hold_min), r.side): r for r in D.itertuples(index=False)}
    nav, nsup, stable = [], [], []
    for r in D.itertuples(index=False):
        keys = neighbor_keys(r)
        sup = 0
        for k in keys:
            x = lookup[k]
            if (
                int(x.trades) >= 700 and float(x.net_pnl) > 0 and float(x.expectancy) > 0 and
                float(x.pf) >= 1.00 and float(x.win_rate) >= .505 and int(x.positive_blocks) >= 2
            ):
                sup += 1
        need = min(2, len(keys))
        nav.append(len(keys)); nsup.append(sup); stable.append(sup >= need)
    D["neighbors_available"] = nav
    D["neighbors_supportive"] = nsup
    D["local_stable"] = stable
    D["candidate_eligible"] = D.healthy_gate & D.local_stable
    D["hold_boundary"] = D.hold_min.isin((min(HOLDS), max(HOLDS)))
    D["side_tie"] = D.side.map({"LONG": 0, "SHORT": 1})

    C = D[D.candidate_eligible].copy()
    C = C.sort_values(
        ["net_per_100", "win_rate", "pf", "max_dd", "max_loss_streak", "hold_min", "clock_min_utc", "side_tie"],
        ascending=[False, False, False, True, True, True, True, True]
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    return D, C


def evaluate_holdouts(x5: pd.DataFrame, sel):
    rows = []; trades = []; all_ok = True
    for part in ("external", "reference_validation"):
        T = trade_frame(x5, part, int(sel.clock_min_utc), int(sel.hold_min), sel.side)
        s = summarize(T, 0)
        ok = (
            s.get("trades", 0) >= 300 and
            s.get("win_rate", 0) >= .505 and
            s.get("net_pnl", -1) > 0 and
            s.get("expectancy", -1) > 0 and
            s.get("pf", 0) >= 1.05 and
            s.get("max_loss_streak", 99) <= 15
        )
        rows.append({"partition": part, **s, "replication_pass": bool(ok)})
        if len(T): trades.append(T)
        all_ok = all_ok and bool(ok)
    return pd.DataFrame(rows), trades, all_ok


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def descriptive_top(D, n=15):
    return D.sort_values(
        ["net_per_100", "win_rate", "pf", "max_dd"],
        ascending=[False, False, False, True]
    ).head(n).copy()


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"ETH 5m coverage too low {coverage}")

    D = dev_scan(x5)
    D2, C = build_leaderboard(D)
    D2.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Economic-First Reset — E1 Clock Drift Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "E1 uses **no H/L/range/breakout/retest/EMA/Fibonacci**. Entry and exit are exact 5m opens.",
        "Fixed economics: **$500 notional / $0.75 round-trip cost / no compounding**.",
        f"Development candidates: **{len(D2)}** = 48 clocks × 2 sides × 11 holds.", "",
        f"Development healthy-gate passers: **{int(D2.healthy_gate.sum())}**; full gate + local-stability passers: **{len(C)}**.", "",
    ]

    if len(C) == 0:
        status = "ETH_ECONOMIC_FIRST_E1_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        top = descriptive_top(D2, 15)
        lines += [
            "No candidate passed the preregistered economic-first Development + local-stability gates.", "",
            "## Best raw Development economics — descriptive only", "",
            "| # | UTC | WIB | Side | Hold | Trades | WR | Net | Exp | PF | DD | L-streak | Blocks | Healthy | Neigh |",
            "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"
        ]
        for i, r in enumerate(top.itertuples(index=False), 1):
            lines.append(
                f"| {i} | {r.clock_utc} | {r.clock_wib} | {r.side} | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | "
                f"{money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
                f"{int(r.positive_blocks)}/4 | {'YES' if bool(r.healthy_gate) else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} |"
            )
        bestwr = D2.sort_values(["win_rate", "expectancy"], ascending=[False, False]).iloc[0]
        lines += [
            "", "## Highest-WR Development candidate — descriptive only", "",
            f"**{bestwr.clock_utc} UTC ({bestwr.clock_wib} WIB) / {bestwr.side} / {int(bestwr.hold_min)}m**: WR **{pct(bestwr.win_rate)}**, net **{money(bestwr.net_pnl)}**, exp **{money(bestwr.expectancy)}/trade**, PF **{float(bestwr.pf):.3f}**, DD **{money(bestwr.max_dd)}**.",
            "", f"**Status: {status}**", "",
            "Per preregistration, pure clock drift is closed rather than rescued by H tuning or post-hoc thresholds.",
            "Research/shadow only. No live promotion or profit guarantee."
        ]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    lines += [
        "## Development-selected economic character", "",
        f"**{sel.clock_utc} UTC ({sel.clock_wib} WIB) / {sel.side} / hold {int(sel.hold_min)}m**", "",
        f"- Trades **{int(sel.trades)}**; net WR **{pct(sel.win_rate)}**.",
        f"- Net **{money(sel.net_pnl)}**; expectancy **{money(sel.expectancy)}/trade**; net/100 **{money(sel.net_per_100)}**.",
        f"- PF **{float(sel.pf):.3f}**; DD **{money(sel.max_dd)}**; max loss/win streak **{int(sel.max_loss_streak)}/{int(sel.max_win_streak)}**.",
        f"- Positive blocks **{int(sel.positive_blocks)}/4**; supportive neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**.", "",
        "Development block details:", "",
        "| Block | N | WR | Net |", "|---:|---:|---:|---:|"
    ]
    for b in range(1, 5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {pct(sel[f'block{b}_wr'])} | {money(sel[f'block{b}_net'])} |")

    Tdev = trade_frame(x5, "development", int(sel.clock_min_utc), int(sel.hold_min), sel.side)
    if bool(sel.hold_boundary):
        status = "ETH_ECONOMIC_FIRST_E1_HOLD_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        Tdev.to_csv(OUT_TRADES, index=False)
        lines += ["", "Winner is on the preregistered hold sentinel. Holdouts remain closed; no second-best substitution.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    H, hold_trades, supported = evaluate_holdouts(x5, sel)
    H.to_csv(OUT_SUMMARY, index=False)
    allT = [Tdev] + hold_trades
    pd.concat(allT, ignore_index=True).to_csv(OUT_TRADES, index=False)
    status = "ETH_ECONOMIC_FIRST_E1_SUPPORTED" if supported else "ETH_ECONOMIC_FIRST_E1_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines += ["", "## Historical replication", "", "| Partition | Trades | WR | Net | Exp | PF | DD | L-streak | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")

    Pall = pd.concat(allT, ignore_index=True)
    sall = summarize(Pall, 0)
    lines += [
        "", "## All three historical partitions combined — descriptive", "",
        f"Trades **{sall['trades']}**; WR **{pct(sall['win_rate'])}**; net **{money(sall['net_pnl'])}**; expectancy **{money(sall['expectancy'])}/trade**; PF **{sall['pf']:.3f}**; DD **{money(sall['max_dd'])}**; loss streak **{sall['max_loss_streak']}**.",
        "", "## BTC A3.9 benchmark context", "",
        "BTC: WR 56.83%, expectancy +$0.6887/trade, PF 1.431, max DD $31.636, loss streak 4.",
        "", "## Top eligible Development candidates", "",
        "| # | UTC | WIB | Side | Hold | WR | Exp | PF | DD | Neigh |",
        "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.head(15).itertuples(index=False):
        lines.append(f"| {int(r.dev_rank)} | {r.clock_utc} | {r.clock_wib} | {r.side} | {int(r.hold_min)}m | {pct(r.win_rate)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} |")
    lines += ["", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
