#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S4_FROZEN_DIRECTION_DETECTOR_VALIDATION"
S1_SIG="4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6"
S2_SIG="53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2"
S3_SIG="dfcfe845a7547c649defe7f47eeafb356bc2c307c00361b0794a131780e32492"

MAP={
    ("UPPER","C1_CLEAN_REJECTION"):"SHORT",
    ("UPPER","C3_ACCEPTANCE_HOLD"):"LONG",
    ("LOWER","C1_CLEAN_REJECTION"):"LONG",
    ("LOWER","C2_RECLAIM_AFTER_CLOSE"):"LONG",
}
CLASS_ORDER=[
    ("UPPER","C1_CLEAN_REJECTION","SHORT"),
    ("UPPER","C3_ACCEPTANCE_HOLD","LONG"),
    ("LOWER","C1_CLEAN_REJECTION","LONG"),
    ("LOWER","C2_RECLAIM_AFTER_CLOSE","LONG"),
]

def verify_parents():
    f1=(ROOT/"results"/"bnb_b41_s1"/"BNB_B41_S1_CAUSAL_STRUCTURAL_WALL_DISCOVERY_Freeze.txt").read_text(encoding="utf-8")
    f2=(ROOT/"results"/"bnb_b41_s2"/"BNB_B41_S2_WALL_IMPORTANCE_AUDIT_Freeze.txt").read_text(encoding="utf-8")
    f3=(ROOT/"results"/"bnb_b41_s3"/"BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER_Freeze.txt").read_text(encoding="utf-8")
    if f"WALL_SIGNATURE_SHA256={S1_SIG}" not in f1: raise RuntimeError("S1 signature mismatch")
    if f"S2_SIGNATURE_SHA256={S2_SIG}" not in f2: raise RuntimeError("S2 signature mismatch")
    if f"S3_SIGNATURE_SHA256={S3_SIG}" not in f3: raise RuntimeError("S3 signature mismatch")

def aligned(sign, future, origin, wd):
    return sign*(future-origin)/wd

def enrich_event(xb, r):
    if not bool(r.eligible_character):
        return {"direction":"NO_TRADE"}
    side=str(r.side); char=str(r.character)
    direction=MAP.get((side,char),"NO_TRADE")
    out={"direction":direction}
    if direction=="NO_TRADE":
        return out

    day=pd.Timestamp(r.session_day)
    det=pd.Timestamp(r.detector_ts)
    daybars=xb[xb.session_day==day]
    if det not in daybars.index:
        raise RuntimeError(f"detector timestamp missing {det}")
    det_close=float(daybars.loc[det,"close"])
    wd=abs(float(r.level)-float(r.session_open))
    if wd<=0: raise RuntimeError("nonpositive wall distance")

    sign=1.0 if direction=="LONG" else -1.0
    after=daybars[daybars.index>det]
    t60=det+pd.Timedelta(minutes=60)
    t180=det+pd.Timedelta(minutes=180)

    a60=np.nan
    a180=np.nan
    if t60 in daybars.index:
        a60=aligned(sign,float(daybars.loc[t60,"close"]),det_close,wd)
    if t180 in daybars.index:
        a180=aligned(sign,float(daybars.loc[t180,"close"]),det_close,wd)

    if len(after):
        hi=float(after.high.max()); lo=float(after.low.min())
        if direction=="LONG":
            mfe=max(0.0,hi-det_close)/wd
            mae=max(0.0,det_close-lo)/wd
        else:
            mfe=max(0.0,det_close-lo)/wd
            mae=max(0.0,hi-det_close)/wd
        session_close_aligned=aligned(sign,float(daybars.close.iloc[-1]),det_close,wd)
    else:
        mfe=mae=session_close_aligned=np.nan

    out.update({
        "detector_close":det_close,
        "wall_distance":wd,
        "aligned60":a60,
        "aligned180":a180,
        "hit60":bool(np.isfinite(a60) and a60>0),
        "hit180":bool(np.isfinite(a180) and a180>0),
        "mfe_post":mfe,
        "mae_post":mae,
        "favorable_dominance":bool(np.isfinite(mfe) and np.isfinite(mae) and mfe>mae),
        "session_close_aligned":session_close_aligned,
    })
    return out

def summarize(q, label_cols):
    rows=[]
    groups=q.groupby(label_cols,dropna=False,sort=False)
    for key,z in groups:
        if not isinstance(key,tuple): key=(key,)
        row={c:v for c,v in zip(label_cols,key)}
        row.update({
            "n":int(len(z)),
            "n60":int(z.aligned60.notna().sum()),
            "median60":float(z.aligned60.median()) if z.aligned60.notna().any() else np.nan,
            "hit60_rate":float(z.loc[z.aligned60.notna(),"hit60"].mean()) if z.aligned60.notna().any() else np.nan,
            "n180":int(z.aligned180.notna().sum()),
            "median180":float(z.aligned180.median()) if z.aligned180.notna().any() else np.nan,
            "hit180_rate":float(z.loc[z.aligned180.notna(),"hit180"].mean()) if z.aligned180.notna().any() else np.nan,
            "median_mfe":float(z.mfe_post.median()) if z.mfe_post.notna().any() else np.nan,
            "median_mae":float(z.mae_post.median()) if z.mae_post.notna().any() else np.nan,
            "favorable_dominance_rate":float(z.favorable_dominance.mean()) if len(z) else np.nan,
            "median_session_close_aligned":float(z.session_close_aligned.median()) if z.session_close_aligned.notna().any() else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    verify_parents()
    L=pd.read_csv(
        ROOT/"results"/"bnb_b41_s3"/"BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER_Ledger.csv.gz",
        compression="gzip",parse_dates=["session_day","first_touch_ts","detector_ts"]
    )
    if len(L)!=712:
        raise RuntimeError(f"S3 ledger parity drift: {len(L)}")
    elig=L[L.eligible_character].copy()
    if len(elig)!=708:
        raise RuntimeError(f"S3 eligible parity drift: {len(elig)}")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)

    extra=[]
    for r in L.itertuples(index=False):
        extra.append(enrich_event(xb,r))
    X=pd.concat([L.reset_index(drop=True),pd.DataFrame(extra)],axis=1)
    X["signal"]=X.direction.isin(["LONG","SHORT"])
    S=X[X.signal].copy()

    expected_signal=sum(
        len(elig[(elig.side==side)&(elig.character==char)])
        for side,char,_ in CLASS_ORDER
    )
    if len(S)!=expected_signal:
        raise RuntimeError(f"signal parity {len(S)} != {expected_signal}")

    class_rows=[]
    for period in ["DEV","REF","ALL"]:
        p=S if period=="ALL" else S[S.period==period]
        for side,char,direction in CLASS_ORDER:
            z=p[(p.side==side)&(p.character==char)&(p.direction==direction)]
            if len(z)==0:
                class_rows.append({"period":period,"side":side,"character":char,"direction":direction,"n":0})
                continue
            ss=summarize(z.assign(_g="x"),["_g"]).iloc[0].to_dict()
            ss.pop("_g",None)
            class_rows.append({"period":period,"side":side,"character":char,"direction":direction,**ss})
    C=pd.DataFrame(class_rows)

    pooled=[]
    for period in ["DEV","REF","ALL"]:
        z=S if period=="ALL" else S[S.period==period]
        ss=summarize(z.assign(_g="x"),["_g"]).iloc[0].to_dict()
        ss.pop("_g",None)
        eligible_n=len(elig) if period=="ALL" else len(elig[elig.period==period])
        pooled.append({
            "period":period,
            "eligible_character_n":eligible_n,
            "signal_n":len(z),
            "signal_coverage":len(z)/eligible_n if eligible_n else np.nan,
            "long_n":int((z.direction=="LONG").sum()),
            "short_n":int((z.direction=="SHORT").sum()),
            **ss
        })
    P=pd.DataFrame(pooled)

    years=[]
    for y in [2022,2023,2024,2025,2026]:
        z=S[S.year==y]
        ss=summarize(z.assign(_g="x"),["_g"]).iloc[0].to_dict() if len(z) else {}
        ss.pop("_g",None)
        years.append({"year":y,"signal_n":len(z),**ss})
    Y=pd.DataFrame(years)

    support=[]
    for side,char,direction in CLASS_ORDER:
        checks=[]
        row={"side":side,"character":char,"direction":direction}
        for period in ["DEV","REF"]:
            z=C[(C.period==period)&(C.side==side)&(C.character==char)&(C.direction==direction)].iloc[0]
            ok=bool(
                z.n180>=20 and
                z.median180>0 and
                z.hit180_rate>0.50 and
                z.favorable_dominance_rate>0.50
            )
            checks.append(ok)
            row[f"{period.lower()}_n180"]=int(z.n180)
            row[f"{period.lower()}_med180"]=float(z.median180)
            row[f"{period.lower()}_hit180"]=float(z.hit180_rate)
            row[f"{period.lower()}_favdom"]=float(z.favorable_dominance_rate)
        row["direction_supported"]=bool(all(checks))
        support.append(row)
    G=pd.DataFrame(support)

    pooled_ok=True
    for period in ["DEV","REF"]:
        z=P[P.period==period].iloc[0]
        pooled_ok=pooled_ok and bool(z.n180>=20 and z.median180>0 and z.hit180_rate>0.50)
    annual_positive=int(((Y.n180>=1)&(Y.median180>0)).sum())
    all_classes=bool(G.direction_supported.all())
    ready=bool(all_classes and pooled_ok and annual_positive>=4)
    status="BNB_B41_S4_READY_FOR_ENTRY_DISCOVERY" if ready else "BNB_B41_S4_DIRECTION_MAP_NOT_READY"

    sig=hashlib.sha256(json.dumps({
        "parent_s1":S1_SIG,"parent_s2":S2_SIG,"parent_s3":S3_SIG,
        "direction_map":{
            "UPPER_C1":"SHORT",
            "UPPER_C3":"LONG",
            "LOWER_C1":"LONG",
            "LOWER_C2":"LONG",
            "OTHER":"NO_TRADE",
        },
        "origin":"DETECTOR_THIRD_5M_CLOSE",
        "normalization":"ABS_Q80_WALL_MINUS_SESSION_OPEN",
        "horizons":[60,180],
        "support":{
            "n180_min_each_period":20,
            "median180":">0",
            "hit180":">0.5",
            "favorable_dominance":">0.5",
            "annual_positive_min":4,
        },
        "entry_sl_tp_pnl":False,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    X.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    C.to_csv(ROOT/f"{PFX}_ByClass.csv",index=False)
    P.to_csv(ROOT/f"{PFX}_Pooled.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    G.to_csv(ROOT/f"{PFX}_Support.csv",index=False)

    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S1_SIGNATURE_SHA256={S1_SIG}\n"
        f"PARENT_S2_SIGNATURE_SHA256={S2_SIG}\n"
        f"PARENT_S3_SIGNATURE_SHA256={S3_SIG}\n"
        f"S4_SIGNATURE_SHA256={sig}\n"
        "UPPER_C1=SHORT\nUPPER_C3=LONG\nLOWER_C1=LONG\nLOWER_C2=LONG\nOTHER=NO_TRADE\n"
        "OUTCOME_ORIGIN=DETECTOR_CLOSE\n"
        "NO_ENTRY_SL_TP_PNL=TRUE\n",
        encoding="utf-8"
    )
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"

    lines=[
        "# BNB B41-S4 — Frozen Direction Detector Validation","",
        f"**Status: {status}**","",
        f"S4 signature: `{sig}`","",
        "All price movement below is measured from the detector close, after the 15m character is fully known.","",
        "## Frozen directional classes","",
        "| Period | Wall side | Character | Direction | N | N180 | 60m | Hit60 | 180m | Hit180 | MFE | MAE | Fav dominance | Session close |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in C.itertuples(index=False):
        if r.n==0:
            continue
        lines.append(
            f"| {r.period} | {r.side} | {r.character} | {r.direction} | {r.n} | {r.n180} | "
            f"{num(r.median60)} | {pct(r.hit60_rate)} | {num(r.median180)} | {pct(r.hit180_rate)} | "
            f"{num(r.median_mfe)} | {num(r.median_mae)} | {pct(r.favorable_dominance_rate)} | {num(r.median_session_close_aligned)} |"
        )

    lines += ["","## Preregistered class support","",
        "| Side | Character | Dir | DEV N180 | REF N180 | DEV 180m | REF 180m | DEV hit | REF hit | DEV fav-dom | REF fav-dom | Supported |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in G.itertuples(index=False):
        lines.append(
            f"| {r.side} | {r.character} | {r.direction} | {r.dev_n180} | {r.ref_n180} | "
            f"{num(r.dev_med180)} | {num(r.ref_med180)} | {pct(r.dev_hit180)} | {pct(r.ref_hit180)} | "
            f"{pct(r.dev_favdom)} | {pct(r.ref_favdom)} | {'YES' if r.direction_supported else 'NO'} |"
        )

    lines += ["","## Pooled detector","",
        "| Period | Eligible chars | Signals | Coverage | LONG | SHORT | N180 | 180m | Hit180 | MFE | MAE | Fav dominance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in P.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.eligible_character_n} | {r.signal_n} | {pct(r.signal_coverage)} | {r.long_n} | {r.short_n} | "
            f"{r.n180} | {num(r.median180)} | {pct(r.hit180_rate)} | {num(r.median_mfe)} | {num(r.median_mae)} | {pct(r.favorable_dominance_rate)} |"
        )

    lines += ["","## Annual pooled direction","",
        "| Year | Signals | N180 | 180m | Hit180 | Fav dominance |",
        "|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.signal_n} | {r.n180} | {num(r.median180)} | {pct(r.hit180_rate)} | {pct(r.favorable_dominance_rate)} |"
        )

    lines += ["","## Gate",
        f"- All four directional classes supported: **{'YES' if all_classes else 'NO'}**.",
        f"- Pooled DEV/REF support: **{'YES' if pooled_ok else 'NO'}**.",
        f"- Positive annual median 180m: **{annual_positive}/5** years.",
        f"- Final S4 gate: **{'READY FOR B41-S5 ENTRY GEOMETRY' if ready else 'NOT READY — do not proceed to entry optimization'}**.",
        "",
        "S4 remains direction-only; no entry, SL, TP, WR, PF, expectancy, or PnL was optimized."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
