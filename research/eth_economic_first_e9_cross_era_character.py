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
PFX = "ETH_ECONOMIC_FIRST_E9_CROSS_ERA_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = tuple(range(0, 1440, 30))
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
MODES = ("MOMENTUM", "REVERSAL")
REGIMES = ("ALL", "B0_20", "B20_40", "B40_60", "B60_80", "B80_100")
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def regime_mask(strength: np.ndarray, name: str) -> np.ndarray:
    finite = np.isfinite(strength)
    if name == "ALL": return finite
    if name == "B0_20": return finite & (strength >= 0.00) & (strength < 0.20)
    if name == "B20_40": return finite & (strength >= 0.20) & (strength < 0.40)
    if name == "B40_60": return finite & (strength >= 0.40) & (strength < 0.60)
    if name == "B60_80": return finite & (strength >= 0.60) & (strength < 0.80)
    if name == "B80_100": return finite & (strength >= 0.80) & (strength <= 1.00)
    raise ValueError(name)


def summarize_arr(net: np.ndarray, gross: np.ndarray) -> dict:
    if len(net) == 0:
        return {"trades":0,"win_rate":np.nan,"net_pnl":0.0,"expectancy":np.nan,"pf":np.nan,"max_dd":np.nan,"max_loss_streak":0,"max_win_streak":0}
    return e3.summarize(net, gross, 0)


def candidate_rows_for_pair(x5: pd.DataFrame, clock: int, lb: int):
    S = e3.signal_frame(x5, clock, lb)
    ent = pd.DatetimeIndex(S.entry_ts)
    pre = pd.DatetimeIndex(S.pre_ts)
    strength = S.strength_pct.to_numpy(float)
    sign = np.where(S.drive_return.to_numpy(float) > 0, 1.0, -1.0)
    pa, pz = base.PARTS["development"]
    rows = []

    for hold in HOLDS:
        ex, valid, xp, delta, _ = e3.hold_base(x5, S, hold)
        base_dev = valid & (pre >= pa) & (ent >= pa) & (ex < pz)
        for mode in MODES:
            direction = sign if mode == "MOMENTUM" else -sign
            gross_all = NOTIONAL * direction * delta
            net_all = gross_all - FEE
            for regime in REGIMES:
                rm = regime_mask(strength, regime)
                # Development aggregate is the union of same-calendar-year contained trades.
                year_masks = {}
                dev_mask = np.zeros(len(S), dtype=bool)
                year_stats = {}
                for y in YEARS:
                    ya = pd.Timestamp(f"{y}-01-01", tz="UTC")
                    yz = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
                    ym = base_dev & rm & (pre >= ya) & (ent >= ya) & (ex < yz)
                    year_masks[y] = ym
                    dev_mask |= ym
                    year_stats[y] = summarize_arr(net_all[ym], gross_all[ym])
                s = summarize_arr(net_all[dev_mask], gross_all[dev_mask])
                row = {
                    "clock_min_utc": clock, "clock_utc": hhmm(clock), "clock_wib": wib(clock),
                    "lookback_min": lb, "mode": mode, "strength_regime": regime, "hold_min": hold,
                    **s,
                }
                for y in YEARS:
                    ys = year_stats[y]
                    row.update({
                        f"y{y}_trades": ys.get("trades",0),
                        f"y{y}_wr": ys.get("win_rate",np.nan),
                        f"y{y}_net": ys.get("net_pnl",0.0),
                        f"y{y}_exp": ys.get("expectancy",np.nan),
                        f"y{y}_pf": ys.get("pf",np.nan),
                    })
                rows.append(row)
    return rows


def scan(x5: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for clock in CLOCKS:
        for lb in LOOKBACKS:
            rows.extend(candidate_rows_for_pair(x5, clock, lb))
    D=pd.DataFrame(rows)
    expected=len(CLOCKS)*len(LOOKBACKS)*len(HOLDS)*len(MODES)*len(REGIMES)
    if len(D)!=expected: raise AssertionError(f"expected {expected} candidates, got {len(D)}")
    return D


def gate(D: pd.DataFrame) -> pd.DataFrame:
    D=D.copy()
    agg=(
        (D.trades>=140)&(D.win_rate>=.55)&(D.net_pnl>0)&(D.expectancy>=.25)&
        (D.pf>=1.20)&(D.max_dd<=100)&(D.max_loss_streak<=8)
    )
    eras=np.ones(len(D),dtype=bool)
    for y in YEARS:
        eras &= (
            (D[f"y{y}_trades"]>=40)&(D[f"y{y}_wr"]>=.52)&(D[f"y{y}_net"]>0)&
            (D[f"y{y}_exp"]>0)&(D[f"y{y}_pf"]>=1.05)
        ).to_numpy(bool)
    D["aggregate_gate"]=agg
    D["all_eras_gate"]=eras
    D["cross_era_gate"]=agg & eras
    D["min_era_exp"]=D[[f"y{y}_exp" for y in YEARS]].min(axis=1)
    D["min_era_wr"]=D[[f"y{y}_wr" for y in YEARS]].min(axis=1)
    D["positive_era_count"]=sum((D[f"y{y}_net"]>0).astype(int) for y in YEARS)
    return D


def key(c,lb,h,mode,reg): return (int(c),int(lb),int(h),str(mode),str(reg))


def neighbor_keys(r):
    c=int(r.clock_min_utc); lb=int(r.lookback_min); h=int(r.hold_min); mode=str(r.mode); reg=str(r.strength_regime)
    li=LOOKBACKS.index(lb); hi=HOLDS.index(h)
    ks=[key((c-30)%1440,lb,h,mode,reg),key((c+30)%1440,lb,h,mode,reg)]
    if li>0: ks.append(key(c,LOOKBACKS[li-1],h,mode,reg))
    if li+1<len(LOOKBACKS): ks.append(key(c,LOOKBACKS[li+1],h,mode,reg))
    if hi>0: ks.append(key(c,lb,HOLDS[hi-1],mode,reg))
    if hi+1<len(HOLDS): ks.append(key(c,lb,HOLDS[hi+1],mode,reg))
    return ks


def build_leaderboard(D):
    D=gate(D)
    lookup={key(r.clock_min_utc,r.lookback_min,r.hold_min,r.mode,r.strength_regime):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        ks=neighbor_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            supportive=(
                int(x.trades)>=120 and float(x.win_rate)>=.52 and float(x.net_pnl)>0 and
                float(x.expectancy)>0 and float(x.pf)>=1.05 and int(x.positive_era_count)>=2
            )
            sup += int(supportive)
        n=len(ks)
        need=math.ceil(.60*n)
        if n>=5: need=max(3,need)
        elif n>=3: need=max(2,need)
        nav.append(n); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.cross_era_gate & D.local_stable
    D["boundary"]=D.lookback_min.isin((min(LOOKBACKS),max(LOOKBACKS))) | D.hold_min.isin((min(HOLDS),max(HOLDS)))
    D["mode_tie"]=D["mode"].map({"MOMENTUM":0,"REVERSAL":1})
    C=D[D.candidate_eligible].copy().sort_values(
        ["min_era_exp","min_era_wr","expectancy","win_rate","pf","max_dd","max_loss_streak","trades","hold_min","lookback_min","clock_min_utc","mode_tie"],
        ascending=[False,False,False,False,False,True,True,False,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def selected_trade_df(x5: pd.DataFrame, part: str, sel) -> pd.DataFrame:
    S=e3.signal_frame(x5,int(sel.clock_min_utc),int(sel.lookback_min))
    ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts); strength=S.strength_pct.to_numpy(float)
    ex,valid,xp,delta,sign=e3.hold_base(x5,S,int(sel.hold_min))
    pa,pz=base.PARTS[part]
    m=valid&(pre>=pa)&(ent>=pa)&(ex<pz)&regime_mask(strength,str(sel.strength_regime))
    direction=sign if str(sel.mode)=="MOMENTUM" else -sign
    gross=NOTIONAL*direction*delta; net=gross-FEE
    idx=np.where(m)[0]
    return pd.DataFrame({
        "partition":part,
        "clock_utc":str(sel.clock_utc),"clock_wib":str(sel.clock_wib),
        "lookback_min":int(sel.lookback_min),"mode":str(sel.mode),"strength_regime":str(sel.strength_regime),"hold_min":int(sel.hold_min),
        "pre_ts":pre[idx],"entry_ts":ent[idx],"exit_ts":ex[idx],
        "pre_price":S.pre_price.to_numpy(float)[idx],"entry_price":S.entry_price.to_numpy(float)[idx],"exit_price":xp[idx],
        "drive_return":S.drive_return.to_numpy(float)[idx],"strength_pct":strength[idx],
        "trade_side":np.where(direction[idx]>0,"LONG","SHORT"),
        "gross_pnl":gross[idx],"fee":FEE,"net_pnl":net[idx],"net_positive":net[idx]>0,
    })


def stats_df(T: pd.DataFrame) -> dict:
    if len(T)==0: return summarize_arr(np.array([]),np.array([]))
    return summarize_arr(T.net_pnl.to_numpy(float),T.gross_pnl.to_numpy(float))


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    D0=scan(x5); D,C=build_leaderboard(D0)
    D.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)

    lines=[
        "# ETH Economic-First E9 — Cross-Era Economic Character Search Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        f"Development candidates: **{len(D)}**.",
        f"Aggregate-gate passers: **{int(D.aggregate_gate.sum())}**; all-era gate passers: **{int(D.all_eras_gate.sum())}**; cross-era + local-stability passers: **{len(C)}**.",
        "No H/L/range/breakout/retest/EMA/Fibonacci; objective is directly WR + net economics through time.",""
    ]

    top=D.sort_values(["min_era_exp","min_era_wr","expectancy","win_rate"],ascending=[False,False,False,False]).head(15)
    lines += ["## Best cross-era persistence — descriptive atlas","",
              "| # | UTC | WIB | Mode | LB | Regime | Hold | N | WR | Exp | PF | DD | 2022 WR/Exp | 2023 WR/Exp | 2024 WR/Exp | Cross-era | Neigh |",
              "|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for i,r in enumerate(top.itertuples(index=False),1):
        lines.append(
            f"| {i} | {r.clock_utc} | {r.clock_wib} | {r.mode} | {int(r.lookback_min)}m | {r.strength_regime} | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | "
            f"{pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | {'YES' if r.cross_era_gate else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} |"
        )

    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E9_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        high=D[D.trades>=140].sort_values(["win_rate","expectancy"],ascending=[False,False]).head(10)
        lines += ["","## Highest-WR Development coordinates — descriptive only","",
                  "| # | UTC | Mode | LB | Regime | Hold | N | WR | Net | Exp | PF | Positive eras |",
                  "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
        for i,r in enumerate(high.itertuples(index=False),1):
            lines.append(f"| {i} | {r.clock_utc} | {r.mode} | {int(r.lookback_min)}m | {r.strength_regime} | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {int(r.positive_era_count)}/3 |")
        lines += ["",f"**Status: {status}**","","No coordinate earned OOS exposure. Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]
    lines += ["","## Development-selected persistent character","",
              f"**{sel.clock_utc} UTC ({sel.clock_wib} WIB) / {sel['mode']} / LB {int(sel.lookback_min)}m / {sel.strength_regime} / hold {int(sel.hold_min)}m**","",
              f"N **{int(sel.trades)}**, WR **{pct(sel.win_rate)}**, net **{money(sel.net_pnl)}**, exp **{money(sel.expectancy)}/trade**, PF **{sel.pf:.3f}**, DD **{money(sel.max_dd)}**, loss streak **{int(sel.max_loss_streak)}**, min-era exp **{money(sel.min_era_exp)}**, min-era WR **{pct(sel.min_era_wr)}**, neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**.",
              f"2022: N{int(sel.y2022_trades)} / WR {pct(sel.y2022_wr)} / exp {money(sel.y2022_exp)} / PF {sel.y2022_pf:.3f}; 2023: N{int(sel.y2023_trades)} / WR {pct(sel.y2023_wr)} / exp {money(sel.y2023_exp)} / PF {sel.y2023_pf:.3f}; 2024: N{int(sel.y2024_trades)} / WR {pct(sel.y2024_wr)} / exp {money(sel.y2024_exp)} / PF {sel.y2024_pf:.3f}."
    ]

    Tdev=selected_trade_df(x5,"development",sel)
    if bool(sel.boundary):
        status="ETH_ECONOMIC_FIRST_E9_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Winner touches a preregistered lookback/hold sentinel; holdouts remain closed.","",f"**Status: {status}**","","Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        T=selected_trade_df(x5,part,sel); s=stats_df(T)
        ok=(s.get("trades",0)>=50 and s.get("win_rate",0)>=.52 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.05 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":bool(ok)}); tlist.append(T); allok &= bool(ok)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False)
    allT=pd.concat(tlist,ignore_index=True).sort_values("entry_ts"); allT.to_csv(OUT_TRADES,index=False)
    sa=stats_df(allT)
    status="ETH_ECONOMIC_FIRST_E9_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E9_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    lines += ["","## Combined historical — descriptive","",
              f"N **{int(sa['trades'])}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{int(sa['max_loss_streak'])}**.","",
              "BTC A3.9 context: WR56.83%, exp+$0.6887/trade, PF1.431, DD$31.636, loss streak4.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
