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
PFX = "ETH_ECONOMIC_FIRST_E11_MARKET_STATE_CHARACTER"
OUT_PANEL = ROOT / f"{PFX}_ClockPanel.csv"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = tuple(range(0, 1440, 30))
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
MODES = ("MOMENTUM", "REVERSAL")
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75
ROLL_N = 60
MIN_HIST = 40
BAR_MIN = 5
BINS = ("LOW", "MID", "HIGH")


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def summarize(net, gross):
    net = np.asarray(net, float); gross = np.asarray(gross, float)
    if len(net) == 0:
        return {"trades":0,"win_rate":np.nan,"net_pnl":0.0,"expectancy":np.nan,"pf":np.nan,"max_dd":np.nan,"max_loss_streak":0,"max_win_streak":0}
    return e3.summarize(net, gross, 0)


def causal_percentile(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan, float)
    for i in range(MIN_HIST, len(x)):
        prev = x[max(0, i-ROLL_N):i]
        prev = prev[np.isfinite(prev)]
        if len(prev) >= MIN_HIST and np.isfinite(x[i]):
            out[i] = float(np.mean(prev <= x[i]))
    return out


def state_frame(x5: pd.DataFrame, clock: int, lb: int) -> pd.DataFrame:
    S = e3.signal_frame(x5, clock, lb).copy()
    idx = x5.index
    op = x5.open.to_numpy(float)
    hi = x5.high.to_numpy(float)
    lo = x5.low.to_numpy(float)
    pi = idx.get_indexer(pd.DatetimeIndex(S.pre_ts))
    ei = S.entry_ix.to_numpy(int)

    eff = np.full(len(S), np.nan, float)
    rv = np.full(len(S), np.nan, float)
    rr = np.full(len(S), np.nan, float)
    ext = np.full(len(S), np.nan, float)

    drive = S.drive_return.to_numpy(float)
    for j, (a, b) in enumerate(zip(pi, ei)):
        if a < 0 or b <= a or (b-a) != lb // BAR_MIN:
            continue
        path = op[a:b+1]  # includes entry open; known at decision time
        d = np.diff(path)
        denom = float(np.abs(d).sum())
        eff[j] = abs(path[-1] - path[0]) / denom if denom > 0 else np.nan
        lr = np.diff(np.log(path))
        rv[j] = float(np.std(lr, ddof=0)) if len(lr) else np.nan
        H = float(np.max(hi[a:b]))  # completed pre-entry bars only
        L = float(np.min(lo[a:b]))
        width = H - L
        rr[j] = width / path[0] if path[0] > 0 else np.nan
        if width > 0:
            raw = (path[-1]-L)/width if drive[j] > 0 else (H-path[-1])/width
            ext[j] = float(np.clip(raw, 0.0, 1.0))

    S["eff"] = eff; S["rv"] = rv; S["range_norm"] = rr; S["ext"] = ext
    S["eff_pct"] = causal_percentile(eff)
    S["rv_pct"] = causal_percentile(rv)
    S["range_pct"] = causal_percentile(rr)
    S["ext_pct"] = causal_percentile(ext)
    return S


def bin_mask(x: np.ndarray, b: str) -> np.ndarray:
    x = np.asarray(x, float); f = np.isfinite(x)
    if b == "LOW": return f & (x >= 0.0) & (x < 1/3)
    if b == "MID": return f & (x >= 1/3) & (x < 2/3)
    if b == "HIGH": return f & (x >= 2/3) & (x <= 1.0)
    raise ValueError(b)


def state_rules():
    rules=[]
    feats=("EFF","RV","RANGE","EXT")
    for f in feats:
        for b in BINS: rules.append((f"{f}_{b}", f, b, None, None))
    pairs=(("EFF","RV"),("EFF","RANGE"),("EFF","EXT"),("RV","RANGE"))
    for f1,f2 in pairs:
        for b1 in BINS:
            for b2 in BINS:
                rules.append((f"{f1}_{b1}__{f2}_{b2}", f1,b1,f2,b2))
    if len(rules)!=48: raise AssertionError(len(rules))
    return tuple(rules)

RULES=state_rules()
COL={"EFF":"eff_pct","RV":"rv_pct","RANGE":"range_pct","EXT":"ext_pct"}


def rule_mask(S: pd.DataFrame, rule) -> np.ndarray:
    _,f1,b1,f2,b2=rule
    m=bin_mask(S[COL[f1]].to_numpy(float),b1)
    if f2 is not None: m &= bin_mask(S[COL[f2]].to_numpy(float),b2)
    return m


def panel_rows(x5: pd.DataFrame) -> pd.DataFrame:
    pa,pz=base.PARTS["development"]
    rows=[]
    for lb in LOOKBACKS:
        for clock in CLOCKS:
            S=state_frame(x5,clock,lb)
            ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts)
            sign=np.where(S.drive_return.to_numpy(float)>0,1.0,-1.0)
            rmasks={r[0]:rule_mask(S,r) for r in RULES}
            for hold in HOLDS:
                ex,valid,xp,delta,_=e3.hold_base(x5,S,hold)
                base_dev=valid&(pre>=pa)&(ent>=pa)&(ex<pz)
                for mode in MODES:
                    direction=sign if mode=="MOMENTUM" else -sign
                    gross_all=NOTIONAL*direction*delta
                    net_all=gross_all-FEE
                    for rule in RULES:
                        rn=rule[0]; m=base_dev&rmasks[rn]
                        s=summarize(net_all[m],gross_all[m])
                        row={"lookback_min":lb,"hold_min":hold,"mode":mode,"state_rule":rn,
                             "clock_min_utc":clock,"clock_utc":hhmm(clock),"clock_wib":wib(clock),**s}
                        for y in YEARS:
                            ya=pd.Timestamp(f"{y}-01-01",tz="UTC"); yz=pd.Timestamp(f"{y+1}-01-01",tz="UTC")
                            ym=m&(pre>=ya)&(ent>=ya)&(ex<yz)
                            ys=summarize(net_all[ym],gross_all[ym])
                            row.update({f"y{y}_trades":ys["trades"],f"y{y}_wr":ys["win_rate"],f"y{y}_net":ys["net_pnl"],f"y{y}_exp":ys["expectancy"],f"y{y}_pf":ys["pf"]})
                        rows.append(row)
    P=pd.DataFrame(rows)
    expected=len(LOOKBACKS)*len(CLOCKS)*len(HOLDS)*len(MODES)*len(RULES)
    if len(P)!=expected: raise AssertionError(f"expected {expected} panel rows, got {len(P)}")
    return P


def aggregate_candidates(P: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    keys=["lookback_min","hold_min","mode","state_rule"]
    for vals,G in P.groupby(keys,sort=False):
        lb,h,mode,rule=vals
        ev=G.trades>=60
        E=G[ev]
        supportive=ev&(G.win_rate>=.52)&(G.net_pnl>0)&(G.expectancy>0)&(G.pf>=1.05)&(G.max_dd<=125)&(G.max_loss_streak<=10)
        pos=ev&(G.expectancy>0)
        block_ok=[]
        for bi in range(6):
            bg=G[(G.clock_min_utc//240)==bi]
            bev=bg.trades>=60
            bs=bev&(bg.win_rate>=.52)&(bg.net_pnl>0)&(bg.expectancy>0)&(bg.pf>=1.05)&(bg.max_dd<=125)&(bg.max_loss_streak<=10)
            block_ok.append(bool(bev.sum()>0 and bs.sum()/bev.sum()>=.50))
        row={
            "lookback_min":int(lb),"hold_min":int(h),"mode":mode,"state_rule":rule,
            "evaluable_clocks":int(ev.sum()),"supportive_clocks":int(supportive.sum()),
            "supportive_fraction":float(supportive.sum()/ev.sum()) if ev.sum() else np.nan,
            "positive_exp_clocks":int(pos.sum()),
            "median_wr":float(E.win_rate.median()) if len(E) else np.nan,
            "median_exp":float(E.expectancy.median()) if len(E) else np.nan,
            "median_pf":float(E.pf.median()) if len(E) else np.nan,
            "median_dd":float(E.max_dd.median()) if len(E) else np.nan,
            "median_loss_streak":float(E.max_loss_streak.median()) if len(E) else np.nan,
            "clock_blocks_ok":int(sum(block_ok)),
        }
        eras_ok=True; era_mins=[]
        for y in YEARS:
            yev=G[f"y{y}_trades"]>=18
            YE=G[yev]
            ymedwr=float(YE[f"y{y}_wr"].median()) if len(YE) else np.nan
            ymedexp=float(YE[f"y{y}_exp"].median()) if len(YE) else np.nan
            ypos=int((yev&(G[f"y{y}_exp"]>0)).sum())
            yfrac=float(ypos/yev.sum()) if yev.sum() else np.nan
            row.update({f"y{y}_evaluable":int(yev.sum()),f"y{y}_median_wr":ymedwr,f"y{y}_median_exp":ymedexp,f"y{y}_positive_exp_fraction":yfrac})
            yok=(yev.sum()>=30 and np.isfinite(ymedwr) and ymedwr>=.51 and np.isfinite(ymedexp) and ymedexp>0 and yfrac>=.55)
            eras_ok &= bool(yok)
            era_mins.append(ymedexp if np.isfinite(ymedexp) else -np.inf)
        breadth=(row["evaluable_clocks"]>=36 and row["supportive_clocks"]>=28 and row["supportive_fraction"]>=.60 and row["positive_exp_clocks"]>=32)
        medgate=(row["median_wr"]>=.53 and row["median_exp"]>=.20 and row["median_pf"]>=1.10 and row["median_dd"]<=90)
        blockgate=row["clock_blocks_ok"]>=5
        row["breadth_gate"]=breadth; row["median_gate"]=medgate; row["era_gate"]=eras_ok; row["block_gate"]=blockgate
        row["candidate_gate"]=breadth and medgate and eras_ok and blockgate
        row["min_era_median_exp"]=float(min(era_mins))
        row["boundary"]=int(lb) in (min(LOOKBACKS),max(LOOKBACKS)) or int(h) in (min(HOLDS),max(HOLDS))
        rows.append(row)
    D=pd.DataFrame(rows)
    expected=len(LOOKBACKS)*len(HOLDS)*len(MODES)*len(RULES)
    if len(D)!=expected: raise AssertionError(f"expected {expected} candidates, got {len(D)}")
    D["mode_tie"]=D["mode"].map({"MOMENTUM":0,"REVERSAL":1})
    C=D[D.candidate_gate].copy().sort_values(
        ["min_era_median_exp","supportive_fraction","median_exp","median_wr","median_pf","median_dd","median_loss_streak","evaluable_clocks","hold_min","lookback_min","mode_tie","state_rule"],
        ascending=[False,False,False,False,False,True,True,False,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def selected_clock_atlas(P: pd.DataFrame, sel: pd.Series) -> pd.DataFrame:
    G=P[(P.lookback_min==int(sel.lookback_min))&(P.hold_min==int(sel.hold_min))&(P["mode"]==str(sel["mode"]))&(P.state_rule==str(sel.state_rule))].copy()
    G["evaluable"]=G.trades>=60
    G["supportive"]=G.evaluable&(G.win_rate>=.52)&(G.net_pnl>0)&(G.expectancy>0)&(G.pf>=1.05)&(G.max_dd<=125)&(G.max_loss_streak<=10)
    return G.sort_values(["supportive","expectancy","win_rate"],ascending=[False,False,False])


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    P=panel_rows(x5); D,C=aggregate_candidates(P)
    P.to_csv(OUT_PANEL,index=False); D.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)

    lines=[
        "# ETH Economic-First E11 — Market-State Character Discovery Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Clock treatment: **48 half-hour UTC clocks are contexts, not candidate coordinates**.",
        "Development only; External and Reference Validation remained closed.",
        f"Candidate identities: **{len(D)}**; full market-state gate passers: **{len(C)}**.","",
        "## Best state candidates — Development panel","",
        "| # | Mode | State | LB | Hold | Eval clocks | Support | Med WR | Med Exp | Med PF | Med DD | Blocks | 2022 Med WR/Exp | 2023 | 2024 | Gate |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    top=D.sort_values(["min_era_median_exp","supportive_fraction","median_exp","median_wr"],ascending=[False,False,False,False]).head(20)
    for i,r in enumerate(top.itertuples(index=False),1):
        lines.append(f"| {i} | {r.mode} | {r.state_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.evaluable_clocks)} | {int(r.supportive_clocks)}/{int(r.evaluable_clocks)} | {pct(r.median_wr)} | {money(r.median_exp)} | {r.median_pf:.3f} | {money(r.median_dd)} | {int(r.clock_blocks_ok)}/6 | {pct(r.y2022_median_wr)}/{money(r.y2022_median_exp)} | {pct(r.y2023_median_wr)}/{money(r.y2023_median_exp)} | {pct(r.y2024_median_wr)}/{money(r.y2024_median_exp)} | {'YES' if r.candidate_gate else 'NO'} |")

    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E11_NO_STATE_CANDIDATE"
        lines += ["",f"**Status: {status}**","","No invariant market-state candidate passed the preregistered breadth + median-economics + all-era + clock-block gates. OOS remained closed; no gate relaxation or raw-top substitution.","","Research/shadow only. No live promotion or profit guarantee."]
        OUT_STATUS.write_text(status+"\n"); OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]; A=selected_clock_atlas(P,sel)
    status="ETH_ECONOMIC_FIRST_E11_STATE_BOUNDARY_OPEN" if bool(sel.boundary) else "ETH_ECONOMIC_FIRST_E11_STATE_SUPPORTED"
    lines += ["","## Selected invariant state grammar","",
        f"**{sel['mode']} / {sel['state_rule']} / lookback {int(sel['lookback_min'])}m / hold {int(sel['hold_min'])}m**","",
        f"Evaluable clocks **{int(sel['evaluable_clocks'])}/48**; supportive **{int(sel['supportive_clocks'])}/{int(sel['evaluable_clocks'])} ({pct(sel['supportive_fraction'])})**; positive-exp clocks **{int(sel['positive_exp_clocks'])}**.",
        f"Median clock WR **{pct(sel['median_wr'])}**; median expectancy **{money(sel['median_exp'])}/trade**; median PF **{float(sel['median_pf']):.3f}**; median DD **{money(sel['median_dd'])}**; clock blocks **{int(sel['clock_blocks_ok'])}/6**.",
        f"2022 median WR/exp **{pct(sel['y2022_median_wr'])} / {money(sel['y2022_median_exp'])}**; 2023 **{pct(sel['y2023_median_wr'])} / {money(sel['y2023_median_exp'])}**; 2024 **{pct(sel['y2024_median_wr'])} / {money(sel['y2024_median_exp'])}**.","",
        "### Strongest clock contexts — descriptive, not selected coordinates","",
        "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |","|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in A.head(12).itertuples(index=False):
        lines.append(f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |")
    lines += ["",f"**Status: {status}**","","E11 does not open OOS. The next preregistered stage must translate this state grammar into a non-overlapping executable deployment rule before holdout exposure.","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_STATUS.write_text(status+"\n"); OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__":
    main()
