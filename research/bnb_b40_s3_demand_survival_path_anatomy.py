#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY"
SRC=ROOT/"results/bnb_b40_s1/BNB_B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE_CandidateLedger.csv.gz"

DECISIONS=["TOUCH_CLOSE","PLUS5_CLOSE","PLUS15_CLOSE"]

NUM_BY_DECISION={
    "TOUCH_CLOSE":[
        "touch_penetration_zone_r","touch_floor_sweep_depth_zone_r",
        "touch_close_vs_zone_high_zone_r","touch_close_vs_floor_zone_r",
        "touch_recovery_from_low_event_r","touch_lower_wick_event_r",
        "touch_upper_wick_event_r","touch_body_event_r","touch_range_event_r",
        "touch_close_location_in_candle",
    ],
    "PLUS5_CLOSE":[
        "p5_close_r","p5_high_r","p5_low_r","p5_body_r","p5_range_r",
        "p5_recovery_from_low_r","p5_close_location","p5_close_vs_zone_high_zone_r",
    ],
    "PLUS15_CLOSE":[
        "p15_close_r","p15_high_r","p15_low_r","p15_body_r","p15_range_r",
        "p15_close_location","p15_green_rate","p15_close_slope_r_per_bar",
        "p15_path_efficiency","p15_min_close_r","p15_max_close_r",
        "p15_close_above_anchor_rate","p15_close_above_zone_rate",
    ],
}

BIN_BY_DECISION={
    "TOUCH_CLOSE":["TOUCH_CLOSE_ABOVE_ZONE","TOUCH_BULLISH","TOUCH_SWEEP_FLOOR_RECLAIM"],
    "PLUS5_CLOSE":[
        "CLOSE5_ABOVE_ANCHOR","CLOSE5_ABOVE_ZONE","CLOSE5_BREAK_TOUCH_HIGH",
        "CLOSE5_BULLISH","LOW5_HOLDS_TOUCH_LOW","RETEST5_ZONE_RECLAIM",
    ],
    "PLUS15_CLOSE":[
        "CLOSE15_ABOVE_ANCHOR","CLOSE15_ABOVE_ZONE","CLOSE15_BREAK_TOUCH_HIGH",
        "ALL3_CLOSES_ABOVE_ANCHOR","ALL3_CLOSES_ABOVE_ZONE",
        "RECLAIM_ZONE_THEN_HOLD","BREAK_TOUCH_HIGH_WITHIN15",
    ],
}

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def close_location(o,h,l,c):
    rng=float(h-l)
    return float((c-l)/rng) if rng>0 else np.nan

def as_bool(s):
    if s.dtype==bool:
        return s
    return s.astype(str).str.lower().map({"true":True,"false":False,"1":True,"0":False})

def load_parent():
    L=pd.read_csv(SRC,compression="gzip")
    for c in [
        "activation_ts","first_retest_ts","survival_resolution_ts","consumption_ts",
        "seed_pivot_ts","seed_confirm_ts","base_start_ts","base_end_ts","departure_start_ts"
    ]:
        if c in L.columns:
            L[c]=pd.to_datetime(L[c],utc=True,errors="coerce")
    L["normalizable"]=as_bool(L["normalizable"])
    E=L[L.normalizable & L.survival_status.isin(["SURVIVE","CONSUMED"])].copy()
    E["survived"]=E.survival_status.eq("SURVIVE")

    exp={"DEV":(657,500,157),"REF":(403,309,94)}
    for per,(n,s,c) in exp.items():
        q=E[E.period==per]
        got=(len(q),int(q.survived.sum()),int((~q.survived).sum()))
        if got!=(n,s,c):
            raise RuntimeError(f"B40-S1 parent parity drift {per}: {got} != {(n,s,c)}")
    return L,E

def raw_bars_after(raw5,ts,n):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(ts),side="right"))
    if i0+n>len(raw5):
        return None
    return raw5.iloc[i0:i0+n].copy()

def decision_plus5(raw5,r):
    bars=raw_bars_after(raw5,r.first_retest_ts,1)
    if bars is None:
        return "DECISION_CENSORED",pd.NaT,pd.DataFrame()
    target=float(r.touch_close)+0.5*float(r.event_risk)
    b=bars.iloc[0]
    if float(b.high)>=target:
        return "TOO_FAST_SURVIVE",bars.index[0],bars
    return "ELIGIBLE",bars.index[0],bars

def decision_plus15(raw5,r):
    bars=raw_bars_after(raw5,r.first_retest_ts,3)
    if bars is None:
        return "DECISION_CENSORED",pd.NaT,pd.DataFrame()
    target=float(r.touch_close)+0.5*float(r.event_risk)
    hit_target=bool((bars.high>=target).any())
    consumed_close=bool(float(bars.close.iloc[-1])<float(r.protected_low))
    if hit_target and consumed_close:
        return "AMBIGUOUS_RESOLUTION",bars.index[-1],bars
    if hit_target:
        return "TOO_FAST_SURVIVE",bars.index[-1],bars
    if consumed_close:
        return "TOO_FAST_CONSUMED",bars.index[-1],bars
    return "ELIGIBLE",bars.index[-1],bars

def touch_features(r):
    bw=float(r.base_width)
    risk=float(r.event_risk)
    o=float(r.touch_open); h=float(r.touch_high); l=float(r.touch_low); c=float(r.touch_close)
    zh=float(r.base_high); floor=float(r.protected_low)
    return {
        "touch_penetration_zone_r":(zh-l)/bw,
        "touch_floor_sweep_depth_zone_r":max(0.0,(floor-l)/bw),
        "touch_close_vs_zone_high_zone_r":(c-zh)/bw,
        "touch_close_vs_floor_zone_r":(c-floor)/bw,
        "touch_recovery_from_low_event_r":(c-l)/risk,
        "touch_lower_wick_event_r":(min(o,c)-l)/risk,
        "touch_upper_wick_event_r":(h-max(o,c))/risk,
        "touch_body_event_r":(c-o)/risk,
        "touch_range_event_r":(h-l)/risk,
        "touch_close_location_in_candle":close_location(o,h,l,c),
        "TOUCH_CLOSE_ABOVE_ZONE":bool(c>=zh),
        "TOUCH_BULLISH":bool(c>o),
        "TOUCH_SWEEP_FLOOR_RECLAIM":bool(l<floor and c>=floor),
    }

def plus5_features(bars,r):
    b=bars.iloc[0]
    anchor=float(r.touch_close); risk=float(r.event_risk); bw=float(r.base_width)
    zh=float(r.base_high); th=float(r.touch_high)
    return {
        "p5_close_r":(float(b.close)-anchor)/risk,
        "p5_high_r":(float(b.high)-anchor)/risk,
        "p5_low_r":(float(b.low)-anchor)/risk,
        "p5_body_r":(float(b.close)-float(b.open))/risk,
        "p5_range_r":(float(b.high)-float(b.low))/risk,
        "p5_recovery_from_low_r":(float(b.close)-float(b.low))/risk,
        "p5_close_location":close_location(float(b.open),float(b.high),float(b.low),float(b.close)),
        "p5_close_vs_zone_high_zone_r":(float(b.close)-zh)/bw,
        "CLOSE5_ABOVE_ANCHOR":bool(float(b.close)>=anchor),
        "CLOSE5_ABOVE_ZONE":bool(float(b.close)>=zh),
        "CLOSE5_BREAK_TOUCH_HIGH":bool(float(b.close)>=th),
        "CLOSE5_BULLISH":bool(float(b.close)>float(b.open)),
        "LOW5_HOLDS_TOUCH_LOW":bool(float(b.low)>=float(r.touch_low)),
        "RETEST5_ZONE_RECLAIM":bool(float(b.low)<=zh and float(b.close)>=zh),
    }

def plus15_features(bars,r):
    q=bars.iloc[:3]
    anchor=float(r.touch_close); risk=float(r.event_risk)
    zh=float(r.base_high); th=float(r.touch_high)
    o=float(q.open.iloc[0]); h=float(q.high.max()); l=float(q.low.min()); c=float(q.close.iloc[-1])
    closes=q.close.to_numpy(float)
    x=np.arange(3,dtype=float)
    slope=float(np.polyfit(x,closes,1)[0])/risk
    denom=float(np.abs(np.diff(closes)).sum())
    eff=float((closes[-1]-closes[0])/denom) if denom>0 else np.nan
    above_a=(q.close>=anchor).to_numpy(bool)
    above_z=(q.close>=zh).to_numpy(bool)
    reclaim_hold=False
    for j in [0,1]:
        if bool(above_z[j]) and bool(np.all(above_z[j:])):
            reclaim_hold=True
            break
    return {
        "p15_close_r":(c-anchor)/risk,
        "p15_high_r":(h-anchor)/risk,
        "p15_low_r":(l-anchor)/risk,
        "p15_body_r":(c-o)/risk,
        "p15_range_r":(h-l)/risk,
        "p15_close_location":close_location(o,h,l,c),
        "p15_green_rate":float((q.close>q.open).mean()),
        "p15_close_slope_r_per_bar":slope,
        "p15_path_efficiency":eff,
        "p15_min_close_r":float((q.close.min()-anchor)/risk),
        "p15_max_close_r":float((q.close.max()-anchor)/risk),
        "p15_close_above_anchor_rate":float(above_a.mean()),
        "p15_close_above_zone_rate":float(above_z.mean()),
        "CLOSE15_ABOVE_ANCHOR":bool(c>=anchor),
        "CLOSE15_ABOVE_ZONE":bool(c>=zh),
        "CLOSE15_BREAK_TOUCH_HIGH":bool(c>=th),
        "ALL3_CLOSES_ABOVE_ANCHOR":bool(np.all(above_a)),
        "ALL3_CLOSES_ABOVE_ZONE":bool(np.all(above_z)),
        "RECLAIM_ZONE_THEN_HOLD":bool(reclaim_hold),
        "BREAK_TOUCH_HIGH_WITHIN15":bool(np.any(q.close.to_numpy(float)>=th)),
    }

def touch_state(r):
    return "TOUCH_CLOSE_ABOVE_ZONE" if float(r.touch_close)>=float(r.base_high) else "TOUCH_CLOSE_IN_ZONE"

def p5_state(status,bars,r):
    if status!="ELIGIBLE":
        return status
    b=bars.iloc[0]
    zh=float(r.base_high); floor=float(r.protected_low)
    c=float(b.close); lo=float(b.low)
    if c>=zh:
        return "P5_RECLAIM_ABOVE_ZONE" if lo<=zh else "P5_HOLD_ABOVE_ZONE"
    if c>=floor:
        return "P5_CLOSE_IN_ZONE"
    return "P5_CLOSE_BELOW_FLOOR_EARLY"

def p15_state(status,bars,r):
    if status!="ELIGIBLE":
        return status
    zh=float(r.base_high)
    closes=(bars.close>=zh).to_numpy(bool)
    n=int(closes.sum())
    if n==3:return "P15_ALL3_ABOVE_ZONE"
    if n==0:return "P15_NO_CLOSE_ABOVE_ZONE"
    return "P15_MIXED_ZONE_ACCEPTANCE"

def numeric_effect(q,feature,dev_iqr):
    s=pd.to_numeric(q.loc[q.survived,feature],errors="coerce").dropna()
    c=pd.to_numeric(q.loc[~q.survived,feature],errors="coerce").dropna()
    if not len(s) or not len(c):
        return np.nan,np.nan,np.nan
    sm=float(s.median()); cm=float(c.median())
    eff=(sm-cm)/dev_iqr if np.isfinite(dev_iqr) and dev_iqr>0 else np.nan
    return sm,cm,eff

def binary_effect(q,feature):
    q=q[q[feature].notna()].copy()
    x=q[feature].astype(bool)
    t=q[x]; f=q[~x]
    tr=float(t.survived.mean()) if len(t) else np.nan
    fr=float(f.survived.mean()) if len(f) else np.nan
    return tr,fr,(tr-fr if np.isfinite(tr) and np.isfinite(fr) else np.nan),len(t),len(f)

def band_name(x,c1,c2,c3):
    if not np.isfinite(x):return "NA"
    if x<=c1:return "Q1"
    if x<=c2:return "Q2"
    if x<=c3:return "Q3"
    return "Q4"

def main():
    if not SRC.exists():
        raise RuntimeError(f"missing frozen B40-S1 ledger {SRC}")

    _,E=load_parent()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)
    raw5=raw[["open","high","low","close"]].astype(float)

    rows=[]
    seq=[]

    for r in E.itertuples(index=False):
        tf=touch_features(r)
        base={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "first_retest_ts":r.first_retest_ts,
            "survival_status":r.survival_status,"survived":bool(r.survived),
            "event_risk":float(r.event_risk),"base_width":float(r.base_width),
            "base_low":float(r.base_low),"base_high":float(r.base_high),
            "protected_low":float(r.protected_low),
            "touch_open":float(r.touch_open),"touch_high":float(r.touch_high),
            "touch_low":float(r.touch_low),"touch_close":float(r.touch_close),
            **tf,
        }
        rows.append({**base,"decision":"TOUCH_CLOSE","decision_status":"ELIGIBLE","decision_ts":r.first_retest_ts})

        st5,dt5,b5=decision_plus5(raw5,r)
        rec5={**base,"decision":"PLUS5_CLOSE","decision_status":st5,"decision_ts":dt5}
        if len(b5)>=1:
            rec5.update(plus5_features(b5,r))
        rows.append(rec5)

        st15,dt15,b15=decision_plus15(raw5,r)
        rec15={**base,"decision":"PLUS15_CLOSE","decision_status":st15,"decision_ts":dt15}
        if len(b15)>=3:
            rec15.update(plus15_features(b15,r))
        rows.append(rec15)

        s0=touch_state(r)
        s5=p5_state(st5,b5,r) if len(b5)>=1 else st5
        s15=p15_state(st15,b15,r) if len(b15)>=3 else st15
        seq.append({
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "final_label":r.survival_status,
            "touch_state":s0,"plus5_state":s5,"plus15_state":s15,
            "path_sequence":f"{s0}->{s5}->{s15}->{r.survival_status}",
        })

    L=pd.DataFrame(rows)
    S=pd.DataFrame(seq)

    # Exact parent parity at touch.
    T=L[L.decision=="TOUCH_CLOSE"]
    for per,(n,s,c) in {"DEV":(657,500,157),"REF":(403,309,94)}.items():
        q=T[T.period==per]
        got=(len(q),int(q.survived.sum()),int((~q.survived).sum()))
        if got!=(n,s,c):
            raise RuntimeError(f"TOUCH parent parity drift {per}: {got}")

    # Decision census.
    census=[]
    for dec in DECISIONS:
        for per in ["DEV","REF"]:
            q=L[(L.decision==dec)&(L.period==per)]
            e=q[q.decision_status=="ELIGIBLE"]
            census.append({
                "decision":dec,"period":per,"n":len(q),"eligible":len(e),
                "eligible_survive":int(e.survived.sum()),
                "eligible_consumed":int((~e.survived).sum()),
                "eligible_survival_rate":float(e.survived.mean()) if len(e) else np.nan,
                "too_fast_survive":int((q.decision_status=="TOO_FAST_SURVIVE").sum()),
                "too_fast_consumed":int((q.decision_status=="TOO_FAST_CONSUMED").sum()),
                "ambiguous_resolution":int((q.decision_status=="AMBIGUOUS_RESOLUTION").sum()),
                "decision_censored":int((q.decision_status=="DECISION_CENSORED").sum()),
            })
    C=pd.DataFrame(census)

    comp=[]; cuts=[]; bands=[]; states=[]
    for dec in DECISIONS:
        ddev=L[(L.decision==dec)&(L.period=="DEV")&(L.decision_status=="ELIGIBLE")]

        for f in NUM_BY_DECISION[dec]:
            if f not in ddev.columns: continue
            xd=pd.to_numeric(ddev[f],errors="coerce").dropna()
            iqr=float(xd.quantile(.75)-xd.quantile(.25)) if len(xd) else np.nan
            q25=float(xd.quantile(.25)) if len(xd) else np.nan
            q50=float(xd.quantile(.50)) if len(xd) else np.nan
            q75=float(xd.quantile(.75)) if len(xd) else np.nan
            cuts.append({"decision":dec,"feature":f,"q25":q25,"q50":q50,"q75":q75,"dev_n":len(xd)})

            vals={}
            for per in ["DEV","REF"]:
                q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")]
                sm,cm,eff=numeric_effect(q,f,iqr)
                vals[per]=(sm,cm,eff,int(pd.to_numeric(q[f],errors="coerce").notna().sum()))
            de=vals["DEV"][2]; re=vals["REF"][2]
            consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            comp.append({
                "decision":dec,"feature":f,"feature_type":"NUMERIC",
                "dev_survive":vals["DEV"][0],"dev_consumed":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3],
                "ref_survive":vals["REF"][0],"ref_consumed":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3],
                "direction_consistent":consistent,
                "robust_score":min(abs(de),abs(re)) if consistent else 0.0,
            })

            if all(np.isfinite([q25,q50,q75])) and q25<q50<q75:
                for per in ["DEV","REF"]:
                    q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")].copy()
                    q["_x"]=pd.to_numeric(q[f],errors="coerce")
                    q=q[np.isfinite(q._x)].copy()
                    q["band"]=[band_name(float(v),q25,q50,q75) for v in q._x]
                    for band in ["Q1","Q2","Q3","Q4"]:
                        z=q[q.band==band]
                        if len(z):
                            bands.append({
                                "decision":dec,"feature":f,"period":per,"band":band,
                                "n":len(z),"survive":int(z.survived.sum()),
                                "survival_rate":float(z.survived.mean()),
                            })

        for f in BIN_BY_DECISION[dec]:
            vals={}
            for per in ["DEV","REF"]:
                q=L[(L.decision==dec)&(L.period==per)&(L.decision_status=="ELIGIBLE")]
                tr,fr,diff,tn,fn=binary_effect(q,f)
                vals[per]=(tr,fr,diff,tn,fn)
                states.append({
                    "decision":dec,"feature":f,"period":per,
                    "true_n":tn,"false_n":fn,
                    "survival_true":tr,"survival_false":fr,"rate_diff":diff,
                })
            de=vals["DEV"][2]; re=vals["REF"][2]
            consistent=bool(np.isfinite(de) and np.isfinite(re) and de!=0 and re!=0 and np.sign(de)==np.sign(re))
            comp.append({
                "decision":dec,"feature":f,"feature_type":"BINARY",
                "dev_survive":vals["DEV"][0],"dev_consumed":vals["DEV"][1],"dev_effect":de,"dev_n":vals["DEV"][3]+vals["DEV"][4],
                "ref_survive":vals["REF"][0],"ref_consumed":vals["REF"][1],"ref_effect":re,"ref_n":vals["REF"][3]+vals["REF"][4],
                "direction_consistent":consistent,
                "robust_score":min(abs(de),abs(re)) if consistent else 0.0,
            })

    FC=pd.DataFrame(comp)
    R=FC.sort_values(["decision","direction_consistent","robust_score"],ascending=[True,False,False]).copy()
    CUT=pd.DataFrame(cuts); B=pd.DataFrame(bands); ST=pd.DataFrame(states)

    # Year audit for top 5 consistent individual features at each decision.
    yrs=[]
    for dec in DECISIONS:
        top=R[(R.decision==dec)&R.direction_consistent].head(5)
        for rr in top.itertuples(index=False):
            if rr.feature_type=="NUMERIC":
                cr=CUT[(CUT.decision==dec)&(CUT.feature==rr.feature)]
                if cr.empty: continue
                cr=cr.iloc[0]
                if not (cr.q25<cr.q50<cr.q75): continue
                for y in [2022,2023,2024,2025,2026]:
                    q=L[(L.decision==dec)&(L.year==y)&(L.decision_status=="ELIGIBLE")].copy()
                    if rr.feature not in q: continue
                    q["_x"]=pd.to_numeric(q[rr.feature],errors="coerce")
                    q=q[np.isfinite(q._x)]
                    q["state"]=[band_name(float(v),cr.q25,cr.q50,cr.q75) for v in q._x]
                    for state,z in q.groupby("state"):
                        yrs.append({
                            "decision":dec,"feature":rr.feature,"feature_type":"NUMERIC",
                            "year":y,"state":state,"n":len(z),
                            "survive":int(z.survived.sum()),"survival_rate":float(z.survived.mean()),
                        })
            else:
                for y in [2022,2023,2024,2025,2026]:
                    q=L[(L.decision==dec)&(L.year==y)&(L.decision_status=="ELIGIBLE")]
                    if rr.feature not in q: continue
                    q=q[q[rr.feature].notna()]
                    for state in [False,True]:
                        z=q[q[rr.feature].astype(bool)==state]
                        if len(z):
                            yrs.append({
                                "decision":dec,"feature":rr.feature,"feature_type":"BINARY",
                                "year":y,"state":str(state),"n":len(z),
                                "survive":int(z.survived.sum()),"survival_rate":float(z.survived.mean()),
                            })
    Y=pd.DataFrame(yrs)

    # Sequence census.
    SC=(S.groupby(["period","touch_state","plus5_state","plus15_state","final_label"])
          .size().reset_index(name="n"))

    L.to_csv(ROOT/f"{PFX}_DecisionLedger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_SequenceLedger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_DecisionCensus.csv",index=False)
    FC.to_csv(ROOT/f"{PFX}_FeatureComparison.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_FeatureRanking.csv",index=False)
    CUT.to_csv(ROOT/f"{PFX}_DevCuts.csv",index=False)
    B.to_csv(ROOT/f"{PFX}_Quartiles.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StateAudit.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_TopFeatureByYear.csv",index=False)
    SC.to_csv(ROOT/f"{PFX}_SequenceCensus.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        "PARENT=B40_S1_DEMAND_SURVIVAL_EXPANSION_UNIVERSE\n"
        "PRIMARY_LABEL=SURVIVE_VS_CONSUMED\n"
        "DECISIONS=TOUCH_CLOSE,PLUS5_CLOSE,PLUS15_CLOSE\n"
        "SURVIVAL_TARGET=PLUS_0_5_EVENT_R\n"
        "CONSUMPTION=15M_CLOSE_BELOW_PROTECTED_LOW\n"
        "PLUS5_GATE=EXCLUDE_ALREADY_REACHED_PLUS_0_5R\n"
        "PLUS15_GATE=EXCLUDE_RESOLVED_SURVIVE_OR_CONSUMED_OR_AMBIGUOUS_WITHIN_FIRST_POST_TOUCH_15M\n"
        "NO_B39_D1_FILTER=TRUE\nNO_COMBINATIONS=TRUE\nNO_PROMOTION=TRUE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B40-S3 — Demand Survival Path Anatomy","",
        "B40-S3 compares SURVIVE vs CONSUMED at three causal checkpoints. No detector is promoted.","",
        "## Decision census","",
        "| Decision | Period | N | Eligible | Survival base | Too-fast survive | Too-fast consumed | Ambiguous |",
        "|---|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.decision} | {r.period} | {r.n} | {r.eligible} | {r.eligible_survive}/{r.eligible} ({fmt_pct(r.eligible_survival_rate)}) | "
            f"{r.too_fast_survive} | {r.too_fast_consumed} | {r.ambiguous_resolution} |"
        )

    for dec in DECISIONS:
        lines += ["",f"## {dec} — strongest consistent individual separators","",
                  "| Feature | Type | DEV effect | REF effect | DEV survive/consumed | REF survive/consumed |",
                  "|---|---|---:|---:|---:|---:|"]
        q=R[(R.decision==dec)&R.direction_consistent].head(12)
        for r in q.itertuples(index=False):
            lines.append(
                f"| {r.feature} | {r.feature_type} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
                f"{fmt_num(r.dev_survive)}/{fmt_num(r.dev_consumed)} | "
                f"{fmt_num(r.ref_survive)}/{fmt_num(r.ref_consumed)} |"
            )

    lines += ["","## Strongest numeric quartile examples","",
              "| Decision | Feature | Period | Q1 | Q2 | Q3 | Q4 |",
              "|---|---|---|---:|---:|---:|---:|"]
    topnum=R[(R.feature_type=="NUMERIC")&R.direction_consistent].groupby("decision",group_keys=False).head(4)
    for rr in topnum.itertuples(index=False):
        for per in ["DEV","REF"]:
            z=B[(B.decision==rr.decision)&(B.feature==rr.feature)&(B.period==per)].set_index("band")
            if len(z)==4:
                vals=[f"{int(z.loc[b,'survive'])}/{int(z.loc[b,'n'])} ({fmt_pct(z.loc[b,'survival_rate'])})" for b in ["Q1","Q2","Q3","Q4"]]
                lines.append(f"| {rr.decision} | {rr.feature} | {per} | "+" | ".join(vals)+" |")

    lines += ["","## Interpretation boundary",
        "S3 identifies where survival/consumption separation first becomes visible.",
        "Resolved outcomes are excluded from later checkpoints rather than credited retrospectively.",
        "No feature combination, score, or final Demand Survival Detector is created in S3."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B40_S3_DEMAND_SURVIVAL_PATH_ANATOMY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
