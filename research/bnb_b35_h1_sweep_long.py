#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B35_H1_SWEEP_LONG"
BAR15=pd.Timedelta(minutes=15)
BAR60=pd.Timedelta(hours=1)
START=b31.START
END=b31.END
YEARS=[2022,2023,2024,2025,2026]
DEV=[2022,2023,2024]
REF=[2025,2026]
EPS=1e-12

def wilson(h,n,z=1.959963984540054):
    if n<=0:return np.nan
    p=h/n; den=1+z*z/n
    cen=p+z*z/(2*n)
    mar=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (cen-mar)/den

def bars60(raw):
    z=raw.reset_index().rename(columns={"ts":"close_ts"})
    z["bucket"]=z["close_ts"].dt.ceil("1h")
    g=z.groupby("bucket",sort=True)
    out=g.agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),
              n=("close","size"),first_ts=("close_ts","first"),last_ts=("close_ts","last")).reset_index()
    out=out[(out.n==12)&((out.last_ts-out.first_ts)==pd.Timedelta(minutes=55))].copy()
    out=out.set_index("bucket")[["open","high","low","close"]].astype(float)
    return out[(out.index>=START-pd.Timedelta(days=10))&(out.index<=END)]

def confirmed_swing_lows(b):
    lo=b.low.to_numpy(float); idx=b.index; by_confirm={}
    for i in range(2,len(b)-2):
        if lo[i] < min(lo[i-2],lo[i-1],lo[i+1],lo[i+2]):
            rec=(idx[i+2],idx[i],float(lo[i]))
            by_confirm.setdefault(idx[i+2],[]).append(rec)
    return by_confirm

def detect(b):
    conf=confirmed_swing_lows(b)
    active=[]; rows=[]; last_event=None
    for t,r in b.iterrows():
        latest=active[-1] if active else None
        if t>=START and latest is not None:
            confirm_ts,pivot_ts,level=latest
            if r.low < level and r.close >= level:
                if last_event is None or t-last_event>=pd.Timedelta(hours=4):
                    rows.append({"event_ts":t,"structure_id":"H1","structure":"H1_SWING_LOW_SWEEP_RECLAIM_LONG",
                                 "direction":"LONG","level":level,"level_pivot_ts":pivot_ts,
                                 "structure_high":float(r.high),"structure_low":float(r.low),
                                 "structure_open":float(r.open),"structure_close":float(r.close)})
                    last_event=t
        for x in conf.get(t,[]): active.append(x)
    e=pd.DataFrame(rows)
    if len(e):e=e[(e.event_ts>=START)&(e.event_ts<=END)].copy()
    return e

def structural_summary(e):
    n=len(e); cnt={y:int((e.event_ts.dt.year==y).sum()) for y in YEARS}
    eras=sum(v>=10 for v in cnt.values()); mx=max(cnt.values())/n if n else np.nan
    viable=(n>=100 and eras>=4 and mx<=.40)
    return {"n":n,**{f"n_{y}":cnt[y] for y in YEARS},"eras_ge10":eras,"max_era_share":mx,
            "status":"STRUCTURALLY_VIABLE" if viable else "INSUFFICIENT_STRUCTURE_SAMPLE"}

def entry_positions(ev,b15):
    out={k:None for k in ["E0","E1","E2","E3","E4"]}
    if ev.event_ts not in b15.index:return out
    pos=b15.index.get_loc(ev.event_ts)
    if not isinstance(pos,(int,np.integer)):return out
    out["E0"]=pos
    level=float(ev.level); hi=float(ev.structure_high)
    mid=(float(ev.structure_high)+float(ev.structure_low))/2.0
    prev=float(b15.close.iloc[pos]); adverse_high=None
    for j in range(pos+1,min(pos+13,len(b15))):
        if b15.index[j]-b15.index[j-1]!=BAR15:break
        r=b15.iloc[j]
        if out["E1"] is None and r.low<=level and r.close>level:out["E1"]=j
        if out["E2"] is None and r.close>hi:out["E2"]=j
        adverse=float(r.close)<prev-EPS
        if adverse:adverse_high=float(r.high)
        elif out["E3"] is None and adverse_high is not None and r.close>adverse_high:out["E3"]=j
        if out["E4"] is None and r.low<=mid and r.close>mid:out["E4"]=j
        prev=float(r.close)
    return out

def signed_forward(b15,p,minutes):
    if p is None:return np.nan
    steps=minutes//15; q=p+steps
    if q>=len(b15):return np.nan
    if b15.index[q]-b15.index[p]!=pd.Timedelta(minutes=minutes):return np.nan
    x=float(b15.close.iloc[q])/float(b15.close.iloc[p])-1.0
    return 0.0 if abs(x)<=EPS else x

def ledger(e,b15):
    names={"E0":"STRUCTURE_CLOSE","E1":"NATIVE_LEVEL_RETEST","E2":"STRUCTURE_HIGH_BREAK",
           "E3":"PULLBACK_RECLAIM","E4":"STRUCTURE_MID_RETEST"}
    rows=[]
    for ev in e.itertuples(index=False):
        ps=entry_positions(ev,b15)
        for pid,name in names.items():
            p=ps[pid]
            rec={"event_ts":ev.event_ts,"event_year":int(ev.event_ts.year),"entry_id":pid,"entry":name,
                 "entry_ts":pd.NaT if p is None else b15.index[p]}
            for h in [60,120,240]:
                x=signed_forward(b15,p,h); rec[f"signed_{h}"]=x; rec[f"hit_{h}"]=bool(np.isfinite(x) and x>EPS)
            rows.append(rec)
    return pd.DataFrame(rows)

def metrics(z,parent_n,years):
    v=z[z.signed_120.notna()].copy(); n=len(v); h=int(v.hit_120.sum())
    d={"n":n,"participation":n/parent_n if parent_n else np.nan,
       "hit_120":h/n if n else np.nan,"wilson_120":wilson(h,n),
       "median_signed_120":float(v.signed_120.median()) if n else np.nan,
       "hit_60":float(v.hit_60.mean()) if n else np.nan,"hit_240":float(v.hit_240.mean()) if n else np.nan}
    for y in years:
        q=v[v.event_year==y]; d[f"n_{y}"]=len(q); d[f"hit_{y}"]=float(q.hit_120.mean()) if len(q) else np.nan
    return d

def development(L,e):
    parent=e[e.event_ts.dt.year.isin(DEV)]; rows=[]
    for pid in ["E0","E1","E2","E3","E4"]:
        z=L[(L.entry_id==pid)&L.event_year.isin(DEV)]
        m=metrics(z,len(parent),DEV)
        worst=min(m[f"hit_{y}"] for y in DEV) if all(np.isfinite(m[f"hit_{y}"]) for y in DEV) else np.nan
        aux=max(m["hit_60"],m["hit_240"]) if np.isfinite(m["hit_60"]) and np.isfinite(m["hit_240"]) else np.nan
        gate=(m["n"]>=100 and min(m[f"n_{y}"] for y in DEV)>=25 and m["participation"]>=.25 and
              m["hit_120"]>=.55 and m["wilson_120"]>.52 and worst>=.52 and m["median_signed_120"]>0 and aux>=.53)
        rows.append({"entry_id":pid,"entry":z.entry.iloc[0] if len(z) else "",**m,"worst_dev_hit":worst,"aux_best":aux,"dev_gate":gate})
    return pd.DataFrame(rows)

def reference(L,e,pid):
    parent=e[e.event_ts.dt.year.isin(REF)]
    z=L[(L.entry_id==pid)&L.event_year.isin(REF)]
    m=metrics(z,len(parent),REF)
    aux=max(m["hit_60"],m["hit_240"]) if np.isfinite(m["hit_60"]) and np.isfinite(m["hit_240"]) else np.nan
    gate=(m["n_2025"]>=30 and m["n_2026"]>=20 and m["participation"]>=.25 and m["hit_120"]>=.53 and
          m["hit_2025"]>.50 and m["hit_2026"]>.50 and m["wilson_120"]>.50 and m["median_signed_120"]>0 and aux>=.52)
    return {**m,"aux_best":aux,"reference_gate":gate}

def pct(x):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:.2f}%"

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:raise RuntimeError(f"identity fail {ident}")
    b60=bars60(raw); b15=b31.bars15(raw); e=detect(b60); s=structural_summary(e)
    pd.DataFrame([s]).to_csv(ROOT/f"{PFX}_StructureSummary.csv",index=False)
    e.to_csv(ROOT/f"{PFX}_StructureEvents.csv.gz",index=False,compression="gzip")

    lines=["# BNB B35 — 1H Liquidity-Sweep LONG Timeframe Result","",
           f"**S1 status: {s['status']}**","",
           "## Integrity",f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**.",
           f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**; close-location diff **{ident['max_close_location_diff']:.12g}**.",
           f"- Exact reconstructed 1H bars: **{len(b60):,}**.","",
           "## S1 structure census",
           f"- H1 sweep-reclaim LONG N **{s['n']:,}**.",
           f"- 2022/2023/2024/2025/2026*: **{s['n_2022']} / {s['n_2023']} / {s['n_2024']} / {s['n_2025']} / {s['n_2026']}**.",
           f"- Eras >=10: **{s['eras_ge10']}/5**; max era share **{pct(s['max_era_share'])}**."]

    if s["status"]!="STRUCTURALLY_VIABLE":
        status="BNB_B35_STOP_INSUFFICIENT_H1_STRUCTURE"
        lines+=["","## Decision",f"**{status}**","","S2 outcomes remained unopened because S1 failed structural viability."]
        (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
        (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
        print("\n".join(lines),flush=True);return

    L=ledger(e,b15); D=development(L,e)
    L.to_csv(ROOT/f"{PFX}_EntryLedger.csv.gz",index=False,compression="gzip")
    D.to_csv(ROOT/f"{PFX}_Development.csv",index=False)
    passers=D[D.dev_gate].sort_values(["worst_dev_hit","wilson_120","hit_120","participation","entry_id"],
                                     ascending=[False,False,False,False,True])
    selected=None if passers.empty else str(passers.iloc[0].entry_id)
    lines+=["","## S2 development","","| Entry | N | Part. | +120 | Wilson | Worst year | +60 | +240 | Pass |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in D.itertuples(index=False):
        lines.append(f"| {r.entry_id} {r.entry} | {r.n} | {pct(r.participation)} | {pct(r.hit_120)} | {pct(r.wilson_120)} | {pct(r.worst_dev_hit)} | {pct(r.hit_60)} | {pct(r.hit_240)} | {'PASS' if r.dev_gate else '—'} |")
    lines+=["",f"Development winner: **{selected or 'NONE'}**."]

    if selected is None:
        status="BNB_B35_NO_DEVELOPMENT_ENTRY"
        lines+=["","Reference 2025-2026 remained **UNOPENED**.","","## Decision",f"**{status}**"]
    else:
        R=reference(L,e,selected)
        pd.DataFrame([{"entry_id":selected,**R}]).to_csv(ROOT/f"{PFX}_Reference.csv",index=False)
        status="BNB_B35_H1_SWEEP_REFERENCE_PASS" if R["reference_gate"] else "BNB_B35_H1_SWEEP_REFERENCE_REJECT"
        lines+=["","## One-shot reference",f"- Frozen entry: **{selected}**",
                f"- N **{R['n']}**, participation **{pct(R['participation'])}**, +120 **{pct(R['hit_120'])}**, Wilson **{pct(R['wilson_120'])}**.",
                f"- 2025: N={R['n_2025']}, hit={pct(R['hit_2025'])}; 2026*: N={R['n_2026']}, hit={pct(R['hit_2026'])}.",
                f"- +60 **{pct(R['hit_60'])}**, +240 **{pct(R['hit_240'])}**.",
                f"- Gate: **{'PASS' if R['reference_gate'] else 'FAIL'}**.","","## Decision",f"**{status}**"]
    lines+=["","No TP/SL/PnL/economic optimization was performed. Only a reference pass may advance to economics."]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    pd.DataFrame([{"selected_entry":selected or "NONE","status":status}]).to_csv(ROOT/f"{PFX}_Selection.csv",index=False)
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
