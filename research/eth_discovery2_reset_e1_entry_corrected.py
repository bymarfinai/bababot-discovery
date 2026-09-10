#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_reset_e1_entry as m


def replicate_corrected(x5, sel):
    mode=str(sel["mode"]); wait=int(sel["wait_min"])
    rows=[]; audits=[]; allok=True
    for part in ("external","reference_validation"):
        A=m.build_audit(x5,part,mode,wait)
        r=m.summarize(A,part,mode,wait)
        ok=(
            int(r["fills"])>=30 and float(r["participation"])>=.45 and
            float(r["continuation_rate"])>=.68 and float(r["resolved_same_side_rate"])>=.78 and
            float(r["C10_reach_rate"])>=.48 and float(r["C20_reach_rate"])>=.32 and
            int(r["same_side"])>int(r["opposite"])
        )
        r["replication_pass"]=bool(ok); rows.append(r); audits.append(A); allok=allok and bool(ok)
    audits.insert(1,m.build_audit(x5,"development",mode,wait))
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),allok


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    D=m.dev_grid(x5); D2,C=m.leaderboard(D)
    D2.to_csv(m.OUT_DEV,index=False); C.to_csv(m.OUT_LEADER,index=False)
    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_E1_NO_DEV_CANDIDATE"; m.OUT_STATUS.write_text(status+"\n")
        m.OUT_RESULT.write_text(f"# ETH Discovery 2 Reset — E1 Pair-Native Entry Result\n\nCoverage **{coverage:.4%}**. Tested 13 causal entries; no Development candidate passed.\n\n**Status: {status}**\n")
        print(m.OUT_RESULT.read_text()); return
    sel=C.iloc[0]
    H,A,supported=replicate_corrected(x5,sel)
    H.to_csv(m.OUT_OOS,index=False); A.to_csv(m.OUT_AUDIT,index=False)
    status="ETH_DISCOVERY2_RESET_E1_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_E1_CANDIDATE_NOT_REPLICATED"
    m.OUT_STATUS.write_text(status+"\n")
    mode=str(sel["mode"]); wait=int(sel["wait_min"])
    label=mode if mode=="NEXT_OPEN" else f"{mode} / {wait}m"
    lines=["# ETH Discovery 2 Reset — E1 Pair-Native Entry Result","",f"Coverage **{coverage:.4%}**.","Old Z5 H+0.06R entry was not included.","","## Development winner","",f"**{label}**",f"Fills **{int(sel['fills'])}/{int(sel['source_signals'])} ({m.pct(sel['participation'])})**; continuation **{m.pct(sel['continuation_rate'])}**; resolved **{m.pct(sel['resolved_same_side_rate'])}**.",f"C10/C20/C30 = **{m.pct(sel['C10_reach_rate'])} / {m.pct(sel['C20_reach_rate'])} / {m.pct(sel['C30_reach_rate'])}**.",f"Median entry offset **{float(sel['median_entry_offset_R']):+.3f}R vs H**; median improvement vs NEXT_OPEN **{float(sel['median_entry_improvement_R']):.3f}R**; p90 adverse **{float(sel['p90_adverse_R']):.3f}R**.",f"Blocks **{int(sel['positive_blocks'])}/4**; neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**.","","## Historical replication","","| Partition | Fills/source | Part. | Cont. | Resolved | C10 | C20 | C30 | Entry offset | p90 adverse | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.fills)}/{int(r.source_signals)} | {m.pct(r.participation)} | {m.pct(r.continuation_rate)} | {m.pct(r.resolved_same_side_rate)} | {m.pct(r.C10_reach_rate)} | {m.pct(r.C20_reach_rate)} | {m.pct(r.C30_reach_rate)} | {float(r.median_entry_offset_R):+.3f}R | {float(r.p90_adverse_R):.3f}R | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Mode | Wait | Fills | Part. | Cont. | C20 | C30 | Offset R | p90 adverse | Blocks |","|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(13).iterrows():
        lines.append(f"| {int(r.dev_rank)} | {r['mode']} | {int(r.wait_min)} | {int(r.fills)} | {m.pct(r.participation)} | {m.pct(r.continuation_rate)} | {m.pct(r.C20_reach_rate)} | {m.pct(r.C30_reach_rate)} | {float(r.median_entry_offset_R):+.3f} | {float(r.p90_adverse_R):.3f} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","SUPPORTED authorizes a separate economics milestone. No TP/SL/PnL has been optimized here."]
    m.OUT_RESULT.write_text("\n".join(lines)+"\n"); print(m.OUT_RESULT.read_text())

if __name__=="__main__": main()
