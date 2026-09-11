#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
PFX="ETH_E15A_LONG_MAX6H_24H_PARALLEL"
OUT_HOURS=ROOT/f"{PFX}_HourSummary.csv"
OUT_PASSERS=ROOT/f"{PFX}_FormalPassers.csv"
OUT_RESULT=ROOT/f"{PFX}_Result.md"
OUT_STATUS=ROOT/f"{PFX}_Status.txt"

def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"

def main():
    sums=[]; passers=[]
    for h in range(24):
        sf=ROOT/f"ETH_E15A_H{h:02d}_Summary.csv"
        pf=ROOT/f"ETH_E15A_H{h:02d}_Passers.csv"
        if not sf.exists(): raise FileNotFoundError(sf)
        sums.append(pd.read_csv(sf))
        if pf.exists() and pf.stat().st_size>0:
            try:
                p=pd.read_csv(pf)
                if len(p): passers.append(p)
            except pd.errors.EmptyDataError: pass
    H=pd.concat(sums,ignore_index=True).sort_values("hour_wib").reset_index(drop=True)
    P=pd.concat(passers,ignore_index=True) if passers else pd.DataFrame()
    H.to_csv(OUT_HOURS,index=False); P.to_csv(OUT_PASSERS,index=False)
    ph=H[H.formal_status=="PASS"]
    status="ETH_E15A_MAX6H_CHARACTER_MAP_FOUND" if len(ph) else "ETH_E15A_NO_MAX6H_FORMAL_PASS_HOURS"
    OUT_STATUS.write_text(status+"\n")
    lines=["# ETH E15A — 24H LONG Character Rediscovery, Max Hold 6h","",
           "Development only; OOS remained closed.",
           "LONG only; holds 60/120/240/360m; exact E12 rule grammar and gates.",
           "Search: **24 x 2,160 = 51,840 candidates**.",
           f"Formal PASS hours: **{len(ph)}/24**; total full-gate candidates: **{len(P)}**.","",
           "| WIB | Status | Passers | Character | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Anchors | Min-year exp | Y>=55 |",
           "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {int(r.hour_wib):02d} | {r.formal_status} | {int(r.full_gate_passers)} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {money(r.min_year_exp)} | {int(r.years_wr55)}/3 |")
    lines += ["","## Formal PASS detail",""]
    if len(ph)==0: lines.append("No full-gate PASS hour under max-6h search.")
    else:
        for r in ph.itertuples(index=False):
            lines += [f"### {int(r.hour_wib):02d}:00–{(int(r.hour_wib)+1)%24:02d}:00 WIB",
                      f"- {r.character_rule} / LB{int(r.lookback_min)} / H{int(r.hold_min)}",
                      f"- N {int(r.trades)}, WR {pct(r.win_rate)}, net {money(r.net_pnl)}, exp {money(r.expectancy)}, PF {float(r.pf):.3f}, DD {money(r.max_dd)}, LS {int(r.max_loss_streak)}",
                      f"- 2022 {pct(r.y2022_wr)}/{money(r.y2022_exp)}; 2023 {pct(r.y2023_wr)}/{money(r.y2023_exp)}; 2024 {pct(r.y2024_wr)}/{money(r.y2024_exp)}",""]
    lines += ["## Status","",f"**{status}**","","Research/shadow only. No OOS exposure and no live authorization."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())
if __name__=="__main__": main()
