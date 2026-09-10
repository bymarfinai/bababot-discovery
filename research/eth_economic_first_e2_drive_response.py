#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E2_DRIVE_RESPONSE"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = tuple(range(0, 1440, 30))
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (15, 30, 60, 120, 240, 360, 720)
MODES = ("MOMENTUM", "REVERSAL")
BAR_MIN = 5
NOTIONAL = 500.0
FEE = 0.75


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def trade_frame(x5: pd.DataFrame, part: str, clock: int, lookback: int, hold: int, mode: str) -> pd.DataFrame:
    pa, pz = base.PARTS[part]
    days = pd.date_range(pa.normalize(), pz.normalize(), freq="D", tz="UTC")
    days = days[np.array([d.weekday() < 5 for d in days], dtype=bool)]
    ent_ts = days + pd.Timedelta(minutes=int(clock))
    pre_ts = ent_ts - pd.Timedelta(minutes=int(lookback))
    exit_ts = ent_ts + pd.Timedelta(minutes=int(hold))
    keep = (pre_ts >= pa) & (ent_ts >= pa) & (exit_ts < pz) & (exit_ts < base.END)
    pre_ts = pre_ts[keep]; ent_ts = ent_ts[keep]; exit_ts = exit_ts[keep]
    if len(ent_ts) == 0:
        return pd.DataFrame()

    pi = x5.index.get_indexer(pre_ts)
    ei = x5.index.get_indexer(ent_ts)
    xi = x5.index.get_indexer(exit_ts)
    complete = (
        (pi >= 0) & (ei >= 0) & (xi >= 0) &
        ((ei - pi) == int(lookback)//BAR_MIN) &
        ((xi - ei) == int(hold)//BAR_MIN)
    )
    pre_ts = pre_ts[complete]; ent_ts = ent_ts[complete]; exit_ts = exit_ts[complete]
    pi = pi[complete]; ei = ei[complete]; xi = xi[complete]
    if len(ei) == 0:
        return pd.DataFrame()

    op = x5.open.to_numpy(float)
    pp = op[pi]; ep = op[ei]; xp = op[xi]
    drive = (ep - pp) / pp
    nz = drive != 0.0
    pre_ts = pre_ts[nz]; ent_ts = ent_ts[nz]; exit_ts = exit_ts[nz]
    pp = pp[nz]; ep = ep[nz]; xp = xp[nz]; drive = drive[nz]
    if len(ep) == 0:
        return pd.DataFrame()

    drive_sign = np.where(drive > 0, 1.0, -1.0)
    direction = drive_sign if mode == "MOMENTUM" else -drive_sign
    forward = (xp - ep) / ep
    gross_ret = direction * forward
    gross = NOTIONAL * gross_ret
    net = gross - FEE
    trade_side = np.where(direction > 0, "LONG", "SHORT")

    return pd.DataFrame({
        "partition": part,
        "clock_min_utc": int(clock),
        "clock_utc": hhmm(clock),
        "clock_wib": wib(clock),
        "lookback_min": int(lookback),
        "hold_min": int(hold),
        "mode": mode,
        "pre_ts": pre_ts,
        "entry_ts": ent_ts,
        "exit_ts": exit_ts,
        "pre_price": pp,
        "entry_price": ep,
        "exit_price": xp,
        "drive_return": drive,
        "trade_side": trade_side,
        "gross_return": gross_ret,
        "gross_pnl": gross,
        "fee": FEE,
        "net_pnl": net,
        "net_positive": net > 0,
    })


def dev_scan(x5):
    rows = []
    for clock in CLOCKS:
        for lookback in LOOKBACKS:
            for hold in HOLDS:
                for mode in MODES:
                    T = trade_frame(x5, "development", clock, lookback, hold, mode)
                    s = e1.summarize(T, 4)
                    rows.append({
                        "clock_min_utc": clock, "clock_utc": hhmm(clock), "clock_wib": wib(clock),
                        "lookback_min": lookback, "hold_min": hold, "mode": mode, **s
                    })
    D = pd.DataFrame(rows)
    if len(D) != 4032:
        raise AssertionError(f"expected 4032 candidates, got {len(D)}")
    return D


def neighbor_keys(r):
    c = int(r.clock_min_utc); lb = int(r.lookback_min); h = int(r.hold_min); mode = r.mode
    li = LOOKBACKS.index(lb); hi = HOLDS.index(h)
    keys = [((c-30)%1440, lb, h, mode), ((c+30)%1440, lb, h, mode)]
    if li > 0: keys.append((c, LOOKBACKS[li-1], h, mode))
    if li+1 < len(LOOKBACKS): keys.append((c, LOOKBACKS[li+1], h, mode))
    if hi > 0: keys.append((c, lb, HOLDS[hi-1], mode))
    if hi+1 < len(HOLDS): keys.append((c, lb, HOLDS[hi+1], mode))
    return keys


def build_leaderboard(D):
    D = D.copy()
    D["healthy_gate"] = (
        (D.trades >= 700) & (D.win_rate >= .52) & (D.net_pnl > 0) &
        (D.expectancy >= .10) & (D.pf >= 1.10) & (D.max_dd <= 100.0) &
        (D.max_loss_streak <= 10) & (D.positive_blocks >= 3)
    )
    lookup = {(int(r.clock_min_utc), int(r.lookback_min), int(r.hold_min), r.mode): r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        keys = neighbor_keys(r); sup = 0
        for k in keys:
            x = lookup[k]
            if (
                int(x.trades) >= 700 and float(x.win_rate) >= .505 and float(x.net_pnl) > 0 and
                float(x.expectancy) > 0 and float(x.pf) >= 1.00 and int(x.positive_blocks) >= 2
            ):
                sup += 1
        n = len(keys)
        need = max(2, math.ceil(.60*n)) if n >= 3 else n
        if n >= 5: need = max(3, need)
        nav.append(n); ns.append(sup); stable.append(sup >= need)
    D["neighbors_available"] = nav; D["neighbors_supportive"] = ns; D["local_stable"] = stable
    D["candidate_eligible"] = D.healthy_gate & D.local_stable
    D["boundary"] = D.lookback_min.isin((min(LOOKBACKS), max(LOOKBACKS))) | D.hold_min.isin((min(HOLDS), max(HOLDS)))
    D["mode_tie"] = D["mode"].map({"MOMENTUM":0, "REVERSAL":1})
    C = D[D.candidate_eligible].copy()
    C = C.sort_values(
        ["net_per_100","win_rate","pf","max_dd","max_loss_streak","hold_min","lookback_min","clock_min_utc","mode_tie"],
        ascending=[False,False,False,True,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return D, C


def holdout(x5, sel):
    rows=[]; trades=[]; all_ok=True
    for part in ("external","reference_validation"):
        T = trade_frame(x5, part, int(sel["clock_min_utc"]), int(sel["lookback_min"]), int(sel["hold_min"]), str(sel["mode"]))
        s = e1.summarize(T, 0)
        ok = (
            s.get("trades",0) >= 300 and s.get("win_rate",0) >= .505 and s.get("net_pnl",-1) > 0 and
            s.get("expectancy",-1) > 0 and s.get("pf",0) >= 1.05 and s.get("max_loss_streak",99) <= 15
        )
        rows.append({"partition":part, **s, "replication_pass":bool(ok)})
        if len(T): trades.append(T)
        all_ok = all_ok and bool(ok)
    return pd.DataFrame(rows), trades, all_ok


def descriptive_top(D, n=15):
    return D.sort_values(["net_per_100","win_rate","pf","max_dd"], ascending=[False,False,False,True]).head(n)


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low {coverage}")
    D = dev_scan(x5)
    D2, C = build_leaderboard(D)
    D2.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)

    lines=[
        "# ETH Economic-First Reset — E2 Drive Response Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "No H/L/range/breakout/retest/EMA/Fibonacci. Signal is only pre-entry return sign.",
        "Fixed economics: **$500 notional / $0.75 round-trip fee / no compounding**.",
        f"Development candidates: **{len(D2)}**.",
        f"Healthy-gate passers: **{int(D2.healthy_gate.sum())}**; healthy + local-stability passers: **{len(C)}**.",""
    ]
    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E2_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status+"\n")
        top=descriptive_top(D2)
        lines += ["No Development candidate passed the preregistered economic-first + local-stability gates.","","## Best raw economics — descriptive only","",
                  "| # | UTC | WIB | Mode | Lookback | Hold | WR | Net | Exp | PF | DD | L-streak | Blocks | Healthy | Neigh |",
                  "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
        for i,r in enumerate(top.itertuples(index=False),1):
            lines.append(f"| {i} | {r.clock_utc} | {r.clock_wib} | {r.mode} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.positive_blocks)}/4 | {'YES' if bool(r.healthy_gate) else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} |")
        bw=D2.sort_values(["win_rate","expectancy"],ascending=[False,False]).iloc[0]
        lines += ["","## Highest-WR Development coordinate — descriptive only","",
                  f"**{bw['clock_utc']} UTC ({bw['clock_wib']} WIB) / {bw['mode']} / lookback {int(bw['lookback_min'])}m / hold {int(bw['hold_min'])}m**: WR **{pct(bw['win_rate'])}**, net **{money(bw['net_pnl'])}**, exp **{money(bw['expectancy'])}**, PF **{float(bw['pf']):.3f}**, DD **{money(bw['max_dd'])}**.",
                  "",f"**Status: {status}**","","Drive-response family is closed; no post-hoc rescue.","Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]
    lines += ["## Development-selected economic character","",
              f"**{sel['clock_utc']} UTC ({sel['clock_wib']} WIB) / {sel['mode']} / lookback {int(sel['lookback_min'])}m / hold {int(sel['hold_min'])}m**","",
              f"Trades **{int(sel['trades'])}**; WR **{pct(sel['win_rate'])}**; net **{money(sel['net_pnl'])}**; exp **{money(sel['expectancy'])}/trade**; PF **{float(sel['pf']):.3f}**; DD **{money(sel['max_dd'])}**; loss streak **{int(sel['max_loss_streak'])}**; blocks **{int(sel['positive_blocks'])}/4**; neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**."]
    Tdev=trade_frame(x5,"development",int(sel["clock_min_utc"]),int(sel["lookback_min"]),int(sel["hold_min"]),str(sel["mode"]))
    if bool(sel["boundary"]):
        status="ETH_ECONOMIC_FIRST_E2_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Selected coordinate touches a preregistered lookback/hold sentinel. Holdouts remain closed.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    H,ht,supported=holdout(x5,sel); H.to_csv(OUT_SUMMARY,index=False); pd.concat([Tdev]+ht,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E2_SUPPORTED" if supported else "ETH_ECONOMIC_FIRST_E2_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | Trades | WR | Net | Exp | PF | DD | Loss streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    allT=pd.concat([Tdev]+ht,ignore_index=True); sa=e1.summarize(allT,0)
    lines += ["","## All historical partitions combined — descriptive","",
              f"Trades **{sa['trades']}**; WR **{pct(sa['win_rate'])}**; net **{money(sa['net_pnl'])}**; exp **{money(sa['expectancy'])}/trade**; PF **{sa['pf']:.3f}**; DD **{money(sa['max_dd'])}**; loss streak **{sa['max_loss_streak']}**.",
              "","## BTC A3.9 context","","BTC WR 56.83%, exp +$0.6887/trade, PF 1.431, DD $31.636, loss streak 4.","",
              f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__":
    main()
