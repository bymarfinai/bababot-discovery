#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R2_H03_R3A"
OUT_GRID = ROOT / f"{PFX}_2022Grid.csv"
OUT_REGIONS = ROOT / f"{PFX}_2022Regions.csv"
OUT_LOCK = ROOT / f"{PFX}_Frozen2022Region.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

HOUR_WIB = 3
LOOKBACKS = r1.LOOKBACKS
HOLDS = r1.HOLDS
START = pd.Timestamp("2022-01-01", tz="UTC")
MID = pd.Timestamp("2022-07-01", tz="UTC")
END = pd.Timestamp("2023-01-01", tz="UTC")
PAIR_STATES = tuple(sorted(x for x in e12.E11_RULES if "__" in x))
if len(PAIR_STATES) != 36:
    raise AssertionError(f"expected 36 E11 pair states, got {len(PAIR_STATES)}")


def finite(x): return bool(np.isfinite(x))
def summarize(T): return r1.stats_from_df(T)


def events(cache, lb, hold, key):
    rows=[]
    for clock in e12.CLOCKS:
        S,ent,pre,ex,valid,xp,delta,masks=cache[(clock,lb,hold)]
        exi=pd.DatetimeIndex(ex)
        m=valid&(pre>=START)&(ent>=START)&(exi<END)&masks[key]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]; net=gross-e12.FEE
        for et,xt,g,n in zip(ent[m],exi[m],gross,net):
            rows.append({"entry_ts":et,"exit_ts":xt,"clock":int(clock),"gross":float(g),"net":float(n)})
    if not rows:
        return pd.DataFrame(columns=["entry_ts","exit_ts","clock","gross","net"])
    return pd.DataFrame(rows).sort_values(["entry_ts","clock"]).reset_index(drop=True)


def period(T,a,z):
    m=(pd.DatetimeIndex(T.entry_ts)>=a)&(pd.DatetimeIndex(T.exit_ts)<z)
    return summarize(T.loc[m])


def eval_cell(cache,lb,hold,pair):
    T=events(cache,lb,hold,f"R3_{pair}"); s=summarize(T)
    h1=period(T,START,MID); h2=period(T,MID,END)
    min_half_exp=min(h1["expectancy"] if finite(h1["expectancy"]) else -np.inf,
                     h2["expectancy"] if finite(h2["expectancy"]) else -np.inf)
    half_ok=bool(h1["trades"]>=18 and h2["trades"]>=18 and
                 finite(h1["expectancy"]) and h1["expectancy"]>0 and finite(h1["pf"]) and h1["pf"]>1 and
                 finite(h2["expectancy"]) and h2["expectancy"]>0 and finite(h2["pf"]) and h2["pf"]>1)
    supportive=bool(s["trades"]>=45 and finite(s["win_rate"]) and s["win_rate"]>=.52 and s["net_pnl"]>0 and
                    finite(s["expectancy"]) and s["expectancy"]>0 and finite(s["pf"]) and s["pf"]>=1.05 and
                    finite(s["max_dd"]) and s["max_dd"]<=125 and s["max_loss_streak"]<=10 and half_ok)
    eval_a=0; pos_a=0
    for clock in e12.CLOCKS:
        a=summarize(T[T.clock==clock]); ev=a["trades"]>=12
        pos=bool(ev and finite(a["expectancy"]) and a["expectancy"]>0 and finite(a["pf"]) and a["pf"]>1)
        eval_a+=int(ev); pos_a+=int(pos)
    strict=bool(supportive and s["trades"]>=60 and s["win_rate"]>=.55 and s["expectancy"]>=.50 and
                s["pf"]>=1.20 and s["max_dd"]<=110 and s["max_loss_streak"]<=8 and eval_a>=3 and pos_a>=3)
    return {"character_rule":pair,"pair_state":pair,"lookback_min":lb,"hold_min":hold,**s,
            "H1_trades":h1["trades"],"H1_wr":h1["win_rate"],"H1_net":h1["net_pnl"],"H1_exp":h1["expectancy"],"H1_pf":h1["pf"],
            "H2_trades":h2["trades"],"H2_wr":h2["win_rate"],"H2_net":h2["net_pnl"],"H2_exp":h2["expectancy"],"H2_pf":h2["pf"],
            "min_half_exp":float(min_half_exp),"evaluable_anchors":eval_a,"positive_anchors":pos_a,
            "discovery_supportive":supportive,"discovery_strict":strict}


def main():
    e12.base.synthetic_tests(); x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    xdisc=x5.loc[pd.DatetimeIndex(x5.index)<END].copy()
    e12.CLOCKS=r1.clocks_for_hour(HOUR_WIB); e12.LOOKBACKS=LOOKBACKS; e12.HOLDS=HOLDS
    cache=e12.prep(xdisc)
    for pack in cache.values():
        S,ent,pre,ex,valid,xp,delta,masks=pack
        for pair in PAIR_STATES:
            masks[f"R3_{pair}"]=masks[pair]

    D=pd.DataFrame([eval_cell(cache,lb,h,pair) for pair in PAIR_STATES for lb in LOOKBACKS for h in HOLDS])
    if len(D)!=720: raise AssertionError(len(D))
    D.to_csv(OUT_GRID,index=False)

    li={v:i for i,v in enumerate(LOOKBACKS)}; hi={v:i for i,v in enumerate(HOLDS)}
    region_rows=[]; region_cells={}; rid=0
    for pair in PAIR_STATES:
        F=D[(D.pair_state==pair)&D.discovery_supportive].copy()
        coords=[(li[int(r.lookback_min)],hi[int(r.hold_min)]) for r in F.itertuples(index=False)]
        for comp in r1.connected_components(coords):
            rid+=1; C=[]
            for i,j in comp:
                C.append(D[(D.pair_state==pair)&(D.lookback_min==LOOKBACKS[i])&(D.hold_min==HOLDS[j])].iloc[0])
            C=pd.DataFrame(C); lbs=sorted(set(int(x) for x in C.lookback_min)); holds=sorted(set(int(x) for x in C.hold_min))
            stricts=int(C.discovery_strict.astype(bool).sum()); med_min_half=float(C.min_half_exp.median())
            med_exp=float(C.expectancy.median()); med_pf=float(C.pf.median()); med_dd=float(C.max_dd.median())
            q=bool(len(C)>=4 and len(lbs)>=2 and len(holds)>=2 and stricts>=1 and med_exp>=.25 and med_pf>=1.10 and med_min_half>0)
            region_rows.append({"region_id":rid,"pair_state":pair,"character_rule":pair,"cells":len(C),"lookbacks":";".join(map(str,lbs)),
                                "holds":";".join(map(str,holds)),"strict_cells":stricts,"median_min_half_exp":med_min_half,
                                "median_exp":med_exp,"median_pf":med_pf,"median_dd":med_dd,"qualifies":q})
            region_cells[rid]=C
    R=pd.DataFrame(region_rows,columns=["region_id","pair_state","character_rule","cells","lookbacks","holds","strict_cells","median_min_half_exp","median_exp","median_pf","median_dd","qualifies"])
    R.to_csv(OUT_REGIONS,index=False); Q=R[R.qualifies].copy()

    lines=["# ETH R2 H03 — Round 3A 2022 Nested Market-State Discovery","",
           "**DISCOVERY = 2022 ONLY. 2023 INTERNAL HOLDOUT UNOPENED. 2024 HARD LOCKED. OOS CLOSED.**","",
           f"Source coverage: {coverage:.4%}.",f"Grammar: {len(PAIR_STATES)} causal E11 pair states × 20 coarse timings = **{len(D)} cells**.",
           f"Supportive 2022 cells: **{int(D.discovery_supportive.sum())}**; strict cells: **{int(D.discovery_strict.sum())}**; qualifying regions: **{len(Q)}**.",""]
    if len(Q)==0:
        OUT_STATUS.write_text("ETH_R2_H03_R3A_NO_2022_ROBUST_REGION\n")
        if OUT_LOCK.exists(): OUT_LOCK.unlink()
        lines += ["## Verdict","","**R3A_NO_2022_ROBUST_REGION**","","2023 remains unopened; no Round-3 state may be rescued using holdout knowledge."]
    else:
        Q=Q.sort_values(["strict_cells","cells","median_min_half_exp","median_exp","median_pf","median_dd","character_rule"],
                        ascending=[False,False,False,False,False,True,True]).reset_index(drop=True)
        reg=Q.iloc[0]; C=region_cells[int(reg.region_id)].copy(); strict=C[C.discovery_strict].copy()
        compcoords=[(li[int(x.lookback_min)],hi[int(x.hold_min)]) for x in C.itertuples(index=False)]
        strict["dist"]=[sum(abs(li[int(x.lookback_min)]-a)+abs(hi[int(x.hold_min)]-b) for a,b in compcoords) for x in strict.itertuples(index=False)]
        strict=strict.sort_values(["dist","hold_min","lookback_min"]).reset_index(drop=True); rep=strict.iloc[0]
        coords=";".join(f"{int(x.lookback_min)}x{int(x.hold_min)}" for x in C.sort_values(["lookback_min","hold_min"]).itertuples(index=False))
        pd.DataFrame([{"region_id":int(reg.region_id),"pair_state":reg.pair_state,"character_rule":reg.character_rule,"region_coords":coords,
                       "region_cells":int(reg.cells),"region_strict_cells":int(reg.strict_cells),"region_median_min_half_exp":float(reg.median_min_half_exp),
                       "region_median_exp":float(reg.median_exp),"region_median_pf":float(reg.median_pf),"representative_lb":int(rep.lookback_min),
                       "representative_hold":int(rep.hold_min),"representative_n":int(rep.trades),"representative_wr":float(rep.win_rate),
                       "representative_exp":float(rep.expectancy),"representative_pf":float(rep.pf),"representative_dd":float(rep.max_dd),
                       "representative_ls":int(rep.max_loss_streak),"confirm_2023_opened":False}]).to_csv(OUT_LOCK,index=False)
        OUT_STATUS.write_text("ETH_R2_H03_R3A_2022_REGION_FROZEN\n")
        lines += ["## Frozen 2022 region","",f"Rule: **{reg.character_rule}**; region {int(reg.cells)} cells / {int(reg.strict_cells)} strict.",
                  f"Representative by centrality: **LB{int(rep.lookback_min)} / H{int(rep.hold_min)}**; N {int(rep.trades)}, WR {100*float(rep.win_rate):.2f}%, exp ${float(rep.expectancy):+.2f}, PF {float(rep.pf):.3f}.",
                  "","The exact region is frozen. R3B may now open 2023 once; no reselection is allowed."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print("\n".join(lines))

if __name__=="__main__": main()
