#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S10_REACTION_DEVELOPMENT"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
REF_START=pd.Timestamp("2025-01-01T00:00:00Z")
CANDS=["E1_RECLAIM_HIGH_BREAK","E2_RECLAIM_HOLD_THEN_BREAK","E3_PROTECTED_LOW_THEN_BREAK"]

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level"),
}

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def resolve(raw5,entry_ts,entry,sl,tp,end):
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

def zone_validity(m15,fam,end):
    idx=m15.index; rows=[]
    for r in fam.itertuples(index=False):
        z1=float(r.demand_high+r.demand_width)
        i0=int(idx.searchsorted(r.first_touch_ts,side="right"))
        i1=int(idx.searchsorted(end,side="right"))
        hit=False
        for i in range(i0,i1):
            c=float(m15.close.iloc[i])
            if c<float(r.demand_low):break
            if c>z1:
                hit=True;break
        rows.append({"zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"zone_1zw_valid":hit})
    return pd.DataFrame(rows)

def find_reclaim(m15,r,end):
    idx=m15.index
    i0=int(idx.searchsorted(r.first_touch_ts,side="left"))
    i1=int(idx.searchsorted(end,side="right"))
    low=float(r.touch_low)
    for i in range(i0,i1):
        b=m15.iloc[i]; low=min(low,float(b.low))
        c=float(b.close)
        if i>i0 and c<float(r.demand_low):
            return None,"INVALIDATED",low
        if c>float(r.demand_high):
            return i,"RECLAIM",low
    return None,"NO_STATE",low

def candidate_plan(m15,r,cand,piv_lo,end):
    idx=m15.index
    ri,status,low=find_reclaim(m15,r,end)
    if ri is None:
        return {"status":status,"entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                "reclaim_ts":pd.NaT,"wait_bars":np.nan}

    rb=m15.iloc[ri]; reclaim_high=float(rb.high); reclaim_ts=idx[ri]
    i1=int(idx.searchsorted(end,side="right"))

    if cand=="E1_RECLAIM_HIGH_BREAK":
        for j in range(ri+1,i1):
            b=m15.iloc[j]; low=min(low,float(b.low))
            if float(b.close)<float(r.demand_low):
                return {"status":"INVALIDATED","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                        "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
            if float(b.close)>reclaim_high:
                return {"status":"ENTRY","entry_ts":idx[j],"entry_price":float(b.close),"sl_ref":low,
                        "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
        return {"status":"NO_STATE","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                "reclaim_ts":reclaim_ts,"wait_bars":i1-ri-1}

    if cand=="E2_RECLAIM_HOLD_THEN_BREAK":
        hold_i=None; hold_high=np.nan
        for j in range(ri+1,i1):
            b=m15.iloc[j]; low=min(low,float(b.low))
            if float(b.close)<float(r.demand_low):
                return {"status":"INVALIDATED","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                        "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
            if hold_i is None:
                if float(b.close)>=float(r.demand_high):
                    hold_i=j; hold_high=float(b.high)
                continue
            level=max(reclaim_high,hold_high)
            if float(b.close)>level:
                return {"status":"ENTRY","entry_ts":idx[j],"entry_price":float(b.close),"sl_ref":low,
                        "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
        return {"status":"NO_STATE","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                "reclaim_ts":reclaim_ts,"wait_bars":i1-ri-1}

    if cand=="E3_PROTECTED_LOW_THEN_BREAK":
        q=piv_lo[(piv_lo.pivot_ts>reclaim_ts)&(piv_lo.confirm_ts<=end)]
        for pr in q.sort_values(["confirm_ts","pivot_ts"]).itertuples(index=False):
            ci=int(idx.searchsorted(pr.confirm_ts,side="left"))
            # Ensure no demand close invalidation through pivot confirmation.
            seg=m15.iloc[ri+1:ci+1]
            if len(seg):
                low=min(low,float(seg.low.min()))
                bad=seg[seg.close<float(r.demand_low)]
                if len(bad):
                    return {"status":"INVALIDATED","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                            "reclaim_ts":reclaim_ts,"wait_bars":int(idx.get_loc(bad.index[0])-ri)}
            for j in range(ci+1,i1):
                b=m15.iloc[j]; low=min(low,float(b.low))
                if float(b.close)<float(r.demand_low):
                    return {"status":"INVALIDATED","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                            "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
                if float(b.close)>reclaim_high:
                    return {"status":"ENTRY","entry_ts":idx[j],"entry_price":float(b.close),"sl_ref":low,
                            "reclaim_ts":reclaim_ts,"wait_bars":j-ri}
            break
        return {"status":"NO_STATE","entry_ts":pd.NaT,"entry_price":np.nan,"sl_ref":np.nan,
                "reclaim_ts":reclaim_ts,"wait_bars":i1-ri-1}

    raise RuntimeError(cand)

def baseline_s5(m15,h1,fam,raw5,end,zonev):
    P=s3.adaptive_plan(m15,h1,fam).merge(zonev,on=["zone_id","first_touch_ts"],how="left")
    rows=[]
    for r in P[P.execution_status=="ENTRY"].itertuples(index=False):
        pol,tcol=MODE_POLICY[r.execution_mode]
        tp=getattr(r,tcol)
        if not np.isfinite(tp):continue
        out,rt,real=resolve(raw5,r.entry_ts,float(r.entry_price),float(r.sl_reference),float(tp),end)
        if out not in ("WIN","LOSS"):continue
        rows.append({"zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":period(r.first_touch_ts),
                     "baseline_outcome":out,"zone_1zw_valid":bool(r.zone_1zw_valid)})
    return pd.DataFrame(rows)

def stats(q):
    r=q[q.outcome.isin(["WIN","LOSS"])].copy()
    w=r[r.outcome=="WIN"]; l=r[r.outcome=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0.0
    return {"resolved":len(r),"wins":len(w),"losses":len(l),
            "wr":len(w)/len(r) if len(r) else np.nan,
            "expectancy_r":float(r.realized_r.mean()) if len(r) else np.nan,
            "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan)}

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1();ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end=raw.index.max()

    s1.START=START;s1.END=end;s3.END=end
    h1=s1.exact_exec(raw,"1h",12);h1=h1[h1.index<=end]
    m15=s1.exact_exec(raw,"15min",3);m15=m15[m15.index<=end]
    raw5=raw[["open","high","low","close"]].astype(float)
    _,piv_lo=s1.pivots_df(m15)
    m15_hi,_=s1.pivots_df(m15)
    h1_hi,_=s1.pivots_df(h1)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()
    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>=REF_START]
    if len(dev)!=788 or len(ref)!=463:
        raise RuntimeError(f"parent parity drift {len(dev)} {len(ref)}")

    Z=zone_validity(m15,fam,end)
    B=baseline_s5(m15,h1,fam,raw5,end,Z)
    base_by_key=B.set_index("zone_id")

    rows=[]
    for r in fam.itertuples(index=False):
        for cand in CANDS:
            p=candidate_plan(m15,r,cand,piv_lo,end)
            out="";rt=pd.NaT;real=np.nan;target=np.nan;target_rr=np.nan
            if p["status"]=="ENTRY":
                ladder=s3.objective_ladder(p["entry_ts"],p["entry_price"],r.activation_ts,
                                           float(r.expansion_high),m15_hi,h1_hi)
                if not ladder:
                    p["status"]="NO_TARGET"
                else:
                    target=float(ladder[0]["level"])
                    target_rr=(target-p["entry_price"])/(p["entry_price"]-p["sl_ref"])
                    if p["entry_price"]<=p["sl_ref"]:
                        p["status"]="INVALID_RISK"
                    else:
                        out,rt,real=resolve(raw5,p["entry_ts"],p["entry_price"],p["sl_ref"],target,end)
            if r.zone_id in base_by_key.index:
                br=base_by_key.loc[r.zone_id]
                bout=str(br.baseline_outcome)
                zvalid=bool(br.zone_1zw_valid)
            else:
                bout="NO_BASELINE_RESOLVED"
                zrow=Z[Z.zone_id==r.zone_id].iloc[0]
                zvalid=bool(zrow.zone_1zw_valid)
            rows.append({
                "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":period(r.first_touch_ts),
                "candidate":cand,"state_status":p["status"],"reclaim_ts":p["reclaim_ts"],
                "entry_ts":p["entry_ts"],"entry_price":p["entry_price"],"sl_ref":p["sl_ref"],
                "wait_bars":p["wait_bars"],"target_level":target,"target_rr":target_rr,
                "outcome":out,"resolution_ts":rt,"realized_r":real,
                "baseline_outcome":bout,"zone_1zw_valid":zvalid
            })
    L=pd.DataFrame(rows)

    S=[]
    for per in ["DEV","REF"]:
        bp=B[B.period==per]
        bw=set(bp[bp.baseline_outcome=="WIN"].zone_id)
        bl=set(bp[bp.baseline_outcome=="LOSS"].zone_id)
        zfail=set(bp[(bp.baseline_outcome=="LOSS")&(~bp.zone_1zw_valid)].zone_id)
        parent_n=len(dev) if per=="DEV" else len(ref)
        for cand in CANDS:
            q=L[(L.period==per)&(L.candidate==cand)]
            st=stats(q)
            entered=set(q[q.state_status=="ENTRY"].zone_id)
            cwin=set(q[q.outcome=="WIN"].zone_id)
            invalid=set(q[q.state_status=="INVALIDATED"].zone_id)
            S.append({
                "period":per,"candidate":cand,"parent_n":parent_n,
                "entries":int((q.state_status=="ENTRY").sum()),
                "invalidated_before_entry":int((q.state_status=="INVALIDATED").sum()),
                "no_state":int((q.state_status=="NO_STATE").sum()),
                "no_target":int((q.state_status=="NO_TARGET").sum()),
                "baseline_wins":len(bw),
                "baseline_wins_entered":len(bw&entered),
                "baseline_win_entry_retention":len(bw&entered)/len(bw) if bw else np.nan,
                "baseline_wins_still_win":len(bw&cwin),
                "baseline_win_outcome_retention":len(bw&cwin)/len(bw) if bw else np.nan,
                "baseline_losses_avoided_before_entry":len(bl&invalid),
                "genuine_zone_failures_avoided_before_entry":len(zfail&invalid),
                **st
            })
    S=pd.DataFrame(S)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.3f}"

    lines=[
      "# BNB B38-S10 — Reaction Development Entry State Machine","",
      "**Reclaim is now a state, not automatically an entry.**","",
      "## Results","",
      "| Period | Candidate | Entries | Invalidated pre-entry | No state | W-L | WR | Exp | PF | Baseline WINs entered | Baseline WINs still WIN | Baseline LOSS avoided | Genuine zone-fail avoided |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.entries} | {r.invalidated_before_entry} | {r.no_state} | "
            f"{r.wins}-{r.losses} | {pct(r.wr)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} | "
            f"{r.baseline_wins_entered}/{r.baseline_wins} ({pct(r.baseline_win_entry_retention)}) | "
            f"{r.baseline_wins_still_win}/{r.baseline_wins} ({pct(r.baseline_win_outcome_retention)}) | "
            f"{r.baseline_losses_avoided_before_entry} | {r.genuine_zone_failures_avoided_before_entry} |"
        )

    lines += ["","## Interpretation boundary",
      "Invalidated-before-entry events are avoided trades, not converted wins.",
      "The key preservation metric is how many historical baseline WIN events still progress to an entry and remain WIN under the later state-machine geometry.",
      "No S10 candidate is promoted automatically."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S10_REACTION_DEVELOPMENT_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
