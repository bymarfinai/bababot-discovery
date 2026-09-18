#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b32_s1_specific_price_action_library as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B32_S2_SPECIFIC_STRUCTURE_ENTRY"
BAR=b31.BAR5
EPS=1e-12
DEV=[2022,2023,2024]
REF=[2025,2026]
H=[30,60,120]
EXPECTED={"S01":1980,"S02":2021,"S03":639,"S04":2702,"S05":1863,"S06":1789,"S07":548,"S08":2637}
POLICIES={
"E0":"COMPLETION_CLOSE",
"E1":"NATIVE_LEVEL_RETEST",
"E2":"COMPLETION_MID_RETEST",
"E3":"COMPLETION_EXTREME_BREAK",
"E4":"PULLBACK_RECLAIM",
"E5":"FOLLOW_THROUGH_DISPLACEMENT",
}

def wilson(h,n,z=1.959963984540054):
    if n<=0:return np.nan
    p=h/n; den=1+z*z/n
    cen=p+z*z/(2*n)
    mar=z*np.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (cen-mar)/den

def br(o,h,l,c):
    r=h-l
    return 0.0 if r<=0 else abs(c-o)/r

def cloc(h,l,c):
    r=h-l
    return 0.0 if r<=0 else ((c-l)-(h-c))/r

def forward(p,side,steps,idx,c):
    if p is None:return np.nan
    e=p+steps
    if e>=len(idx) or idx[e]-idx[p] != steps*BAR:return np.nan
    for k in range(p+1,e+1):
        if idx[k]-idx[k-1] != BAR:return np.nan
    x=side*(float(c[e])/float(c[p])-1.0)
    return 0.0 if abs(x)<=EPS else x

def entry_positions(ev,pos,raw,b15):
    idx=raw.index
    o=raw.open.to_numpy(float); h=raw.high.to_numpy(float); l=raw.low.to_numpy(float); c=raw.close.to_numpy(float)
    side=1 if ev.direction=="LONG" else -1
    out={k:None for k in POLICIES}; out["E0"]=pos
    if ev.event_ts not in b15.index:return out
    q=b15.loc[ev.event_ts]
    sh=float(q.high); sl=float(q.low); mid=(sh+sl)/2.0; level=float(ev.level)
    adverse_ext=None
    prev=float(c[pos])
    for j in range(pos+1,min(pos+13,len(idx))):
        if idx[j]-idx[j-1] != BAR:break
        if out["E1"] is None:
            if side==1 and l[j]<=level and c[j]>level:out["E1"]=j
            if side==-1 and h[j]>=level and c[j]<level:out["E1"]=j
        if out["E2"] is None:
            if side==1 and l[j]<=mid and c[j]>mid:out["E2"]=j
            if side==-1 and h[j]>=mid and c[j]<mid:out["E2"]=j
        if out["E3"] is None:
            if side==1 and c[j]>sh:out["E3"]=j
            if side==-1 and c[j]<sl:out["E3"]=j
        adverse=(c[j]<prev-EPS) if side==1 else (c[j]>prev+EPS)
        if adverse:
            adverse_ext=float(h[j] if side==1 else l[j])
        elif out["E4"] is None and adverse_ext is not None:
            if side==1 and c[j]>adverse_ext:out["E4"]=j
            if side==-1 and c[j]<adverse_ext:out["E4"]=j
        if out["E5"] is None:
            rr=br(o[j],h[j],l[j],c[j]); cc=cloc(h[j],l[j],c[j])
            if side==1 and c[j]>o[j] and rr>=.55 and cc>=.50:out["E5"]=j
            if side==-1 and c[j]<o[j] and rr>=.55 and cc<=-.50:out["E5"]=j
        prev=float(c[j])
    return out

def ledger(raw,b15,E):
    idx=raw.index; c=raw.close.to_numpy(float); posmap={t:i for i,t in enumerate(idx)}
    rows=[]
    for ev in E.itertuples(index=False):
        p0=posmap.get(ev.event_ts)
        if p0 is None:continue
        ep=entry_positions(ev,p0,raw,b15)
        side=1.0 if ev.direction=="LONG" else -1.0
        for pid,pname in POLICIES.items():
            p=ep[pid]
            rec={"structure_ts":ev.event_ts,"structure_id":ev.structure_id,"structure":ev.structure,
                 "direction":ev.direction,"structure_year":int(ev.event_ts.year),"policy_id":pid,"policy":pname,
                 "entry_ts":pd.NaT if p is None else idx[p]}
            for hh in H:
                x=forward(p,side,hh//5,idx,c)
                rec[f"signed_{hh}"]=x
                rec[f"hit_{hh}"]=bool(np.isfinite(x) and x>EPS)
            rows.append(rec)
    return pd.DataFrame(rows)

def metric(z,parent_n,years):
    v=z[z.signed_60.notna()].copy(); n=len(v); hits=int(v.hit_60.sum())
    d={"n":n,"parent_n":parent_n,"participation":n/parent_n if parent_n else np.nan,
       "hit_60":hits/n if n else np.nan,"wilson_60":wilson(hits,n),
       "median_signed_60":float(v.signed_60.median()) if n else np.nan,
       "hit_30":float(v.hit_30.mean()) if n else np.nan,
       "hit_120":float(v.hit_120.mean()) if n else np.nan}
    for y in years:
        q=v[v.structure_year==y]
        d[f"n_{y}"]=len(q); d[f"hit_{y}"]=float(q.hit_60.mean()) if len(q) else np.nan
    return d

def development(L,E):
    meta={sid:(name,d) for sid,name,d in s1.DETECTORS}; rows=[]
    for sid in EXPECTED:
        name,direction=meta[sid]
        parent=E[(E.structure_id==sid)&E.event_ts.dt.year.isin(DEV)]
        for pid,pname in POLICIES.items():
            z=L[(L.structure_id==sid)&(L.policy_id==pid)&L.structure_year.isin(DEV)]
            m=metric(z,len(parent),DEV)
            worst=min(m[f"hit_{y}"] for y in DEV) if all(np.isfinite(m[f"hit_{y}"]) for y in DEV) else np.nan
            aux=sum(np.isfinite(m[f"hit_{hh}"]) and m[f"hit_{hh}"]>=.53 for hh in (30,120))
            gate=(m["n"]>=100 and min(m[f"n_{y}"] for y in DEV)>=25 and m["participation"]>=.25 and
                  m["hit_60"]>=.55 and m["wilson_60"]>.52 and worst>=.52 and m["median_signed_60"]>0 and aux>=1)
            rows.append({"structure_id":sid,"structure":name,"direction":direction,"policy_id":pid,"policy":pname,
                         **m,"worst_dev_hit":worst,"aux_ge53":aux,"dev_gate":gate})
    return pd.DataFrame(rows)

def select(D):
    rows=[]
    for sid,name,direction in s1.DETECTORS:
        q=D[(D.structure_id==sid)&D.dev_gate].copy()
        if q.empty:
            rows.append({"structure_id":sid,"structure":name,"direction":direction,"selection_status":"NO_ENTRY_FOUND"})
        else:
            q=q.sort_values(["worst_dev_hit","wilson_60","hit_60","participation","policy_id"],
                            ascending=[False,False,False,False,True])
            r=q.iloc[0].to_dict(); r["selection_status"]="SELECTED_FOR_REFERENCE"; rows.append(r)
    return pd.DataFrame(rows)

def reference(L,E,S):
    rows=[]
    for s in S.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE":
            rows.append({"structure_id":s.structure_id,"structure":s.structure,"direction":s.direction,"status":"NO_ENTRY_FOUND"})
            continue
        parent=E[(E.structure_id==s.structure_id)&E.event_ts.dt.year.isin(REF)]
        z=L[(L.structure_id==s.structure_id)&(L.policy_id==s.policy_id)&L.structure_year.isin(REF)]
        m=metric(z,len(parent),REF)
        aux=sum(np.isfinite(m[f"hit_{hh}"]) and m[f"hit_{hh}"]>=.52 for hh in (30,120))
        gate=(m["n_2025"]>=25 and m["n_2026"]>=15 and m["participation"]>=.25 and
              m["hit_60"]>=.53 and m["hit_2025"]>.50 and m["hit_2026"]>.50 and
              m["wilson_60"]>.50 and m["median_signed_60"]>0 and aux>=1)
        rows.append({"structure_id":s.structure_id,"structure":s.structure,"direction":s.direction,
                     "policy_id":s.policy_id,"policy":s.policy,**m,"aux_ge52":aux,
                     "status":"STRUCTURE_ENTRY_PASS" if gate else "STRUCTURE_ENTRY_REJECT"})
    return pd.DataFrame(rows)

def pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.2f}%"

def render(S,R,diag,ident):
    n=int((R.status=="STRUCTURE_ENTRY_PASS").sum())
    status="BNB_B32_S2_STRUCTURE_ENTRIES_FOUND" if n else "BNB_B32_S2_NO_ENTRY_PASSED"
    L=["# BNB B32-S2 — Structure-Specific Entry Discovery Result","",f"**Status: {status}**","",
       "B32-S1 structures are frozen. No TP/SL or economics is simulated.","","## Integrity",
       f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**, SHA `{diag['sha256']}`",
       f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**, close-location diff **{ident['max_close_location_diff']:.12g}**","",
       "## Development winner per structure","","| Structure | Entry | N | Part. | +60 | Wilson | Worst era | Status |",
       "|---|---|---:|---:|---:|---:|---:|---|"]
    for s in S.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE":
            L.append(f"| {s.structure_id} {s.structure} | — | — | — | — | — | — | NO_ENTRY_FOUND |")
        else:
            L.append(f"| {s.structure_id} {s.structure} | {s.policy_id} {s.policy} | {int(s.n)} | {pct(s.participation)} | {pct(s.hit_60)} | {pct(s.wilson_60)} | {pct(s.worst_dev_hit)} | SELECTED |")
    L+=["","## One-shot reference","","| Structure | Entry | N | Part. | +60 | 2025 | 2026 | +30 | +120 | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in R.itertuples(index=False):
        if r.status=="NO_ENTRY_FOUND":
            L.append(f"| {r.structure_id} {r.structure} | — | — | — | — | — | — | — | — | NO_ENTRY_FOUND |")
        else:
            L.append(f"| {r.structure_id} {r.structure} | {r.policy_id} {r.policy} | {int(r.n)} | {pct(r.participation)} | {pct(r.hit_60)} | {pct(r.hit_2025)} | {pct(r.hit_2026)} | {pct(r.hit_30)} | {pct(r.hit_120)} | {r.status} |")
    L+=["","## Decision",f"**{status}**","",f"Pairs eligible for B32-S3 economics: **{n}/8**."]
    return "\n".join(L)+"\n",status

def main():
    raw,diag=b31.load_raw(); a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if diag["coverage"]<.995 or ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity failure {diag} {ident}")
    b15=b31.bars15(raw); E=s1.detect(b15)
    counts=E.structure_id.value_counts().to_dict()
    if any(counts.get(k,0)!=v for k,v in EXPECTED.items()):raise RuntimeError(f"parent mismatch {counts}")
    L=ledger(raw,b15,E); D=development(L,E); S=select(D); R=reference(L,E,S); txt,status=render(S,R,diag,ident)
    D.to_csv(ROOT/f"{PFX}_Development.csv",index=False)
    S.to_csv(ROOT/f"{PFX}_Selected.csv",index=False)
    R.to_csv(ROOT/f"{PFX}_Reference.csv",index=False)
    L.to_csv(ROOT/f"{PFX}_Entries.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**diag,**ident,"parent_counts":counts})+"\n",encoding="utf-8")
    print(txt,flush=True)
if __name__=="__main__":main()
