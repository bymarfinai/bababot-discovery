#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1
import bnb_b37_s1b_visual_equivalent as s1b

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S4_CAUSAL_STATE_MACHINE"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")
CANDS=[
 "H4D_H1_PROXIMAL_RECLAIM",
 "H4D_H1_CLEAN_PROXIMAL_RECLAIM",
 "H4D_H1_BULLISH_PROXIMAL_RECLAIM",
 "H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM",
]

@dataclass
class ZoneState:
    zone_id: str
    activation_ts: pd.Timestamp
    origin_ts: pd.Timestamp
    broken_h4_swing_ts: pd.Timestamp
    broken_h4_level: float
    h4_bos_close: float
    demand_low: float
    demand_high: float
    state: str = "WAIT_EXPANSION"
    expansion_pivot_ts: pd.Timestamp | None = None
    expansion_confirm_ts: pd.Timestamp | None = None
    expansion_high: float | None = None
    terminal: bool = False

    @property
    def demand_width(self):
        return float(self.demand_high-self.demand_low)

def h4_activation_stream(b4):
    # Exact causal replay of S1 H4 demand generation.
    hi=b4.high.to_numpy(float)
    idx=b4.index
    confirm_map={}
    for i in range(2,len(b4)-2):
        if hi[i] > max(hi[i-2],hi[i-1],hi[i+1],hi[i+2]):
            confirm_map.setdefault(idx[i+2],[]).append((idx[i],float(hi[i])))

    active=[]
    used=set()
    out=[]
    prev_close=None
    for i,(t,r) in enumerate(b4.iterrows()):
        latest=active[-1] if active else None
        if latest is not None and prev_close is not None:
            pivot_ts,level=latest
            if pivot_ts not in used and prev_close<=level and float(r.close)>level:
                origin=None
                for j in range(i-1,max(-1,i-7),-1):
                    rr=b4.iloc[j]
                    if float(rr.close)<float(rr.open):
                        origin=(b4.index[j],rr)
                        break
                if origin is not None:
                    ots,orr=origin
                    zlow=float(orr.low); zhigh=float(orr.open)
                    if zhigh>zlow:
                        out.append(ZoneState(
                            zone_id=f"H4D_{t.isoformat()}",
                            activation_ts=t,
                            origin_ts=ots,
                            broken_h4_swing_ts=pivot_ts,
                            broken_h4_level=float(level),
                            h4_bos_close=float(r.close),
                            demand_low=zlow,
                            demand_high=zhigh,
                        ))
                        used.add(pivot_ts)
        for pivot_ts,level in confirm_map.get(t,[]):
            active.append((pivot_ts,level))
        prev_close=float(r.close)
    return out

def h1_high_confirm_map(b1):
    hi=b1.high.to_numpy(float); idx=b1.index
    m={}
    for i in range(2,len(b1)-2):
        if hi[i] > max(hi[i-2],hi[i-1],hi[i+1],hi[i+2]):
            m.setdefault(idx[i+2],[]).append({
                "pivot_ts":idx[i],
                "confirm_ts":idx[i+2],
                "pivot_high":float(hi[i]),
            })
    return m

def overlaps(r,z):
    return float(r.low)<=z.demand_high and float(r.high)>=z.demand_low

def path_stats(b1,pivot_ts,touch_ts):
    seg=b1[(b1.index>pivot_ts)&(b1.index<touch_ts)]
    pullback_bars=int(len(seg))
    lower_high=False; lower_low=False
    if len(seg)>=2:
        lower_high=bool((seg.high.diff()<0).any())
        lower_low=bool((seg.low.diff()<0).any())
    return pullback_bars,lower_high,lower_low

def replay(b1,b4):
    zones=h4_activation_stream(b4)
    h1conf=h1_high_confirm_map(b1)
    by_activation={}
    for z in zones:
        by_activation.setdefault(z.activation_ts,[]).append(z)

    active=[]
    parents=[]
    rejects=[]
    transitions=Counter()
    zone_snapshot={}

    # H4 activation may happen on timestamps also occupied by H1 closes.
    # S1B only allows touches strictly after activation, so add activations
    # before processing same-time H1 and enforce t > activation in overlap check.
    all_times=sorted(set(b1.index).union(set(by_activation.keys())))
    h1_lookup={t:r for t,r in b1.iterrows()}

    for t in all_times:
        for z in by_activation.get(t,[]):
            active.append(z)
            zone_snapshot[z.zone_id]=z
            transitions["WAIT_H4_STRUCTURE->DEMAND_REGISTERED"]+=1

        if t not in h1_lookup:
            continue
        r=h1_lookup[t]

        # First-touch evaluation uses only expansions confirmed strictly before t.
        survivors=[]
        for z in active:
            if z.terminal:
                continue
            if t<=z.activation_ts:
                survivors.append(z)
                continue
            if overlaps(r,z):
                transitions[f"{z.state}->RETEST_EVALUATED"]+=1
                pull,lh,ll=(0,False,False)
                if z.expansion_pivot_ts is not None:
                    pull,lh,ll=path_stats(b1,z.expansion_pivot_ts,t)
                hold=float(r.close)>=z.demand_low
                visual=bool(
                    z.expansion_pivot_ts is not None and
                    hold and
                    pull>=2 and
                    (lh or ll)
                )
                base={
                    "zone_id":z.zone_id,
                    "activation_ts":z.activation_ts,
                    "origin_ts":z.origin_ts,
                    "broken_h4_swing_ts":z.broken_h4_swing_ts,
                    "broken_h4_level":z.broken_h4_level,
                    "h4_bos_close":z.h4_bos_close,
                    "demand_low":z.demand_low,
                    "demand_high":z.demand_high,
                    "first_touch_ts":t,
                    "touch_open":float(r.open),
                    "touch_high":float(r.high),
                    "touch_low":float(r.low),
                    "touch_close":float(r.close),
                    "expansion_pivot_ts":z.expansion_pivot_ts,
                    "expansion_confirm_ts":z.expansion_confirm_ts,
                    "expansion_high":z.expansion_high,
                    "pullback_bars":pull,
                    "has_lower_high":lh,
                    "has_lower_low":ll,
                }
                if visual:
                    c1=float(r.close)>z.demand_high
                    c2=bool(c1 and float(r.low)>=z.demand_low)
                    c3=bool(c1 and float(r.close)>float(r.open))
                    c4=bool(c2 and (float(z.expansion_high)-z.h4_bos_close<=z.demand_width))
                    base.update({
                        "H4D_H1_PROXIMAL_RECLAIM":bool(c1),
                        "H4D_H1_CLEAN_PROXIMAL_RECLAIM":bool(c2),
                        "H4D_H1_BULLISH_PROXIMAL_RECLAIM":bool(c3),
                        "H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM":bool(c4),
                    })
                    parents.append(base)
                    transitions["RETEST_EVALUATED->PARENT_DETECTED"]+=1
                else:
                    if z.expansion_pivot_ts is None:
                        reason="NO_CONFIRMED_EXPANSION"
                    elif not hold:
                        reason="RETEST_CLOSE_INVALIDATES_DEMAND"
                    elif pull<2:
                        reason="INSUFFICIENT_PULLBACK_BARS"
                    else:
                        reason="NO_CORRECTIVE_LH_OR_LL"
                    base["reject_reason"]=reason
                    rejects.append(base)
                    transitions["RETEST_EVALUATED->TERMINAL_REJECT"]+=1
                z.terminal=True
                z.state="TERMINAL"
            else:
                survivors.append(z)
        active=survivors

        # Only non-touched zones may consume pivots confirmed at this H1 close.
        for ev in h1conf.get(t,[]):
            for z in active:
                if z.terminal or t<=z.activation_ts:
                    continue
                if ev["pivot_ts"]<=z.activation_ts:
                    continue
                floor=max(z.broken_h4_level,z.h4_bos_close)
                if ev["pivot_high"]>floor:
                    prior=z.state
                    z.expansion_pivot_ts=ev["pivot_ts"]
                    z.expansion_confirm_ts=ev["confirm_ts"]
                    z.expansion_high=float(ev["pivot_high"])
                    z.state="EXPANSION_CONFIRMED"
                    if prior=="WAIT_EXPANSION":
                        transitions["WAIT_EXPANSION->EXPANSION_CONFIRMED"]+=1
                    else:
                        transitions["EXPANSION_CONFIRMED->EXPANSION_REFRESHED"]+=1

    return pd.DataFrame(parents),pd.DataFrame(rejects),transitions,zones

def frozen_step3(b1,b4):
    zones=s1.h4_demand_zones(b4)
    fam,_=s1b.classify(b1,zones)
    v=fam[fam.visual_equivalent].copy()
    width=(v.demand_high-v.demand_low).astype(float)
    out=v[["zone_id","first_touch_ts"]].copy()
    out["H4D_H1_PROXIMAL_RECLAIM"]=(v.touch_close.astype(float)>v.demand_high.astype(float)).to_numpy(bool)
    out["H4D_H1_CLEAN_PROXIMAL_RECLAIM"]=(out["H4D_H1_PROXIMAL_RECLAIM"].to_numpy(bool) & (v.touch_low.astype(float)>=v.demand_low.astype(float)).to_numpy(bool))
    out["H4D_H1_BULLISH_PROXIMAL_RECLAIM"]=(out["H4D_H1_PROXIMAL_RECLAIM"].to_numpy(bool) & (v.touch_close.astype(float)>v.touch_open.astype(float)).to_numpy(bool))
    out["H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM"]=(out["H4D_H1_CLEAN_PROXIMAL_RECLAIM"].to_numpy(bool) & ((v.expansion_high.astype(float)-v.h4_bos_close.astype(float))<=width).to_numpy(bool))
    return out

def equivalence(sm,ref):
    keys=["zone_id","first_touch_ts"]
    m=sm[keys+CANDS].merge(ref[keys+CANDS],on=keys,how="outer",suffixes=("_sm","_ref"),indicator=True)
    missing=int((m._merge=="right_only").sum())
    extra=int((m._merge=="left_only").sum())
    mism={}
    both=m[m._merge=="both"].copy()
    for c in CANDS:
        mism[c]=int((both[f"{c}_sm"].astype(bool)!=both[f"{c}_ref"].astype(bool)).sum())
    return m,missing,extra,mism

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    b1=s1.exact_bars(raw,"1h",12)
    b4=s1.exact_bars(raw,"4h",48)
    b1=b1[(b1.index<=END)].copy()
    b4=b4[(b4.index<=END)].copy()

    sm,rejects,transitions,zones=replay(b1,b4)
    sm=sm[(pd.to_datetime(sm.first_touch_ts,utc=True)>=START)&(pd.to_datetime(sm.first_touch_ts,utc=True)<=END)].copy()
    if len(rejects):
        rejects=rejects[(pd.to_datetime(rejects.first_touch_ts,utc=True)>=START)&(pd.to_datetime(rejects.first_touch_ts,utc=True)<=END)].copy()

    ref=frozen_step3(b1,b4)
    ref=ref[(pd.to_datetime(ref.first_touch_ts,utc=True)>=START)&(pd.to_datetime(ref.first_touch_ts,utc=True)<=END)].copy()
    comp,missing,extra,mism=equivalence(sm,ref)

    support=[]
    for c in CANDS:
        row={"candidate":c,"total":int(sm[c].sum())}
        yrs=pd.to_datetime(sm.first_touch_ts,utc=True).dt.year
        for y in [2022,2023,2024]:
            row[str(y)]=int(sm.loc[yrs==y,c].sum())
        support.append(row)
    S=pd.DataFrame(support)

    expected={
      "H4D_H1_PROXIMAL_RECLAIM":133,
      "H4D_H1_CLEAN_PROXIMAL_RECLAIM":115,
      "H4D_H1_BULLISH_PROXIMAL_RECLAIM":27,
      "H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM":40,
    }
    totals_ok=all(int(sm[c].sum())==expected[c] for c in CANDS)
    gate=bool(len(sm)==201 and len(ref)==201 and missing==0 and extra==0 and all(v==0 for v in mism.values()) and totals_ok)

    sm.to_csv(ROOT/f"{PFX}_ParentAndEmissions.csv.gz",index=False,compression="gzip")
    rejects.to_csv(ROOT/f"{PFX}_TerminalRejects.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Support.csv",index=False)
    pd.DataFrame([{"transition":k,"count":v} for k,v in sorted(transitions.items())]).to_csv(ROOT/f"{PFX}_Transitions.csv",index=False)
    comp.to_csv(ROOT/f"{PFX}_Equivalence.csv.gz",index=False,compression="gzip")

    rc=rejects.reject_reason.value_counts().to_dict() if len(rejects) else {}
    lines=[
      "# BNB B37-S4 — Causal Structural Detector State Machine","",
      "**STEP 4 — LIVE-CAUSAL STATE MACHINE IMPLEMENTATION**","",
      "No outcome labels, WR, TP/SL, PnL, economics, indicators, derivatives, session filters, or 2025-2026 data were used.","",
      "## State flow","",
      "`WAIT_H4_STRUCTURE -> DEMAND_REGISTERED -> WAIT_EXPANSION -> EXPANSION_CONFIRMED -> WAIT_FIRST_RETEST -> RETEST_EVALUATED -> PARENT_DETECTED/TERMINAL_REJECT -> CANDIDATE_EMISSION`","",
      "Each H4 demand zone is an independent state instance. Newer eligible H1 expansion pivots refresh the stored expansion until first retest.","",
      "## Replay census",
      f"- H4 demand instances created through 2024: **{len(zones)}**.",
      f"- State-machine visual parent detections in 2022-2024: **{len(sm)}**.",
      f"- Frozen Step-3 parent reference: **{len(ref)}**.",
      f"- Missing vs Step 3: **{missing}**.",
      f"- Extra vs Step 3: **{extra}**.","",
      "## Candidate emissions","",
      "| Candidate | Total | 2022 | 2023 | 2024 |",
      "|---|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.candidate} | {r.total} | {getattr(r,'_2')} | {getattr(r,'_3')} | {getattr(r,'_4')} |")
    lines += ["","## Flag equivalence"]
    for c in CANDS:
        lines.append(f"- {c}: **{mism[c]} mismatches**.")
    lines += ["","## Terminal reject reasons"]
    for k,v in sorted(rc.items(),key=lambda kv:(-kv[1],kv[0])):
        lines.append(f"- {k}: **{v}**")
    lines += ["","## Equivalence gate",
              f"**{'STATE_MACHINE_EQUIVALENCE_PASS' if gate else 'STATE_MACHINE_EQUIVALENCE_FAIL'}**","",
              "Step 5 validation is permitted only on PASS. Detector definitions remain frozen."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(("BNB_B37_S4_STATE_MACHINE_EQUIVALENCE_PASS" if gate else "BNB_B37_S4_STATE_MACHINE_EQUIVALENCE_FAIL")+"\n",encoding="utf-8")
    print("\n".join(lines))
    if not gate:
        raise RuntimeError("Step-4 state-machine equivalence failed")

if __name__=="__main__":
    main()
