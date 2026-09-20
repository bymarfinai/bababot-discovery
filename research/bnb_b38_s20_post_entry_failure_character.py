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
PFX="BNB_B38_S20_POST_ENTRY_FAILURE_CHARACTER"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727

CANDS=[
    "TOUCH_BREAK_LEVEL",
    "CLOSE5_BELOW_BREAK_LEVEL",
    "CLOSE5_BELOW_HOLD_CLOSE",
    "CLOSE5_BELOW_RECLAIM_CLOSE",
    "CLOSE5_BELOW_DEMAND_HIGH",
    "CLOSE15_BELOW_DEMAND_HIGH",
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

def first_touch_idx(raw5,start_ts,level,kind,end):
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def eval_5m_signal(raw5,entry_ts,entry,sl,tp,level,mode,end):
    idx=raw5.index
    i0=int(idx.searchsorted(entry_ts,side="right"))
    i1=int(idx.searchsorted(end,side="right"))
    if i1<=i0:
        return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan}

    for i in range(i0,i1):
        b=raw5.iloc[i]
        tp_hit=float(b.high)>=tp
        sl_hit=float(b.low)<=sl
        if mode=="TOUCH_LOW":
            sig=float(b.low)<=level
            px=level
        elif mode=="CLOSE_BELOW":
            sig=float(b.close)<level
            px=float(b.close)
        else:
            raise RuntimeError(mode)

        if sig:
            if tp_hit or sl_hit:
                return {"signal_status":"AMBIGUOUS_SAME_BAR","signal_ts":idx[i],"exit_price":np.nan}
            return {"signal_status":"CLEAN_SIGNAL","signal_ts":idx[i],"exit_price":float(px)}

        if tp_hit or sl_hit:
            return {"signal_status":"NO_SIGNAL_BEFORE_RESOLUTION","signal_ts":pd.NaT,"exit_price":np.nan}

    return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan}

def eval_15m_close_signal(raw5,m15,entry_ts,entry,sl,tp,level,end):
    midx=m15.index
    i0=int(midx.searchsorted(entry_ts,side="right"))
    i1=int(midx.searchsorted(end,side="right"))
    cand_ts=pd.NaT
    cand_close=np.nan
    for i in range(i0,i1):
        if float(m15.close.iloc[i])<level:
            cand_ts=midx[i]
            cand_close=float(m15.close.iloc[i])
            break
    if pd.isna(cand_ts):
        return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan}

    # Conservative: any TP/SL touch through candidate close invalidates clean ordering.
    ridx=raw5.index
    r0=int(ridx.searchsorted(entry_ts,side="right"))
    r1=int(ridx.searchsorted(cand_ts,side="right"))
    seg=raw5.iloc[r0:r1]
    if len(seg):
        tp_hits=seg[seg.high>=tp]
        sl_hits=seg[seg.low<=sl]
        if len(tp_hits) or len(sl_hits):
            # If the resolution happens on the same 15m candidate bar or earlier,
            # we do not claim the close signal was predictive.
            return {"signal_status":"NO_SIGNAL_BEFORE_RESOLUTION","signal_ts":pd.NaT,"exit_price":np.nan}
    return {"signal_status":"CLEAN_SIGNAL","signal_ts":cand_ts,"exit_price":cand_close}

def summarize(q):
    n=len(q)
    bw=q[q.baseline_outcome=="WIN"]
    bl=q[q.baseline_outcome=="LOSS"]
    clean=q[q.signal_status=="CLEAN_SIGNAL"]
    clean_w=clean[clean.baseline_outcome=="WIN"]
    clean_l=clean[clean.baseline_outcome=="LOSS"]

    cf=q.copy()
    cf["cf_r"]=np.where(
        cf.signal_status=="CLEAN_SIGNAL",
        cf.signal_realized_r,
        cf.baseline_realized_r
    )
    cf["cf_outcome"]=np.where(cf.cf_r>1e-12,"WIN",np.where(cf.cf_r<-1e-12,"LOSS","BE"))

    pos=float(cf.loc[cf.cf_r>0,"cf_r"].sum())
    neg=abs(float(cf.loc[cf.cf_r<0,"cf_r"].sum()))

    return {
        "n":n,
        "baseline_wins":len(bw),
        "baseline_losses":len(bl),
        "clean_signals":len(clean),
        "signal_rate":len(clean)/n if n else np.nan,
        "loss_captured":len(clean_l),
        "loss_capture_rate":len(clean_l)/len(bl) if len(bl) else np.nan,
        "winner_false_exit":len(clean_w),
        "winner_false_exit_rate":len(clean_w)/len(bw) if len(bw) else np.nan,
        "signal_precision_loss":len(clean_l)/len(clean) if len(clean) else np.nan,
        "median_signal_r_all":float(clean.signal_realized_r.median()) if len(clean) else np.nan,
        "median_signal_r_loss":float(clean_l.signal_realized_r.median()) if len(clean_l) else np.nan,
        "median_signal_r_win":float(clean_w.signal_realized_r.median()) if len(clean_w) else np.nan,
        "median_minutes_signal_to_sl":float(clean_l.minutes_signal_to_baseline_resolution.median()) if len(clean_l) else np.nan,
        "median_minutes_signal_to_tp1":float(clean_w.minutes_signal_to_baseline_resolution.median()) if len(clean_w) else np.nan,
        "cf_wins":int((cf.cf_outcome=="WIN").sum()),
        "cf_losses":int((cf.cf_outcome=="LOSS").sum()),
        "cf_be":int((cf.cf_outcome=="BE").sum()),
        "cf_wr_ex_be":float((cf.cf_outcome=="WIN").sum()/((cf.cf_outcome=="WIN").sum()+(cf.cf_outcome=="LOSS").sum())) if ((cf.cf_outcome=="WIN").sum()+(cf.cf_outcome=="LOSS").sum()) else np.nan,
        "cf_expectancy_r":float(cf.cf_r.mean()) if n else np.nan,
        "cf_total_r":float(cf.cf_r.sum()) if n else np.nan,
        "cf_pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "cf_max_dd_r":maxdd(cf.sort_values(["entry_ts","zone_id"]).cf_r.tolist()) if n else np.nan,
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
    if int((P.period=="DEV").sum())!=440 or int((P.period=="REF").sum())!=272:
        raise RuntimeError("plan parity drift")

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=pd.Timestamp("2022-01-01T00:00:00Z"))&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    F=fam.set_index("zone_id")

    structs=[]
    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        rec=s18.reconstruct_e2(m15,fr,end)
        if rec is None:
            raise RuntimeError(f"reconstruct fail {r.zone_id}")
        if pd.Timestamp(rec["entry_ts"])!=pd.Timestamp(r.entry_ts):
            raise RuntimeError(f"entry mismatch {r.zone_id}")
        if abs(float(rec["entry_price"])-float(r.entry_price))>1e-10:
            raise RuntimeError(f"price mismatch {r.zone_id}")

        reclaim_close=float(m15.close.iloc[rec["reclaim_i"]])
        hold_close=float(m15.close.iloc[rec["hold_i"]])
        break_level=max(float(m15.high.iloc[rec["reclaim_i"]]),float(rec["hold_high"]))

        structs.append({
            "zone_id":r.zone_id,
            "break_level":break_level,
            "hold_close":hold_close,
            "reclaim_close":reclaim_close,
            "demand_high":float(fr.demand_high),
            "demand_low":float(fr.demand_low),
        })
    P=P.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    P["is_wide_q4"]=P.baseline_sl_pct>WIDE_CUT

    rows=[]
    for r in P.itertuples(index=False):
        defs={
            "TOUCH_BREAK_LEVEL":("5M","TOUCH_LOW",float(r.break_level)),
            "CLOSE5_BELOW_BREAK_LEVEL":("5M","CLOSE_BELOW",float(r.break_level)),
            "CLOSE5_BELOW_HOLD_CLOSE":("5M","CLOSE_BELOW",float(r.hold_close)),
            "CLOSE5_BELOW_RECLAIM_CLOSE":("5M","CLOSE_BELOW",float(r.reclaim_close)),
            "CLOSE5_BELOW_DEMAND_HIGH":("5M","CLOSE_BELOW",float(r.demand_high)),
            "CLOSE15_BELOW_DEMAND_HIGH":("15M","CLOSE_BELOW",float(r.demand_high)),
        }
        risk=float(r.entry_price-r.touch_low_sl)
        for cand in CANDS:
            tf,mode,level=defs[cand]
            if tf=="5M":
                z=eval_5m_signal(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),float(r.tp1),level,mode,end)
            else:
                z=eval_15m_close_signal(raw5,m15,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),float(r.tp1),level,end)

            if z["signal_status"]=="CLEAN_SIGNAL":
                sig_r=(float(z["exit_price"])-float(r.entry_price))/risk
                mins=float((pd.Timestamp(r.baseline_resolution_ts)-pd.Timestamp(z["signal_ts"]))/pd.Timedelta(minutes=1))
            else:
                sig_r=np.nan
                mins=np.nan

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "entry_ts":r.entry_ts,"candidate":cand,
                "is_wide_q4":bool(r.is_wide_q4),
                "entry_price":r.entry_price,"structural_sl":r.touch_low_sl,"tp1":r.tp1,
                "signal_level":level,
                "signal_status":z["signal_status"],
                "signal_ts":z["signal_ts"],
                "signal_exit_price":z["exit_price"],
                "signal_realized_r":sig_r,
                "minutes_signal_to_baseline_resolution":mins,
                "baseline_outcome":r.baseline_outcome,
                "baseline_resolution_ts":r.baseline_resolution_ts,
                "baseline_realized_r":r.baseline_realized_r,
            })
    L=pd.DataFrame(rows)

    SUM=[]
    for scope,mask in [
        ("ALL",pd.Series(True,index=P.index)),
        ("Q4_WIDE",P.is_wide_q4),
    ]:
        ids=set(P.loc[mask,"zone_id"])
        for per in ["DEV","REF"]:
            for cand in CANDS:
                q=L[(L.zone_id.isin(ids))&(L.period==per)&(L.candidate==cand)]
                SUM.append({"scope":scope,"period":per,"candidate":cand,**summarize(q)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for scope,ids in [
            ("ALL",set(P[P.year==y].zone_id)),
            ("Q4_WIDE",set(P[(P.year==y)&(P.is_wide_q4)].zone_id)),
        ]:
            if not ids: continue
            for cand in CANDS:
                q=L[(L.zone_id.isin(ids))&(L.year==y)&(L.candidate==cand)]
                if len(q):
                    Y.append({"year":y,"scope":scope,"candidate":cand,**summarize(q)})
    Y=pd.DataFrame(Y)

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\nDEV_PLANS=440\nREF_PLANS=272\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S20 — Post-Entry Failure Character","",
        f"Frozen E2 signature: `{sig}`","",
        "## Structural failure-state audit","",
        "| Scope | Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | Med signal R (loss) | Lead to SL | Lead to later TP1 | CF W-L-BE | CF Exp | CF Total R |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.scope} | {r.period} | {r.candidate} | {r.clean_signals}/{r.n} ({fmt_pct(r.signal_rate)}) | "
            f"{r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_loss)} | {fmt_num(r.median_signal_r_loss)}R | "
            f"{fmt_num(r.median_minutes_signal_to_sl,1)}m | {fmt_num(r.median_minutes_signal_to_tp1,1)}m | "
            f"{r.cf_wins}-{r.cf_losses}-{r.cf_be} | {fmt_num(r.cf_expectancy_r)}R | {fmt_num(r.cf_total_r)}R |"
        )

    lines += ["","## Annual stability — Q4 wide subset","",
        "| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | CF Total R |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    qy=Y[Y.scope=="Q4_WIDE"]
    for r in qy.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_loss)} | {fmt_num(r.cf_expectancy_r)}R | {fmt_num(r.cf_total_r)}R |"
        )

    lines += ["","## Interpretation boundary",
      "S20 discovers failure states only; it does not promote a live exit rule.",
      "A state that captures losses but exits too many eventual TP1 winners is not considered a valid failure character.",
      "Any promoted early-exit policy must be preregistered separately."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S20_POST_ENTRY_FAILURE_CHARACTER_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
