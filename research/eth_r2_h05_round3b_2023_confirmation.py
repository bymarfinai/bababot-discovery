#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT=Path(__file__).resolve().parent.parent
LOCK=ROOT/"ETH_R2_H05_R3A_Frozen2022Region.csv"
PFX="ETH_R2_H05_R3B"
OUT_CELLS=ROOT/f"{PFX}_2023RegionCells.csv"
OUT_CONFIRM=ROOT/f"{PFX}_Confirmation.csv"
OUT_RESULT=ROOT/f"{PFX}_Result.md"
OUT_STATUS=ROOT/f"{PFX}_Status.txt"
START=pd.Timestamp("2023-01-01",tz="UTC"); MID=pd.Timestamp("2023-07-01",tz="UTC"); END=pd.Timestamp("2024-01-01",tz="UTC")


def finite(x): return bool(np.isfinite(x))
def summ(T): return r1.stats_from_df(T)

def events(cache,lb,hold,key):
    rows=[]
    for clock in e12.CLOCKS:
        S,ent,pre,ex,valid,xp,delta,masks=cache[(clock,lb,hold)]
        exi=pd.DatetimeIndex(ex)
        m=valid&(pre>=START)&(ent>=START)&(exi<END)&masks[key]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]; net=gross-e12.FEE
        for et,xt,g,n in zip(ent[m],exi[m],gross,net): rows.append({"entry_ts":et,"exit_ts":xt,"clock":int(clock),"gross":float(g),"net":float(n)})
    if not rows: return pd.DataFrame(columns=["entry_ts","exit_ts","clock","gross","net"])
    return pd.DataFrame(rows).sort_values(["entry_ts","clock"]).reset_index(drop=True)

def period(T,a,b):
    m=(pd.DatetimeIndex(T.entry_ts)>=a)&(pd.DatetimeIndex(T.exit_ts)<b); return summ(T.loc[m])

def eval_coord(cache,lb,hold,key):
    T=events(cache,lb,hold,key); s=summ(T); h1=period(T,START,MID); h2=period(T,MID,END)
    posanchors=0
    for clock in e12.CLOCKS:
        a=summ(T[T.clock==clock]); posanchors+=int(finite(a["expectancy"]) and a["expectancy"]>0 and finite(a["pf"]) and a["pf"]>1)
    return {"lookback_min":lb,"hold_min":hold,**s,
            "H1_trades":h1["trades"],"H1_exp":h1["expectancy"],"H1_pf":h1["pf"],"H1_net":h1["net_pnl"],
            "H2_trades":h2["trades"],"H2_exp":h2["expectancy"],"H2_pf":h2["pf"],"H2_net":h2["net_pnl"],
            "positive_anchors":posanchors}

def main():
    if OUT_RESULT.exists(): raise RuntimeError("R3B one-shot result already exists; refusing to re-open 2023")
    if not LOCK.exists(): raise FileNotFoundError(LOCK)
    L=pd.read_csv(LOCK)
    if len(L)!=1: raise AssertionError("expected exactly one frozen R3A region")
    lock=L.iloc[0]
    if bool(lock.confirm_2023_opened): raise RuntimeError("lock says 2023 already opened")
    pair=str(lock.pair_state); key=f"R3_{pair}"
    coords=[]
    for token in str(lock.region_coords).split(";"):
        lb,h=token.split("x"); coords.append((int(lb),int(h)))
    rep=(int(lock.representative_lb),int(lock.representative_hold))
    if rep not in coords: raise AssertionError("representative not in frozen region")

    e12.base.synthetic_tests(); x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    # Hard firewall: 2024+ bars are not passed to the confirmation engine.
    xconf=x5.loc[pd.DatetimeIndex(x5.index)<END].copy()
    e12.CLOCKS=r1.clocks_for_hour(5); e12.LOOKBACKS=r1.LOOKBACKS; e12.HOLDS=r1.HOLDS
    cache=e12.prep(xconf)
    for pack in cache.values():
        S,ent,pre,ex,valid,xp,delta,masks=pack
        masks[key]=masks["DRIVE_DOWN"] & masks[pair]

    C=pd.DataFrame([eval_coord(cache,lb,h,key) for lb,h in coords])
    C["economic_positive"]=(C.expectancy>0)&(C.pf>1)
    C.to_csv(OUT_CELLS,index=False)
    R=C[(C.lookback_min==rep[0])&(C.hold_min==rep[1])].iloc[0]
    rep_pass=bool(
        R.trades>=45 and R.net_pnl>0 and finite(R.expectancy) and R.expectancy>0 and finite(R.pf) and R.pf>=1.05 and
        R.max_dd<=150 and R.max_loss_streak<=10 and
        R.H1_trades>=18 and finite(R.H1_exp) and R.H1_exp>0 and finite(R.H1_pf) and R.H1_pf>1 and
        R.H2_trades>=18 and finite(R.H2_exp) and R.H2_exp>0 and finite(R.H2_pf) and R.H2_pf>1 and
        R.positive_anchors>=2
    )
    positive_fraction=float(C.economic_positive.mean()); med_exp=float(C.expectancy.median()); med_pf=float(C.pf.median())
    region_pass=bool(positive_fraction>=.50 and med_exp>0 and med_pf>1)
    overall=rep_pass and region_pass
    pd.DataFrame([{"character_rule":str(lock.character_rule),"pair_state":pair,"region_cells":len(C),
                   "representative_lb":rep[0],"representative_hold":rep[1],"representative_n":int(R.trades),
                   "representative_wr":float(R.win_rate),"representative_net":float(R.net_pnl),"representative_exp":float(R.expectancy),
                   "representative_pf":float(R.pf),"representative_dd":float(R.max_dd),"representative_ls":int(R.max_loss_streak),
                   "representative_H1_exp":float(R.H1_exp),"representative_H1_pf":float(R.H1_pf),
                   "representative_H2_exp":float(R.H2_exp),"representative_H2_pf":float(R.H2_pf),
                   "representative_positive_anchors":int(R.positive_anchors),"rep_pass":rep_pass,
                   "region_positive_fraction":positive_fraction,"region_median_exp":med_exp,"region_median_pf":med_pf,
                   "region_pass":region_pass,"overall_pass":overall}]).to_csv(OUT_CONFIRM,index=False)
    if overall:
        status="ETH_R2_H05_R3_INTERNAL_CONFIRMATION_PASS"; verdict="R3_INTERNAL_CONFIRMATION_PASS"
    else:
        status="ETH_R2_H05_R3_INTERNAL_CONFIRMATION_FAIL"; verdict="R3_INTERNAL_CONFIRMATION_FAIL"
    OUT_STATUS.write_text(status+"\n")
    lines=["# ETH R2 H05 — Round 3B 2023 Internal Confirmation","",
           "**EXACT FROZEN R3A REGION ONLY. 2024 HARD LOCKED. OOS CLOSED.**","",
           f"Rule: **{lock.character_rule}**; frozen region cells: **{len(C)}**; representative **LB{rep[0]}/H{rep[1]}**.",
           f"Representative 2023: N {int(R.trades)}, WR {100*float(R.win_rate):.2f}%, net ${float(R.net_pnl):+.2f}, exp ${float(R.expectancy):+.2f}, PF {float(R.pf):.3f}, DD ${float(R.max_dd):.2f}, LS {int(R.max_loss_streak)}.",
           f"Half-years: H1 exp ${float(R.H1_exp):+.2f}/PF {float(R.H1_pf):.3f}; H2 exp ${float(R.H2_exp):+.2f}/PF {float(R.H2_pf):.3f}; positive anchors {int(R.positive_anchors)}/4.",
           f"Frozen region 2023: {100*positive_fraction:.1f}% cells economic-positive; median exp ${med_exp:+.2f}; median PF {med_pf:.3f}.",
           f"Representative gate: **{'PASS' if rep_pass else 'FAIL'}**; region gate: **{'PASS' if region_pass else 'FAIL'}**.","",
           "## Verdict","",f"**{verdict}**","",
           "No alternate 2022 region or timing was evaluated for selection after opening 2023. 2024 remains unopened."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print("\n".join(lines))
if __name__=="__main__": main()
