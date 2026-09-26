#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 5A lead-lag / sequence atlas."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s4 as s4

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A_Result.md"
OUT_JSON = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A_Result.json"
OUT_LAG = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A1_LAG_ATLAS.csv"
OUT_SEQ = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A2_SEQUENCES.csv"
OUT_FAMILY = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A3_FIRST_MOVER.csv"
OUT_STATUS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5A_Status.txt"

PARTS = ["development","validation_2025","validation_2026"]
LAGS = {15:1, 30:2, 60:4}
CONT = ["oi_chg_15m","taker_imb_15m","quotevol_z_24h"]
BINARY = ["breakout_up_24h","breakout_down_24h"]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.1f}%"

def rate(s, name):
    return float((s == name).mean()) if len(s) else np.nan

def prepare():
    raw = s3.load_klines()
    metrics = s3.load_metrics()
    funding = pd.DataFrame(columns=["ts","funding_rate","funding_z_30","funding_change"])
    a = s3.add_targets(s3.add_derivatives(s3.build_15m(raw), metrics, funding), raw)
    a = a[(a.decision_time >= s3.SCORE_START) & (a.decision_time < s3.END)].copy()
    a = s4.attach_impulse(a, raw)

    # Frozen DEV tertiles for variables used in Stage 5A.
    dev = a[a.partition=="development"]
    specs={}
    for f in CONT:
        q=dev[f].dropna().quantile([1/3,2/3]).to_list()
        specs[f]={"kind":"tertile","cuts":[float(q[0]),float(q[1])]}
    specs["impulse5m_prev"]={"kind":"impulse"}
    for f in BINARY:
        specs[f]={"kind":"breakout"}

    for f,spec in specs.items():
        a[f+"_bucket"]=[s4.bucket(v,spec) for v in a[f]]

    # Lagged frozen states.
    for mins,steps in LAGS.items():
        for f in specs:
            a[f"{f}_bucket_lag{mins}"] = a[f+"_bucket"].shift(steps)
    return a,specs

def summarize_group(g):
    lr=rate(g.target_1pct_4h,"LONG")
    sr=rate(g.target_1pct_4h,"SHORT")
    return {
        "n":len(g),
        "long_rate":lr,
        "short_rate":sr,
        "D":lr-sr if len(g) else np.nan,
        "none_rate":rate(g.target_1pct_4h,"NONE"),
        "ambiguous_rate":rate(g.target_1pct_4h,"AMBIGUOUS"),
        "median_fwd_ret_4h":float(g.fwd_ret_4h.median()) if len(g) else np.nan,
        "median_max_up_4h":float(g.max_up_4h.median()) if len(g) else np.nan,
        "median_max_down_4h":float(g.max_down_4h.median()) if len(g) else np.nan,
    }

def lag_atlas(a):
    vars_ = ["oi_chg_15m","taker_imb_15m","quotevol_z_24h","impulse5m_prev","breakout_up_24h","breakout_down_24h"]
    rows=[]
    for f in vars_:
        if f in CONT:
            low,high="LOW","HIGH"
        elif f=="impulse5m_prev":
            low,high="DOWN_IMPULSE","UP_IMPULSE"
        else:
            low,high="ZERO","POSITIVE"
        for mins in LAGS:
            col=f"{f}_bucket_lag{mins}"
            for p in PARTS:
                q=a[(a.partition==p)&a.target_1pct_4h.notna()]
                for b in [low,high]:
                    g=q[q[col]==b]
                    r={"feature":f,"lag_min":mins,"partition":p,"bucket":b}
                    r.update(summarize_group(g))
                    rows.append(r)
    df=pd.DataFrame(rows)

    # Add contrast-level replication classification.
    cs=[]
    for f in vars_:
        if f in CONT:
            low,high="LOW","HIGH"
        elif f=="impulse5m_prev":
            low,high="DOWN_IMPULSE","UP_IMPULSE"
        else:
            low,high="ZERO","POSITIVE"
        for mins in LAGS:
            row={"feature":f,"lag_min":mins}
            ok=True; vals=[]; signs=[]
            for p in PARTS:
                q=df[(df.feature==f)&(df.lag_min==mins)&(df.partition==p)]
                lo=q[q.bucket==low].iloc[0];hi=q[q.bucket==high].iloc[0]
                d=float(hi.D-lo.D)
                row[f"{p}_low_n"]=int(lo.n);row[f"{p}_high_n"]=int(hi.n);row[f"{p}_delta_D"]=d
                need=200 if p=="development" else 100
                ok=ok and int(lo.n)>=need and int(hi.n)>=need
                vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            dd,d25,d26=vals
            rep=(ok and abs(dd)>=.05 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.02 and abs(d26)>=.02)
            row["classification"]="REPLICATED_LAG_EFFECT" if rep else "WEAK_OR_UNSTABLE"
            cs.append(row)
    return df,pd.DataFrame(cs)

MOTIFS = [
    ("A1_OI_to_TakerBuy","oi_chg_15m","HIGH","LOW","taker_imb_15m","HIGH"),
    ("A2_OI_to_TakerSell","oi_chg_15m","HIGH","LOW","taker_imb_15m","LOW"),
    ("B1_Taker_to_OIHigh","taker_imb_15m","HIGH","LOW","oi_chg_15m","HIGH"),
    ("B2_Taker_to_OILow","taker_imb_15m","HIGH","LOW","oi_chg_15m","LOW"),
    ("C1_OI_to_VolumeHigh","oi_chg_15m","HIGH","LOW","quotevol_z_24h","HIGH"),
    ("D1_Volume_to_OIHigh","quotevol_z_24h","HIGH","LOW","oi_chg_15m","HIGH"),
    ("D2_Volume_to_OILow","quotevol_z_24h","HIGH","LOW","oi_chg_15m","LOW"),
    ("E1_OI_to_UpImpulse","oi_chg_15m","HIGH","LOW","impulse5m_prev","UP_IMPULSE"),
    ("E2_OI_to_DownImpulse","oi_chg_15m","HIGH","LOW","impulse5m_prev","DOWN_IMPULSE"),
    ("F1_UpImpulse_to_OIHigh","impulse5m_prev","UP_IMPULSE","DOWN_IMPULSE","oi_chg_15m","HIGH"),
    ("F2_UpImpulse_to_OILow","impulse5m_prev","UP_IMPULSE","DOWN_IMPULSE","oi_chg_15m","LOW"),
    ("G1_OI_to_UpBreakout","oi_chg_15m","HIGH","LOW","breakout_up_24h","POSITIVE"),
    ("G2_OI_to_DownBreakout","oi_chg_15m","HIGH","LOW","breakout_down_24h","POSITIVE"),
    ("H1_UpBreakout_to_OIHigh","breakout_up_24h","POSITIVE","ZERO","oi_chg_15m","HIGH"),
    ("H2_DownBreakout_to_OILow","breakout_down_24h","POSITIVE","ZERO","oi_chg_15m","LOW"),
]

def sequence_atlas(a):
    rows=[]; summaries=[]
    for name,lead,lead_left,lead_right,current,current_bucket in MOTIFS:
        for mins in LAGS:
            lead_col=f"{lead}_bucket_lag{mins}"
            current_col=f"{current}_bucket"
            for p in PARTS:
                q=a[(a.partition==p)&a.target_1pct_4h.notna()&(a[current_col]==current_bucket)]
                for side,b in [("LEFT",lead_left),("RIGHT",lead_right)]:
                    g=q[q[lead_col]==b]
                    r={"motif":name,"lead_feature":lead,"current_feature":current,"lag_min":mins,
                       "partition":p,"side":side,"lead_bucket":b,"current_bucket":current_bucket}
                    r.update(summarize_group(g))
                    rows.append(r)
    df=pd.DataFrame(rows)

    for name,*_ in MOTIFS:
        for mins in LAGS:
            row={"motif":name,"lag_min":mins};ok=True;vals=[];signs=[]
            for p in PARTS:
                q=df[(df.motif==name)&(df.lag_min==mins)&(df.partition==p)]
                l=q[q.side=="LEFT"].iloc[0];r=q[q.side=="RIGHT"].iloc[0]
                d=float(l.D-r.D)
                row[f"{p}_left_n"]=int(l.n);row[f"{p}_right_n"]=int(r.n)
                row[f"{p}_left_D"]=float(l.D);row[f"{p}_right_D"]=float(r.D);row[f"{p}_delta_D"]=d
                need=150 if p=="development" else 75
                ok=ok and int(l.n)>=need and int(r.n)>=need
                vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            dd,d25,d26=vals
            rep=(ok and abs(dd)>=.06 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.03 and abs(d26)>=.03)
            row["classification"]="REPLICATED_SEQUENCE" if rep else "WEAK_OR_UNSTABLE"
            summaries.append(row)
    return df,pd.DataFrame(summaries)

FAMILIES = {
    "OI_vs_Taker":(["A1_OI_to_TakerBuy","A2_OI_to_TakerSell"],["B1_Taker_to_OIHigh","B2_Taker_to_OILow"]),
    "OI_vs_Volume":(["C1_OI_to_VolumeHigh"],["D1_Volume_to_OIHigh","D2_Volume_to_OILow"]),
    "OI_vs_Impulse":(["E1_OI_to_UpImpulse","E2_OI_to_DownImpulse"],["F1_UpImpulse_to_OIHigh","F2_UpImpulse_to_OILow"]),
    "OI_vs_Breakout":(["G1_OI_to_UpBreakout","G2_OI_to_DownBreakout"],["H1_UpBreakout_to_OIHigh","H2_DownBreakout_to_OILow"]),
}

def first_mover(seq_summary):
    rows=[]
    for fam,(oi_first,other_first) in FAMILIES.items():
        for direction,names in [("OI_FIRST",oi_first),("OTHER_FIRST",other_first)]:
            q=seq_summary[(seq_summary.motif.isin(names))&(seq_summary.classification=="REPLICATED_SEQUENCE")]
            lags=sorted(q.lag_min.unique().tolist()) if len(q) else []
            rows.append({
                "family":fam,
                "direction":direction,
                "replicated_sequence_count":int(len(q)),
                "replicated_exact_lags":";".join(str(x) for x in lags),
                "temporal_replication":bool(len(q)>0),
            })
    return pd.DataFrame(rows)

def main():
    a,specs=prepare()
    lag_cells,lag_summary=lag_atlas(a)
    seq_cells,seq_summary=sequence_atlas(a)
    fm=first_mover(seq_summary)

    lag_cells.to_csv(OUT_LAG,index=False)
    seq_cells.to_csv(OUT_SEQ,index=False)
    fm.to_csv(OUT_FAMILY,index=False)

    rep_lag=lag_summary[lag_summary.classification=="REPLICATED_LAG_EFFECT"]
    rep_seq=seq_summary[seq_summary.classification=="REPLICATED_SEQUENCE"]
    status="SOL_INDICATOR_RELATIONSHIP_S5A_COMPLETED"
    payload={
        "status":status,"specs":specs,
        "replicated_lag_effects":rep_lag.to_dict(orient="records"),
        "replicated_sequences":rep_seq.to_dict(orient="records"),
        "first_mover":fm.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 5A Result","",
        "**Lead-lag / ordered mechanism study. Research only.**","",
        f"- Decision rows: **{len(a):,}**",
        f"- Frozen lags: **15m / 30m / 60m**",
        f"- Replicated lagged marginal effects: **{len(rep_lag)}**",
        f"- Replicated ordered motif × lag combinations: **{len(rep_seq)}**","",
        "## Replicated ordered sequences","",
        "| Motif | Lag | DEV delta-D | 2025 | 2026 | Class |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if len(rep_seq):
        for r in rep_seq.itertuples(index=False):
            lines.append(f"| {r.motif} | {r.lag_min}m | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} | {r.classification} |")
    else:
        lines.append("| none | - | - | - | - | - |")

    lines += ["","## First-mover family map","",
              "| Family | Direction | Replicated rows | Exact lags |",
              "|---|---|---:|---|"]
    for r in fm.itertuples(index=False):
        lines.append(f"| {r.family} | {r.direction} | {r.replicated_sequence_count} | {r.replicated_exact_lags or '-'} |")

    lines += ["","## Guardrail","",
              "A replicated lead-lag pattern means a fixed prior state carries conditional predictive information for the later Stage-2 outcome. It does not prove causal market mechanics.",
              "BTC.D / USDT.D are not used here and remain reserved for Stage 5B.","",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(status+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
