#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s10_reaction_development as s10

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S11_E2_ECONOMICS"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")

CANDS=[
("A_TOUCH_LOW__TOUCH__TP1","TOUCH_LOW","TOUCH","TP1"),
("B_TOUCH_LOW__TOUCH__CAP1ZW","TOUCH_LOW","TOUCH","CAP1ZW"),
("C_TOUCH_LOW__CLOSE15__TP1","TOUCH_LOW","CLOSE15","TP1"),
("D_TOUCH_LOW__CLOSE15__CAP1ZW","TOUCH_LOW","CLOSE15","CAP1ZW"),
("E_RECLAIM_LOW__TOUCH__TP1","RECLAIM_LOW","TOUCH","TP1"),
("F_RECLAIM_LOW__TOUCH__CAP1ZW","RECLAIM_LOW","TOUCH","CAP1ZW"),
("G_RECLAIM_LOW__CLOSE15__TP1","RECLAIM_LOW","CLOSE15","TP1"),
("H_RECLAIM_LOW__CLOSE15__CAP1ZW","RECLAIM_LOW","CLOSE15","CAP1ZW"),
]

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def max_dd(rs):
    if not len(rs): return np.nan
    c=np.cumsum(np.asarray(rs,float))
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def max_loss_streak(seq):
    mx=cur=0
    for x in seq:
        if x=="LOSS": cur+=1; mx=max(mx,cur)
        else: cur=0
    return mx

def touch_resolve(raw5,entry_ts,entry,sl,tp,end):
    idx=raw5.index
    i0=int(idx.searchsorted(entry_ts,side="right")); i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return "UNRESOLVED",pd.NaT,np.nan
    hi=raw5.high.to_numpy(float,copy=False)[i0:i1]
    lo=raw5.low.to_numpy(float,copy=False)[i0:i1]
    th=np.flatnonzero(hi>=tp); sh=np.flatnonzero(lo<=sl)
    ti=int(th[0]) if len(th) else None; si=int(sh[0]) if len(sh) else None
    rr=(tp-entry)/(entry-sl)
    if ti is None and si is None:return "UNRESOLVED",pd.NaT,np.nan
    if ti is not None and si is not None and ti==si:return "AMBIGUOUS",idx[i0+ti],np.nan
    if ti is not None and (si is None or ti<si):return "WIN",idx[i0+ti],float(rr)
    return "LOSS",idx[i0+si],-1.0

def close15_resolve(raw5,m15,entry_ts,entry,sl,tp,end):
    rr=(tp-entry)/(entry-sl)

    ridx=raw5.index
    r0=int(ridx.searchsorted(entry_ts,side="right")); r1=int(ridx.searchsorted(end,side="right"))
    target_ts=pd.NaT
    if r1>r0:
        hi=raw5.high.to_numpy(float,copy=False)[r0:r1]
        z=np.flatnonzero(hi>=tp)
        if len(z): target_ts=ridx[r0+int(z[0])]

    midx=m15.index
    m0=int(midx.searchsorted(entry_ts,side="right")); m1=int(midx.searchsorted(end,side="right"))
    invalid_ts=pd.NaT; invalid_close=np.nan
    if m1>m0:
        cl=m15.close.to_numpy(float,copy=False)[m0:m1]
        z=np.flatnonzero(cl<sl)
        if len(z):
            j=m0+int(z[0]); invalid_ts=midx[j]; invalid_close=float(m15.close.iloc[j])

    if pd.notna(target_ts) and (pd.isna(invalid_ts) or target_ts<=invalid_ts):
        return "WIN",target_ts,float(rr)
    if pd.notna(invalid_ts):
        loss_r=(invalid_close-entry)/(entry-sl)
        return "LOSS",invalid_ts,float(loss_r)
    return "UNRESOLVED",pd.NaT,np.nan

def e2_plans(m15,h1,fam,end):
    _,piv_lo=s1.pivots_df(m15)
    m15_hi,_=s1.pivots_df(m15)
    h1_hi,_=s1.pivots_df(h1)
    rows=[]
    idx=m15.index

    for r in fam.itertuples(index=False):
        p=s10.candidate_plan(m15,r,"E2_RECLAIM_HOLD_THEN_BREAK",piv_lo,end)
        if p["status"]!="ENTRY": continue

        entry_ts=p["entry_ts"]; entry=float(p["entry_price"])
        # exact first touch -> entry low (S10 reference)
        i0=int(idx.searchsorted(r.first_touch_ts,side="left"))
        ie=int(idx.searchsorted(entry_ts,side="right"))
        touch_low=float(m15.low.iloc[i0:ie].min())

        # reclaim -> entry low
        ir=int(idx.searchsorted(p["reclaim_ts"],side="left"))
        reclaim_low=float(m15.low.iloc[ir:ie].min())

        ladder=s3.objective_ladder(entry_ts,entry,r.activation_ts,float(r.expansion_high),m15_hi,h1_hi)
        tp1=float(ladder[0]["level"]) if ladder else np.nan
        z1=float(r.demand_high+r.demand_width)

        rows.append({
            "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":period(r.first_touch_ts),
            "year":int(pd.Timestamp(r.first_touch_ts).year),
            "entry_ts":entry_ts,"entry_price":entry,"reclaim_ts":p["reclaim_ts"],
            "touch_low_sl":touch_low,"reclaim_low_sl":reclaim_low,
            "tp1":tp1,"z1":z1,
        })
    return pd.DataFrame(rows)

def summarize(q,baseline):
    r=q[q.outcome.isin(["WIN","LOSS"])].sort_values(["entry_ts","zone_id"])
    w=r[r.outcome=="WIN"]; l=r[r.outcome=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0

    bw=set(baseline[baseline.outcome=="WIN"].zone_id)
    bl=set(baseline[baseline.outcome=="LOSS"].zone_id)
    cw=set(r[r.outcome=="WIN"].zone_id)
    cl=set(r[r.outcome=="LOSS"].zone_id)

    wrs=w.realized_r.to_numpy(float) if len(w) else np.array([])
    return {
        "plans":len(q),"resolved":len(r),"wins":len(w),"losses":len(l),
        "ambiguous":int((q.outcome=="AMBIGUOUS").sum()),
        "unresolved":int((q.outcome=="UNRESOLVED").sum()),
        "wr":len(w)/len(r) if len(r) else np.nan,
        "median_win_r":float(np.median(wrs)) if len(wrs) else np.nan,
        "expectancy_r":float(r.realized_r.mean()) if len(r) else np.nan,
        "total_r":float(r.realized_r.sum()) if len(r) else np.nan,
        "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_loss_streak":max_loss_streak(r.outcome.tolist()),
        "max_drawdown_r":max_dd(r.realized_r.tolist()) if len(r) else np.nan,
        "baseline_wins":len(bw),
        "baseline_win_retained_as_win":len(bw&cw),
        "baseline_win_to_loss":len(bw&cl),
        "baseline_losses":len(bl),
        "baseline_loss_to_win":len(bl&cw),
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end=raw.index.max()

    s1.START=START; s1.END=end; s3.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end]
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end]
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()

    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>DEV_END]
    if len(dev)!=788 or len(ref)!=463:
        raise RuntimeError(f"parent parity drift dev={len(dev)} ref={len(ref)}")

    P=e2_plans(m15,h1,fam,end)

    # Baseline = exact S10 E2: touch-low SL, 5m touch, structural TP1.
    baseline_rows=[]
    for r in P.itertuples(index=False):
        if not np.isfinite(r.tp1): continue
        if not (r.entry_price>r.touch_low_sl): continue
        out,rt,rr=touch_resolve(raw5,r.entry_ts,r.entry_price,r.touch_low_sl,r.tp1,end)
        baseline_rows.append({**r._asdict(),"outcome":out,"resolution_ts":rt,"realized_r":rr})
    BASE=pd.DataFrame(baseline_rows)

    rows=[]
    for r in P.itertuples(index=False):
        for name,slkind,inv,targetkind in CANDS:
            sl=float(r.touch_low_sl if slkind=="TOUCH_LOW" else r.reclaim_low_sl)
            if not np.isfinite(r.tp1) or not (r.entry_price>sl):
                continue
            tp=float(r.tp1)
            if targetkind=="CAP1ZW" and r.z1>r.entry_price and r.z1<tp:
                tp=float(r.z1)

            if inv=="TOUCH":
                out,rt,real=touch_resolve(raw5,r.entry_ts,r.entry_price,sl,tp,end)
            else:
                out,rt,real=close15_resolve(raw5,m15,r.entry_ts,r.entry_price,sl,tp,end)

            rows.append({
                "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":r.period,"year":r.year,
                "entry_ts":r.entry_ts,"candidate":name,"sl_kind":slkind,"invalidation":inv,
                "target_kind":targetkind,"entry_price":r.entry_price,"sl_ref":sl,"target":tp,
                "outcome":out,"resolution_ts":rt,"realized_r":real
            })
    L=pd.DataFrame(rows)

    S=[]
    for per in ["DEV","REF"]:
        bp=BASE[BASE.period==per]
        for name,_,_,_ in CANDS:
            q=L[(L.period==per)&(L.candidate==name)]
            S.append({"period":per,"candidate":name,**summarize(q,bp)})
    S=pd.DataFrame(S)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        bp=BASE[BASE.year==y]
        for name,_,_,_ in CANDS:
            q=L[(L.year==y)&(L.candidate==name)]
            if len(q):
                Y.append({"year":y,"candidate":name,**summarize(q,bp)})
    Y=pd.DataFrame(Y)

    P.to_csv(ROOT/f"{PFX}_E2Plans.csv.gz",index=False,compression="gzip")
    BASE.to_csv(ROOT/f"{PFX}_Baseline.csv.gz",index=False,compression="gzip")
    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=3):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S11 — E2 Structural Economics Matrix","",
      "**E2 entry character frozen. Only SL/invalidation/target geometry changes.**","",
      "## Overall","",
      "| Period | Candidate | W-L | WR | Med WIN R | Exp | PF | Max L | Max DD | Baseline WIN still WIN | Baseline WIN→LOSS | Baseline LOSS→WIN |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.wins}-{r.losses} | {pct(r.wr)} | "
            f"{num(r.median_win_r)}R | {num(r.expectancy_r)}R | {num(r.profit_factor)} | "
            f"{r.max_loss_streak} | {num(r.max_drawdown_r)}R | "
            f"{r.baseline_win_retained_as_win}/{r.baseline_wins} | {r.baseline_win_to_loss} | {r.baseline_loss_to_win} |"
        )

    lines += ["","## Year stability","",
      "| Year | Candidate | W-L | WR | Exp | PF |",
      "|---:|---|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(f"| {r.year} | {r.candidate} | {r.wins}-{r.losses} | {pct(r.wr)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} |")

    lines += ["","## Interpretation boundary",
      "S11 does not change the E2 detector or entry timing.",
      "Candidates with higher WR but negative/near-zero expectancy are not considered economically solved.",
      "No candidate is promoted automatically."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S11_E2_ECONOMICS_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
