#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import math
import numpy as np
import pandas as pd

import eth_discovery2_reset_g4_entry_discovery as g4

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G5_ECONOMIC_TRANSLATION"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_SelectedSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR_MIN = 5
NOTIONAL = 500.0
ROUNDTRIP_COST_RATE = 0.0015
FEE = NOTIONAL * ROUNDTRIP_COST_RATE
TPS = (0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.40, 0.60, 0.80)
SLS = (0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.40, 0.60)
HOLDS = (15, 30, 60, 120, 240, 480, 720)
PARTS = ("development", "external", "reference_validation")
BTC = {
    "trades": 139,
    "win_rate": 0.5683,
    "net_pnl": 95.734,
    "expectancy": 0.6887,
    "net_per_100_trades": 68.873,
    "pf": 1.431,
    "max_dd": 31.636,
    "max_loss_streak": 4,
}


def fmt_money(x):
    return "-" if pd.isna(x) else f"${float(x):.2f}"


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.2f}%"


def build_entries(x5: pd.DataFrame, part: str) -> pd.DataFrame:
    C = g4.build_b00_cases(x5, part)
    rows = []
    for c in C.itertuples(index=False):
        ent = g4.next_open_entry(x5, c)
        if not ent or not ent.get("available", False):
            continue
        j = int(ent["entry_j"])
        ix = int(c.exe_start_pos) + j
        ts = x5.index[ix]
        if ts != pd.Timestamp(ent["entry_ts"]):
            raise AssertionError("NEXT_OPEN timestamp mismatch")
        if ts >= pd.Timestamp(c.execution_end):
            raise AssertionError("entry at/after execution end")
        rows.append({
            "partition": part,
            "reference_start": c.reference_start,
            "execution_start": c.execution_start,
            "execution_end": c.execution_end,
            "H": float(c.H), "L": float(c.L), "R": float(c.R),
            "signal_ts": c.signal_ts,
            "b00_complete_ts": c.b00_complete_ts,
            "b00_close": float(c.b00_close),
            "entry_j": j,
            "entry_bar_start": ts,
            "entry_ts": ts,
            "entry_price": float(ent["entry_price"]),
            "exe_start_pos": int(c.exe_start_pos),
            "exe_n": int(c.exe_n),
        })
    E = pd.DataFrame(rows)
    return E.sort_values("entry_ts").reset_index(drop=True) if len(E) else E


def simulate_trade(x5: pd.DataFrame, r, tp_r: float, sl_r: float, hold_min: int):
    ep = float(r.entry_price)
    R = float(r.R)
    tp = ep + tp_r * R
    sl = ep - sl_r * R
    entry_ts = pd.Timestamp(r.entry_ts)
    deadline = min(pd.Timestamp(r.execution_end), entry_ts + pd.Timedelta(minutes=int(hold_min)))

    start_ix = int(r.exe_start_pos) + int(r.entry_j)
    max_end_ix = int(r.exe_start_pos) + int(r.exe_n)
    reason = "TIMEOUT"
    exit_price = np.nan
    exit_ts = pd.NaT
    last_complete = None

    for ix in range(start_ix, min(max_end_ix, len(x5))):
        ts = x5.index[ix]
        if ts >= deadline or ts >= pd.Timestamp(r.execution_end):
            break
        bar_end = ts + pd.Timedelta(minutes=BAR_MIN)
        if bar_end > deadline or bar_end > pd.Timestamp(r.execution_end):
            break
        b = x5.iloc[ix]
        hi, lo = float(b.high), float(b.low)
        hit_tp = hi >= tp
        hit_sl = lo <= sl
        last_complete = ix
        if hit_tp and hit_sl:
            reason = "SL"
            exit_price = sl
            exit_ts = bar_end
            break
        if hit_sl:
            reason = "SL"
            exit_price = sl
            exit_ts = bar_end
            break
        if hit_tp:
            reason = "TP"
            exit_price = tp
            exit_ts = bar_end
            break

    if pd.isna(exit_ts):
        if last_complete is None:
            return None
        ts = x5.index[last_complete]
        exit_price = float(x5.close.iloc[last_complete])
        exit_ts = ts + pd.Timedelta(minutes=BAR_MIN)
        if exit_ts > deadline + pd.Timedelta(microseconds=1):
            raise AssertionError("timeout exit after deadline")

    gross_ret = exit_price / ep - 1.0
    gross_pnl = NOTIONAL * gross_ret
    net_pnl = gross_pnl - FEE
    hold_actual = float((pd.Timestamp(exit_ts) - entry_ts) / pd.Timedelta(minutes=1))
    return {
        "partition": r.partition,
        "entry_ts": entry_ts,
        "entry_price": ep,
        "R": R,
        "tp_r": tp_r,
        "sl_r": sl_r,
        "hold_cap_min": int(hold_min),
        "tp_price": tp,
        "sl_price": sl,
        "exit_ts": exit_ts,
        "exit_price": exit_price,
        "reason": reason,
        "gross_return": gross_ret,
        "gross_pnl": gross_pnl,
        "fee": FEE,
        "net_pnl": net_pnl,
        "net_positive": bool(net_pnl > 0),
        "hold_minutes": hold_actual,
        "b00_complete_ts": r.b00_complete_ts,
    }


def max_drawdown(pnls):
    if len(pnls) == 0:
        return np.nan
    c = np.cumsum(np.asarray(pnls, dtype=float))
    peaks = np.maximum.accumulate(np.r_[0.0, c])
    return float(np.max(peaks[1:] - c)) if len(c) else 0.0


def streaks(pnls):
    ml = mw = cl = cw = 0
    for p in pnls:
        if p > 0:
            cw += 1; cl = 0; mw = max(mw, cw)
        else:
            cl += 1; cw = 0; ml = max(ml, cl)
    return int(ml), int(mw)


def profit_factor(pnls):
    a = np.asarray(pnls, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def summarize(T: pd.DataFrame, blocks: int = 0):
    if T is None or len(T) == 0:
        return None
    T = T.sort_values(["entry_ts", "exit_ts"]).reset_index(drop=True)
    p = T.net_pnl.to_numpy(float)
    ml, mw = streaks(p)
    out = {
        "trades": len(T),
        "tp_hits": int((T.reason == "TP").sum()),
        "sl_hits": int((T.reason == "SL").sum()),
        "timeouts": int((T.reason == "TIMEOUT").sum()),
        "net_wins": int((T.net_pnl > 0).sum()),
        "net_losses": int((T.net_pnl <= 0).sum()),
        "win_rate": float((T.net_pnl > 0).mean()),
        "gross_pnl": float(T.gross_pnl.sum()),
        "fees": float(T.fee.sum()),
        "net_pnl": float(T.net_pnl.sum()),
        "expectancy": float(T.net_pnl.mean()),
        "net_per_100_trades": float(T.net_pnl.mean() * 100.0),
        "pf": float(profit_factor(p)),
        "max_dd": max_drawdown(p),
        "max_loss_streak": ml,
        "max_win_streak": mw,
        "avg_hold_min": float(T.hold_minutes.mean()),
        "median_hold_min": float(T.hold_minutes.median()),
    }
    if blocks:
        vals = []
        for ix in np.array_split(np.arange(len(T)), blocks):
            vals.append(float(T.iloc[ix].net_pnl.sum()) if len(ix) else 0.0)
        out["block_pnls"] = vals
        out["positive_blocks"] = int(sum(v > 0 for v in vals))
    return out


def run_config(x5, E, tp_r, sl_r, hold_min):
    rows = []
    for r in E.itertuples(index=False):
        t = simulate_trade(x5, r, tp_r, sl_r, hold_min)
        if t is not None:
            rows.append(t)
    return pd.DataFrame(rows)


def development_grid(x5, Edev):
    rows = []
    for tp_r, sl_r, hold_min in itertools.product(TPS, SLS, HOLDS):
        T = run_config(x5, Edev, tp_r, sl_r, hold_min)
        s = summarize(T, blocks=4)
        if s is None:
            continue
        rows.append({
            "tp_r": tp_r, "sl_r": sl_r, "hold_min": int(hold_min),
            **{k: v for k, v in s.items() if k != "block_pnls"},
            "block1": s["block_pnls"][0], "block2": s["block_pnls"][1],
            "block3": s["block_pnls"][2], "block4": s["block_pnls"][3],
        })
    return pd.DataFrame(rows)


def neighbor_keys(tp, sl, hold):
    ti = TPS.index(float(tp)); si = SLS.index(float(sl)); hi = HOLDS.index(int(hold))
    keys = []
    if ti > 0: keys.append((TPS[ti-1], sl, hold))
    if ti+1 < len(TPS): keys.append((TPS[ti+1], sl, hold))
    if si > 0: keys.append((tp, SLS[si-1], hold))
    if si+1 < len(SLS): keys.append((tp, SLS[si+1], hold))
    if hi > 0: keys.append((tp, sl, HOLDS[hi-1]))
    if hi+1 < len(HOLDS): keys.append((tp, sl, HOLDS[hi+1]))
    return keys


def build_leaderboard(G):
    G = G.copy()
    G["dev_gate"] = (
        (G.trades >= 150) & (G.net_pnl > 0) & (G.expectancy > 0) &
        (G.pf >= 1.20) & (G.max_dd <= 40.0) &
        (G.max_loss_streak <= 8) & (G.positive_blocks >= 3)
    )
    lookup = {(float(r.tp_r), float(r.sl_r), int(r.hold_min)): r for r in G.itertuples(index=False)}
    navs, nsups, stable = [], [], []
    for r in G.itertuples(index=False):
        keys = neighbor_keys(float(r.tp_r), float(r.sl_r), int(r.hold_min))
        sup = 0
        for k in keys:
            x = lookup[(float(k[0]), float(k[1]), int(k[2]))]
            if float(x.net_pnl) > 0 and float(x.pf) >= 1.10 and float(x.max_dd) <= 50.0 and int(x.positive_blocks) >= 3:
                sup += 1
        need = max(2, math.ceil(0.50 * len(keys)))
        navs.append(len(keys)); nsups.append(sup); stable.append(sup >= need)
    G["neighbors_available"] = navs
    G["neighbors_supportive"] = nsups
    G["local_stable"] = stable
    G["candidate_eligible"] = G.dev_gate & G.local_stable
    G["outer_boundary"] = (
        G.tp_r.isin((min(TPS), max(TPS))) |
        G.sl_r.isin((min(SLS), max(SLS))) |
        G.hold_min.isin((min(HOLDS), max(HOLDS)))
    )
    C = G[G.candidate_eligible].copy()
    C = C.sort_values(
        ["net_per_100_trades", "pf", "max_dd", "win_rate", "max_loss_streak", "hold_min", "sl_r", "tp_r"],
        ascending=[False, False, True, False, True, True, True, True]
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return G, C


def evaluate_selected(x5, entries, sel):
    rows = []; trades = []; all_ok = True
    tp, sl, hold = float(sel["tp_r"]), float(sel["sl_r"]), int(sel["hold_min"])
    for part in ("external", "reference_validation"):
        T = run_config(x5, entries[part], tp, sl, hold)
        s = summarize(T)
        ok = (
            s is not None and s["trades"] >= 70 and s["net_pnl"] > 0 and
            s["expectancy"] > 0 and s["pf"] >= 1.10 and s["max_dd"] <= 45.0 and
            s["max_loss_streak"] <= 8
        )
        rows.append({"partition": part, **(s or {}), "replication_pass": bool(ok)})
        all_ok = all_ok and bool(ok)
        if T is not None and len(T): trades.append(T)

    pooled_ok = False
    if trades:
        P = pd.concat(trades, ignore_index=True).sort_values("entry_ts")
        ps = summarize(P)
        pooled_ok = bool(ps and ps["net_pnl"] > 0 and ps["pf"] >= 1.15)
        rows.append({"partition": "POOLED_HOLDOUT", **ps, "replication_pass": pooled_ok})
    return pd.DataFrame(rows), bool(all_ok and pooled_ok)


def all_historical(x5, entries, sel):
    tp, sl, hold = float(sel["tp_r"]), float(sel["sl_r"]), int(sel["hold_min"])
    tt = []
    for part in PARTS:
        T = run_config(x5, entries[part], tp, sl, hold)
        if len(T): tt.append(T)
    T = pd.concat(tt, ignore_index=True).sort_values("entry_ts").reset_index(drop=True)
    return T, summarize(T)


def main():
    g4.g1.base.synthetic_tests()
    x5, coverage = g4.g1.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    entries = {p: build_entries(x5, p) for p in PARTS}
    expected = {"development": 184, "external": 88, "reference_validation": 91}
    for p, n in expected.items():
        if len(entries[p]) != n:
            raise AssertionError(f"frozen G4 NEXT_OPEN count mismatch {p}: {len(entries[p])} vs {n}")

    G = development_grid(x5, entries["development"])
    if len(G) != len(TPS)*len(SLS)*len(HOLDS):
        raise AssertionError(f"grid mismatch {len(G)}")
    G2, C = build_leaderboard(G)
    G2.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Discovery 2 Reset — G5 Economic Translation Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen lineage: **LONG / 01:30 UTC / R180 / E720 / HIGH-side pressure → DIRECT B00 → NEXT_OPEN**.",
        f"Frozen entries: Development **{len(entries['development'])}**, External **{len(entries['external'])}**, Reference Validation **{len(entries['reference_validation'])}**.",
        f"Fixed economics: **${NOTIONAL:.0f} notional / ${FEE:.2f} round-trip fee / no compounding**.",
        f"Development grid: **{len(TPS)} TP × {len(SLS)} SL × {len(HOLDS)} hold = {len(G)} configs**.", ""
    ]

    if len(C) == 0:
        status = "ETH_DISCOVERY2_RESET_G5_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        lines += ["No configuration passed the preregistered Development economic + local-stability gates.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(OUT_RESULT.read_text()); return

    sel = C.iloc[0]
    lines += [
        "## Development-selected money geometry", "",
        f"**TP {float(sel.tp_r):.2f}R / SL {float(sel.sl_r):.2f}R / hold {int(sel.hold_min)}m**", "",
        f"Trades **{int(sel.trades)}**; TP/SL/timeout **{int(sel.tp_hits)}/{int(sel.sl_hits)}/{int(sel.timeouts)}**; net WR **{pct(sel.win_rate)}**.",
        f"Net **{fmt_money(sel.net_pnl)}**; expectancy **{fmt_money(sel.expectancy)}/trade**; net/100 **{fmt_money(sel.net_per_100_trades)}**.",
        f"PF **{float(sel.pf):.3f}**; max DD **{fmt_money(sel.max_dd)}**; max loss/win streak **{int(sel.max_loss_streak)}/{int(sel.max_win_streak)}**.",
        f"Positive blocks **{int(sel.positive_blocks)}/4**; block PnLs [{fmt_money(sel.block1)}, {fmt_money(sel.block2)}, {fmt_money(sel.block3)}, {fmt_money(sel.block4)}].",
        f"Supportive neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; outer boundary **{'YES' if bool(sel.outer_boundary) else 'NO'}**.", ""
    ]

    old = G2[(np.isclose(G2.tp_r, .60)) & (np.isclose(G2.sl_r, .30)) & (G2.hold_min == 120)]
    if len(old):
        z = old.iloc[0]
        lines += [
            "## Historical Z6 coordinate on the reset lineage", "",
            f"Old coordinate TP0.60/SL0.30/120m now gives: WR **{pct(z.win_rate)}**, net **{fmt_money(z.net_pnl)}**, expectancy **{fmt_money(z.expectancy)}**, PF **{float(z.pf):.3f}**, DD **{fmt_money(z.max_dd)}**, blocks **{int(z.positive_blocks)}/4**.", ""
        ]

    lines += ["## Top Development candidates", "", "| # | TP | SL | Hold | WR | Net | Exp | PF | DD | Streak | Blocks | Neigh. | Boundary |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in C.head(15).itertuples(index=False):
        lines.append(f"| {int(r.dev_rank)} | {float(r.tp_r):.2f} | {float(r.sl_r):.2f} | {int(r.hold_min)} | {pct(r.win_rate)} | {fmt_money(r.net_pnl)} | {fmt_money(r.expectancy)} | {float(r.pf):.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.positive_blocks)}/4 | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {'YES' if bool(r.outer_boundary) else 'NO'} |")

    if bool(sel.outer_boundary):
        status = "ETH_DISCOVERY2_RESET_G5_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", "The Development winner lies on at least one preregistered outer sentinel. Per preregistration, historical holdouts remain closed; no second-best substitution.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(OUT_RESULT.read_text()); return

    H, replicated = evaluate_selected(x5, entries, sel)
    H.to_csv(OUT_SUMMARY, index=False)
    Tall, allsum = all_historical(x5, entries, sel)
    Tall.to_csv(OUT_TRADES, index=False)
    status = "ETH_DISCOVERY2_RESET_G5_SUPPORTED" if replicated else "ETH_DISCOVERY2_RESET_G5_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines += ["", "## Historical replication", "", "| Partition | Trades | WR | Net | Exp | PF | DD | Loss streak | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {fmt_money(r.net_pnl)} | {fmt_money(r.expectancy)} | {float(r.pf):.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")

    lines += [
        "", "## All historical partitions combined — descriptive", "",
        f"Trades **{int(allsum['trades'])}**; WR **{pct(allsum['win_rate'])}**; net **{fmt_money(allsum['net_pnl'])}**; expectancy **{fmt_money(allsum['expectancy'])}/trade**; net/100 **{fmt_money(allsum['net_per_100_trades'])}**; PF **{float(allsum['pf']):.3f}**; max DD **{fmt_money(allsum['max_dd'])}**; max loss streak **{int(allsum['max_loss_streak'])}**.", "",
        "## BTC A3.9 benchmark comparison", "",
        "| Metric | ETH G5 | BTC A3.9 | ETH beats BTC? |", "|---|---:|---:|---|",
        f"| WR | {pct(allsum['win_rate'])} | {pct(BTC['win_rate'])} | {'YES' if allsum['win_rate'] > BTC['win_rate'] else 'NO'} |",
        f"| Net PnL | {fmt_money(allsum['net_pnl'])} | {fmt_money(BTC['net_pnl'])} | {'YES' if allsum['net_pnl'] > BTC['net_pnl'] else 'NO'} |",
        f"| Expectancy/trade | {fmt_money(allsum['expectancy'])} | ${BTC['expectancy']:.4f} | {'YES' if allsum['expectancy'] > BTC['expectancy'] else 'NO'} |",
        f"| Net/100 trades | {fmt_money(allsum['net_per_100_trades'])} | ${BTC['net_per_100_trades']:.3f} | {'YES' if allsum['net_per_100_trades'] > BTC['net_per_100_trades'] else 'NO'} |",
        f"| PF | {float(allsum['pf']):.3f} | {BTC['pf']:.3f} | {'YES' if allsum['pf'] > BTC['pf'] else 'NO'} |",
        f"| Max DD | {fmt_money(allsum['max_dd'])} | ${BTC['max_dd']:.3f} | {'YES' if allsum['max_dd'] < BTC['max_dd'] else 'NO'} |",
        f"| Max loss streak | {int(allsum['max_loss_streak'])} | {BTC['max_loss_streak']} | {'YES' if allsum['max_loss_streak'] < BTC['max_loss_streak'] else ('TIE' if allsum['max_loss_streak'] == BTC['max_loss_streak'] else 'NO')} |",
        "", f"**Status: {status}**", "",
        "G5 validates money geometry only if SUPPORTED. BTC comparison is descriptive and did not participate in candidate selection or replication gates.",
        "Research/shadow only. No live promotion or profit guarantee."
    ]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
