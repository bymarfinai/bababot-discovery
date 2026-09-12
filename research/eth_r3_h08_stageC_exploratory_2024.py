#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
DEV_LOCK = ROOT / "ETH_R3_H08_STAGEA_FrozenDevCandidate.csv"
TEST_NEIGHBOR = ROOT / "ETH_R3_H08_STAGEB_2023_LocalNeighborhood.csv"
OUT_NEIGHBOR = ROOT / "ETH_R3_H08_STAGEC_2024_LocalNeighborhood.csv"
OUT_RESULT = ROOT / "ETH_R3_H08_STAGEC_Exploratory2024_Result.md"
OUT_STATUS = ROOT / "ETH_R3_H08_STAGEC_Exploratory2024_Status.txt"

HOUR_WIB = 8
START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")


def finite(x): return bool(np.isfinite(x))
def stats(T): return r1.stats_from_df(T)


def events_for_period(cache, lb, hold, rule):
    rows=[]
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
        m=valid & (ent>=START) & (ex<END) & masks[rule]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]
        net=gross-e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({"entry_ts":entry_ts,"exit_ts":exit_ts,"clock":int(clock),"gross":float(g),"net":float(n)})
    return pd.DataFrame(rows, columns=["entry_ts","exit_ts","clock","gross","net"])


def main():
    dev=pd.read_csv(DEV_LOCK).iloc[0]
    t23=pd.read_csv(TEST_NEIGHBOR)
    stable=t23[t23.performance_stable.astype(bool)].copy()
    if len(stable)!=1:
        raise AssertionError(f"expected exactly one 2023 stable cell, got {len(stable)}")
    sel=stable.iloc[0]
    rule=str(dev.character_rule)
    sel_lb=int(sel.lookback_min); sel_hold=int(sel.hold_min)

    LOOKBACKS=list(r1.LOOKBACKS); HOLDS=list(r1.HOLDS)
    li={v:i for i,v in enumerate(LOOKBACKS)}; hi={v:i for i,v in enumerate(HOLDS)}
    di,dj=li[sel_lb],hi[sel_hold]
    coords=[]
    for lb in LOOKBACKS:
        for hold in HOLDS:
            dist=abs(li[lb]-di)+abs(hi[hold]-dj)
            if dist<=1: coords.append((lb,hold,dist))

    e12.base.synthetic_tests()
    x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    x=x5[idx<END].copy()
    e12.CLOCKS=r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS=sorted({x[0] for x in coords}); e12.HOLDS=sorted({x[1] for x in coords})
    cache=e12.prep(x)

    dev_wr=float(dev.dev_wr); dev_exp=float(dev.dev_exp); dev_pf=float(dev.dev_pf); dev_dd=float(dev.dev_dd); dev_ls=int(dev.dev_ls)
    dd_cap=min(160.0,1.50*dev_dd+20.0); ls_warning=max(12,dev_ls+4)
    rows=[]
    for lb,hold,dist in coords:
        T=events_for_period(cache,int(lb),int(hold),rule)
        s=stats(T)
        wr=float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
        exp=float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
        pf=float(s["pf"]) if finite(s["pf"]) else np.nan
        dd=float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
        viable=bool(s["trades"]>=50 and finite(wr) and wr>=.52 and s["net_pnl"]>0 and finite(exp) and exp>0 and finite(pf) and pf>=1.15 and finite(dd) and dd<=dd_cap)
        stable24=bool(viable and wr>=dev_wr-.05 and exp/dev_exp>=.60 and pf/dev_pf>=.70)
        rows.append({"character_rule":rule,"lookback_min":int(lb),"hold_min":int(hold),"distance_from_2023_selected":int(dist),"trades":int(s["trades"]),"wr":wr,"net":float(s["net_pnl"]),"exp":exp,"pf":pf,"dd":dd,"ls":int(s["max_loss_streak"]),"exp_retention_vs_2022":exp/dev_exp if finite(exp) else np.nan,"pf_retention_vs_2022":pf/dev_pf if finite(pf) else np.nan,"wr_change_vs_2022_pp":100*(wr-dev_wr) if finite(wr) else np.nan,"economically_viable":viable,"performance_stable_vs_2022":stable24,"risk_clustering_warning":bool(s["max_loss_streak"]>ls_warning)})
    D=pd.DataFrame(rows).sort_values(["distance_from_2023_selected","lookback_min","hold_min"]).reset_index(drop=True)
    D.to_csv(OUT_NEIGHBOR,index=False)
    exact=D[(D.lookback_min==sel_lb)&(D.hold_min==sel_hold)].iloc[0]
    OUT_STATUS.write_text("ETH_R3_H08_EXPLORATORY_2024_DIAGNOSTIC_COMPLETE\n")

    lines=["# ETH R3 H08 — Exploratory 2024 Diagnostic","","**EXPLORATORY ONLY. Formal 2023 verdict remains LOCAL_NEIGHBORHOOD_FAIL. 2025+ CLOSED.**","",f"Frozen 2022 character: **{rule}**.",f"2023 surviving shifted coordinate selected before opening 2024: **LB{sel_lb} / H{sel_hold}**.","2024 primary diagnostic is that exact selected coordinate. Its immediate neighbors are reported only as context; no reselection is allowed.","",f"2022 Dev: N {int(dev.dev_n)}, WR {100*dev_wr:.2f}%, Net ${float(dev.dev_net):+.2f}, Exp ${dev_exp:+.2f}, PF {dev_pf:.3f}, DD ${dev_dd:.2f}, LS {dev_ls}.",f"2023 selected: N {int(sel.trades)}, WR {100*float(sel.wr):.2f}%, Net ${float(sel.net):+.2f}, Exp ${float(sel.exp):+.2f}, PF {float(sel.pf):.3f}, DD ${float(sel.dd):.2f}, LS {int(sel.ls)}.",f"2024 exact selected: N {int(exact.trades)}, WR {100*float(exact.wr):.2f}%, Net ${float(exact.net):+.2f}, Exp ${float(exact.exp):+.2f}, PF {float(exact.pf):.3f}, DD ${float(exact.dd):.2f}, LS {int(exact.ls)}.","","| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | Exp retain | PF retain | Viable | Stable | Risk warn |","|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|"]
    for r in D.itertuples(index=False):
        lines.append(f"| {r.lookback_min} | {r.hold_min} | {r.distance_from_2023_selected} | {r.trades} | {100*r.wr:.2f}% | ${r.net:+.2f} | ${r.exp:+.2f} | {r.pf:.3f} | ${r.dd:.2f} | {r.ls} | {100*r.exp_retention_vs_2022:.1f}% | {100*r.pf_retention_vs_2022:.1f}% | {'Y' if r.economically_viable else 'N'} | {'Y' if r.performance_stable_vs_2022 else 'N'} | {'Y' if r.risk_clustering_warning else 'N'} |")
    lines += ["","## Diagnostic interpretation","",f"2024 exact selected coordinate economically viable: **{'YES' if bool(exact.economically_viable) else 'NO'}**.",f"2024 exact selected coordinate still meets the same performance-stability retention gates vs 2022: **{'YES' if bool(exact.performance_stable_vs_2022) else 'NO'}**.",f"2024 viable cells around the 2023 selected coordinate: **{int(D.economically_viable.sum())}/{len(D)}**.","This diagnostic cannot retroactively turn the formal Stage-B verdict into a confirmatory pass; it is evidence about whether the shifted habitat persists into 2024."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print("\n".join(lines))

if __name__=="__main__": main()
