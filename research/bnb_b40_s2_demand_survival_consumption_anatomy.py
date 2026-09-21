#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S2_DEMAND_SURVIVAL_CONSUMPTION_ANATOMY"
SRC=ROOT/"results/bnb_b40_s1/BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_CandidateLedger.csv.gz"

FORMATION_NUM=[
    "base_candles","base_width_pct","base_mean_added_overlap","base_mean_body_frac",
    "departure_bars","departure_net_progress_zone_r","departure_efficiency",
    "bos_overshoot_zone_r","bos_body_frac","max_bull_fvg_zone_r",
    "source_age_at_activation_h","protected_depth_to_broken_level_zone_r"
]
FORMATION_BIN=["has_bull_fvg","predeparture_swept_prior_low"]

RETEST_NUM=[
    "zone_age_at_retest_h","approach_slope_per_zone_r","approach_efficiency",
    "approach_overlap_mean","approach_net_progress_zone_r",
    "last1_bear_progress_zone_r","last2_bear_progress_zone_r","last3_bear_progress_zone_r",
    "touch_penetration_zone_r","touch_close_location","touch_body_zone_r","touch_range_zone_r"
]
RETEST_BIN=["touch_local_liquidity_sweep","touch_bullish","touch_close_above_base_high"]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def prepare():
    L=pd.read_csv(SRC,compression="gzip")
    for c in ["activation_ts","seed_pivot_ts","seed_confirm_ts","base_start_ts","base_end_ts",
              "departure_start_ts","first_retest_ts","consumption_ts","survival_resolution_ts"]:
        if c in L.columns:
            L[c]=pd.to_datetime(L[c],utc=True,errors="coerce")

    L["base_width_pct"]=pd.to_numeric(L.base_width,errors="coerce")/pd.to_numeric(L.bos_close,errors="coerce")
    L["protected_depth_to_broken_level_zone_r"]=(
        (pd.to_numeric(L.broken_level,errors="coerce")-pd.to_numeric(L.protected_low,errors="coerce"))/
        pd.to_numeric(L.base_width,errors="coerce")
    )
    L["touch_penetration_zone_r"]=(
        (pd.to_numeric(L.base_high,errors="coerce")-pd.to_numeric(L.touch_low,errors="coerce"))/
        pd.to_numeric(L.base_width,errors="coerce")
    )
    L["touch_close_location"]=(
        (pd.to_numeric(L.touch_close,errors="coerce")-pd.to_numeric(L.base_low,errors="coerce"))/
        pd.to_numeric(L.base_width,errors="coerce")
    )
    L["touch_body_zone_r"]=(
        (pd.to_numeric(L.touch_close,errors="coerce")-pd.to_numeric(L.touch_open,errors="coerce")).abs()/
        pd.to_numeric(L.base_width,errors="coerce")
    )
    L["touch_range_zone_r"]=(
        (pd.to_numeric(L.touch_high,errors="coerce")-pd.to_numeric(L.touch_low,errors="coerce"))/
        pd.to_numeric(L.base_width,errors="coerce")
    )
    L["touch_bullish"]=pd.to_numeric(L.touch_close,errors="coerce")>pd.to_numeric(L.touch_open,errors="coerce")
    L["touch_close_above_base_high"]=pd.to_numeric(L.touch_close,errors="coerce")>pd.to_numeric(L.base_high,errors="coerce")

    for c in FORMATION_BIN+RETEST_BIN:
        if c in L.columns and L[c].dtype!=bool:
            L[c]=L[c].astype(str).str.lower().map({"true":True,"false":False, "1":True,"0":False})

    E=L[(L.normalizable.astype(str).str.lower().isin(["true","1"])) &
        (L.survival_status.isin(["SURVIVE","CONSUMED"]))].copy()
    E["survived"]=E.survival_status.eq("SURVIVE")
    return L,E

def numeric_effect(E,feature):
    rows=[]
    dev=E[E.period=="DEV"]
    xdev=pd.to_numeric(dev[feature],errors="coerce").dropna()
    q25=float(xdev.quantile(.25)) if len(xdev) else np.nan
    q50=float(xdev.quantile(.50)) if len(xdev) else np.nan
    q75=float(xdev.quantile(.75)) if len(xdev) else np.nan
    iqr=q75-q25 if np.isfinite(q75) and np.isfinite(q25) else np.nan

    for per in ["DEV","REF"]:
        q=E[E.period==per].copy()
        x=pd.to_numeric(q[feature],errors="coerce")
        ok=x.notna()
        q=q.loc[ok].copy()
        x=x.loc[ok]
        s=x[q.survived]
        c=x[~q.survived]
        sm=float(s.median()) if len(s) else np.nan
        cm=float(c.median()) if len(c) else np.nan
        eff=(sm-cm)/iqr if np.isfinite(iqr) and abs(iqr)>1e-15 else np.nan
        rows.append({
            "period":per,"feature":feature,"n":len(q),
            "survivor_n":int(q.survived.sum()),"consumed_n":int((~q.survived).sum()),
            "survivor_median":sm,"consumed_median":cm,
            "median_diff":sm-cm if np.isfinite(sm) and np.isfinite(cm) else np.nan,
            "effect_dev_iqr":eff,
            "dev_q25":q25,"dev_q50":q50,"dev_q75":q75,
        })
    return rows,(q25,q50,q75)

def binary_effect(E,feature):
    rows=[]
    for per in ["DEV","REF"]:
        q=E[E.period==per].copy()
        x=q[feature]
        ok=x.notna()
        q=q.loc[ok].copy()
        x=x.loc[ok].astype(bool)
        t=q[x]; f=q[~x]
        tr=float(t.survived.mean()) if len(t) else np.nan
        fr=float(f.survived.mean()) if len(f) else np.nan
        rows.append({
            "period":per,"feature":feature,"n":len(q),
            "true_n":len(t),"false_n":len(f),
            "survival_true":tr,"survival_false":fr,
            "rate_diff":tr-fr if np.isfinite(tr) and np.isfinite(fr) else np.nan,
        })
    return rows

def quartile_table(E,feature,cuts):
    q25,q50,q75=cuts
    if not all(np.isfinite([q25,q50,q75])): return []
    # Discrete/tied structural features can have repeated quartile edges.
    # Do not invent artificial bins; keep their median effect but skip 4-band display.
    if not (q25 < q50 < q75):
        return []
    rows=[]
    for per in ["DEV","REF"]:
        q=E[E.period==per].copy()
        x=pd.to_numeric(q[feature],errors="coerce")
        bins=pd.cut(x,[-np.inf,q25,q50,q75,np.inf],labels=["Q1","Q2","Q3","Q4"],include_lowest=True)
        for band in ["Q1","Q2","Q3","Q4"]:
            z=q[bins==band]
            rows.append({
                "period":per,"feature":feature,"band":band,"n":len(z),
                "survive":int(z.survived.sum()),
                "survival_rate":float(z.survived.mean()) if len(z) else np.nan,
                "dev_q25":q25,"dev_q50":q50,"dev_q75":q75,
            })
    return rows

def rank_consistent(num_df,bin_df):
    rows=[]
    if len(num_df):
        for feature,z in num_df.groupby("feature"):
            if set(z.period)!={"DEV","REF"}: continue
            d=z[z.period=="DEV"].iloc[0]; r=z[z.period=="REF"].iloc[0]
            de=float(d.effect_dev_iqr); re=float(r.effect_dev_iqr)
            same=np.isfinite(de) and np.isfinite(re) and np.sign(de)==np.sign(re) and np.sign(de)!=0
            score=min(abs(de),abs(re)) if same else -1.0
            rows.append({
                "feature":feature,
                "type":"NUMERIC",
                "dev_effect":de,"ref_effect":re,
                "same_direction":same,"consistency_score":score,
            })
    if len(bin_df):
        for feature,z in bin_df.groupby("feature"):
            if set(z.period)!={"DEV","REF"}: continue
            d=z[z.period=="DEV"].iloc[0]; r=z[z.period=="REF"].iloc[0]
            de=float(d.rate_diff); re=float(r.rate_diff)
            same=np.isfinite(de) and np.isfinite(re) and np.sign(de)==np.sign(re) and np.sign(de)!=0
            score=min(abs(de),abs(re)) if same else -1.0
            rows.append({
                "feature":feature,
                "type":"BINARY",
                "dev_effect":de,"ref_effect":re,
                "same_direction":same,"consistency_score":score,
            })
    return pd.DataFrame(rows).sort_values(["same_direction","consistency_score"],ascending=[False,False])

def year_table(E,features):
    rows=[]
    for y in sorted(E.year.unique()):
        q=E[E.year==y].copy()
        for feat,typ in features:
            if typ=="NUMERIC":
                x=pd.to_numeric(q[feat],errors="coerce")
                ok=x.notna(); qq=q.loc[ok]; x=x.loc[ok]
                if len(qq)<10: continue
                med=float(pd.to_numeric(E[E.period==("DEV" if y<=2024 else "REF")][feat],errors="coerce").median())
                lo=qq[x<=med]; hi=qq[x>med]
                rows.append({
                    "year":int(y),"feature":feat,"type":typ,
                    "low_n":len(lo),"low_survival":float(lo.survived.mean()) if len(lo) else np.nan,
                    "high_n":len(hi),"high_survival":float(hi.survived.mean()) if len(hi) else np.nan,
                })
            else:
                x=q[feat].astype(bool)
                f=q[~x]; t=q[x]
                rows.append({
                    "year":int(y),"feature":feat,"type":typ,
                    "low_n":len(f),"low_survival":float(f.survived.mean()) if len(f) else np.nan,
                    "high_n":len(t),"high_survival":float(t.survived.mean()) if len(t) else np.nan,
                })
    return pd.DataFrame(rows)

def main():
    if not SRC.exists():
        raise RuntimeError(f"missing frozen B40-S1 ledger: {SRC}")

    L,E=prepare()
    parity=[]
    for per in ["DEV","REF"]:
        q=L[(L.period==per)&(L.normalizable.astype(str).str.lower().isin(["true","1"]))]
        e=E[E.period==per]
        parity.append({
            "period":per,
            "normalizable":len(q),
            "eligible_survive_consumed":len(e),
            "survive":int(e.survived.sum()),
            "consumed":int((~e.survived).sum()),
        })
    P=pd.DataFrame(parity)

    expected={"DEV":(683,657,500,157),"REF":(414,403,309,94)}
    for r in P.itertuples(index=False):
        if (r.normalizable,r.eligible_survive_consumed,r.survive,r.consumed)!=expected[r.period]:
            raise RuntimeError(f"B40-S1 parity drift {r}")

    num_rows=[]; quart=[]
    num_features=FORMATION_NUM+RETEST_NUM
    for f in num_features:
        rows,cuts=numeric_effect(E,f)
        num_rows.extend(rows)
        quart.extend(quartile_table(E,f,cuts))
    NUM=pd.DataFrame(num_rows)
    Q=pd.DataFrame(quart)

    bin_rows=[]
    for f in FORMATION_BIN+RETEST_BIN:
        bin_rows.extend(binary_effect(E,f))
    BIN=pd.DataFrame(bin_rows)

    R=rank_consistent(NUM,BIN)
    formation=set(FORMATION_NUM+FORMATION_BIN)
    R["family"]=np.where(R.feature.isin(formation),"FORMATION","RETEST")
    RF=R[R.family=="FORMATION"].copy()
    RR=R[R.family=="RETEST"].copy()

    # Descriptive annual check for top 3 consistent descriptors per family.
    tops=[]
    for fam,z in [("FORMATION",RF),("RETEST",RR)]:
        zz=z[z.same_direction].head(3)
        for r in zz.itertuples(index=False):
            tops.append((r.feature,r.type))
    Y=year_table(E,tops)

    P.to_csv(ROOT/f"{PFX}_Parity.csv",index=False)
    NUM.to_csv(ROOT/f"{PFX}_NumericEffects.csv",index=False)
    BIN.to_csv(ROOT/f"{PFX}_BinaryEffects.csv",index=False)
    Q.to_csv(ROOT/f"{PFX}_Quartiles.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_ConsistentRanking.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_TopFeatureByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        "PARENT=B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE\n"
        "TARGET=SURVIVE_VS_CONSUMED\n"
        "AMBIGUOUS_CENSORED_EXCLUDED=TRUE\n"
        "QUARTILE_CUTS=DEV_ONLY_APPLIED_UNCHANGED_TO_REF\n"
        "NO_COMBINATIONS=TRUE\nNO_PROMOTION=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S2 — Demand Survival vs Consumption Anatomy","",
        "Primary target is SURVIVE vs CONSUMED only. Expansion labels are not used to define feature effects.","",
        "## Frozen parent parity","",
        "| Period | Normalizable | Eligible | Survive | Consumed |",
        "|---|---:|---:|---:|---:|"
    ]
    for r in P.itertuples(index=False):
        lines.append(f"| {r.period} | {r.normalizable} | {r.eligible_survive_consumed} | {r.survive} | {r.consumed} |")

    def add_rank(title,df):
        out=["",title,"",
             "| Feature | Type | DEV effect | REF effect | Same direction | Consistency |",
             "|---|---|---:|---:|---|---:|"]
        for r in df.head(10).itertuples(index=False):
            if r.type=="NUMERIC":
                de=f"{fmt_num(r.dev_effect)} DEV-IQR"; re=f"{fmt_num(r.ref_effect)} DEV-IQR"
            else:
                de=f"{fmt_num(100*r.dev_effect,1)}pp"; re=f"{fmt_num(100*r.ref_effect,1)}pp"
            out.append(
                f"| {r.feature} | {r.type} | {de} | {re} | {'YES' if r.same_direction else 'NO'} | {fmt_num(r.consistency_score)} |"
            )
        return out

    lines += add_rank("## Formation-time separators",RF)
    lines += add_rank("## Retest-time separators",RR)

    lines += ["","## Strongest consistent numeric quartile examples","",
              "| Feature | Period | Q1 | Q2 | Q3 | Q4 |",
              "|---|---|---:|---:|---:|---:|"]
    topnum=R[(R.type=="NUMERIC")&(R.same_direction)].head(8).feature.tolist()
    for f in topnum:
        for per in ["DEV","REF"]:
            z=Q[(Q.feature==f)&(Q.period==per)].set_index("band")
            if len(z)==4:
                vals=[f"{int(z.loc[b,'survive'])}/{int(z.loc[b,'n'])} ({fmt_pct(z.loc[b,'survival_rate'])})" for b in ["Q1","Q2","Q3","Q4"]]
                lines.append(f"| {f} | {per} | "+" | ".join(vals)+" |")

    lines += ["","## Binary states","",
              "| Feature | Period | False survival | True survival | Δ true-false |",
              "|---|---|---:|---:|---:|"]
    for r in BIN.itertuples(index=False):
        lines.append(
            f"| {r.feature} | {r.period} | {r.false_n} ({fmt_pct(r.survival_false)}) | "
            f"{r.true_n} ({fmt_pct(r.survival_true)}) | {fmt_num(100*r.rate_diff,1)}pp |"
        )

    lines += ["","## Interpretation boundary",
        "S2 reports individual causal descriptors only.",
        "No score, combination, filter, or final Demand Survival Detector is promoted here.",
        "A strong effect at retest time does not prove formation-time zone quality; formation and approach/reaction layers remain separate."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S2_DEMAND_SURVIVAL_CONSUMPTION_ANATOMY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
