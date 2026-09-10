#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E3_DRIVE_STRENGTH_FAST"
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


def signal_frame(x5: pd.DataFrame, clock: int, lookback: int) -> pd.DataFrame:
    days = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq="D", tz="UTC")
    days = days[np.array([d.weekday() < 5 for d in days], dtype=bool)]
    ent = days + pd.Timedelta(minutes=clock)
    pre = ent - pd.Timedelta(minutes=lookback)
    pi = x5.index.get_indexer(pre)
    ei = x5.index.get_indexer(ent)
    valid = (pi >= 0) & (ei >= 0) & ((ei - pi) == lookback // BAR_MIN)
    ent = ent[valid]; pre = pre[valid]; pi = pi[valid]; ei = ei[valid]
    op = x5.open.to_numpy(float)
    pp = op[pi]; ep = op[ei]
    drive = (ep - pp) / pp
    nz = drive != 0.0
    ent = ent[nz]; pre = pre[nz]; ei = ei[nz]; pp = pp[nz]; ep = ep[nz]; drive = drive[nz]
    ab = np.abs(drive)
    strength = np.full(len(ab), np.nan, float)
    for i in range(MIN_HIST, len(ab)):
        prev = ab[max(0, i - ROLL_N):i]
        if len(prev) >= MIN_HIST:
            strength[i] = np.mean(prev <= ab[i])
    return pd.DataFrame({
        "pre_ts": pre, "entry_ts": ent, "entry_ix": ei,
        "pre_price": pp, "entry_price": ep,
        "drive_return": drive, "strength_pct": strength,
    })


def hold_base(x5: pd.DataFrame, S: pd.DataFrame, hold: int):
    ent = pd.DatetimeIndex(S.entry_ts)
    ex = ent + pd.Timedelta(minutes=hold)
    xi = x5.index.get_indexer(ex)
    ei = S.entry_ix.to_numpy(int)
    valid = (xi >= 0) & ((xi - ei) == hold // BAR_MIN)
    xp = np.full(len(S), np.nan, float)
    ok = xi >= 0
    xp[ok] = x5.open.to_numpy(float)[xi[ok]]
    delta_ret = (xp - S.entry_price.to_numpy(float)) / S.entry_price.to_numpy(float)
    sign = np.where(S.drive_return.to_numpy(float) > 0, 1.0, -1.0)
    return ex, valid, xp, delta_ret, sign


def summarize(net: np.ndarray, gross: np.ndarray, blocks=4):
    p = np.asarray(net, float)
    g = np.asarray(gross, float)
    if len(p) == 0:
        return {}
    ml, mw = e1.streaks(p)
    out = {
        "trades": len(p), "net_wins": int((p > 0).sum()), "net_losses": int((p <= 0).sum()),
        "win_rate": float((p > 0).mean()), "gross_pnl": float(g.sum()), "fees": float(FEE * len(p)),
        "net_pnl": float(p.sum()), "expectancy": float(p.mean()), "net_per_100": float(p.mean() * 100),
        "pf": float(e1.profit_factor(p)), "max_dd": float(e1.max_drawdown(p)),
        "max_loss_streak": int(ml), "max_win_streak": int(mw),
    }
    if blocks:
        positive = 0
        for bi, ix in enumerate(np.array_split(np.arange(len(p)), blocks), 1):
            bp = p[ix]
            bn = float(bp.sum()) if len(bp) else 0.0
            out[f"block{bi}_n"] = len(bp)
            out[f"block{bi}_net"] = bn
            out[f"block{bi}_wr"] = float((bp > 0).mean()) if len(bp) else np.nan
            positive += int(bn > 0)
        out["positive_blocks"] = positive
    return out


def dev_scan(x5):
    pa, pz = base.PARTS["development"]
    rows = []
    for clock in CLOCKS:
        for lb in LOOKBACKS:
            S = signal_frame(x5, clock, lb)
            ent = pd.DatetimeIndex(S.entry_ts)
            pre = pd.DatetimeIndex(S.pre_ts)
            strength = S.strength_pct.to_numpy(float)
            for hold in HOLDS:
                ex, valid, xp, delta, sign = hold_base(x5, S, hold)
                partmask = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & np.isfinite(strength)
                for mode in MODES:
                    direction = sign if mode == "MOMENTUM" else -sign
                    gross_all = NOTIONAL * direction * delta
                    net_all = gross_all - FEE
                    for q in STRENGTHS:
                        m = partmask & (strength >= q)
                        s = summarize(net_all[m], gross_all[m], 4)
                        rows.append({
                            "clock_min_utc": clock, "clock_utc": hhmm(clock), "clock_wib": wib(clock),
                            "lookback_min": lb, "mode": mode, "strength_gate": q, "hold_min": hold, **s,
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


def leaderboard(D):
    D=D.copy()
    D["healthy_gate"]=(
        (D.trades>=120)&(D.win_rate>=.55)&(D.net_pnl>0)&(D.expectancy>=.25)&
        (D.pf>=1.20)&(D.max_dd<=80)&(D.max_loss_streak<=8)&(D.positive_blocks>=3)
    )
    lookup={(int(r.clock_min_utc),int(r.lookback_min),float(r.strength_gate),int(r.hold_min),r.mode):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        keys=neighbor_keys(r); sup=0
        for k in keys:
            x=lookup[k]
            sup += int(int(x.trades)>=100 and float(x.win_rate)>=.52 and float(x.net_pnl)>0 and float(x.expectancy)>0 and float(x.pf)>=1.05 and int(x.positive_blocks)>=2)
        n=len(keys); need=max(2,math.ceil(.50*n)) if n>=3 else n
        if n>=5: need=max(3,need)
        nav.append(n); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.healthy_gate&D.local_stable
    D["boundary"]=D.lookback_min.isin((15,360))|D.strength_gate.isin((.50,.85))|D.hold_min.isin((60,960))
    D["mode_tie"]=D["mode"].map({"MOMENTUM":0,"REVERSAL":1})
    C=D[D.candidate_eligible].copy().sort_values(
        ["net_per_100","win_rate","pf","max_dd","max_loss_streak","trades","hold_min","strength_gate","lookback_min","clock_min_utc","mode_tie"],
        ascending=[False,False,False,True,True,False,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def selected_arrays(x5, part, sel):
    S=signal_frame(x5,int(sel.clock_min_utc),int(sel.lookback_min))
    ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts); strength=S.strength_pct.to_numpy(float)
    ex,valid,xp,delta,sign=hold_base(x5,S,int(sel.hold_min))
    pa,pz=base.PARTS[part]
    m=valid&(pre>=pa)&(ent>=pa)&(ex<pz)&np.isfinite(strength)&(strength>=float(sel.strength_gate))
    direction=sign if sel.mode=="MOMENTUM" else -sign
    gross=NOTIONAL*direction*delta; net=gross-FEE
    return S,ex,xp,direction,gross,net,m


def trade_df(x5,part,sel):
    S,ex,xp,direction,gross,net,m=selected_arrays(x5,part,sel)
    return pd.DataFrame({
        "partition":part,"clock_utc":sel.clock_utc,"clock_wib":sel.clock_wib,
        "lookback_min":int(sel.lookback_min),"mode":sel.mode,"strength_gate":float(sel.strength_gate),"hold_min":int(sel.hold_min),
        "pre_ts":pd.DatetimeIndex(S.pre_ts)[m],"entry_ts":pd.DatetimeIndex(S.entry_ts)[m],"exit_ts":ex[m],
        "pre_price":S.pre_price.to_numpy(float)[m],"entry_price":S.entry_price.to_numpy(float)[m],"exit_price":xp[m],
        "drive_return":S.drive_return.to_numpy(float)[m],"strength_pct":S.strength_pct.to_numpy(float)[m],
        "trade_side":np.where(direction[m]>0,"LONG","SHORT"),"gross_pnl":gross[m],"fee":FEE,"net_pnl":net[m],"net_positive":net[m]>0,
    })


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    D=dev_scan(x5); D2,C=leaderboard(D)
    D2.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)
    lines=["# ETH Economic-First E3 Causal Drive-Strength — Vectorized Equivalent Result","",
           f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Scientific definitions, candidate universe, gates, ranking, partitions, and economics are identical to the preregistered E3 runner; only repeated computation was vectorized.",
           f"Development candidates: **{len(D2)}**.",
           f"High-quality gate passers: **{int(D2.healthy_gate.sum())}**; high-quality + local-stability passers: **{len(C)}**.",""]
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
                  f"**{bw.clock_utc} UTC ({bw.clock_wib} WIB) / {bw.mode} / LB {int(bw.lookback_min)}m / strength {float(bw.strength_gate):.2f} / hold {int(bw.hold_min)}m**: N **{int(bw.trades)}**, WR **{pct(bw.win_rate)}**, net **{money(bw.net_pnl)}**, exp **{money(bw.expectancy)}**, PF **{float(bw.pf):.3f}**, DD **{money(bw.max_dd)}**.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]
    lines += ["## Development-selected character","",
              f"**{sel.clock_utc} UTC ({sel.clock_wib} WIB) / {sel.mode} / LB {int(sel.lookback_min)}m / strength >= {float(sel.strength_gate):.2f} / hold {int(sel.hold_min)}m**","",
              f"N **{int(sel.trades)}**; WR **{pct(sel.win_rate)}**; net **{money(sel.net_pnl)}**; exp **{money(sel.expectancy)}/trade**; PF **{float(sel.pf):.3f}**; DD **{money(sel.max_dd)}**; loss streak **{int(sel.max_loss_streak)}**; blocks **{int(sel.positive_blocks)}/4**; neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**."]
    Tdev=trade_df(x5,"development",sel)
    if bool(sel.boundary):
        status="ETH_ECONOMIC_FIRST_E3_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Winner touches a preregistered sentinel; holdouts remain closed.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        T=trade_df(x5,part,sel); s=summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float),0)
        ok=(s.get("trades",0)>=55 and s.get("win_rate",0)>=.53 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.10 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":ok}); allok &= ok; tlist.append(T)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False); pd.concat(tlist,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E3_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E3_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    lines += ["",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
