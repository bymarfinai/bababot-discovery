#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as engine
import bnb_r4b_component_stageA_2022_freeze as stageA

ROOT = Path(__file__).resolve().parent.parent
FROZEN_CELLS = ROOT / "BNB_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
STABLE_PLATEAUS = ROOT / "BNB_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
STAGEB_CELLS = ROOT / "BNB_R4B_STAGEB_2023_CELL_RESULTS.csv"
OUT_CELLS = ROOT / "BNB_R4B_STAGEC_2024_COMPONENT_CELL_RESULTS.csv"
OUT_VERDICTS = ROOT / "BNB_R4B_STAGEC_2024_COMPONENT_VERDICTS.csv"
OUT_SURVIVORS = ROOT / "BNB_R4B_STAGEC_2024_PERSISTENT_PLATEAUS.csv"
OUT_RESULT = ROOT / "BNB_R4B_STAGEC_2024_COMPONENT_PERSISTENCE.md"
OUT_STATUS = ROOT / "BNB_R4B_STAGEC_2024_Status.txt"

START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")
NOTIONAL = 500.0
FEE = 0.75


def finite(x): return bool(np.isfinite(x))
def stats(net, gross): return engine.summarize(np.asarray(net, float), np.asarray(gross, float))


def events_for_period(cache, clocks, lb: int, hold: int, rule: str) -> pd.DataFrame:
    rows=[]
    for clock in clocks:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
        m=valid & (ent>=START) & (ex<END) & masks[rule]
        gross=NOTIONAL*np.asarray(delta,float)[m]
        net=gross-FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({"entry_ts":entry_ts,"exit_ts":exit_ts,"clock":int(clock),"gross":float(g),"net":float(n)})
    if not rows:
        return pd.DataFrame(columns=["entry_ts","exit_ts","clock","gross","net"])
    return pd.DataFrame(rows).sort_values(["entry_ts","clock"]).reset_index(drop=True)


def main():
    frozen=pd.read_csv(FROZEN_CELLS)
    stable=pd.read_csv(STABLE_PLATEAUS)
    b23=pd.read_csv(STAGEB_CELLS)
    if stable.empty:
        raise AssertionError("Stage C requires at least one Stage-B stable plateau")

    base.synthetic_tests()
    x5,coverage=base.load5("BNBUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    if idx.max()<pd.Timestamp("2024-12-31 23:55:00",tz="UTC"):
        raise RuntimeError(f"2024 dataset incomplete; max timestamp is {idx.max()}")
    x=x5[idx<END].copy()

    rows=[]
    for s in stable.itertuples(index=False):
        hour=int(s.hour_wib); rank=int(s.component_rank); rule=str(s.character_rule)
        C=frozen[(frozen.hour_wib==hour)&(frozen.component_rank==rank)&(frozen.character_rule.astype(str)==rule)].copy()
        if len(C)!=int(s.component_size):
            raise AssertionError(f"frozen component cell count mismatch H{hour:02d} rank {rank}")
        clocks=stageA.hour_clocks(hour)
        engine.CLOCKS=clocks
        engine.LOOKBACKS=tuple(sorted(C.lookback_min.astype(int).unique()))
        engine.HOLDS=tuple(sorted(C.hold_min.astype(int).unique()))
        cache=engine.prep(x)

        for c in C.itertuples(index=False):
            lb=int(c.lookback_min); hold=int(c.hold_min)
            T=events_for_period(cache,clocks,lb,hold,rule)
            st=stats(T.net.to_numpy(float),T.gross.to_numpy(float))
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

    R=pd.DataFrame(rows).sort_values(["hour_wib","component_rank","hold_min","lookback_min"]).reset_index(drop=True)
    R.to_csv(OUT_CELLS,index=False)

    verdicts=[]; survivors=[]
    for (hour,rank),G in R.groupby(["hour_wib","component_rank"],sort=True):
        s=stable[(stable.hour_wib==hour)&(stable.component_rank==rank)].iloc[0]
        n=len(G); viable_n=int(G.economically_viable_2024.sum()); strict_n=int(G.strict_stable_vs_2022_2024.sum())
        med_wr=float(G.y2024_wr.median()); med_exp=float(G.y2024_exp.median()); med_pf=float(G.y2024_pf.median())
        if viable_n/n>=.50 and med_exp>0 and med_pf>=1.15:
            verdict="ECONOMIC_PLATEAU_PERSISTS"
        elif viable_n>=2 or (med_exp>0 and med_pf>1.00):
            verdict="PARTIAL_ECONOMIC_PERSISTENCE"
        else:
            verdict="COMPONENT_COLLAPSE"
        row={
            "hour_wib":int(hour),"component_rank":int(rank),"character_rule":str(s.character_rule),"component_size":int(n),"component_cells":str(s.component_cells),
            "y2024_viable_cells":viable_n,"y2024_strict_cells":strict_n,"y2024_viable_fraction":float(viable_n/n),
            "y2024_median_wr":med_wr,"y2024_median_exp":med_exp,"y2024_median_pf":med_pf,
            "y2024_max_dd":float(G.y2024_dd.max()),"y2024_max_ls":int(G.y2024_ls.max()),"risk_warning_cells":int(G.risk_clustering_warning.sum()),"verdict":verdict,
        }
        verdicts.append(row)
        if verdict=="ECONOMIC_PLATEAU_PERSISTS": survivors.append(row)

    V=pd.DataFrame(verdicts).sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    S=pd.DataFrame(survivors)
    if not S.empty: S=S.sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    V.to_csv(OUT_VERDICTS,index=False); S.to_csv(OUT_SURVIVORS,index=False)

    lines=[
        "# BNB R4b — Stage C 2024 Frozen-Plateau Persistence","",
        "**ONLY STAGE-B STABLE PLATEAUS ARE OPENED. 2025-2026 REMAIN CLOSED.**","",
        f"Raw BNBUSDT 5m coverage: **{coverage:.4%}**.",
        f"Stage-B plateaus tested: **{len(V)}**. 2024 persistent plateaus: **{len(S)}**.","",
        "| Hour | Rank | Character | Size | 2024 viable | Strict | Viable % | Median WR | Median Exp | Median PF | Max DD | Max LS | Verdict |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in V.itertuples(index=False):
        lines.append(f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {int(r.y2024_viable_cells)} | {int(r.y2024_strict_cells)} | {100*float(r.y2024_viable_fraction):.1f}% | {100*float(r.y2024_median_wr):.2f}% | ${float(r.y2024_median_exp):+.2f} | {float(r.y2024_median_pf):.3f} | ${float(r.y2024_max_dd):.2f} | {int(r.y2024_max_ls)} | {r.verdict} |")

    for (hour,rank),G in R.groupby(["hour_wib","component_rank"],sort=True):
        rule=str(G.character_rule.iloc[0])
        lines += ["",f"## H{int(hour):02d} rank {int(rank)} — {rule}","",
                  "| LB/Hold | 2022 WR/Exp/PF | 2023 WR/Exp/PF | 2024 N | WR | Net | Exp | PF | DD | LS | Viable | Strict |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|"]
        for r in G.itertuples(index=False):
            lines.append(f"| LB{int(r.lookback_min)}/H{int(r.hold_min)} | {100*float(r.dev_wr):.2f}%/${float(r.dev_exp):+.2f}/{float(r.dev_pf):.3f} | {100*float(r.test2023_wr):.2f}%/${float(r.test2023_exp):+.2f}/{float(r.test2023_pf):.3f} | {int(r.y2024_n)} | {100*float(r.y2024_wr):.2f}% | ${float(r.y2024_net):+.2f} | ${float(r.y2024_exp):+.2f} | {float(r.y2024_pf):.3f} | ${float(r.y2024_dd):.2f} | {int(r.y2024_ls)} | {'Y' if r.economically_viable_2024 else 'N'} | {'Y' if r.strict_stable_vs_2022_2024 else 'N'} |")

    lines += ["","2024 is a persistence diagnostic; no timing reselection was performed.","Only ECONOMIC_PLATEAU_PERSISTS components may enter 2025 final OOS.","2025 remains untouched; 2026 remains closed.","","Research/shadow only."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text("BNB_R4B_STAGEC_COMPLETE\n")
    print(OUT_RESULT.read_text())


if __name__=="__main__": main()
