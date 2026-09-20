#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s11_e2_economics as s11

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S12_E2_TARGET_SELECTION"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")

CANDS=[
 "T1_FULL_TP1",
 "T2_FULL_TP2_FALLBACK_TP1",
 "T3_FULL_TP3_FALLBACK_HIGHEST",
 "T4_FULL_EXPANSION_FALLBACK_TP1",
 "T5_FULL_H1_NEAREST_FALLBACK_TP1",
 "T6_FULL_MAJOR_NEAREST_FALLBACK_TP1",
 "R1_HALF_TP1_HALF_TP2_BE",
 "R2_HALF_TP1_HALF_MAJOR_BE",
]

def period(ts): return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def maxdd(rs):
    if not len(rs): return np.nan
    c=np.cumsum(np.asarray(rs,float))
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def maxls(seq):
    mx=cur=0
    for x in seq:
        if x=="LOSS": cur+=1; mx=max(mx,cur)
        else: cur=0
    return mx

def first_touch_after(raw5,start_ts,level,kind,end):
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return (i0+int(z[0])) if len(z) else None

def full_resolve(raw5,entry_ts,entry,sl,tp,end):
    idx=raw5.index
    ti=first_touch_after(raw5,entry_ts,tp,"HIGH",end)
    si=first_touch_after(raw5,entry_ts,sl,"LOW",end)
    rr=(tp-entry)/(entry-sl)
    if ti is None and si is None:return "UNRESOLVED",pd.NaT,np.nan
    if ti is not None and si is not None and ti==si:return "AMBIGUOUS",idx[ti],np.nan
    if ti is not None and (si is None or ti<si):return "WIN",idx[ti],float(rr)
    return "LOSS",idx[si],-1.0

def runner_resolve(raw5,entry_ts,entry,sl,tp1,tp2,end):
    idx=raw5.index
    rr1=(tp1-entry)/(entry-sl)
    rr2=(tp2-entry)/(entry-sl)

    t1=first_touch_after(raw5,entry_ts,tp1,"HIGH",end)
    s1i=first_touch_after(raw5,entry_ts,sl,"LOW",end)
    if t1 is None and s1i is None:return "UNRESOLVED",pd.NaT,np.nan
    if t1 is not None and s1i is not None and t1==s1i:return "AMBIGUOUS",idx[t1],np.nan
    if s1i is not None and (t1 is None or s1i<t1):return "LOSS",idx[s1i],-1.0

    # TP1 first: half realized. Runner becomes BE starting next 5m bar.
    partial=0.5*rr1
    tp1_ts=idx[t1]
    runner_start=tp1_ts
    t2=first_touch_after(raw5,runner_start,tp2,"HIGH",end)
    be=first_touch_after(raw5,runner_start,entry,"LOW",end)

    if t2 is None and be is None:
        return "PARTIAL_OPEN",pd.NaT,float(partial)
    if t2 is not None and be is not None and t2==be:
        return "AMBIGUOUS_RUNNER",idx[t2],np.nan
    if t2 is not None and (be is None or t2<be):
        return "WIN",idx[t2],float(partial+0.5*rr2)
    return "WIN",idx[be],float(partial)

def known_targets_at_entry(P,m15,h1,fam):
    m15_hi,_=s1.pivots_df(m15)
    h1_hi,_=s1.pivots_df(h1)
    F=fam.set_index("zone_id")
    rows=[]
    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        ladder=s3.objective_ladder(r.entry_ts,float(r.entry_price),fr.activation_ts,float(fr.expansion_high),m15_hi,h1_hi)
        levels=[float(x["level"]) for x in ladder]
        sources=[str(x["source"]) for x in ladder]

        tp1=levels[0] if len(levels)>=1 else np.nan
        tp2=levels[1] if len(levels)>=2 else np.nan
        tp3=levels[2] if len(levels)>=3 else np.nan

        # frozen expansion is known by construction
        expansion=float(fr.expansion_high) if float(fr.expansion_high)>float(r.entry_price) else np.nan

        q1=h1_hi[
            (h1_hi.pivot_ts>=fr.activation_ts)&
            (h1_hi.confirm_ts<=r.entry_ts)&
            (h1_hi.level>float(r.entry_price))
        ]
        h1nearest=float(q1.level.min()) if len(q1) else np.nan

        majors=[x for x in [expansion,h1nearest] if np.isfinite(x) and x>float(r.entry_price)]
        major=min(majors) if majors else np.nan

        rows.append({
            "zone_id":r.zone_id,"tp2":tp2,"tp3":tp3,
            "tp1_source":sources[0] if len(sources)>=1 else "",
            "tp2_source":sources[1] if len(sources)>=2 else "",
            "tp3_source":sources[2] if len(sources)>=3 else "",
            "expansion_target":expansion,"h1_nearest":h1nearest,"major_nearest":major,
            "known_target_count":len(levels),
        })
    return pd.DataFrame(rows)

def summarize(q,base):
    r=q[q.outcome.isin(["WIN","LOSS"])].sort_values(["entry_ts","zone_id"])
    w=r[r.outcome=="WIN"]; l=r[r.outcome=="LOSS"]
    pos=float(w.realized_r.sum()) if len(w) else 0
    neg=abs(float(l.realized_r.sum())) if len(l) else 0
    bw=set(base[base.outcome=="WIN"].zone_id); bl=set(base[base.outcome=="LOSS"].zone_id)
    cw=set(w.zone_id); cl=set(l.zone_id)
    return {
      "plans":len(q),"resolved":len(r),"wins":len(w),"losses":len(l),
      "wr":len(w)/len(r) if len(r) else np.nan,
      "median_win_r":float(w.realized_r.median()) if len(w) else np.nan,
      "expectancy_r":float(r.realized_r.mean()) if len(r) else np.nan,
      "total_r":float(r.realized_r.sum()) if len(r) else np.nan,
      "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
      "max_loss_streak":maxls(r.outcome.tolist()),
      "max_drawdown_r":maxdd(r.realized_r.tolist()) if len(r) else np.nan,
      "ambiguous":int(q.outcome.astype(str).str.startswith("AMBIGUOUS").sum()),
      "partial_open":int((q.outcome=="PARTIAL_OPEN").sum()),
      "baseline_wins":len(bw),"baseline_win_still_win":len(bw&cw),
      "baseline_win_to_loss":len(bw&cl),
      "baseline_losses":len(bl),"baseline_loss_to_win":len(bl&cw),
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"coverage {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end=raw.index.max()

    s1.START=START;s1.END=end;s3.END=end
    h1=s1.exact_exec(raw,"1h",12);h1=h1[h1.index<=end]
    m15=s1.exact_exec(raw,"15min",3);m15=m15[m15.index<=end]
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&(pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()
    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>DEV_END]
    if len(dev)!=788 or len(ref)!=463:raise RuntimeError(f"parity {len(dev)} {len(ref)}")

    P=s11.e2_plans(m15,h1,fam,end)
    K=known_targets_at_entry(P,m15,h1,fam)
    P=P.merge(K,on="zone_id",how="left",validate="one_to_one")
    P["period"]=[period(x) for x in P.first_touch_ts]

    # TP1 baseline
    b=[]
    for r in P.itertuples(index=False):
        if not np.isfinite(r.tp1) or not (r.entry_price>r.touch_low_sl):continue
        out,rt,real=full_resolve(raw5,r.entry_ts,r.entry_price,r.touch_low_sl,r.tp1,end)
        b.append({**r._asdict(),"outcome":out,"resolution_ts":rt,"realized_r":real})
    BASE=pd.DataFrame(b)

    rows=[]
    for r in P.itertuples(index=False):
        if not np.isfinite(r.tp1) or not (r.entry_price>r.touch_low_sl):continue
        for cand in CANDS:
            kind="FULL"; target=np.nan; target2=np.nan; source=""
            if cand=="T1_FULL_TP1":
                target=r.tp1; source=r.tp1_source
            elif cand=="T2_FULL_TP2_FALLBACK_TP1":
                target=r.tp2 if np.isfinite(r.tp2) else r.tp1
                source=r.tp2_source if np.isfinite(r.tp2) else r.tp1_source
            elif cand=="T3_FULL_TP3_FALLBACK_HIGHEST":
                if np.isfinite(r.tp3):target=r.tp3;source=r.tp3_source
                elif np.isfinite(r.tp2):target=r.tp2;source=r.tp2_source
                else:target=r.tp1;source=r.tp1_source
            elif cand=="T4_FULL_EXPANSION_FALLBACK_TP1":
                target=r.expansion_target if np.isfinite(r.expansion_target) else r.tp1
                source="EXPANSION_HIGH" if np.isfinite(r.expansion_target) else r.tp1_source
            elif cand=="T5_FULL_H1_NEAREST_FALLBACK_TP1":
                target=r.h1_nearest if np.isfinite(r.h1_nearest) else r.tp1
                source="H1_PIVOT_HIGH" if np.isfinite(r.h1_nearest) else r.tp1_source
            elif cand=="T6_FULL_MAJOR_NEAREST_FALLBACK_TP1":
                target=r.major_nearest if np.isfinite(r.major_nearest) else r.tp1
                source="MAJOR_EXPANSION_OR_H1" if np.isfinite(r.major_nearest) else r.tp1_source
            elif cand=="R1_HALF_TP1_HALF_TP2_BE":
                if np.isfinite(r.tp2) and r.tp2>r.tp1:
                    kind="RUNNER"; target=r.tp1;target2=r.tp2;source="TP1+TP2"
                else:
                    target=r.tp1;source=r.tp1_source
            elif cand=="R2_HALF_TP1_HALF_MAJOR_BE":
                if np.isfinite(r.major_nearest) and r.major_nearest>r.tp1:
                    kind="RUNNER";target=r.tp1;target2=r.major_nearest;source="TP1+MAJOR"
                else:
                    target=r.tp1;source=r.tp1_source

            if kind=="FULL":
                out,rt,real=full_resolve(raw5,r.entry_ts,r.entry_price,r.touch_low_sl,float(target),end)
            else:
                out,rt,real=runner_resolve(raw5,r.entry_ts,r.entry_price,r.touch_low_sl,float(target),float(target2),end)

            rows.append({
              "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":r.period,"year":r.year,
              "entry_ts":r.entry_ts,"candidate":cand,"exit_kind":kind,"target_source":source,
              "target1":target,"target2":target2,"outcome":out,"resolution_ts":rt,"realized_r":real
            })
    L=pd.DataFrame(rows)

    S=[]
    for per in ["DEV","REF"]:
        base=BASE[BASE.period==per]
        for cand in CANDS:
            S.append({"period":per,"candidate":cand,**summarize(L[(L.period==per)&(L.candidate==cand)],base)})
    S=pd.DataFrame(S)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        base=BASE[BASE.year==y]
        for cand in CANDS:
            q=L[(L.year==y)&(L.candidate==cand)]
            if len(q):Y.append({"year":y,"candidate":cand,**summarize(q,base)})
    Y=pd.DataFrame(Y)

    U=L.groupby(["period","candidate","target_source"],dropna=False).size().reset_index(name="n")

    P.to_csv(ROOT/f"{PFX}_Plans.csv.gz",index=False,compression="gzip")
    BASE.to_csv(ROOT/f"{PFX}_Baseline.csv.gz",index=False,compression="gzip")
    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    U.to_csv(ROOT/f"{PFX}_TargetUsage.csv",index=False)

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=3):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S12 — E2 Structural Target Selection","",
      "**E2 entry + touch-to-entry structural SL are frozen. Only target realization changes.**","",
      "## Overall","",
      "| Period | Candidate | W-L | WR | Med WIN R | Exp | PF | Max DD | Baseline WIN still WIN | Baseline LOSS→WIN |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
          f"| {r.period} | {r.candidate} | {r.wins}-{r.losses} | {pct(r.wr)} | {num(r.median_win_r)}R | "
          f"{num(r.expectancy_r)}R | {num(r.profit_factor)} | {num(r.max_drawdown_r)}R | "
          f"{r.baseline_win_still_win}/{r.baseline_wins} | {r.baseline_loss_to_win} |"
        )

    lines += ["","## Year stability","",
      "| Year | Candidate | W-L | WR | Exp | PF |",
      "|---:|---|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(f"| {r.year} | {r.candidate} | {r.wins}-{r.losses} | {pct(r.wr)} | {num(r.expectancy_r)}R | {num(r.profit_factor)} |")

    lines += ["","## Interpretation boundary",
      "Full-objective candidates test whether local TP1 is too close.",
      "Runner candidates preserve a first structural realization and only expose the remaining half to a farther known objective.",
      "No target policy is promoted automatically."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S12_E2_TARGET_SELECTION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
