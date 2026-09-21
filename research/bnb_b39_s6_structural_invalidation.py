#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s4_first5_expansion_detector as s4

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S6_STRUCTURAL_INVALIDATION"
START=pd.Timestamp("2022-01-01T00:00:00Z")
D1_CUT=s4.D1_CUT
EXPECTED_SIGNATURE=s4.DETECTOR_SIGNATURE

CANDS=[
    "DEMAND_LOW_BASELINE",
    "TOUCH_BAR_LOW",
    "D1_BAR_LOW",
    "ANCHOR_LEVEL",
    "DEMAND_HIGH_LEVEL",
]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def maxdd(rs):
    if not len(rs): return np.nan
    a=np.asarray(rs,float)
    c=np.cumsum(a)
    peaks=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(peaks-c))

def maxls(vals):
    cur=mx=0
    for x in vals:
        if x<0:
            cur+=1; mx=max(mx,cur)
        else:
            cur=0
    return mx

def first_touch_idx(raw5,start_ts,level,kind,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def resolve(raw5,signal_ts,entry,sl,target,deadline):
    idx=raw5.index
    ti=first_touch_idx(raw5,signal_ts,target,"HIGH",deadline)
    si=first_touch_idx(raw5,signal_ts,sl,"LOW",deadline)
    if ti is None and si is None:
        return {"status":"UNRESOLVED","resolution_ts":pd.NaT,"realized_r":0.0}
    if ti is not None and si is not None and ti==si:
        return {"status":"AMBIGUOUS","resolution_ts":idx[ti],"realized_r":0.0}
    rr=(target-entry)/(entry-sl)
    if ti is not None and (si is None or ti<si):
        return {"status":"WIN","resolution_ts":idx[ti],"realized_r":float(rr)}
    return {"status":"LOSS","resolution_ts":idx[si],"realized_r":-1.0}

def later_target_after_stop(raw5,stop_ts,target,deadline):
    ti=first_touch_idx(raw5,stop_ts,target,"HIGH",deadline)
    return raw5.index[ti] if ti is not None else pd.NaT

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    avail=q[q.available].copy()
    resolved=avail[avail.status.isin(["WIN","LOSS"])].copy()
    w=resolved[resolved.status=="WIN"]; l=resolved[resolved.status=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    ge1=avail[avail.GE1R]
    fp=avail[~avail.GE1R]
    ge1_win=ge1[ge1.status=="WIN"]
    false=ge1[(ge1.status=="LOSS") & ge1.later_target_after_stop]

    return {
        "signals":len(q),
        "available":len(avail),
        "availability_rate":len(avail)/len(q) if len(q) else np.nan,
        "median_sl_distance_event_r":float(avail.sl_distance_event_r.median()) if len(avail) else np.nan,
        "median_risk_compression":float(avail.risk_compression.median()) if len(avail) else np.nan,
        "resolved":len(resolved),
        "wins":len(w),"losses":len(l),
        "ambiguous":int((avail.status=="AMBIGUOUS").sum()),
        "unresolved":int((avail.status=="UNRESOLVED").sum()),
        "wr":len(w)/len(resolved) if len(resolved) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "mean_win_r":float(w.realized_r.mean()) if len(w) else np.nan,
        "expectancy_per_signal":float(avail.realized_r.sum()/len(q)) if len(q) else np.nan,
        "total_r":float(avail.realized_r.sum()),
        "pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_dd_r":maxdd(avail.realized_r.tolist()) if len(avail) else np.nan,
        "max_loss_streak":maxls(avail.realized_r.tolist()) if len(avail) else np.nan,
        "ge1_available":len(ge1),
        "ge1_retained_win":len(ge1_win),
        "ge1_false_stop":len(false),
        "ge1_false_stop_rate":len(false)/len(ge1) if len(ge1) else np.nan,
        "median_stop_to_later_target_min":float(false.stop_to_later_target_min.median()) if len(false) else np.nan,
        "median_false_stop_overshoot_candidate_r":float(false.false_stop_overshoot_candidate_r.median()) if len(false) else np.nan,
        "fp_available":len(fp),
        "fp_became_win":int((fp.status=="WIN").sum()),
        "fp_remain_loss":int((fp.status=="LOSS").sum()),
    }

def main():
    if s4.DETECTOR_SIGNATURE!=EXPECTED_SIGNATURE:
        raise RuntimeError("D1 detector signature drift")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    s1.START=START; s1.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end].copy()
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end].copy()
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    fam["period"]=["DEV" if pd.Timestamp(x)<=pd.Timestamp("2024-12-31T23:59:59Z") else "REF" for x in fam.first_touch_ts]
    fam["year"]=pd.to_datetime(fam.first_touch_ts,utc=True).dt.year
    F=fam.set_index("zone_id")

    L4=s4.build_ledger(raw5,m15,h1,fam,end)
    P=L4[(L4.decision=="PLUS5_CLOSE")&(L4.decision_status=="ELIGIBLE")].copy()
    P["signal"]=pd.to_numeric(P.p5_close_r,errors="coerce")>D1_CUT
    P=P[P.signal].copy()

    hard={
        "DEV_N":int((P.period=="DEV").sum()),
        "DEV_GE1":int(((P.period=="DEV")&P.GE1R).sum()),
        "REF_N":int((P.period=="REF").sum()),
        "REF_GE1":int(((P.period=="REF")&P.GE1R).sum()),
    }
    if hard!={"DEV_N":151,"DEV_GE1":108,"REF_N":101,"REF_GE1":83}:
        raise RuntimeError(f"D1 parity drift {hard}")

    rows=[]
    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        anchor=float(r.anchor_price)
        er=float(r.event_risk)
        demand_low=float(r.demand_low)
        signal=float(anchor+float(r.p5_close_r)*er)
        target=anchor+er
        touch_low=float(fr.touch_low)
        d1_low=float(anchor+float(r.p5_low_r)*er)
        demand_high=float(fr.demand_high)
        deadline=min(end,pd.Timestamp(r.first_touch_ts)+pd.Timedelta(hours=24))

        defs={
            "DEMAND_LOW_BASELINE":demand_low,
            "TOUCH_BAR_LOW":touch_low,
            "D1_BAR_LOW":d1_low,
            "ANCHOR_LEVEL":anchor,
            "DEMAND_HIGH_LEVEL":demand_high,
        }

        baseline_risk=signal-demand_low
        for cand,sl in defs.items():
            available=bool(np.isfinite(sl) and sl<signal-1e-12 and sl<target-1e-12 and signal-sl>0)
            if available:
                z=resolve(raw5,r.decision_ts,signal,sl,target,deadline)
                status=z["status"]; rt=z["resolution_ts"]; rr=z["realized_r"]
            else:
                status="UNAVAILABLE"; rt=pd.NaT; rr=0.0

            risk=signal-sl if available else np.nan
            comp=1.0-risk/baseline_risk if available and baseline_risk>0 else np.nan

            later=False; later_ts=pd.NaT; mins=np.nan; overshoot=np.nan
            if available and status=="LOSS":
                later_ts=later_target_after_stop(raw5,rt,target,deadline)
                later=pd.notna(later_ts)
                if later:
                    mins=float((pd.Timestamp(later_ts)-pd.Timestamp(rt))/pd.Timedelta(minutes=1))
                    idx=raw5.index
                    i0=int(idx.searchsorted(pd.Timestamp(rt),side="left"))
                    i1=int(idx.searchsorted(pd.Timestamp(later_ts),side="right"))
                    seg=raw5.iloc[i0:i1]
                    if len(seg) and risk>0:
                        overshoot=max(0.0,(sl-float(seg.low.min()))/risk)

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "first_touch_ts":r.first_touch_ts,"signal_ts":r.decision_ts,
                "candidate":cand,"available":available,
                "entry":signal,"sl":sl,"target":target,
                "anchor":anchor,"event_risk":er,"demand_low":demand_low,
                "touch_low":touch_low,"d1_low":d1_low,"demand_high":demand_high,
                "sl_distance_event_r":risk/er if available and er>0 else np.nan,
                "risk_compression":comp,
                "status":status,"resolution_ts":rt,"realized_r":rr,
                "GE1R":bool(r.GE1R),"GE1_5R":bool(r.GE1_5R),"GE2R":bool(r.GE2R),
                "later_target_after_stop":bool(later),
                "later_target_ts":later_ts,
                "stop_to_later_target_min":mins,
                "false_stop_overshoot_candidate_r":overshoot,
            })

    E=pd.DataFrame(rows)

    SUM=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            SUM.append({"period":per,"candidate":cand,**summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for cand in CANDS:
            q=E[(E.year==y)&(E.candidate==cand)]
            if len(q):
                Y.append({"year":y,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    FS=E[(E.GE1R)&(E.status=="LOSS")&(E.later_target_after_stop)].copy()
    FSS=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=FS[(FS.period==per)&(FS.candidate==cand)]
            FSS.append({
                "period":per,"candidate":cand,"false_stops":len(q),
                "median_stop_to_later_target_min":float(q.stop_to_later_target_min.median()) if len(q) else np.nan,
                "median_overshoot_candidate_r":float(q.false_stop_overshoot_candidate_r.median()) if len(q) else np.nan,
            })
    FSS=pd.DataFrame(FSS)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FS.to_csv(ROOT/f"{PFX}_FalseStopLedger.csv.gz",index=False,compression="gzip")
    FSS.to_csv(ROOT/f"{PFX}_FalseStopSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"DETECTOR=D1_FIRST5_DISPLACEMENT\n"
        f"DETECTOR_SIGNATURE_SHA256={EXPECTED_SIGNATURE}\n"
        f"D1_P5_CLOSE_R_GT={D1_CUT:.17f}\n"
        "ENTRY=MARKET_SIGNAL_CLOSE\n"
        "TARGET=ANCHOR_PLUS_1_EVENT_R\n"
        "DEADLINE=24H_FROM_FIRST_TOUCH\n"
        "CANDIDATES=DEMAND_LOW_BASELINE,TOUCH_BAR_LOW,D1_BAR_LOW,ANCHOR_LEVEL,DEMAND_HIGH_LEVEL\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S6 — Frozen D1 Structural Invalidation / SL Discovery","",
        f"Frozen detector signature: `{EXPECTED_SIGNATURE}`",
        f"D1 unchanged: `p5_close_r > {D1_CUT:.17f}`",
        "Entry = D1 signal close; target = anchor +1 event-R; only SL changes.","",
        "## Static structural invalidation audit","",
        "| Period | Candidate | Avail | SL dist | Compression | W-L | WR | Med WIN R | Exp/signal | Total R | PF | GE1 retained | False stop | Stop→later target | FP→WIN |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.available}/{r.signals} | "
            f"{fmt_num(r.median_sl_distance_event_r)} event-R | {fmt_pct(r.median_risk_compression)} | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | {fmt_num(r.pf)} | "
            f"{r.ge1_retained_win}/{r.ge1_available} | {r.ge1_false_stop} ({fmt_pct(r.ge1_false_stop_rate)}) | "
            f"{fmt_num(r.median_stop_to_later_target_min,1)}m | {r.fp_became_win} |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | W-L | WR | Exp/signal | Total R | GE1 false-stop |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.wins}-{r.losses} | {fmt_pct(r.wr)} | "
            f"{fmt_num(r.expectancy_per_signal)}R | {fmt_num(r.total_r)}R | "
            f"{r.ge1_false_stop}/{r.ge1_available} ({fmt_pct(r.ge1_false_stop_rate)}) |"
        )

    lines += ["","## False-stop anatomy","",
        "| Period | Candidate | False stops | Med stop→later target | Med overshoot below stop |",
        "|---|---|---:|---:|---:|"
    ]
    for r in FSS.itertuples(index=False):
        if r.false_stops:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_stops} | "
                f"{fmt_num(r.median_stop_to_later_target_min,1)}m | "
                f"{fmt_num(r.median_overshoot_candidate_r)} candidate-R |"
            )

    lines += ["","## Interpretation boundary",
        "S6 changes only the hard structural invalidation level.",
        "A tighter static stop is rejected if its higher R multiple is bought by excessive false stops or DEV/REF instability.",
        "If no static level is robust, the next stage should search post-entry failure-state exits while retaining the wider structural floor."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S6_STRUCTURAL_INVALIDATION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
