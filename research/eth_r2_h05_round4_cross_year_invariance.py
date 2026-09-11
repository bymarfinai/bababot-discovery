#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT=Path(__file__).resolve().parent.parent
PFX="ETH_R2_H05_R4"
OUT_GRID=ROOT/f"{PFX}_CrossYearGrid.csv"
OUT_REGIONS=ROOT/f"{PFX}_Regions.csv"
OUT_LOCK=ROOT/f"{PFX}_FrozenRegion.csv"
OUT_RESULT=ROOT/f"{PFX}_Result.md"
OUT_STATUS=ROOT/f"{PFX}_Status.txt"
LOOKBACKS=r1.LOOKBACKS; HOLDS=r1.HOLDS


def finite(x): return bool(np.isfinite(x))
def summ(T): return r1.stats_from_df(T)

def year_eval(T:pd.DataFrame,y:int):
    a=pd.Timestamp(f"{y}-01-01",tz="UTC"); m=pd.Timestamp(f"{y}-07-01",tz="UTC"); z=pd.Timestamp(f"{y+1}-01-01",tz="UTC")
    Y=T[(pd.DatetimeIndex(T.entry_ts)>=a)&(pd.DatetimeIndex(T.exit_ts)<z)]
    S=summ(Y)
    H1=summ(Y[(pd.DatetimeIndex(Y.entry_ts)>=a)&(pd.DatetimeIndex(Y.exit_ts)<m)])
    H2=summ(Y[(pd.DatetimeIndex(Y.entry_ts)>=m)&(pd.DatetimeIndex(Y.exit_ts)<z)])
    eval_a=0; pos_a=0
    for clock in e12.CLOCKS:
        A=summ(Y[Y.clock==clock]); ev=A["trades"]>=12
        pos=bool(ev and finite(A["expectancy"]) and A["expectancy"]>0 and finite(A["pf"]) and A["pf"]>1)
        eval_a+=int(ev); pos_a+=int(pos)
    halves=bool(H1["trades"]>=18 and H2["trades"]>=18 and finite(H1["expectancy"]) and H1["expectancy"]>0 and finite(H1["pf"]) and H1["pf"]>1 and finite(H2["expectancy"]) and H2["expectancy"]>0 and finite(H2["pf"]) and H2["pf"]>1)
    supportive=bool(S["trades"]>=50 and finite(S["win_rate"]) and S["win_rate"]>=.52 and S["net_pnl"]>0 and finite(S["expectancy"]) and S["expectancy"]>0 and finite(S["pf"]) and S["pf"]>=1.05 and finite(S["max_dd"]) and S["max_dd"]<=125 and S["max_loss_streak"]<=10 and halves and eval_a>=3 and pos_a>=2)
    strict=bool(supportive and S["trades"]>=60 and S["win_rate"]>=.55 and S["expectancy"]>=.50 and S["pf"]>=1.20 and S["max_dd"]<=110 and S["max_loss_streak"]<=8 and pos_a>=3)
    return {"trades":S["trades"],"wr":S["win_rate"],"net":S["net_pnl"],"exp":S["expectancy"],"pf":S["pf"],"dd":S["max_dd"],"ls":S["max_loss_streak"],
            "H1_exp":H1["expectancy"],"H1_pf":H1["pf"],"H2_exp":H2["expectancy"],"H2_pf":H2["pf"],"evaluable_anchors":eval_a,"positive_anchors":pos_a,
            "supportive":supportive,"strict":strict}

def main():
    e12.base.synthetic_tests(); x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    end=pd.Timestamp("2024-01-01",tz="UTC"); x=x5.loc[pd.DatetimeIndex(x5.index)<end].copy()
    e12.CLOCKS=r1.clocks_for_hour(5); e12.LOOKBACKS=LOOKBACKS; e12.HOLDS=HOLDS
    cache=e12.prep(x)
    rows=[]
    for rule in e12.RULES:
        for lb in LOOKBACKS:
            for h in HOLDS:
                T=r1.candidate_events(cache,lb,h,rule)
                a=year_eval(T,2022); b=year_eval(T,2023)
                rows.append({"character_rule":rule,"lookback_min":lb,"hold_min":h,
                             **{f"y2022_{k}":v for k,v in a.items()},**{f"y2023_{k}":v for k,v in b.items()},
                             "min_year_exp":min(a["exp"] if finite(a["exp"]) else -np.inf,b["exp"] if finite(b["exp"]) else -np.inf),
                             "min_year_pf":min(a["pf"] if finite(a["pf"]) else -np.inf,b["pf"] if finite(b["pf"]) else -np.inf),
                             "max_year_dd":max(a["dd"] if finite(a["dd"]) else np.inf,b["dd"] if finite(b["dd"]) else np.inf),
                             "cross_year_stable":bool(a["supportive"] and b["supportive"]),"strict_both":bool(a["strict"] and b["strict"])})
    D=pd.DataFrame(rows)
    if len(D)!=1800: raise AssertionError(len(D))
    D.to_csv(OUT_GRID,index=False)

    li={v:i for i,v in enumerate(LOOKBACKS)}; hi={v:i for i,v in enumerate(HOLDS)}
    rr=[]; rc={}; rid=0
    for rule in e12.RULES:
        F=D[(D.character_rule==rule)&D.cross_year_stable]
        coords=[(li[int(x.lookback_min)],hi[int(x.hold_min)]) for x in F.itertuples(index=False)]
        for comp in r1.connected_components(coords):
            rid+=1; cells=[]
            for i,j in comp: cells.append(D[(D.character_rule==rule)&(D.lookback_min==LOOKBACKS[i])&(D.hold_min==HOLDS[j])].iloc[0])
            C=pd.DataFrame(cells); lbs=sorted(set(int(x) for x in C.lookback_min)); hs=sorted(set(int(x) for x in C.hold_min))
            strict=int(C.strict_both.astype(bool).sum()); mex=float(C.min_year_exp.median()); mpf=float(C.min_year_pf.median()); mdd=float(C.max_year_dd.median())
            q=bool(len(C)>=4 and len(lbs)>=2 and len(hs)>=2 and strict>=1 and mex>=.25 and mpf>=1.10 and mdd<=125)
            rr.append({"region_id":rid,"character_rule":rule,"cells":len(C),"lookbacks":";".join(map(str,lbs)),"holds":";".join(map(str,hs)),"strict_both_cells":strict,"median_min_year_exp":mex,"median_min_year_pf":mpf,"median_max_year_dd":mdd,"qualifies":q}); rc[rid]=C
    R=pd.DataFrame(rr,columns=["region_id","character_rule","cells","lookbacks","holds","strict_both_cells","median_min_year_exp","median_min_year_pf","median_max_year_dd","qualifies"])
    R.to_csv(OUT_REGIONS,index=False); Q=R[R.qualifies].copy()
    lines=["# ETH R2 H05 — Round 4 Cross-Year Invariance","","**2022 AND 2023 EVALUATED SEPARATELY. 2024 HARD LOCKED. OOS CLOSED.**","",
           f"Source coverage: {coverage:.4%}. Original grammar: 90 rules × 20 coarse timings = **{len(D)} cells**.",
           f"2022 supportive cells: **{int(D.y2022_supportive.sum())}**; 2023 supportive cells: **{int(D.y2023_supportive.sum())}**.",
           f"Exact same rule/LB/Hold supportive in both years: **{int(D.cross_year_stable.sum())}**; strict in both: **{int(D.strict_both.sum())}**.",
           f"Qualifying invariant regions: **{len(Q)}**.",""]
    if len(Q)==0:
        status="ETH_R2_H05_LAB_NO_ROBUST_EDGE"; OUT_STATUS.write_text(status+"\n")
        if OUT_LOCK.exists(): OUT_LOCK.unlink()
        lines += ["## Verdict","","**H05_LAB_NO_ROBUST_EDGE**","","Four bounded rounds did not establish a parameter- and time-invariant H05 LONG habitat. Round 5 is not used for another search. 2024 remains unopened."]
    else:
        Q=Q.sort_values(["strict_both_cells","cells","median_min_year_exp","median_min_year_pf","median_max_year_dd","character_rule"],ascending=[False,False,False,False,True,True]).reset_index(drop=True)
        reg=Q.iloc[0]; C=rc[int(reg.region_id)]; strict=C[C.strict_both].copy(); comp=[(li[int(x.lookback_min)],hi[int(x.hold_min)]) for x in C.itertuples(index=False)]
        strict["dist"]=[sum(abs(li[int(x.lookback_min)]-i)+abs(hi[int(x.hold_min)]-j) for i,j in comp) for x in strict.itertuples(index=False)]
        strict=strict.sort_values(["dist","hold_min","lookback_min"]).reset_index(drop=True); rep=strict.iloc[0]
        coords=";".join(f"{int(x.lookback_min)}x{int(x.hold_min)}" for x in C.sort_values(["lookback_min","hold_min"]).itertuples(index=False))
        pd.DataFrame([{"region_id":int(reg.region_id),"character_rule":reg.character_rule,"region_coords":coords,"region_cells":int(reg.cells),"strict_both_cells":int(reg.strict_both_cells),
                       "median_min_year_exp":float(reg.median_min_year_exp),"median_min_year_pf":float(reg.median_min_year_pf),"median_max_year_dd":float(reg.median_max_year_dd),
                       "representative_lb":int(rep.lookback_min),"representative_hold":int(rep.hold_min),"round5_opened":False}]).to_csv(OUT_LOCK,index=False)
        status="ETH_R2_H05_R4_INVARIANT_REGION_FROZEN"; OUT_STATUS.write_text(status+"\n")
        lines += ["## Verdict","","**R4_INVARIANT_REGION_FROZEN**","",f"Rule **{reg.character_rule}**, {int(reg.cells)} stable cells / {int(reg.strict_both_cells)} strict-both; representative **LB{int(rep.lookback_min)}/H{int(rep.hold_min)}**.","Round 5 may test executable/perturbation robustness. 2024 remains locked."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print("\n".join(lines))
if __name__=="__main__": main()
