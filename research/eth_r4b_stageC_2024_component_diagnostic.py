#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
FROZEN_CELLS = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
STABLE_PLATEAUS = ROOT / "ETH_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
STAGEB_CELLS = ROOT / "ETH_R4B_STAGEB_2023_CELL_RESULTS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGEC_2024_COMPONENT_CELL_RESULTS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGEC_2024_COMPONENT_DIAGNOSTIC.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGEC_2024_Status.txt"

START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")


def finite(x): return bool(np.isfinite(x))
def stats(T): return r1.stats_from_df(T)


def events_for_period(cache, lb: int, hold: int, rule: str):
    rows=[]
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
        m=valid & (ent>=START) & (ex<END) & masks[rule]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]
        net=gross-e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({"entry_ts":entry_ts,"exit_ts":exit_ts,"clock":int(clock),"gross":float(g),"net":float(n)})
    return pd.DataFrame(rows,columns=["entry_ts","exit_ts","clock","gross","net"])


def main():
    frozen=pd.read_csv(FROZEN_CELLS)
    stable=pd.read_csv(STABLE_PLATEAUS)
    b23=pd.read_csv(STAGEB_CELLS)
    if len(stable)!=1:
        raise AssertionError(f"Stage C requires exactly one R4b stable plateau, got {len(stable)}")
    s=stable.iloc[0]
    hour=int(s.hour_wib); rank=int(s.component_rank); rule=str(s.character_rule)
    C=frozen[(frozen.hour_wib==hour)&(frozen.component_rank==rank)&(frozen.character_rule.astype(str)==rule)].copy()
    if len(C)!=int(s.component_size):
        raise AssertionError("frozen component cell count mismatch")

    e12.base.synthetic_tests()
    x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    x=x5[idx<END].copy()
    e12.CLOCKS=r1.clocks_for_hour(hour)
    e12.LOOKBACKS=sorted(C.lookback_min.astype(int).unique().tolist())
    e12.HOLDS=sorted(C.hold_min.astype(int).unique().tolist())
    cache=e12.prep(x)

    rows=[]
    for c in C.itertuples(index=False):
        lb=int(c.lookback_min); hold=int(c.hold_min)
        T=events_for_period(cache,lb,hold,rule)
        st=stats(T)
        wr=float(st["win_rate"]) if finite(st["win_rate"]) else np.nan
        exp=float(st["expectancy"]) if finite(st["expectancy"]) else np.nan
        pf=float(st["pf"]) if finite(st["pf"]) else np.nan
        dd=float(st["max_dd"]) if finite(st["max_dd"]) else np.nan
        dev_wr=float(c.dev_wr); dev_exp=float(c.dev_exp); dev_pf=float(c.dev_pf); dev_dd=float(c.dev_dd); dev_ls=int(c.dev_ls)
        wr_change_pp=100*(wr-dev_wr) if finite(wr) else -np.inf
        exp_ret=exp/dev_exp if dev_exp>0 and finite(exp) else -np.inf
        pf_ret=pf/dev_pf if dev_pf>0 and finite(pf) else -np.inf
        dd_cap=min(160.0,1.50*dev_dd+20.0)
        ls_warning=max(12,dev_ls+4)
        viable=bool(st["trades"]>=50 and finite(wr) and wr>=.52 and st["net_pnl"]>0 and finite(exp) and exp>0 and finite(pf) and pf>=1.15 and finite(dd) and dd<=dd_cap)
        strict=bool(viable and wr_change_pp>=-5.0 and exp_ret>=.60 and pf_ret>=.70)
        p23=b23[(b23.hour_wib==hour)&(b23.component_rank==rank)&(b23.lookback_min==lb)&(b23.hold_min==hold)].iloc[0]
        rows.append({
            "hour_wib":hour,"component_rank":rank,"character_rule":rule,"lookback_min":lb,"hold_min":hold,
            "dev_n":int(c.dev_n),"dev_wr":dev_wr,"dev_net":float(c.dev_net),"dev_exp":dev_exp,"dev_pf":dev_pf,"dev_dd":dev_dd,"dev_ls":dev_ls,
            "test2023_n":int(p23.test_n),"test2023_wr":float(p23.test_wr),"test2023_net":float(p23.test_net),"test2023_exp":float(p23.test_exp),"test2023_pf":float(p23.test_pf),"test2023_dd":float(p23.test_dd),"test2023_viable":bool(p23.economically_viable),"test2023_stable":bool(p23.performance_stable),
            "y2024_n":int(st["trades"]),"y2024_wr":wr,"y2024_net":float(st["net_pnl"]),"y2024_exp":exp,"y2024_pf":pf,"y2024_dd":dd,"y2024_ls":int(st["max_loss_streak"]),
            "wr_change_vs_2022_pp":wr_change_pp,"exp_retention_vs_2022":exp_ret,"pf_retention_vs_2022":pf_ret,"dd_cap":dd_cap,"ls_warning_threshold":ls_warning,
            "risk_clustering_warning":bool(st["max_loss_streak"]>ls_warning),"economically_viable_2024":viable,"strict_stable_vs_2022_2024":strict,
        })

    R=pd.DataFrame(rows).sort_values(["hold_min","lookback_min"]).reset_index(drop=True)
    R.to_csv(OUT_CELLS,index=False)
    viable_n=int(R.economically_viable_2024.sum()); strict_n=int(R.strict_stable_vs_2022_2024.sum()); n=len(R)
    median_exp=float(R.y2024_exp.median()); median_pf=float(R.y2024_pf.median()); median_wr=float(R.y2024_wr.median())
    if viable_n/n>=.50 and median_exp>0 and median_pf>=1.15:
        verdict="ECONOMIC_PLATEAU_PERSISTS"
    elif viable_n>=2 or (median_exp>0 and median_pf>1):
        verdict="PARTIAL_ECONOMIC_PERSISTENCE"
    else:
        verdict="COMPONENT_COLLAPSE"

    lines=[
        "# ETH R4b — Stage C 2024 Component Diagnostic","",
        "**ONLY THE R4b STABLE H04 PLATEAU IS OPENED. 2025-2026 REMAIN CLOSED.**","",
        f"Frozen plateau: **H{hour:02d} {rule}**, component rank **{rank}**, size **{n}**.",
        f"2024 economically viable cells: **{viable_n}/{n}**; strict-stable vs 2022: **{strict_n}/{n}**.",
        f"2024 component medians: WR **{100*median_wr:.2f}%**, Exp **${median_exp:+.2f}**, PF **{median_pf:.3f}**.",
        f"Diagnostic verdict: **{verdict}**.","",
        "| LB/Hold | 2022 WR | Exp | PF | 2023 WR | Exp | PF | 2024 WR | Net | Exp | PF | DD | LS | 2024 viable | Strict stable |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for r in R.itertuples(index=False):
        lines.append(
            f"| LB{int(r.lookback_min)}/H{int(r.hold_min)} | {100*float(r.dev_wr):.2f}% | ${float(r.dev_exp):+.2f} | {float(r.dev_pf):.3f} | "
            f"{100*float(r.test2023_wr):.2f}% | ${float(r.test2023_exp):+.2f} | {float(r.test2023_pf):.3f} | "
            f"{100*float(r.y2024_wr):.2f}% | ${float(r.y2024_net):+.2f} | ${float(r.y2024_exp):+.2f} | {float(r.y2024_pf):.3f} | ${float(r.y2024_dd):.2f} | {int(r.y2024_ls)} | "
            f"{'Y' if r.economically_viable_2024 else 'N'} | {'Y' if r.strict_stable_vs_2022_2024 else 'N'} |"
        )
    lines += ["", "This stage is a persistence diagnostic because H04 2024 had prior historical exposure. No 2024 timing reselection is performed.", "2025 remains untouched final OOS; 2026 remains closed."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(verdict+"\n")
    print("\n".join(lines))


if __name__=="__main__": main()
