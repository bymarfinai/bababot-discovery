#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_reset_g1_geometry as g1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G2_GEOMETRY_REFINE"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedSessionAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (30,60,90,120,150)
REFS = (60,90,120,150,180,210,240,270)
EXES = (420,480,540,600,660,720)
SIDE = "LONG"


def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def scan_dev(x5):
    rows=[]
    for c in CLOCKS:
        for r in REFS:
            for e in EXES:
                rows.append(g1.analyze_geometry(x5,c,r,e,"development",False)[SIDE])
    D=pd.DataFrame(rows)
    if len(D)!=240: raise AssertionError(f"expected 240 candidates, got {len(D)}")
    return D


def neigh_keys(r):
    c=int(r.clock_start_min_utc); ref=int(r.reference_min); exe=int(r.execution_min)
    out=[]
    if c-30 in CLOCKS: out.append((c-30,ref,exe))
    if c+30 in CLOCKS: out.append((c+30,ref,exe))
    if ref-30 in REFS: out.append((c,ref-30,exe))
    if ref+30 in REFS: out.append((c,ref+30,exe))
    if exe-60 in EXES: out.append((c,ref,exe-60))
    if exe+60 in EXES: out.append((c,ref,exe+60))
    return out


def leaderboard(D):
    D=D.copy()
    D["dev_gate"]=(D.signals>=80)&(D.continuation_rate>=.76)&(D.resolved_same_side_rate>=.81)&(D.wilson_lb95>=.66)&(D.positive_blocks>=3)
    lookup={(int(r.clock_start_min_utc),int(r.reference_min),int(r.execution_min)):r for r in D.itertuples(index=False)}
    nav=[]; nsup=[]; stable=[]
    for r in D.itertuples(index=False):
        ks=neigh_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            if int(x.signals)>=60 and float(x.continuation_rate)>=.72 and float(x.resolved_same_side_rate)>=.78: sup+=1
        need=max(2,math.ceil(.60*len(ks)))
        if len(ks)>=5: need=max(3,need)
        nav.append(len(ks)); nsup.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=nsup; D["local_stable"]=stable
    D["candidate_eligible"]=D.dev_gate&D.local_stable
    D["total_span_min"]=D.reference_min+D.execution_min
    C=D[D.candidate_eligible].copy().sort_values(
        ["wilson_lb95","min_qualified_block_cont","continuation_rate","resolved_same_side_rate","signals","median_minutes_to_target","total_span_min","clock_start_min_utc","reference_min","execution_min"],
        ascending=[False,False,False,False,False,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def replicate(x5,sel):
    rows=[]; audits=[]; okall=True
    for part in ("external","reference_validation"):
        r=g1.analyze_geometry(x5,int(sel.clock_start_min_utc),int(sel.reference_min),int(sel.execution_min),part,False)[SIDE]
        ok=int(r["signals"])>=40 and float(r["continuation_rate"])>=.72 and float(r["resolved_same_side_rate"])>=.80 and int(r["same_side"])>int(r["opposite"]) and float(r["wilson_lb95"])>=.60
        r["replication_pass"]=bool(ok); rows.append(r); okall=okall and bool(ok)
    for part in ("external","development","reference_validation"):
        audits.append(g1.analyze_geometry(x5,int(sel.clock_start_min_utc),int(sel.reference_min),int(sel.execution_min),part,True)[SIDE])
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),okall


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    D=scan_dev(x5); D2,C=leaderboard(D)
    D2.to_csv(OUT_DEV,index=False); C.to_csv(OUT_LEADER,index=False)
    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_G2_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status+"\n")
        OUT_RESULT.write_text(f"# ETH Discovery 2 Reset — G2 Geometry Refinement Result\n\nCoverage **{coverage:.4%}**.\n\nNo Development candidate passed preregistered gates.\n\n**Status: {status}**\n")
        print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]
    H,A,rep=replicate(x5,sel)
    H.to_csv(OUT_OOS,index=False); A.to_csv(OUT_AUDIT,index=False)
    boundary=(int(sel.clock_start_min_utc) in (min(CLOCKS),max(CLOCKS)) or int(sel.reference_min) in (min(REFS),max(REFS)) or int(sel.execution_min) in (min(EXES),max(EXES)))
    if not rep: status="ETH_DISCOVERY2_RESET_G2_CANDIDATE_NOT_REPLICATED"
    elif boundary: status="ETH_DISCOVERY2_RESET_G2_SUPPORTED_BUT_BOUNDARY_UNRESOLVED"
    else: status="ETH_DISCOVERY2_RESET_G2_SUPPORTED_AND_LOCALIZED"
    OUT_STATUS.write_text(status+"\n")
    lines=["# ETH Discovery 2 Reset — G2 Geometry Refinement Result","",f"Coverage **{coverage:.4%}**.","","## Development winner","",f"**LONG / ref start {g1.hhmm(int(sel.clock_start_min_utc))} UTC ({g1.wib(int(sel.clock_start_min_utc))} WIB) / ref {int(sel.reference_min)}m / execution {int(sel.execution_min)}m**","",f"Execution starts {g1.hhmm(int(sel.clock_start_min_utc)+int(sel.reference_min))} UTC ({g1.wib(int(sel.clock_start_min_utc)+int(sel.reference_min))} WIB).",f"Signals **{int(sel.signals)}**; continuation **{pct(sel.continuation_rate)}**; resolved **{pct(sel.resolved_same_side_rate)}**; Wilson **{pct(sel.wilson_lb95)}**; median continuation **{float(sel.median_minutes_to_target):.0f}m**.",f"Neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; blocks **{int(sel.positive_blocks)}/4**; boundary **{'YES' if boundary else 'NO'}**.","","## Historical replication","","| Partition | Signals | Continuation | Resolved | Wilson | Same/Opp | Gate |","|---|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False): lines.append(f"| {r.partition} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.same_side)}/{int(r.opposite)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Clock UTC | Ref m | Exe m | Signals | Cont. | Resolved | Wilson | Neigh. | Blocks |","|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(15).iterrows(): lines.append(f"| {int(r.dev_rank)} | {g1.hhmm(int(r.clock_start_min_utc))} | {int(r.reference_min)} | {int(r.execution_min)} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","No previous Z2/Z3 structure or Z5 entry is promoted automatically."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
