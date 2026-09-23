#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s1_causal_structural_wall_discovery as s1
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY"
S1_SIG="4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6"
S2_SIG="53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2"
S3_SIG="dfcfe845a7547c649defe7f47eeafb356bc2c307c00361b0794a131780e32492"
S4_SIG="c6eb2c0ade6c4f11c3d9d6512ec06473d5d22c3e2d6c8a75a16a640782d960dc"

TFS=[("TF05",1,5),("TF15",3,15),("TF30",6,30),("TF60",12,60)]
HYPOTHESES=[
    ("UPPER","C1_CLEAN_REJECTION","SHORT"),
    ("UPPER","C3_ACCEPTANCE_HOLD","LONG"),
    ("LOWER","C1_CLEAN_REJECTION","LONG"),
    ("LOWER","C2_RECLAIM_AFTER_CLOSE","LONG"),
]

def verify():
    checks=[
      (ROOT/"results/bnb_b41_s1/BNB_B41_S1_CAUSAL_STRUCTURAL_WALL_DISCOVERY_Freeze.txt","WALL_SIGNATURE_SHA256",S1_SIG),
      (ROOT/"results/bnb_b41_s2/BNB_B41_S2_WALL_IMPORTANCE_AUDIT_Freeze.txt","S2_SIGNATURE_SHA256",S2_SIG),
      (ROOT/"results/bnb_b41_s3/BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER_Freeze.txt","S3_SIGNATURE_SHA256",S3_SIG),
      (ROOT/"results/bnb_b41_s4/BNB_B41_S4_FROZEN_DIRECTION_DETECTOR_VALIDATION_Freeze.txt","S4_SIGNATURE_SHA256",S4_SIG),
    ]
    for p,k,v in checks:
        txt=p.read_text(encoding="utf-8")
        if f"{k}={v}" not in txt:
            raise RuntimeError(f"parent mismatch {p.name}")

def classify(side, closes, level):
    outside=(closes>level) if side=="UPPER" else (closes<level)
    if not outside.any():
        return "C1_CLEAN_REJECTION"
    if not bool(outside[-1]):
        return "C2_RECLAIM_AFTER_CLOSE"
    if len(outside)==1:
        return "C3_ACCEPTANCE_HOLD"
    if bool(outside[-1]) and bool(outside[-2]):
        return "C3_ACCEPTANCE_HOLD"
    return "C4_UNSETTLED_BREAK"

def aligned(direction, future, origin, wd):
    return (future-origin)/wd if direction=="LONG" else (origin-future)/wd

def one_event(daybars, r, tf, nbar, latency):
    touch=pd.Timestamp(r.first_touch_ts)
    if touch not in daybars.index:
        raise RuntimeError(f"missing touch {touch}")
    i=daybars.index.get_loc(touch)
    if not isinstance(i,(int,np.integer)):
        raise RuntimeError("nonunique touch")
    if i+nbar-1>=len(daybars):
        return {"eligible_tf":False,"tf":tf,"latency_min":latency}
    obs=daybars.iloc[i:i+nbar]
    det_ts=obs.index[-1]
    closes=obs.close.to_numpy(float)
    side=str(r.side); level=float(r.level)
    char=classify(side,closes,level)

    direction="NO_TRADE"
    for s,c,d in HYPOTHESES:
        if side==s and char==c:
            direction=d
            break

    out={
        "eligible_tf":True,"tf":tf,"latency_min":latency,
        "detector_ts":det_ts,"detector_close":float(obs.close.iloc[-1]),
        "character":char,"direction":direction,
        "outside_close_count":int(((closes>level) if side=="UPPER" else (closes<level)).sum()),
    }
    if direction=="NO_TRADE":
        return out

    origin=float(obs.close.iloc[-1]); wd=abs(level-float(r.session_open))
    after=daybars[daybars.index>det_ts]
    t60=det_ts+pd.Timedelta(minutes=60)
    t180=det_ts+pd.Timedelta(minutes=180)
    a60=a180=np.nan
    if t60 in daybars.index: a60=aligned(direction,float(daybars.loc[t60,"close"]),origin,wd)
    if t180 in daybars.index: a180=aligned(direction,float(daybars.loc[t180,"close"]),origin,wd)

    if len(after):
        hi=float(after.high.max()); lo=float(after.low.min())
        if direction=="LONG":
            mfe=max(0.0,hi-origin)/wd; mae=max(0.0,origin-lo)/wd
        else:
            mfe=max(0.0,origin-lo)/wd; mae=max(0.0,hi-origin)/wd
    else:
        mfe=mae=np.nan

    out.update({
        "aligned60":a60,"aligned180":a180,
        "hit60":bool(np.isfinite(a60) and a60>0),
        "hit180":bool(np.isfinite(a180) and a180>0),
        "mfe_post":mfe,"mae_post":mae,
        "favorable_dominance":bool(np.isfinite(mfe) and np.isfinite(mae) and mfe>mae),
    })
    return out

def stats(z):
    return {
        "n":len(z),
        "n60":int(z.aligned60.notna().sum()),
        "median60":float(z.aligned60.median()) if z.aligned60.notna().any() else np.nan,
        "hit60":float(z.loc[z.aligned60.notna(),"hit60"].mean()) if z.aligned60.notna().any() else np.nan,
        "n180":int(z.aligned180.notna().sum()),
        "median180":float(z.aligned180.median()) if z.aligned180.notna().any() else np.nan,
        "hit180":float(z.loc[z.aligned180.notna(),"hit180"].mean()) if z.aligned180.notna().any() else np.nan,
        "median_mfe":float(z.mfe_post.median()) if z.mfe_post.notna().any() else np.nan,
        "median_mae":float(z.mae_post.median()) if z.mae_post.notna().any() else np.nan,
        "favdom":float(z.favorable_dominance.mean()) if len(z) else np.nan,
    }

def main():
    verify()
    P=pd.read_csv(ROOT/"results/bnb_b41_s2/BNB_B41_S2_WALL_IMPORTANCE_AUDIT_EventLedger.csv.gz",
                  compression="gzip",parse_dates=["session_day","first_touch_ts"])
    P=P[(P.family=="WALL")&(P.touched)].copy()
    if len(P)!=712: raise RuntimeError(f"S2 wall touch parity {len(P)}")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    for r in P.itertuples(index=False):
        day=pd.Timestamp(r.session_day)
        z=grouped[day]
        for tf,nbar,latency in TFS:
            a=one_event(z,r,tf,nbar,latency)
            rows.append({
                "session_day":day,"year":int(r.year),"period":str(r.period),
                "side":str(r.side),"level":float(r.level),"session_open":float(r.session_open),
                "first_touch_ts":pd.Timestamp(r.first_touch_ts),**a
            })
    E=pd.DataFrame(rows)
    S=E[(E.eligible_tf)&(E.direction.isin(["LONG","SHORT"]))].copy()

    summary=[]
    for period in ["DEV","REF","ALL"]:
        p=S if period=="ALL" else S[S.period==period]
        for side,char,direction in HYPOTHESES:
            for tf,_,latency in TFS:
                z=p[(p.side==side)&(p.character==char)&(p.direction==direction)&(p.tf==tf)]
                row={"period":period,"side":side,"character":char,"direction":direction,"tf":tf,"latency_min":latency}
                if len(z):
                    row.update(stats(z))
                else:
                    row.update({"n":0,"n60":0,"median60":np.nan,"hit60":np.nan,"n180":0,"median180":np.nan,
                                "hit180":np.nan,"median_mfe":np.nan,"median_mae":np.nan,"favdom":np.nan})
                summary.append(row)
    A=pd.DataFrame(summary)

    nominations=[]
    for side,char,direction in HYPOTHESES:
        candidates=[]
        for tf,_,latency in TFS:
            z=A[(A.period=="DEV")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)].iloc[0]
            ok=bool(z.n180>=30 and z.median180>0 and z.hit180>=0.55 and z.favdom>0.50)
            candidates.append((latency,tf,ok,z))
        elig=[x for x in candidates if x[2]]
        if not elig:
            nominations.append({
                "side":side,"character":char,"direction":direction,
                "nom_tf":"NO_NOMINATION","latency_min":np.nan,
                "dev_eligible":False,"ref_validated":False
            })
            continue
        latency,tf,_,d=sorted(elig,key=lambda x:x[0])[0]
        r=A[(A.period=="REF")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)].iloc[0]
        ref_ok=bool(r.n180>=20 and r.median180>0 and r.hit180>0.50 and r.favdom>0.50)
        nominations.append({
            "side":side,"character":char,"direction":direction,"nom_tf":tf,"latency_min":latency,
            "dev_eligible":True,
            "dev_n180":int(d.n180),"dev_med180":float(d.median180),"dev_hit180":float(d.hit180),"dev_favdom":float(d.favdom),
            "ref_n180":int(r.n180),"ref_med180":float(r.median180),"ref_hit180":float(r.hit180),"ref_favdom":float(r.favdom),
            "ref_validated":ref_ok
        })
    N=pd.DataFrame(nominations)

    valid=N[N.ref_validated]
    has_long=bool((valid.direction=="LONG").any())
    has_short=bool((valid.direction=="SHORT").any())
    ready=bool(has_long and has_short)
    status="BNB_B41_S4B_READY_FOR_S5" if ready else "BNB_B41_S4B_NOT_READY_FOR_S5"

    # Pooled nominated detector, using only validated classes and their nominated TF.
    chosen=[]
    for r in N[N.ref_validated].itertuples(index=False):
        chosen.append(S[(S.side==r.side)&(S.character==r.character)&(S.direction==r.direction)&(S.tf==r.nom_tf)].copy())
    V=pd.concat(chosen,ignore_index=True) if chosen else pd.DataFrame(columns=S.columns)
    pooled=[]
    for period in ["DEV","REF","ALL"]:
        z=V if period=="ALL" else V[V.period==period]
        row={"period":period,"n":len(z)}
        if len(z): row.update(stats(z))
        pooled.append(row)
    PO=pd.DataFrame(pooled)

    yearly=[]
    for y in [2022,2023,2024,2025,2026]:
        z=V[V.year==y]
        row={"year":y,"n":len(z)}
        if len(z): row.update(stats(z))
        yearly.append(row)
    Y=pd.DataFrame(yearly)

    sig=hashlib.sha256(json.dumps({
        "parents":[S1_SIG,S2_SIG,S3_SIG,S4_SIG],
        "event_relative_tf_min":[5,15,30,60],
        "taxonomy":"generalized_S3",
        "hypotheses":["UPPER_C1_SHORT","UPPER_C3_LONG","LOWER_C1_LONG","LOWER_C2_LONG"],
        "dev_nomination":{"n180":30,"median180":">0","hit180":">=0.55","favdom":">0.50","selection":"EARLIEST"},
        "ref_validation":{"n180":20,"median180":">0","hit180":">0.50","favdom":">0.50"},
        "no_entry_sl_tp_pnl":True,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_TF_Summary.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    PO.to_csv(ROOT/f"{PFX}_ValidatedPooled.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ValidatedByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S4_SIGNATURE_SHA256={S4_SIG}\nS4B_SIGNATURE_SHA256={sig}\n"
        "TFS=5M,15M,30M,60M\nSELECTION=DEV_ONLY_EARLIEST_ELIGIBLE\nREF=HOLDOUT_ONLY\n"
        "NO_ENTRY_SL_TP_PNL=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"

    lines=[
        "# BNB B41-S4B — Multi-Timeframe Direction Timing Anatomy","",
        f"**Status: {status}**","",f"S4B signature: `{sig}`","",
        "Timeframes are event-relative 5m/15m/30m/60m interaction horizons. Candidate timing is nominated on DEV only; REF is holdout validation.","",
        "## Multi-timeframe anatomy","",
        "| Period | Side | Character | Dir | TF | N180 | 60m | Hit60 | 180m | Hit180 | MFE | MAE | Fav-dom |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        if r.n==0: continue
        lines.append(
            f"| {r.period} | {r.side} | {r.character} | {r.direction} | {r.tf} | {r.n180} | "
            f"{num(r.median60)} | {pct(r.hit60)} | {num(r.median180)} | {pct(r.hit180)} | "
            f"{num(r.median_mfe)} | {num(r.median_mae)} | {pct(r.favdom)} |"
        )

    lines += ["","## DEV-only nominations -> REF holdout","",
        "| Side | Character | Dir | Nom TF | DEV N180 | DEV 180m | DEV hit | DEV fav-dom | REF N180 | REF 180m | REF hit | REF fav-dom | Validated |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in N.itertuples(index=False):
        if r.nom_tf=="NO_NOMINATION":
            lines.append(f"| {r.side} | {r.character} | {r.direction} | NO_NOMINATION | — | — | — | — | — | — | — | — | NO |")
        else:
            lines.append(
                f"| {r.side} | {r.character} | {r.direction} | {r.nom_tf} | {r.dev_n180} | {num(r.dev_med180)} | "
                f"{pct(r.dev_hit180)} | {pct(r.dev_favdom)} | {r.ref_n180} | {num(r.ref_med180)} | "
                f"{pct(r.ref_hit180)} | {pct(r.ref_favdom)} | {'YES' if r.ref_validated else 'NO'} |"
            )

    lines += ["","## Validated-class pooled detector","",
        "| Period | N | N180 | 180m | Hit180 | MFE | MAE | Fav-dom |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in PO.itertuples(index=False):
        if r.n:
            lines.append(f"| {r.period} | {r.n} | {r.n180} | {num(r.median180)} | {pct(r.hit180)} | {num(r.median_mfe)} | {num(r.median_mae)} | {pct(r.favdom)} |")
        else:
            lines.append(f"| {r.period} | 0 | — | — | — | — | — | — |")

    lines += ["","## Gate",
        f"- REF-validated LONG class exists: **{'YES' if has_long else 'NO'}**.",
        f"- REF-validated SHORT class exists: **{'YES' if has_short else 'NO'}**.",
        f"- Final S4B gate: **{'READY FOR B41-S5 ENTRY GEOMETRY' if ready else 'NOT READY FOR S5'}**.",
        "",
        "No entry, stop, target, trade WR, PF, expectancy, or PnL was optimized."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
