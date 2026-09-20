#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b32_s1_specific_price_action_library as b32

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B33_S1_STRUCTURE_LIFECYCLE"
START=b31.START; END=b31.END; YEARS=b31.YEARS
CD=pd.Timedelta(minutes=90)
DETECTORS=[
("F1LE","LIQUIDITY_SWEEP_LONG_EARLY","LONG","F1","EARLY"),
("F1LM","LIQUIDITY_SWEEP_LONG_MATURE","LONG","F1","MATURE"),
("F2LE","IMPULSE_PULLBACK_LONG_EARLY","LONG","F2","EARLY"),
("F2LM","IMPULSE_HL_LONG_MATURE","LONG","F2","MATURE"),
("F3LE","COMPRESSION_BREAK_LONG_EARLY","LONG","F3","EARLY"),
("F3LM","COMPRESSION_RETEST_LONG_MATURE","LONG","F3","MATURE"),
("F4LE","FAILED_BREAK_LONG_EARLY","LONG","F4","EARLY"),
("F4LM","FAILED_BREAK_LONG_MATURE","LONG","F4","MATURE"),
("F1SE","LIQUIDITY_SWEEP_SHORT_EARLY","SHORT","F1","EARLY"),
("F1SM","LIQUIDITY_SWEEP_SHORT_MATURE","SHORT","F1","MATURE"),
("F2SE","IMPULSE_PULLBACK_SHORT_EARLY","SHORT","F2","EARLY"),
("F2SM","IMPULSE_LH_SHORT_MATURE","SHORT","F2","MATURE"),
("F3SE","COMPRESSION_BREAK_SHORT_EARLY","SHORT","F3","EARLY"),
("F3SM","COMPRESSION_RETEST_SHORT_MATURE","SHORT","F3","MATURE"),
("F4SE","FAILED_BREAK_SHORT_EARLY","SHORT","F4","EARLY"),
("F4SM","FAILED_BREAK_SHORT_MATURE","SHORT","F4","MATURE"),
]
MATURE_MAP={"S01":"F1LM","S02":"F2LM","S03":"F3LM","S04":"F4LM","S05":"F1SM","S06":"F2SM","S07":"F3SM","S08":"F4SM"}
EXPECTED_MATURE={"F1LM":1980,"F2LM":2021,"F3LM":639,"F4LM":2702,"F1SM":1863,"F2SM":1789,"F3SM":548,"F4SM":2637}

def cooldown(df):
    out=[]; last={}
    for r in df.sort_values(["event_ts","detector_id"]).itertuples(index=False):
        p=last.get(r.detector_id)
        if p is None or r.event_ts-p>=CD:
            out.append(r); last[r.detector_id]=r.event_ts
    return pd.DataFrame(out,columns=df.columns)

def prev_pivot(seq,before_ts):
    for x in reversed(seq):
        if x[1] < before_ts:return x
    return None

def detect_early(b):
    ph,pl=b31.pivots(b)
    hc={}; lc={}
    for z in ph:hc.setdefault(z[0],[]).append(z)
    for z in pl:lc.setdefault(z[0],[]).append(z)
    ah=[]; al=[]; rows=[]; prev_close=None
    tr_med=(b.high-b.low).rolling(16,min_periods=16).median()
    pend_fl=[]; pend_fs=[]
    for i,(t,r) in enumerate(b.iterrows()):
        last_hi=ah[-1] if ah else None; last_lo=al[-1] if al else None

        # mature failed-break EARLY reclaim state, using only state already known
        for rec in list(pend_fl):
            bi,level=rec
            if i-bi>3: pend_fl.remove(rec)
            elif i>bi and r.close>=level:
                rows.append((t,"F4LE","FAILED_BREAK_LONG_EARLY","LONG","F4","EARLY",float(level)))
                pend_fl.remove(rec)
        for rec in list(pend_fs):
            bi,level=rec
            if i-bi>3: pend_fs.remove(rec)
            elif i>bi and r.close<=level:
                rows.append((t,"F4SE","FAILED_BREAK_SHORT_EARLY","SHORT","F4","EARLY",float(level)))
                pend_fs.remove(rec)

        if t>=START:
            # F1 EARLY sweep-reclaim
            if last_lo and r.low<last_lo[2] and r.close>=last_lo[2]:
                rows.append((t,"F1LE","LIQUIDITY_SWEEP_LONG_EARLY","LONG","F1","EARLY",float(last_lo[2])))
            if last_hi and r.high>last_hi[2] and r.close<=last_hi[2]:
                rows.append((t,"F1SE","LIQUIDITY_SWEEP_SHORT_EARLY","SHORT","F1","EARLY",float(last_hi[2])))

            # F2 EARLY impulse pullback reaction
            med=float(tr_med.loc[t]) if pd.notna(tr_med.loc[t]) else np.nan
            mid=(float(r.high)+float(r.low))/2.0
            if last_hi is not None:
                prev_hi=prev_pivot(ah,last_hi[1])
                prior_lo=prev_pivot(al,last_hi[1])
                if prev_hi and prior_lo and last_hi[2]>prev_hi[2]:
                    amp=float(last_hi[2]-prior_lo[2])
                    depth=(float(last_hi[2])-float(r.low))/amp if amp>0 else np.nan
                    if np.isfinite(med) and amp>=1.25*med and .25<=depth<=.75 and r.low>prior_lo[2] and r.close>=mid:
                        rows.append((t,"F2LE","IMPULSE_PULLBACK_LONG_EARLY","LONG","F2","EARLY",float(r.low)))
            if last_lo is not None:
                prev_lo=prev_pivot(al,last_lo[1])
                prior_hi=prev_pivot(ah,last_lo[1])
                if prev_lo and prior_hi and last_lo[2]<prev_lo[2]:
                    amp=float(prior_hi[2]-last_lo[2])
                    depth=(float(r.high)-float(last_lo[2]))/amp if amp>0 else np.nan
                    if np.isfinite(med) and amp>=1.25*med and .25<=depth<=.75 and r.high<prior_hi[2] and r.close<=mid:
                        rows.append((t,"F2SE","IMPULSE_PULLBACK_SHORT_EARLY","SHORT","F2","EARLY",float(r.high)))

            # F3 EARLY compression breakout
            if prev_close is not None and last_hi and b32.compression3(b,i) and prev_close<=last_hi[2] and r.close>last_hi[2] and r.close>r.open and b32.body_ratio(r)>=.45:
                rows.append((t,"F3LE","COMPRESSION_BREAK_LONG_EARLY","LONG","F3","EARLY",float(last_hi[2])))
            if prev_close is not None and last_lo and b32.compression3(b,i) and prev_close>=last_lo[2] and r.close<last_lo[2] and r.close<r.open and b32.body_ratio(r)>=.45:
                rows.append((t,"F3SE","COMPRESSION_BREAK_SHORT_EARLY","SHORT","F3","EARLY",float(last_lo[2])))

            # start F4 failed-break state
            if prev_close is not None and last_lo and prev_close>=last_lo[2] and r.close<last_lo[2]:
                pend_fl.append((i,float(last_lo[2])))
            if prev_close is not None and last_hi and prev_close<=last_hi[2] and r.close>last_hi[2]:
                pend_fs.append((i,float(last_hi[2])))

        # pivots confirmed at t become available only after current-t checks
        for z in hc.get(t,[]):ah.append(z)
        for z in lc.get(t,[]):al.append(z)
        prev_close=float(r.close)

    e=pd.DataFrame(rows,columns=["event_ts","detector_id","structure","direction","family","phase","level"])
    if len(e):
        e=e[(e.event_ts>=START)&(e.event_ts<=END)].drop_duplicates(["event_ts","detector_id"])
        e=cooldown(e)
    return e

def mature_from_b32(b):
    q=b32.detect(b).copy()
    meta={x[0]:x for x in DETECTORS}
    rows=[]
    for r in q.itertuples(index=False):
        did=MATURE_MAP[r.structure_id]
        _,name,direction,family,phase=meta[did]
        rows.append((r.event_ts,did,name,direction,family,phase,float(r.level)))
    return pd.DataFrame(rows,columns=["event_ts","detector_id","structure","direction","family","phase","level"])

def detect(b):
    e=pd.concat([detect_early(b),mature_from_b32(b)],ignore_index=True)
    return e.sort_values(["event_ts","detector_id"]).reset_index(drop=True)

def summarize(e):
    obs=(END-START)/pd.Timedelta(days=1); rows=[]
    for did,name,direction,family,phase in DETECTORS:
        z=e[e.detector_id==did].sort_values("event_ts"); n=len(z)
        cnt={y:int((z.event_ts.dt.year==y).sum()) for y in YEARS}
        eras=sum(v>=12 for v in cnt.values()); mx=max(cnt.values())/n if n else np.nan
        gaps=z.event_ts.diff().dropna()/pd.Timedelta(minutes=1)
        med=float(gaps.median()) if len(gaps) else np.nan
        viable=n>=100 and eras>=4 and mx<=.35 and (np.isnan(med) or med>=90)
        rows.append({"detector_id":did,"structure":name,"direction":direction,"family":family,"phase":phase,"n":n,
                     **{f"n_{y}":cnt[y] for y in YEARS},"per365":n/obs*365,"median_gap_min":med,
                     "eras_ge12":eras,"max_era_share":mx,
                     "status":"STRUCTURALLY_VIABLE" if viable else "INSUFFICIENT_STRUCTURE_SAMPLE"})
    return pd.DataFrame(rows)

def overlap(e):
    sets={d:set(e.loc[e.detector_id==d,"event_ts"]) for d,_,_,_,_ in DETECTORS}
    rows=[]
    for i,(a,na,_,fa,pa) in enumerate(DETECTORS):
        for b,nb,_,fb,pb in DETECTORS[i+1:]:
            inter=len(sets[a]&sets[b]); union=len(sets[a]|sets[b])
            if fa==fb or inter:
                rows.append({"a":a,"phase_a":pa,"b":b,"phase_b":pb,"same_ts":inter,"jaccard":inter/union if union else np.nan})
    return pd.DataFrame(rows)

def render(s,diag,ident):
    n=int((s.status=="STRUCTURALLY_VIABLE").sum())
    status="BNB_B33_S1_LIFECYCLE_READY" if n else "BNB_B33_S1_NO_VIABLE_LIFECYCLE_PHASE"
    L=["# BNB B33-S1 — Causal Structure Lifecycle Result","",f"**Status: {status}**","",
       "S1 is structure/lifecycle only. No entry or forward outcome is evaluated.","","## Integrity",
       f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**, SHA `{diag['sha256']}`",
       f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**, close-location diff **{ident['max_close_location_diff']:.12g}**","",
       "## Lifecycle census","","| ID | Family | Phase | Side | N | 2022 | 2023 | 2024 | 2025 | 2026* | /yr | Med gap | Status |",
       "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in s.itertuples(index=False):
        mg="—" if not np.isfinite(r.median_gap_min) else f"{r.median_gap_min:.0f}m"
        L.append(f"| {r.detector_id} | {r.family} | {r.phase} | {r.direction} | {r.n} | {r.n_2022} | {r.n_2023} | {r.n_2024} | {r.n_2025} | {r.n_2026} | {r.per365:.1f} | {mg} | {r.status} |")
    L+=["","## Decision",f"**{status}**","",f"Viable lifecycle detectors: **{n}/16**.",
        "Only viable lifecycle phases may advance to B33-S2 entry discovery."]
    return "\n".join(L)+"\n",status

def main():
    raw,diag=b31.load_raw(); a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if diag["coverage"]<.995 or ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity failure {diag} {ident}")
    b=b31.bars15(raw); e=detect(b)
    counts=e.detector_id.value_counts().to_dict()
    for k,v in EXPECTED_MATURE.items():
        if counts.get(k,0)!=v:raise RuntimeError(f"mature B32 audit failed {k}: {counts.get(k,0)} != {v}")
    s=summarize(e); ov=overlap(e); txt,status=render(s,diag,ident)
    s.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    ov.to_csv(ROOT/f"{PFX}_Overlap.csv",index=False)
    e.to_csv(ROOT/f"{PFX}_Events.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**diag,**ident,"mature_counts":{k:counts.get(k,0) for k in EXPECTED_MATURE}})+"\n",encoding="utf-8")
    print(txt,flush=True)
if __name__=="__main__":main()
