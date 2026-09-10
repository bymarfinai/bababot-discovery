#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_reset_g1_geometry as g1
import eth_discovery2_reset_g3_temporal_decomposition as g3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_S1_AUCTION_REPAIR"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedSessionAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR = pd.Timedelta(minutes=5)
DEPTHS = ("D00_LEAVE","D02_CLOSE","D05_CLOSE","D10_CLOSE","D15_CLOSE")
DEPTH_FRAC = {"D00_LEAVE":None,"D02_CLOSE":.02,"D05_CLOSE":.05,"D10_CLOSE":.10,"D15_CLOSE":.15}
WAITS = (30,60,90,120)
PARTS = ("development","external","reference_validation")


def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def source_signals(x5, part):
    A = g3.analyze_candidate(x5, part, 120, 240, True).copy()
    A = A[A.signal.astype(bool)].sort_values("signal_ts").reset_index(drop=True)
    return A


def evaluate_one(x5, r, depth_mode: str, wait_min: int):
    H,L,R = float(r.H),float(r.L),float(r.R)
    sig = pd.Timestamp(r.signal_ts)
    max_trigger = sig + pd.Timedelta(minutes=wait_min)
    g3_end = sig + pd.Timedelta(minutes=240)
    path = base.fast_slice(x5, sig, min(max_trigger, g3_end))
    rejected = False
    rejection_ts = pd.NaT
    rejection_bar = pd.NaT
    trigger_ts = pd.NaT
    trigger_bar = pd.NaT
    absent_reason = "NO_REJECTION_OR_RETEST"

    frac = DEPTH_FRAC[depth_mode]
    for ts,b in path.iterrows():
        hi,lo,cl = float(b.high),float(b.low),float(b.close)
        hit_hi = hi >= H and cl <= H and cl >= L
        hit_lo = lo <= L and cl >= L and cl <= H
        if cl > H:
            absent_reason = "DIRECT_BREAK_BEFORE_TRIGGER"
            break
        if cl < L:
            absent_reason = "INVALIDATED_BEFORE_TRIGGER"
            break
        if hit_hi and hit_lo:
            absent_reason = "AMBIGUOUS_BEFORE_TRIGGER"
            break

        if not rejected:
            if depth_mode == "D00_LEAVE":
                cond = hi < H and L <= cl <= H
            else:
                cond = cl <= H - float(frac)*R and cl >= L
            if cond:
                rejected = True
                rejection_bar = ts
                rejection_ts = ts + BAR
                continue
        else:
            # causal order: retest must be on a later raw bar than rejection bar
            if ts <= rejection_bar:
                continue
            if hit_hi:
                trigger_bar = ts
                trigger_ts = ts + BAR
                absent_reason = ""
                break

    available = pd.notna(trigger_ts)
    terminal = "NO_TRIGGER"
    terminal_ts = pd.NaT
    minutes_trigger_to_target = np.nan
    if available:
        outcome = base.fast_slice(x5, trigger_ts, g3_end)
        terminal = "NO_BREAK"
        for ts,b in outcome.iterrows():
            hi,lo,cl = float(b.high),float(b.low),float(b.close)
            if cl > H:
                terminal = "SAME_SIDE"
                terminal_ts = ts + BAR
                minutes_trigger_to_target = float((terminal_ts-trigger_ts)/pd.Timedelta(minutes=1))
                break
            if cl < L:
                terminal = "OPPOSITE"
                terminal_ts = ts + BAR
                break
            hit_hi = hi >= H and cl <= H and cl >= L
            hit_lo = lo <= L and cl >= L and cl <= H
            if hit_hi and hit_lo:
                terminal = "AMBIGUOUS"
                terminal_ts = ts + BAR
                break

    return {
        "depth_mode":depth_mode,"wait_min":wait_min,
        "available":bool(available),"absent_reason":absent_reason,
        "rejection_bar":rejection_bar,"rejection_ts":rejection_ts,
        "trigger_bar":trigger_bar,"trigger_ts":trigger_ts,
        "signal_to_rejection_min":float((rejection_ts-sig)/pd.Timedelta(minutes=1)) if pd.notna(rejection_ts) else np.nan,
        "rejection_to_retest_min":float((trigger_ts-rejection_ts)/pd.Timedelta(minutes=1)) if available else np.nan,
        "terminal":terminal,"terminal_ts":terminal_ts,
        "trigger_to_target_min":minutes_trigger_to_target,
    }


def build_candidate_audit(x5, part, depth_mode, wait_min):
    S = source_signals(x5,part)
    rows=[]
    for r in S.itertuples(index=False):
        z=evaluate_one(x5,r,depth_mode,wait_min)
        rows.append({
            "partition":part,"reference_start":r.reference_start,"signal_ts":r.signal_ts,
            "H":r.H,"L":r.L,"R":r.R,"g3_terminal":r.terminal,
            **z,
        })
    return pd.DataFrame(rows)


def summarize(A, part, depth_mode, wait_min):
    source_n=len(A)
    q=A[A.available.astype(bool)].copy()
    n=len(q)
    same=int((q.terminal=="SAME_SIDE").sum()) if n else 0
    opp=int((q.terminal=="OPPOSITE").sum()) if n else 0
    amb=int((q.terminal=="AMBIGUOUS").sum()) if n else 0
    nb=int((q.terminal=="NO_BREAK").sum()) if n else 0
    row={
        "partition":part,"depth_mode":depth_mode,"wait_min":wait_min,
        "source_signals":source_n,"triggers":n,"participation":n/source_n if source_n else np.nan,
        "same_side":same,"opposite":opp,"ambiguous":amb,"no_break":nb,
        "continuation_rate":same/n if n else np.nan,
        "resolved_same_side_rate":same/(same+opp) if same+opp else np.nan,
        "wilson_lb95":g1.wilson_lb(same,n),
        "median_signal_to_rejection_min":pd.to_numeric(q.signal_to_rejection_min,errors="coerce").median() if n else np.nan,
        "median_rejection_to_retest_min":pd.to_numeric(q.rejection_to_retest_min,errors="coerce").median() if n else np.nan,
        "median_trigger_to_target_min":pd.to_numeric(q.loc[q.terminal=="SAME_SIDE","trigger_to_target_min"],errors="coerce").median() if same else np.nan,
    }
    if part=="development":
        chunks=np.array_split(np.arange(source_n),4)
        pos=0; qcont=[]
        for i,ix in enumerate(chunks,1):
            z=A.iloc[ix]; t=z[z.available.astype(bool)]
            bn=len(t); bs=int((t.terminal=="SAME_SIDE").sum()); bo=int((t.terminal=="OPPOSITE").sum())
            cont=bs/bn if bn else np.nan; res=bs/(bs+bo) if bs+bo else np.nan
            part_rate=bn/len(z) if len(z) else np.nan
            row[f"block{i}_n"]=bn; row[f"block{i}_participation"]=part_rate
            row[f"block{i}_cont"]=cont; row[f"block{i}_resolved"]=res
            if bn>=7:
                qcont.append(cont)
                if cont>=.70 and res>=.80: pos+=1
        row["positive_blocks"]=pos
        row["min_qualified_block_cont"]=min(qcont) if qcont else np.nan
    return row


def dev_grid(x5):
    rows=[]; audits={}
    for d in DEPTHS:
        for w in WAITS:
            A=build_candidate_audit(x5,"development",d,w)
            audits[(d,w)]=A
            rows.append(summarize(A,"development",d,w))
    return pd.DataFrame(rows),audits


def neighbor_keys(r):
    d=r.depth_mode; w=int(r.wait_min); out=[]
    di=DEPTHS.index(d); wi=WAITS.index(w)
    if di>0: out.append((DEPTHS[di-1],w))
    if di<len(DEPTHS)-1: out.append((DEPTHS[di+1],w))
    if wi>0: out.append((d,WAITS[wi-1]))
    if wi<len(WAITS)-1: out.append((d,WAITS[wi+1]))
    return out


def leaderboard(D):
    D=D.copy()
    D["dev_gate"]=(D.triggers>=35)&(D.participation>=.28)&(D.continuation_rate>=.78)&(D.resolved_same_side_rate>=.86)&(D.wilson_lb95>=.65)&(D.positive_blocks>=3)
    lookup={(r.depth_mode,int(r.wait_min)):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        ks=neighbor_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            if int(x.triggers)>=28 and float(x.participation)>=.22 and float(x.continuation_rate)>=.72 and float(x.resolved_same_side_rate)>=.82:
                sup += 1
        need=1 if len(ks)<=2 else max(2,math.ceil(.60*len(ks)))
        nav.append(len(ks)); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.dev_gate&D.local_stable
    D["depth_tie"]=D.depth_mode.map({d:i for i,d in enumerate(DEPTHS)})
    C=D[D.candidate_eligible].copy().sort_values(
        ["wilson_lb95","min_qualified_block_cont","continuation_rate","resolved_same_side_rate","participation","triggers","wait_min","depth_tie"],
        ascending=[False,False,False,False,False,False,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def replicate(x5,sel):
    rows=[]; audits=[]; allok=True
    for part in ("external","reference_validation"):
        A=build_candidate_audit(x5,part,sel.depth_mode,int(sel.wait_min))
        r=summarize(A,part,sel.depth_mode,int(sel.wait_min))
        ok=int(r["triggers"])>=18 and float(r["participation"])>=.22 and float(r["continuation_rate"])>=.70 and float(r["resolved_same_side_rate"])>=.80 and int(r["same_side"])>int(r["opposite"]) and float(r["wilson_lb95"])>=.52
        r["replication_pass"]=bool(ok); rows.append(r); audits.append(A); allok=allok and bool(ok)
    audits.insert(1,build_candidate_audit(x5,"development",sel.depth_mode,int(sel.wait_min)))
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),allok


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    D,_=dev_grid(x5); D2,C=leaderboard(D); D2.to_csv(OUT_DEV,index=False); C.to_csv(OUT_LEADER,index=False)
    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_S1_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        lines=["# ETH Discovery 2 Reset — S1 Auction-Repair Result","",f"Coverage **{coverage:.4%}**.","Tested 20 preregistered rejection/retest structures on the frozen G3 parent.","","No candidate passed Development + local-stability gates.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]; H,A,supported=replicate(x5,sel); H.to_csv(OUT_OOS,index=False); A.to_csv(OUT_AUDIT,index=False)
    status="ETH_DISCOVERY2_RESET_S1_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_S1_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines=["# ETH Discovery 2 Reset — S1 Auction-Repair Result","",f"Coverage **{coverage:.4%}**.","Tested 20 preregistered rejection/retest structures. Old Z2/Z3 coordinates were not used.","","## Development winner","",f"**{sel.depth_mode} / max retest wait {int(sel.wait_min)}m**",f"Triggers **{int(sel.triggers)}/{int(sel.source_signals)} ({pct(sel.participation)})**; continuation **{pct(sel.continuation_rate)}**; resolved **{pct(sel.resolved_same_side_rate)}**; Wilson **{pct(sel.wilson_lb95)}**.",f"Median signal→rejection **{float(sel.median_signal_to_rejection_min):.0f}m**; rejection→retest **{float(sel.median_rejection_to_retest_min):.0f}m**; trigger→continuation **{float(sel.median_trigger_to_target_min):.0f}m**.",f"Neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; blocks **{int(sel.positive_blocks)}/4**.","","## Historical replication","","| Partition | Triggers/source | Part. | Continuation | Resolved | Wilson | Same/Opp | Gate |","|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False): lines.append(f"| {r.partition} | {int(r.triggers)}/{int(r.source_signals)} | {pct(r.participation)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.same_side)}/{int(r.opposite)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Depth | Wait | Triggers | Part. | Cont. | Resolved | Wilson | Neigh. | Blocks |","|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(12).iterrows(): lines.append(f"| {int(r.dev_rank)} | {r.depth_mode} | {int(r.wait_min)} | {int(r.triggers)} | {pct(r.participation)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","SUPPORTED authorizes entry discovery around this causal trigger only. No TP/SL/economics yet."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
