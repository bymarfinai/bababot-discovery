#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s1_causal_structural_wall_discovery as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S2_WALL_IMPORTANCE_AUDIT"
PARENT_SIG="4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6"

LEVELS=[
    ("MID","UPPER","upper_mid"),
    ("MID","LOWER","lower_mid"),
    ("WALL","UPPER","upper_wall"),
    ("WALL","LOWER","lower_wall"),
    ("EXTREME","UPPER","upper_extreme"),
    ("EXTREME","LOWER","lower_extreme"),
    ("RV1","UPPER","rv1_upper"),
    ("RV1","LOWER","rv1_lower"),
]

def verify_parent():
    p=ROOT/"results"/"bnb_b41_s1"/"BNB_B41_S1_CAUSAL_STRUCTURAL_WALL_DISCOVERY_Freeze.txt"
    txt=p.read_text(encoding="utf-8")
    if f"WALL_SIGNATURE_SHA256={PARENT_SIG}" not in txt:
        raise RuntimeError("B41-S1 parent signature mismatch")

def session_bars(raw):
    x=raw.copy()
    x["session_day"]=(x.index-pd.Timedelta(minutes=5)).floor("D")
    return x

def audit_one(z, level, side, next_level=np.nan):
    wd=abs(level-z.open.iloc[0])
    if not np.isfinite(level) or wd<=0:
        return None
    if side=="UPPER":
        hit=np.flatnonzero(z.high.to_numpy(dtype=float)>=level)
    else:
        hit=np.flatnonzero(z.low.to_numpy(dtype=float)<=level)
    if len(hit)==0:
        return {
            "touched":False,"first_touch_ts":pd.NaT,"minutes_to_touch":np.nan,
            "overshoot_norm":np.nan,"near_extreme25":False,"near_extreme50":False,
            "reaction_norm":np.nan,"close_back_inside":False,"continued_to_next":False,
        }
    i=int(hit[0]); after=z.iloc[i:]
    if side=="UPPER":
        overshoot=max(0.0,float(z.high.max())-level)/wd
        reaction=max(0.0,level-float(after.low.min()))/wd
        close_back=bool(float(z.close.iloc[-1])<level)
        cont=bool(np.isfinite(next_level) and float(z.high.max())>=float(next_level))
    else:
        overshoot=max(0.0,level-float(z.low.min()))/wd
        reaction=max(0.0,float(after.high.max())-level)/wd
        close_back=bool(float(z.close.iloc[-1])>level)
        cont=bool(np.isfinite(next_level) and float(z.low.min())<=float(next_level))
    day=z.session_day.iloc[0]
    touch_interval_start=z.index[i]-pd.Timedelta(minutes=5)
    mins=float((touch_interval_start-day)/pd.Timedelta(minutes=1))
    return {
        "touched":True,
        "first_touch_ts":z.index[i],
        "minutes_to_touch":mins,
        "overshoot_norm":overshoot,
        "near_extreme25":bool(overshoot<=0.25+1e-12),
        "near_extreme50":bool(overshoot<=0.50+1e-12),
        "reaction_norm":reaction,
        "close_back_inside":close_back,
        "continued_to_next":cont,
    }

def summarize(e):
    rows=[]
    for period in ["DEV","REF","ALL"]:
        q=e if period=="ALL" else e[e.period==period]
        sessions=q.session_day.nunique()
        for family,side,_ in LEVELS:
            z=q[(q.family==family)&(q.side==side)]
            t=z[z.touched]
            rows.append({
                "period":period,"family":family,"side":side,
                "sessions":int(sessions),"touch_n":int(len(t)),
                "touch_rate":float(len(t)/sessions) if sessions else np.nan,
                "median_touch_min":float(t.minutes_to_touch.median()) if len(t) else np.nan,
                "median_overshoot_norm":float(t.overshoot_norm.median()) if len(t) else np.nan,
                "near_extreme25_rate":float(t.near_extreme25.mean()) if len(t) else np.nan,
                "near_extreme50_rate":float(t.near_extreme50.mean()) if len(t) else np.nan,
                "median_reaction_norm":float(t.reaction_norm.median()) if len(t) else np.nan,
                "close_back_inside_rate":float(t.close_back_inside.mean()) if len(t) else np.nan,
                "continued_to_next_rate":(
                    float(t.continued_to_next.mean()) if len(t) and family in ["MID","WALL"] else np.nan
                ),
            })
    return pd.DataFrame(rows)

def main():
    verify_parent()
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(diag)
    d=s1.build_daily(raw)
    wm=s1.wall_map(d)
    wm=wm[(wm.index>=s1.START)&(wm.index<=s1.END_DAY)&(wm.hist_n==s1.LOOKBACK)].copy()
    xb=session_bars(raw)
    xb=xb[(xb.session_day>=s1.START)&(xb.session_day<=s1.END_DAY)].copy()

    rows=[]
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=True)}
    for day,r in wm.iterrows():
        if day not in grouped:
            raise RuntimeError(f"missing session bars {day}")
        z=grouped[day]
        for family,side,col in LEVELS:
            level=float(r[col])
            nxt=np.nan
            if family=="MID":
                nxt=float(r["upper_wall" if side=="UPPER" else "lower_wall"])
            elif family=="WALL":
                nxt=float(r["upper_extreme" if side=="UPPER" else "lower_extreme"])
            a=audit_one(z,level,side,nxt)
            rows.append({
                "session_day":day,"year":int(day.year),
                "period":"DEV" if day.year<=2024 else "REF",
                "family":family,"side":side,"level":level,
                "session_open":float(r.session_open),
                **a
            })
    E=pd.DataFrame(rows)

    expected=len(wm)*len(LEVELS)
    if len(E)!=expected:
        raise RuntimeError(f"event parity {len(E)} != {expected}")

    S=summarize(E)

    byyear=[]
    for y in [2022,2023,2024,2025,2026]:
        q=E[E.year==y]
        n_sessions=q.session_day.nunique()
        for family,side,_ in LEVELS:
            z=q[(q.family==family)&(q.side==side)]
            t=z[z.touched]
            byyear.append({
                "year":y,"family":family,"side":side,"sessions":n_sessions,
                "touch_n":len(t),"touch_rate":len(t)/n_sessions if n_sessions else np.nan,
                "median_overshoot_norm":float(t.overshoot_norm.median()) if len(t) else np.nan,
                "near_extreme25_rate":float(t.near_extreme25.mean()) if len(t) else np.nan,
                "median_reaction_norm":float(t.reaction_norm.median()) if len(t) else np.nan,
                "close_back_inside_rate":float(t.close_back_inside.mean()) if len(t) else np.nan,
            })
    Y=pd.DataFrame(byyear)

    support=[]
    for fam in ["WALL","EXTREME","RV1"]:
        for side in ["UPPER","LOWER"]:
            checks=[]
            detail={}
            for per in ["DEV","REF"]:
                base=S[(S.period==per)&(S.family=="MID")&(S.side==side)].iloc[0]
                cur=S[(S.period==per)&(S.family==fam)&(S.side==side)].iloc[0]
                ok=bool(
                    cur.touch_n>=50 and
                    cur.near_extreme25_rate>base.near_extreme25_rate and
                    cur.median_overshoot_norm<base.median_overshoot_norm
                )
                checks.append(ok)
                detail[f"{per.lower()}_n"]=int(cur.touch_n)
                detail[f"{per.lower()}_ne25_delta_pp"]=100.0*float(cur.near_extreme25_rate-base.near_extreme25_rate)
                detail[f"{per.lower()}_overshoot_delta"]=float(cur.median_overshoot_norm-base.median_overshoot_norm)
            support.append({
                "family":fam,"side":side,**detail,
                "decision_point_supported":bool(all(checks))
            })
    A=pd.DataFrame(support)

    wall_supported=bool(
        A[(A.family=="WALL")].decision_point_supported.all()
    )

    sig=hashlib.sha256(json.dumps({
        "parent":PARENT_SIG,
        "touch":"FIRST_5M_HIGH_LOW_CROSS",
        "metrics":["TOUCH_RATE","TOUCH_TIME","OVERSHOOT_NORM","NE25","NE50","REACTION_NORM","CLOSE_BACK_INSIDE","NEXT_LEVEL_CONTINUATION"],
        "thresholds":{"near_extreme":[0.25,0.50],"min_touch_support":50},
        "periods":["DEV_2022_2024","REF_2025_2026"],
        "trading_metrics":False,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    E.to_csv(ROOT/f"{PFX}_EventLedger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    A.to_csv(ROOT/f"{PFX}_ImportanceSupport.csv",index=False)

    status="BNB_B41_S2_WALL_IMPORTANCE_AUDIT_COMPLETE"
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_WALL_SIGNATURE_SHA256={PARENT_SIG}\n"
        f"S2_SIGNATURE_SHA256={sig}\n"
        "S2_TRADING_RULES=PROHIBITED\n"
        "NEAR_EXTREME_THRESHOLDS=0.25,0.50_WALL_DISTANCE\n"
        "IMPORTANCE_BASELINE=MID\n",encoding="utf-8"
    )

    lines=[
        "# BNB B41-S2 — Wall Importance Audit","",
        f"**Status: {status}**","",
        f"Parent wall signature: `{PARENT_SIG}`",
        f"S2 signature: `{sig}`","",
        "S2 is descriptive and non-trading. It measures what happens when the frozen B41-S1 levels are reached.","",
        "## Core audit","",
        "| Period | Family | Side | Touch | Touch rate | Med touch | Med overshoot | NE25 | NE50 | Med reaction | Close inside | Next wall |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        nxt="—" if not np.isfinite(r.continued_to_next_rate) else f"{100*r.continued_to_next_rate:.1f}%"
        lines.append(
            f"| {r.period} | {r.family} | {r.side} | {r.touch_n}/{r.sessions} | {100*r.touch_rate:.1f}% | "
            f"{r.median_touch_min:.0f}m | {r.median_overshoot_norm:.3f}x | {100*r.near_extreme25_rate:.1f}% | "
            f"{100*r.near_extreme50_rate:.1f}% | {r.median_reaction_norm:.3f}x | "
            f"{100*r.close_back_inside_rate:.1f}% | {nxt} |"
        )

    lines += ["","## Preregistered importance support vs MID","",
        "| Family | Side | DEV N | REF N | DEV NE25 Δ | REF NE25 Δ | DEV overshoot Δ | REF overshoot Δ | Supported |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {r.family} | {r.side} | {r.dev_n} | {r.ref_n} | {r.dev_ne25_delta_pp:+.1f}pp | "
            f"{r.ref_ne25_delta_pp:+.1f}pp | {r.dev_overshoot_delta:+.3f}x | {r.ref_overshoot_delta:+.3f}x | "
            f"{'YES' if r.decision_point_supported else 'NO'} |"
        )
    lines += ["","## S2 interpretation boundary",
        f"Q80 WALL both-side decision-point support: **{'YES' if wall_supported else 'NO'}**.",
        "This result does not establish long/short direction or reversal edge.",
        "B41-S3 may use the persisted event ledger to discover interaction character without changing the S1 wall definitions."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
