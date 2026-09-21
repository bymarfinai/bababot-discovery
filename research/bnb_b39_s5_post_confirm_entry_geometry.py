#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s4_first5_expansion_detector as s4

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S5_POST_CONFIRM_ENTRY_GEOMETRY"
START=pd.Timestamp("2022-01-01T00:00:00Z")
D1_CUT=s4.D1_CUT
EXPECTED_SIGNATURE=s4.DETECTOR_SIGNATURE

CANDS=[
    "MARKET_SIGNAL_CLOSE",
    "LIMIT_HALF_RETRACE",
    "LIMIT_ANCHOR_RETEST",
    "LIMIT_DEMAND_HIGH_RETEST",
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

def resolve_after(raw5,start_ts,entry,floor,target,deadline):
    idx=raw5.index
    ti=first_touch_idx(raw5,start_ts,target,"HIGH",deadline)
    si=first_touch_idx(raw5,start_ts,floor,"LOW",deadline)
    rr=(target-entry)/(entry-floor)
    if ti is None and si is None:
        return {"status":"UNRESOLVED","resolution_ts":pd.NaT,"realized_r":0.0}
    if ti is not None and si is not None and ti==si:
        return {"status":"AMBIGUOUS_AFTER_ENTRY","resolution_ts":idx[ti],"realized_r":0.0}
    if ti is not None and (si is None or ti<si):
        return {"status":"WIN","resolution_ts":idx[ti],"realized_r":float(rr)}
    return {"status":"LOSS","resolution_ts":idx[si],"realized_r":-1.0}

def limit_trade(raw5,signal_ts,limit,floor,target,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:
        return {"status":"NO_FILL_END","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":0.0}

    lo=raw5.low.to_numpy(float,copy=False)
    hi=raw5.high.to_numpy(float,copy=False)

    fill_i=None
    for i in range(i0,i1):
        target_here=hi[i]>=target
        floor_here=lo[i]<=floor
        can_fill=lo[i]<=limit<=hi[i]

        if can_fill:
            # Signal is known before this bar, but ordering inside the fill bar is not.
            if target_here or floor_here:
                return {
                    "status":"AMBIGUOUS_FILL_BAR","fill_ts":idx[i],
                    "resolution_ts":idx[i],"realized_r":0.0
                }
            fill_i=i
            break

        if target_here and floor_here:
            return {
                "status":"NO_FILL_AMBIGUOUS_RESOLUTION","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }
        if target_here:
            return {
                "status":"NO_FILL_TARGET_FIRST","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }
        if floor_here:
            return {
                "status":"NO_FILL_FLOOR_FIRST","fill_ts":pd.NaT,
                "resolution_ts":idx[i],"realized_r":0.0
            }

    if fill_i is None:
        return {"status":"NO_FILL_END","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":0.0}

    z=resolve_after(raw5,idx[fill_i],limit,floor,target,deadline)
    return {
        "status":z["status"],"fill_ts":idx[fill_i],
        "resolution_ts":z["resolution_ts"],"realized_r":z["realized_r"]
    }

def summarize(q):
    q=q.sort_values(["signal_ts","zone_id"]).copy()
    avail=q[q.available].copy()
    filled=avail[avail.status.isin(["WIN","LOSS","UNRESOLVED","AMBIGUOUS_AFTER_ENTRY"])].copy()
    resolved=filled[filled.status.isin(["WIN","LOSS"])].copy()
    w=resolved[resolved.status=="WIN"]; l=resolved[resolved.status=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    nofill=avail[avail.status.str.startswith("NO_FILL")].copy()
    ge1=avail[avail.GE1R]
    fp=avail[~avail.GE1R]

    fill_ids=set(filled.zone_id)
    win_ids=set(w.zone_id)
    loss_ids=set(l.zone_id)
    nofill_ids=set(nofill.zone_id)

    return {
        "signals":len(q),
        "available":len(avail),
        "filled":len(filled),
        "fill_rate":len(filled)/len(avail) if len(avail) else np.nan,
        "resolved":len(resolved),
        "wins":len(w),"losses":len(l),
        "wr_resolved":len(w)/len(resolved) if len(resolved) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "mean_win_r":float(w.realized_r.mean()) if len(w) else np.nan,
        "expectancy_per_filled":float(filled.realized_r.mean()) if len(filled) else np.nan,
        "expectancy_per_signal":float(avail.realized_r.sum()/len(q)) if len(q) else np.nan,
        "total_r_per_signal_book":float(avail.realized_r.sum()),
        "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_drawdown_r":maxdd(avail.realized_r.tolist()) if len(avail) else np.nan,
        "max_loss_streak":maxls(avail.realized_r.tolist()) if len(avail) else np.nan,
        "median_entry_improvement_event_r":float(avail.entry_improvement_event_r.median()) if len(avail) else np.nan,
        "median_risk_compression":float(avail.risk_compression_vs_market.median()) if len(avail) else np.nan,
        "median_target_rr":float(avail.target_rr.median()) if len(avail) else np.nan,
        "ge1_winners_available":len(ge1),
        "ge1_winners_filled":len(set(ge1.zone_id)&fill_ids),
        "ge1_winners_resolve_win":len(set(ge1.zone_id)&win_ids),
        "ge1_winners_missed_nofill":len(set(ge1.zone_id)&nofill_ids),
        "ge1_winners_became_loss":len(set(ge1.zone_id)&loss_ids),
        "false_positives_available":len(fp),
        "false_positives_avoided_nofill":len(set(fp.zone_id)&nofill_ids),
        "false_positive_avoid_rate":len(set(fp.zone_id)&nofill_ids)/len(fp) if len(fp) else np.nan,
        "ambiguous_fill_bar":int((avail.status=="AMBIGUOUS_FILL_BAR").sum()),
        "ambiguous_after_entry":int((avail.status=="AMBIGUOUS_AFTER_ENTRY").sum()),
        "unresolved_after_entry":int((avail.status=="UNRESOLVED").sum()),
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

    # Frozen D1 parity.
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
        floor=float(r.demand_low)
        er=float(r.event_risk)
        signal=float(anchor+float(r.p5_close_r)*er)
        target=anchor+er
        deadline=min(end,pd.Timestamp(r.first_touch_ts)+pd.Timedelta(hours=24))
        demand_high=float(fr.demand_high)

        levels={
            "MARKET_SIGNAL_CLOSE":signal,
            "LIMIT_HALF_RETRACE":anchor+0.50*(signal-anchor),
            "LIMIT_ANCHOR_RETEST":anchor,
            "LIMIT_DEMAND_HIGH_RETEST":demand_high,
        }

        market_risk=signal-floor
        for cand in CANDS:
            entry=float(levels[cand])
            available=bool(
                np.isfinite(entry) and
                entry>floor+1e-12 and
                entry<target-1e-12 and
                (cand=="MARKET_SIGNAL_CLOSE" or entry<signal-1e-12)
            )
            if not available:
                status="UNAVAILABLE"; fill_ts=pd.NaT; res_ts=pd.NaT; rr=0.0
            elif cand=="MARKET_SIGNAL_CLOSE":
                z=resolve_after(raw5,r.decision_ts,entry,floor,target,deadline)
                status=z["status"]; fill_ts=r.decision_ts; res_ts=z["resolution_ts"]; rr=z["realized_r"]
            else:
                z=limit_trade(raw5,r.decision_ts,entry,floor,target,deadline)
                status=z["status"]; fill_ts=z["fill_ts"]; res_ts=z["resolution_ts"]; rr=z["realized_r"]

            risk=entry-floor if available else np.nan
            target_rr=(target-entry)/risk if available and risk>0 else np.nan
            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "first_touch_ts":r.first_touch_ts,"signal_ts":r.decision_ts,
                "candidate":cand,"available":available,
                "anchor":anchor,"signal_close":signal,"candidate_entry":entry,
                "floor":floor,"target_anchor_1r":target,"event_risk":er,
                "p5_close_r":r.p5_close_r,
                "entry_improvement_event_r":(signal-entry)/er if available else np.nan,
                "risk_compression_vs_market":1.0-risk/market_risk if available and market_risk>0 else np.nan,
                "target_rr":target_rr,
                "status":status,"fill_ts":fill_ts,"resolution_ts":res_ts,"realized_r":rr,
                "GE1R":bool(r.GE1R),"GE1_5R":bool(r.GE1_5R),"GE2R":bool(r.GE2R),
                "CLEAN1R":bool(r.CLEAN1R),"CLEAN1_5R":bool(r.CLEAN1_5R),
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

    # Candidate trade-state census, useful for understanding why limits miss/fail.
    ST=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            for st,z in q.groupby("status"):
                ST.append({"period":per,"candidate":cand,"status":st,"n":len(z)})
    ST=pd.DataFrame(ST)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_StatusCensus.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"DETECTOR=D1_FIRST5_DISPLACEMENT\n"
        f"DETECTOR_SIGNATURE_SHA256={EXPECTED_SIGNATURE}\n"
        f"D1_P5_CLOSE_R_GT={D1_CUT:.17f}\n"
        "AUDIT_TARGET=ANCHOR_PLUS_1_EVENT_R\n"
        "AUDIT_FLOOR=DEMAND_LOW\n"
        "ORDER_ACTIVATION=STRICTLY_AFTER_SIGNAL_BAR\n"
        "DEADLINE=24H_FROM_FIRST_TOUCH\n"
        "CANDIDATES=MARKET_SIGNAL_CLOSE,LIMIT_HALF_RETRACE,LIMIT_ANCHOR_RETEST,LIMIT_DEMAND_HIGH_RETEST\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S5 — Frozen D1 Post-Confirmation Entry Geometry","",
        f"Frozen detector signature: `{EXPECTED_SIGNATURE}`",
        f"D1 condition unchanged: `p5_close_r > {D1_CUT:.17f}`","",
        "Audit target = anchor +1 event-R; structural floor = demand_low; limit orders activate only after D1 close.","",
        "## Entry geometry","",
        "| Period | Candidate | Fill | W-L | WR resolved | Med WIN R | Exp/fill | Exp/signal | Total R | PF | Med improvement | Risk compression | Med target R:R | GE1 fill/win | GE1 missed | FP avoided | GE1→LOSS |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.filled}/{r.available} ({fmt_pct(r.fill_rate)}) | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr_resolved)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.expectancy_per_filled)}R | {fmt_num(r.expectancy_per_signal)}R | "
            f"{fmt_num(r.total_r_per_signal_book)}R | {fmt_num(r.profit_factor)} | "
            f"{fmt_num(r.median_entry_improvement_event_r)} event-R | {fmt_pct(r.median_risk_compression)} | "
            f"{fmt_num(r.median_target_rr)} | "
            f"{r.ge1_winners_filled}/{r.ge1_winners_resolve_win} of {r.ge1_winners_available} | "
            f"{r.ge1_winners_missed_nofill} | {r.false_positives_avoided_nofill} ({fmt_pct(r.false_positive_avoid_rate)}) | "
            f"{r.ge1_winners_became_loss} |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | Fill | W-L | WR | Exp/signal | Total R | Med target R:R | GE1 missed | FP avoided |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.filled}/{r.available} | {r.wins}-{r.losses} | "
            f"{fmt_pct(r.wr_resolved)} | {fmt_num(r.expectancy_per_signal)}R | "
            f"{fmt_num(r.total_r_per_signal_book)}R | {fmt_num(r.median_target_rr)} | "
            f"{r.ge1_winners_missed_nofill} | {r.false_positives_avoided_nofill} |"
        )

    lines += ["","## Interpretation boundary",
        "S5 changes entry geometry only; D1 remains frozen.",
        "No-fill and unresolved cases contribute 0R to per-signal audit economics.",
        "The +1 event-R target and demand floor are audit geometry, not yet a final live TP/SL policy.",
        "A deeper limit is not preferred automatically if it buys R:R by discarding too many frozen D1 winners."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S5_POST_CONFIRM_ENTRY_GEOMETRY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
