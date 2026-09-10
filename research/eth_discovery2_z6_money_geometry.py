#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_z5_pullback_entry as z5

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_Z6_MONEY_GEOMETRY"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_SUMMARY = ROOT / f"{PFX}_SelectedSummary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
ROUNDTRIP_COST_RATE = 0.0015
FEE = NOTIONAL * ROUNDTRIP_COST_RATE
TPS = (0.20, 0.30, 0.40, 0.50, 0.60)
SLS = (0.15, 0.20, 0.25, 0.30, 0.40)
HOLDS = (60, 120, 240)
COHORTS = ("F95", "F90")
PARTS = ("development", "external", "reference_validation")


def fast_slice(x, a, z):
    return base.fast_slice(x, a, z)


def build_parent_entries(x5: pd.DataFrame) -> pd.DataFrame:
    C = z5.build_cases(x5)
    rows = []
    for c in C.itertuples(index=False):
        ent = z5.limit_entry(x5, c, z5.LEVELS["L06"])
        if not ent.get("available", False):
            continue
        if pd.Timestamp(ent["entry_start"]) >= pd.Timestamp(c.execution_end):
            raise AssertionError("entry at/after execution_end")
        rows.append({
            "cohort": c.cohort,
            "session_id": c.session_id,
            "partition": c.partition,
            "H": float(c.H), "L": float(c.L), "R": float(c.R),
            "breakout_ts": pd.Timestamp(c.breakout_ts),
            "execution_end": pd.Timestamp(c.execution_end),
            "entry_start": pd.Timestamp(ent["entry_start"]),
            "entry_ts": pd.Timestamp(ent["entry_ts"]),
            "entry_price": float(ent["entry_price"]),
            "eval_start": pd.Timestamp(ent["eval_start"]),
            "fill_kind": ent.get("fill_kind", ""),
        })
    E = pd.DataFrame(rows)
    if len(E) == 0:
        raise RuntimeError("no Z5 L06 entries")
    return E


def simulate_trade(x5: pd.DataFrame, r, tp_r: float, sl_r: float, hold_min: int):
    ep = float(r.entry_price); R = float(r.R)
    tp = ep + tp_r * R
    sl = ep - sl_r * R
    ee = pd.Timestamp(r.execution_end)
    deadline = min(ee, pd.Timestamp(r.entry_ts) + pd.Timedelta(minutes=int(hold_min)))
    a = pd.Timestamp(r.eval_start)
    path = fast_slice(x5, a, deadline)
    if len(path) == 0:
        return None

    reason = "TIMEOUT"
    exit_price = np.nan
    exit_ts = pd.NaT
    for ts, b in path.iterrows():
        hi, lo = float(b.high), float(b.low)
        hit_tp = hi >= tp
        hit_sl = lo <= sl
        if hit_tp and hit_sl:
            reason = "SL"
            exit_price = sl
            exit_ts = ts + BAR5
            break
        if hit_sl:
            reason = "SL"
            exit_price = sl
            exit_ts = ts + BAR5
            break
        if hit_tp:
            reason = "TP"
            exit_price = tp
            exit_ts = ts + BAR5
            break

    if pd.isna(exit_ts):
        last_ts = path.index[-1]
        exit_price = float(path.iloc[-1].close)
        exit_ts = last_ts + BAR5
        if exit_ts > deadline:
            raise AssertionError("timeout exit after deadline")

    gross_ret = exit_price / ep - 1.0
    gross_pnl = NOTIONAL * gross_ret
    net_pnl = gross_pnl - FEE
    hold_minutes = float((pd.Timestamp(exit_ts) - pd.Timestamp(r.entry_ts)) / pd.Timedelta(minutes=1))
    return {
        "cohort": r.cohort,
        "session_id": r.session_id,
        "partition": r.partition,
        "entry_ts": r.entry_ts,
        "entry_price": ep,
        "R": R,
        "tp_r": tp_r,
        "sl_r": sl_r,
        "hold_cap_min": hold_min,
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
        "hold_minutes": hold_minutes,
        "fill_kind": r.fill_kind,
    }


def max_drawdown(pnls):
    if len(pnls) == 0:
        return np.nan
    c = np.cumsum(np.asarray(pnls, dtype=float))
    peaks = np.maximum.accumulate(np.r_[0.0, c])
    dd = peaks[1:] - c
    return float(np.max(dd)) if len(dd) else 0.0


def streaks(pnls):
    max_loss = max_win = cur_loss = cur_win = 0
    for p in pnls:
        if p > 0:
            cur_win += 1; cur_loss = 0
            max_win = max(max_win, cur_win)
        else:
            cur_loss += 1; cur_win = 0
            max_loss = max(max_loss, cur_loss)
    return max_loss, max_win


def profit_factor(pnls):
    a = np.asarray(pnls, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def summarize_trades(T: pd.DataFrame, blocks=0):
    if T is None or len(T) == 0:
        return None
    T = T.sort_values(["entry_ts", "session_id"]).reset_index(drop=True)
    pnls = T.net_pnl.to_numpy(float)
    ml, mw = streaks(pnls)
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
        "pf": float(profit_factor(pnls)),
        "max_dd": max_drawdown(pnls),
        "max_loss_streak": int(ml),
        "max_win_streak": int(mw),
        "avg_hold_min": float(T.hold_minutes.mean()),
        "median_hold_min": float(T.hold_minutes.median()),
        "median_gross_return_pct": float(T.gross_return.median() * 100.0),
        "net_per_100_trades": float(T.net_pnl.mean() * 100.0),
    }
    if blocks:
        arrs = np.array_split(np.arange(len(T)), blocks)
        vals = [float(T.iloc[idx].net_pnl.sum()) if len(idx) else 0.0 for idx in arrs]
        out["block_pnls"] = vals
        out["positive_blocks"] = int(sum(v > 0 for v in vals))
    return out


def run_config(x5, E, cohort, part, tp_r, sl_r, hold_min):
    q = E[(E.cohort == cohort) & (E.partition == part)].copy()
    rows = []
    for r in q.itertuples(index=False):
        t = simulate_trade(x5, r, tp_r, sl_r, hold_min)
        if t is not None:
            rows.append(t)
    return pd.DataFrame(rows)


def development_grid(x5, E):
    rows = []
    for cohort, tp_r, sl_r, hold_min in itertools.product(COHORTS, TPS, SLS, HOLDS):
        T = run_config(x5, E, cohort, "development", tp_r, sl_r, hold_min)
        s = summarize_trades(T, blocks=4)
        if s is None:
            continue
        rows.append({
            "cohort": cohort, "tp_r": tp_r, "sl_r": sl_r, "hold_min": hold_min,
            **{k:v for k,v in s.items() if k != "block_pnls"},
            "block1": s["block_pnls"][0], "block2": s["block_pnls"][1],
            "block3": s["block_pnls"][2], "block4": s["block_pnls"][3],
        })
    return pd.DataFrame(rows)


def select_dev(G):
    q = G[
        (G.trades >= 35) &
        (G.net_pnl > 0) &
        (G.expectancy > 0) &
        (G.pf >= 1.20) &
        (G.max_dd <= 40.0) &
        (G.positive_blocks >= 3)
    ].copy()
    if len(q) == 0:
        return None, q
    q["cohort_tie"] = q.cohort.map({"F95":0, "F90":1})
    q = q.sort_values(
        ["net_pnl","pf","max_dd","win_rate","hold_min","sl_r","tp_r","cohort_tie"],
        ascending=[False,False,True,False,True,True,True,True]
    ).reset_index(drop=True)
    return q.iloc[0].to_dict(), q


def evaluate_selected(x5, E, sel):
    rows = []
    if sel is None:
        return pd.DataFrame(), False
    cohort = sel["cohort"]; tp_r=float(sel["tp_r"]); sl_r=float(sel["sl_r"]); hold_min=int(sel["hold_min"])
    holdout_trades = []
    all_ok = True
    for part in ("external", "reference_validation"):
        T = run_config(x5, E, cohort, part, tp_r, sl_r, hold_min)
        s = summarize_trades(T)
        ok = s is not None and s["trades"] >= 15 and s["net_pnl"] > 0 and s["expectancy"] > 0 and s["pf"] >= 1.05
        all_ok = all_ok and bool(ok)
        rows.append({"partition":part, **(s or {}), "pass":bool(ok)})
        if T is not None and len(T):
            holdout_trades.append(T)
    pooled_ok = False
    if holdout_trades:
        P = pd.concat(holdout_trades, ignore_index=True)
        ps = summarize_trades(P)
        pooled_ok = ps["net_pnl"] > 0 and ps["pf"] >= 1.10
        rows.append({"partition":"POOLED_HOLDOUT", **ps, "pass":bool(pooled_ok)})
    return pd.DataFrame(rows), bool(all_ok and pooled_ok)


def fmt_money(x): return f"${float(x):.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def main():
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"ETH raw 5m coverage too low: {coverage:.6f}")
    E = build_parent_entries(x5)
    G = development_grid(x5, E)
    G.to_csv(OUT_GRID, index=False)
    sel, eligible = select_dev(G)
    H, replicated = evaluate_selected(x5, E, sel)

    if sel is None:
        status = "ETH_DISCOVERY2_Z6_NO_DEV_CANDIDATE"
        selected_trades = pd.DataFrame()
    else:
        cohort=sel["cohort"]; tp=float(sel["tp_r"]); sl=float(sel["sl_r"]); hold=int(sel["hold_min"])
        tt=[]
        for part in PARTS:
            T=run_config(x5,E,cohort,part,tp,sl,hold)
            if len(T): tt.append(T)
        selected_trades=pd.concat(tt,ignore_index=True) if tt else pd.DataFrame()
        status = "ETH_DISCOVERY2_Z6_SUPPORTED" if replicated else "ETH_DISCOVERY2_Z6_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status+"\n")
    if len(selected_trades): selected_trades.to_csv(OUT_TRADES,index=False)
    if len(H): H.to_csv(OUT_SUMMARY,index=False)

    lines=[
        "# ETH Discovery 2 — Z6 Money Geometry Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen parent: Z5 L06 entry. Fixed $500 notional, $0.75 round-trip cost, no compounding.",
        f"Frozen Development search: {len(G)} configurations.",""
    ]
    if sel is None:
        lines += ["No configuration passed the preregistered Development economic gate."]
    else:
        lines += ["## Development winner","",
            f"**{sel['cohort']} / TP {float(sel['tp_r']):.2f}R / SL {float(sel['sl_r']):.2f}R / hold {int(sel['hold_min'])}m**","",
            f"- Trades: {int(sel['trades'])}; TP/SL/timeout = {int(sel['tp_hits'])}/{int(sel['sl_hits'])}/{int(sel['timeouts'])}.",
            f"- Net WR: **{pct(sel['win_rate'])}**.",
            f"- Net PnL: **{fmt_money(sel['net_pnl'])}**; expectancy **{fmt_money(sel['expectancy'])}/trade**; net/100 trades **{fmt_money(sel['net_per_100_trades'])}**.",
            f"- PF: **{float(sel['pf']):.3f}**; max DD **{fmt_money(sel['max_dd'])}**; max loss streak **{int(sel['max_loss_streak'])}**; max win streak **{int(sel['max_win_streak'])}**.",
            f"- Positive Development blocks: {int(sel['positive_blocks'])}/4; block PnLs = [{fmt_money(sel['block1'])}, {fmt_money(sel['block2'])}, {fmt_money(sel['block3'])}, {fmt_money(sel['block4'])}].",
            "","## Historical replication","",
            "| Partition | Trades | WR | Net PnL | Exp/trade | PF | Max DD | Loss streak | Pass |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|"
        ]
        for r in H.itertuples(index=False):
            lines.append(
                f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {fmt_money(r.net_pnl)} | {fmt_money(r.expectancy)} | "
                f"{float(r.pf):.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(r.pass_) else 'FAIL'} |"
                if hasattr(r,'pass_') else
                f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {fmt_money(r.net_pnl)} | {fmt_money(r.expectancy)} | {float(r.pf):.3f} | {fmt_money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(getattr(r,'pass')) else 'FAIL'} |"
            )
        allsum=summarize_trades(selected_trades)
        lines += ["","## All historical partitions combined — descriptive only","",
            f"- Trades: {allsum['trades']}.",
            f"- Net WR: **{pct(allsum['win_rate'])}**.",
            f"- Net PnL: **{fmt_money(allsum['net_pnl'])}**; expectancy **{fmt_money(allsum['expectancy'])}/trade**; net/100 trades **{fmt_money(allsum['net_per_100_trades'])}**.",
            f"- PF: **{allsum['pf']:.3f}**; max DD **{fmt_money(allsum['max_dd'])}**; max loss streak **{allsum['max_loss_streak']}**; max win streak **{allsum['max_win_streak']}**.",
            "","## BTC A3.9 preferred consistency context","",
            "BTC reference: 139 trades, 56.83% WR, +$95.734 net, $0.6887/trade expectancy, PF 1.431, $31.636 max DD, max loss streak 4.",
        ]
        boundary=[]
        if float(sel['tp_r']) in (min(TPS),max(TPS)): boundary.append('TP')
        if float(sel['sl_r']) in (min(SLS),max(SLS)): boundary.append('SL')
        if int(sel['hold_min']) in (min(HOLDS),max(HOLDS)): boundary.append('HOLD')
        lines += ["","## Search-boundary diagnostic","", f"Winner boundary dimensions: **{', '.join(boundary) if boundary else 'NONE'}**."]
        lines += ["","## Top Development candidates","",
            "| # | Cohort | TP R | SL R | Hold | Trades | WR | Net | PF | DD | Pos blocks |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        ]
        for i,r in eligible.head(12).iterrows():
            lines.append(f"| {i+1} | {r.cohort} | {r.tp_r:.2f} | {r.sl_r:.2f} | {int(r.hold_min)} | {int(r.trades)} | {pct(r.win_rate)} | {fmt_money(r.net_pnl)} | {r.pf:.3f} | {fmt_money(r.max_dd)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","Research/shadow only. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
