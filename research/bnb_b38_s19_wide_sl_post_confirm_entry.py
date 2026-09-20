#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s14_post_tp1_continuation as s14
import bnb_b38_s18_wide_sl_structural_invalidation as s18

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S19_WIDE_SL_POST_CONFIRM_ENTRY"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727

CANDS=[
    "MARKET_BREAK_CLOSE",
    "LIMIT_BREAK_LEVEL_RETEST",
    "LIMIT_HOLD_CLOSE_RETEST",
    "LIMIT_RECLAIM_CLOSE_RETEST",
    "LIMIT_DEMAND_HIGH_RETEST",
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

def first_touch_after(raw5,start_ts,level,kind,end):
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def resolve_market(raw5,entry_ts,entry,sl,tp,end):
    idx=raw5.index
    ti=first_touch_after(raw5,entry_ts,tp,"HIGH",end)
    si=first_touch_after(raw5,entry_ts,sl,"LOW",end)
    rr=(tp-entry)/(entry-sl)
    if ti is None and si is None:return "UNRESOLVED",pd.NaT,np.nan
    if ti is not None and si is not None and ti==si:return "AMBIGUOUS",idx[ti],np.nan
    if ti is not None and (si is None or ti<si):return "WIN",idx[ti],float(rr)
    return "LOSS",idx[si],-1.0

def limit_trade(raw5,confirm_ts,limit,sl,tp,end):
    idx=raw5.index
    i0=int(idx.searchsorted(confirm_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return {"status":"UNRESOLVED","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":np.nan}

    lo=raw5.low.to_numpy(float,copy=False)
    hi=raw5.high.to_numpy(float,copy=False)

    fill_i=None
    for i in range(i0,i1):
        # Stop/target reached before fill => order never becomes a trade.
        pre_tp=hi[i]>=tp
        pre_sl=lo[i]<=sl
        can_fill=lo[i]<=limit<=hi[i]

        if can_fill:
            # Same-bar order is unknowable if TP or SL also traded.
            if pre_tp or pre_sl:
                return {"status":"AMBIGUOUS_FILL_BAR","fill_ts":idx[i],"resolution_ts":idx[i],"realized_r":np.nan}
            fill_i=i
            break
        if pre_tp:
            return {"status":"NO_FILL_TP_FIRST","fill_ts":pd.NaT,"resolution_ts":idx[i],"realized_r":0.0}
        if pre_sl:
            return {"status":"NO_FILL_SL_FIRST","fill_ts":pd.NaT,"resolution_ts":idx[i],"realized_r":0.0}

    if fill_i is None:
        return {"status":"NO_FILL_END","fill_ts":pd.NaT,"resolution_ts":pd.NaT,"realized_r":0.0}

    risk=limit-sl
    if not (risk>0):
        return {"status":"INVALID_GEOMETRY","fill_ts":idx[fill_i],"resolution_ts":pd.NaT,"realized_r":np.nan}
    rr=(tp-limit)/risk

    # Resolution starts strictly after fill bar to avoid intrabar ordering claims.
    start=idx[fill_i]
    ti=first_touch_after(raw5,start,tp,"HIGH",end)
    si=first_touch_after(raw5,start,sl,"LOW",end)
    if ti is None and si is None:
        return {"status":"UNRESOLVED_AFTER_FILL","fill_ts":idx[fill_i],"resolution_ts":pd.NaT,"realized_r":np.nan}
    if ti is not None and si is not None and ti==si:
        return {"status":"AMBIGUOUS_AFTER_FILL","fill_ts":idx[fill_i],"resolution_ts":idx[ti],"realized_r":np.nan}
    if ti is not None and (si is None or ti<si):
        return {"status":"WIN","fill_ts":idx[fill_i],"resolution_ts":idx[ti],"realized_r":float(rr)}
    return {"status":"LOSS","fill_ts":idx[fill_i],"resolution_ts":idx[si],"realized_r":-1.0}

def summarize(q,base):
    avail=q[q.available].copy()
    filled=avail[avail.status.isin(["WIN","LOSS","AMBIGUOUS_AFTER_FILL","UNRESOLVED_AFTER_FILL"])].copy()
    r=filled[filled.status.isin(["WIN","LOSS"])].sort_values(["entry_ts","zone_id"])
    w=r[r.status=="WIN"]; l=r[r.status=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    bw=set(base[base.baseline_outcome=="WIN"].zone_id)
    bl=set(base[base.baseline_outcome=="LOSS"].zone_id)
    fill_ids=set(filled.zone_id)
    win_ids=set(w.zone_id)
    loss_ids=set(l.zone_id)
    avail_ids=set(avail.zone_id)

    nofill=avail[avail.status.str.startswith("NO_FILL")]
    return {
        "population":len(q),
        "available":len(avail),
        "availability_rate":len(avail)/len(q) if len(q) else np.nan,
        "filled":len(filled),
        "fill_rate_available":len(filled)/len(avail) if len(avail) else np.nan,
        "resolved":len(r),
        "wins":len(w),"losses":len(l),
        "wr":len(w)/len(r) if len(r) else np.nan,
        "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
        "expectancy_r_filled":float(r.realized_r.mean()) if len(r) else np.nan,
        "total_r_filled":float(r.realized_r.sum()) if len(r) else np.nan,
        "pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_dd_r":maxdd(r.realized_r.tolist()) if len(r) else np.nan,
        "max_loss_streak":maxls(r.status.tolist()),
        "median_entry_improvement_pct":float(avail.entry_improvement_pct.median()) if len(avail) else np.nan,
        "median_risk_compression":float(avail.risk_compression.median()) if len(avail) else np.nan,
        "baseline_wins_available":len(bw&avail_ids),
        "baseline_wins_filled":len(bw&fill_ids),
        "baseline_wins_retained_win":len(bw&win_ids),
        "baseline_wins_missed_nofill":len(bw&set(nofill.zone_id)),
        "baseline_wins_became_loss":len(bw&loss_ids),
        "baseline_losses_available":len(bl&avail_ids),
        "baseline_losses_filled":len(bl&fill_ids),
        "baseline_losses_avoided_nofill":len(bl&set(nofill.zone_id)),
        "baseline_losses_became_win":len(bl&win_ids),
        "ambiguous_fill_bar":int((avail.status=="AMBIGUOUS_FILL_BAR").sum()),
        "ambiguous_after_fill":int((avail.status=="AMBIGUOUS_AFTER_FILL").sum()),
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

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=pd.Timestamp("2022-01-01T00:00:00Z"))&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    F=fam.set_index("zone_id")

    P=P.copy()
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    W=P[P.baseline_sl_pct>WIDE_CUT].copy()
    if int((W.period=="DEV").sum())!=110 or int((W.period=="REF").sum())!=50:
        raise RuntimeError("wide parity drift")

    structs=[]
    for r in W.itertuples(index=False):
        fr=F.loc[r.zone_id]
        rec=s18.reconstruct_e2(m15,fr,end)
        if rec is None: raise RuntimeError(f"reconstruct fail {r.zone_id}")
        if pd.Timestamp(rec["entry_ts"])!=pd.Timestamp(r.entry_ts):
            raise RuntimeError(f"entry mismatch {r.zone_id}")

        reclaim_i=rec["reclaim_i"]; hold_i=rec["hold_i"]
        reclaim_close=float(m15.close.iloc[reclaim_i])
        hold_close=float(m15.close.iloc[hold_i])
        reclaim_high=float(m15.high.iloc[reclaim_i])
        break_level=max(reclaim_high,float(rec["hold_high"]))

        structs.append({
            "zone_id":r.zone_id,
            "break_level":break_level,
            "hold_close":hold_close,
            "reclaim_close":reclaim_close,
            "demand_high":float(fr.demand_high),
        })
    W=W.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")

    rows=[]
    for r in W.itertuples(index=False):
        levels={
            "MARKET_BREAK_CLOSE":float(r.entry_price),
            "LIMIT_BREAK_LEVEL_RETEST":float(r.break_level),
            "LIMIT_HOLD_CLOSE_RETEST":float(r.hold_close),
            "LIMIT_RECLAIM_CLOSE_RETEST":float(r.reclaim_close),
            "LIMIT_DEMAND_HIGH_RETEST":float(r.demand_high),
        }
        for cand in CANDS:
            level=levels[cand]
            if cand=="MARKET_BREAK_CLOSE":
                available=True
                out,rt,rr=resolve_market(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),float(r.tp1),end)
                status=out; fill_ts=r.entry_ts
            else:
                available=bool(
                    np.isfinite(level) and
                    level<float(r.entry_price)-1e-12 and
                    level>float(r.touch_low_sl)+1e-12 and
                    level<float(r.tp1)-1e-12
                )
                if available:
                    z=limit_trade(raw5,r.entry_ts,level,float(r.touch_low_sl),float(r.tp1),end)
                    status=z["status"]; fill_ts=z["fill_ts"]; rt=z["resolution_ts"]; rr=z["realized_r"]
                else:
                    status="UNAVAILABLE"; fill_ts=pd.NaT; rt=pd.NaT; rr=np.nan

            base_risk=float(r.entry_price-r.touch_low_sl)
            new_risk=float(level-r.touch_low_sl) if available else np.nan
            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
                "candidate":cand,"available":available,
                "baseline_entry":r.entry_price,"candidate_entry":level,
                "structural_sl":r.touch_low_sl,"tp1":r.tp1,
                "baseline_risk":base_risk,"candidate_risk":new_risk,
                "entry_improvement_pct":(float(r.entry_price)-level)/float(r.entry_price) if available else np.nan,
                "risk_compression":1.0-new_risk/base_risk if available and base_risk>0 else np.nan,
                "status":status,"fill_ts":fill_ts,"resolution_ts":rt,"realized_r":rr,
                "baseline_outcome":r.baseline_outcome,"baseline_realized_r":r.baseline_realized_r,
            })
    L=pd.DataFrame(rows)

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
            if len(q): Y.append({"year":y,"candidate":cand,**summarize(q,base)})
    Y=pd.DataFrame(Y)

    # Full portfolio: wide-Q4 uses candidate; nonfills/unavailable/ambiguous are no-trade (0R).
    PORT=[]
    for per in ["DEV","REF"]:
        full=P[P.period==per].copy()
        wide_ids=set(W[W.period==per].zone_id)
        for cand in CANDS:
            qc=L[(L.period==per)&(L.candidate==cand)].set_index("zone_id")
            rs=[]; outcomes=[]; traded=0
            for r in full.itertuples(index=False):
                if r.zone_id not in wide_ids:
                    rs.append(float(r.baseline_realized_r)); outcomes.append(r.baseline_outcome); traded+=1
                    continue
                row=qc.loc[r.zone_id]
                if row.status in ("WIN","LOSS"):
                    rs.append(float(row.realized_r)); outcomes.append(row.status); traded+=1
                else:
                    rs.append(0.0); outcomes.append("NO_TRADE")
            a=pd.DataFrame({"r":rs,"outcome":outcomes})
            econ=a[a.outcome.isin(["WIN","LOSS"])]
            wins=(econ.outcome=="WIN").sum(); losses=(econ.outcome=="LOSS").sum()
            PORT.append({
                "period":per,"candidate":cand,"all_e2_plans":len(a),"traded":traded,
                "wins":int(wins),"losses":int(losses),
                "wr":wins/len(econ) if len(econ) else np.nan,
                "expectancy_per_all_e2":float(a.r.mean()),
                "total_r":float(a.r.sum()),
                "expectancy_per_traded":float(econ.r.mean()) if len(econ) else np.nan,
            })
    PORT=pd.DataFrame(PORT)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    PORT.to_csv(ROOT/f"{PFX}_PortfolioReplacement.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\nDEV_WIDE=110\nREF_WIDE=50\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S19 — Wide-SL Post-Confirmation Entry Audit","",
        f"Frozen wide-SL cut: `baseline_sl_pct > {WIDE_CUT:.6f}`","",
        "Detector and original structural SL remain unchanged. Retest orders activate only after E2 break confirmation.","",
        "## Q4 entry audit","",
        "| Period | Candidate | Avail | Fill | Entry improvement | Risk compression | W-L | WR | Med WIN R | Exp filled | Total R filled | WIN filled/available | WIN missed | WIN→LOSS | LOSS avoided |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.available}/{r.population} | {r.filled}/{r.available} ({fmt_pct(r.fill_rate_available)}) | "
            f"{fmt_pct(r.median_entry_improvement_pct)} | {fmt_pct(r.median_risk_compression)} | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr)} | {fmt_num(r.median_win_r)}R | "
            f"{fmt_num(r.expectancy_r_filled)}R | {fmt_num(r.total_r_filled)}R | "
            f"{r.baseline_wins_filled}/{r.baseline_wins_available} | {r.baseline_wins_missed_nofill} | "
            f"{r.baseline_wins_became_loss} | {r.baseline_losses_avoided_nofill} |"
        )

    lines += ["","## Full E2 portfolio if Q4 waits for retest","",
      "Nonfills/unavailable/ambiguous Q4 cases are treated as no-trade (0R).","",
      "| Period | Candidate | Traded | W-L | WR | Exp / all E2 | Exp / traded | Total R |",
      "|---|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in PORT.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.traded}/{r.all_e2_plans} | {r.wins}-{r.losses} | "
            f"{fmt_pct(r.wr)} | {fmt_num(r.expectancy_per_all_e2)}R | "
            f"{fmt_num(r.expectancy_per_traded)}R | {fmt_num(r.total_r)}R |"
        )

    lines += ["","## Annual stability","",
      "| Year | Candidate | Avail | Fill | W-L | WR | Exp filled | WIN missed | LOSS avoided |",
      "|---:|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.available}/{r.population} | {r.filled}/{r.available} | "
            f"{r.wins}-{r.losses} | {fmt_pct(r.wr)} | {fmt_num(r.expectancy_r_filled)}R | "
            f"{r.baseline_wins_missed_nofill} | {r.baseline_losses_avoided_nofill} |"
        )

    lines += ["","## Interpretation boundary",
      "S19 does not alter E2 confirmation or structural invalidation.",
      "A retest candidate is useful only if better R is not purchased by missing too many baseline winners or becoming regime-dependent.",
      "No candidate is promoted automatically."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S19_WIDE_SL_POST_CONFIRM_ENTRY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
