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
STAGEB_CELLS = ROOT / "BNB_R4B_STAGEB_2023_CELL_RESULTS.csv"
STAGEC_CELLS = ROOT / "BNB_R4B_STAGEC_2024_COMPONENT_CELL_RESULTS.csv"
PERSISTENT = ROOT / "BNB_R4B_STAGEC_2024_PERSISTENT_PLATEAUS.csv"
OUT_CELLS = ROOT / "BNB_R4B_STAGED_2025_FINAL_OOS_CELLS.csv"
OUT_VERDICTS = ROOT / "BNB_R4B_STAGED_2025_FINAL_OOS_VERDICTS.csv"
OUT_ROBUST = ROOT / "BNB_R4B_STAGED_2025_FINAL_ROBUST_PLATEAUS.csv"
OUT_RESULT = ROOT / "BNB_R4B_STAGED_2025_FINAL_OOS.md"
OUT_STATUS = ROOT / "BNB_R4B_STAGED_2025_Status.txt"

START = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-01-01", tz="UTC")
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
    b23=pd.read_csv(STAGEB_CELLS)
    c24=pd.read_csv(STAGEC_CELLS)
    persistent=pd.read_csv(PERSISTENT)
    if persistent.empty:
        raise AssertionError("Stage D requires at least one Stage-C persistent plateau")

    base.synthetic_tests()
    x5,coverage=base.load5("BNBUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    if idx.max()<pd.Timestamp("2025-12-31 23:55:00",tz="UTC"):
        raise RuntimeError(f"2025 dataset incomplete; max timestamp is {idx.max()}")
    # Full prior history is retained for causal warm-up. Only 2025 events are scored; 2026 is excluded.
    x=x5[idx<END].copy()

    rows=[]
    for s in persistent.itertuples(index=False):
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
            p24=c24[(c24.hour_wib==hour)&(c24.component_rank==rank)&(c24.lookback_min==lb)&(c24.hold_min==hold)].iloc[0]
            rows.append({
                "hour_wib":hour,"component_rank":rank,"character_rule":rule,"lookback_min":lb,"hold_min":hold,
                "dev2022_n":int(c.dev_n),"dev2022_wr":dev_wr,"dev2022_net":float(c.dev_net),"dev2022_exp":dev_exp,"dev2022_pf":dev_pf,"dev2022_dd":dev_dd,"dev2022_ls":dev_ls,
                "test2023_n":int(p23.test_n),"test2023_wr":float(p23.test_wr),"test2023_net":float(p23.test_net),"test2023_exp":float(p23.test_exp),"test2023_pf":float(p23.test_pf),
                "y2024_n":int(p24.y2024_n),"y2024_wr":float(p24.y2024_wr),"y2024_net":float(p24.y2024_net),"y2024_exp":float(p24.y2024_exp),"y2024_pf":float(p24.y2024_pf),
                "oos2025_n":int(st["trades"]),"oos2025_wr":wr,"oos2025_net":float(st["net_pnl"]),"oos2025_exp":exp,"oos2025_pf":pf,"oos2025_dd":dd,"oos2025_ls":int(st["max_loss_streak"]),
                "wr_change_vs_2022_pp":wr_change_pp,"exp_retention_vs_2022":exp_ret,"pf_retention_vs_2022":pf_ret,"dd_cap":dd_cap,"ls_warning_threshold":ls_warning,
                "risk_clustering_warning":bool(st["max_loss_streak"]>ls_warning),"economically_viable_2025":viable,"strict_stable_vs_2022_2025":strict,
            })

    R=pd.DataFrame(rows).sort_values(["hour_wib","component_rank","hold_min","lookback_min"]).reset_index(drop=True)
    R.to_csv(OUT_CELLS,index=False)

    verdicts=[]; robust=[]
    for (hour,rank),G in R.groupby(["hour_wib","component_rank"],sort=True):
        s=persistent[(persistent.hour_wib==hour)&(persistent.component_rank==rank)].iloc[0]
        n=len(G); viable_n=int(G.economically_viable_2025.sum()); strict_n=int(G.strict_stable_vs_2022_2025.sum())
        med_wr=float(G.oos2025_wr.median()); med_exp=float(G.oos2025_exp.median()); med_pf=float(G.oos2025_pf.median())
        total_net=float(G.oos2025_net.sum()); max_dd=float(G.oos2025_dd.max()); max_ls=int(G.oos2025_ls.max())
        if viable_n/n>=.50 and med_exp>0 and med_pf>=1.15:
            verdict="FINAL_OOS_PLATEAU_PASS"
        elif viable_n>=2 or (med_exp>0 and med_pf>1.00):
            verdict="PARTIAL_FINAL_OOS_PERSISTENCE"
        else:
            verdict="FINAL_OOS_PLATEAU_FAIL"
        row={
            "hour_wib":int(hour),"component_rank":int(rank),"character_rule":str(s.character_rule),"component_size":int(n),"component_cells":str(s.component_cells),
            "oos2025_viable_cells":viable_n,"oos2025_strict_cells":strict_n,"oos2025_viable_fraction":float(viable_n/n),
            "oos2025_median_wr":med_wr,"oos2025_median_exp":med_exp,"oos2025_median_pf":med_pf,"oos2025_sum_cell_net":total_net,
            "oos2025_max_dd":max_dd,"oos2025_max_ls":max_ls,"risk_warning_cells":int(G.risk_clustering_warning.sum()),"verdict":verdict,
        }
        verdicts.append(row)
        if verdict=="FINAL_OOS_PLATEAU_PASS": robust.append(row)

    V=pd.DataFrame(verdicts).sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    S=pd.DataFrame(robust)
    if not S.empty: S=S.sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    V.to_csv(OUT_VERDICTS,index=False); S.to_csv(OUT_ROBUST,index=False)

    lines=[
        "# BNB R4b — Stage D 2025 Final Full-Year OOS","",
        "**2025 FINAL FULL-YEAR OOS. FROZEN PERSISTENT PLATEAUS ONLY. NO RESELECTION. 2026 REMAINS CLOSED.**","",
        f"Raw BNBUSDT 5m coverage: **{coverage:.4%}**.",
        f"Frozen persistent plateaus tested: **{len(V)}**. Final OOS plateau passes: **{len(S)}**.","",
        "| Hour | Rank | Character | Size | 2025 viable | Strict | Viable % | Median WR | Median Exp | Median PF | Sum cell Net* | Max DD | Max LS | Verdict |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in V.itertuples(index=False):
        lines.append(f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {int(r.oos2025_viable_cells)} | {int(r.oos2025_strict_cells)} | {100*float(r.oos2025_viable_fraction):.1f}% | {100*float(r.oos2025_median_wr):.2f}% | ${float(r.oos2025_median_exp):+.2f} | {float(r.oos2025_median_pf):.3f} | ${float(r.oos2025_sum_cell_net):+.2f} | ${float(r.oos2025_max_dd):.2f} | {int(r.oos2025_max_ls)} | {r.verdict} |")

    for (hour,rank),G in R.groupby(["hour_wib","component_rank"],sort=True):
        rule=str(G.character_rule.iloc[0])
        lines += ["",f"## H{int(hour):02d} rank {int(rank)} — {rule}","",
                  "| LB/Hold | 2022 WR/Exp/PF | 2023 WR/Exp/PF | 2024 WR/Exp/PF | 2025 N | WR | Net | Exp | PF | DD | LS | Viable | Strict | Risk warn |",
                  "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|"]
        for r in G.itertuples(index=False):
            lines.append(f"| LB{int(r.lookback_min)}/H{int(r.hold_min)} | {100*float(r.dev2022_wr):.2f}%/${float(r.dev2022_exp):+.2f}/{float(r.dev2022_pf):.3f} | {100*float(r.test2023_wr):.2f}%/${float(r.test2023_exp):+.2f}/{float(r.test2023_pf):.3f} | {100*float(r.y2024_wr):.2f}%/${float(r.y2024_exp):+.2f}/{float(r.y2024_pf):.3f} | {int(r.oos2025_n)} | {100*float(r.oos2025_wr):.2f}% | ${float(r.oos2025_net):+.2f} | ${float(r.oos2025_exp):+.2f} | {float(r.oos2025_pf):.3f} | ${float(r.oos2025_dd):.2f} | {int(r.oos2025_ls)} | {'Y' if r.economically_viable_2025 else 'N'} | {'Y' if r.strict_stable_vs_2022_2025 else 'N'} | {'Y' if r.risk_clustering_warning else 'N'} |")

    lines += ["","*Sum of per-cell Net is descriptive only because frozen timing variants overlap; it is not portfolio PnL.",
              "Final verdicts are based on the entire frozen plateau, never a post-hoc best 2025 coordinate.",
              "2026 remains unopened and is not used anywhere in this stage.","","Research/shadow only."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    status="BNB_R4B_FINAL_OOS_ROBUST_PLATEAUS_FOUND" if len(S)>0 else "BNB_R4B_FINAL_OOS_NO_ROBUST_PLATEAU"
    OUT_STATUS.write_text(status+"\n")
    print(OUT_RESULT.read_text())
    print(f"STATUS={status}")


if __name__=="__main__": main()
