#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 5B cross-market dominance."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s4 as s4

ROOT = Path(__file__).resolve().parent.parent
DOM_CSV = ROOT / "research" / "_stage5b_dominance_1d.csv"
DOM_META = ROOT / "research" / "_stage5b_dominance_fetch_meta.json"

OUT_MD = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B_Result.md"
OUT_JSON = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B_Result.json"
OUT_AUDIT = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B_SOURCE_AUDIT.csv"
OUT_BUCKETS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B1_BUCKETS.csv"
OUT_MARG = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B1_MARGINAL_SUMMARY.csv"
OUT_OI = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B2_OI_CONTEXT.csv"
OUT_OI_INC = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B2B_INCREMENTAL_DOMINANCE.csv"
OUT_IMP = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B3_IMPULSE_CONTEXT.csv"
OUT_LAG = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B4_LAGGED.csv"
OUT_STATUS = ROOT / "SOL_INDICATOR_RELATIONSHIP_S5B_Status.txt"

PARTS = ["development","validation_2025","validation_2026"]
WINDOWS = {"24h":1}
LAGS = {}
SERIES = {"btcd":"BTC.D","usdtd":"USDT.D"}

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.1f}%"

def rate(s, name):
    return float((s == name).mean()) if len(s) else np.nan

def group_stats(g):
    lr=rate(g.target_1pct_4h,"LONG")
    sr=rate(g.target_1pct_4h,"SHORT")
    return {
        "n":int(len(g)),
        "long_rate":lr,
        "short_rate":sr,
        "D":lr-sr if len(g) else np.nan,
        "none_rate":rate(g.target_1pct_4h,"NONE"),
        "ambiguous_rate":rate(g.target_1pct_4h,"AMBIGUOUS"),
        "median_fwd_ret_4h":float(g.fwd_ret_4h.median()) if len(g) else np.nan,
        "median_max_up_4h":float(g.max_up_4h.median()) if len(g) else np.nan,
        "median_max_down_4h":float(g.max_down_4h.median()) if len(g) else np.nan,
    }

def load_dominance():
    if not DOM_CSV.exists():
        raise RuntimeError("dominance CSV missing")
    d=pd.read_csv(DOM_CSV)
    d["ts"]=pd.to_datetime(d["ts"],utc=True,errors="coerce")
    for c in ["btcd_close","usdtd_close"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["ts"]).sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    # TradingView timestamps are daily bar opens. Close is causally known one day later.
    d["avail_ts"]=d["ts"]+pd.Timedelta(days=1)

    feature_frames={}
    for key in SERIES:
        c=f"{key}_close"
        z=d[["avail_ts",c]].dropna().copy().sort_values("avail_ts")
        for nm,n in WINDOWS.items():
            lag=z[c].shift(n)
            exact=(z["avail_ts"]-z["avail_ts"].shift(n))==pd.Timedelta(days=n)
            z[f"{key}_chg_{nm}"]=np.where(exact,z[c]/lag-1.0,np.nan)
        feature_frames[key]=z
    return d,feature_frames

def prepare_sol():
    raw=s3.load_klines()
    metrics=s3.load_metrics()
    funding=pd.DataFrame(columns=["ts","funding_rate","funding_z_30","funding_change"])
    a=s3.add_targets(s3.add_derivatives(s3.build_15m(raw),metrics,funding),raw)
    a=a[(a.decision_time>=s3.SCORE_START)&(a.decision_time<s3.END)].copy()
    a=s4.attach_impulse(a,raw)

    dev=a[a.partition=="development"]
    q=dev.oi_chg_15m.dropna().quantile([1/3,2/3]).to_list()
    oi_spec={"kind":"tertile","cuts":[float(q[0]),float(q[1])]}
    a["oi_bucket"]=[s4.bucket(v,oi_spec) for v in a.oi_chg_15m]
    a["impulse_bucket"]=[s4.bucket(v,{"kind":"impulse"}) for v in a.impulse5m_prev]
    return a,oi_spec

def causal_attach(a, feature_frames):
    out=a.copy().sort_values("decision_time")
    audits=[]
    accepted={}
    for key,label in SERIES.items():
        z=feature_frames[key].copy().sort_values("avail_ts")
        cols=[c for c in z.columns if c!="avail_ts"]
        m=pd.merge_asof(
            out[["decision_time"]].sort_values("decision_time"),
            z,
            left_on="decision_time",right_on="avail_ts",
            direction="backward",tolerance=pd.Timedelta(minutes=1440)
        )
        age=(m.decision_time-m.avail_ts).dt.total_seconds()/60.0
        for c in cols:
            out[c]=m[c].to_numpy()
        out[f"{key}_age_min"]=age.to_numpy()

        closecol=f"{key}_close"
        mask=out[closecol].notna() & out.partition.notna()
        cov=float(mask.sum()/out.partition.notna().sum())
        q=out[mask]
        first=None if q.empty else q.decision_time.min()
        last=None if q.empty else q.decision_time.max()
        part_ok={}
        for p in PARTS:
            qp=out[out.partition==p]
            part_ok[p]=float(qp[closecol].notna().mean()) if len(qp) else 0.0
        max_age=float(out.loc[mask,f"{key}_age_min"].max()) if mask.any() else np.nan
        ok=(cov>=.95 and all(v>=.95 for v in part_ok.values()) and np.isfinite(max_age) and max_age<=1440.0)
        accepted[key]=ok
        audits.append({
            "series":label,"rows_source":int(z[closecol].notna().sum()),
            "coverage_all":cov,
            "coverage_development":part_ok["development"],
            "coverage_2025":part_ok["validation_2025"],
            "coverage_2026":part_ok["validation_2026"],
            "first_aligned":None if first is None else str(first),
            "last_aligned":None if last is None else str(last),
            "max_age_min":max_age,
            "accepted":ok,
        })
    return out,pd.DataFrame(audits),accepted

def dom_specs(a,accepted):
    specs={}
    dev=a[a.partition=="development"]
    for key,ok in accepted.items():
        if not ok: continue
        for nm in WINDOWS:
            f=f"{key}_chg_{nm}"
            s=dev[f].dropna()
            q=s.quantile([1/3,2/3]).to_list()
            specs[f]={"cuts":[float(q[0]),float(q[1])]}
            a[f+"_bucket"]=[
                None if pd.isna(v) else ("LOW" if v<=q[0] else ("MID" if v<=q[1] else "HIGH"))
                for v in a[f]
            ]
    return a,specs

def marginal(a,specs):
    cells=[];summ=[]
    for f in specs:
        for p in PARTS:
            q=a[(a.partition==p)&a.target_1pct_4h.notna()]
            for b in ["LOW","MID","HIGH"]:
                g=q[q[f+"_bucket"]==b]
                r={"feature":f,"partition":p,"bucket":b}
                r.update(group_stats(g));cells.append(r)
        row={"feature":f};ok=True;vals=[];signs=[]
        for p in PARTS:
            q=pd.DataFrame(cells)
            q=q[(q.feature==f)&(q.partition==p)]
            lo=q[q.bucket=="LOW"].iloc[0];hi=q[q.bucket=="HIGH"].iloc[0]
            d=float(hi.D-lo.D);need=200 if p=="development" else 100
            row[f"{p}_low_n"]=int(lo.n);row[f"{p}_high_n"]=int(hi.n);row[f"{p}_delta_D"]=d
            ok=ok and int(lo.n)>=need and int(hi.n)>=need
            vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
        dd,d25,d26=vals
        rep=(ok and abs(dd)>=.05 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.02 and abs(d26)>=.02)
        row["classification"]="REPLICATED_DOMINANCE" if rep else "WEAK_OR_UNSTABLE"
        summ.append(row)
    return pd.DataFrame(cells),pd.DataFrame(summ)

def conditional_contrast(a,specs,mode):
    rows=[]
    for f in specs:
        for dom_state in ["HIGH","LOW"]:
            if mode=="oi_effect":
                contexts=[("OI_HIGH","HIGH"),("OI_LOW","LOW")]
                fixed_col=f+"_bucket";fixed_val=dom_state;cmp_col="oi_bucket"
            elif mode=="dom_incremental":
                for oi_state in ["HIGH","LOW"]:
                    row={"feature":f,"context":f"OI_{oi_state}","comparison":"DOM_HIGH_vs_LOW"}
                    ok=True;vals=[];signs=[]
                    for p in PARTS:
                        q=a[(a.partition==p)&a.target_1pct_4h.notna()&(a.oi_bucket==oi_state)]
                        hi=q[q[f+"_bucket"]=="HIGH"];lo=q[q[f+"_bucket"]=="LOW"]
                        hs=group_stats(hi);ls=group_stats(lo);d=hs["D"]-ls["D"]
                        row[f"{p}_left_n"]=hs["n"];row[f"{p}_right_n"]=ls["n"]
                        row[f"{p}_left_D"]=hs["D"];row[f"{p}_right_D"]=ls["D"];row[f"{p}_delta_D"]=d
                        need=150 if p=="development" else 75
                        ok=ok and hs["n"]>=need and ls["n"]>=need
                        vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
                    dd,d25,d26=vals
                    rep=(ok and abs(dd)>=.06 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.03 and abs(d26)>=.03)
                    row["classification"]="REPLICATED_CONDITIONAL" if rep else "WEAK_OR_UNSTABLE"
                    rows.append(row)
                continue
            row={"feature":f,"context":f"DOM_{dom_state}","comparison":"OI_HIGH_vs_LOW"}
            ok=True;vals=[];signs=[]
            for p in PARTS:
                q=a[(a.partition==p)&a.target_1pct_4h.notna()&(a[fixed_col]==fixed_val)]
                hi=q[q[cmp_col]=="HIGH"];lo=q[q[cmp_col]=="LOW"]
                hs=group_stats(hi);ls=group_stats(lo);d=hs["D"]-ls["D"]
                row[f"{p}_left_n"]=hs["n"];row[f"{p}_right_n"]=ls["n"]
                row[f"{p}_left_D"]=hs["D"];row[f"{p}_right_D"]=ls["D"];row[f"{p}_delta_D"]=d
                need=150 if p=="development" else 75
                ok=ok and hs["n"]>=need and ls["n"]>=need
                vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            dd,d25,d26=vals
            rep=(ok and abs(dd)>=.06 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.03 and abs(d26)>=.03)
            row["classification"]="REPLICATED_CONDITIONAL" if rep else "WEAK_OR_UNSTABLE"
            rows.append(row)
    return pd.DataFrame(rows)

def impulse_context(a,specs):
    rows=[]
    for f in specs:
        for imp in ["UP_IMPULSE","DOWN_IMPULSE"]:
            row={"feature":f,"impulse":imp,"comparison":"DOM_HIGH_vs_LOW"}
            ok=True;vals=[];signs=[]
            for p in PARTS:
                q=a[(a.partition==p)&a.target_1pct_4h.notna()&(a.impulse_bucket==imp)]
                hi=q[q[f+"_bucket"]=="HIGH"];lo=q[q[f+"_bucket"]=="LOW"]
                hs=group_stats(hi);ls=group_stats(lo);d=hs["D"]-ls["D"]
                row[f"{p}_high_n"]=hs["n"];row[f"{p}_low_n"]=ls["n"]
                row[f"{p}_high_D"]=hs["D"];row[f"{p}_low_D"]=ls["D"];row[f"{p}_delta_D"]=d
                need=150 if p=="development" else 75
                ok=ok and hs["n"]>=need and ls["n"]>=need
                vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            dd,d25,d26=vals
            rep=(ok and abs(dd)>=.06 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.03 and abs(d26)>=.03)
            row["classification"]="REPLICATED_CONDITIONAL" if rep else "WEAK_OR_UNSTABLE"
            rows.append(row)
    return pd.DataFrame(rows)

def lagged(a,accepted,specs):
    rows=[]
    if not LAGS:
        return pd.DataFrame(columns=["feature","lag_min","classification","development_delta_D","validation_2025_delta_D","validation_2026_delta_D"])
    # Intraday lagged dominance is only run when source resolution supports it.
    for key,ok in accepted.items():
        if not ok: continue
        f=f"{key}_chg_24h"
        for mins,steps in LAGS.items():
            col=f"{f}_bucket_lag{mins}"
            a[col]=a[f+"_bucket"].shift(steps)
            row={"feature":f,"lag_min":mins};gate=True;vals=[];signs=[]
            for p in PARTS:
                q=a[(a.partition==p)&a.target_1pct_4h.notna()]
                hi=q[q[col]=="HIGH"];lo=q[q[col]=="LOW"]
                hs=group_stats(hi);ls=group_stats(lo);d=hs["D"]-ls["D"]
                row[f"{p}_high_n"]=hs["n"];row[f"{p}_low_n"]=ls["n"]
                row[f"{p}_delta_D"]=d
                need=200 if p=="development" else 100
                gate=gate and hs["n"]>=need and ls["n"]>=need
                vals.append(d);signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            dd,d25,d26=vals
            rep=(gate and abs(dd)>=.05 and signs[0]!=0 and signs[1]==signs[0] and signs[2]==signs[0] and abs(d25)>=.02 and abs(d26)>=.02)
            row["classification"]="REPLICATED_LAG_EFFECT" if rep else "WEAK_OR_UNSTABLE"
            rows.append(row)
    return pd.DataFrame(rows)

def main():
    raw_dom,feature_frames=load_dominance()
    a,oi_spec=prepare_sol()
    a,audit,accepted=causal_attach(a,feature_frames)

    if not any(accepted.values()):
        status="SOL_INDICATOR_RELATIONSHIP_S5B_SOURCE_FAIL"
        audit.to_csv(OUT_AUDIT,index=False)
        pd.DataFrame(columns=["feature","partition","bucket","n","long_rate","short_rate","D"]).to_csv(OUT_BUCKETS,index=False)
        pd.DataFrame(columns=["feature","classification"]).to_csv(OUT_MARG,index=False)
        pd.DataFrame(columns=["feature","context","comparison","classification"]).to_csv(OUT_OI,index=False)
        pd.DataFrame(columns=["feature","context","comparison","classification"]).to_csv(OUT_OI_INC,index=False)
        pd.DataFrame(columns=["feature","impulse","comparison","classification"]).to_csv(OUT_IMP,index=False)
        pd.DataFrame(columns=["feature","lag_min","classification"]).to_csv(OUT_LAG,index=False)
        payload={
            "status":status,
            "source_meta":json.loads(DOM_META.read_text()) if DOM_META.exists() else {},
            "source_audit":audit.to_dict(orient="records"),
            "accepted":accepted,
            "reason":"No dominance series passed preregistered full-period coverage gate; no SOL outcome analysis was authorized."
        }
        OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
        lines=[
            "# SOL Indicator Relationship Discovery — Stage 5B Result","",
            "**SOURCE AUDIT FAILED — no analytical BTC.D/USDT.D result was produced.**","",
            "| Series | Coverage all | DEV | 2025 | 2026 | Max age | Accepted |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for r in audit.itertuples(index=False):
            lines.append(f"| {r.series} | {pct(r.coverage_all)} | {pct(r.coverage_development)} | {pct(r.coverage_2025)} | {pct(r.coverage_2026)} | {r.max_age_min:.0f}m | NO |")
        lines += ["","The source did not cover the frozen DEV/2025/2026 partitions at the preregistered minimum. No dominance thresholds, interaction results, or lag claims were computed.","",
                  f"**Status: {status}**"]
        OUT_MD.write_text("\n".join(lines)+"\n")
        OUT_STATUS.write_text(status+"\n")
        print(OUT_MD.read_text())
        return

    a,specs=dom_specs(a,accepted)

    buckets,marg=marginal(a,specs)
    oi=conditional_contrast(a,specs,"oi_effect")
    oi_inc=conditional_contrast(a,specs,"dom_incremental")
    imp=impulse_context(a,specs)
    lag=lagged(a,accepted,specs)

    audit.to_csv(OUT_AUDIT,index=False)
    buckets.to_csv(OUT_BUCKETS,index=False)
    marg.to_csv(OUT_MARG,index=False)
    oi.to_csv(OUT_OI,index=False)
    oi_inc.to_csv(OUT_OI_INC,index=False)
    imp.to_csv(OUT_IMP,index=False)
    lag.to_csv(OUT_LAG,index=False)

    rep_m=marg[marg.classification=="REPLICATED_DOMINANCE"]
    rep_inc=oi_inc[oi_inc.classification=="REPLICATED_CONDITIONAL"]
    rep_imp=imp[imp.classification=="REPLICATED_CONDITIONAL"]
    rep_lag=lag[lag.classification=="REPLICATED_LAG_EFFECT"]

    source_pass=all(bool(v) for v in accepted.values())
    status="SOL_INDICATOR_RELATIONSHIP_S5B_COMPLETED" if any(accepted.values()) else "SOL_INDICATOR_RELATIONSHIP_S5B_SOURCE_FAIL"

    payload={
        "status":status,
        "source_meta":json.loads(DOM_META.read_text()) if DOM_META.exists() else {},
        "source_audit":audit.to_dict(orient="records"),
        "accepted":accepted,
        "oi_spec":oi_spec,
        "dominance_specs":specs,
        "replicated_marginal":rep_m.to_dict(orient="records"),
        "replicated_incremental_beyond_oi":rep_inc.to_dict(orient="records"),
        "replicated_impulse_context":rep_imp.to_dict(orient="records"),
        "replicated_lag_effects":rep_lag.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 5B Result","",
        "**BTC.D / USDT.D 24h cross-market context. Research only.**","",
        "## Source audit","",
        "| Series | Coverage all | DEV | 2025 | 2026 | Max age | Accepted |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in audit.itertuples(index=False):
        lines.append(f"| {r.series} | {pct(r.coverage_all)} | {pct(r.coverage_development)} | {pct(r.coverage_2025)} | {pct(r.coverage_2026)} | {r.max_age_min:.0f}m | {'YES' if r.accepted else 'NO'} |")

    lines += ["","## Replicated marginal dominance changes","",
              "| Feature | DEV delta-D | 2025 | 2026 |",
              "|---|---:|---:|---:|"]
    if len(rep_m):
        for r in rep_m.itertuples(index=False):
            lines.append(f"| {r.feature} | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} |")
    else:
        lines.append("| none | - | - | - |")

    lines += ["","## Dominance adds information after OI is held fixed","",
              "| Feature / OI context | DEV delta-D | 2025 | 2026 |",
              "|---|---:|---:|---:|"]
    if len(rep_inc):
        for r in rep_inc.itertuples(index=False):
            lines.append(f"| {r.feature} / {r.context} | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} |")
    else:
        lines.append("| none | - | - | - |")

    lines += ["","## Dominance × 5m impulse replicated contexts","",
              "| Feature / impulse | DEV delta-D | 2025 | 2026 |",
              "|---|---:|---:|---:|"]
    if len(rep_imp):
        for r in rep_imp.itertuples(index=False):
            lines.append(f"| {r.feature} / {r.impulse} | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} |")
    else:
        lines.append("| none | - | - | - |")

    lines += ["","## Replicated lagged dominance effects","",
              "| Feature | Lag | DEV delta-D | 2025 | 2026 |",
              "|---|---:|---:|---:|---:|"]
    if len(rep_lag):
        for r in rep_lag.itertuples(index=False):
            lines.append(f"| {r.feature} | {r.lag_min}m | {pct(r.development_delta_D)} | {pct(r.validation_2025_delta_D)} | {pct(r.validation_2026_delta_D)} |")
    else:
        lines.append("| unavailable at daily source resolution | - | - | - | - |")

    lines += ["","## Guardrail","",
              "Dominance findings are predictive cross-market associations. They do not establish capital-flow causality and are not deployable rules yet.",
              "TOTAL/TOTAL2/TOTAL3 remain deferred unless BTC.D/USDT.D show replicating incremental information.","",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text(status+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
