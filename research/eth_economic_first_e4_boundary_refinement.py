#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1
import eth_economic_first_e3_drive_strength_fast as e3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E4_BOUNDARY_REFINEMENT"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 20 * 60 + 30
MODE = "REVERSAL"
HOLD = 720
LOOKBACKS = (5, 10, 15, 20, 30)
STRENGTHS = (0.75, 0.80, 0.825, 0.85, 0.875, 0.90, 0.925)
FEE = 0.75
NOTIONAL = 500.0


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def arrays_for(x5, S, part, q):
    ent = pd.DatetimeIndex(S.entry_ts)
    pre = pd.DatetimeIndex(S.pre_ts)
    strength = S.strength_pct.to_numpy(float)
    ex, valid, xp, delta, sign = e3.hold_base(x5, S, HOLD)
    pa, pz = base.PARTS[part]
    m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & np.isfinite(strength) & (strength >= q)
    direction = -sign
    gross = NOTIONAL * direction * delta
    net = gross - FEE
    return ex, xp, direction, gross, net, m


def scan_dev(x5):
    rows=[]
    for lb in LOOKBACKS:
        S=e3.signal_frame(x5,CLOCK,lb)
        for q in STRENGTHS:
            _,_,_,gross,net,m=arrays_for(x5,S,"development",q)
            s=e3.summarize(net[m],gross[m],4)
            rows.append({"clock_min_utc":CLOCK,"clock_utc":"20:30","clock_wib":"03:30","mode":MODE,
                         "lookback_min":lb,"strength_gate":q,"hold_min":HOLD,**s})
    D=pd.DataFrame(rows)
    if len(D)!=35: raise AssertionError(f"expected 35 candidates, got {len(D)}")
    ref=D[(D.lookback_min==15)&(D.strength_gate==0.85)].iloc[0]
    if not (int(ref.trades)==131 and abs(float(ref.win_rate)-0.5648854961832062)<1e-12 and abs(float(ref.net_pnl)-346.11865118480955)<1e-8):
        raise AssertionError("E3 coordinate reproduction invariant failed")
    return D


def neighbors(r):
    lb=int(r.lookback_min); q=float(r.strength_gate)
    li=LOOKBACKS.index(lb); qi=STRENGTHS.index(q); out=[]
    if li>0: out.append((LOOKBACKS[li-1],q))
    if li+1<len(LOOKBACKS): out.append((LOOKBACKS[li+1],q))
    if qi>0: out.append((lb,STRENGTHS[qi-1]))
    if qi+1<len(STRENGTHS): out.append((lb,STRENGTHS[qi+1]))
    return out


def build(D):
    D=D.copy()
    D["healthy_gate"]=(
        (D.trades>=80)&(D.win_rate>=.55)&(D.net_pnl>0)&(D.expectancy>=.25)&
        (D.pf>=1.20)&(D.max_dd<=80)&(D.max_loss_streak<=8)&(D.positive_blocks>=3)
    )
    lookup={(int(r.lookback_min),float(r.strength_gate)):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        ks=neighbors(r); sup=0
        for k in ks:
            x=lookup[k]
            sup += int(int(x.trades)>=60 and float(x.win_rate)>=.52 and float(x.net_pnl)>0 and float(x.expectancy)>0 and float(x.pf)>=1.05 and int(x.positive_blocks)>=2)
        n=len(ks)
        need=n if n<2 else (max(2,math.ceil(.50*n)) if n>=3 else 1)
        nav.append(n); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.healthy_gate&D.local_stable
    D["boundary"]=D.lookback_min.isin((min(LOOKBACKS),max(LOOKBACKS)))|D.strength_gate.isin((min(STRENGTHS),max(STRENGTHS)))
    C=D[D.candidate_eligible].copy().sort_values(
        ["net_per_100","win_rate","pf","max_dd","max_loss_streak","trades","lookback_min","strength_gate"],
        ascending=[False,False,False,True,True,False,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def trade_df(x5,part,sel):
    lb=int(sel["lookback_min"]); q=float(sel["strength_gate"])
    S=e3.signal_frame(x5,CLOCK,lb)
    ex,xp,direction,gross,net,m=arrays_for(x5,S,part,q)
    return pd.DataFrame({
        "partition":part,"clock_utc":"20:30","clock_wib":"03:30","mode":MODE,
        "lookback_min":lb,"strength_gate":q,"hold_min":HOLD,
        "pre_ts":pd.DatetimeIndex(S.pre_ts)[m],"entry_ts":pd.DatetimeIndex(S.entry_ts)[m],"exit_ts":ex[m],
        "pre_price":S.pre_price.to_numpy(float)[m],"entry_price":S.entry_price.to_numpy(float)[m],"exit_price":xp[m],
        "drive_return":S.drive_return.to_numpy(float)[m],"strength_pct":S.strength_pct.to_numpy(float)[m],
        "trade_side":np.where(direction[m]>0,"LONG","SHORT"),"gross_pnl":gross[m],"fee":FEE,
        "net_pnl":net[m],"net_positive":net[m]>0,
    })


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    D=scan_dev(x5); D2,C=build(D)
    D2.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)
    lines=["# ETH Economic-First E4 — Drive-Strength Boundary Refinement Result","",
           f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Frozen: **20:30 UTC / REVERSAL / hold 720m**. Refined only lookback and causal-strength boundaries.",
           "E3 reproduction invariant at LB15 / strength0.85 matched exactly: N131, WR56.49%, net +$346.12.",
           f"Development candidates: **{len(D2)}**.",
           f"High-quality gate passers: **{int(D2.healthy_gate.sum())}**; high-quality + local-stability passers: **{len(C)}**.",""]
    top=D2.sort_values(["net_per_100","win_rate","pf","max_dd"],ascending=[False,False,False,True]).head(12)
    lines += ["## Development atlas — top economics","",
              "| # | LB | Strength | N | WR | Net | Exp | PF | DD | L-streak | Blocks | Healthy | Neigh | Eligible |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    for i,r in enumerate(top.itertuples(index=False),1):
        lines.append(f"| {i} | {int(r.lookback_min)}m | {float(r.strength_gate):.3f} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.positive_blocks)}/4 | {'YES' if r.healthy_gate else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {'YES' if r.candidate_eligible else 'NO'} |")
    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E4_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        lines += ["",f"**Status: {status}**","","No post-hoc rescue."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]
    lines += ["","## Development-selected refinement","",
              f"**20:30 UTC (03:30 WIB) / REVERSAL / LB {int(sel['lookback_min'])}m / strength >= {float(sel['strength_gate']):.3f} / hold720m**","",
              f"N **{int(sel['trades'])}**; WR **{pct(sel['win_rate'])}**; net **{money(sel['net_pnl'])}**; exp **{money(sel['expectancy'])}/trade**; PF **{float(sel['pf']):.3f}**; DD **{money(sel['max_dd'])}**; loss streak **{int(sel['max_loss_streak'])}**; blocks **{int(sel['positive_blocks'])}/4**; neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**."]
    Tdev=trade_df(x5,"development",sel)
    if bool(sel["boundary"]):
        status="ETH_ECONOMIC_FIRST_E4_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Winner touches an E4 outer sentinel; holdouts remain closed.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        T=trade_df(x5,part,sel); s=e3.summarize(T.net_pnl.to_numpy(float),T.gross_pnl.to_numpy(float),0)
        ok=(s.get("trades",0)>=40 and s.get("win_rate",0)>=.53 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.10 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":bool(ok)}); allok &= bool(ok); tlist.append(T)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False); pd.concat(tlist,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E4_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E4_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    allT=pd.concat(tlist,ignore_index=True).sort_values("entry_ts")
    sa=e3.summarize(allT.net_pnl.to_numpy(float),allT.gross_pnl.to_numpy(float),0)
    lines += ["","## Combined historical — descriptive","",
              f"N **{sa['trades']}**; WR **{pct(sa['win_rate'])}**; net **{money(sa['net_pnl'])}**; exp **{money(sa['expectancy'])}/trade**; PF **{sa['pf']:.3f}**; DD **{money(sa['max_dd'])}**; loss streak **{sa['max_loss_streak']}**.",
              "","BTC A3.9 context: WR56.83%, exp+$0.6887/trade, PF1.431, DD$31.636, loss streak4.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
