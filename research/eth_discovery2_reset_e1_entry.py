#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_reset_g3_temporal_decomposition as g3

ROOT=Path(__file__).resolve().parent.parent
PFX="ETH_DISCOVERY2_RESET_E1_ENTRY"
OUT_DEV=ROOT/f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER=ROOT/f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS=ROOT/f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT=ROOT/f"{PFX}_SelectedEntryAudit.csv"
OUT_RESULT=ROOT/f"{PFX}_Result.md"
OUT_STATUS=ROOT/f"{PFX}_Status.txt"

BAR=pd.Timedelta(minutes=5)
LEVELS=("H00","M02","M05","M10","M15","M20")
LEVEL_FRAC={"H00":0.0,"M02":.02,"M05":.05,"M10":.10,"M15":.15,"M20":.20}
WAITS=(30,60)
CHECKS={"C10":.10,"C20":.20,"C30":.30}


def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.1f}%"

def source_signals(x5,part):
    A=g3.analyze_candidate(x5,part,120,240,True)
    return A[A.signal.astype(bool)].sort_values("signal_ts").reset_index(drop=True)


def next_open(x5,r):
    ts=pd.Timestamp(r.signal_ts)
    if ts not in x5.index: return None
    b=x5.loc[ts]
    return {"available":True,"entry_bar":ts,"entry_ts":ts,"entry_price":float(b.open),"intrabar":False,"pre_terminal":""}


def resting_fill(x5,r,level,wait):
    H,L,R=float(r.H),float(r.L),float(r.R)
    limit=H-LEVEL_FRAC[level]*R
    sig=pd.Timestamp(r.signal_ts); stop=sig+pd.Timedelta(minutes=wait)
    path=base.fast_slice(x5,sig,stop)
    for ts,b in path.iterrows():
        op,lo,cl=float(b.open),float(b.low),float(b.close)
        if op<=limit:
            pre="OPPOSITE" if cl<L else "SAME_SIDE" if cl>H else ""
            return {"available":True,"entry_bar":ts,"entry_ts":ts,"entry_price":op,"intrabar":False,"pre_terminal":pre,"limit_price":limit}
        if lo<=limit:
            pre="OPPOSITE" if cl<L else "SAME_SIDE" if cl>H else ""
            return {"available":True,"entry_bar":ts,"entry_ts":ts+BAR,"entry_price":limit,"intrabar":True,"pre_terminal":pre,"limit_price":limit}
        if cl>H:
            return {"available":False,"reason":"MISSED_DIRECT_BREAK","limit_price":limit}
        if cl<L:
            return {"available":False,"reason":"INVALIDATED_BEFORE_FILL","limit_price":limit}
    return {"available":False,"reason":"NO_FILL_WITHIN_WINDOW","limit_price":limit}


def evaluate_entry(x5,r,ent):
    H,L,R=float(r.H),float(r.L),float(r.R); ep=float(ent["entry_price"])
    sig=pd.Timestamp(r.signal_ts); end=sig+pd.Timedelta(minutes=240)
    start=pd.Timestamp(ent["entry_bar"]) if not ent.get("intrabar",False) else pd.Timestamp(ent["entry_bar"])+BAR
    pre=ent.get("pre_terminal","")
    terminal=pre if pre else "NO_BREAK"
    terminal_ts=(pd.Timestamp(ent["entry_bar"])+BAR) if pre else pd.NaT
    same_seen=(pre=="SAME_SIDE"); opp_seen=(pre=="OPPOSITE")
    check_hit={k:False for k in CHECKS}; check_ts={k:pd.NaT for k in CHECKS}
    max_hi=ep; min_lo=ep

    # Same-bar high diagnostics are safe only for open fills.
    if not ent.get("intrabar",False):
        b0=x5.loc[pd.Timestamp(ent["entry_bar"])]
        max_hi=max(max_hi,float(b0.high)); min_lo=min(min_lo,float(b0.low))
        for k,f in CHECKS.items():
            if float(b0.high)>=H+f*R:
                check_hit[k]=True; check_ts[k]=pd.Timestamp(ent["entry_bar"])+BAR

    invalidated=opp_seen
    path=base.fast_slice(x5,start,end)
    for ts,b in path.iterrows():
        # avoid double-counting open-fill entry bar
        if not ent.get("intrabar",False) and ts==pd.Timestamp(ent["entry_bar"]):
            continue
        hi,lo,cl=float(b.high),float(b.low),float(b.close)
        max_hi=max(max_hi,hi); min_lo=min(min_lo,lo)
        if not invalidated:
            for k,f in CHECKS.items():
                if not check_hit[k] and hi>=H+f*R:
                    check_hit[k]=True; check_ts[k]=ts+BAR
        if not same_seen and not opp_seen:
            if cl>H:
                same_seen=True; terminal="SAME_SIDE"; terminal_ts=ts+BAR
            elif cl<L:
                opp_seen=True; terminal="OPPOSITE"; terminal_ts=ts+BAR; invalidated=True
        elif cl<L and not invalidated:
            invalidated=True
        if invalidated:
            # no post-invalidation checkpoint/MFE/MAE credit
            break

    if terminal=="NO_BREAK" and same_seen: terminal="SAME_SIDE"
    offset=(ep-H)/R
    return {
        "terminal":terminal,"terminal_ts":terminal_ts,
        "entry_offset_R":offset,
        "C10_reached":check_hit["C10"],"C20_reached":check_hit["C20"],"C30_reached":check_hit["C30"],
        "C10_ts":check_ts["C10"],"C20_ts":check_ts["C20"],"C30_ts":check_ts["C30"],
        "adverse_R":max(0.0,(ep-min_lo)/R),
        "mfe_R":max(0.0,(max_hi-ep)/R),
        "entry_to_same_min":float((terminal_ts-pd.Timestamp(ent["entry_ts"]))/pd.Timedelta(minutes=1)) if terminal=="SAME_SIDE" and pd.notna(terminal_ts) else np.nan,
    }


def build_audit(x5,part,mode,wait=0):
    S=source_signals(x5,part)
    # same-session NEXT_OPEN prices for improvement comparator
    ctrl={}
    for r in S.itertuples(index=False):
        e=next_open(x5,r)
        if e: ctrl[pd.Timestamp(r.signal_ts)]=e["entry_price"]
    rows=[]
    for r in S.itertuples(index=False):
        if mode=="NEXT_OPEN": ent=next_open(x5,r)
        else: ent=resting_fill(x5,r,mode,wait)
        base_row={"partition":part,"mode":mode,"wait_min":wait,"reference_start":r.reference_start,"signal_ts":r.signal_ts,"H":r.H,"L":r.L,"R":r.R}
        if not ent or not ent.get("available",False):
            rows.append({**base_row,"available":False,"reason":ent.get("reason","") if ent else "NO_ENTRY"})
            continue
        ev=evaluate_entry(x5,r,ent)
        cpx=ctrl.get(pd.Timestamp(r.signal_ts),np.nan)
        improve=(cpx-float(ent["entry_price"]))/float(r.R) if np.isfinite(cpx) else np.nan
        rows.append({**base_row,**ent,**ev,"entry_improvement_R":improve,"reason":""})
    return pd.DataFrame(rows)


def summarize(A,part,mode,wait):
    source=len(A); q=A[A.available.astype(bool)].copy(); n=len(q)
    same=int((q.terminal=="SAME_SIDE").sum()) if n else 0
    opp=int((q.terminal=="OPPOSITE").sum()) if n else 0
    row={
        "partition":part,"mode":mode,"wait_min":wait,"source_signals":source,"fills":n,
        "participation":n/source if source else np.nan,
        "same_side":same,"opposite":opp,
        "continuation_rate":same/n if n else np.nan,
        "resolved_same_side_rate":same/(same+opp) if same+opp else np.nan,
        "C10_reach_rate":float(q.C10_reached.astype(bool).mean()) if n else np.nan,
        "C20_reach_rate":float(q.C20_reached.astype(bool).mean()) if n else np.nan,
        "C30_reach_rate":float(q.C30_reached.astype(bool).mean()) if n else np.nan,
        "median_entry_offset_R":pd.to_numeric(q.entry_offset_R,errors="coerce").median() if n else np.nan,
        "median_entry_improvement_R":pd.to_numeric(q.entry_improvement_R,errors="coerce").median() if n else np.nan,
        "p75_entry_improvement_R":pd.to_numeric(q.entry_improvement_R,errors="coerce").quantile(.75) if n else np.nan,
        "median_adverse_R":pd.to_numeric(q.adverse_R,errors="coerce").median() if n else np.nan,
        "p90_adverse_R":pd.to_numeric(q.adverse_R,errors="coerce").quantile(.90) if n else np.nan,
        "median_mfe_R":pd.to_numeric(q.mfe_R,errors="coerce").median() if n else np.nan,
        "median_entry_to_same_min":pd.to_numeric(q.entry_to_same_min,errors="coerce").median() if same else np.nan,
    }
    if part=="development":
        chunks=np.array_split(np.arange(source),4); pos=0; c20s=[]
        for i,ix in enumerate(chunks,1):
            z=A.iloc[ix]; t=z[z.available.astype(bool)]; bn=len(t)
            bs=int((t.terminal=="SAME_SIDE").sum()) if bn else 0
            cont=bs/bn if bn else np.nan
            c20=float(t.C20_reached.astype(bool).mean()) if bn else np.nan
            row[f"block{i}_fills"]=bn; row[f"block{i}_cont"]=cont; row[f"block{i}_c20"]=c20
            if bn>=12:
                c20s.append(c20)
                if cont>=.70 and c20>=.32: pos+=1
        row["positive_blocks"]=pos
        row["min_qualified_block_c20"]=min(c20s) if c20s else np.nan
    return row


def dev_grid(x5):
    specs=[("NEXT_OPEN",0)]+[(l,w) for l in LEVELS for w in WAITS]
    rows=[]
    for mode,w in specs:
        A=build_audit(x5,"development",mode,w); rows.append(summarize(A,"development",mode,w))
    return pd.DataFrame(rows)


def neighbor_keys(r):
    if r.mode=="NEXT_OPEN": return []
    li=LEVELS.index(r.mode); w=int(r.wait_min); out=[]
    if li>0: out.append((LEVELS[li-1],w))
    if li<len(LEVELS)-1: out.append((LEVELS[li+1],w))
    out.append((r.mode,60 if w==30 else 30))
    return out


def leaderboard(D):
    D=D.copy()
    D["dev_gate"]=(D.fills>=65)&(D.participation>=.52)&(D.continuation_rate>=.78)&(D.resolved_same_side_rate>=.86)&(D.C10_reach_rate>=.58)&(D.C20_reach_rate>=.42)&(D.same_side>D.opposite)&(D.positive_blocks>=3)
    lookup={(r.mode,int(r.wait_min)):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        if r.mode=="NEXT_OPEN":
            nav.append(0); ns.append(0); stable.append(True); continue
        ks=neighbor_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            if int(x.fills)>=55 and float(x.participation)>=.45 and float(x.continuation_rate)>=.72 and float(x.C20_reach_rate)>=.35:
                sup+=1
        need=max(1,math.ceil(.60*len(ks)))
        nav.append(len(ks)); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.dev_gate&D.local_stable
    D["level_tie"]=D["mode"].map({"NEXT_OPEN":99,**{x:i for i,x in enumerate(LEVELS)}})
    C=D[D.candidate_eligible].copy().sort_values(
        ["min_qualified_block_c20","C30_reach_rate","C20_reach_rate","continuation_rate","median_entry_offset_R","p90_adverse_R","participation","wait_min","level_tie"],
        ascending=[False,False,False,False,True,True,False,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def replicate(x5,sel):
    rows=[]; audits=[]; allok=True
    for part in ("external","reference_validation"):
        A=build_audit(x5,part,sel.mode,int(sel.wait_min)); r=summarize(A,part,sel.mode,int(sel.wait_min))
        ok=int(r["fills"])>=30 and float(r["participation"])>=.45 and float(r["continuation_rate"])>=.68 and float(r["resolved_same_side_rate"])>=.78 and float(r["C10_reach_rate"])>=.48 and float(r["C20_reach_rate"])>=.32 and int(r["same_side"])>int(r["opposite"])
        r["replication_pass"]=bool(ok); rows.append(r); audits.append(A); allok=allok and bool(ok)
    audits.insert(1,build_audit(x5,"development",sel.mode,int(sel.wait_min)))
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),allok


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    D=dev_grid(x5); D2,C=leaderboard(D); D2.to_csv(OUT_DEV,index=False); C.to_csv(OUT_LEADER,index=False)
    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_E1_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        OUT_RESULT.write_text(f"# ETH Discovery 2 Reset — E1 Pair-Native Entry Result\n\nCoverage **{coverage:.4%}**. Tested 13 causal entries; no Development candidate passed.\n\n**Status: {status}**\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]; H,A,supported=replicate(x5,sel); H.to_csv(OUT_OOS,index=False); A.to_csv(OUT_AUDIT,index=False)
    status="ETH_DISCOVERY2_RESET_E1_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_E1_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    label=sel.mode if sel.mode=="NEXT_OPEN" else f"{sel.mode} / {int(sel.wait_min)}m"
    lines=["# ETH Discovery 2 Reset — E1 Pair-Native Entry Result","",f"Coverage **{coverage:.4%}**.","Old Z5 H+0.06R entry was not included.","","## Development winner","",f"**{label}**",f"Fills **{int(sel.fills)}/{int(sel.source_signals)} ({pct(sel.participation)})**; continuation **{pct(sel.continuation_rate)}**; resolved **{pct(sel.resolved_same_side_rate)}**.",f"C10/C20/C30 = **{pct(sel.C10_reach_rate)} / {pct(sel.C20_reach_rate)} / {pct(sel.C30_reach_rate)}**.",f"Median entry offset **{float(sel.median_entry_offset_R):+.3f}R vs H**; median improvement vs NEXT_OPEN **{float(sel.median_entry_improvement_R):.3f}R**; p90 adverse **{float(sel.p90_adverse_R):.3f}R**.",f"Blocks **{int(sel.positive_blocks)}/4**; neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**.","","## Historical replication","","| Partition | Fills/source | Part. | Cont. | Resolved | C10 | C20 | C30 | Entry offset | p90 adverse | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False): lines.append(f"| {r.partition} | {int(r.fills)}/{int(r.source_signals)} | {pct(r.participation)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.C10_reach_rate)} | {pct(r.C20_reach_rate)} | {pct(r.C30_reach_rate)} | {float(r.median_entry_offset_R):+.3f}R | {float(r.p90_adverse_R):.3f}R | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Mode | Wait | Fills | Part. | Cont. | C20 | C30 | Offset R | p90 adverse | Blocks |","|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(13).iterrows(): lines.append(f"| {int(r.dev_rank)} | {r['mode']} | {int(r.wait_min)} | {int(r.fills)} | {pct(r.participation)} | {pct(r.continuation_rate)} | {pct(r.C20_reach_rate)} | {pct(r.C30_reach_rate)} | {float(r.median_entry_offset_R):+.3f} | {float(r.p90_adverse_R):.3f} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","SUPPORTED authorizes a separate economics milestone. No TP/SL/PnL has been optimized here."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
