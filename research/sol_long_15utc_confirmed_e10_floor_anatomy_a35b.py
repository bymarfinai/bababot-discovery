#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "SOL_LONG_15UTC_CONFIRMED_RETEST_ANATOMY_A35_COHORT.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_ANATOMY_A35B_Result.md"
OUT_SUM = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_ANATOMY_A35B_SUMMARY.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_ANATOMY_A35B_Status.txt"


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def main():
    t = pd.read_csv(IN)
    t["eventual_E40"] = t.eventual_E40.astype(bool)
    t["e10_close_violation"] = pd.to_numeric(t.min_close_R, errors="coerce") <= 0.10
    rows = []
    for (role, part), q in t.groupby(["role", "partition"], sort=False):
        w = q[q.eventual_E40]
        f = q[~q.eventual_E40]
        rows.append({
            "role": role, "partition": part, "n": len(q),
            "winner_n": len(w), "failure_n": len(f),
            "winner_e10_close_violation": float(w.e10_close_violation.mean()) if len(w) else None,
            "failure_e10_close_violation": float(f.e10_close_violation.mean()) if len(f) else None,
            "gap_failure_minus_winner": (float(f.e10_close_violation.mean()) - float(w.e10_close_violation.mean())) if len(w) and len(f) else None,
            "winner_median_min_close_R": float(pd.to_numeric(w.min_close_R, errors="coerce").median()) if len(w) else None,
            "failure_median_min_close_R": float(pd.to_numeric(f.min_close_R, errors="coerce").median()) if len(f) else None,
        })
    s = pd.DataFrame(rows); s.to_csv(OUT_SUM, index=False)
    cd = s[(s.role=="CENTRAL") & (s.partition=="development")]
    ce = s[(s.role=="CENTRAL") & (s.partition=="external")]
    cr = s[(s.role=="CENTRAL") & (s.partition=="reference_validation")]
    sup = s[(s.role!="CENTRAL") & s.partition.isin(["external","reference_validation"])]
    supported = False; reason = "Required cohorts missing"
    if len(cd)==len(ce)==len(cr)==1:
        d,e,r = cd.iloc[0], ce.iloc[0], cr.iloc[0]
        sp = int((pd.to_numeric(sup.gap_failure_minus_winner, errors="coerce") > 0).sum())
        supported = bool(int(d.winner_n)>=10 and float(d.winner_e10_close_violation)<=0.20 and float(d.failure_e10_close_violation)>=0.50 and float(e.gap_failure_minus_winner)>0 and float(r.gap_failure_minus_winner)>0 and sp>=3)
        reason = f"Dev winner violation={pct(d.winner_e10_close_violation)}, failure violation={pct(d.failure_e10_close_violation)}; Central OOS gaps={pct(e.gap_failure_minus_winner)}/{pct(r.gap_failure_minus_winner)}; support positive gaps={sp}/4"
    status = "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A35B_SUPPORTED_FOR_A36" if supported else "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A35B_INCONCLUSIVE"
    lines = ["# SOL LONG 15:00 UTC Confirmed E10 Close-Floor Anatomy — A35B Result","", "Exact A35 DC10_C12 confirmed cohort; anatomy only.","", "| Role | Partition | N | Winners | Failures | Winner close<=E10 | Failure close<=E10 | Gap | Winner median min close | Failure median min close |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,z in s.iterrows():
        lines.append(f"| {z.role} | {z.partition} | {int(z.n)} | {int(z.winner_n)} | {int(z.failure_n)} | {pct(z.winner_e10_close_violation)} | {pct(z.failure_e10_close_violation)} | {pct(z.gap_failure_minus_winner)} | {z.winner_median_min_close_R:.3f}R | {z.failure_median_min_close_R:.3f}R |")
    lines += ["", "## Decision", "", f"- {reason}.", "", f"**Status: {status}**", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n", encoding="utf-8"); OUT_STATUS.write_text(status+"\n", encoding="utf-8"); print(status)

if __name__ == "__main__": main()
