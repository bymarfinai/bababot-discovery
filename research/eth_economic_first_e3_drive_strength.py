#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E3_DRIVE_STRENGTH"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = tuple(range(0, 1440, 30))
LOOKBACKS = (15, 30, 60, 120, 240, 360)
MODES = ("MOMENTUM", "REVERSAL")
STRENGTHS = (0.50, 0.67, 0.75, 0.80, 0.85)
HOLDS = (60, 120, 240, 360, 720, 960)
BAR_MIN = 5
NOTIONAL = 500.0
FEE = 0.75
ROLL_N = 60
MIN_HIST = 40


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def causal_signal_frame(x5: pd.DataFrame, clock: int, lookback: int) -> pd.DataFrame:
    start = x5.index.min().normalize()
    end = x5.index.max().normalize()
    days = pd.date_range(start, end, freq="D", tz="UTC")
    days = days[np.array([d.weekday() < 5 for d in days], dtype=bool)]
    ent_ts = days + pd.Timedelta(minutes=int(clock))
    pre_ts = ent_ts - pd.Timedelta(minutes=int(lookback))

    pi = x5.index.get_indexer(pre_ts)
    ei = x5.index.get_indexer(ent_ts)
    valid = (pi >= 0) & (ei >= 0) & ((ei - pi) == int(lookback)//BAR_MIN)
    pre_ts = pre_ts[valid]; ent_ts = ent_ts[valid]
    pi = pi[valid]; ei = ei[valid]
    op = x5.open.to_numpy(float)
    pp = op[pi]; ep = op[ei]
    drive = (ep - pp) / pp
    nz = drive != 0.0
    pre_ts = pre_ts[nz]; ent_ts = ent_ts[nz]
    pp = pp[nz]; ep = ep[nz]; drive = drive[nz]
    ab = np.abs(drive)

    strength = np.full(len(ab), np.nan, dtype=float)
    for i in range(len(ab)):
        lo = max(0, i - ROLL_N)
        prev = ab[lo:i]
        if len(prev) >= MIN_HIST:
            strength[i] = float(np.mean(prev <= ab[i]))

    return pd.DataFrame({
        "pre_ts": pre_ts,
        "entry_ts": ent_ts,
        "pre_price": pp,
        "entry_price": ep,
        "drive_return": drive,
        "strength_pct": strength,
    })


def candidate_arrays(x5: pd.DataFrame, S: pd.DataFrame, part: str, hold: int, mode: str, strength_gate: float):
    pa, pz = base.PARTS[part]
    ent_ts = pd.DatetimeIndex(S.entry_ts)
    exit_ts = ent_ts + pd.Timedelta(minutes=int(hold))
    xi = x5.index.get_indexer(exit_ts)
    ei = x5.index.get_indexer(ent_ts)
    valid_exit = (xi >= 0) & (ei >= 0) & ((xi - ei) == int(hold)//BAR_MIN)
    mask = (
        valid_exit &
        (pd.DatetimeIndex(S.pre_ts) >= pa) &
        (ent_ts >= pa) & (exit_ts < pz) &
        np.isfinite(S.strength_pct.to_numpy(float)) &
        (S.strength_pct.to_numpy(float) >= float(strength_gate))
    )
    if not np.any(mask):
        return None
    op = x5.open.to_numpy(float)
    ep = S.entry_price.to_numpy(float)[mask]
    xp = op[xi[mask]]
    drive = S.drive_return.to_numpy(float)[mask]
    drive_sign = np.where(drive > 0, 1.0, -1.0)
    direction = drive_sign if mode == "MOMENTUM" else -drive_sign
    gross_ret = direction * (xp - ep) / ep
    gross = NOTIONAL * gross_ret
    net = gross - FEE
    return {
        "pre_ts": pd.DatetimeIndex(S.pre_ts[mask]),
        "entry_ts": ent_ts[mask],
        "exit_ts": exit_ts[mask],
        "pre_price": S.pre_price.to_numpy(float)[mask],
        "entry_price": ep,
        "exit_price": xp,
        "drive_return": drive,
        "strength_pct": S.strength_pct.to_numpy(float)[mask],
        "trade_side": np.where(direction > 0, "LONG", "SHORT"),
        "gross_return": gross_ret,
        "gross_pnl": gross,
        "net_pnl": net,
    }


def summarize_arrays(A, blocks=4):
    if A is None:
        return {}
    p = np.asarray(A["net_pnl"], dtype=float)
    if len(p) == 0:
        return {}
    ml, mw = e1.streaks(p)
    out = {
        "trades": int(len(p)),
        "net_wins": int((p > 0).sum()),
        "net_losses": int((p <= 0).sum()),
        "win_rate": float((p > 0).mean()),
        "gross_pnl": float(np.asarray(A["gross_pnl"], dtype=float).sum()),
        "fees": float(FEE * len(p)),
        "net_pnl": float(p.sum()),
        "expectancy": float(p.mean()),
        "net_per_100": float(p.mean()*100.0),
        "pf": float(e1.profit_factor(p)),
        "max_dd": float(e1.max_drawdown(p)),
        "max_loss_streak": int(ml),
        "max_win_streak": int(mw),
    }
    if blocks:
        positive = 0
        for bi, ix in enumerate(np.array_split(np.arange(len(p)), blocks), 1):
            bp = p[ix]
            bnet = float(bp.sum()) if len(bp) else 0.0
            out[f"block{bi}_n"] = int(len(bp))
            out[f"block{bi}_net"] = bnet
            out[f"block{bi}_wr"] = float((bp > 0).mean()) if len(bp) else np.nan
            if bnet > 0: positive += 1
        out["positive_blocks"] = int(positive)
    return out


def dev_scan(x5):
    rows = []
    for clock in CLOCKS:
        for lb in LOOKBACKS:
            S = causal_signal_frame(x5, clock, lb)
            for hold in HOLDS:
                for mode in MODES:
                    for q in STRENGTHS:
                        A = candidate_arrays(x5, S, "development", hold, mode, q)
                        s = summarize_arrays(A, 4)
                        rows.append({
                            "clock_min_utc": clock, "clock_utc": hhmm(clock), "clock_wib": wib(clock),
                            "lookback_min": lb, "mode": mode, "strength_gate": q, "hold_min": hold, **s
                        })
    D = pd.DataFrame(rows)
    if len(D) != 17280:
        raise AssertionError(f"expected 17280 candidates, got {len(D)}")
    return D


def neighbor_keys(r):
    c=int(r.clock_min_utc); lb=int(r.lookback_min); q=float(r.strength_gate); h=int(r.hold_min); mode=r.mode
    li=LOOKBACKS.index(lb); qi=STRENGTHS.index(q); hi=HOLDS.index(h)
    keys=[((c-30)%1440,lb,q,h,mode),((c+30)%1440,lb,q,h,mode)]
    if li>0: keys.append((c,LOOKBACKS[li-1],q,h,mode))
    if li+1<len(LOOKBACKS): keys.append((c,LOOKBACKS[li+1],q,h,mode))
    if qi>0: keys.append((c,lb,STRENGTHS[qi-1],h,mode))
    if qi+1<len(STRENGTHS): keys.append((c,lb,STRENGTHS[qi+1],h,mode))
    if hi>0: keys.append((c,lb,q,HOLDS[hi-1],mode))
    if hi+1<len(HOLDS): keys.append((c,lb,q,HOLDS[hi+1],mode))
    return keys


def build_leaderboard(D):
    D=D.copy()
    D["healthy_gate"]=(
        (D.trades>=120)&(D.win_rate>=.55)&(D.net_pnl>0)&(D.expectancy>=.25)&
        (D.pf>=1.20)&(D.max_dd<=80.0)&(D.max_loss_streak<=8)&(D.positive_blocks>=3)
    )
    lookup={(int(r.clock_min_utc),int(r.lookback_min),float(r.strength_gate),int(r.hold_min),r.mode):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        keys=neighbor_keys(r); sup=0
        for k in keys:
            x=lookup[k]
            if int(x.trades)>=100 and float(x.win_rate)>=.52 and float(x.net_pnl)>0 and float(x.expectancy)>0 and float(x.pf)>=1.05 and int(x.positive_blocks)>=2:
                sup += 1
        n=len(keys)
        need=max(2, math.ceil(.50*n)) if n>=3 else n
        if n>=5: need=max(3,need)
        nav.append(n); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.healthy_gate&D.local_stable
    D["boundary"]=(
        D.lookback_min.isin((min(LOOKBACKS),max(LOOKBACKS)))|
        D.strength_gate.isin((min(STRENGTHS),max(STRENGTHS)))|
        D.hold_min.isin((min(HOLDS),max(HOLDS)))
    )
    D["mode_tie"]=D["mode"].map({"MOMENTUM":0,"REVERSAL":1})
    C=D[D.candidate_eligible].copy().sort_values(
        ["net_per_100","win_rate","pf","max_dd","max_loss_streak","trades","hold_min","strength_gate","lookback_min","clock_min_utc","mode_tie"],
        ascending=[False,False,False,True,True,False,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def make_trade_df(A, part, sel):
    if A is None: return pd.DataFrame()
    n=len(A["net_pnl"])
    return pd.DataFrame({
        "partition":part,
        "clock_utc":str(sel["clock_utc"]),"clock_wib":str(sel["clock_wib"]),
        "lookback_min":int(sel["lookback_min"]),"mode":str(sel["mode"]),
        "strength_gate":float(sel["strength_gate"]),"hold_min":int(sel["hold_min"]),
        "pre_ts":A["pre_ts"],"entry_ts":A["entry_ts"],"exit_ts":A["exit_ts"],
        "pre_price":A["pre_price"],"entry_price":A["entry_price"],"exit_price":A["exit_price"],
        "drive_return":A["drive_return"],"strength_pct":A["strength_pct"],"trade_side":A["trade_side"],
        "gross_return":A["gross_return"],"gross_pnl":A["gross_pnl"],"fee":np.full(n,FEE),
        "net_pnl":A["net_pnl"],"net_positive":np.asarray(A["net_pnl"])>0,
    })


def candidate_for(x5, part, sel):
    S=causal_signal_frame(x5,int(sel["clock_min_utc"]),int(sel["lookback_min"]))
    return candidate_arrays(x5,S,part,int(sel["hold_min"]),str(sel["mode"]),float(sel["strength_gate"]))


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    D=dev_scan(x5); D2,C=build_leaderboard(D)
    D2.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)
    lines=[
        "# ETH Economic-First Reset — E3 Causal Drive-Strength Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "No H/L/range/breakout/retest/EMA/Fibonacci. Strength uses only up to 60 earlier same-clock/lookback weekday observations.",
        "Fixed economics: **$500 notional / $0.75 round-trip fee / no compounding**.",
        f"Development candidates: **{len(D2)}**.",
        f"High-quality gate passers: **{int(D2.healthy_gate.sum())}**; high-quality + local-stability passers: **{len(C)}**.",""
    ]
    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E3_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        top=D2.sort_values(["net_per_100","win_rate","pf","max_dd"],ascending=[False,False,False,True]).head(15)
        lines += ["No candidate passed the preregistered high-WR economic + local-stability gates.","","## Best raw economics — descriptive only","",
                  "| # | UTC | WIB | Mode | LB | Strength | Hold | N | WR | Net | Exp | PF | DD | L-streak | Blocks | Healthy | Neigh |",
                  "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
        for i,r in enumerate(top.itertuples(index=False),1):
            lines.append(f"| {i} | {r.clock_utc} | {r.clock_wib} | {r.mode} | {int(r.lookback_min)}m | {float(r.strength_gate):.2f} | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.positive_blocks)}/4 | {'YES' if bool(r.healthy_gate) else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} |")
        bw=D2[D2.trades>=120].sort_values(["win_rate","expectancy"],ascending=[False,False]).iloc[0]
        lines += ["","## Highest-WR coordinate with N>=120 — descriptive only","",
                  f"**{bw['clock_utc']} UTC ({bw['clock_wib']} WIB) / {bw['mode']} / LB {int(bw['lookback_min'])}m / strength {float(bw['strength_gate']):.2f} / hold {int(bw['hold_min'])}m**: N **{int(bw['trades'])}**, WR **{pct(bw['win_rate'])}**, net **{money(bw['net_pnl'])}**, exp **{money(bw['expectancy'])}**, PF **{float(bw['pf']):.3f}**, DD **{money(bw['max_dd'])}**.",
                  "",f"**Status: {status}**","","No post-hoc rescue. Research/shadow only; no live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]
    lines += ["## Development-selected high-quality character","",
              f"**{sel['clock_utc']} UTC ({sel['clock_wib']} WIB) / {sel['mode']} / LB {int(sel['lookback_min'])}m / strength >= {float(sel['strength_gate']):.2f} / hold {int(sel['hold_min'])}m**","",
              f"N **{int(sel['trades'])}**; WR **{pct(sel['win_rate'])}**; net **{money(sel['net_pnl'])}**; exp **{money(sel['expectancy'])}/trade**; PF **{float(sel['pf']):.3f}**; DD **{money(sel['max_dd'])}**; max loss/win streak **{int(sel['max_loss_streak'])}/{int(sel['max_win_streak'])}**; positive blocks **{int(sel['positive_blocks'])}/4**; neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**."]
    Adev=candidate_for(x5,"development",sel); Tdev=make_trade_df(Adev,"development",sel)
    if bool(sel["boundary"]):
        status="ETH_ECONOMIC_FIRST_E3_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Winner touches a preregistered sentinel; holdouts remain closed and no second-best is substituted.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        A=candidate_for(x5,part,sel); s=summarize_arrays(A,0)
        ok=(s.get("trades",0)>=55 and s.get("win_rate",0)>=.53 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.10 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":bool(ok)}); allok=allok and bool(ok)
        T=make_trade_df(A,part,sel)
        if len(T): tlist.append(T)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False); pd.concat(tlist,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E3_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E3_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    allT=pd.concat(tlist,ignore_index=True).sort_values("entry_ts"); sa=e1.summarize(allT,0)
    lines += ["","## All historical partitions combined — descriptive","",
              f"N **{sa['trades']}**; WR **{pct(sa['win_rate'])}**; net **{money(sa['net_pnl'])}**; exp **{money(sa['expectancy'])}/trade**; PF **{sa['pf']:.3f}**; DD **{money(sa['max_dd'])}**; loss streak **{sa['max_loss_streak']}**.",
              "","BTC A3.9 context: WR 56.83%, exp +$0.6887/trade, PF 1.431, DD $31.636, loss streak 4.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__":
    main()
