#!/usr/bin/env python3
"""Stage 4C: high-location x OI x taker three-way checks."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s4 as s4

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4C_Result.md"
OUT_CSV = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4C_CELLS.csv"
OUT_JSON = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4C_Result.json"
OUT_STATUS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4C_Status.txt"

PARTS = ["development","validation_2025","validation_2026"]

def rate(s, x):
    return float((s == x).mean()) if len(s) else np.nan

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.1f}%"

def main():
    raw = s3.load_klines()
    metrics = s3.load_metrics()
    funding = s3.load_funding()
    a = s3.add_targets(s3.add_derivatives(s3.build_15m(raw), metrics, funding), raw)
    a = a[(a.decision_time >= s3.SCORE_START) & (a.decision_time < s3.END)].copy()

    specs = s4.build_specs(a)
    for f in ["loc_24h","oi_chg_15m","taker_imb_15m"]:
        a[f+"_bucket"] = [s4.bucket(v, specs[f]) for v in a[f]]

    a = a[a["loc_24h_bucket"] == "HIGH"].copy()

    definitions = [
        ("HIGHLOC_TAKERBUY_OI", "HIGH", "HIGH"),
        ("HIGHLOC_TAKERSELL_OI", "LOW", "LOW"),
    ]

    rows = []
    for name, taker_bucket, _ in definitions:
        for p in PARTS:
            for oi_bucket in ["HIGH","LOW"]:
                g = a[
                    (a.partition == p) &
                    (a["taker_imb_15m_bucket"] == taker_bucket) &
                    (a["oi_chg_15m_bucket"] == oi_bucket) &
                    a.target_1pct_4h.notna()
                ]
                lr = rate(g.target_1pct_4h, "LONG")
                sr = rate(g.target_1pct_4h, "SHORT")
                rows.append({
                    "contrast":name,
                    "partition":p,
                    "location":"HIGH",
                    "taker_bucket":taker_bucket,
                    "oi_bucket":oi_bucket,
                    "n":len(g),
                    "long_rate":lr,
                    "short_rate":sr,
                    "D":lr-sr if len(g) else np.nan,
                    "none_rate":rate(g.target_1pct_4h,"NONE"),
                    "ambiguous_rate":rate(g.target_1pct_4h,"AMBIGUOUS"),
                    "median_fwd_ret_4h":float(g.fwd_ret_4h.median()) if len(g) else np.nan,
                    "median_max_up_4h":float(g.max_up_4h.median()) if len(g) else np.nan,
                    "median_max_down_4h":float(g.max_down_4h.median()) if len(g) else np.nan,
                })
    cells = pd.DataFrame(rows)
    cells.to_csv(OUT_CSV,index=False)

    summaries=[]
    for name in cells.contrast.unique():
        row={"contrast":name}
        pass_n=True
        vals=[]
        signs=[]
        for p in PARTS:
            q=cells[(cells.contrast==name)&(cells.partition==p)]
            hi=q[q.oi_bucket=="HIGH"].iloc[0]
            lo=q[q.oi_bucket=="LOW"].iloc[0]
            d=float(hi.D-lo.D)
            row[f"{p}_high_n"]=int(hi.n)
            row[f"{p}_low_n"]=int(lo.n)
            row[f"{p}_high_long"]=float(hi.long_rate)
            row[f"{p}_high_short"]=float(hi.short_rate)
            row[f"{p}_low_long"]=float(lo.long_rate)
            row[f"{p}_low_short"]=float(lo.short_rate)
            row[f"{p}_delta_D"]=d
            need=150 if p=="development" else 75
            pass_n = pass_n and int(hi.n)>=need and int(lo.n)>=need
            vals.append(d)
            signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
        dd,d25,d26=vals
        rep=(
            pass_n and abs(dd)>=.06 and signs[0]!=0 and
            signs[1]==signs[0] and signs[2]==signs[0] and
            abs(d25)>=.03 and abs(d26)>=.03
        )
        row["classification"]="REPLICATED_CONDITIONAL" if rep else "WEAK_OR_UNSTABLE"
        summaries.append(row)
    sm=pd.DataFrame(summaries)

    status = "SOL_INDICATOR_RELATIONSHIP_S4C_COMPLETED"
    OUT_JSON.write_text(json.dumps({
        "status":status,
        "specs":{k:specs[k] for k in ["loc_24h","oi_chg_15m","taker_imb_15m"]},
        "summaries":sm.to_dict(orient="records")
    }, indent=2)+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 4C Result","",
        "**High 24h location only; exact Stage 4 DEV tertiles reused.**","",
        "| Context | Partition | OI HIGH N | OI HIGH L/S | OI LOW N | OI LOW L/S | delta-D | Class |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    labels={"HIGHLOC_TAKERBUY_OI":"High-location + Taker BUY high",
            "HIGHLOC_TAKERSELL_OI":"High-location + Taker SELL high"}
    for r in sm.itertuples(index=False):
        for p in PARTS:
            lines.append(
                f"| {labels[r.contrast]} | {p} | {getattr(r,p+'_high_n')} | "
                f"{pct(getattr(r,p+'_high_long'))}/{pct(getattr(r,p+'_high_short'))} | "
                f"{getattr(r,p+'_low_n')} | {pct(getattr(r,p+'_low_long'))}/{pct(getattr(r,p+'_low_short'))} | "
                f"{pct(getattr(r,p+'_delta_D'))} | {r.classification} |"
            )
    lines += ["","## Interpretation guardrail","",
              "The contrast isolates whether OI expansion vs contraction changes directional outcome while both price location and taker state are held fixed.",
              "It does not yet establish temporal causality; sequence ordering remains Stage 5A.","",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(status+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
