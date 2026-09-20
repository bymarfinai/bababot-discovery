#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S8_LOSS_RECOVERY_MATRIX"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
REF_START=pd.Timestamp("2025-01-01T00:00:00Z")

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level","tp2_rr"),
}

CANDS=[
    "BASELINE",
    "C1_NO_CHASE_AFTER_1ZW",
    "C2_CLOSE_BASED_INVALIDATION",
    "C3_DELAYED_SWEEP_USE_TP1",
    "C4_CAP_TARGET_AT_1ZW",
    "C5_CLOSE_INVALIDATION_PLUS_1ZW_CAP",
]

def zone_paths(m15,fam,end):
    idx=m15.index; rows=[]
    for r in fam.itertuples(index=False):
        z1=float(r.demand_high+r.demand_width)
        start_i=int(idx.searchsorted(r.first_touch_ts,side="right"))
        end_i=int(idx.searchsorted(end,side="right"))
        z1_ts=invalid_ts=pd.NaT
        for i in range(start_i,end_i):
            t=idx[i]; c=float(m15.close.iloc[i])
            if c<float(r.demand_low):
                invalid_ts=t; break
            if pd.isna(z1_ts) and c>z1:z1_ts=t
        rows.append({
            "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,
            "z1_level":z1,"z1_hit_ts":z1_ts,
            "zone_1zw_valid":pd.notna(z1_ts),
            "zone_invalid_close_ts":invalid_ts,
        })
    return pd.DataFrame(rows)

def touch_resolve(raw5,entry_ts,sl,tp,end):
    q=raw5[(raw5.index>entry_ts)&(raw5.index<=end)]
    for t,b in q.iterrows():
        st=float(b.low)<=sl
        tg=float(b.high)>=tp
        if st and tg:return "AMBIGUOUS",t,np.nan
        if tg:return "WIN",t,(tp-entry_price_global)/(entry_price_global-sl)
        if st:return "LOSS",t,-1.0
    return "UNRESOLVED",pd.NaT,np.nan

def touch_resolve_explicit(raw5,entry_ts,entry,sl,tp,end):
    q=raw5[(raw5.index>entry_ts)&(raw5.index<=end)]
    rr=(tp-entry)/(entry-sl)
    for t,b in q.iterrows():
        st=float(b.low)<=sl; tg=float(b.high)>=tp
        if st and tg:return "AMBIGUOUS",t,np.nan
        if tg:return "WIN",t,float(rr)
        if st:return "LOSS",t,-1.0
    return "UNRESOLVED",pd.NaT,np.nan

def close_resolve(raw5,m15,entry_ts,entry,sl,tp,end):
    rr=(tp-entry)/(entry-sl)
    closes=m15[(m15.index>entry_ts)&(m15.index<=end)]
    last=entry_ts
    for t,b15 in closes.iterrows():
        seg=raw5[(raw5.index>last)&(raw5.index<=t)]
        if len(seg) and (seg.high>=tp).any():
            hit=seg.index[(seg.high>=tp)][0]
            return "WIN",hit,float(rr)
        if float(b15.close)<sl:
            loss_r=(float(b15.close)-entry)/(entry-sl)
            return "LOSS",t,float(loss_r)
        last=t
    return "UNRESOLVED",pd.NaT,np.nan

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def streak_loss(seq):
    mx=cur=0
    for x in seq:
        if x=="LOSS":cur+=1;mx=max(mx,cur)
        else:cur=0
    return mx

def maxdd(rs):
    if not rs:return np.nan
    c=np.cumsum(np.asarray(rs,float))
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def perf(q):
    r=q[q.cand_outcome.isin(["WIN","LOSS"])].sort_values(["entry_ts","zone_id"])
    w=r[r.cand_outcome=="WIN"]; l=r[r.cand_outcome=="LOSS"]
    pos=float(w.cand_realized_r.sum()) if len(w) else 0.0
    neg=abs(float(l.cand_realized_r.sum())) if len(l) else 0.0
    return {
        "resolved":len(r),"wins":len(w),"losses":len(l),
        "wr":len(w)/len(r) if len(r) else np.nan,
        "expectancy_r":float(r.cand_realized_r.mean()) if len(r) else np.nan,
        "total_r":float(r.cand_realized_r.sum()) if len(r) else np.nan,
        "profit_factor":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "max_loss_streak":streak_loss(r.cand_outcome.tolist()),
        "max_drawdown_r":maxdd(r.cand_realized_r.tolist()) if len(r) else np.nan,
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
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
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()
    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>=REF_START]
    if len(dev)!=788 or len(ref)!=463:
        raise RuntimeError(f"parent parity drift {len(dev)} {len(ref)}")

    Z=zone_paths(m15,fam,end)
    P=s3.adaptive_plan(m15,h1,fam)
    E=P[P.execution_status=="ENTRY"].copy().merge(Z,on=["zone_id","first_touch_ts"],how="left",validate="one_to_one")

    base=[]
    for r in E.itertuples(index=False):
        pol,tcol,rrcol=MODE_POLICY[r.execution_mode]
        tp=getattr(r,tcol); rr=getattr(r,rrcol)
        if not np.isfinite(tp) or not np.isfinite(rr):
            continue
        out,rt,real=touch_resolve_explicit(raw5,r.entry_ts,float(r.entry_price),float(r.sl_reference),float(tp),end)
        late=bool(r.zone_1zw_valid and (
            pd.Timestamp(r.z1_hit_ts)<=pd.Timestamp(r.entry_ts) or
            float(r.entry_price)>=float(r.z1_level)
        ))
        # S7 loss attribution
        false_stop=False
        if r.zone_1zw_valid and not late:
            q=raw5[(raw5.index>r.entry_ts)&(raw5.index<=r.z1_hit_ts)]
            false_stop=bool(len(q) and (q.low<=float(r.sl_reference)).any())
        attrib=""
        if out=="LOSS":
            if not bool(r.zone_1zw_valid):attrib="ZONE_NOT_1ZW_VALID"
            elif late:attrib="ENTRY_LATE_AFTER_1ZW_MOVE"
            elif false_stop:attrib="SL_FALSE_STOP_BEFORE_VALID_REBOUND"
            else:attrib="TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND"
        base.append({
            "zone_id":r.zone_id,"first_touch_ts":r.first_touch_ts,"period":period(r.first_touch_ts),
            "execution_mode":r.execution_mode,"entry_ts":r.entry_ts,
            "entry_price":float(r.entry_price),"sl_reference":float(r.sl_reference),
            "tp1_level":float(r.tp1_level) if np.isfinite(r.tp1_level) else np.nan,
            "tp1_rr":float(r.tp1_rr) if np.isfinite(r.tp1_rr) else np.nan,
            "frozen_target":pol,"frozen_target_level":float(tp),"frozen_target_rr":float(rr),
            "z1_level":float(r.z1_level),"z1_hit_ts":r.z1_hit_ts,
            "zone_1zw_valid":bool(r.zone_1zw_valid),"late_after_z1":late,
            "baseline_outcome":out,"baseline_resolution_ts":rt,"baseline_realized_r":real,
            "baseline_loss_attribution":attrib,
        })
    B=pd.DataFrame(base)

    rows=[]
    for r in B.itertuples(index=False):
        for cand in CANDS:
            out="";rt=pd.NaT;real=np.nan;skipped=False
            tp=float(r.frozen_target_level)

            if cand=="BASELINE":
                out=r.baseline_outcome;rt=r.baseline_resolution_ts;real=r.baseline_realized_r

            elif cand=="C1_NO_CHASE_AFTER_1ZW":
                if r.late_after_z1:
                    out="SKIP";skipped=True
                else:
                    out,rt,real=touch_resolve_explicit(raw5,r.entry_ts,r.entry_price,r.sl_reference,tp,end)

            elif cand=="C2_CLOSE_BASED_INVALIDATION":
                out,rt,real=close_resolve(raw5,m15,r.entry_ts,r.entry_price,r.sl_reference,tp,end)

            elif cand=="C3_DELAYED_SWEEP_USE_TP1":
                if r.execution_mode=="DELAYED_SWEEP_RECLAIM" and np.isfinite(r.tp1_level):
                    tp=float(r.tp1_level)
                out,rt,real=touch_resolve_explicit(raw5,r.entry_ts,r.entry_price,r.sl_reference,tp,end)

            elif cand=="C4_CAP_TARGET_AT_1ZW":
                if r.z1_level>r.entry_price and r.z1_level<tp:
                    tp=float(r.z1_level)
                out,rt,real=touch_resolve_explicit(raw5,r.entry_ts,r.entry_price,r.sl_reference,tp,end)

            elif cand=="C5_CLOSE_INVALIDATION_PLUS_1ZW_CAP":
                if r.z1_level>r.entry_price and r.z1_level<tp:
                    tp=float(r.z1_level)
                out,rt,real=close_resolve(raw5,m15,r.entry_ts,r.entry_price,r.sl_reference,tp,end)

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"execution_mode":r.execution_mode,
                "entry_ts":r.entry_ts,"candidate":cand,
                "baseline_outcome":r.baseline_outcome,
                "baseline_loss_attribution":r.baseline_loss_attribution,
                "cand_outcome":out,"cand_resolution_ts":rt,"cand_realized_r":real,
                "cand_target_level":tp,"skipped":skipped,
            })
    L=pd.DataFrame(rows)

    summaries=[]
    for per in ["DEV","REF"]:
        b=B[B.period==per]
        bw=b[b.baseline_outcome=="WIN"]
        bl=b[b.baseline_outcome=="LOSS"]
        for cand in CANDS:
            q=L[(L.period==per)&(L.candidate==cand)]
            p=perf(q)
            win_ret=int(((q.baseline_outcome=="WIN")&(q.cand_outcome=="WIN")).sum())
            win_skip=int(((q.baseline_outcome=="WIN")&(q.cand_outcome=="SKIP")).sum())
            win_lost=int(((q.baseline_outcome=="WIN")&(~q.cand_outcome.isin(["WIN","SKIP"]))).sum())
            loss_to_win=int(((q.baseline_outcome=="LOSS")&(q.cand_outcome=="WIN")).sum())
            loss_skip=int(((q.baseline_outcome=="LOSS")&(q.cand_outcome=="SKIP")).sum())
            summaries.append({
                "period":per,"candidate":cand,
                "baseline_wins":len(bw),"baseline_losses":len(bl),
                "baseline_win_retained":win_ret,
                "baseline_win_retention":win_ret/len(bw) if len(bw) else np.nan,
                "baseline_win_skipped":win_skip,"baseline_win_lost_nonwin":win_lost,
                "baseline_loss_to_win":loss_to_win,"baseline_loss_skipped":loss_skip,
                "trade_count_reduction":int((q.cand_outcome=="SKIP").sum()),
                **p
            })
    S=pd.DataFrame(summaries)

    matrix=[]
    cats=[
      "ZONE_NOT_1ZW_VALID","ENTRY_LATE_AFTER_1ZW_MOVE",
      "SL_FALSE_STOP_BEFORE_VALID_REBOUND","TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND"
    ]
    for per in ["DEV","REF"]:
        for cat in cats:
            ids=set(B[(B.period==per)&(B.baseline_outcome=="LOSS")&(B.baseline_loss_attribution==cat)].zone_id)
            for cand in CANDS[1:]:
                q=L[(L.period==per)&(L.candidate==cand)&(L.zone_id.isin(ids))]
                matrix.append({
                    "period":per,"loss_category":cat,"candidate":cand,"n":len(q),
                    "to_win":int((q.cand_outcome=="WIN").sum()),
                    "skipped":int((q.cand_outcome=="SKIP").sum()),
                    "still_loss":int((q.cand_outcome=="LOSS").sum()),
                    "other":int((~q.cand_outcome.isin(["WIN","LOSS","SKIP"])).sum()),
                })
    M=pd.DataFrame(matrix)

    B.to_csv(ROOT/f"{PFX}_BaselineLedger.csv.gz",index=False,compression="gzip")
    L.to_csv(ROOT/f"{PFX}_CandidateLedger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    M.to_csv(ROOT/f"{PFX}_LossCategoryMatrix.csv",index=False)

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x,d=3):
        if x==np.inf:return "∞"
        return "—" if not np.isfinite(x) else f"{x:.{d}f}"

    lines=[
      "# BNB B38-S8 — Loss Recovery / Avoidance Matrix","",
      "**All mechanics applied to the whole eligible population. Baseline WIN sacrifice is explicitly measured.**","",
      "## Candidate-level result","",
      "| Period | Candidate | W-L | WR | Baseline WIN retention | WIN skipped | WIN lost | LOSS→WIN | LOSS skipped | Trade reduction | Exp | PF | Max DD |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
          f"| {r.period} | {r.candidate} | {r.wins}-{r.losses} | {pct(r.wr)} | "
          f"{r.baseline_win_retained}/{r.baseline_wins} ({pct(r.baseline_win_retention)}) | "
          f"{r.baseline_win_skipped} | {r.baseline_win_lost_nonwin} | {r.baseline_loss_to_win} | "
          f"{r.baseline_loss_skipped} | {r.trade_count_reduction} | {num(r.expectancy_r)}R | "
          f"{num(r.profit_factor)} | {num(r.max_drawdown_r)}R |"
        )

    lines += ["","## Loss-category conversion matrix",""]
    for per in ["DEV","REF"]:
        lines += [f"### {per}","",
          "| Baseline loss category | Candidate | N | To WIN | Skipped | Still LOSS | Other |",
          "|---|---|---:|---:|---:|---:|---:|"
        ]
        for r in M[M.period==per].itertuples(index=False):
            lines.append(f"| {r.loss_category} | {r.candidate} | {r.n} | {r.to_win} | {r.skipped} | {r.still_loss} | {r.other} |")
        lines.append("")

    lines += ["## Interpretation boundary",
      "C1 is an avoidance rule; skipped losses are not wins.",
      "C2/C4/C5 keep trade count intact and test whether execution mechanics alone can rescue losses.",
      "C3 changes only the already-known structural target for delayed sweep.",
      "No candidate is promoted to final policy in S8."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S8_LOSS_RECOVERY_MATRIX_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
