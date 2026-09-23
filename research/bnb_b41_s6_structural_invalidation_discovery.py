#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6_STRUCTURAL_INVALIDATION_DISCOVERY"
S5_SIG="5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241"

CLASSES=[
    ("UPPER","C1_CLEAN_REJECTION","SHORT","TF05",1),
    ("LOWER","C2_RECLAIM_AFTER_CLOSE","LONG","TF60",12),
]
CANDS=[
    ("D0_WALL_TOUCH","WALL","TOUCH",False),
    ("S1_WALL_CLOSE5","WALL","CLOSE5",True),
    ("S2_WALL_ACCEPT2","WALL","ACCEPT2",True),
    ("S3_WALL_CLOSE15","WALL","CLOSE15",True),
    ("S4_DETECTOR_EXTREME_TOUCH","EXTREME","TOUCH",True),
    ("S5_DETECTOR_EXTREME_CLOSE5","EXTREME","CLOSE5",True),
]
END_MIN=180

def verify_parent():
    txt=(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Freeze.txt").read_text(encoding="utf-8")
    if f"S5_SIGNATURE_SHA256={S5_SIG}" not in txt:
        raise RuntimeError("S5 parent signature mismatch")

def aligned(direction, px, entry, wd):
    return (px-entry)/wd if direction=="LONG" else (entry-px)/wd

def detector_extreme(daybars, det, direction, nbar):
    if det not in daybars.index: raise RuntimeError(f"missing detector {det}")
    i=daybars.index.get_loc(det)
    if not isinstance(i,(int,np.integer)): raise RuntimeError("nonunique detector")
    i0=i-nbar+1
    if i0<0: raise RuntimeError("detector window crosses session start")
    obs=daybars.iloc[i0:i+1]
    return float(obs.low.min()) if direction=="LONG" else float(obs.high.max())

def resolve(daybars, det, endpoint, direction, entry, wd, wall, extreme, candidate, level_name, semantics):
    after=daybars[(daybars.index>det)&(daybars.index<=endpoint)]
    level=wall if level_name=="WALL" else extreme
    outside=lambda c: c<level if direction=="LONG" else c>level

    stop=False; stop_ts=pd.NaT; exit_px=np.nan
    prev_out=False
    for j,(ts,b) in enumerate(after.iterrows()):
        if semantics=="TOUCH":
            hit=float(b.low)<=level if direction=="LONG" else float(b.high)>=level
            if hit:
                stop=True; stop_ts=ts; exit_px=level; break
        elif semantics=="CLOSE5":
            if outside(float(b.close)):
                stop=True; stop_ts=ts; exit_px=float(b.close); break
        elif semantics=="ACCEPT2":
            cur=outside(float(b.close))
            if prev_out and cur:
                stop=True; stop_ts=ts; exit_px=float(b.close); break
            prev_out=cur
        elif semantics=="CLOSE15":
            if ((j+1)%3==0) and outside(float(b.close)):
                stop=True; stop_ts=ts; exit_px=float(b.close); break
        else:
            raise RuntimeError(semantics)

    if stop:
        outcome=aligned(direction,exit_px,entry,wd)
        mins=float((stop_ts-det)/pd.Timedelta(minutes=1))
    else:
        if endpoint not in daybars.index:
            return {"valid180":False,"stop":False,"stop_ts":pd.NaT,"stop_min":np.nan,
                    "exit_price":np.nan,"outcome":np.nan}
        exit_px=float(daybars.loc[endpoint,"close"])
        outcome=aligned(direction,exit_px,entry,wd)
        mins=np.nan

    return {"valid180":True,"stop":stop,"stop_ts":stop_ts,"stop_min":mins,
            "exit_price":exit_px,"outcome":float(outcome)}

def main():
    verify_parent()
    L=pd.read_csv(
        ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
        compression="gzip",parse_dates=["session_day","detector_ts","fill_ts","endpoint_ts"]
    )
    # Frozen final entry is market for both classes.
    L=L[L.candidate=="E0_MARKET"].copy()
    parts=[]
    for side,char,direction,tf,nbar in CLASSES:
        z=L[(L.side==side)&(L.character==char)&(L.direction==direction)&(L.tf==tf)].copy()
        z["nbar"]=nbar
        parts.append(z)
    S=pd.concat(parts,ignore_index=True)
    if len(S)!=305:
        raise RuntimeError(f"S5 market signal parity {len(S)} != 305")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    for r in S.itertuples(index=False):
        day=pd.Timestamp(r.session_day); det=pd.Timestamp(r.detector_ts)
        bars=grouped[day]
        endpoint=det+pd.Timedelta(minutes=END_MIN)
        entry=float(r.detector_close); wall=float(r.wall)
        wd=abs(wall-float(r.session_open))
        extreme=detector_extreme(bars,det,str(r.direction),int(r.nbar))

        baseline=float(r.aligned180) if bool(r.valid180) and np.isfinite(r.aligned180) else np.nan
        for cand,level_name,sem,selectable in CANDS:
            z=resolve(bars,det,endpoint,str(r.direction),entry,wd,wall,extreme,cand,level_name,sem)
            rows.append({
                "signal_key":str(r.signal_key),"session_day":day,"year":int(r.year),"period":str(r.period),
                "side":str(r.side),"character":str(r.character),"direction":str(r.direction),"tf":str(r.tf),
                "entry":entry,"wall":wall,"detector_extreme":extreme,"wall_distance":wd,
                "detector_ts":det,"endpoint_ts":endpoint,
                "baseline_aligned180":baseline,
                "baseline_winner":bool(np.isfinite(baseline) and baseline>0),
                "candidate":cand,"level_name":level_name,"semantics":sem,"selectable":selectable,
                **z
            })
    E=pd.DataFrame(rows)

    def summarize(q):
        q=q[q.valid180 & q.baseline_aligned180.notna()].copy()
        bw=q[q.baseline_winner]
        bl=q[~q.baseline_winner]
        fs=bw[bw.stop]
        lc=bl[bl.stop].copy()
        if len(lc):
            lc["improvement"]=lc.outcome-lc.baseline_aligned180
        return {
            "n180":len(q),
            "baseline_wins":len(bw),"baseline_losers":len(bl),
            "baseline_mean":float(q.baseline_aligned180.mean()) if len(q) else np.nan,
            "baseline_median":float(q.baseline_aligned180.median()) if len(q) else np.nan,
            "baseline_q10":float(q.baseline_aligned180.quantile(.10)) if len(q) else np.nan,
            "stop_n":int(q.stop.sum()),
            "stop_rate":float(q.stop.mean()) if len(q) else np.nan,
            "median_stop_min":float(q.loc[q.stop,"stop_min"].median()) if q.stop.any() else np.nan,
            "false_stop_winners":len(fs),
            "false_stop_rate":len(fs)/len(bw) if len(bw) else np.nan,
            "loser_caught":len(lc),
            "loser_catch_rate":len(lc)/len(bl) if len(bl) else np.nan,
            "median_loser_improvement":float(lc.improvement.median()) if len(lc) else np.nan,
            "mean_outcome":float(q.outcome.mean()) if len(q) else np.nan,
            "median_outcome":float(q.outcome.median()) if len(q) else np.nan,
            "q10_outcome":float(q.outcome.quantile(.10)) if len(q) else np.nan,
            "positive_rate":float((q.outcome>0).mean()) if len(q) else np.nan,
        }

    SUM=[]
    for period in ["DEV","REF","ALL"]:
        p=E if period=="ALL" else E[E.period==period]
        for side,char,direction,tf,_ in CLASSES:
            for cand,_,_,_ in CANDS:
                q=p[(p.side==side)&(p.character==char)&(p.direction==direction)&(p.tf==tf)&(p.candidate==cand)]
                SUM.append({"period":period,"side":side,"character":char,"direction":direction,"tf":tf,
                            "candidate":cand,**summarize(q)})
    A=pd.DataFrame(SUM)

    noms=[]
    for side,char,direction,tf,_ in CLASSES:
        drows=A[(A.period=="DEV")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)]
        elig=[]
        for order,(cand,_,_,selectable) in enumerate(CANDS):
            if not selectable: continue
            z=drows[drows.candidate==cand].iloc[0]
            ok=bool(
                z.n180>=30 and z.false_stop_rate<=0.15 and z.loser_catch_rate>=0.25 and
                np.isfinite(z.median_loser_improvement) and z.median_loser_improvement>0 and
                z.mean_outcome>=z.baseline_mean and z.q10_outcome>z.baseline_q10
            )
            if ok:
                medstop=z.median_stop_min if np.isfinite(z.median_stop_min) else 1e9
                elig.append((medstop,order,cand,z))
        if not elig:
            noms.append({"side":side,"character":char,"direction":direction,"tf":tf,
                         "dev_nomination":"NO_NOMINATION","ref_validated":False})
            continue
        _,_,cand,d=sorted(elig,key=lambda x:(x[0],x[1]))[0]
        r=A[(A.period=="REF")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate==cand)].iloc[0]
        rok=bool(
            r.n180>=20 and r.false_stop_rate<=0.15 and r.loser_catch_rate>=0.25 and
            np.isfinite(r.median_loser_improvement) and r.median_loser_improvement>0 and
            r.mean_outcome>=r.baseline_mean and r.q10_outcome>r.baseline_q10
        )
        noms.append({
            "side":side,"character":char,"direction":direction,"tf":tf,
            "dev_nomination":cand,
            "dev_n180":int(d.n180),"dev_stop_rate":d.stop_rate,"dev_stop_min":d.median_stop_min,
            "dev_false_stop":d.false_stop_rate,"dev_loser_catch":d.loser_catch_rate,
            "dev_loser_improvement":d.median_loser_improvement,
            "dev_mean_delta":d.mean_outcome-d.baseline_mean,"dev_q10_delta":d.q10_outcome-d.baseline_q10,
            "ref_n180":int(r.n180),"ref_stop_rate":r.stop_rate,"ref_stop_min":r.median_stop_min,
            "ref_false_stop":r.false_stop_rate,"ref_loser_catch":r.loser_catch_rate,
            "ref_loser_improvement":r.median_loser_improvement,
            "ref_mean_delta":r.mean_outcome-r.baseline_mean,"ref_q10_delta":r.q10_outcome-r.baseline_q10,
            "ref_validated":rok,
        })
    N=pd.DataFrame(noms)
    ready=bool(len(N)==2 and N.ref_validated.all())
    status="BNB_B41_S6_READY_FOR_S7" if ready else "BNB_B41_S6_STRUCTURAL_INVALIDATION_NOT_READY"

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for side,char,direction,tf,_ in CLASSES:
            for cand,_,_,_ in CANDS:
                q=E[(E.year==y)&(E.side==side)&(E.character==char)&(E.direction==direction)&(E.tf==tf)&(E.candidate==cand)]
                if len(q):
                    Y.append({"year":y,"side":side,"direction":direction,"tf":tf,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    sig=hashlib.sha256(json.dumps({
        "parent":S5_SIG,
        "classes":["UPPER_C1_SHORT_TF05_MARKET","LOWER_C2_LONG_TF60_MARKET"],
        "levels":["Q80_WALL","DETECTOR_EXTREME"],
        "semantics":["WALL_TOUCH_DIAGNOSTIC","WALL_CLOSE5","WALL_ACCEPT2","WALL_CLOSE15","DETECTOR_EXTREME_TOUCH","DETECTOR_EXTREME_CLOSE5"],
        "endpoint":"DETECTOR_PLUS_180M",
        "dev_gate":{"false_stop_max":0.15,"loser_catch_min":0.25,"loser_improvement":">0","mean":">=baseline","q10":">baseline"},
        "selection":"LOWEST_MEDIAN_STOP_TIME",
        "ref_gate":"SAME_AS_DEV_WITH_N180_MIN_20",
        "no_fixed_percent_stop":True,"no_tp":True,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S5_SIGNATURE_SHA256={S5_SIG}\nS6_SIGNATURE_SHA256={sig}\n"
        "LEVELS=Q80_WALL,DETECTOR_EXTREME\n"
        "SEMANTICS=WALL_TOUCH_DIAGNOSTIC,WALL_CLOSE5,WALL_ACCEPT2,WALL_CLOSE15,DETECTOR_EXTREME_TOUCH,DETECTOR_EXTREME_CLOSE5\n"
        "ENDPOINT=DETECTOR_PLUS_180M\nNO_FIXED_PERCENT_STOP=TRUE\nNO_TP=TRUE\n",
        encoding="utf-8"
    )
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"
    lines=[
        "# BNB B41-S6 — Structural Invalidation / SL Discovery","",
        f"**Status: {status}**","",f"S6 signature: `{sig}`","",
        "No fixed-% stop and no TP are used. Baseline is the frozen S5 market entry held to detector+180m.","",
        "## Structural invalidation audit","",
        "| Period | Side | Dir | TF | Candidate | Stops | Stop min | False-stop winners | Loser catch | Med loser improve | Mean Δ vs base | q10 Δ vs base | Positive |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.side} | {r.direction} | {r.tf} | {r.candidate} | {pct(r.stop_rate)} | "
            f"{num(r.median_stop_min)}m | {r.false_stop_winners}/{r.baseline_wins} ({pct(r.false_stop_rate)}) | "
            f"{r.loser_caught}/{r.baseline_losers} ({pct(r.loser_catch_rate)}) | {num(r.median_loser_improvement)} | "
            f"{num(r.mean_outcome-r.baseline_mean)} | {num(r.q10_outcome-r.baseline_q10)} | {pct(r.positive_rate)} |"
        )

    lines += ["","## DEV nomination -> REF holdout","",
        "| Side | Dir | TF | DEV nomination | DEV false-stop | DEV loser catch | DEV improve | DEV mean Δ | DEV q10 Δ | REF false-stop | REF loser catch | REF improve | REF mean Δ | REF q10 Δ | Validated |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in N.itertuples(index=False):
        if r.dev_nomination=="NO_NOMINATION":
            lines.append(f"| {r.side} | {r.direction} | {r.tf} | NO_NOMINATION | — | — | — | — | — | — | — | — | — | — | NO |")
        else:
            lines.append(
                f"| {r.side} | {r.direction} | {r.tf} | {r.dev_nomination} | {pct(r.dev_false_stop)} | "
                f"{pct(r.dev_loser_catch)} | {num(r.dev_loser_improvement)} | {num(r.dev_mean_delta)} | {num(r.dev_q10_delta)} | "
                f"{pct(r.ref_false_stop)} | {pct(r.ref_loser_catch)} | {num(r.ref_loser_improvement)} | "
                f"{num(r.ref_mean_delta)} | {num(r.ref_q10_delta)} | {'YES' if r.ref_validated else 'NO'} |"
            )

    lines += ["","## Gate",
        f"- REF-validated SHORT invalidation: **{'YES' if bool(((N.direction=='SHORT')&N.ref_validated).any()) else 'NO'}**.",
        f"- REF-validated LONG invalidation: **{'YES' if bool(((N.direction=='LONG')&N.ref_validated).any()) else 'NO'}**.",
        f"- Final S6 gate: **{'READY FOR B41-S7 TARGET / TP GEOMETRY' if ready else 'NOT READY FOR S7 — inspect failure anatomy before TP optimization'}**.",
        "",
        "S6 does not optimize TP, trade WR, PF, expectancy, leverage, or PnL."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
