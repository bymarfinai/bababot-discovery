#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s10_reaction_development as s10
import bnb_b38_s11_e2_economics as s11
import bnb_b38_s14_post_tp1_continuation as s14

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S18_WIDE_SL_STRUCTURAL_INVALIDATION"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727

CANDS=[
    "TOUCH_LOW_BASELINE",
    "RECLAIM_LOW",
    "HOLD_LOW",
    "PROTECTED_PIVOT_LOW",
    "DEMAND_LOW_TOUCH",
    "DEMAND_LOW_CLOSE15",
]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def maxdd(rs):
    if not len(rs): return np.nan
    c=np.cumsum(np.asarray(rs,float))
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def maxls(seq):
    cur=mx=0
    for x in seq:
        if x=="LOSS":
            cur+=1; mx=max(mx,cur)
        else:
            cur=0
    return mx

def reconstruct_e2(m15,r,end):
    idx=m15.index
    ri,status,_=s10.find_reclaim(m15,r,end)
    if ri is None:
        return None
    reclaim_ts=idx[ri]
    reclaim_high=float(m15.high.iloc[ri])
    hold_i=None
    hold_high=np.nan
    i1=int(idx.searchsorted(end,side="right"))
    for j in range(ri+1,i1):
        b=m15.iloc[j]
        if float(b.close)<float(r.demand_low):
            return None
        if hold_i is None:
            if float(b.close)>=float(r.demand_high):
                hold_i=j
                hold_high=float(b.high)
            continue
        level=max(reclaim_high,hold_high)
        if float(b.close)>level:
            return {
                "reclaim_i":ri,
                "reclaim_ts":reclaim_ts,
                "hold_i":hold_i,
                "hold_ts":idx[hold_i],
                "hold_low":float(m15.low.iloc[hold_i]),
                "hold_high":hold_high,
                "entry_i":j,
                "entry_ts":idx[j],
                "entry_price":float(b.close),
            }
    return None

def resolve_touch(raw5,entry_ts,entry,sl,tp,end):
    return s11.touch_resolve(raw5,entry_ts,entry,sl,tp,end)

def resolve_close15(raw5,m15,entry_ts,entry,sl,tp,end):
    return s11.close15_resolve(raw5,m15,entry_ts,entry,sl,tp,end)

def summarize(q,base):
    avail=q[q.available].copy()
    r=avail[avail.outcome.isin(["WIN","LOSS"])].sort_values(["entry_ts","zone_id"])
    w=r[r.outcome=="WIN"]; l=r[r.outcome=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0
    bw=set(base[base.baseline_outcome=="WIN"].zone_id)
    bl=set(base[base.baseline_outcome=="LOSS"].zone_id)
    cw=set(w.zone_id); cl=set(l.zone_id)
    false=bw&cl
    return {
        "population":len(q),
        "available":int(avail.available.sum()),
        "availability_rate":float(avail.available.mean()) if len(avail) else np.nan,
        "resolved":len(r),
        "wins":len(w),"losses":len(l),
        "wr":len(w)/len(r) if len(r) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "expectancy_r":float(r.realized_r.mean()) if len(r) else np.nan,
        "total_r":float(r.realized_r.sum()) if len(r) else np.nan,
        "pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_dd_r":maxdd(r.realized_r.tolist()) if len(r) else np.nan,
        "max_loss_streak":maxls(r.outcome.tolist()),
        "median_sl_pct":float(avail.sl_pct.median()) if len(avail) else np.nan,
        "median_compression":float(avail.compression.median()) if len(avail) else np.nan,
        "baseline_wins":len(bw),
        "baseline_wins_available":len(bw & set(avail.zone_id)),
        "baseline_win_retained":len(bw&cw),
        "baseline_win_false_stop":len(false),
        "baseline_win_false_stop_rate_available":len(false)/len(bw & set(avail.zone_id)) if len(bw & set(avail.zone_id)) else np.nan,
        "baseline_losses":len(bl),
        "baseline_loss_to_win":len(bl&cw),
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    raw5,m15,h1,P,sig=s14.build_frozen(raw,end)
    if sig!=EXPECTED_SIGNATURE: raise RuntimeError(f"signature drift {sig}")

    # Rebuild family with zone geometry.
    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=pd.Timestamp("2022-01-01T00:00:00Z"))&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    F=fam.set_index("zone_id")

    # Confirmed 15m pivot lows, causal by confirm_ts.
    _,piv_lo=s1.pivots_df(m15)

    P=P.copy()
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    W=P[P.baseline_sl_pct>WIDE_CUT].copy()
    if int((W.period=="DEV").sum())!=110 or int((W.period=="REF").sum())!=50:
        raise RuntimeError(f"wide parity drift DEV={sum(W.period=='DEV')} REF={sum(W.period=='REF')}")

    structural=[]
    for r in W.itertuples(index=False):
        if r.zone_id not in F.index:
            raise RuntimeError(f"family missing {r.zone_id}")
        fr=F.loc[r.zone_id]
        rec=reconstruct_e2(m15,fr,end)
        if rec is None:
            raise RuntimeError(f"E2 reconstruction missing {r.zone_id}")
        if pd.Timestamp(rec["entry_ts"])!=pd.Timestamp(r.entry_ts):
            raise RuntimeError(f"E2 reconstruction entry mismatch {r.zone_id}: {rec['entry_ts']} != {r.entry_ts}")
        if abs(float(rec["entry_price"])-float(r.entry_price))>1e-10:
            raise RuntimeError(f"E2 reconstruction price mismatch {r.zone_id}")

        # Latest confirmed local pivot low after reclaim and known by entry.
        q=piv_lo[
            (piv_lo.pivot_ts>=rec["reclaim_ts"])&
            (piv_lo.confirm_ts<=r.entry_ts)&
            (piv_lo.level<r.entry_price)
        ].sort_values(["confirm_ts","pivot_ts"])
        pivot_low=float(q.iloc[-1].level) if len(q) else np.nan
        pivot_ts=q.iloc[-1].pivot_ts if len(q) else pd.NaT
        pivot_confirm=q.iloc[-1].confirm_ts if len(q) else pd.NaT

        structural.append({
            "zone_id":r.zone_id,
            "demand_low":float(fr.demand_low),
            "demand_high":float(fr.demand_high),
            "hold_ts":rec["hold_ts"],
            "hold_low":float(rec["hold_low"]),
            "pivot_low":pivot_low,
            "pivot_low_ts":pivot_ts,
            "pivot_low_confirm_ts":pivot_confirm,
        })
    S=pd.DataFrame(structural)
    W=W.merge(S,on="zone_id",how="left",validate="one_to_one")

    rows=[]
    for r in W.itertuples(index=False):
        levels={
            "TOUCH_LOW_BASELINE":float(r.touch_low_sl),
            "RECLAIM_LOW":float(r.reclaim_low_sl),
            "HOLD_LOW":float(r.hold_low),
            "PROTECTED_PIVOT_LOW":float(r.pivot_low) if np.isfinite(r.pivot_low) else np.nan,
            "DEMAND_LOW_TOUCH":float(r.demand_low),
            "DEMAND_LOW_CLOSE15":float(r.demand_low),
        }
        for cand in CANDS:
            sl=levels[cand]
            available=bool(np.isfinite(sl) and sl<r.entry_price and sl>=r.touch_low_sl-1e-12)
            out="UNAVAILABLE"; rt=pd.NaT; rr=np.nan
            if available:
                if cand=="DEMAND_LOW_CLOSE15":
                    out,rt,rr=resolve_close15(raw5,m15,r.entry_ts,float(r.entry_price),sl,float(r.tp1),end)
                else:
                    out,rt,rr=resolve_touch(raw5,r.entry_ts,float(r.entry_price),sl,float(r.tp1),end)

            base_dist=float(r.entry_price-r.touch_low_sl)
            cand_dist=float(r.entry_price-sl) if available else np.nan
            compression=1.0-cand_dist/base_dist if available and base_dist>0 else np.nan

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "entry_ts":r.entry_ts,"candidate":cand,
                "entry_price":r.entry_price,"tp1":r.tp1,
                "baseline_sl":r.touch_low_sl,"candidate_sl":sl,
                "baseline_sl_pct":r.baseline_sl_pct,
                "sl_pct":cand_dist/r.entry_price if available else np.nan,
                "compression":compression,
                "available":available,
                "outcome":out,"resolution_ts":rt,"realized_r":rr,
                "baseline_outcome":r.baseline_outcome,
                "baseline_resolution_ts":r.baseline_resolution_ts,
                "baseline_realized_r":r.baseline_realized_r,
            })
    L=pd.DataFrame(rows)

    # False-stop anatomy: baseline WIN but closer candidate LOSS.
    FSR=[]
    ridx=raw5.index
    for r in L[(L.available)&(L.baseline_outcome=="WIN")&(L.outcome=="LOSS")].itertuples(index=False):
        tp_ts=pd.Timestamp(r.baseline_resolution_ts)
        stop_ts=pd.Timestamp(r.resolution_ts)
        i0=int(ridx.searchsorted(stop_ts,side="left"))
        i1=int(ridx.searchsorted(tp_ts,side="right"))
        seg=raw5.iloc[i0:i1]
        min_low=float(seg.low.min()) if len(seg) else np.nan
        cand_risk=float(r.entry_price-r.candidate_sl)
        adverse_below=max(0.0,float(r.candidate_sl)-min_low) if np.isfinite(min_low) else np.nan
        FSR.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"candidate":r.candidate,
            "stop_ts":stop_ts,"later_tp1_ts":tp_ts,
            "minutes_stop_to_tp1":float((tp_ts-stop_ts)/pd.Timedelta(minutes=1)),
            "candidate_sl":r.candidate_sl,"min_low_before_later_tp1":min_low,
            "overshoot_pct_entry":adverse_below/r.entry_price if np.isfinite(adverse_below) else np.nan,
            "overshoot_candidate_r":adverse_below/cand_risk if cand_risk>0 else np.nan,
        })
    FS=pd.DataFrame(FSR)

    SUM=[]
    for per in ["DEV","REF"]:
        base=W[W.period==per]
        for cand in CANDS:
            q=L[(L.period==per)&(L.candidate==cand)]
            SUM.append({"period":per,"candidate":cand,**summarize(q,base)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        base=W[W.year==y]
        for cand in CANDS:
            q=L[(L.year==y)&(L.candidate==cand)]
            if len(q):
                Y.append({"year":y,"candidate":cand,**summarize(q,base)})
    Y=pd.DataFrame(Y)

    FSS=[]
    if len(FS):
        for per in ["DEV","REF"]:
            for cand in CANDS:
                q=FS[(FS.period==per)&(FS.candidate==cand)]
                FSS.append({
                    "period":per,"candidate":cand,"false_stops":len(q),
                    "median_minutes_to_later_tp1":float(q.minutes_stop_to_tp1.median()) if len(q) else np.nan,
                    "median_overshoot_pct_entry":float(q.overshoot_pct_entry.median()) if len(q) else np.nan,
                    "median_overshoot_candidate_r":float(q.overshoot_candidate_r.median()) if len(q) else np.nan,
                })
    FSS=pd.DataFrame(FSS)

    # Portfolio replacement diagnostic: replace only wide-Q4 baseline outcomes with candidate outcomes when available.
    PORT=[]
    for per in ["DEV","REF"]:
        full=P[P.period==per].copy()
        for cand in CANDS:
            qc=L[(L.period==per)&(L.candidate==cand)&(L.available)&(L.outcome.isin(["WIN","LOSS"]))]
            mp=qc.set_index("zone_id")[["outcome","realized_r"]].to_dict("index")
            outs=[]; rs=[]
            for rr in full.itertuples(index=False):
                if rr.zone_id in mp:
                    outs.append(mp[rr.zone_id]["outcome"]); rs.append(float(mp[rr.zone_id]["realized_r"]))
                else:
                    outs.append(rr.baseline_outcome); rs.append(float(rr.baseline_realized_r))
            a=pd.DataFrame({"outcome":outs,"realized_r":rs})
            econ=a[a.outcome.isin(["WIN","LOSS"])]
            wins=econ[econ.outcome=="WIN"]; losses=econ[econ.outcome=="LOSS"]
            PORT.append({
                "period":per,"candidate":cand,"trades":len(econ),
                "wins":len(wins),"losses":len(losses),
                "wr":len(wins)/len(econ) if len(econ) else np.nan,
                "expectancy_r":float(econ.realized_r.mean()) if len(econ) else np.nan,
                "total_r":float(econ.realized_r.sum()) if len(econ) else np.nan,
            })
    PORT=pd.DataFrame(PORT)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FS.to_csv(ROOT/f"{PFX}_FalseStopLedger.csv.gz",index=False,compression="gzip")
    FSS.to_csv(ROOT/f"{PFX}_FalseStopSummary.csv",index=False)
    PORT.to_csv(ROOT/f"{PFX}_PortfolioReplacement.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\nDEV_WIDE=110\nREF_WIDE=50\n",
        encoding="utf-8"
    )

    lines=[
      "# BNB B38-S18 — Wide-SL Structural Invalidation Audit","",
      f"Frozen wide-SL cut: `baseline_sl_pct > {WIDE_CUT:.6f}`","",
      "## Wide-SL candidate audit","",
      "| Period | Candidate | Avail | Med SL % | Compression | W-L | WR | Med WIN R | Exp | Total R | Baseline WIN retained | False-stop | LOSS→WIN |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.available}/{r.population} | {fmt_pct(r.median_sl_pct)} | "
            f"{fmt_pct(r.median_compression)} | {r.wins}-{r.losses} | {fmt_pct(r.wr)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{r.baseline_win_retained}/{r.baseline_wins_available} | {r.baseline_win_false_stop} "
            f"({fmt_pct(r.baseline_win_false_stop_rate_available)}) | {r.baseline_loss_to_win} |"
        )

    lines += ["","## False-stop anatomy","",
      "| Period | Candidate | False stops | Med stop→later TP1 | Med overshoot below stop | Med overshoot in candidate R |",
      "|---|---|---:|---:|---:|---:|"
    ]
    for r in FSS.itertuples(index=False):
        if r.false_stops:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_stops} | {fmt_num(r.median_minutes_to_later_tp1,1)}m | "
                f"{fmt_pct(r.median_overshoot_pct_entry)} | {fmt_num(r.median_overshoot_candidate_r)}R |"
            )

    lines += ["","## Full E2 portfolio if only wide-SL Q4 is replaced","",
      "| Period | Candidate | W-L | WR | Exp | Total R |",
      "|---|---|---:|---:|---:|---:|"
    ]
    for r in PORT.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.wins}-{r.losses} | {fmt_pct(r.wr)} | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R |"
        )

    lines += ["","## Annual stability","",
      "| Year | Candidate | Avail | W-L | WR | Exp | Total R | False-stop |",
      "|---:|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.available}/{r.population} | {r.wins}-{r.losses} | "
            f"{fmt_pct(r.wr)} | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | {r.baseline_win_false_stop} |"
        )

    lines += ["","## Interpretation boundary",
      "S18 audits whether wide baseline stops contain a closer causal invalidation point.",
      "A tighter level that creates many false stops is not considered structurally valid merely because its R multiple looks better.",
      "No candidate is promoted automatically."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S18_WIDE_SL_STRUCTURAL_INVALIDATION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
