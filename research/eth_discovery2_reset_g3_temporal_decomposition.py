#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_reset_g1_geometry as g1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G3_TEMPORAL_DECOMPOSITION"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedSessionAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

REF_START_MIN = 60
REF_MIN = 150
ACQS = (120,180,240,300,360,420,480)
FOLLOWS = (60,90,120,180,240,300)
BAR = pd.Timedelta(minutes=5)


def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def sessions_for(part: str, acq: int, follow: int):
    anchors=pd.date_range(base.START.normalize(),base.END.normalize(),freq="D",tz="UTC")
    rs=anchors+pd.Timedelta(minutes=REF_START_MIN)
    re=rs+pd.Timedelta(minutes=REF_MIN)
    max_end=re+pd.Timedelta(minutes=acq+follow)
    pa,pz=base.PARTS[part]
    keep=np.array([x.weekday()<5 for x in re],dtype=bool)
    keep &= np.array([(a>=pa and z<=pz) for a,z in zip(rs,max_end)],dtype=bool)
    return pd.DataFrame({"rs":rs[keep],"re":re[keep],"max_end":max_end[keep]})


def analyze_candidate(x5: pd.DataFrame, part: str, acq: int, follow: int, return_audit=False):
    ss=sessions_for(part,acq,follow)
    rows=[]
    for r in ss.itertuples(index=False):
        ref=base.fast_slice(x5,r.rs,r.re)
        acq_end=r.re+pd.Timedelta(minutes=acq)
        acquisition=base.fast_slice(x5,r.re,acq_end)
        if len(ref)!=REF_MIN//5 or len(acquisition)!=acq//5:
            continue
        H=float(ref.high.max()); L=float(ref.low.min()); R=H-L
        if not H>L: continue
        signal_ts=pd.NaT
        signal_bar_start=pd.NaT
        low_seen=False
        terminal_pre="NO_SIGNAL"
        for ts,b in acquisition.iterrows():
            hi,lo,cl=float(b.high),float(b.low),float(b.close)
            if cl>H or cl<L:
                terminal_pre="PRE_SIGNAL_BREAK"
                break
            hit_hi=hi>=H and cl<=H
            hit_lo=lo<=L and cl>=L
            if hit_hi and hit_lo:
                terminal_pre="AMBIGUOUS_PRE_SIGNAL"
                break
            if hit_lo:
                low_seen=True
                terminal_pre="LOW_FIRST"
                break
            if hit_hi and not low_seen:
                signal_bar_start=ts
                signal_ts=ts+BAR
                terminal_pre="SIGNAL"
                break
        terminal="NO_SIGNAL"; terminal_ts=pd.NaT; mins_to_target=np.nan
        if pd.notna(signal_ts):
            f_end=signal_ts+pd.Timedelta(minutes=follow)
            path=base.fast_slice(x5,signal_ts,f_end)
            if len(path)!=follow//5:
                continue
            terminal="NO_BREAK"
            for ts,b in path.iterrows():
                hi,lo,cl=float(b.high),float(b.low),float(b.close)
                if cl>H:
                    terminal="SAME_SIDE"; terminal_ts=ts+BAR
                    mins_to_target=float((terminal_ts-signal_ts)/pd.Timedelta(minutes=1)); break
                if cl<L:
                    terminal="OPPOSITE"; terminal_ts=ts+BAR; break
                hit_hi=hi>=H and cl<=H
                hit_lo=lo<=L and cl>=L
                if hit_hi and hit_lo:
                    terminal="AMBIGUOUS"; terminal_ts=ts+BAR; break
        rows.append({
            "partition":part,"acquisition_min":acq,"follow_min":follow,
            "reference_start":r.rs,"acquisition_start":r.re,"H":H,"L":L,"R":R,
            "signal":pd.notna(signal_ts),"signal_bar_start":signal_bar_start,"signal_ts":signal_ts,
            "signal_delay_min":float((signal_ts-r.re)/pd.Timedelta(minutes=1)) if pd.notna(signal_ts) else np.nan,
            "pre_signal_state":terminal_pre,"terminal":terminal,"terminal_ts":terminal_ts,
            "minutes_to_target":mins_to_target,
        })
    A=pd.DataFrame(rows)
    if return_audit: return A
    return summarize(A,part,acq,follow)


def summarize(A,part,acq,follow):
    if len(A)==0:
        return {"partition":part,"acquisition_min":acq,"follow_min":follow,"complete_sessions":0,"signals":0}
    q=A[A.signal.astype(bool)].copy(); n=len(q)
    same=int((q.terminal=="SAME_SIDE").sum()); opp=int((q.terminal=="OPPOSITE").sum())
    amb=int((q.terminal=="AMBIGUOUS").sum()); nb=int((q.terminal=="NO_BREAK").sum())
    row={
        "partition":part,"acquisition_min":acq,"follow_min":follow,"complete_sessions":len(A),
        "signals":n,"signal_rate":n/len(A) if len(A) else np.nan,
        "same_side":same,"opposite":opp,"ambiguous":amb,"no_break":nb,
        "continuation_rate":same/n if n else np.nan,
        "resolved_same_side_rate":same/(same+opp) if same+opp else np.nan,
        "wilson_lb95":g1.wilson_lb(same,n),
        "median_signal_delay_min":pd.to_numeric(q.signal_delay_min,errors="coerce").median() if n else np.nan,
        "median_minutes_to_target":pd.to_numeric(q.loc[q.terminal=="SAME_SIDE","minutes_to_target"],errors="coerce").median() if same else np.nan,
    }
    pos=0; qual=[]
    if part=="development":
        chunks=np.array_split(np.arange(len(A)),4)
        for i,ix in enumerate(chunks,1):
            z=A.iloc[ix]; s=z[z.signal.astype(bool)]
            bn=len(s); bt=int((s.terminal=="SAME_SIDE").sum()); bo=int((s.terminal=="OPPOSITE").sum())
            cont=bt/bn if bn else np.nan; res=bt/(bt+bo) if bt+bo else np.nan
            row[f"block{i}_n"]=bn; row[f"block{i}_cont"]=cont; row[f"block{i}_resolved"]=res
            if bn>=15:
                qual.append(cont)
                if cont>=.65 and res>=.75: pos+=1
        row["positive_blocks"]=pos
        row["min_qualified_block_cont"]=min(qual) if qual else np.nan
    return row


def dev_grid(x5):
    rows=[]
    for a in ACQS:
        for f in FOLLOWS:
            rows.append(analyze_candidate(x5,"development",a,f,False))
    return pd.DataFrame(rows)


def neighbor_keys(r):
    a=int(r.acquisition_min); f=int(r.follow_min); out=[]
    if a-60 in ACQS: out.append((a-60,f))
    if a+60 in ACQS: out.append((a+60,f))
    fi=FOLLOWS.index(f)
    if fi>0: out.append((a,FOLLOWS[fi-1]))
    if fi<len(FOLLOWS)-1: out.append((a,FOLLOWS[fi+1]))
    return out


def leaderboard(D):
    D=D.copy()
    D["dev_gate"]=(D.signals>=100)&(D.continuation_rate>=.70)&(D.resolved_same_side_rate>=.82)&(D.wilson_lb95>=.62)&(D.positive_blocks>=3)
    lookup={(int(r.acquisition_min),int(r.follow_min)):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; st=[]
    for r in D.itertuples(index=False):
        ks=neighbor_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            if int(x.signals)>=80 and float(x.continuation_rate)>=.66 and float(x.resolved_same_side_rate)>=.78: sup+=1
        need=max(2,math.ceil(.60*len(ks))) if ks else 99
        nav.append(len(ks)); ns.append(sup); st.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=st
    D["candidate_eligible"]=D.dev_gate&D.local_stable
    C=D[D.candidate_eligible].copy().sort_values(
        ["wilson_lb95","min_qualified_block_cont","continuation_rate","resolved_same_side_rate","signals","follow_min","acquisition_min"],
        ascending=[False,False,False,False,False,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def replicate(x5,sel):
    rows=[]; audits=[]; allok=True
    for part in ("external","reference_validation"):
        r=analyze_candidate(x5,part,int(sel.acquisition_min),int(sel.follow_min),False)
        ok=int(r["signals"])>=40 and float(r["continuation_rate"])>=.68 and float(r["resolved_same_side_rate"])>=.78 and int(r["same_side"])>int(r["opposite"]) and float(r["wilson_lb95"])>=.55
        r["replication_pass"]=bool(ok); rows.append(r); allok=allok and bool(ok)
    for part in ("external","development","reference_validation"):
        audits.append(analyze_candidate(x5,part,int(sel.acquisition_min),int(sel.follow_min),True))
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),allok


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    D=dev_grid(x5); D2,C=leaderboard(D); D2.to_csv(OUT_DEV,index=False); C.to_csv(OUT_LEADER,index=False)
    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_G3_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        OUT_RESULT.write_text(f"# ETH Discovery 2 Reset — G3 Temporal Decomposition Result\n\nCoverage **{coverage:.4%}**. No Development candidate passed.\n\n**Status: {status}**\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]; H,A,supported=replicate(x5,sel); H.to_csv(OUT_OOS,index=False); A.to_csv(OUT_AUDIT,index=False)
    status="ETH_DISCOVERY2_RESET_G3_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G3_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines=["# ETH Discovery 2 Reset — G3 Temporal Decomposition Result","",f"Coverage **{coverage:.4%}**.","","## Development winner","",f"**Acquisition {int(sel.acquisition_min)}m / follow-through {int(sel.follow_min)}m** on frozen LONG ref 01:00 UTC / 150m.",f"Signals **{int(sel.signals)}**; continuation **{pct(sel.continuation_rate)}**; resolved **{pct(sel.resolved_same_side_rate)}**; Wilson **{pct(sel.wilson_lb95)}**.",f"Median signal arrival **{float(sel.median_signal_delay_min):.0f}m**; median signal→target **{float(sel.median_minutes_to_target):.0f}m**; neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; blocks **{int(sel.positive_blocks)}/4**.","","## Historical replication","","| Partition | Signals | Cont. | Resolved | Wilson | Same/Opp | Gate |","|---|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False): lines.append(f"| {r.partition} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.same_side)}/{int(r.opposite)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Acquisition | Follow | Signals | Cont. | Resolved | Wilson | Signal med | Target med | Neigh. | Blocks |","|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(15).iterrows(): lines.append(f"| {int(r.dev_rank)} | {int(r.acquisition_min)} | {int(r.follow_min)} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {float(r.median_signal_delay_min):.0f} | {float(r.median_minutes_to_target):.0f} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","If supported, proceed to downstream structure-sequence discovery. Entry remains unfrozen."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
