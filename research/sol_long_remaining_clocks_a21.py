#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A20_PATH = Path(__file__).resolve().parent / "sol_long_additional_clocks_a20.py"
spec = importlib.util.spec_from_file_location("sol_a20", A20_PATH)
a20 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a20)
a17 = a20.a17
a2 = a20.a2

IN_ATLAS = ROOT / "SOL_LONG_VISIT_BREAK_A1_ATLAS.csv"
OUT_MD = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_Result.md"
OUT_DEV = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_TRADES.csv"
OUT_CELLS = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_CELLS.csv"
OUT_STATUS = ROOT / "SOL_LONG_REMAINING_CLOCKS_A21_Status.txt"
SUPPORTED_CLOCKS = (3, 15, 18)
ALREADY_TESTED_HOURS = {3, 8, 12, 13, 15, 18}


def dist(h):
    return min(a17.clock_distance(int(h), s) for s in SUPPORTED_CLOCKS)


def derive_cells(atlas):
    q = atlas[(pd.to_numeric(atlas.dominant_visit, errors="coerce") == 2)
              & atlas.topology_supported.astype(bool)
              & (pd.to_numeric(atlas.same_dom_blocks, errors="coerce") >= 4)
              & (pd.to_numeric(atlas.dominant_opportunity_n, errors="coerce") >= 100)].copy()
    q["distance_to_supported"] = q.hour.astype(int).map(dist)
    q = q[(q.distance_to_supported > 2) & (~q.hour.astype(int).isin(ALREADY_TESTED_HOURS))].copy()
    q = a17.rank_cells(q)
    chosen = []
    for _, r in q.iterrows():
        h = int(r.hour)
        if any(a17.clock_distance(h, int(x.hour)) <= 2 for x in chosen):
            continue
        chosen.append(r)
        if len(chosen) >= 4:
            break
    rows = []
    for rank_i, r in enumerate(chosen, 1):
        ref, hour, dom = int(r.ref_min), int(r.hour), int(r.dominant_visit)
        ch = a17.parse_int_list(r.clock_support_hours)
        cq = atlas[(atlas.ref_min.astype(int) == ref) & atlas.hour.astype(int).isin(ch) & (atlas.dominant_visit.astype(int) == dom)].copy()
        rm = a17.parse_int_list(r.ref_support_mins)
        rq = atlas[(atlas.hour.astype(int) == hour) & atlas.ref_min.astype(int).isin(rm) & (atlas.dominant_visit.astype(int) == dom)].copy()
        if cq.empty or rq.empty:
            continue
        crow, rrow = a17.rank_cells(cq).iloc[0], a17.rank_cells(rq).iloc[0]
        rows.append({"candidate": f"A21_Z{rank_i}_R{ref}_H{hour:02d}", "anatomy_rank": rank_i,
                     "ref_min": ref, "hour": hour, "distance_to_supported": dist(hour),
                     "same_dom_blocks": int(r.same_dom_blocks), "dominant_break_conversion": float(r.dominant_break_conversion),
                     "dominant_median_extension_R": float(r.dominant_median_extension_R),
                     "clock_support_ref_min": int(crow.ref_min), "clock_support_hour": int(crow.hour),
                     "ref_support_ref_min": int(rrow.ref_min), "ref_support_hour": int(rrow.hour)})
    return pd.DataFrame(rows)


def existing_windows(m):
    mature_parent, mature_h2, windows = a17.load_mature_windows()
    for part in ("development", "external", "reference_validation"):
        for ref, hour in ((420,3),(360,15)):
            q = a17.simulate_cell(m, part, ref, hour, f"EXISTING_{hour:02d}", "EXISTING")
            for _, r in q.iterrows():
                windows.append((part, pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)))
    return mature_parent, mature_h2, windows


def main():
    atlas = pd.read_csv(IN_ATLAS)
    cells = derive_cells(atlas)
    cells.to_csv(OUT_CELLS, index=False)
    if cells.empty:
        status = "SOL_LONG_REMAINING_CLOCKS_A21_EXHAUSTED_UNDER_H2_GRAMMAR"
        OUT_DEV.write_text("", encoding="utf-8")
        OUT_OOS.write_text("", encoding="utf-8")
        OUT_TRADES.write_text("", encoding="utf-8")
        OUT_STATUS.write_text(status + "\n", encoding="utf-8")
        OUT_MD.write_text(f"# SOL LONG Remaining Untouched Clocks — A21 Result\n\n**Status: {status}**\n\nNo additional untouched H2-dominant topology-supported clock remains after excluding supported/tested clusters. The hypothesis is not broadened post hoc.\n", encoding="utf-8")
        print(status)
        return

    x, coverage = a2.a1.load5(); m = a2.make_market_with_open(x)
    mature_parent, mature_h2, windows = existing_windows(m)
    dev_rows=[]; all_trades=[]
    for _, c in cells.iterrows():
        q=a17.simulate_cell(m,"development",c.ref_min,c.hour,c.candidate,"CANDIDATE"); all_trades.append(q)
        row=a17.dev_row(q,c.candidate,mature_parent,mature_h2,windows)
        row.update({"anatomy_rank":int(c.anatomy_rank),"ref_min":int(c.ref_min),"hour":int(c.hour),"existing_overlap":a17.overlap_rate(q,"development",windows)})
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
    if winner is None:
        status="SOL_LONG_REMAINING_CLOCKS_A21_REJECTED_DEVELOPMENT"
    else:
        exact=oos[oos.role=="CANDIDATE"]; support=oos[oos.role!="CANDIDATE"]
        central_ok=bool(len(exact)==2 and (exact.net>0).all() and (exact.net_5bps>0).all() and (exact.pf>1).all() and (exact.pf_5bps>1).all())
        status="SOL_LONG_REMAINING_CLOCKS_A21_SUPPORTED" if central_ok and int((support.net>0).sum())>=3 and int((support.net_5bps>0).sum())>=3 else "SOL_LONG_REMAINING_CLOCKS_A21_REJECTED_OOS"
    trades=pd.concat([q for q in all_trades if q is not None and len(q)],ignore_index=True) if any(q is not None and len(q) for q in all_trades) else pd.DataFrame(); trades.to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG Remaining Untouched Clocks — A21 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","","## Candidates","","| Candidate | Ref | Clock | Stable blocks | Break conv | Median ext |","|---|---:|---:|---:|---:|---:|"]
    for _,r in cells.iterrows(): lines.append(f"| {r.candidate} | {int(r.ref_min)}m | {int(r.hour):02d}:00 | {int(r.same_dom_blocks)}/6 | {a17.pct(r.dominant_break_conversion)} | {a17.fmt(r.dominant_median_extension_R,3)}R |")
    lines += ["","## Development","","| Candidate | N | PF | Net | 5bps PF | 5bps Net | Blocks raw/stress | Existing overlap | Pass |","|---|---:|---:|---:|---:|---:|---|---:|---|"]
    for _,r in dev.iterrows(): lines.append(f"| {r.candidate} | {int(r.n)} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {a17.pct(r.existing_overlap)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen winner: **{winner.candidate if winner is not None else 'NONE'}**.",""]
    if winner is not None:
        lines += ["## OOS","","| Role | Partition | Cell | PF | Net | 5bps PF | 5bps Net |","|---|---|---|---:|---:|---:|---:|"]
        for _,r in oos.iterrows(): lines.append(f"| {r.role} | {r.partition} | R{int(r.ref_min)}/{int(r.hour):02d} | {a17.fmt(r.pf)} | ${a17.fmt(r.net)} | {a17.fmt(r.pf_5bps)} | ${a17.fmt(r.net_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)

if __name__ == "__main__": main()
