#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b33_s1_structure_lifecycle as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B33_S2_LIFECYCLE_ENTRY"
BAR=b31.BAR5
EPS=1e-12
DEV=[2022,2023,2024]; REF=[2025,2026]
H=[30,60,120]
POLICIES={
"E0":"PHASE_CLOSE","E1":"NATIVE_LEVEL_RETEST","E2":"PHASE_MID_RETEST",
"E3":"PHASE_EXTREME_BREAK","E4":"PULLBACK_RECLAIM","E5":"FOLLOW_THROUGH_DISPLACEMENT",
}

def wilson(h,n,z=1.959963984540054):
    if n<=0:return np.nan
    p=h/n; den=1+z*z/n
    cen=p+z*z/(2*n)
    mar=z*np.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (cen-mar)/den

def body(o,h,l,c):
    r=h-l
    return 0.0 if r<=0 else abs(c-o)/r

def cloc(h,l,c):
    r=h-l
    return 0.0 if r<=0 else ((c-l)-(h-c))/r

def forward(p,side,steps,idx,c):
    if p is None:return np.nan
    e=p+steps
    if e>=len(idx) or idx[e]-idx[p] != steps*BAR:return np.nan
    x=side*(float(c[e])/float(c[p])-1.0)
    return 0.0 if abs(x)<=EPS else x

def entry_positions(ev,pos,raw,b15):
    idx=raw.index
    o=raw.open.to_numpy(float); h=raw.high.to_numpy(float); l=raw.low.to_numpy(float); c=raw.close.to_numpy(float)
    side=1 if ev.direction=="LONG" else -1
    out={k:None for k in POLICIES}; out["E0"]=pos
    if ev.event_ts not in b15.index:return out
    q=b15.loc[ev.event_ts]; ph=float(q.high); pl=float(q.low); mid=(ph+pl)/2.0; level=float(ev.level)
    adverse_ext=None; prev=float(c[pos])
    for j in range(pos+1,min(pos+13,len(idx))):
        if idx[j]-idx[j-1] != BAR:break
        if out["E1"] is None:
            if side==1 and l[j]<=level and c[j]>level:out["E1"]=j
            if side==-1 and h[j]>=level and c[j]<level:out["E1"]=j
        if out["E2"] is None:
            if side==1 and l[j]<=mid and c[j]>mid:out["E2"]=j
            if side==-1 and h[j]>=mid and c[j]<mid:out["E2"]=j
        if out["E3"] is None:
            if side==1 and c[j]>ph:out["E3"]=j
            if side==-1 and c[j]<pl:out["E3"]=j
        adverse=(c[j]<prev-EPS) if side==1 else (c[j]>prev+EPS)
        if adverse:
            adverse_ext=float(h[j] if side==1 else l[j])
        elif out["E4"] is None and adverse_ext is not None:
            if side==1 and c[j]>adverse_ext:out["E4"]=j
            if side==-1 and c[j]<adverse_ext:out["E4"]=j
        if out["E5"] is None:
            br=body(o[j],h[j],l[j],c[j]); loc=cloc(h[j],l[j],c[j])
            if side==1 and c[j]>o[j] and br>=.55 and loc>=.50:out["E5"]=j
            if side==-1 and c[j]<o[j] and br>=.55 and loc<=-.50:out["E5"]=j
        prev=float(c[j])
    return out

def ledger(raw,b15,E):
    idx=raw.index; c=raw.close.to_numpy(float); posmap={t:i for i,t in enumerate(idx)}
    rows=[]
    for ev in E.itertuples(index=False):
        p0=posmap.get(ev.event_ts)
        if p0 is None:continue
        ep=entry_positions(ev,p0,raw,b15); side=1.0 if ev.direction=="LONG" else -1.0
        for pid,pname in POLICIES.items():
            p=ep[pid]
            rec={"phase_ts":ev.event_ts,"detector_id":ev.detector_id,"structure":ev.structure,
                 "direction":ev.direction,"family":ev.family,"phase":ev.phase,"phase_year":int(ev.event_ts.year),
                 "policy_id":pid,"policy":pname,"entry_ts":pd.NaT if p is None else idx[p]}
            for hh in H:
                x=forward(p,side,hh//5,idx,c)
                rec[f"signed_{hh}"]=x
                rec[f"hit_{hh}"]=bool(np.isfinite(x) and x>EPS)
            rows.append(rec)
    return pd.DataFrame(rows)

def metric(z,parent_n,years):
    v=z[z.signed_60.notna()].copy(); n=len(v); hit=int(v.hit_60.sum())
    d={"n":n,"parent_n":parent_n,"participation":n/parent_n if parent_n else np.nan,
       "hit_60":hit/n if n else np.nan,"wilson_60":wilson(hit,n),
       "median_signed_60":float(v.signed_60.median()) if n else np.nan,
       "hit_30":float(v.hit_30.mean()) if n else np.nan,"hit_120":float(v.hit_120.mean()) if n else np.nan}
    for y in years:
        q=v[v.phase_year==y]; d[f"n_{y}"]=len(q); d[f"hit_{y}"]=float(q.hit_60.mean()) if len(q) else np.nan
    return d

def development(L,E,summary):
    rows=[]; meta={x[0]:x for x in s1.DETECTORS}
    viable=set(summary.loc[summary.status=="STRUCTURALLY_VIABLE","detector_id"])
    for did in [x[0] for x in s1.DETECTORS]:
        _,name,direction,family,phase=meta[did]
        parent=E[(E.detector_id==did)&E.event_ts.dt.year.isin(DEV)]
        if did not in viable:
            for pid,pname in POLICIES.items():
                rows.append({"detector_id":did,"structure":name,"direction":direction,"family":family,"phase":phase,
                             "policy_id":pid,"policy":pname,"n":0,"parent_n":len(parent),"participation":np.nan,
                             "hit_60":np.nan,"wilson_60":np.nan,"median_signed_60":np.nan,"hit_30":np.nan,"hit_120":np.nan,
                             "n_2022":0,"hit_2022":np.nan,"n_2023":0,"hit_2023":np.nan,"n_2024":0,"hit_2024":np.nan,
                             "worst_dev_hit":np.nan,"aux_ge53":0,"dev_gate":False})
            continue
        for pid,pname in POLICIES.items():
            z=L[(L.detector_id==did)&(L.policy_id==pid)&L.phase_year.isin(DEV)]
            m=metric(z,len(parent),DEV)
            worst=min(m[f"hit_{y}"] for y in DEV) if all(np.isfinite(m[f"hit_{y}"]) for y in DEV) else np.nan
            aux=sum(np.isfinite(m[f"hit_{hh}"]) and m[f"hit_{hh}"]>=.53 for hh in (30,120))
            gate=(m["n"]>=100 and min(m[f"n_{y}"] for y in DEV)>=25 and m["participation"]>=.25 and
                  m["hit_60"]>=.55 and m["wilson_60"]>.52 and worst>=.52 and m["median_signed_60"]>0 and aux>=1)
            rows.append({"detector_id":did,"structure":name,"direction":direction,"family":family,"phase":phase,
                         "policy_id":pid,"policy":pname,**m,"worst_dev_hit":worst,"aux_ge53":aux,"dev_gate":gate})
    return pd.DataFrame(rows)

def select(D):
    rows=[]
    for did,name,direction,family,phase in s1.DETECTORS:
        q=D[(D.detector_id==did)&D.dev_gate].copy()
        if q.empty:
            rows.append({"detector_id":did,"structure":name,"direction":direction,"family":family,"phase":phase,
                         "selection_status":"NO_ENTRY_FOUND"})
        else:
            q=q.sort_values(["worst_dev_hit","wilson_60","hit_60","participation","policy_id"],
                            ascending=[False,False,False,False,True])
            r=q.iloc[0].to_dict(); r["selection_status"]="SELECTED_FOR_REFERENCE"; rows.append(r)
    return pd.DataFrame(rows)

def reference(L,E,S):
    rows=[]
    for s in S.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE":
            rows.append({"detector_id":s.detector_id,"structure":s.structure,"direction":s.direction,
                         "family":s.family,"phase":s.phase,"status":"NO_ENTRY_FOUND"})
            continue
        parent=E[(E.detector_id==s.detector_id)&E.event_ts.dt.year.isin(REF)]
        z=L[(L.detector_id==s.detector_id)&(L.policy_id==s.policy_id)&L.phase_year.isin(REF)]
        m=metric(z,len(parent),REF)
        aux=sum(np.isfinite(m[f"hit_{hh}"]) and m[f"hit_{hh}"]>=.52 for hh in (30,120))
        gate=(m["n_2025"]>=25 and m["n_2026"]>=15 and m["participation"]>=.25 and
              m["hit_60"]>=.53 and m["hit_2025"]>.50 and m["hit_2026"]>.50 and
              m["wilson_60"]>.50 and m["median_signed_60"]>0 and aux>=1)
        rows.append({"detector_id":s.detector_id,"structure":s.structure,"direction":s.direction,
                     "family":s.family,"phase":s.phase,"policy_id":s.policy_id,"policy":s.policy,
                     **m,"aux_ge52":aux,"status":"PHASE_ENTRY_PASS" if gate else "PHASE_ENTRY_REJECT"})
    return pd.DataFrame(rows)

def pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.2f}%"

def render(S,R,diag,ident):
    n=int((R.status=="PHASE_ENTRY_PASS").sum())
    status="BNB_B33_S2_PHASE_ENTRIES_FOUND" if n else "BNB_B33_S2_NO_ENTRY_PASSED"
    L=["# BNB B33-S2 — Lifecycle-Phase Entry Discovery Result","",f"**Status: {status}**","",
       "B33-S1 lifecycle detectors are frozen. No economics is simulated.","","## Integrity",
       f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**, SHA `{diag['sha256']}`",
       f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**, close-location diff **{ident['max_close_location_diff']:.12g}**","",
       "## Development selection","","| Detector | Family | Phase | Side | Entry | N | Part. | +60 | Wilson | Worst era | Status |",
       "|---|---|---|---|---|---:|---:|---:|---:|---:|---|"]
    for s in S.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE":
            L.append(f"| {s.detector_id} | {s.family} | {s.phase} | {s.direction} | — | — | — | — | — | — | NO_ENTRY_FOUND |")
        else:
            L.append(f"| {s.detector_id} | {s.family} | {s.phase} | {s.direction} | {s.policy_id} {s.policy} | {int(s.n)} | {pct(s.participation)} | {pct(s.hit_60)} | {pct(s.wilson_60)} | {pct(s.worst_dev_hit)} | SELECTED |")
    L+=["","## One-shot reference","","| Detector | Family | Phase | Entry | N | +60 | 2025 | 2026 | +30 | +120 | Status |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in R.itertuples(index=False):
        if r.status=="NO_ENTRY_FOUND":
            L.append(f"| {r.detector_id} | {r.family} | {r.phase} | — | — | — | — | — | — | — | NO_ENTRY_FOUND |")
        else:
            L.append(f"| {r.detector_id} | {r.family} | {r.phase} | {r.policy_id} {r.policy} | {int(r.n)} | {pct(r.hit_60)} | {pct(r.hit_2025)} | {pct(r.hit_2026)} | {pct(r.hit_30)} | {pct(r.hit_120)} | {r.status} |")
    L+=["","## Decision",f"**{status}**","",f"Phase+entry pairs eligible for B33-S3 economics: **{n}/16**."]
    return "\n".join(L)+"\n",status

def main():
    parent_path=ROOT/"results"/"bnb_b33_s1"/"BNB_B33_S1_STRUCTURE_LIFECYCLE_Summary.csv"
    if not parent_path.exists():raise RuntimeError("B33-S1 persisted summary missing")
    parent=pd.read_csv(parent_path)
    raw,diag=b31.load_raw(); a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if diag["coverage"]<.995 or ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity failure {diag} {ident}")
    b15=b31.bars15(raw); E=s1.detect(b15)
    counts=E.detector_id.value_counts().to_dict()
    expected=dict(zip(parent.detector_id,parent.n.astype(int)))
    if any(counts.get(k,0)!=v for k,v in expected.items()):raise RuntimeError(f"B33-S1 parent count mismatch {counts} vs {expected}")
    L=ledger(raw,b15,E); D=development(L,E,parent); S=select(D); R=reference(L,E,S); txt,status=render(S,R,diag,ident)
    D.to_csv(ROOT/f"{PFX}_Development.csv",index=False)
    S.to_csv(ROOT/f"{PFX}_Selected.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_Reference.csv",index=False)
    L.to_csv(ROOT/f"{PFX}_Entries.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**diag,**ident,"parent_counts":counts})+"\n",encoding="utf-8")
    print(txt,flush=True)
if __name__=="__main__":main()
