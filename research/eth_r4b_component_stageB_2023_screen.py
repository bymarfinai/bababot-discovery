#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
CELLS_PATH = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
COMP_PATH = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENTS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGEB_2023_CELL_RESULTS.csv"
OUT_VERDICTS = ROOT / "ETH_R4B_STAGEB_2023_COMPONENT_VERDICTS.csv"
OUT_SURVIVORS = ROOT / "ETH_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGEB_2023_COMPONENT_SCREEN.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGEB_2023_Status.txt"

START = pd.Timestamp("2023-01-01", tz="UTC")
END = pd.Timestamp("2024-01-01", tz="UTC")


def finite(x): return bool(np.isfinite(x))
def stats(T): return r1.stats_from_df(T)


def main():
    if not CELLS_PATH.exists() or not COMP_PATH.exists():
        raise FileNotFoundError("R4b frozen component files missing")
    cells = pd.read_csv(CELLS_PATH)
    comps = pd.read_csv(COMP_PATH)
    if cells.empty or comps.empty: raise AssertionError("R4b frozen components empty")

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x23 = x5[(idx >= START) & (idx < END)].copy()

    out = []
    for hour in range(24):
        H = cells[cells.hour_wib == hour].copy()
        e12.CLOCKS = r1.clocks_for_hour(hour)
        e12.LOOKBACKS = list(r1.LOOKBACKS)
        e12.HOLDS = list(r1.HOLDS)
        cache = e12.prep(x23)
        for c in H.itertuples(index=False):
            rule = str(c.character_rule); lb = int(c.lookback_min); hold = int(c.hold_min)
            T = r1.candidate_events(cache, lb, hold, rule)
            s = stats(T)
            wr = float(s["win_rate"]) if finite(s["win_rate"]) else np.nan
            exp = float(s["expectancy"]) if finite(s["expectancy"]) else np.nan
            pf = float(s["pf"]) if finite(s["pf"]) else np.nan
            dd = float(s["max_dd"]) if finite(s["max_dd"]) else np.nan
            dev_wr=float(c.dev_wr); dev_exp=float(c.dev_exp); dev_pf=float(c.dev_pf); dev_dd=float(c.dev_dd); dev_ls=int(c.dev_ls)
            wr_change_pp=100*(wr-dev_wr) if finite(wr) else -np.inf
            exp_ret=exp/dev_exp if dev_exp>0 and finite(exp) else -np.inf
            pf_ret=pf/dev_pf if dev_pf>0 and finite(pf) else -np.inf
            dd_cap=min(160.0,1.50*dev_dd+20.0)
            ls_warning=max(12,dev_ls+4)
            viable=bool(s["trades"]>=50 and finite(wr) and wr>=.52 and s["net_pnl"]>0 and finite(exp) and exp>0 and finite(pf) and pf>=1.15 and finite(dd) and dd<=dd_cap)
            stable=bool(viable and wr_change_pp>=-5.0 and exp_ret>=.60 and pf_ret>=.70)
            out.append({
                "hour_wib":hour,"component_rank":int(c.component_rank),"character_rule":rule,
                "component_size":int(c.component_size),"lookback_min":lb,"hold_min":hold,
                "dev_n":int(c.dev_n),"dev_wr":dev_wr,"dev_net":float(c.dev_net),"dev_exp":dev_exp,"dev_pf":dev_pf,"dev_dd":dev_dd,"dev_ls":dev_ls,
                "test_n":int(s["trades"]),"test_wr":wr,"test_net":float(s["net_pnl"]),"test_exp":exp,"test_pf":pf,"test_dd":dd,"test_ls":int(s["max_loss_streak"]),
                "wr_change_pp":wr_change_pp,"exp_retention":exp_ret,"pf_retention":pf_ret,"dd_cap":dd_cap,
                "ls_warning_threshold":ls_warning,"risk_clustering_warning":bool(s["max_loss_streak"]>ls_warning),
                "economically_viable":viable,"performance_stable":stable,
            })

    R=pd.DataFrame(out).sort_values(["hour_wib","component_rank","hold_min","lookback_min"]).reset_index(drop=True)
    R.to_csv(OUT_CELLS,index=False)

    verdicts=[]; survivors=[]
    for (hour,rank),G in R.groupby(["hour_wib","component_rank"],sort=True):
        meta=comps[(comps.hour_wib==hour)&(comps.component_rank==rank)].iloc[0]
        n=len(G); v=int(G.economically_viable.sum()); s=int(G.performance_stable.sum()); frac=v/n if n else 0.0
        if n>=2 and v>=2 and s>=1 and frac>=.50:
            verdict="STABLE_PLATEAU_FROZEN"
        elif v>=2:
            verdict="PARTIAL_PLATEAU_PERSISTENCE"
        elif n==1 and s>=1:
            verdict="NARROW_STABLE_POINT"
        else:
            verdict="PLATEAU_DEGRADATION_FAIL"
        row={
            "hour_wib":int(hour),"component_rank":int(rank),"character_rule":str(meta.character_rule),
            "component_size":int(n),"component_cells":str(meta.component_cells),
            "dev_component_wr_min":float(meta.component_wr_min),"dev_component_wr_mean":float(meta.component_wr_mean),
            "dev_component_exp_floor":float(meta.component_exp_floor),"dev_component_exp_mean":float(meta.component_exp_mean),
            "test_viable_cells":v,"test_stable_cells":s,"test_viable_fraction":frac,
            "test_positive_net_cells":int((G.test_net>0).sum()),"test_positive_exp_cells":int((G.test_exp>0).sum()),
            "test_median_wr":float(G.test_wr.median()),"test_median_exp":float(G.test_exp.median()),"test_median_pf":float(G.test_pf.median()),
            "test_max_dd":float(G.test_dd.max()),"verdict":verdict,
        }
        verdicts.append(row)
        if verdict=="STABLE_PLATEAU_FROZEN": survivors.append(row)

    V=pd.DataFrame(verdicts).sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    S=pd.DataFrame(survivors)
    if not S.empty: S=S.sort_values(["hour_wib","component_rank"]).reset_index(drop=True)
    V.to_csv(OUT_VERDICTS,index=False); S.to_csv(OUT_SURVIVORS,index=False)

    survivor_hours=sorted(S.hour_wib.unique().tolist()) if not S.empty else []
    partial=V[V.verdict=="PARTIAL_PLATEAU_PERSISTENCE"]
    narrow=V[V.verdict=="NARROW_STABLE_POINT"]
    lines=[
        "# ETH R4b — Stage B 2023 Connected-Component Screen","",
        "**COMPONENT MEMBERSHIP WAS FROZEN FROM 2022. EACH CELL IS TESTED AT THE SAME COORDINATE IN 2023. 2024-2026 CLOSED.**","",
        f"Frozen components tested: **{len(V)}**. Stable plateaus: **{len(S)}** across **{len(survivor_hours)}** hours.",
        f"Partial plateau persistence: **{len(partial)}**. Narrow stable points: **{len(narrow)}**.",
        f"Stable-plateau hours: **{', '.join(f'H{h:02d}' for h in survivor_hours) if survivor_hours else 'NONE'}**.","",
        "| Hour | Rank | Character | Size | 2023 viable | Stable | Viable % | Median WR | Median Exp | Median PF | Max DD | Verdict |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in V.itertuples(index=False):
        lines.append(f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {int(r.test_viable_cells)} | {int(r.test_stable_cells)} | {100*float(r.test_viable_fraction):.1f}% | {100*float(r.test_median_wr):.2f}% | ${float(r.test_median_exp):+.2f} | {float(r.test_median_pf):.3f} | ${float(r.test_max_dd):.2f} | {r.verdict} |")
    if not S.empty:
        lines += ["","## Stable plateaus frozen for later 2024 confirmation","",
                  "| Hour | Rank | Character | Size | 2023 viable/stable | Component cells |","|---:|---:|---|---:|---:|---|"]
        for r in S.itertuples(index=False):
            lines.append(f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | {r.character_rule} | {int(r.component_size)} | {int(r.test_viable_cells)}/{int(r.test_stable_cells)} | {r.component_cells} |")
    lines += ["","No component or cell may be modified after observing these 2023 results."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text("ETH_R4B_STAGEB_COMPLETE\n")
    print("\n".join(lines))


if __name__=="__main__": main()
