#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT / "ETH_R4B_STAGE_D_2025_FINAL_OOS_CELLS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGE_E_2026_YTD_CELLS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGE_E_2026_YTD_Result.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGE_E_2026_YTD_Status.txt"
START = pd.Timestamp("2026-01-01", tz="UTC")
EXPECTED = {(120,240),(180,240),(240,240),(180,360),(240,360)}
HOUR = 4
RULE = "DRIVE_DOWN__STR_B80_100"

def finite(x): return bool(np.isfinite(x))
def stats(T): return r1.stats_from_df(T)

def events_for_period(cache, lb, hold, last_ts):
    rows=[]
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
        m=valid & (ent>=START) & (ex<=last_ts) & masks[RULE]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]; net=gross-e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({"entry_ts":entry_ts,"exit_ts":exit_ts,"clock":int(clock),"gross":float(g),"net":float(n)})
    return pd.DataFrame(rows, columns=["entry_ts","exit_ts","clock","gross","net"])

def main():
    prior=pd.read_csv(PRIOR)
    if len(prior)!=5: raise AssertionError(f"expected 5 frozen cells, got {len(prior)}")
    if set(prior.hour_wib.astype(int))!={HOUR}: raise AssertionError("frozen hour changed")
    if set(prior.character_rule.astype(str))!={RULE}: raise AssertionError("frozen rule changed")
    actual=set(zip(prior.lookback_min.astype(int), prior.hold_min.astype(int)))
    if actual!=EXPECTED: raise AssertionError(f"frozen cells changed: {sorted(actual)}")

    e12.base.synthetic_tests()
    x5, coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if not bool((idx>=START).any()): raise RuntimeError(f"no 2026 bars; latest={idx.max()}")
    last_ts=idx.max()
    x=x5[idx<=last_ts].copy()
    e12.CLOCKS=r1.clocks_for_hour(HOUR)
    e12.LOOKBACKS=sorted(prior.lookback_min.astype(int).unique().tolist())
    e12.HOLDS=sorted(prior.hold_min.astype(int).unique().tolist())
    cache=e12.prep(x)

    rows=[]
    for c in prior.sort_values(["hold_min","lookback_min"]).itertuples(index=False):
        lb=int(c.lookback_min); hold=int(c.hold_min)
        T=events_for_period(cache,lb,hold,last_ts); st=stats(T)
        wr=float(st["win_rate"]) if finite(st["win_rate"]) else np.nan
        exp=float(st["expectancy"]) if finite(st["expectancy"]) else np.nan
        pf=float(st["pf"]) if finite(st["pf"]) else np.nan
        dd=float(st["max_dd"]) if finite(st["max_dd"]) else np.nan
        dd_cap=min(160.0,1.50*float(c.dev2022_dd)+20.0)
        ls_warn=max(12,int(c.dev2022_ls)+4)
        viable=bool(st["trades"]>=50 and finite(wr) and wr>=.52 and st["net_pnl"]>0 and finite(exp) and exp>0 and finite(pf) and pf>=1.15 and finite(dd) and dd<=dd_cap)
        rows.append({
            "hour_wib":HOUR,"component_rank":int(c.component_rank),"character_rule":RULE,"lookback_min":lb,"hold_min":hold,
            "dev2022_n":int(c.dev2022_n),"dev2022_wr":float(c.dev2022_wr),"dev2022_exp":float(c.dev2022_exp),"dev2022_pf":float(c.dev2022_pf),
            "test2023_n":int(c.test2023_n),"test2023_wr":float(c.test2023_wr),"test2023_exp":float(c.test2023_exp),"test2023_pf":float(c.test2023_pf),
            "y2024_n":int(c.y2024_n),"y2024_wr":float(c.y2024_wr),"y2024_exp":float(c.y2024_exp),"y2024_pf":float(c.y2024_pf),
            "oos2025_n":int(c.oos2025_n),"oos2025_wr":float(c.oos2025_wr),"oos2025_exp":float(c.oos2025_exp),"oos2025_pf":float(c.oos2025_pf),
            "ytd2026_n":int(st["trades"]),"ytd2026_wr":wr,"ytd2026_net":float(st["net_pnl"]),"ytd2026_exp":exp,"ytd2026_pf":pf,
            "ytd2026_dd":dd,"ytd2026_ls":int(st["max_loss_streak"]),"dd_cap":dd_cap,"ls_warning_threshold":ls_warn,
            "risk_clustering_warning":bool(st["max_loss_streak"]>ls_warn),"economically_viable_2026_ytd":viable,"dataset_last_ts_utc":last_ts.isoformat()
        })

    R=pd.DataFrame(rows).sort_values(["hold_min","lookback_min"]).reset_index(drop=True); R.to_csv(OUT_CELLS,index=False)
    n=len(R); viable_n=int(R.economically_viable_2026_ytd.sum()); pos_n=int((R.ytd2026_net>0).sum())
    med_wr=float(R.ytd2026_wr.median()); med_exp=float(R.ytd2026_exp.median()); med_pf=float(R.ytd2026_pf.median())
    total_net=float(R.ytd2026_net.sum()); max_dd=float(R.ytd2026_dd.max()); warns=int(R.risk_clustering_warning.sum())
    if viable_n/n>=.50 and med_exp>0 and med_pf>=1.15: verdict="CURRENT_REGIME_PLATEAU_ALIVE"
    elif viable_n>=2 or (med_exp>0 and med_pf>1.00): verdict="CURRENT_REGIME_PARTIAL_PERSISTENCE"
    else: verdict="CURRENT_REGIME_PLATEAU_WEAK"
    a=R[(R.lookback_min==240)&(R.hold_min==360)].iloc[0]
    lines=["# ETH R4b — Stage E 2026 YTD Shadow / Current-Regime Check","","**SHADOW CHECK ONLY. FROZEN H04 PLATEAU. NO RESELECTION. NO RETUNING.**","",
           f"Dataset latest timestamp: **{last_ts.isoformat()}**.",f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",f"Frozen plateau: **H{HOUR:02d} {RULE}**, size **{n}**.",
           f"2026 YTD economically viable cells: **{viable_n}/{n}**; Net-positive cells: **{pos_n}/{n}**.",f"2026 YTD plateau medians: WR **{100*med_wr:.2f}%**, Exp **${med_exp:+.2f}**, PF **{med_pf:.3f}**.",
           f"Sum of per-cell Net (descriptive, overlapping variants): **${total_net:+.2f}**; max cell DD **${max_dd:.2f}**.",f"Risk-clustering warnings: **{warns}/{n}**.",f"Stage E verdict: **{verdict}**.","",
           "| LB/Hold | 2026 YTD N | WR | Net | Exp | PF | DD | LS | Viable | Risk warn |","|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|"]
    for r in R.itertuples(index=False):
        lines.append(f"| LB{int(r.lookback_min)}/H{int(r.hold_min)} | {int(r.ytd2026_n)} | {100*float(r.ytd2026_wr):.2f}% | ${float(r.ytd2026_net):+.2f} | ${float(r.ytd2026_exp):+.2f} | {float(r.ytd2026_pf):.3f} | ${float(r.ytd2026_dd):.2f} | {int(r.ytd2026_ls)} | {'Y' if r.economically_viable_2026_ytd else 'N'} | {'Y' if r.risk_clustering_warning else 'N'} |")
    lines += ["","## Canonical pre-2026 anchor continuity — LB240/H360","","| Period | N | WR | Exp | PF |","|---|---:|---:|---:|---:|",
              f"| 2022 Dev | {int(a.dev2022_n)} | {100*float(a.dev2022_wr):.2f}% | ${float(a.dev2022_exp):+.2f} | {float(a.dev2022_pf):.3f} |",
              f"| 2023 Test | {int(a.test2023_n)} | {100*float(a.test2023_wr):.2f}% | ${float(a.test2023_exp):+.2f} | {float(a.test2023_pf):.3f} |",
              f"| 2024 Confirm | {int(a.y2024_n)} | {100*float(a.y2024_wr):.2f}% | ${float(a.y2024_exp):+.2f} | {float(a.y2024_pf):.3f} |",
              f"| 2025 Final OOS | {int(a.oos2025_n)} | {100*float(a.oos2025_wr):.2f}% | ${float(a.oos2025_exp):+.2f} | {float(a.oos2025_pf):.3f} |",
              f"| 2026 YTD Shadow | {int(a.ytd2026_n)} | {100*float(a.ytd2026_wr):.2f}% | ${float(a.ytd2026_exp):+.2f} | {float(a.ytd2026_pf):.3f} |","",
              "Stage D 2025 remains the final untouched full-year OOS verdict. Stage E is a current-regime shadow observation only.","No 2026 result is used to select a new timing cell, threshold, rule, or hour."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); OUT_STATUS.write_text(verdict+"\n"); print("\n".join(lines))

if __name__=="__main__": main()
