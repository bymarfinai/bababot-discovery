#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B32_S1_SPECIFIC_PRICE_ACTION_LIBRARY"
START=b31.START; END=b31.END
YEARS=b31.YEARS
CD=pd.Timedelta(minutes=90)
BAR15=b31.BAR15
DETECTORS=[
("S01","LIQUIDITY_SWEEP_DISPLACEMENT_LONG","LONG"),
("S02","IMPULSE_HL_READY_LONG","LONG"),
("S03","COMPRESSION_BREAK_RETEST_LONG","LONG"),
("S04","FAILED_BREAK_DISPLACEMENT_LONG","LONG"),
("S05","LIQUIDITY_SWEEP_DISPLACEMENT_SHORT","SHORT"),
("S06","IMPULSE_LH_READY_SHORT","SHORT"),
("S07","COMPRESSION_BREAK_RETEST_SHORT","SHORT"),
("S08","FAILED_BREAK_DISPLACEMENT_SHORT","SHORT"),
]

def body_ratio(r):
    rng=float(r.high-r.low)
    return 0.0 if rng<=0 else abs(float(r.close-r.open))/rng

def close_loc(r):
    rng=float(r.high-r.low)
    return 0.0 if rng<=0 else ((float(r.close-r.low)-float(r.high-r.close))/rng)

def bull_disp(r):
    return r.close>r.open and body_ratio(r)>=.55 and close_loc(r)>=.50

def bear_disp(r):
    return r.close<r.open and body_ratio(r)>=.55 and close_loc(r)<=-.50

def compression3(b,i):
    if i<3:return False
    q=b.iloc[i-3:i]
    tr=(q.high-q.low).to_numpy(float)
    return tr[1]<=tr[0] and tr[2]<=tr[1] and tr[2]<=.75*tr[0]

def cooldown(df):
    out=[]; last={}
    for r in df.sort_values(["event_ts","structure_id"]).itertuples(index=False):
        p=last.get(r.structure_id)
        if p is None or r.event_ts-p>=CD:
            out.append(r); last[r.structure_id]=r.event_ts
    return pd.DataFrame(out,columns=df.columns)

def pivots(b):
    return b31.pivots(b)

def detect(b):
    ph,pl=pivots(b)
    hc={}; lc={}
    for z in ph: hc.setdefault(z[0],[]).append(z)
    for z in pl: lc.setdefault(z[0],[]).append(z)
    ah=[]; al=[]; rows=[]
    names={i:(n,d) for i,n,d in DETECTORS}
    pending_sweep_long=[]; pending_sweep_short=[]
    pending_break_long=[]; pending_break_short=[]
    pending_fail_long=[]; pending_fail_short=[]
    prev_close=None
    tr_med=(b.high-b.low).rolling(16,min_periods=16).median()
    idx=list(b.index)
    for i,(t,r) in enumerate(b.iterrows()):
        last_hi=ah[-1] if ah else None; last_lo=al[-1] if al else None

        # mature one-bar sweep displacement windows
        for rec in list(pending_sweep_long):
            sweep_i,level,mid=rec
            if i-sweep_i>1: pending_sweep_long.remove(rec)
            elif i>=sweep_i and bull_disp(r) and r.close>mid:
                rows.append((t,"S01",names["S01"][0],names["S01"][1],level))
                pending_sweep_long.remove(rec)
        for rec in list(pending_sweep_short):
            sweep_i,level,mid=rec
            if i-sweep_i>1: pending_sweep_short.remove(rec)
            elif i>=sweep_i and bear_disp(r) and r.close<mid:
                rows.append((t,"S05",names["S05"][0],names["S05"][1],level))
                pending_sweep_short.remove(rec)

        # compression break retest windows
        for rec in list(pending_break_long):
            bi,level=rec
            if i-bi>3: pending_break_long.remove(rec)
            elif i>bi and r.low<=level and r.close>level:
                rows.append((t,"S03",names["S03"][0],names["S03"][1],level))
                pending_break_long.remove(rec)
        for rec in list(pending_break_short):
            bi,level=rec
            if i-bi>3: pending_break_short.remove(rec)
            elif i>bi and r.high>=level and r.close<level:
                rows.append((t,"S07",names["S07"][0],names["S07"][1],level))
                pending_break_short.remove(rec)

        # failed-break reclaim then displacement window
        for rec in list(pending_fail_long):
            bi,level,state,reclaim_i=rec
            if i-bi>4: pending_fail_long.remove(rec); continue
            if state=="BROKE" and i>bi and r.close>=level:
                pending_fail_long.remove(rec); pending_fail_long.append((bi,level,"RECLAIMED",i))
                if bull_disp(r) and r.close>level:
                    rows.append((t,"S04",names["S04"][0],names["S04"][1],level))
                    pending_fail_long.remove((bi,level,"RECLAIMED",i))
            elif state=="RECLAIMED":
                if i-reclaim_i>1: pending_fail_long.remove(rec)
                elif i>=reclaim_i and bull_disp(r) and r.close>level:
                    rows.append((t,"S04",names["S04"][0],names["S04"][1],level)); pending_fail_long.remove(rec)

        for rec in list(pending_fail_short):
            bi,level,state,reclaim_i=rec
            if i-bi>4: pending_fail_short.remove(rec); continue
            if state=="BROKE" and i>bi and r.close<=level:
                pending_fail_short.remove(rec); pending_fail_short.append((bi,level,"RECLAIMED",i))
                if bear_disp(r) and r.close<level:
                    rows.append((t,"S08",names["S08"][0],names["S08"][1],level))
                    pending_fail_short.remove((bi,level,"RECLAIMED",i))
            elif state=="RECLAIMED":
                if i-reclaim_i>1: pending_fail_short.remove(rec)
                elif i>=reclaim_i and bear_disp(r) and r.close<level:
                    rows.append((t,"S08",names["S08"][0],names["S08"][1],level)); pending_fail_short.remove(rec)

        if t>=START:
            # initiate sweep structures using only previously confirmed pivot levels
            if last_lo and r.low<last_lo[2] and r.close>=last_lo[2]:
                mid=(float(r.high)+float(r.low))/2.0
                pending_sweep_long.append((i,float(last_lo[2]),mid))
            if last_hi and r.high>last_hi[2] and r.close<=last_hi[2]:
                mid=(float(r.high)+float(r.low))/2.0
                pending_sweep_short.append((i,float(last_hi[2]),mid))

            # compression breakout starts
            if prev_close is not None and last_hi and compression3(b,i) and prev_close<=last_hi[2] and r.close>last_hi[2] and r.close>r.open and body_ratio(r)>=.45:
                pending_break_long.append((i,float(last_hi[2])))
            if prev_close is not None and last_lo and compression3(b,i) and prev_close>=last_lo[2] and r.close<last_lo[2] and r.close<r.open and body_ratio(r)>=.45:
                pending_break_short.append((i,float(last_lo[2])))

            # failed-break starts
            if prev_close is not None and last_lo and prev_close>=last_lo[2] and r.close<last_lo[2]:
                pending_fail_long.append((i,float(last_lo[2]),"BROKE",-1))
            if prev_close is not None and last_hi and prev_close<=last_hi[2] and r.close>last_hi[2]:
                pending_fail_short.append((i,float(last_hi[2]),"BROKE",-1))

        # confirm new pivots only after current-bar structure checks
        newh=hc.get(t,[]); newl=lc.get(t,[])
        for z in newh: ah.append(z)
        for z in newl: al.append(z)

        if t>=START:
            # S02 new confirmed higher low after rising high/low sequence
            for z in newl:
                if len(al)>=2 and len(ah)>=2:
                    prev_l,new_l=al[-2],al[-1]
                    prior_highs=[x for x in ah if prev_l[1] < x[1] < new_l[1]]
                    if prior_highs:
                        last_h=prior_highs[-1]
                        prev_h_candidates=[x for x in ah if x[1]<last_h[1]]
                        if prev_h_candidates:
                            prev_h=prev_h_candidates[-1]
                            amp=last_h[2]-prev_l[2]
                            med=float(tr_med.loc[t]) if pd.notna(tr_med.loc[t]) else np.nan
                            depth=(last_h[2]-new_l[2])/amp if amp>0 else np.nan
                            if new_l[2]>prev_l[2] and last_h[2]>prev_h[2] and np.isfinite(med) and amp>=1.25*med and .25<=depth<=.75:
                                mid=(float(r.high)+float(r.low))/2.0
                                if r.close>=mid:
                                    rows.append((t,"S02",names["S02"][0],names["S02"][1],float(new_l[2])))
            # S06 mirror
            for z in newh:
                if len(ah)>=2 and len(al)>=2:
                    prev_h,new_h=ah[-2],ah[-1]
                    prior_lows=[x for x in al if prev_h[1] < x[1] < new_h[1]]
                    if prior_lows:
                        last_l=prior_lows[-1]
                        prev_l_candidates=[x for x in al if x[1]<last_l[1]]
                        if prev_l_candidates:
                            prev_l=prev_l_candidates[-1]
                            amp=prev_h[2]-last_l[2]
                            med=float(tr_med.loc[t]) if pd.notna(tr_med.loc[t]) else np.nan
                            depth=(new_h[2]-last_l[2])/amp if amp>0 else np.nan
                            if new_h[2]<prev_h[2] and last_l[2]<prev_l[2] and np.isfinite(med) and amp>=1.25*med and .25<=depth<=.75:
                                mid=(float(r.high)+float(r.low))/2.0
                                if r.close<=mid:
                                    rows.append((t,"S06",names["S06"][0],names["S06"][1],float(new_h[2])))
        prev_close=float(r.close)

    e=pd.DataFrame(rows,columns=["event_ts","structure_id","structure","direction","level"])
    if len(e):
        e=e[(e.event_ts>=START)&(e.event_ts<=END)].drop_duplicates(["event_ts","structure_id"])
        e=cooldown(e)
    return e

def summarize(e):
    obs=(END-START)/pd.Timedelta(days=1)
    rows=[]
    for sid,name,direction in DETECTORS:
        z=e[e.structure_id==sid].sort_values("event_ts"); n=len(z)
        cnt={y:int((z.event_ts.dt.year==y).sum()) for y in YEARS}
        eras=sum(v>=12 for v in cnt.values()); mx=max(cnt.values())/n if n else np.nan
        gaps=z.event_ts.diff().dropna()/pd.Timedelta(minutes=1)
        med=float(gaps.median()) if len(gaps) else np.nan
        viable=n>=100 and eras>=4 and mx<=.35 and (np.isnan(med) or med>=90)
        rows.append({"structure_id":sid,"structure":name,"direction":direction,"n":n,
                     **{f"n_{y}":cnt[y] for y in YEARS},
                     "per365":n/obs*365,"median_gap_min":med,"eras_ge12":eras,"max_era_share":mx,
                     "status":"STRUCTURALLY_VIABLE" if viable else "INSUFFICIENT_STRUCTURE_SAMPLE"})
    return pd.DataFrame(rows)

def overlaps(e):
    sets={sid:set(e.loc[e.structure_id==sid,"event_ts"]) for sid,_,_ in DETECTORS}
    rows=[]
    for i,(a,na,_) in enumerate(DETECTORS):
        for b,nb,_ in DETECTORS[i+1:]:
            inter=len(sets[a]&sets[b]); union=len(sets[a]|sets[b])
            rows.append({"a":a,"structure_a":na,"b":b,"structure_b":nb,"same_ts":inter,"jaccard":inter/union if union else np.nan})
    return pd.DataFrame(rows)

def render(s,diag,ident):
    n=int((s.status=="STRUCTURALLY_VIABLE").sum())
    status="BNB_B32_S1_SPECIFIC_STRUCTURE_LIBRARY_READY" if n else "BNB_B32_S1_NO_VIABLE_SPECIFIC_STRUCTURE"
    L=["# BNB B32-S1 — Specific Price-Action Structure Library Result","",f"**Status: {status}**","",
       "S1 is structure-only. No entry, forward outcome, or economics is evaluated.","","## Integrity",
       f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**, SHA `{diag['sha256']}`",
       f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**, close-location diff **{ident['max_close_location_diff']:.12g}**","",
       "## Census","","| ID | Structure | Side | N | 2022 | 2023 | 2024 | 2025 | 2026* | /yr | Med gap | Eras>=12 | Max era | Status |",
       "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in s.itertuples(index=False):
        mg="—" if not np.isfinite(r.median_gap_min) else f"{r.median_gap_min:.0f}m"
        L.append(f"| {r.structure_id} | {r.structure} | {r.direction} | {r.n} | {r.n_2022} | {r.n_2023} | {r.n_2024} | {r.n_2025} | {r.n_2026} | {r.per365:.1f} | {mg} | {r.eras_ge12} | {100*r.max_era_share:.1f}% | {r.status} |")
    L+=["","## Decision",f"**{status}**","",f"Viable specific structures: **{n}/8**.","Only viable structures may advance independently to B32-S2 entry discovery."]
    return "\n".join(L)+"\n",status

def main():
    raw,diag=b31.load_raw(); a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if diag["coverage"]<.995 or ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity failure {diag} {ident}")
    b=b31.bars15(raw); e=detect(b); s=summarize(e); ov=overlaps(e); txt,status=render(s,diag,ident)
    s.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    ov.to_csv(ROOT/f"{PFX}_Overlap.csv",index=False)
    e.to_csv(ROOT/f"{PFX}_Events.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**diag,**ident})+"\n",encoding="utf-8")
    print(txt,flush=True)
if __name__=="__main__": main()
