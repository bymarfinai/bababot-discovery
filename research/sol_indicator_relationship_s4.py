#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 4 conditional interactions."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4_Result.md"
OUT_JSON = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4_Result.json"
OUT_CELLS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4A_CELLS.csv"
OUT_CONTRASTS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4B_CONTRASTS.csv"
OUT_STATUS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S4_Status.txt"

PAIR_LIST = [
    ("oi_chg_15m","loc_24h"),
    ("oi_chg_15m","dist_high_24h"),
    ("oi_chg_15m","dist_low_24h"),
    ("oi_chg_15m","taker_imb_15m"),
    ("oi_chg_15m","taker_imb_change_1h"),
    ("oi_chg_15m","quotevol_z_24h"),
    ("oi_chg_15m","breakout_up_24h"),
    ("oi_chg_15m","breakout_down_24h"),
    ("oi_chg_15m","funding_z_30"),
    ("oi_chg_1h","loc_24h"),
    ("impulse5m_prev","oi_chg_15m"),
    ("impulse5m_prev","taker_imb_15m"),
    ("impulse5m_prev","quotevol_z_24h"),
]

CONTINUOUS = {
    "oi_chg_15m","oi_chg_1h","loc_24h","dist_high_24h","dist_low_24h",
    "taker_imb_15m","taker_imb_change_1h","quotevol_z_24h","funding_z_30"
}
BREAKOUT = {"breakout_up_24h","breakout_down_24h"}

PARTS = ["development","validation_2025","validation_2026"]

def attach_impulse(a, raw):
    rr = (raw.set_index("ts").close / raw.set_index("ts").open - 1.0)
    prev_t = pd.to_datetime(a.decision_time, utc=True) - pd.Timedelta(minutes=5)
    a = a.copy()
    a["impulse5m_prev"] = rr.reindex(prev_t).to_numpy(float)
    return a

def build_specs(a):
    specs = {}
    dev = a[a.partition=="development"]
    for f in CONTINUOUS:
        s = pd.to_numeric(dev[f], errors="coerce").dropna()
        q = s.quantile([1/3,2/3]).to_list()
        specs[f] = {"kind":"tertile","cuts":[float(q[0]),float(q[1])]}
    for f in BREAKOUT:
        specs[f] = {"kind":"breakout"}
    specs["impulse5m_prev"] = {"kind":"impulse"}
    return specs

def bucket(v, spec):
    if pd.isna(v):
        return None
    if spec["kind"]=="tertile":
        a,b = spec["cuts"]
        if v <= a: return "LOW"
        if v <= b: return "MID"
        return "HIGH"
    if spec["kind"]=="breakout":
        return "POSITIVE" if float(v)>0 else "ZERO"
    if spec["kind"]=="impulse":
        if v <= -0.005: return "DOWN_IMPULSE"
        if v >= 0.005: return "UP_IMPULSE"
        return "NEUTRAL"
    return None

def rate(s, name):
    return float((s==name).mean()) if len(s) else np.nan

def make_cells(a, specs):
    rows=[]
    base_cols=["partition","target_1pct_4h","fwd_ret_4h","max_up_4h","max_down_4h"]
    for f1,f2 in PAIR_LIST:
        z=a[base_cols+[f1,f2]].copy()
        z=z[z.partition.notna() & z.target_1pct_4h.notna()]
        z["b1"]=[bucket(v,specs[f1]) for v in z[f1]]
        z["b2"]=[bucket(v,specs[f2]) for v in z[f2]]
        z=z[z.b1.notna() & z.b2.notna()]
        for p in PARTS:
            q=z[z.partition==p]
            for (b1,b2),g in q.groupby(["b1","b2"],sort=True):
                lr=rate(g.target_1pct_4h,"LONG")
                sr=rate(g.target_1pct_4h,"SHORT")
                rows.append({
                    "pair":f"{f1}__X__{f2}","f1":f1,"f2":f2,"partition":p,
                    "b1":b1,"b2":b2,"n":len(g),
                    "long_rate":lr,"short_rate":sr,"D":lr-sr,
                    "none_rate":rate(g.target_1pct_4h,"NONE"),
                    "ambiguous_rate":rate(g.target_1pct_4h,"AMBIGUOUS"),
                    "median_fwd_ret_4h":float(g.fwd_ret_4h.median()),
                    "median_max_up_4h":float(g.max_up_4h.median()),
                    "median_max_down_4h":float(g.max_down_4h.median()),
                })
    return pd.DataFrame(rows)

CONTRASTS = [
    ("A_OI_at_high_location","oi_chg_15m__X__loc_24h",("HIGH","HIGH"),("LOW","HIGH")),
    ("B_OI_at_low_location","oi_chg_15m__X__loc_24h",("HIGH","LOW"),("LOW","LOW")),
    ("C_OI_on_up_breakout","oi_chg_15m__X__breakout_up_24h",("HIGH","POSITIVE"),("LOW","POSITIVE")),
    ("D_OI_on_down_breakout","oi_chg_15m__X__breakout_down_24h",("HIGH","POSITIVE"),("LOW","POSITIVE")),
    ("E_UPimpulse_OI","impulse5m_prev__X__oi_chg_15m",("UP_IMPULSE","HIGH"),("UP_IMPULSE","LOW")),
    ("F_DOWNimpulse_OI","impulse5m_prev__X__oi_chg_15m",("DOWN_IMPULSE","HIGH"),("DOWN_IMPULSE","LOW")),
    ("G_aggressive_buy_OI","oi_chg_15m__X__taker_imb_15m",("HIGH","HIGH"),("LOW","HIGH")),
    ("H_aggressive_sell_OI","oi_chg_15m__X__taker_imb_15m",("HIGH","LOW"),("LOW","LOW")),
    ("I_volume_expansion_OI","oi_chg_15m__X__quotevol_z_24h",("HIGH","HIGH"),("LOW","HIGH")),
    ("J1_highFunding_OI","oi_chg_15m__X__funding_z_30",("HIGH","HIGH"),("LOW","HIGH")),
    ("J2_lowFunding_OI","oi_chg_15m__X__funding_z_30",("HIGH","LOW"),("LOW","LOW")),
]

def get_cell(cells,pair,p,b1,b2):
    q=cells[(cells.pair==pair)&(cells.partition==p)&(cells.b1==b1)&(cells.b2==b2)]
    return None if q.empty else q.iloc[0]

def contrasts(cells):
    out=[]
    for name,pair,left,right in CONTRASTS:
        row={"contrast":name,"pair":pair,"left_cell":"|".join(left),"right_cell":"|".join(right)}
        ok=True; signs=[]; deltas=[]
        for p in PARTS:
            l=get_cell(cells,pair,p,*left)
            r=get_cell(cells,pair,p,*right)
            if l is None or r is None:
                row[f"{p}_left_n"]=0;row[f"{p}_right_n"]=0
                row[f"{p}_left_D"]=np.nan;row[f"{p}_right_D"]=np.nan;row[f"{p}_delta_D"]=np.nan
                ok=False;signs.append(0);deltas.append(np.nan);continue
            d=float(l.D-r.D)
            row[f"{p}_left_n"]=int(l.n);row[f"{p}_right_n"]=int(r.n)
            row[f"{p}_left_D"]=float(l.D);row[f"{p}_right_D"]=float(r.D);row[f"{p}_delta_D"]=d
            need=150 if p=="development" else 75
            ok=ok and int(l.n)>=need and int(r.n)>=need
            signs.append(int(np.sign(d)) if np.isfinite(d) else 0);deltas.append(d)
        dd,d25,d26=deltas
        rep = (
            ok and np.isfinite(dd) and abs(dd)>=.06 and signs[0]!=0 and
            signs[1]==signs[0] and signs[2]==signs[0] and
            abs(d25)>=.03 and abs(d26)>=.03
        )
        row["classification"]="REPLICATED_CONDITIONAL" if rep else "WEAK_OR_UNSTABLE"
        out.append(row)
    return pd.DataFrame(out)

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.1f}%"

def main():
    raw=s3.load_klines()
    metrics=s3.load_metrics()
    funding=s3.load_funding()
    a=s3.add_targets(s3.add_derivatives(s3.build_15m(raw),metrics,funding),raw)
    a=a[(a.decision_time>=s3.SCORE_START)&(a.decision_time<s3.END)].copy()
    a=attach_impulse(a,raw)

    specs=build_specs(a)
    cells=make_cells(a,specs)
    cons=contrasts(cells)

    cells.to_csv(OUT_CELLS,index=False)
    cons.to_csv(OUT_CONTRASTS,index=False)

    rep=cons[cons.classification=="REPLICATED_CONDITIONAL"].copy()
    status="SOL_INDICATOR_RELATIONSHIP_S4_COMPLETED_WITH_REPLICATED_INTERACTIONS" if len(rep) else "SOL_INDICATOR_RELATIONSHIP_S4_COMPLETED_NO_REPLICATED_INTERACTION"

    report={
        "protocol":"SOL_INDICATOR_RELATIONSHIP_S4",
        "status":status,
        "frozen_end_exclusive":str(s3.END),
        "decision_rows":int(len(a)),
        "specs":specs,
        "pairs":[list(x) for x in PAIR_LIST],
        "replicated_contrasts":rep.to_dict(orient="records"),
        "all_contrasts":cons.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(report,indent=2,default=str)+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 4 Result","",
        "**Research only. Live BabaBot untouched.**","",
        f"- Decision rows: **{len(a):,}**",
        f"- Pairwise atlases: **{len(PAIR_LIST)}**",
        f"- Frozen mechanism contrasts: **{len(CONTRASTS)}**",
        f"- Replicated conditional contrasts: **{len(rep)} / {len(CONTRASTS)}**","",
        "## Frozen mechanism contrasts","",
        "| Contrast | DEV delta-D | 2025 delta-D | 2026 delta-D | DEV N L/R | 2025 N L/R | 2026 N L/R | Class |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in cons.itertuples(index=False):
        lines.append(
            f"| {r.contrast} | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} | "
            f"{r.development_left_n}/{r.development_right_n} | {r.validation_2025_left_n}/{r.validation_2025_right_n} | "
            f"{r.validation_2026_left_n}/{r.validation_2026_right_n} | {r.classification} |"
        )

    lines += ["","## Replicated conditional effects",""]
    if len(rep):
        for r in rep.itertuples(index=False):
            lines.append(
                f"- **{r.contrast}**: delta-D DEV {pct(r.development_delta_D)}, 2025 {pct(r.validation_2025_delta_D)}, 2026 {pct(r.validation_2026_delta_D)}."
            )
    else:
        lines.append("- None passed the preregistered replication gate.")

    lines += ["","## Stage 5B placement","",
              "BTC.D and USDT.D are explicitly reserved for **Stage 5B — Cross-Market Context & Lead-Lag**.",
              "They were not used anywhere in Stage 4, so future dominance results cannot contaminate these SOL-native interaction findings.","",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(status+"\n")
    print(status)
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
