#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT=Path(__file__).resolve().parent.parent
HOLDS=(60,120,240,360)
LOOKBACKS=(15,30,60,120,240,360)


def clocks_for_hour(h):
    b=((h-7)%24)*60
    return tuple((b+q)%1440 for q in (0,15,30,45))

def rank_passers(D):
    C=D[D.candidate_gate].copy().sort_values(
        ["min_year_exp","supportive_anchors","expectancy","win_rate","pf","max_dd","max_loss_streak","hold_min","lookback_min","character_rule"],
        ascending=[False,False,False,False,False,True,True,True,True,True]).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return C

def representative(D):
    return D.sort_values(
        ["candidate_gate","anchor_gate","pooled_gate","era_gate","min_year_exp","supportive_anchors","expectancy","win_rate","pf","max_dd","max_loss_streak","hold_min","lookback_min","character_rule"],
        ascending=[False,False,False,False,False,False,False,False,False,True,True,True,True,True]).reset_index(drop=True).iloc[0]

def main():
    h=int(os.environ["E15A_HOUR_WIB"])
    e12.base.synthetic_tests(); x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(coverage)
    e12.HOLDS=HOLDS; e12.LOOKBACKS=LOOKBACKS; e12.CLOCKS=clocks_for_hour(h)
    cache=e12.prep(x5)
    rows=[e12.candidate(cache,lb,hold,rule) for lb in LOOKBACKS for hold in HOLDS for rule in e12.RULES]
    D=pd.DataFrame(rows)
    if len(D)!=2160: raise AssertionError(len(D))
    D.insert(0,"hour_wib",h)
    C=rank_passers(D); r=representative(D)
    pfx=ROOT/f"ETH_E15A_H{h:02d}"
    D.to_csv(str(pfx)+"_Grid.csv",index=False)
    C.to_csv(str(pfx)+"_Passers.csv",index=False)
    S=pd.DataFrame([{
        "hour_wib":h,"coverage":coverage,"formal_status":"PASS" if bool(r.candidate_gate) else "FAIL","full_gate_passers":int(D.candidate_gate.sum()),
        "character_rule":r.character_rule,"lookback_min":int(r.lookback_min),"hold_min":int(r.hold_min),"trades":int(r.trades),
        "win_rate":r.win_rate,"net_pnl":r.net_pnl,"expectancy":r.expectancy,"pf":r.pf,"max_dd":r.max_dd,"max_loss_streak":int(r.max_loss_streak),
        "supportive_anchors":int(r.supportive_anchors),"evaluable_anchors":int(r.evaluable_anchors),"anchor_gate":bool(r.anchor_gate),"pooled_gate":bool(r.pooled_gate),"era_gate":bool(r.era_gate),
        "min_year_exp":r.min_year_exp,"years_wr55":int(r.years_wr55),
        "y2022_wr":r.y2022_wr,"y2022_exp":r.y2022_exp,"y2022_net":r.y2022_net,"y2022_pf":r.y2022_pf,
        "y2023_wr":r.y2023_wr,"y2023_exp":r.y2023_exp,"y2023_net":r.y2023_net,"y2023_pf":r.y2023_pf,
        "y2024_wr":r.y2024_wr,"y2024_exp":r.y2024_exp,"y2024_net":r.y2024_net,"y2024_pf":r.y2024_pf,
    }])
    S.to_csv(str(pfx)+"_Summary.csv",index=False)
    print(S.to_string(index=False))
if __name__=="__main__": main()
