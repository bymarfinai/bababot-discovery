#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A21_PATH = Path(__file__).resolve().parent / "sol_long_remaining_clocks_a21.py"
spec = importlib.util.spec_from_file_location("sol_a21", A21_PATH)
a21 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a21)
a20 = a21.a20; a17 = a21.a17; a2 = a21.a2

IN_ATLAS = ROOT / "SOL_LONG_VISIT_BREAK_A1_ATLAS.csv"
OUT_MD = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_Result.md"
OUT_DEV = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_TRADES.csv"
OUT_CELLS = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_CELLS.csv"
OUT_STATUS = ROOT / "SOL_LONG_ALT_VISIT_CLOCKS_A22_Status.txt"
SUPPORTED_CLOCKS=(3,15,18)
TESTED_HOURS={3,8,11,12,13,15,18}


def dist(h): return min(a17.clock_distance(int(h),s) for s in SUPPORTED_CLOCKS)


def derive_cells(atlas):
    base=atlas[atlas.dominant_visit.astype(int).isin([1,3]) & atlas.topology_supported.astype(bool)
               & (pd.to_numeric(atlas.same_dom_blocks,errors="coerce")>=4)
               & (pd.to_numeric(atlas.dominant_opportunity_n,errors="coerce")>=60)].copy()
    base["distance_to_supported"]=base.hour.astype(int).map(dist)
    base=base[(base.distance_to_supported>2)&(~base.hour.astype(int).isin(TESTED_HOURS))].copy()
    rows=[]; chosen=[]; rank_i=1
    for dom in (1,3):
        q=a17.rank_cells(base[base.dominant_visit.astype(int)==dom].copy())
        taken=0
        for _,r in q.iterrows():
            h=int(r.hour)
            if any(a17.clock_distance(h,int(x.hour))<=2 for x in chosen): continue
            ref=int(r.ref_min)
            ch=a17.parse_int_list(r.clock_support_hours)
            cq=atlas[(atlas.ref_min.astype(int)==ref)&atlas.hour.astype(int).isin(ch)&(atlas.dominant_visit.astype(int)==dom)].copy()
            rm=a17.parse_int_list(r.ref_support_mins)
            rq=atlas[(atlas.hour.astype(int)==h)&atlas.ref_min.astype(int).isin(rm)&(atlas.dominant_visit.astype(int)==dom)].copy()
            if cq.empty or rq.empty: continue
            crow=a17.rank_cells(cq).iloc[0]; rrow=a17.rank_cells(rq).iloc[0]
            rows.append({"candidate":f"A22_Z{rank_i}_V{dom}_R{ref}_H{h:02d}","anatomy_rank":rank_i,"dominant_visit":dom,
                         "ref_min":ref,"hour":h,"distance_to_supported":dist(h),"same_dom_blocks":int(r.same_dom_blocks),
                         "dominant_break_conversion":float(r.dominant_break_conversion),"dominant_median_extension_R":float(r.dominant_median_extension_R),
                         "clock_support_ref_min":int(crow.ref_min),"clock_support_hour":int(crow.hour),
                         "ref_support_ref_min":int(rrow.ref_min),"ref_support_hour":int(rrow.hour)})
            chosen.append(r); rank_i+=1; taken+=1
            if taken>=2: break
    return pd.DataFrame(rows)


def existing_windows(m):
    mature_parent,mature_h2,windows=a17.load_mature_windows()
    for part in ("development","external","reference_validation"):
        for ref,hour in ((420,3),(360,15)):
            q=a17.simulate_cell(m,part,ref,hour,f"EXISTING_{hour:02d}","EXISTING")
            for _,r in q.iterrows(): windows.append((part,pd.Timestamp(r.entry_ts),pd.Timestamp(r.exit_ts)))
    return mature_parent,mature_h2,windows


def main():
    atlas=pd.read_csv(IN_ATLAS); cells=derive_cells(atlas); cells.to_csv(OUT_CELLS,index=False)
    if cells.empty:
        status="SOL_LONG_ALT_VISIT_CLOCKS_A22_NO_CANDIDATES"
        for p in (OUT_DEV,OUT_OOS,OUT_TRADES): p.write_text("",encoding="utf-8")
        OUT_STATUS.write_text(status+"\n",encoding="utf-8"); OUT_MD.write_text(f"# SOL LONG Alternate-Visit Clock Habitats — A22 Result\n\n**Status: {status}**\n",encoding="utf-8"); print(status); return
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x); mature_parent,mature_h2,windows=existing_windows(m)
    dev_rows=[]; all_trades=[]
    for _,c in cells.iterrows():
        q=a17.simulate_cell(m,"development",c.ref_min,c.hour,c.candidate,"CANDIDATE"); all_trades.append(q)
        row=a17.dev_row(q,c.candidate,mature_parent,mature_h2,windows)
        row.update({"anatomy_rank":int(c.anatomy_rank),"dominant_visit":int(c.dominant_visit),"ref_min":int(c.ref_min),"hour":int(c.hour),"existing_overlap":a17.overlap_rate(q,"development",windows)})
        dev_rows.append(row)
    dev=pd.DataFrame(dev_rows); dev.to_csv(OUT_DEV,index=False); winner=a17.choose_winner(dev)
    oos_rows=[]
    if winner is not None:
        c=cells[cells.candidate==winner.candidate].iloc[0]
        tests=[("CANDIDATE",int(c.ref_min),int(c.hour)),("CLOCK_SUPPORT",int(c.clock_support_ref_min),int(c.clock_support_hour)),("REF_SUPPORT",int(c.ref_support_ref_min),int(c.ref_support_hour))]
        for role,ref,hour in tests:
            for part in ("external","reference_validation"):
                q=a17.simulate_cell(m,part,ref,hour,c.candidate,role); all_trades.append(q)
                oos_rows.append({"candidate":c.candidate,"role":role,"partition":part,"ref_min":ref,"hour":hour,**a17.stats(q,part)})
    oos=pd.DataFrame(oos_rows); oos.to_csv(OUT_OOS,index=False)
    if winner is None: status="SOL_LONG_ALT_VISIT_CLOCKS_A22_REJECTED_DEVELOPMENT"
    else:
        exact=oos[oos.role=="CANDIDATE"]; support=oos[oos.role!="CANDIDATE"]
        central_ok=bool(len(exact)==2 and (exact.net>0).all() and (exact.net_5bps>0).all() and (exact.pf>1).all() and (exact.pf_5bps>1).all())
        status="SOL_LONG_ALT_VISIT_CLOCKS_A22_SUPPORTED" if central_ok and int((support.net>0).sum())>=3 and int((support.net_5bps>0).sum())>=3 else "SOL_LONG_ALT_VISIT_CLOCKS_A22_REJECTED_OOS"
    trades=pd.concat([q for q in all_trades if q is not None and len(q)],ignore_index=True) if any(q is not None and len(q) for q in all_trades) else pd.DataFrame(); trades.to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG Alternate-Visit Clock Habitats — A22 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","","## Frozen candidates","","| Candidate | Dom visit | Ref | Clock | Stable blocks | Break conv | Median ext |","|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in cells.iterrows(): lines.append(f"| {r.candidate} | H{int(r.dominant_visit)} | {int(r.ref_min)}m | {int(r.hour):02d}:00 | {int(r.same_dom_blocks)}/6 | {a17.pct(r.dominant_break_conversion)} | {a17.fmt(r.dominant_median_extension_R,3)}R |")
    lines += ["","## Development","","| Candidate | N | PF | Net | 5bps PF | 5bps Net | Blocks raw/stress | Existing overlap | Pass |","|---|---:|---:|---:|---:|---:|---|---:|---|"]
    for _,r in dev.iterrows(): lines.append(f"| {r.candidate} | {int(r.n)} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {a17.pct(r.existing_overlap)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen winner: **{winner.candidate if winner is not None else 'NONE'}**.",""]
    if winner is not None:
        lines += ["## OOS","","| Role | Partition | Cell | PF | Net | 5bps PF | 5bps Net |","|---|---|---|---:|---:|---:|---:|"]
        for _,r in oos.iterrows(): lines.append(f"| {r.role} | {r.partition} | R{int(r.ref_min)}/{int(r.hour):02d} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)

if __name__=="__main__": main()
