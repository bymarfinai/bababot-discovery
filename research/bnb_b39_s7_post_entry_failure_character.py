#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s4_first5_expansion_detector as s4
import bnb_b39_s6_structural_invalidation as s6

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S7_POST_ENTRY_FAILURE_CHARACTER"
START=pd.Timestamp("2022-01-01T00:00:00Z")
D1_CUT=s4.D1_CUT
EXPECTED_SIGNATURE=s4.DETECTOR_SIGNATURE

CANDS=[
    "TOUCH_DEMAND_HIGH",
    "CLOSE5_BELOW_DEMAND_HIGH",
    "CLOSE5_BELOW_ANCHOR",
    "CLOSE5_BELOW_D1_LOW",
    "CLOSE15_BELOW_ANCHOR",
    "CLOSE15_BELOW_DEMAND_HIGH",
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

def first_touch_idx(raw5,start_ts,level,kind,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(start_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:return None
    arr=(raw5.high if kind=="HIGH" else raw5.low).to_numpy(float,copy=False)[i0:i1]
    z=np.flatnonzero(arr>=level) if kind=="HIGH" else np.flatnonzero(arr<=level)
    return i0+int(z[0]) if len(z) else None

def eval_5m(raw5,entry_ts,target,floor,level,mode,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(entry_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    if i1<=i0:
        return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan,"signal_level":level}

    for i in range(i0,i1):
        b=raw5.iloc[i]
        tp_hit=float(b.high)>=target
        sl_hit=float(b.low)<=floor

        if mode=="TOUCH_LOW":
            sig=float(b.low)<=level
            exit_px=level
        elif mode=="CLOSE_BELOW":
            sig=float(b.close)<level
            exit_px=float(b.close)
        else:
            raise RuntimeError(mode)

        if sig:
            if tp_hit or sl_hit:
                return {
                    "signal_status":"AMBIGUOUS_SAME_BAR","signal_ts":idx[i],
                    "exit_price":np.nan,"signal_level":level
                }
            return {
                "signal_status":"CLEAN_SIGNAL","signal_ts":idx[i],
                "exit_price":float(exit_px),"signal_level":level
            }

        if tp_hit or sl_hit:
            return {
                "signal_status":"NO_SIGNAL_BEFORE_RESOLUTION","signal_ts":pd.NaT,
                "exit_price":np.nan,"signal_level":level
            }

    return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan,"signal_level":level}

def eval_15m(raw5,m15,entry_ts,target,floor,level,deadline):
    midx=m15.index
    i0=int(midx.searchsorted(pd.Timestamp(entry_ts),side="right"))
    i1=int(midx.searchsorted(pd.Timestamp(deadline),side="right"))

    cand_ts=pd.NaT
    cand_close=np.nan
    for i in range(i0,i1):
        if float(m15.close.iloc[i])<level:
            cand_ts=midx[i]
            cand_close=float(m15.close.iloc[i])
            break

    if pd.isna(cand_ts):
        return {"signal_status":"NO_SIGNAL","signal_ts":pd.NaT,"exit_price":np.nan,"signal_level":level}

    ridx=raw5.index
    r0=int(ridx.searchsorted(pd.Timestamp(entry_ts),side="right"))
    r1=int(ridx.searchsorted(pd.Timestamp(cand_ts),side="right"))
    seg=raw5.iloc[r0:r1]

    if len(seg):
        if bool((seg.high>=target).any()) or bool((seg.low<=floor).any()):
            return {
                "signal_status":"NO_SIGNAL_BEFORE_RESOLUTION","signal_ts":pd.NaT,
                "exit_price":np.nan,"signal_level":level
            }

    return {
        "signal_status":"CLEAN_SIGNAL","signal_ts":cand_ts,
        "exit_price":cand_close,"signal_level":level
    }

def reclaim_flags(raw5,signal_ts,level,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="right"))
    out={"reclaim_next5":False,"reclaim_within15":False}
    if i0>=len(raw5): return out

    # Next completed 5m close.
    b=raw5.iloc[i0]
    out["reclaim_next5"]=bool(float(b.close)>=level)

    i1=min(len(raw5),i0+3)
    end_i=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    i1=min(i1,end_i)
    if i1>i0:
        out["reclaim_within15"]=bool((raw5.close.iloc[i0:i1]>=level).any())
    return out

def false_exit_anatomy(raw5,signal_ts,level,target,deadline,entry,floor):
    ti=first_touch_idx(raw5,signal_ts,target,"HIGH",deadline)
    if ti is None:
        return {
            "later_target_ts":pd.NaT,"minutes_to_target":np.nan,
            "overshoot_original_r":np.nan,"reclaim_next5":False,"reclaim_within15":False
        }

    later_ts=raw5.index[ti]
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="left"))
    i1=ti+1
    seg=raw5.iloc[i0:i1]
    orig_risk=entry-floor
    overshoot=max(0.0,(level-float(seg.low.min()))/orig_risk) if len(seg) and orig_risk>0 else np.nan
    flags=reclaim_flags(raw5,signal_ts,level,deadline)
    return {
        "later_target_ts":later_ts,
        "minutes_to_target":float((later_ts-pd.Timestamp(signal_ts))/pd.Timedelta(minutes=1)),
        "overshoot_original_r":overshoot,
        **flags
    }

def summarize(q):
    q=q.sort_values(["entry_ts","zone_id"]).copy()
    bw=q[q.baseline_status=="WIN"]
    bl=q[q.baseline_status=="LOSS"]
    clean=q[q.signal_status=="CLEAN_SIGNAL"]
    clean_w=clean[clean.baseline_status=="WIN"]
    clean_l=clean[clean.baseline_status=="LOSS"]

    cf=q.copy()
    cf["cf_r"]=np.where(
        cf.signal_status=="CLEAN_SIGNAL",
        cf.signal_realized_r,
        cf.baseline_realized_r
    )
    cf["cf_status"]=np.where(cf.cf_r>1e-12,"WIN",np.where(cf.cf_r<-1e-12,"LOSS","BE"))

    pos=float(cf.loc[cf.cf_r>0,"cf_r"].sum())
    neg=abs(float(cf.loc[cf.cf_r<0,"cf_r"].sum()))

    return {
        "n":len(q),
        "baseline_wins":len(bw),
        "baseline_losses":len(bl),
        "clean_signals":len(clean),
        "signal_rate":len(clean)/len(q) if len(q) else np.nan,
        "loss_captured":len(clean_l),
        "loss_capture_rate":len(clean_l)/len(bl) if len(bl) else np.nan,
        "winner_false_exit":len(clean_w),
        "winner_false_exit_rate":len(clean_w)/len(bw) if len(bw) else np.nan,
        "signal_precision_loss":len(clean_l)/len(clean) if len(clean) else np.nan,
        "median_exit_r_all":float(clean.signal_realized_r.median()) if len(clean) else np.nan,
        "median_exit_r_loss":float(clean_l.signal_realized_r.median()) if len(clean_l) else np.nan,
        "median_exit_r_win":float(clean_w.signal_realized_r.median()) if len(clean_w) else np.nan,
        "median_lead_to_floor_min":float(clean_l.minutes_signal_to_baseline_resolution.median()) if len(clean_l) else np.nan,
        "median_lead_to_target_min":float(clean_w.minutes_signal_to_baseline_resolution.median()) if len(clean_w) else np.nan,
        "false_exit_reclaim_next5_rate":float(clean_w.reclaim_next5.mean()) if len(clean_w) else np.nan,
        "false_exit_reclaim_within15_rate":float(clean_w.reclaim_within15.mean()) if len(clean_w) else np.nan,
        "median_false_exit_overshoot_original_r":float(clean_w.overshoot_original_r.median()) if len(clean_w) else np.nan,
        "cf_wins":int((cf.cf_status=="WIN").sum()),
        "cf_losses":int((cf.cf_status=="LOSS").sum()),
        "cf_be":int((cf.cf_status=="BE").sum()),
        "cf_wr_ex_be":float((cf.cf_status=="WIN").sum()/((cf.cf_status=="WIN").sum()+(cf.cf_status=="LOSS").sum())) if ((cf.cf_status=="WIN").sum()+(cf.cf_status=="LOSS").sum()) else np.nan,
        "cf_expectancy_r":float(cf.cf_r.mean()) if len(cf) else np.nan,
        "cf_total_r":float(cf.cf_r.sum()) if len(cf) else np.nan,
        "cf_pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "cf_max_dd_r":maxdd(cf.cf_r.tolist()) if len(cf) else np.nan,
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
    baseline_check={"DEV":{"WIN":0,"LOSS":0,"AMBIGUOUS":0,"UNRESOLVED":0},
                    "REF":{"WIN":0,"LOSS":0,"AMBIGUOUS":0,"UNRESOLVED":0}}

    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        anchor=float(r.anchor_price)
        er=float(r.event_risk)
        floor=float(r.demand_low)
        entry=float(anchor+float(r.p5_close_r)*er)
        target=anchor+er
        d1_low=float(anchor+float(r.p5_low_r)*er)
        demand_high=float(fr.demand_high)
        deadline=min(end,pd.Timestamp(r.first_touch_ts)+pd.Timedelta(hours=24))

        bz=s6.resolve(raw5,r.decision_ts,entry,floor,target,deadline)
        baseline_status=bz["status"]
        baseline_r=float(bz["realized_r"])
        baseline_rt=bz["resolution_ts"]
        baseline_check[r.period][baseline_status]=baseline_check[r.period].get(baseline_status,0)+1

        defs={
            "TOUCH_DEMAND_HIGH":("5M","TOUCH_LOW",demand_high),
            "CLOSE5_BELOW_DEMAND_HIGH":("5M","CLOSE_BELOW",demand_high),
            "CLOSE5_BELOW_ANCHOR":("5M","CLOSE_BELOW",anchor),
            "CLOSE5_BELOW_D1_LOW":("5M","CLOSE_BELOW",d1_low),
            "CLOSE15_BELOW_ANCHOR":("15M","CLOSE_BELOW",anchor),
            "CLOSE15_BELOW_DEMAND_HIGH":("15M","CLOSE_BELOW",demand_high),
        }

        orig_risk=entry-floor
        for cand,(tf,mode,level) in defs.items():
            if tf=="5M":
                z=eval_5m(raw5,r.decision_ts,target,floor,level,mode,deadline)
            else:
                z=eval_15m(raw5,m15,r.decision_ts,target,floor,level,deadline)

            if z["signal_status"]=="CLEAN_SIGNAL":
                exit_r=(float(z["exit_price"])-entry)/orig_risk
                if pd.notna(baseline_rt):
                    mins=float((pd.Timestamp(baseline_rt)-pd.Timestamp(z["signal_ts"]))/pd.Timedelta(minutes=1))
                else:
                    mins=np.nan
            else:
                exit_r=np.nan
                mins=np.nan

            anatomy={
                "later_target_ts":pd.NaT,"minutes_to_target":np.nan,
                "overshoot_original_r":np.nan,"reclaim_next5":False,"reclaim_within15":False
            }
            if z["signal_status"]=="CLEAN_SIGNAL" and baseline_status=="WIN":
                anatomy=false_exit_anatomy(
                    raw5,z["signal_ts"],level,target,deadline,entry,floor
                )

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "entry_ts":r.decision_ts,"candidate":cand,
                "entry":entry,"target":target,"floor":floor,
                "anchor":anchor,"d1_low":d1_low,"demand_high":demand_high,
                "signal_level":level,
                "signal_status":z["signal_status"],
                "signal_ts":z["signal_ts"],
                "signal_exit_price":z["exit_price"],
                "signal_realized_r":exit_r,
                "minutes_signal_to_baseline_resolution":mins,
                "baseline_status":baseline_status,
                "baseline_realized_r":baseline_r,
                "baseline_resolution_ts":baseline_rt,
                "GE1R":bool(r.GE1R),
                **anatomy,
            })

    # Frozen market-wide-floor parity from S6/S5.
    if baseline_check["DEV"].get("WIN",0)!=108 or baseline_check["DEV"].get("LOSS",0)!=43:
        raise RuntimeError(f"DEV baseline parity drift {baseline_check['DEV']}")
    if baseline_check["REF"].get("WIN",0)!=83 or baseline_check["REF"].get("LOSS",0)!=17 or baseline_check["REF"].get("AMBIGUOUS",0)!=1:
        raise RuntimeError(f"REF baseline parity drift {baseline_check['REF']}")

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

    FW=E[(E.signal_status=="CLEAN_SIGNAL")&(E.baseline_status=="WIN")].copy()
    FWS=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=FW[(FW.period==per)&(FW.candidate==cand)]
            FWS.append({
                "period":per,"candidate":cand,"false_exit_winners":len(q),
                "reclaim_next5":int(q.reclaim_next5.sum()) if len(q) else 0,
                "reclaim_next5_rate":float(q.reclaim_next5.mean()) if len(q) else np.nan,
                "reclaim_within15":int(q.reclaim_within15.sum()) if len(q) else 0,
                "reclaim_within15_rate":float(q.reclaim_within15.mean()) if len(q) else np.nan,
                "median_signal_to_target_min":float(q.minutes_to_target.median()) if len(q) else np.nan,
                "median_overshoot_original_r":float(q.overshoot_original_r.median()) if len(q) else np.nan,
            })
    FWS=pd.DataFrame(FWS)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FW.to_csv(ROOT/f"{PFX}_FalseExitWinnerLedger.csv.gz",index=False,compression="gzip")
    FWS.to_csv(ROOT/f"{PFX}_FalseExitWinnerSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"DETECTOR=D1_FIRST5_DISPLACEMENT\n"
        f"DETECTOR_SIGNATURE_SHA256={EXPECTED_SIGNATURE}\n"
        f"D1_P5_CLOSE_R_GT={D1_CUT:.17f}\n"
        "ENTRY=MARKET_SIGNAL_CLOSE\n"
        "TARGET=ANCHOR_PLUS_1_EVENT_R\n"
        "STRUCTURAL_FLOOR=DEMAND_LOW\n"
        "CANDIDATES=TOUCH_DEMAND_HIGH,CLOSE5_BELOW_DEMAND_HIGH,CLOSE5_BELOW_ANCHOR,CLOSE5_BELOW_D1_LOW,CLOSE15_BELOW_ANCHOR,CLOSE15_BELOW_DEMAND_HIGH\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S7 — Frozen D1 Post-Entry Failure Character","",
        f"Frozen detector signature: `{EXPECTED_SIGNATURE}`",
        f"D1 unchanged: `p5_close_r > {D1_CUT:.17f}`",
        "Entry = D1 signal close; target = anchor +1 event-R; structural floor remains demand_low.","",
        "## Failure-state audit","",
        "| Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | Med exit R loss | Lead to floor | Lead to later target | Reclaim <=5m | Reclaim <=15m | CF W-L-BE | CF Exp | CF Total R | PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.clean_signals}/{r.n} ({fmt_pct(r.signal_rate)}) | "
            f"{r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_loss)} | {fmt_num(r.median_exit_r_loss)}R | "
            f"{fmt_num(r.median_lead_to_floor_min,1)}m | {fmt_num(r.median_lead_to_target_min,1)}m | "
            f"{fmt_pct(r.false_exit_reclaim_next5_rate)} | {fmt_pct(r.false_exit_reclaim_within15_rate)} | "
            f"{r.cf_wins}-{r.cf_losses}-{r.cf_be} | {fmt_num(r.cf_expectancy_r)}R | "
            f"{fmt_num(r.cf_total_r)}R | {fmt_num(r.cf_pf)} |"
        )

    lines += ["","## Annual counterfactual stability","",
        "| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | CF Total R |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.signal_precision_loss)} | {fmt_num(r.cf_expectancy_r)}R | {fmt_num(r.cf_total_r)}R |"
        )

    lines += ["","## False-exit winner reclaim anatomy","",
        "| Period | Candidate | False exits | Reclaim next5 | Reclaim <=15m | Med signal→target | Med overshoot |",
        "|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in FWS.itertuples(index=False):
        if r.false_exit_winners:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_exit_winners} | "
                f"{r.reclaim_next5} ({fmt_pct(r.reclaim_next5_rate)}) | "
                f"{r.reclaim_within15} ({fmt_pct(r.reclaim_within15_rate)}) | "
                f"{fmt_num(r.median_signal_to_target_min,1)}m | {fmt_num(r.median_overshoot_original_r)} original-R |"
            )

    lines += ["","## Interpretation boundary",
        "S7 discovers failure states only; no early-exit rule is promoted automatically.",
        "A candidate must improve DEV and REF economics while separating losses from eventual winners.",
        "Fast reclaim among false exits indicates a liquidity dip rather than durable failure and is evidence against using that state alone."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S7_POST_ENTRY_FAILURE_CHARACTER_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
